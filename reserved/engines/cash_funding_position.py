"""Compose an evidence-qualified set-aside position for dated SA obligations.

This pure W2 component does not calculate tax, alter an HMRC account, infer a
bank balance, allocate or move money, recommend a transfer, persist data, or
render customer language.  It compares explicit customer-recorded set-aside
evidence with an already-reconciled S3 cash-obligation result.  A surplus is
never described as available or safe to spend.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
import re

from . import cash_obligation_reconciliation as obligations


CONTRACT_VERSION = "reserved-cash-funding-position/1.0"
PENNY = Decimal("0.01")
ZERO = Decimal("0.00")
_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_OBLIGATION_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_UNCERTAINTY = frozenset({"missing", "stale", "conflicting", "incomplete"})


class SetAsideSource(str, Enum):
    CUSTOMER_RECORDED = "customer_recorded"
    FINANCIAL_ACCOUNT_EVIDENCE = "financial_account_evidence"
    LOCAL_ESTIMATE = "local_estimate"


class EvidenceCompleteness(str, Enum):
    COMPLETE_FOR_PURPOSE = "complete_for_purpose"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class FundingComputationStatus(str, Enum):
    CALCULATED = "calculated"
    INSUFFICIENT_FACTS = "insufficient_facts"
    STALE_REQUIRES_REVIEW = "stale_requires_review"
    CONFLICT_REQUIRES_REVIEW = "conflict_requires_review"
    OBLIGATION_REVIEW_REQUIRED = "obligation_review_required"


class FundingBalance(str, Enum):
    GAP = "gap"
    EXACT = "exact"
    SURPLUS = "surplus"


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


def _obligation_reference(value) -> str:
    if not isinstance(value, str) or not _OBLIGATION_REFERENCE.fullmatch(value):
        raise ValueError("obligation_id must be a stable non-empty obligation reference")
    return value


def _enum(value, enum_type, name: str):
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value)
        except ValueError:
            pass
    raise ValueError(f"{name} must be a valid {enum_type.__name__}")


@dataclass(frozen=True)
class SetAsideAllocation:
    allocation_id: str
    obligation_id: str
    amount: Decimal

    def __post_init__(self):
        object.__setattr__(
            self, "allocation_id", _reference(self.allocation_id, "allocation_id")
        )
        object.__setattr__(
            self, "obligation_id", _obligation_reference(self.obligation_id)
        )
        object.__setattr__(self, "amount", _money(self.amount, "allocation amount"))


@dataclass(frozen=True)
class SetAsideEvidence:
    evidence_id: str
    total_amount: Decimal
    effective_date: date
    observed_on: date
    source: SetAsideSource
    completeness: EvidenceCompleteness
    source_reference: str
    allocations: tuple[SetAsideAllocation, ...] = ()
    uncertainty: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "evidence_id", _reference(self.evidence_id, "evidence_id"))
        object.__setattr__(self, "total_amount", _money(self.total_amount, "total_amount"))
        object.__setattr__(self, "effective_date", _date(self.effective_date, "effective_date"))
        object.__setattr__(self, "observed_on", _date(self.observed_on, "observed_on"))
        if self.observed_on < self.effective_date:
            raise ValueError("observed_on cannot be before effective_date")
        object.__setattr__(self, "source", _enum(self.source, SetAsideSource, "source"))
        object.__setattr__(
            self,
            "completeness",
            _enum(self.completeness, EvidenceCompleteness, "completeness"),
        )
        object.__setattr__(
            self, "source_reference", _reference(self.source_reference, "source_reference")
        )
        if not isinstance(self.allocations, tuple) or not all(
            isinstance(item, SetAsideAllocation) for item in self.allocations
        ):
            raise ValueError("allocations must be an immutable tuple of SetAsideAllocation")
        if not isinstance(self.uncertainty, tuple):
            raise ValueError("uncertainty must be an immutable tuple")
        if any(item not in _UNCERTAINTY for item in self.uncertainty):
            raise ValueError("uncertainty contains an unsupported reason")


@dataclass(frozen=True)
class DatedFundingRequirement:
    obligation: obligations.ExpectedCashObligation
    explicitly_allocated_set_aside: Decimal
    remaining_requirement: Decimal
    excess_allocation: Decimal


@dataclass(frozen=True)
class DatedFundingTotal:
    due_date: date
    required: Decimal
    explicitly_allocated_set_aside: Decimal
    remaining_requirement: Decimal
    excess_allocation: Decimal


@dataclass(frozen=True)
class CashFundingPosition:
    contract_version: str
    status: FundingComputationStatus
    balance: FundingBalance | None
    total_required: Decimal | None
    total_set_aside: Decimal | None
    funding_gap: Decimal | None
    reserve_surplus: Decimal | None
    unallocated_set_aside: Decimal | None
    dated_coverage_complete: bool
    requirements: tuple[DatedFundingRequirement, ...]
    schedule: tuple[DatedFundingTotal, ...]
    as_of: date
    obligations_hmrc_confirmed: bool
    considered_obligations: obligations.CashObligationReconciliation
    considered_set_aside: SetAsideEvidence | None
    limitations: tuple[str, ...]
    warnings: tuple[str, ...]
    prohibited_uses: tuple[str, ...]


_WARNINGS = (
    "reserve_surplus_is_not_available_or_safe_to_spend",
    "no_payment_or_transfer_is_authorised",
)
_PROHIBITED_USES = (
    "present_surplus_as_available_cash",
    "recommend_or_initiate_payment_or_transfer",
    "autonomous_allocation",
    "hmrc_account_alteration_or_filing",
    "interest_or_penalty_calculation",
    "professional_tax_advice",
    "production_account_access",
    "persistence_or_customer_rendering",
)


def _empty_result(*, status, reconciliation, evidence, as_of, limitations):
    return CashFundingPosition(
        contract_version=CONTRACT_VERSION,
        status=status,
        balance=None,
        total_required=None,
        total_set_aside=None,
        funding_gap=None,
        reserve_surplus=None,
        unallocated_set_aside=None,
        dated_coverage_complete=False,
        requirements=(),
        schedule=(),
        as_of=as_of,
        obligations_hmrc_confirmed=False,
        considered_obligations=reconciliation,
        considered_set_aside=evidence,
        limitations=tuple(dict.fromkeys(limitations)),
        warnings=_WARNINGS,
        prohibited_uses=_PROHIBITED_USES,
    )


def _validated_reconciliation(value):
    if not isinstance(value, obligations.CashObligationReconciliation):
        raise ValueError("obligation_reconciliation must be a CashObligationReconciliation")
    if value.contract_version != obligations.CONTRACT_VERSION:
        raise ValueError("obligation_reconciliation contract_version is unsupported")
    if not isinstance(value.status, obligations.CashObligationStatus):
        return None, "obligation_reconciliation_inconsistent"
    try:
        recomputed = obligations.reconcile_cash_obligations(
            account_reconciliation=value.considered_account,
            poa_assessment=value.considered_poa,
            balancing_position=value.considered_balancing,
        )
    except (ValueError, TypeError, AttributeError, ArithmeticError):
        return None, "obligation_reconciliation_inconsistent"
    if recomputed != value:
        return None, "obligation_reconciliation_inconsistent"
    if value.status not in {
        obligations.CashObligationStatus.ALIGNED,
        obligations.CashObligationStatus.OBSERVATION_NOT_HMRC_CONFIRMED,
    }:
        return None, "obligation_reconciliation_requires_review"
    expected = value.expected_obligations
    if not isinstance(expected, tuple) or not all(
        isinstance(item, obligations.ExpectedCashObligation) for item in expected
    ):
        return None, "obligation_reconciliation_inconsistent"
    identities = tuple(item.obligation_id for item in expected)
    if len(set(identities)) != len(identities):
        return None, "obligation_reconciliation_inconsistent"
    return expected, None


def _validated_set_aside_evidence(value):
    """Revalidate a frozen evidence object at the trust boundary.

    Frozen dataclasses protect ordinary callers, but are not an authenticity
    boundary: low-level mutation can bypass ``__post_init__``.  Reconstructing
    every nested value and requiring exact equality prevents such a forged
    object from producing a calculated funding position.
    """
    if not isinstance(value, SetAsideEvidence):
        raise ValueError("set_aside_evidence must be SetAsideEvidence or None")
    if not isinstance(value.source, SetAsideSource) or not isinstance(
        value.completeness, EvidenceCompleteness
    ):
        return None, "set_aside_evidence_inconsistent"
    if not isinstance(value.allocations, tuple) or not all(
        isinstance(item, SetAsideAllocation) for item in value.allocations
    ):
        return None, "set_aside_evidence_inconsistent"
    try:
        allocations = tuple(
            SetAsideAllocation(
                allocation_id=item.allocation_id,
                obligation_id=item.obligation_id,
                amount=item.amount,
            )
            for item in value.allocations
        )
        reconstructed = SetAsideEvidence(
            evidence_id=value.evidence_id,
            total_amount=value.total_amount,
            effective_date=value.effective_date,
            observed_on=value.observed_on,
            source=value.source,
            completeness=value.completeness,
            source_reference=value.source_reference,
            allocations=allocations,
            uncertainty=value.uncertainty,
        )
    except (ValueError, TypeError, AttributeError, ArithmeticError):
        return None, "set_aside_evidence_inconsistent"
    if reconstructed != value:
        return None, "set_aside_evidence_inconsistent"
    return reconstructed, None


def _schedule(requirements):
    by_date = {}
    for item in requirements:
        values = by_date.setdefault(item.obligation.due_date, [ZERO, ZERO, ZERO, ZERO])
        values[0] += item.obligation.amount
        values[1] += item.explicitly_allocated_set_aside
        values[2] += item.remaining_requirement
        values[3] += item.excess_allocation
    return tuple(
        DatedFundingTotal(due_date, *by_date[due_date])
        for due_date in sorted(by_date)
    )


def compose_cash_funding_position(
    *,
    obligation_reconciliation: obligations.CashObligationReconciliation,
    set_aside_evidence: SetAsideEvidence | None,
    as_of: date,
    stale_after_days: int = 45,
) -> CashFundingPosition:
    """Compose a total and dated funding position from explicit evidence."""
    as_of = _date(as_of, "as_of")
    if isinstance(stale_after_days, bool) or not isinstance(stale_after_days, int):
        raise ValueError("stale_after_days must be an integer")
    if stale_after_days < 0:
        raise ValueError("stale_after_days must be non-negative")
    if set_aside_evidence is not None and not isinstance(
        set_aside_evidence, SetAsideEvidence
    ):
        raise ValueError("set_aside_evidence must be SetAsideEvidence or None")

    expected, problem = _validated_reconciliation(obligation_reconciliation)
    if problem is not None:
        return _empty_result(
            status=(
                FundingComputationStatus.OBLIGATION_REVIEW_REQUIRED
                if problem == "obligation_reconciliation_requires_review"
                else FundingComputationStatus.INSUFFICIENT_FACTS
            ),
            reconciliation=obligation_reconciliation,
            evidence=set_aside_evidence,
            as_of=as_of,
            limitations=(problem, "no_funding_point_result"),
        )
    if set_aside_evidence is None:
        return _empty_result(
            status=FundingComputationStatus.INSUFFICIENT_FACTS,
            reconciliation=obligation_reconciliation,
            evidence=None,
            as_of=as_of,
            limitations=("missing_set_aside_evidence", "no_funding_point_result"),
        )

    evidence, evidence_problem = _validated_set_aside_evidence(set_aside_evidence)
    if evidence_problem is not None:
        return _empty_result(
            status=FundingComputationStatus.INSUFFICIENT_FACTS,
            reconciliation=obligation_reconciliation,
            evidence=set_aside_evidence,
            as_of=as_of,
            limitations=(evidence_problem, "no_funding_point_result"),
        )
    if evidence.observed_on > as_of:
        return _empty_result(
            status=FundingComputationStatus.CONFLICT_REQUIRES_REVIEW,
            reconciliation=obligation_reconciliation,
            evidence=evidence,
            as_of=as_of,
            limitations=("set_aside_observation_is_in_the_future",),
        )
    if "conflicting" in evidence.uncertainty:
        return _empty_result(
            status=FundingComputationStatus.CONFLICT_REQUIRES_REVIEW,
            reconciliation=obligation_reconciliation,
            evidence=evidence,
            as_of=as_of,
            limitations=("set_aside_evidence_conflicting",),
        )
    if evidence.completeness is not EvidenceCompleteness.COMPLETE_FOR_PURPOSE or any(
        item in evidence.uncertainty for item in ("missing", "incomplete")
    ):
        return _empty_result(
            status=FundingComputationStatus.INSUFFICIENT_FACTS,
            reconciliation=obligation_reconciliation,
            evidence=evidence,
            as_of=as_of,
            limitations=("set_aside_evidence_incomplete",),
        )
    if "stale" in evidence.uncertainty or (
        as_of - evidence.observed_on
    ).days > stale_after_days:
        return _empty_result(
            status=FundingComputationStatus.STALE_REQUIRES_REVIEW,
            reconciliation=obligation_reconciliation,
            evidence=evidence,
            as_of=as_of,
            limitations=("set_aside_evidence_stale",),
        )

    allocation_ids = tuple(item.allocation_id for item in evidence.allocations)
    if len(set(allocation_ids)) != len(allocation_ids):
        return _empty_result(
            status=FundingComputationStatus.CONFLICT_REQUIRES_REVIEW,
            reconciliation=obligation_reconciliation,
            evidence=evidence,
            as_of=as_of,
            limitations=("duplicate_set_aside_allocation_id",),
        )
    expected_ids = {item.obligation_id for item in expected}
    if any(item.obligation_id not in expected_ids for item in evidence.allocations):
        return _empty_result(
            status=FundingComputationStatus.CONFLICT_REQUIRES_REVIEW,
            reconciliation=obligation_reconciliation,
            evidence=evidence,
            as_of=as_of,
            limitations=("allocation_references_unknown_obligation",),
        )
    allocated_total = sum((item.amount for item in evidence.allocations), ZERO)
    if allocated_total > evidence.total_amount:
        return _empty_result(
            status=FundingComputationStatus.CONFLICT_REQUIRES_REVIEW,
            reconciliation=obligation_reconciliation,
            evidence=evidence,
            as_of=as_of,
            limitations=("allocated_set_aside_exceeds_total_evidence",),
        )

    by_obligation = {item_id: ZERO for item_id in expected_ids}
    for allocation in evidence.allocations:
        by_obligation[allocation.obligation_id] += allocation.amount
    requirements = []
    for obligation in expected:
        allocated = by_obligation[obligation.obligation_id]
        requirements.append(DatedFundingRequirement(
            obligation=obligation,
            explicitly_allocated_set_aside=allocated,
            remaining_requirement=max(ZERO, obligation.amount - allocated),
            excess_allocation=max(ZERO, allocated - obligation.amount),
        ))
    requirements = tuple(sorted(
        requirements,
        key=lambda item: (
            item.obligation.due_date,
            item.obligation.tax_year,
            item.obligation.kind.value,
            item.obligation.obligation_id,
        ),
    ))

    total_required = sum((item.amount for item in expected), ZERO)
    total_set_aside = evidence.total_amount
    gap = max(ZERO, total_required - total_set_aside)
    surplus = max(ZERO, total_set_aside - total_required)
    balance = (
        FundingBalance.GAP if gap > ZERO
        else FundingBalance.SURPLUS if surplus > ZERO
        else FundingBalance.EXACT
    )
    unallocated = total_set_aside - allocated_total
    dated_complete = (
        unallocated == ZERO
        and not any(item.excess_allocation > ZERO for item in requirements)
        and not any(item.remaining_requirement > ZERO for item in requirements)
    )

    limitations = ["comparison_only_no_payment_or_transfer_action"]
    if obligation_reconciliation.status is (
        obligations.CashObligationStatus.OBSERVATION_NOT_HMRC_CONFIRMED
    ):
        limitations.append("cash_obligations_not_hmrc_confirmed")
    if evidence.source is SetAsideSource.CUSTOMER_RECORDED:
        limitations.append("set_aside_amount_customer_recorded_not_independently_confirmed")
    elif evidence.source is SetAsideSource.LOCAL_ESTIMATE:
        limitations.append("set_aside_amount_is_local_estimate")
    if unallocated > ZERO:
        limitations.append("set_aside_not_fully_allocated_to_dated_obligations")
    if any(item.excess_allocation > ZERO for item in requirements):
        limitations.append("explicit_allocation_exceeds_an_obligation")

    return CashFundingPosition(
        contract_version=CONTRACT_VERSION,
        status=FundingComputationStatus.CALCULATED,
        balance=balance,
        total_required=total_required,
        total_set_aside=total_set_aside,
        funding_gap=gap,
        reserve_surplus=surplus,
        unallocated_set_aside=unallocated,
        dated_coverage_complete=dated_complete,
        requirements=requirements,
        schedule=_schedule(requirements),
        as_of=as_of,
        obligations_hmrc_confirmed=obligation_reconciliation.account_hmrc_confirmed,
        considered_obligations=obligation_reconciliation,
        considered_set_aside=evidence,
        limitations=tuple(dict.fromkeys(limitations)),
        warnings=_WARNINGS,
        prohibited_uses=_PROHIBITED_USES,
    )
