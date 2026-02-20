"""
ValidateBusinessRulesStep — applies insurer-specific business rules.

Rules are configurable per insuree and include things like date range
checks, age validation, sum insured limits, etc.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.core.constants import ValidationStatus
from app.core.logging import get_logger
from app.pipeline.context import PipelineContext, StepResult
from app.pipeline.errors import StepExecutionError
from app.pipeline.step import PipelineStep

logger = get_logger(__name__)


class ValidateBusinessRulesStep(PipelineStep):
    """Run business rule validation on canonical records."""

    name = "validate_business_rules"
    description = "Apply business rules (dates, age, duplicates)"

    async def execute(self, ctx: PipelineContext) -> StepResult:
        started_at = self._now()

        try:
            records = ctx.canonical_records
            if not records:
                return self._success(started_at, metadata={"validated": 0})

            # Load insurer-specific rules config
            rules_config = ctx.insuree_config.get("business_rules", {})
            max_past_days = rules_config.get("max_past_days", 90)
            max_future_days = rules_config.get("max_future_days", 30)
            min_age = rules_config.get("min_age", 0)
            max_age = rules_config.get("max_age", 75)

            blocking_errors = 0
            warnings = 0

            for idx, record in enumerate(records):
                rule_errors = []
                rule_warnings = []

                # ── Rule: effective_date not too old ──
                effective_date = record.get("effective_date")
                if effective_date:
                    try:
                        eff_date = (
                            date.fromisoformat(effective_date)
                            if isinstance(effective_date, str)
                            else effective_date
                        )
                        today = date.today()
                        if (today - eff_date).days > max_past_days:
                            rule_errors.append(
                                f"Effective date {eff_date} is more than {max_past_days} days in the past"
                            )
                        if (eff_date - today).days > max_future_days:
                            rule_warnings.append(
                                f"Effective date {eff_date} is more than {max_future_days} days in the future"
                            )
                    except (ValueError, TypeError):
                        rule_warnings.append(f"Cannot parse effective_date: {effective_date}")

                # ── Rule: member age range ──
                member = record.get("member", {})
                dob = member.get("dob")
                if dob:
                    try:
                        dob_date = (
                            date.fromisoformat(dob)
                            if isinstance(dob, str)
                            else dob
                        )
                        age = (date.today() - dob_date).days // 365
                        if age < min_age or age > max_age:
                            rule_errors.append(
                                f"Member age {age} outside allowed range [{min_age}-{max_age}]"
                            )
                    except (ValueError, TypeError):
                        rule_warnings.append(f"Cannot parse DOB: {dob}")

                # ── TODO: Add more rules ──
                # - sum_insured_in_allowed_range
                # - member_already_active (requires API lookup)
                # - custom insurer-specific rules

                # Update validation results
                if idx < len(ctx.validation_results):
                    ctx.validation_results[idx]["business_errors"] = rule_errors
                    ctx.validation_results[idx]["business_warnings"] = rule_warnings
                    if rule_errors:
                        ctx.validation_results[idx]["business_status"] = ValidationStatus.FAILED
                        blocking_errors += 1
                    elif rule_warnings:
                        ctx.validation_results[idx]["business_status"] = ValidationStatus.WARNING
                        warnings += 1
                    else:
                        ctx.validation_results[idx]["business_status"] = ValidationStatus.PASSED

            logger.info(
                "Business rule validation complete",
                total=len(records),
                blocking_errors=blocking_errors,
                warnings=warnings,
            )

            return self._success(started_at, metadata={
                "total": len(records),
                "blocking_errors": blocking_errors,
                "warnings": warnings,
            })

        except Exception as exc:
            raise StepExecutionError(
                f"Business rule validation failed: {exc}",
                execution_id=ctx.execution_id,
                step_name=self.name,
            ) from exc
