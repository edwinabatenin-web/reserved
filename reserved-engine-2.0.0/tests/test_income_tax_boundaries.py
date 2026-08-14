"""
Income-tax engine — boundary and precision tests for 2026/27.

Every assertion is computed from first principles against HMRC 2026/27
published thresholds.  Tests are grouped into six sections:

  A. Income-tax band boundaries
  B. Class 4 NI band boundaries
  C. Personal Allowance taper boundaries
  D. Student-loan threshold boundaries (2026/27)
  E. Rounding (ROUND_HALF_UP correctness)
  F. Composite / regression scenarios

Thresholds used (2026/27, frozen)
----------------------------------
  PA   £12,570   |  LPL  £12,570
  BRL  £50,270   |  UPL  £50,270
  ART  £125,140  |  main NI 6 %  |  upper NI 2 %

Student-loan thresholds (2026/27)
----------------------------------
  Plan 1  £26,900   Plan 2  £29,385   Plan 4  £33,795
  Plan 5  £25,000   PGL     £21,000
"""
from decimal import Decimal

import pytest

from reserved_engine.income_tax import estimate_incremental_liability

pytestmark = pytest.mark.engine


def D(s: str) -> Decimal:
    return Decimal(s)


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  A. Income-tax band boundaries                                             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# Unless stated otherwise: employment=0, YTD=0, pension=0, no student loan.
_ZERO = {"day_job_salary": "0", "ytd_freelance_profit": "0",
         "personal_pension_contributions": "0"}


def test_it_invoice_entirely_within_pa():
    """£5,000 first invoice — all below PA (£12,570) — no tax."""
    r = estimate_incremental_liability("5000", _ZERO)
    assert r["income_tax"]         == D("0.00")
    assert r["national_insurance"] == D("0.00")
    assert r["total"]              == D("0.00")


def test_it_invoice_exactly_fills_pa():
    """Invoice = £12,570 — income reaches but does not exceed PA.  Zero tax."""
    r = estimate_incremental_liability("12570", _ZERO)
    assert r["income_tax"]         == D("0.00")
    assert r["national_insurance"] == D("0.00")
    assert r["total"]              == D("0.00")


def test_it_first_taxable_pound_income_and_ni():
    """Invoice = £12,571 — one pound above PA.

    Income tax:  20 % × £1.00 = £0.20
    Class 4 NI:  freelance 0 → 12,571; main slice = 12,571 − 12,570 = 1
                 6 % × £1.00 = £0.06
    Total = £0.26
    """
    r = estimate_incremental_liability("12571", _ZERO)
    assert r["income_tax"]         == D("0.20"), r["income_tax"]
    assert r["national_insurance"] == D("0.06"), r["national_insurance"]
    assert r["total"]              == D("0.26"), r["total"]


def test_it_entirely_in_basic_rate_band():
    """Invoice within the basic-rate band, no band crossing.

    start=20,000  end=30,000  (employment=20,000, YTD=0)
    IT = 20 % × 10,000 = £2,000.00
    NI: freelance 0→10,000 all below LPL → £0.00
    """
    profile = {"day_job_salary": "20000", "ytd_freelance_profit": "0",
               "personal_pension_contributions": "0"}
    r = estimate_incremental_liability("10000", profile)
    assert r["income_tax"]         == D("2000.00"), r["income_tax"]
    assert r["national_insurance"] == D("0.00")
    assert r["total"]              == D("2000.00")


def test_it_invoice_exactly_fills_basic_rate_band():
    """Invoice takes income from PA ceiling to BRL exactly.

    YTD freelance = £12,570 (at PA ceiling).  Invoice = £37,700.
    end = £50,270 = BRL exactly.

    IT:  20 % × 37,700 = £7,540.00
    NI:  freelance 12,570 → 50,270; main = 37,700 → 6 % × 37,700 = £2,262.00
    """
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "12570",
               "personal_pension_contributions": "0"}
    r = estimate_incremental_liability("37700", profile)
    assert r["income_tax"]         == D("7540.00"), r["income_tax"]
    assert r["national_insurance"] == D("2262.00"), r["national_insurance"]
    assert r["total"]              == D("9802.00"), r["total"]


def test_it_first_penny_in_higher_rate_band():
    """Invoice of £1 with YTD=£50,270 — first higher-rate penny.

    IT:  40 % × £1.00 = £0.40
    NI:  freelance 50,270 → 50,271; upper slice = 1 → 2 % × 1 = £0.02
    """
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "50270",
               "personal_pension_contributions": "0"}
    r = estimate_incremental_liability("1", profile)
    assert r["income_tax"]         == D("0.40"), r["income_tax"]
    assert r["national_insurance"] == D("0.02"), r["national_insurance"]
    assert r["total"]              == D("0.42")


def test_it_entirely_in_higher_rate_band():
    """Employment=£60,000 (above BRL), freelance invoice = £10,000.

    IT = 40 % × 10,000 = £4,000.00
    NI: freelance 0→10,000, all below LPL → £0.00
    """
    profile = {"day_job_salary": "60000", "ytd_freelance_profit": "0",
               "personal_pension_contributions": "0"}
    r = estimate_incremental_liability("10000", profile)
    assert r["income_tax"]         == D("4000.00"), r["income_tax"]
    assert r["national_insurance"] == D("0.00")
    assert r["total"]              == D("4000.00")


def test_it_invoice_crossing_brl():
    """Invoice straddles the BRL (£50,270) boundary.

    YTD freelance = £45,000.  Invoice = £10,000.
    start=45,000  end=55,000  BRL=50,270

    IT:  20 % × (50,270−45,000) + 40 % × (55,000−50,270)
       = 20 % × 5,270 + 40 % × 4,730
       = 1,054.00 + 1,892.00 = £2,946.00

    NI (freelance 45,000 → 55,000):
      main:  min(55,000,50,270) − max(45,000,12,570) = 50,270−45,000 = 5,270 → £316.20
      upper: max(0, 55,000−50,270) = 4,730 → 2 % × 4,730 = £94.60
      NI = £410.80

    Total = £3,356.80
    """
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "45000",
               "personal_pension_contributions": "0"}
    r = estimate_incremental_liability("10000", profile)
    assert r["income_tax"]         == D("2946.00"), r["income_tax"]
    assert r["national_insurance"] == D("410.80"), r["national_insurance"]
    assert r["total"]              == D("3356.80"), r["total"]


def test_it_invoice_crossing_art():
    """Invoice straddles the Additional Rate Threshold (£125,140).

    YTD freelance = £120,000.  Invoice = £10,000.
    start=120,000  end=130,000

    ANI(start) = 120,000 → PA = 12,570 − (120,000−100,000)/2 = 2,570  (taper zone)
    ANI(end)   = 130,000 → PA = 0

    True marginal = total_tax(130,000) − total_tax(120,000)

    total_tax(130,000): ANI=130,000 → PA=0
      IT = 50,270×20% + 74,870×40% + (130,000−125,140)×45%
         = 10,054 + 29,948 + 4,860×0.45 = 10,054 + 29,948 + 2,187 = £42,189.00

    total_tax(120,000): ANI=120,000 → PA=2,570
      IT = (50,270−2,570)×20% + (120,000−50,270)×40%
         = 47,700×0.20 + 69,730×0.40 = 9,540 + 27,892 = £37,432.00

    Marginal IT = 42,189 − 37,432 = £4,757.00
      (extra £514 vs v1.x: the 2,570 of PA lost at start now taxes at 20%)

    NI (freelance 120,000 → 130,000, both above UPL):
      upper = 10,000 → 2 % × 10,000 = £200.00

    Total = £4,957.00
    """
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "120000",
               "personal_pension_contributions": "0"}
    r = estimate_incremental_liability("10000", profile)
    assert r["income_tax"]         == D("4757.00"), r["income_tax"]
    assert r["national_insurance"] == D("200.00"),  r["national_insurance"]
    assert r["total"]              == D("4957.00"), r["total"]


def test_it_first_penny_in_additional_rate_band():
    """Invoice of £1 with YTD=£125,140 — first additional-rate penny.

    ANI = 125,141 → PA = max(0, 12,570 − (125,141−100,000)/2) = 0
    IT  = 45 % × 1 = £0.45
    NI (upper) = 2 % × 1 = £0.02
    """
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "125140",
               "personal_pension_contributions": "0"}
    r = estimate_incremental_liability("1", profile)
    assert r["income_tax"]         == D("0.45"), r["income_tax"]
    assert r["national_insurance"] == D("0.02"), r["national_insurance"]
    assert r["total"]              == D("0.47")


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  B. Class 4 NI band boundaries                                             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_ni_freelance_exactly_at_lpl():
    """Freelance profit 0 → £12,570 exactly — main-band slice = 0.

    NI = £0.00  (LPL = £12,570; endpoint is not above it)
    """
    r = estimate_incremental_liability("12570", _ZERO)
    assert r["national_insurance"] == D("0.00")


def test_ni_small_amount_above_lpl():
    """Freelance profit £12,570 → £12,670 — first £100 in the main band.

    main slice = 100 → 6 % × 100 = £6.00
    """
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "12570",
               "personal_pension_contributions": "0"}
    r = estimate_incremental_liability("100", profile)
    assert r["national_insurance"] == D("6.00"), r["national_insurance"]


def test_ni_fills_main_band_exactly():
    """Freelance profit £12,570 → £50,270 — entire main band, nothing above.

    main = 50,270 − 12,570 = 37,700 → 6 % × 37,700 = £2,262.00
    upper = 0
    """
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "12570",
               "personal_pension_contributions": "0"}
    r = estimate_incremental_liability("37700", profile)
    assert r["national_insurance"] == D("2262.00"), r["national_insurance"]


def test_ni_one_penny_into_upper_band():
    """Freelance profit £50,270 → £50,271 — first upper-band penny.

    main  slice = min(50,271, 50,270) − max(50,270, 12,570) = 0
    upper slice = 50,271 − 50,270 = 1 → 2 % × 1 = £0.02
    """
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "50270",
               "personal_pension_contributions": "0"}
    r = estimate_incremental_liability("1", profile)
    assert r["national_insurance"] == D("0.02"), r["national_insurance"]


def test_ni_all_in_upper_band():
    """Freelance profit £50,270 → £60,270 — entirely in upper band.

    upper = 10,000 → 2 % × 10,000 = £200.00
    """
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "50270",
               "personal_pension_contributions": "0"}
    r = estimate_incremental_liability("10000", profile)
    assert r["national_insurance"] == D("200.00"), r["national_insurance"]


def test_ni_crosses_both_lpl_and_upl():
    """Single invoice takes freelance from £0 to £60,000, crossing both limits.

    main  = min(60,000, 50,270) − max(0, 12,570) = 50,270 − 12,570 = 37,700
          → 6 % × 37,700 = £2,262.00
    upper = max(0, 60,000 − 50,270) = 9,730
          → 2 % × 9,730  = £194.60
    NI = £2,456.60
    """
    r = estimate_incremental_liability("60000", _ZERO)
    assert r["national_insurance"] == D("2456.60"), r["national_insurance"]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  C. Personal Allowance taper boundaries                                    ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_pa_full_at_exactly_taper_start():
    """Invoice takes ANI to exactly £100,000 — full PA retained.

    ANI = 100,000 = taper start → PA = £12,570 (no reduction).
    IT = 0%×12,570 + 20%×37,700 + 40%×49,730
       = 0 + 7,540 + 19,892 = £27,432.00
    NI = 6%×37,700 + 2%×49,730 = 2,262 + 994.60 = £3,256.60
    """
    r = estimate_incremental_liability("100000", _ZERO)
    assert r["income_tax"]         == D("27432.00"), r["income_tax"]
    assert r["national_insurance"] == D("3256.60"),  r["national_insurance"]
    assert r["total"]              == D("30688.60"), r["total"]


def test_pa_starts_tapering_one_above_threshold():
    """Invoice takes ANI to £100,001 — PA reduced by £0.50 to £12,569.50.

    IT = 0%×12,569.50 + 20%×37,700.50 + 40%×49,731
       = 0 + 7,540.10 + 19,892.40 = £27,432.50
    NI = 6%×37,700 + 2%×49,731 = 2,262.00 + 994.62 = £3,256.62
    Total = £30,689.12
    """
    r = estimate_incremental_liability("100001", _ZERO)
    assert r["income_tax"]         == D("27432.50"), r["income_tax"]
    assert r["national_insurance"] == D("3256.62"),  r["national_insurance"]
    assert r["total"]              == D("30689.12"), r["total"]


def test_pa_fully_tapered_at_art():
    """Invoice takes ANI to exactly £125,140 — PA = 0.

    reduction = (125,140 − 100,000) / 2 = 12,570 → PA = 12,570 − 12,570 = 0.
    IT = 0 + 20%×50,270 + 40%×74,870
       = 10,054 + 29,948 = £40,002.00
    NI = 6%×37,700 + 2%×74,870 = 2,262 + 1,497.40 = £3,759.40
    Total = £43,761.40
    """
    r = estimate_incremental_liability("125140", _ZERO)
    assert r["income_tax"]         == D("40002.00"), r["income_tax"]
    assert r["national_insurance"] == D("3759.40"),  r["national_insurance"]
    assert r["total"]              == D("43761.40"), r["total"]


def test_pa_taper_midpoint_partial_reduction():
    """Invoice takes ANI to £112,570 — PA reduced to £6,285.

    ANI = 112,570; reduction = (112,570 − 100,000) / 2 = 6,285; PA = 6,285.
    IT = 0%×6,285 + 20%×(50,270−6,285) + 40%×(112,570−50,270)
       = 0 + 20%×43,985 + 40%×62,300
       = 8,797.00 + 24,920.00 = £33,717.00
    NI (freelance 0→112,570):
      main  = 50,270 − 12,570 = 37,700 → 6%×37,700 = 2,262.00
      upper = 112,570 − 50,270 = 62,300 → 2%×62,300 = 1,246.00
      NI = £3,508.00
    Total = £37,225.00
    """
    r = estimate_incremental_liability("112570", _ZERO)
    assert r["income_tax"]         == D("33717.00"), r["income_tax"]
    assert r["national_insurance"] == D("3508.00"),  r["national_insurance"]
    assert r["total"]              == D("37225.00"), r["total"]


def test_pa_taper_el001_resolved_crosses_taper_start():
    """EL-001 resolved (v2.0.0): correct result when invoice crosses PA taper start.

    Profile: YTD freelance = £99,000.  Invoice = £4,000.
    Income range: 99,000 → 103,000 (crosses taper-start at £100,000).

    True marginal = total_tax(103,000) − total_tax(99,000)

    total_tax(103,000): ANI=103,000 → PA = 12,570 − 1,500 = £11,070
      IT = (50,270−11,070)×20% + (103,000−50,270)×40%
         = 39,200×0.20 + 52,730×0.40 = 7,840 + 21,092 = £28,932.00

    total_tax(99,000): ANI=99,000 < 100,000 → PA = £12,570
      IT = (50,270−12,570)×20% + (99,000−50,270)×40%
         = 37,700×0.20 + 48,730×0.40 = 7,540 + 19,492 = £27,032.00

    Marginal IT = 28,932 − 27,032 = £1,900.00

    (v1.0.0 EL-001 result was £1,600.00 — £300 underestimate)
    """
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "99000",
               "personal_pension_contributions": "0"}
    r = estimate_incremental_liability("4000", profile)
    assert r["income_tax"] == D("1900.00"), (
        f"EL-001 regression: expected £1900.00 (correct differential), "
        f"got {r['income_tax']}"
    )
    # NI: freelance 99,000→103,000 both above UPL → upper 2%×4,000=£80.00
    assert r["national_insurance"] == D("80.00"), r["national_insurance"]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  D. Student-loan threshold boundaries (2026/27)                            ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

@pytest.mark.parametrize("plan,threshold", [
    (1,              "26900"),
    (2,              "29385"),
    (4,              "33795"),
    (5,              "25000"),
    ("postgraduate", "21000"),
])
def test_sl_zero_repayment_when_income_exactly_at_threshold(plan, threshold):
    """No repayment when end income equals the plan threshold exactly.

    chargeable = max(0, threshold − max(start=0, threshold)) = 0
    """
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "0",
               "personal_pension_contributions": "0",
               "student_loan_plans": [plan]}
    r = estimate_incremental_liability(threshold, profile)
    assert r["student_loan"] == Decimal("0.00"), (plan, r["student_loan"])


@pytest.mark.parametrize("plan,threshold,rate", [
    (1,              26900, "0.09"),
    (2,              29385, "0.09"),
    (4,              33795, "0.09"),
    (5,              25000, "0.09"),
    ("postgraduate", 21000, "0.06"),
])
def test_sl_one_pound_above_threshold_pays_correct_rate(plan, threshold, rate):
    """£1 above threshold → SL = rate × £1.

    start = threshold (YTD), invoice = 1 → end = threshold + 1
    chargeable = max(0, (threshold+1) − max(threshold, threshold)) = 1
    SL = rate × 1.00
    """
    profile = {"day_job_salary": "0",
               "ytd_freelance_profit": str(threshold),
               "personal_pension_contributions": "0",
               "student_loan_plans": [plan]}
    expected = Decimal(rate).quantize(Decimal("0.01"))
    r = estimate_incremental_liability("1", profile)
    assert r["student_loan"] == expected, (plan, r["student_loan"])


def test_sl_plan4_income_below_2026_27_threshold_zero():
    """Income £33,000 is below Plan 4's 2026/27 threshold (£33,795) → £0.

    Distinguishes from 2025/26 where threshold is £32,745 and SL would be £22.95.
    """
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "0",
               "personal_pension_contributions": "0",
               "student_loan_plans": [4]}
    r = estimate_incremental_liability("33000", profile)
    assert r["student_loan"] == D("0.00"), r["student_loan"]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  E. Rounding — ROUND_HALF_UP correctness                                  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_rounding_half_up_not_half_even_income_tax():
    """45 % × £0.50 = £0.225 → ROUND_HALF_UP → £0.23 (not £0.22).

    ROUND_HALF_EVEN (banker's rounding) would give £0.22 since the digit
    before the 5 is 2 (even).  Reserved uses ROUND_HALF_UP throughout.

    Profile: YTD=£125,140 (above ART) → all income in the 45 % band.
    invoice=£0.50 (a whole-penny amount) → 45%×0.50 = 0.2250 exactly.

    Note: invoices with sub-penny amounts (e.g. "4.6125") are rounded to
    2 d.p. by money() *before* multiplication, so they cannot generate a
    mid-point product.  The 45%×0.50 case is the canonical ROUND_HALF_UP
    demonstration with whole-penny inputs.
    """
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "125140",
               "personal_pension_contributions": "0"}
    r = estimate_incremental_liability("0.50", profile)
    assert r["income_tax"] == D("0.23"), (
        f"ROUND_HALF_UP expected £0.23, got {r['income_tax']}. "
        "Check utils.money() uses ROUND_HALF_UP, not ROUND_HALF_EVEN."
    )


def test_rounding_half_up_not_half_even_ni():
    """6 % × £16.75 = £1.005 → ROUND_HALF_UP → £1.01 (not £1.00).

    ROUND_HALF_EVEN would give £1.00 (digit before 5 is 0 = even).
    """
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "12570",
               "personal_pension_contributions": "0"}
    r = estimate_incremental_liability("16.75", profile)
    assert r["national_insurance"] == D("1.01"), (
        f"ROUND_HALF_UP expected £1.01, got {r['national_insurance']}. "
        "Check utils.money() uses ROUND_HALF_UP, not ROUND_HALF_EVEN."
    )


def test_total_exactly_equals_sum_of_components():
    """``total`` must equal income_tax + national_insurance + student_loan.

    Uses a multi-component scenario (all three taxes non-zero) to verify there
    is no rounding accumulation in the total field.
    """
    profile = {
        "day_job_salary": "40000",
        "ytd_freelance_profit": "15000",
        "personal_pension_contributions": "5000",
        "student_loan_plans": [2],
    }
    r = estimate_incremental_liability("10000", profile)
    component_sum = r["income_tax"] + r["national_insurance"] + r["student_loan"]
    assert r["total"] == component_sum, (
        f"total={r['total']} but components sum to {component_sum}"
    )


def test_fractional_invoice_produces_correct_rounding():
    """Invoice £3,333.33 in the basic-rate band.

    20 % × £3,333.33 = £666.666 → ROUND_HALF_UP → £666.67
    NI: freelance 0→3,333.33 all below LPL → £0.00
    """
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "0",
               "personal_pension_contributions": "0"}
    r = estimate_incremental_liability("3333.33", profile)
    # 3333.33 < 12570 (PA) → IT = 0
    assert r["income_tax"]         == D("0.00")
    assert r["national_insurance"] == D("0.00")

    # With start above PA so IT is in basic rate:
    profile2 = {"day_job_salary": "15000", "ytd_freelance_profit": "0",
                "personal_pension_contributions": "0"}
    r2 = estimate_incremental_liability("3333.33", profile2)
    # 20% × 3333.33 = 666.666 → £666.67
    assert r2["income_tax"] == D("666.67"), r2["income_tax"]


# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  F. Composite / regression scenarios                                       ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

def test_regression_plan5_above_brl_all_three_taxes():
    """Comprehensive test: IT crosses BRL, NI crosses UPL, Plan 5 SL.

    YTD freelance = £45,000.  Invoice = £10,000.  Plan 5 (threshold £25,000).
    start=45,000  end=55,000  ANI=55,000  PA=12,570  BRL=50,270

    IT: 20%×5,270 + 40%×4,730 = 1,054 + 1,892 = £2,946.00
    NI: main 6%×5,270=316.20 ; upper 2%×4,730=94.60 → £410.80
    SL: 9%×(55,000−max(45,000,25,000))=9%×10,000 = £900.00
    Total = £4,256.80
    """
    profile = {"day_job_salary": "0", "ytd_freelance_profit": "45000",
               "personal_pension_contributions": "0",
               "student_loan_plans": [5]}
    r = estimate_incremental_liability("10000", profile)
    assert r["income_tax"]         == D("2946.00"), r["income_tax"]
    assert r["national_insurance"] == D("410.80"),  r["national_insurance"]
    assert r["student_loan"]       == D("900.00"),  r["student_loan"]
    assert r["total"]              == D("4256.80"), r["total"]


def test_regression_high_earner_additional_rate_with_ni():
    """Very high earner: employment=£200,000, invoice=£20,000.

    ANI = 220,000 > 125,140 → PA = 0.  All income in additional-rate band.

    IT: 45 % × 20,000 = £9,000.00
    NI: freelance 0 → 20,000
      main = min(20,000, 50,270) − max(0, 12,570) = 20,000 − 12,570 = 7,430
      6 % × 7,430 = £445.80   (upper slice = 0, end < UPL)
    Total = £9,445.80
    """
    profile = {"day_job_salary": "200000", "ytd_freelance_profit": "0",
               "personal_pension_contributions": "0"}
    r = estimate_incremental_liability("20000", profile)
    assert r["income_tax"]         == D("9000.00"), r["income_tax"]
    assert r["national_insurance"] == D("445.80"),  r["national_insurance"]
    assert r["total"]              == D("9445.80"), r["total"]


def test_regression_pension_saves_at_higher_rate_boundary():
    """Pension (RaS) keeps an invoice in the basic-rate band.

    Without pension (YTD=£45,000, invoice=£10,000, end=£55,000):
      IT = 20%×5,270 + 40%×4,730 = £2,946.00

    With pension gross=£6,000 (extBRL = 56,270):
      IT = 20%×(55,000−45,000) = 20%×10,000 = £2,000.00
      Saving = £946.00
    """
    base = {"day_job_salary": "0", "ytd_freelance_profit": "45000",
            "personal_pension_contributions": "0"}
    with_pension = {**base, "personal_pension_contributions": "6000"}

    no_p = estimate_incremental_liability("10000", base)
    w_p  = estimate_incremental_liability("10000", with_pension)

    assert no_p["income_tax"] == D("2946.00"), no_p["income_tax"]
    assert w_p["income_tax"]  == D("2000.00"), w_p["income_tax"]
    assert no_p["income_tax"] - w_p["income_tax"] == D("946.00")


def test_regression_zero_income_start():
    """First invoice of a tax year from a clean £0 start — no prior income."""
    r = estimate_incremental_liability("5000", {})
    assert r["income_tax"]         == D("0.00")
    assert r["national_insurance"] == D("0.00")
    assert r["student_loan"]       == D("0.00")
    assert r["total"]              == D("0.00")
    assert r["tax_year"]           == "2026/27"


def test_all_monetary_results_are_decimal_two_dp():
    """All monetary output values must be Decimal and quantized to 2 d.p."""
    profile = {"day_job_salary": "33333", "ytd_freelance_profit": "7777",
               "personal_pension_contributions": "1111",
               "student_loan_plans": [1, "postgraduate"]}
    r = estimate_incremental_liability("9999.99", profile)
    for key in ("income_tax", "national_insurance", "student_loan", "total"):
        val = r[key]
        assert isinstance(val, Decimal), f"{key} is {type(val)}, expected Decimal"
        assert val == val.quantize(Decimal("0.01")), f"{key}={val} is not 2 d.p."
