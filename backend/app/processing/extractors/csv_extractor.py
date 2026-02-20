"""CSV column-mapping extractor."""
from app.processing.extractors.base import BaseExtractor


class CsvExtractor(BaseExtractor):
    def extract(self, filepath, template=None):
        raise NotImplementedError

    def supports_format(self, format_type):
        return format_type == "STRUCTURED_CSV"
