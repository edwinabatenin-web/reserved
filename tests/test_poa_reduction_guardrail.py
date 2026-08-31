from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from reserved.engines.payments_on_account import (
    BalanceItem,
    Completeness,
    PoAStatus,
    PrecedingYearStatus,
    PriorYearEvidence,
    SourceKind,
    assess_payments_on_account,
)
from reserved.engines.poa_reduction_guardrail import (
    CurrentYearReductionEvidence,
    CustomerReductionProposal,
    PoAReductionStatus,
    ReductionEvidenceSource,
    evaluate_poa_reduction_guardrail,
)


AS_OF = date(2026, 8, 31)


def assessment(*, amount="1200.00", source=SourceKind.LOCAL_ESTIMATE):
    prior = PriorYearEvidence(
        tax_year="2025/26",
        source=source,
        effective_date=date(2026, 4, 5),
        retrieval_date=AS_OF,
        completeness=Completeness.COMPLETE_FOR_PURPOSE,
        income_tax=Decimal(amount),
        hicbc=Decimal("0.00"),
        class_4_nic=Decimal("0.00"),
        tax_deducted_at_source=Decimal("0.00"),
    )
    return assess_payments_on_account(
        preceding_year_status=PrecedingYearStatus.ESTABLISHED,
        prior_year=prior,
        as_of=AS_OF,
    )


def proposal(first="500.00", second="500.00", *, intent=True,
             confirmed=True, acknowledged=True):
    return CustomerReductionProposal(
        "proposal-1", first, second, intent, confirmed, acknowledged,
    )


def evidence(first="500.00", second="500.00", *,
             source=ReductionEvidenceSource.LOCAL_ESTIMATE,
             retrieval=AS_OF, effective=AS_OF, completeness=Completeness.COMPLETE_FOR_PURPOSE,
             uncertainty=()):
    return CurrentYearReductionEvidence(
        "evidence-1",
        "2026/27",
        source,
        effective,
        retrieval,
        completeness,
        first,
        second,
        "source:evidence-1",
        uncertainty,
    )


def evaluate(**overrides):
    return evaluate_poa_reduction_guardrail(
        assessment=overrides.pop("assessment", assessment()),
        proposal=overrides.pop("proposal", proposal()),
        evidence=overrides.pop("evidence", evidence()),
        as_of=overrides.pop("as_of", AS_OF),
        **overrides,
    )


def test_complete_customer_proposal_is_review_ready_not_recommended_or_submitted():
    result = evaluate()
    assert result.status is PoAReductionStatus.REVIEW_READY_FOR_CUSTOMER_HMRC_ACTION
    assert result.ready_for_customer_hmrc_action is True
    assert result.is_hmrc_decision is False
    assert result.recommended_amount is None
    assert result.auto_submission_performed is False
    assert result.proposed_instalments == (Decimal("500.00"), Decimal("500.00"))
    assert "local_estimate_not_hmrc_confirmed" in result.limitations


@pytest.mark.parametrize("field", [
    "customer_intends_to_claim",
    "customer_confirmed_proposed_amounts",
    "under_reduction_interest_warning_acknowledged",
])
def test_each_customer_confirmation_is_required(field):
    candidate = replace(proposal(), **{field: False})
    result = evaluate(proposal=candidate)
    assert result.status is PoAReductionStatus.CUSTOMER_CONFIRMATION_REQUIRED
    assert result.ready_for_customer_hmrc_action is False


@pytest.mark.parametrize("bad", [None, 1, "yes"])
def test_confirmation_fields_are_strict_booleans(bad):
    with pytest.raises(ValueError):
        replace(proposal(), customer_intends_to_claim=bad)


def test_equal_boundary_is_no_reduction():
    result = evaluate(
        proposal=proposal("600.00", "600.00"),
        evidence=evidence("600.00", "600.00"),
    )
    assert result.status is PoAReductionStatus.NO_REDUCTION


def test_one_penny_lower_is_a_reduction_boundary():
    result = evaluate(
        proposal=proposal("599.99", "600.00"),
        evidence=evidence("599.99", "600.00"),
    )
    assert result.status is PoAReductionStatus.REVIEW_READY_FOR_CUSTOMER_HMRC_ACTION


def test_total_not_lower_is_no_reduction():
    result = evaluate(
        proposal=proposal("599.99", "600.01"),
        evidence=evidence("599.99", "600.01"),
    )
    assert result.status is PoAReductionStatus.NO_REDUCTION


def test_lower_total_that_increases_one_instalment_is_conflict():
    result = evaluate(
        proposal=proposal("600.01", "500.00"),
        evidence=evidence("600.01", "500.00"),
    )
    assert result.status is PoAReductionStatus.CONFLICT_REQUIRES_REVIEW


def test_zero_proposal_is_preserved_exactly_but_not_recommended():
    result = evaluate(
        proposal=proposal("0.00", "0.00"),
        evidence=evidence("0.00", "0.00"),
    )
    assert result.status is PoAReductionStatus.REVIEW_READY_FOR_CUSTOMER_HMRC_ACTION
    assert result.proposed_instalments == (Decimal("0.00"), Decimal("0.00"))
    assert result.recommended_amount is None


@pytest.mark.parametrize("status", [
    PoAStatus.NOT_APPLICABLE,
    PoAStatus.FIRST_YEAR_NO_PRECEDING_RETURN,
])
def test_poa_not_applicable_is_distinct(status):
    if status is PoAStatus.FIRST_YEAR_NO_PRECEDING_RETURN:
        item = assess_payments_on_account(
            preceding_year_status=PrecedingYearStatus.FIRST_YEAR,
            as_of=AS_OF,
        )
    else:
        item = assessment(amount="999.99")
    result = evaluate(assessment=item)
    assert result.status is PoAReductionStatus.POA_NOT_APPLICABLE
    assert result.ready_for_customer_hmrc_action is False


def test_missing_proposal_or_evidence_is_insufficient():
    assert evaluate(proposal=None).status is PoAReductionStatus.INSUFFICIENT_FACTS
    assert evaluate(evidence=None).status is PoAReductionStatus.INSUFFICIENT_FACTS


@pytest.mark.parametrize("poa_input,expected", [
    (None, PoAReductionStatus.INSUFFICIENT_FACTS),
    ("conflicting", PoAReductionStatus.CONFLICT_REQUIRES_REVIEW),
    ("stale", PoAReductionStatus.STALE_REQUIRES_REVIEW),
])
def test_unresolved_assessment_fails_closed(poa_input, expected):
    if poa_input is None:
        item = assess_payments_on_account(
            preceding_year_status=PrecedingYearStatus.ESTABLISHED,
            prior_year=None,
            as_of=AS_OF,
        )
    else:
        prior = PriorYearEvidence(
            "2025/26", SourceKind.LOCAL_ESTIMATE, date(2026, 4, 5), AS_OF,
            Completeness.COMPLETE_FOR_PURPOSE,
            income_tax=Decimal("1200"), hicbc=Decimal("0"),
            class_4_nic=Decimal("0"), tax_deducted_at_source=Decimal("0"),
            uncertainty=(poa_input,),
        )
        item = assess_payments_on_account(
            preceding_year_status=PrecedingYearStatus.ESTABLISHED,
            prior_year=prior,
            as_of=AS_OF,
        )
    assert evaluate(assessment=item).status is expected


def test_conflicting_evidence_takes_precedence():
    result = evaluate(evidence=evidence(uncertainty=("conflicting", "stale")))
    assert result.status is PoAReductionStatus.CONFLICT_REQUIRES_REVIEW


@pytest.mark.parametrize("uncertainty", [("missing",), ("incomplete",)])
def test_incomplete_evidence_is_insufficient(uncertainty):
    result = evaluate(evidence=evidence(uncertainty=uncertainty))
    assert result.status is PoAReductionStatus.INSUFFICIENT_FACTS


def test_incomplete_completeness_is_insufficient():
    result = evaluate(evidence=evidence(completeness=Completeness.PARTIAL))
    assert result.status is PoAReductionStatus.INSUFFICIENT_FACTS


def test_stale_evidence_requires_review():
    old = AS_OF - timedelta(days=46)
    result = evaluate(evidence=evidence(retrieval=old, effective=old))
    assert result.status is PoAReductionStatus.STALE_REQUIRES_REVIEW


def test_previously_applicable_assessment_becoming_stale_requires_review():
    old_as_of = AS_OF - timedelta(days=46)
    prior = PriorYearEvidence(
        tax_year="2025/26",
        source=SourceKind.LOCAL_ESTIMATE,
        effective_date=date(2026, 4, 5),
        retrieval_date=old_as_of,
        completeness=Completeness.COMPLETE_FOR_PURPOSE,
        income_tax=Decimal("1200"),
        hicbc=Decimal("0"),
        class_4_nic=Decimal("0"),
        tax_deducted_at_source=Decimal("0"),
    )
    old_assessment = assess_payments_on_account(
        preceding_year_status=PrecedingYearStatus.ESTABLISHED,
        prior_year=prior,
        as_of=old_as_of,
    )
    result = evaluate(assessment=old_assessment)
    assert result.status is PoAReductionStatus.STALE_REQUIRES_REVIEW


def test_future_evidence_is_conflict_not_ready():
    future = AS_OF + timedelta(days=1)
    result = evaluate(evidence=evidence(retrieval=future, effective=AS_OF))
    assert result.status is PoAReductionStatus.CONFLICT_REQUIRES_REVIEW


def test_evidence_tax_year_must_match():
    result = evaluate(evidence=replace(evidence(), tax_year="2027/28"))
    assert result.status is PoAReductionStatus.CONFLICT_REQUIRES_REVIEW


def test_evidence_amounts_must_exactly_bind_proposal():
    result = evaluate(evidence=evidence("499.99", "500.00"))
    assert result.status is PoAReductionStatus.CONFLICT_REQUIRES_REVIEW


@pytest.mark.parametrize("source,limitation", [
    (ReductionEvidenceSource.CUSTOMER_MANUAL,
     "customer_manual_evidence_not_hmrc_confirmed"),
    (ReductionEvidenceSource.LOCAL_ESTIMATE, "local_estimate_not_hmrc_confirmed"),
    (ReductionEvidenceSource.HMRC_ISSUED,
     "hmrc_issued_evidence_does_not_make_this_an_hmrc_decision"),
    (SourceKind.LOCAL_ESTIMATE, "local_estimate_not_hmrc_confirmed"),
    (SourceKind.HMRC_ISSUED,
     "hmrc_issued_evidence_does_not_make_this_an_hmrc_decision"),
])
def test_provenance_remains_distinct(source, limitation):
    item = evidence(source=source)
    result = evaluate(evidence=item)
    assert result.status is PoAReductionStatus.REVIEW_READY_FOR_CUSTOMER_HMRC_ACTION
    assert limitation in result.limitations
    assert result.evidence_source is item.source
    assert result.evidence_source_reference == "source:evidence-1"


def test_warning_and_prohibitions_are_always_explicit():
    result = evaluate()
    assert result.warnings == ("under_reduction_may_lead_to_interest",)
    for value in (
        "recommend_reduction_or_amount",
        "auto_submit_reduction_claim",
        "hmrc_api_or_account_alteration",
        "payment_or_allocation",
        "tax_or_interest_calculation",
        "self_assessment_filing",
        "persistence_or_production_access",
    ):
        assert value in result.prohibited_uses


def test_tampered_poa_amount_fails_closed():
    valid = assessment()
    forged = replace(
        valid,
        instalments=(replace(valid.instalments[0], amount=Decimal("599.99")),
                     valid.instalments[1]),
    )
    result = evaluate(assessment=forged)
    assert result.status is PoAReductionStatus.INSUFFICIENT_FACTS


def test_tampered_poa_dates_or_tax_year_fail_closed():
    valid = assessment()
    wrong_date = replace(
        valid,
        instalments=(replace(valid.instalments[0], due_date=date(2027, 2, 1)),
                     valid.instalments[1]),
    )
    wrong_year = replace(valid, poa_tax_year="2027/28")
    assert evaluate(assessment=wrong_date).status is PoAReductionStatus.INSUFFICIENT_FACTS
    assert evaluate(assessment=wrong_year).status is PoAReductionStatus.INSUFFICIENT_FACTS


def test_forged_not_applicable_status_fails_closed():
    valid = assessment()
    forged = replace(valid, status=PoAStatus.NOT_APPLICABLE, instalments=())
    assert evaluate(assessment=forged).status is PoAReductionStatus.INSUFFICIENT_FACTS


def test_forged_first_year_status_fails_closed():
    valid = assessment()
    forged = replace(
        valid,
        status=PoAStatus.FIRST_YEAR_NO_PRECEDING_RETURN,
        instalments=(),
    )
    assert evaluate(assessment=forged).status is PoAReductionStatus.INSUFFICIENT_FACTS


def test_tampered_source_test_fails_closed():
    valid = assessment()
    forged_test = replace(valid.source_deduction_test, ratio=Decimal("0.50"))
    forged = replace(valid, source_deduction_test=forged_test)
    assert evaluate(assessment=forged).status is PoAReductionStatus.INSUFFICIENT_FACTS


def test_contract_version_and_types_are_strict():
    with pytest.raises(ValueError, match="contract_version"):
        evaluate(assessment=replace(assessment(), contract_version="wrong"))
    with pytest.raises(ValueError):
        evaluate_poa_reduction_guardrail(
            assessment=object(), proposal=proposal(), evidence=evidence(), as_of=AS_OF,
        )
    with pytest.raises(ValueError):
        evaluate(as_of=datetime(2026, 8, 31))


@pytest.mark.parametrize("bad", [True, False, "1.00", Decimal("0.001"), Decimal("NaN")])
def test_bad_staleness_or_money_is_rejected(bad):
    if isinstance(bad, (bool, str)):
        with pytest.raises(ValueError):
            evaluate(stale_after_days=bad)
    else:
        with pytest.raises(ValueError):
            proposal(first=bad)


def test_temporal_order_and_effective_tax_year_are_strict():
    with pytest.raises(ValueError, match="before effective"):
        evidence(retrieval=date(2026, 8, 1), effective=date(2026, 8, 2))
    outside = replace(evidence(), effective_date=date(2026, 4, 5))
    result = evaluate(evidence=outside)
    assert result.status is PoAReductionStatus.CONFLICT_REQUIRES_REVIEW


def test_result_is_deterministic_and_inputs_are_not_mutated():
    a = assessment()
    p = proposal()
    e = evidence()
    before = (a, p, e)
    first = evaluate(assessment=a, proposal=p, evidence=e)
    second = evaluate(assessment=a, proposal=p, evidence=e)
    assert first == second
    assert (a, p, e) == before
    with pytest.raises(FrozenInstanceError):
        p.first_instalment = Decimal("1.00")
