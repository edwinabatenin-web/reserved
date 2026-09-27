"""Focused hostile tests for the pure W10-S5D paid-access guard."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import pickle
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

import reserved.billing.entitlement_core as structural_s3a
import reserved.billing.paid_access_guard as subject


ROOT = Path(__file__).resolve().parents[1]
BASE = "6f3cb30d1bedcebe930084d56c64ab83ff719d5a"
BASE_TREE = "ef36688a8bd07a58b98aa54412cd14b1d7c7d86c"
SOURCE_CHECKPOINT = "88a3c879fbacad9e3f9feebe02764499f1f53daa"
INTEGRATION_PARENT = "47d2ae9c1faf220789bc8ec75f7898c3dca4651a"
INTEGRATION_CHECKPOINT = "824b3060c950ce7f623d29aeadc53ede34b6c565"
OWNED_PATHS = {
    "docs/W10_S5D_PAID_ACCESS_GUARD.md",
    "reserved/billing/paid_access_guard.py",
    "tests/test_w10_paid_access_guard.py",
}
RUNTIME_KEYS = (
    "protocol_version",
    "decision_identity",
    "admission_status",
    "authenticated",
    "runtime_access_authority",
    "owner_id",
    "decision_sequence",
    "predecessor_identity",
    "state",
    "ordinary_access",
    "valid_from_inclusive",
    "valid_until_exclusive",
    "transition_effective_at_utc",
    "recovery_deadline_exclusive_at_utc",
    "predecessor_entitled_access",
    "predecessor_owner_id",
    "derivation_kind",
    "withdrawal_attribution",
)


def git_text(*args):
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def runtime_identity(values):
    material = (
        values["protocol_version"],
        values["admission_status"],
        values["authenticated"],
        values["runtime_access_authority"],
        values["owner_id"],
        values["decision_sequence"],
        values["predecessor_identity"],
        values["state"],
        values["ordinary_access"],
        values["valid_from_inclusive"].isoformat(),
        values["valid_until_exclusive"].isoformat(),
        values["transition_effective_at_utc"].isoformat(),
        (
            None
            if values["recovery_deadline_exclusive_at_utc"] is None
            else values["recovery_deadline_exclusive_at_utc"].isoformat()
        ),
        values["predecessor_entitled_access"],
        values["predecessor_owner_id"],
        values["derivation_kind"],
        values["withdrawal_attribution"],
    )
    payload = json.dumps(material, ensure_ascii=True, separators=(",", ":"))
    return "runtime-entitlement:sha256-" + hashlib.sha256(
        payload.encode("ascii")
    ).hexdigest()


def runtime_view(**changes):
    values = {
        "protocol_version": subject.RUNTIME_DECISION_PROTOCOL_VERSION,
        "decision_identity": "",
        "admission_status": subject.RUNTIME_ADMISSION_STATUS,
        "authenticated": True,
        "runtime_access_authority": True,
        "owner_id": "users:17",
        "decision_sequence": 1,
        "predecessor_identity": None,
        "state": "paid",
        "ordinary_access": True,
        "valid_from_inclusive": date(2026, 9, 1),
        "valid_until_exclusive": date(2026, 10, 1),
        "transition_effective_at_utc": datetime(2026, 9, 1, tzinfo=timezone.utc),
        "recovery_deadline_exclusive_at_utc": None,
        "predecessor_entitled_access": False,
        "predecessor_owner_id": None,
        "derivation_kind": "verified_initial_payment",
        "withdrawal_attribution": "not_applicable",
    }
    values.update(changes)
    if "decision_identity" not in changes:
        values["decision_identity"] = runtime_identity(values)
    return tuple((key, values[key]) for key in RUNTIME_KEYS)


class LiveRuntimeDecision:
    __slots__ = ("view",)

    def __init__(self, view):
        self.view = view


def authority(*, validator_transform=None, projector_transform=None):
    live = set()

    def issue(view):
        decision = LiveRuntimeDecision(view)
        live.add(id(decision))
        return decision

    def validate(value):
        if type(value) is not LiveRuntimeDecision or id(value) not in live:
            raise ValueError("not admitted by the runtime authority")
        view = value.view
        return validator_transform(view) if validator_transform else view

    def project(value):
        if type(value) is not LiveRuntimeDecision or id(value) not in live:
            raise ValueError("not admitted by the runtime authority")
        view = value.view
        return projector_transform(view) if projector_transform else view

    return issue, validate, project


def guard_and_decision(view=None, **authority_kwargs):
    issue, validate, project = authority(**authority_kwargs)
    guard = subject.bind_paid_access_guard(
        validate_runtime_entitlement=validate,
        project_runtime_entitlement=project,
    )
    return guard, issue(runtime_view() if view is None else view)


def guard_and_boundary(prior_view, current_view, **authority_kwargs):
    issue, validate, project = authority(**authority_kwargs)
    guard = subject.bind_paid_access_guard(
        validate_runtime_entitlement=validate,
        project_runtime_entitlement=project,
    )
    prior = None if prior_view is None else issue(prior_view)
    return guard, prior, issue(current_view)


def successor(prior_view, **changes):
    values = dict(prior_view)
    values.update(
        {
            "decision_identity": "",
            "decision_sequence": values["decision_sequence"] + 1,
            "predecessor_identity": values["decision_identity"],
            "predecessor_entitled_access": (
                values["state"] in {"paid", "payment_recovery"}
                and values["ordinary_access"] is True
            ),
            "predecessor_owner_id": (
                values["owner_id"]
                if values["state"] in {"paid", "payment_recovery"}
                and values["ordinary_access"] is True
                else None
            ),
            "transition_effective_at_utc": datetime(
                2026, 9, 15, tzinfo=timezone.utc
            ),
            "recovery_deadline_exclusive_at_utc": None,
            "derivation_kind": "existing_derived_access",
            "withdrawal_attribution": "not_applicable",
        }
    )
    values.update(changes)
    if "decision_identity" not in changes:
        values["decision_identity"] = runtime_identity(values)
    return tuple((key, values[key]) for key in RUNTIME_KEYS)


def full_current_period_suspension(entitled_view=None, **changes):
    prior = runtime_view() if entitled_view is None else entitled_view
    return successor(
        prior,
        state="suspended",
        ordinary_access=False,
        derivation_kind="verified_full_withdrawal",
        withdrawal_attribution="current_subscription_period",
        **changes,
    )


def evaluate(guard, current_runtime_entitlement, *, prior=None, **changes):
    inputs = {
        "endpoint": "v2.index",
        "authenticated_owner_id": "users:17",
        "prior_runtime_entitlement": prior,
        "current_runtime_entitlement": current_runtime_entitlement,
        "evaluated_at_utc": datetime(2026, 9, 15, 12, tzinfo=timezone.utc),
    }
    inputs.update(changes)
    handle = subject.evaluate_paid_access(guard, **inputs)
    return dict(subject.validate_paid_access_decision(handle))


def replace_pair(value, key, replacement):
    return tuple((name, replacement if name == key else item) for name, item in value)


def inventory_paid_endpoints():
    text = (ROOT / "docs/W10_S5A_PAID_SURFACE_INVENTORY.md").read_text()
    body = text.split("<!-- W10-S5A-INVENTORY-BEGIN -->", 1)[1]
    body = body.split("<!-- W10-S5A-INVENTORY-END -->", 1)[0].strip()
    payload = json.loads(body.removeprefix("```json\n").removesuffix("```").strip())
    return tuple(
        route["endpoint"]
        for route in payload["routes"]
        if route["classification"]
        == "authenticated_product_candidate_pending_founder_decision"
    )


def test_candidate_is_confined_to_exact_three_owned_paths_and_base():
    changed = git_text("diff", "--name-only", "HEAD").splitlines()
    untracked = git_text("ls-files", "--others", "--exclude-standard").splitlines()
    allowed = {"tests/test_w10_paid_access_guard.py"}
    if (changed or untracked) and git_text("branch", "--show-current") == "astra/hicbc-annual-source-runtime":
        assert git_text("rev-parse", "HEAD") == "5d91ae0c83bf696cb650d90daa8d25417e466157"
        allowed |= {
            "reserved/services/hicbc_annual_source_runtime.py", "reserved/web/hicbc.py",
            "reserved/database.py", "reserved/config.py",
            "tests/test_hicbc_annual_source_runtime.py", "tests/test_internal_tax_boundary.py",
            "docs/HICBC_ANNUAL_SOURCE_RUNTIME_EVIDENCE.md",
            "docs/W10_S5A_PAID_SURFACE_INVENTORY.md", "tests/test_w10_paid_surface_inventory.py",
            "docs/W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md",
            "reserved/billing/paid_access_guard.py", "docs/W10_S5D_PAID_ACCESS_GUARD.md",
        }
    if (changed or untracked) and git_text("branch", "--show-current") == "sol/w10-stripe-full-withdrawal":
        assert git_text("rev-parse", "HEAD") == "4ba6330b9edec8f5be20245bb7f1e47154e14854"
        allowed |= {
            "reserved/billing/local_stripe_initial_payment.py",
            "reserved/billing/local_billing_provenance_repository.py",
            "reserved/billing/runtime_entitlement_admission.py",
            "reserved/billing/paid_access_guard.py",
            "reserved/billing/local_paid_surface_access.py",
            "tests/test_w10_stripe_full_withdrawal.py",
            "tests/test_w10_billing_provenance_full_withdrawal.py",
            "tests/test_w10_exact_utc_full_withdrawal.py",
            "tests/test_w10_runtime_entitlement_full_withdrawal.py",
            "tests/test_w10_full_withdrawal_paid_surface_access.py",
            "tests/test_w10_billing_provenance_failed_renewal.py",
            "tests/test_w10_billing_provenance_successful_renewal.py",
            "tests/test_w10_runtime_entitlement_admission.py",
            "tests/test_w10_paid_access_guard.py",
            "docs/W10_STRIPE_FULL_WITHDRAWAL_EVIDENCE.md",
        }
    if (changed or untracked) and git_text("branch", "--show-current") == "sol/w10-later-period-restoration":
        assert git_text("rev-parse", "HEAD") == "d4bb9a579c40e0f06710c84654efd98495513370"
        allowed |= {
            "reserved/billing/local_stripe_initial_payment.py",
            "reserved/billing/local_billing_provenance_repository.py",
            "reserved/billing/runtime_entitlement_admission.py",
            "reserved/billing/paid_access_guard.py",
            "tests/test_w10_stripe_later_period_restoration.py",
            "tests/test_w10_billing_provenance_later_period_restoration.py",
            "tests/test_w10_exact_utc_later_period_restoration.py",
            "tests/test_w10_runtime_entitlement_later_period_restoration.py",
            "tests/test_w10_later_period_restoration_paid_surface_access.py",
            "tests/test_w10_billing_provenance_failed_renewal.py",
            "tests/test_w10_billing_provenance_successful_renewal.py",
            "tests/test_w10_billing_provenance_full_withdrawal.py",
            "tests/test_w10_runtime_entitlement_admission.py",
            "tests/test_w10_paid_access_guard.py",
            "docs/W10_STRIPE_LATER_PERIOD_RESTORATION_EVIDENCE.md",
        }
    if (changed or untracked) and git_text("branch", "--show-current") == "codex/launch-paye":
        assert git_text("rev-parse", "HEAD") == "8517a482bd315c93a793bdb32623e784a4766a85"
        allowed |= {
            "docs/W10_S5A_PAID_SURFACE_INVENTORY.md",
            "reserved/billing/local_paid_surface_access.py",
            "reserved/billing/paid_access_guard.py",
            "reserved/config.py", "reserved/database.py",
            "reserved/paye_annual_bridge.py",
            "reserved/services/paye_customer_orchestration.py",
            "reserved/services/paye_manual_baseline.py",
            "reserved/templates/v2/dashboard.html",
            "reserved/templates/v2/paye_manual_journey.html",
            "reserved/web/v2.py",
            "tests/test_paye_annual_bridge.py",
            "tests/test_paye_customer_orchestration.py",
            "tests/test_hicbc_linked_account.py",
            "tests/test_w10_full_withdrawal_paid_surface_access.py",
            "tests/test_w10_later_period_restoration_paid_surface_access.py",
            "tests/test_w10_local_paid_surface_access.py",
            "tests/test_w10_paid_access_guard.py",
            "tests/test_w10_paid_surface_inventory.py",
            "tests/test_w10_stripe_initial_payment_ingress.py",
        }
    assert set(changed + untracked) <= allowed

    assert git_text("rev-parse", f"{BASE}^{{tree}}") == BASE_TREE
    for checkpoint, parent in (
        (SOURCE_CHECKPOINT, BASE),
        (INTEGRATION_CHECKPOINT, INTEGRATION_PARENT),
    ):
        assert git_text("rev-parse", f"{checkpoint}^") == parent
        paths = set(
            git_text("diff-tree", "--no-commit-id", "--name-only", "-r", checkpoint)
            .splitlines()
        )
        assert paths == OWNED_PATHS


def test_paid_endpoint_boundary_is_exact_s5a_settled_class():
    assert len(subject.PAID_ENDPOINTS) == 34
    assert len(set(subject.PAID_ENDPOINTS)) == 34
    assert "v2.paye_manual_baseline" in subject.PAID_ENDPOINTS
    assert "v2.paye_manual_journey" in subject.PAID_ENDPOINTS
    assert "v2.delete_paye_manual_journey_entry" in subject.PAID_ENDPOINTS
    assert "v2.paye_durable_current_position" in subject.PAID_ENDPOINTS
    assert "v2.paye_durable_current_forecast" in subject.PAID_ENDPOINTS
    assert "hicbc.durable_current_annual_position" in subject.PAID_ENDPOINTS
    assert "hicbc.linked_current_annual_position" in subject.PAID_ENDPOINTS
    assert "v2.mtd_manual_scope" in subject.PAID_ENDPOINTS
    assert subject.PAID_ENDPOINTS == inventory_paid_endpoints()
    assert "v2.billing_plans" not in subject.PAID_ENDPOINTS
    assert "api.health" not in subject.PAID_ENDPOINTS
    assert "founder.dashboard" not in subject.PAID_ENDPOINTS


@pytest.mark.parametrize("endpoint", subject.PAID_ENDPOINTS)
def test_exact_initial_paid_decision_can_allow_each_paid_endpoint(endpoint):
    guard, runtime = guard_and_decision()
    result = evaluate(guard, runtime, endpoint=endpoint)
    assert result["allowed"] is True
    assert result["reason"] == "allowed_initial_payment"
    assert result["endpoint"] == endpoint
    assert result["provider_contacted"] is False
    assert result["persisted"] is False
    assert result["route_wiring_active"] is False


def test_admitted_first_renewal_failure_establishes_bounded_payment_recovery():
    prior_view = runtime_view()
    current_view = successor(
        prior_view,
        state="payment_recovery",
        derivation_kind="verified_renewal_failure",
        valid_until_exclusive=date(2026, 10, 8),
        transition_effective_at_utc=datetime(2026, 10, 1, tzinfo=timezone.utc),
        recovery_deadline_exclusive_at_utc=datetime(
            2026, 10, 8, tzinfo=timezone.utc
        ),
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(
        guard,
        current,
        prior=prior,
        evaluated_at_utc=datetime(2026, 10, 2, 12, tzinfo=timezone.utc),
    )
    assert result["allowed"] is True
    assert result["reason"] == "allowed_payment_recovery"


@pytest.mark.parametrize(
    "changes",
    (
        {"recovery_deadline_exclusive_at_utc": datetime(2026, 10, 7, tzinfo=timezone.utc),
         "valid_until_exclusive": date(2026, 10, 7)},
        {"recovery_deadline_exclusive_at_utc": datetime(2026, 10, 9, tzinfo=timezone.utc),
         "valid_until_exclusive": date(2026, 10, 9)},
        {"transition_effective_at_utc": datetime(2026, 9, 30, tzinfo=timezone.utc),
         "recovery_deadline_exclusive_at_utc": datetime(2026, 10, 7, tzinfo=timezone.utc),
         "valid_until_exclusive": date(2026, 10, 7)},
        {"transition_effective_at_utc": datetime(2026, 10, 1, 12, tzinfo=timezone.utc),
         "recovery_deadline_exclusive_at_utc": datetime(2026, 10, 8, 12, tzinfo=timezone.utc)},
    ),
)
def test_payment_recovery_rejects_short_long_shifted_or_non_calendar_intervals(changes):
    prior_view = runtime_view()
    recovery_values = {
        "state": "payment_recovery",
        "derivation_kind": "verified_renewal_failure",
        "valid_until_exclusive": date(2026, 10, 8),
        "transition_effective_at_utc": datetime(2026, 10, 1, tzinfo=timezone.utc),
        "recovery_deadline_exclusive_at_utc": datetime(
            2026, 10, 8, tzinfo=timezone.utc
        ),
    }
    recovery_values.update(changes)
    current_view = successor(
        prior_view,
        **recovery_values,
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(guard, current, prior=prior)
    assert result["allowed"] is False
    assert result["reason"] in {
        "runtime_entitlement_invalid",
        "runtime_entitlement_temporal_order_invalid",
        "restoration_boundary_invalid",
    }


def test_repeated_failure_cannot_extend_existing_payment_recovery():
    paid = runtime_view()
    recovery = successor(
        paid,
        state="payment_recovery",
        derivation_kind="verified_renewal_failure",
        valid_until_exclusive=date(2026, 10, 8),
        transition_effective_at_utc=datetime(2026, 10, 1, tzinfo=timezone.utc),
        recovery_deadline_exclusive_at_utc=datetime(2026, 10, 8, tzinfo=timezone.utc),
    )
    repeated = successor(
        recovery,
        derivation_kind="verified_renewal_failure",
        valid_until_exclusive=date(2026, 10, 15),
        transition_effective_at_utc=datetime(2026, 10, 8, tzinfo=timezone.utc),
        recovery_deadline_exclusive_at_utc=datetime(2026, 10, 15, tzinfo=timezone.utc),
    )
    guard, prior, current = guard_and_boundary(recovery, repeated)
    result = evaluate(
        guard,
        current,
        prior=prior,
        evaluated_at_utc=datetime(2026, 10, 9, 12, tzinfo=timezone.utc),
    )
    assert result["allowed"] is False
    assert result["reason"] == "restoration_boundary_invalid"


@pytest.mark.parametrize(
    ("endpoint", "reason"),
    (
        ("api.health", "endpoint_not_in_paid_boundary"),
        ("v2.billing_plans", "endpoint_not_in_paid_boundary"),
        ("founder.dashboard", "endpoint_not_in_paid_boundary"),
        ("", "endpoint_not_in_paid_boundary"),
        (None, "endpoint_not_in_paid_boundary"),
    ),
)
def test_non_paid_or_malformed_endpoint_never_allows(endpoint, reason):
    guard, runtime = guard_and_decision()
    result = evaluate(guard, runtime, endpoint=endpoint)
    assert result["allowed"] is False
    assert result["reason"] == reason


@pytest.mark.parametrize(
    "owner",
    (None, "", " users:17", "users:17 ", "users:token", 17, True),
)
def test_missing_malformed_or_secret_shaped_authenticated_owner_denies(owner):
    guard, runtime = guard_and_decision()
    result = evaluate(guard, runtime, authenticated_owner_id=owner)
    assert result["allowed"] is False
    assert result["reason"] == "authenticated_owner_unavailable"


def test_missing_or_detached_structural_s3a_candidate_denies():
    guard, _ = guard_and_decision()
    missing = evaluate(guard, None)
    assert missing["reason"] == "runtime_entitlement_missing"
    structural = structural_s3a.empty_entitlement(
        owner_id="users:17",
        billing_account_id="billing-17",
        subscription_id="subscription-17",
    )
    detached = evaluate(guard, structural)
    assert detached["allowed"] is False
    assert detached["reason"] == "runtime_entitlement_invalid"


def test_exact_detached_runtime_tuple_is_not_itself_admission():
    view = runtime_view()
    guard, _ = guard_and_decision(view)
    result = evaluate(guard, view)
    assert result["allowed"] is False
    assert result["reason"] == "runtime_entitlement_invalid"


@pytest.mark.parametrize(
    ("changes", "reason"),
    (
        ({"protocol_version": "future-version"}, "runtime_entitlement_invalid"),
        ({"admission_status": "structural_only"}, "runtime_entitlement_not_admitted"),
        ({"authenticated": False}, "runtime_entitlement_unauthenticated"),
        ({"runtime_access_authority": False}, "runtime_access_authority_missing"),
        ({"owner_id": "users:18"}, "cross_owner_entitlement"),
        ({"derivation_kind": "provider_status_active"}, "unknown_derivation_kind"),
    ),
)
def test_non_authoritative_cross_owner_and_unknown_derivation_deny(changes, reason):
    guard, runtime = guard_and_decision(runtime_view(**changes))
    result = evaluate(guard, runtime)
    assert result["allowed"] is False
    assert result["reason"] == reason


@pytest.mark.parametrize(
    ("evaluated_at_utc", "reason"),
    (
        (
            datetime(2026, 8, 31, 23, 59, tzinfo=timezone.utc),
            "runtime_entitlement_temporal_order_invalid",
        ),
        (
            datetime(2026, 10, 1, tzinfo=timezone.utc),
            "runtime_entitlement_stale",
        ),
    ),
)
def test_not_yet_valid_or_expired_runtime_decision_denies(evaluated_at_utc, reason):
    guard, runtime = guard_and_decision()
    result = evaluate(guard, runtime, evaluated_at_utc=evaluated_at_utc)
    assert result["allowed"] is False
    assert result["reason"] == reason


@pytest.mark.parametrize(
    "evaluated_at_utc",
    (
        None,
        True,
        "2026-09-15T12:00:00Z",
        date(2026, 9, 15),
        datetime(2026, 9, 15, 12),
        datetime(2026, 9, 15, 12, tzinfo=timezone(timedelta(hours=1))),
        object(),
    ),
)
def test_evaluation_requires_exact_timezone_aware_utc_datetime(evaluated_at_utc):
    guard, runtime = guard_and_decision()
    with pytest.raises(TypeError, match="exact timezone-aware UTC datetime"):
        evaluate(guard, runtime, evaluated_at_utc=evaluated_at_utc)


def test_future_initial_payment_cannot_grant_access():
    view = runtime_view(
        transition_effective_at_utc=datetime(
            2026, 9, 15, 12, tzinfo=timezone.utc
        )
    )
    guard, runtime = guard_and_decision(view)
    result = evaluate(
        guard,
        runtime,
        evaluated_at_utc=datetime(2026, 9, 15, 11, 59, 59, tzinfo=timezone.utc),
    )
    assert result["allowed"] is False
    assert result["reason"] == "runtime_entitlement_temporal_order_invalid"


def test_future_full_withdrawal_cannot_change_current_access():
    prior_view = runtime_view()
    current_view = full_current_period_suspension(
        prior_view,
        transition_effective_at_utc=datetime(
            2026, 9, 15, 12, tzinfo=timezone.utc
        ),
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(
        guard,
        current,
        prior=prior,
        evaluated_at_utc=datetime(2026, 9, 15, 11, 59, 59, tzinfo=timezone.utc),
    )
    assert result["allowed"] is False
    assert result["reason"] == "runtime_entitlement_temporal_order_invalid"


def test_future_renewal_failure_cannot_start_payment_recovery():
    prior_view = runtime_view()
    current_view = successor(
        prior_view,
        state="payment_recovery",
        derivation_kind="verified_renewal_failure",
        valid_until_exclusive=date(2026, 10, 8),
        transition_effective_at_utc=datetime(2026, 10, 1, tzinfo=timezone.utc),
        recovery_deadline_exclusive_at_utc=datetime(
            2026, 10, 8, tzinfo=timezone.utc
        ),
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(
        guard,
        current,
        prior=prior,
        evaluated_at_utc=datetime(
            2026, 9, 30, 23, 59, 59, 999999, tzinfo=timezone.utc
        ),
    )
    assert result["allowed"] is False
    assert result["reason"] == "runtime_entitlement_temporal_order_invalid"


def test_current_transition_cannot_precede_its_predecessor_transition():
    prior_view = runtime_view(
        transition_effective_at_utc=datetime(2026, 9, 10, tzinfo=timezone.utc)
    )
    current_view = successor(
        prior_view,
        transition_effective_at_utc=datetime(2026, 9, 9, tzinfo=timezone.utc),
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(guard, current, prior=prior)
    assert result["allowed"] is False
    assert result["reason"] == "runtime_entitlement_temporal_order_invalid"


def test_future_predecessor_and_successor_pair_cannot_be_admitted():
    prior_view = runtime_view(
        transition_effective_at_utc=datetime(2026, 9, 20, tzinfo=timezone.utc)
    )
    current_view = successor(
        prior_view,
        transition_effective_at_utc=datetime(2026, 9, 21, tzinfo=timezone.utc),
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(guard, current, prior=prior)
    assert result["allowed"] is False
    assert result["reason"] == "runtime_entitlement_temporal_order_invalid"


def test_equal_predecessor_and_current_transition_times_are_allowed_by_sequence():
    transition = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)
    prior_view = runtime_view(transition_effective_at_utc=transition)
    current_view = successor(prior_view, transition_effective_at_utc=transition)
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(
        guard,
        current,
        prior=prior,
        evaluated_at_utc=transition,
    )
    assert result["allowed"] is True
    assert result["reason"] == "allowed_existing_derived_access"


def test_same_day_evaluation_observes_exact_transition_instant():
    transition = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)
    view = runtime_view(transition_effective_at_utc=transition)
    guard, runtime = guard_and_decision(view)

    before = evaluate(
        guard,
        runtime,
        evaluated_at_utc=transition - timedelta(microseconds=1),
    )
    at = evaluate(guard, runtime, evaluated_at_utc=transition)
    after = evaluate(
        guard,
        runtime,
        evaluated_at_utc=transition + timedelta(microseconds=1),
    )

    assert before["reason"] == "runtime_entitlement_temporal_order_invalid"
    assert at["reason"] == "allowed_initial_payment"
    assert after["reason"] == "allowed_initial_payment"
    assert at["evaluated_at_utc"] == transition


def test_payment_recovery_uses_exact_transition_and_half_open_day_deadline():
    prior_view = runtime_view()
    recovery_start = datetime(2026, 10, 1, tzinfo=timezone.utc)
    recovery_end = datetime(2026, 10, 8, tzinfo=timezone.utc)
    current_view = successor(
        prior_view,
        state="payment_recovery",
        derivation_kind="verified_renewal_failure",
        valid_until_exclusive=recovery_end.date(),
        transition_effective_at_utc=recovery_start,
        recovery_deadline_exclusive_at_utc=recovery_end,
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)

    before_start = evaluate(
        guard,
        current,
        prior=prior,
        evaluated_at_utc=recovery_start - timedelta(microseconds=1),
    )
    at_start = evaluate(
        guard, current, prior=prior, evaluated_at_utc=recovery_start
    )
    before_end = evaluate(
        guard,
        current,
        prior=prior,
        evaluated_at_utc=recovery_end - timedelta(microseconds=1),
    )
    at_end = evaluate(guard, current, prior=prior, evaluated_at_utc=recovery_end)
    after_end = evaluate(
        guard,
        current,
        prior=prior,
        evaluated_at_utc=recovery_end + timedelta(microseconds=1),
    )

    assert before_start["reason"] == "runtime_entitlement_temporal_order_invalid"
    assert at_start["reason"] == "allowed_payment_recovery"
    assert before_end["reason"] == "allowed_payment_recovery"
    assert at_end["reason"] == "runtime_entitlement_stale"
    assert after_end["reason"] == "runtime_entitlement_stale"


@pytest.mark.parametrize(
    "derivation_kind",
    (
        "withdrawal_open",
        "withdrawal_partial",
        "withdrawal_ambiguous",
        "withdrawal_contradictory",
        "withdrawal_unresolved",
    ),
)
def test_unresolved_withdrawal_evidence_preserves_only_existing_bounded_access(
    derivation_kind,
):
    prior_view = runtime_view()
    current_view = successor(
        prior_view,
        derivation_kind=derivation_kind,
        withdrawal_attribution="current_subscription_period",
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(guard, current, prior=prior)
    assert result["allowed"] is True
    assert result["reason"] == "allowed_preserved_withdrawal_uncertainty"


@pytest.mark.parametrize("attribution", ("other_period", "unknown"))
def test_full_withdrawal_not_attributed_to_current_period_cannot_suspend(attribution):
    prior_view = runtime_view()
    current_view = successor(
        prior_view,
        derivation_kind="verified_full_withdrawal",
        withdrawal_attribution=attribution,
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(guard, current, prior=prior)
    assert result["allowed"] is True
    assert result["reason"] == "allowed_preserved_withdrawal_uncertainty"


def test_full_withdrawal_with_not_applicable_attribution_is_contradictory():
    prior_view = runtime_view()
    current_view = successor(
        prior_view,
        derivation_kind="verified_full_withdrawal",
        withdrawal_attribution="not_applicable",
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(guard, current, prior=prior)
    assert result["allowed"] is False
    assert result["reason"] == "withdrawal_consequence_invalid"


def test_admitted_full_current_period_withdrawal_suspends_at_next_evaluation():
    prior_view = runtime_view()
    current_view = successor(
        prior_view,
        derivation_kind="verified_full_withdrawal",
        withdrawal_attribution="current_subscription_period",
        state="suspended",
        ordinary_access=False,
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(guard, current, prior=prior)
    assert result["allowed"] is False
    assert result["reason"] == "verified_full_current_period_withdrawal"


def test_full_current_period_withdrawal_cannot_leave_paid_access_enabled():
    prior_view = runtime_view()
    contradictory = successor(
        prior_view,
        derivation_kind="verified_full_withdrawal",
        withdrawal_attribution="current_subscription_period",
    )
    guard, prior, current = guard_and_boundary(prior_view, contradictory)
    result = evaluate(guard, current, prior=prior)
    assert result["allowed"] is False
    assert result["reason"] == "withdrawal_consequence_invalid"


@pytest.mark.parametrize(
    "current_view",
    (
        runtime_view(
            derivation_kind="withdrawal_partial",
            withdrawal_attribution="current_subscription_period",
        ),
        runtime_view(derivation_kind="existing_derived_access"),
    ),
)
def test_preservation_never_creates_access_without_prior_derived_access(current_view):
    guard, _, current = guard_and_boundary(None, current_view)
    result = evaluate(guard, current)
    assert result["allowed"] is False
    assert result["reason"] == "preservation_boundary_invalid"


@pytest.mark.parametrize(
    "changes",
    (
        {"valid_from_inclusive": date(2026, 8, 31)},
        {"valid_until_exclusive": date(2026, 10, 2)},
        {"state": "payment_recovery"},
    ),
)
def test_preservation_never_extends_prolongs_or_strengthens_prior_access(changes):
    prior_view = runtime_view()
    current_view = successor(
        prior_view,
        derivation_kind="withdrawal_partial",
        withdrawal_attribution="current_subscription_period",
        **changes,
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(guard, current, prior=prior)
    assert result["allowed"] is False
    assert result["reason"] == "preservation_boundary_invalid"


def test_expired_prior_access_cannot_be_preserved():
    prior_view = runtime_view(valid_until_exclusive=date(2026, 9, 10))
    current_view = successor(
        prior_view,
        derivation_kind="withdrawal_ambiguous",
        withdrawal_attribution="unknown",
        transition_effective_at_utc=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(
        guard,
        current,
        prior=prior,
        evaluated_at_utc=datetime(2026, 9, 15, 12, tzinfo=timezone.utc),
    )
    assert result["allowed"] is False
    assert result["reason"] == "runtime_entitlement_stale"


def test_cross_owner_prior_access_cannot_be_preserved_by_owner_bound_successor():
    prior_view = runtime_view(owner_id="users:18")
    current_view = successor(
        prior_view,
        owner_id="users:17",
        derivation_kind="withdrawal_partial",
        withdrawal_attribution="current_subscription_period",
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(guard, current, prior=prior)
    assert result["allowed"] is False
    assert result["reason"] in {
        "cross_owner_entitlement",
        "runtime_entitlement_invalid",
    }


@pytest.mark.parametrize(
    "order_changes",
    (
        {"decision_sequence": 1},
        {"decision_sequence": 3},
        {"predecessor_identity": None},
        {"predecessor_identity": "runtime-entitlement:sha256-" + "0" * 64},
    ),
)
def test_replayed_duplicated_or_out_of_order_boundary_cannot_preserve(order_changes):
    prior_view = runtime_view()
    current_view = successor(
        prior_view,
        derivation_kind="withdrawal_unresolved",
        withdrawal_attribution="unknown",
        **order_changes,
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(guard, current, prior=prior)
    assert result["allowed"] is False
    assert result["reason"] in {
        "runtime_entitlement_order_invalid",
        "runtime_entitlement_invalid",
    }


@pytest.mark.parametrize(
    ("derivation_kind", "reason"),
    (
        ("verified_reinstatement", "allowed_verified_reinstatement"),
        ("verified_reversal_success", "allowed_verified_reversal_success"),
        ("verified_replacement_payment", "allowed_verified_replacement_payment"),
    ),
)
def test_only_separately_admitted_entitlement_establishing_fact_restores(
    derivation_kind, reason
):
    prior_view = full_current_period_suspension()
    current_view = successor(
        prior_view,
        state="paid",
        ordinary_access=True,
        derivation_kind=derivation_kind,
        valid_from_inclusive=date(2026, 9, 15),
        valid_until_exclusive=date(2026, 10, 15),
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(guard, current, prior=prior)
    assert result["allowed"] is True
    assert result["reason"] == reason


@pytest.mark.parametrize(
    "derivation_kind",
    ("provider_status_active", "verified_renewal_payment", "existing_derived_access"),
)
def test_provider_status_or_non_restoration_fact_cannot_restore_suspended_access(
    derivation_kind,
):
    prior_view = full_current_period_suspension()
    current_view = successor(
        prior_view,
        state="paid",
        ordinary_access=True,
        derivation_kind=derivation_kind,
    )
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    result = evaluate(guard, current, prior=prior)
    assert result["allowed"] is False
    assert result["reason"] in {
        "unknown_derivation_kind",
        "restoration_boundary_invalid",
        "preservation_boundary_invalid",
    }


@pytest.mark.parametrize(
    "originless_suspension",
    (
        runtime_view(state="suspended", ordinary_access=False),
        runtime_view(
            decision_sequence=2,
            predecessor_identity="runtime-entitlement:sha256-" + "0" * 64,
            state="suspended",
            ordinary_access=False,
            derivation_kind="verified_full_withdrawal",
            withdrawal_attribution="current_subscription_period",
        ),
    ),
)
def test_restoration_rejects_sequence_one_or_malformed_suspension_origin(
    originless_suspension,
):
    restored = successor(
        originless_suspension,
        state="paid",
        ordinary_access=True,
        derivation_kind="verified_replacement_payment",
    )
    guard, prior, current = guard_and_boundary(originless_suspension, restored)
    result = evaluate(guard, current, prior=prior)
    assert result["allowed"] is False
    assert result["reason"] == "restoration_boundary_invalid"


def test_restoration_rejects_suspension_whose_embedded_predecessor_was_not_entitled():
    suspension = full_current_period_suspension(
        predecessor_entitled_access=False,
        predecessor_owner_id=None,
    )
    restored = successor(
        suspension,
        state="paid",
        ordinary_access=True,
        derivation_kind="verified_reinstatement",
    )
    guard, prior, current = guard_and_boundary(suspension, restored)
    result = evaluate(guard, current, prior=prior)
    assert result["allowed"] is False
    assert result["reason"] == "restoration_boundary_invalid"


def test_repeat_evaluation_of_same_consistent_pair_is_normal_and_deterministic():
    prior_view = runtime_view()
    current_view = successor(prior_view)
    guard, prior, current = guard_and_boundary(prior_view, current_view)
    first = evaluate(guard, current, prior=prior)
    second = evaluate(guard, current, prior=prior)
    assert first == second
    assert first["allowed"] is True
    assert first["reason"] == "allowed_existing_derived_access"


@pytest.mark.parametrize(
    "bad_view",
    (
        (),
        (("protocol_version", subject.RUNTIME_DECISION_PROTOCOL_VERSION),),
        tuple((key, "wrong") for key in RUNTIME_KEYS),
        replace_pair(runtime_view(), "decision_identity", "runtime-entitlement:sha256-" + "0" * 64),
        replace_pair(runtime_view(), "valid_from_inclusive", date(2026, 10, 1)),
        replace_pair(runtime_view(), "owner_id", "users:token"),
    ),
)
def test_malformed_runtime_projection_fails_closed(bad_view):
    guard, runtime = guard_and_decision(bad_view)
    result = evaluate(guard, runtime)
    assert result["allowed"] is False
    assert result["reason"] == "runtime_entitlement_invalid"


def test_malicious_validator_alone_cannot_override_projected_denial():
    denied = runtime_view(state="suspended", ordinary_access=False)
    lied = runtime_view(state="paid", ordinary_access=True)
    guard, runtime = guard_and_decision(
        denied,
        validator_transform=lambda _view: lied,
    )
    result = evaluate(guard, runtime)
    assert result["allowed"] is False
    assert result["reason"] == "runtime_entitlement_projection_disagrees"


def test_malicious_projector_alone_cannot_override_validated_denial():
    denied = runtime_view(state="suspended", ordinary_access=False)
    lied = runtime_view(state="paid", ordinary_access=True)
    guard, runtime = guard_and_decision(
        denied,
        projector_transform=lambda _view: lied,
    )
    result = evaluate(guard, runtime)
    assert result["allowed"] is False
    assert result["reason"] == "runtime_entitlement_projection_disagrees"


def test_extra_reordered_or_duplicate_runtime_fields_fail_closed():
    exact = runtime_view()
    variants = (
        exact + (("extra", "value"),),
        tuple(reversed(exact)),
        exact[:-1] + (exact[-2],),
    )
    for view in variants:
        guard, runtime = guard_and_decision(view)
        result = evaluate(guard, runtime)
        assert result["allowed"] is False
        assert result["reason"] == "runtime_entitlement_invalid"


def test_bound_dependency_closure_rebinding_fails_closed():
    live = set()
    state = {"enabled": True}

    def issue(view):
        value = LiveRuntimeDecision(view)
        live.add(id(value))
        return value

    def validate(value):
        if state["enabled"] and id(value) in live:
            return value.view
        raise ValueError

    def project(value):
        if state["enabled"] and id(value) in live:
            return value.view
        raise ValueError

    guard = subject.bind_paid_access_guard(
        validate_runtime_entitlement=validate,
        project_runtime_entitlement=project,
    )
    runtime = issue(runtime_view())
    assert evaluate(guard, runtime)["allowed"] is True
    state = {"enabled": True}
    result = evaluate(guard, runtime)
    assert result["allowed"] is False
    assert result["reason"] == "bound_runtime_authority_changed"


def test_handle_is_exact_binder_issued_noncopyable_and_nonserialisable():
    guard, runtime = guard_and_decision()
    assert evaluate(guard, runtime)["allowed"] is True
    with pytest.raises(TypeError, match="binder-issued"):
        subject.PaidAccessGuardHandle()
    forged = object.__new__(subject.PaidAccessGuardHandle)
    with pytest.raises(subject.PaidAccessGuardError, match="not issued"):
        evaluate(forged, runtime)
    with pytest.raises(TypeError, match="not copyable"):
        copy.copy(guard)
    with pytest.raises(TypeError, match="not copyable"):
        copy.deepcopy(guard)
    with pytest.raises(TypeError, match="not serialisable"):
        pickle.dumps(guard)


def test_validator_projector_must_be_distinct_exact_functions():
    def same(value):
        return value

    with pytest.raises(ValueError, match="must be distinct"):
        subject.bind_paid_access_guard(
            validate_runtime_entitlement=same,
            project_runtime_entitlement=same,
        )
    for invalid in (len, object()):
        with pytest.raises(TypeError, match="exact functions"):
            subject.bind_paid_access_guard(
                validate_runtime_entitlement=invalid,
                project_runtime_entitlement=same,
            )


def test_decision_validator_rejects_forged_authority_and_semantics():
    guard, runtime = guard_and_decision()
    decision = subject.evaluate_paid_access(
        guard,
        endpoint="v2.index",
        authenticated_owner_id="users:17",
        prior_runtime_entitlement=None,
        current_runtime_entitlement=runtime,
        evaluated_at_utc=datetime(2026, 9, 15, 12, tzinfo=timezone.utc),
    )
    projected = subject.validate_paid_access_decision(decision)
    assert dict(projected)["allowed"] is True
    forged = object.__new__(subject.PaidAccessDecisionHandle)
    with pytest.raises(subject.PaidAccessGuardError, match="not issued"):
        subject.validate_paid_access_decision(forged)
    for key, value in (
        ("allowed", False),
        ("route_wiring_active", True),
        ("provider_contacted", True),
        ("persisted", True),
        ("runtime_entitlement_identity", None),
        ("endpoint", "api.health"),
    ):
        with pytest.raises(subject.PaidAccessGuardError):
            subject.validate_paid_access_decision(replace_pair(projected, key, value))
    with pytest.raises(TypeError, match="not copyable"):
        copy.copy(decision)
    with pytest.raises(TypeError, match="not copyable"):
        copy.deepcopy(decision)
    with pytest.raises(TypeError, match="not serialisable"):
        pickle.dumps(decision)


def test_public_api_has_no_io_route_provider_or_entitlement_issuer_surface():
    tree = ast.parse((ROOT / "reserved/billing/paid_access_guard.py").read_text())
    imports = {
        node.names[0].name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
    }
    imports |= {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert imports <= {"__future__", "datetime", "hashlib", "json", "re", "types", "weakref"}
    assert set(subject.__all__) == {
        "CONTRACT_VERSION",
        "EXACT_INSTANT_CONTRACT_VERSION",
        "EXACT_INSTANT_RUNTIME_ADMISSION_STATUS",
        "EXACT_INSTANT_RUNTIME_DECISION_PROTOCOL_VERSION",
        "ExactInstantPaidAccessDecisionHandle",
        "ExactInstantPaidAccessGuardHandle",
        "FD_W10_004",
        "PAID_ENDPOINTS",
        "RECOVERY_DAYS",
        "RUNTIME_ADMISSION_STATUS",
        "RUNTIME_DECISION_PROTOCOL_VERSION",
        "PaidAccessGuardError",
        "PaidAccessGuardHandle",
        "PaidAccessDecisionHandle",
        "bind_paid_access_guard",
        "bind_exact_instant_paid_access_guard",
        "evaluate_exact_instant_paid_access",
        "evaluate_paid_access",
        "validate_exact_instant_paid_access_decision",
        "validate_paid_access_decision",
        "WITHDRAWAL_CONTRACT_VERSION",
        "WITHDRAWAL_RUNTIME_DECISION_PROTOCOL_VERSION",
        "WITHDRAWAL_RUNTIME_ADMISSION_STATUS",
        "FullWithdrawalPaidAccessDecisionHandle",
        "FullWithdrawalPaidAccessGuardHandle",
        "bind_full_withdrawal_paid_access_guard",
        "evaluate_full_withdrawal_paid_access",
        "validate_full_withdrawal_paid_access_decision",
        "RESTORATION_CONTRACT_VERSION",
        "RESTORATION_RUNTIME_DECISION_PROTOCOL_VERSION",
        "RESTORATION_RUNTIME_ADMISSION_STATUS",
        "LaterPeriodRestorationPaidAccessGuardHandle",
        "LaterPeriodRestorationPaidAccessDecisionHandle",
        "bind_later_period_restoration_paid_access_guard",
        "evaluate_later_period_restoration_paid_access",
        "validate_later_period_restoration_paid_access_decision",
    }


def test_evidence_states_non_activation_and_provisional_protocol_limits():
    text = (ROOT / "docs/W10_S5D_PAID_ACCESS_GUARD.md").read_text()
    for phrase in (
        "provider-neutral",
        "provisional runtime-decision protocol",
        "does not wire any route",
        "does not complete W10-S3 or W10-S5",
        "Detached S3A candidates cannot grant access",
        "verified full withdrawal",
        "never create, restore, extend or prolong",
        "verified replacement payment",
        "exactly seven calendar days",
        "pair's exact adjacency",
        "globally latest durable state",
        "Repeating evaluation of the same",
        "28 paid endpoints",
    ):
        assert phrase in text
