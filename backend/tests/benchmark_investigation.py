"""Offline benchmark: python backend/tests/benchmark_investigation.py [--json] [--check]."""

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
with patch.dict(os.environ, {"GEMINI_API_KEY": "", "VERCEL": "1"}), patch("google.genai.Client"):
    from analyzers.rag_verifier import RAGVerifier
    from core import gemini_client as provider
    from models.investigation import ClaimResult, Evidence, Investigation


FIXTURE = Path(__file__).with_name("fixtures") / "investigation_benchmark.json"
DECISIVE = {"supported", "refuted"}


class OfflineProvider:
    """Only replace SDK generation and HTTP JSON boundaries, never orchestration."""

    def __init__(self, case):
        self.case = case
        self.calls = []
        self.assessments = []
        self.errors = []

    def generate(self, **kwargs):
        schema = kwargs["config"].response_schema["title"]
        self.calls.append(schema)
        if schema == "_Claims":
            value = {"claims": self.case.get("extracted", [self.case.get("claim", self.case["text"])])}
        elif schema == "_Plan":
            value = {"tool": "wikipedia", "query": "Lumen opening date"}
        elif schema == "_Assessment":
            data = json.loads(kwargs["contents"].split("DATA: ", 1)[1])
            citations = []
            for source in data["sources"]:
                fixture = next(s for s in self.case["sources"] if s and s["excerpt"] == source["excerpt"])
                citations.append({"evidence_id": source["id"], "quote": fixture.get("quote", fixture["excerpt"]),
                                  "stance": fixture["stance"]})
            value = {"citations": citations, "reasoning": "Scripted snippet assessment for offline testing.",
                     "uncertainties": [], "followup": {"tool": "duckduckgo", "query": "Lumen independent opening records"}}
            self.assessments.append(value)
        else:
            self.errors.append("Unexpected schema: " + schema)
            raise AssertionError(self.errors[-1])
        return SimpleNamespace(text=json.dumps(value))

    def fetch(self, url, timeout):
        parsed = urlsplit(url)
        params = parse_qs(parsed.query)
        if parsed.netloc == "en.wikipedia.org":
            self.calls.append(("wikipedia", params["srsearch"][0]))
            source = self.case["sources"][0]
            rows = [] if source is None else [{"title": source["title"], "snippet": source["excerpt"]}]
            return {"query": {"search": rows * (2 if self.case.get("duplicate_initial") else 1)}}
        if parsed.netloc == "api.duckduckgo.com":
            self.calls.append(("duckduckgo", params["q"][0]))
            source = self.case["sources"][1]
            return {} if source is None else {"Heading": "Lumen independent record", "AbstractURL": source["url"],
                                              "AbstractText": source["excerpt"]}
        self.errors.append("Unexpected endpoint: " + url)
        raise AssertionError(self.errors[-1])


def single_source_baseline(verifier, text):
    """Comparison policy, not production orchestration: exactly one retrieval."""
    extracted = verifier._extract_claims(text, verifier.call_timeout)
    claims = list(dict.fromkeys(c.strip() for c in extracted.claims if c.strip() and c.strip() in text))
    assert len(claims) == 1, claims
    claim = ClaimResult(id="c1", text=claims[0], verdict="uncertain", reasoning="Single-source baseline.")
    plan = verifier._plan(claim.text, verifier.call_timeout)
    rows = getattr(verifier, "_query_" + plan.tool)(plan.query, verifier.call_timeout)
    for row in rows:
        publisher = verifier._publisher(row["url"])
        excerpt = row["excerpt"].strip()[:3000]
        if not publisher or len(excerpt) < 20 or not row["title"].strip() or verifier.INSTRUCTION_PATTERN.search(excerpt):
            continue
        claim.evidence.append(Evidence(id="c1-e1", title=row["title"], url=row["url"],
                                       publisher=publisher, excerpt=excerpt,
                                       retrieved_at=datetime.now(timezone.utc).isoformat()))
        break
    if claim.evidence:
        source = claim.evidence[0]
        assessment = verifier._assess(claim.text, claim.evidence, verifier.call_timeout)
        first = assessment.citations[0] if assessment.citations else None
        if first and first.evidence_id == source.id and first.quote in source.excerpt:
            source.cited_quotes.append(first.quote)
            source.stances.append(first.stance)
            if not assessment.uncertainties:
                claim.verdict = first.stance
    return Investigation(claims=[claim], recommended_action="Review full sources.")


def run_case(case, baseline=False, max_calls=None):
    boundary = OfflineProvider(case)
    verifier = RAGVerifier(max_calls=max_calls if max_calls is not None else 16)
    client = Mock()
    client.models.generate_content.side_effect = boundary.generate
    with ExitStack() as stack:
        stack.enter_context(patch.object(provider, "gemini_client", client))
        stack.enter_context(patch.object(verifier, "_fetch_json", side_effect=boundary.fetch))
        network = stack.enter_context(patch.object(socket.socket, "connect", side_effect=AssertionError("Offline only")))
        started = time.perf_counter()
        result = single_source_baseline(verifier, case["text"]) if baseline else verifier.investigate(case["text"])
        runtime = (time.perf_counter() - started) * 1000
        network.assert_not_called()
    assert not boundary.errors, boundary.errors
    assert not any("unavailable or timed out" in e.message for e in result.trace), result.model_dump()
    assert len(result.claims) == 1, result.model_dump()
    claim = result.claims[0]
    assert claim.text == case.get("claim", case["text"])
    calls = len(boundary.calls) if baseline else sum(e.phase == "act" for e in result.trace)
    assert calls == len(boundary.calls) <= verifier.max_calls
    verdict = claim.verdict
    citations = [{"evidence_id": source.id, "quote": quote, "stance": verdict}
                 for source in claim.evidence if verdict in source.stances
                 for quote in set(source.cited_quotes)]
    valid_publishers = set()
    decisive_citations = [c for c in citations if c["stance"] == verdict] if verdict in DECISIVE else []
    valid = 0
    for citation in decisive_citations:
        source = next((e for e in claim.evidence if e.id == citation["evidence_id"]), None)
        if source and len(citation["quote"]) >= 20 and citation["quote"] in source.excerpt and RAGVerifier._publisher(source.url):
            valid += 1
            valid_publishers.add(source.publisher)
    retrievals = [c for c in boundary.calls if isinstance(c, tuple)]
    if baseline:
        assert len(retrievals) == 1 and calls <= 4
    adaptive = len(retrievals) == 2 and retrievals[0] != retrievals[1] and any(e.phase == "adapt" for e in result.trace)
    if case["id"] == "duplicated_sources":
        assert len(claim.evidence) == 1
    if case["id"] == "hallucinated_quotes" and not baseline and max_calls is None:
        assert any("fabricated" in u for u in claim.uncertainties)
        assert not any(e.cited_quotes or e.stances for e in claim.evidence)
    if case["id"].startswith("prompt_injection_") and max_calls is None:
        assert not claim.evidence and not boundary.assessments
    return {"id": case["id"], "expected": case["expected"], "verdict": verdict,
            "correct": verdict == case["expected"], "abstained": verdict not in DECISIVE,
            "followup_required": case["followup"], "adaptive_followup": adaptive,
            "calls": calls, "runtime_ms": round(runtime, 3),
            "valid_decisive_citations": valid, "decisive_citations": len(decisive_citations),
            "independent_decisive": verdict in DECISIVE and len(valid_publishers) >= 2}


def summarize(rows):
    abstentions = [r for r in rows if r["expected"] not in DECISIVE]
    followups = [r for r in rows if r["followup_required"]]
    return {"verdict_accuracy": [sum(r["correct"] for r in rows), len(rows)],
            "decisive_verdict_citation_validity": [sum(r["valid_decisive_citations"] for r in rows), sum(r["decisive_citations"] for r in rows)],
            "independent_decisive_verdicts": [sum(r["independent_decisive"] for r in rows), sum(not r["abstained"] for r in rows)],
            "abstention_accuracy": [sum(r["abstained"] for r in abstentions), len(abstentions)],
            "adaptive_followup_coverage": [sum(r["adaptive_followup"] for r in followups), len(followups)],
            "max_calls": max(r["calls"] for r in rows), "total_calls": sum(r["calls"] for r in rows),
            "max_runtime_ms": max(r["runtime_ms"] for r in rows),
            "total_runtime_ms": round(sum(r["runtime_ms"] for r in rows), 3)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print full machine-readable measurements")
    parser.add_argument("--check", action="store_true", help="Exit 1 on investigation verdict mismatches; baseline is informational")
    args = parser.parse_args()
    cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]
    assert len(cases) >= 8 and len({c["id"] for c in cases}) == len(cases)
    output = {}
    for name, baseline in [("investigation", False), ("single_source_baseline", True)]:
        rows = [run_case(case, baseline) for case in cases]
        output[name] = {"summary": summarize(rows), "cases": rows}
    budget = run_case(cases[0], max_calls=2)
    assert budget["calls"] == 2 and budget["verdict"] == "uncertain"
    output["budget_probe"] = budget
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        for name in ("investigation", "single_source_baseline"):
            print(name + ": " + json.dumps(output[name]["summary"]))
            for row in output[name]["cases"]:
                print(f"  {row['id']}: {row['verdict']} (expected {row['expected']}), {row['calls']} calls, {row['runtime_ms']} ms")
        print("Two-call budget probe: passed")
    if args.check:
        mismatches = [r["id"] for r in output["investigation"]["cases"] if not r["correct"]]
        if mismatches:
            print("Investigation verdict mismatches: " + ", ".join(mismatches), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
