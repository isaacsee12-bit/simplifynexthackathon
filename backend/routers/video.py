import uuid
import time
from google.genai import types
from fastapi import APIRouter, UploadFile, File
from models.schemas import AnalysisResult, ContentType, AnalysisCoverage
from analyzers.media_analyzer import request_gemini, media_assessment
from analyzers.video_analyzer import video_analyzer
from datetime import datetime
from core.config import settings
from core.upload_validation import validate_media
from core.investigation_stream import analysis_response, stage

router = APIRouter(prefix="/api/analyze", tags=["Video Analysis"])


@router.post("/video", response_model=AnalysisResult)
async def analyze_video(file: UploadFile = File(...), stream: bool = False):
    video_bytes = await file.read(50 * 1024 * 1024 + 1)
    validate_media(file, video_bytes, settings.ALLOWED_VIDEO_TYPES, 50)
    return await analysis_response(lambda: _analyze_video(video_bytes, file.filename or ""), stream)


async def _analyze_video(video_bytes, filename):
    """
    Analyze a video for deepfake elements with frame-by-frame analysis.
    """
    start_time = time.time()

    # Run video analysis
    local_start = time.perf_counter()
    vid_details, vid_context = await stage("local", "Analyze sampled video frames locally.", video_analyzer.analyze, video_bytes, filename)
    local_ms = (time.perf_counter() - local_start) * 1000
    frames = vid_context.pop("media_frames", [])
    parts = []
    for timestamp, jpeg in frames:
        parts.extend([types.Part.from_text(text=f"Video frame at {timestamp:.3f} seconds"),
                      types.Part.from_bytes(data=jpeg, mime_type="image/jpeg")])
    coverage = AnalysisCoverage(
        description="Up to 15 evenly spaced timestamped frames, resized to at most 768 pixels. No video audio, continuous motion, or unsampled frames analyzed by Gemini.",
        media_duration_seconds=vid_context.get("duration_seconds") or None,
        total_frames=vid_context.get("total_frames_estimated"),
        frame_timestamps_seconds=[timestamp for timestamp, _ in frames], media_parts=len(frames),
    )
    report = await stage("provider", "Request Gemini sampled-frame assessment.", request_gemini, parts, coverage, threaded=False)

    processing_time = (time.time() - start_time) * 1000

    return AnalysisResult(
        id=str(uuid.uuid4()),
        content_type=ContentType.VIDEO,
        timestamp=datetime.utcnow().isoformat(),
        **media_assessment(report, coverage.model_copy(update={"submitted": False, "description": "Sampled-frame temporal and container heuristics; optional neural detector. No full-video verification."}), local_ms, vid_details),
        details=vid_details,
        uncertainties=["Only sampled frames were checked; video audio, continuous motion, and unsampled frames were not verified."],
        total_frames=vid_context.get("total_frames_estimated"),
        deepfake_frames=vid_context.get("deepfake_frames_sampled"),
        frame_analyses=vid_context.get("frame_analyses"),
        processing_time_ms=round(processing_time, 1),
    )
