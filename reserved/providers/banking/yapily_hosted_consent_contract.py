"""Provisional, network-inert Yapily AIS Hosted Consent request contract.

Provider responses and browser handoff are deliberately outside this module.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlsplit

CREATE_HOSTED_CONSENT_PATH = "/hosted/consent-requests"
GET_HOSTED_CONSENT_PATH_TEMPLATE = "/hosted/consent-requests/{consent_request_id}"
COUNTRY = "GB"
LANGUAGE = "en"
FEATURE_SCOPE = ("ACCOUNTS", "ACCOUNT_TRANSACTIONS")
_MAX_ID = 128
_MAX_URL = 2048
_PATH_SEGMENT = re.compile(r"[A-Za-z0-9._~-]+")


class YapilyHostedConsentContractError(ValueError):
    """A non-sensitive, fail-closed contract-validation error."""


def _text(value: Any, name: str, *, maximum: int = _MAX_ID) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise YapilyHostedConsentContractError(f"{name} must be a bounded non-empty string")
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value):
        raise YapilyHostedConsentContractError(f"{name} contains whitespace or control characters")
    return value


def _https_url(value: Any, name: str) -> str:
    value = _text(value, name, maximum=_MAX_URL)
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError as exc:
        raise YapilyHostedConsentContractError(f"{name} is malformed") from exc
    if parsed.scheme != "https" or not parsed.netloc or not parsed.hostname:
        raise YapilyHostedConsentContractError(f"{name} must be an absolute HTTPS URL")
    if parsed.username is not None or parsed.password is not None or parsed.fragment:
        raise YapilyHostedConsentContractError(f"{name} must not contain userinfo or a fragment")
    if "\\" in value:
        raise YapilyHostedConsentContractError(f"{name} must not contain a backslash")
    if parsed.netloc.endswith(":") or port is not None and not 1 <= port <= 65535:
        raise YapilyHostedConsentContractError(f"{name} contains an invalid port")
    return value


def _mapping(value: Any, fields: frozenset[str], *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise YapilyHostedConsentContractError(f"{name} must be an object")
    if set(value) != fields:
        raise YapilyHostedConsentContractError(f"{name} fields do not match the reviewed contract")
    return value


def _institution_identifiers(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        raise YapilyHostedConsentContractError("institutionIdentifiers must be an object")
    fields = {"institutionCountryCode"}
    if "institutionId" in value:
        fields.add("institutionId")
    data = _mapping(value, frozenset(fields), name="institutionIdentifiers")
    if data["institutionCountryCode"] != COUNTRY:
        raise YapilyHostedConsentContractError("only GB institutions are permitted")
    return _text(data["institutionId"], "institution_id") if "institutionId" in data else None


def _user_settings(value: Any) -> None:
    data = _mapping(value, frozenset({"language", "location"}), name="userSettings")
    if data != {"language": LANGUAGE, "location": COUNTRY}:
        raise YapilyHostedConsentContractError("userSettings must be exactly en and GB")


@dataclass(frozen=True)
class ApplicationUserIdentity:
    """Reserved's stable, non-secret user identifier; never a Yapily user ID."""

    value: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _text(self.value, "application_user_id"))


@dataclass(frozen=True)
class HostedConsentRequest:
    application_user: ApplicationUserIdentity
    redirect_url: str
    institution_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.application_user, ApplicationUserIdentity):
            raise YapilyHostedConsentContractError("application_user must be a stable Reserved identity")
        object.__setattr__(self, "redirect_url", _https_url(self.redirect_url, "redirect_url"))
        if self.institution_id is not None:
            object.__setattr__(self, "institution_id", _text(self.institution_id, "institution_id"))

    def payload(self) -> Mapping[str, Any]:
        identifiers = {"institutionCountryCode": COUNTRY}
        if self.institution_id is not None:
            identifiers["institutionId"] = self.institution_id
        return MappingProxyType({
            "applicationUserId": self.application_user.value,
            "institutionIdentifiers": identifiers,
            "userSettings": {"language": LANGUAGE, "location": COUNTRY},
            "redirectUrl": self.redirect_url,
            "accountRequest": {"featureScope": list(FEATURE_SCOPE)},
        })


def parse_request_payload(payload: Any) -> HostedConsentRequest:
    """Parse the deterministic documented request shape used by Y1."""
    data = _mapping(payload, frozenset({
        "applicationUserId", "institutionIdentifiers", "userSettings", "redirectUrl",
        "accountRequest",
    }), name="request payload")
    institution_id = _institution_identifiers(data["institutionIdentifiers"])
    _user_settings(data["userSettings"])
    account_request = _mapping(
        data["accountRequest"], frozenset({"featureScope"}), name="accountRequest"
    )
    scope = account_request["featureScope"]
    if not isinstance(scope, list) or tuple(scope) != FEATURE_SCOPE:
        raise YapilyHostedConsentContractError("featureScope must be the exact AIS scope")
    return HostedConsentRequest(
        ApplicationUserIdentity(data["applicationUserId"]), data["redirectUrl"], institution_id
    )

def hosted_consent_status_path(consent_request_id: str) -> str:
    """Build the documented relative GET path without retrieving a response."""
    consent_request_id = _text(consent_request_id, "consent_request_id")
    if _PATH_SEGMENT.fullmatch(consent_request_id) is None:
        raise YapilyHostedConsentContractError(
            "consent_request_id must be one ASCII unreserved path segment"
        )
    return GET_HOSTED_CONSENT_PATH_TEMPLATE.format(consent_request_id=consent_request_id)
