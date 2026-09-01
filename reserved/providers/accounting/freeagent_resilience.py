"""Network-inert FreeAgent resilience and connection-state contract.

This module describes safe next states and decisions over already-validated
FreeAgent inputs. It owns no HTTP client, credential access, secret storage,
persistence, sleeping, retry loop, provider enablement, payment action or
canonical accounting mapping. Nothing here claims that a network call, token
storage or provider-side revocation occurred.

Documented FreeAgent facts, existing Reserved invariants and bounded
implementation inference are separated in
``docs/FREEAGENT_RESILIENCE_EVIDENCE.md``. Unknown provider error, revocation
and disconnect semantics remain explicitly unsupported and fail closed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .freeagent_invoice_contract import (
    FreeAgentPagination,
    parse_link_header,
    validate_pagination,
)
from .freeagent_oauth_contract import FreeAgentTokenSet, parse_token_response

# Documented FreeAgent rate-limit facts (see the evidence document for the
# source). These are retained as facts, not used to implement a live limiter.
RATE_LIMIT_USER_REQUESTS_PER_MINUTE = 120
RATE_LIMIT_USER_REQUESTS_PER_HOUR = 3600
RATE_LIMIT_TOKEN_REFRESHES_PER_MINUTE = 15

# Bounded implementation inference, not a documented FreeAgent value. The page
# bound matches the existing provider-neutral sync collector default so that a
# FreeAgent adapter can use the same configured ceiling.
DEFAULT_MAX_PAGES = 1000

# Bounded implementation inference, not a documented FreeAgent value. A 429
# wait above this bound is treated as excessive and fails closed rather than
# being silently clamped or slept through.
DEFAULT_MAX_WAIT_SECONDS = 300

# Local disconnect is exactly that: local. No provider-side revocation call is
# claimed or performed anywhere in this module.
DISCONNECT_IS_LOCAL_ONLY = True

# Caller-supplied opaque non-secret identifier format for a previously issued
# refresh reference. This is NOT a token and NOT a storage handle: a fixed
# namespace plus a fixed-length lowercase hexadecimal identity, so a token-like
# or human-readable secret can never be accepted or echoed by this module.
OLD_REFERENCE_NAMESPACE = "freeagent.ref"
OLD_REFERENCE_IDENTITY_LENGTH = 32
_OLD_REFERENCE_RE = re.compile(
    rf"^{re.escape(OLD_REFERENCE_NAMESPACE)}\.[0-9a-f]{{{OLD_REFERENCE_IDENTITY_LENGTH}}}$"
)


class FreeAgentResilienceError(ValueError):
    """Resilience/state decision failed closed without side effects."""


class PaginationAction(str, Enum):
    CONTINUE = "continue"
    TERMINAL = "terminal"


class RefreshAction(str, Enum):
    ROTATE = "rotate"


class RateLimitAction(str, Enum):
    WAIT_AND_RETRY = "wait_and_retry"


class ConnectionState(str, Enum):
    CONNECTED = "connected"
    REFRESH_REQUIRED = "refresh_required"
    REAUTHORISATION_REQUIRED = "reauthorisation_required"
    # Local-only state; never implies a provider-side revocation call succeeded.
    LOCAL_DISCONNECTED = "local_disconnected"


class ConnectionEvent(str, Enum):
    ACCESS_TOKEN_EXPIRED = "access_token_expired"
    REFRESH_TOKEN_EXPIRED = "refresh_token_expired"
    TOKEN_SET_ROTATED = "token_set_rotated"
    LOCAL_DISCONNECT = "local_disconnect"


class ErrorClass(str, Enum):
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"


class ErrorDisposition(str, Enum):
    RETRYABLE = "retryable"
    REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True)
class PaginationDecision:
    action: PaginationAction
    next_url: str | None = None


@dataclass(frozen=True, repr=False)
class RefreshRotationDecision:
    """A pure rotation decision; ``stored`` is always ``False``.

    ``old_reference`` is a validated non-secret opaque identifier (never a token
    or a storage handle). No access token or refresh token is retained in this
    value, so neither the representation nor any derived error can leak a token
    string.
    """

    action: RefreshAction
    old_reference: str
    token_type: str
    expires_in: int
    refresh_token_expires_in: int
    stored: bool = False

    def __repr__(self) -> str:
        return (
            "RefreshRotationDecision(action='rotate', "
            f"old_reference={self.old_reference!r}, token_type={self.token_type!r}, "
            f"expires_in={self.expires_in}, "
            f"refresh_token_expires_in={self.refresh_token_expires_in}, "
            "stored=False, tokens=[REDACTED])"
        )


@dataclass(frozen=True)
class RateLimitDecision:
    action: RateLimitAction
    retry_after_seconds: int


@dataclass(frozen=True)
class ErrorClassification:
    error_class: ErrorClass
    disposition: ErrorDisposition
    retry_after_seconds: int | None = None
    reason: str | None = None


def _exact_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise FreeAgentResilienceError(f"{field} must be an integer")
    return value


def _exact_positive_int(value: Any, field: str) -> int:
    value = _exact_int(value, field)
    if value <= 0:
        raise FreeAgentResilienceError(f"{field} must be positive")
    return value


def _exact_non_negative_int(value: Any, field: str) -> int:
    value = _exact_int(value, field)
    if value < 0:
        raise FreeAgentResilienceError(f"{field} must be non-negative")
    return value


def _exact_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise FreeAgentResilienceError(f"{field} must be a boolean")
    return value


def _validate_optional_cursor(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise FreeAgentResilienceError(f"{field} must be a non-empty string")
    return value


def _validate_cursor_set(value: Any, field: str) -> frozenset[str]:
    if isinstance(value, str):
        raise FreeAgentResilienceError(f"{field} must be a collection of strings")
    if not isinstance(value, (frozenset, set, tuple, list)):
        raise FreeAgentResilienceError(f"{field} must be an iterable of non-empty strings")
    cursors: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise FreeAgentResilienceError(f"{field} must contain only non-empty strings")
        cursors.add(item)
    return frozenset(cursors)


def _validate_old_reference(value: Any) -> str:
    """Validate a caller-supplied non-secret opaque refresh reference.

    The reference must match the fixed namespace plus a fixed-length lowercase
    hexadecimal identity. Tokens, whitespace, readable slugs and any other
    malformed value are rejected without being echoed.
    """
    if not isinstance(value, str):
        raise FreeAgentResilienceError(
            "old_reference must be a non-secret opaque identifier of the form "
            f"{OLD_REFERENCE_NAMESPACE}.<{OLD_REFERENCE_IDENTITY_LENGTH} "
            "lowercase hexadecimal digits>"
        )
    if _OLD_REFERENCE_RE.fullmatch(value) is None:
        raise FreeAgentResilienceError(
            "old_reference must be a non-secret opaque identifier of the form "
            f"{OLD_REFERENCE_NAMESPACE}.<{OLD_REFERENCE_IDENTITY_LENGTH} "
            "lowercase hexadecimal digits>"
        )
    return value


_LINK_HEADER_DELIMITERS = frozenset(('"', "<", ">", "\n", "\r"))


def _link_header_from_pagination(pagination: FreeAgentPagination) -> str:
    """Reconstruct a Link header from a pagination's retained relations."""
    parts: list[str] = []
    for rel in ("prev", "next", "first", "last"):
        url = getattr(pagination, f"{rel}_url")
        if url is None:
            continue
        if not isinstance(url, str) or not url:
            raise FreeAgentResilienceError(
                f"FreeAgent pagination {rel}_url must be a non-empty string"
            )
        if any(ch in url for ch in _LINK_HEADER_DELIMITERS):
            raise FreeAgentResilienceError(
                f"FreeAgent pagination {rel}_url contains a Link-header delimiter"
            )
        parts.append(f'<{url}>; rel="{rel}"')
    return ", ".join(parts)


def _revalidate_pagination(pagination: FreeAgentPagination) -> FreeAgentPagination:
    """Re-validate a FreeAgent pagination through the existing validator boundary.

    Reconstructing the Link header and calling ``parse_link_header`` reuses the
    exact origin/path/userinfo/fragment/port checks already enforced for the
    invoice contract, so a hand-constructed pagination cannot smuggle a
    cross-origin or non-invoice ``next_url`` past this decision layer.
    """
    if not isinstance(pagination, FreeAgentPagination):
        raise FreeAgentResilienceError("pagination must be a FreeAgentPagination")
    header = _link_header_from_pagination(pagination)
    try:
        if header:
            parse_link_header(header)
        validated = validate_pagination(
            page=pagination.page,
            per_page=pagination.per_page,
            total_count=pagination.total_count,
        )
    except ValueError as exc:
        raise FreeAgentResilienceError(f"invalid FreeAgent pagination: {exc}") from exc
    return validated


def decide_pagination(
    *,
    pagination: FreeAgentPagination,
    page_number: int,
    fetched_count: int,
    current_cursor: str | None = None,
    seen_cursors: frozenset[str] = frozenset(),
    max_pages: int = DEFAULT_MAX_PAGES,
) -> PaginationDecision:
    """Return the safe next pagination decision for one already-validated page.

    ``page_number`` is the 1-based page just fetched; ``fetched_count`` is the
    cumulative number of records fetched so far; ``current_cursor`` is the
    cursor used to fetch the current page (``None`` for the first page); and
    ``seen_cursors`` is the set of every next cursor already returned. The
    next URL is preserved verbatim so cursor/URL identity is never rewritten.

    Fails closed on repeated/cyclic cursors, contradictory page metadata,
    exceeded page limits, a next page claimed at the final permitted page, and
    count-incoherent or ambiguous progress.
    """
    validated = _revalidate_pagination(pagination)
    page_number = _exact_positive_int(page_number, "page_number")
    fetched_count = _exact_non_negative_int(fetched_count, "fetched_count")
    max_pages = _exact_positive_int(max_pages, "max_pages")
    current_cursor = _validate_optional_cursor(current_cursor, "current_cursor")
    seen = _validate_cursor_set(seen_cursors, "seen_cursors")

    page_meta = validated.page
    total_count = validated.total_count
    next_url = pagination.next_url

    if page_meta is not None and page_meta != page_number:
        raise FreeAgentResilienceError(
            "FreeAgent pagination page metadata contradicts the sync page counter"
        )
    if page_number > max_pages:
        raise FreeAgentResilienceError("pagination exceeded the configured page limit")
    if page_number == 1:
        if current_cursor is not None or seen:
            raise FreeAgentResilienceError(
                "the first page must not have current or previously returned cursors"
            )
    else:
        if current_cursor is None:
            raise FreeAgentResilienceError(
                "later pages require the cursor used to fetch the current page"
            )
        if current_cursor not in seen:
            raise FreeAgentResilienceError(
                "the current page cursor must be present in previously returned cursors"
            )
        if len(seen) != page_number - 1:
            raise FreeAgentResilienceError(
                "cursor history is incoherent with the current page number"
            )

    if total_count is not None:
        if fetched_count > total_count:
            raise FreeAgentResilienceError("fetched_count exceeds the source total count")
        if next_url is None and fetched_count != total_count:
            raise FreeAgentResilienceError(
                "terminal page count is incoherent with the source total count"
            )
        if next_url is not None and fetched_count == total_count:
            raise FreeAgentResilienceError(
                "a next page is claimed after the source total count is reached"
            )

    if page_number == max_pages:
        if next_url is not None:
            raise FreeAgentResilienceError(
                "a next page is claimed at the configured maximum page limit"
            )
        return PaginationDecision(PaginationAction.TERMINAL, None)

    if next_url is None:
        return PaginationDecision(PaginationAction.TERMINAL, None)

    if next_url == current_cursor or next_url in seen:
        raise FreeAgentResilienceError("FreeAgent pagination cursor is repeated or cyclic")

    return PaginationDecision(PaginationAction.CONTINUE, next_url)


def decide_refresh_rotation(
    *,
    old_reference: str,
    new: FreeAgentTokenSet,
) -> RefreshRotationDecision:
    """Decide an atomic, complete token-set rotation without performing storage.

    The new value must be a complete ``FreeAgentTokenSet`` (both access and
    refresh tokens present and valid). ``old_reference`` must be a
    caller-supplied non-secret opaque identifier in the fixed
    ``freeagent.ref.<32 lowercase hex digits>`` format; token-like values,
    readable slugs and malformed values are rejected and never echoed. The
    decision only records non-secret metadata and that identifier; it never
    exposes token strings and never sets ``stored``.
    """
    old_reference = _validate_old_reference(old_reference)
    if not isinstance(new, FreeAgentTokenSet):
        raise FreeAgentResilienceError("new token set must be a FreeAgentTokenSet")
    try:
        validated = parse_token_response(
            {
                "access_token": new.access_token,
                "token_type": new.token_type,
                "expires_in": new.expires_in,
                "refresh_token": new.refresh_token,
                "refresh_token_expires_in": new.refresh_token_expires_in,
            }
        )
    except ValueError as exc:
        raise FreeAgentResilienceError(f"invalid FreeAgent refresh token set: {exc}") from exc
    return RefreshRotationDecision(
        action=RefreshAction.ROTATE,
        old_reference=old_reference,
        token_type=validated.token_type,
        expires_in=validated.expires_in,
        refresh_token_expires_in=validated.refresh_token_expires_in,
    )


def classify_connection_state(
    *,
    access_token_valid: bool,
    refresh_token_valid: bool,
    locally_disconnected: bool = False,
) -> ConnectionState:
    """Classify a connection state from validated token-validity facts only."""
    access_token_valid = _exact_bool(access_token_valid, "access_token_valid")
    refresh_token_valid = _exact_bool(refresh_token_valid, "refresh_token_valid")
    locally_disconnected = _exact_bool(locally_disconnected, "locally_disconnected")

    if locally_disconnected:
        return ConnectionState.LOCAL_DISCONNECTED
    if not refresh_token_valid:
        return ConnectionState.REAUTHORISATION_REQUIRED
    if not access_token_valid:
        return ConnectionState.REFRESH_REQUIRED
    return ConnectionState.CONNECTED


_CONNECTION_TRANSITIONS = {
    (ConnectionState.CONNECTED, ConnectionEvent.ACCESS_TOKEN_EXPIRED):
        ConnectionState.REFRESH_REQUIRED,
    (ConnectionState.CONNECTED, ConnectionEvent.REFRESH_TOKEN_EXPIRED):
        ConnectionState.REAUTHORISATION_REQUIRED,
    (ConnectionState.CONNECTED, ConnectionEvent.LOCAL_DISCONNECT):
        ConnectionState.LOCAL_DISCONNECTED,
    (ConnectionState.REFRESH_REQUIRED, ConnectionEvent.TOKEN_SET_ROTATED):
        ConnectionState.CONNECTED,
    (ConnectionState.REFRESH_REQUIRED, ConnectionEvent.REFRESH_TOKEN_EXPIRED):
        ConnectionState.REAUTHORISATION_REQUIRED,
    (ConnectionState.REFRESH_REQUIRED, ConnectionEvent.LOCAL_DISCONNECT):
        ConnectionState.LOCAL_DISCONNECTED,
    (ConnectionState.REAUTHORISATION_REQUIRED, ConnectionEvent.LOCAL_DISCONNECT):
        ConnectionState.LOCAL_DISCONNECTED,
    (ConnectionState.LOCAL_DISCONNECTED, ConnectionEvent.LOCAL_DISCONNECT):
        ConnectionState.LOCAL_DISCONNECTED,
}


def transition_connection(
    current: ConnectionState,
    event: ConnectionEvent,
    *,
    refresh_token_set: FreeAgentTokenSet | None = None,
    old_reference: str | None = None,
) -> ConnectionState:
    """Apply one connection-state transition, failing closed on invalid moves.

    ``TOKEN_SET_ROTATED`` revalidates the complete token set and non-secret old
    reference at this boundary; neither an event label nor a caller-constructed
    summary decision can restore ``CONNECTED``. The tokens are not retained or
    returned. ``LOCAL_DISCONNECT`` is idempotent and is the only permitted exit
    from a locally disconnected state. No transition performs or claims a
    provider-side revocation call.
    """
    if not isinstance(current, ConnectionState):
        raise FreeAgentResilienceError("current must be a ConnectionState")
    if not isinstance(event, ConnectionEvent):
        raise FreeAgentResilienceError("event must be a ConnectionEvent")
    if event is ConnectionEvent.TOKEN_SET_ROTATED:
        if refresh_token_set is None or old_reference is None:
            raise FreeAgentResilienceError(
                "token-set rotation requires the complete token set and old reference"
            )
        decide_refresh_rotation(
            old_reference=old_reference,
            new=refresh_token_set,
        )
    elif refresh_token_set is not None or old_reference is not None:
        raise FreeAgentResilienceError(
            "refresh token inputs are permitted only for token-set rotation"
        )
    try:
        return _CONNECTION_TRANSITIONS[(current, event)]
    except KeyError:
        raise FreeAgentResilienceError(
            f"invalid connection transition {current.value} -> {event.value}"
        ) from None


_RETRY_AFTER_DIGITS = re.compile(r"^[0-9]+$")
_MAX_RETRY_AFTER_DIGITS = 10


def _parse_retry_after(value: Any) -> int:
    if value is None:
        raise FreeAgentResilienceError("Retry-After is required for a 429 response")
    if isinstance(value, bool):
        raise FreeAgentResilienceError("Retry-After must be a non-negative integer")
    if type(value) is int:
        wait = value
    elif isinstance(value, str):
        stripped = value.strip()
        if (
            not stripped
            or len(stripped) > _MAX_RETRY_AFTER_DIGITS
            or not _RETRY_AFTER_DIGITS.fullmatch(stripped)
        ):
            raise FreeAgentResilienceError("Retry-After must be a non-negative integer")
        try:
            wait = int(stripped)
        except ValueError as exc:
            raise FreeAgentResilienceError(
                "Retry-After must be a non-negative integer"
            ) from exc
    else:
        raise FreeAgentResilienceError("Retry-After must be a non-negative integer")
    if wait < 0:
        raise FreeAgentResilienceError("Retry-After must not be negative")
    return wait


def decide_rate_limit_retry(
    *,
    status_code: int,
    retry_after: Any,
    max_wait_seconds: int = DEFAULT_MAX_WAIT_SECONDS,
) -> RateLimitDecision:
    """Validate a 429/Retry-After and return a bounded wait decision (no sleep).

    Fails closed on a missing, malformed, negative, excessive or conflicting
    Retry-After and on any status other than the single documented retryable
    status (429).
    """
    status_code = _exact_int(status_code, "status_code")
    if status_code != 429:
        raise FreeAgentResilienceError("only HTTP 429 has a documented rate-limit retry contract")
    max_wait_seconds = _exact_positive_int(max_wait_seconds, "max_wait_seconds")
    wait = _parse_retry_after(retry_after)
    if wait > max_wait_seconds:
        raise FreeAgentResilienceError("Retry-After exceeds the configured maximum wait")
    return RateLimitDecision(RateLimitAction.WAIT_AND_RETRY, wait)


def classify_provider_error(
    *,
    status_code: Any,
    retry_after: Any = None,
    max_wait_seconds: int = DEFAULT_MAX_WAIT_SECONDS,
) -> ErrorClassification:
    """Classify a provider status conservatively from retained facts only.

    Only a valid 429 with a usable Retry-After is retryable. A 429 whose
    Retry-After is unusable, and every other status, is non-retryable and
    review-required rather than guessed into a retry.
    """
    status_code = _exact_int(status_code, "status_code")
    if status_code == 429:
        try:
            decision = decide_rate_limit_retry(
                status_code=status_code,
                retry_after=retry_after,
                max_wait_seconds=max_wait_seconds,
            )
        except FreeAgentResilienceError as exc:
            return ErrorClassification(
                ErrorClass.RATE_LIMITED,
                ErrorDisposition.REVIEW_REQUIRED,
                reason=str(exc),
            )
        return ErrorClassification(
            ErrorClass.RATE_LIMITED,
            ErrorDisposition.RETRYABLE,
            retry_after_seconds=decision.retry_after_seconds,
        )
    return ErrorClassification(
        ErrorClass.UNKNOWN,
        ErrorDisposition.REVIEW_REQUIRED,
        reason="provider status is not a documented retryable error",
    )
