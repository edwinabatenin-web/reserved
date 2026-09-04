"""Adversarial tests for the pure W10-S4C portal intent contract."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import subprocess
import types
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path

import pytest

import reserved.billing.portal_intent_contract as subject


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reserved/billing/portal_intent_contract.py"
DOC = ROOT / "docs/W10_S4C_PORTAL_INTENT_CONTRACT.md"
BASE = "5f5a948891e1e812a5c74ff6c7266d153bb492fa"
TREE = "639369d06a8da75e8318bec7933993c26e39ace6"
DESTINATION = "reserved_billing_portal_return_reconciliation"


def now():
    return datetime(2026, 9, 4, 15, 0, tzinfo=timezone.utc)


def key_hash(value="portal_idempotency:intent.001"):
    return "sha256:" + hashlib.sha256(value.encode("ascii")).hexdigest()


def auth(owner=41, at=None, **changes):
    at = at or now()
    value = {
        "schema_version": "reserved-authenticated-owner-context/1.0",
        "owner_user_id": owner,
        "authentication_reference": "evidence:auth.001",
        "authenticated_at": at - timedelta(minutes=1),
        "authentication_valid_until": at + timedelta(minutes=10),
        "trust_status": "supplied_by_future_authenticated_reserved_adapter",
    }
    value.update(changes)
    return value


def account_mapping(owner=41, at=None, **changes):
    at = at or now()
    value = {
        "schema_version": "reserved-owner-billing-mapping/1.0",
        "owner_user_id": owner,
        "canonical_owner_id": str(owner),
        "billing_account_id": "billing-account-41",
        "mapping_version": 3,
        "mapping_snapshot_id": "mapping-snapshot-41-3",
        "mapping_evidence_reference": "evidence:mapping.041.v3",
        "observed_at": at - timedelta(minutes=1),
        "fresh_until": at + timedelta(minutes=10),
        "mapping_cardinality": "exactly_one",
        "mapping_status": "active",
        "trust_status": "supplied_by_future_authenticated_durable_repository",
    }
    value.update(changes)
    return value


def replay(owner=41, at=None, **changes):
    at = at or now()
    value = {
        "schema_version": "reserved-portal-intent-replay-snapshot/1.0",
        "owner_user_id": owner,
        "billing_account_id": "billing-account-41",
        "mapping_snapshot_id": "mapping-snapshot-41-3",
        "intent_id": "portal_intent:intent.001",
        "idempotency_key_digest": key_hash(),
        "state": "unused",
        "checked_at": at,
        "existing_candidate_identity": None,
    }
    value.update(changes)
    return value


def facts(owner=41, at=None, **changes):
    at = at or now()
    value = {
        "authentication_context": auth(owner, at),
        "owner_user_id": owner,
        "mapping_snapshot": account_mapping(owner, at),
        "provider_customer_observation_reference": "evidence:provider_observation.customer.041",
        "provider_email_observation_reference": "evidence:provider_observation.email.041",
        "purpose": "manage_existing_owner_bound_subscription_billing",
        "intent_id": "portal_intent:intent.001",
        "idempotency_key": "portal_idempotency:intent.001",
        "requested_at": at,
        "evaluated_at": at,
        "valid_until": at + timedelta(minutes=5),
        "return_destination_id": DESTINATION,
        "replay_snapshot": replay(owner, at),
        "evidence_reference": "evidence:portal_intent.001",
    }
    value.update(changes)
    return value


def candidate(owner=41, **changes):
    return subject.create_portal_request_candidate(owner, **facts(owner, **changes))


def replace(value, field, replacement):
    return tuple((name, replacement if name == field else item) for name, item in value)


def replace_and_reidentify(value, field, replacement):
    changed = replace(value, field, replacement)
    without = tuple(item for item in changed if item[0] != "candidate_identity")
    identity = "portal-intent:sha256-" + hashlib.sha256(
        json.dumps(without, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    ).hexdigest()
    return replace(changed, "candidate_identity", identity)


def test_exact_base_contract_and_source_hashes():
    projected = dict(subject.project_portal_intent_contract())
    assert projected["candidate_base_commit"] == BASE
    assert projected["candidate_base_tree"] == TREE
    for source_id, path, expected, accepted_at in projected["source_bindings"]:
        if source_id == "entitlement_separation":
            blob = subprocess.run(
                ["git", "show", f"{accepted_at}:{path}"], cwd=ROOT, check=True,
                stdout=subprocess.PIPE,
            ).stdout
            assert hashlib.sha256(blob).hexdigest() == expected
        else:
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
    assert hashlib.sha256((ROOT / "reserved/billing/entitlement_core.py").read_bytes()).hexdigest() == (
        "201c92c1093b663b786a5e49a1c2ca0d714f3fe6fdaebf18c0c7d486ef25f415"
    )
    assert projected["return_destination_allowlist"] == (DESTINATION,)


def test_valid_candidate_is_deterministic_detached_and_zero_authority():
    first, second = candidate(), candidate()
    assert first == second and first is not second
    view = dict(first)
    assert view["candidate_identity"].startswith("portal-intent:sha256-")
    assert view["authenticated_owner_user_id"] == 41
    assert view["billing_account_id"] == "billing-account-41"
    assert view["purpose"] == "manage_existing_owner_bound_subscription_billing"
    assert view["provider_observations_are_authentication"] is False
    assert set(dict(view["authority_flags"]).values()) == {False}
    assert subject.validate_portal_request_candidate(first) == first
    assert "portal_idempotency:intent.001" not in repr(first)


def test_provider_customer_and_email_are_only_redacted_observation_references():
    view = dict(candidate())
    assert view["provider_customer_observation_reference"].startswith("evidence:")
    assert view["provider_email_observation_reference"].startswith("evidence:")
    assert "@" not in repr(view)
    assert "cus_" not in repr(view)


@pytest.mark.parametrize("field", ("provider_customer_observation_reference", "provider_email_observation_reference"))
@pytest.mark.parametrize("embedded", ("evidence:cus_ABC123", "evidence:CUS-abc123", "evidence:source.sub_123", "evidence:acct/ABC", "evidence:price.test_123", "evidence:pm-ABC", "evidence:evt_123", "evidence:seti/ABC", "evidence:clock-test_123"))
def test_provider_observation_references_reject_embedded_provider_objects(field, embedded):
    with pytest.raises(ValueError, match="opaque"):
        candidate(**{field: embedded})


@pytest.mark.parametrize("owner", (None, True, False, 0, -1, 1.0, "41"))
def test_owner_requires_exact_positive_integer(owner):
    with pytest.raises((TypeError, ValueError)):
        candidate(owner=owner)


@pytest.mark.parametrize("change", (
    {"owner_user_id": 42},
    {"authentication_context": auth(42)},
    {"mapping_snapshot": account_mapping(42)},
    {"replay_snapshot": replay(42)},
))
def test_cross_owner_substitution_fails(change):
    with pytest.raises((TypeError, ValueError)):
        candidate(**change)


@pytest.mark.parametrize(("field", "value"), (
    ("mapping_cardinality", "multiple"),
    ("mapping_cardinality", "none"),
    ("mapping_status", "stale"),
    ("mapping_status", "conflicting"),
    ("billing_account_id", "cus_customer"),
    ("billing_account_id", "cus_customer"),
    ("canonical_owner_id", "42"),
))
def test_ambiguous_conflicting_or_wrong_mapping_fails(field, value):
    with pytest.raises((TypeError, ValueError)):
        candidate(mapping_snapshot=account_mapping(**{field: value}))


@pytest.mark.parametrize("change", (
    {"state": "used"},
    {"state": "ambiguous"},
    {"billing_account_id": "billing-account-other"},
    {"mapping_snapshot_id": "mapping-snapshot-other"},
    {"intent_id": "portal_intent:other"},
    {"idempotency_key_digest": "sha256:" + "0" * 64},
    {"checked_at": now() - timedelta(seconds=1)},
    {"existing_candidate_identity": "portal-intent:sha256-" + "0" * 64},
))
def test_replayed_stale_or_conflicting_snapshot_fails(change):
    with pytest.raises((TypeError, ValueError)):
        candidate(replay_snapshot=replay(**change))


@pytest.mark.parametrize("destination", ("https://reserved.example/return", "/billing", "other", True))
def test_return_destination_is_fixed_logical_allowlist(destination):
    with pytest.raises((TypeError, ValueError), match="return destination"):
        candidate(return_destination_id=destination)


@pytest.mark.parametrize("change", (
    {"purpose": "refund"},
    {"valid_until": now()},
    {"valid_until": now() + timedelta(minutes=5, microseconds=1)},
    {"evaluated_at": now() - timedelta(seconds=1)},
    {"requested_at": now() - timedelta(minutes=5, seconds=1)},
    {"mapping_snapshot": account_mapping(fresh_until=now())},
    {"mapping_snapshot": account_mapping(observed_at=now() + timedelta(seconds=1))},
))
def test_wrong_purpose_stale_future_or_overlong_facts_fail(change):
    with pytest.raises((TypeError, ValueError)):
        candidate(**change)


class OtherUTC(tzinfo):
    def utcoffset(self, value): return timedelta(0)
    def dst(self, value): return timedelta(0)


def test_only_exact_datetime_and_timezone_utc_are_accepted():
    with pytest.raises((TypeError, ValueError)):
        candidate(evaluated_at=datetime(2026, 9, 4, 15, 0, tzinfo=OtherUTC()))


def test_request_freshness_accepts_exact_five_minutes_but_not_one_second_more():
    candidate(
        requested_at=now() - timedelta(minutes=5),
        authentication_context=auth(
            authenticated_at=now() - timedelta(minutes=6)
        ),
    )
    with pytest.raises(ValueError, match="freshness"):
        candidate(requested_at=now() - timedelta(minutes=5, seconds=1))


def test_detached_validator_rechecks_request_age_after_identity_recomputation():
    original = candidate()
    exact = replace_and_reidentify(
        original, "requested_at", "2026-09-04T14:55:00.000000Z"
    )
    assert subject.validate_portal_request_candidate(exact) == exact
    stale = replace_and_reidentify(
        original, "requested_at", "2026-09-04T14:54:59.000000Z"
    )
    with pytest.raises(ValueError, match="time boundary"):
        subject.validate_portal_request_candidate(stale)


@pytest.mark.parametrize("change", (
    {"intent_id": "portal_intent:sk_live_secret"},
    {"idempotency_key": "portal_idempotency:client_secret_value"},
    {"evidence_reference": "evidence:access_token.value"},
))
def test_secret_shaped_input_is_rejected(change):
    with pytest.raises(ValueError, match="secret-shaped"):
        candidate(**change)


def test_exact_call_shape_and_mutated_defaults_cannot_supply_inputs():
    create = subject.create_portal_request_candidate
    original, kworiginal = create.__defaults__, create.__kwdefaults__
    try:
        create.__defaults__ = (41,)
        create.__kwdefaults__ = facts()
        with pytest.raises((TypeError, ValueError)): create()
        with pytest.raises((TypeError, ValueError)): subject.validate_portal_request_candidate()
        with pytest.raises((TypeError, ValueError)): create(41, **(facts() | {"provider_customer_id": "cus_x"}))
    finally:
        create.__defaults__, create.__kwdefaults__ = original, kworiginal


def test_contract_claims_no_unprovable_shared_interpreter_producer_integrity():
    source = SOURCE.read_text().lower()
    for forbidden in ("integrity_snapshot", "require_integrity", "producer-issued", "admission_authority"):
        assert forbidden not in source
    projected = dict(subject.project_portal_intent_contract())
    assert "contract_only" in projected["assurance_status"]
    assert set(dict(projected["authority_flags"]).values()) == {False}


def test_hostile_closure_rewrite_can_never_mint_action_authority():
    """The former root-guard bypass is an explicit zero-authority boundary.

    Pure Python cannot defend its own closure cells from a same-interpreter
    attacker.  Even the exact historic owner-helper rewrite can therefore
    produce only a structurally reproducible candidate whose every authority
    remains false; no producer/admission claim exists to bypass.
    """
    create = subject.create_portal_request_candidate
    cells = dict(zip(create.__code__.co_freevars, create.__closure__, strict=True))
    assert "integrity_snapshot" not in cells and "require_integrity" not in cells
    owner_cell = cells["owner"]
    original = owner_cell.cell_contents
    try:
        owner_cell.cell_contents = lambda value, label: 41
        rewritten = create(True, **facts(41))
    finally:
        owner_cell.cell_contents = original
    validated = dict(subject.validate_portal_request_candidate(rewritten))
    assert validated["candidate_status"].startswith("structural_candidate_not_")
    assert validated["authentication_runtime_verified"] is False
    assert validated["provider_observations_are_authentication"] is False
    assert set(dict(validated["authority_flags"]).values()) == {False}


def test_saved_functions_ignore_public_rebinding_and_have_no_mutable_registry(monkeypatch):
    create = subject.create_portal_request_candidate
    validate = subject.validate_portal_request_candidate
    project = subject.project_portal_intent_contract
    expected = candidate()
    monkeypatch.setattr(subject, "CONTRACT_VERSION", "forged")
    monkeypatch.setattr(subject, "hashlib", object(), raising=False)
    monkeypatch.setattr(subject, "json", object(), raising=False)
    assert create(41, **facts()) == expected
    assert validate(expected) == expected
    assert dict(project())["contract_version"] == "reserved-w10-portal-intent-contract/1.0"
    pending, seen = [create, validate, project], set()
    while pending:
        value = pending.pop()
        if type(value) is not types.FunctionType or id(value) in seen:
            continue
        seen.add(id(value))
        for cell in value.__closure__ or ():
            nested = cell.cell_contents
            assert type(nested) not in (dict, list, set, bytearray)
            if type(nested) is types.FunctionType:
                pending.append(nested)


@pytest.mark.parametrize(("field", "replacement"), (
    ("authenticated_owner_user_id", 42),
    ("billing_account_id", "billing-account-other"),
    ("mapping_version", True),
    ("provider_observations_are_authentication", True),
    ("purpose", "refund"),
    ("return_destination_id", "other"),
    ("replay_guard_status", "consumed"),
    ("candidate_identity", "portal-intent:sha256-" + "0" * 64),
))
def test_tampered_candidate_fails(field, replacement):
    with pytest.raises((TypeError, ValueError)):
        subject.validate_portal_request_candidate(replace(candidate(), field, replacement))


def test_lifecycle_is_exact_non_extendable_and_portal_has_no_policy_effect():
    lifecycle = dict(dict(candidate())["lifecycle_boundary"])
    assert lifecycle == {
        "canonical_recovery_state": "payment_recovery",
        "recovery_period_calendar_days": 7,
        "recovery_deadline_extendable_by_portal": False,
        "portal_return_changes_entitlement": False,
        "provider_status_changes_entitlement_directly": False,
    }


def test_module_has_no_runtime_io_and_exports_exact_surface():
    tree = ast.parse(SOURCE.read_text())
    imports = {node.module.split(".", 1)[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    imports |= {alias.name.split(".", 1)[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    assert imports == {"__future__", "datetime", "hashlib", "json", "re"}
    assert subject.__all__ == ("CONTRACT_VERSION", "project_portal_intent_contract", "create_portal_request_candidate", "validate_portal_request_candidate")
    for name in subject.__all__[1:]:
        assert tuple(inspect.signature(getattr(subject, name)).parameters) == ("args", "kwargs")


def test_document_preserves_scope_and_open_gates():
    text = DOC.read_text().lower()
    for phrase in ("fd-w10-002", "fd-w10-003", "payment_recovery", "seven calendar days", "no stripe sdk", "q1", "q2", "q3", "does not complete w10-s4", "zero authority"):
        assert phrase in text


def test_exact_three_path_scope():
    import subprocess
    changed = subprocess.check_output(["git", "diff", "--name-only", "HEAD"], cwd=ROOT, text=True).splitlines()
    untracked = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT, text=True).splitlines()
    assert set(changed + untracked) <= {"reserved/billing/portal_intent_contract.py", "tests/test_w10_portal_intent_contract.py", "docs/W10_S4C_PORTAL_INTENT_CONTRACT.md"}
