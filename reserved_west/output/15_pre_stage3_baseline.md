# Pre-Stage 3 Baseline Report
**Document:** RW-BL-001
**Assurance cycle:** Reserved West Initiative 001
**Snapshot type:** Pre-Stage 3 permanent baseline
**Date:** 2026-08-06
**Status:** ✅ Baseline established

This report captures the state of the Reserved engine and assurance framework
immediately prior to Stage 3. It is the permanent reference point for all
subsequent assurance work. Any regression relative to this baseline is a
gate-blocking defect.

---

## 1. Version identifiers

| Item | Value |
|---|---|
| Engine version | **2.0.0** |
| Engine bundle path | `reserved-engine-2.0.0/` |
| Assurance framework version | Reserved West Initiative 001 |
| Reference calculator version | `ref-2026/27-v1.0` (IT) / `ref-cgt-2026/27-v1.0` (CGT) |
| Baseline document | RW-BL-001 (this document) |
| Snapshot date | 2026-08-06 |

---

## 2. Application test count

| Suite | Count | Result |
|---|---|---|
| Main application tests (`tests/`) | **523** | ✅ All passing |
| Standalone engine bundle tests (`reserved-engine-2.0.0/tests/`) | **152** | ✅ All passing |
| **Total** | **675** | ✅ All passing |

Test runner: pytest 9.1.1, Python 3.13.11.

---

## 3. Stage 1 results

**Gate 1: Core Calculations Verified**

| Metric | Value |
|---|---|
| Total scenarios | 30 |
| PASS (exact zero variance) | 30 |
| PASS_PENNY (≤ £0.01) | 0 |
| UNSUPPORTED_EXPECTED | 0 |
| REGRESSION_EL001 | 0 |
| FAIL | 0 |
| ERROR | 0 |
| EL-001 zone scenarios | 3 (all PASS) |

**Gate 1: ✅ PASSED**

Deliverables: docs 01–07 in `reserved_west/output/`.

---

## 4. Stage 2 results

**Gate 2: Representative Scenarios Reliable**

| Metric | Value |
|---|---|
| Total scenarios | 150 |
| PASS (exact zero variance) | 149 |
| PASS_PENNY (≤ £0.01) | 0 |
| UNSUPPORTED_EXPECTED | 1 (RW-S2-136: zero invoice — engine correctly rejects) |
| REGRESSION_EL001 | 0 |
| FAIL | 0 |
| ERROR | 0 |
| EL-001 zone scenarios | 17 (all PASS) |
| Threshold boundary scenarios | 30 (all PASS) |
| Student loan scenarios | 30 (all PASS) |
| Pension RaS scenarios | 15 (all PASS) |
| CGT scenarios | 25 (all PASS) |
| Sequential journey scenarios | 20 (all PASS) |
| Edge case scenarios | 15 (14 PASS + 1 UNSUPPORTED_EXPECTED) |

**Gate 2: ✅ PASSED**

Deliverables: docs 08–13 in `reserved_west/output/`.

---

## 5. Combined assurance summary

| Metric | Total |
|---|---|
| Total scenarios executed (Stages 1 + 2) | 180 |
| Scenarios PASS or UNSUPPORTED_EXPECTED | 180 |
| EL-001 zone scenarios (all PASS) | 20 |
| Active defects | **0** |
| Open gate failures | **0** |

---

## 6. Regression tests

| Defect | Test file | Test count | Status |
|---|---|---|---|
| EL-001 (Moving Personal Allowance) | `tests/test_el001_regression.py` | 18 | ✅ All green |
| EL-002 (CGT BRL sourced from versioned config) | `tests/test_capital_gains.py` | 1 dedicated regression test | ✅ Green |

Total regression tests: **18 EL-001 family + 1 EL-002 regression** (within 523 total).

---

## 7. Historical defects

| ID | Summary | Severity at discovery | Status | Resolved in |
|---|---|---|---|---|
| EL-001 | Moving Personal Allowance — incremental IT applied end-state PA across full interval | Medium | ✅ Resolved | Engine v2.0.0 |
| EL-002 | CGT BASIC_RATE_LIMIT sourced from module-level constant instead of versioned config | Low | ✅ Resolved | Engine v1.0.0 |

**Open defects: 0**

---

## 8. Supported capabilities (as at baseline)

| Capability | Status |
|---|---|
| Income tax — England/Wales/NI | ✅ Supported |
| Personal Allowance (£12,570) | ✅ Supported |
| Personal Allowance taper (ANI > £100,000) | ✅ Supported (EL-001 resolved in v2.0.0) |
| Basic rate (20%) | ✅ Supported |
| Higher rate (40%) | ✅ Supported |
| Additional rate (45%, above £125,140) | ✅ Supported |
| Class 4 NI — main rate (6%, LPL–UPL) | ✅ Supported |
| Class 4 NI — upper rate (2%, above UPL) | ✅ Supported |
| Pension Relief at Source (gross; BRL extension + ANI reduction) | ✅ Supported |
| Student Loan Plan 1 | ✅ Supported (2025/26 and 2026/27) |
| Student Loan Plan 2 | ✅ Supported (2025/26 and 2026/27) |
| Student Loan Plan 4 | ✅ Supported (2025/26 and 2026/27) |
| Student Loan Plan 5 (fixed £25,000 threshold) | ✅ Supported |
| Postgraduate Loan (fixed £21,000 threshold; 6%) | ✅ Supported |
| Multiple loan plans simultaneously | ✅ Supported |
| CGT — shares, crypto, other assets (18%/24% post-Oct 2024) | ✅ Supported |
| CGT — Annual Exempt Amount (£3,000) | ✅ Supported |
| CGT — brought-forward losses | ✅ Supported |
| CGT — basic/higher rate split | ✅ Supported |
| Tax year 2025/26 | ✅ Supported |
| Tax year 2026/27 | ✅ Supported |

---

## 9. Known unsupported capabilities

| Capability | Reason |
|---|---|
| Scottish income tax | Different band rates; out of scope |
| Class 1 NI (employment) | Assumed handled via PAYE |
| Employer pension / salary sacrifice | Out of scope |
| Dividend income | Different ordering rules; out of scope |
| Savings income | Different ordering rules; out of scope |
| CGT — BADR / Investors' Relief | Out of scope; warning issued |
| CGT — share pooling and 30-day matching | Out of scope; warning issued |
| CGT — residential property (distinct rate) | Rates now unified; disclaimer shown |
| Non-UK resident cases | Out of scope |
| Non-domicile rules | Out of scope |
| Zero-amount invoices | Engine correctly rejects (UNSUPPORTED_EXPECTED) |

---

## 10. Gate status

| Gate | Question | Status |
|---|---|---|
| Gate 1 | Core calculations verified? | ✅ PASSED (Stage 1, 30 scenarios) |
| Gate 2 | Representative scenarios reliable? | ✅ PASSED (Stage 2, 150 scenarios) |
| Gate 3 | Interaction scenarios complete? | ⏳ Pending Stage 3 |
| Final Gate | Tolerance testing complete, no unresolved Critical issues? | ⏳ Pending Stage 4 |

---

## 11. Outstanding assurance work (Stage 3+)

**Stage 3 — Interaction scenarios (IDs: RW-S3-001 onwards)**

Complex combined scenarios not yet tested:
- Salary + YTD + pension + all student loan plans simultaneously
- Multi-invoice threshold crossings (salary pushes prior YTD near a boundary)
- Large pension contribution pushing eBRL exactly to or beyond ART
- Student loan + pension combination at higher rate
- CGT combined with high income tax (ANI near PA taper)
- Year-boundary edge cases with both 2025/26 and 2026/27 thresholds active

**Stage 4 — Tolerance and stress scenarios**
- Extremely large inputs (pension > BRL, invoices > £1M)
- Sub-penny precision and statutory rounding invariants
- Input validation edge cases
- Performance under sequential execution

---

## 12. Baseline integrity

This document, combined with the evidence registers (docs 03 and 09), provides a
complete and independently reproducible record of the engine's assurance state prior
to Stage 3. Any result from Stage 3 onwards that diverges from this baseline,
or that reveals a pre-existing gap in Stage 1 or Stage 2 coverage, must be escalated
as a finding before Stage 3 Gate can be assessed.
