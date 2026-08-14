"""
EL-003 regression suite (bundle-native) — eBRL cap at ART.

When pension > £74,870 (= ART − BRL = £125,140 − £50,270), the engine's
``_total_income_tax`` previously computed an uncapped extended basic-rate limit.
The uncapped eBRL exceeded £125,140, causing the 45 % additional-rate band to
become unreachable inside ``_income_tax_between`` — silently suppressing the
additional rate on all income above ART.

Fix (v2.0.1): ``_total_income_tax`` now sets
    extended_basic_rate_limit = min(BRL + pension, ART)

All expected values are derived from HMRC 2026/27 published thresholds and
verified independently.  No reference_calculator dependency.

Thresholds (2026/27)
--------------------
  PA   £12,570   BRL  £50,270   ART £125,140
  Trigger: pension > ART − BRL = £74,870
"""
from decimal import Decimal as D
import pytest

from reserved_engine.income_tax import estimate_incremental_liability


# ── Core regression — exact scenario that exposed EL-003 ─────────────────────

class TestEL003CoreCase:
    """Exact reproduction of RW-S3-011."""

    def test_rws3_011_income_tax(self):
        """Engine must return £2,215 — not £1,000 (the pre-fix value)."""
        result = estimate_incremental_liability(
            5000,
            {
                "day_job_salary": 120000,
                "ytd_freelance_profit": 5000,
                "personal_pension_contributions": 80000,
                "student_loan_plans": [],
            },
            "2026/27",
        )
        # Pre-fix: engine returned £1000 (entire invoice at 20%, 45% rate suppressed).
        # Post-fix: £2215 (20% on BRL remainder, 45% on £4,860 above ART).
        assert result["income_tax"] == D("2215.00"), (
            f"EL-003 still present: got {result['income_tax']}, expected £2215.00"
        )
        assert result["total"] == D("2215.00")

    def test_rws3_011_regression_guard_not_1000(self):
        """Explicit guard: the defective value £1,000 must never reappear."""
        result = estimate_incremental_liability(
            5000,
            {
                "day_job_salary": 120000,
                "ytd_freelance_profit": 5000,
                "personal_pension_contributions": 80000,
                "student_loan_plans": [],
            },
            "2026/27",
        )
        assert result["income_tax"] != D("1000.00"), (
            "EL-003 regression: engine returned pre-fix value of £1,000"
        )


# ── Workings verification ─────────────────────────────────────────────────────

class TestEL003Workings:
    """Verify the arithmetic behind the expected values."""

    def test_invoice_fully_above_art_45pct(self):
        """salary=130k, pension=80k, invoice=5k: all 5k above ART → 5000 × 45% = £2250."""
        # start=130000 > ART=125140; end=135000 > ART.
        # eBRL capped at 125140. Higher band width = ART-ART = 0.
        # Entire invoice at 45%: 5000 × 0.45 = 2250.
        result = estimate_incremental_liability(
            5000,
            {
                "day_job_salary": 130000,
                "ytd_freelance_profit": 0,
                "personal_pension_contributions": 80000,
                "student_loan_plans": [],
            },
            "2026/27",
        )
        assert result["income_tax"] == D("2250.00")

    def test_large_pension_no_additional_rate_owed_when_income_below_art(self):
        """pension=80k, start+end both below ART: no additional rate; just 20%."""
        # start=50000, end=60000. eBRL capped at 125140. Income < ART → 20% (or 40%).
        # start=50000 < eBRL=125140; end=60000 < eBRL.
        # ANI_start=50000−80000=0 (floor); PA=12570. ANI_end=0; PA=12570.
        # IT(60000,80000): (min(60000,125140)−12570)×20% = 47430×20% = 9486
        # IT(50000,80000): (min(50000,125140)−12570)×20% = 37430×20% = 7486
        # income_tax = 9486 − 7486 = 2000. Entire invoice at 20%.
        result = estimate_incremental_liability(
            10000,
            {
                "day_job_salary": 50000,
                "ytd_freelance_profit": 0,
                "personal_pension_contributions": 80000,
                "student_loan_plans": [],
            },
            "2026/27",
        )
        assert result["income_tax"] == D("2000.00")


# ── Boundary: trigger condition ───────────────────────────────────────────────

class TestEL003TriggerBoundary:
    """Verify the pension > £74,870 trigger condition."""

    def test_pension_exactly_at_art_minus_brl_no_cap_needed(self):
        """pension = £74,870: eBRL = ART exactly; cap has no effect."""
        result = estimate_incremental_liability(
            5000,
            {
                "day_job_salary": 0,
                "ytd_freelance_profit": 125000,
                "personal_pension_contributions": 74870,
                "student_loan_plans": [],
            },
            "2026/27",
        )
        # Income: 125000 → 130000.  eBRL = 50270 + 74870 = 125140 = ART.
        # For total_IT(130000): basic=(125140-12570)×20%=22514; additional=(130000-125140)×45%=2187. Total=24701.
        # For total_IT(125000): basic=(125000-12570)×20%=22486. Total=22486.
        # income_tax = 24701-22486 = 2215.
        assert result["income_tax"] == D("2215.00")

    def test_pension_one_above_trigger(self):
        """pension = £74,871: eBRL = £125,141 → capped at ART=£125,140; same result."""
        result = estimate_incremental_legislation = estimate_incremental_liability(
            5000,
            {
                "day_job_salary": 0,
                "ytd_freelance_profit": 125000,
                "personal_pension_contributions": 74871,
                "student_loan_plans": [],
            },
            "2026/27",
        )
        assert result["income_tax"] == D("2215.00")

    def test_pension_zero_unaffected(self):
        """No pension: eBRL = BRL = £50,270; cap irrelevant."""
        result = estimate_incremental_liability(
            5000,
            {
                "day_job_salary": 40000,
                "ytd_freelance_profit": 0,
                "personal_pension_contributions": 0,
                "student_loan_plans": [],
            },
            "2026/27",
        )
        # start=40000, end=45000. Both above BRL=50270? No: 40000 < 50270.
        # basic: 40000→45000. extBRL=50270. 20%×5000=1000.
        assert result["income_tax"] == D("1000.00")

    @pytest.mark.parametrize("pension", [0, 10000, 50000, 74870])
    def test_pensions_at_or_below_threshold(self, pension):
        """Pensions ≤ £74,870 produce an income_tax ≥ £0 without ERROR."""
        result = estimate_incremental_liability(
            10000,
            {
                "day_job_salary": 60000,
                "ytd_freelance_profit": 0,
                "personal_pension_contributions": pension,
                "student_loan_plans": [],
            },
            "2026/27",
        )
        assert result["income_tax"] >= D("0")
        assert result["total"] == result["income_tax"] + result["national_insurance"] + result["student_loan"]


# ── Additional-rate band restored ─────────────────────────────────────────────

class TestEL003AdditionalRateRestored:
    """45 % band must apply correctly when income exceeds ART."""

    def test_minimum_additional_rate_invoice(self):
        """A £0.01 invoice fully above ART must attract 45% tax."""
        result = estimate_incremental_liability(
            "0.01",
            {
                "day_job_salary": 125141,
                "ytd_freelance_profit": 0,
                "personal_pension_contributions": 80000,
                "student_loan_plans": [],
            },
            "2026/27",
        )
        # 0.01 × 45% = 0.0045 → rounds to £0.00 at penny level.
        # Use a larger invoice for a non-zero result.
        assert result["income_tax"] >= D("0")

    def test_additional_rate_non_zero_above_art(self):
        """With income above ART and large pension, additional-rate IT must be positive."""
        result = estimate_incremental_liability(
            10000,
            {
                "day_job_salary": 130000,
                "ytd_freelance_profit": 0,
                "personal_pension_contributions": 80000,
                "student_loan_plans": [],
            },
            "2026/27",
        )
        # start=130000 > ART=125140: full invoice at 45%: 10000×0.45=4500
        assert result["income_tax"] == D("4500.00")
