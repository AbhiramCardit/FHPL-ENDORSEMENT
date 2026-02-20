# FHPL Endorsement Automation Platform

> **Professional enterprise-grade system** — all code must follow the standards below.

---

## For AI Agents & Contributors

### This Is an Enterprise System

This is a **production-grade, enterprise-level** insurance endorsement automation platform for a Third Party Administrator (TPA). It handles sensitive PII data, financial records, and must be audit-compliant. Every piece of code must reflect this.

### Code Standards — Non-Negotiable

| Principle | What It Means |
|-----------|---------------|
| **Clean Architecture** | Layers are separated: API → Repository → Models. No DB calls in route handlers. No HTTP concerns in repositories. |
| **Repository Pattern** | All DB operations live in `app/repositories/<entity>.py`. Functions accept `AsyncSession` explicitly. Repositories flush but never commit — the session lifecycle is controlled by the API dependency layer. |
| **One Model Per File** | Models live in `app/db/models/<table_name>.py`. Register every new model in `app/db/models/__init__.py` so Alembic sees it. |
| **Type Hints Everywhere** | Every function has full type annotations. Use `from __future__ import annotations` where needed. |
| **Async by Default** | All DB and I/O operations are async (`AsyncSession`, `httpx.AsyncClient`, etc.). |
| **No Magic Strings** | Use enums or constants for statuses, roles, types. Define them in a shared `app/core/constants.py` when they span modules. |
| **Error Handling** | Never swallow exceptions. Use structured logging (`app/core/logging.py`). Raise domain-specific exceptions. |
| **Security First** | Hash passwords with bcrypt. JWT for auth. Never log PII. Encrypt SFTP credentials at rest. Validate all inputs with Pydantic. |
| **Docstrings** | Every module, class, and public function has a docstring. |
| **No Premature Code** | Don't add models, tables, or functions until they are actually needed. Build incrementally. |

### Project Structure

```
backend/
├── app/
│   ├── api/                    # FastAPI route handlers (thin — delegates to repositories)
│   │   ├── deps.py             # Shared dependencies (DB session, auth)
│   │   └── v1/                 # Versioned API routes
│   ├── core/                   # Config, security, logging, constants
│   ├── db/
│   │   ├── models/             # One file per table (base.py + <table>.py)
│   │   │   ├── base.py         # DeclarativeBase, shared helpers
│   │   │   ├── user.py         # User model
│   │   │   └── __init__.py     # Re-exports Base + all models
│   │   ├── migrations/         # Alembic
│   │   └── session.py          # Async engine + session factory
│   ├── repositories/           # Data-access layer (one file per aggregate root)
│   │   └── users.py            # create, get, list, update, delete, set_active, etc.
│   ├── ingestion/              # SFTP polling, file fingerprinting, scheduling
│   ├── processing/             # Extractors, OCR, mapper, pipeline
│   ├── validation/             # Schema, business rules, duplicates, confidence
│   ├── submission/             # TPA client, payload builder, retry, response parser
│   ├── tasks/                  # Celery task definitions
│   └── main.py                 # FastAPI app entry point
├── scripts/                    # Seed data, backfill, one-off scripts
├── tests/                      # Unit + integration tests
├── alembic.ini
├── celeryconfig.py
├── Dockerfile
└── requirements.txt
```

### Adding a New Table

1. Create `app/db/models/<table_name>.py` — import `Base`, `generate_uuid`, `utcnow` from `base.py`
2. Add the import in `app/db/models/__init__.py`
3. Create `app/repositories/<entity>.py` with all CRUD operations
4. Run `alembic revision --autogenerate -m "add <table_name> table"`
5. Run `alembic upgrade head`

### Key Technologies

- **Backend:** FastAPI (async), SQLAlchemy 2.0 (async), Alembic, Celery + Redis
- **Database:** PostgreSQL (JSONB, UUID, timestamptz)
- **Frontend:** React + Vite (TypeScript), React Router
- **Infra:** Docker Compose, Nginx, MinIO (S3-compatible)

### Running Locally

```bash
cp .env.example .env
docker-compose up -d postgres redis minio

# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
python -m scripts.seed_insurees        # seed dev users
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

### Full spec

See [`info.md`](./info.md) for the complete system specification.
