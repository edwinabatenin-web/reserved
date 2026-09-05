"""Provider-neutral versioned withdrawal runtime evidence."""
from datetime import timedelta

import pytest

from reserved.billing import local_stripe_initial_payment as source
from reserved.billing import runtime_entitlement_admission as runtime
from tests.test_w10_stripe_full_withdrawal import WithdrawalHarness


def test_withdrawal_fact_admits_only_to_distinct_v3_runtime(tmp_path):
    h = WithdrawalHarness(tmp_path/'runtime.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_withdrawal(); result = h.withdraw()
        binding = runtime.bind_full_withdrawal_runtime_entitlement_admission(
            validate_admitted_billing_fact=source.validate_full_withdrawal_fact,
            project_admitted_billing_fact=source.project_full_withdrawal_fact)
        value = runtime.admit_full_withdrawal_runtime_entitlement(binding,
            authenticated_owner_id='synthetic-owner', billing_account_id='synthetic-billing',
            subscription_id='sub_Synthetic', admitted_billing_fact=result.fact,
            evaluated_at_utc=h.withdrawal_time)
        projected = dict(runtime.validate_full_withdrawal_runtime_entitlement(value))
        assert projected['state'] == 'suspended' and projected['ordinary_access'] is False
        assert projected['recovery_deadline_exclusive_at_utc'] is None
        with pytest.raises(runtime.RuntimeEntitlementAdmissionError):
            runtime.admit_exact_instant_runtime_entitlement(binding,
                authenticated_owner_id='synthetic-owner', billing_account_id='synthetic-billing',
                subscription_id='sub_Synthetic', admitted_billing_fact=result.fact,
                evaluated_at_utc=h.withdrawal_time + timedelta(seconds=1))
    finally:
        h.repo.close()
