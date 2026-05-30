---
phase: "03-contracts-rate-cards-profile-catalogue"
plan: "01"
subsystem: "data-models"
tags: ["orm", "migration", "pydantic", "contracts", "profiles", "rate-cards", "rls"]
dependency_graph:
  requires: ["02-04"]
  provides: ["03-02", "03-03"]
  affects: ["alembic-migrations", "pydantic-schemas"]
tech_stack:
  added: []
  patterns: ["SQLAlchemy 2.0 Mapped[] mapped_column", "Alembic RLS migration", "Pydantic v2 model_validator", "Denormalised tenant_id for RLS"]
key_files:
  created:
    - backend/app/models/contract.py
    - backend/app/models/rate_card.py
    - backend/app/models/profile_catalogue.py
    - backend/app/models/profile_requirement.py
    - backend/app/models/demand.py
    - backend/app/schemas/contract.py
    - backend/app/schemas/profile.py
    - backend/alembic/versions/005_contracts_profiles.py
  modified:
    - backend/app/models/__init__.py
key_decisions:
  - "sfia_level stored as INTEGER with CHECK(1-7) on rate_cards — no FK to sfia_levels table"
  - "Numeric(10,2) used for max_daily_rate — never float"
  - "demands table created as minimal stub (Phase 5 adds remaining columns)"
  - "profile_requirements has denormalised tenant_id for RLS (avoids JOIN-based policies)"
  - "Table name rate_cards matches ARCHITECTURE.md (not rate_card_entries)"
  - "Partial unique index uq_profile_code_tenant for tenant-level profiles (contract_id IS NULL)"
  - "Margin not stored in DB — computed at read time from ceiling minus cost_rate"
metrics:
  duration: "~25 minutes"
  completed_date: "2026-05-30"
  tasks_completed: 2
  tasks_total: 2
  files_created: 8
  files_modified: 1
---

# Phase 03 Plan 01: Contracts, Rate Cards & Profile Catalogue — Data Models Summary

5 new ORM models + Alembic migration 005 with RLS policies + Pydantic v2 schemas for contracts, rate cards, profiles, requirements, and compliance checking.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create ORM models and Alembic migration | e9b93fb | contract.py, rate_card.py, profile_catalogue.py, profile_requirement.py, demand.py, __init__.py, 005_contracts_profiles.py |
| 2 | Create Pydantic v2 schemas for contracts, rate cards, and profiles | 4892f67 | schemas/contract.py, schemas/profile.py |

## What Was Built

### ORM Models (5 new)

**`backend/app/models/contract.py`** — `Contract` model on `contracts` table. Tenant-scoped with RLS. Columns: id, tenant_id (FK tenants), reference, title, lot_number, start_date, end_date, max_value (Numeric 15,2), currency (default EUR), status (active/expired/suspended), created_at, updated_at. `sla_config_id` intentionally omitted — added in Phase 9.

**`backend/app/models/rate_card.py`** — `RateCardEntry` model on `rate_cards` table. `sfia_level` is `INTEGER` with `CHECK(sfia_level BETWEEN 1 AND 7)` — NOT a UUID FK to sfia_levels (per locked decision). `max_daily_rate` uses `Numeric(10,2)`. `UNIQUE(contract_id, profile_id, sfia_level, effective_from)` enforced via `UniqueConstraint`. Cascades on contract deletion.

**`backend/app/models/profile_catalogue.py`** — `ProfileCatalogue` model on `profile_catalogue` table. `tenant_id` nullable (allows global profiles). `contract_id` nullable (allows tenant-level profiles). `UNIQUE(contract_id, code)` for contract-level code uniqueness. `sfia_level_min`/`sfia_level_max` both with `CHECK(1-7)`.

**`backend/app/models/profile_requirement.py`** — `ProfileRequirement` model on `profile_requirements` table. Has denormalised `tenant_id` (FK to tenants) for RLS enforcement — matches locked decision from session context. `req_type` covers: skill, certification, language, clearance, education. `min_cefr_level` only used for language requirements.

**`backend/app/models/demand.py`** — `Demand` stub model on `demands` table. Minimal Phase 3 fields only: id, tenant_id, profile_id (nullable FK to profile_catalogue), profile_snapshot (JSONB), created_at, updated_at. Phase 5 adds remaining demand columns via `ALTER TABLE`.

### Alembic Migration 005

**`backend/alembic/versions/005_contracts_profiles.py`** — Creates all 5 tables in FK-safe order:
1. `contracts` (FK to tenants only)
2. `profile_catalogue` (FK to tenants, contracts)
3. `demands` (FK to tenants, profile_catalogue)
4. `profile_requirements` (FK to profile_catalogue, tenants)
5. `rate_cards` (FK to contracts, profile_catalogue)

Each table has:
- Standard indexes on FK columns
- `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY`
- `tenant_isolation` policy matching the exact pattern from migrations 003/004
- `GRANT SELECT, INSERT, UPDATE, DELETE ... TO bryton_app`

Additional: partial unique index `uq_profile_code_tenant` on `profile_catalogue(tenant_id, code) WHERE contract_id IS NULL` — handles NULL uniqueness edge case in PostgreSQL. Composite index `ix_rate_cards_ceiling_lookup` on `(contract_id, profile_id, sfia_level, effective_from)` for CONTRACT-03 rate ceiling lookup performance.

Note: `rate_cards` uses contract-level tenant scoping (no direct tenant_id column) — bryton_app access controlled via grants; tenant isolation enforced through contracts RLS.

### Pydantic v2 Schemas (2 files)

**`backend/app/schemas/contract.py`**:
- `ContractCreate` — validates status enum (active/expired/suspended), enforces `end_date >= start_date`
- `ContractUpdate` — all fields optional, same validators
- `ContractResponse` — full response with `ConfigDict(from_attributes=True)`
- `RateCardEntryCreate` — `sfia_level` validated via `Field(ge=1, le=7)`, `max_daily_rate` via `Field(gt=0)`, `effective_to >= effective_from` via `model_validator`
- `RateCardEntryUpdate` — all fields optional
- `RateCardEntryResponse` — includes `margin: Decimal | None = None` (optional field for CONTRACT-04 role-gated visibility; populated by API layer, never stored in DB)

**`backend/app/schemas/profile.py`**:
- `ProfileRequirementCreate` — validates `req_type` enum (skill/certification/language/clearance/education)
- `ProfileRequirementResponse` — full response with `ConfigDict(from_attributes=True)`
- `ProfileCreate` — `sfia_level_max >= sfia_level_min` via `model_validator`, nested `requirements` list for atomic creation
- `ProfileUpdate` — all fields optional except code (immutable by convention), SFIA range validator applies when both present
- `ProfileResponse` — full response with nested `requirements: list[ProfileRequirementResponse]`
- `DemandDefaultsResponse` — pre-fill dict for PROFILE-02 demand creation; includes `profile_snapshot` dict
- `ProfileDiffEntry` / `ProfileDiffResponse` — PROFILE-03 field-level deviation tracking
- `ComplianceItem` / `ComplianceCheckResponse` — PROFILE-04 advisory compliance check (MET/PARTIALLY_MET/NOT_MET)

## Decisions Made

1. `sfia_level` on `rate_cards` stored as `INTEGER` with `CHECK(1-7)` — locked decision. Avoided UUID FK to `sfia_levels` table (which uses surrogate UUID PK, not integer PK).
2. `Numeric(10,2)` for all monetary fields — no `float` anywhere in the data layer.
3. Demands table created as minimal stub in Phase 3 — Phase 5 will use `ALTER TABLE` for remaining columns. This keeps demand FK linkage available for Phase 3 profile snapshot functionality.
4. Denormalised `tenant_id` on `profile_requirements` — avoids complex JOIN-based RLS policies that could fail under the `bryton_app` role.
5. Partial unique index `uq_profile_code_tenant` — necessary because standard `UNIQUE(contract_id, code)` treats each NULL as distinct in PostgreSQL, so tenant-level code uniqueness requires a `WHERE contract_id IS NULL` partial index.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

Files created:
- backend/app/models/contract.py — FOUND
- backend/app/models/rate_card.py — FOUND
- backend/app/models/profile_catalogue.py — FOUND
- backend/app/models/profile_requirement.py — FOUND
- backend/app/models/demand.py — FOUND
- backend/app/schemas/contract.py — FOUND
- backend/app/schemas/profile.py — FOUND
- backend/alembic/versions/005_contracts_profiles.py — FOUND
- backend/app/models/__init__.py — MODIFIED (appended, original imports preserved)

Commits verified:
- e9b93fb: feat(03-01): add ORM models and Alembic migration 005 for Phase 3
- 4892f67: feat(03-01): add Pydantic v2 schemas for contracts, rate cards, and profiles

## Self-Check: PASSED
