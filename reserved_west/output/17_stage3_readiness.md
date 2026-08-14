# Stage 3 Readiness Statement
**Document:** RW-RS3-001
**Assurance cycle:** Reserved West Initiative 001
**Date:** 2026-08-06
**Status:** ✅ CLEARED FOR STAGE 3

---

## Decision

**Stage 3 (Interaction Scenarios) may commence.**

All five pre-Stage 3 verification tasks have been completed and confirmed.
The engine is stable, the assurance framework is functioning correctly, and the
evidence base is complete and reproducible.

---

## Verification task summary

| Task | Description | Status |
|---|---|---|
| Task A | Independence of expected results confirmed | ✅ Confirmed (doc 00) |
| Task B | Scenario catalogue audited; all 180 scenarios complete | ✅ Confirmed (doc 14) |
| Task C | Baseline snapshot established | ✅ Complete (doc 15) |
| Task D | Regression integrity verified; all tests green | ✅ Confirmed (doc 16) |
| Task E | This readiness statement | ✅ (this document) |

---

## 1. Engine stability

The engine (v2.0.0) is stable:

- **523 main application tests pass.** No failures, no errors.
- **152 engine bundle tests pass.** No failures, no errors.
- **675 total tests passing.**
- **0 open defects.**
- EL-001 (Moving Personal Allowance) is resolved and regression-pinned.
- EL-002 (CGT config sourcing) is resolved and regression-pinned.

The engine has not changed since Gate 2 was passed. All Stage 2 scenarios continue
to pass with zero variance. No regression has been introduced.

---

## 2. Reference calculator independence

The independent reference calculator remains independent:

- Zero imports from `reserved_engine` or any engine module.
- All thresholds hard-coded from HMRC publications (not shared with engine config).
- Algorithmic approach (total-then-differential) is distinct from the engine's range-based approach.
- All expected values are computed at runtime; no hardcoded expected values exist in scenario definitions.
- All HMRC sources documented in the Reference Register (doc 02).
- All reference calculator assumptions explicitly documented (doc 00).

See Independence Assurance Note (doc 00) for full verification.

---

## 3. Assurance framework functioning correctly

The assurance framework is operating correctly:

- Outcome codes `PASS`, `PASS_PENNY`, `REGRESSION_EL001`, `FAIL`,
  `UNSUPPORTED_EXPECTED`, and `ERROR` are all correctly classified by `runner.py`.
- `KNOWN_LIMITATION` has been retired and is absent from the runner.
- `REGRESSION_EL001` is gate-blocking; the classification test confirms this.
- Gate logic in `run_assurance.py` and `run_stage2.py` correctly evaluates criteria.
- All 13 assurance deliverables (docs 01–13) have been produced and are consistent
  with the scenario and runner results.

---

## 4. Scenario catalogue reproducible

The Scenario Catalogue is fully reproducible:

- All 180 scenarios (30 Stage 1 + 150 Stage 2) contain complete input definitions.
- Every result can be reproduced from the inputs alone, without access to engine source.
- Tax year, income pattern, pension, student loan plans, and CGT inputs are all present.
- HMRC legislative basis is documented in the Reference Register (doc 02).
- Scenario execution status is recorded in evidence registers (docs 03 and 09).

See Catalogue Audit (doc 14) for full verification.

---

## 5. Evidence Register complete

The Evidence Registers are complete for Stages 1 and 2:

- `03_evidence_register.csv` — 30 Stage 1 scenarios with full expected/actual/variance records.
- `09_stage2_evidence_register.csv` — 150 Stage 2 scenarios with full records.
- Both registers include: scenario ID, title, tax year, outcome, el001_zone flag,
  expected values, actual values, and primary variance.

---

## 6. Gate status

| Gate | Question | Status |
|---|---|---|
| Gate 1 | Core calculations verified? | ✅ PASSED — 30/30 PASS |
| Gate 2 | Representative scenarios reliable? | ✅ PASSED — 149/150 PASS + 1 UNSUPPORTED_EXPECTED |

Gate 1 and Gate 2 remain passed. No regression has reopened either gate.

---

## 7. Stage 3 scope

Stage 3 will execute Interaction Scenarios — complex combinations not covered by
Stages 1 and 2. Scenario IDs will begin at **RW-S3-001**.

Planned interaction families:

1. **All components simultaneously** — salary + YTD + pension + multiple student loan plans + invoice, in both tax years
2. **Multi-invoice journeys through combined thresholds** — sequential invoices where salary puts the taxpayer near a threshold and freelance income crosses it
3. **Large pension interactions** — pension large enough to push eBRL to or beyond ART; interaction with PA taper
4. **Student loan + pension cross-effects** — pension affects ANI; SL is income-based; both interact with IT band
5. **CGT + high income tax combined** — income near PA taper + capital gains in the same year
6. **Sequential year comparison** — same earner profile across 2025/26 and 2026/27 with different SL thresholds

Gate 3 criterion: no REGRESSION_EL001, no FAIL, no ERROR across all Stage 3 scenarios.

---

## Authorisation

The pre-Stage 3 verification is complete. All conditions for Stage 3 entry are satisfied.

**Stage 3 is authorised to commence.**
