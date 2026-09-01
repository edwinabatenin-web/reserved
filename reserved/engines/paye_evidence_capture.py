"""Pure, minimised capture boundary for customer-confirmed PAYE evidence.

This module accepts structured facts only.  It performs no document handling,
storage, network access, payroll calculation, forecasting, or source selection.
"""

from dataclasses import dataclass, fields
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
import re

from .paye_reconciliation import (
    Completeness,
    EvidenceKind,
    EvidenceRepresentation,
    PayeEvidence,
)


class CaptureSource(str, Enum):
    SOURCE_DOCUMENT = "source_document"
    MANUAL = "manual"


class SourceDocumentType(str, Enum):
    PAYSLIP = "payslip"
    P45 = "p45"
    P60 = "p60"


class PayFrequency(str, Enum):
    WEEKLY = "weekly"
    FORTNIGHTLY = "fortnightly"
    FOUR_WEEKLY = "four_weekly"
    MONTHLY = "monthly"
    ANNUALLY = "annually"
    OTHER = "other"
    UNKNOWN = "unknown"


class PensionTreatment(str, Enum):
    NONE = "none"
    SALARY_SACRIFICE = "salary_sacrifice"
    NET_PAY = "net_pay"
    RELIEF_AT_SOURCE = "relief_at_source"
    UNKNOWN = "unknown"


_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_TAX_YEAR = re.compile(r"(\d{4})-(\d{2})\Z")
_MONEY = re.compile(r"(?:0|[1-9]\d*)(?:\.\d{1,2})?\Z")
_TAX_CODE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 /-]{0,31}\Z")


def _identifier(name: str, value: object, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{name} must be a non-blank stable identifier")
    return value


def _optional_text(name: str, value: object) -> str | None:
    if value is None:
        return None
    if (
        type(value) is not str
        or value != value.strip()
        or not _TAX_CODE.fullmatch(value)
    ):
        raise ValueError(f"{name} has an invalid value")
    return value


def _enum(name: str, value: object, enum_type: type[Enum]):
    if type(value) is not enum_type:
        raise TypeError(f"{name} must be a {enum_type.__name__}")
    return value


def _date(name: str, value: object) -> date:
    if type(value) is not date:
        raise TypeError(f"{name} must be a date")
    return value


def _amount(name: str, value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool) or isinstance(value, float) or type(value) not in {str, int, Decimal}:
        raise TypeError(f"{name} must be an exact decimal, integer, string, or None")
    if type(value) is str and not _MONEY.fullmatch(value):
        raise ValueError(f"{name} must be an unambiguous non-negative decimal")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError(f"{name} must be an exact decimal") from None
    if not parsed.is_finite() or parsed.is_signed() or parsed.as_tuple().exponent < -2:
        raise ValueError(f"{name} must be finite, non-negative, and have at most two decimal places")
    return parsed.quantize(Decimal("0.01"))


def _tax_year_bounds(value: object) -> tuple[str, date, date]:
    if type(value) is not str:
        raise TypeError("tax_year must be a string")
    match = _TAX_YEAR.fullmatch(value)
    if not match:
        raise ValueError("tax_year must use YYYY-YY format")
    start_year = int(match.group(1))
    if int(match.group(2)) != (start_year + 1) % 100:
        raise ValueError("tax_year end must immediately follow its start")
    return value, date(start_year, 4, 6), date(start_year + 1, 4, 5)


@dataclass(frozen=True, slots=True, repr=False)
class PayeEvidenceCapture:
    """Customer-confirmed, structured PAYE facts; never a raw document."""

    source: CaptureSource
    evidence_id: str
    tax_year: str
    employment_id: str
    gross_pay_to_date: Decimal | str | int | None
    tax_paid_to_date: Decimal | str | int | None
    tax_code: str | None
    pay_frequency: PayFrequency
    pension_treatment: PensionTreatment
    effective_through: date
    observed_on: date
    document_type: SourceDocumentType | None = None
    supersedes_evidence_id: str | None = None

    def __post_init__(self) -> None:
        source = _enum("source", self.source, CaptureSource)
        document_type = self.document_type
        if source is CaptureSource.SOURCE_DOCUMENT:
            _enum("document_type", document_type, SourceDocumentType)
        elif document_type is not None:
            raise ValueError("document_type is only valid for source-document capture")

        tax_year, first_day, last_day = _tax_year_bounds(self.tax_year)
        effective = _date("effective_through", self.effective_through)
        observed = _date("observed_on", self.observed_on)
        if not first_day <= effective <= last_day:
            raise ValueError("effective_through must fall within tax_year")
        if observed < effective:
            raise ValueError("observed_on cannot precede effective_through")

        evidence_id = _identifier("evidence_id", self.evidence_id)
        employment_id = _identifier("employment_id", self.employment_id)
        supersedes = _identifier(
            "supersedes_evidence_id", self.supersedes_evidence_id, optional=True
        )
        if supersedes == evidence_id:
            raise ValueError("evidence cannot supersede itself")

        object.__setattr__(self, "tax_year", tax_year)
        object.__setattr__(self, "evidence_id", evidence_id)
        object.__setattr__(self, "employment_id", employment_id)
        object.__setattr__(self, "gross_pay_to_date", _amount("gross_pay_to_date", self.gross_pay_to_date))
        object.__setattr__(self, "tax_paid_to_date", _amount("tax_paid_to_date", self.tax_paid_to_date))
        object.__setattr__(self, "tax_code", _optional_text("tax_code", self.tax_code))
        object.__setattr__(self, "pay_frequency", _enum("pay_frequency", self.pay_frequency, PayFrequency))
        object.__setattr__(self, "pension_treatment", _enum(
            "pension_treatment", self.pension_treatment, PensionTreatment
        ))
        object.__setattr__(self, "supersedes_evidence_id", supersedes)

    def __repr__(self) -> str:
        present = [field.name for field in fields(self) if getattr(self, field.name) is not None]
        return f"PayeEvidenceCapture(validated_fields={tuple(present)!r})"


def normalise_paye_evidence(capture: PayeEvidenceCapture) -> PayeEvidence:
    """Map one validated capture into the existing reconciliation contract."""
    if type(capture) is not PayeEvidenceCapture:
        raise TypeError("capture must be a PayeEvidenceCapture")
    kind = (
        EvidenceKind.DOCUMENT
        if capture.source is CaptureSource.SOURCE_DOCUMENT
        else EvidenceKind.MANUAL
    )
    source_reference = (
        f"customer_confirmed:{capture.document_type.value}"
        if capture.document_type is not None
        else "customer_confirmed:structured_manual"
    )
    return PayeEvidence(
        kind=kind,
        tax_year=capture.tax_year,
        tax_paid_to_date=capture.tax_paid_to_date,
        gross_pay_to_date=capture.gross_pay_to_date,
        employment_id=capture.employment_id,
        tax_code=capture.tax_code,
        observed_on=capture.observed_on,
        source_reference=source_reference,
        evidence_id=capture.evidence_id,
        representation=EvidenceRepresentation.EMPLOYMENT_CUMULATIVE,
        completeness=Completeness.PARTIAL,
        effective_through=capture.effective_through,
    )
