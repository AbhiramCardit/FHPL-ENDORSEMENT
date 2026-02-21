"""
PipelineFile — one row per file processed in a pipeline run.

Tracks each file in a batch: role, format, record count, status.
Linked to PipelineRun via run_id FK.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.models.base import Base, generate_uuid, utcnow


class PipelineFile(Base):
    """One row per file processed in a pipeline run."""

    __tablename__ = "pipeline_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    run_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── File identity ─────────────────────────
    file_id = Column(String(255), nullable=False)
    filename = Column(String(500), nullable=False)
    role = Column(String(100), nullable=False, index=True)

    # ── Processing info ───────────────────────
    detected_format = Column(String(50), nullable=True)
    s3_key = Column(String(1000), nullable=True)
    local_path = Column(String(1000), nullable=True)
    record_count = Column(Integer, default=0)

    # ── Status ────────────────────────────────
    status = Column(String(50), nullable=False, default="PENDING")
    error_message = Column(Text, nullable=True)

    # ── Timestamps ────────────────────────────
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # ── Relationships ─────────────────────────
    run = relationship("PipelineRun", back_populates="files")
    extracted_data = relationship("PipelineExtractedData", back_populates="file", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<PipelineFile {self.filename} role={self.role} records={self.record_count} status={self.status}>"
