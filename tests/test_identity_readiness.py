"""Synthetic, network-free identity launch-readiness checks."""

import pytest

from reserved.providers.identity.readiness import assess_identity_readiness


def complete_values() -> dict[str, str]:
    return {
        "IDENTITY_BROKER": "clerk",
        "CLERK_PUBLISHABLE_KEY": "pk_test_synthetic-not-a-real-key",
        "SESSION_SECRET": "synthetic-session-secret-at-least-32-characters",
        "AUTH_PUBLIC_ORIGIN": "https://preview.reserved.example",
        "GOOGLE_SIGN_IN_CONFIGURED": "1",
        "APPLE_SIGN_IN_CONFIGURED": "1",
    }


@pytest.mark.parametrize("provider", ["google", "apple"])
def test_complete_attested_configuration_is_ready_for_synthetic_journey(provider):
    result = assess_identity_readiness(provider, complete_values())
    assert result.ready is True
    assert result.blockers == ()


@pytest.mark.parametrize("provider", ["google", "apple"])
def test_provider_configuration_must_be_explicitly_attested(provider):
    values = complete_values()
    values.pop(f"{provider.upper()}_SIGN_IN_CONFIGURED")
    result = assess_identity_readiness(provider, values)
    assert result.ready is False
    assert "synthetic journey checks pass" in result.blockers[-1]


def test_google_attestation_does_not_enable_apple():
    values = complete_values()
    values.pop("APPLE_SIGN_IN_CONFIGURED")
    assert assess_identity_readiness("google", values).ready is True
    assert assess_identity_readiness("apple", values).ready is False


@pytest.mark.parametrize(
    "origin",
    [
        "http://reserved.example",
        "https://user:password@reserved.example",
        "https://reserved.example/callback",
        "https://reserved.example?next=elsewhere",
        "reserved.example",
        "",
    ],
)
def test_public_origin_must_be_a_clean_https_origin(origin):
    values = complete_values()
    values["AUTH_PUBLIC_ORIGIN"] = origin
    result = assess_identity_readiness("google", values)
    assert result.ready is False
    assert any("HTTPS origin" in blocker for blocker in result.blockers)


def test_default_or_short_session_secret_fails_closed():
    for secret in ("", "short", "reserved-local-preview-only"):
        values = complete_values()
        values["SESSION_SECRET"] = secret
        assert assess_identity_readiness("google", values).ready is False


def test_publishable_key_does_not_prove_provider_is_configured():
    values = complete_values()
    values.pop("GOOGLE_SIGN_IN_CONFIGURED")
    result = assess_identity_readiness("google", values)
    assert result.ready is False


def test_unknown_provider_is_rejected():
    with pytest.raises(ValueError):
        assess_identity_readiness("other", complete_values())
