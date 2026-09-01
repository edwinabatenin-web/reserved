"""Self-contained, fail-closed W2 customer-language presentation contract.

This module accepts only deliberately copied presentation facts. It does not
calculate tax, reconcile evidence, calculate funding, map internal objects,
persist data, recommend an amount, or grant payment or transfer authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum


CONTRACT_VERSION = "reserved-w2-customer-language/2.0"
PENNY = Decimal("0.01")
ZERO = Decimal("0.00")


class PresentationStatus(str, Enum):
    READY = "ready"
    REVIEW_REQUIRED = "review_required"


class EvidenceClassification(str, Enum):
    HMRC_CONFIRMED_EXACT = "hmrc_confirmed_exact"
    QUALIFIED_LOCAL_ESTIMATE = "qualified_local_estimate"


class ObligationKind(str, Enum):
    BALANCING_PAYMENT = "balancing_payment"
    FIRST_PAYMENT_ON_ACCOUNT = "first_payment_on_account"
    SECOND_PAYMENT_ON_ACCOUNT = "second_payment_on_account"


class AdjustmentKind(str, Enum):
    DEDUCTIONS_AND_CREDITS = "deductions_and_credits"
    PRIOR_PAYMENTS_ON_ACCOUNT = "prior_payments_on_account"
    PAYMENTS_MADE = "payments_made"
    CREDIT_OR_REFUND = "credit_or_refund"


class FundingClassification(str, Enum):
    GAP = "gap"
    EXACT = "exact"
    SURPLUS = "surplus"


class ClaimToReduceState(str, Enum):
    REVIEW_READY = "review_ready"
    CUSTOMER_CONFIRMATION_REQUIRED = "customer_confirmation_required"
    NO_REDUCTION = "no_reduction"
    NOT_APPLICABLE = "not_applicable"
    REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True)
class ObligationFact:
    kind: ObligationKind
    amount: Decimal
    due_date: date


@dataclass(frozen=True)
class AdjustmentFact:
    kind: AdjustmentKind
    amount: Decimal


@dataclass(frozen=True)
class W2PresentationInput:
    contract_version: str
    status: PresentationStatus
    evidence: EvidenceClassification | None
    annual_liability: Decimal | None
    obligations: tuple[ObligationFact, ...]
    adjustments: tuple[AdjustmentFact, ...]
    funding: FundingClassification | None
    funding_amount: Decimal | None
    claim_to_reduce: ClaimToReduceState | None = None


@dataclass(frozen=True)
class MoneyLine:
    label: str
    amount: str
    due_date: str | None = None


@dataclass(frozen=True)
class W2CustomerLanguageView:
    contract_version: str
    safe_to_present: bool
    status_tone: str
    status_heading: str
    status_message: str
    evidence_label: str
    annual_liability: MoneyLine | None
    obligations: tuple[MoneyLine, ...]
    account_adjustments: tuple[MoneyLine, ...]
    funding_heading: str | None
    funding_message: str | None
    claim_to_reduce_heading: str | None
    claim_to_reduce_message: str | None
    claim_to_reduce_warning: str | None
    no_payment_authority: str


_OBLIGATION_LABELS = {
    ObligationKind.BALANCING_PAYMENT: "Balancing payment",
    ObligationKind.FIRST_PAYMENT_ON_ACCOUNT: "First Payment on Account",
    ObligationKind.SECOND_PAYMENT_ON_ACCOUNT: "Second Payment on Account",
}
_ADJUSTMENT_LABELS = {
    AdjustmentKind.DEDUCTIONS_AND_CREDITS: "Deductions and credits already included",
    AdjustmentKind.PRIOR_PAYMENTS_ON_ACCOUNT: "Prior Payments on Account already included",
    AdjustmentKind.PAYMENTS_MADE: "Payments already included",
    AdjustmentKind.CREDIT_OR_REFUND: "Credit or refund position — not counted as an obligation",
}


def _money(value: Decimal) -> str:
    return f"£{value:,.2f}"


def _date(value: date) -> str:
    return value.strftime("%-d %B %Y")


def _closed() -> W2CustomerLanguageView:
    return W2CustomerLanguageView(
        CONTRACT_VERSION, False, "warning", "Review required",
        "Amounts and dates are hidden because the presentation facts are missing, "
        "stale, conflicting, incomplete, unsupported or need review.",
        "Evidence could not be presented safely", None, (), (), None, None,
        None, None, None,
        "This view does not authorise a payment or transfer.",
    )


def _valid_money(value: object) -> bool:
    if type(value) is not Decimal or not value.is_finite() or value < ZERO:
        return False
    try:
        return value == value.quantize(PENNY)
    except (InvalidOperation, ValueError):
        return False


def _valid_input(value: object) -> bool:
    if type(value) is not W2PresentationInput:
        return False
    if value.contract_version != CONTRACT_VERSION:
        return False
    if type(value.status) is not PresentationStatus or value.status is not PresentationStatus.READY:
        return False
    if type(value.evidence) is not EvidenceClassification:
        return False
    if not _valid_money(value.annual_liability):
        return False
    if type(value.obligations) is not tuple or type(value.adjustments) is not tuple:
        return False
    obligation_kinds: list[ObligationKind] = []
    for item in value.obligations:
        if (
            type(item) is not ObligationFact
            or type(item.kind) is not ObligationKind
            or item.kind not in _OBLIGATION_LABELS
            or not _valid_money(item.amount)
            or type(item.due_date) is not date
        ):
            return False
        obligation_kinds.append(item.kind)
    if len(set(obligation_kinds)) != len(obligation_kinds):
        return False
    adjustment_kinds: list[AdjustmentKind] = []
    for item in value.adjustments:
        if (
            type(item) is not AdjustmentFact
            or type(item.kind) is not AdjustmentKind
            or item.kind not in _ADJUSTMENT_LABELS
            or not _valid_money(item.amount)
        ):
            return False
        adjustment_kinds.append(item.kind)
    if len(set(adjustment_kinds)) != len(adjustment_kinds):
        return False
    if type(value.funding) is not FundingClassification:
        return False
    if value.funding is FundingClassification.EXACT:
        if value.funding_amount is not None:
            return False
    elif not _valid_money(value.funding_amount) or value.funding_amount == ZERO:
        return False
    return value.claim_to_reduce is None or type(value.claim_to_reduce) is ClaimToReduceState


def _claim_language(value: ClaimToReduceState | None):
    if value is None:
        return None, None, None
    messages = {
        ClaimToReduceState.REVIEW_READY:
            "You have prepared a claim for your review and submission to HMRC. No amount is recommended here.",
        ClaimToReduceState.CUSTOMER_CONFIRMATION_REQUIRED:
            "A claim can proceed only after you confirm your proposed amounts. No amount is recommended here.",
        ClaimToReduceState.NO_REDUCTION:
            "No reduction is shown. Any claim is a separate action you initiate with HMRC.",
        ClaimToReduceState.NOT_APPLICABLE:
            "A claim to reduce is not applicable to this Payments on Account position.",
        ClaimToReduceState.REVIEW_REQUIRED:
            "Claim details cannot be shown until they are reviewed.",
    }
    return (
        "Claim to reduce", messages[value],
        "Reducing Payments on Account too far may lead to interest.",
    )


def present_w2_customer_language(value: W2PresentationInput) -> W2CustomerLanguageView:
    """Select fixed presentation language from a strict customer-safe input."""
    if not _valid_input(value):
        return _closed()

    confirmed = value.evidence is EvidenceClassification.HMRC_CONFIRMED_EXACT
    evidence_label = (
        "HMRC-recorded cash obligations" if confirmed
        else "Local estimate — not confirmed by HMRC"
    )
    status_heading = "Exact agreement" if confirmed else "Local estimate available"
    status_message = (
        "The dated obligations agree exactly with the HMRC account evidence."
        if confirmed else
        "These dated obligations are local estimates and must not be read as your current HMRC bill."
    )
    obligations = tuple(
        MoneyLine(_OBLIGATION_LABELS[item.kind], _money(item.amount), _date(item.due_date))
        for item in value.obligations
    )
    adjustments = tuple(
        MoneyLine(_ADJUSTMENT_LABELS[item.kind], _money(item.amount))
        for item in value.adjustments if item.amount != ZERO
    )
    if value.funding is FundingClassification.GAP:
        funding_heading = "Set-aside gap"
        funding_message = (
            f"Recorded set-aside is short by {_money(value.funding_amount)}. "
            "This is not a transfer recommendation."
        )
    elif value.funding is FundingClassification.EXACT:
        funding_heading = "Exact set-aside coverage"
        funding_message = (
            "Recorded set-aside exactly covers the obligations shown. "
            "This is not a payment instruction."
        )
    else:
        funding_heading = "Set-aside surplus"
        funding_message = (
            f"Recorded set-aside exceeds the obligations shown by {_money(value.funding_amount)}. "
            "The surplus is not available cash and is not described as spendable."
        )
    claim_heading, claim_message, claim_warning = _claim_language(value.claim_to_reduce)
    return W2CustomerLanguageView(
        CONTRACT_VERSION, True, "success" if confirmed else "information",
        status_heading, status_message, evidence_label,
        MoneyLine(
            "Calculated annual Self Assessment liability — not your current HMRC bill",
            _money(value.annual_liability),
        ),
        obligations, adjustments, funding_heading, funding_message,
        claim_heading, claim_message, claim_warning,
        "This view does not authorise a payment or transfer.",
    )
