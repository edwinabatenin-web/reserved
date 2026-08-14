"""
Capital Gains Tax estimator — multi-year, versioned configuration.

Supported
---------
  - Shares, cryptoassets, and other chargeable assets
  - Annual Exempt Amount offset
  - Brought-forward losses
  - Basic-rate vs higher-rate CGT split based on taxable income remaining
    in the basic-rate band
  - Multi-year support: pass ``tax_year="2025/26"`` or ``"2026/27"``
    (default) to use the correct rates and thresholds for that year

Out of scope (noted as warnings in the result)
----------------------------------------------
  - Share pooling and same-day / 30-day matching rules
  - Residential property disposals (subject to 60-day reporting)
  - Business Asset Disposal Relief (BADR) and Investors' Relief
  - Carried-interest rules
"""
from dataclasses import dataclass, asdict
from decimal import Decimal
from typing import Iterable

from . import capital_gains_config
from . import tax_config
from .utils import money


@dataclass(frozen=True)
class CapitalDisposal:
    """A single chargeable disposal for CGT purposes."""

    asset_type: str          # must be a key in SUPPORTED_ASSET_TYPES
    description: str
    disposal_date: str       # ISO-8601 string; validated by the caller
    proceeds: Decimal
    allowable_cost: Decimal
    acquisition_costs: Decimal = Decimal("0")
    disposal_costs: Decimal = Decimal("0")

    @property
    def gain_or_loss(self) -> Decimal:
        """Net gain (positive) or loss (negative) on this disposal."""
        return money(
            self.proceeds
            - self.allowable_cost
            - self.acquisition_costs
            - self.disposal_costs
        )


def estimate_cgt(
    disposals: Iterable[CapitalDisposal],
    *,
    taxable_income_before_gains,
    brought_forward_losses=0,
    tax_already_paid=0,
    tax_year: str = "2026/27",
) -> dict:
    """Estimate CGT liability for a set of disposals.

    Parameters
    ----------
    disposals:
        Iterable of :class:`CapitalDisposal` objects.
    taxable_income_before_gains:
        Total taxable income (after Personal Allowance) before adding gains —
        used to determine how much of the basic-rate band remains.
    brought_forward_losses:
        Unused capital losses carried forward from prior tax years.
    tax_already_paid:
        CGT already paid on account this year (e.g. via 60-day property
        reports), deducted from the outstanding reserve.
    tax_year:
        HMRC tax year string, e.g. ``"2026/27"`` (default) or ``"2025/26"``.
        Must be a key in ``capital_gains_config.SUPPORTED_CGT_TAX_YEARS``.

    Returns
    -------
    dict
        Full CGT breakdown including ``estimated_cgt`` (total estimated
        liability) and ``outstanding_reserve`` (liability less tax already
        paid).  All monetary values are :class:`decimal.Decimal` rounded to
        the nearest penny.

    Raises
    ------
    ValueError
        If ``tax_year`` is not in ``capital_gains_config.SUPPORTED_CGT_TAX_YEARS``.
    """
    # ── Load versioned configuration ──────────────────────────────────────────
    # CGT rates (AEA, basic/higher) come from the CGT-specific registry.
    # The basic-rate limit used to split basic/higher CGT slices comes from
    # the income-tax registry — both registries must be queried for the same
    # tax year so the band boundary is always consistent.
    cgt_cfg = capital_gains_config.get_cgt_config(tax_year)
    it_cfg  = tax_config.get_config(tax_year)

    # ── Gain/loss aggregation ─────────────────────────────────────────────────
    disposals = list(disposals)
    total_gains = money(
        sum((max(d.gain_or_loss, Decimal("0")) for d in disposals), Decimal("0"))
    )
    current_losses = money(
        sum((abs(min(d.gain_or_loss, Decimal("0"))) for d in disposals), Decimal("0"))
    )
    losses      = money(current_losses + money(brought_forward_losses))
    net_gains   = money(max(Decimal("0"), total_gains - losses))
    taxable_gains = money(max(Decimal("0"), net_gains - cgt_cfg["ANNUAL_EXEMPT_AMOUNT"]))

    # ── Basic/higher rate split ───────────────────────────────────────────────
    # Gains are first charged at the basic rate to the extent the taxpayer has
    # basic-rate band remaining after their taxable income.
    taxable_income       = money(taxable_income_before_gains)
    basic_band_remaining = money(
        max(Decimal("0"), it_cfg["BASIC_RATE_LIMIT"] - taxable_income)
    )
    basic_slice  = money(min(taxable_gains, basic_band_remaining))
    higher_slice = money(max(Decimal("0"), taxable_gains - basic_slice))

    # ── Tax calculation ───────────────────────────────────────────────────────
    estimated_tax = money(
        basic_slice  * cgt_cfg["BASIC_RATE"]
        + higher_slice * cgt_cfg["HIGHER_RATE"]
    )
    outstanding = money(max(Decimal("0"), estimated_tax - money(tax_already_paid)))

    return {
        "tax_year":             cgt_cfg["tax_year"],
        "rules_version":        cgt_cfg["rules_version"],
        "disposals": [
            {**asdict(d), "gain_or_loss": d.gain_or_loss}
            for d in disposals
        ],
        "total_gains":          total_gains,
        "current_year_losses":  current_losses,
        "losses_used":          money(min(losses, total_gains)),
        "annual_exempt_amount": cgt_cfg["ANNUAL_EXEMPT_AMOUNT"],
        "taxable_gains":        taxable_gains,
        "estimated_cgt":        estimated_tax,
        "tax_already_paid":     money(tax_already_paid),
        "outstanding_reserve":  outstanding,
        "warnings": [
            "This preview does not yet perform share pooling, same-day or 30-day matching.",
            "Residential property disposals use different rates; not modelled here.",
            "BADR and Investors' Relief are not yet implemented.",
            "Complex disposals should be reviewed by a qualified tax adviser.",
        ],
    }
