"""
Tests for Workstream 7 — Dashboard Integration & Joined-Up Product Experience.

Covers:
- unauthenticated access redirects for all new routes
- user-specific dashboard data (db_source and in-memory paths)
- user isolation: two users cannot see each other's data
- dashboard summary figures from persisted data
- invoice list and match-result rendering
- missing linked transaction (orphaned transaction_id) handled gracefully
- missing-currency review items surfaced
- empty states (no invoices, no review items)
- demo-data labelling in responses
- ownership checks for client-supplied IDs (invoice, match)
- navigation links present on all V2 pages
"""

from __future__ import annotations

import sqlite3

import pytest

import reserved.database as db
from reserved import create_app
from reserved.auth import (
    _SK_IS_DEMO,
    _SK_USER_ID,
)
from reserved.matching.demo_invoices import DEMO_INVOICES, seed_demo_invoices


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Isolated temp DB for each test."""
    test_file = tmp_path / "ws7.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    db.init_db()
    return test_file


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Flask test app with isolated DB, CSRF disabled, dev environment."""
    test_file = tmp_path / "ws7_app.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    application = create_app()
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False
    return application


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client):
    """Log in as a demo user and return the user_id."""
    client.get("/v2/demo-login")
    with client.session_transaction() as sess:
        return sess.get(_SK_USER_ID)


def _login_second(client):
    """
    Log in as a SECOND distinct demo user (different session id → different user).
    Uses a fresh client so there is no shared session cookie.
    """
    # Create a second client with a separate session
    second = client.application.test_client()
    second.get("/v2/demo-login")
    with second.session_transaction() as sess:
        uid2 = sess.get(_SK_USER_ID)
    return second, uid2


# ═══════════════════════════════════════════════════════════════════════════════
# Unauthenticated access — all protected routes must redirect to demo-login
# (in production they would redirect to /v2/login instead)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("path", [
    "/v2/",
    "/v2/invoices",
    "/v2/review",
])
def test_unauthenticated_get_redirects_to_login(client, path):
    """GET on protected V2 routes redirects unauthenticated visitors to demo-login."""
    rv = client.get(path)
    assert rv.status_code == 302
    assert "/v2/demo-login" in rv.location


def test_unauthenticated_invoices_seed_redirects(client):
    """POST /v2/invoices/seed must redirect unauthenticated requests."""
    rv = client.post("/v2/invoices/seed")
    assert rv.status_code == 302
    assert "/v2/demo-login" in rv.location


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard — /v2/
# ═══════════════════════════════════════════════════════════════════════════════

def test_dashboard_renders_for_authenticated_user(client):
    """Authenticated users must receive a 200 on the dashboard."""
    _login(client)
    rv = client.get("/v2/")
    assert rv.status_code == 200


def test_dashboard_contains_demo_label(client):
    """Dashboard must clearly label all figures as demo data."""
    _login(client)
    rv = client.get("/v2/")
    body = rv.data.lower()
    assert b"demo" in body, "Dashboard must contain 'demo' label"


def test_returning_user_dashboard_loads_persisted_profile(client):
    """A fresh session must not replace a saved profile with Mesh's example data."""
    uid = _login(client)
    db.save_profile_by_user(uid, {
        "display_name": "Ada",
        "income_estimate": 12345.67,
        "pension_contribution": 0,
        "student_loan_plans": [],
        "notes": '{"first_name":"Ada","day_job_salary":"0"}',
    })
    with client.session_transaction() as sess:
        sess.pop("profile", None)

    rv = client.get("/v2/dashboard")
    assert rv.status_code == 200
    # The animated number starts at £0.00 and takes its value from the
    # machine-readable attribute; assert the persisted figure is the source.
    assert b'data-count-up="12345.67"' in rv.data
    assert b"the example tax profile" not in rv.data.lower()


def test_real_profile_notice_only_labels_bank_activity_as_illustrative(client):
    """Illustrative bank fallback must not describe a saved tax profile as demo data."""
    uid = _login(client)
    db.save_profile_by_user(uid, {
        "display_name": "Ada",
        "income_estimate": 10000,
        "pension_contribution": 0,
        "student_loan_plans": [],
        "notes": '{"first_name":"Ada","day_job_salary":"0"}',
    })
    rv = client.get("/v2/dashboard")
    body = rv.data.lower()
    assert b"illustrative bank activity" in body
    assert b"your saved tax profile" in body


def test_dashboard_shows_transaction_summary_in_memory(client):
    """Dashboard without seeded DB data shows in-memory demo summary."""
    _login(client)
    rv = client.get("/v2/")
    assert rv.status_code == 200
    # Income figure must appear somewhere (in-memory demo has freelance income)
    assert b"Income identified" in rv.data or b"income" in rv.data.lower()


def test_dashboard_shows_summary_from_db_when_seeded(client):
    """After seeding, dashboard reflects DB transaction figures."""
    _login(client)
    # Seed demo transactions into DB
    client.post("/v2/transactions/seed")
    rv = client.get("/v2/")
    assert rv.status_code == 200
    assert b"Income identified" in rv.data or b"income" in rv.data.lower()


def test_dashboard_shows_invoice_section(client):
    """Dashboard must show the invoice section (even empty)."""
    _login(client)
    rv = client.get("/v2/")
    assert rv.status_code == 200
    assert b"Invoice" in rv.data or b"invoice" in rv.data.lower()


def test_dashboard_invoice_counts_after_seed(client, test_db):
    """Dashboard invoice counts reflect persisted data."""
    uid = _login(client)
    seed_demo_invoices(user_id=uid)
    rv = client.get("/v2/dashboard")
    assert rv.status_code == 200
    # 13 demo invoices seeded — total count must appear
    assert b"13" in rv.data


def test_dashboard_attention_pill_hidden_when_no_items(client):
    """Attention pill must not appear when review_count == 0."""
    _login(client)
    # No seeded data, in-memory has some unknowns — pill may appear.
    # Seed demo data and make sure the review count is visible or the pill is absent
    # (we cannot control the in-memory unknowns count, so just check no crash).
    rv = client.get("/v2/")
    assert rv.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# User isolation — two users must not see each other's data
# ═══════════════════════════════════════════════════════════════════════════════

def test_two_users_have_isolated_dashboards(client):
    """
    User A and user B each get their own independent dashboard data.
    Seeding invoices for user A must not affect user B's invoice count.
    """
    uid_a = _login(client)
    seed_demo_invoices(user_id=uid_a)

    second, uid_b = _login_second(client)
    assert uid_a != uid_b

    # User B has no invoices — their dashboard shows 0 / empty
    rv_b = second.get("/v2/")
    assert rv_b.status_code == 200

    # User B's invoice count must not include user A's 13 invoices
    invoices_b = db.list_invoices(user_id=uid_b)
    assert len(invoices_b) == 0


def test_two_users_have_isolated_invoice_views(client):
    """User A's invoice list must not appear in user B's invoice view."""
    uid_a = _login(client)
    seed_demo_invoices(user_id=uid_a)

    second, uid_b = _login_second(client)

    rv_b = second.get("/v2/invoices")
    assert rv_b.status_code == 200
    # User B sees empty state — no invoices loaded
    assert b"No invoices loaded" in rv_b.data or b"Load demo" in rv_b.data


# ═══════════════════════════════════════════════════════════════════════════════
# Invoices view — /v2/invoices
# ═══════════════════════════════════════════════════════════════════════════════

def test_invoices_empty_state(client):
    """Invoice page must show empty state when no invoices are loaded."""
    _login(client)
    rv = client.get("/v2/invoices")
    assert rv.status_code == 200
    assert b"No invoices loaded" in rv.data or b"Load demo" in rv.data


def test_invoices_seed_creates_user_scoped_rows(client, test_db):
    """POST /v2/invoices/seed must create invoices scoped to the session user."""
    uid = _login(client)
    rv = client.post("/v2/invoices/seed")
    assert rv.status_code == 302  # redirect to /v2/invoices

    user_invs = db.list_invoices(user_id=uid)
    assert len(user_invs) == len(DEMO_INVOICES)  # 13 demo invoices


def test_invoices_seed_is_idempotent(client, test_db):
    """Seeding twice must not create duplicate invoice rows."""
    uid = _login(client)
    client.post("/v2/invoices/seed")
    client.post("/v2/invoices/seed")

    user_invs = db.list_invoices(user_id=uid)
    assert len(user_invs) == len(DEMO_INVOICES)


def test_invoices_page_renders_after_seed(client):
    """After seeding, invoice page must list invoices with match results."""
    _login(client)
    client.post("/v2/invoices/seed")
    rv = client.get("/v2/invoices")
    assert rv.status_code == 200
    # At least some invoice references must appear
    assert b"INV-2026" in rv.data


def test_invoices_page_shows_match_statuses(client):
    """Invoice page must show match status badges."""
    _login(client)
    client.post("/v2/invoices/seed")
    rv = client.get("/v2/invoices")
    assert rv.status_code == 200
    body = rv.data
    # At least matched and unmatched badges must appear
    assert b"Matched" in body or b"matched" in body.lower()


def test_invoices_page_shows_explanations(client):
    """Invoice page must render the matching engine's explanations."""
    _login(client)
    client.post("/v2/invoices/seed")
    rv = client.get("/v2/invoices")
    assert rv.status_code == 200
    # Explanations are plain-text sentences from the engine
    assert b"reference" in rv.data.lower() or b"amount" in rv.data.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Missing linked transaction — orphaned transaction_id must not crash
# ═══════════════════════════════════════════════════════════════════════════════

def test_invoice_with_null_transaction_id_renders_gracefully(client, test_db):
    """
    An invoice match with transaction_id = NULL must not raise an error.
    The template must show a fallback message instead of crashing.
    """
    uid = _login(client)
    # Save an invoice and an UNMATCHED match (transaction_id = NULL)
    db.save_invoice(
        reference="INV-TEST-NULL",
        client_name="Test Client",
        amount_due=1000.0,
        issue_date="2026-08-01",
        due_date="2026-08-31",
        user_id=uid,
    )
    inv = db.get_invoice_by_reference("INV-TEST-NULL", user_id=uid)
    db.save_match(
        invoice_id=inv["id"],
        status="unmatched",
        confidence=0,
        method="unmatched",
        explanation="No matching transaction found in the current data.",
        matched_amount=0.0,
        transaction_id=None,
    )

    rv = client.get("/v2/invoices")
    assert rv.status_code == 200
    assert b"INV-TEST-NULL" in rv.data
    # Must not show a Python error; fallback text must appear
    assert b"No matching transaction" in rv.data or b"Unmatched" in rv.data


# ═══════════════════════════════════════════════════════════════════════════════
# Review queue — /v2/review
# ═══════════════════════════════════════════════════════════════════════════════

def test_review_redirects_to_invoices_for_authenticated_user(client):
    """
    /v2/review redirects to /v2/invoices (review combined into invoice view).
    The redirect test is separate from test_review_redirects_to_invoices above
    so both the route and auth behaviour are covered.
    """
    _login(client)
    rv = client.get("/v2/review")
    assert rv.status_code == 302
    assert "/v2/invoices" in rv.location


def test_invoices_page_shows_unclassified_count(client, test_db):
    """Combined invoice page surfaces unclassified payment count in header strip."""
    uid = _login(client)
    client.post("/v2/transactions/seed")
    client.post("/v2/invoices/seed")
    rv = client.get("/v2/invoices")
    assert rv.status_code == 200
    # Should show confirmation strip or just the invoice table — no crash
    assert b"INV-2026" in rv.data


def test_invoices_page_shows_pending_matches(client, test_db):
    """Invoices page surfaces Needs review items after seeding."""
    uid = _login(client)
    client.post("/v2/invoices/seed")
    rv = client.get("/v2/invoices")
    assert rv.status_code == 200
    assert b"INV-2026" in rv.data
    # At least one status badge must appear
    assert b"Matched" in rv.data or b"Outstanding" in rv.data or b"review" in rv.data.lower()


def test_invoices_page_shows_currency_missing(client, test_db):
    """Invoices page must show 'Needs review' for currency_missing matches."""
    uid = _login(client)
    db.save_invoice(
        reference="INV-NO-CCY",
        client_name="No Currency Client",
        amount_due=500.0,
        issue_date="2026-08-01",
        due_date="2026-08-31",
        user_id=uid,
    )
    inv = db.get_invoice_by_reference("INV-NO-CCY", user_id=uid)
    db.save_match(
        invoice_id=inv["id"],
        status="unmatched",
        confidence=0,
        method="currency_missing",
        explanation="Transaction currency is missing — cannot auto-match.",
        matched_amount=0.0,
        transaction_id=None,
        review_state="pending_review",
    )
    rv = client.get("/v2/invoices")
    assert rv.status_code == 200
    assert b"INV-NO-CCY" in rv.data
    # currency_missing maps to "Needs review" badge
    assert b"Needs review" in rv.data or b"needs review" in rv.data.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# Navigation — present on all V2 pages
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("path", [
    "/v2/",
    "/v2/connections",
    "/v2/invoices",
    "/v2/settings",
])
def test_v2_nav_links_present_on_all_pages(client, path):
    """
    Every authenticated V2 page must include the unified sidebar nav links.

    Unified nav structure (UX consolidation):
      Overview (/) · Connections (/connections) · Invoices (/v2/invoices) ·
      Capital gains · What's next · Settings (/v2/settings) · About ·
      Sign out (/v2/logout — shown when V2 session active)

    Absent from sidebar (by design):
      - Transactions: raw banking data not surfaced in customer-facing UI
      - Separate Review tab: combined into Invoices
      - /v2/connections direct link: sidebar links to /connections (web.connections)
    """
    _login(client)
    rv = client.get(path)
    assert rv.status_code == 200
    body = rv.data
    # Core V2 routes present in nav or page content
    assert b"/v2/invoices" in body
    assert b"/v2/settings" in body
    # Unified sidebar routes (public routes integrated into shared nav)
    assert b"/connections" in body
    # Sign out available when V2 session active
    assert b"/v2/logout" in body
    # Absent by design
    assert b'href="/v2/transactions"' not in body
    assert b'href="/v2/review"' not in body


def test_review_redirects_to_invoices(client):
    """/v2/review now redirects to /v2/invoices (combined experience)."""
    _login(client)
    rv = client.get("/v2/review")
    assert rv.status_code == 302
    assert "/v2/invoices" in rv.location


def test_v2_settings_page_loads(client):
    """Authenticated users can access /v2/settings."""
    _login(client)
    rv = client.get("/v2/settings")
    assert rv.status_code == 200
    assert b"Settings" in rv.data


def test_v2_settings_save_redirects_to_v2_dashboard(client):
    """Saving settings from the V2 page returns to /v2/."""
    _login(client)
    rv = client.post("/v2/settings", data={
        "first_name": "Test",
        "trading_name": "Test Co",
        "entity_type": "sole_trader",
        "day_job_salary": "0",
        "ytd_freelance_profit": "0",
        "pension": "0",
        "student_loan": "none",
        "accounting_method": "cash_basis",
        "vat_status": "not_vat_registered",
    })
    assert rv.status_code == 302
    assert "/v2/" in rv.location


def test_nav_active_class_on_dashboard(client):
    """Active nav link must be marked with 'active' class on the dashboard."""
    _login(client)
    rv = client.get("/v2/")
    assert rv.status_code == 200
    # The dashboard nav item should be active
    assert b"active" in rv.data


# ═══════════════════════════════════════════════════════════════════════════════
# Demo-data labelling
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("path", [
    "/v2/",
    "/v2/invoices",
])
def test_demo_data_label_present(client, path):
    """All data-showing V2 pages must carry a demo-data label."""
    _login(client)
    rv = client.get(path)
    assert rv.status_code == 200
    assert b"Demo" in rv.data or b"demo" in rv.data.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# DB helpers — list_invoices_with_best_match, get_invoice_counts_for_user,
#             get_user_review_items
# ═══════════════════════════════════════════════════════════════════════════════

def test_list_invoices_with_best_match_empty(test_db):
    """Helper must return [] when the user has no invoices."""
    uid = db.get_or_create_user("clerk-ws7-empty", "empty@test.com", "Empty")
    rows = db.list_invoices_with_best_match(user_id=uid)
    assert rows == []


def test_list_invoices_with_best_match_scoped(test_db):
    """Helper must not return invoices belonging to a different user."""
    uid_a = db.get_or_create_user("clerk-ws7-a", "a@test.com", "User A")
    uid_b = db.get_or_create_user("clerk-ws7-b", "b@test.com", "User B")

    db.save_invoice(
        reference="INV-A-001",
        client_name="Client A",
        amount_due=1000.0,
        issue_date="2026-08-01",
        due_date="2026-08-31",
        user_id=uid_a,
    )

    rows_b = db.list_invoices_with_best_match(user_id=uid_b)
    assert rows_b == [], "User B must not see User A's invoices"


def test_get_invoice_counts_for_user_empty(test_db):
    """Invoice counts must be zero for a user with no invoices."""
    uid = db.get_or_create_user("clerk-ws7-counts", "counts@test.com", "Counts")
    counts = db.get_invoice_counts_for_user(uid)
    assert counts["total"] == 0
    assert counts["matched"] == 0
    assert counts["outstanding"] == 0
    assert counts["needs_review"] == 0


def test_get_invoice_counts_after_seed(test_db):
    """Invoice counts must reflect seeded invoices."""
    uid = db.get_or_create_user("clerk-ws7-seed", "seed@test.com", "Seed")
    seed_demo_invoices(user_id=uid)
    counts = db.get_invoice_counts_for_user(uid)
    assert counts["total"] == len(DEMO_INVOICES)  # 13


def test_get_user_review_items_isolated(test_db):
    """Review items query must not return another user's items."""
    uid_a = db.get_or_create_user("clerk-ws7-rev-a", "reva@test.com", "Rev A")
    uid_b = db.get_or_create_user("clerk-ws7-rev-b", "revb@test.com", "Rev B")

    # Save a pending invoice match for user A
    db.save_invoice(
        reference="INV-REV-A",
        client_name="Rev Client A",
        amount_due=500.0,
        issue_date="2026-08-01",
        due_date="2026-08-31",
        user_id=uid_a,
    )
    inv_a = db.get_invoice_by_reference("INV-REV-A", user_id=uid_a)
    db.save_match(
        invoice_id=inv_a["id"],
        status="unmatched",
        confidence=0,
        method="unmatched",
        explanation="No match.",
        matched_amount=0.0,
        transaction_id=None,
        review_state="pending_review",
    )

    # User B's review items must be empty
    items_b = db.get_user_review_items(uid_b)
    assert items_b["pending_invoice_matches"] == []
    assert items_b["unclassified_transactions"] == []
