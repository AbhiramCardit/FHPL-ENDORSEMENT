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

    Steps (handled by PipelineEngine):
        1. Download file from S3/MinIO
        2. Detect format (CSV, XLSX, PDF, etc.)
        3. Run appropriate extractor
        4. Map to canonical EndorsementRecord schema
        5. Schema + business rule validation
        6. Duplicate detection
        7. Confidence scoring & routing
        8. Persist records to DB & dispatch downstream tasks

    Args:
        file_ingestion_id: UUID of the FileIngestionRecord to process.
        insuree_id: UUID of the insuree (optional, loaded from DB if absent).
        insuree_config: Dict of insuree configuration (optional, loaded from DB).
    """
    task_log = logger.bind(
        task_id=self.request.id,
        file_ingestion_id=file_ingestion_id,
        insuree_id=insuree_id,
    )

    task_log.info("Processing task started")

    try:
        # TODO: Load insuree_config from DB if not provided
        #   async with async_session() as session:
        #       file_record = await file_repo.get(session, file_ingestion_id)
        #       config = await insuree_repo.get_config(session, file_record.insuree_id)
        #       insuree_config = config.to_dict()

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

        # TODO: Update FileIngestionRecord status in DB
        #   async with async_session() as session:
        #       await file_repo.update_status(
        #           session, file_ingestion_id,
        #           status="PROCESSED" if result.status == PipelineStatus.COMPLETED else "FAILED",
        #           record_count=result.context_summary.get("records_canonical", 0),
        #           error_message=result.error,
        #       )

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
        task_log.exception("Processing task failed", error=str(exc))
        raise
