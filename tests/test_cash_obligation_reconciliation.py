from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from reserved.engines.cash_obligation_reconciliation import (
    CashObligationStatus,
    DiscrepancyKind,
    reconcile_cash_obligations,
)
from reserved.engines.payments_on_account import (
    CONTRACT_VERSION as POA_VERSION,
    BalanceStatus,
    BalancingPosition,
    Completeness as PoACompleteness,
    Instalment,
    PoAAssessment,
    PoAStatus,
    SourceKind,
)
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


AS_OF = date(2027, 2, 10)
JAN = date(2027, 1, 31)
JUL = date(2027, 7, 31)


def poa_result(*, status=PoAStatus.APPLICABLE, source=SourceKind.LOCAL_ESTIMATE):
    instalments = (
        Instalment("payment_on_account_1", JAN, Decimal("600.00")),
        Instalment("payment_on_account_2", JUL, Decimal("600.01")),
    ) if status is PoAStatus.APPLICABLE else ()
    return PoAAssessment(
        POA_VERSION,
        "2025/26" if status is not PoAStatus.FIRST_YEAR_NO_PRECEDING_RETURN else None,
        "2026/27" if status is PoAStatus.APPLICABLE else None,
        status,
        source if status is not PoAStatus.FIRST_YEAR_NO_PRECEDING_RETURN else None,
        date(2026, 4, 5) if status is not PoAStatus.FIRST_YEAR_NO_PRECEDING_RETURN else None,
        AS_OF if status is not PoAStatus.FIRST_YEAR_NO_PRECEDING_RETURN else None,
        PoACompleteness.COMPLETE_FOR_PURPOSE
        if status is not PoAStatus.FIRST_YEAR_NO_PRECEDING_RETURN else None,
        Decimal("1200.01") if status is PoAStatus.APPLICABLE else None,
        Decimal("1200.01") if status is PoAStatus.APPLICABLE else None,
        None,
        None,
        instalments,
        (),
        (),
        (),
    )


def balance_result(*, amount="400.00", status=BalanceStatus.REMAINING_BALANCE,
                   source=SourceKind.LOCAL_ESTIMATE):
    remaining = Decimal(amount) if status is BalanceStatus.REMAINING_BALANCE else None
    excess = Decimal(amount) if status is BalanceStatus.EXCESS_CREDIT else None
    return BalancingPosition(
        POA_VERSION,
        "2025/26",
        JAN,
        status,
        source,
        Decimal("1000.00"),
        Decimal("100.00"),
        Decimal("500.00"),
        Decimal("0.00") if status is not BalanceStatus.UNRESOLVED else None,
        remaining,
        excess,
        (),
        (),
        "missing" if status is BalanceStatus.UNRESOLVED else None,
    )


def charge(identity, kind, tax_year, due, amount, *, source=EvidenceSource.HMRC_ONLINE):
    return AccountCharge(
        identity,
        kind,
        tax_year,
        amount,
        due,
        date(2027, 1, 20),
        AS_OF,
        source,
        Completeness.COMPLETE_FOR_PURPOSE,
        f"hmrc:{identity}",
    )


def account_result(charges, *, source_confirmed=True):
    actual = list(charges)
    if not actual:
        # A credit-free empty account cannot itself prove complete coverage in S2;
        # this helper uses an HMRC-confirmed zero charge for no-obligation cases.
        actual = [charge("zero", ChargeKind.OTHER_SELF_ASSESSMENT_CHARGE,
                         "2025/26", JAN, "0.00")]
    if not source_confirmed:
        actual = [replace(item, source=EvidenceSource.MANUAL) for item in actual]
    return reconcile_sa_account(
        actual,
        [],
        [],
        as_of=AS_OF,
        coverage=Completeness.COMPLETE_FOR_PURPOSE,
    )


def credit_only_account():
    observed = AccountCredit(
        "credit-only",
        CreditKind.HMRC_CREDIT,
        "1.00",
        date(2027, 1, 20),
        AS_OF,
        EvidenceSource.HMRC_ONLINE,
        Completeness.COMPLETE_FOR_PURPOSE,
        "hmrc:credit-only",
    )
    return reconcile_sa_account(
        [], [observed], [], as_of=AS_OF,
        coverage=Completeness.COMPLETE_FOR_PURPOSE,
    )


def allocated_account():
    observed_charge = charge(
        "allocated-charge", ChargeKind.BALANCING_PAYMENT,
        "2025/26", JAN, "400.00",
    )
    observed_credit = AccountCredit(
        "allocated-credit",
        CreditKind.PAYMENT,
        "100.00",
        date(2027, 1, 20),
        AS_OF,
        EvidenceSource.HMRC_ONLINE,
        Completeness.COMPLETE_FOR_PURPOSE,
        "hmrc:allocated-credit",
    )
    allocation = ExplicitAllocation(
        "allocation-1",
        observed_charge.charge_id,
        observed_credit.credit_id,
        "100.00",
        AS_OF,
        EvidenceSource.HMRC_ONLINE,
        Completeness.COMPLETE_FOR_PURPOSE,
        "hmrc:allocation-1",
    )
    return reconcile_sa_account(
        [observed_charge], [observed_credit], [allocation], as_of=AS_OF,
        coverage=Completeness.COMPLETE_FOR_PURPOSE,
    )


def exact_poa_charges():
    return [
        charge("poa-1", ChargeKind.PAYMENT_ON_ACCOUNT_1, "2026/27", JAN, "600.00"),
        charge("poa-2", ChargeKind.PAYMENT_ON_ACCOUNT_2, "2026/27", JUL, "600.01"),
    ]


def exact_balance_charge():
    return charge("balance", ChargeKind.BALANCING_PAYMENT,
                  "2025/26", JAN, "400.00")


def test_exact_poa_match_is_aligned_and_keeps_local_expectation_distinct():
    result = reconcile_cash_obligations(
        poa_assessment=poa_result(),
        account_reconciliation=account_result(exact_poa_charges()),
    )
    assert result.status is CashObligationStatus.ALIGNED
    assert result.aligned is True
    assert len(result.matches) == 2
    assert result.expected_obligations[0].source is SourceKind.LOCAL_ESTIMATE
    assert result.matches[0].observed.source is EvidenceSource.HMRC_ONLINE
    assert "local_expectation_not_hmrc_issued" in result.limitations


def test_exact_balancing_match_is_aligned():
    result = reconcile_cash_obligations(
        balancing_position=balance_result(),
        account_reconciliation=account_result([exact_balance_charge()]),
    )
    assert result.status is CashObligationStatus.ALIGNED
    assert result.matches[0].expected.kind is ChargeKind.BALANCING_PAYMENT


def test_combined_match_is_deterministic_and_preserves_references():
    observed = [exact_poa_charges()[1], exact_balance_charge(), exact_poa_charges()[0]]
    result = reconcile_cash_obligations(
        poa_assessment=poa_result(),
        balancing_position=balance_result(),
        account_reconciliation=account_result(observed),
    )
    assert result.status is CashObligationStatus.ALIGNED
    assert [item.expected.kind for item in result.matches] == [
        ChargeKind.BALANCING_PAYMENT,
        ChargeKind.PAYMENT_ON_ACCOUNT_1,
        ChargeKind.PAYMENT_ON_ACCOUNT_2,
    ]
    assert {item.observed.source_reference for item in result.matches} == {
        "hmrc:balance", "hmrc:poa-1", "hmrc:poa-2",
    }
    assert result.considered_poa == poa_result()
    assert result.considered_balancing == balance_result()


@pytest.mark.parametrize("status", [
    PoAStatus.NOT_APPLICABLE,
    PoAStatus.FIRST_YEAR_NO_PRECEDING_RETURN,
])
def test_no_poa_is_aligned_when_no_poa_charge_is_observed(status):
    result = reconcile_cash_obligations(
        poa_assessment=poa_result(status=status),
        account_reconciliation=account_result([exact_balance_charge()]),
        balancing_position=balance_result(),
    )
    assert result.status is CashObligationStatus.ALIGNED
    assert all(item.kind is not ChargeKind.PAYMENT_ON_ACCOUNT_1
               for item in result.expected_obligations)


def test_zero_balancing_position_creates_no_expected_charge():
    result = reconcile_cash_obligations(
        poa_assessment=poa_result(),
        balancing_position=balance_result(amount="0.00"),
        account_reconciliation=account_result(exact_poa_charges()),
    )
    assert result.status is CashObligationStatus.ALIGNED
    assert len(result.expected_obligations) == 2


def test_no_poa_and_zero_balance_align_with_confirmed_no_charge_account():
    result = reconcile_cash_obligations(
        poa_assessment=poa_result(status=PoAStatus.NOT_APPLICABLE),
        balancing_position=balance_result(amount="0.00"),
        account_reconciliation=credit_only_account(),
    )
    assert result.status is CashObligationStatus.ALIGNED
    assert result.expected_obligations == ()
    assert result.matches == ()


def test_excess_credit_creates_no_balancing_charge_expectation():
    result = reconcile_cash_obligations(
        poa_assessment=poa_result(),
        balancing_position=balance_result(amount="10.00", status=BalanceStatus.EXCESS_CREDIT),
        account_reconciliation=account_result(exact_poa_charges()),
    )
    assert result.status is CashObligationStatus.ALIGNED


def discrepancy_for(observed):
    return reconcile_cash_obligations(
        poa_assessment=poa_result(),
        account_reconciliation=account_result(observed),
    )


def test_missing_observed_charge_fails_closed():
    result = discrepancy_for(exact_poa_charges()[:1])
    assert result.status is CashObligationStatus.DISCREPANCY_REQUIRES_REVIEW
    assert DiscrepancyKind.MISSING_OBSERVED_CHARGE in {
        item.kind for item in result.discrepancies
    }


def test_extra_observed_charge_fails_closed():
    result = discrepancy_for(exact_poa_charges() + [exact_balance_charge()])
    assert DiscrepancyKind.EXTRA_OBSERVED_CHARGE in {
        item.kind for item in result.discrepancies
    }


@pytest.mark.parametrize("field,value,kind", [
    ("amount", "600.02", DiscrepancyKind.WRONG_AMOUNT),
    ("due_date", date(2027, 2, 1), DiscrepancyKind.WRONG_DUE_DATE),
    ("tax_year", "2027/28", DiscrepancyKind.WRONG_TAX_YEAR),
])
def test_single_field_mismatch_fails_closed(field, value, kind):
    first = exact_poa_charges()[0]
    first = replace(first, **{field: Decimal(value) if field == "amount" else value})
    result = discrepancy_for([first, exact_poa_charges()[1]])
    assert kind in {item.kind for item in result.discrepancies}
    assert result.aligned is False


def test_wrong_kind_is_missing_plus_extra_not_amount_only_match():
    wrong = charge("wrong", ChargeKind.OTHER_SELF_ASSESSMENT_CHARGE,
                   "2026/27", JAN, "600.00")
    result = discrepancy_for([wrong, exact_poa_charges()[1]])
    kinds = {item.kind for item in result.discrepancies}
    assert DiscrepancyKind.WRONG_KIND in kinds
    assert DiscrepancyKind.MISSING_OBSERVED_CHARGE not in kinds


def test_ambiguous_duplicate_observations_fail_closed():
    duplicate = replace(exact_poa_charges()[0], charge_id="poa-1-copy",
                        source_reference="hmrc:poa-1-copy")
    result = discrepancy_for(exact_poa_charges() + [duplicate])
    assert DiscrepancyKind.AMBIGUOUS_OBSERVED_CHARGE in {
        item.kind for item in result.discrepancies
    }
    assert result.matches == (result.matches[0],)


def test_manual_account_observation_never_aligns():
    result = reconcile_cash_obligations(
        poa_assessment=poa_result(),
        account_reconciliation=account_result(exact_poa_charges(), source_confirmed=False),
    )
    assert result.status is CashObligationStatus.OBSERVATION_NOT_HMRC_CONFIRMED
    assert result.aligned is False
    assert result.matches == ()


@pytest.mark.parametrize("poa_status", [
    PoAStatus.INSUFFICIENT_FACTS,
    PoAStatus.CONFLICT_REQUIRES_REVIEW,
    PoAStatus.STALE_REQUIRES_REVIEW,
])
def test_unresolved_poa_suppresses_point_result(poa_status):
    result = reconcile_cash_obligations(
        poa_assessment=poa_result(status=poa_status),
        account_reconciliation=account_result(exact_poa_charges()),
    )
    assert result.status is CashObligationStatus.INSUFFICIENT_FACTS
    assert result.expected_obligations == ()
    assert result.matches == ()


def test_unresolved_balance_suppresses_point_result():
    result = reconcile_cash_obligations(
        balancing_position=balance_result(status=BalanceStatus.UNRESOLVED),
        account_reconciliation=account_result([exact_balance_charge()]),
    )
    assert result.status is CashObligationStatus.INSUFFICIENT_FACTS


def test_unresolved_account_suppresses_point_result_and_preserves_input():
    unresolved = replace(
        account_result(exact_poa_charges()),
        status=ReconciliationStatus.INSUFFICIENT_FACTS,
        hmrc_confirmed=False,
    )
    result = reconcile_cash_obligations(
        poa_assessment=poa_result(), account_reconciliation=unresolved,
    )
    assert result.status is CashObligationStatus.INSUFFICIENT_FACTS
    assert result.considered_account is unresolved
    assert result.matches == ()


def test_no_local_result_is_insufficient():
    result = reconcile_cash_obligations(
        account_reconciliation=account_result(exact_poa_charges()),
    )
    assert result.status is CashObligationStatus.INSUFFICIENT_FACTS


@pytest.mark.parametrize("bad", [object(), "bad", None])
def test_account_type_is_strict(bad):
    with pytest.raises(ValueError):
        reconcile_cash_obligations(account_reconciliation=bad, poa_assessment=poa_result())


def test_contract_versions_are_strict():
    with pytest.raises(ValueError, match="contract_version"):
        reconcile_cash_obligations(
            poa_assessment=replace(poa_result(), contract_version="wrong"),
            account_reconciliation=account_result(exact_poa_charges()),
        )
    with pytest.raises(ValueError, match="contract_version"):
        reconcile_cash_obligations(
            poa_assessment=poa_result(),
            account_reconciliation=replace(
                account_result(exact_poa_charges()), contract_version="wrong"
            ),
        )


def test_inconsistent_applicable_poa_fails_closed():
    malformed = replace(poa_result(), instalments=poa_result().instalments[:1])
    result = reconcile_cash_obligations(
        poa_assessment=malformed,
        account_reconciliation=account_result(exact_poa_charges()),
    )
    assert result.status is CashObligationStatus.INSUFFICIENT_FACTS


def test_forged_hmrc_confirmation_over_manual_charge_fails_closed():
    forged = replace(
        account_result(exact_poa_charges(), source_confirmed=False),
        hmrc_confirmed=True,
    )
    result = reconcile_cash_obligations(
        poa_assessment=poa_result(), account_reconciliation=forged,
    )
    assert result.status is CashObligationStatus.INSUFFICIENT_FACTS
    assert "account_reconciliation_inconsistent" in result.limitations


def test_account_charge_position_must_retain_exact_source_evidence():
    observed = account_result(exact_poa_charges())
    forged_position = replace(
        observed.charge_positions[0], source_reference="hmrc:substituted"
    )
    forged = replace(
        observed,
        charge_positions=(forged_position,) + observed.charge_positions[1:],
    )
    result = reconcile_cash_obligations(
        poa_assessment=poa_result(), account_reconciliation=forged,
    )
    assert result.status is CashObligationStatus.INSUFFICIENT_FACTS


def test_temporally_impossible_considered_charge_cannot_be_forged_into_alignment():
    observed = account_result(exact_poa_charges())
    original = observed.considered_charges[0]
    forged_evidence = replace(
        original,
        effective_date=AS_OF,
        observed_on=date(2027, 2, 9),
    )
    forged_position = replace(
        observed.charge_positions[0],
        effective_date=forged_evidence.effective_date,
        observed_on=forged_evidence.observed_on,
    )
    forged = replace(
        observed,
        considered_charges=(forged_evidence,) + observed.considered_charges[1:],
        charge_positions=(forged_position,) + observed.charge_positions[1:],
    )
    result = reconcile_cash_obligations(
        poa_assessment=poa_result(), account_reconciliation=forged,
    )
    assert result.status is CashObligationStatus.INSUFFICIENT_FACTS
    assert "account_reconciliation_inconsistent" in result.limitations


@pytest.mark.parametrize("field,value", [
    ("total_credits", Decimal("1.00")),
    ("unallocated_credit", Decimal("1.00")),
    ("net_account_position", Decimal("1.00")),
])
def test_tampered_account_totals_never_align(field, value):
    observed = account_result(exact_poa_charges())
    forged = replace(observed, **{field: value})
    result = reconcile_cash_obligations(
        poa_assessment=poa_result(), account_reconciliation=forged,
    )
    assert result.status is CashObligationStatus.INSUFFICIENT_FACTS
    assert "account_reconciliation_inconsistent" in result.limitations


def test_tampered_credit_provenance_never_aligns():
    observed = allocated_account()
    forged_credit = replace(
        observed.credit_positions[0], source_reference="hmrc:substituted-credit"
    )
    forged = replace(observed, credit_positions=(forged_credit,))
    result = reconcile_cash_obligations(
        balancing_position=balance_result(), account_reconciliation=forged,
    )
    assert result.status is CashObligationStatus.INSUFFICIENT_FACTS
    assert "account_reconciliation_inconsistent" in result.limitations


def test_tampered_allocation_arithmetic_never_aligns():
    observed = allocated_account()
    forged_allocation = replace(
        observed.allocation_positions[0], amount=Decimal("99.00")
    )
    forged = replace(observed, allocation_positions=(forged_allocation,))
    result = reconcile_cash_obligations(
        balancing_position=balance_result(), account_reconciliation=forged,
    )
    assert result.status is CashObligationStatus.INSUFFICIENT_FACTS
    assert "account_reconciliation_inconsistent" in result.limitations


def test_result_and_discrepancy_order_is_input_order_independent():
    observed = [
        replace(exact_poa_charges()[1], amount=Decimal("700.00")),
        exact_balance_charge(),
        replace(exact_poa_charges()[0], amount=Decimal("500.00")),
    ]
    first = discrepancy_for(observed)
    second = discrepancy_for(list(reversed(observed)))
    assert first.expected_obligations == second.expected_obligations
    assert first.discrepancies == second.discrepancies


def test_provenance_and_prohibited_uses_are_explicit():
    account_input = account_result(exact_poa_charges())
    result = reconcile_cash_obligations(
        poa_assessment=poa_result(), account_reconciliation=account_input,
    )
    assert result.considered_account is account_input
    assert result.matches[0].observed.source_reference.startswith("hmrc:")
    assert "autonomous_payment_or_allocation" in result.prohibited_uses
    assert "payment_advice" in result.prohibited_uses
    assert "self_assessment_filing" in result.prohibited_uses
    assert "interest_or_penalty_calculation" in result.prohibited_uses
    assert "production_account_access" in result.prohibited_uses
