from models.schemas import RiskLevel, AnalysisDetail
from typing import List, Tuple


class TrustScoreEngine:
    """
    Aggregates individual analyzer scores into a unified trust score.
    Assigns risk level and generates human-readable explanations.

    Trust Score = 0 to 100 where:
    - 0-25: Likely authentic, low risk
    - 25-50: Some concerns, moderate risk
    - 50-75: Significant manipulation indicators
    - 75-100: Strong evidence of manipulation/deepfake
    """

    # Category weights — higher = more impact on final score
    CATEGORY_WEIGHTS = {
        "deepfake_detection": 0.30,
        "ai_generation": 0.25,
        "manipulation": 0.20,
        "scam_phishing": 0.20,
        "claim_verification": 0.10,
        "live_web_verification": 0.05,
        "system_error": 0.0,  # Don't let errors affect score
    }

    # Category name normalization mapping
    CATEGORY_ALIASES = {
        # Deepfake Detection variants
        "deepfake detection": "deepfake_detection",
        "deepfake detection (neural net)": "deepfake_detection",
        "deepfake_detection_(neural_net)": "deepfake_detection",
        "deepfake": "deepfake_detection",

        # AI Generation variants
        "ai generation": "ai_generation",
        "ai generation (neural net)": "ai_generation",
        "ai_generation_(neural_net)": "ai_generation",
        "ai_generation_(neural_net)": "ai_generation",

        # Manipulation variants
        "manipulation": "manipulation",
        "file manipulation": "manipulation",

        # Scam/Phishing variants
        "scam phishing": "scam_phishing",
        "scam_phishing": "scam_phishing",
        "phishing": "scam_phishing",
        "scam": "scam_phishing",

        # Claim Verification variants
        "claim verification": "claim_verification",
        "claim_verification": "claim_verification",
        "live web verification": "live_web_verification",
        "live_web_verification": "live_web_verification",

        # System errors
        "system error": "system_error",
        "system_error": "system_error",
        "general": "ai_generation",
    }

    @classmethod
    def _normalize_category(cls, category: str) -> str:
        """Normalize category name to a known weight key using fuzzy matching."""
        cat_lower = category.lower().strip()

        # Direct match
        if cat_lower in cls.CATEGORY_ALIASES:
            return cls.CATEGORY_ALIASES[cat_lower]

        # Underscore-normalized match
        cat_underscore = cat_lower.replace(" ", "_")
        if cat_underscore in cls.CATEGORY_ALIASES:
            return cls.CATEGORY_ALIASES[cat_underscore]

        # Substring matching — find best match
        for alias, normalized in cls.CATEGORY_ALIASES.items():
            if alias in cat_lower or cat_lower in alias:
                return normalized

        # Keyword-based fallback
        if 'deepfake' in cat_lower or 'face' in cat_lower:
            return "deepfake_detection"
        elif 'ai' in cat_lower or 'generat' in cat_lower or 'neural' in cat_lower or 'synthetic' in cat_lower:
            return "ai_generation"
        elif 'manipulat' in cat_lower or 'edit' in cat_lower or 'splice' in cat_lower:
            return "manipulation"
        elif 'scam' in cat_lower or 'phish' in cat_lower or 'fraud' in cat_lower:
            return "scam_phishing"
        elif 'claim' in cat_lower or 'verif' in cat_lower or 'fact' in cat_lower:
            return "claim_verification"
        elif 'error' in cat_lower or 'system' in cat_lower:
            return "system_error"

        return "ai_generation"  # Default fallback

    @classmethod
    def calculate_trust_score(cls, details: List[AnalysisDetail]) -> float:
        """
        Calculate overall trust score (0-100) from individual findings.
        Higher score = MORE likely manipulated/fake.

        Uses a weighted aggregation that accounts for:
        - Category weights (deepfake > ai_gen > manipulation > scam > claims)
        - Severity multipliers
        - Multiple findings escalation (diminishing returns)
        - Low severity findings as positive authenticity signals
        """
        if not details:
            return 0.0

        # Filter out system errors
        real_details = [d for d in details if cls._normalize_category(d.category) != "system_error"]
        if not real_details:
            return 0.0

        severity_multipliers = {
            RiskLevel.LOW: 0.05,      # Low severity barely affects score
            RiskLevel.MEDIUM: 0.35,
            RiskLevel.HIGH: 0.75,
            RiskLevel.CRITICAL: 1.0
        }

        # Group findings by normalized category
        category_scores = {}
        for detail in real_details:
            norm_cat = cls._normalize_category(detail.category)
            if norm_cat not in category_scores:
                category_scores[norm_cat] = []

            mult = severity_multipliers.get(detail.severity, 0.1)
            score = detail.confidence * mult * 100
            category_scores[norm_cat].append(score)

        # Calculate weighted score per category
        # Use diminishing returns: each additional finding in same category adds less
        total_weighted = 0.0
        total_weight = 0.0

        for cat, scores in category_scores.items():
            weight = cls.CATEGORY_WEIGHTS.get(cat, 0.15)

            # Sort descending — highest impact first
            scores.sort(reverse=True)

            # Diminishing returns: 1st finding = full, 2nd = 70%, 3rd = 50%, etc.
            cat_score = 0.0
            for i, score in enumerate(scores):
                diminish = 1.0 / (1.0 + i * 0.4)
                cat_score += score * diminish

            # Cap per-category contribution
            cat_score = min(cat_score, 100.0)

            total_weighted += cat_score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        raw_score = total_weighted / total_weight

        # Apply mild sigmoid to avoid clustering at extremes
        # This spreads scores more naturally across 0-100
        normalized = raw_score * 1.2  # Slight amplification for sensitivity

        return round(max(0, min(100, normalized)), 1)

    @staticmethod
    def determine_risk_level(trust_score: float, details: List[AnalysisDetail]) -> RiskLevel:
        """Determine risk level based on trust score and severity of findings."""
        critical_findings = sum(1 for d in details if d.severity == RiskLevel.CRITICAL)
        high_findings = sum(1 for d in details if d.severity == RiskLevel.HIGH)

        # Critical findings automatically escalate
        if critical_findings >= 2 or trust_score >= 80:
            return RiskLevel.CRITICAL
        elif critical_findings == 1 or high_findings >= 2 or trust_score >= 55:
            return RiskLevel.HIGH
        elif high_findings >= 1 or trust_score >= 30:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    @staticmethod
    def determine_authenticity(trust_score: float, risk_level: RiskLevel) -> bool:
        """Determine if content appears authentic."""
        return trust_score < 35 and risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]

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
        authenticity_score = round(100 - trust_score, 1)

        # Summary line
        if risk_level == RiskLevel.CRITICAL:
            summary = f"CRITICAL: This {content_type} shows strong signs of manipulation or deception. Authenticity: {authenticity_score}%"
        elif risk_level == RiskLevel.HIGH:
            summary = f"HIGH RISK: This {content_type} contains elements that appear manipulated or AI-generated. Authenticity: {authenticity_score}%"
        elif risk_level == RiskLevel.MEDIUM:
            summary = f"MODERATE: This {content_type} has some suspicious indicators worth reviewing. Authenticity: {authenticity_score}%"
        else:
            summary = f"LOW RISK: This {content_type} appears largely authentic. Authenticity: {authenticity_score}%"

        # Build detailed explanation
        explanation_parts = []
        explanation_parts.append(
            f"My analysis indicates that your {content_type} "
            f"{'contains manipulated elements' if trust_score >= 50 else 'appears largely authentic'}."
        )
        explanation_parts.append("")
        explanation_parts.append(f"Here's what my analysis of your {content_type} revealed:")
        explanation_parts.append("")

        # Add video-specific context
        if content_type == "video" and extra_context:
            total_frames = extra_context.get("total_frames", 0)
            deepfake_frames = extra_context.get("deepfake_frames", 0)
            if total_frames > 0:
                explanation_parts.append(
                    f"Video Analysis: {deepfake_frames} of {total_frames} sampled frames showed deepfake indicators."
                )
                if deepfake_frames > 0 and total_frames > 0:
                    ratio = deepfake_frames / total_frames
                    if ratio > 0.8:
                        explanation_parts.append(
                            "This strongly suggests the video has been generated or heavily manipulated using AI techniques."
                        )
                    elif ratio > 0.4:
                        explanation_parts.append(
                            "A significant portion of frames show AI-generation markers, suggesting partial manipulation."
                        )
                explanation_parts.append("")

        # Sort details by severity (critical first)
        severity_order = {RiskLevel.CRITICAL: 0, RiskLevel.HIGH: 1, RiskLevel.MEDIUM: 2, RiskLevel.LOW: 3}
        sorted_details = sorted(details, key=lambda d: severity_order.get(d.severity, 4))

        # Add each finding
        for detail in sorted_details:
            severity_icon = {
                RiskLevel.LOW: "[LOW]",
                RiskLevel.MEDIUM: "[MEDIUM]",
                RiskLevel.HIGH: "[HIGH]",
                RiskLevel.CRITICAL: "[CRITICAL]",
            }.get(detail.severity, "[INFO]")
            explanation_parts.append(
                f"{severity_icon} [{detail.category}] {detail.finding} (confidence: {detail.confidence:.0%})"
            )

        explanation_parts.append("")
        explanation_parts.append(f"Authenticity Score: {authenticity_score}%")

        return summary, "\n".join(explanation_parts)


trust_engine = TrustScoreEngine()
