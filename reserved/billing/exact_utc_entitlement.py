"""Distinct live exact-UTC two-period protocol; no legacy date coercion."""
from datetime import datetime, timezone
import threading
import weakref

VERSION = 'reserved-exact-utc-paid-lineage/2'


def utc(value):
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ValueError('exact UTC instant required')
    return value


def _protocol():
    lock = threading.RLock()
    facts = weakref.WeakKeyDictionary()
    admissions = weakref.WeakKeyDictionary()
    capability = object()

    class Fact:
        __slots__ = ('__weakref__',)
        def __new__(cls):
            raise TypeError('live issuance only')
        def __copy__(self):
            raise TypeError('not copyable')
        def __deepcopy__(self, memo):
            raise TypeError('not copyable')
        def __reduce__(self):
            raise TypeError('not serialisable')

    class Admitted(Fact):
        pass

    def issue(token, authority, repository, revision, head, receipt):
        if token is not capability:
            raise ValueError('invalid issuer')
        # Only the concrete postcommit composition calls this private seam.
        service_start = utc(datetime.fromisoformat(
            receipt.get('service_start', receipt['evidence']['service_start'])))
        start = utc(datetime.fromisoformat(receipt['access_start']))
        end = utc(datetime.fromisoformat(receipt['service_end']))
        sequence = receipt['sequence']
        if (start < service_start or start >= end or sequence not in (1, 2)
                or (sequence == 1 and any(receipt.get(name) is not None for name in
                    ('predecessor', 'predecessor_receipt_id', 'predecessor_fact_id', 'predecessor_head')))
                or (sequence == 2 and (receipt.get('predecessor') != 1
                    or not all(type(receipt.get(name)) is str for name in
                               ('predecessor_receipt_id', 'predecessor_fact_id', 'predecessor_head'))))):
            raise ValueError('invalid paid period')
        value = object.__new__(Fact)
        with lock:
            from .local_billing_provenance_repository import canonical
            facts[value] = (authority, revision, head, receipt['owner'], start, end,
                            repository, canonical(receipt), sequence)
        return value

    def admit(fact, *, authority, owner, now):
        utc(now)
        with lock:
            if type(fact) is not Fact or fact not in facts:
                raise ValueError('not a live fact')
            state = facts[fact]
            from .local_stripe_initial_payment import _validate_live_fact
            _validate_live_fact(state, now=now)
            if state[0] is not authority or state[3] != owner or not state[4] <= now < state[5]:
                raise ValueError('not current scoped access')
            value = object.__new__(Admitted)
            admissions[value] = state
            return value

    def projection(value):
        with lock:
            if type(value) is not Admitted or value not in admissions:
                raise ValueError('not admitted')
            state = admissions[value]
            from .local_stripe_initial_payment import _validate_live_fact
            _validate_live_fact(state)
            return state[:6]

    def initial_payment_presentation_facts(value, *, now):
        """Project safe initial-payment facts after exact live reauthentication."""
        utc(now)
        with lock:
            if type(value) is not Fact or value not in facts:
                raise ValueError('not a live initial-payment fact')
            state = facts[value]
        from .local_stripe_initial_payment import _initial_payment_presentation_facts
        return _initial_payment_presentation_facts(state, now=now)

    return Fact, Admitted, issue, admit, projection, initial_payment_presentation_facts, capability


(
    Fact, Admitted, _issue, admit_initial, _projection,
    initial_payment_presentation_facts, _ISSUER,
) = _protocol()
