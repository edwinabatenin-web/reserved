"""Fail-closed configuration checks for external-provider sandboxes.

This module only inspects whether named environment variables are present. It
never returns, logs or transmits their values and it performs no network calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping
from unicodedata import category
from urllib.parse import urlparse


class ReadinessState(str, Enum):
    DISABLED = "disabled"
    INCOMPLETE = "incomplete"
    READY_FOR_SANDBOX_TEST = "ready_for_sandbox_test"
    CONFIGURED_NOT_IMPLEMENTED = "configured_not_implemented"
    BLOCKED_UNSAFE_ENVIRONMENT = "blocked_unsafe_environment"


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    credential_variables: tuple[str, ...]
    environment_variable: str
    callback_variable: str | None = None
    implementation_enabled: bool = False


@dataclass(frozen=True)
class ReadinessResult:
    provider: str
    state: ReadinessState
    environment: str | None
    missing_variables: tuple[str, ...]
    messages: tuple[str, ...]

    @property
    def may_make_sandbox_calls(self) -> bool:
        return self.state is ReadinessState.READY_FOR_SANDBOX_TEST


PROVIDERS: tuple[ProviderSpec, ...] = (
    ProviderSpec("hmrc", ("HMRC_CLIENT_ID", "HMRC_CLIENT_SECRET"),
                 "HMRC_ENVIRONMENT", "HMRC_REDIRECT_URI"),
    ProviderSpec("yapily", ("YAPILY_APPLICATION_UUID", "YAPILY_SECRET"),
                 "YAPILY_ENVIRONMENT", "YAPILY_CALLBACK_URI"),
    ProviderSpec("freeagent", ("FREEAGENT_OAUTH_IDENTIFIER", "FREEAGENT_OAUTH_SECRET"),
                 "FREEAGENT_ENVIRONMENT", "FREEAGENT_REDIRECT_URI"),
    ProviderSpec("xero", ("XERO_CLIENT_ID", "XERO_CLIENT_SECRET"),
                 "XERO_ENVIRONMENT", "XERO_REDIRECT_URI"),
    ProviderSpec("quickbooks", ("QUICKBOOKS_CLIENT_ID", "QUICKBOOKS_CLIENT_SECRET"),
                 "QUICKBOOKS_ENVIRONMENT", "QUICKBOOKS_REDIRECT_URI"),
)

_SAFE_ENVIRONMENTS = frozenset({"sandbox", "test", "development"})
_HEXADECIMAL_DIGITS = frozenset("0123456789abcdefABCDEF")


def _present(environment: Mapping[str, str], name: str) -> bool:
    return bool(environment.get(name, "").strip())


def _callback_is_safe(value: str) -> bool:
    # Validate the raw value before urllib can discard CR, LF or TAB.  A raw
    # fragment marker is rejected explicitly so that a trailing, empty
    # fragment cannot be confused with no fragment at all.
    if "#" in value or "\\" in value or any(
        char.isspace() or category(char).startswith("C")
        for char in value
    ):
        return False

    index = 0
    while index < len(value):
        if value[index] != "%":
            index += 1
            continue
        if (
            index + 2 >= len(value)
            or value[index + 1] not in _HEXADECIMAL_DIGITS
            or value[index + 2] not in _HEXADECIMAL_DIGITS
        ):
            return False
        encoded_byte = int(value[index + 1:index + 3], 16)
        if encoded_byte <= 0x1F or encoded_byte == 0x7F:
            return False
        index += 3

    try:
        parsed = urlparse(value)
    except ValueError:
        return False

    try:
        username = parsed.username
        password = parsed.password
        hostname = parsed.hostname
        port = parsed.port  # validate port syntax; raises ValueError when invalid
    except ValueError:
        return False

    if parsed.netloc.endswith(":") or "%" in parsed.netloc:
        return False

    if port is not None and not 1 <= port <= 65535:
        return False

    if username is not None or password is not None:
        return False

    if parsed.scheme == "https":
        if not hostname or not hostname.strip("."):
            return False
        return not any(char.isspace() for char in hostname)

    return parsed.scheme == "http" and hostname in {"localhost", "127.0.0.1"}


def assess_provider(spec: ProviderSpec, environment: Mapping[str, str]) -> ReadinessResult:
    """Assess configuration without exposing any secret value."""
    configured_credentials = tuple(v for v in spec.credential_variables if _present(environment, v))
    if not configured_credentials:
        return ReadinessResult(spec.name, ReadinessState.DISABLED, None,
                               spec.credential_variables, ("No credentials configured; connector remains disabled.",))

    missing = tuple(v for v in spec.credential_variables if v not in configured_credentials)
    if missing:
        return ReadinessResult(spec.name, ReadinessState.INCOMPLETE, None, missing,
                               ("Partial credential pair; network access must remain disabled.",))

    environment_name = environment.get(spec.environment_variable, "").strip().lower()
    if environment_name not in _SAFE_ENVIRONMENTS:
        return ReadinessResult(
            spec.name, ReadinessState.BLOCKED_UNSAFE_ENVIRONMENT, environment_name or None,
            (() if environment_name else (spec.environment_variable,)),
            ("Environment must be explicitly set to sandbox, test or development.",),
        )

    if spec.callback_variable:
        callback = environment.get(spec.callback_variable, "")
        if not callback.strip():
            return ReadinessResult(spec.name, ReadinessState.INCOMPLETE, environment_name,
                                   (spec.callback_variable,),
                                   ("Registered OAuth callback URI is required.",))
        if not _callback_is_safe(callback):
            return ReadinessResult(spec.name, ReadinessState.INCOMPLETE, environment_name,
                                   (spec.callback_variable,),
                                   ("Callback must use HTTPS, except localhost during development.",))

    if not spec.implementation_enabled:
        return ReadinessResult(
            spec.name,
            ReadinessState.CONFIGURED_NOT_IMPLEMENTED,
            environment_name,
            (),
            (
                "Sandbox configuration is complete, but the network adapter "
                "has not passed its implementation gate; external calls remain disabled.",
            ),
        )

    return ReadinessResult(spec.name, ReadinessState.READY_FOR_SANDBOX_TEST,
                           environment_name, (), ("Configuration and adapter are ready for an explicit sandbox test.",))


def assess_all(environment: Mapping[str, str]) -> tuple[ReadinessResult, ...]:
    return tuple(assess_provider(spec, environment) for spec in PROVIDERS)
