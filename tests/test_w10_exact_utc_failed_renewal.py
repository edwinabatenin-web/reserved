"""Live failed-renewal fact protocol and exact UTC boundary evidence."""
from datetime import datetime, timedelta
import sqlite3

import pytest

from reserved.billing import exact_utc_entitlement as paid_v1
from reserved.billing import local_stripe_initial_payment as source
from tests.test_w10_stripe_failed_renewal import FailedRenewalHarness
from tests.test_w10_stripe_initial_payment_ingress import RECEIPT_KEY


@pytest.fixture
def fact(tmp_path):
    h = FailedRenewalHarness(tmp_path/'fact.db')
    assert h.ingest().disposition == 'admitted'
    h.prepare_failure()
    result = h.fail()
    yield h, result.fact
    h.repo.close()


def test_live_fact_is_exact_v2_owner_bound_projection(fact):
    h, value = fact
    validated = source.validate_failed_renewal_fact(value)
    projected = source.project_failed_renewal_fact(value)
    assert validated == projected
    fields = dict(validated)
    assert fields['protocol_version'] == source.RECOVERY_FACT_PROTOCOL_VERSION
    assert fields['authenticated'] is True
    assert fields['billing_fact_authority'] is True
    assert fields['provider_observation_direct_authority'] is False
    assert fields['owner_id'] == 'synthetic-owner'
    assert fields['state'] == 'payment_recovery'
    assert fields['recovery_deadline_exclusive_at_utc'] == (
        fields['transition_effective_at_utc'] + timedelta(days=7))
    assert fields['transition_effective_at_utc'].time() != datetime.min.time()


def test_old_paid_fact_protocol_refuses_new_recovery_fact(fact):
    h, value = fact
    with pytest.raises(ValueError):
        paid_v1.admit_initial(value, authority=h.authority,
                              owner='synthetic-owner', now=h.failure_time)


def test_primitive_projection_is_not_live_authority(fact):
    _, value = fact
    projection = source.validate_failed_renewal_fact(value)
    with pytest.raises(source.InitialIngressError):
        source.validate_failed_renewal_fact(projection)


def test_fact_stales_on_authority_revision(fact):
    h, value = fact
    h.authority.revoke()
    with pytest.raises(source.InitialIngressError):
        source.validate_failed_renewal_fact(value)


@pytest.mark.parametrize('column', ['body', 'mac'])
def test_fact_reauthenticates_durable_control(fact, column):
    h, value = fact
    with sqlite3.connect(h.repo.path) as conn:
        if column == 'body':
            conn.execute("UPDATE dispositions SET body=body || ' '")
        else:
            conn.execute("UPDATE dispositions SET mac='forged'")
    with pytest.raises(ValueError):
        source.validate_failed_renewal_fact(value)


def test_fact_binds_exact_original_verification_and_head_across_reopen(fact):
    from reserved.billing.local_billing_provenance_repository import ProvenanceRepository
    h, value = fact
    before = source.failed_renewal_fact_details(value)
    path = h.repo.path
    h.repo.close()
    h.repo = ProvenanceRepository(path)
    replay = h.fail(now=datetime.fromisoformat(
        before['recovery_deadline_exclusive_at_utc']))
    assert replay.fact is value
    assert source.failed_renewal_fact_details(value) == before
    assert h.repo.read_lifecycle(h.authority.snapshot().instance, RECEIPT_KEY)[2] == (
        before['lifecycle_head'])
