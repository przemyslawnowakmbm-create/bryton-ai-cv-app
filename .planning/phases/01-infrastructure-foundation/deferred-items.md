# Deferred Items — Phase 01

## Pre-existing Test Failures (out of scope for Plan 01-03)

**Issue:** 12 tests in test_health.py, test_reference.py, and test_seed.py fail during conftest.py db_engine fixture setup with:
```
sqlalchemy.exc.UnsupportedCompilationError: Compiler can't render element of type JSONB
```

**Root cause:** `backend/app/models/tenant.py` uses PostgreSQL-specific `JSONB` type on the `config` column. The test `conftest.py` creates an in-memory SQLite database via `Base.metadata.create_all` — SQLite does not support JSONB.

**Origin:** Introduced in Plan 01-01 when Tenant model was created with JSONB config column.

**Deferred to:** Future plan (suggest Plan 02 or a dedicated test-infra fix). Fix options:
1. Replace `JSONB` with `JSON` in tenant model (SQLite-compatible, PostgreSQL still supports it)
2. Override the column type in conftest.py only for test scenarios
3. Skip SQLite-based tests for models using JSONB columns

**Impact:** ESCO sync tests (4/4) pass. Plan 01-03 deliverables are not affected.
