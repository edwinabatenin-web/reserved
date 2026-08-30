from decimal import Decimal

import pytest

from reserved.engines.integrated_annual_position import calculate_annual_position


@pytest.mark.engine
@pytest.mark.parametrize(
    "facts, expected",
    [
        ({"employment_income": "15570", "savings_interest": "7000"}, ("600.00", "800.00", "0.00", "1400.00")),
        ({"employment_income": "12571", "savings_interest": "6000"}, ("0.20", "0.20", "0.00", "0.40")),
        ({"employment_income": "49770", "savings_interest": "1000"}, ("7440.00", "200.00", "0.00", "7640.00")),
        ({"employment_income": "125140", "savings_interest": "1000"}, ("42516.00", "450.00", "0.00", "42966.00")),
        ({"employment_income": "45000", "dividends": "5000"}, ("6486.00", "0.00", "483.75", "6969.75")),
        ({"employment_income": "50000", "dividends": "1000"}, ("7486.00", "0.00", "178.75", "7664.75")),
        ({"employment_income": "49498", "dividends": "1500"}, ("7385.60", "0.00", "289.50", "7675.10")),
        (
            {"employment_income": "30000", "sole_trade_profit": "10000", "savings_interest": "2000", "dividends": "5000"},
            ("5486.00", "200.00", "483.75", "6169.75"),
        ),
    ],
)
def test_approved_mixed_income_ordering_literals(facts, expected):
    result = calculate_annual_position(facts)
    assert (result.non_savings_tax, result.savings_tax, result.dividend_tax, result.income_tax_before_limitations) == tuple(
        Decimal(value) for value in expected
    )


def test_ani_tapers_personal_allowance_and_class_4_is_trade_only():
    result = calculate_annual_position({"employment_income": "99500", "savings_interest": "1000"})
    assert result.adjusted_net_income == Decimal("100500.00")
    assert result.personal_allowance == Decimal("12320.00")
    assert result.personal_savings_allowance == Decimal("500.00")
    assert result.income_tax_before_limitations == Decimal("27532.00")

    property_result = calculate_annual_position({"employment_income": "30000", "uk_property_profit": "10000"})
    assert property_result.class_4_ni == Decimal("0.00")
    trade_result = calculate_annual_position({"sole_trade_profit": "20000"})
    assert trade_result.class_4_ni == Decimal("445.80")


def test_uk_property_loss_is_carried_forward_not_set_against_employment():
    result = calculate_annual_position(
        {"employment_income": "30000", "uk_property_receipts": "10000", "uk_property_allowable_expenses": "12000"}
    )
    assert result.uk_property_profit == Decimal("0.00")
    assert result.uk_property_loss_to_carry_forward == Decimal("2000.00")
    assert result.non_savings_tax == Decimal("3486.00")


def test_foreign_property_is_pre_credit_and_fails_closed_on_residence_or_ftcr():
    complete = calculate_annual_position(
        {"uk_resident": True, "employment_income": "30000", "foreign_property_profit": "10000", "foreign_tax_paid": "0"}
    )
    assert complete.income_tax_before_limitations == Decimal("5486.00")
    assert complete.total_liability == Decimal("5486.00")

    credit = calculate_annual_position(
        {"uk_resident": True, "employment_income": "30000", "foreign_property_profit": "10000", "foreign_tax_paid": "1500"}
    )
    assert credit.income_tax_before_limitations == Decimal("5486.00")
    assert credit.total_liability is None
    assert credit.unsupported_families == ("foreign_tax_credit_relief",)

    unknown = calculate_annual_position({"uk_resident": None, "foreign_property_profit": "10000"})
    assert unknown.total_liability is None
    assert "residence_facts_incomplete" in unknown.limitations


def test_residential_finance_costs_are_recorded_as_an_unsupported_limitation():
    result = calculate_annual_position(
        {
            "individual_landlord": True,
            "residential_property": True,
            "employment_income": "30000",
            "rental_income": "10000",
            "non_finance_allowable_expenses": "2000",
            "residential_finance_costs": "3000",
        }
    )
    assert result.uk_property_profit == Decimal("8000.00")
    assert result.income_tax_before_limitations == Decimal("5086.00")
    assert result.total_liability is None
    assert result.unsupported_families == ("residential_finance_cost_reduction",)


@pytest.mark.parametrize(
    "ani, expected",
    [("60199", "0.00"), ("60200", "14.00"), ("79999", "1391.00"), ("80000", "1406.00")],
)
def test_hicbc_uses_complete_200_steps_and_whole_pound_charge(ani, expected):
    result = calculate_annual_position({
        "adjusted_net_income": ani,
        "annual_child_benefit": "1406.60",
        "taxpayer_is_higher_ani_partner": True,
        "payments_received_for_full_charge_period": True,
    })
    assert result.hicbc == Decimal(expected)


def test_hicbc_calculates_only_with_sufficient_payment_and_responsibility_facts():
    household = calculate_annual_position(
        {
            "person_adjusted_net_income": "70000",
            "partner_adjusted_net_income": "75000",
            "annual_child_benefit_received_by_person": "1406.60",
            "payments_received_for_full_charge_period": True,
        }
    )
    assert household.hicbc == Decimal("0")
    assert household.hicbc_household_charge == Decimal("1054.00")
    assert household.hicbc_charge_percentage == 75
    assert household.hicbc_liable_person == "partner"
    assert "hicbc_liability_belongs_to_higher_ani_partner" in household.limitations

    incomplete = calculate_annual_position({"adjusted_net_income": "70000", "child_benefit_applicable": True})
    assert incomplete.hicbc is None
    assert incomplete.total_liability is None
    assert incomplete.unsupported_families == ("hicbc",)


def test_hicbc_ani_can_be_derived_from_explicit_pre_pension_income():
    result = calculate_annual_position(
        {
            "income_before_ras_pension": "70000",
            "gross_ras_pension": "10000",
            "annual_child_benefit": "1406.60",
            "taxpayer_is_higher_ani_partner": True,
            "payments_received_for_full_charge_period": True,
        }
    )
    assert result.hicbc_charge_percentage == 0
    assert result.hicbc == Decimal("0.00")


def test_boundary_never_claims_paye_reconciliation_or_student_loan_support():
    result = calculate_annual_position({"employment_income": "30000"})
    assert result.contract_version == "reserved-estimate-envelope/1.0-internal"
    assert result.total_liability == Decimal("3486.00")
    assert "paye_reconciliation_not_performed" in result.limitations
    assert "student_loan_not_calculated" in result.limitations


@pytest.mark.parametrize("value", ["-1", "NaN", "Infinity", "not-a-number"])
def test_invalid_monetary_facts_fail_closed(value):
    with pytest.raises(ValueError):
        calculate_annual_position({"employment_income": value})


# Hand-written literal audit cases. These values are intentionally repeated
# here: production never reads the assurance fixture pack, and expectations
# are not generated from engine output.
@pytest.mark.engine
@pytest.mark.parametrize(
    "case_id,facts,expected",
    [
        ("RW3-SAV-002", {"employment_income": "10000", "savings_interest": "6000"}, {"income_tax_before_limitations": "0.00"}),
        ("RW3-SAV-003", {"employment_income": "12570", "savings_interest": "6000"}, {"savings_tax": "0.00"}),
        ("RW3-SAV-007", {"employment_income": "99500", "savings_interest": "1000"}, {"personal_allowance": "12320.00", "savings_tax": "200.00"}),
        ("RW3-DIV-002", {"employment_income": "45000", "dividends": "500"}, {"dividend_tax": "0.00", "income_tax_before_limitations": "6486.00"}),
        ("RW3-DIV-003", {"employment_income": "45000", "dividends": "504"}, {"dividend_tax": "0.43", "income_tax_before_limitations": "6486.43"}),
        ("RW3-DIV-005", {"employment_income": "125140", "dividends": "1000"}, {"dividend_tax": "196.75", "income_tax_before_limitations": "42712.75"}),
        ("RW3-DIV-006", {"employment_income": "99500", "dividends": "1000"}, {"personal_allowance": "12320.00", "dividend_tax": "178.75"}),
        ("RW3-PROP-003", {"employment_income": "30000", "uk_property_results": ["5000", "-2000"]}, {"uk_property_profit": "3000.00", "income_tax_before_limitations": "4086.00"}),
        ("RW3-PROP-004", {"employment_income": "30000", "joint_property_total_profit": "10000", "taxpayer_share_percentage": "50"}, {"uk_property_profit": "5000.00", "income_tax_before_limitations": "4486.00"}),
        ("RW3-FPROP-004", {"uk_resident": True, "employment_income": "30000", "foreign_property_gross_receipts": "14000", "foreign_property_allowable_expenses": "4000"}, {"foreign_property_profit": "10000.00", "income_tax_before_limitations": "5486.00"}),
    ],
)
def test_remaining_approved_annual_income_literals(case_id, facts, expected):
    result = calculate_annual_position(facts)
    for field, value in expected.items():
        assert getattr(result, field) == Decimal(value), case_id


@pytest.mark.engine
@pytest.mark.parametrize(
    "case_id,facts,benefit,percentage,charge",
    [
        ("RW3-HICBC-001", {"taxpayer_is_higher_ani_partner": True, "adjusted_net_income": "70000", "eldest_or_only_children": 1, "additional_children": 0, "weeks_entitled": 52}, "1406.60", 50, "703.00"),
        ("RW3-HICBC-006", {"taxpayer_is_higher_ani_partner": True, "adjusted_net_income": "70000", "eldest_or_only_children": 1, "additional_children": 1, "weeks_entitled": 52}, "2337.40", 50, "1168.00"),
        ("RW3-HICBC-007", {"taxpayer_is_higher_ani_partner": True, "adjusted_net_income": "70000", "eldest_or_only_children": 1, "additional_children": 0, "weeks_entitled": 26}, "703.30", 50, "351.00"),
        ("RW3-HICBC-009", {"taxpayer_is_higher_ani_partner": True, "adjusted_net_income": "59999", "annual_child_benefit": "1406.60", "payments_received_for_full_charge_period": True}, "1406.60", 0, "0.00"),
        ("RW3-HICBC-010", {"taxpayer_is_higher_ani_partner": True, "adjusted_net_income": "60000", "annual_child_benefit": "1406.60", "payments_received_for_full_charge_period": True}, "1406.60", 0, "0.00"),
        ("RW3-HICBC-011", {"taxpayer_is_higher_ani_partner": True, "adjusted_net_income": "60001", "annual_child_benefit": "1406.60", "payments_received_for_full_charge_period": True}, "1406.60", 0, "0.00"),
        ("RW3-HICBC-012", {"taxpayer_is_higher_ani_partner": True, "adjusted_net_income": "79800", "annual_child_benefit": "1406.60", "payments_received_for_full_charge_period": True}, "1406.60", 99, "1391.00"),
        ("RW3-HICBC-013", {"taxpayer_is_higher_ani_partner": True, "adjusted_net_income": "80001", "annual_child_benefit": "1406.60", "payments_received_for_full_charge_period": True}, "1406.60", 100, "1406.00"),
        ("RW3-HICBC-016", {"adjusted_net_income": "80200", "annual_child_benefit": "1406.60", "taxpayer_is_higher_ani_partner": True, "payments_received_for_full_charge_period": True}, "1406.60", 100, "1406.00"),
    ],
)
def test_remaining_approved_hicbc_literals(case_id, facts, benefit, percentage, charge):
    result = calculate_annual_position(facts)
    assert result.child_benefit_amount == Decimal(benefit), case_id
    assert result.hicbc_charge_percentage == percentage, case_id
    assert result.hicbc == Decimal(charge), case_id


def test_approved_hicbc_pension_and_payment_opt_out_literals():
    pension = calculate_annual_position(
        {
            "income_before_ras_pension": "70000",
            "gross_ras_pension": "10000",
            "annual_child_benefit": "1406.60",
            "taxpayer_is_higher_ani_partner": True,
            "payments_received_for_full_charge_period": True,
        }
    )
    assert pension.adjusted_net_income == Decimal("60000.00")
    assert pension.hicbc == Decimal("0.00")

    opted_out = calculate_annual_position(
        {"adjusted_net_income": "75000", "child_benefit_entitlement_retained": True, "child_benefit_payments_received": "0", "has_relevant_partner": False}
    )
    assert opted_out.hicbc == Decimal("0.00")
    assert "no_child_benefit_payments_to_charge" in opted_out.limitations


def test_nonresident_foreign_property_literal_stays_outside_supported_case():
    result = calculate_annual_position({"uk_resident": False, "foreign_property_profit": "10000"})
    assert result.total_liability is None
    assert result.calculation_status == "unsupported_rule"
    assert "outside_supported_uk_resident_case" in result.limitations


@pytest.mark.parametrize("field", ["employment_income", "savings_interest", "foreign_tax_paid"])
def test_boolean_values_are_not_accepted_as_money(field):
    with pytest.raises(ValueError, match="not boolean"):
        calculate_annual_position({field: True})


@pytest.mark.parametrize(
    "facts,message",
    [
        ({"uk_property_profit": "1000", "uk_property_results": ["1000"]}, "exactly one input"),
        ({"joint_property_total_profit": "1000", "uk_property_profit": "500"}, "exactly one input"),
        ({"foreign_property_profit": "1000", "foreign_property_gross_receipts": "1000"}, "profit or receipts"),
        ({"annual_child_benefit": "1406.60", "eldest_or_only_children": 1}, "exactly one amount"),
    ],
)
def test_contradictory_input_representations_fail_closed(facts, message):
    with pytest.raises(ValueError, match=message):
        calculate_annual_position(facts)


def test_finance_costs_require_explicit_supported_property_configuration():
    with pytest.raises(ValueError, match="individual-landlord"):
        calculate_annual_position({
            "rental_income": "10000",
            "non_finance_allowable_expenses": "2000",
            "residential_finance_costs": "3000",
            "residential_property": False,
        })


def test_explicit_ani_contradictions_fail_closed():
    with pytest.raises(ValueError, match="facts contradict"):
        calculate_annual_position({"adjusted_net_income": "70000", "person_adjusted_net_income": "71000"})
    with pytest.raises(ValueError, match="gross pension"):
        calculate_annual_position({
            "income_before_ras_pension": "70000",
            "gross_ras_pension": "10000",
            "adjusted_net_income": "61000",
        })


def test_hicbc_ambiguous_responsibility_withholds_total_and_charge():
    result = calculate_annual_position({
        "adjusted_net_income": "70000",
        "annual_child_benefit": "1406.60",
        "taxpayer_is_higher_ani_partner": False,
        "payments_received_for_full_charge_period": True,
    })
    assert result.hicbc is None
    assert result.total_liability is None
    assert result.calculation_status == "insufficient_facts"
    assert "hicbc_responsibility_facts_ambiguous" in result.limitations


def test_partner_ani_without_person_ani_fails_closed():
    with pytest.raises(ValueError, match="person's explicit ANI"):
        calculate_annual_position({
            "partner_adjusted_net_income": "75000",
            "annual_child_benefit_received_by_person": "1406.60",
        })
