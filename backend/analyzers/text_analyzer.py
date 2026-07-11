import json
from typing import List, Tuple
from models.schemas import AnalysisDetail, RiskLevel
from core.groq_client import groq_client

class TextAnalyzer:
    """
    Analyzes text content for AI generation, scams, and misinformation using Groq LLM.
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

        if not groq_client:
            details.append(AnalysisDetail(
                category="System Error",
                finding="Groq API key not configured. Text analysis unavailable.",
                confidence=1.0,
                severity=RiskLevel.CRITICAL
            ))
            return details, {"text_length": text_length, "word_count": word_count}

        prompt = f"""
You are an expert AI and fraud detection system. Analyze the following text for:
1. AI Generation (Does it sound like an LLM? Overly formal, formulaic, specific buzzwords?)
2. Scam/Phishing (Urgency, requests for money/credentials, suspicious links?)
3. Misinformation (Clickbait, conspiracy theories, unsubstantiated dramatic claims?)

Output your analysis in JSON format with the following structure:
{{
  "details": [
    {{
      "category": "AI Generation" | "Scam Phishing" | "Manipulation",
      "finding": "Short description of what you found and why",
      "confidence": (float between 0.0 and 1.0),
      "severity": "low" | "medium" | "high" | "critical"
    }}
  ],
  "scores": {{
    "ai_score": (float 0.0 to 1.0),
    "scam_score": (float 0.0 to 1.0),
    "misinfo_score": (float 0.0 to 1.0)
  }}
}}

Text to analyze:
\"\"\"
{text[:4000]}
\"\"\"
"""
        
        try:
            response = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.1-8b-instant",
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            result_json = json.loads(response.choices[0].message.content)
            
            for item in result_json.get("details", []):
                sev_str = item.get("severity", "low").lower()
                if sev_str == "critical": severity = RiskLevel.CRITICAL
                elif sev_str == "high": severity = RiskLevel.HIGH
                elif sev_str == "medium": severity = RiskLevel.MEDIUM
                else: severity = RiskLevel.LOW
                
                details.append(AnalysisDetail(
                    category=item.get("category", "General"),
                    finding=item.get("finding", "No finding description provided."),
                    confidence=float(item.get("confidence", 0.0)),
                    severity=severity
                ))
            
            scores = result_json.get("scores", {})
            extra_context = {
                "text_length": text_length,
                "word_count": word_count,
                "ai_score": float(scores.get("ai_score", 0.0)),
                "scam_score": float(scores.get("scam_score", 0.0)),
                "misinfo_score": float(scores.get("misinfo_score", 0.0)),
            }
            
        except Exception as e:
            print(f"Groq API error during text analysis: {e}")
            details.append(AnalysisDetail(
                category="System Error",
                finding=f"Groq API error: {str(e)}",
                confidence=1.0,
                severity=RiskLevel.MEDIUM
            ))
            extra_context = {
                "text_length": text_length,
                "word_count": word_count,
                "ai_score": 0.0,
                "scam_score": 0.0,
                "misinfo_score": 0.0,
            }

        return details, extra_context

text_analyzer = TextAnalyzer()
