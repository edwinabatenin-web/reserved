"""Source-bound checks for the evidence-only W10-S5B reconciliation."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
S5A = ROOT / "docs" / "W10_S5A_PAID_SURFACE_INVENTORY.md"
S5B = ROOT / "docs" / "W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md"
S5A_START = "<!-- W10-S5A-INVENTORY-BEGIN -->"
S5A_END = "<!-- W10-S5A-INVENTORY-END -->"
S5B_START = "<!-- W10-S5B-RECONCILIATION-BEGIN -->"
S5B_END = "<!-- W10-S5B-RECONCILIATION-END -->"

EXPECTED = {
    "web.calculate": (
        "/calculate",
        ("POST",),
        "none",
        "global",
        "legacy_product_action_not_independent_october_surface",
        "remove_registration_or_production_404_until_separately_authenticated_and_classified",
        "ordinary_fail_closed_engineering_cleanup",
    ),
    "web.capital_gains": (
        "/capital-gains",
        ("GET", "POST"),
        "always_404",
        "global",
        "excluded_capital_gains_dormant",
        "keep_dormant_always_404_for_october",
        "settled_founder_scope_preservation",
    ),
    "web.connections": (
        "/connections",
        ("GET",),
        "none",
        "not_applicable",
        "legacy_alias_to_authenticated_connections_product",
        "redirect_get_to_customer_authenticated_v2_connections_no_independent_content",
        "ordinary_fail_closed_engineering_cleanup",
    ),
    "web.settings": (
        "/settings",
        ("GET", "POST"),
        "none",
        "global",
        "legacy_alias_to_authenticated_customer_settings_product",
        "redirect_get_to_customer_authenticated_v2_settings_and_disable_legacy_post",
        "ordinary_fail_closed_engineering_cleanup",
    ),
    "web.tax_assurance": (
        "/tax-assurance",
        ("GET",),
        "none",
        "not_applicable",
        "internal_assurance_noncustomer_nonproduction",
        "production_404_and_nonproduction_staff_authenticated_only",
        "ordinary_security_engineering_cleanup",
    ),
    "founder.dashboard": (
        "/founder/",
        ("GET",),
        "founder_session",
        "not_applicable",
        "founder_only_privileged_administration",
        "keep_founder_only_outside_customer_paid_boundary_and_preserve_no_store",
        "ordinary_privilege_boundary_preservation",
    ),
    "founder.export_early_access": (
        "/founder/export/early-access",
        ("GET",),
        "founder_session",
        "not_applicable",
        "founder_only_sensitive_personal_data_export",
        "keep_founder_only_preserve_no_store_and_spreadsheet_safe_csv",
        "ordinary_privilege_boundary_preservation",
    ),
    "founder.export_feedback": (
        "/founder/export/feedback",
        ("GET",),
        "founder_session",
        "not_applicable",
        "founder_only_sensitive_personal_data_export",
        "keep_founder_only_preserve_no_store_and_spreadsheet_safe_csv",
        "ordinary_privilege_boundary_preservation",
    ),
    "founder.login": (
        "/founder/login",
        ("GET", "POST"),
        "founder_password_and_rate_limit",
        "global",
        "founder_only_privileged_authentication_entry",
        "keep_founder_admin_entry_outside_customer_paid_boundary_preserve_rate_limit_and_clean_session",
        "ordinary_privilege_boundary_preservation",
    ),
    "founder.logout": (
        "/founder/logout",
        ("POST",),
        "founder_session",
        "global",
        "founder_only_privileged_session_termination",
        "keep_founder_only_post_csrf_full_session_clear_outside_customer_paid_boundary",
        "ordinary_privilege_boundary_preservation",
    ),
    "v2.sandbox_checklist": (
        "/v2/sandbox-checklist",
        ("GET",),
        "customer_session",
        "not_applicable",
        "internal_provider_assurance_noncustomer_nonproduction",
        "production_404_and_nonproduction_staff_authenticated_only_not_readiness_authority",
        "ordinary_security_engineering_cleanup",
    ),
}

EXPECTED_SOURCE_REACHABILITY = {
    "web.calculate": (
        "reserved/web/routes.py",
        "calculate",
        "public_post_with_valid_csrf_reaches_legacy_calculation",
    ),
    "web.capital_gains": (
        "reserved/web/routes.py",
        "capital_gains",
        "get_is_404_and_post_is_404_after_global_csrf",
    ),
    "web.connections": (
        "reserved/web/routes.py",
        "connections",
        "public_get_renders_legacy_illustrative_connections",
    ),
    "web.settings": (
        "reserved/web/routes.py",
        "settings",
        "public_get_and_valid_csrf_post_updates_session_or_authenticated_owner_profile",
    ),
    "web.tax_assurance": (
        "reserved/web/routes.py",
        "tax_assurance",
        "public_get_reads_local_assurance_metadata_and_renders_internal_page",
    ),
    "founder.dashboard": (
        "reserved/web/founder.py",
        "dashboard",
        "founder_session_required_otherwise_redirect_to_founder_login",
    ),
    "founder.export_early_access": (
        "reserved/web/founder.py",
        "export_early_access",
        "founder_session_required_personal_data_csv_download",
    ),
    "founder.export_feedback": (
        "reserved/web/founder.py",
        "export_feedback",
        "founder_session_required_personal_data_csv_download",
    ),
    "founder.login": (
        "reserved/web/founder.py",
        "login",
        "public_login_form_and_valid_csrf_password_post_with_persistent_rate_limit",
    ),
    "founder.logout": (
        "reserved/web/founder.py",
        "logout",
        "founder_session_and_global_csrf_required_then_entire_session_cleared",
    ),
    "v2.sandbox_checklist": (
        "reserved/web/v2.py",
        "sandbox_checklist",
        "any_authenticated_customer_can_view_provider_mode_and_secret_presence_booleans",
    ),
}


def extract(path: Path, start: str, end: str) -> dict:
    text = path.read_text(encoding="utf-8")
    payload = text.split(start, 1)[1].split(end, 1)[0].strip()
    assert payload.startswith("```json\n") and payload.endswith("```")
    return json.loads(payload.removeprefix("```json\n").removesuffix("```").strip())


def s5a() -> dict:
    return extract(S5A, S5A_START, S5A_END)


def s5b() -> dict:
    return extract(S5B, S5B_START, S5B_END)


def decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Call):
        return decorator_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = decorator_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def function(relative_path: str, name: str) -> ast.FunctionDef:
    tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
    matches = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    assert len(matches) == 1
    return matches[0]


def test_exact_metadata_is_evidence_only_and_no_new_founder_question():
    data = s5b()
    assert data["schema_version"] == "W10-S5B/2026-09-04/v1"
    assert data["repository_head"] == (
        "5612f7a33f27f09d1fa988f15dfdffbe77a72705"
    )
    assert data["repository_tree"] == "4786614d7ea428e3aea1d61a72dc74d9aad6bd92"
    assert data["accepted_s5a_commit"] == (
        "9c0760192bb2420b90e57ec7313f69bbe52cbf74"
    )
    assert data["reconciliation_status"] == "evidence_only_no_runtime_change"
    assert data["s5_status"] == "not_started"
    assert data["paid_boundary_status"] == (
        "unresolved_existing_s5a_founder_question"
    )
    assert data["new_founder_question_required"] is False


def test_every_reviewed_source_is_exactly_hash_bound():
    for relative_path, expected_hash in s5b()["source_sha256"].items():
        actual_hash = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
        assert actual_hash == expected_hash, f"stale S5B source: {relative_path}"


def test_exact_s5a_unknown_set_is_consumed_without_omission_or_expansion():
    accepted_unknown = {
        route["endpoint"]: route
        for route in s5a()["routes"]
        if route["classification"]
        == "internal_admin_unknown_requiring_reconciliation"
    }
    reconciled = {route["endpoint"]: route for route in s5b()["routes"]}
    assert set(accepted_unknown) == set(EXPECTED) == set(reconciled)
    assert len(reconciled) == 11
    for endpoint, route in reconciled.items():
        upstream = accepted_unknown[endpoint]
        assert route["rule"] == upstream["rule"]
        assert route["methods"] == upstream["methods"]
        assert route["registration"] == upstream["registration"] == "always"
        assert route["current_guard"] == upstream["guard"]
        assert route["csrf"] == upstream["csrf"]


def test_guard_category_treatment_and_decision_substitution_is_rejected():
    actual = {}
    actual_source_reachability = {}
    for route in s5b()["routes"]:
        assert set(route) == {
            "endpoint",
            "rule",
            "methods",
            "registration",
            "current_guard",
            "csrf",
            "source",
            "handler",
            "current_reachability",
            "october_category",
            "recommended_treatment",
            "decision_class",
            "collision_security_risks",
        }
        actual[route["endpoint"]] = (
            route["rule"],
            tuple(route["methods"]),
            route["current_guard"],
            route["csrf"],
            route["october_category"],
            route["recommended_treatment"],
            route["decision_class"],
        )
        actual_source_reachability[route["endpoint"]] = (
            route["source"],
            route["handler"],
            route["current_reachability"],
        )
        assert route["collision_security_risks"]
        assert len(route["collision_security_risks"]) == len(
            set(route["collision_security_risks"])
        )
    assert actual == EXPECTED
    assert actual_source_reachability == EXPECTED_SOURCE_REACHABILITY


def test_route_decorators_and_critical_current_guards_match_source():
    web_expected = {
        "calculate": {"web.post"},
        "capital_gains": {"web.route"},
        "connections": {"web.get"},
        "settings": {"web.route"},
        "tax_assurance": {"web.get"},
    }
    for name, expected in web_expected.items():
        node = function("reserved/web/routes.py", name)
        assert {decorator_name(item) for item in node.decorator_list} == expected

    founder_expected = {
        "login": {"founder.route"},
        "dashboard": {"founder.get", "require_founder"},
        "logout": {"founder.post", "require_founder"},
        "export_feedback": {"founder.get", "require_founder"},
        "export_early_access": {"founder.get", "require_founder"},
    }
    for name, expected in founder_expected.items():
        node = function("reserved/web/founder.py", name)
        assert {decorator_name(item) for item in node.decorator_list} == expected

    sandbox = function("reserved/web/v2.py", "sandbox_checklist")
    assert {decorator_name(item) for item in sandbox.decorator_list} == {
        "v2.get",
        "require_auth",
    }

    capital_gains = function("reserved/web/routes.py", "capital_gains")
    # Comments and the function's absent docstring do not occupy AST nodes: the
    # hard abort must remain the first executable statement.
    assert isinstance(capital_gains.body[0], ast.Expr)
    calls = [
        node for node in ast.walk(capital_gains.body[0]) if isinstance(node, ast.Call)
    ]
    assert calls and decorator_name(calls[0].func) == "abort"
    assert isinstance(calls[0].args[0], ast.Constant) and calls[0].args[0].value == 404


def test_security_sensitive_behavior_is_present_in_exact_bound_sources():
    founder = (ROOT / "reserved" / "web" / "founder.py").read_text(encoding="utf-8")
    app = (ROOT / "reserved" / "__init__.py").read_text(encoding="utf-8")
    security = (ROOT / "reserved" / "security.py").read_text(encoding="utf-8")
    v2 = (ROOT / "reserved" / "web" / "v2.py").read_text(encoding="utf-8")

    successful_login = founder.split("if _check_password(password):", 1)[1].split(
        "else:", 1
    )[0]
    logout = founder.split("def logout():", 1)[1].split("@founder.get", 1)[0]
    assert "hmac.compare_digest" in founder
    assert "check_rate_limit" in founder and "record_rate_attempt" in founder
    assert successful_login.index("session.clear()") < successful_login.index(
        "session[_SESSION_KEY] = True"
    )
    assert "session.clear()" in logout and "session.modified = True" in logout
    assert 'path.startswith(("/v2/", "/founder"))' in app
    assert 'h["Cache-Control"] = "no-store, max-age=0"' in app
    assert "def spreadsheet_safe_row" in security
    assert "spreadsheet_safe_row(row)" in founder
    sandbox_body = v2.split("def sandbox_checklist():", 1)[1].split(
        "# ── Protected Yapily", 1
    )[0]
    assert "YapilyClient()" in sandbox_body
    assert "bool(client._uuid)" in sandbox_body
    assert "bool(client._secret)" in sandbox_body


def test_legacy_handlers_match_documented_reachability_and_collision_facts():
    routes = (ROOT / "reserved" / "web" / "routes.py").read_text(encoding="utf-8")
    calculate = routes.split("def calculate():", 1)[1].split("@web.route", 1)[0]
    settings = routes.split("def settings():", 1)[1].split("@web.route", 1)[0]
    connections = routes.split("def connections():", 1)[1].split("@web.get", 1)[0]
    tax_assurance = routes.split("def tax_assurance():", 1)[1]
    assert 'request.form.get("invoice_amount"' in calculate
    assert 'render_template(\n        "dashboard.html"' in calculate
    assert 'session["profile"] = profile' in settings
    assert "save_profile_by_user" in settings
    assert 'render_template("connections.html")' in connections
    assert "meta_path.read_text()" in tax_assurance
    assert 'render_template("tax_assurance.html", meta=metadata)' in tax_assurance


def test_document_preserves_nonimplementation_and_decision_boundaries():
    text = S5B.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    required = (
        "It changes no route or runtime behavior.",
        "W10-S5 implementation remains **not started**",
        "No additional Founder question is created",
        "This evidence neither answers nor restates that question.",
        "None of the routes below becomes a free or paid customer product",
        "No database, network, environment credential or provider code path is exercised.",
    )
    for phrase in required:
        assert phrase in normalized
    forbidden = (
        "paid boundary approved",
        "entitlement implemented",
        "W10-S5 complete",
    )
    for phrase in forbidden:
        assert phrase not in text
    assert "does not claim they are launch-ready" in normalized


def test_assurance_test_itself_is_standard_library_and_io_inert():
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    assert imports == {"__future__", "ast", "hashlib", "json", "pathlib"}
