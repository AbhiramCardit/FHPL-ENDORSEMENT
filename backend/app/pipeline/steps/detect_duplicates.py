"""
DetectDuplicatesStep — within-file and cross-file duplicate detection.

Uses a composite key to identify potential duplicates.
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.pipeline.context import PipelineContext, StepResult
from app.pipeline.errors import StepExecutionError
from app.pipeline.step import PipelineStep

logger = get_logger(__name__)


class DetectDuplicatesStep(PipelineStep):
    """Detect duplicate endorsement records within and across files."""

    name = "detect_duplicates"
    description = "Detect duplicate records within file and against recent submissions"

    async def execute(self, ctx: PipelineContext) -> StepResult:
        started_at = self._now()

        try:
            records = ctx.canonical_records
            if not records:
                return self._success(started_at, metadata={"duplicates_found": 0})

            # ── Within-file duplicate check ───────────
            seen_keys: set[str] = set()
            within_file_dupes = 0

            for idx, record in enumerate(records):
                composite_key = self._build_composite_key(record, ctx.insuree_id)

                if composite_key in seen_keys:
                    within_file_dupes += 1
                    if idx < len(ctx.validation_results):
                        ctx.validation_results[idx].setdefault("duplicate_flags", [])
                        ctx.validation_results[idx]["duplicate_flags"].append("DUPLICATE_IN_FILE")
                    logger.warning(
                        "Duplicate within file",
                        row_index=idx,
                        composite_key=composite_key,
                    )
                else:
                    seen_keys.add(composite_key)

            # ── Cross-file duplicate check (DB) ───────
            # TODO: Query DB for recent submissions (last 30 days)
            #   matching the same composite keys.
            #
            # Real implementation:
            #   recent_keys = await endorsement_repo.get_recent_composite_keys(
            #       insuree_id=ctx.insuree_id,
            #       days=30,
            #   )
            #   for idx, record in enumerate(records):
            #       key = self._build_composite_key(record, ctx.insuree_id)
            #       if key in recent_keys:
            #           ctx.validation_results[idx]["duplicate_flags"].append("POSSIBLE_DUPLICATE")

            cross_file_dupes = 0  # placeholder

            logger.info(
                "Duplicate detection complete",
                within_file=within_file_dupes,
                cross_file=cross_file_dupes,
            )

            return self._success(started_at, metadata={
                "within_file_duplicates": within_file_dupes,
                "cross_file_duplicates": cross_file_dupes,
            })

        except Exception as exc:
            raise StepExecutionError(
                f"Duplicate detection failed: {exc}",
                execution_id=ctx.execution_id,
                step_name=self.name,
            ) from exc

    @staticmethod
    def _build_composite_key(record: dict[str, Any], insuree_id: str) -> str:
        """Build a composite dedup key from record fields."""
        member = record.get("member", {}) or {}
        name = (member.get("name") or "").lower().strip()
        parts = [
            insuree_id or "",
            member.get("employee_id") or "",
            record.get("endorsement_type") or "",
            str(record.get("effective_date") or ""),
            name,
        ]
        return "|".join(parts)
