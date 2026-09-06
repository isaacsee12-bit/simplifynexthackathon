import uuid
import time
from fastapi import APIRouter
from models.schemas import AnalysisResult, TextAnalysisRequest, ContentType
from analyzers.text_analyzer import text_analyzer
from analyzers.rag_verifier import rag_verifier
from core.trust_score import trust_engine
from datetime import datetime
from core.investigation_stream import analysis_response, stage, investigate

router = APIRouter(prefix="/api/analyze", tags=["Text Analysis"])


@router.post("/text", response_model=AnalysisResult)
async def analyze_text(request: TextAnalysisRequest, stream: bool = False):
    return await analysis_response(lambda: _analyze_text(request), stream)


async def _analyze_text(request: TextAnalysisRequest):
    """
    Analyze text content for AI generation, scam/phishing, and misinformation.
    """
    start_time = time.time()
    all_details = []

    # Run text analysis
    if request.check_ai_generated or request.check_scam:
        text_details, text_context = await stage("local", "Run enabled local text checks.",
            text_analyzer.analyze, request.text, check_ai_generated=request.check_ai_generated,
            check_scam=request.check_scam, use_llm=False)
        all_details.extend(text_details)

    # Run claim verification
    claims_verified = 0
    claims_flagged = 0
    investigation = None
    scoring_details = list(all_details)
    if request.check_claims:
        claim_details, investigation = await investigate(rag_verifier, request.text)
        all_details.extend(claim_details)
        claims_verified = sum(c.verdict == "supported" for c in investigation.claims)
        claims_flagged = sum(c.verdict == "refuted" for c in investigation.claims)
        scoring_details.extend(d for d, c in zip(claim_details, investigation.claims)
                               if c.verdict in ("supported", "refuted"))

    # Calculate trust score
    trust_score = trust_engine.calculate_trust_score(scoring_details)
    risk_level = trust_engine.determine_risk_level(trust_score, scoring_details)
    is_authentic = None

    # Generate explanation
    summary, explanation = trust_engine.generate_explanation(
        "text", trust_score, risk_level, scoring_details
    )
    verdict = None
    if not any(trust_engine._normalize_category(d.category) != "system_error" for d in scoring_details):
        trust_score = risk_level = is_authentic = None
        verdict = "inconclusive"
        summary = "Inconclusive: no content evidence was produced by the enabled checks."
        explanation = "Disabled or unavailable checks do not establish authenticity or content risk."

    processing_time = (time.time() - start_time) * 1000

    return AnalysisResult(
        id=str(uuid.uuid4()),
        content_type=ContentType.TEXT,
        timestamp=datetime.utcnow().isoformat(),
        trust_score=trust_score,
        risk_level=risk_level,
        is_authentic=is_authentic,
        verdict=verdict,
        summary=summary,
        explanation=explanation,
        details=all_details,
        investigation=investigation,
        uncertainties=["Text heuristics cannot establish authorship or authenticity."] +
                      ([] if request.check_claims else ["Factual claims were not checked."]),
        extracted_text=request.text[:500],
        claims_verified=claims_verified,
        claims_flagged=claims_flagged,
        processing_time_ms=round(processing_time, 1),
    )
