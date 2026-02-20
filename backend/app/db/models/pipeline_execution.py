"""
PipelineExecution — DB model tracking each pipeline run and its steps.

Immutable execution log for auditability.  Each run creates one row
with the full step-by-step log stored as JSONB.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.models.base import Base, generate_uuid, utcnow


class PipelineExecution(Base):
    """Tracks a single pipeline execution with full step log."""

    __tablename__ = "pipeline_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    file_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    insuree_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    insuree_code = Column(String(100), nullable=True)

    # Overall status
    status = Column(String(50), nullable=False, default="PENDING")
    current_step = Column(String(100), nullable=True)
    total_steps = Column(Integer, nullable=True)
    steps_completed = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime(timezone=True), default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_duration_ms = Column(Integer, nullable=True)

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Full execution log — array of step results
    execution_log = Column(JSONB, default=list)

    # Context summary snapshot
    context_summary = Column(JSONB, default=dict)

    def __repr__(self) -> str:
        return (
            f"<PipelineExecution id={self.id} "
            f"status={self.status} "
            f"steps={self.steps_completed}/{self.total_steps}>"
        )
