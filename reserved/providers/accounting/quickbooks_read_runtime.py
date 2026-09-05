"""Injected-test QuickBooks acquisition; observations are not canonical imports.

Dependencies are explicitly supplied synthetic fixtures, not authenticated
custody, a network sandbox, or protection from arbitrary in-process code.
"""
from base64 import b64decode
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
import json
import re
from types import MappingProxyType
from unicodedata import category
from urllib.parse import urlencode

from ..http_boundary import EndpointPolicy, GuardedTransport, HttpMethod, ProviderRequest, ProviderResponse
from ..oauth_contracts import CredentialReference, CallbackStatus, validate_callback
from ..oauth_security import OAuthStateStore
from . import quickbooks_oauth_contract as oauth
from .quickbooks_observation_contract import observe_company_info
from .quickbooks_sync_evidence import QueryEntity, validate_query_run

VERSION = "quickbooks-injected-read/1.0"
ORIGIN = "https://sandbox-quickbooks.api.intuit.com"
PAGE_SIZE = 25
MAX_PAGES = 20
MAX_RECORDS = 250
MAX_BODY = 262144
MAX_TOTAL_BYTES = 2097152
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z")


class Refusal(ValueError):
    pass


def _ref(value):
    if type(value) is not str or _REF.fullmatch(value) is None:
        raise Refusal()
    return value


def _time(value):
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise Refusal()
    return value


def _reference(value):
    if type(value) is not CredentialReference or type(value.provider) is not str or value.provider != "quickbooks":
        raise Refusal()
    return CredentialReference("quickbooks", _ref(value.reference))


@dataclass(frozen=True, repr=False)
class FixtureBinding:
    owner_id: str
    realm_id: str
    credential: CredentialReference
    revision: int
    state: str
    expires_at: datetime


@dataclass(frozen=True, repr=False)
class FixtureTokenRecord:
    tokens: oauth.QuickBooksTokenSet
    received_at: datetime
    revision: int


def _binding_copy(value):
    if type(value) is not FixtureBinding:
        raise Refusal()
    return FixtureBinding(value.owner_id, value.realm_id, _reference(value.credential),
                          value.revision, value.state, value.expires_at)


def _token_copy(value):
    if type(value) is not oauth.QuickBooksTokenSet:
        raise Refusal()
    parsed = oauth.parse_token_response({name: getattr(value, name) for name in (
        "access_token", "refresh_token", "expires_in", "x_refresh_token_expires_in",
        "token_type", "x_refresh_token_hard_expires_in")})
    for secret in (parsed.access_token, parsed.refresh_token):
        if type(secret) is not str or any(not 33 <= ord(c) <= 126 for c in secret):
            raise Refusal()
    return parsed


@dataclass(frozen=True, repr=False)
class WirePageEvidence:
    request_identity: str
    request_start: int
    local_returned_count: int
    provider_start: int | None
    provider_returned_count: int | None
    provider_total_count: int | None
    provider_time: str | None
    wire_digest: str
    retrieved_at: datetime

    @property
    def position_origin(self):
        return "request_derived" if self.provider_start is None else "provider_cross_checked"

    @property
    def count_origin(self):
        return "array_counted" if self.provider_returned_count is None else "provider_cross_checked"


@dataclass(frozen=True, repr=False)
class Outcome:
    status: str
    credential: CredentialReference | None = None
    company: object = None
    query_evidence: object = None
    pages: tuple = ()
    company_wire_digest: str | None = None
    company_provider_time: str | None = None
    binding: FixtureBinding | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def diagnostic_summary(self):
        return {"version": VERSION, "status": self.status,
                "record_count": len(self.query_evidence.observations) if self.query_evidence else 0,
                "canonical_ingestion": False, "authenticated_membership": False,
                "snapshot_complete": False, "provider_enabled": False}


def _decode(body):
    if type(body) is not bytes or not body or len(body) > MAX_BODY:
        raise Refusal()
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
            if depth > 16:
                raise Refusal()
        elif byte in (93, 125):
            depth -= 1
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Refusal()
            result[key] = value
        return result
    def number(text):
        if len(text) > 32 or re.fullmatch(r"-?(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,12})?", text) is None:
            raise Refusal()
        return Decimal(text)
    def integer(text):
        return int(number(text))
    def forbidden(text):
        raise Refusal()
    # Explicit UTF-8: json.loads(bytes) also accepts other encodings.
    payload = json.loads(body.decode("utf-8"), object_pairs_hook=pairs,
                         parse_int=integer, parse_float=number, parse_constant=forbidden)
    nodes = 0
    def walk(value):
        nonlocal nodes
        nodes += 1
        if nodes > 15000:
            raise Refusal()
        if type(value) in (dict, list):
            if len(value) > 1000:
                raise Refusal()
            for child in (list(value.keys()) + list(value.values()) if type(value) is dict else value):
                walk(child)
        elif type(value) is str and (len(value) > 4096 or any(category(c).startswith("C") for c in value)):
            raise Refusal()
    walk(payload)
    return payload


def _provider_time(payload):
    if "time" not in payload:
        return None
    value = payload["time"]
    if type(value) is not str or _STAMP.fullmatch(value) is None:
        raise Refusal()
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value  # Preserve the provider offset; it is not our retrieval clock.


def _integer(value):
    if type(value) is not int or not 0 <= value <= 10**12:
        raise Refusal()
    return value


class InjectedQuickBooksRuntime:
    """Fixture custody owns full-set atomic CAS and updates the binding revision.

    Required methods: basic_authorization(); load(credential, expected_revision)
    -> FixtureTokenRecord; put/replace(credential, expected_binding, tokens,
    received_at) -> CredentialReference. Successful writes atomically install
    the entire set and active binding at exactly expected revision + 1. The
    binding_source.resolve(reference) is independent of CompanyInfo labels.
    No real store, caller authentication, secret erasure or rollback is provided.
    """
    def __init__(self, *, transport, custody, binding_source, clock, environment):
        self.transport, self.custody = transport, custody
        self.binding_source, self.clock, self.environment = binding_source, clock, environment

    def _enabled(self):
        if type(self.environment) is not str or self.environment != "injected_test":
            raise Refusal()

    def _operation_clock(self):
        last = None
        def tick():
            nonlocal last
            self._enabled()
            now = _time(self.clock())
            self._enabled()
            if last is not None and now < last:
                raise Refusal()
            last = now
            return now
        return tick

    def _snapshot(self, reference, owner, now, states):
        self._enabled()
        value = _binding_copy(self.binding_source.resolve(_reference(reference)))
        self._enabled()
        if type(value) is not FixtureBinding:
            raise Refusal()
        _ref(value.owner_id)
        if type(value.realm_id) is not str or re.fullmatch(r"[0-9]{1,32}", value.realm_id) is None:
            raise Refusal()
        _reference(value.credential)
        if (type(value.revision) is not int or not 1 <= value.revision < 10**9
                or type(value.state) is not str or value.state not in states
                or value.credential != reference or value.owner_id != owner
                or now >= _time(value.expires_at)):
            raise Refusal()
        return value

    def _guard(self, initial, tick, deadline=None):
        def check():
            now = tick()
            current = self._snapshot(initial.credential, initial.owner_id, now, {initial.state})
            if current != initial:
                raise Refusal()
            # Resolver calls may themselves advance time or change environment.
            now = tick()
            if now >= initial.expires_at or (deadline is not None and now >= deadline):
                raise Refusal()
            return now
        return check

    def _deadline(self, record, *, refresh=False):
        seconds = record.tokens.x_refresh_token_expires_in if refresh else record.tokens.expires_in
        if refresh and record.tokens.x_refresh_token_hard_expires_in is not None:
            seconds = min(seconds, record.tokens.x_refresh_token_hard_expires_in)
        return record.received_at + timedelta(seconds=seconds)

    def _load(self, initial, check, *, refresh=False):
        check()
        record = self.custody.load(_reference(initial.credential), expected_revision=initial.revision)
        if type(record) is not FixtureTokenRecord or type(record.revision) is not int or record.revision != initial.revision:
            raise Refusal()
        # Capture dependency-owned facts before calling another dependency.
        record = FixtureTokenRecord(_token_copy(record.tokens), _time(record.received_at), record.revision)
        now = check()
        tokens = record.tokens
        received = _time(record.received_at)
        lifetime = tokens.x_refresh_token_expires_in if refresh else tokens.expires_in
        if now < received or now >= received + timedelta(seconds=lifetime):
            raise Refusal()
        if refresh and tokens.x_refresh_token_hard_expires_in is not None and now >= received + timedelta(seconds=tokens.x_refresh_token_hard_expires_in):
            raise Refusal()
        return record

    def _request(self, *, kind, initial, tick, check, form=None, start=None):
        check()
        if kind == "token":
            method, url = HttpMethod.POST, oauth.TOKEN_ENDPOINT
            auth = self.custody.basic_authorization()
            if type(auth) is not str or not auth.startswith("Basic ") or len(auth) > 4096:
                raise Refusal()
            decoded = b64decode(auth[6:], validate=True)
            if len(decoded.split(b":", 1)) != 2 or not all(decoded.split(b":", 1)) or any(c < 32 or c > 126 for c in decoded):
                raise Refusal()
            headers = {"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
            body = urlencode(form).encode("ascii")
        else:
            record = self._load(initial, check)
            auth = "Bearer " + record.tokens.access_token
            method, body, headers = HttpMethod.GET, None, {"Accept": "application/json"}
            prefix = ORIGIN + "/v3/company/" + initial.realm_id
            if kind == "company":
                url = prefix + "/companyinfo/" + initial.realm_id + "?minorversion=75"
            elif kind == "query" and type(start) is int and 1 <= start <= MAX_RECORDS + 1:
                statement = f"SELECT * FROM Invoice STARTPOSITION {start} MAXRESULTS {PAGE_SIZE}"
                url = prefix + "/query?" + urlencode({"query": statement, "minorversion": "75"})
            else:
                raise Refusal()
        headers["Authorization"] = auth
        check()
        guarded = GuardedTransport(EndpointPolicy("quickbooks", "test", frozenset({
            ORIGIN, "https://oauth.platform.intuit.com"})), self.transport)
        response = guarded.send(ProviderRequest(method, url, headers, body))
        check()
        if type(response) is not ProviderResponse or type(response.status_code) is not int or response.status_code != 200:
            raise Refusal()
        if type(response.headers) is not MappingProxyType or not 1 <= len(response.headers) <= 32:
            raise Refusal()
        lowered = {}
        for key, value in response.headers.items():
            if (type(key) is not str or re.fullmatch(r"[A-Za-z0-9_-]{1,64}", key) is None
                    or key.lower() in lowered or type(value) is not str or len(value) > 4096
                    or any(ord(c) < 32 or ord(c) > 126 for c in value)):
                raise Refusal()
            lowered[key.lower()] = value
        content = lowered.get("content-type", "").lower().replace(" ", "")
        if content not in ("application/json", "application/json;charset=utf-8") or "content-encoding" in lowered or "location" in lowered:
            raise Refusal()
        # Ordinary bounded headers are ignored, never persisted or used as authority.
        payload = _decode(response.body)
        check()
        return payload, sha256(response.body).hexdigest(), len(response.body), tick()

    def _token(self, initial, tick, check, form):
        payload, _, _, received = self._request(kind="token", initial=initial, tick=tick, check=check, form=form)
        if type(payload) is not dict or "error" in payload or "Fault" in payload:
            raise Refusal()
        tokens = oauth.parse_token_response(payload)
        if any(any(not 33 <= ord(c) <= 126 for c in secret) for secret in (tokens.access_token, tokens.refresh_token)):
            raise Refusal()
        return tokens, received

    def _store(self, method, initial, tokens, received, tick, check):
        # Keep private expected values distinct from custody's writable aliases.
        tokens = _token_copy(tokens)
        check()
        reference = _reference(method(credential=_reference(initial.credential), expected_binding=_binding_copy(initial),
                                      tokens=_token_copy(tokens), received_at=received))
        if reference != initial.credential:
            raise Refusal()
        current = self._snapshot(reference, initial.owner_id, tick(), {"active"})
        if (current.realm_id != initial.realm_id or current.revision != initial.revision + 1
                or current.expires_at != initial.expires_at):
            raise Refusal()
        final_check = self._guard(current, tick)
        record = self._load(current, final_check)
        if record.tokens != tokens or record.received_at != received:
            raise Refusal()
        final_check = self._guard(current, tick, self._deadline(record))
        final_check()
        return current, final_check

    def complete_callback(self, *, credential, owner_id, parameters, state_store, redirect_uri):
        try:
            tick = self._operation_clock()
            started = tick()
            reference, owner = _reference(credential), _ref(owner_id)
            initial = self._snapshot(reference, owner, started, {"pending"})
            check = self._guard(initial, tick)
            if type(state_store) is not OAuthStateStore or type(state_store.ttl_seconds) is not int or not 0 < state_store.ttl_seconds <= 300:
                raise Refusal()
            if type(parameters) is not dict or len(parameters) > 4:
                raise Refusal()
            for key, value in parameters.items():
                if type(key) is not str or type(value) is not str or not 0 < len(value) <= 512:
                    raise Refusal()
            callback = validate_callback(provider="quickbooks", parameters=parameters,
                                         state_store=state_store, now=int(check().timestamp()))
            if callback.status is not CallbackStatus.AUTHORISED:
                raise Refusal()
            # Consume before later parse/binding/transport failures; no public code shortcut.
            code = callback.code.consume()
            parsed = oauth.parse_callback(parameters, expected_state=parameters["state"])
            if type(parsed) is not oauth.SuccessfulCallback or parsed.realm_id != initial.realm_id or parsed.code != code:
                raise Refusal()
            tokens, received = self._token(initial, tick, check, oauth.code_exchange_body(code=code, redirect_uri=redirect_uri))
            current, final_check = self._store(self.custody.put, initial, tokens, received, tick, check)
            finished = final_check()
            return Outcome("reference_stored", credential=reference, binding=current, started_at=started, finished_at=finished)
        except Exception:
            return Outcome("callback_refused")

    def refresh(self, *, credential, owner_id):
        try:
            tick = self._operation_clock()
            started = tick()
            initial = self._snapshot(_reference(credential), _ref(owner_id), started, {"active", "refresh_required"})
            check = self._guard(initial, tick)
            previous = self._load(initial, check, refresh=True)
            check = self._guard(initial, tick, self._deadline(previous, refresh=True))
            tokens, received = self._token(initial, tick, check, oauth.refresh_body(refresh_token=previous.tokens.refresh_token))
            if self._load(initial, check, refresh=True) != previous:
                raise Refusal()
            tokens = oauth.replace_token_set(previous.tokens, tokens)
            current, final_check = self._store(self.custody.replace, initial, tokens, received, tick, check)
            finished = final_check()
            return Outcome("reference_rotated", credential=initial.credential, binding=current, started_at=started, finished_at=finished)
        except Exception:
            return Outcome("refresh_refused")

    def acquire(self, *, credential, owner_id, request_identity):
        try:
            tick = self._operation_clock()
            started = tick()
            run = _ref(request_identity)
            initial = self._snapshot(_reference(credential), _ref(owner_id), started, {"active"})
            check = self._guard(initial, tick)
            initial_tokens = self._load(initial, check)
            check = self._guard(initial, tick, self._deadline(initial_tokens))
            kwargs = dict(binding=oauth.RealmBinding(initial.owner_id, initial.realm_id, initial.credential.reference),
                          user_id=initial.owner_id, realm_id=initial.realm_id, credential_reference=initial.credential.reference)
            payload, company_digest, total_bytes, retrieved = self._request(kind="company", initial=initial, tick=tick, check=check)
            if type(payload) is not dict or not {"CompanyInfo"} <= set(payload) <= {"CompanyInfo", "time"}:
                raise Refusal()
            company_time = _provider_time(payload)
            company = observe_company_info(payload["CompanyInfo"], retrieved_at=retrieved, **kwargs)
            pages, local, times, start, ids = [], [], [], 1, set()
            for _ in range(MAX_PAGES):
                payload, digest, size, retrieved = self._request(kind="query", initial=initial, tick=tick, check=check, start=start)
                total_bytes += size
                if total_bytes > MAX_TOTAL_BYTES or type(payload) is not dict or not {"QueryResponse"} <= set(payload) <= {"QueryResponse", "time"}:
                    raise Refusal()
                provider_time = _provider_time(payload)
                query = payload["QueryResponse"]
                if type(query) is not dict or not set(query) <= {"Invoice", "startPosition", "maxResults", "totalCount"}:
                    raise Refusal()
                records = query.get("Invoice", [])
                # Only exactly {} supports an absent entity collection, not a malformed metadata-only page.
                if ("Invoice" not in query and query) or type(records) is not list or len(records) > PAGE_SIZE:
                    raise Refusal()
                if len(ids) + len(records) > MAX_RECORDS:
                    raise Refusal()
                pstart = _integer(query["startPosition"]) if "startPosition" in query else None
                count = _integer(query["maxResults"]) if "maxResults" in query else None
                total = _integer(query["totalCount"]) if "totalCount" in query else None
                if (pstart is not None and pstart != start) or (count is not None and count != len(records)) or (total is not None and total < len(records)):
                    raise Refusal()
                for raw in records:
                    if type(raw) is not dict or type(raw.get("Id")) is not str or raw["Id"] in ids:
                        raise Refusal()
                    ids.add(raw["Id"])
                local.append({"requestIdentity": run, "startPosition": start, "maxResults": len(records), "Invoice": records})
                times.append(retrieved)
                pages.append(WirePageEvidence(run, start, len(records), pstart, count, total, provider_time, digest, retrieved))
                check()
                if len(records) < PAGE_SIZE:
                    evidence = validate_query_run(tuple(local), entity=QueryEntity.INVOICE, request_identity=run,
                        requested_page_size=PAGE_SIZE, retrieved_at=tuple(times), **kwargs)
                    self._load(initial, check)
                    finished = check()
                    return Outcome("observed", company=company, query_evidence=evidence, pages=tuple(pages),
                        company_wire_digest=company_digest, company_provider_time=company_time,
                        binding=initial, started_at=started, finished_at=finished)
                start += len(records)
            raise Refusal()
        except Exception:
            return Outcome("acquisition_refused")
