"""Adversarial tests for the pure W10-S4B Checkout intent contract."""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import subprocess
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from types import FunctionType

import pytest

import reserved.billing.checkout_intent_contract as subject


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reserved" / "billing" / "checkout_intent_contract.py"
DOC = ROOT / "docs" / "W10_S4B_CHECKOUT_INTENT_CONTRACT.md"
BASE = "1d91526d11b5291d5388c78940682ca02edeb61e"
TREE = "e2fc725961f816d80eed9e5373d738e5e21a024c"
RETURN_DESTINATION = "reserved_billing_return_reconciliation"

EXPECTED_SOURCES = (
    (
        "founder_authority",
        "FOUNDER_DECISIONS.md",
        "03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4",
        "FD-W10-001+FD-W10-002+FD-W10-003",
    ),
    (
        "catalogue_authority",
        "reserved/billing/contracts.py",
        "9c5dce7a81652d58562ca339def95fba7cbb2d1c02f965618ebd8f40bcad202b",
        "9e8f94a9906f0c9d5c85b47223d20c34be499e1c",
    ),
    (
        "entitlement_transition_contract",
        "reserved/billing/entitlement_core.py",
        "b46b797614b57047e64f6f6597b1c788b9ab15db90653b07add31b4bbb03cb3b",
        "94bd87f019dc226ec8c73f32515229189500cf06",
    ),
    (
        "event_inbox_contract",
        "reserved/billing/event_inbox_contract.py",
        "4dc0b6bb8b109854531dc1b9d492255e98dca805822cd5e0257f0fdf9b0ca8ed",
        "5bc29bcb30c95ea7a5a9430104653b366d709eb6",
    ),
    (
        "disabled_stripe_edge",
        "reserved/billing/stripe_disabled_first_contract.py",
        "87a84c5ec77f25e12667b5466052b4a84ee6e01a6b075df643202d95aec98638",
        "2ad4a63dd1f10ba38859050b47245c28390667d8",
    ),
    (
        "authenticated_plan_quote_evidence",
        "docs/W10_S6C_AUTHENTICATED_PLAN_QUOTE_EVIDENCE.md",
        "c424c0ca999ef18568dfc1b86f79d9f0e27af1d05e7f9167ef9de43b344b3bb1",
        "3e05fb7f3149ee7030be768909eb6fe4f50e0b75",
    ),
    (
        "plan_selection_preview_evidence",
        "docs/W10_S6D_PLAN_SELECTION_PREVIEW_EVIDENCE.md",
        "d7306da9e1e163420e345567800c6789d8422619ceaf9b91d925458d0a136790",
        "46e2141c421fa80e39b60cd5b6bb955f44dfd863",
    ),
)


def contract():
    return dict(subject.project_checkout_intent_contract())


def idempotency_digest(value="checkout_idempotency:intent.001"):
    return "sha256:" + hashlib.sha256(value.encode("ascii")).hexdigest()


def auth_context(owner=7, now=None, **overrides):
    now = now or datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
    value = {
        "schema_version": "reserved-authenticated-owner-context/1.0",
        "owner_user_id": owner,
        "authentication_reference": "evidence:auth.001",
        "authenticated_at": now - timedelta(minutes=1),
        "authentication_valid_until": now + timedelta(minutes=10),
        "trust_status": (
            "future_authenticated_reserved_owner_adapter_structural_input_only"
        ),
    }
    value.update(overrides)
    return value


def replay_snapshot(owner=7, now=None, **overrides):
    now = now or datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
    value = {
        "schema_version": "reserved-checkout-intent-replay-snapshot/1.0",
        "owner_user_id": owner,
        "intent_id": "checkout_intent:intent.001",
        "idempotency_key_digest": idempotency_digest(),
        "state": "unused",
        "checked_at": now,
        "existing_candidate_identity": None,
    }
    value.update(overrides)
    return value


def candidate_facts(owner=7, now=None, **overrides):
    now = now or datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
    value = {
        "authentication_context": auth_context(owner, now),
        "owner_user_id": owner,
        "catalogue_authority_version": "FD-W10-001/2026-09-02/v1",
        "plan_key": "monthly",
        "intent_id": "checkout_intent:intent.001",
        "idempotency_key": "checkout_idempotency:intent.001",
        "requested_at": now,
        "evaluated_at": now,
        "valid_until": now + timedelta(minutes=5),
        "return_destination_id": RETURN_DESTINATION,
        "replay_snapshot": replay_snapshot(owner, now),
        "evidence_reference": "evidence:intent.001",
    }
    value.update(overrides)
    return value


def make_candidate(owner=7, **overrides):
    return subject.create_checkout_request_candidate(
        owner, **candidate_facts(owner, **overrides)
    )


def test_exact_base_contract_sources_and_no_completion_claim():
    projected = contract()
    assert subject.CONTRACT_VERSION == "reserved-w10-checkout-intent-contract/1.0"
    assert subject.CATALOGUE_AUTHORITY_VERSION == "FD-W10-001/2026-09-02/v1"
    assert projected["candidate_base_commit"] == BASE
    assert projected["candidate_base_tree"] == TREE
    assert projected["source_bindings"] == EXPECTED_SOURCES
    for source_id, path, expected_hash, accepted_at in EXPECTED_SOURCES:
        if source_id == "founder_authority":
            blob = subprocess.run(
                [
                    "git",
                    "show",
                    f"10fb93e2e6ab567a72d2370c1603768a7ac04bb5:{path}",
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
            ).stdout
            assert hashlib.sha256(blob).hexdigest() == expected_hash
        elif source_id == "entitlement_transition_contract":
            blob = subprocess.run(
                ["git", "show", f"{accepted_at}:{path}"], cwd=ROOT, check=True,
                stdout=subprocess.PIPE,
            ).stdout
            assert hashlib.sha256(blob).hexdigest() == expected_hash
        else:
            assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected_hash
    assert hashlib.sha256((ROOT / "reserved/billing/entitlement_core.py").read_bytes()).hexdigest() == (
        "201c92c1093b663b786a5e49a1c2ca0d714f3fe6fdaebf18c0c7d486ef25f415"
    )
    assert projected["assurance_status"] == (
        "contract_only_not_checkout_provider_entitlement_s4_or_launch_assurance"
    )


def test_exact_server_rederived_catalogue_and_fixed_logical_return_allowlist():
    assert contract()["gross_catalogue"] == (
        ("monthly", 2900, "GBP", "month", 1),
        ("six_month", 15600, "GBP", "month", 6),
        ("yearly", 28800, "GBP", "year", 1),
    )
    assert contract()["return_destination_allowlist"] == (RETURN_DESTINATION,)
    assert contract()["maximum_candidate_lifetime_seconds"] == 300


@pytest.mark.parametrize(
    ("plan_key", "amount", "interval", "count"),
    (
        ("monthly", 2900, "month", 1),
        ("six_month", 15600, "month", 6),
        ("yearly", 28800, "year", 1),
    ),
)
def test_valid_candidate_rederives_price_cadence_and_is_structural_only(
    plan_key, amount, interval, count
):
    projected = dict(make_candidate(plan_key=plan_key))
    assert projected["plan_key"] == plan_key
    assert projected["unit_amount_minor"] == amount
    assert projected["currency"] == "GBP"
    assert projected["recurring_interval"] == interval
    assert projected["recurring_interval_count"] == count
    assert projected["checkout_mode"] == "subscription"
    assert projected["quantity"] == 1
    assert projected["candidate_status"].startswith("structural_candidate_not_")
    assert projected["authentication_runtime_verified"] is False


def test_valid_calls_are_deterministic_but_do_not_claim_atomic_consumption():
    first = make_candidate()
    second = make_candidate()
    assert first == second and first is not second
    view = dict(first)
    assert view["candidate_identity"].startswith("checkout-intent:sha256-")
    assert view["replay_guard_status"] == "future_atomic_consume_required"
    assert "checkout_idempotency:intent.001" not in repr(first)
    assert subject.validate_checkout_request_candidate(first) == first


def test_every_runtime_provider_charge_return_and_entitlement_authority_is_false():
    flags = dict(dict(make_candidate())["authority_flags"])
    assert len(flags) == 12
    assert set(flags.values()) == {False}
    assert flags["checkout_session_creation_authority"] is False
    assert flags["browser_return_payment_authority"] is False
    assert flags["provider_status_entitlement_authority"] is False
    assert flags["entitlement_grant_or_mutation_authority"] is False
    assert flags["production_activation_authority"] is False


def test_payment_recovery_is_explicit_without_any_stripe_status_vocabulary():
    lifecycle = dict(dict(make_candidate())["lifecycle_boundary"])
    assert lifecycle == {
        "canonical_recovery_state": "payment_recovery",
        "recovery_period_calendar_days": 7,
        "initial_checkout_starts_access": False,
        "browser_return_starts_access": False,
        "provider_status_copied_into_reserved_state": False,
        "future_entitlement_source": (
            "verified_idempotent_order_safe_owner_bound_provider_observations_only"
        ),
    }
    representation = repr(lifecycle).lower()
    for provider_status in (
        "past_due",
        "unpaid",
        "incomplete",
        "trialing",
        "paused",
    ):
        assert provider_status not in representation


@pytest.mark.parametrize("owner", (None, True, False, 0, -1, 1.0, "7"))
def test_owner_root_requires_exact_positive_users_id(owner):
    with pytest.raises((TypeError, ValueError)):
        make_candidate(owner=owner)


def test_cross_owner_authentication_replay_and_named_owner_fail_closed():
    now = datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
    for override in (
        {"owner_user_id": 8},
        {"authentication_context": auth_context(8, now)},
        {"replay_snapshot": replay_snapshot(8, now)},
    ):
        with pytest.raises(ValueError, match="owner"):
            make_candidate(**override)


@pytest.mark.parametrize(
    "overrides",
    (
        {"catalogue_authority_version": "latest"},
        {"plan_key": "MONTHLY"},
        {"plan_key": "monthly_discounted"},
        {"gross_amount_minor": 1},
        {"currency": "USD"},
        {"recurring_interval_count": 12},
    ),
)
def test_wrong_version_plan_or_caller_supplied_commercial_facts_fail(overrides):
    with pytest.raises((TypeError, ValueError)):
        make_candidate(**overrides)


@pytest.mark.parametrize(
    "destination",
    (
        "https://reserved.example/return",
        "/v2/plans/monthly",
        "reserved_billing_success",
        "reserved_billing_return_reconciliation/other",
        True,
    ),
)
def test_return_destination_is_one_fixed_logical_allowlist_value(destination):
    with pytest.raises(ValueError, match="return destination"):
        make_candidate(return_destination_id=destination)


class StatefulTimezone(tzinfo):
    def utcoffset(self, value):
        return timedelta(0)

    def dst(self, value):
        return timedelta(0)


class StringSubclass(str):
    pass


@pytest.mark.parametrize(
    "overrides",
    (
        {
            "valid_until": datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc),
        },
        {
            "valid_until": datetime(2026, 9, 4, 12, 5, 0, 1, tzinfo=timezone.utc),
        },
        {
            "requested_at": datetime(2026, 9, 4, 12, 0, 1, tzinfo=timezone.utc),
        },
        {
            "evaluated_at": datetime(2026, 9, 4, 11, 59, 59, tzinfo=timezone.utc),
        },
        {
            "evaluated_at": datetime(2026, 9, 4, 12, 0, tzinfo=StatefulTimezone()),
        },
    ),
)
def test_stale_future_overlong_or_stateful_time_inputs_fail_closed(overrides):
    with pytest.raises((TypeError, ValueError)):
        make_candidate(**overrides)


@pytest.mark.parametrize(
    "overrides",
    (
        {"state": "used"},
        {"state": "ambiguous"},
        {"owner_user_id": 8},
        {"intent_id": "checkout_intent:other"},
        {"idempotency_key_digest": "sha256:" + "0" * 64},
        {
            "checked_at": datetime(2026, 9, 4, 11, 59, 59, tzinfo=timezone.utc)
        },
        {"existing_candidate_identity": "checkout-intent:sha256-" + "0" * 64},
    ),
)
def test_replayed_ambiguous_stale_or_conflicting_snapshot_fails(overrides):
    with pytest.raises((TypeError, ValueError)):
        make_candidate(replay_snapshot=replay_snapshot(**overrides))


@pytest.mark.parametrize(
    "overrides",
    (
        {
            "authentication_context": auth_context(
                schema_version=StringSubclass(
                    "reserved-authenticated-owner-context/1.0"
                )
            )
        },
        {
            "authentication_context": auth_context(
                trust_status=StringSubclass(
                    "future_authenticated_reserved_owner_adapter_structural_input_only"
                )
            )
        },
        {
            "replay_snapshot": replay_snapshot(
                schema_version=StringSubclass(
                    "reserved-checkout-intent-replay-snapshot/1.0"
                )
            )
        },
        {"replay_snapshot": replay_snapshot(state=StringSubclass("unused"))},
        {
            "replay_snapshot": replay_snapshot(
                intent_id=StringSubclass("checkout_intent:intent.001")
            )
        },
    ),
)
def test_subtyped_fixed_authentication_and_replay_facts_fail_closed(overrides):
    with pytest.raises((TypeError, ValueError)):
        make_candidate(**overrides)


@pytest.mark.parametrize(
    "overrides",
    (
        {"intent_id": "checkout_intent:sk_live_customer_secret"},
        {"idempotency_key": "checkout_idempotency:client_secret_value"},
        {"evidence_reference": "evidence:access_token_value"},
        {
            "authentication_context": auth_context(
                authentication_reference="evidence:credential_customer"
            )
        },
    ),
)
def test_retained_or_transient_identifiers_reject_secret_shapes(overrides):
    with pytest.raises(ValueError, match="secret-shaped"):
        make_candidate(**overrides)


def test_exact_call_shapes_ignore_mutated_callable_defaults():
    create = subject.create_checkout_request_candidate
    validate = subject.validate_checkout_request_candidate
    original_create_defaults = create.__defaults__
    original_create_kwdefaults = create.__kwdefaults__
    original_validate_defaults = validate.__defaults__
    try:
        create.__defaults__ = (7,)
        create.__kwdefaults__ = candidate_facts()
        validate.__defaults__ = (make_candidate(),)
        with pytest.raises(TypeError, match="exactly 1 positional"):
            create()
        with pytest.raises(TypeError, match="exactly 1 positional"):
            validate()
        assert subject.validate_checkout_request_candidate(make_candidate())
    finally:
        create.__defaults__ = original_create_defaults
        create.__kwdefaults__ = original_create_kwdefaults
        validate.__defaults__ = original_validate_defaults


def test_zero_partial_extra_duplicate_and_positional_substitution_fail_closed():
    facts = candidate_facts()
    with pytest.raises(TypeError, match="exactly 1 positional"):
        subject.create_checkout_request_candidate(**facts)
    with pytest.raises(TypeError, match="exactly 1 positional"):
        subject.create_checkout_request_candidate(7, 8, **facts)
    with pytest.raises(TypeError, match="exact complete"):
        subject.create_checkout_request_candidate(
            7, **{key: value for key, value in facts.items() if key != "plan_key"}
        )
    with pytest.raises(TypeError, match="unsupported fact"):
        subject.create_checkout_request_candidate(
            7, **(facts | {"authenticated_owner_user_id": 7})
        )
    with pytest.raises(TypeError, match="unsupported fact"):
        subject.create_checkout_request_candidate(7, **(facts | {"amount": 2900}))
    with pytest.raises(TypeError, match="exactly 1 positional"):
        subject.validate_checkout_request_candidate(make_candidate(), make_candidate())
    with pytest.raises(TypeError, match="unsupported fact"):
        subject.validate_checkout_request_candidate(make_candidate(), authority=True)


def test_input_mutation_after_creation_cannot_change_detached_candidate():
    facts = candidate_facts()
    candidate = subject.create_checkout_request_candidate(7, **facts)
    facts["authentication_context"]["owner_user_id"] = 999
    facts["replay_snapshot"]["state"] = "used"
    facts["plan_key"] = "yearly"
    projected = dict(candidate)
    assert projected["authenticated_owner_user_id"] == 7
    assert projected["plan_key"] == "monthly"
    assert projected["unit_amount_minor"] == 2900


@pytest.mark.parametrize(
    ("field", "replacement"),
    (
        ("authenticated_owner_user_id", 8),
        ("owner_reference", "users:8"),
        ("unit_amount_minor", 1),
        ("currency", "USD"),
        ("return_destination_id", "other"),
        ("replay_guard_status", "consumed"),
        ("candidate_identity", "checkout-intent:sha256-" + "0" * 64),
        ("authentication_runtime_verified", True),
    ),
)
def test_tampered_structural_candidates_fail_validation(field, replacement):
    candidate = make_candidate()
    tampered = tuple((key, replacement if key == field else value) for key, value in candidate)
    with pytest.raises((TypeError, ValueError)):
        subject.validate_checkout_request_candidate(tampered)


class IntSubclass(int):
    pass


def _replace_and_recompute_identity(candidate, field, replacement):
    replaced = tuple(
        (key, replacement if key == field else value) for key, value in candidate
    )
    without_identity = tuple(
        item for item in replaced if item[0] != "candidate_identity"
    )
    encoded = json.dumps(
        without_identity,
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("ascii")
    identity = "checkout-intent:sha256-" + hashlib.sha256(encoded).hexdigest()
    return tuple(
        (key, identity if key == "candidate_identity" else value)
        for key, value in replaced
    )


@pytest.mark.parametrize(
    "replacement",
    (True, False, 1.0, "1", None, IntSubclass(1)),
)
def test_recomputed_identity_cannot_mask_non_exact_recurring_count(replacement):
    forged = _replace_and_recompute_identity(
        make_candidate(), "recurring_interval_count", replacement
    )
    assert dict(forged)["candidate_identity"].startswith("checkout-intent:sha256-")
    with pytest.raises(ValueError, match="catalogue projection"):
        subject.validate_checkout_request_candidate(forged)


def test_detached_classes_mappings_subtypes_and_forged_shapes_never_gain_authority():
    class TupleSubclass(tuple):
        pass

    class Forged:
        authority_flags = (("checkout_session_creation_authority", True),)

    valid = make_candidate()
    for value in (dict(valid), list(valid), TupleSubclass(valid), Forged(), object()):
        with pytest.raises((TypeError, ValueError)):
            subject.validate_checkout_request_candidate(value)
    assert set(dict(dict(valid)["authority_flags"]).values()) == {False}


def _closure_objects(root):
    pending = [root]
    seen = set()
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        yield value
        if isinstance(value, FunctionType) and value.__closure__:
            pending.extend(cell.cell_contents for cell in value.__closure__)


def test_saved_protocol_resists_public_rebinding_and_has_no_mutable_registry_authority(
    monkeypatch,
):
    create = subject.create_checkout_request_candidate
    validate = subject.validate_checkout_request_candidate
    project = subject.project_checkout_intent_contract
    expected = make_candidate()
    monkeypatch.setattr(subject, "CONTRACT_VERSION", "forged")
    monkeypatch.setattr(subject, "CATALOGUE_AUTHORITY_VERSION", "forged")
    monkeypatch.setattr(subject, "hashlib", object(), raising=False)
    monkeypatch.setattr(subject, "json", object(), raising=False)
    monkeypatch.setattr(subject, "any", lambda values: False, raising=False)
    assert create(7, **candidate_facts()) == expected
    assert validate(expected) == expected
    assert dict(project())["catalogue_authority_version"] == (
        "FD-W10-001/2026-09-02/v1"
    )
    for exported in (create, validate, project):
        assert not any(type(value) in (dict, list, set) for value in _closure_objects(exported))


def test_structurally_recreated_candidate_is_still_explicit_zero_authority():
    original = make_candidate()
    recreated = tuple(tuple(item) for item in original)
    assert recreated == original and recreated is not original
    validated = dict(subject.validate_checkout_request_candidate(recreated))
    assert validated["candidate_status"].startswith("structural_candidate_not_")
    assert validated["authentication_runtime_verified"] is False
    assert set(dict(validated["authority_flags"]).values()) == {False}


def test_module_is_standard_library_only_and_exports_exact_surface():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imports = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imports == {"__future__", "datetime", "hashlib", "json", "re"}
    assert subject.__all__ == (
        "CONTRACT_VERSION",
        "CATALOGUE_AUTHORITY_VERSION",
        "project_checkout_intent_contract",
        "create_checkout_request_candidate",
        "validate_checkout_request_candidate",
    )
    for name in subject.__all__[2:]:
        function = getattr(subject, name)
        assert tuple(inspect.signature(function).parameters) == ("args", "kwargs")
        assert function.__defaults__ is None
        assert function.__kwdefaults__ is None


def test_document_preserves_exact_disabled_first_non_authority_boundary():
    text = DOC.read_text(encoding="utf-8")
    required = (
        BASE,
        TREE,
        "FD-W10-001",
        "FD-W10-002",
        "FD-W10-003",
        "payment_recovery",
        "seven calendar days",
        "zero entitlement",
        "structural candidate",
        "not authenticate",
        "no Stripe SDK",
        "does not complete W10-S4",
        "Q1",
        "Q2",
        "Q3",
    )
    for phrase in required:
        assert phrase.lower() in text.lower()
