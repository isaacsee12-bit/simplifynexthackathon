import re
import hashlib
from typing import List, Tuple
from models.schemas import AnalysisDetail, RiskLevel


class TextAnalyzer:
    """
    Analyzes text content for:
    - AI-generated text patterns
    - Scam/phishing indicators
    - Suspicious language patterns
    - Misinformation markers
    """

    # Common AI-generated text markers
    AI_PATTERNS = [
        (r'\b(as an ai|as a language model|i cannot|i\'m an ai)\b', "AI self-reference detected", 0.95),
        (r'\b(delve|tapestry|multifaceted|comprehensive|leverag(e|ing)|synerg)\b', "Overused AI vocabulary", 0.4),
        (r'\b(in conclusion|to summarize|it\'s worth noting|it is important to note)\b', "Formulaic AI phrasing", 0.35),
        (r'\b(furthermore|moreover|additionally|consequently)\b', "Excessive formal connectors", 0.25),
        (r'(\w+ly,\s){3,}', "Excessive adverb chains (AI pattern)", 0.5),
    ]

    # Scam/phishing patterns
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

    # Misinformation markers
    MISINFO_PATTERNS = [
        (r'\b(they don\'t want you to know|the truth is being hidden|cover.?up|conspiracy)\b', "Conspiracy language", 0.6),
        (r'\b(100% (proven|guaranteed|effective)|miracle cure|scientists hate)\b', "Clickbait/sensationalism", 0.7),
        (r'\b(wake up|sheeple|mainstream media lies|fake news)\b', "Inflammatory rhetoric", 0.55),
        (r'\b(breaking|exclusive|shocking|unbelievable)\b', "Sensational language", 0.4),
    ]

    def analyze(self, text: str) -> Tuple[List[AnalysisDetail], dict]:
        """
        Analyze text content and return findings.
        Returns (details, extra_context).
        """
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

        # Check AI-generated patterns
        ai_score = self._check_patterns(text_lower, self.AI_PATTERNS, "AI Generation", details)

        # Check scam/phishing patterns  
        scam_score = self._check_patterns(text_lower, self.SCAM_PATTERNS, "Scam Phishing", details)

        # Check misinformation
        misinfo_score = self._check_patterns(text_lower, self.MISINFO_PATTERNS, "Manipulation", details)

        # Analyze text statistics
        self._analyze_statistics(text, details)

        # Calculate repetition score (AI tends to be more repetitive)
        self._check_repetition(text, details)

        extra_context = {
            "text_length": text_length,
            "word_count": len(text.split()),
            "ai_score": ai_score,
            "scam_score": scam_score,
            "misinfo_score": misinfo_score,
        }

        return details, extra_context

    def _check_patterns(
        self, text: str, patterns: list, category: str, details: List[AnalysisDetail]
    ) -> float:
        """Check text against a list of regex patterns. Returns aggregate score."""
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

    def _analyze_statistics(self, text: str, details: List[AnalysisDetail]):
        """Analyze statistical properties of text."""
        words = text.split()
        if len(words) < 20:
            return

        # Average word length (AI text tends to use longer words)
        avg_word_len = sum(len(w) for w in words) / len(words)
        if avg_word_len > 6.5:
            details.append(AnalysisDetail(
                category="AI Generation",
                finding=f"Unusually high average word length ({avg_word_len:.1f} chars) — common in AI text",
                confidence=0.35,
                severity=RiskLevel.LOW
            ))

        # Sentence length uniformity (AI tends to produce uniform sentences)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        if len(sentences) >= 3:
            lengths = [len(s.split()) for s in sentences]
            avg_len = sum(lengths) / len(lengths)
            variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
            if variance < 10 and avg_len > 10:
                details.append(AnalysisDetail(
                    category="AI Generation",
                    finding=f"Very uniform sentence lengths (variance: {variance:.1f}) — typical of AI-generated text",
                    confidence=0.45,
                    severity=RiskLevel.MEDIUM
                ))

    def _check_repetition(self, text: str, details: List[AnalysisDetail]):
        """Check for unusual repetition patterns."""
        words = text.lower().split()
        if len(words) < 30:
            return

        # Check for repeated phrases (3-grams)
        trigrams = [' '.join(words[i:i+3]) for i in range(len(words)-2)]
        trigram_counts = {}
        for tg in trigrams:
            trigram_counts[tg] = trigram_counts.get(tg, 0) + 1

        repeated = {k: v for k, v in trigram_counts.items() if v > 2}
        if len(repeated) > 3:
            details.append(AnalysisDetail(
                category="AI Generation",
                finding=f"High phrase repetition detected ({len(repeated)} repeated 3-word phrases)",
                confidence=0.5,
                severity=RiskLevel.MEDIUM
            ))


text_analyzer = TextAnalyzer()
