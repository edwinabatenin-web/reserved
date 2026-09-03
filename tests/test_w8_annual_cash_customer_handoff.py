"""Focused acceptance tests for the W8-S2C annual/cash handoff."""
from __future__ import annotations

import copy
from dataclasses import fields, replace
from datetime import timedelta
from decimal import Decimal
import pickle

import pytest

from reserved.engines import payments_on_account as poa
from reserved.engines import sa_account_reconciliation as account
from reserved.engines.annual_to_cash_integration import (
    AnnualToCashPosition,
    AnnualToCashStatus,
    balance_item_identity,
    cash_ready_annual_position_identity,
    compose_annual_to_cash_position,
    annual_to_cash_position_provenance,
    prior_year_evidence_identity,
)
from reserved.services.w2_customer_language import (
    AdjustmentKind,
    EvidenceClassification,
    FundingClassification,
    ObligationKind,
)
from reserved.services.w8_annual_cash_customer_handoff import (
    compose_w8_annual_cash_customer_result,
)
from reserved.services.w8_customer_result import w8_customer_result_identity
from tests.test_annual_to_cash_integration import (
    AS_OF,
    annual_position,
    balance_item,
    compose,
    expected_positions,
    observed_account,
    payment,
    prior_year,
    set_aside_for,
)


def references(value):
    provenance = annual_to_cash_position_provenance(value)
    annual = value.considered_annual_position
    account = value.obligation_reconciliation.considered_account
    position = value.funding_position
    result = [*annual.evidence_ids]
    result.extend(provenance.deductions_credits_evidence_ids)
    result.extend(provenance.prior_poa_evidence_ids)
    result.extend(provenance.payment_source_ids)
    for item in account.considered_charges:
        result.extend((item.charge_id, item.source_reference))
    for item in account.considered_credits:
        result.extend((item.credit_id, item.source_reference))
    for item in account.considered_allocations:
        result.extend((item.allocation_id, item.source_reference))
    evidence = position.considered_set_aside
    if evidence is not None:
        result.extend((evidence.evidence_id, evidence.source_reference))
        result.extend(item.allocation_id for item in evidence.allocations)
    return tuple(dict.fromkeys(result))


def shared_account_source_position():
    annual = annual_position()
    prior = prior_year()
    deductions = balance_item("0.00")
    prior_poa = balance_item("0.00")
    assessed, balancing = expected_positions(
        annual,
        prior=prior,
        deductions=deductions,
        prior_poa=prior_poa,
    )
    observed = observed_account(assessed, balancing)
    shared_charges = tuple(
        replace(item, source_reference="account:shared-record")
        for item in observed.considered_charges
    )
    shared_account = account.reconcile_sa_account(
        shared_charges,
        observed.considered_credits,
        observed.considered_allocations,
        as_of=AS_OF,
        coverage=account.Completeness.COMPLETE_FOR_PURPOSE,
    )
    set_aside = set_aside_for(assessed, balancing)
    return compose_annual_to_cash_position(
        annual_position=annual,
        annual_position_reference=cash_ready_annual_position_identity(annual),
        preceding_year_status=poa.PrecedingYearStatus.ESTABLISHED,
        prior_year_evidence=prior,
        prior_year_reference=prior_year_evidence_identity(prior),
        deductions_credits=deductions,
        deductions_credits_reference=balance_item_identity(
            deductions,
            channel="deductions-credits",
            evidence_ids=("cash:deductions-credits",),
        ),
        deductions_credits_evidence_ids=("cash:deductions-credits",),
        prior_poa=prior_poa,
        prior_poa_reference=balance_item_identity(
            prior_poa,
            channel="prior-poa",
            evidence_ids=("cash:prior-poa",),
        ),
        prior_poa_evidence_ids=("cash:prior-poa",),
        payments_made=(),
        payment_content_references=(),
        account_reconciliation=shared_account,
        set_aside_evidence=set_aside,
        as_of=AS_OF,
    )


def project(value, **overrides):
    reference_value = overrides.pop("reference_value", value)
    supplied_references = (
        overrides.pop("evidence_references")
        if "evidence_references" in overrides
        else references(reference_value)
    )
    kwargs = {
        "nation": "England",
        "user_id": "user-1",
        "business_id": "business-1",
        "evidence_references": supplied_references,
    }
    kwargs.update(overrides)
    return compose_w8_annual_cash_customer_result(value, **kwargs)


def test_live_producer_result_maps_all_supported_facts_once_as_local_estimate():
    value = compose(
        deductions=balance_item("20.00"),
        prior_poa=balance_item("30.00"),
        payments=(payment("40.00"),),
    )
    result = project(value)
    assert result is not None
    assert result.presentation_input.evidence is EvidenceClassification.QUALIFIED_LOCAL_ESTIMATE
    assert result.presentation_input.annual_liability == value.final_self_assessment_liability
    assert result.evidence_references == references(value)
    assert {item.kind for item in result.presentation_input.obligations} == {
        ObligationKind.BALANCING_PAYMENT,
        ObligationKind.FIRST_PAYMENT_ON_ACCOUNT,
        ObligationKind.SECOND_PAYMENT_ON_ACCOUNT,
    }
    expected_due_dates = {
        item.kind: item.due_date for item in value.obligation_reconciliation.expected_obligations
    }
    assert {
        item.kind.value: item.due_date for item in result.presentation_input.obligations
    } == {
        {
            "balancing_payment": "balancing_payment",
            "payment_on_account_1": "first_payment_on_account",
            "payment_on_account_2": "second_payment_on_account",
        }[item.value]: due
        for item, due in expected_due_dates.items()
    }
    adjustments = {item.kind: item.amount for item in result.presentation_input.adjustments}
    assert adjustments == {
        AdjustmentKind.DEDUCTIONS_AND_CREDITS: Decimal("20.00"),
        AdjustmentKind.PRIOR_PAYMENTS_ON_ACCOUNT: Decimal("30.00"),
        AdjustmentKind.PAYMENTS_MADE: Decimal("40.00"),
        AdjustmentKind.CREDIT_OR_REFUND: Decimal("0.00"),
    }
    assert result.presentation_input.claim_to_reduce is None
    assert "local estimates" in result.view.status_message
    assert "must not be read as your current HMRC bill" in result.view.status_message
    assert w8_customer_result_identity(result) == w8_customer_result_identity(project(value))


@pytest.mark.parametrize(
    "set_aside, expected",
    [
        ("0.00", FundingClassification.GAP),
        ("exact", FundingClassification.EXACT),
        ("99999.00", FundingClassification.SURPLUS),
    ],
)
def test_funding_gap_exact_and_surplus_copy_the_producer_position(set_aside, expected):
    value = compose(set_aside=set_aside)
    result = project(value)
    assert result is not None
    assert result.presentation_input.funding is expected
    if expected is FundingClassification.GAP:
        assert result.presentation_input.funding_amount == value.funding_position.funding_gap
    elif expected is FundingClassification.EXACT:
        assert result.presentation_input.funding_amount is None
    else:
        assert result.presentation_input.funding_amount == value.funding_position.reserve_surplus
        assert "not available cash" in result.view.funding_message
        assert "spendable" in result.view.funding_message


def test_review_required_and_unresolved_positions_are_categorical_and_value_free():
    review = compose(mismatch=True)
    unresolved = compose(set_aside=None)
    assert review.status is AnnualToCashStatus.REVIEW_REQUIRED
    assert unresolved.status is AnnualToCashStatus.UNRESOLVED
    assert project(review) is None
    assert project(unresolved) is None


def test_calculated_name_cannot_promote_local_liability_to_hmrc_exact():
    value = compose()
    assert project(
        replace(value, status=AnnualToCashStatus.CALCULATED),
        reference_value=value,
    ) is None
    genuine = project(value)
    assert genuine.presentation_input.evidence is EvidenceClassification.QUALIFIED_LOCAL_ESTIMATE
    assert "HMRC-recorded cash obligations" not in repr(genuine.view)


@pytest.mark.parametrize("transform", [copy.copy, copy.deepcopy, lambda value: pickle.loads(pickle.dumps(value))])
def test_copied_or_reconstructed_positions_are_not_producer_issued(transform):
    value = compose()
    assert project(transform(value), reference_value=value) is None


def test_direct_and_coherently_replaced_positions_are_not_producer_issued():
    value = compose()
    values = {item.name: object.__getattribute__(value, item.name) for item in fields(value)}
    assert project(AnnualToCashPosition(**values), reference_value=value) is None
    assert project(
        replace(value, limitations=value.limitations + ("plausible",)),
        reference_value=value,
    ) is None


def test_nested_amount_date_and_funding_mutations_fail_closed():
    amount_value = compose()
    amount_refs = references(amount_value)
    object.__setattr__(
        amount_value.balancing_position,
        "payments_made_total",
        Decimal("1.00"),
    )
    assert project(amount_value, evidence_references=amount_refs) is None

    date_value = compose()
    date_refs = references(date_value)
    obligation = date_value.obligation_reconciliation.expected_obligations[0]
    object.__setattr__(obligation, "due_date", obligation.due_date + timedelta(days=1))
    assert project(date_value, evidence_references=date_refs) is None

    funding_value = compose()
    funding_refs = references(funding_value)
    object.__setattr__(funding_value.funding_position, "total_required", Decimal("1.00"))
    assert project(funding_value, evidence_references=funding_refs) is None


def test_exact_complete_evidence_reference_tuple_is_required():
    value = compose(payments=(payment(),))
    refs = references(value)
    assert project(value, evidence_references=refs) is not None
    assert project(value, evidence_references=refs[:-1]) is None
    assert project(value, evidence_references=refs[:-1] + ("substituted:same-payload",)) is None
    assert project(value, evidence_references=list(refs)) is None


def test_distinct_hmrc_charges_may_share_one_canonical_source_reference():
    value = shared_account_source_position()
    assert value.status is AnnualToCashStatus.QUALIFIED_LOCAL_RESULT
    source_references = tuple(
        item.source_reference
        for item in value.obligation_reconciliation.considered_account.considered_charges
    )
    assert len(source_references) > 1
    assert set(source_references) == {"account:shared-record"}
    refs = references(value)
    assert refs.count("account:shared-record") == 1
    result = project(value, evidence_references=refs)
    assert result is not None
    assert result.evidence_references == refs


def test_module_rebinding_cannot_replace_producer_readers_mappings_or_public_composer():
    import reserved.services.w8_annual_cash_customer_handoff as module

    value = compose()
    expected = w8_customer_result_identity(project(value))
    names = {
        "annual_to_cash_position_identity": lambda item: "forged",
        "annual_to_cash_position_provenance": lambda item: object(),
        "compose_w8_customer_result": lambda *args, **kwargs: None,
        "AnnualToCashStatus": object(),
        "ObligationKind": object(),
        "FundingClassification": object(),
        "_ZERO": Decimal("999.00"),
        "_PENNY": Decimal("1.00"),
        "Decimal": object(),
        "date": object(),
    }
    originals = {name: getattr(module, name) for name in names}
    try:
        for name, replacement in names.items():
            setattr(module, name, replacement)
        assert w8_customer_result_identity(project(value)) == expected
        mutated = compose()
        mutated_refs = references(mutated)
        object.__setattr__(mutated, "status", AnnualToCashStatus.CALCULATED)
        assert project(mutated, evidence_references=mutated_refs) is None
    finally:
        for name, original in originals.items():
            setattr(module, name, original)


def test_hostile_subtypes_are_rejected_without_dispatching_hooks():
    calls = []

    class Hostile(AnnualToCashPosition):
        def __getattribute__(self, name):
            calls.append(name)
            raise AssertionError("hostile hook dispatched")

    value = compose()
    values = {item.name: object.__getattribute__(value, item.name) for item in fields(value)}
    hostile = object.__new__(Hostile)
    for name, item in values.items():
        object.__setattr__(hostile, name, item)
    assert compose_w8_annual_cash_customer_result(
        hostile,
        nation="England",
        user_id="user-1",
        business_id="business-1",
        evidence_references=references(value),
    ) is None
    assert calls == []


def test_public_boundary_preserves_geography_ownership_and_no_payment_controls():
    value = compose()
    with pytest.raises(ValueError, match="unsupported geography"):
        project(value, nation="Scotland")
    with pytest.raises(ValueError, match="ownership"):
        project(value, user_id="bad secret token")
    result = project(value)
    assert result is not None
    assert "no_payment_or_transfer_authority" in result.prohibited_uses
    public = repr(result) + repr(result.view)
    assert "AnnualToCashPosition" not in public
    assert "utr" not in public.lower() and "nino" not in public.lower()
    assert "secret" not in public.lower()
