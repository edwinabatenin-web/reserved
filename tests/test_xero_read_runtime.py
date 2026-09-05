"""Synthetic executable Xero requests; no provider or real credentials."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, localcontext
from hashlib import sha256
import json
from urllib.parse import parse_qs

import pytest

from reserved.providers.accounting import xero_read_runtime as runtime
from reserved.providers.http_boundary import ProviderResponse, HttpMethod
from reserved.providers.oauth_contracts import CredentialReference
from reserved.providers.oauth_security import OAuthStateStore
from reserved.providers.import_evidence import CompletenessStatus

NOW = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)


def response(payload):
    return ProviderResponse(200, {"Content-Type": "application/json"}, json.dumps(payload).encode())


def token(number):
    return {"access_token": f"SYNTHETIC-ACCESS-{number}", "refresh_token": f"SYNTHETIC-REFRESH-{number}",
            "expires_in": 1800, "token_type": "Bearer"}


def invoice(number):
    # Literal exact JSON decimals, not float serialization or mapper-derived amounts.
    return ('''{"InvoiceID":"invoice-N","Type":"ACCREC","Contact":{"ContactID":"private-contact"},
      "Date":"2026-09-01","Status":"PAID","LineAmountTypes":"Exclusive","CurrencyCode":"GBP",
      "SubTotal":100.00,"TotalTax":20.00,"Total":120.00,"LineItems":[
      {"LineItemID":"line-N","Description":"PRIVATE-DESCRIPTION","LineAmount":100.00,"TaxAmount":20.00,
       "Quantity":2,"UnitAmount":50.0000}]}'''.replace("-N", "-" + str(number)))


def page(*numbers):
    body = '{"Invoices":[' + ",".join(invoice(n) for n in numbers) + "]}"
    return ProviderResponse(200, {"Content-Type": "application/json"}, body.encode())


def connection(tenant="tenant-1", event="event-1", identifier="connection-1"):
    return {"id": identifier, "authEventId": event, "tenantId": tenant,
            "tenantType": "ORGANISATION", "tenantName": "PRIVATE-COMPANY",
            "createdDateUtc": "2026-09-01", "updatedDateUtc": "2026-09-05"}


class Fixtures:
    def __init__(self):
        self.reference = CredentialReference("xero", "fixture-reference")
        self.binding = runtime.FixtureBinding("owner-1", "connection-1", "tenant-1", "event-1",
            self.reference, 1, "active", NOW + timedelta(hours=1))
        self.tokens = None
        self.calls, self.requests = [], []
        self.responses = [response(token(1)), response(token(2)),
            response([connection("other-tenant", "other-event", "other-connection"), connection()]),
            page(1, 2), page(3), page()]
        self.fail_put = self.fail_replace = False
        self.hook = None
        self.resolve_hook = None

    def resolve(self, reference):
        assert reference == self.reference
        if self.resolve_hook:
            self.resolve_hook(self)
        return self.binding

    def basic_authorization(self):
        return "Basic U1lOVEhFVElDOlNZTlRIRVRJQw=="

    def access_authorization(self, reference):
        assert reference == self.reference
        return "Bearer " + self.tokens.access_token

    def refresh_token(self, reference):
        assert reference == self.reference
        return self.tokens.refresh_token

    def put(self, *, provider, user_id, tokens):
        self.calls.append("put")
        assert provider == "xero" and user_id == "owner-1"
        if self.fail_put:
            raise ValueError("PRIVATE-STORE-FAILURE")
        self.tokens = tokens
        return self.reference

    def replace(self, *, credential, tokens):
        self.calls.append("replace")
        assert credential == self.reference
        if self.fail_replace:
            raise ValueError("PRIVATE-ROTATION-FAILURE")
        # One fixture operation publishes the whole pair and its new binding
        # generation. This tests the required store contract, not real custody.
        self.tokens = tokens
        self.binding = replace(self.binding, revision=self.binding.revision + 1, state="active")

    def delete(self, reference):
        pytest.fail("Old token set must not be deleted before replacement")

    def send(self, request):
        self.requests.append(request)
        if self.hook:
            self.hook(self)
        result = self.responses[len(self.requests) - 1]
        if isinstance(result, Exception):
            raise result
        return result


def setup(environment="injected_test"):
    fixture = Fixtures()
    engine = runtime.InjectedXeroRuntime(transport=fixture, custody=fixture,
        binding_source=fixture, clock=lambda: NOW, environment=environment)
    # Independently chosen state literal, avoiding random token generation.
    state = "SYNTHETIC-STATE"
    session = {OAuthStateStore.KEY: {"xero": {"digest": sha256(state.encode()).hexdigest(),
        "issued_at": int(NOW.timestamp())}}}
    callback = dict(owner_id="owner-1", parameters={"state": state, "code": "SYNTHETIC-CODE"},
                    state_store=OAuthStateStore(session, ttl_seconds=300), redirect_uri="https://reserved.example/callback")
    acquire = dict(credential=fixture.reference, owner_id="owner-1", auth_event_id="event-1",
                   tenant_id="tenant-1", import_run_id="run-1")
    return fixture, engine, callback, acquire


def ready():
    f, engine, callback, acquire = setup()
    assert engine.complete_callback(**callback).status == "reference_stored"
    assert engine.refresh(credential=f.reference, owner_id="owner-1").status == "reference_rotated"
    return f, engine, acquire


def refused(outcome):
    assert "refused" in outcome.status
    assert not outcome.documents and not outcome.observations and outcome.manifest is None
    assert outcome.credential is None and outcome.tenant_id is None
    summary = json.dumps(outcome.diagnostic_summary()) + repr(outcome)
    for secret in ("SYNTHETIC", "PRIVATE", "owner-1", "tenant-1", "fixture-reference", "Basic", "Bearer"):
        assert secret not in summary


def test_full_callback_rotation_explicit_selection_and_real_normalisation(monkeypatch):
    f, engine, callback, acquire = setup()
    assert engine.complete_callback(**callback).credential == f.reference
    assert f.tokens.access_token == "SYNTHETIC-ACCESS-1"
    assert engine.refresh(credential=f.reference, owner_id="owner-1").credential == f.reference
    assert (f.tokens.access_token, f.tokens.refresh_token) == ("SYNTHETIC-ACCESS-2", "SYNTHETIC-REFRESH-2")
    assert f.calls == ["put", "replace"]
    normalised = []
    actual = runtime.normalise_document
    def record(**kwargs):
        value = actual(**kwargs)
        normalised.append(value)
        return value
    monkeypatch.setattr(runtime, "normalise_document", record)
    with localcontext() as ctx:
        ctx.prec = 1
        ctx.Emax = 1
        result = engine.acquire(**acquire)
    assert result.status == "observed" and result.documents == tuple(normalised)
    assert len(result.documents) == 3
    for document, observation in zip(result.documents, result.observations):
        assert document.gross_amount == Decimal("120.00")
        assert document.net_amount == Decimal("100.00") and document.vat_amount == Decimal("20.00")
        assert document.cash_candidate is document.accrual_candidate is None
        assert document.business_id == "tenant-1" and document.connected_organisation_id == "connection-1"
        assert document.provenance == observation.provenance
        assert observation.provenance.identity.user_id == "owner-1"
    assert (result.tenant_id, result.connection_id, result.auth_event_id, result.binding_revision) == ("tenant-1", "connection-1", "event-1", 2)
    assert result.manifest.page_count == 3 and result.manifest.fetched_count == 3
    assert result.manifest.status is CompletenessStatus.UNVERIFIED
    assert result.manifest.source_total_count is result.manifest.source_watermark is None
    assert result.response_digests == tuple(sha256(r.body).hexdigest() for r in f.responses[2:])
    assert [r.url for r in f.requests] == [runtime.oauth.TOKEN_ENDPOINT, runtime.oauth.TOKEN_ENDPOINT,
        runtime.oauth.CONNECTIONS_ENDPOINT] + [runtime.INVOICES_ENDPOINT + f"?page={n}&pageSize=25" for n in (1, 2, 3)]
    assert parse_qs(f.requests[0].body.decode()) == {"grant_type": ["authorization_code"],
        "code": ["SYNTHETIC-CODE"], "redirect_uri": ["https://reserved.example/callback"]}
    assert parse_qs(f.requests[1].body.decode()) == {"grant_type": ["refresh_token"], "refresh_token": ["SYNTHETIC-REFRESH-1"]}
    assert all(r.method is HttpMethod.POST and r.headers["Authorization"].startswith("Basic ") for r in f.requests[:2])
    assert all(r.method is HttpMethod.GET and r.body is None for r in f.requests[2:])
    assert all(r.headers["xero-tenant-id"] == "tenant-1" and r.headers["Authorization"] == "Bearer SYNTHETIC-ACCESS-2" for r in f.requests[3:])
    assert all("summaryOnly" not in r.url for r in f.requests)


@pytest.mark.parametrize("kind", ["replay", "wrong", "other_provider", "denied", "old", "long_ttl", "raw_code"])
def test_callback_state_boundary_before_exchange(kind):
    f, engine, cb, _ = setup()
    if kind == "replay":
        assert engine.complete_callback(**cb).status == "reference_stored"
    elif kind == "wrong":
        cb["parameters"]["state"] = "wrong"
    elif kind == "other_provider":
        states = cb["state_store"].session[OAuthStateStore.KEY]
        states["freeagent"] = states.pop("xero")
    elif kind == "denied":
        cb["parameters"]["error"] = "PRIVATE-DENIED"
    elif kind == "old":
        cb["state_store"].session[OAuthStateStore.KEY]["xero"]["issued_at"] -= 301
    elif kind == "long_ttl":
        cb["state_store"].ttl_seconds = 600
    else:
        cb["parameters"] = {"code": "SYNTHETIC-CODE"}
    before = len(f.requests)
    refused(engine.complete_callback(**cb))
    assert len(f.requests) == before


@pytest.mark.parametrize("operation", ["put", "replace", "token_exchange", "token_refresh"])
def test_storage_and_invalid_tokens_never_false_success(operation):
    f, engine, cb, _ = setup()
    if operation == "put":
        f.fail_put = True
        refused(engine.complete_callback(**cb))
        assert f.tokens is None
        return
    if operation == "token_exchange":
        f.responses[0] = response({"access_token": "SYNTHETIC"})
        refused(engine.complete_callback(**cb))
        assert not f.calls
        return
    assert engine.complete_callback(**cb).status == "reference_stored"
    old = f.tokens
    if operation == "replace":
        f.fail_replace = True
    else:
        f.responses[1] = response({**token(2), "refresh_token": None})
    f.binding = replace(f.binding, state="refresh_required")
    refused(engine.refresh(credential=f.reference, owner_id="owner-1"))
    assert f.tokens is old


@pytest.mark.parametrize("field,value", [("owner_id", "owner-2"), ("tenant_id", "tenant-2"),
    ("auth_event_id", "event-2"), ("credential", CredentialReference("freeagent", "fixture-reference"))])
def test_wrong_requested_binding_before_transport(field, value):
    f, engine, acquire = ready()
    acquire[field] = value
    refused(engine.acquire(**acquire))
    assert len(f.requests) == 2


@pytest.mark.parametrize("connections", [[connection("wrong")], [connection(event="wrong")],
    [connection(identifier="wrong")], [connection(), connection()], [],
    [{**connection(), "tenantType": "PRACTICE"}]])
def test_explicit_event_tenant_connection_selection(connections):
    f, engine, acquire = ready()
    f.responses[2] = response(connections)
    refused(engine.acquire(**acquire))
    assert len(f.requests) == 3


@pytest.mark.parametrize("at", [3, 4, 5, 6])
@pytest.mark.parametrize("field,value", [("revision", 3), ("state", "revoked"),
    ("state", "disconnected"), ("tenant_id", "tenant-2"), ("owner_id", "owner-2"),
    ("auth_event_id", "event-2"), ("expires_at", NOW)])
def test_binding_changes_at_each_fetch_discard_all(at, field, value):
    f, engine, acquire = ready()
    def hook(fixture):
        if len(fixture.requests) == at:
            fixture.binding = replace(fixture.binding, **{field: value})
    f.hook = hook
    refused(engine.acquire(**acquire))
    assert len(f.requests) == at


@pytest.mark.parametrize("body", [b"{", b'{"Invoices":[],"Invoices":[]}', b"[" * 1000 + b"]" * 1000,
    b" " * 262145, b'{"Invoices":[{"Total":1e999}]}', b'{"Invoices":[{"Total":NaN}]}',
    b'{"Invoices":[{"Total":0.123456789}]}', b'{"Invoices":[{"Total":9999999999999999999}]}',
    b"\xff", "not bytes"])
def test_encoding_graph_decimal_and_duplicate_key_bounds(body):
    f, engine, acquire = ready()
    f.responses[4] = ProviderResponse(200, {"Content-Type": "application/json"}, body)
    refused(engine.acquire(**acquire))


@pytest.mark.parametrize("status", [301, 302, 401, 403, 429, 500, 503])
def test_non_success_has_no_retry_or_partial_result(status):
    f, engine, acquire = ready()
    f.responses[4] = ProviderResponse(status, {"Location": "https://evil.example"}, b"PRIVATE")
    result = engine.acquire(**acquire)
    refused(result)
    assert result.failure == (f"http_{status}" if status in (401, 403, 429) else "http_5xx" if status >= 500 else "http_other")
    assert len(f.requests) == 5


@pytest.mark.parametrize("kind", ["duplicate", "conflicting", "missing_detail", "wrong_total", "unknown_envelope", "partial_failure"])
def test_page_mapping_and_interruption_refuse_whole_import(kind):
    f, engine, acquire = ready()
    if kind == "duplicate":
        f.responses[4] = page(1)
    elif kind == "conflicting":
        f.responses[4] = ProviderResponse(200, {"Content-Type": "application/json"}, page(1).body.replace(b"PAID", b"AUTHORISED"))
    elif kind == "missing_detail":
        f.responses[4] = response({"Invoices": [{"InvoiceID": "invoice-3"}]})
    elif kind == "wrong_total":
        f.responses[4] = ProviderResponse(200, {"Content-Type": "application/json"}, page(3).body.replace(b"120.00", b"120.01"))
    elif kind == "unknown_envelope":
        f.responses[4] = response({"Invoices": [], "summaryOnly": True})
    else:
        f.responses[4] = ValueError("PRIVATE-FAILURE")
    refused(engine.acquire(**acquire))


@pytest.mark.parametrize("environment", [None, "production", "sandbox", "test"])
def test_environment_denies_before_transport_or_custody(environment):
    f, engine, cb, acquire = setup(environment)
    refused(engine.complete_callback(**cb))
    refused(engine.refresh(credential=f.reference, owner_id="owner-1"))
    refused(engine.acquire(**acquire))
    assert not f.calls and not f.requests


@pytest.mark.parametrize("limit,value", [("MAX_PAGES", 2), ("MAX_RECORDS", 2), ("MAX_TOTAL_BYTES", 100)])
def test_bounds_never_promote_partial_pages(limit, value, monkeypatch):
    f, engine, acquire = ready()
    monkeypatch.setattr(runtime, limit, value)
    refused(engine.acquire(**acquire))
    assert len(f.requests) <= 5


def test_page_size_ceiling_and_final_empty_page_required():
    f, engine, acquire = ready()
    f.responses[3] = page(*range(26))
    refused(engine.acquire(**acquire))
    f, engine, acquire = ready()
    f.responses = f.responses[:3] + [page(n) for n in range(1, 21)]
    refused(engine.acquire(**acquire))
    assert len(f.requests) == 23


def test_binding_change_during_normalisation_prevents_final_result(monkeypatch):
    f, engine, acquire = ready()
    original = runtime.normalise_document
    def changed(**kwargs):
        result = original(**kwargs)
        object.__setattr__(f.binding, "revision", 3)
        return result
    monkeypatch.setattr(runtime, "normalise_document", changed)
    refused(engine.acquire(**acquire))


def test_refresh_binding_change_before_replace_and_after_store_refuses():
    for after in (False, True):
        f, engine, cb, _ = setup()
        assert engine.complete_callback(**cb).status == "reference_stored"
        old = f.tokens
        if after:
            original = f.replace
            def changed(**kwargs):
                original(**kwargs)
                f.binding = replace(f.binding, tenant_id="tenant-2")
            f.replace = changed
        else:
            f.hook = lambda fixture: setattr(fixture, "binding", replace(fixture.binding, revision=2))
        refused(engine.refresh(credential=f.reference, owner_id="owner-1"))
        if not after:
            assert f.tokens is old and f.calls == ["put"]


@pytest.mark.parametrize("state", ["revoked", "disconnected", "refresh_required", "refresh_failed"])
def test_unusable_references_and_no_cached_grant(state):
    f, engine, acquire = ready()
    assert engine.acquire(**acquire).status == "observed"
    f.binding = replace(f.binding, state=state)
    before = len(f.requests)
    refused(engine.acquire(**acquire))
    assert len(f.requests) == before


@pytest.mark.parametrize("bad", ["Basic not-base64!", "Basic Og==", "Bearer WRONG", "Basic U1lOVEg6U0VD\n"])
def test_invalid_client_auth_never_delegates_or_stores(bad):
    f, engine, cb, _ = setup()
    f.basic_authorization = lambda: bad
    refused(engine.complete_callback(**cb))
    assert not f.requests and not f.calls


@pytest.mark.parametrize("field,value", [("access_token", "bad\nheader"), ("refresh_token", "bad token"),
    ("expires_in", True), ("token_type", "bearer"), ("expires_in", 0)])
def test_malformed_token_set_never_reaches_store(field, value):
    f, engine, cb, _ = setup()
    f.responses[0] = response({**token(1), field: value})
    refused(engine.complete_callback(**cb))
    assert not f.calls


@pytest.mark.parametrize("headers", [{"Location": "https://evil.example"},
    {"Content-Type": "application/json", "Link": '<https://evil.example>; rel="next"'},
    {"Content-Type": "application/json", "content-type": "application/json"},
    {"Content-Type": "text/html"}, {"Content-Type": "application/json", "Set-Cookie": "PRIVATE"}])
def test_unexpected_response_headers_never_drive_requests(headers):
    f, engine, acquire = ready()
    f.responses[3] = ProviderResponse(200, headers, page(1).body)
    refused(engine.acquire(**acquire))
    assert len(f.requests) == 4


def test_production_toggle_during_exchange_prevents_custody():
    f, engine, cb, _ = setup()
    f.hook = lambda fixture: setattr(engine, "environment", "production")
    refused(engine.complete_callback(**cb))
    assert not f.calls


def test_exact_binding_types_no_property_hooks_and_disabled_provider():
    from reserved.providers.accounting.xero import XeroProvider
    from reserved.providers.readiness import PROVIDERS
    assert next(p for p in PROVIDERS if p.name == "xero").implementation_enabled is False
    with pytest.raises(NotImplementedError):
        XeroProvider().list_invoices("fixture-reference")
    class Lookalike:
        @property
        def owner_id(self):
            pytest.fail("Untrusted binding property accessed")
    f, engine, acquire = ready()
    f.resolve = lambda reference: Lookalike()
    refused(engine.acquire(**acquire))
    assert len(f.requests) == 2


def test_acquisition_clock_cannot_reset_after_initial_snapshot():
    f, engine, acquire = ready()
    calls = 0
    def clock():
        nonlocal calls
        calls += 1
        return NOW if calls == 1 else NOW - timedelta(hours=1)
    engine.clock = clock
    refused(engine.acquire(**acquire))
    assert len(f.requests) == 2


def test_refresh_clock_rollback_after_atomic_replace_is_not_success_or_rollback():
    f, engine, cb, _ = setup()
    assert engine.complete_callback(**cb).status == "reference_stored"
    moment = [NOW]
    engine.clock = lambda: moment[0]
    original = f.replace
    def committed(**kwargs):
        original(**kwargs)
        moment[0] = NOW - timedelta(hours=1)
    f.replace = committed
    refused(engine.refresh(credential=f.reference, owner_id="owner-1"))
    assert f.tokens.access_token == "SYNTHETIC-ACCESS-2"
    assert f.tokens.refresh_token == "SYNTHETIC-REFRESH-2"
    assert f.binding.revision == 2


@pytest.mark.parametrize("operation", ["callback", "refresh"])
def test_clock_rollback_at_operation_entry_denies_before_new_request(operation):
    f, engine, cb, _ = setup()
    if operation == "refresh":
        assert engine.complete_callback(**cb).status == "reference_stored"
    before = len(f.requests)
    calls = 0
    def clock():
        nonlocal calls
        calls += 1
        return NOW if calls == 1 else NOW - timedelta(seconds=1)
    engine.clock = clock
    outcome = engine.complete_callback(**cb) if operation == "callback" else engine.refresh(credential=f.reference, owner_id="owner-1")
    refused(outcome)
    assert len(f.requests) == before


def test_callback_post_store_clock_rollback_refuses_without_claiming_erasure():
    f, engine, cb, _ = setup()
    moment = [NOW]
    engine.clock = lambda: moment[0]
    original = f.put
    def stored(**kwargs):
        reference = original(**kwargs)
        moment[0] = NOW - timedelta(hours=1)
        return reference
    f.put = stored
    refused(engine.complete_callback(**cb))
    assert f.tokens.access_token == "SYNTHETIC-ACCESS-1"
    assert f.calls == ["put"]


@pytest.mark.parametrize("operation", ["acquire", "refresh"])
def test_expired_initial_binding_cannot_be_revived_by_later_clock(operation):
    f, engine, acquire = ready()
    f.binding = replace(f.binding, expires_at=NOW)
    calls = 0
    def clock():
        nonlocal calls
        calls += 1
        return NOW if calls == 1 else NOW - timedelta(hours=1)
    engine.clock = clock
    outcome = engine.acquire(**acquire) if operation == "acquire" else engine.refresh(credential=f.reference, owner_id="owner-1")
    refused(outcome)
    assert len(f.requests) == 2


def test_expired_callback_state_not_revived_by_clock_rollback():
    f, engine, cb, _ = setup()
    cb["state_store"].session[OAuthStateStore.KEY]["xero"]["issued_at"] -= 301
    calls = 0
    def clock():
        nonlocal calls
        calls += 1
        return NOW if calls == 1 else NOW - timedelta(seconds=10)
    engine.clock = clock
    refused(engine.complete_callback(**cb))
    assert not f.requests and not f.calls


def test_forward_expiry_after_refresh_store_is_refused_without_rollback_claim():
    f, engine, cb, _ = setup()
    assert engine.complete_callback(**cb).status == "reference_stored"
    moment = [NOW]
    engine.clock = lambda: moment[0]
    original = f.replace
    def committed(**kwargs):
        original(**kwargs)
        moment[0] = NOW + timedelta(hours=2)
    f.replace = committed
    refused(engine.refresh(credential=f.reference, owner_id="owner-1"))
    assert f.tokens.access_token == "SYNTHETIC-ACCESS-2"


def test_continuously_advancing_clock_preserves_full_success_and_manifest_start():
    f, engine, cb, acquire = setup()
    moments = []
    def clock():
        value = NOW + timedelta(seconds=len(moments))
        moments.append(value)
        return value
    engine.clock = clock
    assert engine.complete_callback(**cb).status == "reference_stored"
    assert engine.refresh(credential=f.reference, owner_id="owner-1").status == "reference_rotated"
    expected_start = NOW + timedelta(seconds=len(moments))
    result = engine.acquire(**acquire)
    assert result.status == "observed"
    assert result.manifest.started_at == expected_start
    assert result.manifest.completed_at >= result.retrieved_at[-1] >= result.manifest.started_at
