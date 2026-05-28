---
phase: 02-auth-tenancy-rbac
plan: "01"
subsystem: backend-auth
tags: [auth, jwt, bcrypt, email-verification, password-reset, rate-limiting, slowapi, aiosmtplib, mailpit]
dependency_graph:
  requires: [01-infrastructure]
  provides: [get_current_user, JWT auth flow, email token verification, password reset]
  affects: [all protected endpoints in future plans]
tech_stack:
  added:
    - slowapi>=0.1 (rate limiting)
    - aiosmtplib>=3.0 (async SMTP)
    - pydantic[email] (EmailStr validation)
    - mailpit (docker-compose dev email capture)
  patterns:
    - JWT access token (15-min HS256) + httpOnly refresh cookie (7-day)
    - bcrypt direct (rounds=12, NOT passlib)
    - DB-backed email tokens (secrets.token_urlsafe(64)) for verification + reset
    - In-memory per-account brute-force protection (5 attempts / 15 min)
key_files:
  created:
    - backend/alembic/versions/002_auth_tables.py
    - backend/app/models/refresh_token.py
    - backend/app/models/email_token.py
    - backend/app/schemas/auth.py
    - backend/app/services/auth.py
    - backend/app/utils/email.py
    - backend/app/api/auth.py
    - backend/tests/test_auth.py
  modified:
    - backend/app/models/user.py (email_verified, gdpr_consent, gdpr_consent_at)
    - backend/app/models/__init__.py (RefreshToken, EmailToken imports)
    - backend/app/config.py (SMTP settings, COOKIE_SECURE, FRONTEND_URL, JWT expiry=15)
    - backend/app/deps.py (get_current_user implemented)
    - backend/app/main.py (slowapi, auth router registered at /api/auth/*)
    - backend/requirements.txt (slowapi, aiosmtplib, pydantic[email])
    - docker-compose.yml (mailpit service)
    - backend/tests/conftest.py (SQLiteUUID TypeDecorator, slowapi reset between tests)
decisions:
  - "JWT access token expiry: 15 minutes (locked from session decisions)"
  - "bcrypt.hashpw/checkpw used directly — no passlib anywhere"
  - "Refresh token JTI stored as bcrypt hash in refresh_tokens table for constant-time lookup"
  - "COOKIE_SECURE=False in config (False for dev, overridable via COOKIE_SECURE=true env var in prod)"
  - "In-memory per-account rate limiting (5 attempts/15 min) + slowapi per-IP (10/min)"
  - "Email token stored in DB (secrets.token_urlsafe(64)) — NOT JWT, can be invalidated"
  - "Auth endpoints at /api/auth/* (not /auth/*)"
  - "SQLiteUUID TypeDecorator in conftest remaps postgresql.UUID for SQLite test compatibility"
metrics:
  duration_seconds: 3085
  completed_date: "2026-05-28"
  tasks_completed: 3
  tasks_total: 3
  files_created: 8
  files_modified: 8
  tests_passed: 34
  tests_failed: 0
  tests_skipped: 1
---

# Phase 2 Plan 01: Auth Backend (JWT + Email + Rate Limiting) Summary

**One-liner:** JWT auth with 15-min access tokens + 7-day httpOnly refresh cookies, bcrypt passwords, DB-backed email verification and password-reset tokens, slowapi rate limiting, and mailpit dev email capture.

## What Was Built

### Task 1: Auth models, schemas, services, and email utility (commit 3888ece)

- **requirements.txt**: Added `slowapi>=0.1`, `aiosmtplib>=3.0`, `pydantic[email]` (email-validator required by EmailStr)
- **docker-compose.yml**: Added `mailpit` service (ports 8025 web UI, 1025 SMTP) for dev email capture
- **config.py**: Added SMTP settings (host=mailpit, port=1025, no auth), `COOKIE_SECURE=False`, `FRONTEND_URL`, changed `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` from 60 to 15
- **models/user.py**: Added `email_verified`, `gdpr_consent`, `gdpr_consent_at` columns
- **models/refresh_token.py**: New model — `token_hash` (bcrypt of jti), `expires_at`, `revoked_at`, FK to users CASCADE
- **models/email_token.py**: New model — `token` (secrets.token_urlsafe(64)), `token_type` (verify_email/reset_password), `expires_at`, `used_at`, FK to users CASCADE
- **alembic/versions/002_auth_tables.py**: Migration adding 3 user columns + refresh_tokens + email_tokens tables with indexes
- **schemas/auth.py**: Pydantic v2 schemas for all auth endpoints (RegisterRequest, CandidateRegisterRequest, LoginRequest, TokenResponse, etc.)
- **services/auth.py**: `hash_password`, `verify_password`, `create_access_token`, `create_refresh_token`, `decode_token`, `generate_email_token`
- **utils/email.py**: `send_email` (aiosmtplib), `send_verification_email`, `send_password_reset_email`

### Task 2: Auth API endpoints + get_current_user dependency (commit 61e8abb)

- **deps.py**: Implemented `get_current_user` — HTTPBearer extraction, PyJWT decode, type="access" check, User DB lookup, is_active + email_verified validation
- **api/auth.py**: 8 endpoints at `/api/auth/*`:
  - `POST /register` — creates user (role=candidate), sends verification email
  - `POST /register/candidate` — same + gdpr_consent=True + gdpr_consent_at=now
  - `POST /login` — `@_limiter.limit("10/minute")` per-IP + in-memory per-account (5/15min), returns access token + httpOnly refresh cookie
  - `POST /refresh` — reads refresh cookie, bcrypt-checks JTI against DB, issues new access token
  - `POST /logout` — revokes refresh token in DB, deletes cookie
  - `POST /verify-email` — looks up EmailToken, sets email_verified=True
  - `POST /forgot-password` — creates reset token, sends email; always returns 200 (no enumeration)
  - `POST /reset-password` — applies new password, revokes all existing refresh tokens
- **main.py**: Added slowapi `Limiter`, `SlowAPIMiddleware`, `RateLimitExceeded` handler; registered auth router at `/api/auth/*`

### Task 3: Auth endpoint tests (commit bd6f61a)

- **conftest.py**: Added `SQLiteUUID` TypeDecorator (maps PostgreSQL UUID to `String(36)` for SQLite), JSONB→JSON remapping, slowapi limiter reset and per-account attempt clearing between tests
- **test_auth.py**: 18 passing tests + 1 skipped covering:
  - Registration (success, duplicate, short password, candidate GDPR, no GDPR)
  - Login (unverified 403, success, invalid credentials)
  - Email verification (success, invalid token, expired token)
  - Token refresh (success, no cookie 401)
  - Logout + invalidation
  - Forgot password (unknown email still 200, known email creates DB token)
  - Password reset (full flow, invalid token)
  - Rate limit test skipped (requires running server)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Missing Dependency] Added `pydantic[email]` to requirements.txt**
- **Found during:** Task 1 import verification
- **Issue:** `EmailStr` requires the `email-validator` package; pydantic doesn't include it by default
- **Fix:** Changed `pydantic==2.10.*` to `pydantic[email]==2.10.*` in requirements.txt; installed `email-validator`
- **Files modified:** `backend/requirements.txt`
- **Commit:** 3888ece

**2. [Rule 1 - Bug] Fixed timezone-naive vs timezone-aware datetime comparison in refresh endpoint**
- **Found during:** Task 3 test execution
- **Issue:** SQLite returns timezone-naive datetimes from `DateTime(timezone=True)` columns; comparing `expires_at < datetime.now(timezone.utc)` raised `TypeError`
- **Fix:** Added `.tzinfo is None` check in refresh endpoint — naive datetimes treated as UTC; production PostgreSQL returns aware datetimes unaffected
- **Files modified:** `backend/app/api/auth.py`
- **Commit:** bd6f61a

**3. [Rule 1 - Bug] Fixed `await db_session.expire_all()` — expire_all() is synchronous**
- **Found during:** Task 3 test execution (test_verify_email_success)
- **Issue:** `expire_all()` is a sync method on AsyncSession; awaiting it raises `TypeError`
- **Fix:** Removed `await` keyword
- **Files modified:** `backend/tests/test_auth.py`
- **Commit:** bd6f61a

## Self-Check: PASSED

All created files exist on disk. All commits verified in git log. 34 tests pass, 1 skipped.

Key artifacts verified:
- `backend/alembic/versions/002_auth_tables.py` — FOUND
- `backend/app/models/refresh_token.py` — FOUND
- `backend/app/models/email_token.py` — FOUND
- `backend/app/schemas/auth.py` — FOUND
- `backend/app/services/auth.py` — FOUND
- `backend/app/utils/email.py` — FOUND
- `backend/app/api/auth.py` — FOUND
- `backend/tests/test_auth.py` — FOUND

Commits verified:
- 3888ece (Task 1: models, schemas, services, email utility)
- 61e8abb (Task 2: API endpoints + rate limiting + get_current_user)
- bd6f61a (Task 3: tests + SQLite compatibility fixes)
