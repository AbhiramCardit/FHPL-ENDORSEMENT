"""
Canonical Schema Mapper — maps extracted data to EndorsementRecord[].
"""


def map_to_canonical(raw_data: list[dict], template: dict) -> list[dict]:
    """Map extractor output to standardized endorsement records using the insuree's template."""
    raise NotImplementedError("Mapper not yet implemented")
