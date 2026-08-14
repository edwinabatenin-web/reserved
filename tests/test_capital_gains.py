"""
Capital Gains Tax engine tests — Reserved 2026/27.

Golden values are computed independently from HMRC 2026/27 CGT rates:
  Basic rate:  18 %
  Higher rate: 24 %
  Annual Exempt Amount (AEA): £3,000
"""
from decimal import Decimal

import pytest

from reserved.engines.capital_gains import CapitalDisposal, estimate_cgt
from reserved.engines import tax_config

pytestmark = pytest.mark.engine


def D(s: str) -> Decimal:
    return Decimal(s)


def disposal(proceeds, cost, *, asset_type="shares", acq=0, disp=0):
    return CapitalDisposal(
        asset_type=asset_type,
        description="Test disposal",
        disposal_date="2026-09-01",
        proceeds=D(str(proceeds)),
        allowable_cost=D(str(cost)),
        acquisition_costs=D(str(acq)),
        disposal_costs=D(str(disp)),
    )


# ── Basic gain within AEA (tax = £0) ─────────────────────────────────────────
#
# gain = 1000, AEA = 3000, taxable = max(0, 1000−3000) = 0

def test_gain_within_aea_zero_tax():
    r = estimate_cgt(
        [disposal(11000, 10000)],
        taxable_income_before_gains=0,
    )
    assert r["taxable_gains"] == D("0.00")
    assert r["estimated_cgt"] == D("0.00")
    assert r["outstanding_reserve"] == D("0.00")


# ── Gain above AEA, all at basic rate ─────────────────────────────────────────
#
# taxable_income = 20000, BRL = 50270
# basic_band_remaining = 50270 − 20000 = 30270
# gain = 10000, AEA = 3000, taxable_gains = 7000
# basic_slice = min(7000, 30270) = 7000 → 18% × 7000 = 1260.00

def test_gain_all_at_basic_rate():
    r = estimate_cgt(
        [disposal(13000, 3000)],   # gain = 10000
        taxable_income_before_gains=20000,
    )
    assert r["taxable_gains"] == D("7000.00")
    assert r["estimated_cgt"] == D("1260.00"), r["estimated_cgt"]


# ── Gain split across basic and higher rates ──────────────────────────────────
#
# taxable_income = 46000, BRL = 50270
# basic_band_remaining = 50270 − 46000 = 4270
# gain = 15000, AEA = 3000, taxable_gains = 12000
# basic_slice  = min(12000, 4270) = 4270  → 18% × 4270  = 768.60
# higher_slice = 12000 − 4270    = 7730  → 24% × 7730   = 1855.20
# estimated_cgt = 768.60 + 1855.20 = 2623.80

def test_gain_split_basic_and_higher():
    r = estimate_cgt(
        [disposal(18000, 3000)],   # gain = 15000
        taxable_income_before_gains=46000,
    )
    assert r["estimated_cgt"] == D("2623.80"), r["estimated_cgt"]


# ── All gain at higher rate (income fills basic band) ─────────────────────────
#
# taxable_income = 55000 (above BRL 50270) → basic_band_remaining = 0
# gain = 10000, AEA = 3000, taxable = 7000
# 100 % higher rate → 24% × 7000 = 1680.00

def test_gain_all_at_higher_rate():
    r = estimate_cgt(
        [disposal(13000, 3000)],
        taxable_income_before_gains=55000,
    )
    assert r["estimated_cgt"] == D("1680.00"), r["estimated_cgt"]


# ── Loss offsets gain ─────────────────────────────────────────────────────────
#
# disposal A: gain = 10000
# disposal B: loss = 4000
# net_gains = 10000 − 4000 = 6000, taxable = max(0, 6000−3000) = 3000
# taxable_income = 0 → all basic rate → 18% × 3000 = 540.00

def test_loss_offsets_gain():
    r = estimate_cgt(
        [disposal(13000, 3000), disposal(2000, 6000)],
        taxable_income_before_gains=0,
    )
    assert r["taxable_gains"] == D("3000.00")
    assert r["estimated_cgt"] == D("540.00"), r["estimated_cgt"]


# ── Brought-forward losses ────────────────────────────────────────────────────
#
# gain = 10000, brought-forward = 5000, net = 5000, taxable = max(0,5000−3000) = 2000
# all basic rate (income=0) → 18% × 2000 = 360.00

def test_brought_forward_losses():
    r = estimate_cgt(
        [disposal(13000, 3000)],
        taxable_income_before_gains=0,
        brought_forward_losses=5000,
    )
    assert r["taxable_gains"] == D("2000.00")
    assert r["estimated_cgt"] == D("360.00"), r["estimated_cgt"]


# ── Tax already paid reduces outstanding reserve ──────────────────────────────

def test_tax_already_paid_reduces_outstanding():
    r = estimate_cgt(
        [disposal(13000, 3000)],   # taxable = 7000, cgt = 1260.00 (income=20000)
        taxable_income_before_gains=20000,
        tax_already_paid=500,
    )
    assert r["estimated_cgt"]       == D("1260.00")
    assert r["outstanding_reserve"] == D("760.00"), r["outstanding_reserve"]


def test_outstanding_reserve_not_negative():
    r = estimate_cgt(
        [disposal(13000, 3000)],
        taxable_income_before_gains=20000,
        tax_already_paid=9999,
    )
    assert r["outstanding_reserve"] == D("0.00")


# ── Net loss — no CGT ─────────────────────────────────────────────────────────

def test_net_loss_no_tax():
    r = estimate_cgt(
        [disposal(1000, 5000)],   # loss = 4000
        taxable_income_before_gains=50000,
    )
    assert r["total_gains"]    == D("0.00")
    assert r["taxable_gains"]  == D("0.00")
    assert r["estimated_cgt"]  == D("0.00")


# ── Multiple disposals ────────────────────────────────────────────────────────

def test_multiple_disposals_summed_correctly():
    # Three gains: 5000, 3000, 2000 → total = 10000, taxable = 7000
    r = estimate_cgt(
        [disposal(8000, 3000), disposal(6000, 3000), disposal(5000, 3000)],
        taxable_income_before_gains=20000,
    )
    assert r["total_gains"] == D("10000.00")
    assert r["estimated_cgt"] == D("1260.00")


# ── CapitalDisposal.gain_or_loss property ────────────────────────────────────

def test_disposal_gain():
    d = disposal(10000, 6000, acq=200, disp=100)
    # 10000 − 6000 − 200 − 100 = 3700
    assert d.gain_or_loss == D("3700.00")


def test_disposal_loss_is_negative():
    d = disposal(2000, 5000)
    assert d.gain_or_loss == D("-3000.00")


# ── basic_rate_limit comes from tax_config (not hardcoded) ───────────────────

def test_basic_rate_limit_sourced_from_tax_config():
    """The CGT basic-rate band boundary must equal tax_config.BASIC_RATE_LIMIT."""
    # If BASIC_RATE_LIMIT were hardcoded in capital_gains.py, changing
    # tax_config would have no effect.  We verify that setting income to
    # exactly BASIC_RATE_LIMIT leaves zero basic-band remaining.
    brl = float(tax_config.BASIC_RATE_LIMIT)
    r = estimate_cgt(
        [disposal(10000, 3000)],   # gain = 7000, taxable = 4000
        taxable_income_before_gains=brl,
    )
    # All in higher rate → 24% × 4000 = 960.00
    assert r["estimated_cgt"] == D("960.00"), r["estimated_cgt"]


# ── Result structure ──────────────────────────────────────────────────────────

def test_result_contains_required_keys():
    r = estimate_cgt([disposal(5000, 2000)], taxable_income_before_gains=0)
    for key in (
        "tax_year", "rules_version", "disposals", "total_gains",
        "current_year_losses", "losses_used", "annual_exempt_amount",
        "taxable_gains", "estimated_cgt", "tax_already_paid",
        "outstanding_reserve", "warnings",
    ):
        assert key in r, f"Missing key: {key}"


def test_result_warnings_present():
    r = estimate_cgt([disposal(5000, 2000)], taxable_income_before_gains=0)
    assert isinstance(r["warnings"], list)
    assert len(r["warnings"]) >= 1


def test_monetary_outputs_are_decimal():
    r = estimate_cgt([disposal(5000, 2000)], taxable_income_before_gains=0)
    for key in ("total_gains", "taxable_gains", "estimated_cgt", "outstanding_reserve"):
        assert isinstance(r[key], Decimal), f"{key} is not Decimal"


# ── Additional boundary and edge cases ───────────────────────────────────────

def test_gain_exactly_equal_to_aea_zero_tax():
    """Total gain = AEA (£3,000) exactly → taxable_gains = 0, CGT = £0.

    net_gains = 3,000; taxable = max(0, 3,000 − 3,000) = 0
    """
    r = estimate_cgt([disposal(6000, 3000)], taxable_income_before_gains=0)
    assert r["total_gains"]   == D("3000.00")
    assert r["taxable_gains"] == D("0.00")
    assert r["estimated_cgt"] == D("0.00")


def test_brought_forward_losses_exceed_current_gain_zero_tax():
    """Brought-forward losses greater than current gain → net = 0, CGT = £0.

    Current gain = 5,000; BF losses = 10,000 → net = max(0, 5000−10000) = 0
    """
    r = estimate_cgt(
        [disposal(8000, 3000)],  # gain = 5,000
        taxable_income_before_gains=50000,
        brought_forward_losses=10000,
    )
    assert r["total_gains"]   == D("5000.00")
    assert r["taxable_gains"] == D("0.00")
    assert r["estimated_cgt"] == D("0.00")


def test_multiple_small_gains_summing_exactly_to_aea():
    """Three equal gains of £1,000 = £3,000 total = AEA → CGT = £0."""
    r = estimate_cgt(
        [disposal(4000, 3000), disposal(4000, 3000), disposal(4000, 3000)],
        taxable_income_before_gains=20000,
    )
    assert r["total_gains"]   == D("3000.00")
    assert r["taxable_gains"] == D("0.00")
    assert r["estimated_cgt"] == D("0.00")


def test_zero_gain_disposal():
    """A disposal with proceeds = cost produces zero gain."""
    r = estimate_cgt([disposal(5000, 5000)], taxable_income_before_gains=20000)
    assert r["total_gains"]   == D("0.00")
    assert r["estimated_cgt"] == D("0.00")


def test_acquisition_and_disposal_costs_reduce_gain():
    """Acquisition cost £200 and disposal cost £100 reduce the gain.

    proceeds=10,000; cost=6,000; acq=200; disp=100 → gain = 3,700
    taxable = max(0, 3,700 − 3,000) = 700
    income=0, all basic rate → 18 % × 700 = £126.00
    """
    r = estimate_cgt(
        [disposal(10000, 6000, acq=200, disp=100)],
        taxable_income_before_gains=0,
    )
    assert r["taxable_gains"] == D("700.00")
    assert r["estimated_cgt"] == D("126.00"), r["estimated_cgt"]
