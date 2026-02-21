"""Human review queue endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db

router = APIRouter(
    prefix="/review",
    tags=["Review"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/")
async def list_review_queue(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    """List endorsements pending human review."""
    return {"data": [], "message": "Not yet implemented"}
