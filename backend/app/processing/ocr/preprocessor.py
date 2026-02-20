"""Image preprocessing before OCR."""


def preprocess_image(filepath: str) -> str:
    """Clean up image (deskew, denoise, contrast) before OCR. Returns cleaned filepath."""
    raise NotImplementedError
