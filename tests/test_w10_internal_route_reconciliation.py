"""Source-bound checks for refreshed W10-S5B/S5C route evidence."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
S5A = ROOT / "docs" / "W10_S5A_PAID_SURFACE_INVENTORY.md"
S5B = ROOT / "docs" / "W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md"
S5C = ROOT / "docs" / "W10_S5C_INTERNAL_ROUTE_HARDENING_EVIDENCE.md"
S5A_START = "<!-- W10-S5A-INVENTORY-BEGIN -->"
S5A_END = "<!-- W10-S5A-INVENTORY-END -->"
S5B_START = "<!-- W10-S5B-RECONCILIATION-BEGIN -->"
S5B_END = "<!-- W10-S5B-RECONCILIATION-END -->"
HISTORICAL_MAP = "docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md"
WRONG_MAP_COMMIT = "81ae02044cccd921d98a0d1fc2360e1c4a983ab1"
S5C_START = "<!-- W10-S5C-EVIDENCE-BEGIN -->"
S5C_END = "<!-- W10-S5C-EVIDENCE-END -->"

EXPECTED_PRODUCT_PATH_HASHES = {
    "reserved/web/routes.py": (
        "f1d8f6ea3730c8962899a0ffa4d7a78b8c8791693ca03c0d19e0feb8cec42bed"
    ),
    "reserved/web/v2.py": (
        "dd4bcc1ec49793065da525fefd26709522ce12f5560fd3ee6af7b72ca27ae228"
    ),
    "tests/test_auth.py": (
        "5dd2284eeb57dbed40119936ada5bde9c3902b21d0c0bf44cb61e55275d7b974"
    ),
    "tests/test_tax_year_context.py": (
        "f01625359c365ca0085064e264d747e6d9d4007db0c6a34281f7666fff1d37fd"
    ),
    "tests/test_unsupported_plan_rendering.py": (
        "5e2eae15e80a876a17bd0339526a798def1c238fbf84457178822710ef196c49"
    ),
    "tests/test_w10_internal_route_hardening.py": (
        "20a754059b817eb33e5c83ae3edbe551c92c2bafbbbeeca39ed2c709900db3c8"
    ),
}
CURRENT_ROUTES_SHA256 = (
    "cbac0af6c8e7fa7ef43017ba54dab0186330b556a6c9dd946e8cfcbd3fa0e9fd"
)

EXPECTED = {
    "web.calculate": (
        "/calculate",
        ("POST",),
        "always_404",
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
        "redirect_to_customer_session_guarded_v2_equivalent",
        "not_applicable",
        "legacy_alias_to_authenticated_connections_product",
        "redirect_get_to_customer_authenticated_v2_connections_no_independent_content",
        "ordinary_fail_closed_engineering_cleanup",
    ),
    "web.settings": (
        "/settings",
        ("GET", "POST"),
        "get_redirect_to_customer_session_guarded_v2_equivalent_post_always_404",
        "global",
        "legacy_alias_to_authenticated_customer_settings_product",
        "redirect_get_to_customer_authenticated_v2_settings_and_disable_legacy_post",
        "ordinary_fail_closed_engineering_cleanup",
    ),
    "web.tax_assurance": (
        "/tax-assurance",
        ("GET",),
        "always_404",
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
        "production_404_nonproduction_customer_session",
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
        "valid_csrf_post_is_404_before_profile_calculation_or_render",
    ),
    "web.capital_gains": (
        "reserved/web/routes.py",
        "capital_gains",
        "get_is_404_and_post_is_404_after_global_csrf",
    ),
    "web.connections": (
        "reserved/web/routes.py",
        "connections",
        "public_get_redirects_exactly_to_customer_session_guarded_v2_connections",
    ),
    "web.settings": (
        "reserved/web/routes.py",
        "settings",
        "public_get_redirects_exactly_to_customer_session_guarded_v2_settings_and_valid_csrf_post_is_404_before_mutation",
    ),
    "web.tax_assurance": (
        "reserved/web/routes.py",
        "tax_assurance",
        "get_is_404_before_metadata_read_or_render_in_all_environments_and_auth_states",
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
        "production_404_before_customer_auth_or_provider_construction_nonproduction_customer_session_required",
    ),
}

EXPECTED_IMPLEMENTED_TREATMENTS = {
    "web.calculate": {
        "status": "implemented_at_accepted_s5c_product_checkpoint",
        "treatment": (
            "registered_post_hard_404_before_profile_calculation_or_render"
        ),
    },
    "web.connections": {
        "status": "implemented_at_accepted_s5c_product_checkpoint",
        "treatment": (
            "get_redirects_exactly_to_customer_session_guarded_v2_connections_"
            "with_no_independent_content"
        ),
    },
    "web.settings": {
        "status": "implemented_at_accepted_s5c_product_checkpoint",
        "treatment": (
            "get_redirects_exactly_to_customer_session_guarded_v2_settings_and_"
            "valid_csrf_post_hard_404s_before_mutation"
        ),
    },
    "web.tax_assurance": {
        "status": "implemented_at_accepted_s5c_product_checkpoint",
        "treatment": (
            "hard_404_before_metadata_read_or_render_in_all_environments_and_"
            "auth_states"
        ),
    },
    "v2.sandbox_checklist": {
        "status": "implemented_at_accepted_s5c_product_checkpoint",
        "treatment": (
            "production_404_before_customer_auth_or_provider_construction_"
            "nonproduction_existing_customer_session_guard_preserved"
        ),
    },
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


def git_blob_sha256(commit: str, relative_path: str) -> str:
    """Hash the exact repository blob reviewed at ``commit``."""

    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return hashlib.sha256(result.stdout).hexdigest()


def assert_historical_hash(commit: str, relative_path: str, expected_hash: str):
    actual_hash = git_blob_sha256(commit, relative_path)
    assert actual_hash == expected_hash, (
        f"stale historical S5B source: {commit}:{relative_path}"
    )


def s5c() -> dict:
    return extract(S5C, S5C_START, S5C_END)


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


def test_exact_metadata_preserves_incomplete_s5_and_no_new_founder_question():
    data = s5b()
    assert data["schema_version"] == "W10-S5B/2026-09-04/v2"
    assert data["repository_head"] == (
        "c5e560045ed3d62f02c894e931464c3d7294e99f"
    )
    assert data["repository_tree"] == "bcdbec9108c3c0904139eca278c03fe0f6914db2"
    assert data["accepted_s5a_commit"] == (
        "9c0760192bb2420b90e57ec7313f69bbe52cbf74"
    )
    assert data["accepted_s5b_commit"] == (
        "051ae665a0cc94f6e9cdbbc728c621825c7769fe"
    )
    assert data["accepted_s5c_product_checkpoint"] == (
        "3c63e64e478957ce04ee1154363c2eae94b82b30"
    )
    assert data["accepted_s5c_product_tree"] == (
        "ac3eb6f3028ef2e60bbd1543c1ee92f94655a0b7"
    )
    assert data["accepted_s5c_product_checkpoint"] != data["repository_head"]
    assert data["reconciliation_status"] == (
        "accepted_reconciliation_with_implemented_s5c_treatments"
    )
    assert data["evidence_refresh_status"] == (
        "candidate_requires_independent_review"
    )
    assert data["s5_status"] == (
        "incomplete_prerequisite_route_hardening_implemented"
    )
    assert data["paid_boundary_status"] == (
        "unresolved_existing_s5a_founder_question"
    )
    assert data["paid_entitlement_enforcement_status"] == "not_started"
    assert data["new_founder_question_required"] is False


def test_every_reviewed_source_is_exactly_hash_bound():
    data = s5b()
    for relative_path, expected_hash in data["source_sha256"].items():
        if relative_path in (HISTORICAL_MAP, "FOUNDER_DECISIONS.md"):
            # The map is mutable bookkeeping. Verify the exact blob S5B reviewed
            # and the Founder authority is an immutable historical decision
            # snapshot. Later truthful updates must not look like corruption of
            # the accepted S5B evidence.
            actual_hash = git_blob_sha256(data["repository_head"], relative_path)
        else:
            # Route, guard and authority sources stay live-bound so current drift
            # still invalidates the evidence exactly as before.
            actual_hash = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
        assert actual_hash == expected_hash, f"stale S5B source: {relative_path}"


def test_historical_completion_map_is_verified_from_exact_git_blob_and_rejects_forgery():
    binding = s5b()["historical_completion_map_blob"]
    assert binding == {
        "commit": "5612f7a33f27f09d1fa988f15dfdffbe77a72705",
        "path": "docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md",
        "sha256": "7af205f420c2cf3a9039fff7aad1af65e55221005231b2fabe3bd99c94f96c4d",
    }
    live_hash = hashlib.sha256((ROOT / binding["path"]).read_bytes()).hexdigest()
    assert live_hash != binding["sha256"]
    assert_historical_hash(binding["commit"], binding["path"], binding["sha256"])

    try:
        assert_historical_hash(binding["commit"], binding["path"], "0" * 64)
    except AssertionError:
        pass
    else:  # pragma: no cover - explicit negative-control failure path
        raise AssertionError("an incorrect historical S5B digest was accepted")

    try:
        assert_historical_hash(WRONG_MAP_COMMIT, binding["path"], binding["sha256"])
    except AssertionError:
        pass
    else:  # pragma: no cover - explicit negative-control failure path
        raise AssertionError("an incorrect historical S5B commit was accepted")


def test_s5c_checkpoint_binds_exact_product_diff_hashes_and_disposition():
    data = s5c()
    assert data["schema_version"] == "W10-S5C/2026-09-04/v1"
    assert data["accepted_product_commit"] == (
        "3c63e64e478957ce04ee1154363c2eae94b82b30"
    )
    assert data["accepted_product_tree"] == (
        "ac3eb6f3028ef2e60bbd1543c1ee92f94655a0b7"
    )
    assert data["accepted_product_disposition"] == (
        "independently_reviewed_accepted_and_integrated"
    )
    assert data["evidence_refresh_status"] == (
        "candidate_requires_independent_review"
    )
    assert data["s5_status"] == (
        "incomplete_prerequisite_route_hardening_implemented"
    )
    assert data["paid_boundary_status"] == (
        "unresolved_existing_s5a_founder_question"
    )
    assert data["paid_entitlement_enforcement_status"] == "not_started"
    assert data["verification"] == {
        "accepted_product_focused": "38_passed",
        "accepted_product_affected": "354_passed",
        "pre_refresh_clean_checkpoint_freshness": (
            "3_expected_failures_for_stale_s5a_s5b_source_guard_and_"
            "reachability_evidence"
        ),
        "refreshed_evidence_focused": "28_passed",
        "expanded_evidence_affected": (
            "62_passed_with_one_dirty_worktree_scope_sentinel_deselected"
        ),
        "unfiltered_candidate_full": (
            "6594_passed_2_expected_dirty_worktree_scope_sentinel_failures_"
            "7_subtests_passed"
        ),
        "substantive_candidate_full": (
            "6594_passed_2_dirty_worktree_scope_sentinels_deselected_"
            "7_subtests_passed"
        ),
        "post_commit_unfiltered_expectation": (
            "6596_passed_7_subtests_passed_with_clean_worktree_and_exact_one_"
            "generation_history_allowance"
        ),
    }
    assert data["product_changed_paths_sha256"] == EXPECTED_PRODUCT_PATH_HASHES
    for relative_path, expected_hash in EXPECTED_PRODUCT_PATH_HASHES.items():
        assert git_blob_sha256(
            data["accepted_product_commit"], relative_path
        ) == expected_hash
    changed = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            data["accepted_product_commit"],
        ],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.splitlines()
    assert set(changed) == set(EXPECTED_PRODUCT_PATH_HASHES)


def test_s5c_historical_routes_blob_is_distinct_from_live_s5b_binding():
    path = "reserved/web/routes.py"
    historical_commit = s5c()["accepted_product_commit"]
    historical_hash = EXPECTED_PRODUCT_PATH_HASHES[path]
    live_hash = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()

    assert git_blob_sha256(historical_commit, path) == historical_hash
    assert s5b()["source_sha256"][path] == live_hash == CURRENT_ROUTES_SHA256
    assert historical_hash != live_hash


def test_s5c_treatments_match_current_s5b_guards_reachability_and_treatment():
    checkpoint = s5c()["implemented_route_treatments"]
    reconciliation = {route["endpoint"]: route for route in s5b()["routes"]}
    assert set(checkpoint) == set(EXPECTED_IMPLEMENTED_TREATMENTS)
    for endpoint, outcome in checkpoint.items():
        assert outcome == {
            "guard": reconciliation[endpoint]["current_guard"],
            "reachability": reconciliation[endpoint]["current_reachability"],
            "treatment": EXPECTED_IMPLEMENTED_TREATMENTS[endpoint]["treatment"],
        }


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
    assert s5b()["s5c_implemented_treatments"] == EXPECTED_IMPLEMENTED_TREATMENTS


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
    production_gate = v2.split(
        "def _hide_production_internal_routes():", 1
    )[1].split("# ── Illustrative UK bank roster", 1)[0]
    assert 'request.endpoint == "v2.sandbox_checklist"' in production_gate
    assert "is_production_environment()" in production_gate
    assert "abort(404)" in production_gate


def test_legacy_handlers_match_documented_reachability_and_collision_facts():
    routes = (ROOT / "reserved" / "web" / "routes.py").read_text(encoding="utf-8")
    calculate = routes.split("def calculate():", 1)[1].split("@web.route", 1)[0]
    settings = routes.split("def settings():", 1)[1].split("@web.route", 1)[0]
    connections = routes.split("def connections():", 1)[1].split("@web.get", 1)[0]
    tax_assurance = routes.split("def tax_assurance():", 1)[1]
    assert "abort(404)" in calculate
    assert 'request.form.get("invoice_amount"' not in calculate
    assert "build_dashboard" not in calculate
    assert settings.index('if request.method == "POST":') < settings.index(
        "abort(404)"
    ) < settings.index('url_for("v2.settings_page")')
    assert 'session["profile"] = profile' not in settings
    assert "save_profile_by_user" not in settings
    assert 'return redirect(url_for("v2.connections"))' in connections
    assert 'render_template("connections.html")' not in connections
    assert tax_assurance.index("abort(404)") < tax_assurance.index(
        "meta_path.read_text()"
    )
    assert 'render_template("tax_assurance.html", meta=metadata)' in tax_assurance


def test_document_preserves_nonimplementation_and_decision_boundaries():
    text = S5B.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    required = (
        "This evidence refresh changes no route or runtime behavior.",
        "prerequisite route hardening is implemented",
        "paid-entitlement enforcement remain **not started**",
        "W10-S5 remains incomplete",
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


def test_assurance_test_itself_is_standard_library_and_external_service_inert():
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    assert imports == {
        "__future__",
        "ast",
        "hashlib",
        "json",
        "pathlib",
        "subprocess",
    }
