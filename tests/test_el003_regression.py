"""
EL-003 regression suite — Relief-at-Source pension band extension.

EL-003 concerns the income-tax treatment of gross Relief-at-Source pension
contributions.  The correct rule (HMRC Pensions Tax Manual PTM056120, "Basic
and higher rate limits") is that a gross RAS contribution extends **both** the
basic-rate limit and the higher-rate limit (the point at which the additional
45 % rate begins) by the gross amount:

    extended basic-rate limit  = £37,700 + pension
    extended higher-rate limit = £125,140 + pension

This preserves the £87,440 higher-rate band width and shifts the additional-rate
threshold up by the contribution amount.  There is **no cap** at £125,140.

Earlier engine versions modelled only the basic-rate limit extension (and, in
v2.0.1, incorrectly capped it at the Additional Rate Threshold), which left a
fixed £125,140 higher-rate limit and overcharged the additional-rate slice.
This suite pins the corrected treatment so the defect cannot be reintroduced.

Decisive fixture: RW3-PEN-005 (£125,141 income, £1 pension → £42,516.20).
"""
from decimal import Decimal as D

import pytest

from reserved.engines.income_tax import (
    _total_income_tax,
    estimate_incremental_liability,
)
from reserved.engines.tax_config import get_config
from reserved_west.reference_calculator import ref_estimate

TAX_YEAR = "2026/27"
CFG = get_config(TAX_YEAR)


def _total(income, pension=0):
    return _total_income_tax(D(str(income)), D(str(pension)), CFG)


def _run(invoice, salary=0, ytd=0, pension=0, plans=None, year=TAX_YEAR):
    profile = {
        "day_job_salary":                salary,
        "ytd_freelance_profit":          ytd,
        "personal_pension_contributions": pension,
        "student_loan_plans":             plans or [],
    }
    ref = ref_estimate(invoice, profile, year)
    eng = estimate_incremental_liability(invoice, profile, year)
    return ref, eng


# ── Decisive boundaries (full-liability, independently derived) ──────────────

class TestRASDecisiveBoundaries:
    def test_125140_no_pension(self):
        # PA fully withdrawn at ANI = 125,140 → taxable 125,140.
        # 37,700 @ 20 % + 87,440 @ 40 % = 7,540 + 34,976 = 42,516.00
        assert _total(125140) == D("42516.00")

    def test_125141_no_pension(self):
        # £1 above ART without pension → £1 @ 45 % on top.
        assert _total(125141) == D("42516.45")

    def test_rw3_pen_005_decisive(self):
        # £125,141 income + £1 pension → ANI 125,140 → PA £0 → taxable 125,141.
        # extended basic-rate limit  = 37,700 + 1 = 37,701
        # extended higher-rate limit = 125,140 + 1 = 125,141
        # 37,701 @ 20 % = 7,540.20 ; 87,440 @ 40 % = 34,976.00 ; £0 @ 45 %
        # total = 42,516.20
        assert _total(125141, 1) == D("42516.20")

    def test_extended_additional_boundary_below(self):
        # pension £1 → extended higher-rate limit 125,141.
        # income 125,140 → ANI 125,139 → PA 0.50 → taxable 125,139.50 (< boundary).
        assert _total(125140, 1) == D("42515.60")

    def test_extended_additional_boundary_at(self):
        # taxable 125,141 is exactly the extended higher-rate limit → no 45 %.
        assert _total(125141, 1) == D("42516.20")

    def test_extended_additional_boundary_above(self):
        # income 125,142 → taxable 125,142 → £1 above the extended limit @ 45 %.
        assert _total(125142, 1) == D("42516.65")

    def test_large_pension_extends_both_limits(self):
        # £200,000 income, £80,000 pension → ANI 120,000 → PA 2,570 → taxable 197,430.
        # extended basic-rate limit  = 117,700 ; extended higher-rate limit = 205,140.
        # 117,700 @ 20 % = 23,540 ; 79,730 @ 40 % = 31,892 ; £0 @ 45 % = 55,432.
        # (Assumes the full £80,000 is qualifying gross RAS for IT purposes.)
        assert _total(200000, 80000) == D("55432.00")

    def test_pension_extends_higher_boundary_without_removing_additional(self):
        # £200,000 income, £30,000 pension → extended basic 67,700, higher 155,140.
        # 67,700 @ 20 % = 13,540 ; 87,440 @ 40 % = 34,976 ; 44,860 @ 45 % = 20,187
        # total = 68,703.00 (additional-rate slice survives).
        assert _total(200000, 30000) == D("68703.00")

    def test_pa_taper_interaction(self):
        # £110,000 income, £10,000 pension → ANI 100,000 → full PA 12,570.
        # taxable 97,430 ; extended basic 47,700 → 9,540 + 19,892 = 29,432.
        assert _total(110000, 10000) == D("29432.00")

    def test_zero_pension_matches_no_pension_baseline(self):
        assert _total(125141, 0) == _total(125141)

    def test_rule_applies_across_supported_tax_years(self):
        # The band extension rule (PTM056120) applies identically to every
        # supported non-Scottish year (2025/26 and 2026/27 share the frozen
        # £37,700 / £125,140 bands).
        for year in ("2025/26", "2026/27"):
            cfg = get_config(year)
            got = _total_income_tax(D("125141"), D("1"), cfg)
            assert got == D("42516.20"), f"{year}: {got}"


# ── Production ↔ reference parity across pension sizes ───────────────────────

class TestRASParity:
    @pytest.mark.parametrize("pension", [0, 1, 1000, 10000, 30000, 74870, 80000, 100000])
    def test_production_matches_reference(self, pension):
        ref, eng = _run(invoice=5000, salary=120000, ytd=5000, pension=pension)
        assert eng["income_tax"] == ref["income_tax"], (
            f"income_tax mismatch for pension={pension}: "
            f"{eng['income_tax']} vs {ref['income_tax']}"
        )

    def test_rws3_011_scenario(self):
        # Large-pension Stage 3 scenario must agree between engine and reference.
        ref, eng = _run(invoice=5000, salary=120000, ytd=5000, pension=80000)
        assert eng["total"] == ref["total"]


# ── Input validation / limitation behaviour is unchanged ─────────────────────

class TestRASValidation:
    def test_negative_pension_rejected(self):
        with pytest.raises(ValueError):
            estimate_incremental_liability(
                "5000",
                {"day_job_salary": 0, "ytd_freelance_profit": 0,
                 "personal_pension_contributions": -1, "student_loan_plans": []},
                TAX_YEAR,
            )

    def test_non_numeric_pension_rejected(self):
        with pytest.raises(ValueError):
            estimate_incremental_liability(
                "5000",
                {"day_job_salary": 0, "ytd_freelance_profit": 0,
                 "personal_pension_contributions": "not-a-number",
                 "student_loan_plans": []},
                TAX_YEAR,
            )
