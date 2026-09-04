"""Adversarial acceptance for the customer MTD indication HTML renderer."""

from __future__ import annotations

import ast
import builtins
from decimal import Decimal
from html.parser import HTMLParser
import inspect
from pathlib import Path
from types import MappingProxyType

from jinja2 import Environment, FileSystemLoader, select_autoescape
import pytest

from reserved.engines.mtd_readiness import IncomeKind, IncomeSource
import reserved.services.mtd_scope_indication_presentation as presentation
from reserved.services.mtd_scope_indication import (
    CONTRACT_VERSION,
    FEATURE_LABEL,
    MtdScopeCompleteness,
    MtdScopeIndication,
    as_mtd_scope_mapping,
    present_mtd_scope_indication,
)
from reserved.services.mtd_scope_indication_presentation import (
    render_mtd_scope_indication,
)


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "reserved/services/mtd_scope_indication_presentation.py"
TEMPLATE = ROOT / "reserved/templates/v2/_mtd_scope_indication.html"
COMPLETE = MtdScopeCompleteness(True, True, True, True, True)


def source(
    source_id="trade",
    kind=IncomeKind.SOLE_TRADE,
    gross=Decimal("0.00"),
    *,
    business_id=None,
    complete=True,
):
    return IncomeSource(source_id, kind, gross, business_id, complete)


def indication(
    sources=(),
    *,
    year="2024-25",
    completeness=COMPLETE,
    registered=None,
    exempt=None,
):
    return present_mtd_scope_indication(
        sources,
        assessment_tax_year=year,
        completeness=completeness,
        registered_for_self_assessment=registered,
        exemption_applies=exempt,
    )


def render(value=None):
    if value is None:
        value = indication((), completeness=None)
    return render_mtd_scope_indication(value)


def template_render():
    environment = Environment(
        loader=FileSystemLoader(TEMPLATE.parent.parent),
        autoescape=select_autoescape(("html",)),
    )
    return environment.get_template(f"v2/{TEMPLATE.name}").render


def bind(projector, *, renderer=None):
    return presentation._bind_renderer(
        projector=projector,
        indication_type=MtdScopeIndication,
        render_template=renderer or template_render(),
        mapping_type=type(MappingProxyType({})),
        decimal_type=Decimal,
        contract_version=CONTRACT_VERSION,
        feature_label=FEATURE_LABEL,
        schema=presentation._SCHEMA,
        copy_records=presentation._COPY,
        gross_basis=presentation._GROSS_BASIS,
        determination_basis=presentation._DETERMINATION_BASIS,
        included_categories=presentation._INCLUDED_CATEGORIES,
        excluded_categories=presentation._EXCLUDED_CATEGORIES,
        closed_model=presentation._CLOSED_MODEL,
    )


def substituted(mapping):
    frozen = MappingProxyType(dict(mapping))
    return bind(lambda _value: frozen)


@pytest.mark.parametrize(
    "value,headline,summary",
    [
        (
            indication((), completeness=None),
            "More information needed",
            "We cannot provide an indication until the relevant income and eligibility information is complete.",
        ),
        (
            indication((source(gross=Decimal("50000.00")),)),
            "Worth reviewing",
            "Making Tax Digital may apply from the tax year shown.",
        ),
        (
            indication((source(gross=Decimal("10000.00")),)),
            "Not currently indicated",
            "This is not a promise of exemption or future non-applicability.",
        ),
    ],
)
def test_each_approved_customer_state_renders_deterministic_fixed_copy(
    value, headline, summary
):
    output = render(value)
    assert FEATURE_LABEL in output
    assert headline in output
    assert summary in output
    assert "The threshold uses qualifying gross income before expenses." in output
    assert "This is a local planning indication, not HMRC&#39;s formal determination." in output
    assert output == render(value)
    assert not any(tag in output for tag in ("<a ", "<button", "<form", "<script"))


@pytest.mark.parametrize(
    "year,mandatory,effective,threshold",
    [
        ("2024-25", "2026-27", "2026-04-06", "£50,000.00"),
        ("2025-26", "2027-28", "2027-04-06", "£30,000.00"),
        ("2026-27", "2028-29", "2028-04-06", "£20,000.00"),
    ],
)
def test_supported_period_dates_and_complete_money_are_displayed_exactly(
    year, mandatory, effective, threshold
):
    value = indication(
        (source(gross=Decimal("20000.01")),),
        year=year,
        registered=True,
        exempt=False,
    )
    output = render(value)
    assert f"<dd>{year}</dd>" in output
    assert f"<dd>{mandatory}</dd>" in output
    assert f"<dd>{effective}</dd>" in output
    assert "£20,000.01" in output
    assert threshold in output


def test_negative_distance_is_displayed_without_changing_the_issued_value():
    value = indication(
        (source(gross=Decimal("50000.01")),),
        registered=False,
        exempt=False,
    )
    before = as_mtd_scope_mapping(value)["distance_from_threshold"]
    output = render(value)
    assert "-£0.01" in output
    assert as_mtd_scope_mapping(value)["distance_from_threshold"] is before


@pytest.mark.parametrize(
    "year,mandatory,effective,threshold",
    [
        ("2024-25", "2026-27", "2026-04-06", Decimal("50000")),
        ("2025-26", "2027-28", "2027-04-06", Decimal("30000")),
        ("2026-27", "2028-29", "2028-04-06", Decimal("20000")),
    ],
)
@pytest.mark.parametrize(
    "case,headline",
    [
        ("above", "Worth reviewing"),
        ("approaching", "Worth reviewing"),
        ("below", "Not currently indicated"),
        ("exempt", "Not currently indicated"),
        ("unknown-eligibility", "More information needed"),
        ("unknown-income", "More information needed"),
        ("unsupported-completeness", "More information needed"),
    ],
)
def test_live_issuer_to_renderer_has_neutral_copy_for_current_and_later_starts(
    year, mandatory, effective, threshold, case, headline
):
    gross = threshold + Decimal("0.01")
    if case == "approaching":
        gross = threshold * Decimal("0.80")
    elif case == "below":
        gross = threshold * Decimal("0.79")
    elif case == "unknown-income":
        gross = None
    value = indication(
        (source(gross=gross),),
        year=year,
        registered=None if case == "unknown-eligibility" else True,
        exempt=case == "exempt",
        completeness=None if case == "unsupported-completeness" else COMPLETE,
    )
    projection = as_mtd_scope_mapping(value)
    output = render_mtd_scope_indication(value)
    assert projection["contract_version"] == "reserved-mtd-scope-indication/1.1"
    assert projection["headline"] == headline
    assert headline in output
    assert projection["summary"] in output
    assert "future tax year" not in output
    assert "definitely applies" not in output
    assert "MTD ready" not in output
    assert projection["filing_action_available"] is False
    assert "The threshold uses qualifying gross income before expenses." in output
    assert "This is a local planning indication, not HMRC&#39;s formal determination." in output
    if case == "unsupported-completeness":
        assert projection["assessment_tax_year"] is None
        assert output == render()
    else:
        assert projection["assessment_tax_year"] == year
        assert projection["mandatory_from_tax_year"] == mandatory
        assert projection["effective_start_date"] == effective
        assert projection["threshold"].as_tuple() == threshold.as_tuple()
        for text in (year, mandatory, effective):
            assert f"<dd>{text}</dd>" in output
    if headline == "More information needed":
        assert projection["information_complete"] is False
        assert projection["qualifying_income"] is None
        assert projection["distance_from_threshold"] is None
        assert "£" not in output
    else:
        assert projection["information_complete"] is True
        assert projection["qualifying_income"] == gross
        assert f"£{threshold:,.2f}" in output
        if headline == "Worth reviewing":
            assert projection["summary"] == "Making Tax Digital may apply from the tax year shown."
        else:
            assert projection["summary"] == (
                "Based on the information checked, this does not currently indicate "
                "that Making Tax Digital may apply from the tax year shown. "
                "This is not a promise of exemption or future non-applicability."
            )


@pytest.mark.parametrize("gross", [Decimal("50000"), Decimal("10000")])
@pytest.mark.parametrize("mutation", ["old-copy", "old-version", "old-both", "mismatched-copy"])
def test_stale_or_mismatched_copy_contract_fails_to_generic_refusal(gross, mutation):
    value = indication((source(gross=gross),))
    state = dict(as_mtd_scope_mapping(value))
    if mutation in ("old-copy", "old-both"):
        state["summary"] = (
            "Making Tax Digital may apply in a future tax year."
            if gross == Decimal("50000") else
            "Based on the information checked, this does not currently indicate "
            "that Making Tax Digital may apply from the future tax year shown. "
            "This is not a promise of exemption or future non-applicability."
        )
    if mutation in ("old-version", "old-both"):
        state["contract_version"] = "reserved-mtd-scope-indication/1.0"
    if mutation == "mismatched-copy":
        other = indication((source(gross=Decimal("10000") if gross == Decimal("50000") else Decimal("50000")),))
        state["summary"] = as_mtd_scope_mapping(other)["summary"]
    assert substituted(state)(value) == render()


def test_safe_categories_and_counts_render_without_opaque_identifiers():
    value = indication(
        (
            source("opaque:trade:a", gross=Decimal("12000.00"), business_id="secret:business:a"),
            source("opaque:trade:b", gross=Decimal("9000.00"), business_id="secret:business:b"),
            source("opaque:property", IncomeKind.UK_PROPERTY, Decimal("10000.00")),
            source("opaque:paye", IncomeKind.PAYE_EMPLOYMENT, Decimal("90000.00")),
            source("opaque:dividend", IncomeKind.DIVIDENDS, Decimal("1000.00")),
        ),
        year="2025-26",
        registered=True,
        exempt=False,
    )
    output = render(value)
    assert "Self-employment, UK property" in output
    assert "Employment income, Dividend income" in output
    assert "<dt>Included income sources</dt><dd>3</dd>" in output
    assert "<dt>Included businesses</dt><dd>3</dd>" in output
    assert "<dt>Excluded income sources</dt><dd>2</dd>" in output
    assert "opaque:" not in output and "secret:" not in output


def test_contextual_incomplete_state_shows_dates_and_safe_counts_but_no_money():
    value = indication((source(gross=Decimal("50000.01")),))
    projection = as_mtd_scope_mapping(value)
    assert projection["assessment_tax_year"] == "2024-25"
    output = render(value)
    assert "More information needed" in output
    assert "2024-25" in output and "2026-04-06" in output
    assert "Included income sources</dt><dd>1" in output
    for unsafe_point_value in ("£50,000.01", "£50,000.00", "-£0.01"):
        assert unsafe_point_value not in output
    assert "Qualifying gross income</dt>" not in output
    assert "Threshold</dt>" not in output


def test_value_free_incomplete_and_every_invalid_value_share_one_refusal():
    closed = render()

    class IndicationSubtype(MtdScopeIndication):
        pass

    invalid = (
        None,
        object(),
        object.__new__(MtdScopeIndication),
        object.__new__(IndicationSubtype),
    )
    assert {render_mtd_scope_indication(value) for value in invalid} == {closed}
    assert not any(term in closed for term in ("secret", "opaque", "token", "<script"))


def test_class_and_module_rebinding_cannot_change_supported_renderer(monkeypatch):
    value = indication((source(gross=Decimal("50000.00")),))
    expected = render(value)
    monkeypatch.setattr(
        MtdScopeIndication,
        "as_mapping",
        lambda self: MappingProxyType({"headline": "forged"}),
        raising=False,
    )
    for name, replacement in {
        "as_mtd_scope_mapping": lambda value: MappingProxyType({"headline": "forged"}),
        "MtdScopeIndication": object,
        "CONTRACT_VERSION": "forged",
        "FEATURE_LABEL": "forged",
        "Decimal": object,
        "MappingProxyType": object,
        "Environment": object,
        "FileSystemLoader": object,
        "select_autoescape": object,
        "_SCHEMA": ("forged",),
        "_COPY": (),
        "_GROSS_BASIS": "forged",
        "_DETERMINATION_BASIS": "forged",
        "_INCLUDED_CATEGORIES": (),
        "_EXCLUDED_CATEGORIES": (),
        "_CLOSED_MODEL": ("forged",),
        "_bind_renderer": lambda **kwargs: lambda value: "forged",
        "type": lambda value: object,
        "str": object,
        "int": object,
        "bool": object,
        "tuple": object,
        "frozenset": object,
        "len": lambda value: 0,
        "all": lambda values: False,
        "any": lambda values: True,
        "format": lambda value, spec: "forged",
    }.items():
        monkeypatch.setattr(presentation, name, replacement, raising=False)
    assert render_mtd_scope_indication(value) == expected
    assert render_mtd_scope_indication(object()) == render()


def test_projector_error_and_wrong_mapping_type_fail_to_fixed_refusal():
    value = indication((source(gross=Decimal("50000.00")),))
    closed = render()

    def fail(_value):
        raise RuntimeError("secret projector failure")

    assert bind(fail)(value) == closed
    assert bind(lambda _value: dict(as_mtd_scope_mapping(value)))(value) == closed


def test_reversed_exact_19_key_schema_order_fails_to_fixed_refusal():
    value = indication((source(gross=Decimal("50000.00")),))
    projection = as_mtd_scope_mapping(value)
    reversed_projection = MappingProxyType(dict(reversed(tuple(projection.items()))))

    assert tuple(reversed_projection) == tuple(reversed(presentation._SCHEMA))
    assert bind(lambda _value: reversed_projection)(value) == render()

    subtype_items = list(projection.items())
    subtype_items[0] = (_StringSubclass(subtype_items[0][0]), subtype_items[0][1])
    subtype_projection = MappingProxyType(dict(subtype_items))
    assert bind(lambda _value: subtype_projection)(value) == render()


def test_mandatory_period_before_assessment_period_fails_to_fixed_refusal():
    value = indication((source(gross=Decimal("50000.00")),))
    state = dict(as_mtd_scope_mapping(value))
    state["mandatory_from_tax_year"] = "2023-24"
    state["effective_start_date"] = "2023-04-06"

    assert substituted(state)(value) == render()


def test_complete_nonzero_income_with_zero_included_sources_fails_to_fixed_refusal():
    value = indication((source(gross=Decimal("50000.00")),))
    state = dict(as_mtd_scope_mapping(value))
    state["included_source_categories"] = ()
    state["included_source_count"] = 0
    state["included_business_count"] = 0

    assert state["information_complete"] is True
    assert state["qualifying_income"] == Decimal("50000.00")
    assert substituted(state)(value) == render()


@pytest.mark.parametrize(
    "mutator",
    [
        lambda state: state.pop("summary"),
        lambda state: state.__setitem__("extra", "secret-extra"),
        lambda state: state.__setitem__("headline", "Unknown state"),
        lambda state: state.__setitem__("summary", "<script>secret()</script>"),
        lambda state: state.__setitem__("filing_action_available", True),
        lambda state: state.__setitem__("information_complete", 1),
        lambda state: state.__setitem__("assessment_tax_year", "2024/25"),
        lambda state: state.__setitem__("mandatory_from_tax_year", "2027-28"),
        lambda state: state.__setitem__("effective_start_date", "2026-04-07"),
        lambda state: state.__setitem__("included_source_count", -1),
        lambda state: state.__setitem__("included_business_count", 2),
        lambda state: state.__setitem__("excluded_source_count", True),
        lambda state: state.__setitem__("included_source_categories", ("<img src=x>",)),
        lambda state: state.__setitem__("excluded_source_categories", ("Provider secret",)),
        lambda state: state.__setitem__("qualifying_income", Decimal("50000")),
        lambda state: state.__setitem__("distance_from_threshold", Decimal("0.01")),
        lambda state: state.__setitem__("threshold", Decimal("30000")),
        lambda state: state.__setitem__("threshold", Decimal("1E+100")),
    ],
)
def test_missing_extra_unknown_unsafe_or_incoherent_projection_refuses(mutator):
    value = indication((source(gross=Decimal("50000.00")),))
    state = dict(as_mtd_scope_mapping(value))
    mutator(state)
    output = substituted(state)(value)
    assert output == render()
    assert "secret" not in output.lower() and "<img" not in output


class _StringSubclass(str):
    pass


class _DecimalSubclass(Decimal):
    pass


@pytest.mark.parametrize(
    "field,replacement",
    [
        ("feature_label", _StringSubclass(FEATURE_LABEL)),
        ("assessment_tax_year", _StringSubclass("2024-25")),
        ("included_source_categories", (_StringSubclass("Self-employment"),)),
        ("included_source_count", True),
        ("qualifying_income", _DecimalSubclass("50000.00")),
        ("threshold", _DecimalSubclass("50000")),
        ("distance_from_threshold", _DecimalSubclass("0.00")),
    ],
)
def test_string_decimal_and_numeric_subclasses_are_rejected(field, replacement):
    value = indication((source(gross=Decimal("50000.00")),))
    state = dict(as_mtd_scope_mapping(value))
    state[field] = replacement
    assert substituted(state)(value) == render()


def test_template_failure_returns_the_same_precompiled_generic_refusal():
    value = indication((source(gross=Decimal("50000.00")),))
    real_render = template_render()
    calls = 0

    def flaky(*, model):
        nonlocal calls
        calls += 1
        if calls == 1:
            return real_render(model=model)
        raise RuntimeError("secret render failure")

    renderer = bind(as_mtd_scope_mapping, renderer=flaky)
    assert renderer(value) == render()


class _DOM(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def test_accessible_semantics_and_template_autoescape():
    output = render(indication((source(gross=Decimal("50000.00")),)))
    parser = _DOM()
    parser.feed(output)
    assert parser.tags[0] == (
        "section",
        {
            "role": "status",
            "aria-live": "polite",
            "aria-atomic": "true",
            "aria-labelledby": "mtd-scope-indication-heading",
        },
    )
    assert ("h2", {"id": "mtd-scope-indication-heading"}) in parser.tags
    assert ("dl", {}) in parser.tags
    assert not [tag for tag, _attrs in parser.tags if tag in {"a", "button", "form", "script", "iframe"}]

    hostile = '<img src=x onerror="secret()">'
    model = (
        hostile, hostile, hostile, hostile, hostile, True,
        hostile, hostile, hostile, True, hostile, hostile, hostile,
        (hostile,), hostile, hostile, (hostile,), hostile,
    )
    escaped = template_render()(model=model)
    assert hostile not in escaped
    assert escaped.count("&lt;img") >= 16


def test_request_time_rendering_does_not_open_files(monkeypatch):
    value = indication((source(gross=Decimal("50000.00")),))

    def forbidden(*args, **kwargs):
        raise AssertionError("request-time file access")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    assert "Worth reviewing" in render(value)


def test_public_surface_imports_signature_and_side_effect_exclusions_are_narrow():
    signature = inspect.signature(render_mtd_scope_indication)
    assert tuple(signature.parameters) == ("value",)
    assert render_mtd_scope_indication.__defaults__ is None
    assert render_mtd_scope_indication.__kwdefaults__ is None
    assert render_mtd_scope_indication.__dict__ == {}
    assert presentation.__all__ == ("render_mtd_scope_indication",)

    tree = ast.parse(SERVICE.read_text(encoding="utf-8"))
    imports = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imports == {
        "__future__",
        "decimal",
        "pathlib",
        "types",
        "jinja2",
        "reserved.services.mtd_scope_indication",
    }
    source_text = SERVICE.read_text(encoding="utf-8").lower()
    for forbidden in (
        "import requests",
        "import urllib",
        "import socket",
        "import sqlite",
        "import logging",
        "subprocess",
        "flask",
        "open(",
        "persist(",
        "commit(",
        "connect(",
        "request(",
        "schedule(",
    ):
        assert forbidden not in source_text


def test_exact_four_authorised_candidate_paths_exist():
    assert SERVICE.is_file()
    assert TEMPLATE.is_file()
    assert Path(__file__).is_file()
    assert (ROOT / "docs/MTD_SCOPE_INDICATION_PRESENTATION_EVIDENCE.md").is_file()
