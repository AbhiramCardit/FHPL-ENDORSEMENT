"""
MapCanonicalStep — maps raw extracted data to the canonical EndorsementRecord schema.

Uses the insuree's extraction_template to translate field names,
apply value mappings, and normalise dates.
"""

from __future__ import annotations

from typing import Any

from app.core.constants import EndorsementType
from app.core.logging import get_logger
from app.pipeline.context import PipelineContext, StepResult
from app.pipeline.errors import MappingError, StepExecutionError
from app.pipeline.step import PipelineStep

logger = get_logger(__name__)

# Default action → canonical EndorsementType mapping
DEFAULT_ACTION_MAP: dict[str, str] = {
    "ADD": EndorsementType.ADD_MEMBER,
    "DEL": EndorsementType.REMOVE_MEMBER,
    "DELETE": EndorsementType.REMOVE_MEMBER,
    "REMOVE": EndorsementType.REMOVE_MEMBER,
    "MOD": EndorsementType.CHANGE_DETAILS,
    "MODIFY": EndorsementType.CHANGE_DETAILS,
    "CHANGE": EndorsementType.CHANGE_DETAILS,
    "SI_CHANGE": EndorsementType.CHANGE_SUM_INSURED,
}


class MapCanonicalStep(PipelineStep):
    """Map raw extracted records to canonical EndorsementRecord schema."""

    name = "map_canonical"
    description = "Map extracted data to canonical endorsement schema"

    async def execute(self, ctx: PipelineContext) -> StepResult:
        started_at = self._now()

        try:
            raw_records = ctx.raw_extracted
            if not raw_records:
                logger.warning("No raw records to map")
                return self._success(started_at, metadata={"records_mapped": 0})

            template = ctx.insuree_config.get("extraction_template", {})

            # Per-role templates: insurer can define different column_mappings
            # for different file roles.
            # Example config:
            #   "extraction_template": {
            #       "column_mappings": {...},         ← default
            #       "role_templates": {
            #           "member_data": { "column_mappings": {...} },
            #           "endorsement_actions": { "column_mappings": {...} },
            #       }
            #   }
            role_templates = template.get("role_templates", {})
            default_column_mappings = template.get("column_mappings", {})
            value_mappings = template.get("value_mappings", {})
            action_map = value_mappings.get("endorsement_type", DEFAULT_ACTION_MAP)

            canonical = []
            role_counts: dict[str, int] = {}

            for idx, raw in enumerate(raw_records):
                try:
                    # Use role-specific template if available
                    source_role = raw.get("_source_role", "primary")
                    role_tmpl = role_templates.get(source_role, {})
                    column_mappings = role_tmpl.get("column_mappings", default_column_mappings)

                    record = self._map_single_record(raw, column_mappings, action_map, idx)
                    record["_source_role"] = source_role
                    canonical.append(record)
                    role_counts[source_role] = role_counts.get(source_role, 0) + 1
                except Exception as exc:
                    logger.warning(
                        "Failed to map record, skipping",
                        row_index=idx,
                        source_role=raw.get("_source_role"),
                        error=str(exc),
                    )
                    ctx.add_error(f"Row {idx}: mapping failed — {exc}")

            ctx.canonical_records = canonical

            logger.info(
                "Canonical mapping complete",
                input_records=len(raw_records),
                mapped_records=len(canonical),
                skipped=len(raw_records) - len(canonical),
                by_role=role_counts,
            )

            return self._success(started_at, metadata={
                "input_records": len(raw_records),
                "mapped_records": len(canonical),
                "skipped": len(raw_records) - len(canonical),
                "by_role": role_counts,
            })

        except Exception as exc:
            raise StepExecutionError(
                f"Canonical mapping failed: {exc}",
                execution_id=ctx.execution_id,
                step_name=self.name,
            ) from exc

    def _map_single_record(
        self,
        raw: dict[str, Any],
        column_mappings: dict[str, str],
        action_map: dict[str, str],
        row_index: int,
    ) -> dict[str, Any]:
        """
        Map a single raw record to canonical format.

        If column_mappings is provided (template-driven), use it.
        Otherwise fall back to best-effort field matching.
        """
        # ── Apply column mappings if available ────────
        if column_mappings:
            mapped = {}
            for source_col, target_path in column_mappings.items():
                if source_col in raw:
                    self._set_nested(mapped, target_path, raw[source_col])
        else:
            # Best-effort: use raw keys directly
            mapped = dict(raw)

        # ── Normalise endorsement_type ────────────────
        raw_action = (
            mapped.get("endorsement_type")
            or mapped.get("action")
            or raw.get("action")
            or ""
        )
        mapped["endorsement_type"] = action_map.get(
            str(raw_action).upper().strip(),
            EndorsementType.CHANGE_DETAILS,
        )

        # ── Ensure member sub-object ──────────────────
        if "member" not in mapped:
            mapped["member"] = {
                "name": mapped.pop("name", raw.get("name", "")),
                "employee_id": mapped.pop("employee_id", raw.get("employee_id")),
                "dob": mapped.pop("dob", raw.get("dob")),
                "gender": mapped.pop("gender", raw.get("gender")),
                "relationship": mapped.pop("relationship", raw.get("relationship")),
            }

        # ── Attach row metadata ───────────────────────
        mapped["_row_index"] = row_index
        mapped["_confidence"] = raw.get("_confidence", 1.0)

        return mapped

    @staticmethod
    def _set_nested(d: dict, path: str, value: Any) -> None:
        """Set a nested dict value using dot-notation path (e.g. 'member.name')."""
        keys = path.split(".")
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value
