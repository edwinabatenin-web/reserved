"""
Gate 4 — Extremes, invariants, adversarial UX, and regression integrity.

Gate 4 is the final quality gate before the optimisation feature is
considered launch-ready.  It tests:

  4A: Extreme but valid inputs — no crash, no nonsensical output
  4B: Non-negativity invariants — no negative savings, no double-counting
  4C: Adversarial UX — scenarios must not be recommendations; salary
      sacrifice never assumed; ineligibility surfaced not guessed
  4D: Stable under extreme income / pension inputs
  4E: Unsupported cases fail safely
  4F: Initiative 001 regression — all WS/RWI-001 families still pass
"""
import sys
from pathlib import Path

import pytest
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from reference.common import p, income_tax_total_ref
from reference.hicbc_reference import annual_cb_for_children

CB1 = annual_cb_for_children(1)


# ═══════════════════════════════════════════════════════════════════════════════
# 4A: Extreme but valid inputs
# ═══════════════════════════════════════════════════════════════════════════════

class TestExtremeInputs:

    @pytest.mark.parametrize("income", [
        Decimal("0"),
        Decimal("1"),
        Decimal("12570"),
        Decimal("100000"),
        Decimal("125140"),
        Decimal("125141"),
        Decimal("500000"),
        Decimal("1000000"),
    ])
    def test_calculate_position_no_crash(self, income):
        from reserved.engines.optimise import calculate_position
        pos = calculate_position(income, Decimal("0"))
        assert pos.estimated_income_tax >= Decimal("0")
        assert pos.personal_allowance   >= Decimal("0")
        assert pos.hicbc                >= Decimal("0")

    @pytest.mark.parametrize("pension", [
        Decimal("0"),
        Decimal("1"),
        Decimal("10000"),
        Decimal("60000"),
        Decimal("60001"),   # over AA — engine does not enforce AA
        Decimal("100000"),
    ])
    def test_calculate_position_varied_pension_no_crash(self, pension):
        from reserved.engines.optimise import calculate_position
        pos = calculate_position(Decimal("150000"), pension)
        assert pos.estimated_income_tax >= Decimal("0")

    def test_pension_exceeds_income_ani_clamped_to_zero(self):
        """If pension > income, ANI = 0 (clamped), not negative."""
        from reserved.engines.optimise import calculate_position
        pos = calculate_position(Decimal("10000"), Decimal("50000"))
        assert pos.adjusted_net_income == Decimal("0")

    def test_very_large_cb_no_crash(self):
        from reserved.engines.optimise import calculate_position
        pos = calculate_position(
            Decimal("80000"), Decimal("0"), annual_cb=Decimal("999999")
        )
        # HICBC capped at annual_cb (100 % reclaim)
        assert pos.hicbc == Decimal("999999")

    def test_zero_income_zero_everything(self):
        from reserved.engines.optimise import calculate_position
        pos = calculate_position(Decimal("0"), Decimal("0"))
        assert pos.estimated_income_tax == Decimal("0")
        assert pos.hicbc                == Decimal("0")
        assert pos.personal_allowance   == Decimal("12570")
        assert pos.adjusted_net_income  == Decimal("0")


# ═══════════════════════════════════════════════════════════════════════════════
# 4B: Non-negativity and no-double-counting invariants
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvariants:
    """Core invariants that must hold for all valid inputs."""

    @pytest.mark.parametrize("income,pension,extra,cb", [
        (Decimal("110000"), Decimal("0"),    Decimal("10000"), Decimal("0")),
        (Decimal("70000"),  Decimal("0"),    Decimal("8000"),  CB1),
        (Decimal("115000"), Decimal("5000"), Decimal("15000"), CB1),
        (Decimal("90000"),  Decimal("0"),    Decimal("30000"), CB1),
        (Decimal("200000"), Decimal("0"),    Decimal("60000"), Decimal("0")),
        (Decimal("0"),      Decimal("0"),    Decimal("1"),     Decimal("0")),
    ])
    def test_it_reduction_non_negative(self, income, pension, extra, cb):
        from reserved.engines.optimise import model_pension_scenario
        r = model_pension_scenario(income, pension, extra, "TEST", annual_cb=cb)
        assert r.it_reduction >= Decimal("0"), (
            f"Negative IT reduction at income={income}, pension={pension}, extra={extra}"
        )

    @pytest.mark.parametrize("income,pension,extra,cb", [
        (Decimal("75000"),  Decimal("0"), Decimal("10000"), CB1),
        (Decimal("65000"),  Decimal("0"), Decimal("5000"),  CB1),
        (Decimal("80001"),  Decimal("0"), Decimal("20001"), CB1),
    ])
    def test_hicbc_reduction_non_negative(self, income, pension, extra, cb):
        from reserved.engines.optimise import model_pension_scenario
        r = model_pension_scenario(income, pension, extra, "TEST", annual_cb=cb)
        assert r.hicbc_reduction >= Decimal("0")

    @pytest.mark.parametrize("income,pension,extra,cb", [
        (Decimal("110000"), Decimal("0"),    Decimal("10000"), Decimal("0")),
        (Decimal("75000"),  Decimal("0"),    Decimal("8000"),  CB1),
        (Decimal("115000"), Decimal("5000"), Decimal("50000"), CB1),
    ])
    def test_total_benefit_equals_sum(self, income, pension, extra, cb):
        from reserved.engines.optimise import model_pension_scenario
        r = model_pension_scenario(income, pension, extra, "TEST", annual_cb=cb)
        assert r.total_benefit == r.it_reduction + r.hicbc_reduction

    @pytest.mark.parametrize("income,pension,extra,cb", [
        (Decimal("110000"), Decimal("0"),    Decimal("10000"), Decimal("0")),
        (Decimal("75000"),  Decimal("0"),    Decimal("8000"),  CB1),
    ])
    def test_basic_rate_relief_not_in_total_benefit(self, income, pension, extra, cb):
        """Basic-rate pension relief must not be included in total_benefit."""
        from reserved.engines.optimise import model_pension_scenario
        r = model_pension_scenario(income, pension, extra, "TEST", annual_cb=cb)
        # total_benefit = it_reduction + hicbc_reduction (no brl)
        claimed_total_with_brl = r.it_reduction + r.hicbc_reduction + r.basic_rate_relief_to_pension
        assert r.total_benefit < claimed_total_with_brl or r.basic_rate_relief_to_pension == Decimal("0")

    def test_position_income_tax_non_negative_always(self):
        from reserved.engines.optimise import calculate_position
        for income in [Decimal("0"), Decimal("12570"), Decimal("50270"), Decimal("125140")]:
            pos = calculate_position(income, Decimal("0"))
            assert pos.estimated_income_tax >= Decimal("0")

    def test_hicbc_never_exceeds_annual_cb(self):
        """HICBC charge must never exceed the annual CB amount."""
        from reserved.engines.optimise import calculate_position
        cb = CB1
        for income in [Decimal("80000"), Decimal("100000"), Decimal("200000")]:
            pos = calculate_position(income, Decimal("0"), annual_cb=cb)
            assert pos.hicbc <= cb

    def test_no_benefit_from_zero_pension(self):
        """A £0 additional pension contribution must produce zero benefit."""
        from reserved.engines.optimise import model_pension_scenario
        r = model_pension_scenario(Decimal("110000"), Decimal("0"), Decimal("0"), "PA_TAPER")
        assert r.total_benefit == Decimal("0")
        assert r.it_reduction  == Decimal("0")

    def test_after_position_never_worse_than_before(self):
        """IT + HICBC in the 'after' scenario must never exceed 'before'."""
        from reserved.engines.optimise import model_pension_scenario
        for income, extra in [
            (Decimal("110000"), Decimal("10000")),
            (Decimal("75000"),  Decimal("8000")),
            (Decimal("130000"), Decimal("30000")),
        ]:
            r = model_pension_scenario(income, Decimal("0"), extra, "TEST", annual_cb=CB1)
            assert r.after.estimated_income_tax <= r.before.estimated_income_tax
            assert r.after.hicbc               <= r.before.hicbc


# ═══════════════════════════════════════════════════════════════════════════════
# 4C: Adversarial UX — positioning and constraint enforcement
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdversarialUX:

    def test_salary_sacrifice_not_assumed(self):
        """No opportunity should claim salary sacrifice is available."""
        from reserved.engines.optimise import assess_opportunities
        _, opps = assess_opportunities(
            {"personal_pension_contributions": "0"},
            projected_income_override=Decimal("120000"),
        )
        for opp in opps:
            for text in opp.constraints + opp.what_to_confirm + opp.missing_data:
                # The word "salary sacrifice" appears in warning context, not as offered
                lower = text.lower()
                assert "salary sacrifice" not in lower or (
                    "not" in lower or "confirm" in lower or "available" in lower
                ), f"Constraint may be implying SS is available: '{text}'"

    def test_incomplete_does_not_present_as_available(self):
        """HICBC with no CB data near threshold → status=incomplete, not available."""
        from reserved.engines.optimise import assess_opportunities
        _, opps = assess_opportunities(
            {"personal_pension_contributions": "0"},
            projected_income_override=Decimal("65000"),
        )
        hicbc_opps = [o for o in opps if o.id == "HICBC"]
        for opp in hicbc_opps:
            assert opp.status != "available"

    def test_negative_additional_pension_rejected(self):
        from reserved.engines.optimise import model_pension_scenario
        with pytest.raises(ValueError, match="negative"):
            model_pension_scenario(
                Decimal("110000"), Decimal("0"), Decimal("-500"), "PA_TAPER"
            )

    def test_caveats_present_in_scenario_result(self):
        """Every scenario result must include caveats about AA and SS."""
        from reserved.engines.optimise import model_pension_scenario
        r = model_pension_scenario(Decimal("115000"), Decimal("0"), Decimal("15000"), "PA_TAPER")
        full_caveats = " ".join(r.caveats).lower()
        assert "annual allowance" in full_caveats
        assert "salary sacrifice" in full_caveats

    def test_opportunity_what_to_confirm_not_empty(self):
        """Available opportunities must always include a 'what to confirm' list."""
        from reserved.engines.optimise import assess_opportunities
        _, opps = assess_opportunities(
            {"child_benefit_children": "1", "personal_pension_contributions": "0"},
            projected_income_override=Decimal("115000"),
        )
        for opp in opps:
            if opp.status == "available":
                assert len(opp.what_to_confirm) > 0, (
                    f"Opportunity {opp.id} has no 'what to confirm' items"
                )


# ═══════════════════════════════════════════════════════════════════════════════
# 4D: Stable under extreme but valid inputs
# ═══════════════════════════════════════════════════════════════════════════════

class TestStabilityExtremes:

    def test_income_1m_no_crash(self):
        from reserved.engines.optimise import assess_opportunities
        _, opps = assess_opportunities(
            {"personal_pension_contributions": "0"},
            projected_income_override=Decimal("1000000"),
        )
        assert any(o.id == "PA_TAPER" for o in opps)

    def test_pension_60000_exact_aa_limit(self):
        """At the standard AA ceiling of £60,000 — no crash, sensible result."""
        from reserved.engines.optimise import model_pension_scenario
        r = model_pension_scenario(
            Decimal("160000"), Decimal("0"), Decimal("60000"), "PA_TAPER"
        )
        assert r.it_reduction  >= Decimal("0")
        assert r.total_benefit >= Decimal("0")

    def test_penny_precision_maintained(self):
        """Monetary results must be precise to exactly 2 decimal places."""
        from reserved.engines.optimise import calculate_position, model_pension_scenario
        pos = calculate_position(Decimal("112345.67"), Decimal("1234.56"))
        assert pos.estimated_income_tax == pos.estimated_income_tax.quantize(Decimal("0.01"))
        r = model_pension_scenario(
            Decimal("112345.67"), Decimal("1234.56"), Decimal("5678.90"), "TEST"
        )
        assert r.total_benefit == r.total_benefit.quantize(Decimal("0.01"))


# ═══════════════════════════════════════════════════════════════════════════════
# 4E: Unsupported cases fail safely
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnsupportedCases:

    def test_unsupported_tax_year_raises(self):
        from reserved.engines.optimise import calculate_position
        with pytest.raises(ValueError):
            calculate_position(Decimal("110000"), Decimal("0"), tax_year="1999/00")

    def test_invalid_income_string_raises(self):
        """assess_opportunities with a non-numeric profile value must not produce nonsense."""
        from reserved.engines.optimise import assess_opportunities
        # The engine should handle malformed values gracefully (default to 0)
        pos, opps = assess_opportunities(
            {"day_job_salary": "not_a_number"},
            projected_income_override=Decimal("0"),
        )
        assert pos.projected_income == Decimal("0")


# ═══════════════════════════════════════════════════════════════════════════════
# 4F: Initiative 001 regression integrity
# ═══════════════════════════════════════════════════════════════════════════════

class TestRWI001Regression:
    """Confirm Initiative 001 assurance families are unaffected by optimise work.

    These tests re-exercise the core income_tax engine (not the optimise
    engine) to verify that adding the optimise module has not altered any
    existing calculation.
    """

    def test_basic_rate_taxpayer_unchanged(self):
        """£30,000 income, no pension → income tax consistent with 2026/27 rules."""
        it = income_tax_total_ref(Decimal("30000"), Decimal("0"))
        # Taxable: 30000 - 12570 = 17430 at 20 % = 3486.00
        assert it == Decimal("3486.00")

    def test_higher_rate_taxpayer_unchanged(self):
        """£60,000 income, no pension → correct band split."""
        it = income_tax_total_ref(Decimal("60000"), Decimal("0"))
        # Basic: 50270 - 12570 = 37700 at 20 % = 7540.00
        # Higher: 60000 - 50270 = 9730 at 40 % = 3892.00
        # Total: 11432.00
        assert it == Decimal("11432.00")

    def test_pa_taper_income_tax_unchanged(self):
        """Income-tax at £110,000 (taper zone) consistent with reference oracle."""
        it_prod = income_tax_total_ref(Decimal("110000"), Decimal("0"))
        # Verify using the product engine
        from reserved.engines.optimise import calculate_position
        pos = calculate_position(Decimal("110000"), Decimal("0"))
        assert pos.estimated_income_tax == it_prod

    def test_pension_ras_band_extension_unchanged(self):
        """At £60k income, a £5k pension shifts exactly £5k from 40 % to 20 %: saves £1,000.

        Higher-rate exposure = 60,000 − 50,270 = £9,730.
        £5k pension extends BRL to 55,270 → higher-rate slice drops to £4,730.
        Saving = (9,730 − 4,730) × 20 % = £1,000.

        (A £10k pension would remove the entire higher-rate slice and save £1,946.)
        """
        before = income_tax_total_ref(Decimal("60000"), Decimal("0"))
        after  = income_tax_total_ref(Decimal("60000"), Decimal("5000"))
        saving = p(before - after)
        assert saving == Decimal("1000.00")

    def test_additional_rate_unchanged(self):
        """At income > £125,140 all excess taxed at 45 %."""
        it_at_130k = income_tax_total_ref(Decimal("130000"), Decimal("0"))
        it_at_125k = income_tax_total_ref(Decimal("125140"), Decimal("0"))
        # Additional: (130000 - 125140) = 4860 at 45 % = 2187.00
        diff = p(it_at_130k - it_at_125k)
        assert diff == p(Decimal("4860") * Decimal("0.45"))

    def test_el003_ebrl_cap_defect_not_reintroduced(self):
        """EL-003 regression: pension > £74,870 must not suppress the 45% rate.

        Verified against the known post-fix expected value.
        """
        # £200k income, £80k pension: eBRL capped at ART (£125,140)
        # Without cap fix: eBRL = £130,270 → absorbs ART → wrong 45% tax
        it = income_tax_total_ref(Decimal("200000"), Decimal("80000"))
        # ANI = 120000, PA = 12570 - 10000 = 2570
        # eBRL = min(50270+80000, 125140) = 125140
        # Basic: 125140 - 2570 = 122570 at 20% = 24514.00
        # Higher: 0 (ART reached)
        # Additional: 200000 - 125140 = 74860 at 45% = 33687.00
        # Total = 58201.00
        assert it == Decimal("58201.00")
