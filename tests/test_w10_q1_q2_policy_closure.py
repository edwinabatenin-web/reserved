"""Deterministic checks for the detached W10 Q1/Q2 policy closure."""

from __future__ import annotations

import ast
import copy
import hashlib
import pickle
import subprocess
from pathlib import Path

import pytest

import reserved.billing.q1_q2_policy_closure as subject


ROOT = Path(__file__).resolve().parents[1]
BASE = "030da8a2928473b9b5af35a158ea6ad5c5ad8e49"
BASE_TREE = "7e7430c7f3fe3dd80aeec6c06a8860f48728b520"
SOURCE = ROOT / "reserved" / "billing" / "q1_q2_policy_closure.py"
EVIDENCE = ROOT / "docs" / "W10_S2F_Q1_Q2_POLICY_CLOSURE.md"
ALLOWED_CANDIDATE_PATHS = {
    "docs/W10_S2F_Q1_Q2_POLICY_CLOSURE.md",
    "reserved/billing/q1_q2_policy_closure.py",
    "tests/test_w10_q1_q2_policy_closure.py",
}
ACCEPTED_SOURCES = {
    "FOUNDER_DECISIONS.md": (
        "03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4"
    ),
    "reserved/billing/fail_closed_launch_defaults.py": (
        "cd72be19d8180a52f2e09fec56cc3219347059b025ceb3f12086d7d8dde40715"
    ),
    "docs/W10_S2B_FAIL_CLOSED_LAUNCH_DEFAULTS.md": (
        "617ca21d3555bef8944f9d4173c0dc432816817fb2a73d9f1566380bbf8b9703"
    ),
    "docs/W10_S2C_POLICY_EVIDENCE_DOSSIER.md": (
        "838e6c649f9925e86aca280da6917cc7e650860880204cf06b34a8fc4aa2572f"
    ),
    "docs/W10_S5A_PAID_SURFACE_INVENTORY.md": (
        "5d1d957f53edf04898df8064ee5825a5ab9a55091daf2fed8b292f54db596601"
    ),
    "docs/W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md": (
        "4ba7324883e6aa27081e47ffa6f1c0a1fde99a5f175375a4aae289ce5b7a5917"
    ),
    "docs/W10_S5C_INTERNAL_ROUTE_HARDENING_EVIDENCE.md": (
        "221b244e687611dfa3e55e67051cb9ffab59ef6fcd9f02d8c5c865611439d1f5"
    ),
}


def git_text(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


def projection_tuple():
    return subject.project_q1_q2_policy_closure(subject.Q1_Q2_POLICY_CLOSURE)


def projection():
    return dict(projection_tuple())


def exact_builtin_walk(value):
    if type(value) is tuple:
        for item in value:
            exact_builtin_walk(item)
        return
    assert type(value) in (str, int, bool)


def test_candidate_is_confined_to_three_new_non_colliding_paths():
    changed = git_text("diff", "--name-only", "HEAD").splitlines()
    untracked = git_text("ls-files", "--others", "--exclude-standard").splitlines()
    assert set(changed + untracked) <= ALLOWED_CANDIDATE_PATHS


def test_exact_authoritative_source_commit_tree_and_hashes():
    projected = projection()
    assert projected["source_commit"] == BASE
    assert projected["source_tree"] == BASE_TREE
    assert git_text("rev-parse", f"{BASE}^{{tree}}") == BASE_TREE
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE, "HEAD"],
        cwd=ROOT,
        check=True,
    )

    projected_sources = {
        relative_path: sha256
        for _, relative_path, sha256 in projected["accepted_sources"]
    }
    assert projected_sources == ACCEPTED_SOURCES
    for relative_path, expected_hash in ACCEPTED_SOURCES.items():
        blob = subprocess.run(
            ["git", "show", f"{BASE}:{relative_path}"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
        assert hashlib.sha256(blob).hexdigest() == expected_hash


def test_projection_is_exact_detached_immutable_builtins():
    projected = projection()
    exact_builtin_walk(projection_tuple())
    first = subject.project_q1_q2_policy_closure(subject.Q1_Q2_POLICY_CLOSURE)
    second = subject.project_q1_q2_policy_closure(subject.Q1_Q2_POLICY_CLOSURE)
    assert first == second
    assert first is not second
    assert projected["assurance_status"] == (
        "detached_policy_contract_not_runtime_provider_or_launch_assurance"
    )


def test_policy_partition_closes_only_q1_q2_and_leaves_q3_open():
    projected = projection()
    denominator = projected["source_policy_denominator"]
    partition = (
        projected["previously_closed_policy_keys"]
        + projected["newly_closed_policy_keys"]
        + projected["remaining_policy_keys"]
    )
    assert len(denominator) == 15
    assert len(partition) == 15
    assert set(partition) == set(denominator)
    assert projected["newly_closed_policy_keys"] == (
        "refunds",
        "paid_access_surface",
    )
    assert projected["remaining_policy_keys"] == (
        "tax_invoicing_and_additional_presentation",
        "billing_account_recovery",
        "post_settlement_dispute_chargeback_reversal_consequences",
    )
    assert subject.NEWLY_CLOSED_POLICY_KEYS == projected["newly_closed_policy_keys"]
    assert subject.REMAINING_POLICY_KEYS == projected["remaining_policy_keys"]
    assert projected["policy_status"] == "policy_incomplete_three_keys_remaining"
    assert projected["q3_status"] == "unresolved_requires_founder_decision"


def test_refund_baseline_has_no_discretionary_or_runtime_action():
    refund = dict(projection()["refund_policy"])
    assert refund == {
        "scope": "october_fail_closed_baseline",
        "discretionary_refund_promise": False,
        "automated_refunds_enabled": False,
        "support_discretionary_refunds_enabled": False,
        "mandatory_statutory_and_consumer_rights_override": True,
        "mandatory_remedy_requires_accepted_specialist_treatment": True,
        "legally_required_request_escalation_path_required": True,
        "request_must_be_authenticated_to_current_reserved_owner": True,
        "payment_subscription_and_period_binding_required": True,
        "exact_money_and_aggregate_limit_validation_required": True,
        "idempotency_required": True,
        "provider_outcome_reconciliation_required": True,
        "distinct_outcome_states": (
            "requested",
            "pending",
            "requires_action",
            "succeeded",
            "failed",
        ),
        "pending_or_failed_is_succeeded": False,
        "provider_refund_observation_direct_entitlement_effect": False,
        "access_consequence": (
            "not_invented_apply_only_separately_accepted_legal_policy_outcome"
        ),
        "refund_action_implemented": False,
    }


def test_paid_surface_boundary_follows_paid_launch_without_free_product_exception():
    paid = dict(projection()["paid_surface_policy"])
    assert paid == {
        "scope": "october_paid_subscription_without_free_tier",
        "inventory_source": "accepted_w10_s5a_exact_inventory",
        "authenticated_product_candidate_pending_founder_decision": (
            "paid_entitlement_required"
        ),
        "public_infrastructure_auth_legal_support": (
            "outside_paid_gate_existing_controls_preserved"
        ),
        "billing_purchase_return_recovery_candidate": (
            "outside_paid_gate_existing_controls_preserved"
        ),
        "required_exit_and_privacy_controls": (
            "outside_paid_gate_existing_controls_preserved"
        ),
        "internal_admin_unknown_requiring_reconciliation": (
            "separate_or_closed_exactly_as_reconciled_by_s5b_and_s5c"
        ),
        "customer_product_free_exception_created": False,
        "client_side_hiding_is_enforcement": False,
        "future_server_side_entitlement_enforcement_required": True,
        "runtime_paid_entitlement_enforcement_implemented": False,
    }


def test_authority_basis_is_engineering_not_new_founder_scope():
    basis = dict(projection()["authority_basis"])
    assert basis == {
        "founder_decision_lineage": ("FD-W10-001", "FD-W10-003", "FD-OA-001"),
        "classification": (
            "ordinary_engineering_policy_under_paid_launch_and_no_free_tier_authority"
        ),
        "new_or_changed_product_scope": False,
        "provider_defaults_are_policy_authority": False,
        "provider_observations_are_entitlement_decisions": False,
    }
    assert "FD-W10-004" not in SOURCE.read_text(encoding="utf-8")


def test_q3_and_runtime_actions_remain_explicitly_excluded():
    excluded = projection()["scope_exclusions"]
    assert "post_settlement_dispute_chargeback_reversal_consequence" in excluded
    assert "provider_or_refund_action" in excluded
    assert "runtime_paid_access_enforcement" in excluded
    assert "database_persistence_or_migration" in excluded
    assert "founder_production_release_or_go_live_authority" in excluded
    assert "post_settlement_policy" not in projection()


def test_handle_construction_forgery_copy_and_pickle_fail_closed():
    handle = subject.Q1_Q2_POLICY_CLOSURE
    with pytest.raises(TypeError, match="producer-issued"):
        subject.Q1Q2PolicyClosureHandle()
    forged = object.__new__(subject.Q1Q2PolicyClosureHandle)
    with pytest.raises(ValueError, match="not producer-issued"):
        subject.validate_q1_q2_policy_closure(forged)
    with pytest.raises(TypeError, match="exact Q1/Q2 policy handle"):
        subject.validate_q1_q2_policy_closure(object())
    with pytest.raises(TypeError, match="not copyable"):
        copy.copy(handle)
    with pytest.raises(TypeError, match="not copyable"):
        copy.deepcopy(handle)
    with pytest.raises(TypeError, match="not serialisable"):
        pickle.dumps(handle)


def test_saved_protocol_resists_public_rebinding(monkeypatch):
    handle = subject.Q1_Q2_POLICY_CLOSURE
    validate = subject.validate_q1_q2_policy_closure
    project = subject.project_q1_q2_policy_closure
    expected = project(handle)
    forged = object.__new__(subject.Q1Q2PolicyClosureHandle)

    monkeypatch.setattr(subject, "CONTRACT_VERSION", "forged")
    monkeypatch.setattr(subject, "NEWLY_CLOSED_POLICY_KEYS", ())
    monkeypatch.setattr(subject, "REMAINING_POLICY_KEYS", ())
    monkeypatch.setattr(subject, "Q1_Q2_POLICY_CLOSURE", forged)
    monkeypatch.setattr(subject, "validate_q1_q2_policy_closure", lambda value: ())
    monkeypatch.setattr(subject, "project_q1_q2_policy_closure", lambda value: ())
    monkeypatch.setattr(subject, "tuple", list, raising=False)
    monkeypatch.setattr(subject, "bool", str, raising=False)
    monkeypatch.setattr(
        subject.Q1Q2PolicyClosureHandle,
        "__new__",
        staticmethod(lambda cls, *args, **kwargs: forged),
    )

    assert project(handle) == expected
    assert validate(handle) == expected
    with pytest.raises(ValueError, match="not producer-issued"):
        validate(forged)


def test_module_is_import_inert_and_has_no_runtime_dependencies():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert len(imports) == 1
    assert isinstance(imports[0], ast.ImportFrom)
    assert imports[0].module == "__future__"
    forbidden_calls = {
        "open",
        "exec",
        "eval",
        "compile",
        "__import__",
    }
    called_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called_names.isdisjoint(forbidden_calls)
    text = SOURCE.read_text(encoding="utf-8")
    for forbidden in ("stripe", "requests", "httpx", "sqlalchemy", "flask"):
        assert forbidden not in text.lower()


def test_evidence_records_scope_hash_and_map_delta():
    text = EVIDENCE.read_text(encoding="utf-8")
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert source_hash in text
    assert BASE in text
    assert BASE_TREE in text
    assert "Q1 and Q2 close as ordinary engineering policies" in text
    assert "Q3 remains explicitly open" in text
    assert "three policy keys remain unresolved" in text
    assert "The live completion map is intentionally unchanged" in text
    assert "No runtime paid-entitlement enforcement" in text
