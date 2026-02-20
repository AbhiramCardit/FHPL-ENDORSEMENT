"""PDF text + table extraction using pdfplumber/camelot."""
from app.processing.extractors.base import BaseExtractor


class PdfExtractor(BaseExtractor):
    def extract(self, filepath, template=None):
        raise NotImplementedError

    def supports_format(self, format_type):
        return format_type in ("SEMI_STRUCTURED_PDF", "UNSTRUCTURED_PDF")
