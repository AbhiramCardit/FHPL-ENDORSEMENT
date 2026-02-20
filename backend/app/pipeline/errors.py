"""
Domain-specific exception hierarchy for the pipeline engine.

All pipeline exceptions inherit from PipelineError so callers can
catch broadly or narrowly as needed.  Each exception carries structured
context (step name, execution ID, etc.) for logging/debugging.
"""

from __future__ import annotations


class PipelineError(Exception):
    """Base exception for all pipeline errors."""

    def __init__(
        self,
        message: str,
        *,
        execution_id: str | None = None,
        step_name: str | None = None,
        details: dict | None = None,
    ) -> None:
        self.execution_id = execution_id
        self.step_name = step_name
        self.details = details or {}
        super().__init__(message)


class StepExecutionError(PipelineError):
    """A step failed during execution."""
    pass


class StepRetryExhaustedError(PipelineError):
    """A retryable step exhausted all retry attempts."""

    def __init__(
        self,
        message: str,
        *,
        attempts: int = 0,
        **kwargs,
    ) -> None:
        self.attempts = attempts
        super().__init__(message, **kwargs)


class FlowResolutionError(PipelineError):
    """Could not resolve the step sequence for a given insurer."""
    pass


class ExtractionError(PipelineError):
    """Data extraction from a document failed."""
    pass


class MappingError(PipelineError):
    """Mapping extracted data to canonical schema failed."""
    pass


class ValidationError(PipelineError):
    """Endorsement record validation failed."""
    pass


class APIRequestError(PipelineError):
    """An intermediate API request within the pipeline failed."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
        **kwargs,
    ) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message, **kwargs)


class StorageError(PipelineError):
    """File storage operation (S3/MinIO) failed."""
    pass
