"""HICBC linked-account consent, cross-account authorisation and retention tests.

Covers the HICBC-only mutual-consent link lifecycle (invite → accept → revoke →
re-link), single-use/high-entropy token handling, duplicate-link and self-link
rejection, owner-scoped access, privacy (no partner ANI is stored in link rows
or returned to the other party), manual-vs-linked conflict resolution (neither
source has precedence), and the repository deletion hooks.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3

import pytest

import reserved.database as db
from reserved import create_app
from reserved.auth import _SK_USER_ID
from reserved.web.hicbc import build_responsibility

ROOT = Path(__file__).resolve().parents[1]

TAX_YEAR = "2026/27"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    test_file = tmp_path / "linked.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    db.init_db()
    return test_file


@pytest.fixture
def app(tmp_path, monkeypatch):
    test_file = tmp_path / "linked_app.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("HICBC_ENABLED", "1")
    application = create_app()
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False
    return application


def _user(clerk_id: str, income: float) -> int:
    uid = db.get_or_create_user(clerk_id, email=f"{clerk_id}@x", display_name=clerk_id)
    db.save_profile_by_user(uid, {
        "income_estimate": income,
        "pension_contribution": 0.0,
        "display_name": clerk_id,
        "tax_year": TAX_YEAR,
    })
    return uid


def _mutual_consent(a: int, b: int, tax_year: str = TAX_YEAR) -> None:
    """Record separate, versioned mutual permission for both participants."""
    assert db.record_hicbc_link_consent(a, tax_year, db.HICBC_NOTICE_VERSION) is True
    assert db.record_hicbc_link_consent(b, tax_year, db.HICBC_NOTICE_VERSION) is True


def _as_user(client, user_id: int) -> None:
    with client.session_transaction() as sess:
        sess[_SK_USER_ID] = user_id


def _permission_events(link_id: int) -> list[dict]:
    with db._connection() as conn:
        rows = conn.execute(
            """
            SELECT link_id, permission_cycle, event_type, actor_user_id,
                   occurred_at, notice_version
            FROM hicbc_permission_events
            WHERE link_id = ?
            ORDER BY id
            """,
            (link_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def _permission_binding(client) -> str:
    body = client.get("/v2/hicbc/link").get_data(as_text=True)
    marker = 'name="permission_binding" value="'
    assert marker in body
    return body.split(marker, 1)[1].split('"', 1)[0]


# ── Link lifecycle ────────────────────────────────────────────────────────────

def test_link_lifecycle_invite_accept_revoke_relink(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)

    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    assert len(token) >= 40  # high entropy

    # Self-link rejected.
    assert db.accept_hicbc_link_invitation(a, token, TAX_YEAR) is None

    # Accept establishes a mutual link.
    link = db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    assert link is not None and link["status"] == "active"
    assert db.get_hicbc_link_partner_id(a, TAX_YEAR) == b
    assert db.get_hicbc_link_partner_id(b, TAX_YEAR) == a

    # Token is single-use.
    assert db.accept_hicbc_link_invitation(b, token, TAX_YEAR) is None

    # Duplicate active link is rejected.
    token2 = db.create_hicbc_link_invitation(a, TAX_YEAR)
    assert db.accept_hicbc_link_invitation(b, token2, TAX_YEAR) is None

    # Either party may revoke.
    assert db.revoke_hicbc_link(b, TAX_YEAR) is True
    assert db.get_hicbc_link_partner_id(a, TAX_YEAR) is None
    assert db.get_hicbc_link_partner_id(b, TAX_YEAR) is None

    # Re-link after revoke re-activates (no duplicate row).
    token3 = db.create_hicbc_link_invitation(b, TAX_YEAR)
    link3 = db.accept_hicbc_link_invitation(a, token3, TAX_YEAR)
    assert link3 is not None and link3["status"] == "active"
    assert db.get_hicbc_link_partner_id(a, TAX_YEAR) == b


def test_schema_v10_upgrade_adds_permission_cycle_and_event_history(tmp_path, monkeypatch):
    legacy_file = tmp_path / "linked_v10.db"
    with sqlite3.connect(legacy_file) as conn:
        conn.executescript(
            """
            CREATE TABLE schema_version (version INTEGER NOT NULL);
            INSERT INTO schema_version (version) VALUES (10);
            CREATE TABLE hicbc_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_low_id INTEGER NOT NULL,
                user_high_id INTEGER NOT NULL,
                tax_year TEXT NOT NULL,
                purpose TEXT NOT NULL DEFAULT 'hicbc_responsibility',
                status TEXT NOT NULL,
                initiator_id INTEGER NOT NULL,
                relationship_started_at TEXT,
                created_at TEXT NOT NULL,
                accepted_at TEXT NOT NULL,
                revoked_at TEXT,
                revoked_by INTEGER,
                UNIQUE(user_low_id, user_high_id, tax_year)
            );
            CREATE TABLE hicbc_link_consents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link_id INTEGER NOT NULL REFERENCES hicbc_links(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL,
                notice_version TEXT NOT NULL,
                consented_at TEXT NOT NULL,
                withdrawn_at TEXT,
                UNIQUE(link_id, user_id)
            );
            """
        )
    monkeypatch.setattr(db, "_DB_FILE", legacy_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)

    db.init_db()

    with db._connection() as conn:
        link_columns = {
            row["name"]: dict(row)
            for row in conn.execute("PRAGMA table_info(hicbc_links)")
        }
        event_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(hicbc_permission_events)")
        }
        binding_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(hicbc_permission_form_bindings)")
        }
        version = conn.execute("SELECT version FROM schema_version").fetchone()[0]
    assert link_columns["permission_cycle"]["dflt_value"] == "1"
    assert {
        "link_id", "permission_cycle", "event_type", "actor_user_id",
        "occurred_at", "notice_version",
    } <= event_columns
    assert {
        "token_hash", "link_id", "permission_cycle", "user_id", "tax_year",
        "notice_version", "created_at", "expires_at",
    } <= binding_columns
    assert version == db._SCHEMA_VERSION == 12


def test_expired_invitation_rejected(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR, expires_in_minutes=-1)
    assert db.accept_hicbc_link_invitation(b, token, TAX_YEAR) is None


def test_invalid_token_rejected(tmp_db):
    a = _user("clerk_a", 70000)
    assert db.accept_hicbc_link_invitation(a, "not-a-real-token", TAX_YEAR) is None


def test_token_is_stored_hashed_not_raw(tmp_db):
    a = _user("clerk_a", 70000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    with db._connection() as conn:
        rows = conn.execute("SELECT token_hash FROM hicbc_link_invitations").fetchall()
    assert rows
    assert token not in {r["token_hash"] for r in rows}
    assert all(len(r["token_hash"]) == 64 for r in rows)  # sha256 hex


# ── Cross-account authorisation ───────────────────────────────────────────────

def test_third_user_cannot_resolve_another_pairs_link(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    c = _user("clerk_c", 60000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    db.accept_hicbc_link_invitation(b, token, TAX_YEAR)

    assert db.get_hicbc_link_partner_id(c, TAX_YEAR) is None
    assert db.get_active_hicbc_link(c, TAX_YEAR) is None
    assert db.revoke_hicbc_link(c, TAX_YEAR) is False  # c is not a participant


def test_link_tables_store_no_partner_financial_value(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    db.accept_hicbc_link_invitation(b, token, TAX_YEAR)

    with db._connection() as conn:
        link_cols = {r["name"] for r in conn.execute("PRAGMA table_info(hicbc_links)")}
        inv_cols = {r["name"] for r in conn.execute("PRAGMA table_info(hicbc_link_invitations)")}
        consent_cols = {r["name"] for r in conn.execute("PRAGMA table_info(hicbc_link_consents)")}
        event_cols = {r["name"] for r in conn.execute("PRAGMA table_info(hicbc_permission_events)")}
        binding_cols = {r["name"] for r in conn.execute("PRAGMA table_info(hicbc_permission_form_bindings)")}
    for cols in (link_cols, inv_cols, consent_cols, event_cols, binding_cols):
        assert "ani" not in " ".join(cols).lower()
        assert "income" not in " ".join(cols).lower()
        assert "monetary" not in " ".join(cols).lower()


# ── Privacy + manual/linked conflict resolution ──────────────────────────────

def test_linked_partner_raw_ani_never_in_customer_payload(app):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    _mutual_consent(a, b)

    client = app.test_client()
    client.get("/v2/demo-login")
    with client.session_transaction() as sess:
        sess[_SK_USER_ID] = a

    resp = client.get("/v2/hicbc/result")
    body = resp.get_data(as_text=True)
    assert "90000" not in body  # B's raw ANI must never surface to A


def test_manual_and_linked_conflict_yields_range_not_silent_selection(app):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    _mutual_consent(a, b)

    # Manual estimate says partner ~50k; linked evidence says partner ~90k.
    db.save_hicbc_estimate(a, {
        "tax_year": TAX_YEAR,
        "receives_child_benefit": 1,
        "child_benefit_children": 1, "child_benefit_weeks_entitled": 52,
        "has_relevant_partner": 1,
        "representation": "point",
        "partner_ani_point": "50000",
    })

    built = build_responsibility(a, TAX_YEAR)
    result = built["result"]
    assert result.has_relevant_partner is True
    # Neither source silently wins: the effective evidence is a merged range.
    assert result.partner_evidence.is_range is True
    assert result.partner_evidence.low == 50000
    assert result.partner_evidence.high == 90000
    # Responsibility straddles the user ANI (70k), so it degrades to ambiguous.
    assert result.responsibility_status == "ambiguous"
    # Both provenance records are preserved.
    kinds = {e.source_kind for e in result.evidence}
    assert "user_supplied_partner_estimate" in kinds
    assert "linked_partner_source" in kinds


def test_linked_only_evidence_is_used_when_no_manual_estimate(app):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    _mutual_consent(a, b)

    # No manual estimate, but Child Benefit facts are still required; set them
    # via a manual row that does not declare a partner.
    db.save_hicbc_estimate(a, {
        "tax_year": TAX_YEAR,
        "receives_child_benefit": 1,
        "child_benefit_children": 1, "child_benefit_weeks_entitled": 52,
    })

    built = build_responsibility(a, TAX_YEAR)
    result = built["result"]
    assert result.has_relevant_partner is True  # link affirms the partner
    assert result.partner_evidence.source_kind == "linked_partner_source"


def test_revoked_link_removes_linked_evidence(app):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    _mutual_consent(a, b)

    db.save_hicbc_estimate(a, {
        "tax_year": TAX_YEAR,
        "receives_child_benefit": 1,
        "child_benefit_children": 1, "child_benefit_weeks_entitled": 52,
        "has_relevant_partner": 1,
        "representation": "point",
        "partner_ani_point": "50000",
    })

    before = build_responsibility(a, TAX_YEAR)["result"]
    assert any(e.source_kind == "linked_partner_source" for e in before.evidence)

    db.revoke_hicbc_link(a, TAX_YEAR)
    after = build_responsibility(a, TAX_YEAR)["result"]
    assert not any(e.source_kind == "linked_partner_source" for e in after.evidence)
    assert after.partner_evidence.source_kind == "user_supplied_partner_estimate"


# ── Retention / deletion hooks ────────────────────────────────────────────────

def test_deletion_hooks_remove_hicbc_rows(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    db.save_hicbc_estimate(a, {"tax_year": TAX_YEAR, "child_benefit_children": 1})

    assert db.delete_all_hicbc_estimates_for_user(a) >= 1
    assert db.get_hicbc_estimate(a, TAX_YEAR) is None

    removed = db.delete_all_hicbc_links_for_user(a)
    assert removed >= 2  # link + invitation(s)
    assert db.get_active_hicbc_link(a, TAX_YEAR) is None
    assert db.get_active_hicbc_link(b, TAX_YEAR) is None


# ── Versioned mutual permission journey ───────────────────────────────────────

def test_invitation_acceptance_never_implies_permission(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    link = db.accept_hicbc_link_invitation(b, token, TAX_YEAR)

    assert link is not None
    assert db.get_hicbc_link_permission_status(a, TAX_YEAR) == {
        "linked": True,
        "own_permission": False,
        "mutual_permission": False,
    }
    assert db.has_mutual_hicbc_link_consent(a, TAX_YEAR) is False
    assert _permission_events(link["id"]) == []


def test_separate_one_sided_then_two_sided_permission(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    link = db.accept_hicbc_link_invitation(b, token, TAX_YEAR)

    assert db.record_hicbc_link_consent(a, TAX_YEAR, db.HICBC_NOTICE_VERSION)
    assert not db.has_mutual_hicbc_link_consent(a, TAX_YEAR)
    assert db.get_hicbc_link_permission_status(a, TAX_YEAR)["own_permission"]
    assert not db.get_hicbc_link_permission_status(b, TAX_YEAR)["own_permission"]

    assert db.record_hicbc_link_consent(b, TAX_YEAR, db.HICBC_NOTICE_VERSION)
    assert db.has_mutual_hicbc_link_consent(a, TAX_YEAR)
    assert db.has_mutual_hicbc_link_consent(b, TAX_YEAR)
    assert [event["event_type"] for event in _permission_events(link["id"])] == [
        "consent",
        "consent",
    ]


@pytest.mark.parametrize("version", [None, "", "hicbc-notice-v0", "hicbc-notice-v2", 1, True])
def test_unrecognised_or_non_exact_notice_version_fails_closed(tmp_db, version):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    link = db.accept_hicbc_link_invitation(b, token, TAX_YEAR)

    assert db.record_hicbc_link_consent(a, TAX_YEAR, version) is False
    assert _permission_events(link["id"]) == []


def test_permission_page_shows_exact_four_disclosures_and_unchecked_control(app):
    a = _user("clerk_a", 70000)
    b = _user("clerk_partner_private", 98765)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    db.accept_hicbc_link_invitation(b, token, TAX_YEAR)

    client = app.test_client()
    _as_user(client, a)
    response = client.get("/v2/hicbc/link")
    body = response.get_data(as_text=True)

    disclosures = (
        "Reserved will use the limited relevant information available in both linked accounts to calculate each user's own HICBC position.",
        "Neither person will see the other's income or financial details.",
        "Either person may nevertheless see that their own estimate changed after linked information was considered.",
        "Either person may turn off linked HICBC and unlink the accounts.",
    )
    assert response.status_code == 200
    assert all(disclosure in body for disclosure in disclosures)
    checkbox = body.split('name="acknowledgement"', 1)[0].rsplit("<input", 1)[1]
    assert "checked" not in checkbox
    assert "clerk_partner_private" not in body
    assert "98765" not in body
    assert response.headers["Cache-Control"] == "no-store, max-age=0"
    binding = body.split('name="permission_binding" value="', 1)[1].split('"', 1)[0]
    assert len(binding) >= 40
    with db._connection() as conn:
        stored = conn.execute(
            "SELECT token_hash FROM hicbc_permission_form_bindings"
        ).fetchall()
    assert binding not in {row["token_hash"] for row in stored}


def test_permission_view_atomically_binds_only_minimal_displayed_context(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_partner_private", 98765)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    link = db.accept_hicbc_link_invitation(b, token, TAX_YEAR)

    view = db.get_hicbc_link_permission_view(a, TAX_YEAR)

    assert set(view) == {
        "linked", "own_permission", "mutual_permission", "permission_binding",
    }
    assert view["linked"] is True
    assert view["own_permission"] is False
    assert view["mutual_permission"] is False
    assert view["permission_binding"]
    assert b not in view.values()
    with db._connection() as conn:
        binding = conn.execute(
            """
            SELECT link_id, permission_cycle, user_id, tax_year, notice_version
            FROM hicbc_permission_form_bindings WHERE token_hash = ?
            """,
            (db._token_hash(view["permission_binding"]),),
        ).fetchone()
    assert dict(binding) == {
        "link_id": link["id"],
        "permission_cycle": link["permission_cycle"],
        "user_id": a,
        "tax_year": TAX_YEAR,
        "notice_version": db.HICBC_NOTICE_VERSION,
    }


def test_same_link_endpoint_records_each_participants_explicit_permission(app):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    a_client = app.test_client()
    b_client = app.test_client()
    _as_user(a_client, a)
    _as_user(b_client, b)
    a_binding = _permission_binding(a_client)

    missing_ack = a_client.post(
        "/v2/hicbc/link",
        data={"permission_binding": a_binding},
    )
    tampered_binding = a_client.post(
        "/v2/hicbc/link",
        data={"acknowledgement": "yes", "permission_binding": a_binding + "x"},
    )
    assert missing_ack.status_code == tampered_binding.status_code == 302
    assert not db.get_hicbc_link_permission_status(a, TAX_YEAR)["own_permission"]

    first = a_client.post(
        "/v2/hicbc/link",
        data={
            "acknowledgement": "yes",
            "permission_binding": a_binding,
        },
    )
    assert first.status_code == 302
    assert db.get_hicbc_link_permission_status(a, TAX_YEAR) == {
        "linked": True,
        "own_permission": True,
        "mutual_permission": False,
    }

    # Replaying the exact valid token in the same link cycle is idempotent.
    assert a_client.post(
        "/v2/hicbc/link",
        data={"acknowledgement": "yes", "permission_binding": a_binding},
    ).status_code == 302

    b_binding = _permission_binding(b_client)
    second = b_client.post(
        "/v2/hicbc/link",
        data={
            "acknowledgement": "yes",
            "permission_binding": b_binding,
        },
    )
    assert second.status_code == 302
    assert db.has_mutual_hicbc_link_consent(a, TAX_YEAR)
    assert b_client.get("/v2/hicbc/link").headers["Cache-Control"] == "no-store, max-age=0"

    rules = [
        rule for rule in app.url_map.iter_rules()
        if rule.rule == "/v2/hicbc/link" and rule.endpoint == "hicbc.link_page"
    ]
    assert len(rules) == 1
    assert {"GET", "POST"}.issubset(rules[0].methods)


def test_consent_post_requires_auth_and_cannot_probe_another_link(app):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    c = _user("clerk_c", 60000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    link = db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    a_client = app.test_client()
    _as_user(a_client, a)
    stolen_binding = _permission_binding(a_client)

    anonymous = app.test_client()
    assert anonymous.post(
        "/v2/hicbc/link",
        data={"acknowledgement": "yes", "permission_binding": stolen_binding},
    ).status_code == 302

    third_party = app.test_client()
    _as_user(third_party, c)
    response = third_party.post(
        "/v2/hicbc/link",
        data={"acknowledgement": "yes", "permission_binding": stolen_binding},
        follow_redirects=True,
    )
    body = response.get_data(as_text=True).lower()
    assert "could not record" in body
    assert "clerk_a" not in body and "clerk_b" not in body
    assert _permission_events(link["id"]) == []


def test_consent_post_is_csrf_protected(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "linked_csrf.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("HICBC_ENABLED", "1")
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
    client = application.test_client()
    client.get("/v2/demo-login")

    response = client.post(
        "/v2/hicbc/link",
        data={"acknowledgement": "yes", "permission_binding": "opaque-test-token"},
    )
    assert response.status_code == 400


# ── Permission lifecycle, retry and re-link safety ───────────────────────────

def test_permission_retry_is_idempotent_and_preserves_original_timestamp(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    link = db.accept_hicbc_link_invitation(b, token, TAX_YEAR)

    assert db.record_hicbc_link_consent(a, TAX_YEAR, db.HICBC_NOTICE_VERSION)
    with db._connection() as conn:
        before = conn.execute(
            "SELECT consented_at FROM hicbc_link_consents WHERE link_id=? AND user_id=?",
            (link["id"], a),
        ).fetchone()["consented_at"]
    assert db.record_hicbc_link_consent(a, TAX_YEAR, db.HICBC_NOTICE_VERSION)
    with db._connection() as conn:
        after = conn.execute(
            "SELECT consented_at FROM hicbc_link_consents WHERE link_id=? AND user_id=?",
            (link["id"], a),
        ).fetchone()["consented_at"]
    assert after == before
    assert [event["event_type"] for event in _permission_events(link["id"])] == ["consent"]


def test_unlink_atomically_withdraws_current_permission_and_disables_evidence(app):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    link = db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    _mutual_consent(a, b)
    assert build_responsibility(a, TAX_YEAR)["result"].partner_evidence is not None

    assert db.revoke_hicbc_link(a, TAX_YEAR) is True
    assert db.revoke_hicbc_link(a, TAX_YEAR) is False
    assert not db.has_mutual_hicbc_link_consent(a, TAX_YEAR)
    with db._connection() as conn:
        current = conn.execute(
            "SELECT withdrawn_at FROM hicbc_link_consents WHERE link_id=?",
            (link["id"],),
        ).fetchall()
    assert current and all(row["withdrawn_at"] is not None for row in current)
    assert [event["event_type"] for event in _permission_events(link["id"])] == [
        "consent", "consent", "withdraw", "unlink",
    ]
    assert not any(
        evidence.source_kind == "linked_partner_source"
        for evidence in build_responsibility(a, TAX_YEAR)["result"].evidence
    )


def test_relink_never_revives_prior_permission_and_both_users_reconsent(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    link = db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    _mutual_consent(a, b)
    assert db.revoke_hicbc_link(a, TAX_YEAR)

    relink_token = db.create_hicbc_link_invitation(b, TAX_YEAR)
    relink = db.accept_hicbc_link_invitation(a, relink_token, TAX_YEAR)
    assert relink["id"] == link["id"]
    assert relink["permission_cycle"] == 2
    assert not db.has_mutual_hicbc_link_consent(a, TAX_YEAR)
    assert not db.get_hicbc_link_permission_status(a, TAX_YEAR)["own_permission"]
    assert db.record_hicbc_link_consent(a, TAX_YEAR, db.HICBC_NOTICE_VERSION)
    assert not db.has_mutual_hicbc_link_consent(a, TAX_YEAR)
    assert db.record_hicbc_link_consent(b, TAX_YEAR, db.HICBC_NOTICE_VERSION)
    assert db.has_mutual_hicbc_link_consent(a, TAX_YEAR)


def test_stale_cycle_binding_cannot_consent_after_relink(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    stale_binding = db.create_hicbc_link_permission_binding(a, TAX_YEAR)
    assert stale_binding

    assert db.revoke_hicbc_link(b, TAX_YEAR)
    token2 = db.create_hicbc_link_invitation(b, TAX_YEAR)
    active = db.accept_hicbc_link_invitation(a, token2, TAX_YEAR)

    # Preserve a synthetic stale row as if cleanup had been interrupted.  The
    # consent transaction must still reject its old permission cycle.
    with db._connection() as conn:
        conn.execute(
            """
            INSERT INTO hicbc_permission_form_bindings
                (token_hash, link_id, permission_cycle, user_id, tax_year,
                 notice_version, created_at, expires_at)
            VALUES (?, ?, 1, ?, ?, ?, ?, ?)
            """,
            (
                db._token_hash(stale_binding),
                active["id"],
                a,
                TAX_YEAR,
                db.HICBC_NOTICE_VERSION,
                db._now(),
                db._iso_now_plus_minutes(30),
            ),
        )

    assert not db.record_hicbc_link_consent_from_binding(
        a,
        TAX_YEAR,
        db.HICBC_NOTICE_VERSION,
        permission_binding_token=stale_binding,
    )
    current_binding = db.create_hicbc_link_permission_binding(a, TAX_YEAR)
    assert current_binding and current_binding != stale_binding
    assert db.record_hicbc_link_consent_from_binding(
        a,
        TAX_YEAR,
        db.HICBC_NOTICE_VERSION,
        permission_binding_token=current_binding,
    )


def test_web_form_from_prior_cycle_cannot_be_replayed_after_relink(app):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    client = app.test_client()
    _as_user(client, a)
    stale_binding = _permission_binding(client)

    assert db.revoke_hicbc_link(b, TAX_YEAR)
    token2 = db.create_hicbc_link_invitation(b, TAX_YEAR)
    db.accept_hicbc_link_invitation(a, token2, TAX_YEAR)
    response = client.post(
        "/v2/hicbc/link",
        data={"acknowledgement": "yes", "permission_binding": stale_binding},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "could not record" in response.get_data(as_text=True).lower()
    assert not db.get_hicbc_link_permission_status(a, TAX_YEAR)["own_permission"]


def test_binding_is_exact_to_user_tax_year_link_and_token_hash(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    c = _user("clerk_c", 60000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    binding = db.create_hicbc_link_permission_binding(a, TAX_YEAR)
    assert binding

    assert not db.record_hicbc_link_consent_from_binding(
        c,
        TAX_YEAR,
        db.HICBC_NOTICE_VERSION,
        permission_binding_token=binding,
    )
    assert not db.record_hicbc_link_consent_from_binding(
        a,
        "2025/26",
        db.HICBC_NOTICE_VERSION,
        permission_binding_token=binding,
    )
    assert not db.record_hicbc_link_consent_from_binding(
        a,
        TAX_YEAR,
        db.HICBC_NOTICE_VERSION,
        permission_binding_token=binding[:-1] + ("A" if binding[-1] != "A" else "B"),
    )
    assert db.record_hicbc_link_consent_from_binding(
        a,
        TAX_YEAR,
        db.HICBC_NOTICE_VERSION,
        permission_binding_token=binding,
    )


def test_binding_cannot_move_between_two_distinct_links_for_same_user(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    c = _user("clerk_c", 60000)
    other_tax_year = "2027/28"
    first_token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    db.accept_hicbc_link_invitation(b, first_token, TAX_YEAR)
    second_token = db.create_hicbc_link_invitation(a, other_tax_year)
    db.accept_hicbc_link_invitation(c, second_token, other_tax_year)
    first_binding = db.create_hicbc_link_permission_binding(a, TAX_YEAR)
    second_binding = db.create_hicbc_link_permission_binding(a, other_tax_year)

    assert first_binding and second_binding
    assert not db.record_hicbc_link_consent_from_binding(
        a,
        other_tax_year,
        db.HICBC_NOTICE_VERSION,
        permission_binding_token=first_binding,
    )
    assert not db.record_hicbc_link_consent_from_binding(
        a,
        TAX_YEAR,
        db.HICBC_NOTICE_VERSION,
        permission_binding_token=second_binding,
    )
    assert not db.get_hicbc_link_permission_status(a, TAX_YEAR)["own_permission"]
    assert not db.get_hicbc_link_permission_status(a, other_tax_year)["own_permission"]


def test_expired_permission_binding_fails_closed(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    binding = db.create_hicbc_link_permission_binding(a, TAX_YEAR)
    with db._connection() as conn:
        conn.execute(
            "UPDATE hicbc_permission_form_bindings SET expires_at=? WHERE token_hash=?",
            ("2000-01-01T00:00:00+00:00", db._token_hash(binding)),
        )
    assert not db.record_hicbc_link_consent_from_binding(
        a,
        TAX_YEAR,
        db.HICBC_NOTICE_VERSION,
        permission_binding_token=binding,
    )


def test_notice_change_preserves_each_acceptance_event_in_same_cycle(tmp_db, monkeypatch):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    link = db.accept_hicbc_link_invitation(b, token, TAX_YEAR)

    binding_v1 = db.create_hicbc_link_permission_binding(a, TAX_YEAR)
    assert db.record_hicbc_link_consent_from_binding(
        a,
        TAX_YEAR,
        db.HICBC_NOTICE_VERSION,
        permission_binding_token=binding_v1,
    )

    monkeypatch.setattr(db, "HICBC_NOTICE_VERSION", "hicbc-notice-v2")
    # The form issued for v1 cannot be relabelled as v2.
    assert not db.record_hicbc_link_consent_from_binding(
        a,
        TAX_YEAR,
        "hicbc-notice-v2",
        permission_binding_token=binding_v1,
    )
    binding_v2 = db.create_hicbc_link_permission_binding(a, TAX_YEAR)
    assert db.record_hicbc_link_consent_from_binding(
        a,
        TAX_YEAR,
        "hicbc-notice-v2",
        permission_binding_token=binding_v2,
    )
    assert db.revoke_hicbc_link(a, TAX_YEAR)
    events = _permission_events(link["id"])
    assert [(event["event_type"], event["notice_version"]) for event in events] == [
        ("consent", "hicbc-notice-v1"),
        ("consent", "hicbc-notice-v2"),
        ("withdraw", "hicbc-notice-v2"),
        ("unlink", "hicbc-notice-v2"),
    ]


def test_relink_defensively_invalidates_legacy_unwithdrawn_rows(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    link = db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    _mutual_consent(a, b)
    assert db.revoke_hicbc_link(a, TAX_YEAR)
    # Simulate a pre-correction retained row that falsely appears unwithdrawn.
    with db._connection() as conn:
        conn.execute(
            "UPDATE hicbc_link_consents SET withdrawn_at=NULL WHERE link_id=?",
            (link["id"],),
        )

    relink_token = db.create_hicbc_link_invitation(b, TAX_YEAR)
    db.accept_hicbc_link_invitation(a, relink_token, TAX_YEAR)
    assert not db.has_mutual_hicbc_link_consent(a, TAX_YEAR)
    with db._connection() as conn:
        rows = conn.execute(
            "SELECT withdrawn_at FROM hicbc_link_consents WHERE link_id=?",
            (link["id"],),
        ).fetchall()
    assert rows and all(row["withdrawn_at"] is not None for row in rows)


def test_multiple_cycles_retain_bounded_append_only_history(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    link = db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    _mutual_consent(a, b)
    assert db.revoke_hicbc_link(a, TAX_YEAR)

    token2 = db.create_hicbc_link_invitation(b, TAX_YEAR)
    db.accept_hicbc_link_invitation(a, token2, TAX_YEAR)
    _mutual_consent(a, b)
    assert db.revoke_hicbc_link(b, TAX_YEAR)

    token3 = db.create_hicbc_link_invitation(a, TAX_YEAR)
    active = db.accept_hicbc_link_invitation(b, token3, TAX_YEAR)
    events = _permission_events(link["id"])
    assert active["permission_cycle"] == 3
    assert all(event["notice_version"] == db.HICBC_NOTICE_VERSION for event in events)
    assert [(event["permission_cycle"], event["event_type"]) for event in events] == [
        (1, "consent"), (1, "consent"), (1, "withdraw"), (1, "unlink"),
        (2, "relink"), (2, "consent"), (2, "consent"), (2, "withdraw"),
        (2, "unlink"), (3, "relink"),
    ]
    assert not db.has_mutual_hicbc_link_consent(a, TAX_YEAR)


def test_concurrent_consent_and_unlink_retries_do_not_duplicate_events(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    link = db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    binding = db.create_hicbc_link_permission_binding(a, TAX_YEAR)
    assert binding

    with ThreadPoolExecutor(max_workers=6) as pool:
        consent_results = list(pool.map(
            lambda _: db.record_hicbc_link_consent_from_binding(
                a,
                TAX_YEAR,
                db.HICBC_NOTICE_VERSION,
                permission_binding_token=binding,
            ),
            range(6),
        ))
    assert all(consent_results)
    assert [event["event_type"] for event in _permission_events(link["id"])] == ["consent"]

    with ThreadPoolExecutor(max_workers=6) as pool:
        revoke_results = list(pool.map(lambda _: db.revoke_hicbc_link(a, TAX_YEAR), range(6)))
    assert revoke_results.count(True) == 1
    assert [event["event_type"] for event in _permission_events(link["id"])] == [
        "consent", "withdraw", "unlink",
    ]


def test_account_deletion_removes_current_rows_and_lifecycle_history(tmp_db):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    link = db.accept_hicbc_link_invitation(b, token, TAX_YEAR)
    _mutual_consent(a, b)
    assert _permission_events(link["id"])

    assert db.delete_all_hicbc_links_for_user(a) >= 2
    assert _permission_events(link["id"]) == []
    assert db.get_hicbc_link_permission_status(b, TAX_YEAR) == {
        "linked": False,
        "own_permission": False,
        "mutual_permission": False,
    }
