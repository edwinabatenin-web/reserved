"""Credential-free contract tests for the provider HTTP boundary."""

from reserved.providers.http_boundary import (
    EndpointPolicy,
    GuardedTransport,
    HttpMethod,
    ProviderBoundaryError,
    ProviderRequest,
    ProviderResponse,
)


class RecordingTransport:
    def __init__(self):
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        return ProviderResponse(200, {"content-type": "application/json"}, b"{}")


def policy():
    return EndpointPolicy(
        provider="synthetic-provider",
        environment="sandbox",
        allowed_origins=frozenset({"https://sandbox.provider.example"}),
    )


def assert_rejected(url):
    transport = RecordingTransport()
    guarded = GuardedTransport(policy(), transport)
    try:
        guarded.send(ProviderRequest(HttpMethod.GET, url))
    except ProviderBoundaryError:
        pass
    else:
        raise AssertionError(f"Unsafe URL was accepted: {url}")
    assert transport.requests == [], "Rejected requests must never reach the transport"


def test_exact_sandbox_origin_is_allowed():
    transport = RecordingTransport()
    response = GuardedTransport(policy(), transport).send(
        ProviderRequest(HttpMethod.GET, "https://sandbox.provider.example/v1/items?page=2")
    )
    assert response.status_code == 200
    assert len(transport.requests) == 1


def test_production_and_origin_confusion_are_blocked_before_transport():
    for url in (
        "https://api.provider.example/v1/items",
        "https://sandbox.provider.example.attacker.test/v1/items",
        "https://sandbox.provider.example@attacker.test/v1/items",
        "http://sandbox.provider.example/v1/items",
        "//sandbox.provider.example/v1/items",
    ):
        assert_rejected(url)


def test_fragment_and_invalid_port_are_rejected():
    assert_rejected("https://sandbox.provider.example/v1/items#token")
    assert_rejected("https://sandbox.provider.example:invalid/v1/items")


def test_only_non_live_environment_policies_can_be_constructed():
    try:
        EndpointPolicy("provider", "production", frozenset({"https://api.provider.example"}))
    except ProviderBoundaryError as exc:
        assert "sandbox, test or demo" in str(exc)
    else:
        raise AssertionError("Production policy must not be constructible here")


def test_origins_cannot_contain_paths_credentials_queries_or_fragments():
    for origin in (
        "https://provider.example/api",
        "https://user:secret@provider.example",
        "https://provider.example?environment=sandbox",
        "https://provider.example#sandbox",
    ):
        try:
            EndpointPolicy("provider", "sandbox", frozenset({origin}))
        except ProviderBoundaryError:
            pass
        else:
            raise AssertionError(f"Invalid origin was accepted: {origin}")


def test_evidence_summary_redacts_credentials_and_omits_body_and_query_values():
    secret = "synthetic-secret-must-not-appear"
    request = ProviderRequest(
        HttpMethod.POST,
        f"https://sandbox.provider.example/token?code={secret}",
        headers={"Authorization": f"Bearer {secret}", "Accept": "application/json"},
        body=f"refresh_token={secret}".encode(),
        correlation_id="synthetic-correlation",
    )
    summary = request.redacted_summary()
    rendered = repr(summary)
    assert secret not in rendered
    assert summary["headers"]["Authorization"] == "[REDACTED]"
    assert summary["headers"]["Accept"] == "application/json"
    assert summary["query_present"] is True
    assert summary["body_present"] is True
    assert summary["body_length"] > 0


def test_evidence_summary_never_copies_url_user_information():
    secret = "url-user-info-secret"
    request = ProviderRequest(
        HttpMethod.GET,
        f"https://user:{secret}@sandbox.provider.example/items",
    )
    summary = request.redacted_summary()
    assert secret not in repr(summary)
    assert summary["origin"] == "https://sandbox.provider.example"


def test_request_headers_are_immutable_after_validation():
    original = {"Accept": "application/json"}
    request = ProviderRequest(HttpMethod.GET, "https://sandbox.provider.example/items", original)
    original["Authorization"] = "late-secret"
    assert "Authorization" not in request.headers
    try:
        request.headers["Another"] = "value"
    except TypeError:
        pass
    else:
        raise AssertionError("Request headers must be immutable")


def test_invalid_response_status_fails_closed():
    try:
        ProviderResponse(700)
    except ProviderBoundaryError:
        pass
    else:
        raise AssertionError("Invalid response status must be rejected")
