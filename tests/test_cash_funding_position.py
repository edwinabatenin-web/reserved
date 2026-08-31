from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from reserved.engines import cash_obligation_reconciliation as cash
from reserved.engines import payments_on_account as poa
from reserved.engines import sa_account_reconciliation as account
from reserved.engines.cash_funding_position import (
    CashFundingPosition,
    EvidenceCompleteness,
    FundingBalance,
    FundingComputationStatus,
    SetAsideAllocation,
    SetAsideEvidence,
    SetAsideSource,
    compose_cash_funding_position,
)


AS_OF = date(2026, 8, 31)
JAN = date(2027, 1, 31)
JUL = date(2027, 7, 31)


def poa_assessment(*, source=poa.SourceKind.LOCAL_ESTIMATE):
    prior = poa.PriorYearEvidence(
        tax_year="2025/26",
        source=source,
        effective_date=date(2026, 4, 5),
        retrieval_date=AS_OF,
        completeness=poa.Completeness.COMPLETE_FOR_PURPOSE,
        income_tax=Decimal("1200.00"),
        hicbc=Decimal("0.00"),
        class_4_nic=Decimal("0.00"),
        tax_deducted_at_source=Decimal("0.00"),
    )
    return poa.assess_payments_on_account(
        preceding_year_status=poa.PrecedingYearStatus.ESTABLISHED,
        prior_year=prior,
        as_of=AS_OF,
    )


def charge(charge_id, kind, due_date, amount, *, source=account.EvidenceSource.HMRC_ONLINE):
    return account.AccountCharge(
        charge_id=charge_id,
        kind=kind,
        tax_year="2026/27",
        amount=Decimal(amount),
        due_date=due_date,
        effective_date=date(2026, 8, 30),
        observed_on=AS_OF,
        source=source,
        completeness=account.Completeness.COMPLETE_FOR_PURPOSE,
        source_reference=f"source:{charge_id}",
    )


def reconciliation(*, hmrc=True, discrepancy=False, no_obligations=False):
    if no_obligations:
        assessment = poa.assess_payments_on_account(
            preceding_year_status=poa.PrecedingYearStatus.FIRST_YEAR,
            as_of=AS_OF,
        )
        charges = ()
        credits = (
            account.AccountCredit(
                credit_id="hmrc-credit-1",
                kind=account.CreditKind.HMRC_CREDIT,
                amount=Decimal("1.00"),
                effective_date=date(2026, 8, 30),
                observed_on=AS_OF,
                source=account.EvidenceSource.HMRC_ONLINE,
                completeness=account.Completeness.COMPLETE_FOR_PURPOSE,
                source_reference="source:hmrc-credit-1",
            ),
        )
    else:
        assessment = poa_assessment()
        first_amount = "599.99" if discrepancy else "600.00"
        source = account.EvidenceSource.HMRC_ONLINE if hmrc else account.EvidenceSource.MANUAL
        charges = (
            charge("poa-1", account.ChargeKind.PAYMENT_ON_ACCOUNT_1, JAN, first_amount,
                   source=source),
            charge("poa-2", account.ChargeKind.PAYMENT_ON_ACCOUNT_2, JUL, "600.00",
                   source=source),
        )
        credits = ()
    observed = account.reconcile_sa_account(
        charges,
        credits,
        (),
        as_of=AS_OF,
        coverage=account.Completeness.COMPLETE_FOR_PURPOSE,
    )
    return cash.reconcile_cash_obligations(
        account_reconciliation=observed,
        poa_assessment=assessment,
    )


def allocation(label, obligation_id, amount):
    return SetAsideAllocation(label, obligation_id, Decimal(amount))


def evidence(
    total="1000.00",
    *,
    allocations=None,
    source=SetAsideSource.CUSTOMER_RECORDED,
    completeness=EvidenceCompleteness.COMPLETE_FOR_PURPOSE,
    effective=AS_OF,
    observed=AS_OF,
    uncertainty=(),
):
    if allocations is None:
        allocations = (
            allocation("allocation-1", "poa:2026/27:payment_on_account_1", "500.00"),
            allocation("allocation-2", "poa:2026/27:payment_on_account_2", "500.00"),
        )
    return SetAsideEvidence(
        evidence_id="set-aside-1",
        total_amount=total,
        effective_date=effective,
        observed_on=observed,
        source=source,
        completeness=completeness,
        source_reference="record:set-aside-1",
        allocations=allocations,
        uncertainty=uncertainty,
    )


def compose(**overrides):
    selected_reconciliation = (
        overrides.pop("reconciliation")
        if "reconciliation" in overrides
        else reconciliation()
    )
    selected_evidence = (
        overrides.pop("evidence") if "evidence" in overrides else evidence()
    )
    return compose_cash_funding_position(
        obligation_reconciliation=selected_reconciliation,
        set_aside_evidence=selected_evidence,
        as_of=overrides.pop("as_of", AS_OF),
        **overrides,
    )


def test_gap_is_calculated_from_explicit_obligations_and_set_aside():
    result = compose()
    assert result.status is FundingComputationStatus.CALCULATED
    assert result.balance is FundingBalance.GAP
    assert result.total_required == Decimal("1200.00")
    assert result.total_set_aside == Decimal("1000.00")
    assert result.funding_gap == Decimal("200.00")
    assert result.reserve_surplus == Decimal("0.00")
    assert result.dated_coverage_complete is False
    assert [item.remaining_requirement for item in result.requirements] == [
        Decimal("100.00"), Decimal("100.00"),
    ]


def test_exact_and_surplus_boundaries_are_distinct():
    exact = compose(evidence=evidence(
        "1200.00",
        allocations=(
            allocation("a1", "poa:2026/27:payment_on_account_1", "600.00"),
            allocation("a2", "poa:2026/27:payment_on_account_2", "600.00"),
        ),
    ))
    surplus = compose(evidence=evidence(
        "1200.01",
        allocations=(
            allocation("a1", "poa:2026/27:payment_on_account_1", "600.01"),
            allocation("a2", "poa:2026/27:payment_on_account_2", "600.00"),
        ),
    ))
    assert exact.balance is FundingBalance.EXACT
    assert exact.funding_gap == exact.reserve_surplus == Decimal("0.00")
    assert exact.dated_coverage_complete is True
    assert surplus.balance is FundingBalance.SURPLUS
    assert surplus.reserve_surplus == Decimal("0.01")
    assert surplus.dated_coverage_complete is False


def test_unallocated_reserve_does_not_claim_dated_coverage():
    result = compose(evidence=evidence("1000.00", allocations=()))
    assert result.balance is FundingBalance.GAP
    assert result.unallocated_set_aside == Decimal("1000.00")
    assert result.dated_coverage_complete is False
    assert all(item.explicitly_allocated_set_aside == Decimal("0.00")
               for item in result.requirements)
    assert "set_aside_not_fully_allocated_to_dated_obligations" in result.limitations


def test_schedule_preserves_due_dates_and_totals():
    result = compose()
    assert [(item.due_date, item.required, item.remaining_requirement)
            for item in result.schedule] == [
        (JAN, Decimal("600.00"), Decimal("100.00")),
        (JUL, Decimal("600.00"), Decimal("100.00")),
    ]


def test_surplus_is_never_available_cash_or_payment_authority():
    result = compose(evidence=evidence(
        "1300.00",
        allocations=(
            allocation("a1", "poa:2026/27:payment_on_account_1", "700.00"),
            allocation("a2", "poa:2026/27:payment_on_account_2", "600.00"),
        ),
    ))
    assert result.balance is FundingBalance.SURPLUS
    assert "reserve_surplus_is_not_available_or_safe_to_spend" in result.warnings
    assert "present_surplus_as_available_cash" in result.prohibited_uses
    assert "recommend_or_initiate_payment_or_transfer" in result.prohibited_uses


def test_manual_obligation_and_customer_record_are_qualified_not_rejected():
    result = compose(reconciliation=reconciliation(hmrc=False))
    assert result.status is FundingComputationStatus.CALCULATED
    assert result.obligations_hmrc_confirmed is False
    assert "cash_obligations_not_hmrc_confirmed" in result.limitations
    assert "set_aside_amount_customer_recorded_not_independently_confirmed" in result.limitations


def test_financial_account_evidence_remains_provider_neutral():
    result = compose(evidence=evidence(source=SetAsideSource.FINANCIAL_ACCOUNT_EVIDENCE))
    assert result.considered_set_aside.source is SetAsideSource.FINANCIAL_ACCOUNT_EVIDENCE
    assert all("provider" not in item for item in result.prohibited_uses)


def test_missing_evidence_suppresses_point_result():
    result = compose_cash_funding_position(
        obligation_reconciliation=reconciliation(),
        set_aside_evidence=None,
        as_of=AS_OF,
    )
    assert result.status is FundingComputationStatus.INSUFFICIENT_FACTS
    assert result.balance is None
    assert result.total_required is None


@pytest.mark.parametrize("uncertainty,status", [
    (("conflicting",), FundingComputationStatus.CONFLICT_REQUIRES_REVIEW),
    (("missing",), FundingComputationStatus.INSUFFICIENT_FACTS),
    (("incomplete",), FundingComputationStatus.INSUFFICIENT_FACTS),
    (("stale",), FundingComputationStatus.STALE_REQUIRES_REVIEW),
])
def test_uncertainty_fails_closed(uncertainty, status):
    result = compose(evidence=evidence(uncertainty=uncertainty))
    assert result.status is status
    assert result.balance is None


def test_partial_evidence_and_old_evidence_fail_closed():
    partial = compose(evidence=evidence(completeness=EvidenceCompleteness.PARTIAL))
    old = AS_OF - timedelta(days=46)
    stale = compose(evidence=evidence(effective=old, observed=old))
    assert partial.status is FundingComputationStatus.INSUFFICIENT_FACTS
    assert stale.status is FundingComputationStatus.STALE_REQUIRES_REVIEW


def test_future_and_temporally_impossible_evidence_is_rejected():
    future = compose(evidence=evidence(observed=AS_OF + timedelta(days=1)))
    assert future.status is FundingComputationStatus.CONFLICT_REQUIRES_REVIEW
    with pytest.raises(ValueError, match="before effective"):
        evidence(effective=AS_OF, observed=AS_OF - timedelta(days=1))
    with pytest.raises(ValueError):
        compose(as_of=datetime(2026, 8, 31))


def test_unknown_or_duplicate_allocations_fail_closed():
    unknown = compose(evidence=evidence(
        allocations=(allocation("a1", "unknown-obligation", "1.00"),)
    ))
    duplicate = compose(evidence=evidence(
        allocations=(
            allocation("a1", "poa:2026/27:payment_on_account_1", "1.00"),
            allocation("a1", "poa:2026/27:payment_on_account_2", "1.00"),
        )
    ))
    assert unknown.status is FundingComputationStatus.CONFLICT_REQUIRES_REVIEW
    assert duplicate.status is FundingComputationStatus.CONFLICT_REQUIRES_REVIEW


def test_allocations_cannot_exceed_evidenced_total():
    result = compose(evidence=evidence(
        "100.00",
        allocations=(allocation("a1", "poa:2026/27:payment_on_account_1", "100.01"),),
    ))
    assert result.status is FundingComputationStatus.CONFLICT_REQUIRES_REVIEW
    assert result.balance is None


def test_obligation_discrepancy_suppresses_funding_result():
    result = compose(reconciliation=reconciliation(discrepancy=True))
    assert result.status is FundingComputationStatus.OBLIGATION_REVIEW_REQUIRED
    assert result.total_required is None


def test_tampered_obligation_result_is_recomputed_and_rejected():
    original = reconciliation()
    forged_expected = replace(original.expected_obligations[0], amount=Decimal("599.99"))
    forged = replace(
        original,
        expected_obligations=(forged_expected,) + original.expected_obligations[1:],
    )
    result = compose(reconciliation=forged)
    assert result.status is FundingComputationStatus.INSUFFICIENT_FACTS
    assert "obligation_reconciliation_inconsistent" in result.limitations


@pytest.mark.parametrize("field,value", [
    ("total_amount", Decimal("1200.001")),
    ("source", "customer_recorded"),
    ("completeness", "complete_for_purpose"),
])
def test_low_level_forged_set_aside_evidence_fails_closed(field, value):
    forged = evidence()
    object.__setattr__(forged, field, value)
    result = compose(evidence=forged)
    assert result.status is FundingComputationStatus.INSUFFICIENT_FACTS
    assert result.balance is None
    assert "set_aside_evidence_inconsistent" in result.limitations


def test_low_level_temporal_forgery_fails_closed():
    forged = evidence()
    object.__setattr__(forged, "effective_date", AS_OF)
    object.__setattr__(forged, "observed_on", AS_OF - timedelta(days=1))
    result = compose(evidence=forged)
    assert result.status is FundingComputationStatus.INSUFFICIENT_FACTS
    assert result.balance is None


def test_low_level_forged_allocation_fails_closed():
    forged = evidence()
    object.__setattr__(forged.allocations[0], "amount", Decimal("500.001"))
    result = compose(evidence=forged)
    assert result.status is FundingComputationStatus.INSUFFICIENT_FACTS
    assert result.balance is None
    assert "set_aside_evidence_inconsistent" in result.limitations


def test_zero_obligations_with_zero_or_positive_reserve_is_exact_or_surplus():
    empty = reconciliation(no_obligations=True)
    exact = compose(reconciliation=empty, evidence=evidence("0.00", allocations=()))
    surplus = compose(reconciliation=empty, evidence=evidence("1.00", allocations=()))
    assert exact.balance is FundingBalance.EXACT
    assert surplus.balance is FundingBalance.SURPLUS
    assert surplus.reserve_surplus == Decimal("1.00")
    assert surplus.requirements == ()


@pytest.mark.parametrize("bad", [True, False, "1", 1.0, None])
def test_stale_after_days_is_strict(bad):
    with pytest.raises(ValueError):
        compose(stale_after_days=bad)


@pytest.mark.parametrize("bad", [True, Decimal("0.001"), Decimal("NaN"), -1])
def test_money_is_strict(bad):
    with pytest.raises(ValueError):
        evidence(total=bad)


def test_result_is_deterministic_immutable_and_preserves_inputs():
    upstream = reconciliation()
    recorded = evidence()
    before = (upstream, recorded)
    first = compose(reconciliation=upstream, evidence=recorded)
    second = compose(reconciliation=upstream, evidence=recorded)
    assert first == second
    assert isinstance(first, CashFundingPosition)
    assert (upstream, recorded) == before
    with pytest.raises(FrozenInstanceError):
        first.funding_gap = Decimal("0.00")


def test_contract_and_input_types_are_strict():
    with pytest.raises(ValueError, match="contract_version"):
        compose(reconciliation=replace(reconciliation(), contract_version="wrong"))
    with pytest.raises(ValueError):
        compose_cash_funding_position(
            obligation_reconciliation=object(),
            set_aside_evidence=evidence(),
            as_of=AS_OF,
        )
    with pytest.raises(ValueError):
        compose(evidence=object())
