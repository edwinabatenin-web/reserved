"""Transport-neutral source evidence for HMRC Individual Tax API 1.1.

Consumes only an exact, fully revalidated success observation and preserves
literal provider facts, order, duplicates, presence/absence, safe unknown names
and exact ``int``/``Decimal`` values. It performs no aggregation, netting,
identity/join/deduplication, tax/cash/currentness inference, canonical mapping,
transport, persistence, routing or provider activation.

Completeness is always ``UNVERIFIED``. Empty employments and omitted numeric
members remain valid-but-unverified; explicit zero remains distinct from
absence. ``employerPayeReference`` (including ``267/LS500``) is a literal
provider value only, never an identity or cross-endpoint join key.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from reserved.providers.hmrc_individual_tax_contract import (
    HMRC_INDIVIDUAL_TAX_API_VERSION,
    HMRC_INDIVIDUAL_TAX_COMPLETENESS,
    EmploymentItemObservation,
    IndividualTaxAnnualSummaryObservation,
    PensionsBenefitsObservation,
    RefundsObservation,
    validate_individual_tax_annual_summary_observation,
)

HMRC_INDIVIDUAL_TAX_API_NAME = "Individual Tax"
RESERVED_DEFENSIVE_MAX_EVIDENCE_REFERENCE_LENGTH = 256


class HMRCIndividualTaxSourceEvidenceError(ValueError):
    """Controlled validation failure whose message contains no source value."""


def _create_source_evidence_api(
    *, source_validator: Any,
    source_summary_type: type[IndividualTaxAnnualSummaryObservation],
    source_employment_type: type[EmploymentItemObservation],
    source_benefits_type: type[PensionsBenefitsObservation],
    source_refunds_type: type[RefundsObservation],
    error_type: type[HMRCIndividualTaxSourceEvidenceError],
    datetime_type: type[datetime], timezone_type: type[timezone],
    decimal_type: type[Decimal], integer_type: type[int], string_type: type[str],
    tuple_type: type[tuple], frozenset_type: type[frozenset], dict_type: type[dict],
    set_type: type[set],
    object_type: type[object], type_of: Any, length: Any, absolute: Any,
    maximum: Any, unicode_category: Any, tax_year_fullmatch: Any,
    digest_fullmatch: Any, api_name: str, api_version: str,
    completeness_value: str,
    source_exception_type: type[Exception],
    attribute_error_type: type[AttributeError],
    type_error_type: type[TypeError],
) -> tuple[type, type, type, type, object, object]:
    """Build a closure-sealed API from exact type/constant snapshots.

    Public builder and result methods resolve validation primitives through
    closure cells, not mutable module names. This is process-local tamper
    resistance, not an unforgeable boundary against trusted code able to
    rewrite closure cells or type dictionaries.
    """
    top_names = frozenset_type(
        {"employments", "pensionsAnnuitiesAndOtherStateBenefits", "refunds"}
    )
    employment_names = frozenset_type({"employerPayeReference", "taxTakenOffPay"})
    benefits_names = frozenset_type(
        {"otherPensionsAndRetirementAnnuities", "incapacityBenefit"}
    )
    refund_names = frozenset_type({"taxRefundedOrSetOff"})
    summary_state_names = frozenset_type({
        "employments", "pensions_benefits", "refunds", "request", "tax_year",
        "unknown_names", "completeness", "_request_binding",
    })
    employment_state_names = frozenset_type(
        {"employer_paye_reference", "tax_taken_off_pay", "unknown_names"}
    )
    benefits_state_names = frozenset_type({
        "other_pensions_and_retirement_annuities", "incapacity_benefit",
        "present_fields", "absent_fields", "unknown_names",
    })
    refunds_state_names = frozenset_type(
        {"tax_refunded_or_set_off", "present_fields", "absent_fields", "unknown_names"}
    )
    max_decimal = decimal_type("1000000000000000000")

    def fail(rule: str) -> None:
        raise error_type(f"HMRC Individual Tax source evidence: {rule}")

    def exact_string(value: Any, field_name: str, maximum_length: int) -> str:
        if type_of(value) is not string_type:
            fail(f"{field_name} must be an exact built-in string")
        if length(value) > maximum_length:
            fail(f"{field_name} exceeds the Reserved defensive bound")
        for character in value:
            if unicode_category(character).startswith("C"):
                fail(f"{field_name} contains unsafe Unicode characters")
        return value

    def exact_state(value: Any, expected: frozenset[str], field_name: str) -> dict:
        try:
            state = object_type.__getattribute__(value, "__dict__")
        except (attribute_error_type, type_error_type):
            fail(f"{field_name} has uninspectable instance state")
        if type_of(state) is not dict_type or state.keys() != expected:
            fail(f"{field_name} has unexpected instance state")
        return state

    def unknown_names(value: Any, field_name: str, documented: frozenset[str]) -> frozenset[str]:
        if type_of(value) is not frozenset_type or length(value) > 32:
            fail(f"{field_name} must be a bounded exact frozenset")
        for name in value:
            exact_string(name, f"{field_name} name", 256)
            if not name or name in documented:
                fail(f"{field_name} contains an invalid unknown name")
        return value

    def presence(present_value: Any, absent_value: Any, documented: frozenset[str], field_name: str) -> tuple[frozenset[str], frozenset[str]]:
        if type_of(present_value) is not frozenset_type or type_of(absent_value) is not frozenset_type:
            fail(f"{field_name} presence state must use exact frozensets")
        for names in (present_value, absent_value):
            for name in names:
                if type_of(name) is not string_type or name not in documented:
                    fail(f"{field_name} presence state contains an invalid name")
        if present_value & absent_value or present_value | absent_value != documented:
            fail(f"{field_name} presence state must be disjoint and exhaustive")
        return present_value, absent_value

    def number(value: Any, field_name: str) -> int | Decimal:
        if type_of(value) is integer_type:
            if value > 10**18 or value < -(10**18):
                fail(f"{field_name} exceeds the Reserved integer bound")
            return value
        if type_of(value) is decimal_type:
            if not value.is_finite():
                fail(f"{field_name} must be finite")
            parts = value.as_tuple()
            places = maximum(0, -parts.exponent)
            integer_digits = maximum(1, length(parts.digits) + parts.exponent)
            if (absolute(value) > max_decimal or length(parts.digits) > 38
                    or places > 12 or integer_digits > 38):
                fail(f"{field_name} exceeds the Reserved decimal bound")
            return value
        fail(f"{field_name} must be an exact built-in int or Decimal")

    def optional_number(value: Any, present_fields: frozenset[str], source_name: str) -> int | Decimal | None:
        if source_name in present_fields:
            if value is None:
                fail(f"{source_name} cannot be None when present")
            return number(value, source_name)
        if value is not None:
            fail(f"{source_name} must be None when absent")
        return None

    def collection_time(value: Any) -> datetime:
        if (type_of(value) is not datetime_type or type_of(value.tzinfo) is not timezone_type
                or value.utcoffset() is None):
            fail("collection time must be an aware fixed-offset datetime")
        return value

    def opaque_reference(value: Any) -> str:
        result = exact_string(value, "evidence reference", 256)
        if not result:
            fail("evidence reference must be non-empty")
        return result

    def artifact_digest(value: Any) -> str | None:
        if value is None:
            return None
        if type_of(value) is not string_type or digest_fullmatch(value) is None:
            fail("artifact digest must be lowercase 64-character SHA-256 hex")
        return value

    def source_employment(value: Any) -> EmploymentItemObservation:
        if type_of(value) is not source_employment_type:
            fail("employment must be an exact source observation")
        state = exact_state(value, employment_state_names, "employment")
        exact_string(state["employer_paye_reference"], "employer PAYE reference", 4096)
        number(state["tax_taken_off_pay"], "taxTakenOffPay")
        unknown_names(state["unknown_names"], "employment unknown names", employment_names)
        return value

    def source_benefits(value: Any) -> PensionsBenefitsObservation:
        if type_of(value) is not source_benefits_type:
            fail("pensions and benefits must be an exact source observation")
        state = exact_state(value, benefits_state_names, "pensions and benefits")
        present_fields, _ = presence(state["present_fields"], state["absent_fields"], benefits_names, "benefits")
        optional_number(state["other_pensions_and_retirement_annuities"], present_fields, "otherPensionsAndRetirementAnnuities")
        optional_number(state["incapacity_benefit"], present_fields, "incapacityBenefit")
        unknown_names(state["unknown_names"], "benefits unknown names", benefits_names)
        return value

    def source_refunds(value: Any) -> RefundsObservation:
        if type_of(value) is not source_refunds_type:
            fail("refunds must be an exact source observation")
        state = exact_state(value, refunds_state_names, "refunds")
        present_fields, _ = presence(state["present_fields"], state["absent_fields"], refund_names, "refunds")
        optional_number(state["tax_refunded_or_set_off"], present_fields, "taxRefundedOrSetOff")
        unknown_names(state["unknown_names"], "refund unknown names", refund_names)
        return value

    def source_summary(value: Any) -> IndividualTaxAnnualSummaryObservation:
        try:
            validated = source_validator(value)
        except source_exception_type:
            fail("source must be an exact fully validated success observation")
        if validated is not value or type_of(value) is not source_summary_type:
            fail("source validator returned an incoherent observation")
        state = exact_state(value, summary_state_names, "source observation")
        tax_year = state["tax_year"]
        if type_of(tax_year) is not string_type or tax_year_fullmatch(tax_year) is None:
            fail("source tax year is invalid")
        if type_of(state["completeness"]) is not string_type or state["completeness"] != completeness_value:
            fail("source completeness must be UNVERIFIED")
        employments = state["employments"]
        if type_of(employments) is not tuple_type or length(employments) > 10_000:
            fail("source employments must be a bounded exact tuple")
        for item in employments:
            source_employment(item)
        source_benefits(state["pensions_benefits"])
        source_refunds(state["refunds"])
        unknown_names(state["unknown_names"], "top-level unknown names", top_names)
        return value

    # These cells are populated after the four local classes are defined. All
    # construction and reconstruction security paths call these closure-held
    # validators directly; public ``_validate`` methods are compatibility
    # wrappers only and may be rebound without changing enforcement.
    employment_evidence_class: type | None = None
    benefits_evidence_class: type | None = None
    refund_evidence_class: type | None = None
    source_evidence_class: type | None = None

    def validate_employment_evidence(value: Any) -> None:
        if type_of(value) is not employment_evidence_class:
            fail("employment evidence must be an exact result type")
        exact_string(value.employer_paye_reference, "employer PAYE reference", 4096)
        number(value.tax_taken_off_pay, "taxTakenOffPay")
        unknown_names(value.unknown_names, "employment unknown names", employment_names)

    def validate_benefits_evidence(value: Any) -> None:
        if type_of(value) is not benefits_evidence_class:
            fail("pensions and benefits evidence must be an exact result type")
        present_fields, _ = presence(
            value.present_fields, value.absent_fields, benefits_names, "benefits"
        )
        optional_number(
            value.other_pensions_and_retirement_annuities,
            present_fields,
            "otherPensionsAndRetirementAnnuities",
        )
        optional_number(value.incapacity_benefit, present_fields, "incapacityBenefit")
        unknown_names(value.unknown_names, "benefits unknown names", benefits_names)

    def validate_refund_evidence(value: Any) -> None:
        if type_of(value) is not refund_evidence_class:
            fail("refund evidence must be an exact result type")
        present_fields, _ = presence(
            value.present_fields, value.absent_fields, refund_names, "refunds"
        )
        optional_number(
            value.tax_refunded_or_set_off, present_fields, "taxRefundedOrSetOff"
        )
        unknown_names(value.unknown_names, "refund unknown names", refund_names)

    def validate_source_evidence(value: Any) -> None:
        if type_of(value) is not source_evidence_class:
            fail("source evidence must be an exact result type")
        if type_of(value.source_api_name) is not string_type or value.source_api_name != api_name:
            fail("source API name is invalid")
        if type_of(value.source_api_version) is not string_type or value.source_api_version != api_version:
            fail("source API version is invalid")
        if type_of(value.tax_year) is not string_type or tax_year_fullmatch(value.tax_year) is None:
            fail("tax year is invalid")
        if type_of(value.employments) is not tuple_type or length(value.employments) > 10_000:
            fail("employments must be a bounded exact tuple")
        for item in value.employments:
            validate_employment_evidence(item)
        validate_benefits_evidence(value.pensions_benefits)
        validate_refund_evidence(value.refunds)
        unknown_names(value.top_level_unknown_names, "top-level unknown names", top_names)
        opaque_reference(value.evidence_reference)
        collection_time(value.collected_at)
        if type_of(value.completeness) is not string_type or value.completeness != completeness_value:
            fail("completeness must be UNVERIFIED")
        artifact_digest(value.source_artifact_sha256)

    @dataclass(frozen=True, slots=True, repr=False, init=False)
    class EmploymentEvidence:
        employer_paye_reference: str
        tax_taken_off_pay: int | Decimal
        unknown_names: frozenset[str]

        def __init__(self, employer_paye_reference: Any, tax_taken_off_pay: Any, unknown_names: Any) -> None:
            object_type.__setattr__(self, "employer_paye_reference", employer_paye_reference)
            object_type.__setattr__(self, "tax_taken_off_pay", tax_taken_off_pay)
            object_type.__setattr__(self, "unknown_names", unknown_names)
            validate_employment_evidence(self)

        def _validate(self) -> None:
            validate_employment_evidence(self)

        def __repr__(self) -> str:
            return "IndividualTaxEmploymentEvidence([REDACTED])"

        def __copy__(self):
            validate_employment_evidence(self)
            return self

        def __deepcopy__(self, memo: Any):
            validate_employment_evidence(self)
            return self

        def __reduce_ex__(self, protocol: int):
            validate_employment_evidence(self)
            return (
                EmploymentEvidence,
                (
                    self.employer_paye_reference,
                    self.tax_taken_off_pay,
                    self.unknown_names,
                ),
            )

    @dataclass(frozen=True, slots=True, repr=False, init=False)
    class BenefitsEvidence:
        other_pensions_and_retirement_annuities: int | Decimal | None
        incapacity_benefit: int | Decimal | None
        present_fields: frozenset[str]
        absent_fields: frozenset[str]
        unknown_names: frozenset[str]

        def __init__(self, other_pensions_and_retirement_annuities: Any, incapacity_benefit: Any, present_fields: Any, absent_fields: Any, unknown_names: Any) -> None:
            for name, value in (("other_pensions_and_retirement_annuities", other_pensions_and_retirement_annuities), ("incapacity_benefit", incapacity_benefit), ("present_fields", present_fields), ("absent_fields", absent_fields), ("unknown_names", unknown_names)):
                object_type.__setattr__(self, name, value)
            validate_benefits_evidence(self)

        def _validate(self) -> None:
            validate_benefits_evidence(self)

        def __repr__(self) -> str:
            return "IndividualTaxPensionsBenefitsEvidence([REDACTED])"

        def __copy__(self):
            validate_benefits_evidence(self)
            return self

        def __deepcopy__(self, memo: Any):
            validate_benefits_evidence(self)
            return self

        def __reduce_ex__(self, protocol: int):
            validate_benefits_evidence(self)
            return (
                BenefitsEvidence,
                (
                    self.other_pensions_and_retirement_annuities,
                    self.incapacity_benefit,
                    self.present_fields,
                    self.absent_fields,
                    self.unknown_names,
                ),
            )

    @dataclass(frozen=True, slots=True, repr=False, init=False)
    class RefundEvidence:
        tax_refunded_or_set_off: int | Decimal | None
        present_fields: frozenset[str]
        absent_fields: frozenset[str]
        unknown_names: frozenset[str]

        def __init__(self, tax_refunded_or_set_off: Any, present_fields: Any, absent_fields: Any, unknown_names: Any) -> None:
            for name, value in (("tax_refunded_or_set_off", tax_refunded_or_set_off), ("present_fields", present_fields), ("absent_fields", absent_fields), ("unknown_names", unknown_names)):
                object_type.__setattr__(self, name, value)
            validate_refund_evidence(self)

        def _validate(self) -> None:
            validate_refund_evidence(self)

        def __repr__(self) -> str:
            return "IndividualTaxRefundEvidence([REDACTED])"

        def __copy__(self):
            validate_refund_evidence(self)
            return self

        def __deepcopy__(self, memo: Any):
            validate_refund_evidence(self)
            return self

        def __reduce_ex__(self, protocol: int):
            validate_refund_evidence(self)
            return (
                RefundEvidence,
                (
                    self.tax_refunded_or_set_off,
                    self.present_fields,
                    self.absent_fields,
                    self.unknown_names,
                ),
            )

    @dataclass(frozen=True, slots=True, repr=False, init=False)
    class SourceEvidence:
        source_api_name: str
        source_api_version: str
        tax_year: str
        employments: tuple[EmploymentEvidence, ...]
        pensions_benefits: BenefitsEvidence
        refunds: RefundEvidence
        top_level_unknown_names: frozenset[str]
        evidence_reference: str
        collected_at: datetime
        completeness: str
        source_artifact_sha256: str | None

        def __init__(self, source_api_name: Any, source_api_version: Any, tax_year: Any, employments: Any, pensions_benefits: Any, refunds: Any, top_level_unknown_names: Any, evidence_reference: Any, collected_at: Any, completeness: Any, source_artifact_sha256: Any, **unsupported: Any) -> None:
            if unsupported:
                fail("evidence construction contains an unsupported field")
            for name, value in (("source_api_name", source_api_name), ("source_api_version", source_api_version), ("tax_year", tax_year), ("employments", employments), ("pensions_benefits", pensions_benefits), ("refunds", refunds), ("top_level_unknown_names", top_level_unknown_names), ("evidence_reference", evidence_reference), ("collected_at", collected_at), ("completeness", completeness), ("source_artifact_sha256", source_artifact_sha256)):
                object_type.__setattr__(self, name, value)
            validate_source_evidence(self)

        def _validate(self) -> None:
            validate_source_evidence(self)

        def __repr__(self) -> str:
            return "HMRCIndividualTaxSourceEvidence([REDACTED])"

        def __copy__(self):
            validate_source_evidence(self)
            return self

        def __deepcopy__(self, memo: Any):
            validate_source_evidence(self)
            return self

        def __reduce_ex__(self, protocol: int):
            validate_source_evidence(self)
            return (rebuild_source_evidence, ({
                "source_api_name": self.source_api_name,
                "source_api_version": self.source_api_version,
                "tax_year": self.tax_year,
                "employments": self.employments,
                "pensions_benefits": self.pensions_benefits,
                "refunds": self.refunds,
                "top_level_unknown_names": self.top_level_unknown_names,
                "evidence_reference": self.evidence_reference,
                "collected_at": self.collected_at,
                "completeness": self.completeness,
                "source_artifact_sha256": self.source_artifact_sha256,
            },))

    employment_evidence_class = EmploymentEvidence
    benefits_evidence_class = BenefitsEvidence
    refund_evidence_class = RefundEvidence
    source_evidence_class = SourceEvidence

    def rebuild_source_evidence(values: Any) -> SourceEvidence:
        if type_of(values) is not dict_type:
            fail("serialized evidence state is invalid")
        return SourceEvidence(**values)

    class Builder:
        __slots__ = ()

        def __call__(self, observation: Any, *, evidence_reference: Any, collected_at: Any, **options: Any) -> SourceEvidence:
            if set_type(options) - {"source_artifact_sha256"}:
                fail("builder received an unsupported option")
            source = source_summary(observation)
            exact_reference = opaque_reference(evidence_reference)
            exact_time = collection_time(collected_at)
            digest = None
            if "source_artifact_sha256" in options:
                supplied = options["source_artifact_sha256"]
                if supplied is None:
                    fail("an explicitly supplied artifact digest must not be None")
                digest = artifact_digest(supplied)
            employments = tuple_type(EmploymentEvidence(item.employer_paye_reference, item.tax_taken_off_pay, item.unknown_names) for item in source.employments)
            benefits = BenefitsEvidence(source.pensions_benefits.other_pensions_and_retirement_annuities, source.pensions_benefits.incapacity_benefit, source.pensions_benefits.present_fields, source.pensions_benefits.absent_fields, source.pensions_benefits.unknown_names)
            refunds = RefundEvidence(source.refunds.tax_refunded_or_set_off, source.refunds.present_fields, source.refunds.absent_fields, source.refunds.unknown_names)
            return SourceEvidence(api_name, api_version, source.tax_year, employments, benefits, refunds, source.unknown_names, exact_reference, exact_time, completeness_value, digest)

    return EmploymentEvidence, BenefitsEvidence, RefundEvidence, SourceEvidence, Builder(), rebuild_source_evidence


(
    IndividualTaxEmploymentEvidence,
    IndividualTaxPensionsBenefitsEvidence,
    IndividualTaxRefundEvidence,
    HMRCIndividualTaxSourceEvidence,
    build_hmrc_individual_tax_source_evidence,
    _rebuild_hmrc_individual_tax_source_evidence,
) = _create_source_evidence_api(
    source_validator=validate_individual_tax_annual_summary_observation,
    source_summary_type=IndividualTaxAnnualSummaryObservation,
    source_employment_type=EmploymentItemObservation,
    source_benefits_type=PensionsBenefitsObservation,
    source_refunds_type=RefundsObservation,
    error_type=HMRCIndividualTaxSourceEvidenceError,
    datetime_type=datetime, timezone_type=timezone, decimal_type=Decimal,
    integer_type=int, string_type=str, tuple_type=tuple, frozenset_type=frozenset,
    dict_type=dict, set_type=set, object_type=object, type_of=type, length=len, absolute=abs,
    maximum=max, unicode_category=unicodedata.category,
    tax_year_fullmatch=re.compile(r"[0-9]{4}-[0-9]{2}").fullmatch,
    digest_fullmatch=re.compile(r"[0-9a-f]{64}").fullmatch,
    api_name=HMRC_INDIVIDUAL_TAX_API_NAME,
    api_version=HMRC_INDIVIDUAL_TAX_API_VERSION,
    completeness_value=HMRC_INDIVIDUAL_TAX_COMPLETENESS,
    source_exception_type=Exception,
    attribute_error_type=AttributeError,
    type_error_type=TypeError,
)

for _name, _value in (
    ("IndividualTaxEmploymentEvidence", IndividualTaxEmploymentEvidence),
    ("IndividualTaxPensionsBenefitsEvidence", IndividualTaxPensionsBenefitsEvidence),
    ("IndividualTaxRefundEvidence", IndividualTaxRefundEvidence),
    ("HMRCIndividualTaxSourceEvidence", HMRCIndividualTaxSourceEvidence),
    ("_rebuild_hmrc_individual_tax_source_evidence", _rebuild_hmrc_individual_tax_source_evidence),
):
    _value.__module__ = __name__
    _value.__qualname__ = _name
