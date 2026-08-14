"""Synthetic, endpoint-free checks for OAuth callback and token custody."""

from reserved.providers.oauth_contracts import (
    CallbackStatus,
    CredentialReference,
    OAuthContractError,
    OAuthTokenSet,
    exchange_and_store,
    refresh_and_rotate,
    validate_callback,
)
from reserved.providers.oauth_security import OAuthStateStore


class SyntheticExchanger:
    def __init__(self):
        self.codes = []

    def exchange(self, code, redirect_uri):
        self.codes.append((code, redirect_uri))
        return OAuthTokenSet("synthetic-access-token", "synthetic-refresh-token", 3600)


class RecordingTokenStore:
    def __init__(self):
        self.puts = []
        self.replacements = []
        self.deletes = []

    def put(self, *, provider, user_id, tokens):
        self.puts.append((provider, user_id, tokens))
        return CredentialReference(provider, "credential-reference-001")

    def replace(self, *, credential, tokens):
        self.replacements.append((credential, tokens))

    def delete(self, credential):
        self.deletes.append(credential)


class SyntheticRefresher:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.references = []

    def refresh(self, credential):
        self.references.append(credential)
        if self.error:
            raise self.error
        return self.result


def issue(provider="xero"):
    session = {}
    store = OAuthStateStore(session, ttl_seconds=60)
    return store, store.issue(provider, now=100)


def test_state_is_validated_before_code_is_exposed():
    store, state = issue()
    result = validate_callback(
        provider="xero", parameters={"state": state, "code": "synthetic-code"},
        state_store=store, now=101,
    )
    assert result.status is CallbackStatus.AUTHORISED
    assert "synthetic-code" not in repr(result)
    assert result.code.consume() == "synthetic-code"


def test_invalid_state_never_exposes_or_echoes_code():
    store, _ = issue()
    secret_code = "secret-callback-code"
    try:
        validate_callback(
            provider="xero", parameters={"state": "wrong", "code": secret_code},
            state_store=store, now=101,
        )
    except OAuthContractError as exc:
        assert secret_code not in str(exc)
    else:
        raise AssertionError("Invalid state must fail")


def test_provider_denial_consumes_state_and_discards_description():
    store, state = issue("freeagent")
    sensitive = "provider detail must not be retained"
    result = validate_callback(
        provider="freeagent",
        parameters={"state": state, "error": "access_denied", "error_description": sensitive},
        state_store=store, now=101,
    )
    assert result.status is CallbackStatus.DENIED
    assert result.code is None
    assert sensitive not in repr(result)
    try:
        validate_callback(
            provider="freeagent", parameters={"state": state, "code": "second"},
            state_store=store, now=102,
        )
    except OAuthContractError:
        pass
    else:
        raise AssertionError("Denied callback state must not be replayable")


def test_missing_code_after_valid_state_fails_without_replay_window():
    store, state = issue("hmrc")
    try:
        validate_callback(
            provider="hmrc", parameters={"state": state}, state_store=store, now=101,
        )
    except OAuthContractError:
        pass
    else:
        raise AssertionError("Missing code must fail")
    try:
        validate_callback(
            provider="hmrc", parameters={"state": state, "code": "late"},
            state_store=store, now=102,
        )
    except OAuthContractError:
        pass
    else:
        raise AssertionError("State must already be consumed")


def test_exchange_is_single_use_and_only_reference_returns_to_caller():
    store, state = issue("quickbooks")
    callback = validate_callback(
        provider="quickbooks", parameters={"state": state, "code": "synthetic-code"},
        state_store=store, now=101,
    )
    exchanger = SyntheticExchanger()
    token_store = RecordingTokenStore()
    credential = exchange_and_store(
        provider="quickbooks", user_id="synthetic-user", redirect_uri="https://reserved.example/callback",
        code=callback.code, exchanger=exchanger, token_store=token_store,
    )
    assert credential == CredentialReference("quickbooks", "credential-reference-001")
    assert "synthetic-access-token" not in repr(credential)
    assert "synthetic-access-token" not in repr(token_store.puts[0][2])
    try:
        exchange_and_store(
            provider="quickbooks", user_id="synthetic-user", redirect_uri="https://reserved.example/callback",
            code=callback.code, exchanger=exchanger, token_store=token_store,
        )
    except OAuthContractError:
        pass
    else:
        raise AssertionError("Code must not be exchangeable twice")
    assert len(exchanger.codes) == 1


def test_token_set_rejects_missing_access_token_and_invalid_expiry():
    for args in (("", None, 3600), ("synthetic", None, 0)):
        try:
            OAuthTokenSet(*args)
        except OAuthContractError:
            pass
        else:
            raise AssertionError("Invalid token response must fail closed")


def test_refresh_rotation_replaces_complete_token_set_without_delete():
    credential = CredentialReference("xero", "opaque-reference")
    rotated = OAuthTokenSet("new-access", "new-refresh", 1800)
    refresher = SyntheticRefresher(result=rotated)
    store = RecordingTokenStore()
    refresh_and_rotate(credential=credential, refresher=refresher, token_store=store)
    assert refresher.references == [credential]
    assert store.replacements == [(credential, rotated)]
    assert store.deletes == []
    assert "new-access" not in repr(store.replacements[0][1])
    assert "new-refresh" not in repr(store.replacements[0][1])


def test_refresh_failure_preserves_current_reference_and_never_replaces():
    credential = CredentialReference("quickbooks", "opaque-reference")
    refresher = SyntheticRefresher(error=RuntimeError("synthetic provider unavailable"))
    store = RecordingTokenStore()
    try:
        refresh_and_rotate(credential=credential, refresher=refresher, token_store=store)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Refresh failure must propagate")
    assert store.replacements == []
    assert store.deletes == []


def test_refresh_rejects_untyped_provider_payload_before_storage():
    credential = CredentialReference("freeagent", "opaque-reference")
    refresher = SyntheticRefresher(result={"access_token": "must-not-be-stored"})
    store = RecordingTokenStore()
    try:
        refresh_and_rotate(credential=credential, refresher=refresher, token_store=store)
    except OAuthContractError as exc:
        assert "must-not-be-stored" not in str(exc)
    else:
        raise AssertionError("Untyped provider response must be rejected")
    assert store.replacements == []
    assert store.deletes == []
