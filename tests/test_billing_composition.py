"""Application-factory checks for the fail-closed injected billing boundary."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

import reserved.database as db
from reserved import create_app
from reserved.auth import _SK_USER_ID
from reserved.billing import stripe_runtime as subject
from reserved.billing.paid_access_guard import PAID_ENDPOINTS
from reserved.billing.stripe_runtime import (
    HostedUrlPolicy,
    PriceBinding,
    SQLiteBillingRuntimeRepository,
    StripeBillingRuntime,
    Transition,
)


NOW = 1_800_000_000


class Provider:
    def create_checkout(self, **kwargs):
        return "https://checkout.example.test/session"

    def create_portal(self, **kwargs):
        return "https://portal.example.test/session"


class Reconciler:
    def reconcile(self, *, event, owner_id, billing_account_id, prior_state):
        if event["type"] != "invoice.paid" or prior_state is not None:
            return None
        return Transition(
            owner_id, billing_account_id, "sub_composition", "paid",
            event["id"], event["created"], "verified_payment_reconciled",
            "initial_payment", paid_until=NOW + 31 * 24 * 60 * 60,
            payment_identity="pi_composition",
        )


def runtime(tmp_path):
    verifier = lambda raw, signature: signature == "sig=" + hmac.new(
        b"composition-key", raw, hashlib.sha256
    ).hexdigest()
    return StripeBillingRuntime(
        SQLiteBillingRuntimeRepository(tmp_path / "billing.db"), Provider(), verifier,
        Reconciler(), (
            PriceBinding("monthly", "price_monthly", "GBP", 999, "month", 1),
            PriceBinding("six_month", "price_six_month", "GBP", 1999, "month", 6),
            PriceBinding("yearly", "price_yearly", "GBP", 499, "year", 1),
        ), HostedUrlPolicy(("checkout.example.test",), ("portal.example.test",)),
        clock=lambda: datetime.fromtimestamp(NOW, timezone.utc),
    )


def app_factory(tmp_path, monkeypatch, *, billing_runtime=None, production=False):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "app.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "production" if production else "development")
    if production:
        monkeypatch.setenv("SESSION_SECRET", "synthetic-production-secret-for-tests")
    monkeypatch.setenv("MTD_MANUAL_SCOPE_ENABLED", "1")
    app = create_app(billing_runtime=billing_runtime)
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return app


def login(app):
    owner = db.get_or_create_user("billing-composition-owner", email="owner@example.test")
    client = app.test_client()
    with client.session_transaction() as session:
        session[_SK_USER_ID] = owner
    return client, owner


def paid_event(runtime, owner):
    account = runtime.repository.account_for(owner)
    event = {
        "id": "evt_composition_paid", "created": NOW, "type": "invoice.paid",
        "data": {"object": {"metadata": {
            "reserved_owner_id": str(owner),
            "reserved_billing_account_id": account,
        }}},
    }
    raw = json.dumps(event, separators=(",", ":")).encode()
    signature = "sig=" + hmac.new(b"composition-key", raw, hashlib.sha256).hexdigest()
    assert runtime.webhook(raw, signature) == "reconciled"


def test_absent_runtime_keeps_billing_and_enabled_paid_feature_unavailable(tmp_path, monkeypatch):
    app = app_factory(tmp_path, monkeypatch, production=True)
    client, _ = login(app)
    assert client.post("/v2/billing/checkout", json={"plan_key": "monthly"},
                       headers={"Idempotency-Key": "x" * 16}).status_code == 404
    assert client.post("/v2/billing/portal", headers={"Idempotency-Key": "x" * 16}).status_code == 404
    assert client.post("/v2/billing/webhook", data=b"{}").status_code == 404
    assert client.get("/v2/mtd/scope-indication").status_code == 404


def test_partial_or_invalid_injection_is_closed_not_implicitly_composed(tmp_path, monkeypatch):
    app = app_factory(tmp_path, monkeypatch, billing_runtime=object())
    client, _ = login(app)
    assert client.post("/v2/billing/checkout", json={"plan_key": "monthly"},
                       headers={"Idempotency-Key": "x" * 16}).status_code == 404
    assert client.get("/v2/mtd/scope-indication").status_code == 404


def test_complete_injected_runtime_exposes_billing_and_guards_every_paid_route(tmp_path, monkeypatch):
    live = runtime(tmp_path)
    app = app_factory(tmp_path, monkeypatch, billing_runtime=live)
    client, owner = login(app)
    assert "billing" in app.blueprints
    originals = app.extensions["reserved.billing.stripe_runtime.paid_surface.disabled"]
    expected = tuple(endpoint for endpoint in PAID_ENDPOINTS if not endpoint.startswith("hicbc."))
    assert set(originals) == set(expected)
    assert all(
        getattr(app.view_functions[endpoint], "__wrapped__", None) is originals[endpoint]
        for endpoint in expected
    )
    assert client.post("/v2/billing/checkout", json={"plan_key": "monthly"},
                       headers={"Idempotency-Key": "x" * 16}).status_code == 201
    assert client.get("/v2/mtd/scope-indication").status_code == 403
    paid_event(live, owner)
    assert client.get("/v2/mtd/scope-indication").status_code == 200


def test_installation_failure_leaves_only_the_closed_boundary(tmp_path, monkeypatch):
    def fail(app, runtime):
        raise RuntimeError("synthetic composition failure")

    monkeypatch.setattr(subject, "install_stripe_billing_runtime", fail)
    app = app_factory(tmp_path, monkeypatch, billing_runtime=runtime(tmp_path))
    client, _ = login(app)
    assert "billing" not in app.blueprints
    assert "reserved.billing.stripe_runtime" not in app.extensions
    assert client.post("/v2/billing/webhook", data=b"{}").status_code == 404
    assert client.get("/v2/mtd/scope-indication").status_code == 404
