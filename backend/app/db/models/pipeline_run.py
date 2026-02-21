"""
PipelineRun — main pipeline execution record.

One row per pipeline run. Tracks insurer, status, timing, and step counts.
Replaces the old flat PipelineExecution model with proper indexed columns
for filtering by insurer, status, and date range.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.models.base import Base, generate_uuid, utcnow


class PipelineRun(Base):
    """One row per pipeline execution."""

    __tablename__ = "pipeline_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)

    # ── Insurer ──────────────────────────────
    insurer_code = Column(String(50), nullable=False, index=True)
    insurer_name = Column(String(255), nullable=True)

    # ── Status / Progress ────────────────────
    status = Column(String(50), nullable=False, default="PENDING", index=True)
    total_steps = Column(Integer, nullable=True)
    steps_completed = Column(Integer, default=0)

    # ── Timing (UTC) ─────────────────────────
    started_at = Column(DateTime(timezone=True), default=utcnow, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # ── Error ─────────────────────────────────
    error_message = Column(Text, nullable=True)

    # ── Config snapshot ───────────────────────
    config_snapshot = Column(JSONB, default=dict)

    # ── Final state snapshot ──────────────────
    # Full context summary at end of run: total records,
    # extracted by role, canonical counts, errors, etc.
    context_summary = Column(JSONB, default=dict)

    # ── Audit timestamps ─────────────────────
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # ── Relationships ─────────────────────────
    step_logs = relationship("PipelineStepLog", back_populates="run", cascade="all, delete-orphan", order_by="PipelineStepLog.step_index")
    files = relationship("PipelineFile", back_populates="run", cascade="all, delete-orphan")
    extracted_data = relationship("PipelineExtractedData", back_populates="run", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<PipelineRun {self.id} insurer={self.insurer_code} status={self.status} steps={self.steps_completed}/{self.total_steps}>"
