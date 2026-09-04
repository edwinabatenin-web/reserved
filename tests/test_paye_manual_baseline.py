"""Real synthetic Flask capture/review requests; no provider or live database."""
from datetime import datetime, timezone
from html.parser import HTMLParser
import importlib

import pytest
from werkzeug.datastructures import MultiDict

import reserved.database as db
from reserved import create_app
from reserved.auth import _SK_USER_ID
from reserved.engines.paye_evidence_capture import CaptureSource
from reserved.engines.paye_reconciliation import Completeness, EvidenceKind
from reserved.services import paye_manual_baseline as service

route = importlib.import_module("reserved.web.v2")
URL = "/v2/paye/manual-baseline"


class Parser(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.token = None
        self.fields = set()
        self.links = []
        self.inside = False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name") == "csrf-token":
            self.token = attrs["content"]
        if tag == "form":
            self.inside = attrs.get("action") == URL
        if self.inside and tag in ("input", "select") and attrs.get("name"):
            self.fields.add(attrs["name"])
        if tag == "a":
            self.links.append(attrs.get("href"))

    def handle_endtag(self, tag):
        if tag == "form":
            self.inside = False


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 4, 12, tzinfo=timezone.utc)


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "synthetic.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("PAYE_MANUAL_BASELINE_ENABLED", "1")
    monkeypatch.setattr(route, "datetime", Clock)
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    owner = db.get_or_create_user("baseline-a", email="a@example.test")
    other = db.get_or_create_user("baseline-b", email="b@example.test")
    with client.session_transaction() as session:
        session[_SK_USER_ID] = owner
    return app, client, owner, other


def facts(**changes):
    values = dict(gross_pay_to_date="12345.67", tax_paid_to_date="2345.60", tax_code="1257L",
                  pay_frequency="monthly", pension_treatment="net_pay", effective_through="2026-08-31",
                  confirmation="yes")
    values.update(changes)
    return values


def csrf(client):
    response = client.get(URL)
    assert response.status_code == 200
    return Parser(response.get_data(as_text=True)).token


def post(client, values=None):
    return client.post(URL, data=facts() if values is None else values,
                       headers={"X-CSRFToken": csrf(client)})


def test_discovery_form_normalizer_and_all_review_fields(env, monkeypatch, caplog):
    _, client, _, _ = env
    assert URL in Parser(client.get("/v2/dashboard").get_data(as_text=True)).links
    form = client.get(URL)
    assert Parser(form.get_data(as_text=True)).fields == service.FIELDS | {"csrf_token"}
    calls = []
    real = service.normalise_paye_evidence
    def observe(capture):
        evidence = real(capture)
        calls.append((capture, evidence))
        return evidence
    monkeypatch.setattr(service, "normalise_paye_evidence", observe)
    token = csrf(client)
    with client.session_transaction() as session:
        before_session = dict(session)
    with db._connection() as conn:
        before_db = tuple(conn.iterdump())
    response = client.post(URL, data=facts(), headers={"X-CSRFToken": token})
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    for text in ("£12345.67", "£2345.60", "1257L", "Monthly", "Net pay", "2026-08-31",
                 "2026-09-04", "2026/27", "Partial", "Manual", "not saved", "not an annual tax estimate"):
        assert text in html
    assert len(calls) == 1
    capture, evidence = calls[0]
    assert capture.source is CaptureSource.MANUAL and capture.document_type is None
    assert evidence.kind is EvidenceKind.MANUAL and evidence.completeness is Completeness.PARTIAL
    assert evidence.tax_year == "2026-27"
    assert capture.evidence_id not in html and capture.employment_id not in html
    assert "<form method=\"post\" action=\"/v2/paye/manual-baseline\"" not in html
    assert "no-store" in response.headers["Cache-Control"] and "Cookie" in response.headers["Vary"]
    with client.session_transaction() as session:
        assert dict(session) == before_session
    with db._connection() as conn:
        assert tuple(conn.iterdump()) == before_db
    assert caplog.text == ""


def test_missing_and_zero_are_distinct_and_start_over_is_blank(env):
    client = env[1]
    for values, expected in [(dict(effective_through="2026-08-31", confirmation="yes"), "Unknown"),
                             (facts(gross_pay_to_date="0", tax_paid_to_date="0.00"), "£0.00")]:
        response = post(client, values)
        assert response.status_code == 200 and expected in response.get_data(as_text=True)
    html = client.get(URL).get_data(as_text=True)
    assert "12345.67" not in html and "2345.60" not in html


@pytest.mark.parametrize("field,value", [
    ("gross_pay_to_date", "-1"), ("gross_pay_to_date", "1e3"), ("gross_pay_to_date", "1,000"),
    ("gross_pay_to_date", " 1000"), ("gross_pay_to_date", "NaN"), ("tax_paid_to_date", "Infinity"),
    ("tax_paid_to_date", "0.001"), ("gross_pay_to_date", "10000000000"),
    ("tax_code", "<script>private</script>"), ("tax_code", "x" * 33),
    ("pay_frequency", "daily"), ("pension_treatment", "default"),
    ("effective_through", "2026-09-05"), ("effective_through", "2026-04-05"),
    ("effective_through", "2026-02-30"), ("effective_through", "20260831"),
    ("confirmation", ""), ("confirmation", "true"), ("confirmation", "no"),
    ("tax_year", "2025/26"), ("source", "source_document"), ("employment_id", "forged"),
    ("evidence_id", "forged"), ("owner_id", "2"), ("supersedes_evidence_id", "forged"),
    ("observed_on", "2027-01-01"), ("gross_pay_to_date", "x" * 5000),
])
def test_invalid_forged_and_oversized_are_safe_non_results(env, field, value, caplog):
    response = post(env[1], facts(**{field: value}))
    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert "Review your manual facts" not in html and "We could not review" in html
    assert "<script>private" not in html + caplog.text
    assert caplog.text == ""


def test_duplicate_and_wrong_request_formats(env):
    client = env[1]
    data = MultiDict(facts())
    data.add("gross_pay_to_date", "0")
    assert post(client, data).status_code == 400
    assert client.post(URL, json=facts(), headers={"X-CSRFToken": csrf(client)}).status_code == 400
    assert client.get(URL + "?owner_id=2").status_code == 400


@pytest.mark.parametrize("value", ["", "0", "true", "yes", " 1 "])
def test_strict_disabled_flag_hides_discovery_and_denies(env, monkeypatch, value):
    monkeypatch.setenv("PAYE_MANUAL_BASELINE_ENABLED", value)
    client = env[1]
    assert client.get(URL).status_code == 404
    assert URL not in Parser(client.get("/v2/dashboard").get_data(as_text=True)).links


@pytest.mark.parametrize("key,value", [("FLASK_ENV", "production"), ("CLERK_PUBLISHABLE_KEY", "pk_live_synthetic")])
def test_production_signals_deny(env, monkeypatch, key, value):
    client = env[1]
    token = csrf(client)
    monkeypatch.setenv(key, value)
    assert client.get(URL).status_code == 404
    assert client.post(URL, data=facts(), headers={"X-CSRFToken": token}).status_code == 404
    assert URL not in Parser(client.get("/v2/dashboard").get_data(as_text=True)).links


@pytest.mark.parametrize("owner", [True, "1", 1.0, -1, 999999, {"id": 1}])
def test_malformed_or_missing_signed_owner_is_not_authorized(env, owner):
    client = env[1]
    with client.session_transaction() as session:
        session[_SK_USER_ID] = owner
    assert client.get(URL).status_code == 403


def test_deleted_owner_auth_csrf_and_owner_isolation(env):
    _, client, owner, other = env
    token = csrf(client)
    assert client.post(URL, data=facts()).status_code == 400
    assert client.post(URL, data=facts(), headers={"X-CSRFToken": "bad"}).status_code == 400
    with client.session_transaction() as session:
        session[_SK_USER_ID] = other
    assert "12345.67" not in client.get(URL).get_data(as_text=True)
    with db._connection() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (other,))
    assert client.get(URL).status_code == 403
    with client.session_transaction() as session:
        session.pop(_SK_USER_ID)
    assert client.get(URL).status_code == 302
    assert client.post(URL, data=facts(), headers={"X-CSRFToken": token}).status_code == 302


def test_prior_supported_year_and_exact_date_boundaries(env, monkeypatch):
    client = env[1]
    assert post(client, facts(effective_through="2026-04-06")).status_code == 200
    assert post(client, facts(effective_through="2026-09-04")).status_code == 200
    from reserved.engines import tax_config
    monkeypatch.setattr(tax_config, "TAX_YEAR", "2025/26")
    response = post(client, facts(effective_through="2026-04-05"))
    assert response.status_code == 200 and "2025/26" in response.get_data(as_text=True)
    monkeypatch.setattr(tax_config, "TAX_YEAR", "unknown")
    assert client.get(URL).status_code == 404


def test_no_calculation_or_forecast_called(env, monkeypatch):
    from reserved.engines import paye_reconciliation, integrated_annual_position
    from reserved.services import paye_future_pay_forecast
    def forbidden(*a, **k):
        pytest.fail("capture invoked calculation/forecast")
    monkeypatch.setattr(integrated_annual_position, "calculate_annual_position", forbidden)
    for module in (paye_reconciliation, paye_future_pay_forecast):
        for name in dir(module):
            if name.startswith(("reconcile_", "forecast_", "compose_")):
                monkeypatch.setattr(module, name, forbidden)
    assert post(env[1]).status_code == 200


def test_template_autoescapes_even_hostile_projection_text(env, monkeypatch):
    monkeypatch.setattr(route, "review_manual_baseline", lambda *a, **k: (("Tax code", '<script>private</script>'),))
    response = post(env[1])
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "&lt;script&gt;private&lt;/script&gt;" in html
    assert "<script>private</script>" not in html


@pytest.mark.parametrize("frequency", ["weekly", "fortnightly", "four_weekly", "monthly", "annually", "other", "unknown"])
def test_all_existing_frequency_choices_review_without_forecast(env, frequency):
    response = post(env[1], facts(pay_frequency=frequency))
    assert response.status_code == 200
    assert frequency.replace("_", " ").capitalize() in response.get_data(as_text=True)


@pytest.mark.parametrize("pension", ["none", "salary_sacrifice", "net_pay", "relief_at_source", "unknown"])
def test_all_existing_pension_choices_review_without_adjustment(env, pension):
    response = post(env[1], facts(pension_treatment=pension, gross_pay_to_date="9999999999.99"))
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert pension.replace("_", " ").capitalize() in html and "£9999999999.99" in html


def test_endpoint_only_reads_user_existence(env, monkeypatch):
    client = env[1]
    token = csrf(client)
    reads = []
    real = route.get_user
    def user(uid):
        reads.append(uid)
        return real(uid)
    monkeypatch.setattr(route, "get_user", user)
    def forbidden(*a, **k):
        pytest.fail("capture read existing financial state")
    for name in ("list_connections_for_user", "get_invoice_counts_for_user", "get_transactions", "build_dashboard"):
        monkeypatch.setattr(route, name, forbidden)
    response = client.post(URL, data=facts(), headers={"X-CSRFToken": token})
    assert response.status_code == 200 and reads == [env[2]]
