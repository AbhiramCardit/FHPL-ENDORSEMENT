"""Excel extraction with template-driven column mapping."""
from app.processing.extractors.base import BaseExtractor


class XlsxExtractor(BaseExtractor):
    def extract(self, filepath, template=None):
        raise NotImplementedError

    def supports_format(self, format_type):
        return format_type == "STRUCTURED_XLSX"
