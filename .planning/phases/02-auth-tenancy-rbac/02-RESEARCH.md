# Phase 2: Auth, Tenancy & RBAC - Research

**Researched:** 2026-05-28
**Domain:** FastAPI JWT auth, PostgreSQL RLS, RBAC enforcement, TanStack Router auth guards, approval chains
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-01 | Email/password registration with verification email before access granted | bcrypt already in requirements.txt; PyJWT already installed; email sending needs new dependency (fastapi-mail or smtp via aiosmtplib) |
| AUTH-02 | JWT access token (15-min) + refresh token (7-day httpOnly cookie) | PyJWT confirmed in requirements.txt; config already has JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60 (must change to 15); httpOnly cookie via Response.set_cookie |
| AUTH-03 | Logout invalidating refresh token | Refresh token must be stored in DB for invalidation; blacklist pattern OR token_id in DB |
| AUTH-04 | Password reset via email with time-limited token | Separate secure token (not JWT) stored in DB with expiry; same email infra as AUTH-01 |
| AUTH-05 | Rate limiting login attempts per IP and per account | slowapi library; per-IP via get_remote_address; per-account via custom key_func on email param |
| AUTH-06 | Admin CRUD for users of any role across all tenants | Superuser engine (bypasses RLS); role check dependency returning 403; standard CRUD endpoints |
| AUTH-07 | SM manages Customer users within their assigned tenant(s) | App engine (RLS-enforced); SM can only see their tenant; junction table for multi-tenant SM |
| AUTH-08 | Candidate self-registration with GDPR consent | Public endpoint (no auth); separate registration form; GDPR consent flag stored on user |
| TENANT-01 | Create tenant with unique 2-6 char prefix | Tenant model already exists with prefix field; validation in Pydantic schema |
| TENANT-02 | PostgreSQL RLS via SET app.current_tenant per session | App role (bryton_app) already created in init-db; get_tenant_db dependency to build; RLS policies via Alembic migration |
| TENANT-03 | SM/Recruiter multi-tenant assignment via junction table | New user_tenant_assignments table needed; not in Phase 1 schema |
| TENANT-04 | Customer sees only own tenant data | RLS policy + role check; Customer's tenant_id is their single tenant |
| TENANT-05 | Admin can deactivate tenant making data read-only | is_active flag already on Tenant model; read-only enforcement via RLS policy or middleware check |
| RBAC-01 | 5 roles with per-endpoint 403 enforcement | User.role already a string field; role enum + require_roles() dependency pattern |
| RBAC-02 | Demand lifecycle transitions restricted by role | Demand model not yet built — transitions table belongs in a later phase; Phase 2 establishes the role enforcement pattern |
| RBAC-03 | Configurable approval gates per tenant (stored in tenant.config JSONB) | tenant.config JSONB already exists; approval config structure to be defined |
| RBAC-04 | Approval requests with justification, approve/reject/request-changes | New approval_requests table needed |
| RBAC-05 | Approval decisions logged in audit trail | New audit_log table needed |
</phase_requirements>

---

## Summary

Phase 1 built the exact foundation Phase 2 requires: a dual-engine database pattern (superuser `engine` + RLS-enforced `app_engine`), `bryton_app` non-superuser role, Tenant and User models with all the right fields, PyJWT and bcrypt installed, and TanStack Router with a `_auth.tsx` layout route scaffold. The `deps.py` even contains explicit `TODO (Phase 02)` comments pointing to `get_tenant_db` and `get_current_user`.

The core technical work in Phase 2 is: (1) writing the `get_tenant_db` dependency that opens an `app_async_session`, runs `SET LOCAL app.current_tenant = :id`, and yields it; (2) writing RLS policies in an Alembic migration that use that GUC; (3) implementing JWT auth endpoints (register, login, refresh, logout, password-reset); (4) wiring `slowapi` rate limiting on login; (5) building role enforcement via a `require_roles()` FastAPI dependency; (6) creating the `user_tenant_assignments` junction table for multi-tenant SM/Recruiter; (7) building the approval_requests + audit_log tables with their CRUD logic; and (8) wiring up the React auth state using Zustand + TanStack Router `beforeLoad` guards.

The most subtle correctness requirement is the RLS `SET LOCAL` scope. `SET LOCAL` is scoped to the current transaction — which is correct when each request is one transaction, but requires confirming the SQLAlchemy session is in autocommit=False mode (the default). Using `SET` (without LOCAL) would leak tenant context across pooled connections, which is a critical data isolation bug.

**Primary recommendation:** Use `SET LOCAL app.current_tenant = :tenant_id` inside `get_tenant_db` after beginning a transaction, never `SET` without LOCAL. Use the superuser `get_db` only for login/register/refresh/admin-cross-tenant endpoints. Use `app_async_session` + tenant context for all other authenticated endpoints.

---

## What Phase 1 Built (Codebase State)

### Already Done — No Rebuild Needed

| Item | Location | Phase 2 Use |
|------|----------|-------------|
| `Tenant` model with `id`, `prefix`, `name`, `config` (JSONB), `is_active` | `app/models/tenant.py` | Extend with RLS policies; add TENANT-01/05 endpoints |
| `User` model with `id`, `email`, `hashed_password`, `role`, `tenant_id`, `is_active` | `app/models/user.py` | Extend: add `email_verified`, `gdpr_consent`; tighten role to enum |
| Dual engine: `engine` (superuser) + `app_engine` (bryton_app, RLS) | `app/database.py` | `get_tenant_db` uses `app_async_session`; login uses `async_session` |
| `get_db` superuser dependency | `app/deps.py` | Keep for admin/pre-auth; add `get_tenant_db` and `get_current_user` |
| `bryton_app` DB role with non-superuser login | `backend/init-db/01_create_app_role.sql` | Role is there; RLS policies need to be written |
| `SECRET_KEY`, `JWT_ALGORITHM`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_MINUTES` in config | `app/config.py` | Note: `JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60` must be corrected to `15` |
| PyJWT and bcrypt in requirements.txt | `requirements.txt` | Use directly; no passlib |
| TanStack Router `_auth.tsx` layout route (sidebar nav, Outlet) | `frontend/src/routes/_auth.tsx` | Add `beforeLoad` guard; replace "Phase 1 Scaffold" footer |
| Login page scaffold | `frontend/src/routes/login.tsx` | Replace placeholder with real form |
| Zustand, react-hook-form, Zod already installed | `frontend/package.json` | Auth store (Zustand), form validation (react-hook-form + Zod) |
| TanStack Query already installed | `frontend/package.json` | API request management, cache invalidation |

### NOT Yet Built — Phase 2 Must Build

| Item | Notes |
|------|-------|
| RLS policies (CREATE POLICY) on `users`, future tenant-scoped tables | Alembic migration; must use bryton_app role |
| `user_tenant_assignments` junction table | Multi-tenant SM/Recruiter (TENANT-03) |
| `refresh_tokens` table | For invalidation on logout (AUTH-03) |
| `email_verification_tokens` table | For AUTH-01 / AUTH-04 |
| `approval_requests` table | RBAC-04 |
| `audit_log` table | RBAC-05 |
| `get_tenant_db` dependency | SET LOCAL + yield app_async_session |
| `get_current_user` dependency | Decode JWT bearer token |
| `require_roles(*roles)` dependency | 403 enforcement |
| Auth router: `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/verify-email`, `/auth/forgot-password`, `/auth/reset-password` | Full auth flow |
| Tenant router: `/tenants` CRUD (admin), `/tenants/{id}/deactivate` | TENANT-01/05 |
| User management router: `/users` (admin), `/tenants/{id}/users` (SM) | AUTH-06/07 |
| Approval router: `/approvals` CRUD | RBAC-04 |
| Email sending integration | aiosmtplib or SMTP settings |
| React auth store (Zustand) | Token storage, user state |
| React `beforeLoad` guards on `_auth.tsx` | Redirect to login |
| Login/register/verify/reset frontend pages | Full auth UI flow |
| Candidate self-registration page | Public; AUTH-08 |

---

## Standard Stack

### Backend — New in Phase 2

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| PyJWT | >=2.8 (installed) | JWT encode/decode | Already in requirements.txt; confirmed decision |
| bcrypt | >=4.0 (installed) | Password hashing | Already in requirements.txt; NOT passlib |
| slowapi | latest (0.1.x) | Rate limiting per IP and per account | Starlette/FastAPI native; decorator-based; zero config for per-IP |
| aiosmtplib | >=3.0 | Async SMTP email sending | Pure-async; no threading; works with FastAPI lifespan |
| python-multipart | 0.0.20 (installed) | Form data parsing | Already installed; needed for login form |

### Frontend — No New Packages Needed

All required packages are already installed in `package.json`:
- `zustand` ^5.0.0 — auth state store
- `react-hook-form` ^7.0.0 — form management
- `zod` ^3.0.0 — schema validation for forms
- `@tanstack/react-query` ^5.0.0 — server state / API calls
- `@tanstack/react-router` ^1.0.0 — route guards via `beforeLoad`

**Installation (backend only):**
```bash
pip install slowapi aiosmtplib
```

Add to `requirements.txt`:
```
slowapi>=0.1
aiosmtplib>=3.0
```

### Config additions to `app/config.py`

```python
# Email
SMTP_HOST: str = "smtp.example.com"
SMTP_PORT: int = 587
SMTP_USER: str = ""
SMTP_PASSWORD: str = ""
SMTP_FROM: str = "noreply@brytonai.com"
FRONTEND_URL: str = "http://localhost:3000"

# JWT — fix the access token expiry
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15   # was 60 in Phase 1
```

---

## Architecture Patterns

### Backend Structure (new files in `app/`)

```
app/
├── api/
│   ├── auth.py          # /auth/* endpoints
│   ├── tenants.py       # /tenants/* endpoints
│   ├── users.py         # /users/* (admin), /tenants/{id}/users (SM)
│   └── approvals.py     # /approvals/* endpoints
├── models/
│   ├── user.py          # EXTEND: add email_verified, gdpr_consent fields
│   ├── refresh_token.py # New: refresh token store
│   ├── email_token.py   # New: email verification + password reset tokens
│   ├── user_tenant.py   # New: user_tenant_assignments junction
│   ├── approval.py      # New: approval_requests
│   └── audit_log.py     # New: audit trail
├── schemas/
│   ├── auth.py          # RegisterRequest, LoginRequest, TokenResponse, etc.
│   ├── tenant.py        # TenantCreate, TenantResponse, etc.
│   ├── user.py          # UserCreate, UserResponse, UserUpdate
│   └── approval.py      # ApprovalCreate, ApprovalResponse, etc.
├── services/
│   ├── auth.py          # Password hash/verify, token creation, email send
│   └── approval.py      # Approval workflow logic
├── deps.py              # Add get_tenant_db, get_current_user, require_roles
└── utils/
    └── email.py         # aiosmtplib send helper
```

### Pattern 1: Dual DB Dependency (RLS enforcement)

The existing `get_db` uses the superuser engine and bypasses RLS. For tenant-scoped endpoints, add `get_tenant_db`:

```python
# app/deps.py
from contextlib import asynccontextmanager
from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import app_async_session

async def get_tenant_db(
    current_user: User = Depends(get_current_user),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a session that has RLS enforced via SET LOCAL app.current_tenant.
    Uses app_async_session (bryton_app role — NOT superuser).
    SET LOCAL scopes the GUC to the current transaction only, preventing
    tenant context leaking across pooled connections.
    """
    tenant_id = current_user.tenant_id
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant context")

    async with app_async_session() as session:
        try:
            # SET LOCAL — scoped to this transaction only
            await session.execute(
                text("SET LOCAL app.current_tenant = :tid"),
                {"tid": str(tenant_id)},
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**CRITICAL:** `SET LOCAL` — not `SET`. Without `LOCAL`, the GUC persists for the lifetime of the connection, leaking tenant context to the next request on that pooled connection.

### Pattern 2: PostgreSQL RLS Policies (via Alembic migration)

RLS policies run SQL that cannot be expressed in SQLAlchemy model syntax. Write them directly in an Alembic migration:

```python
# alembic/versions/002_rls_and_auth_tables.py

def upgrade() -> None:
    # Enable RLS on tenant-scoped tables
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")

    # Policy: users can only see rows matching current_setting('app.current_tenant')
    # current_user = 'bryton' (superuser) bypasses this automatically
    op.execute("""
        CREATE POLICY tenant_isolation ON users
            USING (
                tenant_id = current_setting('app.current_tenant', true)::uuid
                OR current_setting('app.current_tenant', true) IS NULL
                OR current_setting('app.current_tenant', true) = ''
            )
    """)

    # Admin users (role='admin') see all rows — handled by using superuser engine
    # not by RLS policy, to keep policies simple
```

**Note:** `current_setting('app.current_tenant', true)` — the `true` second argument means "return NULL if missing" rather than raising an error.

### Pattern 3: JWT Auth with PyJWT

```python
# app/services/auth.py
import jwt
from datetime import datetime, timedelta, timezone
from app.config import settings

def create_access_token(user_id: str, role: str, tenant_id: str | None) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "tenant_id": str(tenant_id) if tenant_id else None,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token(user_id: str, token_id: str) -> str:
    payload = {
        "sub": user_id,
        "jti": token_id,   # stored in DB for invalidation
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
```

**httpOnly cookie for refresh token:**
```python
# In the login endpoint response
response.set_cookie(
    key="refresh_token",
    value=refresh_token_str,
    httponly=True,
    secure=True,          # requires HTTPS in production
    samesite="lax",
    max_age=60 * 60 * 24 * 7,  # 7 days in seconds
    path="/auth/refresh",      # scoped to refresh endpoint only
)
```

### Pattern 4: get_current_user Dependency

```python
# app/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),  # superuser — reads users table
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user = await db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user
```

### Pattern 5: Role Enforcement Dependency

```python
# app/deps.py
from enum import StrEnum
from typing import Callable

class Role(StrEnum):
    ADMIN = "admin"
    SM = "sm"
    RECRUITER = "recruiter"
    CUSTOMER = "customer"
    CANDIDATE = "candidate"

def require_roles(*roles: Role) -> Callable:
    """Factory returning a FastAPI dependency that enforces role membership."""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {[r.value for r in roles]}"
            )
        return current_user
    return _check

# Usage on an endpoint:
@router.post("/tenants")
async def create_tenant(
    body: TenantCreate,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),  # admin bypasses RLS via superuser engine
):
    ...
```

### Pattern 6: slowapi Rate Limiting

```python
# app/main.py — add to app setup
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# app/api/auth.py — on login endpoint
from slowapi import Limiter
from slowapi.util import get_remote_address

# Per-IP limit
@router.post("/auth/login")
@limiter.limit("10/minute")        # per IP
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    ...
```

For per-account rate limiting, use a custom key function that extracts email from the request body. Note that slowapi's `key_func` receives the Request object; for body-based keying you must parse the body manually or use a middleware approach.

### Pattern 7: TanStack Router Auth Guards (Frontend)

The `_auth.tsx` layout route already exists. Add `beforeLoad` to redirect unauthenticated users:

```typescript
// frontend/src/routes/_auth.tsx
import { createFileRoute, redirect, Outlet } from '@tanstack/react-router'
import { useAuthStore } from '../stores/auth'

export const Route = createFileRoute('/_auth')({
  beforeLoad: ({ context }) => {
    // Read auth state from router context (populated in __root.tsx)
    if (!context.auth.isAuthenticated) {
      throw redirect({ to: '/login', search: { redirect: location.href } })
    }
  },
  component: AuthLayout,
})
```

**Router context setup in `__root.tsx`:**
```typescript
// frontend/src/routes/__root.tsx
import { createRootRouteWithContext, Outlet } from '@tanstack/react-router'

interface RouterContext {
  auth: { isAuthenticated: boolean; user: User | null }
}

export const Route = createRootRouteWithContext<RouterContext>()({
  component: () => <Outlet />,
})
```

**Zustand auth store:**
```typescript
// frontend/src/stores/auth.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: string
  email: string
  role: 'admin' | 'sm' | 'recruiter' | 'customer' | 'candidate'
  tenant_id: string | null
  display_name: string | null
}

interface AuthState {
  user: User | null
  accessToken: string | null
  setAuth: (user: User, accessToken: string) => void
  clearAuth: () => void
  isAuthenticated: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      setAuth: (user, accessToken) => set({ user, accessToken }),
      clearAuth: () => set({ user: null, accessToken: null }),
      isAuthenticated: () => get().accessToken !== null && get().user !== null,
    }),
    { name: 'bryton-auth' }
  )
)
```

**Note:** Access token stored in Zustand (in-memory + sessionStorage). Refresh token is httpOnly cookie — not accessible from JS. TanStack Query handles token refresh on 401 via a query client onError interceptor.

### Pattern 8: Approval Request Flow

```sql
-- approval_requests table
CREATE TABLE approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    requester_id UUID NOT NULL REFERENCES users(id),
    approver_id UUID REFERENCES users(id),      -- null until assigned
    type VARCHAR(50) NOT NULL,                  -- 'shortlist_submission', 'rate_override', etc.
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending, approved, rejected, changes_requested
    context_data JSONB NOT NULL DEFAULT '{}',   -- demand_id, candidate_id, etc.
    justification TEXT NOT NULL,
    decision_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- audit_log table (append-only, no UPDATE/DELETE)
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    actor_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,               -- 'approval.approved', 'approval.rejected', etc.
    entity_type VARCHAR(50),                    -- 'approval_request', 'user', etc.
    entity_id UUID,
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

RLS applies to `approval_requests` (tenant-scoped). `audit_log` is INSERT-only from application code; no UPDATE/DELETE endpoints.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rate limiting | Custom middleware counting requests in dict | `slowapi` | Thread-safety, TTL, Redis backend, decorator ergonomics |
| Password hashing | SHA256 or MD5 or raw bcrypt with wrong work factor | `bcrypt.hashpw` with rounds=12 | Side-channel timing attacks, salt generation, work factor |
| JWT expiry checking | Manual `datetime.now() > exp_field` | `jwt.decode()` with `algorithms=` — it validates `exp` automatically | Off-by-one timezone errors, clock skew |
| Email tokens | JWT for email verification | Separate `email_verification_tokens` table with `token` (secrets.token_urlsafe), `expires_at` | JWTs can't be invalidated; DB token can be deleted after use |
| RLS enforcement | Application-level WHERE clauses on every query | PostgreSQL RLS + `SET LOCAL app.current_tenant` | Missed clauses, SQL injection risk, maintainability |
| Role checks | if/elif chains in every endpoint | `require_roles()` dependency factory | Consistent 403, testable, single update point |
| Token refresh | Polling `/auth/refresh` on a timer | TanStack Query `onError` interceptor that retries on 401 | No polling, correct timing, race-condition-free |

---

## Common Pitfalls

### Pitfall 1: SET vs SET LOCAL (Critical Data Isolation Bug)
**What goes wrong:** Using `SET app.current_tenant = :id` (without LOCAL) means the GUC persists for the entire PostgreSQL connection, not just the transaction. With connection pooling, the next request reusing that connection sees the previous tenant's data.
**Why it happens:** Developers test with a single connection where the bug doesn't manifest.
**How to avoid:** Always `SET LOCAL app.current_tenant = :id`. SQLAlchemy async sessions begin a transaction automatically (autocommit=False), so SET LOCAL takes effect for the transaction lifetime.
**Warning signs:** Tests that run sequentially pass; concurrent tests with different tenants cross-contaminate.

### Pitfall 2: Superuser Bypasses RLS
**What goes wrong:** Using `get_db` (superuser engine) on a tenant-scoped endpoint returns all rows from all tenants silently.
**Why it happens:** It's easy to accidentally inject `get_db` instead of `get_tenant_db` in endpoint signatures.
**How to avoid:** Name them distinctly. Add a linting comment: `# TENANT-SCOPED: must use get_tenant_db`. Admin endpoints that legitimately need all tenants should explicitly use `get_db` with a comment.
**Warning signs:** TENANT-04 test (Customer can't see other tenant data) passes when it should.

### Pitfall 3: Access Token in localStorage (XSS)
**What goes wrong:** Storing access token in localStorage makes it readable by any JS on the page, including injected scripts.
**Why it happens:** Easy to implement; many tutorials do this.
**How to avoid:** Store access token in Zustand memory state (lost on tab close) or sessionStorage. The refresh token is httpOnly cookie and is never accessible from JS. On tab close, the user must re-login — this is the tradeoff.
**Warning signs:** Token visible in `localStorage` in browser devtools.

### Pitfall 4: Refresh Token Replay After Logout
**What goes wrong:** User logs out, but refresh token cookie remains valid until expiry (7 days). Attacker with cookie can get new access tokens.
**Why it happens:** JWT refresh tokens are stateless by nature — no server-side state to invalidate.
**How to avoid:** Store refresh token `jti` (JWT ID) in `refresh_tokens` table. On logout, delete the row. On `/auth/refresh`, look up `jti` and reject if not found.
**Warning signs:** `/auth/refresh` returns 200 after logout.

### Pitfall 5: RLS Policy Blocks Admin
**What goes wrong:** Admin user needs to see all tenants' data but the RLS policy blocks them because they're using `app_async_session` (bryton_app role).
**Why it happens:** RLS enforcement is at the DB role level, not the application role level.
**How to avoid:** Admin endpoints use `get_db` (superuser engine, bypasses RLS). Non-admin authenticated endpoints use `get_tenant_db`. This is already the design — just enforce it consistently.

### Pitfall 6: Empty current_setting Raising Exception
**What goes wrong:** `current_setting('app.current_tenant')` raises an error if the GUC has never been set, crashing queries that run before any tenant context is set (e.g., during migrations).
**Why it happens:** PostgreSQL raises ERROR for missing settings by default.
**How to avoid:** Use `current_setting('app.current_tenant', true)` — the `true` second argument returns NULL instead of raising. Always include NULL check in RLS policy: `OR current_setting('app.current_tenant', true) IS NULL`.

### Pitfall 7: JWT Payload Size
**What goes wrong:** Adding too much data to the JWT payload (full user object) causes cookie size issues and performance overhead on every request.
**Why it happens:** Temptation to avoid DB lookup by embedding everything in the token.
**How to avoid:** JWT payload: only `sub` (user_id), `role`, `tenant_id`, `type`, `exp`, `iat`. Fetch full user from DB in `get_current_user` dependency (one indexed lookup per request).

### Pitfall 8: TanStack Router context not hydrated at beforeLoad
**What goes wrong:** `beforeLoad` runs before the Zustand store is read from persisted storage, so `isAuthenticated` returns false on hard refresh even though the user is logged in.
**Why it happens:** Zustand `persist` middleware rehydrates asynchronously.
**How to avoid:** Use Zustand's `useAuthStore.persist.rehydrate()` and wait for `hasHydrated` flag before creating the router. Or read the token directly from sessionStorage in `beforeLoad`.

---

## Database Schema — Phase 2 Additions

### New Tables (Alembic migration 002)

```sql
-- Multi-tenant SM/Recruiter assignments
CREATE TABLE user_tenant_assignments (
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, tenant_id)
);

-- Refresh token store (for logout invalidation)
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,  -- bcrypt hash of token
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ
);
CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens(user_id);

-- Email verification + password reset tokens (short-lived, DB-backed)
CREATE TABLE email_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(128) NOT NULL UNIQUE,   -- secrets.token_urlsafe(64)
    token_type VARCHAR(20) NOT NULL,      -- 'verify_email', 'reset_password'
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ
);
CREATE INDEX ix_email_tokens_token ON email_tokens(token);
```

### User model extensions

```sql
-- Add to users table via Alembic migration 002
ALTER TABLE users
    ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN gdpr_consent BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN gdpr_consent_at TIMESTAMPTZ;

-- Change role default to match the 5-role enum
-- (migration: UPDATE users SET role='admin' WHERE role='user' for seeded admin)
```

### RLS policies for existing tables

Enable RLS only on tables that will contain tenant-scoped data. In Phase 2, only `users` gets RLS. Future phases add policies for demands, candidates, etc.

---

## Code Examples

### bcrypt password hash/verify (direct, no passlib)

```python
# Source: bcrypt library docs + requirements.txt constraint
import bcrypt

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
```

### Email sending (aiosmtplib)

```python
# app/utils/email.py
import aiosmtplib
from email.mime.text import MIMEText
from app.config import settings

async def send_email(to: str, subject: str, html_body: str) -> None:
    msg = MIMEText(html_body, "html")
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    await aiosmtplib.send(
        msg,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        start_tls=True,
    )
```

### TanStack Query API client with 401 refresh

```typescript
// frontend/src/lib/api.ts
import { QueryClient } from '@tanstack/react-query'
import { useAuthStore } from '../stores/auth'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const { accessToken } = useAuthStore.getState()
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    credentials: 'include',   // send httpOnly refresh_token cookie
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...init?.headers,
    },
  })

  if (res.status === 401) {
    // Try refresh
    const refresh = await fetch(`${BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    })
    if (refresh.ok) {
      const data = await refresh.json()
      useAuthStore.getState().setAuth(data.user, data.access_token)
      // Retry original request
      return apiFetch(path, init)
    } else {
      useAuthStore.getState().clearAuth()
      window.location.href = '/login'
    }
  }

  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
```

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| passlib for bcrypt | Direct `bcrypt` library | passlib adds no value for single-algo use; bcrypt 4.x is pure-Python and fast |
| python-jose for JWT | PyJWT | python-jose has CVEs; PyJWT is actively maintained; already in requirements.txt |
| Session-based auth | JWT access + httpOnly refresh cookie | Stateless access token; revocable refresh via DB; standard for SPAs |
| Application-level tenant WHERE clauses | PostgreSQL RLS | DB-enforced isolation; can't be bypassed by missed WHERE; auditable |
| Celery for background tasks | APScheduler (already used in Phase 1) | No additional infrastructure; APScheduler already running for ESCO sync |

---

## Open Questions

1. **Email provider for development**
   - What we know: `aiosmtplib` sends via SMTP; config needs SMTP credentials
   - What's unclear: Is there a MailHog/Mailpit dev container in the docker-compose?
   - Recommendation: Add `mailpit` service to docker-compose for local dev; production uses real SMTP. This is a DISCRETION AREA — the planner should include the mailpit dev service.

2. **Zustand persist hydration timing with TanStack Router**
   - What we know: Zustand `persist` is async on rehydration; `beforeLoad` may run before state is ready
   - What's unclear: Whether the existing `_auth.tsx` scaffold needs `createRootRouteWithContext` to thread auth state
   - Recommendation: Use `createRootRouteWithContext` with auth context; initialize router after Zustand hydrates (wrap in `StoreHydration` component with `hasHydrated` flag).

3. **Approval gate configuration schema in tenant.config JSONB**
   - What we know: `tenant.config` JSONB column exists; RBAC-03 says approval gates are configurable per tenant
   - What's unclear: Exact JSON structure for approval gate config
   - Recommendation: Use structure `{"approval_gates": {"shortlist_submission": true, "rate_override": true}}` with tenant-level overrides. Default gates active for all tenants.

4. **Rate limiting storage backend**
   - What we know: slowapi supports in-memory (default) and Redis backends
   - What's unclear: No Redis in the Phase 1 docker-compose
   - Recommendation: Use in-memory backend for Phase 2 (single-instance dev). Note in plan: upgrade to Redis backend when multi-instance deployment is needed. In-memory is fine for the success criteria tests.

---

## Sources

### Primary (HIGH confidence)
- Codebase at `/home/przem/bryton-ai-cv-app/` — all existing model/config/dep patterns read directly
- `requirements.txt` — confirmed PyJWT >=2.8, bcrypt >=4.0, python-multipart 0.0.20 already installed
- `package.json` — confirmed zustand ^5, react-hook-form ^7, zod ^3, @tanstack/react-query ^5 already installed
- `app/database.py` — dual engine pattern verified
- `app/deps.py` — TODO comments explicitly name Phase 02 items

### Secondary (MEDIUM confidence)
- [slowapi GitHub README](https://github.com/laurentS/slowapi) — installation, basic usage, middleware integration verified via WebFetch
- [Row-Level Security with SQLAlchemy and Alembic Guide](https://www.adrianovieira.eng.br/en/posts/architecture/row-level-security-sqlachemy-alembic-guide/) — SET LOCAL pattern, async session structure
- [TanStack Router Authenticated Routes Docs](https://tanstack.com/router/latest/docs/framework/react/guide/authenticated-routes) — beforeLoad + redirect pattern (URL returned 404 from WebFetch; pattern confirmed from prior knowledge + search snippets)

### Tertiary (LOW confidence — flagged for validation)
- Per-account rate limiting with slowapi: custom key_func pattern described in search results; exact async body-parsing approach for email-keyed limits needs implementation verification

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries confirmed in existing requirements.txt/package.json
- Architecture: HIGH — patterns derived directly from existing codebase structure + official library docs
- RLS patterns: HIGH — dual engine already implemented; SET LOCAL is documented PostgreSQL behavior
- Pitfalls: HIGH — most derive from direct codebase analysis (superuser bypass, SET vs SET LOCAL)
- Frontend auth guards: MEDIUM — TanStack Router official docs URL returned 404; pattern is well-established from search snippets and code reading

**Research date:** 2026-05-28
**Valid until:** 2026-06-28 (stable libraries; RLS patterns don't change)
