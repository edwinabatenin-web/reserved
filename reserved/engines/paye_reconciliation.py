"""Validated, source-neutral PAYE evidence reconciliation.

This module performs no provider, transport, persistence, presentation or
forecasting work. Recency and conflict tolerances are required per-call policy
inputs, not embedded universal defaults.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
import threading
from types import MappingProxyType
from typing import Iterable
import weakref


class EvidenceKind(str, Enum):
    HMRC = "hmrc"
    DOCUMENT = "document"
    MANUAL = "manual"
    BANK_INFERENCE = "bank_inference"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INCOMPLETE = "incomplete"


class EvidenceRepresentation(str, Enum):
    EMPLOYMENT_CUMULATIVE = "employment_cumulative"
    EMPLOYMENTS_AGGREGATE_CUMULATIVE = "employments_aggregate_cumulative"


class Completeness(str, Enum):
    COMPLETE_FOR_REPRESENTATION = "complete_for_representation"
    PARTIAL = "partial"
    UNKNOWN = "unknown"


def _build_boundary():
    """Capture the complete validation, selection and issuance graph."""

    kind_type = EvidenceKind
    confidence_type = Confidence
    representation_type = EvidenceRepresentation
    completeness_type = Completeness
    decimal_type = Decimal
    date_type = date
    string_type = str
    integer_type = int
    boolean_type = bool
    tuple_type = tuple
    frozen_set_type = frozenset
    exact_type = type
    none_type = type(None)
    raw = object.__getattribute__
    set_raw = object.__setattr__
    new_instance = object.__new__
    identity_of = id
    make_ref = weakref.ref
    length = len
    all_values = all
    any_values = any
    sum_values = sum
    minimum = min
    maximum = max
    sorted_values = sorted
    absolute = abs
    enumerate_values = enumerate
    range_values = range
    decimal_errors = (InvalidOperation, ValueError, TypeError, OverflowError)
    error_type = ValueError
    type_error = TypeError
    attribute_error = AttributeError
    caught_errors = (Exception,)

    zero = decimal_type("0.00")
    penny = decimal_type("0.01")
    maximum_amount = decimal_type("1000000000000000000.00")
    maximum_policy_days = 36_600
    maximum_evidence_count = 10_000
    maximum_covered_employment_count = 1_000
    identifier_characters = frozen_set_type(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-"
    )
    identifier_initial = frozen_set_type(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    )
    tax_code_characters = frozen_set_type(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 /-"
    )
    decimal_characters = frozen_set_type("0123456789")

    confidence_priority = MappingProxyType(
        {
            confidence_type.INCOMPLETE: 0,
            confidence_type.LOW: 1,
            confidence_type.MEDIUM: 2,
            confidence_type.HIGH: 3,
        }
    )
    completeness_priority = MappingProxyType(
        {
            completeness_type.UNKNOWN: 0,
            completeness_type.PARTIAL: 1,
            completeness_type.COMPLETE_FOR_REPRESENTATION: 2,
        }
    )

    def exact_identifier(value: object, *, optional: bool = False) -> str | None:
        if optional and value is None:
            return None
        if (
            exact_type(value) is not string_type
            or not 1 <= length(value) <= 128
            or value[0] not in identifier_initial
            or any_values(character not in identifier_characters for character in value)
        ):
            raise error_type("PAYE evidence identifier is invalid")
        return value

    def exact_tax_code(value: object) -> str | None:
        if value is None:
            return None
        if (
            exact_type(value) is not string_type
            or not 1 <= length(value) <= 32
            or value != value.strip()
            or value[0] not in identifier_initial
            or any_values(character not in tax_code_characters for character in value)
        ):
            raise error_type("PAYE tax code is invalid")
        return value

    def tax_year_bounds(value: object) -> tuple[str, date, date]:
        if exact_type(value) is not string_type:
            raise type_error("PAYE tax year must be an exact string")
        if (
            length(value) != 7
            or value[4] != "-"
            or any_values(
                character not in decimal_characters
                for character in value[:4] + value[5:]
            )
        ):
            raise error_type("PAYE tax year must use ASCII YYYY-YY")
        start_year = integer_type(value[:4])
        if integer_type(value[5:]) != (start_year + 1) % 100:
            raise error_type("PAYE tax year end must immediately follow its start")
        try:
            first = date_type(start_year, 4, 6)
            last = date_type(start_year + 1, 4, 5)
        except caught_errors:
            raise error_type("PAYE tax year is outside the supported date range") from None
        return value, first, last

    def exact_optional_date(value: object) -> date | None:
        if value is None:
            return None
        if exact_type(value) is not date_type:
            raise type_error("PAYE evidence date must be an exact date")
        return value

    def normalise_amount(value: object, *, optional: bool) -> Decimal | None:
        if optional and value is None:
            return None
        value_type = exact_type(value)
        if value_type not in (decimal_type, string_type, integer_type):
            raise type_error("PAYE amount must be an exact Decimal, string or integer")
        if value_type is string_type:
            if (
                not 1 <= length(value) <= 32
                or value != value.strip()
                or value.startswith("+")
                or "e" in value.lower()
                or value.count(".") > 1
                or any_values(
                    character not in decimal_characters and character != "."
                    for character in value
                )
            ):
                raise error_type("PAYE amount string is invalid")
            whole, dot, fraction = value.partition(".")
            if not whole or (dot and not 1 <= length(fraction) <= 2):
                raise error_type("PAYE amount string is invalid")
            if length(whole) > 1 and whole[0] == "0":
                raise error_type("PAYE amount string is ambiguous")
        try:
            parsed = decimal_type(value)
        except decimal_errors:
            raise error_type("PAYE amount is invalid") from None
        if (
            not parsed.is_finite()
            or parsed.is_signed()
            or parsed.as_tuple().exponent < -2
            or parsed > maximum_amount
        ):
            raise error_type("PAYE amount is outside the exact supported bound")
        return parsed.quantize(penny)

    def exact_money(value: object, *, optional: bool = False) -> Decimal | None:
        if optional and value is None:
            return None
        if (
            exact_type(value) is not decimal_type
            or not value.is_finite()
            or value.is_signed()
            or value.as_tuple().exponent != -2
            or value > maximum_amount
        ):
            raise error_type("PAYE amount representation is invalid")
        return value

    def money(value: Decimal) -> Decimal:
        return value.quantize(penny)

    def exact_fingerprint(value: object) -> tuple[object, ...]:
        """Tag scalar and tuple state with its exact runtime representation."""

        value_type = exact_type(value)
        if value_type is none_type:
            return (none_type,)
        if value_type is decimal_type:
            return (decimal_type, value.as_tuple())
        if value_type is date_type:
            return (date_type, value.toordinal())
        if value_type is tuple_type:
            return (tuple_type, tuple_type(exact_fingerprint(item) for item in value))
        return (value_type, value)

    evidence_registry: dict[
        int, tuple[weakref.ReferenceType[object], tuple[object, ...]]
    ] = {}
    evidence_lock = threading.RLock()

    @dataclass(frozen=True, slots=True, repr=False, weakref_slot=True)
    class PayeEvidence:
        kind: EvidenceKind
        tax_year: str
        tax_paid_to_date: Decimal | str | int | None
        gross_pay_to_date: Decimal | str | int | None = None
        employment_id: str | None = None
        tax_code: str | None = None
        observed_on: date | None = None
        source_reference: str | None = None
        evidence_id: str | None = None
        representation: EvidenceRepresentation | None = None
        completeness: Completeness = completeness_type.UNKNOWN
        effective_through: date | None = None
        covered_employment_ids: tuple[str, ...] = ()

        def __post_init__(self) -> None:
            values = evidence_components_unchecked(self)
            kind, tax_year_value, tax_paid, gross_pay, employment_value, tax_code_value = values[:6]
            observed_value, source_value, evidence_value, representation_value = values[6:10]
            completeness_value, effective_value, covered = values[10:]
            if exact_type(kind) is not kind_type:
                raise type_error("PAYE evidence kind must use the exact enum")
            if exact_type(representation_value) is not representation_type:
                raise type_error("PAYE evidence representation must use the exact enum")
            if exact_type(completeness_value) is not completeness_type:
                raise type_error("PAYE evidence completeness must use the exact enum")
            tax_year, first, last = tax_year_bounds(tax_year_value)
            evidence_id = exact_identifier(evidence_value)
            employment_id = exact_identifier(employment_value, optional=True)
            source_reference = exact_identifier(source_value, optional=True)
            observed = exact_optional_date(observed_value)
            effective = exact_optional_date(effective_value)
            if effective is not None and not first <= effective <= last:
                raise error_type("PAYE effective date must fall within its tax year")
            if observed is not None and effective is not None and observed < effective:
                raise error_type("PAYE observation date cannot precede its effective date")
            if exact_type(covered) is not tuple_type:
                raise type_error("PAYE covered employment identities must be an exact tuple")
            if length(covered) > maximum_covered_employment_count:
                raise error_type("PAYE aggregate employment coverage exceeds the defensive bound")
            checked_covered = tuple_type(exact_identifier(item) for item in covered)
            if length(checked_covered) != length(frozen_set_type(checked_covered)):
                raise error_type("PAYE covered employment identities contain duplicates")
            if representation_value is representation_type.EMPLOYMENT_CUMULATIVE:
                if employment_id is None or checked_covered:
                    raise error_type("PAYE employment representation identity is incoherent")
            elif employment_id is not None or not checked_covered:
                raise error_type("PAYE aggregate representation coverage is incoherent")

            set_raw(self, "tax_year", tax_year)
            set_raw(self, "tax_paid_to_date", normalise_amount(tax_paid, optional=True))
            set_raw(self, "gross_pay_to_date", normalise_amount(gross_pay, optional=True))
            set_raw(self, "employment_id", employment_id)
            set_raw(self, "tax_code", exact_tax_code(tax_code_value))
            set_raw(self, "source_reference", source_reference)
            set_raw(self, "evidence_id", evidence_id)
            set_raw(self, "observed_on", observed)
            set_raw(self, "effective_through", effective)
            set_raw(self, "covered_employment_ids", checked_covered)

            values = evidence_components_unchecked(self)
            fingerprint = evidence_fingerprint(values)
            key = identity_of(self)

            def discard(reference, *, key=key):
                with evidence_lock:
                    retained = evidence_registry.get(key)
                    if retained is not None and retained[0] is reference:
                        evidence_registry.pop(key, None)

            with evidence_lock:
                evidence_registry[key] = (make_ref(self, discard), fingerprint)

        def __repr__(self) -> str:
            validated_evidence(self)
            return "PayeEvidence(validated=True)"

        def __getattribute__(self, name):
            return evidence_public_read(self, name)

        def __copy__(self):
            validated_evidence(self)
            return self

        def __deepcopy__(self, memo):
            validated_evidence(self)
            return self

        def __reduce__(self):
            raise type_error("PayeEvidence cannot be pickled")

        def __reduce_ex__(self, protocol):
            raise type_error("PayeEvidence cannot be pickled")

    evidence_type = PayeEvidence
    evidence_field_names = (
        "kind", "tax_year", "tax_paid_to_date", "gross_pay_to_date",
        "employment_id", "tax_code", "observed_on", "source_reference",
        "evidence_id", "representation", "completeness", "effective_through",
        "covered_employment_ids",
    )
    evidence_namespace = raw(evidence_type, "__dict__")
    evidence_descriptors = tuple_type(
        exact_type(evidence_namespace).__getitem__(evidence_namespace, name)
        for name in evidence_field_names
    )

    def evidence_components_unchecked(value: object) -> tuple[object, ...]:
        return tuple_type(
            descriptor.__get__(value, evidence_type)
            for descriptor in evidence_descriptors
        )

    def evidence_fingerprint(values: tuple[object, ...]) -> tuple[object, ...]:
        return (tuple_type, tuple_type(exact_fingerprint(value) for value in values))

    def validated_evidence(value: object) -> tuple[object, ...]:
        if exact_type(value) is not evidence_type:
            raise type_error("PAYE evidence must use the exact validated type")
        values = evidence_components_unchecked(value)
        with evidence_lock:
            retained = evidence_registry.get(identity_of(value))
            if (
                retained is None
                or retained[0]() is not value
                or retained[1] != evidence_fingerprint(values)
            ):
                raise error_type("PAYE evidence integrity validation failed")
        return values

    evidence_field_indexes = MappingProxyType(
        {name: index for index, name in enumerate_values(evidence_field_names)}
    )

    def evidence_public_read(value: object, name: object):
        if exact_type(name) is string_type and name in evidence_field_indexes:
            return validated_evidence(value)[evidence_field_indexes[name]]
        return raw(value, name)

    policy_registry: dict[
        int, tuple[weakref.ReferenceType[object], tuple[object, ...]]
    ] = {}
    policy_lock = threading.RLock()

    class _ExactPolicyMeta(type):
        def __call__(cls, *args, **kwargs):
            raise type_error(
                "PayeReconciliationPolicy is issued only by make_paye_reconciliation_policy"
            )

    class PayeReconciliationPolicy(metaclass=_ExactPolicyMeta):
        """Explicit provisional operating inputs; never universal defaults."""

        __slots__ = ("stale_after_days", "conflict_tolerance", "__weakref__")

        def __new__(cls, *args, **kwargs):
            raise type_error(
                "PayeReconciliationPolicy is issued only by make_paye_reconciliation_policy"
            )

        def __setattr__(self, name, value):
            raise attribute_error("PayeReconciliationPolicy is immutable")

        def __delattr__(self, name):
            raise attribute_error("PayeReconciliationPolicy is immutable")

        def __repr__(self):
            validated_policy(self)
            return "PayeReconciliationPolicy(validated=True)"

        def __getattribute__(self, name):
            return policy_public_read(self, name)

        def __copy__(self):
            validated_policy(self)
            return self

        def __deepcopy__(self, memo):
            validated_policy(self)
            return self

        def __reduce__(self):
            raise type_error("PayeReconciliationPolicy cannot be pickled")

        def __reduce_ex__(self, protocol):
            raise type_error("PayeReconciliationPolicy cannot be pickled")

        def __init_subclass__(cls, **kwargs):
            raise type_error("PayeReconciliationPolicy cannot be subclassed")

    policy_type = PayeReconciliationPolicy
    policy_namespace = raw(policy_type, "__dict__")
    policy_days_descriptor = exact_type(policy_namespace).__getitem__(
        policy_namespace, "stale_after_days"
    )
    policy_tolerance_descriptor = exact_type(policy_namespace).__getitem__(
        policy_namespace, "conflict_tolerance"
    )

    def policy_components_unchecked(value: object) -> tuple[object, object]:
        return (
            policy_days_descriptor.__get__(value, policy_type),
            policy_tolerance_descriptor.__get__(value, policy_type),
        )

    def policy_fingerprint(values: tuple[object, object]) -> tuple[object, ...]:
        return (tuple_type, tuple_type(exact_fingerprint(value) for value in values))

    def validated_policy(value: object) -> tuple[object, object]:
        if exact_type(value) is not policy_type:
            raise type_error("PAYE reconciliation requires an exact explicit policy")
        values = policy_components_unchecked(value)
        with policy_lock:
            retained = policy_registry.get(identity_of(value))
            if (
                retained is None
                or retained[0]() is not value
                or retained[1] != policy_fingerprint(values)
            ):
                raise error_type("PAYE reconciliation policy integrity validation failed")
        return values

    policy_field_indexes = MappingProxyType(
        {"stale_after_days": 0, "conflict_tolerance": 1}
    )

    def policy_public_read(value: object, name: object):
        if exact_type(name) is string_type and name in policy_field_indexes:
            return validated_policy(value)[policy_field_indexes[name]]
        return raw(value, name)

    def make_paye_reconciliation_policy(*args, **kwargs):
        """Issue one explicit policy from exactly two positional inputs."""

        if length(args) != 2 or kwargs:
            raise type_error(
                "make_paye_reconciliation_policy requires exactly two positional inputs"
            )
        days, tolerance = args
        if (
            exact_type(days) is not integer_type
            or not 0 <= days <= maximum_policy_days
        ):
            raise error_type("PAYE recency policy is outside the bounded range")
        if (
            exact_type(tolerance) is not decimal_type
            or not tolerance.is_finite()
            or tolerance.is_signed()
            or tolerance.as_tuple().exponent != -2
            or tolerance > maximum_amount
        ):
            raise error_type("PAYE conflict policy must be an exact bounded Decimal")

        policy = new_instance(policy_type)
        policy_days_descriptor.__set__(policy, days)
        policy_tolerance_descriptor.__set__(policy, tolerance)
        fingerprint = policy_fingerprint((days, tolerance))
        key = identity_of(policy)

        def discard(reference, *, key=key):
            with policy_lock:
                retained = policy_registry.get(key)
                if retained is not None and retained[0] is reference:
                    policy_registry.pop(key, None)

        with policy_lock:
            policy_registry[key] = (make_ref(policy, discard), fingerprint)
        return policy

    conflict_registry: dict[
        int, tuple[weakref.ReferenceType[object], tuple[object, ...]]
    ] = {}
    conflict_lock = threading.RLock()

    @dataclass(frozen=True, slots=True, repr=False, weakref_slot=True)
    class EvidenceConflict:
        field: str
        selected_kind: EvidenceKind
        other_kind: EvidenceKind
        difference: Decimal
        employment_id: str | None

        def __post_init__(self) -> None:
            components = conflict_components_unchecked(self)
            field, selected_kind, other_kind, difference, employment_id = components
            if exact_type(field) is not string_type or field != "tax_paid_to_date":
                raise error_type("PAYE conflict field is invalid")
            if exact_type(selected_kind) is not kind_type or exact_type(other_kind) is not kind_type:
                raise type_error("PAYE conflict kind is invalid")
            exact_money(difference)
            exact_identifier(employment_id, optional=True)

            fingerprint = conflict_values_fingerprint(components)
            key = identity_of(self)

            def discard(reference, *, key=key):
                with conflict_lock:
                    retained = conflict_registry.get(key)
                    if retained is not None and retained[0] is reference:
                        conflict_registry.pop(key, None)

            with conflict_lock:
                conflict_registry[key] = (make_ref(self, discard), fingerprint)

        def __repr__(self):
            validated_conflict(self)
            return "EvidenceConflict(validated=True)"

        def __getattribute__(self, name):
            return conflict_public_read(self, name)

        def __copy__(self):
            validated_conflict(self)
            return self

        def __deepcopy__(self, memo):
            validated_conflict(self)
            return self

        def __reduce__(self):
            raise type_error("EvidenceConflict cannot be pickled")

        def __reduce_ex__(self, protocol):
            raise type_error("EvidenceConflict cannot be pickled")

    conflict_type = EvidenceConflict
    conflict_namespace = raw(conflict_type, "__dict__")
    conflict_descriptors = tuple_type(
        exact_type(conflict_namespace).__getitem__(conflict_namespace, name)
        for name in ("field", "selected_kind", "other_kind", "difference", "employment_id")
    )

    def conflict_components_unchecked(value: object) -> tuple[object, ...]:
        return tuple_type(
            descriptor.__get__(value, conflict_type)
            for descriptor in conflict_descriptors
        )

    def conflict_values_fingerprint(values: tuple[object, ...]) -> tuple[object, ...]:
        return (tuple_type, tuple_type(exact_fingerprint(value) for value in values))

    def validated_conflict(value: object) -> tuple[object, ...]:
        if exact_type(value) is not conflict_type:
            raise error_type("PAYE conflict integrity validation failed")
        values = conflict_components_unchecked(value)
        with conflict_lock:
            retained = conflict_registry.get(identity_of(value))
            if (
                retained is None
                or retained[0]() is not value
                or retained[1] != conflict_values_fingerprint(values)
            ):
                raise error_type("PAYE conflict integrity validation failed")
        return values

    conflict_field_indexes = MappingProxyType(
        {
            "field": 0,
            "selected_kind": 1,
            "other_kind": 2,
            "difference": 3,
            "employment_id": 4,
        }
    )

    def conflict_public_read(value: object, name: object):
        if exact_type(name) is string_type and name in conflict_field_indexes:
            return validated_conflict(value)[conflict_field_indexes[name]]
        return raw(value, name)

    class _FrozenResultMeta(type):
        def __setattr__(cls, name, value):
            raise type_error("PayeReconciliation class is immutable")

        def __delattr__(cls, name):
            raise type_error("PayeReconciliation class is immutable")

    result_registry: dict[
        int, tuple[weakref.ReferenceType[object], tuple[object, ...], tuple[object, ...]]
    ] = {}
    result_lock = threading.RLock()

    class PayeReconciliation(metaclass=_FrozenResultMeta):
        __slots__ = ("__weakref__",)

        def __new__(cls, *args, **kwargs):
            raise type_error("PayeReconciliation cannot be constructed directly")

        def __setattr__(self, name, value):
            raise attribute_error("PayeReconciliation is immutable")

        def __delattr__(self, name):
            raise attribute_error("PayeReconciliation is immutable")

        def __repr__(self):
            validated_result_values(self)
            return "PayeReconciliation(validated=True)"

        def __getattribute__(self, name):
            return result_public_read(self, name)

        def __copy__(self):
            validated_result_values(self)
            return self

        def __deepcopy__(self, memo):
            validated_result_values(self)
            return self

        def __reduce__(self):
            raise type_error("PayeReconciliation cannot be pickled")

        def __reduce_ex__(self, protocol):
            raise type_error("PayeReconciliation cannot be pickled")

    result_type = PayeReconciliation
    result_field_names = (
        "tax_year", "tax_paid_to_date", "estimated_remaining_liability",
        "confidence", "selected_kind", "selected_observed_on", "conflicts",
        "warnings", "evidence_count", "selected_evidence", "considered_evidence",
        "estimated_remaining_liability_low", "estimated_remaining_liability_high",
        "calculation_status", "selected_evidence_ids", "selection_reasons",
        "tax_paid_known", "conservative_assumed_tax_paid", "apparent_overpayment",
        "range_completeness", "indeterminable_effect",
    )

    def conflict_fingerprint(value: object) -> tuple[object, ...]:
        return (conflict_type, conflict_values_fingerprint(validated_conflict(value)))

    def evidence_object_fingerprint(value: object) -> tuple[object, ...]:
        return (evidence_type, evidence_fingerprint(validated_evidence(value)))

    def result_fingerprint(values: tuple[object, ...]) -> tuple[object, ...]:
        fingerprints = []
        for index, value in enumerate_values(values):
            if index == 6:
                fingerprints.append((
                    exact_type(value),
                    tuple_type(conflict_fingerprint(item) for item in value),
                ))
            elif index in (9, 10):
                fingerprints.append((
                    exact_type(value),
                    tuple_type(evidence_object_fingerprint(item) for item in value),
                ))
            else:
                fingerprints.append(exact_fingerprint(value))
        return (tuple_type, tuple_type(fingerprints))

    def validated_result_values(value: object) -> tuple[object, ...]:
        if exact_type(value) is not result_type:
            raise type_error("PAYE reconciliation result type is invalid")
        with result_lock:
            retained = result_registry.get(identity_of(value))
            if retained is None or retained[0]() is not value:
                raise error_type("PAYE reconciliation result is not producer-issued")
            values, expected_fingerprint = retained[1], retained[2]
        if result_fingerprint(values) != expected_fingerprint:
            raise error_type("PAYE reconciliation result integrity validation failed")
        return values

    def result_property(index: int):
        def getter(value):
            return validated_result_values(value)[index]

        return property(getter)

    for field_index, field_name in enumerate_values(result_field_names):
        exact_type.__setattr__(result_type, field_name, result_property(field_index))

    result_field_indexes = MappingProxyType(
        {name: index for index, name in enumerate_values(result_field_names)}
    )

    def result_public_read(value: object, name: object):
        if exact_type(name) is string_type and name in result_field_indexes:
            return validated_result_values(value)[result_field_indexes[name]]
        return raw(value, name)

    kind_literals = MappingProxyType({
        kind_type.HMRC: "hmrc",
        kind_type.DOCUMENT: "document",
        kind_type.MANUAL: "manual",
        kind_type.BANK_INFERENCE: "bank_inference",
    })
    confidence_literals = MappingProxyType({
        confidence_type.HIGH: "high",
        confidence_type.MEDIUM: "medium",
        confidence_type.LOW: "low",
        confidence_type.INCOMPLETE: "incomplete",
    })
    representation_literals = MappingProxyType({
        representation_type.EMPLOYMENT_CUMULATIVE: "employment_cumulative",
        representation_type.EMPLOYMENTS_AGGREGATE_CUMULATIVE:
            "employments_aggregate_cumulative",
    })
    completeness_literals = MappingProxyType({
        completeness_type.COMPLETE_FOR_REPRESENTATION: "complete_for_representation",
        completeness_type.PARTIAL: "partial",
        completeness_type.UNKNOWN: "unknown",
    })

    def immutable_projection_value(value: object):
        value_type = exact_type(value)
        if value_type in (
            none_type, string_type, integer_type, boolean_type, decimal_type, date_type
        ):
            return value
        if value_type is tuple_type:
            return tuple_type(immutable_projection_value(item) for item in value)
        raise error_type("PAYE projected state contains an unsupported value")

    def evidence_projection(values: tuple[object, ...]) -> tuple[tuple[str, object], ...]:
        projected = (
            kind_literals[values[0]], values[1], values[2], values[3], values[4], values[5],
            values[6], values[7], values[8], representation_literals[values[9]],
            completeness_literals[values[10]], values[11], values[12],
        )
        return tuple_type(
            (name, immutable_projection_value(projected[index]))
            for index, name in enumerate_values(evidence_field_names)
        )

    conflict_field_names = (
        "field", "selected_kind", "other_kind", "difference", "employment_id"
    )

    def conflict_projection(values: tuple[object, ...]) -> tuple[tuple[str, object], ...]:
        projected = (
            values[0], kind_literals[values[1]], kind_literals[values[2]],
            values[3], values[4],
        )
        return tuple_type(
            (name, immutable_projection_value(projected[index]))
            for index, name in enumerate_values(conflict_field_names)
        )

    policy_field_names = ("stale_after_days", "conflict_tolerance")

    def policy_projection(values: tuple[object, ...]) -> tuple[tuple[str, object], ...]:
        return tuple_type(
            (name, immutable_projection_value(values[index]))
            for index, name in enumerate_values(policy_field_names)
        )

    def result_projection(values: tuple[object, ...]) -> tuple[tuple[str, object], ...]:
        projected = []
        for index, value in enumerate_values(values):
            if index == 3:
                safe_value = confidence_literals[value]
            elif index == 4:
                safe_value = None if value is None else kind_literals[value]
            elif index == 6:
                safe_value = tuple_type(
                    conflict_projection(validated_conflict(item)) for item in value
                )
            elif index in (9, 10):
                safe_value = tuple_type(
                    evidence_projection(validated_evidence(item)) for item in value
                )
            else:
                safe_value = immutable_projection_value(value)
            projected.append((result_field_names[index], safe_value))
        return tuple_type(projected)

    def project_paye_evidence(*args, **kwargs):
        if length(args) != 1 or kwargs:
            raise type_error("project_paye_evidence requires exactly one positional input")
        return evidence_projection(validated_evidence(args[0]))

    def project_paye_conflict(*args, **kwargs):
        if length(args) != 1 or kwargs:
            raise type_error("project_paye_conflict requires exactly one positional input")
        return conflict_projection(validated_conflict(args[0]))

    def project_paye_reconciliation_policy(*args, **kwargs):
        if length(args) != 1 or kwargs:
            raise type_error(
                "project_paye_reconciliation_policy requires exactly one positional input"
            )
        return policy_projection(validated_policy(args[0]))

    def project_paye_reconciliation(*args, **kwargs):
        if length(args) != 1 or kwargs:
            raise type_error("project_paye_reconciliation requires exactly one positional input")
        return result_projection(validated_result_values(args[0]))

    def issue_result(values: tuple[object, ...]):
        if exact_type(values) is not tuple_type or length(values) != length(result_field_names):
            raise error_type("PAYE reconciliation result state is invalid")
        fingerprint = result_fingerprint(values)
        result = new_instance(result_type)
        key = identity_of(result)

        def discard(reference, *, key=key):
            with result_lock:
                retained = result_registry.get(key)
                if retained is not None and retained[0] is reference:
                    result_registry.pop(key, None)

        with result_lock:
            result_registry[key] = (make_ref(result, discard), values, fingerprint)
        return result

    def confidence_for(kind: EvidenceKind) -> Confidence:
        if kind in (kind_type.HMRC, kind_type.DOCUMENT):
            return confidence_type.HIGH
        if kind is kind_type.MANUAL:
            return confidence_type.MEDIUM
        return confidence_type.LOW

    def reduce_confidence(value: Confidence) -> Confidence:
        if value is confidence_type.HIGH:
            return confidence_type.MEDIUM
        if value is confidence_type.MEDIUM:
            return confidence_type.LOW
        return value

    def completeness_score(values: tuple[object, ...]) -> int:
        fact_count = sum_values(
            item is not None for item in (values[2], values[3], values[5], values[7])
        )
        return fact_count + completeness_priority[values[10]]

    def selection_key(values: tuple[object, ...]):
        observed = values[6]
        return (
            observed is not None,
            observed or date_type.min,
            completeness_score(values),
            values[8],
        )

    def remaining_range(liability, aggregates, per_employment):
        possible_paid = [values[2] for values in aggregates if values[2] is not None]
        by_employment = {}
        for values in per_employment:
            if values[2] is not None:
                by_employment.setdefault(values[4], []).append(values[2])
        if by_employment:
            possible_paid.extend((
                sum_values((minimum(amounts) for amounts in by_employment.values()), zero),
                sum_values((maximum(amounts) for amounts in by_employment.values()), zero),
            ))
        if not possible_paid:
            return None, None
        low_paid, high_paid = minimum(possible_paid), maximum(possible_paid)
        return (
            money(maximum(zero, liability - high_paid)),
            money(maximum(zero, liability - low_paid)),
        )

    def reconcile_implementation(
        estimated_total_liability: object,
        evidence: Iterable[PayeEvidence],
        tax_year: object,
        as_of: object,
        policy: object,
    ) -> PayeReconciliation:
        """Reconcile one exact evidence tuple under one explicit policy."""

        liability = normalise_amount(estimated_total_liability, optional=False)
        tax_year, first_day, last_day = tax_year_bounds(tax_year)
        if exact_type(as_of) is not date_type:
            raise type_error("PAYE reconciliation as_of must be an exact date")
        if not first_day <= as_of <= last_day:
            raise error_type("PAYE reconciliation as_of must fall within tax_year")
        stale_after_days, conflict_tolerance = validated_policy(policy)
        if (
            exact_type(stale_after_days) is not integer_type
            or not 0 <= stale_after_days <= maximum_policy_days
            or exact_type(conflict_tolerance) is not decimal_type
            or not conflict_tolerance.is_finite()
            or conflict_tolerance.is_signed()
            or conflict_tolerance.as_tuple().exponent != -2
            or conflict_tolerance > maximum_amount
        ):
            raise error_type("PAYE reconciliation policy integrity validation failed")
        if exact_type(evidence) is not tuple_type:
            raise type_error("PAYE evidence must be one exact tuple")
        if length(evidence) > maximum_evidence_count:
            raise error_type("PAYE evidence tuple exceeds the defensive bound")

        supplied_pairs = tuple_type(
            (validated_evidence(item), item) for item in evidence
        )
        supplied_pairs = tuple_type(
            sorted_values(supplied_pairs, key=lambda pair: pair[0][8])
        )
        supplied = tuple_type(pair[0] for pair in supplied_pairs)
        supplied_objects = tuple_type(pair[1] for pair in supplied_pairs)
        if any_values(values[1] != tax_year for values in supplied):
            raise error_type("PAYE evidence contains mixed or mismatched tax years")
        evidence_ids = tuple_type(values[8] for values in supplied)
        if length(evidence_ids) != length(frozen_set_type(evidence_ids)):
            raise error_type("PAYE evidence identifiers contain duplicates")
        if any_values(values[6] is not None and values[6] > as_of for values in supplied):
            raise error_type("PAYE evidence observation date is after reconciliation date")

        usable_indexes = tuple_type(
            index for index, values in enumerate_values(supplied)
            if (
                values[2] is not None and values[6] is not None
                and values[10] is not completeness_type.UNKNOWN and values[11] is not None
            )
        )
        usable = tuple_type(supplied[index] for index in usable_indexes)
        usable_objects = tuple_type(supplied_objects[index] for index in usable_indexes)
        if not usable:
            return issue_result((
                tax_year, None, None, confidence_type.INCOMPLETE, None, None, (),
                ("No direct evidence of PAYE tax paid is available.",), length(supplied),
                (), supplied_objects, None, None, "insufficient_facts", (), (), False, zero, None,
                "partial", True,
            ))

        aggregate_indexes = tuple_type(
            index for index, values in enumerate_values(usable) if values[4] is None
        )
        employment_indexes = tuple_type(
            index for index, values in enumerate_values(usable) if values[4] is not None
        )
        aggregates = tuple_type(usable[index] for index in aggregate_indexes)
        aggregate_objects = tuple_type(usable_objects[index] for index in aggregate_indexes)
        per_employment = tuple_type(usable[index] for index in employment_indexes)
        per_employment_objects = tuple_type(usable_objects[index] for index in employment_indexes)
        employment_ids = frozen_set_type(values[4] for values in per_employment)
        linked_aggregate_indexes = tuple_type(
            index for index, values in enumerate_values(aggregates)
            if (
                employment_ids
                and frozen_set_type(values[12]) == employment_ids
                and all_values(
                    candidate[11] == values[11]
                    for candidate in per_employment if candidate[4] in values[12]
                )
            )
        )
        linked_aggregates = tuple_type(aggregates[index] for index in linked_aggregate_indexes)
        linked_aggregate_objects = tuple_type(
            aggregate_objects[index] for index in linked_aggregate_indexes
        )
        warnings = []

        if aggregates and per_employment and length(linked_aggregates) != length(aggregates):
            return issue_result((
                tax_year, None, None, confidence_type.INCOMPLETE, None, None, (),
                ("Aggregate and employment evidence cannot be reconciled without "
                 "matching identities and effective period.",),
                length(supplied), (), supplied_objects, None, None, "insufficient_facts",
                (), (), False, None, None, "partial", True,
            ))
        if linked_aggregates:
            selected_index = maximum(
                range_values(length(linked_aggregates)),
                key=lambda index: selection_key(linked_aggregates[index]),
            )
            selected_values = (linked_aggregates[selected_index],)
            selected_objects = (linked_aggregate_objects[selected_index],)
            warnings.append(
                "Aggregate and employment-level evidence were both supplied; "
                "the aggregate was used to avoid double counting."
            )
        elif aggregates and per_employment:
            return issue_result((
                tax_year, None, None, confidence_type.INCOMPLETE, None, None, (),
                ("Aggregate and employment evidence cannot be reconciled without "
                 "matching identities and effective period.",),
                length(supplied), (), supplied_objects, None, None, "insufficient_facts",
                (), (), False, None, None, "partial", True,
            ))
        elif aggregates:
            aggregate_scopes = frozen_set_type(
                (values[12], values[11]) for values in aggregates
            )
            if length(aggregate_scopes) != 1:
                return issue_result((
                    tax_year, None, None, confidence_type.INCOMPLETE, None, None, (),
                    ("Aggregate PAYE evidence represents incompatible scopes.",),
                    length(supplied), (), supplied_objects, None, None,
                    "insufficient_facts", (), (), False, None, None, "partial", True,
                ))
            selected_index = maximum(
                range_values(length(aggregates)),
                key=lambda index: selection_key(aggregates[index]),
            )
            selected_values = (aggregates[selected_index],)
            selected_objects = (aggregate_objects[selected_index],)
        else:
            selected_indexes_by_employment = {}
            for index, values in enumerate_values(per_employment):
                employment_id = values[4]
                existing = selected_indexes_by_employment.get(employment_id)
                if existing is None or selection_key(values) > selection_key(per_employment[existing]):
                    selected_indexes_by_employment[employment_id] = index
            selected_indexes = tuple_type(sorted_values(
                selected_indexes_by_employment.values(),
                key=lambda index: (per_employment[index][4], per_employment[index][8]),
            ))
            selected_values = tuple_type(per_employment[index] for index in selected_indexes)
            selected_objects = tuple_type(per_employment_objects[index] for index in selected_indexes)

        conflicts = []
        for selected in selected_values:
            comparable = (
                aggregates if selected[4] is None else
                tuple_type(values for values in per_employment if values[4] == selected[4])
            )
            for other in comparable:
                if other is selected:
                    continue
                difference = money(absolute(selected[2] - other[2]))
                if difference > conflict_tolerance:
                    conflicts.append(conflict_type(
                        "tax_paid_to_date", selected[0], other[0], difference, selected[4]
                    ))

        if linked_aggregates:
            selected_employment_values = []
            for employment_id in sorted_values(employment_ids):
                candidates = tuple_type(
                    values for values in per_employment if values[4] == employment_id
                )
                representative = maximum(candidates, key=selection_key)
                selected_employment_values.append(representative)
                for other in candidates:
                    if other is representative:
                        continue
                    candidate_difference = money(
                        absolute(representative[2] - other[2])
                    )
                    if candidate_difference > conflict_tolerance:
                        conflicts.append(conflict_type(
                            "tax_paid_to_date", representative[0], other[0],
                            candidate_difference, employment_id,
                        ))
            employment_total = money(sum_values(
                (values[2] for values in selected_employment_values), zero
            ))
            difference = money(absolute(selected_values[0][2] - employment_total))
            if difference > conflict_tolerance:
                conflicts.append(conflict_type(
                    "tax_paid_to_date", selected_values[0][0], per_employment[0][0],
                    difference, None,
                ))

        if conflicts:
            conflicts = sorted_values(
                conflicts,
                key=lambda conflict: (
                    validated_conflict(conflict)[4] or "",
                    validated_conflict(conflict)[0],
                    validated_conflict(conflict)[1].value,
                    validated_conflict(conflict)[2].value,
                    validated_conflict(conflict)[3],
                ),
            )
            range_low, range_high = remaining_range(liability, aggregates, per_employment)
            stale_conflict = any_values(
                (as_of - values[6]).days > stale_after_days
                or (as_of - values[11]).days > stale_after_days
                for values in usable
            )
            return issue_result((
                tax_year, None, None, confidence_type.INCOMPLETE, None, None,
                tuple_type(conflicts),
                ("Conflicting PAYE evidence requires review; neither candidate was selected.",),
                length(supplied), (), supplied_objects, range_low, range_high,
                "conflict_requires_review", (), (), False, None, None,
                "partial" if stale_conflict else "complete_for_identified_uncertainties",
                stale_conflict,
            ))

        tax_paid = money(sum_values((values[2] for values in selected_values), zero))
        remaining = money(maximum(zero, liability - tax_paid))
        confidence = minimum(
            (confidence_for(values[0]) for values in selected_values),
            key=lambda value: confidence_priority[value],
        )
        stale = any_values(
            (as_of - values[6]).days > stale_after_days
            or (as_of - values[11]).days > stale_after_days
            for values in selected_values
        )
        if stale:
            warnings.append("Selected PAYE evidence may be out of date.")
            confidence = reduce_confidence(confidence)
        if any_values(values[0] is kind_type.BANK_INFERENCE for values in selected_values):
            warnings.append(
                "Bank-payment inference is a last-resort estimate, not direct PAYE evidence."
            )

        strongest = maximum(selected_values, key=selection_key)
        latest = maximum(values[6] for values in selected_values)
        apparent_overpayment = money(maximum(zero, tax_paid - liability)) or None
        if apparent_overpayment is not None:
            warnings.append(
                "Apparent overpayment requires separate review; it is not a "
                "confirmed or available refund."
            )
        linked_object_ids = frozen_set_type(identity_of(item) for item in linked_aggregate_objects)
        selection_reasons = tuple_type(
            "explicit aggregate coverage prevents double counting"
            if identity_of(item) in linked_object_ids
            else "only usable direct evidence for represented scope"
            for item in selected_objects
        )
        materially_uncertain = stale or apparent_overpayment is not None
        return issue_result((
            tax_year, tax_paid, remaining, confidence, strongest[0], latest, (),
            tuple_type(warnings), length(supplied), selected_objects, supplied_objects,
            None, None,
            "calculated_with_material_uncertainty" if materially_uncertain else "calculated",
            tuple_type(values[8] for values in selected_values), selection_reasons,
            True, None, apparent_overpayment, "partial" if stale else None, stale,
        ))

    def reconcile_paye(*args, **kwargs):
        """Require two positional facts and all three explicit named controls."""

        required = ("tax_year", "as_of", "policy")
        if length(args) != 2 or length(kwargs) != 3:
            raise type_error(
                "reconcile_paye requires two positional inputs and exact tax_year/as_of/policy keywords"
            )
        if any_values(
            exact_type(key) is not string_type or key not in required for key in kwargs
        ) or any_values(name not in kwargs for name in required):
            raise type_error("reconcile_paye keyword shape is invalid")
        return reconcile_implementation(
            args[0], args[1], kwargs["tax_year"], kwargs["as_of"], kwargs["policy"]
        )

    return (
        PayeEvidence, PayeReconciliationPolicy, EvidenceConflict,
        PayeReconciliation, make_paye_reconciliation_policy,
        project_paye_evidence, project_paye_conflict,
        project_paye_reconciliation_policy, project_paye_reconciliation,
        reconcile_paye,
    )


(
    PayeEvidence,
    PayeReconciliationPolicy,
    EvidenceConflict,
    PayeReconciliation,
    make_paye_reconciliation_policy,
    project_paye_evidence,
    project_paye_conflict,
    project_paye_reconciliation_policy,
    project_paye_reconciliation,
    reconcile_paye,
) = _build_boundary()
del _build_boundary


__all__ = (
    "Completeness",
    "Confidence",
    "EvidenceConflict",
    "EvidenceKind",
    "EvidenceRepresentation",
    "PayeEvidence",
    "PayeReconciliation",
    "PayeReconciliationPolicy",
    "make_paye_reconciliation_policy",
    "project_paye_conflict",
    "project_paye_evidence",
    "project_paye_reconciliation",
    "project_paye_reconciliation_policy",
    "reconcile_paye",
)
