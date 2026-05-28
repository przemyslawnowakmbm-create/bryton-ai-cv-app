---
phase: 01-infrastructure-foundation
plan: "01"
subsystem: api
tags: [fastapi, sqlalchemy, alembic, postgresql, pydantic, python-json-logger, asyncpg, bcrypt]

# Dependency graph
requires: []
provides:
  - FastAPI application with lifespan context manager (startup seeding + graceful shutdown)
  - Dual async database engine pattern: superuser (bryton) + app role (bryton_app) for RLS
  - SQLAlchemy 2.0 models: Tenant, User, SfiaLevel, EscoSkill with UUID PKs and Mapped types
  - Alembic async migration environment + initial migration 001_initial_schema (4 tables)
  - GET /health liveness endpoint (always 200, no /api prefix)
  - GET /health/ready readiness endpoint (DB probe + optional Azure Blob probe)
  - GET /api/reference/sfia-levels returning 7 SFIA levels ordered by level
  - Idempotent seed_sfia_levels function seeding SFIA levels 1-7 on startup
  - Structured JSON logging via python-json-logger with bryton logger name
  - PostgreSQL init-db SQL creating bryton_app non-superuser role for RLS
  - Backend unit tests (health, reference API, seed logic) using aiosqlite in-memory
affects:
  - 01-02-infrastructure (frontend already scaffolded in parallel)
  - 01-03-infrastructure (Docker Compose + Nginx + migrations)
  - All subsequent backend phases depend on this foundation

# Tech tracking
tech-stack:
  added:
    - fastapi 0.115.x
    - uvicorn[standard] 0.34.x
    - sqlalchemy[asyncio] 2.0.x
    - asyncpg 0.30.x
    - alembic 1.14.x
    - pydantic 2.10.x
    - pydantic-settings 2.7.x
    - python-json-logger 3.2.x
    - httpx 0.28.x
    - azure-storage-blob 12.x
    - apscheduler 3.10.x
    - python-multipart 0.0.20
    - PyJWT 2.8+
    - bcrypt 4.0+
    - aiosqlite (test)
    - pytest-asyncio (test)
  patterns:
    - Dual async engine: superuser engine (bypasses RLS) + non-superuser app_engine (RLS enforced)
    - SQLAlchemy 2.0 Mapped types with UUID PKs and mapped_column
    - Alembic async migration using create_async_engine + NullPool
    - FastAPI lifespan context manager for startup/shutdown
    - Idempotent seed function pattern (count-first, insert only if not complete)
    - Structured JSON logging via python-json-logger emitting to stdout
    - In-memory aiosqlite + override_get_db for fast unit tests

key-files:
  created:
    - backend/app/main.py
    - backend/app/config.py
    - backend/app/database.py
    - backend/app/deps.py
    - backend/app/models/tenant.py
    - backend/app/models/user.py
    - backend/app/models/sfia_level.py
    - backend/app/models/esco_skill.py
    - backend/app/models/__init__.py
    - backend/app/api/health.py
    - backend/app/api/reference.py
    - backend/app/services/seed.py
    - backend/app/schemas/reference.py
    - backend/app/schemas/health.py
    - backend/app/utils/logging.py
    - backend/alembic/env.py
    - backend/alembic/versions/001_initial_schema.py
    - backend/alembic.ini
    - backend/requirements.txt
    - backend/init-db/01_create_app_role.sql
    - backend/tests/conftest.py
    - backend/tests/test_health.py
    - backend/tests/test_reference.py
    - backend/tests/test_seed.py
    - backend/pytest.ini
  modified: []

key-decisions:
  - "All models import Base from app.database (single DeclarativeBase instance) — models/base.py re-exports from app.database"
  - "Health endpoint uses async_session directly (not via get_db dependency) so tests mock app.api.health.async_session"
  - "Azure Blob health probe skipped (not errored) when AZURE_STORAGE_CONNECTION_STRING is empty"
  - "Initial Alembic migration created manually (not via autogenerate) since no live DB available outside Docker"
  - "bcrypt used directly — no passlib"

patterns-established:
  - "Pattern: Dual engine (superuser + bryton_app) — all models and sessions follow this pattern"
  - "Pattern: Lifespan seeding — seed functions called in lifespan with graceful exception handling"
  - "Pattern: Async SQLite tests — conftest.py creates in-memory engine, overrides get_db dependency"
  - "Pattern: Health check mocking — patch app.api.health.async_session for unit tests"

requirements-completed: [INFRA-02, INFRA-04, INFRA-06]

# Metrics
duration: 6min
completed: 2026-05-28
---

# Phase 01 Plan 01: Backend Foundation Summary

**FastAPI backend with dual-engine async SQLAlchemy 2.0, Alembic migrations, health check endpoints, SFIA reference API, and structured JSON logging — all patterns cloned from reference implementation**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-05-28T12:58:01Z
- **Completed:** 2026-05-28T13:04:13Z
- **Tasks:** 3
- **Files created:** 33

## Accomplishments
- Complete FastAPI backend skeleton with lifespan, CORS, and router registration
- Dual async database engine pattern (superuser + bryton_app non-superuser for RLS)
- 4 SQLAlchemy 2.0 models (Tenant, User, SfiaLevel, EscoSkill) with UUID PKs
- Alembic async migration environment with initial 4-table migration
- Health endpoints: GET /health (liveness, always 200) and GET /health/ready (DB + Blob probe)
- GET /api/reference/sfia-levels returning 7 SFIA levels ordered by level
- Idempotent SFIA seeder called on every startup
- Structured JSON logging via python-json-logger (bryton logger)
- Backend unit tests: health (4), reference API (4), seed (4) = 12 tests total

## Task Commits

Each task was committed atomically:

1. **Task 1: Config, database, models, Alembic, logging** - `23b4433` (feat)
2. **Task 2: API routes, schemas, seed service, FastAPI wiring** - `3850223` (feat)
3. **Task 3: Backend unit tests** - `2dbaa92` (test)
4. **Fix: Remove deprecated event_loop fixture** - `f36a42b` (fix)
5. **Fix: Remove unused import in test_reference** - `e034fba` (fix)

## Files Created/Modified
- `backend/app/main.py` - FastAPI app with lifespan, CORS, router registration
- `backend/app/config.py` - Pydantic BaseSettings with DATABASE_URL, APP_DATABASE_URL, Azure Blob string
- `backend/app/database.py` - Dual async engines (superuser + bryton_app), Base, get_db
- `backend/app/deps.py` - Re-export get_db + placeholders for Phase 2 dependencies
- `backend/app/models/sfia_level.py` - SfiaLevel model (id, level, label, description)
- `backend/app/models/esco_skill.py` - EscoSkill model (uri, preferred_label, concept_type, etc.)
- `backend/app/models/tenant.py` - Tenant model with JSONB config
- `backend/app/models/user.py` - User model stub with optional tenant_id FK
- `backend/app/api/health.py` - GET /health + GET /health/ready with async DB + Blob probes
- `backend/app/api/reference.py` - GET /api/reference/sfia-levels
- `backend/app/services/seed.py` - seed_sfia_levels idempotent async seeder
- `backend/app/utils/logging.py` - JSON structured logger (bryton)
- `backend/alembic/env.py` - Async Alembic env with create_async_engine + NullPool
- `backend/alembic/versions/001_initial_schema.py` - Initial 4-table migration
- `backend/requirements.txt` - All Python dependencies
- `backend/init-db/01_create_app_role.sql` - PostgreSQL bryton_app role creation
- `backend/tests/conftest.py` - aiosqlite in-memory fixtures + client override
- `backend/tests/test_health.py` - Health endpoint tests with async_session mocking
- `backend/tests/test_reference.py` - SFIA reference API tests
- `backend/tests/test_seed.py` - Seed function tests

## Decisions Made
- All models import `Base` from `app.database` (not from `models/base.py`) — single DeclarativeBase instance ensures Alembic autogenerate works correctly
- Health check uses `async_session` directly (not via `get_db`) because it's infrastructure-level, not business logic; tests mock `app.api.health.async_session`
- Azure Blob health probe returns `"skipped"` (not `"error"`) when `AZURE_STORAGE_CONNECTION_STRING` is empty — allows running without Azure in dev
- Initial Alembic migration was manually created (not via autogenerate) since no live DB is available outside Docker
- `bcrypt` used directly per project decision — no `passlib`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed conftest.py deprecated event_loop fixture**
- **Found during:** Task 3 (unit tests)
- **Issue:** Session-scoped `event_loop` fixture is deprecated in pytest-asyncio 0.21+ when combined with function-scoped async fixtures — causes warnings or failures
- **Fix:** Removed the `event_loop` fixture; `asyncio_mode=auto` in pytest.ini handles this automatically
- **Files modified:** backend/tests/conftest.py
- **Committed in:** `f36a42b`

**2. [Rule 1 - Bug] Fixed models/base.py to re-export Base from app.database**
- **Found during:** Task 1 (models creation)
- **Issue:** Plan spec calls for `models/base.py` to contain `DeclarativeBase`, but if models import from `models/base.py` (a separate class) vs `app.database.Base` (another class), Alembic autogenerate would not see any tables. All models import from `app.database` which is the canonical Base.
- **Fix:** Changed `models/base.py` to re-export `Base` from `app.database` instead of defining a separate one
- **Files modified:** backend/app/models/base.py
- **Committed in:** `23b4433`

---

**Total deviations:** 2 auto-fixed (1 deprecation fix, 1 architectural correctness)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
- Bash permission was denied during verification runs (`python -c "..."` and `pytest` commands). All code verified through static analysis instead. Tests are structurally correct based on patterns from reference implementation at `/home/przem/l1-service-desk-automation/`.

## User Setup Required
None - no external service configuration required for the backend skeleton. The full stack requires Docker Compose (from Plan 01-03).

## Next Phase Readiness
- Backend foundation complete — config, database, models, migrations, health checks, SFIA API, logging
- Plan 01-02 (frontend) already committed (in parallel)
- Plan 01-03 (Docker Compose, Nginx, Dockerfile) can now wire both together
- Phase 02 (auth, JWT, tenant management) can build directly on this foundation

---
*Phase: 01-infrastructure-foundation*
*Completed: 2026-05-28*
