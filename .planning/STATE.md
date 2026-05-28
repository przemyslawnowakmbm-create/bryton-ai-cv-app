# Bryton AI CV App — Project State

## Project Reference

**Core value**: Demonstrate auditable, AI-powered recruitment governance to EUROCONTROL — every candidate submission backed by profile compliance checks, rate card enforcement, security clearance validation, and explainable AI matching, all visible through real-time SLA dashboards.

**Current focus**: Phase 1 — Infrastructure & Foundation

---

## Current Position

| Field | Value |
|-------|-------|
| Milestone | v1 |
| Phase | 1 — Infrastructure & Foundation |
| Plan | Not started |
| Status | Roadmap created, awaiting planning |

**Progress bar**: Phase 0/10 complete

```
[          ] 0%
Phase: 1/10 | Plans: 0 complete
```

---

## Performance Metrics

| Metric | Value |
|--------|-------|
| Phases total | 10 |
| Phases complete | 0 |
| Plans complete | 0 |
| Requirements mapped | 102/102 |
| Coverage | 100% |

---

## Accumulated Context

### Key Decisions

| Decision | Rationale |
|----------|-----------|
| Hybrid multi-tenancy (shared DB + RLS) | Balance isolation with operational simplicity at 5-20 tenant scale |
| LLM holistic matching over taxonomy-driven | Free-text skills + Claude reads full JD vs full CV catches contextual matches no code system would |
| ESCO as background enrichment only | Users should never be constrained by taxonomy; ESCO powers analytics silently |
| Profile catalogue as template, not constraint | Flexibility for customers to customize demands while maintaining audit trail of deviations |
| Advisory profile compliance (not blocking) | Demands intentionally modified from profile should not trigger false compliance failures |
| EU AI Act compliance from day one | Enforcement Aug 2026; retrofitting is harder than building it in |
| Desktop-only target (min 1280px) | Internal enterprise tool, all users on office computers |
| No placement tracking | EUROCONTROL has a separate system for post-hire engagement |

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite + TypeScript + Tanstack Router |
| UI | Shadcn/UI + Tailwind CSS + EUROCONTROL design system (Exo font, EC color palette) |
| Backend | Python FastAPI + async SQLAlchemy 2.0 + Alembic + Pydantic v2 |
| Database | PostgreSQL 16 with Row-Level Security |
| AI | Anthropic Claude API exclusively |
| File storage | Azure Blob Storage |
| Deployment | Docker Compose on single Azure VM (Standard_D4s_v5) |
| Auth | Username/password + JWT (Entra ID deferred to v2) |

### Important Constraints

- Multi-tenancy enforced via PostgreSQL RLS (`SET app.current_tenant` per session)
- EU AI Act Annex III Category 4 (recruitment AI high-risk) — enforcement Aug 2, 2026
- 7-year audit log retention required (EU institutional contract)
- 5 roles: Admin, SM (Service Manager), Recruiter, Customer, Candidate
- SFIA framework for seniority; ESCO for background skills enrichment only
- Security clearances: NATO/EU/National types with 3-18 month lead times
- Rate card ceiling enforcement with SM approval chain for overrides

### External Systems

| System | Integration approach |
|--------|---------------------|
| Atos tool | Manual text field for external demand ID only |
| EUROCONTROL engagement system | No integration — post-hire tracking is out of scope |

### Todos

- [ ] Begin Phase 1 planning with `/forge-plan-phase 1`

### Blockers

None

---

## Session Continuity

**Last active**: 2026-05-28 — Roadmap created by forge-roadmap agent

**To resume**: Run `/forge-plan-phase 1` to begin planning Phase 1 (Infrastructure & Foundation)

**Phase sequence**:
1. Infrastructure & Foundation (INFRA-01..06)
2. Auth, Tenancy & RBAC (AUTH-01..08, TENANT-01..05, RBAC-01..05)
3. Contracts, Rate Cards & Profile Catalogue (CONTRACT-01..04, PROFILE-01..04)
4. Candidate Profiles & CV Management (CAND-01..09)
5. Demand Management & AI JD Enhancement (DEMAND-01..07, AIJD-01..06)
6. AI Matching & Shortlisting (MATCH-01..08, SHORT-01..03)
7. CV Verification & Formatted CV (VERIFY-01..04, FMTCV-01..03)
8. Interviews & Assessments (INTV-01..05, ASSESS-01..05)
9. SLA, Dashboards & Reporting (SLA-01..05, DASH-01..06)
10. Notifications, Audit & Compliance (NOTIF-01..03, AUDIT-01..06)

---

*Last updated: 2026-05-28*
