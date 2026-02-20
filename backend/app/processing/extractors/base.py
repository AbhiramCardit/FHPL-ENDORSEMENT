"""
Abstract base class for all extractors.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseExtractor(ABC):
    """Base interface for document extractors."""

    @abstractmethod
    def extract(self, filepath: str, template: dict | None = None) -> list[dict[str, Any]]:
        """Extract endorsement records from a file. Returns list of raw dicts."""
        ...

    @abstractmethod
    def supports_format(self, format_type: str) -> bool:
        """Return True if this extractor handles the given format type."""
        ...
