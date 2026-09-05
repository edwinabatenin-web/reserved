"""Injected-test acquisition execution, not authenticated/live FreeAgent access.

The injected binding source and transport are fixture dependencies, not custody
or membership authorities. No transport implementation or token handling exists
here. API URLs describe requests as data; sandbox compatibility is not inferred.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from types import MappingProxyType
from urllib.parse import urlsplit, parse_qsl

from ..http_boundary import EndpointPolicy, GuardedTransport, HttpMethod, ProviderRequest, ProviderResponse
from ..oauth_contracts import CredentialReference
from ..import_evidence import ImportManifest, ImportScope
from .freeagent_invoice_contract import COMPANY_ENDPOINT, INVOICES_ENDPOINT, parse_company, parse_invoice_list, validate_pagination
from .freeagent_invoice_adapter import observe_invoice, adapt_invoice
from .freeagent_resilience import decide_pagination

VERSION = "freeagent-injected-read/1.0"
MAX_BODY = 65536
MAX_TOTAL_BYTES = 1048576
MAX_PAGES = 20
MAX_RECORDS = 500
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


class ReadRefusal(ValueError):
    """Fixed diagnostic only, never dependency exception text."""


@dataclass(frozen=True, repr=False)
class FixtureBinding:
    owner_id: str
    connection_id: str
    business_id: str
    company_id: str | int
    credential: CredentialReference
    revision: int
    state: str
    expires_at: datetime


@dataclass(frozen=True, repr=False)
class ReadResult:
    status: str
    reason: str
    mappings: tuple = ()
    manifest: ImportManifest | None = None
    page_digests: tuple[str, ...] = ()
    company_digest: str | None = None
    request_count: int = 0
    company_retrieved_at: datetime | None = None
    page_retrieved_at: tuple[datetime, ...] = ()
    binding_revision: int | None = None
    annual_income_complete: bool = False
    authenticated_membership: bool = False

    def diagnostic_summary(self):
        # Deliberately not ImportManifest.evidence_summary(), which contains
        # caller references. No raw URL/header/body or dependency exception.
        return {"version": VERSION, "status": self.status, "reason": self.reason,
                "request_count": self.request_count, "document_count": len(self.mappings),
                "pagination_status": self.manifest.status.value if self.manifest else "not_admitted",
                "annual_income_complete": False, "authenticated_membership": False}


def _ref(value):
    if type(value) is not str or _REF.fullmatch(value) is None:
        raise ReadRefusal("invalid_context")
    return value


def _time(value):
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise ReadRefusal("invalid_clock")
    return value


def _credential(value):
    if type(value) is not CredentialReference or type(value.provider) is not str or value.provider != "freeagent":
        raise ReadRefusal("invalid_reference")
    return CredentialReference("freeagent", _ref(value.reference))


def _binding(value):
    if type(value) is not FixtureBinding:
        raise ReadRefusal("invalid_binding")
    company = value.company_id
    if not ((type(company) is int and 0 < company <= 9999999999) or
            (type(company) is str and re.fullmatch(r"[1-9][0-9]{0,9}", company))):
        raise ReadRefusal("invalid_binding")
    if type(value.revision) is not int or not 0 < value.revision <= 9999999999:
        raise ReadRefusal("invalid_binding")
    if type(value.state) is not str or value.state != "active":
        raise ReadRefusal("binding_unavailable")
    return FixtureBinding(_ref(value.owner_id), _ref(value.connection_id), _ref(value.business_id),
                          company, _credential(value.credential), value.revision, value.state,
                          _time(value.expires_at))


def _url(url, *, company=False):
    if type(url) is not str or len(url) > 512:
        raise ReadRefusal("invalid_destination")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "api.freeagent.com" or
            parsed.fragment or "%" in url or any(ord(c) < 33 or ord(c) > 126 for c in url)):
        raise ReadRefusal("invalid_destination")
    if company:
        if url != COMPANY_ENDPOINT:
            raise ReadRefusal("invalid_destination")
    else:
        if parsed.path != "/v2/invoices":
            raise ReadRefusal("invalid_destination")
        pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
        if len(pairs) > 2 or len(dict(pairs)) != len(pairs):
            raise ReadRefusal("invalid_destination")
        for key, value in pairs:
            if key not in ("page", "per_page") or re.fullmatch(r"[1-9][0-9]{0,2}", value) is None:
                raise ReadRefusal("invalid_destination")
            if int(value) > (MAX_PAGES if key == "page" else 100):
                raise ReadRefusal("invalid_destination")
    return url


def _json(body):
    if type(body) is not bytes or len(body) > MAX_BODY:
        raise ReadRefusal("body_bounds")
    # Bound nesting before the JSON parser allocates deeply nested containers.
    depth, quoted, escaped = 0, False, False
    for byte in body:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            if depth > 8:
                raise ReadRefusal("json_bounds")
        elif byte in (93, 125):
            depth -= 1
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ReadRefusal("duplicate_json_key")
            result[key] = value
        return result
    def integer(value):
        if len(value) > 10:
            raise ReadRefusal("json_bounds")
        return int(value)
    def forbidden(value):
        raise ReadRefusal("unsupported_json_number")
    result = json.loads(body, object_pairs_hook=pairs, parse_int=integer,
                        parse_float=forbidden, parse_constant=forbidden)
    nodes = 0
    def walk(value):
        nonlocal nodes
        nodes += 1
        if nodes > 5000:
            raise ReadRefusal("json_bounds")
        if type(value) in (dict, list):
            if len(value) > 100:
                raise ReadRefusal("json_bounds")
            for child in (list(value.keys()) + list(value.values()) if type(value) is dict else value):
                walk(child)
        elif type(value) is str and (len(value) > 2048 or any(ord(c) < 32 for c in value)):
            raise ReadRefusal("json_bounds")
    walk(result)
    return result


def _response(response):
    if type(response) is not ProviderResponse or type(response.status_code) is not int:
        raise ReadRefusal("invalid_response")
    if response.status_code != 200:
        raise ReadRefusal("response_not_successful")
    if type(response.headers) is not MappingProxyType or len(response.headers) > 4:
        raise ReadRefusal("invalid_headers")
    headers = {}
    for key, value in response.headers.items():
        if type(key) is not str or type(value) is not str or len(value) > 4096:
            raise ReadRefusal("invalid_headers")
        name = key.lower()
        if name not in ("content-type", "link", "x-total-count") or name in headers or any(ord(c) < 32 for c in value):
            raise ReadRefusal("invalid_headers")
        headers[name] = value
    if headers.get("content-type") not in ("application/json", "application/json; charset=utf-8"):
        raise ReadRefusal("invalid_headers")
    if "x-total-count" in headers and re.fullmatch(r"(?:0|[1-9][0-9]{0,2})", headers["x-total-count"]) is None:
        raise ReadRefusal("invalid_headers")
    body = response.body
    payload = _json(body)
    return payload, headers, sha256(body).hexdigest(), len(body)


def acquire_invoices(*, credential, owner_id, connection_id, import_run_id,
                     binding_source, transport, clock, environment="injected_test"):
    """Execute one bounded, all-or-nothing, fixture-bound import.

    binding_source.resolve(reference) independently supplies a FixtureBinding.
    transport.send(ProviderRequest) is an explicitly supplied in-process fixture;
    it is not authenticated by this executor. No defaults or network client.
    Returned evidence is a call-time snapshot, not a revocable/live capability.
    """
    requests = 0
    try:
        if type(environment) is not str or environment != "injected_test":
            raise ReadRefusal("unsupported_environment")
        reference = _credential(credential)
        owner, connection, run = _ref(owner_id), _ref(connection_id), _ref(import_run_id)
        started = _time(clock())
        initial = _binding(binding_source.resolve(reference))
        if initial.owner_id != owner or initial.connection_id != connection or initial.credential != reference:
            raise ReadRefusal("binding_mismatch")
        last_time = started
        def check():
            nonlocal last_time
            now = _time(clock())
            current = _binding(binding_source.resolve(reference))
            if now < last_time:
                raise ReadRefusal("invalid_clock")
            last_time = now
            if current != initial or type(current.company_id) is not type(initial.company_id):
                raise ReadRefusal("binding_changed")
            if now >= initial.expires_at:
                raise ReadRefusal("binding_expired")
            return now
        guarded = GuardedTransport(EndpointPolicy("freeagent", "test", frozenset({"https://api.freeagent.com"})), transport)
        total_bytes = 0
        def fetch(url, *, company=False):
            nonlocal requests, total_bytes
            _url(url, company=company)
            check()
            requests += 1
            response = guarded.send(ProviderRequest(HttpMethod.GET, url, {"Accept": "application/json"}))
            retrieved = check()
            payload, headers, digest, size = _response(response)
            total_bytes += size
            if total_bytes > MAX_TOTAL_BYTES:
                raise ReadRefusal("import_bounds")
            return payload, headers, digest, retrieved
        company, headers, company_digest, company_retrieved = fetch(COMPANY_ENDPOINT, company=True)
        if set(headers) != {"content-type"} or type(company) is not dict or set(company) != {"company"}:
            raise ReadRefusal("invalid_company")
        parsed_company = parse_company(company)
        if (parsed_company.unknown_fields or type(parsed_company.id) is not type(initial.company_id)
                or parsed_company.id != initial.company_id):
            raise ReadRefusal("company_mismatch")
        documents, digests, retrievals, ids, cursors = [], [], [], set(), set()
        requested_invoice_urls = set()
        url, current, total_count = INVOICES_ENDPOINT, None, None
        fetched = 0
        for page in range(1, MAX_PAGES + 1):
            # Actual destinations include the initial collection URL, unlike
            # the shared pagination contract's returned-next-cursor history.
            if url in requested_invoice_urls:
                raise ReadRefusal("repeated_destination")
            query = dict(parse_qsl(urlsplit(url).query))
            if page > 1 and ("page" not in query or int(query["page"]) != page):
                raise ReadRefusal("page_order_mismatch")
            requested_invoice_urls.add(url)
            payload, headers, digest, retrieved = fetch(url)
            digests.append(digest)
            retrievals.append(retrieved)
            if type(payload) is not dict or set(payload) != {"invoices"}:
                raise ReadRefusal("invalid_invoice_envelope")
            records = parse_invoice_list(payload)
            # The documented default is 25; an explicit per_page sets the
            # maximum records for this request, not an aggregate import cap.
            if len(records) > int(query.get("per_page", "25")):
                raise ReadRefusal("page_size_mismatch")
            fetched += len(records)
            if fetched > MAX_RECORDS:
                raise ReadRefusal("import_bounds")
            pagination = validate_pagination(page=1 if page == 1 else query["page"], per_page=query.get("per_page"),
                                             link_header=headers.get("link"), total_count=headers.get("x-total-count"))
            if page == 1:
                total_count = pagination.total_count
            elif pagination.total_count != total_count:
                raise ReadRefusal("source_total_changed")
            for target in (pagination.next_url, pagination.prev_url, pagination.first_url, pagination.last_url):
                if target is not None:
                    _url(target)
            relation_pages = {}
            for relation, target in (("first", pagination.first_url),
                                     ("prev", pagination.prev_url),
                                     ("last", pagination.last_url)):
                if target is not None:
                    relation_pages[relation] = int(dict(parse_qsl(urlsplit(target).query)).get("page", "1"))
            if (relation_pages.get("first", 1) != 1
                    or ("prev" in relation_pages and (page == 1 or relation_pages["prev"] != page - 1))
                    or ("last" in relation_pages and relation_pages["last"] < page)
                    or (pagination.next_url is None and "last" in relation_pages
                        and relation_pages["last"] != page)):
                raise ReadRefusal("page_relation_mismatch")
            decision = decide_pagination(pagination=pagination, page_number=page, fetched_count=fetched,
                                         current_cursor=current, seen_cursors=frozenset(cursors), max_pages=MAX_PAGES)
            if decision.next_url is not None:
                if decision.next_url in requested_invoice_urls:
                    raise ReadRefusal("repeated_destination")
                next_page = dict(parse_qsl(urlsplit(decision.next_url).query)).get("page")
                if next_page is None or int(next_page) != page + 1:
                    raise ReadRefusal("page_order_mismatch")
                if "last" in relation_pages and relation_pages["last"] < int(next_page):
                    raise ReadRefusal("page_relation_mismatch")
            for raw, record in zip(payload["invoices"], records):
                if record.url in ids:
                    raise ReadRefusal("duplicate_document")
                ids.add(record.url)
                context = dict(user_id=owner, connected_organisation_id=connection, business_id=initial.business_id,
                               company_id=initial.company_id, import_run_id=run, retrieved_at=retrieved)
                try:
                    observed = observe_invoice(company, {"invoices": [raw]}, **context)
                    documents.append(adapt_invoice(company, {"invoices": [raw]}, observation=observed, **context))
                except Exception:
                    raise ReadRefusal("unsupported_invoice") from None
            check()
            if decision.next_url is None:
                completed = check()
                manifest = ImportManifest(run, ImportScope("freeagent", "test", initial.business_id, "invoices"),
                                          started, completed, page, fetched, len(ids), True, total_count)
                return ReadResult("observed", "snapshot_not_annual_income_authority", tuple(documents),
                                  manifest, tuple(digests), company_digest, requests,
                                  company_retrieved, tuple(retrievals), initial.revision)
            if not records:
                raise ReadRefusal("empty_nonterminal_page")
            url = decision.next_url
            cursors.add(url)
            current = url
        raise ReadRefusal("import_bounds")
    except Exception as error:
        # No partial successful documents survive a dependency failure. This
        # deliberately excludes KeyboardInterrupt/SystemExit and promises no
        # protection against arbitrary malicious in-process dependency code.
        # Only exact internally used literals may escape. Dependencies may
        # raise this public error type too, so never copy arbitrary messages.
        reason = "acquisition_not_admitted"
        if type(error) is ReadRefusal and len(error.args) == 1 and type(error.args[0]) is str and error.args[0] in (
            "unsupported_invoice", "duplicate_document", "source_total_changed",
            "binding_unavailable", "binding_changed", "binding_expired",
            "binding_mismatch", "company_mismatch", "unsupported_environment",
        ):
            reason = error.args[0]
        return ReadResult("refused", reason, request_count=requests)
