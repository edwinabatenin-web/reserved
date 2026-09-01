from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest

from reserved.engines import cash_funding_position as funding
from reserved.engines import cash_obligation_reconciliation as obligations
from reserved.engines import payments_on_account as poa
from reserved.engines import sa_account_reconciliation as account
from reserved.engines.annual_to_cash_integration import (
    AnnualToCashStatus,
    balance_item_identity,
    cash_ready_annual_position_identity,
    compose_annual_to_cash_position,
    payment_made_identity,
    prior_year_evidence_identity,
)
from reserved.engines.annual_loan_reconciliation import (
    AnnualLoanIncomeBasis,
    DeductionRepresentation,
    LoanBasisEvidence,
    LoanComponent,
    LoanDeductionEvidence,
    reconcile_annual_student_loans,
)
from reserved.engines.cash_ready_annual_position import (
    NoStudentLoanEvidence,
    annual_position_identity,
    compose_cash_ready_annual_position,
    student_loan_position_identity,
)
from reserved.engines.integrated_annual_position import calculate_annual_position


AS_OF = date(2027, 4, 5)
BPA = {
    "blind_persons_allowance_entitled": False,
    "blind_persons_allowance_transferred_in": "0",
    "blind_persons_allowance_transferred_out": "0",
}


def annual_position():
    annual_tax = calculate_annual_position({"employment_income": "30000", **BPA})
    no_loans = NoStudentLoanEvidence(
        "annual-no-loan", "2026/27", "uk-2026-27-v4", AS_OF,
        "person-a", "synthetic", "synthetic:no-loan", True,
    )
    return compose_cash_ready_annual_position(
        annual_tax,
        no_loans,
        annual_tax_reference=annual_position_identity(annual_tax),
        student_loan_reference=student_loan_position_identity(no_loans),
        as_of=AS_OF,
    )


def annual_position_with_plan_2():
    annual_tax = calculate_annual_position({"employment_income": "103000", **BPA})
    basis = LoanBasisEvidence(
        "loan-basis", "synthetic", "synthetic:loan-basis", "person-a", AS_OF,
        "2026/27 annual basis", True,
    )
    deduction = LoanDeductionEvidence(
        "loan-deduction", LoanComponent.PLAN_2, Decimal("3000.00"), "2026/27",
        AS_OF, AS_OF, "job-a", DeductionRepresentation.EMPLOYMENT_CUMULATIVE,
        True, "synthetic", "synthetic:loan-deduction",
    )
    loans = reconcile_annual_student_loans(
        AnnualLoanIncomeBasis("103000", ("loan-basis",), True, True, (basis,)),
        (2,), (deduction,), as_of=AS_OF, declared_employment_ids=("job-a",),
    )
    return compose_cash_ready_annual_position(
        annual_tax,
        loans,
        annual_tax_reference=annual_position_identity(annual_tax),
        student_loan_reference=student_loan_position_identity(loans),
        as_of=AS_OF,
    )


def prior_year(*, amount="1200.00", source=poa.SourceKind.HMRC_ISSUED,
               effective=AS_OF, retrieved=AS_OF, uncertainty=()):
    return poa.PriorYearEvidence(
        tax_year="2026/27",
        source=source,
        effective_date=effective,
        retrieval_date=retrieved,
        completeness=poa.Completeness.COMPLETE_FOR_PURPOSE,
        income_tax=Decimal(amount),
        hicbc=Decimal("0.00"),
        class_4_nic=Decimal("0.00"),
        tax_deducted_at_source=Decimal("0.00"),
        uncertainty=uncertainty,
    )


def balance_item(amount, source=poa.SourceKind.HMRC_ISSUED, retrieved=AS_OF):
    return poa.BalanceItem(
        Decimal(amount), source, poa.Completeness.COMPLETE_FOR_PURPOSE, retrieved
    )


def payment(amount="100.00", *, paid_on=AS_OF, retrieved=AS_OF, reference="cash:payment-1"):
    return poa.PaymentMade(
        poa.PaymentKind.BALANCING_PAYMENT,
        Decimal(amount),
        poa.SourceKind.HMRC_ISSUED,
        paid_on,
        retrieved,
        reference=reference,
    )


def expected_positions(
    annual,
    *,
    status=poa.PrecedingYearStatus.ESTABLISHED,
    prior=None,
    deductions=None,
    prior_poa=None,
    payments=(),
):
    prior = prior if prior is not None else prior_year()
    deductions = deductions if deductions is not None else balance_item("0.00")
    prior_poa = prior_poa if prior_poa is not None else balance_item("0.00")
    assessed = poa.assess_payments_on_account(
        preceding_year_status=status,
        prior_year=prior if status is poa.PrecedingYearStatus.ESTABLISHED else None,
        as_of=AS_OF,
    )
    balancing = poa.compose_balancing_position(
        tax_year=annual.tax_year,
        final_liability=poa.BalanceItem(
            annual.final_self_assessment_liability,
            poa.SourceKind.LOCAL_ESTIMATE,
            poa.Completeness.COMPLETE_FOR_PURPOSE,
            AS_OF,
        ),
        deductions_credits=deductions,
        prior_poa=prior_poa,
        payments_made=payments,
        as_of=AS_OF,
    )
    return assessed, balancing


def observed_account(assessed, balancing, *, hmrc=True, mismatch=False):
    source = account.EvidenceSource.HMRC_ONLINE if hmrc else account.EvidenceSource.MANUAL
    charges = []
    for instalment in assessed.instalments:
        kind = {
            "payment_on_account_1": account.ChargeKind.PAYMENT_ON_ACCOUNT_1,
            "payment_on_account_2": account.ChargeKind.PAYMENT_ON_ACCOUNT_2,
        }[instalment.label]
        amount = instalment.amount + (Decimal("1.00") if mismatch and not charges else Decimal("0"))
        charges.append(account.AccountCharge(
            f"charge-{instalment.label}", kind, assessed.poa_tax_year, amount,
            instalment.due_date, AS_OF, AS_OF, source,
            account.Completeness.COMPLETE_FOR_PURPOSE,
            f"account:{instalment.label}",
        ))
    if balancing.status is poa.BalanceStatus.REMAINING_BALANCE and balancing.remaining_balance:
        charges.append(account.AccountCharge(
            "charge-balancing", account.ChargeKind.BALANCING_PAYMENT,
            balancing.tax_year, balancing.remaining_balance, balancing.due_date,
            AS_OF, AS_OF, source, account.Completeness.COMPLETE_FOR_PURPOSE,
            "account:balancing",
        ))
    credits = ()
    if not charges:
        credits = (account.AccountCredit(
            "credit-evidence", account.CreditKind.HMRC_CREDIT, Decimal("1.00"),
            AS_OF, AS_OF, source, account.Completeness.COMPLETE_FOR_PURPOSE,
            "account:credit-evidence",
        ),)
    return account.reconcile_sa_account(
        charges, credits, (), as_of=AS_OF,
        coverage=account.Completeness.COMPLETE_FOR_PURPOSE,
    )


def set_aside_for(assessed, balancing, amount=None):
    expected = obligations.reconcile_cash_obligations(
        account_reconciliation=observed_account(assessed, balancing),
        poa_assessment=assessed,
        balancing_position=balancing,
    ).expected_obligations
    total = sum((item.amount for item in expected), Decimal("0.00"))
    selected = total if amount is None else Decimal(amount)
    allocations = []
    remaining = selected
    for index, item in enumerate(expected):
        allocated = min(item.amount, remaining)
        if allocated:
            allocations.append(funding.SetAsideAllocation(
                f"set-aside-allocation-{index}", item.obligation_id, allocated
            ))
        remaining -= allocated
    return funding.SetAsideEvidence(
        "set-aside-evidence", selected, AS_OF, AS_OF,
        funding.SetAsideSource.CUSTOMER_RECORDED,
        funding.EvidenceCompleteness.COMPLETE_FOR_PURPOSE,
        "set-aside:source", tuple(allocations), (),
    )


def compose(
    *, annual=None, status=poa.PrecedingYearStatus.ESTABLISHED,
    prior=None, deductions=None, prior_poa=None, payments=(),
    hmrc=True, mismatch=False, set_aside="exact", annual_reference=None,
    deductions_evidence_ids=("cash:deductions-credits",),
    prior_poa_evidence_ids=("cash:prior-poa",),
    deductions_reference=None,
):
    annual = annual if annual is not None else annual_position()
    prior = prior if prior is not None else (
        prior_year() if status is poa.PrecedingYearStatus.ESTABLISHED else None
    )
    deductions = deductions if deductions is not None else balance_item("0.00")
    prior_poa = prior_poa if prior_poa is not None else balance_item("0.00")
    assessed, balancing = expected_positions(
        annual, status=status, prior=prior, deductions=deductions,
        prior_poa=prior_poa, payments=payments,
    )
    account_result = observed_account(assessed, balancing, hmrc=hmrc, mismatch=mismatch)
    evidence = None if set_aside is None else set_aside_for(
        assessed, balancing, None if set_aside == "exact" else set_aside
    )
    return compose_annual_to_cash_position(
        annual_position=annual,
        annual_position_reference=(
            annual_reference or cash_ready_annual_position_identity(annual)
        ),
        preceding_year_status=status,
        prior_year_evidence=prior,
        prior_year_reference=(prior_year_evidence_identity(prior) if prior else None),
        deductions_credits=deductions,
        deductions_credits_reference=(deductions_reference or balance_item_identity(
            deductions, channel="deductions-credits", evidence_ids=deductions_evidence_ids
        )),
        deductions_credits_evidence_ids=deductions_evidence_ids,
        prior_poa=prior_poa,
        prior_poa_reference=balance_item_identity(
            prior_poa, channel="prior-poa", evidence_ids=prior_poa_evidence_ids
        ),
        prior_poa_evidence_ids=prior_poa_evidence_ids,
        payments_made=payments,
        payment_content_references=tuple(
            payment_made_identity(item) for item in payments
        ),
        account_reconciliation=account_result,
        set_aside_evidence=evidence,
        as_of=AS_OF,
    )


def test_complete_annual_position_composes_poa_balance_obligations_and_funding():
    result = compose()
    assert result.status is AnnualToCashStatus.QUALIFIED_LOCAL_RESULT
    assert result.final_self_assessment_liability == Decimal("3486.00")
    assert result.poa_assessment.status is poa.PoAStatus.APPLICABLE
    assert len(result.poa_assessment.instalments) == 2
    assert result.balancing_position.remaining_balance == Decimal("3486.00")
    assert result.obligation_reconciliation.status is obligations.CashObligationStatus.ALIGNED
    assert result.funding_position.status is funding.FundingComputationStatus.CALCULATED
    assert result.funding_position.balance is funding.FundingBalance.EXACT


def test_supported_student_loan_enters_final_balance_but_never_poa_basis():
    annual = annual_position_with_plan_2()
    result = compose(annual=annual)
    assert annual.student_loan_self_assessment_amount > Decimal("0.00")
    assert result.balancing_position.final_liability == (
        annual.annual_tax_liability + annual.student_loan_self_assessment_amount
    )
    assert annual.poa_excluded_families == ("plan_2",)
    assert result.poa_assessment.relevant_amount == Decimal("1200.00")
    assert [item.amount for item in result.poa_assessment.instalments] == [
        Decimal("600.00"), Decimal("600.00")
    ]


def test_first_year_never_invents_prior_year_poa():
    result = compose(status=poa.PrecedingYearStatus.FIRST_YEAR)
    assert result.poa_assessment.status is poa.PoAStatus.FIRST_YEAR_NO_PRECEDING_RETURN
    assert result.poa_assessment.instalments == ()
    assert [item.kind for item in result.obligation_reconciliation.expected_obligations] == [
        account.ChargeKind.BALANCING_PAYMENT
    ]


def test_first_year_conflicting_prior_evidence_fails_closed():
    annual = annual_position()
    deductions = balance_item("0.00")
    prior_poa = balance_item("0.00")
    assessed, balancing = expected_positions(
        annual, status=poa.PrecedingYearStatus.FIRST_YEAR,
        prior=None, deductions=deductions, prior_poa=prior_poa,
    )
    prior = prior_year()
    result = compose_annual_to_cash_position(
        annual_position=annual,
        annual_position_reference=cash_ready_annual_position_identity(annual),
        preceding_year_status=poa.PrecedingYearStatus.FIRST_YEAR,
        prior_year_evidence=prior,
        prior_year_reference=prior_year_evidence_identity(prior),
        deductions_credits=deductions,
        deductions_credits_reference=balance_item_identity(
            deductions, channel="deductions-credits",
            evidence_ids=("cash:deductions-credits",),
        ),
        deductions_credits_evidence_ids=("cash:deductions-credits",),
        prior_poa=prior_poa,
        prior_poa_reference=balance_item_identity(
            prior_poa, channel="prior-poa", evidence_ids=("cash:prior-poa",),
        ),
        prior_poa_evidence_ids=("cash:prior-poa",),
        payments_made=(), payment_content_references=(),
        account_reconciliation=observed_account(assessed, balancing),
        set_aside_evidence=None, as_of=AS_OF,
    )
    assert result.status is AnnualToCashStatus.UNRESOLVED
    assert "first_year_conflicts_with_prior_year_evidence" in result.limitations


def test_first_year_nonzero_prior_poa_fails_closed():
    result = compose(
        status=poa.PrecedingYearStatus.FIRST_YEAR,
        prior_poa=balance_item("600.00"),
    )
    assert result.status is AnnualToCashStatus.UNRESOLVED
    assert result.balancing_position is None
    assert "first_year_has_nonzero_prior_poa" in result.limitations


def test_prior_poa_deductions_and_payment_are_each_applied_once():
    result = compose(
        deductions=balance_item("100.00"),
        prior_poa=balance_item("600.00"),
        payments=(payment("100.00"),),
    )
    assert result.balancing_position.remaining_balance == Decimal("2686.00")


def test_excess_credit_remains_non_spendable_and_creates_no_balance_charge():
    result = compose(deductions=balance_item("4000.00"))
    assert result.balancing_position.status is poa.BalanceStatus.EXCESS_CREDIT
    assert result.balancing_position.excess_credit == Decimal("514.00")
    assert all(
        item.kind is not account.ChargeKind.BALANCING_PAYMENT
        for item in result.obligation_reconciliation.expected_obligations
    )
    assert "present_surplus_as_available_or_safe_to_spend" in result.prohibited_uses


@pytest.mark.parametrize("amount,applies", [("1000.00", True), ("999.99", False)])
def test_statutory_poa_fixed_amount_boundary_is_preserved(amount, applies):
    result = compose(prior=prior_year(amount=amount))
    assert (result.poa_assessment.status is poa.PoAStatus.APPLICABLE) is applies


def test_duplicate_payment_identity_fails_closed_before_arithmetic():
    duplicate = payment("100.00")
    result = compose(payments=(duplicate, duplicate))
    assert result.status is AnnualToCashStatus.UNRESOLVED
    assert "evidence_identity_reused_across_cash_channels" in result.limitations


def test_forged_subpenny_or_plain_string_balance_evidence_is_rejected():
    forged_penny = balance_item("0.00")
    object.__setattr__(forged_penny, "amount", Decimal("0.001"))
    with pytest.raises(ValueError, match="exact-penny"):
        compose(deductions=forged_penny)

    forged_source = balance_item("0.00")
    object.__setattr__(forged_source, "source", "hmrc_issued")
    with pytest.raises(ValueError, match="exact-penny"):
        compose(deductions=forged_source)


def test_balance_source_ids_are_content_bound_and_checked_against_account_evidence():
    item = balance_item("0.00")
    trusted = balance_item_identity(
        item, channel="deductions-credits", evidence_ids=("cash:deductions-credits",)
    )
    with pytest.raises(ValueError, match="exact supplied content"):
        compose(
            deductions=item,
            deductions_evidence_ids=("cash:substituted",),
            deductions_reference=trusted,
        )

    duplicated = compose(deductions_evidence_ids=("account:balancing",))
    assert duplicated.status is AnnualToCashStatus.UNRESOLVED
    assert "evidence_identity_reused_in_account_channel" in duplicated.limitations


def test_forged_or_mismatched_annual_content_identity_is_rejected():
    original = annual_position()
    reference = cash_ready_annual_position_identity(original)
    forged = replace(
        original,
        final_self_assessment_liability=original.final_self_assessment_liability + Decimal("1.00"),
    )
    with pytest.raises(ValueError, match="exact supplied content"):
        compose(annual=forged, annual_reference=reference)


def test_unready_annual_position_suppresses_all_downstream_point_results():
    original = annual_position()
    unready = replace(
        original,
        calculation_status="unresolved",
        component_set_complete=False,
        annual_tax_liability=None,
        student_loan_self_assessment_amount=None,
        final_self_assessment_liability=None,
    )
    result = compose(annual=unready)
    assert result.status is AnnualToCashStatus.UNRESOLVED
    assert result.poa_assessment is None
    assert result.balancing_position is None
    assert result.final_self_assessment_liability is None


def test_hmrc_and_manual_observations_preserve_identical_arithmetic_but_qualification():
    hmrc = compose(hmrc=True)
    manual = compose(hmrc=False)
    assert hmrc.funding_position.total_required == manual.funding_position.total_required
    assert hmrc.obligation_reconciliation.account_hmrc_confirmed is True
    assert manual.obligation_reconciliation.account_hmrc_confirmed is False
    assert manual.status is AnnualToCashStatus.QUALIFIED_LOCAL_RESULT


def test_account_discrepancy_requires_review_and_suppresses_final_point_result():
    result = compose(mismatch=True)
    assert result.status is AnnualToCashStatus.REVIEW_REQUIRED
    assert result.final_self_assessment_liability is None
    assert result.obligation_reconciliation.discrepancies


def test_missing_stale_or_conflicting_evidence_fails_closed():
    stale = compose(prior=prior_year(
        effective=AS_OF - timedelta(days=60),
        retrieved=AS_OF - timedelta(days=46),
    ))
    assert stale.status is AnnualToCashStatus.UNRESOLVED
    assert stale.poa_assessment.status is poa.PoAStatus.STALE_REQUIRES_REVIEW

    conflicting = compose(prior=prior_year(uncertainty=("conflicting",)))
    assert conflicting.status is AnnualToCashStatus.UNRESOLVED
    assert conflicting.poa_assessment.status is poa.PoAStatus.CONFLICT_REQUIRES_REVIEW

    with pytest.raises(ValueError, match="future"):
        compose(prior=prior_year(retrieved=AS_OF + timedelta(days=1)))

    with pytest.raises(ValueError, match="invalid"):
        compose(prior=prior_year(retrieved=AS_OF - timedelta(days=1)))

    with pytest.raises(ValueError, match="invalid"):
        compose(payments=(payment(retrieved=AS_OF - timedelta(days=1)),))


def test_recomputed_identity_cannot_make_an_invalid_annual_contract_usable():
    original = annual_position()
    invalid = replace(original, contract_version="reserved-cash-ready-annual-position/2.0")
    result = compose(annual=invalid)
    assert result.status is AnnualToCashStatus.UNRESOLVED
    assert "annual_position_contract_version_invalid" in result.limitations

    fabricated_loan = replace(
        original,
        student_loan_self_assessment_amount=Decimal("100.00"),
        final_self_assessment_liability=original.final_self_assessment_liability + Decimal("100.00"),
    )
    fabricated_result = compose(annual=fabricated_loan)
    assert fabricated_result.status is AnnualToCashStatus.UNRESOLVED
    assert "annual_position_loan_components_invalid" in fabricated_result.limitations

    with_loan = annual_position_with_plan_2()
    forged_component = replace(with_loan.loan_components[0], component="plan_2")
    forged_nested = replace(with_loan, loan_components=(forged_component,))
    nested_result = compose(annual=forged_nested)
    assert nested_result.status is AnnualToCashStatus.UNRESOLVED
    assert "annual_position_loan_components_invalid" in nested_result.limitations

    wrong_effective_date = replace(original, as_of=AS_OF - timedelta(days=1))
    date_result = compose(annual=wrong_effective_date)
    assert date_result.status is AnnualToCashStatus.UNRESOLVED
    assert "annual_position_date_invalid" in date_result.limitations


def test_funding_gap_and_surplus_remain_distinct_and_surplus_is_never_spendable():
    exact = compose()
    gap = compose(set_aside="1000.00")
    surplus = compose(set_aside="5000.00")
    assert exact.funding_position.balance is funding.FundingBalance.EXACT
    assert gap.funding_position.balance is funding.FundingBalance.GAP
    assert gap.funding_position.funding_gap > Decimal("0.00")
    assert surplus.funding_position.balance is funding.FundingBalance.SURPLUS
    assert surplus.funding_position.reserve_surplus > Decimal("0.00")
    assert "present_surplus_as_available_or_safe_to_spend" in surplus.prohibited_uses


def test_missing_set_aside_evidence_keeps_obligations_but_suppresses_funding_result():
    result = compose(set_aside=None)
    assert result.status is AnnualToCashStatus.UNRESOLVED
    assert result.obligation_reconciliation.status is obligations.CashObligationStatus.ALIGNED
    assert result.funding_position.status is funding.FundingComputationStatus.INSUFFICIENT_FACTS
    assert result.final_self_assessment_liability is None
