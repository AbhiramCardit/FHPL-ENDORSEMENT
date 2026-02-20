"""
File ingestion record endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db

router = APIRouter(prefix="/files", tags=["Files"])


@router.get("/")
async def list_files(db: AsyncSession = Depends(get_db)):
    """List all file ingestion records (filterable)."""
    return {"data": [], "message": "Not yet implemented"}


@router.get("/{file_id}")
async def get_file(file_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get file detail with all extracted records."""
    return {"message": "Not yet implemented"}
