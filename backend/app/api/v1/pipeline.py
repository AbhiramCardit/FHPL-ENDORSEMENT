"""
Pipeline management endpoints — trigger, list, and detail views.
"""

from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.db.models.pipeline_run import PipelineRun
from app.db.models.pipeline_step_log import PipelineStepLog
from app.db.models.pipeline_file import PipelineFile
from app.db.models.pipeline_extracted_data import PipelineExtractedData

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


# ─── Trigger ──────────────────────────────────────────────
@router.post("/trigger")
async def trigger_pipeline(db: AsyncSession = Depends(get_db)):
    """
    Trigger the ABHI pipeline.

    1. Creates a PipelineRun row with status=PENDING (visible immediately)
    2. Dispatches a Celery task (worker updates to RUNNING → COMPLETED/FAILED)
    3. Returns instantly with the run_id
    """
    from app.tasks.processing_tasks import process_file
    from app.pipeline.insurers.abhi import ABHI_CONFIG

    test_dir = "/app/test_files"

    # ── Step 1: Create PENDING run in DB ──────────────────
    run = PipelineRun(
        insurer_code=ABHI_CONFIG.get("code", "ABHI"),
        insurer_name=ABHI_CONFIG.get("name", "Aditya Birla Health Insurance"),
        status="PENDING",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    await db.flush()  # get run.id
    run_id = str(run.id)

    # ── Step 2: Dispatch to Celery ────────────────────────
    task = process_file.delay(
        file_ingestion_id=run_id,   # use the DB run_id as execution_id
        insuree_id="abhi-insuree-001",
        insuree_config=ABHI_CONFIG,
        files=[
            {"file_id": "abhi-f1", "filename": "Annexure.xls", "role": "endorsement_data", "s3_key": f"{test_dir}/Annexure.xls"},
            {"file_id": "abhi-f2", "filename": "Schedule.pdf", "role": "endorsement_pdf", "s3_key": f"{test_dir}/Schedule.pdf"},
        ],
    )

    # Commit happens automatically via get_db dependency
    return {
        "message": "Pipeline queued",
        "run_id": run_id,
        "celery_task_id": task.id,
        "status": "PENDING",
    }


# ─── List Runs ────────────────────────────────────────────
@router.get("/runs")
async def list_pipeline_runs(
    insurer_code: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List pipeline runs with optional filters."""
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
                "id": str(r.id),
                "insurer_code": r.insurer_code,
                "insurer_name": r.insurer_name,
                "status": r.status,
                "total_steps": r.total_steps,
                "steps_completed": r.steps_completed,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                "duration_ms": r.duration_ms,
                "error_message": r.error_message,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ],
        "total": len(runs),
    }


# ─── Run Detail ───────────────────────────────────────────
@router.get("/runs/{run_id}")
async def get_pipeline_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get full detail: run + steps + files + extracted data."""
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

    if not run:
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
        # ── Steps ──
        "steps": [
            {
                "id": str(s.id),
                "step_index": s.step_index,
                "step_name": s.step_name,
                "step_description": s.step_description,
                "status": s.status,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "duration_ms": s.duration_ms,
                "error_message": s.error_message,
                "metadata": s.metadata_,
                "retry_count": s.retry_count,
            }
            for s in sorted(run.step_logs, key=lambda x: x.step_index)
        ],
        # ── Files ──
        "files": [
            {
                "id": str(f.id),
                "file_id": f.file_id,
                "filename": f.filename,
                "role": f.role,
                "detected_format": f.detected_format,
                "record_count": f.record_count,
                "status": f.status,
                "error_message": f.error_message,
            }
            for f in run.files
        ],
        # ── Extracted Data ──
        "extracted_data": [
            {
                "id": str(ed.id),
                "source_role": ed.source_role,
                "extraction_method": ed.extraction_method,
                "llm_model": ed.llm_model,
                "raw_data": ed.raw_data,
                "data": ed.data,
                "created_at": ed.created_at.isoformat() if ed.created_at else None,
            }
            for ed in run.extracted_data
        ],
    }
