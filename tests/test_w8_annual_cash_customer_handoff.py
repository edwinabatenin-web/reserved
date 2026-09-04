"""Focused acceptance tests for the W8-S2C owner-unbound handoff."""
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
import copy
import inspect
import pickle

import pytest

from reserved.engines.annual_to_cash_integration import AnnualToCashStatus
from reserved.services import w8_annual_cash_customer_handoff as handoff_contract
from reserved.services.w2_customer_language import (
    AdjustmentKind,
    EvidenceClassification,
    FundingClassification,
    ObligationKind,
)
from reserved.services.w8_annual_cash_customer_handoff import (
    UnboundAnnualCashPresentation,
    annual_to_cash_source_identity,
    compose_w8_annual_cash_customer_handoff,
    project_w8_annual_cash_presentation,
    validate_w8_annual_cash_customer_handoff,
    w8_annual_cash_customer_handoff_identity,
)
from reserved.services.w8_customer_result import compose_w8_customer_result
from tests.test_annual_to_cash_integration import (
    annual_position,
    balance_item,
    compose,
    payment,
)


def references(value):
    annual = value.considered_annual_position
    account = value.obligation_reconciliation.considered_account
    position = value.funding_position
    result = list(annual.evidence_ids)
    for item in account.considered_charges:
        result.extend((item.charge_id, item.source_reference))
    for item in account.considered_credits:
        result.extend((item.credit_id, item.source_reference))
    for item in account.considered_allocations:
        result.extend((item.allocation_id, item.source_reference))
    evidence = position.considered_set_aside
    if evidence:
        result.extend((evidence.evidence_id, evidence.source_reference))
        result.extend(item.allocation_id for item in evidence.allocations)
    return tuple(result)


def handoff(value, **overrides):
    kwargs = dict(evidence_references=references(value))
    kwargs.update(overrides)
    return compose_w8_annual_cash_customer_handoff(value, **kwargs)


def project(value, **overrides):
    """Build the legacy owner-bound fixture only for downstream contract tests.

    Production W8-S2C now stops at ``handoff``. Later authenticated-boundary
    tests import this helper to exercise their already-reviewed contracts; the
    helper is not product code and cannot weaken the owner-unbound boundary.
    """
    user_id = overrides.pop("user_id", "user-1")
    business_id = overrides.pop("business_id", "business-1")
    result = handoff(value, **overrides)
    if result is None:
        return None
    return compose_w8_customer_result(
        result.presentation_input,
        nation=result.nation,
        tax_year=result.tax_year,
        user_id=user_id,
        business_id=business_id,
        evidence_references=result.evidence_references,
    )


def identity(value, source):
    return w8_annual_cash_customer_handoff_identity(
        value,
        source_position=source,
        evidence_references=references(source),
        expected_as_of=source.as_of,
    )


def test_qualified_result_maps_all_facts_once_and_is_explicitly_owner_unbound():
    value = compose(
        deductions=balance_item("20.00"),
        prior_poa=balance_item("30.00"),
        payments=(payment("40.00"),),
    )
    result = handoff(value)
    assert result.owner_authoritative is False
    assert "requires_separate_authenticated_owner_business_binding" in result.limitations
    assert "owner_authoritative_public_result" in result.prohibited_uses
    assert result.presentation_input.evidence is EvidenceClassification.QUALIFIED_LOCAL_ESTIMATE
    assert {item.kind for item in result.presentation_input.obligations} == {
        ObligationKind.BALANCING_PAYMENT,
        ObligationKind.FIRST_PAYMENT_ON_ACCOUNT,
        ObligationKind.SECOND_PAYMENT_ON_ACCOUNT,
    }
    mapped = {item.kind: item.amount for item in result.presentation_input.adjustments}
    assert mapped[AdjustmentKind.DEDUCTIONS_AND_CREDITS] == Decimal("20.00")
    assert mapped[AdjustmentKind.PRIOR_PAYMENTS_ON_ACCOUNT] == Decimal("30.00")
    assert mapped[AdjustmentKind.PAYMENTS_MADE] == Decimal("40.00")
    assert result == handoff(value)
    assert identity(result, value) == identity(handoff(value), value)
    assert result.source_position_identity == annual_to_cash_source_identity(
        value, evidence_references=references(value)
    )
    assert result.tax_year == value.tax_year == "2026/27"
    assert result.nation == value.nation == "England"
    assert project_w8_annual_cash_presentation(
        result,
        source_position=value,
        evidence_references=references(value),
        expected_as_of=value.as_of,
    ) is result.presentation_input
    assert result.presentation_input.claim_to_reduce is None


def test_handoff_accepts_no_raw_owner_identifiers():
    parameters = inspect.signature(compose_w8_annual_cash_customer_handoff).parameters
    assert "user_id" not in parameters and "business_id" not in parameters
    source = compose()
    presentation = handoff(source).presentation_input
    with pytest.raises(ValueError, match="issued only"):
        UnboundAnnualCashPresentation(
            presentation,
            references(source),
            source.as_of,
            source.tax_year,
            source.nation,
            source.ruleset_version,
            source.contract_version,
            annual_to_cash_source_identity(
                source, evidence_references=references(source)
            ),
            source.annual_position_reference,
        )


def test_copy_pickle_dataclass_replace_and_low_level_mutation_fail_closed():
    source = compose()
    result = handoff(source)
    with pytest.raises(TypeError, match="cannot be copied"):
        copy.copy(result)
    with pytest.raises(TypeError, match="cannot be copied"):
        copy.deepcopy(result)
    with pytest.raises(TypeError, match="cannot be pickled"):
        pickle.dumps(result)
    with pytest.raises(ValueError, match="issued only"):
        replace(result, tax_year="2025/26")

    object.__setattr__(result, "tax_year", "2025/26")
    with pytest.raises(ValueError, match="integrity mismatch"):
        identity(result, source)


def test_nested_mutation_substitution_and_mismatched_or_replayed_context_fail():
    source = compose()
    refs = references(source)
    result = handoff(source)
    other = compose(set_aside="0.00")
    other_refs = references(other)

    with pytest.raises(ValueError, match="expected source context"):
        validate_w8_annual_cash_customer_handoff(
            result,
            source_position=other,
            evidence_references=other_refs,
            expected_as_of=other.as_of,
        )
    with pytest.raises(ValueError, match="expected source context"):
        validate_w8_annual_cash_customer_handoff(
            result,
            source_position=source,
            evidence_references=refs,
            expected_as_of=source.as_of + timedelta(days=1),
        )

    object.__setattr__(result.presentation_input, "annual_liability", Decimal("1.00"))
    with pytest.raises(ValueError, match="integrity mismatch"):
        validate_w8_annual_cash_customer_handoff(
            result,
            source_position=source,
            evidence_references=refs,
            expected_as_of=source.as_of,
        )

    clean_result = handoff(source)
    object.__setattr__(clean_result.presentation_input, "undeclared", "state")
    with pytest.raises(ValueError, match="undeclared state"):
        identity(clean_result, source)


def test_presentation_cycle_fails_closed_in_identity_validator_and_projector():
    source = compose()
    refs = references(source)
    result = handoff(source)
    object.__setattr__(
        result.presentation_input, "obligations", (result.presentation_input,)
    )
    with pytest.raises(ValueError, match="contains a cycle"):
        identity(result, source)
    with pytest.raises(ValueError, match="contains a cycle"):
        validate_w8_annual_cash_customer_handoff(
            result,
            source_position=source,
            evidence_references=refs,
            expected_as_of=source.as_of,
        )
    with pytest.raises(ValueError, match="contains a cycle"):
        project_w8_annual_cash_presentation(
            result,
            source_position=source,
            evidence_references=refs,
            expected_as_of=source.as_of,
        )


def test_private_issue_token_and_valid_seal_do_not_prove_source_admission():
    source = compose()
    refs = references(source)
    legitimate = handoff(source)
    substituted = replace(
        legitimate.presentation_input, annual_liability=Decimal("1.00")
    )
    forged = UnboundAnnualCashPresentation(
        substituted,
        refs,
        source.as_of,
        source.tax_year,
        source.nation,
        source.ruleset_version,
        source.contract_version,
        annual_to_cash_source_identity(source, evidence_references=refs),
        source.annual_position_reference,
        _issue_token=handoff_contract._ISSUE_TOKEN,
    )
    assert "validated-owner-unbound" in repr(forged)
    with pytest.raises(ValueError, match="not derived from the exact source"):
        identity(forged, source)


@pytest.mark.parametrize(
    "set_aside, expected",
    [("0.00", FundingClassification.GAP), ("exact", FundingClassification.EXACT),
     ("99999.00", FundingClassification.SURPLUS)],
)
def test_funding_mapping(set_aside, expected):
    result = handoff(compose(set_aside=set_aside))
    assert result.presentation_input.funding is expected


def test_forged_calculated_status_never_becomes_hmrc_confirmed_exact():
    value = compose()
    assert handoff(replace(value, status=AnnualToCashStatus.CALCULATED)) is None
    result = handoff(value)
    assert result.presentation_input.evidence is EvidenceClassification.QUALIFIED_LOCAL_ESTIMATE


@pytest.mark.parametrize("nation", ["England", "Wales", "Northern Ireland"])
def test_geography_and_tax_year_are_derived_only_from_the_exact_source(nation):
    parameters = inspect.signature(compose_w8_annual_cash_customer_handoff).parameters
    assert "nation" not in parameters and "tax_year" not in parameters
    source = compose(annual=annual_position(nation))
    result = handoff(source)
    assert result.nation == nation
    assert result.tax_year == source.tax_year
    assert validate_w8_annual_cash_customer_handoff(
        result,
        source_position=source,
        evidence_references=references(source),
        expected_as_of=source.as_of,
    ) is result


def test_missing_mutated_and_coherently_reconstructed_geography_fail_closed():
    missing = compose(annual=annual_position(None))
    assert missing.nation is None
    assert handoff(missing) is None

    source = compose(annual=annual_position("England"))
    refs = references(source)
    assert handoff(replace(source, nation="Wales"), evidence_references=refs) is None

    mutated = compose(annual=annual_position("England"))
    mutated_refs = references(mutated)
    object.__setattr__(mutated, "nation", "Wales")
    object.__setattr__(mutated.considered_annual_position, "nation", "Wales")
    assert handoff(mutated, evidence_references=mutated_refs) is None


def test_tax_year_mutation_and_coherent_reconstruction_fail_closed():
    source = compose()
    refs = references(source)
    assert handoff(replace(source, tax_year="2025/26"), evidence_references=refs) is None

    mutated = compose()
    mutated_refs = references(mutated)
    object.__setattr__(mutated, "tax_year", "2025/26")
    object.__setattr__(mutated.considered_annual_position, "tax_year", "2025/26")
    assert handoff(mutated, evidence_references=mutated_refs) is None


@pytest.mark.parametrize("status", [AnnualToCashStatus.REVIEW_REQUIRED, AnnualToCashStatus.UNRESOLVED])
def test_non_actionable_states_fail_closed(status):
    assert handoff(replace(compose(), status=status)) is None


def test_recomputes_reconciliation_and_rejects_mutated_amount_or_due_date():
    for field_name, forged in (
        ("amount", Decimal("1.00")),
        ("due_date", date(2029, 1, 31)),
    ):
        value = compose()
        refs = references(value)
        expected = value.obligation_reconciliation.expected_obligations[0]
        object.__setattr__(expected, field_name, forged)
        assert compose_w8_annual_cash_customer_handoff(
            value, evidence_references=refs
        ) is None


@pytest.mark.parametrize(
    "field_name, forged",
    [
        ("total_required", Decimal("1.00")),
        ("total_set_aside", Decimal("1.00")),
        ("funding_gap", Decimal("1.00")),
        ("reserve_surplus", Decimal("1.00")),
    ],
)
def test_recomputes_funding_and_rejects_mutated_totals(field_name, forged):
    value = compose()
    refs = references(value)
    object.__setattr__(value.funding_position, field_name, forged)
    assert compose_w8_annual_cash_customer_handoff(value, evidence_references=refs) is None


def test_recomputes_funding_and_rejects_mutated_schedule_date():
    value = compose()
    refs = references(value)
    object.__setattr__(value.funding_position.schedule[0], "due_date", date(2030, 1, 31))
    assert compose_w8_annual_cash_customer_handoff(value, evidence_references=refs) is None


def test_cycle_and_overdeep_graph_fail_closed_without_recursion_error():
    value = compose()
    refs = references(value)
    object.__setattr__(value.funding_position, "considered_obligations", value)
    assert compose_w8_annual_cash_customer_handoff(value, evidence_references=refs) is None

    value = compose()
    refs = references(value)
    nested = ()
    for _ in range(70):
        nested = (nested,)
    object.__setattr__(value, "limitations", nested)
    assert compose_w8_annual_cash_customer_handoff(value, evidence_references=refs) is None


def test_substitution_duplicate_reference_and_nested_mutation_fail_closed():
    value = compose()
    refs = references(value)
    assert compose_w8_annual_cash_customer_handoff(
        value, evidence_references=refs[:-1] + ("substituted:same-payload",)
    ) is None
    assert compose_w8_annual_cash_customer_handoff(
        value, evidence_references=refs[:-1] + (refs[0],)
    ) is None
    object.__setattr__(value.funding_position, "funding_gap", Decimal("1.00"))
    assert compose_w8_annual_cash_customer_handoff(value, evidence_references=refs) is None


def test_handoff_contains_no_owner_or_secret_material():
    result = handoff(compose())
    rendered = repr(result)
    assert "user_id" not in rendered and "business_id" not in rendered
    assert "utr" not in rendered.lower() and "nino" not in rendered.lower()
    assert "secret" not in rendered.lower()
