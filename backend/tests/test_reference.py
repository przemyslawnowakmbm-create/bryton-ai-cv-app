"""Tests for the SFIA reference data API."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.seed import seed_sfia_levels


@pytest.mark.asyncio
async def test_sfia_levels_empty_returns_empty_list(client: AsyncClient):
    """GET /api/reference/sfia-levels returns [] when no data is seeded."""
    response = await client.get("/api/reference/sfia-levels")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_sfia_levels_returns_seeded_data(
    client: AsyncClient, db_session: AsyncSession
):
    """GET /api/reference/sfia-levels returns 7 items after seeding."""
    await seed_sfia_levels(db_session)
    await db_session.commit()

    response = await client.get("/api/reference/sfia-levels")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 7


@pytest.mark.asyncio
async def test_sfia_levels_ordered_by_level(
    client: AsyncClient, db_session: AsyncSession
):
    """GET /api/reference/sfia-levels returns items ordered by level ascending."""
    await seed_sfia_levels(db_session)
    await db_session.commit()

    response = await client.get("/api/reference/sfia-levels")
    assert response.status_code == 200
    data = response.json()
    levels = [item["level"] for item in data]
    assert levels == sorted(levels)
    assert levels == list(range(1, 8))


@pytest.mark.asyncio
async def test_sfia_level_response_shape(
    client: AsyncClient, db_session: AsyncSession
):
    """Each SFIA level response item has id, level, label, description fields."""
    await seed_sfia_levels(db_session)
    await db_session.commit()

    response = await client.get("/api/reference/sfia-levels")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    item = data[0]
    assert "id" in item
    assert "level" in item
    assert "label" in item
    assert "description" in item
