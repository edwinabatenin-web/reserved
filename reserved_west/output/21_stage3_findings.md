# Stage 3 Findings
**Assurance cycle:** Reserved West Initiative 001
**Engine version:** 2.0.1
**Date:** 2026-08-07

## Headline

- **Total scenarios:** 80
- **PASS:** 80
- **PASS_PENNY:** 0
- **FAIL:** 0
- **REGRESSION_EL001:** 0
- **ERROR:** 0
- **EL-001 zone passing:** 19

## Finding S3-F0: All scenarios pass

No defects, regressions, or errors were found in Stage 3.

The engine produces correct results across all 80 interaction scenarios:

- All five SL plans activate correctly when combined with pension, NI, and IT.
- Pension eBRL extension interacts correctly with all IT band boundaries.
- Pension ANI reduction is independent of student-loan repayment (as required).
- All EL-001 zone interaction scenarios return zero variance.
- CGT basic/higher rate split correctly uses IT taxable income as the band reference.
- Year-over-year SL threshold changes produce the correct difference in repayment.
- NI main and upper rate transitions interact correctly with SL and pension simultaneously.

**Combined Stage 1 + Stage 2 + Stage 3: 240 scenarios, all passing.**

## EL-001 interaction family: confirmed resolved

All 19 EL-001 zone interaction scenarios in Stage 3 return PASS.

Combined EL-001 zone coverage across all stages:
  Stage 1: 3 scenarios — PASS
  Stage 2: 17 scenarios — PASS
  Stage 3: 19 scenarios (with pension/SL/NI interaction) — PASS

The engine correctly handles the Moving Personal Allowance in all tested
interaction contexts: with pension contributions, student-loan plans,
NI upper rate, and salary at various levels.