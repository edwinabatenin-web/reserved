"""Exact 28-member paid-boundary consequence for full withdrawal."""
from datetime import timedelta

from reserved.billing import local_stripe_initial_payment as source
from reserved.billing import paid_access_guard as guard
from reserved.billing import runtime_entitlement_admission as runtime
from tests.test_w10_stripe_full_withdrawal import WithdrawalHarness


def test_every_paid_endpoint_denies_at_transition_and_allows_immediately_before(tmp_path):
    h = WithdrawalHarness(tmp_path/'access.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_withdrawal(); result = h.withdraw()
        admission = runtime.bind_full_withdrawal_runtime_entitlement_admission(
            validate_admitted_billing_fact=source.validate_full_withdrawal_fact,
            project_admitted_billing_fact=source.project_full_withdrawal_fact)
        entitlement = runtime.admit_full_withdrawal_runtime_entitlement(admission,
            authenticated_owner_id='synthetic-owner', billing_account_id='synthetic-billing',
            subscription_id='sub_Synthetic', admitted_billing_fact=result.fact,
            evaluated_at_utc=h.withdrawal_time)
        boundary = guard.bind_full_withdrawal_paid_access_guard(
            validate_runtime_entitlement=runtime.validate_full_withdrawal_runtime_entitlement,
            project_runtime_entitlement=runtime.project_full_withdrawal_runtime_entitlement)
        assert len(guard.PAID_ENDPOINTS) == 33
        for endpoint in guard.PAID_ENDPOINTS:
            before = guard.evaluate_full_withdrawal_paid_access(boundary, endpoint=endpoint,
                authenticated_owner_id='synthetic-owner',
                current_runtime_entitlement=entitlement,
                evaluated_at_utc=h.withdrawal_time - timedelta(microseconds=1))
            at = guard.evaluate_full_withdrawal_paid_access(boundary, endpoint=endpoint,
                authenticated_owner_id='synthetic-owner',
                current_runtime_entitlement=entitlement,
                evaluated_at_utc=h.withdrawal_time)
            assert dict(guard.validate_full_withdrawal_paid_access_decision(before))['allowed']
            assert not dict(guard.validate_full_withdrawal_paid_access_decision(at))['allowed']
    finally:
        h.repo.close()
