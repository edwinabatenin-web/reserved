"""Network-free regression tests for Clerk claim-validation boundaries."""

from reserved.auth import _clerk_claims_are_accepted


ISSUER = "https://reserved.clerk.accounts.dev"
ORIGINS = ("https://reserved.example", "http://localhost:5000")


def claims(**overrides):
    value = {
        "iss": ISSUER,
        "sub": "user_synthetic",
        "sid": "sess_synthetic",
        "azp": "https://reserved.example",
    }
    value.update(overrides)
    return value


def accepted(value, audience=None):
    return _clerk_claims_are_accepted(
        value,
        frontend_api=ISSUER,
        authorized_parties=ORIGINS,
        audience=audience,
    )


def test_expected_instance_and_authorized_party_are_accepted():
    assert accepted(claims()) is True


def test_wrong_instance_issuer_is_rejected():
    assert accepted(claims(iss="https://other.clerk.accounts.dev")) is False


def test_unlisted_authorized_party_is_rejected():
    assert accepted(claims(azp="https://attacker.example")) is False


def test_absent_authorized_party_is_allowed_per_clerk_contract():
    value = claims()
    value.pop("azp")
    assert accepted(value) is True


def test_subject_and_session_id_are_required():
    assert accepted(claims(sub="")) is False
    assert accepted(claims(sid="")) is False


def test_configured_string_audience_must_match():
    assert accepted(claims(aud="reserved-api"), "reserved-api") is True
    assert accepted(claims(aud="other"), "reserved-api") is False


def test_configured_list_audience_must_contain_expected_value():
    assert accepted(claims(aud=["other", "reserved-api"]), "reserved-api") is True
    assert accepted(claims(aud=["other"]), "reserved-api") is False


def test_audience_is_not_required_without_explicit_custom_configuration():
    value = claims()
    value.pop("aud", None)
    assert accepted(value) is True
