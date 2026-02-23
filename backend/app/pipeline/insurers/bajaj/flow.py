"""
Bajaj Allianz General Insurance — flow definition.

Expected files per endorsement run:
    - endorsement_data (XLS/XLSX): ER08 deletion endorsement sheet
    - endorsement_pdf (PDF): endorsement document for LLM extraction

Flow:
    Download → Bajaj Extract XLS → Bajaj Extract PDF (LLM)
"""

from __future__ import annotations

from app.pipeline.step import PipelineStep

# ─── Import common steps ──────────────────────────
from app.pipeline.steps.download_file import DownloadFileStep

# ─── Import Bajaj-specific steps ──────────────────
from app.pipeline.insurers.bajaj.steps import BajajExtractXLSStep, BajajExtractPDFStep


# ═══════════════════════════════════════════════════════════
#  Default Bajaj config
# ═══════════════════════════════════════════════════════════

BAJAJ_CONFIG: dict = {
    "code": "BAJAJ",
    "name": "Bajaj Allianz General Insurance",

    # File roles expected in each batch
    "file_roles": {
        "endorsement_data": {
            "description": "ER08 deletion endorsement XLS/XLSX sheet",
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
            # These will be configured per actual Bajaj sheet format
        },
        "value_mappings": {
            "endorsement_type": {
                "DEL": "REMOVE_MEMBER",
                "DELETE": "REMOVE_MEMBER",
                "DELETION": "REMOVE_MEMBER",
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
    "required_fields": ["S.No", "Name of Member"],
}


# ═══════════════════════════════════════════════════════════
#  Bajaj Flow
# ═══════════════════════════════════════════════════════════

def bajaj_flow() -> list[PipelineStep]:
    """
    Bajaj pipeline flow.

    Step 1: Download files
    Step 2: Extract endorsement data from XLS/XLSX
    Step 3: Extract endorsement data from PDF via Gemini LLM
    """
    return [
        DownloadFileStep(),
        BajajExtractXLSStep(),
        BajajExtractPDFStep(),
    ]
