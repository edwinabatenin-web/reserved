"""Transport-neutral source-evidence boundary for the HMRC Individual
Employment 1.2 read.

This module consumes only an exact, already validated
``EmploymentHistoryObservation`` produced by
``reserved.providers.hmrc_individual_employment_contract`` and emits a deeply
immutable, redacted, transport-neutral evidence bundle. It is deliberately not a
transport adapter, parser of the full OpenAPI document, credential store,
provider enabler or activation path. It creates no ``PayeEvidence``, no
canonical accounting evidence, no money/tax/cash/customer data and no
employment-identity join.

The bundle re-validates the entire nested source observation defensively rather
than trusting dataclass construction history, and preserves only:

- the source API name and version constants;
- the validated tax year;
- each source record's explicit provider employer reference and employer name;
- the off-payroll field presence/absence and exact value;
- safe unknown member names already evidenced at each source layer;
- a caller-supplied opaque evidence/run reference;
- an aware UTC or fixed-offset observation timestamp; and
- an optional lowercase SHA-256 digest of a separately redacted source artefact.

Completeness is always ``UNVERIFIED``. Source record order and duplicates are
preserved as evidence only: order has no semantic precedence, and matching
employer references or names do not establish identity or a join. Empty or
whitespace-only provider strings remain schema-valid only where the exact source
contract allows them and are preserved exactly, without trimming, normalising or
inferring meaning.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from reserved.providers.hmrc_individual_employment_contract import (
    COMPLETENESS_UNVERIFIED,
    HMRC_INDIVIDUAL_EMPLOYMENT_API_NAME,
    HMRC_INDIVIDUAL_EMPLOYMENT_API_VERSION,
    HMRC_INDIVIDUAL_EMPLOYMENT_OPTIONAL_EMPLOYMENT_FIELDS,
    HMRC_INDIVIDUAL_EMPLOYMENT_REQUIRED_EMPLOYMENT_FIELDS,
    HMRC_INDIVIDUAL_EMPLOYMENT_SUCCESS_STATUS,
    RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH,
    RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH,
    RESERVED_DEFENSIVE_MAX_EMPLOYMENTS,
    RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH,
    RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS,
    EmploymentHistoryObservation,
    EmploymentRecordObservation,
)

# ── Reserved defensive policy bounds (NOT HMRC wire facts) ──────────────────
#
# The source contract records HMRC's schemas state no maximum for the
# ``employments`` array, the employer identifier/name strings, or the
# length/number of unknown member names. The bound below is a local safety
# limit only for the caller-supplied opaque evidence/run reference. It is not a
# provider fact and must not be presented as such.
RESERVED_DEFENSIVE_MAX_EVIDENCE_REFERENCE_LENGTH = 256

_TAX_YEAR_RE = re.compile(r"[0-9]{4}-[0-9]{2}")
_SHA256_HEX_RE = re.compile(r"[0-9a-f]{64}")

_TOP_LEVEL_DOCUMENTED_FIELDS = frozenset({"employments"})
_EMPLOYMENT_DOCUMENTED_FIELDS = (
    HMRC_INDIVIDUAL_EMPLOYMENT_REQUIRED_EMPLOYMENT_FIELDS
    | HMRC_INDIVIDUAL_EMPLOYMENT_OPTIONAL_EMPLOYMENT_FIELDS
)

_UNSET = object()

_SOURCE_RECORD_INSTANCE_FIELDS = frozenset(
    {
        "employer_paye_reference",
        "employer_name",
        "off_payroll_work_flag",
        "absent_fields",
        "unknown_fields",
    }
)
_SOURCE_OBSERVATION_INSTANCE_FIELDS = frozenset(
    {
        "tax_year",
        "status_code",
        "employments",
        "completeness",
        "absent_fields",
        "unknown_fields",
    }
)


class HMRCIndividualEmploymentSourceEvidenceError(ValueError):
    """Controlled validation failure whose message never includes source values."""


# ── Exact built-in validators ────────────────────────────────────────────────


def _has_unsafe_unicode_character(text: str) -> bool:
    """Return ``True`` if any character is in Unicode general category ``C``.

    The caller guarantees ``text`` is an exact built-in ``str``, so iteration
    cannot dispatch to a subclass override.
    """
    for character in text:
        if unicodedata.category(character).startswith("C"):
            return True
    return False


def _require_exact_str(value: Any, field: str) -> str:
    if type(value) is not str:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            f"HMRC Individual Employment source evidence: {field} must be a string"
        )
    return value


def _require_retained_string(value: Any, field: str, max_length: int) -> str:
    """Validate an exact built-in string within a Reserved defensive bound."""
    result = _require_exact_str(value, field)
    if len(result) > max_length:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            f"HMRC Individual Employment source evidence: {field} exceeds the "
            "Reserved defensive bound"
        )
    if _has_unsafe_unicode_character(result):
        raise HMRCIndividualEmploymentSourceEvidenceError(
            f"HMRC Individual Employment source evidence: {field} contains unsafe "
            "Unicode characters"
        )
    return result


def _require_exact_frozenset(value: Any, field: str) -> frozenset[str]:
    if type(value) is not frozenset:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            f"HMRC Individual Employment source evidence: {field} must be a frozenset"
        )
    return value


def _validate_absent_fields(
    value: Any, field: str, optional: frozenset[str]
) -> frozenset[str]:
    names = _require_exact_frozenset(value, field)
    for name in names:
        if type(name) is not str:
            raise HMRCIndividualEmploymentSourceEvidenceError(
                f"HMRC Individual Employment source evidence: {field} names must "
                "be strings"
            )
        if name not in optional:
            raise HMRCIndividualEmploymentSourceEvidenceError(
                f"HMRC Individual Employment source evidence: {field} contains a "
                "non-optional field"
            )
    return names


def _validate_unknown_fields(
    value: Any, field: str, documented: frozenset[str]
) -> frozenset[str]:
    names = _require_exact_frozenset(value, field)
    if len(names) > RESERVED_DEFENSIVE_MAX_UNKNOWN_KEYS:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            f"HMRC Individual Employment source evidence: {field} exceeds the "
            "Reserved unknown-field bound"
        )
    for name in names:
        if type(name) is not str:
            raise HMRCIndividualEmploymentSourceEvidenceError(
                f"HMRC Individual Employment source evidence: {field} names must "
                "be strings"
            )
        if len(name) > RESERVED_DEFENSIVE_MAX_MEMBER_NAME_LENGTH:
            raise HMRCIndividualEmploymentSourceEvidenceError(
                f"HMRC Individual Employment source evidence: {field} name "
                "exceeds the Reserved defensive bound"
            )
        if _has_unsafe_unicode_character(name):
            raise HMRCIndividualEmploymentSourceEvidenceError(
                f"HMRC Individual Employment source evidence: {field} name "
                "contains unsafe Unicode characters"
            )
        if name in documented:
            raise HMRCIndividualEmploymentSourceEvidenceError(
                f"HMRC Individual Employment source evidence: {field} name "
                "collides with a documented field"
            )
    return names


def _validate_evidence_reference(value: Any) -> str:
    result = _require_exact_str(value, "evidence reference")
    if len(result) > RESERVED_DEFENSIVE_MAX_EVIDENCE_REFERENCE_LENGTH:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: evidence reference "
            "exceeds the Reserved defensive bound"
        )
    if _has_unsafe_unicode_character(result):
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: evidence reference "
            "contains unsafe Unicode characters"
        )
    return result


def _validate_observed_at(value: Any) -> datetime:
    """Validate an aware fixed-offset ``datetime`` and return it unchanged.

    ``datetime`` is immutable, so no defensive copy is required. The instant is
    preserved exactly as supplied and no timezone conversion or source
    chronology is invented.
    """
    if type(value) is not datetime:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: observation time must "
            "be an aware built-in datetime"
        )
    if type(value.tzinfo) is not timezone:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: observation time must "
            "carry a fixed-offset timezone"
        )
    return value


def _validate_source_artifact_sha256(value: Any) -> str:
    if type(value) is not str:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: artifact digest must be "
            "a lowercase 64-character SHA-256 hex string"
        )
    if _SHA256_HEX_RE.fullmatch(value) is None:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: artifact digest must be "
            "a lowercase 64-character SHA-256 hex string"
        )
    return value


# ── Deep source re-validation ────────────────────────────────────────────────


def _validate_exact_instance_state(
    value: Any, expected_names: frozenset[str], field_name: str
) -> None:
    """Reject missing or additional source-instance attributes by name only.

    The exact source dataclasses are non-slotted, so their instance dictionary
    is the authoritative state shape.  Comparing its key view does not read or
    otherwise interact with any attached value.
    """
    state = object.__getattribute__(value, "__dict__")
    if type(state) is not dict or state.keys() != expected_names:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            f"HMRC Individual Employment source evidence: {field_name} has "
            "unexpected instance state"
        )


def _validate_source_record(record: Any) -> EmploymentRecordObservation:
    if type(record) is not EmploymentRecordObservation:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: employment must be an "
            "exact EmploymentRecordObservation"
        )
    _validate_exact_instance_state(
        record, _SOURCE_RECORD_INSTANCE_FIELDS, "employment"
    )

    _require_retained_string(
        record.employer_paye_reference,
        "employerPayeReference",
        RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH,
    )
    _require_retained_string(
        record.employer_name,
        "employerName",
        RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH,
    )

    off_payroll = record.off_payroll_work_flag
    if off_payroll is not None and type(off_payroll) is not bool:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: off_payroll_work_flag "
            "must be a boolean or None"
        )

    absent = _validate_absent_fields(
        record.absent_fields,
        "absent_fields",
        HMRC_INDIVIDUAL_EMPLOYMENT_OPTIONAL_EMPLOYMENT_FIELDS,
    )
    if (off_payroll is None) != ("offPayrollWorkFlag" in absent):
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: off-payroll absence is "
            "incoherent"
        )

    unknown = _validate_unknown_fields(
        record.unknown_fields, "unknown_fields", _EMPLOYMENT_DOCUMENTED_FIELDS
    )
    if not absent.isdisjoint(unknown):
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: absent and unknown field "
            "names overlap"
        )

    return record


def _validate_source_observation(observation: Any) -> EmploymentHistoryObservation:
    if type(observation) is not EmploymentHistoryObservation:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: source must be an exact "
            "EmploymentHistoryObservation"
        )
    _validate_exact_instance_state(
        observation, _SOURCE_OBSERVATION_INSTANCE_FIELDS, "source"
    )

    tax_year = _require_exact_str(observation.tax_year, "tax_year")
    if _TAX_YEAR_RE.fullmatch(tax_year) is None:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: tax_year must match YYYY-YY"
        )

    status = observation.status_code
    if type(status) is not int:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: status_code must be an integer"
        )
    if status != HMRC_INDIVIDUAL_EMPLOYMENT_SUCCESS_STATUS:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: source must be a "
            "successful observation"
        )

    completeness = observation.completeness
    if type(completeness) is not str or completeness != COMPLETENESS_UNVERIFIED:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: completeness must be UNVERIFIED"
        )

    _validate_absent_fields(observation.absent_fields, "absent_fields", frozenset())
    if len(observation.absent_fields) != 0:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: top-level absent_fields "
            "must be empty"
        )

    _validate_unknown_fields(
        observation.unknown_fields, "unknown_fields", _TOP_LEVEL_DOCUMENTED_FIELDS
    )

    employments = observation.employments
    if type(employments) is not tuple:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: employments must be a tuple"
        )
    if len(employments) == 0:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: employments must not be empty"
        )
    if len(employments) > RESERVED_DEFENSIVE_MAX_EMPLOYMENTS:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: employments exceeds the "
            "Reserved defensive bound"
        )

    for entry in employments:
        _validate_source_record(entry)

    return observation


# ── Deeply immutable, redacted evidence objects ──────────────────────────────


def _validate_evidence_record(record: "EmploymentSourceEvidenceRecord") -> None:
    _require_retained_string(
        record.employer_paye_reference,
        "employerPayeReference",
        RESERVED_DEFENSIVE_MAX_EMPLOYER_PAYE_REFERENCE_LENGTH,
    )
    _require_retained_string(
        record.employer_name,
        "employerName",
        RESERVED_DEFENSIVE_MAX_EMPLOYER_NAME_LENGTH,
    )

    off_payroll = record.off_payroll_work_flag
    if off_payroll is not None and type(off_payroll) is not bool:
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: off_payroll_work_flag "
            "must be a boolean or None"
        )

    absent = _validate_absent_fields(
        record.absent_fields,
        "absent_fields",
        HMRC_INDIVIDUAL_EMPLOYMENT_OPTIONAL_EMPLOYMENT_FIELDS,
    )
    if (off_payroll is None) != ("offPayrollWorkFlag" in absent):
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: off-payroll absence is "
            "incoherent"
        )

    unknown = _validate_unknown_fields(
        record.unknown_fields, "unknown_fields", _EMPLOYMENT_DOCUMENTED_FIELDS
    )
    if not absent.isdisjoint(unknown):
        raise HMRCIndividualEmploymentSourceEvidenceError(
            "HMRC Individual Employment source evidence: absent and unknown field "
            "names overlap"
        )


@dataclass(frozen=True, repr=False)
class EmploymentSourceEvidenceRecord:
    """Redacted, deeply immutable evidence for one source employment record.

    ``off_payroll_work_flag`` is ``None`` when, and only when, the optional
    source field is absent; ``absent_fields`` records that omission. Unknown
    member names are preserved for review without their values.
    """

    employer_paye_reference: str
    employer_name: str
    off_payroll_work_flag: bool | None = None
    absent_fields: frozenset[str] = frozenset()
    unknown_fields: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        _validate_evidence_record(self)

    def __repr__(self) -> str:
        return "EmploymentSourceEvidenceRecord([REDACTED])"

    def __reduce_ex__(self, protocol: int):
        return (
            type(self),
            (
                self.employer_paye_reference,
                self.employer_name,
                self.off_payroll_work_flag,
                self.absent_fields,
                self.unknown_fields,
            ),
        )


@dataclass(frozen=True, repr=False, init=False)
class HMRCIndividualEmploymentEvidence:
    """Deeply immutable, redacted, transport-neutral source-evidence bundle.

    Completeness is always ``UNVERIFIED``. Record order and duplicates are
    preserved as evidence only; order has no semantic precedence and matching
    employer references/names do not establish identity or a join.
    """

    source_api_name: str
    source_api_version: str
    tax_year: str
    records: tuple[EmploymentSourceEvidenceRecord, ...]
    evidence_reference: str
    observed_at: datetime
    completeness: str = COMPLETENESS_UNVERIFIED
    unknown_fields: frozenset[str] = frozenset()
    _source_artifact_sha256_state: Any = field(
        default=_UNSET, repr=False, compare=True
    )

    def __init__(
        self,
        source_api_name: str,
        source_api_version: str,
        tax_year: str,
        records: tuple[EmploymentSourceEvidenceRecord, ...],
        evidence_reference: str,
        observed_at: datetime,
        completeness: str = COMPLETENESS_UNVERIFIED,
        source_artifact_sha256: Any = _UNSET,
        unknown_fields: frozenset[str] = frozenset(),
        *,
        _source_artifact_sha256_state: Any = _UNSET,
    ) -> None:
        object.__setattr__(self, "source_api_name", source_api_name)
        object.__setattr__(self, "source_api_version", source_api_version)
        object.__setattr__(self, "tax_year", tax_year)
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "evidence_reference", evidence_reference)
        object.__setattr__(self, "observed_at", observed_at)
        object.__setattr__(self, "completeness", completeness)
        object.__setattr__(self, "unknown_fields", unknown_fields)
        digest_state = (
            _source_artifact_sha256_state
            if source_artifact_sha256 is _UNSET
            else source_artifact_sha256
        )
        object.__setattr__(self, "_source_artifact_sha256_state", digest_state)
        self.__post_init__()

    def __post_init__(self) -> None:
        if type(self.source_api_name) is not str or (
            self.source_api_name != HMRC_INDIVIDUAL_EMPLOYMENT_API_NAME
        ):
            raise HMRCIndividualEmploymentSourceEvidenceError(
                "HMRC Individual Employment source evidence: source_api_name must "
                "be the exact source API name"
            )
        if type(self.source_api_version) is not str or (
            self.source_api_version != HMRC_INDIVIDUAL_EMPLOYMENT_API_VERSION
        ):
            raise HMRCIndividualEmploymentSourceEvidenceError(
                "HMRC Individual Employment source evidence: source_api_version "
                "must be the exact source API version"
            )

        tax_year = _require_exact_str(self.tax_year, "tax_year")
        if _TAX_YEAR_RE.fullmatch(tax_year) is None:
            raise HMRCIndividualEmploymentSourceEvidenceError(
                "HMRC Individual Employment source evidence: tax_year must match YYYY-YY"
            )

        if type(self.records) is not tuple:
            raise HMRCIndividualEmploymentSourceEvidenceError(
                "HMRC Individual Employment source evidence: records must be a tuple"
            )
        if len(self.records) == 0:
            raise HMRCIndividualEmploymentSourceEvidenceError(
                "HMRC Individual Employment source evidence: records must not be empty"
            )
        if len(self.records) > RESERVED_DEFENSIVE_MAX_EMPLOYMENTS:
            raise HMRCIndividualEmploymentSourceEvidenceError(
                "HMRC Individual Employment source evidence: records exceeds the "
                "Reserved defensive bound"
            )
        for record in self.records:
            if type(record) is not EmploymentSourceEvidenceRecord:
                raise HMRCIndividualEmploymentSourceEvidenceError(
                    "HMRC Individual Employment source evidence: each record must "
                    "be an exact EmploymentSourceEvidenceRecord"
                )
            _validate_evidence_record(record)

        if type(self.completeness) is not str or (
            self.completeness != COMPLETENESS_UNVERIFIED
        ):
            raise HMRCIndividualEmploymentSourceEvidenceError(
                "HMRC Individual Employment source evidence: completeness must be "
                "UNVERIFIED"
            )

        _validate_evidence_reference(self.evidence_reference)
        _validate_observed_at(self.observed_at)

        retained_digest = self._source_artifact_sha256_state
        if retained_digest is not _UNSET:
            _validate_source_artifact_sha256(retained_digest)

        _validate_unknown_fields(
            self.unknown_fields, "unknown_fields", _TOP_LEVEL_DOCUMENTED_FIELDS
        )

    def __repr__(self) -> str:
        return "HMRCIndividualEmploymentEvidence([REDACTED])"

    def __reduce_ex__(self, protocol: int):
        return (
            _reconstruct_evidence,
            (
                self.source_api_name,
                self.source_api_version,
                self.tax_year,
                self.records,
                self.evidence_reference,
                self.observed_at,
                self.completeness,
                self.unknown_fields,
                self._source_artifact_sha256_state is not _UNSET,
                self.source_artifact_sha256,
            ),
        )


def _get_source_artifact_sha256(
    evidence: HMRCIndividualEmploymentEvidence,
) -> str | None:
    retained = evidence._source_artifact_sha256_state
    return None if retained is _UNSET else retained


# Install the read-only public view after dataclass has collected the retained
# fields, leaving constructor presence as a non-retained input.
HMRCIndividualEmploymentEvidence.source_artifact_sha256 = property(  # type: ignore[assignment]
    _get_source_artifact_sha256
)


def _reconstruct_evidence(
    source_api_name: str,
    source_api_version: str,
    tax_year: str,
    records: tuple[EmploymentSourceEvidenceRecord, ...],
    evidence_reference: str,
    observed_at: datetime,
    completeness: str,
    unknown_fields: frozenset[str],
    digest_present: bool,
    digest: Any,
) -> HMRCIndividualEmploymentEvidence:
    kwargs = {}
    if digest_present:
        kwargs["source_artifact_sha256"] = digest
    return HMRCIndividualEmploymentEvidence(
        source_api_name=source_api_name,
        source_api_version=source_api_version,
        tax_year=tax_year,
        records=records,
        evidence_reference=evidence_reference,
        observed_at=observed_at,
        completeness=completeness,
        unknown_fields=unknown_fields,
        **kwargs,
    )


# ── Public builder ───────────────────────────────────────────────────────────


def build_hmrc_individual_employment_source_evidence(
    observation: EmploymentHistoryObservation,
    *,
    evidence_reference: str,
    observed_at: datetime,
    source_artifact_sha256: str | None = _UNSET,
) -> HMRCIndividualEmploymentEvidence:
    """Build a deeply immutable, redacted, transport-neutral evidence bundle.

    Only an exact successful ``EmploymentHistoryObservation`` is accepted; error
    observations, subclasses and arbitrary lookalikes fail closed. The entire
    nested source observation is re-validated before translation.

    ``source_artifact_sha256`` is optional. Omission (the default) is distinct
    from presence; an explicit ``None`` is rejected rather than treated as
    omission.
    """
    validated = _validate_source_observation(observation)

    reference = _validate_evidence_reference(evidence_reference)
    observed = _validate_observed_at(observed_at)
    digest = (
        _UNSET
        if source_artifact_sha256 is _UNSET
        else _validate_source_artifact_sha256(source_artifact_sha256)
    )

    records = tuple(
        EmploymentSourceEvidenceRecord(
            employer_paye_reference=entry.employer_paye_reference,
            employer_name=entry.employer_name,
            off_payroll_work_flag=entry.off_payroll_work_flag,
            absent_fields=entry.absent_fields,
            unknown_fields=entry.unknown_fields,
        )
        for entry in validated.employments
    )

    evidence_kwargs = {}
    if digest is not _UNSET:
        evidence_kwargs["source_artifact_sha256"] = digest
    return HMRCIndividualEmploymentEvidence(
        source_api_name=HMRC_INDIVIDUAL_EMPLOYMENT_API_NAME,
        source_api_version=HMRC_INDIVIDUAL_EMPLOYMENT_API_VERSION,
        tax_year=validated.tax_year,
        records=records,
        evidence_reference=reference,
        observed_at=observed,
        completeness=COMPLETENESS_UNVERIFIED,
        unknown_fields=validated.unknown_fields,
        **evidence_kwargs,
    )
