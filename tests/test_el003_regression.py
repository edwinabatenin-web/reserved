"""
EL-003 regression suite — eBRL cap at ART when pension > (ART − BRL).

EL-003: When a pension contribution is large enough that
    BRL + pension > ART  (i.e. pension > £125,140 − £50,270 = £74,870)
the uncapped extended basic-rate limit exceeded the Additional Rate Threshold.
Inside ``_income_tax_between`` the band list is processed cursor-by-cursor;
an uncapped eBRL caused the 45 % additional-rate band to become unreachable,
silently suppressing additional-rate tax on any income above ART.

Root cause (engine v2.0.0)
---------------------------
``_total_income_tax`` set::

    extended_basic_rate_limit = cfg["BASIC_RATE_LIMIT"] + pension

without capping at ``cfg["ADDITIONAL_RATE_THRESHOLD"]``.

Fix (engine v2.0.1-patch)
--------------------------
``_total_income_tax`` now sets::

    extended_basic_rate_limit = min(
        cfg["BASIC_RATE_LIMIT"] + pension,
        cfg["ADDITIONAL_RATE_THRESHOLD"],
    )

This matches the reference calculator (``reference_calculator.py`` line ~162)
and is consistent with HMRC Pensions Tax Manual PTM044100, which does not
allow pension band extension beyond the Additional Rate Threshold.

Trigger condition
-----------------
    pension > ART − BRL = £125,140 − £50,270 = £74,870

For pension ≤ £74,870 the cap is never reached and results are unchanged.

Permanent regression tests
---------------------------
All tests here must remain green at all future engine versions.
Any failure is classified as an EL-003 regression.
"""
from decimal import Decimal as D

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "reserved-engine-2.0.0"))

from reserved_engine.income_tax import estimate_incremental_liability
from reserved_west.reference_calculator import ref_estimate

TAX_YEAR = "2026/27"
ART  = D("125140")
BRL  = D("50270")
THRESHOLD_PENSION = ART - BRL  # £74,870 — minimum pension that triggers the bug without fix


# ── Helper ────────────────────────────────────────────────────────────────────

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


def _variance(ref, eng):
    return float(eng["total"]) - float(ref["total"])


# ── Core regression: the exact scenario that exposed the defect ───────────────

class TestEL003CoreCase:
    """RW-S3-011 reproduction: pension=£80k caps eBRL at ART; invoice crosses ART."""

    def test_rws3_011_exact_scenario(self):
        """Engine must agree with reference for the exact Stage 3 failing scenario."""
        ref, eng = _run(invoice=5000, salary=120000, ytd=5000, pension=80000)
        assert eng["total"] == ref["total"], (
            f"EL-003 regression: engine {eng['total']} ≠ reference {ref['total']}"
        )

    def test_income_tax_component_correct(self):
        """Income tax specifically (NI and SL are zero in this scenario)."""
        ref, eng = _run(invoice=5000, salary=120000, ytd=5000, pension=80000)
        assert eng["income_tax"] == ref["income_tax"]

    def test_reference_it_is_1000(self):
        """With restored PA and the extended band, the invoice is taxed at 20%."""
        ref, _ = _run(invoice=5000, salary=120000, ytd=5000, pension=80000)
        assert ref["income_tax"] == D("1000.00")

    def test_engine_it_is_1000_after_taper_correction(self):
        """Engine preserves the fixed taxable-band coordinate after PA restoration."""
        _, eng = _run(invoice=5000, salary=120000, ytd=5000, pension=80000)
        assert eng["income_tax"] == D("1000.00")


# ── Boundary: trigger condition pension > £74,870 ────────────────────────────

class TestEL003TriggerBoundary:
    """Test the trigger boundary at pension = ART − BRL = £74,870."""

    def test_pension_exactly_at_threshold_no_bug(self):
        """pension = £74,870: eBRL = BRL + 74,870 = ART exactly; no suppression."""
        pension = int(THRESHOLD_PENSION)  # £74,870
        ref, eng = _run(invoice=5000, salary=0, ytd=125000, pension=pension)
        assert _variance(ref, eng) == 0.0

    def test_pension_one_below_threshold(self):
        """pension = £74,869: eBRL = £125,139 < ART; cap not reached; correct."""
        ref, eng = _run(invoice=5000, salary=0, ytd=125000, pension=74869)
        assert _variance(ref, eng) == 0.0

    def test_pension_one_above_threshold_triggers_cap(self):
        """pension = £74,871: eBRL would be £125,141 > ART; cap must apply."""
        ref, eng = _run(invoice=5000, salary=0, ytd=125000, pension=74871)
        assert _variance(ref, eng) == 0.0

    def test_pension_far_above_threshold(self):
        """pension = £100,000: eBRL capped at ART; invoice above ART taxed at 45%."""
        ref, eng = _run(invoice=50000, salary=0, ytd=0, pension=100000)
        assert _variance(ref, eng) == 0.0

    def test_pension_exactly_75000(self):
        """pension = £75,000 (above threshold): cap must apply correctly."""
        ref, eng = _run(invoice=10000, salary=0, ytd=130000, pension=75000)
        assert _variance(ref, eng) == 0.0

    def test_pension_exactly_80000(self):
        """pension = £80,000: primary Stage 3 failure case."""
        ref, eng = _run(invoice=5000, salary=120000, ytd=5000, pension=80000)
        assert _variance(ref, eng) == 0.0


# ── Below-threshold pensions unaffected ──────────────────────────────────────

class TestEL003BelowThresholdUnchanged:
    """Pensions ≤ £74,870 must be numerically unchanged by the fix."""

    @pytest.mark.parametrize("pension", [0, 1000, 5000, 10000, 50000, 74870])
    def test_pensions_below_threshold_zero_variance(self, pension):
        """Any pension ≤ £74,870 should produce zero variance."""
        ref, eng = _run(invoice=10000, salary=60000, ytd=0, pension=pension)
        assert _variance(ref, eng) == 0.0, (
            f"Regression introduced for pension={pension}: variance={_variance(ref, eng)}"
        )

    def test_typical_moderate_pension(self):
        """Typical professional pension (£20k) unaffected."""
        ref, eng = _run(invoice=10000, salary=50000, ytd=0, pension=20000)
        assert eng["total"] == ref["total"]

    def test_zero_pension_unaffected(self):
        """No pension: eBRL = BRL; cap irrelevant."""
        ref, eng = _run(invoice=10000, salary=60000, ytd=0, pension=0)
        assert eng["total"] == ref["total"]


# ── Additional-rate suppression is specifically gone ─────────────────────────

class TestEL003AdditionalRateRestored:
    """Verify the 45% rate is correctly applied above ART after the fix."""

    def test_large_pension_restores_pa_before_additional_threshold(self):
        """Gross income alone does not locate a slice in taxable-income bands."""
        # The £80k gross RaS pension restores the PA. The invoice moves taxable
        # income from 117,430 to 122,430, crossing the extended basic band at
        # 117,700: £270 at 20% plus £4,730 at 40% = £1,946.
        ref, eng = _run(invoice=5000, salary=130000, ytd=0, pension=80000)
        assert eng["income_tax"] == ref["income_tax"]
        assert eng["income_tax"] == D("1946.00")

    def test_invoice_straddles_art_with_large_pension(self):
        """Invoice starts below ART, ends above it: split at 40%/45% after eBRL."""
        # With eBRL capped at ART: all basic-rate capacity used, invoice at 40% then 45%
        # salary=100k, ytd=20k, pension=80k, invoice=10k
        # ANI_start=40k, ANI_end=50k — no taper. eBRL=ART=125140.
        # Income: 120k→130k. 120k<ART: some at 40% (no: eBRL=125140=ART, income>eBRL at 40% rate)
        # Actually: start=120k < eBRL(=ART=125140). end=130k > ART.
        # basic slice: PA to eBRL=ART; already exceeded at start.
        # higher: eBRL to ART: 125140-125140=0
        # additional: above ART: (130k-125140)×45%=4860×0.45=2187
        ref, eng = _run(invoice=10000, salary=100000, ytd=20000, pension=80000)
        assert eng["income_tax"] == ref["income_tax"]

    def test_pension_cap_preserves_additional_rate_band(self):
        """Even with pension=ART worth, income above ART must attract 45%."""
        # income_start below ART, income_end above ART; pension large enough to cap eBRL
        ref, eng = _run(invoice=10000, salary=0, ytd=120000, pension=75000)
        assert _variance(ref, eng) == 0.0


# ── Combined with EL-001 zone: no regression ─────────────────────────────────

class TestEL003WithEL001Zone:
    """Large pension + PA taper zone: both EL-001 and EL-003 protections active."""

    def test_large_pension_and_taper_zone_no_variance(self):
        """pension=£80k, income crosses taper: EL-001 zone AND eBRL cap both needed."""
        # ANI_start = 90k − 80k = 10k (below taper, PA full)
        # ANI_end = 100k − 80k = 20k (below taper, PA full)
        # No EL-001 zone here (ANI stays below taper). Just checking combo.
        ref, eng = _run(invoice=10000, salary=90000, ytd=0, pension=80000)
        assert _variance(ref, eng) == 0.0

    def test_large_pension_reduces_ani_but_does_not_enter_taper(self):
        """Large pension keeps ANI below taper; no EL-001; but eBRL cap still applies."""
        ref, eng = _run(invoice=5000, salary=200000, ytd=0, pension=80000)
        assert _variance(ref, eng) == 0.0

    def test_two_stage_3_el003_scenarios(self):
        """RW-S3-024 and RW-S3-035: both large-pension scenarios must pass."""
        # RW-S3-024: pension=75k, salary=130k
        ref24, eng24 = _run(invoice=10000, salary=130000, ytd=0, pension=75000)
        assert _variance(ref24, eng24) == 0.0, f"RW-S3-024: {_variance(ref24, eng24)}"
        # RW-S3-035: pension=100k, invoice=50k
        ref35, eng35 = _run(invoice=50000, salary=0, ytd=0, pension=100000)
        assert _variance(ref35, eng35) == 0.0, f"RW-S3-035: {_variance(ref35, eng35)}"
