"""
Yapily Hosted Pages — bank-connection provider.

Sandbox mode
────────────
Set YAPILY_APPLICATION_UUID and YAPILY_SECRET in Replit Secrets to enable
live/sandbox calls. When either secret is absent the client runs in MOCK mode:
every method returns fixture data and logs a clear warning. No credentials
are ever invented or hard-coded here.

Integration readiness
─────────────────────
Before activating with real secrets, complete the Yapily sandbox checklist
available at /v2/sandbox-checklist.

Hosted Pages flow (summary)
────────────────────────────
1. POST /institutions/{id}/consent  → returns a consent token + Hosted Pages URL
2. Redirect user to Hosted Pages URL (bank selects account, authorises)
3. Bank redirects user back to Reserved callback URL with consent token
4. GET  /accounts?consent={token}   → account list
5. GET  /transactions?consent={token} → transaction history
6. DELETE /consents/{consent_id}     → revoke (on disconnect)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from reserved.providers.readiness import PROVIDERS, assess_provider

log = logging.getLogger(__name__)

# ── Sandbox fixture data ──────────────────────────────────────────────────────

_MOCK_CONSENT_TOKEN = "mock-consent-token-abc123"

_MOCK_INSTITUTIONS: list[dict] = [
    {"id": "monzo",     "name": "Monzo",     "countries": [{"displayName": "United Kingdom"}], "media": []},
    {"id": "starling",  "name": "Starling",  "countries": [{"displayName": "United Kingdom"}], "media": []},
    {"id": "barclays",  "name": "Barclays",  "countries": [{"displayName": "United Kingdom"}], "media": []},
    {"id": "hsbc",      "name": "HSBC",      "countries": [{"displayName": "United Kingdom"}], "media": []},
    {"id": "lloyds",    "name": "Lloyds",    "countries": [{"displayName": "United Kingdom"}], "media": []},
    {"id": "natwest",   "name": "NatWest",   "countries": [{"displayName": "United Kingdom"}], "media": []},
    {"id": "revolut",   "name": "Revolut",   "countries": [{"displayName": "United Kingdom"}], "media": []},
    {"id": "chase",     "name": "Chase",     "countries": [{"displayName": "United Kingdom"}], "media": []},
]

_MOCK_ACCOUNTS: list[dict] = [
    {
        "id": "mock-account-001",
        "type": "CURRENT",
        "balance": 4821.55,
        "currency": "GBP",
        "nickname": "Personal account",
        "accountIdentifications": [{"type": "SORT_CODE", "identification": "204060"},
                                    {"type": "ACCOUNT_NUMBER", "identification": "12347821"}],
        "institution_id": "monzo",
    }
]

_MOCK_TRANSACTIONS: list[dict] = [
    {
        "id": "txn-001",
        "date": "2026-08-01",
        "amount": 4800.00,
        "currency": "GBP",
        "description": "DESIGN STUDIO LTD",
        "transactionInformation": "Invoice INV-2026-084",
        "proprietaryBankTransactionCode": "CREDIT",
        "status": "BOOKED",
    },
    {
        "id": "txn-002",
        "date": "2026-07-15",
        "amount": 2400.00,
        "currency": "GBP",
        "description": "ACME CORP",
        "transactionInformation": "Freelance July",
        "proprietaryBankTransactionCode": "CREDIT",
        "status": "BOOKED",
    },
    {
        "id": "txn-003",
        "date": "2026-07-03",
        "amount": 1200.00,
        "currency": "GBP",
        "description": "COFFEE CLIENT",
        "transactionInformation": "Consulting",
        "proprietaryBankTransactionCode": "CREDIT",
        "status": "BOOKED",
    },
]


# ── Consent state dataclass ───────────────────────────────────────────────────

@dataclass
class ConsentRecord:
    """Represents a stored consent for one bank account connection."""
    consent_token: str
    institution_id: str
    account_id: str
    account_nickname: str
    account_last4: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime | None = None
    status: str = "AUTHORIZED"   # AUTHORIZED | EXPIRED | REVOKED | AWAITING_AUTHORISATION

    @property
    def days_until_expiry(self) -> int | None:
        if not self.expires_at:
            return None
        delta = self.expires_at - datetime.now(timezone.utc)
        return max(0, delta.days)

    @property
    def is_expiring_soon(self) -> bool:
        d = self.days_until_expiry
        return d is not None and d <= 7

    @property
    def is_expired(self) -> bool:
        return self.status == "EXPIRED" or (
            self.expires_at is not None and datetime.now(timezone.utc) > self.expires_at
        )


# ── Client ────────────────────────────────────────────────────────────────────

class YapilyClient:
    """
    Sandbox-ready Yapily client.

    Runs in MOCK mode unless YAPILY_APPLICATION_UUID and YAPILY_SECRET are both
    present as environment secrets. In MOCK mode every method returns fixture
    data; no network calls are made and no credentials are required.

    Integration points (activated when secrets are present)
    ────────────────────────────────────────────────────────
    • self._post()  / self._get()  / self._delete()  — HTTP helpers (not yet
      implemented; wire to requests or httpx here).
    • Consent tokens must be stored server-side in the database, never in the
      browser session.
    • Webhook authenticity verification remains deliberately fail-closed until
      confirmed against the contracted Yapily product documentation.
    """

    YAPILY_BASE = "https://api.yapily.com"
    CONSENT_TTL_DAYS = 90   # most UK banks grant 90-day AIS consent

    def __init__(self) -> None:
        self._uuid   = os.environ.get("YAPILY_APPLICATION_UUID", "")
        self._secret = os.environ.get("YAPILY_SECRET", "")
        spec = next(item for item in PROVIDERS if item.name == "yapily")
        self.readiness = assess_provider(spec, os.environ)
        self.mock = not self.readiness.may_make_sandbox_calls
        if self.mock:
            log.warning(
                "YapilyClient disabled (%s) — running in fixture mode. "
                "No external data will be read.", self.readiness.state.value
            )

    # ── Institution catalogue ─────────────────────────────────────────────────

    def list_institutions(self) -> list[dict]:
        """Return the list of supported UK institutions.

        Live: GET /institutions?country=GB
        """
        if self.mock:
            return _MOCK_INSTITUTIONS
        raise NotImplementedError(  # replace with live HTTP call
            "Wire self._get('/institutions') here."
        )

    # ── Consent / Hosted Pages ────────────────────────────────────────────────

    def initiate_consent(
        self,
        institution_id: str,
        user_id: str,
        callback_url: str,
        state: str | None = None,
    ) -> dict:
        """
        Start the Hosted Pages authorisation flow for a given institution.

        Returns:
            {
                "consent_token":  str,   # opaque; store server-side
                "hosted_url":     str,   # redirect user here
                "expires_in":     int,   # seconds
            }

        Live: POST /account-auth-requests
        Body:
            {
                "applicationUserId": user_id,
                "institutionId": institution_id,
                "callback": callback_url,
                "oneTimeToken": false,
            }
        Headers: Basic auth with APPLICATION_UUID:SECRET (base64).
        """
        if self.mock:
            state_part = f"&state={state}" if state else ""
            return {
                "consent_token": _MOCK_CONSENT_TOKEN,
                "hosted_url": (
                    f"{callback_url}?consent={_MOCK_CONSENT_TOKEN}"
                    f"&institution={institution_id}&mock=1{state_part}"
                ),
                "expires_in": 300,
            }
        raise NotImplementedError("Wire self._post('/account-auth-requests') here.")

    def handle_callback(
        self,
        consent_token: str,
        institution_id: str,
    ) -> ConsentRecord:
        """
        Process the return from Hosted Pages and fetch the authorised account.

        Called from the /v2/yapily/callback route after the bank redirects back.

        Live steps:
            1. GET /accounts?consent={consent_token}
               → pick the first or only CURRENT account
            2. Build a ConsentRecord with expires_at = now + 90 days
            3. Persist the ConsentRecord to the database (not implemented yet)
        """
        if self.mock:
            acct = _MOCK_ACCOUNTS[0]
            last4 = (
                next(
                    (x["identification"][-4:]
                     for x in acct["accountIdentifications"]
                     if x["type"] == "ACCOUNT_NUMBER"),
                    "0000",
                )
            )
            return ConsentRecord(
                consent_token=consent_token,
                institution_id=institution_id,
                account_id=acct["id"],
                account_nickname=acct["nickname"],
                account_last4=last4,
                expires_at=datetime.now(timezone.utc) + timedelta(days=self.CONSENT_TTL_DAYS),
            )
        raise NotImplementedError("Wire GET /accounts here.")

    def validate_callback_signature(self, raw_body: bytes, signature_header: str) -> bool:
        """
        Fail closed until the current Yapily webhook authenticity contract is
        confirmed and implemented from official documentation.

        OAuth redirect callbacks are protected separately by the one-time
        application-generated state value in the route. They must not be
        treated as authenticated webhooks.
        """
        if self.mock:
            return True   # no validation needed against fixture data
        return False

    # ── Account and transaction access ───────────────────────────────────────

    def list_accounts(self, consent_token: str) -> list[dict]:
        """
        Return accounts visible under this consent.

        Live: GET /accounts?consent={consent_token}
        """
        if self.mock:
            return _MOCK_ACCOUNTS
        raise NotImplementedError("Wire GET /accounts here.")

    def list_transactions(
        self,
        consent_token: str,
        account_id: str,
        from_date: date | None = None,
    ) -> list[dict]:
        """
        Return transaction history for one account.

        Live: GET /accounts/{account_id}/transactions?consent={consent_token}
              &from={from_date:%Y-%m-%d}

        Pagination: Yapily returns a 'next' cursor; loop until exhausted for
        initial sync. Incremental syncs use the last-seen transaction date.
        """
        if self.mock:
            return _MOCK_TRANSACTIONS
        raise NotImplementedError("Wire GET /accounts/{id}/transactions here.")

    def check_consent_status(self, consent_token: str) -> str:
        """
        Return the live status of a stored consent.

        Live: GET /consents/{consent_token}
        Returns one of: AUTHORIZED | EXPIRED | REVOKED | AWAITING_AUTHORISATION
        """
        if self.mock:
            return "AUTHORIZED"
        raise NotImplementedError("Wire GET /consents/{token} here.")

    def revoke_consent(self, consent_token: str) -> bool:
        """
        Revoke a consent and delete all associated data.

        Called on disconnect. Returns True on success.

        Live: DELETE /consents/{consent_token}
        Also: delete stored ConsentRecord and transactions from the database.
        """
        if self.mock:
            log.info("MOCK: consent %s revoked", consent_token[:12])
            return True
        raise NotImplementedError("Wire DELETE /consents/{token} here.")

    # ── Webhook handling ──────────────────────────────────────────────────────

    def handle_webhook(self, raw_body: bytes, signature_header: str) -> dict:
        """
        Process an inbound Yapily webhook notification.

        Event names and authenticity verification must be mapped from the
        currently contracted Yapily product documentation before activation.
        Never infer either from fixture behaviour.

        Always authenticate the notification before processing.
        Webhook idempotency: record the event ID; skip if already processed.
        """
        if not self.validate_callback_signature(raw_body, signature_header):
            return {"ok": False, "error": "invalid_signature"}
        if self.mock:
            return {"ok": True, "mock": True}
        raise NotImplementedError("Parse raw_body JSON and dispatch by event type.")
