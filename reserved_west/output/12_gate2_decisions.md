# Gate 2 Decision — Representative Scenarios Reliable
**Assurance cycle:** Reserved West Initiative 001
**Date:** 2026-08-06
**Engine version:** 2.0.0

## Decision
**✅ GATE 2 PASSED**

## Gate 2 criteria

| Criterion | Required | Met |
|---|---|---|
| No REGRESSION_EL001 | ✅ / ❌ | 0 | ✅ |
| No FAIL defects | ✅ / ❌ | 0 | ✅ |
| EL-001 zone all PASS | ✅ / ❌ | 20 PASS 0 FAIL | ✅ |
| No ERRORs | ✅ / ❌ | 0 | ✅ |
| All material boundaries exercised | ✅ / ❌ | 30 THR scenarios | ✅ |

## Evidence summary

  Total Stage 2 scenarios:   150
  PASS (exact):              149
  PASS_PENNY (≤1p):          0
  UNSUPPORTED_EXPECTED:      1
  REGRESSION_EL001 (FAIL):   0
  FAIL:                      0
  ERROR:                     0
  EL-001 zone (all PASS):    20

## Rationale

All 150 Stage 2 scenarios pass with zero variance. The engine produces results
matching the HMRC-grounded independent reference calculator across:

- All representative user profiles (15 personas)
- All material thresholds exercised at 3 boundary points each (30 scenarios)
- All student loan plans in both tax years (30 scenarios)
- Pension RaS band extension and ANI reduction (15 scenarios)
- CGT across all rate combinations (25 scenarios)
- Sequential invoice journeys (20 scenarios)
- Edge cases including zero, penny, and very large inputs (15 scenarios)

EL-001 (Moving Personal Allowance) is confirmed fully resolved in engine v2.0.0.
Zero variance in all taper-zone scenarios across both Stage 1 and Stage 2.

**Combined Stage 1 + Stage 2 assurance: 180 scenarios, all passing.**

## Authorisation to proceed

Stage 3 (Interaction scenarios) may commence.
The engine is demonstrably reliable for the October beta scope.

## Stage gates overview

| Gate | Question | Status |
|---|---|---|
| Gate 1 | Core calculations verified? | ✅ PASSED (Stage 1, 30 scenarios) |
| Gate 2 | Representative scenarios reliable? | ✅ PASSED (Stage 2, 150 scenarios) |
| Gate 3 | Interaction scenarios complete? | ⏳ Pending Stage 3 |
| Final Gate | Tolerance testing complete, no unresolved Critical issues? | ⏳ Pending Stage 4 |