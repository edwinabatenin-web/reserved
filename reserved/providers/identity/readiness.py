"""Fail-closed readiness checks for brokered Google and Apple sign-in.

Reserved currently uses Clerk as its identity broker.  These checks do not
contact Clerk, Google or Apple and do not inspect credentials.  They require a
deployment owner to attest that the corresponding provider configuration has
been completed and tested before a provider may be described as launch-ready.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlparse


PROVIDERS = ("google", "apple")
_ATTESTATION_VARIABLE = {
    "google": "GOOGLE_SIGN_IN_CONFIGURED",
    "apple": "APPLE_SIGN_IN_CONFIGURED",
}


@dataclass(frozen=True)
class IdentityReadiness:
    provider: str
    ready: bool
    blockers: tuple[str, ...]


def _is_https_origin(value: str) -> bool:
    parsed = urlparse(value)
    return (
        parsed.scheme == "https"
        and bool(parsed.netloc)
        and parsed.path in ("", "/")
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
        and parsed.username is None
        and parsed.password is None
    )


def _has_production_session_secret(value: str) -> bool:
    return len(value) >= 32 and value != "reserved-local-preview-only"


def assess_identity_readiness(
    provider: str,
    values: Mapping[str, str],
) -> IdentityReadiness:
    """Return launch readiness without making network calls or exposing secrets.

    ``*_SIGN_IN_CONFIGURED=1`` is an explicit human attestation, not a secret.
    It should be set only after the provider-console checklist and a synthetic
    end-to-end journey have passed.  Missing or ambiguous evidence fails closed.
    """
    name = provider.strip().lower()
    if name not in PROVIDERS:
        raise ValueError(f"Unsupported identity provider: {provider}")

    blockers: list[str] = []
    broker = values.get("IDENTITY_BROKER", "").strip().lower()
    if broker != "clerk":
        blockers.append("IDENTITY_BROKER must explicitly be set to clerk.")

    publishable_key = values.get("CLERK_PUBLISHABLE_KEY", "").strip()
    if not publishable_key.startswith(("pk_test_", "pk_live_")):
        blockers.append("A recognisable Clerk publishable key is required.")

    if not _has_production_session_secret(values.get("SESSION_SECRET", "")):
        blockers.append("A non-default SESSION_SECRET of at least 32 characters is required.")

    origin = values.get("AUTH_PUBLIC_ORIGIN", "").strip()
    if not _is_https_origin(origin):
        blockers.append("AUTH_PUBLIC_ORIGIN must be one HTTPS origin with no path or credentials.")

    attestation = _ATTESTATION_VARIABLE[name]
    if values.get(attestation, "").strip() != "1":
        blockers.append(
            f"{attestation}=1 is required only after provider-console and synthetic journey checks pass."
        )

    return IdentityReadiness(name, not blockers, tuple(blockers))
