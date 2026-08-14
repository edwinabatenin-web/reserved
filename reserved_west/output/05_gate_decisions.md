# Gate Decisions
**Assurance cycle:** Reserved West Initiative 001
**Date:** 2026-08-06

---

## Gate 1 — Core calculations verified
**Question:** Are the core calculations and reference implementation sound?
**Decision:** ✅ GATE 1 PASSED

**Evidence:**
  - Total scenarios run (Stage 1): 30
  - PASS (exact):                 30
  - PASS_PENNY (≤1p):             0
  - UNSUPPORTED_EXPECTED:         0
  - REGRESSION_EL001 (FAIL):      0
  - FAIL:                         0
  - ERROR:                        0
  - Scenarios in EL-001 zone:     4 (all PASS — EL-001 resolved in v2.0.0)

**Rationale:** No defects found. All variances are either exact matches
or acceptable rounding (≤1p). EL-001 was resolved in engine v2.0.0;
all PA taper zone scenarios return PASS with zero variance.

**Authorisation to proceed:** Stage 2 (Representative & Boundary,
~150 scenarios) may commence.

---

## Gate 2 — Representative scenarios reliable
**Status:** Not yet evaluated (pending Stage 2 execution)

## Gate 3 — Interaction scenarios complete
**Status:** Not yet evaluated (pending Stage 3 execution)

## Final Gate — Tolerance testing complete, no unresolved Critical issues
**Status:** Not yet evaluated (pending Stage 4 execution)
