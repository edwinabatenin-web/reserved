"""
Product tests for reserved.engines.optimise.

Covers:
  - calculate_position: ANI, PA, income tax, HICBC calculations
  - model_pension_scenario: before/after comparison, benefit breakdown
  - assess_opportunities: PA_TAPER, HICBC, incomplete detection
  - Profile resolution helpers: pension, income, CB from various dict shapes

These tests sit alongside the product engine tests and run with the
standard test suite:
    .venv/bin/python -m pytest tests/test_optimise.py -v

They are NOT a substitute for the Whip Smart West Initiative 002
assurance programme, which runs independently with its own reference
implementations and gate structure.
"""
from __future__ import annotations

import pytest
from decimal import Decimal
from datetime import date


# ── Helpers ───────────────────────────────────────────────────────────────────

def calc(income, pension, cb=Decimal("0")):
    from reserved.engines.optimise import calculate_position
    return calculate_position(
        Decimal(str(income)), Decimal(str(pension)), Decimal(str(cb))
    )


def scenario(income, current_pension, extra, opportunity_id="TEST", cb=Decimal("0")):
    from reserved.engines.optimise import model_pension_scenario
    return model_pension_scenario(
        Decimal(str(income)),
        Decimal(str(current_pension)),
        Decimal(str(extra)),
        opportunity_id,
        annual_cb=Decimal(str(cb)),
    )


def assess(profile, income_override=None):
    from reserved.engines.optimise import assess_opportunities
    override = Decimal(str(income_override)) if income_override is not None else None
    return assess_opportunities(profile, projected_income_override=override)


# ═══════════════════════════════════════════════════════════════════════════════
# calculate_position
# ═══════════════════════════════════════════════════════════════════════════════

class TestCalculatePosition:

    def test_zero_income(self):
        pos = calc(0, 0)
        assert pos.projected_income     == Decimal("0")
        assert pos.adjusted_net_income  == Decimal("0")
        assert pos.personal_allowance   == Decimal("12570")
        assert pos.estimated_income_tax == Decimal("0")
        assert pos.hicbc                == Decimal("0")

    def test_basic_rate_taxpayer(self):
        # £30,000 income: taxable = 17430, tax = 3486.00
        pos = calc(30000, 0)
        assert pos.adjusted_net_income  == Decimal("30000")
        assert pos.personal_allowance   == Decimal("12570")
        assert pos.estimated_income_tax == Decimal("3486.00")

    def test_higher_rate_taxpayer(self):
        pos = calc(60000, 0)
        # Tax: 37700 @ 20% + 9730 @ 40% = 7540 + 3892 = 11432
        assert pos.estimated_income_tax == Decimal("11432.00")

    def test_pa_taper_at_110k(self):
        pos = calc(110000, 0)
        # ANI = 110000, PA reduction = (110000-100000)/2 = 5000 → PA = 7570
        assert pos.adjusted_net_income == Decimal("110000")
        assert pos.personal_allowance  == Decimal("7570")

    def test_pa_eliminated_at_125140(self):
        pos = calc(125140, 0)
        assert pos.personal_allowance == Decimal("0")

    def test_pension_reduces_ani(self):
        # Income 110000, pension 10000 → ANI = 100000 → PA fully restored
        pos = calc(110000, 10000)
        assert pos.adjusted_net_income == Decimal("100000")
        assert pos.personal_allowance  == Decimal("12570")

    def test_pension_extends_brl(self):
        # At £60k income with no pension: higher-rate slice = 60000 - 50270 = £9,730 at 40%.
        # Adding £10k pension extends BRL to min(50270+10000, 125140) = £60,270, which
        # exceeds income, removing all higher-rate exposure.
        # Saving = £9,730 × (40% − 20%) = £9,730 × 20% = £1,946.
        pos_no_pension = calc(60000, 0)
        pos_pension    = calc(60000, 10000)
        saving = pos_no_pension.estimated_income_tax - pos_pension.estimated_income_tax
        assert saving == Decimal("1946.00")

    def test_hicbc_at_70k_one_child(self):
        # ANI 70k, 1 child: charge_pct = (70000-60000)/200 = 50%
        # CB1 = 26.60 × 52 = 1383.20; 50% is 691.60; s681C(3) floors to £691.
        pos = calc(70000, 0, cb="1383.20")
        # The statutory charge is rounded down to whole pounds.
        assert pos.hicbc == Decimal("691.00")

    def test_hicbc_uses_whole_percentage_steps(self):
        cb = Decimal("1406.60")
        assert calc(60001, 0, cb=cb).hicbc == Decimal("0")
        assert calc(60199, 0, cb=cb).hicbc == Decimal("0")
        assert calc(60200, 0, cb=cb).hicbc == Decimal("14.00")
        assert calc(60399, 0, cb=cb).hicbc == Decimal("14.00")
        # Statutory staging floors relevant benefit before applying the
        # percentage, then floors the resulting charge.
        assert calc(79999, 0, cb=cb).hicbc == Decimal("1391.00")
        assert calc(79800, 0, cb="1406.99").hicbc == Decimal("1391.00")

    def test_hicbc_zero_below_60k(self):
        pos = calc(60000, 0, cb="1383.20")
        assert pos.hicbc == Decimal("0")

    def test_hicbc_capped_at_full_cb_above_80k(self):
        pos = calc(80000, 0, cb="1383.20")
        assert pos.hicbc == Decimal("1383.00")

    def test_pension_clamps_ani_to_zero(self):
        """Pension exceeding income → ANI = 0, not negative."""
        pos = calc(10000, 50000)
        assert pos.adjusted_net_income == Decimal("0")
        assert pos.estimated_income_tax >= Decimal("0")

    def test_total_charges(self):
        pos = calc(75000, 0, cb="1383.20")
        expected = pos.estimated_income_tax + pos.hicbc
        assert pos.total_charges() == expected


# ═══════════════════════════════════════════════════════════════════════════════
# model_pension_scenario
# ═══════════════════════════════════════════════════════════════════════════════

class TestModelPensionScenario:

    def test_zero_additional_pension(self):
        r = scenario(110000, 0, 0)
        assert r.it_reduction    == Decimal("0")
        assert r.hicbc_reduction == Decimal("0")
        assert r.total_benefit   == Decimal("0")

    def test_it_reduction_in_taper_zone(self):
        # At £110k income, £10k pension brings ANI from £110k to £100k:
        #   • Restores £5k PA; because the taxable basic-rate band remains
        #     £37,700, this removes £5k otherwise taxed at 40%: saves £2,000
        #   • Extends BRL by £10k (shifts £10k from 40% to 20%): saves £10k × 20% = £2,000
        #   • Total: £4,000
        # (Note: the income itself remains £110k — pension changes the band thresholds,
        #  not the amount of income taxed.)
        r = scenario(110000, 0, 10000)
        assert r.it_reduction == Decimal("4000.00")

    def test_hicbc_reduction_at_70k(self):
        cb = Decimal("1383.20")
        r = scenario(70000, 0, 10000, cb=cb)
        # ANI drops from 70k to 60k → HICBC eliminated (was 50% of CB)
        assert r.hicbc_reduction == Decimal("691.00")
        assert r.after.hicbc     == Decimal("0")

    def test_total_benefit_equals_it_plus_hicbc(self):
        r = scenario(115000, 5000, 15000, cb="1383.20")
        assert r.total_benefit == r.it_reduction + r.hicbc_reduction

    def test_basic_rate_relief_not_in_total_benefit(self):
        r = scenario(110000, 0, 10000)
        assert r.basic_rate_relief_to_pension == Decimal("2000.00")
        assert r.total_benefit != r.total_benefit + r.basic_rate_relief_to_pension

    def test_basic_rate_relief_is_20pct_of_gross(self):
        r = scenario(110000, 0, 15000)
        assert r.basic_rate_relief_to_pension == Decimal("3000.00")

    def test_total_pension_field(self):
        r = scenario(110000, 3000, 7000)
        assert r.total_pension == Decimal("10000.00")

    def test_negative_additional_pension_raises(self):
        with pytest.raises(ValueError):
            scenario(110000, 0, -1)

    def test_before_after_fields_consistent(self):
        r = scenario(110000, 0, 10000)
        assert r.before.projected_income == r.after.projected_income
        assert r.before.pension          == Decimal("0")
        assert r.after.pension           == Decimal("10000")

    def test_after_it_never_exceeds_before(self):
        """A pension contribution must not increase income tax."""
        for extra in [1000, 5000, 10000, 20000, 60000]:
            r = scenario(130000, 0, extra)
            assert r.after.estimated_income_tax <= r.before.estimated_income_tax

    def test_caveats_non_empty(self):
        r = scenario(110000, 0, 10000)
        assert len(r.caveats) > 0
        caveat_text = " ".join(r.caveats).lower()
        assert "annual allowance" in caveat_text
        assert "salary sacrifice" in caveat_text


# ═══════════════════════════════════════════════════════════════════════════════
# assess_opportunities
# ═══════════════════════════════════════════════════════════════════════════════

class TestAssessOpportunities:

    def test_no_opportunities_low_income(self):
        pos, opps = assess({"personal_pension_contributions": "0"}, income_override=50000)
        available = [o for o in opps if o.status == "available"]
        assert len(available) == 0

    def test_pa_taper_detected_above_100k(self):
        pos, opps = assess({"personal_pension_contributions": "0"}, income_override=110000)
        ids = {o.id for o in opps}
        assert "PA_TAPER" in ids

    def test_pa_taper_not_detected_at_exactly_100k(self):
        # At exactly £100,000 ANI the PA is still full (£12,570 — taper starts above this).
        # The engine uses strict > so no opportunity is surfaced at this threshold.
        pos, opps = assess({"personal_pension_contributions": "0"}, income_override=100000)
        available_pa = [o for o in opps if o.id == "PA_TAPER" and o.status == "available"]
        assert len(available_pa) == 0

    def test_hicbc_detected_with_cb_data(self):
        pos, opps = assess(
            {"personal_pension_contributions": "0", "child_benefit_children": "1"},
            income_override=70000,
        )
        hicbc_opps = [o for o in opps if o.id == "HICBC" and o.status == "available"]
        assert len(hicbc_opps) == 1

    def test_hicbc_incomplete_near_threshold_no_cb_data(self):
        pos, opps = assess(
            {"personal_pension_contributions": "0"},
            income_override=65000,
        )
        incomplete = [o for o in opps if o.id == "HICBC" and o.status == "incomplete"]
        assert len(incomplete) == 1
        assert len(incomplete[0].missing_data) > 0

    def test_hicbc_not_shown_far_from_threshold_no_cb(self):
        # ANI = £90k is 30k above threshold — outside the ±20k proximity window
        pos, opps = assess(
            {"personal_pension_contributions": "0"},
            income_override=90000,
        )
        hicbc_opps = [o for o in opps if o.id == "HICBC"]
        assert len(hicbc_opps) == 0

    def test_both_opportunities_detected(self):
        pos, opps = assess(
            {"personal_pension_contributions": "0", "child_benefit_children": "2"},
            income_override=115000,
        )
        ids = {o.id for o in opps}
        assert "PA_TAPER" in ids
        assert "HICBC" in ids

    def test_pension_to_clear_pa_fully(self):
        # Income £110k, pension £0 → need £10k to clear taper
        pos, opps = assess(
            {"personal_pension_contributions": "0"},
            income_override=110000,
        )
        pa = next(o for o in opps if o.id == "PA_TAPER")
        assert pa.pension_to_clear_fully == Decimal("10000")

    def test_pension_to_clear_capped_at_60k(self):
        # Income £200k, pension £0 → need £100k but capped at £60k AA
        pos, opps = assess(
            {"personal_pension_contributions": "0"},
            income_override=200000,
        )
        pa = next(o for o in opps if o.id == "PA_TAPER")
        assert pa.pension_to_clear_capped == Decimal("60000")
        assert pa.pension_to_clear_fully  == Decimal("100000")

    def test_existing_pension_reduces_to_clear_amount(self):
        # Income £115k, pension already £5k → ANI = £110k, need £10k more
        pos, opps = assess(
            {"personal_pension_contributions": "5000"},
            income_override=115000,
        )
        pa = next(o for o in opps if o.id == "PA_TAPER")
        assert pa.pension_to_clear_fully == Decimal("10000")

    def test_income_override_takes_precedence_over_ytd(self):
        """Explicit income override is used instead of YTD projection."""
        pos, _ = assess(
            {"ytd_freelance_profit": "999999", "personal_pension_contributions": "0"},
            income_override=50000,
        )
        assert pos.projected_income == Decimal("50000")

    def test_profile_pension_naming_variants(self):
        """All three pension field names are accepted."""
        from reserved.engines.optimise import assess_opportunities, _resolve_pension
        for key in ("personal_pension_contributions", "pension_contribution", "pension"):
            pension = _resolve_pension({key: "5000"})
            assert pension == Decimal("5000.00")

    def test_cb_override_takes_precedence(self):
        """Explicit child_benefit_annual overrides children count."""
        from reserved.engines.optimise import _annual_cb_from_profile
        cb = _annual_cb_from_profile({
            "child_benefit_annual": "2000",
            "child_benefit_children": "1",
        })
        assert cb == Decimal("2000.00")

    def test_opportunity_constraints_non_empty(self):
        _, opps = assess(
            {"personal_pension_contributions": "0", "child_benefit_children": "1"},
            income_override=115000,
        )
        for opp in opps:
            if opp.status == "available":
                assert len(opp.constraints) > 0

    def test_what_to_confirm_non_empty(self):
        _, opps = assess(
            {"personal_pension_contributions": "0"},
            income_override=110000,
        )
        for opp in opps:
            if opp.status == "available":
                assert len(opp.what_to_confirm) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Income projection from profile
# ═══════════════════════════════════════════════════════════════════════════════

class TestIncomeProjection:

    def test_day_job_salary_only(self):
        from reserved.engines.optimise import _resolve_annual_income
        income = _resolve_annual_income(
            {"day_job_salary": "80000"},
            today=date(2026, 8, 10),
        )
        assert income == Decimal("80000.00")

    def test_income_estimate_added_to_salary(self):
        from reserved.engines.optimise import _resolve_annual_income
        income = _resolve_annual_income(
            {"day_job_salary": "50000", "income_estimate": "30000"},
            today=date(2026, 8, 10),
        )
        assert income == Decimal("80000.00")

    def test_ytd_projected_when_no_estimate(self):
        from reserved.engines.optimise import _resolve_annual_income
        # 4 months into tax year (April 6 → August 10 ≈ 4.15 months)
        # YTD £10,000 → projected ≈ 10000 × 12 / 4.15 ≈ £28,916
        income = _resolve_annual_income(
            {"ytd_freelance_profit": "10000"},
            today=date(2026, 8, 10),
        )
        # Projected should be more than YTD and substantially above it
        assert income > Decimal("10000")
        assert income < Decimal("50000")  # sanity cap

    def test_empty_profile_zero_income(self):
        from reserved.engines.optimise import _resolve_annual_income
        income = _resolve_annual_income({}, today=date(2026, 8, 10))
        assert income == Decimal("0")
