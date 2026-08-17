"""Purpose-aware HICBC annual-position integration boundary.

This module decides, for each customer purpose, whether a HICBC responsibility
result may contribute a figure and with what status.  It does **not** recalculate
or aggregate any tax; it gates an already computed :class:`HicbcResponsibilityResult`
by the existing uncertainty vocabulary so an ambiguous, uncertain or
insufficient result can never be promoted into an actionable total, reserve or
payment figure.

The purpose tiers are deliberately distinct:

- ``informational_rule``: a qualified point or bounded range may be shown, but it
  is never an actionable amount.
- ``personalised_estimate``: HICBC may enter the estimated total tax only when
  responsibility and Child Benefit evidence are adequate (determinate, no
  material uncertainty).
- ``reserve_guidance``: the same determinate requirement, but never when the
  effect is indeterminable or responsibility is ambiguous.
- ``payment``: never actionable in this package — payment integration has no
  independent approval yet, so HICBC is always excluded from a payment figure.

It never connects HICBC to PIS/VRP and never fabricates a point estimate.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .hicbc_partner import (
    RESPONSIBILITY_AMBIGUOUS,
    RESPONSIBILITY_INSUFFICIENT_FACTS,
    HicbcResponsibilityResult,
)

INFORMATIONAL = "informational_rule"
PERSONALISED_ESTIMATE = "personalised_estimate"
RESERVE_GUIDANCE = "reserve_guidance"
PAYMENT = "payment"

_PURPOSES = frozenset({INFORMATIONAL, PERSONALISED_ESTIMATE, RESERVE_GUIDANCE, PAYMENT})

# A determinate status carries an uncertainty-free point charge.
_DETERMINATE_STATUSES = frozenset({"calculated", "not_applicable"})


@dataclass(frozen=True)
class HicbcContribution:
    """The purpose-gated HICBC contribution derived from a responsibility result."""

    purpose: str
    included: bool                 # may enter this purpose's figure
    charge: Decimal | None         # determinate point charge (user's own HICBC)
    charge_low: Decimal | None     # bounded possible charge (informational only)
    charge_high: Decimal | None
    adequacy: str                  # adequate | adequate_with_material_uncertainty | bounded | excluded
    actionable: bool               # may inform reserve/payment guidance
    reason: str


def integrate_hicbc(result: HicbcResponsibilityResult, purpose: str) -> HicbcContribution:
    """Return the purpose-gated HICBC contribution for ``result``.

    ``result`` must already be computed; this function only gates it by purpose.
    """
    if purpose not in _PURPOSES:
        raise ValueError(f"Unknown HICBC integration purpose: {purpose!r}")

    status = result.calculation_status
    point = result.projected_user_hicbc
    low = result.possible_charge_low
    high = result.possible_charge_high
    determinate = status in _DETERMINATE_STATUSES and point is not None

    if purpose == INFORMATIONAL:
        if status == "insufficient_facts":
            return HicbcContribution(
                purpose=purpose,
                included=False,
                charge=None,
                charge_low=None,
                charge_high=None,
                adequacy="excluded",
                actionable=False,
                reason="Insufficient Child Benefit or partner facts to estimate HICBC.",
            )
        if status == "bounded_range":
            return HicbcContribution(
                purpose=purpose,
                included=True,
                charge=None,
                charge_low=low,
                charge_high=high,
                adequacy="bounded",
                actionable=False,
                reason="Responsibility is ambiguous; only a bounded possible charge is shown.",
            )
        if point is not None:
            adequacy = (
                "adequate"
                if status in _DETERMINATE_STATUSES
                else "adequate_with_material_uncertainty"
            )
            return HicbcContribution(
                purpose=purpose,
                included=True,
                charge=point,
                charge_low=point,
                charge_high=point,
                adequacy=adequacy,
                actionable=False,
                reason="Qualified informational HICBC estimate.",
            )
        return HicbcContribution(
            purpose=purpose,
            included=False,
            charge=None,
            charge_low=None,
            charge_high=None,
            adequacy="excluded",
            actionable=False,
            reason="HICBC cannot currently be estimated.",
        )

    # personalised_estimate / reserve_guidance / payment
    if not determinate:
        if status == "insufficient_facts":
            reason = "Insufficient facts; HICBC is excluded from the actionable total."
        elif result.responsibility_status == RESPONSIBILITY_AMBIGUOUS:
            reason = "Responsibility is ambiguous; HICBC is excluded from the actionable total."
        else:
            reason = "Material uncertainty; HICBC is excluded from the actionable total."
        return HicbcContribution(
            purpose=purpose,
            included=False,
            charge=None,
            charge_low=low,
            charge_high=high,
            adequacy="excluded",
            actionable=False,
            reason=reason,
        )

    # Determinate point available.
    if purpose == PAYMENT:
        return HicbcContribution(
            purpose=purpose,
            included=False,
            charge=point,
            charge_low=point,
            charge_high=point,
            adequacy="adequate",
            actionable=False,
            reason="HICBC payment integration is not independently approved; excluded from any payment figure.",
        )
    return HicbcContribution(
        purpose=purpose,
        included=True,
        charge=point,
        charge_low=point,
        charge_high=point,
        adequacy="adequate",
        actionable=(purpose == RESERVE_GUIDANCE),
        reason="Determinate HICBC responsibility; included in the estimate.",
    )
