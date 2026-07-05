import uuid
import time
from fastapi import APIRouter, UploadFile, File
from models.schemas import AnalysisResult, ContentType
from analyzers.audio_analyzer import audio_analyzer
from core.trust_score import trust_engine
from datetime import datetime

router = APIRouter(prefix="/api/analyze", tags=["Audio Analysis"])


@router.post("/audio", response_model=AnalysisResult)
async def analyze_audio(file: UploadFile = File(...)):
    """
    Analyze audio for voice cloning, AI-generated speech, and manipulation.
    """
    start_time = time.time()

    # Read file bytes
    audio_bytes = await file.read()

    # Run audio analysis
    aud_details, aud_context = audio_analyzer.analyze(audio_bytes, file.filename or "")

    # Calculate trust score
    trust_score = trust_engine.calculate_trust_score(aud_details)
    risk_level = trust_engine.determine_risk_level(trust_score, aud_details)
    is_authentic = trust_engine.determine_authenticity(trust_score, risk_level)

    # Generate explanation
    summary, explanation = trust_engine.generate_explanation(
        "audio", trust_score, risk_level, aud_details
    )

    processing_time = (time.time() - start_time) * 1000

    return AnalysisResult(
        id=str(uuid.uuid4()),
        content_type=ContentType.AUDIO,
        timestamp=datetime.utcnow().isoformat(),
        trust_score=trust_score,
        risk_level=risk_level,
        is_authentic=is_authentic,
        summary=summary,
        explanation=explanation,
        details=aud_details,
        processing_time_ms=round(processing_time, 1),
    )
