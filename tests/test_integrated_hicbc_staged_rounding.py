"""Independent regressions for statutory HICBC rounding stages."""

from decimal import Decimal

import pytest

from reserved.engines.integrated_annual_position import calculate_annual_position


@pytest.mark.engine
@pytest.mark.parametrize(
    "ani,benefit,percentage,charge",
    [
        ("79800", "1406.99", 99, "1391.00"),
        ("75000", "1406.99", 75, "1054.00"),
        ("70000", "1406.99", 50, "703.00"),
        ("80000", "1406.99", 100, "1406.00"),
        ("80000", "1407.00", 100, "1407.00"),
    ],
)
def test_relevant_benefit_is_floored_before_percentage_and_final_charge(
    ani, benefit, percentage, charge
):
    result = calculate_annual_position({
        "adjusted_net_income": ani,
        "annual_child_benefit": benefit,
    })
    assert result.hicbc_charge_percentage == percentage
    assert result.hicbc == Decimal(charge)
