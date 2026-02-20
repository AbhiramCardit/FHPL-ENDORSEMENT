"""
Insuree configuration CRUD + SFTP test + manual poll trigger.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user

router = APIRouter(prefix="/insurees", tags=["Insurees"])


@router.get("/")
async def list_insurees(db: AsyncSession = Depends(get_db)):
    """List all insuree configurations."""
    # TODO: implement query
    return {"data": [], "message": "Not yet implemented"}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_insuree(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Create a new insuree configuration."""
    # TODO: implement creation
    return {"message": "Not yet implemented"}


@router.put("/{insuree_id}")
async def update_insuree(insuree_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Update an existing insuree configuration."""
    # TODO: implement update
    return {"message": "Not yet implemented"}


@router.post("/{insuree_id}/test-sftp")
async def test_sftp(insuree_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Test SFTP connectivity for an insuree."""
    # TODO: implement SFTP test
    return {"message": "Not yet implemented"}


@router.post("/{insuree_id}/trigger-poll")
async def trigger_poll(insuree_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Manually trigger SFTP poll for an insuree."""
    # TODO: dispatch celery task
    return {"message": "Not yet implemented"}
