"""Focused real-request tests for the disabled-first Stripe runtime wiring."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

import pytest
from flask import Flask

import reserved.database as db
from reserved import create_app
from reserved.billing.stripe_runtime import (
    BillingRuntimeError,
    HostedUrlPolicy,
    SQLiteBillingRuntimeRepository,
    PriceBinding,
    StripeBillingRuntime,
    Transition,
    install_stripe_billing_runtime,
)


class Provider:
    def __init__(self):
        self.calls = []

    def create_checkout(self, **kwargs):
        self.calls.append(("checkout", kwargs))
        return "https://checkout.example.test/session-" + kwargs["plan_key"]

    def create_portal(self, **kwargs):
        self.calls.append(("portal", kwargs))
        return "https://portal.example.test/session"


class Reconciler:
    def reconcile(self, *, event, owner_id, billing_account_id, prior_state):
        kind = event["type"]
        if kind == "invoice.paid":
            state, reason, transition_kind = "paid", "verified_payment_reconciled", "initial_payment" if prior_state is None else "renewal_payment"
            return Transition(owner_id, billing_account_id, "sub_test", state,
                              event["id"], event["created"], reason, transition_kind,
                              paid_until=event["created"] + (31 * 24 * 60 * 60), payment_identity="pi_test")
        elif kind == "invoice.payment_failed":
            state, reason, transition_kind = "payment_recovery", "verified_failure_reconciled", "failed_renewal"
        elif kind == "charge.refunded":
            return Transition(owner_id, billing_account_id, "sub_test", "suspended",
                              event["id"], event["created"], "verified_full_withdrawal_reconciled", "full_withdrawal",
                              payment_identity="pi_test", withdrawal_attribution="current_period")
        elif kind == "customer.subscription.updated" and prior_state in {"paid", "payment_recovery"}:
            return Transition(owner_id, billing_account_id, "sub_test", prior_state,
                              event["id"], event["created"], "verified_scheduled_cancellation", "cancellation",
                              cancel_at_period_end=True)
        else:
            return None
        return Transition(owner_id, billing_account_id, "sub_test", state,
                          event["id"], event["created"], reason, transition_kind)


def _signed(payload: dict):
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return raw, "sig=" + hmac.new(b"test-signing-key", raw, hashlib.sha256).hexdigest()


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "app.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return application


def _login(client):
    assert client.get("/v2/demo-login").status_code == 302


def _runtime(tmp_path, clock=None):
    provider = Provider()
    verifier = lambda raw, header: header == "sig=" + hmac.new(
        b"test-signing-key", raw, hashlib.sha256).hexdigest()
    return StripeBillingRuntime(
        SQLiteBillingRuntimeRepository(tmp_path / "billing.db"), provider, verifier,
        Reconciler(), (
            PriceBinding("monthly", "price_monthly", "GBP", 2900, "month", 1),
            PriceBinding("six_month", "price_six_month", "GBP", 15600, "month", 6),
            PriceBinding("yearly", "price_yearly", "GBP", 28800, "year", 1),
        ), HostedUrlPolicy(("checkout.example.test",), ("portal.example.test",)),
        clock=clock or (lambda: datetime.now(timezone.utc)),
    ), provider


def test_default_routes_are_truthfully_disabled_and_do_not_contact_a_provider(app):
    client = app.test_client()
    _login(client)
    response = client.post("/v2/billing/checkout", json={"plan_key": "monthly"}, headers={"Idempotency-Key": "x" * 16})
    assert response.status_code == 404
    assert client.post("/v2/billing/webhook", data=b"{}", headers={"Stripe-Signature": "anything"}).status_code == 404


def test_installation_preflight_leaves_no_partial_billing_runtime_without_paid_targets(tmp_path):
    incomplete = Flask(__name__)
    runtime, _ = _runtime(tmp_path)
    with pytest.raises(BillingRuntimeError, match="paid endpoints"):
        install_stripe_billing_runtime(incomplete, runtime)
    assert "billing" not in incomplete.blueprints
    assert "reserved.billing.stripe_runtime" not in incomplete.extensions
    assert "reserved.billing.stripe_runtime.paid_surface" not in incomplete.extensions
    assert not any(rule.rule.startswith("/v2/billing/") for rule in incomplete.url_map.iter_rules())


def test_installation_rejects_one_missing_settled_paid_endpoint_without_partial_activation(app, tmp_path):
    app.view_functions.pop("v2.mtd_manual_scope")
    runtime, _ = _runtime(tmp_path)
    with pytest.raises(BillingRuntimeError, match="incomplete"):
        install_stripe_billing_runtime(app, runtime)
    assert "billing" not in app.blueprints
    assert "reserved.billing.stripe_runtime" not in app.extensions
    assert "reserved.billing.stripe_runtime.paid_surface" not in app.extensions


def test_installation_rejects_billing_endpoint_collision_before_any_mutation(app, tmp_path):
    app.add_url_rule("/synthetic-collision", endpoint="billing.checkout", view_func=lambda: "collision")
    runtime, _ = _runtime(tmp_path)
    before_rules = tuple((rule.rule, rule.endpoint) for rule in app.url_map.iter_rules())
    with pytest.raises(BillingRuntimeError, match="collision"):
        install_stripe_billing_runtime(app, runtime)
    assert tuple((rule.rule, rule.endpoint) for rule in app.url_map.iter_rules()) == before_rules
    assert "billing" not in app.blueprints
    assert "reserved.billing.stripe_runtime" not in app.extensions
    assert "reserved.billing.stripe_runtime.paid_surface" not in app.extensions


def test_incomplete_price_or_signature_configuration_cannot_create_a_runtime(tmp_path):
    provider = Provider()
    with pytest.raises(BillingRuntimeError, match="complete price"):
        StripeBillingRuntime(SQLiteBillingRuntimeRepository(tmp_path / "billing.db"), provider,
                             lambda *_: True, Reconciler(), (PriceBinding("monthly", "price_monthly", "GBP", 2900, "month", 1),),
                             HostedUrlPolicy(("checkout.example.test",), ("portal.example.test",)))


@pytest.mark.parametrize("bad", [
    PriceBinding("monthly", "price_monthly", "USD", 2900, "month", 1),
    PriceBinding("monthly", "price_monthly", "GBP", 2901, "month", 1),
    PriceBinding("monthly", "price_monthly", "GBP", 2900, "year", 1),
    PriceBinding("monthly", "price_monthly", "GBP", 2900, "month", 2),
])
def test_price_binding_rejects_wrong_currency_amount_or_period(tmp_path, bad):
    bindings = (bad, PriceBinding("six_month", "price_six_month", "GBP", 15600, "month", 6),
                PriceBinding("yearly", "price_yearly", "GBP", 28800, "year", 1))
    with pytest.raises(BillingRuntimeError):
        StripeBillingRuntime(SQLiteBillingRuntimeRepository(tmp_path / "billing.db"), Provider(), lambda *_: True, Reconciler(), bindings,
                             HostedUrlPolicy(("checkout.example.test",), ("portal.example.test",)))


def test_price_binding_rejects_duplicate_provider_price_id(tmp_path):
    bindings = (PriceBinding("monthly", "price_duplicate", "GBP", 2900, "month", 1),
                PriceBinding("six_month", "price_duplicate", "GBP", 15600, "month", 6),
                PriceBinding("yearly", "price_yearly", "GBP", 28800, "year", 1))
    with pytest.raises(BillingRuntimeError):
        StripeBillingRuntime(SQLiteBillingRuntimeRepository(tmp_path / "billing.db"), Provider(), lambda *_: True, Reconciler(), bindings,
                             HostedUrlPolicy(("checkout.example.test",), ("portal.example.test",)))


def test_checkout_and_portal_are_owner_bound_and_idempotent(app, tmp_path):
    runtime, provider = _runtime(tmp_path)
    install_stripe_billing_runtime(app, runtime)
    client = app.test_client()
    _login(client)
    headers = {"Idempotency-Key": "checkout-key-0001"}
    first = client.post("/v2/billing/checkout", json={"plan_key": "monthly"}, headers=headers)
    duplicate = client.post("/v2/billing/checkout", json={"plan_key": "monthly"}, headers=headers)
    assert first.status_code == duplicate.status_code == 201
    assert first.json == duplicate.json
    assert provider.calls == [("checkout", provider.calls[0][1])]
    assert provider.calls[0][1]["plan_key"] == "monthly"
    assert provider.calls[0][1]["price_id"] == "price_monthly"
    assert client.post("/v2/billing/checkout", json={"plan_key": "yearly"}, headers=headers).status_code == 409
    portal = client.post("/v2/billing/portal", headers={"Idempotency-Key": "portal-key-000001"})
    assert portal.status_code == 201 and portal.json["status"] == "portal_created"


def test_durable_request_reservation_reuses_the_same_provider_idempotency_key_after_crash(tmp_path):
    repository = SQLiteBillingRuntimeRepository(tmp_path / "billing.db")
    calls = []
    def crash(provider_key):
        calls.append(provider_key)
        raise RuntimeError("process interrupted after provider request")
    with pytest.raises(RuntimeError):
        repository.request_result(1, "checkout", "crash-retry-key-01", "monthly", crash,
                                  allowed_hosts=("checkout.example.test",))
    result = repository.request_result(1, "checkout", "crash-retry-key-01", "monthly",
                                       lambda provider_key: calls.append(provider_key) or "https://checkout.example.test/recovered",
                                       allowed_hosts=("checkout.example.test",))
    assert result == "https://checkout.example.test/recovered"
    assert calls[0] == calls[1] and calls[0].startswith("reserved-")


def test_provider_idempotency_is_owner_operation_and_plan_bound(tmp_path):
    repository = SQLiteBillingRuntimeRepository(tmp_path / "billing.db")
    keys = []

    def create(provider_key):
        keys.append(provider_key)
        return "https://checkout.example.test/" + provider_key

    first = repository.request_result(1, "checkout", "shared-client-key", "monthly", create,
                                      allowed_hosts=("checkout.example.test",))
    second = repository.request_result(2, "checkout", "shared-client-key", "monthly", create,
                                       allowed_hosts=("checkout.example.test",))
    portal = repository.request_result(1, "portal", "shared-client-key", None, create,
                                       allowed_hosts=("checkout.example.test",))

    assert len(set(keys)) == 3
    assert len({first, second, portal}) == 3
    assert all(key.startswith("reserved-") for key in keys)


@pytest.mark.parametrize("invalid_owner", [0, -1, True, "1"])
def test_request_reservation_rejects_invalid_owner(tmp_path, invalid_owner):
    repository = SQLiteBillingRuntimeRepository(tmp_path / "billing.db")
    with pytest.raises(BillingRuntimeError, match="authenticated owner"):
        repository.request_result(invalid_owner, "checkout", "shared-client-key", "monthly",
                                  lambda key: "https://checkout.example.test/" + key,
                                  allowed_hosts=("checkout.example.test",))


@pytest.mark.parametrize("hostile", [
    "http://checkout.example.test/session",
    "https://evil.example.test/session",
    "https://checkout.example.test.evil.example/session",
    "https://user@checkout.example.test/session",
    "https://checkout.example.test:443/session",
    "https://checkout.example.test/session#redirect",
    "https://checkout.example.test\\@evil.example/session",
])
def test_provider_hosted_url_is_restricted_to_exact_reviewed_origin(tmp_path, hostile):
    repository = SQLiteBillingRuntimeRepository(tmp_path / "billing.db")
    with pytest.raises(BillingRuntimeError, match="invalid hosted URL"):
        repository.request_result(1, "checkout", "hostile-url-key-01", "monthly",
                                  lambda _: hostile, allowed_hosts=("checkout.example.test",))


def test_cached_hosted_url_is_revalidated_when_provider_policy_changes(tmp_path):
    repository = SQLiteBillingRuntimeRepository(tmp_path / "billing.db")
    assert repository.request_result(
        1, "checkout", "policy-change-key", "monthly",
        lambda _: "https://checkout.example.test/session",
        allowed_hosts=("checkout.example.test",),
    ) == "https://checkout.example.test/session"
    with pytest.raises(BillingRuntimeError, match="invalid hosted URL"):
        repository.request_result(
            1, "checkout", "policy-change-key", "monthly",
            lambda _: pytest.fail("completed request must not contact provider"),
            allowed_hosts=("replacement.example.test",),
        )


def test_verified_event_requires_owner_binding_is_replay_safe_and_does_not_grant_without_reconciler(app, tmp_path):
    runtime, _ = _runtime(tmp_path)
    install_stripe_billing_runtime(app, runtime)
    client = app.test_client()
    _login(client)
    account = runtime.repository.account_for(1)
    now = int(datetime.now(timezone.utc).timestamp())
    pending = {"id": "evt_pending", "created": now, "type": "customer.updated", "data": {"object": {"metadata": {"reserved_owner_id": "1", "reserved_billing_account_id": account}}}}
    raw, signature = _signed(pending)
    assert client.post("/v2/billing/webhook", data=raw, headers={"Stripe-Signature": signature}).json == {"status": "recorded_pending_reconciliation"}
    assert client.get("/v2/billing/status").json == {"state": "no_entitlement", "ordinary_access": "false"}
    paid = {**pending, "id": "evt_paid", "created": now + 1, "type": "invoice.paid"}
    raw, signature = _signed(paid)
    assert client.post("/v2/billing/webhook", data=raw, headers={"Stripe-Signature": signature}).json == {"status": "reconciled"}
    assert client.get("/v2/billing/status").json == {"state": "paid", "ordinary_access": "true"}
    assert client.post("/v2/billing/webhook", data=raw, headers={"Stripe-Signature": signature}).json == {"status": "duplicate"}
    stale = {**paid, "id": "evt_stale", "created": now}
    raw, signature = _signed(stale)
    assert client.post("/v2/billing/webhook", data=raw, headers={"Stripe-Signature": signature}).status_code == 400


def test_invalid_signature_and_cross_owner_event_are_rejected_before_entitlement(app, tmp_path):
    runtime, _ = _runtime(tmp_path)
    install_stripe_billing_runtime(app, runtime)
    client = app.test_client()
    _login(client)
    assert client.post("/v2/billing/webhook", data=b"{}", headers={"Stripe-Signature": "not-valid"}).status_code == 400
    raw, signature = _signed({"id": "evt_cross", "created": 1, "type": "invoice.paid", "data": {"object": {"metadata": {"reserved_owner_id": "2", "reserved_billing_account_id": "billing-account-anything"}}}})
    assert client.post("/v2/billing/webhook", data=raw, headers={"Stripe-Signature": signature}).status_code == 400
    assert client.get("/v2/billing/status").json == {"state": "no_entitlement", "ordinary_access": "false"}


def test_recovery_deadline_is_fixed_at_first_failure_and_expires_without_another_event(tmp_path):
    runtime, _ = _runtime(tmp_path)
    account = runtime.repository.account_for(1)
    base = int(datetime.now(timezone.utc).timestamp()) - 100

    def event(event_id, created, kind):
        return {"id": event_id, "created": created, "type": kind,
                "data": {"object": {"metadata": {"reserved_owner_id": "1", "reserved_billing_account_id": account}}}}

    for value in (event("evt_paid", base, "invoice.paid"), event("evt_fail_one", base + 1, "invoice.payment_failed"), event("evt_fail_two", base + 2, "invoice.payment_failed")):
        raw, signature = _signed(value)
        assert runtime.webhook(raw, signature) == "reconciled"
    deadline = base + 1 + (7 * 24 * 60 * 60)
    assert runtime.repository.status_for(1, now_epoch=deadline - 1) == {"state": "payment_recovery", "ordinary_access": "true"}
    assert runtime.repository.status_for(1, now_epoch=deadline) == {"state": "suspended", "ordinary_access": "false"}
    recovered = event("evt_recovered", base + 3, "invoice.paid")
    raw, signature = _signed(recovered)
    assert runtime.webhook(raw, signature) == "reconciled"
    assert runtime.repository.status_for(1, now_epoch=deadline + 1) == {"state": "paid", "ordinary_access": "true"}


def test_failed_renewal_at_paid_until_has_recovery_access_through_its_own_deadline(tmp_path):
    base = 1_700_000_000
    current = [base]
    runtime, _ = _runtime(tmp_path, clock=lambda: datetime.fromtimestamp(current[0], timezone.utc))
    account = runtime.repository.account_for(1)
    def event(event_id, created, kind):
        return {"id": event_id, "created": created, "type": kind,
                "data": {"object": {"metadata": {"reserved_owner_id": "1", "reserved_billing_account_id": account}}}}
    raw, signature = _signed(event("evt_paid", base, "invoice.paid"))
    assert runtime.webhook(raw, signature) == "reconciled"
    paid_until = base + 31 * 24 * 60 * 60
    current[0] = paid_until
    raw, signature = _signed(event("evt_failed_at_boundary", paid_until, "invoice.payment_failed"))
    assert runtime.webhook(raw, signature) == "reconciled"
    deadline = paid_until + 7 * 24 * 60 * 60
    assert runtime.repository.status_for(1, now_epoch=paid_until) == {"state": "payment_recovery", "ordinary_access": "true"}
    assert runtime.repository.status_for(1, now_epoch=deadline - 1) == {"state": "payment_recovery", "ordinary_access": "true"}
    assert runtime.repository.status_for(1, now_epoch=deadline) == {"state": "suspended", "ordinary_access": "false"}


def test_recovery_created_before_deadline_but_admitted_after_deadline_cannot_restore_access(tmp_path):
    base = 1_700_000_000
    current = [base]
    runtime, _ = _runtime(tmp_path, clock=lambda: datetime.fromtimestamp(current[0], timezone.utc))
    account = runtime.repository.account_for(1)
    def event(event_id, created, kind):
        return {"id": event_id, "created": created, "type": kind,
                "data": {"object": {"metadata": {"reserved_owner_id": "1", "reserved_billing_account_id": account}}}}
    for value in (event("evt_paid", base, "invoice.paid"), event("evt_failed", base + 1, "invoice.payment_failed")):
        current[0] = value["created"]
        raw, signature = _signed(value)
        assert runtime.webhook(raw, signature) == "reconciled"
    deadline = base + 1 + 7 * 24 * 60 * 60
    current[0] = deadline
    raw, signature = _signed(event("evt_late_recovery", deadline - 1, "invoice.paid"))
    with pytest.raises(BillingRuntimeError, match="post-deadline"):
        runtime.webhook(raw, signature)
    assert runtime.status(1) == {"state": "suspended", "ordinary_access": "false"}


def test_cancellation_retains_access_only_to_the_existing_paid_boundary_and_wrong_withdrawal_is_refused(tmp_path):
    runtime, _ = _runtime(tmp_path)
    account = runtime.repository.account_for(1)
    now = int(datetime.now(timezone.utc).timestamp())
    def event(event_id, created, kind):
        return {"id": event_id, "created": created, "type": kind,
                "data": {"object": {"metadata": {"reserved_owner_id": "1", "reserved_billing_account_id": account}}}}
    for value in (event("evt_paid", now, "invoice.paid"), event("evt_cancel", now + 1, "customer.subscription.updated")):
        raw, signature = _signed(value)
        assert runtime.webhook(raw, signature) == "reconciled"
    assert runtime.repository.status_for(1, now_epoch=now + 30 * 24 * 60 * 60)["ordinary_access"] == "true"
    assert runtime.repository.status_for(1, now_epoch=now + 31 * 24 * 60 * 60)["ordinary_access"] == "false"
    # The stock reconciler emits a current-period payment identity.  A hostile
    # reconciler cannot suspend with an old/other period payment identity.
    class OtherPeriod(Reconciler):
        def reconcile(self, **kwargs):
            value = super().reconcile(**kwargs)
            if value and value.kind == "full_withdrawal":
                return Transition(value.owner_id, value.billing_account_id, value.subscription_id, value.state,
                                  value.event_id, value.occurred_at, value.reason, value.kind,
                                  payment_identity="pi_other", withdrawal_attribution="other_period")
            return value
    hostile = StripeBillingRuntime(runtime.repository, Provider(), runtime.verify_signature, OtherPeriod(),
                                   runtime.price_bindings, runtime.hosted_url_policy)
    raw, signature = _signed(event("evt_wrong_refund", now + 2, "charge.refunded"))
    with pytest.raises(BillingRuntimeError):
        hostile.webhook(raw, signature)


def test_hostile_reconciler_cannot_mislabel_initial_failure_or_cross_subscription_cancellation(tmp_path):
    now = int(datetime.now(timezone.utc).timestamp())
    class WrongInitial(Reconciler):
        def reconcile(self, **kwargs):
            value = super().reconcile(**kwargs)
            return Transition(value.owner_id, value.billing_account_id, value.subscription_id, "payment_recovery",
                              value.event_id, value.occurred_at, value.reason, "initial_payment",
                              paid_until=value.paid_until, payment_identity=value.payment_identity)
    runtime, _ = _runtime(tmp_path)
    bad = StripeBillingRuntime(runtime.repository, Provider(), runtime.verify_signature, WrongInitial(),
                               runtime.price_bindings, runtime.hosted_url_policy)
    account = runtime.repository.account_for(1)
    event = {"id": "evt_bad_initial", "created": now, "type": "invoice.paid", "data": {"object": {"metadata": {"reserved_owner_id": "1", "reserved_billing_account_id": account}}}}
    raw, signature = _signed(event)
    with pytest.raises(BillingRuntimeError, match="invalid transition"):
        bad.webhook(raw, signature)


def test_explicit_runtime_enforces_paid_surface_only_after_reconciled_payment(app, tmp_path):
    runtime, _ = _runtime(tmp_path)
    install_stripe_billing_runtime(app, runtime)
    client = app.test_client()
    _login(client)
    assert client.get("/v2/dashboard").status_code == 403
    account = runtime.repository.account_for(1)
    now = int(datetime.now(timezone.utc).timestamp())
    event = {"id": "evt_access", "created": now, "type": "invoice.paid", "data": {"object": {"metadata": {"reserved_owner_id": "1", "reserved_billing_account_id": account}}}}
    raw, signature = _signed(event)
    assert client.post("/v2/billing/webhook", data=raw, headers={"Stripe-Signature": signature}).status_code == 200
    assert client.get("/v2/dashboard").status_code == 200


@pytest.mark.parametrize("invalid_owner", [0, -1, True, "1", []])
def test_paid_surface_fails_closed_for_malformed_authenticated_owner(app, tmp_path, invalid_owner):
    runtime, _ = _runtime(tmp_path)
    install_stripe_billing_runtime(app, runtime)
    client = app.test_client()
    with client.session_transaction() as current_session:
        current_session["_v2_user_id"] = invalid_owner
    assert client.get("/v2/dashboard").status_code == 403
