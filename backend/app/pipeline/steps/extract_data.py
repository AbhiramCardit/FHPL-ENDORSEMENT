"""
ExtractDataStep — extracts data from EACH file in the batch.

For each FileInfo in ctx.files:
    1. Determines the extractor based on file_info.detected_format
    2. Runs extraction
    3. Stores results in ctx.raw_extracted_by_role[file_info.role]

After all files are extracted, merges everything into ctx.raw_extracted
(flat list) for backward-compat with single-file flows.
"""

from __future__ import annotations

from typing import Any

from app.core.constants import FileFormat
from app.core.logging import get_logger
from app.core.tracing import traceable_step
from app.pipeline.context import FileInfo, PipelineContext, StepResult
from app.pipeline.errors import ExtractionError, StepExecutionError
from app.pipeline.step import PipelineStep

logger = get_logger(__name__)


class ExtractDataStep(PipelineStep):
    """Extract data from every file in the batch using format-specific extractors."""

    name = "extract_data"
    description = "Extract endorsement data from file(s)"
    retryable = True     # LLM calls can be flaky
    max_retries = 2

    async def execute(self, ctx: PipelineContext) -> StepResult:
        started_at = self._now()

        try:
            if not ctx.files:
                raise StepExecutionError(
                    "No files to extract from",
                    execution_id=ctx.execution_id,
                    step_name=self.name,
                )

            per_file_results = []

            for file_info in ctx.files:
                if file_info.error:
                    # Skip files that failed download
                    logger.warning(
                        "Skipping file with download error",
                        role=file_info.role,
                        filename=file_info.filename,
                        error=file_info.error,
                    )
                    per_file_results.append({
                        "role": file_info.role,
                        "filename": file_info.filename,
                        "status": "skipped",
                        "reason": "download_error",
                    })
                    continue

                fmt = file_info.detected_format
                logger.info(
                    "Extracting from file",
                    role=file_info.role,
                    filename=file_info.filename,
                    format=fmt,
                )

                try:
                    records = await self._extract_file(file_info, ctx)
                    file_info.record_count = len(records)

                    # Store by role
                    ctx.raw_extracted_by_role[file_info.role] = records

                    per_file_results.append({
                        "role": file_info.role,
                        "filename": file_info.filename,
                        "format": fmt,
                        "records": len(records),
                        "status": "ok",
                    })
                    logger.info(
                        "File extraction complete",
                        role=file_info.role,
                        records=len(records),
                    )

                except Exception as exc:
                    file_info.error = str(exc)
                    ctx.add_error(
                        f"Extraction failed for {file_info.filename} "
                        f"(role={file_info.role}): {exc}"
                    )
                    per_file_results.append({
                        "role": file_info.role,
                        "filename": file_info.filename,
                        "status": "failed",
                        "error": str(exc),
                    })
                    logger.error(
                        "File extraction failed",
                        role=file_info.role,
                        error=str(exc),
                    )

            # ── Merge all per-role data into flat list ─
            ctx.merge_extracted_to_flat()

            total_records = len(ctx.raw_extracted)
            files_ok = sum(1 for r in per_file_results if r["status"] == "ok")

            if files_ok == 0 and len(ctx.files) > 0:
                raise StepExecutionError(
                    "All file extractions failed",
                    execution_id=ctx.execution_id,
                    step_name=self.name,
                )

            logger.info(
                "All extractions complete",
                total_files=len(ctx.files),
                files_ok=files_ok,
                total_records=total_records,
                by_role={
                    role: len(records)
                    for role, records in ctx.raw_extracted_by_role.items()
                },
            )

            return self._success(started_at, metadata={
                "total_files": len(ctx.files),
                "files_extracted": files_ok,
                "total_records": total_records,
                "by_role": {
                    role: len(records)
                    for role, records in ctx.raw_extracted_by_role.items()
                },
                "per_file": per_file_results,
            })

        except (ExtractionError, StepExecutionError):
            raise
        except Exception as exc:
            raise StepExecutionError(
                f"Extraction failed: {exc}",
                execution_id=ctx.execution_id,
                step_name=self.name,
            ) from exc

    async def _extract_file(
        self,
        file_info: FileInfo,
        ctx: PipelineContext,
    ) -> list[dict[str, Any]]:
        """Route a single file to the correct extractor."""
        fmt = file_info.detected_format

        if fmt == FileFormat.STRUCTURED_CSV:
            return await self._extract_csv(file_info, ctx)
        elif fmt == FileFormat.STRUCTURED_XLSX:
            return await self._extract_xlsx(file_info, ctx)
        elif fmt in (FileFormat.SEMI_STRUCTURED_PDF, FileFormat.UNSTRUCTURED_PDF):
            return await self._extract_pdf(file_info, ctx)
        elif fmt == FileFormat.SCANNED_IMAGE:
            return await self._extract_ocr(file_info, ctx)
        elif fmt == FileFormat.UNSTRUCTURED_DOCX:
            return await self._extract_docx(file_info, ctx)
        else:
            raise ExtractionError(
                f"Unsupported format '{fmt}' for file {file_info.filename}",
                execution_id=ctx.execution_id,
                step_name=self.name,
            )

    # ─── Extractor placeholders ───────────────────────
    # Each returns list[dict].  Replace with real extractor integrations.
    # The 'role' field is used to generate different placeholder data
    # so multi-file demos look realistic.

    async def _extract_csv(
        self, fi: FileInfo, ctx: PipelineContext
    ) -> list[dict[str, Any]]:
        """Placeholder: extract from CSV."""
        logger.info("CSV extraction (placeholder)", role=fi.role, filepath=fi.local_path)
        # TODO: CSVExtractor with template column_mappings
        return [
            {"name": "John Doe", "employee_id": "EMP001", "action": "ADD",
             "dob": "1990-01-15", "_source_file": fi.filename},
            {"name": "Jane Smith", "employee_id": "EMP002", "action": "DEL",
             "dob": "1985-06-20", "_source_file": fi.filename},
        ]

    async def _extract_xlsx(
        self, fi: FileInfo, ctx: PipelineContext
    ) -> list[dict[str, Any]]:
        """Placeholder: extract from Excel."""
        logger.info("XLSX extraction (placeholder)", role=fi.role, filepath=fi.local_path)
        # TODO: XLSXExtractor with sheet_name, header_row, column_mappings
        return [
            {"name": "Alice Johnson", "employee_id": "EMP003", "action": "ADD",
             "dob": "1992-03-10", "_source_file": fi.filename},
        ]

    async def _extract_pdf(
        self, fi: FileInfo, ctx: PipelineContext
    ) -> list[dict[str, Any]]:
        """Extract from PDF — uses LLM for unstructured, pdfplumber for structured."""
        return await self._traced_extract_pdf(
            file_path=fi.local_path,
            role=fi.role,
            filename=fi.filename,
            format=fi.detected_format,
            execution_id=ctx.execution_id,
            insuree_code=ctx.insuree_code,
        )

    @staticmethod
    @traceable_step(
        name="extract_pdf",
        run_type="chain",
        tags=["extraction", "pdf"],
    )
    async def _traced_extract_pdf(
        file_path: str,
        role: str,
        filename: str,
        format: str,
        execution_id: str,
        insuree_code: str,
    ) -> list[dict[str, Any]]:
        """LangSmith-traced PDF extraction."""
        logger.info("PDF extraction (placeholder)", role=role, filepath=file_path)
        # TODO: For structured PDFs → pdfplumber / camelot
        # TODO: For unstructured PDFs → LLM extraction (Anthropic Claude)
        #
        # Real implementation:
        #   from anthropic import AsyncAnthropic
        #   client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        #   response = await client.messages.create(
        #       model=settings.LLM_MODEL,
        #       messages=[{"role": "user", "content": prompt}],
        #   )
        #   return parse_llm_response(response)
        return [
            {"name": "Bob Wilson", "employee_id": "EMP004", "action": "MOD",
             "dob": "1988-11-25", "plan_code": "GOLD-100",
             "sum_insured": 500000, "_source_file": filename},
        ]

    async def _extract_ocr(
        self, fi: FileInfo, ctx: PipelineContext
    ) -> list[dict[str, Any]]:
        """OCR then LLM extraction for scanned images."""
        return await self._traced_extract_ocr(
            file_path=fi.local_path,
            role=fi.role,
            filename=fi.filename,
            execution_id=ctx.execution_id,
            insuree_code=ctx.insuree_code,
        )

    @staticmethod
    @traceable_step(
        name="extract_ocr",
        run_type="chain",
        tags=["extraction", "ocr", "llm"],
    )
    async def _traced_extract_ocr(
        file_path: str,
        role: str,
        filename: str,
        execution_id: str,
        insuree_code: str,
    ) -> list[dict[str, Any]]:
        """LangSmith-traced OCR + LLM extraction."""
        logger.info("OCR + LLM extraction (placeholder)", role=role)
        # TODO: Tesseract/Textract → get text → LLM parse
        return []

    async def _extract_docx(
        self, fi: FileInfo, ctx: PipelineContext
    ) -> list[dict[str, Any]]:
        """Extract from Word document — LLM for unstructured content."""
        return await self._traced_extract_docx(
            file_path=fi.local_path,
            role=fi.role,
            filename=fi.filename,
            execution_id=ctx.execution_id,
            insuree_code=ctx.insuree_code,
        )

    @staticmethod
    @traceable_step(
        name="extract_docx",
        run_type="chain",
        tags=["extraction", "docx", "llm"],
    )
    async def _traced_extract_docx(
        file_path: str,
        role: str,
        filename: str,
        execution_id: str,
        insuree_code: str,
    ) -> list[dict[str, Any]]:
        """LangSmith-traced DOCX extraction."""
        logger.info("DOCX extraction (placeholder)", role=role)
        # TODO: python-docx → get text → LLM parse
        return [
            {"approval_note": "Approved for endorsement batch",
             "effective_date": "2026-03-01", "_source_file": filename},
        ]
