"""
Bajaj-specific pipeline steps.

Two separate extraction steps for maximum transparency:
    - BajajExtractXLSStep: endorsement_data (XLS/XLSX) → ER08 deletion sheet extractor
    - BajajExtractPDFStep: endorsement_pdf (PDF) → PDF sent directly to Gemini 2.5 Flash
"""

from __future__ import annotations

import json
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.core.tracing import traceable_step
from app.pipeline.context import FileInfo, PipelineContext, StepMetadata, StepResult
from app.pipeline.errors import ExtractionError, StepExecutionError
from app.pipeline.step import PipelineStep
from app.pipeline.insurers.bajaj.extractors import extract_xls
from app.pipeline.insurers.bajaj.prompts import ENDORSEMENT_PDF_PROMPT, SYSTEM_PROMPT

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════
#  Step 1: XLS Extraction
# ═══════════════════════════════════════════════════════════

class BajajExtractXLSStep(PipelineStep):
    """
    Bajaj XLS extraction step.

    Extracts endorsement data from XLS/XLSX files using the
    ER08 deletion sheet extractor. Operates on files with role 'endorsement_data'.
    """

    name = "bajaj_extract_xls"
    description = "Extract endorsement data from Bajaj XLS/XLSX file"
    retryable = True
    max_retries = 2

    async def should_skip(self, ctx: PipelineContext) -> bool:
        """Skip if there is no endorsement_data file."""
        fi = ctx.get_file_by_role("endorsement_data")
        if fi is None:
            logger.info("No endorsement_data file — skipping XLS extraction")
            return True
        if fi.error:
            logger.info("endorsement_data file has error — skipping XLS extraction", error=fi.error)
            return True
        return False

    async def execute(self, ctx: PipelineContext) -> StepResult:
        started_at = self._now()

        fi = ctx.get_file_by_role("endorsement_data")
        if fi is None or fi.error:
            raise StepExecutionError(
                "No valid endorsement_data file to extract from",
                execution_id=ctx.execution_id,
                step_name=self.name,
            )

        try:
            full_result = await self._extract_xls(fi, ctx)
        except Exception as exc:
            fi.error = str(exc)
            ctx.add_error(f"Bajaj XLS extraction failed for {fi.filename}: {exc}")
            raise StepExecutionError(
                f"XLS extraction failed: {exc}",
                execution_id=ctx.execution_id,
                step_name=self.name,
            ) from exc

        records = full_result.get("records", [])
        fi.record_count = len(records)

        # Store CLEAN records (no internal tracking keys)
        ctx.raw_extracted_by_role[fi.role] = records

        # Store the full extraction metadata
        ctx.extraction_metadata_by_role[fi.role] = {
            "summary": full_result.get("summary", {}),
            "extraction_method": "xls_extractor",
        }

        ctx.merge_extracted_to_flat()

        return self._success(
            started_at,
            metadata=StepMetadata(
                files_processed=1,
                records_processed=len(records),
                extraction_method="xls_extractor",
            ),
            output={
                "filename": fi.filename,
                "summary": full_result.get("summary", {}),
                "records_count": len(records),
            },
        )

    async def _extract_xls(self, fi: FileInfo, ctx: PipelineContext) -> dict[str, Any]:
        """Extract from Bajaj XLS/XLSX using the ER08 sheet extractor.

        Returns the complete extraction result dict with keys:
        records, summary.
        """
        logger.info("Bajaj XLS extraction", role=fi.role, filepath=fi.local_path)

        # Demo mode — no real file
        if not fi.local_path or fi.local_path.startswith("/tmp/pipeline/"):
            return {
                "records": self._xls_demo_data(fi.filename),
                "summary": {},
            }

        result = extract_xls(fi.local_path)

        ctx.set_extra("bajaj_xls_summary", result.get("summary", {}))

        return result

    @staticmethod
    def _xls_demo_data(filename: str) -> list[dict[str, Any]]:
        """Placeholder data for demo mode (no real file)."""
        return [
            {"S.No": 1, "Name of Member": "Demo Member 1", "action": "DEL",
             "dob": "1990-05-15", "relationship": "Self", "gender": "Male",
             "sum_insured": 500000},
            {"S.No": 2, "Name of Member": "Demo Member 2", "action": "DEL",
             "dob": "1992-08-20", "relationship": "Spouse", "gender": "Female",
             "sum_insured": 500000},
        ]


# ═══════════════════════════════════════════════════════════
#  Step 2: PDF → Gemini LLM Extraction
# ═══════════════════════════════════════════════════════════

class BajajExtractPDFStep(PipelineStep):
    """
    Bajaj PDF extraction step.

    Sends the endorsement PDF directly to Gemini 2.5 Flash for
    structured data extraction. Operates on files with role 'endorsement_pdf'.
    """

    name = "bajaj_extract_pdf"
    description = "Extract endorsement data from Bajaj PDF via Gemini LLM"
    retryable = True
    max_retries = 2

    async def should_skip(self, ctx: PipelineContext) -> bool:
        """Skip if there is no endorsement_pdf file."""
        fi = ctx.get_file_by_role("endorsement_pdf")
        if fi is None:
            logger.info("No endorsement_pdf file — skipping PDF extraction")
            return True
        if fi.error:
            logger.info("endorsement_pdf file has error — skipping PDF extraction", error=fi.error)
            return True
        return False

    async def execute(self, ctx: PipelineContext) -> StepResult:
        started_at = self._now()

        fi = ctx.get_file_by_role("endorsement_pdf")
        if fi is None or fi.error:
            raise StepExecutionError(
                "No valid endorsement_pdf file to extract from",
                execution_id=ctx.execution_id,
                step_name=self.name,
            )

        try:
            records = await self._extract_pdf(fi, ctx)
        except Exception as exc:
            fi.error = str(exc)
            ctx.add_error(f"Bajaj PDF extraction failed for {fi.filename}: {exc}")
            raise StepExecutionError(
                f"PDF extraction failed: {exc}",
                execution_id=ctx.execution_id,
                step_name=self.name,
            ) from exc

        fi.record_count = len(records)

        # Store CLEAN records (no internal tracking keys)
        ctx.raw_extracted_by_role[fi.role] = records

        model = settings.GEMINI_MODEL

        # Store extraction metadata for this role
        ctx.extraction_metadata_by_role[fi.role] = {
            "extraction_method": "llm",
            "llm_model": model,
        }

        ctx.merge_extracted_to_flat()

        return self._success(
            started_at,
            metadata=StepMetadata(
                files_processed=1,
                records_processed=len(records),
                extraction_method="llm",
                llm_model=model,
            ),
            output={
                "filename": fi.filename,
                "records_count": len(records),
                "model": model,
            },
        )

    async def _extract_pdf(self, fi: FileInfo, ctx: PipelineContext) -> list[dict[str, Any]]:
        """Send the PDF directly to Gemini 2.5 Flash for extraction."""
        return await self._traced_extract_pdf(
            file_path=fi.local_path,
            filename=fi.filename,
            execution_id=ctx.execution_id,
            insuree_code=ctx.insuree_code,
        )

    @staticmethod
    @traceable_step(
        name="bajaj_extract_pdf",
        run_type="chain",
        tags=["extraction", "pdf", "llm", "bajaj", "gemini"],
    )
    async def _traced_extract_pdf(
        file_path: str,
        filename: str,
        execution_id: str,
        insuree_code: str,
    ) -> list[dict[str, Any]]:
        """
        Send PDF directly to Gemini 2.5 Flash.

        Uses google-genai's file upload to pass the raw PDF bytes
        to the model — no pdfplumber text extraction needed.
        """
        # Demo mode
        if not file_path or file_path.startswith("/tmp/pipeline/"):
            logger.info("Bajaj PDF extraction (demo mode)")
            return [{
                "Proposer Name": "Demo Corp",
                "Policy Number": "OG-26-0000-0000-00000000",
                "Endorsement Type": "Deletion",
                "Premium": {
                    "Net Premium": {"Endorsement Premium": -1000.00},
                    "Gross premium": {"Endorsement Premium": -1180.00},
                },
            }]

        # ── Upload PDF and call Gemini ────────────────
        from google import genai

        client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        model = settings.GEMINI_MODEL

        logger.info("Uploading PDF to Gemini", filepath=file_path, model=model)

        # Upload the PDF file directly
        uploaded_file = client.files.upload(file=file_path)

        logger.info("Calling Gemini with PDF", model=model, file_name=uploaded_file.name)

        response = client.models.generate_content(
            model=model,
            contents=[
                uploaded_file,
                ENDORSEMENT_PDF_PROMPT,
            ],
            config=genai.types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=settings.LLM_TEMPERATURE,
                max_output_tokens=settings.LLM_MAX_TOKENS,
            ),
        )

        response_text = response.text.strip()

        logger.info("Gemini response received", response_length=len(response_text))

        # ── Parse JSON ────────────────────────────────
        # Strip markdown code block if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        try:
            records = json.loads(response_text)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Gemini JSON", error=str(exc), preview=response_text[:300])
            raise ExtractionError(
                f"LLM JSON parse failed: {exc}",
                execution_id=execution_id,
                step_name="bajaj_extract_pdf",
            ) from exc

        # The PDF prompt returns a single object (policy metadata)
        if isinstance(records, dict):
            records = [records]

        logger.info("Bajaj PDF extraction complete", records=len(records), model=model)
        return records
