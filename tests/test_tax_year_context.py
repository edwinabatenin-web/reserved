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
    configured_tax_year,
    is_supported_tax_year,
    resolve_tax_year,
)

ROOT = Path(__file__).resolve().parents[1]


# ── Resolver ──────────────────────────────────────────────────────────────────

def test_resolve_prefers_result_tax_year():
    assert resolve_tax_year(result_tax_year="2026/27", context_tax_year="2025/26") == "2026/27"


def test_resolve_falls_back_to_context_tax_year():
    assert resolve_tax_year(result_tax_year=None, context_tax_year="2026/27") == "2026/27"
    assert resolve_tax_year(result_tax_year="bogus", context_tax_year="2026/27") == "2026/27"


def test_resolve_returns_none_when_unsupported():
    assert resolve_tax_year(result_tax_year="1999/00", context_tax_year="nonsense") is None


def test_resolve_never_infers_from_today():
    assert resolve_tax_year() is None


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


def test_public_settings_renders_configured_tax_year(client):
    rv = client.get("/settings")
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
