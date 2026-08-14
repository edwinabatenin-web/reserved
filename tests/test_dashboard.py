"""
Dashboard service tests.

Verifies that build_dashboard() produces live engine-derived values — not
hard-coded figures — and that changing the profile changes the outputs.

All tests pass ``today=date(2026, 8, 3)`` so results are reproducible.
"""
from datetime import date
from decimal import Decimal

import pytest

from reserved.services.dashboard import build_dashboard, DEFAULT_PROFILE


TODAY = date(2026, 8, 3)


def D(s: str) -> Decimal:
    return Decimal(s)


def test_unsupported_multiple_undergraduate_profile_withholds_all_money_and_allocation():
    result = build_dashboard(
        {
            "day_job_salary": "30000",
            "ytd_freelance_profit": "5000",
            "personal_pension_contributions": "0",
            "student_loan_plans": [1, 2],
        },
        today=TODAY,
    )
    assert result["liability"]["calculation_status"] == "unsupported_rule"
    assert result["liability"]["student_loan"] is None
    assert result["liability"]["total"] is None
    assert result["allocation"] is None
    assert result["summary"]["protected"] is None
    assert result["liability"]["uncertainty_effect"] == "not_determinable"
    assert result["liability"]["student_loan_plans_supplied"] == (1, 2)
    assert "Verify the applicable annual Self Assessment plan treatment" in result["liability"]["verification_requirement"]


@pytest.mark.parametrize("plans", [["mystery"], [2, "mystery"]])
def test_unknown_loan_plan_dashboard_withholds_all_money_and_requires_verification(plans):
    result = build_dashboard({"student_loan_plans": plans}, today=TODAY)
    assert result["liability"]["calculation_status"] == "unsupported_rule"
    assert result["liability"]["student_loan"] is None
    assert result["liability"]["total"] is None
    assert result["allocation"] is None
    assert result["summary"]["protected"] is None
    assert result["liability"]["uncertainty_effect"] == "not_determinable"
    assert "HMRC or a qualified tax adviser" in result["liability"]["verification_requirement"]


# ── Structural contracts ──────────────────────────────────────────────────────

def test_returns_required_keys():
    r = build_dashboard(today=TODAY)
    for key in (
        "profile", "invoice_amount", "liability", "allocation",
        "today", "is_demo", "summary", "connections", "chart", "activity",
    ):
        assert key in r, f"Missing top-level key: {key}"


def test_summary_contains_required_keys():
    s = build_dashboard(today=TODAY)["summary"]
    for key in (
        "protected", "annual_target",
        "funding_percentage", "income_ytd",
    ):
        assert key in s, f"Missing summary key: {key}"


def test_monetary_summary_values_are_decimal():
    s = build_dashboard(today=TODAY)["summary"]
    for key in ("protected", "annual_target", "income_ytd"):
        assert isinstance(s[key], Decimal), f"{key} is not Decimal"


def test_today_is_passed_through():
    r = build_dashboard(today=TODAY)
    assert r["today"] == TODAY


# ── Default profile golden values ─────────────────────────────────────────────
#
# DEFAULT_PROFILE: day_job=42000, ytd_profit=18000, pension=2500, Plan 2
#
# YTD tax = estimate_incremental_liability("18000", {day_job=42000, ytd=0, pension=2500, plans=[2]})
#
# start=42000, end=60000
# ANI = 60000−2500 = 57500 → PA = 12570
# Extended BRL = 50270+2500 = 52770
#
# IT:  20%×(52770−42000) + 40%×(60000−52770)
#    = 20%×10770          + 40%×7230
#    = 2154.00            + 2892.00 = 5046.00
#
# NI (freelance 0→18000):
#   main = min(18000,50270)−max(0,12570) = 18000−12570 = 5430 → 6%×5430 = 325.80
#
# SL Plan2 (42000→60000, thresh=29385):
#   chargeable = 60000−max(42000,29385) = 60000−42000 = 18000 → 9%×18000 = 1620.00
#
# YTD total = 5046.00 + 325.80 + 1620.00 = 6991.80


def test_default_profile_ytd_tax_protected():
    r = build_dashboard(today=TODAY)
    assert r["summary"]["protected"] == D("6991.80"), r["summary"]["protected"]


def test_default_profile_does_not_expose_safe_to_spend():
    r = build_dashboard(today=TODAY)
    assert "safe_to_spend" not in r["summary"]


def test_default_profile_income_ytd():
    r = build_dashboard(today=TODAY)
    assert r["summary"]["income_ytd"] == D("18000.00")


def test_default_profile_reserve_rate():
    # reserve_rate = round(6991.80 / 18000 * 100) = round(38.84) = 39
    r = build_dashboard(today=TODAY)
    assert r["summary"]["funding_percentage"] == 39, r["summary"]["funding_percentage"]


def test_default_profile_annual_target_greater_than_ytd_tax():
    r = build_dashboard(today=TODAY)
    assert r["summary"]["annual_target"] > D("6991.80")


# ── Zero income profile ───────────────────────────────────────────────────────

ZERO_PROFILE = {
    "first_name": "Test",
    "entity_type": "sole_trader",
    "day_job_salary": "0",
    "ytd_freelance_profit": "0",
    "personal_pension_contributions": "0",
    "student_loan_plans": [],
    "vat_registered": False,
    "accounting_method": "cash_basis",
}


def test_zero_income_all_summary_zeros():
    r = build_dashboard(ZERO_PROFILE, today=TODAY)
    s = r["summary"]
    assert s["protected"]     == D("0.00")
    assert s["income_ytd"]    == D("0.00")
    assert s["annual_target"] == D("0.00")
    assert s["funding_percentage"] == 0


# ── Profile sensitivity ───────────────────────────────────────────────────────

def test_higher_ytd_profit_raises_protected():
    low  = build_dashboard({**ZERO_PROFILE, "ytd_freelance_profit": "10000"}, today=TODAY)
    high = build_dashboard({**ZERO_PROFILE, "ytd_freelance_profit": "20000"}, today=TODAY)
    assert high["summary"]["protected"] > low["summary"]["protected"]


def test_higher_ytd_profit_has_higher_tax_reserve_ratio_than_lower():
    """Higher total income has a higher effective tax reserve ratio.

    Comparing £15k (mostly within PA/LPL) vs £55k (well into basic-rate band)
    where the effective rate on the upper portion is 20% IT + 6% NI = 26%.
    """
    low  = build_dashboard({**ZERO_PROFILE, "ytd_freelance_profit": "15000"}, today=TODAY)
    high = build_dashboard({**ZERO_PROFILE, "ytd_freelance_profit": "55000"}, today=TODAY)
    low_ratio  = float(low["summary"]["protected"]  / low["summary"]["income_ytd"])
    high_ratio = float(high["summary"]["protected"] / high["summary"]["income_ytd"])
    assert high_ratio > low_ratio


def test_pension_reduces_protected():
    """Pension RaS band extension should lower the estimated tax liability."""
    without = build_dashboard(
        {**ZERO_PROFILE, "ytd_freelance_profit": "55000"},
        today=TODAY,
    )
    with_ = build_dashboard(
        {**ZERO_PROFILE, "ytd_freelance_profit": "55000",
         "personal_pension_contributions": "6000"},
        today=TODAY,
    )
    assert with_["summary"]["protected"] < without["summary"]["protected"]


def test_student_loan_increases_protected():
    base = build_dashboard(
        {**ZERO_PROFILE, "day_job_salary": "30000", "ytd_freelance_profit": "10000"},
        today=TODAY,
    )
    with_sl = build_dashboard(
        {**ZERO_PROFILE, "day_job_salary": "30000", "ytd_freelance_profit": "10000",
         "student_loan_plans": [2]},
        today=TODAY,
    )
    assert with_sl["summary"]["protected"] > base["summary"]["protected"]


# ── Invoice calculator independence ──────────────────────────────────────────
#
# The calculator panel (allocation / liability) uses the invoice amount,
# NOT the YTD figures. Changing the invoice must change allocation but not
# the YTD summary.

def test_invoice_calculator_uses_invoice_amount():
    small = build_dashboard(DEFAULT_PROFILE.copy(), "1000.00", today=TODAY)
    large = build_dashboard(DEFAULT_PROFILE.copy(), "10000.00", today=TODAY)
    assert small["allocation"]["tax_reserve"] < large["allocation"]["tax_reserve"]


def test_invoice_calculator_does_not_change_ytd_summary():
    small = build_dashboard(DEFAULT_PROFILE.copy(), "1000.00", today=TODAY)
    large = build_dashboard(DEFAULT_PROFILE.copy(), "10000.00", today=TODAY)
    assert small["summary"]["protected"] == large["summary"]["protected"]
    assert small["summary"]["income_ytd"] == large["summary"]["income_ytd"]


def test_allocation_reconciles():
    r = build_dashboard(today=TODAY)
    alloc = r["allocation"]
    assert alloc["reconciles"] is True


# ── Invoice calculator golden values ─────────────────────────────────────────
#
# Default profile, invoice £4,800:
# start=60000, end=64800
# ANI = 64800−2500 = 62300 → PA = 12570
# Extended BRL = 50270+2500 = 52770
#
# IT (60000→64800, BRL=52770):
#   60000 > 52770 → all higher rate
#   40% × 4800 = 1920.00
#
# NI (freelance 18000→22800):
#   main = min(22800,50270)−max(18000,12570) = 22800−18000 = 4800 → 6%×4800 = 288.00
#
# SL Plan2 (60000→64800, thresh=29385):
#   chargeable = 64800−max(60000,29385) = 64800−60000 = 4800 → 9%×4800 = 432.00
#
# Total = 1920+288+432 = 2640.00


def test_default_invoice_income_tax():
    r = build_dashboard(today=TODAY)
    assert r["liability"]["income_tax"] == D("1920.00"), r["liability"]["income_tax"]


def test_default_invoice_ni():
    r = build_dashboard(today=TODAY)
    assert r["liability"]["national_insurance"] == D("288.00"), r["liability"]["national_insurance"]


def test_default_invoice_student_loan():
    r = build_dashboard(today=TODAY)
    assert r["liability"]["student_loan"] == D("432.00"), r["liability"]["student_loan"]


def test_default_invoice_total():
    r = build_dashboard(today=TODAY)
    assert r["liability"]["total"] == D("2640.00"), r["liability"]["total"]


def test_default_invoice_allocation_does_not_expose_safe_to_spend():
    r = build_dashboard(today=TODAY)
    assert "safe_to_spend" not in r["allocation"]


# ── is_demo flag ──────────────────────────────────────────────────────────────

def test_is_demo_true_by_default():
    r = build_dashboard(today=TODAY)
    assert r["is_demo"] is True


def test_is_demo_false_when_passed():
    r = build_dashboard(DEFAULT_PROFILE.copy(), is_demo=False, today=TODAY)
    assert r["is_demo"] is False


# ── Activity feed ─────────────────────────────────────────────────────────────

def test_activity_has_three_items():
    r = build_dashboard(today=TODAY)
    assert len(r["activity"]) == 3


def test_activity_items_have_required_keys():
    r = build_dashboard(today=TODAY)
    for item in r["activity"]:
        for key in ("title", "detail", "time", "meta"):
            assert key in item, f"Activity item missing key: {key}"


def test_activity_with_zero_income_no_tax_estimate():
    r = build_dashboard(ZERO_PROFILE, today=TODAY)
    first = r["activity"][0]
    # Should prompt to add income rather than show a reserve amount
    assert "income" in first["title"].lower() or "add" in first["title"].lower()
