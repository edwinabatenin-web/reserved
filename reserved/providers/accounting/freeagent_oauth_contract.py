"""Network-inert FreeAgent sandbox OAuth wire contracts.

This module only constructs and validates documented values. It owns no HTTP
client, credentials, token storage or adapter-enablement path.

Authority observed 2026-08-13:
https://dev.freeagent.com/docs/oauth
https://dev.freeagent.com/docs/quick_start
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any
from urllib.parse import urlencode, urlparse, parse_qs


SANDBOX_AUTHORISATION_ENDPOINT = "https://api.sandbox.freeagent.com/v2/approve_app"
SANDBOX_TOKEN_ENDPOINT = "https://api.sandbox.freeagent.com/v2/token_endpoint"


@dataclass(frozen=True)
class FreeAgentTokenSet:
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    refresh_token_expires_in: int


def build_sandbox_authorisation_url(*, client_id: str, redirect_uri: str, state: str) -> str:
    """Build the documented request, requiring Reserved's stronger state rule."""
    values = {"client_id": client_id, "redirect_uri": redirect_uri, "state": state}
    if any(not isinstance(value, str) or not value.strip() for value in values.values()):
        raise ValueError("client_id, redirect_uri and state must be non-empty strings")
    parsed = urlparse(redirect_uri)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError("redirect_uri must be an absolute HTTP(S) URI")
    query = urlencode({
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
    })
    return f"{SANDBOX_AUTHORISATION_ENDPOINT}?{query}"


def validate_authorisation_url(url: str) -> None:
    """Fail closed if a constructed request leaves the official sandbox shape."""
    parsed = urlparse(url)
    endpoint = urlparse(SANDBOX_AUTHORISATION_ENDPOINT)
    if (parsed.scheme, parsed.netloc, parsed.path) != (endpoint.scheme, endpoint.netloc, endpoint.path):
        raise ValueError("FreeAgent authorisation request is not sandbox-confined")
    if parsed.fragment:
        raise ValueError("FreeAgent authorisation request must not contain a fragment")
    query = parse_qs(parsed.query, keep_blank_values=True, strict_parsing=True)
    if set(query) != {"client_id", "response_type", "redirect_uri", "state"}:
        raise ValueError("FreeAgent authorisation parameters do not match the reviewed contract")
    if any(len(value) != 1 or not value[0] for value in query.values()):
        raise ValueError("FreeAgent authorisation parameters must be singular and non-empty")
    if query["response_type"] != ["code"]:
        raise ValueError("FreeAgent response_type must be code")


def code_exchange_body(*, code: str, redirect_uri: str) -> dict[str, str]:
    if not code or not redirect_uri:
        raise ValueError("code and redirect_uri are required")
    return {"grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri}


def refresh_body(*, refresh_token: str) -> dict[str, str]:
    if not refresh_token:
        raise ValueError("refresh_token is required")
    return {"grant_type": "refresh_token", "refresh_token": refresh_token}


def parse_token_response(payload: Mapping[str, Any]) -> FreeAgentTokenSet:
    """Validate the five fields in FreeAgent's documented token response."""
    required = {
        "access_token", "token_type", "expires_in", "refresh_token",
        "refresh_token_expires_in",
    }
    if not isinstance(payload, Mapping) or not required.issubset(payload):
        raise ValueError("FreeAgent token response is missing documented fields")
    if not isinstance(payload["access_token"], str) or not payload["access_token"]:
        raise ValueError("FreeAgent access_token must be a non-empty string")
    if payload["token_type"] != "bearer":
        raise ValueError("FreeAgent token_type must be bearer")
    if not isinstance(payload["refresh_token"], str) or not payload["refresh_token"]:
        raise ValueError("FreeAgent refresh_token must be a non-empty string")
    for name in ("expires_in", "refresh_token_expires_in"):
        if type(payload[name]) is not int or payload[name] <= 0:
            raise ValueError(f"FreeAgent {name} must be a positive integer")
    return FreeAgentTokenSet(
        access_token=payload["access_token"],
        token_type=payload["token_type"],
        expires_in=payload["expires_in"],
        refresh_token=payload["refresh_token"],
        refresh_token_expires_in=payload["refresh_token_expires_in"],
    )

