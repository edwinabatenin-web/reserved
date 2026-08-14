"""
Workstream 6 — Tests for the invoice matching engine and persistence layer.

Covers:
- Invoice dataclass construction and Decimal coercion
- All five single-transaction matching rules (confidence 100 → 60)
- Aggregate rules: MULTIPLE_PAYMENTS, PARTIAL_PAYMENT, OVERPAID, UNDERPAID (6A)
- MULTIPLE_MATCHES when two transactions independently match
- UNMATCHED when no candidate is found
- Currency validation (6A): mismatched currency → UNMATCHED
- Reference normalisation (dash-insensitive, case-insensitive)
- Amount tolerance boundaries
- Date-proximity boundaries
- match_all() — one result per invoice
- Database: invoices CRUD (save, get_by_reference, get, list, update_status)
- Database: invoice_matches CRUD (save_match, get_matches_for_invoice, update_review_state)
- Database: persist_match_result() for all status types
- Demo data: DEMO_INVOICES cover all 9 statuses (incl. UNDERPAID from 6A)
- Demo data: seed_demo_invoices() idempotency
- Demo data: run_demo_matching() produces expected scenario statuses
- Existing 401 tests must continue to pass (no regressions)
"""

from __future__ import annotations

import sqlite3
from decimal import Decimal

import pytest

import reserved.database as db
from reserved.matching.engine import (
    Invoice,
    MatchResult,
    MatchStatus,
    MatchingEngine,
    ReviewState,
    _currencies_compatible,
    _currency_check,
)
from reserved.matching.demo_invoices import (
    DEMO_INVOICES,
    DEMO_EXTRA_TRANSACTIONS,
    get_demo_transactions_for_matching,
    run_demo_matching,
    seed_demo_invoices,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Isolated temp SQLite file for each test; never touches instance/reserved.db."""
    test_file = tmp_path / "test_matching.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    db.init_db()
    return test_file


@pytest.fixture
def engine():
    return MatchingEngine()


# ── Sample invoices ───────────────────────────────────────────────────────────

def _inv(
    reference="INV-2026-001",
    client_name="Test Client",
    amount_due="1000.00",
    issue_date="2026-06-01",
    due_date="2026-06-30",
    **kwargs,
) -> Invoice:
    return Invoice(
        reference=reference,
        client_name=client_name,
        amount_due=Decimal(amount_due),
        issue_date=issue_date,
        due_date=due_date,
        **kwargs,
    )


def _tx(
    id=1,
    tx_date="2026-06-30",
    description="Test payment",
    amount="1000.00",
    info="",
    yapily_tx_id="txn-test",
    currency="GBP",
) -> dict:
    return {
        "id": id,
        "tx_date": tx_date,
        "description": description,
        "transactionInformation": info,
        "amount": float(amount),
        "currency": currency,
        "yapily_tx_id": yapily_tx_id,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Invoice dataclass
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvoiceDataclass:
    def test_amount_due_is_decimal(self):
        inv = _inv(amount_due="1500.75")
        assert isinstance(inv.amount_due, Decimal)

    def test_amount_due_coerced_from_float(self):
        inv = Invoice(
            reference="INV-X", client_name="X",
            amount_due=1200.50, issue_date="2026-01-01", due_date="2026-01-31",
        )
        assert isinstance(inv.amount_due, Decimal)
        assert inv.amount_due == Decimal("1200.5")

    def test_defaults(self):
        inv = _inv()
        assert inv.currency == "GBP"
        assert inv.status == "unpaid"
        assert inv.notes is None
        assert inv.id is None
        assert inv.user_id is None

    def test_optional_fields(self):
        inv = _inv(notes="Test note", id=42, user_id=7)
        assert inv.notes == "Test note"
        assert inv.id == 42
        assert inv.user_id == 7


# ═══════════════════════════════════════════════════════════════════════════════
# Single-transaction rules
# ═══════════════════════════════════════════════════════════════════════════════

class TestExactAmountAndReference:
    """Rule 1: 100% · MATCHED — exact amount AND reference in text."""

    def test_exact_match(self, engine):
        inv = _inv(reference="INV-2026-047", amount_due="3200.00")
        tx = _tx(
            description="INV-2026-047 STUDIO CLIENT LTD",
            amount="3200.00",
        )
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.MATCHED
        assert r.confidence == 100
        assert r.method == "exact_amount_and_reference"
        assert "INV-2026-047" in r.explanation
        assert r.matched_amount == Decimal("3200.00")

    def test_reference_in_transaction_information(self, engine):
        """Reference in transactionInformation field, not description."""
        inv = _inv(reference="INV-2026-039", amount_due="4500.00")
        tx = _tx(
            description="MERIDIAN GROUP CONSULTING FEE",
            info="INV-2026-039 design consultancy",
            amount="4500.00",
        )
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.MATCHED
        assert r.confidence == 100

    def test_case_insensitive(self, engine):
        inv = _inv(reference="INV-2026-001", amount_due="500.00")
        tx = _tx(description="inv-2026-001 payment", amount="500.00")
        r = engine.match(inv, [tx])
        assert r.confidence == 100

    def test_wrong_amount_does_not_match(self, engine):
        inv = _inv(reference="INV-2026-001", amount_due="1000.00")
        tx = _tx(description="INV-2026-001 payment", amount="999.00")
        r = engine.match(inv, [tx])
        # Amount not exact — should fall through to a lower rule
        assert r.confidence < 100

    def test_transaction_id_captured(self, engine):
        inv = _inv(reference="INV-2026-001", amount_due="500.00")
        tx = _tx(id=42, description="INV-2026-001 payment", amount="500.00")
        r = engine.match(inv, [tx])
        assert 42 in r.transaction_ids


class TestReferenceAndCloseAmount:
    """Rule 2: 95% · MATCHED — reference found AND amount within 0.5%."""

    def test_fires_when_amount_slightly_off(self, engine):
        """£1000 invoice, £1004.99 received (0.499% diff) → 95%."""
        inv = _inv(reference="INV-001", amount_due="1000.00")
        tx = _tx(description="INV-001 payment", amount="1004.99")
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.MATCHED
        assert r.confidence == 95
        assert r.method == "reference_and_close_amount"

    def test_does_not_fire_when_amount_too_far(self, engine):
        """0.6% diff — outside 0.5% tolerance, so reference_and_close_amount does NOT fire.
        Since the reference matches and amount (£1,006) > invoice (£1,000), OVERPAID fires
        at the aggregate stage (90%), which is the correct, more informative result."""
        inv = _inv(reference="INV-001", amount_due="1000.00", due_date="2026-06-30")
        tx = _tx(description="INV-001 payment", amount="1006.00", tx_date="2026-07-10")
        r = engine.match(inv, [tx])
        # reference_and_close_amount (95%) must NOT fire for 0.6% diff
        assert r.method != "reference_and_close_amount"
        # Correct result: OVERPAID — reference matched, £6 excess received
        assert r.status == MatchStatus.OVERPAID
        assert r.confidence == 90

    def test_amount_boundary_exactly_05pct(self, engine):
        """Exactly 0.5% over — should still match at 95%."""
        inv = _inv(reference="INV-001", amount_due="1000.00")
        tx = _tx(description="INV-001 payment", amount="1005.00")
        r = engine.match(inv, [tx])
        assert r.confidence == 95


class TestExactAmountAndDate:
    """Rule 3: 85% · LIKELY_MATCH — exact amount AND within 7 days of due date."""

    def test_fires_within_7_days(self, engine):
        inv = _inv(amount_due="2850.00", due_date="2026-07-28")
        tx = _tx(description="BACS TRANSFER", amount="2850.00", tx_date="2026-07-31")
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.LIKELY_MATCH
        assert r.confidence == 85
        assert r.method == "exact_amount_and_date"

    def test_fires_on_due_date(self, engine):
        inv = _inv(amount_due="1500.00", due_date="2026-06-15")
        tx = _tx(description="Transfer", amount="1500.00", tx_date="2026-06-15")
        r = engine.match(inv, [tx])
        assert r.confidence == 85

    def test_does_not_fire_8_days_late(self, engine):
        """8 days after due date — beyond the 7-day window."""
        inv = _inv(amount_due="1500.00", due_date="2026-06-15")
        tx = _tx(description="Transfer", amount="1500.00", tx_date="2026-06-23")
        r = engine.match(inv, [tx])
        assert r.confidence < 85

    def test_fires_before_due_date(self, engine):
        """Payment received 5 days early — still within window."""
        inv = _inv(amount_due="1000.00", due_date="2026-06-30")
        tx = _tx(description="Early payment", amount="1000.00", tx_date="2026-06-25")
        r = engine.match(inv, [tx])
        assert r.confidence == 85


class TestCloseAmountAndDate:
    """Rule 4: 74% · LIKELY_MATCH — amount within 2% AND within 2 days of due date."""

    def test_fires_within_1pct_and_1_day(self, engine):
        """£2850 invoice, £2822 received (0.98% diff), 1 day early."""
        inv = _inv(amount_due="2850.00", due_date="2026-07-31")
        tx = _tx(description="FASTER PAYMENT", amount="2822.00", tx_date="2026-07-30")
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.LIKELY_MATCH
        assert r.confidence == 74
        assert r.method == "close_amount_and_date"

    def test_does_not_fire_3_days_off(self, engine):
        """3 days off — beyond the 2-day window."""
        inv = _inv(amount_due="1000.00", due_date="2026-06-30")
        tx = _tx(description="Payment", amount="1010.00", tx_date="2026-07-03")
        r = engine.match(inv, [tx])
        assert r.confidence < 74

    def test_does_not_fire_when_amount_too_far(self, engine):
        """3% diff — beyond the 2% tolerance."""
        inv = _inv(amount_due="1000.00", due_date="2026-06-30")
        tx = _tx(description="Payment", amount="1031.00", tx_date="2026-06-30")
        r = engine.match(inv, [tx])
        assert r.confidence < 74

    def test_boundary_exactly_2pct(self, engine):
        """Exactly 2% over, on the due date — should match at 74%."""
        inv = _inv(amount_due="1000.00", due_date="2026-06-30")
        tx = _tx(description="Payment", amount="1020.00", tx_date="2026-06-30")
        r = engine.match(inv, [tx])
        assert r.confidence == 74


class TestReferenceMatching:
    """
    Tests for reference-based matching paths.

    The reference_only rule (60%) feeds into the candidate pool, but aggregate
    rules always supersede it when a reference match exists:
      - amount < invoice  → PARTIAL_PAYMENT (80%)
      - amount > invoice  → OVERPAID (90%)
      - amount == invoice → MATCHED via exact_amount_and_reference (100%)

    These tests verify the end-to-end outcomes through the engine.
    """

    def test_reference_partial_amount_triggers_partial_payment(self, engine):
        """Reference matches, amount received < invoiced → PARTIAL_PAYMENT."""
        inv = _inv(reference="INV-001", amount_due="1000.00", due_date="2026-06-30")
        tx = _tx(description="INV-001 payment", amount="600.00", tx_date="2026-07-10")
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.PARTIAL_PAYMENT
        assert r.confidence == 80
        assert "INV-001" in r.explanation

    def test_reference_excess_amount_triggers_overpaid(self, engine):
        """Reference matches, amount received > invoiced → OVERPAID."""
        inv = _inv(reference="INV-001", amount_due="1000.00", due_date="2026-06-30")
        tx = _tx(description="INV-001 payment", amount="1050.00", tx_date="2026-07-10")
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.OVERPAID
        assert r.confidence == 90
        assert "INV-001" in r.explanation

    def test_reference_tiny_amount_triggers_partial_payment(self, engine):
        """Even a £50 deposit on a £1,000 invoice with reference is a PARTIAL_PAYMENT."""
        inv = _inv(reference="INV-001", amount_due="1000.00", due_date="2026-06-30")
        tx = _tx(description="INV-001 deposit", amount="50.00", tx_date="2026-07-10")
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.PARTIAL_PAYMENT

    def test_unmatched_when_no_reference_and_amount_tiny(self, engine):
        """No reference match AND small unrelated amount → UNMATCHED."""
        inv = _inv(reference="INV-001", amount_due="1000.00")
        tx = _tx(description="GROCERIES TESCO", amount="50.00", tx_date="2026-01-01")
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.UNMATCHED

    def test_dash_insensitive_reference_partial(self, engine):
        """INV2026001 in description matches reference INV-2026-001 (dash-insensitive)."""
        inv = _inv(reference="INV-2026-001", amount_due="1000.00", due_date="2026-06-30")
        tx = _tx(description="INV2026001 payment", amount="600.00", tx_date="2026-07-10")
        r = engine.match(inv, [tx])
        # Reference must be detected despite no dashes in the transaction text
        assert r.status != MatchStatus.UNMATCHED
        assert "INV-2026-001" in r.explanation

    def test_case_insensitive_reference(self, engine):
        """inv-001 in description matches reference INV-001 (case-insensitive)."""
        inv = _inv(reference="INV-001", amount_due="1000.00")
        tx = _tx(description="inv-001 payment", amount="900.00")
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.PARTIAL_PAYMENT

    def test_explanation_mentions_reference(self, engine):
        inv = _inv(reference="INV-X42", amount_due="500.00")
        tx = _tx(description="INV-X42 partial", amount="250.00")
        r = engine.match(inv, [tx])
        assert "INV-X42" in r.explanation


# ═══════════════════════════════════════════════════════════════════════════════
# Aggregate rules
# ═══════════════════════════════════════════════════════════════════════════════

class TestMultiplePayments:
    """90% · MULTIPLE_PAYMENTS — two or more transactions sum to invoice amount."""

    def test_two_equal_payments(self, engine):
        inv = _inv(reference="INV-044", amount_due="3000.00")
        txs = [
            _tx(id=1, description="INV-044 MILESTONE 1", amount="1500.00",
                tx_date="2026-06-15", yapily_tx_id="tx-1"),
            _tx(id=2, description="INV-044 MILESTONE 2", amount="1500.00",
                tx_date="2026-06-28", yapily_tx_id="tx-2"),
        ]
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.MULTIPLE_PAYMENTS
        assert r.confidence == 90
        assert r.method == "multiple_payments"
        assert 1 in r.transaction_ids
        assert 2 in r.transaction_ids
        assert r.matched_amount == Decimal("3000.00")

    def test_three_payments(self, engine):
        """All three payments must reference the invoice (engine rule: ALL must match)."""
        inv = _inv(reference="INV-050", amount_due="1500.00")
        txs = [
            _tx(id=1, description="INV-050 instalment 1", amount="500.00", tx_date="2026-05-01"),
            _tx(id=2, description="INV-050 instalment 2", amount="500.00", tx_date="2026-05-15"),
            _tx(id=3, description="INV-050 instalment 3", amount="500.00", tx_date="2026-05-30"),
        ]
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.MULTIPLE_PAYMENTS
        assert len(r.transaction_ids) == 3

    def test_within_1pct_tolerance(self, engine):
        """Three payments summing to £2970 against £3000 invoice — within 1%."""
        inv = _inv(reference="INV-TOL", amount_due="3000.00")
        txs = [
            _tx(id=1, description="INV-TOL pmt 1", amount="990.00", tx_date="2026-06-01"),
            _tx(id=2, description="INV-TOL pmt 2", amount="990.00", tx_date="2026-06-15"),
            _tx(id=3, description="INV-TOL pmt 3", amount="990.00", tx_date="2026-06-28"),
        ]
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.MULTIPLE_PAYMENTS

    def test_does_not_fire_when_single_tx_matches(self, engine):
        """If one transaction already matches at 100%, don't escalate to multi."""
        inv = _inv(reference="INV-001", amount_due="2000.00")
        txs = [
            _tx(id=1, description="INV-001 payment", amount="2000.00"),
            _tx(id=2, description="another payment", amount="1000.00"),
            _tx(id=3, description="another payment", amount="1000.00"),
        ]
        r = engine.match(inv, txs)
        assert r.confidence == 100
        assert len(r.transaction_ids) == 1


class TestPartialPayment:
    """80% · PARTIAL_PAYMENT — reference matched, partial amount received."""

    def test_partial_payment(self, engine):
        inv = _inv(reference="INV-055", amount_due="2000.00")
        tx = _tx(
            id=5,
            description="VERTEX MEDIA INV-055 DEPOSIT",
            amount="500.00",
            tx_date="2026-07-22",
        )
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.PARTIAL_PAYMENT
        assert r.confidence == 80
        assert r.method == "partial_payment"
        assert r.matched_amount == Decimal("500.00")
        assert "500.00" in r.explanation or "£500.00" in r.explanation
        assert "outstanding" in r.explanation.lower() or "remaining" in r.explanation.lower()

    def test_partial_percentage_in_explanation(self, engine):
        """50% partial payment: explanation should mention the percentage."""
        inv = _inv(reference="INV-060", amount_due="2000.00")
        tx = _tx(description="INV-060 half payment", amount="1000.00")
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.PARTIAL_PAYMENT
        assert "50%" in r.explanation


class TestOverpaid:
    """90% · OVERPAID — reference matched, total received > invoice amount."""

    def test_overpaid(self, engine):
        inv = _inv(reference="INV-041", amount_due="1000.00")
        tx = _tx(
            id=9,
            description="HARLOW SONS INV-041",
            amount="1050.00",
            tx_date="2026-06-27",
        )
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.OVERPAID
        assert r.confidence == 90
        assert r.method == "overpaid"
        assert "excess" in r.explanation.lower() or "exceeds" in r.explanation.lower()
        assert r.matched_amount == Decimal("1050.00")


class TestMultipleMatches:
    """MULTIPLE_MATCHES — two transactions each independently match the invoice."""

    def test_two_identical_payments_flag_multiple_matches(self, engine):
        inv = _inv(reference="INV-DUP", amount_due="1000.00")
        txs = [
            _tx(id=1, description="INV-DUP payment", amount="1000.00", tx_date="2026-06-30"),
            _tx(id=2, description="INV-DUP payment", amount="1000.00", tx_date="2026-06-30"),
        ]
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.MULTIPLE_MATCHES
        assert 1 in r.transaction_ids
        assert 2 in r.transaction_ids
        assert "review" in r.explanation.lower()


class TestUnmatched:
    """UNMATCHED — no transaction matches the invoice."""

    def test_no_transactions(self, engine):
        inv = _inv()
        r = engine.match(inv, [])
        assert r.status == MatchStatus.UNMATCHED
        assert r.confidence == 0
        assert r.matched_amount == Decimal("0")

    def test_no_matching_transaction(self, engine):
        inv = _inv(reference="INV-999", amount_due="5000.00")
        txs = [
            _tx(description="groceries", amount="42.50"),
            _tx(description="netflix sub", amount="15.99"),
        ]
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.UNMATCHED

    def test_negative_transactions_ignored(self, engine):
        """Outgoing (negative) transactions must never match income invoices."""
        inv = _inv(reference="INV-001", amount_due="1000.00")
        tx = _tx(description="INV-001", amount="-1000.00")
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.UNMATCHED


# ═══════════════════════════════════════════════════════════════════════════════
# match_all
# ═══════════════════════════════════════════════════════════════════════════════

class TestMatchAll:
    def test_returns_one_result_per_invoice(self, engine):
        invoices = [_inv(reference=f"INV-{i:03d}") for i in range(5)]
        txs = []
        results = engine.match_all(invoices, txs)
        assert len(results) == 5

    def test_order_preserved(self, engine):
        invoices = [
            _inv(reference="INV-001", amount_due="1000.00"),
            _inv(reference="INV-002", amount_due="2000.00"),
            _inv(reference="INV-003", amount_due="3000.00"),
        ]
        txs = [
            _tx(id=1, description="INV-001 pmt", amount="1000.00"),
            _tx(id=2, description="INV-002 pmt", amount="2000.00"),
            _tx(id=3, description="INV-003 pmt", amount="3000.00"),
        ]
        results = engine.match_all(invoices, txs)
        assert results[0].invoice.reference == "INV-001"
        assert results[1].invoice.reference == "INV-002"
        assert results[2].invoice.reference == "INV-003"

    def test_transactions_shared_across_invoices(self, engine):
        """The same transaction pool is used for every invoice — no consumption.
        Amounts differ so each transaction unambiguously matches only its own invoice."""
        invoices = [
            _inv(reference="INV-001", amount_due="500.00"),
            _inv(reference="INV-002", amount_due="750.00"),
        ]
        txs = [
            _tx(id=1, description="INV-001 pmt", amount="500.00"),
            _tx(id=2, description="INV-002 pmt", amount="750.00"),
        ]
        results = engine.match_all(invoices, txs)
        assert results[0].status == MatchStatus.MATCHED
        assert results[1].status == MatchStatus.MATCHED


# ═══════════════════════════════════════════════════════════════════════════════
# MatchResult dataclass
# ═══════════════════════════════════════════════════════════════════════════════

class TestMatchResult:
    def test_default_review_state(self, engine):
        inv = _inv()
        r = engine.match(inv, [])
        assert r.review_state == ReviewState.PENDING_REVIEW

    def test_matched_amount_is_decimal(self, engine):
        inv = _inv(reference="INV-001", amount_due="1000.00")
        tx = _tx(description="INV-001 pmt", amount="1000.00")
        r = engine.match(inv, [tx])
        assert isinstance(r.matched_amount, Decimal)

    def test_explanation_is_non_empty(self, engine):
        inv = _inv()
        r = engine.match(inv, [])
        assert len(r.explanation) > 10


# ═══════════════════════════════════════════════════════════════════════════════
# Database: invoices CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestInvoiceCRUD:
    def test_save_and_get_invoice(self, test_db):
        iid = db.save_invoice(
            reference="INV-TEST-001",
            client_name="ACME Ltd",
            amount_due=1500.00,
            issue_date="2026-06-01",
            due_date="2026-06-30",
        )
        assert isinstance(iid, int)
        row = db.get_invoice(iid)
        assert row is not None
        assert row["reference"] == "INV-TEST-001"
        assert row["client_name"] == "ACME Ltd"
        assert row["amount_due"] == 1500.00
        assert row["currency"] == "GBP"
        assert row["status"] == "unpaid"

    def test_get_invoice_by_reference(self, test_db):
        db.save_invoice(
            reference="INV-REF-001",
            client_name="Beta Corp",
            amount_due=2000.00,
            issue_date="2026-07-01",
            due_date="2026-07-31",
        )
        row = db.get_invoice_by_reference("INV-REF-001")
        assert row is not None
        assert row["client_name"] == "Beta Corp"

    def test_get_invoice_by_reference_missing(self, test_db):
        assert db.get_invoice_by_reference("INV-DOES-NOT-EXIST") is None

    def test_get_invoice_missing(self, test_db):
        assert db.get_invoice(99999) is None

    def test_list_invoices_empty(self, test_db):
        assert db.list_invoices() == []

    def test_list_invoices(self, test_db):
        db.save_invoice("INV-A", "Client A", 1000.00, "2026-06-01", "2026-06-30")
        db.save_invoice("INV-B", "Client B", 2000.00, "2026-07-01", "2026-07-31")
        rows = db.list_invoices()
        assert len(rows) == 2

    def test_update_invoice_status(self, test_db):
        iid = db.save_invoice("INV-STATUS", "Client", 500.00, "2026-06-01", "2026-06-30")
        db.update_invoice_status(iid, "paid")
        row = db.get_invoice(iid)
        assert row["status"] == "paid"

    def test_user_id_scoping(self, test_db):
        """get_invoice_by_reference scoped by user_id returns distinct rows."""
        uid_a = db.get_or_create_user("user_scope_a", email="a@test.com")
        uid_b = db.get_or_create_user("user_scope_b", email="b@test.com")
        db.save_invoice("INV-SCOPE", "Client A", 1000.00,
                        "2026-06-01", "2026-06-30", user_id=uid_a)
        db.save_invoice("INV-SCOPE", "Client B", 2000.00,
                        "2026-07-01", "2026-07-31", user_id=uid_b)

        row_a = db.get_invoice_by_reference("INV-SCOPE", user_id=uid_a)
        row_b = db.get_invoice_by_reference("INV-SCOPE", user_id=uid_b)
        assert row_a["client_name"] == "Client A"
        assert row_b["client_name"] == "Client B"
        assert row_a["id"] != row_b["id"]

    def test_unique_constraint_same_user(self, test_db):
        """Same (user_id, reference) pair raises IntegrityError."""
        uid = db.get_or_create_user("user_unique", email="u@test.com")
        db.save_invoice("INV-DUP", "Client", 100.00, "2026-06-01", "2026-06-30", user_id=uid)
        with pytest.raises(Exception):
            db.save_invoice("INV-DUP", "Client", 200.00, "2026-06-01", "2026-06-30", user_id=uid)

    def test_save_invoice_with_all_fields(self, test_db):
        uid = db.get_or_create_user("user_full", email="full@test.com")
        iid = db.save_invoice(
            reference="INV-FULL",
            client_name="Full Client",
            amount_due=9999.99,
            issue_date="2026-01-01",
            due_date="2026-01-31",
            currency="GBP",
            status="partially_paid",
            notes="Milestone 1 paid",
            user_id=uid,
        )
        row = db.get_invoice(iid)
        assert row["currency"] == "GBP"
        assert row["status"] == "partially_paid"
        assert row["notes"] == "Milestone 1 paid"
        assert row["user_id"] == uid


# ═══════════════════════════════════════════════════════════════════════════════
# Database: invoice_matches CRUD
# ═══════════════════════════════════════════════════════════════════════════════

class TestMatchCRUD:
    def _make_invoice(self) -> int:
        return db.save_invoice(
            "INV-MATCH-001", "Client", 1000.00, "2026-06-01", "2026-06-30"
        )

    def test_save_match(self, test_db):
        iid = self._make_invoice()
        mid = db.save_match(
            invoice_id=iid,
            status="matched",
            confidence=100,
            method="exact_amount_and_reference",
            explanation="Test explanation.",
            matched_amount=1000.00,
        )
        assert isinstance(mid, int)

    def test_get_matches_for_invoice(self, test_db):
        iid = self._make_invoice()
        db.save_match(iid, "matched", 100, "exact_amount_and_reference", "Exact.", 1000.00)
        matches = db.get_matches_for_invoice(iid)
        assert len(matches) == 1
        m = matches[0]
        assert m["invoice_id"] == iid
        assert m["status"] == "matched"
        assert m["confidence"] == 100
        assert m["review_state"] == "pending_review"

    def test_get_matches_for_invoice_empty(self, test_db):
        iid = self._make_invoice()
        assert db.get_matches_for_invoice(iid) == []

    def test_update_review_state(self, test_db):
        iid = self._make_invoice()
        mid = db.save_match(iid, "likely_match", 85, "exact_amount_and_date", "Expl.", 1000.00)
        db.update_match_review_state(mid, "confirmed")
        matches = db.get_matches_for_invoice(iid)
        assert matches[0]["review_state"] == "confirmed"

    def test_match_with_transaction_id(self, test_db):
        iid = self._make_invoice()
        db.save_match(iid, "matched", 100, "exact", "Expl.", 1000.00, transaction_id=42)
        m = db.get_matches_for_invoice(iid)[0]
        assert m["transaction_id"] == 42

    def test_match_without_transaction_id(self, test_db):
        """UNMATCHED rows have NULL transaction_id."""
        iid = self._make_invoice()
        db.save_match(iid, "unmatched", 0, "unmatched", "No match.", 0.00, transaction_id=None)
        m = db.get_matches_for_invoice(iid)[0]
        assert m["transaction_id"] is None

    def test_cascade_delete(self, test_db):
        """Deleting an invoice cascades to invoice_matches."""
        iid = self._make_invoice()
        db.save_match(iid, "matched", 100, "exact", "Expl.", 1000.00)
        assert len(db.get_matches_for_invoice(iid)) == 1

        # Delete the invoice directly
        import sqlite3 as _sqlite3
        with _sqlite3.connect(test_db) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("DELETE FROM invoices WHERE id = ?", (iid,))
            conn.commit()

        assert db.get_matches_for_invoice(iid) == []


# ═══════════════════════════════════════════════════════════════════════════════
# Database: persist_match_result
# ═══════════════════════════════════════════════════════════════════════════════

class TestPersistMatchResult:
    def test_unmatched_writes_one_row(self, test_db, engine):
        iid = db.save_invoice("INV-P1", "C", 1000.00, "2026-06-01", "2026-06-30")
        inv = _inv(reference="INV-P1", amount_due="1000.00")
        result = engine.match(inv, [])
        assert result.status == MatchStatus.UNMATCHED

        match_ids = db.persist_match_result(result, iid)
        assert len(match_ids) == 1
        rows = db.get_matches_for_invoice(iid)
        assert len(rows) == 1
        assert rows[0]["status"] == "unmatched"
        assert rows[0]["transaction_id"] is None

    def test_matched_writes_one_row(self, test_db, engine):
        iid = db.save_invoice("INV-P2", "C", 500.00, "2026-06-01", "2026-06-30")
        inv = _inv(reference="INV-P2", amount_due="500.00")
        tx = _tx(id=None, description="INV-P2 payment", amount="500.00")
        result = engine.match(inv, [tx])
        assert result.status == MatchStatus.MATCHED

        match_ids = db.persist_match_result(result, iid)
        assert len(match_ids) == 1

    def test_multiple_payments_writes_one_row_per_tx(self, test_db, engine):
        iid = db.save_invoice("INV-P3", "C", 3000.00, "2026-06-01", "2026-06-30")
        inv = _inv(reference="INV-P3X", amount_due="3000.00")
        # Use real DB-style integer IDs and include reference in both transactions
        txs = [
            _tx(id=101, description="INV-P3X milestone 1", amount="1500.00", tx_date="2026-06-15"),
            _tx(id=102, description="INV-P3X milestone 2", amount="1500.00", tx_date="2026-06-28"),
        ]
        result = engine.match(inv, txs)
        assert result.status == MatchStatus.MULTIPLE_PAYMENTS
        assert len(result.transaction_ids) == 2

        match_ids = db.persist_match_result(result, iid)
        assert len(match_ids) == 2
        rows = db.get_matches_for_invoice(iid)
        assert len(rows) == 2
        assert all(r["status"] == "multiple_payments" for r in rows)


# ═══════════════════════════════════════════════════════════════════════════════
# Demo data
# ═══════════════════════════════════════════════════════════════════════════════

class TestDemoInvoices:
    def test_demo_invoices_count(self):
        assert len(DEMO_INVOICES) == 13  # 12 original + 1 UNDERPAID (6A)

    def test_all_references_unique(self):
        refs = [inv.reference for inv in DEMO_INVOICES]
        assert len(refs) == len(set(refs)), "All demo invoice references must be unique"

    def test_all_amount_dues_positive(self):
        for inv in DEMO_INVOICES:
            assert inv.amount_due > 0, f"{inv.reference} has non-positive amount_due"

    def test_all_amount_dues_are_decimal(self):
        for inv in DEMO_INVOICES:
            assert isinstance(inv.amount_due, Decimal), f"{inv.reference} amount_due is not Decimal"

    def test_all_dates_parseable(self):
        from datetime import date
        for inv in DEMO_INVOICES:
            date.fromisoformat(inv.issue_date)
            date.fromisoformat(inv.due_date)

    def test_extra_transactions_positive_amounts(self):
        for tx in DEMO_EXTRA_TRANSACTIONS:
            assert tx["amount"] > 0


class TestDemoMatching:
    """Integration: run the engine over all demo data and verify expected outcomes."""

    def test_run_demo_matching_returns_one_per_invoice(self):
        results = run_demo_matching()
        assert len(results) == len(DEMO_INVOICES)

    def test_inv_2026_047_exact_match(self):
        """INV-2026-047 should match txn-001 at 100%."""
        results = run_demo_matching()
        r = next(r for r in results if r.invoice.reference == "INV-2026-047")
        assert r.status == MatchStatus.MATCHED
        assert r.confidence == 100

    def test_inv_2026_048_exact_match(self):
        results = run_demo_matching()
        r = next(r for r in results if r.invoice.reference == "INV-2026-048")
        assert r.status in (MatchStatus.MATCHED,)
        assert r.confidence >= 95

    def test_inv_2026_039_reference_match(self):
        """INV-2026-039 reference is in transactionInformation, not description."""
        results = run_demo_matching()
        r = next(r for r in results if r.invoice.reference == "INV-2026-039")
        assert r.status == MatchStatus.MATCHED
        assert r.confidence >= 95

    def test_inv_2026_035_exact_match(self):
        results = run_demo_matching()
        r = next(r for r in results if r.invoice.reference == "INV-2026-035")
        assert r.status == MatchStatus.MATCHED
        assert r.confidence == 100

    def test_inv_2026_052_likely_match_by_date(self):
        """INV-2026-052: exact amount, no reference, 3 days after due → 85%."""
        results = run_demo_matching()
        r = next(r for r in results if r.invoice.reference == "INV-2026-052")
        assert r.status == MatchStatus.LIKELY_MATCH
        assert r.confidence == 85

    def test_inv_2026_044_multiple_payments(self):
        """INV-2026-044: two £1,500 payments → MULTIPLE_PAYMENTS.
        Demo extra transactions have id=None so transaction_ids may be empty in
        the engine result — assert on status only."""
        results = run_demo_matching()
        r = next(r for r in results if r.invoice.reference == "INV-2026-044")
        assert r.status == MatchStatus.MULTIPLE_PAYMENTS

    def test_inv_2026_055_partial_payment(self):
        """INV-2026-055: £500 deposit of £2,000 → PARTIAL_PAYMENT."""
        results = run_demo_matching()
        r = next(r for r in results if r.invoice.reference == "INV-2026-055")
        assert r.status == MatchStatus.PARTIAL_PAYMENT
        assert r.matched_amount == Decimal("500.00")

    def test_inv_2026_041_overpaid(self):
        """INV-2026-041: £1,050 received against £1,000 → OVERPAID."""
        results = run_demo_matching()
        r = next(r for r in results if r.invoice.reference == "INV-2026-041")
        assert r.status == MatchStatus.OVERPAID
        assert r.matched_amount == Decimal("1050.00")

    def test_inv_2026_058_unmatched(self):
        """INV-2026-058: no payment received → UNMATCHED."""
        results = run_demo_matching()
        r = next(r for r in results if r.invoice.reference == "INV-2026-058")
        assert r.status == MatchStatus.UNMATCHED
        assert r.confidence == 0

    def test_all_results_have_explanation(self):
        results = run_demo_matching()
        for r in results:
            assert r.explanation, f"{r.invoice.reference} has empty explanation"

    def test_all_statuses_are_valid(self):
        valid = {s for s in MatchStatus}
        results = run_demo_matching()
        for r in results:
            assert r.status in valid


class TestSeedDemoInvoices:
    def test_seed_saves_all_invoices(self, test_db):
        result = seed_demo_invoices(user_id=None)
        assert result["saved"] == len(DEMO_INVOICES)
        assert result["skipped"] == 0

    def test_seed_is_idempotent(self, test_db):
        seed_demo_invoices(user_id=None)
        result2 = seed_demo_invoices(user_id=None)
        assert result2["saved"] == 0
        assert result2["skipped"] == len(DEMO_INVOICES)

    def test_seed_persists_to_db(self, test_db):
        seed_demo_invoices(user_id=None)
        rows = db.list_invoices(user_id=None)
        assert len(rows) == len(DEMO_INVOICES)

    def test_seed_with_user_id(self, test_db):
        uid = db.get_or_create_user("seed_user", email="seed@test.com")
        result = seed_demo_invoices(user_id=uid)
        assert result["saved"] == len(DEMO_INVOICES)
        rows = db.list_invoices(user_id=uid)
        assert len(rows) == len(DEMO_INVOICES)


# ═══════════════════════════════════════════════════════════════════════════════
# DB schema: WS6 tables created by init_db
# ═══════════════════════════════════════════════════════════════════════════════

def test_init_db_creates_ws6_tables(test_db):
    conn = sqlite3.connect(test_db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert "invoices" in tables
    assert "invoice_matches" in tables


def test_invoices_table_schema(test_db):
    conn = sqlite3.connect(test_db)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(invoices)").fetchall()}
    conn.close()
    required = {"id", "user_id", "reference", "client_name", "amount_due",
                "currency", "issue_date", "due_date", "status", "notes", "created_at"}
    assert required <= cols


def test_invoice_matches_table_schema(test_db):
    conn = sqlite3.connect(test_db)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(invoice_matches)").fetchall()}
    conn.close()
    required = {"id", "invoice_id", "transaction_id", "matched_at", "status",
                "confidence", "method", "explanation", "matched_amount", "review_state"}
    assert required <= cols


# ═══════════════════════════════════════════════════════════════════════════════
# 6A — Currency validation
# ═══════════════════════════════════════════════════════════════════════════════

class TestCurrencyCheck:
    """Unit tests for the three-way _currency_check helper."""

    def test_ok_same_currency(self):
        assert _currency_check("GBP", "GBP") == "ok"

    def test_ok_case_insensitive(self):
        assert _currency_check("gbp", "GBP") == "ok"
        assert _currency_check("GBP", "gbp") == "ok"

    def test_ok_whitespace_stripped(self):
        assert _currency_check(" GBP ", " GBP ") == "ok"

    def test_mismatch_different_currencies(self):
        assert _currency_check("GBP", "USD") == "mismatch"
        assert _currency_check("USD", "EUR") == "mismatch"

    def test_missing_blank_invoice_currency(self):
        assert _currency_check("", "GBP") == "missing"

    def test_missing_blank_tx_currency(self):
        assert _currency_check("GBP", "") == "missing"

    def test_missing_both_blank(self):
        assert _currency_check("", "") == "missing"

    def test_missing_none_invoice_currency(self):
        assert _currency_check(None, "GBP") == "missing"

    def test_missing_none_tx_currency(self):
        assert _currency_check("GBP", None) == "missing"

    def test_missing_both_none(self):
        assert _currency_check(None, None) == "missing"


class TestCurrenciesCompatible:
    """Unit tests for the _currencies_compatible boolean helper."""

    def test_returns_true_when_ok(self):
        assert _currencies_compatible("GBP", "GBP") is True
        assert _currencies_compatible("gbp", "GBP") is True
        assert _currencies_compatible(" GBP ", "GBP") is True

    def test_returns_false_for_mismatch(self):
        assert _currencies_compatible("GBP", "USD") is False
        assert _currencies_compatible("USD", "EUR") is False

    def test_returns_false_for_missing_tx_currency(self):
        """Blank/missing currency is NOT treated as any default — returns False."""
        assert _currencies_compatible("GBP", "") is False
        assert _currencies_compatible("GBP", None) is False

    def test_returns_false_for_missing_invoice_currency(self):
        assert _currencies_compatible("", "GBP") is False
        assert _currencies_compatible(None, "GBP") is False

    def test_returns_false_when_both_missing(self):
        assert _currencies_compatible("", "") is False
        assert _currencies_compatible(None, None) is False


class TestCurrencyFiltering:
    """Currency handling in MatchingEngine.match()."""

    def test_mismatch_usd_tx_does_not_match_gbp_invoice(self, engine):
        inv = _inv(reference="INV-CCY-001", amount_due="1000.00", currency="GBP")
        txs = [_tx(id=1, description="INV-CCY-001 payment", amount="1000.00", currency="USD")]
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.UNMATCHED
        assert r.method == "unmatched"  # mismatch → plain UNMATCHED, not currency_missing

    def test_mismatch_gbp_tx_does_not_match_usd_invoice(self, engine):
        inv = _inv(reference="INV-CCY-002", amount_due="1000.00", currency="USD")
        txs = [_tx(id=1, description="INV-CCY-002 payment", amount="1000.00", currency="GBP")]
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.UNMATCHED
        assert r.method == "unmatched"

    def test_matching_currency_still_works(self, engine):
        inv = _inv(reference="INV-CCY-003", amount_due="1000.00", currency="USD")
        txs = [_tx(id=1, description="INV-CCY-003 payment", amount="1000.00", currency="USD")]
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.MATCHED
        assert r.confidence == 100

    def test_mixed_currencies_only_compatible_txs_match(self, engine):
        """When pool has both GBP and USD, only GBP is used for a GBP invoice."""
        inv = _inv(reference="INV-CCY-004", amount_due="500.00", currency="GBP")
        txs = [
            _tx(id=1, description="INV-CCY-004 payment", amount="500.00", currency="USD"),
            _tx(id=2, description="INV-CCY-004 payment", amount="500.00", currency="GBP"),
        ]
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.MATCHED
        assert r.transaction_ids == [2]

    # ── Missing currency tests ────────────────────────────────────────────────

    def test_missing_tx_currency_returns_currency_missing(self, engine):
        """Blank transaction currency → currency_missing, not MATCHED."""
        inv = _inv(reference="INV-CCY-005", amount_due="250.00", currency="GBP")
        tx = _tx(id=1, description="INV-CCY-005 payment", amount="250.00", currency="")
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.UNMATCHED
        assert r.method == "currency_missing"

    def test_missing_invoice_currency_returns_currency_missing(self, engine):
        """Invoice with blank currency → all transactions are excluded, currency_missing."""
        inv = _inv(reference="INV-CCY-007", amount_due="500.00", currency="")
        tx = _tx(id=1, description="INV-CCY-007 payment", amount="500.00", currency="GBP")
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.UNMATCHED
        assert r.method == "currency_missing"

    def test_both_currencies_missing_returns_currency_missing(self, engine):
        """Both sides blank → currency_missing."""
        inv = _inv(reference="INV-CCY-008", amount_due="300.00", currency="")
        tx = _tx(id=1, description="INV-CCY-008 payment", amount="300.00", currency="")
        r = engine.match(inv, [tx])
        assert r.status == MatchStatus.UNMATCHED
        assert r.method == "currency_missing"

    def test_currency_missing_method_is_machine_readable(self, engine):
        """The method field is the machine-readable review-queue discriminator."""
        inv = _inv(reference="INV-CCY-009", amount_due="100.00", currency="GBP")
        tx = _tx(id=1, description="INV-CCY-009 payment", amount="100.00", currency="")
        r = engine.match(inv, [tx])
        assert r.method == "currency_missing"

    def test_currency_missing_explanation_is_user_readable(self, engine):
        """The explanation must mention verification failure and manual review."""
        inv = _inv(reference="INV-CCY-010", amount_due="100.00", currency="GBP")
        tx = _tx(id=1, description="INV-CCY-010 payment", amount="100.00", currency="")
        r = engine.match(inv, [tx])
        assert "currency" in r.explanation.lower()
        assert "review" in r.explanation.lower()

    def test_compatible_match_wins_over_missing_currency_tx(self, engine):
        """If pool has one compatible and one missing-currency tx, the match proceeds."""
        inv = _inv(reference="INV-CCY-011", amount_due="400.00", currency="GBP")
        txs = [
            _tx(id=1, description="INV-CCY-011 payment", amount="400.00", currency=""),
            _tx(id=2, description="INV-CCY-011 payment", amount="400.00", currency="GBP"),
        ]
        r = engine.match(inv, txs)
        # Compatible GBP match wins; the missing-currency tx is set aside
        assert r.status == MatchStatus.MATCHED
        assert r.transaction_ids == [2]

    def test_mismatch_does_not_produce_currency_missing(self, engine):
        """A known mismatch (GBP vs EUR) produces plain UNMATCHED, not currency_missing."""
        inv = _inv(reference="INV-CCY-012", amount_due="750.00", currency="EUR")
        txs = [_tx(id=1, description="INV-CCY-012 payment", amount="750.00", currency="GBP")]
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.UNMATCHED
        assert r.method == "unmatched"
        assert r.explanation  # non-empty


# ═══════════════════════════════════════════════════════════════════════════════
# 6A — UNDERPAID aggregate rule
# ═══════════════════════════════════════════════════════════════════════════════

class TestUnderpaid:
    """Tests for the _aggregate_underpaid rule."""

    def test_two_payments_short_of_total(self, engine):
        """Two reference-matched payments totalling less than due → UNDERPAID."""
        inv = _inv(reference="INV-U001", amount_due="2400.00")
        txs = [
            _tx(id=1, description="INV-U001 instalment 1", amount="800.00"),
            _tx(id=2, description="INV-U001 instalment 2", amount="1000.00"),
        ]
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.UNDERPAID
        assert r.matched_amount == Decimal("1800.00")
        assert r.confidence == 75

    def test_three_payments_still_short(self, engine):
        inv = _inv(reference="INV-U002", amount_due="3000.00")
        txs = [
            _tx(id=1, description="INV-U002 pmt 1", amount="600.00"),
            _tx(id=2, description="INV-U002 pmt 2", amount="700.00"),
            _tx(id=3, description="INV-U002 pmt 3", amount="800.00"),
        ]
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.UNDERPAID
        assert r.matched_amount == Decimal("2100.00")

    def test_single_tx_does_not_trigger_underpaid(self, engine):
        """One reference-matched payment below due → PARTIAL_PAYMENT, not UNDERPAID."""
        inv = _inv(reference="INV-U003", amount_due="2400.00")
        txs = [_tx(id=1, description="INV-U003 payment", amount="800.00")]
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.PARTIAL_PAYMENT

    def test_does_not_fire_when_total_exceeds_99pct(self, engine):
        """If two payments together sum to ≥ 99% of due → MULTIPLE_PAYMENTS territory."""
        inv = _inv(reference="INV-U004", amount_due="2000.00")
        txs = [
            _tx(id=1, description="INV-U004 pmt 1", amount="1000.00"),
            _tx(id=2, description="INV-U004 pmt 2", amount="1000.00"),
        ]
        r = engine.match(inv, txs)
        # Exactly equal → MULTIPLE_PAYMENTS, not UNDERPAID
        assert r.status == MatchStatus.MULTIPLE_PAYMENTS

    def test_requires_reference_on_all_txs(self, engine):
        """If one payment lacks the reference it is not included in UNDERPAID calculation."""
        inv = _inv(reference="INV-U005", amount_due="2400.00")
        txs = [
            _tx(id=1, description="INV-U005 instalment 1", amount="800.00"),
            _tx(id=2, description="unrelated payment", amount="1000.00"),  # no reference
        ]
        # Only one reference-matching tx → PARTIAL_PAYMENT, not UNDERPAID
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.PARTIAL_PAYMENT

    def test_too_small_total_does_not_trigger(self, engine):
        """If combined total is < 10% of due the rule does not fire."""
        inv = _inv(reference="INV-U006", amount_due="10000.00")
        txs = [
            _tx(id=1, description="INV-U006 tiny 1", amount="50.00"),
            _tx(id=2, description="INV-U006 tiny 2", amount="50.00"),
        ]
        # 100/10000 = 1% — below the 10% floor, UNDERPAID should not fire
        r = engine.match(inv, txs)
        assert r.status != MatchStatus.UNDERPAID

    def test_matched_amount_is_sum_of_matched_txs(self, engine):
        inv = _inv(reference="INV-U007", amount_due="3000.00")
        txs = [
            _tx(id=1, description="INV-U007 pmt a", amount="900.00"),
            _tx(id=2, description="INV-U007 pmt b", amount="900.00"),
        ]
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.UNDERPAID
        assert r.matched_amount == Decimal("1800.00")

    def test_explanation_is_non_empty(self, engine):
        inv = _inv(reference="INV-U008", amount_due="2000.00")
        txs = [
            _tx(id=1, description="INV-U008 pmt 1", amount="600.00"),
            _tx(id=2, description="INV-U008 pmt 2", amount="700.00"),
        ]
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.UNDERPAID
        assert r.explanation
        assert "INV-U008" in r.explanation

    def test_method_slug(self, engine):
        inv = _inv(reference="INV-U009", amount_due="2000.00")
        txs = [
            _tx(id=1, description="INV-U009 pmt 1", amount="500.00"),
            _tx(id=2, description="INV-U009 pmt 2", amount="500.00"),
        ]
        r = engine.match(inv, txs)
        assert r.status == MatchStatus.UNDERPAID
        assert r.method == "underpaid"


# ═══════════════════════════════════════════════════════════════════════════════
# 6A — Demo scenario: INV-2026-060 (UNDERPAID)
# ═══════════════════════════════════════════════════════════════════════════════

class TestDemoUnderpaid:
    def test_inv_2026_060_underpaid(self):
        """INV-2026-060: two payments (£800 + £1,000 = £1,800) against £2,400 → UNDERPAID."""
        results = run_demo_matching()
        r = next(r for r in results if r.invoice.reference == "INV-2026-060")
        assert r.status == MatchStatus.UNDERPAID
        assert r.matched_amount == Decimal("1800.00")
        assert r.confidence == 75

    def test_all_13_demo_invoices_have_results(self):
        """After adding UNDERPAID, run_demo_matching returns one result per invoice."""
        results = run_demo_matching()
        assert len(results) == len(DEMO_INVOICES)

    def test_all_9_statuses_covered_in_demo(self):
        """
        All statuses reachable from the demo transaction pool appear at least once.

        MULTIPLE_MATCHES requires two independently high-confidence matching transactions
        for the same invoice — a scenario that does not arise naturally in the shared demo
        pool (where each transaction is associated with a different invoice). It is
        covered by dedicated unit tests in TestMultipleMatches instead.
        """
        results = run_demo_matching()
        statuses = {r.status for r in results}
        expected = set(MatchStatus) - {MatchStatus.MULTIPLE_MATCHES}
        for status in expected:
            assert status in statuses, f"Demo does not cover {status}"
