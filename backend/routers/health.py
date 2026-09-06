from fastapi import APIRouter
from models.schemas import HealthResponse
from core.config import settings
from core import gemini_client
from analyzers.ocr_engine import ocr_engine
from datetime import datetime

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow().isoformat(),
        analyzers={
            "text_analyzer": "local_heuristics",
            "image_analyzer": "sampled_analysis_available",
            "video_analyzer": "sampled_analysis_available",
            "audio_analyzer": "sampled_analysis_available",
            "ocr_engine": "available" if ocr_engine.tesseract_available else "unavailable",
            "rag_verifier": "configured_not_tested" if gemini_client.gemini_client else "not_configured",
            "gemini": "configured_not_tested" if gemini_client.gemini_client else "not_configured",
        }
    )
