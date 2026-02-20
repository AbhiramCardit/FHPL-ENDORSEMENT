"""OCR engine wrapper — Tesseract / AWS Textract."""


def extract_text(filepath: str, provider: str = "tesseract") -> str:
    """Run OCR on an image or image-based PDF. Returns extracted text."""
    raise NotImplementedError
