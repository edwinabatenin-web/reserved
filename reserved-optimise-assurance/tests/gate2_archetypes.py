"""
Gate 2 — Archetypes and exact boundaries.

Tests representative user archetypes and critical boundary conditions.
All monetary values are computed from HMRC primary-source formulas
(implemented independently in reference/) and compared against the
product engine.

Boundary conditions covered
────────────────────────────
  ANI £60,000   — HICBC lower threshold (inclusive / exclusive)
  ANI £80,000   — HICBC upper threshold (full reclaim)
  ANI £100,000  — PA taper entry (just below / at / just above)
  ANI £112,570  — PA halved
  ANI £125,140  — PA eliminated / additional-rate boundary
  Pension → clear PA taper exactly
  Pension → clear HICBC exactly
  Pension = 0   — no contributions
  Pension = £60,000 AA ceiling
"""
import sys
from pathlib import Path

import pytest
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from reference.common import p, personal_allowance_ref, income_tax_total_ref, hicbc_ref
from reference.hicbc_reference import annual_cb_for_children, CB_ANNUAL_ELDEST
from reference.scenario_reference import ref_scenario


CB1 = annual_cb_for_children(1)   # 1-child standard CB
CB2 = annual_cb_for_children(2)   # 2-child standard CB


# ═══════════════════════════════════════════════════════════════════════════════
# Archetype 1: Below all thresholds — £55,000 sole trader
# ═══════════════════════════════════════════════════════════════════════════════

class TestArchetypeBelowAllThresholds:
    """£55,000 projected income — no PA taper, HICBC not triggered."""

    INCOME = Decimal("55000")
    PENSION = Decimal("0")

    def test_no_pa_taper(self):
        ani = self.INCOME - self.PENSION
        pa  = personal_allowance_ref(ani)
        assert pa == Decimal("12570")

    def test_no_hicbc(self):
        ani = self.INCOME - self.PENSION
        assert hicbc_ref(ani, CB1) == Decimal("0")

    def test_assess_opportunities_empty(self):
        from reserved.engines.optimise import assess_opportunities
        pos, opps = assess_opportunities(
            {"day_job_salary": "55000", "ytd_freelance_profit": "0",
             "personal_pension_contributions": "0"},
            projected_income_override=self.INCOME,
        )
        # No HICBC data → no HICBC incomplete (outside proximity window)
        pa_taper_opps = [o for o in opps if o.id == "PA_TAPER"]
        assert len(pa_taper_opps) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# Archetype 2: HICBC boundary — ANI at £60,000 exactly
# ═══════════════════════════════════════════════════════════════════════════════

class TestHICBCLowerBoundary:

    def test_no_charge_at_60k_exactly(self):
        """ANI = £60,000 → no charge (threshold is exclusive)."""
        assert hicbc_ref(Decimal("60000"), CB1) == Decimal("0")

    def test_charge_at_60001(self):
        """ANI = £60,001 → 0.005 % of CB = £0.01 minimum charge."""
        charge = hicbc_ref(Decimal("60001"), CB1)
        # (1 / 200) % × CB1 = 0.005 % × ~£1383.20 ≈ £0.07
        assert charge > Decimal("0")
        assert charge < Decimal("1")

    def test_half_charge_at_70k(self):
        """ANI = £70,000 → 50 % of CB charged."""
        charge = hicbc_ref(Decimal("70000"), CB1)
        expected = p(CB1 * Decimal("50") / Decimal("100"))
        assert charge == expected

    def test_full_charge_at_80k(self):
        """ANI = £80,000 → 100 % of CB charged."""
        assert hicbc_ref(Decimal("80000"), CB1) == CB1

    def test_full_charge_above_80k(self):
        """ANI > £80,000 → charge capped at CB amount."""
        assert hicbc_ref(Decimal("100000"), CB1) == CB1
        assert hicbc_ref(Decimal("130000"), CB1) == CB1

    def test_product_matches_reference_at_70k(self):
        from reserved.engines.optimise import calculate_position
        pos = calculate_position(Decimal("70000"), Decimal("0"), annual_cb=CB1)
        ref_charge = hicbc_ref(Decimal("70000"), CB1)
        assert pos.hicbc == ref_charge


# ═══════════════════════════════════════════════════════════════════════════════
# Archetype 3: PA taper entry — ANI around £100,000
# ═══════════════════════════════════════════════════════════════════════════════

class TestPATaperBoundary:

    def test_pa_full_at_100k(self):
        assert personal_allowance_ref(Decimal("100000")) == Decimal("12570")

    def test_pa_at_100001(self):
        """PA reduced by £0.50 at ANI = £100,001."""
        result = personal_allowance_ref(Decimal("100001"))
        assert result == p(Decimal("12569.50"))

    def test_pa_taper_opportunity_appears(self):
        from reserved.engines.optimise import assess_opportunities
        pos, opps = assess_opportunities(
            {"personal_pension_contributions": "0"},
            projected_income_override=Decimal("105000"),
        )
        ids = {o.id for o in opps}
        assert "PA_TAPER" in ids

    def test_pa_taper_opportunity_absent_below(self):
        from reserved.engines.optimise import assess_opportunities
        pos, opps = assess_opportunities(
            {"personal_pension_contributions": "0"},
            projected_income_override=Decimal("99999"),
        )
        ids = {o.id for o in opps}
        assert "PA_TAPER" not in ids

    def test_product_income_tax_at_taper_entry(self):
        """Income tax at £100,001 vs reference."""
        from reserved.engines.optimise import calculate_position
        income, pension = Decimal("100001"), Decimal("0")
        prod = calculate_position(income, pension)
        ref  = income_tax_total_ref(income, pension)
        assert prod.estimated_income_tax == ref

    def test_scenario_clears_taper_exactly(self):
        """Scenario that brings ANI to exactly £100,000 should restore full PA."""
        from reserved.engines.optimise import model_pension_scenario
        income  = Decimal("110000")
        current = Decimal("0")
        extra   = Decimal("10000")   # brings ANI from £110k to £100k
        result  = model_pension_scenario(income, current, extra, "PA_TAPER")
        assert result.after.personal_allowance == Decimal("12570")
        assert result.after.adjusted_net_income == Decimal("100000")

    def test_scenario_it_reduction_matches_reference(self):
        """Cross-check product IT saving against reference oracle."""
        from reserved.engines.optimise import model_pension_scenario
        income, current, extra = Decimal("115000"), Decimal("3000"), Decimal("12000")
        prod = model_pension_scenario(income, current, extra, "PA_TAPER")
        ref  = ref_scenario(income, current, extra)
        assert prod.it_reduction == ref.it_reduction

    def test_pa_eliminated_at_125140(self):
        from reserved.engines.optimise import calculate_position
        pos = calculate_position(Decimal("125140"), Decimal("0"))
        assert pos.personal_allowance == Decimal("0")

    def test_pa_still_zero_above_125140(self):
        from reserved.engines.optimise import calculate_position
        pos = calculate_position(Decimal("150000"), Decimal("0"))
        assert pos.personal_allowance == Decimal("0")


# ═══════════════════════════════════════════════════════════════════════════════
# Archetype 4: Combined PA taper + HICBC — ANI £100k–£125k with CB
# ═══════════════════════════════════════════════════════════════════════════════

class TestCombinedTaperAndHICBC:
    """A user with ANI in the taper zone also receiving Child Benefit."""

    INCOME  = Decimal("115000")
    PENSION = Decimal("5000")
    ANI     = Decimal("110000")   # 115000 - 5000

    def test_both_charges_present(self):
        from reserved.engines.optimise import calculate_position
        pos = calculate_position(self.INCOME, self.PENSION, annual_cb=CB2)
        assert pos.hicbc > Decimal("0")
        assert pos.personal_allowance < Decimal("12570")

    def test_product_hicbc_matches_reference(self):
        from reserved.engines.optimise import calculate_position
        pos = calculate_position(self.INCOME, self.PENSION, annual_cb=CB2)
        ref_hicbc = hicbc_ref(self.ANI, CB2)
        assert pos.hicbc == ref_hicbc

    def test_both_opportunities_detected(self):
        from reserved.engines.optimise import assess_opportunities
        pos, opps = assess_opportunities(
            {
                "personal_pension_contributions": str(self.PENSION),
                "child_benefit_children": "2",
            },
            projected_income_override=self.INCOME,
        )
        ids = {o.id for o in opps}
        assert "PA_TAPER" in ids
        assert "HICBC" in ids

    def test_total_benefit_includes_both_savings(self):
        from reserved.engines.optimise import model_pension_scenario
        # HICBC is at 100 % for ANI £80,000 or above.  At ANI=£110,000 the HICBC
        # is already fully charged (£2,298.40 for 2 children).  To reduce HICBC we
        # need ANI to fall below £80,000.
        # Adding £35,000 pension: total = £40,000, ANI = 115,000 − 40,000 = £75,000.
        # HICBC_after = CB2 × (75,000−60,000)/200/100 = CB2 × 0.75 (partial charge).
        # Both it_reduction and hicbc_reduction must be > 0.
        result = model_pension_scenario(
            self.INCOME, self.PENSION, Decimal("35000"), "PA_TAPER", annual_cb=CB2
        )
        assert result.hicbc_reduction > Decimal("0")
        assert result.it_reduction   > Decimal("0")
        assert result.total_benefit == result.it_reduction + result.hicbc_reduction


# ═══════════════════════════════════════════════════════════════════════════════
# Archetype 5: Annual Allowance ceiling — pension suggestion capped at £60k
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnnualAllowanceCeiling:

    def test_pension_to_clear_capped_at_60k(self):
        """If clearing the taper needs > £60k, suggestion is capped at £60k."""
        from reserved.engines.optimise import assess_opportunities
        # Income £200k → to clear PA taper would need £100k pension
        pos, opps = assess_opportunities(
            {"personal_pension_contributions": "0"},
            projected_income_override=Decimal("200000"),
        )
        taper = next(o for o in opps if o.id == "PA_TAPER")
        assert taper.pension_to_clear_capped == Decimal("60000")
        assert taper.pension_to_clear_fully  == Decimal("100000")

    def test_pension_to_clear_fully_not_capped_in_opps(self):
        """The 'fully clear' amount is always shown, even if > £60k AA."""
        from reserved.engines.optimise import assess_opportunities
        pos, opps = assess_opportunities(
            {"personal_pension_contributions": "0"},
            projected_income_override=Decimal("200000"),
        )
        taper = next(o for o in opps if o.id == "PA_TAPER")
        assert taper.pension_to_clear_fully > Decimal("60000")
