"""
FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.api.v1 import insurees, files, endorsements, submissions, review, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown events."""
    setup_logging("DEBUG" if settings.APP_ENV == "development" else "INFO")
    logger = get_logger("startup")
    logger.info("Application starting", env=settings.APP_ENV)
    yield
    logger.info("Application shutting down")


app = FastAPI(
    title="Endorsements Automation API",
    description="End-to-end insurance endorsement processing platform",
    version="0.1.0",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ───────────────────────────────────
API_PREFIX = "/api/v1"
app.include_router(insurees.router, prefix=API_PREFIX)
app.include_router(files.router, prefix=API_PREFIX)
app.include_router(endorsements.router, prefix=API_PREFIX)
app.include_router(submissions.router, prefix=API_PREFIX)
app.include_router(review.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)


# ─── Health Check ─────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "env": settings.APP_ENV}
