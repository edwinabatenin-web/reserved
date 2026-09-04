"""Focused W10-S3A provider-neutral entitlement transition tests."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from reserved.billing.entitlement_core import (
    CONTRACT_VERSION,
    RECOVERY_DAYS,
    BillingObservationKind,
    EntitlementState,
    ReconciledBillingObservation,
    apply_reconciled_observation,
    empty_entitlement,
    materialise_time_boundary,
    project_entitlement_transition,
    project_ordinary_access,
)


ROOT = Path(__file__).resolve().parents[1]


def _empty(owner="owner-1", account="account-1", subscription="subscription-1"):
    return empty_entitlement(
        owner_id=owner,
        billing_account_id=account,
        subscription_id=subscription,
    )


def _event(
    kind,
    *,
    event_id="evt-1",
    effective=date(2026, 9, 1),
    paid_through=None,
    owner="owner-1",
    account="account-1",
    subscription="subscription-1",
):
    return ReconciledBillingObservation(
        CONTRACT_VERSION,
        event_id,
        owner,
        account,
        subscription,
        kind,
        effective,
        paid_through,
        f"billing-evidence:{event_id}",
    )


def _paid(*, paid_through=date(2026, 9, 30)):
    return apply_reconciled_observation(
        _empty(),
        _event(
            BillingObservationKind.INITIAL_PAYMENT_CONFIRMED,
            paid_through=paid_through,
        ),
    )


def test_empty_state_never_grants_ordinary_access():
    state = _empty()
    assert state.state is EntitlementState.NO_ENTITLEMENT
    assert project_ordinary_access(state, as_of=date(2026, 9, 1)).ordinary_access is False


def test_verified_initial_payment_projection_starts_paid_period_only():
    paid = _paid()
    assert paid.state is EntitlementState.PAID
    assert paid.renews_automatically is True
    assert paid.paid_through == date(2026, 9, 30)
    assert paid.recovery_started_on is None
    assert paid.recovery_deadline_exclusive is None
    before = project_ordinary_access(paid, as_of=date(2026, 8, 31))
    assert before.ordinary_access is False
    assert before.reason == "outside_verified_paid_period"
    access = project_ordinary_access(paid, as_of=date(2026, 9, 30))
    assert access.ordinary_access is True
    assert access.reason == "verified_paid_period"
    assert access.valid_until_exclusive == date(2026, 10, 1)


def test_initial_payment_requires_paid_period_and_cannot_replace_state():
    with pytest.raises(ValueError, match="paid period"):
        _event(BillingObservationKind.INITIAL_PAYMENT_CONFIRMED)
    paid = _paid()
    with pytest.raises(ValueError, match="initial payment"):
        apply_reconciled_observation(
            paid,
            _event(
                BillingObservationKind.INITIAL_PAYMENT_CONFIRMED,
                event_id="evt-2",
                effective=date(2026, 10, 1),
                paid_through=date(2026, 10, 31),
            ),
        )


def test_first_failed_renewal_enters_explicit_seven_day_recovery():
    paid = _paid()
    failed_on = date(2026, 10, 1)
    recovery = apply_reconciled_observation(
        paid,
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-fail-1",
            effective=failed_on,
        ),
    )
    assert recovery.state is EntitlementState.PAYMENT_RECOVERY
    assert recovery.state is not EntitlementState.PAID
    assert recovery.recovery_started_on == failed_on
    assert recovery.recovery_deadline_exclusive == failed_on + timedelta(days=7)
    assert RECOVERY_DAYS == 7
    assert project_ordinary_access(
        recovery, as_of=date(2026, 10, 7)
    ).ordinary_access is True
    expired = project_ordinary_access(recovery, as_of=date(2026, 10, 8))
    assert expired.ordinary_access is False
    assert expired.reason == "outside_paid_and_recovery_periods"


def test_delayed_failure_does_not_retroactively_fill_access_gap():
    paid = _paid()
    recovery = apply_reconciled_observation(
        paid,
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-delayed-fail",
            effective=date(2026, 10, 5),
        ),
    )
    for gap_day in (date(2026, 10, 1), date(2026, 10, 4)):
        gap = project_ordinary_access(recovery, as_of=gap_day)
        assert gap.ordinary_access is False
        assert gap.reason == "outside_paid_and_recovery_periods"
    started = project_ordinary_access(recovery, as_of=date(2026, 10, 5))
    assert started.ordinary_access is True
    assert started.reason == "bounded_payment_recovery"
    assert started.valid_from_inclusive == date(2026, 10, 5)


def test_repeated_failure_cannot_extend_recovery_deadline():
    paid = _paid()
    first = apply_reconciled_observation(
        paid,
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-fail-1",
            effective=date(2026, 10, 1),
        ),
    )
    repeated = apply_reconciled_observation(
        first,
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-fail-2",
            effective=date(2026, 10, 4),
        ),
    )
    assert repeated.recovery_started_on == first.recovery_started_on
    assert repeated.recovery_deadline_exclusive == first.recovery_deadline_exclusive
    assert repeated.processed_event_ids[-1] == "evt-fail-2"


def test_failure_at_or_after_recovery_deadline_suspends_without_extension():
    recovery = apply_reconciled_observation(
        _paid(),
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-fail-1",
            effective=date(2026, 10, 1),
        ),
    )
    deadline = recovery.recovery_deadline_exclusive
    suspended = apply_reconciled_observation(
        recovery,
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-fail-late",
            effective=deadline,
        ),
    )
    assert suspended.state is EntitlementState.SUSPENDED
    assert suspended.recovery_deadline_exclusive == deadline
    assert project_ordinary_access(suspended, as_of=deadline).ordinary_access is False


def test_duplicate_event_is_idempotent_and_does_not_duplicate_evidence():
    paid = _paid()
    failed = _event(
        BillingObservationKind.RENEWAL_PAYMENT_FAILED,
        event_id="evt-fail-1",
        effective=date(2026, 10, 1),
    )
    first = apply_reconciled_observation(paid, failed)
    second = apply_reconciled_observation(first, failed)
    assert second is first
    assert second.processed_event_ids.count("evt-fail-1") == 1
    assert second.evidence_references.count("billing-evidence:evt-fail-1") == 1


def test_reused_event_id_with_different_content_fails_closed():
    paid = _paid()
    conflicting = _event(
        BillingObservationKind.CANCELLATION_CONFIRMED,
        event_id="evt-1",
        effective=date(2026, 9, 15),
    )
    with pytest.raises(ValueError, match="reused with different content"):
        apply_reconciled_observation(paid, conflicting)


def test_failed_renewal_cannot_truncate_an_already_paid_period():
    paid = _paid(paid_through=date(2026, 11, 30))
    with pytest.raises(ValueError, match="truncate"):
        apply_reconciled_observation(
            paid,
            _event(
                BillingObservationKind.RENEWAL_PAYMENT_FAILED,
                event_id="evt-early-fail",
                effective=date(2026, 10, 1),
            ),
        )
    assert project_ordinary_access(
        paid, as_of=date(2026, 11, 30)
    ).ordinary_access is True


def test_successful_recovery_returns_to_paid_and_advances_period():
    recovery = apply_reconciled_observation(
        _paid(),
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-fail-1",
            effective=date(2026, 10, 1),
        ),
    )
    recovered = apply_reconciled_observation(
        recovery,
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_CONFIRMED,
            event_id="evt-renew-1",
            effective=date(2026, 10, 5),
            paid_through=date(2026, 10, 31),
        ),
    )
    assert recovered.state is EntitlementState.PAID
    assert recovered.recovery_started_on is None
    assert recovered.recovery_deadline_exclusive is None
    assert recovered.paid_through == date(2026, 10, 31)


def test_renewal_cannot_create_initial_access_or_fail_to_advance_period():
    with pytest.raises(ValueError, match="initial entitlement"):
        apply_reconciled_observation(
            _empty(),
            _event(
                BillingObservationKind.RENEWAL_PAYMENT_CONFIRMED,
                paid_through=date(2026, 9, 30),
            ),
        )
    with pytest.raises(ValueError, match="advance"):
        apply_reconciled_observation(
            _paid(),
            _event(
                BillingObservationKind.RENEWAL_PAYMENT_CONFIRMED,
                event_id="evt-renew-1",
                effective=date(2026, 9, 29),
                paid_through=date(2026, 9, 30),
            ),
        )


def test_cancellation_stops_renewal_but_keeps_paid_period_access():
    paid = _paid()
    cancelled = apply_reconciled_observation(
        paid,
        _event(
            BillingObservationKind.CANCELLATION_CONFIRMED,
            event_id="evt-cancel-1",
            effective=date(2026, 9, 15),
        ),
    )
    assert cancelled.state is EntitlementState.PAID
    assert cancelled.renews_automatically is False
    assert cancelled.paid_through == paid.paid_through
    assert project_ordinary_access(
        cancelled, as_of=date(2026, 9, 30)
    ).ordinary_access is True
    with pytest.raises(ValueError, match="after cancellation"):
        apply_reconciled_observation(
            cancelled,
            _event(
                BillingObservationKind.RENEWAL_PAYMENT_FAILED,
                event_id="evt-fail-after-cancel",
                effective=date(2026, 10, 1),
            ),
        )


def test_cancellation_during_recovery_is_not_inferred():
    recovery = apply_reconciled_observation(
        _paid(),
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-fail-1",
            effective=date(2026, 10, 1),
        ),
    )
    with pytest.raises(ValueError, match="requires reconciliation"):
        apply_reconciled_observation(
            recovery,
            _event(
                BillingObservationKind.CANCELLATION_CONFIRMED,
                event_id="evt-cancel-1",
                effective=date(2026, 10, 2),
            ),
        )


@pytest.mark.parametrize("field", ["owner", "account", "subscription"])
def test_cross_boundary_observation_is_rejected(field):
    kwargs = {field: f"other-{field}"}
    with pytest.raises(ValueError, match="ownership boundary"):
        apply_reconciled_observation(
            _paid(),
            _event(
                BillingObservationKind.RENEWAL_PAYMENT_FAILED,
                event_id="evt-fail-1",
                effective=date(2026, 10, 1),
                **kwargs,
            ),
        )


def test_older_and_same_day_distinct_events_fail_closed():
    paid = _paid()
    for effective in (date(2026, 8, 31), date(2026, 9, 1)):
        with pytest.raises(ValueError, match="out-of-order or same-day"):
            apply_reconciled_observation(
                paid,
                _event(
                    BillingObservationKind.CANCELLATION_CONFIRMED,
                    event_id=f"evt-{effective}",
                    effective=effective,
                ),
            )


def test_time_boundary_materialises_suspension_without_extending_access():
    paid = _paid()
    assert materialise_time_boundary(paid, as_of=date(2026, 9, 30)) is paid
    suspended_paid = materialise_time_boundary(paid, as_of=date(2026, 10, 1))
    assert suspended_paid.state is EntitlementState.SUSPENDED
    assert project_ordinary_access(
        suspended_paid, as_of=date(2026, 10, 1)
    ).ordinary_access is False

    recovery = apply_reconciled_observation(
        paid,
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-fail-1",
            effective=date(2026, 10, 1),
        ),
    )
    assert materialise_time_boundary(recovery, as_of=date(2026, 10, 7)) is recovery
    suspended_recovery = materialise_time_boundary(
        recovery, as_of=date(2026, 10, 8)
    )
    assert suspended_recovery.state is EntitlementState.SUSPENDED
    assert suspended_recovery.recovery_deadline_exclusive == date(2026, 10, 8)


def test_late_verified_recovery_can_restore_suspended_recovery_only():
    recovery = apply_reconciled_observation(
        _paid(),
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-fail-1",
            effective=date(2026, 10, 1),
        ),
    )
    suspended = materialise_time_boundary(recovery, as_of=date(2026, 10, 8))
    restored = apply_reconciled_observation(
        suspended,
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_CONFIRMED,
            event_id="evt-late-recovery",
            effective=date(2026, 10, 9),
            paid_through=date(2026, 11, 8),
        ),
    )
    assert restored.state is EntitlementState.PAID
    assert restored.recovery_started_on is None
    assert restored.recovery_deadline_exclusive is None


def test_direct_observation_construction_is_explicitly_not_provider_proof():
    source = (ROOT / "reserved/billing/entitlement_core.py").read_text()
    assert "Construction proves shape only" in source
    assert "never evidence that a provider event was authentic" in source
    assert "contact Stripe" in source


def test_module_is_network_persistence_route_and_provider_sdk_inert():
    source = (ROOT / "reserved/billing/entitlement_core.py").read_text()
    for forbidden in (
        "import stripe",
        "import requests",
        "import socket",
        "import sqlite3",
        "from flask",
        "reserved.database",
        "reserved.web",
        "sk_live",
        "sk_test",
        "checkout.session",
        "webhook_secret",
    ):
        assert forbidden not in source.lower()


def test_unresolved_post_settlement_and_override_policy_is_absent():
    source = (ROOT / "reserved/billing/entitlement_core.py").read_text().lower()
    for forbidden in ("refund", "chargeback", "dispute", "manual_override", "proration"):
        assert forbidden not in source


def test_projection_state_is_opaque_producer_issued_and_immutable():
    state = _empty()
    with pytest.raises(TypeError, match="producer-issued"):
        type(state)()
    with pytest.raises(AttributeError):
        object.__setattr__(state, "state", EntitlementState.PAID)
    projected = dict(project_entitlement_transition(state))
    assert projected["state"] is EntitlementState.NO_ENTITLEMENT
