from fastapi import APIRouter
from models.schemas import HealthResponse
from core.config import settings
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
            "text_analyzer": "active",
            "image_analyzer": "active",
            "video_analyzer": "active",
            "audio_analyzer": "active",
            "ocr_engine": "active",
            "rag_verifier": "active",
        }
    )
