"""
BAJAJ — Bajaj Allianz General Insurance pipeline module.

Files expected per endorsement run:
    - endorsement_data (XLS/XLSX): ER08 deletion endorsement sheet
    - endorsement_pdf (PDF): endorsement document for LLM extraction

Exports:
    - bajaj_flow(): returns the Bajaj step sequence
    - BAJAJ_CONFIG: default insurer configuration
"""

from app.pipeline.insurers.bajaj.flow import bajaj_flow, BAJAJ_CONFIG

__all__ = ["bajaj_flow", "BAJAJ_CONFIG"]
