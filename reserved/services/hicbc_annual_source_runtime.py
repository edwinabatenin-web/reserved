"""Non-production first-person manual annual source for HICBC only.

No storage, partner operands, source precedence, entitlement or annual-result
publication. The only returned operand is the engine-derived own ANI, used by
the named HICBC caller. A valid source is not approval of an annual tax total.
"""
from decimal import Decimal
import re

from reserved.engines.integrated_annual_position import calculate_annual_position


SCHEMA_VERSION = "hicbc-manual-annual/1"
_MONEY = re.compile(r"(?:0|[1-9][0-9]{0,7})(?:\.[0-9]{1,2})?\Z")
_AMOUNTS = (
    "employment_income", "sole_trade_profit", "savings_interest", "dividends",
    "uk_property_receipts", "uk_property_allowable_expenses",
    "brought_forward_uk_property_loss", "foreign_property_gross_receipts",
    "foreign_property_allowable_expenses", "gross_ras_pension",
    "residential_finance_costs", "foreign_tax_paid",
)
_REQUIRED = frozenset(_AMOUNTS) | {
    "schema_version", "tax_year", "country", "full_tax_year_including_known_future",
    "employment_basis", "uk_resident", "other_ani_adjustments",
}


def own_ani_from_manual_annual(payload, tax_year):
    """Validate complete canonical first-person facts; return own ANI or raise.

    Money is a bounded decimal string, never JSON float/bool. Null/unknown and
    missing groups are rejected, not zero-filled. Unsupported ANI adjustments
    require another evidence route; no tax formula is duplicated here.
    """
    if type(payload) is not dict or set(payload) != _REQUIRED:
        raise ValueError("Complete canonical annual facts are required")
    if (
        payload["schema_version"] != SCHEMA_VERSION
        or type(payload["tax_year"]) is not str
        or payload["tax_year"] != tax_year
        or tax_year != "2026/27"
        or type(payload["country"]) is not str
        or payload["country"] not in ("England", "Wales", "Northern Ireland")
        or payload["full_tax_year_including_known_future"] is not True
        or payload["uk_resident"] is not True
        or payload["employment_basis"] != "all_jobs_taxable_after_salary_sacrifice_and_net_pay"
        or payload["other_ani_adjustments"] != "none"
    ):
        raise ValueError("Annual scope, pension basis or evidence is unsupported")
    facts = {}
    for name in _AMOUNTS:
        value = payload[name]
        if type(value) is not str or _MONEY.fullmatch(value) is None:
            raise ValueError("An explicit bounded annual amount is required")
        facts[name] = value
    facts["country"] = payload["country"]
    facts["uk_resident"] = True
    # These are the stated meaning of this schema's residential finance field,
    # not an inference about relief. Foreign tax/finance relief affects total,
    # not ANI, and remains unresolved by this source.
    facts["individual_landlord"] = True
    facts["residential_property"] = True
    result = calculate_annual_position(facts, tax_year=tax_year)
    if set(result.unsupported_families) - {
        "residential_finance_cost_reduction", "foreign_tax_credit_relief",
    }:
        raise ValueError("Annual evidence does not establish own ANI")
    ani = result.adjusted_net_income
    if type(ani) is not Decimal or not ani.is_finite() or ani < 0:
        raise ValueError("Annual evidence does not establish own ANI")
    return ani
