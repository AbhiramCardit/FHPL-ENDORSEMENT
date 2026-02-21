"""
LangSmith tracing utilities for the pipeline engine.

Provides a setup function and a @traceable-safe wrapper so that
tracing works when LangSmith is configured but degrades gracefully
when it isn't (e.g. local dev without API key).

Usage:
    from app.core.tracing import setup_tracing, traceable_step

    setup_tracing()   # call once at startup

    @traceable_step(name="extract_pdf", run_type="chain")
    async def extract(file_path, ctx):
        ...
"""

from __future__ import annotations

import os
import functools
from typing import Any, Callable

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_tracing_enabled = False


def setup_tracing() -> bool:
    """
    Configure LangSmith tracing from application settings.

    Sets environment variables that the LangSmith SDK reads.
    Call this once at application startup (e.g. in main.py lifespan).

    Returns True if tracing was enabled, False otherwise.
    """
    global _tracing_enabled

    if not settings.LANGSMITH_TRACING or not settings.LANGSMITH_API_KEY:
        logger.info(
            "LangSmith tracing disabled",
            reason="LANGSMITH_TRACING=False or no API key",
        )
        _tracing_enabled = False
        return False

    os.environ["LANGSMITH_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGSMITH_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
    os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGSMITH_TRACING"] = "true"

    logger.info(
        "LangSmith tracing enabled",
        project=settings.LANGSMITH_PROJECT,
    )
    _tracing_enabled = True
    return True


def is_tracing_enabled() -> bool:
    """Check if LangSmith tracing is active."""
    return _tracing_enabled


def traceable_step(
    name: str,
    run_type: str = "chain",
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> Callable:
    """
    Decorator that wraps a function with LangSmith @traceable
    when tracing is enabled.  Falls back to a no-op wrapper
    when LangSmith is not configured.

    Args:
        name: Trace name shown in LangSmith UI.
        run_type: One of "chain", "llm", "tool", "retriever".
        metadata: Static metadata attached to every trace.
        tags: Tags for filtering in LangSmith.

    Usage::

        @traceable_step(name="extract_pdf", run_type="chain")
        async def extract_pdf(file_path: str, **kwargs):
            # LLM call here
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if _tracing_enabled:
                try:
                    from langsmith import traceable

                    traced_fn = traceable(
                        name=name,
                        run_type=run_type,
                        metadata=metadata or {},
                        tags=tags or [],
                    )(func)
                    return await traced_fn(*args, **kwargs)
                except ImportError:
                    logger.warning("langsmith not installed, skipping tracing")
                    return await func(*args, **kwargs)
                except Exception as exc:
                    # Tracing failure should never break the pipeline
                    logger.warning("LangSmith tracing failed, continuing without", error=str(exc))
                    return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
        return wrapper
    return decorator
