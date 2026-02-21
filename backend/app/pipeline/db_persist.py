"""
Pipeline DB persistence — saves pipeline execution results to the database.

Called by PipelineEngine after a run completes. Now UPDATES the existing
PipelineRun row (created as PENDING by the trigger endpoint) rather than
creating a new one.

Uses a FRESH engine per call to avoid event loop conflicts when called
from Celery workers (which use asyncio.run() in a sync context).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.logging import get_logger
from app.core.config import settings
from app.db.models.pipeline_run import PipelineRun
from app.db.models.pipeline_step_log import PipelineStepLog
from app.db.models.pipeline_file import PipelineFile
from app.db.models.pipeline_extracted_data import PipelineExtractedData

logger = get_logger(__name__)


def _parse_dt(value):
    """Convert ISO-format string to datetime, passthrough datetime/None."""
    if value is None:
        return None
    if isinstance(value, str):
        from datetime import datetime
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    return value  # already a datetime


def _make_session():
    """Create a fresh async engine + session (avoids event loop conflicts in Celery)."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return factory, engine


async def persist_pipeline_result(
    execution_id: str,
    status: str,
    insurer_code: str,
    insurer_name: str,
    config_snapshot: dict[str, Any],
    started_at,
    completed_at,
    duration_ms: int,
    total_steps: int,
    steps_completed: int,
    error_message: str | None,
    step_results: list[dict[str, Any]],
    files: list | None = None,
    extracted_by_role: dict[str, list[dict]] | None = None,
    context_summary: dict[str, Any] | None = None,
) -> str | None:
    """
    Persist a full pipeline execution to the database.

    If a PipelineRun with matching UUID exists (created as PENDING by trigger),
    UPDATE it. Otherwise CREATE a new row (for backward compat with demo scripts).
    """
    session_factory = None
    engine = None
    try:
        import uuid as uuid_mod
        from sqlalchemy import select as sa_select

        session_factory, engine = _make_session()

        async with session_factory() as session:
            async with session.begin():
                # ── Try to find existing PENDING/RUNNING row ──
                existing_run = None
                try:
                    run_uuid = uuid_mod.UUID(execution_id)
                    result = await session.execute(
                        sa_select(PipelineRun).where(PipelineRun.id == run_uuid)
                    )
                    existing_run = result.scalar_one_or_none()
                except (ValueError, AttributeError):
                    pass  # execution_id is not a UUID — create new

                if existing_run:
                    # ── UPDATE existing row ────────────────────
                    existing_run.status = status
                    existing_run.total_steps = total_steps
                    existing_run.steps_completed = steps_completed
                    existing_run.started_at = _parse_dt(started_at) or existing_run.started_at
                    existing_run.completed_at = _parse_dt(completed_at)
                    existing_run.duration_ms = duration_ms
                    existing_run.error_message = error_message
                    existing_run.config_snapshot = config_snapshot
                    existing_run.context_summary = context_summary or {}
                    run_id = existing_run.id
                else:
                    # ── CREATE new row (demo/scripts) ──────────
                    run = PipelineRun(
                        insurer_code=insurer_code,
                        insurer_name=insurer_name,
                        status=status,
                        total_steps=total_steps,
                        steps_completed=steps_completed,
                        started_at=_parse_dt(started_at),
                        completed_at=_parse_dt(completed_at),
                        duration_ms=duration_ms,
                        error_message=error_message,
                        config_snapshot=config_snapshot,
                        context_summary=context_summary or {},
                    )
                    session.add(run)
                    await session.flush()
                    run_id = run.id

                # ── PipelineStepLogs ──────────────────────
                for sr in step_results:
                    step_log = PipelineStepLog(
                        run_id=run_id,
                        step_index=sr.get("step_index", 0),
                        step_name=sr.get("step_name", "unknown"),
                        step_description=sr.get("step_description", ""),
                        status=sr.get("status", "UNKNOWN"),
                        started_at=_parse_dt(sr.get("started_at")),
                        completed_at=_parse_dt(sr.get("completed_at")),
                        duration_ms=sr.get("duration_ms", 0),
                        error_message=sr.get("error"),
                        metadata_=sr.get("metadata", {}),
                        retry_count=sr.get("retry_count", 0),
                    )
                    session.add(step_log)

                # ── PipelineFiles ─────────────────────────
                file_db_map = {}

                if files:
                    for fi in files:
                        pf = PipelineFile(
                            run_id=run_id,
                            file_id=fi.get("file_id", ""),
                            filename=fi.get("filename", ""),
                            role=fi.get("role", "primary"),
                            detected_format=fi.get("detected_format"),
                            s3_key=fi.get("s3_key"),
                            local_path=fi.get("local_path"),
                            record_count=fi.get("record_count", 0),
                            status="OK" if not fi.get("error") else "FAILED",
                            error_message=fi.get("error"),
                        )
                        session.add(pf)
                        await session.flush()
                        file_db_map[fi.get("role", "primary")] = pf.id

                # ── PipelineExtractedData ─────────────────
                if extracted_by_role:
                    for role, records in extracted_by_role.items():
                        if not records:
                            continue
                        first = records[0] if records else {}
                        method = first.get("_extraction_method", "xls_extractor")
                        model = first.get("_llm_model")

                        ed = PipelineExtractedData(
                            run_id=run_id,
                            file_id=file_db_map.get(role),
                            source_role=role,
                            extraction_method=method,
                            llm_model=model,
                            data=records,
                        )
                        session.add(ed)

        logger.info(
            "Pipeline result persisted to DB",
            run_id=str(run_id),
            insurer_code=insurer_code,
            status=status,
            steps=steps_completed,
            files=len(files) if files else 0,
            mode="update" if existing_run else "create",
        )
        return str(run_id)

    except Exception as exc:
        logger.error(
            "Failed to persist pipeline result to DB (non-fatal)",
            error=str(exc),
        )
        return None
    finally:
        if engine:
            await engine.dispose()
