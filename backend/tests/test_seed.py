"""Tests for the SFIA levels seed function."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sfia_level import SfiaLevel
from app.services.seed import seed_sfia_levels


@pytest.mark.asyncio
async def test_seed_sfia_levels_creates_7_records(db_session: AsyncSession):
    """seed_sfia_levels creates exactly 7 records on an empty database."""
    await seed_sfia_levels(db_session)
    await db_session.commit()

    result = await db_session.execute(select(SfiaLevel))
    levels = result.scalars().all()
    assert len(levels) == 7


@pytest.mark.asyncio
async def test_seed_sfia_levels_idempotent(db_session: AsyncSession):
    """Calling seed_sfia_levels twice still results in exactly 7 records."""
    await seed_sfia_levels(db_session)
    await db_session.commit()

    # Call again — should be a no-op
    await seed_sfia_levels(db_session)
    await db_session.commit()

    result = await db_session.execute(select(SfiaLevel))
    levels = result.scalars().all()
    assert len(levels) == 7


@pytest.mark.asyncio
async def test_seed_sfia_levels_correct_data(db_session: AsyncSession):
    """Level 1 label = 'Follow', level 7 label = 'Set Strategy/Inspire'."""
    await seed_sfia_levels(db_session)
    await db_session.commit()

    result = await db_session.execute(
        select(SfiaLevel).order_by(SfiaLevel.level)
    )
    levels = result.scalars().all()
    assert levels[0].level == 1
    assert levels[0].label == "Follow"
    assert levels[6].level == 7
    assert levels[6].label == "Set Strategy/Inspire"


@pytest.mark.asyncio
async def test_seed_sfia_levels_all_have_descriptions(db_session: AsyncSession):
    """All 7 SFIA levels have non-empty descriptions."""
    await seed_sfia_levels(db_session)
    await db_session.commit()

    result = await db_session.execute(select(SfiaLevel))
    levels = result.scalars().all()
    for level in levels:
        assert level.description
        assert len(level.description) > 10
