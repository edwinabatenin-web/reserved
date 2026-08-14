from decimal import Decimal

import pytest

from reserved.engines.internal_hicbc_scenario import compare_hicbc_scenario


def compare(current, scenario, benefit="1406.60", **kwargs):
    return compare_hicbc_scenario(
        current_adjusted_net_income=current,
        scenario_adjusted_net_income=scenario,
        annual_child_benefit=benefit,
        taxpayer_is_higher_ani_partner=kwargs.pop("taxpayer_is_higher_ani_partner", True),
        facts_complete_for_full_charge_period=kwargs.pop("facts_complete_for_full_charge_period", True),
        **kwargs,
    )


@pytest.mark.parametrize(
    "ani,percentage,charge",
    [
        ("59999", 0, "0.00"),
        ("60000", 0, "0.00"),
        ("60199", 0, "0.00"),
        ("60200", 1, "14.00"),
        ("79800", 99, "1391.00"),
        ("79999", 99, "1391.00"),
        ("80000", 100, "1406.00"),
        ("80200", 100, "1406.00"),
    ],
)
def test_independently_approved_step_cap_and_whole_pound_literals(ani, percentage, charge):
    result = compare(ani, ani)
    assert result.current.charge_percentage == percentage
    assert result.current.hicbc == Decimal(charge)


def test_explicit_ani_scenario_compares_approved_pension_effect_without_recommending_it():
    result = compare("70000", "60000")
    assert result.current.hicbc == Decimal("703.00")
    assert result.scenario.hicbc == Decimal("0.00")
    assert result.charge_difference == Decimal("-703.00")
    assert "scenario_ani_is_supplied_not_derived" in result.limitations
    assert "pension_relief_and_annual_allowance_eligibility_not_assessed" in result.limitations
    assert "recommendation" in result.prohibited_uses


def test_additional_child_benefit_literal_uses_same_approved_rounding():
    result = compare("70000", "70000", benefit="2337.40")
    assert result.current.charge_percentage == 50
    assert result.current.hicbc == Decimal("1168.00")


def test_statutory_staging_floors_benefit_before_percentage_counterexample():
    result = compare("79800", "79800", benefit="1406.99")
    assert result.current.charge_percentage == 99
    assert result.current.hicbc == Decimal("1391.00")


@pytest.mark.parametrize(
    "ani,benefit,expected",
    [
        ("60200", "99.99", "0.00"),
        ("60200", "100.00", "1.00"),
        ("70000", "1406.99", "703.00"),
        ("80000", "1406.99", "1406.00"),
        ("80000", "1407.00", "1407.00"),
    ],
)
def test_benefit_floor_percentage_and_final_floor_are_distinct_stages(ani, benefit, expected):
    result = compare(ani, ani, benefit=benefit)
    assert result.current.hicbc == Decimal(expected)


@pytest.mark.parametrize(
    "kwargs,limitation",
    [
        ({"taxpayer_is_higher_ani_partner": None}, "hicbc_responsibility_not_confirmed"),
        ({"taxpayer_is_higher_ani_partner": False}, "hicbc_responsibility_not_confirmed"),
        ({"facts_complete_for_full_charge_period": False}, "child_benefit_charge_period_facts_incomplete"),
    ],
)
def test_responsibility_and_charge_period_facts_fail_closed(kwargs, limitation):
    result = compare("70000", "60000", **kwargs)
    assert result.calculation_status == "insufficient_facts"
    assert result.current is None and result.scenario is None and result.charge_difference is None
    assert limitation in result.limitations


@pytest.mark.parametrize("value", [True, "-1", "NaN", "Infinity", "bad"])
def test_invalid_explicit_amounts_fail_closed(value):
    with pytest.raises(ValueError):
        compare(value, "60000")


def test_other_tax_year_is_not_inferred():
    with pytest.raises(ValueError, match="2026/27 only"):
        compare("70000", "60000", tax_year="2025/26")
