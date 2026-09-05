"""Executable injected-test Xero acquisition; no live custody or membership.

All dependencies are explicitly supplied synthetic fixtures. Secrets exist only
transiently in token/request custody operations, never result or diagnostics.
"""
from base64 import b64decode
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Context, Decimal, localcontext
from hashlib import sha256
import json
import re
from types import MappingProxyType
from urllib.parse import urlencode

from ..http_boundary import EndpointPolicy, GuardedTransport, HttpMethod, ProviderRequest, ProviderResponse
from ..oauth_contracts import (CredentialReference, OAuthTokenSet, CallbackStatus,
                              validate_callback, exchange_and_store, refresh_and_rotate)
from ..oauth_security import OAuthStateStore
from ..import_evidence import ImportScope, ImportManifest
from . import xero_oauth_contract as oauth
from .xero_invoice_contract import map_detailed_invoice_response
from .normalisation import normalise_document

VERSION = "xero-injected-read/1.0"
INVOICES_ENDPOINT = "https://api.xero.com/api.xro/2.0/Invoices"
PAGE_SIZE = 25
MAX_PAGES = 20
MAX_RECORDS = 250
MAX_BODY = 262144
MAX_TOTAL_BYTES = 2097152
_REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


class Refusal(ValueError):
    pass


class ResponseFailure(Refusal):
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
    if type(value) is not CredentialReference or type(value.provider) is not str or value.provider != "xero":
        raise Refusal()
    return CredentialReference("xero", _ref(value.reference))


@dataclass(frozen=True, repr=False)
class FixtureBinding:
    owner_id: str
    connection_id: str
    tenant_id: str
    auth_event_id: str
    credential: CredentialReference
    revision: int
    state: str
    expires_at: datetime


def _binding(value):
    if type(value) is not FixtureBinding or type(value.revision) is not int or not 0 < value.revision <= 999999999:
        raise Refusal()
    if type(value.state) is not str or value.state not in ("active", "refresh_required"):
        raise Refusal()
    return FixtureBinding(_ref(value.owner_id), _ref(value.connection_id), _ref(value.tenant_id),
                          _ref(value.auth_event_id), _reference(value.credential), value.revision,
                          value.state, _time(value.expires_at))


@dataclass(frozen=True, repr=False)
class Outcome:
    status: str
    credential: CredentialReference | None = None
    documents: tuple = ()
    observations: tuple = ()
    manifest: ImportManifest | None = None
    response_digests: tuple[str, ...] = ()
    retrieved_at: tuple[datetime, ...] = ()
    tenant_id: str | None = None
    connection_id: str | None = None
    auth_event_id: str | None = None
    binding_revision: int | None = None
    failure: str | None = None

    def diagnostic_summary(self):
        return {"version": VERSION, "status": self.status, "failure": self.failure, "document_count": len(self.documents),
                "pagination_status": self.manifest.status.value if self.manifest else "not_admitted",
                "annual_income_complete": False, "authenticated_membership": False}


def _failed(status, error):
    reason = "operation_not_admitted"
    if type(error) is ResponseFailure and len(error.args) == 1 and type(error.args[0]) is str and error.args[0] in (
        "http_401", "http_403", "http_429", "http_5xx", "http_other",
    ):
        reason = error.args[0]
    return Outcome(status, failure=reason)


def _decode(body):
    if type(body) is not bytes or len(body) > MAX_BODY:
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
            if depth > 12:
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
        # Bounded lexical precision before Decimal construction; no float or
        # huge exponents. This is a conservative transport support boundary.
        if len(text) > 32 or re.fullmatch(r"-?(?:0|[1-9][0-9]{0,17})(?:\.[0-9]{1,8})?", text) is None:
            raise Refusal()
        return Decimal(text)
    def integer(text):
        value = number(text)
        return int(value)
    def forbidden(text):
        raise Refusal()
    payload = json.loads(body, object_pairs_hook=pairs, parse_int=integer,
                         parse_float=number, parse_constant=forbidden)
    nodes = 0
    def walk(value):
        nonlocal nodes
        nodes += 1
        if nodes > 10000:
            raise Refusal()
        if type(value) in (dict, list):
            if len(value) > 250:
                raise Refusal()
            for child in (list(value.keys()) + list(value.values()) if type(value) is dict else value):
                walk(child)
        elif type(value) is str and (len(value) > 4096 or any(ord(c) < 32 for c in value)):
            raise Refusal()
    walk(payload)
    return payload


class InjectedXeroRuntime:
    """No default dependencies; fixtures own synthetic secrets and atomic CAS.

    custody implements neutral put/replace plus basic_authorization(),
    access_authorization(reference) and refresh_token(reference). binding_source
    resolve(reference) supplies a versioned FixtureBinding independently of
    provider labels. Neither dependency is authenticated by this runtime.
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
            if last is not None and now < last:
                raise Refusal()
            last = now
            return now
        return tick

    def _snapshot(self, reference, owner, *, now, refresh=False):
        self._enabled()
        value = _binding(self.binding_source.resolve(reference))
        if value.credential != reference or value.owner_id != owner or now >= value.expires_at:
            raise Refusal()
        if not refresh and value.state != "active":
            raise Refusal()
        return value

    def _guard(self, reference, owner, initial, *, tick, refresh=False):
        def check():
            now = tick()
            if self._snapshot(reference, owner, refresh=refresh, now=now) != initial:
                raise Refusal()
            return now
        return check

    def _request(self, kind, *, tick, reference=None, form=None, tenant=None, page=None, check=lambda: None):
        self._enabled()
        tick()
        check()
        if kind == "token":
            url, method = oauth.TOKEN_ENDPOINT, HttpMethod.POST
            authorization = self.custody.basic_authorization()
            prefix = "Basic "
            headers = {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"}
            body = urlencode(form).encode("ascii")
        elif kind in ("connections", "invoices"):
            url, method = oauth.CONNECTIONS_ENDPOINT, HttpMethod.GET
            if kind == "invoices":
                if type(page) is not int or not 1 <= page <= MAX_PAGES:
                    raise Refusal()
                url = INVOICES_ENDPOINT + f"?page={page}&pageSize={PAGE_SIZE}"
            authorization = self.custody.access_authorization(reference)
            prefix = "Bearer "
            headers = {"Accept": "application/json"}
            if kind == "invoices":
                headers["xero-tenant-id"] = _ref(tenant)
            body = None
        else:
            raise Refusal()
        if (type(authorization) is not str or not authorization.startswith(prefix)
                or not 0 < len(authorization) - len(prefix) <= 4096
                or any(ord(c) < 33 or ord(c) > 126 for c in authorization[len(prefix):])):
            raise Refusal()
        headers["Authorization"] = authorization
        if kind == "token":
            decoded = b64decode(authorization[len(prefix):], validate=True)
            parts = decoded.split(b":", 1)
            if len(parts) != 2 or not all(parts) or any(byte < 32 or byte == 127 for byte in decoded):
                raise Refusal()
        self._enabled()
        tick()
        check()
        guarded = GuardedTransport(EndpointPolicy("xero", "test", frozenset({
            "https://identity.xero.com", "https://api.xero.com"})), self.transport)
        # Only the exact fixed kind/method/path/query/header combinations above
        # are constructed. No caller-supplied URL or redirect is delegated.
        response = guarded.send(ProviderRequest(method, url, headers, body))
        self._enabled()
        tick()
        check()
        if type(response) is not ProviderResponse or type(response.status_code) is not int:
            raise Refusal()
        if response.status_code != 200:
            status = response.status_code
            raise ResponseFailure(f"http_{status}" if status in (401, 403, 429) else "http_5xx" if 500 <= status <= 599 else "http_other")
        if type(response.headers) is not MappingProxyType or len(response.headers) != 1:
            raise Refusal()
        key, value = next(iter(response.headers.items()))
        if type(key) is not str or key.lower() != "content-type" or type(value) is not str or value not in (
            "application/json", "application/json; charset=utf-8"):
            raise Refusal()
        body = response.body
        payload = _decode(body)
        self._enabled()
        check()
        return payload, sha256(body).hexdigest(), len(body), tick()

    def _token(self, form, *, tick, check=lambda: None):
        payload, _, _, _ = self._request("token", form=form, tick=tick, check=check)
        if type(payload) is not dict or set(payload) != {"access_token", "refresh_token", "expires_in", "token_type"}:
            raise Refusal()
        tokens = oauth.parse_token_response(payload)
        if any(len(value) > 4096 or any(ord(char) < 33 or ord(char) > 126 for char in value)
               for value in (tokens.access_token, tokens.refresh_token)):
            raise Refusal()
        return OAuthTokenSet(tokens.access_token, tokens.refresh_token, tokens.expires_in)

    def complete_callback(self, *, owner_id, parameters, state_store, redirect_uri):
        """Compose state validation internally; no raw/typed-code shortcut API.

        The supplied session/state store and owner still require an authenticated
        application caller. A legacy consumed-code type alone is not proof.
        """
        try:
            self._enabled()
            tick = self._operation_clock()
            tick()
            owner = _ref(owner_id)
            if type(state_store) is not OAuthStateStore or type(state_store.ttl_seconds) is not int or not 0 < state_store.ttl_seconds <= 300:
                raise Refusal()
            if type(parameters) is not dict or set(parameters) - {"state", "code", "error"}:
                raise Refusal()
            copied = {}
            for key, value in parameters.items():
                if type(key) is not str or type(value) is not str or not 0 < len(value) <= 4096:
                    raise Refusal()
                copied[key] = value
            callback = validate_callback(provider="xero", parameters=copied, state_store=state_store,
                                         now=int(tick().timestamp()))
            if callback.status is not CallbackStatus.AUTHORISED:
                raise Refusal()
            runtime = self
            class Exchange:
                def exchange(self, code, redirect_uri):
                    return runtime._token(oauth.code_exchange_body(code=code, redirect_uri=redirect_uri), tick=tick)
            reference = _reference(exchange_and_store(provider="xero", user_id=owner,
                redirect_uri=redirect_uri, code=callback.code, exchanger=Exchange(), token_store=self.custody))
            self._snapshot(reference, owner, now=tick())
            return Outcome("reference_stored", credential=reference)
        except Exception as error:
            return _failed("callback_refused", error)

    def refresh(self, *, credential, owner_id):
        try:
            self._enabled()
            tick = self._operation_clock()
            started = tick()
            reference, owner = _reference(credential), _ref(owner_id)
            initial = self._snapshot(reference, owner, now=started, refresh=True)
            check = self._guard(reference, owner, initial, tick=tick, refresh=True)
            runtime = self
            class Refresh:
                def refresh(self, credential):
                    check()
                    token = runtime.custody.refresh_token(credential)
                    if type(token) is not str or not 0 < len(token) <= 4096:
                        raise Refusal()
                    check()
                    return runtime._token(oauth.refresh_body(refresh_token=token), tick=tick, check=check)
            class Store:
                def replace(self, *, credential, tokens):
                    check()
                    runtime.custody.replace(credential=credential, tokens=tokens)
            refresh_and_rotate(credential=reference, refresher=Refresh(), token_store=Store())
            current = self._snapshot(reference, owner, now=tick())
            if (current.owner_id, current.connection_id, current.tenant_id, current.auth_event_id, current.credential) != (
                initial.owner_id, initial.connection_id, initial.tenant_id, initial.auth_event_id, initial.credential
            ) or current.revision <= initial.revision:
                raise Refusal()
            return Outcome("reference_rotated", credential=reference)
        except Exception as error:
            return _failed("refresh_refused", error)

    def acquire(self, *, credential, owner_id, auth_event_id, tenant_id, import_run_id):
        try:
            self._enabled()
            tick = self._operation_clock()
            started = tick()
            reference, owner = _reference(credential), _ref(owner_id)
            event, tenant, run = _ref(auth_event_id), _ref(tenant_id), _ref(import_run_id)
            initial = self._snapshot(reference, owner, now=started)
            if initial.tenant_id != tenant or initial.auth_event_id != event:
                raise Refusal()
            check = self._guard(reference, owner, initial, tick=tick)
            payload, digest, size, retrieved = self._request("connections", reference=reference, check=check, tick=tick)
            connections = oauth.parse_connections(payload)
            selected = oauth.match_organisation_connections(connections, expected_auth_event_id=event, expected_tenant_id=tenant)
            if len(selected) != 1 or selected[0].connection_id != initial.connection_id:
                raise Refusal()
            documents, observations, ids = [], [], set()
            digests, times, total_bytes = [digest], [retrieved], size
            for page in range(1, MAX_PAGES + 1):
                payload, digest, size, retrieved = self._request("invoices", reference=reference, tenant=tenant, page=page, check=check, tick=tick)
                total_bytes += size
                if total_bytes > MAX_TOTAL_BYTES or type(payload) is not dict or set(payload) != {"Invoices"}:
                    raise Refusal()
                records = payload["Invoices"]
                if type(records) is not list or len(records) > PAGE_SIZE or len(ids) + len(records) > MAX_RECORDS:
                    raise Refusal()
                digests.append(digest)
                times.append(retrieved)
                for raw in records:
                    with localcontext(Context(prec=64)):
                        mapping = map_detailed_invoice_response({"Invoices": [raw]}, user_id=owner,
                            connected_organisation_id=initial.connection_id, tenant_id=tenant,
                            import_run_id=run, retrieved_at=retrieved)
                        if mapping.invoice.invoice_id in ids:
                            raise Refusal()
                        ids.add(mapping.invoice.invoice_id)
                        documents.append(normalise_document(observation=mapping.observation, adapter_result=mapping.adapter_result))
                        observations.append(mapping.observation)
                check()
                if not records:
                    manifest = ImportManifest(run, ImportScope("xero", "test", tenant, "Invoices"), started,
                        check(), page, len(ids), len(ids), True, source_total_count=None)
                    return Outcome("observed", documents=tuple(documents), observations=tuple(observations),
                        manifest=manifest, response_digests=tuple(digests), retrieved_at=tuple(times),
                        tenant_id=tenant, connection_id=initial.connection_id, auth_event_id=event,
                        binding_revision=initial.revision)
            raise Refusal()
        except Exception as error:
            return _failed("acquisition_refused", error)
