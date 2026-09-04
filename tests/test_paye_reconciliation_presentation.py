"""Adversarial acceptance for the route-less PAYE evidence renderer."""

from __future__ import annotations

import ast
import builtins
import copy
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import pickle

from jinja2 import Environment, FileSystemLoader, select_autoescape
import pytest

import reserved.services.paye_reconciliation_presentation as presentation
from reserved.engines.paye_reconciliation import (
    Completeness,
    EvidenceKind,
    EvidenceRepresentation,
    PayeEvidence,
    PayeReconciliation,
    make_paye_reconciliation_policy,
    project_paye_reconciliation,
    reconcile_paye,
)
from reserved.services.paye_reconciliation_presentation import (
    render_paye_reconciliation,
)


ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "reserved/services/paye_reconciliation_presentation.py"
TEMPLATE = ROOT / "reserved/templates/v2/_paye_reconciliation.html"
TODAY = date(2026, 8, 12)
POLICY = make_paye_reconciliation_policy(45, Decimal("1.00"))


def evidence(
    kind=EvidenceKind.HMRC,
    paid="2000",
    *,
    employment="job-a",
    evidence_id="evidence-a",
    days_old=0,
):
    return PayeEvidence(
        kind=kind,
        tax_year="2026-27",
        tax_paid_to_date=paid,
        employment_id=employment,
        observed_on=TODAY - timedelta(days=days_old),
        effective_through=TODAY - timedelta(days=days_old),
        evidence_id=evidence_id,
        representation=EvidenceRepresentation.EMPLOYMENT_CUMULATIVE,
        completeness=Completeness.COMPLETE_FOR_REPRESENTATION,
    )


def result(*items, liability="6000"):
    return reconcile_paye(
        liability,
        tuple(items),
        tax_year="2026-27",
        as_of=TODAY,
        policy=POLICY,
    )


def calculated():
    return result(evidence(EvidenceKind.DOCUMENT))


def uncertain():
    return result(evidence(days_old=72))


def conflict(*, stale=False):
    age = 72 if stale else 0
    return result(
        evidence(EvidenceKind.HMRC, "2100", evidence_id="a-hmrc", days_old=age),
        evidence(EvidenceKind.DOCUMENT, "2000", evidence_id="b-document", days_old=age),
    )


def projection(value=None):
    return project_paye_reconciliation(value or calculated())


def changed_projection(value=None, **changes):
    return tuple(
        (key, changes.get(key, item)) for key, item in projection(value)
    )


def changed_record(record, **changes):
    return tuple((key, changes.get(key, item)) for key, item in record)


def template_render():
    environment = Environment(
        loader=FileSystemLoader(TEMPLATE.parent.parent),
        autoescape=select_autoescape(("html",)),
    )
    return environment.get_template(f"v2/{TEMPLATE.name}").render


def bind(projector, *, renderer=None):
    return presentation._bind_renderer(
        projector=projector,
        result_type=PayeReconciliation,
        render_template=renderer or template_render(),
        decimal_type=Decimal,
        date_type=date,
        schema=presentation._SCHEMA,
        evidence_schema=presentation._EVIDENCE_SCHEMA,
        conflict_schema=presentation._CONFLICT_SCHEMA,
        confidence_copy=presentation._CONFIDENCE_COPY,
        status_copy=presentation._STATUS_COPY,
        source_copy=presentation._SOURCE_COPY,
        source_order=presentation._SOURCE_ORDER,
        representations=presentation._REPRESENTATIONS,
        completeness=presentation._COMPLETENESS,
        selection_reasons=presentation._SELECTION_REASONS,
        warnings=presentation._WARNINGS,
        closed_model=presentation._CLOSED_MODEL,
        closed_html=presentation._CLOSED_HTML,
    )


@pytest.mark.parametrize(
    "value,headline,status_copy",
    [
        (calculated(), "PAYE evidence available", "Calculated from usable evidence"),
        (uncertain(), "PAYE evidence needs review", "Calculated with material uncertainty"),
        (conflict(), "PAYE evidence needs review", "Conflicting evidence"),
        (result(), "More information needed", "Insufficient evidence"),
    ],
)
def test_exact_supported_states_render_fixed_customer_copy(value, headline, status_copy):
    output = render_paye_reconciliation(value)
    assert "PAYE evidence check" in output
    assert headline in output
    assert status_copy in output
    assert output == render_paye_reconciliation(value)
    assert not any(tag in output for tag in ("<script", "<form", "<button", "<a "))


@pytest.mark.parametrize(
    "kind,copy_text",
    [
        (EvidenceKind.HMRC, "The evidence looks reliable."),
        (EvidenceKind.DOCUMENT, "The evidence looks reliable."),
        (EvidenceKind.MANUAL, "The evidence looks fairly reliable."),
        (EvidenceKind.BANK_INFERENCE, "The evidence needs more information."),
    ],
)
def test_confidence_uses_only_approved_fixed_copy(kind, copy_text):
    output = render_paye_reconciliation(result(evidence(kind)))
    assert copy_text in output


def test_direct_evidence_shows_only_carefully_qualified_current_figures():
    output = render_paye_reconciliation(calculated())
    assert "Tax currently evidenced as deducted</dt><dd>£2,000.00" in output
    assert (
        "Supplied annual estimate less tax currently evidenced as deducted</dt><dd>£4,000.00"
        in output
    )
    assert "annual estimate supplied to us" in output
    assert "before future payroll deductions" in output
    banned = (
        "HMRC-confirmed", "tax owed", "tax bill", "set aside", "payment due",
        "future payroll estimate",
    )
    assert not any(term.lower() in output.lower() for term in banned)


def test_bank_inference_suppresses_all_point_money_and_requests_direct_evidence():
    output = render_paye_reconciliation(
        result(evidence(EvidenceKind.BANK_INFERENCE, "1234.56"))
    )
    assert "Bank-payment estimate" in output
    assert "Direct PAYE evidence is needed before amounts can be shown." in output
    assert "£" not in output
    assert "Tax currently evidenced as deducted</dt>" not in output


def test_conflict_suppresses_points_and_shows_only_complete_bounded_range():
    output = render_paye_reconciliation(conflict())
    assert "no single amount is shown" in output
    assert "Lower figure from the supplied annual estimate</dt><dd>£3,900.00" in output
    assert "Higher figure from the supplied annual estimate</dt><dd>£4,000.00" in output
    assert "Tax currently evidenced as deducted</dt>" not in output


def test_stale_conflict_and_stale_point_make_partial_state_visible_without_range():
    stale_conflict = render_paye_reconciliation(conflict(stale=True))
    stale_point = render_paye_reconciliation(uncertain())
    for output in (stale_conflict, stale_point):
        assert "may be out of date or may not cover the full period" in output
    assert "Lower figure" not in stale_conflict
    assert "£" not in stale_conflict


def test_apparent_overpayment_is_provisional_and_never_a_refund_claim():
    output = render_paye_reconciliation(
        result(evidence(paid="1200"), liability="1000")
    )
    assert "Possible difference above the supplied annual estimate: £200.00" in output
    assert "provisional and is not a confirmed or available refund" in output
    assert "refund due" not in output.lower()


def test_only_safe_tax_year_source_category_date_status_and_money_are_exposed():
    item = evidence(
        EvidenceKind.DOCUMENT,
        evidence_id="opaque-evidence-secret",
        employment="opaque-employment-secret",
    )
    output = render_paye_reconciliation(result(item))
    assert "2026-27" in output
    assert "Document" in output
    assert "2026-08-12" in output
    assert "opaque" not in output and "secret" not in output
    assert "only usable direct evidence" not in output
    assert "source_reference" not in output and "evidence_id" not in output
    assert "conflict_tolerance" not in output and "digest" not in output


def test_reconstructed_subtyped_mutated_and_wrong_values_share_one_refusal():
    closed = render_paye_reconciliation(object())

    class ResultSubtype(PayeReconciliation):
        pass

    invalid = (
        None,
        object(),
        object.__new__(PayeReconciliation),
        object.__new__(ResultSubtype),
    )
    assert {render_paye_reconciliation(value) for value in invalid} == {closed}
    item = evidence()
    issued = result(item)
    object.__setattr__(item, "evidence_id", "mutated")
    assert render_paye_reconciliation(issued) == closed


class _StringSubtype(str):
    pass


class _DecimalSubtype(Decimal):
    pass


class _TupleSubtype(tuple):
    pass


@pytest.mark.parametrize(
    "projected",
    [
        projection()[:-1],
        projection() + (("extra", None),),
        tuple(reversed(projection())),
        ((_StringSubtype("tax_year"), "2026-27"),) + projection()[1:],
        _TupleSubtype(projection()),
        changed_projection(confidence=_StringSubtype("high")),
        changed_projection(tax_paid_to_date=_DecimalSubtype("2000.00")),
        changed_projection(calculation_status="future_status"),
        changed_projection(tax_paid_known=False),
        changed_projection(selected_kind="bank_inference"),
        changed_projection(evidence_count=999),
        changed_projection(range_completeness="complete_for_identified_uncertainties"),
    ],
)
def test_malformed_top_level_projection_fails_to_byte_identical_refusal(projected):
    closed = render_paye_reconciliation(object())
    assert bind(lambda _value: projected)(calculated()) == closed


def test_nested_schema_ids_kinds_conflicts_and_injection_fail_closed():
    closed = render_paye_reconciliation(object())
    value = calculated()
    base = dict(projection(value))
    nested = base["selected_evidence"][0]
    bad_nested_values = (
        nested[:-1],
        tuple(reversed(nested)),
        tuple((key, "<script>alert(1)</script>" if key == "evidence_id" else item)
              for key, item in nested),
        tuple((key, "future_source" if key == "kind" else item) for key, item in nested),
    )
    for bad_nested in bad_nested_values:
        projected = changed_projection(
            value,
            selected_evidence=(bad_nested,),
        )
        assert bind(lambda _value, projected=projected: projected)(value) == closed

    conflict_value = conflict()
    conflict_projection = dict(projection(conflict_value))["conflicts"][0]
    bad_conflict = tuple(
        (key, _StringSubtype("tax_paid_to_date") if key == "field" else item)
        for key, item in conflict_projection
    )
    projected = changed_projection(conflict_value, conflicts=(bad_conflict,))
    assert bind(lambda _value: projected)(conflict_value) == closed
    assert "script" not in closed.lower()


@pytest.mark.parametrize(
    "top_changes,nested_changes",
    [
        (
            {"tax_year": "9999-00", "selected_observed_on": date(9999, 4, 6)},
            {
                "tax_year": "9999-00",
                "observed_on": date(9999, 4, 6),
                "effective_through": date(9999, 4, 6),
            },
        ),
        (
            {"selected_observed_on": date(2030, 1, 1)},
            {"observed_on": date(2030, 1, 1), "effective_through": date(2030, 1, 1)},
        ),
        (
            {"selected_observed_on": date(2030, 1, 1)},
            {"observed_on": date(2030, 1, 1)},
        ),
        ({}, {"tax_code": "/1257"}),
    ],
)
def test_impossible_and_cross_year_dates_and_invalid_tax_code_fail_closed(
    top_changes, nested_changes
):
    closed = render_paye_reconciliation(object())
    value = calculated()
    nested = changed_record(dict(projection(value))["selected_evidence"][0], **nested_changes)
    projected = changed_projection(
        value,
        selected_evidence=(nested,),
        considered_evidence=(nested,),
        **top_changes,
    )
    assert bind(lambda _value: projected)(value) == closed


def test_projection_error_wrong_container_and_template_failure_are_fixed_refusal():
    closed = render_paye_reconciliation(object())
    value = calculated()

    def fail(_value):
        raise RuntimeError("secret projector failure")

    def render_fail(**_kwargs):
        raise RuntimeError("secret template failure")

    assert bind(fail)(value) == closed
    assert bind(lambda _value: dict(projection(value)))(value) == closed
    assert bind(project_paye_reconciliation, renderer=render_fail)(value) == closed
    assert bind(project_paye_reconciliation, renderer=lambda **_kwargs: object())(value) == closed


def test_module_helper_and_class_rebinding_cannot_change_captured_renderer(monkeypatch):
    value = calculated()
    expected = render_paye_reconciliation(value)
    for name, replacement in {
        "project_paye_reconciliation": lambda _value: (("tax_year", "forged"),),
        "PayeReconciliation": object,
        "Decimal": object,
        "date": object,
        "Path": object,
        "Environment": object,
        "FileSystemLoader": object,
        "select_autoescape": object,
        "MappingProxyType": object,
        "_SCHEMA": ("forged",),
        "_SOURCE_COPY": {},
        "_CLOSED_HTML": "forged",
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
        "sum": lambda values, start=None: Decimal("999.00"),
        "max": lambda values: None,
        "format": lambda value, spec: "forged",
    }.items():
        monkeypatch.setattr(presentation, name, replacement, raising=False)
    assert render_paye_reconciliation(value) == expected
    assert render_paye_reconciliation(object()) != "forged"


def test_renderer_uses_projector_not_result_attributes_under_class_dispatch_attack():
    value = calculated()
    expected = render_paye_reconciliation(value)
    original_getattribute = PayeReconciliation.__dict__["__getattribute__"]
    original_tax_year = PayeReconciliation.__dict__["tax_year"]
    try:
        type.__setattr__(PayeReconciliation, "__getattribute__", object.__getattribute__)
        type.__setattr__(
            PayeReconciliation, "tax_year", property(lambda _value: "forged")
        )
        assert value.tax_year == "forged"
        assert render_paye_reconciliation(value) == expected
    finally:
        type.__setattr__(PayeReconciliation, "__getattribute__", original_getattribute)
        type.__setattr__(PayeReconciliation, "tax_year", original_tax_year)


def test_template_autoescapes_and_renderer_has_no_request_time_io(monkeypatch):
    rendered = template_render()(model=(
        "<script>feature</script>", "headline", "summary", "confidence", "status",
        None, ("<img src=x onerror=alert(1)>",), None, False, None, None, False,
        None, None, False, False, None,
    ))
    assert "<script>" not in rendered and "<img" not in rendered
    assert "&lt;script&gt;" in rendered and "&lt;img" in rendered

    def forbidden(*_args, **_kwargs):
        raise AssertionError("request-time I/O attempted")

    monkeypatch.setattr(builtins, "open", forbidden)
    assert render_paye_reconciliation(calculated())


def test_source_is_route_network_persistence_logging_and_action_free():
    source = SERVICE.read_text()
    tree = ast.parse(source)
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not imported & {
        "flask", "requests", "httpx", "urllib", "socket", "logging",
        "sqlite3", "sqlalchemy",
    }
    render_node = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "render_paye_reconciliation"
    )
    called = {
        node.func.id
        for node in ast.walk(render_node)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not called & {"open", "print", "Path", "Environment", "FileSystemLoader"}
    banned = (
        "tax owed", "tax bill", "set aside", "payment due", "hmrc-confirmed",
        "file now", "submit return",
    )
    assert not any(term in source.lower() for term in banned)


def test_valid_handle_copy_and_pickle_behavior_cannot_reconstruct_renderer_input():
    value = calculated()
    assert copy.copy(value) is value
    assert copy.deepcopy(value) is value
    with pytest.raises(TypeError, match="cannot be pickled"):
        pickle.dumps(value)
    assert render_paye_reconciliation(value) == render_paye_reconciliation(copy.copy(value))
