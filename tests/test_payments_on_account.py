"""Independent tests for the pure Payments on Account component."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from reserved.engines.payments_on_account import (
    CONTRACT_VERSION,
    BalanceItem,
    BalanceStatus,
    Completeness,
    IncomeTaxScope,
    PaymentKind,
    PaymentMade,
    PoAStatus,
    PrecedingYearStatus,
    PriorYearEvidence,
    SourceKind,
    assess_payments_on_account,
    compose_balancing_position,
)


TODAY = date(2026, 8, 31)


def prior_year(
    *,
    tax_year="2025/26",
    source=SourceKind.HMRC_ISSUED,
    completeness=Completeness.COMPLETE_FOR_PURPOSE,
    retrieval_date=TODAY,
    income_tax_scope=IncomeTaxScope.EXCLUDES_HICBC,
    income_tax=None,
    hicbc=None,
    class_4_nic=None,
    student_loan_repayment=None,
    class_2_nic=None,
    capital_gains_tax=None,
    tax_deducted_at_source=None,
    uncertainty=(),
    effective_date=date(2026, 1, 31),
):
    return PriorYearEvidence(
        tax_year=tax_year,
        source=source,
        effective_date=effective_date,
        retrieval_date=retrieval_date,
        completeness=completeness,
        income_tax_scope=income_tax_scope,
        income_tax=income_tax,
        hicbc=hicbc,
        class_4_nic=class_4_nic,
        student_loan_repayment=student_loan_repayment,
        class_2_nic=class_2_nic,
        capital_gains_tax=capital_gains_tax,
        tax_deducted_at_source=tax_deducted_at_source,
        uncertainty=uncertainty,
    )


def complete_prior_year(**overrides):
    values = dict(
        tax_year="2025/26",
        source=SourceKind.HMRC_ISSUED,
        completeness=Completeness.COMPLETE_FOR_PURPOSE,
        retrieval_date=TODAY,
        income_tax_scope=IncomeTaxScope.EXCLUDES_HICBC,
        income_tax="2500",
        hicbc="0",
        class_4_nic="500",
        student_loan_repayment="200",
        class_2_nic="150",
        capital_gains_tax="300",
        tax_deducted_at_source="400",
        uncertainty=(),
        effective_date=date(2026, 1, 31),
    )
    values.update(overrides)
    return PriorYearEvidence(**values)


def item(amount, *, source=SourceKind.HMRC_ISSUED,
         completeness=Completeness.COMPLETE_FOR_PURPOSE, retrieval_date=TODAY):
    return BalanceItem(
        amount=amount, source=source, completeness=completeness,
        retrieval_date=retrieval_date,
    )


def payment(kind, amount, *, reference=None, source=SourceKind.HMRC_ISSUED,
            retrieval_date=TODAY, paid_on=None):
    return PaymentMade(
        kind=kind, amount=amount, source=source, reference=reference,
        retrieval_date=retrieval_date, paid_on=paid_on,
    )


def assess(evidence, **kwargs):
    return assess_payments_on_account(
        preceding_year_status=PrecedingYearStatus.ESTABLISHED,
        prior_year=evidence,
        as_of=TODAY,
        **kwargs,
    )


# ── Fixed-amount test boundary ────────────────────────────────────────────────

def test_fixed_amount_test_at_999_99_1000_00_and_1000_01():
    below = assess(complete_prior_year(
        income_tax="999.99", hicbc="0", class_4_nic="0", student_loan_repayment="0",
        tax_deducted_at_source="0",
    ))
    at = assess(complete_prior_year(
        income_tax="1000.00", hicbc="0", class_4_nic="0", student_loan_repayment="0",
        tax_deducted_at_source="0",
    ))
    above = assess(complete_prior_year(
        income_tax="1000.01", hicbc="0", class_4_nic="0", student_loan_repayment="0",
        tax_deducted_at_source="0",
    ))

    assert below.fixed_amount_test.meets_threshold is False
    assert below.status is PoAStatus.NOT_APPLICABLE
    assert below.instalments == ()

    # Exactly £1,000 meets the threshold (TMA 1970 s59A(1)(c)) and produces
    # two equal £500 instalments.
    assert at.fixed_amount_test.meets_threshold is True
    assert at.status is PoAStatus.APPLICABLE
    assert at.instalments[0].amount == Decimal("500.00")
    assert at.instalments[1].amount == Decimal("500.00")

    assert above.fixed_amount_test.meets_threshold is True
    assert above.status is PoAStatus.APPLICABLE
    assert above.instalments[0].amount == Decimal("500.00")
    assert above.instalments[1].amount == Decimal("500.01")


def test_fixed_amount_test_applies_to_relevant_amount_not_gross_basis():
    result = assess(complete_prior_year(
        income_tax="1500", hicbc="0", class_4_nic="0", student_loan_repayment="0",
        tax_deducted_at_source="600",
    ))
    # Gross basis £1,500 exceeds £1,000 but the relevant amount is only £900,
    # so the fixed threshold is not met.
    assert result.poa_basis == Decimal("1500.00")
    assert result.relevant_amount == Decimal("900.00")
    assert result.fixed_amount_test.relevant_amount == Decimal("900.00")
    assert result.fixed_amount_test.meets_threshold is False
    assert result.status is PoAStatus.NOT_APPLICABLE
    assert result.instalments == ()


# ── Tax-deducted-at-source test boundary ──────────────────────────────────────

def test_source_deduction_test_below_at_and_above_80_percent():
    # Basis is £10,000 so the relevant amount stays above the £1,000 fixed
    # threshold in all three cases, isolating the 80% source-deduction test.
    below = assess(complete_prior_year(
        income_tax="10000", hicbc="0", class_4_nic="0", student_loan_repayment="0",
        tax_deducted_at_source="7999.99",
    ))
    at = assess(complete_prior_year(
        income_tax="10000", hicbc="0", class_4_nic="0", student_loan_repayment="0",
        tax_deducted_at_source="8000.00",
    ))
    above = assess(complete_prior_year(
        income_tax="10000", hicbc="0", class_4_nic="0", student_loan_repayment="0",
        tax_deducted_at_source="8000.01",
    ))

    assert below.source_deduction_test.below_threshold is True
    assert below.status is PoAStatus.APPLICABLE
    assert at.source_deduction_test.below_threshold is False
    assert at.status is PoAStatus.NOT_APPLICABLE
    assert above.source_deduction_test.below_threshold is False
    assert above.status is PoAStatus.NOT_APPLICABLE


# ── First versus established Self Assessment year ─────────────────────────────

def test_first_year_produces_no_prior_year_derived_instalments():
    result = assess_payments_on_account(
        preceding_year_status=PrecedingYearStatus.FIRST_YEAR,
    )
    assert result.status is PoAStatus.FIRST_YEAR_NO_PRECEDING_RETURN
    assert result.instalments == ()
    assert result.poa_basis is None
    assert result.relevant_amount is None


def test_established_year_derives_instalments():
    result = assess(complete_prior_year())
    assert result.status is PoAStatus.APPLICABLE
    assert result.poa_basis == Decimal("3000.00")
    assert result.relevant_amount == Decimal("2600.00")
    assert [i.amount for i in result.instalments] == [
        Decimal("1300.00"), Decimal("1300.00"),
    ]


# ── Due dates and schedule ────────────────────────────────────────────────────

def test_first_poa_and_balancing_on_31_january_second_poa_on_31_july():
    result = assess(complete_prior_year(tax_year="2025/26"))
    assert result.poa_tax_year == "2026/27"
    assert result.instalments[0].due_date == date(2027, 1, 31)
    assert result.instalments[1].due_date == date(2027, 7, 31)

    balancing = compose_balancing_position(
        tax_year="2025/26",
        final_liability=item("3000"),
        deductions_credits=item("0"),
        prior_poa=item("0"),
    )
    assert balancing.due_date == date(2027, 1, 31)


# ── Odd-penny allocation preserves the exact total ────────────────────────────

def test_odd_penny_loaded_onto_second_instalment():
    result = assess(complete_prior_year(
        income_tax="1000.01", hicbc="0", class_4_nic="0", student_loan_repayment="0",
        tax_deducted_at_source="0",
    ))
    assert result.status is PoAStatus.APPLICABLE
    assert result.instalments[0].amount == Decimal("500.00")
    assert result.instalments[1].amount == Decimal("500.01")
    total = sum((i.amount for i in result.instalments), Decimal("0"))
    assert total == result.relevant_amount == Decimal("1000.01")


# ── Balancing position is reduced only by credits and payments ────────────────

def test_prior_poa_payments_and_credits_reduce_only_balancing_position():
    balancing = compose_balancing_position(
        tax_year="2025/26",
        final_liability=item("5000"),
        deductions_credits=item("1000"),
        prior_poa=item("2000"),
        payments_made=[
            payment(PaymentKind.OTHER_PAYMENT, "1000"),
        ],
    )
    assert balancing.status is BalanceStatus.REMAINING_BALANCE
    assert balancing.remaining_balance == Decimal("1000.00")
    assert balancing.excess_credit is None


def test_excess_credit_refund_candidate():
    balancing = compose_balancing_position(
        tax_year="2025/26",
        final_liability=item("3000"),
        deductions_credits=item("1000"),
        prior_poa=item("2500"),
    )
    assert balancing.status is BalanceStatus.EXCESS_CREDIT
    assert balancing.excess_credit == Decimal("500.00")
    assert balancing.remaining_balance is None


def test_zero_balance_is_remaining_balance_not_excess_credit():
    balancing = compose_balancing_position(
        tax_year="2025/26",
        final_liability=item("3000"),
        deductions_credits=item("1000"),
        prior_poa=item("2000"),
    )
    assert balancing.status is BalanceStatus.REMAINING_BALANCE
    assert balancing.remaining_balance == Decimal("0.00")


def test_prior_poa_not_double_counted_through_payments_made():
    balancing = compose_balancing_position(
        tax_year="2025/26",
        final_liability=item("5000"),
        deductions_credits=item("0"),
        prior_poa=item("2000"),
        payments_made=[
            payment(PaymentKind.PAYMENT_ON_ACCOUNT, "2000"),
        ],
    )
    assert balancing.status is BalanceStatus.UNRESOLVED
    assert balancing.unresolved_reason == "prior_poa_duplicated_in_payments_made"
    assert balancing.remaining_balance is None
    assert balancing.excess_credit is None


# ── Exclusion / double-count prevention ───────────────────────────────────────

def test_basis_families_and_excluded_families_are_explicit():
    result = assess(complete_prior_year(
        income_tax="2500", hicbc="400", class_4_nic="500",
        student_loan_repayment="300", class_2_nic="150", capital_gains_tax="900",
        tax_deducted_at_source="400",
    ))
    # Income Tax, HICBC and Class 4 enter the basis; Student Loan is excluded.
    assert result.poa_basis == Decimal("3400.00")
    excluded = {e.family: e.amount for e in result.excluded_amounts}
    assert excluded["student_loan_repayment"] == Decimal("300.00")
    assert excluded["class_2_nic"] == Decimal("150.00")
    assert excluded["capital_gains_tax"] == Decimal("900.00")
    assert result.poa_basis == Decimal("2500") + Decimal("400") + Decimal("500")


def test_student_loan_is_excluded_from_poa_basis():
    result = assess(complete_prior_year(
        income_tax="2500", hicbc="0", class_4_nic="500",
        student_loan_repayment="300", tax_deducted_at_source="0",
    ))
    assert result.poa_basis == Decimal("3000.00")
    excluded = {e.family: e.amount for e in result.excluded_amounts}
    assert excluded["student_loan_repayment"] == Decimal("300.00")


def test_hicbc_included_once_when_separately_stated():
    result = assess(complete_prior_year(
        income_tax="2000", hicbc="500", class_4_nic="0",
        student_loan_repayment="0", tax_deducted_at_source="0",
        income_tax_scope=IncomeTaxScope.EXCLUDES_HICBC,
    ))
    assert result.poa_basis == Decimal("2500.00")


def test_hicbc_included_inside_income_tax_when_scope_includes():
    result = assess(complete_prior_year(
        income_tax="2500",  # already includes HICBC
        hicbc="0",
        class_4_nic="0",
        student_loan_repayment="0",
        tax_deducted_at_source="0",
        income_tax_scope=IncomeTaxScope.INCLUDES_HICBC,
    ))
    assert result.poa_basis == Decimal("2500.00")


def test_hicbc_not_double_counted_when_income_tax_includes_hicbc():
    result = assess(complete_prior_year(
        income_tax="2000",  # already includes HICBC
        hicbc="500",        # separately supplied → would double count
        class_4_nic="0",
        student_loan_repayment="0",
        tax_deducted_at_source="0",
        income_tax_scope=IncomeTaxScope.INCLUDES_HICBC,
    ))
    assert result.status is PoAStatus.CONFLICT_REQUIRES_REVIEW
    assert result.poa_basis is None
    assert result.instalments == ()


# ── Mixed PAYE / trade / property expressed through the explicit basis ───────

def test_mixed_paye_trade_property_through_explicit_basis():
    result = assess(complete_prior_year(
        income_tax="4000",  # employment + property income tax
        hicbc="0",
        class_4_nic="500",  # trade Class 4
        student_loan_repayment="300",
        tax_deducted_at_source="1500",  # PAYE collected at source
    ))
    assert result.poa_basis == Decimal("4500.00")
    assert result.relevant_amount == Decimal("3000.00")
    assert result.source_deduction_test.ratio == Decimal("1500") / Decimal("4500")
    assert [i.amount for i in result.instalments] == [
        Decimal("1500.00"), Decimal("1500.00"),
    ]


# ── Fail-closed: missing, stale, conflicting, incomplete ──────────────────────

def test_missing_prior_year_evidence_fails_closed():
    result = assess_payments_on_account(
        preceding_year_status=PrecedingYearStatus.ESTABLISHED,
        prior_year=None,
    )
    assert result.status is PoAStatus.INSUFFICIENT_FACTS
    assert result.poa_basis is None
    assert result.instalments == ()


def test_missing_prior_year_component_fails_closed():
    result = assess(complete_prior_year(income_tax=None))
    assert result.status is PoAStatus.INSUFFICIENT_FACTS
    assert result.poa_basis is None
    assert result.instalments == ()


def test_incomplete_prior_year_evidence_fails_closed():
    result = assess(complete_prior_year(completeness=Completeness.PARTIAL))
    assert result.status is PoAStatus.INSUFFICIENT_FACTS
    assert result.instalments == ()


def test_stale_prior_year_evidence_fails_closed():
    result = assess(complete_prior_year(retrieval_date=TODAY - timedelta(days=60)))
    assert result.status is PoAStatus.STALE_REQUIRES_REVIEW
    assert result.poa_basis is None
    assert result.instalments == ()


def test_conflicting_prior_year_evidence_fails_closed():
    result = assess(complete_prior_year(uncertainty=("conflicting",)))
    assert result.status is PoAStatus.CONFLICT_REQUIRES_REVIEW
    assert result.poa_basis is None
    assert result.instalments == ()


def test_balancing_position_fails_closed_on_missing_evidence():
    balancing = compose_balancing_position(
        tax_year="2025/26",
        final_liability=item(None),
        deductions_credits=item("0"),
        prior_poa=item("0"),
    )
    assert balancing.status is BalanceStatus.UNRESOLVED
    assert balancing.remaining_balance is None
    assert balancing.excess_credit is None


def test_balancing_position_fails_closed_on_conflicting_payment_history():
    balancing = compose_balancing_position(
        tax_year="2025/26",
        final_liability=item("4000"),
        deductions_credits=item("0"),
        prior_poa=item("0"),
        payments_made=[
            payment(PaymentKind.BALANCING_PAYMENT, "1500", reference="bp-1"),
            payment(PaymentKind.BALANCING_PAYMENT, "1700", reference="bp-1"),
        ],
    )
    assert balancing.status is BalanceStatus.UNRESOLVED
    assert balancing.unresolved_reason == "conflicting_payment_history"


# ── Source provenance remains semantically distinct ───────────────────────────

def test_hmrc_issued_and_local_estimate_remain_distinct():
    hmrc = assess(complete_prior_year(source=SourceKind.HMRC_ISSUED))
    local = assess(complete_prior_year(source=SourceKind.LOCAL_ESTIMATE))
    # Numerically identical, but provenance must remain distinguishable.
    assert hmrc.poa_basis == local.poa_basis
    assert hmrc.relevant_amount == local.relevant_amount
    assert hmrc.source is SourceKind.HMRC_ISSUED
    assert local.source is SourceKind.LOCAL_ESTIMATE
    assert any("local_estimate" in lim for lim in local.limitations)


def test_balancing_source_remains_local_estimate_when_numbers_match():
    hmrc = compose_balancing_position(
        tax_year="2025/26",
        final_liability=item("3000", source=SourceKind.HMRC_ISSUED),
        deductions_credits=item("0"),
        prior_poa=item("0"),
    )
    local = compose_balancing_position(
        tax_year="2025/26",
        final_liability=item("3000", source=SourceKind.LOCAL_ESTIMATE),
        deductions_credits=item("0"),
        prior_poa=item("0"),
    )
    assert hmrc.remaining_balance == local.remaining_balance
    assert hmrc.source is SourceKind.HMRC_ISSUED
    assert local.source is SourceKind.LOCAL_ESTIMATE
    assert any("local_estimate" in lim for lim in local.limitations)


# ── Invalid inputs are rejected ───────────────────────────────────────────────

def test_boolean_amount_is_rejected():
    with pytest.raises(ValueError):
        complete_prior_year(income_tax=True)


def test_negative_amount_is_rejected():
    with pytest.raises(ValueError):
        complete_prior_year(class_4_nic="-1")


def test_non_finite_amount_is_rejected():
    with pytest.raises(ValueError):
        complete_prior_year(income_tax=float("nan"))
    with pytest.raises(ValueError):
        complete_prior_year(income_tax=float("inf"))


def test_malformed_tax_year_is_rejected():
    with pytest.raises(ValueError):
        complete_prior_year(tax_year="2026-27")
    with pytest.raises(ValueError):
        complete_prior_year(tax_year="2026/28")


def test_invalid_enum_is_rejected():
    with pytest.raises(ValueError):
        complete_prior_year(source="not_a_source")
    with pytest.raises(ValueError):
        complete_prior_year(completeness="not_a_completeness")
    with pytest.raises(ValueError):
        complete_prior_year(income_tax_scope="not_a_scope")
    with pytest.raises(ValueError):
        assess_payments_on_account(
            preceding_year_status="not_a_status",
        )


def test_invalid_uncertainty_reason_is_rejected():
    with pytest.raises(ValueError):
        complete_prior_year(uncertainty=("invented_reason",))


def test_datetime_is_rejected_where_date_required():
    with pytest.raises(ValueError):
        complete_prior_year(effective_date=datetime(2026, 1, 31))
    with pytest.raises(ValueError):
        complete_prior_year(retrieval_date=datetime(2026, 8, 31))


def test_effective_date_outside_tax_year_is_rejected():
    with pytest.raises(ValueError):
        complete_prior_year(effective_date=date(2026, 5, 1))   # after 2025/26
    with pytest.raises(ValueError):
        complete_prior_year(effective_date=date(2025, 3, 31))  # before 2025/26


def test_future_retrieval_date_is_rejected():
    future = TODAY + timedelta(days=1)
    with pytest.raises(ValueError):
        assess(complete_prior_year(retrieval_date=future))


def test_future_payment_date_is_rejected():
    future = TODAY + timedelta(days=1)
    with pytest.raises(ValueError):
        compose_balancing_position(
            tax_year="2025/26",
            final_liability=item("3000"),
            deductions_credits=item("0"),
            prior_poa=item("0"),
            payments_made=[
                payment(PaymentKind.OTHER_PAYMENT, "1000", paid_on=future),
            ],
            as_of=TODAY,
        )
    with pytest.raises(ValueError):
        compose_balancing_position(
            tax_year="2025/26",
            final_liability=item("3000"),
            deductions_credits=item("0"),
            prior_poa=item("0"),
            payments_made=[
                payment(PaymentKind.OTHER_PAYMENT, "1000", retrieval_date=future),
            ],
            as_of=TODAY,
        )


def test_contract_version_is_exposed():
    assert CONTRACT_VERSION == "reserved-payments-on-account/1.0"
