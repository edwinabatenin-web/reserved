"""Feature-gate and household-change tests for the HICBC October v1 package.

Covers: the explicit, strictly-parsed feature gate (absent/empty/malformed/false
=> disabled; never inferred from other flags); the 404 behaviour when disabled;
and the server-derived, one-shot household-change notification that cannot be
fabricated by a stale query parameter.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import reserved.database as db
from reserved import create_app
from reserved.auth import _SK_USER_ID
from reserved.engines.hicbc_partner import household_change_status

ROOT = Path(__file__).resolve().parents[1]


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    test_file = tmp_path / "activation.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    db.init_db()
    return test_file


def _make_app(tmp_path, monkeypatch, hicbc_env=None, extra_env=None):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "activation_app.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    if hicbc_env is None:
        monkeypatch.delenv("HICBC_ENABLED", raising=False)
    else:
        monkeypatch.setenv("HICBC_ENABLED", hicbc_env)
    for key, value in (extra_env or {}).items():
        monkeypatch.setenv(key, value)
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    return app


def _routes(app):
    return {str(r) for r in app.url_map.iter_rules()}


def _has_hicbc(app):
    return any("hicbc" in r for r in _routes(app))


# ── Feature gate ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw", [None, "", "0", "false", "no", "off", "banana"])
def test_gate_disabled_for_absent_empty_false_or_malformed(tmp_path, monkeypatch, raw):
    app = _make_app(tmp_path, monkeypatch, hicbc_env=raw)
    assert not _has_hicbc(app)


@pytest.mark.parametrize("raw", ["1", "true", "TRUE", "yes", "on", "enabled", " true "])
def test_gate_enabled_for_explicit_true(tmp_path, monkeypatch, raw):
    app = _make_app(tmp_path, monkeypatch, hicbc_env=raw)
    assert _has_hicbc(app)


def test_gate_not_inferred_from_other_flags(tmp_path, monkeypatch):
    # Demo mode, production environment and a live Clerk key must never enable HICBC.
    app = _make_app(
        tmp_path,
        monkeypatch,
        hicbc_env=None,
        extra_env={
            "RESERVED_DEMO_MODE": "1",
            "FLASK_ENV": "production",
            "CLERK_PUBLISHABLE_KEY": "pk_live_dummy",
            "SESSION_SECRET": "test-secret-not-for-production",
        },
    )
    assert not _has_hicbc(app)


def test_disabled_routes_return_404(tmp_path, monkeypatch):
    app = _make_app(tmp_path, monkeypatch, hicbc_env=None)
    client = app.test_client()
    assert client.get("/v2/hicbc/").status_code == 404
    assert client.get("/v2/hicbc/link").status_code == 404
    assert client.post("/v2/hicbc/estimate", data={}).status_code == 404


# ── Household change ──────────────────────────────────────────────────────────

def _login_and_profile(client, income=70000):
    client.get("/v2/demo-login")
    with client.session_transaction() as sess:
        uid = sess[_SK_USER_ID]
    db.save_profile_by_user(uid, {
        "income_estimate": float(income),
        "pension_contribution": 0.0,
        "display_name": "Test User",
    })
    return uid


def _estimate_form(**overrides):
    form = {
        "receives_child_benefit": "1",
        "child_benefit_children": "1",
        "has_relevant_partner": "1",
        "representation": "point",
        "partner_ani_point": "50000",
    }
    form.update(overrides)
    return form


def test_household_change_notification_is_server_derived_and_one_shot(tmp_path, monkeypatch):
    app = _make_app(tmp_path, monkeypatch, hicbc_env="1")
    client = app.test_client()
    _login_and_profile(client, income=70000)

    # No change yet: page must not show the change message.
    resp = client.get("/v2/hicbc/")
    assert b"household tax position has changed" not in resp.data.lower()

    # From "partner below" to "partner above" — a real household responsibility change.
    client.post("/v2/hicbc/estimate", data=_estimate_form(partner_ani_point="50000"))
    client.post("/v2/hicbc/estimate", data=_estimate_form(partner_ani_point="90000"))

    resp = client.get("/v2/hicbc/")
    assert b"household tax position has changed" in resp.data.lower()

    # One-shot: the transition is popped on read and must not reappear.
    resp = client.get("/v2/hicbc/")
    assert b"household tax position has changed" not in resp.data.lower()


def test_stale_previous_status_query_param_does_not_fabricate_change(tmp_path, monkeypatch):
    app = _make_app(tmp_path, monkeypatch, hicbc_env="1")
    client = app.test_client()
    _login_and_profile(client, income=70000)
    resp = client.get("/v2/hicbc/?previous_status=changed")
    assert b"household tax position has changed" not in resp.data.lower()


def test_household_change_status_engine_semantics():
    # The engine-level status vocabulary must remain intact for API/structured use.
    assert household_change_status("no_charge", "person_liable") == "changed"
    assert household_change_status("person_liable", "person_liable") == "unchanged"
