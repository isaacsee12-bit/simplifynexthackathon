import uuid
import time
from google.genai import types
from fastapi import APIRouter, UploadFile, File
from models.schemas import AnalysisResult, ContentType, AnalysisCoverage
from analyzers.media_analyzer import request_gemini, media_assessment
from analyzers.audio_analyzer import audio_analyzer
from datetime import datetime
from core.config import settings
from core.upload_validation import validate_media
from core.investigation_stream import analysis_response, stage

router = APIRouter(prefix="/api/analyze", tags=["Audio Analysis"])


@router.post("/audio", response_model=AnalysisResult)
async def analyze_audio(file: UploadFile = File(...), stream: bool = False):
    audio_bytes = await file.read(20 * 1024 * 1024 + 1)
    validate_media(file, audio_bytes, settings.ALLOWED_AUDIO_TYPES, 20)
    return await analysis_response(lambda: _analyze_audio(audio_bytes, file.filename or ""), stream)


async def _analyze_audio(audio_bytes, filename):
    """
    Analyze audio for voice cloning, AI-generated speech, and manipulation.
    """
    start_time = time.time()

    # Run audio analysis
    local_start = time.perf_counter()
    aud_details, aud_context = await stage("local", "Analyze opening audio sample locally.", audio_analyzer.analyze, audio_bytes, filename)
    local_ms = (time.perf_counter() - local_start) * 1000
    sample = aud_context.pop("media_audio", None)
    parts = [types.Part.from_bytes(data=sample, mime_type="audio/wav")] if sample else []
    coverage = AnalysisCoverage(
        description="Decoded opening audio sample only, capped at 60 seconds, mono PCM WAV at 22050 Hz. Remainder and speaker identity are not verified; full source duration is unknown.",
        analyzed_duration_seconds=aud_context.get("duration_seconds") or None,
        media_parts=len(parts),
    )
    report = await stage("provider", "Request Gemini audio-sample assessment.", request_gemini, parts, coverage, threaded=False)

    processing_time = (time.time() - start_time) * 1000

    return AnalysisResult(
        id=str(uuid.uuid4()),
        content_type=ContentType.AUDIO,
        timestamp=datetime.utcnow().isoformat(),
        **media_assessment(report, coverage.model_copy(update={"submitted": False, "description": "Spectral/signal checks on the opening at-most-60-second decoded sample, plus container heuristics; byte-level fallback when decoding fails."}), local_ms, aud_details),
        details=aud_details,
        uncertainties=["Only the opening at-most-60-second sample was checked; remaining audio, speaker identity, and spoken factual claims were not verified."],
        processing_time_ms=round(processing_time, 1),
    )
