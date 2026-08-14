"""Endpoint-free OAuth callback and token-custody contracts.

Provider adapters supply their own documented URLs and token exchange. This
module enforces ordering and custody only: callback state is consumed before an
authorisation code becomes usable, codes are single-use, and raw token sets are
handed directly to a token store rather than returned to application callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Protocol

from .oauth_security import OAuthStateStore


class OAuthContractError(ValueError):
    """Safe OAuth failure whose message contains no callback parameter values."""


class CallbackStatus(str, Enum):
    AUTHORISED = "authorised"
    DENIED = "denied"


class ValidatedAuthorizationCode:
    """Single-use code available only after provider-bound state validation."""

    __slots__ = ("_code", "_consumed")

    def __init__(self, code: str) -> None:
        if not code:
            raise OAuthContractError("Authorisation callback did not include a code")
        self._code = code
        self._consumed = False

    def consume(self) -> str:
        if self._consumed:
            raise OAuthContractError("Authorisation code has already been consumed")
        self._consumed = True
        return self._code

    def __repr__(self) -> str:
        return "ValidatedAuthorizationCode([REDACTED])"


@dataclass(frozen=True)
class CallbackResult:
    status: CallbackStatus
    code: ValidatedAuthorizationCode | None = field(default=None, repr=False)
    provider_error: str | None = None


def validate_callback(
    *,
    provider: str,
    parameters: Mapping[str, str],
    state_store: OAuthStateStore,
    now: int | None = None,
) -> CallbackResult:
    """Consume state first, then expose either a denial or a one-use code.

    Provider error descriptions and callback values are intentionally not
    copied into exceptions or the result. A stable error code may be retained
    for UI mapping, but callers must use an allowlist before displaying it.
    """
    supplied_state = parameters.get("state")
    if not state_store.consume(provider, supplied_state, now=now):
        raise OAuthContractError("Authorisation callback state is invalid or expired")

    if parameters.get("error"):
        return CallbackResult(
            CallbackStatus.DENIED,
            provider_error="provider_denied_authorisation",
        )
    return CallbackResult(
        CallbackStatus.AUTHORISED,
        code=ValidatedAuthorizationCode(parameters.get("code", "")),
    )


@dataclass(frozen=True, repr=False)
class OAuthTokenSet:
    """Raw provider tokens with a deliberately redacted representation."""

    access_token: str
    refresh_token: str | None
    expires_in: int | None = None
    provider_subject: str | None = None

    def __post_init__(self) -> None:
        if not self.access_token:
            raise OAuthContractError("Token response did not include an access token")
        if self.expires_in is not None and self.expires_in <= 0:
            raise OAuthContractError("Token response included an invalid expiry")

    def __repr__(self) -> str:
        return "OAuthTokenSet([REDACTED])"


@dataclass(frozen=True)
class CredentialReference:
    provider: str
    reference: str

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.reference.strip():
            raise OAuthContractError("Credential reference and provider are required")


class TokenExchanger(Protocol):
    def exchange(self, code: str, redirect_uri: str) -> OAuthTokenSet: ...


class TokenStore(Protocol):
    """Secure server-side store; implementations own encryption and rotation."""

    def put(
        self,
        *,
        provider: str,
        user_id: str,
        tokens: OAuthTokenSet,
    ) -> CredentialReference: ...

    def replace(
        self,
        *,
        credential: CredentialReference,
        tokens: OAuthTokenSet,
    ) -> None: ...

    def delete(self, credential: CredentialReference) -> None: ...


class TokenRefresher(Protocol):
    """Provider adapter refreshes using secrets resolved inside its boundary."""

    def refresh(self, credential: CredentialReference) -> OAuthTokenSet: ...


def exchange_and_store(
    *,
    provider: str,
    user_id: str,
    redirect_uri: str,
    code: ValidatedAuthorizationCode,
    exchanger: TokenExchanger,
    token_store: TokenStore,
) -> CredentialReference:
    """Exchange exactly once and return only an opaque credential reference."""
    raw_code = code.consume()
    tokens = exchanger.exchange(raw_code, redirect_uri)
    return token_store.put(provider=provider, user_id=user_id, tokens=tokens)


def refresh_and_rotate(
    *,
    credential: CredentialReference,
    refresher: TokenRefresher,
    token_store: TokenStore,
) -> None:
    """Refresh then atomically replace the complete provider token set.

    The current credential is never deleted first. If the provider refresh
    fails, or if its response is rejected while constructing ``OAuthTokenSet``,
    ``replace`` is not called. Store implementations must commit the entire new
    token set atomically so a rotated refresh token cannot be separated from
    its associated access token.
    """
    tokens = refresher.refresh(credential)
    if not isinstance(tokens, OAuthTokenSet):
        raise OAuthContractError("Refresher returned an invalid token set")
    token_store.replace(credential=credential, tokens=tokens)
