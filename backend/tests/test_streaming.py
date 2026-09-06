"""Offline route parity, live trace, validation, and cancellation regressions."""

import asyncio
import json
import os
import threading
import unittest
from unittest.mock import AsyncMock, patch

with patch.dict(os.environ, {"VERCEL": "1", "GEMINI_API_KEY": ""}), \
        patch("socket.socket.connect", side_effect=AssertionError("Network disabled")):
    from app import app

from fastapi.testclient import TestClient
from core.investigation_stream import analysis_response, stage, emit
from models.investigation import ClaimResult, Investigation, TraceEvent
from models.schemas import AnalysisCoverage, AnalysisProvenance


def investigation(text, emit):
    emit(TraceEvent(sequence=1, phase="act", message="Retrieve source snippets", elapsed_ms=0))
    emit(TraceEvent(sequence=2, phase="conclude", message="Abstain", elapsed_ms=1))
    return Investigation(claims=[ClaimResult(id="c1", text=text, verdict="uncertain",
        reasoning="Not enough evidence", uncertainties=["No independent sources"] )],
        recommended_action="Obtain independent sources.", uncertainties=["Snippet-only evidence"])


def stable(result):
    result = dict(result)
    for field in ("id", "timestamp", "processing_time_ms"):
        result.pop(field, None)
    if result.get("investigation"):
        result["investigation"] = dict(result["investigation"])
        result["investigation"]["trace"] = [dict(event, elapsed_ms=0)
                                              for event in result["investigation"]["trace"]]
    for report in result.get("provenance", []):
        report["duration_ms"] = 0
    return result


class StreamingTests(unittest.TestCase):
    def setUp(self):
        self.client = self.enterContext(TestClient(app))
        self.enterContext(patch("routers.text.rag_verifier.investigate", side_effect=investigation))
        self.local = self.enterContext(patch("routers.text.text_analyzer.analyze", return_value=([], {})))

    def records(self, response):
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.headers["content-type"].startswith("application/x-ndjson"))
        records = [json.loads(line) for line in response.iter_lines()]
        trace = [row["event"] for row in records if row["type"] == "trace"]
        self.assertEqual([e["sequence"] for e in trace], list(range(1, len(trace) + 1)))
        self.assertEqual([e["elapsed_ms"] for e in trace], sorted(e["elapsed_ms"] for e in trace))
        self.assertTrue(all(row["type"] == "trace" for row in records[:-1]))
        return records

    def test_text_parity_and_investigation_trace(self):
        payload = {"text": "A checkable claim."}
        normal = self.client.post("/api/analyze/text", json=payload).json()
        rows = self.records(self.client.post("/api/analyze/text?stream=true", json=payload))
        self.assertEqual(rows[-1]["type"], "result")
        result = rows[-1]["result"]
        self.assertEqual(stable(normal), stable(result))
        self.assertEqual(result["investigation"]["trace"], [r["event"] for r in rows[:-1]])
        self.assertIsNone(result["is_authentic"])
        self.assertIsNone(result["trust_score"])
        self.assertEqual(result["verdict"], "inconclusive")
        self.assertEqual(result["claims_verified"], 0)
        self.assertIn("No independent sources", result["uncertainties"])
        self.assertEqual(self.local.call_args.kwargs,
                         {"check_ai_generated": True, "check_scam": True, "use_llm": False})

    def test_independent_toggles(self):
        for ai, scam in ((True, False), (False, True), (False, False)):
            self.local.reset_mock()
            response = self.client.post("/api/analyze/text", json={"text": "Example content.",
                "check_claims": False, "check_ai_generated": ai, "check_scam": scam})
            self.assertEqual(response.status_code, 200)
            if ai or scam:
                self.assertEqual(self.local.call_args.kwargs,
                                 {"check_ai_generated": ai, "check_scam": scam, "use_llm": False})
            else:
                self.local.assert_not_called()

    def test_stream_error_is_terminal_and_sanitized(self):
        self.local.side_effect = RuntimeError("private provider credentials")
        rows = self.records(self.client.post("/api/analyze/text?stream=true", json={"text": "Example text"}))
        self.assertEqual(rows[-1]["type"], "error")
        self.assertNotIn("private", rows[-1]["message"])
        self.assertFalse(any(r["type"] == "result" for r in rows))

    def test_validation_before_streaming(self):
        for text in ("", "   ", "x" * 12001):
            response = self.client.post("/api/analyze/text?stream=true", json={"text": text})
            self.assertEqual(response.status_code, 422)
            self.assertIn("application/json", response.headers["content-type"])
        for kind, mime, limit in (("image", "image/png", 15), ("video", "video/mp4", 50),
                                  ("audio", "audio/wav", 20)):
            response = self.client.post(f"/api/analyze/{kind}?stream=true",
                                       files={"file": ("sample", b"bad", "text/plain")})
            self.assertEqual(response.status_code, 415)
            with patch("starlette.datastructures.UploadFile.read", new_callable=AsyncMock,
                       return_value=b"x" * (limit * 1024 * 1024 + 1)) as read:
                response = self.client.post(f"/api/analyze/{kind}?stream=true",
                                           files={"file": ("sample", b"data", mime)})
                self.assertEqual(response.status_code, 413)
                read.assert_awaited_once_with(limit * 1024 * 1024 + 1)
                self.assertIn("application/json", response.headers["content-type"])

    def test_media_parity_preserves_verdict(self):
        for kind, mime in (("image", "image/png"), ("video", "video/mp4"), ("audio", "audio/wav")):
            with self.subTest(kind=kind):
                report = AnalysisProvenance(provider="Google Gemini", status="not_configured",
                    coverage=AnalysisCoverage(description="Mock sample"), message="Provider not configured")
                with patch(f"routers.{kind}.{kind}_analyzer.analyze", return_value=([], {})), \
                        patch(f"routers.{kind}.request_gemini", new_callable=AsyncMock, return_value=report), \
                        patch("routers.image.ocr_engine.extract_text", return_value="A checkable claim."), \
                        patch("routers.image.prepare_image", return_value=([], AnalysisCoverage(description="Image"))):
                    normal = self.client.post(f"/api/analyze/{kind}", files={"file": ("sample", b"data", mime)}).json()
                    rows = self.records(self.client.post(f"/api/analyze/{kind}?stream=true",
                                        files={"file": ("sample", b"data", mime)}))
                    self.assertEqual(rows[-1]["type"], "result")
                    result = rows[-1]["result"]
                    self.assertEqual(stable(normal), stable(result))
                    self.assertEqual(result["verdict"], "inconclusive")
                    self.assertTrue(result["recommended_action"])
                    self.assertTrue(result["uncertainties"])


class LiveCancellationTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_investigation_callback_prevents_future_work(self):
        entered = threading.Event()
        release = threading.Event()
        finished = threading.Event()
        later = []

        def worker():
            try:
                entered.set()
                release.wait(3)
                emit(TraceEvent(sequence=1, phase="act", message="Next provider call", elapsed_ms=0))
                later.append(True)
            finally:
                finished.set()

        async def operation():
            await stage("investigation", "Start investigation", worker)

        response = await analysis_response(operation, True)
        iterator = response.body_iterator
        try:
            await asyncio.wait_for(anext(iterator), 1)
            self.assertTrue(await asyncio.to_thread(entered.wait, 1))
            await iterator.aclose()
            release.set()
            self.assertTrue(await asyncio.to_thread(finished.wait, 2))
            self.assertEqual(later, [])
        finally:
            release.set()

    async def test_trace_is_live_and_cancellation_stops_next_stage(self):
        entered = threading.Event()
        release = threading.Event()
        later = []

        def worker():
            entered.set()
            release.wait(3)

        async def operation():
            await stage("local", "Blocked local check", worker)
            later.append(True)

        response = await analysis_response(operation, True)
        iterator = response.body_iterator
        try:
            first = await asyncio.wait_for(anext(iterator), 1)
            self.assertEqual(json.loads(first)["type"], "trace")
            await asyncio.to_thread(entered.wait, 1)
            self.assertFalse(release.is_set(), "Trace must arrive before work completes")
            await iterator.aclose()
            release.set()
            await asyncio.sleep(0.05)
            self.assertEqual(later, [])
        finally:
            release.set()


class LocalChecksTests(unittest.TestCase):
    def test_real_analyzer_flags_skip_disabled_checks_and_llm(self):
        from analyzers.text_analyzer import TextAnalyzer

        analyzer = TextAnalyzer()
        with patch.object(analyzer, "_statistical_analysis", return_value={}) as ai, \
                patch.object(analyzer, "_scam_pattern_detection") as scam, \
                patch.object(analyzer, "_llm_analysis") as llm:
            analyzer.analyze("Some sufficiently long text.", check_ai_generated=False, use_llm=False)
            ai.assert_not_called()
            scam.assert_called_once()
            scam.reset_mock()
            analyzer.analyze("Some sufficiently long text.", check_scam=False, use_llm=False)
            ai.assert_called_once()
            scam.assert_not_called()
            llm.assert_not_called()

    def test_ocr_does_not_treat_binary_metadata_as_visible_text(self):
        from analyzers.ocr_engine import ocr_engine

        with patch.object(ocr_engine, "tesseract_available", False):
            self.assertIsNone(ocr_engine.extract_text(b"This metadata contains a false factual claim."))


if __name__ == "__main__":
    unittest.main()
