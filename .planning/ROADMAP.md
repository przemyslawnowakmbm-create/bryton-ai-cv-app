# Bryton AI CV App — Roadmap

## Phases

- [ ] **Phase 1: Infrastructure & Foundation** - Scaffold repo, Docker Compose stack, design system, reference data, health checks
- [ ] **Phase 2: Auth, Tenancy & RBAC** - User accounts, JWT auth, multi-tenant RLS, five-role RBAC, configurable approval chains
- [ ] **Phase 3: Contracts, Rate Cards & Profile Catalogue** - Framework contracts, rate card enforcement, profile templates with deviation tracking
- [ ] **Phase 4: Candidate Profiles & CV Management** - Candidate self-registration, CV upload + AI parsing, profile management, clearance lifecycle
- [ ] **Phase 5: Demand Management & AI JD Enhancement** - Demand creation, 8-state lifecycle, AI-powered JD editor with streaming, version history
- [ ] **Phase 6: AI Matching & Shortlisting** - Hard-filter + Claude holistic matching, auto-shortlisting, candidate comparison, approval chain
- [ ] **Phase 7: CV Verification & Formatted CV** - Verification checklists with evidence upload, AI inconsistency detection, Brayton-branded CV export
- [ ] **Phase 8: Interviews & Assessments** - Interview scheduling with AI question generation, scorecards, configurable test builder, AI scoring
- [ ] **Phase 9: SLA, Dashboards & Reporting** - SLA configuration and tracking, five role-specific dashboards, BI charts, CSV/PDF exports
- [ ] **Phase 10: Notifications, Audit & Compliance** - WebSocket in-app + email notifications, 7-year audit trail, GDPR right-to-be-forgotten, EU AI Act logs

---

## Phase Details

### Phase 1: Infrastructure & Foundation

**Goal**: The application skeleton is running in Docker Compose with the EUROCONTROL design system applied, health endpoints responding, and all reference data (SFIA levels, ESCO taxonomy) seeded and available for use by every subsequent phase.

**Depends on**: Nothing

**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, INFRA-06

**Success Criteria** (what must be TRUE):
1. Developer can run `docker compose up` and reach the React frontend at localhost on a browser without errors, with Exo font and EC color palette visibly applied
2. `GET /health` returns 200 liveness; `GET /health/ready` returns 200 with DB and Blob connectivity confirmed, or a clear error if either is unavailable
3. FastAPI backend logs structured JSON to stdout; Alembic migration runs clean on a fresh PostgreSQL 16 container
4. SFIA levels 1-7 are queryable via a reference API endpoint; ESCO taxonomy weekly sync job runs without errors and populates the local reference table
5. Tanstack Router serves at least a placeholder for every top-level route without 404s; Shadcn/UI component renders correctly with HSL custom properties

**Plans**: 3 plans

Plans:
- [ ] 01-01-PLAN.md — Backend foundation: FastAPI + SQLAlchemy + Alembic + health endpoints + SFIA reference API
- [ ] 01-02-PLAN.md — Frontend foundation: React 19 + TanStack Router + EUROCONTROL design system + placeholder routes
- [ ] 01-03-PLAN.md — Docker Compose stack + ESCO weekly sync + integration smoke tests

---

### Phase 2: Auth, Tenancy & RBAC

**Goal**: Every user can securely create an account and log in; all data is isolated by tenant via PostgreSQL RLS; the five-role permission model is enforced on every endpoint; and configurable approval chains are operational.

**Depends on**: Phase 1

**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07, AUTH-08, TENANT-01, TENANT-02, TENANT-03, TENANT-04, TENANT-05, RBAC-01, RBAC-02, RBAC-03, RBAC-04, RBAC-05

**Success Criteria** (what must be TRUE):
1. A new user can register with email/password, receive a verification email, verify their account, log in, receive a JWT access token and httpOnly refresh cookie, and remain logged in across browser sessions until they explicitly log out
2. A candidate can self-register via a public URL, complete GDPR consent, and access only the candidate-scoped views — attempting to reach a recruiter endpoint returns HTTP 403
3. Admin can create a tenant with a 2-6 character prefix; a second Admin session with `SET app.current_tenant` for a different tenant cannot see the first tenant's data, confirming RLS enforcement
4. An SM can create a Customer user in their tenant; that Customer user sees only their tenant's data even if they manipulate query parameters
5. An approval request created by a Recruiter for shortlist submission is visible to the assigned SM approver; the SM can approve/reject with a reason; the decision appears in the audit log with full context

**Plans**: 4 plans

Plans:
- [ ] 02-01-PLAN.md — Auth backend: JWT service, registration, login, refresh, logout, email verification, password reset, rate limiting
- [ ] 02-02-PLAN.md — Tenancy + RLS + RBAC: get_tenant_db with SET LOCAL, RLS policies, require_roles, tenant CRUD, multi-tenant assignments
- [ ] 02-03-PLAN.md — Frontend auth: Zustand store, API client with 401 refresh, TanStack Router guards, login/register/reset pages
- [ ] 02-04-PLAN.md — User management + Approvals + Audit: Admin CRUD users, SM tenant-scoped management, approval chain, audit log

---

### Phase 3: Contracts, Rate Cards & Profile Catalogue

**Goal**: Admins and SMs can define the commercial framework (contracts, rate ceilings) and profile templates that govern every downstream demand and candidate submission, with rate enforcement and deviation tracking active.

**Depends on**: Phase 2

**Requirements**: CONTRACT-01, CONTRACT-02, CONTRACT-03, CONTRACT-04, PROFILE-01, PROFILE-02, PROFILE-03, PROFILE-04

**Success Criteria** (what must be TRUE):
1. Admin can create a framework contract with reference, lot number, dates, and max value; SM can create rate card entries per profile code per SFIA level with effective dates, and the entries are visible on the contract detail page
2. When a Recruiter shortlists a candidate whose rate expectation exceeds the rate card ceiling, the system blocks shortlisting with a clear error — the block is lifted only after an SM approves a rate override via the approval chain
3. SM can view the margin calculation (ceiling minus cost rate) for a candidate against a demand; the Customer role accessing the same page sees no margin data
4. Admin can create a profile catalogue entry with SFIA range, baseline skills, certifications, CEFR requirements, and clearance requirement; when a Recruiter creates a demand from that profile, all fields are pre-populated and freely editable
5. After editing a demand's pre-populated fields, the system displays a diff showing exactly which fields deviate from the source profile

**Plans**: TBD

---

### Phase 4: Candidate Profiles & CV Management

**Goal**: Candidates can upload their CV and have it AI-parsed into a structured profile they can review and correct; their security clearances, languages, and visibility preferences are managed in one place; and clearance expiry alerts fire automatically.

**Depends on**: Phase 2

**Requirements**: CAND-01, CAND-02, CAND-03, CAND-04, CAND-05, CAND-06, CAND-07, CAND-08, CAND-09

**Success Criteria** (what must be TRUE):
1. Candidate can upload a PDF or DOCX CV (up to 10MB) and within a reasonable wait see AI-parsed results: name, experience timeline, education, skills list, inferred SFIA level, CEFR languages, and rate expectation — all pre-filled in the profile form for review
2. Candidate can correct any AI-inferred field (including SFIA level and CEFR), save the corrections, and see the updated profile persisted across sessions
3. Candidate can upload a second CV version, set it as current, and see version history with dates; the previous version remains accessible but is not used for matching
4. Candidate profile shows a completeness percentage that increases as more fields are filled in and decreases if required fields are cleared
5. When a clearance expiry date is within 90 days, the candidate and recruiter receive an alert notification; alerts repeat at 60 and 30 days

**Plans**: TBD

---

### Phase 5: Demand Management & AI JD Enhancement

**Goal**: SMs, Recruiters, and Customers can create and manage demands through an 8-state lifecycle with role-gated transitions; every demand has AI-assisted JD editing with streaming chat, inline suggestions, and full version history.

**Depends on**: Phase 3, Phase 4

**Requirements**: DEMAND-01, DEMAND-02, DEMAND-03, DEMAND-04, DEMAND-05, DEMAND-06, DEMAND-07, AIJD-01, AIJD-02, AIJD-03, AIJD-04, AIJD-05, AIJD-06

**Success Criteria** (what must be TRUE):
1. SM creates a demand; it receives an immutable tenant-prefixed number (e.g., ECTL-0001); the demand can be transitioned through all 8 states by the correct roles; attempting an unauthorized transition returns a clear error
2. On the demand editor screen, the user types a message in the AI chat panel and sees Claude's response stream token by token via SSE — the full conversation persists when the user navigates away and returns
3. AI chat panel surfaces inline suggestions in the JD editor (grammar, missing sections, biased language flags) and those suggestions can be accepted or dismissed individually
4. Recruiter saves an accepted JD revision; a version is created with timestamp and author; the diff between any two versions is viewable; reverting to a previous version creates a new version (not destructive)
5. SM creates a replacement demand linked to an original demand; it is flagged as Replacement, pre-populated from the same profile, and shows a SLA countdown from creation

**Plans**: TBD

---

### Phase 6: AI Matching & Shortlisting

**Goal**: Recruiters can trigger AI matching on any open demand and receive a ranked, explained shortlist within a reasonable time; Customers can review shortlisted candidates with full AI transparency; all AI decisions are logged for EU AI Act compliance.

**Depends on**: Phase 5

**Requirements**: MATCH-01, MATCH-02, MATCH-03, MATCH-04, MATCH-05, MATCH-06, MATCH-07, MATCH-08, SHORT-01, SHORT-02, SHORT-03

**Success Criteria** (what must be TRUE):
1. Recruiter clicks "Find Matches" on a demand; candidates who fail hard filters (clearance, CEFR, rate, availability) are excluded before any AI is called, and the reason for exclusion is visible per candidate
2. Passing candidates receive a Claude-generated composite score (0-100), dimension scores, a narrative explanation, listed strengths and gaps, and a profile compliance assessment — all visible to Recruiter and SM
3. Top N candidates (configurable per tenant, default 10) are auto-shortlisted; Recruiter can add/remove candidates and compare up to 4 side-by-side before submitting to SM for approval
4. After SM approves, Customer can view the shortlist with full profiles, AI explanations, compliance checklists, verification status, and formatted CVs
5. Customer can reject a candidate with a structured reason code; rejection reasons are aggregated in analytics by profile, tenant, and time period
6. Every AI match decision is logged with model ID, prompt version hash, input/output summary, and the human action taken, queryable for audit

**Plans**: TBD

---

### Phase 7: CV Verification & Formatted CV

**Goal**: Recruiters can verify candidate credentials against profile requirements with evidence upload and AI-flagged inconsistencies; they can generate and edit a Brayton-branded formatted CV in PDF or DOCX for client submission.

**Depends on**: Phase 6

**Requirements**: VERIFY-01, VERIFY-02, VERIFY-03, VERIFY-04, FMTCV-01, FMTCV-02, FMTCV-03

**Success Criteria** (what must be TRUE):
1. When a candidate is shortlisted, a verification checklist is automatically created with items for education, certifications, employment, languages, and clearance derived from profile requirements — the checklist is visible immediately without manual setup
2. Recruiter can update each verification item status (verified / self-declared / pending / unverifiable / failed) and attach an evidence document; the overall verification status (Fully Verified / Partially Verified / Failed) is visible on the candidate profile
3. AI flags at least one plausible inconsistency in a test CV (e.g., 10 years experience with graduation 8 years ago) and surfaces it as a recruiter review item; the recruiter can dismiss or confirm the flag
4. Recruiter generates a formatted CV from parsed data; the output matches the Brayton-branded template with SFIA level, skills matrix, experience timeline, certifications with verification status, CEFR languages, and clearance level
5. Formatted CV is downloadable as both PDF and DOCX; each generated version is stored in Azure Blob with a version history linked to the specific demand

**Plans**: TBD

---

### Phase 8: Interviews & Assessments

**Goal**: Recruiters can schedule interviews with AI-generated question sets and scorecards; candidates can take in-app assessments with server-enforced timers; AI scores free-text answers with human override capability.

**Depends on**: Phase 6

**Requirements**: INTV-01, INTV-02, INTV-03, INTV-04, INTV-05, ASSESS-01, ASSESS-02, ASSESS-03, ASSESS-04, ASSESS-05

**Success Criteria** (what must be TRUE):
1. Recruiter schedules an interview with date, time, interviewers, and meeting link; all participants (candidate and interviewers) receive email notifications with the event details
2. Recruiter triggers AI question generation and receives categorized questions (technical, behavioral, situational, culture fit) with difficulty tags; questions can be edited, reordered, or removed before finalizing
3. Each interview has a structured scorecard with criteria from the profile and JD; interviewers submit 1-5 ratings per criterion; when all interviewers submit, scores aggregate and status transitions to Scored
4. Recruiter creates an assessment from a template with MCQ and free-text questions, configurable time limit, and passing score; candidate takes it in-app with a visible countdown timer that auto-submits on timeout
5. MCQ answers are scored immediately on submission; free-text answers receive a Claude score with reasoning; answers flagged as low confidence (<0.6) appear in a review queue for human override; human can override any score before the composite is finalized

**Plans**: TBD

---

### Phase 9: SLA, Dashboards & Reporting

**Goal**: SMs and Customers can monitor SLA compliance with real-time gauges and trend charts; every role sees a purpose-built dashboard with the data they need; all key entities are exportable as CSV and PDF.

**Depends on**: Phase 8

**Requirements**: SLA-01, SLA-02, SLA-03, SLA-04, SLA-05, DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06

**Success Criteria** (what must be TRUE):
1. Admin configures SLA targets for a contract (time-to-fill, replacement time, CV-to-interview ratio); system automatically marks each demand as On Track, At Risk, or Breached based on lifecycle timestamps without manual input
2. Customer views the SLA dashboard and sees current KPI gauges vs targets, trend lines, per-demand breakdowns; replacement demands show a prominent countdown timer; the dashboard is exportable as PDF
3. When a demand transitions to Filled, a quality survey notification is sent to the Customer; the Customer completes ratings for timeliness, candidate quality, communication, and overall satisfaction; the scores appear in the SM dashboard trends
4. Each role sees a dashboard with role-appropriate data: Admin sees cross-tenant system health; SM sees pipeline funnel and rate card utilization; Recruiter sees matching queue and verification queue; Customer sees shortlist review items; Candidate sees application status and clearance alerts
5. User can export any data table as CSV and download PDF versions of candidate profiles, scorecards, assessment results, demand summaries, and SLA reports

**Plans**: TBD

---

### Phase 10: Notifications, Audit & Compliance

**Goal**: All users receive real-time in-app and email notifications for the events they care about; the 7-year audit trail with tiered storage is operational; GDPR right-to-be-forgotten and EU AI Act logging are fully enforced.

**Depends on**: Phase 9

**Requirements**: NOTIF-01, NOTIF-02, NOTIF-03, AUDIT-01, AUDIT-02, AUDIT-03, AUDIT-04, AUDIT-05, AUDIT-06

**Success Criteria** (what must be TRUE):
1. User receives an in-app notification without refreshing the page when a relevant event occurs (e.g., shortlist submitted, approval pending); the notification badge count updates live via WebSocket
2. System sends an HTML email notification for each key event in the list (demand created, status changed, shortlist ready, interview scheduled, assessment assigned, approval pending/decided, SLA alert, clearance expiring) and the email arrives with correct content
3. Each user can open notification preferences and select per-event whether to receive in-app only, email only, both, or neither; preference changes take effect immediately on subsequent events
4. Admin can search audit logs by date range, user, action type, and entity and retrieve results within a reasonable time; logs older than 12 months are stored in Azure Blob as compressed JSON but remain retrievable via bulk export
5. A candidate requests account deletion; after the 30-day grace period, CV files are removed from Azure Blob, parsed data is cleared, historical records are anonymized with a tombstone marker, and audit events are retained with the candidate ID replaced by an anonymized reference — the deletion itself is logged in the audit trail

**Plans**: TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Infrastructure & Foundation | 0/3 | Planning complete | - |
| 2. Auth, Tenancy & RBAC | 0/4 | Planning complete | - |
| 3. Contracts, Rate Cards & Profile Catalogue | 0/? | Not started | - |
| 4. Candidate Profiles & CV Management | 0/? | Not started | - |
| 5. Demand Management & AI JD Enhancement | 0/? | Not started | - |
| 6. AI Matching & Shortlisting | 0/? | Not started | - |
| 7. CV Verification & Formatted CV | 0/? | Not started | - |
| 8. Interviews & Assessments | 0/? | Not started | - |
| 9. SLA, Dashboards & Reporting | 0/? | Not started | - |
| 10. Notifications, Audit & Compliance | 0/? | Not started | - |

---

*Last updated: 2026-05-28*
