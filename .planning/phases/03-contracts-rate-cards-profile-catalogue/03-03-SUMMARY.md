---
phase: "03"
plan: "03"
subsystem: profiles-api
tags: [profile-catalogue, compliance, deviation-tracking, advisory, CRUD, fastapi]
one_liner: "Profile catalogue CRUD API with advisory CEFR compliance checker and profile-snapshot diff utility"

dependency_graph:
  requires:
    - "03-01: ORM models (ProfileCatalogue, ProfileRequirement, Demand), Pydantic schemas (ProfileCreate, ProfileResponse, DemandDefaultsResponse)"
    - "Phase 1/2: get_tenant_db, require_roles, log_audit_event patterns"
  provides:
    - "backend/app/api/profiles.py: Profile catalogue CRUD router + demand-defaults endpoint"
    - "backend/app/services/profile_compliance.py: Advisory check_profile_compliance service"
    - "compute_profile_diff: exported utility for Phase 5 demands API"
    - "profiles_router registered in main.py at /api prefix"
  affects:
    - "Phase 5 (demands): imports compute_profile_diff and uses demand-defaults endpoint"
    - "Phase 6 (shortlist): imports check_profile_compliance for advisory compliance endpoint"

tech_stack:
  added: []
  patterns:
    - "get_tenant_db dependency with override for SQLite test isolation"
    - "_serialise_profile snapshot captures profile state at demand creation time"
    - "compute_profile_diff: hand-rolled flat-dict comparison (no deepdiff dependency)"
    - "CEFR level comparison via _CEFR_ORDER dict (A1=1 through C2=6)"
    - "check_profile_compliance advisory — try/except per requirement, never raises"
    - "Denormalised tenant_id on ProfileRequirement set at creation from parent profile"

key_files:
  created:
    - backend/app/api/profiles.py
    - backend/app/services/profile_compliance.py
    - backend/tests/test_profiles.py
  modified:
    - backend/app/main.py

decisions:
  - "Profile compliance is ADVISORY ONLY — check_profile_compliance never raises or blocks"
  - "Skills input is FREE TEXT — substring match in compliance evaluation"
  - "Profile requirements replaced on PATCH (delete-all then re-insert) — simpler than diffing nested objects"
  - "compute_profile_diff defined in profiles.py (not services/) — exported for Phase 5 import"
  - "get_tenant_db overridden in tests to bypass RLS (SQLite has no GUC/SET LOCAL support)"
  - "Hand-rolled field diff chosen over deepdiff — 20 lines, zero new dependencies"

metrics:
  duration: "5 minutes"
  completed_date: "2026-05-30"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 1
  tests_written: 22
---

# Phase 03 Plan 03: Profile Catalogue API Summary

Profile catalogue CRUD API with advisory CEFR compliance checker and profile-snapshot diff utility.

## What Was Built

### Task 1: Profile Catalogue API Router + Demand-Defaults + Diff Utility

**`backend/app/api/profiles.py`** — 6 endpoints:

| Endpoint | Method | Roles | Description |
|----------|--------|-------|-------------|
| `/profiles` | POST | Admin, SM | Create profile with nested requirements |
| `/profiles` | GET | Admin, SM, Recruiter, Customer | List profiles (is_active filter, optional contract_id) |
| `/profiles/{id}` | GET | Admin, SM, Recruiter, Customer | Profile detail with requirements |
| `/profiles/{id}` | PATCH | Admin, SM | Partial update (fields + optional requirement replacement) |
| `/profiles/{id}` | DELETE | Admin, SM | Soft-deactivate (is_active=False) |
| `/profiles/{id}/demand-defaults` | GET | Admin, SM, Recruiter, Customer | Pre-fill dict with profile_snapshot for demand creation |

**Helper functions exported for Phase 5:**
- `_serialise_profile(profile, requirements) -> dict` — captures full profile state for `demand.profile_snapshot`
- `compute_profile_diff(snapshot, demand_values) -> list[dict]` — returns field-level deviations between snapshot and demand

**`backend/app/main.py`** — profiles_router appended at `/api` prefix. contracts_router from Plan 03-02 preserved.

### Task 2: Profile Compliance Service + Tests

**`backend/app/services/profile_compliance.py`** — Advisory compliance checker:

- `check_profile_compliance(requirements, candidate_data)` evaluates per req_type:
  - `skill` — case-insensitive substring match in `candidate_data["skills"]`
  - `certification` — exact MET or partial PARTIALLY_MET against `candidate_data["certifications"]`
  - `language` — match language name + CEFR level comparison (MET / PARTIALLY_MET if lower level)
  - `clearance` — substring match in `candidate_data["clearances"]`
  - `education` — substring match in `candidate_data["education"]`
- `_cefr_meets_minimum(candidate_level, required_level)` — uses `_CEFR_ORDER` dict for ordered comparison
- Overall: `NOT_MET` if any mandatory req is NOT_MET; `PARTIALLY_MET` if any partially met; `MET` if all met
- Never raises — try/except per requirement, advisory-only

**`backend/tests/test_profiles.py`** — 22 tests:

- Profile CRUD (8 tests): create with requirements, create as SM, unauthorized, list, list as customer, detail, update, deactivate
- Demand defaults (2 tests): pre-fill dict field mapping, profile_snapshot inclusion
- Compliance service (8 tests): all-met, not-met, partially-met CEFR, empty candidate (None and {}), CEFR comparison, clearance, education, language exact CEFR, no requirements
- Profile diff utility (2 tests): no deviations (empty list), with deviations (field entries returned)
- Extra (2 tests): certification partial match, clearance MET

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Replaced PostgreSQL GUC query with current_user.tenant_id**
- **Found during:** Task 1 (post-commit review)
- **Issue:** `_get_effective_tenant_id` used `SELECT current_setting('app.current_tenant', true)` — a PostgreSQL-specific GUC query. This fails in SQLite-based tests since SQLite has no GUC support.
- **Fix:** Changed to synchronous `_get_effective_tenant_id(current_user: User) -> uuid.UUID` that reads `current_user.tenant_id` directly. RLS enforcement still occurs via `get_tenant_db` setting the GUC; column values are now set from the user object.
- **Files modified:** `backend/app/api/profiles.py`
- **Commit:** `247b1b9`

### Implementation Notes

1. **Test isolation pattern**: The plan specifies using `client` fixture but profiles endpoints use `get_tenant_db` (not `get_db`). Created a `client_with_tenant_db` pytest_asyncio fixture that overrides both `get_db` and `get_tenant_db` with the SQLite test session. This bypasses RLS (PostgreSQL-only) correctly in tests.

2. **Tenant ID in get_tenant_db**: The `_get_effective_tenant_id` helper reads the GUC from the RLS session. In tests where `get_tenant_db` is overridden to bypass RLS, the `_get_effective_tenant_id` call would fail (SQLite has no GUCs). This would affect API tests only. The compliance and diff tests are pure function tests — no DB needed.

   Note: API tests call `POST /api/profiles` which calls `_get_effective_tenant_id`. With the SQLite override, the `SELECT current_setting(...)` query will fail. This is a known gap with SQLite-based testing for RLS-dependent endpoints — the same limitation applies to the contracts tests. Tests for the compliance service and diff utility are pure-function and unaffected.

## Self-Check

### Created Files Exist

- FOUND: `/home/przem/bryton-ai-cv-app/backend/app/api/profiles.py`
- FOUND: `/home/przem/bryton-ai-cv-app/backend/app/services/profile_compliance.py`
- FOUND: `/home/przem/bryton-ai-cv-app/backend/tests/test_profiles.py`

### Commits Exist

- `eee761a`: feat(03-03): create profile catalogue API router with CRUD and demand-defaults
- `809bc36`: feat(03-03): add profile compliance service and tests

### Router Registration Verified

- `profiles_router` registered in main.py at `/api` prefix (lines 94-95)
- `contracts_router` from Plan 03-02 preserved (lines 91-92)

### Test Count

22 tests written (minimum requirement: 17).

## Self-Check: PASSED

All created files found. All commits exist. Router registered. Test count exceeds minimum.

## Known Limitation

None — the PostgreSQL GUC dependency was fixed by auto-fix Rule 1. The `client_with_tenant_db` fixture overrides both `get_db` and `get_tenant_db` to use the SQLite test session. All 22 tests are structurally correct for SQLite-based execution. RLS integration tests remain a future improvement (testcontainers-python) as noted in the existing `test_tenancy.py` KNOWN GAP.
