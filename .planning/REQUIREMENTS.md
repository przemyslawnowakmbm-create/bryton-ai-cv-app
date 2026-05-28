# Bryton AI CV App — v1 Requirements

## Authentication & Users

- [ ] **AUTH-01**: User can create an account with email and password, receiving a verification email before access is granted
- [ ] **AUTH-02**: User can log in with email/password and receive a JWT access token (15-min) and refresh token (7-day httpOnly cookie)
- [ ] **AUTH-03**: User can log out from any page, invalidating their refresh token
- [ ] **AUTH-04**: User can request a password reset via email with a secure time-limited token
- [ ] **AUTH-05**: System rate-limits login attempts per IP and per account to prevent brute force
- [ ] **AUTH-06**: Admin can create, view, update, and deactivate users of any role across all tenants
- [ ] **AUTH-07**: SM can create and manage Customer users within their assigned tenant(s)
- [ ] **AUTH-08**: Candidate can self-register via a public registration page with email verification and GDPR consent

## Multi-Tenancy

- [ ] **TENANT-01**: Admin can create a new tenant with a unique 2-6 character prefix, name, and settings
- [ ] **TENANT-02**: All tenant-scoped database queries are filtered by PostgreSQL Row-Level Security policies, enforced via `SET app.current_tenant` on each session
- [ ] **TENANT-03**: SM and Recruiter can be assigned to multiple tenants and see data scoped to their assignments
- [ ] **TENANT-04**: Customer users see only data from their own tenant
- [ ] **TENANT-05**: Admin can deactivate a tenant, making all its data read-only

## RBAC & Approvals

- [ ] **RBAC-01**: System enforces 5 roles (Admin, SM, Recruiter, Customer, Candidate) with per-endpoint permission checks returning 403 for unauthorized access
- [ ] **RBAC-02**: Demand lifecycle transitions are restricted to specific roles per transition as defined in the transition rules table
- [ ] **RBAC-03**: Configurable approval gates per tenant: shortlist submission (Recruiter→SM), rate override (SM→Admin), candidate above rate (Recruiter→SM)
- [ ] **RBAC-04**: Approval requests are created with justification and context data, and the approver can approve, reject (with reason), or request changes
- [ ] **RBAC-05**: All approval decisions are logged in the audit trail with full context

## Contracts & Rate Cards

- [ ] **CONTRACT-01**: Admin/SM can create framework contracts under a tenant with reference, title, lot number, dates, max value, and status
- [ ] **CONTRACT-02**: Admin/SM can create rate card entries per contract defining max daily rate per profile code per SFIA level with effective dates
- [ ] **CONTRACT-03**: When a candidate is shortlisted for a demand linked to a contract, the system checks the candidate's rate expectation against the rate card ceiling and blocks shortlisting if exceeded (unless SM overrides via approval chain)
- [ ] **CONTRACT-04**: SM/Recruiter can view margin calculation (ceiling minus cost rate) per candidate per demand — not visible to Customer role

## Profile Catalogue

- [ ] **PROFILE-01**: Admin/SM can create profile catalogue entries under a contract with code, title, SFIA range, min experience, baseline skills (free text), certifications, languages (CEFR), clearance requirement, and education
- [ ] **PROFILE-02**: When creating a demand, user can optionally select a profile which pre-populates the demand form — all pre-populated fields are freely editable
- [ ] **PROFILE-03**: System tracks deviations between the demand and its source profile, showing a diff of what was changed
- [ ] **PROFILE-04**: System runs an advisory compliance check comparing shortlisted candidates against the original profile requirements, producing a MET/PARTIALLY MET/NOT MET checklist visible to all roles (advisory only, does not block)

## Candidates & CVs

- [ ] **CAND-01**: Candidate can upload a CV in PDF or DOCX format (max 10MB) which is stored in Azure Blob Storage and virus-scanned
- [ ] **CAND-02**: Upon CV upload, system extracts text and sends to Claude API for AI parsing, extracting: personal info, work experience, education, skills (free text with background ESCO mapping), certifications, languages (CEFR inference), clearance mentions, availability, rate expectations, and suggested SFIA level
- [ ] **CAND-03**: Candidate can review AI-parsed data and correct any field including CEFR levels, SFIA level, availability, rate, and visibility preferences
- [ ] **CAND-04**: Candidate profile shows a completeness percentage calculated from weighted field presence
- [ ] **CAND-05**: All uploaded CV versions are retained with version history; candidate can set which is current
- [ ] **CAND-06**: Candidate can add/edit/remove security clearances with level, type, issuing authority, dates, status, and reference number
- [ ] **CAND-07**: Candidate can add/edit/remove language proficiencies with language, CEFR level, source (self-declared/test/AI-inferred), and test details
- [ ] **CAND-08**: Candidate can set visibility preferences controlling which industries/tenant types can discover them in the global pool
- [ ] **CAND-09**: System monitors clearance expiry dates and sends alerts at 90, 60, and 30 days before expiry

## Demand Management

- [ ] **DEMAND-01**: SM, Recruiter, or Customer can create a demand with title, JD (free text), location, employment type, and optionally link to a profile and contract
- [ ] **DEMAND-02**: Each demand receives an auto-generated immutable number in format `{TENANT_PREFIX}-{SEQUENCE}` (e.g., ECTL-0001)
- [ ] **DEMAND-03**: SM can set a free-text "External Demand ID" field on any demand for linking to the Atos tool
- [ ] **DEMAND-04**: Demands follow an 8-state lifecycle (Draft→Open→Matching→Shortlisted→Interview→Offered→Filled→Closed) with role-based transition rules and configurable approval gates
- [ ] **DEMAND-05**: Every state transition is logged with who, when, from/to status, and optional notes
- [ ] **DEMAND-06**: SM can create a replacement demand linked to an original demand, pre-populated from the same profile, flagged as "Replacement" with a stricter SLA countdown
- [ ] **DEMAND-07**: Skills input on demands is free text — user types naturally; system suggests ESCO-aligned tags as optional autocomplete

## AI JD Enhancement

- [ ] **AIJD-01**: Demand creation/edit screen shows a split view: rich text editor (left) with an AI chat panel (right) powered by Claude API
- [ ] **AIJD-02**: AI chat responses stream in real-time via Server-Sent Events so users see tokens appearing progressively
- [ ] **AIJD-03**: AI provides inline suggestions in the editor for grammar, clarity, missing sections, and flags biased language (gendered, ageist, exclusionary)
- [ ] **AIJD-04**: Full conversation history is persisted per demand; users can revisit and continue previous enhancement sessions
- [ ] **AIJD-05**: Each accepted JD revision is saved as a version with timestamp and author; users can view diffs between versions and revert to any previous version
- [ ] **AIJD-06**: If demand is linked to a profile, AI cross-references the JD against profile baseline requirements and flags deviations

## CV-to-Demand Matching

- [ ] **MATCH-01**: Recruiter or SM can trigger matching on a demand by clicking "Find Matches"; matching can be re-run at any time
- [ ] **MATCH-02**: Phase 1 of matching applies structured hard filters (security clearance, language CEFR, rate ceiling, availability) to eliminate non-qualifying candidates before any AI is invoked
- [ ] **MATCH-03**: Phase 2 sends the full JD text and full parsed CV to Claude for holistic assessment, returning: composite score (0-100), dimension scores, narrative explanation, strengths, gaps, and profile compliance assessment
- [ ] **MATCH-04**: Each match result includes a human-readable narrative explanation stored for audit, visible to Recruiter, SM, and Customer on shortlisted candidates
- [ ] **MATCH-05**: Top N candidates (configurable per tenant, default 10) are auto-shortlisted; Recruiter reviews and can add/remove candidates before submission
- [ ] **MATCH-06**: Recruiter can view a side-by-side comparison of 2-4 candidates showing scores, qualifications, rates, and narrative explanations
- [ ] **MATCH-07**: Shortlist submission to Customer triggers the approval chain (Recruiter→SM approval before Customer sees it)
- [ ] **MATCH-08**: Every AI match decision is logged per EU AI Act requirements with model ID, prompt version, input/output summary, and subsequent human action

## Shortlisting & Rejections

- [ ] **SHORT-01**: Customer can view shortlisted candidates with full profiles, match scores, AI explanations, compliance checklists, verification status, and formatted CVs
- [ ] **SHORT-02**: Customer can approve candidates for interview or reject with a structured reason code selected from a predefined list (SKILLS_MISMATCH, CLEARANCE_NOT_MET, CLIENT_PREFERENCE, etc.)
- [ ] **SHORT-03**: Rejection reasons are aggregated into analytics showing most common reasons by profile, tenant, and time period

## CV Verification

- [ ] **VERIFY-01**: When a candidate is shortlisted, system auto-creates a verification checklist from the profile requirements with items for education, certifications, employment, languages, and clearance
- [ ] **VERIFY-02**: Recruiter can update each verification item status (verified, self-declared, pending, unverifiable, failed) and upload evidence documents to Azure Blob Storage
- [ ] **VERIFY-03**: AI flags inconsistencies in parsed CV data (e.g., experience years vs graduation date) for recruiter review
- [ ] **VERIFY-04**: Overall verification status (fully verified / partially verified / verification failed) is visible on the candidate profile and formatted CV

## Formatted CV Generation

- [ ] **FMTCV-01**: Recruiter/SM can generate a formatted CV from parsed candidate data using a standardized Brayton template including profile mapping, SFIA level, skills matrix, experience, certifications with verification status, languages (CEFR), and clearance level
- [ ] **FMTCV-02**: Formatted CV is exportable as PDF and DOCX, stored in Azure Blob with version tracking linked to the demand
- [ ] **FMTCV-03**: SM/Recruiter can edit the formatted CV before submission to the client

## Interviews

- [ ] **INTV-01**: Recruiter/SM can schedule an interview by entering date, time, duration, location/meeting link, interviewer(s), candidate, and interview type; all participants receive email notifications
- [ ] **INTV-02**: Recruiter/SM can trigger AI interview question generation which produces categorized questions (technical, behavioral, situational, culture fit) tagged by difficulty, based on JD + CV + profile
- [ ] **INTV-03**: Recruiter/SM can edit, add, or remove AI-generated questions before finalizing the question set
- [ ] **INTV-04**: AI generates a structured scorecard template per interview with criteria derived from profile requirements and JD; interviewers fill it in with 1-5 ratings per criterion, notes, and an overall recommendation
- [ ] **INTV-05**: When all interviewers submit scorecards, scores are aggregated and the interview status transitions to Scored

## Assessments

- [ ] **ASSESS-01**: Recruiter/Admin can create assessment templates with multiple question types (MCQ single, MCQ multi, short text, long text, scenario) with configurable time limit, passing score, randomization, and retake policy
- [ ] **ASSESS-02**: AI can suggest assessment questions based on JD + profile; Recruiter curates the final test from suggestions and/or a reusable question bank
- [ ] **ASSESS-03**: Candidate takes assessments in-app with a countdown timer (server-side enforced), question navigation, save progress, and auto-submit on timeout
- [ ] **ASSESS-04**: MCQ answers are auto-scored immediately; free text and scenario answers are scored by Claude API with score, reasoning, and confidence — low confidence (<0.6) flagged for human review
- [ ] **ASSESS-05**: Human can override any AI-scored answer; final composite score is a weighted sum of all question scores

## SLA & KPI Management

- [ ] **SLA-01**: Admin/SM can configure SLA targets per tenant per contract: time-to-fill (default 15 days), replacement time (default 10 days), CV-to-interview ratio (default 3:1), fill rate (default 90%), quality score (default 4.0/5.0)
- [ ] **SLA-02**: System automatically calculates SLA status per demand from lifecycle timestamps: On Track (<80% consumed), At Risk (80-99%), Breached (>=100%)
- [ ] **SLA-03**: Customer can view an SLA dashboard for their contract(s) showing current KPI performance vs targets, trend lines, per-demand breakdowns, and exportable PDF reports
- [ ] **SLA-04**: Replacement demands display a prominent countdown timer on dashboards showing days remaining vs SLA target
- [ ] **SLA-05**: When a demand transitions to Filled, a quality survey is triggered asking the Customer to rate timeliness, candidate quality, communication, and overall satisfaction (1-5 scale)

## Dashboards & Reporting

- [ ] **DASH-01**: Admin dashboard shows system health, cross-tenant metrics, AI system health (costs, override rates), user activity, and tenant comparison
- [ ] **DASH-02**: SM dashboard shows SLA performance gauges, tenant pipeline funnel, time-to-fill trends, rate card utilization, contract budget tracking, replacement countdowns, and attention-needed demands
- [ ] **DASH-03**: Recruiter dashboard shows assigned demands, matching queue, verification queue, recent match results, interview schedule, pending assessment reviews, and pending approvals
- [ ] **DASH-04**: Customer dashboard shows SLA gauges, demand status overview, shortlisted candidates awaiting review, upcoming interviews, filled positions, pipeline funnel, and quality trend
- [ ] **DASH-05**: Candidate dashboard shows application status tracker, matched demands, upcoming interviews, pending assessments, profile completeness, verification status, and clearance alerts
- [ ] **DASH-06**: All data tables support CSV export; key entities (candidate profiles, scorecards, assessment results, demand summaries, SLA reports) support PDF export

## Notifications

- [ ] **NOTIF-01**: System delivers in-app notifications via WebSocket with live badge count updates (no page refresh needed)
- [ ] **NOTIF-02**: System sends HTML email notifications for key events (demand created, status changed, shortlist ready, interview scheduled, assessment assigned/completed, approval pending/decided, SLA alerts, clearance expiring)
- [ ] **NOTIF-03**: Each user can configure per-event notification preferences choosing in-app only, email only, both, or neither

## Compliance & Audit

- [ ] **AUDIT-01**: System logs critical actions (demand transitions, login/logout, data deletions, role changes, tenant modifications, approval decisions, rate overrides, AI decisions, CV verifications) with timestamp, user, tenant, action, entity, IP, and details
- [ ] **AUDIT-02**: Audit logs are retained for 7 years with tiered storage: 12 months hot in PostgreSQL, remainder in Azure Blob as compressed JSON
- [ ] **AUDIT-03**: Admin can search and filter audit logs by date range, user, action type, and entity
- [ ] **AUDIT-04**: Admin can trigger a bulk audit export producing a ZIP of all data for a tenant + contract + date range (demands, candidates, matches, shortlists, scorecards, assessments, approvals, verifications, audit logs)
- [ ] **AUDIT-05**: All AI calls are logged in a separate ai_decision_logs table with model ID, prompt version hash, input/output summary, confidence, tokens, latency, cost estimate, and the human action taken on the output
- [ ] **AUDIT-06**: Candidate can request account deletion (GDPR right to be forgotten) with a 30-day grace period; after expiry, CV files are deleted, parsed data removed, and historical records anonymized while audit events are retained

## Design System & Infrastructure

- [ ] **INFRA-01**: Frontend uses React 19 + Vite + TypeScript + Tanstack Router with the exact EUROCONTROL design system (Exo font, EC color palette, Shadcn/UI components, Tailwind CSS with HSL custom properties)
- [ ] **INFRA-02**: Backend uses Python FastAPI with async SQLAlchemy 2.0, Alembic migrations, Pydantic v2 schemas, and structured JSON logging
- [ ] **INFRA-03**: Application deploys via Docker Compose (Nginx + FastAPI + PostgreSQL 16) on a single Azure VM
- [ ] **INFRA-04**: Health check endpoints exist at GET /health (liveness) and GET /health/ready (readiness — checks DB and Blob connectivity)
- [ ] **INFRA-05**: ESCO skills taxonomy is synced weekly from the EC API into a local reference table for background enrichment (no user-facing UI)
- [ ] **INFRA-06**: SFIA levels 1-7 are stored as reference data and used for rate card alignment and candidate seniority validation

## Future Requirements

- [ ] **AUTH-09**: Internal users authenticate via Microsoft Entra ID SSO — deferred to Phase 2
- [ ] **INTV-06**: Interview scheduling integrates with Outlook/Google Calendar — deferred to Phase 2
- [ ] **AUDIT-07**: Automated bias detection and adverse impact analysis across pipeline stages — on hold

## Out of Scope

- Mobile/tablet optimization — desktop-only enterprise tool (min 1280px viewport)
- Self-service tenant registration — Admin provisions manually at this scale
- Billing/metering per tenant — not needed for 5-20 tenants
- Video interview hosting — interviews happen offline
- Active placement / post-hire tracking — handled by external EUROCONTROL system
- Timesheet / hours tracking — handled by external system
- Automated reference checking via API (Xref/Checkster) — manual verification workflow instead
- Multi-language / i18n — English only
- Candidate sourcing from external job boards — candidates self-register
- Atos API integration — manual text field only

## Traceability

| Requirement | Phase | Plan | Status |
|------------|-------|------|--------|
| INFRA-01 | Phase 1 | TBD | Pending |
| INFRA-02 | Phase 1 | TBD | Pending |
| INFRA-03 | Phase 1 | TBD | Pending |
| INFRA-04 | Phase 1 | TBD | Pending |
| INFRA-05 | Phase 1 | TBD | Pending |
| INFRA-06 | Phase 1 | TBD | Pending |
| AUTH-01 | Phase 2 | TBD | Pending |
| AUTH-02 | Phase 2 | TBD | Pending |
| AUTH-03 | Phase 2 | TBD | Pending |
| AUTH-04 | Phase 2 | TBD | Pending |
| AUTH-05 | Phase 2 | TBD | Pending |
| AUTH-06 | Phase 2 | TBD | Pending |
| AUTH-07 | Phase 2 | TBD | Pending |
| AUTH-08 | Phase 2 | TBD | Pending |
| TENANT-01 | Phase 2 | TBD | Pending |
| TENANT-02 | Phase 2 | TBD | Pending |
| TENANT-03 | Phase 2 | TBD | Pending |
| TENANT-04 | Phase 2 | TBD | Pending |
| TENANT-05 | Phase 2 | TBD | Pending |
| RBAC-01 | Phase 2 | TBD | Pending |
| RBAC-02 | Phase 2 | TBD | Pending |
| RBAC-03 | Phase 2 | TBD | Pending |
| RBAC-04 | Phase 2 | TBD | Pending |
| RBAC-05 | Phase 2 | TBD | Pending |
| CONTRACT-01 | Phase 3 | TBD | Pending |
| CONTRACT-02 | Phase 3 | TBD | Pending |
| CONTRACT-03 | Phase 3 | TBD | Pending |
| CONTRACT-04 | Phase 3 | TBD | Pending |
| PROFILE-01 | Phase 3 | TBD | Pending |
| PROFILE-02 | Phase 3 | TBD | Pending |
| PROFILE-03 | Phase 3 | TBD | Pending |
| PROFILE-04 | Phase 3 | TBD | Pending |
| CAND-01 | Phase 4 | TBD | Pending |
| CAND-02 | Phase 4 | TBD | Pending |
| CAND-03 | Phase 4 | TBD | Pending |
| CAND-04 | Phase 4 | TBD | Pending |
| CAND-05 | Phase 4 | TBD | Pending |
| CAND-06 | Phase 4 | TBD | Pending |
| CAND-07 | Phase 4 | TBD | Pending |
| CAND-08 | Phase 4 | TBD | Pending |
| CAND-09 | Phase 4 | TBD | Pending |
| DEMAND-01 | Phase 5 | TBD | Pending |
| DEMAND-02 | Phase 5 | TBD | Pending |
| DEMAND-03 | Phase 5 | TBD | Pending |
| DEMAND-04 | Phase 5 | TBD | Pending |
| DEMAND-05 | Phase 5 | TBD | Pending |
| DEMAND-06 | Phase 5 | TBD | Pending |
| DEMAND-07 | Phase 5 | TBD | Pending |
| AIJD-01 | Phase 5 | TBD | Pending |
| AIJD-02 | Phase 5 | TBD | Pending |
| AIJD-03 | Phase 5 | TBD | Pending |
| AIJD-04 | Phase 5 | TBD | Pending |
| AIJD-05 | Phase 5 | TBD | Pending |
| AIJD-06 | Phase 5 | TBD | Pending |
| MATCH-01 | Phase 6 | TBD | Pending |
| MATCH-02 | Phase 6 | TBD | Pending |
| MATCH-03 | Phase 6 | TBD | Pending |
| MATCH-04 | Phase 6 | TBD | Pending |
| MATCH-05 | Phase 6 | TBD | Pending |
| MATCH-06 | Phase 6 | TBD | Pending |
| MATCH-07 | Phase 6 | TBD | Pending |
| MATCH-08 | Phase 6 | TBD | Pending |
| SHORT-01 | Phase 6 | TBD | Pending |
| SHORT-02 | Phase 6 | TBD | Pending |
| SHORT-03 | Phase 6 | TBD | Pending |
| VERIFY-01 | Phase 7 | TBD | Pending |
| VERIFY-02 | Phase 7 | TBD | Pending |
| VERIFY-03 | Phase 7 | TBD | Pending |
| VERIFY-04 | Phase 7 | TBD | Pending |
| FMTCV-01 | Phase 7 | TBD | Pending |
| FMTCV-02 | Phase 7 | TBD | Pending |
| FMTCV-03 | Phase 7 | TBD | Pending |
| INTV-01 | Phase 8 | TBD | Pending |
| INTV-02 | Phase 8 | TBD | Pending |
| INTV-03 | Phase 8 | TBD | Pending |
| INTV-04 | Phase 8 | TBD | Pending |
| INTV-05 | Phase 8 | TBD | Pending |
| ASSESS-01 | Phase 8 | TBD | Pending |
| ASSESS-02 | Phase 8 | TBD | Pending |
| ASSESS-03 | Phase 8 | TBD | Pending |
| ASSESS-04 | Phase 8 | TBD | Pending |
| ASSESS-05 | Phase 8 | TBD | Pending |
| SLA-01 | Phase 9 | TBD | Pending |
| SLA-02 | Phase 9 | TBD | Pending |
| SLA-03 | Phase 9 | TBD | Pending |
| SLA-04 | Phase 9 | TBD | Pending |
| SLA-05 | Phase 9 | TBD | Pending |
| DASH-01 | Phase 9 | TBD | Pending |
| DASH-02 | Phase 9 | TBD | Pending |
| DASH-03 | Phase 9 | TBD | Pending |
| DASH-04 | Phase 9 | TBD | Pending |
| DASH-05 | Phase 9 | TBD | Pending |
| DASH-06 | Phase 9 | TBD | Pending |
| NOTIF-01 | Phase 10 | TBD | Pending |
| NOTIF-02 | Phase 10 | TBD | Pending |
| NOTIF-03 | Phase 10 | TBD | Pending |
| AUDIT-01 | Phase 10 | TBD | Pending |
| AUDIT-02 | Phase 10 | TBD | Pending |
| AUDIT-03 | Phase 10 | TBD | Pending |
| AUDIT-04 | Phase 10 | TBD | Pending |
| AUDIT-05 | Phase 10 | TBD | Pending |
| AUDIT-06 | Phase 10 | TBD | Pending |
