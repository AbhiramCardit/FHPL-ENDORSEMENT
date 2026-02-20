"""
FlowResolver — maps insurer configuration to an ordered step sequence.

Each insurer type gets a specific flow (list of PipelineStep instances).
Common steps are shared across all flows; insurer-specific steps are
injected at the correct positions.

Supports multi-file batches: insurer configs define which file roles
to expect (e.g. "member_data" from XLSX, "policy_details" from PDF).
The engine populates ctx.files before the pipeline starts.

To add a new insurer flow:
    1. Create insurer-specific steps in steps/insurer/
    2. Register the flow in FLOW_REGISTRY below
    3. Define file_roles in the insurer config
    4. The engine picks it up automatically
"""

from __future__ import annotations

from typing import Any

from app.core.logging import get_logger
from app.pipeline.errors import FlowResolutionError
from app.pipeline.step import PipelineStep

# ─── Import all steps ─────────────────────────────────
from app.pipeline.steps.download_file import DownloadFileStep
from app.pipeline.steps.detect_format import DetectFormatStep
from app.pipeline.steps.extract_data import ExtractDataStep
from app.pipeline.steps.map_canonical import MapCanonicalStep
from app.pipeline.steps.validate_schema import ValidateSchemaStep
from app.pipeline.steps.validate_business_rules import ValidateBusinessRulesStep
from app.pipeline.steps.detect_duplicates import DetectDuplicatesStep
from app.pipeline.steps.score_confidence import ScoreConfidenceStep
from app.pipeline.steps.persist_records import PersistRecordsStep
from app.pipeline.steps.api_request import APIRequestStep

# ─── Import insurer-specific flows ────────────────────
from app.pipeline.insurers.abhi.flow import abhi_flow

logger = get_logger(__name__)


def _common_pre_steps() -> list[PipelineStep]:
    """Steps that run for EVERY insurer before extraction."""
    return [
        DownloadFileStep(),
        DetectFormatStep(),
    ]


def _common_post_steps() -> list[PipelineStep]:
    """Steps that run for EVERY insurer after extraction + mapping."""
    return [
        ValidateSchemaStep(),
        ValidateBusinessRulesStep(),
        DetectDuplicatesStep(),
        ScoreConfidenceStep(),
        PersistRecordsStep(),
    ]


def _default_flow() -> list[PipelineStep]:
    """
    Default flow — works for both single and multi-file.

    Download ALL files → Detect each format → Extract each →
    Map ALL to canonical → Validate → Score → Persist

    For single-file runs: ctx.files has 1 entry.
    For multi-file runs: ctx.files has N entries, each with a role.
    ExtractDataStep handles both transparently.
    """
    return [
        *_common_pre_steps(),
        ExtractDataStep(),
        MapCanonicalStep(),
        *_common_post_steps(),
    ]


def _example_insurer_a_flow() -> list[PipelineStep]:
    """
    Example: Insurer A — multi-file batch.

    Expected files:
        - member_data (XLSX): employee roster with demographics
        - endorsement_actions (CSV): list of add/remove/modify actions

    After extracting both files, calls member lookup API to enrich
    the data before canonical mapping.
    """
    return [
        *_common_pre_steps(),
        ExtractDataStep(),
        # ── Custom: call insurer A's member lookup API ──
        # Uses data extracted from the "endorsement_actions" role
        APIRequestStep(
            step_name="insurer_a_member_lookup",
            step_description="Call Insurer A member lookup API to enrich records",
            method="POST",
            url_template="{base_url}/api/members/lookup",
            request_builder=lambda ctx: {
                "members": [
                    {"name": r.get("name"), "employee_id": r.get("employee_id")}
                    for r in ctx.get_extracted_for_role("endorsement_actions")
                ],
                "roster_count": len(ctx.get_extracted_for_role("member_data")),
            },
            response_key="member_lookup_response",
            retryable=True,
        ),
        MapCanonicalStep(),
        *_common_post_steps(),
    ]


def _example_insurer_b_flow() -> list[PipelineStep]:
    """
    Example: Insurer B — multi-file batch with multiple API stages.

    Expected files:
        - endorsements (XLSX): main endorsement file
        - policy_details (PDF): policy summary / coverage details
        - approval_letter (DOCX): approval document

    Flow:
        1. Download + detect all files
        2. Fetch policy details from insurer API (uses policy_id from config)
        3. Extract all files
        4. Map (merge data from endorsements + policy PDFs)
        5. Create endorsement request via POST API
        6. Validate + score + persist
    """
    return [
        *_common_pre_steps(),
        # ── Custom: fetch policy details first ──
        APIRequestStep(
            step_name="insurer_b_fetch_policy",
            step_description="Fetch active policy details from Insurer B API",
            method="GET",
            url_template="{base_url}/api/policies/{policy_id}",
            response_key="policy_details_api",
            retryable=True,
        ),
        ExtractDataStep(),
        MapCanonicalStep(),
        # ── Custom: create endorsement batch request via POST ──
        APIRequestStep(
            step_name="insurer_b_create_endorsement",
            step_description="Create endorsement request via Insurer B API",
            method="POST",
            url_template="{base_url}/api/endorsements",
            request_builder=lambda ctx: {
                "policy_id": ctx.get_extra("policy_details_api", {}).get("id"),
                "records": ctx.canonical_records,
                "files_processed": len(ctx.files),
                "approval_data": ctx.get_extracted_for_role("approval_letter"),
            },
            response_key="endorsement_creation_response",
            retryable=True,
        ),
        *_common_post_steps(),
    ]


# ═══════════════════════════════════════════════════════════
#  Flow Registry
# ═══════════════════════════════════════════════════════════
#
#  Maps insuree_code → flow builder function.
#  Add new insurers here.
#

FLOW_REGISTRY: dict[str, callable] = {
    "DEFAULT": _default_flow,
    "INSURER_A": _example_insurer_a_flow,
    "INSURER_B": _example_insurer_b_flow,
    # ─── Real insurers ────────────────────────────
    "ABHI": abhi_flow,
}


class FlowResolver:
    """
    Resolves an insuree configuration to an ordered list of pipeline steps.

    Lookup order:
        1. Exact match on insuree_config["code"] in FLOW_REGISTRY
        2. Match on insuree_config["flow_type"] if present
        3. Fall back to "DEFAULT"
    """

    def __init__(self, registry: dict[str, callable] | None = None) -> None:
        self.registry = registry or FLOW_REGISTRY

    def resolve(self, insuree_config: dict[str, Any]) -> list[PipelineStep]:
        """
        Return the ordered step list for the given insurer.

        Args:
            insuree_config: Dict with at least "code" key.

        Returns:
            Ordered list of PipelineStep instances.

        Raises:
            FlowResolutionError: If no matching flow is found and no DEFAULT.
        """
        insuree_code = insuree_config.get("code", "")
        flow_type = insuree_config.get("flow_type", "")

        # Try exact code match
        if insuree_code in self.registry:
            logger.info(
                "Flow resolved by insurer code",
                insuree_code=insuree_code,
            )
            return self.registry[insuree_code]()

        # Try flow_type match
        if flow_type and flow_type in self.registry:
            logger.info(
                "Flow resolved by flow_type",
                flow_type=flow_type,
                insuree_code=insuree_code,
            )
            return self.registry[flow_type]()

        # Fall back to DEFAULT
        if "DEFAULT" in self.registry:
            logger.info(
                "Flow resolved to DEFAULT",
                insuree_code=insuree_code,
            )
            return self.registry["DEFAULT"]()

        raise FlowResolutionError(
            f"No flow registered for insurer '{insuree_code}' and no DEFAULT flow",
            step_name="flow_resolution",
        )

    def list_available_flows(self) -> list[str]:
        """Return all registered flow keys."""
        return list(self.registry.keys())
