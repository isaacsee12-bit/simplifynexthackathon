import uuid
import time
from fastapi import APIRouter, UploadFile, File
from models.schemas import AnalysisResult, ContentType
from analyzers.video_analyzer import video_analyzer
from core.trust_score import trust_engine
from datetime import datetime

router = APIRouter(prefix="/api/analyze", tags=["Video Analysis"])


@router.post("/video", response_model=AnalysisResult)
async def analyze_video(file: UploadFile = File(...)):
    """
    Analyze a video for deepfake elements with frame-by-frame analysis.
    """
    start_time = time.time()

    # Read file bytes
    video_bytes = await file.read()

    # Run video analysis
    vid_details, vid_context = video_analyzer.analyze(video_bytes, file.filename or "")

    # Calculate trust score
    trust_score = trust_engine.calculate_trust_score(vid_details)
    risk_level = trust_engine.determine_risk_level(trust_score, vid_details)
    is_authentic = trust_engine.determine_authenticity(trust_score, risk_level)

    # Generate explanation with video-specific context
    summary, explanation = trust_engine.generate_explanation(
        "video", trust_score, risk_level, vid_details,
        extra_context={
            "total_frames": vid_context.get("total_frames", 0),
            "deepfake_frames": vid_context.get("deepfake_frames", 0),
        }
    )

    processing_time = (time.time() - start_time) * 1000

    return AnalysisResult(
        id=str(uuid.uuid4()),
        content_type=ContentType.VIDEO,
        timestamp=datetime.utcnow().isoformat(),
        trust_score=trust_score,
        risk_level=risk_level,
        is_authentic=is_authentic,
        summary=summary,
        explanation=explanation,
        details=vid_details,
        total_frames=vid_context.get("total_frames"),
        deepfake_frames=vid_context.get("deepfake_frames"),
        frame_analyses=vid_context.get("frame_analyses"),
        processing_time_ms=round(processing_time, 1),
    )
