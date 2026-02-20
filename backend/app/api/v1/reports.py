"""
Analytics & reporting endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/volume")
async def get_volume_report(db: AsyncSession = Depends(get_db)):
    """Volume by insuree and date range."""
    return {"data": [], "message": "Not yet implemented"}


@router.get("/sla")
async def get_sla_report(db: AsyncSession = Depends(get_db)):
    """SLA compliance metrics."""
    return {"data": [], "message": "Not yet implemented"}


@router.get("/errors")
async def get_error_report(db: AsyncSession = Depends(get_db)):
    """Error rate by insuree."""
    return {"data": [], "message": "Not yet implemented"}
