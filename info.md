# Insurance Endorsements Automation Platform

> An end-to-end automation system for a Third Party Administrator (TPA) to ingest, extract, validate, and submit insurance endorsements from multiple insurees — with full audit tracking and a management UI.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Folder Structure](#3-folder-structure)
4. [Core Modules](#4-core-modules)
   - 4.1 [SFTP Ingestion Layer](#41-sftp-ingestion-layer)
   - 4.2 [Document Processing Pipeline](#42-document-processing-pipeline)
   - 4.3 [LLM Extraction Engine](#43-llm-extraction-engine)
   - 4.4 [Validation Engine](#44-validation-engine)
   - 4.5 [TPA Submission Layer](#45-tpa-submission-layer)
   - 4.6 [Audit & Tracking](#46-audit--tracking)
   - 4.7 [Management UI](#47-management-ui)
5. [Data Models & Schema](#5-data-models--schema)
6. [Insuree Configuration System](#6-insuree-configuration-system)
7. [API Reference](#7-api-reference)
8. [Tech Stack](#8-tech-stack)
9. [Environment Variables](#9-environment-variables)
10. [Database Setup](#10-database-setup)
11. [Running the Project](#11-running-the-project)
12. [Deployment](#12-deployment)
13. [Implementation Phases](#13-implementation-phases)
14. [Error Handling Strategy](#14-error-handling-strategy)
15. [Security Considerations](#15-security-considerations)
16. [Adding a New Insuree](#16-adding-a-new-insuree)
17. [Monitoring & Alerting](#17-monitoring--alerting)
18. [FAQ](#18-faq)

---

## 1. Project Overview

### What This System Does

Insurance endorsements are change requests on existing policies — adding/removing members, changing coverage, updating personal details, etc. Insurees (companies holding group policies) send these endorsement files weekly to the TPA. The files arrive:

- On different days (Monday for Insuree A, Tuesday for Insuree B, etc.)
- In different formats (PDF, Excel, CSV, Word, scanned images)
- With different internal structures and column naming conventions
- Via SFTP servers (one per insuree or shared with subfolders)

This platform automates the entire journey from **file arrival on SFTP → data extracted → validated → submitted to TPA's API → tracked with full audit trail**.

### Key Capabilities

- **Multi-insuree SFTP polling** on per-insuree schedules
- **LLM-powered extraction** for unstructured documents (PDFs, scanned images, free-form Word docs)
- **Rule-based extraction** for structured files (CSV, XLSX with known column mappings)
- **Canonical data normalization** — all insuree formats map to one standard schema
- **Intelligent validation** with blocking and non-blocking rules
- **Human review queue** for low-confidence extractions
- **Reliable TPA API submission** with retry logic and full request/response logging
- **Complete audit trail** for every endorsement record from file detection to TPA acknowledgement
- **TPA management UI** — dashboards, review queues, submission tracking, reporting

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INSUREE SIDE                                 │
│  Insuree A (Mon)    Insuree B (Tue)    Insuree C (Wed)  ...        │
│  SFTP Server        SFTP Server        SFTP Server                  │
│  /uploads/          /uploads/          /uploads/                    │
└────────────┬────────────────┬──────────────────┬───────────────────┘
             │                │                  │
             ▼                ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    INGESTION LAYER                                   │
│   Scheduler (Celery Beat)                                           │
│   Per-insuree cron jobs → SFTP Poller → File Fingerprint Check     │
│   → Download to staging → Move to /processing on SFTP              │
│   → Upload raw file to S3/MinIO                                     │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 DOCUMENT PROCESSING PIPELINE                         │
│                                                                      │
│  ┌──────────────┐   ┌──────────────┐   ┌───────────────────────┐   │
│  │ Format       │   │ Structured   │   │ Unstructured          │   │
│  │ Detector     │──▶│ Extractor    │   │ LLM Extractor         │   │
│  │              │   │ (CSV, XLSX)  │   │ (PDF, Image, DOCX)    │   │
│  └──────────────┘   └──────┬───────┘   └──────────┬────────────┘   │
│                            │                       │                │
│                            ▼                       ▼                │
│                    ┌───────────────────────────────────────┐        │
│                    │     Canonical Schema Mapper            │        │
│                    │  (normalize to EndorsementRecord[])   │        │
│                    └───────────────────┬───────────────────┘        │
└────────────────────────────────────────┼────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     VALIDATION ENGINE                                │
│   Schema Validation → Business Rules → Duplicate Detection         │
│   → Confidence Scoring → Flag for Human Review if needed           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
               ┌───────────────┴──────────────────┐
               │                                  │
               ▼                                  ▼
   ┌───────────────────────┐           ┌──────────────────────┐
   │  Human Review Queue   │           │  Auto-Submit Queue   │
   │  (TPA Operator UI)    │           │  (Celery Workers)    │
   └──────────┬────────────┘           └──────────┬───────────┘
              │                                   │
              └──────────────┬────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    TPA SUBMISSION LAYER                              │
│   Submission Queue → HTTP Client → TPA API                         │
│   Retry Logic (exponential backoff, max 5 attempts)                │
│   Full request/response logging → Update audit trail               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      MANAGEMENT UI (Next.js)                        │
│   Dashboard | File Queue | Review Queue | Submission Tracker       │
│   Insuree Config | Reports | Alert Center                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Folder Structure

```
endorsements-automation/
│
├── backend/
│   ├── app/
│   │   ├── api/                        # FastAPI route handlers
│   │   │   ├── v1/
│   │   │   │   ├── insurees.py         # Insuree config CRUD
│   │   │   │   ├── files.py            # File processing status
│   │   │   │   ├── endorsements.py     # Endorsement record management
│   │   │   │   ├── submissions.py      # TPA submission management
│   │   │   │   ├── review.py           # Human review queue
│   │   │   │   └── reports.py          # Analytics endpoints
│   │   │   └── deps.py                 # Shared dependencies (DB session, auth)
│   │   │
│   │   ├── core/
│   │   │   ├── config.py               # Settings via pydantic-settings
│   │   │   ├── security.py             # JWT auth, API key validation
│   │   │   └── logging.py              # Structured logging setup
│   │   │
│   │   ├── db/
│   │   │   ├── models.py               # SQLAlchemy ORM models
│   │   │   ├── session.py              # DB connection pool
│   │   │   └── migrations/             # Alembic migration files
│   │   │
│   │   ├── ingestion/
│   │   │   ├── sftp_poller.py          # SFTP connection & file polling
│   │   │   ├── file_fingerprint.py     # MD5/SHA hash dedup
│   │   │   └── scheduler.py            # Celery Beat schedule builder
│   │   │
│   │   ├── processing/
│   │   │   ├── format_detector.py      # Detect file type & insuree format
│   │   │   ├── extractors/
│   │   │   │   ├── base.py             # Abstract extractor interface
│   │   │   │   ├── csv_extractor.py    # CSV column mapping extractor
│   │   │   │   ├── xlsx_extractor.py   # Excel extraction with template
│   │   │   │   ├── pdf_extractor.py    # PDF text + table extraction
│   │   │   │   └── llm_extractor.py    # LLM-based unstructured extraction
│   │   │   ├── ocr/
│   │   │   │   ├── preprocessor.py     # Image cleanup before OCR
│   │   │   │   └── engine.py           # Tesseract / cloud OCR wrapper
│   │   │   ├── mapper.py               # Map extracted data → canonical schema
│   │   │   └── pipeline.py             # Orchestrates full processing flow
│   │   │
│   │   ├── validation/
│   │   │   ├── schema_validator.py     # Required fields, types, formats
│   │   │   ├── business_rules.py       # Domain-specific rules per insuree
│   │   │   ├── duplicate_detector.py   # Cross-file and within-file dedup
│   │   │   └── confidence_scorer.py    # Score extraction quality
│   │   │
│   │   ├── submission/
│   │   │   ├── tpa_client.py           # HTTP client for TPA API
│   │   │   ├── payload_builder.py      # Build TPA-specific request payload
│   │   │   ├── retry_handler.py        # Exponential backoff retry logic
│   │   │   └── response_parser.py      # Parse & store TPA responses
│   │   │
│   │   ├── tasks/                      # Celery task definitions
│   │   │   ├── ingestion_tasks.py
│   │   │   ├── processing_tasks.py
│   │   │   ├── validation_tasks.py
│   │   │   └── submission_tasks.py
│   │   │
│   │   └── main.py                     # FastAPI app entry point
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/                   # Sample files per insuree format
│   │
│   ├── scripts/
│   │   ├── seed_insurees.py            # Seed initial insuree configs
│   │   └── backfill.py                 # Reprocess historical files
│   │
│   ├── Dockerfile
│   ├── requirements.txt
│   └── celeryconfig.py
│
├── frontend/
│   ├── src/
│   │   ├── app/                        # Next.js App Router pages
│   │   │   ├── dashboard/
│   │   │   ├── insurees/
│   │   │   ├── files/
│   │   │   ├── review/
│   │   │   ├── submissions/
│   │   │   └── reports/
│   │   ├── components/
│   │   │   ├── ui/                     # shadcn/ui base components
│   │   │   ├── endorsement-table/
│   │   │   ├── document-viewer/        # Side-by-side doc + extracted data
│   │   │   ├── pipeline-status/        # Stage-by-stage tracker
│   │   │   └── charts/
│   │   ├── lib/
│   │   │   ├── api-client.ts           # Backend API calls
│   │   │   └── types.ts                # Shared TypeScript types
│   │   └── hooks/
│   │       └── use-websocket.ts        # Real-time status updates
│   │
│   ├── Dockerfile
│   └── package.json
│
├── infra/
│   ├── docker-compose.yml              # Local development stack
│   ├── docker-compose.prod.yml
│   └── nginx/
│       └── nginx.conf
│
├── docs/
│   ├── insuree-onboarding.md           # Guide for adding a new insuree
│   ├── tpa-api-spec.md                 # TPA API contract documentation
│   └── extraction-templates.md        # How to write extraction templates
│
└── README.md                           # This file
```

---

## 4. Core Modules

### 4.1 SFTP Ingestion Layer

**Location:** `backend/app/ingestion/`

Each insuree has its own SFTP configuration stored in the database. The Celery Beat scheduler generates a cron job per insuree based on their `poll_schedule` field.

#### How Polling Works

1. Celery Beat triggers `poll_sftp_for_insuree(insuree_id)` at the configured schedule
2. SFTP connection is opened using the insuree's stored credentials (host, port, username, private key — decrypted at runtime)
3. Files in the watch folder are listed and filtered by extension whitelist
4. Each file's MD5 hash is computed and checked against `processed_files` table to avoid reprocessing
5. New files are downloaded to a local temp directory, then uploaded to S3/MinIO under `raw/{insuree_id}/{date}/{filename}`
6. On SFTP, the file is moved from `/uploads/` to `/processing/` to signal it has been picked up
7. A `FileIngestionRecord` is created in the DB with status `DOWNLOADED`
8. A Celery task `process_file.delay(file_ingestion_id)` is dispatched

#### SFTP Poller — Key Logic

```python
# backend/app/ingestion/sftp_poller.py

def poll_sftp_for_insuree(insuree_id: str):
    config = get_insuree_config(insuree_id)
    with open_sftp_connection(config) as sftp:
        files = sftp.listdir(config.watch_folder)
        for filename in files:
            if not is_allowed_extension(filename, config.allowed_extensions):
                continue
            file_hash = compute_remote_file_hash(sftp, filename)
            if is_already_processed(file_hash):
                continue
            local_path = download_file(sftp, filename)
            s3_key = upload_to_storage(local_path, insuree_id)
            record = create_file_ingestion_record(insuree_id, filename, s3_key, file_hash)
            sftp.rename(filename, filename.replace('/uploads/', '/processing/'))
            process_file.delay(record.id)
```

---

### 4.2 Document Processing Pipeline

**Location:** `backend/app/processing/`

The pipeline determines which extraction strategy to use based on the insuree's configured `format_type` and the file's actual content. It then maps extracted records to the canonical schema.

#### Processing Flow

```
FileIngestionRecord
        │
        ▼
format_detector.py
        │
        ├── CSV → csv_extractor.py → column_mapper (template-driven)
        ├── XLSX → xlsx_extractor.py → column_mapper (template-driven)
        ├── Structured PDF → pdf_extractor.py (pdfplumber/camelot)
        └── Unstructured PDF / Image / DOCX → llm_extractor.py
                                                       │
                                                       ▼
                                              mapper.py → EndorsementRecord[]
```

#### Extraction Templates (for structured files)

Each insuree has an extraction template stored in the DB as JSON. This defines how their file maps to the canonical schema without writing code.

```json
{
  "insuree_id": "insuree_abc",
  "format_type": "XLSX",
  "sheet_name": "Endorsements",
  "header_row": 2,
  "skip_rows_after_header": 0,
  "column_mappings": {
    "Emp ID": "member.employee_id",
    "Full Name": "member.name",
    "Date of Birth": "member.dob",
    "Action": "endorsement_type",
    "Effective Dt": "effective_date",
    "Plan Code": "coverage.plan_code",
    "Sum Insured": "coverage.sum_insured"
  },
  "value_mappings": {
    "endorsement_type": {
      "ADD": "ADD_MEMBER",
      "DEL": "REMOVE_MEMBER",
      "MOD": "CHANGE_DETAILS"
    }
  },
  "date_format": "%d/%m/%Y"
}
```

---

### 4.3 LLM Extraction Engine

**Location:** `backend/app/processing/extractors/llm_extractor.py`

This is the most powerful part of the system — used for unstructured or semi-structured documents that cannot be reliably parsed with rule-based approaches.

#### Extraction Process

1. **Pre-processing:** For scanned images or image-based PDFs, run OCR first (Tesseract or AWS Textract) to get raw text. For native PDFs and DOCX, extract text directly using `pdfplumber` / `python-docx`.

2. **LLM Prompt:** The extracted text is sent to the LLM with a structured system prompt instructing it to extract endorsement data and return a JSON array conforming to the canonical schema.

3. **Confidence Scoring:** The LLM is asked to include a confidence score per field (0.0–1.0) and an overall record confidence. Records below `MIN_CONFIDENCE_THRESHOLD` (default: `0.80`) are flagged for human review.

4. **Fallback:** If the LLM returns malformed JSON or an error, the record is flagged for human review with status `EXTRACTION_FAILED`.

#### System Prompt Design

```
You are an insurance data extraction assistant. You will be given text from an 
insurance endorsement document submitted by an employer to a TPA.

Extract all endorsement records from the text and return ONLY a valid JSON array.
Each object must follow this schema:

{
  "endorsement_type": "<ADD_MEMBER|REMOVE_MEMBER|CHANGE_DETAILS|CHANGE_SUM_INSURED>",
  "effective_date": "<YYYY-MM-DD>",
  "member": {
    "employee_id": "<string or null>",
    "name": "<full name>",
    "dob": "<YYYY-MM-DD or null>",
    "gender": "<M|F|OTHER|null>",
    "relationship": "<SELF|SPOUSE|CHILD|PARENT|null>"
  },
  "coverage": {
    "plan_code": "<string or null>",
    "sum_insured": <number or null>
  },
  "_confidence": <0.0 to 1.0>,
  "_notes": "<any ambiguity or assumptions made>"
}

If a field is genuinely absent from the document, set it to null.
Do not invent data. Return [] if no endorsement records found.
```

#### LLM Client Configuration

```python
# Supports Claude (Anthropic) or OpenAI — configurable per environment
LLM_PROVIDER = "anthropic"          # or "openai"
LLM_MODEL = "claude-opus-4-6"       # or "gpt-4o"
LLM_MAX_TOKENS = 4096
LLM_TEMPERATURE = 0.0               # Always 0 for extraction — determinism matters
```

---

### 4.4 Validation Engine

**Location:** `backend/app/validation/`

Every extracted record passes through three validation stages before being eligible for submission.

#### Stage 1 — Schema Validation

Checks that required fields are present and correctly typed/formatted. Uses Pydantic models as the validation layer.

Required fields: `endorsement_type`, `effective_date`, `member.name`
Conditionally required: `member.dob` for `ADD_MEMBER`, `member.employee_id` if insuree config requires it

#### Stage 2 — Business Rule Validation

Rules are configurable per insuree and stored as a rule set in the DB. Built-in rules include:

| Rule | Type | Description |
|------|------|-------------|
| `effective_date_not_too_old` | Blocking | Effective date cannot be more than 90 days in the past |
| `effective_date_not_future` | Warning | Effective date is more than 30 days in the future |
| `member_age_range` | Blocking | Member DOB implies age outside 0–75 years |
| `duplicate_add` | Blocking | Member already active on policy (checked via TPA lookup API) |
| `duplicate_remove` | Blocking | Member not found on policy for removal |
| `sum_insured_in_allowed_range` | Warning | Sum insured outside expected range for plan |

#### Stage 3 — Duplicate Detection

Within a single file and across the insuree's recent submissions:
- Composite key: `(insuree_id, policy_number, member.employee_id, endorsement_type, effective_date)`
- Duplicates within a file: second occurrence is flagged as `DUPLICATE_IN_FILE`
- Duplicates against DB (recent 30 days): flagged as `POSSIBLE_DUPLICATE` — warning, not blocking

#### Validation Result Structure

```python
@dataclass
class ValidationResult:
    is_valid: bool                    # False = at least one blocking error
    blocking_errors: list[str]        # Must be fixed before submission
    warnings: list[str]              # Submitted but flagged
    needs_human_review: bool          # True if confidence < threshold or any blocking error
```

---

### 4.5 TPA Submission Layer

**Location:** `backend/app/submission/`

After validation, approved records enter the submission queue. This layer is built for reliability above all else.

#### Submission Queue

Uses Celery with Redis as broker. Each endorsement record becomes an individual job. The queue supports:

- **Priority queues:** Urgent corrections can be pushed to a high-priority queue
- **Batching:** If TPA API supports batch submission, records from the same file are grouped into a single batch request (configurable per TPA endpoint)
- **Rate limiting:** Respects TPA API rate limits (configured as `TPA_REQUESTS_PER_MINUTE`)

#### Retry Strategy

```python
@celery_app.task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,  # seconds — doubles with each retry
    autoretry_for=(TPAAPIException, ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=3600,   # cap at 1 hour
    retry_jitter=True
)
def submit_endorsement(self, endorsement_id: str):
    ...
```

#### Submission Lifecycle

```
QUEUED_FOR_SUBMISSION
        │
        ▼
SUBMISSION_IN_PROGRESS
        │
        ├──[success]──▶ SUBMITTED ──▶ TPA_ACKNOWLEDGED (with TPA reference ID)
        │
        └──[failure]──▶ SUBMISSION_FAILED (retrying)
                               │
                          [max retries]
                               │
                               ▼
                        SUBMISSION_FAILED_FINAL (alert sent, manual retry available)
```

#### Full Request/Response Logging

Every API call is logged immutably to the `submission_logs` table:

```
submission_logs
  id, endorsement_id, attempt_number
  request_timestamp, request_payload (JSON)
  response_timestamp, response_status_code, response_body (JSON)
  tpa_reference_id (if success)
  error_message (if failure)
```

---

### 4.6 Audit & Tracking

**Location:** `backend/app/db/models.py` — `EndorsementAuditLog` table

Every state transition for every endorsement record is written to an immutable audit log:

```sql
endorsement_audit_log (
  id              UUID PRIMARY KEY,
  endorsement_id  UUID REFERENCES endorsement_records(id),
  from_status     VARCHAR,
  to_status       VARCHAR,
  timestamp       TIMESTAMPTZ DEFAULT now(),
  actor           VARCHAR,     -- 'system', 'celery_worker', or TPA operator user_id
  metadata        JSONB        -- extra context (e.g., validation errors, TPA response code)
)
```

This gives you full traceability: for any endorsement, you can reconstruct exactly when it arrived, how long each stage took, who reviewed it, and what the TPA said.

---

### 4.7 Management UI

**Location:** `frontend/`

Built with **Next.js 14 (App Router)**, **Tailwind CSS**, and **shadcn/ui**.

#### Pages & Features

**`/dashboard`**
- Today's file counts by insuree and status
- Submission success rate (last 7 days)
- Pending human review count (highlighted if > 0)
- Recent failures requiring attention
- Pipeline health (queue depths, worker status)

**`/files`**
- Table of all ingested files with columns: Insuree, Filename, Received At, Status, Records Count, Actions
- Drill into a file to see all extracted records and their individual statuses
- Filter by insuree, date range, status, format type

**`/review`**
- Human review queue for low-confidence extractions and validation failures
- **Side-by-side view:** Original document rendered on the left, extracted fields as editable form on the right
- Operator can correct any field, add notes, then Approve (submits) or Reject (discards)
- Keyboard shortcuts for fast processing

**`/submissions`**
- Full submission tracker with filters by insuree, date, TPA status, endorsement type
- See TPA reference IDs, response codes per record
- One-click **manual retry** for `SUBMISSION_FAILED_FINAL` records
- Download submission report as CSV

**`/insurees`**
- List of all configured insurees with their schedule, format type, last file received, last success
- Create / edit insuree config (SFTP credentials, schedule, extraction template, field mappings)
- **Test SFTP connection** button
- **Run extraction test** — upload a sample file and preview what would be extracted

**`/reports`**
- Weekly volume per insuree (bar chart)
- Endorsement type breakdown (pie chart)
- SLA compliance: time from file receipt to TPA submission (target: < 4 hours)
- Error rate by insuree — useful for identifying insurees with problematic formats
- Export reports as PDF or CSV

---

## 5. Data Models & Schema

### Core Tables

```sql
-- Insuree configuration
insuree_configs (
  id                    UUID PRIMARY KEY,
  name                  VARCHAR NOT NULL,
  code                  VARCHAR UNIQUE NOT NULL,    -- short code e.g. 'ACME_CORP'
  sftp_host             VARCHAR,
  sftp_port             INTEGER DEFAULT 22,
  sftp_username         VARCHAR,
  sftp_private_key      TEXT,                       -- encrypted at rest
  sftp_watch_folder     VARCHAR,
  poll_schedule         VARCHAR,                    -- cron expression
  allowed_extensions    TEXT[],                     -- ['csv', 'xlsx', 'pdf']
  format_type           VARCHAR,                    -- 'STRUCTURED' | 'SEMI_STRUCTURED' | 'UNSTRUCTURED'
  extraction_template   JSONB,
  tpa_endpoint_override VARCHAR,                    -- if different endpoint per insuree
  min_confidence        FLOAT DEFAULT 0.80,
  is_active             BOOLEAN DEFAULT true,
  created_at            TIMESTAMPTZ DEFAULT now(),
  updated_at            TIMESTAMPTZ DEFAULT now()
)

-- One record per file picked up from SFTP
file_ingestion_records (
  id            UUID PRIMARY KEY,
  insuree_id    UUID REFERENCES insuree_configs(id),
  filename      VARCHAR NOT NULL,
  s3_key        VARCHAR NOT NULL,
  file_hash     VARCHAR NOT NULL UNIQUE,
  file_format   VARCHAR,                    -- detected format
  file_size_kb  INTEGER,
  status        VARCHAR NOT NULL,           -- see lifecycle statuses below
  record_count  INTEGER,                    -- total records extracted
  error_message TEXT,
  received_at   TIMESTAMPTZ DEFAULT now(),
  processed_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ DEFAULT now()
)

-- One record per endorsement row extracted from a file
endorsement_records (
  id                  UUID PRIMARY KEY,
  file_id             UUID REFERENCES file_ingestion_records(id),
  insuree_id          UUID REFERENCES insuree_configs(id),
  row_index           INTEGER,             -- original row in source file
  endorsement_type    VARCHAR NOT NULL,    -- ADD_MEMBER | REMOVE_MEMBER | etc.
  effective_date      DATE,
  member_data         JSONB NOT NULL,      -- name, dob, employee_id, gender, relationship
  coverage_data       JSONB,              -- plan_code, sum_insured
  raw_extracted_json  JSONB,              -- exactly what was extracted before mapping
  confidence_score    FLOAT,
  validation_status   VARCHAR,            -- PASSED | FAILED | WARNING
  validation_errors   JSONB,
  review_status       VARCHAR,            -- PENDING | APPROVED | REJECTED
  reviewed_by         UUID,
  reviewed_at         TIMESTAMPTZ,
  reviewer_notes      TEXT,
  submission_status   VARCHAR,
  tpa_reference_id    VARCHAR,
  submitted_at        TIMESTAMPTZ,
  created_at          TIMESTAMPTZ DEFAULT now()
)

-- Immutable audit log
endorsement_audit_log (
  id              UUID PRIMARY KEY,
  endorsement_id  UUID REFERENCES endorsement_records(id),
  from_status     VARCHAR,
  to_status       VARCHAR,
  actor           VARCHAR,
  metadata        JSONB,
  created_at      TIMESTAMPTZ DEFAULT now()
)

-- Full submission log per API call attempt
submission_logs (
  id                  UUID PRIMARY KEY,
  endorsement_id      UUID REFERENCES endorsement_records(id),
  attempt_number      INTEGER NOT NULL,
  request_timestamp   TIMESTAMPTZ,
  request_payload     JSONB,
  response_timestamp  TIMESTAMPTZ,
  response_status     INTEGER,
  response_body       JSONB,
  tpa_reference_id    VARCHAR,
  error_message       TEXT,
  created_at          TIMESTAMPTZ DEFAULT now()
)
```

### Canonical Endorsement Schema (Python / Pydantic)

```python
class MemberData(BaseModel):
    employee_id: str | None
    name: str
    dob: date | None
    gender: Literal["M", "F", "OTHER"] | None
    relationship: Literal["SELF", "SPOUSE", "CHILD", "PARENT"] | None

class CoverageData(BaseModel):
    plan_code: str | None
    sum_insured: float | None
    coverage_type: str | None

class EndorsementRecord(BaseModel):
    endorsement_type: Literal[
        "ADD_MEMBER", "REMOVE_MEMBER",
        "CHANGE_DETAILS", "CHANGE_SUM_INSURED"
    ]
    effective_date: date
    member: MemberData
    coverage: CoverageData | None
    confidence_score: float = 1.0
    extraction_notes: str | None
```

---

## 6. Insuree Configuration System

Each insuree is fully configured in the DB — no code changes needed to onboard a new insuree (unless their format is truly novel and requires a new extractor strategy).

### Format Types

| Format Type | When to Use | Extractor Used |
|-------------|-------------|----------------|
| `STRUCTURED_CSV` | Clean CSV with consistent columns | `csv_extractor.py` |
| `STRUCTURED_XLSX` | Excel file with consistent layout | `xlsx_extractor.py` |
| `SEMI_STRUCTURED_PDF` | PDF with tables, consistent layout | `pdf_extractor.py` |
| `UNSTRUCTURED_PDF` | Narrative/free-form PDF, mixed layout | `llm_extractor.py` |
| `SCANNED_IMAGE` | Image-based PDF or image file | OCR → `llm_extractor.py` |
| `UNSTRUCTURED_DOCX` | Free-form Word document | `llm_extractor.py` |

### Template Versioning

Extraction templates are versioned. When an insuree changes their format:

1. Create a new template version (don't overwrite the old one)
2. Set the new template's `effective_from` date
3. The system automatically uses the correct template version based on the file's received date — old files continue to process with the old template

---

## 7. API Reference

Base URL: `https://api.your-platform.com/api/v1`

### Authentication

All endpoints require a Bearer JWT token obtained via:
```
POST /auth/login
Body: { "username": "...", "password": "..." }
Returns: { "access_token": "...", "token_type": "bearer" }
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/insurees` | List all insurees |
| `POST` | `/insurees` | Create insuree config |
| `PUT` | `/insurees/{id}` | Update insuree config |
| `POST` | `/insurees/{id}/test-sftp` | Test SFTP connectivity |
| `POST` | `/insurees/{id}/trigger-poll` | Manually trigger SFTP poll |
| `GET` | `/files` | List file ingestion records |
| `GET` | `/files/{id}` | File detail with all records |
| `GET` | `/endorsements` | List endorsements (filterable) |
| `GET` | `/endorsements/{id}` | Single endorsement detail |
| `POST` | `/endorsements/{id}/approve` | Approve for submission (review queue) |
| `POST` | `/endorsements/{id}/reject` | Reject endorsement |
| `POST` | `/endorsements/{id}/retry-submission` | Retry failed submission |
| `GET` | `/submissions` | List submissions with TPA status |
| `GET` | `/reports/volume` | Volume by insuree and date range |
| `GET` | `/reports/sla` | SLA compliance metrics |
| `GET` | `/reports/errors` | Error rate by insuree |

---

## 8. Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Backend Framework | **FastAPI** (Python) | Async support, auto-generated OpenAPI docs, Pydantic built-in |
| Task Queue | **Celery** + **Redis** | Battle-tested for scheduled jobs and async workers |
| Database | **PostgreSQL** | JSONB support for flexible extracted data, strong ACID guarantees |
| File Storage | **MinIO** (self-hosted S3-compatible) | Store raw files and extracted JSON; swap to AWS S3 in production |
| Structured Extraction | **pdfplumber**, **camelot**, **openpyxl** | Best Python-native options per format |
| OCR | **AWS Textract** (primary), **Tesseract** (fallback) | Textract significantly outperforms open-source for insurance docs |
| LLM Extraction | **Anthropic Claude API** | Superior at structured extraction from messy documents |
| Frontend | **Next.js 14**, **Tailwind CSS**, **shadcn/ui** | Modern, type-safe, great DX |
| Auth | **JWT** + **bcrypt** (simple) or **Keycloak** (enterprise) | Depending on TPA's existing auth infrastructure |
| Monitoring | **Grafana** + **Prometheus** | Queue depth, submission rates, error rates |
| Log Aggregation | **Loki** or **Datadog** | Structured logs from all services |
| Containerization | **Docker** + **Docker Compose** | Local dev parity with production |
| SFTP Client | **Paramiko** (Python) | Mature, well-tested SFTP library |

---

## 9. Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/endorsements_db

# Redis / Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# File Storage (MinIO / S3)
STORAGE_ENDPOINT=http://localhost:9000
STORAGE_ACCESS_KEY=minioadmin
STORAGE_SECRET_KEY=minioadmin
STORAGE_BUCKET_NAME=endorsements

# LLM Provider
LLM_PROVIDER=anthropic                  # anthropic | openai
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...                   # if using OpenAI
LLM_MODEL=claude-opus-4-6
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=4096

# OCR Provider
OCR_PROVIDER=aws_textract               # aws_textract | tesseract
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=ap-south-1

# TPA API
TPA_API_BASE_URL=https://api.tpa-provider.com/v2
TPA_API_KEY=...
TPA_REQUESTS_PER_MINUTE=60

# Auth
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480

# Application
APP_ENV=development                     # development | staging | production
MIN_CONFIDENCE_THRESHOLD=0.80
MAX_SUBMISSION_RETRIES=5
ALERT_EMAIL_TO=ops@yourcompany.com

# SFTP Credentials Encryption
SFTP_CREDENTIAL_ENCRYPTION_KEY=...     # Fernet key for encrypting stored credentials
```

---

## 10. Database Setup

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run migrations
cd backend
alembic upgrade head

# Seed initial data (optional)
python scripts/seed_insurees.py
```

---

## 11. Running the Project

### Local Development

```bash
# 1. Start infrastructure
docker-compose up -d postgres redis minio

# 2. Start backend API
cd backend
uvicorn app.main:app --reload --port 8000

# 3. Start Celery worker
celery -A app.tasks worker --loglevel=info --concurrency=4

# 4. Start Celery Beat (scheduler)
celery -A app.tasks beat --loglevel=info

# 5. Start frontend
cd frontend
npm install
npm run dev
```

### Full Stack via Docker Compose

```bash
docker-compose up --build
```

Services available at:
- Frontend UI: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API Docs (Swagger): `http://localhost:8000/docs`
- MinIO Console: `http://localhost:9001`
- Flower (Celery monitor): `http://localhost:5555`

---

## 12. Deployment

### Recommended Production Architecture

```
                    ┌─────────────┐
                    │   Nginx     │  (SSL termination, reverse proxy)
                    └──────┬──────┘
                   ┌───────┴──────┐
                   │              │
            ┌──────┴──────┐ ┌────┴──────┐
            │  Next.js    │ │  FastAPI  │
            │  (2+ pods)  │ │  (2+ pods)│
            └─────────────┘ └─────┬─────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
       ┌──────┴──────┐   ┌───────┴──────┐   ┌───────┴──────┐
       │  PostgreSQL │   │    Redis     │   │    MinIO     │
       │  (RDS/etc)  │   │  (ElastiC.)  │   │  (or S3)     │
       └─────────────┘   └─────────────┘   └─────────────┘
              │
       ┌──────┴──────┐
       │   Celery    │
       │  Workers    │
       │  (2+ pods)  │
       └─────────────┘
```

### Production Checklist

- [ ] Rotate all default credentials and API keys
- [ ] Enable PostgreSQL SSL (`sslmode=require`)
- [ ] Store SFTP private keys encrypted (Fernet) in DB, never in plaintext
- [ ] Set up automated DB backups (daily at minimum)
- [ ] Configure Celery worker autoscaling based on queue depth
- [ ] Set up alerting for queue depth > 1000, error rate > 5%, failed submissions
- [ ] Enable structured logging to log aggregation service
- [ ] Configure TPA API rate limit monitoring
- [ ] Set up health check endpoints for all services (`/health`)

---

## 13. Implementation Phases

### Phase 1 — Foundation (Weeks 1–4)
- Set up project structure and infrastructure (Docker Compose, PostgreSQL, Redis, MinIO)
- Implement SFTP poller for 2 pilot insurees
- Build structured extractor (CSV + XLSX) with template-driven column mapping
- Manual submission trigger (no queue yet)
- Basic status dashboard (file received, extracted, submitted)
- Canonical schema + Pydantic models
- Core DB tables and migrations

### Phase 2 — LLM Extraction & Template Engine (Weeks 5–8)
- Implement `llm_extractor.py` with Claude API integration
- OCR pipeline for scanned documents (Textract integration)
- Template versioning system
- Confidence scoring and human review flagging
- Human review UI (side-by-side document viewer + editable fields)
- Onboard 3–5 more insurees across different format types

### Phase 3 — Reliable Submission & Full Tracking (Weeks 9–12)
- Production-grade Celery submission queue with retry logic
- Full audit trail and state machine
- TPA API error code mapping and handling
- Alerting system (email/webhook on failures, daily summaries)
- Duplicate detection across files
- Business rule validation engine

### Phase 4 — Full UI & Operations (Weeks 13–16)
- Complete management UI all pages
- Insuree self-service configuration (test SFTP, preview extraction)
- Reporting and analytics dashboards
- SLA tracking and breach alerting
- Load testing and performance optimization
- Runbooks and operations documentation

---

## 14. Error Handling Strategy

### Error Categories and Responses

| Error Type | Example | System Response |
|------------|---------|-----------------|
| SFTP connection failure | Wrong credentials, host down | Retry 3x, alert ops, mark poll as failed |
| File download failure | Network interruption mid-download | Retry, don't move file to /processing/ |
| Extraction failure (structured) | Unexpected column format | Flag file for manual review, alert |
| LLM extraction failure | API error, malformed JSON response | Retry LLM call 2x, then flag for human review |
| OCR failure | Image too blurry | Flag record for human review with original image |
| Validation blocking error | Missing required field | Block submission, human review queue |
| TPA API 4xx | Invalid payload | Log response, flag as SUBMISSION_FAILED, do NOT retry |
| TPA API 5xx | Server error | Retry with exponential backoff |
| TPA API timeout | Slow response | Retry up to 5 times |
| Duplicate detection | Same member submitted twice | Flag as warning, allow operator to decide |

### Error Notification

Operators are notified via email/webhook for:
- Any file that reaches `EXTRACTION_FAILED` status
- Any submission that reaches `SUBMISSION_FAILED_FINAL`
- Daily digest: files processed, success rate, pending reviews, failures
- SLA breach: any file not submitted within 4 hours of receipt

---

## 15. Security Considerations

**SFTP Credentials:** Private keys and passwords stored encrypted at rest using Fernet symmetric encryption. The encryption key is stored in environment variables / secrets manager, never in DB.

**API Authentication:** JWT tokens with short expiry (8 hours). Refresh token pattern for long sessions. Role-based access: `ADMIN` (full access), `OPERATOR` (review + submit), `VIEWER` (read-only).

**Data Privacy:** All endorsement data contains PII (names, DOBs, employee IDs). Ensure PostgreSQL encryption at rest. Use column-level encryption for especially sensitive fields if required. Log sanitization — never log full member data in application logs.

**TPA API Keys:** Stored in environment variables / secrets manager. Rotated quarterly.

**Audit Trail:** The `endorsement_audit_log` table is append-only. Application DB user does not have DELETE permission on this table.

**File Storage:** S3/MinIO bucket is private, not publicly accessible. Presigned URLs used for document viewer in the UI (30-minute expiry).

---

## 16. Adding a New Insuree

1. **Gather requirements from the insuree:**
   - SFTP host, port, username, and provide them a public key (or get their password)
   - Watch folder path on their SFTP
   - Day and time they send files each week
   - Sample files in their actual format

2. **Identify format type:**
   - Open the sample files and determine if they are structured (CSV/XLSX with consistent columns) or unstructured (PDF narrative, scanned image, mixed Word doc)

3. **Create extraction template (for structured files):**
   - Map their column names to the canonical schema fields
   - Document any value transformations (e.g., their "A" means our "ADD_MEMBER")
   - Note the date format they use

4. **Add insuree via the UI (`/insurees` → New Insuree):**
   - Fill in SFTP connection details
   - Set poll schedule (cron format)
   - Select format type
   - Upload or paste extraction template JSON
   - Click "Test SFTP Connection" to verify

5. **Run an extraction test:**
   - Upload one of their sample files via "Test Extraction" in the UI
   - Review the extracted records and adjust the template if needed

6. **Enable the insuree** — toggle `is_active: true`

The scheduler will automatically pick up the new insuree's cron job on next Celery Beat heartbeat.

---

## 17. Monitoring & Alerting

### Key Metrics to Track

| Metric | Alert Threshold |
|--------|----------------|
| Celery queue depth (submission) | > 500 jobs |
| Submission success rate (1h window) | < 95% |
| Files pending review | > 50 |
| SFTP poll failure rate | Any consecutive 3 failures per insuree |
| Average extraction confidence | < 0.75 per insuree |
| SLA: receipt to submission | > 4 hours for any file |
| LLM API error rate | > 2% of calls |
| TPA API error rate | > 1% of submissions |

### Recommended Dashboards (Grafana)

- **Operations Overview:** Real-time queue depths, submission rates, active workers
- **Per-Insuree Health:** Last poll time, last success, error rate, volume trend
- **SLA Dashboard:** Distribution of file processing time, breach count
- **Extraction Quality:** Confidence score distribution, review queue trend

---

## 18. FAQ

**Q: What happens if the LLM extracts incorrect data and it gets submitted to the TPA?**
A: The confidence scoring and human review queue are the primary safeguards. Any record below the configured confidence threshold requires operator approval. Additionally, business rule validation catches common errors (invalid dates, impossible ages, etc.). For critical insurees, you can set `min_confidence: 1.0` effectively forcing all LLM extractions through human review.

**Q: What if an insuree sends their file on an unusual day or time?**
A: The SFTP poller picks up any file present in the watch folder during the scheduled poll. If they send early, the file just waits until the next scheduled poll. You can also trigger a manual poll from the UI at any time. Alternatively, configure a more frequent poll schedule (e.g., every 6 hours) for insurees with irregular schedules.

**Q: What if the TPA API goes down during a busy submission period?**
A: The Celery retry queue handles this automatically. Submissions retry with exponential backoff for up to 5 attempts over several hours. If TPA is down for an extended period, all records remain in `QUEUED_FOR_SUBMISSION` and process when the API recovers. No data is lost.

**Q: Can we support multiple TPA APIs (if TPA changes or we onboard multiple TPAs)?**
A: Yes — the `tpa_client.py` is abstracted behind an interface. Per-insuree TPA endpoint overrides are supported. Adding a new TPA integration requires implementing the `TPAClientInterface` and registering the new client.

**Q: How do we handle an insuree that changes their file format?**
A: Create a new extraction template version with an `effective_from` date. The system uses the correct template version based on when the file was received. No re-extraction of historical files is needed unless you choose to backfill.

---

## License

Proprietary — Internal use only.

---

*Last updated: February 2026*