"""Synthetic adversarial checks for the network-inert QuickBooks Q-S1 contract."""

import ast
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pytest

from reserved.providers.accounting.quickbooks_oauth_contract import (
    ACCOUNTING_SCOPE,
    AUTHORISATION_ENDPOINT,
    REVOCATION_ENDPOINT,
    TOKEN_ENDPOINT,
    ErrorCallback,
    QuickBooksOAuthContractError,
    RealmBinding,
    SuccessfulCallback,
    build_authorisation_url,
    code_exchange_body,
    parse_callback,
    parse_token_response,
    refresh_body,
    replace_token_set,
    validate_authorisation_url,
)


REDIRECT = "https://reserved.example:8443/oauth/quickbooks/callback"


def valid_url() -> str:
    return build_authorisation_url(
        client_id="synthetic-client", redirect_uri=REDIRECT, state="synthetic-state",
    )


def valid_token_payload() -> dict[str, object]:
    return {
        "access_token": "synthetic-access",
        "refresh_token": "synthetic-refresh",
        "expires_in": 3600,
        "x_refresh_token_expires_in": 100 * 24 * 60 * 60,
        "token_type": "bearer",
    }


def test_exact_endpoints_scope_and_canonical_five_field_request():
    assert AUTHORISATION_ENDPOINT == "https://appcenter.intuit.com/connect/oauth2"
    assert TOKEN_ENDPOINT == "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
    assert REVOCATION_ENDPOINT == "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"
    assert ACCOUNTING_SCOPE == "com.intuit.quickbooks.accounting"
    url = valid_url()
    validate_authorisation_url(url)
    assert parse_qsl(urlsplit(url).query, keep_blank_values=True) == [
        ("client_id", "synthetic-client"),
        ("scope", ACCOUNTING_SCOPE),
        ("redirect_uri", REDIRECT),
        ("response_type", "code"),
        ("state", "synthetic-state"),
    ]


@pytest.mark.parametrize("mutation", [
    lambda pairs: pairs[1:],
    lambda pairs: [(name, "") if name == "state" else (name, value) for name, value in pairs],
    lambda pairs: pairs + [("state", "duplicate")],
    lambda pairs: pairs + [("prompt", "consent")],
    lambda pairs: [pairs[1], pairs[0], *pairs[2:]],
    lambda pairs: [(name, "token") if name == "response_type" else (name, value) for name, value in pairs],
    lambda pairs: [(name, "com.intuit.quickbooks.payment") if name == "scope" else (name, value) for name, value in pairs],
    lambda pairs: [(name, "openid") if name == "scope" else (name, value) for name, value in pairs],
    lambda pairs: [(name, f"{value} openid") if name == "scope" else (name, value) for name, value in pairs],
])
def test_authorisation_parameter_mutations_reach_validator_and_fail(mutation):
    parsed = urlsplit(valid_url())
    original = parse_qsl(parsed.query, keep_blank_values=True)
    changed = mutation(list(original))
    assert changed != original
    unsafe = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(changed), ""))
    with pytest.raises(QuickBooksOAuthContractError):
        validate_authorisation_url(unsafe)


@pytest.mark.parametrize("unsafe", [
    "http://appcenter.intuit.com/connect/oauth2",
    "https://evil.example/connect/oauth2",
    "https://appcenter.intuit.com/wrong",
    "https://user@appcenter.intuit.com/connect/oauth2",
    "https://appcenter.intuit.com:443/connect/oauth2",
    "https://appcenter.intuit.com:/connect/oauth2",
    "https://appcenter.intuit.com:bad/connect/oauth2",
    "https://appcenter.intuit.com/connect/oauth2#fragment",
])
def test_wrong_authorisation_endpoint_mutation_reaches_validator_and_fails(unsafe):
    query = urlsplit(valid_url()).query
    candidate = f"{unsafe}?{query}" if "#" not in unsafe else unsafe.replace("#", f"?{query}#")
    assert candidate != valid_url()
    with pytest.raises(QuickBooksOAuthContractError):
        validate_authorisation_url(candidate)


@pytest.mark.parametrize("redirect", [
    "http://reserved.example/callback",
    "//reserved.example/callback",
    "https://user@reserved.example/callback",
    "https://reserved.example/callback#fragment",
    "https://reserved.example:/callback",
    "https://reserved.example:bad/callback",
    "https://reserved.example:70000/callback",
])
def test_redirect_security_mutations_reach_builders_and_fail(redirect):
    assert redirect != REDIRECT
    with pytest.raises(QuickBooksOAuthContractError):
        build_authorisation_url(client_id="client", redirect_uri=redirect, state="state")
    with pytest.raises(QuickBooksOAuthContractError):
        code_exchange_body(code="code", redirect_uri=redirect)


def test_valid_explicit_https_port_is_preserved_and_bodies_contain_no_secret():
    assert REDIRECT in urlsplit(valid_url()).query.replace("%3A", ":").replace("%2F", "/")
    assert code_exchange_body(code="synthetic-code", redirect_uri=REDIRECT) == {
        "grant_type": "authorization_code", "code": "synthetic-code", "redirect_uri": REDIRECT,
    }
    assert refresh_body(refresh_token="synthetic-refresh") == {
        "grant_type": "refresh_token", "refresh_token": "synthetic-refresh",
    }
    assert "client_secret" not in code_exchange_body(code="code", redirect_uri=REDIRECT)


def test_success_callback_state_code_and_realm_boundaries():
    callback = parse_callback(
        {"code": "c" * 512, "state": "expected", "realmId": "realm-1"},
        expected_state="expected",
    )
    assert isinstance(callback, SuccessfulCallback)
    assert callback.realm_id == "realm-1"
    assert "c" * 512 not in repr(callback)


@pytest.mark.parametrize("parameters, expected_state", [
    ({"code": "code", "realmId": "realm"}, "expected"),
    ({"code": "code", "state": "wrong", "realmId": "realm"}, "expected"),
    ({"code": "code", "state": "expected", "realmId": ""}, "expected"),
    ({"code": "", "state": "expected", "realmId": "realm"}, "expected"),
    ({"code": "c" * 513, "state": "expected", "realmId": "realm"}, "expected"),
    ({"code": "code", "state": "expected", "realmId": "realm", "error": "access_denied"}, "expected"),
])
def test_invalid_success_callbacks_fail(parameters, expected_state):
    with pytest.raises(QuickBooksOAuthContractError):
        parse_callback(parameters, expected_state=expected_state)


@pytest.mark.parametrize("error", ["access_denied", "invalid_scope"])
def test_documented_error_callbacks_are_never_usable_bindings(error):
    callback = parse_callback({"error": error, "state": "expected"}, expected_state="expected")
    assert callback == ErrorCallback(error=error)
    assert not isinstance(callback, SuccessfulCallback)
    assert not hasattr(callback, "realm_id")


def test_realm_binding_rejects_blanks_and_cross_owner_or_realm_substitution():
    binding = RealmBinding("user-1", "realm-1", "opaque-credential-reference")
    binding.assert_owner(user_id="user-1", realm_id="realm-1")
    for user_id, realm_id in (("user-2", "realm-1"), ("user-1", "realm-2")):
        with pytest.raises(QuickBooksOAuthContractError):
            binding.assert_owner(user_id=user_id, realm_id=realm_id)
    for values in (("", "realm", "ref"), ("user", "", "ref"), ("user", "realm", "")):
        with pytest.raises(QuickBooksOAuthContractError):
            RealmBinding(*values)


@pytest.mark.parametrize("field", list(valid_token_payload()))
def test_token_response_requires_every_documented_minimum_field(field):
    payload = valid_token_payload()
    removed = payload.pop(field)
    assert removed is not None and field not in payload
    with pytest.raises(QuickBooksOAuthContractError):
        parse_token_response(payload)


@pytest.mark.parametrize("field, value", [
    ("access_token", ""), ("access_token", "a" * 4097),
    ("refresh_token", ""), ("refresh_token", "r" * 513),
    ("token_type", "Bearer"), ("token_type", 1),
    ("expires_in", 0), ("expires_in", -1), ("expires_in", True),
    ("expires_in", False), ("expires_in", 3600.0), ("expires_in", "3600"),
    ("x_refresh_token_expires_in", 0), ("x_refresh_token_expires_in", True),
    ("x_refresh_token_expires_in", 1.0), ("x_refresh_token_expires_in", "8640000"),
])
def test_token_type_length_and_exact_lifetime_mutations_fail(field, value):
    payload = valid_token_payload()
    assert payload[field] != value or type(payload[field]) is not type(value)
    payload[field] = value
    with pytest.raises(QuickBooksOAuthContractError):
        parse_token_response(payload)


@pytest.mark.parametrize("value", [0, -1, True, False, 1.0, "1"])
def test_conditional_hard_expiry_requires_positive_exact_integer(value):
    payload = valid_token_payload()
    payload["x_refresh_token_hard_expires_in"] = value
    with pytest.raises(QuickBooksOAuthContractError):
        parse_token_response(payload)


def test_additive_fields_and_conditional_hard_expiry_are_accepted_without_meaning():
    payload = valid_token_payload()
    payload.update({"x_refresh_token_hard_expires_in": 123, "future_field": {"opaque": True}})
    tokens = parse_token_response(payload)
    assert tokens.x_refresh_token_hard_expires_in == 123
    assert not hasattr(tokens, "future_field")


def test_documented_maximum_token_lengths_are_accepted():
    payload = valid_token_payload()
    payload.update({"access_token": "a" * 4096, "refresh_token": "r" * 512})
    tokens = parse_token_response(payload)
    assert len(tokens.access_token) == 4096
    assert len(tokens.refresh_token) == 512


def test_rotation_selects_complete_latest_set_and_repr_reveals_neither_token():
    previous = parse_token_response(valid_token_payload())
    refreshed_payload = valid_token_payload()
    refreshed_payload.update({"access_token": "latest-access", "refresh_token": "latest-refresh"})
    refreshed = parse_token_response(refreshed_payload)
    latest = replace_token_set(previous, refreshed)
    assert latest is refreshed and latest is not previous
    assert refresh_body(refresh_token=latest.refresh_token) == {
        "grant_type": "refresh_token", "refresh_token": "latest-refresh",
    }
    combined_repr = repr((previous, refreshed, latest))
    for secret in ("synthetic-access", "synthetic-refresh", "latest-access", "latest-refresh"):
        assert secret not in combined_repr


def test_module_has_no_network_capable_imports_and_placeholder_stays_unexposed():
    module_path = Path("reserved/providers/accounting/quickbooks_oauth_contract.py")
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree) if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    assert imported_roots.isdisjoint({"requests", "httpx", "urllib3", "socket", "http", "subprocess"})

    from reserved.providers.accounting.quickbooks import QuickBooksProvider

    provider = QuickBooksProvider()
    with pytest.raises(NotImplementedError):
        provider.authorisation_url("user", REDIRECT)
