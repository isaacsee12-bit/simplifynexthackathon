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


import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

@app.get("/api/info")
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

# Mount the frontend static files
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "webapp", "dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Don't intercept API calls
        if full_path.startswith("api/") or full_path in ["docs", "redoc", "openapi.json"]:
            return {"detail": "Not Found"}
            
        requested_file = os.path.join(frontend_dist, full_path)
        if os.path.isfile(requested_file):
            return FileResponse(requested_file)
            
        return FileResponse(os.path.join(frontend_dist, "index.html"))


if __name__ == "__main__":
    import uvicorn
    # Use reload=True only if running locally on port 8000 (heuristic for dev)
    is_dev = settings.PORT == 8000
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=is_dev)
