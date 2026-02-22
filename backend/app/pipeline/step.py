"""
PipelineStep — abstract base class for all pipeline steps.

Every step in the processing pipeline inherits from this class.
The engine calls execute() and records timing, logging, and errors
automatically.  Steps only need to implement the business logic.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from app.core.constants import StepStatus
from app.core.logging import get_logger
from app.pipeline.context import PipelineContext, StepMetadata, StepResult
from app.pipeline.errors import StepExecutionError

logger = get_logger(__name__)


class PipelineStep(ABC):
    """
    Base class for every pipeline step.

    Subclasses MUST implement:
        - name (str)          — unique identifier, e.g. "download_file"
        - description (str)   — human-readable label for logs/UI
        - execute(ctx)        — the actual business logic

    Subclasses MAY implement:
        - rollback(ctx)       — cleanup on failure
        - should_skip(ctx)    — return True to skip this step conditionally
    """

    name: str = "unnamed_step"
    description: str = "No description"
    retryable: bool = False
    max_retries: int = 3

    @abstractmethod
    async def execute(self, ctx: PipelineContext) -> StepResult:
        """
        Run the step's logic.  Must return a StepResult.

        Read from and write to `ctx` to pass data between steps.
        Raise StepExecutionError on failure.
        """
        ...

    async def rollback(self, ctx: PipelineContext) -> None:
        """Optional cleanup when this step fails (e.g. delete temp files)."""
        pass

    async def should_skip(self, ctx: PipelineContext) -> bool:
        """Return True to skip this step.  Default: never skip."""
        return False

    # ─── Helpers available to all steps ────────────────

    def _success(
        self,
        started_at: datetime,
        metadata: StepMetadata | dict[str, Any] | None = None,
        output: dict[str, Any] | None = None,
    ) -> StepResult:
        """Build a successful StepResult with timing.

        For backward compatibility, `metadata` can be a raw dict —
        it will be treated as step output, and metadata defaults to StepMetadata().
        """
        now = datetime.now(timezone.utc)
        duration_ms = int((now - started_at).total_seconds() * 1000)

        # Backward compat: raw dict passed as metadata → treat as output
        if isinstance(metadata, dict):
            actual_metadata = StepMetadata()
            actual_output = metadata  # legacy steps pass output as metadata
        else:
            actual_metadata = metadata or StepMetadata()
            actual_output = output or {}

        return StepResult(
            step_name=self.name,
            step_description=self.description,
            status=StepStatus.COMPLETED,
            started_at=started_at,
            completed_at=now,
            duration_ms=duration_ms,
            metadata=actual_metadata,
            output=actual_output,
        )

    def _failure(
        self,
        started_at: datetime,
        error: str,
        metadata: StepMetadata | dict[str, Any] | None = None,
        output: dict[str, Any] | None = None,
    ) -> StepResult:
        """Build a failed StepResult with timing and error message."""
        now = datetime.now(timezone.utc)
        duration_ms = int((now - started_at).total_seconds() * 1000)

        # Backward compat: raw dict passed as metadata → treat as output
        if isinstance(metadata, dict):
            actual_metadata = StepMetadata()
            actual_output = metadata
        else:
            actual_metadata = metadata or StepMetadata()
            actual_output = output or {}

        return StepResult(
            step_name=self.name,
            step_description=self.description,
            status=StepStatus.FAILED,
            started_at=started_at,
            completed_at=now,
            duration_ms=duration_ms,
            error=error,
            metadata=actual_metadata,
            output=actual_output,
        )

    def _now(self) -> datetime:
        """UTC-aware now."""
        return datetime.now(timezone.utc)
