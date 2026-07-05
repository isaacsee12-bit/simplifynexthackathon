from pydantic import BaseModel
from typing import Optional, List
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


class AnalysisDetail(BaseModel):
    """Individual finding from an analyzer."""
    category: str
    finding: str
    confidence: float  # 0.0 to 1.0
    severity: RiskLevel


class FrameAnalysis(BaseModel):
    """Analysis result for a single video frame."""
    frame_number: int
    is_deepfake: bool
    deepfake_probability: float
    details: str


class AnalysisResult(BaseModel):
    """Complete analysis result returned by the API."""
    id: str
    content_type: ContentType
    timestamp: str
    trust_score: float  # 0 to 100
    risk_level: RiskLevel
    is_authentic: bool
    summary: str
    explanation: str
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
