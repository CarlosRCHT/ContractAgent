# Contoso Contract Management - Multi-Agent Demo Test Scenarios

**Document ID:** AC-TEST-SCEN-2024-001
**Version:** 1.0
**Date:** January 2024
**Owner:** Contract Management Automation Team

---

## Overview

This document defines test scenarios for the Contoso Contract Management multi-agent Copilot Studio solution. Each scenario tests specific agent capabilities and cross-agent interactions.

### Agent Architecture

| Agent | Role |
|---|---|
| **Contract Intake Agent** | Classification, urgency assessment, routing |
| **Legal Review Agent** | Playbook comparison, clause analysis, risk flagging |
| **Compliance & Risk Agent** | Tax, insurance, cybersecurity, regulatory checks |
| **Summary & Reporting Agent** | Term extraction, obligation tracking, executive summary |

### Knowledge Sources

| Source | Description |
|---|---|
| corporate-procurement-policy.md | Approval thresholds, mandatory clauses, prohibited terms, payment standards |
| legal-review-playbook.md | Clause-by-clause checklist, risk classification, approved language |
| contract-template-vendor-agreement.md | Standard vendor agreement template |
| contract-template-nda.md | Standard mutual NDA template |
| compliance-checklist.md | Tax, insurance, cybersecurity, regulatory, ESG requirements |

---

## Test Scenario 1: Happy Path - Compliant Contract

**Test ID:** TS-001
**Priority:** P1 - Critical
**Input:** sample-contract-compliant.md (NovaTech Solutions Inc., Cloud Infrastructure, $320K/year)

### Contract Intake Agent - Expected Behavior

| Step | Expected Action | Expected Output |
|---|---|---|
| Classification | Identify as Vendor Services Agreement - Technology/SaaS | Contract Type: Technology/SaaS; Category: Cloud Infrastructure |
| Value Assessment | Extract annual value of $320,000 | Value: $320,000 USD/year |
| Approval Routing | Map to Director-level approval (AC-PROC-POL S2.1: $250K-$499K = VP) | Required Approver: Vice-President; Note: value is in $250K-$499K range |
| Urgency | Standard priority (no urgency indicators) | Priority: Standard; SLA: 15 business days |
| Routing | Route to Legal Review Agent + Compliance & Risk Agent | Routed to: Legal Review, Compliance & Risk |

### Legal Review Agent - Expected Behavior

| Step | Expected Action | Expected Output |
|---|---|---|
| Template Comparison | Compare against vendor agreement template | Deviation Level: Low (follows standard template closely) |
| Mandatory Clauses | Verify all 8 mandatory clauses present | All mandatory clauses present: Indemnification, LoL, IP, Confidentiality, Termination, Force Majeure, Data Protection, Governing Law |
| Prohibited Terms | Scan for prohibited terms | No prohibited terms detected |
| Risk Classification | Assess overall risk | Risk Level: Minor; No Major or Moderate flags |
| Payment Terms | Verify Net 45 against policy | Payment terms compliant (Net 45 for $50K-$499K range) |
| Liability Cap | Verify cap >= max(2x annual, $1M) | Cap: $1,000,000 (max of 2x$320K=$640K or $1M). Compliant. |

### Compliance & Risk Agent - Expected Behavior

| Step | Expected Action | Expected Output |
|---|---|---|
| Insurance | Verify coverage meets Technology/SaaS minimums | Compliant: CGL $2M/$5M, Prof Liability $5M/$10M, Cyber $10M |
| Cybersecurity | Verify SOC 2, ISO 27001, encryption, MFA, pen testing | Compliant: All cybersecurity requirements met |
| Data Residency | Verify domestic-only storage | Compliant: East Region and West Region data centres |
| Tax | Verify Sales Tax registration numbers present | Compliant: Tax registrations provided |
| Privacy | Verify Data Privacy Regulation and Regional Privacy Regulation compliance | Compliant: Data protection provisions present |

### Summary & Reporting Agent - Expected Output

```
CONTRACT REVIEW SUMMARY
========================
Contract: AC-VSA-2024-0472 (NovaTech Solutions Inc.)
Type: Vendor Services Agreement - Technology/SaaS (Cloud Infrastructure)
Value: USD $320,000/year
Term: 3 years (March 1, 2024 - February 28, 2027) + auto-renewal (1-year, max 3 years cumulative)
Risk Classification: MINOR
Recommendation: APPROVE - proceed to execution with Director/VP approval

Key Terms:
- Payment: Net 45 (compliant)
- Liability Cap: $1,000,000 (compliant)
- Insurance: All minimums met
- Cybersecurity: SOC 2 Type II, ISO 27001, AES-256/TLS 1.3
- Data Residency: domestic-only (the designated forum/secondary location)
- Governing Law: New York State/the domestic jurisdiction

Issues: None requiring remediation
Action Required: Route to VP for approval signature
```

---

## Test Scenario 2: High-Risk Contract Detection

**Test ID:** TS-002
**Priority:** P1 - Critical
**Input:** sample-contract-high-risk.md (GlobalServe Consulting Ltd., IT Consulting, $1.2M/year)

### Contract Intake Agent - Expected Behavior

| Step | Expected Action | Expected Output |
|---|---|---|
| Classification | Identify as Services Agreement - Professional/Consulting (IT) | Contract Type: Professional/Consulting; Category: IT Consulting & Digital Transformation |
| Value Assessment | Extract annual value of $1,200,000 | Value: $1,200,000 USD/year |
| Approval Routing | Map to EVP/CFO approval ($1M-$4.99M) | Required Approver: Executive Vice-President / CFO |
| Urgency | Escalated priority due to high value and cross-border vendor | Priority: High; SLA: 20 business days |
| Routing | Route to Legal + Compliance + Tax department review (cross-border > $50K) | Routed to: Legal Review, Compliance & Risk, Tax Department |

### Legal Review Agent - Expected Behavior

The agent should identify ALL of the following Major risk flags:

| # | Risk Flag | Risk Level | Detail |
|---|---|---|---|
| 1 | Unlimited liability for Contoso (S6.3) | **Major** | Client liable "without limitation" - strictly prohibited |
| 2 | Auto-renewal for 5-year terms (S1.2) | **Major** | Exceeds 3-year maximum per AC-PROC-POL S4 |
| 3 | Missing cybersecurity requirements | **Major** | No cybersecurity section for $1.2M IT consulting contract |
| 4 | Missing insurance requirements | **Major** | No insurance section at all |
| 5 | Weak/one-sided indemnification (S5) | **Major** | Contoso indemnifies vendor for use of deliverables |
| 6 | No termination for convenience (S9) | **Major** | Only for-cause termination with punitive termination fee |
| 7 | Vendor owns custom deliverables (S7) | **Major** | License terminates with agreement |
| 8 | Foreign governing law - Delaware (S14) | **Major** | Requires General Counsel approval |
| 9 | Data stored outside the domestic jurisdiction (S10.2) | **Major** | US, India, or other locations |
| 10 | Liability cap below 1x annual ($300K on $1.2M) | **Major** | Well below minimum |

Expected recommendation: **DO NOT EXECUTE. Comprehensive renegotiation required.**

### Compliance & Risk Agent - Expected Behavior

| Domain | Expected Finding |
|---|---|
| Insurance | FAIL: No insurance requirements present |
| Cybersecurity | FAIL: No cybersecurity section; no SOC 2, ISO 27001, encryption, MFA |
| Data Residency | FAIL: Data may be stored outside the domestic jurisdiction (US, India) |
| Tax | FLAG: Cross-border vendor (US) - withholding tax review needed |
| Privacy | FLAG: Missing Data Privacy Regulation compliance for data in US/India |
| Anti-corruption | FLAG: International vendor > $100K without applicable anti-corruption laws clause |

---

## Test Scenario 3: Missing Clauses Detection

**Test ID:** TS-003
**Priority:** P1 - Critical
**Input:** sample-contract-missing-clauses.md (SkyBridge Analytics Corp., Data Analytics, $180K/year)

### Expected Risk Flags

| # | Missing/Deficient Item | Risk Level | Expected Agent |
|---|---|---|---|
| 1 | No confidentiality clause | **Major** | Legal Review Agent |
| 2 | No termination for convenience | **Major** | Legal Review Agent |
| 3 | Vague IP ownership ("case-by-case basis") | **Moderate** | Legal Review Agent |
| 4 | Pre-existing IP license is term-limited | **Moderate** | Legal Review Agent |
| 5 | Missing ISO 27001 | **Minor** | Compliance & Risk Agent |
| 6 | Missing enterprise-specific force majeure events | **Minor** | Legal Review Agent |

### Expected Recommendation
MODERATE-TO-MAJOR risk. Negotiate addition of confidentiality clause and termination for convenience before execution. Clarify IP ownership.

---

## Test Scenario 4: Expired Terms Detection

**Test ID:** TS-004
**Priority:** P1 - Critical
**Input:** sample-contract-expired-terms.md (ProMaintain Services Inc., Maintenance, $95K/year)

### Expected Risk Flags

| # | Issue | Risk Level | Expected Agent |
|---|---|---|---|
| 1 | Contract expired June 30, 2023 - no renewal | **Major** | Contract Intake Agent |
| 2 | Insurance minimums below current policy | **Major** | Compliance & Risk Agent |
| 3 | Liability cap ($95K) below $1M minimum | **Major** | Legal Review Agent |
| 4 | industry safety audit certification expired (2020, valid 2 years) | **Moderate** | Compliance & Risk Agent |
| 5 | maintenance organization certificate needs re-verification | **Moderate** | Compliance & Risk Agent |
| 6 | Confidentiality survival below standard (3y vs 5y) | **Moderate** | Legal Review Agent |
| 7 | Governing law is a different state, not New York State | **Moderate** | Legal Review Agent |
| 8 | Payment terms don't match current policy | **Minor** | Legal Review Agent |

### Expected Recommendation
MAJOR risk. Execute new agreement under current standards. Verify all certifications. Do not continue under expired agreement.

---

## Test Scenario 5: NDA-Specific Review

**Test ID:** TS-005
**Priority:** P2 - High
**Input:** contract-template-nda.md (used as-is with sample counterparty details filled in)

### Contract Intake Agent - Expected Behavior

| Step | Expected Output |
|---|---|
| Classification | Contract Type: Mutual NDA |
| Urgency | Standard; SLA: 3 business days (template NDA) |
| Routing | Legal Review Agent only (NDAs do not require Compliance review unless involving personal data) |

### Legal Review Agent - Expected Behavior

| Step | Expected Output |
|---|---|
| Template match | Matches standard AC NDA template; minimal deviations expected |
| Confidentiality term | 5-year survival + indefinite for trade secrets - compliant |
| Return/destruction | 30-day return/destruction - compliant |
| Governing law | New York State law - compliant |
| Data protection | Section 5 present with Data Privacy Regulation/Regional Privacy Regulation - compliant |
| Non-solicitation | 12-month non-solicitation - compliant |

### Expected Recommendation
LOW RISK. Approve for execution. Standard template NDA.

---

## Test Scenario 6: Urgency Escalation

**Test ID:** TS-006
**Priority:** P2 - High
**Input:** Simulated contract submission with urgency indicators

### Scenario Details

A $750,000 technology services contract submitted with the following context:
- Business owner indicates critical deadline: "Must be executed within 5 business days due to regulatory compliance requirement from the regulatory authority."
- Contract is from a sole-source vendor (only vendor with required industry certification).
- VP Operations has flagged as mission-critical.

### Contract Intake Agent - Expected Behavior

| Step | Expected Output |
|---|---|
| Value assessment | $750,000 - requires SVP approval |
| Urgency detection | EXPEDITED: Regulatory deadline within 10 business days + safety-critical |
| SLA assignment | Expedited SLA: 10 business days (vs standard 20 for > $500K) |
| Special flags | Sole-source > $100K: VP approval + written justification needed |
| Special flags | Safety-critical: VP Operations + VP Safety sign-off needed |
| Routing | Priority routing to Legal + Compliance with escalation to SVP |

### Expected Escalation Chain
1. Immediate notification to Legal department with expedited flag
2. Parallel review by Legal and Compliance
3. VP Operations and VP Safety sign-off for safety-critical designation
4. SVP approval for contract value
5. Sole-source justification documented

---

## Test Scenario 7: Multi-Domain Risk (Tax + Cyber + Insurance)

**Test ID:** TS-007
**Priority:** P2 - High
**Input:** Simulated contract with specific multi-domain issues

### Scenario Details

A $2,000,000/year data processing agreement with an international vendor (based in Ireland, with processing in the US and India):
- **Tax issues:** No withholding tax provisions; no permanent establishment risk assessment; no W-8BEN-E equivalent
- **Cybersecurity issues:** Vendor has SOC 2 Type I only (not Type II); data stored in US and India; no ISO 27001; TLS 1.1 still in use for some services
- **Insurance issues:** Cyber liability coverage of $5M (requires $15M for Data Processing per AC-PROC-POL S6.1); no additional insured endorsement

### Compliance & Risk Agent - Expected Behavior

| Domain | Finding | Risk Level |
|---|---|---|
| Tax | Missing withholding tax provisions for international vendor | **Major** |
| Tax | No permanent establishment assessment for $2M engagement | **Moderate** |
| Tax | No applicable tax forms (W-8BEN-E equivalent for Ireland) | **Moderate** |
| Cybersecurity | SOC 2 Type I only (Type II required) | **Major** |
| Cybersecurity | Data in US and India (domestic-only required) | **Major** |
| Cybersecurity | No ISO 27001 | **Major** |
| Cybersecurity | TLS 1.1 in use (TLS 1.2+ required) | **Major** |
| Insurance | Cyber liability $5M vs $15M required | **Major** |
| Insurance | Missing additional insured endorsement | **Moderate** |

### Expected Cross-Agent Coordination

1. Compliance Agent flags tax, cyber, and insurance issues
2. Legal Review Agent correlates compliance findings with contract clause review
3. Summary Agent consolidates into unified risk report with recommendations
4. Contract Intake Agent escalates to EVP/CFO (>$1M value) with multi-domain risk flag

---

## Test Scenario 8: Reporting and Summary Generation

**Test ID:** TS-008
**Priority:** P2 - High
**Input:** Multiple contracts reviewed in sequence (TS-001 through TS-004 results)

### Summary & Reporting Agent - Expected Behavior

The agent should generate a consolidated executive summary covering all reviewed contracts:

### Expected Output: Portfolio Summary Report

```
Contoso CONTRACT REVIEW - PORTFOLIO SUMMARY
================================================
Report Date: [Current Date]
Contracts Reviewed: 4
Review Period: Q1 2024

RISK DISTRIBUTION:
- Major Risk: 2 contracts (GlobalServe, ProMaintain)
- Moderate Risk: 1 contract (SkyBridge)
- Minor Risk: 1 contract (NovaTech)

CRITICAL ACTION ITEMS:
1. [URGENT] GlobalServe Consulting (AC-GS-2024-1187): DO NOT EXECUTE
 - 18 risk flags including unlimited liability, missing cybersecurity/insurance
 - Requires comprehensive renegotiation or vendor replacement
 - Escalation: General Counsel + CFO

2. [URGENT] ProMaintain Services (AC-MSA-2021-0156): CONTRACT EXPIRED
 - Operating without valid agreement since June 2023
 - Must execute new agreement under current policy standards
 - Action: Procurement to initiate emergency renewal process

3. [ACTION] SkyBridge Analytics (AC-SPA-2024-0298): CONDITIONAL APPROVAL
 - Add confidentiality clause and termination for convenience
 - Clarify IP ownership language
 - Target resolution: 10 business days

4. [APPROVE] NovaTech Solutions (AC-VSA-2024-0472): APPROVE
 - Fully compliant; route for VP signature

KEY COMPLIANCE GAPS ACROSS PORTFOLIO:
- Insurance: 2 contracts below current minimums
- Cybersecurity: 2 contracts missing requirements
- Confidentiality: 1 contract missing entirely
- Liability caps: 2 contracts below policy minimums

OBLIGATION TRACKING:
- Insurance certificate renewals due: [dates]
- SOC 2 report renewals: NovaTech (September 2024)
- Contract renewal decisions: NovaTech (December 2026)
```

---

## Test Scenario 9: Amendment Review

**Test ID:** TS-009
**Priority:** P3 - Medium
**Input:** Simulated amendment to the NovaTech contract (TS-001)

### Scenario Details

Amendment to increase NovaTech contract from $320,000 to $480,000/year (50% increase) to add additional cloud services.

### Contract Intake Agent - Expected Behavior

| Step | Expected Output |
|---|---|
| Change assessment | Cumulative change >25% of original value |
| Policy trigger | AC-PROC-POL S2.3: >25% requires new contract process |
| Routing | Flag that amendment exceeds change order threshold |
| Recommendation | New contract or major amendment with full review cycle |
| Approval level | VP approval (updated value $480K is in $250K-$499K range) |

---

## Test Scenario 10: Vendor Due Diligence Integration

**Test ID:** TS-010
**Priority:** P3 - Medium
**Input:** New vendor onboarding for Tier 1 vendor ($3M/year enterprise services)

### Expected Multi-Agent Flow

| Step | Agent | Expected Action |
|---|---|---|
| 1 | Contract Intake | Classify as Enterprise Services (On-site); Tier 1 Critical vendor |
| 2 | Contract Intake | Flag: CEO/Board approval required (>$1M); full due diligence |
| 3 | Compliance & Risk | Run full compliance checklist (all domains) |
| 4 | Compliance & Risk | Verify: $10M/$25M CGL, $10M Prof Liability, statutory WC, $5M Auto |
| 5 | Compliance & Risk | Verify: industry regulatory authority, industry safety audit, secure area clearances, Safety management alignment |
| 6 | Compliance & Risk | Tax: Cross-border review if international; withholding tax assessment |
| 7 | Legal Review | Full 26-item checklist review |
| 8 | Legal Review | Enterprise-specific force majeure events required |
| 9 | Summary & Reporting | Full due diligence report + contract review summary |
| 10 | Summary & Reporting | Generate Board-ready executive summary |

---

## Execution Notes

### Test Data Dependencies

| Scenario | Required Input Files |
|---|---|
| TS-001 | sample-contract-compliant.md, corporate-procurement-policy.md, legal-review-playbook.md, compliance-checklist.md |
| TS-002 | sample-contract-high-risk.md, corporate-procurement-policy.md, legal-review-playbook.md, compliance-checklist.md |
| TS-003 | sample-contract-missing-clauses.md, corporate-procurement-policy.md, legal-review-playbook.md |
| TS-004 | sample-contract-expired-terms.md, corporate-procurement-policy.md, compliance-checklist.md |
| TS-005 | contract-template-nda.md, legal-review-playbook.md |
| TS-006 | Simulated input (described in scenario) |
| TS-007 | Simulated input (described in scenario) |
| TS-008 | Results from TS-001 through TS-004 |
| TS-009 | sample-contract-compliant.md (as base); simulated amendment |
| TS-010 | Simulated input; all knowledge source files |

### Success Criteria

- All Major risk flags correctly identified (zero false negatives for Major risks)
- Compliant contract (TS-001) passes with no false Major flags
- Risk classification matches expected levels for each scenario
- Agent routing decisions align with AC-PROC-POL approval matrix
- Summary reports include all identified issues with policy references
- Cross-agent coordination produces consistent, non-contradictory findings

---

*This test scenario document is maintained by the Contract Management Automation Team. Updates should be coordinated with changes to the procurement policy, legal playbook, or compliance checklist.*
