import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

if os.environ.get("VERCEL"):
    # librosa/Numba must not write compiled caches into the read-only bundle.
    os.environ.setdefault("NUMBA_CACHE_DIR", os.path.join(tempfile.gettempdir(), "verifyai_numba"))

# Backend configuration
class Settings:
    APP_NAME: str = "VerifyAI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Multimodal Content Verification System"
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
    
    # Server
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", 8000))
    
    # CORS origins
    CORS_ORIGINS: list = [origin.strip() for origin in os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()]
    
    # File upload limits
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_IMAGE_TYPES: list = ["image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"]
    ALLOWED_VIDEO_TYPES: list = ["video/mp4", "video/avi", "video/mov", "video/quicktime", "video/webm", "video/mkv"]
    ALLOWED_AUDIO_TYPES: list = ["audio/mpeg", "audio/wav", "audio/x-wav", "audio/ogg", "audio/flac", "audio/mp3", "audio/mp4", "audio/aac"]
    
    # Analysis
    VIDEO_FRAME_SAMPLE_RATE: int = 5  # Analyze every Nth frame
    MAX_FRAMES_TO_ANALYZE: int = 100
    
    # Temp storage
    TEMP_DIR: str = os.path.join(tempfile.gettempdir(), "verifyai_uploads")

settings = Settings()

# Ensure temp dir exists
os.makedirs(settings.TEMP_DIR, exist_ok=True)
