import re
from typing import List, Tuple
from models.schemas import AnalysisDetail, RiskLevel


class RAGVerifier:
    """
    RAG-backed claim verification engine.
    Verifies extracted claims against a built-in knowledge base of trusted facts.
    In production, this would connect to a vector database + LLM.
    """

    # Built-in knowledge base of common claims and their verification status
    KNOWLEDGE_BASE = {
        # Health misinformation
        "5g causes": {"verdict": "FALSE", "source": "WHO", "explanation": "5G technology does not cause COVID-19 or other diseases. This has been debunked by multiple health organizations."},
        "vaccines cause autism": {"verdict": "FALSE", "source": "CDC, WHO", "explanation": "Extensive research has found no link between vaccines and autism. The original study was retracted."},
        "drinking bleach": {"verdict": "FALSE", "source": "FDA", "explanation": "Drinking bleach or disinfectant is extremely dangerous and does not cure any disease."},
        "essential oils cure": {"verdict": "MISLEADING", "source": "NIH", "explanation": "Essential oils have some therapeutic properties but cannot cure serious diseases."},
        "flat earth": {"verdict": "FALSE", "source": "NASA, scientific consensus", "explanation": "The Earth is an oblate spheroid, confirmed by centuries of scientific observation."},
        
        # Financial scams
        "guaranteed returns": {"verdict": "SCAM INDICATOR", "source": "SEC", "explanation": "No legitimate investment guarantees returns. This is a common fraud tactic."},
        "double your money": {"verdict": "SCAM INDICATOR", "source": "FTC", "explanation": "Promises to double your money quickly are almost always scams."},
        "nigerian prince": {"verdict": "SCAM", "source": "FBI IC3", "explanation": "Classic advance-fee fraud scheme targeting victims worldwide."},
        "lottery winner": {"verdict": "SCAM INDICATOR", "source": "FTC", "explanation": "Unsolicited lottery winning notifications are fraudulent. You cannot win a lottery you didn't enter."},
        
        # Technology misinformation  
        "phone charger explosion": {"verdict": "PARTIALLY TRUE", "source": "Consumer Reports", "explanation": "While rare, using non-certified chargers can pose safety risks."},
        "airplane mode radiation": {"verdict": "MISLEADING", "source": "FCC", "explanation": "Phones emit non-ionizing radiation at levels well within safety standards."},
    }

    # Claim extraction patterns
    CLAIM_PATTERNS = [
        r'(?:studies?\s+(?:show|prove|found|reveal))\s+(?:that\s+)?(.+?)(?:\.|$)',
        r'(?:according\s+to\s+\w+)\s*,?\s*(.+?)(?:\.|$)',
        r'(?:it\s+(?:is|has been)\s+(?:proven|confirmed|shown))\s+(?:that\s+)?(.+?)(?:\.|$)',
        r'(?:scientists?\s+(?:say|confirm|discover))\s+(?:that\s+)?(.+?)(?:\.|$)',
        r'(?:research\s+(?:shows|proves|indicates))\s+(?:that\s+)?(.+?)(?:\.|$)',
        r'(?:experts?\s+(?:say|warn|confirm))\s+(?:that\s+)?(.+?)(?:\.|$)',
    ]

    def verify_claims(self, text: str) -> Tuple[List[AnalysisDetail], dict]:
        """
        Extract and verify claims from text.
        Returns (details, extra_context).
        """
        details = []
        text_lower = text.lower()
        claims_found = 0
        claims_flagged = 0

        # Check against knowledge base
        for trigger, info in self.KNOWLEDGE_BASE.items():
            if trigger in text_lower:
                claims_found += 1
                verdict = info["verdict"]

                if verdict in ["FALSE", "SCAM", "SCAM INDICATOR"]:
                    claims_flagged += 1
                    severity = RiskLevel.CRITICAL if verdict in ["FALSE", "SCAM"] else RiskLevel.HIGH
                    confidence = 0.9 if verdict in ["FALSE", "SCAM"] else 0.75
                elif verdict == "MISLEADING":
                    claims_flagged += 1
                    severity = RiskLevel.HIGH
                    confidence = 0.7
                else:
                    severity = RiskLevel.MEDIUM
                    confidence = 0.5

                details.append(AnalysisDetail(
                    category="Claim Verification",
                    finding=f"Claim matched: '{trigger}' → {verdict} (Source: {info['source']}). {info['explanation']}",
                    confidence=confidence,
                    severity=severity
                ))

        # Try to extract and flag unverified claims
        extracted_claims = self._extract_claims(text)
        for claim in extracted_claims:
            if not any(trigger in claim.lower() for trigger in self.KNOWLEDGE_BASE):
                claims_found += 1
                details.append(AnalysisDetail(
                    category="Claim Verification",
                    finding=f"Unverified claim detected: '{claim[:80]}...' — could not be verified against trusted sources",
                    confidence=0.3,
                    severity=RiskLevel.MEDIUM
                ))

        extra_context = {
            "claims_found": claims_found,
            "claims_flagged": claims_flagged,
            "claims_verified": claims_found - claims_flagged,
        }

        return details, extra_context

    def _extract_claims(self, text: str) -> list:
        """Extract factual claims from text using regex patterns."""
        claims = []
        for pattern in self.CLAIM_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            claims.extend(matches)
        # Deduplicate and limit
        seen = set()
        unique_claims = []
        for claim in claims:
            claim_clean = claim.strip().lower()
            if claim_clean not in seen and len(claim_clean) > 10:
                seen.add(claim_clean)
                unique_claims.append(claim.strip())
        return unique_claims[:10]


rag_verifier = RAGVerifier()
