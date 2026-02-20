"""LLM-based unstructured document extraction."""
from app.processing.extractors.base import BaseExtractor


class LlmExtractor(BaseExtractor):
    def extract(self, filepath, template=None):
        raise NotImplementedError

    def supports_format(self, format_type):
        return format_type in ("UNSTRUCTURED_PDF", "SCANNED_IMAGE", "UNSTRUCTURED_DOCX")
