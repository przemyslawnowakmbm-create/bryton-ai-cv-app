# Bryton AI CV App — Gap Analysis & Improvement Proposals

**Version:** 1.0
**Date:** 2026-05-28
**Status:** Draft
**Context:** Tool must demonstrate recruitment governance excellence to EUROCONTROL under a T&M framework contract

---

## Research Sources

Three parallel research streams were conducted:

1. **Competitive ATS landscape** — Bullhorn, SAP SuccessFactors, Workday, Beamery, iCIMS, Jobvite, Greenhouse, Lever, Manatal, Vincere
2. **T&M governance requirements** — EUROCONTROL procurement framework, DIGIT-TM III, ESA contracting, SFIA, NATO clearances
3. **AI recruitment innovation** — ESCO taxonomy, EU AI Act, bias detection, predictive analytics, candidate experience

---

## Executive Summary

The current spec builds a solid recruitment platform but **misses the entire T&M governance layer** that is the primary reason for building it. EUROCONTROL won't be impressed by a generic ATS with AI features — they'll be impressed by a system that proves Brayton has **auditable, enforceable control** over every aspect of the staffing process.

**28 gaps identified** across 5 categories:

| Category | Critical | High | Medium | Total |
|----------|:--------:|:----:|:------:|:-----:|
| T&M Contract Governance | 7 | 2 | 1 | 10 |
| EU AI Act / Regulatory | 3 | 2 | 0 | 5 |
| Competitive Feature Gaps | 0 | 4 | 4 | 8 |
| Audit & Compliance | 2 | 1 | 0 | 3 |
| Candidate & Client Experience | 0 | 1 | 1 | 2 |

---

## Category 1: T&M Contract Governance (THE BIGGEST MISS)

These gaps are the difference between "we have a recruitment tool" and "we have a T&M staffing governance platform." EUROCONTROL's procurement office evaluates suppliers partly on their ability to demonstrate process control. Every gap here is a missed opportunity to score higher in technical evaluation.

---

### GAP-01: No Profile Catalogue System
**Severity: CRITICAL**

**What's missing:** EU institutional T&M contracts (DIGIT-TM III, EUROCONTROL frameworks) define a **catalogue of predefined profiles** — e.g., "Senior Java Developer," "Cloud Architect," "Project Manager" — each with mandatory qualifications, minimum years of experience, required certifications, and language requirements. Every CV submitted must be mapped to a profile and validated against its requirements.

**What we have:** Free-form demands with arbitrary skill lists. No standardized profile definitions.

**What competitors do:** SprintCV (niche tool specifically for DIGIT-TM CV formatting) exists solely because this need is so acute. SAP SuccessFactors has configurable job profiles with mandatory requirements.

**Proposal:**
- Add a **Profile Catalogue** module — Admin/SM defines standardized profiles per contract
- Each profile has: code, title, mandatory qualifications, min experience, required certifications, required language levels, SFIA level range, rate card ceiling
- When creating a demand, user selects from the catalogue (or creates custom)
- AI auto-validates submitted CVs against profile requirements and produces a **compliance checklist** showing met/unmet criteria
- Visual gap indicator: green (all met), amber (minor gaps), red (disqualifying gaps)

---

### GAP-02: No SFIA Framework Alignment
**Severity: CRITICAL**

**What's missing:** The **Skills Framework for the Information Age (SFIA)** is the standard taxonomy used across UK/EU government procurement for mapping seniority to rate bands. SFIA defines 7 levels (Follow → Set Strategy) with specific responsibility descriptors. EUROCONTROL and EU institutions use SFIA (or equivalent) to validate that a candidate's claimed seniority matches their actual experience.

**What we have:** Free-text `experience_level` field (junior, mid, senior, lead, principal). No standardized framework.

**What competitors do:** Bullhorn and enterprise tools support configurable seniority frameworks.

**Proposal:**
- Implement SFIA level mapping (Levels 1-7) as a core taxonomy
- Each profile in the catalogue maps to a SFIA level range (e.g., "Senior Developer" = SFIA 4-5)
- AI parsing extracts experience indicators and **suggests SFIA level** based on CV evidence
- SM/Recruiter validates and confirms SFIA level
- Client (EUROCONTROL) can see SFIA level justification in candidate profile
- Rate card ceilings linked to SFIA levels

---

### GAP-03: No Rate Card Management
**Severity: CRITICAL**

**What's missing:** T&M contracts define **maximum daily-rate ceilings per profile and seniority level**. Suppliers must submit candidates within rate card bounds. Submitting above ceiling = automatic rejection. This is a core commercial governance function.

**What we have:** Salary range fields on demands and candidates. No rate card structure, no ceiling enforcement.

**What competitors do:** Vincere has billing rate management. Bullhorn has rate/margin tracking.

**Proposal:**
- Add **Rate Card** entity per tenant per contract
- Rate card defines: profile → SFIA level → max daily rate (EUR) → currency → effective dates
- When a candidate is matched to a demand, system checks if candidate's rate falls within ceiling
- **Hard block** on shortlisting a candidate whose rate exceeds ceiling (SM override with documented justification)
- Margin calculation: (client rate ceiling - candidate cost rate) = margin per day
- Dashboard widget: margin overview across all active placements

---

### GAP-04: No Security Clearance Tracking
**Severity: CRITICAL**

**What's missing:** EUROCONTROL handles NATO-adjacent classified information. Candidates may require security clearances (NATO RESTRICTED, CONFIDENTIAL, SECRET). Clearance is granted by **national security authorities** and can take 3-18 months. Clearance has an expiry date.

**What we have:** Nothing. No clearance fields anywhere in the data model.

**What competitors do:** iCIMS supports custom compliance fields. Government-specific ATS tools (ClearanceJobs, etc.) are built around this.

**Proposal:**
- Add to candidate profile: `security_clearances` array
- Each entry: level (RESTRICTED/CONFIDENTIAL/SECRET/TOP SECRET), issuing authority (country), issue date, expiry date, status (ACTIVE/EXPIRED/PENDING/DENIED)
- Profile catalogue can specify required clearance level per profile
- Matching engine factors clearance status (no clearance + required = auto-exclude)
- Dashboard: clearance expiry alerts (30/60/90 day warnings)
- Clearance application tracking: status pipeline from "Application Submitted" → "Investigation" → "Granted" / "Denied"

---

### GAP-05: No Placement / Active Engagement Tracking
**Severity: ~~CRITICAL~~ EXCLUDED — EUROCONTROL uses a separate system for active engagement tracking. This tool focuses on recruitment up to onboarding/hire.**

**What's missing:** Our workflow ends at "Filled → Closed." But in T&M contracts, filling a position is the **beginning**, not the end. The placed contractor works for months/years. Brayton needs to track active placements: who is where, doing what, since when, at what rate, until when.

**What we have:** Demand lifecycle ends at Closed. No post-placement tracking.

**What competitors do:** Bullhorn and Vincere track active placements as first-class entities. Vincere's TimeTemp links placements to timesheets.

**Proposal:**
- Add **Placement** entity: links candidate + demand + tenant + contract terms
- Placement fields: start date, end date (estimated), daily rate, SFIA level, profile, status (ACTIVE/ON_NOTICE/ENDED), location, reporting manager
- New demand lifecycle state: `Filled → Placed` (placement created) → `Closed` (when placement ends or for record-keeping)
- **Active Placements Dashboard**: all current contractors, by tenant, with contract end dates, renewal alerts
- Placement history per candidate: full timeline of all engagements

---

### GAP-06: No Replacement / Offboarding Workflow
**Severity: CRITICAL**

**What's missing:** When a placed contractor leaves (resignation, contract end, performance), the contract typically requires a qualified replacement within 5-15 business days at the same or higher skill level, with a knowledge-transfer period. This is a contractual SLA.

**What we have:** Nothing. Demand goes to Closed. No replacement pipeline.

**What competitors do:** Bullhorn has redeployment tracking. Vincere links to contractor lifecycle events.

**Proposal:**
- Add **Replacement Workflow** triggered from an active placement:
  - SM marks placement as "Ending" (reason: resignation/contract end/performance/client request)
  - System auto-creates a new demand pre-populated from the original profile catalogue entry
  - Demand status starts at "Open" with an **SLA countdown** (e.g., 10 business days to fill)
  - Knowledge-transfer checklist attached to the outgoing placement (documentation, handover meetings, access revocation)
  - SLA tracker visible to client: "Replacement due by [date], current status: [Matching/Shortlisted/etc.]"

---

### GAP-07: No SLA / KPI Tracking
**Severity: CRITICAL**

**What's missing:** Sophisticated clients like EUROCONTROL contractualize staffing KPIs as SLAs. The tool should track and display these in real-time — both for internal management and client-facing transparency.

**What we have:** Dashboard metrics exist (fill rate, time-to-fill) but no SLA framework, no client-visible KPI dashboard, no alerting on SLA breaches.

**What competitors do:** Bullhorn has SLA tracking. Enterprise tools (SAP, Workday) have configurable SLA dashboards.

**Proposal:**
- Add **SLA Configuration** per tenant:
  - Time-to-fill: max business days from demand creation to placement (default: 15)
  - CV-to-interview ratio: target CVs submitted per interview secured (benchmark: 3:1)
  - Replacement time: max business days for replacement contractor (default: 10)
  - Staff retention rate: target % per quarter
  - Quality score: client satisfaction survey at 3/6 months
- **SLA Dashboard** (client-visible):
  - Current period performance vs. targets
  - Trend lines over time
  - Breach alerts with escalation (amber at 80% of SLA, red at breach)
  - Exportable SLA reports for governance meetings
- **Internal SLA view** (SM/Recruiter):
  - Same metrics plus margin data, cost analysis, utilization rates

---

### GAP-08: No CV Verification / Evidence Trail
**Severity: HIGH**

**What's missing:** DIGIT-TM III explicitly states that inaccurate or non-verifiable CV information is grounds for exclusion. EU institutions verify degrees, certifications, employment history, and language skills. A recruitment tool should facilitate and track this verification.

**What we have:** CV parsed by AI. No verification workflow. No evidence attachments.

**Proposal:**
- Add **Verification Checklist** per candidate per demand submission:
  - Education: verified (Y/N), evidence (uploaded document/link), verified by, date
  - Certifications: verified (Y/N), certification number, expiry date, evidence
  - Employment history: reference check status per employer
  - Language skills: self-declared level, test result (if available)
- AI assists: flag claims that seem inconsistent (e.g., "10 years experience" but graduated 5 years ago)
- Verification status visible on candidate profile: verified / partially verified / unverified
- Client sees verification status on shortlisted candidates

---

### GAP-09: No Contract / Framework Agreement Management
**Severity: HIGH**

**What's missing:** Brayton may operate under multiple framework agreements with EUROCONTROL (different lots, periods, scopes). The tool should track which demands fall under which contract.

**What we have:** Tenants represent customers but no contract structure within a tenant.

**Proposal:**
- Add **Contract** entity within tenant: contract reference, lot number, start date, end date, max value, rate card reference, SLA terms
- Demands linked to a specific contract
- Contract budget tracking: total placed value vs. contract ceiling
- Contract expiry alerts
- Reporting scoped by contract

---

### GAP-10: No Language Proficiency Tracking
**Severity: MEDIUM**

**What's missing:** EUROCONTROL requires specific language proficiencies (typically English B2+ minimum, sometimes French). EU Common European Framework of Reference (CEFR) levels are the standard.

**What we have:** Languages are part of parsed CV skills. No structured CEFR-level tracking.

**Proposal:**
- Add structured language proficiency to candidate profile: language + CEFR level (A1-C2) + self-declared / tested
- Profile catalogue specifies required language + minimum CEFR level
- Matching engine includes language compliance check
- Filter candidates by language proficiency in search

---

## Category 2: EU AI Act & Regulatory Compliance

The tool uses AI extensively for recruitment decisions (matching, scoring, assessments). Under the EU AI Act, **recruitment AI is classified as high-risk (Annex III, Category 4)**. Full enforcement: **August 2, 2026**. Non-compliance penalties: up to €35M or 7% of global turnover. Building for EUROCONTROL without addressing this would be a serious oversight.

---

### GAP-11: No EU AI Act Compliance Framework
**Severity: CRITICAL**

**What's missing:** The EU AI Act requires high-risk AI systems (which this is) to have: mandatory risk assessments, technical documentation, bias testing, human oversight mechanisms, transparency disclosures, continuous monitoring, and conformity assessment.

**What we have:** "AI scoring is advisory, human override available." That's one line in business rules — not a compliance framework.

**Proposal:**
- **AI Transparency Log**: every AI decision (match score, assessment score, JD suggestion) logged with: model used, input summary, output, confidence, timestamp
- **Human-in-the-loop enforcement**: no AI score can move a candidate forward without human review and explicit approval. This is already partially true (recruiter reviews matches) but must be formalized
- **AI System Card**: public-facing documentation describing each AI feature, its purpose, limitations, and data used
- **Conformity assessment documentation**: maintained per Article 9 requirements
- **Settings page**: per-tenant toggle to enable/disable AI features (some clients may not want AI-driven decisions)

---

### GAP-12: No Bias Detection / Adverse Impact Analysis
**Severity: ~~CRITICAL~~ ON HOLD — Deferred to a future phase.**

**What's missing:** NYC AEDT law (2023) already requires annual bias audits. The EU AI Act mandates bias testing for high-risk systems. EUROCONTROL as a pan-European organization will be particularly sensitive to fairness.

**What we have:** Nothing. No demographic tracking on candidates, no bias analysis on match scores.

**Proposal:**
- **Optional demographic data collection** (candidate self-reports, voluntary): gender, age range, nationality — stored separately, never used in matching
- **Adverse impact analysis dashboard** (Admin only):
  - Selection rates by demographic group at each pipeline stage (matched, shortlisted, interviewed, offered, placed)
  - Four-fifths rule calculation (if selection rate for any group < 80% of highest group, flag)
  - Quarterly automated report generation
- **Match score distribution analysis**: detect if scores systematically differ by demographic group
- **JD bias scanner**: AI checks JD text for gendered ("rockstar," "ninja"), ageist, or exclusionary language before publishing

---

### GAP-13: No AI Explainability for Match Decisions
**Severity: CRITICAL**

**What's missing:** Under the EU AI Act, individuals affected by high-risk AI decisions have a right to meaningful explanation. Our matching produces scores but doesn't explain WHY in human-readable terms.

**What we have:** Dimension scores (skills: 85, experience: 80, etc.). Numbers without narrative.

**What competitors do:** Jobvite's explainable AI shows reasoning. Greenhouse's structured scorecards create defensible records.

**Proposal:**
- Each match result includes **AI narrative explanation**: "Candidate scored 85/100. Strong match on cloud architecture skills (AWS, Kubernetes) and 8 years relevant experience exceeding the 5-year minimum. Gap: no Azure DevOps certification (preferred, not required). Location compatible (London, remote-friendly role)."
- Explanation stored alongside score for audit purposes
- Client sees explanations on shortlisted candidates
- Explanation generation adds ~$0.01 per candidate to AI costs — negligible

---

### GAP-14: No AI Model Versioning / Monitoring
**Severity: HIGH**

**What's missing:** EU AI Act requires continuous monitoring of AI system performance. If we update prompts or switch models, we need to track what version produced what results.

**What we have:** "All prompts versioned in code." But no runtime tracking of which model/prompt version produced which output.

**Proposal:**
- Every AI call logged with: prompt version hash, model ID (e.g., claude-sonnet-4-6), input token count, output token count, latency, cost estimate
- AI performance dashboard: accuracy trends over time (human override rate as proxy for AI quality)
- When prompts change, flag that results from new vs. old version should not be directly compared
- A/B testing capability for prompt improvements

---

### GAP-15: No ESCO Skills Taxonomy Integration
**Severity: HIGH**

**What's missing:** ESCO (European Skills, Competences, Qualifications and Occupations) is the EU's multilingual classification. Using ESCO alignment for skills matching would signal regulatory sophistication to EUROCONTROL and enable standardized skills vocabulary across the platform.

**What we have:** Free-form skill arrays (JSONB). No taxonomy.

**What competitors do:** Beamery and enterprise tools increasingly use Lightcast (33,000+ skills). EU public employment services use ESCO.

**Proposal:**
- Integrate ESCO taxonomy as the canonical skills vocabulary
- AI CV parsing maps extracted skills to ESCO codes
- JDs use ESCO-aligned skill tags (with autocomplete)
- Matching operates on ESCO codes (semantic matching, not string matching)
- Enables: skills gap analysis, supply/demand reporting, cross-border skill comparability
- ESCO API is free and maintained by the European Commission

---

## Category 3: Competitive Feature Gaps

Features that leading competitors offer and that would strengthen the platform's value proposition.

---

### GAP-16: No Timesheet / Hours Tracking
**Severity: HIGH**

**What's missing:** In T&M contracts, billing is based on hours/days worked. Vincere's TimeTemp and Bullhorn One provide seamless placement-to-timesheet-to-invoice workflows.

**What we have:** Nothing post-placement.

**Proposal:**
- Add **Timesheet Module** (can be Phase 2):
  - Contractors submit weekly timesheets (hours per day, project code)
  - SM/client approves timesheets
  - Approved hours × daily rate = billing amount
  - Monthly invoice generation
  - Timesheet history per placement
- Even without full invoicing, timesheet tracking demonstrates governance

---

### GAP-17: No Talent Pool / Pipeline Nurturing
**Severity: HIGH**

**What's missing:** Lever and Beamery excel at passive candidate nurturing — maintaining warm relationships with candidates not currently placed but potentially suitable for future demands.

**What we have:** Candidates exist in a global pool but there's no concept of "warm pipeline" or proactive engagement.

**Proposal:**
- Add **Talent Pool** feature: named pools (e.g., "Cloud Engineers — Belgium," "Java Seniors — Cleared")
- SM/Recruiter can add candidates to pools manually or via saved search criteria
- Pool analytics: size, average availability date, skill distribution
- When a new demand is created, system suggests relevant pools to search first
- Optional: automated re-engagement emails to pooled candidates ("Are you still available?")

---

### GAP-18: No Structured Candidate Rejection Reasons
**Severity: HIGH**

**What's missing:** Greenhouse's structured hiring approach requires documented reasons for every candidate rejection. This creates a defensible audit trail — critical for government clients.

**What we have:** Shortlist entries have status (proposed/approved/rejected) and notes. But no structured rejection taxonomy.

**Proposal:**
- Add **rejection reason taxonomy**: skills mismatch, experience insufficient, clearance not met, rate exceeds ceiling, availability mismatch, language requirements not met, client preference, other
- Required when rejecting at any stage (shortlist, interview, offer)
- Aggregated rejection analytics: most common rejection reasons by profile, by tenant
- Feeds back into demand quality improvement (if 80% are rejected for "skills mismatch," the JD may need refinement)

---

### GAP-19: No Client Satisfaction / Quality Scoring
**Severity: HIGH**

**What's missing:** T&M contracts often include quality-of-hire measurement at 3/6 months. No mechanism to capture this.

**What we have:** Nothing post-placement.

**Proposal:**
- **Placement Review** triggered at configurable intervals (3 months, 6 months, 12 months):
  - Client rates contractor: technical competence, communication, reliability, cultural fit (1-5 scale)
  - Optional free-text feedback
  - Results stored per placement
- Aggregate quality scores feed into:
  - Supplier KPI dashboard (visible to client)
  - Candidate profile (track record across placements)
  - Brayton internal quality management

---

### GAP-20: No Supply/Demand Skills Intelligence
**Severity: MEDIUM**

**What's missing:** Beamery's talent intelligence shows skills supply vs. demand. For a staffing company, knowing "we have 15 cloud architects in our pool but 23 open demands" is strategically critical.

**What we have:** Dashboard metrics exist but no supply/demand analysis.

**Proposal:**
- **Skills Supply/Demand Dashboard**:
  - Supply: candidates in pool by top skills (from parsed CVs)
  - Demand: open demands by required skills
  - Gap visualization: skills where demand > supply (recruitment priority) and supply > demand (bench strength)
  - Trend over time: is the gap growing or shrinking?

---

### GAP-21: No Configurable Workflow Engine
**Severity: MEDIUM**

**What's missing:** Different contracts may require different workflows. EUROCONTROL may want an extra "Client Technical Interview" step that another client doesn't need.

**What we have:** Fixed 8-state demand lifecycle.

**Proposal:**
- Make the demand lifecycle **configurable per tenant/contract**:
  - Core states (Draft, Open, Closed) are fixed
  - Intermediate states can be added/removed/renamed per tenant
  - Transition rules configurable per tenant
- Default workflow matches current spec; EUROCONTROL tenant can add custom states

---

### GAP-22: No Candidate Ranking Comparison View
**Severity: MEDIUM**

**What's missing:** When reviewing shortlisted candidates, there's no side-by-side comparison view.

**What we have:** Ranked list with individual profiles. No comparison.

**Proposal:**
- **Comparison view**: select 2-4 candidates, see side-by-side table of all scoring dimensions, qualifications, experience, certifications, availability, rate
- Exportable as PDF for client decision meetings

---

### GAP-23: No Document Generation (Formatted CV)
**Severity: MEDIUM**

**What's missing:** Staffing companies typically submit CVs to clients in a **standardized company template** — not the candidate's raw CV. SprintCV exists solely for DIGIT-TM formatted CV generation.

**What we have:** Raw CV storage and parsed data. No formatted output.

**Proposal:**
- **CV Template Engine**: generate client-ready CVs from parsed data in Brayton's branded template
- Template customizable per tenant/contract (EUROCONTROL may require a specific format)
- Includes: profile mapping, SFIA level, skills matrix, experience summary, certifications, language levels
- Export as PDF/DOCX
- This is a high-impact, moderate-effort feature that directly mirrors SprintCV's core value

---

## Category 4: Audit & Compliance Gaps

---

### GAP-24: Audit Retention Period Too Short
**Severity: CRITICAL**

**What's missing:** Our spec says "retained for 12 months." EU institutional contracts require audit records retained for **5 years post-final-payment**. Final payment on a multi-year framework could be 4+ years from start. Effectively: retain everything for 7-10 years.

**What we have:** 12-month retention.

**Proposal:**
- Change audit log retention to **7 years** (configurable per tenant/contract)
- Implement tiered storage: hot (recent 12 months in primary DB), cold (older logs in Azure Blob as compressed JSON)
- Ensure GDPR compatibility: audit logs must be anonymized for deleted candidates but the audit event itself retained

---

### GAP-25: No Approval Chain / Four-Eyes Principle
**Severity: CRITICAL**

**What's missing:** Government procurement often requires a **four-eyes principle** — critical decisions (candidate submission to client, rate approval, placement confirmation) require approval from a second person.

**What we have:** Single-actor transitions. Any SM can move a demand through any allowed transition alone.

**Proposal:**
- Add **configurable approval gates** per tenant:
  - Shortlist submission to client: requires SM approval (even if recruiter prepared it)
  - Rate override (above ceiling): requires Admin approval
  - Placement confirmation: requires SM + Customer approval
- Approval request → notification → approve/reject with comments
- Audit log captures full approval chain

---

### GAP-26: No Data Export for External Audit
**Severity: HIGH**

**What's missing:** EU institutions retain full audit rights (DG DIGIT, OLAF, European Court of Auditors). They may request a full data export of all recruitment decisions for a specific contract period.

**What we have:** CSV/PDF exports for individual entities. No bulk audit export.

**Proposal:**
- **Audit Export** function (Admin only): export all data for a specific tenant + date range as a structured archive:
  - All demands with full lifecycle history
  - All candidate profiles (as submitted, not current)
  - All match results with AI explanations
  - All shortlist decisions with reasons
  - All interview scorecards
  - All assessment results
  - All approval chains
  - All audit log entries
- Format: ZIP containing structured JSON + PDFs
- Triggered on-demand or schedulable

---

## Category 5: Candidate & Client Experience

---

### GAP-27: No Candidate Experience Scoring
**Severity: HIGH**

**What's missing:** Industry data shows candidate NPS averages -7 (vs. hiring manager +73). Tracking candidate experience signals professionalism to clients.

**What we have:** Nothing.

**Proposal:**
- **Candidate NPS survey** triggered at key pipeline stages:
  - After application/registration
  - After assessment completion
  - After interview
  - After placement or rejection
- Short survey (1 question NPS + 1 optional comment)
- Aggregate cNPS visible on internal dashboards
- Improvement tracking over time

---

### GAP-28: No Client Portal Branding
**Severity: MEDIUM**

**What's missing:** When EUROCONTROL logs in, they should see a portal that feels like "their" recruitment dashboard, not a generic tool.

**What we have:** Single UI for all roles. No tenant-specific branding.

**Proposal:**
- Allow per-tenant customization:
  - Logo (displayed in header when customer is logged in)
  - Accent color override (optional)
  - Welcome message on customer dashboard
- Lightweight — just logo + color, not full white-labeling

---

## Priority Matrix

### Must-Have Before EUROCONTROL Demo (Critical)

| # | Gap | Effort | Impact |
|---|-----|--------|--------|
| GAP-01 | Profile Catalogue | High | Differentiating — shows you understand EU procurement |
| GAP-02 | SFIA Alignment | Medium | Industry standard, expected by sophisticated clients |
| GAP-03 | Rate Card Management | Medium | Core T&M commercial governance |
| GAP-04 | Security Clearance | Medium | Non-negotiable for EUROCONTROL |
| GAP-05 | Placement Tracking | High | Without this, the tool stops at recruitment — misses operations |
| GAP-06 | Replacement Workflow | Medium | Contractual SLA, demonstrates readiness |
| GAP-07 | SLA/KPI Dashboard | High | The single most impressive thing to show a client |
| GAP-11 | EU AI Act Compliance | High | Legal requirement by Aug 2026, shows regulatory awareness |
| GAP-12 | Bias Detection | Medium | EU AI Act requirement + DEI commitment signal |
| GAP-13 | AI Explainability | Low | Low-cost, high-impact — just add narrative to existing scores |
| GAP-24 | 7-Year Audit Retention | Low | Config change, massive compliance signal |
| GAP-25 | Four-Eyes Approval | Medium | Government governance standard |

### Should-Have (High Priority, Phase 2)

| # | Gap | Effort | Impact |
|---|-----|--------|--------|
| GAP-08 | CV Verification | Medium | Demonstrates due diligence |
| GAP-09 | Contract Management | Medium | Multi-contract governance |
| GAP-10 | Language CEFR Tracking | Low | Easy win for EU clients |
| GAP-14 | AI Model Monitoring | Medium | EU AI Act continuous monitoring |
| GAP-15 | ESCO Taxonomy | High | Differentiating for EU market |
| GAP-18 | Structured Rejection Reasons | Low | Audit defensibility |
| GAP-19 | Client Satisfaction Scoring | Low | Quality management signal |
| GAP-23 | Formatted CV Generation | Medium | High-value, directly useful |
| GAP-26 | Audit Export | Medium | Audit readiness |

### Nice-to-Have (Phase 3+)

| # | Gap | Effort | Impact |
|---|-----|--------|--------|
| GAP-16 | Timesheet Module | High | Extends into operations |
| GAP-17 | Talent Pool Nurturing | Medium | Proactive sourcing |
| GAP-20 | Supply/Demand Intelligence | Medium | Strategic planning |
| GAP-21 | Configurable Workflow | High | Flexibility |
| GAP-22 | Comparison View | Low | UX improvement |
| GAP-27 | Candidate NPS | Low | Experience tracking |
| GAP-28 | Client Portal Branding | Low | Polish |

---

## Impact on Current Spec

If all Critical gaps are addressed, the following documents need updates:

| Document | Sections Affected |
|----------|------------------|
| **REQUIREMENTS.md** | New sections: Profile Catalogue (§4.7), SFIA Framework (§4.8), Rate Cards (§4.9), Security Clearance (§4.10), Placements (§4.11), Replacement Workflow (§4.12), SLA Management (§4.13), EU AI Act Compliance (§8.3), Bias Detection (§8.4). Updates: audit retention (§11.4), approval gates (§3.2) |
| **ARCHITECTURE.md** | New tables: profiles, profile_requirements, rate_cards, security_clearances, placements, sla_configs, sla_metrics, approval_requests, ai_decision_logs, candidate_demographics. New API endpoints. New backend modules. |
| **BUSINESS_WORKFLOW.md** | New workflows: Placement Management, Replacement Pipeline, SLA Monitoring, CV Verification, Approval Chain, Periodic Quality Review. Updated demand lifecycle (add Placed state). |

---

## Competitive Positioning Statement

With these gaps addressed, Brayton AI CV App would be positioned as:

> **"The only recruitment platform purpose-built for T&M staffing governance in EU institutional procurement — with profile catalogue compliance, SFIA-aligned seniority validation, rate card enforcement, security clearance lifecycle management, real-time SLA dashboards, and EU AI Act-compliant matching, all in a multi-tenant architecture designed for framework contract operations."**

No single competitor covers all of this. Bullhorn and Vincere handle T&M operations but lack AI and EU regulatory compliance. SAP/Workday handle enterprise compliance but aren't staffing-specific. Manatal and Beamery lead on AI but have no T&M governance. This tool would occupy an uncontested niche.
