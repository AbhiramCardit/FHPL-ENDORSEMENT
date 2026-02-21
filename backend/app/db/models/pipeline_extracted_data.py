"""
PipelineExtractedData — stores extraction output per file.

Generic JSONB `data` field holds whatever the step produced —
could be an array of records, schedule metadata, or anything else.
Linked to PipelineRun and PipelineFile via FKs.
"""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.models.base import Base, generate_uuid, utcnow


class PipelineExtractedData(Base):
    """Extraction output for a single file in a pipeline run."""

    __tablename__ = "pipeline_extracted_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=generate_uuid)
    run_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(UUID(as_uuid=True), ForeignKey("pipeline_files.id", ondelete="CASCADE"), nullable=True, index=True)

    # ── Source info ───────────────────────────
    source_role = Column(String(100), nullable=False, index=True)
    extraction_method = Column(String(50), nullable=False)  # xls_extractor, llm
    llm_model = Column(String(100), nullable=True)          # gemini-2.5-flash, etc.

    # ── Output ────────────────────────────────
    raw_data = Column(JSONB, default=dict)  # Original extraction output (unprocessed)
    data = Column(JSONB, default=dict)      # Parsed / processed / mapped data

    # ── Timestamps ────────────────────────────
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # ── Relationships ─────────────────────────
    run = relationship("PipelineRun", back_populates="extracted_data")
    file = relationship("PipelineFile", back_populates="extracted_data")

    def __repr__(self) -> str:
        return f"<PipelineExtractedData role={self.source_role} method={self.extraction_method}>"
