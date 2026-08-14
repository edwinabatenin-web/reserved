# Stage 3 Component-Level Summary
**Assurance cycle:** Reserved West Initiative 001
**Engine version:** 2.0.1
**Date:** 2026-08-07

## Summary by group

| Group | Scenarios | Passing | Failing | Pass rate |
|---|---|---|---|---|
| All-component (INT) | 20 | 20 | 0 | 100% |
| Pension deep (PIG) | 15 | 15 | 0 | 100% |
| Student-loan cross (SLX) | 10 | 10 | 0 | 100% |
| CGT + IT interaction (CGX) | 10 | 10 | 0 | 100% |
| Year comparison (YTC) | 5 | 5 | 0 | 100% |
| EL-001 zone scenarios | 19 | 19 | 0 | 100% |

## EL-001 zone interaction scenarios

Stage 3 includes interaction scenarios that exercise the EL-001 regression zone
(ANI crossing £100,000–£125,140) alongside pension, SL, and NI interactions.

EL-001 zone scenarios in Stage 3: 19

| ID | Title | Outcome |
|---|---|---|
| RW-S3-004 | Salary + pension + SL Plan 2 — invoice crosses PA taper | PASS |
| RW-S3-005 | Pension keeps ANI at taper start; invoice crosses deep  | PASS |
| RW-S3-006 | Salary + pension + SL Plan 1 — invoice enters PA taper  | PASS |
| RW-S3-008 | Near-taper earnings + SL Plan 5 + pension — invoice cro | PASS |
| RW-S3-013 | High earner + SL Plan 2 + pension — invoice spans taper | PASS |
| RW-S3-015 | All five SL plans + no pension — sole trader traverses  | PASS |
| RW-S3-022 | Pension keeps ANI below taper at start; invoice crosses | PASS |
| RW-S3-023 | Pension reduces ANI through taper midpoint — PA halved  | PASS |
| RW-S3-030 | Pension + PA taper + ART crossing — three-zone income t | PASS |
| RW-S3-034 | Pension + EL-001 zone + SL Plan 5 — three-way interacti | PASS |
| RW-S3-061 | Sequential: second invoice with profile already fully w | PASS |
| RW-S3-064 | Sequential: second invoice fully within EL-001 zone wit | PASS |
| RW-S3-066 | Stress: very large invoice from zero — traverses all IT | PASS |
| RW-S3-070 | Stress: EL-003 cap + EL-001 zone simultaneously — large | PASS |
| RW-S3-071 | Stress: practical user ceiling — all components at uppe | PASS |
| RW-S3-076 | Combined: EL-001 zone + EL-003 cap + SL — three constra | PASS |
| RW-S3-078 | Combined: NI sole-trader UPL + EL-001 zone — independen | PASS |
| RW-S3-079 | Combined: SL Plan 4 + EL-001 zone — Scotland-origin loa | PASS |
| RW-S3-080 | Combined: EL-001 zone + pension + SL in 2025/26 — froze | PASS |

## Outcome distribution

| Outcome | Count | Percentage |
|---|---|---|
| PASS | 80 | 100% |