"""
Tests for Workstream 4 — Database Persistence.

All tests run against an isolated temporary SQLite file; the production
instance/reserved.db is never touched.

Covers:
- init_db() creates all WS4 tables
- bank_connections CRUD
- connected_accounts CRUD
- transactions: save, upsert, get, summary, category filter
- transaction_overrides: save, get, category updated on transaction row
- user_profiles: save, get, update, student_loan_plans JSON round-trip
- cascade delete: deleting a connection removes accounts and transactions
- ingestion.persist_transactions() converts ClassifiedTransaction → DB rows
- ingestion.seed_demo_data() is idempotent
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

import reserved.database as db
from reserved.providers.banking.ingestion import (
    get_demo_transactions,
    persist_transactions,
    seed_demo_data,
)


# ── Test DB fixture ────────────────────────────────────────────────────────────

@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Patch database module to use a fresh temp file for each test."""
    test_file = tmp_path / "test_reserved.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    db.init_db()
    return test_file


# ── init_db() ─────────────────────────────────────────────────────────────────

def test_init_db_creates_all_tables(test_db):
    conn = sqlite3.connect(test_db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    expected = {
        "feedback_submissions",
        "early_access_registrations",
        "bank_connections",
        "connected_accounts",
        "transactions",
        "transaction_overrides",
        "user_profiles",
        "tax_calculations",
        "invoice_sources",
    }
    assert expected.issubset(tables), f"Missing tables: {expected - tables}"


def test_init_db_is_idempotent(test_db):
    """Calling init_db() twice should not raise."""
    db.init_db()  # second call
    db.init_db()  # third call


# ── bank_connections ──────────────────────────────────────────────────────────

def test_save_and_get_connection(test_db):
    cid = db.save_connection(
        institution_id="monzo",
        institution_name="Monzo",
        consent_token="tok-001",
        expires_at="2026-12-31T00:00:00+00:00",
        session_key="sess-abc",
    )
    assert isinstance(cid, int) and cid > 0
    record = db.get_connection_by_token("tok-001")
    assert record is not None
    assert record["institution_id"] == "monzo"
    assert record["status"] == "active"
    assert record["session_key"] == "sess-abc"


def test_get_connection_returns_none_for_missing(test_db):
    assert db.get_connection_by_token("does-not-exist") is None


def test_list_active_connections_filters_by_session(test_db):
    db.save_connection("monzo", "Monzo", "tok-a", session_key="sess-1")
    db.save_connection("starling", "Starling", "tok-b", session_key="sess-2")
    results = db.list_active_connections(session_key="sess-1")
    assert len(results) == 1
    assert results[0]["consent_token"] == "tok-a"


def test_list_active_connections_excludes_revoked(test_db):
    db.save_connection("monzo", "Monzo", "tok-live", session_key="s1")
    db.save_connection("starling", "Starling", "tok-dead", session_key="s1")
    db.update_connection_status("tok-dead", "revoked")
    results = db.list_active_connections(session_key="s1")
    tokens = [r["consent_token"] for r in results]
    assert "tok-live" in tokens
    assert "tok-dead" not in tokens


def test_update_connection_status(test_db):
    db.save_connection("monzo", "Monzo", "tok-upd")
    db.update_connection_status("tok-upd", "expiring")
    record = db.get_connection_by_token("tok-upd")
    assert record["status"] == "expiring"


def test_delete_connection(test_db):
    db.save_connection("monzo", "Monzo", "tok-del")
    db.delete_connection("tok-del")
    assert db.get_connection_by_token("tok-del") is None


# ── connected_accounts ────────────────────────────────────────────────────────

def test_save_and_get_account(test_db):
    cid = db.save_connection("monzo", "Monzo", "tok-acct")
    aid = db.save_account(
        connection_id=cid,
        yapily_account_id="yap-acc-001",
        account_type="CURRENT",
        nickname="Main account",
        currency="GBP",
        sort_code="040004",
        account_number="12345678",
        balance=4821.55,
        balance_at="2026-08-05T10:00:00+00:00",
    )
    assert isinstance(aid, int) and aid > 0
    acc = db.get_account("yap-acc-001")
    assert acc is not None
    assert acc["nickname"] == "Main account"
    assert acc["balance"] == pytest.approx(4821.55)


def test_get_account_returns_none_for_missing(test_db):
    assert db.get_account("not-here") is None


def test_list_accounts(test_db):
    cid = db.save_connection("monzo", "Monzo", "tok-list-acc")
    db.save_account(cid, "acc-001", nickname="Current")
    db.save_account(cid, "acc-002", nickname="Savings")
    accounts = db.list_accounts(cid)
    assert len(accounts) == 2
    nicknames = {a["nickname"] for a in accounts}
    assert nicknames == {"Current", "Savings"}


def test_update_account_balance(test_db):
    cid = db.save_connection("monzo", "Monzo", "tok-bal")
    db.save_account(cid, "acc-bal", balance=100.0, balance_at="2026-01-01T00:00:00+00:00")
    db.update_account_balance("acc-bal", 250.0, "2026-08-05T12:00:00+00:00")
    acc = db.get_account("acc-bal")
    assert acc["balance"] == pytest.approx(250.0)
    assert acc["balance_at"] == "2026-08-05T12:00:00+00:00"


# ── transactions ──────────────────────────────────────────────────────────────

def _make_tx_row(tx_id: str, amount: float, category: str) -> dict:
    return {
        "yapily_tx_id": tx_id,
        "tx_date": "2026-07-01",
        "description": f"Test tx {tx_id}",
        "amount": amount,
        "currency": "GBP",
        "category": category,
        "confidence": 0.90,
        "method": "rules",
        "subcategory": None,
        "tax_relevant": category in ("freelance_income", "tax_payment"),
        "raw_json": json.dumps({"id": tx_id}),
    }


def test_save_and_get_transactions(test_db):
    cid = db.save_connection("monzo", "Monzo", "tok-txn")
    aid = db.save_account(cid, "acc-txn")
    rows = [
        _make_tx_row("t1", 1000.0, "freelance_income"),
        _make_tx_row("t2", -500.0, "tax_payment"),
    ]
    count = db.save_transactions(aid, rows)
    assert count == 2
    stored = db.get_transactions(aid)
    assert len(stored) == 2


def test_save_transactions_upserts_on_conflict(test_db):
    cid = db.save_connection("monzo", "Monzo", "tok-upsert")
    aid = db.save_account(cid, "acc-upsert")
    row = _make_tx_row("dup-001", 1000.0, "freelance_income")
    db.save_transactions(aid, [row])
    # Re-save with updated category (manual override scenario)
    row["category"] = "salary"
    db.save_transactions(aid, [row])
    stored = db.get_transactions(aid)
    # Should still be 1 row, not 2
    assert len(stored) == 1
    assert stored[0]["category"] == "salary"


def test_get_transactions_filtered_by_category(test_db):
    cid = db.save_connection("monzo", "Monzo", "tok-filter")
    aid = db.save_account(cid, "acc-filter")
    db.save_transactions(aid, [
        _make_tx_row("f1", 1000.0, "freelance_income"),
        _make_tx_row("f2", -54.0, "subscription"),
        _make_tx_row("f3", -68.0, "utility"),
    ])
    subscriptions = db.get_transactions(aid, category="subscription")
    assert len(subscriptions) == 1
    assert subscriptions[0]["yapily_tx_id"] == "f2"


def test_get_transaction_summary(test_db):
    cid = db.save_connection("monzo", "Monzo", "tok-summary")
    aid = db.save_account(cid, "acc-summary")
    db.save_transactions(aid, [
        _make_tx_row("s1", 3200.0, "freelance_income"),
        _make_tx_row("s2", 1800.0, "freelance_income"),
        _make_tx_row("s3", -2840.0, "tax_payment"),
        _make_tx_row("s4", -54.99, "subscription"),
        _make_tx_row("s5", -45.0, "unknown"),
    ])
    summary = db.get_transaction_summary(aid)
    assert summary["total_income"] == pytest.approx(5000.0)
    assert summary["total_tax_payments"] == pytest.approx(2840.0)
    assert summary["total_expenses"] == pytest.approx(54.99)
    assert summary["unclassified_count"] == 1
    assert summary["transaction_count"] == 5


def test_get_transaction_summary_empty_account(test_db):
    cid = db.save_connection("monzo", "Monzo", "tok-empty-sum")
    aid = db.save_account(cid, "acc-empty-sum")
    summary = db.get_transaction_summary(aid)
    assert summary["total_income"] == 0
    assert summary["transaction_count"] == 0


# ── transaction_overrides ─────────────────────────────────────────────────────

def test_save_override_and_updates_transaction(test_db):
    cid = db.save_connection("monzo", "Monzo", "tok-override")
    aid = db.save_account(cid, "acc-override")
    db.save_transactions(aid, [_make_tx_row("ov1", -349.0, "personal_spending")])

    tx_row = db.get_transactions(aid)[0]
    tx_id = tx_row["id"]

    db.save_override(tx_id, "personal_spending", "business_expense", note="iPad for studio")

    # Transaction row should now reflect the override
    updated = db.get_transactions(aid)[0]
    assert updated["category"] == "business_expense"
    assert updated["method"] == "manual"
    assert updated["confidence"] == pytest.approx(1.0)


def test_get_overrides(test_db):
    cid = db.save_connection("monzo", "Monzo", "tok-get-ov")
    aid = db.save_account(cid, "acc-get-ov")
    db.save_transactions(aid, [_make_tx_row("ov2", -12.0, "personal_spending")])
    tx_id = db.get_transactions(aid)[0]["id"]

    db.save_override(tx_id, "personal_spending", "subscription", note="First correction")
    db.save_override(tx_id, "subscription", "business_expense", note="Second correction")

    overrides = db.get_overrides(tx_id)
    assert len(overrides) == 2
    assert overrides[0]["new_category"] == "subscription"
    assert overrides[1]["new_category"] == "business_expense"
    assert overrides[0]["note"] == "First correction"


# ── user_profiles ─────────────────────────────────────────────────────────────

def test_save_and_get_profile(test_db):
    db.save_profile("sess-001", {
        "display_name": "Edwina",
        "tax_year": "2026/27",
        "income_estimate": 45000.0,
        "pension_contribution": 3000.0,
        "student_loan_plans": ["plan2"],
    })
    profile = db.get_profile("sess-001")
    assert profile is not None
    assert profile["display_name"] == "Edwina"
    assert profile["income_estimate"] == pytest.approx(45000.0)
    assert profile["student_loan_plans"] == ["plan2"]


def test_get_profile_returns_none_for_missing(test_db):
    assert db.get_profile("no-such-session") is None


def test_save_profile_updates_on_conflict(test_db):
    db.save_profile("sess-upd", {"display_name": "Initial", "income_estimate": 30000.0})
    db.save_profile("sess-upd", {"display_name": "Updated", "income_estimate": 45000.0})
    profile = db.get_profile("sess-upd")
    assert profile["display_name"] == "Updated"
    assert profile["income_estimate"] == pytest.approx(45000.0)


def test_save_profile_student_loan_plans_json_roundtrip(test_db):
    plans = ["plan1", "plan2", "postgraduate"]
    db.save_profile("sess-plans", {"student_loan_plans": plans})
    profile = db.get_profile("sess-plans")
    assert profile["student_loan_plans"] == plans


# ── CASCADE deletes ───────────────────────────────────────────────────────────

def test_delete_connection_cascades_to_accounts_and_transactions(test_db):
    cid = db.save_connection("monzo", "Monzo", "tok-cascade")
    aid = db.save_account(cid, "acc-cascade")
    db.save_transactions(aid, [_make_tx_row("c1", 1000.0, "freelance_income")])

    db.delete_connection("tok-cascade")

    assert db.get_account("acc-cascade") is None
    assert db.get_transactions(aid) == []


# ── ingestion.persist_transactions() ─────────────────────────────────────────

def test_persist_transactions_writes_to_db(test_db):
    cid = db.save_connection("monzo", "Monzo", "tok-persist")
    aid = db.save_account(cid, "acc-persist")
    classified = get_demo_transactions()
    count = persist_transactions(aid, classified)
    assert count == len(classified)
    stored = db.get_transactions(aid)
    assert len(stored) == len(classified)


def test_persist_transactions_is_idempotent(test_db):
    cid = db.save_connection("monzo", "Monzo", "tok-idem")
    aid = db.save_account(cid, "acc-idem")
    classified = get_demo_transactions()
    persist_transactions(aid, classified)
    persist_transactions(aid, classified)  # second call
    stored = db.get_transactions(aid)
    assert len(stored) == len(classified)  # no duplicates


def test_persist_transactions_preserves_category(test_db):
    cid = db.save_connection("monzo", "Monzo", "tok-cat")
    aid = db.save_account(cid, "acc-cat")
    classified = get_demo_transactions()
    persist_transactions(aid, classified)
    stored = {r["yapily_tx_id"]: r for r in db.get_transactions(aid)}
    for ct in classified:
        assert stored[ct.id]["category"] == ct.classification.category.value


# ── ingestion.seed_demo_data() ────────────────────────────────────────────────

def test_seed_demo_data_returns_expected_keys(test_db):
    result = seed_demo_data()
    assert "connection_id" in result
    assert "account_id" in result
    assert "tx_count" in result
    assert isinstance(result["connection_id"], int)
    assert isinstance(result["account_id"], int)
    assert result["tx_count"] > 0


def test_seed_demo_data_is_idempotent(test_db):
    result1 = seed_demo_data()
    result2 = seed_demo_data()
    # Same IDs on second call
    assert result1["connection_id"] == result2["connection_id"]
    assert result1["account_id"] == result2["account_id"]
    # Transaction count same (upsert, no duplicates)
    stored_after_two = db.get_transactions(result1["account_id"])
    assert len(stored_after_two) == result1["tx_count"]


def test_seed_demo_data_creates_monzo_connection(test_db):
    seed_demo_data()
    connections = db.list_active_connections(session_key="demo")
    assert len(connections) == 1
    assert connections[0]["institution_id"] == "monzo"


def test_seed_demo_data_creates_account_with_balance(test_db):
    result = seed_demo_data()
    accounts = db.list_accounts(result["connection_id"])
    assert len(accounts) == 1
    assert accounts[0]["balance"] == pytest.approx(4821.55)


def test_seed_demo_summary_totals_are_positive(test_db):
    result = seed_demo_data()
    summary = db.get_transaction_summary(result["account_id"])
    assert summary["total_income"] > 0
    assert summary["transaction_count"] > 0
