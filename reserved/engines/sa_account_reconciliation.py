"""Pure reconciliation of explicit Self Assessment account evidence.

The component does not call HMRC, infer payments from bank activity, calculate
interest or penalties, or decide how a payment should be allocated.  It only
checks charges, credits and allocations that another boundary has normalised.

An arithmetically reconciled position is not necessarily HMRC-confirmed.
Confirmation is reported separately and requires complete-for-purpose evidence
whose provenance is HMRC online data or an HMRC-issued document.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
import re
from typing import Iterable


CONTRACT_VERSION = "reserved-sa-account-reconciliation/1.0"
PENNY = Decimal("0.01")
ZERO = Decimal("0.00")
_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_TAX_YEAR = re.compile(r"^(\d{4})/(\d{2})$")


class EvidenceSource(str, Enum):
    HMRC_ONLINE = "hmrc_online"
    HMRC_DOCUMENT = "hmrc_document"
    MANUAL = "manual"
    LOCAL_ESTIMATE = "local_estimate"


class Completeness(str, Enum):
    COMPLETE_FOR_PURPOSE = "complete_for_purpose"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class ChargeKind(str, Enum):
    BALANCING_PAYMENT = "balancing_payment"
    PAYMENT_ON_ACCOUNT_1 = "payment_on_account_1"
    PAYMENT_ON_ACCOUNT_2 = "payment_on_account_2"
    OTHER_SELF_ASSESSMENT_CHARGE = "other_self_assessment_charge"


class CreditKind(str, Enum):
    PAYMENT = "payment"
    HMRC_CREDIT = "hmrc_credit"
    TRANSFER_IN = "transfer_in"


class ReconciliationStatus(str, Enum):
    RECONCILED = "reconciled"
    INSUFFICIENT_FACTS = "insufficient_facts"
    STALE_REQUIRES_REVIEW = "stale_requires_review"
    CONFLICT_REQUIRES_REVIEW = "conflict_requires_review"


def _enum(value, enum_type, name):
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value)
        except ValueError:
            pass
    raise ValueError(f"{name} must be a valid {enum_type.__name__}")


def _money(value, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be monetary, not boolean")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{name} must be numeric") from None
    if not amount.is_finite() or amount < 0:
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


def _tax_year(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("tax_year must be a string")
    match = _TAX_YEAR.fullmatch(value)
    if not match or int(match.group(2)) != (int(match.group(1)) + 1) % 100:
        raise ValueError("tax_year must use consecutive YYYY/YY form")
    return value


@dataclass(frozen=True)
class AccountCharge:
    charge_id: str
    kind: ChargeKind
    tax_year: str
    amount: Decimal
    due_date: date
    effective_date: date
    observed_on: date
    source: EvidenceSource
    completeness: Completeness
    source_reference: str

    def __post_init__(self):
        object.__setattr__(self, "charge_id", _reference(self.charge_id, "charge_id"))
        object.__setattr__(self, "kind", _enum(self.kind, ChargeKind, "kind"))
        object.__setattr__(self, "tax_year", _tax_year(self.tax_year))
        object.__setattr__(self, "amount", _money(self.amount, "amount"))
        for field in ("due_date", "effective_date", "observed_on"):
            object.__setattr__(self, field, _date(getattr(self, field), field))
        object.__setattr__(self, "source", _enum(self.source, EvidenceSource, "source"))
        object.__setattr__(
            self, "completeness", _enum(self.completeness, Completeness, "completeness")
        )
        object.__setattr__(
            self, "source_reference", _reference(self.source_reference, "source_reference")
        )


@dataclass(frozen=True)
class AccountCredit:
    credit_id: str
    kind: CreditKind
    amount: Decimal
    effective_date: date
    observed_on: date
    source: EvidenceSource
    completeness: Completeness
    source_reference: str

    def __post_init__(self):
        object.__setattr__(self, "credit_id", _reference(self.credit_id, "credit_id"))
        object.__setattr__(self, "kind", _enum(self.kind, CreditKind, "kind"))
        object.__setattr__(self, "amount", _money(self.amount, "amount"))
        for field in ("effective_date", "observed_on"):
            object.__setattr__(self, field, _date(getattr(self, field), field))
        object.__setattr__(self, "source", _enum(self.source, EvidenceSource, "source"))
        object.__setattr__(
            self, "completeness", _enum(self.completeness, Completeness, "completeness")
        )
        object.__setattr__(
            self, "source_reference", _reference(self.source_reference, "source_reference")
        )


@dataclass(frozen=True)
class ExplicitAllocation:
    allocation_id: str
    charge_id: str
    credit_id: str
    amount: Decimal
    observed_on: date
    source: EvidenceSource
    completeness: Completeness
    source_reference: str

    def __post_init__(self):
        for field in ("allocation_id", "charge_id", "credit_id", "source_reference"):
            object.__setattr__(self, field, _reference(getattr(self, field), field))
        object.__setattr__(self, "amount", _money(self.amount, "amount"))
        object.__setattr__(self, "observed_on", _date(self.observed_on, "observed_on"))
        object.__setattr__(self, "source", _enum(self.source, EvidenceSource, "source"))
        object.__setattr__(
            self, "completeness", _enum(self.completeness, Completeness, "completeness")
        )


@dataclass(frozen=True)
class ChargePosition:
    charge_id: str
    kind: ChargeKind
    tax_year: str
    due_date: date
    amount: Decimal
    allocated: Decimal
    remaining: Decimal
    overdue: bool
    source: EvidenceSource
    effective_date: date
    observed_on: date
    completeness: Completeness
    source_reference: str


@dataclass(frozen=True)
class CreditPosition:
    credit_id: str
    kind: CreditKind
    effective_date: date
    amount: Decimal
    allocated: Decimal
    unallocated: Decimal
    source: EvidenceSource
    observed_on: date
    completeness: Completeness
    source_reference: str


@dataclass(frozen=True)
class AllocationPosition:
    allocation_id: str
    charge_id: str
    credit_id: str
    amount: Decimal
    observed_on: date
    source: EvidenceSource
    completeness: Completeness
    source_reference: str


@dataclass(frozen=True)
class AccountReconciliation:
    contract_version: str
    as_of: date
    status: ReconciliationStatus
    hmrc_confirmed: bool
    total_charges: Decimal | None
    total_credits: Decimal | None
    remaining_charge_balance: Decimal | None
    unallocated_credit: Decimal | None
    net_account_position: Decimal | None
    charge_positions: tuple[ChargePosition, ...]
    credit_positions: tuple[CreditPosition, ...]
    allocation_positions: tuple[AllocationPosition, ...]
    considered_charges: tuple[AccountCharge, ...]
    considered_credits: tuple[AccountCredit, ...]
    considered_allocations: tuple[ExplicitAllocation, ...]
    evidence_sources: tuple[EvidenceSource, ...]
    limitations: tuple[str, ...]
    prohibited_uses: tuple[str, ...]


_PROHIBITED_USES = (
    "present_unconfirmed_position_as_hmrc_bill",
    "present_as_available_cash",
    "autonomous_payment_or_reallocation",
    "self_assessment_filing",
    "debt_or_enforcement_action",
)


def _unresolved(
    as_of: date,
    status: ReconciliationStatus,
    sources,
    limitations,
    charges=(),
    credits=(),
    allocations=(),
):
    return AccountReconciliation(
        contract_version=CONTRACT_VERSION,
        as_of=as_of,
        status=status,
        hmrc_confirmed=False,
        total_charges=None,
        total_credits=None,
        remaining_charge_balance=None,
        unallocated_credit=None,
        net_account_position=None,
        charge_positions=(),
        credit_positions=(),
        allocation_positions=(),
        considered_charges=tuple(sorted(
            charges,
            key=lambda item: (
                item.charge_id, item.source_reference, item.kind.value,
                item.amount, item.effective_date, item.observed_on,
            ),
        )),
        considered_credits=tuple(sorted(
            credits,
            key=lambda item: (
                item.credit_id, item.source_reference, item.kind.value,
                item.amount, item.effective_date, item.observed_on,
            ),
        )),
        considered_allocations=tuple(sorted(
            allocations,
            key=lambda item: (
                item.allocation_id, item.charge_id, item.credit_id,
                item.source_reference, item.amount, item.observed_on,
            ),
        )),
        evidence_sources=tuple(sorted(set(sources), key=lambda item: item.value)),
        limitations=tuple(dict.fromkeys(limitations)),
        prohibited_uses=_PROHIBITED_USES,
    )


def reconcile_sa_account(
    charges: Iterable[AccountCharge],
    credits: Iterable[AccountCredit],
    allocations: Iterable[ExplicitAllocation],
    *,
    as_of: date,
    coverage: Completeness,
    stale_after_days: int = 45,
) -> AccountReconciliation:
    """Reconcile only supplied explicit allocation evidence.

    ``net_account_position`` is charges minus credits.  It is an evidence
    position, not an instruction to pay and not an HMRC-confirmed bill unless
    ``hmrc_confirmed`` is also true.
    """
    as_of = _date(as_of, "as_of")
    coverage = _enum(coverage, Completeness, "coverage")
    if isinstance(stale_after_days, bool) or not isinstance(stale_after_days, int):
        raise ValueError("stale_after_days must be an integer")
    if stale_after_days < 0:
        raise ValueError("stale_after_days must be non-negative")

    charges = tuple(charges)
    credits = tuple(credits)
    allocations = tuple(allocations)
    all_items = charges + credits + allocations
    sources = tuple(item.source for item in all_items)

    def unresolved(status, limitations):
        return _unresolved(
            as_of, status, sources, limitations, charges, credits, allocations,
        )

    for item in all_items:
        if item.observed_on > as_of:
            raise ValueError("evidence observed_on cannot be in the future")
    for charge in charges:
        if charge.effective_date > as_of:
            raise ValueError("charge effective_date cannot be in the future")
        if charge.effective_date > charge.observed_on:
            raise ValueError("charge effective_date cannot be after observed_on")
    for credit in credits:
        if credit.effective_date > as_of:
            raise ValueError("credit effective_date cannot be in the future")
        if credit.effective_date > credit.observed_on:
            raise ValueError("credit effective_date cannot be after observed_on")

    if not charges and not credits:
        return unresolved(
            ReconciliationStatus.INSUFFICIENT_FACTS,
            ("no_account_transactions_supplied",),
        )

    charge_ids = [item.charge_id for item in charges]
    credit_ids = [item.credit_id for item in credits]
    allocation_ids = [item.allocation_id for item in allocations]
    if len(set(charge_ids)) != len(charge_ids):
        return unresolved(ReconciliationStatus.CONFLICT_REQUIRES_REVIEW,
                          ("duplicate_or_conflicting_charge_identity",))
    if len(set(credit_ids)) != len(credit_ids):
        return unresolved(ReconciliationStatus.CONFLICT_REQUIRES_REVIEW,
                          ("duplicate_or_conflicting_credit_identity",))
    if len(set(allocation_ids)) != len(allocation_ids):
        return unresolved(ReconciliationStatus.CONFLICT_REQUIRES_REVIEW,
                          ("duplicate_or_conflicting_allocation_identity",))

    charge_by_id = {item.charge_id: item for item in charges}
    credit_by_id = {item.credit_id: item for item in credits}
    if any(item.charge_id not in charge_by_id for item in allocations):
        return unresolved(ReconciliationStatus.CONFLICT_REQUIRES_REVIEW,
                          ("allocation_references_unknown_charge",))
    if any(item.credit_id not in credit_by_id for item in allocations):
        return unresolved(ReconciliationStatus.CONFLICT_REQUIRES_REVIEW,
                          ("allocation_references_unknown_credit",))

    allocated_to_charge = {identity: ZERO for identity in charge_by_id}
    allocated_from_credit = {identity: ZERO for identity in credit_by_id}
    for item in allocations:
        allocated_to_charge[item.charge_id] += item.amount
        allocated_from_credit[item.credit_id] += item.amount
    if any(allocated_to_charge[key] > charge_by_id[key].amount for key in charge_by_id):
        return unresolved(ReconciliationStatus.CONFLICT_REQUIRES_REVIEW,
                          ("allocation_exceeds_charge",))
    if any(allocated_from_credit[key] > credit_by_id[key].amount for key in credit_by_id):
        return unresolved(ReconciliationStatus.CONFLICT_REQUIRES_REVIEW,
                          ("allocation_exceeds_credit",))

    if coverage is not Completeness.COMPLETE_FOR_PURPOSE or any(
        item.completeness is not Completeness.COMPLETE_FOR_PURPOSE for item in all_items
    ):
        return unresolved(ReconciliationStatus.INSUFFICIENT_FACTS,
                          ("account_evidence_not_complete_for_purpose",))
    if any((as_of - item.observed_on).days > stale_after_days for item in all_items):
        return unresolved(ReconciliationStatus.STALE_REQUIRES_REVIEW,
                          ("account_evidence_is_stale",))

    charge_positions = tuple(
        ChargePosition(
            item.charge_id,
            item.kind,
            item.tax_year,
            item.due_date,
            item.amount,
            allocated_to_charge[item.charge_id],
            item.amount - allocated_to_charge[item.charge_id],
            item.due_date < as_of and item.amount > allocated_to_charge[item.charge_id],
            item.source,
            item.effective_date,
            item.observed_on,
            item.completeness,
            item.source_reference,
        )
        for item in sorted(charges, key=lambda value: (value.due_date, value.tax_year, value.charge_id))
    )
    credit_positions = tuple(
        CreditPosition(
            item.credit_id,
            item.kind,
            item.effective_date,
            item.amount,
            allocated_from_credit[item.credit_id],
            item.amount - allocated_from_credit[item.credit_id],
            item.source,
            item.observed_on,
            item.completeness,
            item.source_reference,
        )
        for item in sorted(credits, key=lambda value: (value.effective_date, value.credit_id))
    )
    allocation_positions = tuple(
        AllocationPosition(
            item.allocation_id,
            item.charge_id,
            item.credit_id,
            item.amount,
            item.observed_on,
            item.source,
            item.completeness,
            item.source_reference,
        )
        for item in sorted(
            allocations,
            key=lambda value: (
                value.allocation_id, value.charge_id, value.credit_id,
                value.source_reference,
            ),
        )
    )
    total_charges = sum((item.amount for item in charges), ZERO)
    total_credits = sum((item.amount for item in credits), ZERO)
    remaining = sum((item.remaining for item in charge_positions), ZERO)
    unallocated = sum((item.unallocated for item in credit_positions), ZERO)
    confirming_sources = {EvidenceSource.HMRC_ONLINE, EvidenceSource.HMRC_DOCUMENT}
    hmrc_confirmed = bool(all_items) and all(item.source in confirming_sources for item in all_items)
    limitations = ["observed_allocations_only_no_automatic_allocation"]
    if not hmrc_confirmed:
        limitations.append("position_not_hmrc_confirmed")
    if any(item.source is EvidenceSource.LOCAL_ESTIMATE for item in charges):
        limitations.append("local_estimate_charge_is_not_hmrc_issued")

    evidence_record = _unresolved(
        as_of, ReconciliationStatus.INSUFFICIENT_FACTS, sources, (),
        charges, credits, allocations,
    )

    return AccountReconciliation(
        contract_version=CONTRACT_VERSION,
        as_of=as_of,
        status=ReconciliationStatus.RECONCILED,
        hmrc_confirmed=hmrc_confirmed,
        total_charges=total_charges,
        total_credits=total_credits,
        remaining_charge_balance=remaining,
        unallocated_credit=unallocated,
        net_account_position=total_charges - total_credits,
        charge_positions=charge_positions,
        credit_positions=credit_positions,
        allocation_positions=allocation_positions,
        considered_charges=evidence_record.considered_charges,
        considered_credits=evidence_record.considered_credits,
        considered_allocations=evidence_record.considered_allocations,
        evidence_sources=tuple(sorted(set(sources), key=lambda item: item.value)),
        limitations=tuple(limitations),
        prohibited_uses=_PROHIBITED_USES,
    )
