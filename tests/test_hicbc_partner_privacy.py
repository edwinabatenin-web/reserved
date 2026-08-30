"""Persistence, web and privacy tests for the HICBC partner-estimate path.

Covers owner isolation, Decimal-string round-trip, unauthenticated access,
CSRF protection, server-side validation, and the privacy boundary that the
partner's raw ANI/range operands never appear in customer JSON payloads or the
rendered result section.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

import reserved.database as db
from reserved import create_app
from reserved.auth import _SK_USER_ID

ROOT = Path(__file__).resolve().parents[1]


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def test_db(tmp_path, monkeypatch):
    test_file = tmp_path / "hicbc.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    db.init_db()
    return test_file


@pytest.fixture
def app(tmp_path, monkeypatch):
    test_file = tmp_path / "hicbc_app.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("HICBC_ENABLED", "1")
    application = create_app()
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client, income=70000):
    client.get("/v2/demo-login")
    with client.session_transaction() as sess:
        uid = sess[_SK_USER_ID]
    db.save_profile_by_user(uid, {
        "income_estimate": float(income),
        "pension_contribution": 0.0,
        "display_name": "Test User",
        "tax_year": "2026/27",
    })
    return uid


def _estimate_form(**overrides):
    data = {
        "child_benefit_claimant": "person",
        "child_benefit_children": "1",
        "child_benefit_weeks_entitled": "52",
        "has_relevant_partner": "yes",
        "relationship_covers_full_year": "yes",
        "representation": "point",
        "partner_ani_point": "55000",
    }
    data.update(overrides)
    return data


# ── Persistence ───────────────────────────────────────────────────────────────

def _users(test_db):
    return (
        db.get_or_create_user("clerk_a", email="a@example.com"),
        db.get_or_create_user("clerk_b", email="b@example.com"),
    )


def test_hicbc_estimate_roundtrip_preserves_decimal_string(test_db):
    uid, _ = _users(test_db)
    db.save_hicbc_estimate(uid, {
        "tax_year": "2026/27",
        "receives_child_benefit": 1,
        "child_benefit_children": 1,
        "child_benefit_annual": "1406.60",
        "has_relevant_partner": 1,
        "representation": "point",
        "partner_ani_point": "79000.01",
        "partner_ani_low": None,
        "partner_ani_high": None,
    })
    row = db.get_hicbc_estimate(uid, "2026/27")
    assert row is not None
    assert row["partner_ani_point"] == "79000.01"  # exact string, no float loss
    assert row["child_benefit_annual"] == "1406.60"
    assert row["has_relevant_partner"] == 1


def test_hicbc_estimate_roundtrip_preserves_claimant_and_period_facts(test_db):
    uid, _ = _users(test_db)
    db.save_hicbc_estimate(uid, {
        "tax_year": "2026/27",
        "child_benefit_claimant": "partner",
        "child_benefit_children": 2,
        "child_benefit_weeks_entitled": 40,
        "has_relevant_partner": 1,
        "relationship_covers_full_year": 0,
        "representation": "range",
        "partner_ani_low": "50000",
        "partner_ani_high": "60000",
    })
    row = db.get_hicbc_estimate(uid, "2026/27")
    assert row is not None
    # Claimant identity, entitlement weeks and relationship-period facts survive
    # the persistence round trip without being relabelled to defaults.
    assert row["child_benefit_claimant"] == "partner"
    assert row["child_benefit_weeks_entitled"] == 40
    assert row["relationship_covers_full_year"] == 0
    assert row["partner_status_period_semantics"] == "status_answer_full_year"


def test_v9_migration_leaves_new_facts_unknown(test_db):
    # A pre-v9 row carries only the legacy columns.  The v9 columns must be NULL
    # (unknown) after migration — never silently defaulted to the user, 52 weeks
    # or a full-year relationship.
    uid, _ = _users(test_db)
    with db._connection() as conn:
        conn.execute(
            """
            INSERT INTO hicbc_estimates
                (user_id, tax_year, receives_child_benefit, child_benefit_children,
                 child_benefit_annual, has_relevant_partner, representation,
                 partner_ani_point, partner_ani_low, partner_ani_high,
                 evidence_id, source_kind, observed_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (uid, "2026/27", 1, 1, None, 1, "point", "79000", None, None,
             "legacy-evidence", "user_supplied_partner_estimate",
             "2026-08-10T00:00:00+00:00", "2026-08-10T00:00:00+00:00",
             "2026-08-10T00:00:00+00:00"),
        )
    row = db.get_hicbc_estimate(uid, "2026/27")
    assert row is not None
    # The new columns are not populated by the pre-v9 record.
    assert row["child_benefit_claimant"] is None
    assert row["child_benefit_weeks_entitled"] is None
    assert row["relationship_covers_full_year"] is None


def test_v9_migration_statements_add_columns_without_default():
    # Each v9 migration statement must be a plain ADD COLUMN (no DEFAULT), so
    # existing rows keep NULL and are never silently assigned a claimant, weeks
    # or full-year assumption.
    for sql in db._MIGRATIONS[9]:
        upper = sql.strip().upper()
        assert upper.startswith("ALTER TABLE HICBC_ESTIMATES ADD COLUMN")
        assert "DEFAULT" not in upper


def test_v10_migration_leaves_legacy_period_semantics_unknown():
    sql = db._MIGRATIONS[10]
    assert len(sql) == 1
    assert "PARTNER_STATUS_PERIOD_SEMANTICS" in sql[0].upper()
    assert "DEFAULT" not in sql[0].upper()


def test_hicbc_estimate_owner_isolation(test_db):
    uid_a, uid_b = _users(test_db)
    db.save_hicbc_estimate(uid_a, {"tax_year": "2026/27", "partner_ani_point": "79000"})
    assert db.get_hicbc_estimate(uid_a, "2026/27") is not None
    assert db.get_hicbc_estimate(uid_b, "2026/27") is None


def test_hicbc_estimate_upsert_preserves_evidence_id(test_db):
    uid, _ = _users(test_db)
    db.save_hicbc_estimate(uid, {"tax_year": "2026/27", "partner_ani_point": "55000"})
    first = db.get_hicbc_estimate(uid, "2026/27")
    db.save_hicbc_estimate(uid, {"tax_year": "2026/27", "partner_ani_point": "79000"})
    second = db.get_hicbc_estimate(uid, "2026/27")
    assert first["evidence_id"] == second["evidence_id"]  # stable identity across updates
    assert second["partner_ani_point"] == "79000"  # replaced value


def test_hicbc_estimate_delete(test_db):
    uid, _ = _users(test_db)
    db.save_hicbc_estimate(uid, {"tax_year": "2026/27", "partner_ani_point": "79000"})
    assert db.delete_hicbc_estimate(uid, "2026/27") is True
    assert db.get_hicbc_estimate(uid, "2026/27") is None
    assert db.delete_hicbc_estimate(uid, "2026/27") is False


def test_hicbc_estimate_delete_is_owner_scoped(test_db):
    uid_a, uid_b = _users(test_db)
    db.save_hicbc_estimate(uid_a, {"tax_year": "2026/27", "partner_ani_point": "79000"})
    assert db.delete_hicbc_estimate(uid_b, "2026/27") is False
    assert db.get_hicbc_estimate(uid_a, "2026/27") is not None


# ── Web: access control and validation ────────────────────────────────────────

def test_unauthenticated_hicbc_redirects(client):
    resp = client.get("/v2/hicbc/")
    assert resp.status_code == 302
    assert resp.location.endswith("/v2/demo-login")


def test_hicbc_result_json_is_owner_scoped(client):
    _login(client, income=70000)
    client.post("/v2/hicbc/estimate", data=_estimate_form(partner_ani_point="55000"))

    # A second user sees an empty (insufficient-facts) result, not user A's data.
    client2 = client.application.test_client()
    client2.get("/v2/demo-login")
    resp = client2.get("/v2/hicbc/result")
    data = resp.get_json()
    assert data["responsibility_status"] == "insufficient_facts"
    assert data["based_on_partner_estimate"] is False


def test_hicbc_save_rejects_negative_children(client):
    _login(client)
    resp = client.post("/v2/hicbc/estimate", data=_estimate_form(child_benefit_children="-2"))
    assert resp.status_code == 400
    assert b"whole number" in resp.data


def test_hicbc_save_rejects_low_above_high(client):
    _login(client)
    resp = client.post("/v2/hicbc/estimate", data=_estimate_form(
        representation="range", partner_ani_low="80000", partner_ani_high="50000",
    ))
    assert resp.status_code == 400
    assert b"must not exceed" in resp.data


def test_hicbc_save_rejects_non_numeric_partner_ani(client):
    _login(client)
    resp = client.post("/v2/hicbc/estimate", data=_estimate_form(partner_ani_point="abc"))
    assert resp.status_code == 400


def test_hicbc_form_explains_that_period_qualifies_partner_answer(client):
    _login(client)
    body = client.get("/v2/hicbc/").get_data(as_text=True)
    assert "Was your answer about having a partner true for the whole 2026/27 tax year?" in body
    assert "Yes, for the whole tax year" in body
    assert "No, it changed during the tax year" in body
    assert "Does the relationship cover" not in body


def test_hicbc_save_rejects_malformed_partner_period(client):
    uid = _login(client)
    resp = client.post(
        "/v2/hicbc/estimate",
        data=_estimate_form(relationship_covers_full_year="whole-ish"),
    )
    assert resp.status_code == 400
    assert db.get_hicbc_estimate(uid, "2026/27") is None


@pytest.mark.parametrize(
    ("partner_answer", "period_answer", "expected_status", "expected_charge"),
    [
        ("no", "yes", "person_liable", "703.00"),
        ("yes", "yes", "person_liable", "703.00"),
        ("no", "no", "insufficient_facts", None),
        ("yes", "no", "person_liable", None),
        ("no", "", "insufficient_facts", None),
        ("yes", "", "person_liable", None),
        ("", "yes", "insufficient_facts", None),
        ("", "no", "insufficient_facts", None),
    ],
)
def test_post_persistence_result_chain_preserves_partner_status_period_semantics(
    client, partner_answer, period_answer, expected_status, expected_charge
):
    uid = _login(client, income=70000)
    form = _estimate_form(
        has_relevant_partner=partner_answer,
        relationship_covers_full_year=period_answer,
    )
    if partner_answer != "yes":
        form.update(representation="", partner_ani_point="")

    posted = client.post("/v2/hicbc/estimate", data=form)
    assert posted.status_code == 302

    row = db.get_hicbc_estimate(uid, "2026/27")
    assert row["has_relevant_partner"] == ({"yes": 1, "no": 0}.get(partner_answer))
    assert row["relationship_covers_full_year"] == ({"yes": 1, "no": 0}.get(period_answer))
    assert row["partner_status_period_semantics"] == "status_answer_full_year"

    result = client.get("/v2/hicbc/result").get_json()
    assert result["responsibility_status"] == expected_status
    assert result["projected_user_hicbc"] == expected_charge


def test_hicbc_csrf_protection(tmp_path, monkeypatch):
    test_file = tmp_path / "hicbc_csrf.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("HICBC_ENABLED", "1")
    application = create_app()
    application.config["TESTING"] = True
    # CSRF left enabled — a state-changing POST without a token must be rejected.
    c = application.test_client()
    c.get("/v2/demo-login")
    resp = c.post("/v2/hicbc/estimate", data=_estimate_form())
    assert resp.status_code == 400


# ── Privacy: raw partner values never leak into customer payloads ─────────────

def test_result_json_excludes_raw_partner_value(client):
    _login(client, income=70000)
    client.post("/v2/hicbc/estimate", data=_estimate_form(partner_ani_point="79000"))
    resp = client.get("/v2/hicbc/result")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "79000" not in body
    assert "partner_evidence" not in body
    assert "original_value" not in body


def test_result_json_has_no_income_band_or_relative_salary(client):
    _login(client, income=70000)
    client.post("/v2/hicbc/estimate", data=_estimate_form(partner_ani_point="90000"))
    body = client.get("/v2/hicbc/result").get_data(as_text=True).lower()
    assert "earns more" not in body
    assert "relative salary" not in body
    assert "income band" not in body


def test_rendered_result_section_uses_only_the_customer_view():
    # The result section must render the privacy-minimised ``view``, never the raw
    # persisted partner values; the raw values may only appear as the user's own
    # form inputs (edit echo).
    template = (ROOT / "reserved" / "templates" / "v2" / "hicbc.html").read_text(encoding="utf-8")
    result_section = template.split('<section class="panel" aria-live="polite">', 1)[1].split("</section>", 1)[0]
    for field in ("view.headline", "view.projected_user_hicbc", "view.possible_charge_low", "view.messages"):
        assert field in result_section
    for forbidden in ("partner_ani_point", "partner_ani_low", "partner_ani_high", "partner_evidence", "original_value"):
        assert forbidden not in result_section


def test_web_module_does_not_log_raw_partner_values():
    source = (ROOT / "reserved" / "web" / "hicbc.py").read_text(encoding="utf-8")
    for line in source.splitlines():
        if "log." in line:
            assert "partner" not in line and "request.form" not in line
