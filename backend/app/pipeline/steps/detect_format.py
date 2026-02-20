"""
DetectFormatStep — detects the format for EACH file in the batch.

Sets file_info.detected_format on each FileInfo.
For single-file runs, also sets ctx.detected_format.
"""

from __future__ import annotations

import os
from typing import Any

from app.core.constants import FileFormat
from app.core.logging import get_logger
from app.pipeline.context import PipelineContext, StepResult
from app.pipeline.errors import StepExecutionError
from app.pipeline.step import PipelineStep

logger = get_logger(__name__)

# Extension → format mapping
EXTENSION_MAP: dict[str, str] = {
    ".csv": FileFormat.STRUCTURED_CSV,
    ".xlsx": FileFormat.STRUCTURED_XLSX,
    ".xls": FileFormat.STRUCTURED_XLSX,
    ".pdf": FileFormat.SEMI_STRUCTURED_PDF,
    ".docx": FileFormat.UNSTRUCTURED_DOCX,
    ".doc": FileFormat.UNSTRUCTURED_DOCX,
    ".png": FileFormat.SCANNED_IMAGE,
    ".jpg": FileFormat.SCANNED_IMAGE,
    ".jpeg": FileFormat.SCANNED_IMAGE,
    ".tiff": FileFormat.SCANNED_IMAGE,
    ".tif": FileFormat.SCANNED_IMAGE,
}


class DetectFormatStep(PipelineStep):
    """Detect file format for each file in the batch."""

    name = "detect_formats"
    description = "Detect file format(s) and extraction strategy"

    async def execute(self, ctx: PipelineContext) -> StepResult:
        started_at = self._now()

        try:
            results = []

            for file_info in ctx.files:
                # Priority 1: Insuree config specifies format per role
                role_formats = ctx.insuree_config.get("role_formats", {})
                config_format = role_formats.get(file_info.role)

                if config_format and config_format in FileFormat.__members__.values():
                    file_info.detected_format = config_format
                    results.append({
                        "role": file_info.role,
                        "format": config_format,
                        "source": "role_config",
                    })
                    continue

                # Priority 2: Global format_type from insuree config
                global_format = ctx.insuree_config.get("format_type")
                if (
                    global_format
                    and global_format in FileFormat.__members__.values()
                    and not ctx.is_batch  # only use global for single-file
                ):
                    file_info.detected_format = global_format
                    results.append({
                        "role": file_info.role,
                        "format": global_format,
                        "source": "insuree_config",
                    })
                    continue

                # Priority 3: Detect from file extension
                ext = os.path.splitext(file_info.filename)[1].lower()
                if ext in EXTENSION_MAP:
                    file_info.detected_format = EXTENSION_MAP[ext]
                    results.append({
                        "role": file_info.role,
                        "format": file_info.detected_format,
                        "source": "extension",
                        "extension": ext,
                    })
                    continue

                # Priority 4: Fallback
                file_info.detected_format = FileFormat.UNSTRUCTURED_PDF
                results.append({
                    "role": file_info.role,
                    "format": file_info.detected_format,
                    "source": "fallback",
                })

            # Update single-file shortcut
            primary = ctx.primary_file
            if primary:
                ctx.detected_format = primary.detected_format

            logger.info(
                "Format detection complete",
                total_files=len(ctx.files),
                results=results,
            )

            return self._success(started_at, metadata={
                "total_files": len(ctx.files),
                "detections": results,
            })

        except Exception as exc:
            raise StepExecutionError(
                f"Format detection failed: {exc}",
                execution_id=ctx.execution_id,
                step_name=self.name,
            ) from exc
