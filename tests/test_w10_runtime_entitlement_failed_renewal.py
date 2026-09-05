"""Versioned exact-instant runtime admission and paid-access guard tests."""
import gc
from datetime import timedelta

import pytest

from reserved.billing import local_stripe_initial_payment as source
from reserved.billing import paid_access_guard as guard_module
from reserved.billing import runtime_entitlement_admission as runtime
from tests.test_w10_stripe_failed_renewal import FailedRenewalHarness


def admitted_recovery(tmp_path):
    h = FailedRenewalHarness(tmp_path/'runtime.db')
    assert h.ingest().disposition == 'admitted'
    h.prepare_failure()
    fact = h.fail().fact
    binding = runtime.bind_exact_instant_runtime_entitlement_admission(
        validate_admitted_billing_fact=source.validate_failed_renewal_fact,
        project_admitted_billing_fact=source.project_failed_renewal_fact)
    value = runtime.admit_exact_instant_runtime_entitlement(
        binding, authenticated_owner_id='synthetic-owner',
        billing_account_id='synthetic-billing', subscription_id='sub_Synthetic',
        admitted_billing_fact=fact, evaluated_at_utc=h.failure_time)
    return h, fact, binding, value


def exact_guard():
    return guard_module.bind_exact_instant_paid_access_guard(
        validate_runtime_entitlement=runtime.validate_exact_instant_runtime_entitlement,
        project_runtime_entitlement=runtime.project_exact_instant_runtime_entitlement)


def decision(guard, value, at, **changes):
    inputs = dict(endpoint='v2.settings_page',
        authenticated_owner_id='synthetic-owner', current_runtime_entitlement=value,
        evaluated_at_utc=at)
    inputs.update(changes)
    return dict(guard_module.validate_exact_instant_paid_access_decision(
        guard_module.evaluate_exact_instant_paid_access(guard, **inputs)))


def test_v2_runtime_is_exactly_bound_to_live_durable_recovery(tmp_path):
    h, _, _, value = admitted_recovery(tmp_path)
    try:
        fields = dict(runtime.validate_exact_instant_runtime_entitlement(value))
        assert fields['protocol_version'] == runtime.EXACT_INSTANT_RUNTIME_DECISION_PROTOCOL_VERSION
        assert fields['admission_status'] == runtime.EXACT_INSTANT_RUNTIME_ADMISSION_STATUS
        assert fields['state'] == 'payment_recovery' and fields['ordinary_access'] is True
        assert fields['transition_effective_at_utc'] == h.failure_time
        assert fields['recovery_deadline_exclusive_at_utc'] == h.failure_time + timedelta(days=7)
        assert fields['lifecycle_head'] == h.authority.snapshot().lifecycle_head
    finally:
        h.repo.close()


def test_v1_and_v2_readers_refuse_each_others_runtime_handles(tmp_path):
    from tests.test_w10_runtime_entitlement_admission import authority, fact_view, admit
    old_binding, issue = authority()
    old_runtime = admit(old_binding, issue(fact_view()))
    h, _, _, value = admitted_recovery(tmp_path)
    try:
        with pytest.raises(ValueError):
            runtime.validate_runtime_entitlement(value)
        with pytest.raises(ValueError):
            runtime.validate_exact_instant_runtime_entitlement(old_runtime)
    finally:
        h.repo.close()


@pytest.mark.parametrize('offset,allowed,reason', [
    (timedelta(0), True, 'allowed_payment_recovery'),
    (timedelta(days=7, microseconds=-1), True, 'allowed_payment_recovery'),
    (timedelta(days=7), False, 'runtime_entitlement_stale'),
    (timedelta(days=7, microseconds=1), False, 'runtime_entitlement_stale'),
])
def test_guard_enforces_half_open_arbitrary_second_interval(tmp_path, offset, allowed, reason):
    h, _, _, value = admitted_recovery(tmp_path)
    try:
        result = decision(exact_guard(), value, h.failure_time + offset)
        assert result['allowed'] is allowed and result['reason'] == reason
        assert result['provider_contacted'] is False
        assert result['persisted'] is False
        assert result['route_wiring_active'] is False
    finally:
        h.repo.close()


def test_before_transition_wrong_owner_and_nonpaid_endpoint_deny(tmp_path):
    h, _, _, value = admitted_recovery(tmp_path)
    try:
        guard = exact_guard()
        assert decision(guard, value, h.failure_time - timedelta(microseconds=1))['reason'] == (
            'runtime_entitlement_temporal_order_invalid')
        assert decision(guard, value, h.failure_time,
            authenticated_owner_id='other-owner')['reason'] == 'cross_owner_entitlement'
        assert decision(guard, value, h.failure_time,
            endpoint='public.plans')['reason'] == 'endpoint_not_in_paid_boundary'
    finally:
        h.repo.close()


def test_runtime_revalidation_fails_after_authority_or_store_loss(tmp_path):
    h, _, _, value = admitted_recovery(tmp_path)
    h.authority.revoke()
    try:
        with pytest.raises(ValueError):
            runtime.validate_exact_instant_runtime_entitlement(value)
        result = decision(exact_guard(), value, h.failure_time)
        assert result['allowed'] is False and result['reason'] == 'runtime_entitlement_invalid'
    finally:
        h.repo.close()


@pytest.mark.parametrize('owner,account,subscription', [
    ('other-owner', 'synthetic-billing', 'sub_Synthetic'),
    ('synthetic-owner', 'other-billing', 'sub_Synthetic'),
    ('synthetic-owner', 'synthetic-billing', 'sub_Other'),
])
def test_runtime_admission_refuses_cross_scope_fact(tmp_path, owner, account, subscription):
    h = FailedRenewalHarness(tmp_path/'cross.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_failure()
        fact = h.fail().fact
        binding = runtime.bind_exact_instant_runtime_entitlement_admission(
            validate_admitted_billing_fact=source.validate_failed_renewal_fact,
            project_admitted_billing_fact=source.project_failed_renewal_fact)
        with pytest.raises(ValueError):
            runtime.admit_exact_instant_runtime_entitlement(binding,
                authenticated_owner_id=owner, billing_account_id=account,
                subscription_id=subscription, admitted_billing_fact=fact,
                evaluated_at_utc=h.failure_time)
    finally:
        h.repo.close()


def test_plain_tuples_and_same_validator_projector_have_no_authority(tmp_path):
    with pytest.raises(ValueError):
        runtime.bind_exact_instant_runtime_entitlement_admission(
            validate_admitted_billing_fact=source.validate_failed_renewal_fact,
            project_admitted_billing_fact=source.validate_failed_renewal_fact)
    h, _, _, value = admitted_recovery(tmp_path)
    try:
        projection = runtime.validate_exact_instant_runtime_entitlement(value)
        result = decision(exact_guard(), projection, h.failure_time)
        assert result['allowed'] is False and result['reason'] == 'runtime_entitlement_invalid'
    finally:
        h.repo.close()


def _registry_sizes():
    return (len(runtime._EXACT_BINDINGS), len(runtime._EXACT_RUNTIMES),
            len(guard_module._EXACT_GUARDS), len(guard_module._EXACT_DECISIONS))


def test_repeated_allowed_and_expired_requests_release_all_v2_registry_rows(tmp_path):
    h = FailedRenewalHarness(tmp_path/'gc-requests.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_failure()
        assert h.fail().disposition == 'admitted'
        gc.collect()
        baseline = _registry_sizes()
        deadline = h.failure_time + timedelta(days=7)
        for _ in range(40):
            assert source.allows_paid_request(
                h.authority, h.repo, user_id=1,
                now=deadline - timedelta(microseconds=1))
        for offset in (timedelta(0), timedelta(microseconds=1)):
            for _ in range(40):
                assert not source.allows_paid_request(
                    h.authority, h.repo, user_id=1, now=deadline + offset)
        gc.collect()
        assert _registry_sizes() == baseline
    finally:
        h.repo.close()


def test_v2_registry_callbacks_preserve_live_and_reused_identity_entries(tmp_path):
    h, fact, binding, value = admitted_recovery(tmp_path)
    guard = exact_guard()
    issued_decision = guard_module.evaluate_exact_instant_paid_access(
        guard, endpoint='v2.settings_page', authenticated_owner_id='synthetic-owner',
        current_runtime_entitlement=value, evaluated_at_utc=h.failure_time)
    try:
        gc.collect()
        assert runtime._EXACT_BINDINGS[id(binding)][2]() is binding
        assert runtime._EXACT_RUNTIMES[id(value)][3]() is value
        assert guard_module._EXACT_GUARDS[id(guard)][2]() is guard
        assert guard_module._EXACT_DECISIONS[id(issued_decision)][1]() is issued_decision
        runtime.validate_exact_instant_runtime_entitlement(value)
        guard_module.validate_exact_instant_paid_access_decision(issued_decision)

        # Simulate an allocator reusing a collected handle identity: each stale
        # callback must compare its own weakref before removing the newer row.
        older_binding = runtime.bind_exact_instant_runtime_entitlement_admission(
            validate_admitted_billing_fact=source.validate_failed_renewal_fact,
            project_admitted_billing_fact=source.project_failed_renewal_fact)
        newer_binding = runtime.bind_exact_instant_runtime_entitlement_admission(
            validate_admitted_billing_fact=source.validate_failed_renewal_fact,
            project_admitted_billing_fact=source.project_failed_renewal_fact)
        old_id = id(older_binding)
        newer_state = runtime._EXACT_BINDINGS[id(newer_binding)]
        runtime._EXACT_BINDINGS[old_id] = newer_state
        del older_binding
        gc.collect()
        assert runtime._EXACT_BINDINGS.get(old_id) is newer_state
        runtime._EXACT_BINDINGS.pop(old_id)

        newer_value = runtime.admit_exact_instant_runtime_entitlement(
            binding, authenticated_owner_id='synthetic-owner',
            billing_account_id='synthetic-billing', subscription_id='sub_Synthetic',
            admitted_billing_fact=fact, evaluated_at_utc=h.failure_time)
        old_id = id(value)
        newer_state = runtime._EXACT_RUNTIMES[id(newer_value)]
        runtime._EXACT_RUNTIMES[old_id] = newer_state
        del value
        gc.collect()
        assert runtime._EXACT_RUNTIMES.get(old_id) is newer_state
        runtime._EXACT_RUNTIMES.pop(old_id)

        newer_guard = exact_guard()
        old_id = id(guard)
        newer_state = guard_module._EXACT_GUARDS[id(newer_guard)]
        guard_module._EXACT_GUARDS[old_id] = newer_state
        del guard
        gc.collect()
        assert guard_module._EXACT_GUARDS.get(old_id) is newer_state
        guard_module._EXACT_GUARDS.pop(old_id)

        newer_decision = guard_module.evaluate_exact_instant_paid_access(
            newer_guard, endpoint='v2.settings_page',
            authenticated_owner_id='synthetic-owner',
            current_runtime_entitlement=newer_value,
            evaluated_at_utc=h.failure_time + timedelta(days=7))
        old_id = id(issued_decision)
        newer_state = guard_module._EXACT_DECISIONS[id(newer_decision)]
        guard_module._EXACT_DECISIONS[old_id] = newer_state
        del issued_decision
        gc.collect()
        assert guard_module._EXACT_DECISIONS.get(old_id) is newer_state
        guard_module._EXACT_DECISIONS.pop(old_id)
        assert dict(guard_module.validate_exact_instant_paid_access_decision(
            newer_decision))['allowed'] is False
    finally:
        h.repo.close()
