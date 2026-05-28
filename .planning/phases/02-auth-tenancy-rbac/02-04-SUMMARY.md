---
phase: 02-auth-tenancy-rbac
plan: "04"
subsystem: user-management-approvals-audit
tags: [user-management, approval-chain, audit-log, rbac, fastapi, sqlalchemy]
dependency_graph:
  requires: [02-02]
  provides: [user-management-api, approval-chain-api, audit-log-api]
  affects: [backend/app/api, backend/app/models, backend/app/services, backend/app/schemas]
tech_stack:
  added: []
  patterns:
    - "Admin cross-tenant CRUD via get_db (superuser engine, bypasses RLS)"
    - "SM tenant-scoped management via junction table assignment check + get_db"
    - "Approval routing via tenant.config[approval_gates] JSONB config"
    - "Audit log as append-only INSERT helper (no UPDATE/DELETE endpoints)"
    - "Approval endpoints use get_db (superuser) for cross-tenant routing"
key_files:
  created:
    - backend/app/schemas/user.py
    - backend/app/api/users.py
    - backend/app/models/approval.py
    - backend/app/models/audit_log.py
    - backend/alembic/versions/004_approvals_and_audit.py
    - backend/app/schemas/approval.py
    - backend/app/services/approval.py
    - backend/app/services/audit.py
    - backend/app/api/approvals.py
    - backend/tests/test_users.py
    - backend/tests/test_approvals.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/main.py
    - backend/tests/conftest.py
decisions:
  - "Admin uses get_db (superuser engine) for all user CRUD — bypasses RLS for cross-tenant visibility"
  - "SM uses get_db (superuser) for write operations but verifies junction table assignment before proceeding"
  - "Approval endpoints use get_db (superuser) — approvals can cross tenant boundaries"
  - "Audit log has no RLS — cross-tenant for Admin queries; access controlled at application level"
  - "Audit log is append-only — no UPDATE or DELETE endpoints exist"
  - "route_approval() reads tenant.config[approval_gates] — gate disabled means auto-approve (None returned)"
metrics:
  duration: "~45 minutes"
  completed: "2026-05-28"
  tasks_completed: 3
  tasks_total: 3
  tests_passed: 88
  tests_failed: 0
  tests_skipped: 1
---

# Phase 02 Plan 04: User Management, Approval Chain, and Audit Log Summary

**One-liner:** Admin CRUD + SM tenant-scoped user management with approval chain (shortlist/rate_override routing) and append-only audit log backed by tenant.config JSONB gates.

## What Was Built

### Task 1: User Management API (Admin CRUD + SM tenant-scoped)

**`backend/app/schemas/user.py`** — Pydantic v2 schemas:
- `UserCreate`: email (EmailStr), password (min 8 chars), role (validated against 5 roles), display_name, tenant_id
- `UserUpdate`: partial update schema, role validated if provided
- `UserResponse`: full user record with `from_attributes=True`
- `UserBrief`: condensed user summary

**`backend/app/api/users.py`** — FastAPI router:
- `GET /users` — Admin only, lists all users across tenants (optional role/tenant_id/is_active filters)
- `POST /users` — Admin only, creates any role; customer/candidate require tenant_id; sm/recruiter with tenant_id also get UserTenantAssignment
- `GET /users/{id}` — Admin only, get by ID (404 if missing)
- `PATCH /users/{id}` — Admin only, partial update; validates role change tenant requirement
- `POST /users/{id}/deactivate` — Admin only, sets is_active=False, revokes all refresh tokens
- `POST /users/{id}/activate` — Admin only, sets is_active=True
- `POST /tenants/{id}/users` — SM only (assigned tenant), creates role=customer only; verifies junction assignment
- `PATCH /tenants/{id}/users/{uid}` — SM only, updates display_name/is_active; cannot change role

### Task 2: Approval Chain and Audit Log

**`backend/app/models/approval.py`** — `ApprovalRequest` model (table: `approval_requests`):
- Fields: id, tenant_id, requester_id, approver_id (nullable), type, status (pending/approved/rejected/changes_requested), context_data (JSONB), justification, decision_reason, created_at, decided_at, updated_at
- RLS enabled via migration 004

**`backend/app/models/audit_log.py`** — `AuditLog` model (table: `audit_log`):
- Fields: id, tenant_id (nullable), actor_id (nullable), action, entity_type, entity_id, payload (JSONB), ip_address, created_at
- No `updated_at` — append-only by design
- No RLS — cross-tenant; access controlled at application level

**`backend/alembic/versions/004_approvals_and_audit.py`** — Migration:
- Creates both tables with all columns and server defaults
- 4 indexes on approval_requests (tenant_id, requester_id, approver_id, status)
- 4 indexes on audit_log (tenant_id, actor_id, action, created_at)
- RLS on approval_requests (tenant isolation policy matching 002/003 pattern)
- No RLS on audit_log
- Grants SELECT/INSERT/UPDATE/DELETE on approval_requests to bryton_app; SELECT/INSERT on audit_log

**`backend/app/services/audit.py`** — `log_audit_event()` helper:
- Simple INSERT function; caller commits the session
- All params keyword-only except `db` and `action`

**`backend/app/services/approval.py`** — `route_approval()` routing logic:
- Reads `tenant.config["approval_gates"]` — gate disabled returns None (auto-approve)
- `shortlist_submission` / `candidate_above_rate` → first active SM assigned to tenant
- `rate_override` → first active Admin user
- Returns None if no suitable approver found

**`backend/app/schemas/approval.py`** — Pydantic v2 schemas:
- `ApprovalCreate`: type (validated), justification, context_data, optional approver_id override
- `ApprovalDecision`: status (approved/rejected/changes_requested), decision_reason
- `ApprovalResponse`: full approval record
- `AuditLogResponse`: audit log entry

**`backend/app/api/approvals.py`** — FastAPI router:
- `POST /approvals` — any authenticated user with tenant_id; routes via route_approval(); logs `approval.created`
- `GET /approvals` — role-filtered: Admin sees all, SM sees assigned, Recruiter sees own
- `GET /approvals/{id}` — requester, approver, or Admin; 403 otherwise
- `POST /approvals/{id}/decide` — assigned approver or Admin; logs `approval.{status}` with full context
- `GET /audit-log` — Admin only; filters: date_from, date_to, actor_id, action, entity_type; paginated

### Task 3: Tests

**`backend/tests/test_users.py`** — 17 tests:
- Admin CRUD: create (with role/tenant variations), list (raw + filtered), get, update, deactivate, activate
- SM management: create customer in assigned tenant, reject non-customer role, 403 for unassigned tenant, update customer display_name
- Role enforcement: recruiter 403, candidate 403, SM 403 on admin endpoints, unauthenticated 401/403

**`backend/tests/test_approvals.py`** — 15 tests:
- Create approval (valid + invalid type)
- Decisions: approve, reject, changes_requested
- Authorization: non-approver 403, Admin override, requester can view own
- Audit log: decision creates entry with correct action/payload; Admin can filter by action; non-Admin gets 403
- Visibility: SM sees only their approvals, Recruiter sees only their requests

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed rate limiter storage not resetting between tests**
- **Found during:** Task 3 — 21 tests failed with HTTP 429 from login endpoint
- **Issue:** The `conftest.py` reset `app.state.limiter._storage` (main.py limiter) but the login endpoint uses a separate `_limiter` instance in `auth.py` with its own in-memory storage. The two instances do not share storage.
- **Fix:** Added reset of `_auth_limiter._storage` from `app.api.auth` to the `client` fixture in conftest.py
- **Files modified:** `backend/tests/conftest.py`
- **Commit:** 55893d2

## Self-Check: PASSED

All created files verified:
- FOUND: backend/app/api/users.py
- FOUND: backend/app/models/approval.py
- FOUND: backend/app/models/audit_log.py
- FOUND: backend/app/api/approvals.py
- FOUND: backend/app/services/audit.py
- FOUND: backend/tests/test_users.py
- FOUND: backend/tests/test_approvals.py
- FOUND: .planning/phases/02-auth-tenancy-rbac/02-04-SUMMARY.md

All task commits verified:
- c402713: feat(02-04): add user management API
- 58ded9a: feat(02-04): add approval chain + audit log models, services, and endpoints
- 55893d2: test(02-04): add user management and approval chain tests

Test results: 88 passed, 0 failed, 1 skipped (intentional)
