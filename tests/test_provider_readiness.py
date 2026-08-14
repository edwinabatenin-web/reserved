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
