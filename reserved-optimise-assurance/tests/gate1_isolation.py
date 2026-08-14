"""
Gate 1 — Isolation tests.

Each supported optimisation mechanism is tested in isolation against
HMRC-grounded reference calculations.  No product-engine code is imported
in Sections A–C (reference vs reference).  Section D cross-checks the
product engine against the reference oracle.

All monetary assertions are to the nearest penny.

HMRC sources
────────────
  ITEPA 2003 s.35           — Personal Allowance
  Finance (No.2) Act 2015   — PA taper
  Finance Act 2012 s.681B   — HICBC formula (revised April 2024)
  Finance Act 2004 s.192    — Pension Relief at Source
  HMRC PTM044100            — RaS band extension

Gate 1 PASS criteria
────────────────────
  All test functions must pass without error.
  Numerical results must match reference within ±£0.01.
  No scenario result may show a negative saving.
  No double-counting invariant must be violated.
"""
import sys
from pathlib import Path

import pytest
from decimal import Decimal

# Ensure imports resolve from workspace root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from reference.common import (
    p, personal_allowance_ref, income_tax_total_ref, hicbc_ref,
    PA, TAPER_START, TAPER_END, BRL, ART,
    HICBC_LOWER, HICBC_UPPER,
)
from reference.pa_taper_reference import (
    effective_marginal_rate_in_taper,
    pension_to_restore_full_pa,
    pa_at_ani,
    pa_reduction_at_ani,
)
from reference.hicbc_reference import (
    annual_cb_for_children,
    hicbc_charge,
    pension_to_eliminate_hicbc,
    charge_percentage,
    CB_ANNUAL_ELDEST, CB_ANNUAL_ADDITIONAL,
)
from reference.pension_reference import (
    net_to_gross, gross_to_net, basic_rate_relief,
    extended_brl, it_saving_from_pension,
    ANNUAL_ALLOWANCE,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Section A: Personal Allowance taper (reference only)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPATaperReference:

    def test_pa_below_taper_unchanged(self):
        """PA is full £12,570 when ANI ≤ £100,000."""
        assert pa_at_ani(Decimal("99999")) == PA
        assert pa_at_ani(Decimal("100000")) == PA
        assert pa_at_ani(Decimal("0")) == PA

    def test_pa_at_taper_entry_plus_one(self):
        """ANI = £100,001: PA reduced by £0.50 → £12,569.50."""
        result = pa_at_ani(Decimal("100001"))
        assert result == p(Decimal("12569.50"))

    def test_pa_midpoint(self):
        """ANI = £112,570: PA reduced by £6,285 → £6,285."""
        # reduction = (112570 - 100000) / 2 = 6285
        result = pa_at_ani(Decimal("112570"))
        assert result == Decimal("6285.00")

    def test_pa_eliminated_at_125140(self):
        """PA is £0 at ANI = £125,140."""
        result = pa_at_ani(Decimal("125140"))
        assert result == Decimal("0.00")

    def test_pa_above_125140_still_zero(self):
        """PA remains £0 for ANI > £125,140."""
        assert pa_at_ani(Decimal("150000")) == Decimal("0.00")
        assert pa_at_ani(Decimal("1000000")) == Decimal("0.00")

    def test_effective_marginal_rate_60pct(self):
        """Effective marginal rate in taper band at 40 % should be 60 %."""
        emr = effective_marginal_rate_in_taper(Decimal("0.40"))
        assert emr == Decimal("0.60")

    def test_pension_to_restore_full_pa(self):
        """ANI = £110,000 → needs £10,000 gross pension to restore full PA."""
        result = pension_to_restore_full_pa(Decimal("110000"))
        assert result == Decimal("10000.00")

    def test_pension_to_restore_full_pa_below_taper(self):
        """ANI ≤ £100,000 → no pension needed to restore PA."""
        assert pension_to_restore_full_pa(Decimal("90000")) == Decimal("0.00")
        assert pension_to_restore_full_pa(Decimal("100000")) == Decimal("0.00")

    def test_pa_reduction_exact(self):
        """PA reduction at ANI = £120,000 should be £10,000."""
        # (120000 - 100000) / 2 = 10000
        assert pa_reduction_at_ani(Decimal("120000")) == Decimal("10000.00")

    def test_taper_is_linear(self):
        """PA reduction is linear in the taper zone."""
        pa_100k = pa_at_ani(Decimal("100000"))
        pa_110k = pa_at_ani(Decimal("110000"))
        pa_120k = pa_at_ani(Decimal("120000"))
        # Each £10k ANI increase → £5k PA reduction
        assert p(pa_100k - pa_110k) == Decimal("5000.00")
        assert p(pa_110k - pa_120k) == Decimal("5000.00")


# ═══════════════════════════════════════════════════════════════════════════════
# Section B: HICBC (reference only)
# ═══════════════════════════════════════════════════════════════════════════════

class TestHICBCReference:

    def test_no_charge_below_threshold(self):
        """No HICBC when ANI ≤ £60,000."""
        cb = annual_cb_for_children(1)
        assert hicbc_charge(Decimal("60000"), cb) == Decimal("0.00")
        assert hicbc_charge(Decimal("59999"), cb) == Decimal("0.00")

    def test_no_charge_no_cb(self):
        """No HICBC when no Child Benefit is received."""
        assert hicbc_charge(Decimal("80000"), Decimal("0")) == Decimal("0.00")
        assert hicbc_charge(Decimal("100000"), Decimal("0")) == Decimal("0.00")

    def test_full_charge_at_80k(self):
        """HICBC equals the whole-pound relevant benefit when ANI ≥ £80,000.

        At 100 % the charge is the relevant total benefit floored to whole
        pounds: £1,406.60 → £1,406.
        """
        cb = annual_cb_for_children(1)
        expected = p(Decimal("1406.00"))
        assert hicbc_charge(Decimal("80000"), cb) == expected
        assert hicbc_charge(Decimal("90000"), cb) == expected
        assert hicbc_charge(Decimal("125140"), cb) == expected

    def test_half_charge_at_70k(self):
        """ANI = £70,000 → 50 complete £200 steps → 50 % of CB, staged-floor.

        relevant benefit = floor(1406.60) = 1406; 1406 × 50 / 100 = 703.
        """
        cb = annual_cb_for_children(1)
        expected = p(Decimal("703.00"))
        assert hicbc_charge(Decimal("70000"), cb) == expected

    def test_pension_to_eliminate_hicbc(self):
        """ANI = £70,000 → needs £10,000 gross pension to clear HICBC."""
        assert pension_to_eliminate_hicbc(Decimal("70000")) == Decimal("10000.00")

    def test_pension_to_eliminate_below_threshold(self):
        """No pension needed when ANI already ≤ £60,000."""
        assert pension_to_eliminate_hicbc(Decimal("60000")) == Decimal("0.00")
        assert pension_to_eliminate_hicbc(Decimal("55000")) == Decimal("0.00")

    def test_annual_cb_one_child(self):
        """1-child CB = eldest/only = £27.05 × 52 = £1,406.60."""
        expected = p(Decimal("27.05") * Decimal("52"))
        assert annual_cb_for_children(1) == expected

    def test_annual_cb_two_children(self):
        """2-child CB = eldest (£27.05) + 1 additional (£17.90) = £44.95 × 52."""
        expected = p(
            Decimal("27.05") * Decimal("52")
            + Decimal("17.90") * Decimal("52")
        )
        assert annual_cb_for_children(2) == expected

    def test_annual_cb_zero_children(self):
        assert annual_cb_for_children(0) == Decimal("0.00")

    def test_charge_percentage_linear(self):
        """Charge percentage rises by 1 for each complete £200 step (staged)."""
        assert charge_percentage(Decimal("60000")) == Decimal("0")
        assert charge_percentage(Decimal("60199")) == Decimal("0")
        assert charge_percentage(Decimal("60200")) == Decimal("1")
        assert charge_percentage(Decimal("60400")) == Decimal("2")

    def test_charge_percentage_caps_at_100(self):
        assert charge_percentage(Decimal("80000")) == Decimal("100")
        assert charge_percentage(Decimal("100000")) == Decimal("100")


# ═══════════════════════════════════════════════════════════════════════════════
# Section C: Pension RaS mechanics (reference only)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPensionRaSReference:

    def test_net_to_gross(self):
        """£8,000 net → £10,000 gross."""
        assert net_to_gross(Decimal("8000")) == Decimal("10000.00")

    def test_gross_to_net(self):
        """£10,000 gross → £8,000 net."""
        assert gross_to_net(Decimal("10000")) == Decimal("8000.00")

    def test_basic_rate_relief(self):
        """20 % of gross = basic rate relief added to pension by HMRC."""
        assert basic_rate_relief(Decimal("10000")) == Decimal("2000.00")

    def test_extended_brl(self):
        """Basic-rate band (£37,700) extended by gross pension, uncapped here."""
        assert extended_brl(Decimal("0"))     == Decimal("37700.00")
        assert extended_brl(Decimal("10000")) == Decimal("47700.00")

    def test_extended_brl_cap_at_art(self):
        """Extended band cannot exceed ART (£125,140)."""
        assert extended_brl(Decimal("100000")) == Decimal("125140.00")
        assert extended_brl(Decimal("200000")) == Decimal("125140.00")

    def test_it_saving_basic_rate_below_taper(self):
        """At £60,000 income with no pension, adding £5,000 pension saves £1,000 IT.
        (The £5k pension extends BRL, saving £5k × 20 % = £1,000 at basic rate.)
        Wait — at £60k income, the portion above BRL (£50,270) is £9,730 at 40 %.
        Adding £5k pension extends BRL to £55,270 → saves £5,000 × 40 % = £2,000.
        """
        saving = it_saving_from_pension(
            projected_income  = Decimal("60000"),
            current_pension   = Decimal("0"),
            additional_pension= Decimal("5000"),
        )
        # £5k of income shifts from 40 % to 20 % band → saves £5k × 20 % = £1,000
        assert saving == Decimal("1000.00")

    def test_it_saving_in_taper_zone(self):
        """£10,000 pension at £110,000 income (ANI £110k → £100k).

        Without pension: ANI=110,000 → PA=7,570; taxable=102,430 →
          37,700 @ 20 % (7,540) + 64,730 @ 40 % (25,892) = 33,432.
        With £10,000 pension: ANI=100,000 → PA=12,570; taxable=97,430;
          basic band extends to 47,700 →
          47,700 @ 20 % (9,540) + 49,730 @ 40 % (19,892) = 29,432.
        Saving = 33,432 − 29,432 = £4,000.
        """
        saving = it_saving_from_pension(
            projected_income  = Decimal("110000"),
            current_pension   = Decimal("0"),
            additional_pension= Decimal("10000"),
        )
        assert saving == Decimal("4000.00")

    def test_no_saving_above_art(self):
        """Pension contribution that stays above ART — saving comes from ANI reduction only."""
        saving = it_saving_from_pension(
            projected_income  = Decimal("200000"),
            current_pension   = Decimal("0"),
            additional_pension= Decimal("10000"),
        )
        # At 45 % — no BRL extension possible (already above ART), but ANI reduced
        # and potentially PA restored if ANI was in taper zone
        assert saving >= Decimal("0")


# ═══════════════════════════════════════════════════════════════════════════════
# Section D: Product engine cross-check (reference vs product)
# ═══════════════════════════════════════════════════════════════════════════════

class TestProductVsReference:
    """Cross-check reserved.engines.optimise against the independent reference.

    These tests import the product engine.  A failure here indicates a
    divergence between the product and the reference — not necessarily a
    product bug (the reference could be wrong too, but it triggers a review).
    """

    @pytest.fixture(autouse=True)
    def _import_product(self):
        from reserved.engines.optimise import calculate_position, model_pension_scenario
        self.calc = calculate_position
        self.model = model_pension_scenario

    def _ref_pos(self, income, pension, cb=Decimal("0")):
        from reference.scenario_reference import ref_position
        return ref_position(income, pension, cb)

    def test_position_ani_matches(self):
        income, pension = Decimal("110000"), Decimal("5000")
        prod = self.calc(income, pension)
        ref  = self._ref_pos(income, pension)
        assert prod.adjusted_net_income == ref.ani

    def test_position_pa_matches(self):
        income, pension = Decimal("110000"), Decimal("5000")
        prod = self.calc(income, pension)
        ref  = self._ref_pos(income, pension)
        assert prod.personal_allowance == ref.pa

    def test_position_income_tax_matches(self):
        income, pension = Decimal("110000"), Decimal("5000")
        prod = self.calc(income, pension)
        ref  = self._ref_pos(income, pension)
        assert prod.estimated_income_tax == ref.income_tax

    def test_position_hicbc_matches(self):
        cb = annual_cb_for_children(2)
        income, pension = Decimal("75000"), Decimal("0")
        prod = self.calc(income, pension, annual_cb=cb)
        ref  = self._ref_pos(income, pension, cb)
        assert prod.hicbc == ref.hicbc

    def test_scenario_it_reduction_matches(self):
        from reference.scenario_reference import ref_scenario
        income  = Decimal("115000")
        current = Decimal("3000")
        extra   = Decimal("15000")
        prod = self.model(income, current, extra, "PA_TAPER")
        ref  = ref_scenario(income, current, extra)
        assert prod.it_reduction == ref.it_reduction

    def test_scenario_total_benefit_non_negative(self):
        """Product must never return a negative total_benefit."""
        prod = self.model(Decimal("105000"), Decimal("0"), Decimal("5000"), "PA_TAPER")
        assert prod.total_benefit >= Decimal("0")

    def test_basic_rate_relief_not_in_total_benefit(self):
        """basic_rate_relief_to_pension must not be included in total_benefit."""
        prod = self.model(Decimal("110000"), Decimal("0"), Decimal("10000"), "PA_TAPER")
        # total_benefit should only be IT + HICBC savings, NOT + basic_rate_relief
        assert prod.total_benefit == prod.it_reduction + prod.hicbc_reduction
        # And basic_rate_relief is shown separately (it = 20 % of gross)
        assert prod.basic_rate_relief_to_pension == p(Decimal("10000") * Decimal("0.20"))

    def test_zero_additional_pension_no_benefit(self):
        """Adding £0 to pension must produce zero benefit."""
        prod = self.model(Decimal("110000"), Decimal("5000"), Decimal("0"), "PA_TAPER")
        assert prod.it_reduction    == Decimal("0")
        assert prod.hicbc_reduction == Decimal("0")
        assert prod.total_benefit   == Decimal("0")
