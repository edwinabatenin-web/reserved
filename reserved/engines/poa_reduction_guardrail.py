"""Fail-closed guardrails for a customer-initiated PoA reduction claim.

This module does not recommend a reduction or amount. It does not calculate
tax or interest, call HMRC, submit a claim, alter an account, move money,
persist data, render a UI, or define the final annual-to-cash contract. It only
checks whether amounts explicitly proposed by a customer are lower than the
existing PoA instalments and are bound to complete purpose-specific evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from enum import Enum
import re

from . import payments_on_account as poa


CONTRACT_VERSION = "reserved-poa-reduction-guardrail/1.0"
PENNY = Decimal("0.01")
ZERO = Decimal("0.00")
_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_TAX_YEAR = re.compile(r"^(\d{4})/(\d{2})$")
_UNCERTAINTY = frozenset({"missing", "stale", "conflicting", "incomplete"})


class ReductionEvidenceSource(str, Enum):
    HMRC_ISSUED = "hmrc_issued"
    LOCAL_ESTIMATE = "local_estimate"
    CUSTOMER_MANUAL = "customer_manual"


class PoAReductionStatus(str, Enum):
    POA_NOT_APPLICABLE = "poa_not_applicable"
    INSUFFICIENT_FACTS = "insufficient_facts"
    STALE_REQUIRES_REVIEW = "stale_requires_review"
    CONFLICT_REQUIRES_REVIEW = "conflict_requires_review"
    NO_REDUCTION = "no_reduction"
    CUSTOMER_CONFIRMATION_REQUIRED = "customer_confirmation_required"
    REVIEW_READY_FOR_CUSTOMER_HMRC_ACTION = "review_ready_for_customer_hmrc_action"


def _money(value, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be monetary, not boolean")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{name} must be numeric") from None
    if not amount.is_finite() or amount < ZERO:
        raise ValueError(f"{name} must be finite and non-negative")
    try:
        pennies = amount.quantize(PENNY)
    except InvalidOperation:
        raise ValueError(f"{name} cannot be represented safely as pennies") from None
    if pennies != amount:
        raise ValueError(f"{name} must be expressed in whole pennies")
    return pennies


def _date(value, name: str) -> date:
    if isinstance(value, datetime) or not isinstance(value, date):
        raise ValueError(f"{name} must be a date, not a datetime")
    return value


def _reference(value, name: str) -> str:
    if not isinstance(value, str) or not _REFERENCE.fullmatch(value):
        raise ValueError(f"{name} must be a stable non-empty reference")
    return value


def _tax_year(value, name: str) -> tuple[str, int]:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a tax-year string")
    match = _TAX_YEAR.fullmatch(value)
    if not match or int(match.group(2)) != (int(match.group(1)) + 1) % 100:
        raise ValueError(f"{name} must use consecutive YYYY/YY form")
    return value, int(match.group(1))


def _source(value) -> ReductionEvidenceSource:
    if isinstance(value, ReductionEvidenceSource):
        return value
    if isinstance(value, poa.SourceKind):
        return ReductionEvidenceSource(value.value)
    if isinstance(value, str):
        try:
            return ReductionEvidenceSource(value)
        except ValueError:
            pass
    raise ValueError("source must be a valid ReductionEvidenceSource")


@dataclass(frozen=True)
class CurrentYearReductionEvidence:
    evidence_id: str
    tax_year: str
    source: ReductionEvidenceSource
    effective_date: date
    retrieval_date: date
    completeness: poa.Completeness
    evidenced_first_instalment: Decimal
    evidenced_second_instalment: Decimal
    source_reference: str
    uncertainty: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "evidence_id", _reference(self.evidence_id, "evidence_id"))
        tax_year, _ = _tax_year(self.tax_year, "tax_year")
        object.__setattr__(self, "tax_year", tax_year)
        object.__setattr__(self, "source", _source(self.source))
        object.__setattr__(self, "effective_date", _date(self.effective_date, "effective_date"))
        object.__setattr__(self, "retrieval_date", _date(self.retrieval_date, "retrieval_date"))
        if self.retrieval_date < self.effective_date:
            raise ValueError("retrieval_date cannot be before effective_date")
        if not isinstance(self.completeness, poa.Completeness):
            raise ValueError("completeness must be a Payments on Account Completeness")
        object.__setattr__(
            self,
            "evidenced_first_instalment",
            _money(self.evidenced_first_instalment, "evidenced_first_instalment"),
        )
        object.__setattr__(
            self,
            "evidenced_second_instalment",
            _money(self.evidenced_second_instalment, "evidenced_second_instalment"),
        )
        object.__setattr__(
            self, "source_reference", _reference(self.source_reference, "source_reference")
        )
        if not isinstance(self.uncertainty, tuple):
            raise ValueError("uncertainty must be an immutable tuple")
        if any(reason not in _UNCERTAINTY for reason in self.uncertainty):
            raise ValueError("uncertainty contains an unsupported reason")


@dataclass(frozen=True)
class CustomerReductionProposal:
    proposal_id: str
    first_instalment: Decimal
    second_instalment: Decimal
    customer_intends_to_claim: bool
    customer_confirmed_proposed_amounts: bool
    under_reduction_interest_warning_acknowledged: bool

    def __post_init__(self):
        object.__setattr__(self, "proposal_id", _reference(self.proposal_id, "proposal_id"))
        object.__setattr__(
            self, "first_instalment", _money(self.first_instalment, "first_instalment")
        )
        object.__setattr__(
            self, "second_instalment", _money(self.second_instalment, "second_instalment")
        )
        for name in (
            "customer_intends_to_claim",
            "customer_confirmed_proposed_amounts",
            "under_reduction_interest_warning_acknowledged",
        ):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be boolean")


@dataclass(frozen=True)
class PoAReductionGuardrailResult:
    contract_version: str
    status: PoAReductionStatus
    ready_for_customer_hmrc_action: bool
    is_hmrc_decision: bool
    recommended_amount: None
    auto_submission_performed: bool
    current_instalments: tuple[poa.Instalment, ...]
    proposed_instalments: tuple[Decimal, Decimal] | tuple[()]
    considered_assessment: poa.PoAAssessment
    considered_proposal: CustomerReductionProposal | None
    considered_evidence: CurrentYearReductionEvidence | None
    evidence_source: ReductionEvidenceSource | None
    evidence_source_reference: str | None
    evidence_effective_date: date | None
    evidence_retrieval_date: date | None
    evidence_uncertainty: tuple[str, ...]
    limitations: tuple[str, ...]
    warnings: tuple[str, ...]
    prohibited_uses: tuple[str, ...]


_WARNING = "under_reduction_may_lead_to_interest"
_PROHIBITED_USES = (
    "recommend_reduction_or_amount",
    "present_as_hmrc_decision",
    "auto_submit_reduction_claim",
    "hmrc_api_or_account_alteration",
    "payment_or_allocation",
    "tax_or_interest_calculation",
    "regulated_or_personal_tax_advice",
    "self_assessment_filing",
    "persistence_or_production_access",
)


def _result(
    *,
    status,
    assessment,
    proposal,
    evidence,
    current=(),
    limitations=(),
):
    proposed = () if proposal is None else (
        proposal.first_instalment,
        proposal.second_instalment,
    )
    return PoAReductionGuardrailResult(
        contract_version=CONTRACT_VERSION,
        status=status,
        ready_for_customer_hmrc_action=(
            status is PoAReductionStatus.REVIEW_READY_FOR_CUSTOMER_HMRC_ACTION
        ),
        is_hmrc_decision=False,
        recommended_amount=None,
        auto_submission_performed=False,
        current_instalments=tuple(current),
        proposed_instalments=proposed,
        considered_assessment=assessment,
        considered_proposal=proposal,
        considered_evidence=evidence,
        evidence_source=None if evidence is None else evidence.source,
        evidence_source_reference=None if evidence is None else evidence.source_reference,
        evidence_effective_date=None if evidence is None else evidence.effective_date,
        evidence_retrieval_date=None if evidence is None else evidence.retrieval_date,
        evidence_uncertainty=() if evidence is None else evidence.uncertainty,
        limitations=tuple(dict.fromkeys(limitations)),
        warnings=(_WARNING,),
        prohibited_uses=_PROHIBITED_USES,
    )


def _assessment_state(
    assessment: poa.PoAAssessment, as_of: date, stale_after_days: int,
):
    if not isinstance(assessment, poa.PoAAssessment):
        raise ValueError("assessment must be a PoAAssessment")
    if assessment.contract_version != poa.CONTRACT_VERSION:
        raise ValueError("assessment contract_version is unsupported")
    if not isinstance(assessment.status, poa.PoAStatus):
        return "inconsistent", ()
    if assessment.status is poa.PoAStatus.FIRST_YEAR_NO_PRECEDING_RETURN:
        if (
            assessment.prior_tax_year is not None
            or assessment.poa_tax_year is not None
            or assessment.source is not None
            or assessment.effective_date is not None
            or assessment.retrieval_date is not None
            or assessment.completeness is not None
            or assessment.poa_basis is not None
            or assessment.relevant_amount is not None
            or assessment.fixed_amount_test is not None
            or assessment.source_deduction_test is not None
            or assessment.instalments
            or assessment.excluded_amounts
            or assessment.limitations != (
                "no_preceding_return_no_prior_year_derived_instalments",
            )
        ):
            return "inconsistent", ()
        return "not_applicable", ()
    if assessment.status is poa.PoAStatus.STALE_REQUIRES_REVIEW:
        return "stale", ()
    if assessment.status is poa.PoAStatus.CONFLICT_REQUIRES_REVIEW:
        return "conflicting", ()
    if assessment.status is poa.PoAStatus.INSUFFICIENT_FACTS:
        return "insufficient", ()
    if assessment.status not in {
        poa.PoAStatus.APPLICABLE,
        poa.PoAStatus.NOT_APPLICABLE,
    }:
        return "inconsistent", ()

    try:
        prior_year, prior_start = _tax_year(assessment.prior_tax_year, "prior_tax_year")
        current_year, current_start = _tax_year(assessment.poa_tax_year, "poa_tax_year")
        effective = _date(assessment.effective_date, "assessment effective_date")
        retrieval = _date(assessment.retrieval_date, "assessment retrieval_date")
        basis = _money(assessment.poa_basis, "poa_basis")
        relevant = _money(assessment.relevant_amount, "relevant_amount")
    except ValueError:
        return "inconsistent", ()
    if current_start != prior_start + 1 or retrieval < effective or retrieval > as_of:
        return "inconsistent", ()
    if not date(prior_start, 4, 6) <= effective <= date(prior_start + 1, 4, 5):
        return "inconsistent", ()
    if not isinstance(assessment.source, poa.SourceKind):
        return "inconsistent", ()
    if assessment.completeness is not poa.Completeness.COMPLETE_FOR_PURPOSE:
        return "inconsistent", ()
    if (as_of - retrieval).days > stale_after_days:
        return "stale", ()
    if not isinstance(assessment.fixed_amount_test, poa.FixedAmountTest):
        return "inconsistent", ()
    if not isinstance(assessment.source_deduction_test, poa.SourceDeductionTest):
        return "inconsistent", ()

    fixed = assessment.fixed_amount_test
    deducted_test = assessment.source_deduction_test
    try:
        fixed_relevant = _money(fixed.relevant_amount, "fixed relevant_amount")
        fixed_threshold = _money(fixed.threshold, "fixed threshold")
        test_basis = _money(deducted_test.basis, "source test basis")
        deducted = _money(deducted_test.deducted_at_source, "deducted_at_source")
    except ValueError:
        return "inconsistent", ()
    if not isinstance(fixed.meets_threshold, bool) or not isinstance(
        deducted_test.below_threshold, bool
    ):
        return "inconsistent", ()
    expected_relevant = basis - deducted
    if expected_relevant < ZERO:
        expected_relevant = ZERO
    expected_ratio = deducted / basis if basis > ZERO else ZERO
    expected_meets = relevant >= poa.FIXED_AMOUNT_THRESHOLD
    expected_below = expected_ratio < poa.SOURCE_DEDUCTION_THRESHOLD
    applies = expected_meets and expected_below
    if (
        fixed_relevant != relevant
        or fixed_threshold != poa.FIXED_AMOUNT_THRESHOLD
        or fixed.meets_threshold is not expected_meets
        or test_basis != basis
        or deducted_test.ratio != expected_ratio
        or deducted_test.threshold != poa.SOURCE_DEDUCTION_THRESHOLD
        or deducted_test.below_threshold is not expected_below
        or relevant != expected_relevant
    ):
        return "inconsistent", ()

    if assessment.status is poa.PoAStatus.NOT_APPLICABLE:
        if applies or assessment.instalments:
            return "inconsistent", ()
        return "not_applicable", ()
    if not applies:
        return "inconsistent", ()

    if not isinstance(assessment.instalments, tuple) or len(assessment.instalments) != 2:
        return "inconsistent", ()
    by_label = {item.label: item for item in assessment.instalments if isinstance(item, poa.Instalment)}
    if set(by_label) != {"payment_on_account_1", "payment_on_account_2"}:
        return "inconsistent", ()
    first = by_label["payment_on_account_1"]
    second = by_label["payment_on_account_2"]
    try:
        first_amount = _money(first.amount, "first current instalment")
        second_amount = _money(second.amount, "second current instalment")
        first_due = _date(first.due_date, "first current due_date")
        second_due = _date(second.due_date, "second current due_date")
    except ValueError:
        return "inconsistent", ()
    expected_first = (relevant / Decimal("2")).quantize(PENNY, rounding=ROUND_DOWN)
    if (
        first_due != date(current_start + 1, 1, 31)
        or second_due != date(current_start + 1, 7, 31)
        or first_amount != expected_first
        or second_amount != relevant - expected_first
    ):
        return "inconsistent", ()
    return "applicable", (first, second)


def evaluate_poa_reduction_guardrail(
    *,
    assessment: poa.PoAAssessment,
    proposal: CustomerReductionProposal | None,
    evidence: CurrentYearReductionEvidence | None,
    as_of: date,
    stale_after_days: int = 45,
) -> PoAReductionGuardrailResult:
    """Evaluate readiness without recommending or submitting a reduction."""
    as_of = _date(as_of, "as_of")
    if isinstance(stale_after_days, bool) or not isinstance(stale_after_days, int):
        raise ValueError("stale_after_days must be an integer")
    if stale_after_days < 0:
        raise ValueError("stale_after_days must be non-negative")
    if proposal is not None and not isinstance(proposal, CustomerReductionProposal):
        raise ValueError("proposal must be a CustomerReductionProposal or None")
    if evidence is not None and not isinstance(evidence, CurrentYearReductionEvidence):
        raise ValueError("evidence must be CurrentYearReductionEvidence or None")

    state, current = _assessment_state(assessment, as_of, stale_after_days)
    if state == "not_applicable":
        return _result(
            status=PoAReductionStatus.POA_NOT_APPLICABLE,
            assessment=assessment, proposal=proposal, evidence=evidence,
            limitations=("payments_on_account_not_applicable",),
        )
    if state == "stale":
        return _result(
            status=PoAReductionStatus.STALE_REQUIRES_REVIEW,
            assessment=assessment, proposal=proposal, evidence=evidence,
            limitations=("payments_on_account_assessment_stale",),
        )
    if state == "conflicting":
        return _result(
            status=PoAReductionStatus.CONFLICT_REQUIRES_REVIEW,
            assessment=assessment, proposal=proposal, evidence=evidence,
            limitations=("payments_on_account_assessment_conflicting",),
        )
    if state != "applicable":
        return _result(
            status=PoAReductionStatus.INSUFFICIENT_FACTS,
            assessment=assessment, proposal=proposal, evidence=evidence,
            limitations=("payments_on_account_assessment_unresolved_or_inconsistent",),
        )
    if proposal is None or evidence is None:
        return _result(
            status=PoAReductionStatus.INSUFFICIENT_FACTS,
            assessment=assessment, proposal=proposal, evidence=evidence,
            current=current,
            limitations=("proposal_and_current_year_evidence_required",),
        )

    _, current_start = _tax_year(assessment.poa_tax_year, "poa_tax_year")
    _, evidence_start = _tax_year(evidence.tax_year, "evidence tax_year")
    if evidence_start != current_start:
        return _result(
            status=PoAReductionStatus.CONFLICT_REQUIRES_REVIEW,
            assessment=assessment, proposal=proposal, evidence=evidence, current=current,
            limitations=("evidence_tax_year_does_not_match_poa_tax_year",),
        )
    if not date(current_start, 4, 6) <= evidence.effective_date <= date(
        current_start + 1, 4, 5
    ):
        return _result(
            status=PoAReductionStatus.CONFLICT_REQUIRES_REVIEW,
            assessment=assessment, proposal=proposal, evidence=evidence, current=current,
            limitations=("evidence_effective_date_outside_poa_tax_year",),
        )
    if evidence.retrieval_date > as_of:
        return _result(
            status=PoAReductionStatus.CONFLICT_REQUIRES_REVIEW,
            assessment=assessment, proposal=proposal, evidence=evidence, current=current,
            limitations=("evidence_retrieval_date_in_future",),
        )
    if "conflicting" in evidence.uncertainty:
        return _result(
            status=PoAReductionStatus.CONFLICT_REQUIRES_REVIEW,
            assessment=assessment, proposal=proposal, evidence=evidence, current=current,
            limitations=("current_year_evidence_conflicting",),
        )
    if evidence.completeness is not poa.Completeness.COMPLETE_FOR_PURPOSE or any(
        reason in evidence.uncertainty for reason in ("missing", "incomplete")
    ):
        return _result(
            status=PoAReductionStatus.INSUFFICIENT_FACTS,
            assessment=assessment, proposal=proposal, evidence=evidence, current=current,
            limitations=("current_year_evidence_incomplete",),
        )
    if "stale" in evidence.uncertainty or (
        as_of - evidence.retrieval_date
    ).days > stale_after_days:
        return _result(
            status=PoAReductionStatus.STALE_REQUIRES_REVIEW,
            assessment=assessment, proposal=proposal, evidence=evidence, current=current,
            limitations=("current_year_evidence_stale",),
        )

    proposed = (proposal.first_instalment, proposal.second_instalment)
    evidenced = (
        evidence.evidenced_first_instalment,
        evidence.evidenced_second_instalment,
    )
    if proposed != evidenced:
        return _result(
            status=PoAReductionStatus.CONFLICT_REQUIRES_REVIEW,
            assessment=assessment, proposal=proposal, evidence=evidence, current=current,
            limitations=("proposal_not_bound_to_evidence_amounts",),
        )
    current_amounts = tuple(_money(item.amount, "current instalment") for item in current)
    if proposed == current_amounts:
        return _result(
            status=PoAReductionStatus.NO_REDUCTION,
            assessment=assessment, proposal=proposal, evidence=evidence, current=current,
            limitations=("proposed_amounts_equal_current_instalments",),
        )
    if sum(proposed, ZERO) >= sum(current_amounts, ZERO):
        return _result(
            status=PoAReductionStatus.NO_REDUCTION,
            assessment=assessment, proposal=proposal, evidence=evidence, current=current,
            limitations=("proposed_total_not_lower_than_current_total",),
        )
    if any(proposed_amount > current_amount for proposed_amount, current_amount in zip(
        proposed, current_amounts
    )):
        return _result(
            status=PoAReductionStatus.CONFLICT_REQUIRES_REVIEW,
            assessment=assessment, proposal=proposal, evidence=evidence, current=current,
            limitations=("proposal_increases_an_instalment",),
        )
    if not (
        proposal.customer_intends_to_claim
        and proposal.customer_confirmed_proposed_amounts
        and proposal.under_reduction_interest_warning_acknowledged
    ):
        return _result(
            status=PoAReductionStatus.CUSTOMER_CONFIRMATION_REQUIRED,
            assessment=assessment, proposal=proposal, evidence=evidence, current=current,
            limitations=("explicit_customer_intent_confirmation_and_warning_acknowledgement_required",),
        )

    limitations = ["customer_proposed_amounts_not_a_recommendation"]
    if evidence.source is ReductionEvidenceSource.LOCAL_ESTIMATE:
        limitations.append("local_estimate_not_hmrc_confirmed")
    elif evidence.source is ReductionEvidenceSource.CUSTOMER_MANUAL:
        limitations.append("customer_manual_evidence_not_hmrc_confirmed")
    else:
        limitations.append("hmrc_issued_evidence_does_not_make_this_an_hmrc_decision")
    return _result(
        status=PoAReductionStatus.REVIEW_READY_FOR_CUSTOMER_HMRC_ACTION,
        assessment=assessment, proposal=proposal, evidence=evidence, current=current,
        limitations=limitations,
    )
