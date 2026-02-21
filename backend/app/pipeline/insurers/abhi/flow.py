"""
ABHI (Aditya Birla Health Insurance) — flow definition.

Expected files per endorsement run:
    - endorsement_data (XLS/XLSX): structured endorsement sheet
    - endorsement_pdf (PDF): endorsement document for LLM extraction

Flow:
    Download → Detect → ABHI Extract (XLS + PDF LLM) → Map → Validate → Score → Persist
"""

from __future__ import annotations

from app.pipeline.step import PipelineStep

# ─── Import common steps ──────────────────────────
from app.pipeline.steps.download_file import DownloadFileStep
from app.pipeline.steps.detect_format import DetectFormatStep
from app.pipeline.steps.map_canonical import MapCanonicalStep
from app.pipeline.steps.validate_schema import ValidateSchemaStep
from app.pipeline.steps.validate_business_rules import ValidateBusinessRulesStep
from app.pipeline.steps.detect_duplicates import DetectDuplicatesStep
from app.pipeline.steps.score_confidence import ScoreConfidenceStep
from app.pipeline.steps.persist_records import PersistRecordsStep

# ─── Import ABHI-specific steps ──────────────────
from app.pipeline.insurers.abhi.steps import ABHIExtractDataStep


# ═══════════════════════════════════════════════════════════
#  Default ABHI config
# ═══════════════════════════════════════════════════════════

ABHI_CONFIG: dict = {
    "code": "ABHI",
    "name": "Aditya Birla Health Insurance",

    # File roles expected in each batch
    "file_roles": {
        "endorsement_data": {
            "description": "Structured XLS/XLSX endorsement sheet",
            "required": True,
            "formats": ["STRUCTURED_XLSX"],
        },
        "endorsement_pdf": {
            "description": "Endorsement PDF document (LLM extraction)",
            "required": False,
            "formats": ["SEMI_STRUCTURED_PDF", "UNSTRUCTURED_PDF"],
        },
    },

    # Format detection overrides per role
    "role_formats": {
        "endorsement_data": "STRUCTURED_XLSX",
        "endorsement_pdf": "SEMI_STRUCTURED_PDF",
    },

    # Extraction template for canonical mapping
    "extraction_template": {
        "column_mappings": {
            # XLS column name → canonical field path
            # These will be configured per actual ABHI sheet format
        },
        "value_mappings": {
            "endorsement_type": {
                "ADD": "ADD_MEMBER",
                "DEL": "REMOVE_MEMBER",
                "DELETE": "REMOVE_MEMBER",
                "MOD": "CHANGE_DETAILS",
                "MODIFY": "CHANGE_DETAILS",
                "SI_CHANGE": "CHANGE_SUM_INSURED",
            },
        },
    },

    # Validation rules
    "min_confidence": 0.80,
    "business_rules": {
        "max_past_days": 90,
        "max_future_days": 30,
        "min_age": 0,
        "max_age": 100,
    },
    "required_fields": ["name", "employee_id", "action"],
}


# ═══════════════════════════════════════════════════════════
#  ABHI Flow
# ═══════════════════════════════════════════════════════════

def abhi_flow() -> list[PipelineStep]:
    """
    ABHI pipeline flow.

    Step 1: Download files
    Step 2: ABHI Extract (XLS sheet extractor + PDF via Gemini LLM)
    """
    return [
        DownloadFileStep(),
        ABHIExtractDataStep(),
    ]
