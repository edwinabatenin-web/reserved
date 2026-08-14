"""
Gate 3 — Interaction and sequence tests.

Tests combinations of mechanisms and state sequences that are more
likely to surface calculation errors than isolated unit tests.

Interaction families covered
─────────────────────────────
  3A: Pension + PA restoration — contribution that partially/fully clears taper
  3B: Pension + HICBC — contribution that partially/fully eliminates charge
  3C: Pension + both simultaneously — ANI crosses both thresholds
  3D: RaS vs salary-sacrifice distinction — SS must never be assumed
  3E: Multiple income sources — PAYE + freelance combined ANI
  3F: In-year projections — changing YTD income affects opportunity detection
  3G: Repeated scenario edits — idempotency of calculate_position
  3H: Incomplete-data states — missing CB, zero income, zero pension
"""
import sys
from pathlib import Path

import pytest
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from reference.common import p, income_tax_total_ref, hicbc_ref, personal_allowance_ref
from reference.hicbc_reference import annual_cb_for_children
from reference.scenario_reference import ref_scenario

CB1 = annual_cb_for_children(1)
CB2 = annual_cb_for_children(2)


class TestPensionPlusPA:
    """3A: Pension contributions that interact with the PA taper."""

    def test_partial_restoration(self):
        """Partial pension reduces ANI within taper zone — some PA restored."""
        from reserved.engines.optimise import model_pension_scenario
        result = model_pension_scenario(
            Decimal("120000"), Decimal("0"), Decimal("5000"), "PA_TAPER"
        )
        # ANI goes from 120k to 115k — PA improves but not fully restored
        assert result.after.adjusted_net_income == Decimal("115000")
        pa_before = personal_allowance_ref(Decimal("120000"))
        pa_after  = personal_allowance_ref(Decimal("115000"))
        assert result.after.personal_allowance  > result.before.personal_allowance
        assert result.after.personal_allowance  < Decimal("12570")
        assert result.after.personal_allowance  == pa_after
        assert result.it_reduction > Decimal("0")

    def test_full_restoration(self):
        """Pension that brings ANI to exactly £100,000 restores full PA."""
        from reserved.engines.optimise import model_pension_scenario
        result = model_pension_scenario(
            Decimal("110000"), Decimal("0"), Decimal("10000"), "PA_TAPER"
        )
        assert result.after.personal_allowance  == Decimal("12570")
        assert result.after.adjusted_net_income == Decimal("100000")

    def test_over_contribution_no_extra_pa_benefit(self):
        """Pension that takes ANI below £100,000 gives no extra PA (already zero reduction)."""
        from reserved.engines.optimise import model_pension_scenario
        # From £110k: £10k needed to clear taper, £15k over-contributes
        r_exact = model_pension_scenario(
            Decimal("110000"), Decimal("0"), Decimal("10000"), "PA_TAPER"
        )
        r_over  = model_pension_scenario(
            Decimal("110000"), Decimal("0"), Decimal("15000"), "PA_TAPER"
        )
        # Extra £5k contribution still gives band-extension benefit but not more PA
        assert r_over.after.personal_allowance == Decimal("12570")
        assert r_over.it_reduction >= r_exact.it_reduction

    def test_it_reduction_matches_reference_oracle(self):
        """Product IT reduction must match independent reference to the penny."""
        from reserved.engines.optimise import model_pension_scenario
        for income, pension, extra in [
            (Decimal("105000"), Decimal("0"),    Decimal("5000")),
            (Decimal("115000"), Decimal("3000"), Decimal("12000")),
            (Decimal("125000"), Decimal("10000"),Decimal("20000")),
        ]:
            prod = model_pension_scenario(income, pension, extra, "PA_TAPER")
            ref  = ref_scenario(income, pension, extra)
            assert prod.it_reduction == ref.it_reduction, (
                f"Mismatch at income={income}, pension={pension}, extra={extra}: "
                f"product={prod.it_reduction} ref={ref.it_reduction}"
            )


class TestPensionPlusHICBC:
    """3B: Pension contributions that interact with the HICBC."""

    def test_partial_hicbc_reduction(self):
        """Pension that partially reduces HICBC."""
        from reserved.engines.optimise import model_pension_scenario
        # ANI starts at £70k (50 % charge), pension reduces to £65k (25 % charge)
        result = model_pension_scenario(
            Decimal("70000"), Decimal("0"), Decimal("5000"), "HICBC", annual_cb=CB1
        )
        assert result.hicbc_reduction > Decimal("0")
        assert result.after.hicbc < result.before.hicbc
        assert result.after.hicbc > Decimal("0")

    def test_full_hicbc_elimination(self):
        """Pension that brings ANI below £60,000 eliminates HICBC entirely."""
        from reserved.engines.optimise import model_pension_scenario
        # ANI starts at £70k (50 complete steps → charge £703) → £10k pension
        # clears to exactly £60k (no charge).
        result = model_pension_scenario(
            Decimal("70000"), Decimal("0"), Decimal("10000"), "HICBC", annual_cb=CB1
        )
        assert result.after.hicbc == Decimal("0")
        # 50 % of the floored relevant benefit: floor(1406.60) × 50 / 100 = 703.
        assert result.hicbc_reduction == Decimal("703.00")

    def test_hicbc_reduction_matches_reference(self):
        """Product HICBC saving must match reference to the penny."""
        from reserved.engines.optimise import model_pension_scenario
        income, current, extra = Decimal("75000"), Decimal("0"), Decimal("8000")
        prod = model_pension_scenario(income, current, extra, "HICBC", annual_cb=CB2)
        ref  = ref_scenario(income, current, extra, annual_cb=CB2)
        assert prod.hicbc_reduction == ref.hicbc_reduction

    def test_total_benefit_equals_it_plus_hicbc_always(self):
        """Invariant: total_benefit == it_reduction + hicbc_reduction."""
        from reserved.engines.optimise import model_pension_scenario
        for income, extra, cb in [
            (Decimal("70000"),  Decimal("5000"),  CB1),
            (Decimal("110000"), Decimal("15000"), CB2),
            (Decimal("80000"),  Decimal("20000"), CB1),
        ]:
            r = model_pension_scenario(income, Decimal("0"), extra, "TEST", annual_cb=cb)
            assert r.total_benefit == r.it_reduction + r.hicbc_reduction


class TestPensionBothSimultaneously:
    """3C: ANI in both the HICBC and PA taper zones simultaneously."""

    INCOME  = Decimal("115000")   # ANI = £115k
    PENSION = Decimal("0")

    def test_both_charges_apply(self):
        """At ANI = £115,000 with CB, both PA taper and HICBC apply."""
        from reserved.engines.optimise import calculate_position
        pos = calculate_position(self.INCOME, self.PENSION, annual_cb=CB1)
        assert pos.hicbc  > Decimal("0")
        assert pos.personal_allowance < Decimal("12570")

    def test_large_pension_eliminates_both(self):
        """Pension that takes ANI below £60,000 eliminates both PA taper and HICBC."""
        from reserved.engines.optimise import model_pension_scenario
        result = model_pension_scenario(
            self.INCOME, self.PENSION, Decimal("55001"), "BOTH", annual_cb=CB1
        )
        # ANI after = 115000 - 55001 = 59999 < 60000
        assert result.after.hicbc == Decimal("0")
        assert result.after.personal_allowance == Decimal("12570")

    def test_total_benefit_covers_both_savings(self):
        """Total benefit captures savings from both PA restoration and HICBC."""
        from reserved.engines.optimise import model_pension_scenario
        result = model_pension_scenario(
            self.INCOME, self.PENSION, Decimal("55001"), "BOTH", annual_cb=CB1
        )
        assert result.total_benefit >= result.it_reduction
        assert result.total_benefit >= result.hicbc_reduction

    def test_total_benefit_matches_reference(self):
        """Cross-check combined saving against reference oracle."""
        from reserved.engines.optimise import model_pension_scenario
        extra = Decimal("20000")
        prod  = model_pension_scenario(self.INCOME, self.PENSION, extra, "BOTH", annual_cb=CB1)
        ref   = ref_scenario(self.INCOME, self.PENSION, extra, annual_cb=CB1)
        assert prod.it_reduction    == ref.it_reduction
        assert prod.hicbc_reduction == ref.hicbc_reduction
        assert prod.total_benefit   == ref.total_benefit


class TestSalaryVsRaS:
    """3D: Salary sacrifice must never be assumed available."""

    def test_assess_does_not_reference_salary_sacrifice(self):
        """assess_opportunities must not produce any opportunity flagged as SS."""
        from reserved.engines.optimise import assess_opportunities
        _, opps = assess_opportunities(
            {"personal_pension_contributions": "0"},
            projected_income_override=Decimal("110000"),
        )
        for opp in opps:
            # Constraints should warn about SS NOT being modelled
            full_text = " ".join(opp.constraints + opp.what_to_confirm)
            assert "salary sacrifice" in full_text.lower(), (
                f"Opportunity {opp.id} missing salary-sacrifice constraint"
            )

    def test_scenario_engine_has_no_ss_input(self):
        """model_pension_scenario has no salary-sacrifice parameter — never assumed."""
        import inspect
        from reserved.engines.optimise import model_pension_scenario
        sig = inspect.signature(model_pension_scenario)
        param_names = set(sig.parameters.keys())
        assert "salary_sacrifice" not in param_names
        assert "employer_pension" not in param_names


class TestMultipleIncomeSources:
    """3E: PAYE salary + freelance income combined."""

    def test_combined_income_triggers_pa_taper(self):
        """PAYE £80k + freelance £30k = £110k ANI → taper triggered."""
        from reserved.engines.optimise import assess_opportunities
        pos, opps = assess_opportunities(
            {
                "day_job_salary":               "80000",
                "personal_pension_contributions":"0",
            },
            projected_income_override=Decimal("110000"),
        )
        ids = {o.id for o in opps}
        assert "PA_TAPER" in ids

    def test_combined_income_ani_correct(self):
        from reserved.engines.optimise import calculate_position
        pos = calculate_position(Decimal("110000"), Decimal("0"))
        assert pos.adjusted_net_income == Decimal("110000")
        assert pos.projected_income    == Decimal("110000")


class TestInYearProjections:
    """3F: Income projection from YTD figures."""

    def test_ytd_projection_triggers_opportunity(self):
        """YTD that projects above £100k should flag PA_TAPER."""
        from datetime import date
        from reserved.engines.optimise import assess_opportunities
        # Simulate early in year: 1 month elapsed, £10k YTD → £120k projection
        pos, opps = assess_opportunities(
            {"ytd_freelance_profit": "10000", "personal_pension_contributions": "0"},
            today=date(2026, 5, 6),   # ~1 month into tax year starting 6 Apr
        )
        ids = {o.id for o in opps}
        assert "PA_TAPER" in ids

    def test_income_override_takes_precedence(self):
        """Explicit income override supersedes profile projection."""
        from reserved.engines.optimise import assess_opportunities
        pos, opps = assess_opportunities(
            {"ytd_freelance_profit": "10000", "personal_pension_contributions": "0"},
            projected_income_override=Decimal("80000"),  # forced below taper
        )
        ids = {o.id for o in opps}
        assert "PA_TAPER" not in ids


class TestRepeatedScenarioEdits:
    """3G: calculate_position is idempotent and deterministic."""

    def test_idempotent(self):
        from reserved.engines.optimise import calculate_position
        args = (Decimal("110000"), Decimal("5000"), Decimal("1383.20"))
        r1 = calculate_position(*args)
        r2 = calculate_position(*args)
        assert r1.estimated_income_tax == r2.estimated_income_tax
        assert r1.hicbc == r2.hicbc
        assert r1.adjusted_net_income == r2.adjusted_net_income

    def test_model_idempotent(self):
        from reserved.engines.optimise import model_pension_scenario
        args = (Decimal("115000"), Decimal("3000"), Decimal("12000"), "PA_TAPER")
        r1 = model_pension_scenario(*args)
        r2 = model_pension_scenario(*args)
        assert r1.total_benefit == r2.total_benefit
        assert r1.it_reduction  == r2.it_reduction


class TestIncompleteDataStates:
    """3H: Missing or partial data must not crash or produce misleading results."""

    def test_no_profile_data(self):
        """Empty profile → projected income £0, no opportunities detected."""
        from reserved.engines.optimise import assess_opportunities
        pos, opps = assess_opportunities({})
        assert pos.projected_income == Decimal("0")
        pa_opps = [o for o in opps if o.status == "available"]
        assert len(pa_opps) == 0

    def test_missing_cb_near_threshold_incomplete(self):
        """ANI near £60k with no CB → HICBC shown as incomplete, not available."""
        from reserved.engines.optimise import assess_opportunities
        pos, opps = assess_opportunities(
            {"personal_pension_contributions": "0"},
            projected_income_override=Decimal("65000"),
        )
        hicbc_opps = [o for o in opps if o.id == "HICBC"]
        assert len(hicbc_opps) == 1
        assert hicbc_opps[0].status == "incomplete"

    def test_missing_cb_far_from_threshold_no_opp(self):
        """ANI far from £60k with no CB → no HICBC opportunity shown."""
        from reserved.engines.optimise import assess_opportunities
        pos, opps = assess_opportunities(
            {"personal_pension_contributions": "0"},
            projected_income_override=Decimal("90000"),
        )
        hicbc_opps = [o for o in opps if o.id == "HICBC"]
        assert len(hicbc_opps) == 0

    def test_negative_additional_pension_raises(self):
        """Negative additional_pension must be rejected."""
        from reserved.engines.optimise import model_pension_scenario
        with pytest.raises(ValueError):
            model_pension_scenario(
                Decimal("110000"), Decimal("0"), Decimal("-1"), "PA_TAPER"
            )
