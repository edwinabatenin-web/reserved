# Regression Integrity Report — Pre-Stage 3
**Document:** RW-RI-001
**Assurance cycle:** Reserved West Initiative 001
**Date:** 2026-08-06
**Status:** ✅ CONFIRMED — All regression tests green; no historical regression introduced or weakened

---

## 1. Purpose

This report confirms, immediately prior to Stage 3, that:

1. All existing regression tests pass.
2. EL-001 regression tests remain green.
3. No regression test has been removed or weakened.
4. Every historical defect has at least one permanent regression test protecting it.

---

## 2. Full test suite run

The complete test suite was executed immediately prior to Stage 3:

```
Main application tests:  523 passed   (pytest tests/)
Engine bundle tests:     152 passed   (pytest reserved-engine-2.0.0/tests/)
Total:                   675 passed   0 failed   0 errors
```

**Result: ✅ All 675 tests pass.**

---

## 3. EL-001 regression tests

EL-001 (Moving Personal Allowance) is a permanent regression family. Any recurrence is
a gate-blocking REGRESSION_EL001 defect.

**Test file:** `tests/test_el001_regression.py`
**Test count:** 18 tests

### Test inventory

| Test | Purpose | Result |
|---|---|---|
| `test_basic_rate_invoice_no_variance` | Confirm no variance outside taper zone | ✅ |
| `test_higher_rate_invoice_no_variance` | Invoice fully at 40%; no PA change | ✅ |
| `test_taper_entry_zero_variance` | Invoice enters taper (ANI crosses £100k) — v2.0.0 must pass | ✅ |
| `test_fully_within_taper_zero_variance` | Invoice fully within taper zone — v2.0.0 must pass | ✅ |
| `test_pa_elimination_zero_variance` | Invoice crosses £125,140 elimination — v2.0.0 must pass | ✅ |
| `test_no_variance_below_taper` | Below taper: no EL-001 zone; variance must be zero | ✅ |
| `test_taper_entry_variance_is_regression` | If v2.0.0 regresses, variance would be non-zero | ✅ |
| `test_various_income_levels_outside_taper` | Multiple income levels below £100k; all PASS | ✅ |
| `test_cgt_scenarios_not_el001` | CGT scenarios never flagged as EL-001 zone | ✅ |
| `test_el001_zone_detection_boundary` | `in_el001_zone()` boundary detection accuracy | ✅ |
| `test_canonical_gabriel_persona` | Gabriel canonical scenario; no variance | ✅ |
| `test_dual_student_loan_taper_zone` | SL + taper zone combined; no variance | ✅ |
| `test_pension_eliminates_taper` | Pension reduces ANI below £100k; no EL-001 | ✅ |
| `test_pension_partial_taper_relief` | Pension partially reduces ANI; still EL-001 zone | ✅ |
| `test_2025_26_taper_scenarios` | EL-001 zone in 2025/26 tax year | ✅ |
| `test_pa_taper_sequential_invoices` | Multiple sequential invoices through taper | ✅ |
| `test_el001_zone_variance_is_regression_not_known_limitation` | **Classification test**: EL-001 variance → REGRESSION_EL001, never KNOWN_LIMITATION | ✅ |
| `test_el001_zero_variance_is_pass` | Zero variance in EL-001 zone returns PASS | ✅ |

**All 18 EL-001 regression tests: ✅ GREEN**

---

## 4. EL-002 regression test

EL-002 (CGT BASIC_RATE_LIMIT sourced from module-level constant instead of versioned config)
was resolved in engine v1.0.0.

**Test file:** `tests/test_capital_gains.py`
**Test:** `test_cgt_uses_versioned_brl` (line ~188)

```python
def test_cgt_uses_versioned_brl():
    """The CGT basic-rate band boundary must equal tax_config.BASIC_RATE_LIMIT."""
    # If BASIC_RATE_LIMIT were hardcoded in capital_gains.py, changing
    # the config would not propagate. This test verifies the config is
    # read at runtime: an invoice exactly at BASIC_RATE_LIMIT leaves zero
    # basic-band remaining.
    brl = float(tax_config.BASIC_RATE_LIMIT)
    ...
```

**Result: ✅ GREEN** (within 523 passing main tests)

---

## 5. Defect-to-regression mapping

Every historical defect has at least one permanent regression test:

| Defect ID | Description | Regression test(s) | Status |
|---|---|---|---|
| EL-001 | Moving Personal Allowance | `tests/test_el001_regression.py` — 18 tests | ✅ All green |
| EL-002 | CGT BRL from versioned config | `tests/test_capital_gains.py::test_cgt_uses_versioned_brl` | ✅ Green |

---

## 6. Regression test integrity checks

| Check | Result |
|---|---|
| EL-001 regression file exists at expected path | ✅ `tests/test_el001_regression.py` — confirmed |
| EL-001 test count unchanged (18) | ✅ Confirmed (grep `def test_` = 18) |
| EL-002 regression test exists | ✅ `tests/test_capital_gains.py` — confirmed |
| `KNOWN_LIMITATION` outcome code absent from runner | ✅ Not present in `reserved_west/runner.py` |
| `REGRESSION_EL001` classification confirmed in runner | ✅ `_classify()` returns `REGRESSION_EL001` for el001=True with variance > 0 |
| Classification test (`test_el001_zone_variance_is_regression_not_known_limitation`) passes | ✅ |
| No test file deletions relative to last baseline | ✅ All test files present |

---

## 7. Stage 2 EL-001 zone verification

In addition to the unit regression tests, all 17 Stage 2 EL-001 zone scenarios were
executed as part of Stage 2 assurance and returned PASS with zero variance:

| Scenario | Description | Outcome |
|---|---|---|
| RW-S2-006 | PA taper zone — invoice enters taper (EL-001 family) | PASS |
| RW-S2-007 | PA taper zone — invoice fully within taper (EL-001 family) | PASS |
| RW-S2-008 | Six-figure earner — invoice crosses PA elimination (EL-001 family) | PASS |
| RW-S2-027 | Taper start — invoice enters taper zone (EL-001 family) | PASS |
| RW-S2-028 | Taper midpoint — invoice ends below midpoint | PASS |
| RW-S2-029 | Taper midpoint — invoice ends at midpoint (PA = £6,285) | PASS |
| RW-S2-030 | Taper midpoint — invoice crosses midpoint | PASS |
| RW-S2-031 | PA zero boundary — invoice ends just below PA elimination | PASS |
| RW-S2-032 | PA zero boundary — invoice ends exactly at PA elimination | PASS |
| RW-S2-033 | PA zero boundary — invoice crosses PA elimination into 45% | PASS |
| RW-S2-042 | Combined — salary in PA taper zone, freelance extends (EL-001) | PASS |
| RW-S2-079 | Pension — reduces ANI to just below taper start (PA preserved) | PASS |
| RW-S2-080 | Pension — prevents PA taper at start but invoice crosses into taper | PASS |
| RW-S2-081 | Pension — eliminates PA taper effect entirely | PASS |
| RW-S2-122 | SEQ Journey B — Invoice 3 of 4 (YTD=60k, near taper, EL-001 family) | PASS |
| RW-S2-123 | SEQ Journey B — Invoice 4 of 4 (YTD=110k, crosses PA elimination) | PASS |
| RW-S2-130 | SEQ Journey D — Invoice 3 of 4 (YTD=10k, EL-001 watch zone) | PASS |

**Combined EL-001 zone coverage: 20 scenarios (3 Stage 1 + 17 Stage 2), all PASS.**

---

## 8. Conclusion

The regression integrity check is satisfied in full:

1. ✅ All historical defects remain resolved.
2. ✅ All 18 EL-001 regression tests remain green.
3. ✅ The EL-002 regression test remains green.
4. ✅ No regression test has been removed or weakened.
5. ✅ Every historical defect has at least one permanent regression test.
6. ✅ `KNOWN_LIMITATION` is absent from the runner; `REGRESSION_EL001` is active.
7. ✅ All 675 tests pass.

**The engine regression baseline is intact. Stage 3 may proceed.**
