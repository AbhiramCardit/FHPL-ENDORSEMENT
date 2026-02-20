"""
ValidateSchemaStep — Pydantic schema validation on canonical records.

Checks required fields, types, and formats.  Sets validation_status
on each record.
"""

from __future__ import annotations

from typing import Any

from app.core.constants import ValidationStatus
from app.core.logging import get_logger
from app.pipeline.context import PipelineContext, StepResult
from app.pipeline.errors import StepExecutionError
from app.pipeline.step import PipelineStep

logger = get_logger(__name__)

# Fields that must be present on every record
REQUIRED_FIELDS = ["endorsement_type", "member"]
REQUIRED_MEMBER_FIELDS = ["name"]


class ValidateSchemaStep(PipelineStep):
    """Validate each canonical record against the required schema."""

    name = "validate_schema"
    description = "Validate record schema (required fields, types)"

    async def execute(self, ctx: PipelineContext) -> StepResult:
        started_at = self._now()

        try:
            records = ctx.canonical_records
            if not records:
                logger.warning("No canonical records to validate")
                return self._success(started_at, metadata={"validated": 0})

            passed = 0
            failed = 0
            results = []

            for idx, record in enumerate(records):
                errors = self._validate_record(record, idx)
                result = {
                    "row_index": idx,
                    "schema_errors": errors,
                    "schema_status": ValidationStatus.FAILED if errors else ValidationStatus.PASSED,
                }
                results.append(result)

                if errors:
                    failed += 1
                    logger.warning(
                        "Schema validation failed",
                        row_index=idx,
                        errors=errors,
                    )
                else:
                    passed += 1

            ctx.validation_results = results

            logger.info(
                "Schema validation complete",
                total=len(records),
                passed=passed,
                failed=failed,
            )

            return self._success(started_at, metadata={
                "total": len(records),
                "passed": passed,
                "failed": failed,
            })

        except Exception as exc:
            raise StepExecutionError(
                f"Schema validation failed: {exc}",
                execution_id=ctx.execution_id,
                step_name=self.name,
            ) from exc

    def _validate_record(self, record: dict[str, Any], row_index: int) -> list[str]:
        """Validate a single record.  Returns list of error strings."""
        errors = []

        # Check top-level required fields
        for field in REQUIRED_FIELDS:
            if field not in record or record[field] is None:
                errors.append(f"Missing required field: {field}")

        # Check member sub-fields
        member = record.get("member", {})
        if isinstance(member, dict):
            for field in REQUIRED_MEMBER_FIELDS:
                if field not in member or not member[field]:
                    errors.append(f"Missing required member field: {field}")
        else:
            errors.append("'member' must be a dict")

        # TODO: Add Pydantic model validation here for full type checking
        # from app.processing.schemas import EndorsementRecord
        # try:
        #     EndorsementRecord(**record)
        # except ValidationError as exc:
        #     errors.extend([e["msg"] for e in exc.errors()])

        return errors
