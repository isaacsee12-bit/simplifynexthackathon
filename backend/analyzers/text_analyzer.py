import re
from typing import List, Tuple
from models.schemas import AnalysisDetail, RiskLevel

try:
    from transformers import pipeline
    print("Loading HuggingFace RoBERTa AI Detector model... This may take a moment.")
    ai_detector = pipeline("text-classification", model="roberta-base-openai-detector", device=-1)
except ImportError:
    ai_detector = None
    print("Transformers not installed. Falling back to heuristics.")
except Exception as e:
    ai_detector = None
    print(f"Error loading HuggingFace model: {e}. Falling back to heuristics.")


class TextAnalyzer:
    """
    Analyzes text content for:
    - AI-generated text patterns (via Neural Networks)
    - Scam/phishing indicators
    - Misinformation markers
    """

    AI_PATTERNS = [
        (r'\b(as an ai|as a language model|i cannot|i\'m an ai)\b', "AI self-reference detected", 0.95),
        (r'\b(delve|tapestry|multifaceted|comprehensive|leverag(e|ing)|synerg)\b', "Overused AI vocabulary", 0.4),
        (r'\b(in conclusion|to summarize|it\'s worth noting|it is important to note)\b', "Formulaic AI phrasing", 0.35),
        (r'\b(furthermore|moreover|additionally|consequently)\b', "Excessive formal connectors", 0.25),
    ]

    SCAM_PATTERNS = [
        (r'\b(urgent|act now|limited time|expire|hurry)\b', "Urgency pressure tactic", 0.7),
        (r'\b(congratulations|you\'ve won|claim your|free gift|winner)\b', "Prize/reward bait", 0.85),
        (r'\b(verify your (account|identity|password)|confirm your|update your payment)\b', "Credential phishing attempt", 0.9),
        (r'\b(click (here|this link|below)|follow this link)\b', "Suspicious link prompt", 0.6),
        (r'\b(wire transfer|western union|bitcoin|crypto wallet|gift card)\b', "Suspicious payment method", 0.8),
        (r'\b(nigerian|prince|inheritance|beneficiary|estate)\b', "Advance-fee fraud markers", 0.9),
        (r'\b(irs|social security|arrest warrant|legal action)\b', "Government impersonation", 0.85),
        (r'\b(password|ssn|social security number|credit card number|bank account)\b', "Sensitive data request", 0.75),
        (r'(https?://[^\s]+(?:bit\.ly|tinyurl|t\.co|goo\.gl|short))', "Shortened/suspicious URL", 0.65),
    ]

    MISINFO_PATTERNS = [
        (r'\b(they don\'t want you to know|the truth is being hidden|cover.?up|conspiracy)\b', "Conspiracy language", 0.6),
        (r'\b(100% (proven|guaranteed|effective)|miracle cure|scientists hate)\b', "Clickbait/sensationalism", 0.7),
        (r'\b(wake up|sheeple|mainstream media lies|fake news)\b', "Inflammatory rhetoric", 0.55),
    ]

    def analyze(self, text: str) -> Tuple[List[AnalysisDetail], dict]:
        details = []
        text_lower = text.lower()
        text_length = len(text)

        if text_length < 10:
            details.append(AnalysisDetail(
                category="AI Generation",
                finding="Text too short for comprehensive analysis",
                confidence=0.1,
                severity=RiskLevel.LOW
            ))
            return details, {"text_length": text_length}

        ai_score = 0
        if ai_detector:
            try:
                result = ai_detector(text[:2000])[0]
                if result['label'] == 'Fake' and result['score'] > 0.6:
                    confidence = result['score']
                    ai_score = confidence
                    severity = RiskLevel.CRITICAL if confidence > 0.9 else RiskLevel.HIGH if confidence > 0.75 else RiskLevel.MEDIUM
                    details.append(AnalysisDetail(
                        category="AI Generation (Neural Net)",
                        finding=f"Deep Learning model detected synthetic text patterns",
                        confidence=round(confidence, 2),
                        severity=severity
                    ))
            except Exception as e:
                print(f"Model inference error: {e}")
                
        if ai_score == 0:
            ai_score = self._check_patterns(text_lower, self.AI_PATTERNS, "AI Generation (Heuristic)", details)

        scam_score = self._check_patterns(text_lower, self.SCAM_PATTERNS, "Scam Phishing", details)
        misinfo_score = self._check_patterns(text_lower, self.MISINFO_PATTERNS, "Manipulation", details)

        extra_context = {
            "text_length": text_length,
            "word_count": len(text.split()),
            "ai_score": ai_score,
            "scam_score": scam_score,
            "misinfo_score": misinfo_score,
        }

        return details, extra_context

    def _check_patterns(self, text: str, patterns: list, category: str, details: List[AnalysisDetail]) -> float:
        total_confidence = 0
        match_count = 0
        for pattern, description, confidence in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                match_count += 1
                adjusted_confidence = min(confidence + (len(matches) - 1) * 0.05, 0.99)
                total_confidence += adjusted_confidence
                severity = (
                    RiskLevel.CRITICAL if adjusted_confidence >= 0.85
                    else RiskLevel.HIGH if adjusted_confidence >= 0.65
                    else RiskLevel.MEDIUM if adjusted_confidence >= 0.4
                    else RiskLevel.LOW
                )
                details.append(AnalysisDetail(
                    category=category,
                    finding=f"{description} ({len(matches)} occurrence{'s' if len(matches) > 1 else ''})",
                    confidence=round(adjusted_confidence, 2),
                    severity=severity
                ))
        return total_confidence / max(match_count, 1)

text_analyzer = TextAnalyzer()
