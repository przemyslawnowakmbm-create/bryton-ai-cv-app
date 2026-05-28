# Bryton AI CV App -- Cross-Document Consistency Analysis

**Date:** 2026-05-28
**Documents Analyzed:**
- REQUIREMENTS.md v2.0
- ARCHITECTURE.md v2.0
- BUSINESS_WORKFLOW.md v2.0

**Analysis Scope:** Entity consistency, role/permission consistency, API endpoint coverage, notification events, data flow, state machine, numerical values, and out-of-scope enforcement.

---

## A. Entity Consistency

### A.1 REQUIREMENTS Entities vs. ARCHITECTURE DB Tables

| REQUIREMENTS Entity | ARCHITECTURE Table | Status |
|---|---|---|
| Tenants | `tenants` | PASS |
| Contracts | `contracts` | PASS |
| Rate Cards | `rate_cards` | PASS |
| Profile Catalogue | `profile_catalogue` | PASS |
| Profile Requirements | `profile_requirements` | PASS |
| SFIA Levels | `sfia_levels` | PASS |
| ESCO Skills | `esco_skills` | PASS |
| Users | `users` | PASS |
| User-Tenant Assignments | `user_tenant_assignments` | PASS |
| Candidates | `candidates` | PASS |
| Candidate Languages | `candidate_languages` | PASS |
| Security Clearances | `security_clearances` | PASS |
| CV Files | `cv_files` | PASS |
| Demands | `demands` | PASS |
| Demand Sequences | `demand_sequences` | PASS |
| Demand Transitions | `demand_transitions` | PASS |
| JD Versions | `jd_versions` | PASS |
| Chat Sessions / Messages | `chat_sessions`, `chat_messages` | PASS |
| Match Results | `match_results` | PASS |
| Shortlist Entries | `shortlist_entries` | PASS |
| Verification Checklists | `verification_checklists` | PASS |
| Verification Items | `verification_items` | PASS |
| Approval Requests | `approval_requests` | PASS |
| SLA Configs | `sla_configs` | PASS |
| SLA Metric Snapshots | `sla_metric_snapshots` | PASS |
| Quality Surveys | `quality_surveys` | PASS |
| AI Decision Logs | `ai_decision_logs` | PASS |
| Audit Logs | `audit_logs` | PASS |
| Formatted CV Outputs | `formatted_cv_outputs` | PASS |
| Notifications | Referenced as "(Same as v1)" | PASS (deferred to v1 schema) |
| Notification Preferences | Referenced as "(Same as v1)" | PASS (deferred to v1 schema) |

**ISSUE A-1: Missing explicit DDL for Interviews, Scorecards, Assessment tables**

ARCHITECTURE S4.3 states: "interviews, interview_interviewers, scorecards, assessment_templates, assessment_questions, question_bank, assessment_assignments, assessment_answers -- (Same as v1 -- see original ARCHITECTURE.md for full DDL)". However, this is the v2.0 document and no v1 ARCHITECTURE.md is included in the repository. A developer working only from the v2.0 docs would have incomplete schema definitions for 8 tables covering the interview and assessment features.

- **Severity: HIGH** -- developers need the full DDL. The reference to a missing v1 document creates a gap.

**ISSUE A-2: Missing explicit DDL for Notifications and Notification Preferences**

Same problem as A-1. The notifications tables are deferred to v1 with "(Same as v1)" but the v1 doc is not present.

- **Severity: HIGH** -- same reasoning as A-1.

**ISSUE A-3: No dedicated table for Candidate Skills (ESCO-mapped)**

REQUIREMENTS S4.2.2 states "Skills that don't map to ESCO are stored as 'custom skills' with a flag for future mapping." The `candidates` table has a `parsed_skills_esco JSONB` column, but there is no dedicated `candidate_skills` join table linking candidates to ESCO codes with metadata (confidence score, custom flag, source). This means:
- No referential integrity between candidate skills and the `esco_skills` reference table
- No ability to query "all candidates with ESCO skill X" without JSONB scanning (performance concern at scale)
- REQUIREMENTS S4.2.2 mentions a "confidence score" per skill mapping, which would be difficult to manage in a flat JSONB array

- **Severity: MEDIUM** -- functional but likely a performance and queryability issue at the "tens of thousands of CVs" scale mentioned in REQUIREMENTS S11.5.

**ISSUE A-4: No Consent tracking table**

REQUIREMENTS S8.1 specifies GDPR consent tracking with "timestamp, IP, version" recorded. The `candidates` table has `consent_given BOOLEAN` and `consent_at TIMESTAMPTZ`, but no IP address or consent version fields. REQUIREMENTS implies multiple consent records could exist (e.g., version changes), but the schema only supports a single boolean flag.

- **Severity: MEDIUM** -- GDPR compliance requires tracking consent per version of T&Cs. A single boolean is insufficient for audit.

### A.2 ARCHITECTURE Tables vs. REQUIREMENTS Features

Every table in ARCHITECTURE maps to at least one feature in REQUIREMENTS. **PASS**.

### A.3 BUSINESS_WORKFLOW Entities vs. Other Docs

All entities referenced in BUSINESS_WORKFLOW workflows exist in both REQUIREMENTS and ARCHITECTURE. **PASS**.

---

## B. Role & Permission Consistency

### B.1 Role Definitions

| Role | REQUIREMENTS S1.2 | ARCHITECTURE (routes, RBAC) | WORKFLOW S17.1 | Status |
|---|---|---|---|---|
| Admin | System-wide config, tenant mgmt, user mgmt, global audit | Admin routes defined, full access | CRUD on everything, all transitions | PASS |
| Service Manager (SM) | Tenant-scoped, demand oversight, Atos ID, rate cards, approval authority | Internal routes (SM + Recruiter) | Extensive permissions per matrix | PASS |
| Recruiter | Demand mgmt, CV review, matching, verification | Internal routes (SM + Recruiter) | CRUD on demands (assigned), initiates approvals | PASS |
| Customer | External, demand creation, shortlist review, SLA dashboard | Customer routes defined | CR on demands, approve/reject shortlist, submit surveys | PASS |
| Candidate | Global, self-service, CV upload, assessments | Candidate routes defined | CRUD on self, take assessments | PASS |

### B.2 Demand Lifecycle Transition Permissions

**ISSUE B-1: Admin role missing from REQUIREMENTS transition table but present in WORKFLOW**

REQUIREMENTS S4.7.5 transition table lists allowed roles as:
- Draft -> Open: Customer, SM, Recruiter
- Open -> Matching: Recruiter, SM
- Matching -> Shortlisted: Recruiter, SM
- Shortlisted -> Interview: Customer, SM
- Interview -> Offered: SM
- Offered -> Filled: SM
- Filled -> Closed: SM, Admin
- Any -> Closed: SM, Admin

WORKFLOW S17.2 transition permission matrix shows Admin has a checkmark for **every transition** (Draft->Open, Open->Matching, Matching->Shortlisted, Shortlisted->Interview, Interview->Offered, Offered->Filled, Filled->Closed, Any->Closed).

WORKFLOW S5.2 transition rules table lists the same roles as REQUIREMENTS (no Admin in T1-T6).

So there is an internal inconsistency within BUSINESS_WORKFLOW itself (S5.2 vs S17.2), and between REQUIREMENTS S4.7.5 and WORKFLOW S17.2.

The question is whether Admin should have transition authority on all states. Given Admin has "Full system access across all tenants" in REQUIREMENTS S3.2, it makes sense that Admin can perform any transition. But the REQUIREMENTS transition table and the WORKFLOW transition rules table both omit Admin from most transitions.

- **Severity: HIGH** -- must decide whether Admin can perform all transitions and make all three locations consistent.

**ISSUE B-2: Recruiter allowed for Open -> Matching in REQUIREMENTS but also in WORKFLOW S17.2**

WORKFLOW S17.2 gives Recruiter a checkmark for Open -> Matching. REQUIREMENTS S4.7.5 also allows Recruiter for this transition. WORKFLOW S5.2 also allows Recruiter. All three agree. **PASS** for this specific transition.

However, WORKFLOW S17.2 gives Recruiter a checkmark for Matching -> Shortlisted as "initiator" -- this is consistent with the approval chain (Recruiter initiates, SM approves). **PASS**.

**ISSUE B-3: Recruiter missing from Shortlisted -> Interview**

REQUIREMENTS S4.7.5: Shortlisted -> Interview allowed by Customer, SM.
WORKFLOW S5.2: Shortlisted -> Interview allowed by Customer, SM.
WORKFLOW S17.2: Shortlisted -> Interview -- Recruiter has no checkmark.

This is consistent across all three docs: Recruiter cannot move demand from Shortlisted to Interview. **PASS** (no inconsistency, but noting that the Recruiter who manages the demand day-to-day cannot initiate interviews -- by design).

### B.3 Approval Chain Consistency

REQUIREMENTS S3.3 Approval Chain table:

| Action | Initiator | Approver |
|---|---|---|
| Shortlist submission to client | Recruiter | SM |
| Rate card ceiling override | SM | Admin |
| Candidate submission above rate | Recruiter | SM |
| Demand cancellation | SM | Admin |
| Profile catalogue modification | SM | Admin |

WORKFLOW S7.2 Approval Gates table:

| Gate | Initiator | Approver |
|---|---|---|
| Shortlist submission | Recruiter | SM |
| Rate override | Recruiter/SM | SM/Admin |
| Profile non-compliance override | Recruiter | SM |
| Demand cancellation | SM | Admin |
| Profile catalogue change | SM | Admin |

**ISSUE B-4: Rate override initiator/approver discrepancy**

REQUIREMENTS S3.3 has two separate lines:
- "Rate card ceiling override": SM -> Admin
- "Candidate submission above rate": Recruiter -> SM

WORKFLOW S7.2 collapses these into one line:
- "Rate override": Recruiter/SM -> SM/Admin

While not strictly contradictory, the WORKFLOW version is ambiguous about the escalation path. REQUIREMENTS makes it clear there are two distinct approval paths depending on who initiates, while WORKFLOW merges them. This could cause implementation confusion.

- **Severity: MEDIUM** -- should be clarified to match the two-path model in REQUIREMENTS.

**ISSUE B-5: Profile non-compliance override missing from REQUIREMENTS approval table**

WORKFLOW S7.2 includes "Profile non-compliance: Shortlist candidate with failed mandatory requirement -- Recruiter -> SM". This gate is described in REQUIREMENTS S4.4.3 ("Red items block shortlisting unless SM overrides with documented justification (triggers approval chain)") but is NOT listed in the REQUIREMENTS S3.3 approval chain table.

- **Severity: MEDIUM** -- the approval chain table in REQUIREMENTS should include this gate for completeness.

---

## C. API Endpoint Coverage

### C.1 Features vs. Endpoints

| REQUIREMENTS Feature | Expected API Endpoint(s) | ARCHITECTURE S3.3 Coverage | Status |
|---|---|---|---|
| CV Upload | POST /candidates/:id/cv | Present | PASS |
| CV Parsing (AI) | Triggered by upload | Implicit in upload flow | PASS |
| Candidate Profile CRUD | GET/PATCH /candidates/:id | Present | PASS |
| Formatted CV Generation | GET /candidates/:id/cv/formatted | Present | PASS |
| Language Proficiency CRUD | /candidates/:id/languages/* | Present | PASS |
| ESCO Skills Search | GET /esco/skills | Present | PASS |
| SFIA Levels | GET /sfia/levels | Present | PASS |
| Profile Catalogue CRUD | /profiles/* | Present | PASS |
| Profile Compliance Check | POST /profiles/:id/compliance-check | Present | PASS |
| Security Clearance CRUD | /candidates/:id/clearances/* | Present | PASS |
| Contract CRUD | /contracts/* | Present | PASS |
| Rate Card Management | /contracts/:id/rate-card/* | Present | PASS |
| Demand CRUD | /demands/* | Present | PASS |
| Demand Lifecycle Transition | POST /demands/:id/transition | Present | PASS |
| Replacement Demand | POST /demands/:id/replacement | Present | PASS |
| JD Enhancement (AI Chat) | /ai/chat/* | Present | PASS |
| AI Inline Suggestions | GET /ai/inline-suggest | Present | PASS |
| Matching | POST /demands/:id/match, GET /demands/:id/matches | Present | PASS |
| Shortlist Management | GET/PATCH /demands/:id/shortlist | Present | PASS |
| Structured Rejection | GET /demands/:id/rejections | Present | PASS |
| CV Verification | /verification/* | Present | PASS |
| Approval Chain | /approvals/* | Present | PASS |
| SLA Management | /sla/* | Present | PASS |
| Interview Management | /interviews/* | Present | PASS |
| Interview Question Generation | POST /interviews/:id/generate-questions | Present | PASS |
| Assessment Management | /assessments/* | Present | PASS |
| Quality Survey | /surveys/* | Present | PASS |
| Notifications | /notifications/*, WS /ws/notifications | Present | PASS |
| Dashboards (per role) | /dashboards/* | Present | PASS |
| Exports (CSV, PDF) | /exports/* | Present | PASS |
| Audit Logs | /audit/* | Present | PASS |
| AI Monitoring | /ai/monitoring/* | Present | PASS |

**ISSUE C-1: No GDPR deletion endpoint**

REQUIREMENTS S8.1 specifies "Right to be forgotten: candidate can request data deletion." WORKFLOW S16 describes the full GDPR deletion flow. ARCHITECTURE S3.3 has `DELETE /candidates/:id` described as "GDPR deletion request" but this is under the general Candidates section. This is actually covered -- the DELETE endpoint serves as the GDPR request trigger. **PASS** (on closer inspection).

**ISSUE C-2: No endpoint for Bulk Audit Export download**

ARCHITECTURE S3.3 has `POST /audit/export` (trigger) and `GET /audit/export/:job_id` (check status / download). REQUIREMENTS S8.4 describes bulk audit export. WORKFLOW does not have a dedicated workflow for this but it is an admin function. **PASS**.

**ISSUE C-3: No endpoint for Demand comparison view**

REQUIREMENTS S4.10.5 mentions "Comparison view: select 2-4 candidates, see side-by-side table." There is no dedicated API endpoint for candidate comparison. However, this could be implemented client-side by fetching individual match results.

- **Severity: LOW** -- can be handled on the frontend, but a dedicated comparison endpoint could improve performance.

**ISSUE C-4: No endpoint for SLA configuration per contract**

ARCHITECTURE S3.3 has `GET/PATCH /sla/config` but the description says "for current tenant." REQUIREMENTS S4.11.1 says SLA is "Per tenant per contract" and ARCHITECTURE table `sla_configs` has both `tenant_id` and `contract_id`. However, the contract route `/contracts/:id/sla` is listed in the frontend routing (S2.3) but NOT in the API endpoints (S3.3). The `/sla/config` endpoint would need a contract_id parameter or a dedicated `/contracts/:id/sla` API endpoint.

- **Severity: MEDIUM** -- the frontend routing implies a per-contract SLA config endpoint that does not exist in the API specification.

**ISSUE C-5: No endpoint for Clearance Application Tracking updates**

REQUIREMENTS S4.5.3 describes clearance application tracking (Application Submitted -> Under Investigation -> Granted/Denied). The `security_clearances` table has `application_status VARCHAR(30)` which would hold this, and the PATCH endpoint exists. The workflow in BUSINESS_WORKFLOW does not have a dedicated clearance application workflow. The candidate registration workflow (S3) mentions adding clearances but not the lifecycle tracking. This is a minor gap -- the API exists but the workflow documentation does not explicitly cover it.

- **Severity: LOW** -- API capable, workflow documentation could be more explicit.

---

## D. Notification Event Consistency

### D.1 REQUIREMENTS S6.2 Events vs. WORKFLOW Notification Triggers

| REQUIREMENTS Event | WORKFLOW Trigger Location | Status |
|---|---|---|
| New demand created | S4.1: Notify SM + Recruiter on Open | PASS |
| Demand status changed | S5.2: Side effects on each transition include "notify" | PASS |
| New match results available | S6.1: "Match results ready" notification | PASS |
| Shortlist ready for review | S9.1: "Shortlist ready for ECTL-0001" notification | PASS |
| Candidate approved/rejected | S9.1: Status change on shortlist entry | PASS (implicit) |
| Interview scheduled | S10.1: "Notify: interviewers, candidate, customer" | PASS |
| Assessment assigned | S11.1: "Notify candidates" | PASS |
| Assessment completed | S11.2: "Notify Recruiter/SM" | PASS |
| Approval request pending | S7.1: "Notify approver (in-app + email)" | PASS |
| Approval decision made | S7.1: "Notification: approved/rejected" | PASS |
| SLA at risk | S13.1: SLA status calculation (AMBER) | **ISSUE** |
| SLA breached | S13.1: SLA status calculation (RED) | **ISSUE** |
| Security clearance expiring | Not explicitly triggered in any workflow | **ISSUE** |
| Rate card ceiling exceeded | S6.1: "Flag if exceeds" in Phase 4 | PASS (implicit) |
| Replacement demand created | S12.1: "Notify: Recruiter" | PASS |
| New candidate registration | Not mentioned in any workflow | **ISSUE** |
| Quality survey requested | S14.1: "Trigger quality survey (notification + email)" | PASS |
| Password reset | Not mentioned in any workflow | PASS (trivial, infrastructure) |

**ISSUE D-1: SLA alert notifications not explicitly triggered in WORKFLOW**

REQUIREMENTS S6.2 lists "SLA at risk" and "SLA breached" as notification events. WORKFLOW S13.1 describes the SLA calculation engine and the GREEN/AMBER/RED statuses, and S5.3 mentions "SLA status recalculated on every transition." But the workflow does not explicitly state "send notification when SLA transitions to AMBER or RED." The notification trigger is implicit in the status calculation but never explicitly called out as a side effect.

- **Severity: MEDIUM** -- the SLA monitoring workflow should explicitly state that notifications are sent when SLA status transitions to AMBER (at risk) or RED (breached).

**ISSUE D-2: Security clearance expiry notifications not in any workflow**

REQUIREMENTS S4.5.2 states "Clearance expiry monitoring: alerts at 90, 60, and 30 days before expiry" and S6.2 lists "Security clearance expiring" as a notification event. No workflow in BUSINESS_WORKFLOW describes a scheduled job or trigger for clearance expiry alerts. The SLA Monitoring workflow (S13) runs as a daily scheduled job, but there is no analogous "Clearance Monitoring" workflow.

- **Severity: MEDIUM** -- a scheduled workflow for clearance expiry monitoring should be added to BUSINESS_WORKFLOW.

**ISSUE D-3: New candidate registration notification not in any workflow**

REQUIREMENTS S6.2 lists "New candidate registration" (in-app only, no email). WORKFLOW S3 describes candidate registration but does not mention any notification to internal users (Admin/SM/Recruiter) upon a new candidate registering. This may be intentional (candidates are global, not tenant-scoped at registration) but should be documented.

- **Severity: LOW** -- likely intentional but should be explicitly noted in the workflow.

---

## E. Data Flow Consistency

### E.1 ESCO

| Aspect | REQUIREMENTS | ARCHITECTURE | WORKFLOW | Status |
|---|---|---|---|---|
| Reference data loaded | S4.2.2 "loaded as reference data" | `esco_skills` table | S4.2 "ESCO-coded skills" in profile requirements | PASS |
| AI maps skills to ESCO | S4.1.2 "Skills mapped to ESCO codes" | `parsed_skills_esco JSONB` on candidates | S3.1 "Map skills -> ESCO" | PASS |
| Matching uses ESCO | S4.10.2 "operates on ESCO skill codes" | matching/scorer.py | S6.1 "ESCO-coded skills" in matching | PASS |
| JD uses ESCO tags | S4.2.2 "JD creation uses ESCO-aligned skill tags" | GET /esco/skills autocomplete | S4.2 profile requirements with ESCO codes | PASS |
| Custom skills flagged | S4.2.2 "stored as custom skills with flag" | No dedicated column/table | Not mentioned in workflow | ISSUE |

**ISSUE E-1: Custom skills storage not reflected in ARCHITECTURE**

REQUIREMENTS S4.2.2 says unmapped skills are stored as "custom skills with a flag for future mapping." The ARCHITECTURE has only `parsed_skills_esco JSONB` on the candidates table, which could contain custom skills as JSON entries, but there is no explicit flag or separate storage. The BUSINESS_WORKFLOW does not mention custom skills either.

- **Severity: LOW** -- can be handled within the JSONB structure, but should be explicitly documented in the schema design notes.

### E.2 SFIA

| Aspect | REQUIREMENTS | ARCHITECTURE | WORKFLOW | Status |
|---|---|---|---|---|
| 7 levels (1-7) | S4.3.2 table with all 7 levels | `sfia_levels` table CHECK (1-7), `rate_cards` CHECK (1-7) | S6.2 "SFIA Level: 5" in examples | PASS |
| Profile mapped to SFIA range | S4.4.2 "SFIA Level Range: Min-Max" | `profile_catalogue.sfia_level_min/max` | S4.1 "SFIA level range" pre-populated | PASS |
| AI suggests SFIA | S4.1.2 "SFIA level suggestion" | `candidates.sfia_level`, `sfia_level_source` | S3.1 "Suggest SFIA level" | PASS |
| Rate cards linked to SFIA | S4.6.2 "per profile and SFIA level" | `rate_cards(profile_id, sfia_level)` | S12.2 "same SFIA range" | PASS |
| Mismatch alert (>=2 difference) | S4.3.3 "if AI differs by >=2, flag" | Not in schema | Not in workflow | ISSUE |

**ISSUE E-2: SFIA mismatch alert (>=2 level difference) not reflected in ARCHITECTURE or WORKFLOW**

REQUIREMENTS S4.3.3 specifies "Mismatch alert: if AI-suggested SFIA level differs from the recruiter-assigned level by >=2, flag for review." Neither ARCHITECTURE nor WORKFLOW mentions this business rule, how it is triggered, where the alert surfaces, or how it is stored.

- **Severity: MEDIUM** -- a documented business rule with no implementation path in the other two docs.

### E.3 Rate Cards

| Aspect | REQUIREMENTS | ARCHITECTURE | WORKFLOW | Status |
|---|---|---|---|---|
| Rate card enforcement | S4.6.3 "hard block" | `rate_cards` table, error response example | S6.1 Phase 4 "Rate Card Check" | PASS |
| Margin calculation | S4.6.3 "Margin = ceiling - cost" | Not in schema (computed) | S6.2 "Margin: EUR80/day (10.0%)" | PASS |
| SM override with approval | S4.6.3 "triggers approval chain (SM -> Admin)" | Approval chain in approvals module | S7.2 "Rate override" gate | PASS |

**PASS** -- rate card data flow is consistent.

### E.4 Security Clearances

| Aspect | REQUIREMENTS | ARCHITECTURE | WORKFLOW | Status |
|---|---|---|---|---|
| Clearance levels | S4.5.1: RESTRICTED, CONFIDENTIAL, SECRET, TOP SECRET | `security_clearances.level VARCHAR(20)` | S6.2 "NATO RESTRICTED" example | PASS |
| Clearance types | S4.5.1: NATO, EU, National, Other | `security_clearances.clearance_type VARCHAR(20)` | Not enumerated in workflow | PASS |
| Status values | S4.5.1: ACTIVE, EXPIRED, PENDING, DENIED, REVOKED | `security_clearances.status VARCHAR(20) DEFAULT 'self_declared'` | Not enumerated in workflow | ISSUE |

**ISSUE E-3: Security clearance status enum mismatch**

REQUIREMENTS S4.5.1 defines status values: ACTIVE, EXPIRED, PENDING, DENIED, REVOKED.
ARCHITECTURE schema has `status VARCHAR(20) NOT NULL DEFAULT 'self_declared'`.

The default value 'self_declared' is not in the REQUIREMENTS enum. This suggests the ARCHITECTURE added an additional status value not described in REQUIREMENTS. However, this may be intentional (self_declared is the initial state before any verification). But the discrepancy should be reconciled -- either REQUIREMENTS should list 'self_declared' as a valid status, or the default should be 'PENDING'.

- **Severity: MEDIUM** -- enum mismatch between spec and schema. Developers will not know which values are valid.

### E.5 Verification

| Aspect | REQUIREMENTS | ARCHITECTURE | WORKFLOW | Status |
|---|---|---|---|---|
| Verification statuses | S4.9.2: Verified, Self-declared, Pending verification, Unverifiable, Failed | `verification_items.status VARCHAR(20) DEFAULT 'pending'` | S8.1: FULLY_VERIFIED, PARTIALLY_VERIFIED, VERIFICATION_FAILED | **Partial** |

The verification status naming differs slightly between docs. REQUIREMENTS uses "Pending verification" while ARCHITECTURE defaults to "pending." WORKFLOW S8.1 uses three aggregate statuses (FULLY_VERIFIED, PARTIALLY_VERIFIED, VERIFICATION_FAILED) which are for the overall checklist, not individual items. The item-level statuses in REQUIREMENTS (Verified, Self-declared, Pending verification, Unverifiable, Failed) need to map to ARCHITECTURE column values. This is not explicitly defined in the ARCHITECTURE DDL.

- **Severity: LOW** -- naming convention differences, easily resolved during implementation by defining an enum.

### E.6 AI Decision Logging

| Aspect | REQUIREMENTS | ARCHITECTURE | WORKFLOW | Status |
|---|---|---|---|---|
| Fields logged | S8.2.1: 11 fields listed | `ai_decision_logs` table: matches all fields | S3.1, S6.1, S10.1, S11.2: "Log AI decision" | PASS |
| Human Action tracking | S8.2.1: "accepted/modified/rejected" | `human_action VARCHAR(20)` | S19 rule 12: "model, prompt version, input/output, human action recorded" | PASS |
| 7-year retention | S11.4 "same 7-year retention" | S6.2 Cold storage includes ai_decision_logs | S16.1 "audit log retained for 7 years" | PASS |

**PASS** -- AI decision logging is consistent.

---

## F. State Machine Consistency

### F.1 Demand Lifecycle States

| Source | States Listed |
|---|---|
| REQUIREMENTS S4.7.5 | Draft -> Open -> Matching -> Shortlisted -> Interview -> Offered -> Filled -> Closed |
| ARCHITECTURE `demands.status VARCHAR(20)` | Not enumerated (implicit from transitions) |
| WORKFLOW S5.1 (diagram) | DRAFT -> OPEN -> MATCHING -> SHORTLISTED -> INTERVIEW -> OFFERED -> FILLED -> CLOSED |
| WORKFLOW S5.2 (transition rules table) | draft -> open -> matching -> shortlisted -> interview -> offered -> filled -> closed |
| WORKFLOW S5.4 (Python code) | draft, open, matching, shortlisted, interview, offered, filled, closed |

**PASS** -- all documents agree on the same 8 states and the same linear progression with cancel-to-closed from any state.

### F.2 Transition Preconditions

| Transition | REQUIREMENTS S4.7.5 | WORKFLOW S5.2 | Status |
|---|---|---|---|
| Draft -> Open | (none stated) | "description not empty" | ISSUE |
| Open -> Matching | (none stated) | "required_skills not empty OR profile linked" | ISSUE |
| Matching -> Shortlisted | (none stated beyond approval) | "match_results exist; shortlist reviewed" | ISSUE |
| Shortlisted -> Interview | (none stated) | ">=1 shortlist entry approved by customer" | ISSUE |
| Interview -> Offered | (none stated) | ">=1 interview scored" | ISSUE |
| Offered -> Filled | (none stated) | (none) | PASS |
| Filled -> Closed | (none stated) | (none) | PASS |
| Any -> Closed | "Configurable" | "cancellation_reason provided" | PASS |

**ISSUE F-1: REQUIREMENTS S4.7.5 lacks preconditions**

REQUIREMENTS S4.7.5 transition table has columns for "Transition", "Allowed Roles", and "Approval Required" but no "Preconditions" column. WORKFLOW S5.2 adds preconditions to each transition. These preconditions are not contradicted by REQUIREMENTS, but they are absent from it. REQUIREMENTS S4.7.5 says "See BUSINESS_WORKFLOW.md for detailed state machine", so this is likely intentional delegation. However, REQUIREMENTS S4.7.5 should at minimum note that preconditions exist and are defined in the workflow doc.

- **Severity: LOW** -- intentional delegation, but the REQUIREMENTS doc should reference that preconditions are defined in the workflow.

### F.3 Approval Gates on Transitions

REQUIREMENTS S4.7.5 shows approval required on Matching -> Shortlisted. WORKFLOW S5.2 also shows approval required on this same transition. Both agree that no other transitions have mandatory approval (though cancellation is configurable). **PASS**.

---

## G. Numerical Consistency

### G.1 SLA Default Values

| KPI | REQUIREMENTS S4.11.1 | ARCHITECTURE `sla_configs` defaults | WORKFLOW S2.1 / S13.1 | Status |
|---|---|---|---|---|
| Time-to-fill | 15 days | `time_to_fill_days INTEGER DEFAULT 15` | "time-to-fill: 15 days" | PASS |
| Replacement time | 10 days | `replacement_time_days INTEGER DEFAULT 10` | "replacement: 10 days" | PASS |
| CV-to-interview ratio | 3:1 | `cv_to_interview_ratio DECIMAL(3,1) DEFAULT 3.0` | "3:1" | PASS |
| Fill rate | 90% | `fill_rate_target DECIMAL(5,2) DEFAULT 90.00` | "fill rate: 90%" | PASS |
| Quality score | 4.0/5.0 | `quality_score_target DECIMAL(3,1) DEFAULT 4.0` | Not explicit default in workflow | PASS |

**PASS** -- all SLA defaults are consistent.

### G.2 SLA Amber Threshold

**ISSUE G-1: SLA "At Risk" threshold inconsistency**

REQUIREMENTS S4.11.2: "At Risk (amber, >=80% of SLA consumed)"
WORKFLOW S5.3: "Amber: 60-99% of target consumed"
WORKFLOW S13.1 Time-to-fill: "AMBER if elapsed < target" (which means up to 99%)

The threshold for AMBER onset differs: REQUIREMENTS says >= 80%, WORKFLOW says >= 60%.

- **Severity: HIGH** -- this directly affects when SLA alerts fire and what the dashboard shows. Must pick one threshold and apply consistently. The 60% threshold in WORKFLOW is more conservative (earlier warning), which may be preferable, but it contradicts the REQUIREMENTS specification.

### G.3 Audit Retention Period

| Source | Value |
|---|---|
| REQUIREMENTS S3.2 (Admin role) | "7-year history" |
| REQUIREMENTS S8.3 | "Retention: 7 years" |
| REQUIREMENTS S11.4 | "7 years (configurable per tenant)" |
| ARCHITECTURE S6.2 | "Retention: 7 years (configurable per tenant)" |
| WORKFLOW S16.1 | "audit log itself retained for 7 years per policy" |
| WORKFLOW S19 rule 17 | "Audit logs retained for 7 years" |

**PASS** -- 7-year retention is consistent everywhere.

### G.4 SFIA Levels (1-7)

| Source | Range |
|---|---|
| REQUIREMENTS S4.3.2 | 7 levels (1-7), all labeled |
| ARCHITECTURE `sfia_levels` | `CHECK (level BETWEEN 1 AND 7)` |
| ARCHITECTURE `rate_cards` | `CHECK (sfia_level BETWEEN 1 AND 7)` |
| WORKFLOW S6.2 example | "SFIA Level: 5" |

**PASS** -- SFIA 1-7 is consistent.

### G.5 Token Counts and Cost Estimates

| Feature | REQUIREMENTS | ARCHITECTURE S5.4 | Status |
|---|---|---|---|
| CV parsing | "~$0.01 per candidate explanation" (S4.10.4, for match explanation) | "$0.01-0.03 per CV" (parsing), "$0.03-0.08 per candidate" (matching) | PASS (different features, no conflict) |
| File size limit | S4.1.1: "10 MB per file" | Not in ARCHITECTURE (but S8.1 mentions "size limits") | PASS |

**PASS** -- no numerical contradictions in cost estimates.

### G.6 Other Numerical Values

| Value | REQUIREMENTS | ARCHITECTURE | WORKFLOW | Status |
|---|---|---|---|---|
| Password min length | S3.1: "minimum 12 characters" | Not stated (impl detail) | Not stated | PASS |
| JWT access token lifetime | S11.2: "15-minute access" | S8.1: "access: 15min" | Not stated | PASS |
| JWT refresh token lifetime | S11.2: "7-day refresh" | S8.1: "refresh: 7d httpOnly cookie" | Not stated | PASS |
| Auto-shortlist top N default | S4.10.5: "default: 10" | Not stated | Not stated | PASS |
| Hot storage period | S8.3: "12 months" | S6.2: "older than 12 months" | Not stated | PASS |
| Invite link expiry | Not stated in REQ | Not stated in ARCH | S2.2: "72 hours" | N/A (only in workflow) |
| Approval timeout | Not stated in REQ | Not stated in ARCH | S7.3: "48 business hours" | N/A (only in workflow) |
| GDPR grace period | S8.1: "30-day grace period" | Not stated | S16.1: "30-day grace period" | PASS |
| Clearance expiry alerts | S4.5.2: "90, 60, and 30 days" | Not stated | Not stated | N/A (only in REQ) |

---

## H. Out of Scope Consistency

### H.1 Items Listed as Out of Scope in REQUIREMENTS S12

| Out of Scope Item | In ARCHITECTURE? | In WORKFLOW? | Status |
|---|---|---|---|
| Microsoft Entra ID SSO | S10.1 "Phase 2" migration path described | Not in any workflow | PASS (prep only, not implemented) |
| Calendar integration (Outlook/Google) | S2.3 mentions "Architecture prepared for future calendar integration" in route comments | Not in any workflow | PASS (prep only) |
| API integration with Atos tool | Manual field only (`external_id` in demands) | S17.1 "External ID (Atos)" is RU only | PASS |
| Mobile/tablet optimization | S2 is desktop-only (REQUIREMENTS S9.6: "1280px") | Not mentioned | PASS |
| Self-service tenant registration | Admin creates tenants manually (S2.1, S2.5) | S2.1 Admin creates tenant | PASS |
| Billing/metering per tenant | Not in ARCHITECTURE | Not in WORKFLOW | PASS |
| Video interview hosting | Not in ARCHITECTURE | Not in WORKFLOW | PASS |
| Bias detection / adverse impact analysis | NOT in ARCHITECTURE or WORKFLOW | NOT in ARCHITECTURE or WORKFLOW | **ISSUE** |
| Active placement / post-hire tracking | Not in ARCHITECTURE | Not in WORKFLOW | PASS |
| Timesheet / hours tracking | Not in ARCHITECTURE | Not in WORKFLOW | PASS |
| Automated reference checking | Not in ARCHITECTURE | Not in WORKFLOW | PASS |
| Multi-language / i18n support | Not in ARCHITECTURE | Not in WORKFLOW | PASS |
| Candidate sourcing from external job boards | Not in ARCHITECTURE | Not in WORKFLOW | PASS |

**ISSUE H-1: JD Bias Detection is partially implemented despite "Bias detection" being out of scope**

REQUIREMENTS S12 lists "Bias detection / adverse impact analysis (on hold -- future phase)" as out of scope.

However, REQUIREMENTS S4.8.1 describes "JD bias scanner: AI flags gendered, ageist, or exclusionary language." ARCHITECTURE S5.1 includes "JD Bias Detection: Haiku model, <2s." ARCHITECTURE S3.2 has `inline_suggester.py` described as "Inline editor suggestions + bias detection." WORKFLOW S4.1 shows bias detection in the JD enhancement workflow.

The out-of-scope item appears to refer specifically to **adverse impact analysis** (statistical bias detection across hiring outcomes, i.e., GAP-12 from the gap analysis), which is different from **JD language bias scanning** (flagging problematic text in job descriptions). These are distinct features, but the out-of-scope label "Bias detection" is ambiguous and could confuse stakeholders.

- **Severity: LOW** -- the distinction between "JD language bias scanning" (in scope) and "adverse impact analysis on hiring outcomes" (out of scope) should be clarified in REQUIREMENTS S12 to avoid confusion.

**ISSUE H-2: Placement tracking (GAP-05) correctly excluded**

REQUIREMENTS S1 explicitly states "The tool covers recruitment up to onboarding/hire. Post-hire engagement tracking is handled by an external system." REQUIREMENTS S12 lists "Active placement / post-hire tracking" as out of scope. Neither ARCHITECTURE nor WORKFLOW includes any post-hire tracking. **PASS**.

---

## Summary of All Issues

| ID | Dimension | Issue | Severity |
|---|---|---|---|
| A-1 | Entity | Missing DDL for interview, scorecard, and assessment tables (deferred to nonexistent v1 doc) | **HIGH** |
| A-2 | Entity | Missing DDL for notification and notification_preferences tables (deferred to nonexistent v1 doc) | **HIGH** |
| A-3 | Entity | No dedicated candidate_skills table; ESCO skill mapping relies on JSONB (query performance, no referential integrity) | MEDIUM |
| A-4 | Entity | GDPR consent tracking lacks IP address, consent version; single boolean insufficient for versioned consent audit | MEDIUM |
| B-1 | Role/Perm | Admin transition permissions: REQUIREMENTS and WORKFLOW S5.2 omit Admin from most transitions, but WORKFLOW S17.2 gives Admin all transitions | **HIGH** |
| B-4 | Role/Perm | Rate override approval: REQUIREMENTS has two distinct paths (Recruiter->SM, SM->Admin); WORKFLOW merges into one ambiguous entry | MEDIUM |
| B-5 | Role/Perm | Profile non-compliance override gate present in WORKFLOW S7.2 and implied in REQUIREMENTS S4.4.3 but missing from REQUIREMENTS S3.3 approval table | MEDIUM |
| C-4 | API | No per-contract SLA config API endpoint, despite frontend route /contracts/:id/sla existing | MEDIUM |
| D-1 | Notification | SLA at-risk and breached notifications described in REQUIREMENTS but not explicitly triggered in any WORKFLOW | MEDIUM |
| D-2 | Notification | Security clearance expiry monitoring (90/60/30 day alerts) not covered by any workflow | MEDIUM |
| D-3 | Notification | New candidate registration notification trigger not documented in any workflow | LOW |
| E-1 | Data Flow | Custom skills (non-ESCO) storage not reflected in ARCHITECTURE schema | LOW |
| E-2 | Data Flow | SFIA mismatch alert (>=2 level difference) described in REQUIREMENTS but absent from ARCHITECTURE and WORKFLOW | MEDIUM |
| E-3 | Data Flow | Security clearance status enum mismatch: REQUIREMENTS defines ACTIVE/EXPIRED/PENDING/DENIED/REVOKED; ARCHITECTURE defaults to 'self_declared' (not in enum) | MEDIUM |
| F-1 | State Machine | REQUIREMENTS lacks transition preconditions (delegates to WORKFLOW but does not state this in the table) | LOW |
| G-1 | Numerical | SLA "At Risk" threshold: REQUIREMENTS says >=80%, WORKFLOW says >=60% | **HIGH** |
| H-1 | Out of Scope | "Bias detection" out-of-scope label is ambiguous; JD language bias scanning IS implemented, but the label could be confused with it | LOW |

### Severity Summary

| Severity | Count | Resolved |
|---|---|---|
| **CRITICAL** | 0 | — |
| **HIGH** | 4 | **4 RESOLVED** |
| **MEDIUM** | 8 | 0 |
| **LOW** | 6 | 0 |
| **Total** | 18 | 4 |

### HIGH Issue Resolution Log (2026-05-28)

- **A-1/A-2 RESOLVED**: Full DDL for all 10 tables (interviews, interview_interviewers, scorecards, assessment_templates, assessment_questions, question_bank, assessment_assignments, assessment_answers, notifications, notification_preferences) inlined into ARCHITECTURE.md v2.0. No references to v1 remain.
- **B-1 RESOLVED**: Admin added to all demand lifecycle transitions in REQUIREMENTS §4.7.5, BUSINESS_WORKFLOW §5.2 table, and §5.4 Python transition rules. Now consistent with WORKFLOW §17.2 permission matrix.
- **G-1 RESOLVED**: SLA "At Risk" threshold set to ≥80% in both REQUIREMENTS §4.11.2 and BUSINESS_WORKFLOW §5.3 and §13.1. All references now consistent.

---

## Recommendations

### Must Fix Before Development (HIGH)

1. **A-1 / A-2**: Inline the full DDL for all tables into the v2.0 ARCHITECTURE.md. Remove references to a "v1" document that is not part of the deliverable.

2. **B-1**: Decide on Admin transition authority. Recommended: Admin CAN perform all transitions (consistent with "full system access" description). Update REQUIREMENTS S4.7.5 and WORKFLOW S5.2 to include Admin in all transition rows. This aligns with WORKFLOW S17.2 which already grants Admin all transitions.

3. **G-1**: Reconcile SLA "At Risk" threshold. Pick either 60% (earlier warning, per WORKFLOW) or 80% (per REQUIREMENTS) and update both documents. Recommend 80% to match REQUIREMENTS, as 60% may cause excessive alerts.

### Should Fix During Development (MEDIUM)

4. **A-3**: Consider adding a `candidate_skills` join table with (candidate_id, esco_code, confidence, source, is_custom) for queryability at scale.

5. **A-4**: Expand consent tracking to include IP and consent version, either as additional columns or a separate `consent_records` table.

6. **B-4**: Split the WORKFLOW S7.2 "Rate override" row into two rows matching REQUIREMENTS S3.3.

7. **B-5**: Add "Profile non-compliance override: Recruiter -> SM" to REQUIREMENTS S3.3 approval chain table.

8. **C-4**: Add `GET/PATCH /contracts/:id/sla` endpoints to ARCHITECTURE S3.3, or clarify that `/sla/config` accepts a `contract_id` query parameter.

9. **D-1 / D-2**: Add explicit notification trigger statements to the SLA monitoring workflow and add a new "Clearance Monitoring" scheduled workflow.

10. **E-2**: Add the SFIA mismatch alert rule to ARCHITECTURE (as a business rule in the profiles/compliance module) and add a corresponding UI notification in WORKFLOW.

11. **E-3**: Reconcile security clearance status values. Add 'SELF_DECLARED' to REQUIREMENTS S4.5.1 or change the ARCHITECTURE default to 'PENDING'.
