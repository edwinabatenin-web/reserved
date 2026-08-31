from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from reserved.engines.sa_account_reconciliation import (
    AccountCharge,
    AccountCredit,
    ChargeKind,
    Completeness,
    CreditKind,
    EvidenceSource,
    ExplicitAllocation,
    ReconciliationStatus,
    reconcile_sa_account,
)


TODAY = date(2027, 2, 10)
COMPLETE = Completeness.COMPLETE_FOR_PURPOSE


def charge(identity="charge-1", amount="1200.00", *, source=EvidenceSource.HMRC_ONLINE,
           observed=TODAY, effective=date(2027, 1, 20),
           due=date(2027, 1, 31), complete=COMPLETE):
    return AccountCharge(identity, ChargeKind.BALANCING_PAYMENT, "2025/26", amount,
                         due, effective, observed, source, complete, f"src-{identity}")


def credit(identity="credit-1", amount="700.00", *, source=EvidenceSource.HMRC_ONLINE,
           observed=TODAY, effective=date(2027, 1, 30), complete=COMPLETE):
    return AccountCredit(identity, CreditKind.PAYMENT, amount, effective,
                         observed, source, complete, f"src-{identity}")


def allocation(identity="alloc-1", amount="700.00", *, charge_id="charge-1",
               credit_id="credit-1", source=EvidenceSource.HMRC_ONLINE,
               observed=TODAY, complete=COMPLETE):
    return ExplicitAllocation(identity, charge_id, credit_id, amount, observed,
                              source, complete, f"src-{identity}")


def reconcile(charges=None, credits=None, allocations=None, **kwargs):
    return reconcile_sa_account(
        [charge()] if charges is None else charges,
        [credit()] if credits is None else credits,
        [allocation()] if allocations is None else allocations,
        as_of=kwargs.pop("as_of", TODAY), coverage=kwargs.pop("coverage", COMPLETE),
        **kwargs,
    )


def test_exact_complete_hmrc_reconciliation():
    result = reconcile()
    assert result.status is ReconciliationStatus.RECONCILED
    assert result.hmrc_confirmed is True
    assert result.total_charges == Decimal("1200.00")
    assert result.total_credits == Decimal("700.00")
    assert result.remaining_charge_balance == Decimal("500.00")
    assert result.unallocated_credit == Decimal("0.00")
    assert result.net_account_position == Decimal("500.00")
    assert result.charge_positions[0].overdue is True
    assert result.charge_positions[0].source_reference == "src-charge-1"
    assert result.charge_positions[0].observed_on == TODAY
    assert result.credit_positions[0].source_reference == "src-credit-1"
    assert result.allocation_positions[0].source_reference == "src-alloc-1"
    assert result.allocation_positions[0].charge_id == "charge-1"
    assert result.allocation_positions[0].credit_id == "credit-1"
    assert result.considered_charges == (charge(),)
    assert result.considered_credits == (credit(),)
    assert result.considered_allocations == (allocation(),)


def test_partial_allocation_and_unallocated_credit_are_not_manufactured():
    result = reconcile(
        credits=[credit(amount="900.00")], allocations=[allocation(amount="400.00")]
    )
    assert result.charge_positions[0].remaining == Decimal("800.00")
    assert result.credit_positions[0].unallocated == Decimal("500.00")
    assert result.net_account_position == Decimal("300.00")


def test_credit_only_complete_position_is_supported():
    result = reconcile(charges=[], credits=[credit(amount="0.01")], allocations=[])
    assert result.status is ReconciliationStatus.RECONCILED
    assert result.net_account_position == Decimal("-0.01")
    assert result.unallocated_credit == Decimal("0.01")


def test_zero_charge_and_credit_reconcile_exactly():
    result = reconcile(charges=[charge(amount="0")], credits=[credit(amount="0")],
                       allocations=[allocation(amount="0")])
    assert result.net_account_position == Decimal("0.00")
    assert result.charge_positions[0].overdue is False


@pytest.mark.parametrize("items,reason", [
    ([charge(), charge()], "duplicate_or_conflicting_charge_identity"),
    ([credit(), credit()], "duplicate_or_conflicting_credit_identity"),
    ([allocation(), allocation()], "duplicate_or_conflicting_allocation_identity"),
])
def test_duplicate_identities_fail_closed(items, reason):
    if isinstance(items[0], AccountCharge):
        result = reconcile(charges=items)
    elif isinstance(items[0], AccountCredit):
        result = reconcile(credits=items)
    else:
        result = reconcile(allocations=items)
    assert result.status is ReconciliationStatus.CONFLICT_REQUIRES_REVIEW
    assert result.net_account_position is None
    assert reason in result.limitations


def test_conflicting_same_identity_never_overwrites_by_source_priority():
    result = reconcile(charges=[charge(), charge(amount="1300", source=EvidenceSource.MANUAL)])
    assert result.status is ReconciliationStatus.CONFLICT_REQUIRES_REVIEW
    assert result.hmrc_confirmed is False
    assert len(result.considered_charges) == 2
    assert {item.amount for item in result.considered_charges} == {
        Decimal("1200.00"), Decimal("1300.00")
    }


@pytest.mark.parametrize("item,reason", [
    (allocation(charge_id="missing"), "allocation_references_unknown_charge"),
    (allocation(credit_id="missing"), "allocation_references_unknown_credit"),
    (allocation(amount="1200.01"), "allocation_exceeds_charge"),
])
def test_dangling_and_charge_overallocation_fail_closed(item, reason):
    result = reconcile(allocations=[item])
    assert result.status is ReconciliationStatus.CONFLICT_REQUIRES_REVIEW
    assert reason in result.limitations


def test_credit_overallocation_fails_closed():
    result = reconcile(allocations=[allocation(amount="700.01")])
    assert result.status is ReconciliationStatus.CONFLICT_REQUIRES_REVIEW
    assert "allocation_exceeds_credit" in result.limitations


@pytest.mark.parametrize("coverage", [Completeness.PARTIAL, Completeness.UNKNOWN])
def test_incomplete_account_coverage_has_no_point_position(coverage):
    result = reconcile(coverage=coverage)
    assert result.status is ReconciliationStatus.INSUFFICIENT_FACTS
    assert result.net_account_position is None


def test_incomplete_item_has_no_point_position():
    result = reconcile(charges=[charge(complete=Completeness.PARTIAL)])
    assert result.status is ReconciliationStatus.INSUFFICIENT_FACTS


def test_no_transactions_is_insufficient_even_with_complete_coverage():
    result = reconcile(charges=[], credits=[], allocations=[])
    assert result.status is ReconciliationStatus.INSUFFICIENT_FACTS


def test_stale_evidence_has_no_point_position():
    observed = TODAY - timedelta(days=46)
    result = reconcile(charges=[charge(observed=observed, effective=observed)])
    assert result.status is ReconciliationStatus.STALE_REQUIRES_REVIEW
    assert result.net_account_position is None


@pytest.mark.parametrize("factory,field", [
    (lambda: charge(observed=TODAY + timedelta(days=1)), "observed_on"),
    (lambda: credit(observed=TODAY + timedelta(days=1)), "observed_on"),
    (lambda: allocation(observed=TODAY + timedelta(days=1)), "observed_on"),
])
def test_future_observations_are_rejected(factory, field):
    item = factory()
    with pytest.raises(ValueError, match=field):
        if isinstance(item, AccountCharge):
            reconcile(charges=[item])
        elif isinstance(item, AccountCredit):
            reconcile(credits=[item])
        else:
            reconcile(allocations=[item])


def test_manual_complete_evidence_reconciles_but_is_not_hmrc_confirmed():
    result = reconcile(
        charges=[charge(source=EvidenceSource.MANUAL)],
        credits=[credit(source=EvidenceSource.MANUAL)],
        allocations=[allocation(source=EvidenceSource.MANUAL)],
    )
    assert result.status is ReconciliationStatus.RECONCILED
    assert result.hmrc_confirmed is False
    assert "position_not_hmrc_confirmed" in result.limitations


def test_local_estimate_charge_never_becomes_hmrc_confirmed():
    result = reconcile(charges=[charge(source=EvidenceSource.LOCAL_ESTIMATE)])
    assert result.hmrc_confirmed is False
    assert "local_estimate_charge_is_not_hmrc_issued" in result.limitations


def test_hmrc_document_can_confirm_complete_explicit_evidence():
    result = reconcile(
        charges=[charge(source=EvidenceSource.HMRC_DOCUMENT)],
        credits=[credit(source=EvidenceSource.HMRC_DOCUMENT)],
        allocations=[allocation(source=EvidenceSource.HMRC_DOCUMENT)],
    )
    assert result.hmrc_confirmed is True


def test_deterministic_charge_and_credit_order():
    later = charge("charge-z", amount="2", due=date(2027, 7, 31))
    earlier = charge("charge-a", amount="1", due=date(2027, 1, 31))
    credit_z = credit("credit-z", amount="2")
    credit_a = AccountCredit("credit-a", CreditKind.HMRC_CREDIT, "1",
                             date(2027, 1, 1), TODAY, EvidenceSource.HMRC_ONLINE,
                             COMPLETE, "src-credit-a")
    result = reconcile(charges=[later, earlier], credits=[credit_z, credit_a], allocations=[])
    assert [item.charge_id for item in result.charge_positions] == ["charge-a", "charge-z"]
    assert [item.credit_id for item in result.credit_positions] == ["credit-a", "credit-z"]


def test_due_today_is_not_overdue():
    result = reconcile(charges=[charge(due=TODAY)], credits=[], allocations=[])
    assert result.charge_positions[0].overdue is False


@pytest.mark.parametrize(
    "bad", [True, False, "NaN", "Infinity", "-0.01", "0.001", "1E+999999"]
)
def test_malformed_money_rejected(bad):
    with pytest.raises(ValueError):
        charge(amount=bad)


@pytest.mark.parametrize("bad", ["2026/26", "26/27", "2026-27", 2026])
def test_malformed_tax_year_rejected(bad):
    with pytest.raises(ValueError):
        AccountCharge("charge-1", ChargeKind.BALANCING_PAYMENT, bad, "1",
                      TODAY, TODAY, TODAY, EvidenceSource.HMRC_ONLINE, COMPLETE, "src-1")


def test_datetime_is_not_silently_accepted_as_date():
    with pytest.raises(ValueError, match="datetime"):
        AccountCredit("credit-1", CreditKind.PAYMENT, "1", TODAY,
                      datetime(2027, 2, 10), EvidenceSource.HMRC_ONLINE, COMPLETE, "src-1")


def test_missing_required_date_is_rejected():
    with pytest.raises(ValueError, match="effective_date"):
        AccountCredit("credit-1", CreditKind.PAYMENT, "1", None, TODAY,
                      EvidenceSource.HMRC_ONLINE, COMPLETE, "src-1")


def test_datetime_as_of_is_rejected():
    with pytest.raises(ValueError, match="as_of"):
        reconcile(as_of=datetime(2027, 2, 10))


@pytest.mark.parametrize("enum_value", ["bank_inference", "unsupported", 1, None])
def test_unsupported_source_rejected(enum_value):
    with pytest.raises(ValueError):
        AccountCredit("credit-1", CreditKind.PAYMENT, "1", TODAY, TODAY,
                      enum_value, COMPLETE, "src-1")


def test_future_effective_date_rejected_at_reconciliation_boundary():
    item = AccountCredit("credit-1", CreditKind.PAYMENT, "1", TODAY + timedelta(days=1),
                         TODAY, EvidenceSource.HMRC_ONLINE, COMPLETE, "src-1")
    with pytest.raises(ValueError, match="effective_date"):
        reconcile(credits=[item], allocations=[])


@pytest.mark.parametrize("item_kind", ["charge", "credit"])
def test_effective_date_after_observation_is_rejected(item_kind):
    observed = date(2027, 1, 15)
    effective = date(2027, 1, 16)
    with pytest.raises(ValueError, match="after observed_on"):
        if item_kind == "charge":
            reconcile(charges=[charge(observed=observed, effective=effective)],
                      credits=[], allocations=[], as_of=TODAY)
        else:
            reconcile(charges=[], credits=[credit(observed=observed, effective=effective)],
                      allocations=[], as_of=TODAY)


def test_allocation_positions_are_deterministic_and_lossless():
    alloc_z = allocation("alloc-z", amount="300")
    alloc_a = allocation("alloc-a", amount="400")
    result = reconcile(allocations=[alloc_z, alloc_a])
    assert [item.allocation_id for item in result.allocation_positions] == [
        "alloc-a", "alloc-z"
    ]
    assert result.considered_allocations == (alloc_a, alloc_z)


@pytest.mark.parametrize("stale", [True, 1.0, "45", -1])
def test_bad_staleness_policy_rejected(stale):
    with pytest.raises(ValueError):
        reconcile(stale_after_days=stale)


def test_prohibited_uses_and_observed_only_limitation_are_always_explicit():
    result = reconcile()
    assert "autonomous_payment_or_reallocation" in result.prohibited_uses
    assert "self_assessment_filing" in result.prohibited_uses
    assert "debt_or_enforcement_action" in result.prohibited_uses
    assert "observed_allocations_only_no_automatic_allocation" in result.limitations
