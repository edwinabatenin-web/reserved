"""
Workstream 6 — Representative demo invoices and matching scenarios.

Persona: UK sole-trader / freelance designer (same as demo_transactions.py).
Tax year 2025/26.

Scenarios covered
-----------------
1.  MATCHED (100%)  — exact amount + reference in description
2.  MATCHED (100%)  — exact amount + reference in description (second invoice)
3.  MATCHED (95%)   — reference in transactionInformation, not description
4.  MATCHED (100%)  — exact amount + reference in description
5.  MATCHED (100%)  — reference in transactionInformation
6.  MATCHED (100%)  — exact amount + reference in description
7.  LIKELY_MATCH (85%) — exact amount, received 3 days after due date, no reference
8.  LIKELY_MATCH (74%) — amount within 1%, received 1 day before due date
9.  MULTIPLE_PAYMENTS  — invoice settled by two separate payments
10. PARTIAL_PAYMENT    — reference matched, only 25% paid so far (one payment)
11. OVERPAID           — client paid £50 more than invoiced
12. UNMATCHED          — no corresponding transaction in the demo set
13. UNDERPAID          — two payments received but together fall short of amount due
"""

from __future__ import annotations

from decimal import Decimal

from reserved.matching.engine import Invoice, MatchResult, MatchingEngine


# ── Demo invoices ─────────────────────────────────────────────────────────────

DEMO_INVOICES: list[Invoice] = [

    # 1. Exact match via description — txn-001
    Invoice(
        reference="INV-2026-047",
        client_name="Studio Client Ltd",
        amount_due=Decimal("3200.00"),
        issue_date="2026-07-01",
        due_date="2026-07-28",
        notes="Brand identity project, Phase 2",
    ),

    # 2. Exact match via description — txn-002
    Invoice(
        reference="INV-2026-048",
        client_name="Apex Digital",
        amount_due=Decimal("1850.00"),
        issue_date="2026-07-07",
        due_date="2026-07-14",
        notes="UX audit and wireframes",
    ),

    # 3. Reference in transactionInformation, not description — txn-003
    Invoice(
        reference="INV-2026-039",
        client_name="Meridian Group",
        amount_due=Decimal("4500.00"),
        issue_date="2026-06-01",
        due_date="2026-06-30",
        notes="Design consultancy retainer, June",
    ),

    # 4. Exact match via description — txn-004
    Invoice(
        reference="INV-2026-035",
        client_name="Bloom Creative",
        amount_due=Decimal("2700.00"),
        issue_date="2026-06-01",
        due_date="2026-06-15",
        notes="Brand identity project",
    ),

    # 5. Reference in transactionInformation — txn-005
    Invoice(
        reference="INV-2026-029",
        client_name="Kova Agency",
        amount_due=Decimal("1200.00"),
        issue_date="2026-05-15",
        due_date="2026-05-31",
        notes="Social media asset pack",
    ),

    # 6. Exact match via description — txn-006
    Invoice(
        reference="INV-2026-022",
        client_name="Northgate Labs",
        amount_due=Decimal("3900.00"),
        issue_date="2026-04-15",
        due_date="2026-04-30",
        notes="Design contract, sprint 3",
    ),

    # 7. LIKELY_MATCH (85%) — exact amount, 3 days late, no reference in transaction
    #    Matched against a synthetic transaction (tx-demo-A) with no reference
    Invoice(
        reference="INV-2026-052",
        client_name="Prism Media",
        amount_due=Decimal("2850.00"),
        issue_date="2026-07-15",
        due_date="2026-07-28",
        notes="Motion graphics package",
    ),

    # 8. LIKELY_MATCH (74%) — amount within 1%, 1 day early, no reference
    #    Matched against a synthetic transaction (tx-demo-B) with £2,822 amount
    Invoice(
        reference="INV-2026-053",
        client_name="Opal Studio",
        amount_due=Decimal("2850.00"),
        issue_date="2026-07-15",
        due_date="2026-07-31",
        notes="Icon library — 40 icons",
    ),

    # 9. MULTIPLE_PAYMENTS — two payments of £1,500 each settle a £3,000 invoice
    Invoice(
        reference="INV-2026-044",
        client_name="Cyan & Co",
        amount_due=Decimal("3000.00"),
        issue_date="2026-06-01",
        due_date="2026-06-30",
        notes="Website redesign — milestone payments",
    ),

    # 10. PARTIAL_PAYMENT — £500 deposit received, £1,500 outstanding
    Invoice(
        reference="INV-2026-055",
        client_name="Vertex Media",
        amount_due=Decimal("2000.00"),
        issue_date="2026-07-20",
        due_date="2026-08-10",
        notes="Brand guidelines document",
    ),

    # 11. OVERPAID — client paid £1,050 against a £1,000 invoice
    Invoice(
        reference="INV-2026-041",
        client_name="Harlow & Sons",
        amount_due=Decimal("1000.00"),
        issue_date="2026-06-10",
        due_date="2026-06-28",
        notes="Logo refresh",
    ),

    # 12. UNMATCHED — no payment received yet
    Invoice(
        reference="INV-2026-058",
        client_name="Selene Consulting",
        amount_due=Decimal("4200.00"),
        issue_date="2026-08-01",
        due_date="2026-08-31",
        notes="Product design sprint — awaiting payment",
    ),

    # 13. UNDERPAID — two reference-matched payments totalling £1,800 against £2,400 due
    #     Matched against txn-demo-F (£800) and txn-demo-G (£1,000)
    Invoice(
        reference="INV-2026-060",
        client_name="Indigo Creative",
        amount_due=Decimal("2400.00"),
        issue_date="2026-07-01",
        due_date="2026-07-31",
        notes="Branding sprint — 3 instalments agreed, only 2 received",
    ),
]


# ── Demo transactions (additional — not in demo_transactions.py) ──────────────
# These complement the existing Yapily-sourced demo transactions and cover
# the edge-case matching scenarios above (7–11).

DEMO_EXTRA_TRANSACTIONS: list[dict] = [

    # Scenario 7: exact amount, 3 days after INV-2026-052 due date (2026-07-28 + 3 = 2026-07-31)
    # No reference in description — triggers exact_amount_and_date at 85%
    {
        "id": None,
        "yapily_tx_id": "txn-demo-A",
        "tx_date": "2026-07-31",
        "description": "BACS TRANSFER PRISM MEDIA",
        "transactionInformation": "Payment August",
        "amount": 2850.00,
        "currency": "GBP",
    },

    # Scenario 8: £2,822 received 1 day before INV-2026-053 due date (2026-07-30)
    # Amount within ~1%, date within 2 days — triggers close_amount_and_date at 74%
    {
        "id": None,
        "yapily_tx_id": "txn-demo-B",
        "tx_date": "2026-07-30",
        "description": "FASTER PAYMENT OPAL STUDIO",
        "transactionInformation": "Icon project balance",
        "amount": 2822.00,
        "currency": "GBP",
    },

    # Scenario 9: two £1,500 payments for INV-2026-044
    {
        "id": None,
        "yapily_tx_id": "txn-demo-C1",
        "tx_date": "2026-06-15",
        "description": "CYAN CO INV-2026-044 MILESTONE 1",
        "transactionInformation": "Website redesign deposit",
        "amount": 1500.00,
        "currency": "GBP",
    },
    {
        "id": None,
        "yapily_tx_id": "txn-demo-C2",
        "tx_date": "2026-06-28",
        "description": "CYAN CO INV-2026-044 MILESTONE 2",
        "transactionInformation": "Website redesign final",
        "amount": 1500.00,
        "currency": "GBP",
    },

    # Scenario 10: £500 deposit for INV-2026-055 (partial: £500 of £2,000)
    {
        "id": None,
        "yapily_tx_id": "txn-demo-D",
        "tx_date": "2026-07-22",
        "description": "VERTEX MEDIA INV-2026-055 DEPOSIT",
        "transactionInformation": "Brand guidelines deposit 25%",
        "amount": 500.00,
        "currency": "GBP",
    },

    # Scenario 11: £1,050 received against INV-2026-041 (£50 overpayment)
    {
        "id": None,
        "yapily_tx_id": "txn-demo-E",
        "tx_date": "2026-06-27",
        "description": "HARLOW SONS INV-2026-041",
        "transactionInformation": "Logo refresh payment",
        "amount": 1050.00,
        "currency": "GBP",
    },

    # Scenario 13: two underpaying instalments for INV-2026-060 (£800 + £1,000 = £1,800 of £2,400)
    {
        "id": None,
        "yapily_tx_id": "txn-demo-F",
        "tx_date": "2026-07-10",
        "description": "INDIGO CREATIVE INV-2026-060 INSTALMENT 1",
        "transactionInformation": "Branding sprint instalment 1 of 3",
        "amount": 800.00,
        "currency": "GBP",
    },
    {
        "id": None,
        "yapily_tx_id": "txn-demo-G",
        "tx_date": "2026-07-22",
        "description": "INDIGO CREATIVE INV-2026-060 INSTALMENT 2",
        "transactionInformation": "Branding sprint instalment 2 of 3",
        "amount": 1000.00,
        "currency": "GBP",
    },
]


# ── Demo transaction pool (primary + extra, for matching demo) ─────────────────

def get_demo_transactions_for_matching() -> list[dict]:
    """
    Return the full set of transactions used by the matching demo.
    Includes the primary Yapily demo transactions (from demo_transactions.py)
    plus the WS6 supplementary transactions covering edge-case scenarios.
    """
    from reserved.providers.banking.demo_transactions import DEMO_TRANSACTIONS
    # Assign synthetic numeric IDs to extra transactions for display purposes
    primary = [dict(t, tx_date=t["date"]) for t in DEMO_TRANSACTIONS]
    return primary + DEMO_EXTRA_TRANSACTIONS


# ── Seed function ─────────────────────────────────────────────────────────────

def seed_demo_invoices(user_id: int | None = None) -> dict:
    """
    Persist DEMO_INVOICES to the database for a given user.

    Idempotent — existing invoices (matched by user_id + reference) are skipped.
    Returns {"saved": n, "skipped": n}.

    Parameters
    ----------
    user_id : int | None
        Internal DB user_id. When None, the invoices are saved without a user FK
        (useful for integration tests that do not create a user record).
    """
    from reserved.database import save_invoice, get_invoice_by_reference

    saved = 0
    skipped = 0
    for inv in DEMO_INVOICES:
        existing = get_invoice_by_reference(inv.reference, user_id=user_id)
        if existing:
            skipped += 1
            continue
        save_invoice(
            reference=inv.reference,
            client_name=inv.client_name,
            amount_due=float(inv.amount_due),
            issue_date=inv.issue_date,
            due_date=inv.due_date,
            currency=inv.currency,
            status=inv.status,
            notes=inv.notes,
            user_id=user_id,
        )
        saved += 1
    return {"saved": saved, "skipped": skipped}


def run_demo_matching() -> list[MatchResult]:
    """
    Run the matching engine over all demo invoices and the demo transaction pool.
    Returns one MatchResult per invoice, useful for previewing matching output.
    """
    engine = MatchingEngine()
    transactions = get_demo_transactions_for_matching()
    return engine.match_all(DEMO_INVOICES, transactions)
