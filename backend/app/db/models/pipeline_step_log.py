"""
PipelineStepLog — one row per step per pipeline run.

Enables querying/filtering by step name, status, and duration.
Linked to PipelineRun via run_id FK.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.models.base import Base, generate_uuid, utcnow


class PipelineStepLog(Base):
    """One row per step execution within a pipeline run."""

    __tablename__ = "pipeline_step_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    run_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── Step identity ─────────────────────────
    step_index = Column(Integer, nullable=False)
    step_name = Column(String(100), nullable=False, index=True)
    step_description = Column(String(500), nullable=True)

    # ── Status ────────────────────────────────
    status = Column(String(50), nullable=False, index=True)

    # ── Timing (UTC) ─────────────────────────
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # ── Error ─────────────────────────────────
    error_message = Column(Text, nullable=True)

    # ── Step output / metadata ────────────────
    metadata_ = Column("metadata", JSONB, default=dict)

    # ── Retry info ────────────────────────────
    retry_count = Column(Integer, default=0)

    # ── Relationship ──────────────────────────
    run = relationship("PipelineRun", back_populates="step_logs")

    def __repr__(self) -> str:
        return f"<PipelineStepLog {self.step_name} status={self.status} index={self.step_index}>"
