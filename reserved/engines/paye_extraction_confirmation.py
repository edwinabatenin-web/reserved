"""S2A: network-inert extraction-confirmation contract for the PAYE fallback.

This module is the pure boundary between an untrusted structured payslip
extraction candidate and an explicit customer-confirmed ``PayeEvidenceCapture``.
It accepts typed, bounded fields only; it never handles raw documents, bytes,
OCR text, paths, credentials, tokens, NINOs, or provider/bank identifiers. It
performs no filesystem, network, subprocess, environment, persistence, logging,
or deletion work of any kind.

The only successful output is an in-memory S1-compatible ``PayeEvidenceCapture``
whose source is ``SOURCE_DOCUMENT``, whose document type is exactly ``PAYSLIP``,
and whose eventual normalised completeness remains ``Completeness.PARTIAL``.
"""

from dataclasses import dataclass, fields
from datetime import date
from decimal import Decimal
from enum import Enum
import hashlib
import re

from .paye_evidence_capture import (
    CaptureSource,
    PayFrequency,
    PayeEvidenceCapture,
    PensionTreatment,
    SourceDocumentType,
    _amount,
    _date,
    _enum,
    _identifier,
    _optional_text,
    _tax_year_bounds,
)


class Disposition(str, Enum):
    """The single permitted post-confirmation disposition for the raw document."""

    SECURE_DELETION_REQUIRED = "secure_deletion_required"


class Decision(str, Enum):
    """One customer decision per confirmable field: accept or correct."""

    ACCEPT = "accept"
    CORRECT = "correct"


class FieldName(str, Enum):
    """The exact customer-confirmable fields of a payslip extraction candidate."""

    TAX_YEAR = "tax_year"
    EMPLOYMENT_ID = "employment_id"
    GROSS_PAY_TO_DATE = "gross_pay_to_date"
    TAX_PAID_TO_DATE = "tax_paid_to_date"
    TAX_CODE = "tax_code"
    PAY_FREQUENCY = "pay_frequency"
    PENSION_TREATMENT = "pension_treatment"
    EFFECTIVE_THROUGH = "effective_through"
    OBSERVED_ON = "observed_on"


_FIELD_ORDER = (
    FieldName.TAX_YEAR,
    FieldName.EMPLOYMENT_ID,
    FieldName.GROSS_PAY_TO_DATE,
    FieldName.TAX_PAID_TO_DATE,
    FieldName.TAX_CODE,
    FieldName.PAY_FREQUENCY,
    FieldName.PENSION_TREATMENT,
    FieldName.EFFECTIVE_THROUGH,
    FieldName.OBSERVED_ON,
)
_CONFIRMABLE_FIELDS = frozenset(_FIELD_ORDER)

# A sentinel that is distinct from every possible corrected value (including None).
_UNSET = object()

_SHA256_HEX = re.compile(r"[0-9a-f]{64}\Z")
_PENNY = Decimal("0.01")

_CANDIDATE_DOMAIN = "reserved:hmrc-paye-extraction:candidate"
_CONFIRMATION_DOMAIN = "reserved:hmrc-paye-extraction:confirmation"
_SCHEMA_VERSION = "1"

# ── Reserved defensive resource/magnitude bounds ─────────────────────────────
#
# These are engineering resource limits for this S2A module only. They are NOT
# HMRC or statutory amount limits, and they are far beyond any plausible PAYE
# evidence value. They exist solely to fail closed before an attacker-supplied
# extreme magnitude/length reaches expensive Decimal conversion or quantisation.

# Exact-ASCII tax-year shape, enforced before the inherited S1 ``\d`` validator
# so non-ASCII decimal digits (e.g. Arabic-Indic or full-width) cannot survive
# validation and later explode inside ASCII canonical encoding.
_ASCII_TAX_YEAR = re.compile(r"[0-9]{4}-[0-9]{2}\Z")

# 10^18, matching the established Reserved defensive decimal ceiling used
# elsewhere in the codebase. Inclusive at the boundary, rejected just above.
_MAX_ABS_AMOUNT = Decimal("1000000000000000000")
_MAX_AMOUNT_INTEGER = 1_000_000_000_000_000_000
_MAX_AMOUNT_STRING_CHARS = 128

# Honest caller-supplied replay check remains exact, but its input set is now
# bounded so a caller cannot force unbounded iteration/memory work.
_MAX_CONSUMED_DIGESTS = 10_000


def _validate_digest(name: str, value: object) -> None:
    if type(value) is not str or not _SHA256_HEX.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase hexadecimal SHA-256 digest")


def _tax_year_ascii(name: str, value: object) -> str:
    """Require an exact-ASCII ``YYYY-YY`` tax year before S1 canonical bounds."""
    if type(value) is not str:
        raise TypeError(f"{name} must be a string")
    if not _ASCII_TAX_YEAR.fullmatch(value):
        raise ValueError(f"{name} must use ASCII YYYY-YY format")
    return _tax_year_bounds(value)[0]


def _amount_bounded(name: str, value: object) -> Decimal | None:
    """Apply the Reserved defensive numeric/resource bound around S1 ``_amount``.

    Extreme integers, Decimals and numeric strings are rejected before the
    inherited validator performs expensive conversion or quantisation. The bound
    is a defensive resource limit, not an HMRC or statutory amount limit.
    """
    if value is None:
        return None
    if isinstance(value, bool) or isinstance(value, float) or type(value) not in {str, int, Decimal}:
        raise TypeError(f"{name} must be an exact decimal, integer, string, or None")

    if type(value) is int:
        if abs(value) > _MAX_AMOUNT_INTEGER:
            raise ValueError(f"{name} exceeds the Reserved defensive magnitude bound")
    elif type(value) is Decimal:
        if value.is_finite():
            adjusted = value.adjusted()
            if adjusted > _MAX_ABS_AMOUNT.adjusted() or (
                adjusted == _MAX_ABS_AMOUNT.adjusted()
                and abs(value) > _MAX_ABS_AMOUNT
            ):
                raise ValueError(f"{name} exceeds the Reserved defensive magnitude bound")
    else:  # str
        if len(value) > _MAX_AMOUNT_STRING_CHARS:
            raise ValueError(f"{name} exceeds the Reserved defensive length bound")

    normalised = _amount(name, value)

    # Defence in depth: re-assert the magnitude bound on the normalised Decimal
    # so no accepted value can exceed the Reserved ceiling.
    if normalised is not None:
        adjusted = normalised.adjusted()
        if adjusted > _MAX_ABS_AMOUNT.adjusted() or (
            adjusted == _MAX_ABS_AMOUNT.adjusted() and normalised > _MAX_ABS_AMOUNT
        ):
            raise ValueError(f"{name} exceeds the Reserved defensive magnitude bound")
    return normalised


def _normalise_corrected_value(field: FieldName, value: object):
    """Validate and normalise one corrected value against its exact field contract."""
    if field is FieldName.TAX_YEAR:
        return _tax_year_ascii("tax_year", value)
    if field is FieldName.EMPLOYMENT_ID:
        return _identifier("employment_id", value)
    if field is FieldName.GROSS_PAY_TO_DATE:
        return _amount_bounded("gross_pay_to_date", value)
    if field is FieldName.TAX_PAID_TO_DATE:
        return _amount_bounded("tax_paid_to_date", value)
    if field is FieldName.TAX_CODE:
        return _optional_text("tax_code", value)
    if field is FieldName.PAY_FREQUENCY:
        return _enum("pay_frequency", value, PayFrequency)
    if field is FieldName.PENSION_TREATMENT:
        return _enum("pension_treatment", value, PensionTreatment)
    if field is FieldName.EFFECTIVE_THROUGH:
        return _date("effective_through", value)
    if field is FieldName.OBSERVED_ON:
        return _date("observed_on", value)
    raise ValueError("unknown confirmable field")


# ── Canonical length-prefixed encoding (never calls attacker hooks) ────────────

_TAG_MISSING = b"\x00"
_TAG_STRING = b"\x01"
_TAG_MONEY = b"\x02"
_TAG_DATE = b"\x03"
_TAG_ENUM = b"\x04"
_TAG_DIGEST = b"\x05"


def _length_prefixed(payload: bytes) -> bytes:
    return len(payload).to_bytes(4, "big") + payload


def _enc_missing() -> bytes:
    return _TAG_MISSING


def _enc_string(value: str) -> bytes:
    return _TAG_STRING + _length_prefixed(value.encode("ascii"))


def _enc_money(value: Decimal) -> bytes:
    return _TAG_MONEY + _length_prefixed(
        format(value.quantize(_PENNY), "f").encode("ascii")
    )


def _enc_date(value: date) -> bytes:
    return _TAG_DATE + _length_prefixed(value.isoformat().encode("ascii"))


def _enc_enum(value: Enum) -> bytes:
    return _TAG_ENUM + _length_prefixed(value.value.encode("ascii"))


def _enc_digest(value: str) -> bytes:
    return _TAG_DIGEST + _length_prefixed(value.encode("ascii"))


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True, repr=False)
class FieldDecision:
    """One explicit accept-or-correct decision for one confirmable field."""

    field: FieldName
    decision: Decision
    corrected_value: object = _UNSET

    def __post_init__(self) -> None:
        _enum("field", self.field, FieldName)
        _enum("decision", self.decision, Decision)
        if self.decision is Decision.ACCEPT:
            if self.corrected_value is not _UNSET:
                raise ValueError("an accept decision must not carry a corrected value")
        else:
            if self.corrected_value is _UNSET:
                raise ValueError("a correct decision must carry a corrected value")
            object.__setattr__(
                self,
                "corrected_value",
                _normalise_corrected_value(self.field, self.corrected_value),
            )

    def __repr__(self) -> str:
        return f"FieldDecision(field={self.field.value}, decision={self.decision.value})"


@dataclass(frozen=True, slots=True, repr=False)
class PayeExtractionCandidate:
    """A structured payslip extraction candidate; typed and bounded, never raw."""

    candidate_id: str
    document_id: str
    evidence_id: str
    document_type: SourceDocumentType
    supersedes_evidence_id: str | None
    tax_year: str
    employment_id: str
    gross_pay_to_date: Decimal | str | int | None
    tax_paid_to_date: Decimal | str | int | None
    tax_code: str | None
    pay_frequency: PayFrequency
    pension_treatment: PensionTreatment
    effective_through: date
    observed_on: date

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_id", _identifier("candidate_id", self.candidate_id))
        object.__setattr__(self, "document_id", _identifier("document_id", self.document_id))
        object.__setattr__(self, "evidence_id", _identifier("evidence_id", self.evidence_id))
        object.__setattr__(
            self,
            "supersedes_evidence_id",
            _identifier("supersedes_evidence_id", self.supersedes_evidence_id, optional=True),
        )
        object.__setattr__(self, "document_type", _enum("document_type", self.document_type, SourceDocumentType))
        if self.document_type is not SourceDocumentType.PAYSLIP:
            raise ValueError("only payslip documents are supported")
        object.__setattr__(self, "tax_year", _tax_year_ascii("tax_year", self.tax_year))
        object.__setattr__(self, "employment_id", _identifier("employment_id", self.employment_id))
        object.__setattr__(self, "gross_pay_to_date", _amount_bounded("gross_pay_to_date", self.gross_pay_to_date))
        object.__setattr__(self, "tax_paid_to_date", _amount_bounded("tax_paid_to_date", self.tax_paid_to_date))
        object.__setattr__(self, "tax_code", _optional_text("tax_code", self.tax_code))
        object.__setattr__(self, "pay_frequency", _enum("pay_frequency", self.pay_frequency, PayFrequency))
        object.__setattr__(
            self,
            "pension_treatment",
            _enum("pension_treatment", self.pension_treatment, PensionTreatment),
        )
        object.__setattr__(self, "effective_through", _date("effective_through", self.effective_through))
        object.__setattr__(self, "observed_on", _date("observed_on", self.observed_on))

    def __repr__(self) -> str:
        present = [field.name for field in fields(self) if getattr(self, field.name) is not None]
        return f"PayeExtractionCandidate(validated_fields={tuple(present)!r})"


def _candidate_canonical_bytes(candidate: PayeExtractionCandidate) -> bytes:
    return b"".join((
        _enc_string(_CANDIDATE_DOMAIN),
        _enc_string(_SCHEMA_VERSION),
        _enc_string(candidate.candidate_id),
        _enc_string(candidate.document_id),
        _enc_string(candidate.evidence_id),
        _enc_enum(candidate.document_type),
        _enc_string(candidate.supersedes_evidence_id)
        if candidate.supersedes_evidence_id is not None
        else _enc_missing(),
        _enc_string(candidate.tax_year),
        _enc_string(candidate.employment_id),
        _enc_money(candidate.gross_pay_to_date)
        if candidate.gross_pay_to_date is not None
        else _enc_missing(),
        _enc_money(candidate.tax_paid_to_date)
        if candidate.tax_paid_to_date is not None
        else _enc_missing(),
        _enc_string(candidate.tax_code) if candidate.tax_code is not None else _enc_missing(),
        _enc_enum(candidate.pay_frequency),
        _enc_enum(candidate.pension_treatment),
        _enc_date(candidate.effective_through),
        _enc_date(candidate.observed_on),
    ))


def candidate_digest(candidate: PayeExtractionCandidate) -> str:
    """Return the canonical candidate digest for an exact candidate instance."""
    if type(candidate) is not PayeExtractionCandidate:
        raise TypeError("candidate must be a PayeExtractionCandidate")
    return _sha256(_candidate_canonical_bytes(candidate))


def _resolve_value(field: FieldName, decision: FieldDecision, candidate: PayeExtractionCandidate):
    if decision.decision is Decision.ACCEPT:
        return getattr(candidate, field.value)
    try:
        return _normalise_corrected_value(field, decision.corrected_value)
    except (ValueError, TypeError):
        raise ValueError(f"correction for {field.value} is invalid") from None


def _encode_confirmed_value(field: FieldName, value) -> bytes:
    if field in (FieldName.GROSS_PAY_TO_DATE, FieldName.TAX_PAID_TO_DATE):
        return _enc_money(value) if value is not None else _enc_missing()
    if field is FieldName.TAX_CODE:
        return _enc_string(value) if value is not None else _enc_missing()
    if field in (FieldName.PAY_FREQUENCY, FieldName.PENSION_TREATMENT):
        return _enc_enum(value)
    if field in (FieldName.EFFECTIVE_THROUGH, FieldName.OBSERVED_ON):
        return _enc_date(value)
    return _enc_string(value)


def _organise_decisions(decisions) -> dict[FieldName, FieldDecision]:
    if type(decisions) is not tuple:
        raise TypeError("decisions must be a tuple")
    seen: dict[FieldName, FieldDecision] = {}
    for decision in decisions:
        if type(decision) is not FieldDecision:
            raise TypeError("each decision must be a FieldDecision")
        field = decision.field
        if field in seen:
            raise ValueError("duplicate decision for a field")
        seen[field] = decision
    if frozenset(seen) != _CONFIRMABLE_FIELDS:
        raise ValueError("exactly one decision is required for each confirmable field")
    return seen


def _validate_consumed_digests(value: object) -> None:
    if type(value) is not frozenset:
        raise TypeError("consumed_candidate_digests must be a frozenset")
    if len(value) > _MAX_CONSUMED_DIGESTS:
        raise ValueError(
            "consumed_candidate_digests exceeds the Reserved defensive maximum count"
        )
    for digest in value:
        if type(digest) is not str or not _SHA256_HEX.fullmatch(digest):
            raise ValueError(
                "each consumed candidate digest must be a lowercase hexadecimal SHA-256"
            )


def _confirmation_canonical_bytes(
    candidate_digest_value: str,
    decisions_by_field: dict[FieldName, FieldDecision],
    resolved: dict[FieldName, object],
    confirmation_id: str,
    disposition: Disposition,
) -> bytes:
    parts = [
        _enc_string(_CONFIRMATION_DOMAIN),
        _enc_string(_SCHEMA_VERSION),
        _enc_digest(candidate_digest_value),
    ]
    for field in _FIELD_ORDER:
        decision = decisions_by_field[field]
        parts.append(_enc_enum(decision.decision))
        if decision.decision is Decision.CORRECT:
            parts.append(_encode_confirmed_value(field, resolved[field]))
    parts.append(_enc_string(confirmation_id))
    parts.append(_enc_enum(disposition))
    return b"".join(parts)


@dataclass(frozen=True, slots=True, repr=False, init=False)
class PayeExtractionConfirmation:
    """Immutable, redacted confirmation result; never evidence of deletion.

    A successful result is producible only by the validated
    ``confirm_paye_extraction`` path. The public ``__init__`` always raises,
    ``dataclasses.replace`` therefore cannot produce a forged/spliced result, and
    pickling is disabled. ``copy.copy``/``copy.deepcopy`` return this same deeply
    immutable instance. This does not protect against deliberate use of
    ``object.__new__`` or private implementation import by malicious code.
    """

    candidate_digest: str
    confirmation_digest: str
    confirmation_id: str
    disposition: Disposition
    capture: PayeEvidenceCapture

    def __init__(self, *args, **kwargs):
        raise TypeError(
            "PayeExtractionConfirmation cannot be constructed directly; "
            "use confirm_paye_extraction"
        )

    @classmethod
    def _create(
        cls,
        *,
        candidate_digest: str,
        confirmation_digest: str,
        confirmation_id: str,
        disposition: Disposition,
        capture: PayeEvidenceCapture,
    ) -> "PayeExtractionConfirmation":
        _validate_digest("candidate_digest", candidate_digest)
        _validate_digest("confirmation_digest", confirmation_digest)
        confirmation_id = _identifier("confirmation_id", confirmation_id)
        if (
            type(disposition) is not Disposition
            or disposition is not Disposition.SECURE_DELETION_REQUIRED
        ):
            raise ValueError("disposition must be secure_deletion_required")
        if type(capture) is not PayeEvidenceCapture:
            raise TypeError("capture must be a PayeEvidenceCapture")
        instance = object.__new__(cls)
        object.__setattr__(instance, "candidate_digest", candidate_digest)
        object.__setattr__(instance, "confirmation_digest", confirmation_digest)
        object.__setattr__(instance, "confirmation_id", confirmation_id)
        object.__setattr__(instance, "disposition", disposition)
        object.__setattr__(instance, "capture", capture)
        return instance

    @property
    def secure_deletion_required(self) -> bool:
        return self.disposition is Disposition.SECURE_DELETION_REQUIRED

    def __repr__(self) -> str:
        return f"PayeExtractionConfirmation(disposition={self.disposition.value})"

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __reduce__(self):
        raise TypeError("PayeExtractionConfirmation cannot be pickled")

    def __reduce_ex__(self, protocol):
        raise TypeError("PayeExtractionConfirmation cannot be pickled")


def confirm_paye_extraction(
    candidate: PayeExtractionCandidate,
    decisions,
    confirmation_id: str,
    *,
    candidate_digest: str | None = None,
    consumed_candidate_digests=frozenset(),
) -> PayeExtractionConfirmation:
    """Confirm a typed payslip extraction candidate into an S1-compatible capture.

    The result is immutable, redacted, and states only that secure deletion is
    required. It performs no I/O and never claims the raw document was deleted.
    """
    if type(candidate) is not PayeExtractionCandidate:
        raise TypeError("candidate must be a PayeExtractionCandidate")
    confirmation_id = _identifier("confirmation_id", confirmation_id)

    actual_candidate_digest = _sha256(_candidate_canonical_bytes(candidate))
    if candidate_digest is not None:
        _validate_digest("candidate_digest", candidate_digest)
        if candidate_digest != actual_candidate_digest:
            raise ValueError("supplied candidate digest does not match the candidate")

    _validate_consumed_digests(consumed_candidate_digests)
    if actual_candidate_digest in consumed_candidate_digests:
        raise ValueError("candidate digest has already been consumed")

    decisions_by_field = _organise_decisions(decisions)

    resolved: dict[FieldName, object] = {}
    for field in _FIELD_ORDER:
        resolved[field] = _resolve_value(field, decisions_by_field[field], candidate)

    try:
        capture = PayeEvidenceCapture(
            source=CaptureSource.SOURCE_DOCUMENT,
            document_type=SourceDocumentType.PAYSLIP,
            evidence_id=candidate.evidence_id,
            tax_year=resolved[FieldName.TAX_YEAR],
            employment_id=resolved[FieldName.EMPLOYMENT_ID],
            gross_pay_to_date=resolved[FieldName.GROSS_PAY_TO_DATE],
            tax_paid_to_date=resolved[FieldName.TAX_PAID_TO_DATE],
            tax_code=resolved[FieldName.TAX_CODE],
            pay_frequency=resolved[FieldName.PAY_FREQUENCY],
            pension_treatment=resolved[FieldName.PENSION_TREATMENT],
            effective_through=resolved[FieldName.EFFECTIVE_THROUGH],
            observed_on=resolved[FieldName.OBSERVED_ON],
            supersedes_evidence_id=candidate.supersedes_evidence_id,
        )
    except (ValueError, TypeError):
        raise ValueError("resolved PAYE capture failed validation") from None

    disposition = Disposition.SECURE_DELETION_REQUIRED
    confirmation_digest_value = _sha256(
        _confirmation_canonical_bytes(
            actual_candidate_digest,
            decisions_by_field,
            resolved,
            confirmation_id,
            disposition,
        )
    )

    return PayeExtractionConfirmation._create(
        candidate_digest=actual_candidate_digest,
        confirmation_digest=confirmation_digest_value,
        confirmation_id=confirmation_id,
        disposition=disposition,
        capture=capture,
    )


__all__ = [
    "Decision",
    "Disposition",
    "FieldDecision",
    "FieldName",
    "PayeExtractionCandidate",
    "PayeExtractionConfirmation",
    "candidate_digest",
    "confirm_paye_extraction",
]
