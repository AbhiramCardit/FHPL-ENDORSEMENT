"""
Endorsement record management endpoints.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user

router = APIRouter(prefix="/endorsements", tags=["Endorsements"])


@router.get("/")
async def list_endorsements(db: AsyncSession = Depends(get_db)):
    """List endorsements (filterable by insuree, status, type, date)."""
    return {"data": [], "message": "Not yet implemented"}


@router.get("/{endorsement_id}")
async def get_endorsement(endorsement_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get single endorsement detail."""
    return {"message": "Not yet implemented"}


@router.post("/{endorsement_id}/approve")
async def approve_endorsement(endorsement_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Approve endorsement for submission (from review queue)."""
    return {"message": "Not yet implemented"}


@router.post("/{endorsement_id}/reject")
async def reject_endorsement(endorsement_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Reject endorsement (from review queue)."""
    return {"message": "Not yet implemented"}


@router.post("/{endorsement_id}/retry-submission")
async def retry_submission(endorsement_id: UUID, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Retry a failed submission."""
    return {"message": "Not yet implemented"}
