"""Adversarial W10-S6D selected-plan renderer and authenticated routes."""

from __future__ import annotations

import importlib
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from itsdangerous import TimestampSigner, URLSafeTimedSerializer
from markupsafe import Markup

import reserved.database as db
from reserved import create_app
from reserved.auth import set_user_session
from reserved.billing.contracts import INITIAL_BILLING_AUTHORITY
import reserved.services.w10_billing_plan_selection as selection
from reserved.services.w10_billing_plan_selection import (
    render_w10_billing_plan_selection_fragment,
)
from reserved.services.w10_billing_presentation import (
    CONTRACT_VERSION,
    VAT_QUALIFICATION,
    PlanCard,
    W10BillingPresentation,
    present_w10_billing_presentation,
)


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "reserved" / "templates" / "v2" / "_w10_billing_plan_selection.html"
PAGE = ROOT / "reserved" / "templates" / "v2" / "plans.html"
V2 = ROOT / "reserved" / "web" / "v2.py"
KEYS = ("monthly", "six_month", "yearly")
LABELS = ("£29 per month", "£156 for six months", "£288 per year")
VAT = "Prices include VAT where applicable."
CLOSED = "Plan unavailable — review required."
_CSRF_VALUE = re.compile(
    r'((?:<meta name="csrf-token" content|'
    r'<input type="hidden" name="csrf_token" value)=")([^"\r\n]+)(")'
)


class _StringSubclass(str):
    pass


class _PresentationSubclass(W10BillingPresentation):
    pass


class _DOM(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.text: list[str] = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        if data.strip():
            self.text.append(data.strip())


def _view() -> W10BillingPresentation:
    value = present_w10_billing_presentation(INITIAL_BILLING_AUTHORITY)
    assert value is not None
    return value


def _render(value: object, key: object) -> str:
    return render_w10_billing_plan_selection_fragment(value, key)


def _closed() -> str:
    return _render(None, None)


def _csrf_token(body: str) -> str:
    tokens = _CSRF_VALUE.findall(body)
    assert len(tokens) == 2
    assert tokens[0][1] == tokens[1][1]
    return tokens[0][1]


def _without_csrf_token(body: str) -> str:
    return _CSRF_VALUE.sub(r"\1<csrf-token>\3", body)


@pytest.fixture
def app(tmp_path, monkeypatch):
    test_file = tmp_path / "w10_s6d.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client) -> None:
    assert client.get("/v2/demo-login").status_code == 302


def _direct_registered_route(app, plan_key: object, raw_environ: dict[str, object]) -> str:
    """Call the registered authenticated endpoint with exact synthetic WSGI evidence."""
    with app.test_request_context("/v2/plans/monthly"):
        from flask import request

        request.environ.pop("RAW_URI", None)
        request.environ.pop("REQUEST_URI", None)
        request.environ.update(raw_environ)
        set_user_session(
            user_id=1,
            clerk_id="demo_s6d",
            email="demo@example.test",
            display_name="S6D",
            is_demo=True,
        )
        result = app.view_functions["v2.billing_plan_selection"](plan_key=plan_key)
        return app.make_response(result).get_data(as_text=True)


@pytest.mark.parametrize("key,label", tuple(zip(KEYS, LABELS)))
def test_renderer_emits_exactly_one_selected_label_and_exact_vat(key, label):
    output = _render(_view(), key)
    assert output.count(label) == 1
    assert output.count(VAT) == 1
    assert all(other not in output for other in LABELS if other != label)
    assert CLOSED not in output


def test_fragment_is_semantic_autoescaped_and_has_no_actions():
    output = _render(_view(), "monthly")
    parser = _DOM()
    parser.feed(output)
    assert parser.tags[0][0] == "section"
    assert any(tag == "h2" for tag, _ in parser.tags)
    assert not any(tag in {"a", "button", "form", "script", "iframe"} for tag, _ in parser.tags)
    lowered = output.lower()
    for term in (
        "checkout", "payment", "portal", "provider", "discount", "saving",
        "entitlement", "renew", "cancel", "refund", "http://", "https://",
    ):
        assert term not in lowered


@pytest.mark.parametrize(
    "key",
    (
        None, True, False, 0, b"monthly", _StringSubclass("monthly"),
        "MONTHLY", "Monthly", "six-month", "six month", "year", "",
        "monthly/extra", "../monthly", "monthly%2Fextra", "<script>",
    ),
)
def test_every_invalid_key_has_one_identical_value_free_state(key):
    output = _render(_view(), key)
    assert output == _closed()
    assert output.count(CLOSED) == 1
    assert "£" not in output and VAT not in output
    assert not any(label in output for label in LABELS)
    assert "script" not in output and "monthly" not in output


@pytest.mark.parametrize("mutation,replacement", (
    ("contract_version", "latest"),
    ("vat_qualification", "VAT never applies."),
    ("_authority_version", "latest"),
    ("_source_identity", "hostile"),
    ("plans", (PlanCard("£29 per month"),)),
))
def test_mutated_presentations_fail_to_same_value_free_state(mutation, replacement):
    value = _view()
    object.__setattr__(value, mutation, replacement)
    assert _render(value, "monthly") == _closed()


def test_reordered_subtyped_incomplete_and_reconstructed_presentations_fail_closed():
    reordered = _view()
    object.__setattr__(reordered, "plans", tuple(reversed(reordered.plans)))
    subtype = object.__new__(_PresentationSubclass)
    incomplete = object.__new__(W10BillingPresentation)
    forged = object.__new__(W10BillingPresentation)
    valid = _view()
    for name, value in (
        ("contract_version", CONTRACT_VERSION),
        ("plans", valid.plans),
        ("vat_qualification", VAT_QUALIFICATION),
        ("_authority_version", "FD-W10-001/2026-09-02/v1"),
        ("_source_identity", "forged"),
    ):
        object.__setattr__(forged, name, value)
    for value in (reordered, subtype, incomplete, forged, object(), {}, LABELS):
        assert _render(value, "monthly") == _closed()


def test_string_subtype_nested_label_fails_closed():
    value = _view()
    card = object.__new__(PlanCard)
    object.__setattr__(card, "label", _StringSubclass(LABELS[0]))
    object.__setattr__(value, "plans", (card, *value.plans[1:]))
    assert _render(value, "monthly") == _closed()


def test_service_module_rebinding_and_function_metadata_are_inert(monkeypatch):
    baseline = _render(_view(), "monthly")
    attack = lambda *args, **kwargs: (True, "<script>bad()</script>", "VAT never")
    for name in (
        "_selection_model",
        "W10BillingPresentation",
        "w10_billing_presentation_authority_version",
        "w10_billing_presentation_source_identity",
        "Environment",
        "FileSystemLoader",
        "select_autoescape",
    ):
        monkeypatch.setattr(selection, name, attack)
    renderer = render_w10_billing_plan_selection_fragment
    assert renderer.__defaults__ is None
    assert renderer.__kwdefaults__ is None
    assert "__wrapped__" not in renderer.__dict__
    monkeypatch.setattr(renderer, "__defaults__", (attack,))
    monkeypatch.setattr(renderer, "__kwdefaults__", {"model": attack})
    monkeypatch.setitem(renderer.__dict__, "projector", attack)
    monkeypatch.setitem(renderer.__dict__, "__wrapped__", attack)
    output = _render(_view(), "monthly")
    assert output == baseline
    assert "script" not in output and "VAT never" not in output


def test_only_supported_renderer_is_public_and_template_contains_no_values():
    assert selection.__all__ == ("render_w10_billing_plan_selection_fragment",)
    template = TEMPLATE.read_text(encoding="utf-8")
    assert not any(label in template for label in LABELS)
    assert VAT not in template
    assert "|safe" not in template


def test_catalogue_has_three_canonical_ordered_price_free_links(client):
    _login(client)
    response = client.get("/v2/plans")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    hrefs = [f'/v2/plans/{key}' for key in KEYS]
    positions = [body.index(f'href="{href}"') for href in hrefs]
    assert positions == sorted(positions)
    assert all(body.count(f'href="{href}"') == 1 for href in hrefs)
    assert all(body.count(label) == 1 for label in LABELS)
    assert body.count(VAT) == 1


@pytest.mark.parametrize("key,label", tuple(zip(KEYS, LABELS)))
def test_authenticated_selection_route_shows_only_selected_value(client, key, label):
    _login(client)
    response = client.get(f"/v2/plans/{key}")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert body.count(label) == 1
    assert body.count(VAT) == 1
    assert all(other not in body for other in LABELS if other != label)
    assert CLOSED not in body


def test_selection_route_requires_existing_authentication(client):
    response = client.get("/v2/plans/monthly")
    assert response.status_code == 302
    assert "/v2/demo-login" in response.location


@pytest.mark.parametrize("path", (
    "/v2/plans/MONTHLY",
    "/v2/plans/Monthly",
    "/v2/plans/monthly/extra",
    "/v2/plans/%6donthly",
    "/v2/plans/monthly%2Fextra",
    "/v2/plans/%3Cscript%3E",
))
def test_malformed_case_encoded_and_extra_paths_share_value_free_page(client, path):
    _login(client)
    response = client.get(path)
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert body.count(CLOSED) == 1
    assert "£" not in body and VAT not in body
    assert not any(label in body for label in LABELS)


@pytest.mark.parametrize(
    "raw_environ",
    (
        {},
        {"RAW_URI": None},
        {"REQUEST_URI": 42},
        {"RAW_URI": _StringSubclass("/v2/plans/monthly")},
        {"RAW_URI": "/v2/plans/yearly"},
        {"REQUEST_URI": "/v2/plans/monthly/extra"},
        {"RAW_URI": "/v2/plans/%6donthly"},
        {"REQUEST_URI": "/v2/plans/monthly%2Fextra"},
        {
            "RAW_URI": "/v2/plans/monthly",
            "REQUEST_URI": "/v2/plans/yearly",
        },
        {
            "RAW_URI": "/v2/plans/monthly",
            "REQUEST_URI": "/v2/plans/%6donthly",
        },
    ),
)
def test_registered_route_requires_exact_unambiguous_raw_uri_evidence(app, raw_environ):
    body = _direct_registered_route(app, "monthly", raw_environ)
    assert body.count(CLOSED) == 1
    assert "£" not in body and VAT not in body
    assert not any(label in body for label in LABELS)


@pytest.mark.parametrize(
    "raw_environ",
    (
        {"RAW_URI": "/v2/plans/monthly"},
        {"REQUEST_URI": "/v2/plans/monthly?ignored=yes"},
        {
            "RAW_URI": "/v2/plans/monthly?one=1",
            "REQUEST_URI": "/v2/plans/monthly?two=2",
        },
    ),
)
def test_registered_route_accepts_exact_agreeing_raw_paths(app, raw_environ):
    body = _direct_registered_route(app, "monthly", raw_environ)
    assert body.count(LABELS[0]) == 1
    assert body.count(VAT) == 1
    assert CLOSED not in body


def test_registered_route_rejects_decoded_canonical_key_from_encoded_raw_path(app):
    body = _direct_registered_route(
        app,
        "monthly",
        {
            "RAW_URI": "/v2/plans/%6donthly",
            "REQUEST_URI": "/v2/plans/%6donthly",
        },
    )
    assert CLOSED in body
    assert LABELS[0] not in body and VAT not in body


def test_selection_query_is_inert_and_modifying_methods_are_rejected(
    client, monkeypatch
):
    # Flask-WTF signs the otherwise stable per-session CSRF value with the
    # current second. Freeze only that signing clock so exact response equality
    # continues to test query inertness rather than wall-clock coincidence.
    monkeypatch.setattr(TimestampSigner, "get_timestamp", lambda self: 1_700_000_000)
    _login(client)
    baseline = client.get("/v2/plans/monthly").get_data(as_text=True)
    hostile = client.get(
        "/v2/plans/monthly?price=1&plan=yearly&checkout=https://evil.invalid"
    ).get_data(as_text=True)
    assert hostile == baseline
    for method in ("post", "put", "patch", "delete"):
        assert getattr(client, method)("/v2/plans/monthly").status_code == 405


def test_selection_query_is_inert_across_csrf_signing_time_rollover(
    app, client, monkeypatch
):
    clock = {"now": 1_700_000_000}
    monkeypatch.setattr(
        TimestampSigner, "get_timestamp", lambda self: clock["now"]
    )
    _login(client)
    baseline = client.get("/v2/plans/monthly").get_data(as_text=True)
    clock["now"] += 1
    hostile = client.get(
        "/v2/plans/monthly?price=1&plan=yearly&checkout=https://evil.invalid"
    ).get_data(as_text=True)

    baseline_token = _csrf_token(baseline)
    hostile_token = _csrf_token(hostile)
    assert baseline_token != hostile_token
    assert _without_csrf_token(hostile) == _without_csrf_token(baseline)

    with client.session_transaction() as current_session:
        raw_token = current_session["csrf_token"]
    signer = URLSafeTimedSerializer(app.secret_key, salt="wtf-csrf-token")
    assert signer.loads(baseline_token, max_age=60) == raw_token
    assert signer.loads(hostile_token, max_age=60) == raw_token


def test_selection_route_preserves_no_store_and_security_headers(client):
    _login(client)
    response = client.get("/v2/plans/monthly")
    assert response.headers["Cache-Control"] == "no-store, max-age=0"
    assert response.headers["Pragma"] == "no-cache"
    assert response.headers["Expires"] == "0"
    assert "Cookie" in response.headers.getlist("Vary")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "payment=()" in response.headers["Permissions-Policy"]


def test_route_rebinding_defaults_dict_and_wrapped_metadata_cannot_inject(
    app, client, monkeypatch
):
    route_module = importlib.import_module("reserved.web.v2")
    route = route_module.billing_plan_selection
    attack = lambda *args, **kwargs: Markup("<script id='selection-attack'>bad()</script>")
    clock = {"now": 1_700_000_000}
    monkeypatch.setattr(
        TimestampSigner, "get_timestamp", lambda self: clock["now"]
    )
    assert route.__defaults__ is None
    assert route.__kwdefaults__ is None
    assert "__wrapped__" not in route.__dict__
    _login(client)
    baseline = client.get("/v2/plans/monthly").get_data(as_text=True)
    for name in (
        "INITIAL_BILLING_AUTHORITY",
        "present_w10_billing_presentation",
        "render_w10_billing_plan_selection_fragment",
        "_w10_plan_selection_fragment",
    ):
        monkeypatch.setattr(route_module, name, attack)
    monkeypatch.setattr(route, "__defaults__", (attack,))
    monkeypatch.setattr(route, "__kwdefaults__", {"renderer": attack})
    monkeypatch.setitem(route.__dict__, "fragment_supplier", attack)
    monkeypatch.setitem(route.__dict__, "template_renderer", attack)
    monkeypatch.setitem(route.__dict__, "__wrapped__", attack)
    clock["now"] += 1
    body = client.get("/v2/plans/monthly").get_data(as_text=True)

    baseline_token = _csrf_token(baseline)
    body_token = _csrf_token(body)
    assert baseline_token != body_token
    assert _without_csrf_token(body) == _without_csrf_token(baseline)

    with client.session_transaction() as current_session:
        raw_token = current_session["csrf_token"]
    signer = URLSafeTimedSerializer(app.secret_key, salt="wtf-csrf-token")
    assert signer.loads(baseline_token, max_age=60) == raw_token
    assert signer.loads(body_token, max_age=60) == raw_token
    assert "selection-attack" not in body and "bad()" not in body


def test_route_performs_no_billing_domain_database_or_network_action(app, client, monkeypatch):
    route_module = importlib.import_module("reserved.web.v2")
    app.config["WTF_CSRF_ENABLED"] = True
    _login(client)

    def forbidden(*args, **kwargs):
        raise AssertionError("selected-plan route attempted a state or network action")

    for name in (
        "get_or_create_user", "list_connections_for_user", "persist_match_result",
        "seed_demo_data", "YapilyClient",
    ):
        monkeypatch.setattr(route_module, name, forbidden)
    with client.session_transaction() as session:
        before = dict(session)
    response = client.get("/v2/plans/monthly")
    with client.session_transaction() as session:
        after = dict(session)
    assert response.status_code == 200
    assert set(before) <= set(after)
    assert set(after) - set(before) <= {"csrf_token"}
    assert all(after[key] == value for key, value in before.items())


def test_trusted_fragment_is_internal_and_page_has_no_safe_filter_or_values():
    route_source = V2.read_text(encoding="utf-8")
    page = PAGE.read_text(encoding="utf-8")
    assert "trusted_html_type(renderer(presentation, plan_key))" in route_source
    assert "billing_plan_selection_fragment|safe" not in page
    assert not any(label in page for label in LABELS)
    assert VAT not in page
