import os
import logging
import uvicorn
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from starlette.responses import FileResponse, JSONResponse, RedirectResponse

from database import init_db, get_db
from routers.tutor import router as tutor_router
from routers.quiz import router as quiz_router
from routers.grade import router as grade_router
from routers.documents import router as documents_router
from config import settings

logger = logging.getLogger("uvicorn.error")

# --- Lifespan ---------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and other resources on startup."""
    try:
        await init_db()
        logger.info("Database initialization completed.")
    except Exception as e:
        # Don't crash the app on startup; surface via /api/health
        logger.exception("Database initialization failed: %s", e)
    yield
    # (Optional) add graceful shutdown cleanup here


# --- App --------------------------------------------------------------------
app = FastAPI(
    title="AI Educational Tutoring Platform",
    description="AI-powered tutoring platform with vector search and quiz generation",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # Critical: prevent Swagger from prefixing /api again
    schema["servers"] = [{"url": ""}]
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi

# --- CORS -------------------------------------------------------------------
# Use settings if provided; otherwise default to permissive for now.
allow_origins: Optional[list[str]] = getattr(settings, "CORS_ORIGINS", None) or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ----------------------------------------------------------------
app.include_router(tutor_router, prefix="/api/tutor", tags=["tutoring"])
app.include_router(quiz_router, prefix="/api/quiz", tags=["quiz"])
app.include_router(grade_router, prefix="/api/grade", tags=["grading"])
app.include_router(documents_router, prefix="/api/documents", tags=["documents"])

# --- Frontend / Root handling ----------------------------------------------
FRONTEND_DIR = os.getenv("FRONTEND_DIR", "frontend")

def _frontend_index_path() -> str:
    return os.path.join(FRONTEND_DIR, "index.html")

if os.path.isdir(FRONTEND_DIR):
    # Serve static assets under /assets (or adjust to your build output)
    assets_dir = os.path.join(FRONTEND_DIR, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        """
        Serve the frontend index.html if present; otherwise fall back to docs.
        This avoids 404 at "/" when the frontend exists.
        """
        index_path = _frontend_index_path()
        if os.path.isfile(index_path):
            return FileResponse(index_path, media_type="text/html")
        return RedirectResponse(url="/docs")
else:
    @app.get("/", include_in_schema=False)
    async def root_message():
        """
        If no frontend directory, return a helpful landing JSON instead of 404.
        """
        return JSONResponse(
            {
                "message": "API is running ✅",
                "docs": "/docs",
                "redoc": "/redoc",
                "health": "/health",
                "api_health": "/api/health",
                "routes": {
                    "tutor": "/api/tutor/…",
                    "quiz": "/api/quiz/…",
                    "grade": "/api/grade/…",
                    "documents": "/api/documents/…",
                },
            }
        )

# --- Health endpoints -------------------------------------------------------
@app.get("/health")
async def health_check():
    """Simple service liveness check (does not assert DB)."""
    return {"status": "healthy", "service": "AI Educational Tutoring Platform"}

@app.get("/api/health")
async def api_health_check():
    """Deep health check that verifies DB connectivity."""
    try:
        async with get_db() as db:
            await db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        msg = f"Database connection failed: {str(e)}"
        logger.error(msg)
        raise HTTPException(status_code=500, detail=msg)


# --- Entrypoint -------------------------------------------------------------
if __name__ == "__main__":
    # Honor common env vars so the same file works locally and on servers.
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload_flag = os.getenv("RELOAD", "false").lower() in {"1", "true", "yes"}
    log_level = os.getenv("LOG_LEVEL", "info")

    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload_flag,
        log_level=log_level,
        # If behind a proxy (e.g., Nginx), uncomment:
        # proxy_headers=True,
        # forwarded_allow_ips="*",
    )
