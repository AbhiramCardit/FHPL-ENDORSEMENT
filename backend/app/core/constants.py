"""Shared constants and enums used across the application."""

from enum import StrEnum


class UserRole(StrEnum):
    """Application roles for authenticated dashboard users."""

    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


class PipelineStatus(StrEnum):
    """Overall status of a pipeline execution."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"


class StepStatus(StrEnum):
    """Status of an individual pipeline step."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    RETRYING = "RETRYING"


class FileFormat(StrEnum):
    """Detected file format types."""

    STRUCTURED_CSV = "STRUCTURED_CSV"
    STRUCTURED_XLSX = "STRUCTURED_XLSX"
    SEMI_STRUCTURED_PDF = "SEMI_STRUCTURED_PDF"
    UNSTRUCTURED_PDF = "UNSTRUCTURED_PDF"
    SCANNED_IMAGE = "SCANNED_IMAGE"
    UNSTRUCTURED_DOCX = "UNSTRUCTURED_DOCX"


class FileIngestionStatus(StrEnum):
    """Status of a file through the ingestion lifecycle."""

    DOWNLOADED = "DOWNLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class EndorsementType(StrEnum):
    """Types of endorsement actions."""

    ADD_MEMBER = "ADD_MEMBER"
    REMOVE_MEMBER = "REMOVE_MEMBER"
    CHANGE_DETAILS = "CHANGE_DETAILS"
    CHANGE_SUM_INSURED = "CHANGE_SUM_INSURED"


class ValidationStatus(StrEnum):
    """Validation result for an endorsement record."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"


class ReviewStatus(StrEnum):
    """Human review status."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class SubmissionStatus(StrEnum):
    """TPA submission lifecycle status."""

    QUEUED = "QUEUED_FOR_SUBMISSION"
    IN_PROGRESS = "SUBMISSION_IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "TPA_ACKNOWLEDGED"
    FAILED = "SUBMISSION_FAILED"
    FAILED_FINAL = "SUBMISSION_FAILED_FINAL"


class APIRequestMethod(StrEnum):
    """HTTP methods used in pipeline API steps."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"
