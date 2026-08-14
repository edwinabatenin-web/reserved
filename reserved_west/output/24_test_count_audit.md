# Test Count Audit Note — Reserved West Initiative 001
**Document:** RW-AUDIT-001
**Assurance cycle:** Reserved West Initiative 001
**Date:** 2026-08-07
**Status:** ✅ Reconciled — no tests removed; discrepancy is a reporting/classification artefact

---

## 1. Subject

During the project a figure of **699** was cited in the session summary as the workspace
test count (`tests/`).  The actual verified workspace count is **547**.  This note
reconciles the discrepancy, confirms that no regression coverage has been lost, and
establishes the permanent baseline for all future reports.

---

## 2. Evidence trail — test count history

| Checkpoint | Workspace (`tests/`) | Bundle (`reserved-engine-2.0.0/tests/`) | Combined | Source |
|---|---|---|---|---|
| Pre-Stage 3 baseline | **523** | **152** | **675** | Docs 15 + 16 (RW-BL-001 / RW-RI-001) |
| After EL-003 workspace tests added | **547** | 152 (not yet updated) | **699** | `MANIFEST.json` `reserved_full_suite_result` — intermediate snapshot |
| After EL-003 bundle tests added | **547** | **165** | **712** | Current verified state |

---

## 3. How the figure of 699 was derived

**Origin:** `reserved-engine-2.0.0/MANIFEST.json`, field `test_suite_summary.reserved_full_suite_result`,
value `"699 passed"`.

**How it was produced:** During the EL-003 fix, a single agent turn:

1. Added `tests/test_el003_regression.py` (24 tests) → workspace count rose from 523 to **547**.
2. Updated `MANIFEST.json`, recording a combined pytest run (workspace + bundle) *at that moment*:
   `547 (workspace) + 152 (bundle, not yet updated) = 699`.
3. Then added `reserved-engine-2.0.0/tests/test_el003_regression.py` (13 tests) → bundle count
   rose from 152 to **165**.

All three file writes landed in the same git commit (`5601ec3`), so version control cannot
distinguish the order.  The MANIFEST captured an intermediate combined state: the workspace
update had already occurred but the bundle update had not.

**How it propagated:** The session summary picked up `"699 passed"` from MANIFEST and
misattributed it as the *workspace-only* count, labelling it
`"699 workspace (tests/)"`.  The `combined` nature of the figure was dropped, and
the bundle's contribution (152 at that moment) was silently merged into a figure
that appeared to describe a single suite.

---

## 4. Why the current workspace count is 547 (not 699)

547 is the correct and complete workspace-only count.  It was never 699.

| Test file | Count |
|---|---|
| `tests/test_allocation.py` | 16 |
| `tests/test_auth.py` | 91 |
| `tests/test_capital_gains.py` | 21 |
| `tests/test_dashboard.py` | 27 |
| `tests/test_el001_regression.py` | 18 |
| `tests/test_el003_regression.py` | 24 |
| `tests/test_income_tax.py` | 40 |
| `tests/test_income_tax_boundaries.py` | 41 |
| `tests/test_matching.py` | 127 |
| `tests/test_multi_year.py` | 18 |
| `tests/test_persistence.py` | 32 |
| `tests/test_transaction_classification.py` | 53 |
| `tests/test_ws7.py` | 39 |
| **Total** | **547** |

The increase from the pre-Stage 3 baseline of 523 is entirely accounted for by the
24 EL-003 regression tests added in `tests/test_el003_regression.py`.
`523 + 24 = 547`.

---

## 5. Confirmation that no tests have been removed

```
git log --diff-filter=D -- "tests/*.py" "reserved-engine-2.0.0/tests/*.py"
→ (no output)
```

No test file has ever been deleted from this repository.  The discrepancy is
**purely a reporting and classification artefact**: a combined figure was
misattributed as a single-suite figure in a session summary.

---

## 6. Current test inventory (authoritative baseline from 2026-08-07)

### Pytest suites

| Suite | Run command | Count | Result |
|---|---|---|---|
| Workspace application tests | `pytest tests/` | **547** | ✅ All passing |
| Standalone engine bundle tests | `PYTHONPATH=reserved-engine-2.0.0 pytest reserved-engine-2.0.0/tests/` | **165** | ✅ All passing |
| **Total executable pytest tests** | | **712** | ✅ All passing |

### Reserved West independent assurance scenarios

| Stage | Scenario IDs | Count | Gate |
|---|---|---|---|
| Stage 1 — Core calculations | RW-S1-001 – RW-S1-030 | 30 | ✅ PASSED |
| Stage 2 — Representative & boundary | RW-S2-001 – RW-S2-150 | 150 | ✅ PASSED |
| Stage 3 — Interaction | RW-S3-001 – RW-S3-080 | 80 | ✅ PASSED |
| **Total assurance scenarios** | | **260** | |

Reserved West scenarios are run by the standalone runner (`python -m reserved_west.run_stage3`
etc.), not by pytest.  They must not be combined with the pytest counts.

### Regression test coverage by defect family

| Defect | Family status | Test file(s) | Test count | Result |
|---|---|---|---|---|
| EL-001 (Moving Personal Allowance) | Permanent regression family | `tests/test_el001_regression.py` | 18 | ✅ All green |
| EL-002 (CGT BRL from versioned config) | Resolved; 1 regression test | `tests/test_capital_gains.py` | 1 | ✅ Green |
| EL-003 (eBRL not capped at ART) | Permanent regression family | `tests/test_el003_regression.py` + `reserved-engine-2.0.0/tests/test_el003_regression.py` | 24 + 13 = 37 | ✅ All green |

---

## 7. Confirmation that no regression coverage has been lost

The current test suite is a **strict superset** of every prior baseline:

| Baseline | Workspace count | Bundle count | Status |
|---|---|---|---|
| Pre-EL-001 fix (v1.0.0 → v2.0.0) | <523 | <152 | Superseded |
| Pre-Stage 3 baseline (RW-BL-001) | 523 | 152 | ✅ Superseded — all 675 tests still present |
| Post-EL-003 fix (v2.0.1) | **547** | **165** | ✅ Current |

EL-001 (18 tests), EL-002 (1 test), and EL-003 (37 tests) regression families are
all present, named, and green.  The scenario catalogue covers 19 EL-001 zone
scenarios in Stage 3 alone (up from the 20 across Stages 1+2 at the pre-Stage 3
baseline).  No defect family is weaker than at any prior checkpoint.

---

## 8. Root cause of the reporting discrepancy

Two separate failures combined to produce the cited figure of 699:

**Primary cause — intermediate MANIFEST snapshot.**
The field `test_suite_summary.reserved_full_suite_result` in `MANIFEST.json` records a
combined pytest count taken *within an agent turn*, after workspace tests were updated
but before bundle tests were updated.  A within-turn snapshot is not a stable checkpoint:
both updates land in the same git commit, but the snapshot can only reflect the state at
the moment it was written.  The field captured `547 + 152 = 699` — a transient figure
that was never the final state of that commit.

**Secondary cause — misattribution in session summary.**
The session summary read `"699 passed"` from MANIFEST and reported it as
*workspace-only* (`"699 workspace (tests/)"`), stripping out the fact that this was a
combined figure.  This made the number appear to describe a single suite rather than a
mid-turn combined count.

---

## 9. Process improvement

**MANIFEST.json should record workspace and bundle counts as separate fields, not as a
combined total.**  A combined figure conflates two independently runnable test suites and
is fragile to within-turn ordering.  The field `reserved_full_suite_result` has been
corrected and split (see section 10).

**Future reporting rule:** Any cited test count must specify exactly which run command
produced it.  The three categories must never be aggregated without explicit labelling:

| Category | Run command | Label |
|---|---|---|
| Workspace tests | `pytest tests/` | "workspace" |
| Bundle tests | `PYTHONPATH=reserved-engine-2.0.0 pytest reserved-engine-2.0.0/tests/` | "bundle" |
| All pytest | both commands combined | "combined" |
| Assurance scenarios | `python -m reserved_west.run_stageN` | "scenarios (not pytest)" |

---

## 10. MANIFEST.json correction

The field `test_suite_summary.reserved_full_suite_result` in
`reserved-engine-2.0.0/MANIFEST.json` has been corrected from:

```
"reserved_full_suite_result": "699 passed"
```

to:

```
"reserved_workspace_tests":    "547 passed  (pytest tests/)",
"reserved_bundle_tests":       "165 passed  (PYTHONPATH=reserved-engine-2.0.0 pytest reserved-engine-2.0.0/tests/)",
"reserved_combined_tests":     "712 passed  (both suites)",
"reserved_full_suite_note":    "699 was an intermediate combined count (workspace 547 + bundle 152 pre-EL-003-bundle) captured mid-turn; the correct final figure is 712."
```

---

## 11. Sign-off

| Assertion | Result |
|---|---|
| 699 workspace tests never existed | ✅ Confirmed — 699 was a combined intermediate figure |
| No test files deleted at any point in project history | ✅ Confirmed via git log --diff-filter=D |
| Current workspace count is 547 | ✅ Confirmed by live pytest run |
| Current bundle count is 165 | ✅ Confirmed by live pytest run |
| Combined total is 712 | ✅ Confirmed |
| All 712 tests pass | ✅ Confirmed |
| All regression families (EL-001 / EL-002 / EL-003) intact | ✅ Confirmed |
| No regression coverage lost relative to any prior baseline | ✅ Confirmed — current is strict superset |
| MANIFEST.json corrected | ✅ Done |
| Permanent documentation updated | ✅ This document (RW-AUDIT-001) |
