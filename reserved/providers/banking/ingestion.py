"""
Transaction ingestion pipeline for Reserved™.

Orchestrates: Yapily raw transactions → classification → ClassifiedTransaction list.

Usage (live):
    client = YapilyClient()
    results = ingest_transactions(client, consent_token, account_id)

Usage (demo / V2 preview):
    results = get_demo_transactions()

Usage (demo persistence):
    seed_demo_data()   # idempotent; creates a demo connection, account, and transactions in the DB
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal

from reserved.providers.banking.classifier import (
    ClassifiedTransaction,
    ClassificationResult,
    RulesClassifier,
    TransactionCategory,
    TransactionPipeline,
)
from reserved.providers.banking.demo_transactions import DEMO_TRANSACTIONS


def ingest_transactions(
    client,               # YapilyClient — not type-hinted to avoid circular import
    consent_token: str,
    account_id: str,
    pipeline: TransactionPipeline | None = None,
) -> list[ClassifiedTransaction]:
    """
    Fetch transactions from Yapily and classify them.

    Args:
        client:        A YapilyClient instance (mock or live).
        consent_token: Active Yapily consent token.
        account_id:    Yapily account ID to fetch transactions for.
        pipeline:      Optional custom TransactionPipeline; defaults to RulesClassifier.

    Returns:
        List of ClassifiedTransaction objects, newest first.
    """
    raw = client.list_transactions(consent_token, account_id)
    _pipeline = pipeline or TransactionPipeline(classifiers=[RulesClassifier()])
    classified = _pipeline.process(raw)
    return sorted(classified, key=lambda t: t.date, reverse=True)


def get_demo_transactions(
    pipeline: TransactionPipeline | None = None,
) -> list[ClassifiedTransaction]:
    """
    Return classified demo transactions for the V2 preview.

    Uses DEMO_TRANSACTIONS from demo_transactions.py — no Yapily credentials needed.
    """
    _pipeline = pipeline or TransactionPipeline(classifiers=[RulesClassifier()])
    classified = _pipeline.process(DEMO_TRANSACTIONS)
    return sorted(classified, key=lambda t: t.date, reverse=True)


# ── Summary helpers ────────────────────────────────────────────────────────────

def persist_transactions(account_id: int, classified: list[ClassifiedTransaction]) -> int:
    """
    Persist classified transactions to the database.

    Converts each ClassifiedTransaction to a plain dict and calls
    database.save_transactions(). Safe to call repeatedly — rows are
    upserted on (account_id, yapily_tx_id).

    Returns the number of rows written.
    """
    from reserved.database import save_transactions

    rows = [
        {
            "yapily_tx_id": ct.id or ct.raw.get("id", ""),
            "tx_date": ct.date,
            "description": ct.description,
            "amount": float(ct.amount),
            "currency": ct.currency,
            "category": ct.classification.category.value,
            "confidence": ct.classification.confidence,
            "method": ct.classification.method,
            "subcategory": ct.classification.subcategory,
            "tax_relevant": ct.classification.tax_relevant,
            "raw_json": json.dumps(ct.raw),
        }
        for ct in classified
    ]
    return save_transactions(account_id, rows)


def seed_demo_data(user_id: int | None = None) -> dict:
    """
    Persist the demo bank connection, account, and transactions to the DB.

    When *user_id* is provided the seeded connection is owned by that user;
    each user gets their own demo connection row keyed by a per-user token so
    users cannot access each other's seeded data.

    When *user_id* is None the legacy global token is used (backward-compatible
    for existing callers such as the startup fixture).

    Idempotent — safe to call multiple times; existing rows are reused or
    updated. Returns {"connection_id": int, "account_id": int, "tx_count": int}.
    """
    from reserved.database import (
        delete_connection,
        get_account,
        get_connection_by_token,
        save_account,
        save_connection,
    )

    # Per-user token isolates each user's demo data.
    if user_id is not None:
        _DEMO_TOKEN    = f"demo-consent-token-user-{user_id}"
        _DEMO_YAPILY_ID = f"demo-account-user-{user_id}"
    else:
        _DEMO_TOKEN    = "demo-consent-token-ws4"
        _DEMO_YAPILY_ID = "demo-account-ws4-001"
    _now = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")  # noqa: E731

    # Connection — owned by this user
    existing = get_connection_by_token(_DEMO_TOKEN)
    conn_id = existing["id"] if existing else save_connection(
        institution_id="monzo",
        institution_name="Monzo (demo)",
        consent_token=_DEMO_TOKEN,
        expires_at="2026-12-31T00:00:00+00:00",
        session_key=f"demo-user-{user_id}" if user_id else "demo",
        user_id=user_id,
    )

    # Account
    existing_acc = get_account(_DEMO_YAPILY_ID)
    acc_id = existing_acc["id"] if existing_acc else save_account(
        connection_id=conn_id,
        yapily_account_id=_DEMO_YAPILY_ID,
        account_type="CURRENT",
        nickname="Monzo — demo",
        currency="GBP",
        sort_code="040004",
        account_number="12345678",
        balance=4821.55,
        balance_at=_now(),
    )

    # Transactions
    classified = get_demo_transactions()
    tx_count = persist_transactions(acc_id, classified)

    return {"connection_id": conn_id, "account_id": acc_id, "tx_count": tx_count}


def summarise(transactions: list[ClassifiedTransaction]) -> dict:
    """
    Return a summary dict of tax-relevant totals for a list of classified transactions.

    Keys:
        total_income        — sum of all income categories (GBP, positive)
        total_tax_payments  — sum of TAX_PAYMENT amounts (GBP, positive)
        total_expenses      — sum of BUSINESS_EXPENSE + SUBSCRIPTION (GBP, positive)
        unclassified_count  — number of UNKNOWN transactions
        by_category         — dict[TransactionCategory, Decimal] of totals
    """
    income_cats = {
        TransactionCategory.FREELANCE_INCOME,
        TransactionCategory.SALARY,
        TransactionCategory.DIVIDEND,
        TransactionCategory.INTEREST,
        TransactionCategory.RENTAL_INCOME,
        TransactionCategory.TAX_REFUND,
    }
    expense_cats = {
        TransactionCategory.BUSINESS_EXPENSE,
        TransactionCategory.SUBSCRIPTION,
    }

    total_income = Decimal("0")
    total_tax = Decimal("0")
    total_expenses = Decimal("0")
    unclassified = 0
    by_category: dict[TransactionCategory, Decimal] = {}

    for ct in transactions:
        cat = ct.classification.category
        amt = abs(ct.amount)
        by_category[cat] = by_category.get(cat, Decimal("0")) + amt

        if cat in income_cats:
            total_income += ct.amount  # positive
        elif cat == TransactionCategory.TAX_PAYMENT:
            total_tax += amt
        elif cat in expense_cats:
            total_expenses += amt
        elif cat == TransactionCategory.UNKNOWN:
            unclassified += 1

    return {
        "total_income": total_income,
        "total_tax_payments": total_tax,
        "total_expenses": total_expenses,
        "unclassified_count": unclassified,
        "by_category": by_category,
    }
