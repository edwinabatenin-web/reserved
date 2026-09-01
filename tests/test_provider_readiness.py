from reserved.providers.oauth_security import OAuthStateStore
from reserved.providers.readiness import PROVIDERS, ReadinessState, assess_provider


def spec(name):
    return next(item for item in PROVIDERS if item.name == name)


def configured(name):
    item = spec(name)
    values = {variable: "synthetic-not-a-secret" for variable in item.credential_variables}
    values[item.environment_variable] = "sandbox"
    values[item.callback_variable] = f"https://sandbox.reserved.example/oauth/{name}/callback"
    return values


def test_all_five_provider_specs_distinguish_configuration_from_implementation():
    for item in PROVIDERS:
        result = assess_provider(item, configured(item.name))
        assert result.state is ReadinessState.CONFIGURED_NOT_IMPLEMENTED
        assert not result.may_make_sandbox_calls
        assert result.missing_variables == ()


def test_explicitly_enabled_synthetic_adapter_can_reach_ready_state():
    original = spec("xero")
    synthetic_implemented = type(original)(
        original.name,
        original.credential_variables,
        original.environment_variable,
        original.callback_variable,
        implementation_enabled=True,
    )
    result = assess_provider(synthetic_implemented, configured("xero"))
    assert result.state is ReadinessState.READY_FOR_SANDBOX_TEST
    assert result.may_make_sandbox_calls


def test_partial_credentials_fail_closed_without_returning_values():
    item = spec("freeagent")
    environment = {item.credential_variables[0]: "do-not-leak-this"}
    result = assess_provider(item, environment)
    assert result.state is ReadinessState.INCOMPLETE
    assert "do-not-leak-this" not in repr(result)


def test_missing_environment_cannot_default_to_sandbox():
    item = spec("hmrc")
    environment = configured("hmrc")
    environment.pop(item.environment_variable)
    result = assess_provider(item, environment)
    assert result.state is ReadinessState.BLOCKED_UNSAFE_ENVIRONMENT


def test_production_environment_is_blocked_by_readiness_harness():
    item = spec("quickbooks")
    environment = configured("quickbooks")
    environment[item.environment_variable] = "production"
    assert assess_provider(item, environment).state is ReadinessState.BLOCKED_UNSAFE_ENVIRONMENT


def test_insecure_non_local_callback_is_rejected():
    item = spec("xero")
    environment = configured("xero")
    environment[item.callback_variable] = "http://reserved.example/callback"
    assert assess_provider(item, environment).state is ReadinessState.INCOMPLETE


def assert_hostile_callback_is_rejected_without_echo(provider, value):
    item = spec(provider)
    environment = configured(provider)
    environment[item.callback_variable] = value
    result = assess_provider(item, environment)
    assert result.state is ReadinessState.INCOMPLETE
    assert value not in repr(result)
    assert all(value not in message for message in result.messages)


def test_fragments_are_rejected_for_xero_and_quickbooks_without_echoing():
    for provider in ("xero", "quickbooks"):
        for suffix in ("#access-token", "#"):
            assert_hostile_callback_is_rejected_without_echo(
                provider,
                f"https://reserved.example/callback{suffix}",
            )


def test_ascii_controls_anywhere_in_callback_are_rejected_without_echoing():
    hostile_values = (
        "https://reserved.example/call\nback",
        "https://reserved.example/callback?code=line\nfeed",
        "https://reserved.example/call\rback",
        "https://reserved.example/callback?code=carriage\rreturn",
        "https://reserved.example/call\tback",
        "https://reserved.example/callback?code=horizontal\ttab",
        "https://reserved.example/\x00callback",
        "https://reserved.example/callback?code=escape\x1b",
        "https://user\x07@reserved.example/callback",
        "https://reserved.example\x7f/callback",
    )
    for provider in ("xero", "quickbooks"):
        for value in hostile_values:
            assert_hostile_callback_is_rejected_without_echo(provider, value)


def test_unicode_whitespace_and_controls_are_rejected_without_echoing():
    hostile_values = (
        "https://reserved.example/call\u00a0back",
        "https://reserved.example/callback?code=thin\u2009space",
        "https://reserved.example/callback?code=next\u0085line",
        "https://reserved.example/call\u200bback",
        "https://reserved.example/callback?code=direction\u202eoverride",
    )
    for provider in ("xero", "quickbooks"):
        for value in hostile_values:
            assert_hostile_callback_is_rejected_without_echo(provider, value)


def test_all_unicode_other_categories_are_rejected_without_echoing():
    hostile_values = (
        "https://reserved.example/callback?code=surrogate\ud800",
        "https://reserved.example/callback?code=private\ue000use",
        "https://reserved.example/callback?code=unassigned\u0378",
        "https://reserved.example/callback?code=control\u009f",
    )
    for provider in ("xero", "quickbooks"):
        for value in hostile_values:
            assert_hostile_callback_is_rejected_without_echo(provider, value)


def test_raw_backslashes_are_rejected_without_echoing():
    hostile_values = (
        "https://\\reserved.example/callback",
        "https://reserved.example\\callback",
        "https://reserved.example/call\\back",
        "https://reserved.example/callback?next=\\attacker.example",
        "https:\\//reserved.example/callback",
        "https:/\\reserved.example/callback",
        "https://reserved.example\\@attacker.example/callback",
    )
    for provider in ("xero", "quickbooks"):
        for value in hostile_values:
            assert_hostile_callback_is_rejected_without_echo(provider, value)


def test_malformed_ipv6_callback_fails_closed_without_raising():
    item = spec("xero")
    for value in ("http://[::1", "https://[::1"):
        environment = configured("xero")
        environment[item.callback_variable] = value
        result = assess_provider(item, environment)
        assert result.state is ReadinessState.INCOMPLETE
        assert value not in repr(result)


def test_credential_bearing_https_callback_is_rejected():
    item = spec("xero")
    for value in (
        "https://user:secret@reserved.example/callback",
        "https://token@reserved.example/callback",
        "https://:@reserved.example/callback",
    ):
        environment = configured("xero")
        environment[item.callback_variable] = value
        result = assess_provider(item, environment)
        assert result.state is ReadinessState.INCOMPLETE
        assert value not in repr(result)


def test_missing_host_https_callback_is_rejected():
    item = spec("xero")
    for value in ("https://:443/path", "https:///path", "https://", "https://user@"):
        environment = configured("xero")
        environment[item.callback_variable] = value
        assert assess_provider(item, environment).state is ReadinessState.INCOMPLETE


def test_dot_only_and_whitespace_https_callback_hostnames_are_rejected():
    item = spec("xero")
    for value in (
        "https://.",
        "https://../callback",
        "https://.../callback",
        "https://a b/callback",
    ):
        environment = configured("xero")
        environment[item.callback_variable] = value
        result = assess_provider(item, environment)
        assert result.state is ReadinessState.INCOMPLETE
        assert value not in repr(result)


def test_invalid_and_explicitly_empty_ports_are_rejected_without_echoing():
    for value in (
        "https://reserved.example:/callback",
        "http://localhost:/callback",
        "https://reserved.example:invalid/callback",
        "https://reserved.example:99999/callback",
        "http://localhost:invalid/callback",
        "http://localhost:65536/callback",
    ):
        for provider in ("xero", "quickbooks"):
            assert_hostile_callback_is_rejected_without_echo(provider, value)


def test_explicit_port_zero_is_rejected_without_echoing():
    for value in (
        "https://reserved.example:0/callback",
        "http://localhost:0/callback",
        "http://127.0.0.1:0/callback",
    ):
        for provider in ("xero", "quickbooks"):
            assert_hostile_callback_is_rejected_without_echo(provider, value)


def test_malformed_percent_escapes_are_rejected_without_echoing():
    hostile_values = (
        "https://reserved.example/callback%",
        "https://reserved.example/callback%A",
        "https://reserved.example/callback%GG",
        "https://reserved.example/callback?code=%0Z",
    )
    for provider in ("xero", "quickbooks"):
        for value in hostile_values:
            assert_hostile_callback_is_rejected_without_echo(provider, value)


def test_percent_encoded_authority_values_are_rejected_without_echoing():
    hostile_values = (
        "https://reserved%2eexample/callback",
        "https://reserved.example%3a443/callback",
        "https://user%40reserved.example/callback",
        "https://reserved.example%5c@attacker.example/callback",
    )
    for provider in ("xero", "quickbooks"):
        for value in hostile_values:
            assert_hostile_callback_is_rejected_without_echo(provider, value)


def test_percent_encoded_c0_and_del_controls_are_rejected_without_echoing():
    hostile_values = (
        "https://reserved.example/%00callback",
        "https://reserved.example/callback?code=%1f",
        "https://reserved.example/callback?code=%7F",
    )
    for provider in ("xero", "quickbooks"):
        for value in hostile_values:
            assert_hostile_callback_is_rejected_without_echo(provider, value)


def test_safe_ordinary_percent_encoding_is_preserved():
    for provider in ("xero", "quickbooks"):
        item = spec(provider)
        environment = configured(provider)
        environment[item.callback_variable] = (
            "https://reserved.example/oauth/callback%20path?state=hello%2Dworld"
        )
        assert assess_provider(item, environment).state is ReadinessState.CONFIGURED_NOT_IMPLEMENTED


def test_valid_https_callback_is_preserved():
    item = spec("xero")
    for value in (
        "https://sandbox.reserved.example/oauth/xero/callback",
        "https://reserved.example:8443/callback",
    ):
        environment = configured("xero")
        environment[item.callback_variable] = value
        assert assess_provider(item, environment).state is ReadinessState.CONFIGURED_NOT_IMPLEMENTED


def test_http_loopback_hosts_are_preserved():
    item = spec("xero")
    for value in (
        "http://localhost/callback",
        "http://localhost:8000/callback",
        "http://127.0.0.1/callback",
        "http://127.0.0.1:8080/callback",
    ):
        environment = configured("xero")
        environment[item.callback_variable] = value
        assert assess_provider(item, environment).state is ReadinessState.CONFIGURED_NOT_IMPLEMENTED


def test_oauth_state_is_provider_bound_single_use_and_not_stored_raw():
    session = {}
    store = OAuthStateStore(session, ttl_seconds=60)
    state = store.issue("xero", now=100)
    assert state not in repr(session)
    assert not store.consume("freeagent", state, now=110)
    assert store.consume("xero", state, now=110)
    assert not store.consume("xero", state, now=110)


def test_failed_oauth_state_attempt_consumes_token():
    session = {}
    store = OAuthStateStore(session, ttl_seconds=60)
    state = store.issue("hmrc", now=100)
    assert not store.consume("hmrc", "wrong", now=101)
    assert not store.consume("hmrc", state, now=102)


def test_expired_oauth_state_is_rejected():
    session = {}
    store = OAuthStateStore(session, ttl_seconds=60)
    state = store.issue("quickbooks", now=100)
    assert not store.consume("quickbooks", state, now=161)
