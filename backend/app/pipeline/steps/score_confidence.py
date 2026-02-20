"""
ScoreConfidenceStep — scores extraction confidence and routes records.

Records above the confidence threshold → auto-submit queue.
Records below → human review queue.
Records with blocking validation errors → also flagged for review.
"""

from __future__ import annotations

from typing import Any

from app.core.constants import ValidationStatus
from app.core.logging import get_logger
from app.pipeline.context import PipelineContext, StepResult
from app.pipeline.errors import StepExecutionError
from app.pipeline.step import PipelineStep

logger = get_logger(__name__)

DEFAULT_MIN_CONFIDENCE = 0.80


class ScoreConfidenceStep(PipelineStep):
    """Score confidence and route records to submit or review queues."""

    name = "score_confidence"
    description = "Score extraction confidence and route records"

    async def execute(self, ctx: PipelineContext) -> StepResult:
        started_at = self._now()

        try:
            records = ctx.canonical_records
            if not records:
                return self._success(started_at, metadata={"routed": 0})

            min_confidence = ctx.insuree_config.get(
                "min_confidence", DEFAULT_MIN_CONFIDENCE
            )

            for_submission: list[str] = []
            for_review: list[str] = []

            for idx, record in enumerate(records):
                confidence = record.get("_confidence", 1.0)
                record_id = f"{ctx.execution_id}:{idx}"

                # Check validation results for blocking errors
                has_blocking = False
                if idx < len(ctx.validation_results):
                    vr = ctx.validation_results[idx]
                    has_blocking = bool(vr.get("schema_errors")) or bool(
                        vr.get("business_errors")
                    )
                    has_duplicates = bool(vr.get("duplicate_flags"))
                else:
                    has_duplicates = False

                needs_review = (
                    confidence < min_confidence
                    or has_blocking
                    or has_duplicates
                )

                if needs_review:
                    for_review.append(record_id)
                    reason = []
                    if confidence < min_confidence:
                        reason.append(f"low_confidence ({confidence:.2f})")
                    if has_blocking:
                        reason.append("blocking_errors")
                    if has_duplicates:
                        reason.append("duplicates")
                    logger.info(
                        "Record routed to review",
                        row_index=idx,
                        reason=", ".join(reason),
                    )
                else:
                    for_submission.append(record_id)

            ctx.records_for_submission = for_submission
            ctx.records_for_review = for_review

            logger.info(
                "Routing complete",
                total=len(records),
                auto_submit=len(for_submission),
                human_review=len(for_review),
                min_confidence=min_confidence,
            )

            return self._success(started_at, metadata={
                "total": len(records),
                "auto_submit": len(for_submission),
                "human_review": len(for_review),
            })

        except Exception as exc:
            raise StepExecutionError(
                f"Confidence scoring failed: {exc}",
                execution_id=ctx.execution_id,
                step_name=self.name,
            ) from exc
