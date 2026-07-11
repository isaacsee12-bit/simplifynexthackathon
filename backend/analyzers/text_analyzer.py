import json
import re
import math
from collections import Counter
from typing import List, Tuple
from models.schemas import AnalysisDetail, RiskLevel
from core.groq_client import groq_client


class TextAnalyzer:
    """
    Production-grade text forensic analyzer:
    1. Statistical text analysis (perplexity proxy, burstiness, TTR, sentence variance)
    2. LLM-based analysis with Groq (upgraded model)
    3. Scam/phishing pattern detection
    4. AI-writing pattern detection
    """

    def analyze(self, text: str) -> Tuple[List[AnalysisDetail], dict]:
        details = []
        text_length = len(text)
        word_count = len(text.split())

        if text_length < 10:
            details.append(AnalysisDetail(
                category="AI Generation",
                finding="Text too short for comprehensive analysis",
                confidence=0.1,
                severity=RiskLevel.LOW
            ))
            return details, {"text_length": text_length, "word_count": word_count}

        # 1. Statistical text analysis (pre-LLM signals)
        stats = self._statistical_analysis(text, details)

        # 2. Pattern-based scam/phishing detection
        self._scam_pattern_detection(text, details)

        # 3. LLM-based deep analysis
        if groq_client:
            self._llm_analysis(text, details, stats)
        else:
            details.append(AnalysisDetail(
                category="System Error",
                finding="Groq API key not configured. LLM-based text analysis unavailable.",
                confidence=1.0,
                severity=RiskLevel.CRITICAL
            ))

        extra_context = {
            "text_length": text_length,
            "word_count": word_count,
            **stats
        }

        return details, extra_context

    # ─── Statistical Text Analysis ───────────────────────────────────────
    def _statistical_analysis(self, text: str, details: List[AnalysisDetail]) -> dict:
        """
        Compute statistical features that distinguish AI text from human text.
        """
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        stats = {
            "ai_score": 0.0,
            "scam_score": 0.0,
            "misinfo_score": 0.0,
        }

        if len(words) < 5:
            return stats

        # --- Type-Token Ratio (Vocabulary Richness) ---
        word_lower = [w.lower().strip('.,!?;:"\'()[]{}') for w in words]
        word_lower = [w for w in word_lower if w]
        unique_words = set(word_lower)
        ttr = len(unique_words) / len(word_lower) if word_lower else 0

        # AI text tends to have moderate TTR (not too high, not too low)
        # Human text often has higher variance in TTR

        # --- Sentence Length Variance ---
        if len(sentences) >= 3:
            sent_lengths = [len(s.split()) for s in sentences]
            sent_mean = sum(sent_lengths) / len(sent_lengths)
            sent_std = (sum((l - sent_mean) ** 2 for l in sent_lengths) / len(sent_lengths)) ** 0.5
            sent_cv = sent_std / sent_mean if sent_mean > 0 else 0

            stats["sentence_length_cv"] = round(sent_cv, 3)

            # AI text tends to have very uniform sentence lengths
            if sent_cv < 0.25 and len(sentences) >= 5:
                details.append(AnalysisDetail(
                    category="AI Generation",
                    finding=f"Sentence length is unusually uniform (CV={sent_cv:.3f}) — AI-generated text often has consistent sentence structure",
                    confidence=min(0.65, 0.3 + (0.25 - sent_cv) * 2),
                    severity=RiskLevel.MEDIUM
                ))

        # --- Burstiness Analysis ---
        # Human writing is "bursty" — repeats certain words in clusters
        # AI writing distributes vocabulary more evenly
        if len(word_lower) >= 30:
            word_freq = Counter(word_lower)
            common_words = [w for w, c in word_freq.most_common(10) if c >= 3 and len(w) > 3]

            if common_words:
                burstiness_scores = []
                for word in common_words[:5]:
                    positions = [i for i, w in enumerate(word_lower) if w == word]
                    if len(positions) >= 2:
                        gaps = [positions[i+1] - positions[i] for i in range(len(positions)-1)]
                        gap_mean = sum(gaps) / len(gaps)
                        gap_std = (sum((g - gap_mean) ** 2 for g in gaps) / len(gaps)) ** 0.5 if len(gaps) > 1 else 0
                        burstiness = gap_std / gap_mean if gap_mean > 0 else 0
                        burstiness_scores.append(burstiness)

                if burstiness_scores:
                    avg_burstiness = sum(burstiness_scores) / len(burstiness_scores)
                    stats["burstiness"] = round(avg_burstiness, 3)

                    # Low burstiness = words evenly distributed = AI-like
                    if avg_burstiness < 0.3 and len(word_lower) > 50:
                        details.append(AnalysisDetail(
                            category="AI Generation",
                            finding=f"Low lexical burstiness ({avg_burstiness:.3f}) — AI text distributes vocabulary too evenly compared to human writing",
                            confidence=min(0.6, 0.3 + (0.3 - avg_burstiness)),
                            severity=RiskLevel.MEDIUM
                        ))

        # --- Repetitive Phrase Patterns ---
        # AI often uses certain connector phrases excessively
        ai_connectors = [
            'in conclusion', 'it is important to note', 'furthermore',
            'in today\'s world', 'in the realm of', 'it is worth noting',
            'on the other hand', 'in this regard', 'to sum up',
            'as we delve', 'it is crucial', 'in essence',
            'a testament to', 'navigating the', 'in the ever-evolving',
            'leveraging', 'holistic', 'synergy', 'paradigm shift',
            'cutting-edge', 'groundbreaking', 'revolutionary',
        ]
        text_lower = text.lower()
        ai_phrase_count = sum(1 for phrase in ai_connectors if phrase in text_lower)
        if ai_phrase_count >= 3:
            details.append(AnalysisDetail(
                category="AI Generation",
                finding=f"Multiple AI-typical phrases detected ({ai_phrase_count} matches) — text contains language patterns common in LLM output",
                confidence=min(0.75, 0.35 + ai_phrase_count * 0.1),
                severity=RiskLevel.HIGH
            ))
        elif ai_phrase_count >= 1 and len(words) < 200:
            details.append(AnalysisDetail(
                category="AI Generation",
                finding=f"AI-typical phrasing detected ({ai_phrase_count} matches) in relatively short text",
                confidence=0.35,
                severity=RiskLevel.MEDIUM
            ))

        stats["ttr"] = round(ttr, 3)
        stats["ai_phrase_count"] = ai_phrase_count
        return stats

    # ─── Scam/Phishing Pattern Detection ─────────────────────────────────
    def _scam_pattern_detection(self, text: str, details: List[AnalysisDetail]):
        """Rule-based scam/phishing detection."""
        text_lower = text.lower()

        # Urgency indicators
        urgency_phrases = [
            'act now', 'limited time', 'don\'t miss', 'expires soon',
            'immediate action', 'urgent', 'last chance', 'only today',
            'claim your', 'verify your account', 'confirm your identity',
            'suspend your account', 'unauthorized access',
        ]
        urgency_count = sum(1 for p in urgency_phrases if p in text_lower)

        # Money/credential requests
        money_phrases = [
            'send money', 'bank details', 'credit card', 'ssn',
            'social security', 'wire transfer', 'bitcoin', 'crypto',
            'password', 'login credentials', 'click here', 'click the link',
            'prize', 'winner', 'congratulations', 'you\'ve won',
            'inheritance', 'nigerian prince', 'beneficiary',
        ]
        money_count = sum(1 for p in money_phrases if p in text_lower)

        # Suspicious URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+|bit\.ly|tinyurl|t\.co'
        suspicious_urls = re.findall(url_pattern, text_lower)

        scam_score = 0
        if urgency_count >= 2:
            scam_score += 0.3
            details.append(AnalysisDetail(
                category="Scam Phishing",
                finding=f"Multiple urgency-inducing phrases detected ({urgency_count}) — classic social engineering tactic",
                confidence=min(0.8, 0.4 + urgency_count * 0.15),
                severity=RiskLevel.HIGH
            ))
        elif urgency_count == 1:
            scam_score += 0.1

        if money_count >= 2:
            scam_score += 0.4
            details.append(AnalysisDetail(
                category="Scam Phishing",
                finding=f"Multiple financial/credential request indicators ({money_count}) — likely phishing attempt",
                confidence=min(0.9, 0.5 + money_count * 0.15),
                severity=RiskLevel.CRITICAL
            ))
        elif money_count == 1:
            scam_score += 0.15

        if len(suspicious_urls) > 0 and (urgency_count > 0 or money_count > 0):
            details.append(AnalysisDetail(
                category="Scam Phishing",
                finding=f"Suspicious URLs found ({len(suspicious_urls)}) combined with urgency/financial language — high phishing risk",
                confidence=0.75,
                severity=RiskLevel.HIGH
            ))

    # ─── LLM Analysis ────────────────────────────────────────────────────
    def _llm_analysis(self, text: str, details: List[AnalysisDetail], stats: dict):
        """Use Groq LLM for deep text analysis."""
        prompt = f"""You are an expert AI content detection and fraud analysis system. Analyze the following text for:

1. **AI Generation Detection**: Does this text appear to be written by an LLM? Look for:
   - Overly uniform sentence structure and length
   - Generic filler phrases and hedging language
   - Lack of personal anecdotes, typos, or colloquialisms
   - Unnaturally smooth transitions and perfect grammar
   - Formulaic structure (intro → body → conclusion pattern)

2. **Scam/Phishing Detection**: Is this text attempting to deceive? Look for:
   - Urgency tactics, fear-mongering
   - Requests for personal info, credentials, or money
   - Impersonation of authority figures or organizations
   - Too-good-to-be-true offers
   - Suspicious links or call-to-action patterns

3. **Misinformation Detection**: Does this contain false or misleading claims?
   - Unsubstantiated dramatic claims presented as fact
   - Cherry-picked statistics or misrepresented data
   - Conspiracy theory language patterns
   - Clickbait or sensationalist framing
   - Claims that contradict established scientific consensus

Pre-computed statistics for reference:
- Type-Token Ratio: {stats.get('ttr', 'N/A')}
- Sentence Length CV: {stats.get('sentence_length_cv', 'N/A')}
- AI Phrase Count: {stats.get('ai_phrase_count', 'N/A')}
- Burstiness: {stats.get('burstiness', 'N/A')}

Output JSON format:
{{
  "details": [
    {{
      "category": "AI Generation" | "Scam Phishing" | "Manipulation",
      "finding": "Specific, evidence-based description of what you found",
      "confidence": (float 0.0 to 1.0 — be calibrated, not extreme),
      "severity": "low" | "medium" | "high" | "critical"
    }}
  ],
  "scores": {{
    "ai_score": (float 0.0 to 1.0),
    "scam_score": (float 0.0 to 1.0),
    "misinfo_score": (float 0.0 to 1.0)
  }}
}}

IMPORTANT: Be calibrated in your confidence scores. Don't give 0.9+ unless there's very strong evidence. Normal human-written text should get low scores.

Text to analyze:
\"\"\"
{text[:5000]}
\"\"\"
"""

        try:
            response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=1500,
            )

            result_json = json.loads(response.choices[0].message.content)

            for item in result_json.get("details", []):
                sev_str = item.get("severity", "low").lower()
                if sev_str == "critical":
                    severity = RiskLevel.CRITICAL
                elif sev_str == "high":
                    severity = RiskLevel.HIGH
                elif sev_str == "medium":
                    severity = RiskLevel.MEDIUM
                else:
                    severity = RiskLevel.LOW

                # Validate confidence is reasonable
                confidence = float(item.get("confidence", 0.0))
                confidence = max(0.0, min(1.0, confidence))

                details.append(AnalysisDetail(
                    category=item.get("category", "General"),
                    finding=item.get("finding", "No finding description provided."),
                    confidence=confidence,
                    severity=severity
                ))

            scores = result_json.get("scores", {})
            stats["ai_score"] = float(scores.get("ai_score", 0.0))
            stats["scam_score"] = float(scores.get("scam_score", 0.0))
            stats["misinfo_score"] = float(scores.get("misinfo_score", 0.0))

        except Exception as e:
            print(f"Groq API error during text analysis: {e}")
            details.append(AnalysisDetail(
                category="System Error",
                finding=f"LLM analysis error: {str(e)[:100]}",
                confidence=1.0,
                severity=RiskLevel.MEDIUM
            ))


text_analyzer = TextAnalyzer()
