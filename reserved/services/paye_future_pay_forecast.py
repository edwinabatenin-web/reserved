"""Pure composition of confirmed future-pay facts with reconciled PAYE evidence.

This module does not project salary, calculate payroll deductions or tax
liability, acquire provider data, persist state, or render customer copy.  It
accepts only explicit per-payment facts and a live producer-issued PAYE
reconciliation, then emits a detached immutable forecast candidate.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
import hashlib
import threading
import weakref

from reserved.engines.paye_reconciliation import (
    PayeReconciliation,
    project_paye_reconciliation,
)


class FuturePaySource(str, Enum):
    CUSTOMER_CONFIRMED = "customer_confirmed"
    CONFIRMED_SOURCE_DOCUMENT = "confirmed_source_document"


class FuturePayFrequency(str, Enum):
    ONE_OFF = "one_off"
    WEEKLY = "weekly"
    FORTNIGHTLY = "fortnightly"
    FOUR_WEEKLY = "four_weekly"
    MONTHLY = "monthly"


class PeriodCompleteness(str, Enum):
    COMPLETE = "complete"
    PARTIAL = "partial"


_RECONCILIATION_SCHEMA = (
    "tax_year", "tax_paid_to_date", "estimated_remaining_liability",
    "confidence", "selected_kind", "selected_observed_on", "conflicts",
    "warnings", "evidence_count", "selected_evidence", "considered_evidence",
    "estimated_remaining_liability_low", "estimated_remaining_liability_high",
    "calculation_status", "selected_evidence_ids", "selection_reasons",
    "tax_paid_known", "conservative_assumed_tax_paid", "apparent_overpayment",
    "range_completeness", "indeterminable_effect",
)

_EVIDENCE_SCHEMA = (
    "kind", "tax_year", "tax_paid_to_date", "gross_pay_to_date",
    "employment_id", "tax_code", "observed_on", "source_reference",
    "evidence_id", "representation", "completeness", "effective_through",
    "covered_employment_ids",
)


def _build_boundary(*, reconciliation_projector, reconciliation_type):
    exact_type = type
    string_type = str
    integer_type = int
    decimal_type = Decimal
    date_type = date
    tuple_type = tuple
    frozen_set_type = frozenset
    bool_type = bool
    none_type = type(None)
    source_type = FuturePaySource
    frequency_type = FuturePayFrequency
    completeness_type = PeriodCompleteness
    length = len
    any_values = any
    sorted_values = sorted
    sum_values = sum
    enumerate_values = enumerate
    zip_values = zip
    identity_of = id
    raw = object.__getattribute__
    new_instance = object.__new__
    make_ref = weakref.ref
    sha256 = hashlib.sha256
    encode_text = str.encode
    maximum = max
    format_value = format
    decimal_errors = (InvalidOperation, ValueError, TypeError, OverflowError)
    caught_errors = (Exception,)
    error_type = ValueError
    type_error = TypeError
    attribute_error = AttributeError
    zero = decimal_type("0.00")
    penny = decimal_type("0.01")
    maximum_amount = decimal_type("1000000000000000000.00")
    maximum_policy_days = 36_600
    maximum_fact_count = 10_000
    identifier_chars = frozen_set_type(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-"
    )
    identifier_initial = frozen_set_type(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    )
    hex_chars = frozen_set_type("0123456789abcdef")
    decimal_chars = frozen_set_type("0123456789")
    reconciliation_schema = tuple_type(_RECONCILIATION_SCHEMA)
    evidence_schema = tuple_type(_EVIDENCE_SCHEMA)
    uncertainty_literals = (
        "future_pay_is_confirmed_input_not_observed_payment",
        "expected_tax_deduction_is_explicit_input_not_payroll_calculation",
        "forecast_does_not_establish_final_tax_liability",
    )
    coverage_scope = "submitted_confirmed_periods_only"
    owner_business_authentication = (
        "not_established_requires_authenticated_orchestration"
    )
    customer_authority = "not_customer_authoritative"
    orchestration_requirement = (
        "authenticated_owner_business_reconciliation_binding_required"
    )
    source_literals = {
        source_type.CUSTOMER_CONFIRMED: "customer_confirmed",
        source_type.CONFIRMED_SOURCE_DOCUMENT: "confirmed_source_document",
    }
    frequency_literals = {
        frequency_type.ONE_OFF: "one_off",
        frequency_type.WEEKLY: "weekly",
        frequency_type.FORTNIGHTLY: "fortnightly",
        frequency_type.FOUR_WEEKLY: "four_weekly",
        frequency_type.MONTHLY: "monthly",
    }
    complete_period = completeness_type.COMPLETE

    def exact_identifier(value: object) -> str:
        if (
            exact_type(value) is not string_type
            or not 1 <= length(value) <= 128
            or value[0] not in identifier_initial
            or any_values(character not in identifier_chars for character in value)
        ):
            raise error_type("future-pay identifier is invalid")
        return value

    def exact_digest(value: object) -> str:
        if (
            exact_type(value) is not string_type
            or length(value) != 64
            or any_values(character not in hex_chars for character in value)
        ):
            raise error_type("future-pay source digest is invalid")
        return value

    def tax_year_bounds(value: object) -> tuple[str, date, date]:
        if exact_type(value) is not string_type:
            raise type_error("future-pay tax year must be an exact string")
        if (
            length(value) != 7
            or value[4] != "-"
            or any_values(character not in decimal_chars for character in value[:4] + value[5:])
        ):
            raise error_type("future-pay tax year must use ASCII YYYY-YY")
        start_year = integer_type(value[:4])
        if integer_type(value[5:]) != (start_year + 1) % 100:
            raise error_type("future-pay tax year is not consecutive")
        try:
            first = date_type(start_year, 4, 6)
            last = date_type(start_year + 1, 4, 5)
        except caught_errors:
            raise error_type("future-pay tax year is outside the supported date range") from None
        return value, first, last

    def exact_date(value: object, label: str) -> date:
        if exact_type(value) is not date_type:
            raise type_error(f"{label} must be an exact date")
        return value

    def exact_amount(value: object, label: str, *, allow_zero: bool) -> Decimal:
        value_type = exact_type(value)
        if value_type not in (decimal_type, string_type, integer_type):
            raise type_error(f"{label} must be an exact Decimal, string or integer")
        if value_type is string_type:
            if (
                not 1 <= length(value) <= 32
                or value != value.strip()
                or value.startswith("+")
                or "e" in value.lower()
                or value.count(".") > 1
                or any_values(
                    character not in decimal_chars and character != "."
                    for character in value
                )
            ):
                raise error_type(f"{label} is invalid")
            whole, dot, fraction = value.partition(".")
            if not whole or (dot and not 1 <= length(fraction) <= 2):
                raise error_type(f"{label} is invalid")
            if length(whole) > 1 and whole[0] == "0":
                raise error_type(f"{label} is ambiguous")
        try:
            parsed = decimal_type(value)
        except decimal_errors:
            raise error_type(f"{label} is invalid") from None
        if (
            not parsed.is_finite()
            or parsed.is_signed()
            or parsed.as_tuple().exponent < -2
            or parsed > maximum_amount
            or (not allow_zero and parsed == zero)
        ):
            raise error_type(f"{label} is outside the exact supported bound")
        return parsed.quantize(penny)

    def exact_money(value: object, label: str) -> Decimal:
        if (
            exact_type(value) is not decimal_type
            or not value.is_finite()
            or value.is_signed()
            or value.as_tuple().exponent != -2
            or value > maximum_amount
        ):
            raise error_type(f"{label} is not exact money")
        return value

    def scalar_fingerprint(value: object) -> tuple[object, ...]:
        value_type = exact_type(value)
        if value_type is decimal_type:
            return (decimal_type, value.as_tuple())
        if value_type is date_type:
            return (date_type, value.toordinal())
        if value_type is tuple_type:
            return (tuple_type, tuple_type(scalar_fingerprint(item) for item in value))
        if value_type in (none_type, string_type, integer_type, bool_type, source_type,
                          frequency_type, completeness_type):
            if value_type is source_type:
                return (source_type, source_literals[value])
            if value_type is frequency_type:
                return (frequency_type, frequency_literals[value])
            if value_type is completeness_type:
                return (
                    completeness_type,
                    "complete" if value is complete_period else "partial",
                )
            return (value_type, value)
        raise error_type("future-pay state contains an unsupported value")

    fact_registry: dict[int, tuple[weakref.ReferenceType[object], tuple[object, ...]]] = {}
    fact_lock = threading.RLock()

    @dataclass(frozen=True, slots=True, repr=False, weakref_slot=True)
    class ConfirmedFuturePayFact:
        source: FuturePaySource
        fact_id: str
        source_evidence_id: str
        source_evidence_digest: str
        owner_id: str
        business_id: str
        tax_year: str
        employment_id: str
        gross_pay: Decimal | str | int
        expected_tax_deduction: Decimal | str | int
        pay_date: date
        period_start: date
        period_end: date
        confirmed_on: date
        frequency: FuturePayFrequency
        period_completeness: PeriodCompleteness

        def __post_init__(self) -> None:
            key = identity_of(self)
            with fact_lock:
                retained = fact_registry.get(key)
                if retained is not None and retained[0]() is self:
                    raise error_type("future-pay fact cannot be re-issued")
            values = fact_components_unchecked(self)
            source, fact_id, source_id, source_digest, owner_id, business_id = values[:6]
            tax_year_value, employment_id, gross_pay, expected_tax = values[6:10]
            pay_date, period_start, period_end, confirmed_on, frequency, completeness = values[10:]
            if exact_type(source) is not source_type:
                raise type_error("future-pay source must use the exact enum")
            if exact_type(frequency) is not frequency_type:
                raise type_error("future-pay frequency must use the exact enum")
            if exact_type(completeness) is not completeness_type:
                raise type_error("future-pay period completeness must use the exact enum")
            tax_year, first, last = tax_year_bounds(tax_year_value)
            checked_pay_date = exact_date(pay_date, "future-pay pay_date")
            checked_start = exact_date(period_start, "future-pay period_start")
            checked_end = exact_date(period_end, "future-pay period_end")
            checked_confirmed = exact_date(confirmed_on, "future-pay confirmed_on")
            if not first <= checked_start <= checked_end <= last:
                raise error_type("future-pay period must fall wholly within its tax year")
            if not checked_end <= checked_pay_date <= last:
                raise error_type("future-pay date must follow its represented period")
            if checked_confirmed > checked_pay_date:
                raise error_type("future-pay confirmation cannot follow the payment date")
            checked_gross_pay = exact_amount(
                gross_pay, "future-pay gross pay", allow_zero=False
            )
            checked_expected_tax = exact_amount(
                expected_tax, "future-pay expected tax deduction", allow_zero=True
            )
            if checked_expected_tax > checked_gross_pay:
                raise error_type("future-pay expected tax deduction exceeds gross pay")
            checked = (
                source,
                exact_identifier(fact_id), exact_identifier(source_id), exact_digest(source_digest),
                exact_identifier(owner_id), exact_identifier(business_id), tax_year,
                exact_identifier(employment_id),
                checked_gross_pay, checked_expected_tax,
                checked_pay_date, checked_start, checked_end, checked_confirmed,
                frequency, completeness,
            )
            for descriptor, value in zip_values(fact_descriptors, checked, strict=True):
                descriptor.__set__(self, value)
            fingerprint = (tuple_type, tuple_type(scalar_fingerprint(item) for item in checked))

            def discard(reference, *, key=key):
                with fact_lock:
                    retained = fact_registry.get(key)
                    if retained is not None and retained[0] is reference:
                        fact_registry.pop(key, None)

            with fact_lock:
                fact_registry[key] = (make_ref(self, discard), fingerprint)

        def __repr__(self):
            validated_fact(self)
            return "ConfirmedFuturePayFact(validated=True)"

        def __copy__(self):
            validated_fact(self)
            return self

        def __deepcopy__(self, memo):
            validated_fact(self)
            return self

        def __reduce__(self):
            raise type_error("ConfirmedFuturePayFact cannot be pickled")

        def __reduce_ex__(self, protocol):
            raise type_error("ConfirmedFuturePayFact cannot be pickled")

    fact_type = ConfirmedFuturePayFact
    fact_field_names = tuple_type(field.name for field in fact_type.__dataclass_fields__.values())
    fact_namespace = raw(fact_type, "__dict__")
    fact_descriptors = tuple_type(
        exact_type(fact_namespace).__getitem__(fact_namespace, name) for name in fact_field_names
    )

    def fact_components_unchecked(value: object) -> tuple[object, ...]:
        return tuple_type(descriptor.__get__(value, fact_type) for descriptor in fact_descriptors)

    def validated_fact(value: object) -> tuple[object, ...]:
        if exact_type(value) is not fact_type:
            raise type_error("future-pay fact must use the exact validated type")
        values = fact_components_unchecked(value)
        fingerprint = (tuple_type, tuple_type(scalar_fingerprint(item) for item in values))
        with fact_lock:
            retained = fact_registry.get(identity_of(value))
            if retained is None or retained[0]() is not value or retained[1] != fingerprint:
                raise error_type("future-pay fact integrity validation failed")
        return values

    policy_registry: dict[int, tuple[weakref.ReferenceType[object], tuple[object, ...]]] = {}
    policy_lock = threading.RLock()

    class _PolicyMeta(type):
        def __call__(cls, *args, **kwargs):
            raise type_error("FuturePayForecastPolicy is factory-issued")

    class FuturePayForecastPolicy(metaclass=_PolicyMeta):
        __slots__ = ("max_confirmation_age_days", "material_tax_threshold", "__weakref__")

        def __new__(cls, *args, **kwargs):
            raise type_error("FuturePayForecastPolicy is factory-issued")

        def __setattr__(self, name, value):
            raise attribute_error("FuturePayForecastPolicy is immutable")

        def __delattr__(self, name):
            raise attribute_error("FuturePayForecastPolicy is immutable")

        def __repr__(self):
            validated_policy(self)
            return "FuturePayForecastPolicy(validated=True)"

        def __copy__(self):
            validated_policy(self)
            return self

        def __deepcopy__(self, memo):
            validated_policy(self)
            return self

        def __reduce__(self):
            raise type_error("FuturePayForecastPolicy cannot be pickled")

        def __reduce_ex__(self, protocol):
            raise type_error("FuturePayForecastPolicy cannot be pickled")

    policy_type = FuturePayForecastPolicy
    policy_namespace = raw(policy_type, "__dict__")
    days_descriptor = exact_type(policy_namespace).__getitem__(
        policy_namespace, "max_confirmation_age_days"
    )
    threshold_descriptor = exact_type(policy_namespace).__getitem__(
        policy_namespace, "material_tax_threshold"
    )

    def policy_components(value: object) -> tuple[object, object]:
        return (
            days_descriptor.__get__(value, policy_type),
            threshold_descriptor.__get__(value, policy_type),
        )

    def validated_policy(value: object) -> tuple[int, Decimal]:
        if exact_type(value) is not policy_type:
            raise type_error("future-pay forecast requires an exact issued policy")
        values = policy_components(value)
        fingerprint = (tuple_type, tuple_type(scalar_fingerprint(item) for item in values))
        with policy_lock:
            retained = policy_registry.get(identity_of(value))
            if retained is None or retained[0]() is not value or retained[1] != fingerprint:
                raise error_type("future-pay policy integrity validation failed")
        return values  # type: ignore[return-value]

    def make_future_pay_forecast_policy(*args, **kwargs):
        if length(args) != 2 or kwargs:
            raise type_error("future-pay policy factory requires exactly two positional inputs")
        days, threshold = args
        if exact_type(days) is not integer_type or not 0 <= days <= maximum_policy_days:
            raise error_type("future-pay confirmation-age threshold is outside the bounded range")
        exact_money(threshold, "future-pay materiality threshold")
        policy = new_instance(policy_type)
        days_descriptor.__set__(policy, days)
        threshold_descriptor.__set__(policy, threshold)
        values = (days, threshold)
        fingerprint = (tuple_type, tuple_type(scalar_fingerprint(item) for item in values))
        key = identity_of(policy)

        def discard(reference, *, key=key):
            with policy_lock:
                retained = policy_registry.get(key)
                if retained is not None and retained[0] is reference:
                    policy_registry.pop(key, None)

        with policy_lock:
            policy_registry[key] = (make_ref(policy, discard), fingerprint)
        return policy

    result_registry: dict[int, tuple[weakref.ReferenceType[object], tuple[object, ...]]] = {}
    result_lock = threading.RLock()

    class _CandidateMeta(type):
        def __call__(cls, *args, **kwargs):
            raise type_error("PayeFuturePayForecast is composer-issued")

    class PayeFuturePayForecast(metaclass=_CandidateMeta):
        __slots__ = ("__weakref__",)

        def __new__(cls, *args, **kwargs):
            raise type_error("PayeFuturePayForecast is composer-issued")

        def __setattr__(self, name, value):
            raise attribute_error("PayeFuturePayForecast is immutable")

        def __delattr__(self, name):
            raise attribute_error("PayeFuturePayForecast is immutable")

        def __repr__(self):
            validated_result(self)
            return "PayeFuturePayForecast(validated=True)"

        def __copy__(self):
            validated_result(self)
            return self

        def __deepcopy__(self, memo):
            validated_result(self)
            return self

        def __reduce__(self):
            raise type_error("PayeFuturePayForecast cannot be pickled")

        def __reduce_ex__(self, protocol):
            raise type_error("PayeFuturePayForecast cannot be pickled")

    result_type = PayeFuturePayForecast
    result_field_names = (
        "owner_id", "business_id", "tax_year", "as_of",
        "reconciliation_digest", "reconciliation_provenance",
        "reconciliation_effective_through", "reconciled_tax_paid_to_date",
        "expected_future_gross_pay", "expected_future_tax_deduction",
        "projected_tax_deducted_total", "fact_count", "expected_pay_dates",
        "source_provenance", "uncertainties", "material_tax_threshold",
        "material_threshold_reached", "forecast_status", "coverage_scope",
        "owner_business_authentication_status", "customer_authority_status",
        "orchestration_requirement",
    )

    def validated_result(value: object) -> tuple[object, ...]:
        if exact_type(value) is not result_type:
            raise type_error("future-pay forecast must use the exact issued type")
        with result_lock:
            retained = result_registry.get(identity_of(value))
            if retained is None or retained[0]() is not value:
                raise error_type("future-pay forecast is not producer-issued")
            values = retained[1]
        # Values are detached exact immutable primitives; validate on every read.
        tuple_type(scalar_fingerprint(item) for item in values)
        return values

    def issue_result(values: tuple[object, ...]):
        if exact_type(values) is not tuple_type or length(values) != length(result_field_names):
            raise error_type("future-pay forecast state is invalid")
        tuple_type(scalar_fingerprint(item) for item in values)
        result = new_instance(result_type)
        key = identity_of(result)

        def discard(reference, *, key=key):
            with result_lock:
                retained = result_registry.get(key)
                if retained is not None and retained[0] is reference:
                    result_registry.pop(key, None)

        with result_lock:
            result_registry[key] = (make_ref(result, discard), values)
        return result

    def encode_scalar(value: object) -> bytes:
        value_type = exact_type(value)
        if value_type is none_type:
            return b"n"
        if value_type is bool_type:
            return b"b1" if value else b"b0"
        if value_type is integer_type:
            return b"i" + encode_text(string_type(value), "ascii")
        if value_type is decimal_type:
            exact_money(value, "projected PAYE amount")
            return b"m" + encode_text(format_value(value, ".2f"), "ascii")
        if value_type is date_type:
            return b"d" + encode_text(value.isoformat(), "ascii")
        if value_type is string_type:
            encoded = encode_text(value, "utf-8")
            return b"s" + encode_text(string_type(length(encoded)), "ascii") + b":" + encoded
        if value_type is tuple_type:
            return b"t" + b"".join(
                encode_text(string_type(length(item)), "ascii") + b":" + item
                for item in (encode_scalar(member) for member in value)
            )
        raise error_type("projected PAYE state cannot be canonicalised")

    def exact_record(value: object, names: tuple[str, ...], label: str) -> tuple[object, ...]:
        if exact_type(value) is not tuple_type or length(value) != length(names):
            raise error_type(f"{label} schema is invalid")
        extracted = []
        for index, pair in enumerate_values(value):
            if (
                exact_type(pair) is not tuple_type
                or length(pair) != 2
                or exact_type(pair[0]) is not string_type
                or pair[0] != names[index]
            ):
                raise error_type(f"{label} schema is invalid")
            extracted.append(pair[1])
        return tuple_type(extracted)

    def compose_paye_future_pay_forecast(*args, **kwargs):
        required = ("owner_id", "business_id", "tax_year", "as_of", "policy")
        if length(args) != 2 or length(kwargs) != length(required):
            raise type_error(
                "future-pay composer requires reconciliation/facts and exact named binding inputs"
            )
        if any_values(exact_type(key) is not string_type or key not in required for key in kwargs):
            raise type_error("future-pay composer keyword shape is invalid")
        if any_values(name not in kwargs for name in required):
            raise type_error("future-pay composer keyword shape is invalid")
        reconciliation, facts = args
        if exact_type(reconciliation) is not reconciliation_type:
            raise type_error("future-pay composer requires an exact PAYE reconciliation")
        if exact_type(facts) is not tuple_type:
            raise type_error("future-pay facts must be one exact tuple")
        if not 1 <= length(facts) <= maximum_fact_count:
            raise error_type("future-pay facts count is outside the bounded range")

        owner_id = exact_identifier(kwargs["owner_id"])
        business_id = exact_identifier(kwargs["business_id"])
        tax_year, first, last = tax_year_bounds(kwargs["tax_year"])
        as_of = exact_date(kwargs["as_of"], "future-pay as_of")
        if not first <= as_of <= last:
            raise error_type("future-pay as_of must fall within its tax year")
        maximum_age, material_threshold = validated_policy(kwargs["policy"])

        try:
            projection = reconciliation_projector(reconciliation)
        except caught_errors:
            raise error_type("PAYE reconciliation validation failed") from None
        reconciliation_values = exact_record(
            projection, reconciliation_schema, "PAYE reconciliation projection"
        )
        if reconciliation_values[0] != tax_year:
            raise error_type("PAYE reconciliation tax year does not match forecast")
        if (
            reconciliation_values[13] != "calculated"
            or reconciliation_values[16] is not True
            or reconciliation_values[6] != ()
            or reconciliation_values[20] is not False
        ):
            raise error_type("PAYE reconciliation is incomplete, stale or ambiguous")
        reconciled_paid = exact_money(
            reconciliation_values[1], "reconciled PAYE tax paid"
        )
        selected = reconciliation_values[9]
        if exact_type(selected) is not tuple_type or not selected:
            raise error_type("PAYE reconciliation has no selected evidence")
        selected_period_ends = []
        selected_evidence_ids = []
        reconciliation_provenance = []
        for evidence_record in selected:
            evidence_values = exact_record(
                evidence_record, evidence_schema, "selected PAYE evidence"
            )
            if evidence_values[1] != tax_year:
                raise error_type("selected PAYE evidence tax year does not match forecast")
            selected_observed_on = exact_date(
                evidence_values[6], "selected PAYE evidence observation date"
            )
            selected_effective_through = exact_date(
                evidence_values[11], "selected PAYE evidence effective date"
            )
            if selected_effective_through > as_of:
                raise error_type("selected PAYE evidence effective period is after forecast date")
            if selected_observed_on > as_of:
                raise error_type("selected PAYE evidence observation is after forecast date")
            selected_period_ends.append(selected_effective_through)
            selected_evidence_ids.append(evidence_values[8])
            reconciliation_provenance.append((
                evidence_values[0], evidence_values[7], evidence_values[8],
                selected_observed_on, selected_effective_through,
            ))
        evidence_effective_through = maximum(selected_period_ends)
        reconciliation_provenance = tuple_type(sorted_values(
            reconciliation_provenance, key=lambda values: values[2]
        ))

        validated = tuple_type(validated_fact(item) for item in facts)
        fact_ids = tuple_type(values[1] for values in validated)
        evidence_ids = tuple_type(values[2] for values in validated)
        evidence_digests = tuple_type(values[3] for values in validated)
        if length(fact_ids) != length(frozen_set_type(fact_ids)):
            raise error_type("future-pay fact identifiers contain duplicates")
        if length(evidence_ids) != length(frozen_set_type(evidence_ids)):
            raise error_type("future-pay source evidence identifiers contain duplicates")
        if frozen_set_type(evidence_ids) & frozen_set_type(selected_evidence_ids):
            raise error_type(
                "future-pay source evidence identity collides with reconciled evidence"
            )
        if length(evidence_digests) != length(frozen_set_type(evidence_digests)):
            raise error_type("future-pay source evidence digests contain duplicates")
        semantic_keys = tuple_type(
            (values[7], values[10], values[11], values[12]) for values in validated
        )
        if length(semantic_keys) != length(frozen_set_type(semantic_keys)):
            raise error_type("future-pay facts contain duplicate represented payments")
        for left_index, left in enumerate_values(validated):
            for right in validated[left_index + 1:]:
                if (
                    left[7] == right[7]
                    and left[11] <= right[12]
                    and right[11] <= left[12]
                ):
                    raise error_type("future-pay facts contain overlapping represented periods")

        for values in validated:
            if values[4] != owner_id or values[5] != business_id or values[6] != tax_year:
                raise error_type("future-pay fact owner, business or tax year does not match")
            if values[9] > values[8]:
                raise error_type("future-pay expected tax deduction exceeds gross pay")
            if values[15] is not complete_period:
                raise error_type("future-pay fact represents a partial period")
            if values[10] <= as_of:
                raise error_type("future-pay payment must be after the forecast date")
            if values[11] <= evidence_effective_through:
                raise error_type("future-pay period overlaps reconciled PAYE evidence")
            if values[13] > as_of:
                raise error_type("future-pay fact was not confirmed by the forecast date")
            if (as_of - values[13]).days > maximum_age:
                raise error_type("future-pay fact confirmation is stale")

        ordered = tuple_type(sorted_values(
            validated, key=lambda values: (values[10], values[7], values[1])
        ))
        future_gross = sum_values((values[8] for values in ordered), zero).quantize(penny)
        future_tax = sum_values((values[9] for values in ordered), zero).quantize(penny)
        projected_total = (reconciled_paid + future_tax).quantize(penny)
        if (
            future_gross > maximum_amount
            or future_tax > maximum_amount
            or projected_total > maximum_amount
        ):
            raise error_type("future-pay forecast aggregate exceeds the supported bound")
        provenance = tuple_type(
            (
                values[1], values[2], values[3], source_literals[values[0]],
                values[7], values[10], values[11], values[12], frequency_literals[values[14]],
            )
            for values in ordered
        )
        reconciliation_digest = sha256(encode_scalar(projection)).hexdigest()
        return issue_result((
            owner_id, business_id, tax_year, as_of, reconciliation_digest,
            reconciliation_provenance, evidence_effective_through,
            reconciled_paid, future_gross, future_tax, projected_total, length(ordered),
            tuple_type(values[10] for values in ordered), provenance,
            uncertainty_literals, material_threshold, future_tax >= material_threshold,
            "confirmed_inputs_composed_not_observed", coverage_scope,
            owner_business_authentication, customer_authority,
            orchestration_requirement,
        ))

    def project_paye_future_pay_forecast(*args, **kwargs):
        if length(args) != 1 or kwargs:
            raise type_error("future-pay projector requires exactly one positional input")
        values = validated_result(args[0])
        return tuple_type(
            (name, values[index]) for index, name in enumerate_values(result_field_names)
        )

    return (
        ConfirmedFuturePayFact,
        FuturePayForecastPolicy,
        PayeFuturePayForecast,
        make_future_pay_forecast_policy,
        compose_paye_future_pay_forecast,
        project_paye_future_pay_forecast,
    )


(
    ConfirmedFuturePayFact,
    FuturePayForecastPolicy,
    PayeFuturePayForecast,
    make_future_pay_forecast_policy,
    compose_paye_future_pay_forecast,
    project_paye_future_pay_forecast,
) = _build_boundary(
    reconciliation_projector=project_paye_reconciliation,
    reconciliation_type=PayeReconciliation,
)
del _build_boundary


__all__ = (
    "ConfirmedFuturePayFact",
    "FuturePayForecastPolicy",
    "FuturePayFrequency",
    "FuturePaySource",
    "PayeFuturePayForecast",
    "PeriodCompleteness",
    "compose_paye_future_pay_forecast",
    "make_future_pay_forecast_policy",
    "project_paye_future_pay_forecast",
)
