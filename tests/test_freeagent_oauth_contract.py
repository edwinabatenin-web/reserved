"""Synthetic, network-free FreeAgent OAuth contract tests."""

from urllib.parse import parse_qs, urlparse

import pytest

from reserved.providers.accounting.freeagent_oauth_contract import (
    SANDBOX_AUTHORISATION_ENDPOINT,
    SANDBOX_TOKEN_ENDPOINT,
    build_sandbox_authorisation_url,
    code_exchange_body,
    parse_token_response,
    refresh_body,
    validate_authorisation_url,
)


def test_sandbox_endpoints_are_exact_reviewed_origins():
    assert SANDBOX_AUTHORISATION_ENDPOINT == "https://api.sandbox.freeagent.com/v2/approve_app"
    assert SANDBOX_TOKEN_ENDPOINT == "https://api.sandbox.freeagent.com/v2/token_endpoint"


def test_authorisation_request_is_sandbox_confined_and_exact():
    url = build_sandbox_authorisation_url(
        client_id="synthetic-client", redirect_uri="https://reserved.example/callback",
        state="synthetic-single-use-state",
    )
    validate_authorisation_url(url)
    parsed = urlparse(url)
    assert parse_qs(parsed.query) == {
        "client_id": ["synthetic-client"], "response_type": ["code"],
        "redirect_uri": ["https://reserved.example/callback"],
        "state": ["synthetic-single-use-state"],
    }


@pytest.mark.parametrize("unsafe", [
    "https://api.freeagent.com/v2/approve_app?client_id=x&response_type=code&redirect_uri=https%3A%2F%2Fr&state=s",
    "https://api.sandbox.freeagent.com/v2/other?client_id=x&response_type=code&redirect_uri=https%3A%2F%2Fr&state=s",
    "https://api.sandbox.freeagent.com/v2/approve_app?client_id=x&response_type=token&redirect_uri=https%3A%2F%2Fr&state=s",
])
def test_authorisation_validator_rejects_production_wrong_path_and_wrong_flow(unsafe):
    with pytest.raises(ValueError):
        validate_authorisation_url(unsafe)


def test_exact_code_and_refresh_request_bodies():
    assert code_exchange_body(code="synthetic-code", redirect_uri="https://reserved.example/callback") == {
        "grant_type": "authorization_code", "code": "synthetic-code",
        "redirect_uri": "https://reserved.example/callback",
    }
    assert refresh_body(refresh_token="synthetic-refresh") == {
        "grant_type": "refresh_token", "refresh_token": "synthetic-refresh",
    }


def test_documented_token_response_is_typed_and_refresh_token_is_preserved():
    result = parse_token_response({
        "access_token": "synthetic-access", "token_type": "bearer", "expires_in": 3600,
        "refresh_token": "synthetic-rotated-refresh", "refresh_token_expires_in": 631151957,
    })
    assert result.refresh_token == "synthetic-rotated-refresh"
    assert result.expires_in == 3600


@pytest.mark.parametrize("change", [
    {"access_token": ""}, {"token_type": "Bearer"}, {"expires_in": "3600"},
    {"refresh_token": ""}, {"refresh_token_expires_in": 0},
])
def test_token_response_fails_closed_on_missing_or_wrong_documented_values(change):
    payload = {
        "access_token": "synthetic-access", "token_type": "bearer", "expires_in": 3600,
        "refresh_token": "synthetic-refresh", "refresh_token_expires_in": 631151957,
    }
    payload.update(change)
    with pytest.raises(ValueError):
        parse_token_response(payload)


def test_module_contains_no_http_client_or_credentials():
    import reserved.providers.accounting.freeagent_oauth_contract as contract

    assert not hasattr(contract, "requests")
    assert not hasattr(contract, "httpx")

