"""Pipeline management endpoints for trigger, list, and detail views."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.db.models.pipeline_file import PipelineFile
from app.db.models.pipeline_run import PipelineRun

router = APIRouter(
    prefix="/pipeline",
    tags=["Pipeline"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/trigger")
async def trigger_pipeline(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Trigger the ABHI pipeline and return an immediately-visible run id."""
    from app.pipeline.insurers.abhi import ABHI_CONFIG
    from app.tasks.processing_tasks import process_file

    test_dir = "/app/test_files"

    run = PipelineRun(
        insurer_code=ABHI_CONFIG.get("code", "ABHI"),
        insurer_name=ABHI_CONFIG.get("name", "Aditya Birla Health Insurance"),
        status="PENDING",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()
    run_id = str(run.id)

    task = process_file.delay(
        file_ingestion_id=run_id,
        insuree_id="abhi-insuree-001",
        insuree_config=ABHI_CONFIG,
        files=[
            {
                "file_id": "abhi-f1",
                "filename": "Annexure.xls",
                "role": "endorsement_data",
                "s3_key": f"{test_dir}/Annexure.xls",
            },
            {
                "file_id": "abhi-f2",
                "filename": "Schedule.pdf",
                "role": "endorsement_pdf",
                "s3_key": f"{test_dir}/Schedule.pdf",
            },
        ],
    )

    return {
        "message": "Pipeline queued",
        "run_id": run_id,
        "celery_task_id": task.id,
        "status": "PENDING",
    }


@router.get("/runs")
async def list_pipeline_runs(
    insurer_code: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    """List pipeline runs with optional insurer/status filters."""
    query = select(PipelineRun).order_by(desc(PipelineRun.started_at))

    if insurer_code:
        query = query.where(PipelineRun.insurer_code == insurer_code)
    if status:
        query = query.where(PipelineRun.status == status)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    runs = result.scalars().all()

    return {
        "data": [
            {
                "id": str(run.id),
                "insurer_code": run.insurer_code,
                "insurer_name": run.insurer_name,
                "status": run.status,
                "total_steps": run.total_steps,
                "steps_completed": run.steps_completed,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "duration_ms": run.duration_ms,
                "error_message": run.error_message,
                "created_at": run.created_at.isoformat() if run.created_at else None,
            }
            for run in runs
        ],
        "total": len(runs),
    }


@router.get("/runs/{run_id}")
async def get_pipeline_run(run_id: UUID, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    """Get full run detail including steps, files, and extracted payloads."""
    result = await db.execute(
        select(PipelineRun)
        .where(PipelineRun.id == run_id)
        .options(
            selectinload(PipelineRun.step_logs),
            selectinload(PipelineRun.files).selectinload(PipelineFile.extracted_data),
            selectinload(PipelineRun.extracted_data),
        )
    )
    run = result.scalar_one_or_none()

    if run is None:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    return {
        "id": str(run.id),
        "insurer_code": run.insurer_code,
        "insurer_name": run.insurer_name,
        "status": run.status,
        "total_steps": run.total_steps,
        "steps_completed": run.steps_completed,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "duration_ms": run.duration_ms,
        "error_message": run.error_message,
        "config_snapshot": run.config_snapshot,
        "context_summary": run.context_summary,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        "steps": [
            {
                "id": str(step.id),
                "step_index": step.step_index,
                "step_name": step.step_name,
                "step_description": step.step_description,
                "status": step.status,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                "duration_ms": step.duration_ms,
                "error_message": step.error_message,
                "metadata": step.metadata_,
                "retry_count": step.retry_count,
            }
            for step in sorted(run.step_logs, key=lambda item: item.step_index)
        ],
        "files": [
            {
                "id": str(file_row.id),
                "file_id": file_row.file_id,
                "filename": file_row.filename,
                "role": file_row.role,
                "detected_format": file_row.detected_format,
                "record_count": file_row.record_count,
                "status": file_row.status,
                "error_message": file_row.error_message,
            }
            for file_row in run.files
        ],
        "extracted_data": [
            {
                "id": str(extracted.id),
                "source_role": extracted.source_role,
                "extraction_method": extracted.extraction_method,
                "llm_model": extracted.llm_model,
                "raw_data": extracted.raw_data,
                "data": extracted.data,
                "created_at": extracted.created_at.isoformat() if extracted.created_at else None,
            }
            for extracted in run.extracted_data
        ],
    }
