"""Injected synthetic Basil initial and one-successor paid reconciliation.

Not a webhook, provider client, credential store, or production bootstrap. The
only supported lifecycle is initial payment followed by one ordinary renewal.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
import calendar
import hashlib
import json
import re
import threading
import uuid

from reserved.auth import is_production_environment
from .stripe_signature_verifier import verify_stripe_signature
from .local_billing_provenance_repository import ProvenanceRepository, CommitOutcomeError, canonical, identity
from . import exact_utc_entitlement as exact

API_VERSION = '2025-03-31.basil'
ORIGIN = 'https://api.stripe.com'
_LOCK = threading.RLock()
# A live-process consumed-scope tombstone is deliberately not resettable.
# It is not a second durable witness and is not real process-restart recovery.
_SCOPES = {}
_AUTHORITIES = {}
_ID = re.compile(r'[a-z][a-z0-9]*_[A-Za-z0-9]{1,100}\Z')
_PLANS = {'monthly': (2900, 'month', 1), 'six_month': (15600, 'month', 6),
          'yearly': (28800, 'year', 1)}


class InitialIngressError(ValueError):
    pass


@dataclass(frozen=True)
class SourceRequest:
    origin: str
    path: str
    query: tuple
    account: str
    endpoint: str
    api_version: str
    livemode: bool
    context_identity: str


@dataclass(frozen=True)
class SourceResponse:
    request: SourceRequest
    body: bytes


@dataclass(frozen=True)
class BindingSnapshot:
    instance: str
    epoch: str
    revision: int
    active: bool
    consumed: bool
    accepted: tuple | None


@dataclass(frozen=True)
class IngressResult:
    disposition: str
    committed: bool | None
    fact: object = None


def _identifier(value, prefix=None):
    if type(value) is not str or not _ID.fullmatch(value) or (prefix and not value.startswith(prefix + '_')):
        raise InitialIngressError('invalid source identifier')
    return value


def _ref(value):
    if type(value) is not str or not 1 <= len(value) <= 160 or any(ord(c) < 33 or ord(c) > 126 for c in value):
        raise InitialIngressError('invalid independent reference')
    return value


def _integer(value):
    if type(value) is not int or not 0 <= value <= 10**12:
        raise InitialIngressError('invalid source number')
    return value


def _effective_hmac_key(key):
    """RFC HMAC-SHA256 key reduction and zero padding to its 64-byte block."""
    reduced = hashlib.sha256(key).digest() if len(key) > 64 else key
    return reduced.ljust(64, b'\x00')


def _timestamp(value):
    return datetime.fromtimestamp(_integer(value), timezone.utc)


def _approved_period_end(start, plan):
    """Apply the fixed catalogue cadence using deterministic UTC calendars.

    The predecessor day is retained when it exists in the target month and is
    otherwise clamped to that month's final day (including leap February).
    This is Reserved's bounded validation rule, not a general Stripe semantic.
    """
    exact.utc(start)
    if type(plan) is not str or plan not in _PLANS:
        raise InitialIngressError('unsupported independent plan')
    _, interval, count = _PLANS[plan]
    months = count if interval == 'month' else count * 12
    ordinal = start.year * 12 + start.month - 1 + months
    year, zero_month = divmod(ordinal, 12)
    month = zero_month + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)


def _parse(raw):
    if type(raw) is not bytes or len(raw) > 1_048_576:
        raise InitialIngressError('invalid bounded source')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InitialIngressError('duplicate JSON key')
            result[key] = value
        return result
    def nonfinite(value):
        raise InitialIngressError('nonfinite source')
    result = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    def bound(value, depth=0):
        if depth > 16:
            raise InitialIngressError('source nesting bound')
        if type(value) is dict:
            if len(value) > 128:
                raise InitialIngressError('source field bound')
            for key, child in value.items():
                if len(key) > 160:
                    raise InitialIngressError('source key bound')
                bound(child, depth + 1)
        elif type(value) is list:
            if len(value) > 100:
                raise InitialIngressError('source enumeration bound')
            for child in value:
                bound(child, depth + 1)
        elif type(value) is str and len(value) > 8192:
            raise InitialIngressError('source string bound')
        elif type(value) not in (str, int, bool, type(None)):
            raise InitialIngressError('unsupported JSON value')
    bound(result)
    if type(result) is not dict:
        raise InitialIngressError('source object required')
    return result


class SyntheticInitialAuthority:
    """Independent process-local ownership/currentness, explicitly synthetic.

    Pristine eligibility is an assertion of the trusted test composition, not
    inferred from an empty table. Binding immediately fixes a fresh store. A
    replacement store/epoch cannot reset a consumed scope within this process.
    Private implementation state is not a sandbox against hostile Python code.
    """
    __slots__ = ('__weakref__',)

    def __init__(self, *, repository, user_id, owner, billing_account, subscription,
                 customer, item, price, plan, endpoint, account, signing_keys,
                 receipt_key, receipt_key_id, signing_key_ids, retrieve,
                 pristine_initial_eligible):
        if is_production_environment() or type(repository) is not ProvenanceRepository:
            raise InitialIngressError('local explicit store required')
        if type(user_id) is not int or user_id <= 0 or pristine_initial_eligible is not True:
            raise InitialIngressError('independent pristine eligibility required')
        owner, billing_account, endpoint, account = map(_ref, (owner, billing_account, endpoint, account))
        for value, prefix in ((subscription, 'sub'), (customer, 'cus'), (item, 'si'), (price, 'price')):
            _identifier(value, prefix)
        if type(plan) is not str or plan not in _PLANS or not callable(retrieve):
            raise InitialIngressError('unsupported independent plan or retrieval')
        if (type(signing_keys) is not tuple or not 1 <= len(signing_keys) <= 3
                or any(type(k) is not bytes or not 32 <= len(k) <= 512 for k in signing_keys)
                or type(receipt_key) is not bytes or not 32 <= len(receipt_key) <= 512
                or receipt_key in signing_keys or len(set(signing_keys)) != len(signing_keys)
                or type(signing_key_ids) is not tuple or len(signing_key_ids) != len(signing_keys)
                or len(set(signing_key_ids)) != len(signing_key_ids)
                or receipt_key_id in signing_key_ids):
            raise InitialIngressError('distinct independent key domains required')
        for key_id in (*signing_key_ids, receipt_key_id):
            _ref(key_id)
        effective = [_effective_hmac_key(key) for key in (*signing_keys, receipt_key)]
        if len(set(effective)) != len(effective):
            raise InitialIngressError('equivalent HMAC key domains')
        scope = owner, billing_account, subscription
        with _LOCK:
            source_scope = account, subscription
            if source_scope in _SCOPES or not repository.empty():
                raise InitialIngressError('scope or store is not pristine')
            instance, epoch = uuid.uuid4().hex, uuid.uuid4().hex
            snapshot = BindingSnapshot(instance, epoch, 1, True, False, None)
            state = dict(publication=(snapshot, None), store=repository.store_id, physical=repository.physical_identity, user=user_id, scope=scope,
                         customer=customer, item=item, price=price, plan=plan, endpoint=endpoint,
                         account=account, signing_keys=signing_keys, receipt_key=receipt_key,
                         receipt_key_id=receipt_key_id, signing_key_ids=signing_key_ids,
                         retrieve=retrieve, retrieval_code=getattr(retrieve, '__code__', None),
                         last_clock=None, commit_seen=set())
            _AUTHORITIES[self] = state
            _SCOPES[source_scope] = instance

    def snapshot(self):
        with _LOCK:
            return _state(self)['publication'][0]

    def revoke(self):
        with _LOCK:
            state = _state(self)
            snap, reservation = state['publication']
            state['publication'] = (
                replace(snap, revision=snap.revision + 1, active=False, consumed=True),
                reservation,
            )

    def lose(self):
        """Simulate loss of the independent authority; scope tombstone remains."""
        with _LOCK:
            _AUTHORITIES.pop(self, None)


def _state(authority):
    if type(authority) is not SyntheticInitialAuthority or authority not in _AUTHORITIES:
        raise InitialIngressError('independent authority unavailable')
    return _AUTHORITIES[authority]


def _check(authority, snapshot, now=None):
    with _LOCK:
        state = _state(authority)
        if (state['publication'][0] != snapshot or not snapshot.active
                or getattr(state['retrieve'], '__code__', None) is not state['retrieval_code']):
            raise InitialIngressError('changed authority')
        if now is not None:
            exact.utc(now)
            if state['last_clock'] is not None and now < state['last_clock']:
                raise InitialIngressError('clock rollback')
            state['last_clock'] = now
        return state


def _fetch(state, path, query=()):
    request = SourceRequest(ORIGIN, path, query, state['account'], state['endpoint'],
                            API_VERSION, False, state['publication'][0].instance)
    response = state['retrieve'](request)
    if type(response) is not SourceResponse or response.request is not request:
        raise InitialIngressError('unbound retrieval')
    return _parse(response.body)


def _object(state, path, source_id, kind):
    obj = _fetch(state, path)
    if obj.get('id') != source_id or obj.get('object') != kind or obj.get('livemode') is not False:
        raise InitialIngressError('mismatched source object')
    return obj


def _single_list(value):
    if (type(value) is not dict or value.get('object') != 'list' or value.get('has_more') is not False
            or type(value.get('data')) is not list or len(value['data']) != 1
            or ('total_count' in value and (type(value['total_count']) is not int or value['total_count'] != 1))):
        raise InitialIngressError('unsupported or incomplete enumeration')
    if type(value['data'][0]) is not dict:
        raise InitialIngressError('invalid list object')
    return value['data'][0]


def _reconcile(state, invoice_id, billing_reason):
    invoice = _object(state, '/v1/invoices/' + invoice_id, invoice_id, 'invoice')
    scope = state['scope']
    amount, interval, count = _PLANS[state['plan']]
    if (invoice['customer'] != state['customer'] or invoice['status'] != 'paid'
            or invoice['billing_reason'] != billing_reason or invoice['currency'] != 'gbp'
            or invoice['collection_method'] != 'charge_automatically'
            or invoice['parent']['type'] != 'subscription_details'
            or invoice['parent']['subscription_details']['subscription'] != scope[2]):
        raise InitialIngressError('unsupported paid invoice')
    for key in ('amount_paid', 'amount_due', 'total'):
        if _integer(invoice[key]) != amount:
            raise InitialIngressError('unreconciled payment amount')
    for key in ('amount_remaining', 'amount_overpaid', 'starting_balance',
                'pre_payment_credit_notes_amount', 'post_payment_credit_notes_amount'):
        if _integer(invoice[key]) != 0:
            raise InitialIngressError('unsupported payment complication')
    if invoice['discounts'] != [] or invoice['total_discount_amounts'] != []:
        raise InitialIngressError('discount implementation remains open')
    line = _single_list(_fetch(state, '/v1/invoices/' + invoice_id + '/lines', (('limit', '100'),)))
    if (line['object'] != 'line_item' or line['livemode'] is not False or line['currency'] != 'gbp'
            or _integer(line['quantity']) != 1 or _integer(line['amount']) != amount
            or line['parent']['type'] != 'subscription_item_details'
            or line['parent']['subscription_item_details']['subscription_item'] != state['item']
            or line['parent']['subscription_item_details']['subscription'] != scope[2]
            or line['parent']['subscription_item_details']['proration'] is not False
            or line['pricing']['type'] != 'price_details'
            or line['pricing']['price_details']['price'] != state['price']
            or line['discounts'] != [] or line['discount_amounts'] != []):
        raise InitialIngressError('unsupported line')
    _identifier(line['id'], 'il')
    if line.get('invoice', invoice_id) != invoice_id:
        raise InitialIngressError('line invoice mismatch')
    start, end = _timestamp(line['period']['start']), _timestamp(line['period']['end'])
    if not start < end:
        raise InitialIngressError('invalid purchased period')
    subscription = _object(state, '/v1/subscriptions/' + scope[2], scope[2], 'subscription')
    item = _single_list(subscription['items'])
    if (subscription['customer'] != state['customer'] or subscription['status'] != 'active'
            or subscription['latest_invoice'] != invoice_id or subscription['discounts'] != []
            or subscription['collection_method'] != 'charge_automatically'
            or item['id'] != state['item'] or item['object'] != 'subscription_item'
            or item['subscription'] != scope[2] or _integer(item['quantity']) != 1
            or item['price']['id'] != state['price']
            or _timestamp(item['current_period_start']) != start or _timestamp(item['current_period_end']) != end):
        raise InitialIngressError('subscription period mismatch')
    price = _object(state, '/v1/prices/' + state['price'], state['price'], 'price')
    if (price['currency'] != 'gbp' or _integer(price['unit_amount']) != amount
            or price['type'] != 'recurring' or price['billing_scheme'] != 'per_unit'
            or price['recurring']['interval'] != interval or _integer(price['recurring']['interval_count']) != count
            or price['recurring']['usage_type'] != 'licensed'):
        raise InitialIngressError('unapproved price')
    payment = _single_list(_fetch(state, '/v1/invoice_payments', (('invoice', invoice_id), ('limit', '100'))))
    if (payment['object'] != 'invoice_payment' or payment['livemode'] is not False
            or payment['invoice'] != invoice_id or payment['status'] != 'paid'
            or payment['currency'] != 'gbp' or _integer(payment['amount_paid']) != amount
            or _integer(payment['amount_requested']) != amount or payment['payment']['type'] != 'payment_intent'):
        raise InitialIngressError('unallocated payment')
    _identifier(payment['id'], 'inpay')
    pi_id = _identifier(payment['payment']['payment_intent'], 'pi')
    intent = _object(state, '/v1/payment_intents/' + pi_id, pi_id, 'payment_intent')
    if (intent['status'] != 'succeeded' or intent['customer'] != state['customer']
            or intent['currency'] != 'gbp' or _integer(intent['amount_received']) != amount
            or _integer(intent['amount']) != amount):
        raise InitialIngressError('unverified payment')
    charge_id = _identifier(intent['latest_charge'], 'ch')
    charge = _object(state, '/v1/charges/' + charge_id, charge_id, 'charge')
    if (charge['payment_intent'] != pi_id or charge['customer'] != state['customer']
            or charge['currency'] != 'gbp' or charge['paid'] is not True or charge['captured'] is not True
            or charge['status'] != 'succeeded' or charge['payment_method_details']['type'] != 'card'
            or _integer(charge['amount_captured']) != amount or _integer(charge['amount']) != amount
            or _integer(charge['amount_refunded']) != 0 or charge['refunded'] is not False
            or charge['disputed'] is not False):
        raise InitialIngressError('capture or withdrawal complication')
    invoice_paid = _timestamp(invoice['status_transitions']['paid_at'])
    payment_paid = _timestamp(payment['status_transitions']['paid_at'])
    observed_times = [_timestamp(obj['created']) for obj in (invoice, payment, intent, charge)]
    if observed_times[0] > invoice_paid or any(value > payment_paid for value in observed_times[1:]):
        raise InitialIngressError('contradictory source payment times')
    evidence = dict(invoice=invoice_id, line=line['id'], payment=payment['id'], intent=pi_id,
                    charge=charge_id, amount=amount, currency='gbp', service_start=start.isoformat(),
                    service_end=end.isoformat(), plan=state['plan'], price=state['price'], item=state['item'],
                    invoice_paid_at=invoice_paid.isoformat(), payment_paid_at=payment_paid.isoformat())
    # Full bounded observations compared only transiently, never persisted.
    return evidence, canonical((invoice, line, subscription, price, payment, intent, charge))


def _lineage(authority, repository, snapshot):
    state = _check(authority, snapshot)
    if (type(repository) is not ProvenanceRepository or repository.store_id != state['store']
            or repository.physical_identity != state['physical']):
        raise InitialIngressError('wrong store')
    lineage = repository.read_lineage(snapshot.instance, state['receipt_key'])
    for receipt, _ in lineage:
        if (receipt['epoch'] != snapshot.epoch or receipt['owner'] != state['scope'][0]
                or receipt['scope'] != list(state['scope'])
                or receipt['receipt_key_id'] != state['receipt_key_id']):
            raise InitialIngressError('receipt binding mismatch')
    return lineage


def _accepted_lineage(authority, repository, snapshot):
    lineage = _lineage(authority, repository, snapshot)
    if not lineage or snapshot.accepted is None:
        raise InitialIngressError('missing accepted lineage')
    receipt, head = lineage[-1]
    if snapshot.accepted != (repository.store_id, receipt['receipt_id'], receipt['fact_id'], head):
        raise InitialIngressError('obsolete authentic receipt')
    return lineage


def current_fact(authority, repository, *, user_id, now):
    """Issue the effective period bound to the current lineage head and revision."""
    if is_production_environment():
        raise InitialIngressError('local only')
    snapshot = authority.snapshot()
    state = _check(authority, snapshot, now)
    if type(user_id) is not int or user_id != state['user']:
        raise InitialIngressError('current membership unavailable')
    lineage = _accepted_lineage(authority, repository, snapshot)
    selected = None
    for unit in lineage:
        receipt = unit[0]
        if (datetime.fromisoformat(receipt['access_start']) <= now
                < datetime.fromisoformat(receipt['service_end'])):
            selected = receipt
    if selected is None:
        raise InitialIngressError('no effective verified period')
    current_head = lineage[-1][1]
    _check(authority, snapshot)
    return exact._issue(exact._ISSUER, authority, repository, snapshot.revision,
                        current_head, selected)


def _validate_live_fact(fact_state, now=None):
    authority, revision, current_head, owner, start, end, repository, material, sequence = fact_state
    snapshot = authority.snapshot()
    state = _check(authority, snapshot, now)
    lineage = _accepted_lineage(authority, repository, snapshot)
    selected = next((receipt for receipt, _ in lineage if receipt['sequence'] == sequence), None)
    if (snapshot.revision != revision or state['scope'][0] != owner
            or lineage[-1][1] != current_head or selected is None
            or canonical(selected) != material
            or start != datetime.fromisoformat(selected['access_start'])
            or end != datetime.fromisoformat(selected['service_end'])):
        raise InitialIngressError('stale live fact')
    _check(authority, snapshot)


def allows_paid_request(authority, repository, *, user_id, now):
    """Concrete exact admission then final independent currentness linearization."""
    try:
        fact = current_fact(authority, repository, user_id=user_id, now=now)
        snapshot = authority.snapshot()
        state = _check(authority, snapshot)
        admitted = exact.admit_initial(fact, authority=authority, owner=state['scope'][0], now=now)
        _, revision, head, _, _, _ = exact._projection(admitted)
        lineage = _accepted_lineage(authority, repository, snapshot)
        if revision != snapshot.revision or lineage[-1][1] != head:
            return False
        _check(authority, snapshot, now)  # access-decision linearization point
        return not is_production_environment()
    except Exception:
        return False


def _ingest_paid_invoice(authority, repository, raw_body, signature_header, *, clock,
                         billing_reason, sequence):
    """The sole signed ingress and paid-invoice reconciler for both public entries."""
    def _publish(snapshot, receipt, head):
        with _LOCK:
            state = _check(authority, snapshot)
            current, reservation = state['publication']
            accepted = (repository.store_id, receipt['receipt_id'], receipt['fact_id'], head)
            if (current != snapshot or reservation is None or reservation['sequence'] != sequence
                    or reservation['material'] != canonical(receipt)
                    or reservation['revision'] != snapshot.revision
                    or reservation['predecessor'] != snapshot.accepted):
                raise InitialIngressError('changed reservation')
            published = replace(snapshot, revision=snapshot.revision + 1,
                                consumed=True, accepted=accepted)
            state['publication'] = (published, None)
            return published

    committed = False
    try:
        if is_production_environment() or billing_reason not in ('subscription_create', 'subscription_cycle'):
            raise InitialIngressError('local bounded lifecycle only')
        snapshot = authority.snapshot()
        received = exact.utc(clock())
        state = _check(authority, snapshot, received)
        if (type(repository) is not ProvenanceRepository or repository.store_id != state['store']
                or repository.physical_identity != state['physical']):
            raise InitialIngressError('wrong store')
        # Renewal independently repeats signature verification through this
        # single dependency call site before reserving a successor.
        for _ in range(2 if sequence == 2 else 1):
            if not verify_stripe_signature(raw_body, signature_header, state['signing_keys'], now=int(received.timestamp())):
                raise InitialIngressError('signature refusal')
        event = _parse(raw_body)
        if (event['object'] != 'event' or event['type'] != 'invoice.paid' or event['livemode'] is not False
                or event['api_version'] != API_VERSION or event.get('account') is not None):
            raise InitialIngressError('unsupported event')
        _identifier(event['id'], 'evt')
        source_time = _timestamp(event['created'])
        if source_time > received:
            raise InitialIngressError('future source event')
        invoice_id = _identifier(event['data']['object']['id'], 'in')
        if event['data']['object']['object'] != 'invoice':
            raise InitialIngressError('wrong event object')
        event_invoice = event['data']['object']
        if (event_invoice['customer'] != state['customer'] or event_invoice['livemode'] is not False
                or event_invoice['status'] != 'paid' or event_invoice['billing_reason'] != billing_reason
                or event_invoice['parent']['type'] != 'subscription_details'
                or event_invoice['parent']['subscription_details']['subscription'] != state['scope'][2]):
            raise InitialIngressError('event scope mismatch')
        evidence, observations = _reconcile(state, invoice_id, billing_reason)
        check_evidence, check_observations = _reconcile(state, invoice_id, billing_reason)
        if (evidence, observations) != (check_evidence, check_observations):
            raise InitialIngressError('changed source observations')
        completed = exact.utc(clock())
        _check(authority, snapshot, completed)
        if any(datetime.fromisoformat(evidence[key]) > source_time
               for key in ('invoice_paid_at', 'payment_paid_at')):
            raise InitialIngressError('payment occurs after signed success observation')
        service_start = datetime.fromisoformat(evidence['service_start'])
        service_end = datetime.fromisoformat(evidence['service_end'])
        access_start = max(service_start, completed)
        if access_start >= service_end:
            raise InitialIngressError('expired purchased period')
        raw_digest = hashlib.sha256(raw_body).hexdigest()
        lineage = _lineage(authority, repository, snapshot)
        predecessor = None
        if sequence == 1:
            if snapshot.accepted is not None and (len(lineage) != 1 or state['publication'][1] is not None):
                raise InitialIngressError('consumed initial scope')
        elif sequence == 2:
            if snapshot.accepted is None or not lineage:
                raise InitialIngressError('accepted predecessor required')
            if len(lineage) == 1:
                predecessor = lineage[0]
                prior_receipt, prior_head = predecessor
                if (snapshot.accepted != (repository.store_id, prior_receipt['receipt_id'],
                                          prior_receipt['fact_id'], prior_head)
                        or service_start != datetime.fromisoformat(prior_receipt['service_end'])
                        or service_end != _approved_period_end(service_start, state['plan'])):
                    raise InitialIngressError('wrong or noncontiguous predecessor')
            elif len(lineage) == 2:
                predecessor = lineage[0]
                if service_end != _approved_period_end(service_start, state['plan']):
                    raise InitialIngressError('cadence-mismatched successor')
            else:
                raise InitialIngressError('sequence three remains unsupported')
        else:
            raise InitialIngressError('unsupported sequence')

        if len(lineage) >= sequence:
            committed = True
            receipt, head = lineage[sequence - 1]
            if (receipt['raw_digest'] != raw_digest or receipt['event_id'] != event['id']
                    or receipt['evidence'] != evidence or receipt['epoch'] != snapshot.epoch):
                repository.record_conflict(snapshot.instance, event_id=event['id'], raw_digest=raw_digest,
                    object_key=invoice_id + ':invoice.paid', key=state['receipt_key'])
                return IngressResult('reconciliation_required', True)
            if snapshot.accepted == (repository.store_id, receipt['receipt_id'], receipt['fact_id'], head):
                fact = exact._issue(exact._ISSUER, authority, repository,
                                    snapshot.revision, head, receipt)
                return IngressResult('admitted', True, fact)
            _, reservation = state['publication']
            if (reservation is None or reservation['material'] != canonical(receipt)
                    or reservation['predecessor'] != snapshot.accepted):
                raise InitialIngressError('durable successor lacks exact reservation')
            snapshot = state['publication'][0]
        else:
            if sequence in state['commit_seen']:
                raise InitialIngressError('consumed uncertain attempt')
            common = dict(store=repository.store_id, binding=snapshot.instance, epoch=snapshot.epoch,
                binding_revision=snapshot.revision, owner=state['scope'][0], scope=list(state['scope']),
                endpoint=state['endpoint'], account=state['account'], api_version=API_VERSION,
                livemode=False, receipt_key_id=state['receipt_key_id'],
                signing_key_ids=list(state['signing_key_ids']), event_id=event['id'],
                object_key=invoice_id + ':invoice.paid', raw_digest=raw_digest,
                received_at=received.isoformat(), source_created_at=source_time.isoformat(),
                verification_completed_at=completed.isoformat(), access_start=access_start.isoformat(),
                service_end=evidence['service_end'], evidence=evidence)
            if sequence == 1:
                # Preserve the accepted v1 receipt/fact identity and field meaning;
                # only its enclosing newly-created store schema has evolved.
                receipt = dict(version='reserved-initial-receipt/1', **common,
                               sequence=1, predecessor=None,
                               disposition='verified_initial_payment')
                receipt['fact_id'] = identity('exact-initial-fact/1', receipt)
                receipt['receipt_id'] = identity('initial-receipt/1', receipt)
            else:
                receipt = dict(version='reserved-successful-renewal-receipt/1', **common,
                    service_start=evidence['service_start'], sequence=2,
                    predecessor=predecessor[0]['sequence'],
                    predecessor_receipt_id=predecessor[0]['receipt_id'],
                    predecessor_fact_id=predecessor[0]['fact_id'], predecessor_head=predecessor[1],
                    disposition='verified_successful_renewal')
                receipt['fact_id'] = identity('exact-paid-period-fact/2', receipt)
                receipt['receipt_id'] = identity('paid-lineage-receipt/2', receipt)
            with _LOCK:
                _check(authority, snapshot)
                current, reservation = state['publication']
                if reservation is None:
                    reserved = replace(snapshot, revision=snapshot.revision + 1, consumed=True)
                    reservation = dict(sequence=sequence, material=canonical(receipt),
                                       predecessor=snapshot.accepted, revision=reserved.revision)
                    state['publication'] = (reserved, reservation)
                    snapshot = reserved
                else:
                    receipt = json.loads(reservation['material'])
                    snapshot = current
                    if (reservation['sequence'] != sequence or reservation['predecessor'] != snapshot.accepted
                            or receipt['raw_digest'] != raw_digest or receipt['event_id'] != event['id']
                            or receipt['evidence'] != evidence):
                        raise InitialIngressError('different reserved proposal')
            try:
                if sequence == 1:
                    receipt, head = repository.commit_initial(receipt, state['receipt_key'])
                else:
                    receipt, head = repository.commit_successor(receipt, predecessor, state['receipt_key'])
                committed = True
            except CommitOutcomeError as error:
                committed = error.committed
                raise
            except Exception:
                committed = None
                try:
                    durable = repository.read_sequence(snapshot.instance, sequence, state['receipt_key'])
                    if durable is not None:
                        receipt, head = durable
                        committed = True
                except Exception:
                    pass
                raise
            finally:
                with _LOCK:
                    if committed is not False:
                        state['commit_seen'].add(sequence)
        if repository.read_sequence(snapshot.instance, sequence, state['receipt_key']) != (receipt, head):
            raise InitialIngressError('changed committed unit')
        published = _publish(snapshot, receipt, head)
        _check(authority, published)
        if _accepted_lineage(authority, repository, published)[-1] != (receipt, head):
            raise InitialIngressError('changed publication')
        _check(authority, published)
        fact = exact._issue(exact._ISSUER, authority, repository,
                            published.revision, head, receipt)
        return IngressResult('admitted', True, fact)
    except Exception:
        disposition = ('commit_outcome_unknown' if committed is None else
                       ('committed_but_unadmitted' if committed else 'refused'))
        return IngressResult(disposition, committed)


def ingest_initial_payment(authority, repository, raw_body, signature_header, *, clock):
    return _ingest_paid_invoice(authority, repository, raw_body, signature_header, clock=clock,
                                billing_reason='subscription_create', sequence=1)


def ingest_successful_renewal(authority, repository, raw_body, signature_header, *, clock):
    return _ingest_paid_invoice(authority, repository, raw_body, signature_header, clock=clock,
                                billing_reason='subscription_cycle', sequence=2)
