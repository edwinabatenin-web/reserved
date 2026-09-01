"""Pure, network-inert Xero OAuth and tenant-discovery wire contracts.

This module constructs and validates documented values only. HTTP, credentials,
callback state/replay, token custody, routes and provider enablement are owned
elsewhere. Official contract evidence was observed on 2026-09-01 and is
recorded in ``docs/XERO_XS1_OAUTH_CONTRACT_EVIDENCE.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qs, urlencode, urlparse


AUTHORISATION_ENDPOINT = "https://login.xero.com/identity/connect/authorize"
TOKEN_ENDPOINT = "https://identity.xero.com/connect/token"
CONNECTIONS_ENDPOINT = "https://api.xero.com/connections"
AUTHORISATION_SCOPES = ("accounting.invoices.read", "offline_access")
AUTHORISATION_SCOPE = " ".join(AUTHORISATION_SCOPES)


@dataclass(frozen=True, repr=False)
class XeroTokenSet:
    access_token: str
    expires_in: int
    token_type: str
    refresh_token: str

    def __repr__(self) -> str:
        return "XeroTokenSet([REDACTED])"


@dataclass(frozen=True)
class XeroConnection:
    connection_id: str
    auth_event_id: str
    tenant_id: str
    tenant_type: str
    tenant_name: str | None
    created_date_utc: str
    updated_date_utc: str


def _required_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Xero {name} must be a non-empty string")
    return value


def _validate_redirect_uri(redirect_uri: object) -> str:
    value = _required_string(redirect_uri, "redirect_uri")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.hostname is None:
        raise ValueError("Xero redirect_uri must be an absolute HTTPS URI")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Xero redirect_uri must not contain userinfo")
    if parsed.fragment:
        raise ValueError("Xero redirect_uri must not contain a fragment")
    if parsed.netloc.endswith(":"):
        raise ValueError("Xero redirect_uri must contain a valid port if supplied")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("Xero redirect_uri must contain a valid port if supplied") from exc
    return value


def build_authorisation_url(*, client_id: str, redirect_uri: str, state: str) -> str:
    """Build the exact reviewed read-only authorization-code request."""
    client_id = _required_string(client_id, "client_id")
    redirect_uri = _validate_redirect_uri(redirect_uri)
    state = _required_string(state, "state")
    query = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "scope": AUTHORISATION_SCOPE,
            "redirect_uri": redirect_uri,
            "state": state,
        }
    )
    url = f"{AUTHORISATION_ENDPOINT}?{query}"
    validate_authorisation_url(url)
    return url


def validate_authorisation_url(url: str) -> None:
    """Reject any authorization request outside the reviewed exact shape."""
    url = _required_string(url, "authorisation URL")
    parsed = urlparse(url)
    endpoint = urlparse(AUTHORISATION_ENDPOINT)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("Xero authorisation URL must not contain userinfo")
    if (
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
    ) != (endpoint.scheme, endpoint.netloc, endpoint.path, endpoint.params):
        raise ValueError("Xero authorisation URL does not match the reviewed endpoint")
    if parsed.fragment:
        raise ValueError("Xero authorisation URL must not contain a fragment")
    try:
        query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise ValueError("Xero authorisation query is malformed") from exc
    required = {"response_type", "client_id", "scope", "redirect_uri", "state"}
    if set(query) != required:
        raise ValueError("Xero authorisation parameters do not match the reviewed contract")
    if any(len(values) != 1 or not values[0].strip() for values in query.values()):
        raise ValueError("Xero authorisation parameters must be singular and non-empty")
    if query["response_type"] != ["code"]:
        raise ValueError("Xero response_type must be code")
    if query["scope"] != [AUTHORISATION_SCOPE]:
        raise ValueError("Xero scopes must be the fixed read-only scope set")
    _validate_redirect_uri(query["redirect_uri"][0])


def code_exchange_body(*, code: str, redirect_uri: str) -> dict[str, str]:
    """Return form fields; Basic client authentication is an HTTP-layer concern."""
    return {
        "grant_type": "authorization_code",
        "code": _required_string(code, "code"),
        "redirect_uri": _validate_redirect_uri(redirect_uri),
    }


def refresh_body(*, refresh_token: str) -> dict[str, str]:
    """Return the refresh form without placing any secret in a URL."""
    return {
        "grant_type": "refresh_token",
        "refresh_token": _required_string(refresh_token, "refresh_token"),
    }


def parse_token_response(payload: Mapping[str, Any]) -> XeroTokenSet:
    """Validate the documented token set, including the rotated refresh token."""
    if not isinstance(payload, Mapping):
        raise ValueError("Xero token response must be an object")
    required = {"access_token", "expires_in", "token_type", "refresh_token"}
    if not required.issubset(payload):
        raise ValueError("Xero token response is missing documented fields")
    access_token = _required_string(payload["access_token"], "access_token")
    refresh_token = _required_string(payload["refresh_token"], "refresh_token")
    if payload["token_type"] != "Bearer":
        raise ValueError("Xero token_type must be Bearer")
    if type(payload["expires_in"]) is not int or payload["expires_in"] <= 0:
        raise ValueError("Xero expires_in must be a positive integer")
    return XeroTokenSet(
        access_token=access_token,
        expires_in=payload["expires_in"],
        token_type="Bearer",
        refresh_token=refresh_token,
    )


def parse_connections(payload: object) -> tuple[XeroConnection, ...]:
    """Copy a JSON array into immutable organisation-only typed records."""
    if not isinstance(payload, list):
        raise ValueError("Xero connections response must be an array")
    required = {
        "id", "authEventId", "tenantId", "tenantType", "tenantName",
        "createdDateUtc", "updatedDateUtc",
    }
    connections: list[XeroConnection] = []
    seen_connection_ids: set[str] = set()
    seen_tenants: set[tuple[str, str]] = set()
    for item in payload:
        if not isinstance(item, Mapping) or not required.issubset(item):
            raise ValueError("Xero connection is missing documented fields")
        connection_id = _required_string(item["id"], "connection id")
        auth_event_id = _required_string(item["authEventId"], "authEventId")
        tenant_id = _required_string(item["tenantId"], "tenantId")
        tenant_type = _required_string(item["tenantType"], "tenantType")
        if tenant_type != "ORGANISATION":
            raise ValueError("Xero accounting connections must be ORGANISATION tenants")
        tenant_name = item["tenantName"]
        if tenant_name is not None and (
            not isinstance(tenant_name, str) or not tenant_name.strip()
        ):
            raise ValueError("Xero tenantName must be a non-empty string or null")
        created = _required_string(item["createdDateUtc"], "createdDateUtc")
        updated = _required_string(item["updatedDateUtc"], "updatedDateUtc")
        tenant_key = (auth_event_id, tenant_id)
        if connection_id in seen_connection_ids or tenant_key in seen_tenants:
            raise ValueError("Xero connections response contains a duplicate connection")
        seen_connection_ids.add(connection_id)
        seen_tenants.add(tenant_key)
        connections.append(
            XeroConnection(
                connection_id=connection_id,
                auth_event_id=auth_event_id,
                tenant_id=tenant_id,
                tenant_type=tenant_type,
                tenant_name=tenant_name,
                created_date_utc=created,
                updated_date_utc=updated,
            )
        )
    return tuple(connections)


def match_organisation_connections(
    connections: Sequence[XeroConnection],
    *,
    expected_auth_event_id: str,
    expected_tenant_id: str | None = None,
) -> tuple[XeroConnection, ...]:
    """Return explicit event matches, optionally requiring one explicit tenant."""
    event_id = _required_string(expected_auth_event_id, "expected authEventId")
    if not isinstance(connections, (tuple, list)) or any(
        not isinstance(connection, XeroConnection) for connection in connections
    ):
        raise ValueError("Xero connections must be validated typed records")
    matches = tuple(
        connection for connection in connections if connection.auth_event_id == event_id
    )
    if not matches:
        raise ValueError("No Xero organisation connection matches the expected authEventId")
    if expected_tenant_id is None:
        return matches
    tenant_id = _required_string(expected_tenant_id, "expected tenantId")
    selected = tuple(connection for connection in matches if connection.tenant_id == tenant_id)
    if len(selected) != 1:
        raise ValueError("Expected Xero tenantId does not identify exactly one connection")
    return selected
