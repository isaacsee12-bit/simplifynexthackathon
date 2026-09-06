import os
from ipaddress import ip_address
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, SecretStr

from core.config import settings
from core.gemini_client import configure_gemini
from analyzers.media_analyzer import request_gemini
from models.schemas import AnalysisCoverage, AnalysisProvenance


def require_local_request(request: Request):
    def is_loopback(host):
        try:
            return ip_address(host).is_loopback
        except ValueError:
            return host == "localhost"

    origin = request.headers.get("origin")
    try:
        local_origin = not origin or (
            urlsplit(origin).scheme in ("http", "https")
            and is_loopback(urlsplit(origin).hostname or "")
        )
    except ValueError:
        local_origin = False
    if (
        os.environ.get("VERCEL")
        or not request.client
        or not is_loopback(request.client.host)
        or not is_loopback(request.url.hostname or "")
        or not local_origin
        or request.headers.get("x-verifyai-settings") != "1"
    ):
        raise HTTPException(status_code=403, detail="Settings are available on localhost only.")


router = APIRouter(
    prefix="/api/settings", tags=["Local Settings"],
    dependencies=[Depends(require_local_request)],
)


class GeminiSettingsRequest(BaseModel):
    api_key: SecretStr | None = None
    model: str = Field(default="gemini-3.5-flash", min_length=1, max_length=200,
                       pattern=r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


@router.get("/gemini")
def get_gemini_settings():
    return {"configured": bool(settings.GEMINI_API_KEY), "model": settings.GEMINI_MODEL}


@router.put("/gemini")
def update_gemini_settings(body: GeminiSettingsRequest):
    key = body.api_key.get_secret_value().strip() if body.api_key is not None else None
    try:
        configure_gemini(key or None, body.model)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not configure Gemini.") from None
    return get_gemini_settings()


@router.delete("/gemini")
def clear_gemini_settings():
    configure_gemini("", settings.GEMINI_MODEL)
    return get_gemini_settings()


@router.post("/gemini/test", response_model=AnalysisProvenance)
async def test_gemini_connection():
    return await request_gemini([], AnalysisCoverage(
        description="Minimal text-only connection test using saved session settings. No uploaded media or key is returned.",
    ), connection_test=True)
