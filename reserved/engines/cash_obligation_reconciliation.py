"""Compare local W2 cash expectations with explicit HMRC account charges.

This pure component does not calculate tax, call HMRC, infer bank activity,
allocate or pay money, advise payment, file, persist, render a UI, calculate
interest or penalties, or define the eventual annual-to-cash integration.
It only compares already-derived PoA/balancing expectations with an already-
reconciled Self Assessment account observation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum

from . import payments_on_account as poa
from . import sa_account_reconciliation as account


CONTRACT_VERSION = "reserved-cash-obligation-reconciliation/1.0"
PENNY = Decimal("0.01")
ZERO = Decimal("0.00")


class CashObligationStatus(str, Enum):
    ALIGNED = "aligned"
    INSUFFICIENT_FACTS = "insufficient_facts"
    OBSERVATION_NOT_HMRC_CONFIRMED = "observation_not_hmrc_confirmed"
    DISCREPANCY_REQUIRES_REVIEW = "discrepancy_requires_review"


class ObligationOrigin(str, Enum):
    PAYMENT_ON_ACCOUNT = "payment_on_account"
    BALANCING_POSITION = "balancing_position"


class DiscrepancyKind(str, Enum):
    MISSING_OBSERVED_CHARGE = "missing_observed_charge"
    EXTRA_OBSERVED_CHARGE = "extra_observed_charge"
    AMBIGUOUS_OBSERVED_CHARGE = "ambiguous_observed_charge"
    WRONG_AMOUNT = "wrong_amount"
    WRONG_DUE_DATE = "wrong_due_date"
    WRONG_TAX_YEAR = "wrong_tax_year"
    WRONG_KIND = "wrong_kind"
    MULTIPLE_FIELDS_MISMATCH = "multiple_fields_mismatch"


@dataclass(frozen=True)
class ExpectedCashObligation:
    obligation_id: str
    origin: ObligationOrigin
    kind: account.ChargeKind
    tax_year: str
    due_date: date
    amount: Decimal
    source: poa.SourceKind | None
    upstream_contract_version: str


@dataclass(frozen=True)
class ObligationMatch:
    expected: ExpectedCashObligation
    observed: account.ChargePosition


@dataclass(frozen=True)
class ObligationDiscrepancy:
    kind: DiscrepancyKind
    expected: ExpectedCashObligation | None
    observed: tuple[account.ChargePosition, ...]
    mismatched_fields: tuple[str, ...]


@dataclass(frozen=True)
class CashObligationReconciliation:
    contract_version: str
    status: CashObligationStatus
    aligned: bool
    expected_obligations: tuple[ExpectedCashObligation, ...]
    matches: tuple[ObligationMatch, ...]
    discrepancies: tuple[ObligationDiscrepancy, ...]
    account_as_of: date | None
    account_hmrc_confirmed: bool
    considered_poa: poa.PoAAssessment | None
    considered_balancing: poa.BalancingPosition | None
    considered_account: account.AccountReconciliation
    limitations: tuple[str, ...]
    prohibited_uses: tuple[str, ...]


_PROHIBITED_USES = (
    "present_local_expectation_as_hmrc_bill",
    "present_as_available_cash",
    "autonomous_payment_or_allocation",
    "payment_advice",
    "self_assessment_filing",
    "interest_or_penalty_calculation",
    "production_account_access",
)


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


def _tax_year(value, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a tax-year string")
    parts = value.split("/")
    if (
        len(parts) != 2
        or len(parts[0]) != 4
        or len(parts[1]) != 2
        or not all(part.isdigit() for part in parts)
        or int(parts[1]) != (int(parts[0]) + 1) % 100
    ):
        raise ValueError(f"{name} must use consecutive YYYY/YY form")
    return value


def _expected_key(item: ExpectedCashObligation):
    return (
        item.due_date,
        item.tax_year,
        item.kind.value,
        item.origin.value,
        item.obligation_id,
        item.amount,
    )


def _observed_key(item: account.ChargePosition):
    return (
        item.due_date,
        item.tax_year,
        item.kind.value,
        item.charge_id,
        item.amount,
        item.source_reference,
    )


def _exact_signature(item):
    return (item.kind, item.tax_year, item.due_date, item.amount)


def _validate_poa(value: poa.PoAAssessment | None):
    if value is None:
        return (), None
    if not isinstance(value, poa.PoAAssessment):
        raise ValueError("poa_assessment must be a PoAAssessment or None")
    if value.contract_version != poa.CONTRACT_VERSION:
        raise ValueError("poa_assessment contract_version is unsupported")
    if not isinstance(value.status, poa.PoAStatus):
        raise ValueError("poa_assessment status is invalid")

    unresolved = {
        poa.PoAStatus.INSUFFICIENT_FACTS,
        poa.PoAStatus.CONFLICT_REQUIRES_REVIEW,
        poa.PoAStatus.STALE_REQUIRES_REVIEW,
    }
    if value.status in unresolved:
        return (), "poa_assessment_unresolved"

    no_poa = {
        poa.PoAStatus.NOT_APPLICABLE,
        poa.PoAStatus.FIRST_YEAR_NO_PRECEDING_RETURN,
    }
    if value.status in no_poa:
        if value.instalments:
            return (), "poa_assessment_inconsistent"
        return (), None

    if value.status is not poa.PoAStatus.APPLICABLE:
        return (), "poa_assessment_inconsistent"
    if value.completeness is not poa.Completeness.COMPLETE_FOR_PURPOSE:
        return (), "poa_assessment_incomplete"
    if not isinstance(value.source, poa.SourceKind):
        return (), "poa_assessment_inconsistent"
    tax_year = _tax_year(value.poa_tax_year, "poa_tax_year")
    if len(value.instalments) != 2:
        return (), "poa_assessment_inconsistent"

    labels = {
        "payment_on_account_1": account.ChargeKind.PAYMENT_ON_ACCOUNT_1,
        "payment_on_account_2": account.ChargeKind.PAYMENT_ON_ACCOUNT_2,
    }
    obligations = []
    seen = set()
    for instalment in value.instalments:
        if not isinstance(instalment, poa.Instalment) or instalment.label not in labels:
            return (), "poa_assessment_inconsistent"
        if instalment.label in seen:
            return (), "poa_assessment_inconsistent"
        seen.add(instalment.label)
        due_date = _date(instalment.due_date, "instalment due_date")
        amount = _money(instalment.amount, "instalment amount")
        if amount == ZERO:
            return (), "poa_assessment_inconsistent"
        obligations.append(ExpectedCashObligation(
            obligation_id=f"poa:{tax_year}:{instalment.label}",
            origin=ObligationOrigin.PAYMENT_ON_ACCOUNT,
            kind=labels[instalment.label],
            tax_year=tax_year,
            due_date=due_date,
            amount=amount,
            source=value.source,
            upstream_contract_version=value.contract_version,
        ))
    if seen != set(labels):
        return (), "poa_assessment_inconsistent"
    return tuple(sorted(obligations, key=_expected_key)), None


def _validate_balancing(value: poa.BalancingPosition | None):
    if value is None:
        return (), None
    if not isinstance(value, poa.BalancingPosition):
        raise ValueError("balancing_position must be a BalancingPosition or None")
    if value.contract_version != poa.CONTRACT_VERSION:
        raise ValueError("balancing_position contract_version is unsupported")
    if not isinstance(value.status, poa.BalanceStatus):
        raise ValueError("balancing_position status is invalid")
    tax_year = _tax_year(value.tax_year, "balancing tax_year")

    if value.status is poa.BalanceStatus.UNRESOLVED:
        return (), "balancing_position_unresolved"
    if value.status is poa.BalanceStatus.EXCESS_CREDIT:
        if value.remaining_balance is not None or value.excess_credit is None:
            return (), "balancing_position_inconsistent"
        _money(value.excess_credit, "excess_credit")
        return (), None
    if value.status is not poa.BalanceStatus.REMAINING_BALANCE:
        return (), "balancing_position_inconsistent"
    if value.remaining_balance is None or value.excess_credit is not None:
        return (), "balancing_position_inconsistent"
    if not isinstance(value.source, poa.SourceKind):
        return (), "balancing_position_inconsistent"
    amount = _money(value.remaining_balance, "remaining_balance")
    if amount == ZERO:
        return (), None
    due_date = _date(value.due_date, "balancing due_date")
    return (ExpectedCashObligation(
        obligation_id=f"balance:{tax_year}:balancing_payment",
        origin=ObligationOrigin.BALANCING_POSITION,
        kind=account.ChargeKind.BALANCING_PAYMENT,
        tax_year=tax_year,
        due_date=due_date,
        amount=amount,
        source=value.source,
        upstream_contract_version=value.contract_version,
    ),), None


def _validate_account(value: account.AccountReconciliation):
    if not isinstance(value, account.AccountReconciliation):
        raise ValueError("account_reconciliation must be an AccountReconciliation")
    if value.contract_version != account.CONTRACT_VERSION:
        raise ValueError("account_reconciliation contract_version is unsupported")
    if not isinstance(value.status, account.ReconciliationStatus):
        raise ValueError("account_reconciliation status is invalid")
    _date(value.as_of, "account as_of")
    if not isinstance(value.hmrc_confirmed, bool):
        raise ValueError("account hmrc_confirmed must be boolean")
    if not isinstance(value.charge_positions, tuple):
        raise ValueError("account charge_positions must be an immutable tuple")
    identities = []
    for item in value.charge_positions:
        if not isinstance(item, account.ChargePosition):
            raise ValueError("account charge_positions contain an invalid item")
        identities.append(item.charge_id)
        if not isinstance(item.kind, account.ChargeKind):
            return "account_reconciliation_inconsistent"
        _tax_year(item.tax_year, "observed charge tax_year")
        _date(item.due_date, "observed charge due_date")
        amount = _money(item.amount, "observed charge amount")
        allocated = _money(item.allocated, "observed charge allocated")
        remaining = _money(item.remaining, "observed charge remaining")
        if allocated + remaining != amount:
            return "account_reconciliation_inconsistent"
        if not isinstance(item.source, account.EvidenceSource):
            return "account_reconciliation_inconsistent"
        if not isinstance(item.completeness, account.Completeness):
            return "account_reconciliation_inconsistent"
    if len(set(identities)) != len(identities):
        return "account_reconciliation_inconsistent"
    if value.status is account.ReconciliationStatus.RECONCILED:
        if any(
            item.completeness is not account.Completeness.COMPLETE_FOR_PURPOSE
            for item in value.charge_positions
        ):
            return "account_reconciliation_inconsistent"
        if value.total_charges is None:
            return "account_reconciliation_inconsistent"
        if not all(isinstance(items, tuple) for items in (
            value.considered_charges,
            value.considered_credits,
            value.considered_allocations,
        )):
            return "account_reconciliation_inconsistent"
        if not all(
            isinstance(item, account.AccountCharge)
            for item in value.considered_charges
        ):
            return "account_reconciliation_inconsistent"
        if not all(
            isinstance(item, account.AccountCredit)
            for item in value.considered_credits
        ):
            return "account_reconciliation_inconsistent"
        if not all(
            isinstance(item, account.ExplicitAllocation)
            for item in value.considered_allocations
        ):
            return "account_reconciliation_inconsistent"
        by_id = {item.charge_id: item for item in value.considered_charges}
        if len(by_id) != len(value.considered_charges):
            return "account_reconciliation_inconsistent"
        if set(by_id) != set(identities):
            return "account_reconciliation_inconsistent"
        for position in value.charge_positions:
            evidence = by_id[position.charge_id]
            if (
                position.kind is not evidence.kind
                or position.tax_year != evidence.tax_year
                or position.due_date != evidence.due_date
                or position.amount != evidence.amount
                or position.source is not evidence.source
                or position.effective_date != evidence.effective_date
                or position.observed_on != evidence.observed_on
                or position.completeness is not evidence.completeness
                or position.source_reference != evidence.source_reference
            ):
                return "account_reconciliation_inconsistent"
        if sum((item.amount for item in value.charge_positions), ZERO) != value.total_charges:
            return "account_reconciliation_inconsistent"
        try:
            recomputed = account.reconcile_sa_account(
                value.considered_charges,
                value.considered_credits,
                value.considered_allocations,
                as_of=value.as_of,
                coverage=account.Completeness.COMPLETE_FOR_PURPOSE,
            )
        except (ValueError, TypeError, AttributeError, ArithmeticError):
            return "account_reconciliation_inconsistent"
        if recomputed != value:
            return "account_reconciliation_inconsistent"
    if value.hmrc_confirmed and any(
        item.source not in {
            account.EvidenceSource.HMRC_ONLINE,
            account.EvidenceSource.HMRC_DOCUMENT,
        }
        for item in value.charge_positions
    ):
        return "account_reconciliation_inconsistent"
    if value.hmrc_confirmed and any(
        item.source not in {
            account.EvidenceSource.HMRC_ONLINE,
            account.EvidenceSource.HMRC_DOCUMENT,
        }
        for item in (
            value.considered_charges
            + value.considered_credits
            + value.considered_allocations
        )
    ):
        return "account_reconciliation_inconsistent"
    return None


def _result(
    *,
    status: CashObligationStatus,
    expected,
    matches,
    discrepancies,
    poa_assessment,
    balancing_position,
    account_reconciliation,
    limitations,
):
    return CashObligationReconciliation(
        contract_version=CONTRACT_VERSION,
        status=status,
        aligned=status is CashObligationStatus.ALIGNED,
        expected_obligations=tuple(sorted(expected, key=_expected_key)),
        matches=tuple(sorted(matches, key=lambda item: _expected_key(item.expected))),
        discrepancies=tuple(discrepancies),
        account_as_of=account_reconciliation.as_of,
        account_hmrc_confirmed=account_reconciliation.hmrc_confirmed,
        considered_poa=poa_assessment,
        considered_balancing=balancing_position,
        considered_account=account_reconciliation,
        limitations=tuple(dict.fromkeys(limitations)),
        prohibited_uses=_PROHIBITED_USES,
    )


def reconcile_cash_obligations(
    *,
    account_reconciliation: account.AccountReconciliation,
    poa_assessment: poa.PoAAssessment | None = None,
    balancing_position: poa.BalancingPosition | None = None,
) -> CashObligationReconciliation:
    """Compare explicit local obligations to explicit account charges.

    An ``aligned`` result means exact identity-field agreement only. It does not
    convert a local estimate into an HMRC bill or authorise any payment action.
    """
    account_problem = _validate_account(account_reconciliation)
    if account_problem is not None:
        return _result(
            status=CashObligationStatus.INSUFFICIENT_FACTS,
            expected=(), matches=(), discrepancies=(),
            poa_assessment=poa_assessment,
            balancing_position=balancing_position,
            account_reconciliation=account_reconciliation,
            limitations=(account_problem, "no_aligned_point_result"),
        )
    if poa_assessment is None and balancing_position is None:
        return _result(
            status=CashObligationStatus.INSUFFICIENT_FACTS,
            expected=(), matches=(), discrepancies=(),
            poa_assessment=None, balancing_position=None,
            account_reconciliation=account_reconciliation,
            limitations=("no_local_obligation_result_supplied",),
        )

    poa_expected, poa_problem = _validate_poa(poa_assessment)
    balance_expected, balance_problem = _validate_balancing(balancing_position)
    expected = tuple(sorted(poa_expected + balance_expected, key=_expected_key))
    upstream_problems = tuple(
        problem for problem in (poa_problem, balance_problem) if problem is not None
    )
    if upstream_problems:
        return _result(
            status=CashObligationStatus.INSUFFICIENT_FACTS,
            expected=(), matches=(), discrepancies=(),
            poa_assessment=poa_assessment,
            balancing_position=balancing_position,
            account_reconciliation=account_reconciliation,
            limitations=upstream_problems + ("no_aligned_point_result",),
        )

    if account_reconciliation.status is not account.ReconciliationStatus.RECONCILED:
        return _result(
            status=CashObligationStatus.INSUFFICIENT_FACTS,
            expected=expected, matches=(), discrepancies=(),
            poa_assessment=poa_assessment,
            balancing_position=balancing_position,
            account_reconciliation=account_reconciliation,
            limitations=("account_reconciliation_unresolved", "no_aligned_point_result"),
        )
    if not account_reconciliation.hmrc_confirmed:
        return _result(
            status=CashObligationStatus.OBSERVATION_NOT_HMRC_CONFIRMED,
            expected=expected, matches=(), discrepancies=(),
            poa_assessment=poa_assessment,
            balancing_position=balancing_position,
            account_reconciliation=account_reconciliation,
            limitations=("account_observation_not_hmrc_confirmed", "no_aligned_point_result"),
        )

    observed = tuple(sorted(account_reconciliation.charge_positions, key=_observed_key))
    matches = []
    discrepancies = []
    consumed = set()

    for expected_item in expected:
        available = tuple(
            item for item in observed if item.charge_id not in consumed
        )
        exact = [
            item for item in available
            if _exact_signature(item) == _exact_signature(expected_item)
        ]
        if len(exact) == 1:
            match = exact[0]
            matches.append(ObligationMatch(expected_item, match))
            consumed.add(match.charge_id)
            continue
        if len(exact) > 1:
            candidates = tuple(sorted(exact, key=_observed_key))
            consumed.update(item.charge_id for item in candidates)
            discrepancies.append(ObligationDiscrepancy(
                DiscrepancyKind.AMBIGUOUS_OBSERVED_CHARGE,
                expected_item,
                candidates,
                (),
            ))
            continue

        same_kind = tuple(sorted(
            (item for item in available if item.kind is expected_item.kind),
            key=_observed_key,
        ))
        if not same_kind:
            wrong_kind = tuple(sorted(
                (
                    item for item in available
                    if item.tax_year == expected_item.tax_year
                    and item.due_date == expected_item.due_date
                    and item.amount == expected_item.amount
                ),
                key=_observed_key,
            ))
            if len(wrong_kind) == 1:
                candidate = wrong_kind[0]
                consumed.add(candidate.charge_id)
                discrepancies.append(ObligationDiscrepancy(
                    DiscrepancyKind.WRONG_KIND,
                    expected_item,
                    (candidate,),
                    ("kind",),
                ))
                continue
            if len(wrong_kind) > 1:
                consumed.update(item.charge_id for item in wrong_kind)
                discrepancies.append(ObligationDiscrepancy(
                    DiscrepancyKind.AMBIGUOUS_OBSERVED_CHARGE,
                    expected_item,
                    wrong_kind,
                    ("kind",),
                ))
                continue
            discrepancies.append(ObligationDiscrepancy(
                DiscrepancyKind.MISSING_OBSERVED_CHARGE,
                expected_item,
                (),
                (),
            ))
            continue
        if len(same_kind) > 1:
            consumed.update(item.charge_id for item in same_kind)
            discrepancies.append(ObligationDiscrepancy(
                DiscrepancyKind.AMBIGUOUS_OBSERVED_CHARGE,
                expected_item,
                same_kind,
                (),
            ))
            continue

        candidate = same_kind[0]
        consumed.add(candidate.charge_id)
        fields = []
        if candidate.tax_year != expected_item.tax_year:
            fields.append("tax_year")
        if candidate.due_date != expected_item.due_date:
            fields.append("due_date")
        if candidate.amount != expected_item.amount:
            fields.append("amount")
        kind = {
            ("amount",): DiscrepancyKind.WRONG_AMOUNT,
            ("due_date",): DiscrepancyKind.WRONG_DUE_DATE,
            ("tax_year",): DiscrepancyKind.WRONG_TAX_YEAR,
        }.get(tuple(fields), DiscrepancyKind.MULTIPLE_FIELDS_MISMATCH)
        discrepancies.append(ObligationDiscrepancy(
            kind,
            expected_item,
            (candidate,),
            tuple(fields),
        ))

    for item in observed:
        if item.charge_id not in consumed:
            discrepancies.append(ObligationDiscrepancy(
                DiscrepancyKind.EXTRA_OBSERVED_CHARGE,
                None,
                (item,),
                (),
            ))

    discrepancies = tuple(sorted(
        discrepancies,
        key=lambda item: (
            item.kind.value,
            _expected_key(item.expected) if item.expected else (
                date.min, "", "", "", "", ZERO,
            ),
            tuple(_observed_key(value) for value in item.observed),
            item.mismatched_fields,
        ),
    ))
    limitations = ["comparison_only_no_payment_action"]
    if any(item.source is poa.SourceKind.LOCAL_ESTIMATE for item in expected):
        limitations.append("local_expectation_not_hmrc_issued")

    return _result(
        status=(
            CashObligationStatus.DISCREPANCY_REQUIRES_REVIEW
            if discrepancies else CashObligationStatus.ALIGNED
        ),
        expected=expected,
        matches=matches,
        discrepancies=discrepancies,
        poa_assessment=poa_assessment,
        balancing_position=balancing_position,
        account_reconciliation=account_reconciliation,
        limitations=limitations,
    )
