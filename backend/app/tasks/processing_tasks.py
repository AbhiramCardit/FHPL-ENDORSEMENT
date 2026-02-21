"""
Celery tasks — document processing pipeline.

Wires the PipelineEngine into the Celery task system.
Each file ingestion record gets processed through the full pipeline.
"""

import asyncio
import json

import structlog

from app.tasks import celery_app
from app.core.constants import PipelineStatus
from app.pipeline.engine import PipelineEngine, PipelineResult
from app.pipeline.flow_resolver import FlowResolver

logger = structlog.get_logger("tasks.processing")


def _update_run_status_sync(run_id: str, status: str):
    """Update a PipelineRun's status using a blocking sync call (for Celery)."""
    asyncio.run(_update_run_status(run_id, status))


async def _update_run_status(run_id: str, status: str):
    """Update PipelineRun status in the DB (fresh engine to avoid loop conflicts)."""
    import uuid as uuid_mod
    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from app.core.config import settings
    from app.db.models.pipeline_run import PipelineRun

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as session:
            async with session.begin():
                await session.execute(
                    update(PipelineRun)
                    .where(PipelineRun.id == uuid_mod.UUID(run_id))
                    .values(status=status)
                )
    finally:
        await engine.dispose()


@celery_app.task(bind=True, name="app.tasks.processing_tasks.process_file")
def process_file(
    self,
    file_ingestion_id: str,
    insuree_id: str | None = None,
    insuree_config: dict | None = None,
    files: list[dict] | None = None,
):
    """
    Process a downloaded file through the full pipeline.

    file_ingestion_id is now the PipelineRun UUID (created by the trigger endpoint).
    This task updates status: PENDING → RUNNING → COMPLETED/FAILED.
    """
    task_log = logger.bind(
        task_id=self.request.id,
        run_id=file_ingestion_id,
        insuree_id=insuree_id,
    )

    task_log.info("Processing task started, setting status to RUNNING")

    # ── Mark as RUNNING ──────────────────────────
    try:
        _update_run_status_sync(file_ingestion_id, "RUNNING")
    except Exception as exc:
        task_log.warning("Failed to set RUNNING status (non-fatal)", error=str(exc))

    try:
        if insuree_config is None:
            insuree_config = {
                "code": "DEFAULT",
                "format_type": None,
                "extraction_template": {},
                "min_confidence": 0.80,
                "business_rules": {},
            }

        # Run the async pipeline engine in sync Celery context
        engine = PipelineEngine(flow_resolver=FlowResolver())
        result: PipelineResult = asyncio.run(
            engine.run(
                file_ingestion_id=file_ingestion_id,
                insuree_id=insuree_id,
                insuree_config=insuree_config,
                files=files,
            )
        )

        task_log.info(
            "Processing task finished",
            pipeline_status=result.status,
            steps_completed=result.steps_completed,
            total_steps=result.total_steps,
            duration_ms=result.total_duration_ms,
        )

        return {
            "execution_id": result.execution_id,
            "status": result.status,
            "steps_completed": result.steps_completed,
            "total_steps": result.total_steps,
            "duration_ms": result.total_duration_ms,
        }

    except Exception as exc:
        # Mark as FAILED if the task itself crashes
        task_log.exception("Processing task failed", error=str(exc))
        try:
            _update_run_status_sync(file_ingestion_id, "FAILED")
        except Exception:
            pass
        raise
