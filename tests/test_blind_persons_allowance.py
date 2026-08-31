from decimal import Decimal

import pytest

from reserved.engines.integrated_annual_position import calculate_annual_position
from reserved.engines.internal_snapshot import decode_internal_snapshot, encode_internal_snapshot


EMPLOYMENT = {"employment_income": "30000"}
NO_BPA = {
    "blind_persons_allowance_entitled": False,
    "blind_persons_allowance_transferred_in": "0",
    "blind_persons_allowance_transferred_out": "0",
}
FULL_BPA = {
    "blind_persons_allowance_entitled": True,
    "blind_persons_allowance_transferred_in": "0",
    "blind_persons_allowance_transferred_out": "0",
}


@pytest.mark.engine
def test_full_2026_27_entitlement_is_3250_and_reduces_tax():
    result = calculate_annual_position({**EMPLOYMENT, **FULL_BPA})
    assert result.blind_persons_allowance == Decimal("3250.00")
    assert result.personal_allowance == Decimal("12570.00")
    assert result.income_tax_before_limitations == Decimal("2836.00")
    assert result.total_liability == Decimal("2836.00")
    assert result.calculation_status == "calculated"


@pytest.mark.engine
def test_explicit_no_entitlement_and_no_transfers_is_zero():
    result = calculate_annual_position({**EMPLOYMENT, **NO_BPA})
    assert result.blind_persons_allowance == Decimal("0.00")
    assert result.income_tax_before_limitations == Decimal("3486.00")
    assert result.total_liability == Decimal("3486.00")
    assert result.calculation_status == "calculated"


@pytest.mark.engine
def test_transfer_in_for_person_who_is_not_entitled():
    result = calculate_annual_position(
        {
            **EMPLOYMENT,
            "blind_persons_allowance_entitled": False,
            "blind_persons_allowance_transferred_in": "3250",
            "blind_persons_allowance_transferred_out": "0",
        }
    )
    assert result.blind_persons_allowance == Decimal("3250.00")
    assert result.income_tax_before_limitations == Decimal("2836.00")


@pytest.mark.engine
@pytest.mark.parametrize(
    "transferred_out, expected_allowance, expected_tax",
    [
        ("1000", "2250.00", "3036.00"),
        ("3250", "0.00", "3486.00"),
    ],
)
def test_partial_and_full_transfer_out(transferred_out, expected_allowance, expected_tax):
    result = calculate_annual_position(
        {
            **EMPLOYMENT,
            "blind_persons_allowance_entitled": True,
            "blind_persons_allowance_transferred_in": "0",
            "blind_persons_allowance_transferred_out": transferred_out,
        }
    )
    assert result.blind_persons_allowance == Decimal(expected_allowance)
    assert result.income_tax_before_limitations == Decimal(expected_tax)


@pytest.mark.engine
def test_wholly_absent_bpa_fact_group_is_insufficient_not_silently_zero():
    result = calculate_annual_position({**EMPLOYMENT})
    assert result.blind_persons_allowance is None
    assert result.calculation_status == "insufficient_facts"
    assert result.total_liability is None
    assert "blind_persons_allowance_facts_incomplete" in result.limitations
    # Useful pre-limitation component evidence is preserved.
    assert result.income_tax_before_limitations == Decimal("3486.00")
    assert result.personal_allowance == Decimal("12570.00")


@pytest.mark.engine
@pytest.mark.parametrize(
    "facts",
    [
        {"blind_persons_allowance_entitled": True},
        {"blind_persons_allowance_entitled": False},
        {"blind_persons_allowance_transferred_in": "1000"},
        {"blind_persons_allowance_transferred_out": "1000"},
        {
            "blind_persons_allowance_entitled": True,
            "blind_persons_allowance_transferred_in": "0",
        },
        {
            "blind_persons_allowance_entitled": True,
            "blind_persons_allowance_transferred_out": "0",
        },
        {
            "blind_persons_allowance_entitled": None,
            "blind_persons_allowance_transferred_in": "0",
            "blind_persons_allowance_transferred_out": "0",
        },
    ],
)
def test_partially_supplied_bpa_fact_group_is_insufficient_not_silently_zero(facts):
    result = calculate_annual_position({**EMPLOYMENT, **facts})
    assert result.blind_persons_allowance is None
    assert result.calculation_status == "insufficient_facts"
    assert result.total_liability is None
    assert "blind_persons_allowance_facts_incomplete" in result.limitations


@pytest.mark.engine
@pytest.mark.parametrize(
    "facts, match",
    [
        (
            {
                "blind_persons_allowance_entitled": False,
                "blind_persons_allowance_transferred_in": "0",
                "blind_persons_allowance_transferred_out": "1000",
            },
            "cannot be transferred out without own entitlement",
        ),
        (
            {
                "blind_persons_allowance_entitled": "maybe",
                "blind_persons_allowance_transferred_in": "0",
                "blind_persons_allowance_transferred_out": "0",
            },
            "must be a boolean",
        ),
        (
            {
                "blind_persons_allowance_entitled": True,
                "blind_persons_allowance_transferred_in": "0",
                "blind_persons_allowance_transferred_out": "-1",
            },
            "must be finite and non-negative",
        ),
        (
            {
                "blind_persons_allowance_entitled": True,
                "blind_persons_allowance_transferred_in": "0",
                "blind_persons_allowance_transferred_out": "not-money",
            },
            "must be numeric",
        ),
        (
            {
                "blind_persons_allowance_entitled": True,
                "blind_persons_allowance_transferred_in": "0",
                "blind_persons_allowance_transferred_out": "4000",
            },
            "exceeds the statutory allowance",
        ),
        (
            {
                "blind_persons_allowance_entitled": False,
                "blind_persons_allowance_transferred_in": "4000",
                "blind_persons_allowance_transferred_out": "0",
            },
            "exceeds the statutory allowance",
        ),
        (
            {
                "blind_persons_allowance_entitled": True,
                "blind_persons_allowance_transferred_in": "1000",
                "blind_persons_allowance_transferred_out": "1000",
            },
            "cannot be both transferred in and transferred out",
        ),
    ],
)
def test_malformed_negative_excessive_or_contradictory_transfer_facts_fail_closed(facts, match):
    with pytest.raises(ValueError, match=match):
        calculate_annual_position({**EMPLOYMENT, **facts})


@pytest.mark.engine
@pytest.mark.parametrize(
    "employment, expected_personal_allowance",
    [
        ("30000", "12570.00"),   # fully available ordinary Personal Allowance
        ("120000", "2570.00"),   # tapered ordinary Personal Allowance
        ("130000", "0.00"),      # zero ordinary Personal Allowance
    ],
)
def test_bpa_applies_without_tapering_personal_allowance(employment, expected_personal_allowance):
    result = calculate_annual_position(
        {"employment_income": employment, **FULL_BPA}
    )
    assert result.personal_allowance == Decimal(expected_personal_allowance)
    # BPA is never folded into, nor tapered alongside, ordinary Personal Allowance.
    assert result.blind_persons_allowance == Decimal("3250.00")


@pytest.mark.engine
def test_ordering_across_non_savings_savings_and_dividends():
    result = calculate_annual_position(
        {
            "employment_income": "12000",
            "savings_interest": "5000",
            "dividends": "2000",
            **FULL_BPA,
        }
    )
    # BPA is consumed first by non-savings income, then savings, then dividends.
    assert result.non_savings_tax == Decimal("0.00")
    assert result.savings_tax == Decimal("0.00")
    assert result.dividend_tax == Decimal("161.25")
    assert result.total_liability == Decimal("161.25")


@pytest.mark.engine
def test_bpa_does_not_change_ani_class_4_or_hicbc():
    with_bpa = calculate_annual_position(
        {
            "income_before_ras_pension": "70000",
            "gross_ras_pension": "10000",
            "annual_child_benefit": "1406.60",
            "taxpayer_is_higher_ani_partner": True,
            "payments_received_for_full_charge_period": True,
            **FULL_BPA,
        }
    )
    without_bpa = calculate_annual_position(
        {
            "income_before_ras_pension": "70000",
            "gross_ras_pension": "10000",
            "annual_child_benefit": "1406.60",
            "taxpayer_is_higher_ani_partner": True,
            "payments_received_for_full_charge_period": True,
            **NO_BPA,
        }
    )
    assert with_bpa.adjusted_net_income == without_bpa.adjusted_net_income == Decimal("60000.00")
    assert with_bpa.hicbc == without_bpa.hicbc == Decimal("0.00")

    trade = calculate_annual_position(
        {"sole_trade_profit": "20000", **FULL_BPA}
    )
    assert trade.class_4_ni == Decimal("445.80")


@pytest.mark.engine
def test_internal_contract_version_bumped_and_snapshot_round_trips():
    result = calculate_annual_position({**EMPLOYMENT, **FULL_BPA})
    assert result.contract_version == "reserved-estimate-envelope/1.1-internal"
    assert result.blind_persons_allowance == Decimal("3250.00")

    snapshot = encode_internal_snapshot(result)
    assert decode_internal_snapshot(snapshot) == result


@pytest.mark.engine
def test_insufficient_bpa_result_snapshot_round_trips():
    result = calculate_annual_position({**EMPLOYMENT})
    assert result.calculation_status == "insufficient_facts"
    assert result.total_liability is None
    snapshot = encode_internal_snapshot(result)
    assert decode_internal_snapshot(snapshot) == result


@pytest.mark.engine
def test_legacy_contract_version_is_deliberately_rejected():
    result = calculate_annual_position({**EMPLOYMENT, **FULL_BPA})
    snapshot = encode_internal_snapshot(result)
    snapshot["payload"]["fields"]["contract_version"] = "reserved-estimate-envelope/1.0-internal"
    with pytest.raises(ValueError, match="producer contract version"):
        decode_internal_snapshot(snapshot)
