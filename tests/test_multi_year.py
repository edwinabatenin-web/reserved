"""
Multi-year tax engine tests — 2025/26 vs 2026/27.

Verifies that:
  1. The ``tax_year`` parameter selects the correct configuration.
  2. Income-tax and NI results are identical between supported years
     (bands are frozen; rates unchanged).
  3. Student-loan repayment amounts differ between years where thresholds
     were uprated by the Student Loans Company.
  4. Invalid year strings raise ValueError.

2025/26 thresholds (SLC Annual Threshold Notice 2025/26)
---------------------------------------------------------
  Plan 1  £24,990   Plan 2  £28,470   Plan 4  £32,745
  Plan 5  £25,000   PGL     £21,000   (Plans 5 and PGL: fixed by statute)

2026/27 thresholds (SLC Annual Threshold Notice 2026/27)
---------------------------------------------------------
  Plan 1  £26,900   Plan 2  £29,385   Plan 4  £33,795
  Plan 5  £25,000   PGL     £21,000

Income tax and NI bands are frozen (PA £12,570; BRL £50,270; ART £125,140;
LPL £12,570; UPL £50,270) and identical in both years.
"""
from decimal import Decimal

import pytest

from reserved.engines.income_tax import estimate_incremental_liability
from reserved.engines import tax_config

pytestmark = pytest.mark.engine


def D(s: str) -> Decimal:
    return Decimal(s)


# ── Helpers ───────────────────────────────────────────────────────────────────

_ZERO = {"day_job_salary": "0", "ytd_freelance_profit": "0",
         "personal_pension_contributions": "0"}


def _run(invoice, profile_extra=None, tax_year="2026/27"):
    profile = {**_ZERO, **(profile_extra or {})}
    return estimate_incremental_liability(invoice, profile, tax_year=tax_year)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  1. Year selection and metadata                                            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_default_tax_year_is_2026_27():
    """Omitting ``tax_year`` defaults to 2026/27."""
    r = estimate_incremental_liability("1000", _ZERO)
    assert r["tax_year"] == "2026/27"


def test_explicit_2026_27():
    """Explicit ``tax_year="2026/27"`` works and sets correct metadata."""
    r = estimate_incremental_liability("1000", _ZERO, tax_year="2026/27")
    assert r["tax_year"]      == "2026/27"
    assert r["rules_version"] == "uk-2026-27-v4"


def test_explicit_2025_26_metadata():
    """``tax_year="2025/26"`` sets 2025/26 metadata fields."""
    r = estimate_incremental_liability("1000", _ZERO, tax_year="2025/26")
    assert r["tax_year"]      == "2025/26"
    assert r["rules_version"] == "uk-2025-26-v2"


def test_invalid_tax_year_raises_value_error():
    """Unsupported tax year must raise ValueError."""
    with pytest.raises(ValueError, match="not supported"):
        estimate_incremental_liability("1000", _ZERO, tax_year="2023/24")


def test_get_config_raises_for_unsupported_year():
    """tax_config.get_config() raises ValueError for unknown year."""
    with pytest.raises(ValueError, match="not supported"):
        tax_config.get_config("2020/21")


def test_supported_tax_years_includes_both():
    """Both 2025/26 and 2026/27 are in SUPPORTED_TAX_YEARS."""
    assert "2025/26" in tax_config.SUPPORTED_TAX_YEARS
    assert "2026/27" in tax_config.SUPPORTED_TAX_YEARS


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  2. Income tax and NI — identical in both years (frozen bands)             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_income_tax_identical_both_years():
    """Income-tax result is the same in 2025/26 and 2026/27.

    Employment=£40,000  invoice=£10,000 (no SL, no pension).
    start=40,000  end=50,000  IT = 20%×10,000 = £2,000.00
    """
    profile = {"day_job_salary": "40000", "ytd_freelance_profit": "0",
               "personal_pension_contributions": "0"}
    r25 = estimate_incremental_liability("10000", profile, tax_year="2025/26")
    r26 = estimate_incremental_liability("10000", profile, tax_year="2026/27")
    assert r25["income_tax"] == r26["income_tax"] == D("2000.00")


def test_ni_identical_both_years():
    """Class 4 NI result is the same in 2025/26 and 2026/27.

    Invoice=£30,000 from £0 start.
    main = 30,000 − 12,570 = 17,430 → 6%×17,430 = £1,045.80
    """
    r25 = _run("30000", tax_year="2025/26")
    r26 = _run("30000", tax_year="2026/27")
    assert r25["national_insurance"] == r26["national_insurance"] == D("1045.80")


def test_income_tax_identical_both_years_higher_rate():
    """Higher-rate IT also identical — bands are frozen.

    Employment=£60,000, invoice=£10,000.
    IT = 40%×10,000 = £4,000.00
    """
    profile = {"day_job_salary": "60000", "ytd_freelance_profit": "0",
               "personal_pension_contributions": "0"}
    r25 = estimate_incremental_liability("10000", profile, tax_year="2025/26")
    r26 = estimate_incremental_liability("10000", profile, tax_year="2026/27")
    assert r25["income_tax"] == r26["income_tax"] == D("4000.00")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  3. Student-loan thresholds differ between years                           ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_sl_plan1_higher_repayment_in_2025_26():
    """Plan 1: 2025/26 threshold £24,990 < 2026/27 threshold £26,900.

    Income = £28,000 (invoice from £0).

    2025/26: chargeable = 3,010 → 9% = £270.90 → £270 annual liability
    2026/27: chargeable = 28,000 − 26,900 = 1,100 → 9%×1,100 = £99.00
    """
    profile = {**_ZERO, "student_loan_plans": [1]}
    r25 = estimate_incremental_liability("28000", profile, tax_year="2025/26")
    r26 = estimate_incremental_liability("28000", profile, tax_year="2026/27")
    assert r25["student_loan"] == D("270.00"), r25["student_loan"]
    assert r26["student_loan"] == D("99.00"),  r26["student_loan"]
    assert r25["student_loan"] > r26["student_loan"]


def test_sl_plan2_higher_repayment_in_2025_26():
    """Plan 2: 2025/26 threshold £28,470 < 2026/27 threshold £29,385.

    Income = £30,000 (invoice from £0).

    2025/26: 9%×1,530 = £137.70 → £137 annual liability
    2026/27: 9%×615 = £55.35 → £55 annual liability
    """
    profile = {**_ZERO, "student_loan_plans": [2]}
    r25 = estimate_incremental_liability("30000", profile, tax_year="2025/26")
    r26 = estimate_incremental_liability("30000", profile, tax_year="2026/27")
    assert r25["student_loan"] == D("137.00"), r25["student_loan"]
    assert r26["student_loan"] == D("55.00"),  r26["student_loan"]


def test_sl_plan4_higher_repayment_in_2025_26():
    """Plan 4: 2025/26 threshold £32,745 < 2026/27 threshold £33,795.

    Income = £36,000 (invoice from £0).

    2025/26: chargeable = 36,000 − 32,745 = 3,255 → 9%×3,255 = £292.95
    2026/27: chargeable = 36,000 − 33,795 = 2,205 → 9%×2,205 = £198.45
    """
    profile = {**_ZERO, "student_loan_plans": [4]}
    r25 = estimate_incremental_liability("36000", profile, tax_year="2025/26")
    r26 = estimate_incremental_liability("36000", profile, tax_year="2026/27")
    assert r25["student_loan"] == D("292.00"), r25["student_loan"]
    assert r26["student_loan"] == D("198.00"), r26["student_loan"]


def test_sl_plan5_unchanged_both_years():
    """Plan 5: threshold £25,000 fixed by statute — identical in both years.

    Income = £30,000 → chargeable = 5,000 → 9%×5,000 = £450.00
    """
    profile = {**_ZERO, "student_loan_plans": [5]}
    r25 = estimate_incremental_liability("30000", profile, tax_year="2025/26")
    r26 = estimate_incremental_liability("30000", profile, tax_year="2026/27")
    assert r25["student_loan"] == r26["student_loan"] == D("450.00")


def test_sl_pgl_unchanged_both_years():
    """Postgraduate Loan: threshold £21,000 fixed by statute — identical.

    Income = £25,000 → chargeable = 4,000 → 6%×4,000 = £240.00
    """
    profile = {**_ZERO, "student_loan_plans": ["postgraduate"]}
    r25 = estimate_incremental_liability("25000", profile, tax_year="2025/26")
    r26 = estimate_incremental_liability("25000", profile, tax_year="2026/27")
    assert r25["student_loan"] == r26["student_loan"] == D("240.00")


def test_sl_plan1_income_between_thresholds_triggers_only_in_2025_26():
    """Income of £26,000 is above 2025/26 Plan 1 threshold (£24,990) but
    below 2026/27 threshold (£26,900).

    2025/26: chargeable = 26,000 − 24,990 = 1,010 → 9%×1,010 = £90.90
    2026/27: chargeable = max(0, 26,000 − 26,900) = 0 → £0.00
    """
    profile = {**_ZERO, "student_loan_plans": [1]}
    r25 = estimate_incremental_liability("26000", profile, tax_year="2025/26")
    r26 = estimate_incremental_liability("26000", profile, tax_year="2026/27")
    assert r25["student_loan"] == D("90.00"), r25["student_loan"]
    assert r26["student_loan"] == D("0.00"),  r26["student_loan"]


def test_sl_plan2_income_between_thresholds_triggers_only_in_2025_26():
    """Income of £29,000 is above 2025/26 Plan 2 threshold (£28,470) but
    below 2026/27 threshold (£29,385).

    2025/26: chargeable = 29,000 − 28,470 = 530 → 9%×530 = £47.70
    2026/27: chargeable = max(0, 29,000 − 29,385) = 0 → £0.00
    """
    profile = {**_ZERO, "student_loan_plans": [2]}
    r25 = estimate_incremental_liability("9990", profile, tax_year="2025/26")
    r26 = estimate_incremental_liability("9990", profile, tax_year="2026/27")
    assert r25["student_loan"] == D("47.00"), r25["student_loan"]
    assert r26["student_loan"] == D("0.00"),  r26["student_loan"]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  4. End-to-end totals differ only by student-loan delta                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_total_difference_equals_student_loan_delta_plan2():
    """For a Plan 2 borrower, total(2025/26) − total(2026/27) = SL delta.

    IT and NI are identical in both years; the only difference is SL.

    Invoice = £30,000 from £0 start, Plan 2.

    IT = 20%×(30,000−12,570) = 20%×17,430 = £3,486.00  (same both years)
    NI = 6%×17,430 = £1,045.80                          (same both years)
    SL 2025/26 = £137.70    total 2025/26 = £4,669.50
    SL 2026/27 = £55.35     total 2026/27 = £4,587.15
    """
    profile = {**_ZERO, "student_loan_plans": [2]}
    r25 = estimate_incremental_liability("30000", profile, tax_year="2025/26")
    r26 = estimate_incremental_liability("30000", profile, tax_year="2026/27")

    assert r25["income_tax"]         == r26["income_tax"]         == D("3486.00")
    assert r25["national_insurance"] == r26["national_insurance"] == D("1045.80")

    assert r25["total"] == D("4668.80"), r25["total"]
    assert r26["total"] == D("4586.80"), r26["total"]

    sl_delta = r25["student_loan"] - r26["student_loan"]
    total_delta = r25["total"] - r26["total"]
    assert total_delta == sl_delta


def test_gabriel_profile_same_both_years():
    """Gabriel (Plan 2, employment £40k, YTD £15k) gives identical totals.

    At start_income = £55,000 he is already above both years' Plan 2
    thresholds (£28,470 and £29,385), so threshold differences don't matter.
    Both years: total = £5,446.00.
    """
    gabriel = {
        "day_job_salary": "40000",
        "ytd_freelance_profit": "15000",
        "personal_pension_contributions": "5000",
        "student_loan_plans": [2],
    }
    r25 = estimate_incremental_liability("10000", gabriel, tax_year="2025/26")
    r26 = estimate_incremental_liability("10000", gabriel, tax_year="2026/27")
    assert r25["total"] == r26["total"] == D("5446.00")
