import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from database import init_db, get_db
from routers.tutor import router as tutor_router
from routers.quiz import router as quiz_router
from routers.grade import router as grade_router
from routers.documents import router as documents_router
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and other resources on startup"""
    await init_db()
    yield


# Create FastAPI app with lifespan management
app = FastAPI(
    title="AI Educational Tutoring Platform",
    description="AI-powered tutoring platform with vector search and quiz generation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tutor_router, prefix="/api/tutor", tags=["tutoring"])
app.include_router(quiz_router, prefix="/api/quiz", tags=["quiz"])
app.include_router(grade_router, prefix="/api/grade", tags=["grading"])
app.include_router(documents_router, prefix="/api/documents", tags=["documents"])

# Serve static files for frontend
try:
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
except Exception:
    # Frontend directory might not exist in development
    pass


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "AI Educational Tutoring Platform"}


@app.get("/api/health")
async def api_health_check():
    """API health check endpoint"""
    try:
        # Test database connection
        async with get_db() as db:
            await db.execute("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
