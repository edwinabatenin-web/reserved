"""Actual injected request execution using synthetic source bytes only."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json

import pytest

from reserved.providers.accounting import freeagent_read_runtime as runtime
from reserved.providers.accounting.contracts import CorrectionLifecycle, EvidenceState
from reserved.providers.http_boundary import ProviderResponse, HttpMethod
from reserved.providers.oauth_contracts import CredentialReference
from reserved.providers.import_evidence import CompletenessStatus

NOW = datetime(2026, 9, 5, 12, tzinfo=timezone.utc)
COMPANY = {"company": {"id": "123", "type": "UkSoleTrader", "currency": "GBP",
    "country": "United Kingdom", "cis_enabled": False, "cis_subcontractor": False,
    "cis_contractor": False, "name": "PRIVATE COMPANY"}}


def invoice(number):
    return {"url": f"https://api.freeagent.com/v2/invoices/{number}",
        "contact": "https://api.freeagent.com/v2/contacts/90", "dated_on": "2026-09-01",
        "payment_terms_in_days": 30, "currency": "GBP", "status": "Open",
        "net_value": "12.50", "total_value": "12.50", "sales_tax_value": "0",
        "involves_sales_tax": False, "is_interim_uk_vat": False, "ec_status": "UK/Non-EC",
        "discount_percent": "0", "invoice_items": [
            {"url": f"https://api.freeagent.com/v2/invoice_items/{number}1", "item_type": "Services",
             "description": "PRIVATE DESCRIPTION", "quantity": "2", "price": "5", "position": "1"},
            {"url": f"https://api.freeagent.com/v2/invoice_items/{number}2", "item_type": "Products",
             "description": "PRIVATE DESCRIPTION", "quantity": "0.5", "price": "5", "position": "2"}]}


def response(payload, **headers):
    return ProviderResponse(200, {"Content-Type": "application/json", **headers}, json.dumps(payload).encode())


class BindingSource:
    def __init__(self):
        self.value = runtime.FixtureBinding("owner:1", "connection:1", "business:1", "123",
            CredentialReference("freeagent", "fixture:reference"), 1, "active", NOW + timedelta(hours=1))
        self.calls = 0
        self.hook = None

    def resolve(self, reference):
        assert reference == self.value.credential
        self.calls += 1
        if self.hook:
            self.hook(self)
        return self.value


class Transport:
    def __init__(self, responses):
        self.responses = responses
        self.requests = []
        self.hook = None

    def send(self, request):
        self.requests.append(request)
        if self.hook:
            self.hook(self)
        value = self.responses[len(self.requests) - 1]
        if isinstance(value, Exception):
            raise value
        return value


def setup():
    source = BindingSource()
    transport = Transport([
        response(COMPANY),
        response({"invoices": [invoice(101), invoice(102)]}, **{
            "X-Total-Count": "3", "Link": '<https://api.freeagent.com/v2/invoices?page=2>; rel="next"'}),
        response({"invoices": [invoice(103)]}, **{"X-Total-Count": "3"}),
    ])
    kwargs = dict(credential=source.value.credential, owner_id="owner:1", connection_id="connection:1",
                  import_run_id="run:1", binding_source=source, transport=transport, clock=lambda: NOW)
    return source, transport, kwargs


def refused(result):
    assert result.status == "refused"
    assert result.mappings == () and result.manifest is None
    assert result.company_digest is None and result.page_digests == ()
    assert not result.annual_income_complete and not result.authenticated_membership
    summary = json.dumps(result.diagnostic_summary())
    for private in ("PRIVATE", "owner:1", "123", "fixture:reference", "Traceback", "api.freeagent"):
        assert private not in summary


def test_actual_company_pages_and_canonical_documents():
    source, transport, kwargs = setup()
    result = runtime.acquire_invoices(**kwargs)
    assert result.status == "observed"
    assert [request.url for request in transport.requests] == [runtime.COMPANY_ENDPOINT,
        runtime.INVOICES_ENDPOINT, runtime.INVOICES_ENDPOINT + "?page=2"]
    assert all(r.method is HttpMethod.GET and dict(r.headers) == {"Accept": "application/json"}
               and r.body is None for r in transport.requests)
    assert source.calls > len(transport.requests) * 2
    assert [m.document.document_id for m in result.mappings] == [f"https://api.freeagent.com/v2/invoices/{n}" for n in (101, 102, 103)]
    for mapping in result.mappings:
        assert mapping.document.gross_amount == Decimal("12.50")
        assert [line.money.original_amount for line in mapping.document.lines] == [Decimal("10"), Decimal("2.5")]
        assert mapping.document.correction_lifecycle is CorrectionLifecycle.UNKNOWN
        assert mapping.document.cash_candidate is mapping.document.accrual_candidate is None
        assert mapping.observation.evidence_state is EvidenceState.UNRESOLVED
        assert mapping.observation.provenance.retrieved_at == NOW
        assert mapping.observation.provenance.identity.user_id == "owner:1"
    assert result.manifest.page_count == 2 and result.manifest.fetched_count == result.manifest.unique_count == 3
    assert result.manifest.status is CompletenessStatus.COMPLETE
    assert result.company_digest == sha256(transport.responses[0].body).hexdigest()
    assert result.company_retrieved_at == NOW and result.page_retrieved_at == (NOW, NOW)
    assert result.binding_revision == 1
    assert result.page_digests == tuple(sha256(r.body).hexdigest() for r in transport.responses[1:])
    assert not result.annual_income_complete and not result.authenticated_membership
    assert "PRIVATE" not in repr(result)


@pytest.mark.parametrize("field,value", [("owner_id", "owner:2"), ("connection_id", "connection:2"),
    ("credential", CredentialReference("xero", "fixture:reference")), ("environment", "sandbox"),
    ("environment", "production"), ("environment", "test"), ("owner_id", None)])
def test_wrong_context_or_environment_refused_before_send(field, value):
    _, t, kwargs = setup()
    kwargs[field] = value
    refused(runtime.acquire_invoices(**kwargs))
    assert not t.requests


@pytest.mark.parametrize("field,value", [("owner_id", "owner:2"), ("connection_id", "connection:2"),
    ("company_id", "999"), ("company_id", 123), ("state", "disconnected"),
    ("state", "revoked"), ("state", "refresh_required"), ("state", "refresh_failed"),
    ("expires_at", NOW), ("revision", True)])
def test_binding_and_same_label_company_mismatch(field, value):
    s, t, kwargs = setup()
    s.value = replace(s.value, **{field: value})
    refused(runtime.acquire_invoices(**kwargs))
    assert len(t.requests) <= 1


@pytest.mark.parametrize("at", [1, 2, 3])
@pytest.mark.parametrize("field,value", [("revision", 2), ("state", "revoked"),
    ("owner_id", "owner:2"), ("connection_id", "connection:2"), ("business_id", "business:2"),
    ("company_id", "999"), ("expires_at", NOW)])
def test_binding_change_during_any_request_discards_all_results(at, field, value):
    s, t, kwargs = setup()
    def mutate(transport):
        if len(transport.requests) == at:
            s.value = replace(s.value, **{field: value})
    t.hook = mutate
    refused(runtime.acquire_invoices(**kwargs))
    assert len(t.requests) == at


def test_binding_change_at_finalization_and_dependency_mutation():
    for mutate in (False, True):
        s, t, kwargs = setup()
        def hook(source):
            # After final page has been received and mapped, at final check.
            if source.calls == 10:
                if mutate:
                    object.__setattr__(source.value, "revision", 2)
                else:
                    source.value = replace(source.value, revision=2)
        s.hook = hook
        refused(runtime.acquire_invoices(**kwargs))


@pytest.mark.parametrize("target", [
    "https://evil.example/v2/invoices?page=2", "http://api.freeagent.com/v2/invoices?page=2",
    "https://api.sandbox.freeagent.com/v2/invoices?page=2", "https://api.freeagent.com/v2/company",
    "https://api.freeagent.com/v2/invoices?page=2&token=PRIVATE", "https://api.freeagent.com/v2/invoices?page=2&page=2",
    "https://api.freeagent.com/v2/invoices?page=2#x", "https://api.freeagent.com/v2/invoices?page=%32",
    "https://api.freeagent.com/v2/invoices?page=0", "https://api.freeagent.com/v2/invoices?page=21",
    "https://api.freeagent.com/v2/invoices?per_page=101", "https://api.freeagent.com:443/v2/invoices?page=2",
])
def test_hostile_destination_never_delegated(target):
    _, t, kwargs = setup()
    t.responses[1] = response({"invoices": [invoice(101)]}, Link=f'<{target}>; rel="next"')
    refused(runtime.acquire_invoices(**kwargs))
    assert len(t.requests) == 2


@pytest.mark.parametrize("bad", [ProviderResponse(302, {"Location": "https://evil.example"}),
    ProviderResponse(401), ProviderResponse(429), ProviderResponse(500), None, {},
    RuntimeError("PRIVATE secret fixture:reference"),
    ProviderResponse(200, {"Content-Type": "application/json", "Set-Cookie": "PRIVATE"}, b"{}"),
    ProviderResponse(200, {"Content-Type": "application/json", "content-type": "application/json"}, b"{}"),
    ProviderResponse(200, {}, b"{}")])
def test_failed_or_malformed_final_page_never_returns_stale_success(bad):
    _, t, kwargs = setup()
    t.responses[2] = bad
    refused(runtime.acquire_invoices(**kwargs))


@pytest.mark.parametrize("body", [b"{", b"\xff", b'{"invoices":[],"invoices":[]}',
    b"[" * 1000 + b"]" * 1000, b" " * 65537, b'{"invoices":[],"n":1e999}',
    b'{"invoices":[],"n":NaN}', b'{"invoices":[],"n":999999999999999999}',
    b'{"invoices":[],"text":"' + b"x" * 2049 + b'"}', "not bytes"])
def test_json_and_body_bounds(body):
    _, t, kwargs = setup()
    t.responses[1] = ProviderResponse(200, {"Content-Type": "application/json"}, body)
    refused(runtime.acquire_invoices(**kwargs))


@pytest.mark.parametrize("change", ["duplicate", "conflicting", "unsupported", "total_change", "missing_total", "cycle", "wrong_page", "empty_next"])
def test_multistage_import_contradictions(change):
    _, t, kwargs = setup()
    raw = invoice(103)
    headers = {"X-Total-Count": "3"}
    if change in ("duplicate", "conflicting"):
        raw = invoice(101)
        if change == "conflicting":
            raw["reference"] = "different"
    elif change == "unsupported":
        raw["invoice_items"][0]["item_type"] = "Discount"
    elif change == "total_change":
        headers["X-Total-Count"] = "4"
    elif change == "missing_total":
        headers = {}
    elif change == "cycle":
        headers = {"Link": '<https://api.freeagent.com/v2/invoices?page=2>; rel="next"'}
        t.responses[1] = response({"invoices": [invoice(101)]}, **headers)
    elif change == "wrong_page":
        t.responses[1] = response({"invoices": [invoice(101)]}, Link='<https://api.freeagent.com/v2/invoices?page=3>; rel="next"')
        headers = {}
    elif change == "empty_next":
        t.responses[1] = response({"invoices": []}, Link='<https://api.freeagent.com/v2/invoices?page=2>; rel="next"')
    t.responses[2] = response({"invoices": [raw]}, **headers)
    refused(runtime.acquire_invoices(**kwargs))


@pytest.mark.parametrize("records", [[], [invoice(101)]])
def test_missing_total_is_unverified_not_annual_completeness(records):
    _, t, kwargs = setup()
    t.responses = [response(COMPANY), response({"invoices": records})]
    result = runtime.acquire_invoices(**kwargs)
    assert result.status == "observed"
    assert result.manifest.status is CompletenessStatus.UNVERIFIED
    assert not result.annual_income_complete


def test_no_cached_success_after_disconnect():
    s, t, kwargs = setup()
    assert runtime.acquire_invoices(**kwargs).status == "observed"
    s.value = replace(s.value, state="disconnected")
    refused(runtime.acquire_invoices(**kwargs))
    assert len(t.requests) == 3


@pytest.mark.parametrize("target", [runtime.INVOICES_ENDPOINT, runtime.INVOICES_ENDPOINT + "?per_page=1"])
def test_initial_destination_repeat_or_missing_next_page_identity_never_sent(target):
    _, t, kwargs = setup()
    # Distinct IDs and matching totals must not hide a repeated/ambiguous fetch.
    t.responses[1] = response({"invoices": [invoice(101)]}, **{
        "X-Total-Count": "2", "Link": f'<{target}>; rel="next"'})
    t.responses[2] = response({"invoices": [invoice(102)]}, **{"X-Total-Count": "2"})
    refused(runtime.acquire_invoices(**kwargs))
    assert [request.url for request in t.requests] == [runtime.COMPANY_ENDPOINT, runtime.INVOICES_ENDPOINT]


def test_unsupported_and_absent_completeness_are_explicit():
    _, t, kwargs = setup()
    raw = invoice(103)
    raw["invoice_items"][0]["item_type"] = "Discount"
    t.responses[2] = response({"invoices": [raw]}, **{"X-Total-Count": "3"})
    result = runtime.acquire_invoices(**kwargs)
    refused(result)
    assert result.reason == "unsupported_invoice"
    assert result.diagnostic_summary()["pagination_status"] == "not_admitted"
    t.requests.clear()
    t.responses = [response(COMPANY), response({"invoices": []})]
    result = runtime.acquire_invoices(**kwargs)
    assert result.diagnostic_summary()["pagination_status"] == "unverified"


@pytest.mark.parametrize("count,accepted", [(25, True), (26, False)])
def test_default_page_size_is_enforced_without_truncation(count, accepted):
    _, t, kwargs = setup()
    t.responses = [response(COMPANY), response(
        {"invoices": [invoice(n) for n in range(1, count + 1)]},
        **{"X-Total-Count": str(count)})]
    result = runtime.acquire_invoices(**kwargs)
    if accepted:
        assert result.status == "observed" and len(result.mappings) == count
    else:
        refused(result)
    assert len(t.requests) == 2


@pytest.mark.parametrize("count,accepted", [(1, True), (2, False)])
def test_explicit_page_size_is_enforced_without_truncation(count, accepted):
    _, t, kwargs = setup()
    total = str(2 + count)
    t.responses[1] = response({"invoices": [invoice(101), invoice(102)]}, **{
        "X-Total-Count": total,
        "Link": f'<{runtime.INVOICES_ENDPOINT}?page=2&per_page=1>; rel="next"'})
    t.responses[2] = response({"invoices": [invoice(103 + n) for n in range(count)]},
                              **{"X-Total-Count": total})
    result = runtime.acquire_invoices(**kwargs)
    if accepted:
        assert result.status == "observed" and len(result.mappings) == int(total)
    else:
        refused(result)
    assert len(t.requests) == 3


@pytest.mark.parametrize("relation,page", [("last", 1), ("first", 2), ("prev", 2), ("prev", 1)])
def test_contradictory_first_page_relations_refuse_before_next_request(relation, page):
    _, t, kwargs = setup()
    t.responses[1] = response({"invoices": [invoice(101), invoice(102)]}, **{
        "X-Total-Count": "3",
        "Link": f'<{runtime.INVOICES_ENDPOINT}?page=2>; rel="next", '
                f'<{runtime.INVOICES_ENDPOINT}?page={page}>; rel="{relation}"'})
    refused(runtime.acquire_invoices(**kwargs))
    assert len(t.requests) == 2


@pytest.mark.parametrize("previous,last,accepted", [(1, 2, True), (2, 2, False), (1, 1, False)])
def test_terminal_page_relation_identity(previous, last, accepted):
    _, t, kwargs = setup()
    t.responses[2] = response({"invoices": [invoice(103)]}, **{
        "X-Total-Count": "3",
        "Link": f'<{runtime.INVOICES_ENDPOINT}>; rel="first", '
                f'<{runtime.INVOICES_ENDPOINT}?page={previous}>; rel="prev", '
                f'<{runtime.INVOICES_ENDPOINT}?page={last}>; rel="last"'})
    result = runtime.acquire_invoices(**kwargs)
    if accepted:
        assert result.status == "observed" and len(result.mappings) == 3
    else:
        refused(result)


@pytest.mark.parametrize("current", [1, 2])
@pytest.mark.parametrize("last", [1, 2, 3, 20])
def test_terminal_requires_supplied_last_to_be_current(current, last):
    _, t, kwargs = setup()
    terminal = response({"invoices": [invoice(103)]}, **{
        "X-Total-Count": "1" if current == 1 else "3",
        "Link": f'<{runtime.INVOICES_ENDPOINT}?page={last}>; rel="last"'})
    if current == 1:
        t.responses = [response(COMPANY), terminal]
    else:
        t.responses[2] = terminal
    result = runtime.acquire_invoices(**kwargs)
    if last == current:
        assert result.status == "observed" and result.manifest.terminal_page_observed
    else:
        refused(result)
    assert len(t.requests) == current + 1


@pytest.mark.parametrize("bad", [True, "200", 201])
def test_mutated_response_status_is_revalidated(bad):
    _, t, kwargs = setup()
    object.__setattr__(t.responses[1], "status_code", bad)
    refused(runtime.acquire_invoices(**kwargs))


def test_payload_owned_after_transport_and_results_are_point_in_time():
    _, t, kwargs = setup()
    raw = invoice(101)
    t.responses = [response(COMPANY), response({"invoices": [raw]}, **{"X-Total-Count": "1"})]
    raw["reference"] = "Changed after encoding"
    result = runtime.acquire_invoices(**kwargs)
    assert result.status == "observed"
    assert result.mappings[0].document.document_number is None
    assert result.manifest.source_watermark is None
    with pytest.raises(AttributeError):
        result.status = "complete"
    with pytest.raises(TypeError):
        t.requests[0].headers["Authorization"] = "PRIVATE"


@pytest.mark.parametrize("bad_time", [NOW.replace(tzinfo=None), NOW - timedelta(seconds=1)])
def test_clock_cannot_hide_expiry_or_move_backwards(bad_time):
    _, t, kwargs = setup()
    values = iter([NOW, bad_time])
    kwargs["clock"] = lambda: next(values)
    refused(runtime.acquire_invoices(**kwargs))
    assert not t.requests


def test_dependency_error_of_own_error_type_still_cannot_leak():
    _, t, kwargs = setup()
    t.responses[2] = runtime.ReadRefusal("PRIVATE owner:1 fixture:reference")
    refused(runtime.acquire_invoices(**kwargs))


@pytest.mark.parametrize("limit", [1, 2])
def test_page_budget_refuses_without_extra_send(limit, monkeypatch):
    _, t, kwargs = setup()
    monkeypatch.setattr(runtime, "MAX_PAGES", limit)
    if limit == 2:
        t.responses[2] = response({"invoices": [invoice(103)]}, Link='<https://api.freeagent.com/v2/invoices?page=3>; rel="next"')
    refused(runtime.acquire_invoices(**kwargs))
    assert len(t.requests) <= limit + 1


@pytest.mark.parametrize("limit,value", [("MAX_RECORDS", 2), ("MAX_TOTAL_BYTES", 500)])
def test_aggregate_limits_do_not_return_partial_results(limit, value, monkeypatch):
    _, _, kwargs = setup()
    monkeypatch.setattr(runtime, limit, value)
    refused(runtime.acquire_invoices(**kwargs))


@pytest.mark.parametrize("total", ["2", "4", "0", "-1", "3.0", "1000", "PRIVATE"])
def test_count_contradictions_and_header_bounds(total):
    _, t, kwargs = setup()
    t.responses[2] = response({"invoices": [invoice(103)]}, **{"X-Total-Count": total})
    refused(runtime.acquire_invoices(**kwargs))


def test_twenty_page_limit_executes_exact_terminal_request():
    _, t, kwargs = setup()
    t.responses = [response(COMPANY)]
    for n in range(1, 21):
        headers = {"X-Total-Count": "20"}
        if n < 20:
            headers["Link"] = f'<https://api.freeagent.com/v2/invoices?page={n + 1}>; rel="next"'
        t.responses.append(response({"invoices": [invoice(n)]}, **headers))
    result = runtime.acquire_invoices(**kwargs)
    assert result.status == "observed" and result.manifest.page_count == 20
    assert len(t.requests) == 21 and len(result.mappings) == 20


def test_duplicate_within_page_and_unexpected_company_fields_refuse():
    for company_bad in (False, True):
        _, t, kwargs = setup()
        if company_bad:
            t.responses[0] = response({**COMPANY, "extra": "PRIVATE"})
        else:
            t.responses[1] = response({"invoices": [invoice(101), invoice(101)]})
        refused(runtime.acquire_invoices(**kwargs))


def test_no_default_transport_or_activation_and_no_hooks_from_binding_lookalike():
    import ast
    from pathlib import Path
    from reserved.providers.accounting.freeagent import FreeAgentProvider
    from reserved.providers.readiness import PROVIDERS
    assert next(p for p in PROVIDERS if p.name == "freeagent").implementation_enabled is False
    with pytest.raises(NotImplementedError):
        FreeAgentProvider().list_invoices("fixture:reference")
    class Lookalike:
        @property
        def owner_id(self):
            pytest.fail("Binding lookalike property executed")
    s, t, kwargs = setup()
    s.resolve = lambda reference: Lookalike()
    refused(runtime.acquire_invoices(**kwargs))
    assert not t.requests
    parsed = ast.parse(Path(runtime.__file__).read_text())
    forbidden = {"requests", "httpx", "socket", "sqlite3", "os", "flask"}
    for node in ast.walk(parsed):
        if isinstance(node, ast.Import):
            assert not ({alias.name.split(".")[0] for alias in node.names} & forbidden)
        if isinstance(node, ast.ImportFrom):
            assert (node.module or "").split(".")[0] not in forbidden
