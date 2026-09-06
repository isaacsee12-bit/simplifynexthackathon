from google import genai
from google.genai import types

from core.config import settings


gemini_client = (
    genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=30000),
    )
    if settings.GEMINI_API_KEY
    else None
)


def configure_gemini(api_key: str | None, model: str):
    global gemini_client
    key = settings.GEMINI_API_KEY if api_key is None else api_key
    client = (
        genai.Client(api_key=key, http_options=types.HttpOptions(timeout=30000))
        if key else None
    )
    settings.GEMINI_API_KEY = key
    settings.GEMINI_MODEL = model
    gemini_client = client
