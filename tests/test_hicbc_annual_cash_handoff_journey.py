"""Synthetic HICBC-bearing annual-to-cash journey, not activation evidence.

All account observations are invented manual fixtures with literal amounts.
No expected amount is calculated by a tax/cash producer or taken from its output.
The journey ends at the owner-unbound handoff; no route or owner is fabricated.
"""
from dataclasses import asdict, replace
from datetime import date, timedelta
from decimal import Decimal
import json
import re

import pytest

from reserved.engines import cash_funding_position as funding
from reserved.engines import payments_on_account as poa
from reserved.engines import sa_account_reconciliation as account
from reserved.engines.annual_to_cash_integration import (
    AnnualToCashStatus,
    annual_to_cash_position_provenance,
    balance_item_identity,
    cash_ready_annual_position_identity,
    compose_annual_to_cash_position,
    payment_made_identity,
    prior_year_evidence_identity,
)
from reserved.engines.cash_ready_annual_position import (
    NoStudentLoanEvidence,
    annual_position_identity,
    compose_cash_ready_annual_position,
    student_loan_position_identity,
)
from reserved.engines.integrated_annual_position import calculate_annual_position
from reserved.services.w2_customer_language import (
    EvidenceClassification, FundingClassification, ObligationKind,
    present_w2_customer_language,
)
from reserved.services.w8_annual_cash_customer_handoff import (
    annual_to_cash_source_identity,
    compose_w8_annual_cash_customer_handoff,
    project_w8_annual_cash_presentation,
)


AS_OF = date(2027, 4, 5)
JANUARY = date(2028, 1, 31)
JULY = date(2028, 7, 31)
# £70,000 earnings: £37,700 at 20% + £19,730 at 40% = £15,432.
# Settled RW3-HICBC-001: £1,406.60 benefit at £70,000 ANI -> £703 charge.
# Deduct £10,000 at source, £1,000 prior PoA and £100 already paid once each.
# Independent preceding-return evidence: £1,200 basis -> £600 + £600 PoA.
# £500 explicitly allocated savings is separate from all those deductions.
CASES = (
    ("50000", "703.00", "16135.00", "5035.00", "6235.00", "5735.00"),
    ("75000", "0.00", "15432.00", "4332.00", "5532.00", "5032.00"),
)


def assert_no_private_details(presented, language, partner):
    """Check exact fixture values without normalising or rewriting output.

    Numeric boundaries prevent matching £150,000 or £50,000.01 as £50,000.
    Currency prefixes need no special treatment: the exact numeric token is
    detected with or without £/GBP, whitespace, commas or zero decimal places.
    This is bounded fixture assurance, not a general-purpose privacy scanner.
    """
    output = json.dumps(
        [asdict(presented), asdict(language)], default=str, ensure_ascii=False,
    ).lower()
    for forbidden in ("partner", "household", "liable_person", "adjusted_net_income"):
        assert forbidden not in output, f"private field/name disclosed: {forbidden}"
    values = (partner, "1054") if partner == "75000" else (partner,)
    for value in values:
        alternatives = "|".join(re.escape(token) for token in (value, f"{int(value):,}"))
        pattern = rf"(?<![\d.,])(?:{alternatives})(?:\.0{{1,2}})?(?![\d.,])"
        assert re.search(pattern, output) is None, f"private numeric value disclosed: {value}"


def annual_chain(*, partner="50000", nation="England", overrides=None):
    facts = {
        "employment_income": "70000", "person_adjusted_net_income": "70000",
        "country": nation,
        "blind_persons_allowance_entitled": False,
        "blind_persons_allowance_transferred_in": "0",
        "blind_persons_allowance_transferred_out": "0",
        "annual_child_benefit": "1406.60",
        "payments_received_for_full_charge_period": True,
        "has_relevant_partner": True,
        "partner_adjusted_net_income": partner,
        "child_benefit_claimant": "person",
    }
    facts.update(overrides or {})
    tax = calculate_annual_position(facts)
    no_loans = NoStudentLoanEvidence(
        "synthetic-no-loan", "2026/27", "uk-2026-27-v4", AS_OF,
        "synthetic-person", "synthetic", "synthetic:no-loan-source", True,
    )
    annual = compose_cash_ready_annual_position(
        tax, no_loans, annual_tax_reference=annual_position_identity(tax),
        student_loan_reference=student_loan_position_identity(no_loans), as_of=AS_OF,
    )
    return tax, annual


def cash_chain(annual, *, balance="5035.00", prior_income="1200.00",
               instalment="600.00"):
    """Use independent literal manual account evidence, never producer outputs."""
    prior = poa.PriorYearEvidence(
        tax_year="2026/27", source=poa.SourceKind.LOCAL_ESTIMATE,
        effective_date=AS_OF, retrieval_date=AS_OF,
        completeness=poa.Completeness.COMPLETE_FOR_PURPOSE,
        income_tax=Decimal(prior_income), hicbc=Decimal("0.00"),
        class_4_nic=Decimal("0.00"), tax_deducted_at_source=Decimal("0.00"),
    )
    deductions = poa.BalanceItem(Decimal("10000.00"), poa.SourceKind.LOCAL_ESTIMATE,
                               poa.Completeness.COMPLETE_FOR_PURPOSE, AS_OF)
    previous_poa = poa.BalanceItem(Decimal("1000.00"), poa.SourceKind.LOCAL_ESTIMATE,
                                 poa.Completeness.COMPLETE_FOR_PURPOSE, AS_OF)
    paid = poa.PaymentMade(
        poa.PaymentKind.BALANCING_PAYMENT, Decimal("100.00"),
        poa.SourceKind.LOCAL_ESTIMATE, AS_OF, AS_OF, reference="synthetic:paid",
    )
    charges = tuple(account.AccountCharge(
        f"synthetic-charge-{name}", kind, year, Decimal(amount), due,
        AS_OF, AS_OF, account.EvidenceSource.MANUAL,
        account.Completeness.COMPLETE_FOR_PURPOSE, f"synthetic:account-{name}",
    ) for name, kind, year, amount, due in (
        ("balance", account.ChargeKind.BALANCING_PAYMENT, "2026/27", balance, JANUARY),
        ("first", account.ChargeKind.PAYMENT_ON_ACCOUNT_1, "2027/28", instalment, JANUARY),
        ("second", account.ChargeKind.PAYMENT_ON_ACCOUNT_2, "2027/28", instalment, JULY),
    ))
    observed = account.reconcile_sa_account(
        charges, (), (), as_of=AS_OF, coverage=account.Completeness.COMPLETE_FOR_PURPOSE,
    )
    savings = funding.SetAsideEvidence(
        "synthetic-savings", Decimal("500.00"), AS_OF, AS_OF,
        funding.SetAsideSource.CUSTOMER_RECORDED,
        funding.EvidenceCompleteness.COMPLETE_FOR_PURPOSE, "synthetic:savings-source",
        (funding.SetAsideAllocation(
            "synthetic-allocation", "balance:2026/27:balancing_payment", Decimal("500.00"),
        ),),
    )
    source = compose_annual_to_cash_position(
        annual_position=annual,
        annual_position_reference=cash_ready_annual_position_identity(annual),
        preceding_year_status=poa.PrecedingYearStatus.ESTABLISHED,
        prior_year_evidence=prior, prior_year_reference=prior_year_evidence_identity(prior),
        deductions_credits=deductions,
        deductions_credits_reference=balance_item_identity(
            deductions, channel="deductions-credits", evidence_ids=("synthetic:deducted",),
        ),
        deductions_credits_evidence_ids=("synthetic:deducted",),
        prior_poa=previous_poa,
        prior_poa_reference=balance_item_identity(
            previous_poa, channel="prior-poa", evidence_ids=("synthetic:prior-paid",),
        ),
        prior_poa_evidence_ids=("synthetic:prior-paid",),
        payments_made=(paid,), payment_content_references=(payment_made_identity(paid),),
        account_reconciliation=observed, set_aside_evidence=savings, as_of=AS_OF,
    )
    refs = annual.evidence_ids + tuple(
        ref for charge in charges for ref in (charge.charge_id, charge.source_reference)
    ) + (savings.evidence_id, savings.source_reference, "synthetic-allocation")
    return source, refs, prior


@pytest.mark.parametrize("nation", ["England", "Wales", "Northern Ireland"])
@pytest.mark.parametrize("partner,charge,total,balance,required,gap", CASES)
def test_authentic_hicbc_reaches_cash_and_unbound_presentation_once(
    nation, partner, charge, total, balance, required, gap,
):
    tax, annual = annual_chain(partner=partner, nation=nation)
    source, refs, prior = cash_chain(annual, balance=balance)
    assert tax.income_tax_before_limitations == Decimal("15432.00")
    assert tax.hicbc == Decimal(charge)
    assert tax.total_liability == annual.final_self_assessment_liability == Decimal(total)
    assert "hicbc" in annual.annual_tax_families
    assert source.status is AnnualToCashStatus.QUALIFIED_LOCAL_RESULT
    assert source.balancing_position.remaining_balance == Decimal(balance)
    assert source.funding_position.total_required == Decimal(required)
    assert source.funding_position.total_set_aside == Decimal("500.00")
    assert source.funding_position.funding_gap == Decimal(gap)
    assert source.poa_assessment.relevant_amount == Decimal("1200.00")
    assert tuple(i.amount for i in source.poa_assessment.instalments) == (
        Decimal("600.00"), Decimal("600.00"),
    )
    assert source.poa_assessment.poa_tax_year == "2027/28"
    assert prior.income_tax == Decimal("1200.00") and prior.hicbc == Decimal("0.00")
    provenance = annual_to_cash_position_provenance(source)
    assert provenance.prior_year_reference == prior_year_evidence_identity(prior)
    assert provenance.annual_position_reference == cash_ready_annual_position_identity(annual)

    handoff = compose_w8_annual_cash_customer_handoff(source, evidence_references=refs)
    assert handoff is not None
    presented = project_w8_annual_cash_presentation(
        handoff, source_position=source, evidence_references=refs, expected_as_of=AS_OF,
    )
    assert presented is handoff.presentation_input
    assert handoff.evidence_references == refs
    assert handoff.source_position_identity == annual_to_cash_source_identity(
        source, evidence_references=refs,
    )
    assert handoff.nation == source.nation == annual.nation == nation
    assert handoff.tax_year == source.tax_year == annual.tax_year == "2026/27"
    assert handoff.as_of == AS_OF
    assert handoff.ruleset_version == annual.ruleset_version == "uk-2026-27-v4"
    assert presented.annual_liability == Decimal(total)
    assert presented.evidence is EvidenceClassification.QUALIFIED_LOCAL_ESTIMATE
    assert presented.funding is FundingClassification.GAP
    assert presented.funding_amount == Decimal(gap)
    assert {(o.kind, o.amount, o.due_date) for o in presented.obligations} == {
        (ObligationKind.BALANCING_PAYMENT, Decimal(balance), JANUARY),
        (ObligationKind.FIRST_PAYMENT_ON_ACCOUNT, Decimal("600.00"), JANUARY),
        (ObligationKind.SECOND_PAYMENT_ON_ACCOUNT, Decimal("600.00"), JULY),
    }
    # Inspect fixed wording locally; this is not permitted customer rendering.
    language = present_w2_customer_language(presented)
    assert language.evidence_label == "Local estimate — not confirmed by HMRC"
    assert language.no_payment_authority == "This view does not authorise a payment or transfer."
    assert handoff.owner_authoritative is False
    assert "persistence_or_customer_rendering" in handoff.prohibited_uses
    assert "payment_or_transfer_action" in handoff.prohibited_uses
    assert "recommend_or_initiate_payment_or_transfer" in source.prohibited_uses
    assert "payment" in annual.prohibited_uses
    # Internal household details are deliberately real in this fixture, but absent
    # from both projected facts and fixed customer language (including field names).
    assert_no_private_details(presented, language, partner)
    if partner == "75000":
        assert tax.hicbc_household_charge == Decimal("1054.00")
        assert tax.hicbc_liable_person == "partner"


@pytest.mark.parametrize("partner,balance", [("50000", "5035.00"), ("75000", "4332.00")])
@pytest.mark.parametrize("format_spec,prefix", [
    (".0f", ""), (".1f", ""), (".2f", ""),
    (",.0f", ""), (",.1f", ""), (",.2f", ""),
    (".0f", "£"), (".2f", "£"), (",.0f", "£"),
    (",.2f", "£"), (",.2f", "£ "), (",.2f", "GBP "),
])
@pytest.mark.parametrize("surface", ["projected_facts", "fixed_language"])
def test_privacy_assertion_detects_formatted_ani_mutation(partner, balance, format_spec, prefix, surface):
    _, annual = annual_chain(partner=partner)
    source, refs, _ = cash_chain(annual, balance=balance)
    handoff = compose_w8_annual_cash_customer_handoff(source, evidence_references=refs)
    presented = project_w8_annual_cash_presentation(
        handoff, source_position=source, evidence_references=refs, expected_as_of=AS_OF,
    )
    language = present_w2_customer_language(presented)
    assert_no_private_details(presented, language, partner)
    leaked = prefix + format(Decimal(partner), format_spec)
    # Deliberately corrupt local copies only to challenge the same assertion
    # used by the authentic journey. Never submit these copies to a producer.
    if surface == "projected_facts":
        presented = replace(presented, annual_liability=leaked)
    else:
        language = replace(language, status_message=leaked)
    with pytest.raises(AssertionError, match="private numeric value disclosed"):
        assert_no_private_details(presented, language, partner)


@pytest.mark.parametrize("unrelated", ["£150,000.00", "£50,000.01", "£500,000.00", "£175,000.00", "£75,000.01"])
def test_privacy_numeric_check_does_not_match_other_amounts(unrelated):
    _, annual = annual_chain()
    source, refs, _ = cash_chain(annual)
    handoff = compose_w8_annual_cash_customer_handoff(source, evidence_references=refs)
    presented = project_w8_annual_cash_presentation(
        handoff, source_position=source, evidence_references=refs, expected_as_of=AS_OF,
    )
    language = replace(present_w2_customer_language(presented), status_message=unrelated)
    for partner in ("50000", "75000"):
        assert_no_private_details(presented, language, partner)


def test_changing_separate_prior_return_changes_only_future_instalments():
    _, annual = annual_chain()
    source, refs, _ = cash_chain(annual, prior_income="2000.00", instalment="1000.00")
    handoff = compose_w8_annual_cash_customer_handoff(source, evidence_references=refs)
    assert handoff is not None
    facts = project_w8_annual_cash_presentation(
        handoff, source_position=source, evidence_references=refs, expected_as_of=AS_OF,
    )
    assert facts.annual_liability == Decimal("16135.00")
    assert source.balancing_position.remaining_balance == Decimal("5035.00")
    assert source.poa_assessment.relevant_amount == Decimal("2000.00")
    assert tuple(i.amount for i in source.poa_assessment.instalments) == (
        Decimal("1000.00"), Decimal("1000.00"),
    )
    assert source.funding_position.total_required == Decimal("7035.00")
    assert facts.funding_amount == Decimal("6535.00")


@pytest.mark.parametrize("overrides,reason", [
    ({"payments_received_for_full_charge_period": None}, "hicbc_facts_incomplete"),
    ({"partner_adjusted_net_income": None}, "hicbc_responsibility_facts_ambiguous"),
    ({"partner_adjusted_net_income": "75000", "taxpayer_is_higher_ani_partner": True},
     "hicbc_responsibility_facts_ambiguous"),
    ({"partner_adjusted_net_income": "70000", "child_benefit_claimant": None},
     "hicbc_responsibility_facts_ambiguous"),
])
def test_authentic_inadequate_hicbc_source_cannot_reach_cash_or_presentation(overrides, reason):
    tax, annual = annual_chain(overrides=overrides)
    assert reason in tax.limitations
    assert tax.hicbc is None and tax.total_liability is None
    assert annual.calculation_status == "unresolved"
    assert annual.final_self_assessment_liability is None
    # Otherwise complete manual cash evidence must not rescue missing annual facts.
    source, refs, _ = cash_chain(annual)
    assert source.status is AnnualToCashStatus.UNRESOLVED
    assert "annual_position_not_ready_for_w2_s6" in source.limitations
    assert source.final_self_assessment_liability is None
    assert source.balancing_position is None and source.funding_position is None
    assert compose_w8_annual_cash_customer_handoff(source, evidence_references=refs) is None


def test_hicbc_handoff_rejects_other_authentic_source_and_stale_context():
    _, annual = annual_chain()
    source, refs, _ = cash_chain(annual)
    handoff = compose_w8_annual_cash_customer_handoff(source, evidence_references=refs)
    _, other_annual = annual_chain(partner="75000")
    other, other_refs, _ = cash_chain(other_annual, balance="4332.00")
    assert handoff is not None
    for selected, selected_refs, expected_date in (
        (other, other_refs, AS_OF),
        (source, refs, AS_OF - timedelta(days=1)),
        (source, refs + ("synthetic:substituted",), AS_OF),
    ):
        with pytest.raises(ValueError):
            project_w8_annual_cash_presentation(
                handoff, source_position=selected, evidence_references=selected_refs,
                expected_as_of=expected_date,
            )
