"""Insuree configuration CRUD and operational endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db

router = APIRouter(
    prefix="/insurees",
    tags=["Insurees"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/")
async def list_insurees(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    """List all insuree configurations."""
    return {"data": [], "message": "Not yet implemented"}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_insuree(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Create a new insuree configuration."""
    return {"message": "Not yet implemented"}


@router.put("/{insuree_id}")
async def update_insuree(insuree_id: UUID, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Update an existing insuree configuration."""
    return {"message": "Not yet implemented"}


@router.post("/{insuree_id}/test-sftp")
async def test_sftp(insuree_id: UUID, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Test SFTP connectivity for an insuree."""
    return {"message": "Not yet implemented"}


@router.post("/{insuree_id}/trigger-poll")
async def trigger_poll(insuree_id: UUID, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Manually trigger SFTP polling for an insuree."""
    return {"message": "Not yet implemented"}
