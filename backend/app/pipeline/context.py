"""
PipelineContext — mutable state object carried through every step.

This is the single source of truth for a pipeline run.  Each step
reads from and writes to the context.  The engine serialises the
final context to the execution log for auditability.

Supports MULTI-FILE batches: a single pipeline run can process
multiple documents (XLSX, CSV, PDF, DOCX) from one insurer.
Each file is tracked via FileInfo with a "role" label so downstream
steps know which extracted data to use.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


# ═══════════════════════════════════════════════════════════
#  FileInfo — per-file metadata within a batch
# ═══════════════════════════════════════════════════════════

@dataclass
class FileInfo:
    """
    Metadata for a single file within a multi-file batch.

    Args:
        file_id: Unique ID (FileIngestionRecord UUID).
        filename: Original filename from SFTP.
        role: Logical role of this file in the batch, e.g.
              "member_data", "endorsement_actions", "policy_details".
              Configured per insurer.  Used as the key in
              ctx.raw_extracted_by_role.
        s3_key: Object storage key for the raw file.
        local_path: Local temp path after download.
        detected_format: FileFormat enum value after detection.
        record_count: Number of records extracted from this file.
        error: Error message if processing this file failed.
    """

    file_id: str
    filename: str
    role: str = "primary"
    s3_key: str | None = None
    local_path: str | None = None
    detected_format: str | None = None
    record_count: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise for JSONB storage."""
        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "role": self.role,
            "s3_key": self.s3_key,
            "local_path": self.local_path,
            "detected_format": self.detected_format,
            "record_count": self.record_count,
            "error": self.error,
        }


# ═══════════════════════════════════════════════════════════
#  StepMetadata — standardised metrics every step reports
# ═══════════════════════════════════════════════════════════

@dataclass
class StepMetadata:
    """
    Standard metadata that every step reports.

    These fields are the SAME for all steps, enabling consistent
    querying, comparison across runs, and dashboard aggregation.
    """

    files_processed: int = 0
    records_processed: int = 0
    extraction_method: str | None = None    # "xls_extractor", "llm", etc.
    llm_model: str | None = None            # "gemini-2.5-flash-lite", etc.
    retry_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialise — omits None/zero values for clean storage."""
        result: dict[str, Any] = {}
        if self.files_processed:
            result["files_processed"] = self.files_processed
        if self.records_processed:
            result["records_processed"] = self.records_processed
        if self.extraction_method:
            result["extraction_method"] = self.extraction_method
        if self.llm_model:
            result["llm_model"] = self.llm_model
        if self.retry_count:
            result["retry_count"] = self.retry_count
        return result


# ═══════════════════════════════════════════════════════════
#  StepResult
# ═══════════════════════════════════════════════════════════

@dataclass
class StepResult:
    """
    Outcome of a single pipeline step execution.

    - metadata: Standardised StepMetadata (same structure for all steps)
    - output:   Step-specific custom data (varies per step type)
    """

    step_name: str
    step_description: str = ""
    status: str = ""

    # ── Timing ──
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int = 0

    # ── Error ──
    error: str | None = None

    # ── Standard metadata (same keys for ALL steps) ──
    metadata: StepMetadata = field(default_factory=StepMetadata)

    # ── Step-specific output (varies per step) ──
    output: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise for JSONB storage."""
        return {
            "step_name": self.step_name,
            "step_description": self.step_description,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "metadata": self.metadata.to_dict() if isinstance(self.metadata, StepMetadata) else self.metadata,
            "output": self.output,
        }


# ═══════════════════════════════════════════════════════════
#  PipelineContext
# ═══════════════════════════════════════════════════════════

@dataclass
class PipelineContext:
    """
    Carries all state between pipeline steps.

    Supports both single-file and multi-file (batch) pipelines.
    For multi-file batches, each file has a "role" label and its
    extracted data is stored separately in raw_extracted_by_role.

    Populated progressively — early steps fill in file data,
    later steps fill in extracted records and validation results.
    """

    # ─── Identity (set at init) ────────────────────────
    file_ingestion_id: str              # primary file ID (or batch ID)
    insuree_id: str
    execution_id: str = field(default=None)  # type: ignore[assignment]

    # ─── Insuree config (loaded by engine before first step) ──
    insuree_config: dict[str, Any] = field(default_factory=dict)
    insuree_code: str = ""

    def __post_init__(self):
        # Use file_ingestion_id as execution_id (matches the DB PipelineRun row)
        # Fall back to generating a new UUID for demo/test scripts
        if self.execution_id is None:
            self.execution_id = self.file_ingestion_id or str(uuid.uuid4())

    # ─── Multi-file batch ─────────────────────────────
    # List of ALL files in this batch.  For single-file runs,
    # this will contain just one FileInfo entry.
    files: list[FileInfo] = field(default_factory=list)

    # ─── Backward-compat single-file shortcuts ────────
    # These point to the "primary" file (first in the list).
    # Steps can use these for simple single-file flows.
    local_filepath: str | None = None
    s3_key: str | None = None
    filename: str | None = None
    detected_format: str | None = None

    # ─── Extraction results ───────────────────────────
    #
    # raw_extracted_by_role:
    #   Keyed by file role.  Each value is a list of CLEAN record
    #   dicts — no internal tracking keys (no _source_file etc).
    #   Example:
    #     {
    #       "endorsement_data":  [{"Sr.NO": 1, "Name": "John", ...}, ...],
    #       "endorsement_pdf":   [{"name": "Jane", "action": "ADD", ...}, ...],
    #     }
    #
    # extraction_metadata_by_role:
    #   Full extraction output per role — includes wrapper info like
    #   title, header, summary that is NOT part of the records.
    #   Example:
    #     {
    #       "endorsement_data": {
    #         "title": "Group Endorsement - ...",
    #         "header": {"Policy Number": "...", ...},
    #         "summary": {"Premium": 0, ...},
    #       },
    #     }
    #
    # raw_extracted:
    #   Flat list of ALL raw records across all files (merged).
    #   Kept for backward-compat with single-file flows.

    raw_extracted_by_role: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    extraction_metadata_by_role: dict[str, dict[str, Any]] = field(default_factory=dict)
    raw_extracted: list[dict[str, Any]] = field(default_factory=list)
    canonical_records: list[dict[str, Any]] = field(default_factory=list)

    # ─── Validation (populated by validation steps) ──
    validation_results: list[dict[str, Any]] = field(default_factory=list)
    records_for_review: list[str] = field(default_factory=list)
    records_for_submission: list[str] = field(default_factory=list)

    # ─── API responses (populated by intermediate API steps) ──
    api_responses: dict[str, Any] = field(default_factory=dict)

    # ─── Execution tracking ────────────────────────────
    current_step_index: int = 0
    total_steps: int = 0
    step_results: list[StepResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    # ─── Arbitrary step-to-step data ───────────────────
    extra: dict[str, Any] = field(default_factory=dict)

    # ─── File helpers ──────────────────────────────────

    @property
    def is_batch(self) -> bool:
        """True if this context has multiple files."""
        return len(self.files) > 1

    @property
    def primary_file(self) -> FileInfo | None:
        """Return the first / primary file in the batch."""
        return self.files[0] if self.files else None

    def get_file_by_role(self, role: str) -> FileInfo | None:
        """Find a file by its role label."""
        for f in self.files:
            if f.role == role:
                return f
        return None

    def get_files_by_role(self, role: str) -> list[FileInfo]:
        """Find all files matching a role (if duplicates exist)."""
        return [f for f in self.files if f.role == role]

    def get_extracted_for_role(self, role: str) -> list[dict[str, Any]]:
        """Get the raw extracted records for a specific file role."""
        return self.raw_extracted_by_role.get(role, [])

    def add_file(self, file_info: FileInfo) -> None:
        """Add a file to the batch."""
        self.files.append(file_info)
        # Update single-file shortcuts for the primary file
        if len(self.files) == 1:
            self.local_filepath = file_info.local_path
            self.s3_key = file_info.s3_key
            self.filename = file_info.filename
            self.detected_format = file_info.detected_format

    def merge_extracted_to_flat(self) -> None:
        """
        Merge all per-role extracted data into the flat raw_extracted list.
        Called after all files have been extracted.
        Each record gets a '_source_role' field so you can trace its origin.
        """
        merged = []
        for role, records in self.raw_extracted_by_role.items():
            for record in records:
                record["_source_role"] = role
                merged.append(record)
        self.raw_extracted = merged

    # ─── General helpers ───────────────────────────────

    def add_error(self, error: str) -> None:
        """Record a non-fatal error."""
        self.errors.append(error)

    def set_extra(self, key: str, value: Any) -> None:
        """Store arbitrary data for downstream steps."""
        self.extra[key] = value

    def get_extra(self, key: str, default: Any = None) -> Any:
        """Retrieve data stored by an upstream step."""
        return self.extra.get(key, default)

    def to_summary_dict(self) -> dict[str, Any]:
        """Compact summary for logging / DB storage."""
        return {
            "execution_id": self.execution_id,
            "file_ingestion_id": self.file_ingestion_id,
            "insuree_id": self.insuree_id,
            "insuree_code": self.insuree_code,
            "is_batch": self.is_batch,
            "files": [f.to_dict() for f in self.files],
            "total_files": len(self.files),
            "extracted_by_role": {
                role: len(records)
                for role, records in self.raw_extracted_by_role.items()
            },
            "records_extracted_total": len(self.raw_extracted),
            "records_canonical": len(self.canonical_records),
            "records_for_review": len(self.records_for_review),
            "records_for_submission": len(self.records_for_submission),
            "steps_completed": len(self.step_results),
            "total_steps": self.total_steps,
            "errors": self.errors,
        }
