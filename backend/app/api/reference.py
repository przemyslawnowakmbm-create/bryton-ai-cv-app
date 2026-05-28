from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.sfia_level import SfiaLevel
from app.schemas.reference import SfiaLevelResponse

router = APIRouter(prefix="/api/reference", tags=["reference"])


@router.get("/sfia-levels", response_model=list[SfiaLevelResponse])
async def list_sfia_levels(db: AsyncSession = Depends(get_db)):
    """Return all SFIA levels ordered by level number ascending."""
    result = await db.execute(select(SfiaLevel).order_by(SfiaLevel.level))
    return [SfiaLevelResponse.model_validate(r) for r in result.scalars().all()]
