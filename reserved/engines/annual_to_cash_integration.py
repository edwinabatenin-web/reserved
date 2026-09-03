"""Bind the reviewed W1 annual result to W2 cash-obligation contracts.

This pure internal adapter composes existing W1 and W2 results.  It does not
recalculate annual tax, source HMRC/provider evidence, persist or render data,
recommend or initiate a payment, file a return, or treat a reserve surplus as
available cash.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import hashlib
import hmac
import json
import re
import threading
from typing import Iterable
import weakref

from . import cash_funding_position as funding
from . import cash_obligation_reconciliation as obligations
from . import payments_on_account as poa
from . import sa_account_reconciliation as account
from .annual_loan_reconciliation import LoanComponent
from .cash_ready_annual_position import CashReadyAnnualPosition, CashReadyLoanComponent


CONTRACT_VERSION = "reserved-annual-to-cash-integration/1.0"
ANNUAL_CONTRACT_VERSION = "reserved-cash-ready-annual-position/1.0"
PENNY = Decimal("0.01")
ZERO = Decimal("0.00")
ANNUAL_PERIOD_END = date(2027, 4, 5)
_DIGEST_REFERENCE = re.compile(r"^[a-z-]+:sha256-[0-9a-f]{64}$")
_SOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")


class AnnualToCashStatus(str, Enum):
    CALCULATED = "calculated"
    QUALIFIED_LOCAL_RESULT = "qualified_local_result"
    REVIEW_REQUIRED = "review_required"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True)
class AnnualToCashPosition:
    contract_version: str
    status: AnnualToCashStatus
    tax_year: str
    ruleset_version: str
    as_of: date
    annual_position_reference: str
    considered_annual_position: CashReadyAnnualPosition
    poa_assessment: poa.PoAAssessment | None
    balancing_position: poa.BalancingPosition | None
    obligation_reconciliation: obligations.CashObligationReconciliation | None
    funding_position: funding.CashFundingPosition | None
    final_self_assessment_liability: Decimal | None
    limitations: tuple[str, ...]
    prohibited_uses: tuple[str, ...]


@dataclass(frozen=True)
class AnnualToCashInputProvenance:
    """Process-local evidence bindings captured by the producer."""

    annual_position_reference: str
    preceding_year_status: poa.PrecedingYearStatus
    prior_year_reference: str | None
    deductions_credits_reference: str
    deductions_credits_evidence_ids: tuple[str, ...]
    prior_poa_reference: str
    prior_poa_evidence_ids: tuple[str, ...]
    payment_content_references: tuple[str, ...]
    payment_source_ids: tuple[str, ...]
    account_reconciliation_reference: str
    set_aside_evidence_reference: str | None
    as_of: date
    stale_after_days: int


_PROHIBITED_USES = (
    "customer_presentation_without_separate_ux_approval",
    "present_local_expectation_as_hmrc_bill",
    "present_surplus_as_available_or_safe_to_spend",
    "recommend_or_initiate_payment_or_transfer",
    "autonomous_allocation",
    "self_assessment_filing",
    "production_account_access",
    "persistence_without_separate_approval",
)


def _canonical(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "type": type(value).__name__,
            "fields": {
                item.name: _canonical(getattr(value, item.name)) for item in fields(value)
            },
        }
    if isinstance(value, Decimal):
        return {"decimal": str(value)}
    if type(value) is date:
        return {"date": value.isoformat()}
    if isinstance(value, Enum):
        return {"enum": f"{type(value).__name__}:{value.value}"}
    if isinstance(value, tuple):
        return [_canonical(item) for item in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise ValueError(f"Unsupported identity value type: {type(value).__name__}")


def _content_digest(value: object) -> str:
    payload = json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _make_issuance_capability():
    """Create capabilities whose security-critical state has no global lookup."""
    sha256 = hashlib.sha256
    dumps = json.dumps
    compare = hmac.compare_digest
    dc_fields = fields
    lock = threading.RLock()
    registry: dict[int, tuple[weakref.ReferenceType[AnnualToCashPosition],
                              AnnualToCashInputProvenance, str]] = {}
    allowed_dataclasses = frozenset(
        value
        for module in (poa, account, obligations, funding)
        for value in vars(module).values()
        if type(value) is type and is_dataclass(value)
    ) | frozenset({
        AnnualToCashPosition, AnnualToCashInputProvenance,
        CashReadyAnnualPosition, CashReadyLoanComponent,
    })
    allowed_enums = frozenset(
        value
        for module in (poa, account, obligations, funding)
        for value in vars(module).values()
        if isinstance(value, type) and issubclass(value, Enum)
    ) | frozenset({AnnualToCashStatus, LoanComponent})
    failure = "annual-to-cash position is not a valid live producer-issued value"

    def canonical(value: object) -> object:
        value_type = type(value)
        if value_type in allowed_dataclasses:
            return {
                "type": f"{value_type.__module__}.{value_type.__qualname__}",
                "fields": {
                    item.name: canonical(object.__getattribute__(value, item.name))
                    for item in dc_fields(value_type)
                },
            }
        if value_type is Decimal:
            return {"decimal": str(value)}
        if value_type is date:
            return {"date": value.isoformat()}
        if value_type in allowed_enums:
            return {
                "enum": f"{value_type.__module__}.{value_type.__qualname__}",
                "value": canonical(object.__getattribute__(value, "_value_")),
            }
        if value_type is tuple:
            return {"tuple": [canonical(item) for item in value]}
        if value is None or value_type in (str, int, bool):
            return value
        raise ValueError(failure)

    def digest(value: AnnualToCashPosition,
               provenance: AnnualToCashInputProvenance) -> str:
        payload = dumps(
            canonical((value, provenance)), sort_keys=True,
            separators=(",", ":"), ensure_ascii=True,
        ).encode("utf-8")
        return "annual-to-cash-position:sha256-" + sha256(payload).hexdigest()

    def issue(value: AnnualToCashPosition,
              provenance: AnnualToCashInputProvenance) -> AnnualToCashPosition:
        if (
            type(value) is not AnnualToCashPosition
            or type(provenance) is not AnnualToCashInputProvenance
        ):
            raise ValueError(failure)
        expected = digest(value, provenance)
        if not compare(expected, digest(value, provenance)):
            raise ValueError(failure)
        key = id(value)

        def discard(reference: weakref.ReferenceType[AnnualToCashPosition],
                    *, identity: int = key) -> None:
            with lock:
                current = registry.get(identity)
                if current is not None and current[0] is reference:
                    registry.pop(identity, None)

        reference = weakref.ref(value, discard)
        with lock:
            registry[key] = (reference, provenance, expected)
        return value

    def lookup(value: object) -> tuple[AnnualToCashInputProvenance, str]:
        if type(value) is not AnnualToCashPosition:
            raise ValueError(failure)
        with lock:
            entry = registry.get(id(value))
            if entry is None or entry[0]() is not value:
                raise ValueError(failure)
            provenance, expected = entry[1], entry[2]
            try:
                current = digest(value, provenance)
                confirmation = digest(value, provenance)
            except BaseException:
                raise ValueError(failure) from None
            if not compare(current, confirmation) or not compare(current, expected):
                raise ValueError(failure)
            return provenance, expected

    def identity(value: object) -> str:
        return lookup(value)[1]

    def provenance(value: object) -> AnnualToCashInputProvenance:
        return lookup(value)[0]

    def content_reference(value: object, exact_type: type, namespace: str) -> str:
        if type(value) is not exact_type:
            raise ValueError(failure)
        payload = dumps(
            canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")
        return f"{namespace}:sha256-{sha256(payload).hexdigest()}"

    def bind(composer):
        def compose(
            *,
            annual_position: CashReadyAnnualPosition,
            annual_position_reference: str,
            preceding_year_status: poa.PrecedingYearStatus,
            prior_year_evidence: poa.PriorYearEvidence | None,
            prior_year_reference: str | None,
            deductions_credits: poa.BalanceItem,
            deductions_credits_reference: str,
            deductions_credits_evidence_ids: tuple[str, ...],
            prior_poa: poa.BalanceItem,
            prior_poa_reference: str,
            prior_poa_evidence_ids: tuple[str, ...],
            payments_made: Iterable[poa.PaymentMade],
            payment_content_references: tuple[str, ...],
            account_reconciliation: account.AccountReconciliation,
            set_aside_evidence: funding.SetAsideEvidence | None,
            as_of: date,
            stale_after_days: int = 45,
        ) -> AnnualToCashPosition:
            value, provenance = composer(
                annual_position=annual_position,
                annual_position_reference=annual_position_reference,
                preceding_year_status=preceding_year_status,
                prior_year_evidence=prior_year_evidence,
                prior_year_reference=prior_year_reference,
                deductions_credits=deductions_credits,
                deductions_credits_reference=deductions_credits_reference,
                deductions_credits_evidence_ids=deductions_credits_evidence_ids,
                prior_poa=prior_poa,
                prior_poa_reference=prior_poa_reference,
                prior_poa_evidence_ids=prior_poa_evidence_ids,
                payments_made=payments_made,
                payment_content_references=payment_content_references,
                account_reconciliation=account_reconciliation,
                set_aside_evidence=set_aside_evidence,
                as_of=as_of,
                stale_after_days=stale_after_days,
            )
            return issue(value, provenance)

        return compose

    return bind, identity, provenance, content_reference


_bind_annual_to_cash_composer, annual_to_cash_position_identity, \
    annual_to_cash_position_provenance, _secure_content_reference = \
    _make_issuance_capability()


def cash_ready_annual_position_identity(value: CashReadyAnnualPosition) -> str:
    """Return the identity that an independent W1 review must persist."""
    if type(value) is not CashReadyAnnualPosition:
        raise ValueError("annual identity requires an exact CashReadyAnnualPosition")
    return f"cash-ready-annual-position:sha256-{_content_digest(value)}"


def prior_year_evidence_identity(value: poa.PriorYearEvidence) -> str:
    if type(value) is not poa.PriorYearEvidence:
        raise ValueError("prior-year identity requires an exact PriorYearEvidence")
    return f"prior-year-evidence:sha256-{_content_digest(value)}"


def balance_item_identity(
    value: poa.BalanceItem, *, channel: str, evidence_ids: tuple[str, ...]
) -> str:
    if type(value) is not poa.BalanceItem:
        raise ValueError("balance identity requires an exact BalanceItem")
    if channel not in {"deductions-credits", "prior-poa"}:
        raise ValueError("unsupported balance evidence channel")
    bound_ids = _source_ids(evidence_ids, f"{channel}_evidence_ids")
    return f"{channel}:sha256-{_content_digest((value, bound_ids))}"


def payment_made_identity(value: poa.PaymentMade) -> str:
    """Return the exact content identity for a source-identified payment."""
    if type(value) is not poa.PaymentMade:
        raise ValueError("payment identity requires an exact PaymentMade")
    if not isinstance(value.reference, str) or not _SOURCE_ID.fullmatch(value.reference):
        raise ValueError("payment must retain a stable source evidence reference")
    return f"payment:sha256-{_content_digest(value)}"


def _bind(value: object, supplied: str | None, namespace: str, name: str) -> str:
    if not isinstance(supplied, str) or not _DIGEST_REFERENCE.fullmatch(supplied):
        raise ValueError(f"{name} must be a SHA-256 content identity")
    expected = f"{namespace}:sha256-{_content_digest(value)}"
    if not hmac.compare_digest(supplied, expected):
        raise ValueError(f"{name} does not match the exact supplied content")
    return supplied


def _date(value: object, name: str) -> date:
    if isinstance(value, datetime) or type(value) is not date:
        raise ValueError(f"{name} must be a date, not a datetime")
    return value


def _money(value: object) -> bool:
    return (
        isinstance(value, Decimal)
        and not isinstance(value, bool)
        and value.is_finite()
        and value >= ZERO
        and value == value.quantize(PENNY)
    )


def _validate_balance_item(value: poa.BalanceItem, name: str) -> None:
    if (
        type(value) is not poa.BalanceItem
        or not isinstance(value.source, poa.SourceKind)
        or not isinstance(value.completeness, poa.Completeness)
        or (value.amount is not None and not _money(value.amount))
        or (value.retrieval_date is not None and type(value.retrieval_date) is not date)
    ):
        raise ValueError(f"{name} is not a valid exact-penny BalanceItem")
    try:
        reconstructed = poa.BalanceItem(
            value.amount, value.source, value.completeness, value.retrieval_date
        )
    except (ValueError, TypeError, AttributeError, ArithmeticError):
        raise ValueError(f"{name} is not a valid exact-penny BalanceItem") from None
    if reconstructed != value:
        raise ValueError(f"{name} is not a valid exact-penny BalanceItem")


def _validate_prior_year(value: poa.PriorYearEvidence) -> None:
    if (
        type(value) is not poa.PriorYearEvidence
        or not isinstance(value.source, poa.SourceKind)
        or not isinstance(value.completeness, poa.Completeness)
        or not isinstance(value.income_tax_scope, poa.IncomeTaxScope)
        or type(value.effective_date) is not date
        or (value.retrieval_date is not None and type(value.retrieval_date) is not date)
        or (
            value.retrieval_date is not None
            and value.retrieval_date < value.effective_date
        )
    ):
        raise ValueError("prior_year_evidence is invalid")
    monetary = (
        value.income_tax, value.hicbc, value.class_4_nic,
        value.student_loan_repayment, value.class_2_nic,
        value.capital_gains_tax, value.tax_deducted_at_source,
    )
    if any(item is not None and not _money(item) for item in monetary):
        raise ValueError("prior_year_evidence must use exact-penny amounts")
    try:
        reconstructed = poa.PriorYearEvidence(
            tax_year=value.tax_year,
            source=value.source,
            effective_date=value.effective_date,
            retrieval_date=value.retrieval_date,
            completeness=value.completeness,
            income_tax_scope=value.income_tax_scope,
            income_tax=value.income_tax,
            hicbc=value.hicbc,
            class_4_nic=value.class_4_nic,
            student_loan_repayment=value.student_loan_repayment,
            class_2_nic=value.class_2_nic,
            capital_gains_tax=value.capital_gains_tax,
            tax_deducted_at_source=value.tax_deducted_at_source,
            uncertainty=value.uncertainty,
        )
    except (ValueError, TypeError, AttributeError, ArithmeticError):
        raise ValueError("prior_year_evidence is invalid") from None
    if reconstructed != value:
        raise ValueError("prior_year_evidence is invalid")


def _validate_payment(value: poa.PaymentMade) -> None:
    if (
        type(value) is not poa.PaymentMade
        or not isinstance(value.kind, poa.PaymentKind)
        or not isinstance(value.source, poa.SourceKind)
        or not isinstance(value.completeness, poa.Completeness)
        or not _money(value.amount)
        or (value.paid_on is not None and type(value.paid_on) is not date)
        or (value.retrieval_date is not None and type(value.retrieval_date) is not date)
        or (
            value.paid_on is not None
            and value.retrieval_date is not None
            and value.retrieval_date < value.paid_on
        )
        or not isinstance(value.reference, str)
        or not _SOURCE_ID.fullmatch(value.reference)
    ):
        raise ValueError("payment is invalid or not expressed in exact pennies")
    try:
        reconstructed = poa.PaymentMade(
            value.kind, value.amount, value.source, value.paid_on,
            value.retrieval_date, value.completeness, value.reference,
        )
    except (ValueError, TypeError, AttributeError, ArithmeticError):
        raise ValueError("payment is invalid or not expressed in exact pennies") from None
    if reconstructed != value:
        raise ValueError("payment is invalid or not expressed in exact pennies")


def _annual_limitations(value: CashReadyAnnualPosition, *, as_of: date) -> tuple[str, ...]:
    limitations: list[str] = []
    if type(value) is not CashReadyAnnualPosition:
        return ("annual_position_type_invalid",)
    if value.contract_version != ANNUAL_CONTRACT_VERSION:
        limitations.append("annual_position_contract_version_invalid")
    if value.calculation_status != "ready_for_w2_s6" or value.component_set_complete is not True:
        limitations.append("annual_position_not_ready_for_w2_s6")
    if not isinstance(value.limitations, tuple) or value.limitations:
        limitations.append("annual_position_contains_limitations")
    if value.tax_year != "2026/27" or value.ruleset_version != "uk-2026-27-v4":
        limitations.append("annual_position_period_or_ruleset_invalid")
    if type(value.as_of) is not date or value.as_of != ANNUAL_PERIOD_END or value.as_of > as_of:
        limitations.append("annual_position_date_invalid")
    amounts = (
        value.annual_tax_liability,
        value.student_loan_self_assessment_amount,
        value.final_self_assessment_liability,
    )
    if not all(_money(item) for item in amounts):
        limitations.append("annual_position_amount_invalid")
    elif amounts[0] + amounts[1] != amounts[2]:
        limitations.append("annual_position_arithmetic_invalid")
    family_values = (
        value.annual_tax_families,
        value.poa_eligible_families,
        value.poa_excluded_families,
    )
    families_well_formed = all(
        isinstance(items, tuple) and all(type(item) is str for item in items)
        for items in family_values
    )
    if not families_well_formed or (
        not value.annual_tax_families
        or len(value.annual_tax_families) != len(set(value.annual_tax_families))
        or value.poa_eligible_families != value.annual_tax_families
        or not set(value.poa_eligible_families).issubset({"income_tax", "class_4_ni", "hicbc"})
        or set(value.poa_eligible_families) & set(value.poa_excluded_families)
    ):
        limitations.append("annual_position_family_classification_invalid")
    loan_collection_valid = isinstance(value.loan_components, tuple) and all(
            type(item) is CashReadyLoanComponent
            and isinstance(item.component, LoanComponent)
            and _money(item.annual_liability)
            and _money(item.evidenced_deductions)
            and _money(item.remaining_self_assessment_amount)
            and item.remaining_self_assessment_amount
            == max(ZERO, item.annual_liability - item.evidenced_deductions)
            and isinstance(item.selected_evidence_ids, tuple)
            and bool(item.selected_evidence_ids)
            and all(type(identity) is str for identity in item.selected_evidence_ids)
            and len(item.selected_evidence_ids) == len(set(item.selected_evidence_ids))
            for item in value.loan_components
    )
    loan_total = (
        sum((item.remaining_self_assessment_amount for item in value.loan_components), ZERO)
        if loan_collection_valid else None
    )
    if not loan_collection_valid or (
        loan_total != value.student_loan_self_assessment_amount
        or not families_well_formed
        or tuple(item.component.value for item in value.loan_components)
        != value.poa_excluded_families
    ):
        limitations.append("annual_position_loan_components_invalid")
    if (
        not isinstance(value.evidence_ids, tuple)
        or not value.evidence_ids
        or not all(type(item) is str and _SOURCE_ID.fullmatch(item) for item in value.evidence_ids)
        or len(value.evidence_ids) != len(set(value.evidence_ids))
    ):
        limitations.append("annual_position_evidence_identity_reused")
    if not _DIGEST_REFERENCE.fullmatch(value.annual_tax_reference) or not (
        _DIGEST_REFERENCE.fullmatch(value.student_loan_reference)
    ):
        limitations.append("annual_position_upstream_identity_invalid")
    if (
        not isinstance(value.prohibited_uses, tuple)
        or "current_forecast_as_hmrc_poa_basis" not in value.prohibited_uses
    ):
        limitations.append("annual_position_poa_prohibition_missing")
    return tuple(dict.fromkeys(limitations))


def _account_identities(value: account.AccountReconciliation) -> set[str]:
    if not all(
        isinstance(items, tuple)
        for items in (
            value.considered_charges,
            value.considered_credits,
            value.considered_allocations,
        )
    ):
        raise ValueError("account reconciliation evidence collections are invalid")
    if not all(type(item) is account.AccountCharge for item in value.considered_charges):
        raise ValueError("account reconciliation charge evidence is invalid")
    if not all(type(item) is account.AccountCredit for item in value.considered_credits):
        raise ValueError("account reconciliation credit evidence is invalid")
    if not all(
        type(item) is account.ExplicitAllocation for item in value.considered_allocations
    ):
        raise ValueError("account reconciliation allocation evidence is invalid")
    identities: set[str] = set()
    for item in value.considered_charges:
        identities.update((item.charge_id, item.source_reference))
    for item in value.considered_credits:
        identities.update((item.credit_id, item.source_reference))
    for item in value.considered_allocations:
        identities.update((item.allocation_id, item.source_reference))
    return identities


def _source_ids(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, tuple) or not value:
        raise ValueError(f"{name} must be a non-empty immutable tuple")
    if not all(isinstance(item, str) and _SOURCE_ID.fullmatch(item) for item in value):
        raise ValueError(f"{name} contains an invalid source evidence identity")
    if len(value) != len(set(value)):
        raise ValueError(f"{name} contains a duplicate source evidence identity")
    return value


def _unresolved(
    annual_position: CashReadyAnnualPosition,
    annual_reference: str,
    as_of: date,
    limitations: Iterable[str],
) -> AnnualToCashPosition:
    return AnnualToCashPosition(
        contract_version=CONTRACT_VERSION,
        status=AnnualToCashStatus.UNRESOLVED,
        tax_year=annual_position.tax_year,
        ruleset_version=annual_position.ruleset_version,
        as_of=as_of,
        annual_position_reference=annual_reference,
        considered_annual_position=annual_position,
        poa_assessment=None,
        balancing_position=None,
        obligation_reconciliation=None,
        funding_position=None,
        final_self_assessment_liability=None,
        limitations=tuple(dict.fromkeys((*limitations, "no_cash_point_result"))),
        prohibited_uses=_PROHIBITED_USES,
    )


def _unresolved_with_provenance(
    annual_position: CashReadyAnnualPosition,
    annual_reference: str,
    as_of: date,
    limitations: Iterable[str],
    provenance: AnnualToCashInputProvenance,
) -> tuple[AnnualToCashPosition, AnnualToCashInputProvenance]:
    return _unresolved(annual_position, annual_reference, as_of, limitations), provenance


def _compose_annual_to_cash_position(
    *,
    annual_position: CashReadyAnnualPosition,
    annual_position_reference: str,
    preceding_year_status: poa.PrecedingYearStatus,
    prior_year_evidence: poa.PriorYearEvidence | None,
    prior_year_reference: str | None,
    deductions_credits: poa.BalanceItem,
    deductions_credits_reference: str,
    deductions_credits_evidence_ids: tuple[str, ...],
    prior_poa: poa.BalanceItem,
    prior_poa_reference: str,
    prior_poa_evidence_ids: tuple[str, ...],
    payments_made: Iterable[poa.PaymentMade],
    payment_content_references: tuple[str, ...],
    account_reconciliation: account.AccountReconciliation,
    set_aside_evidence: funding.SetAsideEvidence | None,
    as_of: date,
    stale_after_days: int = 45,
) -> tuple[AnnualToCashPosition, AnnualToCashInputProvenance]:
    """Compose the final internal W1-to-W2 result from exact evidence channels."""
    as_of = _date(as_of, "as_of")
    if isinstance(stale_after_days, bool) or not isinstance(stale_after_days, int):
        raise ValueError("stale_after_days must be an integer")
    if stale_after_days < 0:
        raise ValueError("stale_after_days must be non-negative")
    if type(annual_position) is not CashReadyAnnualPosition:
        raise ValueError("annual_position must be an exact CashReadyAnnualPosition")
    annual_reference = _bind(
        annual_position,
        annual_position_reference,
        "cash-ready-annual-position",
        "annual_position_reference",
    )
    _validate_balance_item(deductions_credits, "deductions_credits")
    _validate_balance_item(prior_poa, "prior_poa")
    deductions_source_ids = _source_ids(
        deductions_credits_evidence_ids, "deductions_credits_evidence_ids"
    )
    prior_poa_source_ids = _source_ids(
        prior_poa_evidence_ids, "prior_poa_evidence_ids"
    )
    deductions_ref = _bind(
        (deductions_credits, deductions_source_ids), deductions_credits_reference,
        "deductions-credits", "deductions_credits_reference",
    )
    prior_poa_ref = _bind(
        (prior_poa, prior_poa_source_ids), prior_poa_reference,
        "prior-poa", "prior_poa_reference"
    )
    if not isinstance(preceding_year_status, poa.PrecedingYearStatus):
        raise ValueError("preceding_year_status must be a PrecedingYearStatus")
    first_year_conflict = (
        preceding_year_status is poa.PrecedingYearStatus.FIRST_YEAR
        and (prior_year_evidence is not None or prior_year_reference is not None)
    )
    if preceding_year_status is poa.PrecedingYearStatus.FIRST_YEAR and not first_year_conflict:
        prior_year_ref = None
    elif prior_year_evidence is None:
        if prior_year_reference is not None:
            raise ValueError("prior_year_reference cannot exist without evidence")
        prior_year_ref = None
    else:
        _validate_prior_year(prior_year_evidence)
        prior_year_ref = _bind(
            prior_year_evidence, prior_year_reference, "prior-year-evidence",
            "prior_year_reference",
        )

    payments = tuple(payments_made)
    if not all(type(item) is poa.PaymentMade for item in payments):
        raise ValueError("payments_made must contain exact PaymentMade values")
    if not isinstance(payment_content_references, tuple) or (
        len(payment_content_references) != len(payments)
    ):
        raise ValueError("payment_content_references must exactly parallel payments_made")
    payment_refs: list[str] = []
    payment_source_ids: list[str] = []
    for item, supplied_reference in zip(payments, payment_content_references):
        _validate_payment(item)
        payment_source_ids.append(item.reference)
        payment_refs.append(
            _bind(item, supplied_reference, "payment", "payment content reference")
        )

    refs = [annual_reference, deductions_ref, prior_poa_ref, *payment_refs]
    if prior_year_ref is not None:
        refs.append(prior_year_ref)
    duplicate_content_reference = len(refs) != len(set(refs))
    if type(account_reconciliation) is not account.AccountReconciliation:
        raise ValueError("account_reconciliation must be an AccountReconciliation")
    account_date_mismatch = account_reconciliation.as_of != as_of
    source_ids = [
        *annual_position.evidence_ids,
        *deductions_source_ids,
        *prior_poa_source_ids,
        *payment_source_ids,
    ]
    duplicate_source_id = len(source_ids) != len(set(source_ids))
    account_ids = _account_identities(account_reconciliation)
    account_source_reuse = bool(set(source_ids) & account_ids)
    if set_aside_evidence is not None and type(set_aside_evidence) is not funding.SetAsideEvidence:
        raise ValueError("set_aside_evidence must be an exact SetAsideEvidence or None")
    if set_aside_evidence is not None and (
        not isinstance(set_aside_evidence.allocations, tuple)
        or not all(
            type(item) is funding.SetAsideAllocation
            for item in set_aside_evidence.allocations
        )
    ):
        raise ValueError("set_aside_evidence contains invalid allocations")
    set_aside_source_reuse = set_aside_evidence is not None and bool(set(source_ids) & {
        set_aside_evidence.evidence_id, set_aside_evidence.source_reference,
        *(item.allocation_id for item in set_aside_evidence.allocations),
    })

    provenance = AnnualToCashInputProvenance(
        annual_position_reference=annual_reference,
        preceding_year_status=preceding_year_status,
        prior_year_reference=prior_year_ref,
        deductions_credits_reference=deductions_ref,
        deductions_credits_evidence_ids=deductions_source_ids,
        prior_poa_reference=prior_poa_ref,
        prior_poa_evidence_ids=prior_poa_source_ids,
        payment_content_references=tuple(payment_refs),
        payment_source_ids=tuple(payment_source_ids),
        account_reconciliation_reference=_secure_content_reference(
            account_reconciliation, account.AccountReconciliation,
            "account-reconciliation",
        ),
        set_aside_evidence_reference=(
            None if set_aside_evidence is None else
            _secure_content_reference(
                set_aside_evidence, funding.SetAsideEvidence, "set-aside-evidence"
            )
        ),
        as_of=as_of,
        stale_after_days=stale_after_days,
    )

    early_limitations = []
    if first_year_conflict:
        early_limitations.append("first_year_conflicts_with_prior_year_evidence")
    if duplicate_content_reference:
        early_limitations.append("evidence_identity_reused_across_cash_channels")
    if account_date_mismatch:
        early_limitations.append("account_reconciliation_as_of_mismatch")
    if duplicate_source_id:
        early_limitations.append("source_evidence_identity_reused_across_cash_channels")
    if account_source_reuse:
        early_limitations.append("evidence_identity_reused_in_account_channel")
    if set_aside_source_reuse:
        early_limitations.append("evidence_identity_reused_in_set_aside_channel")
    if early_limitations:
        return _unresolved_with_provenance(
            annual_position, annual_reference, as_of, early_limitations, provenance
        )

    annual_problems = _annual_limitations(annual_position, as_of=as_of)
    if annual_problems:
        return _unresolved_with_provenance(
            annual_position, annual_reference, as_of, annual_problems, provenance
        )
    if (
        preceding_year_status is poa.PrecedingYearStatus.FIRST_YEAR
        and prior_poa.amount != ZERO
    ):
        return _unresolved_with_provenance(
            annual_position, annual_reference, as_of,
            ("first_year_has_nonzero_prior_poa",), provenance,
        )
    if prior_year_evidence is not None and prior_year_evidence.tax_year != annual_position.tax_year:
        return _unresolved_with_provenance(
            annual_position, annual_reference, as_of,
            ("prior_year_evidence_tax_year_mismatch",), provenance,
        )

    poa_assessment = poa.assess_payments_on_account(
        preceding_year_status=preceding_year_status,
        prior_year=prior_year_evidence,
        as_of=as_of,
        stale_after_days=stale_after_days,
    )
    final_liability = poa.BalanceItem(
        annual_position.final_self_assessment_liability,
        poa.SourceKind.LOCAL_ESTIMATE,
        poa.Completeness.COMPLETE_FOR_PURPOSE,
        as_of,
    )
    balancing = poa.compose_balancing_position(
        tax_year=annual_position.tax_year,
        final_liability=final_liability,
        deductions_credits=deductions_credits,
        prior_poa=prior_poa,
        payments_made=payments,
        as_of=as_of,
        stale_after_days=stale_after_days,
    )
    reconciliation = obligations.reconcile_cash_obligations(
        account_reconciliation=account_reconciliation,
        poa_assessment=poa_assessment,
        balancing_position=balancing,
    )
    funding_position = funding.compose_cash_funding_position(
        obligation_reconciliation=reconciliation,
        set_aside_evidence=set_aside_evidence,
        as_of=as_of,
        stale_after_days=stale_after_days,
    )

    unresolved_poa = poa_assessment.status in {
        poa.PoAStatus.INSUFFICIENT_FACTS,
        poa.PoAStatus.CONFLICT_REQUIRES_REVIEW,
        poa.PoAStatus.STALE_REQUIRES_REVIEW,
    }
    limitations = [
        "annual_liability_is_local_estimate_not_hmrc_issued",
        "cash_channel_identity_uniqueness_depends_on_caller_preserving_source_identity",
        *poa_assessment.limitations,
        *balancing.limitations,
        *reconciliation.limitations,
        *funding_position.limitations,
    ]
    if unresolved_poa or balancing.status is poa.BalanceStatus.UNRESOLVED:
        status = AnnualToCashStatus.UNRESOLVED
    elif reconciliation.status in {
        obligations.CashObligationStatus.DISCREPANCY_REQUIRES_REVIEW,
        obligations.CashObligationStatus.INSUFFICIENT_FACTS,
    }:
        status = AnnualToCashStatus.REVIEW_REQUIRED
    elif funding_position.status is not funding.FundingComputationStatus.CALCULATED:
        status = AnnualToCashStatus.UNRESOLVED
    elif (
        reconciliation.status is obligations.CashObligationStatus.OBSERVATION_NOT_HMRC_CONFIRMED
        or not account_reconciliation.hmrc_confirmed
        or final_liability.source is poa.SourceKind.LOCAL_ESTIMATE
    ):
        status = AnnualToCashStatus.QUALIFIED_LOCAL_RESULT
    else:
        status = AnnualToCashStatus.CALCULATED

    result = AnnualToCashPosition(
        contract_version=CONTRACT_VERSION,
        status=status,
        tax_year=annual_position.tax_year,
        ruleset_version=annual_position.ruleset_version,
        as_of=as_of,
        annual_position_reference=annual_reference,
        considered_annual_position=annual_position,
        poa_assessment=poa_assessment,
        balancing_position=balancing,
        obligation_reconciliation=reconciliation,
        funding_position=funding_position,
        final_self_assessment_liability=(
            annual_position.final_self_assessment_liability
            if status not in {AnnualToCashStatus.UNRESOLVED, AnnualToCashStatus.REVIEW_REQUIRED}
            else None
        ),
        limitations=tuple(dict.fromkeys(limitations)),
        prohibited_uses=_PROHIBITED_USES,
    )
    return result, provenance


compose_annual_to_cash_position = _bind_annual_to_cash_composer(
    _compose_annual_to_cash_position
)
compose_annual_to_cash_position.__name__ = "compose_annual_to_cash_position"
compose_annual_to_cash_position.__qualname__ = "compose_annual_to_cash_position"
compose_annual_to_cash_position.__doc__ = (
    "Compose the final internal W1-to-W2 result from exact evidence channels."
)
del _bind_annual_to_cash_composer
del _compose_annual_to_cash_position
del _make_issuance_capability
