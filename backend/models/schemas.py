from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from enum import Enum
from datetime import datetime


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContentType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    SCREENSHOT = "screenshot"


class DetailedMetric(BaseModel):
    """Detailed forensic metric for advanced reporting."""
    name: str
    score: float
    description: str


class AnalysisDetail(BaseModel):
    """Individual finding from an analyzer."""
    category: str
    finding: str
    confidence: float  # 0.0 to 1.0
    severity: RiskLevel


class FrameAnalysis(BaseModel):
    """Analysis result for a single video frame."""
    frame_number: int
    is_deepfake: Optional[bool]
    deepfake_probability: Optional[float]
    details: str


class AnalysisCoverage(BaseModel):
    description: str
    media_duration_seconds: Optional[float] = None
    analyzed_duration_seconds: Optional[float] = None
    frame_timestamps_seconds: List[float] = Field(default_factory=list)
    total_frames: Optional[int] = None
    media_parts: int = 0
    submitted: bool = False


class AnalysisProvenance(BaseModel):
    provider: str
    model: Optional[str] = None
    status: Literal["completed", "partial", "not_configured", "insufficient_media",
                    "timeout", "authentication_error", "quota_exceeded", "model_unavailable",
                    "provider_error", "invalid_response", "blocked"]
    duration_ms: float = 0
    coverage: AnalysisCoverage
    message: str
    verdict: Literal["suspicious", "no_indicators", "inconclusive"] = "inconclusive"
    observations: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Complete analysis result returned by the API."""
    id: str
    content_type: ContentType
    timestamp: str
    trust_score: Optional[float]  # Legacy uncalibrated indicator score, not a probability
    risk_level: Optional[RiskLevel]
    is_authentic: Optional[bool]
    verdict: Optional[Literal["suspicious", "no_indicators", "inconclusive"]] = None
    provenance: List[AnalysisProvenance] = Field(default_factory=list)
    summary: str
    explanation: str
    analysis_summary: Optional[str] = None
    detailed_breakdown: Optional[List[DetailedMetric]] = None
    details: List[AnalysisDetail]
    # Video-specific
    total_frames: Optional[int] = None
    deepfake_frames: Optional[int] = None
    frame_analyses: Optional[List[FrameAnalysis]] = None
    # Text-specific
    extracted_text: Optional[str] = None
    claims_verified: Optional[int] = None
    claims_flagged: Optional[int] = None
    # Processing metadata
    processing_time_ms: float = 0
    analyzer_version: str = "1.0.0"


class TextAnalysisRequest(BaseModel):
    """Request body for text analysis."""
    text: str
    check_claims: bool = True
    check_ai_generated: bool = True
    check_scam: bool = True


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    app_name: str
    version: str
    timestamp: str
    analyzers: dict
