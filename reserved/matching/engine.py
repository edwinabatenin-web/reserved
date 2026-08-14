"""
Workstream 6 — Deterministic, explainable invoice matching engine.

Architecture
------------
Matching is a pipeline of named rules applied in descending confidence order.
Each rule is self-contained: it takes one invoice and one transaction candidate
and returns a MatchResult or None.

The engine stops at the first rule that fires for a given transaction.
After all single-transaction rules are evaluated across all candidates, the
engine also checks whether multiple transactions together settle one invoice.

Rules (in order of confidence):

  Rule                          │ Confidence │ Status
  ──────────────────────────────┼────────────┼──────────────────
  exact_amount_and_reference    │ 100 %      │ MATCHED
  reference_and_close_amount    │  95 %      │ MATCHED
  exact_amount_and_date         │  85 %      │ LIKELY_MATCH
  close_amount_and_date         │  74 %      │ LIKELY_MATCH
  reference_only                │  60 %      │ LIKELY_MATCH
  ──────────────────────────────┼────────────┼──────────────────
  (aggregate) overpaid          │  90 %      │ OVERPAID
  (aggregate) multiple_payments │  90 %      │ MULTIPLE_PAYMENTS
  (aggregate) underpaid         │  75 %      │ UNDERPAID
  (aggregate) partial_payment   │  80 %      │ PARTIAL_PAYMENT
  ──────────────────────────────┼────────────┼──────────────────
  no match                      │   0 %      │ UNMATCHED

When two or more candidates independently satisfy the top-tier rules, the
invoice is flagged MULTIPLE_MATCHES and the user must arbitrate.

Currency validation
-------------------
Before any amount comparison, each transaction is classified by currency:

  "ok"       Both invoice and transaction have present, matching currency codes.
             Matching proceeds normally.
  "mismatch" Both currencies are present but differ. The transaction is silently
             excluded — a GBP transaction is simply not relevant to a USD invoice.
  "missing"  Either the invoice or the transaction has a blank/absent currency.
             The transaction is excluded from automatic matching. If no compatible
             match is found, the result carries method="currency_missing" so the
             invoice can surface in the user-review queue. No currency is assumed.

Cross-currency matching (with FX conversion) is intentionally unsupported.

Review workflow (stub — not fully wired in WS6)
-----------------------------------------------
Every MatchResult carries a review_state (PENDING_REVIEW | CONFIRMED | REJECTED).
Future workstreams can filter by review_state and wire confirm/reject routes.

Design principles (per spec)
----------------------------
- Simple, deterministic, explainable.
- Every match includes confidence %, method slug, and plain-English explanation.
- No ML, no clever heuristics.
- The status model is a string enum — subclasses may add new statuses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date as _date
from decimal import Decimal
from enum import Enum
from typing import Sequence


# ── Status & review enums ─────────────────────────────────────────────────────

class MatchStatus(str, Enum):
    """All possible invoice-matching outcomes. Extensible via subclassing."""
    MATCHED           = "matched"           # high confidence, single transaction
    LIKELY_MATCH      = "likely_match"      # probable but review recommended
    PARTIAL_PAYMENT   = "partial_payment"   # one payment, more expected
    MULTIPLE_PAYMENTS = "multiple_payments" # several payments together settle invoice
    OVERPAID          = "overpaid"          # total received > amount due
    UNDERPAID         = "underpaid"         # total received < amount due (closed)
    MULTIPLE_MATCHES  = "multiple_matches"  # >1 transaction independently matches
    UNMATCHED         = "unmatched"         # no plausible candidate found


class ReviewState(str, Enum):
    """User review workflow state. Architecture stub for future workstreams."""
    PENDING_REVIEW = "pending_review"
    CONFIRMED      = "confirmed"
    REJECTED       = "rejected"


# ── Invoice dataclass ─────────────────────────────────────────────────────────

@dataclass
class Invoice:
    """
    A single invoice issued by the user.

    Fields
    ------
    reference    Unique invoice reference (e.g. "INV-2026-047").
    client_name  Display name of the client.
    amount_due   Gross amount owed, in the invoice currency.
    issue_date   Date the invoice was raised.
    due_date     Payment due date (used for date-proximity matching).
    currency     ISO 4217 code. Defaults to "GBP".
    status       Accounting status: unpaid | partially_paid | paid | overpaid | void.
    notes        Free-text notes. Not used by the engine.
    id           Database primary key (None for unsaved invoices).
    user_id      FK to users table (None for unsaved / demo invoices).
    created_at   ISO-8601 timestamp (None for unsaved invoices).
    """
    reference:   str
    client_name: str
    amount_due:  Decimal
    issue_date:  str   # YYYY-MM-DD
    due_date:    str   # YYYY-MM-DD
    currency:    str  = "GBP"
    status:      str  = "unpaid"
    notes:       str | None = None
    id:          int | None = None
    user_id:     int | None = None
    created_at:  str | None = None

    def __post_init__(self):
        # Ensure amount_due is always a Decimal for precise arithmetic
        if not isinstance(self.amount_due, Decimal):
            self.amount_due = Decimal(str(self.amount_due))


# ── Match result dataclass ────────────────────────────────────────────────────

@dataclass
class MatchResult:
    """
    The result of matching one invoice against a set of transactions.

    Fields
    ------
    invoice         The Invoice being matched.
    status          Outcome (MatchStatus enum).
    confidence      Integer 0–100. The engine's certainty of the match.
    method          Slug identifying which rule(s) fired (e.g. "exact_amount_and_reference").
    explanation     Plain-English sentence explaining the match. Shown to the user.
    matched_amount  The total amount attributed to this invoice across all matched txs.
    transaction_ids List of DB transaction IDs that contribute to this match.
                    Empty for UNMATCHED; multiple IDs for MULTIPLE_PAYMENTS.
    review_state    Initial review state — always PENDING_REVIEW from the engine.
                    Callers may override after persisting.
    db_match_ids    List of invoice_matches.id PKs after persistence (empty before save).
    """
    invoice:         Invoice
    status:          MatchStatus
    confidence:      int
    method:          str
    explanation:     str
    matched_amount:  Decimal
    transaction_ids: list[int]         = field(default_factory=list)
    review_state:    ReviewState       = ReviewState.PENDING_REVIEW
    db_match_ids:    list[int]         = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.matched_amount, Decimal):
            self.matched_amount = Decimal(str(self.matched_amount))


# ── Internal helpers ──────────────────────────────────────────────────────────

def _to_decimal(value) -> Decimal:
    return Decimal(str(value or 0))


def _currency_check(invoice_ccy: str | None, tx_ccy: str | None) -> str:
    """
    Three-way currency compatibility test.

    Returns
    -------
    "ok"       Both values are present after normalisation and are equal.
    "mismatch" Both values are present and normalised, but differ.
    "missing"  Either value is absent or blank after normalisation.

    Normalisation: strip whitespace, uppercase.  No implicit defaults —
    a blank currency is treated as unknown, not as any particular currency code.
    This is intentional: assuming a currency would silently produce incorrect
    financial data.

    Callers
    -------
    _currencies_compatible()  — public helper used by tests / external code.
    MatchingEngine.match()    — uses the three-way result to distinguish
                                silent exclusion (mismatch) from review-queue
                                flagging (missing).
    """
    inv = (invoice_ccy or "").upper().strip()
    txc = (tx_ccy or "").upper().strip()
    if not inv or not txc:
        return "missing"
    if inv == txc:
        return "ok"
    return "mismatch"


def _currencies_compatible(invoice_ccy: str | None, tx_ccy: str | None) -> bool:
    """
    True only when both currencies are present, normalised, and equal.

    Returns False for known mismatches AND for missing/blank values.
    Use _currency_check() directly when you need to distinguish those two cases.
    """
    return _currency_check(invoice_ccy, tx_ccy) == "ok"


def _normalise_tx(tx: dict) -> dict:
    """
    Normalise a transaction dict from any source (DB row or raw demo dict)
    into a consistent internal shape.

    Accepts either:
      - DB-style:   {id, tx_date, description, amount, ...}
      - Yapily-style: {id, date, description, amount, transactionInformation, ...}
    """
    tx_date = tx.get("tx_date") or tx.get("date", "")
    description = (tx.get("description") or "").strip()
    info = (tx.get("transactionInformation") or "").strip()
    amount = _to_decimal(tx.get("amount", 0))
    return {
        "id":          tx.get("id"),
        "yapily_tx_id": tx.get("yapily_tx_id") or tx.get("id", ""),
        "tx_date":     tx_date,
        "description": description,
        "info":        info,
        # Searchable text: description + info combined, uppercased
        "_search_text": f"{description} {info}".upper(),
        "amount":      amount,
        # Normalise currency: strip whitespace + uppercase. Store "" when absent —
        # the engine treats blank as "unknown" rather than assuming any default.
        "currency":    (tx.get("currency") or "").upper().strip(),
    }


def _reference_in_text(reference: str, search_text: str) -> bool:
    """
    True if the invoice reference (or a normalised variant) appears in search_text.

    Matching strategies, tried in order:
    1. Exact match:     "INV-2026-047" in "INV-2026-047 STUDIO CLIENT LTD"
    2. Dash-stripped:   "INV2026047"   in "INV2026047 PAYMENT"
    3. Numeric suffix:  "2026-048"     in "APEX DIGITAL INVOICE 2026-048"
       Handles bank descriptions that spell "INVOICE" in full rather than "INV".
       Only applied when the numeric portion is ≥ 5 characters (avoids short
       false-positive matches like "001" appearing in unrelated text).
    """
    ref = reference.strip().upper()
    if ref in search_text:
        return True

    # Dash/slash/space stripped
    ref_no_sep = ref.replace("-", "").replace("/", "").replace(" ", "")
    text_no_sep = search_text.replace("-", "").replace("/", "").replace(" ", "")
    if ref_no_sep and ref_no_sep in text_no_sep:
        return True

    # Numeric suffix: strip leading alphabetic prefix and optional separator
    # e.g. "INV-2026-048" → "2026-048", then search for "2026-048" in original text
    suffix_match = re.match(r'^[A-Z]+[-/]?\s*([\d][\w\-/]*\d)$', ref)
    if suffix_match:
        numeric_part = suffix_match.group(1)
        if len(numeric_part) >= 5 and numeric_part in search_text:
            return True

    return False


def _amount_exact(tx_amount: Decimal, due: Decimal) -> bool:
    return tx_amount == due


def _amount_within_pct(tx_amount: Decimal, due: Decimal, pct: Decimal) -> bool:
    """True if tx_amount is within pct% of due (e.g. pct=Decimal("0.02") → 2%)."""
    if due == 0:
        return False
    return abs(tx_amount - due) / due <= pct


def _date_diff_days(date_a: str, date_b: str) -> int:
    """Calendar days between two YYYY-MM-DD strings."""
    da = _date.fromisoformat(date_a)
    db_ = _date.fromisoformat(date_b)
    return abs((da - db_).days)


def _before_or_after(tx_date: str, due_date: str) -> str:
    d_tx = _date.fromisoformat(tx_date)
    d_due = _date.fromisoformat(due_date)
    if d_tx < d_due:
        return "before"
    if d_tx > d_due:
        return "after"
    return "on"


def _fmt_gbp(amount: Decimal) -> str:
    return f"£{amount:,.2f}"


# ── Matching rules ────────────────────────────────────────────────────────────
# Each rule takes (invoice, normalised_tx) and returns MatchResult | None.
# Rules are listed in descending confidence order in MatchingEngine.

_CLOSE_PCT        = Decimal("0.005")  # 0.5 % for "close" amount rules
_APPROX_PCT       = Decimal("0.02")   # 2 %   for "approximate" rules
_DATE_PROXIMITY   = 7                 # days for normal date-proximity rules
_DATE_STRICT      = 2                 # days for strict date-proximity rules


def _rule_exact_amount_and_reference(invoice: Invoice, tx: dict) -> MatchResult | None:
    """
    100 % · MATCHED
    Exact amount AND invoice reference found in transaction text.
    The strongest possible deterministic match.
    """
    if not _amount_exact(tx["amount"], invoice.amount_due):
        return None
    if not _reference_in_text(invoice.reference, tx["_search_text"]):
        return None
    return MatchResult(
        invoice=invoice,
        transaction_ids=[tx["id"]] if tx["id"] is not None else [],
        status=MatchStatus.MATCHED,
        confidence=100,
        method="exact_amount_and_reference",
        explanation=(
            f"Exact amount ({_fmt_gbp(invoice.amount_due)}) and invoice reference "
            f"({invoice.reference}) both found in transaction."
        ),
        matched_amount=tx["amount"],
    )


def _rule_reference_and_close_amount(invoice: Invoice, tx: dict) -> MatchResult | None:
    """
    95 % · MATCHED
    Invoice reference found AND amount within 0.5% of invoice amount.
    Handles minor rounding or currency conversion artefacts.
    """
    if not _reference_in_text(invoice.reference, tx["_search_text"]):
        return None
    if not _amount_within_pct(tx["amount"], invoice.amount_due, _CLOSE_PCT):
        return None
    diff = abs(tx["amount"] - invoice.amount_due)
    return MatchResult(
        invoice=invoice,
        transaction_ids=[tx["id"]] if tx["id"] is not None else [],
        status=MatchStatus.MATCHED,
        confidence=95,
        method="reference_and_close_amount",
        explanation=(
            f"Invoice reference ({invoice.reference}) found. "
            f"Amount differs by {_fmt_gbp(diff)} (within 0.5%)."
        ),
        matched_amount=tx["amount"],
    )


def _rule_exact_amount_and_date(invoice: Invoice, tx: dict) -> MatchResult | None:
    """
    85 % · LIKELY_MATCH
    Exact amount AND received within DATE_PROXIMITY_DAYS of the due date.
    No reference match — user review recommended.
    """
    if not _amount_exact(tx["amount"], invoice.amount_due):
        return None
    days = _date_diff_days(tx["tx_date"], invoice.due_date)
    if days > _DATE_PROXIMITY:
        return None
    direction = _before_or_after(tx["tx_date"], invoice.due_date)
    day_word = "day" if days == 1 else "days"
    timing = f"{days} {day_word} {direction} the due date" if days else "on the due date"
    return MatchResult(
        invoice=invoice,
        transaction_ids=[tx["id"]] if tx["id"] is not None else [],
        status=MatchStatus.LIKELY_MATCH,
        confidence=85,
        method="exact_amount_and_date",
        explanation=(
            f"Exact amount ({_fmt_gbp(invoice.amount_due)}) received {timing}. "
            f"No reference found — review recommended."
        ),
        matched_amount=tx["amount"],
    )


def _rule_close_amount_and_date(invoice: Invoice, tx: dict) -> MatchResult | None:
    """
    74 % · LIKELY_MATCH
    Amount within 2% AND received within DATE_STRICT_DAYS of the due date.
    """
    if not _amount_within_pct(tx["amount"], invoice.amount_due, _APPROX_PCT):
        return None
    days = _date_diff_days(tx["tx_date"], invoice.due_date)
    if days > _DATE_STRICT:
        return None
    diff = abs(tx["amount"] - invoice.amount_due)
    direction = _before_or_after(tx["tx_date"], invoice.due_date)
    day_word = "day" if days == 1 else "days"
    timing = f"{days} {day_word} {direction} due date" if days else "on due date"
    return MatchResult(
        invoice=invoice,
        transaction_ids=[tx["id"]] if tx["id"] is not None else [],
        status=MatchStatus.LIKELY_MATCH,
        confidence=74,
        method="close_amount_and_date",
        explanation=(
            f"Amount matched within 2% (differs by {_fmt_gbp(diff)}). "
            f"Received {timing}."
        ),
        matched_amount=tx["amount"],
    )


def _rule_reference_only(invoice: Invoice, tx: dict) -> MatchResult | None:
    """
    60 % · LIKELY_MATCH
    Invoice reference found but amount does not match closely.
    Flags for user review — could be a deposit, credit note, or different invoice.
    """
    if not _reference_in_text(invoice.reference, tx["_search_text"]):
        return None
    # Only flag if the amount is at least 10% of the invoice — avoids noise
    if tx["amount"] < invoice.amount_due * Decimal("0.10"):
        return None
    diff = tx["amount"] - invoice.amount_due
    direction = "more" if diff > 0 else "less"
    return MatchResult(
        invoice=invoice,
        transaction_ids=[tx["id"]] if tx["id"] is not None else [],
        status=MatchStatus.LIKELY_MATCH,
        confidence=60,
        method="reference_only",
        explanation=(
            f"Invoice reference ({invoice.reference}) found but amount differs "
            f"by {_fmt_gbp(abs(diff))} ({direction} than invoiced). Review required."
        ),
        matched_amount=tx["amount"],
    )


# Ordered list — the engine tries them top-to-bottom and stops at the first hit
_SINGLE_TX_RULES = [
    _rule_exact_amount_and_reference,
    _rule_reference_and_close_amount,
    _rule_exact_amount_and_date,
    _rule_close_amount_and_date,
    _rule_reference_only,
]

# Minimum confidence to consider a single-tx match "strong" (MATCHED or LIKELY_MATCH)
_STRONG_MATCH_THRESHOLD = 60


# ── Aggregate rules ───────────────────────────────────────────────────────────

def _aggregate_multiple_payments(
    invoice: Invoice,
    candidates: list[dict],
) -> MatchResult | None:
    """
    90 % · MULTIPLE_PAYMENTS
    Check whether 2–5 transactions together sum exactly (±1%) to the invoice amount.

    To prevent false positives from random combinations of unrelated transactions
    that happen to sum to the invoice amount, at least ONE transaction in the winning
    combination must carry the invoice reference in its description or info text.

    Uses a brute-force combinations search — practical for small transaction sets.
    """
    from itertools import combinations

    target = invoice.amount_due
    tol = target * Decimal("0.01")   # 1 % tolerance

    # Only consider positive (incoming) transactions
    positives = [tx for tx in candidates if tx["amount"] > 0]

    # Try combinations of 2 up to min(5, len(positives))
    for r in range(2, min(6, len(positives) + 1)):
        for combo in combinations(positives, r):
            total = sum(tx["amount"] for tx in combo)
            if abs(total - target) <= tol:
                # ALL transactions in the combination must reference this invoice.
                # This prevents false positives: a combo like (deposit-with-reference,
                # unrelated-transaction) should not be treated as a multi-payment plan.
                if not all(_reference_in_text(invoice.reference, tx["_search_text"]) for tx in combo):
                    continue
                ids = [tx["id"] for tx in combo if tx["id"] is not None]
                amounts = ", ".join(_fmt_gbp(tx["amount"]) for tx in combo)
                return MatchResult(
                    invoice=invoice,
                    transaction_ids=ids,
                    status=MatchStatus.MULTIPLE_PAYMENTS,
                    confidence=90,
                    method="multiple_payments",
                    explanation=(
                        f"{len(combo)} payments ({amounts}) together total "
                        f"{_fmt_gbp(total)} against invoice of {_fmt_gbp(target)}."
                    ),
                    matched_amount=total,
                )
    return None


def _aggregate_underpaid(
    invoice: Invoice,
    candidates: list[dict],
) -> MatchResult | None:
    """
    75 % · UNDERPAID
    Two or more transactions all reference the invoice, but together they sum
    to less than the amount due (i.e. the client has made multiple payments but
    has still not settled the full balance).

    Distinguishes from PARTIAL_PAYMENT (one payment, more expected) by requiring
    ≥ 2 reference-matching transactions.  The sum must be at least 10 % of the
    invoice amount (to avoid noise from tiny unrelated reference matches).

    This aggregate is evaluated BEFORE _aggregate_partial_payment so that a pair
    of underpaying transactions is classified as UNDERPAID rather than the first
    one firing PARTIAL_PAYMENT on its own.
    """
    ref_txs = [
        tx for tx in candidates
        if _reference_in_text(invoice.reference, tx["_search_text"]) and tx["amount"] > 0
    ]
    if len(ref_txs) < 2:
        return None
    total = sum(tx["amount"] for tx in ref_txs)
    if total >= invoice.amount_due * Decimal("0.99"):
        # Close enough to be MULTIPLE_PAYMENTS — let that rule handle it
        return None
    if total < invoice.amount_due * Decimal("0.10"):
        return None
    remaining = invoice.amount_due - total
    pct = int(total / invoice.amount_due * 100)
    ids = [tx["id"] for tx in ref_txs if tx["id"] is not None]
    amounts = ", ".join(_fmt_gbp(tx["amount"]) for tx in ref_txs)
    return MatchResult(
        invoice=invoice,
        transaction_ids=ids,
        status=MatchStatus.UNDERPAID,
        confidence=75,
        method="underpaid",
        explanation=(
            f"{len(ref_txs)} payments ({amounts}) total {_fmt_gbp(total)} ({pct}%) "
            f"— {_fmt_gbp(remaining)} still outstanding. Reference ({invoice.reference}) matched."
        ),
        matched_amount=total,
    )


def _aggregate_partial_payment(
    invoice: Invoice,
    candidates: list[dict],
) -> MatchResult | None:
    """
    80 % · PARTIAL_PAYMENT
    One transaction partially settles the invoice (reference matches, amount < due).
    """
    for tx in candidates:
        if not _reference_in_text(invoice.reference, tx["_search_text"]):
            continue
        if tx["amount"] >= invoice.amount_due:
            continue
        if tx["amount"] <= 0:
            continue
        remaining = invoice.amount_due - tx["amount"]
        pct = int(tx["amount"] / invoice.amount_due * 100)
        return MatchResult(
            invoice=invoice,
            transaction_ids=[tx["id"]] if tx["id"] is not None else [],
            status=MatchStatus.PARTIAL_PAYMENT,
            confidence=80,
            method="partial_payment",
            explanation=(
                f"Partial payment of {_fmt_gbp(tx['amount'])} ({pct}%) received. "
                f"{_fmt_gbp(remaining)} still outstanding. Reference ({invoice.reference}) matched."
            ),
            matched_amount=tx["amount"],
        )
    return None


def _aggregate_overpaid(
    invoice: Invoice,
    candidates: list[dict],
) -> MatchResult | None:
    """
    90 % · OVERPAID
    Total received (across matched transactions with reference) exceeds the invoice amount.
    """
    matching_txs = [
        tx for tx in candidates
        if _reference_in_text(invoice.reference, tx["_search_text"]) and tx["amount"] > 0
    ]
    if not matching_txs:
        return None
    total = sum(tx["amount"] for tx in matching_txs)
    if total <= invoice.amount_due:
        return None
    excess = total - invoice.amount_due
    ids = [tx["id"] for tx in matching_txs if tx["id"] is not None]
    return MatchResult(
        invoice=invoice,
        transaction_ids=ids,
        status=MatchStatus.OVERPAID,
        confidence=90,
        method="overpaid",
        explanation=(
            f"Total received ({_fmt_gbp(total)}) exceeds invoice of "
            f"{_fmt_gbp(invoice.amount_due)} by {_fmt_gbp(excess)}. "
            f"Reference ({invoice.reference}) matched."
        ),
        matched_amount=total,
    )


# ── Engine ────────────────────────────────────────────────────────────────────

class MatchingEngine:
    """
    Deterministic, explainable invoice matching engine.

    Usage
    -----
    engine = MatchingEngine()
    result = engine.match(invoice, transactions)
    results = engine.match_all(invoices, transactions)

    Transactions
    ------------
    Each transaction dict must contain at minimum:
        id (int | None), tx_date (YYYY-MM-DD), description (str), amount (float | Decimal)
    It may also contain:
        transactionInformation (str), yapily_tx_id (str), currency (str)

    Both DB-fetched rows (with tx_date) and raw Yapily dicts (with date) are accepted.
    """

    def match(
        self,
        invoice: Invoice,
        transactions: Sequence[dict],
    ) -> MatchResult:
        """
        Match one invoice against a collection of transactions.

        Returns the single best MatchResult. If no match is found, returns a
        MatchResult with status=UNMATCHED, confidence=0.
        """
        # Normalise all transactions, then classify by currency.
        # Three outcomes per transaction:
        #   "ok"       — same currency as invoice; proceed to matching rules
        #   "mismatch" — different known currency; silently exclude
        #   "missing"  — either side blank; exclude from auto-matching but flag
        #                for user review if no other match is found
        normed: list[dict] = []
        has_missing_currency = False
        for t in transactions:
            tx = _normalise_tx(t)
            check = _currency_check(invoice.currency, tx["currency"])
            if check == "ok":
                normed.append(tx)
            elif check == "missing":
                has_missing_currency = True
            # check == "mismatch": silently excluded (different known currency)

        # ── Step 1: single-transaction matching ──────────────────────────────
        strong_hits: list[MatchResult] = []
        best: MatchResult | None = None

        for tx in normed:
            # Only consider positive amounts (incoming money)
            if tx["amount"] <= 0:
                continue
            for rule in _SINGLE_TX_RULES:
                result = rule(invoice, tx)
                if result is not None:
                    if result.confidence >= _STRONG_MATCH_THRESHOLD:
                        strong_hits.append(result)
                    break  # stop trying lower rules for this transaction

        # ── Classify hits by strength ─────────────────────────────────────────
        # A "full-payment candidate" can individually settle the invoice (≥ 80% of due).
        # Partial-amount hits (e.g. two £1,500 milestone payments against a £3,000
        # invoice) are NOT full-payment candidates; they go to the aggregate stage.
        full_payment_threshold = invoice.amount_due * Decimal("0.80")
        full_hits   = [r for r in strong_hits if r.matched_amount >= full_payment_threshold]
        low_hits    = [r for r in strong_hits if r.matched_amount <  full_payment_threshold]

        # MULTIPLE_MATCHES: ≥2 transactions each independently and confidently look like
        # the complete payment.  Only fires when ALL candidates have confidence ≥ 85 —
        # a lower-confidence secondary hit (e.g. 74 % close_amount_and_date) is not
        # treated as a genuine ambiguity; the higher-confidence primary simply wins.
        high_conf_full_hits = [r for r in full_hits if r.confidence >= 85]
        if len(high_conf_full_hits) > 1:
            all_ids = [ids for r in high_conf_full_hits for ids in r.transaction_ids]
            amounts = ", ".join(_fmt_gbp(r.matched_amount) for r in high_conf_full_hits)
            return MatchResult(
                invoice=invoice,
                transaction_ids=all_ids,
                status=MatchStatus.MULTIPLE_MATCHES,
                confidence=max(r.confidence for r in high_conf_full_hits),
                method="multiple_matches",
                explanation=(
                    f"{len(high_conf_full_hits)} transactions independently match this invoice "
                    f"(amounts: {amounts}). User review required."
                ),
                matched_amount=high_conf_full_hits[0].matched_amount,
            )

        # Exactly 1 high-confidence full-payment candidate → return it directly,
        # but only if it has confidence ≥ 74 (i.e., not just reference_only).
        # reference_only hits (60%) must still be checked against aggregates first
        # because partial_payment (80%) is more informative.
        best_full = max(full_hits, key=lambda r: r.confidence) if full_hits else None
        if best_full is not None and best_full.confidence >= 74:
            return best_full

        # ── Step 2: aggregate matching ────────────────────────────────────────
        # Run aggregates before falling back to any low-confidence single-tx hit.
        # This ensures PARTIAL_PAYMENT (80%) and MULTIPLE_PAYMENTS (90%) take
        # precedence over LIKELY_MATCH/reference_only (60%) when appropriate.
        pos_normed = [tx for tx in normed if tx["amount"] > 0]

        for agg_rule in [
            _aggregate_overpaid,
            _aggregate_multiple_payments,
            _aggregate_underpaid,      # must precede partial_payment (2+ txs < due)
            _aggregate_partial_payment,
        ]:
            result = agg_rule(invoice, pos_normed)
            if result is not None:
                return result

        # ── Step 3: fall back to best single-tx hit (if any) ─────────────────
        # A full_hit at 60% (reference_only, full amount) or any low_hit that
        # survived but was not superseded by an aggregate.
        if full_hits:
            return full_hits[0]
        if low_hits:
            return low_hits[0]

        # ── Step 4: no match ──────────────────────────────────────────────────
        # If we found no compatible match but some transactions had an unknown
        # currency, flag for user review instead of returning a plain UNMATCHED.
        # method="currency_missing" is the machine-readable reason the review
        # queue can filter on; the explanation is the user-facing message.
        if has_missing_currency:
            inv_ccy = (invoice.currency or "").strip() or "(not set)"
            return MatchResult(
                invoice=invoice,
                transaction_ids=[],
                status=MatchStatus.UNMATCHED,
                confidence=0,
                method="currency_missing",
                explanation=(
                    f"Currency could not be verified for one or more transactions "
                    f"(invoice currency: {inv_ccy}) — automatic matching was skipped. "
                    f"Manual review required."
                ),
                matched_amount=Decimal("0"),
            )

        return MatchResult(
            invoice=invoice,
            transaction_ids=[],
            status=MatchStatus.UNMATCHED,
            confidence=0,
            method="unmatched",
            explanation=(
                f"No transaction found matching {_fmt_gbp(invoice.amount_due)} "
                f"for invoice {invoice.reference}."
            ),
            matched_amount=Decimal("0"),
        )

    def match_all(
        self,
        invoices: Sequence[Invoice],
        transactions: Sequence[dict],
    ) -> list[MatchResult]:
        """
        Match every invoice against the shared transaction pool.

        Returns one MatchResult per invoice, in the same order as invoices.
        Transactions may be reused across multiple invoices (the engine does not
        consume them — that is a UI/persistence concern for future workstreams).
        """
        return [self.match(inv, transactions) for inv in invoices]
