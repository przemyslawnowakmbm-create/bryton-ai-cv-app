"""Unit tests for the ESCO sync service."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_httpx_response(data: dict, status_code: int = 200):
    """Build a mock httpx response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json = MagicMock(return_value=data)
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def _make_httpx_client(pages: list[dict]):
    """Build a mock httpx.AsyncClient that returns pages sequentially."""
    responses = [_make_httpx_response(page) for page in pages]
    call_count = 0

    async def _get(*args, **kwargs):
        nonlocal call_count
        resp = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return resp

    mock_client = AsyncMock()
    mock_client.get = _get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def _make_mock_db_session():
    """Build a mock async DB session context manager."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=None)
    mock_session.commit = AsyncMock(return_value=None)

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock_factory = MagicMock(return_value=ctx)
    return mock_factory, mock_session


SAMPLE_SKILLS = [
    {
        "uri": "http://data.europa.eu/esco/skill/001",
        "title": "Python programming",
        "className": "KnowledgeSkillCompetence",
        "description": {"en": {"literal": "Proficiency in Python language"}},
    },
    {
        "uri": "http://data.europa.eu/esco/skill/002",
        "title": "SQL databases",
        "className": "KnowledgeSkillCompetence",
        "description": {"en": {"literal": "Structured query language expertise"}},
    },
    {
        "uri": "http://data.europa.eu/esco/skill/003",
        "title": "Docker containers",
        "className": "KnowledgeSkillCompetence",
        "description": None,
    },
]


@pytest.mark.asyncio
async def test_sync_esco_skills_inserts_records():
    """Sync fetches one page of 3 skills and executes upserts for each."""
    page_data = {"_embedded": {"results": SAMPLE_SKILLS}}
    empty_page = {"_embedded": {"results": []}}

    mock_client = _make_httpx_client([page_data, empty_page])
    mock_factory, mock_session = _make_mock_db_session()

    with (
        patch("app.services.esco_sync.httpx.AsyncClient", return_value=mock_client),
        patch("app.services.esco_sync.async_session", mock_factory),
    ):
        from app.services.esco_sync import sync_esco_skills

        await sync_esco_skills()

    # 3 execute calls (one per skill) + 1 commit
    assert mock_session.execute.call_count == 3
    assert mock_session.commit.call_count == 1


@pytest.mark.asyncio
async def test_sync_esco_skills_upsert_on_conflict():
    """Sync calls execute once per skill, then commit — simulating upsert."""
    skill_v1 = [
        {
            "uri": "http://data.europa.eu/esco/skill/001",
            "title": "Python programming",
            "className": "KnowledgeSkillCompetence",
            "description": None,
        }
    ]
    skill_v2 = [
        {
            "uri": "http://data.europa.eu/esco/skill/001",
            "title": "Python programming (updated)",
            "className": "KnowledgeSkillCompetence",
            "description": None,
        }
    ]

    # First sync
    page1 = {"_embedded": {"results": skill_v1}}
    empty = {"_embedded": {"results": []}}
    mock_client_1 = _make_httpx_client([page1, empty])
    mock_factory_1, mock_session_1 = _make_mock_db_session()

    with (
        patch("app.services.esco_sync.httpx.AsyncClient", return_value=mock_client_1),
        patch("app.services.esco_sync.async_session", mock_factory_1),
    ):
        from app.services.esco_sync import sync_esco_skills

        await sync_esco_skills()

    assert mock_session_1.execute.call_count == 1

    # Second sync with updated label — same URI triggers ON CONFLICT DO UPDATE
    page2 = {"_embedded": {"results": skill_v2}}
    mock_client_2 = _make_httpx_client([page2, empty])
    mock_factory_2, mock_session_2 = _make_mock_db_session()

    with (
        patch("app.services.esco_sync.httpx.AsyncClient", return_value=mock_client_2),
        patch("app.services.esco_sync.async_session", mock_factory_2),
    ):
        await sync_esco_skills()

    # Execute called once (upsert updates existing row)
    assert mock_session_2.execute.call_count == 1
    assert mock_session_2.commit.call_count == 1


@pytest.mark.asyncio
async def test_sync_esco_skills_handles_empty_response():
    """Sync with empty API response completes without error and zero executes."""
    empty_page = {"_embedded": {"results": []}}
    mock_client = _make_httpx_client([empty_page])
    mock_factory, mock_session = _make_mock_db_session()

    with (
        patch("app.services.esco_sync.httpx.AsyncClient", return_value=mock_client),
        patch("app.services.esco_sync.async_session", mock_factory),
    ):
        from app.services.esco_sync import sync_esco_skills

        # Should not raise
        await sync_esco_skills()

    assert mock_session.execute.call_count == 0
    assert mock_session.commit.call_count == 0


@pytest.mark.asyncio
async def test_sync_esco_skills_handles_api_error(caplog):
    """Sync logs error when httpx raises but does not propagate the exception."""
    import logging

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("Network error"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    mock_factory, mock_session = _make_mock_db_session()

    with (
        patch("app.services.esco_sync.httpx.AsyncClient", return_value=mock_client),
        patch("app.services.esco_sync.async_session", mock_factory),
        caplog.at_level(logging.ERROR),
    ):
        from app.services.esco_sync import sync_esco_skills

        # Must NOT raise — sync wraps errors
        await sync_esco_skills()

    assert mock_session.execute.call_count == 0
