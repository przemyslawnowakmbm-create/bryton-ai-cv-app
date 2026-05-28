"""Test configuration for Bryton AI CV App.

Uses SQLite in-memory for speed. PostgreSQL-specific types (JSONB, UUID) are
remapped to SQLite-compatible equivalents via column-level type patching before
table creation, plus native UUID rendering disabled.

RLS tests (Plan 02) require a real PostgreSQL testcontainer — those are out of scope here.
"""
import uuid
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, String, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.types import TypeDecorator

from app.database import Base, get_db
from app.main import app


class SQLiteUUID(TypeDecorator):
    """Store UUID as VARCHAR(36) for SQLite compatibility."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return uuid.UUID(value)


def _remap_pg_types_for_sqlite():
    """Patch JSONB and UUID columns in all mapped tables to SQLite-compatible types.

    This mutates Base.metadata in-place. Called once per test session setup.
    Because all tests share the same metadata object, this is safe to call
    multiple times (the check is idempotent — already-remapped types won't match).
    """
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
            elif isinstance(column.type, PGUUID):
                column.type = SQLiteUUID()


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create an in-memory SQLite engine for each test function.

    Remaps PostgreSQL-specific column types (JSONB -> JSON, UUID -> SQLiteUUID)
    so that SQLAlchemy DDL and binding work with SQLite.
    """
    _remap_pg_types_for_sqlite()

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Enable foreign key support in SQLite
    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession backed by the in-memory SQLite engine."""
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Yield an AsyncClient with the get_db dependency overridden to use the test DB.

    Also resets the slowapi limiter storage and clears per-account login attempt tracking
    to avoid rate-limit interference between tests.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Reset slowapi in-memory storage to avoid rate-limit interference between tests.
    # Both app.state.limiter (main.py) and _limiter (auth.py) have separate storages;
    # both must be reset to avoid cross-test rate limit bleed.
    if hasattr(app.state, "limiter") and hasattr(app.state.limiter, "_storage"):
        try:
            app.state.limiter._storage.reset()
        except Exception:
            pass  # storage reset not supported
    try:
        from app.api.auth import _limiter as _auth_limiter
        if hasattr(_auth_limiter, "_storage"):
            _auth_limiter._storage.reset()
    except Exception:
        pass

    # Clear per-account login attempt tracking
    try:
        from app.api.auth import _login_attempts
        _login_attempts.clear()
    except ImportError:
        pass

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
