# Bryton AI CV App — System Architecture

**Version:** 2.0
**Date:** 2026-05-28
**Status:** Draft
**Change log:** v2.0 adds Profile Catalogue, SFIA, Rate Cards, Security Clearance, ESCO taxonomy, Replacement Workflow, SLA, EU AI Act compliance, Approval Chain, CV Verification, Formatted CV, Audit Export.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AZURE VM (Docker Compose)                   │
│                                                                     │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────────┐    │
│  │   Frontend    │     │   Backend    │     │   PostgreSQL 16  │    │
│  │  (Nginx +    │────▶│  (FastAPI)   │────▶│  (with RLS)      │    │
│  │   React SPA) │     │              │     │                  │    │
│  │  :443/:80    │     │  :8000       │     │  :5432           │    │
│  └──────────────┘     └──────┬───────┘     └──────────────────┘    │
│                              │                                      │
│                     ┌────────┼────────┐                             │
│                     │        │        │                             │
│               ┌─────▼──┐ ┌──▼────┐ ┌─▼───────────┐                │
│               │ Claude  │ │ Azure │ │   SMTP      │                │
│               │  API    │ │ Blob  │ │  (Email)    │                │
│               │(External│ │Storage│ │             │                │
│               └─────────┘ └───────┘ └─────────────┘                │
│                     │                                               │
│               ┌─────▼──┐                                            │
│               │ ESCO   │                                            │
│               │  API   │                                            │
│               │(EC.eu) │                                            │
│               └────────┘                                            │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.1 Component Summary

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | React 19 + Vite + TypeScript + Tanstack Router | SPA served via Nginx |
| Backend | Python FastAPI + SQLAlchemy + Alembic | REST API + WebSocket + SSE |
| Database | PostgreSQL 16 with RLS | Primary datastore, tenant isolation |
| File Storage | Azure Blob Storage | CV documents, exported PDFs, cold audit logs |
| AI | Anthropic Claude API | JD enhancement, CV parsing, matching, assessments |
| Skills Taxonomy | ESCO API (European Commission) | Canonical skills vocabulary |
| Email | SMTP (configurable) | Transactional email notifications |
| Reverse Proxy | Nginx | TLS termination, static file serving, API routing |

---

## 2. Frontend Architecture

### 2.1 Stack

```
React 19 + TypeScript
├── Tanstack Router (type-safe routing)
├── Tanstack Query (server state management)
├── Shadcn/UI + Radix (component library)
├── Tailwind CSS (styling — EUROCONTROL design system)
├── Zustand (client state — auth, UI preferences)
├── React Hook Form + Zod (form validation)
├── Recharts (dashboard charts, SLA gauges, analytics)
├── TipTap (rich text editor for JD enhancement)
└── Vite (build tooling)
```

### 2.2 Directory Structure

```
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── ui/                  # Shadcn components (copied from L1)
│   │   ├── layout/              # Sidebar, Header, PageShell
│   │   ├── demands/             # Demand-specific components
│   │   ├── candidates/          # Candidate-specific components
│   │   ├── matching/            # Match results, score displays, comparison view
│   │   ├── interviews/          # Scheduling, scorecards
│   │   ├── assessments/         # Test builder, test taker
│   │   ├── ai-chat/             # JD enhancement chat panel
│   │   ├── profiles/            # Profile catalogue management
│   │   ├── contracts/           # Contract & rate card management
│   │   ├── clearances/          # Security clearance tracking
│   │   ├── verification/        # CV verification checklists
│   │   ├── sla/                 # SLA dashboards, KPI gauges
│   │   ├── approvals/           # Approval chain UI
│   │   ├── dashboards/          # Role-specific dashboard widgets
│   │   ├── notifications/       # Bell, inbox, preference panel
│   │   ├── formatted-cv/        # CV template preview & generation
│   │   └── admin/               # Tenant management, user management, AI monitoring
│   ├── routes/                  # Tanstack Router route definitions
│   ├── api/                     # API client (Tanstack Query hooks)
│   ├── stores/                  # Zustand stores
│   ├── hooks/                   # Custom React hooks
│   ├── lib/                     # Utilities, cn(), constants
│   ├── types/                   # TypeScript type definitions
│   └── index.css                # EUROCONTROL design tokens
├── tailwind.config.ts
├── components.json
├── vite.config.ts
├── tsconfig.json
└── package.json
```

### 2.3 Routing Structure

```
/                              → Redirect to role-specific dashboard
/login                         → Login page
/register                      → Candidate self-registration

# Admin routes
/admin/dashboard               → System-wide dashboard + AI monitoring
/admin/tenants                 → Tenant list + CRUD
/admin/tenants/:id             → Tenant detail + settings
/admin/tenants/:id/contracts   → Contract management
/admin/users                   → User management (all roles)
/admin/audit-log               → System audit log viewer
/admin/audit-export            → Bulk audit export tool
/admin/ai-monitoring           → AI system health, override rates, costs
/admin/esco                    → ESCO taxonomy browser & sync status

# Internal routes (SM + Recruiter)
/contracts                     → Contract list (filtered by tenant)
/contracts/:id                 → Contract detail with rate card
/contracts/:id/rate-card       → Rate card management
/contracts/:id/profiles        → Profile catalogue for this contract
/contracts/:id/sla             → SLA configuration

/profiles                      → Profile catalogue browser
/profiles/:id                  → Profile detail with requirements

/demands                       → Demand list (filtered by tenant)
/demands/new                   → Create demand (profile selection + AI chat)
/demands/:id                   → Demand detail (lifecycle, matches, interviews)
/demands/:id/enhance           → JD enhancement (chat + editor)
/demands/:id/matches           → Match results with explanations
/demands/:id/shortlist         → Shortlist management with compliance status
/demands/:id/interviews        → Interview list
/demands/:id/interviews/:iid   → Interview detail + scorecard
/demands/:id/assessments       → Assessment management
/demands/:id/verification      → CV verification checklists for shortlisted candidates

/candidates                    → Candidate pool (tenant-visibility scoped)
/candidates/:id                → Candidate profile detail
/candidates/:id/formatted-cv   → Generate formatted CV for a demand
/candidates/:id/clearances     → Security clearance management
/candidates/:id/verification   → Verification status overview

/assessments/builder           → Test template builder
/assessments/bank              → Question bank management

/approvals                     → Pending approval requests
/sla                           → SLA dashboard (SM view)
/dashboard                     → SM or Recruiter dashboard

# Customer routes
/customer/dashboard            → Customer dashboard with SLA gauges
/customer/demands              → Customer's demands
/customer/demands/new          → Raise a new demand (profile selection)
/customer/demands/:id          → Demand detail (customer view)
/customer/demands/:id/enhance  → JD enhancement (chat + editor)
/customer/sla                  → SLA performance dashboard
/customer/survey/:id           → Quality survey form

# Candidate routes
/candidate/dashboard           → Candidate dashboard
/candidate/profile             → Edit profile / upload CV
/candidate/clearances          → Manage security clearances
/candidate/languages           → Manage language proficiencies
/candidate/matches             → Matched demands
/candidate/assessments         → Assigned assessments
/candidate/assessments/:id     → Take assessment
/candidate/interviews          → Upcoming interviews
/candidate/applications        → Application tracker

# Shared
/settings                      → User settings + notification preferences
/notifications                 → Notification inbox
```

### 2.4 Real-Time Connections

- **WebSocket** (`/ws/notifications`): persistent connection for live notification delivery
- **SSE** (`/api/ai/chat/stream`): server-sent events for streaming AI chat responses
- Tanstack Query handles cache invalidation on WebSocket events (e.g., new approval request, SLA status change)

### 2.5 Auth Flow (Frontend)

1. User submits credentials to `/api/auth/login`
2. Backend returns `{ access_token, refresh_token, user }` with role, tenant, and permissions
3. Access token stored in memory (Zustand), refresh token in httpOnly cookie
4. Tanstack Query `queryClient` attaches access token to all API requests
5. Token refresh interceptor handles 401 responses transparently
6. Route guards check role before rendering protected routes

---

## 3. Backend Architecture

### 3.1 Stack

```
Python 3.12 + FastAPI
├── SQLAlchemy 2.0 (async ORM)
├── Alembic (database migrations)
├── Pydantic v2 (request/response schemas)
├── python-jose (JWT handling)
├── passlib[bcrypt] (password hashing)
├── anthropic (Claude API SDK)
├── python-multipart (file uploads)
├── azure-storage-blob (Azure Blob SDK)
├── aiosmtplib (async email)
├── pdfplumber (PDF text extraction)
├── python-docx (DOCX text extraction)
├── uvicorn (ASGI server)
└── websockets (WS support via FastAPI)
```

### 3.2 Directory Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app factory
│   ├── config.py                # Settings (pydantic-settings, env-based)
│   ├── deps.py                  # Dependency injection (DB session, current user, tenant)
│   │
│   ├── auth/
│   │   ├── router.py            # /api/auth/* endpoints
│   │   ├── service.py           # Login, register, token refresh
│   │   ├── jwt.py               # Token creation/verification
│   │   └── password.py          # Hashing utilities
│   │
│   ├── tenants/
│   │   ├── router.py            # /api/tenants/* endpoints
│   │   ├── service.py           # Tenant CRUD, provisioning
│   │   ├── models.py            # SQLAlchemy models
│   │   └── schemas.py           # Pydantic schemas
│   │
│   ├── contracts/
│   │   ├── router.py            # /api/contracts/* endpoints
│   │   ├── service.py           # Contract CRUD, rate card management
│   │   ├── models.py            # Contract, RateCard, RateCardEntry
│   │   └── schemas.py
│   │
│   ├── profiles/
│   │   ├── router.py            # /api/profiles/* endpoints
│   │   ├── service.py           # Profile catalogue CRUD, compliance checking
│   │   ├── compliance.py        # Profile-to-CV compliance checker
│   │   ├── models.py            # ProfileCatalogue, ProfileRequirement
│   │   └── schemas.py
│   │
│   ├── users/
│   │   ├── router.py            # /api/users/* endpoints
│   │   ├── service.py           # User CRUD, role management
│   │   ├── models.py
│   │   └── schemas.py
│   │
│   ├── demands/
│   │   ├── router.py            # /api/demands/* endpoints
│   │   ├── service.py           # Demand CRUD, lifecycle transitions
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── numbering.py         # Tenant-prefixed demand number generation
│   │   └── replacement.py       # Replacement demand creation logic
│   │
│   ├── candidates/
│   │   ├── router.py            # /api/candidates/* endpoints
│   │   ├── service.py           # Profile CRUD, CV management
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── parser.py            # CV parsing via Claude API + ESCO mapping
│   │   ├── clearances.py        # Security clearance management
│   │   ├── languages.py         # CEFR language proficiency management
│   │   └── formatted_cv.py      # Formatted CV generation (PDF/DOCX)
│   │
│   ├── matching/
│   │   ├── router.py            # /api/demands/:id/match endpoints
│   │   ├── service.py           # Matching orchestration
│   │   ├── scorer.py            # Multi-dimensional scoring engine
│   │   ├── explainer.py         # AI narrative explanation generator
│   │   ├── filters.py           # Hard filters (clearance, language, profile compliance)
│   │   ├── models.py            # Match results, shortlists, rejection records
│   │   └── schemas.py
│   │
│   ├── interviews/
│   │   ├── router.py            # /api/interviews/* endpoints
│   │   ├── service.py           # Scheduling, scorecard management
│   │   ├── generator.py         # AI question generation
│   │   ├── models.py
│   │   └── schemas.py
│   │
│   ├── assessments/
│   │   ├── router.py            # /api/assessments/* endpoints
│   │   ├── service.py           # Test builder, assignment, submission
│   │   ├── scorer.py            # AI scoring engine
│   │   ├── models.py
│   │   └── schemas.py
│   │
│   ├── ai/
│   │   ├── router.py            # /api/ai/chat/* endpoints (SSE)
│   │   ├── service.py           # Chat session management
│   │   ├── jd_enhancer.py       # JD enhancement logic + prompts
│   │   ├── inline_suggester.py  # Inline editor suggestions + bias detection
│   │   ├── decision_log.py      # EU AI Act decision logging
│   │   ├── monitoring.py        # AI performance monitoring + override tracking
│   │   ├── models.py            # Chat sessions, messages, JD versions, AI decision logs
│   │   └── prompts/
│   │       ├── cv_parsing.py           # CV extraction + ESCO mapping
│   │       ├── jd_enhancement.py       # Chat mode system prompt
│   │       ├── jd_inline.py            # Inline suggestions + bias detection
│   │       ├── matching.py             # Scoring + explanation
│   │       ├── sfia_assessment.py      # SFIA level inference
│   │       ├── interview_questions.py  # Question generation
│   │       ├── assessment_generate.py  # Test question generation
│   │       └── assessment_scoring.py   # Answer evaluation
│   │
│   ├── verification/
│   │   ├── router.py            # /api/verification/* endpoints
│   │   ├── service.py           # Verification checklist management
│   │   ├── models.py            # VerificationChecklist, VerificationItem
│   │   └── schemas.py
│   │
│   ├── approvals/
│   │   ├── router.py            # /api/approvals/* endpoints
│   │   ├── service.py           # Approval request lifecycle
│   │   ├── models.py            # ApprovalRequest
│   │   └── schemas.py
│   │
│   ├── sla/
│   │   ├── router.py            # /api/sla/* endpoints
│   │   ├── service.py           # SLA calculation, breach detection
│   │   ├── calculator.py        # KPI calculation engine
│   │   ├── models.py            # SLAConfig, SLAMetricSnapshot
│   │   └── schemas.py
│   │
│   ├── esco/
│   │   ├── router.py            # /api/esco/* endpoints (search, browse)
│   │   ├── service.py           # ESCO taxonomy operations
│   │   ├── sync.py              # ESCO API sync job
│   │   ├── models.py            # EscoSkill
│   │   └── schemas.py
│   │
│   ├── notifications/
│   │   ├── router.py            # /api/notifications/* endpoints
│   │   ├── service.py           # Create, mark read, preferences
│   │   ├── websocket.py         # WebSocket connection manager
│   │   ├── email.py             # Email sending
│   │   ├── models.py
│   │   └── schemas.py
│   │
│   ├── dashboards/
│   │   ├── router.py            # /api/dashboards/* endpoints
│   │   └── service.py           # Aggregation queries per role
│   │
│   ├── audit/
│   │   ├── router.py            # /api/audit/* endpoints (admin only)
│   │   ├── service.py           # Log retrieval, filtering, cold storage query
│   │   ├── middleware.py        # Auto-logging middleware for critical actions
│   │   ├── export.py            # Bulk audit export (ZIP generation)
│   │   ├── cold_storage.py      # Tier audit logs to Azure Blob after 12 months
│   │   └── models.py
│   │
│   ├── exports/
│   │   ├── router.py            # /api/exports/* endpoints
│   │   └── service.py           # CSV/PDF generation
│   │
│   └── db/
│       ├── base.py              # SQLAlchemy base, engine, session factory
│       ├── rls.py               # RLS policy setup and session tenant binding
│       └── migrations/          # Alembic migration scripts
│           ├── env.py
│           └── versions/
│
├── tests/
│   ├── conftest.py
│   ├── test_auth/
│   ├── test_demands/
│   ├── test_matching/
│   ├── test_profiles/
│   ├── test_sla/
│   └── ...
│
├── alembic.ini
├── pyproject.toml
├── Dockerfile
└── .env.example
```

### 3.3 API Design

RESTful API with consistent conventions:

```
Base URL: /api/v1

# Auth
POST   /auth/login
POST   /auth/register
POST   /auth/refresh
POST   /auth/logout
POST   /auth/password-reset
POST   /auth/password-reset/confirm

# Tenants (Admin only)
GET    /tenants
POST   /tenants
GET    /tenants/:id
PATCH  /tenants/:id
DELETE /tenants/:id

# Contracts (Admin, SM)
GET    /contracts                        → List contracts (tenant-scoped)
POST   /contracts                        → Create contract
GET    /contracts/:id                    → Contract detail
PATCH  /contracts/:id                    → Update contract
GET    /contracts/:id/rate-card          → Get rate card entries
POST   /contracts/:id/rate-card          → Add rate card entry
PATCH  /contracts/:id/rate-card/:rid     → Update rate card entry
DELETE /contracts/:id/rate-card/:rid     → Remove rate card entry

# Profile Catalogue (Admin, SM)
GET    /profiles                         → List profiles (tenant-scoped or global)
POST   /profiles                         → Create profile
GET    /profiles/:id                     → Profile detail with requirements
PATCH  /profiles/:id                     → Update profile
DELETE /profiles/:id                     → Deactivate profile
POST   /profiles/:id/compliance-check    → Run compliance check for a candidate

# SFIA (reference data)
GET    /sfia/levels                      → List all SFIA levels

# ESCO (reference data)
GET    /esco/skills                      → Search ESCO skills (autocomplete)
GET    /esco/skills/:code                → Skill detail with hierarchy
POST   /esco/sync                        → Trigger ESCO data refresh (Admin)

# Users
GET    /users
POST   /users
GET    /users/:id
PATCH  /users/:id
DELETE /users/:id

# Demands
GET    /demands                          → List demands (tenant-scoped)
POST   /demands                          → Create demand (with profile link)
GET    /demands/:id                      → Demand detail
PATCH  /demands/:id                      → Update demand
POST   /demands/:id/transition           → Lifecycle state transition
POST   /demands/:id/match               → Trigger matching (manual)
GET    /demands/:id/matches              → Get match results with explanations
GET    /demands/:id/shortlist            → Get shortlist
PATCH  /demands/:id/shortlist            → Update shortlist (add/remove candidates)
GET    /demands/:id/versions             → JD version history
GET    /demands/:id/compliance           → Profile compliance summary for shortlisted candidates
POST   /demands/:id/replacement          → Create replacement demand from this demand
GET    /demands/:id/rejections           → Rejection records with structured reasons

# Candidates
GET    /candidates                       → List candidates (visibility-scoped)
GET    /candidates/:id                   → Candidate profile
PATCH  /candidates/:id                   → Update profile
POST   /candidates/:id/cv               → Upload CV (triggers parsing)
GET    /candidates/:id/cv               → Download current CV
GET    /candidates/:id/cv/formatted     → Generate formatted CV (with demand context)
GET    /candidates/:id/matches           → Demands matched to this candidate
DELETE /candidates/:id                   → GDPR deletion request

# Candidate — Security Clearances
GET    /candidates/:id/clearances        → List clearances
POST   /candidates/:id/clearances        → Add clearance
PATCH  /candidates/:id/clearances/:cid   → Update clearance
DELETE /candidates/:id/clearances/:cid   → Remove clearance

# Candidate — Language Proficiencies
GET    /candidates/:id/languages         → List language proficiencies
POST   /candidates/:id/languages         → Add language proficiency
PATCH  /candidates/:id/languages/:lid    → Update proficiency
DELETE /candidates/:id/languages/:lid    → Remove proficiency

# AI Chat (JD Enhancement)
POST   /ai/chat/sessions                → Create new chat session for a demand
GET    /ai/chat/sessions/:sid           → Get chat session with history
POST   /ai/chat/sessions/:sid/messages  → Send message (SSE response)
POST   /ai/chat/sessions/:sid/accept    → Accept current JD version
GET    /ai/inline-suggest               → Get inline suggestions for JD text

# CV Verification
GET    /verification/demands/:did        → Verification checklists for a demand
GET    /verification/candidates/:cid     → Verification status for a candidate
POST   /verification/items               → Create verification item
PATCH  /verification/items/:id           → Update verification item (mark verified/failed)
POST   /verification/items/:id/evidence  → Upload evidence document

# Approvals
GET    /approvals                        → List pending approvals (for current user)
GET    /approvals/:id                    → Approval request detail
POST   /approvals/:id/approve            → Approve request
POST   /approvals/:id/reject             → Reject request (reason required)
POST   /approvals/:id/request-changes    → Request changes

# SLA
GET    /sla/config                       → SLA configuration for current tenant
PATCH  /sla/config                       → Update SLA configuration
GET    /sla/dashboard                    → SLA metrics dashboard data
GET    /sla/dashboard/export             → Export SLA report as PDF
GET    /sla/demands/:id                  → SLA metrics for a specific demand

# Interviews
GET    /interviews
POST   /interviews
GET    /interviews/:id
PATCH  /interviews/:id
POST   /interviews/:id/generate-questions
GET    /interviews/:id/scorecard
POST   /interviews/:id/scorecard

# Assessments
GET    /assessments/templates
POST   /assessments/templates
GET    /assessments/templates/:id
PATCH  /assessments/templates/:id
POST   /assessments/templates/:id/ai-suggest
POST   /assessments/assign
GET    /assessments/:id
POST   /assessments/:id/start
POST   /assessments/:id/submit
GET    /assessments/:id/results

# Question Bank
GET    /questions
POST   /questions
PATCH  /questions/:id
DELETE /questions/:id

# Quality Surveys
GET    /surveys                          → List surveys for current user
POST   /surveys/:id/submit              → Submit quality survey response
GET    /surveys/analytics                → Survey results analytics

# Notifications
GET    /notifications
PATCH  /notifications/:id/read
PATCH  /notifications/read-all
GET    /notifications/preferences
PATCH  /notifications/preferences
WS     /ws/notifications

# Dashboards
GET    /dashboards/admin
GET    /dashboards/sm
GET    /dashboards/recruiter
GET    /dashboards/customer
GET    /dashboards/candidate

# Exports
GET    /exports/demands
GET    /exports/candidates
GET    /exports/demand/:id/pdf
GET    /exports/candidate/:id/pdf
GET    /exports/candidate/:id/formatted-cv/:did
GET    /exports/scorecard/:id/pdf
GET    /exports/sla-report/:contract_id

# Audit (Admin only)
GET    /audit/logs                       → Query audit logs (filterable, hot + cold)
POST   /audit/export                     → Trigger bulk audit export (async, returns job ID)
GET    /audit/export/:job_id             → Check export status / download

# AI Monitoring (Admin only)
GET    /ai/monitoring/overview           → AI system health dashboard data
GET    /ai/monitoring/decisions           → Query AI decision logs
GET    /ai/monitoring/costs              → Cost breakdown by feature/tenant
GET    /ai/monitoring/overrides          → Human override rate trends
```

### 3.4 Dependency Injection

FastAPI dependency chain for every request:

```python
# 1. Extract and verify JWT
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User

# 2. Extract tenant context from user
async def get_current_tenant(user: User = Depends(get_current_user)) -> Tenant | None

# 3. Bind tenant to DB session (sets RLS context)
async def get_db(tenant: Tenant | None = Depends(get_current_tenant)) -> AsyncSession
    # Executes: SET app.current_tenant = '{tenant_id}'
    # RLS policies filter all queries automatically

# 4. Role-based permission check
def require_role(*roles: Role) -> Depends
    # Returns 403 if current user's role not in allowed roles

# 5. Approval check (for gated actions)
async def check_approval(action: str, entity_id: UUID) -> ApprovalStatus
    # Returns APPROVED, PENDING, or NOT_REQUIRED
```

### 3.5 Error Handling

Consistent error response format:

```json
{
  "error": {
    "code": "RATE_EXCEEDS_CEILING",
    "message": "Candidate rate (€850/day) exceeds rate card ceiling (€800/day) for profile SC-DEV-03 at SFIA 5",
    "details": {
      "candidate_rate": 850,
      "ceiling_rate": 800,
      "profile_code": "SC-DEV-03",
      "sfia_level": 5,
      "action": "Request SM override via approval chain"
    }
  }
}
```

HTTP status codes: 400 (validation), 401 (unauthenticated), 403 (unauthorized), 404 (not found), 409 (conflict/approval required), 422 (unprocessable), 429 (rate limited), 500 (internal).

---

## 4. Database Architecture

### 4.1 Multi-Tenancy with RLS

```sql
ALTER TABLE demands ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON demands
  USING (tenant_id = current_setting('app.current_tenant')::uuid);

SET app.current_tenant = 'tenant-uuid-here';
```

Every tenant-scoped table follows this pattern.

### 4.2 Entity-Relationship Overview

```
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  Tenant   │──1:N│ Contract │──1:N│  Profile     │──1:N│  Profile     │
│           │     │          │     │  Catalogue   │     │  Requirement │
└─────┬─────┘     └────┬─────┘     └──────────────┘     └──────────────┘
      │                │
      │ 1:N            │ 1:1
      ▼                ▼
┌──────────┐     ┌──────────┐
│  Demand   │────▶│ Rate Card│
│           │     │ (ceiling)│
└─────┬─────┘     └──────────┘
      │
      │ 1:N
      ▼
┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│  Match       │     │  Interview   │     │ Assessment  │
│  Result      │     │              │     │ Assignment  │
└──────┬───────┘     └──────┬───────┘     └──────┬──────┘
       │                    │                     │
       ▼                    ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Shortlist   │     │  Scorecard   │     │ Submission   │
│  Entry       │     │              │     │ + AI Score   │
└──────────────┘     └──────────────┘     └──────────────┘

GLOBAL ENTITIES:
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Candidate   │──1:N│  Security    │     │  Language    │
│  (Global)    │     │  Clearance   │     │  Proficiency │
└──────┬───────┘     └──────────────┘     └──────────────┘
       │ 1:N
       ▼
┌──────────────┐     ┌──────────────┐
│  CV File     │     │  ESCO Skill  │  (reference)
└──────────────┘     └──────────────┘
```

### 4.3 Core Tables

#### tenants
```sql
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    prefix          VARCHAR(6) NOT NULL UNIQUE,
    settings        JSONB DEFAULT '{}',
    approval_config JSONB DEFAULT '{}',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### contracts
```sql
CREATE TABLE contracts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    reference       VARCHAR(100) NOT NULL,
    title           VARCHAR(255) NOT NULL,
    lot_number      VARCHAR(50),
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    max_value       DECIMAL(15,2),
    currency        VARCHAR(3) DEFAULT 'EUR',
    status          VARCHAR(20) DEFAULT 'active',
    sla_config_id   UUID REFERENCES sla_configs(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### rate_cards
```sql
CREATE TABLE rate_cards (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id     UUID NOT NULL REFERENCES contracts(id),
    profile_id      UUID NOT NULL REFERENCES profile_catalogue(id),
    sfia_level      INTEGER NOT NULL CHECK (sfia_level BETWEEN 1 AND 7),
    max_daily_rate  DECIMAL(10,2) NOT NULL,
    currency        VARCHAR(3) DEFAULT 'EUR',
    effective_from  DATE NOT NULL,
    effective_to    DATE NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(contract_id, profile_id, sfia_level, effective_from)
);
```

#### sfia_levels (reference data)
```sql
CREATE TABLE sfia_levels (
    level           INTEGER PRIMARY KEY CHECK (level BETWEEN 1 AND 7),
    label           VARCHAR(50) NOT NULL,
    description     TEXT NOT NULL,
    responsibility  TEXT NOT NULL
);
```

#### profile_catalogue
```sql
CREATE TABLE profile_catalogue (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID REFERENCES tenants(id),
    contract_id     UUID REFERENCES contracts(id),
    code            VARCHAR(20) NOT NULL,
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    sfia_level_min  INTEGER NOT NULL REFERENCES sfia_levels(level),
    sfia_level_max  INTEGER NOT NULL REFERENCES sfia_levels(level),
    min_years_exp   INTEGER NOT NULL DEFAULT 0,
    min_education   VARCHAR(50),
    required_clearance VARCHAR(20),
    is_active       BOOLEAN DEFAULT TRUE,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(contract_id, code)
);
```

#### profile_requirements
```sql
CREATE TABLE profile_requirements (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id      UUID NOT NULL REFERENCES profile_catalogue(id),
    req_type        VARCHAR(20) NOT NULL,
    esco_code       VARCHAR(50),
    description     VARCHAR(255) NOT NULL,
    is_mandatory    BOOLEAN DEFAULT TRUE,
    min_cefr_level  VARCHAR(2),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### esco_skills (reference data)
```sql
CREATE TABLE esco_skills (
    code            VARCHAR(50) PRIMARY KEY,
    preferred_label VARCHAR(255) NOT NULL,
    alt_labels      JSONB DEFAULT '[]',
    description     TEXT,
    parent_code     VARCHAR(50) REFERENCES esco_skills(code),
    skill_type      VARCHAR(20),
    last_synced     TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_esco_skills_label ON esco_skills USING gin(to_tsvector('english', preferred_label));
```

#### users
```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL,
    tenant_id       UUID REFERENCES tenants(id),
    is_active       BOOLEAN DEFAULT TRUE,
    last_login      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### user_tenant_assignments
```sql
CREATE TABLE user_tenant_assignments (
    user_id         UUID REFERENCES users(id),
    tenant_id       UUID REFERENCES tenants(id),
    PRIMARY KEY (user_id, tenant_id)
);
```

#### candidates
```sql
CREATE TABLE candidates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    full_name       VARCHAR(255) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    phone           VARCHAR(50),
    location        VARCHAR(255),
    availability    DATE,
    remote_pref     VARCHAR(20),
    rate_expectation DECIMAL(10,2),
    rate_currency   VARCHAR(3) DEFAULT 'EUR',
    sfia_level      INTEGER REFERENCES sfia_levels(level),
    sfia_level_source VARCHAR(20) DEFAULT 'ai_inferred',
    parsed_data     JSONB,
    parsed_skills_esco JSONB DEFAULT '[]',
    profile_complete DECIMAL(3,0) DEFAULT 0,
    visibility      JSONB DEFAULT '[]',
    verification_status VARCHAR(20) DEFAULT 'unverified',
    consent_given   BOOLEAN DEFAULT FALSE,
    consent_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### candidate_languages
```sql
CREATE TABLE candidate_languages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID NOT NULL REFERENCES candidates(id),
    language        VARCHAR(10) NOT NULL,
    cefr_level      VARCHAR(10) NOT NULL,
    source          VARCHAR(20) DEFAULT 'self_declared',
    test_name       VARCHAR(100),
    test_date       DATE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(candidate_id, language)
);
```

#### security_clearances
```sql
CREATE TABLE security_clearances (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID NOT NULL REFERENCES candidates(id),
    level           VARCHAR(20) NOT NULL,
    clearance_type  VARCHAR(20) NOT NULL,
    issuing_authority VARCHAR(10) NOT NULL,
    reference_number VARCHAR(100),
    issue_date      DATE,
    expiry_date     DATE,
    status          VARCHAR(20) NOT NULL DEFAULT 'self_declared',
    application_status VARCHAR(30),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### cv_files
```sql
CREATE TABLE cv_files (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID REFERENCES candidates(id),
    file_name       VARCHAR(255) NOT NULL,
    file_type       VARCHAR(10) NOT NULL,
    blob_path       VARCHAR(512) NOT NULL,
    file_size       INTEGER NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    is_current      BOOLEAN DEFAULT TRUE,
    parsed_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### demands
```sql
CREATE TABLE demands (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    contract_id     UUID REFERENCES contracts(id),
    profile_id      UUID REFERENCES profile_catalogue(id),
    demand_number   VARCHAR(20) NOT NULL UNIQUE,
    external_id     VARCHAR(255),
    title           VARCHAR(255) NOT NULL,
    description     TEXT NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'draft',
    demand_type     VARCHAR(20) DEFAULT 'standard',
    replaces_demand_id UUID REFERENCES demands(id),
    location        VARCHAR(255),
    employment_type VARCHAR(20),
    sfia_level_min  INTEGER REFERENCES sfia_levels(level),
    sfia_level_max  INTEGER REFERENCES sfia_levels(level),
    required_skills JSONB DEFAULT '[]',
    preferred_skills JSONB DEFAULT '[]',
    rate_min        DECIMAL(10,2),
    rate_max        DECIMAL(10,2),
    rate_currency   VARCHAR(3) DEFAULT 'EUR',
    remote_policy   VARCHAR(20),
    positions       INTEGER DEFAULT 1,
    start_date      DATE,
    department      VARCHAR(255),
    match_weights   JSONB,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### demand_sequences
```sql
CREATE TABLE demand_sequences (
    tenant_id       UUID PRIMARY KEY REFERENCES tenants(id),
    last_sequence   INTEGER NOT NULL DEFAULT 0
);
```

#### demand_transitions
```sql
CREATE TABLE demand_transitions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demand_id       UUID NOT NULL REFERENCES demands(id),
    from_status     VARCHAR(20),
    to_status       VARCHAR(20) NOT NULL,
    transitioned_by UUID REFERENCES users(id),
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### jd_versions
```sql
CREATE TABLE jd_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demand_id       UUID NOT NULL REFERENCES demands(id),
    version         INTEGER NOT NULL,
    content         TEXT NOT NULL,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### chat_sessions / chat_messages
```sql
CREATE TABLE chat_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demand_id       UUID NOT NULL REFERENCES demands(id),
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE chat_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID NOT NULL REFERENCES chat_sessions(id),
    role            VARCHAR(10) NOT NULL,
    content         TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### match_results
```sql
CREATE TABLE match_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demand_id       UUID NOT NULL REFERENCES demands(id),
    candidate_id    UUID NOT NULL REFERENCES candidates(id),
    composite_score DECIMAL(5,2) NOT NULL,
    dimension_scores JSONB NOT NULL,
    explanation     TEXT,
    profile_compliance JSONB,
    run_at          TIMESTAMPTZ DEFAULT NOW(),
    run_id          UUID NOT NULL
);
```

#### shortlist_entries
```sql
CREATE TABLE shortlist_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demand_id       UUID NOT NULL REFERENCES demands(id),
    candidate_id    UUID NOT NULL REFERENCES candidates(id),
    match_result_id UUID REFERENCES match_results(id),
    status          VARCHAR(20) DEFAULT 'proposed',
    added_by        VARCHAR(10) DEFAULT 'auto',
    reviewed_by     UUID REFERENCES users(id),
    rejection_reason VARCHAR(50),
    rejection_notes TEXT,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(demand_id, candidate_id)
);
```

#### verification_checklists
```sql
CREATE TABLE verification_checklists (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demand_id       UUID NOT NULL REFERENCES demands(id),
    candidate_id    UUID NOT NULL REFERENCES candidates(id),
    overall_status  VARCHAR(20) DEFAULT 'pending',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(demand_id, candidate_id)
);
```

#### verification_items
```sql
CREATE TABLE verification_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    checklist_id    UUID NOT NULL REFERENCES verification_checklists(id),
    item_type       VARCHAR(30) NOT NULL,
    description     VARCHAR(512) NOT NULL,
    status          VARCHAR(20) DEFAULT 'pending',
    evidence_blob   VARCHAR(512),
    verified_by     UUID REFERENCES users(id),
    verified_at     TIMESTAMPTZ,
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### approval_requests
```sql
CREATE TABLE approval_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    action_type     VARCHAR(50) NOT NULL,
    entity_type     VARCHAR(50) NOT NULL,
    entity_id       UUID NOT NULL,
    requested_by    UUID NOT NULL REFERENCES users(id),
    justification   TEXT NOT NULL,
    context_data    JSONB,
    status          VARCHAR(20) DEFAULT 'pending',
    decided_by      UUID REFERENCES users(id),
    decision_reason TEXT,
    decided_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### sla_configs
```sql
CREATE TABLE sla_configs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    contract_id     UUID REFERENCES contracts(id),
    time_to_fill_days INTEGER DEFAULT 15,
    replacement_time_days INTEGER DEFAULT 10,
    cv_to_interview_ratio DECIMAL(3,1) DEFAULT 3.0,
    fill_rate_target DECIMAL(5,2) DEFAULT 90.00,
    quality_score_target DECIMAL(3,1) DEFAULT 4.0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### sla_metric_snapshots
```sql
CREATE TABLE sla_metric_snapshots (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    contract_id     UUID REFERENCES contracts(id),
    period_start    DATE NOT NULL,
    period_end      DATE NOT NULL,
    time_to_fill_avg DECIMAL(5,1),
    replacement_time_avg DECIMAL(5,1),
    cv_to_interview_ratio DECIMAL(5,2),
    fill_rate       DECIMAL(5,2),
    quality_score_avg DECIMAL(3,1),
    demands_opened  INTEGER,
    demands_filled  INTEGER,
    snapshot_at     TIMESTAMPTZ DEFAULT NOW()
);
```

#### quality_surveys
```sql
CREATE TABLE quality_surveys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demand_id       UUID NOT NULL REFERENCES demands(id),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    respondent_id   UUID REFERENCES users(id),
    timeliness      INTEGER CHECK (timeliness BETWEEN 1 AND 5),
    candidate_quality INTEGER CHECK (candidate_quality BETWEEN 1 AND 5),
    communication   INTEGER CHECK (communication BETWEEN 1 AND 5),
    overall         INTEGER CHECK (overall BETWEEN 1 AND 5),
    comments        TEXT,
    submitted_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### ai_decision_logs
```sql
CREATE TABLE ai_decision_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature         VARCHAR(50) NOT NULL,
    model_id        VARCHAR(100) NOT NULL,
    prompt_version  VARCHAR(64) NOT NULL,
    input_summary   JSONB NOT NULL,
    output_summary  JSONB NOT NULL,
    confidence      DECIMAL(3,2),
    tokens_in       INTEGER,
    tokens_out      INTEGER,
    latency_ms      INTEGER,
    cost_estimate   DECIMAL(8,4),
    human_action    VARCHAR(20),
    user_id         UUID REFERENCES users(id),
    tenant_id       UUID REFERENCES tenants(id),
    entity_type     VARCHAR(50),
    entity_id       UUID,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_ai_decision_logs_feature ON ai_decision_logs(feature, created_at DESC);
CREATE INDEX idx_ai_decision_logs_tenant ON ai_decision_logs(tenant_id, created_at DESC);
```

#### interviews
```sql
CREATE TABLE interviews (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demand_id       UUID NOT NULL REFERENCES demands(id),
    candidate_id    UUID NOT NULL REFERENCES candidates(id),
    scheduled_at    TIMESTAMPTZ NOT NULL,
    duration_min    INTEGER DEFAULT 60,
    location        VARCHAR(512),
    interview_type  VARCHAR(20),
    status          VARCHAR(20) DEFAULT 'scheduled',
    questions       JSONB,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### interview_interviewers
```sql
CREATE TABLE interview_interviewers (
    interview_id    UUID REFERENCES interviews(id),
    user_id         UUID REFERENCES users(id),
    PRIMARY KEY (interview_id, user_id)
);
```

#### scorecards
```sql
CREATE TABLE scorecards (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_id    UUID NOT NULL REFERENCES interviews(id),
    interviewer_id  UUID NOT NULL REFERENCES users(id),
    criteria        JSONB NOT NULL,
    overall_score   DECIMAL(3,1),
    recommendation  VARCHAR(20),
    notes           TEXT,
    submitted_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(interview_id, interviewer_id)
);
```

#### assessment_templates
```sql
CREATE TABLE assessment_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID REFERENCES tenants(id),
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    time_limit_min  INTEGER,
    passing_score   DECIMAL(5,2),
    randomize       BOOLEAN DEFAULT FALSE,
    show_results    BOOLEAN DEFAULT FALSE,
    allow_retake    BOOLEAN DEFAULT FALSE,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### assessment_questions
```sql
CREATE TABLE assessment_questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id     UUID REFERENCES assessment_templates(id),
    question_bank_id UUID REFERENCES question_bank(id),
    question_type   VARCHAR(20) NOT NULL,
    content         TEXT NOT NULL,
    options         JSONB,
    scoring_rubric  TEXT,
    points          DECIMAL(5,2) DEFAULT 1,
    sort_order      INTEGER NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### question_bank
```sql
CREATE TABLE question_bank (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID REFERENCES tenants(id),
    question_type   VARCHAR(20) NOT NULL,
    content         TEXT NOT NULL,
    options         JSONB,
    scoring_rubric  TEXT,
    tags            JSONB DEFAULT '[]',
    difficulty      VARCHAR(10),
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### assessment_assignments
```sql
CREATE TABLE assessment_assignments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id     UUID NOT NULL REFERENCES assessment_templates(id),
    demand_id       UUID NOT NULL REFERENCES demands(id),
    candidate_id    UUID NOT NULL REFERENCES candidates(id),
    status          VARCHAR(20) DEFAULT 'assigned',
    started_at      TIMESTAMPTZ,
    submitted_at    TIMESTAMPTZ,
    time_spent_sec  INTEGER,
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(template_id, demand_id, candidate_id)
);
```

#### assessment_answers
```sql
CREATE TABLE assessment_answers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id   UUID NOT NULL REFERENCES assessment_assignments(id),
    question_id     UUID NOT NULL REFERENCES assessment_questions(id),
    answer          JSONB NOT NULL,
    ai_score        DECIMAL(5,2),
    ai_reasoning    TEXT,
    ai_confidence   DECIMAL(3,2),
    human_score     DECIMAL(5,2),
    scored_by       UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### notifications
```sql
CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id),
    tenant_id       UUID REFERENCES tenants(id),
    event_type      VARCHAR(50) NOT NULL,
    title           VARCHAR(255) NOT NULL,
    body            TEXT,
    entity_type     VARCHAR(50),
    entity_id       UUID,
    is_read         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

#### notification_preferences
```sql
CREATE TABLE notification_preferences (
    user_id         UUID NOT NULL REFERENCES users(id),
    event_type      VARCHAR(50) NOT NULL,
    in_app          BOOLEAN DEFAULT TRUE,
    email           BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (user_id, event_type)
);
```

#### audit_logs
```sql
CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id),
    tenant_id       UUID REFERENCES tenants(id),
    action          VARCHAR(50) NOT NULL,
    entity_type     VARCHAR(50),
    entity_id       UUID,
    details         JSONB,
    ip_address      INET,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_logs_tenant ON audit_logs(tenant_id, created_at DESC);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at DESC);
-- Partition by month for efficient cold-storage tiering
```

#### formatted_cv_outputs
```sql
CREATE TABLE formatted_cv_outputs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id    UUID NOT NULL REFERENCES candidates(id),
    demand_id       UUID REFERENCES demands(id),
    template_version VARCHAR(20) NOT NULL,
    blob_path       VARCHAR(512) NOT NULL,
    generated_by    UUID REFERENCES users(id),
    generated_at    TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 5. AI Integration Architecture

### 5.1 Claude API Usage

| Feature | Model | Input | Output | Latency |
|---------|-------|-------|--------|---------|
| CV Parsing + ESCO mapping | Sonnet | Raw CV text | Structured JSON with ESCO codes | 5-15s |
| SFIA Level Inference | Sonnet | Parsed CV summary | SFIA level + justification | 2-5s |
| JD Enhancement Chat | Sonnet | Conversation + JD + profile | Streaming text | 1-3s first token |
| JD Bias Detection | Haiku | JD paragraph | Flagged issues | <2s |
| Inline JD Suggestions | Haiku | JD paragraph | Suggestion list | <2s |
| CV-Demand Matching | Sonnet | JD + parsed CV (batched) | Score + dimensions + explanation | 3-8s per candidate |
| Profile Compliance Check | Haiku | Profile reqs + parsed CV | Checklist (met/unmet per req) | 2-4s |
| Interview Questions | Sonnet | JD + CV + profile | Categorized question set | 5-10s |
| Assessment Questions | Sonnet | JD + profile + test config | Question list | 5-10s |
| Assessment Scoring | Sonnet | Question + rubric + answer | Score + reasoning + confidence | 2-5s per answer |

### 5.2 AI Decision Logging (EU AI Act)

Every AI call is intercepted by a logging middleware:

```python
async def log_ai_decision(
    feature: str,
    model_id: str,
    prompt_version: str,
    input_summary: dict,
    output_summary: dict,
    confidence: float | None,
    tokens: tuple[int, int],
    latency_ms: int,
    user_id: UUID,
    tenant_id: UUID | None,
    entity_type: str,
    entity_id: UUID
) -> None:
    # Insert into ai_decision_logs
    # Calculate cost estimate from token counts
```

### 5.3 ESCO Integration

- ESCO API base: `https://ec.europa.eu/esco/api`
- Sync job: runs weekly, pulls full skills taxonomy
- Local cache in `esco_skills` table for fast autocomplete
- CV parsing prompt includes instruction to map skills to ESCO codes
- Matching scorer uses ESCO hierarchy for semantic similarity

### 5.4 Cost Management

- Usage tracking per tenant per feature
- CV parsing: ~$0.01-0.03 per CV
- JD enhancement: ~$0.01-0.05 per exchange
- Matching + explanation: ~$0.03-0.08 per candidate
- Assessment scoring: ~$0.01-0.03 per answer
- Admin dashboard: cost breakdown by feature, by tenant, by month

---

## 6. File Storage Architecture

### 6.1 Azure Blob Storage Layout

```
bryton-cv-app/
├── cvs/
│   ├── {candidate_id}/
│   │   ├── v1_original.pdf
│   │   ├── v2_original.docx
│   │   └── ...
├── formatted-cvs/
│   ├── {candidate_id}/
│   │   ├── {demand_id}_{timestamp}.pdf
│   │   └── ...
├── verification-evidence/
│   ├── {checklist_id}/
│   │   ├── diploma_scan.pdf
│   │   ├── cert_aws_saa.pdf
│   │   └── ...
├── exports/
│   ├── {tenant_id}/
│   │   ├── sla_report_{date}.pdf
│   │   └── ...
├── audit-cold/
│   ├── {year}/{month}/
│   │   ├── audit_logs_{tenant_id}.json.gz
│   │   └── ai_decision_logs_{tenant_id}.json.gz
└── temp/
```

### 6.2 Cold Audit Storage

- Cron job runs monthly: moves audit_logs and ai_decision_logs older than 12 months to Azure Blob
- Format: gzipped JSON, partitioned by tenant + month
- Queryable via Admin bulk export function (reads from both hot DB and cold Blob)
- Retention: 7 years (configurable per tenant)

---

## 7. Deployment Architecture

### 7.1 Docker Compose

```yaml
services:
  frontend:
    build: ./frontend
    ports: ["443:443", "80:80"]
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/ssl/certs

  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql+asyncpg://...
      - AZURE_STORAGE_CONNECTION_STRING=...
      - ANTHROPIC_API_KEY=...
      - SMTP_HOST=...
      - JWT_SECRET=...
      - ESCO_API_BASE=https://ec.europa.eu/esco/api
    depends_on:
      - db

  db:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=bryton
      - POSTGRES_USER=bryton
      - POSTGRES_PASSWORD=...
    ports: ["5432:5432"]

volumes:
  pgdata:
```

### 7.2 Nginx Configuration

```
server {
    listen 443 ssl;
    server_name app.braytonglobal.com;

    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/certs/privkey.pem;

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 7.3 Azure VM Spec

- **VM Size:** Standard_D4s_v5 (4 vCPU, 16 GB RAM)
- **OS Disk:** 64 GB Premium SSD
- **Data Disk:** 128 GB Premium SSD (PostgreSQL data)
- **Region:** West Europe
- **Networking:** NSG allowing 80, 443 inbound

### 7.4 Backup Strategy

- PostgreSQL: `pg_dump` daily via cron, stored in Azure Blob (separate container)
- Retain 30 days of daily backups
- Azure Blob Storage: geo-redundant storage (GRS) for all data
- VM snapshots: weekly via Azure Backup

---

## 8. Security Architecture

### 8.1 Security Layers

| Layer | Mechanism |
|-------|-----------|
| Transport | TLS 1.3 (Nginx) |
| Authentication | JWT (access: 15min, refresh: 7d httpOnly cookie) |
| Authorization | RBAC middleware per endpoint |
| Approval Chain | Four-eyes principle for critical actions |
| Tenant Isolation | PostgreSQL RLS policies |
| Input Validation | Pydantic v2 schemas on all endpoints |
| SQL Injection | SQLAlchemy ORM (parameterized queries) |
| XSS | React default escaping + CSP headers |
| CSRF | SameSite cookies + CORS restrictions |
| File Upload | Type validation + virus scanning + size limits |
| Rate Limiting | FastAPI middleware (per-IP and per-user) |
| Secrets | Environment variables (never in code) |
| AI Transparency | Full decision logging per EU AI Act |

### 8.2 CORS Policy

```python
origins = [
    "https://app.braytonglobal.com",
]
```

---

## 9. Monitoring & Observability

### 9.1 Health Checks

- `GET /health` — basic liveness
- `GET /health/ready` — readiness (DB, Blob, Claude API reachable)

### 9.2 Logging

- Structured JSON logging (Python `structlog`)
- Request/response logging (excluding sensitive fields)
- AI API call logging (model, tokens, latency, cost)

### 9.3 AI Monitoring Dashboard

- Human override rate by feature (trending over time)
- AI cost per tenant per month
- Latency percentiles per AI feature
- Model version tracking
- Prompt version changelog

---

## 10. Migration Path

### 10.1 Entra ID Integration (Phase 2)

- Add OIDC middleware alongside JWT auth
- Internal users: Brayton Entra tenant
- External customers: B2B federation
- Map Entra groups to RBAC roles

### 10.2 Scaling (When Needed)

- Stateless backend → multiple instances behind Azure Load Balancer
- PostgreSQL → Azure Database for PostgreSQL Flexible Server
- Docker Compose → Azure Container Apps or AKS
- Add Redis for session caching and job queuing
- Add Elasticsearch for full-text CV search
