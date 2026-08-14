"""
Allocation engine tests — Reserved 2026/27.

Verifies that gross invoices are correctly split into tax_reserve,
platform_fee, and safe_to_spend, and that the reconciliation invariant holds.
"""
from decimal import Decimal

import pytest

from reserved_engine.allocation import build_allocation

pytestmark = pytest.mark.engine


def D(s: str) -> Decimal:
    return Decimal(s)


# ── Basic split ───────────────────────────────────────────────────────────────

def test_basic_split_no_fee():
    r = build_allocation("1000.00", "200.00")
    assert r["gross_amount"]  == D("1000.00")
    assert r["tax_reserve"]   == D("200.00")
    assert r["platform_fee"]  == D("0.00")
    assert r["safe_to_spend"] == D("800.00")
    assert r["reconciles"]    is True


def test_basic_split_with_fee():
    # fee = 200 * 0.01 = 2.00; safe = 1000 − 200 − 2 = 798.00
    r = build_allocation("1000.00", "200.00", fee_rate="0.01")
    assert r["platform_fee"]  == D("2.00")
    assert r["safe_to_spend"] == D("798.00")
    assert r["reconciles"]    is True


def test_zero_liability_full_safe_to_spend():
    r = build_allocation("500.00", "0.00")
    assert r["tax_reserve"]   == D("0.00")
    assert r["safe_to_spend"] == D("500.00")
    assert r["reconciles"]    is True


# ── Reconciliation invariant ──────────────────────────────────────────────────

def test_reconciles_is_true_on_normal_inputs():
    r = build_allocation("4800.00", "1234.56")
    assert r["reconciles"] is True
    total = r["tax_reserve"] + r["platform_fee"] + r["safe_to_spend"]
    assert total == r["gross_amount"]


def test_reconciles_with_fractional_fee():
    # fee = 333.33 * 0.05 = 16.6665 → rounds to 16.67
    # safe = 1000.00 − 333.33 − 16.67 = 650.00
    r = build_allocation("1000.00", "333.33", fee_rate="0.05")
    assert r["reconciles"] is True
    assert r["tax_reserve"] + r["platform_fee"] + r["safe_to_spend"] == D("1000.00")


def test_reconciles_gross_exactly_equals_liability():
    # No room for safe_to_spend; safe = 0, reconciles = True
    r = build_allocation("500.00", "500.00")
    assert r["safe_to_spend"] == D("0.00")
    assert r["reconciles"] is True


def test_reconciles_false_when_liability_exceeds_gross():
    # liability > gross: safe_to_spend clamped to 0 and reconciles = False
    r = build_allocation("100.00", "200.00")
    assert r["safe_to_spend"] == D("0.00")
    assert r["reconciles"] is False


# ── Rounding edge cases ───────────────────────────────────────────────────────

def test_penny_inputs_reconcile():
    r = build_allocation("0.03", "0.01")
    assert r["reconciles"] is True
    assert r["safe_to_spend"] == D("0.02")


def test_large_amount_reconciles():
    r = build_allocation("100000.00", "45000.00", fee_rate="0.01")
    assert r["reconciles"] is True
    total = r["tax_reserve"] + r["platform_fee"] + r["safe_to_spend"]
    assert total == D("100000.00")


# ── Return types ──────────────────────────────────────────────────────────────

def test_all_monetary_values_are_decimal():
    r = build_allocation("1000", "300")
    for key in ("gross_amount", "tax_reserve", "platform_fee", "safe_to_spend"):
        assert isinstance(r[key], Decimal), f"{key} is not Decimal"


def test_reconciles_is_bool():
    r = build_allocation("1000", "300")
    assert isinstance(r["reconciles"], bool)


# ── Additional edge cases ─────────────────────────────────────────────────────

def test_fee_on_zero_liability_is_zero():
    """Fee is applied to the liability, not the gross.  When liability=£0
    the fee must also be £0 regardless of fee_rate."""
    r = build_allocation("1000.00", "0.00", fee_rate="0.01")
    assert r["platform_fee"]  == D("0.00")
    assert r["safe_to_spend"] == D("1000.00")
    assert r["reconciles"]    is True


def test_gross_exactly_equals_liability_plus_fee():
    """When gross = liability + fee, safe_to_spend = £0 and reconciles = True.

    liability = £950.00, fee_rate = 5 % → fee = £47.50
    gross = 950.00 + 47.50 = 997.50 → safe = £0.00, reconciles = True
    """
    r = build_allocation("997.50", "950.00", fee_rate="0.05")
    assert r["platform_fee"]  == D("47.50")
    assert r["safe_to_spend"] == D("0.00")
    assert r["reconciles"]    is True


def test_small_invoice_reconciles():
    """Smallest plausible invoice (£0.03) reconciles correctly."""
    r = build_allocation("0.03", "0.01")
    assert r["reconciles"]    is True
    assert r["safe_to_spend"] == D("0.02")
    assert r["tax_reserve"] + r["platform_fee"] + r["safe_to_spend"] == D("0.03")


def test_liability_slightly_exceeds_gross_reconciles_false():
    """When liability > gross, safe_to_spend = £0 and reconciles = False.

    This is the edge case where the invoice is smaller than its own tax estimate.
    """
    r = build_allocation("0.01", "100.00")
    assert r["safe_to_spend"] == D("0.00")
    assert r["reconciles"]    is False


def test_all_result_keys_present():
    """All documented result keys must be present in every allocation."""
    r = build_allocation("500.00", "100.00", fee_rate="0.02")
    for key in ("gross_amount", "tax_reserve", "platform_fee",
                "safe_to_spend", "reconciles"):
        assert key in r, f"Missing key: {key}"
