# Final Gate Decision — Reserved West Initiative 001
**Assurance cycle:** Reserved West Initiative 001
**Date:** 2026-08-07
**Engine version:** 2.0.1

## Decision
**✅ FINAL GATE PASSED**

## Final Gate criteria

| Criterion | Required | Result | Met |
|---|---|---|---|
| No REGRESSION_EL001 | Zero | 0 | ✅ |
| EL-001 zone scenarios all PASS | All | 5 PASS, 0 FAIL | ✅ |
| No unexplained FAIL | Zero | 0 | ✅ |
| No ERRORs | Zero | 0 | ✅ |
| EL-003 cap boundary confirmed | ≥1 PASS | 3/3 | ✅ |
| ROUND_HALF_UP invariants confirmed | All PASS | 3/3 | ✅ |
| Zero-invoice rejection confirmed | ≥1 UNSUPPORTED_EXPECTED | 1 | ✅ |

## Evidence summary

  Stage 4 scenarios:             32
  PASS (exact):                  31
  PASS_PENNY (≤1p):              0
  UNSUPPORTED_EXPECTED:          1
  FAIL:                          0
  REGRESSION_EL001:              0
  ERROR:                         0
  EL-001 zone (PASS):            5
  EL-003 boundary (PASS):        3
  Rounding invariants (PASS):    3

## Rationale

All 32 Stage 4 scenarios pass. Combined with Stages 1, 2, and 3, the engine has been verified across 292 independent reference-grounded scenarios.

**Extreme inputs:** The engine scales correctly to £1,000,000 invoices, £500,000 YTD positions, £500,000 salaries, and pension contributions far exceeding total income. No arithmetic failures, overflows, or silent truncations were observed.

**Boundary conditions:** The engine correctly detects all key thresholds: BRL/UPL (£50,270), ART (£125,140), PA taper entry (£100,000), PA/LPL joint zero (£12,570), and the EL-003 eBRL cap (eBRL = ART exactly). No off-by-one errors were found.

**Mathematical invariants:** Eight structural invariants confirmed: IT non-negativity, SL independence from pension, NI independence from pension, zero-tax floor, ROUND_HALF_UP at 20%/2%/9%, and IT+NI+SL component additivity.

**Validation:** Zero-invoice correctly rejected. Sub-threshold inputs produce zero tax. CGT correctly handles zero taxable gains, all-basic-rate gains, and BF-loss absorption.

**Regression families:** EL-001 (18 tests + 20+ Stage 3 scenarios + 3 Stage 4 scenarios) and EL-003 (37 regression tests + 2 Stage 4 scenarios) remain fully green. No new defect families discovered in Stage 4.

## Stage gates — final overview

| Gate | Question | Status |
|---|---|---|
| Gate 1 | Core calculations verified? | ✅ PASSED (Stage 1, 30 scenarios) |
| Gate 2 | Representative scenarios reliable? | ✅ PASSED (Stage 2, 150 scenarios) |
| Gate 3 | Interaction scenarios complete? | ✅ PASSED (Stage 3, 80 scenarios) |
| **Final Gate** | **Tolerance, boundary, invariant, and validation complete?** | **✅ PASSED (Stage 4, 32 scenarios)** |

## Combined assurance record

| Stage | Scenarios | Gate |
|---|---|---|
| Stage 1 — Core calculations | 30 | ✅ PASSED |
| Stage 2 — Representative & boundary | 150 | ✅ PASSED |
| Stage 3 — Interaction | 80 | ✅ PASSED |
| Stage 4 — Tolerance / Boundary / Invariant / Validation | 32 | ✅ PASSED |
| **Total** | **292** | **✅ All passing** |

## Certification

The Reserved engine (v2.0.1) is hereby certified by Reserved West Initiative 001 for use in the October 2026 private beta.

Certification scope:
- England/Wales/NI income tax (2025/26 and 2026/27)
- Class 4 National Insurance (freelance profit only)
- Pension Relief at Source
- Student Loan Plans 1, 2, 4, 5, and Postgraduate Loan
- Capital Gains Tax (post-Oct 2024 rates; shares, crypto, other assets)
- Annual Exempt Amount and brought-forward losses

Exclusions from scope remain as documented in the Capability Register (01_capability_register.md).