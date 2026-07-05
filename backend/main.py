from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from routers import health, text, image, video, audio

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(text.router)
app.include_router(image.router)
app.include_router(video.router)
app.include_router(audio.router)


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "tagline": "See through the lies.",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "endpoints": {
            "health": "/api/health",
            "analyze_text": "POST /api/analyze/text",
            "analyze_image": "POST /api/analyze/image",
            "analyze_video": "POST /api/analyze/video",
            "analyze_audio": "POST /api/analyze/audio",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
