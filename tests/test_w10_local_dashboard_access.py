"""W10-S5 local dashboard access installer — real-request enforcement tests.

This is the actual application consumer of the already-reviewed W10-S3C
runtime-entitlement admission and W10-S5D paid-access guard.  Every test drives
the real, registered Flask ``v2.dashboard_view`` through the explicit
non-production installer using disposable synthetic databases in temporary
directories.  No provider call, network tool, model configuration, application
database, migration or persistent user data is involved.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import re
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

import reserved.database as db
import reserved.billing.local_billing_repository as repo_mod
import reserved.billing.paid_access_guard as s5d
import reserved.billing.runtime_entitlement_admission as s3c
from reserved import create_app
from reserved.web import v2
from reserved.billing.local_billing_repository import (
    LocalBillingRepository,
    LocalBillingRepositoryError,
)
from reserved.billing.local_dashboard_access import (
    BillingSnapshot,
    LocalDashboardAccessError,
    SnapshotEntry,
    install_local_dashboard_access,
)

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc

OWNER = "users:17"
ACCOUNT = "billing:17"
SUBSCRIPTION = "subscription:17"
SCOPE = (OWNER, ACCOUNT, SUBSCRIPTION)

DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64
DIGEST_D = "sha256:" + "d" * 64
DIGEST_E = "sha256:" + "e" * 64

FACT_KEYS = (
    "protocol_version",
    "fact_identity",
    "admission_status",
    "authenticated",
    "billing_fact_authority",
    "provider_observation_direct_authority",
    "owner_id",
    "billing_account_id",
    "subscription_id",
    "decision_sequence",
    "predecessor_fact_identity",
    "state",
    "valid_from_inclusive",
    "valid_until_exclusive",
    "transition_effective_at_utc",
    "recovery_deadline_exclusive_at_utc",
    "derivation_kind",
    "withdrawal_attribution",
)

CLOCK = datetime(2026, 10, 2, 12, tzinfo=UTC)
CLOCK_WITHDRAWAL = datetime(2026, 10, 16, 12, tzinfo=UTC)
CLOCK_RESTORATION = datetime(2026, 10, 21, 12, tzinfo=UTC)
CLOCK_RECOVERY = datetime(2026, 11, 2, 12, tzinfo=UTC)
CLOCK_RECOVERY_EXPIRED = datetime(2026, 11, 8, 12, tzinfo=UTC)


# ── S3C billing-fact fixtures (unchanged S3C identity scheme) ────────────────

def _fact_identity(values):
    material = (
        values["protocol_version"],
        values["admission_status"],
        values["authenticated"],
        values["billing_fact_authority"],
        values["provider_observation_direct_authority"],
        values["owner_id"],
        values["billing_account_id"],
        values["subscription_id"],
        values["decision_sequence"],
        values["predecessor_fact_identity"],
        values["state"],
        values["valid_from_inclusive"].isoformat(),
        values["valid_until_exclusive"].isoformat(),
        values["transition_effective_at_utc"].isoformat(),
        (
            None
            if values["recovery_deadline_exclusive_at_utc"] is None
            else values["recovery_deadline_exclusive_at_utc"].isoformat()
        ),
        values["derivation_kind"],
        values["withdrawal_attribution"],
    )
    payload = json.dumps(material, ensure_ascii=True, separators=(",", ":"))
    return "billing-fact:sha256-" + hashlib.sha256(payload.encode("ascii")).hexdigest()


def _fact_values(record, predecessor_fact_identity):
    values = {
        "protocol_version": s3c.BILLING_FACT_PROTOCOL_VERSION,
        "fact_identity": "",
        "admission_status": s3c.BILLING_FACT_ADMISSION_STATUS,
        "authenticated": True,
        "billing_fact_authority": True,
        "provider_observation_direct_authority": False,
        "owner_id": record.owner_id,
        "billing_account_id": record.billing_account_id,
        "subscription_id": record.subscription_id,
        "decision_sequence": record.sequence,
        "predecessor_fact_identity": predecessor_fact_identity,
        "state": record.state,
        "valid_from_inclusive": record.valid_from_inclusive,
        "valid_until_exclusive": record.valid_until_exclusive,
        "transition_effective_at_utc": record.transition_effective_at_utc,
        "recovery_deadline_exclusive_at_utc": record.recovery_deadline_exclusive_at_utc,
        "derivation_kind": record.derivation_kind,
        "withdrawal_attribution": record.withdrawal_attribution,
    }
    values["fact_identity"] = _fact_identity(values)
    return tuple((key, values[key]) for key in FACT_KEYS)


def _facts(records):
    facts = []
    predecessor = None
    for record in records:
        fact = _fact_values(record, predecessor)
        facts.append(fact)
        predecessor = dict(fact)["fact_identity"]
    return facts


class LiveBillingFact:
    __slots__ = ("view",)

    def __init__(self, view):
        self.view = view


def _authority():
    live = set()

    def issue(view):
        fact = LiveBillingFact(view)
        live.add(id(fact))
        return fact

    def validate(value):
        if type(value) is not LiveBillingFact or id(value) not in live:
            raise ValueError("not admitted")
        return value.view

    def project(value):
        if type(value) is not LiveBillingFact or id(value) not in live:
            raise ValueError("not admitted")
        return value.view

    return validate, project, issue


# ── Repository observation fixtures (unchanged S3D write path) ───────────────

def _append(repo, **changes):
    values = dict(
        owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
        plan_key="monthly",
        source_namespace="stripe-subscription/test-scope",
        source_event_id="evt-1",
        source_event_digest=DIGEST_A,
        observation_kind="initial_payment_confirmed",
        effective_date=date(2026, 10, 1),
        paid_through=date(2026, 10, 31),
        evidence_reference="evidence/ref-1",
        state="paid",
        valid_from_inclusive=date(2026, 10, 1),
        valid_until_exclusive=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 10, 1, tzinfo=UTC),
        recovery_deadline_exclusive_at_utc=None,
        derivation_kind="verified_initial_payment",
        withdrawal_attribution="not_applicable",
        expected_predecessor_identity=None,
        expected_sequence=1,
        recorded_at_utc=datetime(2026, 10, 1, 12, tzinfo=UTC),
    )
    values.update(changes)
    return repo.append_observation(**values)


def _append_recovery(repo, predecessor):
    return _append(
        repo,
        source_event_id="evt-2",
        source_event_digest=DIGEST_B,
        observation_kind="renewal_payment_failed",
        effective_date=date(2026, 11, 1),
        paid_through=None,
        evidence_reference="evidence/ref-2",
        state="payment_recovery",
        valid_from_inclusive=date(2026, 10, 1),
        valid_until_exclusive=date(2026, 11, 8),
        transition_effective_at_utc=datetime(2026, 11, 1, tzinfo=UTC),
        recovery_deadline_exclusive_at_utc=datetime(2026, 11, 8, tzinfo=UTC),
        derivation_kind="verified_renewal_failure",
        withdrawal_attribution="not_applicable",
        expected_predecessor_identity=predecessor.content_identity,
        expected_sequence=2,
        recorded_at_utc=datetime(2026, 11, 1, 12, tzinfo=UTC),
    )


def _append_withdrawal(repo, predecessor):
    return _append(
        repo,
        source_event_id="evt-3",
        source_event_digest=DIGEST_C,
        observation_kind="cancellation_confirmed",
        effective_date=date(2026, 10, 15),
        paid_through=None,
        evidence_reference="evidence/ref-3",
        state="suspended",
        valid_from_inclusive=date(2026, 10, 1),
        valid_until_exclusive=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 10, 15, tzinfo=UTC),
        recovery_deadline_exclusive_at_utc=None,
        derivation_kind="verified_full_withdrawal",
        withdrawal_attribution="current_subscription_period",
        expected_predecessor_identity=predecessor.content_identity,
        expected_sequence=2,
        recorded_at_utc=datetime(2026, 10, 15, 12, tzinfo=UTC),
    )


def _append_ambiguous(repo, predecessor):
    """Ambiguous withdrawal evidence that only preserves prior paid access."""
    return _append(
        repo,
        source_event_id="evt-4",
        source_event_digest=DIGEST_D,
        observation_kind="dispute_observed",
        effective_date=date(2026, 10, 15),
        paid_through=None,
        evidence_reference="evidence/ref-4",
        state="paid",
        valid_from_inclusive=date(2026, 10, 1),
        valid_until_exclusive=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 10, 15, tzinfo=UTC),
        recovery_deadline_exclusive_at_utc=None,
        derivation_kind="withdrawal_ambiguous",
        withdrawal_attribution="unknown",
        expected_predecessor_identity=predecessor.content_identity,
        expected_sequence=2,
        recorded_at_utc=datetime(2026, 10, 15, 12, tzinfo=UTC),
    )


def _append_restoration(repo, predecessor):
    """Independently admitted verified reinstatement after a withdrawal."""
    return _append(
        repo,
        source_event_id="evt-5",
        source_event_digest=DIGEST_E,
        observation_kind="renewal_payment_confirmed",
        effective_date=date(2026, 10, 20),
        paid_through=date(2026, 10, 31),
        evidence_reference="evidence/ref-5",
        state="paid",
        valid_from_inclusive=date(2026, 10, 20),
        valid_until_exclusive=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 10, 20, tzinfo=UTC),
        recovery_deadline_exclusive_at_utc=None,
        derivation_kind="verified_reinstatement",
        withdrawal_attribution="not_applicable",
        expected_predecessor_identity=predecessor.content_identity,
        expected_sequence=3,
        recorded_at_utc=datetime(2026, 10, 20, 12, tzinfo=UTC),
    )


def _append_reinstatement_without_withdrawal(repo, predecessor):
    """A reinstatement that has no suspended withdrawal lineage to restore."""
    return _append(
        repo,
        source_event_id="evt-6",
        source_event_digest="sha256:" + "f" * 64,
        observation_kind="renewal_payment_confirmed",
        effective_date=date(2026, 10, 5),
        paid_through=date(2026, 10, 31),
        evidence_reference="evidence/ref-6",
        state="paid",
        valid_from_inclusive=date(2026, 10, 1),
        valid_until_exclusive=date(2026, 11, 1),
        transition_effective_at_utc=datetime(2026, 10, 5, tzinfo=UTC),
        recovery_deadline_exclusive_at_utc=None,
        derivation_kind="verified_reinstatement",
        withdrawal_attribution="not_applicable",
        expected_predecessor_identity=predecessor.content_identity,
        expected_sequence=2,
        recorded_at_utc=datetime(2026, 10, 5, 12, tzinfo=UTC),
    )


def _ambiguous_preservation_fact(record, predecessor_fact_identity):
    """A valid same-scope/sequence S3C ambiguous fact for a recorded withdrawal.

    This is deliberately a *different* meaning from ``record``: the S3D entry is
    a ``suspended`` / ``verified_full_withdrawal``, while this valid S3C fact is
    ``paid`` / ``withdrawal_ambiguous``.  It must never be allowed to stand in
    for the recorded withdrawal entry.
    """
    values = {
        "protocol_version": s3c.BILLING_FACT_PROTOCOL_VERSION,
        "fact_identity": "",
        "admission_status": s3c.BILLING_FACT_ADMISSION_STATUS,
        "authenticated": True,
        "billing_fact_authority": True,
        "provider_observation_direct_authority": False,
        "owner_id": record.owner_id,
        "billing_account_id": record.billing_account_id,
        "subscription_id": record.subscription_id,
        "decision_sequence": record.sequence,
        "predecessor_fact_identity": predecessor_fact_identity,
        "state": "paid",
        "valid_from_inclusive": record.valid_from_inclusive,
        "valid_until_exclusive": record.valid_until_exclusive,
        "transition_effective_at_utc": record.transition_effective_at_utc,
        "recovery_deadline_exclusive_at_utc": record.recovery_deadline_exclusive_at_utc,
        "derivation_kind": "withdrawal_ambiguous",
        "withdrawal_attribution": "unknown",
    }
    values["fact_identity"] = _fact_identity(values)
    return tuple((key, values[key]) for key in FACT_KEYS)


# ── Explicit server bindings (synthetic fixtures only) ───────────────────────

def _membership_resolver(user_id):
    def resolve(uid):
        if uid == user_id:
            return SCOPE
        return None

    return resolve


def _entry_from_record(r):
    """Project one S3D journal record into its structural snapshot entry.

    Carries the recorded outcome/meaning fields so the installer can bind the
    separately admitted live fact to this exact structural entry.
    """
    return SnapshotEntry(
        sequence=r.sequence,
        content_identity=r.content_identity,
        predecessor_identity=r.predecessor_identity,
        state=r.state,
        derivation_kind=r.derivation_kind,
        withdrawal_attribution=r.withdrawal_attribution,
        valid_from_inclusive=r.valid_from_inclusive,
        valid_until_exclusive=r.valid_until_exclusive,
        transition_effective_at_utc=r.transition_effective_at_utc,
        recovery_deadline_exclusive_at_utc=r.recovery_deadline_exclusive_at_utc,
    )


def _snapshot_reader(repo, scope=SCOPE):
    def read(owner, account, subscription):
        if (owner, account, subscription) != scope:
            return None
        head = repo.current_head(
            owner_id=owner, billing_account_id=account, subscription_id=subscription
        )
        if head is None:
            return None
        records = repo.journal(
            owner_id=owner, billing_account_id=account, subscription_id=subscription
        )
        entries = tuple(_entry_from_record(r) for r in records)
        return BillingSnapshot(
            owner_id=owner,
            billing_account_id=account,
            subscription_id=subscription,
            head_identity=head.head_identity,
            head_sequence=head.sequence,
            entries=entries,
        )

    return read


def _live_fact_resolver(repo, scope, issue):
    def resolve(owner, account, subscription, content_identity, sequence):
        if (owner, account, subscription) != scope:
            return None
        try:
            records = repo.journal(
                owner_id=owner, billing_account_id=account, subscription_id=subscription
            )
        except Exception:
            return None
        if sequence < 1 or sequence > len(records):
            return None
        record = records[sequence - 1]
        if record.sequence != sequence or record.content_identity != content_identity:
            return None
        facts = _facts(records)
        return issue(facts[sequence - 1])

    return resolve


def _install(app, *, user_id, repo, validate, project, issue, clock, scope=SCOPE):
    return install_local_dashboard_access(
        app,
        membership_resolver=_membership_resolver(user_id),
        snapshot_reader=_snapshot_reader(repo, scope),
        live_fact_resolver=_live_fact_resolver(repo, scope, issue),
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
        clock=clock,
    )


# ── Application fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def app(tmp_path, monkeypatch):
    test_file = tmp_path / "w10_dashboard.db"
    monkeypatch.setattr(db, "_DB_FILE", test_file)
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return application


@pytest.fixture
def billing_repo(tmp_path):
    repo = LocalBillingRepository.create(tmp_path / "billing.db")
    yield repo
    repo.close()


def _authenticated_client(app, *, clerk_id="users:17"):
    user_id = db.get_or_create_user(
        clerk_id, email="owner@example.test", display_name="Owner"
    )
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_v2_user_id"] = user_id
        sess["_v2_clerk_id"] = clerk_id
        sess["_v2_email"] = "owner@example.test"
        sess["_v2_display_name"] = "Owner"
        sess["_v2_is_demo"] = True
    return client, user_id


# ── Installation contract ────────────────────────────────────────────────────

def test_import_has_no_application_side_effects(app):
    """Default app keeps the original registered dashboard and no extension key."""
    original = app.view_functions["v2.dashboard_view"]
    assert original is v2.dashboard_view or getattr(original, "__wrapped__", None) is v2.dashboard_view
    assert "reserved.billing.local_dashboard_access" not in app.extensions


def test_installer_refuses_production(app, monkeypatch, billing_repo):
    validate, project, issue = _authority()
    monkeypatch.setattr("reserved.auth.is_production_environment", lambda: True)
    with pytest.raises(LocalDashboardAccessError):
        _install(app, user_id=1, repo=billing_repo, validate=validate,
                 project=project, issue=issue, clock=lambda: CLOCK)


def test_installer_refuses_duplicate(app, billing_repo):
    validate, project, issue = _authority()
    _install(app, user_id=1, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    with pytest.raises(LocalDashboardAccessError):
        _install(app, user_id=1, repo=billing_repo, validate=validate,
                 project=project, issue=issue, clock=lambda: CLOCK)


def test_installer_refuses_late_installation(app, billing_repo):
    validate, project, issue = _authority()
    app._got_first_request = True
    with pytest.raises(LocalDashboardAccessError):
        _install(app, user_id=1, repo=billing_repo, validate=validate,
                 project=project, issue=issue, clock=lambda: CLOCK)


def test_installer_refuses_ambiguous_endpoint(app, monkeypatch, billing_repo):
    validate, project, issue = _authority()
    monkeypatch.setattr(v2, "dashboard_view", lambda: "not-the-dashboard")
    with pytest.raises(LocalDashboardAccessError):
        _install(app, user_id=1, repo=billing_repo, validate=validate,
                 project=project, issue=issue, clock=lambda: CLOCK)


def test_installer_creates_no_new_files(app, tmp_path, billing_repo):
    validate, project, issue = _authority()
    before = {p.name for p in tmp_path.iterdir()}
    _install(app, user_id=1, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    after = {p.name for p in tmp_path.iterdir()}
    assert before == after


# ── Real authenticated synthetic-user enforcement ────────────────────────────

def test_real_authenticated_synthetic_user_allows_dashboard(app, billing_repo):
    validate, project, issue = _authority()
    _append(billing_repo)
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    response = client.get("/v2/dashboard")
    assert response.status_code == 200
    assert b"demo" in response.data.lower()


def test_denied_before_dashboard_financial_reads(app, billing_repo, monkeypatch):
    """Absent evidence denies before the dashboard's first financial read runs."""
    validate, project, issue = _authority()

    def tripwire(user_id):
        raise AssertionError("dashboard financial read executed")

    monkeypatch.setattr(v2, "list_connections_for_user", tripwire)
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    response = client.get("/v2/dashboard")
    assert response.status_code == 403
    assert response.data == b""


def test_unresolved_membership_denies(app, billing_repo):
    """An authenticated user with no trusted membership scope is denied."""
    validate, project, issue = _authority()
    _append(billing_repo)
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id + 999, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    response = client.get("/v2/dashboard")
    assert response.status_code == 403


def test_deleted_user_denies(app, billing_repo):
    """A session pointing at a missing DB user is denied."""
    validate, project, issue = _authority()
    _append(billing_repo)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_v2_user_id"] = 999_999
        sess["_v2_clerk_id"] = "users:ghost"
        sess["_v2_email"] = "ghost@example.test"
        sess["_v2_display_name"] = "Ghost"
        sess["_v2_is_demo"] = True
    _install(app, user_id=999_999, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    response = client.get("/v2/dashboard")
    assert response.status_code == 403


def test_forged_session_identifier_denies(app, billing_repo):
    """A non-exact (string) session identifier is denied before financial work."""
    validate, project, issue = _authority()
    _append(billing_repo)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["_v2_user_id"] = "17"
        sess["_v2_clerk_id"] = "users:17"
        sess["_v2_is_demo"] = True
    _install(app, user_id=17, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    response = client.get("/v2/dashboard")
    assert response.status_code == 403


def test_structured_row_alone_never_grants(app, billing_repo):
    """A resolver issuing a raw stored row/tuple (not an admitted fact) denies."""
    validate, project, issue = _authority()
    _append(billing_repo)

    def raw_resolver(owner, account, subscription, content_identity, sequence):
        return ("paid", "provider_label_paid")

    install_local_dashboard_access(
        app,
        membership_resolver=_membership_resolver(1),
        snapshot_reader=_snapshot_reader(billing_repo),
        live_fact_resolver=raw_resolver,
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
        clock=lambda: CLOCK,
    )
    client, _ = _authenticated_client(app, clerk_id="users:17")
    # Rebind membership to the actual authenticated user for the denial path.
    response = client.get("/v2/dashboard")
    assert response.status_code == 403


# ── Paid and payment-recovery facts ──────────────────────────────────────────

def test_paid_and_payment_recovery_allow_dashboard(app, billing_repo):
    validate, project, issue = _authority()
    paid = _append(billing_repo)
    _append_recovery(billing_repo, paid)
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK_RECOVERY)
    assert client.get("/v2/dashboard").status_code == 200


def test_exact_recovery_expiry_denies(app, billing_repo):
    validate, project, issue = _authority()
    paid = _append(billing_repo)
    _append_recovery(billing_repo, paid)
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK_RECOVERY_EXPIRED)
    response = client.get("/v2/dashboard")
    assert response.status_code == 403
    assert response.data == b""


def test_verified_full_current_period_withdrawal_denies(app, billing_repo):
    validate, project, issue = _authority()
    paid = _append(billing_repo)
    _append_withdrawal(billing_repo, paid)
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK_WITHDRAWAL)
    response = client.get("/v2/dashboard")
    assert response.status_code == 403
    assert response.data == b""


# ── Competing successor, race, replay/fork, cross-scope ──────────────────────

def test_committed_successor_invalidates_previous_grant(app, billing_repo):
    """A 200 must not be cached: a committed withdrawal successor denies next."""
    validate, project, issue = _authority()
    paid = _append(billing_repo)
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    assert client.get("/v2/dashboard").status_code == 200
    _append_withdrawal(billing_repo, paid)
    assert client.get("/v2/dashboard").status_code == 403


def test_race_during_resolution_fails_closed(app, billing_repo):
    """Head changing between snapshot read and recheck must fail closed."""
    validate, project, issue = _authority()
    paid = _append(billing_repo)
    client, user_id = _authenticated_client(app)
    calls = {"n": 0}

    def racing_reader(owner, account, subscription):
        if (owner, account, subscription) != SCOPE:
            return None
        calls["n"] += 1
        if calls["n"] == 1:
            head = billing_repo.current_head(
                owner_id=owner, billing_account_id=account, subscription_id=subscription
            )
            records = billing_repo.journal(
                owner_id=owner, billing_account_id=account, subscription_id=subscription
            )
            entries = tuple(_entry_from_record(r) for r in records)
            # Commit a competing successor before the recheck.
            _append_withdrawal(billing_repo, paid)
            return BillingSnapshot(
                owner_id=owner, billing_account_id=account, subscription_id=subscription,
                head_identity=head.head_identity, head_sequence=head.sequence,
                entries=entries,
            )
        # Recheck sees the advanced head.
        return _snapshot_reader(billing_repo)(owner, account, subscription)

    install_local_dashboard_access(
        app,
        membership_resolver=_membership_resolver(user_id),
        snapshot_reader=racing_reader,
        live_fact_resolver=_live_fact_resolver(billing_repo, SCOPE, issue),
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
        clock=lambda: CLOCK_WITHDRAWAL,
    )
    response = client.get("/v2/dashboard")
    assert response.status_code == 403


def test_fork_or_backwards_head_denies(app, billing_repo):
    """A snapshot whose head does not match its own last entry is denied."""
    validate, project, issue = _authority()
    _append(billing_repo)
    client, user_id = _authenticated_client(app)

    def backwards_reader(owner, account, subscription):
        snap = _snapshot_reader(billing_repo)(owner, account, subscription)
        if snap is None:
            return None
        return BillingSnapshot(
            owner_id=snap.owner_id,
            billing_account_id=snap.billing_account_id,
            subscription_id=snap.subscription_id,
            head_identity=snap.head_identity,
            head_sequence=snap.head_sequence - 1,
            entries=snap.entries,
        )

    install_local_dashboard_access(
        app,
        membership_resolver=_membership_resolver(user_id),
        snapshot_reader=backwards_reader,
        live_fact_resolver=_live_fact_resolver(billing_repo, SCOPE, issue),
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
        clock=lambda: CLOCK,
    )
    assert client.get("/v2/dashboard").status_code == 403


def test_cross_scope_denies(app, billing_repo):
    """Facts for a different owner/account/subscription are denied."""
    validate, project, issue = _authority()
    _append(billing_repo)
    client, user_id = _authenticated_client(app)
    other_scope = ("users:99", "billing:99", "subscription:99")
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK, scope=other_scope)
    assert client.get("/v2/dashboard").status_code == 403


def test_replayed_fact_denies(app, billing_repo):
    """A replayed (duplicate-sequence) live fact is denied, never re-admitted."""
    validate, project, issue = _authority()
    paid = _append(billing_repo)
    _append_recovery(billing_repo, paid)
    client, user_id = _authenticated_client(app)

    records = billing_repo.journal(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    )
    facts = _facts(records)

    def replay_resolver(owner, account, subscription, content_identity, sequence):
        if (owner, account, subscription) != SCOPE:
            return None
        # Replays the first (paid, sequence=1) fact for every requested entry.
        return issue(facts[0])

    install_local_dashboard_access(
        app,
        membership_resolver=_membership_resolver(user_id),
        snapshot_reader=_snapshot_reader(billing_repo),
        live_fact_resolver=replay_resolver,
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
        clock=lambda: CLOCK_RECOVERY,
    )
    assert client.get("/v2/dashboard").status_code == 403


def test_forked_predecessor_denies(app, billing_repo):
    """A fork (an entry whose predecessor is not the previous entry) is denied."""
    validate, project, issue = _authority()
    paid = _append(billing_repo)
    _append_recovery(billing_repo, paid)
    client, user_id = _authenticated_client(app)

    def forked_reader(owner, account, subscription):
        snap = _snapshot_reader(billing_repo)(owner, account, subscription)
        if snap is None:
            return None
        first, second = snap.entries
        forked_second = replace(second, predecessor_identity=first.content_identity + "-fork")
        return BillingSnapshot(
            owner_id=snap.owner_id,
            billing_account_id=snap.billing_account_id,
            subscription_id=snap.subscription_id,
            head_identity=snap.head_identity,
            head_sequence=snap.head_sequence,
            entries=(first, forked_second),
        )

    install_local_dashboard_access(
        app,
        membership_resolver=_membership_resolver(user_id),
        snapshot_reader=forked_reader,
        live_fact_resolver=_live_fact_resolver(billing_repo, SCOPE, issue),
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
        clock=lambda: CLOCK_RECOVERY,
    )
    assert client.get("/v2/dashboard").status_code == 403


# ── Corruption, lock, restart/lost live authority ────────────────────────────

def test_repository_corruption_denies(app, billing_repo):
    validate, project, issue = _authority()
    _append(billing_repo)
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    assert client.get("/v2/dashboard").status_code == 200
    # Corrupt the SQLite file contents directly.
    with open(billing_repo._path, "wb") as fh:
        fh.write(b"not a sqlite database")
    assert client.get("/v2/dashboard").status_code == 403


def test_lost_live_authority_denies(app, billing_repo):
    """A resolver that loses its live evidence cannot rehydrate authority."""
    validate, project, issue = _authority()
    _append(billing_repo)
    client, user_id = _authenticated_client(app)

    def lost_resolver(owner, account, subscription, content_identity, sequence):
        return None

    install_local_dashboard_access(
        app,
        membership_resolver=_membership_resolver(user_id),
        snapshot_reader=_snapshot_reader(billing_repo),
        live_fact_resolver=lost_resolver,
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
        clock=lambda: CLOCK,
    )
    assert client.get("/v2/dashboard").status_code == 403


# ── Excluded surfaces: auth, CSRF, no-store ──────────────────────────────────

def test_unauthenticated_still_redirects_to_demo_login(app, billing_repo):
    validate, project, issue = _authority()
    _append(billing_repo)
    _install(app, user_id=1, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    client = app.test_client()
    response = client.get("/v2/dashboard")
    assert response.status_code == 302
    assert "/v2/demo-login" in response.location


def test_denial_has_no_store_headers(app, billing_repo):
    validate, project, issue = _authority()
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    response = client.get("/v2/dashboard")
    assert response.status_code == 403
    assert "no-store" in response.headers.get("Cache-Control", "")
    assert response.headers.get("Pragma") == "no-cache"


def test_installer_preserves_csrf_protection(app, billing_repo):
    """Installing the guard must not exempt the dashboard endpoint from CSRF."""
    from reserved.extensions import csrf
    validate, project, issue = _authority()
    _append(billing_repo)
    exempt_before = set(csrf._exempt_views)
    _install(app, user_id=1, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    assert "reserved.web.v2.dashboard_view" not in csrf._exempt_views
    assert set(csrf._exempt_views) == exempt_before


def test_other_paid_routes_are_not_wired(app, billing_repo):
    """Only the dashboard endpoint is gated; e.g. the overview stays open."""
    validate, project, issue = _authority()
    _append(billing_repo)
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    assert client.get("/v2/dashboard").status_code == 200
    assert client.get("/v2/").status_code == 200


# ── Defect 1: live-fact meaning/provenance binding ───────────────────────────

def test_recorded_withdrawal_rejects_substituted_ambiguous_fact(app, billing_repo):
    """A valid but substituted same-scope/sequence ambiguous fact cannot stand
    in for the recorded ``suspended`` / ``verified_full_withdrawal`` entry."""
    validate, project, issue = _authority()
    paid = _append(billing_repo)
    _append_withdrawal(billing_repo, paid)
    client, user_id = _authenticated_client(app)

    records = billing_repo.journal(
        owner_id=OWNER, billing_account_id=ACCOUNT, subscription_id=SUBSCRIPTION
    )
    facts = _facts(records)
    paid_identity = dict(facts[0])["fact_identity"]
    withdrawal_record = records[1]
    substituted = _ambiguous_preservation_fact(withdrawal_record, paid_identity)

    def substitute_resolver(owner, account, subscription, content_identity, sequence):
        if (owner, account, subscription) != SCOPE:
            return None
        if sequence < 1 or sequence > len(records):
            return None
        record = records[sequence - 1]
        if record.sequence != sequence or record.content_identity != content_identity:
            return None
        if sequence == 2:
            return issue(substituted)
        return issue(facts[sequence - 1])

    install_local_dashboard_access(
        app,
        membership_resolver=_membership_resolver(user_id),
        snapshot_reader=_snapshot_reader(billing_repo),
        live_fact_resolver=substitute_resolver,
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
        clock=lambda: CLOCK_WITHDRAWAL,
    )
    response = client.get("/v2/dashboard")
    assert response.status_code == 403
    assert response.data == b""


@pytest.mark.parametrize("changed_sequence", [1, 2])
def test_admission_time_fact_mutation_binds_every_immutable_outcome(
    app, billing_repo, monkeypatch, changed_sequence
):
    """Mutate only fact data at entry to the original real S3C validator.

    The original issuer/validator/projector and S3C functions stay unchanged.
    A tracing hook deterministically schedules the data race after the consumer's
    precheck, rather than replacing admission with a successful test result.
    """
    validate, project, issue = _authority()
    paid = _append(billing_repo)
    _append_withdrawal(billing_repo, paid)
    records = billing_repo.journal(owner_id=OWNER, billing_account_id=ACCOUNT,
                                   subscription_id=SUBSCRIPTION)
    facts = _facts(records)
    if changed_sequence == 2:
        replacement = _ambiguous_preservation_fact(records[1], dict(facts[0])["fact_identity"])
    else:
        values = dict(facts[0])
        values["valid_until_exclusive"] = date(2026, 10, 31)
        values["fact_identity"] = _fact_identity(values)
        replacement = tuple((key, values[key]) for key in FACT_KEYS)
    original_codes = (validate.__code__, project.__code__, s3c.admit_runtime_entitlement.__code__)
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK_WITHDRAWAL)
    touched, admitted = [], []
    financial_calls = []
    def tripwire(*args, **kwargs):
        financial_calls.append(True)
        raise AssertionError("financial read/render must not execute")
    monkeypatch.setattr(v2, "list_connections_for_user", tripwire)
    monkeypatch.setattr(v2, "render_template", tripwire)
    def trace(frame, event, argument):
        if frame.f_code is validate.__code__ and event == "call":
            fact = frame.f_locals["value"]
            if dict(fact.view)["decision_sequence"] == changed_sequence:
                assert fact.view == facts[changed_sequence - 1]
                fact.view = replacement
                touched.append(True)
        if frame.f_code is s3c.admit_runtime_entitlement.__code__ and event == "return" and argument is not None:
            admitted.append(dict(s3c.project_runtime_entitlement(argument)))
        return trace
    previous_trace = sys.gettrace()
    try:
        sys.settrace(trace)
        result = client.get("/v2/dashboard")
    finally:
        sys.settrace(previous_trace)
    assert touched == [True]
    assert len(admitted) == changed_sequence
    assert admitted[-1]["state"] == "paid" and admitted[-1]["ordinary_access"] is True
    assert result.status_code == 403 and result.data == b""
    assert "no-store" in result.headers["Cache-Control"]
    assert financial_calls == []
    assert original_codes == (validate.__code__, project.__code__, s3c.admit_runtime_entitlement.__code__)


def test_installed_guard_preserves_actual_modifying_request_csrf(app, billing_repo):
    """Existing settings POST still requires the existing Flask-WTF token.

    This does not claim a modifying dashboard route: dashboard itself is GET.
    Settings stays under its original auth/CSRF controls, outside this paid gate.
    """
    app.config["WTF_CSRF_ENABLED"] = True
    validate, project, issue = _authority()
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    assert client.get("/v2/dashboard").status_code == 403
    before = db.get_profile_by_user(user_id)
    for data in ({}, {"csrf_token": "forged-test-token"}):
        denied = client.post("/v2/settings", data=data)
        assert denied.status_code == 400
        assert db.get_profile_by_user(user_id) == before
    rendered = client.get("/v2/settings")
    assert rendered.status_code == 200
    token = re.search(rb'name="csrf_token" value="([^"]+)"', rendered.data).group(1).decode()
    updated = client.post("/v2/settings", data={"csrf_token": token,
        "entity_type": "sole_trader", "student_loan": "none",
        "accounting_method": "cash_basis", "vat_status": "not_vat_registered"})
    assert updated.status_code == 302 and updated.headers["Location"].endswith("/v2/dashboard")
    assert db.get_profile_by_user(user_id) is not None
    assert client.get("/v2/dashboard").status_code == 403


# ── Defect 2: full scoped snapshot/chain recheck, not just head labels ───────

def test_recheck_scope_change_denies(app, billing_repo):
    """A recheck that keeps the head but changes owner/account/subscription denies."""
    validate, project, issue = _authority()
    _append(billing_repo)
    client, user_id = _authenticated_client(app)
    calls = {"n": 0}

    def scope_change_reader(owner, account, subscription):
        calls["n"] += 1
        snap = _snapshot_reader(billing_repo)(owner, account, subscription)
        if snap is None:
            return None
        if calls["n"] == 2:
            return BillingSnapshot(
                owner_id="users:999",
                billing_account_id=snap.billing_account_id,
                subscription_id=snap.subscription_id,
                head_identity=snap.head_identity,
                head_sequence=snap.head_sequence,
                entries=snap.entries,
            )
        return snap

    install_local_dashboard_access(
        app,
        membership_resolver=_membership_resolver(user_id),
        snapshot_reader=scope_change_reader,
        live_fact_resolver=_live_fact_resolver(billing_repo, SCOPE, issue),
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
        clock=lambda: CLOCK,
    )
    assert client.get("/v2/dashboard").status_code == 403


def test_recheck_preceding_content_change_denies(app, billing_repo):
    """A recheck that retains the head but alters a preceding entry denies."""
    validate, project, issue = _authority()
    paid = _append(billing_repo)
    _append_recovery(billing_repo, paid)
    client, user_id = _authenticated_client(app)
    calls = {"n": 0}

    def content_change_reader(owner, account, subscription):
        calls["n"] += 1
        snap = _snapshot_reader(billing_repo)(owner, account, subscription)
        if snap is None:
            return None
        if calls["n"] == 2:
            first = snap.entries[0]
            tampered_first = replace(first, content_identity=first.content_identity + "-tampered")
            return BillingSnapshot(
                owner_id=snap.owner_id,
                billing_account_id=snap.billing_account_id,
                subscription_id=snap.subscription_id,
                head_identity=snap.head_identity,
                head_sequence=snap.head_sequence,
                entries=(tampered_first,) + snap.entries[1:],
            )
        return snap

    install_local_dashboard_access(
        app,
        membership_resolver=_membership_resolver(user_id),
        snapshot_reader=content_change_reader,
        live_fact_resolver=_live_fact_resolver(billing_repo, SCOPE, issue),
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
        clock=lambda: CLOCK_RECOVERY,
    )
    assert client.get("/v2/dashboard").status_code == 403


# ── Defect 3: malformed or unavailable dependencies fail closed ──────────────

def test_malformed_snapshot_entries_deny(app, billing_repo):
    """``entries=(None,)`` fails closed before financial reads, not AttributeError."""
    validate, project, issue = _authority()
    _append(billing_repo)
    client, user_id = _authenticated_client(app)

    def malformed_reader(owner, account, subscription):
        snap = _snapshot_reader(billing_repo)(owner, account, subscription)
        if snap is None:
            return None
        return BillingSnapshot(
            owner_id=snap.owner_id,
            billing_account_id=snap.billing_account_id,
            subscription_id=snap.subscription_id,
            head_identity=snap.head_identity,
            head_sequence=snap.head_sequence,
            entries=(None,),
        )

    install_local_dashboard_access(
        app,
        membership_resolver=_membership_resolver(user_id),
        snapshot_reader=malformed_reader,
        live_fact_resolver=_live_fact_resolver(billing_repo, SCOPE, issue),
        validate_admitted_billing_fact=validate,
        project_admitted_billing_fact=project,
        clock=lambda: CLOCK,
    )
    response = client.get("/v2/dashboard")
    assert response.status_code == 403
    assert response.data == b""


def test_current_user_lookup_exception_denies(app, billing_repo, monkeypatch):
    """A current-user lookup failure fails closed with a value-free 403."""
    validate, project, issue = _authority()
    _append(billing_repo)
    client, user_id = _authenticated_client(app)

    def boom(user_id):
        raise RuntimeError("user store unavailable")

    monkeypatch.setattr("reserved.database.get_user", boom)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    response = client.get("/v2/dashboard")
    assert response.status_code == 403
    assert response.data == b""


def test_clock_exception_denies(app, billing_repo):
    """A clock failure fails closed before any financial read."""
    validate, project, issue = _authority()
    _append(billing_repo)
    client, user_id = _authenticated_client(app)

    def broken_clock():
        raise RuntimeError("clock unavailable")

    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=broken_clock)
    response = client.get("/v2/dashboard")
    assert response.status_code == 403
    assert response.data == b""


# ── Defect 4: ambiguous preservation, restoration and extension ──────────────

def test_ambiguous_preservation_allows_then_expired_denies(app, billing_repo):
    """Independently admitted ambiguous evidence preserves existing access only
    while the prior paid entitlement is still valid, then denies."""
    validate, project, issue = _authority()
    paid = _append(billing_repo)
    _append_ambiguous(billing_repo, paid)
    client, user_id = _authenticated_client(app)
    clock_state = {"now": CLOCK_WITHDRAWAL}
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: clock_state["now"])
    assert client.get("/v2/dashboard").status_code == 200
    clock_state["now"] = datetime(2026, 11, 2, 12, tzinfo=UTC)
    assert client.get("/v2/dashboard").status_code == 403


def test_verified_restoration_allows_dashboard(app, billing_repo):
    """Independently admitted verified reinstatement after a withdrawal restores 200."""
    validate, project, issue = _authority()
    paid = _append(billing_repo)
    withdrawal = _append_withdrawal(billing_repo, paid)
    _append_restoration(billing_repo, withdrawal)
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK_RESTORATION)
    assert client.get("/v2/dashboard").status_code == 200


def test_prohibited_restoration_denies(app, billing_repo):
    """A reinstatement with no suspended withdrawal lineage is denied."""
    validate, project, issue = _authority()
    paid = _append(billing_repo)
    _append_reinstatement_without_withdrawal(billing_repo, paid)
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK_WITHDRAWAL)
    response = client.get("/v2/dashboard")
    assert response.status_code == 403
    assert response.data == b""


def test_ambiguous_extension_denies(app, billing_repo):
    """Ambiguous evidence cannot extend the prior paid validity window."""
    validate, project, issue = _authority()
    paid = _append(billing_repo)
    _append(
        billing_repo,
        source_event_id="evt-7",
        source_event_digest="sha256:" + "1" * 64,
        observation_kind="dispute_observed",
        effective_date=date(2026, 10, 15),
        paid_through=None,
        evidence_reference="evidence/ref-7",
        state="paid",
        valid_from_inclusive=date(2026, 10, 1),
        valid_until_exclusive=date(2026, 11, 8),
        transition_effective_at_utc=datetime(2026, 10, 15, tzinfo=UTC),
        recovery_deadline_exclusive_at_utc=None,
        derivation_kind="withdrawal_ambiguous",
        withdrawal_attribution="unknown",
        expected_predecessor_identity=paid.content_identity,
        expected_sequence=2,
        recorded_at_utc=datetime(2026, 10, 15, 12, tzinfo=UTC),
    )
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK_WITHDRAWAL)
    response = client.get("/v2/dashboard")
    assert response.status_code == 403
    assert response.data == b""


# ── SQLite lock / reopen / restart ───────────────────────────────────────────

def test_closed_repository_denies(app, billing_repo):
    """A closed repository fails closed rather than rehydrating a stale grant."""
    validate, project, issue = _authority()
    _append(billing_repo)
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    assert client.get("/v2/dashboard").status_code == 200
    billing_repo.close()
    assert client.get("/v2/dashboard").status_code == 403


def test_reopen_recomputes_access(app, billing_repo):
    """Close the original repository before reopening and recomputing access."""
    validate, project, issue = _authority()
    paid = _append(billing_repo)
    path = billing_repo._path
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    assert client.get("/v2/dashboard").status_code == 200
    billing_repo.close()
    assert client.get("/v2/dashboard").status_code == 403
    reopened = LocalBillingRepository.open(path)
    try:
        fresh_app = create_app()
        fresh_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        client2, user_id2 = _authenticated_client(fresh_app)
        _install(fresh_app, user_id=user_id2, repo=reopened, validate=validate,
                 project=project, issue=issue, clock=lambda: CLOCK)
        assert client2.get("/v2/dashboard").status_code == 200
        _append_withdrawal(reopened, paid)
        assert client2.get("/v2/dashboard").status_code == 403
    finally:
        reopened.close()


def test_sqlite_lock_denies(app, tmp_path):
    """An exclusively locked SQLite journal fails closed, not a stale 200."""
    validate, project, issue = _authority()
    repo = LocalBillingRepository.create(tmp_path / "locked.db", busy_timeout_seconds=0.2)
    try:
        _append(repo)
        client, user_id = _authenticated_client(app)
        _install(app, user_id=user_id, repo=repo, validate=validate,
                 project=project, issue=issue, clock=lambda: CLOCK)
        assert client.get("/v2/dashboard").status_code == 200
        blocker = sqlite3.connect(str(tmp_path / "locked.db"), isolation_level=None)
        try:
            blocker.execute("BEGIN EXCLUSIVE")
            assert client.get("/v2/dashboard").status_code == 403
        finally:
            blocker.execute("ROLLBACK")
            blocker.close()
    finally:
        repo.close()


# ── Defect 5: dual production signal enforced at request time ────────────────

def test_production_env_flip_after_install_denies(app, billing_repo, monkeypatch):
    """FLASK_ENV flipping to production after install denies the request."""
    validate, project, issue = _authority()
    _append(billing_repo)
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    assert client.get("/v2/dashboard").status_code == 200
    monkeypatch.setenv("FLASK_ENV", "production")
    assert client.get("/v2/dashboard").status_code == 403


def test_live_clerk_key_flip_after_install_denies(app, billing_repo, monkeypatch):
    """A live Clerk publishable key appearing after install denies the request."""
    validate, project, issue = _authority()
    _append(billing_repo)
    client, user_id = _authenticated_client(app)
    _install(app, user_id=user_id, repo=billing_repo, validate=validate,
             project=project, issue=issue, clock=lambda: CLOCK)
    assert client.get("/v2/dashboard").status_code == 200
    monkeypatch.setenv("CLERK_PUBLISHABLE_KEY", "pk_live_deadbeef")
    assert client.get("/v2/dashboard").status_code == 403
