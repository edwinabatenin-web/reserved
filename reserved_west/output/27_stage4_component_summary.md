# Stage 4 Component-Level Summary
**Assurance cycle:** Reserved West Initiative 001
**Engine version:** 2.0.1
**Date:** 2026-08-07

## Summary by group

| Group | Scenarios | Passing | Failing | Pass rate |
|---|---|---|---|---|
| Extreme inputs (EXT) | 8 | 8 | 0 | 100% |
| Boundary conditions (BND) | 10 | 10 | 0 | 100% |
| Mathematical invariants (INV) | 8 | 8 | 0 | 100% |
| Validation (VAL) | 6 | 6 | 0 | 100% |
| EL-001 zone scenarios | 5 | 5 | 0 | 100% |
| EL-003 boundary scenarios | 3 | 3 | 0 | 100% |
| Rounding invariant scenarios | 3 | 3 | 0 | 100% |

## Mathematical invariant verification

| Invariant | Scenario | Outcome |
|---|---|---|
| Non-negativity (pension > income; IT ≥ £0) | RW-S4-019 | PASS |
| SL independence from pension | RW-S4-020 | PASS |
| NI independence from pension | RW-S4-021 | PASS |
| Zero-tax floor (income below all thresholds) | RW-S4-022 | PASS |
| ROUND_HALF_UP: IT at 20% (£0.005 → £0.01) | RW-S4-023 | PASS |
| ROUND_HALF_UP: NI at 2% (£0.005 → £0.01) | RW-S4-024 | PASS |
| ROUND_HALF_UP: SL at 9% (£0.045 → £0.05) | RW-S4-025 | PASS |
| Component additivity (IT + NI + SL = Total) | RW-S4-026 | PASS |

## Outcome distribution

| Outcome | Count | Percentage |
|---|---|---|
| PASS | 31 | 96% |
| UNSUPPORTED_EXPECTED | 1 | 3% |