"""
Format Detector — identifies file type and determines extraction strategy.
"""


def detect_format(filepath: str, insuree_config: dict) -> str:
    """
    Detect file format and return the format type string.
    Returns one of: STRUCTURED_CSV, STRUCTURED_XLSX, SEMI_STRUCTURED_PDF,
    UNSTRUCTURED_PDF, SCANNED_IMAGE, UNSTRUCTURED_DOCX
    """
    raise NotImplementedError("Format detection not yet implemented")
