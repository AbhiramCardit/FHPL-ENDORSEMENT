"""
Pydantic Settings — centralized configuration loaded from environment variables.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ── Database (individual vars, like healthpay-ai) ──
    POSTGRES_USER: str = "endorsements_user"
    POSTGRES_PASSWORD: str = "endorsements_pass"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "endorsements_db"

    @property
    def DATABASE_URL(self) -> str:
        """Async URL for app runtime (asyncpg)."""
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync URL for Alembic migrations (psycopg2)."""
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # ── Redis / Celery ────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # ── File Storage ──────────────────────────
    STORAGE_ENDPOINT: str = "http://localhost:9000"
    STORAGE_ACCESS_KEY: str = "minioadmin"
    STORAGE_SECRET_KEY: str = "minioadmin"
    STORAGE_BUCKET_NAME: str = "endorsements"

    # ── LLM Provider ─────────────────────────
    LLM_PROVIDER: str = "anthropic"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_MODEL: str = "claude-sonnet-4-20250514"
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 4096

    # ── Google Gemini ────────────────────────
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # ── LangSmith Tracing ────────────────────
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_PROJECT: str = "fhpl-endorsements"
    LANGSMITH_TRACING: bool = False

    # ── OCR ───────────────────────────────────
    OCR_PROVIDER: str = "tesseract"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"

    # ── TPA API ───────────────────────────────
    TPA_API_BASE_URL: str = "https://api.tpa-provider.com/v2"
    TPA_API_KEY: str = ""
    TPA_REQUESTS_PER_MINUTE: int = 60

    # ── Auth / JWT ────────────────────────────
    JWT_SECRET_KEY: str = "change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # ── Application ───────────────────────────
    APP_ENV: str = "development"
    MIN_CONFIDENCE_THRESHOLD: float = 0.80
    MAX_SUBMISSION_RETRIES: int = 5
    ALERT_EMAIL_TO: str = ""

    # ── SFTP Encryption ──────────────────────
    SFTP_CREDENTIAL_ENCRYPTION_KEY: str = ""

    model_config = {"env_file": ["../.env", ".env"], "extra": "ignore"}


settings = Settings()
