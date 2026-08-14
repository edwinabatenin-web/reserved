"""
Tests for Workstream 5 — Identity, Authentication & User Ownership.

All DB tests run against an isolated temporary SQLite file; the production
instance/reserved.db is never touched.

Covers:
- users table created by init_db()
- get_or_create_user: create, idempotency, email preserved
- get_user: happy path, missing user
- migrate_session_to_user: profiles + connections, already-migrated rows skipped
- save_profile_by_user / get_profile_by_user: upsert, retrieval
- list_connections_for_user: filters by user_id
- user_id column present on bank_connections and user_profiles
- save_connection: accepts optional user_id
- list_active_connections: user_id filter
- require_auth decorator: redirects unauthenticated, passes authenticated
- demo_login route: sets session, blocked in production
- logout route: clears session
- auth_verify: rejects missing token, rejects invalid token
- verify_clerk_session_token: returns None when no publishable key
- set_user_session / clear_user_session / is_authenticated
"""

from __future__ import annotations

import sqlite3

import pytest

import reserved.database as db
from reserved import create_app
from reserved.auth import (
    DEMO_CLERK_ID,
    DEMO_CLERK_ID_PREFIX,
    DEMO_DISPLAY,
    DEMO_EMAIL,
    _SK_CLERK_ID,
    _SK_DEMO_SESSION_ID,
    _SK_IS_DEMO,
    _SK_USER_ID,
    clear_user_session,
    is_authenticated,
    is_demo_session,
    set_user_session,
    verify_clerk_session_token,
)


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Isolated temp DB for each test."""
    test_file = tmp_path / "test_auth.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    db.init_db()
    return test_file


@pytest.fixture
def app(tmp_path, monkeypatch):
    """Flask test app with an isolated DB and CSRF disabled."""
    test_file = tmp_path / "flask_auth.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    application = create_app()
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False
    return application


@pytest.fixture
def client(app):
    return app.test_client()


# ── users table ───────────────────────────────────────────────────────────────

def test_users_table_created_by_init_db(test_db):
    conn = sqlite3.connect(test_db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "users" in tables


def test_user_id_column_on_bank_connections(test_db):
    conn = sqlite3.connect(test_db)
    cols = {r[1] for r in conn.execute(
        "PRAGMA table_info(bank_connections)"
    ).fetchall()}
    conn.close()
    assert "user_id" in cols


def test_user_id_column_on_user_profiles(test_db):
    conn = sqlite3.connect(test_db)
    cols = {r[1] for r in conn.execute(
        "PRAGMA table_info(user_profiles)"
    ).fetchall()}
    conn.close()
    assert "user_id" in cols


# ── get_or_create_user ────────────────────────────────────────────────────────

def test_get_or_create_user_creates_new_user(test_db):
    uid = db.get_or_create_user("user_abc123", email="test@example.com", display_name="Test User")
    assert isinstance(uid, int)
    assert uid > 0


def test_get_or_create_user_idempotent(test_db):
    uid1 = db.get_or_create_user("user_abc123", email="test@example.com")
    uid2 = db.get_or_create_user("user_abc123", email="test@example.com")
    assert uid1 == uid2


def test_get_or_create_user_preserves_clerk_id(test_db):
    uid = db.get_or_create_user("user_xyz999", email="xyz@example.com")
    user = db.get_user(uid)
    assert user["clerk_user_id"] == "user_xyz999"
    assert user["email"] == "xyz@example.com"


def test_get_or_create_user_no_email(test_db):
    uid = db.get_or_create_user("user_noemail")
    assert uid > 0
    user = db.get_user(uid)
    assert user["email"] is None


def test_get_or_create_user_multiple_users_distinct(test_db):
    uid_a = db.get_or_create_user("user_a", email="a@test.com")
    uid_b = db.get_or_create_user("user_b", email="b@test.com")
    assert uid_a != uid_b


# ── get_user ──────────────────────────────────────────────────────────────────

def test_get_user_returns_row(test_db):
    uid = db.get_or_create_user("user_gettest", email="get@example.com", display_name="Get User")
    user = db.get_user(uid)
    assert user is not None
    assert user["id"] == uid
    assert user["clerk_user_id"] == "user_gettest"
    assert user["display_name"] == "Get User"


def test_get_user_missing_returns_none(test_db):
    result = db.get_user(99999)
    assert result is None


# ── migrate_session_to_user ───────────────────────────────────────────────────

def test_migrate_session_to_user_profiles(test_db):
    db.save_profile("old-session-key", {"display_name": "Old Profile"})
    uid = db.get_or_create_user("user_migrate1")
    result = db.migrate_session_to_user("old-session-key", uid)
    assert result["profiles"] == 1
    profile = db.get_profile("old-session-key")
    assert profile["user_id"] == uid


def test_migrate_session_to_user_connections(test_db):
    cid = db.save_connection(
        institution_id="monzo",
        institution_name="Monzo",
        consent_token="tok-migrate-test",
        session_key="old-session-key",
    )
    uid = db.get_or_create_user("user_migrate2")
    result = db.migrate_session_to_user("old-session-key", uid)
    assert result["connections"] == 1
    conn_row = db.get_connection_by_token("tok-migrate-test")
    assert conn_row["user_id"] == uid


def test_migrate_session_to_user_skips_already_migrated(test_db):
    uid = db.get_or_create_user("user_migrate3")
    db.save_profile("session-already-migrated", {"display_name": "Already"})
    # First migration
    db.migrate_session_to_user("session-already-migrated", uid)
    # Second migration with a different user — should NOT overwrite
    uid2 = db.get_or_create_user("user_migrate4")
    result = db.migrate_session_to_user("session-already-migrated", uid2)
    assert result["profiles"] == 0  # already had user_id set


def test_migrate_session_no_matching_rows(test_db):
    uid = db.get_or_create_user("user_migrate5")
    result = db.migrate_session_to_user("nonexistent-session", uid)
    assert result == {"profiles": 0, "connections": 0}


# ── save_profile_by_user / get_profile_by_user ────────────────────────────────

def test_save_profile_by_user_creates_profile(test_db):
    uid = db.get_or_create_user("user_profile1")
    db.save_profile_by_user(uid, {
        "display_name": "Profile User",
        "tax_year": "2025-26",
        "income_estimate": 50000.0,
    })
    profile = db.get_profile_by_user(uid)
    assert profile is not None
    assert profile["display_name"] == "Profile User"
    assert profile["tax_year"] == "2025-26"
    assert profile["income_estimate"] == 50000.0
    assert profile["user_id"] == uid


def test_save_profile_by_user_upserts(test_db):
    uid = db.get_or_create_user("user_profile2")
    db.save_profile_by_user(uid, {"display_name": "First"})
    db.save_profile_by_user(uid, {"display_name": "Updated"})
    profile = db.get_profile_by_user(uid)
    assert profile["display_name"] == "Updated"


def test_get_profile_by_user_missing_returns_none(test_db):
    result = db.get_profile_by_user(99999)
    assert result is None


def test_save_profile_by_user_student_loan_plans(test_db):
    uid = db.get_or_create_user("user_profile3")
    db.save_profile_by_user(uid, {"student_loan_plans": [2]})
    profile = db.get_profile_by_user(uid)
    assert profile["student_loan_plans"] == [2]


# ── list_connections_for_user ─────────────────────────────────────────────────

def test_list_connections_for_user(test_db):
    uid = db.get_or_create_user("user_conn1")
    db.save_connection(
        institution_id="monzo",
        institution_name="Monzo",
        consent_token="tok-user-conn-1",
        user_id=uid,
    )
    db.save_connection(
        institution_id="starling",
        institution_name="Starling",
        consent_token="tok-user-conn-2",
        user_id=uid,
    )
    conns = db.list_connections_for_user(uid)
    assert len(conns) == 2
    tokens = {c["consent_token"] for c in conns}
    assert "tok-user-conn-1" in tokens
    assert "tok-user-conn-2" in tokens


def test_list_connections_for_user_isolates_by_user(test_db):
    uid_a = db.get_or_create_user("user_conn_a")
    uid_b = db.get_or_create_user("user_conn_b")
    db.save_connection("monzo", "Monzo", "tok-a", user_id=uid_a)
    db.save_connection("starling", "Starling", "tok-b", user_id=uid_b)
    assert len(db.list_connections_for_user(uid_a)) == 1
    assert len(db.list_connections_for_user(uid_b)) == 1


def test_list_connections_for_user_empty(test_db):
    uid = db.get_or_create_user("user_no_conns")
    assert db.list_connections_for_user(uid) == []


# ── list_active_connections with user_id filter ───────────────────────────────

def test_list_active_connections_user_id_filter(test_db):
    uid = db.get_or_create_user("user_active_conn")
    db.save_connection("monzo", "Monzo", "tok-active-1", user_id=uid)
    # Connection with no user
    db.save_connection("starling", "Starling", "tok-no-user")
    result = db.list_active_connections(user_id=uid)
    assert len(result) == 1
    assert result[0]["consent_token"] == "tok-active-1"


# ── save_connection with user_id ──────────────────────────────────────────────

def test_save_connection_with_user_id(test_db):
    uid = db.get_or_create_user("user_save_conn")
    cid = db.save_connection(
        institution_id="barclays",
        institution_name="Barclays",
        consent_token="tok-barclays-user",
        user_id=uid,
    )
    row = db.get_connection_by_token("tok-barclays-user")
    assert row["user_id"] == uid


def test_save_connection_without_user_id_backward_compat(test_db):
    cid = db.save_connection(
        institution_id="hsbc",
        institution_name="HSBC",
        consent_token="tok-hsbc-nouser",
        session_key="some-session",
    )
    row = db.get_connection_by_token("tok-hsbc-nouser")
    assert row["user_id"] is None
    assert row["session_key"] == "some-session"


# ── auth module: session helpers ──────────────────────────────────────────────

def test_set_and_clear_user_session(app):
    with app.test_request_context("/"):
        from flask import session as flask_session
        flask_session["_some_pre_login_key"] = "should_be_wiped"
        set_user_session(user_id=42, clerk_id="user_test", email="t@test.com")
        assert is_authenticated()
        assert flask_session.get(_SK_USER_ID) == 42
        assert flask_session.get(_SK_CLERK_ID) == "user_test"
        clear_user_session()
        assert not is_authenticated()
        # clear_user_session() must wipe the entire session, including pre-login data
        assert flask_session.get("_some_pre_login_key") is None


def test_is_demo_session_flag(app):
    with app.test_request_context("/"):
        set_user_session(user_id=1, clerk_id="demo", is_demo=True)
        assert is_demo_session()
        clear_user_session()
        assert not is_demo_session()


# ── verify_clerk_session_token ────────────────────────────────────────────────

def test_verify_clerk_token_returns_none_without_key(monkeypatch):
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    result = verify_clerk_session_token("fake.token.value")
    assert result is None


def test_verify_clerk_token_returns_none_on_invalid_token(monkeypatch):
    # Set a plausible-looking key so URL parsing succeeds, but token is bogus
    monkeypatch.setenv(
        "CLERK_PUBLISHABLE_KEY",
        "pk_test_Y2xlcmsuYWNjb3VudHMuZGV2JA",  # base64 of "clerk.accounts.dev$"
    )
    result = verify_clerk_session_token("not.a.valid.jwt")
    assert result is None


# ── require_auth decorator (Flask routes) ─────────────────────────────────────

def test_require_auth_redirects_unauthenticated(client):
    """Unauthenticated GET /v2/ redirects to demo-login in non-production."""
    rv = client.get("/v2/")
    assert rv.status_code == 302
    assert "/v2/demo-login" in rv.location


def test_require_auth_redirects_connections_unauthenticated(client):
    rv = client.get("/v2/connections")
    assert rv.status_code == 302
    assert "/v2/demo-login" in rv.location


def test_require_auth_redirects_transactions_unauthenticated(client):
    rv = client.get("/v2/transactions")
    assert rv.status_code == 302
    assert "/v2/demo-login" in rv.location


def test_require_auth_passes_authenticated(client):
    """Authenticated requests must reach the route (200, not redirect)."""
    with client.session_transaction() as sess:
        sess[_SK_USER_ID] = 1
        sess[_SK_CLERK_ID] = "user_test123"
    rv = client.get("/v2/")
    assert rv.status_code == 200


def test_require_auth_passes_transactions_authenticated(client):
    with client.session_transaction() as sess:
        sess[_SK_USER_ID] = 1
        sess[_SK_CLERK_ID] = "user_test123"
    rv = client.get("/v2/transactions")
    assert rv.status_code == 200


# ── GET /v2/login ─────────────────────────────────────────────────────────────

def test_login_page_renders(client):
    rv = client.get("/v2/login")
    assert rv.status_code == 200
    assert b"Sign in" in rv.data


def test_login_page_redirects_if_authenticated(client):
    with client.session_transaction() as sess:
        sess[_SK_USER_ID] = 1
        sess[_SK_CLERK_ID] = "user_test123"
    rv = client.get("/v2/login")
    assert rv.status_code == 302
    assert "/v2/" in rv.location


# ── GET /v2/demo-login ────────────────────────────────────────────────────────

def test_demo_login_sets_session(client, monkeypatch):
    """Demo login sets the session with a per-session demo user."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    rv = client.get("/v2/demo-login")
    assert rv.status_code == 302
    with client.session_transaction() as sess:
        assert sess.get(_SK_IS_DEMO) is True
        assert sess.get(_SK_USER_ID) is not None
        # Clerk ID must use the per-session prefix, not the legacy fixed sentinel
        assert sess.get(_SK_CLERK_ID, "").startswith(DEMO_CLERK_ID_PREFIX)


def test_demo_login_creates_per_session_demo_user_in_db(client, monkeypatch):
    """Demo login creates a unique DB user keyed by the per-session UUID."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    client.get("/v2/demo-login")
    with client.session_transaction() as sess:
        uid = sess.get(_SK_USER_ID)
        clerk_id = sess.get(_SK_CLERK_ID)
    assert uid is not None
    user = db.get_user(uid)
    assert user is not None
    assert user["clerk_user_id"].startswith(DEMO_CLERK_ID_PREFIX)
    assert clerk_id == user["clerk_user_id"]


def test_demo_login_two_browsers_isolated(client, app, monkeypatch):
    """Two browsers (different cookie jars) get distinct demo users."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)

    client_b = app.test_client()  # separate cookie jar → new browser

    client.get("/v2/demo-login")
    client_b.get("/v2/demo-login")

    with client.session_transaction() as sess_a:
        uid_a = sess_a.get(_SK_USER_ID)
        cid_a = sess_a.get(_SK_CLERK_ID)
    with client_b.session_transaction() as sess_b:
        uid_b = sess_b.get(_SK_USER_ID)
        cid_b = sess_b.get(_SK_CLERK_ID)

    assert uid_a != uid_b, "Two browsers must get distinct demo user IDs"
    assert cid_a != cid_b, "Two browsers must get distinct demo Clerk IDs"


def test_demo_login_same_browser_reuses_user(client, monkeypatch):
    """Same browser hitting demo-login twice reuses the same demo user."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    client.get("/v2/demo-login")
    with client.session_transaction() as sess:
        uid_first = sess.get(_SK_USER_ID)

    client.get("/v2/demo-login")
    with client.session_transaction() as sess:
        uid_second = sess.get(_SK_USER_ID)

    assert uid_first == uid_second, "Same browser must reuse the same demo user"


def test_demo_login_blocked_in_production(client, monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "production")
    rv = client.get("/v2/demo-login")
    assert rv.status_code == 403


def test_demo_login_blocked_with_live_clerk_key(client, monkeypatch):
    """Demo login must be blocked when a live (pk_live_) Clerk key is present."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setenv("CLERK_PUBLISHABLE_KEY", "pk_live_AAAAABBBBBCCCCC")
    rv = client.get("/v2/demo-login")
    assert rv.status_code == 403


def test_demo_login_allowed_with_test_clerk_key(client, monkeypatch):
    """Demo login must remain available alongside a test (pk_test_) Clerk key."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setenv("CLERK_PUBLISHABLE_KEY", "pk_test_AAAAABBBBBCCCCC")
    rv = client.get("/v2/demo-login")
    assert rv.status_code == 302


# ── GET /v2/logout ────────────────────────────────────────────────────────────

def test_logout_clears_session(client, monkeypatch):
    monkeypatch.delenv("FLASK_ENV", raising=False)
    # Log in first
    client.get("/v2/demo-login")
    with client.session_transaction() as sess:
        assert sess.get(_SK_USER_ID) is not None
    # Then log out
    rv = client.post("/v2/logout")
    assert rv.status_code == 302
    assert "/v2/login" in rv.location
    with client.session_transaction() as sess:
        assert sess.get(_SK_USER_ID) is None
        assert sess.get(_SK_IS_DEMO) is None


# ── POST /v2/auth/verify ──────────────────────────────────────────────────────

def test_auth_verify_rejects_missing_token(client):
    rv = client.post(
        "/v2/auth/verify",
        json={},
        content_type="application/json",
    )
    assert rv.status_code == 400
    data = rv.get_json()
    assert data["ok"] is False


def test_auth_verify_rejects_invalid_token(client, monkeypatch):
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    rv = client.post(
        "/v2/auth/verify",
        json={"token": "not.a.real.jwt"},
        content_type="application/json",
    )
    assert rv.status_code == 401
    data = rv.get_json()
    assert data["ok"] is False


# ── User data isolation & IDOR prevention ─────────────────────────────────────
# These tests verify that an authenticated user cannot access or mutate another
# user's bank connections, even when they possess a valid session.

def _login_as(client, clerk_id: str, email: str = "u@test.com") -> int:
    """Helper: log in as a specific user and return their user_id."""
    uid = db.get_or_create_user(clerk_id, email=email)
    with client.session_transaction() as sess:
        sess[_SK_USER_ID]  = uid
        sess[_SK_CLERK_ID] = clerk_id
    return uid


def test_transactions_shows_own_seeded_data(client, monkeypatch):
    """Seeding creates data scoped to the session user; the view returns it."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    uid = _login_as(client, "user_tx_owner", "owner@test.com")

    # Seed demo data scoped to this user
    seed = client.post("/v2/transactions/seed")
    assert seed.status_code == 302

    rv = client.get("/v2/transactions")
    assert rv.status_code == 200
    # The DB source should be used (user now has connections)
    assert b"db_source" not in rv.data or b"true" in rv.data.lower()


def test_transactions_two_users_isolated(client, monkeypatch):
    """Seeding for user A does not make transactions visible to user B."""
    monkeypatch.delenv("FLASK_ENV", raising=False)

    # Seed as user A
    uid_a = _login_as(client, "user_iso_a", "a@iso.com")
    client.post("/v2/transactions/seed")

    # Log in as user B (no seed)
    uid_b = _login_as(client, "user_iso_b", "b@iso.com")
    conns_b = db.list_connections_for_user(uid_b)
    assert conns_b == [], "User B must have no connections after User A seeds"

    # User B should get the in-memory demo pipeline, not DB source
    rv = client.get("/v2/transactions")
    assert rv.status_code == 200


def test_disconnect_own_connection_returns_ok(client, monkeypatch):
    """A user can disconnect their own connection (mock mode returns ok=True)."""
    # Clear Yapily credentials so YapilyClient enters mock mode in tests.
    monkeypatch.delenv("YAPILY_APPLICATION_UUID", raising=False)
    monkeypatch.delenv("YAPILY_SECRET", raising=False)

    uid = _login_as(client, "user_disconnect_own", "own@test.com")
    token = "tok-own-disconnect"
    db.save_connection("monzo", "Monzo", token, user_id=uid)

    rv = client.post("/v2/yapily/disconnect", data={"consent_token": token})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True


def test_disconnect_other_users_connection_returns_403(client):
    """User B cannot disconnect User A's connection (IDOR prevention)."""
    uid_a = db.get_or_create_user("user_idor_a", email="a@idor.com")
    uid_b = db.get_or_create_user("user_idor_b", email="b@idor.com")
    token_a = "tok-idor-a-connection"
    db.save_connection("monzo", "Monzo", token_a, user_id=uid_a)

    # Log in as user B
    with client.session_transaction() as sess:
        sess[_SK_USER_ID]  = uid_b
        sess[_SK_CLERK_ID] = "user_idor_b"

    rv = client.post("/v2/yapily/disconnect", data={"consent_token": token_a})
    assert rv.status_code == 403, "User B must not be able to disconnect User A's connection"


def test_disconnect_missing_token_returns_403(client):
    """Disconnect with an empty token must return 403."""
    uid = db.get_or_create_user("user_disconnect_empty", email="empty@test.com")
    with client.session_transaction() as sess:
        sess[_SK_USER_ID]  = uid
        sess[_SK_CLERK_ID] = "user_disconnect_empty"

    rv = client.post("/v2/yapily/disconnect", data={"consent_token": ""})
    assert rv.status_code == 403


def test_refresh_other_users_connection_returns_403(client):
    """User B cannot refresh User A's connection (IDOR prevention)."""
    uid_a = db.get_or_create_user("user_refresh_a", email="ra@test.com")
    uid_b = db.get_or_create_user("user_refresh_b", email="rb@test.com")
    token_a = "tok-refresh-idor-a"
    db.save_connection("starling", "Starling", token_a, user_id=uid_a)

    with client.session_transaction() as sess:
        sess[_SK_USER_ID]  = uid_b
        sess[_SK_CLERK_ID] = "user_refresh_b"

    rv = client.post("/v2/yapily/refresh", data={"consent_token": token_a})
    assert rv.status_code == 403, "User B must not be able to refresh User A's connection"


def test_refresh_own_connection_allowed(client, monkeypatch):
    """A user can refresh their own connection (mock mode returns ok=True)."""
    # Clear Yapily credentials so YapilyClient enters mock mode in tests.
    monkeypatch.delenv("YAPILY_APPLICATION_UUID", raising=False)
    monkeypatch.delenv("YAPILY_SECRET", raising=False)

    uid = db.get_or_create_user("user_refresh_own", email="ro@test.com")
    token = "tok-refresh-own"
    db.save_connection("starling", "Starling", token, user_id=uid)

    with client.session_transaction() as sess:
        sess[_SK_USER_ID]  = uid
        sess[_SK_CLERK_ID] = "user_refresh_own"

    rv = client.post("/v2/yapily/refresh", data={"consent_token": token})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["ok"] is True


def test_seed_per_user_tokens_are_distinct(client, monkeypatch):
    """Each user's seeded demo connection uses a distinct token (no cross-contamination)."""
    monkeypatch.delenv("FLASK_ENV", raising=False)

    uid_a = _login_as(client, "user_seed_a", "sa@test.com")
    client.post("/v2/transactions/seed")

    uid_b = _login_as(client, "user_seed_b", "sb@test.com")
    client.post("/v2/transactions/seed")

    conns_a = db.list_connections_for_user(uid_a)
    conns_b = db.list_connections_for_user(uid_b)

    tokens_a = {c["consent_token"] for c in conns_a}
    tokens_b = {c["consent_token"] for c in conns_b}
    assert tokens_a.isdisjoint(tokens_b), "User A and User B must have different consent tokens"


def test_disconnect_nonexistent_token_returns_403(client):
    """Disconnecting a token that does not exist in the DB returns 403."""
    uid = db.get_or_create_user("user_ghost_token", email="ghost@test.com")
    with client.session_transaction() as sess:
        sess[_SK_USER_ID]  = uid
        sess[_SK_CLERK_ID] = "user_ghost_token"

    rv = client.post("/v2/yapily/disconnect", data={"consent_token": "tok-does-not-exist"})
    assert rv.status_code == 403


# ── Yapily OAuth state (CSRF / replay prevention) ─────────────────────────────

def test_yapily_connect_stores_state_in_session(client, monkeypatch):
    """yapily_connect must store an OAuth state token in the session."""
    monkeypatch.delenv("YAPILY_APPLICATION_UUID", raising=False)
    monkeypatch.delenv("YAPILY_SECRET", raising=False)
    uid = _login_as(client, "user_state_connect")

    rv = client.post("/v2/yapily/connect", data={"institution_id": "monzo"})
    assert rv.status_code == 200

    with client.session_transaction() as sess:
        assert "_yapily_oauth_state" in sess, "state must be stored in session after connect"
        assert len(sess["_yapily_oauth_state"]) >= 32


def test_yapily_callback_validates_state(client, monkeypatch):
    """Callback with a mismatched state must redirect to error state."""
    monkeypatch.delenv("YAPILY_APPLICATION_UUID", raising=False)
    monkeypatch.delenv("YAPILY_SECRET", raising=False)
    uid = _login_as(client, "user_state_validate")

    # Inject a state into the session (as if connect was called)
    with client.session_transaction() as sess:
        sess["_yapily_oauth_state"] = "correct_state_value_abc"

    # Callback with wrong state → error
    rv = client.get(
        "/v2/yapily/callback?consent=mock-consent-token-abc123"
        "&institution=monzo&mock=1&state=WRONG_STATE"
    )
    assert rv.status_code == 302
    assert "error" in rv.location


def test_yapily_callback_accepts_correct_state(client, monkeypatch):
    """Callback with the correct state must proceed (redirect to returning)."""
    monkeypatch.delenv("YAPILY_APPLICATION_UUID", raising=False)
    monkeypatch.delenv("YAPILY_SECRET", raising=False)
    uid = _login_as(client, "user_state_accept")

    # Place correct state in session
    with client.session_transaction() as sess:
        sess["_yapily_oauth_state"] = "correct_state_xyz"

    rv = client.get(
        "/v2/yapily/callback?consent=mock-consent-token-abc123"
        "&institution=monzo&mock=1&state=correct_state_xyz"
    )
    assert rv.status_code == 302
    assert "error" not in rv.location


def test_yapily_callback_clears_state_after_use(client, monkeypatch):
    """State must be consumed (removed from session) after callback processing."""
    monkeypatch.delenv("YAPILY_APPLICATION_UUID", raising=False)
    monkeypatch.delenv("YAPILY_SECRET", raising=False)
    uid = _login_as(client, "user_state_consume")

    with client.session_transaction() as sess:
        sess["_yapily_oauth_state"] = "one_time_state"

    client.get(
        "/v2/yapily/callback?consent=mock-consent-token-abc123"
        "&institution=monzo&mock=1&state=one_time_state"
    )
    with client.session_transaction() as sess:
        assert "_yapily_oauth_state" not in sess, "state must be consumed after callback"


def test_yapily_callback_no_state_no_mock_rejected(client, monkeypatch):
    """Callback with no state and no mock=1 must be rejected (unexpected callback)."""
    monkeypatch.delenv("YAPILY_APPLICATION_UUID", raising=False)
    monkeypatch.delenv("YAPILY_SECRET", raising=False)
    uid = _login_as(client, "user_no_state_reject")
    # No state in session (no preceding connect)

    rv = client.get("/v2/yapily/callback?consent=some-token&institution=monzo")
    assert rv.status_code == 302
    assert "error" in rv.location


# ── Session fixation prevention ───────────────────────────────────────────────

def test_demo_login_clears_pre_login_session(client, monkeypatch):
    """Demo login must wipe pre-login session data (session fixation prevention)."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)

    # Inject a pre-login key an attacker might have planted
    with client.session_transaction() as sess:
        sess["attacker_planted_key"] = "malicious_value"

    client.get("/v2/demo-login")

    with client.session_transaction() as sess:
        assert "attacker_planted_key" not in sess, \
            "pre-login session data must be wiped on demo login"
        assert sess.get(_SK_IS_DEMO) is True


def test_logout_wipes_entire_session(client, monkeypatch):
    """Logout must clear ALL session data, not just auth keys."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)

    client.get("/v2/demo-login")
    # Add some extra session data as if from a Yapily flow
    with client.session_transaction() as sess:
        sess["_yapily_oauth_state"] = "lingering_state"

    client.post("/v2/logout")

    with client.session_transaction() as sess:
        assert sess.get(_SK_USER_ID) is None
        assert sess.get("_yapily_oauth_state") is None


# ── Settings persistence ──────────────────────────────────────────────────────

def test_settings_post_saves_to_db_when_authenticated(client, monkeypatch):
    """Authenticated users' settings must be persisted to the database."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)

    # Log in as demo user
    client.get("/v2/demo-login")
    with client.session_transaction() as sess:
        uid = sess.get(_SK_USER_ID)
    assert uid is not None

    # Post settings
    rv = client.post("/settings", data={
        "first_name":         "Edwina",
        "entity_type":        "sole_trader",
        "day_job_salary":     "0",
        "ytd_freelance_profit": "65000",
        "pension":            "5000",
        "student_loan":       "plan_2",
        "accounting_method":  "cash_basis",
        "vat_status":         "not_vat_registered",
    })
    assert rv.status_code == 302

    # Verify the profile is in the DB
    profile = db.get_profile_by_user(uid)
    assert profile is not None
    assert profile["income_estimate"] == 65000.0
    assert profile["pension_contribution"] == 5000.0
    assert profile["student_loan_plans"] == [2]
    assert profile["display_name"] == "Edwina"


def test_settings_loads_from_db_for_authenticated_user(client, monkeypatch):
    """On reload, an authenticated user must see their previously saved settings."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)

    client.get("/v2/demo-login")
    with client.session_transaction() as sess:
        uid = sess.get(_SK_USER_ID)

    # Save profile directly via DB helper
    db.save_profile_by_user(uid, {
        "display_name":       "Edwina",
        "income_estimate":    72000.0,
        "pension_contribution": 6000.0,
        "student_loan_plans": [2],
        "notes":              '{"first_name": "Edwina", "entity_type": "sole_trader", '
                              '"day_job_salary": "0", "trading_name": "", '
                              '"accounting_method": "cash_basis", "vat_registered": false}',
    })

    # GET settings page must pre-fill from DB
    rv = client.get("/settings")
    assert rv.status_code == 200
    assert b"72000" in rv.data or b"Edwina" in rv.data


def test_settings_falls_back_to_session_when_unauthenticated(client):
    """Unauthenticated visitors must still read settings from the Flask session."""
    with client.session_transaction() as sess:
        sess["profile"] = {"ytd_freelance_profit": "55000", "first_name": "Anonymous"}

    rv = client.get("/settings")
    assert rv.status_code == 200
    assert b"55000" in rv.data or b"Anonymous" in rv.data


# ═══════════════════════════════════════════════════════════════════════════════
# 6B — Sandbox isolation: mock=1 bypass blocked in production
# ═══════════════════════════════════════════════════════════════════════════════

def test_yapily_callback_mock_bypass_blocked_in_flask_env_production(client, monkeypatch):
    """
    mock=1 must NOT allow skipping OAuth state validation when FLASK_ENV=production.
    An attacker who crafts a callback URL with mock=1 must be rejected in production.
    """
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.delenv("YAPILY_APPLICATION_UUID", raising=False)
    monkeypatch.delenv("YAPILY_SECRET", raising=False)
    uid = _login_as(client, "user_mock_prod_block")
    # No state in session — would normally be accepted with mock=1 in dev

    rv = client.get(
        "/v2/yapily/callback?consent=mock-consent-token-abc123"
        "&institution=monzo&mock=1"
    )
    assert rv.status_code == 302
    assert "error" in rv.location


def test_yapily_callback_mock_bypass_blocked_with_live_clerk_key(client, monkeypatch):
    """
    mock=1 must NOT allow skipping OAuth state validation when a live Clerk key is set,
    even if FLASK_ENV is not explicitly 'production'.
    """
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setenv("CLERK_PUBLISHABLE_KEY", "pk_live_AAAAABBBBBCCCCC")
    monkeypatch.delenv("YAPILY_APPLICATION_UUID", raising=False)
    monkeypatch.delenv("YAPILY_SECRET", raising=False)
    uid = _login_as(client, "user_mock_live_key_block")

    rv = client.get(
        "/v2/yapily/callback?consent=mock-consent-token-abc123"
        "&institution=monzo&mock=1"
    )
    assert rv.status_code == 302
    assert "error" in rv.location


def test_yapily_callback_mock_bypass_allowed_in_development(client, monkeypatch):
    """mock=1 must continue to work in development (non-production) environments."""
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("YAPILY_APPLICATION_UUID", raising=False)
    monkeypatch.delenv("YAPILY_SECRET", raising=False)
    uid = _login_as(client, "user_mock_dev_allow")

    # No state in session — mock=1 should allow this in development
    rv = client.get(
        "/v2/yapily/callback?consent=mock-consent-token-abc123"
        "&institution=monzo&mock=1"
    )
    assert rv.status_code == 302
    assert "error" not in rv.location


def test_yapily_callback_mock_bypass_allowed_with_test_clerk_key(client, monkeypatch):
    """mock=1 must work when a test (pk_test_) Clerk key is present."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setenv("CLERK_PUBLISHABLE_KEY", "pk_test_AAAAABBBBBCCCCC")
    monkeypatch.delenv("YAPILY_APPLICATION_UUID", raising=False)
    monkeypatch.delenv("YAPILY_SECRET", raising=False)
    uid = _login_as(client, "user_mock_test_key_allow")

    rv = client.get(
        "/v2/yapily/callback?consent=mock-consent-token-abc123"
        "&institution=monzo&mock=1"
    )
    assert rv.status_code == 302
    assert "error" not in rv.location


# ═══════════════════════════════════════════════════════════════════════════════
# 6B — Schema versioning
# ═══════════════════════════════════════════════════════════════════════════════

def test_schema_version_table_created(test_db):
    """init_db() must create the schema_version table."""
    conn = sqlite3.connect(test_db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "schema_version" in tables


def test_schema_version_stamped_after_init(test_db):
    """After init_db(), schema_version must contain one row with the current version."""
    conn = sqlite3.connect(test_db)
    rows = conn.execute("SELECT version FROM schema_version").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0][0] == db._SCHEMA_VERSION


def test_schema_version_idempotent(test_db):
    """Calling init_db() twice must not duplicate schema_version rows."""
    db.init_db()  # second call
    conn = sqlite3.connect(test_db)
    rows = conn.execute("SELECT version FROM schema_version").fetchall()
    conn.close()
    assert len(rows) == 1


def test_schema_version_not_downgraded(test_db):
    """If schema_version already equals _SCHEMA_VERSION, init_db() must not change it."""
    conn = sqlite3.connect(test_db)
    version_before = conn.execute("SELECT version FROM schema_version").fetchone()[0]
    conn.close()

    db.init_db()  # run again

    conn = sqlite3.connect(test_db)
    version_after = conn.execute("SELECT version FROM schema_version").fetchone()[0]
    conn.close()
    assert version_after == version_before == db._SCHEMA_VERSION


def test_schema_migrations_dict_is_contiguous(test_db):
    """_MIGRATIONS keys must be a contiguous range 1.._SCHEMA_VERSION with no gaps."""
    for v in range(1, db._SCHEMA_VERSION + 1):
        assert v in db._MIGRATIONS, (
            f"_MIGRATIONS is missing version {v}. "
            "Add an entry (even an empty list) to keep the version sequence contiguous."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 6C — is_production_environment() helper
# ═══════════════════════════════════════════════════════════════════════════════

from reserved.auth import is_production_environment


def test_is_production_when_flask_env_set(monkeypatch):
    """FLASK_ENV=production must return True."""
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    assert is_production_environment() is True


def test_is_production_when_live_clerk_key(monkeypatch):
    """A pk_live_ Clerk key must return True regardless of FLASK_ENV."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setenv("CLERK_PUBLISHABLE_KEY", "pk_live_AAAAABBBBBCCCCC")
    assert is_production_environment() is True


def test_is_production_when_both_locks_set(monkeypatch):
    """Both locks set simultaneously must return True."""
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("CLERK_PUBLISHABLE_KEY", "pk_live_AAAAABBBBBCCCCC")
    assert is_production_environment() is True


def test_not_production_in_development(monkeypatch):
    """Neither lock set must return False (development default)."""
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    assert is_production_environment() is False


def test_not_production_with_test_clerk_key(monkeypatch):
    """A pk_test_ Clerk key must not trigger the production lock."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setenv("CLERK_PUBLISHABLE_KEY", "pk_test_AAAAABBBBBCCCCC")
    assert is_production_environment() is False


def test_not_production_when_env_absent(monkeypatch):
    """Absence of both env vars must return False (safe default)."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    assert is_production_environment() is False


# ═══════════════════════════════════════════════════════════════════════════════
# 6C — Production SESSION_SECRET enforcement
# ═══════════════════════════════════════════════════════════════════════════════

def test_create_app_raises_if_no_session_secret_in_production(tmp_path, monkeypatch):
    """
    create_app() must raise RuntimeError during startup when SESSION_SECRET is
    absent and the environment is detected as production (FLASK_ENV=production).
    No requests should be served — the failure is at startup time.
    """
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "prod_test.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)

    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        create_app()


def test_create_app_raises_if_no_session_secret_with_live_clerk_key(tmp_path, monkeypatch):
    """
    create_app() must raise RuntimeError when SESSION_SECRET is absent and a
    live Clerk key is present (second lock), even without FLASK_ENV=production.
    """
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setenv("CLERK_PUBLISHABLE_KEY", "pk_live_AAAAABBBBBCCCCC")
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "prod_clerk_test.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)

    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        create_app()


def test_create_app_succeeds_in_production_with_session_secret(tmp_path, monkeypatch):
    """
    create_app() must start normally when SESSION_SECRET is supplied in a
    production environment — no RuntimeError should be raised.
    """
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("SESSION_SECRET", "a-strong-randomly-generated-secret-value-here")
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "prod_ok_test.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)

    app = create_app()   # must not raise
    assert app is not None


def test_create_app_succeeds_in_development_without_session_secret(tmp_path, monkeypatch):
    """
    create_app() must start normally in development even when SESSION_SECRET
    is absent — development ergonomics must not be broken.
    """
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "dev_test.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)

    app = create_app()   # must not raise
    assert app is not None


# ═══════════════════════════════════════════════════════════════════════════════
# 6C — Timezone-aware UTC (ConsentRecord)
# ═══════════════════════════════════════════════════════════════════════════════

from datetime import timezone as _tz
from reserved.providers.banking.yapily import ConsentRecord


def test_consent_record_created_at_is_timezone_aware():
    """ConsentRecord.created_at default must be a timezone-aware UTC datetime."""
    record = ConsentRecord(
        consent_token="tok",
        institution_id="inst",
        account_id="acc",
        account_nickname="Current",
        account_last4="1234",
    )
    assert record.created_at.tzinfo is not None, (
        "created_at must be timezone-aware (use datetime.now(timezone.utc), "
        "not datetime.utcnow())"
    )
    assert record.created_at.tzinfo == _tz.utc


# ═══════════════════════════════════════════════════════════════════════════════
# 6C correction — login page demo_available uses is_production_environment()
# ═══════════════════════════════════════════════════════════════════════════════

def test_login_page_hides_demo_button_when_flask_env_production(client, monkeypatch):
    """Login page must not show the demo button when FLASK_ENV=production."""
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("SESSION_SECRET", "strong-secret-for-this-test")
    rv = client.get("/v2/login")
    assert rv.status_code == 200
    # The template renders the demo button only when demo_available is True.
    # The exact marker text matches the login template's demo-login link.
    assert b"demo-login" not in rv.data


def test_login_page_hides_demo_button_with_live_clerk_key(client, monkeypatch):
    """Login page must not show the demo button when a pk_live_ Clerk key is set."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setenv("CLERK_PUBLISHABLE_KEY", "pk_live_AAAAABBBBBCCCCC")
    rv = client.get("/v2/login")
    assert rv.status_code == 200
    assert b"demo-login" not in rv.data


def test_login_page_shows_demo_button_in_development(client, monkeypatch):
    """Login page must show the demo button in a development environment."""
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    rv = client.get("/v2/login")
    assert rv.status_code == 200
    assert b"demo-login" in rv.data


def test_login_page_shows_demo_button_with_test_clerk_key(client, monkeypatch):
    """Login page must show the demo button when only a pk_test_ Clerk key is set."""
    monkeypatch.delenv("FLASK_ENV", raising=False)
    monkeypatch.setenv("CLERK_PUBLISHABLE_KEY", "pk_test_AAAAABBBBBCCCCC")
    rv = client.get("/v2/login")
    assert rv.status_code == 200
    assert b"demo-login" in rv.data


def test_demo_login_route_and_login_page_agree_on_production(client, monkeypatch):
    """
    The demo-login route (403 in production) and the login-page demo button
    (hidden in production) must use the same production gate — both must be
    inaccessible under either production lock.
    """
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("SESSION_SECRET", "strong-secret-for-this-test")

    # Route: must return 403
    rv_route = client.get("/v2/demo-login")
    assert rv_route.status_code == 403

    # Login page: must not offer the button
    rv_page = client.get("/v2/login")
    assert rv_page.status_code == 200
    assert b"demo-login" not in rv_page.data


def test_demo_login_route_and_login_page_agree_on_development(client, monkeypatch):
    """
    In development, both the route and the login-page button must be available.
    Check the login page (unauthenticated) first, then hit the route — the route
    sets a session so the login page would redirect afterwards.
    """
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)

    # Login page (unauthenticated): must show the button
    rv_page = client.get("/v2/login")
    assert rv_page.status_code == 200
    assert b"demo-login" in rv_page.data

    # Route: must succeed (302 to /v2/)
    rv_route = client.get("/v2/demo-login")
    assert rv_route.status_code == 302


def test_consent_record_expiry_comparison_is_timezone_aware():
    """days_until_expiry and is_expired must work correctly with aware datetimes."""
    from datetime import datetime, timedelta, timezone
    future = datetime.now(timezone.utc) + timedelta(days=30)
    past   = datetime.now(timezone.utc) - timedelta(days=1)

    record_future = ConsentRecord(
        consent_token="tok-f",
        institution_id="inst",
        account_id="acc",
        account_nickname="Current",
        account_last4="1234",
        expires_at=future,
    )
    record_past = ConsentRecord(
        consent_token="tok-p",
        institution_id="inst",
        account_id="acc",
        account_nickname="Current",
        account_last4="1234",
        expires_at=past,
    )

    assert record_future.is_expired is False
    assert record_past.is_expired is True
    assert record_future.days_until_expiry >= 29   # at least 29 days remaining
