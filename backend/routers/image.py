import uuid
import time
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
from core.investigation_stream import analysis_response, stage, investigate

router = APIRouter(prefix="/api/analyze", tags=["Image Analysis"])


@router.post("/image", response_model=AnalysisResult)
async def analyze_image(file: UploadFile = File(...), stream: bool = False):
    image_bytes = await file.read(15 * 1024 * 1024 + 1)
    validate_media(file, image_bytes, settings.ALLOWED_IMAGE_TYPES, 15)
    return await analysis_response(lambda: _analyze_image(image_bytes, file.filename or ""), stream)


async def _analyze_image(image_bytes, filename):
    """
    Analyze an image for AI generation, manipulation, and embedded text.
    """
    start_time = time.time()
    all_details = []

    # Run image analysis
    local_start = time.perf_counter()
    img_details, img_context = await stage("local", "Run local image checks.", image_analyzer.analyze, image_bytes, filename)
    all_details.extend(img_details)

    # Try OCR extraction
    extracted_text = await stage("ocr", "Extract visible image text with OCR.", ocr_engine.extract_text, image_bytes)
    claims_verified = 0
    claims_flagged = 0
    investigation = None

    if extracted_text:
        # Analyze extracted text for scams/phishing
        text_details, _ = await stage("local", "Check extracted text locally.", text_analyzer.analyze, extracted_text, use_llm=False)
        all_details.extend(text_details)

        # Verify claims in extracted text
        claim_details, investigation = await investigate(rag_verifier, extracted_text)
        all_details.extend(claim_details)
        claims_verified = sum(c.verdict == "supported" for c in investigation.claims)
        claims_flagged = sum(c.verdict == "refuted" for c in investigation.claims)

    local_ms = (time.perf_counter() - local_start) * 1000
    parts, coverage = await stage("prepare", "Prepare image for provider review.", prepare_image, image_bytes)
    report = await stage("provider", "Request Gemini media assessment.", request_gemini, parts, coverage, threaded=False)

    processing_time = (time.time() - start_time) * 1000

    return AnalysisResult(
        id=str(uuid.uuid4()),
        content_type=ContentType.IMAGE,
        timestamp=datetime.utcnow().isoformat(),
        **media_assessment(report, AnalysisCoverage(description="Image heuristics and optional neural detector/OCR; extracted-text checks may use Gemini and web retrieval."), local_ms, all_details),
        details=all_details,
        investigation=investigation,
        uncertainties=["OCR may omit or misread visible text."] if extracted_text else
                      ["No visible text extracted; OCR may be unavailable or the image may contain no readable text. Factual claims were not checked."],
        extracted_text=extracted_text[:500] if extracted_text else None,
        claims_verified=claims_verified,
        claims_flagged=claims_flagged,
        processing_time_ms=round(processing_time, 1),
    )
