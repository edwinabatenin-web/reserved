"""Production-shaped MTD boundary tests using the real local billing runtime."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

import reserved.database as db
from reserved import create_app
from reserved.auth import _SK_USER_ID
from reserved.billing.stripe_runtime import (
    HostedUrlPolicy,
    PriceBinding,
    SQLiteBillingRuntimeRepository,
    StripeBillingRuntime,
    Transition,
    install_stripe_billing_runtime,
)


NOW = 1_800_000_000
URL = "/v2/mtd/scope-indication"


class _NoNetworkProvider:
    def create_checkout(self, **kwargs):
        raise AssertionError("production-boundary test must not call a provider")

    def create_portal(self, **kwargs):
        raise AssertionError("production-boundary test must not call a provider")


class _PaidEventReconciler:
    def reconcile(self, *, event, owner_id, billing_account_id, prior_state):
        if event["type"] != "invoice.paid" or prior_state is not None:
            return None
        return Transition(
            owner_id,
            billing_account_id,
            "sub_mtd_boundary",
            "paid",
            event["id"],
            event["created"],
            "verified_payment_reconciled",
            "initial_payment",
            paid_until=NOW + 31 * 24 * 60 * 60,
            payment_identity="pi_mtd_boundary",
        )


def _runtime(tmp_path):
    verifier = lambda raw, signature: signature == "sig=" + hmac.new(
        b"mtd-boundary-key", raw, hashlib.sha256
    ).hexdigest()
    return StripeBillingRuntime(
        SQLiteBillingRuntimeRepository(tmp_path / "billing.db"),
        _NoNetworkProvider(),
        verifier,
        _PaidEventReconciler(),
        (
            PriceBinding("monthly", "price_monthly", "GBP", 999, "month", 1),
            PriceBinding("six_month", "price_six_month", "GBP", 1999, "month", 6),
            PriceBinding("yearly", "price_yearly", "GBP", 499, "year", 1),
        ),
        HostedUrlPolicy(("checkout.example.test",), ("portal.example.test",)),
        clock=lambda: datetime.fromtimestamp(NOW, timezone.utc),
    )


def _production_app(tmp_path, monkeypatch, *, enabled):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "app.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "mtd-production-boundary-test-secret")
    if enabled:
        monkeypatch.setenv("MTD_MANUAL_SCOPE_ENABLED", "1")
    else:
        monkeypatch.delenv("MTD_MANUAL_SCOPE_ENABLED", raising=False)
    app = create_app()
    app.config.update(TESTING=True, SECRET_KEY="mtd-production-boundary-test-secret")
    runtime = _runtime(tmp_path)
    install_stripe_billing_runtime(app, runtime)
    owner_id = db.get_or_create_user("mtd-production-owner", email="owner@example.test")
    client = app.test_client()
    with client.session_transaction() as session:
        session[_SK_USER_ID] = owner_id
    return client, runtime, owner_id


def _admit_paid_event(runtime, owner_id):
    account = runtime.repository.account_for(owner_id)
    event = {
        "id": "evt_mtd_paid",
        "created": NOW,
        "type": "invoice.paid",
        "data": {"object": {"metadata": {
            "reserved_owner_id": str(owner_id),
            "reserved_billing_account_id": account,
        }}},
    }
    raw = json.dumps(event, separators=(",", ":")).encode()
    signature = "sig=" + hmac.new(b"mtd-boundary-key", raw, hashlib.sha256).hexdigest()
    assert runtime.webhook(raw, signature) == "reconciled"


def test_production_shaped_mtd_requires_exact_flag_and_paid_owner(tmp_path, monkeypatch):
    client, runtime, owner_id = _production_app(tmp_path, monkeypatch, enabled=True)
    assert client.get(URL).status_code == 403
    _admit_paid_event(runtime, owner_id)
    response = client.get(URL)
    assert response.status_code == 200
    assert "Making Tax Digital" in response.get_data(as_text=True)


def test_production_shaped_paid_owner_cannot_enable_mtd_without_flag(tmp_path, monkeypatch):
    client, runtime, owner_id = _production_app(tmp_path, monkeypatch, enabled=False)
    _admit_paid_event(runtime, owner_id)
    assert client.get(URL).status_code == 404
