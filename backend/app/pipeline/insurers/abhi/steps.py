"""
ABHI-specific pipeline steps.

ABHIExtractDataStep handles two file roles:
    - endorsement_data (XLS/XLSX) → proven XLS sheet extractor
    - endorsement_pdf (PDF) → PDF sent directly to Gemini 2.5 Flash
"""

from __future__ import annotations

import json
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.core.tracing import traceable_step
from app.pipeline.context import FileInfo, PipelineContext, StepResult
from app.pipeline.errors import ExtractionError, StepExecutionError
from app.pipeline.step import PipelineStep
from app.pipeline.insurers.abhi.extractors import extract_xls
from app.pipeline.insurers.abhi.prompts import ENDORSEMENT_PDF_PROMPT, SYSTEM_PROMPT

logger = get_logger(__name__)


class ABHIExtractDataStep(PipelineStep):
    """
    ABHI extraction step.

    Routes files by role:
        - endorsement_data → extract_xls()
        - endorsement_pdf  → Gemini 2.5 Flash (PDF sent directly)
    """

    name = "abhi_extract_data"
    description = "Extract endorsement data from ABHI XLS and PDF files"
    retryable = True
    max_retries = 2

    async def execute(self, ctx: PipelineContext) -> StepResult:
        started_at = self._now()

        if not ctx.files:
            raise StepExecutionError(
                "No files to extract from",
                execution_id=ctx.execution_id,
                step_name=self.name,
            )

        per_file_results = []

        for fi in ctx.files:
            if fi.error:
                per_file_results.append({"role": fi.role, "status": "skipped"})
                continue

            try:
                if fi.role == "endorsement_data":
                    records = await self._extract_xls(fi, ctx)
                elif fi.role == "endorsement_pdf":
                    records = await self._extract_pdf(fi, ctx)
                else:
                    per_file_results.append({"role": fi.role, "status": "skipped", "reason": "unknown_role"})
                    continue

                fi.record_count = len(records)
                ctx.raw_extracted_by_role[fi.role] = records
                per_file_results.append({
                    "role": fi.role, "filename": fi.filename,
                    "records": len(records), "status": "ok",
                })

            except Exception as exc:
                fi.error = str(exc)
                ctx.add_error(f"ABHI extraction failed for {fi.filename}: {exc}")
                per_file_results.append({
                    "role": fi.role, "filename": fi.filename,
                    "status": "failed", "error": str(exc),
                })

        ctx.merge_extracted_to_flat()
        files_ok = sum(1 for r in per_file_results if r["status"] == "ok")

        if files_ok == 0:
            raise StepExecutionError(
                "All ABHI file extractions failed",
                execution_id=ctx.execution_id,
                step_name=self.name,
            )

        return self._success(started_at, metadata={
            "total_files": len(ctx.files),
            "files_extracted": files_ok,
            "total_records": len(ctx.raw_extracted),
            "by_role": {r: len(d) for r, d in ctx.raw_extracted_by_role.items()},
            "per_file": per_file_results,
        })

    # ─── Step 1: XLS Extraction ───────────────────────

    async def _extract_xls(self, fi: FileInfo, ctx: PipelineContext) -> list[dict[str, Any]]:
        """Extract from ABHI XLS/XLSX using the proven sheet extractor."""
        logger.info("ABHI XLS extraction", role=fi.role, filepath=fi.local_path)

        # Demo mode — no real file
        if not fi.local_path or fi.local_path.startswith("/tmp/pipeline/"):
            return self._xls_demo_data(fi.filename)

        result = extract_xls(fi.local_path)

        ctx.set_extra("abhi_xls_header", result.get("header", {}))
        ctx.set_extra("abhi_xls_summary", result.get("summary", {}))
        ctx.set_extra("abhi_xls_title", result.get("title"))

        records = result.get("records", [])
        for r in records:
            r["_source_file"] = fi.filename
        return records

    # ─── Step 2: PDF → Gemini LLM (direct file upload) ─

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
        name="abhi_extract_pdf",
        run_type="chain",
        tags=["extraction", "pdf", "llm", "abhi", "gemini"],
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
            logger.info("ABHI PDF extraction (demo mode)")
            return [{
                "name": "Rahul Sharma", "employee_id": "ABHI-EMP001",
                "action": "ADD", "dob": "1990-05-15",
                "relation": "Self", "gender": "Male",
                "sum_insured": 500000, "plan": "GOLD",
                "effective_date": "2026-03-01",
                "remarks": "New addition per endorsement letter",
                "_source_file": filename,
                "_extraction_method": "llm",
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
                step_name="abhi_extract_pdf",
            ) from exc

        # The PDF prompt returns a single object (endorsement schedule metadata)
        if isinstance(records, dict):
            records = [records]

        for r in records:
            r["_source_file"] = filename
            r["_extraction_method"] = "llm"
            r["_llm_model"] = model

        logger.info("ABHI PDF extraction complete", records=len(records), model=model)
        return records

    # ─── Demo Data ────────────────────────────────────

    @staticmethod
    def _xls_demo_data(filename: str) -> list[dict[str, Any]]:
        """Placeholder data for demo mode (no real file)."""
        return [
            {"name": "Rahul Sharma", "employee_id": "ABHI-EMP001", "action": "ADD",
             "dob": "1990-05-15", "relationship": "Self", "gender": "Male",
             "sum_insured": 500000, "plan": "GOLD", "_source_file": filename},
            {"name": "Priya Sharma", "employee_id": "ABHI-EMP001", "action": "ADD",
             "dob": "1992-08-20", "relationship": "Spouse", "gender": "Female",
             "sum_insured": 500000, "plan": "GOLD", "_source_file": filename},
            {"name": "Amit Patel", "employee_id": "ABHI-EMP002", "action": "DEL",
             "dob": "1985-11-03", "relationship": "Self", "gender": "Male",
             "sum_insured": 300000, "plan": "SILVER", "_source_file": filename},
        ]
