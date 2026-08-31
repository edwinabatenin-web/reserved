"""Pure, fail-closed Payments on Account component.

This module calculates whether UK Self Assessment Payments on Account (PoA)
apply, derives the two prior-year-based instalments, and composes a separate
balancing position. It is driven only by explicit inputs and never calls HMRC,
reads a database or renders a customer surface.

Statutory basis
---------------
Payments on Account are governed by TMA 1970 s.59A (as amended). For a person
who had a preceding-year Self Assessment liability:

* the **fixed-amount test** — the statutory relevant amount is not less than
  £1,000 (TMA 1970 s59A(1)(c)); and
* the **tax-deducted-at-source test** — less than 80% of the assessed Income
  Tax / Class 4 basis was collected at source (PAYE, tax deducted from
  interest, etc.).

The statutory relevant amount is the assessed basis **after** tax deducted at
source has been subtracted once. When both tests are met, two equal payments on
account are due for the following year, each equal to 50% of that relevant
amount. The first instalment falls due on 31 January and the second on 31 July
of the applicable cycle. An odd penny is loaded onto the second instalment.

Amount families that enter the PoA basis (the assessed Income Tax / Class 4
basis):

* Income Tax,
* High Income Child Benefit Charge (ITEPA 2003 Part 10 — collected as income
  tax through Self Assessment), and
* Class 4 National Insurance contributions (SSCBA 1992 s.15).

Student Loan and Postgraduate Loan repayments collected through Self Assessment
are **excluded** from Payments on Account (HMRC SALF303 and SAM1010). They are
kept explicit and may enter the later balancing position only through explicit
final-liability composition.

HICBC is an Income Tax charge and is included exactly once. The input contract
declares the scope of ``income_tax`` via ``IncomeTaxScope``:

* ``EXCLUDES_HICBC`` (default) — ``income_tax`` excludes separately-stated
  HICBC, so ``hicbc`` is supplied separately and added once; and
* ``INCLUDES_HICBC`` — ``income_tax`` already includes HICBC, so a separate
  non-zero ``hicbc`` is a double count and fails closed as conflicting.

Amount families that do **not** enter the PoA basis and therefore remain
explicit (never silently folded or double-counted):

* Class 2 National Insurance contributions,
* Capital Gains Tax (TCGA 1992 — CGT is excluded from Payments on Account), and
* Student Loan / Postgraduate Loan repayments (SALF303 / SAM1010).

Failure model
-------------
There are two distinct failure modes, matching the rest of the engine:

1. Malformed input (booleans, non-finite or negative money, malformed tax
   years, ``datetime`` where a calendar ``date`` is required, effective dates
   outside the stated tax year, future retrieval/payment dates, invalid enum
   values) raises ``ValueError``.
2. Genuinely missing, stale, conflicting or incomplete evidence is returned as
   a fail-closed result with no manufactured point estimate: the relevant
   amount and instalments are ``None``/empty and the status is one of
   ``insufficient_facts``, ``stale_requires_review`` or
   ``conflict_requires_review``.

This module deliberately does not couple to ``AnnualPositionResult``,
``InternalAnnualComposition``, ``PayeReconciliation`` or ``internal_snapshot``.
The annual-to-cash contract remains later work.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_DOWN, ROUND_HALF_UP
from enum import Enum
import re
from typing import Iterable

CONTRACT_VERSION = "reserved-payments-on-account/1.0"

FIXED_AMOUNT_THRESHOLD = Decimal("1000")
SOURCE_DEDUCTION_THRESHOLD = Decimal("0.80")
PENNY = Decimal("0.01")
ZERO = Decimal("0")

_UNCERTAINTY_REASONS = frozenset({"missing", "stale", "conflicting", "incomplete"})
_TAX_YEAR = re.compile(r"^(\d{4})/(\d{2})$")


class SourceKind(str, Enum):
    """Provenance of an amount: HMRC-issued versus a qualified local estimate."""

    HMRC_ISSUED = "hmrc_issued"
    LOCAL_ESTIMATE = "local_estimate"


class Completeness(str, Enum):
    COMPLETE_FOR_PURPOSE = "complete_for_purpose"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


class IncomeTaxScope(str, Enum):
    """Declared scope of ``income_tax`` with respect to separately-stated HICBC."""

    EXCLUDES_HICBC = "excludes_hicbc"
    INCLUDES_HICBC = "includes_hicbc"


class PrecedingYearStatus(str, Enum):
    """Whether a prior-year Self Assessment return exists."""

    ESTABLISHED = "established"
    FIRST_YEAR = "first_year"


class PoAStatus(str, Enum):
    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"
    FIRST_YEAR_NO_PRECEDING_RETURN = "first_year_no_preceding_return"
    INSUFFICIENT_FACTS = "insufficient_facts"
    CONFLICT_REQUIRES_REVIEW = "conflict_requires_review"
    STALE_REQUIRES_REVIEW = "stale_requires_review"


class BalanceStatus(str, Enum):
    REMAINING_BALANCE = "remaining_balance"
    EXCESS_CREDIT = "excess_credit"
    UNRESOLVED = "unresolved"


class PaymentKind(str, Enum):
    PAYMENT_ON_ACCOUNT = "payment_on_account"
    BALANCING_PAYMENT = "balancing_payment"
    OTHER_PAYMENT = "other_payment"
    HMRC_CREDIT = "hmrc_credit"


# ── Validation helpers ────────────────────────────────────────────────────────

def _coerce_enum(value, enum_cls, name):
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            raise ValueError(
                f"{name} {value!r} is not a valid {enum_cls.__name__}"
            ) from None
    raise ValueError(f"{name} must be a {enum_cls.__name__}")


def _coerce_optional_money(value, name) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{name} must be monetary, not boolean")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{name} must be numeric") from None
    if not parsed.is_finite():
        raise ValueError(f"{name} must be finite")
    if parsed < ZERO:
        raise ValueError(f"{name} must be non-negative")
    return parsed


def _coerce_money(value, name) -> Decimal:
    parsed = _coerce_optional_money(value, name)
    if parsed is None:
        raise ValueError(f"{name} must be a non-negative amount")
    return parsed


def _coerce_date(value, name) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        raise ValueError(f"{name} must be a date, not a datetime")
    if not isinstance(value, date):
        raise ValueError(f"{name} must be a date")
    return value


def _parse_tax_year_start(tax_year: str) -> int:
    """Validate the ``YYYY/YY+1`` form and return the start calendar year."""
    if not isinstance(tax_year, str):
        raise ValueError("tax_year must be a string")
    match = _TAX_YEAR.fullmatch(tax_year)
    if not match:
        raise ValueError(f"tax_year {tax_year!r} must use the 'YYYY/YY+1' form")
    start = int(match.group(1))
    end = int(match.group(2))
    if end != (start + 1) % 100:
        raise ValueError(f"tax_year {tax_year!r} must name two consecutive years")
    return start


def _tax_year_bounds(start_year: int) -> tuple[date, date]:
    """Return the (inclusive) calendar bounds of a tax year: 6 April → 5 April."""
    return date(start_year, 4, 6), date(start_year + 1, 4, 5)


def _poa_due_dates(prior_tax_year: str) -> tuple[str, date, date]:
    """Return ``(poa_tax_year, first_due, second_due)`` for a prior-year basis.

    For prior tax year ``YYYY/YY+1`` the following-year cycle is
    ``YYYY+1/YY+2``, whose first instalment falls due 31 January ``YYYY+2`` and
    second instalment 31 July ``YYYY+2``.
    """
    start = _parse_tax_year_start(prior_tax_year)
    poa_tax_year = f"{start + 1}/{(start + 2) % 100:02d}"
    first_due = date(start + 2, 1, 31)
    second_due = date(start + 2, 7, 31)
    return poa_tax_year, first_due, second_due


def _round_penny(value: Decimal) -> Decimal:
    return value.quantize(PENNY, rounding=ROUND_HALF_UP)


def _floor_penny(value: Decimal) -> Decimal:
    """Round down (truncate toward zero) to the nearest penny.

    Used for the first PoA instalment so that any odd penny is loaded onto the
    second instalment (HMRC SAM1010).
    """
    return value.quantize(PENNY, rounding=ROUND_DOWN)


def _is_stale(retrieval_date: date | None, as_of: date, stale_after_days: int) -> bool:
    if retrieval_date is None:
        return True
    return (as_of - retrieval_date).days > stale_after_days


# ── Input types ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PriorYearEvidence:
    """Explicit prior-year Self Assessment components with provenance.

    The PoA basis requires ``income_tax``, ``class_4_nic`` and (for the default
    ``EXCLUDES_HICBC`` scope) ``hicbc``; ``tax_deducted_at_source`` is also
    required for the two statutory tests. Student Loan/PGL repayments, Class 2
    NIC and CGT are explicit exclusions and never enter the basis.
    """

    tax_year: str
    source: SourceKind
    effective_date: date
    retrieval_date: date | None
    completeness: Completeness
    income_tax_scope: IncomeTaxScope = IncomeTaxScope.EXCLUDES_HICBC
    income_tax: Decimal | None = None
    hicbc: Decimal | None = None
    class_4_nic: Decimal | None = None
    student_loan_repayment: Decimal | None = None
    class_2_nic: Decimal | None = None
    capital_gains_tax: Decimal | None = None
    tax_deducted_at_source: Decimal | None = None
    uncertainty: tuple[str, ...] = ()

    def __post_init__(self):
        _parse_tax_year_start(self.tax_year)
        object.__setattr__(self, "source", _coerce_enum(self.source, SourceKind, "source"))
        object.__setattr__(
            self, "completeness",
            _coerce_enum(self.completeness, Completeness, "completeness"),
        )
        object.__setattr__(
            self, "income_tax_scope",
            _coerce_enum(self.income_tax_scope, IncomeTaxScope, "income_tax_scope"),
        )
        if not isinstance(self.effective_date, date) or isinstance(
            self.effective_date, datetime
        ):
            raise ValueError("effective_date must be a date, not a datetime")
        start = _parse_tax_year_start(self.tax_year)
        lower, upper = _tax_year_bounds(start)
        if not (lower <= self.effective_date <= upper):
            raise ValueError(
                f"effective_date {self.effective_date.isoformat()} is outside "
                f"tax year {self.tax_year}"
            )
        object.__setattr__(
            self, "retrieval_date", _coerce_date(self.retrieval_date, "retrieval_date"),
        )
        for field in (
            "income_tax", "hicbc", "class_4_nic", "student_loan_repayment",
            "class_2_nic", "capital_gains_tax", "tax_deducted_at_source",
        ):
            object.__setattr__(
                self, field, _coerce_optional_money(getattr(self, field), field),
            )
        for reason in self.uncertainty:
            if reason not in _UNCERTAINTY_REASONS:
                raise ValueError(f"uncertainty reason {reason!r} is not recognised")

    @property
    def poa_basis(self) -> Decimal | None:
        """Gross assessed Income Tax / Class 4 basis, or ``None`` when a required
        family is missing.

        Student Loan/PGL repayments are excluded (SALF303 / SAM1010). HICBC is
        included exactly once: either inside ``income_tax`` (``INCLUDES_HICBC``)
        or supplied separately via ``hicbc`` (``EXCLUDES_HICBC``).
        """
        if self.income_tax is None or self.class_4_nic is None:
            return None
        hicbc_amount = ZERO
        if self.income_tax_scope is IncomeTaxScope.EXCLUDES_HICBC:
            if self.hicbc is None:
                return None
            hicbc_amount = self.hicbc
        return self.income_tax + hicbc_amount + self.class_4_nic


@dataclass(frozen=True)
class BalanceItem:
    """A money amount entering the balancing calculation, with provenance."""

    amount: Decimal | None
    source: SourceKind
    completeness: Completeness = Completeness.COMPLETE_FOR_PURPOSE
    retrieval_date: date | None = None

    def __post_init__(self):
        object.__setattr__(
            self, "amount", _coerce_optional_money(self.amount, "amount"),
        )
        object.__setattr__(self, "source", _coerce_enum(self.source, SourceKind, "source"))
        object.__setattr__(
            self, "completeness",
            _coerce_enum(self.completeness, Completeness, "completeness"),
        )
        object.__setattr__(
            self, "retrieval_date", _coerce_date(self.retrieval_date, "retrieval_date"),
        )


@dataclass(frozen=True)
class PaymentMade:
    """A payment or credit already applied to an account, with provenance."""

    kind: PaymentKind
    amount: Decimal
    source: SourceKind
    paid_on: date | None = None
    retrieval_date: date | None = None
    completeness: Completeness = Completeness.COMPLETE_FOR_PURPOSE
    reference: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "kind", _coerce_enum(self.kind, PaymentKind, "kind"))
        object.__setattr__(self, "amount", _coerce_money(self.amount, "amount"))
        object.__setattr__(self, "source", _coerce_enum(self.source, SourceKind, "source"))
        object.__setattr__(
            self, "completeness",
            _coerce_enum(self.completeness, Completeness, "completeness"),
        )
        object.__setattr__(self, "paid_on", _coerce_date(self.paid_on, "paid_on"))
        object.__setattr__(
            self, "retrieval_date", _coerce_date(self.retrieval_date, "retrieval_date"),
        )
        if self.reference is not None and not isinstance(self.reference, str):
            raise ValueError("reference must be a string or None")


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class FixedAmountTest:
    relevant_amount: Decimal
    threshold: Decimal
    meets_threshold: bool


@dataclass(frozen=True)
class SourceDeductionTest:
    basis: Decimal
    deducted_at_source: Decimal
    ratio: Decimal
    threshold: Decimal
    below_threshold: bool


@dataclass(frozen=True)
class Instalment:
    label: str
    due_date: date
    amount: Decimal


@dataclass(frozen=True)
class ExcludedAmount:
    family: str
    amount: Decimal
    reason: str


@dataclass(frozen=True)
class PoAAssessment:
    contract_version: str
    prior_tax_year: str | None
    poa_tax_year: str | None
    status: PoAStatus
    source: SourceKind | None
    effective_date: date | None
    retrieval_date: date | None
    completeness: Completeness | None
    poa_basis: Decimal | None
    relevant_amount: Decimal | None
    fixed_amount_test: FixedAmountTest | None
    source_deduction_test: SourceDeductionTest | None
    instalments: tuple[Instalment, ...]
    excluded_amounts: tuple[ExcludedAmount, ...]
    limitations: tuple[str, ...]
    prohibited_uses: tuple[str, ...]


@dataclass(frozen=True)
class BalancingPosition:
    contract_version: str
    tax_year: str
    due_date: date | None
    status: BalanceStatus
    source: SourceKind | None
    final_liability: Decimal | None
    deductions_credits: Decimal | None
    prior_poa: Decimal | None
    payments_made_total: Decimal | None
    remaining_balance: Decimal | None
    excess_credit: Decimal | None
    limitations: tuple[str, ...]
    prohibited_uses: tuple[str, ...]
    unresolved_reason: str | None


_POA_PROHIBITED_USES = (
    "present_as_hmrc_confirmed_bill",
    "present_as_available_cash",
    "autonomous_payment",
    "self_assessment_filing",
)

_BALANCE_PROHIBITED_USES = (
    "present_as_available_cash",
    "present_as_hmrc_confirmed_bill",
    "autonomous_payment",
)


# ── Payments on Account assessment ────────────────────────────────────────────

def assess_payments_on_account(
    *,
    preceding_year_status: PrecedingYearStatus,
    prior_year: PriorYearEvidence | None = None,
    as_of: date | None = None,
    stale_after_days: int = 45,
) -> PoAAssessment:
    """Determine PoA applicability and derive the two instalments.

    ``preceding_year_status`` distinguishes a first Self Assessment year (no
    preceding return, hence no prior-year PoA) from an established year.
    ``prior_year`` supplies the explicit prior-year basis for the established
    case; ``None`` (or incomplete/stale/conflicting evidence) fails closed with
    no manufactured point estimate.
    """
    status = _coerce_enum(
        preceding_year_status, PrecedingYearStatus, "preceding_year_status",
    )
    if not isinstance(stale_after_days, int) or isinstance(stale_after_days, bool) \
            or stale_after_days < 0:
        raise ValueError("stale_after_days must be a non-negative integer")
    if as_of is not None and not isinstance(as_of, date):
        raise ValueError("as_of must be a date")

    base_prohibited = _POA_PROHIBITED_USES

    if status is PrecedingYearStatus.FIRST_YEAR:
        return PoAAssessment(
            contract_version=CONTRACT_VERSION,
            prior_tax_year=None,
            poa_tax_year=None,
            status=PoAStatus.FIRST_YEAR_NO_PRECEDING_RETURN,
            source=None,
            effective_date=None,
            retrieval_date=None,
            completeness=None,
            poa_basis=None,
            relevant_amount=None,
            fixed_amount_test=None,
            source_deduction_test=None,
            instalments=(),
            excluded_amounts=(),
            limitations=("no_preceding_return_no_prior_year_derived_instalments",),
            prohibited_uses=base_prohibited,
        )

    if prior_year is None:
        return PoAAssessment(
            contract_version=CONTRACT_VERSION,
            prior_tax_year=None,
            poa_tax_year=None,
            status=PoAStatus.INSUFFICIENT_FACTS,
            source=None,
            effective_date=None,
            retrieval_date=None,
            completeness=None,
            poa_basis=None,
            relevant_amount=None,
            fixed_amount_test=None,
            source_deduction_test=None,
            instalments=(),
            excluded_amounts=(),
            limitations=("missing_prior_year_evidence",),
            prohibited_uses=base_prohibited,
        )

    today = as_of or date.today()
    if prior_year.retrieval_date is not None and prior_year.retrieval_date > today:
        raise ValueError("retrieval_date must not be in the future")

    # Conflicting evidence takes precedence over other fail-closed states.
    if "conflicting" in prior_year.uncertainty:
        return _fail_closed(
            prior_year, PoAStatus.CONFLICT_REQUIRES_REVIEW,
            "conflicting_prior_year_evidence",
        )
    if prior_year.completeness is not Completeness.COMPLETE_FOR_PURPOSE:
        return _fail_closed(
            prior_year, PoAStatus.INSUFFICIENT_FACTS,
            "incomplete_prior_year_evidence",
        )

    # HICBC must be included exactly once: when income_tax already includes it,
    # a separately supplied non-zero HICBC is a double count.
    if (
        prior_year.income_tax_scope is IncomeTaxScope.INCLUDES_HICBC
        and (prior_year.hicbc or ZERO) > ZERO
    ):
        return _fail_closed(
            prior_year, PoAStatus.CONFLICT_REQUIRES_REVIEW,
            "hicbc_supplied_twice",
        )

    basis = prior_year.poa_basis
    if basis is None or prior_year.tax_deducted_at_source is None:
        return _fail_closed(
            prior_year, PoAStatus.INSUFFICIENT_FACTS,
            "missing_prior_year_components",
        )
    if "stale" in prior_year.uncertainty or _is_stale(
        prior_year.retrieval_date, today, stale_after_days,
    ):
        return _fail_closed(
            prior_year, PoAStatus.STALE_REQUIRES_REVIEW, "stale_prior_year_evidence",
        )
    if "missing" in prior_year.uncertainty or "incomplete" in prior_year.uncertainty:
        return _fail_closed(
            prior_year, PoAStatus.INSUFFICIENT_FACTS,
            "flagged_prior_year_uncertainty",
        )

    deducted = prior_year.tax_deducted_at_source
    relevant_amount = basis - deducted
    if relevant_amount < ZERO:
        relevant_amount = ZERO

    meets_threshold = relevant_amount >= FIXED_AMOUNT_THRESHOLD
    ratio = (deducted / basis) if basis > ZERO else ZERO
    below_threshold = ratio < SOURCE_DEDUCTION_THRESHOLD
    applies = meets_threshold and below_threshold

    poa_tax_year, first_due, second_due = _poa_due_dates(prior_year.tax_year)

    instalments: tuple[Instalment, ...] = ()
    limitations: list[str] = []
    if applies:
        half = relevant_amount / Decimal("2")
        first = _floor_penny(half)
        second = relevant_amount - first
        instalments = (
            Instalment("payment_on_account_1", first_due, first),
            Instalment("payment_on_account_2", second_due, second),
        )
        limitations.append("installments_are_prior_year_derived")
    else:
        limitations.append("no_prior_year_derived_instalments_due")

    if prior_year.source is SourceKind.LOCAL_ESTIMATE:
        limitations.append("prior_year_is_local_estimate_not_hmrc_issued")

    excluded_amounts = (
        ExcludedAmount(
            "student_loan_repayment",
            prior_year.student_loan_repayment
            if prior_year.student_loan_repayment is not None else ZERO,
            "not_in_payments_on_account_basis",
        ),
        ExcludedAmount(
            "class_2_nic",
            prior_year.class_2_nic if prior_year.class_2_nic is not None else ZERO,
            "not_in_payments_on_account_basis",
        ),
        ExcludedAmount(
            "capital_gains_tax",
            prior_year.capital_gains_tax
            if prior_year.capital_gains_tax is not None else ZERO,
            "not_in_payments_on_account_basis",
        ),
    )

    return PoAAssessment(
        contract_version=CONTRACT_VERSION,
        prior_tax_year=prior_year.tax_year,
        poa_tax_year=poa_tax_year,
        status=PoAStatus.APPLICABLE if applies else PoAStatus.NOT_APPLICABLE,
        source=prior_year.source,
        effective_date=prior_year.effective_date,
        retrieval_date=prior_year.retrieval_date,
        completeness=prior_year.completeness,
        poa_basis=basis,
        relevant_amount=relevant_amount,
        fixed_amount_test=FixedAmountTest(
            relevant_amount, FIXED_AMOUNT_THRESHOLD, meets_threshold,
        ),
        source_deduction_test=SourceDeductionTest(
            basis, deducted, ratio, SOURCE_DEDUCTION_THRESHOLD, below_threshold,
        ),
        instalments=instalments,
        excluded_amounts=excluded_amounts,
        limitations=tuple(limitations),
        prohibited_uses=base_prohibited,
    )


def _fail_closed(
    prior_year: PriorYearEvidence, status: PoAStatus, limitation: str,
) -> PoAAssessment:
    return PoAAssessment(
        contract_version=CONTRACT_VERSION,
        prior_tax_year=prior_year.tax_year,
        poa_tax_year=None,
        status=status,
        source=prior_year.source,
        effective_date=prior_year.effective_date,
        retrieval_date=prior_year.retrieval_date,
        completeness=prior_year.completeness,
        poa_basis=None,
        relevant_amount=None,
        fixed_amount_test=None,
        source_deduction_test=None,
        instalments=(),
        excluded_amounts=(),
        limitations=(limitation, "no_prior_year_derived_instalments_due"),
        prohibited_uses=_POA_PROHIBITED_USES,
    )


# ── Balancing position composition ────────────────────────────────────────────

def compose_balancing_position(
    *,
    tax_year: str,
    final_liability: BalanceItem,
    deductions_credits: BalanceItem,
    prior_poa: BalanceItem,
    payments_made: Iterable[PaymentMade] = (),
    as_of: date | None = None,
    stale_after_days: int = 45,
    conflict_tolerance=Decimal("1.00"),
) -> BalancingPosition:
    """Compose a balancing position from final liability and credits/payments.

    The balancing position is kept separate from the PoA instalments. It
    composes the final liability, deductions/credits (tax deducted at source and
    HMRC-recorded credits), prior payments on account and other payments already
    made into one of:

    * ``remaining_balance``  — a positive amount still to be funded;
    * ``excess_credit``      — an overpayment / refund candidate; or
    * ``unresolved``         — evidence is missing, stale, conflicting or
                               incomplete, so no number may escape.

    ``prior_poa`` is the single, aggregate prior-PoA credit channel. PoA-kind
    entries must therefore not also be passed through ``payments_made``; doing
    so is a double count and fails closed.

    Neither outcome is labelled available cash or an HMRC-confirmed bill.
    """
    start = _parse_tax_year_start(tax_year)
    if not isinstance(stale_after_days, int) or isinstance(stale_after_days, bool) \
            or stale_after_days < 0:
        raise ValueError("stale_after_days must be a non-negative integer")
    if as_of is not None and not isinstance(as_of, date):
        raise ValueError("as_of must be a date")
    tolerance = _coerce_optional_money(conflict_tolerance, "conflict_tolerance")
    if tolerance is None:
        raise ValueError("conflict_tolerance must be a non-negative amount")

    today = as_of or date.today()
    due_date = date(start + 2, 1, 31)

    items = (final_liability, deductions_credits, prior_poa)
    for name, item in zip(
        ("final_liability", "deductions_credits", "prior_poa"), items,
    ):
        if item.retrieval_date is not None and item.retrieval_date > today:
            raise ValueError(f"{name} retrieval_date must not be in the future")

    payments = tuple(payments_made)
    for p in payments:
        if p.paid_on is not None and p.paid_on > today:
            raise ValueError("payment paid_on must not be in the future")
        if p.retrieval_date is not None and p.retrieval_date > today:
            raise ValueError("payment retrieval_date must not be in the future")

    unresolved: str | None = None

    missing = [name for name, item in zip(
        ("final_liability", "deductions_credits", "prior_poa"), items,
    ) if item.amount is None]
    if missing:
        unresolved = f"missing_evidence:{','.join(missing)}"
    elif any(item.completeness is not Completeness.COMPLETE_FOR_PURPOSE for item in items):
        unresolved = "incomplete_evidence"
    elif any(_is_stale(item.retrieval_date, today, stale_after_days) for item in items):
        unresolved = "stale_evidence"

    if unresolved is None and prior_poa.amount is not None and any(
        p.kind is PaymentKind.PAYMENT_ON_ACCOUNT for p in payments
    ):
        unresolved = "prior_poa_duplicated_in_payments_made"
    if unresolved is None and _conflicting_payments(payments, tolerance):
        unresolved = "conflicting_payment_history"
    if unresolved is None and any(
        item.completeness is not Completeness.COMPLETE_FOR_PURPOSE for item in payments
    ):
        unresolved = "incomplete_payment_history"
    if unresolved is None and any(
        _is_stale(item.retrieval_date, today, stale_after_days) for item in payments
    ):
        unresolved = "stale_payment_history"

    if unresolved is not None:
        return BalancingPosition(
            contract_version=CONTRACT_VERSION,
            tax_year=tax_year,
            due_date=due_date,
            status=BalanceStatus.UNRESOLVED,
            source=final_liability.source,
            final_liability=final_liability.amount,
            deductions_credits=deductions_credits.amount,
            prior_poa=prior_poa.amount,
            payments_made_total=None,
            remaining_balance=None,
            excess_credit=None,
            limitations=("balancing_position_unresolved", unresolved),
            prohibited_uses=_BALANCE_PROHIBITED_USES,
            unresolved_reason=unresolved,
        )

    payments_total = sum((item.amount for item in payments), ZERO)
    net = (
        final_liability.amount
        - deductions_credits.amount
        - prior_poa.amount
        - payments_total
    )
    net = _round_penny(net)

    limitations: list[str] = []
    if final_liability.source is SourceKind.LOCAL_ESTIMATE:
        limitations.append("final_liability_is_local_estimate_not_hmrc_issued")
    if any(item.source is SourceKind.LOCAL_ESTIMATE for item in (deductions_credits, prior_poa)):
        limitations.append("credits_or_prior_poa_are_local_estimates")

    if net >= ZERO:
        return BalancingPosition(
            contract_version=CONTRACT_VERSION,
            tax_year=tax_year,
            due_date=due_date,
            status=BalanceStatus.REMAINING_BALANCE,
            source=final_liability.source,
            final_liability=final_liability.amount,
            deductions_credits=deductions_credits.amount,
            prior_poa=prior_poa.amount,
            payments_made_total=payments_total,
            remaining_balance=net,
            excess_credit=None,
            limitations=tuple(limitations),
            prohibited_uses=_BALANCE_PROHIBITED_USES,
            unresolved_reason=None,
        )

    return BalancingPosition(
        contract_version=CONTRACT_VERSION,
        tax_year=tax_year,
        due_date=due_date,
        status=BalanceStatus.EXCESS_CREDIT,
        source=final_liability.source,
        final_liability=final_liability.amount,
        deductions_credits=deductions_credits.amount,
        prior_poa=prior_poa.amount,
        payments_made_total=payments_total,
        remaining_balance=None,
        excess_credit=abs(net),
        limitations=tuple(limitations),
        prohibited_uses=_BALANCE_PROHIBITED_USES,
        unresolved_reason=None,
    )


def _conflicting_payments(payments: tuple[PaymentMade, ...], tolerance: Decimal) -> bool:
    by_reference: dict[str, list[Decimal]] = {}
    for item in payments:
        if item.reference is None:
            continue
        by_reference.setdefault(item.reference, []).append(item.amount)
    for amounts in by_reference.values():
        if len(amounts) < 2:
            continue
        if max(amounts) - min(amounts) > tolerance:
            return True
    return False
