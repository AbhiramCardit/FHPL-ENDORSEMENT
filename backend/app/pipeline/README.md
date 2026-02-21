# Pipeline Engine — Developer Guide

> Enterprise document processing pipeline for FHPL endorsement workflows.
> Supports multi-file batches, per-insurer flows, LLM extraction with tracing, and step-based orchestration.

---

## Architecture Overview

```
PipelineEngine.run()
    │
    ├── 1. Build PipelineContext (files, config, execution tracking)
    ├── 2. FlowResolver → resolve insurer code to step sequence
    └── 3. Execute steps sequentially → PipelineResult
```

### Core Components

| Component | File | Purpose |
|-----------|------|---------|
| **PipelineEngine** | `engine.py` | Orchestrator — runs steps, handles retries, timing |
| **PipelineContext** | `context.py` | Mutable state bag passed between steps |
| **PipelineStep** | `step.py` | Abstract base class for all steps |
| **FlowResolver** | `flow_resolver.py` | Maps insurer code → step sequence |
| **FileInfo** | `context.py` | Per-file metadata in a batch |
| **StepResult** | `context.py` | Outcome of a single step |

---

## Step Lifecycle

Every step follows this contract:

```python
class MyStep(PipelineStep):
    name = "my_step"                          # unique ID
    description = "What this step does"       # for logs/UI
    retryable = False                         # retry on failure?
    max_retries = 3                           # if retryable

    async def execute(self, ctx: PipelineContext) -> StepResult:
        started_at = self._now()
        # ... your logic, read/write ctx ...
        return self._success(started_at, metadata={"key": "value"})

    async def should_skip(self, ctx: PipelineContext) -> bool:
        return False  # override to skip conditionally

    async def rollback(self, ctx: PipelineContext) -> None:
        pass  # cleanup on failure (e.g. delete temp files)
```

### Available Helpers

| Method | Returns | Purpose |
|--------|---------|---------|
| `self._now()` | `datetime` | UTC timestamp for timing |
| `self._success(started_at, metadata)` | `StepResult` | Build success result |
| `self._failure(started_at, error, metadata)` | `StepResult` | Build failure result |

---

## Built-in Steps

| Step | File | What it Does |
|------|------|-------------|
| `DownloadFileStep` | `steps/download_file.py` | Downloads all files in batch from S3/MinIO |
| `DetectFormatStep` | `steps/detect_format.py` | Detects format per file (CSV, XLSX, PDF, etc.) |
| `ExtractDataStep` | `steps/extract_data.py` | Generic extractor — routes by format |
| `MapCanonicalStep` | `steps/map_canonical.py` | Maps raw records → canonical schema |
| `ValidateSchemaStep` | `steps/validate_schema.py` | Schema validation (required fields, types) |
| `ValidateBusinessRulesStep` | `steps/validate_business_rules.py` | Business rule checks (age, dates, etc.) |
| `DetectDuplicatesStep` | `steps/detect_duplicates.py` | Within-file and cross-file dedup |
| `ScoreConfidenceStep` | `steps/score_confidence.py` | Confidence scoring for auto-submit vs review |
| `PersistRecordsStep` | `steps/persist_records.py` | Save to database |
| `APIRequestStep` | `steps/api_request.py` | Configurable HTTP API call |

---

## How Flows Work

A **flow** is an ordered list of steps for a specific insurer:

```python
# Default flow (works for any insurer)
Download → Detect → Extract → Map → Validate → Score → Persist

# ABHI flow (custom extraction)
Download → Detect → ABHIExtract (XLS + PDF LLM) → Map → Validate → Score → Persist

# Custom insurer with API calls
Download → Detect → [FetchPolicyAPI] → Extract → Map → [CreateEndorsementAPI] → Validate → Persist
```

Flows are registered in `flow_resolver.py`:

```python
FLOW_REGISTRY = {
    "DEFAULT": _default_flow,
    "ABHI": abhi_flow,           # Aditya Birla
    "INSURER_A": insurer_a_flow, # Example
}
```

---

## Adding a New Insurer

### 1. Create the insurer folder

```
pipeline/insurers/
  └── my_insurer/
      ├── __init__.py     — exports flow + config
      ├── prompts.py      — LLM prompts (if needed)
      ├── extractors.py   — file-specific extractors
      ├── steps.py        — custom PipelineStep subclasses
      └── flow.py         — flow definition + insurer config
```

### 2. Define the flow (`flow.py`)

```python
from app.pipeline.steps.download_file import DownloadFileStep
from app.pipeline.steps.detect_format import DetectFormatStep
# ... import common steps
from app.pipeline.insurers.my_insurer.steps import MyExtractStep

MY_INSURER_CONFIG = {
    "code": "MY_INSURER",
    "name": "My Insurance Company",
    "file_roles": {
        "endorsement_data": {"required": True},
        "supporting_doc": {"required": False},
    },
    "min_confidence": 0.80,
}

def my_insurer_flow() -> list[PipelineStep]:
    return [
        DownloadFileStep(),
        DetectFormatStep(),
        MyExtractStep(),           # your custom extraction
        MapCanonicalStep(),
        ValidateSchemaStep(),
        ValidateBusinessRulesStep(),
        DetectDuplicatesStep(),
        ScoreConfidenceStep(),
        PersistRecordsStep(),
    ]
```

### 3. Register in FlowResolver (`flow_resolver.py`)

```python
from app.pipeline.insurers.my_insurer.flow import my_insurer_flow

FLOW_REGISTRY = {
    "DEFAULT": _default_flow,
    "ABHI": abhi_flow,
    "MY_INSURER": my_insurer_flow,  # ← add here
}
```

### 4. Create custom steps (`steps.py`)

```python
class MyExtractStep(PipelineStep):
    name = "my_insurer_extract"
    description = "Extract data from My Insurer files"

    async def execute(self, ctx: PipelineContext) -> StepResult:
        started_at = self._now()

        for file_info in ctx.files:
            if file_info.role == "endorsement_data":
                records = await self._extract_xlsx(file_info)
            elif file_info.role == "supporting_doc":
                records = await self._extract_pdf(file_info)

            ctx.raw_extracted_by_role[file_info.role] = records

        ctx.merge_extracted_to_flat()
        return self._success(started_at, metadata={...})
```

### 5. Add LLM prompts (`prompts.py`)

```python
EXTRACTION_PROMPT = """
Extract endorsement records from the following document.
Return ONLY a valid JSON array.

Each record must contain:
- "name": member name
- "action": ADD/DELETE/MODIFY
...

Document text:
{document_text}
""".strip()
```

---

## Multi-File Batch Processing

### How it works

```python
# Trigger a batch run
result = await engine.run(
    file_ingestion_id="batch-001",
    insuree_config={"code": "ABHI"},
    files=[
        {"file_id": "f1", "filename": "data.xlsx", "role": "endorsement_data"},
        {"file_id": "f2", "filename": "letter.pdf", "role": "endorsement_pdf"},
    ],
)
```

### Accessing per-role data in steps

```python
# In any step:
xls_records = ctx.get_extracted_for_role("endorsement_data")
pdf_records = ctx.get_extracted_for_role("endorsement_pdf")
all_records = ctx.raw_extracted  # merged flat list with _source_role tags

# File metadata:
xls_file = ctx.get_file_by_role("endorsement_data")
print(xls_file.filename, xls_file.record_count)
```

### Context properties

| Property | Type | Description |
|----------|------|-------------|
| `ctx.files` | `list[FileInfo]` | All files in batch |
| `ctx.is_batch` | `bool` | True if >1 file |
| `ctx.raw_extracted_by_role` | `dict[str, list]` | Records keyed by role |
| `ctx.raw_extracted` | `list[dict]` | Merged flat list |
| `ctx.get_file_by_role(role)` | `FileInfo` | Lookup file by role |
| `ctx.get_extracted_for_role(role)` | `list[dict]` | Records for a role |
| `ctx.merge_extracted_to_flat()` | — | Merge by-role → flat |

---

## LLM Extraction with Tracing

### Setup

1. Add your API key to `.env`:
   ```env
   GOOGLE_API_KEY=your-key
   GEMINI_MODEL=gemini-2.5-flash

   # Optional: LangSmith tracing
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=your-langsmith-key
   LANGSMITH_PROJECT=fhpl-endorsements
   ```

2. Tracing is automatic — every `@traceable_step` decorated function sends traces to LangSmith with execution metadata.

### Using `@traceable_step`

```python
from app.core.tracing import traceable_step

@traceable_step(
    name="extract_pdf",
    run_type="chain",
    tags=["extraction", "pdf", "llm"],
)
async def _traced_extract(file_path, role, execution_id, ...):
    # This function's inputs/outputs appear in LangSmith
    ...
```

- Traces include `execution_id`, `insuree_code`, file `role` as metadata
- Degrades gracefully when LangSmith is not configured
- Never breaks the pipeline even if tracing fails

---

## PipelineContext Data Flow

```
DownloadFileStep
  → ctx.files[i].local_path = "/tmp/..."

DetectFormatStep
  → ctx.files[i].detected_format = "STRUCTURED_XLSX"

ExtractDataStep / ABHIExtractDataStep
  → ctx.raw_extracted_by_role["endorsement_data"] = [{...}, ...]
  → ctx.raw_extracted_by_role["endorsement_pdf"]  = [{...}, ...]
  → ctx.raw_extracted = [merged flat list with _source_role]

MapCanonicalStep
  → ctx.canonical_records = [{member: {}, endorsement_type: ...}, ...]

ValidateSchemaStep
  → ctx.validation_results = [{valid: true, ...}, ...]

ScoreConfidenceStep
  → ctx.records_for_submission = [high confidence]
  → ctx.records_for_review = [low confidence]

PersistRecordsStep
  → ctx.extra["persist_result"] = {submitted: N, review: M}
```

---

## Running the Demo

```bash
cd backend
python -m scripts.demo_pipeline
```

Runs 5 demo flows:
1. Single-file DEFAULT
2. Multi-file DEFAULT (3 files)
3. Insurer A (2 files + API)
4. Insurer B (3 files + 2 APIs)
5. **ABHI** (XLS + PDF LLM via Gemini)

---

## Error Handling

| Error Type | When | Effect |
|------------|------|--------|
| `StepExecutionError` | Step logic fails | Pipeline stops (unless step handles internally) |
| `ExtractionError` | File extraction fails | Logged, pipeline can continue with other files |
| `FlowResolutionError` | Unknown insurer code | Pipeline fails before steps run |
| `StepRetryExhaustedError` | Retryable step exhausts retries | Pipeline stops |
| Per-file error | Single file fails in batch | Stored in `file_info.error`, other files continue |

---

## File Structure

```
app/pipeline/
├── __init__.py             — public exports
├── engine.py               — PipelineEngine orchestrator
├── context.py              — PipelineContext + FileInfo + StepResult
├── step.py                 — PipelineStep ABC
├── flow_resolver.py        — maps insurer → step sequence
├── errors.py               — custom exception classes
├── steps/                  — built-in reusable steps
│   ├── download_file.py
│   ├── detect_format.py
│   ├── extract_data.py
│   ├── map_canonical.py
│   ├── validate_schema.py
│   ├── validate_business_rules.py
│   ├── detect_duplicates.py
│   ├── score_confidence.py
│   ├── persist_records.py
│   └── api_request.py
└── insurers/               — per-insurer modules
    └── abhi/
        ├── __init__.py
        ├── flow.py         — ABHI flow + config
        ├── steps.py        — ABHIExtractDataStep
        ├── extractors.py   — XLS sheet extractor
        └── prompts.py      — LLM prompts for PDF
```
