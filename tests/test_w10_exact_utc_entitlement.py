"""Opaque exact-instant fact/admission and concrete independent currentness."""
import copy
from datetime import timedelta
import sys
import threading

import pytest
from reserved.billing import exact_utc_entitlement as exact
from reserved.billing import local_stripe_initial_payment as source
from reserved.billing.local_billing_provenance_repository import ProvenanceRepository
from tests.test_w10_stripe_initial_payment_ingress import harness, Harness, NOW, START, ENDS, RECEIPT_KEY


def allow(h, now=NOW, uid=1):
    return source.allows_paid_request(h.authority, h.repo, user_id=uid, now=now)


@pytest.mark.parametrize('operation', [copy.copy, copy.deepcopy, lambda value: object.__new__(exact.Fact)])
def test_copied_or_forged_handle_denied(harness, operation):
    fact = harness.ingest().fact
    try:
        forged = operation(fact)
    except TypeError:
        return
    with pytest.raises(ValueError):
        exact.admit_initial(forged, authority=harness.authority, owner='synthetic-owner', now=NOW)


@pytest.mark.parametrize('field', ['access_start', 'service_end', 'verification_completed_at', 'sequence', 'scope'])
def test_private_issuer_cannot_relabel_accepted_receipt(harness, field):
    assert harness.ingest().fact is not None
    snapshot = harness.authority.snapshot()
    receipt, head = harness.repo.read(snapshot.instance, RECEIPT_KEY)
    if field == 'access_start':
        receipt[field] = START.isoformat()
    elif field == 'service_end':
        receipt[field] = (ENDS['monthly']+timedelta(days=365)).isoformat()
    elif field == 'verification_completed_at':
        receipt[field] = START.isoformat()
    elif field == 'sequence':
        receipt[field] = 2
    else:
        receipt[field] = ['forged', 'scope', 'subscription']
    try:
        fact = exact._issue(exact._ISSUER, harness.authority, harness.repo, snapshot.revision, head, receipt)
    except ValueError:
        return
    with pytest.raises(ValueError):
        exact.admit_initial(fact, authority=harness.authority, owner='synthetic-owner', now=NOW)


def test_delayed_verification_never_backdates_access(harness):
    times = iter((NOW, NOW+timedelta(seconds=20)))
    assert harness.ingest(clock=lambda: next(times)).disposition == 'admitted'
    receipt, _ = harness.repo.read(harness.authority.snapshot().instance, RECEIPT_KEY)
    assert receipt['access_start'] == (NOW+timedelta(seconds=20)).isoformat()
    assert not allow(harness, NOW)
    assert allow(harness, NOW+timedelta(seconds=20))


def test_future_service_does_not_grant_yet(harness):
    # Source period is genuinely future, not date-truncated to today's midnight.
    future = NOW + timedelta(hours=1)
    harness.data['/v1/invoices/in_Synthetic/lines']['data'][0]['period']['start'] = int(future.timestamp())
    harness.data['/v1/subscriptions/sub_Synthetic']['items']['data'][0]['current_period_start'] = int(future.timestamp())
    assert harness.ingest().disposition == 'admitted'
    assert not allow(harness)
    assert allow(harness, future)


def test_clock_rollback_during_source_verification_refuses(harness):
    times = iter((NOW, NOW-timedelta(microseconds=1)))
    assert harness.ingest(clock=lambda: next(times)).disposition == 'refused'
    assert harness.repo.empty()


def test_request_clock_rollback_does_not_revive_expired_state(harness):
    assert harness.ingest().fact is not None
    assert not allow(harness, ENDS['monthly'])
    assert not allow(harness, NOW)


def test_revocation_invalidates_already_issued_handles(harness):
    fact = harness.ingest().fact
    admitted = exact.admit_initial(fact, authority=harness.authority, owner='synthetic-owner', now=NOW)
    harness.authority.revoke()
    assert not allow(harness)
    with pytest.raises(ValueError):
        exact.admit_initial(fact, authority=harness.authority, owner='synthetic-owner', now=NOW)
    with pytest.raises(ValueError):
        exact._projection(admitted)
    assert harness.ingest().disposition == 'refused'


@pytest.mark.parametrize('revoked', [False, True])
def test_duplicate_binding_or_fresh_store_cannot_reset_scope(harness, tmp_path, revoked):
    assert harness.ingest().fact is not None
    if revoked:
        harness.authority.revoke()
    fresh = ProvenanceRepository(tmp_path/'fresh.db', create=True)
    try:
        for changes in ({}, {'owner': 'another-owner', 'billing_account': 'another-billing'}):
            with pytest.raises(source.InitialIngressError):
                source.SyntheticInitialAuthority(**{**harness.kwargs, 'repository': fresh, **changes})
        harness.authority.lose()
        with pytest.raises(source.InitialIngressError):
            source.SyntheticInitialAuthority(**{**harness.kwargs, 'repository': fresh})
    finally:
        fresh.close()


def test_pristine_assertion_and_key_domains_required(tmp_path):
    h = Harness(tmp_path/'base.db')
    other = ProvenanceRepository(tmp_path/'other.db', create=True)
    try:
        for changes in ({'pristine_initial_eligible': False}, {'receipt_key': h.kwargs['signing_keys'][0]},
                        {'receipt_key_id': h.kwargs['signing_key_ids'][0]}):
            with pytest.raises(source.InitialIngressError):
                source.SyntheticInitialAuthority(**{**h.kwargs, 'repository': other, 'account': 'other', **changes})
    finally:
        h.repo.close()
        other.close()


def test_request_time_revocation_during_admission_denies(harness):
    assert harness.ingest().fact is not None
    touched = []
    def trace(frame, event, arg):
        if event == 'call' and frame.f_code is exact.admit_initial.__code__:
            harness.authority.revoke()
            touched.append(True)
        return trace
    prior = sys.gettrace()
    try:
        sys.settrace(trace)
        assert not allow(harness)
    finally:
        sys.settrace(prior)
    assert touched == [True]


def test_concurrent_initial_claims_cannot_issue_different_heads(harness):
    barrier = threading.Barrier(2)
    outcomes = []
    def run():
        barrier.wait()
        outcomes.append(harness.ingest())
    threads = [threading.Thread(target=run) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert any(r.disposition == 'admitted' for r in outcomes)
    assert len(harness.authority.snapshot().accepted) == 4
    assert allow(harness)


def test_cross_user_never_infers_membership_from_receipt(harness):
    assert harness.ingest().fact is not None
    assert not allow(harness, uid=2)


@pytest.mark.parametrize('equivalence', ['trailing_zero', 'long_digest'])
@pytest.mark.parametrize('domain', ['receipt_signing', 'rotation'])
def test_hmac_effective_key_collisions_rejected(tmp_path, equivalence, domain):
    import hashlib
    import hmac
    import uuid
    h = Harness(tmp_path/'base.db')
    candidate = ProvenanceRepository(tmp_path/'candidate.db', create=True)
    first = b'synthetic-equivalence-key-00000000' if equivalence == 'trailing_zero' else b'synthetic-long-key-' * 6
    second = first + b'\x00' if equivalence == 'trailing_zero' else hashlib.sha256(first).digest()
    assert first != second
    # Independent library demonstration, not the product's key-normaliser.
    for payload in (b'synthetic webhook bytes', b'synthetic receipt bytes'):
        assert hmac.digest(first, payload, 'sha256') == hmac.digest(second, payload, 'sha256')
    overrides = dict(repository=candidate, account='synthetic-' + uuid.uuid4().hex)
    if domain == 'receipt_signing':
        overrides.update(signing_keys=(first,), receipt_key=second)
    else:
        overrides.update(signing_keys=(first, second), signing_key_ids=('rotation-one', 'rotation-two'))
    try:
        with pytest.raises(source.InitialIngressError):
            source.SyntheticInitialAuthority(**{**h.kwargs, **overrides})
        assert candidate.empty()
    finally:
        h.repo.close()
        candidate.close()


@pytest.mark.parametrize('long_keys', [False, True])
def test_genuinely_distinct_effective_keys_remain_supported(tmp_path, long_keys):
    import uuid
    h = Harness(tmp_path/'base.db')
    candidate = ProvenanceRepository(tmp_path/'candidate.db', create=True)
    keys = tuple((b'synthetic-distinct-key-' + bytes([65+i]) * (100 if long_keys else 12)) for i in range(3))
    try:
        authority = source.SyntheticInitialAuthority(**{**h.kwargs, 'repository': candidate,
            'account': 'synthetic-' + uuid.uuid4().hex, 'signing_keys': keys[:2],
            'signing_key_ids': ('rotation-one', 'rotation-two'), 'receipt_key': keys[2]})
        assert authority.snapshot().active is True and candidate.empty()
    finally:
        h.repo.close()
        candidate.close()
