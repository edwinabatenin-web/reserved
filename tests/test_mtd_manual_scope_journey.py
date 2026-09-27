"""Actual synthetic dashboard/form/admission/issuer/live-renderer journey."""
from datetime import datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
import importlib

import pytest
from werkzeug.datastructures import MultiDict

import reserved.database as db
from reserved import create_app
from reserved.auth import _SK_USER_ID
from reserved.services import mtd_manual_source_admission as admission
from reserved.services.mtd_scope_indication import as_mtd_scope_mapping, MtdScopeIndication

route = importlib.import_module("reserved.web.v2")
URL = "/v2/mtd/scope-indication"


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 5, 12, tzinfo=timezone.utc)


class Form(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.fields = {}
        self.links = []
        self.inside = False
        self.select = None
        self.token = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.links.append(attrs.get("href"))
        if tag == "meta" and attrs.get("name") == "csrf-token":
            self.token = attrs["content"]
        if tag == "form":
            self.inside = attrs.get("action") == URL
        if self.inside and tag == "input":
            self.fields[attrs["name"]] = attrs.get("value", "")
        if self.inside and tag == "select":
            self.select = attrs["name"]
        if self.select and tag == "option" and self.select not in self.fields:
            self.fields[self.select] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.inside = False
        if tag == "select":
            self.select = None


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "synthetic.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("MTD_MANUAL_SCOPE_ENABLED", "1")
    monkeypatch.setattr(route, "datetime", Clock)
    app = create_app()
    app.config.update(TESTING=True)
    client = app.test_client()
    owner = db.get_or_create_user("mtd-manual-a", email="a@example.test")
    other = db.get_or_create_user("mtd-manual-b", email="b@example.test")
    with client.session_transaction() as session:
        session[_SK_USER_ID] = owner
    return app, client, owner, other


def valid(year="2024-25", **changes):
    start = int(year[:4])
    facts = dict(assessment_year=year, submitted_on="2026-01-31" if year == "2024-25" else "2026-04-30",
        source_basis="submitted_return", return_revision="original_unamended", registered_for_sa="yes",
        acting_capacity="own_individual", relevant_tax_region="england", residence="ordinary_uk",
        ni_held_before_boundary="yes", hmrc_exemption_position="none_known",
        prior_mtd_position="not_previously_enrolled_or_under_an_earlier_requirement",
        all_sources_once="yes", own_shares="yes", vat_or_special_treatment="no", source_version_conflict="no",
        source_1_kind="sole_trade", source_1_gross_income="50000.01", source_1_period_start=f"{start}-04-06",
        source_1_period_end=f"{start+1}-04-05", source_1_lifecycle="active_throughout_and_still_continuing",
        source_1_amount_basis="own_gross_before_expenses")
    facts.update({f"{name}_{year}": "no" for year in admission.SCREEN_YEARS for name, _ in admission.SPECIAL_FACTS})
    facts.update(changes)
    return facts


def form(client):
    page = client.get(URL)
    assert page.status_code == 200
    return Form(page.get_data(as_text=True))


def post(client, facts=None):
    rendered = form(client)
    data = rendered.fields
    data.update(valid() if facts is None else facts)
    return client.post(URL, data=data)


def nonnumeric(response, status=200):
    assert response.status_code == status
    html = response.get_data(as_text=True)
    assert "More information needed" in html and "£" not in html
    assert "Qualifying gross income</dt>" not in html
    return html


@pytest.mark.parametrize("year,amount,threshold,start", [
    ("2024-25", "0", "50000", "2026-04-06"),
    ("2024-25", "49999.99", "50000", "2026-04-06"),
    ("2024-25", "50000", "50000", "2026-04-06"),
    ("2024-25", "50000.01", "50000", "2026-04-06"),
    ("2025-26", "29999.99", "30000", "2027-04-06"),
    ("2025-26", "30000", "30000", "2027-04-06"),
    ("2025-26", "30000.01", "30000", "2027-04-06"),
])
def test_real_discovery_form_issuer_live_renderer_and_thresholds(env, monkeypatch, year, amount, threshold, start):
    client = env[1]
    assert URL in Form(client.get("/v2/dashboard").get_data(as_text=True)).links
    captured = []
    real_render = route._render_manual_mtd
    def render(handle):
        assert type(handle) is MtdScopeIndication
        captured.append(as_mtd_scope_mapping(handle))
        return real_render(handle)
    monkeypatch.setattr(route, "_render_manual_mtd", render)
    response = post(client, valid(year, source_1_gross_income=amount))
    assert response.status_code == 200
    value = captured[0]
    assert value["information_complete"] is True
    assert value["qualifying_income"] == Decimal(amount)
    assert value["threshold"] == Decimal(threshold)
    assert value["distance_from_threshold"] == Decimal(threshold) - Decimal(amount)
    assert value["effective_start_date"] == start
    html = response.get_data(as_text=True)
    assert start in html and "future tax year" not in html
    assert "not saved" in html.lower() and "Employment, dividends, savings" in html


SUPPORTED = valid()
NEGATIVES = [(name, choice) for name, _, choices in admission.QUESTIONS
             for choice in ("",) + choices
             if choice not in (("england", "wales", "northern_ireland")
                               if name == "relevant_tax_region" else (SUPPORTED[name],))]


@pytest.mark.parametrize("region", ["england", "wales", "northern_ireland"])
def test_supported_regions_are_distinct_from_residence(env, region):
    response = post(env[1], valid(relevant_tax_region=region))
    assert response.status_code == 200
    assert "£50,000.01" in response.get_data(as_text=True)


@pytest.mark.parametrize("field,value", NEGATIVES)
def test_each_admission_question_negative_cannot_produce_numeric(env, field, value):
    nonnumeric(post(env[1], valid(**{field: value})))


@pytest.mark.parametrize("field", [f"{name}_{year}" for year in admission.SCREEN_YEARS for name, _ in admission.SPECIAL_FACTS])
@pytest.mark.parametrize("value", ["yes", "unknown", ""])
def test_each_year_specific_special_fact_refuses(env, field, value):
    nonnumeric(post(env[1], valid(**{field: value})))


@pytest.mark.parametrize("changes", [
    {"assessment_year": "2026-27"}, {"assessment_year": "2027-28"}, {"assessment_year": ""},
    {"submitted_on": ""}, {"submitted_on": "2025-04-05"}, {"submitted_on": "2026-04-07"},
    {"source_1_period_start": "2024-04-07"}, {"source_1_period_end": "2025-04-04"},
    {"source_1_lifecycle": "started_or_ceased"}, {"source_1_lifecycle": "unknown"},
    {"source_1_lifecycle": ""}, {"source_1_kind": ""},
    {"source_1_amount_basis": "whole_joint_or_net"}, {"source_1_amount_basis": "special_or_uncertain"},
    {"source_1_amount_basis": "unknown"}, {"source_1_amount_basis": ""},
    {"source_1_gross_income": ""}, {"source_1_kind": "unknown"},
    {"source_1_period_start": ""}, {"source_1_period_end": ""},
])
def test_unknown_partial_future_or_unsupported_source_is_not_numeric(env, changes):
    nonnumeric(post(env[1], valid(**changes)))


@pytest.mark.parametrize("changes", [
    {"threshold": "1"}, {"as_of": "2025-01-01"}, {"owner_id": "2"}, {"business_id": "forged"},
    {"source_1_id": "forged"}, {"source_inventory_complete": "true"}, {"result": "applies"},
    {"assessment_year": "2024/25"}, {"submitted_on": "2026-02-30"},
    {"source_1_gross_income": "-1"}, {"source_1_gross_income": "NaN"}, {"source_1_gross_income": "Infinity"},
    {"source_1_gross_income": "1e5"}, {"source_1_gross_income": "50,000"}, {"source_1_gross_income": "0.001"},
    {"source_1_gross_income": "10000000000"}, {"source_1_gross_income": "x" * 33000},
    {"acting_capacity": "<script>private</script>"}, {"source_1_period_end": "20250230"},
])
def test_malformed_or_forged_is_bounded_400(env, changes, caplog):
    html = nonnumeric(post(env[1], valid(**changes)), 400)
    assert "<script>private" not in html + caplog.text and caplog.text == ""


def test_source_grouping_distinct_equal_trades_and_bound(env):
    client = env[1]
    data = valid()
    for index in range(2, 13):
        data.update({f"source_{index}_{key}": data[f"source_1_{key}"] for key in admission.ROW_FIELDS})
    response = post(client, data)
    assert response.status_code == 200 and "£600,000.12" in response.get_data(as_text=True)
    data["source_13_kind"] = "sole_trade"
    nonnumeric(post(client, data))
    data = valid(source_1_kind="uk_property")
    data.update({f"source_2_{key}": data[f"source_1_{key}"] for key in admission.ROW_FIELDS})
    nonnumeric(post(client, data))
    data["source_2_kind"] = "foreign_property"
    assert "£100,000.02" in post(client, data).get_data(as_text=True)


def test_boundaries_derive_from_rules_and_server_asof(env):
    metadata = admission.manual_year_metadata(Clock.now().date())
    assert metadata[0][4].isoformat() == "2026-04-06"
    assert metadata[1][4].isoformat() == "2026-09-05"
    assert post(env[1], valid(submitted_on="2026-04-06")).status_code == 200
    assert "More information needed" not in post(env[1], valid("2025-26", submitted_on="2026-09-05")).get_data(as_text=True)
    nonnumeric(post(env[1], valid("2025-26", submitted_on="2026-09-06")))


def test_confirmed_empty_inventory_is_zero_but_unconfirmed_is_unknown(env):
    facts = valid(**{f"source_1_{key}": "" for key in admission.ROW_FIELDS})
    assert "£0.00" in post(env[1], facts).get_data(as_text=True)
    facts["all_sources_once"] = "unknown"
    nonnumeric(post(env[1], facts))


@pytest.mark.parametrize("gross", ["0", None])
@pytest.mark.parametrize("changes", [
    {"prior_mtd_position": "existing_or_previous_requirement"},
    {"prior_mtd_position": "unknown"}, {"ni_held_before_boundary": "no"},
])
def test_zero_or_empty_sources_cannot_bypass_continuation_or_ni_boundary(env, gross, changes):
    facts = valid(source_1_gross_income=gross or "0", **changes)
    if gross is None:
        facts.update({f"source_1_{key}": "" for key in admission.ROW_FIELDS})
    html = nonnumeric(post(env[1], facts))
    assert "not a finding that you are exempt" in html


def test_period_not_yet_complete_refuses_even_with_future_return(env, monkeypatch):
    class Earlier(Clock):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 4, 5, 12, tzinfo=timezone.utc)
    monkeypatch.setattr(route, "datetime", Earlier)
    nonnumeric(post(env[1], valid("2025-26")))


@pytest.mark.parametrize("content_type,data", [
    ("application/json", '{"assessment_year":"2024-25"}'),
    ("text/plain", "assessment_year=2024-25"),
    ("multipart/form-data", {"assessment_year": "2024-25"}),
])
def test_only_bounded_urlencoded_body_admitted(env, content_type, data):
    token = form(env[1]).token
    nonnumeric(env[1].post(URL, data=data, content_type=content_type,
                          headers={"X-CSRFToken": token}), 400)


@pytest.mark.parametrize("values", [[], {"source_1_gross_income": 0}, {1: "yes"},
                                      {"source_basis": "x" * 101}])
def test_internal_admission_rejects_nonstring_or_oversize_facts(values):
    with pytest.raises(ValueError):
        admission.admit_manual_mtd(values, as_of=Clock.now().date())


def test_duplicates_never_silently_choose_a_row_or_fact(env):
    client = env[1]
    parsed = form(client)
    data = MultiDict({**parsed.fields, **valid()})
    data.add("source_1_gross_income", "0")
    nonnumeric(client.post(URL, data=data), 400)
    assert client.get(URL + "?assessment_year=2024-25").status_code == 400


def test_owner_csrf_nostore_and_no_financial_state(env, caplog):
    _, client, owner, other = env
    parsed = form(client)
    with client.session_transaction() as session:
        session_before = dict(session)
    with db._connection() as conn:
        before = tuple(conn.iterdump())
    response = client.post(URL, data={**parsed.fields, **valid()})
    assert response.status_code == 200
    assert "no-store" in response.headers["Cache-Control"] and "Cookie" in response.headers["Vary"]
    with client.session_transaction() as session:
        assert dict(session) == session_before
    with db._connection() as conn:
        assert tuple(conn.iterdump()) == before
    assert caplog.text == "" and "manual-" not in response.get_data(as_text=True)
    assert client.post(URL, data=valid()).status_code == 400
    assert client.post(URL, data=valid(), headers={"X-CSRFToken": "bad"}).status_code == 400
    with client.session_transaction() as session:
        session[_SK_USER_ID] = other
    assert "50000.01" not in client.get(URL).get_data(as_text=True)
    with db._connection() as conn:
        conn.execute("DELETE FROM users WHERE id = ?", (other,))
    assert client.get(URL).status_code == 403
    with client.session_transaction() as session:
        session.pop(_SK_USER_ID)
    assert client.get(URL).status_code == 302


def test_fresh_changed_facts_reissue_local_sources_without_financial_reads(env, monkeypatch):
    sources_seen, handles = [], []
    real_issue = admission._issue
    def issue(sources, **kwargs):
        sources_seen.append(sources)
        handle = real_issue(sources, **kwargs)
        handles.append(handle)
        return handle
    def forbidden(*args, **kwargs):
        pytest.fail("Manual MTD must not read financial/provider state")
    monkeypatch.setattr(admission, "_issue", issue)
    for name in ("get_transactions", "get_transaction_summary", "list_connections_for_user",
                 "list_accounts", "list_invoices", "YapilyClient"):
        monkeypatch.setattr(route, name, forbidden)
    first = post(env[1], valid(source_1_gross_income="0"))
    second = post(env[1], valid(source_1_gross_income="50000.01"))
    assert "Not currently indicated" in first.get_data(as_text=True)
    assert "Worth reviewing" in second.get_data(as_text=True)
    assert handles[0] is not handles[1]
    assert sources_seen[0][0].source_id != sources_seen[1][0].source_id
    assert all(len(sources) == 1 for sources in sources_seen)  # no fabricated excluded rows
    for sources in sources_seen:
        source = sources[0]
        assert source.business_id == source.source_id and source.complete is True
        assert source.kind.value == "sole_trade"
    blank = env[1].get(URL)
    assert "no-store" in blank.headers["Cache-Control"]
    assert "50000.01" not in blank.get_data(as_text=True)


@pytest.mark.parametrize("owner", [True, "1", 1.0, -1, {"id": 1}])
def test_malformed_signed_owner_denied(env, owner):
    with env[1].session_transaction() as session:
        session[_SK_USER_ID] = owner
    assert env[1].get(URL).status_code == 403


@pytest.mark.parametrize("flag", ["", "0", "true", "yes", " 1 "])
def test_strict_flag_and_dashboard_discovery(env, monkeypatch, flag):
    monkeypatch.setenv("MTD_MANUAL_SCOPE_ENABLED", flag)
    assert env[1].get(URL).status_code == 404
    assert URL not in Form(env[1].get("/v2/dashboard").get_data(as_text=True)).links


@pytest.mark.parametrize("key,value", [("FLASK_ENV", "production"), ("CLERK_PUBLISHABLE_KEY", "pk_live_synthetic")])
def test_explicit_flag_is_not_overridden_by_environment_signal(env, monkeypatch, key, value):
    data = {**form(env[1]).fields, **valid()}
    monkeypatch.setenv(key, value)
    assert env[1].get(URL).status_code == 200
    response = env[1].post(URL, data=data)
    assert response.status_code == 200 and "Worth reviewing" in response.get_data(as_text=True)
    assert URL in Form(env[1].get("/v2/dashboard").get_data(as_text=True)).links


@pytest.mark.parametrize("key,value", [("FLASK_ENV", "production"), ("CLERK_PUBLISHABLE_KEY", "pk_live_synthetic")])
def test_environment_signal_never_enables_journey_without_exact_flag(env, monkeypatch, key, value):
    monkeypatch.delenv("MTD_MANUAL_SCOPE_ENABLED", raising=False)
    monkeypatch.setenv(key, value)
    assert env[1].get(URL).status_code == 404
    assert URL not in Form(env[1].get("/v2/dashboard").get_data(as_text=True)).links
