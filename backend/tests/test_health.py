"""Tests for health check endpoints."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient


def _make_mock_session(execute_side_effect=None):
    """Build a mock async context manager that mimics async_session()."""
    mock_session = AsyncMock()
    if execute_side_effect:
        mock_session.execute = AsyncMock(side_effect=execute_side_effect)
    else:
        mock_session.execute = AsyncMock(return_value=None)

    # async_session() returns an async context manager
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_factory = MagicMock(return_value=ctx)
    return mock_factory


@pytest.mark.asyncio
async def test_liveness_returns_200(client: AsyncClient):
    """GET /health always returns 200 with status ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_returns_db_check(client: AsyncClient):
    """GET /health/ready returns 200 with checks.db = ok when DB is available."""
    mock_factory = _make_mock_session()
    with patch("app.api.health.async_session", mock_factory):
        response = await client.get("/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["checks"]["db"] == "ok"
    assert data["checks"]["blob"] == "skipped"  # No AZURE_STORAGE_CONNECTION_STRING set
    assert data["status"] == "ready"


@pytest.mark.asyncio
async def test_readiness_returns_503_on_db_failure(client: AsyncClient):
    """GET /health/ready returns 503 when DB raises an exception."""
    mock_factory = _make_mock_session(
        execute_side_effect=Exception("DB connection refused")
    )
    with patch("app.api.health.async_session", mock_factory):
        response = await client.get("/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "degraded"
    assert "error" in data["checks"]["db"]


@pytest.mark.asyncio
async def test_readiness_status_field(client: AsyncClient):
    """GET /health/ready returns status=ready when all checks pass."""
    mock_factory = _make_mock_session()
    with patch("app.api.health.async_session", mock_factory):
        response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
