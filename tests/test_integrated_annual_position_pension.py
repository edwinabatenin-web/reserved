"""F1 regression tests: PTM056120 pension band extension in the full-position engine.

A gross Relief-at-Source pension contribution extends BOTH the basic-rate limit
and the higher-rate limit (the additional-rate threshold) by the gross amount
(HMRC Pensions Tax Manual PTM056120).  These tests pin the full-position engine
(``integrated_annual_position.py``) to the same treatment as the corrected
incremental engine (``income_tax.py``).

Expected values below are derived from first principles (band widths and the
configured rates), not copied from production output.
"""

from decimal import Decimal

from reserved.engines.integrated_annual_position import calculate_annual_position


def test_pension_extends_both_limits_rw3_pen_005_equivalent():
    # income £125,141, gross RaS £1 -> ANI £125,140 -> PA £0.
    # extended basic-rate limit £37,701; extended higher-rate limit £125,141.
    # £37,701 @ 20% = £7,540.20; £87,440 @ 40% = £34,976.00; no 45% slice.
    result = calculate_annual_position(
        {"employment_income": "125141", "gross_ras_pension": "1"}
    )
    assert result.adjusted_net_income == Decimal("125140.00")
    assert result.personal_allowance == Decimal("0.00")
    assert result.non_savings_tax == Decimal("42516.20")


def test_pension_extends_both_limits_large_contribution():
    # £200,000 income, £80,000 gross RaS -> ANI £120,000 -> PA £2,570.
    # This is an Income Tax example only: it assumes the full contribution
    # qualifies for Income Tax relief and does not establish pension annual
    # allowance, carry-forward, or relevant-earnings eligibility.
    # extended basic-rate limit £117,700; extended higher-rate limit £205,140.
    # £117,700 @ 20% = £23,540.00; £79,730 @ 40% = £31,892.00; total £55,432.00.
    result = calculate_annual_position(
        {"employment_income": "200000", "gross_ras_pension": "80000"}
    )
    assert result.personal_allowance == Decimal("2570.00")
    assert result.non_savings_tax == Decimal("55432.00")


def test_extended_additional_rate_boundary_below_at_above():
    # Extended higher-rate limit = £125,140 + £10,000 = £135,140.
    # Just below / at / just above that boundary with a £10,000 gross RaS.
    cases = [
        ("135139", "44515.40"),  # below: no 45% slice
        ("135140", "44516.00"),  # at:    no 45% slice
        ("135141", "44516.45"),  # above: £1 @ 45%
    ]
    for income, expected in cases:
        result = calculate_annual_position(
            {"employment_income": income, "gross_ras_pension": "10000"}
        )
        assert result.non_savings_tax == Decimal(expected), income


def test_pension_extension_applies_to_dividend_higher_rate_limit():
    # £120,000 employment + £30,000 dividends, £10,000 gross RaS.
    # Extended limits: basic £47,700; higher-rate £135,140.
    # Non-savings: £47,700 @ 20% = £9,540.00; £72,300 @ 40% = £28,920.00 -> £38,460.00.
    # Dividends (£29,500 after £500 allowance) stacked from cursor £120,500:
    #   £14,640 @ 35.75% = £5,233.80; £14,860 @ 39.35% = £5,847.41 -> £11,081.21.
    result = calculate_annual_position(
        {"employment_income": "120000", "gross_ras_pension": "10000", "dividends": "30000"}
    )
    assert result.non_savings_tax == Decimal("38460.00")
    assert result.dividend_tax == Decimal("11081.21")
    assert result.income_tax_before_limitations == Decimal("49541.21")
