"""
DownloadFileStep — downloads ALL files in the batch from S3/MinIO.

For single-file runs: downloads one file, sets ctx.local_filepath.
For multi-file batches: downloads each FileInfo and sets local_path on each.
"""

from __future__ import annotations

import os
from typing import Any

from app.core.logging import get_logger
from app.pipeline.context import FileInfo, PipelineContext, StepResult
from app.pipeline.errors import StorageError, StepExecutionError
from app.pipeline.step import PipelineStep

logger = get_logger(__name__)


class DownloadFileStep(PipelineStep):
    """Download all files in the batch from MinIO/S3 to local temp."""

    name = "download_files"
    description = "Download raw file(s) from object storage"
    retryable = True
    max_retries = 3

    async def execute(self, ctx: PipelineContext) -> StepResult:
        started_at = self._now()

        try:
            # ── Ensure we have files to download ──────
            if not ctx.files:
                # Single-file backward-compat: create a FileInfo from the ID
                ctx.add_file(FileInfo(
                    file_id=ctx.file_ingestion_id,
                    filename=f"endorsement_file_{ctx.file_ingestion_id}",
                    role="primary",
                ))

            downloaded = 0

            for file_info in ctx.files:
                try:
                    await self._download_single(file_info, ctx)
                    downloaded += 1
                    logger.info(
                        "File downloaded",
                        file_id=file_info.file_id,
                        role=file_info.role,
                        filename=file_info.filename,
                        local_path=file_info.local_path,
                    )
                except Exception as exc:
                    file_info.error = str(exc)
                    ctx.add_error(
                        f"Failed to download {file_info.filename} "
                        f"(role={file_info.role}): {exc}"
                    )
                    logger.error(
                        "File download failed",
                        file_id=file_info.file_id,
                        role=file_info.role,
                        error=str(exc),
                    )

            if downloaded == 0:
                raise StepExecutionError(
                    "No files could be downloaded",
                    execution_id=ctx.execution_id,
                    step_name=self.name,
                )

            # Update single-file shortcuts from primary
            primary = ctx.primary_file
            if primary:
                ctx.local_filepath = primary.local_path
                ctx.s3_key = primary.s3_key
                ctx.filename = primary.filename

            logger.info(
                "All downloads complete",
                downloaded=downloaded,
                total=len(ctx.files),
                is_batch=ctx.is_batch,
            )

            return self._success(started_at, metadata={
                "downloaded": downloaded,
                "total_files": len(ctx.files),
                "is_batch": ctx.is_batch,
                "files": [
                    {"role": f.role, "filename": f.filename, "ok": f.error is None}
                    for f in ctx.files
                ],
            })

        except StepExecutionError:
            raise
        except Exception as exc:
            raise StepExecutionError(
                f"Failed to download files: {exc}",
                execution_id=ctx.execution_id,
                step_name=self.name,
            ) from exc

    async def _download_single(
        self,
        file_info: FileInfo,
        ctx: PipelineContext,
    ) -> None:
        """
        Download a single file from S3/MinIO to local temp.

        If s3_key points to a local file that exists, uses it directly
        (for local testing without S3).
        """
        s3_key = (
            file_info.s3_key
            or f"raw/{ctx.insuree_id}/{file_info.file_id}/{file_info.filename}"
        )
        file_info.s3_key = s3_key

        # ── Local file? Use directly ──────────────────
        if os.path.isfile(s3_key):
            file_info.local_path = s3_key
            logger.info("Using local file directly", path=s3_key, role=file_info.role)
            return

        # ── Otherwise: placeholder (real S3 download TODO) ─
        # TODO: Replace with actual boto3/MinIO download:
        #   s3_client = boto3.client("s3", endpoint_url=settings.STORAGE_ENDPOINT)
        #   local_path = tempfile.mktemp(suffix=os.path.splitext(file_info.filename)[1])
        #   s3_client.download_file(settings.STORAGE_BUCKET_NAME, s3_key, local_path)
        file_info.local_path = (
            f"/tmp/pipeline/{ctx.execution_id}/{file_info.role}/{file_info.filename}"
        )

    async def rollback(self, ctx: PipelineContext) -> None:
        """Clean up all downloaded temp files on failure."""
        for file_info in ctx.files:
            if file_info.local_path and os.path.exists(file_info.local_path):
                os.remove(file_info.local_path)
                logger.info("Temp file cleaned up", path=file_info.local_path)
