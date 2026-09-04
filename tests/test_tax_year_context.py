"""
Tax-year derivation for customer-facing surfaces.

Customer-facing templates and routes must derive the displayed tax year from
the result contract or the authoritative configured context rather than a
literal, and the result tax year must travel with serialized responses so a
saved scenario cannot silently lose it.
"""
from decimal import Decimal
from pathlib import Path

import pytest

import reserved.database as db
from reserved import create_app
from reserved.auth import _SK_CLERK_ID, _SK_USER_ID
from reserved.engines import tax_config
from reserved.tax_year_context import (
    UnsupportedTaxYear,
    configured_tax_year,
    is_supported_tax_year,
    resolve_tax_year,
)

ROOT = Path(__file__).resolve().parents[1]


# ── Resolver ──────────────────────────────────────────────────────────────────

def test_resolve_uses_valid_result_tax_year():
    assert resolve_tax_year(result_tax_year="2026/27") == "2026/27"
    assert resolve_tax_year(result_tax_year="2026/27", context_tax_year="2026/27") == "2026/27"


def test_resolve_falls_back_to_context_when_result_absent():
    assert resolve_tax_year(result_tax_year=None, context_tax_year="2026/27") == "2026/27"


def test_resolve_returns_none_when_unavailable():
    assert resolve_tax_year() is None
    assert resolve_tax_year(result_tax_year=None, context_tax_year="nonsense") is None


def test_resolve_never_infers_from_today():
    assert resolve_tax_year() is None


def test_resolve_fails_closed_on_malformed_result_year():
    with pytest.raises(UnsupportedTaxYear):
        resolve_tax_year(result_tax_year="bogus", context_tax_year="2026/27")


def test_resolve_fails_closed_on_unsupported_result_year():
    with pytest.raises(UnsupportedTaxYear):
        resolve_tax_year(result_tax_year="1999/00", context_tax_year="2026/27")


def test_resolve_fails_closed_on_whitespace_or_empty():
    with pytest.raises(UnsupportedTaxYear):
        resolve_tax_year(result_tax_year="", context_tax_year="2026/27")
    with pytest.raises(UnsupportedTaxYear):
        resolve_tax_year(result_tax_year="  ", context_tax_year="2026/27")
    with pytest.raises(UnsupportedTaxYear):
        resolve_tax_year(result_tax_year="2026/27 ", context_tax_year="2026/27")


def test_resolve_fails_closed_on_conflicting_years():
    with pytest.raises(UnsupportedTaxYear):
        resolve_tax_year(result_tax_year="2026/27", context_tax_year="2025/26")


def test_is_supported_tax_year():
    assert is_supported_tax_year("2026/27")
    assert not is_supported_tax_year("2026/27 ")  # trailing space is not a supported key
    assert not is_supported_tax_year(None)
    assert not is_supported_tax_year(2026)


def test_configured_tax_year_is_the_authoritative_config():
    assert configured_tax_year() == tax_config.TAX_YEAR
    assert is_supported_tax_year(configured_tax_year())


# ── Position / serialization carry the year ───────────────────────────────────

def test_position_carries_its_tax_year():
    from reserved.engines.optimise import calculate_position

    pos = calculate_position(Decimal("50000"), Decimal("0"))
    assert pos.tax_year == "2026/27"


def test_model_pension_scenario_positions_carry_tax_year():
    from reserved.engines.optimise import model_pension_scenario

    r = model_pension_scenario(
        Decimal("120000"), Decimal("0"), Decimal("10000"), "PA_TAPER"
    )
    assert r.before.tax_year == "2026/27"
    assert r.after.tax_year == "2026/27"


# ── Templates no longer hard-code the year ────────────────────────────────────

@pytest.mark.parametrize(
    "rel",
    [
        "reserved/templates/settings.html",
        "reserved/templates/v2/settings.html",
        "reserved/templates/v2/optimise.html",
    ],
)
def test_customer_templates_do_not_hardcode_tax_year(rel):
    text = (ROOT / rel).read_text()
    assert "2026/27" not in text
    assert "{{ tax_year }}" in text


# ── Routes ────────────────────────────────────────────────────────────────────

@pytest.fixture
def app(tmp_path, monkeypatch):
    test_file = tmp_path / "flask_tax_year.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    application = create_app()
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def test_authenticated_v2_settings_renders_configured_tax_year(client):
    with client.session_transaction() as sess:
        sess[_SK_USER_ID] = 1
        sess[_SK_CLERK_ID] = "user_tax_year"
    rv = client.get("/v2/settings")
    assert rv.status_code == 200
    assert f"({configured_tax_year()})".encode() in rv.data


def test_optimise_calculate_response_carries_tax_year(client):
    with client.session_transaction() as sess:
        sess[_SK_USER_ID] = 1
        sess[_SK_CLERK_ID] = "user_test123"
    rv = client.post(
        "/v2/optimise/calculate",
        json={
            "opportunity_id": "PA_TAPER",
            "projected_income": 120000,
            "current_pension": 0,
            "additional_pension": 10000,
        },
    )
    assert rv.status_code == 200
    payload = rv.get_json()
    assert payload["ok"] is True
    assert payload["tax_year"] == configured_tax_year()


# ── F3: Explore scenario save carries and preserves the tax year ──────────────

def _auth_session(client):
    """Create the backing user row and authenticate the test client as it."""
    user_id = db.get_or_create_user("user_test123", email="test@example.com")
    with client.session_transaction() as sess:
        sess[_SK_USER_ID] = user_id
        sess[_SK_CLERK_ID] = "user_test123"
    return user_id


def test_save_scenario_route_requires_tax_year(client):
    _auth_session(client)
    rv = client.post(
        "/v2/optimise/save-scenario",
        json={"opportunity_id": "PA_TAPER", "inputs": {}, "outputs": {}},
    )
    assert rv.status_code == 400
    assert rv.get_json()["ok"] is False


def test_save_scenario_route_rejects_malformed_tax_year(client):
    _auth_session(client)
    rv = client.post(
        "/v2/optimise/save-scenario",
        json={"opportunity_id": "PA_TAPER", "inputs": {}, "outputs": {}, "tax_year": "bogus"},
    )
    assert rv.status_code == 400
    assert rv.get_json()["ok"] is False


def test_save_scenario_route_rejects_conflicting_tax_year(client):
    _auth_session(client)
    rv = client.post(
        "/v2/optimise/save-scenario",
        json={"opportunity_id": "PA_TAPER", "inputs": {}, "outputs": {}, "tax_year": "2025/26"},
    )
    assert rv.status_code == 400
    assert rv.get_json()["ok"] is False


def test_save_scenario_route_persists_tax_year(client):
    user_id = _auth_session(client)
    rv = client.post(
        "/v2/optimise/save-scenario",
        json={
            "opportunity_id": "PA_TAPER",
            "inputs": {"additional_pension": 10000},
            "outputs": {"total_benefit": "100.00"},
            "tax_year": configured_tax_year(),
        },
    )
    assert rv.status_code == 200
    assert rv.get_json()["ok"] is True
    saved = db.list_optimise_scenarios(user_id)
    assert saved and saved[0]["tax_year"] == configured_tax_year()


def test_saved_scenario_year_is_not_relabelled_by_configured_year_change(client, monkeypatch):
    user_id = _auth_session(client)
    db.save_optimise_scenario(
        user_id, "PA_TAPER", {}, {"total_benefit": "1"}, tax_year="2026/27"
    )
    monkeypatch.setattr(tax_config, "TAX_YEAR", "2025/26")
    saved = db.list_optimise_scenarios(user_id)
    assert saved[0]["tax_year"] == "2026/27"


def test_legacy_record_without_year_surfaces_as_none(client):
    import json
    user_id = _auth_session(client)
    with db._connection() as conn:
        conn.execute(
            """INSERT INTO optimise_scenarios
               (user_id, opportunity, label, tax_year, inputs_json, outputs_json, saved_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, "PA_TAPER", None, None, json.dumps({}), json.dumps({}), "2026-01-01T00:00:00Z"),
        )
    saved = db.list_optimise_scenarios(user_id)
    assert saved[0]["tax_year"] is None
