"""
TPA submission management endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db

router = APIRouter(prefix="/submissions", tags=["Submissions"])


@router.get("/")
async def list_submissions(db: AsyncSession = Depends(get_db)):
    """List submissions with TPA status."""
    return {"data": [], "message": "Not yet implemented"}
