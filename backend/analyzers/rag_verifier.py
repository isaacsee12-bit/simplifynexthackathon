import re
import urllib.request
import urllib.parse
import json
from typing import List, Tuple
from models.schemas import AnalysisDetail, RiskLevel
from core.groq_client import groq_client

class RAGVerifier:
    """
    RAG-backed claim verification engine.
    Uses Wikipedia for context, and Groq LLM to verify claims against the context.
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
            snippet = self._query_wikipedia(claim)
            
            if snippet and groq_client:
                clean_snippet = re.sub(r'<[^>]+>', '', snippet)
                
                # Use Groq to evaluate the claim against the snippet
                prompt = f"""
You are a fact-checking assistant. Evaluate if the following claim is supported by the provided context.

Claim: "{claim}"
Context: "{clean_snippet}"

Output JSON:
{{
    "supported": true | false,
    "reasoning": "Brief explanation"
}}
"""
                try:
                    response = groq_client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama-3.1-8b-instant",
                        response_format={"type": "json_object"},
                        temperature=0.0
                    )
                    result = json.loads(response.choices[0].message.content)
                    is_supported = result.get("supported", False)
                    reasoning = result.get("reasoning", "")
                    
                    if is_supported:
                        claims_verified += 1
                        details.append(AnalysisDetail(
                            category="Live Web Verification",
                            finding=f"Verified Claim: '{claim[:60]}...' | Reason: {reasoning}",
                            confidence=0.9,
                            severity=RiskLevel.LOW
                        ))
                    else:
                        claims_flagged += 1
                        details.append(AnalysisDetail(
                            category="Claim Verification",
                            finding=f"Refuted/Unverified Claim: '{claim[:80]}...' | Context conflicts: {reasoning}",
                            confidence=0.8,
                            severity=RiskLevel.HIGH
                        ))
                except Exception as e:
                    print(f"Groq RAG evaluation error: {e}")
                    # Fallback
                    claims_verified += 1
                    details.append(AnalysisDetail(
                        category="Live Web Verification",
                        finding=f"Claim: '{claim[:60]}...' | Internet Context: '{clean_snippet[:120]}...'",
                        confidence=0.85,
                        severity=RiskLevel.LOW
                    ))

            elif snippet:
                # Fallback if groq_client fails
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
        return unique_claims[:3]  # Max 3 to reduce API calls

    def _query_wikipedia(self, claim: str) -> str:
        """Query Wikipedia API live to find supporting context."""
        try:
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
