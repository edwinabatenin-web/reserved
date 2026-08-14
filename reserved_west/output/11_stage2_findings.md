# Stage 2 Findings & Root-Cause Groupings
**Assurance cycle:** Reserved West Initiative 001
**Engine version:** 2.0.0
**Date:** 2026-08-06

## Headline

- **Total scenarios:** 150
- **PASS:** 149
- **PASS_PENNY:** 0
- **FAIL:** 0
- **REGRESSION_EL001:** 0
- **ERROR:** 0
- **EL-001 zone scenarios passing:** 20

## Finding S2-F0: All scenarios pass

No defects, regressions, or errors were found in Stage 2.

The engine produces results matching the independent HMRC reference calculator
on all 150 representative and boundary scenarios:

- All IT band boundaries (PA, BRL, ART) confirmed correct.
- All PA taper zone scenarios confirm EL-001 is fully resolved (zero variance).
- All NI boundaries (LPL, UPL) confirmed correct.
- All student loan plans (1, 2, 4, 5, PGL) confirmed correct in both tax years.
- Pension RaS band extension and ANI reduction confirmed correct.
- CGT (AEA, basic/higher split, brought-forward losses) confirmed correct.
- Sequential journey scenarios confirm cumulative YTD handling is correct.
- Edge cases confirm stability at zero, penny, and very large inputs.

## EL-001 regression family: confirmed resolved

All 20 EL-001 zone scenarios in Stage 2 return PASS.

Stage 2 EL-001 zone scenarios cover:
- Representative profiles entering the taper (RW-S2-006, RW-S2-007, RW-S2-008)
- ART boundary scenarios (RW-S2-022–024)
- PA taper boundary scenarios (RW-S2-025–033)
- Sequential journeys crossing the taper (RW-S2-122, RW-S2-123)
- Combined salary+taper scenarios (RW-S2-042, RW-S2-044)
- Pension with taper (RW-S2-080)

Combined with the 16 permanent EL-001 regression tests and the 3 EL-001 zone
Stage 1 scenarios, this gives comprehensive assurance that EL-001 is fully resolved.

## Root-cause summary

No systemic root causes identified. The engine's before-and-after differential approach is producing correct results
across all tested income levels, tax years, and component combinations.