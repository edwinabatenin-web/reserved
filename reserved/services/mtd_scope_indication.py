"""Pure customer indication over the bounded MTD readiness engine.

The public operation owns one assess-and-present call. It validates explicit
completeness confirmations and detached exact ``IncomeSource`` inputs, invokes
the captured engine assessor, revalidates the complete ``MtdReadiness`` state
against the captured current rule set and only then issues an opaque customer
presentation handle. The supported output API is ``as_mtd_scope_mapping``.

It performs no network, provider, persistence, route, filing or payment work.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal, DecimalException, ROUND_HALF_UP
from types import MappingProxyType
import threading
import weakref

from reserved.engines import mtd_readiness as _engine


CONTRACT_VERSION = "reserved-mtd-scope-indication/1.0"
FEATURE_LABEL = "Could Making Tax Digital apply to you?"


@dataclass(frozen=True, slots=True)
class MtdScopeCompleteness:
    """Explicit support/completeness confirmations for one indication run.

    These booleans do not encode substantive residence, cessation or timing
    rules. ``True`` confirms supported circumstances and complete evidence.
    """

    supported_residence_circumstances: bool
    source_inventory_complete: bool
    source_assessment_timing_complete: bool
    cessation_facts_complete: bool
    current_year_annualisation_basis_complete: bool


def _build_boundary():
    # Capture the acceptance graph before public module names can be rebound.
    source_type = _engine.IncomeSource
    kind_type = _engine.IncomeKind
    readiness_type = _engine.MtdReadiness
    status_type = _engine.MtdStatus
    completeness_type = MtdScopeCompleteness
    assessor = _engine.assess_mtd_readiness
    engine_namespace = object.__getattribute__(_engine, "__dict__")

    exact_type = type
    raw = object.__getattribute__
    set_raw = object.__setattr__
    new_instance = object.__new__
    identity_of = id
    make_ref = weakref.ref
    dc_fields = fields
    decimal_type = Decimal
    string_type = str
    integer_type = int
    float_type = float
    boolean_type = bool
    tuple_type = tuple
    dict_type = dict
    dict_item = dict.__getitem__
    frozen_set = frozenset
    mapping_proxy = MappingProxyType
    stringify = str
    length = len
    all_values = all
    any_values = any
    set_type = set
    sum_values = sum
    zip_values = zip
    decimal_errors = (DecimalException, ValueError, TypeError, OverflowError)
    caught_errors = (Exception,)
    error_type = ValueError
    type_error = TypeError
    attribute_error = AttributeError
    hash_value = hash
    penny = decimal_type("0.01")
    approaching_ratio = decimal_type("0.80")
    zero = decimal_type("0")
    rounding = ROUND_HALF_UP

    source_fields = frozen_set(item.name for item in dc_fields(source_type))
    readiness_fields = frozen_set(item.name for item in dc_fields(readiness_type))
    completeness_fields = tuple_type(
        item.name for item in dc_fields(completeness_type)
    )
    completeness_namespace = raw(completeness_type, "__dict__")
    class_item = exact_type(completeness_namespace).__getitem__
    completeness_descriptors = tuple_type(
        (name, class_item(completeness_namespace, name))
        for name in completeness_fields
    )
    qualifying_kinds = frozen_set(_engine._QUALIFYING)
    decimal_digits = frozen_set("0123456789")

    def derive_effective_start(mandatory_from: object) -> str:
        if (
            exact_type(mandatory_from) is not string_type
            or length(mandatory_from) != 7
            or mandatory_from[4] != "-"
            or any_values(
                character not in decimal_digits
                for character in mandatory_from[:4] + mandatory_from[5:]
            )
        ):
            raise error_type("MTD mandatory tax year is invalid")
        first_year = integer_type(mandatory_from[:4])
        ending_year = integer_type(mandatory_from[5:])
        if ending_year != (first_year + 1) % 100:
            raise error_type("MTD mandatory tax year is incoherent")
        return mandatory_from[:4] + "-04-06"

    rule_records = tuple_type(
        (
            year,
            raw(rule, "mandatory_from_tax_year"),
            raw(rule, "threshold"),
            derive_effective_start(raw(rule, "mandatory_from_tax_year")),
        )
        for year, rule in _engine.MTD_THRESHOLD_RULES.items()
    )
    rule_by_year = {
        year: (mandatory_from, threshold, effective_start)
        for year, mandatory_from, threshold, effective_start in rule_records
    }
    supported_years = frozen_set(rule_by_year)

    not_in_scope = status_type.NOT_CURRENTLY_IN_SCOPE
    approaching = status_type.APPROACHING_MTD_THRESHOLD
    applies = status_type.MTD_APPLIES
    incomplete = status_type.MTD_DATA_INCOMPLETE
    allowed_statuses = frozen_set((not_in_scope, approaching, applies, incomplete))

    identifier_characters = frozen_set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-"
    )
    category_labels = {
        kind_type.SOLE_TRADE: "Self-employment",
        kind_type.UK_PROPERTY: "UK property",
        kind_type.FOREIGN_PROPERTY: "Foreign property",
        kind_type.PAYE_EMPLOYMENT: "Employment income",
        kind_type.DIVIDENDS: "Dividend income",
        kind_type.SAVINGS_INTEREST: "Savings interest",
        kind_type.OTHER_TAXABLE_INCOME: "Other taxable income",
        kind_type.CAPITAL_GAINS: "Capital gains",
    }
    known_kinds = frozen_set(category_labels)

    feature_label = FEATURE_LABEL
    contract_version = CONTRACT_VERSION
    more_information = "More information needed"
    worth_reviewing = "Worth reviewing"
    not_currently_indicated = "Not currently indicated"
    material_summary = "Making Tax Digital may apply in a future tax year."
    incomplete_summary = (
        "We cannot provide an indication until the relevant income and "
        "eligibility information is complete."
    )
    not_scope_summary = (
        "Based on the information checked, this does not currently indicate "
        "that Making Tax Digital may apply from the future tax year shown. "
        "This is not a promise of exemption or future non-applicability."
    )
    gross_basis = "The threshold uses qualifying gross income before expenses."
    determination_basis = (
        "This is a local planning indication, not HMRC's formal determination."
    )
    no_action = False
    missing_binding = object()
    engine_dependency_names = (
        "MTD_THRESHOLD_RULES",
        "_QUALIFYING",
        "_amount",
        "money",
        "MtdStatus",
        "MtdReadiness",
        "tuple",
        "all",
        "sum",
        "Decimal",
        "str",
        "dict",
    )
    engine_dependency_bindings = tuple_type(
        (name, engine_namespace.get(name, missing_binding))
        for name in engine_dependency_names
    )

    def engine_bindings_intact() -> bool:
        return all_values(
            engine_namespace.get(name, missing_binding) is expected
            for name, expected in engine_dependency_bindings
        )

    def exact_identifier(value: object) -> bool:
        return (
            exact_type(value) is string_type
            and 1 <= length(value) <= 160
            and all_values(character in identifier_characters for character in value)
        )

    def exact_optional_identifier(value: object) -> bool:
        return value is None or exact_identifier(value)

    def amount(value: object) -> Decimal | None:
        if value is None:
            return None
        value_type = exact_type(value)
        if value_type is boolean_type or value_type not in (
            decimal_type,
            string_type,
            integer_type,
            float_type,
        ):
            return None
        if value_type is string_type and (value == "" or value.strip() != value):
            return None
        try:
            parsed = decimal_type(stringify(value or 0)).quantize(
                penny, rounding=rounding
            )
        except decimal_errors:
            return None
        if not parsed.is_finite() or parsed < zero:
            return None
        return parsed

    def money(value: Decimal) -> Decimal:
        return value.quantize(penny, rounding=rounding)

    def validate_rules() -> bool:
        if exact_type(rule_records) is not tuple_type or length(rule_records) != 3:
            return False
        seen = set_type()
        for year, mandatory_from, threshold, effective_start in rule_records:
            if (
                exact_type(year) is not string_type
                or exact_type(mandatory_from) is not string_type
                or exact_type(threshold) is not decimal_type
                or not threshold.is_finite()
                or threshold <= zero
                or exact_type(effective_start) is not string_type
                or effective_start != derive_effective_start(mandatory_from)
                or year in seen
            ):
                return False
            seen.add(year)
        return True

    if not validate_rules():
        raise RuntimeError("MTD rule snapshot is invalid")

    def validate_completeness(candidate: object) -> None:
        if exact_type(candidate) is not completeness_type:
            raise type_error("MTD completeness facts are required")
        for _name, descriptor in completeness_descriptors:
            value = descriptor.__get__(candidate, completeness_type)
            if exact_type(value) is not boolean_type or value is not True:
                raise error_type("MTD completeness facts are not confirmed")

    def snapshot_sources(candidate: object) -> tuple[tuple[object, ...], tuple[object, ...]]:
        if exact_type(candidate) is not tuple_type:
            raise type_error("sources must be an exact tuple")
        detached = []
        components = []
        seen_source_ids = set_type()
        seen_business_ids = set_type()
        for source in candidate:
            if exact_type(source) is not source_type:
                raise type_error("source must be an exact IncomeSource")
            state = raw(source, "__dict__")
            if exact_type(state) is not dict_type or frozen_set(state) != source_fields:
                raise error_type("source state is invalid")
            source_id = dict_item(state, "source_id")
            kind = dict_item(state, "kind")
            gross_income = dict_item(state, "gross_income")
            business_id = dict_item(state, "business_id")
            complete = dict_item(state, "complete")
            if not exact_identifier(source_id) or source_id in seen_source_ids:
                raise error_type("source identity is invalid")
            if exact_type(kind) is not kind_type or kind not in known_kinds:
                raise error_type("source kind is invalid")
            parsed = amount(gross_income)
            if (
                gross_income is not None
                and not (exact_type(gross_income) is string_type and gross_income == "")
                and parsed is None
            ):
                raise error_type("source amount is invalid")
            if not exact_optional_identifier(business_id):
                raise error_type("business identity is invalid")
            if exact_type(complete) is not boolean_type:
                raise error_type("source completeness is invalid")
            if kind in qualifying_kinds:
                effective_business_id = business_id or source_id
                if effective_business_id in seen_business_ids:
                    raise error_type("qualifying business identity is duplicated")
                seen_business_ids.add(effective_business_id)
            seen_source_ids.add(source_id)
            detached_source = new_instance(source_type)
            set_raw(detached_source, "source_id", source_id)
            set_raw(detached_source, "kind", kind)
            set_raw(detached_source, "gross_income", gross_income)
            set_raw(detached_source, "business_id", business_id)
            set_raw(detached_source, "complete", complete)
            detached.append(detached_source)
            components.append(
                (source_id, kind, gross_income, parsed, business_id, complete)
            )
        return tuple_type(detached), tuple_type(components)

    def expected_result_components(
        components: tuple[tuple[object, ...], ...],
        assessment_year: str,
        registered: bool | None,
        exemption: bool | None,
    ) -> tuple[object, ...]:
        mandatory_from, threshold, _effective_start = rule_by_year[assessment_year]
        qualifying = tuple_type(item for item in components if item[1] in qualifying_kinds)
        excluded = tuple_type(item for item in components if item[1] not in qualifying_kinds)
        data_complete = all_values(item[5] and item[3] is not None for item in qualifying)
        qualifying_income = money(
            sum_values((item[3] or zero for item in qualifying), zero)
        )
        distance = money(threshold - qualifying_income)
        above = qualifying_income > threshold
        eligibility_complete = not above or (
            registered is not None and exemption is not None
        )
        if not data_complete or not eligibility_complete:
            status = incomplete
        elif above and exemption:
            status = not_in_scope
        elif above and registered:
            status = applies
        elif above:
            status = not_in_scope
        elif qualifying_income >= money(threshold * approaching_ratio):
            status = approaching
        else:
            status = not_in_scope
        source_ids = tuple_type(item[0] for item in qualifying)
        business_ids = tuple_type(item[4] or item[0] for item in qualifying)
        excluded_ids = tuple_type(item[0] for item in excluded)
        return (
            status,
            assessment_year,
            mandatory_from,
            qualifying_income,
            threshold,
            distance,
            source_ids,
            business_ids,
            excluded_ids,
            data_complete,
            eligibility_complete,
            exemption,
        )

    def readiness_components(value: object) -> tuple[object, ...]:
        if exact_type(value) is not readiness_type:
            raise type_error("assessment result type is invalid")
        state = raw(value, "__dict__")
        if exact_type(state) is not dict_type or frozen_set(state) != readiness_fields:
            raise error_type("assessment result state is invalid")
        status = dict_item(state, "status")
        assessment_year = dict_item(state, "assessment_tax_year")
        mandatory_from = dict_item(state, "mandatory_from_tax_year")
        qualifying_income = dict_item(state, "qualifying_income")
        threshold = dict_item(state, "threshold")
        distance = dict_item(state, "distance_from_threshold")
        qualifying_source_ids = dict_item(state, "qualifying_source_ids")
        qualifying_business_ids = dict_item(state, "qualifying_business_ids")
        excluded_source_ids = dict_item(state, "excluded_source_ids")
        data_complete = dict_item(state, "data_complete")
        eligibility_complete = dict_item(state, "eligibility_complete")
        exemption = dict_item(state, "exemption_applies")
        if exact_type(status) is not status_type or status not in allowed_statuses:
            raise error_type("assessment status is invalid")
        if (
            exact_type(assessment_year) is not string_type
            or assessment_year not in supported_years
            or exact_type(mandatory_from) is not string_type
        ):
            raise error_type("assessment period is invalid")
        for value_ in (qualifying_income, threshold, distance):
            if exact_type(value_) is not decimal_type or not value_.is_finite():
                raise error_type("assessment amount is invalid")
        if qualifying_income < zero or threshold <= zero:
            raise error_type("assessment amount is invalid")
        if (
            qualifying_income.as_tuple().exponent != -2
            or distance.as_tuple().exponent != -2
            or (qualifying_income.is_zero() and qualifying_income.is_signed())
            or (distance.is_zero() and distance.is_signed())
        ):
            raise error_type("assessment amount representation is invalid")
        expected_threshold = rule_by_year[assessment_year][1]
        if threshold.as_tuple() != expected_threshold.as_tuple():
            raise error_type("assessment threshold representation is invalid")
        for identities in (
            qualifying_source_ids,
            qualifying_business_ids,
            excluded_source_ids,
        ):
            if (
                exact_type(identities) is not tuple_type
                or any_values(not exact_identifier(item) for item in identities)
                or length(identities) != length(set_type(identities))
            ):
                raise error_type("assessment identities are invalid")
        if set_type(qualifying_source_ids) & set_type(excluded_source_ids):
            raise error_type("assessment identities overlap")
        if exact_type(data_complete) is not boolean_type:
            raise error_type("assessment completeness is invalid")
        if exact_type(eligibility_complete) is not boolean_type:
            raise error_type("assessment eligibility is invalid")
        if exemption is not None and exact_type(exemption) is not boolean_type:
            raise error_type("assessment exemption is invalid")
        return (
            status,
            assessment_year,
            mandatory_from,
            qualifying_income,
            threshold,
            distance,
            qualifying_source_ids,
            qualifying_business_ids,
            excluded_source_ids,
            data_complete,
            eligibility_complete,
            exemption,
        )

    presentation_field_names = (
        "contract_version",
        "feature_label",
        "headline",
        "summary",
        "gross_income_basis",
        "determination_basis",
        "assessment_tax_year",
        "mandatory_from_tax_year",
        "effective_start_date",
        "qualifying_income",
        "threshold",
        "distance_from_threshold",
        "included_source_categories",
        "included_source_count",
        "included_business_count",
        "excluded_source_categories",
        "excluded_source_count",
        "information_complete",
        "filing_action_available",
    )
    registry: dict[int, tuple[weakref.ReferenceType[object], tuple[object, ...]]] = {}
    lock = threading.RLock()

    class MtdScopeIndication:
        """Opaque process-local handle; project with ``as_mtd_scope_mapping``."""

        __slots__ = ("__weakref__",)

        def __new__(cls):
            raise type_error("MTD indication construction is private")

        def __setattr__(self, name: str, value: object) -> None:
            raise attribute_error("MtdScopeIndication is opaque and immutable")

        def __delattr__(self, name: str) -> None:
            raise attribute_error("MtdScopeIndication is opaque and immutable")

        def __copy__(self):
            validated_components(self)
            raise type_error("MtdScopeIndication cannot be copied")

        def __deepcopy__(self, memo):
            validated_components(self)
            raise type_error("MtdScopeIndication cannot be copied")

        def __reduce__(self):
            validated_components(self)
            raise type_error("MtdScopeIndication cannot be reconstructed")

        def __repr__(self) -> str:
            try:
                validated_components(self)
            except caught_errors:
                return "MtdScopeIndication(<invalid-handle>)"
            return "MtdScopeIndication(<validated-handle>)"

        def __eq__(self, other: object) -> bool:
            own = validated_components(self)
            if exact_type(other) is not presentation_type:
                return False
            return own == validated_components(other)

        def __hash__(self) -> int:
            return hash_value(validated_components(self))

    presentation_type = MtdScopeIndication

    def validated_components(value: object) -> tuple[object, ...]:
        if exact_type(value) is not presentation_type:
            raise type_error("MTD indication type is invalid")
        with lock:
            retained = registry.get(identity_of(value))
            if retained is None or retained[0]() is not value:
                raise error_type("MTD indication is not a valid live presentation")
            return retained[1]

    def issue(values: tuple[object, ...]):
        if exact_type(values) is not tuple_type or length(values) != length(
            presentation_field_names
        ):
            raise error_type("MTD indication projection is invalid")
        value = new_instance(presentation_type)
        key = identity_of(value)

        def discard(reference, *, key=key):
            with lock:
                current = registry.get(key)
                if current is not None and current[0] is reference:
                    registry.pop(key, None)

        with lock:
            registry[key] = (make_ref(value, discard), values)
        return value

    def as_mtd_scope_mapping(value: object):
        values = validated_components(value)
        return mapping_proxy(
            {
                name: projected
                for name, projected in zip_values(presentation_field_names, values)
            }
        )

    def generic_incomplete():
        return issue(
            (
                contract_version,
                feature_label,
                more_information,
                incomplete_summary,
                gross_basis,
                determination_basis,
                None,
                None,
                None,
                None,
                None,
                None,
                (),
                None,
                None,
                (),
                None,
                False,
                no_action,
            )
        )

    def unique_categories(items: tuple[tuple[object, ...], ...]) -> tuple[str, ...]:
        labels = []
        seen = set_type()
        for item in items:
            label = category_labels[item[1]]
            if label not in seen:
                seen.add(label)
                labels.append(label)
        return tuple_type(labels)

    def build_presentation(
        result: tuple[object, ...], components: tuple[tuple[object, ...], ...]
    ):
        (
            status,
            assessment_year,
            mandatory_from,
            qualifying_income,
            threshold,
            distance,
            _source_ids,
            business_ids,
            _excluded_ids,
            data_complete,
            eligibility_complete,
            exemption,
        ) = result
        information_complete = data_complete and eligibility_complete
        if not information_complete or status is incomplete:
            headline, summary = more_information, incomplete_summary
            safe_qualifying_income = None
            safe_distance = None
        else:
            material = (
                exemption is not True
                and qualifying_income >= money(threshold * approaching_ratio)
            )
            if material:
                headline, summary = worth_reviewing, material_summary
            else:
                headline, summary = not_currently_indicated, not_scope_summary
            safe_qualifying_income = qualifying_income
            safe_distance = distance
        qualifying = tuple_type(item for item in components if item[1] in qualifying_kinds)
        excluded = tuple_type(item for item in components if item[1] not in qualifying_kinds)
        effective_start = rule_by_year[assessment_year][2]
        return issue(
            (
                contract_version,
                feature_label,
                headline,
                summary,
                gross_basis,
                determination_basis,
                assessment_year,
                mandatory_from,
                effective_start,
                safe_qualifying_income,
                threshold,
                safe_distance,
                unique_categories(qualifying),
                length(qualifying),
                length(business_ids),
                unique_categories(excluded),
                length(excluded),
                information_complete,
                no_action,
            )
        )

    def present_mtd_scope_indication(
        sources: object,
        *,
        assessment_tax_year: object,
        completeness: object = None,
        registered_for_self_assessment: object = None,
        exemption_applies: object = None,
    ):
        try:
            if not engine_bindings_intact():
                return generic_incomplete()
            validate_completeness(completeness)
            if (
                exact_type(assessment_tax_year) is not string_type
                or assessment_tax_year not in supported_years
            ):
                return generic_incomplete()
            if registered_for_self_assessment is not None and (
                exact_type(registered_for_self_assessment) is not boolean_type
            ):
                return generic_incomplete()
            if exemption_applies is not None and (
                exact_type(exemption_applies) is not boolean_type
            ):
                return generic_incomplete()
            detached, components = snapshot_sources(sources)
            expected = expected_result_components(
                components,
                assessment_tax_year,
                registered_for_self_assessment,
                exemption_applies,
            )
            result = assessor(
                detached,
                assessment_tax_year=assessment_tax_year,
                registered_for_self_assessment=registered_for_self_assessment,
                exemption_applies=exemption_applies,
            )
            if not engine_bindings_intact():
                return generic_incomplete()
            actual = readiness_components(result)
            if actual[0] is not expected[0] or actual[1:] != expected[1:]:
                return generic_incomplete()
            return build_presentation(actual, components)
        except caught_errors:
            return generic_incomplete()

    return MtdScopeIndication, present_mtd_scope_indication, as_mtd_scope_mapping


MtdScopeIndication, present_mtd_scope_indication, as_mtd_scope_mapping = (
    _build_boundary()
)
del _build_boundary


__all__ = (
    "CONTRACT_VERSION",
    "FEATURE_LABEL",
    "MtdScopeCompleteness",
    "MtdScopeIndication",
    "as_mtd_scope_mapping",
    "present_mtd_scope_indication",
)
