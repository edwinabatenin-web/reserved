"""Bounded internal HICBC before/after scenario comparison for 2026/27.

This component compares explicit facts. It does not recommend a pension,
establish pension-relief or annual-allowance eligibility, infer partner
responsibility, calculate a complete annual position, or connect to Optimise.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_FLOOR

from .tax_config import get_config


ZERO = Decimal("0")
PENNY = Decimal("0.01")


@dataclass(frozen=True)
class HicbcScenarioPoint:
    adjusted_net_income: Decimal
    charge_percentage: int
    hicbc: Decimal


@dataclass(frozen=True)
class InternalHicbcScenario:
    contract_version: str
    tax_year: str
    ruleset_version: str
    calculation_status: str
    annual_child_benefit: Decimal
    current: HicbcScenarioPoint | None
    scenario: HicbcScenarioPoint | None
    charge_difference: Decimal | None
    limitations: tuple[str, ...]
    prohibited_uses: tuple[str, ...]


def _amount(value, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be monetary, not boolean")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{name} must be numeric") from None
    if not result.is_finite() or result < ZERO:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def _point(ani: Decimal, benefit: Decimal, cfg: dict) -> HicbcScenarioPoint:
    rules = cfg["HICBC"]
    percentage = min(100, int(max(ZERO, ani - rules["lower_threshold"]) // rules["income_per_percentage_point"]))
    # ITEPA 2003 s681C staging: first round down the annual relevant Child
    # Benefit to whole pounds, then apply the whole complete-£200 percentage,
    # then round the resulting charge down to whole pounds.
    whole_pound_benefit = benefit.to_integral_value(rounding=ROUND_FLOOR)
    charge = (whole_pound_benefit * percentage / Decimal("100")).to_integral_value(
        rounding=ROUND_FLOOR
    )
    return HicbcScenarioPoint(ani.quantize(PENNY), percentage, charge.quantize(PENNY))


def compare_hicbc_scenario(
    *,
    current_adjusted_net_income,
    scenario_adjusted_net_income,
    annual_child_benefit,
    taxpayer_is_higher_ani_partner: bool | None,
    facts_complete_for_full_charge_period: bool,
    tax_year: str = "2026/27",
) -> InternalHicbcScenario:
    """Compare two explicit ANI values without deriving how either was reached."""
    if tax_year != "2026/27":
        raise ValueError("The bounded HICBC scenario supports 2026/27 only")
    cfg = get_config(tax_year)
    current_ani = _amount(current_adjusted_net_income, "current_adjusted_net_income")
    scenario_ani = _amount(scenario_adjusted_net_income, "scenario_adjusted_net_income")
    benefit = _amount(annual_child_benefit, "annual_child_benefit")
    limitations = (
        "informational_hicbc_component_comparison_only",
        "scenario_ani_is_supplied_not_derived",
        "pension_relief_and_annual_allowance_eligibility_not_assessed",
        "not_a_complete_annual_tax_position",
    )
    prohibited = ("customer_presentation", "recommendation", "reserve_guidance", "filing", "payment")
    if taxpayer_is_higher_ani_partner is not True:
        return InternalHicbcScenario(
            "reserved-internal-hicbc-scenario/1.0", tax_year, cfg["rules_version"],
            "insufficient_facts", benefit.quantize(PENNY), None, None, None,
            limitations + ("hicbc_responsibility_not_confirmed",), prohibited,
        )
    if facts_complete_for_full_charge_period is not True:
        return InternalHicbcScenario(
            "reserved-internal-hicbc-scenario/1.0", tax_year, cfg["rules_version"],
            "insufficient_facts", benefit.quantize(PENNY), None, None, None,
            limitations + ("child_benefit_charge_period_facts_incomplete",), prohibited,
        )
    current = _point(current_ani, benefit, cfg)
    scenario = _point(scenario_ani, benefit, cfg)
    return InternalHicbcScenario(
        "reserved-internal-hicbc-scenario/1.0", tax_year, cfg["rules_version"],
        "calculated", benefit.quantize(PENNY), current, scenario,
        (scenario.hicbc - current.hicbc).quantize(PENNY), limitations, prohibited,
    )
