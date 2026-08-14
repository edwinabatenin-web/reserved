# Stage 4 Findings
**Assurance cycle:** Reserved West Initiative 001
**Engine version:** 2.0.1
**Date:** 2026-08-07

## Headline

- **Total scenarios:** 32
- **PASS:** 31
- **PASS_PENNY:** 0
- **UNSUPPORTED_EXPECTED:** 1
- **FAIL:** 0
- **REGRESSION_EL001:** 0
- **ERROR:** 0

## Finding S4-F0: All scenarios pass

No defects, regressions, or errors were found in Stage 4.

The engine passes all 32 Final Gate scenarios:

**Extreme inputs (EXT):** The engine handles invoices up to £1,000,000, YTD up to £500,000, salary up to £500,000, pension exceeding total income, and all five SL plans on a £200,000 invoice without arithmetic failure or silent truncation.

**Boundary conditions (BND):** The engine lands correctly on all exact thresholds: BRL/UPL at £50,270 (both sides), ART at £125,140 (both sides), PA taper entry at £100,000, PA/LPL joint zero at £12,570, eBRL exactly at ART (EL-003 cap boundary), and SL Plan 2/5 threshold straddles.

**Mathematical invariants (INV):** All eight invariants confirmed: non-negativity of IT, independence of SL and NI from pension contributions, zero-tax floor when income is below all thresholds, and ROUND_HALF_UP for IT (20%), NI upper (2%), and SL (9%). Component additivity confirmed: IT + NI + SL = Total in all cases.

**Validation (VAL):** Zero invoice correctly rejected (UNSUPPORTED_EXPECTED). Single-penny invoice within PA produces zero total tax. Extreme pension (£200k) correctly floors ANI and applies EL-003 cap. CGT correctly handles zero taxable gain (gain = AEA), all-basic-rate gain from zero income, and BF losses exceeding gain.

## UNSUPPORTED_EXPECTED outcomes

| ID | Title |
|---|---|
| RW-S4-027 | Validation: zero invoice — engine must reject; UNSUPPORTED_EXPECTED |

These scenarios confirm the engine correctly rejects invalid inputs. UNSUPPORTED_EXPECTED is a passing outcome.