"""HICBC linked-account consent, cross-account authorisation and retention tests.

Covers the HICBC-only mutual-consent link lifecycle (invite → accept → revoke →
re-link), single-use/high-entropy token handling, duplicate-link and self-link
rejection, owner-scoped access, privacy (no partner ANI is stored in link rows
or returned to the other party), manual-vs-linked conflict resolution (neither
source has precedence), and the repository deletion hooks.
"""

from __future__ import annotations

import json
from pathlib import Path

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
    })
    return uid


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
    for cols in (link_cols, inv_cols):
        assert "ani" not in " ".join(cols).lower()
        assert "income" not in " ".join(cols).lower()
        assert "monetary" not in " ".join(cols).lower()


# ── Privacy + manual/linked conflict resolution ──────────────────────────────

def test_linked_partner_raw_ani_never_in_customer_payload(app):
    a = _user("clerk_a", 70000)
    b = _user("clerk_b", 90000)
    token = db.create_hicbc_link_invitation(a, TAX_YEAR)
    db.accept_hicbc_link_invitation(b, token, TAX_YEAR)

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

    # Manual estimate says partner ~50k; linked evidence says partner ~90k.
    db.save_hicbc_estimate(a, {
        "tax_year": TAX_YEAR,
        "receives_child_benefit": 1,
        "child_benefit_children": 1,
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

    # No manual estimate, but Child Benefit facts are still required; set them
    # via a manual row that does not declare a partner.
    db.save_hicbc_estimate(a, {
        "tax_year": TAX_YEAR,
        "receives_child_benefit": 1,
        "child_benefit_children": 1,
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

    db.save_hicbc_estimate(a, {
        "tax_year": TAX_YEAR,
        "receives_child_benefit": 1,
        "child_benefit_children": 1,
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
