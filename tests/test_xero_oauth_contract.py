"""Synthetic, network-free Xero OAuth and tenant contract tests."""

from dataclasses import FrozenInstanceError
from urllib.parse import parse_qs, urlparse

import pytest

from reserved.providers.accounting.xero_oauth_contract import (
    AUTHORISATION_ENDPOINT,
    AUTHORISATION_SCOPE,
    CONNECTIONS_ENDPOINT,
    TOKEN_ENDPOINT,
    build_authorisation_url,
    code_exchange_body,
    match_organisation_connections,
    parse_connections,
    parse_token_response,
    refresh_body,
    validate_authorisation_url,
)


def connection(**changes):
    value = {
        "id": "connection-1",
        "authEventId": "event-1",
        "tenantId": "tenant-1",
        "tenantType": "ORGANISATION",
        "tenantName": None,
        "createdDateUtc": "2026-provider-created",
        "updatedDateUtc": "2026-provider-updated",
    }
    value.update(changes)
    return value


def token(**changes):
    value = {
        "access_token": "synthetic-access",
        "expires_in": 1800,
        "token_type": "Bearer",
        "refresh_token": "synthetic-rotated-refresh",
    }
    value.update(changes)
    return value


def test_exact_endpoints_and_fixed_minimum_scope():
    assert AUTHORISATION_ENDPOINT == "https://login.xero.com/identity/connect/authorize"
    assert TOKEN_ENDPOINT == "https://identity.xero.com/connect/token"
    assert CONNECTIONS_ENDPOINT == "https://api.xero.com/connections"
    assert AUTHORISATION_SCOPE == "accounting.invoices.read offline_access"


def test_builds_exact_https_authorisation_request_with_required_state():
    url = build_authorisation_url(
        client_id="synthetic-client",
        redirect_uri="https://reserved.example/xero/callback",
        state="synthetic-state",
    )
    validate_authorisation_url(url)
    assert parse_qs(urlparse(url).query) == {
        "response_type": ["code"],
        "client_id": ["synthetic-client"],
        "scope": ["accounting.invoices.read offline_access"],
        "redirect_uri": ["https://reserved.example/xero/callback"],
        "state": ["synthetic-state"],
    }


@pytest.mark.parametrize(
    "change",
    [{"client_id": ""}, {"state": " "}, {"redirect_uri": "http://localhost/cb"}],
)
def test_builder_rejects_blank_values_missing_state_and_non_https_redirect(change):
    values = {
        "client_id": "client",
        "redirect_uri": "https://reserved.example/cb",
        "state": "state",
    }
    values.update(change)
    with pytest.raises(ValueError):
        build_authorisation_url(**values)


@pytest.mark.parametrize(
    "redirect_uri",
    [
        "https://reserved.example/cb#fragment",
        "https://reserved.example:not-a-port/cb",
    ],
)
def test_builder_rejects_fragment_and_invalid_explicit_port_in_redirect_uri(redirect_uri):
    with pytest.raises(ValueError):
        build_authorisation_url(client_id="c", redirect_uri=redirect_uri, state="s")


def test_explicit_empty_port_is_rejected_by_every_redirect_entry_point():
    redirect_uri = "https://reserved.example:/cb"
    with pytest.raises(ValueError):
        build_authorisation_url(client_id="c", redirect_uri=redirect_uri, state="s")
    with pytest.raises(ValueError):
        code_exchange_body(code="synthetic-code", redirect_uri=redirect_uri)
    with pytest.raises(ValueError):
        validate_authorisation_url(
            f"{AUTHORISATION_ENDPOINT}?response_type=code&client_id=c"
            "&scope=accounting.invoices.read%20offline_access"
            "&redirect_uri=https%3A%2F%2Freserved.example%3A%2Fcb&state=s"
        )


@pytest.mark.parametrize(
    "redirect_uri",
    ["https://reserved.example/cb", "https://reserved.example:8443/cb"],
)
def test_redirect_uri_preserves_absent_and_valid_numeric_ports(redirect_uri):
    url = build_authorisation_url(client_id="c", redirect_uri=redirect_uri, state="s")
    validate_authorisation_url(url)
    assert parse_qs(urlparse(url).query)["redirect_uri"] == [redirect_uri]
    assert code_exchange_body(code="synthetic-code", redirect_uri=redirect_uri)[
        "redirect_uri"
    ] == redirect_uri


@pytest.mark.parametrize(
    "url",
    [
        "http://login.xero.com/identity/connect/authorize?response_type=code&client_id=c"
        "&scope=accounting.invoices.read%20offline_access"
        "&redirect_uri=https%3A%2F%2Fr.example%2Fcb&state=s",
        "https://evil.example/identity/connect/authorize?response_type=code&client_id=c"
        "&scope=accounting.invoices.read%20offline_access"
        "&redirect_uri=https%3A%2F%2Fr.example%2Fcb&state=s",
        "https://login.xero.com/identity/connect/other?response_type=code&client_id=c"
        "&scope=accounting.invoices.read%20offline_access"
        "&redirect_uri=https%3A%2F%2Fr.example%2Fcb&state=s",
        "https://user@login.xero.com/identity/connect/authorize?response_type=code&client_id=c"
        "&scope=accounting.invoices.read%20offline_access"
        "&redirect_uri=https%3A%2F%2Fr.example%2Fcb&state=s",
        "https://login.xero.com/identity/connect/authorize?response_type=code&client_id=c"
        "&scope=accounting.invoices.read%20offline_access"
        "&redirect_uri=https%3A%2F%2Fr.example%2Fcb&state=s#fragment",
    ],
)
def test_validator_rejects_wrong_scheme_origin_path_userinfo_and_fragment(url):
    with pytest.raises(ValueError):
        validate_authorisation_url(url)


@pytest.mark.parametrize(
    "query",
    [
        "response_type=code&client_id=c&scope=accounting.invoices.read%20offline_access"
        "&redirect_uri=https%3A%2F%2Fr.example%2Fcb",
        "response_type=code&client_id=c&scope=accounting.invoices.read%20offline_access"
        "&redirect_uri=https%3A%2F%2Fr.example%2Fcb&state=",
        "response_type=code&client_id=c&client_id=d"
        "&scope=accounting.invoices.read%20offline_access"
        "&redirect_uri=https%3A%2F%2Fr.example%2Fcb&state=s",
        "response_type=code&client_id=c&scope=accounting.invoices.read%20offline_access"
        "&redirect_uri=https%3A%2F%2Fr.example%2Fcb&state=s&extra=x",
        "response_type=code&client_id=c&scope=accounting.transactions.read%20offline_access"
        "&redirect_uri=https%3A%2F%2Fr.example%2Fcb&state=s",
        "response_type=code&client_id=c&scope=accounting.invoices%20offline_access"
        "&redirect_uri=https%3A%2F%2Fr.example%2Fcb&state=s",
        "response_type=code&client_id=c"
        "&scope=openid%20profile%20accounting.invoices.read%20offline_access"
        "&redirect_uri=https%3A%2F%2Fr.example%2Fcb&state=s",
    ],
)
def test_validator_rejects_bad_parameter_or_scope_shape(query):
    with pytest.raises(ValueError):
        validate_authorisation_url(f"{AUTHORISATION_ENDPOINT}?{query}")


def test_exact_form_bodies_do_not_embed_secrets_in_urls():
    assert code_exchange_body(
        code="synthetic-code", redirect_uri="https://reserved.example/cb"
    ) == {
        "grant_type": "authorization_code",
        "code": "synthetic-code",
        "redirect_uri": "https://reserved.example/cb",
    }
    assert refresh_body(refresh_token="synthetic-refresh") == {
        "grant_type": "refresh_token",
        "refresh_token": "synthetic-refresh",
    }
    assert "synthetic" not in TOKEN_ENDPOINT


def test_token_response_is_typed_rotated_and_repr_redacted():
    parsed = parse_token_response(token())
    assert parsed.refresh_token == "synthetic-rotated-refresh"
    assert parsed.expires_in == 1800
    assert "synthetic" not in repr(parsed)


@pytest.mark.parametrize(
    "change",
    [
        {"access_token": ""}, {"refresh_token": " "}, {"token_type": "bearer"},
        {"expires_in": 0}, {"expires_in": True}, {"expires_in": 1800.0},
    ],
)
def test_token_response_fails_closed_on_invalid_documented_fields(change):
    with pytest.raises(ValueError):
        parse_token_response(token(**change))


def test_connections_are_immutable_typed_and_preserve_id_boundary_without_raw_payload():
    raw = [connection()]
    parsed = parse_connections(raw)
    raw[0]["tenantId"] = "mutated"
    assert parsed[0].connection_id == "connection-1"
    assert parsed[0].tenant_id == "tenant-1"
    assert parsed[0].tenant_name is None
    assert not hasattr(parsed[0], "raw_payload")
    with pytest.raises(FrozenInstanceError):
        parsed[0].tenant_id = "other"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [connection(tenantType="PRACTICEMANAGER")],
        [connection(tenantType="PRACTICE")],
        [connection(tenantName=7)],
        [connection(tenantName="")],
        [connection(tenantName=" \t")],
        [connection(id="")],
        [connection(createdDateUtc=3)],
        [{key: value for key, value in connection().items() if key != "tenantId"}],
        [connection(), connection(id="connection-1", tenantId="tenant-2")],
        [connection(), connection(id="connection-2")],
    ],
)
def test_connections_fail_closed_on_wrong_shape_type_missing_fields_and_duplicates(payload):
    with pytest.raises(ValueError):
        parse_connections(payload)


def test_explicit_event_can_return_all_organisation_connections_for_caller_selection():
    parsed = parse_connections([
        connection(),
        connection(id="connection-2", tenantId="tenant-2", tenantName="Second"),
        connection(id="connection-3", authEventId="event-2", tenantId="tenant-3"),
    ])
    matches = match_organisation_connections(parsed, expected_auth_event_id="event-1")
    assert tuple(item.tenant_id for item in matches) == ("tenant-1", "tenant-2")


def test_explicit_event_and_tenant_select_exactly_one_without_first_item_default():
    parsed = parse_connections([
        connection(),
        connection(id="connection-2", tenantId="tenant-2"),
    ])
    selected = match_organisation_connections(
        parsed, expected_auth_event_id="event-1", expected_tenant_id="tenant-2"
    )
    assert selected[0].connection_id == "connection-2"
    assert selected[0].tenant_id == "tenant-2"


@pytest.mark.parametrize(
    "event, tenant",
    [("wrong-event", None), ("event-1", "wrong-tenant"), ("", "tenant-1")],
)
def test_matching_rejects_wrong_or_blank_event_and_wrong_tenant(event, tenant):
    parsed = parse_connections([connection()])
    with pytest.raises(ValueError):
        match_organisation_connections(
            parsed, expected_auth_event_id=event, expected_tenant_id=tenant
        )


def test_module_is_network_inert_and_has_no_credentials_or_enablement():
    import reserved.providers.accounting.xero_oauth_contract as contract

    for name in ("requests", "httpx", "urllib3", "socket", "os", "environ", "XeroProvider"):
        assert not hasattr(contract, name)
