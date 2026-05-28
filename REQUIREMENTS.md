# Bryton AI CV App — Product Requirements Document

**Version:** 2.0
**Date:** 2026-05-28
**Status:** Draft
**Change log:** v2.0 incorporates T&M governance layer, EU AI Act compliance, SFIA/ESCO alignment, and 19 gap analysis findings.

---

## 1. Product Overview

Bryton AI CV App is a multi-tenant **T&M staffing governance platform** that manages the full recruitment lifecycle — from demand creation through candidate matching, interview, assessment, and hire — purpose-built for EU institutional framework contracts. The platform provides AI-powered recruitment with full auditability, profile catalogue compliance, rate card enforcement, and real-time SLA tracking.

The tool covers recruitment **up to onboarding/hire**. Post-hire engagement tracking (timesheets, active placement management) is handled by an external system.

### 1.1 Key Objectives

- Demonstrate auditable, enforceable recruitment governance to clients (EUROCONTROL)
- Enforce profile catalogue compliance — every CV mapped to predefined profiles with gap analysis
- Enforce rate card ceilings — no candidate submitted above contractual rate limits
- Track security clearance lifecycle — block submission of uncleared candidates
- Provide client-visible SLA dashboards — real-time time-to-fill, fill rate, CV-to-interview ratio
- Accelerate recruiter workflow through AI-powered matching, JD refinement, and interview preparation
- Comply with EU AI Act (Annex III high-risk) from day one — explainability, human oversight, monitoring
- Enable candidates to self-manage profiles and track applications through to hire

### 1.2 Target Users

| Role | Type | Description |
|------|------|-------------|
| **Admin** | Internal | System-wide configuration, tenant management, user management, system health, global audit access |
| **Service Manager (SM)** | Internal | Tenant-scoped operations, demand oversight, Atos ID linking, rate card management, approval authority, SLA monitoring |
| **Recruiter** | Internal | Day-to-day demand management, CV review, matching, interview coordination, CV verification |
| **Customer** | External | Raises demands, reviews shortlisted candidates, provides feedback, approves candidates, views SLA performance |
| **Candidate** | External | Self-registration, CV upload, views matched demands, takes assessments, tracks applications |

---

## 2. Multi-Tenancy

### 2.1 Isolation Model

**Hybrid: shared database with Row-Level Security (RLS)**

- Single PostgreSQL database with RLS policies enforcing tenant isolation at the database level
- Every tenant-scoped table includes a `tenant_id` column
- RLS policies applied via `SET app.current_tenant` on each database session
- Global entities (candidates, system config, ESCO taxonomy, SFIA levels) are not tenant-scoped but have visibility rules
- Designed for **5–20 tenants** at launch with manual provisioning

### 2.2 Tenant-Scoped Entities

- Contracts and rate cards
- Profile catalogues and profile requirements
- Demands (job descriptions, lifecycle state)
- Shortlists and rejection records
- Interviews, scorecards, and assessments
- SLA configurations and SLA metrics
- Approval requests
- Notifications
- Audit logs
- Customer users
- AI chat sessions (JD enhancement)
- CV verification checklists
- Formatted CV templates

### 2.3 Global Entities

- Candidates (profiles, CVs, parsed data, security clearances, language proficiencies)
- Admin users, Recruiter users, Service Manager users
- SFIA framework levels (reference data)
- ESCO skills taxonomy (reference data)
- System configuration
- Assessment question banks (global templates)
- Tenant definitions
- AI decision logs

### 2.4 Candidate Visibility Rules

Candidates exist in a global pool. Tenant-level visibility rules control which tenants' recruiters can discover which candidates:

- Candidates can opt into visibility for specific industries or demand types
- Recruiters only see candidates visible to their assigned tenant(s)
- A candidate matched to a demand in Tenant A is not visible to Tenant B unless independently matched
- Admin sees all candidates globally

### 2.5 Tenant Onboarding

1. Admin creates tenant via internal UI (name, prefix code, settings)
2. Admin creates contract(s) under tenant with rate cards and SLA terms
3. Admin uploads or creates profile catalogue for the contract
4. Admin creates first Customer user and sends invite link
5. Customer admin logs in and self-configures: additional users, preferences, notification settings

---

## 3. Authentication & Authorization

### 3.1 Authentication

**Phase 1 (Launch):** Username + password for all roles

- Email-based registration with email verification
- Password requirements: minimum 12 characters, complexity rules
- Session management via JWT (access token + refresh token)
- Rate limiting on login attempts
- Password reset via email

**Phase 2 (Deferred):** Microsoft Entra ID SSO

- Internal roles authenticate via Brayton's Entra tenant
- External customers authenticate via their own Entra tenant (B2B federation)
- Architecture prepared for OIDC integration from day one

### 3.2 Role-Based Access Control (RBAC)

Five roles with hierarchical permissions:

#### Admin
- Full system access across all tenants
- Tenant CRUD (create, read, update, deactivate)
- Contract and rate card management
- Profile catalogue management (global templates)
- User management (all roles)
- System configuration
- Global audit log access (7-year history)
- Global candidate pool access
- AI system monitoring and configuration
- Bulk audit export for external auditors
- Dashboard: system-wide metrics across all tenants

#### Service Manager (SM)
- Scoped to assigned tenant(s)
- Contract and rate card management within tenant
- Profile catalogue management within tenant
- Full demand lifecycle management
- Atos external ID assignment
- Shortlist review and approval
- Rate card ceiling enforcement (override with documented justification)
- Replacement demand creation
- SLA monitoring and reporting
- CV verification oversight
- **Approval authority**: can approve/reject approval requests
- Interview oversight
- Dashboard: tenant pipeline metrics + SLA performance

#### Recruiter
- Scoped to assigned tenant(s) and demands
- Demand creation (linked to profile catalogue)
- JD enhancement via AI chat
- CV review, matching trigger, and shortlist creation
- CV verification execution
- Formatted CV generation
- Interview scheduling and question generation
- Assessment creation and review
- **Initiates approval requests** (shortlist submission, rate override)
- Dashboard: assigned demand workload

#### Customer
- Scoped to own tenant only
- Demand creation (raise JD requests, selecting from profile catalogue)
- JD enhancement via AI chat
- View shortlisted candidates (full profiles with verification status)
- Approve/reject candidates for interview (with structured reason)
- View demand status and pipeline
- View SLA dashboard for their contract(s)
- Provide feedback on candidates and recruitment process quality
- Dashboard: own demands, candidate status, SLA metrics

#### Candidate
- Global (not tenant-scoped)
- Self-registration and profile management
- CV upload and update
- Security clearance self-declaration
- Language proficiency self-declaration (CEFR levels)
- View matched demands (anonymized company info until shortlisted)
- Express interest or decline matches
- Take assigned assessments in-app
- View interview schedules
- Track application status end-to-end
- Request data deletion (GDPR)
- Dashboard: application status and upcoming activities

### 3.3 Approval Chain (Four-Eyes Principle)

Configurable per tenant. Certain actions require approval from a second authorized person before taking effect:

| Action | Initiator | Approver | Default |
|--------|-----------|----------|---------|
| Shortlist submission to client | Recruiter | SM | Enabled |
| Rate card ceiling override | SM | Admin | Enabled |
| Candidate submission above rate | Recruiter | SM | Enabled |
| Demand cancellation | SM | Admin | Disabled |
| Profile catalogue modification | SM | Admin | Disabled |

- Approval request creates a pending item with: action description, justification, supporting data
- Approver receives notification (in-app + email)
- Approver can: approve, reject (with reason), or request changes
- Approved actions execute automatically; rejected actions are logged
- All approval decisions logged in audit trail with full context
- Configurable: tenants can enable/disable individual approval gates

---

## 4. Core Features

### 4.1 CV Management

#### 4.1.1 CV Upload
- Supported formats: PDF, DOCX
- Maximum file size: 10 MB per file
- Storage: Azure Blob Storage with tenant-scoped containers
- Virus scanning on upload

#### 4.1.2 AI CV Parsing
- Extract structured data from uploaded CVs via Claude API:
  - Personal information (name, contact, location)
  - Work experience (company, role, duration, description)
  - Education (institution, degree, field, year)
  - Skills mapped to **ESCO taxonomy codes** (see §4.2)
  - Certifications and licenses (name, issuer, date, expiry)
  - Language proficiencies with **CEFR level inference** (see §4.1.6)
  - Security clearance mentions (see §4.5)
  - Availability and preferences (remote/on-site/hybrid, relocation)
  - Salary / rate expectations (if stated)
  - **SFIA level suggestion** based on experience evidence (see §4.3)
- Parsed data stored as structured JSON alongside the original document
- Candidates can review and correct parsed data
- Re-parsing triggered on CV update

#### 4.1.3 Candidate Profile
- Auto-populated from parsed CV data
- Candidate-editable fields: availability date, location preference, rate expectation, industry preferences, visibility settings, security clearances, language proficiencies
- Profile completeness indicator
- CV version history (all uploaded versions retained)
- **Verification status badge**: unverified / partially verified / fully verified (see §4.9)

#### 4.1.4 Formatted CV Generation
- Generate client-ready CVs from parsed data in a **standardized Brayton template**
- Template customizable per tenant/contract (EUROCONTROL may require a specific format)
- Includes: profile catalogue mapping, SFIA level, skills matrix (ESCO-tagged), experience summary, certifications with verification status, language proficiencies (CEFR), security clearance level
- Export as PDF and DOCX
- Version tracking: each generated CV is timestamped and linked to the demand it was generated for
- SM/Recruiter can edit the generated CV before submission

#### 4.1.5 Language Proficiency (CEFR)
- Structured language proficiency on candidate profile:
  - Language (from ISO 639-1 list)
  - CEFR level: A1, A2, B1, B2, C1, C2 (or Native)
  - Source: self-declared / test result / AI-inferred from CV
  - Test name and date (if applicable)
- AI parsing infers CEFR levels from CV text (e.g., "fluent English" → C1, "basic French" → A2)
- Candidate can correct AI-inferred levels
- Profile catalogue specifies required language + minimum CEFR level per profile
- Matching engine includes language compliance check (hard filter: below minimum = excluded)

### 4.2 ESCO Skills Taxonomy

#### 4.2.1 Overview
The **European Skills, Competences, Qualifications and Occupations (ESCO)** classification is the EU's multilingual skills taxonomy, maintained by the European Commission. Integrating ESCO provides standardized skills vocabulary, semantic matching, and EU institutional alignment.

#### 4.2.2 Integration
- ESCO taxonomy loaded as reference data (skills hierarchy with codes)
- AI CV parsing maps extracted skills to ESCO codes (with confidence score)
- JD creation and profile catalogue use ESCO-aligned skill tags (with autocomplete search)
- Matching operates on ESCO codes (semantic similarity, not string matching)
- Skills that don't map to ESCO are stored as "custom skills" with a flag for future mapping
- ESCO data refreshed periodically from the ESCO API (free, maintained by EC)

#### 4.2.3 Benefits
- Standardized vocabulary eliminates matching failures from naming differences (e.g., "JS" vs "JavaScript" both map to the same ESCO code)
- Cross-border skill comparability (multilingual candidates)
- Signals regulatory sophistication to EU institutional clients
- Enables future skills gap analysis and supply/demand reporting

### 4.3 SFIA Framework

#### 4.3.1 Overview
The **Skills Framework for the Information Age (SFIA)** defines 7 levels of responsibility and competence, used across EU/UK government procurement to standardize seniority mapping and rate card alignment.

#### 4.3.2 SFIA Levels

| Level | Label | Description |
|-------|-------|-------------|
| 1 | Follow | Works under close direction. Routine tasks. |
| 2 | Assist | Works under routine direction. Some autonomy. |
| 3 | Apply | Works under general direction. Uses discretion. |
| 4 | Enable | Works under general guidance. Substantial responsibility. |
| 5 | Ensure/Advise | Broad direction. Accountable for significant outcomes. |
| 6 | Initiate/Influence | Has defined authority. Accountable for critical outcomes. |
| 7 | Set Strategy/Inspire | Highest level. Sets organizational strategy. |

#### 4.3.3 Implementation
- SFIA levels stored as reference data
- Each profile in the catalogue maps to a SFIA level range (e.g., "Senior Developer" = SFIA 4-5)
- AI parsing suggests SFIA level based on CV evidence (years of experience, role titles, responsibility descriptors)
- SM/Recruiter validates and confirms SFIA level before submission
- Rate card ceilings linked to SFIA levels
- Client sees SFIA level with justification on candidate profile
- Mismatch alert: if AI-suggested SFIA level differs from the recruiter-assigned level by ≥2, flag for review

### 4.4 Profile Catalogue

#### 4.4.1 Overview
EU institutional T&M contracts define a catalogue of **predefined profiles** — standardized role definitions with mandatory qualifications, minimum experience, required certifications, and language requirements. Every candidate submitted must map to a profile and be validated against its requirements.

#### 4.4.2 Profile Definition
Each profile contains:

| Field | Description | Example |
|-------|-------------|---------|
| Code | Unique identifier within contract | `SC-DEV-03` |
| Title | Role name | "Senior Java Developer" |
| Description | Role summary | "Designs, develops, and maintains..." |
| SFIA Level Range | Min-Max SFIA level | 4-5 |
| Min Years Experience | Total relevant experience | 8 |
| Required Skills | ESCO-coded mandatory skills | Java, Spring Boot, Microservices |
| Preferred Skills | ESCO-coded nice-to-have skills | Kubernetes, AWS |
| Required Certifications | Must-have certs | Oracle Java SE Certified |
| Required Languages | Language + min CEFR level | English B2+, French B1+ |
| Required Clearance | Min security clearance level | NATO RESTRICTED |
| Education | Min degree level | Bachelor's in CS or equivalent |
| Contract | Link to parent contract | ECTL-FWC-2026-01 |
| Rate Ceiling | Max daily rate for this profile | Linked to rate card |

#### 4.4.3 Profile Compliance Check
When a candidate is matched or shortlisted against a profile-linked demand:
- System runs automated compliance check against all profile requirements
- Produces a **compliance checklist**: each requirement marked as MET / PARTIALLY MET / NOT MET / UNVERIFIED
- Visual indicator: green (all mandatory met), amber (minor gaps in preferred), red (mandatory requirement not met)
- Red items block shortlisting unless SM overrides with documented justification (triggers approval chain)
- Compliance checklist attached to the candidate-demand submission record
- Client sees the checklist on shortlisted candidate profiles

### 4.5 Security Clearance Management

#### 4.5.1 Clearance Tracking
Each candidate can have zero or more security clearances:

| Field | Description |
|-------|-------------|
| Level | RESTRICTED, CONFIDENTIAL, SECRET, TOP SECRET |
| Type | NATO, EU, National, Other |
| Issuing Authority | Country code (e.g., BE, FR, DE) |
| Issue Date | When granted |
| Expiry Date | When it expires |
| Status | ACTIVE, EXPIRED, PENDING, DENIED, REVOKED |
| Reference Number | Clearance reference (optional) |

#### 4.5.2 Clearance Lifecycle
- Candidates self-declare clearances during registration
- SM/Recruiter can update clearance status (e.g., after verification with national authority)
- Profile catalogue specifies required clearance level per profile
- Matching engine: candidate without required clearance level = **auto-excluded** from match results
- Clearance expiry monitoring: alerts at 90, 60, and 30 days before expiry
- Dashboard widget: candidates with expiring clearances, candidates with pending clearance applications

#### 4.5.3 Clearance Application Tracking
- For candidates undergoing clearance application: track pipeline status
  - Application Submitted → Under Investigation → Granted / Denied
- Estimated timelines visible (3-18 months depending on level and country)
- SM can flag candidates as "clearance pending — available once granted" for advance matching

### 4.6 Contract & Rate Card Management

#### 4.6.1 Contract Entity
Each tenant can have one or more framework contracts:

| Field | Description | Example |
|-------|-------------|---------|
| Reference | Contract identifier | `ECTL-FWC-2026-01` |
| Title | Contract name | "EUROCONTROL IT Services Lot 2" |
| Lot Number | Lot within framework | Lot 2 |
| Start Date | Contract effective date | 2026-07-01 |
| End Date | Contract expiry date | 2030-06-30 |
| Max Value | Contract ceiling (EUR) | 5,000,000 |
| SLA Terms | Link to SLA configuration | See §4.11 |
| Profile Catalogue | Link to profiles | See §4.4 |
| Rate Card | Link to rate card | See §4.6.2 |
| Status | ACTIVE, EXPIRED, TERMINATED | ACTIVE |

#### 4.6.2 Rate Card
Rate cards define maximum daily-rate ceilings per profile and SFIA level:

| Profile Code | SFIA Level | Max Daily Rate (EUR) | Currency | Effective From | Effective To |
|-------------|-----------|---------------------|----------|---------------|-------------|
| SC-DEV-03 | 4 | 650 | EUR | 2026-07-01 | 2027-06-30 |
| SC-DEV-03 | 5 | 800 | EUR | 2026-07-01 | 2027-06-30 |
| SC-PM-01 | 5 | 850 | EUR | 2026-07-01 | 2027-06-30 |

#### 4.6.3 Rate Card Enforcement
- When a candidate is shortlisted for a demand linked to a contract:
  - System checks candidate's rate expectation against rate card ceiling for the profile + SFIA level
  - **Within ceiling**: proceeds normally
  - **Exceeds ceiling**: hard block — cannot be shortlisted without SM override
  - SM override requires: documented justification, triggers approval chain (SM → Admin)
  - Override logged in audit trail
- Margin calculation available to SM/Recruiter (not visible to client):
  - Margin = rate card ceiling − candidate cost rate
  - Margin % = margin / ceiling × 100
- Dashboard: margin overview across all demands in a contract

### 4.7 Demand Management

#### 4.7.1 Demand Creation
- Created by: Service Manager, Recruiter, or Customer
- **Must select from profile catalogue** (if demand is linked to a contract with a catalogue)
  - Profile selection pre-populates: required skills, experience level, certifications, languages, clearance, SFIA range
  - User can refine but cannot remove mandatory requirements from the profile
- Free-form demands allowed for contracts without a profile catalogue
- Required fields: title, description/JD, location, employment type, profile (if applicable), contract (if applicable)
- Optional fields: salary/rate range, start date, number of positions, department, remote policy
- AI JD enhancement available during creation (see §4.8)

#### 4.7.2 Demand Numbering
- Format: `{TENANT_PREFIX}-{SEQUENCE}` (e.g., `ACME-0001`, `ECTL-0042`)
- Tenant prefix: 2–6 character alphanumeric code, set during tenant creation
- Sequence: auto-incrementing per tenant, zero-padded to 4 digits
- Immutable once assigned

#### 4.7.3 External Demand ID (Atos Link)
- Free-text field: "External Demand ID"
- Editable by Service Manager only
- No format validation, no uniqueness enforcement
- Displayed alongside internal demand number in all views
- Searchable/filterable

#### 4.7.4 Replacement Demands
- SM can create a **replacement demand** when a position needs to be re-filled
- Replacement demand linked to the original demand it replaces
- Pre-populated from the same profile catalogue entry as the original
- Flagged as "Replacement" type with SLA countdown (see §4.11)
- SLA countdown starts from replacement demand creation date
- Follows the same lifecycle as a standard demand but with stricter time tracking

#### 4.7.5 Demand Lifecycle

States: `Draft → Open → Matching → Shortlisted → Interview → Offered → Filled → Closed`

| Transition | Allowed Roles | Approval Required |
|------------|---------------|:-----------------:|
| Draft → Open | Admin, SM, Recruiter, Customer | No |
| Open → Matching | Admin, SM, Recruiter | No |
| Matching → Shortlisted | Admin, SM, Recruiter | **Yes** (SM approves shortlist) |
| Shortlisted → Interview | Admin, SM, Customer | No |
| Interview → Offered | Admin, SM | No |
| Offered → Filled | Admin, SM | No |
| Filled → Closed | Admin, SM | No |
| Any → Closed (cancel) | Admin, SM | Configurable |

See BUSINESS_WORKFLOW.md for detailed state machine.

#### 4.7.6 Structured Rejection Reasons
At every stage where a candidate is rejected, a **structured reason** is required:

| Reason Code | Label | Applicable Stages |
|-------------|-------|-------------------|
| SKILLS_MISMATCH | Required skills not met | Matching, Shortlisting |
| EXPERIENCE_INSUFFICIENT | Below minimum experience | Matching, Shortlisting |
| CLEARANCE_NOT_MET | Security clearance not met | Matching, Shortlisting |
| RATE_EXCEEDS_CEILING | Rate above rate card ceiling | Shortlisting |
| AVAILABILITY_MISMATCH | Not available in required timeframe | Matching, Shortlisting |
| LANGUAGE_NOT_MET | Language requirements not met | Matching, Shortlisting |
| PROFILE_COMPLIANCE_FAIL | Mandatory profile requirements not met | Shortlisting |
| INTERVIEW_PERFORMANCE | Did not meet interview standards | Interview |
| ASSESSMENT_BELOW_THRESHOLD | Assessment score below passing threshold | Assessment |
| CLIENT_PREFERENCE | Client declined candidate | Shortlisting, Interview |
| CANDIDATE_WITHDREW | Candidate withdrew from process | Any |
| OTHER | Free-text reason required | Any |

- Required when rejecting at any stage
- Aggregated rejection analytics: most common reasons by profile, by tenant, over time
- Feeds into demand quality improvement and supply/demand intelligence

### 4.8 AI JD Enhancement

#### 4.8.1 Hybrid Editor Interface
- Rich text editor for the JD body (left panel)
- AI chat panel alongside (right panel)
- **Chat panel:** conversational interface for strategic edits ("make this more senior", "add cloud migration skills", "clarify remote policy")
- **Inline editor:** AI provides inline suggestions for grammar, clarity, missing sections, weak language
- **JD bias scanner:** AI flags gendered, ageist, or exclusionary language (e.g., "rockstar," "young dynamic team," "native English speaker")
- Powered by Claude API (Anthropic)

#### 4.8.2 Chat Persistence & Versioning
- Full conversation history persisted per demand
- Users can revisit and continue previous sessions
- Each accepted JD version is saved with timestamp and author
- JD version history viewable with diff between versions
- Revert to any previous version

#### 4.8.3 AI Capabilities
- Identify missing JD sections (responsibilities, qualifications, benefits, team context)
- Suggest ESCO-coded skill requirements based on role type
- Flag ambiguous language or unrealistic requirement combinations
- Improve readability and structure
- Generate JD from minimal input via guided conversation
- Cross-reference JD against profile catalogue requirements (flag if JD deviates from profile)

### 4.9 CV Verification

#### 4.9.1 Verification Checklist
Per candidate per demand submission, a structured verification checklist:

| Verification Item | Status | Evidence | Verified By | Date |
|-------------------|--------|----------|-------------|------|
| Education: MSc Computer Science, UCL | Verified | Diploma scan uploaded | J. Smith (Recruiter) | 2026-06-15 |
| Cert: AWS Solutions Architect | Verified | Cert #12345, expires 2027-03 | J. Smith | 2026-06-15 |
| Employment: TechCo, 2021-2024 | Reference obtained | Reference letter uploaded | J. Smith | 2026-06-16 |
| Language: English C1 | Self-declared | — | — | — |
| Clearance: NATO RESTRICTED | Pending verification | Application ref: BE-2026-789 | — | — |

#### 4.9.2 Verification Statuses
- **Verified**: evidence collected and confirmed
- **Self-declared**: candidate's claim, not independently verified
- **Pending verification**: verification in progress
- **Unverifiable**: unable to obtain evidence
- **Failed**: evidence contradicts claim

#### 4.9.3 AI Verification Assistance
- AI flags inconsistencies in parsed CV data (e.g., "10 years experience" but graduation year was 5 years ago)
- AI cross-references certification names against known certification databases
- Verification status visible on candidate profile and formatted CV
- Profile compliance check incorporates verification status (unverified mandatory items flagged as amber)

### 4.10 CV-to-Demand Matching

#### 4.10.1 Trigger
- Manual trigger only: Recruiter or SM clicks "Find Matches" on a demand
- Can be re-run at any time (new CVs may have been added)

#### 4.10.2 ESCO-Based Skill Matching
- Matching operates on ESCO skill codes, not raw text
- Required skills from JD/profile matched against candidate's ESCO-coded skills
- Semantic similarity: skills in the same ESCO branch score higher than exact-match-only systems
- Preferred skills scored separately (contribute to ranking but don't disqualify)

#### 4.10.3 Matching Dimensions
Full multi-dimensional scoring across:

| Dimension | Weight | Source | Hard Filter |
|-----------|--------|--------|:-----------:|
| Skills match (ESCO) | High | Parsed CV skills vs. JD/profile required skills | No |
| Experience level | High | Years of experience, SFIA level alignment | No |
| Profile compliance | High | Mandatory profile requirements met/unmet | **Yes** — fails = excluded |
| Security clearance | N/A | Required clearance present | **Yes** — missing = excluded |
| Language proficiency | N/A | Required CEFR levels met | **Yes** — below minimum = excluded |
| Location compatibility | Medium | Candidate location vs. demand location + remote policy | No |
| Availability | Medium | Candidate available date vs. demand start date | No |
| Education | Low-Medium | Degree level, field relevance | No |
| Certifications | Medium | Required certs present/absent | No |
| Rate alignment | Medium | Candidate rate vs. rate card ceiling | No |
| Career trajectory | Low | Progression pattern suggests fit for role level | No |

- Hard filters applied first (clearance, language, profile mandatory requirements)
- Remaining candidates scored on soft dimensions
- Composite weighted score (0–100)
- Each dimension scored individually and visible in match detail
- Configurable weights per tenant (SM can adjust)

#### 4.10.4 AI Explainability (EU AI Act Compliance)
Every match result includes a **human-readable narrative explanation**:

> "Candidate scored 85/100. Strong match on cloud architecture skills (AWS [ESCO:S5.2.1], Kubernetes [ESCO:S5.3.4]) and 8 years relevant experience exceeding the 5-year minimum (SFIA Level 5 confirmed). Gap: no Azure DevOps certification (preferred, not required). Location compatible: London, role is remote-friendly. Rate (€720/day) within ceiling (€800/day). Profile compliance: all mandatory requirements met."

- Explanation generated by Claude alongside score
- Stored in `match_results.explanation` for audit purposes
- Visible to Recruiter, SM, and Customer (on shortlisted candidates)
- Cost: ~$0.01 per candidate explanation — negligible

#### 4.10.5 Match Output
- Ranked list of candidates with composite scores
- Per-candidate breakdown of dimension scores + narrative explanation
- Highlight: strong matches (green), partial matches (amber), gaps (red)
- Top N candidates auto-shortlisted (N configurable per tenant, default: 10)
- Recruiter reviews auto-shortlist, can add/remove candidates
- **Comparison view**: select 2-4 candidates, see side-by-side table of all dimensions, qualifications, rates
- Shortlist submission to client triggers approval chain (Recruiter → SM)

### 4.11 SLA & KPI Management

#### 4.11.1 SLA Configuration
Per tenant per contract, configurable SLA targets:

| KPI | Description | Default Target | Measurement |
|-----|-------------|---------------|-------------|
| Time-to-fill | Business days from Open → Filled | 15 days | Per demand |
| Replacement time | Business days from replacement demand Open → Filled | 10 days | Per replacement demand |
| CV-to-interview ratio | CVs shortlisted per interview secured | 3:1 | Per demand |
| Fill rate | Demands filled / demands opened | 90% | Per quarter |
| Quality score | Client satisfaction rating (post-fill survey) | 4.0/5.0 | Per filled demand |

#### 4.11.2 SLA Tracking
- System automatically calculates KPI values from demand lifecycle timestamps
- Status per KPI: **On Track** (green), **At Risk** (amber, ≥80% of SLA consumed), **Breached** (red)
- Escalation alerts: notification to SM when KPI moves to At Risk or Breached

#### 4.11.3 Client-Visible SLA Dashboard
- Customer role sees SLA performance for their contract(s):
  - Current period performance vs. targets (gauges/charts)
  - Trend lines over time (monthly/quarterly)
  - Per-demand time-to-fill breakdown
  - Historical fill rates
- Exportable as PDF report for governance meetings
- SM/Admin see same data plus internal metrics (margin, cost, utilization)

#### 4.11.4 Recruitment Process Quality Survey
- Triggered when a demand transitions to "Filled":
  - Customer rates the recruitment process: timeliness, candidate quality, communication, overall satisfaction (1-5 scale)
  - Optional free-text feedback
  - Results stored per demand
- Aggregate quality scores feed into SLA dashboard and internal analytics

### 4.12 Interviews

#### 4.12.1 AI Interview Question Generation
- Input: JD + candidate CV + profile catalogue requirements
- Output: categorized question set
  - Technical questions (role-specific, aligned to profile required skills)
  - Behavioral questions (STAR format prompts)
  - Situational questions (scenario-based)
  - Culture fit questions
- Questions tagged by difficulty: Easy / Medium / Hard
- Recruiter/SM can edit, add, remove questions before finalizing

#### 4.12.2 Scorecard Templates
- AI generates structured scorecard per interview:
  - Criteria derived from profile requirements and JD
  - Rating scale per criterion (1–5)
  - Space for notes per criterion
  - Overall recommendation field
- Interviewers fill in scorecards after interview
- Scores aggregated across multiple interviewers
- Results stored per candidate per demand

#### 4.12.3 Interview Scheduling
- Manual date/time entry by Recruiter or SM
- Fields: date, time, duration, location/meeting link, interviewer(s), candidate, interview type
- Email notification sent to all participants
- Status tracking: Scheduled → Completed → Scored
- Architecture prepared for future calendar integration (Outlook/Google)

### 4.13 Assessments

#### 4.13.1 Configurable Test Builder
- Admin/Recruiter can create custom test templates
- Question types supported:
  - Multiple choice (single answer)
  - Multiple choice (multiple answers)
  - Free text (short answer)
  - Free text (long answer / essay)
  - Scenario/case-study
- AI suggests questions based on JD + profile catalogue — human curates final test
- Reusable question bank (global + tenant-scoped)
- Test settings: time limit, passing score, randomize order, show results to candidate

#### 4.13.2 In-App Test Taking
- Candidate logs in and sees assigned assessments on their dashboard
- Test interface:
  - Timer (countdown if time-limited)
  - Question navigation sidebar
  - Save progress (can return if allowed)
  - Auto-submit on timeout (enforced server-side)
- One attempt per assignment (configurable: allow retakes)

#### 4.13.3 AI Scoring
- MCQ: auto-scored immediately
- Free text / scenario: AI evaluates with score + reasoning
  - Claude API processes each answer against expected criteria
  - Provides confidence score and justification
  - Flags low-confidence scores (< 0.6) for human review
- Human override available on any AI-scored answer
- Final score: weighted composite of all question scores
- Results feed into candidate ranking for the demand

---

## 5. Dashboards & Reporting

### 5.1 Role-Specific Dashboards

#### Admin Dashboard
- System health: active tenants, total users, storage usage
- Cross-tenant metrics: total open demands, fill rate, avg time-to-fill
- AI system health: API costs, human override rates, model performance
- User activity: logins, active users by role
- Tenant comparison: pipeline size, conversion rates
- Security clearance alerts: expiring clearances across all candidates

#### Service Manager Dashboard
- **SLA Performance**: gauges for each KPI vs. target, with trend lines
- Tenant pipeline: demands by status (funnel visualization)
- Time-to-fill trends (line chart, filterable by date range)
- Rate card utilization: margin overview across demands
- Contract budget tracking: spent vs. ceiling
- Replacement demands: countdown timers
- Candidates with expiring clearances (assigned tenants)
- Demands requiring attention (stale, unmatched, SLA at risk)

#### Recruiter Dashboard
- Assigned demands: status overview with profile compliance indicators
- Matching queue: demands ready for matching
- Verification queue: pending CV verification items
- Recent match results
- Interview schedule (this week)
- Assessment results pending review
- Approval requests: pending items I initiated

#### Customer Dashboard
- **SLA Dashboard**: real-time performance for their contract(s)
- My demands: status overview with counts per state
- Shortlisted candidates awaiting review (with compliance status)
- Upcoming interviews
- Recently filled positions
- Pipeline funnel for their demands
- Process quality trend (satisfaction scores over time)

#### Candidate Dashboard
- Application status tracker
- Matched demands (with opt-in/decline)
- Upcoming interviews
- Pending assessments
- Profile completeness
- Verification status overview
- Security clearance status and expiry alerts

### 5.2 Analytics & Charts

- Pipeline funnel (demand states — bar/funnel chart)
- Time-to-fill distribution (histogram)
- Fill rate over time (line chart)
- SLA compliance trend (% on-track over months)
- Demands by tenant/contract (stacked bar)
- Match score distribution (histogram)
- Rejection reason analysis (bar chart by reason code, filterable by period)
- Skills supply vs. demand (gap chart)
- Assessment pass rates by profile
- Rate card utilization (margin distribution)

### 5.3 Exports

- CSV export for all data tables
- PDF export for:
  - Formatted candidate CVs (branded template)
  - Interview scorecards
  - Assessment results
  - Demand summaries with full lifecycle history
  - SLA performance reports
  - Profile compliance checklists
- **Bulk audit export** (Admin only): structured archive of all data for a tenant + date range for external auditors (see §8.4)
- Filterable date ranges on all reports

---

## 6. Notifications

### 6.1 Channels

- **In-app:** notification bell with unread count, notification inbox with history
- **Email:** HTML email for key events

### 6.2 Configurable Preferences

Each user can configure per-event notification preferences:

| Event | Default: In-App | Default: Email |
|-------|:---:|:---:|
| New demand created | ✓ | ✓ |
| Demand status changed | ✓ | ✓ |
| New match results available | ✓ | ✓ |
| Shortlist ready for review | ✓ | ✓ |
| Candidate approved/rejected | ✓ | ✓ |
| Interview scheduled | ✓ | ✓ |
| Assessment assigned | ✓ | ✓ |
| Assessment completed | ✓ | ✓ |
| Approval request pending | ✓ | ✓ |
| Approval decision made | ✓ | ✓ |
| SLA at risk | ✓ | ✓ |
| SLA breached | ✓ | ✓ |
| Security clearance expiring | ✓ | ✓ |
| Rate card ceiling exceeded (override needed) | ✓ | ✓ |
| Replacement demand created | ✓ | ✓ |
| New candidate registration | ✓ | ✗ |
| Quality survey requested | ✓ | ✓ |
| Password reset | — | ✓ |

### 6.3 Real-Time Delivery

- In-app notifications delivered via WebSocket (live badge update, no refresh needed)
- Email notifications sent asynchronously via background job

---

## 7. Real-Time Features

- **AI chat streaming:** Server-Sent Events (SSE) for streaming Claude API responses in the JD enhancement chat
- **Live notifications:** WebSocket connection for real-time notification badge updates
- Standard HTTP request/response for all other operations

---

## 8. Compliance & Regulatory

### 8.1 GDPR
- **Consent tracking**: candidates consent to data processing during registration; recorded with timestamp, IP, version
- **Right to be forgotten**: candidate can request data deletion; 30-day grace period; anonymizes audit records
- **Data model preparation**: supports future retention policies, DPA records, data export

### 8.2 EU AI Act (Annex III — High-Risk)
Recruitment AI is classified as **high-risk under EU AI Act Annex III, Category 4**. Full enforcement: **August 2, 2026**. The platform implements compliance from day one:

#### 8.2.1 AI Decision Log
Every AI-assisted decision is logged:

| Field | Description |
|-------|-------------|
| Timestamp | When the AI call was made |
| Feature | matching / cv_parsing / jd_enhancement / assessment_scoring / interview_questions |
| Model ID | e.g., `claude-sonnet-4-6` |
| Prompt Version | Hash of the prompt template used |
| Input Summary | Anonymized summary of input (demand ID, candidate count, etc.) |
| Output Summary | Score, recommendation, or content generated |
| Confidence | AI confidence score (where applicable) |
| Human Action | What the human did with the AI output (accepted / modified / rejected) |
| User ID | Who triggered and who reviewed |
| Tokens In / Out | Token counts for cost tracking |
| Latency | Response time in ms |

#### 8.2.2 Human Oversight
- No AI output can advance a candidate in the pipeline without explicit human review and approval
- Matching results: Recruiter must review and confirm shortlist
- Assessment scoring: AI scores flagged for human review at low confidence
- JD enhancement: all AI suggestions require human acceptance
- Human override always available and takes precedence over AI
- Override rate tracked as a proxy for AI quality

#### 8.2.3 AI Transparency
- AI System Card: public documentation per feature describing purpose, data used, limitations
- Candidates informed when AI is used in their evaluation (transparency disclosure in T&Cs)
- Per-tenant toggle: enable/disable individual AI features

#### 8.2.4 AI Model Monitoring
- Prompt version tracking: which model + prompt produced which output
- Performance trending: human override rate over time (rising rate = potential quality issue)
- Cost tracking per feature per tenant
- Model change alerts: when underlying model is updated, flag that historical comparisons may not be valid
- Quarterly review report: AI performance summary for compliance documentation

### 8.3 Audit Trail
- Critical actions logged: demand state changes, user login/logout, data deletions, role changes, tenant modifications, approval chain decisions, rate card overrides, AI decisions, CV verifications
- Log fields: timestamp, user_id, tenant_id, action, entity_type, entity_id, ip_address, details (before/after for changes)
- **Retention: 7 years** (configurable per tenant; default 7 years per EU institutional contract requirements)
- Tiered storage: hot (recent 12 months in primary DB), cold (older logs in Azure Blob as compressed JSON)
- Viewable by Admin via internal UI
- Searchable and filterable by date range, user, action type, entity

### 8.4 Bulk Audit Export
- Admin-only function for external auditor requests (DG DIGIT, OLAF, European Court of Auditors)
- Export all data for a specific tenant + contract + date range as a structured archive:
  - All demands with full lifecycle history and transition logs
  - All candidate profiles as submitted (not current version — point-in-time snapshots)
  - All match results with AI explanations and decision logs
  - All shortlist decisions with structured rejection reasons
  - All interview scorecards
  - All assessment results with AI scoring logs
  - All approval chain records
  - All CV verification checklists
  - All audit log entries
- Format: ZIP containing structured JSON + PDFs
- Triggered on-demand, logged as an audit event itself

---

## 9. Design System

**Exact reuse of EUROCONTROL design system from L1 Service Desk Automation project.**

### 9.1 Stack
- Shadcn/UI (Radix primitives) + Tailwind CSS + class-variance-authority
- CSS custom properties (HSL color space) for theming
- Dark mode support (class-based toggle)

### 9.2 Design Tokens

| Token | Light | Dark |
|-------|-------|------|
| Primary | `#003366` (HSL 210 100% 20%) | `#2990EA` (HSL 211 82% 54%) |
| Secondary | `#2990EA` (HSL 211 82% 54%) | `#003366` (HSL 210 100% 20%) |
| Accent | `#008dbb` (HSL 195 100% 37%) | `#008dbb` (unchanged) |
| Background | HSL 210 20% 98% | HSL 210 50% 6% |
| Success | `#1f8851` (HSL 152 69% 31%) | same |
| Warning | `#ffb81c` (HSL 38 92% 50%) | same |
| Danger | `#ff4d4d` (HSL 0 84% 60%) | same |

### 9.3 Typography
- Font: **Exo** (weights 300, 400, 500, 600, 700)
- Fallbacks: system-ui, -apple-system, sans-serif
- Headings: Exo 600

### 9.4 Layout Constants
- Sidebar width: 260px
- Header height: 56px
- Border radius: 0.375rem (6px)
- Container max-width: 1400px (centered, 2rem padding)

### 9.5 Component Library
- 17+ pre-built Shadcn components: Button, Card, Badge, Dialog, Accordion, Dropdown Menu, Select, Sheet, Tabs, Input, Label, Progress, Switch, Separator, Skeleton, Tooltip, Avatar, Collapsible
- Custom EC utility classes: `ec-badge-high`, `ec-badge-medium`, `ec-badge-low`, `ec-nav-active`, `ec-card-interactive`, `ec-header-gradient`, `ec-accent-line`

### 9.6 Responsiveness
- Desktop-only target (no mobile optimization required)
- Minimum supported viewport: 1280px wide

---

## 10. Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite + TypeScript + Tanstack Router |
| UI Components | Shadcn/UI + Radix + Tailwind CSS |
| Backend | Python FastAPI |
| Database | PostgreSQL 16 (with RLS) |
| File Storage | Azure Blob Storage |
| AI Provider | Anthropic Claude API |
| Skills Taxonomy | ESCO API (European Commission) |
| Seniority Framework | SFIA (Skills Framework for the Information Age) |
| Real-Time | WebSocket (notifications) + SSE (AI chat streaming) |
| Email | SMTP (configurable provider) |
| Deployment | Docker Compose on Azure VM |
| Auth | JWT (username/password), Entra ID deferred |

---

## 11. Non-Functional Requirements

### 11.1 Performance
- Page load: < 2 seconds on desktop broadband
- API response: < 500ms for CRUD operations
- AI matching: < 30 seconds for 1000 candidate pool
- AI chat response: streaming starts within 2 seconds
- Profile compliance check: < 2 seconds per candidate

### 11.2 Security
- All traffic over HTTPS (TLS 1.3)
- Passwords hashed with bcrypt (cost factor 12)
- JWT tokens: 15-minute access, 7-day refresh
- CORS restricted to known origins
- SQL injection prevention via parameterized queries + ORM
- XSS prevention via React default escaping + CSP headers
- Rate limiting on all public endpoints
- File upload validation (type, size, virus scan)

### 11.3 Availability
- Target: 99.5% uptime (single VM deployment)
- Automated daily database backups (Azure managed)
- Application-level health check endpoint

### 11.4 Audit & Retention
- Audit log retention: **7 years** (configurable per tenant)
- Tiered storage: 12 months hot (PostgreSQL), remainder cold (Azure Blob compressed JSON)
- AI decision logs: same 7-year retention
- CV files: retained while candidate is active; anonymized/deleted per GDPR on deletion request
- Cold audit logs queryable via Admin export function (not real-time search)

### 11.5 Scalability Path
- Designed for 5–20 tenants, hundreds of users, tens of thousands of CVs
- Architecture supports migration to Azure Container Apps or AKS when scale demands
- Stateless backend enables horizontal scaling behind load balancer

---

## 12. Out of Scope (Phase 1)

- Microsoft Entra ID SSO (architecture prepared, implementation deferred)
- Calendar integration (Outlook/Google)
- API integration with Atos tool (manual field only)
- Mobile/tablet optimization
- Self-service tenant registration
- Billing/metering per tenant
- Video interview hosting
- Bias detection / adverse impact analysis (on hold — future phase)
- Active placement / post-hire tracking (handled by external EUROCONTROL system)
- Timesheet / hours tracking (handled by external system)
- Automated reference checking (API integration with Xref/Checkster)
- Multi-language / i18n support
- Candidate sourcing from external job boards
