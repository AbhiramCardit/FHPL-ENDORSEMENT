"""File ingestion record endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db

router = APIRouter(
    prefix="/files",
    tags=["Files"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/")
async def list_files(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    """List all file ingestion records."""
    return {"data": [], "message": "Not yet implemented"}


@router.get("/{file_id}")
async def get_file(file_id: UUID, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Get details for one file record."""
    return {"message": "Not yet implemented"}
