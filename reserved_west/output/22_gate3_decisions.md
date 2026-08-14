# Gate 3 Decision — Interaction Scenarios Complete
**Assurance cycle:** Reserved West Initiative 001
**Date:** 2026-08-07
**Engine version:** 2.0.1

## Decision
**✅ GATE 3 PASSED**

## Gate 3 criteria

| Criterion | Required | Result | Met |
|---|---|---|---|
| No REGRESSION_EL001 | Zero | 0 | ✅ |
| EL-001 zone interaction scenarios all PASS | All | 19 PASS 0 FAIL | ✅ |
| No unexplained FAIL | Zero | 0 | ✅ |
| No ERRORs | Zero | 0 | ✅ |
| All interaction groups exercised | 5 groups | INT PIG SLX CGX YTC | ✅ |

## Evidence summary

  Total Stage 3 scenarios:   80
  PASS (exact):              80
  PASS_PENNY (≤1p):          0
  UNSUPPORTED_EXPECTED:      0
  REGRESSION_EL001 (FAIL):   0
  FAIL:                      0
  ERROR:                     0
  EL-001 zone (PASS):        19

## Rationale

All 80 Stage 3 interaction scenarios pass with zero variance.
The engine produces correct results when multiple components are active simultaneously:

- All-component scenarios (INT): IT + NI + pension + all five SL plans interact correctly.
- Pension deep scenarios (PIG): eBRL extension, ANI reduction, and taper interaction all produce correct results. Pension correctly affects IT but not student-loan repayment.
- Student-loan cross scenarios (SLX): Plans 1/2/4/5/PGL activate at correct thresholds; year-over-year differences confirmed for 2025/26 vs 2026/27.
- CGT interaction scenarios (CGX): Basic/higher rate band split correctly uses taxable income before gains; pension-reduced income correctly frees BRL for CGT.
- Year comparison scenarios (YTC): Correct 2025/26 thresholds applied for Plans 1, 2, 4; Plans 5 and PGL confirmed identical across both years.

EL-001 zone interaction scenarios: 19 PASS across contexts including pension + taper, salary + taper + SL, and multi-band traversal.

**Combined assurance: 260 scenarios across Stages 1–3, all passing.**

## Authorisation to proceed

Stage 4 (Tolerance and stress testing) may commence.
The engine is demonstrably reliable for complex interaction scenarios.

## Stage gates overview

| Gate | Question | Status |
|---|---|---|
| Gate 1 | Core calculations verified? | ✅ PASSED (Stage 1, 30 scenarios) |
| Gate 2 | Representative scenarios reliable? | ✅ PASSED (Stage 2, 150 scenarios) |
| Gate 3 | Interaction scenarios complete? | ✅ PASSED (Stage 3, 80 scenarios) |
| Final Gate | Tolerance testing complete, no unresolved Critical issues? | ✅ PASSED (Stage 4, 32 scenarios) |