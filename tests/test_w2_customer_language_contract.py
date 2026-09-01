"""Focused checks for the self-contained W2 presentation boundary."""
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from reserved.engines import annual_to_cash_integration as integration
from reserved.engines import cash_funding_position as funding
from reserved.engines import cash_obligation_reconciliation as obligations
from reserved.engines import payments_on_account as poa
from reserved.engines import poa_reduction_guardrail as reduction
from reserved.services.w2_customer_language import (
    CONTRACT_VERSION,
    AdjustmentFact,
    AdjustmentKind,
    ClaimToReduceState,
    EvidenceClassification,
    FundingClassification,
    ObligationFact,
    ObligationKind,
    PresentationStatus,
    W2PresentationInput,
    present_w2_customer_language,
)
from tests.test_annual_to_cash_integration import balance_item, compose, payment
from tests.test_internal_tax_boundary import INTERNAL_MODULE_MARKERS
from tests.test_poa_reduction_guardrail import evaluate


ROOT = Path(__file__).resolve().parents[1]


def render(model):
    environment = Environment(
        loader=FileSystemLoader(ROOT / "reserved" / "templates"),
        autoescape=select_autoescape(("html",)),
    )
    return environment.get_template("v2/_w2_cash_obligations.html").render(model=model)


def _claim_state(result):
    states = {
        reduction.PoAReductionStatus.REVIEW_READY_FOR_CUSTOMER_HMRC_ACTION:
            ClaimToReduceState.REVIEW_READY,
        reduction.PoAReductionStatus.CUSTOMER_CONFIRMATION_REQUIRED:
            ClaimToReduceState.CUSTOMER_CONFIRMATION_REQUIRED,
        reduction.PoAReductionStatus.NO_REDUCTION: ClaimToReduceState.NO_REDUCTION,
        reduction.PoAReductionStatus.POA_NOT_APPLICABLE: ClaimToReduceState.NOT_APPLICABLE,
    }
    return states.get(result.status, ClaimToReduceState.REVIEW_REQUIRED)


def presentation_input(*, claim=None, **compose_options):
    """Test-only copy adapter; it is not a production integration boundary."""
    result = compose(**compose_options)
    if result.status not in {
        integration.AnnualToCashStatus.CALCULATED,
        integration.AnnualToCashStatus.QUALIFIED_LOCAL_RESULT,
    }:
        return W2PresentationInput(
            CONTRACT_VERSION, PresentationStatus.REVIEW_REQUIRED, None, None,
            (), (), None, None,
        )
    reconciliation = result.obligation_reconciliation
    obligation_kinds = {
        "balancing_payment": ObligationKind.BALANCING_PAYMENT,
        "payment_on_account_1": ObligationKind.FIRST_PAYMENT_ON_ACCOUNT,
        "payment_on_account_2": ObligationKind.SECOND_PAYMENT_ON_ACCOUNT,
    }
    copied_obligations = tuple(
        ObligationFact(obligation_kinds[item.kind.value], item.amount, item.due_date)
        for item in reconciliation.expected_obligations
    )
    balance = result.balancing_position
    copied_adjustments = tuple(
        AdjustmentFact(kind, amount)
        for kind, amount in (
            (AdjustmentKind.DEDUCTIONS_AND_CREDITS, balance.deductions_credits),
            (AdjustmentKind.PRIOR_PAYMENTS_ON_ACCOUNT, balance.prior_poa),
            (AdjustmentKind.PAYMENTS_MADE, balance.payments_made_total),
            (AdjustmentKind.CREDIT_OR_REFUND, balance.excess_credit),
        )
        if amount is not None
    )
    funding_kinds = {
        funding.FundingBalance.GAP: FundingClassification.GAP,
        funding.FundingBalance.EXACT: FundingClassification.EXACT,
        funding.FundingBalance.SURPLUS: FundingClassification.SURPLUS,
    }
    selected_funding = funding_kinds[result.funding_position.balance]
    funding_amount = {
        FundingClassification.GAP: result.funding_position.funding_gap,
        FundingClassification.EXACT: None,
        FundingClassification.SURPLUS: result.funding_position.reserve_surplus,
    }[selected_funding]
    confirmed = (
        reconciliation.status is obligations.CashObligationStatus.ALIGNED
        and reconciliation.account_hmrc_confirmed is True
        and result.funding_position.obligations_hmrc_confirmed is True
    )
    return W2PresentationInput(
        CONTRACT_VERSION,
        PresentationStatus.READY,
        EvidenceClassification.HMRC_CONFIRMED_EXACT if confirmed
        else EvidenceClassification.QUALIFIED_LOCAL_ESTIMATE,
        result.final_self_assessment_liability,
        copied_obligations,
        copied_adjustments,
        selected_funding,
        funding_amount,
        None if claim is None else _claim_state(claim),
    )


def test_customer_service_contains_no_internal_customer_boundary_markers():
    source = (ROOT / "reserved/services/w2_customer_language.py").read_text()
    assert "reserved.engines" not in source
    assert not [marker for marker in INTERNAL_MODULE_MARKERS if marker in source]


def test_annual_liability_is_not_labelled_as_current_hmrc_bill():
    view = present_w2_customer_language(presentation_input())
    assert view.safe_to_present
    assert "not your current HMRC bill" in view.annual_liability.label


def test_local_and_hmrc_account_evidence_are_visibly_distinct():
    hmrc = present_w2_customer_language(presentation_input(hmrc=True))
    local = present_w2_customer_language(presentation_input(hmrc=False))
    assert hmrc.evidence_label == "HMRC-recorded cash obligations"
    assert local.evidence_label == "Local estimate — not confirmed by HMRC"
    assert "must not be read as your current HMRC bill" in local.status_message


def test_balancing_and_both_poa_rows_keep_explicit_labels_amounts_and_dates():
    facts = presentation_input()
    view = present_w2_customer_language(facts)
    assert [line.amount for line in view.obligations] == [
        f"£{item.amount:,.2f}" for item in facts.obligations
    ]
    assert [line.due_date for line in view.obligations] == [
        item.due_date.strftime("%-d %B %Y") for item in facts.obligations
    ]
    assert {line.label for line in view.obligations} == {
        "Balancing payment", "First Payment on Account", "Second Payment on Account"
    }


@pytest.mark.parametrize("kind,label", [
    (ObligationKind.BALANCING_PAYMENT, "Balancing payment"),
    (ObligationKind.FIRST_PAYMENT_ON_ACCOUNT, "First Payment on Account"),
    (ObligationKind.SECOND_PAYMENT_ON_ACCOUNT, "Second Payment on Account"),
])
def test_each_supported_obligation_kind_has_only_its_fixed_label(kind, label):
    facts = presentation_input()
    labelled = dict(zip(
        (item.kind for item in facts.obligations),
        (item.label for item in present_w2_customer_language(facts).obligations),
    ))
    assert labelled[kind] == label


@pytest.mark.parametrize("bad_kind", ["unexpected", None, 1])
def test_unknown_obligation_kind_fails_whole_view_closed(bad_kind):
    facts = presentation_input()
    malformed = replace(facts.obligations[0], kind=bad_kind)
    view = present_w2_customer_language(
        replace(facts, obligations=(malformed,) + facts.obligations[1:])
    )
    output = render(view)
    assert not view.safe_to_present and view.obligations == ()
    assert view.annual_liability is None and "£" not in output


def test_duplicate_obligation_kind_is_incoherent_and_fails_closed():
    facts = presentation_input()
    duplicate = replace(facts.obligations[1], kind=facts.obligations[0].kind)
    view = present_w2_customer_language(
        replace(facts, obligations=(facts.obligations[0], duplicate) + facts.obligations[2:])
    )
    assert not view.safe_to_present


def test_prior_payments_credits_and_refunds_are_shown_once_not_obligations():
    facts = presentation_input(
        deductions=balance_item("100.00"), prior_poa=balance_item("600.00"),
        payments=(payment("100.00"),), set_aside="5000.00",
    )
    view = present_w2_customer_language(facts)
    assert [item.label for item in view.account_adjustments] == [
        "Deductions and credits already included",
        "Prior Payments on Account already included",
        "Payments already included",
    ]
    assert len(view.obligations) == len(facts.obligations)


def test_first_year_sa_does_not_invent_prior_year_poa():
    view = present_w2_customer_language(
        presentation_input(status=poa.PrecedingYearStatus.FIRST_YEAR)
    )
    assert [item.label for item in view.obligations] == ["Balancing payment"]
    assert all("Prior Payments on Account" not in item.label for item in view.account_adjustments)


def test_exact_reconciliation_has_dates_but_no_payment_authority():
    output = render(present_w2_customer_language(presentation_input()))
    assert "Exact agreement" in output and "due " in output
    assert "does not authorise a payment or transfer" in output


@pytest.mark.parametrize("unsafe", [
    lambda value: replace(value, status=PresentationStatus.REVIEW_REQUIRED),
    lambda value: replace(value, status="ready"),
    lambda value: replace(value, contract_version="unsupported/3.0"),
    lambda value: replace(value, evidence=None),
    lambda value: replace(value, funding=None),
])
def test_unsafe_states_suppress_all_monetary_presentation(unsafe):
    view = present_w2_customer_language(unsafe(presentation_input()))
    output = render(view)
    assert not view.safe_to_present
    assert view.annual_liability is None and view.obligations == ()
    assert "£" not in output and "Review required" in output


@pytest.mark.parametrize("amount,heading,required", [
    ("100.00", "Set-aside gap", "not a transfer recommendation"),
    ("exact", "Exact set-aside coverage", "not a payment instruction"),
    ("5000.00", "Set-aside surplus", "not available cash"),
])
def test_funding_language_never_becomes_spending_or_movement_advice(amount, heading, required):
    view = present_w2_customer_language(presentation_input(set_aside=amount))
    assert view.funding_heading == heading and required in view.funding_message
    assert "safe to spend" not in view.funding_message.lower()


BAD_MONEY = (
    pytest.param(Decimal("NaN"), id="nan"),
    pytest.param(Decimal("Infinity"), id="infinite"),
    pytest.param(Decimal("-0.01"), id="negative"),
)


def _corrupt_visible_money(facts, family, amount):
    if family == "annual":
        return replace(facts, annual_liability=amount)
    if family == "obligation":
        changed = replace(facts.obligations[0], amount=amount)
        return replace(facts, obligations=(changed,) + facts.obligations[1:])
    if family == "adjustment":
        changed = replace(facts.adjustments[0], amount=amount)
        return replace(facts, adjustments=(changed,) + facts.adjustments[1:])
    if family == "funding":
        return replace(facts, funding=FundingClassification.GAP, funding_amount=amount)
    raise AssertionError("unsupported test family")


@pytest.mark.parametrize("amount", BAD_MONEY)
@pytest.mark.parametrize("family", ["annual", "obligation", "adjustment", "funding"])
def test_malformed_customer_visible_money_fails_closed_without_currency(family, amount):
    view = present_w2_customer_language(
        _corrupt_visible_money(presentation_input(), family, amount)
    )
    output = render(view)
    assert not view.safe_to_present
    assert view.annual_liability is None and view.obligations == ()
    assert "£" not in output


@pytest.mark.parametrize(
    "classification",
    [FundingClassification.GAP, FundingClassification.SURPLUS],
)
def test_zero_gap_or_surplus_fails_closed_without_currency(classification):
    facts = presentation_input()
    incoherent = replace(
        facts,
        funding=classification,
        funding_amount=Decimal("0.00"),
    )
    view = present_w2_customer_language(incoherent)
    assert not view.safe_to_present
    assert view.annual_liability is None and view.obligations == ()
    assert "£" not in render(view)


@pytest.mark.parametrize(
    ("classification", "amount", "expected"),
    [
        (FundingClassification.GAP, Decimal("0.01"), "short by £0.01"),
        (FundingClassification.SURPLUS, Decimal("0.01"), "exceeds the obligations shown by £0.01"),
    ],
)
def test_positive_exact_gap_and_surplus_amounts_remain_presentable(
    classification, amount, expected
):
    facts = replace(
        presentation_input(),
        funding=classification,
        funding_amount=amount,
    )
    view = present_w2_customer_language(facts)
    assert view.safe_to_present
    assert expected in view.funding_message


def test_exact_funding_requires_none_and_remains_presentable():
    facts = presentation_input()
    assert facts.funding is FundingClassification.EXACT
    assert facts.funding_amount is None
    assert present_w2_customer_language(facts).safe_to_present
    assert not present_w2_customer_language(
        replace(facts, funding_amount=Decimal("0.00"))
    ).safe_to_present


def test_exact_zero_adjustments_remain_valid_and_suppressed():
    view = present_w2_customer_language(presentation_input())
    assert view.safe_to_present and view.account_adjustments == ()


def test_claim_to_reduce_has_no_recommendation_and_keeps_interest_warning():
    view = present_w2_customer_language(presentation_input(claim=evaluate()))
    output = render(view)
    assert "No amount is recommended here" in output
    assert "may lead to interest" in output and "£500" not in output


def test_input_and_output_expose_no_source_payload_or_private_evidence_fields():
    facts = presentation_input()
    assert not hasattr(facts, "source_reference")
    output = render(present_w2_customer_language(facts))
    assert "source_reference" not in output and "credential" not in output


@pytest.mark.parametrize("facts", [
    pytest.param(presentation_input(), id="safe"),
    pytest.param(replace(presentation_input(), status=PresentationStatus.REVIEW_REQUIRED), id="closed"),
])
def test_accessible_status_and_heading_semantics_survive_every_state(facts):
    output = render(present_w2_customer_language(facts))
    assert '<section aria-labelledby="w2-cash-heading">' in output
    assert '<h2 id="w2-cash-heading">' in output
    assert 'role="status"' in output and 'aria-live="polite"' in output
    assert 'role="note"' in output
