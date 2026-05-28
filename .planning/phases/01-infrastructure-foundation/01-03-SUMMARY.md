---
phase: 01-infrastructure-foundation
plan: 03
subsystem: infra
tags: [docker, docker-compose, nginx, postgres, apscheduler, esco, fastapi, python]

requires:
  - phase: 01-infrastructure-foundation
    plan: 01
    provides: FastAPI backend with health endpoints, SQLAlchemy models, Alembic migrations
  - phase: 01-infrastructure-foundation
    plan: 02
    provides: React frontend build (Vite/TanStack Router) that produces dist/

provides:
  - docker-compose.yml orchestrating 3 services (db, backend, frontend)
  - backend/Dockerfile building FastAPI/uvicorn container with PYTHONPATH=/app
  - frontend/Dockerfile multi-stage build (node:20-alpine builder + nginx:alpine)
  - frontend/nginx/nginx.conf with SPA fallback and /api/ + /health proxying
  - backend/app/services/esco_sync.py weekly ESCO taxonomy upsert with APScheduler
  - APScheduler AsyncIOScheduler registered in lifespan (Monday 02:00 UTC)
  - scripts/smoke-test.sh for full-stack integration validation
  - .env.example with all required environment variables

affects:
  - all future phases (deployment infrastructure established)
  - backend phases needing ESCO data sync
  - frontend phases serving through Nginx

tech-stack:
  added:
    - APScheduler 3.x (AsyncIOScheduler for in-process cron jobs)
    - Nginx (alpine, multi-stage frontend container)
    - PostgreSQL 16 Alpine (Docker service)
    - httpx (async HTTP client for ESCO API)
  patterns:
    - Docker Compose 3-service stack with health-check-gated depends_on
    - Multi-stage Docker build: node builder -> nginx:alpine
    - APScheduler AsyncIOScheduler in FastAPI lifespan context manager
    - ESCO upsert using pg_insert ON CONFLICT DO UPDATE on uri column
    - Nginx SPA fallback with try_files + separate /health proxy block

key-files:
  created:
    - docker-compose.yml
    - backend/Dockerfile
    - frontend/Dockerfile
    - frontend/nginx/nginx.conf
    - backend/app/services/esco_sync.py
    - scripts/smoke-test.sh
    - .env.example
    - .gitignore
    - .dockerignore
  modified:
    - backend/app/main.py (added AsyncIOScheduler + ESCO sync job registration)

key-decisions:
  - "APScheduler AsyncIOScheduler (not BackgroundScheduler) for ESCO weekly sync to avoid event loop conflicts"
  - "Nginx /health block proxied separately (not under /api/) because health routes have no /api prefix"
  - "Backend command: alembic upgrade head then uvicorn — migrations run on startup before server starts"
  - "Frontend uses --legacy-peer-deps for npm install in Docker due to React 19 peer dep warnings"
  - "ESCO sync wrapped in try/except to never crash the app on sync failure"

patterns-established:
  - "Docker Compose health-check-gated depends_on: db waits for pg_isready before backend starts"
  - "Multi-stage frontend Dockerfile: builder stage compiles React, nginx stage serves static files"
  - "APScheduler job registered in lifespan: scheduler.add_job -> scheduler.start() before yield, scheduler.shutdown() after"
  - "ESCO paginated sync: break on empty results OR len(embedded) < limit, asyncio.sleep(0.1) between pages"

requirements-completed: [INFRA-03, INFRA-05]

duration: 25min
completed: 2026-05-28
---

# Phase 01 Plan 03: Docker Compose Deployment Stack Summary

**3-service Docker Compose stack (Postgres 16 + FastAPI + Nginx) with weekly APScheduler ESCO sync and Nginx SPA proxy routing**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-05-28T00:00:00Z
- **Completed:** 2026-05-28T00:25:00Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Complete Docker Compose stack: db (postgres:16-alpine with pg_isready health check), backend (FastAPI + Alembic migration on startup), frontend (nginx:alpine serving built React SPA)
- Nginx config with SPA try_files fallback + separate /api/ and /health proxy blocks (critical: /health must not go through /api/ prefix)
- APScheduler AsyncIOScheduler registered in main.py lifespan, ESCO sync job scheduled Monday 02:00 UTC without Celery or Redis dependency
- ESCO sync service using httpx.AsyncClient with pg_insert ON CONFLICT DO UPDATE upsert pattern
- 4 ESCO sync unit tests passing (insert, upsert, empty response, API error handling)
- Integration smoke test script validating liveness, readiness, SFIA API, frontend serving, and SPA fallback

## Task Commits

1. **Task 1: Docker Compose stack, Dockerfiles, Nginx, and ESCO sync service** - `7f9e5d9` (feat)
2. **Task 2: ESCO sync unit test and integration smoke test script** - `150a6c7` (test)

## Files Created/Modified

- `docker-compose.yml` - 3-service stack: db, backend, frontend with healthcheck-gated depends_on
- `backend/Dockerfile` - python:3.12-slim with PYTHONPATH=/app, uvicorn entrypoint
- `frontend/Dockerfile` - Multi-stage: node:20-alpine builder -> nginx:alpine server
- `frontend/nginx/nginx.conf` - SPA fallback, /api/ proxy, /health proxy (separate block)
- `backend/app/services/esco_sync.py` - Weekly ESCO API sync with pagination and upsert
- `backend/app/main.py` - Updated with AsyncIOScheduler and ESCO sync job registration
- `scripts/smoke-test.sh` - 5-check integration smoke test (executable)
- `.env.example` - Template with POSTGRES_USER, DATABASE_URL, APP_DATABASE_URL, CORS_ORIGINS
- `.gitignore` - Python/Node/Docker/IDE excludes
- `.dockerignore` - Excludes node_modules, .git, __pycache__, .env, .venv, dist, *.md

## Decisions Made

- Used APScheduler AsyncIOScheduler (not BackgroundScheduler) — avoids threading/event loop conflicts in async FastAPI context
- Nginx /health location is a separate block from /api/ because backend health routes have no /api prefix (per Plan 01-01 architecture)
- Backend Docker command runs `alembic upgrade head` before uvicorn starts — ensures migrations run on every container restart
- ESCO sync uses try/except at the top level — sync failure logs an error but never crashes the application

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed .dockerignore from .gitignore**
- **Found during:** Task 1 commit staging
- **Issue:** The generated .gitignore had a `# Docker / .dockerignore` entry, which caused `git add .dockerignore` to fail (file was git-ignored)
- **Fix:** Removed `.dockerignore` entry from .gitignore — .dockerignore should be committed, not ignored
- **Files modified:** .gitignore
- **Verification:** `git add .dockerignore` succeeded after fix
- **Committed in:** 7f9e5d9 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Minor fix to .gitignore. No scope creep.

## Issues Encountered

**Pre-existing test failures (out of scope):** 12 tests in test_health.py, test_reference.py, and test_seed.py fail with `UnsupportedCompilationError: can't render element of type JSONB`. Root cause: Tenant model (created in Plan 01-01) uses PostgreSQL-specific JSONB type; conftest.py creates SQLite in-memory DB which doesn't support JSONB. Deferred to future plan. Logged in `deferred-items.md`. ESCO sync tests (4/4) are unaffected and pass.

## User Setup Required

None — `.env` is created from `.env.example` with default local dev values. Run `docker compose up` to start all services.

## Next Phase Readiness

- Full deployment stack ready: `docker compose up` starts all services
- Alembic runs migrations on backend startup
- SFIA levels seeded from lifespan startup
- ESCO weekly sync scheduled (Monday 02:00 UTC)
- Nginx serves React SPA at localhost:80 with /api/ and /health proxied to backend
- Smoke test at `scripts/smoke-test.sh` validates full stack

---
*Phase: 01-infrastructure-foundation*
*Completed: 2026-05-28*
