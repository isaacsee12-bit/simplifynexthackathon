from models.schemas import RiskLevel, AnalysisDetail
from typing import List, Tuple


class TrustScoreEngine:
    """
    Aggregates individual analyzer scores into a unified trust score.
    Assigns risk level and generates human-readable explanations.
    """

    # Weight each analysis category
    CATEGORY_WEIGHTS = {
        "deepfake_detection": 0.30,
        "ai_generation": 0.25,
        "manipulation": 0.20,
        "scam_phishing": 0.15,
        "claim_verification": 0.10,
    }

    @staticmethod
    def calculate_trust_score(details: List[AnalysisDetail]) -> float:
        """
        Calculate overall trust score (0-100) from individual findings.
        Higher score = MORE manipulated/anomalous (used as risk score).
        """
        if not details:
            return 0.0  # Clean/Authentic if no anomalies detected

        # Multipliers based on severity
        severity_multipliers = {
            RiskLevel.LOW: 0.1,
            RiskLevel.MEDIUM: 0.4,
            RiskLevel.HIGH: 0.8,
            RiskLevel.CRITICAL: 1.0
        }

        total_weight = 0
        weighted_score = 0

        for detail in details:
            category = detail.category.lower().replace(" ", "_")
            weight = TrustScoreEngine.CATEGORY_WEIGHTS.get(category, 0.15)
            
            # Map severity, defaulting to LOW if not found
            mult = severity_multipliers.get(detail.severity, 0.1)
            detail_risk = detail.confidence * mult * 100
            
            weighted_score += detail_risk * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        raw_score = weighted_score / total_weight
        # Clamp between 0 and 100
        return round(max(0, min(100, raw_score)), 1)

    @staticmethod
    def determine_risk_level(trust_score: float, details: List[AnalysisDetail]) -> RiskLevel:
        """Determine risk level based on trust score and findings."""
        critical_findings = sum(1 for d in details if d.severity == RiskLevel.CRITICAL)
        high_findings = sum(1 for d in details if d.severity == RiskLevel.HIGH)

        if critical_findings > 0 or trust_score >= 85:
            return RiskLevel.CRITICAL
        elif high_findings > 0 or trust_score >= 65:
            return RiskLevel.HIGH
        elif trust_score >= 40:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    @staticmethod
    def determine_authenticity(trust_score: float, risk_level: RiskLevel) -> bool:
        """Determine if content appears authentic."""
        return trust_score < 40 and risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]

    @staticmethod
    def generate_explanation(
        content_type: str,
        trust_score: float,
        risk_level: RiskLevel,
        details: List[AnalysisDetail],
        extra_context: dict = None
    ) -> Tuple[str, str]:
        """
        Generate summary and detailed explanation.
        Returns (summary, full_explanation).
        """
        extra_context = extra_context or {}

        # Summary line
        if risk_level == RiskLevel.CRITICAL:
            summary = f"⚠️ CRITICAL: This {content_type} shows strong signs of manipulation or deception."
        elif risk_level == RiskLevel.HIGH:
            summary = f"🔴 HIGH RISK: This {content_type} contains elements that appear manipulated or AI-generated."
        elif risk_level == RiskLevel.MEDIUM:
            summary = f"🟡 MODERATE: This {content_type} has some suspicious indicators worth reviewing."
        else:
            summary = f"🟢 LOW RISK: This {content_type} appears largely authentic."

        # Build detailed explanation
        explanation_parts = []
        explanation_parts.append(f"My analysis indicates that your {content_type} {'contains manipulated elements' if trust_score >= 50 else 'appears largely authentic'}.")
        explanation_parts.append("")
        explanation_parts.append(f"Here's what my analysis of your {content_type} revealed:")
        explanation_parts.append("")

        # Add video-specific context
        if content_type == "video" and extra_context:
            total_frames = extra_context.get("total_frames", 0)
            deepfake_frames = extra_context.get("deepfake_frames", 0)
            if total_frames > 0:
                explanation_parts.append(
                    f"The video you submitted appears to contain deepfake elements."
                )
                explanation_parts.append(
                    f"Out of {total_frames} total frames, {deepfake_frames} frames were identified as potentially being deepfakes."
                )
                if deepfake_frames / total_frames > 0.8:
                    explanation_parts.append(
                        "This suggests that the video may have been altered or manipulated using AI techniques."
                    )
                    explanation_parts.append(
                        "While it wasn't flagged as an entirely AI-generated video, the significant presence of deepfake frames is noteworthy."
                    )
                explanation_parts.append("")

        # Add each finding
        for detail in details:
            severity_icon = {
                RiskLevel.LOW: "✅",
                RiskLevel.MEDIUM: "⚡",
                RiskLevel.HIGH: "🔴",
                RiskLevel.CRITICAL: "⚠️",
            }.get(detail.severity, "•")
            explanation_parts.append(
                f"{severity_icon} [{detail.category}] {detail.finding} (confidence: {detail.confidence:.0%})"
            )

        explanation_parts.append("")
        explanation_parts.append(f"Authenticity Score: {round(100 - trust_score, 1)}%")

        return summary, "\n".join(explanation_parts)


trust_engine = TrustScoreEngine()
