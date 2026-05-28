# Bryton AI CV App

## What This Is

A multi-tenant T&M staffing governance platform that manages the full recruitment lifecycle — from demand creation through AI-powered candidate matching, interview, assessment, and hire — purpose-built for EU institutional framework contracts (EUROCONTROL). Covers recruitment up to onboarding/hire; post-hire tracking handled by an external system.

## Core Value

Demonstrate auditable, AI-powered recruitment governance to EUROCONTROL — every candidate submission backed by profile compliance checks, rate card enforcement, security clearance validation, and explainable AI matching, all visible through real-time SLA dashboards.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Multi-tenant data isolation with PostgreSQL RLS (5-20 tenants)
- [ ] 5-role RBAC: Admin, Service Manager, Recruiter, Customer, Candidate
- [ ] Username/password auth with JWT (Entra ID deferred)
- [ ] Four-eyes approval chain (configurable per tenant)
- [ ] CV upload (PDF/DOCX) with AI parsing via Claude API
- [ ] SFIA level inference from CV evidence
- [ ] CEFR language proficiency tracking
- [ ] Security clearance lifecycle management (NATO/EU/National)
- [ ] ESCO skills taxonomy as background enrichment (invisible to users)
- [ ] Contract and rate card management with ceiling enforcement
- [ ] Profile catalogue as demand templates (not constraints)
- [ ] Demand creation with free-text skills, tenant-prefixed numbering, 8-state lifecycle
- [ ] Replacement demand workflow with stricter SLA
- [ ] AI JD enhancement (hybrid chat + inline editor with bias detection)
- [ ] JD versioning with full chat history persistence
- [ ] LLM holistic CV-to-demand matching (hard filters + Claude assessment)
- [ ] AI explainability — narrative explanation per match (EU AI Act)
- [ ] Auto-shortlisting with recruiter review and SM approval gate
- [ ] Structured rejection reasons at every pipeline stage
- [ ] CV verification checklists with evidence upload
- [ ] Formatted CV generation (Brayton-branded template, PDF/DOCX)
- [ ] AI interview question generation (technical, behavioral, situational)
- [ ] Scorecard templates with aggregated scoring
- [ ] Manual interview scheduling with email notifications
- [ ] Configurable test builder with AI-suggested questions
- [ ] In-app assessment taking with server-side timer enforcement
- [ ] AI assessment scoring with human override
- [ ] SLA/KPI management with client-visible dashboards
- [ ] Quality survey on demand fill
- [ ] Role-specific dashboards with full BI charts
- [ ] CSV/PDF exports including formatted CVs, scorecards, SLA reports
- [ ] In-app + email notifications (configurable per event, real-time via WebSocket)
- [ ] AI chat streaming via SSE
- [ ] GDPR consent tracking and right-to-be-forgotten
- [ ] EU AI Act compliance: decision logging, human oversight, transparency
- [ ] 7-year audit trail with tiered hot/cold storage
- [ ] Bulk audit export for external auditors
- [ ] EUROCONTROL design system (Exo font, EC color palette, Shadcn/UI)
- [ ] Docker Compose deployment on Azure VM

### Out of Scope

- Microsoft Entra ID SSO — deferred to Phase 2, architecture prepared for OIDC
- Calendar integration (Outlook/Google) — manual scheduling only
- Atos API integration — manual text field for external demand ID
- Mobile/tablet optimization — desktop-only (min 1280px)
- Self-service tenant registration — Admin provisions tenants manually
- Billing/metering per tenant — not needed at this scale
- Video interview hosting — interviews happen offline
- Bias detection / adverse impact analysis — on hold, future phase
- Active placement / post-hire tracking — handled by external EUROCONTROL system
- Timesheet / hours tracking — handled by external system
- Automated reference checking — manual verification workflow instead
- Multi-language / i18n — English only
- Candidate sourcing from external job boards — candidates self-register

## Context

This tool is being built by Brayton Global to demonstrate recruitment process governance to EUROCONTROL under a T&M framework contract. The primary audience for the tool's governance features is EUROCONTROL's procurement office — they evaluate suppliers on process control, auditability, and SLA compliance.

Key context:
- EUROCONTROL uses predefined profile catalogues (similar to DIGIT-TM III framework)
- Rate cards define maximum daily-rate ceilings per profile per SFIA level
- NATO security clearances required for many positions (3-18 month lead time)
- EU AI Act classifies recruitment AI as high-risk (Annex III Category 4), enforcement Aug 2, 2026
- SFIA (Skills Framework for the Information Age) is the standard seniority taxonomy
- ESCO (European Commission skills taxonomy) used for background analytics only
- Existing EUROCONTROL design system from L1 Service Desk project will be reused exactly
- Two external systems: Atos tool (linked via manual demand ID), EUROCONTROL engagement system (post-hire)

## Constraints

- **Tech stack**: React 19 + Vite + TypeScript + Tanstack Router (frontend), Python FastAPI (backend), PostgreSQL 16 (database)
- **Design system**: Exact EUROCONTROL design system — Exo font, EC color palette, Shadcn/UI + Tailwind
- **AI provider**: Anthropic Claude API exclusively
- **Deployment**: Docker Compose on single Azure VM (Standard_D4s_v5)
- **File storage**: Azure Blob Storage
- **Desktop only**: no mobile/tablet optimization (min viewport 1280px)
- **Auth**: Username/password only at launch (Entra ID deferred)
- **Audit retention**: 7 years minimum (EU institutional contract requirement)
- **Scale**: 5-20 tenants, hundreds of users, tens of thousands of CVs

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Hybrid multi-tenancy (shared DB + RLS) | Balance isolation with operational simplicity at 5-20 tenant scale | — Pending |
| LLM holistic matching over taxonomy-driven | Free-text skills + Claude reads full JD vs full CV catches contextual matches no code system would | — Pending |
| ESCO as background enrichment only | Users should never be constrained by taxonomy; ESCO powers analytics silently | — Pending |
| Profile catalogue as template, not constraint | Flexibility for customers to customize demands while maintaining audit trail of deviations | — Pending |
| Advisory profile compliance (not blocking) | Demands intentionally modified from profile shouldn't trigger false compliance failures | — Pending |
| EU AI Act compliance from day one | Enforcement Aug 2026; retrofitting is harder than building it in | — Pending |
| Desktop-only target | Internal enterprise tool, all users on office computers | — Pending |
| No placement tracking | EUROCONTROL has a separate system for post-hire engagement | — Pending |

---
*Last updated: 2026-05-28 after initialization*
