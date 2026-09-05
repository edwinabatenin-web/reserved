"""Exact-UTC selection after a later-period restoration."""
from datetime import timedelta

import pytest

from reserved.billing import exact_utc_entitlement as exact
from reserved.billing import local_stripe_initial_payment as source
from tests.test_w10_stripe_later_period_restoration import RestorationHarness


def test_exact_fact_selects_only_new_period_and_old_fact_stays_stale(tmp_path):
    h = RestorationHarness(tmp_path/'exact.db')
    try:
        initial = h.ingest()
        assert initial.disposition == 'admitted'
        assert h.withdraw_initial().disposition == 'admitted'
        h.prepare_restoration(); assert h.restore().disposition == 'admitted'
        with pytest.raises(Exception):
            exact.admit_initial(initial.fact, authority=h.authority,
                                owner='synthetic-owner', now=h.initial_end)
        with pytest.raises(source.InitialIngressError):
            source.current_fact(h.authority, h.repo, user_id=1,
                                now=h.initial_end - timedelta(microseconds=1))
        fact = source.current_fact(h.authority, h.repo, user_id=1,
                                   now=h.initial_end)
        admitted = exact.admit_initial(fact, authority=h.authority,
                                       owner='synthetic-owner', now=h.initial_end)
        projection = exact._projection(admitted)
        assert projection[4] == h.initial_end and projection[5] > h.initial_end
    finally:
        h.repo.close()


def test_delayed_access_start_is_exact_and_half_open(tmp_path):
    h = RestorationHarness(tmp_path/'delayed.db')
    try:
        assert h.ingest().disposition == 'admitted'
        assert h.withdraw_initial().disposition == 'admitted'
        h.prepare_restoration()
        delayed = h.initial_end + timedelta(days=3)
        assert h.restore(now=delayed).disposition == 'admitted'
        assert not source.allows_paid_request(h.authority, h.repo, user_id=1,
            now=delayed - timedelta(microseconds=1))
        assert source.allows_paid_request(h.authority, h.repo, user_id=1,
            now=delayed)
    finally:
        h.repo.close()
