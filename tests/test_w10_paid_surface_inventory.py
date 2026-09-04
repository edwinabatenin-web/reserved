"""Machine-checkable W10-S5A route-inventory freshness evidence."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

import reserved


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "W10_S5A_PAID_SURFACE_INVENTORY.md"
START = "<!-- W10-S5A-INVENTORY-BEGIN -->"
END = "<!-- W10-S5A-INVENTORY-END -->"

CLASSIFICATIONS = {
    "public_infrastructure_auth_legal_support",
    "authenticated_product_candidate_pending_founder_decision",
    "billing_purchase_return_recovery_candidate",
    "internal_admin_unknown_requiring_reconciliation",
}
REGISTRATIONS = {"always", "hicbc_feature_enabled"}
GUARDS = {
    "none",
    "customer_session",
    "founder_session",
    "clerk_session_token",
    "nonproduction_only",
    "founder_password_and_rate_limit",
    "always_404",
}

EXPECTED_CLASSIFICATION_MEMBERS = {
    "public_infrastructure_auth_legal_support": {
        "api.health",
        "favicon",
        "static",
        "v2.auth_verify",
        "v2.demo_login",
        "v2.login",
        "v2.logout",
        "web.about",
        "web.dashboard",
        "web.early_access",
        "web.feedback",
        "web.future",
        "web.privacy",
        "web.robots_txt",
    },
    "authenticated_product_candidate_pending_founder_decision": {
        "hicbc.delete_estimate",
        "hicbc.index",
        "hicbc.link_accept",
        "hicbc.link_invite",
        "hicbc.link_page",
        "hicbc.link_revoke",
        "hicbc.result_json",
        "hicbc.save_estimate",
        "v2.connections",
        "v2.dashboard_view",
        "v2.index",
        "v2.invoices",
        "v2.invoices_seed",
        "v2.optimise_calculate",
        "v2.optimise_delete_scenario",
        "v2.optimise_save_scenario",
        "v2.optimise_view",
        "v2.review_queue",
        "v2.settings_page",
        "v2.transactions",
        "v2.transactions_seed",
        "v2.yapily_callback",
        "v2.yapily_connect",
        "v2.yapily_disconnect",
        "v2.yapily_refresh",
    },
    "billing_purchase_return_recovery_candidate": {
        "v2.billing_plan_selection",
        "v2.billing_plans",
    },
    "internal_admin_unknown_requiring_reconciliation": {
        "founder.dashboard",
        "founder.export_early_access",
        "founder.export_feedback",
        "founder.login",
        "founder.logout",
        "v2.sandbox_checklist",
        "web.calculate",
        "web.capital_gains",
        "web.connections",
        "web.settings",
        "web.tax_assurance",
    },
}

EXPECTED_GUARD_MEMBERS = {
    "none": {
        "api.health",
        "favicon",
        "static",
        "v2.login",
        "v2.logout",
        "web.about",
        "web.calculate",
        "web.connections",
        "web.dashboard",
        "web.early_access",
        "web.feedback",
        "web.future",
        "web.privacy",
        "web.robots_txt",
        "web.settings",
        "web.tax_assurance",
    },
    "customer_session": {
        "hicbc.delete_estimate",
        "hicbc.index",
        "hicbc.link_accept",
        "hicbc.link_invite",
        "hicbc.link_page",
        "hicbc.link_revoke",
        "hicbc.result_json",
        "hicbc.save_estimate",
        "v2.billing_plan_selection",
        "v2.billing_plans",
        "v2.connections",
        "v2.dashboard_view",
        "v2.index",
        "v2.invoices",
        "v2.invoices_seed",
        "v2.optimise_calculate",
        "v2.optimise_delete_scenario",
        "v2.optimise_save_scenario",
        "v2.optimise_view",
        "v2.review_queue",
        "v2.sandbox_checklist",
        "v2.settings_page",
        "v2.transactions",
        "v2.transactions_seed",
        "v2.yapily_callback",
        "v2.yapily_connect",
        "v2.yapily_disconnect",
        "v2.yapily_refresh",
    },
    "founder_session": {
        "founder.dashboard",
        "founder.export_early_access",
        "founder.export_feedback",
        "founder.logout",
    },
    "clerk_session_token": {"v2.auth_verify"},
    "nonproduction_only": {"v2.demo_login"},
    "founder_password_and_rate_limit": {"founder.login"},
    "always_404": {"web.capital_gains"},
}


def inventory():
    text = EVIDENCE.read_text(encoding="utf-8")
    payload = text.split(START, 1)[1].split(END, 1)[0].strip()
    assert payload.startswith("```json\n") and payload.endswith("```")
    return json.loads(payload.removeprefix("```json\n").removesuffix("```").strip())


def route_identity(route):
    return route["endpoint"], route["rule"], tuple(route["methods"])


def registered_routes(app):
    return {
        (
            rule.endpoint,
            rule.rule,
            tuple(sorted(rule.methods - {"HEAD", "OPTIONS"})),
        )
        for rule in app.url_map.iter_rules()
    }


def build_registry(monkeypatch, *, hicbc_enabled):
    monkeypatch.setenv("FLASK_ENV", "development")
    monkeypatch.delenv("CLERK_PUBLISHABLE_KEY", raising=False)
    monkeypatch.setenv("HICBC_ENABLED", "1" if hicbc_enabled else "0")
    monkeypatch.setattr(reserved, "init_db", lambda: None)
    return registered_routes(reserved.create_app())


def decorator_name(node):
    if isinstance(node, ast.Call):
        return decorator_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = decorator_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def decorated_endpoints(relative_path, blueprint_name, decorator):
    tree = ast.parse((ROOT / relative_path).read_text(encoding="utf-8"))
    return {
        f"{blueprint_name}.{node.name}"
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and decorator in {decorator_name(item) for item in node.decorator_list}
    }


def test_inventory_metadata_is_non_authorising_and_s5_remains_not_started():
    data = inventory()
    assert data["schema_version"] == "W10-S5A/2026-09-04/v1"
    assert data["integration_commit"] == (
        "6edf3cd6b96090f25036688e83da1d3b5295b098"
    )
    assert data["integration_tree"] == "0d77f1853cc22a8c1e923552425478b7b9155cb2"
    assert data["inventory_status"] == "evidence_only_no_paid_boundary_decision"
    assert data["s5_status"] == "not_started"
    assert data["paid_boundary_status"] == "unresolved_founder_decision"
    assert data["enforcement_changes"] is False


def test_bound_route_auth_and_csrf_sources_have_not_changed():
    for relative_path, expected_digest in inventory()["source_sha256"].items():
        actual_digest = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
        assert actual_digest == expected_digest, f"stale inventory source: {relative_path}"


def test_every_inventory_entry_has_one_exact_classification_and_unique_identity():
    routes = inventory()["routes"]
    identities = [route_identity(route) for route in routes]
    endpoints = [route["endpoint"] for route in routes]
    assert len(identities) == len(set(identities))
    assert len(endpoints) == len(set(endpoints))
    assert {route["classification"] for route in routes} <= CLASSIFICATIONS
    assert {route["registration"] for route in routes} <= REGISTRATIONS
    assert {route["guard"] for route in routes} <= GUARDS
    for route in routes:
        assert set(route) == {
            "endpoint",
            "rule",
            "methods",
            "registration",
            "guard",
            "csrf",
            "classification",
            "note",
        }
        assert route["classification"] in CLASSIFICATIONS
        assert type(route["note"]) is str and route["note"]
        assert route["methods"] == sorted(route["methods"])


def test_exact_endpoint_classifications_and_category_counts_are_bound():
    data = inventory()
    actual_members = {
        classification: {
            route["endpoint"] for route in data["routes"]
            if route["classification"] == classification
        }
        for classification in CLASSIFICATIONS
    }
    assert actual_members == EXPECTED_CLASSIFICATION_MEMBERS
    expected_counts = {
        classification: len(endpoints)
        for classification, endpoints in EXPECTED_CLASSIFICATION_MEMBERS.items()
    }
    assert expected_counts == {
        "public_infrastructure_auth_legal_support": 14,
        "authenticated_product_candidate_pending_founder_decision": 25,
        "billing_purchase_return_recovery_candidate": 2,
        "internal_admin_unknown_requiring_reconciliation": 11,
    }
    assert data["classification_counts"] == expected_counts


def test_exact_endpoint_guard_labels_are_bound():
    routes = inventory()["routes"]
    actual_members = {
        guard: {
            route["endpoint"] for route in routes if route["guard"] == guard
        }
        for guard in GUARDS
    }
    assert actual_members == EXPECTED_GUARD_MEMBERS


def test_inventory_exactly_matches_registry_with_optional_blueprint_off(monkeypatch):
    data = inventory()
    expected = {
        route_identity(route)
        for route in data["routes"]
        if route["registration"] == "always"
    }
    actual = build_registry(monkeypatch, hicbc_enabled=False)
    assert actual == expected
    assert len(actual) == data["route_counts"]["always"] == 44


def test_inventory_exactly_matches_registry_with_optional_blueprint_on(monkeypatch):
    data = inventory()
    expected = {route_identity(route) for route in data["routes"]}
    actual = build_registry(monkeypatch, hicbc_enabled=True)
    conditional = [
        route for route in data["routes"]
        if route["registration"] == "hicbc_feature_enabled"
    ]
    assert actual == expected
    assert len(conditional) == data["route_counts"]["hicbc_feature_enabled_additional"] == 8
    assert len(actual) == data["route_counts"]["hicbc_feature_enabled_total"] == 52


def test_customer_and_founder_decorator_guards_match_inventory():
    data = inventory()
    documented_customer = {
        route["endpoint"] for route in data["routes"]
        if route["guard"] == "customer_session"
    }
    source_customer = decorated_endpoints(
        "reserved/web/v2.py", "v2", "require_auth"
    ) | decorated_endpoints("reserved/web/hicbc.py", "hicbc", "require_auth")
    # These closure-bound plan routes apply require_auth programmatically and
    # remove the mutable __wrapped__ introspection pointer before registration.
    source_customer |= {"v2.billing_plans", "v2.billing_plan_selection"}
    assert documented_customer == source_customer

    documented_founder = {
        route["endpoint"] for route in data["routes"]
        if route["guard"] == "founder_session"
    }
    source_founder = decorated_endpoints(
        "reserved/web/founder.py", "founder", "require_founder"
    )
    assert documented_founder == source_founder


def test_csrf_exemptions_and_state_changing_methods_match_inventory():
    routes = inventory()["routes"]
    documented_exempt = {
        route["endpoint"] for route in routes if route["csrf"] == "exempt"
    }
    source_exempt = decorated_endpoints("reserved/web/v2.py", "v2", "csrf.exempt")
    assert documented_exempt == source_exempt

    state_changing = {"POST", "PUT", "PATCH", "DELETE"}
    for route in routes:
        has_state_change = bool(state_changing.intersection(route["methods"]))
        if has_state_change:
            assert route["csrf"] in {"global", "exempt"}
        else:
            assert route["csrf"] == "not_applicable"


def test_authentication_and_billing_candidate_routes_are_exact():
    by_endpoint = {route["endpoint"]: route for route in inventory()["routes"]}
    assert by_endpoint["v2.auth_verify"]["guard"] == "clerk_session_token"
    assert by_endpoint["v2.auth_verify"]["csrf"] == "exempt"
    assert by_endpoint["v2.demo_login"]["guard"] == "nonproduction_only"
    assert by_endpoint["founder.login"]["guard"] == (
        "founder_password_and_rate_limit"
    )
    assert by_endpoint["web.capital_gains"]["guard"] == "always_404"

    billing_candidates = {
        route["endpoint"] for route in inventory()["routes"]
        if route["classification"] == "billing_purchase_return_recovery_candidate"
    }
    assert billing_candidates == {"v2.billing_plans", "v2.billing_plan_selection"}
    assert all(
        by_endpoint[endpoint]["guard"] == "customer_session"
        for endpoint in billing_candidates
    )


def test_ambiguous_internal_and_legacy_routes_remain_reconciliation_only():
    reconciliation = {
        route["endpoint"] for route in inventory()["routes"]
        if route["classification"] == "internal_admin_unknown_requiring_reconciliation"
    }
    assert reconciliation == {
        "web.calculate",
        "web.capital_gains",
        "web.connections",
        "web.settings",
        "web.tax_assurance",
        "founder.dashboard",
        "founder.export_early_access",
        "founder.export_feedback",
        "founder.login",
        "founder.logout",
        "v2.sandbox_checklist",
    }


def test_evidence_contains_exact_minimal_founder_question_and_no_boundary_claim():
    text = EVIDENCE.read_text(encoding="utf-8")
    assert "The exact minimal question is:" in text
    assert "If not, identify the" in text
    assert "exact route exceptions and intended treatment." in text
    assert "It does not decide which customer" in text
    assert "W10-S5 remains **not started**" in text
    assert "no registered subscription checkout" in text
    assert "does not approve the recommended default" in text


@pytest.mark.parametrize(
    "forbidden",
    (
        "paid_entitlement_granted",
        "paid_boundary_approved",
        "s5_complete",
        "launch_ready",
    ),
)
def test_machine_inventory_contains_no_approval_or_entitlement_outcome(forbidden):
    assert forbidden not in json.dumps(inventory(), sort_keys=True).casefold()
