"""
Human review queue endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user

router = APIRouter(prefix="/review", tags=["Review"])


@router.get("/")
async def list_review_queue(db: AsyncSession = Depends(get_db)):
    """List endorsements pending human review."""
    return {"data": [], "message": "Not yet implemented"}
