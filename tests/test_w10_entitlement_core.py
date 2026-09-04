"""Focused W10-S3A provider-neutral entitlement transition tests."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import copy
import pickle
import subprocess
import sys
import types

import pytest

import reserved.billing.entitlement_core as entitlement_core
from reserved.billing.entitlement_core import (
    CANDIDATE_CLASSIFICATION,
    CANDIDATE_SCHEMA_VERSION,
    CONTRACT_VERSION,
    RECOVERY_DAYS,
    BillingObservationCandidate,
    BillingObservationKind,
    EntitlementState,
    EntitlementTransitionCandidate,
    ReconciledBillingObservation,
    apply_reconciled_observation,
    copy_entitlement_transition,
    empty_entitlement,
    materialise_time_boundary,
    project_entitlement_transition,
    project_ordinary_access,
    validate_entitlement_transition,
    validate_ordinary_access_candidate,
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


def _unchecked_event(
    kind,
    *,
    contract_version=CONTRACT_VERSION,
    event_id="evt-unchecked",
    effective=date(2026, 9, 1),
    paid_through=None,
    owner="owner-1",
    account="account-1",
    subscription="subscription-1",
):
    value = object.__new__(BillingObservationCandidate)
    for name, field_value in (
        ("contract_version", contract_version),
        ("event_id", event_id),
        ("owner_id", owner),
        ("billing_account_id", account),
        ("subscription_id", subscription),
        ("kind", kind),
        ("effective_date", effective),
        ("paid_through", paid_through),
        ("evidence_reference", f"billing-evidence:{event_id}"),
    ):
        object.__setattr__(value, name, field_value)
    return value


def _paid(*, paid_through=date(2026, 9, 30)):
    return apply_reconciled_observation(
        _empty(),
        _event(
            BillingObservationKind.INITIAL_PAYMENT_CONFIRMED,
            paid_through=paid_through,
        ),
    )


def _state(candidate):
    return dict(project_entitlement_transition(candidate))


def _access(candidate, *, as_of):
    return dict(project_ordinary_access(candidate, as_of=as_of))


def test_empty_state_never_grants_ordinary_access():
    state = _empty()
    assert _state(state)["state"] == EntitlementState.NO_ENTITLEMENT.value
    assert _access(state, as_of=date(2026, 9, 1))["ordinary_access"] is False


def test_verified_initial_payment_projection_starts_paid_period_only():
    paid = _paid()
    values = _state(paid)
    assert values["state"] == EntitlementState.PAID.value
    assert values["renews_automatically"] is True
    assert values["paid_through"] == date(2026, 9, 30)
    assert values["recovery_started_on"] is None
    assert values["recovery_deadline_exclusive"] is None
    before = _access(paid, as_of=date(2026, 8, 31))
    assert before["ordinary_access"] is False
    assert before["reason"] == "no_ordinary_paid_access"
    access = _access(paid, as_of=date(2026, 9, 30))
    assert access["ordinary_access"] is True
    assert access["reason"] == "structural_paid_period_candidate"
    assert access["valid_until_exclusive"] == date(2026, 10, 1)


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


class _PlainVersionSubclass(str):
    pass


class _EqualityOverridingVersion(str):
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False


@pytest.mark.parametrize(
    "substituted_version",
    (
        _PlainVersionSubclass(CONTRACT_VERSION),
        _EqualityOverridingVersion("attacker-contract"),
    ),
)
def test_contract_version_subclasses_cannot_construct_or_reach_paid_transition(
    substituted_version,
):
    assert substituted_version == CONTRACT_VERSION
    with pytest.raises(ValueError, match="unsupported billing observation contract"):
        BillingObservationCandidate(
            substituted_version,
            "evt-substituted-version",
            "owner-1",
            "account-1",
            "subscription-1",
            BillingObservationKind.INITIAL_PAYMENT_CONFIRMED,
            date(2026, 9, 1),
            date(2026, 9, 30),
            "billing-evidence:evt-substituted-version",
        )

    empty = _empty()
    forged = _unchecked_event(
        BillingObservationKind.INITIAL_PAYMENT_CONFIRMED,
        contract_version=substituted_version,
        event_id="evt-substituted-version",
        paid_through=date(2026, 9, 30),
    )
    with pytest.raises(ValueError, match="unsupported billing observation contract"):
        apply_reconciled_observation(empty, forged)
    assert _state(empty)["state"] == EntitlementState.NO_ENTITLEMENT.value

    with pytest.raises(ValueError):
        validate_entitlement_transition(
            _replace(empty, contract_version=substituted_version)
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
    values = _state(recovery)
    assert values["state"] == EntitlementState.PAYMENT_RECOVERY.value
    assert values["state"] != EntitlementState.PAID.value
    assert values["recovery_started_on"] == failed_on
    assert values["recovery_deadline_exclusive"] == failed_on + timedelta(days=7)
    assert RECOVERY_DAYS == 7
    assert _access(recovery, as_of=date(2026, 10, 7))["ordinary_access"] is True
    expired = _access(recovery, as_of=date(2026, 10, 8))
    assert expired["ordinary_access"] is False
    assert expired["state"] == EntitlementState.SUSPENDED.value
    assert expired["reason"] == "no_ordinary_paid_access"


@pytest.mark.parametrize(
    "kind",
    (
        BillingObservationKind.INITIAL_PAYMENT_CONFIRMED,
        BillingObservationKind.RENEWAL_PAYMENT_CONFIRMED,
    ),
)
def test_payment_paid_through_date_max_fails_closed_without_overflow(kind):
    kwargs = {
        "event_id": "evt-date-max-payment",
        "effective": date.max - timedelta(days=1),
        "paid_through": date.max,
    }
    with pytest.raises(ValueError, match="paid-through date exceeds supported boundary"):
        _event(kind, **kwargs)

    forged = _unchecked_event(kind, **kwargs)
    current = _empty() if kind is BillingObservationKind.INITIAL_PAYMENT_CONFIRMED else _paid()
    with pytest.raises(ValueError, match="paid-through date exceeds supported boundary"):
        apply_reconciled_observation(current, forged)


def test_failure_near_date_max_fails_closed_without_overflow():
    too_late = date.max - timedelta(days=RECOVERY_DAYS - 1)
    with pytest.raises(ValueError, match="supported recovery boundary"):
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-late-boundary-failure",
            effective=too_late,
        )

    forged = _unchecked_event(
        BillingObservationKind.RENEWAL_PAYMENT_FAILED,
        event_id="evt-late-boundary-failure",
        effective=too_late,
    )
    with pytest.raises(ValueError, match="supported recovery boundary"):
        apply_reconciled_observation(_paid(), forged)


def test_supported_date_boundaries_project_without_overflow():
    initial_on = date.max - timedelta(days=30)
    paid_through = date.max - timedelta(days=8)
    paid = apply_reconciled_observation(
        _empty(),
        _event(
            BillingObservationKind.INITIAL_PAYMENT_CONFIRMED,
            event_id="evt-supported-max-payment",
            effective=initial_on,
            paid_through=paid_through,
        ),
    )
    failed_on = date.max - timedelta(days=RECOVERY_DAYS)
    recovery = apply_reconciled_observation(
        paid,
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-supported-max-failure",
            effective=failed_on,
        ),
    )
    values = _state(recovery)
    assert values["recovery_deadline_exclusive"] == date.max
    access = _access(recovery, as_of=date.max - timedelta(days=1))
    assert access["ordinary_access"] is True
    assert access["valid_until_exclusive"] == date.max
    assert _access(recovery, as_of=date.max)["ordinary_access"] is False

    latest_paid = apply_reconciled_observation(
        _empty(owner="owner-max", account="account-max", subscription="sub-max"),
        _event(
            BillingObservationKind.INITIAL_PAYMENT_CONFIRMED,
            event_id="evt-latest-safe-payment",
            effective=date.max - timedelta(days=2),
            paid_through=date.max - timedelta(days=1),
            owner="owner-max",
            account="account-max",
            subscription="sub-max",
        ),
    )
    latest_access = _access(latest_paid, as_of=date.max - timedelta(days=1))
    assert latest_access["valid_until_exclusive"] == date.max


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
        gap = _access(recovery, as_of=gap_day)
        assert gap["ordinary_access"] is False
        assert gap["state"] == EntitlementState.SUSPENDED.value
        assert gap["reason"] == "no_ordinary_paid_access"
    started = _access(recovery, as_of=date(2026, 10, 5))
    assert started["ordinary_access"] is True
    assert started["reason"] == "structural_bounded_payment_recovery_candidate"
    assert started["valid_from_inclusive"] == date(2026, 10, 5)


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
    first_values = _state(first)
    repeated_values = _state(repeated)
    assert repeated_values["recovery_started_on"] == first_values["recovery_started_on"]
    assert (
        repeated_values["recovery_deadline_exclusive"]
        == first_values["recovery_deadline_exclusive"]
    )
    assert repeated_values["processed_observations"][-1][0] == "evt-fail-2"


def test_failure_at_or_after_recovery_deadline_suspends_without_extension():
    recovery = apply_reconciled_observation(
        _paid(),
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-fail-1",
            effective=date(2026, 10, 1),
        ),
    )
    deadline = _state(recovery)["recovery_deadline_exclusive"]
    suspended = apply_reconciled_observation(
        recovery,
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-fail-late",
            effective=deadline,
        ),
    )
    values = _state(suspended)
    assert values["state"] == EntitlementState.SUSPENDED.value
    assert values["recovery_deadline_exclusive"] == deadline
    assert _access(suspended, as_of=deadline)["ordinary_access"] is False


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
    processed = _state(second)["processed_observations"]
    assert tuple(item[0] for item in processed).count("evt-fail-1") == 1
    assert tuple(item[7] for item in processed).count("billing-evidence:evt-fail-1") == 1


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
    assert _access(paid, as_of=date(2026, 11, 30))["ordinary_access"] is True


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
    values = _state(recovered)
    assert values["state"] == EntitlementState.PAID.value
    assert values["recovery_started_on"] is None
    assert values["recovery_deadline_exclusive"] is None
    assert values["paid_through"] == date(2026, 10, 31)


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
    values = _state(cancelled)
    assert values["state"] == EntitlementState.PAID.value
    assert values["renews_automatically"] is False
    assert values["paid_through"] == _state(paid)["paid_through"]
    assert _access(cancelled, as_of=date(2026, 9, 30))["ordinary_access"] is True
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
    assert _state(suspended_paid)["state"] == EntitlementState.SUSPENDED.value
    paid_at_end = _access(suspended_paid, as_of=date(2026, 9, 30))
    paid_after_end = _access(suspended_paid, as_of=date(2026, 10, 1))
    assert paid_at_end["state"] == EntitlementState.PAID.value
    assert paid_at_end["ordinary_access"] is True
    assert paid_after_end["state"] == EntitlementState.SUSPENDED.value
    assert paid_after_end["ordinary_access"] is False

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
    values = _state(suspended_recovery)
    assert values["state"] == EntitlementState.SUSPENDED.value
    assert values["recovery_deadline_exclusive"] == date(2026, 10, 8)


@pytest.mark.parametrize("failed_on", (date(2026, 10, 1), date(2026, 10, 5)))
def test_paid_expiry_and_first_failure_are_order_independent(failed_on):
    paid = _paid()
    failure = _event(
        BillingObservationKind.RENEWAL_PAYMENT_FAILED,
        event_id="evt-order-independent-failure",
        effective=failed_on,
    )

    failure_then_boundary = materialise_time_boundary(
        apply_reconciled_observation(paid, failure),
        as_of=failed_on,
    )
    boundary_then_failure = apply_reconciled_observation(
        materialise_time_boundary(paid, as_of=failed_on),
        failure,
    )

    assert boundary_then_failure == failure_then_boundary
    values = _state(boundary_then_failure)
    assert values["state"] == EntitlementState.PAYMENT_RECOVERY.value
    assert values["recovery_started_on"] == failed_on
    assert values["recovery_deadline_exclusive"] == failed_on + timedelta(days=7)
    assert _access(boundary_then_failure, as_of=failed_on)[
        "ordinary_access"
    ] is True
    if failed_on > date(2026, 10, 1):
        assert _access(boundary_then_failure, as_of=date(2026, 10, 4))[
            "ordinary_access"
        ] is False


def test_suspended_paid_state_preserves_failure_owner_and_history_guards():
    suspended = materialise_time_boundary(_paid(), as_of=date(2026, 10, 1))
    with pytest.raises(ValueError, match="ownership boundary"):
        apply_reconciled_observation(
            suspended,
            _event(
                BillingObservationKind.RENEWAL_PAYMENT_FAILED,
                event_id="evt-cross-owner-after-boundary",
                effective=date(2026, 10, 1),
                owner="other-owner",
            ),
        )
    with pytest.raises(ValueError, match="reused with different content"):
        apply_reconciled_observation(
            suspended,
            _event(
                BillingObservationKind.RENEWAL_PAYMENT_FAILED,
                event_id="evt-1",
                effective=date(2026, 10, 1),
            ),
        )
    with pytest.raises(ValueError, match="out-of-order or same-day"):
        apply_reconciled_observation(
            suspended,
            _event(
                BillingObservationKind.RENEWAL_PAYMENT_FAILED,
                event_id="evt-old-after-boundary",
                effective=date(2026, 9, 1),
            ),
        )


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
    values = _state(restored)
    assert values["state"] == EntitlementState.PAID.value
    assert values["recovery_started_on"] is None
    assert values["recovery_deadline_exclusive"] is None
    assert values["entitlement_started_on"] == date(2026, 10, 9)
    prior_paid = _access(restored, as_of=date(2026, 9, 30))
    prior_recovery = _access(restored, as_of=date(2026, 10, 7))
    before = _access(restored, as_of=date(2026, 10, 8))
    at_restoration = _access(restored, as_of=date(2026, 10, 9))
    after = _access(restored, as_of=date(2026, 10, 10))
    assert prior_paid["ordinary_access"] is True
    assert prior_paid["state"] == EntitlementState.PAID.value
    assert prior_recovery["ordinary_access"] is True
    assert prior_recovery["state"] == EntitlementState.PAYMENT_RECOVERY.value
    assert prior_recovery["reason"] == "structural_bounded_payment_recovery_candidate"
    assert before["ordinary_access"] is False
    assert before["state"] == EntitlementState.SUSPENDED.value
    assert before["reason"] == "no_ordinary_paid_access"
    assert at_restoration["ordinary_access"] is True
    assert at_restoration["state"] == EntitlementState.PAID.value
    assert at_restoration["valid_from_inclusive"] == date(2026, 10, 9)
    assert after["ordinary_access"] is True


def test_late_recovery_is_order_independent_and_never_backfills_expired_gap():
    recovery = apply_reconciled_observation(
        _paid(),
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-fail-before-late-recovery",
            effective=date(2026, 10, 1),
        ),
    )
    renewal = _event(
        BillingObservationKind.RENEWAL_PAYMENT_CONFIRMED,
        event_id="evt-late-order-independent-recovery",
        effective=date(2026, 10, 9),
        paid_through=date(2026, 11, 8),
    )
    renewal_then_boundary = materialise_time_boundary(
        apply_reconciled_observation(recovery, renewal),
        as_of=date(2026, 10, 9),
    )
    boundary_then_renewal = apply_reconciled_observation(
        materialise_time_boundary(recovery, as_of=date(2026, 10, 8)),
        renewal,
    )
    assert boundary_then_renewal == renewal_then_boundary
    at_gap = _access(boundary_then_renewal, as_of=date(2026, 10, 8))
    in_recovery = _access(boundary_then_renewal, as_of=date(2026, 10, 7))
    restored = _access(boundary_then_renewal, as_of=date(2026, 10, 9))
    assert at_gap["state"] == EntitlementState.SUSPENDED.value
    assert at_gap["ordinary_access"] is False
    assert in_recovery["state"] == EntitlementState.PAYMENT_RECOVERY.value
    assert in_recovery["ordinary_access"] is True
    assert restored["state"] == EntitlementState.PAID.value
    assert restored["ordinary_access"] is True


def test_delayed_direct_renewal_preserves_gap_in_both_materialisation_orders():
    paid = _paid()
    renewal = _event(
        BillingObservationKind.RENEWAL_PAYMENT_CONFIRMED,
        event_id="evt-delayed-direct-renewal",
        effective=date(2026, 10, 5),
        paid_through=date(2026, 10, 31),
    )
    renewal_then_boundary = materialise_time_boundary(
        apply_reconciled_observation(paid, renewal),
        as_of=date(2026, 10, 5),
    )
    boundary_first = apply_reconciled_observation(
        materialise_time_boundary(paid, as_of=date(2026, 10, 1)),
        renewal,
    )
    assert renewal_then_boundary == boundary_first
    assert _state(renewal_then_boundary)["entitlement_started_on"] == date(2026, 10, 5)
    assert _access(renewal_then_boundary, as_of=date(2026, 9, 30))[
        "ordinary_access"
    ] is True
    for gap_day in (
        date(2026, 10, 1),
        date(2026, 10, 2),
        date(2026, 10, 3),
        date(2026, 10, 4),
    ):
        gap = _access(renewal_then_boundary, as_of=gap_day)
        assert gap["state"] == EntitlementState.SUSPENDED.value
        assert gap["ordinary_access"] is False
    restored = _access(renewal_then_boundary, as_of=date(2026, 10, 5))
    assert restored["state"] == EntitlementState.PAID.value
    assert restored["ordinary_access"] is True
    assert restored["valid_from_inclusive"] == date(2026, 10, 5)


def test_continuous_renewal_has_no_invented_gap_in_either_order():
    paid = _paid()
    renewal = _event(
        BillingObservationKind.RENEWAL_PAYMENT_CONFIRMED,
        event_id="evt-continuous-renewal",
        effective=date(2026, 10, 1),
        paid_through=date(2026, 10, 31),
    )
    renewal_then_boundary = materialise_time_boundary(
        apply_reconciled_observation(paid, renewal),
        as_of=date(2026, 10, 1),
    )
    boundary_first = apply_reconciled_observation(
        materialise_time_boundary(paid, as_of=date(2026, 10, 1)),
        renewal,
    )
    assert renewal_then_boundary == boundary_first
    assert _state(renewal_then_boundary)["entitlement_started_on"] == date(2026, 9, 1)
    for access_day in (
        date(2026, 9, 30),
        date(2026, 10, 1),
        date(2026, 10, 2),
    ):
        access = _access(renewal_then_boundary, as_of=access_day)
        assert access["state"] == EntitlementState.PAID.value
        assert access["ordinary_access"] is True


def test_suspended_recovery_rejects_observation_predating_its_deadline():
    recovery = apply_reconciled_observation(
        _paid(),
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-fail-before-suspension",
            effective=date(2026, 10, 1),
        ),
    )
    suspended = materialise_time_boundary(recovery, as_of=date(2026, 10, 8))
    with pytest.raises(ValueError, match="predating a suspended recovery deadline"):
        apply_reconciled_observation(
            suspended,
            _event(
                BillingObservationKind.RENEWAL_PAYMENT_CONFIRMED,
                event_id="evt-backdated-recovery",
                effective=date(2026, 10, 5),
                paid_through=date(2026, 10, 31),
            ),
        )


def test_direct_observation_construction_is_explicitly_not_provider_proof():
    source = (ROOT / "reserved/billing/entitlement_core.py").read_text()
    assert "construction is never provider or reconciliation proof" in source.lower()
    assert "separately authenticated adapter" in source
    assert "contact a provider" in source


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


def test_projection_is_exact_detached_non_authoritative_structure():
    state = _empty()
    assert type(state) is EntitlementTransitionCandidate is tuple
    assert copy.copy(state) is state
    projected = dict(project_entitlement_transition(state))
    assert projected["state"] == EntitlementState.NO_ENTITLEMENT.value
    assert projected["candidate_classification"] == CANDIDATE_CLASSIFICATION
    assert projected["candidate_schema_version"] == CANDIDATE_SCHEMA_VERSION
    for name in (
        "provider_observation_authenticated",
        "provider_provenance_authenticated",
        "provider_status_authority",
        "persistence_authority",
        "runtime_access_authority",
    ):
        assert projected[name] is False


def test_valid_detached_reconstruction_is_semantic_only_and_non_admitted():
    reconstructed = tuple(
        (str(name), tuple(value) if name == "processed_observations" else value)
        for name, value in _paid()
    )
    validated = dict(validate_entitlement_transition(reconstructed))
    assert copy_entitlement_transition(reconstructed) == reconstructed
    assert validate_entitlement_transition(copy.deepcopy(reconstructed)) == reconstructed
    round_trip = pickle.loads(pickle.dumps(reconstructed))
    assert validate_entitlement_transition(round_trip) == reconstructed
    assert validated["state"] == EntitlementState.PAID.value
    assert validated["provider_observation_authenticated"] is False
    assert validated["runtime_access_authority"] is False

    class TupleSubclass(tuple):
        pass

    with pytest.raises(ValueError, match="exact detached tuple"):
        validate_entitlement_transition(TupleSubclass(reconstructed))


def test_old_combined_registry_forgery_surface_is_removed():
    source = (ROOT / "reserved/billing/entitlement_core.py").read_text()
    for forbidden in (
        "_registry",
        "_live",
        "weakvaluedictionary",
        "import weakref",
        "object.__new__",
        "producer-issued",
    ):
        assert forbidden not in source.lower()
    with pytest.raises(TypeError):
        object.__new__(EntitlementTransitionCandidate)

    found_mutable_state = []
    seen = set()
    pending = [
        apply_reconciled_observation,
        project_entitlement_transition,
        project_ordinary_access,
    ]
    while pending:
        function = pending.pop()
        if not isinstance(function, types.FunctionType) or id(function) in seen:
            continue
        seen.add(id(function))
        for cell in function.__closure__ or ():
            value = cell.cell_contents
            if type(value) is dict:
                found_mutable_state.append((function.__name__, value))
            if isinstance(value, types.FunctionType):
                pending.append(value)
    assert found_mutable_state == []


def test_coherent_public_cluster_substitution_does_not_enter_kernel(monkeypatch):
    genuine_empty = empty_entitlement
    genuine_apply = apply_reconciled_observation

    class FakeProjection:
        pass

    class FakeState:
        PAYMENT_RECOVERY = "payment_recovery"

    monkeypatch.setattr(
        entitlement_core, "EntitlementTransitionProjection", FakeProjection
    )
    monkeypatch.setattr(entitlement_core, "EntitlementState", FakeState)
    monkeypatch.setattr(entitlement_core, "RECOVERY_DAYS", 999)
    monkeypatch.setattr(entitlement_core, "CANDIDATE_CLASSIFICATION", "admitted")
    monkeypatch.setattr(
        entitlement_core,
        "project_entitlement_transition",
        lambda value: (("state", "payment_recovery"),),
    )
    with pytest.raises(ValueError, match="exact detached tuple"):
        genuine_apply(
            FakeProjection(),
            _event(
                BillingObservationKind.RENEWAL_PAYMENT_FAILED,
                effective=date(2026, 10, 1),
            ),
        )
    recovery = genuine_apply(
        _paid(),
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-cluster-fail",
            effective=date(2026, 10, 1),
        ),
    )
    assert _state(recovery)["recovery_deadline_exclusive"] == date(2026, 10, 8)
    assert _state(
        genuine_empty(
            owner_id="owner-1",
            billing_account_id="account-1",
            subscription_id="subscription-1",
        )
    )["runtime_access_authority"] is False


def test_clean_process_cluster_substitution_before_consumer_import_fails_closed():
    script = """
import datetime
import reserved.billing.entitlement_core as core

class FakeProjection:
    pass

class FakeState:
    PAYMENT_RECOVERY = "payment_recovery"

core.EntitlementTransitionProjection = FakeProjection
core.EntitlementState = FakeState
core.project_entitlement_transition = lambda value: (
    ("state", "payment_recovery"),
    ("runtime_access_authority", True),
)

from reserved.billing.entitlement_core import (
    BillingObservationCandidate,
    BillingObservationKind,
    CONTRACT_VERSION,
    apply_reconciled_observation,
)

observation = BillingObservationCandidate(
    CONTRACT_VERSION,
    "evt-fake",
    "attacker-owner",
    "account-1",
    "subscription-1",
    BillingObservationKind.RENEWAL_PAYMENT_FAILED,
    datetime.date(2026, 12, 24),
    None,
    "billing-evidence:evt-fake",
)
try:
    apply_reconciled_observation(FakeProjection(), observation)
except ValueError as error:
    assert "exact detached tuple" in str(error)
else:
    raise AssertionError("coherent substituted public cluster entered the kernel")
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def _replace(candidate, **changes):
    return tuple((name, changes.get(name, value)) for name, value in candidate)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("candidate_schema_version", "unsafe", "candidate schema"),
        ("owner_id", "attacker-owner", "ownership boundary"),
        ("recovery_started_on", date(2026, 12, 24), "event history"),
        ("recovery_deadline_exclusive", date(2026, 12, 31), "event history"),
        ("recovery_deadline_exclusive", date(2026, 10, 9), "event history"),
        ("provider_status_authority", True, "zero provider_status_authority"),
        ("runtime_access_authority", True, "zero runtime_access_authority"),
    ),
)
def test_reconstructed_owner_deadline_or_authority_tamper_fails(field, value, message):
    recovery = apply_reconciled_observation(
        _paid(),
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="evt-fail-1",
            effective=date(2026, 10, 1),
        ),
    )
    with pytest.raises(ValueError, match=message):
        validate_entitlement_transition(_replace(recovery, **{field: value}))


@pytest.mark.parametrize(
    "invalid",
    (
        datetime(2026, 10, 1),
        "2026-10-01",
        None,
        True,
    ),
)
def test_invalid_or_non_exact_policy_times_fail_closed(invalid):
    with pytest.raises(TypeError, match="exact date"):
        project_ordinary_access(_paid(), as_of=invalid)


@pytest.mark.parametrize(
    ("effective", "paid_through"),
    (
        (datetime(2026, 9, 1), date(2026, 9, 30)),
        (date(2026, 9, 1), datetime(2026, 9, 30)),
    ),
)
def test_observation_candidate_rejects_non_exact_dates(effective, paid_through):
    with pytest.raises(ValueError, match="date"):
        BillingObservationCandidate(
            CONTRACT_VERSION,
            "evt-invalid-time",
            "owner-1",
            "account-1",
            "subscription-1",
            BillingObservationKind.INITIAL_PAYMENT_CONFIRMED,
            effective,
            paid_through,
            "billing-evidence:evt-invalid-time",
        )


def test_captured_observation_descriptors_ignore_later_class_substitution(monkeypatch):
    observation = _event(
        BillingObservationKind.INITIAL_PAYMENT_CONFIRMED,
        paid_through=date(2026, 9, 30),
    )
    monkeypatch.setattr(
        BillingObservationCandidate,
        "owner_id",
        property(lambda value: "attacker-owner"),
    )
    monkeypatch.setattr(
        BillingObservationKind,
        "value",
        property(lambda value: "renewal_payment_failed"),
        raising=False,
    )
    monkeypatch.setattr(BillingObservationKind, "__eq__", lambda left, right: True)
    paid = apply_reconciled_observation(_empty(), observation)
    assert _state(paid)["owner_id"] == "owner-1"
    assert _state(paid)["state"] == EntitlementState.PAID.value


def test_access_candidate_is_structural_and_carries_zero_runtime_authority():
    access = project_ordinary_access(_paid(), as_of=date(2026, 9, 30))
    values = dict(validate_ordinary_access_candidate(access))
    assert values["ordinary_access"] is True
    assert values["runtime_access_authority"] is False
    with pytest.raises(ValueError, match="zero runtime_access_authority"):
        validate_ordinary_access_candidate(
            _replace(access, runtime_access_authority=True)
        )
    with pytest.raises(ValueError, match="semantics are contradictory"):
        validate_ordinary_access_candidate(
            _replace(access, state="no_entitlement")
        )
