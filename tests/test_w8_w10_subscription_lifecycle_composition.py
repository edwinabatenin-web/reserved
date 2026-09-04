"""Early-W8 local composition checks for the bounded W10 lifecycle contracts.

The projections in this file are deliberately test-only.  They exercise exact
public structural APIs; they are not provider admission, persistence, runtime
access control, customer rendering, or a production adapter.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
import hashlib
from pathlib import Path
import subprocess

import pytest

from reserved.billing import cancellation_presentation
from reserved.billing import initial_paid_presentation
from reserved.billing import initial_payment_presentation
from reserved.billing import payment_recovery_presentation
from reserved.billing.entitlement_core import (
    CANDIDATE_CLASSIFICATION,
    CONTRACT_VERSION,
    BillingObservationCandidate,
    BillingObservationKind,
    EntitlementState,
    apply_reconciled_observation,
    empty_entitlement,
    materialise_time_boundary,
    project_entitlement_transition,
    project_ordinary_access,
    validate_entitlement_transition,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/W8_W10_SUBSCRIPTION_LIFECYCLE_COMPOSITION_EVIDENCE.md"
ALLOWED_PATHS = {
    "docs/W8_W10_SUBSCRIPTION_LIFECYCLE_COMPOSITION_EVIDENCE.md",
    "tests/test_w8_w10_subscription_lifecycle_composition.py",
}

OWNER = "owner-w8-local"
ACCOUNT = "billing-w8-local"
SUBSCRIPTION = "subscription-w8-local"
PLAN = "plan-monthly-29-local"


def _state(candidate):
    return dict(project_entitlement_transition(candidate))


def _access(candidate, on_date):
    return dict(project_ordinary_access(candidate, as_of=on_date))


def _event(
    kind,
    *,
    event_id,
    effective,
    paid_through=None,
    owner=OWNER,
    account=ACCOUNT,
    subscription=SUBSCRIPTION,
    evidence_reference=None,
):
    """Build a shape-only observation; this helper does not authenticate it."""

    return BillingObservationCandidate(
        CONTRACT_VERSION,
        event_id,
        owner,
        account,
        subscription,
        kind,
        effective,
        paid_through,
        evidence_reference or f"test-only-evidence:{event_id}",
    )


def _empty():
    return empty_entitlement(
        owner_id=OWNER,
        billing_account_id=ACCOUNT,
        subscription_id=SUBSCRIPTION,
    )


def _initial_paid():
    return apply_reconciled_observation(
        _empty(),
        _event(
            BillingObservationKind.INITIAL_PAYMENT_CONFIRMED,
            event_id="event-initial-success",
            effective=date(2026, 10, 1),
            paid_through=date(2026, 10, 31),
        ),
    )


def _utc_midnight(value):
    assert type(value) is date
    return datetime.combine(value, time.min).strftime("%Y-%m-%dT%H:%M:%SZ")


def _exclusive_paid_boundary(values):
    """Test-only date-to-exclusive-UTC projection; never production authority."""

    paid_through = values["paid_through"]
    assert type(paid_through) is date
    return _utc_midnight(paid_through + timedelta(days=1))


def _assert_entitlement_is_structural_only(values):
    assert values["candidate_classification"] == CANDIDATE_CLASSIFICATION
    for field in (
        "provider_observation_authenticated",
        "provider_provenance_authenticated",
        "provider_status_authority",
        "persistence_authority",
        "runtime_access_authority",
    ):
        assert values[field] is False


def _assert_presentation_is_zero_authority(presentation, projector):
    projected = dict(projector(presentation))
    assert projected["classification"] == "detached_zero_authority_copy_candidate"
    assert all(value is False for _, value in projected["authority"])
    return projected


def _initial_pending_presentation():
    facts = {
        "schema_version": initial_payment_presentation.FACTS_VERSION,
        "owner_reference": OWNER,
        "subscription_reference": SUBSCRIPTION,
        "plan_reference": PLAN,
        "state": "initial_payment_pending",
        "observed_at_utc": "2026-10-01T12:00:00Z",
        "evaluated_at_utc": "2026-10-01T12:04:59Z",
    }
    return initial_payment_presentation.build_initial_payment_presentation(
        facts=facts,
        expected_owner_reference=OWNER,
        expected_subscription_reference=SUBSCRIPTION,
        expected_plan_reference=PLAN,
    )


def _test_only_initial_paid_presentation(candidate, *, plan=PLAN):
    """Project compatible structural facts; explicitly not an admission adapter."""

    values = _state(validate_entitlement_transition(candidate))
    _assert_entitlement_is_structural_only(values)
    if values["state"] != EntitlementState.PAID.value:
        raise ValueError("test projection requires the exact paid structural state")
    if values["renews_automatically"] is not True:
        raise ValueError("test projection requires automatic renewal")
    history = values["processed_observations"]
    if len(history) != 1 or history[0][4] != "initial_payment_confirmed":
        raise ValueError("test projection requires direct initial-payment history")
    effective = _utc_midnight(values["entitlement_started_on"])
    boundary = _exclusive_paid_boundary(values)
    evaluated = (
        datetime.combine(values["entitlement_started_on"], time.min)
        + timedelta(minutes=4, seconds=59)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    facts = {
        "schema_version": initial_paid_presentation.FACTS_VERSION,
        "owner_reference": values["owner_id"],
        "subscription_reference": values["subscription_id"],
        "plan_reference": plan,
        "state": "initial_payment_verified_paid",
        # These are synthetic prerequisites assumed only to exercise S6H. The
        # zero-authority entitlement candidate cannot establish either fact.
        "successful_payment_observation_reconciled": True,
        "canonical_entitlement_state_observed": True,
        "renews_automatically": values["renews_automatically"],
        "payment_verified_at_utc": effective,
        "entitlement_effective_at_utc": effective,
        "paid_through_exclusive_utc": boundary,
        "next_renewal_at_utc": boundary,
        "evaluated_at_utc": evaluated,
    }
    return initial_paid_presentation.build_initial_paid_presentation(
        facts=facts,
        expected_owner_reference=OWNER,
        expected_subscription_reference=SUBSCRIPTION,
        expected_plan_reference=plan,
    )


def _test_only_recovery_presentation(candidate, *, evaluated=date(2026, 11, 3)):
    values = _state(validate_entitlement_transition(candidate))
    _assert_entitlement_is_structural_only(values)
    if values["state"] != EntitlementState.PAYMENT_RECOVERY.value:
        raise ValueError("test projection requires payment_recovery")
    facts = {
        "schema_version": payment_recovery_presentation.FACTS_VERSION,
        "owner_reference": values["owner_id"],
        "billing_account_reference": values["billing_account_id"],
        "subscription_reference": values["subscription_id"],
        "state": "payment_recovery",
        "recovery_started_at_utc": _utc_midnight(values["recovery_started_on"]),
        "recovery_deadline_exclusive_utc": _utc_midnight(
            values["recovery_deadline_exclusive"]
        ),
        "evaluated_at_utc": _utc_midnight(evaluated),
    }
    return payment_recovery_presentation.build_payment_recovery_presentation(
        facts=facts,
        expected_owner_reference=OWNER,
    )


def _test_only_cancellation_presentation(candidate, *, evaluated_on=date(2026, 10, 12)):
    values = _state(validate_entitlement_transition(candidate))
    _assert_entitlement_is_structural_only(values)
    if values["state"] != EntitlementState.PAID.value:
        raise ValueError("test projection requires paid remainder")
    if values["renews_automatically"] is not False:
        raise ValueError("test projection requires stopped renewal")
    history = values["processed_observations"]
    if not history or history[-1][4] != "cancellation_confirmed":
        raise ValueError("test projection requires cancellation-event history")
    cancellation_event_date = date.fromisoformat(history[-1][5])
    if type(evaluated_on) is not date or evaluated_on < cancellation_event_date:
        raise ValueError("evaluation cannot predate the cancellation event")
    boundary = _exclusive_paid_boundary(values)
    verified = f"{cancellation_event_date.isoformat()}T09:14:07Z"
    evaluated = f"{evaluated_on.isoformat()}T09:14:07Z"
    facts = {
        "schema_version": cancellation_presentation.FACTS_VERSION,
        "owner_reference": values["owner_id"],
        "billing_account_reference": values["billing_account_id"],
        "subscription_reference": values["subscription_id"],
        "state": "cancellation_confirmed_end_of_paid_period",
        "future_renewal_stopped": True,
        "paid_period_started_at_utc": _utc_midnight(values["entitlement_started_on"]),
        "cancellation_verified_at_utc": verified,
        "paid_through_exclusive_utc": boundary,
        "cancellation_effective_at_utc": boundary,
        "evaluated_at_utc": evaluated,
    }
    return cancellation_presentation.build_cancellation_presentation(
        facts=facts,
        expected_owner_reference=OWNER,
        expected_subscription_reference=SUBSCRIPTION,
    )


@pytest.mark.parametrize("state", ("initial_payment_pending", "initial_payment_failed"))
def test_pending_and_failed_initial_copy_never_claims_or_grants_paid_access(state):
    facts = {
        "schema_version": initial_payment_presentation.FACTS_VERSION,
        "owner_reference": OWNER,
        "subscription_reference": SUBSCRIPTION,
        "plan_reference": PLAN,
        "state": state,
        "observed_at_utc": "2026-10-01T12:00:00Z",
        "evaluated_at_utc": "2026-10-01T12:04:59Z",
    }
    presentation = initial_payment_presentation.build_initial_payment_presentation(
        facts=facts,
        expected_owner_reference=OWNER,
        expected_subscription_reference=SUBSCRIPTION,
        expected_plan_reference=PLAN,
    )
    values = _assert_presentation_is_zero_authority(
        presentation, initial_payment_presentation.project_initial_payment_presentation
    )
    assert dict(values["copy"])["access_message"] == "Paid access has not started."
    with pytest.raises((TypeError, ValueError)):
        apply_reconciled_observation(_empty(), presentation)
    with pytest.raises((TypeError, ValueError)):
        validate_entitlement_transition(presentation)


def test_structural_initial_success_transitions_to_paid_but_remains_non_authoritative():
    paid = _initial_paid()
    values = _state(paid)
    assert values["state"] == EntitlementState.PAID.value
    assert values["renews_automatically"] is True
    assert values["paid_through"] == date(2026, 10, 31)
    _assert_entitlement_is_structural_only(values)
    access = _access(paid, date(2026, 10, 31))
    assert access["ordinary_access"] is True
    assert access["runtime_access_authority"] is False


@pytest.mark.parametrize(
    "label",
    ("checkout_complete", "browser_returned", "provider_paid", "active", "paid"),
)
def test_browser_provider_and_generic_paid_labels_cannot_build_paid_copy(label):
    facts = {
        "schema_version": initial_paid_presentation.FACTS_VERSION,
        "owner_reference": OWNER,
        "subscription_reference": SUBSCRIPTION,
        "plan_reference": PLAN,
        "state": label,
        "successful_payment_observation_reconciled": True,
        "canonical_entitlement_state_observed": True,
        "renews_automatically": True,
        "payment_verified_at_utc": "2026-10-01T00:00:00Z",
        "entitlement_effective_at_utc": "2026-10-01T00:00:00Z",
        "paid_through_exclusive_utc": "2026-11-01T00:00:00Z",
        "next_renewal_at_utc": "2026-11-01T00:00:00Z",
        "evaluated_at_utc": "2026-10-01T00:04:59Z",
    }
    with pytest.raises(ValueError, match="state must be exactly"):
        initial_paid_presentation.build_initial_paid_presentation(
            facts=facts,
            expected_owner_reference=OWNER,
            expected_subscription_reference=SUBSCRIPTION,
            expected_plan_reference=PLAN,
        )


def test_paid_start_copy_requires_renewing_paid_state_and_exact_boundary():
    paid = _initial_paid()
    presentation = _test_only_initial_paid_presentation(paid)
    values = _assert_presentation_is_zero_authority(
        presentation, initial_paid_presentation.project_initial_paid_presentation
    )
    assert values["kind"] == "initial_payment_verified_paid"
    assert values["paid_through_exclusive_utc"] == "2026-11-01T00:00:00Z"
    assert values["next_renewal_at_utc"] == "2026-11-01T00:00:00Z"
    assert dict(values["copy"])["paid_through_exclusive_utc"] == values[
        "paid_through_exclusive_utc"
    ]

    tampered = dict(
        (
            ("schema_version", initial_paid_presentation.FACTS_VERSION),
            ("owner_reference", OWNER),
            ("subscription_reference", SUBSCRIPTION),
            ("plan_reference", PLAN),
            ("state", "initial_payment_verified_paid"),
            ("successful_payment_observation_reconciled", True),
            ("canonical_entitlement_state_observed", True),
            ("renews_automatically", True),
            ("payment_verified_at_utc", "2026-10-01T00:00:00Z"),
            ("entitlement_effective_at_utc", "2026-10-01T00:00:00Z"),
            ("paid_through_exclusive_utc", "2026-11-01T00:00:00Z"),
            ("next_renewal_at_utc", "2026-11-01T00:00:01Z"),
            ("evaluated_at_utc", "2026-10-01T00:04:59Z"),
        )
    )
    with pytest.raises(ValueError, match="boundaries must match"):
        initial_paid_presentation.build_initial_paid_presentation(
            facts=tampered,
            expected_owner_reference=OWNER,
            expected_subscription_reference=SUBSCRIPTION,
            expected_plan_reference=PLAN,
        )

    recovery = apply_reconciled_observation(
        paid,
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="event-later-failure",
            effective=date(2026, 11, 1),
        ),
    )
    restored = apply_reconciled_observation(
        recovery,
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_CONFIRMED,
            event_id="event-later-recovery",
            effective=date(2026, 11, 3),
            paid_through=date(2026, 11, 30),
        ),
    )
    with pytest.raises(ValueError, match="direct initial-payment history"):
        _test_only_initial_paid_presentation(restored)


def test_cancellation_preserves_paid_remainder_and_excludes_renewal_copy():
    cancelled = apply_reconciled_observation(
        _initial_paid(),
        _event(
            BillingObservationKind.CANCELLATION_CONFIRMED,
            event_id="event-cancellation",
            effective=date(2026, 10, 12),
        ),
    )
    values = _state(cancelled)
    assert values["state"] == EntitlementState.PAID.value
    assert values["renews_automatically"] is False
    assert values["paid_through"] == date(2026, 10, 31)
    assert _access(cancelled, date(2026, 10, 31))["ordinary_access"] is True
    with pytest.raises(ValueError, match="automatic renewal"):
        _test_only_initial_paid_presentation(cancelled)

    presentation = _test_only_cancellation_presentation(cancelled)
    projected = _assert_presentation_is_zero_authority(
        presentation, cancellation_presentation.project_cancellation_presentation
    )
    assert dict(projected["copy"])["paid_through_exclusive_utc"] == (
        "2026-11-01T00:00:00Z"
    )
    with pytest.raises(ValueError, match="after cancellation"):
        apply_reconciled_observation(
            cancelled,
            _event(
                BillingObservationKind.RENEWAL_PAYMENT_CONFIRMED,
                event_id="event-success-after-cancellation",
                effective=date(2026, 11, 1),
                paid_through=date(2026, 11, 30),
            ),
        )
    with pytest.raises(ValueError, match="after cancellation"):
        apply_reconciled_observation(
            cancelled,
            _event(
                BillingObservationKind.RENEWAL_PAYMENT_FAILED,
                event_id="event-failure-after-cancellation",
                effective=date(2026, 11, 1),
            ),
        )
    expired = materialise_time_boundary(cancelled, as_of=date(2026, 11, 1))
    assert _state(expired)["state"] == EntitlementState.SUSPENDED.value
    assert _access(expired, date(2026, 11, 1))["ordinary_access"] is False


def test_cancellation_projection_binds_history_and_cannot_predate_event():
    cancelled = apply_reconciled_observation(
        _initial_paid(),
        _event(
            BillingObservationKind.CANCELLATION_CONFIRMED,
            event_id="event-cancellation",
            effective=date(2026, 10, 12),
        ),
    )
    with pytest.raises(ValueError, match="cannot predate"):
        _test_only_cancellation_presentation(
            cancelled, evaluated_on=date(2026, 10, 11)
        )


def test_first_failure_has_non_extendable_seven_day_recovery_and_matching_copy():
    failure = _event(
        BillingObservationKind.RENEWAL_PAYMENT_FAILED,
        event_id="event-renewal-failure",
        effective=date(2026, 11, 1),
    )
    recovery = apply_reconciled_observation(_initial_paid(), failure)
    duplicate = apply_reconciled_observation(recovery, failure)
    values = _state(recovery)
    duplicate_values = _state(duplicate)
    assert values["state"] == EntitlementState.PAYMENT_RECOVERY.value
    assert values["recovery_started_on"] == date(2026, 11, 1)
    assert values["recovery_deadline_exclusive"] == date(2026, 11, 8)
    assert duplicate_values["recovery_deadline_exclusive"] == values[
        "recovery_deadline_exclusive"
    ]
    assert duplicate_values["processed_observations"] == values["processed_observations"]

    distinct_before_deadline = apply_reconciled_observation(
        recovery,
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="event-distinct-failure-before-deadline",
            effective=date(2026, 11, 3),
        ),
    )
    before_values = _state(distinct_before_deadline)
    assert before_values["state"] == EntitlementState.PAYMENT_RECOVERY.value
    assert before_values["recovery_started_on"] == date(2026, 11, 1)
    assert before_values["recovery_deadline_exclusive"] == date(2026, 11, 8)
    for offset in range(7):
        assert _access(
            distinct_before_deadline, date(2026, 11, 1) + timedelta(days=offset)
        )["ordinary_access"] is True
    assert _access(distinct_before_deadline, date(2026, 11, 8))[
        "ordinary_access"
    ] is False

    for failed_on in (date(2026, 11, 8), date(2026, 11, 9)):
        stopped = apply_reconciled_observation(
            distinct_before_deadline,
            _event(
                BillingObservationKind.RENEWAL_PAYMENT_FAILED,
                event_id=f"event-distinct-failure-{failed_on.isoformat()}",
                effective=failed_on,
            ),
        )
        stopped_values = _state(stopped)
        assert stopped_values["state"] == EntitlementState.SUSPENDED.value
        assert stopped_values["recovery_started_on"] == date(2026, 11, 1)
        assert stopped_values["recovery_deadline_exclusive"] == date(2026, 11, 8)
        assert _access(stopped, failed_on)["ordinary_access"] is False

    presentation = _test_only_recovery_presentation(distinct_before_deadline)
    projected = _assert_presentation_is_zero_authority(
        presentation,
        payment_recovery_presentation.project_payment_recovery_presentation,
    )
    assert dict(projected["copy"])["deadline_exclusive_utc"] == (
        "2026-11-08T00:00:00Z"
    )


def test_verified_recovery_restores_paid_state_without_presentation_authority():
    recovery = apply_reconciled_observation(
        _initial_paid(),
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="event-renewal-failure",
            effective=date(2026, 11, 1),
        ),
    )
    restored = apply_reconciled_observation(
        recovery,
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_CONFIRMED,
            event_id="event-renewal-restored",
            effective=date(2026, 11, 3),
            paid_through=date(2026, 11, 30),
        ),
    )
    values = _state(restored)
    assert values["state"] == EntitlementState.PAID.value
    assert values["recovery_started_on"] is None
    assert values["recovery_deadline_exclusive"] is None
    assert values["paid_through"] == date(2026, 11, 30)
    _assert_entitlement_is_structural_only(values)


def test_expiry_suspends_and_stale_recovery_and_cancellation_construction_rejects():
    recovery = apply_reconciled_observation(
        _initial_paid(),
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="event-renewal-failure",
            effective=date(2026, 11, 1),
        ),
    )
    suspended = materialise_time_boundary(recovery, as_of=date(2026, 11, 8))
    assert _state(suspended)["state"] == EntitlementState.SUSPENDED.value
    assert _access(suspended, date(2026, 11, 8))["ordinary_access"] is False
    with pytest.raises(ValueError, match="requires payment_recovery"):
        _test_only_recovery_presentation(suspended, evaluated=date(2026, 11, 8))

    stale_recovery_facts = {
        "schema_version": payment_recovery_presentation.FACTS_VERSION,
        "owner_reference": OWNER,
        "billing_account_reference": ACCOUNT,
        "subscription_reference": SUBSCRIPTION,
        "state": "payment_recovery",
        "recovery_started_at_utc": "2026-11-01T00:00:00Z",
        "recovery_deadline_exclusive_utc": "2026-11-08T00:00:00Z",
        "evaluated_at_utc": "2026-11-08T00:00:00Z",
    }
    with pytest.raises(ValueError, match="stale or not effective"):
        payment_recovery_presentation.build_payment_recovery_presentation(
            facts=stale_recovery_facts,
            expected_owner_reference=OWNER,
        )

    cancelled = apply_reconciled_observation(
        _initial_paid(),
        _event(
            BillingObservationKind.CANCELLATION_CONFIRMED,
            event_id="event-cancellation",
            effective=date(2026, 10, 12),
        ),
    )
    boundary = _exclusive_paid_boundary(_state(cancelled))
    stale_facts = {
        "schema_version": cancellation_presentation.FACTS_VERSION,
        "owner_reference": OWNER,
        "billing_account_reference": ACCOUNT,
        "subscription_reference": SUBSCRIPTION,
        "state": "cancellation_confirmed_end_of_paid_period",
        "future_renewal_stopped": True,
        "paid_period_started_at_utc": "2026-10-01T00:00:00Z",
        "cancellation_verified_at_utc": "2026-10-12T09:14:07Z",
        "paid_through_exclusive_utc": boundary,
        "cancellation_effective_at_utc": boundary,
        "evaluated_at_utc": boundary,
    }
    with pytest.raises(ValueError, match="stale or not effective"):
        cancellation_presentation.build_cancellation_presentation(
            facts=stale_facts,
            expected_owner_reference=OWNER,
            expected_subscription_reference=SUBSCRIPTION,
        )


def test_emitted_recovery_and_cancellation_candidates_are_not_freshness_bearing():
    recovery = apply_reconciled_observation(
        _initial_paid(),
        _event(
            BillingObservationKind.RENEWAL_PAYMENT_FAILED,
            event_id="event-renewal-failure",
            effective=date(2026, 11, 1),
        ),
    )
    recovery_output = _test_only_recovery_presentation(recovery)
    cancelled = apply_reconciled_observation(
        _initial_paid(),
        _event(
            BillingObservationKind.CANCELLATION_CONFIRMED,
            event_id="event-cancellation",
            effective=date(2026, 10, 12),
        ),
    )
    cancellation_output = _test_only_cancellation_presentation(cancelled)

    # Projectors can only revalidate the emitted structure. Neither candidate
    # retains evaluated_at, accepts an as-of time, or proves safe later render.
    assert "evaluated_at_utc" not in dict(recovery_output)
    assert "evaluated_at_utc" not in dict(cancellation_output)
    assert (
        payment_recovery_presentation.project_payment_recovery_presentation(
            recovery_output
        )
        == recovery_output
    )
    assert (
        cancellation_presentation.project_cancellation_presentation(
            cancellation_output
        )
        == cancellation_output
    )


def test_presentation_outputs_cannot_be_reused_as_entitlement_or_admission_authority():
    outputs = (
        _initial_pending_presentation(),
        _test_only_initial_paid_presentation(_initial_paid()),
        _test_only_recovery_presentation(
            apply_reconciled_observation(
                _initial_paid(),
                _event(
                    BillingObservationKind.RENEWAL_PAYMENT_FAILED,
                    event_id="event-renewal-failure",
                    effective=date(2026, 11, 1),
                ),
            )
        ),
        _test_only_cancellation_presentation(
            apply_reconciled_observation(
                _initial_paid(),
                _event(
                    BillingObservationKind.CANCELLATION_CONFIRMED,
                    event_id="event-cancellation",
                    effective=date(2026, 10, 12),
                ),
            )
        ),
    )
    for output in outputs:
        with pytest.raises((TypeError, ValueError)):
            apply_reconciled_observation(_initial_paid(), output)
        with pytest.raises((TypeError, ValueError)):
            validate_entitlement_transition(output)
        assert all(value is False for _, value in dict(output)["authority"])


@pytest.mark.parametrize(
    ("field", "replacement", "expected_name"),
    (
        ("owner", "other-owner", "owner_reference"),
        ("subscription", "other-subscription", "ownership boundary"),
        ("plan", "other-plan", "plan_reference"),
    ),
)
def test_cross_owner_subscription_and_plan_projections_fail_closed(
    field, replacement, expected_name
):
    paid = _initial_paid()
    if field == "owner":
        with pytest.raises(ValueError, match=expected_name):
            initial_paid_presentation.build_initial_paid_presentation(
                facts=dict(
                    (
                        ("schema_version", initial_paid_presentation.FACTS_VERSION),
                        ("owner_reference", OWNER),
                        ("subscription_reference", SUBSCRIPTION),
                        ("plan_reference", PLAN),
                        ("state", "initial_payment_verified_paid"),
                        ("successful_payment_observation_reconciled", True),
                        ("canonical_entitlement_state_observed", True),
                        ("renews_automatically", True),
                        ("payment_verified_at_utc", "2026-10-01T00:00:00Z"),
                        ("entitlement_effective_at_utc", "2026-10-01T00:00:00Z"),
                        ("paid_through_exclusive_utc", "2026-11-01T00:00:00Z"),
                        ("next_renewal_at_utc", "2026-11-01T00:00:00Z"),
                        ("evaluated_at_utc", "2026-10-01T00:04:59Z"),
                    )
                ),
                expected_owner_reference=replacement,
                expected_subscription_reference=SUBSCRIPTION,
                expected_plan_reference=PLAN,
            )
    elif field == "subscription":
        with pytest.raises(ValueError, match=expected_name):
            apply_reconciled_observation(
                paid,
                _event(
                    BillingObservationKind.RENEWAL_PAYMENT_FAILED,
                    event_id="event-cross-subscription",
                    effective=date(2026, 11, 1),
                    subscription=replacement,
                ),
            )
    else:
        presentation = _test_only_initial_paid_presentation(paid)
        facts = dict(
            (
                ("schema_version", initial_paid_presentation.FACTS_VERSION),
                ("owner_reference", OWNER),
                ("subscription_reference", SUBSCRIPTION),
                ("plan_reference", PLAN),
                ("state", "initial_payment_verified_paid"),
                ("successful_payment_observation_reconciled", True),
                ("canonical_entitlement_state_observed", True),
                ("renews_automatically", True),
                ("payment_verified_at_utc", dict(presentation)["payment_verified_at_utc"]),
                (
                    "entitlement_effective_at_utc",
                    dict(presentation)["entitlement_effective_at_utc"],
                ),
                ("paid_through_exclusive_utc", dict(presentation)["paid_through_exclusive_utc"]),
                ("next_renewal_at_utc", dict(presentation)["next_renewal_at_utc"]),
                ("evaluated_at_utc", dict(presentation)["evaluated_at_utc"]),
            )
        )
        with pytest.raises(ValueError, match=expected_name):
            initial_paid_presentation.build_initial_paid_presentation(
                facts=facts,
                expected_owner_reference=OWNER,
                expected_subscription_reference=SUBSCRIPTION,
                expected_plan_reference=replacement,
            )


def test_reused_event_id_with_altered_provenance_fails_closed():
    paid = _initial_paid()
    altered = _event(
        BillingObservationKind.INITIAL_PAYMENT_CONFIRMED,
        event_id="event-initial-success",
        effective=date(2026, 10, 1),
        paid_through=date(2026, 10, 31),
        evidence_reference="test-only-evidence:altered",
    )
    with pytest.raises(ValueError, match="reused with different content"):
        apply_reconciled_observation(paid, altered)


def test_evidence_binds_exact_current_integration_sources_and_scope():
    evidence = EVIDENCE.read_text(encoding="utf-8")
    expected = {
        "FOUNDER_DECISIONS.md": (
            "03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4"
        ),
        "reserved/billing/entitlement_core.py": (
            "201c92c1093b663b786a5e49a1c2ca0d714f3fe6fdaebf18c0c7d486ef25f415"
        ),
        "reserved/billing/initial_payment_presentation.py": (
            "009970f3217bee7dddc59471f02ce801d8992e7d92b951f41a7ee97cc2bd5451"
        ),
        "reserved/billing/initial_paid_presentation.py": (
            "cdb3d75d109bcaabe281f07f22675b785d40406bca685f6892b3085c45208b6d"
        ),
        "reserved/billing/payment_recovery_presentation.py": (
            "48d49f28136690f5be8a6cdf0dd927f9e3f0d0ffa0972d1daa0b60f5f23c42e8"
        ),
        "reserved/billing/cancellation_presentation.py": (
            "0f8d252f6a5556333187856e527fcdf02197572baebef1a0edc4c71999d0946d"
        ),
    }
    assert "8fdcc0414c72393c4f575f7597bd30850b707d35" in evidence
    assert "773aea8429967dc086ac0ced2f38302b8998fc7c" in evidence
    for path, expected_hash in expected.items():
        if path == "FOUNDER_DECISIONS.md":
            content = subprocess.run(
                [
                    "git",
                    "show",
                    f"10fb93e2e6ab567a72d2370c1603768a7ac04bb5:{path}",
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
            ).stdout
        else:
            content = (ROOT / path).read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected_hash
        assert expected_hash in evidence
    for phrase in (
        "test-only projection",
        "not production admission",
        "does not close w8 or w10",
        "completion denominators",
    ):
        assert phrase in evidence.lower()


def test_historical_package_scope_remains_exact_after_checkpoint():
    introduction_commits = {
        subprocess.run(
            ["git", "log", "--diff-filter=A", "-1", "--format=%H", "--", path],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        for path in ALLOWED_PATHS
    }
    assert len(introduction_commits) == 1
    introduced = subprocess.run(
        [
            "git",
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            introduction_commits.pop(),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert set(introduced) == ALLOWED_PATHS
