# Assurance Decision Log
**Assurance cycle:** Reserved West Initiative 001
**Date:** 2026-08-06

This log records significant decisions, assumptions, and findings
made during the assurance cycle.  Routine implementation details
are omitted; the focus is on reasoning that affects reproducibility.

---

## DL-001 — Reference calculator algorithm
**Decision:** Use `total_tax(end) − total_tax(start)` (total-then-differential)
at both reference and engine.
**Reason:** Maximum independence from the engine.  The reference computes PA
independently at each income point; this was more correct than the engine's
v1.0.0 range-based approach.  Engine v2.0.0 adopted the same algorithm,
resolving EL-001.  Both reference and engine now agree in the taper zone.

## DL-002 — HMRC configuration grounded independently
**Decision:** All thresholds and rates in the reference calculator are
hard-coded from HMRC primary sources (cited inline) rather than copied
from the engine's `tax_config.py`.
**Finding:** Cross-check against `tax_config.py` revealed zero discrepancies
in rates or thresholds for both 2025/26 and 2026/27.  Engine configuration
is confirmed correct.

## DL-003 — EL-001 zone detection role
**Decision:** The EL-001 zone detector (`in_el001_zone`) is retained for
diagnostic annotation (the `el001_zone` field in results) but must not
soften or suppress a failure.  A non-zero variance in the EL-001 zone
is classified `REGRESSION_EL001` — a gate-blocking FAIL.
**Reason:** EL-001 was resolved in engine v2.0.0.  Any recurrence is a
regression defect, not a known limitation.  The outcome `KNOWN_LIMITATION`
has been removed from the runner.

## DL-004 — Penny variance policy
**Decision:** Max absolute variance ≤ £0.01 classified PASS_PENNY.
**Reason:** The reference rounds `total_it()` at each income point before
subtracting; the engine rounds the incremental result.  At integer-pound
inputs (all Stage 1 scenarios) no PASS_PENNY cases actually arose,
confirming the two approaches agree at whole-pound amounts.

## DL-005 — Stage 1 scenario design
**Decision:** 30 scenarios across five groups: Representative (8),
Boundary (8), Student Loan (7), Pension RaS (3), CGT (4).
**Reason:** Covers all supported calculation pathways for smoke-test
confidence.  Does not yet cover cross-year scenarios or all threshold
combinations (deferred to Stage 2).

## DL-006 — Gate 1 outcome
**Decision:** Gate 1 PASSED.
**Reason:** No defects found. All variances are exact matches or acceptable rounding (≤1p). EL-001 is resolved; all taper-zone scenarios PASS.  Stage 2 authorised.

## DL-007 — EL-001 permanent regression family
**Decision:** EL-001 is archived as a permanent regression family with outcome
code `REGRESSION_EL001`.  The outcome `KNOWN_LIMITATION` is retired.
**Reason:** EL-001 was resolved in engine v2.0.0.  Any future recurrence is
a regression defect, not an acceptable known limitation.  The assurance
framework must not re-soften this outcome.
**Scope:** Any variance in a scenario whose income pattern matches the EL-001
family (PA changes between starting and ending tax positions) is classified
REGRESSION_EL001 and is a Critical defect.  This includes all three EL-001
cases: entering the taper, remaining within the taper, and crossing PA elimination.
**Permanent tests:** `tests/test_el001_regression.py` (16 scenarios + classification test).

---

## Key finding: Engine fully correct for all Stage 1 paths

Stage 1 (engine v2.0.0) confirms that the Reserved engine produces exact results
(zero variance) on all 30 scenarios, including the three EL-001 taper-zone cases.
This includes: all four income tax bands, all NI rate boundaries, all
five student loan plans, pension RaS band extension, and CGT
(AEA, brought-forward losses, basic/higher split).

## Key finding: EL-001 is fully resolved

The PA taper moving-allowance defect (EL-001) is fully resolved in v2.0.0.
Permanent regression tests cover all three taper-zone cases.  A classification
test confirms that any future recurrence will produce REGRESSION_EL001 (FAIL),
not KNOWN_LIMITATION.