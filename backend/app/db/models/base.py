"""
SQLAlchemy declarative base and shared utilities for all models.

Convention:
    - Each table lives in its own file under `app/db/models/`
    - Every model file imports `Base` from here
    - The `__init__.py` re-exports all models so Alembic sees them
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ─── Shared helpers ───────────────────────────
def generate_uuid() -> uuid.UUID:
    """Generate a new UUID v4."""
    return uuid.uuid4()


def utcnow() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)
