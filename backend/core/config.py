import os

# Backend configuration
class Settings:
    APP_NAME: str = "TruthLens AI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Multimodal Content Verification System"
    
    # Server
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", 8000))
    
    # CORS origins
    CORS_ORIGINS: list = [
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",
        "*"
    ]
    
    # File upload limits
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_IMAGE_TYPES: list = ["image/jpeg", "image/png", "image/webp", "image/gif", "image/bmp"]
    ALLOWED_VIDEO_TYPES: list = ["video/mp4", "video/avi", "video/mov", "video/webm", "video/mkv"]
    ALLOWED_AUDIO_TYPES: list = ["audio/mpeg", "audio/wav", "audio/ogg", "audio/flac", "audio/mp3"]
    
    # Analysis
    VIDEO_FRAME_SAMPLE_RATE: int = 5  # Analyze every Nth frame
    MAX_FRAMES_TO_ANALYZE: int = 100
    
    # Temp storage
    TEMP_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp_uploads")

settings = Settings()

# Ensure temp dir exists
os.makedirs(settings.TEMP_DIR, exist_ok=True)
