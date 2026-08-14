# Stage 3 Scenario Catalogue
**Assurance cycle:** Reserved West Initiative 001
**Date:** 2026-08-07
**Total scenarios:** 80

## Group overview

| Group | Description | Scenario range | Count |
|---|---|---|---|
| INT | All-component interaction | RW-S3-001–RW-S3-020 | 20 |
| PIG | Pension deep interaction | RW-S3-021–RW-S3-035 | 15 |
| SLX | Student-loan cross-plan effects | RW-S3-036–RW-S3-045 | 10 |
| CGX | CGT + income-tax interaction | RW-S3-046–RW-S3-055 | 10 |
| YTC | Year-to-year comparison | RW-S3-056–RW-S3-060 | 5 |
| SEQ | Sequential invoice behaviour | RW-S3-061–RW-S3-065 | 5 |
| TOL | Tolerance and stress | RW-S3-066–RW-S3-072 | 7 |
| CAG | CGT additional interaction | RW-S3-073–RW-S3-075 | 3 |
| CMP | Combined remaining gaps | RW-S3-076–RW-S3-080 | 5 |

## Interaction matrix

Each Stage 3 scenario is designed to fire multiple engine components simultaneously.
The matrix below shows which components are active in each group:

| Group | IT bands | NI bands | Pension RaS | Student Loan | EL-001 zone |
|---|---|---|---|---|---|
| INT | ✅ Multiple | ✅ Multiple | Most | All five (many) | Several |
| PIG | ✅ Higher/ART | ✅ Upper | All | Some | Several |
| SLX | ✅ Basic/Higher | ✅ Main/Upper | Some | All five | Some |
| CGX | Via taxable income | n/a | Some | n/a | Some |
| YTC | ✅ Both years | ✅ Both years | None | All plans | None |
| SEQ | ✅ Multiple | ✅ Multiple | Some | Some | Several |
| TOL | ✅ All bands | ✅ All bands | Some | Most | Several |
| CAG | Via taxable income | n/a | Some | n/a | None |
| CMP | ✅ Higher/ART | ✅ Upper | Some | All five | Several |

## EL-001 coverage in Stage 3

The following Stage 3 scenarios exercise the EL-001 regression zone (ANI crossing £100,000–£125,140):

| ID | Description |
|---|---|
| RW-S3-004 | Pension + salary + Plan 2: invoice crosses taper |
| RW-S3-005 | Pension keeps ANI at taper start; invoice crosses deep into taper |
| RW-S3-006 | Salary + pension + Plan 1: invoice enters taper |
| RW-S3-008 | Near-taper YTD + Plan 5 + pension: invoice crosses taper start |
| RW-S3-013 | High earner + Plan 2 + pension: invoice spans taper to PA elimination |
| RW-S3-015 | All five plans + no pension: all bands traversed, EL-001 zone included |
| RW-S3-022 | Pension keeps ANI below taper; invoice crosses taper (EL-001) |
| RW-S3-023 | Pension reduces ANI through taper midpoint (EL-001) |
| RW-S3-030 | Pension + PA taper + ART crossing in one invoice |
| RW-S3-034 | Pension + EL-001 + Plan 5 three-way |
| RW-S3-050 | CGT: taxable income in taper zone reduces BRL remaining |
| RW-S3-061 | Sequential: second invoice already fully within taper zone |
| RW-S3-064 | Sequential: second invoice in EL-001 zone with pension active |
| RW-S3-070 | Stress: EL-003 cap + EL-001 zone simultaneously (large pension) |
| RW-S3-071 | Stress: all components near practical ceiling; EL-001 zone entered |
| RW-S3-076 | Combined: EL-001 + EL-003 cap + SL — three constraints active |
| RW-S3-078 | Combined: NI UPL + EL-001 zone — NI and taper independence |
| RW-S3-079 | Combined: SL Plan 4 + EL-001 zone |
| RW-S3-080 | Combined: EL-001 zone + pension + SL in 2025/26 |

## ID assignment

Stage 3 IDs: RW-S3-001 through RW-S3-080. Permanent — do not re-use or renumber.
Stage 4 IDs will begin at RW-S4-001.

## Full scenario list

| ID | Group | Title | Tax Year | Type |
|---|---|---|---|---|
| RW-S3-001 | INT | All five SL plans + pension + salary + invoice crosses BRL and | 2026/27 | income_tax |
| RW-S3-002 | INT | All five SL plans + pension — same profile in 2025/26 | 2025/26 | income_tax |
| RW-S3-003 | INT | All five SL plans + large pension + NI crossing UPL | 2026/27 | income_tax |
| RW-S3-004 | INT | Salary + pension + SL Plan 2 — invoice crosses PA taper (EL-00 | 2026/27 | income_tax |
| RW-S3-005 | INT | Pension keeps ANI at taper start; invoice crosses deep into ta | 2026/27 | income_tax |
| RW-S3-006 | INT | Salary + pension + SL Plan 1 — invoice enters PA taper from be | 2026/27 | income_tax |
| RW-S3-007 | INT | Sole trader — all NI bands + Plan 2 + PGL + pension; large inv | 2026/27 | income_tax |
| RW-S3-008 | INT | Near-taper earnings + SL Plan 5 + pension — invoice crosses ta | 2026/27 | income_tax |
| RW-S3-009 | INT | Plan 2 + PGL + pension — invoice crosses eBRL into higher rate | 2026/27 | income_tax |
| RW-S3-010 | INT | All five SL plans + pension — sole trader invoice crosses all  | 2026/27 | income_tax |
| RW-S3-011 | INT | Very large pension caps eBRL at ART; invoice partly at 45% | 2026/27 | income_tax |
| RW-S3-012 | INT | Salary at BRL + pension extends eBRL + SL Plan 4 + NI crosses  | 2026/27 | income_tax |
| RW-S3-013 | INT | High earner + SL Plan 2 + pension — invoice spans taper into P | 2026/27 | income_tax |
| RW-S3-014 | INT | Plan 1 crosses threshold + pension + NI crossing LPL + IT at b | 2026/27 | income_tax |
| RW-S3-015 | INT | All five SL plans + no pension — sole trader traverses all ban | 2026/27 | income_tax |
| RW-S3-016 | INT | Plan 2 + Plan 4 simultaneously + pension — invoice crosses eBR | 2026/27 | income_tax |
| RW-S3-017 | INT | All five SL plans + no pension — salary in higher rate + invoi | 2026/27 | income_tax |
| RW-S3-018 | INT | Plan 1 + Plan 2 cross different thresholds in 2025/26 — two SL | 2025/26 | income_tax |
| RW-S3-019 | INT | Plan 1 + Plan 2 — same income pattern in 2026/27 (higher thres | 2026/27 | income_tax |
| RW-S3-020 | INT | Extended Gabriel — all five SL plans added to canonical pensio | 2026/27 | income_tax |
| RW-S3-021 | PIG | Pension keeps ANI just below taper; invoice pushes ANI exactly | 2026/27 | income_tax |
| RW-S3-022 | PIG | Pension keeps ANI below taper at start; invoice crosses taper  | 2026/27 | income_tax |
| RW-S3-023 | PIG | Pension reduces ANI through taper midpoint — PA halved (EL-001 | 2026/27 | income_tax |
| RW-S3-024 | PIG | Very large pension: eBRL capped exactly at ART; all invoice ab | 2026/27 | income_tax |
| RW-S3-025 | PIG | Large pension + salary in higher rate — pension pulls entire i | 2026/27 | income_tax |
| RW-S3-026 | PIG | Pension extends BRL; invoice straddles eBRL — split between 20 | 2026/27 | income_tax |
| RW-S3-027 | PIG | Pension reduces ANI for IT but SL is on gross income — decoupl | 2026/27 | income_tax |
| RW-S3-028 | PIG | Pension with PGL — income near PGL threshold; pension does not | 2026/27 | income_tax |
| RW-S3-029 | PIG | Pension extends eBRL just past BRL — invoice exactly straddles | 2026/27 | income_tax |
| RW-S3-030 | PIG | Pension + PA taper + ART crossing — three-zone income tax inte | 2026/27 | income_tax |
| RW-S3-031 | PIG | Pension exactly prevents PA taper — ANI stays at £100,000 thro | 2026/27 | income_tax |
| RW-S3-032 | PIG | Comparison baseline — no pension, salary in higher rate (for R | 2026/27 | income_tax |
| RW-S3-033 | PIG | Large pension saves entire invoice from higher rate — paired w | 2026/27 | income_tax |
| RW-S3-034 | PIG | Pension + EL-001 zone + SL Plan 5 — three-way interaction | 2026/27 | income_tax |
| RW-S3-035 | PIG | Massive pension contribution — ANI near zero; eBRL capped; no  | 2026/27 | income_tax |
| RW-S3-036 | SLX | Plans 1 + 2 + 4 simultaneously — invoice crosses all three thr | 2026/27 | income_tax |
| RW-S3-037 | SLX | Plan 5 + PGL simultaneously — both thresholds crossed by invoi | 2026/27 | income_tax |
| RW-S3-038 | SLX | Plan 1 + pension — pension reduces IT but SL repayment based o | 2026/27 | income_tax |
| RW-S3-039 | SLX | Plan 2 threshold crossing — 2025/26 threshold (£28,470) vs 202 | 2025/26 | income_tax |
| RW-S3-040 | SLX | Plan 2 threshold crossing — same income in 2026/27 (higher thr | 2026/27 | income_tax |
| RW-S3-041 | SLX | All five plans — income starts below all thresholds, invoice c | 2026/27 | income_tax |
| RW-S3-042 | SLX | Plan 4 — threshold crossing with NI UPL interaction in 2026/27 | 2026/27 | income_tax |
| RW-S3-043 | SLX | Plan 5 + Plan 2 — Plan 5 fixed threshold both years; Plan 2 ch | 2025/26 | income_tax |
| RW-S3-044 | SLX | PGL (Postgraduate) alone crossing threshold + IT band interact | 2026/27 | income_tax |
| RW-S3-045 | SLX | Plan 4 + Plan 5 + pension — both SL plans above threshold; pen | 2026/27 | income_tax |
| RW-S3-046 | CGX | CGT: high income exhausts BRL — entire gain at higher rate (24 | 2026/27 | cgt |
| RW-S3-047 | CGX | CGT: income below PA — all gain at basic rate (18%); BRL fully | 2026/27 | cgt |
| RW-S3-048 | CGX | CGT: pension reduces taxable income; frees BRL for CGT basic r | 2026/27 | cgt |
| RW-S3-049 | CGX | CGT: income partially fills BRL — gain split basic/higher rate | 2026/27 | cgt |
| RW-S3-050 | CGX | CGT: taxable income in PA taper zone — reduced PA affects taxa | 2026/27 | cgt |
| RW-S3-051 | CGX | CGT: two disposals + income in higher rate — both disposals fu | 2026/27 | cgt |
| RW-S3-052 | CGX | CGT: brought-forward losses reduce taxable gain to zero; high  | 2026/27 | cgt |
| RW-S3-053 | CGX | CGT: same income and gain in 2025/26 — rates and AEA identical | 2025/26 | cgt |
| RW-S3-054 | CGX | CGT: three disposals with mixed gains and losses + income spli | 2026/27 | cgt |
| RW-S3-055 | CGX | CGT: very large gain in 2025/26 — all at higher rate; partiall | 2025/26 | cgt |
| RW-S3-056 | YTC | Plan 1 — income starts below 2025/26 threshold (£24,990); cros | 2025/26 | income_tax |
| RW-S3-057 | YTC | Plan 1 — same income in 2026/27 (higher threshold = lower SL r | 2026/27 | income_tax |
| RW-S3-058 | YTC | Plan 4 — income straddles the 2025/26 threshold (£32,745) | 2025/26 | income_tax |
| RW-S3-059 | YTC | Plan 4 — same income in 2026/27 (threshold £33,795 vs £32,745  | 2026/27 | income_tax |
| RW-S3-060 | YTC | All plans — profile where Plans 1 and 2 cross thresholds in 20 | 2025/26 | income_tax |
| RW-S3-061 | SEQ | Sequential: second invoice with profile already fully within E | 2026/27 | income_tax |
| RW-S3-062 | SEQ | Sequential: second invoice straddling eBRL — profile starts ex | 2026/27 | income_tax |
| RW-S3-063 | SEQ | Sequential: second invoice crosses SL Plan 1 threshold mid-inv | 2026/27 | income_tax |
| RW-S3-064 | SEQ | Sequential: second invoice fully within EL-001 zone with pensi | 2026/27 | income_tax |
| RW-S3-065 | SEQ | Sequential: third-position invoice — all components in their u | 2026/27 | income_tax |
| RW-S3-066 | TOL | Stress: very large invoice from zero — traverses all IT and NI | 2026/27 | income_tax |
| RW-S3-067 | TOL | Stress: pension at annual allowance limit (£60k) — entire invo | 2026/27 | income_tax |
| RW-S3-068 | TOL | Stress: sub-penny invoice at additional rate — rounding to cor | 2026/27 | income_tax |
| RW-S3-069 | TOL | Stress: sub-pound invoice with multiple SL plans — ROUND_HALF_ | 2026/27 | income_tax |
| RW-S3-070 | TOL | Stress: EL-003 cap + EL-001 zone simultaneously — large pensio | 2026/27 | income_tax |
| RW-S3-071 | TOL | Stress: practical user ceiling — all components at upper end o | 2026/27 | income_tax |
| RW-S3-072 | TOL | Stress: pension just below EL-003 cap — eBRL near ART; large i | 2026/27 | income_tax |
| RW-S3-073 | CAG | CGT: pension raises BRL remaining — gain split shifts toward b | 2026/27 | cgt |
| RW-S3-074 | CAG | CGT: brought-forward losses + AEA exactly cancel the gain — ze | 2026/27 | cgt |
| RW-S3-075 | CAG | CGT: very large BF loss partially offsets large gain — higher  | 2025/26 | cgt |
| RW-S3-076 | CMP | Combined: EL-001 zone + EL-003 cap + SL — three constraints si | 2026/27 | income_tax |
| RW-S3-077 | CMP | Combined: all five SL plans + pension at annual allowance + in | 2026/27 | income_tax |
| RW-S3-078 | CMP | Combined: NI sole-trader UPL + EL-001 zone — independence of N | 2026/27 | income_tax |
| RW-S3-079 | CMP | Combined: SL Plan 4 + EL-001 zone — Scotland-origin loan on gr | 2026/27 | income_tax |
| RW-S3-080 | CMP | Combined: EL-001 zone + pension + SL in 2025/26 — frozen IT/NI | 2025/26 | income_tax |