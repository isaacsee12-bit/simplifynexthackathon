import re
import urllib.request
import urllib.parse
import json
from typing import List, Tuple
from models.schemas import AnalysisDetail, RiskLevel
from core.gemini_client import gemini_client
from google.genai import types
from core.config import settings


class RAGVerifier:
    """
    RAG-backed claim verification engine.
    Uses Wikipedia + DuckDuckGo for context, and Gemini to verify claims.
    """

    CLAIM_PATTERNS = [
        r'(?:studies?\s+(?:show|prove|found|reveal))\s+(?:that\s+)?(.+?)(?:\.|$)',
        r'(?:according\s+to\s+\w+)\s*,?\s*(.+?)(?:\.|$)',
        r'(?:it\s+(?:is|has been)\s+(?:proven|confirmed|shown))\s+(?:that\s+)?(.+?)(?:\.|$)',
        r'(?:scientists?\s+(?:say|confirm|discover))\s+(?:that\s+)?(.+?)(?:\.|$)',
        r'(?:research\s+(?:shows|proves|indicates))\s+(?:that\s+)?(.+?)(?:\.|$)',
        r'(?:experts?\s+(?:say|warn|confirm))\s+(?:that\s+)?(.+?)(?:\.|$)',
        r'(?:reports?\s+(?:show|indicate|suggest))\s+(?:that\s+)?(.+?)(?:\.|$)',
        r'(?:data\s+(?:shows|proves|reveals))\s+(?:that\s+)?(.+?)(?:\.|$)',
        r'(?:(?:new|recent)\s+(?:study|research|findings?))\s+(?:that\s+)?(.+?)(?:\.|$)',
    ]

    def verify_claims(self, text: str) -> Tuple[List[AnalysisDetail], dict]:
        details = []
        claims_found = 0
        claims_flagged = 0
        claims_verified = 0

        extracted_claims = self._extract_claims(text)

        for claim in extracted_claims:
            claims_found += 1

            # Try Wikipedia first
            snippet = self._query_wikipedia(claim)

            # Fallback to DuckDuckGo if Wikipedia has no results
            if not snippet:
                snippet = self._query_duckduckgo(claim)

            if snippet and gemini_client:
                clean_snippet = re.sub(r'<[^>]+>', '', snippet)

                prompt = f"""You are a fact-checking assistant. Evaluate if the following claim is supported, refuted, or uncertain based on the provided context.

Claim: "{claim}"
Context: "{clean_snippet[:1000]}"

Output JSON:
{{
    "verdict": "supported" | "refuted" | "uncertain",
    "reasoning": "Brief, specific explanation citing evidence from context"
}}

Be rigorous: if the context doesn't directly address the claim, use "uncertain" not "supported".
"""
                try:
                    response = gemini_client.models.generate_content(
                        contents=prompt,
                        model=settings.GEMINI_MODEL,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.0,
                            max_output_tokens=300,
                        ),
                    )
                    result = json.loads(response.text)
                    verdict = result.get("verdict", "uncertain").lower()
                    reasoning = result.get("reasoning", "")

                    if verdict == "supported":
                        claims_verified += 1
                        details.append(AnalysisDetail(
                            category="Live Web Verification",
                            finding=f"✓ Verified: '{claim[:60]}...' — {reasoning[:120]}",
                            confidence=0.85,
                            severity=RiskLevel.LOW
                        ))
                    elif verdict == "refuted":
                        claims_flagged += 1
                        details.append(AnalysisDetail(
                            category="Claim Verification",
                            finding=f"✗ Refuted: '{claim[:80]}...' — {reasoning[:120]}",
                            confidence=0.8,
                            severity=RiskLevel.HIGH
                        ))
                    else:
                        details.append(AnalysisDetail(
                            category="Claim Verification",
                            finding=f"? Uncertain: '{claim[:80]}...' — {reasoning[:120]}",
                            confidence=0.5,
                            severity=RiskLevel.MEDIUM
                        ))
                except Exception as e:
                    print(f"Gemini RAG evaluation error: {type(e).__name__}")
                    details.append(AnalysisDetail(
                        category="Live Web Verification",
                        finding=f"Claim unverified (Gemini unavailable): '{claim[:60]}...' | Context found: '{clean_snippet[:120]}...'",
                        confidence=0.6,
                        severity=RiskLevel.LOW
                    ))

            elif snippet:
                clean_snippet = re.sub(r'<[^>]+>', '', snippet)
                details.append(AnalysisDetail(
                    category="Live Web Verification",
                    finding=f"Claim unverified (Gemini not configured): '{claim[:60]}...' | Internet Context: '{clean_snippet[:120]}...'",
                    confidence=0.6,
                    severity=RiskLevel.LOW
                ))
            else:
                claims_flagged += 1
                details.append(AnalysisDetail(
                    category="Claim Verification",
                    finding=f"⚠ Unverifiable: '{claim[:80]}...' — No matching internet consensus found",
                    confidence=0.55,
                    severity=RiskLevel.MEDIUM
                ))

        extra_context = {
            "claims_found": claims_found,
            "claims_flagged": claims_flagged,
            "claims_verified": claims_verified,
        }

        return details, extra_context

    def _extract_claims(self, text: str) -> list:
        claims = []
        for pattern in self.CLAIM_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            claims.extend(matches)

        seen = set()
        unique_claims = []
        for claim in claims:
            claim_clean = claim.strip().lower()
            if claim_clean not in seen and len(claim_clean) > 10:
                seen.add(claim_clean)
                unique_claims.append(claim.strip())
        return unique_claims[:5]  # Up to 5 claims

    def _query_wikipedia(self, claim: str) -> str:
        """Query Wikipedia API live to find supporting context."""
        try:
            words = [w for w in claim.split() if len(w) > 4][:5]
            if not words:
                return None
            query = urllib.parse.quote(" ".join(words))
            url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&utf8=&format=json&srlimit=1"
            req = urllib.request.Request(url, headers={'User-Agent': 'VerifyAI/2.0'})

            with urllib.request.urlopen(req, timeout=3.0) as response:
                data = json.loads(response.read().decode())
                search_results = data.get('query', {}).get('search', [])
                if search_results:
                    return search_results[0].get('snippet', '')
        except Exception as e:
            print(f"Wikipedia search failed: {e}")
        return None

    def _query_duckduckgo(self, claim: str) -> str:
        """Fallback: query DuckDuckGo Instant Answer API for context."""
        try:
            words = [w for w in claim.split() if len(w) > 3][:6]
            if not words:
                return None
            query = urllib.parse.quote(" ".join(words))
            url = f"https://api.duckduckgo.com/?q={query}&format=json&no_redirect=1&no_html=1"
            req = urllib.request.Request(url, headers={'User-Agent': 'VerifyAI/2.0'})

            with urllib.request.urlopen(req, timeout=3.0) as response:
                data = json.loads(response.read().decode())
                # Check Abstract, AbstractText, or RelatedTopics
                abstract = data.get('AbstractText', '')
                if abstract and len(abstract) > 30:
                    return abstract

                # Try related topics
                related = data.get('RelatedTopics', [])
                if related and isinstance(related[0], dict):
                    return related[0].get('Text', '')
        except Exception as e:
            print(f"DuckDuckGo search failed: {e}")
        return None


rag_verifier = RAGVerifier()
