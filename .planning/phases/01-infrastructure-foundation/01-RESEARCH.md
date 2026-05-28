# Phase 1: Infrastructure & Foundation - Research

**Researched:** 2026-05-28
**Domain:** Docker Compose scaffold, React 19 + TanStack Router + EUROCONTROL design system, FastAPI + async SQLAlchemy + Alembic, PostgreSQL 16 RLS, Azure Blob health check, ESCO/SFIA reference data seeding
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INFRA-01 | Frontend uses React 19 + Vite + TypeScript + Tanstack Router with exact EUROCONTROL design system (Exo font, EC color palette, Shadcn/UI, Tailwind CSS with HSL custom properties) | Design system files verified at source; TanStack Router file-based routing documented; React 19 + Vite scaffolding confirmed |
| INFRA-02 | Backend uses Python FastAPI with async SQLAlchemy 2.0, Alembic migrations, Pydantic v2 schemas, and structured JSON logging | All patterns verified against working reference implementation at /home/przem/l1-service-desk-automation/backend/ |
| INFRA-03 | Application deploys via Docker Compose (Nginx + FastAPI + PostgreSQL 16) on a single Azure VM | Docker Compose pattern verified from reference project; Nginx needed (this project differs — reference uses Vite dev server) |
| INFRA-04 | Health check endpoints at GET /health (liveness) and GET /health/ready (readiness — checks DB and Blob connectivity) | Readiness pattern with DB + Blob checks is novel relative to reference; standard async probe pattern applies |
| INFRA-05 | ESCO skills taxonomy synced weekly from EC API into local reference table (no user-facing UI) | EC API base URL confirmed; pagination approach confirmed; APScheduler pattern for weekly job without Celery |
| INFRA-06 | SFIA levels 1-7 stored as reference data for rate card alignment and candidate seniority validation | Static data: 7 rows, well-defined structure; simple seed-on-startup pattern |
</phase_requirements>

---

## Summary

This phase creates the complete project skeleton. A working reference implementation exists at `/home/przem/l1-service-desk-automation/` and should be treated as the primary pattern source for backend structure, Docker Compose setup, Alembic async migrations, SQLAlchemy 2.0 models, Pydantic v2 schemas, and structured JSON logging. The reference uses React 18 + React Router DOM v7; this project upgrades to React 19 + TanStack Router — a meaningful routing difference requiring attention. The EUROCONTROL design system files (index.css, tailwind.config.ts, components.json, postcss.config.js) exist verbatim at `/home/przem/l1-service-desk-automation/frontend/` and must be copied exactly.

The biggest novel element compared to the reference is: (1) TanStack Router instead of React Router DOM — different setup requiring `@tanstack/router-vite-plugin`, `routeTree.gen.ts` generation, and `__root.tsx` file conventions; (2) Nginx for the frontend container (reference uses Vite dev server, this project uses Nginx for production-grade serving); (3) Azure Blob Storage health check in the readiness endpoint (reference checks DB + Redis); (4) APScheduler for the weekly ESCO sync job instead of Celery Beat (no Celery in this stack); (5) PostgreSQL 16 plain image (not pgvector variant, no vector columns needed at this phase).

**Primary recommendation:** Clone the reference backend structure verbatim for all patterns except ESCO sync (use APScheduler) and health check (add Azure Blob probe). For the frontend, copy the four design system files then scaffold TanStack Router from scratch using the official Vite plugin approach.

---

## Standard Stack

### Core — Frontend

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react | 19.x | UI framework | Required by INFRA-01 |
| react-dom | 19.x | DOM rendering | Required by INFRA-01 |
| @tanstack/react-router | ^1.x (latest v1) | Type-safe routing | Required by INFRA-01 |
| @tanstack/router-vite-plugin | ^1.x | File-based route tree generation | Required for file-based routing with Vite |
| vite | ^6.x | Build tool | Required by INFRA-01; matches reference |
| typescript | ^5.7 | Type safety | Required by INFRA-01; matches reference |
| tailwindcss | ^3.4 | CSS utility framework | Required by INFRA-01; Shadcn/UI requires v3 |
| autoprefixer | ^10.4 | CSS vendor prefixes | Required by postcss pipeline |
| postcss | ^8.4 | CSS transform pipeline | Required by tailwindcss |
| tailwindcss-animate | ^1.0.7 | Shadcn/UI animations | Required by components.json |

### Core — UI Components

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| class-variance-authority | ^0.7 | Shadcn variant system | Required by Shadcn/UI |
| clsx | ^2.1 | Class merging | Required by Shadcn/UI cn() |
| tailwind-merge | ^2.6 | Tailwind class deduplication | Required by Shadcn/UI cn() |
| lucide-react | ^0.469 | Icon set | Used by Shadcn/UI components |
| @radix-ui/react-slot | ^1.1 | Shadcn Button asChild | Core Shadcn/UI primitive |

### Core — Backend

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.115.x | Async web framework | Required by INFRA-02 |
| uvicorn[standard] | 0.34.x | ASGI server | Standard FastAPI runner |
| sqlalchemy[asyncio] | 2.0.x | Async ORM | Required by INFRA-02 |
| asyncpg | 0.30.x | PostgreSQL async driver | Required by SQLAlchemy asyncio |
| alembic | 1.14.x | Database migrations | Required by INFRA-02 |
| pydantic | 2.10.x | Request/response schemas | Required by INFRA-02 |
| pydantic-settings | 2.7.x | Env-based config | Standard for FastAPI settings |
| python-json-logger | 3.2.x | Structured JSON logging | Required by INFRA-02 |
| httpx | 0.28.x | Async HTTP client (ESCO sync) | Non-blocking HTTP calls |
| azure-storage-blob | ^12.x | Azure Blob SDK | Required for readiness health check (INFRA-04) |
| apscheduler | ^3.10 | Weekly ESCO sync job | Replaces Celery Beat — no Redis dependency |
| python-multipart | 0.0.20 | Form/file uploads | Standard FastAPI file handling |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @tanstack/react-query | ^5.x | Server state | Not needed in Phase 1, but add to package.json for subsequent phases |
| zustand | ^5.x | Client auth state | Not needed in Phase 1, but add now |
| react-hook-form | ^7.x | Form management | Future phases |
| zod | ^3.x | Schema validation | Future phases |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| APScheduler | Celery Beat | Celery requires Redis broker; this stack has no Redis. APScheduler runs in-process and is sufficient for a single weekly sync job |
| APScheduler | `asyncio.create_task` with sleep loop | APScheduler provides cron expressions, missed-job handling, persistence if needed |
| azure-storage-blob sync | azure-storage-blob-async | azure-storage-blob ≥12.x supports async natively via `BlobServiceClient(...).from_connection_string(...)` with `async with` |
| TanStack Router file-based | Code-based route definitions | File-based generates `routeTree.gen.ts` automatically; code-based requires manual maintenance. File-based is the recommended approach |

**Installation — Frontend:**
```bash
npm install @tanstack/react-router @tanstack/router-vite-plugin
npm install -D tailwindcss autoprefixer postcss tailwindcss-animate
npm install class-variance-authority clsx tailwind-merge lucide-react
npm install @radix-ui/react-slot
# Add for future phases (add now to avoid churn):
npm install @tanstack/react-query zustand react-hook-form zod
```

**Installation — Backend:**
```bash
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic
pip install pydantic pydantic-settings python-json-logger httpx
pip install azure-storage-blob apscheduler python-multipart
pip install PyJWT bcrypt
# Dev
pip install pytest pytest-asyncio aiosqlite ruff
```

---

## Architecture Patterns

### Recommended Project Structure

```
bryton-ai-cv-app/
├── frontend/
│   ├── src/
│   │   ├── routes/              # TanStack Router file-based routes
│   │   │   ├── __root.tsx       # Root layout (Outlet + providers)
│   │   │   ├── index.tsx        # / redirect to /dashboard
│   │   │   ├── login.tsx        # /login
│   │   │   ├── _auth.tsx        # Pathless auth layout guard
│   │   │   ├── _auth.dashboard.tsx
│   │   │   ├── _auth.demands.tsx
│   │   │   ├── _auth.candidates.tsx
│   │   │   ├── _auth.contracts.tsx
│   │   │   ├── _auth.profiles.tsx
│   │   │   ├── _auth.approvals.tsx
│   │   │   ├── _auth.sla.tsx
│   │   │   ├── _auth.admin.tsx
│   │   │   └── ... (one file per top-level route for Phase 1 placeholders)
│   │   ├── routeTree.gen.ts     # AUTO-GENERATED — do not edit
│   │   ├── components/
│   │   │   ├── ui/              # Shadcn/UI components
│   │   │   └── layout/          # Sidebar, Header, PageShell
│   │   ├── lib/
│   │   │   └── utils.ts         # cn() helper
│   │   ├── stores/              # Zustand stores
│   │   ├── types/               # TypeScript interfaces
│   │   ├── main.tsx             # Entry point
│   │   └── index.css            # EUROCONTROL design tokens (copied from reference)
│   ├── tailwind.config.ts       # Copied from reference
│   ├── components.json          # Copied from reference
│   ├── postcss.config.js        # Copied from reference
│   ├── vite.config.ts           # MODIFIED: add TanStack Router plugin
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── package.json
│   ├── index.html
│   └── Dockerfile
│
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, lifespan (seed + APScheduler)
│   │   ├── config.py            # Pydantic BaseSettings
│   │   ├── database.py          # Engine + session factory (superuser + app role)
│   │   ├── deps.py              # get_db, get_tenant_db, get_current_user
│   │   ├── api/
│   │   │   ├── health.py        # GET /health, GET /health/ready
│   │   │   └── reference.py     # GET /api/reference/sfia-levels
│   │   ├── models/
│   │   │   ├── __init__.py      # Import all models for Alembic autodiscovery
│   │   │   ├── base.py          # DeclarativeBase
│   │   │   ├── tenant.py
│   │   │   ├── user.py
│   │   │   ├── sfia_level.py    # SFIA reference data
│   │   │   └── esco_skill.py    # ESCO taxonomy reference table
│   │   ├── services/
│   │   │   └── esco_sync.py     # Weekly ESCO sync job (APScheduler)
│   │   └── utils/
│   │       └── logging.py       # Structured JSON logger
│   ├── alembic/
│   │   ├── env.py               # Async migration setup
│   │   └── versions/
│   │       └── 001_initial.py   # Tenants, users, sfia_levels, esco_skills
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
│
├── nginx/
│   └── nginx.conf               # Serve React SPA + proxy /api to backend
│
├── docker-compose.yml
└── .env.example
```

### Pattern 1: TanStack Router File-Based Setup

**What:** Vite plugin generates `routeTree.gen.ts` from files in `src/routes/`. Provides 100% type-safe navigation.
**When to use:** Always — this is the locked router choice.

```typescript
// vite.config.ts — Source: TanStack Router official docs
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { TanStackRouterVite } from '@tanstack/router-vite-plugin'
import path from 'path'

export default defineConfig({
  plugins: [
    TanStackRouterVite({ target: 'react', autoCodeSplitting: true }),
    react(),
  ],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': { target: 'http://backend:8000', changeOrigin: true },
    },
  },
})
```

```typescript
// src/main.tsx — Source: TanStack Router official docs
import { StrictMode } from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider, createRouter } from '@tanstack/react-router'
import { routeTree } from './routeTree.gen'

const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register { router: typeof router }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>
)
```

```typescript
// src/routes/__root.tsx
import { createRootRoute, Outlet } from '@tanstack/react-router'

export const Route = createRootRoute({
  component: () => <Outlet />,
})
```

```typescript
// src/routes/_auth.dashboard.tsx (placeholder pattern for Phase 1)
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_auth/dashboard')({
  component: () => (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-foreground">Dashboard</h1>
      <p className="text-sm text-muted-foreground">Coming in Phase 2.</p>
    </div>
  ),
})
```

### Pattern 2: FastAPI Lifespan with APScheduler

**What:** All startup logic (seeding + scheduler start) in a single `lifespan` context manager.
**When to use:** Any FastAPI app needing startup/shutdown hooks.

```python
# app/main.py — Source: reference project pattern + APScheduler
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.esco_sync import sync_esco_skills
from app.utils.logging import logger

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Bryton AI CV App")
    try:
        async with async_session() as session:
            await seed_sfia_levels(session)
            await session.commit()
    except Exception as e:
        logger.warning(f"Seed skipped: {e}")

    # Weekly ESCO sync — every Monday at 02:00 UTC
    scheduler.add_job(sync_esco_skills, 'cron', day_of_week='mon', hour=2)
    scheduler.start()

    yield

    scheduler.shutdown()
    logger.info("Shutting down")
```

### Pattern 3: SQLAlchemy 2.0 Async Models

**What:** Use `Mapped[T]` + `mapped_column()` with `UUID(as_uuid=True)` PKs.
**When to use:** All SQLAlchemy models.

```python
# app/models/sfia_level.py — Source: reference project models pattern
import uuid
from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class SfiaLevel(Base):
    __tablename__ = "sfia_levels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)          # 1-7
    label: Mapped[str] = mapped_column(String(50), nullable=False)                    # "Follow", "Assist", etc.
    description: Mapped[str] = mapped_column(Text, nullable=False)
```

```python
# app/models/esco_skill.py
import uuid
from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class EscoSkill(Base):
    __tablename__ = "esco_skills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uri: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    preferred_label: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    concept_type: Mapped[str] = mapped_column(String(50), nullable=False)             # "KnowledgeSkillCompetence"
    isco_group: Mapped[str | None] = mapped_column(String(20), nullable=True)
    synced_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### Pattern 4: Readiness Health Check with DB + Blob

**What:** Two-tier health: `/health` = liveness (always 200), `/health/ready` = readiness (checks DB + Blob).
**When to use:** INFRA-04 requirement.

```python
# app/api/health.py
from fastapi import APIRouter
from sqlalchemy import text
from app.database import async_session
from app.config import settings

router = APIRouter(tags=["health"])

@router.get("/health")
async def liveness():
    return {"status": "ok"}

@router.get("/health/ready")
async def readiness():
    checks = {}
    # DB check
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"

    # Azure Blob check
    try:
        from azure.storage.blob.aio import BlobServiceClient
        async with BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        ) as client:
            await client.get_service_properties()
        checks["blob"] = "ok"
    except Exception as e:
        checks["blob"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"status": "ready" if all_ok else "degraded", "checks": checks}
    )
```

### Pattern 5: Async Alembic Migration

**What:** Alembic env.py uses `create_async_engine` with `asyncio.run()` wrapper.
**When to use:** Any async SQLAlchemy project.

```python
# alembic/env.py — Source: reference project pattern
import asyncio
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings
from app.models import *  # noqa — registers all models with Base.metadata

async def run_async_migrations() -> None:
    connectable = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()
```

### Pattern 6: Structured JSON Logging

**What:** `python-json-logger` emits JSON to stdout. Docker captures stdout for centralized logging.
**When to use:** All log output from backend.

```python
# app/utils/logging.py — Source: reference project verbatim
import logging, sys
from pythonjsonlogger import json as json_logger

def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("bryton")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = json_logger.JsonFormatter(
            fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

logger = setup_logging()
```

### Pattern 7: ESCO Weekly Sync (APScheduler)

**What:** Paginated ESCO API fetch into local `esco_skills` table via upsert-on-conflict.
**When to use:** INFRA-05 weekly sync job.

```python
# app/services/esco_sync.py
import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.database import async_session
from app.models.esco_skill import EscoSkill
from app.utils.logging import logger

ESCO_API_BASE = "https://ec.europa.eu/esco/api"

async def sync_esco_skills():
    """Fetch all ESCO KnowledgeSkillCompetence entries and upsert into esco_skills."""
    logger.info("Starting ESCO weekly sync")
    offset, limit, total_synced = 0, 100, 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            resp = await client.get(
                f"{ESCO_API_BASE}/resource/skill",
                params={"language": "en", "type": "KnowledgeSkillCompetence",
                        "offset": offset, "limit": limit}
            )
            resp.raise_for_status()
            data = resp.json()
            embedded = data.get("_embedded", {}).get("results", [])
            if not embedded:
                break
            async with async_session() as db:
                for skill in embedded:
                    stmt = pg_insert(EscoSkill).values(
                        uri=skill["uri"],
                        preferred_label=skill.get("title", ""),
                        description=skill.get("description", {}).get("en", {}).get("literal"),
                        concept_type=skill.get("className", ""),
                    ).on_conflict_do_update(
                        index_elements=["uri"],
                        set_={"preferred_label": skill.get("title", ""), "synced_at": func.now()}
                    )
                    await db.execute(stmt)
                await db.commit()
            total_synced += len(embedded)
            if len(embedded) < limit:
                break
            offset += limit
    logger.info(f"ESCO sync complete: {total_synced} skills upserted")
```

### Pattern 8: SFIA Reference Data Seed

**What:** Idempotent seed function checks existence before inserting.
**When to use:** Startup seeding of immutable reference data.

```python
# app/services/seed.py
SFIA_LEVELS = [
    (1, "Follow",             "Works under close direction. Routine tasks with no significant decisions."),
    (2, "Assist",             "Works under routine direction. Some autonomy in choosing work approach."),
    (3, "Apply",              "Works under general direction. Uses discretion in approach."),
    (4, "Enable",             "Works under general guidance. Substantial responsibility for outcomes."),
    (5, "Ensure/Advise",      "Broad direction. Accountable for significant outcomes."),
    (6, "Initiate/Influence", "Has defined authority. Accountable for critical business outcomes."),
    (7, "Set Strategy/Inspire","Highest level. Sets organizational strategy and direction."),
]

async def seed_sfia_levels(db: AsyncSession) -> None:
    existing = (await db.execute(select(func.count()).select_from(SfiaLevel))).scalar()
    if existing == 7:
        return
    for level, label, description in SFIA_LEVELS:
        db.add(SfiaLevel(level=level, label=label, description=description))
```

### Pattern 9: Docker Compose with Nginx Frontend

**What:** Nginx serves the built React SPA and proxies `/api` to backend. Different from reference (which uses Vite dev server in container).
**When to use:** INFRA-03 production-grade deployment.

```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16-alpine   # No pgvector needed at this phase
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./backend/init-db:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: { context: ./backend }
    ports: ["8000:8000"]
    env_file: .env
    depends_on:
      db: { condition: service_healthy }
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  frontend:
    build: { context: ./frontend }  # Multi-stage: build React then copy to Nginx
    ports: ["80:80"]
    depends_on: [backend]

volumes:
  pgdata:
```

```nginx
# nginx/nginx.conf
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;   # SPA fallback
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```dockerfile
# frontend/Dockerfile — Multi-stage build
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

### Pattern 10: PostgreSQL Init-DB for App Role

**What:** `init-db/` SQL scripts run once on first container start. Creates non-superuser app role required for RLS enforcement.
**When to use:** Anytime using PostgreSQL RLS (RLS is bypassed by superusers).

```sql
-- backend/init-db/01_create_app_role.sql
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'bryton_app') THEN
        CREATE ROLE bryton_app WITH LOGIN PASSWORD 'bryton_dev';
    END IF;
END
$$;
GRANT CONNECT ON DATABASE bryton TO bryton_app;
GRANT USAGE ON SCHEMA public TO bryton_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO bryton_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bryton_app;
ALTER DEFAULT PRIVILEGES FOR ROLE bryton IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO bryton_app;
```

### Anti-Patterns to Avoid

- **Using TanStack Router `createBrowserRouter` (React Router pattern):** TanStack Router has its own `createRouter()` — never import from `react-router-dom`.
- **Manually editing `routeTree.gen.ts`:** This file is auto-generated by the Vite plugin. Editing it directly will be overwritten. All route definitions go in `src/routes/`.
- **Running Alembic without `PYTHONPATH=/app`:** Inside Docker, Alembic must run with `PYTHONPATH=/app` to resolve app imports. Bake this into the `docker compose exec` command.
- **Using superuser session for tenant-scoped queries:** PostgreSQL superusers bypass RLS. Use the `bryton_app` non-superuser role for all data queries where tenant isolation matters.
- **Importing `postgres:16` with pgvector for this phase:** No vector columns needed. Use `postgres:16-alpine` (lighter). Upgrade to `pgvector/pgvector:pg16` only when vector search is needed.
- **APScheduler `BackgroundScheduler` in async FastAPI:** Use `AsyncIOScheduler` (not `BackgroundScheduler`) to avoid event loop conflicts in async context.
- **Shadcn/UI + Tailwind v4 combination:** Shadcn/UI currently targets Tailwind v3. The reference project uses Tailwind 3.4.x. Do not upgrade to Tailwind v4 until Shadcn/UI officially supports it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured JSON logging | Custom formatter | `python-json-logger` | Handles log record serialization, timestamps, exception formatting edge cases |
| CSS custom properties for design tokens | Manual CSS variables | Copy `index.css` from reference | Already battle-tested with all EUROCONTROL HSL values; exact tokens required by Shadcn/UI |
| Async database engine with RLS | Custom session factory | Pattern from `database.py` in reference | Dual engine pattern (superuser + app role) is non-obvious; session commit/rollback handling is finicky |
| ESCO upsert | DELETE + INSERT on sync | `INSERT ... ON CONFLICT DO UPDATE` | Transactional upsert avoids data loss window if sync fails mid-way |
| TanStack Router type registration | Manual type casting | `declare module '@tanstack/react-router'` | Required for `<Link>`, `useNavigate` to be type-safe without explicit generics |
| Environment config | Manual `os.environ` | `pydantic-settings BaseSettings` | Handles type coercion, defaults, `.env` loading, validation in one place |
| Health check Blob probe | Stream download | `get_service_properties()` | Minimal traffic, tests auth + connectivity without downloading data |

**Key insight:** The reference project at `/home/przem/l1-service-desk-automation/` is a fully functional template. Deviating from its patterns without clear reason adds risk and time.

---

## Common Pitfalls

### Pitfall 1: TanStack Router Plugin Order in vite.config.ts
**What goes wrong:** `routeTree.gen.ts` is not generated or routes don't update.
**Why it happens:** `TanStackRouterVite` plugin must be declared BEFORE the `react()` plugin.
**How to avoid:** Always place `TanStackRouterVite(...)` first in the `plugins` array.
**Warning signs:** TypeScript errors on `routeTree.gen.ts` not found, routes return 404.

### Pitfall 2: Alembic `target_metadata` Missing Models
**What goes wrong:** `alembic revision --autogenerate` produces empty migrations.
**Why it happens:** Models must be imported before `Base.metadata` is referenced in `env.py`.
**How to avoid:** `from app.models import *` (wildcard import of the `__init__.py` that imports all models).
**Warning signs:** Empty `op.create_table()` in generated migration.

### Pitfall 3: `await db.refresh(obj)` After Flush
**What goes wrong:** `MissingGreenlet` error when Pydantic tries to serialize a model after `flush()`.
**Why it happens:** SQLAlchemy expires server-side columns (`updated_at`, `created_at`) on flush. Accessing them outside an async context raises `MissingGreenlet`.
**How to avoid:** Always `await db.refresh(obj)` before `model_validate(obj)`.
**Warning signs:** `MissingGreenlet` error on Pydantic `.model_validate()`.

### Pitfall 4: APScheduler AsyncIOScheduler Not Started
**What goes wrong:** ESCO sync never runs despite being scheduled.
**Why it happens:** `scheduler.start()` must be called explicitly in lifespan, and `scheduler.shutdown()` on teardown.
**How to avoid:** Start scheduler in lifespan context, shut down on exit. Verify with `scheduler.get_jobs()`.
**Warning signs:** No log output from `sync_esco_skills` after first Monday.

### Pitfall 5: Nginx SPA Fallback Missing
**What goes wrong:** Direct URL navigation to `/dashboard` returns 404 from Nginx.
**Why it happens:** Nginx serves static files; without `try_files $uri /index.html`, it looks for a physical file at `/dashboard`.
**How to avoid:** Always include `try_files $uri $uri/ /index.html` in the location block.
**Warning signs:** `docker compose up` works, localhost:80 works, but refreshing on any route gives 404.

### Pitfall 6: Blob SDK Sync vs Async in Health Check
**What goes wrong:** FastAPI readiness endpoint blocks event loop during Blob health probe.
**Why it happens:** Using `azure.storage.blob.BlobServiceClient` (sync) instead of `azure.storage.blob.aio.BlobServiceClient` in an async endpoint.
**How to avoid:** Import from `azure.storage.blob.aio` for async usage. Use `async with` context manager.
**Warning signs:** Slow health check response, event loop blocked warnings.

### Pitfall 7: ESCO API Pagination Termination
**What goes wrong:** Sync loop runs forever or truncates data.
**Why it happens:** ESCO API returns empty `_embedded.results` when offset exceeds total. Must check for empty results AND for `len(results) < limit` to terminate cleanly.
**How to avoid:** Break when `not embedded` OR `len(embedded) < limit`.
**Warning signs:** Sync completes with unexpectedly low skill count.

### Pitfall 8: CORS Configuration Missing WebSocket Paths
**What goes wrong:** Future WebSocket connections fail CORS pre-flight.
**Why it happens:** FastAPI `CORSMiddleware` configured only for HTTP origins; WebSocket (`ws://`) needs separate handling.
**How to avoid:** Set CORS origins correctly from day one to include frontend URL. WebSocket CORS is handled by the Origin header check in FastAPI's WebSocket dependency, not CORSMiddleware.
**Warning signs:** Browser console CORS error on WebSocket connect.

---

## Code Examples

Verified patterns from official sources and reference implementation:

### EUROCONTROL Design System File — index.css (copy verbatim)

Source: `/home/przem/l1-service-desk-automation/frontend/src/index.css` (verified)

Key CSS variables to confirm are present after copy:
- `--ec-primary: 210 100% 20%` (EUROCONTROL Primary Blue #003366)
- `--ec-secondary: 211 82% 54%` (EUROCONTROL Secondary Blue #2990EA)
- `--ec-accent: 195 100% 37%` (EUROCONTROL Accent Teal #008dbb)
- `--ec-sky: 211 82% 94%` (light blue background)
- Exo font import: `@import url('https://fonts.googleapis.com/css2?family=Exo:wght@300;400;500;600;700&display=swap')`

### EUROCONTROL Tailwind Config (copy verbatim)

Source: `/home/przem/l1-service-desk-automation/frontend/tailwind.config.ts` (verified)

Key verified color tokens: `ec.primary`, `ec.secondary`, `ec.accent`, `ec.sky`, `ec.navy`, `ec.success`, `ec.warning`, `ec.danger` — all use `hsl(var(--ec-*))` pattern.

### Shadcn/UI Installation (after copying components.json)

```bash
# components.json specifies: style=default, tailwind.config=tailwind.config.ts, css=src/index.css
# Install Shadcn components via CLI
npx shadcn@latest add button card badge input label separator
```

### Reference SFIA Endpoint

```python
# app/api/reference.py
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.sfia_level import SfiaLevel
from app.schemas.reference import SfiaLevelResponse

router = APIRouter(prefix="/api/reference", tags=["reference"])

@router.get("/sfia-levels", response_model=list[SfiaLevelResponse])
async def list_sfia_levels(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SfiaLevel).order_by(SfiaLevel.level))
    return [SfiaLevelResponse.model_validate(r) for r in result.scalars().all()]
```

### Pydantic v2 Schema Pattern

```python
# app/schemas/reference.py
from pydantic import BaseModel
import uuid

class SfiaLevelResponse(BaseModel):
    id: uuid.UUID
    level: int
    label: str
    description: str

    model_config = {"from_attributes": True}
```

---

## UI/UX Recommendations

### Design System: Copy Verbatim

**Do not recreate the EUROCONTROL design system.** Copy these files exactly from `/home/przem/l1-service-desk-automation/frontend/`:

| File | Destination | Notes |
|------|-------------|-------|
| `src/index.css` | `frontend/src/index.css` | All CSS variables + Exo font + utility classes |
| `tailwind.config.ts` | `frontend/tailwind.config.ts` | EC color tokens, Exo font-family |
| `components.json` | `frontend/components.json` | Shadcn/UI configuration |
| `postcss.config.js` | `frontend/postcss.config.js` | Tailwind + autoprefixer pipeline |

### Colors

EUROCONTROL color palette (locked — must match):

| Token | HSL | Hex | Use |
|-------|-----|-----|-----|
| `ec-primary` | 210 100% 20% | #003366 | Primary actions, sidebar background |
| `ec-secondary` | 211 82% 54% | #2990EA | Secondary actions, links, highlights |
| `ec-accent` | 195 100% 37% | #008dbb | Accent decorations, badges |
| `ec-sky` | 211 82% 94% | light blue | Card backgrounds, info panels |
| `ec-navy` | 210 100% 12% | dark navy | Deep header gradients |

Primary action buttons: `bg-gradient-to-r from-ec-primary to-ec-secondary text-white`

### Typography

**Font:** Exo (Google Fonts) — loaded in `index.css`. Set as default `font-sans` in tailwind config.

All headings use Exo with `font-weight: 600`. Body text uses Exo regular. No secondary typeface needed.

### Accessibility

Desktop-only (min 1280px). No mobile breakpoints required. Contrast ratios:
- ec-primary (#003366) on white: ~13:1 — exceeds WCAG AAA
- ec-secondary (#2990EA) on white: ~3.5:1 — meets WCAG AA for large text, acceptable for buttons with white text as per existing design system
- ec-accent (#008dbb) on white: ~3.3:1 — meets WCAG AA for large text

### Utility Classes (from index.css — do not recreate)

- `ec-card-interactive` — hover lift + border highlight (use on all clickable cards)
- `ec-badge-high` / `ec-badge-medium` / `ec-badge-low` — status badges
- `ec-accent-line` — gradient underline (secondary → accent)
- `ec-header-gradient` — dark blue sidebar gradient
- `ec-nav-active` — gradient active state for nav items

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| React Router DOM v6/v7 | TanStack Router v1 | This project spec | Type-safe routing, file-based routes, mandatory `routeTree.gen.ts` |
| React 18 | React 19 | 2024 React 19 stable release | No breaking changes for this phase; hooks work the same |
| Celery + Redis for scheduled jobs | APScheduler (in-process) | This project has no Redis | Simpler; no broker required; sufficient for single weekly job |
| `pgvector/pgvector:pg16` image | `postgres:16-alpine` | This project has no vectors in Phase 1 | Lighter image; add pgvector in matching phase |
| Vite dev server in Docker | Nginx + multi-stage build | Production deployment requirement | INFRA-03 requires Nginx |
| React Router `<Route>` tree | TanStack Router file-based `src/routes/` | This project spec | Flat files with dot notation (`_auth.dashboard.tsx`) |
| `passlib[bcrypt]` for hashing | Direct `bcrypt` | Reference project fix | passlib has incompatibilities with newer bcrypt; use `bcrypt` directly |

**Deprecated/outdated:**
- `React Router DOM` in this project: replaced by TanStack Router — do not install `react-router-dom`
- `Celery` + `Redis`: no Celery in this stack — use APScheduler for scheduled tasks
- `python-jose` for JWT: reference project uses `PyJWT` directly — use `PyJWT`

---

## Open Questions

1. **ESCO API rate limits**
   - What we know: API is free, no auth required, pagination via `offset`/`limit`
   - What's unclear: Rate limits not documented; with 13,000+ skills, sync may take multiple requests
   - Recommendation: Add `asyncio.sleep(0.1)` between pages in sync loop; use limit=100 per page; add retry logic with exponential backoff on 429

2. **Azure Blob Storage connection string format**
   - What we know: `BlobServiceClient.from_connection_string(conn_str)` is the standard pattern
   - What's unclear: Whether the VM will use connection string or managed identity; both patterns need to be supported
   - Recommendation: Config supports `AZURE_STORAGE_CONNECTION_STRING`; if empty, skip Blob health check with a warning instead of erroring

3. **ESCO API endpoint for skills — confirmed base URL**
   - What we know: `https://ec.europa.eu/esco/api/resource/skill` with `type=KnowledgeSkillCompetence`, `offset`, `limit` params
   - What's unclear: Response envelope structure may vary between ESCO versions
   - Recommendation: Implement sync with version pinned to `selectedVersion=1.1.2` (stable); wrap in try/except with detailed logging

4. **TanStack Router version compatibility with React 19**
   - What we know: TanStack Router v1.x supports React 18+; React 19 is backward compatible
   - What's unclear: Whether any peer dependency warnings exist for React 19 + TanStack Router
   - Recommendation: Use `npm install --legacy-peer-deps` if peer dep warnings appear; or check if `@tanstack/react-router` latest has explicit React 19 peer dep

---

## Sources

### Primary (HIGH confidence)
- Reference implementation at `/home/przem/l1-service-desk-automation/` — all backend patterns, Docker Compose setup, Alembic async migration, structured logging, SQLAlchemy 2.0 model patterns, init-db SQL, CORS setup
- Reference design system files at `/home/przem/l1-service-desk-automation/frontend/` — index.css, tailwind.config.ts, components.json, postcss.config.js — all read verbatim
- ARCHITECTURE.md at `/home/przem/bryton-ai-cv-app/! Background Information/ARCHITECTURE.md` — confirmed project stack and directory structure
- REQUIREMENTS.md at `/home/przem/bryton-ai-cv-app/! Background Information/REQUIREMENTS.md` — confirmed SFIA levels 1-7 definitions, ESCO background enrichment model

### Secondary (MEDIUM confidence)
- [TanStack Router file-based routing docs](https://tanstack.com/router/latest/docs/routing/file-based-routing) — file naming conventions, `__root.tsx`, `_pathlessLayout` pattern
- [ESCO API documentation](https://ec.europa.eu/esco/api/doc/esco_api_doc.html) — `/resource/skill` endpoint, pagination, no auth required
- [ESCO API web service overview](https://esco.ec.europa.eu/en/use-esco/use-esco-services-api/esco-web-service-api) — version confirmation (v1.2.1 current, v1.0.9 default)

### Tertiary (LOW confidence)
- APScheduler `AsyncIOScheduler` for FastAPI lifespan — pattern derived from library docs; verified as correct pattern for asyncio contexts but not tested against this specific stack combination

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified against reference project or official docs
- Architecture: HIGH — backend structure cloned from verified reference; frontend TanStack Router patterns from official docs
- EUROCONTROL design system: HIGH — files verified at source location on disk
- ESCO sync: MEDIUM — API endpoint confirmed, response structure inferred from docs (not tested live)
- APScheduler pattern: MEDIUM — correct pattern type, specific integration with FastAPI lifespan not tested

**Research date:** 2026-05-28
**Valid until:** 2026-07-01 (stable libraries; APScheduler + TanStack Router may release updates)
