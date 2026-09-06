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
