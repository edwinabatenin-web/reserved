"""Focused tests for the corrected, network-inert Yapily AIS Y1 contract."""

import ast
from dataclasses import FrozenInstanceError
import inspect

import pytest

from reserved.providers.banking import yapily_hosted_consent_contract as contract


def request(**changes):
    value = {
        "applicationUserId": "reserved-user-123",
        "institutionIdentifiers": {"institutionCountryCode": "GB"},
        "userSettings": {"language": "en", "location": "GB"},
        "redirectUrl": "https://reserved.example/banking/return?state=opaque",
        "accountRequest": {"featureScope": ["ACCOUNTS", "ACCOUNT_TRANSACTIONS"]},
    }
    value.update(changes)
    return value


def test_minimal_request_has_exact_documented_nesting_and_settings():
    parsed = contract.parse_request_payload(request())
    assert parsed.payload() == request()
    assert parsed.payload()["accountRequest"]["featureScope"] == [
        "ACCOUNTS", "ACCOUNT_TRANSACTIONS"
    ]
    assert parsed.payload()["userSettings"] == {"language": "en", "location": "GB"}


def test_application_user_identity_is_stable_immutable_and_not_provider_user():
    identity = contract.parse_request_payload(request()).application_user
    assert identity.value == "reserved-user-123"
    with pytest.raises(FrozenInstanceError):
        identity.value = "provider-user"  # type: ignore[misc]


def test_optional_institution_id_is_a_restriction_inside_documented_object():
    payload = request(institutionIdentifiers={
        "institutionCountryCode": "GB", "institutionId": "modelo-sandbox"
    })
    assert contract.parse_request_payload(payload).payload() == payload


@pytest.mark.parametrize("value", [
    ["modelo-sandbox"], {}, {"institutionId": "modelo-sandbox"},
    {"institutionCountryCode": "US"},
    {"institutionCountryCode": "GB", "institutionId": ""},
    {"institutionCountryCode": "GB", "institutionId": "one", "extra": True},
])
def test_bad_institution_objects_and_non_gb_fail_closed(value):
    with pytest.raises(contract.YapilyHostedConsentContractError):
        contract.parse_request_payload(request(institutionIdentifiers=value))


def test_former_wrong_wire_shapes_are_rejected():
    top_level_scope = request()
    top_level_scope["featureScope"] = top_level_scope.pop("accountRequest")["featureScope"]
    wrong_location = request(userSettings={"language": "en", "location": {"country": "GB"}})
    list_institutions = request(institutionIdentifiers=["modelo-sandbox"])
    for payload in (top_level_scope, wrong_location, list_institutions):
        with pytest.raises(contract.YapilyHostedConsentContractError):
            contract.parse_request_payload(payload)


@pytest.mark.parametrize("scope", [
    [], ["ACCOUNTS"], ["ACCOUNT_TRANSACTIONS", "ACCOUNTS"],
    ["ACCOUNTS", "ACCOUNT_BALANCES", "ACCOUNT_TRANSACTIONS"],
    ["ACCOUNTS", "PAYMENTS"], ("ACCOUNTS", "ACCOUNT_TRANSACTIONS"), True,
])
def test_only_exact_nested_account_transaction_scope_is_accepted(scope):
    with pytest.raises(contract.YapilyHostedConsentContractError):
        contract.parse_request_payload(request(accountRequest={"featureScope": scope}))


def test_missing_extra_and_malformed_request_fields_fail_closed():
    for payload in (None, [], {}, {**request(), "secret": "x"}):
        with pytest.raises(contract.YapilyHostedConsentContractError):
            contract.parse_request_payload(payload)
    for field in request():
        payload = request()
        del payload[field]
        with pytest.raises(contract.YapilyHostedConsentContractError):
            contract.parse_request_payload(payload)
    with pytest.raises(contract.YapilyHostedConsentContractError):
        contract.parse_request_payload(request(accountRequest={
            "featureScope": list(contract.FEATURE_SCOPE), "extra": True
        }))


@pytest.mark.parametrize("settings", [
    {"language": "EN", "location": "GB"}, {"language": "en", "location": "US"},
    {"language": "en", "location": "GB "}, {"location": "GB"},
    {"language": "en", "location": "GB", "extra": True},
])
def test_user_settings_must_be_deterministic_documented_shape(settings):
    with pytest.raises(contract.YapilyHostedConsentContractError):
        contract.parse_request_payload(request(userSettings=settings))


@pytest.mark.parametrize("bad", [
    "", " value", "value ", "value with space", "value\n", "val\x00ue", "\tvalue", True, 12,
])
def test_identifiers_reject_whitespace_controls_and_coercion(bad):
    with pytest.raises(contract.YapilyHostedConsentContractError):
        contract.ApplicationUserIdentity(bad)
    with pytest.raises(contract.YapilyHostedConsentContractError):
        contract.hosted_consent_status_path(bad)


def test_identifier_and_url_lengths_are_bounded():
    with pytest.raises(contract.YapilyHostedConsentContractError):
        contract.ApplicationUserIdentity("x" * 129)
    with pytest.raises(contract.YapilyHostedConsentContractError):
        contract.parse_request_payload(request(redirectUrl="https://example.test/" + "x" * 2049))


@pytest.mark.parametrize("bad", [
    "http://reserved.example/return", "//reserved.example/return", "/return",
    "https:///return", "https://user:pass@reserved.example/return",
    "https://reserved.example/return#token", "https://reserved.example:bad/return",
    "https://reserved.example:/return", "https://reserved.example:70000/return",
    " https://reserved.example/return", "https://reserved.example/return\n",
    "https://reserved.example/a b", "https://reserved.example/a\\b",
])
def test_url_validation_fails_closed(bad):
    with pytest.raises(contract.YapilyHostedConsentContractError):
        contract.parse_request_payload(request(redirectUrl=bad))


def test_get_path_uses_consent_request_id_and_rejects_path_confusion():
    assert contract.hosted_consent_status_path("request-1") == "/hosted/consent-requests/request-1"
    for value in ("a/b", "a?b", "a#b", "a%2Fb", "a\\b", "a b", "å"):
        with pytest.raises(contract.YapilyHostedConsentContractError):
            contract.hosted_consent_status_path(value)


def test_no_provider_response_parser_is_exposed():
    assert not hasattr(contract, "HostedConsentCreated")
    assert not hasattr(contract, "HostedConsentStatusResponse")


def test_no_network_environment_credentials_or_payment_names():
    tree = ast.parse(inspect.getsource(contract).lower())
    imports = {
        alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attributes = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert not ({"requests", "httpx", "urllib.request", "socket", "os"} & imports)
    forbidden = {
        "environ", "application_secret", "consent_token", "access_token", "auth_token",
        "refresh_token", "webhook", "payment", "bulk", "vrp", "sweeping", "same_owner",
    }
    assert not forbidden.intersection(names | attributes)
