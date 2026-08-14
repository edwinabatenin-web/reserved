"""Provider-neutral, network-inert HTTP boundary for sandbox adapters.

This module does not perform HTTP requests. It validates an adapter's intended
request before a separately supplied transport sends it. Exact origins are
injected by the provider adapter so this layer never guesses provider paths or
silently falls back from sandbox to production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Mapping, Protocol
from urllib.parse import urlsplit


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class ProviderBoundaryError(ValueError):
    """Raised before network access when a provider request is unsafe."""


_SENSITIVE_HEADERS = frozenset({
    "authorization", "proxy-authorization", "cookie", "set-cookie",
    "x-api-key", "api-key",
})


def _normalise_origin(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ProviderBoundaryError("Provider origin must be an absolute HTTPS origin")
    if parsed.username or parsed.password:
        raise ProviderBoundaryError("Provider origin must not contain user information")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise ProviderBoundaryError("Provider origin must not contain a path, query or fragment")
    host = parsed.hostname.lower()
    port = f":{parsed.port}" if parsed.port is not None else ""
    return f"https://{host}{port}"


@dataclass(frozen=True)
class EndpointPolicy:
    """Exact origins approved for one explicitly selected environment."""

    provider: str
    environment: str
    allowed_origins: frozenset[str]

    def __post_init__(self) -> None:
        if self.environment not in {"sandbox", "test", "demo"}:
            raise ProviderBoundaryError("Only sandbox, test or demo policies are permitted")
        if not self.provider.strip() or not self.allowed_origins:
            raise ProviderBoundaryError("Provider and at least one origin are required")
        normalised = frozenset(_normalise_origin(item) for item in self.allowed_origins)
        object.__setattr__(self, "allowed_origins", normalised)

    def validate_url(self, url: str) -> None:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ProviderBoundaryError("Provider URL must be absolute HTTPS")
        if parsed.username or parsed.password or parsed.fragment:
            raise ProviderBoundaryError("Provider URL contains prohibited URL components")
        try:
            port = f":{parsed.port}" if parsed.port is not None else ""
        except ValueError as exc:
            raise ProviderBoundaryError("Provider URL has an invalid port") from exc
        origin = f"https://{parsed.hostname.lower()}{port}"
        if origin not in self.allowed_origins:
            raise ProviderBoundaryError(
                f"URL origin is not approved for {self.provider} {self.environment}"
            )


@dataclass(frozen=True)
class ProviderRequest:
    method: HttpMethod
    url: str
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes | None = None
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        # A read-only copy prevents mutation after policy validation.
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))

    def redacted_summary(self) -> dict:
        """Return evidence-safe metadata, never request bodies or secret values."""
        parsed = urlsplit(self.url)
        # Rebuild the origin from hostname/port so URL user-info can never be
        # copied into evidence even if a caller summarises before validation.
        try:
            port = f":{parsed.port}" if parsed.port is not None else ""
        except ValueError:
            port = ":invalid-port"
        safe_origin = (
            f"{parsed.scheme}://{parsed.hostname.lower()}{port}"
            if parsed.scheme and parsed.hostname else "[INVALID ORIGIN]"
        )
        headers = {
            name: ("[REDACTED]" if name.lower() in _SENSITIVE_HEADERS else value)
            for name, value in self.headers.items()
        }
        return {
            "method": self.method.value,
            "origin": safe_origin,
            "path": parsed.path,
            "query_present": bool(parsed.query),
            "headers": headers,
            "body_present": self.body is not None,
            "body_length": len(self.body) if self.body is not None else 0,
            "correlation_id": self.correlation_id,
        }


@dataclass(frozen=True)
class ProviderResponse:
    status_code: int
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes = b""

    def __post_init__(self) -> None:
        if not 100 <= self.status_code <= 599:
            raise ProviderBoundaryError("Invalid HTTP response status")
        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))


class HttpTransport(Protocol):
    """Injected transport. Tests can implement this without network access."""

    def send(self, request: ProviderRequest) -> ProviderResponse: ...


class GuardedTransport:
    """Validate every outbound URL before delegating to an injected transport."""

    def __init__(self, policy: EndpointPolicy, transport: HttpTransport) -> None:
        self._policy = policy
        self._transport = transport

    def send(self, request: ProviderRequest) -> ProviderResponse:
        self._policy.validate_url(request.url)
        return self._transport.send(request)
