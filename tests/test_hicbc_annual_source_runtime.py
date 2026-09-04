"""Real non-production Flask requests; synthetic database/owners only."""
from contextlib import contextmanager
import json
import importlib
import threading
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from flask_wtf.csrf import generate_csrf

import reserved.database as db
from reserved import create_app
from reserved.auth import _SK_USER_ID
from reserved.services import hicbc_annual_source_runtime as runtime
route = importlib.import_module("reserved.web.hicbc")


URL = "/v2/hicbc/annual-preview"
YEAR = "2026/27"


def facts(**changes):
    value = {name: "0" for name in runtime._AMOUNTS}
    value.update(schema_version=runtime.SCHEMA_VERSION, tax_year=YEAR,
                 country="England", full_tax_year_including_known_future=True,
                 employment_basis="all_jobs_taxable_after_salary_sacrifice_and_net_pay",
                 uk_resident=True, other_ani_adjustments="none", employment_income="70000")
    value.update(changes)
    return value


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "synthetic.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("HICBC_ENABLED", "1")
    monkeypatch.setenv("HICBC_ANNUAL_PREVIEW_ENABLED", "1")
    app = create_app()
    app.config.update(TESTING=True)
    # Test-only token endpoint uses the real Flask-WTF signing/session mechanism.
    app.add_url_rule("/test-csrf", "test_csrf", lambda: generate_csrf())
    client = app.test_client()
    owner = db.get_or_create_user("synthetic-a", email="a@example.test", display_name="A")
    other = db.get_or_create_user("synthetic-b", email="b@example.test", display_name="B")
    with client.session_transaction() as session:
        session[_SK_USER_ID] = owner
    seed(owner)
    return app, client, owner, other


def seed(owner, **changes):
    row = dict(tax_year=YEAR, child_benefit_claimant="person", child_benefit_annual="1406.60",
               has_relevant_partner=1, relationship_covers_full_year=1,
               partner_status_period_semantics="status_answer_full_year", representation="point",
               partner_ani_point="50000", completeness="complete_for_purpose", recency_state="current",
               confirmed_at="2026-09-04", observed_at="2026-09-04")
    row.update(changes)
    db.save_hicbc_estimate(owner, row)


def post(client, payload=None, **kwargs):
    token = client.get("/test-csrf").get_data(as_text=True)
    return client.post(URL, json=facts() if payload is None else payload,
                       headers={"X-CSRFToken": token}, **kwargs)


def test_real_request_uses_engine_ani_not_legacy_profile(env, monkeypatch, caplog):
    app, client, owner, _ = env
    db.save_profile_by_user(owner, {"income_estimate": 1, "tax_year": YEAR,
                                   "notes": '{"unrelated":"preserve"}'})
    before = db.get_profile_by_user(owner)
    with db._connection() as conn:
        all_rows_before = tuple(conn.iterdump())
    captured = []
    real = runtime.calculate_annual_position
    def observe(*args, **kwargs):
        result = real(*args, **kwargs)
        captured.append(result)
        return result
    monkeypatch.setattr(runtime, "calculate_annual_position", observe)
    response = post(client, facts(employment_income="60000", sole_trade_profit="5000",
                    savings_interest="1000", dividends="1000", uk_property_receipts="10000",
                    uk_property_allowable_expenses="4000", brought_forward_uk_property_loss="1000",
                    foreign_property_gross_receipts="3000", foreign_property_allowable_expenses="1000",
                    gross_ras_pension="4000"))
    assert response.status_code == 200
    assert captured[0].adjusted_net_income == Decimal("70000.00")
    assert "blind_persons_allowance_facts_incomplete" in captured[0].limitations
    assert response.json["projected_user_hicbc"] == "703.00"
    assert "no-store" in response.headers["Cache-Control"]
    assert "Cookie" in response.headers["Vary"]
    assert db.get_profile_by_user(owner) == before
    with db._connection() as conn:
        assert tuple(conn.iterdump()) == all_rows_before
    body = response.get_data(as_text=True) + caplog.text
    for forbidden in ("70000", "70,000", "50000", "50,000", "adjusted_net_income",
                      "total_liability", "user_id", "evidence_id", "reserve", "payment"):
        assert forbidden not in body
    assert set(response.json) == {"tax_year", "responsibility_status", "calculation_status",
        "headline", "projected_user_hicbc", "possible_charge_low", "possible_charge_high",
        "household_change_status", "based_on_partner_estimate", "messages"}


@pytest.mark.parametrize("switch", ["", "0", "true", "yes", "banana", " 1 "])
def test_strict_annual_switch(env, monkeypatch, switch):
    monkeypatch.setenv("HICBC_ANNUAL_PREVIEW_ENABLED", switch)
    assert post(env[1]).status_code == 404


@pytest.mark.parametrize("key,value", [("HICBC_ENABLED", "0"), ("FLASK_ENV", "production"),
                                      ("CLERK_PUBLISHABLE_KEY", "pk_live_synthetic")])
def test_other_gate_and_production_deny_execution(env, monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    monkeypatch.setattr(runtime, "calculate_annual_position", lambda *a, **k: pytest.fail("engine called"))
    assert post(env[1]).status_code == 404


def test_auth_and_real_csrf_distinct(env):
    app, client, _, _ = env
    assert client.post(URL, json=facts()).status_code == 400
    assert client.post(URL, json=facts(), headers={"X-CSRFToken": "invalid"}).status_code == 400
    anonymous = app.test_client()
    assert post(anonymous).status_code == 302
    assert post(client).status_code == 200


@pytest.mark.parametrize("field", tuple(runtime._REQUIRED))
def test_every_required_answer_must_be_present(env, field):
    payload = facts()
    del payload[field]
    response = post(env[1], payload)
    assert response.status_code == 400
    assert response.json["projected_user_hicbc"] is None


@pytest.mark.parametrize("changes", [
    {"employment_income": None}, {"employment_income": 70000}, {"employment_income": True},
    {"employment_income": "NaN"}, {"employment_income": "Infinity"}, {"employment_income": "1e5"},
    {"employment_income": "100000000"}, {"employment_income": "-1"}, {"employment_income": "1.001"},
    {"full_tax_year_including_known_future": False}, {"employment_basis": "ytd"},
    {"employment_basis": "gross_before_pension"}, {"gross_ras_pension": "unknown"},
    {"country": "Scotland"}, {"country": "Ireland"}, {"tax_year": "2025/26"},
    {"uk_resident": None}, {"uk_resident": False}, {"other_ani_adjustments": "gift_aid"},
    {"foreign_property_allowable_expenses": "1"}, {"caller_ani": "70000"},
    {"adjusted_net_income": "70000"}, {"user_id": 1}, {"business_id": "x"},
    {"admitted": True}, {"current": True}, {"trust": True}, {"permission": True},
    {"hicbc": "0"}, {"income": "70000"},
])
def test_unsupported_unknown_or_forged_facts_fail_closed(env, changes):
    response = post(env[1], facts(**changes))
    assert response.status_code == 400
    assert response.json["projected_user_hicbc"] is None


@pytest.mark.parametrize("nation", ["England", "Wales", "Northern Ireland"])
def test_supported_geography_and_unrelated_total_limitations(env, nation):
    response = post(env[1], facts(country=nation, residential_finance_costs="500", foreign_tax_paid="100"))
    assert response.status_code == 200
    assert response.json["projected_user_hicbc"] == "703.00"


def test_owner_year_isolation_and_no_new_rows(env):
    _, client, owner, other = env
    seed(other, partner_ani_point="90000")
    seed(owner, tax_year="2025/26", partner_ani_point="90000")
    before = db.get_hicbc_estimate(owner, YEAR)
    assert post(client).json["projected_user_hicbc"] == "703.00"
    assert db.get_hicbc_estimate(owner, YEAR) == before
    with client.session_transaction() as session:
        session[_SK_USER_ID] = other
    assert post(client).json["projected_user_hicbc"] == "0.00"


@pytest.mark.parametrize("changes", [
    {"representation": "range", "partner_ani_point": None, "partner_ani_low": "65000", "partner_ani_high": "75000"},
    {"recency_state": "stale"}, {"completeness": "partial"},
    {"relationship_covers_full_year": None},
])
def test_stored_uncertainty_not_upgraded(env, changes):
    seed(env[2], **changes)
    response = post(env[1])
    assert response.status_code == 200
    assert response.json["projected_user_hicbc"] is None
    assert response.json["calculation_status"] != "calculated"


def link(a, b):
    token = db.create_hicbc_link_invitation(a, YEAR)
    assert db.accept_hicbc_link_invitation(b, token, YEAR) is not None


def test_active_link_refusal_invariant_under_inputs_consent_withdrawal_relink(env, monkeypatch):
    _, client, owner, other = env
    link(owner, other)
    monkeypatch.setattr(db, "get_profile_by_user", lambda *a: pytest.fail("partner/profile read"))
    monkeypatch.setattr(route, "get_profile_by_user", lambda *a: pytest.fail("partner/profile read"))
    monkeypatch.setattr(route, "_linked_partner_evidence", lambda *a: pytest.fail("linked operand read"))
    real_source = route.own_ani_from_manual_annual
    monkeypatch.setattr(route, "own_ani_from_manual_annual", lambda *a: pytest.fail("linked preview calculated"))
    baseline = post(client)
    assert baseline.status_code == 409
    assert baseline.json["projected_user_hicbc"] is None
    for income in ("0", "60000", "80000", "99999999"):
        assert post(client, facts(employment_income=income)).json == baseline.json
    for user in (owner, other):
        assert db.record_hicbc_link_consent(user, YEAR, db.HICBC_NOTICE_VERSION)
    assert post(client).json == baseline.json
    assert db.revoke_hicbc_link(other, YEAR)
    monkeypatch.setattr(route, "own_ani_from_manual_annual", real_source)
    assert post(client).status_code == 200
    link(owner, other)
    assert post(client).status_code == 409  # no old permission revived, still no probing


def test_preview_read_serialises_against_relink(env):
    _, _, owner, other = env
    started, finished = threading.Event(), threading.Event()
    def relink():
        started.set()
        link(owner, other)
        finished.set()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with db.hicbc_manual_preview_read(owner, YEAR) as (_, linked):
            assert not linked
            future = pool.submit(relink)
            assert started.wait(1)
            assert not finished.wait(.1)
        future.result(timeout=5)
    with db.hicbc_manual_preview_read(owner, YEAR) as (_, linked):
        assert linked


@pytest.mark.parametrize("initial_link", [False, True])
def test_real_request_linearises_before_concurrent_link_change(env, monkeypatch, initial_link):
    _, client, owner, other = env
    if initial_link:
        link(owner, other)
    entered, release, changing, changed = (threading.Event() for _ in range(4))
    real_read = route.hicbc_manual_preview_read
    @contextmanager
    def paused_read(*args):
        with real_read(*args) as snapshot:
            entered.set()
            assert release.wait(3)
            yield snapshot
    def change():
        changing.set()
        if initial_link:
            assert db.revoke_hicbc_link(other, YEAR)
        else:
            link(owner, other)
        changed.set()
    monkeypatch.setattr(route, "hicbc_manual_preview_read", paused_read)
    with ThreadPoolExecutor(max_workers=2) as pool:
        request_future = pool.submit(post, client)
        assert entered.wait(2)
        change_future = pool.submit(change)
        assert changing.wait(1)
        try:
            assert not changed.wait(.1)
        finally:
            release.set()
        assert request_future.result(timeout=5).status_code == (409 if initial_link else 200)
        change_future.result(timeout=5)
    assert post(client).status_code == (200 if initial_link else 409)


def test_duplicate_fields_query_and_oversize_fail_closed(env):
    client = env[1]
    token = client.get("/test-csrf").get_data(as_text=True)
    raw = json.dumps(facts())[:-1] + ', "employment_income":"0"}'
    assert client.post(URL, data=raw, content_type="application/json", headers={"X-CSRFToken": token}).status_code == 400
    assert post(client, query_string={"user_id": "1"}).status_code == 400
    assert post(client, facts(employment_income="0" * 9000)).status_code == 400
    deep = "[" * 1500 + "0" + "]" * 1500
    assert client.post(URL, data=deep, content_type="application/json", headers={"X-CSRFToken": token}).status_code == 400


def test_invalid_owner_and_configured_year_are_not_used(env, monkeypatch):
    client = env[1]
    monkeypatch.setattr(route, "configured_tax_year", lambda: "2025/26")
    assert post(client).status_code == 400
    monkeypatch.setattr(route, "configured_tax_year", lambda: YEAR)
    with client.session_transaction() as session:
        session[_SK_USER_ID] = 999999
    assert post(client).status_code == 400
