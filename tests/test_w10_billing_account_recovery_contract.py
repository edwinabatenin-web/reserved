"""Adversarial tests for the pure W10-S2D recovery decision contract."""

from __future__ import annotations

import ast
import copy
import gc
import hashlib
import pickle
import weakref
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path

import pytest

from reserved.billing import billing_account_recovery_contract as subject


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs" / "W10_S2D_BILLING_ACCOUNT_RECOVERY_CONTRACT.md"
NOW = datetime(2026, 9, 4, 12, 0, 0, tzinfo=timezone.utc)


def authentication(owner: int = 41, **changes):
    value = {
        "schema_version": "reserved-authenticated-owner-context/1.0",
        "owner_user_id": owner,
        "authentication_reference": "evidence:auth-event-41",
        "authenticated_at": NOW - timedelta(minutes=2),
        "authentication_valid_until": NOW + timedelta(minutes=5),
        "trust_status": "supplied_by_future_authenticated_reserved_adapter",
    }
    value.update(changes)
    return value


def mapping(owner: int = 41, **changes):
    value = {
        "schema_version": "reserved-owner-billing-mapping/1.0",
        "owner_user_id": owner,
        "canonical_owner_id": str(owner),
        "billing_account_id": f"billing-account-{owner}",
        "mapping_version": 7,
        "mapping_snapshot_id": f"mapping-snapshot-{owner}-7",
        "mapping_evidence_reference": f"evidence:mapping-{owner}-7",
        "observed_at": NOW - timedelta(minutes=1),
        "fresh_until": NOW + timedelta(minutes=3),
        "mapping_cardinality": "exactly_one",
        "mapping_status": "active",
        "trust_status": "supplied_by_future_authenticated_durable_repository",
    }
    value.update(changes)
    return value


def initiation(**changes):
    value = {
        "schema_version": "reserved-billing-recovery-initiation/1.0",
        "request_id": "recovery-request-41-1",
        "idempotency_key": "recovery-idempotency-41-1",
        "requested_at": NOW,
        "purpose": "manage_existing_owner_bound_subscription_billing",
    }
    value.update(changes)
    return value


def replay(**changes):
    value = {
        "schema_version": "reserved-billing-recovery-replay/1.0",
        "mapping_snapshot_id": "mapping-snapshot-41-7",
        "request_id": "recovery-request-41-1",
        "idempotency_key": "recovery-idempotency-41-1",
        "checked_at": NOW,
        "status": "unused_for_request",
        "existing_decision_reference": None,
    }
    value.update(changes)
    return value


def decide(*, owner=41, auth=None, account_mapping="default", request=None, guard=None, now=NOW):
    if auth is None:
        auth = authentication(owner)
    if account_mapping == "default":
        account_mapping = mapping(owner)
    if request is None:
        request = initiation()
    if guard is None:
        guard = replay()
    return subject.decide_billing_account_recovery(
        authenticated_owner_user_id=owner,
        authentication_context=auth,
        mapping_snapshot=account_mapping,
        initiation=request,
        replay_snapshot=guard,
        evaluated_at=now,
    )


def projected(value):
    return dict(subject.project_billing_account_recovery_decision(value))


def test_contract_is_disabled_first_and_source_bound_without_claiming_completion():
    data = dict(
        subject.project_billing_account_recovery_contract(
            subject.BILLING_ACCOUNT_RECOVERY_CONTRACT
        )
    )
    assert data["contract_version"] == (
        "reserved-w10-billing-account-recovery-contract/1.0"
    )
    assert data["candidate_base_commit"] == (
        "26944b22dfc4287287827ee7cdabe849e8906531"
    )
    assert data["candidate_base_tree"] == (
        "a072db4cfb9d22a32a9b41525098dbd110dcfeca"
    )
    assert data["authenticated_owner_root"] == "positive_exact_reserved_users.id_only"
    assert data["mapping_source"] == (
        "future_separately_authenticated_durable_repository"
    )
    assert data["runtime_activation"] == "disabled"
    assert data["maximum_candidate_lifetime_seconds"] == 300
    assert data["assurance_status"] == "contract_only_not_w10_s2_s3_s5_completion"
    assert len(data["unresolved_gates"]) == 10
    assert "provider_sdk_network_or_session_creation" in data["scope_exclusions"]
    provenance = dict(data["authority_provenance"])
    assert provenance["w10_s2c_commit"] == (
        "a07348976321df65bbd95c9170c906bcddd5baa5"
    )
    assert provenance["w10_s3b_commit"] == (
        "5bc29bcb30c95ea7a5a9430104653b366d709eb6"
    )


def test_exact_owner_bound_mapping_yields_only_short_lived_structural_candidate():
    data = projected(decide())
    assert data["authenticated_owner_user_id"] == 41
    assert data["canonical_owner_id"] == "41"
    assert data["billing_account_id"] == "billing-account-41"
    assert data["decision_not_after"] == NOW + timedelta(minutes=3)
    assert data["decision"] == (
        "future_provider_management_session_request_candidate_only"
    )
    assert data["reason"] == (
        "exact_owner_bound_mapping_and_atomic_unused_replay_state"
    )
    assert data["future_management_session_request_candidate_authorized"] is True
    assert data["activation_required_separately"] is True
    assert data["existing_decision_reference"] is None
    for field in (
        "provider_session_creation_authority",
        "network_authority",
        "entitlement_mutation_allowed",
        "charge_authority",
        "refund_authority",
        "transfer_merge_delegation_authority",
        "manual_entitlement_grant_authority",
    ):
        assert data[field] is False
    assert data["evidence_references"] == (
        "evidence:auth-event-41",
        "evidence:mapping-41-7",
    )
    assert data["trust_status"] == (
        "structural_candidate_not_authentication_not_persistence_not_provider_authority"
    )


def test_earliest_authentication_or_mapping_expiry_bounds_candidate():
    auth = authentication(authentication_valid_until=NOW + timedelta(seconds=20))
    data = projected(decide(auth=auth))
    assert data["decision_not_after"] == NOW + timedelta(seconds=20)


def test_candidate_lifetime_is_capped_even_when_caller_expiries_are_long():
    auth = authentication(authentication_valid_until=NOW + timedelta(days=30))
    account_mapping = mapping(fresh_until=NOW + timedelta(days=30))
    data = projected(decide(auth=auth, account_mapping=account_mapping))
    assert data["decision_not_after"] == NOW + timedelta(minutes=5)


@pytest.mark.parametrize(
    ("account_mapping", "reason"),
    [
        (None, "mapping_missing"),
        (mapping(mapping_cardinality="none"), "mapping_ambiguous_or_missing"),
        (mapping(mapping_cardinality="multiple"), "mapping_ambiguous_or_missing"),
        (mapping(mapping_cardinality="conflicting"), "mapping_ambiguous_or_missing"),
        (mapping(mapping_status="stale"), "mapping_not_active"),
        (mapping(mapping_status="conflicting"), "mapping_not_active"),
        (mapping(mapping_status="deleted"), "mapping_not_active"),
    ],
)
def test_missing_ambiguous_conflicting_and_inactive_mapping_fail_closed(account_mapping, reason):
    data = projected(decide(account_mapping=account_mapping))
    assert data["decision"] == "fail_closed_no_management_session_request"
    assert data["reason"] == reason
    assert data["decision_not_after"] is None
    assert data["future_management_session_request_candidate_authorized"] is False


def test_cross_owner_substitution_fails_closed_without_leaking_an_account_selection_path():
    other = mapping(52)
    data = projected(decide(owner=41, account_mapping=other))
    assert data["reason"] == "cross_owner_mapping_rejected"
    assert data["future_management_session_request_candidate_authorized"] is False
    assert data["authenticated_owner_user_id"] == 41
    assert data["billing_account_id"] is None
    assert data["mapping_snapshot_id"] is None
    assert data["evidence_references"] == ("evidence:auth-event-41",)


def test_authentication_context_cannot_rebind_the_exact_authenticated_owner():
    data = projected(
        decide(
            owner=41,
            auth=authentication(
                52,
                authentication_reference="evidence:auth-event-owner-52",
            ),
        )
    )
    assert data["reason"] == "authenticated_owner_context_conflict"
    assert data["future_management_session_request_candidate_authorized"] is False
    assert data["evidence_references"] == ()


def test_mutable_callable_defaults_cannot_supply_mandatory_decision_facts():
    decision = subject.decide_billing_account_recovery
    original_defaults = decision.__defaults__
    original_keyword_defaults = decision.__kwdefaults__
    try:
        decision.__defaults__ = (
            41,
            authentication(),
            mapping(),
            initiation(),
            replay(),
            NOW,
        )
        decision.__kwdefaults__ = {
            "authenticated_owner_user_id": 41,
            "authentication_context": authentication(),
            "mapping_snapshot": mapping(),
            "initiation": initiation(),
            "replay_snapshot": replay(),
            "evaluated_at": NOW,
        }
        with pytest.raises(ValueError, match="exact contract fields"):
            decision()
    finally:
        decision.__defaults__ = original_defaults
        decision.__kwdefaults__ = original_keyword_defaults


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "email",
        "billing_email",
        "provider_customer_id",
        "subscription_id",
        "redirect_url",
        "return_url",
        "owner_id_from_browser",
    ],
)
def test_browser_provider_or_redirect_fields_are_never_selection_authority(forbidden_field):
    request = initiation()
    request[forbidden_field] = "attacker-controlled"
    with pytest.raises(ValueError, match="exact contract fields"):
        decide(request=request)


@pytest.mark.parametrize("provider_id", ["cus_123ABC", "sub_123ABC", "acct_123ABC"])
def test_provider_ids_cannot_stand_in_for_internal_owner_bound_account(provider_id):
    with pytest.raises(ValueError, match="provider identifier"):
        decide(account_mapping=mapping(billing_account_id=provider_id))


@pytest.mark.parametrize(
    ("guard", "reason", "disposition"),
    [
        (
            replay(
                status="exact_request_replay",
                existing_decision_reference="recovery-decision-existing",
            ),
            "exact_replay_no_new_request",
            "return_existing_decision_reference_only",
        ),
        (
            replay(
                status="mapping_replayed_for_other_request",
                existing_decision_reference="recovery-decision-other",
            ),
            "mapping_replayed_for_other_request",
            "no_new_request",
        ),
        (
            replay(
                status="idempotency_conflict",
                existing_decision_reference="recovery-decision-conflict",
            ),
            "idempotency_conflict",
            "no_new_request",
        ),
    ],
)
def test_replay_and_conflict_never_authorize_a_new_provider_request(guard, reason, disposition):
    data = projected(decide(guard=guard))
    assert data["reason"] == reason
    assert data["idempotency_disposition"] == disposition
    if reason == "exact_replay_no_new_request":
        assert data["existing_decision_reference"] == "recovery-decision-existing"
    else:
        assert data["existing_decision_reference"] is None
    assert data["future_management_session_request_candidate_authorized"] is False
    assert data["provider_session_creation_authority"] is False


def test_pure_duplicate_evaluation_has_deterministic_identity_but_distinct_handles():
    first = decide()
    second = decide()
    assert first is not second
    assert projected(first) == projected(second)
    assert projected(first)["idempotency_disposition"] == (
        "new_deterministic_request_candidate"
    )


@pytest.mark.parametrize(
    ("guard", "reason"),
    [
        (replay(mapping_snapshot_id="mapping-snapshot-other"), "replay_mapping_snapshot_conflict"),
        (replay(request_id="request-other"), "replay_request_identity_conflict"),
        (replay(idempotency_key="idem-other"), "replay_request_identity_conflict"),
        (
            replay(checked_at=NOW - timedelta(microseconds=1)),
            "replay_check_not_atomic_with_evaluation",
        ),
    ],
)
def test_replay_snapshot_must_match_mapping_request_and_exact_evaluation_time(guard, reason):
    data = projected(decide(guard=guard))
    assert data["reason"] == reason
    assert data["future_management_session_request_candidate_authorized"] is False


@pytest.mark.parametrize(
    ("auth", "account_mapping", "request_input", "now", "reason"),
    [
        (
            authentication(authentication_valid_until=NOW),
            mapping(),
            initiation(),
            NOW,
            "authentication_stale_at_evaluation",
        ),
        (
            authentication(),
            mapping(fresh_until=NOW),
            initiation(),
            NOW,
            "mapping_stale_at_evaluation",
        ),
        (
            authentication(),
            mapping(observed_at=NOW + timedelta(seconds=1), fresh_until=NOW + timedelta(minutes=2)),
            initiation(),
            NOW,
            "mapping_observation_from_future",
        ),
        (
            authentication(),
            mapping(),
            initiation(requested_at=NOW + timedelta(seconds=1)),
            NOW,
            "request_from_future",
        ),
        (
            authentication(authenticated_at=NOW, authentication_valid_until=NOW + timedelta(minutes=1)),
            mapping(),
            initiation(requested_at=NOW - timedelta(microseconds=1)),
            NOW,
            "request_predates_authentication",
        ),
    ],
)
def test_stale_future_and_time_of_check_edges_fail_closed(
    auth, account_mapping, request_input, now, reason
):
    data = projected(
        decide(
            auth=auth,
            account_mapping=account_mapping,
            request=request_input,
            now=now,
        )
    )
    assert data["reason"] == reason
    assert data["future_management_session_request_candidate_authorized"] is False


@pytest.mark.parametrize(
    ("factory", "field"),
    [
        (authentication, "authentication_reference"),
        (mapping, "billing_account_id"),
        (mapping, "mapping_snapshot_id"),
        (mapping, "mapping_evidence_reference"),
        (initiation, "request_id"),
        (initiation, "idempotency_key"),
        (replay, "mapping_snapshot_id"),
        (replay, "request_id"),
        (replay, "idempotency_key"),
    ],
)
def test_secret_shaped_retained_fields_are_rejected(factory, field):
    malicious_value = (
        "evidence:sk_live_customer_secret"
        if field.endswith("evidence_reference") or field == "authentication_reference"
        else "sk_live_customer_secret"
    )
    malicious = factory(**{field: malicious_value})
    with pytest.raises(ValueError, match="credential-shaped"):
        if factory is authentication:
            decide(auth=malicious)
        elif factory is mapping:
            decide(account_mapping=malicious)
        elif factory is initiation:
            decide(request=malicious)
        else:
            decide(guard=malicious)


class StringSubclass(str):
    def __hash__(self):
        raise AssertionError("hostile string hash must not run")

    def __eq__(self, other):
        raise AssertionError("hostile string equality must not run")


class DictSubclass(dict):
    pass


class PassiveStringKeySubclass(str):
    __hash__ = str.__hash__

    def __eq__(self, other):
        raise AssertionError("hostile field-name equality must not run")


class IntegerSubclass(int):
    pass


class StatefulTimezone(tzinfo):
    def utcoffset(self, dt):
        return timedelta(0)

    def dst(self, dt):
        return timedelta(0)


def test_mutable_subclass_and_stateful_object_inputs_fail_before_dispatch():
    with pytest.raises(TypeError, match="exact built-in dict"):
        decide(auth=DictSubclass(authentication()))
    with pytest.raises(ValueError, match="positive exact users.id integer"):
        decide(owner=IntegerSubclass(41))
    with pytest.raises(ValueError, match="invalid request_id"):
        decide(request=initiation(request_id=StringSubclass("recovery-request-41-1")))
    hostile_time = NOW.replace(tzinfo=StatefulTimezone())
    with pytest.raises(ValueError, match="timezone.utc"):
        decide(now=hostile_time)
    with pytest.raises(ValueError, match="positive exact users.id integer"):
        decide(owner=True)


def test_subclassed_field_names_and_schema_literals_fail_without_equality_dispatch():
    auth = authentication()
    hostile_key_auth = {
        (PassiveStringKeySubclass(key) if key == "schema_version" else key): value
        for key, value in auth.items()
    }
    with pytest.raises(TypeError, match="field names must be exact"):
        decide(auth=hostile_key_auth)

    auth["schema_version"] = StringSubclass(
        "reserved-authenticated-owner-context/1.0"
    )
    with pytest.raises(ValueError, match="authentication context schema"):
        decide(auth=auth)


def test_input_mutation_after_evaluation_cannot_change_issued_decision():
    auth = authentication()
    account_mapping = mapping()
    request = initiation()
    guard = replay()
    decision = decide(
        auth=auth,
        account_mapping=account_mapping,
        request=request,
        guard=guard,
    )
    expected = projected(decision)
    auth.clear()
    account_mapping["owner_user_id"] = 999
    request["request_id"] = "changed"
    guard["status"] = "idempotency_conflict"
    assert projected(decision) == expected


def test_direct_construction_subclass_object_new_and_pickle_cannot_forge_authority():
    for cls in (
        subject.BillingAccountRecoveryContractHandle,
        subject.BillingAccountRecoveryDecision,
    ):
        with pytest.raises(TypeError, match="producer-issued"):
            cls()
        forged = object.__new__(cls)
        validator = (
            subject.validate_billing_account_recovery_contract
            if cls is subject.BillingAccountRecoveryContractHandle
            else subject.validate_billing_account_recovery_decision
        )
        with pytest.raises(ValueError, match="not producer-issued"):
            validator(forged)
        with pytest.raises(TypeError, match="serialisable"):
            pickle.dumps(forged)

        class Subclass(cls):
            pass

        with pytest.raises(TypeError, match="exact producer-issued"):
            validator(object.__new__(Subclass))

    with pytest.raises(TypeError, match="serialisable"):
        pickle.dumps(decide())


def test_authoritative_copy_paths_revalidate_and_issue_fresh_equal_projections():
    original = decide()
    copies = (
        subject.copy_billing_account_recovery_decision(original),
        copy.copy(original),
        copy.deepcopy(original),
    )
    for candidate in copies:
        assert candidate is not original
        assert projected(candidate) == projected(original)


def test_public_global_and_class_metadata_mutation_cannot_authorize_forgery(monkeypatch):
    decide_captured = subject.decide_billing_account_recovery
    validate_captured = subject.validate_billing_account_recovery_decision
    project_captured = subject.project_billing_account_recovery_decision
    copy_captured = subject.copy_billing_account_recovery_decision
    cls = subject.BillingAccountRecoveryDecision
    genuine = decide_captured(
        authenticated_owner_user_id=41,
        authentication_context=authentication(),
        mapping_snapshot=mapping(),
        initiation=initiation(),
        replay_snapshot=replay(),
        evaluated_at=NOW,
    )
    expected = dict(project_captured(genuine))

    monkeypatch.setattr(subject, "decide_billing_account_recovery", lambda **kwargs: object())
    monkeypatch.setattr(subject, "validate_billing_account_recovery_decision", lambda value: ())
    monkeypatch.setattr(subject, "project_billing_account_recovery_decision", lambda value: ())
    monkeypatch.setattr(cls, "__hash__", lambda self: 1)
    monkeypatch.setattr(cls, "__eq__", lambda self, other: True)
    monkeypatch.setattr(cls, "__copy__", lambda self: object())
    monkeypatch.setattr(cls, "__reduce__", lambda self: (object, ()))

    assert dict(project_captured(genuine)) == expected
    assert dict(project_captured(copy_captured(genuine))) == expected
    forged = object.__new__(cls)
    with pytest.raises(ValueError, match="not producer-issued"):
        validate_captured(forged)


def test_generation_safe_registry_drops_collected_decisions():
    validator = subject.validate_billing_account_recovery_decision
    validated = next(
        cell.cell_contents
        for cell in validator.__closure__
        if callable(cell.cell_contents)
        and getattr(cell.cell_contents, "__name__", "") == "_validated"
    )
    registry = next(
        cell.cell_contents
        for cell in validated.__closure__
        if type(cell.cell_contents) is dict
        and subject.BillingAccountRecoveryDecision in cell.cell_contents
    )
    decision_state = registry[subject.BillingAccountRecoveryDecision]
    baseline = len(decision_state)
    decisions = [decide() for _ in range(100)]
    assert len(decision_state) == baseline + 100
    references = [weakref.ref(value) for value in decisions]
    decisions.clear()
    del decisions
    gc.collect()
    assert all(reference() is None for reference in references)
    assert len(decision_state) == baseline


def test_exported_api_is_minimal_and_contains_no_route_provider_or_persistence_surface():
    assert set(subject.__all__) == {
        "BILLING_ACCOUNT_RECOVERY_CONTRACT",
        "CONTRACT_VERSION",
        "BillingAccountRecoveryContractHandle",
        "BillingAccountRecoveryDecision",
        "copy_billing_account_recovery_contract",
        "copy_billing_account_recovery_decision",
        "decide_billing_account_recovery",
        "project_billing_account_recovery_contract",
        "project_billing_account_recovery_decision",
        "validate_billing_account_recovery_contract",
        "validate_billing_account_recovery_decision",
    }
    forbidden = ("route", "stripe", "provider_session", "database", "entitlement_grant")
    assert not any(fragment in name.lower() for name in subject.__all__ for fragment in forbidden)


def test_module_imports_are_standard_library_and_has_no_io_network_or_sdk_calls():
    path = ROOT / "reserved" / "billing" / "billing_account_recovery_contract.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = set()
    call_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                call_names.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                call_names.add(node.func.attr)
    assert imports == {"__future__", "copy", "datetime", "hashlib", "json", "re", "weakref"}
    assert call_names.isdisjoint(
        {"open", "connect", "execute", "commit", "urlopen", "post", "create_session"}
    )


def test_document_and_accepted_source_hashes_are_exactly_bound():
    expected = {
        "FOUNDER_DECISIONS.md": "03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4",
        "reserved/billing/provider_lifecycle_authority.py": "fc21c3a0f9d8d7eeb9a06bcbf5fc4a418568fe06aa5f65f47c325d8ecfde834a",
        "reserved/billing/fail_closed_launch_defaults.py": "cd72be19d8180a52f2e09fec56cc3219347059b025ceb3f12086d7d8dde40715",
        "reserved/billing/entitlement_core.py": "b46b797614b57047e64f6f6597b1c788b9ab15db90653b07add31b4bbb03cb3b",
        "reserved/billing/event_inbox_contract.py": "4dc0b6bb8b109854531dc1b9d492255e98dca805822cd5e0257f0fdf9b0ca8ed",
        "reserved/billing/stripe_disabled_first_contract.py": "87a84c5ec77f25e12667b5466052b4a84ee6e01a6b075df643202d95aec98638",
        "docs/W10_S2C_POLICY_EVIDENCE_DOSSIER.md": "db31ba2e7c0e51701bc62c6a7b4b489cbde072b5efaf1f09f7c67a5f75fd5dcd",
    }
    for relative_path, digest in expected.items():
        assert hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest() == digest


def test_document_preserves_disabled_nonimplementation_and_open_gate_boundaries():
    text = " ".join(DOCUMENT.read_text(encoding="utf-8").split())
    required = (
        "sole identity root is the exact, positive `users.id`",
        "does **not** prove that Reserved authenticated the owner",
        "provider-session creation and network authority",
        "Runtime activation remains `disabled`",
        "W10-S2 remains incomplete",
        "does not complete W10-S3 or start/complete W10-S5",
        "browser, provider email, provider customer/subscription ID",
        "A denied decision deliberately omits billing-account",
        "never exceed five minutes after evaluation",
        "No additional Founder question is needed",
    )
    for phrase in required:
        assert phrase in text
    forbidden = (
        "W10-S2 is complete",
        "provider session is created",
        "entitlement is granted",
        "production-ready",
    )
    for phrase in forbidden:
        assert phrase not in text
