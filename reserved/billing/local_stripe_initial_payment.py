"""Injected synthetic Basil paid, failure, withdrawal and restoration reconciliation.

Not a webhook, provider client, credential store, or production bootstrap. The
Supported paid lineage remains initial payment plus one ordinary renewal. A
versioned lifecycle control can record either scheduled cancellation or the
first verified recurring-payment failure without creating a paid sequence three.
"""
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import calendar
import hashlib
import json
import os
import re
import threading
import uuid
import weakref

from reserved.auth import is_production_environment
from .stripe_signature_verifier import verify_stripe_signature
from .local_billing_provenance_repository import (
    ProvenanceRepository, CommitOutcomeError, canonical, identity, _control_head,
)
from . import exact_utc_entitlement as exact

API_VERSION = '2025-03-31.basil'
ORIGIN = 'https://api.stripe.com'
RECOVERY_FACT_PROTOCOL_VERSION = 'reserved-owner-bound-billing-recovery-fact/2.0'
RECOVERY_FACT_ADMISSION_STATUS = 'authoritative_owner_bound_billing_recovery_fact_admitted'
_LOCK = threading.RLock()
# A live-process consumed-scope tombstone is deliberately not resettable.
# It is not a second durable witness and is not real process-restart recovery.
_SCOPES = {}
_AUTHORITIES = {}
_CANCELLATION_FACTS = weakref.WeakKeyDictionary()
_RECOVERY_FACTS = weakref.WeakKeyDictionary()
_WITHDRAWAL_FACTS = weakref.WeakKeyDictionary()
_RESTORATION_FACTS = weakref.WeakKeyDictionary()
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
    lifecycle_head: str | None
    cancellation: tuple | None
    recovery: tuple | None = None
    withdrawal: tuple | None = None


@dataclass(frozen=True)
class IngressResult:
    disposition: str
    committed: bool | None
    fact: object = None


class CancellationFact:
    """Opaque live handle for one authenticated scheduled-end control."""
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('live issuance only')

    def __copy__(self):
        raise TypeError('not copyable')

    def __deepcopy__(self, memo):
        raise TypeError('not copyable')

    def __reduce__(self):
        raise TypeError('not serialisable')


class FailedRenewalFact:
    """Opaque live handle for one authenticated failed-renewal control."""
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('live issuance only')

    def __copy__(self):
        raise TypeError('not copyable')

    def __deepcopy__(self, memo):
        raise TypeError('not copyable')

    def __reduce__(self):
        raise TypeError('not serialisable')


class FullWithdrawalFact:
    """Opaque live handle for one authenticated full-withdrawal control."""
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('live issuance only')

    def __copy__(self):
        raise TypeError('not copyable')

    def __deepcopy__(self, memo):
        raise TypeError('not copyable')

    def __reduce__(self):
        raise TypeError('not serialisable')


class LaterPeriodRestorationFact:
    """Opaque live handle for the one authenticated later-period restoration."""
    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('live issuance only')

    def __copy__(self):
        raise TypeError('not copyable')

    def __deepcopy__(self, memo):
        raise TypeError('not copyable')

    def __reduce__(self):
        raise TypeError('not serialisable')


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


def _verified_signature(raw_body, signature_header, state, received):
    return verify_stripe_signature(raw_body, signature_header, state['signing_keys'],
                                   now=int(received.timestamp()))


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
            snapshot = BindingSnapshot(instance, epoch, 1, True, False, None, None, None, None)
            state = dict(publication=(snapshot, None), store=repository.store_id,
                         physical=repository.physical_identity, process=os.getpid(),
                         user=user_id, scope=scope,
                         customer=customer, item=item, price=price, plan=plan, endpoint=endpoint,
                         account=account, signing_keys=signing_keys, receipt_key=receipt_key,
                         receipt_key_id=receipt_key_id, signing_key_ids=signing_key_ids,
                         retrieve=retrieve, retrieval_code=getattr(retrieve, '__code__', None),
                         last_clock=None, commit_seen=set(), control_facts={})
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
                or state['process'] != os.getpid()
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


def _reconcile(state, invoice_id, billing_reason, *, event_created=None,
               exact_projection=False):
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
    line_listing = _fetch(state, '/v1/invoices/' + invoice_id + '/lines',
                          (('limit', '100'),))
    line = _single_list(line_listing)
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
    payment_listing = _fetch(state, '/v1/invoice_payments',
                             (('invoice', invoice_id), ('limit', '100')))
    payment = _single_list(payment_listing)
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
    if event_created is not None:
        event_created = exact.utc(event_created)
        if invoice_paid > event_created or payment_paid > event_created:
            raise InitialIngressError('payment occurs after signed success observation')
    evidence = dict(invoice=invoice_id, line=line['id'], payment=payment['id'], intent=pi_id,
                    charge=charge_id, amount=amount, currency='gbp', service_start=start.isoformat(),
                    service_end=end.isoformat(), plan=state['plan'], price=state['price'], item=state['item'],
                    invoice_paid_at=invoice_paid.isoformat(), payment_paid_at=payment_paid.isoformat())
    if exact_projection:
        # Unknown provider fields and JSON key order are deliberately excluded;
        # only the accepted source-admission projection participates in the
        # two-pass equality decision.
        def selected(value, names):
            return tuple(value[name] for name in names)
        def optional(value, name):
            return ('present', value[name]) if name in value else ('absent',)
        projection = (
            ('invoice', (
             *selected(invoice, (
                'id', 'object', 'livemode', 'customer', 'status',
                'billing_reason', 'currency', 'collection_method',
             )),
             invoice['parent']['type'],
             invoice['parent']['subscription_details']['subscription'],
             *selected(invoice, (
                'amount_paid', 'amount_due', 'total', 'amount_remaining',
                'amount_overpaid', 'starting_balance',
                'pre_payment_credit_notes_amount',
                'post_payment_credit_notes_amount', 'discounts',
                'total_discount_amounts')),
             invoice['status_transitions']['paid_at'], invoice['created'])),
            ('line_list', (
             line_listing['object'], line_listing['has_more'],
             optional(line_listing, 'total_count'),
             (*selected(line, ('id', 'object', 'livemode')),
              optional(line, 'invoice'),
              *selected(line, ('currency', 'quantity', 'amount')),
              line['parent']['type'],
              line['parent']['subscription_item_details']['subscription_item'],
              line['parent']['subscription_item_details']['subscription'],
              line['parent']['subscription_item_details']['proration'],
              line['pricing']['type'],
              line['pricing']['price_details']['price'],
              line['discounts'], line['discount_amounts'],
              line['period']['start'], line['period']['end']))),
            ('subscription', (
             *selected(subscription, (
                'id', 'object', 'livemode', 'customer', 'status',
                'latest_invoice', 'discounts', 'collection_method')),
             (subscription['items']['object'],
              subscription['items']['has_more'],
              optional(subscription['items'], 'total_count'),
              (*selected(item, ('id', 'object', 'subscription', 'quantity')),
               item['price']['id'], item['current_period_start'],
               item['current_period_end'])))),
            ('price', (
             *selected(price, ('id', 'object', 'livemode', 'currency',
                'unit_amount', 'type', 'billing_scheme')),
             price['recurring']['interval'],
             price['recurring']['interval_count'],
             price['recurring']['usage_type'])),
            ('invoice_payment_list', (
             payment_listing['object'], payment_listing['has_more'],
             optional(payment_listing, 'total_count'),
             (*selected(payment, (
                'id', 'object', 'livemode', 'invoice', 'status', 'currency',
                'amount_paid', 'amount_requested')),
              payment['payment']['type'],
              payment['payment']['payment_intent'],
              payment['status_transitions']['paid_at'], payment['created']))),
            ('payment_intent', selected(intent, ('id', 'object', 'livemode',
                'status', 'customer', 'currency', 'amount', 'amount_received',
                'latest_charge', 'created'))),
            ('charge', (
             *selected(charge, ('id', 'object', 'livemode',
                'payment_intent', 'customer', 'currency', 'status', 'paid',
                'captured')),
             charge['payment_method_details']['type'],
             *selected(charge, ('amount', 'amount_captured', 'amount_refunded',
                                'refunded', 'disputed', 'created')))),
        )
        observations = canonical(projection)
    else:
        # Full bounded observations compared only transiently, never persisted.
        observations = canonical((invoice, line, subscription, price, payment,
                                  intent, charge))
    return evidence, observations


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
    state = _check(authority, snapshot)
    if (type(repository) is not ProvenanceRepository or repository.store_id != state['store']
            or repository.physical_identity != state['physical']):
        raise InitialIngressError('wrong store')
    lineage, controls, lifecycle_head = repository.read_lifecycle_chain(
        snapshot.instance, state['receipt_key'])
    if not lineage or snapshot.accepted is None:
        raise InitialIngressError('missing accepted lineage')
    receipt, head = lineage[-1]
    control = controls[-1] if controls else None
    restoration_current = (
        receipt.get('version') == 'reserved-later-period-restoration-receipt/1')
    expected_control = (None if control is None else
        (repository.store_id, control['receipt_id'], control['fact_id'],
         (lifecycle_head if not restoration_current else _control_head(control))))
    cancellation_control = next((item for item in controls if item.get('version') ==
        'reserved-scheduled-cancellation-receipt/1'), None)
    expected_cancellation = None
    # Cancellation's publication tuple uses its own head, not a later
    # withdrawal head.
    if cancellation_control is not None:
        expected_cancellation = (repository.store_id,
            cancellation_control['receipt_id'], cancellation_control['fact_id'],
            _control_head(cancellation_control))
    expected_recovery = (expected_control if control is not None
        and control.get('version') == 'reserved-failed-renewal-receipt/1' else None)
    expected_withdrawal = (expected_control if not restoration_current
        and control is not None
        and control.get('version') == 'reserved-full-withdrawal-receipt/1' else None)
    if (snapshot.accepted != (repository.store_id, receipt['receipt_id'], receipt['fact_id'], head)
            or snapshot.lifecycle_head != lifecycle_head
            or snapshot.cancellation != expected_cancellation
            or snapshot.recovery != expected_recovery
            or snapshot.withdrawal != expected_withdrawal):
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
    if snapshot.withdrawal is not None:
        raise InitialIngressError('paid fact superseded by withdrawal')
    selected = None
    candidates = (lineage[-1],) if (
        lineage[-1][0].get('version') ==
        'reserved-later-period-restoration-receipt/1') else lineage
    for unit in candidates:
        receipt = unit[0]
        if (datetime.fromisoformat(receipt['access_start']) <= now
                < datetime.fromisoformat(receipt['service_end'])):
            selected = receipt
    if selected is None:
        raise InitialIngressError('no effective verified period')
    current_head = snapshot.lifecycle_head
    _check(authority, snapshot)
    return exact._issue(exact._ISSUER, authority, repository, snapshot.revision,
                        current_head, selected)


def _validate_live_fact(fact_state, now=None):
    authority, revision, current_head, owner, start, end, repository, material, sequence = fact_state
    snapshot = authority.snapshot()
    state = _check(authority, snapshot, now)
    lineage = _accepted_lineage(authority, repository, snapshot)
    if snapshot.withdrawal is not None:
        raise InitialIngressError('paid fact superseded by withdrawal')
    selected = next((receipt for receipt, _ in lineage if receipt['sequence'] == sequence), None)
    if (snapshot.revision != revision or state['scope'][0] != owner
            or snapshot.lifecycle_head != current_head or selected is None
            or canonical(selected) != material
            or start != datetime.fromisoformat(selected['access_start'])
            or end != datetime.fromisoformat(selected['service_end'])):
        raise InitialIngressError('stale live fact')
    _check(authority, snapshot)


def allows_paid_request(authority, repository, *, user_id, now,
                        endpoint='v2.settings_page'):
    """Concrete exact admission then final independent currentness linearization."""
    try:
        snapshot = authority.snapshot()
        state = _check(authority, snapshot, now)
        if type(user_id) is not int or user_id != state['user']:
            raise InitialIngressError('current membership unavailable')
        lifecycle_lineage, lifecycle_controls, lifecycle_head = (
            repository.read_lifecycle_chain(snapshot.instance,
                                            state['receipt_key']))
        if (lifecycle_lineage
                and lifecycle_lineage[-1][0].get('version') ==
                    'reserved-later-period-restoration-receipt/1'):
            receipt, head = lifecycle_lineage[-1]
            if (len(lifecycle_lineage) != 2 or len(lifecycle_controls) != 1
                    or lifecycle_head != head
                    or snapshot.lifecycle_head != head
                    or snapshot.accepted != (repository.store_id,
                        receipt['receipt_id'], receipt['fact_id'], head)
                    or snapshot.withdrawal is not None):
                raise InitialIngressError('restoration lifecycle unavailable')
            fact = _issue_restoration_fact(authority, repository, snapshot,
                                           receipt, head)
            from . import runtime_entitlement_admission as runtime
            from . import paid_access_guard as guard_module
            binding = runtime.bind_later_period_restoration_runtime_entitlement_admission(
                validate_admitted_billing_fact=
                    validate_later_period_restoration_fact,
                project_admitted_billing_fact=
                    project_later_period_restoration_fact)
            entitlement = runtime.admit_later_period_restoration_runtime_entitlement(
                binding, authenticated_owner_id=state['scope'][0],
                billing_account_id=state['scope'][1],
                subscription_id=state['scope'][2],
                admitted_billing_fact=fact, evaluated_at_utc=now)
            guard = guard_module.bind_later_period_restoration_paid_access_guard(
                validate_runtime_entitlement=
                    runtime.validate_later_period_restoration_runtime_entitlement,
                project_runtime_entitlement=
                    runtime.project_later_period_restoration_runtime_entitlement)
            decision = guard_module.evaluate_later_period_restoration_paid_access(
                guard, endpoint=endpoint,
                authenticated_owner_id=state['scope'][0],
                current_runtime_entitlement=entitlement,
                evaluated_at_utc=now)
            allowed = dict(
                guard_module.validate_later_period_restoration_paid_access_decision(
                    decision))['allowed']
            _check(authority, snapshot, now)
            if repository.read_lifecycle_chain(snapshot.instance,
                    state['receipt_key']) != (lifecycle_lineage,
                                              lifecycle_controls, head):
                return False
            return allowed and not is_production_environment()
        if snapshot.withdrawal is not None:
            lineage, control, head = repository.read_lifecycle(
                snapshot.instance, state['receipt_key'])
            if (not lineage or control is None
                    or control.get('version') != 'reserved-full-withdrawal-receipt/1'
                    or snapshot.lifecycle_head != head
                    or snapshot.withdrawal != (repository.store_id, control['receipt_id'],
                                               control['fact_id'], head)):
                raise InitialIngressError('withdrawal lifecycle unavailable')
            fact = _issue_withdrawal_fact(authority, repository, snapshot, control, head)
            from . import runtime_entitlement_admission as runtime
            from . import paid_access_guard as guard_module
            binding = runtime.bind_full_withdrawal_runtime_entitlement_admission(
                validate_admitted_billing_fact=validate_full_withdrawal_fact,
                project_admitted_billing_fact=project_full_withdrawal_fact)
            entitlement = runtime.admit_full_withdrawal_runtime_entitlement(
                binding, authenticated_owner_id=state['scope'][0],
                billing_account_id=state['scope'][1], subscription_id=state['scope'][2],
                admitted_billing_fact=fact, evaluated_at_utc=now)
            guard = guard_module.bind_full_withdrawal_paid_access_guard(
                validate_runtime_entitlement=
                    runtime.validate_full_withdrawal_runtime_entitlement,
                project_runtime_entitlement=
                    runtime.project_full_withdrawal_runtime_entitlement)
            decision = guard_module.evaluate_full_withdrawal_paid_access(
                guard, endpoint=endpoint, authenticated_owner_id=state['scope'][0],
                current_runtime_entitlement=entitlement, evaluated_at_utc=now)
            allowed = dict(guard_module.validate_full_withdrawal_paid_access_decision(
                decision))['allowed']
            _check(authority, snapshot, now)
            if repository.read_lifecycle(snapshot.instance, state['receipt_key'])[1:] != (
                    control, head):
                return False
            return allowed and not is_production_environment()
        if snapshot.recovery is not None:
            lineage, control, head = repository.read_lifecycle(
                snapshot.instance, state['receipt_key'])
            if (not lineage or control is None
                    or control.get('version') != 'reserved-failed-renewal-receipt/1'
                    or snapshot.lifecycle_head != head
                    or snapshot.recovery != (repository.store_id, control['receipt_id'],
                                             control['fact_id'], head)):
                raise InitialIngressError('recovery lifecycle unavailable')
            fact = _issue_failed_renewal_fact(authority, repository, snapshot, control, head)
            from . import runtime_entitlement_admission as runtime
            from . import paid_access_guard as guard_module
            binding = runtime.bind_exact_instant_runtime_entitlement_admission(
                validate_admitted_billing_fact=validate_failed_renewal_fact,
                project_admitted_billing_fact=project_failed_renewal_fact)
            entitlement = runtime.admit_exact_instant_runtime_entitlement(
                binding, authenticated_owner_id=state['scope'][0],
                billing_account_id=state['scope'][1], subscription_id=state['scope'][2],
                admitted_billing_fact=fact, evaluated_at_utc=now)
            guard = guard_module.bind_exact_instant_paid_access_guard(
                validate_runtime_entitlement=runtime.validate_exact_instant_runtime_entitlement,
                project_runtime_entitlement=runtime.project_exact_instant_runtime_entitlement)
            decision = guard_module.evaluate_exact_instant_paid_access(
                guard, endpoint=endpoint,
                authenticated_owner_id=state['scope'][0],
                current_runtime_entitlement=entitlement, evaluated_at_utc=now)
            allowed = dict(guard_module.validate_exact_instant_paid_access_decision(
                decision))['allowed']
            _check(authority, snapshot, now)
            return allowed and not is_production_environment()
        fact = current_fact(authority, repository, user_id=user_id, now=now)
        snapshot = authority.snapshot()
        state = _check(authority, snapshot)
        admitted = exact.admit_initial(fact, authority=authority, owner=state['scope'][0], now=now)
        _, revision, head, _, _, _ = exact._projection(admitted)
        lineage = _accepted_lineage(authority, repository, snapshot)
        if revision != snapshot.revision or snapshot.lifecycle_head != head:
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
                                consumed=True, accepted=accepted, lifecycle_head=head)
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
            if not _verified_signature(raw_body, signature_header, state, received):
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
                        or snapshot.lifecycle_head != prior_head or snapshot.cancellation is not None
                        or snapshot.recovery is not None
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
                                    snapshot.revision, snapshot.lifecycle_head, receipt)
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
                            published.revision, published.lifecycle_head, receipt)
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


def _complete_list(value):
    if (type(value) is not dict or value.get('object') != 'list'
            or value.get('has_more') is not False or type(value.get('data')) is not list
            or ('total_count' in value and (type(value['total_count']) is not int
                or value['total_count'] != len(value['data'])))):
        raise InitialIngressError('unsupported or incomplete enumeration')
    if any(type(item) is not dict for item in value['data']):
        raise InitialIngressError('invalid list object')
    return value['data']


def _nullable_source_identifier(value, prefix):
    if value is not None:
        _identifier(value, prefix)
    return value


def _failure_invoice_projection(state, invoice):
    """Validate admission-relevant signed/retrieved recurring-failure fields."""
    if type(invoice) is not dict:
        raise InitialIngressError('invoice object required')
    amount, _, _ = _PLANS[state['plan']]
    scope = state['scope']
    if (invoice.get('id') is None or _identifier(invoice['id'], 'in') != invoice['id']
            or invoice.get('object') != 'invoice' or invoice.get('livemode') is not False
            or invoice.get('customer') != state['customer'] or invoice.get('status') != 'open'
            or invoice.get('billing_reason') != 'subscription_cycle'
            or invoice.get('currency') != 'gbp'
            or invoice.get('collection_method') != 'charge_automatically'
            or type(invoice.get('parent')) is not dict
            or invoice['parent'].get('type') != 'subscription_details'
            or type(invoice['parent'].get('subscription_details')) is not dict
            or invoice['parent']['subscription_details'].get('subscription') != scope[2]
            or invoice.get('attempted') is not True
            or _integer(invoice.get('attempt_count')) < 1
            or invoice.get('paid_out_of_band') is not False
            or type(invoice.get('status_transitions')) is not dict
            or 'paid_at' not in invoice['status_transitions']
            or invoice['status_transitions']['paid_at'] is not None):
        raise InitialIngressError('unsupported failed invoice')
    for name in ('amount_due', 'amount_remaining', 'total'):
        if _integer(invoice.get(name)) != amount:
            raise InitialIngressError('unreconciled failed amount')
    for name in ('amount_paid', 'amount_overpaid', 'starting_balance',
                 'pre_payment_credit_notes_amount', 'post_payment_credit_notes_amount'):
        if _integer(invoice.get(name)) != 0:
            raise InitialIngressError('unsupported failed-payment complication')
    for name in ('discounts', 'total_discount_amounts'):
        if name not in invoice or type(invoice[name]) is not list or invoice[name] != []:
            raise InitialIngressError('unsupported failed-invoice discount')
    defaults = []
    for name, prefix in (('default_payment_method', 'pm'), ('default_source', 'src')):
        if name not in invoice:
            raise InitialIngressError('missing nullable invoice payment default')
        defaults.append(_nullable_source_identifier(invoice[name], prefix))
    return dict(invoice=invoice['id'], customer=state['customer'], subscription=scope[2],
                livemode=False, status='open', billing_reason='subscription_cycle',
                collection_method='charge_automatically', currency='gbp', amount=amount,
                attempted=True, attempt_count=invoice['attempt_count'], paid_out_of_band=False,
                default_payment_method=defaults[0], default_source=defaults[1],
                invoice_created_at=_timestamp(invoice.get('created')).isoformat())


def _failure_reconcile(state, signed_projection):
    invoice_id = signed_projection['invoice']
    invoice = _object(state, '/v1/invoices/' + invoice_id, invoice_id, 'invoice')
    retrieved_projection = _failure_invoice_projection(state, invoice)
    if retrieved_projection != signed_projection:
        raise InitialIngressError('failed-invoice snapshot retrieval disagreement')
    amount, interval, count = _PLANS[state['plan']]
    scope = state['scope']

    line = _single_list(_fetch(
        state, '/v1/invoices/' + invoice_id + '/lines', (('limit', '100'),)))
    parent = line.get('parent')
    details = parent.get('subscription_item_details') if type(parent) is dict else None
    pricing = line.get('pricing')
    price_details = pricing.get('price_details') if type(pricing) is dict else None
    if (line.get('object') != 'line_item' or line.get('livemode') is not False
            or line.get('invoice') != invoice_id or line.get('currency') != 'gbp'
            or _integer(line.get('quantity')) != 1 or _integer(line.get('amount')) != amount
            or type(details) is not dict or parent.get('type') != 'subscription_item_details'
            or details.get('subscription_item') != state['item']
            or details.get('subscription') != scope[2] or details.get('proration') is not False
            or type(price_details) is not dict or pricing.get('type') != 'price_details'
            or price_details.get('price') != state['price']):
        raise InitialIngressError('unsupported failed-invoice line')
    line_id = _identifier(line.get('id'), 'il')
    for name in ('discounts', 'discount_amounts'):
        if name not in line or type(line[name]) is not list or line[name] != []:
            raise InitialIngressError('unsupported failed-line discount')
    start = _timestamp(line.get('period', {}).get('start'))
    end = _timestamp(line.get('period', {}).get('end'))
    if not start < end or end != _approved_period_end(start, state['plan']):
        raise InitialIngressError('unsupported failed service period')

    subscription = _object(state, '/v1/subscriptions/' + scope[2], scope[2], 'subscription')
    absent = ('schedule', 'pause_collection', 'trial_start', 'trial_end', 'trial_settings',
              'pending_update', 'discount', 'promotion_code', 'offer', 'cancel_at',
              'canceled_at', 'cancellation_details')
    empty = ('discounts', 'promotion_codes', 'offers')
    if (subscription.get('customer') != state['customer']
            or subscription.get('status') not in ('active', 'past_due')
            or subscription.get('latest_invoice') != invoice_id
            or subscription.get('collection_method') != 'charge_automatically'
            or subscription.get('cancel_at_period_end') is not False
            or any(name not in subscription or subscription[name] is not None for name in absent)
            or any(name not in subscription or type(subscription[name]) is not list
                   or subscription[name] != [] for name in empty)):
        raise InitialIngressError('unsupported failed-renewal subscription')
    subscription_defaults = []
    for name, prefix in (('default_payment_method', 'pm'), ('default_source', 'src')):
        if name not in subscription:
            raise InitialIngressError('missing nullable subscription payment default')
        subscription_defaults.append(_nullable_source_identifier(subscription[name], prefix))
    item = _single_list(subscription.get('items'))
    item_absent = ('discount', 'promotion_code', 'offer')
    item_empty = ('discounts', 'promotion_codes', 'offers')
    if (item.get('id') != state['item'] or item.get('object') != 'subscription_item'
            or item.get('subscription') != scope[2] or _integer(item.get('quantity')) != 1
            or type(item.get('price')) is not dict or item['price'].get('id') != state['price']
            or item.get('proration') is not False
            or _timestamp(item.get('current_period_start')) != start
            or _timestamp(item.get('current_period_end')) != end
            or any(name not in item or item[name] is not None for name in item_absent)
            or any(name not in item or type(item[name]) is not list or item[name] != []
                   for name in item_empty)):
        raise InitialIngressError('unsupported failed-renewal item')
    price = _object(state, '/v1/prices/' + state['price'], state['price'], 'price')
    if (price.get('currency') != 'gbp' or _integer(price.get('unit_amount')) != amount
            or price.get('type') != 'recurring' or price.get('billing_scheme') != 'per_unit'
            or type(price.get('recurring')) is not dict
            or price['recurring'].get('interval') != interval
            or _integer(price['recurring'].get('interval_count')) != count
            or price['recurring'].get('usage_type') != 'licensed'):
        raise InitialIngressError('unapproved failed-renewal price')

    payments = _complete_list(_fetch(
        state, '/v1/invoice_payments', (('invoice', invoice_id), ('limit', '100'))))
    payment = intent = charge = None
    artifact_created = []
    artifact_shape = None
    if not payments:
        if (signed_projection['default_payment_method'] is not None
                or signed_projection['default_source'] is not None
                or tuple(subscription_defaults) != (None, None)):
            raise InitialIngressError('unsupported no-payment-artifact evidence')
        artifact_shape = 'no_payment_artifact'
    elif len(payments) == 1:
        payment_object = payments[0]
        union = payment_object.get('payment')
        if (payment_object.get('object') != 'invoice_payment'
                or payment_object.get('livemode') is not False
                or payment_object.get('invoice') != invoice_id
                or payment_object.get('status') != 'open'
                or payment_object.get('currency') != 'gbp'
                or _integer(payment_object.get('amount_requested')) != amount
                or _integer(payment_object.get('amount_paid')) != 0
                or type(payment_object.get('status_transitions')) is not dict
                or 'paid_at' not in payment_object['status_transitions']
                or payment_object['status_transitions']['paid_at'] is not None
                or type(union) is not dict or set(union) != {'type', 'payment_intent'}
                or union.get('type') != 'payment_intent'):
            raise InitialIngressError('unsupported failed InvoicePayment')
        payment = _identifier(payment_object.get('id'), 'inpay')
        artifact_created.append(_timestamp(payment_object.get('created')).isoformat())
        intent = _identifier(union.get('payment_intent'), 'pi')
        intent_object = _object(state, '/v1/payment_intents/' + intent,
                                intent, 'payment_intent')
        if (intent_object.get('status') != 'requires_payment_method'
                or intent_object.get('customer') != state['customer']
                or intent_object.get('currency') != 'gbp'
                or _integer(intent_object.get('amount')) != amount
                or _integer(intent_object.get('amount_received')) != 0
                or 'latest_charge' not in intent_object):
            raise InitialIngressError('unsupported unresolved PaymentIntent')
        artifact_created.append(_timestamp(intent_object.get('created')).isoformat())
        latest_charge = intent_object['latest_charge']
        if latest_charge is None:
            artifact_shape = 'unresolved_payment_intent'
        else:
            charge = _identifier(latest_charge, 'ch')
            charge_object = _object(state, '/v1/charges/' + charge, charge, 'charge')
            if (charge_object.get('payment_intent') != intent
                    or charge_object.get('customer') != state['customer']
                    or charge_object.get('currency') != 'gbp'
                    or _integer(charge_object.get('amount')) != amount
                    or charge_object.get('status') != 'failed'
                    or charge_object.get('paid') is not False
                    or charge_object.get('captured') is not False
                    or _integer(charge_object.get('amount_captured')) != 0
                    or charge_object.get('refunded') is not False
                    or _integer(charge_object.get('amount_refunded')) != 0
                    or charge_object.get('disputed') is not False):
                raise InitialIngressError('unsupported failed Charge')
            artifact_created.append(_timestamp(charge_object.get('created')).isoformat())
            artifact_shape = 'failed_charge'
    else:
        raise InitialIngressError('unsupported multiple failed payments')

    evidence = dict(invoice=invoice_id, line=line_id, payment=payment, intent=intent,
        charge=charge, artifact_shape=artifact_shape, amount=amount, currency='gbp',
        service_start=start.isoformat(), service_end=end.isoformat(), plan=state['plan'],
        price=state['price'], item=state['item'], attempt_count=signed_projection['attempt_count'],
        source_object_created_at=tuple(
            (signed_projection['invoice_created_at'], *artifact_created)))
    observations = canonical((invoice, line, subscription, price, payments,
        None if intent is None else intent_object,
        None if charge is None else charge_object))
    return evidence, observations


def _cancellation_projection(state, subscription, *, verified_at):
    """Validate and minimise the supported Basil scheduled-end object."""
    if type(subscription) is not dict:
        raise InitialIngressError('subscription object required')
    scope = state['scope']
    absent = ('schedule', 'pause_collection', 'trial_start', 'trial_end',
              'trial_settings', 'pending_update', 'discount', 'promotion_code',
              'offer')
    empty = ('discounts', 'promotion_codes', 'offers')
    if (subscription.get('id') != scope[2] or subscription.get('object') != 'subscription'
            or subscription.get('livemode') is not False
            or subscription.get('customer') != state['customer']
            or subscription.get('status') != 'active'
            or subscription.get('collection_method') != 'charge_automatically'
            or subscription.get('cancel_at_period_end') is not True
            or any(name not in subscription or subscription[name] is not None
                   for name in absent)
            or any(name not in subscription or type(subscription[name]) is not list
                   or subscription[name] != [] for name in empty)):
        raise InitialIngressError('unsupported scheduled cancellation')
    details = subscription.get('cancellation_details')
    if (type(details) is not dict or details.get('reason') != 'cancellation_requested'
            or any(name not in ('reason', 'comment', 'feedback') for name in details)
            or any(value is not None and (type(value) is not str or len(value) > 160)
                   for name, value in details.items() if name != 'reason')):
        raise InitialIngressError('unsupported cancellation reason')
    item = _single_list(subscription.get('items'))
    price = item.get('price')
    item_absent = ('discount', 'promotion_code', 'offer')
    item_empty = ('discounts', 'promotion_codes', 'offers')
    if (item.get('id') != state['item'] or item.get('object') != 'subscription_item'
            or item.get('subscription') != scope[2] or _integer(item.get('quantity')) != 1
            or type(price) is not dict or price.get('id') != state['price']
            or item.get('proration') is not False
            or any(name not in item or item[name] is not None for name in item_absent)
            or any(name not in item or type(item[name]) is not list or item[name] != []
                   for name in item_empty)):
        raise InitialIngressError('unsupported subscription item')
    start = _timestamp(item.get('current_period_start'))
    end = _timestamp(item.get('current_period_end'))
    if not start < end:
        raise InitialIngressError('invalid item period')
    if 'cancel_at' not in subscription:
        raise InitialIngressError('missing cancellation boundary')
    cancel_at = subscription['cancel_at']
    if cancel_at is not None and _timestamp(cancel_at) != end:
        raise InitialIngressError('custom cancellation boundary')
    canceled_at = subscription.get('canceled_at')
    if canceled_at is not None:
        canceled = _timestamp(canceled_at)
        if canceled > verified_at or canceled >= end:
            raise InitialIngressError('invalid cancellation context')
    return dict(subscription=scope[2], customer=state['customer'], item=state['item'],
                price=state['price'], livemode=False, status='active',
                collection_method='charge_automatically', cancel_at_period_end=True,
                cancellation_reason='cancellation_requested',
                current_period_start=start.isoformat(), current_period_end=end.isoformat(),
                cancel_at=cancel_at, canceled_at=canceled_at)


def _issue_cancellation_fact(authority, repository, snapshot, receipt, head):
    with _LOCK:
        state = _check(authority, snapshot)
        cached = state['control_facts'].get('scheduled_cancellation')
        repository_identity = (repository.store_id, repository.physical_identity)
        expected = (repository_identity, snapshot.revision, head, canonical(receipt))
        if cached is not None:
            value, material = cached
            if material != expected:
                raise InitialIngressError('changed cancellation fact cache')
            # An authorised reopen of the same exact physical store refreshes
            # only the live reader used to reauthenticate the original handle.
            _CANCELLATION_FACTS[value] = (authority, repository, snapshot.revision,
                                          head, canonical(receipt))
            return value
        value = object.__new__(CancellationFact)
        _CANCELLATION_FACTS[value] = (authority, repository, snapshot.revision, head,
                                      canonical(receipt))
        state['control_facts']['scheduled_cancellation'] = (value, expected)
    return value


def _live_cancellation_control(fact):
    """Reauthenticate and return the exact durable scheduled-end control."""
    with _LOCK:
        if type(fact) is not CancellationFact or fact not in _CANCELLATION_FACTS:
            raise InitialIngressError('not a live cancellation fact')
        authority, repository, revision, head, material = _CANCELLATION_FACTS[fact]
    snapshot = authority.snapshot()
    state = _check(authority, snapshot)
    lineage, control, lifecycle_head = repository.read_lifecycle(snapshot.instance,
                                                                  state['receipt_key'])
    conflicts = repository.read_conflicts(snapshot.instance, key=state['receipt_key'])
    if (snapshot.revision != revision or snapshot.lifecycle_head != head
            or lifecycle_head != head or control is None or canonical(control) != material
            or not lineage or conflicts):
        raise InitialIngressError('stale cancellation fact')
    _check(authority, snapshot)
    return dict(control)


def cancellation_fact_details(fact):
    """Return only the conservative effect after reauthenticating the live handle."""
    control = _live_cancellation_control(fact)
    return dict(disposition='subscription_scheduled_to_end_at_paid_period_boundary',
                exclusive_service_end=control['service_end'],
                paid_receipt_id=control['paid_receipt_id'],
                paid_fact_id=control['paid_fact_id'])


def cancellation_presentation_facts(fact):
    """Project exact S6F facts from the reauthenticated paid+cancellation control."""
    control = _live_cancellation_control(fact)
    scope = control.get('scope')
    if (type(scope) is not list or len(scope) != 3
            or not all(type(value) is str and value for value in scope)
            or control.get('owner') != scope[0]
            or control.get('subscription') != scope[2]):
        raise InitialIngressError('invalid cancellation presentation scope')
    return dict(
        owner=scope[0], billing_account=scope[1], subscription=scope[2],
        paid_period_started_at_utc=control['service_start'],
        cancellation_verified_at_utc=control['verification_completed_at'],
        paid_through_exclusive_utc=control['service_end'],
        paid_receipt_id=control['paid_receipt_id'],
        paid_fact_id=control['paid_fact_id'],
        disposition=control['disposition'],
    )


def ingest_scheduled_cancellation(authority, repository, raw_body, signature_header, *, clock):
    """Admit one signed, provider-confirmed end at the current paid boundary."""
    def publish(snapshot, receipt, head):
        with _LOCK:
            state = _check(authority, snapshot)
            current, reservation = state['publication']
            accepted = (repository.store_id, receipt['receipt_id'], receipt['fact_id'], head)
            if (current != snapshot or reservation is None
                    or reservation.get('kind') != 'scheduled_cancellation'
                    or reservation.get('material') != canonical(receipt)
                    or reservation.get('revision') != snapshot.revision
                    or reservation.get('predecessor') != snapshot.lifecycle_head):
                raise InitialIngressError('changed cancellation reservation')
            published = replace(snapshot, revision=snapshot.revision + 1,
                                consumed=True, lifecycle_head=head, cancellation=accepted)
            state['publication'] = (published, None)
            return published

    committed = False
    attempt = 'scheduled_cancellation'
    try:
        if is_production_environment():
            raise InitialIngressError('local bounded lifecycle only')
        snapshot = authority.snapshot()
        received = exact.utc(clock())
        state = _check(authority, snapshot, received)
        if (type(repository) is not ProvenanceRepository or repository.store_id != state['store']
                or repository.physical_identity != state['physical']):
            raise InitialIngressError('wrong store')
        if not _verified_signature(raw_body, signature_header, state, received):
            raise InitialIngressError('signature refusal')
        event = _parse(raw_body)
        if (event.get('object') != 'event'
                or event.get('livemode') is not False or event.get('api_version') != API_VERSION
                or event.get('account') is not None):
            raise InitialIngressError('unsupported event')
        event_id = _identifier(event.get('id'), 'evt')
        source_time = _timestamp(event.get('created'))
        if source_time > received:
            raise InitialIngressError('future source event')
        raw_digest = hashlib.sha256(raw_body).hexdigest()
        _, prior_control, _ = repository.read_lifecycle(snapshot.instance,
                                                         state['receipt_key'])
        if prior_control is not None and (prior_control['event_id'] != event_id
                                          or event.get('type') != 'customer.subscription.updated'
                                          or prior_control['raw_digest'] != raw_digest):
            repository.record_conflict(snapshot.instance, event_id=event_id,
                raw_digest=raw_digest,
                object_key=state['scope'][2] + ':scheduled_cancellation',
                key=state['receipt_key'])
            return IngressResult('reconciliation_required', True)
        if event.get('type') != 'customer.subscription.updated':
            raise InitialIngressError('unsupported event type')
        request = event.get('request')
        if (type(request) is not dict or set(request) - {'id', 'idempotency_key'}
                or _identifier(request.get('id'), 'req') != request.get('id')):
            raise InitialIngressError('unsupported source request')
        idempotency_key = request.get('idempotency_key')
        if idempotency_key is not None:
            _ref(idempotency_key)
        data = event.get('data')
        if (type(data) is not dict
                or data.get('previous_attributes') != {'cancel_at_period_end': False}):
            raise InitialIngressError('missing exact cancellation transition')
        signed_subscription = data.get('object')
        signed_projection = _cancellation_projection(
            state, signed_subscription, verified_at=received)
        retrieved = _object(state, '/v1/subscriptions/' + state['scope'][2],
                            state['scope'][2], 'subscription')
        retrieved_again = _object(state, '/v1/subscriptions/' + state['scope'][2],
                                  state['scope'][2], 'subscription')
        if canonical(retrieved) != canonical(retrieved_again):
            raise InitialIngressError('changed current subscription')
        completed = exact.utc(clock())
        retrieved_projection = _cancellation_projection(state, retrieved, verified_at=completed)
        if signed_projection != retrieved_projection:
            raise InitialIngressError('snapshot retrieval disagreement')
        _check(authority, snapshot, completed)
        lineage = _lineage(authority, repository, snapshot)
        if not lineage:
            raise InitialIngressError('missing accepted lineage')
        paid, paid_head = lineage[-1]
        if snapshot.accepted != (repository.store_id, paid['receipt_id'], paid['fact_id'], paid_head):
            raise InitialIngressError('obsolete authentic paid receipt')
        paid_start = datetime.fromisoformat(paid.get(
            'service_start', paid['evidence']['service_start']))
        paid_end = datetime.fromisoformat(paid['service_end'])
        if (signed_projection['current_period_start'] != paid_start.isoformat()
                or signed_projection['current_period_end'] != paid_end.isoformat()):
            raise InitialIngressError('not the authenticated paid boundary')
        evidence_digest = hashlib.sha256(canonical(
            (signed_subscription, retrieved))).hexdigest()
        durable_lineage, control, lifecycle_head = repository.read_lifecycle(
            snapshot.instance, state['receipt_key'])
        if durable_lineage != lineage:
            raise InitialIngressError('changed lifecycle head')
        if control is not None:
            committed = True
            exact_duplicate = (control['event_id'] == event_id
                and control['raw_digest'] == raw_digest
                and control['source_evidence_digest'] == evidence_digest
                and control['paid_head'] == paid_head)
            if not exact_duplicate:
                repository.record_conflict(snapshot.instance, event_id=event_id,
                    raw_digest=raw_digest, object_key=state['scope'][2] + ':scheduled_cancellation',
                    key=state['receipt_key'])
                return IngressResult('reconciliation_required', True)
            expected = (repository.store_id, control['receipt_id'], control['fact_id'], lifecycle_head)
            if snapshot.cancellation == expected and snapshot.lifecycle_head == lifecycle_head:
                return IngressResult('admitted', True, _issue_cancellation_fact(
                    authority, repository, snapshot, control, lifecycle_head))
            _, reservation = state['publication']
            if (reservation is None or reservation.get('material') != canonical(control)
                    or reservation.get('predecessor') != control['predecessor_lifecycle_head']):
                raise InitialIngressError('durable cancellation lacks exact reservation')
            receipt, head = control, lifecycle_head
            snapshot = state['publication'][0]
        else:
            if (snapshot.lifecycle_head != paid_head or snapshot.cancellation is not None
                    or snapshot.recovery is not None):
                raise InitialIngressError('obsolete lifecycle head')
            if not received < paid_end or not completed < paid_end:
                raise InitialIngressError('paid boundary is no longer current')
            if attempt in state['commit_seen']:
                raise InitialIngressError('consumed uncertain attempt')
            material = dict(version='reserved-scheduled-cancellation-receipt/1',
                store=repository.store_id, binding=snapshot.instance, epoch=snapshot.epoch,
                binding_revision=snapshot.revision, owner=state['scope'][0],
                scope=list(state['scope']), endpoint=state['endpoint'], account=state['account'],
                api_version=API_VERSION, livemode=False, receipt_key_id=state['receipt_key_id'],
                signing_key_ids=list(state['signing_key_ids']), event_id=event_id,
                object_key=state['scope'][2] + ':scheduled_cancellation', raw_digest=raw_digest,
                source_evidence_digest=evidence_digest, received_at=received.isoformat(),
                source_created_at=source_time.isoformat(),
                verification_completed_at=completed.isoformat(), request_id=request['id'],
                cancellation_reason='cancellation_requested', subscription=state['scope'][2],
                customer=state['customer'], item=state['item'], price=state['price'],
                service_start=paid_start.isoformat(), service_end=paid_end.isoformat(),
                paid_sequence=paid['sequence'], paid_receipt_id=paid['receipt_id'],
                paid_fact_id=paid['fact_id'], paid_head=paid_head,
                predecessor_lifecycle_head=snapshot.lifecycle_head,
                disposition='subscription_scheduled_to_end_at_paid_period_boundary')
            receipt = dict(material)
            receipt['fact_id'] = identity('scheduled-cancellation-fact/1', material)
            receipt['receipt_id'] = identity('scheduled-cancellation-receipt/1', material)
            with _LOCK:
                _check(authority, snapshot)
                current, reservation = state['publication']
                if reservation is None:
                    reserved = replace(snapshot, revision=snapshot.revision + 1, consumed=True)
                    reservation = dict(kind=attempt, material=canonical(receipt),
                                       predecessor=snapshot.lifecycle_head,
                                       revision=reserved.revision)
                    state['publication'] = (reserved, reservation)
                    snapshot = reserved
                else:
                    receipt = json.loads(reservation['material'])
                    snapshot = current
                    if (reservation.get('kind') != attempt
                            or reservation.get('predecessor') != snapshot.lifecycle_head
                            or receipt.get('raw_digest') != raw_digest
                            or receipt.get('event_id') != event_id
                            or receipt.get('source_evidence_digest') != evidence_digest):
                        raise InitialIngressError('different reserved proposal')
            predecessor = lineage[-1]
            try:
                receipt, head = repository.commit_cancellation(
                    receipt, predecessor, state['receipt_key'])
                committed = True
            except CommitOutcomeError as error:
                committed = error.committed
                raise
            except Exception:
                committed = None
                try:
                    _, durable, head = repository.read_lifecycle(
                        snapshot.instance, state['receipt_key'])
                    if durable is not None and durable == receipt:
                        committed = True
                except Exception:
                    pass
                raise
            finally:
                with _LOCK:
                    if committed is not False:
                        state['commit_seen'].add(attempt)
        if repository.read_lifecycle(snapshot.instance, state['receipt_key'])[1:] != (receipt, head):
            raise InitialIngressError('changed committed cancellation')
        published = publish(snapshot, receipt, head)
        _check(authority, published)
        if repository.read_lifecycle(published.instance, state['receipt_key'])[1:] != (receipt, head):
            raise InitialIngressError('changed cancellation publication')
        _accepted_lineage(authority, repository, published)
        _check(authority, published)
        fact = _issue_cancellation_fact(authority, repository, published, receipt, head)
        return IngressResult('admitted', True, fact)
    except Exception:
        disposition = ('commit_outcome_unknown' if committed is None else
                       ('committed_but_unadmitted' if committed else 'refused'))
        return IngressResult(disposition, committed)


def _issue_failed_renewal_fact(authority, repository, snapshot, receipt, head):
    with _LOCK:
        state = _check(authority, snapshot)
        repository_identity = (repository.store_id, repository.physical_identity)
        expected = (repository_identity, snapshot.revision, head, canonical(receipt))
        cached = state['control_facts'].get('failed_renewal')
        if cached is not None:
            value, material = cached
            if material != expected:
                raise InitialIngressError('changed failed-renewal fact cache')
            _RECOVERY_FACTS[value] = (authority, repository, snapshot.revision,
                                      head, canonical(receipt))
            return value
        value = object.__new__(FailedRenewalFact)
        _RECOVERY_FACTS[value] = (authority, repository, snapshot.revision,
                                  head, canonical(receipt))
        state['control_facts']['failed_renewal'] = (value, expected)
        return value


def _failed_renewal_fact_state(fact):
    with _LOCK:
        if type(fact) is not FailedRenewalFact or fact not in _RECOVERY_FACTS:
            raise InitialIngressError('not a live failed-renewal fact')
        authority, repository, revision, head, material = _RECOVERY_FACTS[fact]
    snapshot = authority.snapshot()
    state = _check(authority, snapshot)
    lineage, control, lifecycle_head = repository.read_lifecycle(
        snapshot.instance, state['receipt_key'])
    if (snapshot.revision != revision or snapshot.lifecycle_head != head
            or lifecycle_head != head or control is None
            or control.get('version') != 'reserved-failed-renewal-receipt/1'
            or canonical(control) != material or not lineage
            or snapshot.recovery != (repository.store_id, control['receipt_id'],
                                     control['fact_id'], head)
            or snapshot.cancellation is not None):
        raise InitialIngressError('stale failed-renewal fact')
    _check(authority, snapshot)
    return state, control, head


def _failed_renewal_fact_projection(fact):
    state, control, head = _failed_renewal_fact_state(fact)
    transition = exact.utc(datetime.fromisoformat(control['failure_verified_at_utc']))
    deadline = exact.utc(datetime.fromisoformat(
        control['recovery_deadline_exclusive_at_utc']))
    material = (
        RECOVERY_FACT_PROTOCOL_VERSION,
        RECOVERY_FACT_ADMISSION_STATUS,
        True,
        True,
        False,
        state['scope'][0],
        state['scope'][1],
        state['scope'][2],
        control['fact_id'],
        control['paid_fact_id'],
        head,
        'payment_recovery',
        transition,
        deadline,
        'verified_renewal_failure',
    )
    identity_material = tuple(value.isoformat() if type(value) is datetime else value
                              for value in material)
    fact_identity = identity('billing-recovery-fact/2', identity_material)
    names = (
        'protocol_version', 'fact_identity', 'admission_status', 'authenticated',
        'billing_fact_authority', 'provider_observation_direct_authority', 'owner_id',
        'billing_account_id', 'subscription_id', 'source_fact_id',
        'predecessor_paid_fact_id', 'lifecycle_head', 'state',
        'transition_effective_at_utc', 'recovery_deadline_exclusive_at_utc',
        'derivation_kind',
    )
    values = (material[0], fact_identity, *material[1:])
    return tuple(zip(names, values, strict=True))


def validate_failed_renewal_fact(fact):
    """Reauthenticate and return the exact v2 recovery-fact projection."""
    return _failed_renewal_fact_projection(fact)


def project_failed_renewal_fact(fact):
    """Distinct projector required by the exact-instant runtime binder."""
    return _failed_renewal_fact_projection(fact)


def failed_renewal_fact_details(fact):
    _, control, head = _failed_renewal_fact_state(fact)
    return dict(disposition='verified_renewal_failure',
                failure_verified_at_utc=control['failure_verified_at_utc'],
                recovery_deadline_exclusive_at_utc=
                    control['recovery_deadline_exclusive_at_utc'],
                failed_service_start=control['failed_service_start'],
                failed_service_end=control['failed_service_end'],
                artifact_shape=control['artifact_shape'],
                paid_receipt_id=control['paid_receipt_id'],
                paid_fact_id=control['paid_fact_id'],
                receipt_id=control['receipt_id'], fact_id=control['fact_id'],
                lifecycle_head=head)


_FAILED_RENEWAL_ADMISSION_FIELDS = frozenset({
    'failure_verified_at_utc', 'recovery_deadline_exclusive_at_utc',
    'receipt_id', 'fact_id',
})


def _failed_renewal_proposal(receipt):
    return {name: value for name, value in receipt.items()
            if name not in _FAILED_RENEWAL_ADMISSION_FIELDS}


def ingest_failed_renewal(authority, repository, raw_body, signature_header, *, clock):
    """Admit the first exact recurring failure into the shared lifecycle head."""
    def publish(snapshot, receipt, head):
        with _LOCK:
            state = _check(authority, snapshot)
            current, reservation = state['publication']
            accepted = (repository.store_id, receipt['receipt_id'], receipt['fact_id'], head)
            if (current != snapshot or reservation is None
                    or reservation.get('kind') != 'failed_renewal'
                    or reservation.get('material') != canonical(
                        _failed_renewal_proposal(receipt))
                    or reservation.get('revision') != snapshot.revision
                    or reservation.get('predecessor') != receipt['predecessor_lifecycle_head']):
                raise InitialIngressError('changed failed-renewal reservation')
            published = replace(snapshot, revision=snapshot.revision + 1, consumed=True,
                                lifecycle_head=head, recovery=accepted)
            state['publication'] = (published, None)
            return published

    committed = False
    attempt = 'failed_renewal'
    try:
        if is_production_environment():
            raise InitialIngressError('local bounded lifecycle only')
        snapshot = authority.snapshot()
        received = exact.utc(clock())
        state = _check(authority, snapshot, received)
        if (type(repository) is not ProvenanceRepository or repository.store_id != state['store']
                or repository.physical_identity != state['physical']):
            raise InitialIngressError('wrong store')
        for _ in range(2):
            if not _verified_signature(raw_body, signature_header, state, received):
                raise InitialIngressError('signature refusal')
        event = _parse(raw_body)
        if (event.get('object') != 'event' or event.get('type') != 'invoice.payment_failed'
                or event.get('livemode') is not False or event.get('api_version') != API_VERSION
                or event.get('account') is not None):
            raise InitialIngressError('unsupported failed-renewal event')
        event_id = _identifier(event.get('id'), 'evt')
        source_time = _timestamp(event.get('created'))
        if source_time > received:
            raise InitialIngressError('future source event')
        data = event.get('data')
        if type(data) is not dict or type(data.get('object')) is not dict:
            raise InitialIngressError('wrong failed-renewal event object')
        signed_invoice = data['object']
        signed_projection = _failure_invoice_projection(state, signed_invoice)
        invoice_id = signed_projection['invoice']
        raw_digest = hashlib.sha256(raw_body).hexdigest()

        _, prior_control, _ = repository.read_lifecycle(snapshot.instance,
                                                         state['receipt_key'])
        if prior_control is not None and (prior_control.get('version') !=
                'reserved-failed-renewal-receipt/1'
                or prior_control.get('event_id') != event_id
                or prior_control.get('raw_digest') != raw_digest):
            repository.record_conflict(snapshot.instance, event_id=event_id,
                raw_digest=raw_digest, object_key=invoice_id + ':invoice.payment_failed',
                key=state['receipt_key'])
            return IngressResult('reconciliation_required', True)

        evidence, observations = _failure_reconcile(state, signed_projection)
        checked_evidence, checked_observations = _failure_reconcile(state, signed_projection)
        if (evidence, observations) != (checked_evidence, checked_observations):
            raise InitialIngressError('changed failed-renewal observations')
        if any(datetime.fromisoformat(value) > source_time
               for value in evidence['source_object_created_at']):
            raise InitialIngressError('failed-payment object occurs after signed observation')
        evidence_digest = hashlib.sha256(
            canonical(signed_invoice) + b'\x00' + observations).hexdigest()

        lineage = _lineage(authority, repository, snapshot)
        if not lineage:
            raise InitialIngressError('missing accepted paid predecessor')
        paid, paid_head = lineage[-1]
        if (snapshot.accepted != (repository.store_id, paid['receipt_id'],
                                  paid['fact_id'], paid_head)):
            raise InitialIngressError('obsolete authentic paid predecessor')
        paid_end = datetime.fromisoformat(paid['service_end'])
        failed_start = datetime.fromisoformat(evidence['service_start'])
        if (failed_start != paid_end or source_time < paid_end
                or received < paid_end):
            raise InitialIngressError('failure is not the next paid boundary')

        durable_lineage, control, lifecycle_head = repository.read_lifecycle(
            snapshot.instance, state['receipt_key'])
        if durable_lineage != lineage:
            raise InitialIngressError('changed lifecycle lineage')
        if control is not None:
            committed = True
            exact_duplicate = (control.get('version') == 'reserved-failed-renewal-receipt/1'
                and control.get('event_id') == event_id
                and control.get('raw_digest') == raw_digest
                and control.get('source_evidence_digest') == evidence_digest
                and control.get('paid_head') == paid_head
                and control.get('artifact_shape') == evidence['artifact_shape'])
            if not exact_duplicate:
                repository.record_conflict(snapshot.instance, event_id=event_id,
                    raw_digest=raw_digest, object_key=invoice_id + ':invoice.payment_failed',
                    key=state['receipt_key'])
                return IngressResult('reconciliation_required', True)
            expected = (repository.store_id, control['receipt_id'], control['fact_id'],
                        lifecycle_head)
            if snapshot.recovery == expected and snapshot.lifecycle_head == lifecycle_head:
                return IngressResult('admitted', True, _issue_failed_renewal_fact(
                    authority, repository, snapshot, control, lifecycle_head))
            _, reservation = state['publication']
            if (reservation is None or reservation.get('kind') != attempt
                    or reservation.get('material') != canonical(
                        _failed_renewal_proposal(control))
                    or reservation.get('predecessor') != control['predecessor_lifecycle_head']):
                raise InitialIngressError('durable failed renewal lacks exact reservation')
            receipt, head = control, lifecycle_head
            snapshot = state['publication'][0]
        else:
            if (snapshot.lifecycle_head != paid_head or snapshot.cancellation is not None
                    or snapshot.recovery is not None):
                raise InitialIngressError('obsolete lifecycle head')
            if attempt in state['commit_seen']:
                raise InitialIngressError('consumed uncertain attempt')
            proposal = dict(version='reserved-failed-renewal-receipt/1',
                store=repository.store_id, binding=snapshot.instance, epoch=snapshot.epoch,
                binding_revision=snapshot.revision, owner=state['scope'][0],
                scope=list(state['scope']), endpoint=state['endpoint'], account=state['account'],
                api_version=API_VERSION, livemode=False, receipt_key_id=state['receipt_key_id'],
                signing_key_ids=list(state['signing_key_ids']), event_id=event_id,
                object_key=invoice_id + ':invoice.payment_failed', raw_digest=raw_digest,
                source_evidence_digest=evidence_digest, received_at=received.isoformat(),
                source_created_at=source_time.isoformat(),
                subscription=state['scope'][2], customer=state['customer'], item=state['item'],
                price=state['price'], invoice=invoice_id, line=evidence['line'],
                payment=evidence['payment'], intent=evidence['intent'], charge=evidence['charge'],
                artifact_shape=evidence['artifact_shape'], attempt_count=evidence['attempt_count'],
                amount=evidence['amount'], currency=evidence['currency'], plan=evidence['plan'],
                failed_service_start=evidence['service_start'],
                failed_service_end=evidence['service_end'], paid_sequence=paid['sequence'],
                paid_receipt_id=paid['receipt_id'], paid_fact_id=paid['fact_id'],
                paid_head=paid_head, predecessor_lifecycle_head=snapshot.lifecycle_head,
                disposition='verified_renewal_failure')
            with _LOCK:
                _check(authority, snapshot)
                current, reservation = state['publication']
                if reservation is None:
                    reserved = replace(snapshot, revision=snapshot.revision + 1, consumed=True)
                    reservation = dict(kind=attempt, material=canonical(proposal),
                        predecessor=snapshot.lifecycle_head, revision=reserved.revision)
                    state['publication'] = (reserved, reservation)
                    snapshot = reserved
                else:
                    proposal = json.loads(reservation['material'])
                    snapshot = current
                    if (reservation.get('kind') != attempt
                            or reservation.get('predecessor') != snapshot.lifecycle_head
                            or proposal.get('raw_digest') != raw_digest
                            or proposal.get('event_id') != event_id
                            or proposal.get('source_evidence_digest') != evidence_digest):
                        raise InitialIngressError('different reserved failed renewal')
            predecessor = lineage[-1]

            def admission_clock():
                verified = exact.utc(clock())
                _check(authority, snapshot, verified)
                return verified

            try:
                receipt, head = repository.commit_failed_renewal(
                    proposal, predecessor, state['receipt_key'], admission_clock)
                committed = True
            except CommitOutcomeError as error:
                committed = error.committed
                raise
            except Exception:
                committed = None
                try:
                    _, durable, durable_head = repository.read_lifecycle(
                        snapshot.instance, state['receipt_key'])
                    if (durable is not None
                            and _failed_renewal_proposal(durable) == proposal):
                        committed = True
                        receipt, head = durable, durable_head
                except Exception:
                    pass
                raise
            finally:
                with _LOCK:
                    if committed is not False:
                        state['commit_seen'].add(attempt)
        if repository.read_lifecycle(snapshot.instance, state['receipt_key'])[1:] != (receipt, head):
            raise InitialIngressError('changed committed failed renewal')
        published = publish(snapshot, receipt, head)
        _check(authority, published)
        if repository.read_lifecycle(published.instance, state['receipt_key'])[1:] != (receipt, head):
            raise InitialIngressError('changed failed-renewal publication')
        _accepted_lineage(authority, repository, published)
        _check(authority, published)
        fact = _issue_failed_renewal_fact(authority, repository, published, receipt, head)
        return IngressResult('admitted', True, fact)
    except Exception:
        disposition = ('commit_outcome_unknown' if committed is None else
                       ('committed_but_unadmitted' if committed else 'refused'))
        return IngressResult(disposition, committed)


WITHDRAWAL_FACT_PROTOCOL_VERSION = 'reserved-owner-bound-billing-withdrawal-fact/3.0'
WITHDRAWAL_FACT_ADMISSION_STATUS = 'authoritative_owner_bound_billing_withdrawal_fact_admitted'


def _required_fields(value, names, label):
    if type(value) is not dict or any(name not in value or value[name] is None for name in names):
        raise InitialIngressError('incomplete ' + label)


def _full_refund_projection(state, paid):
    evidence = paid['evidence']
    charge_id = _identifier(evidence['charge'], 'ch')
    intent_id = _identifier(evidence['intent'], 'pi')
    amount = _integer(evidence['amount'])
    if amount <= 0 or evidence['currency'] != 'gbp':
        raise InitialIngressError('invalid paid receipt amount')
    charge = _fetch(state, '/v1/charges/' + charge_id)
    charge_fields = ('id', 'object', 'livemode', 'customer', 'currency',
        'payment_intent', 'status', 'paid', 'captured', 'amount',
        'amount_captured', 'refunded', 'amount_refunded', 'disputed')
    _required_fields(charge, charge_fields, 'withdrawal charge')
    if (charge['id'] != charge_id or charge['object'] != 'charge'
            or charge['livemode'] is not False or charge['customer'] != state['customer']
            or charge['currency'] != evidence['currency']
            or charge['payment_intent'] != intent_id or charge['status'] != 'succeeded'
            or charge['paid'] is not True or charge['captured'] is not True
            or charge['refunded'] is not True or charge['disputed'] is not False):
        raise InitialIngressError('unverified withdrawal charge')
    charge_amounts = tuple(_integer(charge[name]) for name in
                           ('amount', 'amount_captured', 'amount_refunded'))
    if any(value <= 0 for value in charge_amounts) or charge_amounts != (amount,) * 3:
        raise InitialIngressError('withdrawal charge amount mismatch')
    listing = _fetch(state, '/v1/refunds', (('charge', charge_id), ('limit', '100')))
    _required_fields(listing, ('object', 'url', 'has_more', 'data'), 'refund list')
    data = listing['data']
    if (listing['object'] != 'list' or listing['url'] != '/v1/refunds'
            or listing['has_more'] is not False or type(data) is not list
            or not 1 <= len(data) <= 100):
        raise InitialIngressError('incomplete refund enumeration')
    fields = ('id', 'object', 'amount', 'charge', 'payment_intent',
              'currency', 'status', 'balance_transaction')
    projected = []
    total = 0
    identifiers = set()
    for refund in data:
        _required_fields(refund, fields, 'refund')
        refund_id = _identifier(refund['id'], 're')
        if refund_id in identifiers:
            raise InitialIngressError('duplicate refund')
        identifiers.add(refund_id)
        refund_amount = _integer(refund['amount'])
        if (refund_amount <= 0 or refund['object'] != 'refund'
                or refund['charge'] != charge_id or refund['payment_intent'] != intent_id
                or refund['currency'] != evidence['currency']
                or refund['status'] != 'succeeded'
                or type(refund['balance_transaction']) is not str
                or not refund['balance_transaction']):
            raise InitialIngressError('unsupported refund')
        _identifier(refund['balance_transaction'], 'txn')
        total += refund_amount
        if total > amount:
            raise InitialIngressError('refund aggregate exceeds capture')
        projected.append(tuple(refund[name] for name in fields))
    if total != amount:
        raise InitialIngressError('partial refund aggregate')
    projected.sort(key=lambda item: item[0])
    return (tuple(charge[name] for name in charge_fields),
            ('list', '/v1/refunds', False, tuple(projected)))


def _issue_withdrawal_fact(authority, repository, snapshot, receipt, head):
    with _LOCK:
        state = _check(authority, snapshot)
        repository_identity = (repository.store_id, repository.physical_identity)
        expected = (repository_identity, snapshot.revision, head, canonical(receipt))
        cached = state['control_facts'].get('full_withdrawal')
        if cached is not None:
            value, material = cached
            if material != expected:
                raise InitialIngressError('changed full-withdrawal fact cache')
            _WITHDRAWAL_FACTS[value] = (authority, repository, snapshot.revision,
                                        head, canonical(receipt))
            return value
        value = object.__new__(FullWithdrawalFact)
        _WITHDRAWAL_FACTS[value] = (authority, repository, snapshot.revision,
                                    head, canonical(receipt))
        state['control_facts']['full_withdrawal'] = (value, expected)
        return value


def _withdrawal_fact_state(fact):
    with _LOCK:
        if type(fact) is not FullWithdrawalFact or fact not in _WITHDRAWAL_FACTS:
            raise InitialIngressError('not a live full-withdrawal fact')
        authority, repository, revision, head, material = _WITHDRAWAL_FACTS[fact]
    snapshot = authority.snapshot()
    state = _check(authority, snapshot)
    lineage, control, lifecycle_head = repository.read_lifecycle(
        snapshot.instance, state['receipt_key'])
    if (snapshot.revision != revision or snapshot.lifecycle_head != head
            or lifecycle_head != head or control is None
            or control.get('version') != 'reserved-full-withdrawal-receipt/1'
            or canonical(control) != material or not lineage
            or snapshot.withdrawal != (repository.store_id, control['receipt_id'],
                                       control['fact_id'], head)
            or snapshot.recovery is not None):
        raise InitialIngressError('stale full-withdrawal fact')
    _accepted_lineage(authority, repository, snapshot)
    _check(authority, snapshot)
    return state, control, head


def _withdrawal_fact_projection(fact):
    state, control, head = _withdrawal_fact_state(fact)
    transition = exact.utc(datetime.fromisoformat(control['withdrawal_verified_at_utc']))
    material = (WITHDRAWAL_FACT_PROTOCOL_VERSION, WITHDRAWAL_FACT_ADMISSION_STATUS,
        True, True, False, state['scope'][0], state['scope'][1], state['scope'][2],
        control['fact_id'], control['paid_fact_id'], head, 'suspended', False,
        transition, None, 'verified_full_withdrawal', 'current_subscription_period')
    identity_material = tuple(value.isoformat() if type(value) is datetime else value
                              for value in material)
    fact_identity = identity('billing-withdrawal-fact/3', identity_material)
    names = ('protocol_version', 'fact_identity', 'admission_status', 'authenticated',
        'billing_fact_authority', 'provider_observation_direct_authority', 'owner_id',
        'billing_account_id', 'subscription_id', 'source_fact_id',
        'predecessor_paid_fact_id', 'lifecycle_head', 'state', 'ordinary_access',
        'transition_effective_at_utc', 'recovery_deadline_exclusive_at_utc',
        'derivation_kind', 'withdrawal_attribution')
    return tuple(zip(names, (material[0], fact_identity, *material[1:]), strict=True))


def validate_full_withdrawal_fact(fact):
    return _withdrawal_fact_projection(fact)


def project_full_withdrawal_fact(fact):
    return _withdrawal_fact_projection(fact)


def full_withdrawal_fact_details(fact):
    _, control, head = _withdrawal_fact_state(fact)
    return dict(disposition=control['disposition'], source_shape=control['source_shape'],
        withdrawal_verified_at_utc=control['withdrawal_verified_at_utc'],
        paid_service_start=control['paid_service_start'],
        paid_service_end=control['paid_service_end'], refunds=tuple(control['refunds']),
        paid_receipt_id=control['paid_receipt_id'], paid_fact_id=control['paid_fact_id'],
        receipt_id=control['receipt_id'], fact_id=control['fact_id'], lifecycle_head=head)


_WITHDRAWAL_ADMISSION_FIELDS = frozenset({
    'withdrawal_verified_at_utc', 'receipt_id', 'fact_id',
})


def _withdrawal_proposal(receipt):
    return {name: value for name, value in receipt.items()
            if name not in _WITHDRAWAL_ADMISSION_FIELDS}


def ingest_full_withdrawal(authority, repository, raw_body, signature_header, *, clock):
    """Admit only the closed successful-full-refund shape."""
    def publish(snapshot, receipt, head):
        with _LOCK:
            state = _check(authority, snapshot)
            current, reservation = state['publication']
            accepted = (repository.store_id, receipt['receipt_id'], receipt['fact_id'], head)
            if (current != snapshot or reservation is None
                    or reservation.get('kind') != 'full_withdrawal'
                    or reservation.get('material') != canonical(_withdrawal_proposal(receipt))
                    or reservation.get('revision') != snapshot.revision
                    or reservation.get('predecessor') != receipt['predecessor_lifecycle_head']):
                raise InitialIngressError('changed full-withdrawal reservation')
            published = replace(snapshot, revision=snapshot.revision + 1, consumed=True,
                                lifecycle_head=head, withdrawal=accepted)
            state['publication'] = (published, None)
            return published

    committed = False
    attempt = 'full_withdrawal'
    conflict = None
    try:
        if is_production_environment():
            raise InitialIngressError('local bounded lifecycle only')
        snapshot = authority.snapshot()
        received = exact.utc(clock())
        state = _check(authority, snapshot, received)
        if (type(repository) is not ProvenanceRepository
                or repository.store_id != state['store']
                or repository.physical_identity != state['physical']):
            raise InitialIngressError('wrong store')
        for _ in range(2):
            if not _verified_signature(raw_body, signature_header, state, received):
                raise InitialIngressError('signature refusal')
        event = _parse(raw_body)
        if (event.get('object') != 'event' or event.get('livemode') is not False
                or event.get('api_version') != API_VERSION or event.get('account') is not None):
            raise InitialIngressError('unsupported full-withdrawal event')
        event_id = _identifier(event.get('id'), 'evt')
        source_time = _timestamp(event.get('created'))
        if source_time > received:
            raise InitialIngressError('future source event')
        data = event.get('data')
        if type(data) is not dict or type(data.get('object')) is not dict:
            raise InitialIngressError('wrong full-withdrawal event object')
        if event.get('type') != 'charge.refunded':
            unresolved = frozenset({
                'refund.created', 'refund.updated', 'refund.failed',
                'charge.dispute.created', 'charge.dispute.updated',
                'charge.dispute.closed', 'charge.dispute.funds_withdrawn',
                'charge.dispute.funds_reinstated',
            })
            if event.get('type') not in unresolved:
                raise InitialIngressError('unsupported full-withdrawal event')
            object_id = _identifier(data['object'].get('id'))
            repository.record_conflict(snapshot.instance, event_id=event_id,
                raw_digest=hashlib.sha256(raw_body).hexdigest(),
                object_key=object_id + ':' + event['type'], key=state['receipt_key'])
            return IngressResult('reconciliation_required', True)
        trigger = data['object']
        if (trigger.get('object') != 'charge' or trigger.get('livemode') is not False):
            raise InitialIngressError('wrong full-withdrawal trigger')
        charge_id = _identifier(trigger.get('id'), 'ch')
        raw_digest = hashlib.sha256(raw_body).hexdigest()
        object_key = charge_id + ':charge.refunded'
        reconciled = repository.read_conflict(snapshot.instance, event_id=event_id,
                                              key=state['receipt_key'])
        if reconciled is not None:
            if (reconciled['raw_digest'] != raw_digest
                    or reconciled['object_key'] != object_key):
                raise InitialIngressError('changed reconciled withdrawal event')
            return IngressResult('reconciliation_required', True)
        lineage = _lineage(authority, repository, snapshot)
        if not lineage:
            raise InitialIngressError('missing accepted paid predecessor')
        paid, paid_head = lineage[-1]
        if snapshot.accepted != (repository.store_id, paid['receipt_id'],
                                 paid['fact_id'], paid_head):
            raise InitialIngressError('obsolete authentic paid predecessor')
        if charge_id != paid['evidence']['charge']:
            if any(charge_id == receipt['evidence']['charge']
                   for receipt, _ in lineage[:-1]):
                repository.record_conflict(snapshot.instance, event_id=event_id,
                    raw_digest=raw_digest, object_key=object_key,
                    key=state['receipt_key'])
                return IngressResult('reconciliation_required', True)
            raise InitialIngressError('event is not current paid charge')
        conflict = (snapshot.instance, event_id, raw_digest,
                    object_key, state['receipt_key'])
        durable_lineage, controls, lifecycle_head = repository.read_lifecycle_chain(
            snapshot.instance, state['receipt_key'])
        if durable_lineage != lineage:
            raise InitialIngressError('changed lifecycle lineage')
        current = controls[-1] if controls else None
        if current is not None and current.get('version') == 'reserved-full-withdrawal-receipt/1':
            committed = True
            if (current.get('event_id') != event_id or current.get('raw_digest') != raw_digest):
                repository.record_conflict(snapshot.instance, event_id=event_id,
                    raw_digest=raw_digest, object_key=charge_id + ':charge.refunded',
                    key=state['receipt_key'])
                return IngressResult('reconciliation_required', True)
            expected = (repository.store_id, current['receipt_id'], current['fact_id'], lifecycle_head)
            if snapshot.withdrawal == expected and snapshot.lifecycle_head == lifecycle_head:
                return IngressResult('admitted', True, _issue_withdrawal_fact(
                    authority, repository, snapshot, current, lifecycle_head))
            _, reservation = state['publication']
            if (reservation is None or reservation.get('kind') != attempt
                    or reservation.get('material') != canonical(_withdrawal_proposal(current))):
                raise InitialIngressError('durable withdrawal lacks exact reservation')
            receipt, head = current, lifecycle_head
            snapshot = state['publication'][0]
        else:
            if attempt in state['commit_seen']:
                conflict = None
                raise InitialIngressError('consumed uncertain full-withdrawal attempt')
            if (current is not None and current.get('version') !=
                    'reserved-scheduled-cancellation-receipt/1'):
                repository.record_conflict(snapshot.instance, event_id=event_id,
                    raw_digest=raw_digest, object_key=charge_id + ':charge.refunded',
                    key=state['receipt_key'])
                return IngressResult('reconciliation_required', True)
            if (snapshot.lifecycle_head != lifecycle_head or snapshot.recovery is not None
                    or snapshot.withdrawal is not None):
                raise InitialIngressError('obsolete lifecycle head')
            first = _full_refund_projection(state, paid)
            second = _full_refund_projection(state, paid)
            if first != second:
                raise InitialIngressError('changed full-withdrawal observations')
            charge_projection, refund_projection = first
            refund_ids = [item[0] for item in refund_projection[3]]
            evidence_digest = hashlib.sha256(canonical(first)).hexdigest()
            proposal = dict(version='reserved-full-withdrawal-receipt/1',
                store=repository.store_id, binding=snapshot.instance, epoch=snapshot.epoch,
                binding_revision=snapshot.revision, owner=state['scope'][0],
                scope=list(state['scope']), endpoint=state['endpoint'], account=state['account'],
                api_version=API_VERSION, livemode=False, receipt_key_id=state['receipt_key_id'],
                signing_key_ids=list(state['signing_key_ids']), event_id=event_id,
                object_key=charge_id + ':charge.refunded', raw_digest=raw_digest,
                source_evidence_digest=evidence_digest, received_at=received.isoformat(),
                source_created_at=source_time.isoformat(), subscription=state['scope'][2],
                customer=state['customer'], invoice=paid['evidence']['invoice'],
                line=paid['evidence']['line'], payment=paid['evidence']['payment'],
                intent=paid['evidence']['intent'], charge=charge_id, refunds=refund_ids,
                amount=paid['evidence']['amount'], currency=paid['evidence']['currency'],
                paid_sequence=paid['sequence'], paid_receipt_id=paid['receipt_id'],
                paid_fact_id=paid['fact_id'], paid_head=paid_head,
                predecessor_lifecycle_head=lifecycle_head,
                paid_service_start=paid['evidence']['service_start'],
                paid_service_end=paid['service_end'], source_shape='successful_full_refund',
                disposition='verified_full_withdrawal')
            with _LOCK:
                _check(authority, snapshot)
                current_snapshot, reservation = state['publication']
                if reservation is None:
                    reserved = replace(snapshot, revision=snapshot.revision + 1, consumed=True)
                    reservation = dict(kind=attempt, material=canonical(proposal),
                        predecessor=lifecycle_head, revision=reserved.revision)
                    state['publication'] = (reserved, reservation)
                    snapshot = reserved
                else:
                    proposal = json.loads(reservation['material'])
                    snapshot = current_snapshot
                    if (reservation.get('kind') != attempt
                            or reservation.get('predecessor') != lifecycle_head
                            or proposal.get('event_id') != event_id
                            or proposal.get('raw_digest') != raw_digest
                            or proposal.get('source_evidence_digest') != evidence_digest):
                        raise InitialIngressError('different reserved full withdrawal')

            def admission_clock():
                verified = exact.utc(clock())
                _check(authority, snapshot, verified)
                return verified

            predecessor = (lineage[-1], lifecycle_head, current)
            try:
                receipt, head = repository.commit_full_withdrawal(
                    proposal, predecessor, state['receipt_key'], admission_clock)
                committed = True
            except CommitOutcomeError as error:
                committed = error.committed
                raise
            except Exception:
                committed = None
                try:
                    _, durable, durable_head = repository.read_lifecycle(
                        snapshot.instance, state['receipt_key'])
                    if durable is not None and _withdrawal_proposal(durable) == proposal:
                        committed = True
                        receipt, head = durable, durable_head
                except Exception:
                    pass
                raise
            finally:
                with _LOCK:
                    if committed is not False:
                        state['commit_seen'].add(attempt)
        if repository.read_lifecycle(snapshot.instance, state['receipt_key'])[1:] != (receipt, head):
            raise InitialIngressError('changed committed full withdrawal')
        published = publish(snapshot, receipt, head)
        _check(authority, published)
        if repository.read_lifecycle(published.instance, state['receipt_key'])[1:] != (receipt, head):
            raise InitialIngressError('changed full-withdrawal publication')
        _accepted_lineage(authority, repository, published)
        fact = _issue_withdrawal_fact(authority, repository, published, receipt, head)
        return IngressResult('admitted', True, fact)
    except Exception:
        if committed is False and conflict is not None:
            try:
                binding, event_id, raw_digest, object_key, key = conflict
                repository.record_conflict(binding, event_id=event_id,
                    raw_digest=raw_digest, object_key=object_key, key=key)
                return IngressResult('reconciliation_required', True)
            except Exception:
                pass
        disposition = ('commit_outcome_unknown' if committed is None else
                       ('committed_but_unadmitted' if committed else 'refused'))
        return IngressResult(disposition, committed)


RESTORATION_FACT_PROTOCOL_VERSION = (
    'reserved-owner-bound-billing-later-period-restoration-fact/1.0')
RESTORATION_FACT_ADMISSION_STATUS = (
    'authoritative_owner_bound_later_period_restoration_fact_admitted')


def _restoration_proposal(receipt):
    return {name: value for name, value in receipt.items() if name not in {
        'restoration_verified_at_utc', 'access_start', 'receipt_id', 'fact_id'}}


def _issue_restoration_fact(authority, repository, snapshot, receipt, head):
    with _LOCK:
        state = _check(authority, snapshot)
        expected = ((repository.store_id, repository.physical_identity),
                    snapshot.revision, head, canonical(receipt))
        cached = state['control_facts'].get('later_period_restoration')
        if cached is not None:
            value, material = cached
            if material != expected:
                raise InitialIngressError('changed restoration fact cache')
            _RESTORATION_FACTS[value] = (authority, repository,
                snapshot.revision, head, canonical(receipt))
            return value
        value = object.__new__(LaterPeriodRestorationFact)
        _RESTORATION_FACTS[value] = (authority, repository, snapshot.revision,
                                     head, canonical(receipt))
        state['control_facts']['later_period_restoration'] = (value, expected)
        return value


def _restoration_fact_state(fact):
    with _LOCK:
        if (type(fact) is not LaterPeriodRestorationFact
                or fact not in _RESTORATION_FACTS):
            raise InitialIngressError('not a live later-period restoration fact')
        authority, repository, revision, head, material = _RESTORATION_FACTS[fact]
    snapshot = authority.snapshot()
    state = _check(authority, snapshot)
    lineage, controls, lifecycle_head = repository.read_lifecycle_chain(
        snapshot.instance, state['receipt_key'])
    receipt = lineage[-1][0] if lineage else None
    if (snapshot.revision != revision or snapshot.lifecycle_head != head
            or lifecycle_head != head or len(lineage) != 2 or len(controls) != 1
            or receipt is None
            or receipt.get('version') !=
                'reserved-later-period-restoration-receipt/1'
            or canonical(receipt) != material
            or controls[0].get('version') !=
                'reserved-full-withdrawal-receipt/1'
            or snapshot.withdrawal is not None or snapshot.recovery is not None
            or snapshot.cancellation is not None
            or snapshot.accepted != (repository.store_id, receipt['receipt_id'],
                                     receipt['fact_id'], head)):
        raise InitialIngressError('stale later-period restoration fact')
    _accepted_lineage(authority, repository, snapshot)
    _check(authority, snapshot)
    return state, receipt, controls[0], head


def _restoration_fact_projection(fact):
    state, receipt, withdrawal, head = _restoration_fact_state(fact)
    verified = exact.utc(datetime.fromisoformat(
        receipt['restoration_verified_at_utc']))
    service_start = exact.utc(datetime.fromisoformat(receipt['service_start']))
    access_start = exact.utc(datetime.fromisoformat(receipt['access_start']))
    service_end = exact.utc(datetime.fromisoformat(receipt['service_end']))
    material = (
        RESTORATION_FACT_PROTOCOL_VERSION, RESTORATION_FACT_ADMISSION_STATUS,
        True, True, False, state['scope'][0], state['scope'][1],
        state['scope'][2], receipt['fact_id'], receipt['predecessor_fact_id'],
        withdrawal['fact_id'], head, 'paid', True, service_start, access_start,
        service_end, verified, 'verified_later_period_restoration', 2,
    )
    identity_material = tuple(value.isoformat() if type(value) is datetime else value
                              for value in material)
    fact_identity = identity('billing-later-period-restoration-fact/1',
                             identity_material)
    names = (
        'protocol_version', 'fact_identity', 'admission_status',
        'authenticated', 'billing_fact_authority',
        'provider_observation_direct_authority', 'owner_id',
        'billing_account_id', 'subscription_id', 'source_fact_id',
        'predecessor_paid_fact_id', 'withdrawal_fact_id', 'lifecycle_head',
        'state', 'ordinary_access', 'service_start_utc', 'access_start_utc',
        'service_end_exclusive_utc', 'restoration_verified_at_utc',
        'derivation_kind', 'paid_sequence',
    )
    return tuple(zip(names, (material[0], fact_identity, *material[1:]),
                     strict=True))


def validate_later_period_restoration_fact(fact):
    return _restoration_fact_projection(fact)


def project_later_period_restoration_fact(fact):
    return _restoration_fact_projection(fact)


def later_period_restoration_fact_details(fact):
    _, receipt, withdrawal, head = _restoration_fact_state(fact)
    return dict(disposition=receipt['disposition'],
        restoration_verified_at_utc=receipt['restoration_verified_at_utc'],
        access_start=receipt['access_start'], service_start=receipt['service_start'],
        service_end=receipt['service_end'], receipt_id=receipt['receipt_id'],
        fact_id=receipt['fact_id'], lifecycle_head=head,
        withdrawal_receipt_id=withdrawal['receipt_id'],
        withdrawal_fact_id=withdrawal['fact_id'])


def ingest_later_period_restoration(authority, repository, raw_body,
                                    signature_header, *, clock):
    """Admit only the exact sequence-two paid period after sequence-one withdrawal."""
    def publish(snapshot, receipt, head):
        with _LOCK:
            state = _check(authority, snapshot)
            current, reservation = state['publication']
            accepted = (repository.store_id, receipt['receipt_id'],
                        receipt['fact_id'], head)
            if (current != snapshot or reservation is None
                    or reservation.get('kind') != 'later_period_restoration'
                    or reservation.get('material') !=
                        canonical(_restoration_proposal(receipt))
                    or reservation.get('revision') != snapshot.revision
                    or reservation.get('predecessor') !=
                        receipt['predecessor_lifecycle_head']):
                raise InitialIngressError('changed restoration reservation')
            published = replace(snapshot, revision=snapshot.revision + 1,
                consumed=True, accepted=accepted, lifecycle_head=head,
                cancellation=None, recovery=None, withdrawal=None)
            state['publication'] = (published, None)
            return published

    committed = False
    conflict = None
    attempt = 'later_period_restoration'
    known_rollback = False
    reserved_retry = False
    try:
        if is_production_environment():
            raise InitialIngressError('local bounded lifecycle only')
        snapshot = authority.snapshot()
        state = _check(authority, snapshot)
        if (type(repository) is not ProvenanceRepository
                or repository.store_id != state['store']
                or repository.physical_identity != state['physical']):
            raise InitialIngressError('wrong store')

        # Exact durable replay rechecks its bounded HMAC at the signed header's
        # own instant. It does not consult the caller clock, refetch provider
        # state, or create a later observation that could prolong access.
        replay_lineage, _, _ = repository.read_lifecycle_chain(
            snapshot.instance, state['receipt_key'])
        replay_digest = hashlib.sha256(raw_body).hexdigest()
        if (len(replay_lineage) == 2
                and replay_lineage[-1][0].get('version') ==
                    'reserved-later-period-restoration-receipt/1'
                and replay_lineage[-1][0].get('raw_digest') == replay_digest):
            receipt, head = replay_lineage[-1]
            timestamp_values = ([] if type(signature_header) is not str else
                [part[2:] for part in signature_header.split(',')
                 if part.startswith('t=')])
            replay_signature_time = (int(timestamp_values[0])
                if len(timestamp_values) == 1
                and re.fullmatch(r'[0-9]{1,16}', timestamp_values[0]) else -1)
            replay_observed = datetime.fromtimestamp(
                max(replay_signature_time, 0), timezone.utc)
            for _ in range(2):
                if not _verified_signature(raw_body, signature_header, state,
                                           replay_observed):
                    raise InitialIngressError('signature refusal')
            committed = True
            replay_event = _parse(raw_body)
            replay_data = replay_event.get('data')
            replay_trigger = (replay_data.get('object')
                              if type(replay_data) is dict else None)
            if (replay_event.get('id') != receipt['event_id']
                    or type(replay_trigger) is not dict
                    or replay_trigger.get('id') != receipt['evidence']['invoice']
                    or receipt['object_key'] !=
                        receipt['evidence']['invoice'] +
                        ':invoice.payment_succeeded'):
                raise InitialIngressError('changed restoration replay')
            accepted = (repository.store_id, receipt['receipt_id'],
                        receipt['fact_id'], head)
            if (snapshot.accepted != accepted or snapshot.lifecycle_head != head
                    or snapshot.withdrawal is not None):
                current, reservation = state['publication']
                if (current != snapshot or reservation is None
                        or reservation.get('kind') != attempt
                        or reservation.get('material') !=
                            canonical(_restoration_proposal(receipt))
                        or reservation.get('predecessor') !=
                            receipt['predecessor_lifecycle_head']):
                    raise InitialIngressError('durable restoration not published')
                snapshot = publish(snapshot, receipt, head)
            return IngressResult('admitted', True, _issue_restoration_fact(
                authority, repository, snapshot, receipt, head))

        received = exact.utc(clock())
        state = _check(authority, snapshot, received)
        for _ in range(2):
            if not _verified_signature(raw_body, signature_header, state, received):
                raise InitialIngressError('signature refusal')
        event = _parse(raw_body)
        if (event.get('object') != 'event' or event.get('livemode') is not False
                or event.get('api_version') != API_VERSION
                or event.get('account') is not None):
            raise InitialIngressError('unsupported restoration event')
        event_id = _identifier(event.get('id'), 'evt')
        source_time = _timestamp(event.get('created'))
        if source_time > received:
            raise InitialIngressError('future source event')
        data = event.get('data')
        trigger = data.get('object') if type(data) is dict else None
        if type(trigger) is not dict:
            raise InitialIngressError('wrong restoration event object')
        if event.get('type') != 'invoice.payment_succeeded':
            raise InitialIngressError('unsupported restoration trigger')
        invoice_id = _identifier(trigger.get('id'), 'in')
        if (trigger.get('object') != 'invoice' or trigger.get('livemode') is not False
                or trigger.get('customer') != state['customer']
                or trigger.get('status') != 'paid'
                or trigger.get('billing_reason') != 'subscription_cycle'
                or type(trigger.get('parent')) is not dict
                or trigger['parent'].get('type') != 'subscription_details'
                or type(trigger['parent'].get('subscription_details')) is not dict
                or trigger['parent']['subscription_details'].get('subscription') !=
                    state['scope'][2]):
            raise InitialIngressError('restoration trigger scope mismatch')
        raw_digest = hashlib.sha256(raw_body).hexdigest()
        object_key = invoice_id + ':invoice.payment_succeeded'
        reconciliations = repository.read_conflicts(
            snapshot.instance, key=state['receipt_key'])
        event_matches = tuple(item for item in reconciliations
                              if item['event_id'] == event_id)
        if len(event_matches) > 1:
            raise InitialIngressError('ambiguous restoration reconciliation')
        reconciled = event_matches[0] if event_matches else None
        if reconciled is not None:
            if (reconciled['raw_digest'] != raw_digest
                    or reconciled['object_key'] != object_key):
                raise InitialIngressError('changed reconciled restoration event')
            return IngressResult('reconciliation_required', True)
        if any(item['object_key'] == object_key
               and item['event_id'] != event_id for item in reconciliations):
            raise InitialIngressError('consumed restoration object')

        lineage, controls, lifecycle_head = repository.read_lifecycle_chain(
            snapshot.instance, state['receipt_key'])
        if (len(lineage) == 2
                and lineage[-1][0].get('version') ==
                    'reserved-later-period-restoration-receipt/1'):
            committed = True
            receipt, head = lineage[-1]
            if (receipt.get('event_id') != event_id
                    or receipt.get('raw_digest') != raw_digest
                    or receipt.get('object_key') != object_key):
                repository.record_conflict(snapshot.instance, event_id=event_id,
                    raw_digest=raw_digest, object_key=object_key,
                    key=state['receipt_key'])
                return IngressResult('reconciliation_required', True)
            accepted = (repository.store_id, receipt['receipt_id'],
                        receipt['fact_id'], head)
            if (snapshot.accepted != accepted or snapshot.lifecycle_head != head
                    or snapshot.withdrawal is not None):
                current, reservation = state['publication']
                if (current != snapshot or reservation is None
                        or reservation.get('kind') != attempt
                        or reservation.get('material') !=
                            canonical(_restoration_proposal(receipt))
                        or reservation.get('predecessor') !=
                            receipt['predecessor_lifecycle_head']):
                    raise InitialIngressError('durable restoration not published')
                snapshot = publish(snapshot, receipt, head)
            return IngressResult('admitted', True, _issue_restoration_fact(
                authority, repository, snapshot, receipt, head))

        if (len(lineage) != 1 or len(controls) != 1
                or controls[0].get('version') !=
                    'reserved-full-withdrawal-receipt/1'
                or controls[0].get('paid_sequence') != 1
                or lifecycle_head != _control_head(controls[0])
                or snapshot.accepted != (repository.store_id,
                    lineage[0][0]['receipt_id'], lineage[0][0]['fact_id'],
                    lineage[0][1])
                or snapshot.lifecycle_head != lifecycle_head
                or snapshot.withdrawal != (repository.store_id,
                    controls[0]['receipt_id'], controls[0]['fact_id'], lifecycle_head)
                or snapshot.cancellation is not None or snapshot.recovery is not None):
            raise InitialIngressError('exact withdrawn predecessor unavailable')
        if any(item[0].get('event_id') == event_id for item in lineage) or any(
                item.get('event_id') == event_id for item in controls):
            raise InitialIngressError('consumed restoration event')
        with _LOCK:
            _check(authority, snapshot)
            existing_reservation = state['publication'][1]
            reserved_retry = (existing_reservation is not None
                              and existing_reservation.get('kind') == attempt)
        conflict = (snapshot.instance, event_id, raw_digest, object_key,
                    state['receipt_key'])
        evidence, observations = _reconcile(state, invoice_id,
            'subscription_cycle', event_created=source_time,
            exact_projection=True)
        checked_evidence, checked_observations = _reconcile(state, invoice_id,
            'subscription_cycle', event_created=source_time,
            exact_projection=True)
        if (evidence, observations) != (checked_evidence, checked_observations):
            raise InitialIngressError('changed restoration source observations')
        paid, paid_head = lineage[0]
        service_start = datetime.fromisoformat(evidence['service_start'])
        service_end = datetime.fromisoformat(evidence['service_end'])
        if (service_start != datetime.fromisoformat(paid['service_end'])
                or service_end != _approved_period_end(service_start, state['plan'])):
            raise InitialIngressError('wrong later paid period')
        historical_ids = set()
        for item in lineage:
            historical_ids.update(item[0]['evidence'][name] for name in
                                  ('invoice', 'line', 'payment', 'intent', 'charge'))
        historical_ids.update(controls[0].get(name) for name in
                              ('invoice', 'line', 'payment', 'intent', 'charge'))
        if any(evidence[name] in historical_ids for name in
               ('invoice', 'line', 'payment', 'intent', 'charge')):
            raise InitialIngressError('reused restoration source identity')
        proposal = dict(
            version='reserved-later-period-restoration-receipt/1',
            store=repository.store_id, binding=snapshot.instance,
            epoch=snapshot.epoch, binding_revision=snapshot.revision,
            owner=state['scope'][0], scope=list(state['scope']),
            endpoint=state['endpoint'], account=state['account'],
            api_version=API_VERSION, livemode=False,
            receipt_key_id=state['receipt_key_id'],
            signing_key_ids=list(state['signing_key_ids']), event_id=event_id,
            object_key=object_key, raw_digest=raw_digest,
            source_evidence_digest=hashlib.sha256(observations).hexdigest(),
            received_at=received.isoformat(), source_created_at=source_time.isoformat(),
            evidence=evidence, service_start=evidence['service_start'],
            service_end=evidence['service_end'], sequence=2, predecessor=1,
            predecessor_receipt_id=paid['receipt_id'],
            predecessor_fact_id=paid['fact_id'], predecessor_head=paid_head,
            withdrawal_receipt_id=controls[0]['receipt_id'],
            withdrawal_fact_id=controls[0]['fact_id'],
            withdrawal_head=lifecycle_head,
            predecessor_lifecycle_head=lifecycle_head,
            disposition='verified_later_period_restoration')
        with _LOCK:
            _check(authority, snapshot)
            current, reservation = state['publication']
            if reservation is None:
                reserved = replace(snapshot, revision=snapshot.revision + 1,
                                   consumed=True)
                reservation = dict(kind=attempt, material=canonical(proposal),
                    predecessor=lifecycle_head, revision=reserved.revision)
                state['publication'] = (reserved, reservation)
                snapshot = reserved
            else:
                reserved_retry = True
                proposal = json.loads(reservation['material'])
                snapshot = current
                if (reservation.get('kind') != attempt
                        or reservation.get('predecessor') != lifecycle_head
                        or proposal.get('event_id') != event_id
                        or proposal.get('raw_digest') != raw_digest
                        or proposal.get('source_evidence_digest') !=
                            hashlib.sha256(observations).hexdigest()):
                    raise InitialIngressError('different reserved restoration')

        def admission_clock():
            verified = exact.utc(clock())
            _check(authority, snapshot, verified)
            return verified

        predecessor = (lineage[0], controls[0], lifecycle_head)
        try:
            receipt, head = repository.commit_later_period_restoration(
                proposal, predecessor, state['receipt_key'], admission_clock)
            committed = True
        except CommitOutcomeError as error:
            committed = error.committed
            known_rollback = committed is False
            raise
        except Exception:
            committed = None
            exact_durable_successor = False
            try:
                durable = repository.read_sequence(snapshot.instance, 2,
                                                   state['receipt_key'])
                if (durable is not None
                        and _restoration_proposal(durable[0]) == proposal):
                    receipt, head = durable
                    committed = True
                    exact_durable_successor = True
            except Exception:
                pass
            if not exact_durable_successor:
                repository._poison_unproven_outcome()
            raise
        finally:
            with _LOCK:
                if committed is not False:
                    state['commit_seen'].add(attempt)
        if repository.read_sequence(snapshot.instance, 2,
                                    state['receipt_key']) != (receipt, head):
            raise InitialIngressError('changed committed restoration')
        published = publish(snapshot, receipt, head)
        _check(authority, published)
        if _accepted_lineage(authority, repository, published)[-1] != (receipt, head):
            raise InitialIngressError('changed restoration publication')
        return IngressResult('admitted', True, _issue_restoration_fact(
            authority, repository, published, receipt, head))
    except Exception:
        if (committed is False and conflict is not None
                and not known_rollback and not reserved_retry):
            try:
                binding, event_id, raw_digest, object_key, key = conflict
                repository.record_conflict(binding, event_id=event_id,
                    raw_digest=raw_digest, object_key=object_key, key=key)
                return IngressResult('reconciliation_required', True)
            except Exception:
                pass
        disposition = ('commit_outcome_unknown' if committed is None else
                       ('committed_but_unadmitted' if committed else 'refused'))
        return IngressResult(disposition, committed)
