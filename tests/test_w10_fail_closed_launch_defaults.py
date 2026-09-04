"""Adversarial tests for the contract-only W10-S2B launch defaults."""

from __future__ import annotations

import ast
import builtins
import copy
import gc
import hashlib
import inspect
import pickle
import subprocess
import weakref
from pathlib import Path
from types import FunctionType

import pytest

import reserved.billing.fail_closed_launch_defaults as subject


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reserved" / "billing" / "fail_closed_launch_defaults.py"

EXPECTED_DEFAULT_KEYS = (
    "promotion_and_discount_mechanics",
    "partner_offer_handling",
    "plan_changes_and_proration",
    "manual_overrides",
)
EXPECTED_UNRESOLVED_KEYS = (
    "refunds",
    "tax_invoicing_and_additional_presentation",
    "paid_access_surface",
    "billing_account_recovery",
    "post_settlement_dispute_chargeback_reversal_consequences",
)
EXPECTED_SOURCES = (
    (
        "W10-S1",
        "9e8f94a9906f0c9d5c85b47223d20c34be499e1c",
        "reserved/billing/contracts.py",
        "9c5dce7a81652d58562ca339def95fba7cbb2d1c02f965618ebd8f40bcad202b",
        "FD-W10-001/2026-09-02/v1",
    ),
    (
        "W10-S2A",
        "5464bfac7bec6b3456d1895b2355a7e8ce86859b",
        "reserved/billing/provider_lifecycle_authority.py",
        "fc21c3a0f9d8d7eeb9a06bcbf5fc4a418568fe06aa5f65f47c325d8ecfde834a",
        "FD-W10-002+FD-W10-003/2026-09-04/v1",
    ),
    (
        "W10-S3A",
        "94bd87f019dc226ec8c73f32515229189500cf06",
        "reserved/billing/entitlement_core.py",
        "b46b797614b57047e64f6f6597b1c788b9ab15db90653b07add31b4bbb03cb3b",
        "reserved-w10-entitlement-transition/1.0",
    ),
    (
        "W10-S3B",
        "5bc29bcb30c95ea7a5a9430104653b366d709eb6",
        "reserved/billing/event_inbox_contract.py",
        "4dc0b6bb8b109854531dc1b9d492255e98dca805822cd5e0257f0fdf9b0ca8ed",
        "reserved-w10-event-inbox-contract/1.0",
    ),
    (
        "W10-S4A",
        "2ad4a63dd1f10ba38859050b47245c28390667d8",
        "reserved/billing/stripe_disabled_first_contract.py",
        "87a84c5ec77f25e12667b5466052b4a84ee6e01a6b075df643202d95aec98638",
        "W10-S4A/2026-09-04/v1",
    ),
)


def projection_tuple():
    return subject.project_fail_closed_launch_defaults(
        subject.FAIL_CLOSED_LAUNCH_DEFAULTS
    )


def projection():
    return dict(projection_tuple())


def exact_builtin_walk(value):
    if type(value) is tuple:
        for item in value:
            exact_builtin_walk(item)
        return
    assert type(value) in (str, int, bool)


def test_exact_contract_identity_and_accepted_source_hashes():
    projected = projection()
    assert projected["contract_version"] == "W10-S2B/2026-09-04/v1"
    assert projected["integration_head"] == (
        "5bc29bcb30c95ea7a5a9430104653b366d709eb6"
    )
    assert projected["accepted_sources"] == EXPECTED_SOURCES
    for _, accepted_commit, relative_path, expected_hash, _ in EXPECTED_SOURCES:
        blob = subprocess.run(
            ["git", "show", f"{accepted_commit}:{relative_path}"], cwd=ROOT,
            check=True, stdout=subprocess.PIPE,
        ).stdout
        actual = hashlib.sha256(blob).hexdigest()
        assert actual == expected_hash
    assert hashlib.sha256((ROOT / "reserved/billing/entitlement_core.py").read_bytes()).hexdigest() == (
        "201c92c1093b663b786a5e49a1c2ca0d714f3fe6fdaebf18c0c7d486ef25f415"
    )


def test_exact_policy_partition_remains_incomplete_with_five_unresolved_keys():
    projected = projection()
    assert projected["fail_closed_policy_keys"] == EXPECTED_DEFAULT_KEYS
    assert projected["unresolved_policy_keys"] == EXPECTED_UNRESOLVED_KEYS
    assert subject.FAIL_CLOSED_POLICY_KEYS == EXPECTED_DEFAULT_KEYS
    assert subject.UNRESOLVED_POLICY_KEYS == EXPECTED_UNRESOLVED_KEYS
    assert projected["policy_status"] == "policy_incomplete"
    denominator = projected["source_policy_denominator"]
    partition = (
        projected["founder_settled_policy_keys"]
        + projected["fail_closed_policy_keys"]
        + projected["unresolved_policy_keys"]
    )
    assert len(denominator) == 15
    assert len(partition) == 15
    assert set(partition) == set(denominator)


def test_four_defaults_are_engineering_defaults_not_new_founder_decisions():
    basis = dict(projection()["authority_basis"])
    assert basis["founder_decision_lineage"] == (
        "FD-W10-001",
        "FD-W10-002",
        "FD-W10-003",
    )
    assert basis["classification"] == (
        "ordinary_engineering_fail_closed_defaults_not_separately_founder_settled"
    )
    assert basis["provider_defaults_are_policy_authority"] is False
    assert basis["provider_observations_are_entitlement_decisions"] is False
    assert "FD-W10-004" not in SOURCE.read_text(encoding="utf-8")


def test_promotions_are_reserved_as_capability_but_completely_inactive():
    defaults = dict(projection()["engineering_defaults"])
    promotions = dict(defaults["promotion_and_discount_mechanics"])
    assert promotions == {
        "capability_reserved": True,
        "active": False,
        "promotion_codes_enabled": False,
        "promotion_codes": (),
        "eligibility_rules": (),
        "duration_rules": (),
        "stacking_rules": (),
        "discounted_prices": (),
        "direct_entitlement_effect": False,
    }


def test_partner_offers_are_disabled_and_unsupported():
    partner = dict(dict(projection()["engineering_defaults"])["partner_offer_handling"])
    assert partner == {
        "enabled": False,
        "supported": False,
        "offer_definitions": (),
        "marketplace_or_reseller_path_enabled": False,
        "direct_entitlement_effect": False,
    }


def test_mid_cycle_plan_changes_and_proration_are_disabled():
    plan_changes = dict(
        dict(projection()["engineering_defaults"])["plan_changes_and_proration"]
    )
    assert plan_changes == {
        "scope": "ordinary_product_customer_plan_change_and_cancellation_behaviour",
        "mid_cycle_plan_changes_enabled": False,
        "proration_enabled": False,
        "immediate_cancellation_enabled": False,
        "paid_period_end_cancellation_preserved": True,
        "paid_period_end_cancellation_outcome": (
            "stop_future_renewal_keep_access_through_already_paid_period"
        ),
        "mandatory_statutory_and_consumer_rights_override": True,
        "direct_entitlement_effect": False,
    }


def test_ordinary_cancellation_default_never_displaces_mandatory_rights():
    plan_changes = dict(
        dict(projection()["engineering_defaults"])["plan_changes_and_proration"]
    )
    assert plan_changes["scope"] == (
        "ordinary_product_customer_plan_change_and_cancellation_behaviour"
    )
    assert plan_changes["immediate_cancellation_enabled"] is False
    assert plan_changes["mandatory_statutory_and_consumer_rights_override"] is True
    assert "refunds" in projection()["unresolved_policy_keys"]


def test_manual_entitlement_override_is_disabled_and_corrections_do_not_entitle():
    overrides = dict(dict(projection()["engineering_defaults"])["manual_overrides"])
    assert overrides == {
        "manual_entitlement_override_enabled": False,
        "direct_entitlement_mutation_enabled": False,
        "permitted_correction_path": "append_only_observation_and_reconciliation",
        "correction_direct_entitlement_effect": False,
    }


def test_scope_exclusions_are_exact_and_contract_claim_is_bounded():
    projected = projection()
    assert projected["scope_exclusions"] == (
        "provider_sdk_or_network",
        "credentials_or_provider_activation",
        "database_persistence_or_io",
        "route_or_paid_access_enforcement",
        "entitlement_mutation",
        "refund_policy_or_action",
        "tax_invoice_or_additional_vat_outcome",
        "billing_account_recovery",
        "post_settlement_access_consequence",
    )
    assert projected["assurance_status"] == (
        "contract_only_not_s2_completion_or_runtime_implementation"
    )


def test_projection_is_detached_exact_immutable_builtins_only():
    first = projection_tuple()
    second = projection_tuple()
    assert first == second
    assert first is not second
    exact_builtin_walk(first)
    with pytest.raises(TypeError):
        first[0] = ("contract_version", "forged")
    forged_view = dict(first)
    forged_view["policy_status"] = "policy_inputs_complete"
    assert projection()["policy_status"] == "policy_incomplete"


def test_handles_are_producer_issued_and_exact_type_only():
    with pytest.raises(TypeError, match="producer-issued"):
        subject.FailClosedLaunchDefaultsHandle()
    forged = object.__new__(subject.FailClosedLaunchDefaultsHandle)
    with pytest.raises(ValueError, match="producer-issued"):
        subject.validate_fail_closed_launch_defaults(forged)

    class Forged(subject.FailClosedLaunchDefaultsHandle):
        pass

    with pytest.raises(TypeError, match="exact producer-issued"):
        subject.validate_fail_closed_launch_defaults(object.__new__(Forged))


def test_authoritative_copy_and_ordinary_copy_issue_fresh_valid_handles():
    original = subject.FAIL_CLOSED_LAUNCH_DEFAULTS
    clones = (
        subject.copy_fail_closed_launch_defaults(original),
        copy.copy(original),
        copy.deepcopy(original),
    )
    for clone in clones:
        assert clone is not original
        assert subject.validate_fail_closed_launch_defaults(clone) == projection_tuple()


def test_pickle_and_rebound_pickle_protocol_never_create_authority(monkeypatch):
    original = subject.FAIL_CLOSED_LAUNCH_DEFAULTS
    with pytest.raises(TypeError, match="not serialisable"):
        pickle.dumps(original)

    monkeypatch.setattr(
        subject.FailClosedLaunchDefaultsHandle,
        "__reduce_ex__",
        lambda self, protocol: (object, ()),
    )
    reloaded = pickle.loads(pickle.dumps(original))
    with pytest.raises(TypeError, match="exact producer-issued"):
        subject.validate_fail_closed_launch_defaults(reloaded)


def test_saved_protocol_resists_public_global_and_class_rebinding(monkeypatch):
    handle = subject.FAIL_CLOSED_LAUNCH_DEFAULTS
    validate = subject.validate_fail_closed_launch_defaults
    project = subject.project_fail_closed_launch_defaults
    copy_contract = subject.copy_fail_closed_launch_defaults
    expected = project(handle)
    forged = object.__new__(subject.FailClosedLaunchDefaultsHandle)

    monkeypatch.setattr(subject, "CONTRACT_VERSION", "forged")
    monkeypatch.setattr(subject, "FAIL_CLOSED_POLICY_KEYS", ())
    monkeypatch.setattr(subject, "UNRESOLVED_POLICY_KEYS", ())
    monkeypatch.setattr(subject, "FAIL_CLOSED_LAUNCH_DEFAULTS", object())
    monkeypatch.setattr(subject, "validate_fail_closed_launch_defaults", lambda value: ())
    monkeypatch.setattr(subject, "project_fail_closed_launch_defaults", lambda value: ())
    monkeypatch.setattr(subject, "tuple", list, raising=False)
    monkeypatch.setattr(subject, "bool", str, raising=False)
    monkeypatch.setattr(
        subject.FailClosedLaunchDefaultsHandle,
        "__new__",
        staticmethod(lambda cls, *args, **kwargs: forged),
    )
    monkeypatch.setattr(
        subject.FailClosedLaunchDefaultsHandle,
        "policy_status",
        property(lambda self: "policy_inputs_complete"),
        raising=False,
    )
    monkeypatch.setattr(
        subject.FailClosedLaunchDefaultsHandle,
        "__copy__",
        lambda self: forged,
    )

    assert project(handle) == expected
    assert dict(project(handle))["policy_status"] == "policy_incomplete"
    clone = copy_contract(handle)
    assert clone is not forged
    assert validate(clone) == expected
    with pytest.raises(ValueError, match="producer-issued"):
        validate(copy.copy(handle))


def _closure_objects(root):
    pending = [root]
    seen = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        if isinstance(current, FunctionType) and current.__closure__:
            pending.extend(cell.cell_contents for cell in current.__closure__)


def test_registry_rebinding_or_entry_corruption_fails_closed():
    handle = subject.FAIL_CLOSED_LAUNCH_DEFAULTS
    project = subject.project_fail_closed_launch_defaults
    registry = next(
        value
        for value in _closure_objects(project)
        if (
            type(value) is dict
            and id(handle) in value
            and type(value[id(handle)]) is tuple
            and type(value[id(handle)][0]) is tuple
        )
    )
    original_binding = registry[id(handle)]
    forged_binding = tuple(item for item in original_binding)
    assert forged_binding == original_binding
    assert forged_binding is not original_binding
    try:
        registry[id(handle)] = forged_binding
        with pytest.raises(ValueError, match="registry binding"):
            project(handle)
    finally:
        registry[id(handle)] = original_binding
    assert project(handle) == projection_tuple()


def _contract_registries():
    handle = subject.FAIL_CLOSED_LAUNCH_DEFAULTS
    dictionaries = [
        value
        for value in _closure_objects(subject.project_fail_closed_launch_defaults)
        if type(value) is dict and id(handle) in value
    ]
    registry = next(value for value in dictionaries if type(value[id(handle)][0]) is tuple)
    live = next(
        value
        for value in dictionaries
        if isinstance(value[id(handle)][0], weakref.ReferenceType)
    )
    return registry, live


def test_copy_registry_returns_to_single_baseline_entry_after_collection():
    handle = subject.FAIL_CLOSED_LAUNCH_DEFAULTS
    registry, live = _contract_registries()
    # The two build-time ordinary-copy probes must already have cleaned up.
    assert set(registry) == {id(handle)}
    assert set(live) == {id(handle)}
    gc.collect()
    assert set(registry) == {id(handle)}
    assert set(live) == {id(handle)}

    copies = [subject.copy_fail_closed_launch_defaults(handle) for _ in range(1000)]
    assert len(registry) == 1001
    assert len(live) == 1001
    del copies
    gc.collect()

    assert set(registry) == {id(handle)}
    assert set(live) == {id(handle)}
    assert subject.project_fail_closed_launch_defaults(handle) == projection_tuple()


def test_stale_weakref_callback_cannot_remove_newer_generation_for_same_id():
    handle = subject.FAIL_CLOSED_LAUNCH_DEFAULTS
    registry, live = _contract_registries()
    identity = id(handle)
    original_live = live[identity]
    original_binding = registry[identity]
    stale_reference = original_live[0]
    stale_callback = stale_reference.__callback__
    assert stale_callback is not None

    newer = subject.copy_fail_closed_launch_defaults(handle)
    newer_identity = id(newer)
    newer_live = live[newer_identity]
    newer_binding = registry[newer_identity]
    try:
        # Simulate id reuse by installing a later generation at the old id.
        live[identity] = newer_live
        registry[identity] = newer_binding
        stale_callback(stale_reference)
        assert live[identity] is newer_live
        assert registry[identity] is newer_binding
    finally:
        live[identity] = original_live
        registry[identity] = original_binding
        del newer
        gc.collect()

    assert subject.project_fail_closed_launch_defaults(handle) == projection_tuple()


def test_saved_projector_does_not_trust_exported_validator_code():
    validate = subject.validate_fail_closed_launch_defaults
    project = subject.project_fail_closed_launch_defaults
    original_code = validate.__code__

    def make_forged_code():
        captured = (("policy_status", "policy_inputs_complete"),)

        def forged(value):
            captured
            return (("policy_status", "policy_inputs_complete"),)

        return forged.__code__

    try:
        validate.__code__ = make_forged_code()
        assert dict(validate(object()))["policy_status"] == "policy_inputs_complete"
        with pytest.raises(TypeError, match="exact producer-issued"):
            project(object())
        assert dict(project(subject.FAIL_CLOSED_LAUNCH_DEFAULTS))["policy_status"] == (
            "policy_incomplete"
        )
    finally:
        validate.__code__ = original_code


def test_supported_protocol_performs_no_file_io(monkeypatch):
    handle = subject.FAIL_CLOSED_LAUNCH_DEFAULTS
    project = subject.project_fail_closed_launch_defaults
    copy_contract = subject.copy_fail_closed_launch_defaults

    def forbidden_open(*args, **kwargs):
        raise AssertionError("contract attempted file I/O")

    monkeypatch.setattr(builtins, "open", forbidden_open)
    assert dict(project(handle))["policy_status"] == "policy_incomplete"
    assert project(copy_contract(handle)) == project(handle)


def test_module_has_no_runtime_provider_persistence_or_route_dependencies():
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported_roots <= {"__future__", "copy", "weakref"}
    assert not imported_roots.intersection(
        {"stripe", "requests", "httpx", "socket", "sqlite3", "flask", "os"}
    )
    public_callables = {
        name for name in subject.__all__ if callable(getattr(subject, name))
    }
    assert public_callables == {
        "FailClosedLaunchDefaultsHandle",
        "validate_fail_closed_launch_defaults",
        "project_fail_closed_launch_defaults",
        "copy_fail_closed_launch_defaults",
    }
    assert tuple(inspect.signature(subject.project_fail_closed_launch_defaults).parameters) == (
        "value",
    )
