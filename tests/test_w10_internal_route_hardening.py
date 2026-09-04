"""Adversarial runtime checks for W10-S5C internal-route hardening.

These tests prove only fail-closed route behavior.  They do not define the
unresolved customer paid surface or grant entitlement/provider authority.
"""
from __future__ import annotations

import ast
import hashlib
import subprocess
from importlib import import_module
from pathlib import Path

import pytest

import reserved.database as db
from reserved import create_app
from reserved.auth import _SK_CLERK_ID, _SK_USER_ID

legacy_routes = import_module("reserved.web.routes")
v2_routes = import_module("reserved.web.v2")


ROOT = Path(__file__).resolve().parents[1]
BASE_COMMIT = "26944b22dfc4287287827ee7cdabe849e8906531"
BASE_TREE = "a072db4cfb9d22a32a9b41525098dbd110dcfeca"
ACCEPTED_S5B_COMMIT = "051ae665a0cc94f6e9cdbbc728c621825c7769fe"
FOUNDER_SOURCE_SHA256 = (
    "f0568a760771f9847aeaa6f7e3349b7bda3a2fe861808f4ab3e856e40b90f67b"
)
CAPITAL_GAINS_SOURCE_SHA256 = (
    "2789ff514411d516b90f9edc8c73a0f73a0ba8671231ac5386e95bca01fb1990"
)

ALLOWED_CANDIDATE_PATHS = {
    "reserved/web/routes.py",
    "reserved/web/v2.py",
    "tests/test_w10_internal_route_hardening.py",
    "tests/test_auth.py",
    "tests/test_tax_year_context.py",
    "tests/test_unsupported_plan_rendering.py",
}


def _make_app(tmp_path, monkeypatch, *, production=False, csrf_enabled=False):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "w10-s5c.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", "production" if production else "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    if production:
        monkeypatch.setenv("SESSION_SECRET", "s5c-test-only-session-secret-32-bytes")
    else:
        monkeypatch.delenv("SESSION_SECRET", raising=False)
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=csrf_enabled)
    return application


def _authenticate(client) -> int:
    user_id = db.get_or_create_user(
        clerk_user_id="user_w10_s5c",
        email="w10-s5c@example.invalid",
        display_name="W10 S5C",
    )
    with client.session_transaction() as stored:
        stored[_SK_USER_ID] = user_id
        stored[_SK_CLERK_ID] = "user_w10_s5c"
    return user_id


def _methods_by_endpoint(application) -> dict[str, tuple[str, ...]]:
    return {
        rule.endpoint: tuple(sorted(rule.methods - {"HEAD", "OPTIONS"}))
        for rule in application.url_map.iter_rules()
    }


def _function_source(relative_path: str, function_name: str) -> str:
    text = (ROOT / relative_path).read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == function_name
    ]
    assert len(functions) == 1
    function = functions[0]
    start = min(
        [function.lineno]
        + [decorator.lineno for decorator in function.decorator_list]
    )
    return "".join(lines[start - 1 : function.end_lineno])


def test_exact_route_and_security_authority_is_bound():
    assert BASE_COMMIT == "26944b22dfc4287287827ee7cdabe849e8906531"
    assert BASE_TREE == "a072db4cfb9d22a32a9b41525098dbd110dcfeca"
    evidence = (
        ROOT / "docs" / "W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md"
    ).read_text(encoding="utf-8")
    assert "This is not a paid-surface decision" in evidence
    assert "No additional Founder question is created" in evidence
    assert "fail-closed cleanup" in evidence
    subprocess.run(
        [
            "git", "-C", str(ROOT), "merge-base", "--is-ancestor",
            ACCEPTED_S5B_COMMIT, "HEAD",
        ],
        check=True,
    )


def test_route_registry_preserves_methods_and_founder_separation(tmp_path, monkeypatch):
    application = _make_app(tmp_path, monkeypatch)
    methods = _methods_by_endpoint(application)
    assert methods["web.calculate"] == ("POST",)
    assert methods["web.settings"] == ("GET", "POST")
    assert methods["web.connections"] == ("GET",)
    assert methods["web.tax_assurance"] == ("GET",)
    assert methods["web.capital_gains"] == ("GET", "POST")
    assert {
        endpoint: methods[endpoint]
        for endpoint in methods
        if endpoint.startswith("founder.")
    } == {
        "founder.login": ("GET", "POST"),
        "founder.dashboard": ("GET",),
        "founder.logout": ("POST",),
        "founder.export_feedback": ("GET",),
        "founder.export_early_access": ("GET",),
    }


@pytest.mark.parametrize("authenticated", [False, True])
@pytest.mark.parametrize("production", [False, True])
@pytest.mark.parametrize(
    ("legacy_path", "canonical_path"),
    [
        ("/connections", "/v2/connections"),
        ("/settings", "/v2/settings"),
    ],
)
def test_legacy_get_is_only_an_exact_canonical_redirect(
    tmp_path, monkeypatch, production, authenticated, legacy_path, canonical_path
):
    application = _make_app(tmp_path, monkeypatch, production=production)
    client = application.test_client()
    if authenticated:
        _authenticate(client)

    response = client.get(legacy_path)
    assert response.status_code == 302
    assert response.headers["Location"].endswith(canonical_path)

    canonical = client.get(canonical_path)
    if authenticated:
        assert canonical.status_code == 200
    else:
        assert canonical.status_code == 302
        expected_login = "/v2/login" if production else "/v2/demo-login"
        assert canonical.headers["Location"].endswith(expected_login)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/calculate"),
        ("put", "/calculate"),
        ("post", "/connections"),
        ("delete", "/settings"),
        ("post", "/tax-assurance"),
    ],
)
def test_unregistered_legacy_methods_cannot_reach_product_behavior(
    tmp_path, monkeypatch, method, path
):
    application = _make_app(tmp_path, monkeypatch)
    response = getattr(application.test_client(), method)(path)
    assert response.status_code == 405


@pytest.mark.parametrize("path", ["/calculate", "/settings"])
@pytest.mark.parametrize("authenticated", [False, True])
def test_legacy_post_hard_closes_before_session_or_database_mutation(
    tmp_path, monkeypatch, path, authenticated
):
    application = _make_app(tmp_path, monkeypatch)
    client = application.test_client()
    user_id = _authenticate(client) if authenticated else None
    with client.session_transaction() as stored:
        stored["profile"] = {"first_name": "unchanged"}

    def forbidden_mutation(*_args, **_kwargs):
        raise AssertionError("retired legacy route reached a mutation boundary")

    monkeypatch.setattr(legacy_routes, "save_profile_by_user", forbidden_mutation)
    monkeypatch.setattr(legacy_routes, "build_dashboard", forbidden_mutation)
    response = client.post(
        path,
        data={"invoice_amount": "9000", "first_name": "attacker"},
    )
    assert response.status_code == 404
    with client.session_transaction() as stored:
        assert stored["profile"] == {"first_name": "unchanged"}
    if user_id is not None:
        assert db.get_profile_by_user(user_id) is None


@pytest.mark.parametrize("path", ["/calculate", "/settings"])
def test_global_csrf_still_precedes_legacy_post_handler(tmp_path, monkeypatch, path):
    application = _make_app(tmp_path, monkeypatch, csrf_enabled=True)
    response = application.test_client().post(path, data={"first_name": "attacker"})
    assert response.status_code == 400


@pytest.mark.parametrize("production", [False, True])
@pytest.mark.parametrize("authenticated", [False, True])
def test_tax_assurance_is_never_customer_or_public_reachable(
    tmp_path, monkeypatch, production, authenticated
):
    application = _make_app(tmp_path, monkeypatch, production=production)
    client = application.test_client()
    if authenticated:
        _authenticate(client)
    response = client.get("/tax-assurance")
    assert response.status_code == 404
    assert b"test counts" not in response.data.lower()
    assert b"release status" not in response.data.lower()


@pytest.mark.parametrize("path", ["/capital-gains", "/capital-gains?x=1"])
@pytest.mark.parametrize("authenticated", [False, True])
def test_capital_gains_hard_404_is_unchanged(
    tmp_path, monkeypatch, path, authenticated
):
    application = _make_app(tmp_path, monkeypatch)
    client = application.test_client()
    if authenticated:
        _authenticate(client)
    assert client.get(path).status_code == 404
    assert client.post(path, data={"proceeds": "999999"}).status_code == 404


@pytest.mark.parametrize(
    ("flask_env", "clerk_key"),
    [
        ("production", "pk_test_synthetic"),
        ("development", "pk_live_synthetic"),
    ],
)
@pytest.mark.parametrize("authenticated", [False, True])
def test_sandbox_checklist_404s_before_auth_or_provider_construction_in_production(
    tmp_path, monkeypatch, flask_env, clerk_key, authenticated
):
    monkeypatch.setattr(db, "_DB_FILE", tmp_path / "w10-s5c-production.db")
    monkeypatch.setattr(db, "_INSTANCE", tmp_path)
    monkeypatch.setenv("FLASK_ENV", flask_env)
    monkeypatch.setenv("CLERK_PUBLISHABLE_KEY", clerk_key)
    monkeypatch.setenv("SESSION_SECRET", "s5c-test-only-session-secret-32-bytes")
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = application.test_client()
    if authenticated:
        _authenticate(client)

    def forbidden_client():
        raise AssertionError("production sandbox route constructed a provider client")

    monkeypatch.setattr(v2_routes, "YapilyClient", forbidden_client)
    response = client.get("/v2/sandbox-checklist")
    assert response.status_code == 404
    assert response.headers["Cache-Control"] == "no-store, max-age=0"


def test_sandbox_checklist_retains_nonproduction_customer_session_guard(
    tmp_path, monkeypatch
):
    application = _make_app(tmp_path, monkeypatch)
    client = application.test_client()
    unauthenticated = client.get("/v2/sandbox-checklist")
    assert unauthenticated.status_code == 302
    assert unauthenticated.headers["Location"].endswith("/v2/demo-login")

    calls = []

    class FakeClient:
        mock = True
        _uuid = "present"
        _secret = "present"

        def __init__(self):
            calls.append("constructed")

    monkeypatch.setattr(v2_routes, "YapilyClient", FakeClient)
    _authenticate(client)
    authenticated = client.get("/v2/sandbox-checklist")
    assert authenticated.status_code == 200
    assert calls == ["constructed"]
    assert authenticated.headers["Cache-Control"] == "no-store, max-age=0"


def test_founder_source_and_capital_gains_body_are_byte_stable():
    founder_hash = hashlib.sha256(
        (ROOT / "reserved/web/founder.py").read_bytes()
    ).hexdigest()
    assert founder_hash == FOUNDER_SOURCE_SHA256
    capital_source = _function_source("reserved/web/routes.py", "capital_gains")
    assert hashlib.sha256(capital_source.encode("utf-8")).hexdigest() == (
        CAPITAL_GAINS_SOURCE_SHA256
    )


def test_customer_session_never_grants_founder_administration(tmp_path, monkeypatch):
    application = _make_app(tmp_path, monkeypatch)
    client = application.test_client()
    _authenticate(client)
    assert client.get("/founder/login").status_code == 200
    for path in (
        "/founder/",
        "/founder/export/feedback",
        "/founder/export/early-access",
    ):
        response = client.get(path)
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/founder/login")
    logout = client.post("/founder/logout")
    assert logout.status_code == 302
    assert logout.headers["Location"].endswith("/founder/login")
    with client.session_transaction() as stored:
        assert stored[_SK_USER_ID]


def test_hardened_routes_do_not_claim_or_consult_paid_entitlement():
    sources = "\n".join(
        _function_source("reserved/web/routes.py", name)
        for name in ("calculate", "settings", "connections", "tax_assurance")
    )
    sources += _function_source("reserved/web/v2.py", "sandbox_checklist")
    sources += _function_source(
        "reserved/web/v2.py", "_hide_production_internal_routes"
    )
    lowered = sources.lower()
    for forbidden in (
        "entitlement",
        "subscription",
        "paid_access",
        "checkout",
        "stripe",
    ):
        assert forbidden not in lowered


def test_candidate_changes_only_authorised_route_and_test_paths():
    changed = subprocess.run(
        ["git", "-C", str(ROOT), "diff", "--name-only", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    untracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert set(changed + untracked) <= ALLOWED_CANDIDATE_PATHS
