"""Route-less customer-safe HTML for an issued PAYE reconciliation.

The live result is read only through the import-captured authoritative PAYE
projector.  The template is compiled once at import.  Rendering performs no
filesystem, network, provider, persistence, logging, route or action work.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType

from jinja2 import Environment, FileSystemLoader, select_autoescape

from reserved.engines.paye_reconciliation import (
    PayeReconciliation,
    project_paye_reconciliation,
)


_SCHEMA = (
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

_CONFLICT_SCHEMA = (
    "field", "selected_kind", "other_kind", "difference", "employment_id",
)

_FEATURE = "PAYE evidence check"
_CONFIDENCE_COPY = MappingProxyType({
    "high": "The evidence looks reliable.",
    "medium": "The evidence looks fairly reliable.",
    "low": "The evidence needs more information.",
    "incomplete": "The evidence needs more information.",
})
_STATUS_COPY = MappingProxyType({
    "calculated": (
        "PAYE evidence available",
        "We found usable evidence of tax deducted through PAYE.",
        "Calculated from usable evidence",
    ),
    "calculated_with_material_uncertainty": (
        "PAYE evidence needs review",
        "Some PAYE evidence may be incomplete, out of date or provisional.",
        "Calculated with material uncertainty",
    ),
    "conflict_requires_review": (
        "PAYE evidence needs review",
        "The PAYE evidence does not agree, so no single amount is shown.",
        "Conflicting evidence",
    ),
    "insufficient_facts": (
        "More information needed",
        "There is not enough PAYE evidence to show an amount.",
        "Insufficient evidence",
    ),
})
_SOURCE_COPY = MappingProxyType({
    "hmrc": "HMRC data",
    "document": "Document",
    "manual": "Customer-entered information",
    "bank_inference": "Bank-payment estimate",
})
_SOURCE_ORDER = ("hmrc", "document", "manual", "bank_inference")
_REPRESENTATIONS = frozenset((
    "employment_cumulative", "employments_aggregate_cumulative",
))
_COMPLETENESS = frozenset((
    "complete_for_representation", "partial", "unknown",
))
_SELECTION_REASONS = frozenset((
    "explicit aggregate coverage prevents double counting",
    "only usable direct evidence for represented scope",
))
_WARNINGS = frozenset((
    "No direct evidence of PAYE tax paid is available.",
    "Aggregate and employment evidence cannot be reconciled without matching identities and effective period.",
    "Aggregate and employment-level evidence were both supplied; the aggregate was used to avoid double counting.",
    "Aggregate PAYE evidence represents incompatible scopes.",
    "Conflicting PAYE evidence requires review; neither candidate was selected.",
    "Selected PAYE evidence may be out of date.",
    "Bank-payment inference is a last-resort estimate, not direct PAYE evidence.",
    "Apparent overpayment requires separate review; it is not a confirmed or available refund.",
))
_MONEY_EXPLANATION = (
    "These figures use the annual estimate supplied to us and tax currently "
    "evidenced as deducted. They are before future payroll deductions."
)
_PARTIAL_COPY = "The evidence may be out of date or may not cover the full period."
_BANK_COPY = "Direct PAYE evidence is needed before amounts can be shown."
_OVERPAYMENT_COPY = (
    "This possible difference is provisional and is not a confirmed or available refund."
)
_CLOSED_MODEL = (
    _FEATURE,
    "More information needed",
    "We cannot show this PAYE evidence summary safely. Please check the information and try again.",
    "The evidence needs more information.",
    "Unavailable",
    None,
    (),
    None,
    False,
    None,
    None,
    False,
    None,
    None,
    False,
    False,
    None,
)


def _bind_renderer(
    *, projector, result_type, render_template, decimal_type, date_type,
    schema, evidence_schema, conflict_schema, confidence_copy, status_copy,
    source_copy, source_order, representations, completeness,
    selection_reasons, warnings, closed_model, closed_html,
):
    """Capture the exact trusted projection, schema and fixed vocabulary."""

    exact_type = type
    string_type = str
    integer_type = int
    boolean_type = bool
    tuple_type = tuple
    frozen_set_type = frozenset
    none_type = type(None)
    length = len
    enumerate_values = enumerate
    all_values = all
    any_values = any
    sum_values = sum
    maximum = max
    sorted_values = sorted
    format_value = format
    caught_errors = (Exception,)
    zero = decimal_type("0.00")
    maximum_money = decimal_type("1000000000000000000.00")
    identifier_chars = frozen_set_type(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-"
    )
    identifier_initial = frozen_set_type(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    )
    decimal_chars = frozen_set_type("0123456789")
    tax_code_chars = frozen_set_type(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 /-"
    )
    schema = tuple_type(schema)
    evidence_schema = tuple_type(evidence_schema)
    conflict_schema = tuple_type(conflict_schema)
    allowed_confidence = MappingProxyType(dict(confidence_copy))
    allowed_status = MappingProxyType(dict(status_copy))
    allowed_sources = MappingProxyType(dict(source_copy))
    source_order = tuple_type(source_order)
    representations = frozen_set_type(representations)
    completeness = frozen_set_type(completeness)
    selection_reasons = frozen_set_type(selection_reasons)
    warnings = frozen_set_type(warnings)
    warning_order = (
        "No direct evidence of PAYE tax paid is available.",
        "Aggregate and employment evidence cannot be reconciled without matching identities and effective period.",
        "Aggregate and employment-level evidence were both supplied; the aggregate was used to avoid double counting.",
        "Aggregate PAYE evidence represents incompatible scopes.",
        "Conflicting PAYE evidence requires review; neither candidate was selected.",
        "Selected PAYE evidence may be out of date.",
        "Bank-payment inference is a last-resort estimate, not direct PAYE evidence.",
        "Apparent overpayment requires separate review; it is not a confirmed or available refund.",
    )
    warning_indexes = MappingProxyType(
        {text: index for index, text in enumerate_values(warning_order)}
    )
    completeness_priority = MappingProxyType({
        "unknown": 0, "partial": 1, "complete_for_representation": 2,
    })
    closed_model = tuple_type(closed_model)
    feature = closed_model[0]
    if exact_type(closed_html) is not string_type:
        raise TypeError("PAYE refusal template did not return exact text")

    def exact_record(value: object, names: tuple[str, ...]) -> tuple[object, ...] | None:
        if exact_type(value) is not tuple_type or length(value) != length(names):
            return None
        values = []
        for index, pair in enumerate_values(value):
            if (
                exact_type(pair) is not tuple_type
                or length(pair) != 2
                or exact_type(pair[0]) is not string_type
                or pair[0] != names[index]
            ):
                return None
            values.append(pair[1])
        return tuple_type(values)

    def exact_identifier(value: object, *, optional: bool = False) -> bool:
        if optional and value is None:
            return True
        return (
            exact_type(value) is string_type
            and 1 <= length(value) <= 128
            and value[0] in identifier_initial
            and all_values(character in identifier_chars for character in value)
        )

    def tax_year_bounds(value: object) -> tuple[object, object] | None:
        if (
            exact_type(value) is not string_type
            or length(value) != 7
            or value[4] != "-"
            or any_values(character not in decimal_chars for character in value[:4] + value[5:])
        ):
            return None
        start_year = integer_type(value[:4])
        if integer_type(value[5:]) != (start_year + 1) % 100:
            return None
        try:
            first = date_type(start_year, 4, 6)
            last = date_type(start_year + 1, 4, 5)
        except caught_errors:
            return None
        if exact_type(first) is not date_type or exact_type(last) is not date_type:
            return None
        return first, last

    def exact_money(value: object, *, optional: bool = False, positive: bool = False) -> bool:
        if optional and value is None:
            return True
        if (
            exact_type(value) is not decimal_type
            or not value.is_finite()
            or value.is_signed()
            or value.as_tuple().exponent != -2
            or value > maximum_money
        ):
            return False
        return not positive or value > zero

    def exact_strings(value: object, *, identifiers: bool = False) -> bool:
        if exact_type(value) is not tuple_type:
            return False
        if identifiers:
            return all_values(exact_identifier(item) for item in value)
        return all_values(exact_type(item) is string_type for item in value)

    def evidence_values(
        value: object, tax_year: str, first_day: object, last_day: object
    ) -> tuple[object, ...] | None:
        values = exact_record(value, evidence_schema)
        if values is None:
            return None
        (
            kind, evidence_year, tax_paid, gross_pay, employment_id, tax_code,
            observed_on, source_reference, evidence_id, representation,
            evidence_completeness, effective_through, covered_ids,
        ) = values
        if (
            exact_type(kind) is not string_type or kind not in allowed_sources
            or evidence_year != tax_year or exact_type(evidence_year) is not string_type
            or not exact_money(tax_paid, optional=True)
            or not exact_money(gross_pay, optional=True)
            or not exact_identifier(employment_id, optional=True)
            or not exact_identifier(source_reference, optional=True)
            or not exact_identifier(evidence_id)
            or exact_type(representation) is not string_type
            or representation not in representations
            or exact_type(evidence_completeness) is not string_type
            or evidence_completeness not in completeness
            or (tax_code is not None and (
                exact_type(tax_code) is not string_type
                or not 1 <= length(tax_code) <= 32
                or tax_code != tax_code.strip()
                or tax_code[0] not in identifier_initial
                or any_values(character not in tax_code_chars for character in tax_code)
            ))
            or (observed_on is not None and exact_type(observed_on) is not date_type)
            or (effective_through is not None and exact_type(effective_through) is not date_type)
            or not exact_strings(covered_ids, identifiers=True)
            or length(covered_ids) != length(frozen_set_type(covered_ids))
            or length(covered_ids) > 1_000
        ):
            return None
        if representation == "employment_cumulative":
            if employment_id is None or covered_ids != ():
                return None
        elif employment_id is not None or covered_ids == ():
            return None
        if effective_through is not None and not first_day <= effective_through <= last_day:
            return None
        if observed_on is not None and observed_on > last_day:
            return None
        if observed_on is not None and effective_through is not None and observed_on < effective_through:
            return None
        return values

    def conflict_values(value: object, considered_kinds: frozenset[str]) -> tuple[object, ...] | None:
        values = exact_record(value, conflict_schema)
        if values is None:
            return None
        field, selected_kind, other_kind, difference, employment_id = values
        if (
            exact_type(field) is not string_type or field != "tax_paid_to_date"
            or exact_type(selected_kind) is not string_type
            or exact_type(other_kind) is not string_type
            or selected_kind not in considered_kinds or other_kind not in considered_kinds
            or not exact_money(difference, positive=True)
            or not exact_identifier(employment_id, optional=True)
        ):
            return None
        return values

    def money_text(value: Decimal) -> str:
        return "£" + format_value(value, ",.2f")

    def valid_model(value: object) -> tuple[object, ...] | None:
        if exact_type(value) is not result_type:
            return None
        projection = projector(value)
        values = exact_record(projection, schema)
        if values is None:
            return None
        (
            tax_year, tax_paid, remaining, confidence, selected_kind,
            selected_observed_on, conflicts, raw_warnings, evidence_count,
            selected_evidence, considered_evidence, range_low, range_high,
            status, selected_ids, reasons, tax_paid_known, conservative_zero,
            apparent_overpayment, range_completeness, indeterminable_effect,
        ) = values
        bounds = tax_year_bounds(tax_year)
        if (
            bounds is None
            or exact_type(confidence) is not string_type or confidence not in allowed_confidence
            or exact_type(status) is not string_type or status not in allowed_status
            or (selected_kind is not None and (
                exact_type(selected_kind) is not string_type or selected_kind not in allowed_sources
            ))
            or (selected_observed_on is not None and exact_type(selected_observed_on) is not date_type)
            or exact_type(evidence_count) is not integer_type
            or not 0 <= evidence_count <= 10_000
            or exact_type(tax_paid_known) is not boolean_type
            or exact_type(indeterminable_effect) is not boolean_type
            or not exact_money(tax_paid, optional=True)
            or not exact_money(remaining, optional=True)
            or not exact_money(range_low, optional=True)
            or not exact_money(range_high, optional=True)
            or not exact_money(conservative_zero, optional=True)
            or not exact_money(apparent_overpayment, optional=True, positive=True)
            or (
                range_completeness is not None
                and exact_type(range_completeness) is not string_type
            )
            or range_completeness not in (
                None, "partial", "complete_for_identified_uncertainties"
            )
            or not exact_strings(raw_warnings)
            or length(raw_warnings) != length(frozen_set_type(raw_warnings))
            or any_values(item not in warnings for item in raw_warnings)
            or tuple_type(sorted_values(raw_warnings, key=lambda item: warning_indexes[item]))
            != raw_warnings
            or not exact_strings(selected_ids, identifiers=True)
            or not exact_strings(reasons)
            or any_values(item not in selection_reasons for item in reasons)
        ):
            return None

        if exact_type(considered_evidence) is not tuple_type or length(considered_evidence) != evidence_count:
            return None
        first_day, last_day = bounds
        considered = tuple_type(
            evidence_values(item, tax_year, first_day, last_day)
            for item in considered_evidence
        )
        if any_values(item is None for item in considered):
            return None
        evidence_ids = tuple_type(item[8] for item in considered)
        if length(evidence_ids) != length(frozen_set_type(evidence_ids)):
            return None
        if evidence_ids != tuple_type(sorted_values(evidence_ids)):
            return None
        considered_kinds = frozen_set_type(item[0] for item in considered)

        if exact_type(selected_evidence) is not tuple_type:
            return None
        selected = tuple_type(
            evidence_values(item, tax_year, first_day, last_day)
            for item in selected_evidence
        )
        if any_values(item is None for item in selected):
            return None
        if any_values(item not in considered for item in selected):
            return None
        if selected_ids != tuple_type(item[8] for item in selected) or length(reasons) != length(selected):
            return None
        if any_values(
            item[2] is None or item[6] is None or item[10] == "unknown" or item[11] is None
            for item in selected
        ):
            return None
        if length(selected) > 1 and tuple_type(
            (item[4] or "", item[8]) for item in selected
        ) != tuple_type(sorted_values((item[4] or "", item[8]) for item in selected)):
            return None

        if exact_type(conflicts) is not tuple_type or length(conflicts) > 10_000:
            return None
        checked_conflicts = tuple_type(conflict_values(item, considered_kinds) for item in conflicts)
        if any_values(item is None for item in checked_conflicts):
            return None
        if checked_conflicts != tuple_type(sorted_values(
            checked_conflicts,
            key=lambda item: (item[4] or "", item[0], item[1], item[2], item[3]),
        )):
            return None

        partial = range_completeness == "partial" or indeterminable_effect
        if (range_completeness == "partial") is not indeterminable_effect:
            return None
        bank_inference = any_values(item[0] == "bank_inference" for item in (
            selected if selected else considered
        ))

        if status in ("calculated", "calculated_with_material_uncertainty"):
            if (
                not tax_paid_known or not selected or conflicts != ()
                or not exact_money(tax_paid) or not exact_money(remaining)
                or selected_kind not in frozen_set_type(item[0] for item in selected)
                or selected_observed_on != maximum(item[6] for item in selected)
                or range_low is not None or range_high is not None
                or conservative_zero is not None
                or range_completeness not in (None, "partial")
            ):
                return None
            strongest = maximum(
                selected,
                key=lambda item: (
                    item[6] is not None,
                    item[6] or date_type.min,
                    sum_values(
                        fact is not None for fact in (item[2], item[3], item[5], item[7])
                    ) + completeness_priority[item[10]],
                    item[8],
                ),
            )
            if selected_kind != strongest[0]:
                return None
            minimum_confidence = "high"
            if any_values(item[0] == "bank_inference" for item in selected):
                minimum_confidence = "low"
            elif any_values(item[0] == "manual" for item in selected):
                minimum_confidence = "medium"
            if partial:
                minimum_confidence = {"high": "medium", "medium": "low", "low": "low"}[
                    minimum_confidence
                ]
            if confidence != minimum_confidence:
                return None
            if status == "calculated" and (partial or apparent_overpayment is not None):
                return None
            if status == "calculated_with_material_uncertainty" and not (
                partial or apparent_overpayment is not None
            ):
                return None
            if apparent_overpayment is not None and remaining != zero:
                return None
            stale_warning = "Selected PAYE evidence may be out of date." in raw_warnings
            bank_warning = (
                "Bank-payment inference is a last-resort estimate, not direct PAYE evidence."
                in raw_warnings
            )
            overpayment_warning = (
                "Apparent overpayment requires separate review; it is not a confirmed or available refund."
                in raw_warnings
            )
            if stale_warning is not partial:
                return None
            if bank_warning is not any_values(item[0] == "bank_inference" for item in selected):
                return None
            if overpayment_warning is not (apparent_overpayment is not None):
                return None
            show_point = not bank_inference
            show_range = False
        elif status == "conflict_requires_review":
            if (
                tax_paid_known or tax_paid is not None or remaining is not None
                or confidence != "incomplete" or selected_kind is not None
                or selected_observed_on is not None or not checked_conflicts
                or selected != () or selected_ids != () or reasons != ()
                or conservative_zero is not None or apparent_overpayment is not None
                or not exact_money(range_low) or not exact_money(range_high)
                or range_low > range_high
                or range_completeness not in ("partial", "complete_for_identified_uncertainties")
                or indeterminable_effect is (range_completeness == "complete_for_identified_uncertainties")
            ):
                return None
            if raw_warnings != (
                "Conflicting PAYE evidence requires review; neither candidate was selected.",
            ):
                return None
            show_point = False
            show_range = (
                not bank_inference
                and range_completeness == "complete_for_identified_uncertainties"
                and indeterminable_effect is False
            )
        else:
            if (
                status != "insufficient_facts" or tax_paid_known
                or tax_paid is not None or remaining is not None
                or confidence != "incomplete" or selected_kind is not None
                or selected_observed_on is not None or conflicts != ()
                or selected != () or selected_ids != () or reasons != ()
                or range_low is not None or range_high is not None
                or apparent_overpayment is not None
                or range_completeness != "partial" or indeterminable_effect is not True
                or (conservative_zero is not None and conservative_zero != zero)
            ):
                return None
            if raw_warnings not in (
                ("No direct evidence of PAYE tax paid is available.",),
                (
                    "Aggregate and employment evidence cannot be reconciled without matching identities and effective period.",
                ),
                ("Aggregate PAYE evidence represents incompatible scopes.",),
            ):
                return None
            show_point = False
            show_range = False

        source_kinds = frozen_set_type(item[0] for item in (selected if selected else considered))
        source_labels = tuple_type(
            allowed_sources[kind] for kind in source_order if kind in source_kinds
        )
        headline, summary, status_label = allowed_status[status]
        evidence_date = (
            date_type.isoformat(selected_observed_on)
            if selected_observed_on is not None else None
        )
        return (
            feature,
            headline,
            summary,
            allowed_confidence[confidence],
            status_label,
            tax_year,
            source_labels,
            evidence_date,
            show_point or show_range,
            money_text(tax_paid) if show_point else None,
            money_text(remaining) if show_point else None,
            show_range,
            money_text(range_low) if show_range else None,
            money_text(range_high) if show_range else None,
            partial,
            bank_inference,
            money_text(apparent_overpayment) if show_point and apparent_overpayment is not None else None,
        )

    def render_paye_reconciliation(value: object) -> str:
        try:
            model = valid_model(value)
            if model is None:
                return closed_html
            rendered = render_template(model=model)
            return rendered if exact_type(rendered) is string_type else closed_html
        except caught_errors:
            return closed_html

    return render_paye_reconciliation


_TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "templates"
_ENVIRONMENT = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_ROOT)),
    autoescape=select_autoescape(("html",)),
)
_TEMPLATE_RENDER = _ENVIRONMENT.get_template("v2/_paye_reconciliation.html").render
_CLOSED_HTML = _TEMPLATE_RENDER(model=_CLOSED_MODEL)

render_paye_reconciliation = _bind_renderer(
    projector=project_paye_reconciliation,
    result_type=PayeReconciliation,
    render_template=_TEMPLATE_RENDER,
    decimal_type=Decimal,
    date_type=date,
    schema=_SCHEMA,
    evidence_schema=_EVIDENCE_SCHEMA,
    conflict_schema=_CONFLICT_SCHEMA,
    confidence_copy=_CONFIDENCE_COPY,
    status_copy=_STATUS_COPY,
    source_copy=_SOURCE_COPY,
    source_order=_SOURCE_ORDER,
    representations=_REPRESENTATIONS,
    completeness=_COMPLETENESS,
    selection_reasons=_SELECTION_REASONS,
    warnings=_WARNINGS,
    closed_model=_CLOSED_MODEL,
    closed_html=_CLOSED_HTML,
)


__all__ = ("render_paye_reconciliation",)
