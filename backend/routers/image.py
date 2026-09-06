import uuid
import time
import asyncio
from fastapi import APIRouter, UploadFile, File
from models.schemas import AnalysisResult, ContentType, AnalysisCoverage
from analyzers.media_analyzer import prepare_image, request_gemini, media_assessment
from analyzers.image_analyzer import image_analyzer
from analyzers.ocr_engine import ocr_engine
from analyzers.text_analyzer import text_analyzer
from analyzers.rag_verifier import rag_verifier
from datetime import datetime
from core.config import settings
from core.upload_validation import validate_media

router = APIRouter(prefix="/api/analyze", tags=["Image Analysis"])


@router.post("/image", response_model=AnalysisResult)
async def analyze_image(file: UploadFile = File(...)):
    """
    Analyze an image for AI generation, manipulation, and embedded text.
    """
    start_time = time.time()
    all_details = []

    # Read file bytes
    image_bytes = await file.read()
    validate_media(file, image_bytes, settings.ALLOWED_IMAGE_TYPES, 15)

    # Run image analysis
    local_start = time.perf_counter()
    img_details, img_context = await asyncio.to_thread(image_analyzer.analyze, image_bytes, file.filename or "")
    all_details.extend(img_details)

    # Try OCR extraction
    extracted_text = await asyncio.to_thread(ocr_engine.extract_text, image_bytes)
    claims_verified = 0
    claims_flagged = 0

    if extracted_text:
        # Analyze extracted text for scams/phishing
        text_details, _ = await asyncio.to_thread(text_analyzer.analyze, extracted_text)
        all_details.extend(text_details)

        # Verify claims in extracted text
        claim_details, claim_context = await asyncio.to_thread(rag_verifier.verify_claims, extracted_text)
        all_details.extend(claim_details)
        claims_verified = claim_context.get("claims_verified", 0)
        claims_flagged = claim_context.get("claims_flagged", 0)

    local_ms = (time.perf_counter() - local_start) * 1000
    parts, coverage = await asyncio.to_thread(prepare_image, image_bytes)
    report = await request_gemini(parts, coverage)

    processing_time = (time.time() - start_time) * 1000

    return AnalysisResult(
        id=str(uuid.uuid4()),
        content_type=ContentType.IMAGE,
        timestamp=datetime.utcnow().isoformat(),
        **media_assessment(report, AnalysisCoverage(description="Image heuristics and optional neural detector/OCR; extracted-text checks may use Gemini and web retrieval."), local_ms, all_details),
        details=all_details,
        extracted_text=extracted_text[:500] if extracted_text else None,
        claims_verified=claims_verified,
        claims_flagged=claims_flagged,
        processing_time_ms=round(processing_time, 1),
    )
