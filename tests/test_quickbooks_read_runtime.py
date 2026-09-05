"""Synthetic executed request tests; no live authentication or provider access."""
from base64 import b64encode
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
from urllib.parse import parse_qs, urlsplit

import pytest

from reserved.providers.accounting import quickbooks_read_runtime as rt
from reserved.providers.accounting import quickbooks_oauth_contract as oauth
from reserved.providers.accounting.quickbooks_observation_contract import observe_invoice
from reserved.providers.accounting.contracts import CompletenessState
from reserved.providers.import_evidence import FitnessStatus
from reserved.providers.http_boundary import ProviderResponse, HttpMethod
from reserved.providers.oauth_contracts import CredentialReference
from reserved.providers.oauth_security import OAuthStateStore

NOW = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)
REF = CredentialReference("quickbooks", "fixture-vault-1")
OWNER = "fixture-owner"
REALM = "1234567890"
REDIRECT = "https://reserved.example.test/callback"
STATE = "synthetic-state-not-a-credential"


def token_payload(suffix="one"):
    return dict(access_token="synthetic-access-" + suffix,
                refresh_token="synthetic-refresh-" + suffix, expires_in=3600,
                x_refresh_token_expires_in=86400, token_type="bearer",
                x_refresh_token_hard_expires_in=172800, id_token="documented-additive-field")


def invoice(identity="inv-1"):
    # Full observation, not precomputed evidence or a canonical mapping fixture.
    return {"Id": identity, "SyncToken": "3", "CustomerRef": {"value": "customer-1"},
            "TxnDate": "2026-09-01", "DueDate": "2026-09-30", "CurrencyRef": {"value": "GBP"},
            "GlobalTaxCalculation": "TaxExcluded", "TotalAmt": "12.30", "Balance": "2.30",
            "TxnTaxDetail": {"TotalTax": "2.05"},
            "MetaData": {"LastUpdatedTime": "2026-09-01T10:00:00+01:00"},
            "Line": [{"Id": "line-1", "Amount": "10.25", "DetailType": "SalesItemLineDetail",
                      "SalesItemLineDetail": {"ItemRef": {"value": "item-1"}, "Qty": 1, "UnitPrice": "10.25"}}],
            "PrivateNote": "synthetic-private-body"}


def company():
    return {"CompanyInfo": {"Id": "1", "SyncToken": "0", "CompanyName": "Synthetic Limited", "Country": "United Kingdom"},
            "time": "2026-09-05T05:00:00-07:00"}


def page(records, start=1, metadata=True):
    query = {"Invoice": records}
    if metadata:
        query.update(startPosition=start, maxResults=len(records), totalCount=len(records))
    return {"QueryResponse": query, "time": "2026-09-05T05:00:01-07:00"}


def response(payload, *, headers=None, status=200):
    return ProviderResponse(status, headers or {"Content-Type": "application/json;charset=UTF-8",
        "Date": "Sat, 05 Sep 2026 12:00:00 GMT", "Cache-Control": "max-age=0, no-cache, no-store",
        "QBO-Version": "fixture", "intuit_tid": "synthetic-trace"},
        payload if type(payload) is bytes else json.dumps(payload).encode())


class Fixture:
    def __init__(self, state="active"):
        self.now = NOW
        self.binding = rt.FixtureBinding(OWNER, REALM, REF, 1, state, NOW + timedelta(days=1))
        self.record = rt.FixtureTokenRecord(oauth.parse_token_response(token_payload()), NOW, 1)
        self.responses = []
        self.requests = []
        self.events = []
        self.hook = lambda event: None
        self.runtime = rt.InjectedQuickBooksRuntime(transport=self, custody=self,
            binding_source=self, clock=self.clock, environment="injected_test")
        self.writes = []

    def event(self, label):
        self.events.append(label)
        self.hook(label)

    def clock(self):
        self.event("clock")
        return self.now

    def resolve(self, reference):
        self.event("resolve")
        assert reference == REF
        return self.binding

    def basic_authorization(self):
        self.event("basic")
        return "Basic " + b64encode(b"synthetic-client:synthetic-secret").decode()

    def load(self, credential, *, expected_revision):
        self.event("load")
        assert credential == REF and expected_revision == self.binding.revision
        return self.record

    def put(self, **kwargs):
        return self.store("put", **kwargs)

    def replace(self, **kwargs):
        return self.store("replace", **kwargs)

    def store(self, method, *, credential, expected_binding, tokens, received_at):
        self.event("before_" + method)
        assert expected_binding == self.binding and credential == REF
        assert type(tokens) is oauth.QuickBooksTokenSet
        self.writes.append((method, tokens))
        self.binding = replace(self.binding, revision=self.binding.revision + 1, state="active")
        self.record = rt.FixtureTokenRecord(tokens, received_at, self.binding.revision)
        self.event("after_" + method)
        return REF

    def send(self, request):
        self.requests.append(request)
        self.event("send")
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def acquire(self):
        return self.runtime.acquire(credential=REF, owner_id=OWNER, request_identity="run-1")

    def refresh(self):
        return self.runtime.refresh(credential=REF, owner_id=OWNER)

    def callback(self, *, parameters=None, state_store=None):
        return self.runtime.complete_callback(credential=REF, owner_id=OWNER,
            parameters=parameters if parameters is not None else {"code": "synthetic-code", "state": STATE, "realmId": REALM},
            state_store=state_store or states(), redirect_uri=REDIRECT)


def states(provider="quickbooks", issued=NOW):
    # Seed a synthetic fixture; do not generate credentials or contact a provider.
    return OAuthStateStore({OAuthStateStore.KEY: {provider: {
        "digest": sha256(STATE.encode()).hexdigest(), "issued_at": int(issued.timestamp())}}}, ttl_seconds=300)


def assert_refused(result):
    assert result.status.endswith("refused")
    assert result.company is None and result.query_evidence is None and result.pages == ()
    assert result.credential is None and result.binding is None
    assert result.company_wire_digest is None and result.started_at is None
    text = repr(result) + repr(result.diagnostic_summary())
    for private in (OWNER, REALM, REF.reference, "synthetic-access", "synthetic-refresh", "synthetic-code", "synthetic-private-body"):
        assert private not in text


def test_full_executed_callback_rotation_company_multipage_chain(monkeypatch):
    fixture = Fixture("pending")
    fixture.responses = [response(token_payload()), response(token_payload("two")), response(company()),
        response(page([invoice(str(i)) for i in range(rt.PAGE_SIZE)])),
        response(page([invoice("last")], 26))]
    callback = fixture.callback()
    assert callback.status == "reference_stored" and callback.credential == REF
    assert fixture.record.tokens.x_refresh_token_expires_in == 86400
    assert fixture.record.tokens.x_refresh_token_hard_expires_in == 172800
    assert fixture.refresh().status == "reference_rotated"
    assert fixture.record.tokens.refresh_token == "synthetic-refresh-two"
    calls = []
    original = rt.validate_query_run
    def spy(*args, **kwargs):
        calls.append((args, kwargs))
        return original(*args, **kwargs)
    monkeypatch.setattr(rt, "validate_query_run", spy)
    result = fixture.acquire()
    assert result.status == "observed"
    assert result.binding.revision == 3 and result.company.entity_id == "1"
    assert result.company.realm_id == REALM  # CompanyInfo.Id is not realm identity.
    assert len(result.query_evidence.observations) == 26 and len(calls) == 1
    evidence = result.query_evidence
    assert evidence.canonical_ingestion_fitness is FitnessStatus.UNVERIFIED
    assert evidence.resource_completeness.pagination is CompletenessState.UNKNOWN
    assert evidence.source_total_count is None and "canonical_ingestion" in evidence.prohibited_uses
    assert [p.provider_total_count for p in result.pages] == [25, 1]  # No invented global semantics.
    assert all(p.count_origin == "provider_cross_checked" for p in result.pages)
    first = evidence.observations[0]
    expected = observe_invoice(invoice("0"), binding=oauth.RealmBinding(OWNER, REALM, REF.reference),
        user_id=OWNER, realm_id=REALM, credential_reference=REF.reference, retrieved_at=NOW)
    assert first == expected
    assert first.total_amount == Decimal("12.30") and first.balance == Decimal("2.30")
    assert first.source_evidence["PrivateNote"] == "synthetic-private-body"
    assert result.company_wire_digest == sha256(response(company()).body).hexdigest()
    assert result.pages[0].wire_digest == sha256(response(page([invoice(str(i)) for i in range(25)])).body).hexdigest()
    assert result.company_provider_time.endswith("-07:00")
    requests = fixture.requests
    assert [r.method for r in requests] == [HttpMethod.POST, HttpMethod.POST, HttpMethod.GET, HttpMethod.GET, HttpMethod.GET]
    assert parse_qs(requests[0].body.decode()) == {"code": ["synthetic-code"], "grant_type": ["authorization_code"], "redirect_uri": [REDIRECT]}
    assert parse_qs(requests[1].body.decode())["refresh_token"] == ["synthetic-refresh-one"]
    assert requests[2].url == rt.ORIGIN + "/v3/company/1234567890/companyinfo/1234567890?minorversion=75"
    assert parse_qs(urlsplit(requests[4].url).query) == {"query": ["SELECT * FROM Invoice STARTPOSITION 26 MAXRESULTS 25"], "minorversion": ["75"]}
    assert requests[2].headers["Authorization"] == "Bearer synthetic-access-two"
    assert [name for name, _ in fixture.writes] == ["put", "replace"]
    assert not hasattr(result, "documents")


@pytest.mark.parametrize("terminal", [{"QueryResponse": {}}, {"QueryResponse": {"Invoice": []}}, page([], 26)])
def test_exact_full_page_then_empty_terminal_and_absent_metadata(terminal):
    fixture = Fixture()
    fixture.responses = [response(company()), response(page([invoice(str(i)) for i in range(25)], metadata=False)), response(terminal)]
    result = fixture.acquire()
    assert result.status == "observed" and len(result.pages) == 2
    assert result.pages[0].position_origin == "request_derived"
    assert result.pages[0].count_origin == "array_counted"
    assert result.pages[0].provider_start is None and result.pages[0].provider_returned_count is None
    assert result.pages[-1].local_returned_count == 0 and result.pages[-1].request_start == 26


@pytest.mark.parametrize("payload", [None, [], {}, {"time": "2026-09-05T12:00:00Z"}, {"Fault": {}},
    {"QueryResponse": None}, {"QueryResponse": []}, {"QueryResponse": {"Payment": []}},
    {"QueryResponse": {"Invoice": None}}, {"QueryResponse": {"Invoice": {}}},
    {"QueryResponse": {"maxResults": 0}}, {"QueryResponse": {"Fault": {}}},
    {"QueryResponse": {}, "realmId": "other"}, {"QueryResponse": {"requestIdentity": "run-other"}},
    {"QueryResponse": {}, "time": None}, {"QueryResponse": {}, "time": "2026-09-05"}])
def test_wrong_wire_envelope_never_becomes_empty(payload):
    fixture = Fixture()
    fixture.responses = [response(company()), response(payload)]
    assert_refused(fixture.acquire())


@pytest.mark.parametrize("field,value", [("startPosition", 0), ("startPosition", 2), ("startPosition", True),
    ("startPosition", "1"), ("maxResults", 0), ("maxResults", 2), ("maxResults", None),
    ("maxResults", True), ("totalCount", -1), ("totalCount", 0), ("totalCount", None), ("totalCount", "1")])
def test_supplied_metadata_contradictions_and_types_reject(field, value):
    fixture = Fixture()
    payload = page([invoice()])
    payload["QueryResponse"][field] = value
    fixture.responses = [response(company()), response(payload)]
    assert_refused(fixture.acquire())


@pytest.mark.parametrize("raw", [b'{"QueryResponse":{},"QueryResponse":{}}', b'{"QueryResponse":{"Invoice":[],"maxResults":NaN}}',
    b'{"QueryResponse":{"Invoice":[],"totalCount":1e999}}', b'{"x":123456789012345678901234567890}',
    b'{"x":0.1234567890123456789}', b'{"x":"\\u0000"}', b'{"x":"\\ud800"}', b'['*17+b']'*17,
    b'{} trailing', b'\xff', b'{}'*140000, '{"QueryResponse":{}}'.encode("utf-16")])
def test_hostile_bytes_fail_before_interpretation(raw):
    fixture = Fixture()
    fixture.responses = [response(company()), response(raw)]
    assert_refused(fixture.acquire())


@pytest.mark.parametrize("headers", [{"Content-Type": "text/html"}, {"Content-Type": "application/json", "content-type": "application/json"},
    {"Content-Type": "application/json", "Content-Encoding": "gzip"}, {"Content-Type": "application/json", "Location": "https://evil.test"},
    {"Content-Type": "application/json", "Date": "bad\r\nvalue"}, {"Content-Type": "application/json", "X-Large": "x"*4097}])
def test_response_headers_and_encoding_fail_closed(headers):
    fixture = Fixture()
    fixture.responses = [response(company(), headers=headers)]
    assert_refused(fixture.acquire())
    assert len(fixture.requests) == 1


@pytest.mark.parametrize("status", [201, 204, 301, 302, 400, 401, 403, 429, 500, 503])
def test_no_retry_redirect_or_partial_success(status):
    fixture = Fixture()
    fixture.responses = [response(company()), response(page([invoice(str(i)) for i in range(25)])), response({}, status=status)]
    assert_refused(fixture.acquire())
    assert len(fixture.requests) == 3


@pytest.mark.parametrize("second", [page([invoice("0")], 26), page([invoice("last")], 25), RuntimeError("synthetic-private-body")])
def test_duplicate_gap_and_interruption_discard_all(second):
    fixture = Fixture()
    fixture.responses = [response(company()), response(page([invoice(str(i)) for i in range(25)])), second if isinstance(second, Exception) else response(second)]
    assert_refused(fixture.acquire())


@pytest.mark.parametrize("field,value", [("realm_id", "other/realm"), ("owner_id", "other-owner"), ("state", "disconnected"),
    ("state", "revoked"), ("state", "pending"), ("revision", True), ("expires_at", NOW)])
def test_current_binding_denial_precedes_transport(field, value):
    fixture = Fixture()
    fixture.binding = replace(fixture.binding, **{field: value})
    assert_refused(fixture.acquire())
    assert not fixture.requests


@pytest.mark.parametrize("operation", ["acquire", "refresh", "callback"])
@pytest.mark.parametrize("event", ["resolve", "load", "basic", "send", "after_put", "after_replace"])
def test_production_toggle_inside_dependency_is_refused(operation, event):
    fixture = Fixture("pending" if operation == "callback" else "active")
    fixture.responses = [response(company()), response(page([]))] if operation == "acquire" else [response(token_payload())]
    def hook(label):
        if label == event:
            fixture.runtime.environment = "production"
    fixture.hook = hook
    result = getattr(fixture, operation)()
    if event in fixture.events:
        assert_refused(result)
    else:
        assert result.status in ("observed", "reference_stored", "reference_rotated")


@pytest.mark.parametrize("change", [dict(state="disconnected"), dict(state="revoked"), dict(revision=2), dict(realm_id="999"), dict(owner_id="other")])
@pytest.mark.parametrize("request_index", [1, 2, 3])
def test_binding_changes_around_each_acquisition_request(change, request_index):
    fixture = Fixture()
    fixture.responses = [response(company()), response(page([invoice(str(i)) for i in range(25)])), response(page([], 26))]
    def hook(label):
        if label == "send" and len(fixture.requests) == request_index:
            fixture.binding = replace(fixture.binding, **change)
    fixture.hook = hook
    assert_refused(fixture.acquire())
    assert len(fixture.requests) == request_index


@pytest.mark.parametrize("operation", ["acquire", "refresh", "callback"])
@pytest.mark.parametrize("event", ["resolve", "send", "after_put", "after_replace"])
def test_operation_clock_never_resets_on_dependency_or_generation_transition(operation, event):
    fixture = Fixture("pending" if operation == "callback" else "active")
    fixture.responses = [response(company()), response(page([]))] if operation == "acquire" else [response(token_payload())]
    fixture.hook = lambda label: setattr(fixture, "now", NOW-timedelta(hours=1)) if label == event else None
    result = getattr(fixture, operation)()
    if event in fixture.events:
        assert_refused(result)
        if event.startswith("after_"):
            assert fixture.writes  # Commit occurred; result makes no rollback claim.
    else:
        assert not result.status.endswith("refused")


@pytest.mark.parametrize("operation,expiry", [("acquire", "expires_in"), ("refresh", "x_refresh_token_expires_in"), ("refresh", "x_refresh_token_hard_expires_in")])
def test_token_expiry_exact_boundary_before_and_during_request(operation, expiry):
    for during in (False, True):
        fixture = Fixture()
        fixture.record = replace(fixture.record, tokens=replace(fixture.record.tokens, **{expiry: 1}))
        fixture.responses = [response(company()), response(page([]))] if operation == "acquire" else [response(token_payload())]
        if during:
            fixture.hook = lambda label: setattr(fixture, "now", NOW+timedelta(seconds=1)) if label == "send" else None
        else:
            fixture.now += timedelta(seconds=1)
        assert_refused(getattr(fixture, operation)())
        assert not fixture.writes


@pytest.mark.parametrize("payload", [{"code": "synthetic-code", "state": STATE, "realmId": "999"},
    {"code": "synthetic-code", "state": STATE}, {"error": "access_denied", "state": STATE},
    {"code": "synthetic-code", "state": STATE, "realmId": REALM, "error": "access_denied"}])
def test_callback_failures_consume_state_without_exchange(payload):
    fixture = Fixture("pending")
    store = states()
    assert_refused(fixture.callback(parameters=payload, state_store=store))
    assert "quickbooks" not in store.session[store.KEY]
    assert_refused(fixture.callback(state_store=store))
    assert not fixture.requests


@pytest.mark.parametrize("store", [states("xero"), states(issued=NOW-timedelta(seconds=301)), states(issued=NOW+timedelta(seconds=1))])
def test_state_provider_expiry_and_future_issuance(store):
    fixture = Fixture("pending")
    assert_refused(fixture.callback(state_store=store))
    assert not fixture.requests


def test_callback_error_never_reuses_consumed_state():
    fixture = Fixture("pending")
    fixture.responses = [RuntimeError("synthetic-code")]
    store = states()
    assert_refused(fixture.callback(state_store=store))
    assert_refused(fixture.callback(state_store=store))
    assert len(fixture.requests) == 1 and not fixture.writes


@pytest.mark.parametrize("field,value", [("expires_in", 0), ("x_refresh_token_expires_in", None),
    ("x_refresh_token_hard_expires_in", -1), ("token_type", "Bearer"), ("refresh_token", "x"*513)])
def test_invalid_full_refresh_set_never_replaces_old(field, value):
    fixture = Fixture()
    old = fixture.record
    payload = token_payload("two")
    payload[field] = value
    fixture.responses = [response(payload)]
    assert_refused(fixture.refresh())
    assert fixture.record == old and not fixture.writes


@pytest.mark.parametrize("fault", ["before", "after", "wrong_ack", "drop_expiry", "unchanged_revision"])
def test_atomic_storage_ambiguity_never_claims_success_or_rollback(fault):
    fixture = Fixture()
    fixture.responses = [response(token_payload("two"))]
    original = fixture.replace
    def broken(**kwargs):
        if fault == "before":
            raise RuntimeError("synthetic-refresh")
        result = original(**kwargs)
        if fault == "after":
            raise RuntimeError("synthetic-refresh")
        if fault == "wrong_ack":
            return CredentialReference("quickbooks", "other")
        if fault == "drop_expiry":
            fixture.record = replace(fixture.record, tokens=replace(fixture.record.tokens, x_refresh_token_hard_expires_in=None))
        if fault == "unchanged_revision":
            fixture.binding = replace(fixture.binding, revision=1)
        return result
    fixture.replace = broken
    assert_refused(fixture.refresh())
    assert bool(fixture.writes) is (fault != "before")


@pytest.mark.parametrize("limit", ["MAX_PAGES", "MAX_RECORDS", "MAX_TOTAL_BYTES"])
def test_aggregate_bounds_never_produce_partial_import(monkeypatch, limit):
    fixture = Fixture()
    fixture.responses = [response(company()), response(page([invoice(str(i)) for i in range(25)])), response(page([], 26))]
    monkeypatch.setattr(rt, limit, 1)
    assert_refused(fixture.acquire())


def test_raw_decimal_wire_is_exact_and_unknown_fields_retained():
    fixture = Fixture()
    body = json.dumps(page([invoice()])).replace('"12.30"', '12.30').encode()
    fixture.responses = [response(company()), response(body)]
    result = fixture.acquire()
    assert result.status == "observed"
    assert result.query_evidence.observations[0].total_amount.as_tuple().exponent == -2
    assert result.pages[0].wire_digest == sha256(body).hexdigest()


def test_qs4_real_observer_rejection_and_qs5b_rejection_are_not_bypassed(monkeypatch):
    fixture = Fixture()
    invalid = invoice()
    invalid["Line"] = []
    fixture.responses = [response(company()), response(page([invalid]))]
    assert_refused(fixture.acquire())
    fixture.responses = [response(company()), response(page([]))]
    def reject(*args, **kwargs):
        raise ValueError("synthetic-private-body")
    monkeypatch.setattr(rt, "validate_query_run", reject)
    assert_refused(fixture.acquire())


@pytest.mark.parametrize("operation", ["acquire", "refresh", "callback"])
@pytest.mark.parametrize("environment", ["production", "sandbox", "test", "demo", None, True])
def test_only_explicit_injected_profile_runs_any_dependency(operation, environment):
    fixture = Fixture("pending" if operation == "callback" else "active")
    fixture.runtime.environment = environment
    assert_refused(getattr(fixture, operation)())
    assert fixture.events == []


@pytest.mark.parametrize("mutation", ["revision", "disconnect", "expiry", "production", "rollback", "token_expiry"])
def test_final_qs5b_execution_cannot_return_stale_success(monkeypatch, mutation):
    fixture = Fixture()
    fixture.responses = [response(company()), response(page([invoice()]))]
    original = rt.validate_query_run
    def wrapped(*args, **kwargs):
        result = original(*args, **kwargs)
        if mutation == "revision":
            fixture.binding = replace(fixture.binding, revision=2)
        elif mutation == "disconnect":
            fixture.binding = replace(fixture.binding, state="disconnected")
        elif mutation == "expiry":
            fixture.now = fixture.binding.expires_at
        elif mutation == "production":
            fixture.runtime.environment = "production"
        elif mutation == "rollback":
            fixture.now -= timedelta(seconds=1)
        else:
            fixture.now += timedelta(seconds=3600)
        return result
    monkeypatch.setattr(rt, "validate_query_run", wrapped)
    assert_refused(fixture.acquire())


@pytest.mark.parametrize("payload", [{"CompanyInfo": None}, {"CompanyInfo": {}}, {"CompanyInfo": []},
    {"CompanyInfo": company()["CompanyInfo"], "Fault": {}}, {"Invoice": []}])
def test_company_observation_and_envelope_are_mandatory(payload):
    fixture = Fixture()
    fixture.responses = [response(payload)]
    assert_refused(fixture.acquire())
    assert len(fixture.requests) == 1


@pytest.mark.parametrize("auth", ["Bearer secret", "Basic !!!", "Basic ", "Basic YTo=", "Basic OmI=", "Basic YToKYg=="])
def test_invalid_basic_client_header_prevents_exchange(auth):
    fixture = Fixture("pending")
    fixture.basic_authorization = lambda: auth
    assert_refused(fixture.callback())
    assert not fixture.requests


def test_refresh_uses_current_full_record_not_a_cached_token():
    fixture = Fixture()
    fixture.record = replace(fixture.record, tokens=oauth.parse_token_response(token_payload("latest")))
    fixture.responses = [response(token_payload("new"))]
    assert fixture.refresh().status == "reference_rotated"
    assert parse_qs(fixture.requests[0].body.decode())["refresh_token"] == ["synthetic-refresh-latest"]
    assert fixture.record.tokens == oauth.parse_token_response(token_payload("new"))


def test_successful_callback_state_replay_does_not_exchange_again():
    fixture = Fixture("pending")
    fixture.responses = [response(token_payload())]
    store = states()
    assert fixture.callback(state_store=store).status == "reference_stored"
    # Even another pending fixture cannot redeem the consumed state.
    fixture.binding = replace(fixture.binding, state="pending")
    assert_refused(fixture.callback(state_store=store))
    assert len(fixture.requests) == 1


@pytest.mark.parametrize("payload", [{"QueryResponse": {}, "extra": [0]*1001},
    {"QueryResponse": {}, "extra": "x"*4097}, {"QueryResponse": {}, "extra": [[0]*100 for _ in range(160)]}])
def test_wire_graph_bounds_before_envelope_interpretation(payload):
    with pytest.raises(rt.Refusal):
        rt._decode(json.dumps(payload).encode())


def test_unknown_invoice_detail_does_not_silently_become_supported():
    fixture = Fixture()
    raw = invoice()
    raw["Line"][0] = {"DetailType": "UnknownLineDetail", "UnknownLineDetail": {}}
    fixture.responses = [response(company()), response(page([raw]))]
    assert_refused(fixture.acquire())


def test_production_flip_on_every_clock_tick_is_refused_including_finalization():
    baseline = Fixture()
    baseline.responses = [response(company()), response(page([]))]
    assert baseline.acquire().status == "observed"
    total = baseline.events.count("clock")
    for target in range(1, total + 1):
        fixture = Fixture()
        fixture.responses = [response(company()), response(page([]))]
        seen = 0
        def hook(label):
            nonlocal seen
            if label == "clock":
                seen += 1
                if seen == target:
                    fixture.runtime.environment = "production"
        fixture.hook = hook
        assert_refused(fixture.acquire())


@pytest.mark.parametrize("operation", ["acquire", "callback", "refresh"])
def test_token_expires_at_final_clock_tick_never_returns_success(operation):
    def prepared():
        fixture = Fixture("pending" if operation == "callback" else "active")
        fixture.responses = ([response(company()), response(page([]))] if operation == "acquire"
                             else [response(token_payload())])
        return fixture
    baseline = prepared()
    assert not getattr(baseline, operation)().status.endswith("refused")
    last = baseline.events.count("clock")
    fixture = prepared()
    def hook(label):
        if label == "clock" and fixture.events.count("clock") == last:
            fixture.now += timedelta(seconds=3600)
    fixture.hook = hook
    assert_refused(getattr(fixture, operation)())


@pytest.mark.parametrize("field,value", [("realm_id", "999999"), ("state", "revoked"), ("revision", 2)])
def test_inplace_dependency_binding_change_does_not_rewrite_baseline(field, value):
    fixture = Fixture()
    fixture.responses = [response(company()), response(page([]))]
    def hook(label):
        if label == "send" and len(fixture.requests) == 1:
            object.__setattr__(fixture.binding, field, value)
    fixture.hook = hook
    assert_refused(fixture.acquire())
    assert len(fixture.requests) == 1


def test_returned_binding_is_detached_from_dependency_and_nested_reference():
    fixture = Fixture()
    # Avoid altering the shared test constant when challenging a nested alias.
    fixture.binding = replace(fixture.binding, credential=CredentialReference("quickbooks", REF.reference))
    fixture.responses = [response(company()), response(page([]))]
    result = fixture.acquire()
    assert result.status == "observed"
    assert result.binding is not fixture.binding
    assert result.binding.credential is not fixture.binding.credential
    object.__setattr__(fixture.binding, "realm_id", "999999")
    object.__setattr__(fixture.binding.credential, "reference", "other-reference")
    assert result.binding.realm_id == REALM
    assert result.binding.credential.reference == REF.reference


@pytest.mark.parametrize("mutation", ["nested_token", "token_set", "received_at"])
def test_refresh_previous_record_is_a_detached_full_snapshot(mutation):
    fixture = Fixture()
    fixture.responses = [response(token_payload("new"))]
    def hook(label):
        if label != "send":
            return
        if mutation == "nested_token":
            object.__setattr__(fixture.record.tokens, "refresh_token", "synthetic-refresh-changed")
        elif mutation == "token_set":
            object.__setattr__(fixture.record, "tokens", oauth.parse_token_response(token_payload("changed")))
        else:
            object.__setattr__(fixture.record, "received_at", NOW - timedelta(seconds=1))
    fixture.hook = hook
    assert_refused(fixture.refresh())
    assert not fixture.writes


def test_callback_inplace_binding_change_during_put_is_refused():
    fixture = Fixture("pending")
    fixture.responses = [response(token_payload())]
    def hook(label):
        if label == "before_put":
            object.__setattr__(fixture.binding, "realm_id", "999999")
    fixture.hook = hook
    assert_refused(fixture.callback())
    assert not fixture.writes


def test_custody_cannot_mutate_expected_binding_to_hide_wrong_realm_commit():
    fixture = Fixture("pending")
    fixture.responses = [response(token_payload())]
    original = fixture.put
    def malicious(**kwargs):
        object.__setattr__(kwargs["expected_binding"], "realm_id", "999999")
        object.__setattr__(fixture.binding, "realm_id", "999999")
        return original(**kwargs)
    fixture.put = malicious
    assert_refused(fixture.callback())
    assert fixture.writes  # Detect committed-but-refused, do not claim rollback.


@pytest.mark.parametrize("operation", ["callback", "refresh"])
def test_custody_token_mutation_cannot_change_expected_full_set(operation):
    fixture = Fixture("pending" if operation == "callback" else "active")
    fixture.responses = [response(token_payload("new"))]
    def hook(label):
        if label in {"after_put", "after_replace"}:
            object.__setattr__(fixture.record.tokens, "x_refresh_token_hard_expires_in", None)
    fixture.hook = hook
    assert_refused(getattr(fixture, operation)())
    assert fixture.writes
