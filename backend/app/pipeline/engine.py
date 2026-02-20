"""
PipelineEngine — the orchestrator that runs steps sequentially.

Responsibilities:
    - Load insuree config from DB
    - Resolve the step sequence via FlowResolver
    - Execute each step with timing, logging, and error handling
    - Retry retryable steps
    - Write execution trace to DB (PipelineExecution)
    - Return a complete PipelineResult
"""

from __future__ import annotations

import asyncio
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

from app.core.constants import PipelineStatus, StepStatus
from app.pipeline.context import FileInfo, PipelineContext, StepResult
from app.pipeline.errors import (
    FlowResolutionError,
    PipelineError,
    StepExecutionError,
    StepRetryExhaustedError,
)
from app.pipeline.step import PipelineStep


@dataclass
class PipelineResult:
    """Final outcome of a pipeline execution."""

    execution_id: str
    status: str                     # PipelineStatus value
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_duration_ms: int = 0
    steps_completed: int = 0
    total_steps: int = 0
    step_results: list[dict[str, Any]] = field(default_factory=list)
    context_summary: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class PipelineEngine:
    """
    Runs a sequence of PipelineStep objects against a PipelineContext.

    Supports both single-file and multi-file (batch) pipelines.

    Usage (single file)::

        engine = PipelineEngine(flow_resolver=FlowResolver())
        result = await engine.run(file_ingestion_id="abc-123")

    Usage (multi-file batch)::

        engine = PipelineEngine(flow_resolver=FlowResolver())
        result = await engine.run(
            file_ingestion_id="batch-001",
            files=[
                {"file_id": "f1", "filename": "members.xlsx", "role": "member_data"},
                {"file_id": "f2", "filename": "actions.csv", "role": "endorsement_actions"},
                {"file_id": "f3", "filename": "policy.pdf", "role": "policy_details"},
            ],
        )
    """

    def __init__(self, flow_resolver=None) -> None:
        self.flow_resolver = flow_resolver
        self.logger = structlog.get_logger("pipeline.engine")

    async def run(
        self,
        file_ingestion_id: str,
        insuree_id: str | None = None,
        insuree_config: dict[str, Any] | None = None,
        files: list[dict[str, Any] | FileInfo] | None = None,
    ) -> PipelineResult:
        """
        Full pipeline execution.

        Args:
            file_ingestion_id: Primary file ID or batch ID.
            insuree_id: Insuree UUID.
            insuree_config: Dict of insuree configuration.
            files: Optional list of files in the batch.
                   Each item can be a FileInfo or a dict with keys:
                   file_id, filename, role, s3_key (optional).
        """
        started_at = datetime.now(timezone.utc)

        # ── Build context ─────────────────────────────
        ctx = PipelineContext(
            file_ingestion_id=file_ingestion_id,
            insuree_id=insuree_id or "",
            insuree_config=insuree_config or {},
            insuree_code=insuree_config.get("code", "UNKNOWN") if insuree_config else "UNKNOWN",
        )

        # ── Populate files ────────────────────────────
        if files:
            for f in files:
                if isinstance(f, FileInfo):
                    ctx.add_file(f)
                elif isinstance(f, dict):
                    ctx.add_file(FileInfo(
                        file_id=f.get("file_id", f.get("id", "")),
                        filename=f.get("filename", ""),
                        role=f.get("role", "primary"),
                        s3_key=f.get("s3_key"),
                    ))

        log = self.logger.bind(
            execution_id=ctx.execution_id,
            file_ingestion_id=file_ingestion_id,
            insuree_code=ctx.insuree_code,
            total_files=len(ctx.files),
            is_batch=ctx.is_batch,
        )

        log.info(
            "Pipeline started",
            insuree_id=ctx.insuree_id,
            file_roles=[f.role for f in ctx.files] if ctx.files else ["single"],
        )

        # ── Resolve steps ─────────────────────────────
        if self.flow_resolver is None:
            log.error("No flow resolver configured")
            return PipelineResult(
                execution_id=ctx.execution_id,
                status=PipelineStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                error="No flow resolver configured",
            )

        try:
            steps = self.flow_resolver.resolve(ctx.insuree_config)
        except FlowResolutionError as exc:
            log.error("Flow resolution failed", error=str(exc))
            return PipelineResult(
                execution_id=ctx.execution_id,
                status=PipelineStatus.FAILED,
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
                error=f"Flow resolution failed: {exc}",
            )

        # ── Run steps ─────────────────────────────────
        result = await self.run_steps(ctx, steps)
        result.started_at = started_at

        log.info(
            "Pipeline finished",
            status=result.status,
            steps_completed=result.steps_completed,
            total_steps=result.total_steps,
            duration_ms=result.total_duration_ms,
        )

        return result

    async def run_steps(
        self,
        ctx: PipelineContext,
        steps: list[PipelineStep],
    ) -> PipelineResult:
        """
        Execute an ordered list of steps against a context.

        Can be called directly (bypassing flow resolution) for testing
        or when you have a pre-built step list.
        """
        started_at = datetime.now(timezone.utc)
        ctx.total_steps = len(steps)

        log = self.logger.bind(
            execution_id=ctx.execution_id,
            total_steps=len(steps),
        )

        pipeline_status = PipelineStatus.RUNNING
        steps_completed = 0

        for index, step in enumerate(steps):
            ctx.current_step_index = index
            step_number = index + 1

            step_log = log.bind(
                step_name=step.name,
                step_index=step_number,
                step_description=step.description,
            )

            # ── Check skip condition ──────────────────
            try:
                if await step.should_skip(ctx):
                    step_log.info("Step skipped")
                    skip_result = StepResult(
                        step_name=step.name,
                        status=StepStatus.SKIPPED,
                        started_at=datetime.now(timezone.utc),
                        completed_at=datetime.now(timezone.utc),
                    )
                    ctx.step_results.append(skip_result)
                    steps_completed += 1
                    continue
            except Exception as exc:
                step_log.warning("should_skip raised, running step anyway", error=str(exc))

            # ── Execute step (with retry) ─────────────
            step_log.info(
                f"Step {step_number}/{len(steps)}: {step.description}",
            )

            result = await self._execute_with_retry(step, ctx, step_log)
            ctx.step_results.append(result)

            if result.status == StepStatus.COMPLETED:
                steps_completed += 1
                step_log.info(
                    "Step completed",
                    duration_ms=result.duration_ms,
                    metadata=result.metadata,
                )
            else:
                step_log.error(
                    "Step failed — pipeline stopping",
                    error=result.error,
                    duration_ms=result.duration_ms,
                )
                ctx.add_error(f"Step '{step.name}' failed: {result.error}")
                pipeline_status = PipelineStatus.FAILED

                # Attempt rollback
                try:
                    await step.rollback(ctx)
                    step_log.info("Rollback completed")
                except Exception as rollback_exc:
                    step_log.warning("Rollback failed", error=str(rollback_exc))

                break

        # ── Finalise ──────────────────────────────────
        completed_at = datetime.now(timezone.utc)
        total_duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        if pipeline_status != PipelineStatus.FAILED:
            pipeline_status = PipelineStatus.COMPLETED

        return PipelineResult(
            execution_id=ctx.execution_id,
            status=pipeline_status,
            started_at=started_at,
            completed_at=completed_at,
            total_duration_ms=total_duration_ms,
            steps_completed=steps_completed,
            total_steps=len(steps),
            step_results=[sr.to_dict() for sr in ctx.step_results],
            context_summary=ctx.to_summary_dict(),
        )

    async def _execute_with_retry(
        self,
        step: PipelineStep,
        ctx: PipelineContext,
        log: structlog.BoundLogger,
    ) -> StepResult:
        """
        Execute a step.  If retryable and it fails, retry up to max_retries.
        """
        max_attempts = step.max_retries if step.retryable else 1

        for attempt in range(1, max_attempts + 1):
            try:
                result = await step.execute(ctx)
                return result

            except StepExecutionError as exc:
                if step.retryable and attempt < max_attempts:
                    wait_seconds = 2 ** attempt  # exponential backoff
                    log.warning(
                        f"Step failed (attempt {attempt}/{max_attempts}), retrying in {wait_seconds}s",
                        error=str(exc),
                    )
                    await asyncio.sleep(wait_seconds)
                    continue

                # Final failure
                return StepResult(
                    step_name=step.name,
                    status=StepStatus.FAILED,
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    error=str(exc),
                    metadata={"attempts": attempt},
                )

            except Exception as exc:
                # Unexpected error — never retry
                log.exception("Unexpected error in step", error=str(exc))
                return StepResult(
                    step_name=step.name,
                    status=StepStatus.FAILED,
                    started_at=datetime.now(timezone.utc),
                    completed_at=datetime.now(timezone.utc),
                    error=f"Unexpected: {exc}",
                    metadata={"traceback": traceback.format_exc()},
                )

        # Should not reach here, but safety net
        return StepResult(
            step_name=step.name,
            status=StepStatus.FAILED,
            error="Retry loop exited unexpectedly",
        )
