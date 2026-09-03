"""Pure HTML presentation for an issued customer MTD indication.

The supported renderer accepts only an exact live ``MtdScopeIndication`` and
projects it through the import-bound service projector. It validates the exact
approved mapping before rendering fixed customer copy. The template is loaded
once at import; request-time rendering performs no filesystem, network,
provider, persistence, logging, route or scheduling work.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import MappingProxyType

from jinja2 import Environment, FileSystemLoader, select_autoescape

from reserved.services.mtd_scope_indication import (
    CONTRACT_VERSION,
    FEATURE_LABEL,
    MtdScopeIndication,
    as_mtd_scope_mapping,
)


_SCHEMA = (
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

_COPY = (
    (
        "More information needed",
        "We cannot provide an indication until the relevant income and "
        "eligibility information is complete.",
        False,
    ),
    (
        "Worth reviewing",
        "Making Tax Digital may apply in a future tax year.",
        True,
    ),
    (
        "Not currently indicated",
        "Based on the information checked, this does not currently indicate "
        "that Making Tax Digital may apply from the future tax year shown. "
        "This is not a promise of exemption or future non-applicability.",
        True,
    ),
)

_GROSS_BASIS = "The threshold uses qualifying gross income before expenses."
_DETERMINATION_BASIS = (
    "This is a local planning indication, not HMRC's formal determination."
)

_INCLUDED_CATEGORIES = (
    "Self-employment",
    "UK property",
    "Foreign property",
)
_EXCLUDED_CATEGORIES = (
    "Employment income",
    "Dividend income",
    "Savings interest",
    "Other taxable income",
    "Capital gains",
)

# The generic model is also the exact rendering of the service's value-free
# incomplete projection. It contains no caller-controlled values.
_CLOSED_MODEL = (
    FEATURE_LABEL,
    _COPY[0][0],
    _COPY[0][1],
    _GROSS_BASIS,
    _DETERMINATION_BASIS,
    False,
    None,
    None,
    None,
    False,
    None,
    None,
    None,
    (),
    None,
    None,
    (),
    None,
)


def _bind_renderer(
    *,
    projector,
    indication_type,
    render_template,
    mapping_type,
    decimal_type,
    contract_version,
    feature_label,
    schema,
    copy_records,
    gross_basis,
    determination_basis,
    included_categories,
    excluded_categories,
    closed_model,
):
    """Snapshot the entire accepted projection and rendering vocabulary."""

    exact_type = type
    string_type = str
    integer_type = int
    boolean_type = bool
    tuple_type = tuple
    frozen_set_type = frozenset
    length = len
    all_values = all
    any_values = any
    format_value = format
    mapping_get = mapping_type.__getitem__
    caught_errors = (Exception,)
    zero = decimal_type("0")
    decimal_digits = frozen_set_type("0123456789")

    schema = tuple_type(schema)
    copies = tuple_type(
        (headline, summary, complete)
        for headline, summary, complete in copy_records
    )
    allowed_included = frozen_set_type(included_categories)
    allowed_excluded = frozen_set_type(excluded_categories)
    closed_model = tuple_type(closed_model)
    closed_html = render_template(model=closed_model)
    if exact_type(closed_html) is not string_type:
        raise TypeError("MTD refusal template did not return exact text")

    def exact_categories(value: object, allowed: frozenset[str]) -> bool:
        if exact_type(value) is not tuple_type:
            return False
        if any_values(exact_type(item) is not string_type for item in value):
            return False
        return (
            length(value) == length(frozen_set_type(value))
            and all_values(item in allowed for item in value)
        )

    def exact_count(value: object) -> bool:
        return exact_type(value) is integer_type and value >= 0

    def exact_tax_year(value: object) -> bool:
        if (
            exact_type(value) is not string_type
            or length(value) != 7
            or value[4] != "-"
            or any_values(
                character not in decimal_digits
                for character in value[:4] + value[5:]
            )
        ):
            return False
        return integer_type(value[5:]) == (integer_type(value[:4]) + 1) % 100

    def categories_match_count(categories: tuple[str, ...], count: int) -> bool:
        return (
            count >= length(categories)
            and ((count == 0 and categories == ()) or (count > 0 and categories != ()))
        )

    def exact_money(value: object, *, nonnegative: bool) -> bool:
        if exact_type(value) is not decimal_type or not value.is_finite():
            return False
        if value.as_tuple().exponent != -2:
            return False
        if value.is_zero() and value.is_signed():
            return False
        if not value.is_zero() and not -2 <= value.adjusted() <= 18:
            return False
        return not nonnegative or value >= zero

    def money_text(value: Decimal) -> str:
        if value < zero:
            return "-£" + format_value(-value, ",.2f")
        return "£" + format_value(value, ",.2f")

    def validated_model(value: object) -> tuple[object, ...] | None:
        if exact_type(value) is not indication_type:
            return None
        projection = projector(value)
        if exact_type(projection) is not mapping_type:
            return None
        keys = tuple_type(projection)
        if (
            any_values(exact_type(key) is not string_type for key in keys)
            or keys != schema
        ):
            return None
        values = tuple_type(mapping_get(projection, name) for name in schema)
        (
            actual_contract,
            actual_feature,
            headline,
            summary,
            actual_gross_basis,
            actual_determination_basis,
            assessment_year,
            mandatory_year,
            effective_start,
            qualifying_income,
            threshold,
            distance,
            included,
            included_count,
            business_count,
            excluded,
            excluded_count,
            information_complete,
            filing_action,
        ) = values

        for text, expected in (
            (actual_contract, contract_version),
            (actual_feature, feature_label),
            (actual_gross_basis, gross_basis),
            (actual_determination_basis, determination_basis),
        ):
            if exact_type(text) is not string_type or text != expected:
                return None
        if exact_type(headline) is not string_type or exact_type(summary) is not string_type:
            return None
        if exact_type(information_complete) is not boolean_type:
            return None
        if exact_type(filing_action) is not boolean_type or filing_action is not False:
            return None
        matched_copy = False
        for expected_headline, expected_summary, expected_complete in copies:
            if headline == expected_headline:
                if summary != expected_summary or information_complete is not expected_complete:
                    return None
                matched_copy = True
                break
        if not matched_copy:
            return None

        if not exact_categories(included, allowed_included):
            return None
        if not exact_categories(excluded, allowed_excluded):
            return None

        period_present = False
        if assessment_year is not None:
            if (
                not exact_tax_year(assessment_year)
                or not exact_tax_year(mandatory_year)
                or integer_type(mandatory_year[:4])
                <= integer_type(assessment_year[:4])
                or exact_type(effective_start) is not string_type
                or effective_start != mandatory_year[:4] + "-04-06"
            ):
                return None
            period_present = True
        elif mandatory_year is not None or effective_start is not None:
            return None

        if not period_present:
            if (
                information_complete is not False
                or headline != copies[0][0]
                or qualifying_income is not None
                or threshold is not None
                or distance is not None
                or included != ()
                or excluded != ()
                or included_count is not None
                or business_count is not None
                or excluded_count is not None
            ):
                return None
            return closed_model

        if (
            exact_type(threshold) is not decimal_type
            or not threshold.is_finite()
            or threshold <= zero
            or (threshold.is_zero() and threshold.is_signed())
            or not -2 <= threshold.as_tuple().exponent <= 0
            or threshold.adjusted() > 18
        ):
            return None
        if (
            not exact_count(included_count)
            or not exact_count(business_count)
            or not exact_count(excluded_count)
            or business_count != included_count
            or not categories_match_count(included, included_count)
            or not categories_match_count(excluded, excluded_count)
        ):
            return None

        if information_complete:
            if (
                not exact_money(qualifying_income, nonnegative=True)
                or not exact_money(distance, nonnegative=False)
                or (included_count == 0 and not qualifying_income.is_zero())
                or distance.as_tuple() != (threshold - qualifying_income).as_tuple()
            ):
                return None
            qualifying_text = money_text(qualifying_income)
            threshold_text = money_text(threshold)
            distance_text = money_text(distance)
        else:
            if qualifying_income is not None or distance is not None:
                return None
            qualifying_text = None
            threshold_text = None
            distance_text = None

        return (
            feature_label,
            headline,
            summary,
            gross_basis,
            determination_basis,
            True,
            assessment_year,
            mandatory_year,
            effective_start,
            information_complete,
            qualifying_text,
            threshold_text,
            distance_text,
            included,
            included_count,
            business_count,
            excluded,
            excluded_count,
        )

    def render_mtd_scope_indication(value: object) -> str:
        """Return approved deterministic HTML or one fixed generic refusal."""

        try:
            model = validated_model(value)
            if model is None:
                return closed_html
            rendered = render_template(model=model)
            return rendered if exact_type(rendered) is string_type else closed_html
        except caught_errors:
            return closed_html

    return render_mtd_scope_indication


_template_root = Path(__file__).resolve().parents[1] / "templates"
_environment = Environment(
    loader=FileSystemLoader(_template_root),
    autoescape=select_autoescape(("html",)),
)
_template = _environment.get_template("v2/_mtd_scope_indication.html")

render_mtd_scope_indication = _bind_renderer(
    projector=as_mtd_scope_mapping,
    indication_type=MtdScopeIndication,
    render_template=_template.render,
    mapping_type=type(MappingProxyType({})),
    decimal_type=Decimal,
    contract_version=CONTRACT_VERSION,
    feature_label=FEATURE_LABEL,
    schema=_SCHEMA,
    copy_records=_COPY,
    gross_basis=_GROSS_BASIS,
    determination_basis=_DETERMINATION_BASIS,
    included_categories=_INCLUDED_CATEGORIES,
    excluded_categories=_EXCLUDED_CATEGORIES,
    closed_model=_CLOSED_MODEL,
)
del _environment, _template, _template_root


__all__ = ("render_mtd_scope_indication",)
