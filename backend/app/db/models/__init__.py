"""
Models package — re-exports Base and all models.

Import models here so Alembic's `target_metadata = Base.metadata`
picks up every table automatically.

When adding a new model:
    1. Create `app/db/models/<table_name>.py`
    2. Import it here
"""

from app.db.models.base import Base
from app.db.models.user import User
from app.db.models.pipeline_execution import PipelineExecution

__all__ = [
    "Base",
    "User",
    "PipelineExecution",
]

