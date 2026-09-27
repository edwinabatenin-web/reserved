"""Mutable, disabled-by-default Stripe Billing runtime composition.

This is deliberately a small application boundary rather than a Stripe SDK
adapter.  It has no network client, credentials or environment-variable based
activation.  A deployment must explicitly install a caller-owned provider
client, signature verifier, reconciler and SQLite path before any route can do
work.  Until then every mutating route fails closed.

Provider events are observations.  They are stored only after signature
verification, and can change an entitlement only when the separately supplied
``reconciler`` emits an owner-bound transition.  This keeps the provider edge
from becoming an entitlement flag by accident.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from urllib.parse import urlsplit
from functools import wraps
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Protocol

from flask import Blueprint, Flask, abort, g, jsonify, request, session

from reserved.auth import require_auth
from reserved.extensions import csrf


PLAN_PRICES = {
    "monthly": (2900, "month", 1),
    "six_month": (15600, "month", 6),
    "yearly": (28800, "year", 1),
}
PLAN_LABELS = {
    "monthly": "£29 per month",
    "six_month": "£156 for six months",
    "yearly": "£288 per year",
}
_RUNTIME_KEY = "reserved.billing.stripe_runtime"
_DISABLED_PAID_SURFACE_KEY = _RUNTIME_KEY + ".paid_surface.disabled"
_ALLOWED_STATES = frozenset({"paid", "payment_recovery", "suspended"})
_MAX_INITIAL_EVENT_AGE_SECONDS = 24 * 60 * 60


class BillingRuntimeError(ValueError):
    """A request or dependency was rejected without a partial mutation."""


@dataclass(frozen=True)
class Transition:
    """The only shape a reconciler may use to update Reserved entitlement."""

    owner_id: int
    billing_account_id: str
    subscription_id: str
    state: str
    event_id: str
    occurred_at: int
    reason: str
    kind: str
    paid_until: int | None = None
    payment_identity: str | None = None
    withdrawal_attribution: str = "not_applicable"
    cancel_at_period_end: bool = False


@dataclass(frozen=True)
class PriceBinding:
    """Immutable provider configuration for one already-settled Reserved plan."""

    plan_key: str
    provider_price_id: str
    currency: str
    amount_minor: int
    interval: str
    interval_count: int


@dataclass(frozen=True)
class HostedUrlPolicy:
    """Exact provider-owned HTTPS hosts accepted for customer redirects."""

    checkout_hosts: tuple[str, ...]
    portal_hosts: tuple[str, ...]

    def __post_init__(self):
        host_pattern = __import__("re").compile(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?\Z")
        for hosts in (self.checkout_hosts, self.portal_hosts):
            if (type(hosts) is not tuple or not hosts or len(set(hosts)) != len(hosts)
                    or any(type(host) is not str or "." not in host or ".." in host
                           or host_pattern.fullmatch(host) is None for host in hosts)):
                raise BillingRuntimeError("hosted URL policy must contain exact reviewed provider hosts")


class ProviderClient(Protocol):
    def create_checkout(self, *, owner_id: int, billing_account_id: str,
                        plan_key: str, price_id: str, idempotency_key: str) -> str: ...

    def create_portal(self, *, owner_id: int, billing_account_id: str,
                      idempotency_key: str) -> str: ...


class EventReconciler(Protocol):
    def reconcile(self, *, event: dict[str, Any], owner_id: int,
                  billing_account_id: str,
                  prior_state: str | None) -> Transition | None: ...


class SQLiteBillingRuntimeRepository:
    """Owner-bound billing journal with atomic idempotency and event replay keys.

    The path is explicitly supplied by the composition root.  It is not the
    legacy local evidence repository and makes no claim about production key
    custody, backups or retention; those remain deployment gates.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if self.path.is_symlink():
            raise BillingRuntimeError("billing database path must not be a symlink")
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _init(self):
        with self._lock, self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS billing_accounts (
                    owner_id INTEGER PRIMARY KEY,
                    account_id TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS billing_requests (
                    owner_id INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    idempotency_digest TEXT NOT NULL,
                    plan_key TEXT,
                    provider_idempotency_key TEXT NOT NULL,
                    state TEXT NOT NULL,
                    result_url TEXT,
                    PRIMARY KEY(owner_id, kind, idempotency_digest)
                );
                CREATE TABLE IF NOT EXISTS billing_events (
                    event_id TEXT PRIMARY KEY,
                    digest TEXT NOT NULL,
                    occurred_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS billing_entitlements (
                    owner_id INTEGER PRIMARY KEY,
                    billing_account_id TEXT NOT NULL,
                    subscription_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    event_id TEXT NOT NULL UNIQUE,
                    occurred_at INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    recovery_deadline INTEGER,
                    paid_until INTEGER,
                    payment_identity TEXT,
                    cancellation_effective_at INTEGER,
                    withdrawal_attribution TEXT NOT NULL DEFAULT 'not_applicable'
                );
            """)
            columns = {row[1] for row in db.execute("PRAGMA table_info(billing_entitlements)")}
            for column, declaration in (
                ("recovery_deadline", "INTEGER"), ("paid_until", "INTEGER"),
                ("payment_identity", "TEXT"), ("cancellation_effective_at", "INTEGER"),
                ("withdrawal_attribution", "TEXT NOT NULL DEFAULT 'not_applicable'"),
            ):
                if column not in columns:
                    db.execute(f"ALTER TABLE billing_entitlements ADD COLUMN {column} {declaration}")

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def account_for(self, owner_id: int) -> str:
        if type(owner_id) is not int or owner_id <= 0:
            raise BillingRuntimeError("authenticated owner is invalid")
        with self._lock, self._connect() as db:
            row = db.execute("SELECT account_id FROM billing_accounts WHERE owner_id=?", (owner_id,)).fetchone()
            if row:
                return row["account_id"]
            account = "billing-account-" + hashlib.sha256(str(owner_id).encode()).hexdigest()[:24]
            db.execute("INSERT INTO billing_accounts(owner_id, account_id) VALUES (?, ?)", (owner_id, account))
            return account

    def request_result(self, owner_id: int, kind: str, idempotency_key: str,
                       plan_key: str | None, create: Callable[[str], str],
                       *, allowed_hosts: tuple[str, ...]) -> str:
        if type(owner_id) is not int or owner_id <= 0:
            raise BillingRuntimeError("authenticated owner is invalid")
        if kind not in {"checkout", "portal"} or (plan_key is not None and plan_key not in PLAN_PRICES):
            raise BillingRuntimeError("unsupported billing request")
        if not isinstance(idempotency_key, str) or not 16 <= len(idempotency_key) <= 200:
            raise BillingRuntimeError("Idempotency-Key is required")
        digest = self._digest(idempotency_key)
        provider_identity = json.dumps(
            [owner_id, kind, plan_key, idempotency_key],
            ensure_ascii=True,
            separators=(",", ":"),
        )
        provider_key = "reserved-" + self._digest(provider_identity)
        with self._lock, self._connect() as db:
            found = db.execute("SELECT result_url, plan_key, state, provider_idempotency_key FROM billing_requests WHERE owner_id=? AND kind=? AND idempotency_digest=?", (owner_id, kind, digest)).fetchone()
            if found:
                if found["plan_key"] != plan_key:
                    raise BillingRuntimeError("idempotency key cannot change the requested plan")
                if found["state"] == "complete":
                    return self._validated_hosted_url(found["result_url"], allowed_hosts)
                provider_key = found["provider_idempotency_key"]
            else:
                # Commit a durable reservation before any provider boundary.
                # A retry after a crash uses the same derived provider key.
                db.execute("INSERT INTO billing_requests(owner_id,kind,idempotency_digest,plan_key,provider_idempotency_key,state,result_url) VALUES (?, ?, ?, ?, ?, 'pending', NULL)",
                           (owner_id, kind, digest, plan_key, provider_key))
        result = self._validated_hosted_url(create(provider_key), allowed_hosts)
        with self._lock, self._connect() as db:
            found = db.execute("SELECT state, result_url, provider_idempotency_key FROM billing_requests WHERE owner_id=? AND kind=? AND idempotency_digest=?", (owner_id, kind, digest)).fetchone()
            if found is None or found["provider_idempotency_key"] != provider_key:
                raise BillingRuntimeError("billing request reservation changed")
            if found["state"] == "complete":
                return self._validated_hosted_url(found["result_url"], allowed_hosts)
            db.execute("UPDATE billing_requests SET state='complete', result_url=? WHERE owner_id=? AND kind=? AND idempotency_digest=? AND state='pending'", (result, owner_id, kind, digest))
            return result

    @staticmethod
    def _validated_hosted_url(value: object, allowed_hosts: tuple[str, ...]) -> str:
        if (type(value) is not str or not value or len(value) > 2048 or value != value.strip()
                or "\\" in value or any(ord(character) < 0x20 for character in value)):
            raise BillingRuntimeError("provider returned an invalid hosted URL")
        try:
            value.encode("ascii")
            parsed = urlsplit(value)
            port = parsed.port
        except (UnicodeEncodeError, ValueError):
            raise BillingRuntimeError("provider returned an invalid hosted URL") from None
        if (parsed.scheme != "https" or parsed.username is not None or parsed.password is not None
                or port is not None or parsed.hostname not in allowed_hosts
                or parsed.netloc != parsed.hostname or not parsed.path.startswith("/")
                or parsed.fragment):
            raise BillingRuntimeError("provider returned an invalid hosted URL")
        return value

    def prior_state(self, owner_id: int) -> str | None:
        with self._lock, self._connect() as db:
            row = db.execute("SELECT state FROM billing_entitlements WHERE owner_id=?", (owner_id,)).fetchone()
            return row["state"] if row else None

    def record_verified_event(self, raw_body: bytes, event: dict[str, Any], reconciler: EventReconciler, *, received_at: int) -> str:
        event_id = event.get("id")
        occurred_at = event.get("created")
        metadata = event.get("data", {}).get("object", {}).get("metadata", {})
        owner_value = metadata.get("reserved_owner_id") if isinstance(metadata, dict) else None
        account = metadata.get("reserved_billing_account_id") if isinstance(metadata, dict) else None
        if (not isinstance(event_id, str) or not event_id.startswith("evt_") or type(occurred_at) is not int
                or occurred_at > received_at + 300):
            raise BillingRuntimeError("event identity is invalid")
        if not isinstance(owner_value, str) or not owner_value.isdecimal() or int(owner_value) <= 0:
            raise BillingRuntimeError("event is missing an owner binding")
        if not isinstance(account, str) or not account.startswith("billing-account-"):
            raise BillingRuntimeError("event is missing a billing account binding")
        owner_id = int(owner_value)
        digest = hashlib.sha256(raw_body).hexdigest()
        with self._lock, self._connect() as db:
            account_row = db.execute("SELECT account_id FROM billing_accounts WHERE owner_id=?", (owner_id,)).fetchone()
            if account_row is None or account_row["account_id"] != account:
                raise BillingRuntimeError("event owner/account binding is unknown")
            existing = db.execute("SELECT digest FROM billing_events WHERE event_id=?", (event_id,)).fetchone()
            if existing:
                if existing["digest"] != digest:
                    raise BillingRuntimeError("event replay identity has different bytes")
                return "duplicate"
            prior = db.execute("SELECT state, subscription_id, occurred_at, recovery_deadline, paid_until, payment_identity, cancellation_effective_at FROM billing_entitlements WHERE owner_id=?", (owner_id,)).fetchone()
            if prior and occurred_at < prior["occurred_at"]:
                raise BillingRuntimeError("out-of-order event is quarantined")
            if not prior and event.get("type") == "invoice.paid" and occurred_at < received_at - _MAX_INITIAL_EVENT_AGE_SECONDS:
                raise BillingRuntimeError("stale initial payment is quarantined")
            transition = reconciler.reconcile(event=event, owner_id=owner_id, billing_account_id=account,
                                               prior_state=prior["state"] if prior else None)
            db.execute("INSERT INTO billing_events VALUES (?, ?, ?)", (event_id, digest, occurred_at))
            if transition is None:
                return "recorded_pending_reconciliation"
            self._validate_transition(transition, owner_id, account, event_id, occurred_at)
            if (prior and prior["state"] == "payment_recovery"
                    and prior["recovery_deadline"] is not None
                    and (occurred_at >= prior["recovery_deadline"] or received_at >= prior["recovery_deadline"])
                    and transition.state in {"paid", "payment_recovery"}):
                raise BillingRuntimeError("post-deadline event cannot restore access")
            if transition.kind == "initial_payment" and prior:
                raise BillingRuntimeError("initial payment cannot replace an existing subscription")
            if transition.kind != "initial_payment" and not prior:
                raise BillingRuntimeError("subscription transition has no predecessor")
            if prior and transition.kind != "initial_payment" and transition.subscription_id != prior["subscription_id"]:
                raise BillingRuntimeError("subscription transition does not match the current subscription")
            if transition.kind == "full_withdrawal" and transition.withdrawal_attribution != "current_period":
                raise BillingRuntimeError("non-current or ambiguous withdrawal cannot suspend access")
            if (transition.kind == "full_withdrawal"
                    and (not prior or transition.payment_identity != prior["payment_identity"])):
                raise BillingRuntimeError("withdrawal does not identify the current period payment")
            if (transition.kind == "cancellation"
                    and (prior["state"] not in {"paid", "payment_recovery"} or transition.state != prior["state"])):
                raise BillingRuntimeError("cancellation does not preserve an active subscription state")
            if transition.kind != "full_withdrawal" and transition.withdrawal_attribution != "not_applicable":
                raise BillingRuntimeError("withdrawal attribution is invalid")
            # FD-W10-003: the first verified failure fixes one seven-calendar-
            # day recovery deadline.  Later failures record their observation
            # but must never replace or prolong that deadline.
            recovery_deadline = None
            if transition.state == "payment_recovery":
                recovery_deadline = prior["recovery_deadline"] if prior and prior["state"] == "payment_recovery" else occurred_at + (7 * 24 * 60 * 60)
            paid_until = transition.paid_until if transition.paid_until is not None else (prior["paid_until"] if prior else None)
            payment_identity = transition.payment_identity if transition.payment_identity is not None else (prior["payment_identity"] if prior else None)
            cancellation_at = paid_until if transition.cancel_at_period_end else (prior["cancellation_effective_at"] if prior else None)
            db.execute("""INSERT INTO billing_entitlements(owner_id,billing_account_id,subscription_id,state,event_id,occurred_at,reason,recovery_deadline,paid_until,payment_identity,cancellation_effective_at,withdrawal_attribution)
                          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                          ON CONFLICT(owner_id) DO UPDATE SET billing_account_id=excluded.billing_account_id,
                          subscription_id=excluded.subscription_id,state=excluded.state,event_id=excluded.event_id,
                          occurred_at=excluded.occurred_at,reason=excluded.reason,recovery_deadline=excluded.recovery_deadline,
                          paid_until=excluded.paid_until,payment_identity=excluded.payment_identity,
                          cancellation_effective_at=excluded.cancellation_effective_at,withdrawal_attribution=excluded.withdrawal_attribution""",
                       (owner_id, account, transition.subscription_id, transition.state, event_id, occurred_at, transition.reason, recovery_deadline, paid_until, payment_identity, cancellation_at, transition.withdrawal_attribution))
            return "reconciled"

    @staticmethod
    def _validate_transition(value: Transition, owner_id: int, account: str, event_id: str, occurred_at: int):
        if (not isinstance(value, Transition) or value.owner_id != owner_id
                or value.billing_account_id != account or value.event_id != event_id
                or value.occurred_at != occurred_at or value.state not in _ALLOWED_STATES
                or not isinstance(value.subscription_id, str) or not value.subscription_id.startswith("sub_")
                or not isinstance(value.reason, str) or not value.reason
                or value.kind not in {"initial_payment", "renewal_payment", "failed_renewal", "cancellation", "full_withdrawal"}
                or (value.kind in {"initial_payment", "renewal_payment"} and (value.state != "paid" or type(value.paid_until) is not int or value.paid_until <= occurred_at or not isinstance(value.payment_identity, str) or not value.payment_identity.startswith("pi_")))
                or (value.kind == "failed_renewal" and value.state != "payment_recovery")
                or (value.kind == "full_withdrawal" and (value.state != "suspended" or not isinstance(value.payment_identity, str) or not value.payment_identity.startswith("pi_")))
                or (value.kind == "cancellation" and not value.cancel_at_period_end)):
            raise BillingRuntimeError("reconciler returned an invalid transition")

    def status_for(self, owner_id: int, *, now_epoch: int | None = None) -> dict[str, str]:
        now_epoch = int(datetime.now(timezone.utc).timestamp()) if now_epoch is None else now_epoch
        with self._lock, self._connect() as db:
            row = db.execute("SELECT state, subscription_id, recovery_deadline, paid_until, cancellation_effective_at FROM billing_entitlements WHERE owner_id=?", (owner_id,)).fetchone()
            if row is None:
                return {"state": "no_entitlement", "ordinary_access": "false"}
            if row["state"] == "payment_recovery":
                deadline = row["recovery_deadline"]
                if type(deadline) is not int or now_epoch >= deadline:
                    return {"state": "suspended", "ordinary_access": "false"}
                return {"state": "payment_recovery", "ordinary_access": "true"}
            if type(row["paid_until"]) is not int or now_epoch >= row["paid_until"]:
                return {"state": "suspended", "ordinary_access": "false"}
            return {"state": row["state"], "ordinary_access": "true" if row["state"] in {"paid", "payment_recovery"} else "false"}


@dataclass(frozen=True)
class StripeBillingRuntime:
    repository: SQLiteBillingRuntimeRepository
    provider: ProviderClient
    verify_signature: Callable[[bytes, str], bool]
    reconciler: EventReconciler
    price_bindings: tuple[PriceBinding, ...]
    hosted_url_policy: HostedUrlPolicy
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)

    def __post_init__(self):
        if (type(self.price_bindings) is not tuple or len(self.price_bindings) != len(PLAN_PRICES)
                or type(self.hosted_url_policy) is not HostedUrlPolicy
                or not callable(self.verify_signature) or not callable(getattr(self.reconciler, "reconcile", None))):
            raise BillingRuntimeError("complete price, signature and reconciliation configuration is required")
        bindings = {}
        for binding in self.price_bindings:
            if (type(binding) is not PriceBinding or binding.plan_key in bindings
                    or not binding.provider_price_id.startswith("price_")
                    or PLAN_PRICES.get(binding.plan_key) != (binding.amount_minor, binding.interval, binding.interval_count)
                    or binding.currency != "GBP" or binding.provider_price_id in {item.provider_price_id for item in bindings.values()}):
                raise BillingRuntimeError("price configuration must uniquely bind the settled GBP catalogue")
            bindings[binding.plan_key] = binding
        if set(bindings) != set(PLAN_PRICES):
            raise BillingRuntimeError("price configuration must cover every settled plan")
        object.__setattr__(self, "_price_by_plan", MappingProxyType(bindings))

    def checkout(self, owner_id: int, plan_key: str, idempotency_key: str) -> str:
        if plan_key not in PLAN_PRICES:
            raise BillingRuntimeError("unsupported plan")
        account = self.repository.account_for(owner_id)
        return self.repository.request_result(owner_id, "checkout", idempotency_key, plan_key,
            lambda provider_key: self.provider.create_checkout(owner_id=owner_id, billing_account_id=account,
                                                  plan_key=plan_key, price_id=self._price_by_plan[plan_key].provider_price_id,
                                                  idempotency_key=provider_key),
            allowed_hosts=self.hosted_url_policy.checkout_hosts)

    def portal(self, owner_id: int, idempotency_key: str) -> str:
        account = self.repository.account_for(owner_id)
        return self.repository.request_result(owner_id, "portal", idempotency_key, None,
            lambda provider_key: self.provider.create_portal(owner_id=owner_id, billing_account_id=account,
                                                idempotency_key=provider_key),
            allowed_hosts=self.hosted_url_policy.portal_hosts)

    def webhook(self, raw_body: bytes, signature: str) -> str:
        if not isinstance(raw_body, bytes) or not signature or not self.verify_signature(raw_body, signature):
            raise BillingRuntimeError("webhook signature is invalid")
        try:
            event = json.loads(raw_body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BillingRuntimeError("webhook body is invalid") from exc
        if not isinstance(event, dict):
            raise BillingRuntimeError("webhook body is invalid")
        created = event.get("created")
        now = self.clock()
        if (type(created) is not int or type(now) is not datetime
                or now.tzinfo is not timezone.utc
                or created > int(now.timestamp()) + 300):
            raise BillingRuntimeError("webhook event time is invalid")
        return self.repository.record_verified_event(raw_body, event, self.reconciler, received_at=int(now.timestamp()))

    def status(self, owner_id: int) -> dict[str, str]:
        now = self.clock()
        if type(now) is not datetime or now.tzinfo is not timezone.utc:
            raise BillingRuntimeError("runtime clock must return UTC datetime")
        return self.repository.status_for(owner_id, now_epoch=int(now.timestamp()))


billing = Blueprint("billing", __name__, url_prefix="/v2/billing")


def _runtime() -> StripeBillingRuntime:
    # App extensions are only accessed after this route has been associated
    # with its Flask application; no environment flag can turn billing on.
    from flask import current_app
    value = current_app.extensions.get(_RUNTIME_KEY)
    if not isinstance(value, StripeBillingRuntime):
        abort(503, description="Billing is not configured.")
    return value


def _idempotency_key() -> str:
    value = request.headers.get("Idempotency-Key", "")
    if not value:
        abort(400, description="Idempotency-Key is required.")
    return value


@billing.post("/checkout")
@require_auth
def checkout():
    body = request.get_json(silent=True) or {}
    plan_key = body.get("plan_key")
    if not isinstance(plan_key, str):
        abort(400, description="A supported plan_key is required.")
    try:
        hosted_url = _runtime().checkout(g.user_id, plan_key, _idempotency_key())
    except BillingRuntimeError as exc:
        abort(409, description=str(exc))
    return jsonify({"status": "checkout_created", "hosted_url": hosted_url, "plan_key": plan_key}), 201


@billing.post("/portal")
@require_auth
def portal():
    try:
        hosted_url = _runtime().portal(g.user_id, _idempotency_key())
    except BillingRuntimeError as exc:
        abort(409, description=str(exc))
    return jsonify({"status": "portal_created", "hosted_url": hosted_url}), 201


@billing.post("/webhook")
@csrf.exempt
def webhook():
    try:
        result = _runtime().webhook(request.get_data(cache=True), request.headers.get("Stripe-Signature", ""))
    except BillingRuntimeError as exc:
        abort(400, description=str(exc))
    return jsonify({"status": result}), 200


@billing.get("/status")
@require_auth
def status():
    return jsonify(_runtime().status(g.user_id))


def install_stripe_billing_runtime(app: Flask, runtime: StripeBillingRuntime) -> None:
    """Install the billing boundary only with all explicit dependencies.

    ``create_app`` calls this function only when an already-complete runtime is
    explicitly injected.  An absent route is the normal disabled state, so a
    configuration typo cannot expose a half-wired purchase or webhook endpoint.
    """
    if not isinstance(runtime, StripeBillingRuntime):
        raise BillingRuntimeError("an explicit complete billing runtime is required")
    if _RUNTIME_KEY in app.extensions or "billing" in app.blueprints:
        raise BillingRuntimeError("billing runtime already installed")
    marker, replacements = _prepare_runtime_paid_surface_enforcement(app, runtime)
    app.register_blueprint(billing)
    app.extensions[_RUNTIME_KEY] = runtime
    app.view_functions.update(replacements)
    app.extensions[marker] = True


def _prepare_runtime_paid_surface_enforcement(
    app: Flask, runtime: StripeBillingRuntime
) -> tuple[str, dict[str, object]]:
    """Validate and construct every paid wrapper without mutating the app."""
    from reserved.billing.paid_access_guard import PAID_ENDPOINTS

    if not isinstance(app, Flask) or not isinstance(runtime, StripeBillingRuntime):
        raise BillingRuntimeError("explicit Flask app and billing runtime required")
    marker = _RUNTIME_KEY + ".paid_surface"
    if marker in app.extensions:
        raise BillingRuntimeError("paid-surface enforcement already installed")
    hicbc_registered = "hicbc" in app.blueprints
    expected = tuple(
        endpoint for endpoint in PAID_ENDPOINTS
        if hicbc_registered or not endpoint.startswith("hicbc.")
    )
    disabled = app.extensions.get(_DISABLED_PAID_SURFACE_KEY)
    originals = None
    if disabled is not None:
        if type(disabled) is not dict or set(disabled) != set(expected):
            raise BillingRuntimeError("disabled paid-surface boundary is inconsistent")
        if any(not callable(value) for value in disabled.values()):
            raise BillingRuntimeError("disabled paid-surface boundary is inconsistent")
        originals = disabled

    missing = tuple(
        endpoint for endpoint in expected
        if endpoint not in app.view_functions or not callable(app.view_functions[endpoint])
    )
    if missing:
        raise BillingRuntimeError("settled paid endpoints are incomplete")
    if not expected:
        raise BillingRuntimeError("no settled paid endpoints are registered")

    replacements = {}
    for endpoint in expected:
        original = originals[endpoint] if originals is not None else app.view_functions[endpoint]

        @wraps(original)
        def guarded(*args, __original=original, **kwargs):
            # Preserve the existing authentication redirect for visitors with
            # no session.  The existing decorated endpoint remains responsible
            # for loading g and validating the signed session.
            owner_id = session.get("_v2_user_id")
            if owner_id is not None:
                if type(owner_id) is not int or owner_id <= 0:
                    abort(403)
                try:
                    if runtime.status(owner_id)["ordinary_access"] != "true":
                        abort(403)
                except BillingRuntimeError:
                    abort(403)
            return __original(*args, **kwargs)

        replacements[endpoint] = guarded
    return marker, replacements


def install_disabled_paid_surface_enforcement(app: Flask) -> None:
    """Make every settled paid route unavailable until billing is installed.

    This is the default application composition.  It is intentionally a route
    boundary, rather than a collection of feature-flag conventions: a new
    paid feature cannot accidentally become free merely because its own flag
    is enabled before the complete owner-bound billing runtime is installed.
    The original views are retained privately so a complete runtime can replace
    these exact denial wrappers atomically after its full preflight succeeds.
    """
    from reserved.billing.paid_access_guard import PAID_ENDPOINTS

    if not isinstance(app, Flask):
        raise BillingRuntimeError("explicit Flask app is required")
    if _RUNTIME_KEY in app.extensions or _DISABLED_PAID_SURFACE_KEY in app.extensions:
        raise BillingRuntimeError("paid-surface boundary already installed")

    hicbc_registered = "hicbc" in app.blueprints
    expected = tuple(
        endpoint for endpoint in PAID_ENDPOINTS
        if hicbc_registered or not endpoint.startswith("hicbc.")
    )
    originals = {endpoint: app.view_functions.get(endpoint) for endpoint in expected}
    if not expected or any(not callable(view) for view in originals.values()):
        raise BillingRuntimeError("settled paid endpoints are incomplete")

    replacements = {}
    for endpoint, original in originals.items():
        @wraps(original)
        def unavailable(*args, **kwargs):
            abort(404)
        replacements[endpoint] = unavailable

    # All validation and wrapper construction precede mutation.  Thus a
    # malformed route inventory cannot leave one paid route exposed.
    app.view_functions.update(replacements)
    app.extensions[_DISABLED_PAID_SURFACE_KEY] = originals


def install_runtime_paid_surface_enforcement(app: Flask, runtime: StripeBillingRuntime) -> None:
    """Install server-side paid access checks on the settled ordinary surfaces.

    This is intentionally a separate explicit composition action: purchase,
    portal, recovery and authentication routes remain outside the paid surface,
    while every registered ordinary product endpoint denies when the own
    reconciled state is absent, suspended or recovery-expired.
    """
    marker, replacements = _prepare_runtime_paid_surface_enforcement(app, runtime)
    app.view_functions.update(replacements)
    app.extensions[marker] = True
