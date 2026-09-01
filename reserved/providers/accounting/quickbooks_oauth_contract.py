"""Pure, network-inert QuickBooks Online OAuth and realm-binding contract.

Official facts encoded here were observed on 2026-09-01 and are recorded in
``docs/QUICKBOOKS_QS1_OAUTH_CONTRACT_EVIDENCE.md``.  This module performs no
HTTP, credential custody, persistence, logging, configuration, or enablement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlencode, urlsplit


AUTHORISATION_ENDPOINT = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_ENDPOINT = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
REVOCATION_ENDPOINT = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"
ACCOUNTING_SCOPE = "com.intuit.quickbooks.accounting"

_AUTHORISATION_FIELDS = (
    "client_id", "scope", "redirect_uri", "response_type", "state",
)
_TOKEN_FIELDS = {
    "access_token", "refresh_token", "expires_in",
    "x_refresh_token_expires_in", "token_type",
}


class QuickBooksOAuthContractError(ValueError):
    """Fail-closed validation error which never includes token values."""


def _non_blank(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise QuickBooksOAuthContractError(f"{name} must be a non-blank string")
    return value


def _validate_https_redirect(redirect_uri: object) -> str:
    """Apply Reserved's fail-closed redirect rule, not an Intuit claim."""
    value = _non_blank(redirect_uri, "redirect_uri")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise QuickBooksOAuthContractError("redirect_uri has a malformed port") from exc
    if parsed.scheme != "https" or not parsed.netloc or not parsed.hostname:
        raise QuickBooksOAuthContractError("redirect_uri must be an absolute HTTPS URI")
    if parsed.username is not None or parsed.password is not None:
        raise QuickBooksOAuthContractError("redirect_uri must not contain userinfo")
    if parsed.netloc.endswith(":"):
        raise QuickBooksOAuthContractError("redirect_uri has a malformed port")
    if parsed.fragment:
        raise QuickBooksOAuthContractError("redirect_uri must not contain a fragment")
    if port is not None and not 1 <= port <= 65535:
        raise QuickBooksOAuthContractError("redirect_uri has a malformed port")
    return value


def build_authorisation_url(*, client_id: str, redirect_uri: str, state: str) -> str:
    """Build the exact five-field Intuit authorisation request."""
    client_id = _non_blank(client_id, "client_id")
    redirect_uri = _validate_https_redirect(redirect_uri)
    state = _non_blank(state, "state")
    query = urlencode((
        ("client_id", client_id),
        ("scope", ACCOUNTING_SCOPE),
        ("redirect_uri", redirect_uri),
        ("response_type", "code"),
        ("state", state),
    ))
    result = f"{AUTHORISATION_ENDPOINT}?{query}"
    validate_authorisation_url(result)
    return result


def validate_authorisation_url(url: str) -> None:
    """Reject any drift from the reviewed endpoint and canonical request."""
    value = _non_blank(url, "authorisation URL")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise QuickBooksOAuthContractError("authorisation URL has a malformed port") from exc
    endpoint = urlsplit(AUTHORISATION_ENDPOINT)
    if parsed.username is not None or parsed.password is not None:
        raise QuickBooksOAuthContractError("authorisation URL must not contain userinfo")
    if parsed.netloc.endswith(":"):
        raise QuickBooksOAuthContractError("authorisation URL has a malformed port")
    if parsed.fragment or port is not None:
        raise QuickBooksOAuthContractError("authorisation endpoint must be exact")
    if (parsed.scheme, parsed.hostname, parsed.path) != (
        endpoint.scheme, endpoint.hostname, endpoint.path,
    ):
        raise QuickBooksOAuthContractError("authorisation endpoint must be exact")
    try:
        pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise QuickBooksOAuthContractError("authorisation query is malformed") from exc
    if tuple(name for name, _ in pairs) != _AUTHORISATION_FIELDS:
        raise QuickBooksOAuthContractError("authorisation parameters must be exact and ordered")
    values = dict(pairs)
    if any(not item for item in values.values()):
        raise QuickBooksOAuthContractError("authorisation parameters must not be blank")
    if values["scope"] != ACCOUNTING_SCOPE or values["response_type"] != "code":
        raise QuickBooksOAuthContractError("authorisation scope or response type is invalid")
    _validate_https_redirect(values["redirect_uri"])
    canonical = urlencode(tuple((name, values[name]) for name in _AUTHORISATION_FIELDS))
    if parsed.query != canonical:
        raise QuickBooksOAuthContractError("authorisation query is not canonical")


@dataclass(frozen=True, repr=False)
class SuccessfulCallback:
    code: str
    realm_id: str

    def __repr__(self) -> str:
        return "SuccessfulCallback(code=[REDACTED], realm_id=[REDACTED])"


@dataclass(frozen=True)
class ErrorCallback:
    error: str


def parse_callback(parameters: Mapping[str, str], *, expected_state: str) -> SuccessfulCallback | ErrorCallback:
    """Parse disjoint successful or documented-error callback parameters."""
    expected_state = _non_blank(expected_state, "expected_state")
    if not isinstance(parameters, Mapping):
        raise QuickBooksOAuthContractError("callback parameters must be a mapping")
    if any(not isinstance(name, str) or not isinstance(value, str) for name, value in parameters.items()):
        raise QuickBooksOAuthContractError("callback parameters must be singular strings")
    state = parameters.get("state")
    if not state or state != expected_state:
        raise QuickBooksOAuthContractError("callback state does not match")
    has_success = "code" in parameters or "realmId" in parameters
    has_error = "error" in parameters
    if has_success and has_error:
        raise QuickBooksOAuthContractError("callback success and error values are disjoint")
    if has_error:
        if set(parameters) != {"error", "state"}:
            raise QuickBooksOAuthContractError("error callback parameters are invalid")
        error = parameters["error"]
        if error not in {"access_denied", "invalid_scope"}:
            raise QuickBooksOAuthContractError("callback error is not documented")
        return ErrorCallback(error=error)
    if set(parameters) != {"code", "state", "realmId"}:
        raise QuickBooksOAuthContractError("success callback parameters are invalid")
    code = _non_blank(parameters["code"], "code")
    realm_id = _non_blank(parameters["realmId"], "realmId")
    if len(code) > 512:
        raise QuickBooksOAuthContractError("code exceeds the documented maximum length")
    return SuccessfulCallback(code=code, realm_id=realm_id)


@dataclass(frozen=True)
class RealmBinding:
    user_id: str
    realm_id: str
    credential_reference: str

    def __post_init__(self) -> None:
        for name in ("user_id", "realm_id", "credential_reference"):
            _non_blank(getattr(self, name), name)

    def assert_owner(self, *, user_id: str, realm_id: str) -> None:
        if user_id != self.user_id or realm_id != self.realm_id:
            raise QuickBooksOAuthContractError("realm binding ownership does not match")


def code_exchange_body(*, code: str, redirect_uri: str) -> dict[str, str]:
    code = _non_blank(code, "code")
    if len(code) > 512:
        raise QuickBooksOAuthContractError("code exceeds the documented maximum length")
    return {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": _validate_https_redirect(redirect_uri),
    }


def refresh_body(*, refresh_token: str) -> dict[str, str]:
    token = _non_blank(refresh_token, "refresh_token")
    if len(token) > 512:
        raise QuickBooksOAuthContractError("refresh_token exceeds the documented maximum length")
    return {"grant_type": "refresh_token", "refresh_token": token}


@dataclass(frozen=True, repr=False)
class QuickBooksTokenSet:
    access_token: str
    refresh_token: str
    expires_in: int
    x_refresh_token_expires_in: int
    token_type: str
    x_refresh_token_hard_expires_in: int | None = None

    def __repr__(self) -> str:
        return "QuickBooksTokenSet([REDACTED])"


def parse_token_response(payload: Mapping[str, Any]) -> QuickBooksTokenSet:
    """Validate documented fields while ignoring additive fields without meaning."""
    if not isinstance(payload, Mapping) or not _TOKEN_FIELDS.issubset(payload):
        raise QuickBooksOAuthContractError("token response is missing documented fields")
    access_token = _non_blank(payload["access_token"], "access_token")
    refresh_token = _non_blank(payload["refresh_token"], "refresh_token")
    if len(access_token) > 4096:
        raise QuickBooksOAuthContractError("access_token exceeds the documented maximum length")
    if len(refresh_token) > 512:
        raise QuickBooksOAuthContractError("refresh_token exceeds the documented maximum length")
    if type(payload["token_type"]) is not str or payload["token_type"] != "bearer":
        raise QuickBooksOAuthContractError("token_type must be bearer")
    for name in ("expires_in", "x_refresh_token_expires_in"):
        if type(payload[name]) is not int or payload[name] <= 0:
            raise QuickBooksOAuthContractError(f"{name} must be a positive exact integer")
    hard_expiry = payload.get("x_refresh_token_hard_expires_in")
    if hard_expiry is not None and (type(hard_expiry) is not int or hard_expiry <= 0):
        raise QuickBooksOAuthContractError(
            "x_refresh_token_hard_expires_in must be a positive exact integer"
        )
    return QuickBooksTokenSet(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=payload["expires_in"],
        x_refresh_token_expires_in=payload["x_refresh_token_expires_in"],
        token_type=payload["token_type"],
        x_refresh_token_hard_expires_in=hard_expiry,
    )


def replace_token_set(previous: QuickBooksTokenSet, refreshed: QuickBooksTokenSet) -> QuickBooksTokenSet:
    """Return the complete refresh result; callers must discard ``previous``."""
    if type(previous) is not QuickBooksTokenSet or type(refreshed) is not QuickBooksTokenSet:
        raise QuickBooksOAuthContractError("rotation requires complete QuickBooks token sets")
    return refreshed
