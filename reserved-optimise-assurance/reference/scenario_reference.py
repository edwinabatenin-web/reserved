"""
Initiative 002 — End-to-end independent scenario reference.

Combines pa_taper, hicbc, and pension references to compute the same
before/after comparison as the product's ``model_pension_scenario``,
but using completely independent code.

Used in Gate 2 (archetypes) and Gate 3 (interactions) to validate
product outputs against an independent oracle.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .common import p, personal_allowance_ref, income_tax_total_ref, hicbc_ref


@dataclass(frozen=True)
class RefPosition:
    """Independent reference position."""
    projected_income:    Decimal
    pension:             Decimal
    ani:                 Decimal
    pa:                  Decimal
    income_tax:          Decimal
    hicbc:               Decimal
    annual_cb:           Decimal = Decimal("0")


@dataclass(frozen=True)
class RefScenario:
    """Independent reference scenario result."""
    additional_pension: Decimal
    before: RefPosition
    after:  RefPosition
    it_reduction:     Decimal
    hicbc_reduction:  Decimal
    total_benefit:    Decimal
    basic_rate_relief: Decimal   # HMRC adds to pension pot — NOT part of total_benefit


def ref_position(
    projected_income: Decimal,
    pension: Decimal,
    annual_cb: Decimal = Decimal("0"),
) -> RefPosition:
    """Calculate a position using only the reference implementations."""
    ani = max(Decimal("0"), projected_income - pension)
    pa  = personal_allowance_ref(ani)
    it  = income_tax_total_ref(projected_income, pension)
    hb  = hicbc_ref(ani, annual_cb)
    return RefPosition(
        projected_income = projected_income,
        pension          = pension,
        ani              = ani,
        pa               = pa,
        income_tax       = it,
        hicbc            = hb,
        annual_cb        = annual_cb,
    )


def ref_scenario(
    projected_income: Decimal,
    current_pension: Decimal,
    additional_pension: Decimal,
    annual_cb: Decimal = Decimal("0"),
) -> RefScenario:
    """Model a pension-contribution scenario using reference implementations."""
    before = ref_position(projected_income, current_pension, annual_cb)
    after  = ref_position(projected_income, current_pension + additional_pension, annual_cb)

    it_reduction    = p(max(Decimal("0"), before.income_tax - after.income_tax))
    hicbc_reduction = p(max(Decimal("0"), before.hicbc      - after.hicbc))
    total_benefit   = p(it_reduction + hicbc_reduction)
    brl             = p(additional_pension * Decimal("0.20"))

    return RefScenario(
        additional_pension = additional_pension,
        before             = before,
        after              = after,
        it_reduction       = it_reduction,
        hicbc_reduction    = hicbc_reduction,
        total_benefit      = total_benefit,
        basic_rate_relief  = brl,
    )
