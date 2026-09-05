"""Live withdrawal fact exact-instant and stale-handle evidence."""
from datetime import timedelta

import pytest

from reserved.billing import local_stripe_initial_payment as source
from reserved.billing import exact_utc_entitlement as exact
from tests.test_w10_stripe_full_withdrawal import WithdrawalHarness


def test_live_fact_projection_and_exact_boundary(tmp_path):
    h = WithdrawalHarness(tmp_path/'fact.db')
    try:
        assert h.ingest().disposition == 'admitted'
        h.prepare_withdrawal(); result = h.withdraw()
        projection = dict(source.validate_full_withdrawal_fact(result.fact))
        assert projection['state'] == 'suspended'
        assert projection['ordinary_access'] is False
        assert projection['withdrawal_attribution'] == 'current_subscription_period'
        assert not source.allows_paid_request(h.authority, h.repo, user_id=1,
            now=h.withdrawal_time)
        h.authority.revoke()
        with pytest.raises(source.InitialIngressError):
            source.validate_full_withdrawal_fact(result.fact)
    finally:
        h.repo.close()


def test_withdrawal_head_invalidates_all_older_paid_fact_readers(tmp_path):
    h = WithdrawalHarness(tmp_path/'old-paid-reader.db')
    try:
        paid = h.ingest()
        h.prepare_withdrawal()
        admitted = exact.admit_initial(paid.fact, authority=h.authority,
            owner='synthetic-owner', now=h.withdrawal_time - timedelta(seconds=1))
        assert h.withdraw().disposition == 'admitted'
        with pytest.raises(source.InitialIngressError):
            source.current_fact(h.authority, h.repo, user_id=1,
                                now=h.withdrawal_time)
        with pytest.raises(ValueError):
            exact.admit_initial(paid.fact, authority=h.authority,
                owner='synthetic-owner', now=h.withdrawal_time)
        with pytest.raises(ValueError):
            exact._projection(admitted)
    finally:
        h.repo.close()
