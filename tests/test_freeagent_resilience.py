"""Synthetic, network-free FreeAgent resilience/state-contract tests."""

import inspect

import pytest

from reserved.providers.accounting.freeagent_invoice_contract import (
    FreeAgentPagination,
    validate_pagination,
)
from reserved.providers.accounting.freeagent_oauth_contract import FreeAgentTokenSet
from reserved.providers.accounting.freeagent_resilience import (
    DEFAULT_MAX_PAGES,
    DEFAULT_MAX_WAIT_SECONDS,
    DISCONNECT_IS_LOCAL_ONLY,
    OLD_REFERENCE_IDENTITY_LENGTH,
    OLD_REFERENCE_NAMESPACE,
    RATE_LIMIT_TOKEN_REFRESHES_PER_MINUTE,
    RATE_LIMIT_USER_REQUESTS_PER_HOUR,
    RATE_LIMIT_USER_REQUESTS_PER_MINUTE,
    ConnectionEvent,
    ConnectionState,
    ErrorClass,
    ErrorDisposition,
    FreeAgentResilienceError,
    PaginationAction,
    RateLimitAction,
    RefreshAction,
    RefreshRotationDecision,
    classify_connection_state,
    classify_provider_error,
    decide_pagination,
    decide_rate_limit_retry,
    decide_refresh_rotation,
    transition_connection,
)


def _pagination(*, next_url=None, page=None, per_page=None, total_count=None,
                prev_url=None, first_url=None, last_url=None):
    return FreeAgentPagination(
        page=page,
        per_page=per_page,
        next_url=next_url,
        prev_url=prev_url,
        first_url=first_url,
        last_url=last_url,
        total_count=total_count,
    )


def _tokens(**overrides):
    values = {
        "access_token": "synthetic-access",
        "token_type": "bearer",
        "expires_in": 3600,
        "refresh_token": "synthetic-refresh",
        "refresh_token_expires_in": 631151957,
    }
    values.update(overrides)
    return FreeAgentTokenSet(**values)


NEXT = "https://api.freeagent.com/v2/invoices?page=2&per_page=25"


def _cursor_context(page_number, *, per_page=25):
    assert page_number > 1
    cursors = {
        f"https://api.freeagent.com/v2/invoices?page={page}&per_page={per_page}"
        for page in range(2, page_number + 1)
    }
    return {
        "current_cursor": (
            f"https://api.freeagent.com/v2/invoices?page={page_number}&per_page={per_page}"
        ),
        "seen_cursors": cursors,
    }

OLD_REF = f"{OLD_REFERENCE_NAMESPACE}.0123456789abcdef0123456789abcdef"


# ── Pagination decisions ─────────────────────────────────────────────────────


def test_terminal_pagination_returns_terminal():
    pagination = _pagination(next_url=None, page=1, per_page=25, total_count=25)
    decision = decide_pagination(
        pagination=pagination, page_number=1, fetched_count=25,
    )
    assert decision.action is PaginationAction.TERMINAL
    assert decision.next_url is None


def test_multi_page_pagination_continues_and_preserves_url():
    pagination = _pagination(next_url=NEXT, page=1, per_page=25, total_count=100)
    decision = decide_pagination(
        pagination=pagination, page_number=1, fetched_count=25,
    )
    assert decision.action is PaginationAction.CONTINUE
    assert decision.next_url == NEXT


@pytest.mark.parametrize("url", [
    "https://api.freeagent.com/v2/invoices?page=2",
    "https://api.freeagent.com/v2/invoices?page=2&per_page=100",
    "https://api.freeagent.com/v2/invoices?page=6&per_page=50",
    "https://api.freeagent.com:443/v2/invoices?page=2",
])
def test_next_url_is_preserved_verbatim(url):
    pagination = _pagination(next_url=url, page=1, per_page=25, total_count=100)
    decision = decide_pagination(
        pagination=pagination, page_number=1, fetched_count=25,
    )
    assert decision.next_url == url


def test_pagination_decision_is_deterministic():
    pagination = _pagination(next_url=NEXT, page=1, per_page=25, total_count=100)
    first = decide_pagination(pagination=pagination, page_number=1, fetched_count=25)
    second = decide_pagination(pagination=pagination, page_number=1, fetched_count=25)
    assert first == second


def test_pagination_rejects_repeated_cursor():
    pagination = _pagination(next_url=NEXT, page=2, per_page=25, total_count=100)
    with pytest.raises(FreeAgentResilienceError):
        decide_pagination(
            pagination=pagination,
            page_number=2,
            fetched_count=50,
            current_cursor="https://api.freeagent.com/v2/invoices?page=2&per_page=25",
            seen_cursors={NEXT},
        )


def test_pagination_rejects_cyclic_self_cursor():
    pagination = _pagination(next_url=NEXT, page=2, per_page=25, total_count=100)
    with pytest.raises(FreeAgentResilienceError):
        decide_pagination(
            pagination=pagination,
            page_number=2,
            fetched_count=50,
            current_cursor=NEXT,
            seen_cursors={NEXT},
        )


def test_pagination_rejects_fetched_count_exceeding_total():
    pagination = _pagination(next_url=None, page=1, per_page=25, total_count=10)
    with pytest.raises(FreeAgentResilienceError):
        decide_pagination(pagination=pagination, page_number=1, fetched_count=11)


def test_pagination_rejects_incoherent_terminal_count():
    pagination = _pagination(next_url=None, page=3, per_page=25, total_count=100)
    with pytest.raises(FreeAgentResilienceError):
        decide_pagination(
            pagination=pagination,
            page_number=3,
            fetched_count=75,
            **_cursor_context(3),
        )


def test_pagination_rejects_next_page_after_total_reached():
    pagination = _pagination(next_url=NEXT, page=4, per_page=25, total_count=100)
    with pytest.raises(FreeAgentResilienceError):
        decide_pagination(
            pagination=pagination,
            page_number=4,
            fetched_count=100,
            **_cursor_context(4),
        )


def test_pagination_rejects_page_limit_exceeded():
    pagination = _pagination(next_url=NEXT, page=2, per_page=25, total_count=100)
    with pytest.raises(FreeAgentResilienceError):
        decide_pagination(
            pagination=pagination, page_number=2, fetched_count=50, max_pages=1,
        )


def test_pagination_rejects_page_metadata_contradiction():
    pagination = _pagination(next_url=NEXT, page=7, per_page=25, total_count=100)
    with pytest.raises(FreeAgentResilienceError):
        decide_pagination(pagination=pagination, page_number=2, fetched_count=50)


@pytest.mark.parametrize("bad_url", [
    "http://api.freeagent.com/v2/invoices?page=2",
    "https://evil.example.com/v2/invoices?page=2",
    "https://user:pass@api.freeagent.com/v2/invoices?page=2",
    "https://api.freeagent.com/v2/invoices?page=2#frag",
    "https://api.freeagent.com:8443/v2/invoices?page=2",
    "https://api.freeagent.com/v2/contacts?page=2",
])
def test_pagination_rejects_unsafe_urls_through_validator_boundary(bad_url):
    pagination = _pagination(next_url=bad_url, page=1, per_page=25, total_count=100)
    with pytest.raises(FreeAgentResilienceError):
        decide_pagination(pagination=pagination, page_number=1, fetched_count=25)


def test_pagination_accepts_validated_pagination_from_existing_boundary():
    pagination = validate_pagination(
        page=5,
        per_page=50,
        link_header=(
            '<https://api.freeagent.com/v2/invoices?page=6&per_page=50>; rel="next"'
        ),
        total_count="500",
    )
    decision = decide_pagination(
        pagination=pagination,
        page_number=5,
        fetched_count=250,
        **_cursor_context(5, per_page=50),
    )
    assert decision.action is PaginationAction.CONTINUE
    assert decision.next_url == "https://api.freeagent.com/v2/invoices?page=6&per_page=50"


@pytest.mark.parametrize("kwargs", [
    {"page_number": True},
    {"page_number": 1.0},
    {"page_number": 0},
    {"page_number": "1"},
    {"fetched_count": -1},
    {"fetched_count": True},
    {"fetched_count": 1.0},
    {"fetched_count": "25"},
    {"max_pages": 0},
    {"max_pages": True},
    {"max_pages": 1.0},
    {"max_pages": "2"},
    {"current_cursor": 5},
    {"current_cursor": ""},
    {"seen_cursors": "https://api.freeagent.com/v2/invoices?page=2"},
    {"seen_cursors": {1}},
])
def test_pagination_rejects_malformed_context_types(kwargs):
    pagination = _pagination(next_url=NEXT, page=1, per_page=25, total_count=100)
    base = {
        "pagination": pagination,
        "page_number": 1,
        "fetched_count": 25,
    }
    base.update(kwargs)
    with pytest.raises(FreeAgentResilienceError):
        decide_pagination(**base)


def test_pagination_allows_page_before_maximum():
    pagination = _pagination(next_url=NEXT, page=1, per_page=25, total_count=100)
    decision = decide_pagination(
        pagination=pagination, page_number=1, fetched_count=25, max_pages=2,
    )
    assert decision.action is PaginationAction.CONTINUE
    assert decision.next_url == NEXT


def test_pagination_terminal_at_maximum_without_next():
    pagination = _pagination(next_url=None, page=2, per_page=25, total_count=50)
    decision = decide_pagination(
        pagination=pagination, page_number=2, fetched_count=50, max_pages=2,
        **_cursor_context(2),
    )
    assert decision.action is PaginationAction.TERMINAL
    assert decision.next_url is None


def test_pagination_fails_closed_on_next_claimed_at_maximum():
    pagination = _pagination(next_url=NEXT, page=2, per_page=25, total_count=100)
    with pytest.raises(FreeAgentResilienceError):
        decide_pagination(
            pagination=pagination, page_number=2, fetched_count=50, max_pages=2,
            **_cursor_context(2),
        )


def test_pagination_fails_closed_on_next_claimed_at_maximum_without_total():
    pagination = _pagination(next_url=NEXT, page=2, per_page=25)
    with pytest.raises(FreeAgentResilienceError):
        decide_pagination(
            pagination=pagination, page_number=2, fetched_count=50, max_pages=2,
            **_cursor_context(2),
        )


def test_pagination_accepts_set_tuple_and_list_cursors():
    current = NEXT
    following = "https://api.freeagent.com/v2/invoices?page=3&per_page=25"
    pagination = _pagination(next_url=following, page=2, per_page=25, total_count=100)
    for seen in ({current}, [current], (current,)):
        decision = decide_pagination(
            pagination=pagination,
            page_number=2,
            fetched_count=50,
            current_cursor=current,
            seen_cursors=seen,
        )
        assert decision.action is PaginationAction.CONTINUE


def test_first_page_rejects_cursor_context():
    pagination = _pagination(next_url=NEXT, page=1, per_page=25, total_count=100)
    with pytest.raises(FreeAgentResilienceError):
        decide_pagination(
            pagination=pagination,
            page_number=1,
            fetched_count=25,
            current_cursor=NEXT,
            seen_cursors={NEXT},
        )


def test_later_page_requires_current_cursor_and_coherent_history():
    following = "https://api.freeagent.com/v2/invoices?page=3&per_page=25"
    pagination = _pagination(next_url=following, page=2, per_page=25, total_count=100)
    with pytest.raises(FreeAgentResilienceError):
        decide_pagination(pagination=pagination, page_number=2, fetched_count=50)
    with pytest.raises(FreeAgentResilienceError):
        decide_pagination(
            pagination=pagination,
            page_number=2,
            fetched_count=50,
            current_cursor=NEXT,
            seen_cursors=set(),
        )
    with pytest.raises(FreeAgentResilienceError):
        decide_pagination(
            pagination=pagination,
            page_number=2,
            fetched_count=50,
            current_cursor=NEXT,
            seen_cursors={NEXT, following},
        )


# ── Refresh rotation decisions ───────────────────────────────────────────────


def test_refresh_rotation_decides_atomic_rotation_without_storage():
    decision = decide_refresh_rotation(old_reference=OLD_REF, new=_tokens())
    assert decision.action is RefreshAction.ROTATE
    assert decision.old_reference == OLD_REF
    assert decision.token_type == "bearer"
    assert decision.expires_in == 3600
    assert decision.refresh_token_expires_in == 631151957
    assert decision.stored is False


def test_refresh_decision_never_leaks_token_strings():
    decision = decide_refresh_rotation(old_reference=OLD_REF, new=_tokens())
    for secret in ("synthetic-access", "synthetic-refresh"):
        assert secret not in repr(decision)
        assert secret not in str(decision)


def test_refresh_error_never_leaks_token_strings():
    bad = _tokens(expires_in=0)
    with pytest.raises(FreeAgentResilienceError) as exc:
        decide_refresh_rotation(old_reference=OLD_REF, new=bad)
    for secret in ("synthetic-access", "synthetic-refresh"):
        assert secret not in str(exc.value)


def test_refresh_rotation_requires_complete_valid_token_set():
    with pytest.raises(FreeAgentResilienceError):
        decide_refresh_rotation(old_reference=OLD_REF, new="not-a-token-set")
    with pytest.raises(FreeAgentResilienceError):
        decide_refresh_rotation(old_reference=OLD_REF, new=_tokens(token_type="Bearer"))
    with pytest.raises(FreeAgentResilienceError):
        decide_refresh_rotation(old_reference=OLD_REF, new=_tokens(access_token=""))
    with pytest.raises(FreeAgentResilienceError):
        decide_refresh_rotation(old_reference=OLD_REF, new=_tokens(refresh_token=""))
    with pytest.raises(FreeAgentResilienceError):
        decide_refresh_rotation(old_reference=OLD_REF, new=_tokens(expires_in="3600"))
    with pytest.raises(FreeAgentResilienceError):
        decide_refresh_rotation(old_reference=OLD_REF, new=_tokens(expires_in=True))


@pytest.mark.parametrize("bad_reference", [
    "",
    "   ",
    "opaque-ref",
    "old-reference-123",
    "FreeAgent Refresh Reference 123",
    "synthetic-access",
    "synthetic-refresh",
    "freeagent.ref.ABCDEF0123456789ABCDEF0123456789",
    "freeagent.ref.0123456789abcdef0123456789abcde",
    "freeagent.ref.0123456789abcdef0123456789abcdef0",
    "freeagent.ref.0123456789abcdef0123456789abcdeg",
    "other.ref.0123456789abcdef0123456789abcdef",
    "freeagent.ref-0123456789abcdef0123456789abcdef",
    "freeagent.ref.0123456789abcdef0123456789abcdef ",
])
def test_refresh_rotation_rejects_invalid_old_reference(bad_reference):
    with pytest.raises(FreeAgentResilienceError):
        decide_refresh_rotation(old_reference=bad_reference, new=_tokens())


def test_refresh_rotation_rejects_non_string_old_reference():
    for bad in (None, 123, True, ["freeagent.ref.0123456789abcdef0123456789abcdef"]):
        with pytest.raises(FreeAgentResilienceError):
            decide_refresh_rotation(old_reference=bad, new=_tokens())


def test_refresh_error_never_echoes_rejected_old_reference():
    for bad in ("synthetic-access", "synthetic-refresh", "opaque-ref"):
        with pytest.raises(FreeAgentResilienceError) as exc:
            decide_refresh_rotation(old_reference=bad, new=_tokens())
        assert bad not in str(exc.value)
        assert bad not in repr(exc.value)


# ── Connection-state model ───────────────────────────────────────────────────


@pytest.mark.parametrize("valid,refresh,disconnected,expected", [
    (True, True, False, ConnectionState.CONNECTED),
    (False, True, False, ConnectionState.REFRESH_REQUIRED),
    (False, False, False, ConnectionState.REAUTHORISATION_REQUIRED),
    (True, False, False, ConnectionState.REAUTHORISATION_REQUIRED),
    (False, True, True, ConnectionState.LOCAL_DISCONNECTED),
    (True, True, True, ConnectionState.LOCAL_DISCONNECTED),
])
def test_connection_classification(valid, refresh, disconnected, expected):
    assert classify_connection_state(
        access_token_valid=valid,
        refresh_token_valid=refresh,
        locally_disconnected=disconnected,
    ) is expected


@pytest.mark.parametrize("kwargs", [
    {"access_token_valid": 1},
    {"refresh_token_valid": 0},
    {"locally_disconnected": None},
])
def test_connection_classification_rejects_non_booleans(kwargs):
    base = {"access_token_valid": True, "refresh_token_valid": True}
    base.update(kwargs)
    with pytest.raises(FreeAgentResilienceError):
        classify_connection_state(**base)


@pytest.mark.parametrize("current,event,expected", [
    (ConnectionState.CONNECTED, ConnectionEvent.ACCESS_TOKEN_EXPIRED, ConnectionState.REFRESH_REQUIRED),
    (ConnectionState.CONNECTED, ConnectionEvent.REFRESH_TOKEN_EXPIRED, ConnectionState.REAUTHORISATION_REQUIRED),
    (ConnectionState.CONNECTED, ConnectionEvent.LOCAL_DISCONNECT, ConnectionState.LOCAL_DISCONNECTED),
    (ConnectionState.REFRESH_REQUIRED, ConnectionEvent.REFRESH_TOKEN_EXPIRED, ConnectionState.REAUTHORISATION_REQUIRED),
    (ConnectionState.REFRESH_REQUIRED, ConnectionEvent.LOCAL_DISCONNECT, ConnectionState.LOCAL_DISCONNECTED),
    (ConnectionState.REAUTHORISATION_REQUIRED, ConnectionEvent.LOCAL_DISCONNECT, ConnectionState.LOCAL_DISCONNECTED),
    (ConnectionState.LOCAL_DISCONNECTED, ConnectionEvent.LOCAL_DISCONNECT, ConnectionState.LOCAL_DISCONNECTED),
])
def test_valid_connection_transitions(current, event, expected):
    assert transition_connection(current, event) is expected


def test_complete_validated_rotation_restores_connected():
    assert transition_connection(
        ConnectionState.REFRESH_REQUIRED,
        ConnectionEvent.TOKEN_SET_ROTATED,
        refresh_token_set=_tokens(),
        old_reference=OLD_REF,
    ) is ConnectionState.CONNECTED


def test_rotation_event_without_complete_decision_fails_closed():
    with pytest.raises(FreeAgentResilienceError):
        transition_connection(
            ConnectionState.REFRESH_REQUIRED,
            ConnectionEvent.TOKEN_SET_ROTATED,
        )


def test_caller_constructed_rotation_summary_cannot_restore_connected():
    forged = RefreshRotationDecision(
        action=RefreshAction.ROTATE,
        old_reference=OLD_REF,
        token_type="bearer",
        expires_in=1,
        refresh_token_expires_in=1,
    )
    with pytest.raises(FreeAgentResilienceError):
        transition_connection(
            ConnectionState.REFRESH_REQUIRED,
            ConnectionEvent.TOKEN_SET_ROTATED,
            refresh_token_set=forged,
            old_reference=OLD_REF,
        )


def test_refresh_inputs_are_rejected_for_non_rotation_events():
    with pytest.raises(FreeAgentResilienceError):
        transition_connection(
            ConnectionState.CONNECTED,
            ConnectionEvent.LOCAL_DISCONNECT,
            refresh_token_set=_tokens(),
            old_reference=OLD_REF,
        )


@pytest.mark.parametrize("current,event", [
    (ConnectionState.CONNECTED, ConnectionEvent.TOKEN_SET_ROTATED),
    (ConnectionState.LOCAL_DISCONNECTED, ConnectionEvent.TOKEN_SET_ROTATED),
    (ConnectionState.LOCAL_DISCONNECTED, ConnectionEvent.ACCESS_TOKEN_EXPIRED),
    (ConnectionState.REAUTHORISATION_REQUIRED, ConnectionEvent.TOKEN_SET_ROTATED),
    (ConnectionState.REAUTHORISATION_REQUIRED, ConnectionEvent.REFRESH_TOKEN_EXPIRED),
])
def test_invalid_connection_transitions_fail_closed(current, event):
    with pytest.raises(FreeAgentResilienceError):
        transition_connection(current, event)


def test_transition_rejects_non_enum_inputs():
    with pytest.raises(FreeAgentResilienceError):
        transition_connection("connected", ConnectionEvent.LOCAL_DISCONNECT)
    with pytest.raises(FreeAgentResilienceError):
        transition_connection(ConnectionState.CONNECTED, "local_disconnect")


def test_disconnect_is_local_only_and_never_claims_revocation():
    assert DISCONNECT_IS_LOCAL_ONLY is True
    import reserved.providers.accounting.freeagent_resilience as mod
    public = [name for name in dir(mod) if not name.startswith("_")]
    assert not any("revoke" in name.lower() for name in public)


# ── Rate-limit handling ──────────────────────────────────────────────────────


def test_documented_rate_limit_constants_are_retained():
    assert RATE_LIMIT_USER_REQUESTS_PER_MINUTE == 120
    assert RATE_LIMIT_USER_REQUESTS_PER_HOUR == 3600
    assert RATE_LIMIT_TOKEN_REFRESHES_PER_MINUTE == 15


def test_rate_limit_decision_is_bounded_and_does_not_sleep():
    decision = decide_rate_limit_retry(status_code=429, retry_after="60")
    assert decision.action is RateLimitAction.WAIT_AND_RETRY
    assert decision.retry_after_seconds == 60


@pytest.mark.parametrize("retry_after,expected", [
    ("0", 0),
    (0, 0),
    ("1", 1),
    (1, 1),
    ("300", 300),
    (300, 300),
])
def test_rate_limit_accepts_integer_boundaries(retry_after, expected):
    decision = decide_rate_limit_retry(status_code=429, retry_after=retry_after)
    assert decision.retry_after_seconds == expected


def test_rate_limit_cap_is_enforced():
    with pytest.raises(FreeAgentResilienceError):
        decide_rate_limit_retry(status_code=429, retry_after=301)
    assert decide_rate_limit_retry(
        status_code=429, retry_after=300, max_wait_seconds=300,
    ).retry_after_seconds == 300


@pytest.mark.parametrize("retry_after", [
    None, "", "   ", "soon", "+5", "-1", "5.0", 5.0, True, -1,
])
def test_rate_limit_fails_closed_on_missing_malformed_or_negative(retry_after):
    with pytest.raises(FreeAgentResilienceError):
        decide_rate_limit_retry(status_code=429, retry_after=retry_after)


@pytest.mark.parametrize("status_code", [200, 401, 500, 503, 429.0, True, "429"])
def test_rate_limit_fails_closed_on_unsupported_status(status_code):
    with pytest.raises(FreeAgentResilienceError):
        decide_rate_limit_retry(status_code=status_code, retry_after="60")


# ── Conservative error classification ────────────────────────────────────────


def test_error_classification_marks_only_valid_429_as_retryable():
    classification = classify_provider_error(status_code=429, retry_after="30")
    assert classification.error_class is ErrorClass.RATE_LIMITED
    assert classification.disposition is ErrorDisposition.RETRYABLE
    assert classification.retry_after_seconds == 30


def test_error_classification_fails_closed_on_unusable_retry_after():
    classification = classify_provider_error(status_code=429, retry_after=None)
    assert classification.error_class is ErrorClass.RATE_LIMITED
    assert classification.disposition is ErrorDisposition.REVIEW_REQUIRED
    assert classification.retry_after_seconds is None


def test_very_long_retry_after_is_controlled_and_review_required():
    value = "9" * 5000
    with pytest.raises(FreeAgentResilienceError):
        decide_rate_limit_retry(status_code=429, retry_after=value)
    classification = classify_provider_error(status_code=429, retry_after=value)
    assert classification.error_class is ErrorClass.RATE_LIMITED
    assert classification.disposition is ErrorDisposition.REVIEW_REQUIRED
    assert value not in (classification.reason or "")


@pytest.mark.parametrize("status_code", [401, 403, 500, 503])
def test_error_classification_marks_unknown_status_as_review_required(status_code):
    classification = classify_provider_error(status_code=status_code)
    assert classification.error_class is ErrorClass.UNKNOWN
    assert classification.disposition is ErrorDisposition.REVIEW_REQUIRED


def test_error_classification_rejects_malformed_status_type():
    with pytest.raises(FreeAgentResilienceError):
        classify_provider_error(status_code="429", retry_after="30")


# ── No network/persistence/credential/config/readiness side effects ──────────


def test_module_contains_no_forbidden_imports_or_side_effects():
    import reserved.providers.accounting.freeagent_resilience as mod

    source = inspect.getsource(mod)
    for forbidden in (
        "import requests", "from requests", "import httpx", "from httpx",
        "urlopen", "sqlite3", "pickle", "time.sleep", "os.environ", "getenv",
        "subprocess", "pathlib", "readiness", "oauth_security",
    ):
        assert forbidden not in source, forbidden

    for name in ("requests", "httpx", "urlopen", "sleep", "pickle", "subprocess"):
        assert not hasattr(mod, name), name


def test_default_bounds_are_bounded_inference_constants():
    assert DEFAULT_MAX_PAGES == 1000
    assert DEFAULT_MAX_WAIT_SECONDS == 300
