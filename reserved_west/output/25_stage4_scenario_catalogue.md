# Stage 4 Scenario Catalogue
**Assurance cycle:** Reserved West Initiative 001
**Date:** 2026-08-07
**Total scenarios:** 32

## Group overview

| Group | Description | Scenario range | Count |
|---|---|---|---|
| EXT | Extreme valid inputs | RW-S4-001–RW-S4-008 | 8 |
| BND | Exact boundary conditions | RW-S4-009–RW-S4-018 | 10 |
| INV | Mathematical invariants | RW-S4-019–RW-S4-026 | 8 |
| VAL | Validation and edge cases | RW-S4-027–RW-S4-032 | 6 |

## Coverage matrix

| Group | IT bands | NI bands | Pension | SL | EL-001/003 family |
|---|---|---|---|---|---|
| EXT | ✅ All | ✅ All | Some | Some | EL-001 in S4-005 |
| BND | ✅ All (boundary) | ✅ All (boundary) | S4-015 (EL-003 cap) | S4-016–017 | EL-001 in S4-012, S4-014 |
| INV | ✅ Multiple | ✅ Multiple | Several | Several | None |
| VAL | Minimal | Minimal | S4-029 (extreme) | S4-022 | None |

## Invariant checklist

| Invariant | Tested by |
|---|---|
| IT ≥ £0 (non-negativity) | RW-S4-019 |
| SL is on gross income, not ANI | RW-S4-020 |
| NI is on gross profit, not ANI | RW-S4-021 |
| Total = £0 when income below all thresholds | RW-S4-022 |
| ROUND_HALF_UP at 20% (IT) | RW-S4-023 |
| ROUND_HALF_UP at 2% (NI upper) | RW-S4-024 |
| ROUND_HALF_UP at 9% (SL) | RW-S4-025 |
| IT + NI + SL = Total | RW-S4-026 |

## ID assignment

Stage 4 IDs: RW-S4-001 through RW-S4-032. Permanent — do not re-use or renumber.
Stage 5 IDs (if needed) begin at RW-S5-001.

## Full scenario list

| ID | Group | Title | Tax Year | Type |
|---|---|---|---|---|
| RW-S4-001 | EXT | Extreme: £1,000,000 invoice from zero — all IT and NI bands at | 2026/27 | income_tax |
| RW-S4-002 | EXT | Extreme: £500k YTD, £50k invoice — entirely at ceiling rates w | 2026/27 | income_tax |
| RW-S4-003 | EXT | Extreme: pension far exceeds total income — ANI floored to zer | 2026/27 | income_tax |
| RW-S4-004 | EXT | Extreme: £500k day-job salary + invoice — freelance NI at basi | 2026/27 | income_tax |
| RW-S4-005 | EXT | Extreme: all five SL plans + pension at annual allowance + £50 | 2026/27 | income_tax |
| RW-S4-006 | EXT | Extreme: all five SL plans + £200k invoice from zero — maximum | 2026/27 | income_tax |
| RW-S4-007 | EXT | Extreme: £1 invoice at the top of the 40% band — last penny be | 2026/27 | income_tax |
| RW-S4-008 | EXT | Extreme: £1 invoice at the ART boundary — first pound of 45% a | 2026/27 | income_tax |
| RW-S4-009 | BND | Boundary: invoice ends exactly at BRL/UPL (£50,270) — no highe | 2026/27 | income_tax |
| RW-S4-010 | BND | Boundary: invoice starts exactly at BRL/UPL — entire invoice a | 2026/27 | income_tax |
| RW-S4-011 | BND | Boundary: invoice straddles BRL and UPL simultaneously (both a | 2026/27 | income_tax |
| RW-S4-012 | BND | Boundary: invoice ends exactly at ART (£125,140) from zero — P | 2026/27 | income_tax |
| RW-S4-013 | BND | Boundary: invoice starts exactly at ART — entire invoice at 45 | 2026/27 | income_tax |
| RW-S4-014 | BND | Boundary: invoice from zero ends exactly at taper entry (ANI = | 2026/27 | income_tax |
| RW-S4-015 | BND | Boundary: pension sets eBRL exactly at ART — EL-003 cap at exa | 2026/27 | income_tax |
| RW-S4-016 | BND | Boundary: SL Plan 2 — invoice starts exactly at threshold (£29 | 2026/27 | income_tax |
| RW-S4-017 | BND | Boundary: SL Plan 5 — invoice straddles fixed threshold (£25,0 | 2026/27 | income_tax |
| RW-S4-018 | BND | Boundary: income ends exactly at PA = LPL = £12,570 — IT = 0,  | 2026/27 | income_tax |
| RW-S4-019 | INV | Invariant: non-negativity — pension > income, ANI = 0; IT must | 2026/27 | income_tax |
| RW-S4-020 | INV | Invariant: SL is independent of pension — pension reduces IT/A | 2026/27 | income_tax |
| RW-S4-021 | INV | Invariant: NI is independent of pension — NI on gross profit,  | 2026/27 | income_tax |
| RW-S4-022 | INV | Invariant: zero-tax floor — income below all thresholds produc | 2026/27 | income_tax |
| RW-S4-023 | INV | Invariant: ROUND_HALF_UP for IT at 20% — £0.005 rounds UP to £ | 2026/27 | income_tax |
| RW-S4-024 | INV | Invariant: ROUND_HALF_UP for NI at 2% upper rate — £0.005 roun | 2026/27 | income_tax |
| RW-S4-025 | INV | Invariant: ROUND_HALF_UP for SL at 9% — £0.045 rounds UP to £0 | 2026/27 | income_tax |
| RW-S4-026 | INV | Invariant: component additivity — IT + NI + SL equals the repo | 2026/27 | income_tax |
| RW-S4-027 | VAL | Validation: zero invoice — engine must reject; UNSUPPORTED_EXP | 2026/27 | income_tax |
| RW-S4-028 | VAL | Validation: single-penny invoice entirely within PA — all comp | 2026/27 | income_tax |
| RW-S4-029 | VAL | Validation: pension far exceeds income — ANI = 0; no negative  | 2026/27 | income_tax |
| RW-S4-030 | VAL | Validation: CGT — gain exactly equals AEA; zero taxable gain,  | 2026/27 | cgt |
| RW-S4-031 | VAL | Validation: CGT — all gain at 18% basic rate when taxable inco | 2026/27 | cgt |
| RW-S4-032 | VAL | Validation: CGT — brought-forward losses exceed gain; net gain | 2026/27 | cgt |