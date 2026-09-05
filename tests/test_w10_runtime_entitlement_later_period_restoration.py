"""Provider-neutral admission for one later-period restoration fact."""
from datetime import timedelta

import pytest

from reserved.billing import local_stripe_initial_payment as source
from reserved.billing import runtime_entitlement_admission as runtime
from tests.test_w10_stripe_later_period_restoration import RestorationHarness


def test_live_restoration_fact_is_consumed_by_distinct_runtime_boundary(tmp_path):
    h = RestorationHarness(tmp_path/'runtime.db')
    try:
        assert h.ingest().disposition == 'admitted'
        assert h.withdraw_initial().disposition == 'admitted'
        h.prepare_restoration(); result = h.restore()
        binding = runtime.bind_later_period_restoration_runtime_entitlement_admission(
            validate_admitted_billing_fact=source.validate_later_period_restoration_fact,
            project_admitted_billing_fact=source.project_later_period_restoration_fact)
        value = runtime.admit_later_period_restoration_runtime_entitlement(
            binding, authenticated_owner_id='synthetic-owner',
            billing_account_id='synthetic-billing', subscription_id='sub_Synthetic',
            admitted_billing_fact=result.fact,
            evaluated_at_utc=h.initial_end - timedelta(microseconds=1))
        projected = dict(
            runtime.validate_later_period_restoration_runtime_entitlement(value))
        assert projected['state'] == 'paid'
        assert projected['ordinary_access'] is True
        assert projected['derivation_kind'] == 'verified_later_period_restoration'
        assert projected['paid_sequence'] == 2
        assert projected['access_start_utc'] == h.initial_end
    finally:
        h.repo.close()


def test_cross_scope_or_wrong_protocol_fact_cannot_enter_restoration_runtime(tmp_path):
    h = RestorationHarness(tmp_path/'scope.db')
    try:
        assert h.ingest().disposition == 'admitted'
        assert h.withdraw_initial().disposition == 'admitted'
        h.prepare_restoration(); result = h.restore()
        binding = runtime.bind_later_period_restoration_runtime_entitlement_admission(
            validate_admitted_billing_fact=source.validate_later_period_restoration_fact,
            project_admitted_billing_fact=source.project_later_period_restoration_fact)
        with pytest.raises(runtime.RuntimeEntitlementAdmissionError):
            runtime.admit_later_period_restoration_runtime_entitlement(
                binding, authenticated_owner_id='other-owner',
                billing_account_id='synthetic-billing',
                subscription_id='sub_Synthetic', admitted_billing_fact=result.fact,
                evaluated_at_utc=h.initial_end)
        with pytest.raises(runtime.RuntimeEntitlementAdmissionError):
            runtime.admit_full_withdrawal_runtime_entitlement(binding,
                authenticated_owner_id='synthetic-owner',
                billing_account_id='synthetic-billing',
                subscription_id='sub_Synthetic', admitted_billing_fact=result.fact,
                evaluated_at_utc=h.initial_end)
    finally:
        h.repo.close()
