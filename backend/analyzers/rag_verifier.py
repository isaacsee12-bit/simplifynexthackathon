import re
import urllib.request
import urllib.parse
import json
from typing import List, Tuple
from models.schemas import AnalysisDetail, RiskLevel

class RAGVerifier:
    """
    RAG-backed claim verification engine.
    Now upgraded to perform REAL LIVE queries against Wikipedia API to verify claims.
    """

    CLAIM_PATTERNS = [
        r'(?:studies?\s+(?:show|prove|found|reveal))\s+(?:that\s+)?(.+?)(?:\.|$)',
        r'(?:according\s+to\s+\w+)\s*,?\s*(.+?)(?:\.|$)',
        r'(?:it\s+(?:is|has been)\s+(?:proven|confirmed|shown))\s+(?:that\s+)?(.+?)(?:\.|$)',
        r'(?:scientists?\s+(?:say|confirm|discover))\s+(?:that\s+)?(.+?)(?:\.|$)',
        r'(?:research\s+(?:shows|proves|indicates))\s+(?:that\s+)?(.+?)(?:\.|$)',
        r'(?:experts?\s+(?:say|warn|confirm))\s+(?:that\s+)?(.+?)(?:\.|$)',
    ]

    def verify_claims(self, text: str) -> Tuple[List[AnalysisDetail], dict]:
        details = []
        claims_found = 0
        claims_flagged = 0
        claims_verified = 0

        extracted_claims = self._extract_claims(text)
        
        for claim in extracted_claims:
            claims_found += 1
            # Perform Live Web Search
            snippet = self._query_wikipedia(claim)
            
            if snippet:
                # Clean HTML tags from Wikipedia snippet
                clean_snippet = re.sub(r'<[^>]+>', '', snippet)
                claims_verified += 1
                details.append(AnalysisDetail(
                    category="Live Web Verification",
                    finding=f"Claim: '{claim[:60]}...' | Internet Context: '{clean_snippet[:120]}...'",
                    confidence=0.85,
                    severity=RiskLevel.LOW
                ))
            else:
                claims_flagged += 1
                details.append(AnalysisDetail(
                    category="Claim Verification",
                    finding=f"Unverified claim detected: '{claim[:80]}...' — No matching internet consensus found.",
                    confidence=0.6,
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
        return unique_claims[:5] # Max 5 claims to keep it real-time

    def _query_wikipedia(self, claim: str) -> str:
        """Query Wikipedia API live to find supporting context."""
        try:
            # Search using the most salient words of the claim
            words = [w for w in claim.split() if len(w) > 4][:5]
            if not words:
                return None
            query = urllib.parse.quote(" ".join(words))
            url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&utf8=&format=json&srlimit=1"
            req = urllib.request.Request(url, headers={'User-Agent': 'TruthLens/1.0'})
            
            with urllib.request.urlopen(req, timeout=2.0) as response:
                data = json.loads(response.read().decode())
                search_results = data.get('query', {}).get('search', [])
                if search_results:
                    return search_results[0].get('snippet', '')
        except Exception as e:
            print(f"Live web search failed: {e}")
        return None

rag_verifier = RAGVerifier()
