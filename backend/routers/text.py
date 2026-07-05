import uuid
import time
from fastapi import APIRouter
from models.schemas import AnalysisResult, TextAnalysisRequest, ContentType
from analyzers.text_analyzer import text_analyzer
from analyzers.rag_verifier import rag_verifier
from core.trust_score import trust_engine
from datetime import datetime

router = APIRouter(prefix="/api/analyze", tags=["Text Analysis"])


@router.post("/text", response_model=AnalysisResult)
async def analyze_text(request: TextAnalysisRequest):
    """
    Analyze text content for AI generation, scam/phishing, and misinformation.
    """
    start_time = time.time()
    all_details = []

    # Run text analysis
    if request.check_ai_generated or request.check_scam:
        text_details, text_context = text_analyzer.analyze(request.text)
        all_details.extend(text_details)

    # Run claim verification
    claims_verified = 0
    claims_flagged = 0
    if request.check_claims:
        claim_details, claim_context = rag_verifier.verify_claims(request.text)
        all_details.extend(claim_details)
        claims_verified = claim_context.get("claims_verified", 0)
        claims_flagged = claim_context.get("claims_flagged", 0)

    # Calculate trust score
    trust_score = trust_engine.calculate_trust_score(all_details)
    risk_level = trust_engine.determine_risk_level(trust_score, all_details)
    is_authentic = trust_engine.determine_authenticity(trust_score, risk_level)

    # Generate explanation
    summary, explanation = trust_engine.generate_explanation(
        "text", trust_score, risk_level, all_details
    )

    processing_time = (time.time() - start_time) * 1000

    return AnalysisResult(
        id=str(uuid.uuid4()),
        content_type=ContentType.TEXT,
        timestamp=datetime.utcnow().isoformat(),
        trust_score=trust_score,
        risk_level=risk_level,
        is_authentic=is_authentic,
        summary=summary,
        explanation=explanation,
        details=all_details,
        extracted_text=request.text[:500],
        claims_verified=claims_verified,
        claims_flagged=claims_flagged,
        processing_time_ms=round(processing_time, 1),
    )
