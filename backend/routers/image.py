import uuid
import time
from fastapi import APIRouter, UploadFile, File
from models.schemas import AnalysisResult, ContentType
from analyzers.image_analyzer import image_analyzer
from analyzers.ocr_engine import ocr_engine
from analyzers.text_analyzer import text_analyzer
from analyzers.rag_verifier import rag_verifier
from core.trust_score import trust_engine
from datetime import datetime

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

    # Run image analysis
    img_details, img_context = image_analyzer.analyze(image_bytes, file.filename or "")
    all_details.extend(img_details)

    # Try OCR extraction
    extracted_text = ocr_engine.extract_text(image_bytes)
    claims_verified = 0
    claims_flagged = 0

    if extracted_text:
        # Analyze extracted text for scams/phishing
        text_details, _ = text_analyzer.analyze(extracted_text)
        all_details.extend(text_details)

        # Verify claims in extracted text
        claim_details, claim_context = rag_verifier.verify_claims(extracted_text)
        all_details.extend(claim_details)
        claims_verified = claim_context.get("claims_verified", 0)
        claims_flagged = claim_context.get("claims_flagged", 0)

    # Calculate trust score
    trust_score = trust_engine.calculate_trust_score(all_details)
    risk_level = trust_engine.determine_risk_level(trust_score, all_details)
    is_authentic = trust_engine.determine_authenticity(trust_score, risk_level)

    # Generate explanation
    summary, explanation = trust_engine.generate_explanation(
        "image", trust_score, risk_level, all_details
    )

    processing_time = (time.time() - start_time) * 1000

    return AnalysisResult(
        id=str(uuid.uuid4()),
        content_type=ContentType.IMAGE,
        timestamp=datetime.utcnow().isoformat(),
        trust_score=trust_score,
        risk_level=risk_level,
        is_authentic=is_authentic,
        summary=summary,
        explanation=explanation,
        details=all_details,
        extracted_text=extracted_text[:500] if extracted_text else None,
        claims_verified=claims_verified,
        claims_flagged=claims_flagged,
        processing_time_ms=round(processing_time, 1),
    )
