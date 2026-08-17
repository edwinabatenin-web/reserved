"""
Income-tax engine tests — Reserved 2026/27.

Golden values are computed independently from first principles using published
HMRC 2026/27 thresholds and standard sole-trader tax rules.  Every assertion
includes the manual workings so reviewers can re-verify without running code.

Personas
--------
  Gabriel   — mid-career freelancer crossing the higher-rate boundary, Plan 2
               student loan, Relief-at-Source pension
  Hannah    — first-year freelancer, single small invoice, no deductions
  Emily     — employee with side income, crossing basic/higher boundary mid-invoice
  Felipe    — pure freelancer with RaS pension keeping him in the basic-rate band
  Olivia    — very high earner, PA fully tapered to zero
  Priya     — high earner with pension that restores full PA via ANI reduction
  Dual-loan — Plan 1 + Postgraduate running concurrently
"""
from decimal import Decimal

import pytest

from reserved.engines.income_tax import estimate_incremental_liability

pytestmark = pytest.mark.engine


# ── Helpers ──────────────────────────────────────────────────────────────────

def D(s: str) -> Decimal:
    return Decimal(s)


# ── Gabriel persona ──────────────────────────────────────────────────────────
#
# Profile:
#   Employment income      £40,000
#   YTD freelance profit   £15,000
#   Pension (gross, RaS)   £ 5,000
#   Student loan           Plan 2 (threshold £29,385)
#
# Invoice: £10,000
#
# start_income = 40000 + 15000 = 55000
# end_income   = 55000 + 10000 = 65000
# ANI          = 65000 − 5000  = 60000 → PA = 12570 (full)
# Extended HRT (higher-rate threshold) = 50270 + 5000  = 55270
#
# Income tax (55000→65000, HRT=55270):
#   55000→55270  20 % × 270    =    54.00
#   55270→65000  40 % × 9730   = 3,892.00
#                              = 3,946.00
#
# Class 4 NI (freelance 15000→25000):
#   main band: min(25000,50270)−max(15000,12570) = 25000−15000 = 10000
#   6 % × 10000 = 600.00
#
# Student loan Plan 2 (55000→65000):
#   max(0, 65000−max(55000,29385)) = 65000−55000 = 10000
#   9 % × 10000 = 900.00
#
# Total = 3946.00 + 600.00 + 900.00 = 5,446.00


GABRIEL_PROFILE = {
    "day_job_salary": "40000",
    "ytd_freelance_profit": "15000",
    "personal_pension_contributions": "5000",
    "student_loan_plans": [2],
}


def test_gabriel_income_tax():
    r = estimate_incremental_liability("10000", GABRIEL_PROFILE)
    assert r["income_tax"] == D("3946.00"), r["income_tax"]


def test_gabriel_national_insurance():
    r = estimate_incremental_liability("10000", GABRIEL_PROFILE)
    assert r["national_insurance"] == D("600.00"), r["national_insurance"]


def test_gabriel_student_loan():
    r = estimate_incremental_liability("10000", GABRIEL_PROFILE)
    assert r["student_loan"] == D("900.00"), r["student_loan"]


def test_gabriel_total():
    r = estimate_incremental_liability("10000", GABRIEL_PROFILE)
    assert r["total"] == D("5446.00"), r["total"]


def test_gabriel_metadata():
    r = estimate_incremental_liability("10000", GABRIEL_PROFILE)
    assert r["tax_year"] == "2026/27"
    assert r["rules_version"].startswith("uk-2026-27")
    assert isinstance(r["assumptions"], list)
    assert len(r["assumptions"]) >= 1


# ── Hannah persona ────────────────────────────────────────────────────────────
#
# Profile:
#   Employment income      £0
#   YTD freelance profit   £0
#   Pension                £0
#   No student loan
#
# Invoice: £5,000  (first invoice; fully within Personal Allowance)
#
# start_income = 0, end_income = 5000, ANI = 5000, PA = 12570
# All income below PA → income tax = £0
# NI:  min(5000,50270) − max(0,12570) = 5000−12570 < 0 → £0
# SL:  none → £0
# Total = £0.00


HANNAH_PROFILE = {
    "day_job_salary": "0",
    "ytd_freelance_profit": "0",
    "personal_pension_contributions": "0",
}


def test_hannah_zero_tax_within_allowance():
    r = estimate_incremental_liability("5000", HANNAH_PROFILE)
    assert r["income_tax"] == D("0.00")
    assert r["national_insurance"] == D("0.00")
    assert r["student_loan"] == D("0.00")
    assert r["total"] == D("0.00")


def test_hannah_exactly_at_personal_allowance():
    # Invoice that takes income exactly to £12,570 — still £0 tax.
    r = estimate_incremental_liability("12570", HANNAH_PROFILE)
    assert r["income_tax"] == D("0.00")
    assert r["total"] == D("0.00")


def test_hannah_one_pound_above_personal_allowance():
    # £12,571 end_income → £1 above PA → income tax = 20 % × £1.00 = £0.20.
    # (The invoice is £12,571, taking income from £0 to £12,571; £12,570 is PA-free,
    #  the remaining £1 is taxed at the basic rate.)
    r = estimate_incremental_liability("12571", HANNAH_PROFILE)
    assert r["income_tax"] == D("0.20")


# ── Emily persona ─────────────────────────────────────────────────────────────
#
# Profile:
#   Employment income      £45,000
#   YTD freelance profit   £0
#   Pension                £0
#   No student loan
#
# Invoice: £10,000
#
# start = 45000, end = 55000, ANI = 55000, PA = 12570, BRL = 50270
#
# Income tax:
#   45000→50270  20 % × 5270 = 1,054.00
#   50270→55000  40 % × 4730 = 1,892.00
#                            = 2,946.00
#
# Class 4 NI (freelance 0→10000):
#   min(10000,50270)−max(0,12570) = 10000−12570 < 0 → £0
#
# Total = £2,946.00


EMILY_PROFILE = {
    "day_job_salary": "45000",
    "ytd_freelance_profit": "0",
    "personal_pension_contributions": "0",
}


def test_emily_income_tax():
    r = estimate_incremental_liability("10000", EMILY_PROFILE)
    assert r["income_tax"] == D("2946.00"), r["income_tax"]


def test_emily_no_ni_on_first_invoice():
    # NI applies only to freelance profit; Emily's YTD profit is £0.
    r = estimate_incremental_liability("10000", EMILY_PROFILE)
    assert r["national_insurance"] == D("0.00")


def test_emily_total():
    r = estimate_incremental_liability("10000", EMILY_PROFILE)
    assert r["total"] == D("2946.00")


# ── Felipe persona — pension extends basic-rate band ─────────────────────────
#
# Profile:
#   Employment income      £0
#   YTD freelance profit   £45,000
#   Pension (gross, RaS)   £6,000
#   No student loan
#
# Invoice: £10,000
#
# start = 45000, end = 55000
# ANI  = 55000 − 6000 = 49000 → PA = 12570 (full)
# Extended HRT (higher-rate threshold) = 50270 + 6000 = 56270
#
# Income tax (45000→55000, HRT=56270):
#   All income falls within the extended basic band → 20 % × 10000 = 2,000.00
#
# WITHOUT pension: 20%×5270 + 40%×4730 = 1054 + 1892 = 2,946.00
# Pension saves: £946.00
#
# Class 4 NI (45000→55000):
#   main:  min(55000,50270)−max(45000,12570) = 50270−45000 = 5270
#   upper: max(0, 55000−max(45000,50270))    = 55000−50270 = 4730
#   NI = 5270×0.06 + 4730×0.02 = 316.20 + 94.60 = 410.80
#
# Total = 2000.00 + 410.80 = 2,410.80


FELIPE_PROFILE = {
    "day_job_salary": "0",
    "ytd_freelance_profit": "45000",
    "personal_pension_contributions": "6000",
}


def test_felipe_pension_extends_basic_rate_band():
    """Pension RaS band extension keeps Felipe in the basic-rate band."""
    r = estimate_incremental_liability("10000", FELIPE_PROFILE)
    assert r["income_tax"] == D("2000.00"), r["income_tax"]


def test_felipe_national_insurance():
    r = estimate_incremental_liability("10000", FELIPE_PROFILE)
    assert r["national_insurance"] == D("410.80"), r["national_insurance"]


def test_felipe_total():
    r = estimate_incremental_liability("10000", FELIPE_PROFILE)
    assert r["total"] == D("2410.80"), r["total"]


def test_felipe_pension_saves_vs_no_pension():
    """Pension contribution should reduce the tax bill vs no pension."""
    without = estimate_incremental_liability("10000", {
        **FELIPE_PROFILE,
        "personal_pension_contributions": "0",
    })
    with_ = estimate_incremental_liability("10000", FELIPE_PROFILE)
    assert with_["income_tax"] < without["income_tax"]
    # Income tax saving = £946.00
    saving = without["income_tax"] - with_["income_tax"]
    assert saving == D("946.00"), saving


# ── Olivia persona — PA fully tapered to zero ─────────────────────────────────
#
# Profile:
#   Employment income      £130,000
#   YTD freelance profit   £0
#   Pension                £0
#   No student loan
#
# Invoice: £5,000
#
# start = 130000, end = 135000
# ANI = 135000 > 125140 → PA = 0
# BRL = 50270
#
# Income tax (130000→135000):
#   Above additional rate threshold (125140) → 45 % × 5000 = 2,250.00
#
# Class 4 NI (0→5000):
#   min(5000,50270)−max(0,12570) < 0 → £0
#
# Total = £2,250.00


OLIVIA_PROFILE = {
    "day_job_salary": "130000",
    "ytd_freelance_profit": "0",
    "personal_pension_contributions": "0",
}


def test_olivia_pa_fully_tapered():
    r = estimate_incremental_liability("5000", OLIVIA_PROFILE)
    assert r["income_tax"] == D("2250.00"), r["income_tax"]


def test_olivia_total():
    r = estimate_incremental_liability("5000", OLIVIA_PROFILE)
    assert r["total"] == D("2250.00")


# ── Priya persona — PA taper, pension restores via ANI reduction ──────────────
#
# Profile:
#   Employment income      £95,000
#   YTD freelance profit   £0
#   Pension (gross, RaS)   £12,000   (ANI = 103000 − 12000 = 91000 < 100000)
#   No student loan
#
# Invoice: £8,000
#
# start = 95000, end = 103000
# ANI  = 103000 − 12000 = 91000 < 100000 → PA = 12570 (full)
# Extended HRT (higher-rate threshold) = 50270 + 12000 = 62270
#
# Income tax (95000→103000, HRT=62270):
#   Both start and end are above 62270 → higher rate band
#   40 % × 8000 = 3,200.00
#
# WITHOUT pension (ANI=103000):
#   Reduction = (103000−100000)/2 = 1500 → PA = 12570−1500 = 11070
#   All income above 50270 → higher rate
#   40 % × 8000 = 3,200.00  (same; PA taper doesn't affect marginal rate here)
#   But income_tax is identical because start/end are both above all band
#   ceilings regardless of allowance.
#
# NI: freelance 0→8000 all below lower limit 12570 → £0
#
# Total = £3,200.00


PRIYA_PROFILE = {
    "day_job_salary": "95000",
    "ytd_freelance_profit": "0",
    "personal_pension_contributions": "12000",
}


def test_priya_pension_ani_below_taper_start():
    """Pension reduces ANI below 100k restoring the full PA."""
    r = estimate_incremental_liability("8000", PRIYA_PROFILE)
    assert r["income_tax"] == D("3200.00"), r["income_tax"]
    assert r["national_insurance"] == D("0.00")
    assert r["total"] == D("3200.00")


# ── PA taper boundary — invoice crosses taper start ──────────────────────────
#
# Profile:
#   Employment income      £95,000
#   YTD freelance profit   £0
#   Pension                £0
#   No student loan
#
# Invoice: £10,000
#
# start = 95,000, end = 105,000
# ANI(start) = 95,000 < 100,000 → PA = £12,570
# ANI(end)   = 105,000          → PA = 12,570 − 2,500 = £10,070
#
# True marginal = total_tax(105,000) − total_tax(95,000)
#
#   total_tax(105,000): ANI=105,000 → PA=10,070
#     taxable income = 94,930: 37,700×20% + 57,230×40%
#        = 7,540 + 22,892 = £30,432.00
#
#   total_tax(95,000): ANI=95,000 → PA=12,570
#     IT = (50,270−12,570)×20% + (95,000−50,270)×40%
#        = 37,700×0.20 + 44,730×0.40 = 7,540 + 17,892 = £25,432.00
#
# Marginal IT = 30,432 − 25,432 = £5,000.00
#   The £2,500 PA loss exposes income at 40%, adding £1,000 to the
#   £4,000 tax on the additional income.
#
# NI: freelance 0→10,000 below LPL → £0
# Total = £5,000.00


def test_pa_taper_partially_reduced():
    profile = {
        "day_job_salary": "95000",
        "ytd_freelance_profit": "0",
        "personal_pension_contributions": "0",
    }
    r = estimate_incremental_liability("10000", profile)
    assert r["income_tax"] == D("5000.00"), r["income_tax"]
    assert r["total"] == D("5000.00")


# ── Student loan — all plans independently ───────────────────────────────────
#
# Base profile: employment £30,000, YTD £0, pension £0, invoice £10,000
# start = 30000, end = 40000
#
# Plan thresholds (2026/27):
#   Plan 1: £26,900  Plan 2: £29,385  Plan 4: £33,795  Plan 5: £25,000  PGL: £21,000
#
# chargeable = end − max(start, threshold)
#   Plan 1: max(0, 40000−max(30000,26900)) = 40000−30000 = 10000 → 9% = 900.00
#   Plan 2: max(0, 40000−max(30000,29385)) = 40000−30000 = 10000 → 9% = 900.00
#   Plan 4: max(0, 40000−max(30000,33795)) = 40000−33795 = 6205  → 9% = 558.45
#   Plan 5: max(0, 40000−max(30000,25000)) = 40000−30000 = 10000 → 9% = 900.00
#   PGL:    max(0, 40000−max(30000,21000)) = 40000−30000 = 10000 → 6% = 600.00


BASE_30K = {
    "day_job_salary": "30000",
    "ytd_freelance_profit": "0",
    "personal_pension_contributions": "0",
}


@pytest.mark.parametrize("plan,expected", [
    (1,             "900.00"),
    (2,             "900.00"),
    (4,             "558.00"),
    (5,             "900.00"),
    ("postgraduate","600.00"),
])
def test_student_loan_each_plan(plan, expected):
    profile = {**BASE_30K, "student_loan_plans": [plan]}
    r = estimate_incremental_liability("10000", profile)
    assert r["student_loan"] == Decimal(expected), (plan, r["student_loan"])


def test_student_loan_below_threshold_plan2():
    # Invoice keeps income well below Plan 2 threshold (£29,385).
    # start = 0, end = 5000 → chargeable = 0
    profile = {**BASE_30K, "day_job_salary": "0", "student_loan_plans": [2]}
    r = estimate_incremental_liability("5000", profile)
    assert r["student_loan"] == D("0.00")


def test_student_loan_partially_above_threshold():
    # start = 28000, end = 31000 → Plan 2 threshold = 29385
    # chargeable = max(0, 31000−max(28000, 29385)) = 31000−29385 = 1615
    # 9% × 1615 = 145.35, rounded down to £145 annual liability.
    profile = {
        "day_job_salary": "28000",
        "ytd_freelance_profit": "0",
        "personal_pension_contributions": "0",
        "student_loan_plans": [2],
    }
    r = estimate_incremental_liability("3000", profile)
    assert r["student_loan"] == D("145.00"), r["student_loan"]


# ── Dual student loan (Plan 1 + Postgraduate) ─────────────────────────────────
#
# Profile: employment £30,000, YTD £0, pension £0, invoice £5,000
# start = 30000, end = 35000
#
# Plan 1  (threshold £26,900): chargeable = 35000−30000 = 5000 → 9% = 450.00
# PGL     (threshold £21,000): chargeable = 35000−30000 = 5000 → 6% = 300.00
# Total SL = £750.00


def test_dual_student_loan():
    profile = {
        "day_job_salary": "30000",
        "ytd_freelance_profit": "0",
        "personal_pension_contributions": "0",
        "student_loan_plans": [1, "postgraduate"],
    }
    r = estimate_incremental_liability("5000", profile)
    assert r["student_loan"] == D("750.00"), r["student_loan"]
    assert "student_loan_breakdown" in r
    amounts = {item["plan"]: item["amount"] for item in r["student_loan_breakdown"]}
    assert amounts[1] == D("450.00")
    assert amounts["postgraduate"] == D("300.00")


# ── Legacy singular student_loan_plan key ────────────────────────────────────

def test_legacy_student_loan_plan_key():
    """The old singular 'student_loan_plan' key must still work."""
    profile = {
        "day_job_salary": "30000",
        "ytd_freelance_profit": "0",
        "personal_pension_contributions": "0",
        "student_loan_plan": 2,   # legacy key
    }
    r = estimate_incremental_liability("10000", profile)
    assert r["student_loan"] == D("900.00")


# ── Class 4 NI boundary cases ────────────────────────────────────────────────
#
# LPL = £12,570, UPL = £50,270

def test_ni_entirely_below_lpl():
    # freelance 0 → 10000 (below LPL 12570) → £0
    profile = {
        "day_job_salary": "0",
        "ytd_freelance_profit": "0",
        "personal_pension_contributions": "0",
    }
    r = estimate_incremental_liability("10000", profile)
    assert r["national_insurance"] == D("0.00")


def test_ni_crossing_lpl():
    # freelance 10000 → 20000 (crosses LPL 12570)
    # main: min(20000,50270)−max(10000,12570) = 20000−12570 = 7430
    # 6% × 7430 = 445.80
    profile = {
        "day_job_salary": "0",
        "ytd_freelance_profit": "10000",
        "personal_pension_contributions": "0",
    }
    r = estimate_incremental_liability("10000", profile)
    assert r["national_insurance"] == D("445.80"), r["national_insurance"]


def test_ni_crossing_upl():
    # freelance 48000 → 58000 (crosses UPL 50270)
    # main:  min(58000,50270)−max(48000,12570) = 50270−48000 = 2270 → 6%×2270 = 136.20
    # upper: max(0, 58000−max(48000,50270))     = 58000−50270 = 7730 → 2%×7730 = 154.60
    # NI = 290.80
    profile = {
        "day_job_salary": "0",
        "ytd_freelance_profit": "48000",
        "personal_pension_contributions": "0",
    }
    r = estimate_incremental_liability("10000", profile)
    assert r["national_insurance"] == D("290.80"), r["national_insurance"]


# ── Input validation ──────────────────────────────────────────────────────────

def test_invalid_invoice_zero():
    with pytest.raises(ValueError, match="greater than zero"):
        estimate_incremental_liability("0", {})


def test_invalid_invoice_negative():
    with pytest.raises(ValueError, match="greater than zero"):
        estimate_incremental_liability("-100", {})


def test_invalid_invoice_not_a_number():
    with pytest.raises((ValueError, Exception)):
        estimate_incremental_liability("not-a-number", {})


def test_negative_employment_income_rejected():
    with pytest.raises(ValueError, match="day_job_salary"):
        estimate_incremental_liability("1000", {"day_job_salary": "-1"})


def test_negative_prior_profit_rejected():
    with pytest.raises(ValueError, match="ytd_freelance_profit"):
        estimate_incremental_liability("1000", {"ytd_freelance_profit": "-1"})


def test_negative_pension_rejected():
    with pytest.raises(ValueError, match="personal_pension_contributions"):
        estimate_incremental_liability("1000", {"personal_pension_contributions": "-1"})


def test_missing_profile_fields_default_to_zero():
    """Absent profile keys must default to zero, not raise."""
    r = estimate_incremental_liability("5000", {})
    assert r["total"] == D("0.00")


# ── Decimal precision ─────────────────────────────────────────────────────────

def test_result_values_are_decimal():
    r = estimate_incremental_liability("1000", {})
    for key in ("income_tax", "national_insurance", "student_loan", "total"):
        assert isinstance(r[key], Decimal), f"{key} is not Decimal"


def test_result_values_are_two_dp():
    """All monetary outputs must be quantized to exactly two decimal places."""
    r = estimate_incremental_liability("3333.33", {
        "day_job_salary": "20000",
        "ytd_freelance_profit": "0",
        "personal_pension_contributions": "0",
    })
    for key in ("income_tax", "national_insurance", "student_loan", "total"):
        val = r[key]
        assert val == val.quantize(Decimal("0.01")), f"{key}={val} is not 2 dp"
