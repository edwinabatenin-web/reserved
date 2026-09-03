"""Adversarial acceptance for the non-actionable W10 billing-plan fragment."""

from __future__ import annotations

import ast
import copy
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape

from reserved.billing.contracts import INITIAL_BILLING_AUTHORITY
import reserved.services.w10_billing_page as page
from reserved.services.w10_billing_page import (
    W10BillingPageContext,
    _w10_billing_page_context,
    _w10_billing_page_render_model,
    render_w10_billing_plans_fragment,
)
from reserved.services.w10_billing_presentation import (
    CONTRACT_VERSION,
    VAT_QUALIFICATION,
    PlanCard,
    W10BillingPresentation,
    present_w10_billing_presentation,
    w10_billing_presentation_authority_version,
    w10_billing_presentation_source_identity,
)

ROOT = Path(__file__).resolve().parents[1]
SERVICE_PATH = ROOT / "reserved" / "services" / "w10_billing_page.py"
TEMPLATE_PATH = ROOT / "reserved" / "templates" / "v2" / "_w10_billing_plans.html"
EXPECTED_LABELS = ("£29 per month", "£156 for six months", "£288 per year")
EXPECTED_AVAILABLE_HTML = (
    '<section aria-labelledby="w10-billing-plans-heading">\n'
    '    <h2 id="w10-billing-plans-heading">Billing plans</h2>\n    \n'
    '    <ul id="w10-billing-plan-list" aria-describedby="w10-billing-vat-note">\n'
    '        <li>£29 per month</li><li>£156 for six months</li><li>£288 per year</li>\n'
    '    </ul>\n'
    '    <p id="w10-billing-vat-note">Prices include VAT where applicable.</p>\n'
    '    \n</section>'
)
EXPECTED_CLOSED_HTML = (
    '<section aria-labelledby="w10-billing-plans-heading">\n'
    '    <h2 id="w10-billing-plans-heading">Billing plans</h2>\n    \n'
    '    <p role="status">Review required — billing plans are temporarily unavailable.</p>\n'
    '    \n</section>'
)


def _presentation() -> W10BillingPresentation:
    value = present_w10_billing_presentation(INITIAL_BILLING_AUTHORITY)
    assert value is not None
    return value


def _raw_template_render(model: object) -> str:
    """Render the internal include directly; never the supported boundary."""
    environment = Environment(
        loader=FileSystemLoader(ROOT / "reserved" / "templates"),
        autoescape=select_autoescape(("html",)),
    )
    return environment.get_template("v2/_w10_billing_plans.html").render(model=model)


def _render(value: object) -> str:
    return render_w10_billing_plans_fragment(value)


class _DOM(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.ids: list[str] = []
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.tags.append((tag, attributes))
        if attributes.get("id"):
            self.ids.append(attributes["id"])

    def handle_data(self, data):
        stripped = data.strip()
        if stripped:
            self.text.append(stripped)


def _dom(output: str) -> _DOM:
    parser = _DOM()
    parser.feed(output)
    return parser


def _corrupt(value: W10BillingPresentation, name: str, replacement: object) -> object:
    object.__setattr__(value, name, replacement)
    return value


def test_exact_labels_render_once_in_canonical_dom_order():
    output = _render(_presentation())
    assert output == EXPECTED_AVAILABLE_HTML
    assert all(output.count(label) == 1 for label in EXPECTED_LABELS)
    assert [text for text in _dom(output).text if text in EXPECTED_LABELS] == list(EXPECTED_LABELS)


def test_vat_copy_is_once_and_programmatically_associated_with_list():
    output = _render(_presentation())
    parser = _dom(output)
    assert output.count(VAT_QUALIFICATION) == 1
    tags = parser.tags
    section = next(attrs for tag, attrs in tags if tag == "section")
    heading = next(attrs for tag, attrs in tags if tag == "h2")
    plan_list = next(attrs for tag, attrs in tags if tag == "ul")
    note = next(attrs for tag, attrs in tags if tag == "p")
    assert section["aria-labelledby"] == heading["id"] == "w10-billing-plans-heading"
    assert plan_list["aria-describedby"] == note["id"] == "w10-billing-vat-note"


@pytest.mark.parametrize("closed", [False, True])
def test_semantic_structure_readable_order_and_unique_ids(closed):
    parser = _dom(_render(None if closed else _presentation()))
    assert parser.tags[0][0] == "section"
    assert any(tag == "h2" for tag, _ in parser.tags)
    assert len(parser.ids) == len(set(parser.ids))
    if closed:
        assert not any(tag in {"ul", "ol"} for tag, _ in parser.tags)
        assert "Review required — billing plans are temporarily unavailable." in parser.text
    else:
        assert sum(tag == "ul" for tag, _ in parser.tags) == 1
        assert sum(tag == "li" for tag, _ in parser.tags) == 3


@pytest.mark.parametrize("closed", [False, True])
def test_fragment_has_no_actionable_controls_behaviour_or_forbidden_semantics(closed):
    output = _render(None if closed else _presentation())
    parser = _dom(output)
    forbidden_tags = {"a", "button", "form", "script", "iframe", "object", "embed"}
    assert not [tag for tag, _ in parser.tags if tag in forbidden_tags]
    assert not [name for _, attrs in parser.tags for name in attrs if name.startswith("on")]
    forbidden = (
        "checkout", "portal", "customer action", "provider", "product_", "price_",
        "offer", "discount", "saving", "equivalent", "vat rate", "vat applies",
        "renew", "cancel", "refund", "grace", "dispute", "chargeback", "entitlement",
        "grant access", "payment authority", "javascript:", "data:", "http://", "https://",
    )
    lowered = output.lower()
    assert not [term for term in forbidden if term in lowered]


class _PresentationSubclass(W10BillingPresentation):
    pass


def _invalid_values():
    valid = _presentation()
    incomplete = object.__new__(W10BillingPresentation)
    forged = W10BillingPresentation(CONTRACT_VERSION, valid.plans, VAT_QUALIFICATION)
    object.__setattr__(forged, "_source_identity", "hostile-source-identity")
    tampered = _corrupt(_presentation(), "vat_qualification", "<script>hostile()</script>")
    reordered = _corrupt(_presentation(), "plans", tuple(reversed(_presentation().plans)))
    subclassed = object.__new__(_PresentationSubclass)
    return (None, incomplete, forged, tampered, reordered, subclassed)


@pytest.mark.parametrize("value", _invalid_values())
def test_all_invalid_inputs_share_one_fixed_price_free_output(value):
    context = _w10_billing_page_context(value)
    output = _render(value)
    assert context.status == "review_required"
    assert (context.contract_version, context.plan_labels, context.vat_qualification) == (None, (), None)
    assert output == _render(None) == EXPECTED_CLOSED_HTML
    assert "£" not in output and not any(label in output for label in EXPECTED_LABELS)
    assert "hostile" not in output and "invalid-state" not in output


def test_template_autoescaping_blocks_hostile_markup():
    hostile = '<img src=x onerror="alert(1)">'
    output = _raw_template_render((True, (hostile,), hostile))
    assert hostile not in output
    assert output.count("&lt;img") == 2
    assert not any(tag == "img" for tag, _ in _dom(output).tags)


def test_raw_template_is_internal_only_and_not_the_supported_security_boundary():
    hostile_model = (True, ("Pay £999 now",), "VAT never applies.")
    raw = _raw_template_render(hostile_model)
    assert "£999" in raw and "VAT never applies." in raw
    supported = _render(hostile_model)
    assert supported == _render(None)
    assert "£999" not in supported and "VAT never applies." not in supported


@pytest.mark.parametrize(
    "caller_model",
    (
        (True, ("Pay £999 now",), "VAT never applies."),
        (1, ("<img src=x onerror=alert(1)>",), "Renewal guaranteed."),
        (True, (), None),
    ),
)
def test_caller_created_models_cannot_emit_available_or_partial_supported_html(caller_model):
    assert _render(caller_model) == _render(None)


def test_supported_operation_accepts_no_render_model_or_copy_overrides():
    with pytest.raises(TypeError):
        render_w10_billing_plans_fragment(_presentation(), (True, (), None))
    for keyword in ("model", "available", "plan_labels", "vat_qualification"):
        with pytest.raises(TypeError):
            render_w10_billing_plans_fragment(_presentation(), **{keyword: "hostile"})


def test_only_the_supported_customer_html_operation_is_public():
    assert page.__all__ == ("render_w10_billing_plans_fragment",)


@pytest.mark.parametrize(
    ("name", "replacement"),
    (
        ("status", "available-but-hostile"),
        ("contract_version", "hostile-contract"),
        ("plan_labels", ("Pay £999 now",)),
        ("vat_qualification", "No VAT is payable."),
        ("_authority_version", "hostile-authority"),
        ("_source_identity", "hostile-source"),
    ),
)
def test_consumption_revalidates_every_mutated_available_field(name, replacement):
    context = _w10_billing_page_context(_presentation())
    object.__setattr__(context, name, replacement)
    output = _raw_template_render(_w10_billing_page_render_model(context))
    assert output == _render(None)
    assert "£" not in output and "hostile" not in output and "No VAT" not in output


def test_mutated_closed_context_cannot_become_available():
    context = _w10_billing_page_context(None)
    replacements = {
        "status": "available",
        "contract_version": CONTRACT_VERSION,
        "plan_labels": EXPECTED_LABELS,
        "vat_qualification": VAT_QUALIFICATION,
        "_authority_version": "FD-W10-001/2026-09-02/v1",
        "_source_identity": "w10-billing-source:sha256-" + "0" * 64,
    }
    for name, replacement in replacements.items():
        object.__setattr__(context, name, replacement)
    assert _raw_template_render(_w10_billing_page_render_model(context)) == _render(None)


class _StringSubclass(str):
    def __eq__(self, other):
        raise AssertionError("string-subclass equality must not run")


class _TupleSubclass(tuple):
    def __eq__(self, other):
        raise AssertionError("tuple-subclass equality must not run")


class _EqualitySpoof:
    def __eq__(self, other):
        raise AssertionError("spoof equality must not run")

    def __str__(self):
        raise AssertionError("spoof string conversion must not run")


@pytest.mark.parametrize(
    ("name", "replacement"),
    (
        ("status", _StringSubclass("available")),
        ("status", _EqualitySpoof()),
        ("contract_version", _StringSubclass(CONTRACT_VERSION)),
        ("plan_labels", _TupleSubclass(EXPECTED_LABELS)),
        ("plan_labels", (_EqualitySpoof(), *EXPECTED_LABELS[1:])),
        ("vat_qualification", _StringSubclass(VAT_QUALIFICATION)),
        ("_authority_version", _EqualitySpoof()),
        ("_source_identity", _StringSubclass("hostile")),
    ),
)
def test_consumption_rejects_inexact_types_before_hostile_hooks(name, replacement):
    context = _w10_billing_page_context(_presentation())
    object.__setattr__(context, name, replacement)
    assert _raw_template_render(_w10_billing_page_render_model(context)) == _render(None)


@pytest.mark.parametrize(
    ("name", "replacement"),
    (
        ("contract_version", _StringSubclass(CONTRACT_VERSION)),
        ("contract_version", _EqualitySpoof()),
        ("plans", _TupleSubclass(_presentation().plans)),
        ("plans", (_EqualitySpoof(), *_presentation().plans[1:])),
        ("vat_qualification", _StringSubclass(VAT_QUALIFICATION)),
        ("vat_qualification", _EqualitySpoof()),
    ),
)
def test_supported_operation_rejects_mutated_inexact_and_equality_spoof_fields(name, replacement):
    value = _presentation()
    object.__setattr__(value, name, replacement)
    assert _render(value) == EXPECTED_CLOSED_HTML


def test_direct_arbitrary_render_models_are_sanitized_before_template_consumption():
    hostile = SimpleNamespace(
        status="available",
        contract_version=CONTRACT_VERSION,
        plan_labels=("Pay £999 now",),
        vat_qualification="VAT never applies.",
    )
    output = _render(hostile)
    assert output == _render(None)
    assert "£999" not in output and "VAT never" not in output


def test_public_s6a_global_rebinding_cannot_authorize_fake_or_changed_copy(monkeypatch):
    class FakePresentation:
        contract_version = "changed-contract"
        plans = (SimpleNamespace(label="Pay £999 now"),)
        vat_qualification = "VAT never applies."

    monkeypatch.setattr(page, "W10BillingPresentation", FakePresentation)
    monkeypatch.setattr(page, "w10_billing_presentation_authority_version", lambda _: "changed")
    monkeypatch.setattr(page, "w10_billing_presentation_source_identity", lambda _: "changed")
    monkeypatch.setattr(page, "_AVAILABLE", "changed")
    monkeypatch.setattr(page, "_PRESENTATION_CONTRACT_VERSION", "changed-contract")
    monkeypatch.setattr(page, "_EXPECTED_LABELS", ("Pay £999 now",))
    monkeypatch.setattr(page, "_VAT_QUALIFICATION", "VAT never applies.")
    monkeypatch.setattr(page, "_EXPECTED_AUTHORITY_VERSION", "changed")
    monkeypatch.setattr(page, "_EXPECTED_SOURCE_IDENTITY", "changed")
    assert _render(FakePresentation()) == _render(None)

    context = _w10_billing_page_context(_presentation())
    assert EXPECTED_LABELS == context.plan_labels
    assert all(_render(_presentation()).count(label) == 1 for label in EXPECTED_LABELS)


def test_supported_renderer_ignores_later_dependency_global_rebinding(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("rebound global must not be used")

    for name in (
        "_w10_billing_page_context", "_w10_billing_page_render_model",
        "Environment", "FileSystemLoader", "select_autoescape",
    ):
        monkeypatch.setattr(page, name, fail)
    assert _render(_presentation()) == EXPECTED_AVAILABLE_HTML
    assert _render(None) == EXPECTED_CLOSED_HTML


def test_internal_provenance_and_representations_never_render():
    value = _presentation()
    authority = w10_billing_presentation_authority_version(value)
    source = w10_billing_presentation_source_identity(value)
    context = _w10_billing_page_context(value)
    output = _render(value)
    assert authority not in output and source not in output
    assert repr(value) not in output and repr(context) not in output
    assert "sha256" not in output and "FD-W10" not in output


def test_rendering_is_deterministic_for_fresh_reconstructed_and_copies():
    fresh = _presentation()
    reconstructed = W10BillingPresentation(
        CONTRACT_VERSION,
        tuple(PlanCard(label) for label in EXPECTED_LABELS),
        VAT_QUALIFICATION,
    )
    values = (fresh, _presentation(), reconstructed, copy.copy(fresh), copy.deepcopy(fresh))
    outputs = {_render(value) for value in values}
    assert len(outputs) == 1


def test_service_imports_only_s6a_and_future_standard_library():
    tree = ast.parse(SERVICE_PATH.read_text())
    imports = {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imports == {
        "__future__", "jinja2", "pathlib",
        "reserved.services.w10_billing_presentation",
    }
    source = SERVICE_PATH.read_text().lower()
    forbidden = ("provider", "payment", "reserved.auth", "database", "reserved.web", "route", "network", "requests", "urllib", "socket", "config", "persist")
    assert not [term for term in forbidden if term in source]


def test_context_is_exact_immutable_detached_and_rejects_unsupported_state():
    value = _presentation()
    context = _w10_billing_page_context(value)
    assert type(context) is W10BillingPageContext
    assert context.contract_version == CONTRACT_VERSION
    assert context.plan_labels == EXPECTED_LABELS and type(context.plan_labels) is tuple
    assert context.vat_qualification == VAT_QUALIFICATION
    assert all(type(label) is str for label in context.plan_labels)
    _corrupt(value, "plans", ())
    assert context.plan_labels == EXPECTED_LABELS
    with pytest.raises(AttributeError):
        context.status = "review_required"
    with pytest.raises((TypeError, ValueError)):
        W10BillingPageContext("available", CONTRACT_VERSION, ("£1",), VAT_QUALIFICATION)
    with pytest.raises((TypeError, ValueError)):
        W10BillingPageContext("unknown")


def test_only_authorised_new_paths_are_present():
    assert TEMPLATE_PATH.is_file() and SERVICE_PATH.is_file()
