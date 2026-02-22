"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, endorsements, files, insurees, pipeline, reports, review, submissions
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.tracing import setup_tracing


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle hooks."""
    setup_logging("DEBUG" if settings.APP_ENV == "development" else "INFO")
    setup_tracing()
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(insurees.router, prefix=API_PREFIX)
app.include_router(files.router, prefix=API_PREFIX)
app.include_router(endorsements.router, prefix=API_PREFIX)
app.include_router(submissions.router, prefix=API_PREFIX)
app.include_router(review.router, prefix=API_PREFIX)
app.include_router(reports.router, prefix=API_PREFIX)
app.include_router(pipeline.router, prefix=API_PREFIX)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Public health-check endpoint."""
    return {"status": "ok", "env": settings.APP_ENV}
