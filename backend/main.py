import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from routers import health, text, image, video, audio
from routers import settings as settings_router

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
app.include_router(settings_router.router)


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

# Vercel serves public assets through its CDN; only mount assets locally.
project_root = Path(__file__).resolve().parent.parent
is_vercel = bool(os.environ.get("VERCEL"))
frontend_dist = (project_root / ("public" if is_vercel else "webapp/dist")).resolve()
if not is_vercel and (frontend_dist / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    requested_file = (frontend_dist / full_path).resolve()
    if not requested_file.is_relative_to(frontend_dist):
        raise HTTPException(status_code=404, detail="Not Found")

    relative_path = requested_file.relative_to(frontend_dist).as_posix()
    if relative_path == "api" or relative_path.startswith("api/") or relative_path in ["docs", "redoc", "openapi.json"]:
        raise HTTPException(status_code=404, detail="Not Found")

    if requested_file.is_file():
        return FileResponse(requested_file)

    index_file = frontend_dist / "index.html"
    if not index_file.is_file():
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(index_file)


if __name__ == "__main__":
    import uvicorn
    # Use reload=True only if running locally on port 8000 (heuristic for dev)
    is_dev = settings.PORT == 8000
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=is_dev)
