"""Adversarial contract tests for the W10-S2A authority subset."""

from __future__ import annotations

import ast
import copy
import hashlib
import inspect
import pickle
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

import pytest

import reserved.billing as s1_package
from reserved.billing import contracts as s1
from reserved.billing import provider_lifecycle_authority as subject


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "reserved/billing/provider_lifecycle_authority.py"
MAP = REPO_ROOT / "docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md"

EXPECTED_SETTLED = (
    "billing_provider",
    "renewal_behaviour",
    "cancellation_timing",
    "failed_payment_and_grace",
    "entitlement_start_and_end",
    "trial_and_free_access_if_applicable",
)
EXPECTED_UNRESOLVED = (
    "refunds",
    "tax_invoicing_and_additional_presentation",
    "promotion_and_discount_mechanics",
    "partner_offer_handling",
    "paid_access_surface",
    "plan_changes_and_proration",
    "billing_account_recovery",
    "manual_overrides",
    "post_settlement_dispute_chargeback_reversal_consequences",
)


def _projection():
    return subject.project_provider_lifecycle_authority(
        subject.PROVIDER_LIFECYCLE_AUTHORITY
    )


def _as_dict(items):
    return dict(items)


def _walk_exact_builtins(value):
    assert type(value) in (tuple, str, int, bool)
    if type(value) is tuple:
        for item in value:
            _walk_exact_builtins(item)


def test_exact_authority_identity_and_corrected_s1_binding():
    projection = _as_dict(_projection())
    assert projection["authority_version"] == "FD-W10-002+FD-W10-003/2026-09-04/v1"
    assert projection["source_authority_version"] == s1.AUTHORITY_VERSION
    assert projection["source_integration_commit"] == (
        "9e8f94a9906f0c9d5c85b47223d20c34be499e1c"
    )
    assert projection["source_contract_sha256"] == hashlib.sha256(
        Path(s1.__file__).read_bytes()
    ).hexdigest()
    assert projection["founder_decisions"] == (
        ("FD-W10-001", "2026-09-02"),
        ("FD-W10-002", "2026-09-04"),
        ("FD-W10-003", "2026-09-04"),
    )
    s1.validate_billing_authority(s1.INITIAL_BILLING_AUTHORITY)
    s1.validate_billing_authority(
        s1.project_billing_authority(s1.INITIAL_BILLING_AUTHORITY)
    )


def test_exact_six_settled_and_nine_unresolved_keys_keep_register_incomplete():
    projection = _as_dict(_projection())
    assert subject.SETTLED_POLICY_KEYS == EXPECTED_SETTLED
    assert subject.UNRESOLVED_POLICY_KEYS == EXPECTED_UNRESOLVED
    assert projection["settled_policy_keys"] == EXPECTED_SETTLED
    assert projection["unresolved_policy_keys"] == EXPECTED_UNRESOLVED
    assert projection["policy_status"] == "policy_incomplete"
    assert len(EXPECTED_SETTLED) == 6
    assert len(EXPECTED_UNRESOLVED) == 9
    assert _as_dict(_projection())["source_policy_denominator"] == tuple(
        key.value for key in s1.REQUIRED_BILLING_POLICY_KEYS
    )
    assert set(EXPECTED_SETTLED + EXPECTED_UNRESOLVED) == set(
        _as_dict(_projection())["source_policy_denominator"]
    )


def test_provider_is_exact_provisional_capability_boundary_not_connect():
    provider = _as_dict(_as_dict(_projection())["provider"])
    assert provider == {
        "family": "stripe_subscription",
        "status": "provisional_disabled_first",
        "capabilities": ("billing", "checkout", "customer_portal"),
        "excluded": ("stripe_connect",),
        "portable_provider_boundary_required": True,
    }


def test_paid_lifecycle_and_recovery_state_are_exact_and_distinct():
    lifecycle = _as_dict(_as_dict(_projection())["lifecycle"])
    assert lifecycle["initial_access"] == "after_verified_successful_initial_payment_only"
    assert lifecycle["renewal"] == "automatic_for_selected_paid_plan"
    assert lifecycle["cancellation"] == (
        "stop_future_renewal_keep_access_through_already_paid_period"
    )
    assert lifecycle["ordinary_paid_state"] == "paid"
    assert lifecycle["recovery_state"] == "payment_recovery"
    assert lifecycle["recovery_state"] != lifecycle["ordinary_paid_state"]
    assert lifecycle["trial"] == "no_october_free_trial"
    assert lifecycle["free_tier"] == "no_october_free_tier"


def test_recovery_is_first_verified_failure_plus_exactly_seven_days_non_extendable():
    lifecycle = _as_dict(_as_dict(_projection())["lifecycle"])
    assert type(lifecycle["recovery_days"]) is int
    assert lifecycle["recovery_days"] == 7
    assert lifecycle["recovery_deadline_origin"] == (
        "first_verified_failed_renewal_observation"
    )
    assert lifecycle["recovery_deadline_extendable"] is False
    assert lifecycle["duplicate_or_repeated_failure_effect"] == (
        "must_not_extend_recovery_deadline"
    )
    assert lifecycle["unresolved_recovery_expiry_effect"] == "suspend_ordinary_access"


@pytest.mark.parametrize(
    "caller_value",
    [6, 8, True, False, datetime(2026, 9, 11, tzinfo=timezone.utc)],
)
def test_callers_cannot_construct_or_select_recovery_values(caller_value):
    with pytest.raises(TypeError, match="producer-issued"):
        subject.ProviderLifecycleAuthorityHandle(caller_value)


def test_provider_observations_never_become_entitlement_flags():
    lifecycle = _as_dict(_as_dict(_projection())["lifecycle"])
    assert lifecycle["provider_status_is_entitlement"] is False
    assert lifecycle["untrusted_observation_effect"] == (
        "fail_closed_reconciliation_input_never_access_grant"
    )


def test_projection_contains_exact_immutable_builtins_only():
    first = _projection()
    second = _projection()
    assert first == second
    assert first is not second
    _walk_exact_builtins(first)
    with pytest.raises(TypeError):
        first[0] = ("authority_version", "forged")


def test_direct_construction_subclassing_and_object_new_are_not_authority():
    with pytest.raises(TypeError, match="producer-issued"):
        subject.ProviderLifecycleAuthorityHandle()

    forged = object.__new__(subject.ProviderLifecycleAuthorityHandle)
    with pytest.raises(ValueError, match="producer-issued"):
        subject.validate_provider_lifecycle_authority(forged)

    class Forged(subject.ProviderLifecycleAuthorityHandle):
        pass

    forged_subclass = object.__new__(Forged)
    with pytest.raises(TypeError, match="exact producer-issued"):
        subject.validate_provider_lifecycle_authority(forged_subclass)


def test_authoritative_copy_and_deepcopy_issue_fresh_registered_handles():
    original = subject.PROVIDER_LIFECYCLE_AUTHORITY
    copied = subject.copy_provider_lifecycle_authority(original)
    ordinary_copy = copy.copy(original)
    deep_copy = copy.deepcopy(original)
    for candidate in (copied, ordinary_copy, deep_copy):
        assert candidate is not original
        assert _as_dict(subject.validate_provider_lifecycle_authority(candidate)) == _as_dict(
            _projection()
        )


def test_pickle_and_reconstruction_fail_closed():
    with pytest.raises(TypeError, match="not serialisable"):
        pickle.dumps(subject.PROVIDER_LIFECYCLE_AUTHORITY)
    forged = object.__new__(subject.ProviderLifecycleAuthorityHandle)
    with pytest.raises(ValueError):
        subject.project_provider_lifecycle_authority(forged)


def test_saved_protocol_resists_public_helper_and_class_metadata_rebinding(monkeypatch):
    validate = subject.validate_provider_lifecycle_authority
    project = subject.project_provider_lifecycle_authority
    copy_authority = subject.copy_provider_lifecycle_authority
    authority = subject.PROVIDER_LIFECYCLE_AUTHORITY
    expected_lifecycle = _as_dict(project(authority))["lifecycle"]

    monkeypatch.setattr(subject, "validate_provider_lifecycle_authority", lambda value: ())
    monkeypatch.setattr(subject, "project_provider_lifecycle_authority", lambda value: ())
    monkeypatch.setattr(subject, "copy_provider_lifecycle_authority", lambda value: object())
    monkeypatch.setattr(subject, "str", object, raising=False)
    monkeypatch.setattr(subject, "int", object, raising=False)
    monkeypatch.setattr(subject, "bool", object, raising=False)
    monkeypatch.setattr(
        subject.ProviderLifecycleAuthorityHandle,
        "__copy__",
        lambda self: object(),
    )
    monkeypatch.setattr(
        subject.ProviderLifecycleAuthorityHandle,
        "__reduce_ex__",
        lambda self, protocol: (object, ()),
    )

    assert _as_dict(validate(authority))["policy_status"] == "policy_incomplete"
    assert _as_dict(project(authority))["lifecycle"] == expected_lifecycle
    assert _as_dict(validate(copy_authority(authority)))["authority_version"] == (
        "FD-W10-002+FD-W10-003/2026-09-04/v1"
    )


def test_mutable_s1_status_global_cannot_promote_incomplete_policy(monkeypatch):
    class ForgedStatus(str, Enum):
        POLICY_INCOMPLETE = "policy_inputs_complete"
        POLICY_INPUTS_COMPLETE = "policy_inputs_complete"

    monkeypatch.setattr(s1, "PolicyCompletenessStatus", ForgedStatus)
    kernel = subject._build_provider_lifecycle_authority()
    projection = dict(kernel[6](kernel[4]))
    assert projection["policy_status"] == "policy_incomplete"
    assert len(projection["unresolved_policy_keys"]) == 9


def test_reordered_s1_runtime_denominator_cannot_change_s2a(monkeypatch):
    monkeypatch.setattr(
        s1,
        "REQUIRED_BILLING_POLICY_KEYS",
        tuple(reversed(s1.REQUIRED_BILLING_POLICY_KEYS)),
    )
    kernel = subject._build_provider_lifecycle_authority()
    projection = dict(kernel[6](kernel[4]))
    assert projection["settled_policy_keys"] == EXPECTED_SETTLED
    assert projection["unresolved_policy_keys"] == EXPECTED_UNRESOLVED


def test_fabricated_s1_key_type_and_denominator_cannot_change_s2a(monkeypatch):
    ForgedPolicyKey = Enum(
        "BillingPolicyKey",
        {key.name: key.value for key in s1.REQUIRED_BILLING_POLICY_KEYS},
        type=str,
    )
    monkeypatch.setattr(s1, "BillingPolicyKey", ForgedPolicyKey)
    monkeypatch.setattr(
        s1,
        "REQUIRED_BILLING_POLICY_KEYS",
        tuple(ForgedPolicyKey),
    )
    kernel = subject._build_provider_lifecycle_authority()
    projection = dict(kernel[6](kernel[4]))
    assert projection["settled_policy_keys"] == EXPECTED_SETTLED
    assert projection["unresolved_policy_keys"] == EXPECTED_UNRESOLVED


def test_forged_s1_authority_helpers_and_source_cannot_change_s2a(monkeypatch):
    def forged_validate(value):
        return (
            "FD-W10-001",
            object(),
            "FORGED-S1/V9",
            object(),
            (),
            object(),
            object(),
            object(),
        )

    monkeypatch.setattr(s1, "validate_billing_authority", forged_validate)
    monkeypatch.setattr(s1, "project_billing_authority", lambda value: value)
    monkeypatch.setattr(s1, "INITIAL_BILLING_AUTHORITY", object())
    kernel = subject._build_provider_lifecycle_authority()
    projection = dict(kernel[6](kernel[4]))
    assert projection["source_authority_version"] == "FD-W10-001/2026-09-02/v1"
    assert projection["source_contract_sha256"] == (
        "9c5dce7a81652d58562ca339def95fba7cbb2d1c02f965618ebd8f40bcad202b"
    )


def test_combined_s1_module_and_package_rebinding_cannot_change_s2a(monkeypatch):
    ForgedPolicyKey = Enum(
        "BillingPolicyKey",
        {key.name: key.value for key in s1.REQUIRED_BILLING_POLICY_KEYS},
        type=str,
    )

    def fake_policy_validator():
        captured = ForgedPolicyKey

        def validate(value):
            return captured

        return validate

    for module in (s1, s1_package):
        monkeypatch.setattr(module, "validate_billing_policy_decision", fake_policy_validator())
        monkeypatch.setattr(module, "BillingPolicyKey", ForgedPolicyKey)
        monkeypatch.setattr(module, "REQUIRED_BILLING_POLICY_KEYS", tuple(ForgedPolicyKey))
        monkeypatch.setattr(module, "validate_billing_authority", lambda value: ("forged",))
        monkeypatch.setattr(module, "project_billing_authority", lambda value: value)
        monkeypatch.setattr(module, "INITIAL_BILLING_AUTHORITY", object())
        monkeypatch.setattr(module, "AUTHORITY_VERSION", "FORGED-S1/V10")

    kernel = subject._build_provider_lifecycle_authority()
    projection = dict(kernel[6](kernel[4]))
    assert projection["source_authority_version"] == "FD-W10-001/2026-09-02/v1"
    assert projection["policy_status"] == "policy_incomplete"
    assert projection["settled_policy_keys"] == EXPECTED_SETTLED
    assert projection["unresolved_policy_keys"] == EXPECTED_UNRESOLVED


def test_saved_projector_does_not_call_mutable_exported_validator_code():
    validate = subject.validate_provider_lifecycle_authority
    project = subject.project_provider_lifecycle_authority
    original_code = validate.__code__

    forged_result = (("policy_status", "policy_inputs_complete"),)

    def make_forged_code():
        captured = forged_result

        def forged(value):
            # Preserve one closure cell so the code object is assignment-
            # compatible with the exported wrapper, but return attacker data.
            captured
            return (("policy_status", "policy_inputs_complete"),)

        return forged.__code__

    try:
        validate.__code__ = make_forged_code()
        assert validate(object()) == forged_result
        with pytest.raises(TypeError, match="exact producer-issued"):
            project(object())
        assert dict(project(subject.PROVIDER_LIFECYCLE_AUTHORITY))[
            "policy_status"
        ] == "policy_incomplete"
    finally:
        validate.__code__ = original_code


def test_copy_issuance_bypasses_rebound_class_new(monkeypatch):
    authority = subject.PROVIDER_LIFECYCLE_AUTHORITY
    copy_authority = subject.copy_provider_lifecycle_authority
    forged = object.__new__(subject.ProviderLifecycleAuthorityHandle)

    monkeypatch.setattr(
        subject.ProviderLifecycleAuthorityHandle,
        "__new__",
        staticmethod(lambda cls, *args, **kwargs: forged),
    )
    copied = copy_authority(authority)
    assert copied is not forged
    assert dict(subject.validate_provider_lifecycle_authority(copied))[
        "policy_status"
    ] == "policy_incomplete"
    with pytest.raises(ValueError, match="producer-issued"):
        subject.validate_provider_lifecycle_authority(forged)


def test_no_provider_ids_secrets_sdk_network_runtime_or_persistence_surface():
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
    assert not imported_roots.intersection(
        {"stripe", "requests", "httpx", "urllib", "socket", "sqlite3", "flask"}
    )
    lowered = source.casefold()
    for forbidden in (
        "api_key",
        "webhook_secret",
        "price_id",
        "customer_id",
        "subscription_id",
        "account_id",
        "https://",
        "os.environ",
        "database",
        "commit(",
    ):
        assert forbidden not in lowered


def test_public_surface_has_no_runtime_event_or_entitlement_api():
    assert set(subject.__all__) == {
        "AUTHORITY_VERSION",
        "PROVIDER_LIFECYCLE_AUTHORITY",
        "SETTLED_POLICY_KEYS",
        "UNRESOLVED_POLICY_KEYS",
        "ProviderLifecycleAuthorityHandle",
        "copy_provider_lifecycle_authority",
        "project_provider_lifecycle_authority",
        "validate_provider_lifecycle_authority",
    }
    assert not any(
        token in name.casefold()
        for name in subject.__all__
        for token in ("event", "deadline", "grant", "activate", "persist", "webhook")
    )
    assert "datetime" not in str(inspect.signature(subject.project_provider_lifecycle_authority))


def test_completion_map_preserves_denominator_and_records_s2_partial_only():
    text = MAP.read_text(encoding="utf-8")
    assert "0/8 slices complete" in text
    assert "0/8 (0%)" in text
    assert "0/13 terminal" in text
    assert "S2 partially implemented" in text
    assert "Six Founder-settled policy keys are explicit" in text
    assert "six settled\npolicy keys and nine policy keys unresolved" in text
    assert "closes Q1 and\nQ2 as bounded ordinary engineering policies" in text
    assert "is the sole genuine current Founder choice" in text
    assert "S2 remains incomplete" in text
    assert "not launch-ready" in text
