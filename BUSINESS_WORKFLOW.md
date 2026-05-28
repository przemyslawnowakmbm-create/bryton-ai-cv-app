# Bryton AI CV App — Business Workflow Design

**Version:** 2.0
**Date:** 2026-05-28
**Status:** Draft
**Change log:** v2.0 adds Profile Catalogue workflow, Replacement Pipeline, SLA Monitoring, CV Verification, Approval Chain, Rate Card Enforcement, Security Clearance lifecycle. Updated matching with ESCO + explainability. Updated permission matrix.

---

## 1. End-to-End Process Overview

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                     BRAYTON AI CV APP — E2E RECRUITMENT GOVERNANCE                      │
│                                                                                        │
│  SETUP PHASE (once per contract):                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐            │
│  │  Tenant   │──▶│ Contract │──▶│  Rate    │──▶│ Profile  │──▶│   SLA    │            │
│  │ Onboard  │   │  Setup   │   │  Card    │   │ Catalogue│   │  Config  │            │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘            │
│                                                                                        │
│  RECRUITMENT PHASE (per demand):                                                       │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐            │
│  │  Demand  │──▶│   AI JD  │──▶│    AI    │──▶│ Profile  │──▶│  Rate    │            │
│  │ Creation │   │ Enhance  │   │ Matching │   │Compliance│   │  Card    │            │
│  │(profile) │   │          │   │ + ESCO   │   │  Check   │   │  Check   │            │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘            │
│                                                                      │                 │
│                                                                      ▼                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐            │
│  │  Hire /  │◀──│  Offer   │◀──│Interview │◀──│Assessment│◀──│ Shortlist│            │
│  │  Close   │   │          │   │+Scorecard│   │  + AI    │   │ Approval │            │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘            │
│       │                                                                                │
│       ▼                                                                                │
│  ┌──────────┐   ┌──────────┐                                                          │
│  │ Quality  │   │   SLA    │  ← tracked throughout                                    │
│  │  Survey  │   │ Metrics  │                                                          │
│  └──────────┘   └──────────┘                                                          │
│                                                                                        │
│  PARALLEL TRACKS:                                                                      │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                               │
│  │  Candidate   │──▶│  CV Upload   │──▶│  Clearance   │  (feeds into matching pool)   │
│  │ Registration │   │  + AI Parse  │   │  + Languages │                               │
│  └──────────────┘   └──────────────┘   └──────────────┘                               │
│                                                                                        │
│  REPLACEMENT TRACK:                                                                    │
│  ┌──────────────┐   ┌──────────────────────────────────────┐                          │
│  │  Replacement │──▶│  Same recruitment pipeline as above  │  (with SLA countdown)    │
│  │  Triggered   │   │  (pre-populated from profile)        │                          │
│  └──────────────┘   └──────────────────────────────────────┘                          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Workflow 1: Tenant & Contract Setup

### 2.1 Process Flow

```
Admin                          System                        Customer Admin
  │                               │                               │
  │── Create tenant ────────────▶│                               │
  │   (name: "EUROCONTROL",      │── Provision tenant ──────────▶│
  │    prefix: "ECTL")           │   - Create DB records         │
  │                               │   - Initialize sequence       │
  │── Create contract ─────────▶│                               │
  │   (ref: ECTL-FWC-2026-01,   │── Store contract              │
  │    lot: 2, dates, max value) │                               │
  │                               │                               │
  │── Upload rate card ─────────▶│                               │
  │   (profile × SFIA level ×   │── Store rate card entries     │
  │    max daily rate)           │── Validate: no gaps, no       │
  │                               │   duplicates                  │
  │                               │                               │
  │── Create profile catalogue ─▶│                               │
  │   (profiles with mandatory   │── Store profiles +            │
  │    requirements, ESCO skills,│   requirements                │
  │    SFIA ranges, clearance,   │── Link to rate card           │
  │    languages)                │                               │
  │                               │                               │
  │── Configure SLA targets ───▶│                               │
  │   (time-to-fill: 15 days,   │── Store SLA config            │
  │    replacement: 10 days,     │                               │
  │    fill rate: 90%)           │                               │
  │                               │                               │
  │── Create customer user ────▶│                               │
  │   (email, name, role)        │── Send invite email ─────────▶│
  │                               │                               │── Set password
  │                               │                               │── Configure users
  │                               │                               │── Set notification prefs
  │                               │◀── Tenant operational ───────│
```

### 2.2 Validation Rules

- Tenant prefix: 2–6 alphanumeric, unique
- Contract dates: end > start, no overlapping active contracts with same lot
- Rate card: every profile in the catalogue must have at least one rate card entry
- Profile catalogue: ESCO skill codes validated against local ESCO cache
- SLA config: all targets must be positive values
- Invite links expire after 72 hours

---

## 3. Workflow 2: Candidate Registration & CV Upload

### 3.1 Process Flow

```
Candidate                      System                         AI (Claude)
  │                               │                               │
  │── Register ────────────────▶│                               │
  │   (name, email, password)    │── Create account              │
  │                               │── Send verification email     │
  │── Verify email ────────────▶│── Activate account            │
  │                               │                               │
  │── Upload CV ───────────────▶│                               │
  │   (PDF/DOCX, max 10MB)      │── Virus scan                  │
  │                               │── Store in Azure Blob         │
  │                               │── Extract text (pdfplumber/   │
  │                               │   python-docx)               │
  │                               │── Send for parsing ─────────▶│
  │                               │                               │── Parse CV
  │                               │                               │── Map skills → ESCO
  │                               │                               │── Infer CEFR levels
  │                               │                               │── Suggest SFIA level
  │                               │◀── Structured data ──────────│
  │                               │── Log AI decision             │
  │                               │── Store parsed data           │
  │                               │                               │
  │◀── Review parsed profile ────│                               │
  │                               │                               │
  │── Correct/complete profile ─▶│                               │
  │   - Fix AI-inferred CEFR     │── Update profile              │
  │   - Add availability date    │── Recalculate completeness    │
  │   - Set rate expectation     │                               │
  │   - Set visibility prefs     │                               │
  │                               │                               │
  │── Add security clearances ──▶│                               │
  │   (level, type, authority,   │── Store clearances            │
  │    dates, status)            │── Set expiry alerts           │
  │                               │                               │
  │── Add language proficiencies▶│                               │
  │   (correct AI-inferred or    │── Store/update languages      │
  │    add missing ones)         │                               │
  │                               │                               │
  │   ✓ Candidate in global pool │                               │
```

### 3.2 Profile Completeness Scoring

| Field | Weight | Required |
|-------|--------|----------|
| Full name | 5% | Yes |
| Email | 5% | Yes |
| Phone | 5% | No |
| Location | 5% | No |
| CV uploaded | 15% | No |
| Work experience (parsed) | 15% | No |
| Skills (ESCO-mapped) | 10% | No |
| Education (parsed) | 5% | No |
| SFIA level (confirmed) | 5% | No |
| Availability date | 5% | No |
| Rate expectation | 5% | No |
| Security clearances | 5% | No |
| Language proficiencies | 5% | No |
| Visibility preferences | 5% | No |
| Consent given | 5% | Yes |

---

## 4. Workflow 3: Demand Creation & JD Enhancement

### 4.1 Process Flow

```
Customer/SM/Recruiter          System                         AI (Claude)
  │                               │                               │
  │── Select profile from ──────▶│                               │
  │   catalogue (e.g., SC-DEV-03)│── Pre-populate demand form:   │
  │                               │   - Title from profile        │
  │                               │   - Required skills (ESCO)    │
  │                               │   - SFIA level range          │
  │                               │   - Required certs            │
  │                               │   - Required languages (CEFR) │
  │                               │   - Required clearance        │
  │                               │   - Rate ceiling from card    │
  │                               │                               │
  │── Refine demand details ────▶│                               │
  │   (location, start date,     │── Assign demand number        │
  │    remote policy, positions) │   (e.g., ECTL-0001)           │
  │                               │── Status = DRAFT              │
  │                               │── Save JD v1                  │
  │                               │── Link to contract + profile  │
  │                               │                               │
  │── Open AI Enhancement ──────▶│                               │
  │                               │── Create chat session         │
  │                               │                               │
  │── Chat: "add cloud skills"──▶│                               │
  │                               │── Send to Claude (system      │
  │                               │   prompt + chat history +     │
  │                               │   JD + profile requirements)─▶│
  │                               │                               │── Analyze JD
  │                               │                               │── Check vs profile
  │◀── Streaming response ───────│◀── SSE stream ────────────────│
  │                               │── Log AI decision             │
  │                               │                               │
  │   BIAS DETECTION:            │                               │
  │── (typing in editor) ───────▶│                               │
  │                               │── Debounced send to Haiku ──▶│
  │                               │                               │── Flag: "young dynamic
  │◀── ⚠ "Gendered language     │◀── Bias flags ────────────────│   team" → ageist
  │      detected: 'rockstar'"   │                               │
  │                               │                               │
  │── Accept JD version ────────▶│── Save JD v2                  │
  │                               │── Update demand.description   │
  │                               │                               │
  │── Transition to Open ───────▶│── Status = OPEN               │
  │                               │── SLA clock starts            │
  │                               │── Log transition              │
  │                               │── Notify: SM, Recruiter       │
```

### 4.2 JD Cross-Reference with Profile

When creating/editing a JD for a profile-linked demand, the AI chat system prompt includes:

```
Profile requirements for SC-DEV-03:
- Mandatory skills: Java [ESCO:S1.2.3], Spring Boot [ESCO:S1.2.4], Microservices [ESCO:S1.5.1]
- Min experience: 8 years
- SFIA: 4-5
- Clearance: NATO RESTRICTED
- Languages: English B2+, French B1+

Ensure the JD aligns with these requirements. Flag if the user's edits
would create a mismatch with the profile definition.
```

---

## 5. Workflow 4: Demand Lifecycle State Machine

### 5.1 State Diagram

```
                    ┌────────────────────────────────────────┐
                    │                CLOSED                   │
                    │          (terminal state)               │
                    └────────────────────────────────────────┘
                      ▲         ▲         ▲         ▲     ▲
                      │         │         │         │     │
                  (cancel)  (cancel)  (cancel)  (cancel)  │
                      │         │         │         │     │
┌────────┐     ┌──────┴──┐  ┌──┴─────┐  ┌┴────────┐  ┌──┴──────┐  ┌────────┐
│        │     │         │  │        │  │         │  │         │  │        │
│ DRAFT  │────▶│  OPEN   │─▶│MATCHING│─▶│SHORTLIST│─▶│INTERVIEW│─▶│OFFERED │
│        │     │  (SLA   │  │        │  │   ED    │  │         │  │        │
│        │     │  starts)│  │        │  │(approval│  │         │  │        │
└────────┘     └─────────┘  └────────┘  │  gate)  │  └─────────┘  └───┬────┘
                                        └─────────┘                    │
                                                                       ▼
                                                                  ┌────────┐
                                                                  │ FILLED │
                                                                  │(survey)│
                                                                  └───┬────┘
                                                                      │
                                                                      ▼
                                                                  ┌────────┐
                                                                  │ CLOSED │
                                                                  └────────┘
```

### 5.2 Transition Rules

| # | From | To | Allowed Roles | Approval Gate | Preconditions | Side Effects |
|---|------|----|---------------|:-------------:|---------------|--------------|
| T1 | Draft | Open | Admin, SM, Recruiter, Customer | No | description not empty | SLA clock starts; notify SM + Recruiter |
| T2 | Open | Matching | Admin, SM, Recruiter | No | required_skills not empty OR profile linked | Triggers AI matching pipeline |
| T3 | Matching | Shortlisted | Admin, SM, Recruiter | **Yes** (SM approves shortlist before client sees) | match_results exist; shortlist reviewed | Notify Customer |
| T4 | Shortlisted | Interview | Admin, SM, Customer | No | ≥1 shortlist entry approved by customer | Create interview slots; notify Recruiter |
| T5 | Interview | Offered | Admin, SM | No | ≥1 interview scored | Notify Customer + Candidate |
| T6 | Offered | Filled | Admin, SM | No | — | Trigger quality survey; update SLA metrics; notify all |
| T7 | Filled | Closed | Admin, SM | No | — | Archive; final SLA snapshot |
| T8 | Any → Closed | Admin, SM | Configurable | cancellation_reason provided | Notify all parties |

### 5.3 SLA Clock

- **Starts** when demand transitions to Open (T1)
- **Stops** when demand transitions to Filled (T6) or Closed (T7/T8)
- **Business days** counted (excludes weekends; holidays configurable per tenant)
- SLA status recalculated on every transition:
  - Green: < 80% of target consumed
  - Amber: 80-99% of target consumed
  - Red: ≥ 100% (breached)

### 5.4 Transition Validation

```python
TRANSITION_RULES = {
    ("draft", "open"): {
        "allowed_roles": ["admin", "sm", "recruiter", "customer"],
        "approval_required": False,
        "preconditions": ["demand.description is not empty"],
    },
    ("open", "matching"): {
        "allowed_roles": ["admin", "sm", "recruiter"],
        "approval_required": False,
        "preconditions": ["demand.required_skills is not empty OR demand.profile_id is not null"],
    },
    ("matching", "shortlisted"): {
        "allowed_roles": ["admin", "sm", "recruiter"],
        "approval_required": True,  # SM must approve shortlist
        "preconditions": ["match_results exist for this demand", "shortlist has been reviewed"],
    },
    ("shortlisted", "interview"): {
        "allowed_roles": ["admin", "sm", "customer"],
        "approval_required": False,
        "preconditions": ["at least 1 shortlist entry with status=approved"],
    },
    ("interview", "offered"): {
        "allowed_roles": ["admin", "sm"],
        "approval_required": False,
        "preconditions": ["at least 1 interview with status=scored"],
    },
    ("offered", "filled"): {
        "allowed_roles": ["admin", "sm"],
        "approval_required": False,
        "preconditions": [],
    },
    ("filled", "closed"): {
        "allowed_roles": ["admin", "sm"],
        "approval_required": False,
        "preconditions": [],
    },
    ("*", "closed"): {
        "allowed_roles": ["admin", "sm"],
        "approval_required": "configurable",
        "preconditions": ["cancellation_reason is provided"],
    },
}
```

---

## 6. Workflow 5: AI Matching (with ESCO + Explainability)

### 6.1 Process Flow

```
Recruiter/SM                   System                         AI (Claude)
  │                               │                               │
  │── "Find Matches" on ────────▶│                               │
  │    demand ECTL-0001          │                               │
  │                               │── Transition: Open → Matching │
  │                               │                               │
  │                               │── PHASE 1: Hard Filters       │
  │                               │   Fetch all visible candidates│
  │                               │   Filter OUT:                 │
  │                               │   ✗ Missing required clearance│
  │                               │   ✗ Below min language CEFR   │
  │                               │   ✗ Below min experience yrs  │
  │                               │   → Reduced candidate pool    │
  │                               │                               │
  │                               │── PHASE 2: AI Scoring         │
  │                               │   For each batch of 10-20:    │
  │                               │   Send to Claude: ───────────▶│
  │                               │   - JD + profile (system ctx) │── Score each
  │                               │   - ESCO-coded skills         │   candidate on
  │                               │   - Candidate batch (parsed)  │   all dimensions
  │                               │   - Scoring dimensions        │── Generate
  │                               │   - Weight config             │   explanations
  │                               │   ◀── Scores + explanations ──│
  │                               │   Log AI decisions            │
  │                               │                               │
  │                               │── PHASE 3: Profile Compliance │
  │                               │   For each scored candidate:  │
  │                               │   Run compliance check vs     │
  │                               │   profile catalogue            │
  │                               │   Attach checklist to result  │
  │                               │                               │
  │                               │── PHASE 4: Rate Card Check    │
  │                               │   For each scored candidate:  │
  │                               │   Check rate vs ceiling       │
  │                               │   Flag if exceeds             │
  │                               │                               │
  │                               │── Aggregate, rank, auto-      │
  │                               │   shortlist top N             │
  │                               │                               │
  │◀── Match results ready ──────│                               │
  │                               │                               │
  │── Review results: ──────────▶│                               │
  │   Each candidate shows:      │                               │
  │   - Score (85/100)           │                               │
  │   - Dimension breakdown      │                               │
  │   - AI explanation (text)    │                               │
  │   - Profile compliance ✓/✗   │                               │
  │   - Rate card status ✓/⚠     │                               │
  │                               │                               │
  │── Adjust shortlist ─────────▶│                               │
  │   - Remove candidate C       │── Update shortlist_entries    │
  │     (reason: RATE_EXCEEDS)   │   (structured rejection)      │
  │   - Add candidate D (manual) │                               │
  │                               │                               │
  │── Submit shortlist ─────────▶│                               │
  │                               │── Create approval request    │
  │                               │── Notify SM for approval      │
  │                               │                               │
SM │◀── Approval request ────────│                               │
  │── Approve shortlist ────────▶│                               │
  │                               │── Transition: Matching →      │
  │                               │   Shortlisted                 │
  │                               │── Notify Customer             │
```

### 6.2 Matching Dimensions

```
┌─────────────────────────────────────────────────────────────────┐
│  MATCH RESULT — Senior Java Developer (SC-DEV-03)               │
│  Demand: ECTL-0001 | Candidate: John Smith                      │
│                                                                  │
│  HARD FILTERS:                                                   │
│  ✓ Clearance: NATO RESTRICTED (active, expires 2028-03)         │
│  ✓ Language: English C1 (req: B2+), French B1 (req: B1+)       │
│  ✓ Experience: 10 years (req: 8+)                               │
│                                                                  │
│  SCORED DIMENSIONS:                    Score    Weight           │
│  Skills Match (ESCO)      ██████████████████████████ 90  × 25%  │
│  Experience Level         ████████████████████████ 82    × 20%  │
│  Location Compatibility   ██████████████████████████ 88  × 15%  │
│  Availability             ██████████████████████████████ 100 × 10%│
│  Education                ██████████████████ 70          × 10%  │
│  Certifications           ██████████████████████ 80      × 10%  │
│  Rate Alignment           ████████████████████████ 85    × 5%   │
│  Career Trajectory        ██████████████████ 70          × 5%   │
│                                                                  │
│  COMPOSITE: 84.5 / 100                                          │
│                                                                  │
│  PROFILE COMPLIANCE:                                             │
│  ✓ Java [ESCO:S1.2.3] — 8 years                                │
│  ✓ Spring Boot [ESCO:S1.2.4] — 5 years                         │
│  ✓ Microservices [ESCO:S1.5.1] — 4 years                       │
│  ✓ Oracle Java SE Certified — verified, expires 2027-06         │
│  ⚠ Kubernetes [ESCO:S5.3.4] — preferred, not on CV             │
│                                                                  │
│  RATE CARD: ✓ Within ceiling                                     │
│  Candidate: €720/day | Ceiling: €800/day (SFIA 5)              │
│  Margin: €80/day (10.0%)                                        │
│                                                                  │
│  AI EXPLANATION:                                                 │
│  "Strong match. 10 years of Java experience with Spring Boot    │
│   and microservices architecture aligns well with SC-DEV-03     │
│   requirements. SFIA Level 5 confirmed by track record of       │
│   leading technical teams and making architectural decisions.    │
│   Minor gap: Kubernetes is listed as preferred but candidate    │
│   has Docker/container experience which is closely related      │
│   [ESCO:S5.3 branch]. All mandatory requirements met.           │
│   Available from 2026-07-15, within demand start window."       │
│                                                                  │
│  [✓ Shortlist]  [✗ Reject (select reason)]  [📋 Comparison]    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Workflow 6: Approval Chain

### 7.1 Generic Approval Flow

```
Initiator                      System                         Approver
  │                               │                               │
  │── Trigger gated action ─────▶│                               │
  │   (e.g., submit shortlist)   │── Check: approval required?   │
  │                               │   YES (per tenant config)     │
  │                               │                               │
  │                               │── Create approval_request:    │
  │                               │   - action_type: shortlist    │
  │                               │   - justification (required)  │
  │                               │   - context_data (shortlist)  │
  │                               │   - status: PENDING           │
  │                               │                               │
  │                               │── Notify approver ───────────▶│
  │                               │   (in-app + email)            │
  │                               │                               │
  │                               │                    ┌──────────┤
  │                               │                    │ Review   │
  │                               │                    │ context  │
  │                               │                    │ data     │
  │                               │                    └──────────┤
  │                               │                               │
  │                               │              ┌── APPROVE ─────│
  │                               │              │   (optional     │
  │                               │              │    comment)     │
  │                               │◀─────────────┘                │
  │                               │── Execute action              │
  │                               │── Log approval in audit       │
  │◀── Notification: approved ───│                               │
  │                               │                               │
  │                     OR:       │                               │
  │                               │              ┌── REJECT ──────│
  │                               │              │   (reason       │
  │                               │              │    required)    │
  │                               │◀─────────────┘                │
  │                               │── Log rejection in audit      │
  │◀── Notification: rejected ───│                               │
  │   (with reason)              │                               │
```

### 7.2 Approval Gates

| Gate | Action | Initiator | Approver | Context Data |
|------|--------|-----------|----------|-------------|
| Shortlist submission | Shortlist visible to client | Recruiter | SM | Candidate list, compliance status, match scores |
| Rate override | Shortlist candidate above ceiling | Recruiter/SM | SM/Admin | Candidate rate, ceiling, margin impact, justification |
| Profile non-compliance | Shortlist candidate with failed mandatory requirement | Recruiter | SM | Failed requirement(s), mitigation rationale |
| Demand cancellation | Cancel demand (configurable) | SM | Admin | Demand details, reason, impact |
| Profile catalogue change | Modify active profile | SM | Admin | Before/after diff, affected demands |

### 7.3 Approval SLA
- Approval requests have a configurable timeout (default: 48 business hours)
- Escalation: if not acted on within timeout, escalate to Admin
- Pending approvals visible on approver's dashboard with aging indicator

---

## 8. Workflow 7: CV Verification

### 8.1 Process Flow

```
Recruiter                      System                         Verification
  │                               │                               │
  │── Candidate shortlisted ────▶│                               │
  │   for ECTL-0001             │── Auto-create verification    │
  │                               │   checklist from profile      │
  │                               │   requirements:               │
  │                               │   - Education items           │
  │                               │   - Certification items       │
  │                               │   - Employment items          │
  │                               │   - Language items            │
  │                               │   - Clearance items           │
  │                               │                               │
  │◀── Verification checklist ───│                               │
  │    created (15 items)        │                               │
  │                               │                               │
  │   For each item:             │                               │
  │── Collect evidence ─────────▶│                               │
  │   (upload diploma scan,      │── Store in Azure Blob         │
  │    cert screenshot, etc.)    │── Link to verification item   │
  │                               │                               │
  │── Mark item as verified ────▶│                               │
  │   or failed                  │── Update item status          │
  │                               │── Recalculate overall status  │
  │                               │                               │
  │   AI ASSISTANCE:             │                               │
  │                               │── AI flags inconsistencies:   │
  │                               │   ⚠ "CV says 10yr exp but    │
  │                               │     graduation was 2021"      │
  │                               │   ⚠ "Cert 'AWS SAA' — check  │
  │                               │     if version is current"    │
  │                               │                               │
  │── All items checked ────────▶│                               │
  │                               │── Overall status:             │
  │                               │   FULLY_VERIFIED (all green)  │
  │                               │   PARTIALLY_VERIFIED (some    │
  │                               │     self-declared)            │
  │                               │   VERIFICATION_FAILED (any    │
  │                               │     failed items)             │
  │                               │                               │
  │                               │── Verification status shown   │
  │                               │   on formatted CV and         │
  │                               │   candidate profile           │
```

### 8.2 Verification Items by Type

| Type | Auto-Generated From | Evidence Expected |
|------|-------------------|-------------------|
| EDUCATION | Parsed CV + profile min_education | Diploma/transcript scan |
| CERTIFICATION | Profile required_certifications | Certificate image, reference number |
| EMPLOYMENT | Parsed CV work history entries | Reference letter, LinkedIn confirmation |
| LANGUAGE | Profile required_languages | Test result, self-declaration accepted |
| CLEARANCE | Profile required_clearance | Clearance reference number, national authority confirmation |

---

## 9. Workflow 8: Shortlist Review (Customer)

### 9.1 Process Flow

```
Customer                       System                         Recruiter/SM
  │                               │                               │
  │◀── Notification: ────────────│                               │
  │   "Shortlist ready for       │                               │
  │    ECTL-0001"                │                               │
  │                               │                               │
  │── View shortlist ───────────▶│                               │
  │   Each candidate shows:      │                               │
  │   - Name & profile           │                               │
  │   - Match score + breakdown  │                               │
  │   - AI explanation           │                               │
  │   - Profile compliance ✓/⚠   │                               │
  │   - Verification status      │                               │
  │   - SFIA level + evidence    │                               │
  │   - Clearance status         │                               │
  │   - Languages (CEFR)         │                               │
  │   - Formatted CV (download)  │                               │
  │                               │                               │
  │── For each candidate:        │                               │
  │   ┌───────────────────────┐  │                               │
  │   │ ✓ Approve (interview) │──▶── status = approved           │
  │   │ ✗ Reject (reason req) │──▶── status = rejected           │
  │   │   [CLIENT_PREFERENCE] │  │   rejection logged            │
  │   │ 💬 Request info       │──▶── Notify Recruiter ──────────▶│
  │   └───────────────────────┘  │                               │
  │                               │                               │
  │── Compare 2-4 candidates ───▶│                               │
  │   (side-by-side table)       │                               │
```

---

## 10. Workflow 9: Interview Process

### 10.1 Process Flow

```
Recruiter/SM                   System                         AI (Claude)
  │                               │                               │
  │── Schedule interview ───────▶│── Create interview record     │
  │   (date, time, duration,     │── Notify: interviewers,       │
  │    location, interviewers)   │   candidate, customer         │
  │                               │                               │
  │── Generate questions ───────▶│                               │
  │                               │── Send JD + CV + profile ───▶│
  │                               │   requirements to Claude     │── Generate
  │                               │                               │   questions
  │                               │◀── Question set ──────────────│
  │                               │── Log AI decision             │
  │◀── Review & edit questions ──│                               │
  │── Finalize questions ───────▶│── Generate scorecard template │
  │                               │   (criteria from profile)    │
  │                               │                               │

  ... (interview happens offline) ...

Interviewer                    System
  │                               │
  │── Fill scorecard ───────────▶│── Store scorecard             │
  │                               │── If all interviewers scored: │
  │                               │   - Aggregate scores          │
  │                               │   - Status = SCORED           │
  │                               │   - Notify SM                 │
```

---

## 11. Workflow 10: Assessment Process

### 11.1 Test Creation

```
Recruiter/SM                   System                         AI (Claude)
  │                               │                               │
  │── Open Test Builder ────────▶│                               │
  │── Select "Generate from JD" ▶│── Send JD + profile + config─▶│
  │                               │                               │── Generate questions
  │                               │◀── Suggested questions ───────│
  │                               │── Log AI decision             │
  │◀── Review suggestions ───────│                               │
  │── Curate: accept/edit/add ──▶│── Store template + questions  │
  │── Assign to candidates ────▶│── Create assignments          │
  │                               │── Notify candidates           │
```

### 11.2 Test Taking

```
Candidate                      System                         AI (Claude)
  │── Start assessment ─────────▶│── Record started_at           │
  │                               │── Start timer (server-side)  │
  │◀── Questions served ─────────│                               │
  │── Answer & submit ──────────▶│── Auto-score MCQ              │
  │                               │── For free text:             │
  │                               │   Send to Claude ────────────▶│
  │                               │                               │── Evaluate
  │                               │◀── Score + reasoning ─────────│
  │                               │── Log AI decisions            │
  │                               │── Calculate composite         │
  │                               │── Status = SCORED             │
  │                               │── Notify Recruiter/SM         │
```

---

## 12. Workflow 11: Replacement Pipeline

### 12.1 Process Flow

```
SM                             System                         Notifications
  │                               │                               │
  │── Receives notice: position  │                               │
  │   needs re-filling (from     │                               │
  │   external ECTL system)      │                               │
  │                               │                               │
  │── Create Replacement ───────▶│                               │
  │   Demand for ECTL-0001       │                               │
  │                               │── Create new demand:          │
  │                               │   - demand_type = 'replacement'│
  │                               │   - replaces_demand_id =      │
  │                               │     ECTL-0001                 │
  │                               │   - Pre-populate from same    │
  │                               │     profile (SC-DEV-03)       │
  │                               │   - Assign number: ECTL-0042 │
  │                               │                               │
  │                               │── SLA countdown starts:       │
  │                               │   replacement_time = 10 days  │
  │                               │                               │
  │                               │── Notify: Recruiter ─────────▶│
  │                               │   "Replacement demand created │
  │                               │    ECTL-0042 — 10 days SLA"  │
  │                               │                               │
  │   SAME PIPELINE AS STANDARD: │                               │
  │   Open → Matching →          │                               │
  │   Shortlisted → Interview →  │                               │
  │   Offered → Filled           │                               │
  │                               │                               │
  │   BUT with SLA dashboard:    │                               │
  │   ┌───────────────────────┐  │                               │
  │   │ ECTL-0042 (REPLACE)   │  │                               │
  │   │ Day 3 of 10           │  │                               │
  │   │ Status: Matching      │  │                               │
  │   │ SLA: ██████░░░░ 30%   │  │                               │
  │   │ [ON TRACK]            │  │                               │
  │   └───────────────────────┘  │                               │
```

### 12.2 Replacement Rules

- Replacement demand inherits: profile, contract, SFIA range, required skills, clearance requirements
- SM can modify the JD (different focus, updated requirements)
- SLA tracks replacement-specific target (default: 10 business days)
- Dashboard flags replacement demands prominently (red badge, countdown)
- Client SLA view shows replacement metrics separately

---

## 13. Workflow 12: SLA Monitoring (Continuous)

### 13.1 SLA Calculation Engine

```
TRIGGERED ON: every demand state transition + daily scheduled job

For each active contract:

  TIME-TO-FILL (per demand):
  ────────────────────────────
  elapsed = business_days(demand.open_date, now_or_fill_date)
  target = sla_config.time_to_fill_days
  status = GREEN if elapsed < 0.8 × target
           AMBER if elapsed < target
           RED   if elapsed ≥ target

  REPLACEMENT TIME (per replacement demand):
  ────────────────────────────
  elapsed = business_days(replacement.open_date, now_or_fill_date)
  target = sla_config.replacement_time_days
  (same GREEN/AMBER/RED logic)

  CV-TO-INTERVIEW RATIO (per demand):
  ────────────────────────────
  submitted = count(shortlist_entries where status != 'rejected_before_client')
  interviewed = count(interviews where status in ['completed', 'scored'])
  ratio = submitted / max(interviewed, 1)
  target = sla_config.cv_to_interview_ratio
  status = GREEN if ratio ≤ target
           AMBER if ratio ≤ target × 1.5
           RED   if ratio > target × 1.5

  FILL RATE (per quarter):
  ────────────────────────────
  opened = count(demands where status transitioned to 'open' in period)
  filled = count(demands where status transitioned to 'filled' in period)
  rate = filled / max(opened, 1) × 100
  target = sla_config.fill_rate_target

  QUALITY SCORE (per quarter):
  ────────────────────────────
  avg = mean(quality_surveys.overall where submitted_at in period)
  target = sla_config.quality_score_target
```

### 13.2 SLA Dashboard Views

**Client (Customer) view:**
```
┌─────────────────────────────────────────────────────────────┐
│  SLA PERFORMANCE — ECTL-FWC-2026-01 — Q3 2026              │
│                                                              │
│  Time to Fill    ████████████████████░░░ 12.3 days (target: 15) ✓ │
│  Replacement     ████████████████░░░░░░  8.1 days (target: 10) ✓ │
│  CV:Interview    ██████████████████████  2.8 : 1  (target: 3:1) ✓ │
│  Fill Rate       ████████████████████████████ 92%  (target: 90%) ✓ │
│  Quality Score   ████████████████████████ 4.2/5  (target: 4.0) ✓ │
│                                                              │
│  ACTIVE DEMANDS:                                             │
│  ECTL-0042 [REPLACE] Day 5/10 ██████████████░░ Matching  ⚠  │
│  ECTL-0043          Day 3/15  ████░░░░░░░░░░░░ Open      ✓  │
│  ECTL-0044          Day 8/15  █████████████░░░ Interview ✓  │
│                                                              │
│  [Export PDF Report]                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 14. Workflow 13: Quality Survey

### 14.1 Process Flow

```
System                         Customer
  │                               │
  │── Demand transitions ────────▶│
  │   to "Filled"                │
  │                               │
  │── Trigger quality survey ───▶│
  │   (notification + email)     │
  │                               │
  │                               │── Opens survey form:
  │                               │   Timeliness    ★★★★☆ (4/5)
  │                               │   Candidate     ★★★★★ (5/5)
  │                               │    Quality
  │                               │   Communication ★★★★☆ (4/5)
  │                               │   Overall       ★★★★☆ (4/5)
  │                               │   Comments: "Fast turnaround,
  │                               │    excellent candidate match"
  │                               │
  │◀── Survey submitted ─────────│
  │── Store results              │
  │── Update SLA quality metric  │
  │── Notify SM                  │
```

---

## 15. Workflow 14: Formatted CV Generation

### 15.1 Process Flow

```
Recruiter/SM                   System
  │                               │
  │── Request formatted CV ─────▶│
  │   (candidate + demand)       │── Pull parsed CV data
  │                               │── Pull profile mapping
  │                               │── Pull SFIA level + evidence
  │                               │── Pull ESCO-coded skills
  │                               │── Pull language proficiencies
  │                               │── Pull clearance status
  │                               │── Pull verification status
  │                               │── Pull certifications
  │                               │
  │                               │── Render into Brayton template:
  │                               │   ┌─────────────────────────┐
  │                               │   │  BRAYTON GLOBAL          │
  │                               │   │  Candidate Profile       │
  │                               │   │                          │
  │                               │   │  Profile: SC-DEV-03      │
  │                               │   │  SFIA Level: 5           │
  │                               │   │  Clearance: NATO RESTR.  │
  │                               │   │                          │
  │                               │   │  SKILLS MATRIX:          │
  │                               │   │  Java ████████████ Expert │
  │                               │   │  Spring ██████████ Adv   │
  │                               │   │  K8s ████████ Inter      │
  │                               │   │                          │
  │                               │   │  EXPERIENCE: ...         │
  │                               │   │  EDUCATION: ...          │
  │                               │   │  CERTS: [✓ verified]     │
  │                               │   │  LANGUAGES:              │
  │                               │   │  EN: C1 | FR: B1        │
  │                               │   └─────────────────────────┘
  │                               │
  │                               │── Store in Azure Blob
  │◀── PDF/DOCX ready ──────────│
  │── Review / edit ────────────▶│── (optional manual edits)
  │── Download / attach to       │
  │   shortlist submission       │
```

---

## 16. Workflow 15: GDPR Deletion Request

### 16.1 Process Flow

```
Candidate                      System                         Admin
  │                               │                               │
  │── Request deletion ─────────▶│── Mark for deletion           │
  │                               │── Start 30-day grace period  │
  │                               │── Notify Admin ──────────────▶│
  │                               │── Send confirmation email     │
  │                               │                               │
  │   GRACE PERIOD (30 days):    │                               │
  │   - Candidate can cancel     │                               │
  │   - Account deactivated      │                               │
  │                               │                               │
  │   AFTER 30 DAYS:             │                               │
  │                               │── Delete CV files from Blob  │
  │                               │── Delete parsed_data         │
  │                               │── Delete verification evidence│
  │                               │── Anonymize match_results    │
  │                               │── Anonymize shortlist_entries│
  │                               │── Anonymize interview records│
  │                               │── Delete assessment_answers  │
  │                               │── Delete formatted CVs       │
  │                               │── Delete user account        │
  │                               │── Create audit log (no PII)  │
  │                               │   (audit log itself retained  │
  │                               │    for 7 years per policy)   │
```

---

## 17. Cross-Workflow: Role Permission Matrix

### 17.1 Entity-Level Permissions

| Entity | Admin | SM | Recruiter | Customer | Candidate |
|--------|:-----:|:--:|:---------:|:--------:|:---------:|
| **Tenants** | CRUD | R (own) | R (assigned) | R (own) | — |
| **Contracts** | CRUD | CRU (own tenant) | R (assigned) | R (own tenant) | — |
| **Rate Cards** | CRUD | CRU (own tenant) | R (assigned) | — | — |
| **Profile Catalogue** | CRUD | CRU (own tenant) | R (assigned) | R (own tenant) | — |
| **Users** | CRUD | CRU (own tenant) | R (own tenant) | CRU (own tenant) | R (self) |
| **Demands** | CRUD | CRUD (own tenant) | CRUD (assigned) | CR (own tenant) | R (matched) |
| **Demand transition** | All | All (own tenant) | T1-T3 | T1, T4 | — |
| **External ID (Atos)** | RU | RU | R | R | — |
| **Candidates** | CRUD (all) | R (visible) | R (visible) | R (shortlisted) | CRUD (self) |
| **CV files** | R (all) | R (visible) | R (visible) | R (shortlisted) | CRUD (own) |
| **Formatted CVs** | R (all) | CR (own tenant) | CR (assigned) | R (shortlisted) | — |
| **Security Clearances** | RU (all) | R (visible) | R (visible) | R (shortlisted) | CRUD (own) |
| **Language Proficiencies** | R (all) | R (visible) | R (visible) | R (shortlisted) | CRUD (own) |
| **Match results** | R (all) | R (own tenant) | R (assigned) | R (own demand) | R (own) |
| **Shortlist** | RU (all) | RU (own tenant) | CRU (assigned) | R + approve/reject | — |
| **Rejection reasons** | R (all) | R (own tenant) | CR (assigned) | R (own demand) | — |
| **Verification** | R (all) | RU (own tenant) | CRUD (assigned) | R (shortlisted) | — |
| **Interviews** | R (all) | CRUD (own tenant) | CRUD (assigned) | R (own demand) | R (own) |
| **Scorecards** | R (all) | R (own tenant) | CR (assigned) | — | — |
| **Assessments** | CRUD (all) | CRUD (own tenant) | CRUD (assigned) | R (own demand) | R + take (own) |
| **Question bank** | CRUD (all) | CRUD (own tenant) | CRUD (assigned) | — | — |
| **Approvals** | Approve any | Approve (own tenant) | Initiate | — | — |
| **SLA config** | CRUD | RU (own tenant) | R (assigned) | R (own tenant) | — |
| **SLA dashboard** | R (all) | R (own tenant) | R (assigned) | R (own tenant) | — |
| **Quality surveys** | R (all) | R (own tenant) | R (assigned) | Submit + R (own) | — |
| **Notifications** | R (own) | R (own) | R (own) | R (own) | R (own) |
| **Audit logs** | R (all) + export | — | — | — | — |
| **AI decision logs** | R (all) | — | — | — | — |
| **Dashboards** | Admin view | SM view | Recruiter view | Customer view | Candidate view |

### 17.2 Demand Transition Permissions

| Transition | Admin | SM | Recruiter | Customer | Candidate |
|------------|:-----:|:--:|:---------:|:--------:|:---------:|
| Draft → Open | ✓ | ✓ | ✓ | ✓ | — |
| Open → Matching | ✓ | ✓ | ✓ | — | — |
| Matching → Shortlisted | ✓ | ✓ (approver) | ✓ (initiator) | — | — |
| Shortlisted → Interview | ✓ | ✓ | — | ✓ | — |
| Interview → Offered | ✓ | ✓ | — | — | — |
| Offered → Filled | ✓ | ✓ | — | — | — |
| Filled → Closed | ✓ | ✓ | — | — | — |
| Any → Closed (cancel) | ✓ | ✓ | — | — | — |

---

## 18. Workflow Summary Table

| # | Workflow | Primary Actors | AI Involved | New in v2 |
|---|---------|---------------|:-----------:|:---------:|
| 1 | Tenant & Contract Setup | Admin, Customer Admin | — | ✓ |
| 2 | Candidate Registration + CV Upload | Candidate | CV Parsing + ESCO + SFIA | Updated |
| 3 | Demand Creation + JD Enhancement | Customer/SM/Recruiter | JD Chat + Inline + Bias | Updated |
| 4 | Demand Lifecycle | All internal + Customer | — | Updated |
| 5 | AI Matching | Recruiter/SM | ESCO scoring + Explainability | Updated |
| 6 | Approval Chain | Recruiter → SM → Admin | — | ✓ |
| 7 | CV Verification | Recruiter | Consistency flags | ✓ |
| 8 | Shortlist Review | Customer | — | Updated |
| 9 | Interview Process | Recruiter/SM, Interviewers | Question generation | Same |
| 10 | Assessment Process | Recruiter, Candidate | Question gen + scoring | Same |
| 11 | Replacement Pipeline | SM, Recruiter | Same as standard | ✓ |
| 12 | SLA Monitoring | System (continuous) | — | ✓ |
| 13 | Quality Survey | Customer | — | ✓ |
| 14 | Formatted CV Generation | Recruiter/SM | — | ✓ |
| 15 | GDPR Deletion | Candidate, Admin | — | Updated |

---

## 19. Key Business Rules

1. **Demand numbers are immutable** — once assigned, `ECTL-0001` never changes
2. **Profile selection is required** for demands linked to a contract with a catalogue
3. **Mandatory profile requirements are non-negotiable** — red compliance items block shortlisting unless SM overrides via approval chain
4. **Rate card ceilings are enforced** — candidates above ceiling cannot be shortlisted without documented approval
5. **Security clearance is a hard filter** — candidates without required clearance are excluded from matching, no override
6. **Language requirements are hard filters** — below minimum CEFR = excluded from matching
7. **Shortlist submission requires approval** — Recruiter prepares, SM approves before client sees
8. **Matching does not auto-transition** — recruiter must review results before shortlist is created
9. **Customer cannot see candidates before shortlisting** — no browsing the candidate pool
10. **Candidates are global** — one candidate can be matched across multiple tenants
11. **AI scoring is advisory** — human override always available and takes precedence
12. **All AI decisions are logged** — model, prompt version, input/output, human action recorded per EU AI Act
13. **Cancellation requires reason** — structured rejection reasons at every stage
14. **SLA clock starts at Open** — business days counted, monitored continuously
15. **Replacement demands have stricter SLA** — shorter time target, prominent dashboard flag
16. **Quality survey triggers on Filled** — client rates recruitment process quality
17. **Audit logs retained for 7 years** — hot (12 months) + cold (Azure Blob) storage
18. **GDPR deletion anonymizes but retains audit events** — 30-day grace period before permanent deletion
19. **Formatted CVs are versioned** — each generation timestamped and linked to demand
20. **Assessment time enforced server-side** — auto-submit on expiry regardless of client state
