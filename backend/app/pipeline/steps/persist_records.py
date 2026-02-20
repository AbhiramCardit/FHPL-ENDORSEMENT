"""
PersistRecordsStep — saves endorsement records to DB and dispatches tasks.

This is the final common step.  It creates EndorsementRecord rows,
then dispatches Celery tasks for submission or human review routing.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.pipeline.context import PipelineContext, StepResult
from app.pipeline.errors import StepExecutionError
from app.pipeline.step import PipelineStep

logger = get_logger(__name__)


class PersistRecordsStep(PipelineStep):
    """Persist canonical records to DB and dispatch downstream tasks."""

    name = "persist_records"
    description = "Save records to database and dispatch submission/review tasks"

    async def execute(self, ctx: PipelineContext) -> StepResult:
        started_at = self._now()

        try:
            records = ctx.canonical_records
            if not records:
                logger.warning("No records to persist")
                return self._success(started_at, metadata={"persisted": 0})

            # ── Save to DB ────────────────────────────
            # TODO: Replace with actual DB operations
            #
            # Real implementation:
            #   async with async_session() as session:
            #       for idx, record in enumerate(records):
            #           db_record = EndorsementRecord(
            #               file_id=ctx.file_ingestion_id,
            #               insuree_id=ctx.insuree_id,
            #               row_index=idx,
            #               endorsement_type=record["endorsement_type"],
            #               effective_date=record.get("effective_date"),
            #               member_data=record.get("member", {}),
            #               coverage_data=record.get("coverage"),
            #               raw_extracted_json=ctx.raw_extracted[idx] if idx < len(ctx.raw_extracted) else {},
            #               confidence_score=record.get("_confidence", 1.0),
            #               validation_status=...,
            #               review_status=...,
            #           )
            #           session.add(db_record)
            #       await session.flush()

            persisted_count = len(records)
            logger.info(
                "Records persisted (placeholder)",
                count=persisted_count,
            )

            # ── Dispatch downstream tasks ─────────────
            # TODO: Replace with actual Celery task dispatch
            #
            # Real implementation:
            #   for record_id in ctx.records_for_submission:
            #       submit_endorsement.delay(record_id)
            #
            #   for record_id in ctx.records_for_review:
            #       # These go to the human review queue (no task needed)
            #       pass

            logger.info(
                "Downstream tasks dispatched (placeholder)",
                for_submission=len(ctx.records_for_submission),
                for_review=len(ctx.records_for_review),
            )

            return self._success(started_at, metadata={
                "persisted": persisted_count,
                "dispatched_submission": len(ctx.records_for_submission),
                "dispatched_review": len(ctx.records_for_review),
            })

        except Exception as exc:
            raise StepExecutionError(
                f"Record persistence failed: {exc}",
                execution_id=ctx.execution_id,
                step_name=self.name,
            ) from exc
