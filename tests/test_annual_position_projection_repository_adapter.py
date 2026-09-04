"""Focused acceptance tests for the pure W9-S3C projection adapter."""

from __future__ import annotations

import dataclasses
import dis
import hashlib
import pickle
import types
from datetime import date, timedelta
from pathlib import Path

import pytest

import reserved.annual_position_persistence_contract as s3a
import reserved.annual_position_projection_repository_adapter as subject
import reserved.annual_position_repository_contract as s3b
from reserved.annual_position_persistence_contract import (
    AnnualPositionPersistenceProjection,
    admit_annual_position_projection,
    annual_position_projection_identity,
    supersede_annual_position_projection,
)
from reserved.annual_position_projection_repository_adapter import (
    ADAPTER_VERSION,
    AUTHORITY_STATUS,
    ProjectionRepositoryAdapterError,
    adapt_admitted_projection_to_structural_candidate,
    extract_structural_candidate,
    validate_projection_repository_adapter_operation,
)
from reserved.annual_position_repository_contract import (
    make_structural_candidate,
    structural_candidate_identity,
)
from tests.test_annual_to_cash_integration import compose
from tests.test_w8_annual_cash_customer_handoff import project


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "reserved" / "annual_position_projection_repository_adapter.py"
DOCUMENT = ROOT / "docs" / "W9_S3C_PROJECTION_REPOSITORY_ADAPTER.md"
BASE = "1d91526d11b5291d5388c78940682ca02edeb61e"
BASE_TREE = "e2fc725961f816d80eed9e5373d738e5e21a024c"
S3A_COMMIT = "c489c25bab669c64e1c11d28caf29fcde9678fdd"
S3A_HASH = "da68058811e1f1f3974851f3f85703c7b2d79e05695ed88c2980251a3c649469"
S3B_COMMIT = "110a90043dfc770c70059482be9d7b7e237749a6"
S3B_HASH = "fa033039500b97bab04f3a047c07ad661c14c49d6167d65396d4d9ab0227053e"
OWNED_PATHS = {
    "reserved/annual_position_projection_repository_adapter.py",
    "tests/test_annual_position_projection_repository_adapter.py",
    "docs/W9_S3C_PROJECTION_REPOSITORY_ADAPTER.md",
}


class PlainStr(str):
    """Benign subclass that must still be rejected at an exact boundary."""


class EvilStr(str):
    """Hostile subclass that attempts to make every equality check pass."""

    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    __hash__ = str.__hash__


def admitted(*, user_id="user-1", business_id="business-1"):
    annual = compose()
    result = project(annual, user_id=user_id, business_id=business_id)
    assert result is not None
    return annual, result, admit_annual_position_projection(annual, result)


def init_values(projection):
    return tuple(
        getattr(projection, field.name)
        for field in dataclasses.fields(projection)
        if field.init
    )


def adapt(projection, *, previous_projection=None, previous_candidate=None,
        user_id=None, business_id=None, evaluated_on=None):
    return adapt_admitted_projection_to_structural_candidate(
        projection=projection,
        authenticated_user_id=projection.user_id if user_id is None else user_id,
        authenticated_business_id=(
            projection.business_id if business_id is None else business_id
        ),
        evaluated_on=projection.as_of if evaluated_on is None else evaluated_on,
        previous_projection=previous_projection,
        previous_structural_candidate=previous_candidate,
    )


def operation_map(operation):
    return dict(validate_projection_repository_adapter_operation(operation))


def candidate_map(operation):
    return dict(extract_structural_candidate(operation))


def replace_pair(value, field, replacement):
    return tuple(
        (name, replacement if name == field else item) for name, item in value
    )


def test_exact_base_and_accepted_source_identities_are_bound():
    import subprocess

    assert subprocess.check_output(
        ["git", "rev-parse", f"{BASE}^{{tree}}"], cwd=ROOT, text=True
    ).strip() == BASE_TREE
    assert subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT
    ).returncode == 0
    assert hashlib.sha256(
        (ROOT / "reserved/annual_position_persistence_contract.py").read_bytes()
    ).hexdigest() == S3A_HASH
    assert hashlib.sha256(
        (ROOT / "reserved/annual_position_repository_contract.py").read_bytes()
    ).hexdigest() == S3B_HASH
    assert subject.SOURCE_S3A_COMMIT == S3A_COMMIT
    assert subject.SOURCE_S3A_SHA256 == S3A_HASH
    assert subject.SOURCE_S3B_COMMIT == S3B_COMMIT
    assert subject.SOURCE_S3B_SHA256 == S3B_HASH


def test_initial_projection_is_detached_to_exact_non_authoritative_candidate():
    _, _, projection = admitted()
    operation = adapt(projection)
    mapped = operation_map(operation)
    candidate = candidate_map(operation)

    assert mapped["adapter_version"] == ADAPTER_VERSION
    assert mapped["authority_status"] == AUTHORITY_STATUS
    assert mapped["source_projection_identity"] == (
        annual_position_projection_identity(projection)
    )
    assert mapped["source_predecessor_projection_identity"] is None
    assert mapped["structural_candidate_identity"] == structural_candidate_identity(
        mapped["structural_candidate"]
    )
    assert candidate["record_version"] == 1
    assert candidate["user_id"] == projection.user_id
    assert candidate["business_id"] == projection.business_id
    assert candidate["annual_cash_identity_admitted"] is False
    assert candidate["persistence_authority"] is False


def test_all_adapter_operation_authorities_are_permanently_false():
    _, _, projection = admitted()
    mapped = operation_map(adapt(projection))
    assert {
        key: mapped[key]
        for key in (
            "source_admission_transferred",
            "persistence_authority",
            "storage_authority",
            "migration_authority",
            "retention_authority",
            "deletion_authority",
            "legal_authority",
            "credential_authority",
            "encryption_or_key_custody_authority",
            "target_authority",
            "production_activation_authority",
            "release_authority",
        )
    } == {
        "source_admission_transferred": False,
        "persistence_authority": False,
        "storage_authority": False,
        "migration_authority": False,
        "retention_authority": False,
        "deletion_authority": False,
        "legal_authority": False,
        "credential_authority": False,
        "encryption_or_key_custody_authority": False,
        "target_authority": False,
        "production_activation_authority": False,
        "release_authority": False,
    }


def test_minimised_provenance_uncertainty_and_exact_primitives_are_preserved():
    _, _, projection = admitted()
    candidate = candidate_map(adapt(projection))
    assert candidate["evidence_references"] == projection.evidence_references
    assert candidate["ruleset_version"] == projection.ruleset_version
    assert candidate["stale_after_days"] == projection.stale_after_days
    assert candidate["customer_result_limitations"] == (
        projection.customer_result_limitations
    )
    assert candidate["customer_result_prohibited_uses"] == (
        projection.customer_result_prohibited_uses
    )
    assert candidate["unresolved_inputs"] == projection.unresolved_inputs
    assert candidate["annual_liability"] == str(projection.annual_liability)
    assert all(type(value) is str for _, value, *_ in candidate["obligations"])
    assert all(type(value) is str for _, value in candidate["adjustments"])

    def assert_primitive(value):
        assert type(value) in (tuple, str, int, bool, type(None))
        if type(value) is tuple:
            for item in value:
                assert_primitive(item)

    assert_primitive(extract_structural_candidate(adapt(projection)))


def test_same_live_projection_produces_deterministic_operation_and_candidate():
    _, _, projection = admitted()
    first = adapt(projection)
    second = adapt(projection)
    assert first == second
    assert extract_structural_candidate(first) == extract_structural_candidate(second)


def test_publicly_reconstructed_and_pickle_decoded_projections_are_rejected():
    _, _, projection = admitted()
    reconstructed = AnnualPositionPersistenceProjection(*init_values(projection))
    decoded = pickle.loads(pickle.dumps(projection))
    assert reconstructed.annual_cash_identity_admitted is False
    assert decoded.annual_cash_identity_admitted is False
    for value in (reconstructed, decoded):
        with pytest.raises(ProjectionRepositoryAdapterError, match="not admitted"):
            adapt(value)


def test_duck_typed_and_subclass_inputs_are_rejected():
    _, _, projection = admitted()

    class Pretend:
        annual_cash_identity_admitted = True

    class Text(str):
        pass

    with pytest.raises(ProjectionRepositoryAdapterError, match="exact W9-S3A"):
        adapt_admitted_projection_to_structural_candidate(
            projection=Pretend(),
            authenticated_user_id=projection.user_id,
            authenticated_business_id=projection.business_id,
            evaluated_on=projection.as_of,
            previous_projection=None,
            previous_structural_candidate=None,
        )
    with pytest.raises(ProjectionRepositoryAdapterError, match="exact strings"):
        adapt(projection, user_id=Text(projection.user_id))


def test_tampered_projection_is_rejected_before_detachment():
    _, _, projection = admitted()
    object.__setattr__(projection, "user_id", "attacker")
    with pytest.raises(ValueError):
        adapt(projection, user_id="attacker")


@pytest.mark.parametrize(
    ("user_id", "business_id", "message"),
    [
        ("other-user", None, "owner boundary"),
        (None, "other-business", "business boundary"),
    ],
)
def test_cross_owner_and_cross_business_inputs_fail_closed(
    user_id, business_id, message
):
    _, _, projection = admitted()
    with pytest.raises(ProjectionRepositoryAdapterError, match=message):
        adapt(projection, user_id=user_id, business_id=business_id)


def test_future_and_stale_projection_dates_fail_closed():
    _, _, projection = admitted()
    with pytest.raises(ProjectionRepositoryAdapterError, match="future"):
        adapt(projection, evaluated_on=projection.as_of - timedelta(days=1))
    with pytest.raises(ProjectionRepositoryAdapterError, match="stale"):
        adapt(
            projection,
            evaluated_on=projection.as_of
            + timedelta(days=projection.stale_after_days + 1),
        )
    # The exact end of the declared freshness horizon remains accepted.
    adapt(
        projection,
        evaluated_on=projection.as_of + timedelta(days=projection.stale_after_days),
    )


def test_date_subclass_is_rejected():
    _, _, projection = admitted()

    class DateSubclass(date):
        pass

    with pytest.raises(ProjectionRepositoryAdapterError, match="exact date"):
        adapt(projection, evaluated_on=DateSubclass.fromisoformat(str(projection.as_of)))


def test_successor_preserves_both_s3a_and_s3b_predecessor_chains():
    annual, result, previous = admitted()
    previous_operation = adapt(previous)
    previous_candidate = extract_structural_candidate(previous_operation)
    successor = supersede_annual_position_projection(previous, annual, result)

    operation = adapt(
        successor,
        previous_projection=previous,
        previous_candidate=previous_candidate,
    )
    mapped = operation_map(operation)
    candidate = candidate_map(operation)
    assert mapped["source_predecessor_projection_identity"] == (
        annual_position_projection_identity(previous)
    )
    assert mapped["source_predecessor_structural_candidate"] == previous_candidate
    assert mapped["source_predecessor_structural_candidate"] is not previous_candidate
    assert candidate["record_version"] == 2
    assert candidate["predecessor_identity"] == structural_candidate_identity(
        previous_candidate
    )


def test_successor_requires_both_exact_predecessor_inputs():
    annual, result, previous = admitted()
    successor = supersede_annual_position_projection(previous, annual, result)
    previous_candidate = extract_structural_candidate(adapt(previous))
    with pytest.raises(ProjectionRepositoryAdapterError, match="both predecessor"):
        adapt(successor)
    with pytest.raises(ProjectionRepositoryAdapterError, match="both predecessor"):
        adapt(successor, previous_projection=previous)
    with pytest.raises(ProjectionRepositoryAdapterError, match="both predecessor"):
        adapt(successor, previous_candidate=previous_candidate)


def test_initial_projection_rejects_injected_predecessor_inputs():
    _, _, initial = admitted()
    previous_candidate = extract_structural_candidate(adapt(initial))
    with pytest.raises(ProjectionRepositoryAdapterError, match="initial"):
        adapt(
            initial,
            previous_projection=initial,
            previous_candidate=previous_candidate,
        )


def test_successor_rejects_wrong_or_malformed_previous_candidate():
    annual, result, previous = admitted()
    successor = supersede_annual_position_projection(previous, annual, result)
    _, _, other = admitted(user_id="other-user", business_id="other-business")
    other_candidate = extract_structural_candidate(adapt(other))
    with pytest.raises(ProjectionRepositoryAdapterError, match="does not match"):
        adapt(
            successor,
            previous_projection=previous,
            previous_candidate=other_candidate,
        )
    with pytest.raises((ProjectionRepositoryAdapterError, s3b.RepositoryContractError)):
        adapt(
            successor,
            previous_projection=previous,
            previous_candidate=(("candidate_version", "malformed"),),
        )


def test_successor_rejects_unadmitted_or_cross_owner_previous_projection():
    annual, result, previous = admitted()
    successor = supersede_annual_position_projection(previous, annual, result)
    previous_candidate = extract_structural_candidate(adapt(previous))
    unadmitted = AnnualPositionPersistenceProjection(*init_values(previous))
    with pytest.raises(ProjectionRepositoryAdapterError, match="not admitted"):
        adapt(
            successor,
            previous_projection=unadmitted,
            previous_candidate=previous_candidate,
        )
    _, _, other = admitted(user_id="other-user", business_id="other-business")
    with pytest.raises(ProjectionRepositoryAdapterError, match="owner boundary"):
        adapt(
            successor,
            previous_projection=other,
            previous_candidate=previous_candidate,
        )


def test_operation_validation_rejects_tampered_identity_owner_and_authority():
    _, _, projection = admitted()
    operation = adapt(projection)
    bad_identity = replace_pair(
        operation,
        "structural_candidate_identity",
        "annual-position-structural:sha256-" + "0" * 64,
    )
    bad_owner = replace_pair(operation, "authenticated_user_id", "other-user")
    bad_authority = replace_pair(operation, "persistence_authority", True)
    for bad in (bad_identity, bad_owner, bad_authority):
        with pytest.raises(ProjectionRepositoryAdapterError):
            validate_projection_repository_adapter_operation(bad)


def test_operation_validation_rejects_bad_source_identity_and_date():
    _, _, projection = admitted()
    operation = adapt(projection)
    for field, value in (
        ("source_projection_identity", "not-an-identity"),
        ("evaluated_on", "2026-02-30"),
        ("evaluated_on", "04/09/2026"),
    ):
        with pytest.raises(ProjectionRepositoryAdapterError):
            validate_projection_repository_adapter_operation(
                replace_pair(operation, field, value)
            )
    stale = projection.as_of + timedelta(days=projection.stale_after_days + 1)
    with pytest.raises(ProjectionRepositoryAdapterError, match="freshness"):
        validate_projection_repository_adapter_operation(
            replace_pair(operation, "evaluated_on", stale.isoformat())
        )


@pytest.mark.parametrize(
    "field",
    (
        "adapter_version",
        "authority_status",
        "source_s3a_commit",
        "source_s3a_sha256",
        "source_s3b_commit",
        "source_s3b_sha256",
        "source_projection_identity",
        "structural_candidate_identity",
    ),
)
@pytest.mark.parametrize("text_type", (PlainStr, EvilStr))
def test_operation_fixed_provenance_and_identity_fields_require_exact_strings(
    field, text_type
):
    _, _, projection = admitted()
    operation = adapt(projection)
    original = dict(operation)[field]
    hostile = text_type(original if text_type is PlainStr else "attacker")
    with pytest.raises(ProjectionRepositoryAdapterError):
        validate_projection_repository_adapter_operation(
            replace_pair(operation, field, hostile)
        )


@pytest.mark.parametrize("text_type", (PlainStr, EvilStr))
def test_successor_source_predecessor_identity_requires_an_exact_string(text_type):
    annual, result, previous = admitted()
    previous_candidate = extract_structural_candidate(adapt(previous))
    successor = supersede_annual_position_projection(previous, annual, result)
    operation = adapt(
        successor,
        previous_projection=previous,
        previous_candidate=previous_candidate,
    )
    original = dict(operation)["source_predecessor_projection_identity"]
    hostile = text_type(original if text_type is PlainStr else "attacker")
    with pytest.raises(ProjectionRepositoryAdapterError):
        validate_projection_repository_adapter_operation(
            replace_pair(operation, "source_predecessor_projection_identity", hostile)
        )


def test_successor_rejects_regex_valid_source_predecessor_substitution():
    annual, result, previous = admitted()
    previous_candidate = extract_structural_candidate(adapt(previous))
    successor = supersede_annual_position_projection(previous, annual, result)
    operation = adapt(
        successor,
        previous_projection=previous,
        previous_candidate=previous_candidate,
    )
    substitute = "annual-position-persistence:sha256-" + "f" * 64
    assert substitute != dict(operation)["source_predecessor_projection_identity"]
    with pytest.raises(ProjectionRepositoryAdapterError, match="not reproducible"):
        validate_projection_repository_adapter_operation(
            replace_pair(operation, "source_predecessor_projection_identity", substitute)
        )


def test_successor_rejects_recomputed_structural_predecessor_substitution():
    annual, result, previous = admitted()
    previous_candidate = extract_structural_candidate(adapt(previous))
    successor = supersede_annual_position_projection(previous, annual, result)
    operation = adapt(
        successor,
        previous_projection=previous,
        previous_candidate=previous_candidate,
    )
    current_candidate = dict(operation)["structural_candidate"]
    substituted_previous = replace_pair(
        previous_candidate,
        "stale_after_days",
        dict(previous_candidate)["stale_after_days"] + 1,
    )
    substituted_current = replace_pair(
        current_candidate,
        "predecessor_identity",
        structural_candidate_identity(substituted_previous),
    )
    tampered = replace_pair(
        operation, "source_predecessor_structural_candidate", substituted_previous
    )
    tampered = replace_pair(tampered, "structural_candidate", substituted_current)
    tampered = replace_pair(
        tampered,
        "structural_candidate_identity",
        structural_candidate_identity(substituted_current),
    )
    # The substituted prior content does not match the bound S3A predecessor.
    with pytest.raises(ProjectionRepositoryAdapterError, match="source predecessor"):
        validate_projection_repository_adapter_operation(tampered)


def test_successor_rejects_cross_owner_business_prior_chain():
    annual, result, previous = admitted()
    previous_candidate = extract_structural_candidate(adapt(previous))
    successor = supersede_annual_position_projection(previous, annual, result)
    operation = adapt(
        successor,
        previous_projection=previous,
        previous_candidate=previous_candidate,
    )
    _, _, other = admitted(user_id="other-user", business_id="other-business")
    changed_previous = extract_structural_candidate(adapt(other))
    changed_current = replace_pair(
        dict(operation)["structural_candidate"],
        "predecessor_identity",
        structural_candidate_identity(changed_previous),
    )
    tampered = replace_pair(
        operation, "source_predecessor_structural_candidate", changed_previous
    )
    tampered = replace_pair(
        tampered,
        "source_predecessor_projection_identity",
        annual_position_projection_identity(other),
    )
    tampered = replace_pair(tampered, "structural_candidate", changed_current)
    tampered = replace_pair(
        tampered,
        "structural_candidate_identity",
        structural_candidate_identity(changed_current),
    )
    with pytest.raises(ProjectionRepositoryAdapterError, match="chain boundary"):
        validate_projection_repository_adapter_operation(tampered)


def test_successor_rejects_coherent_wrong_version_prior_chain():
    annual, result, previous = admitted()
    previous_candidate = extract_structural_candidate(adapt(previous))
    successor = supersede_annual_position_projection(previous, annual, result)
    successor_candidate = extract_structural_candidate(
        adapt(
            successor,
            previous_projection=previous,
            previous_candidate=previous_candidate,
        )
    )
    operation = adapt(
        successor,
        previous_projection=previous,
        previous_candidate=previous_candidate,
    )
    changed_current = replace_pair(
        dict(operation)["structural_candidate"],
        "predecessor_identity",
        structural_candidate_identity(successor_candidate),
    )
    tampered = replace_pair(
        operation, "source_predecessor_structural_candidate", successor_candidate
    )
    tampered = replace_pair(
        tampered,
        "source_predecessor_projection_identity",
        annual_position_projection_identity(successor),
    )
    tampered = replace_pair(tampered, "structural_candidate", changed_current)
    tampered = replace_pair(
        tampered,
        "structural_candidate_identity",
        structural_candidate_identity(changed_current),
    )
    with pytest.raises(ProjectionRepositoryAdapterError, match="version progression"):
        validate_projection_repository_adapter_operation(tampered)


def test_regex_valid_random_source_identity_cannot_replace_content_provenance():
    _, _, projection = admitted()
    operation = adapt(projection)
    substitute = "annual-position-persistence:sha256-" + "f" * 64
    assert substitute != dict(operation)["source_projection_identity"]
    with pytest.raises(ProjectionRepositoryAdapterError, match="not reproducible"):
        validate_projection_repository_adapter_operation(
            replace_pair(operation, "source_projection_identity", substitute)
        )


def test_candidate_substitution_requires_matching_recomputed_source_identity():
    _, _, projection = admitted()
    operation = adapt(projection)
    candidate = dict(operation)["structural_candidate"]
    changed_candidate = replace_pair(
        candidate, "stale_after_days", dict(candidate)["stale_after_days"] + 1
    )
    tampered = replace_pair(operation, "structural_candidate", changed_candidate)
    tampered = replace_pair(
        tampered,
        "structural_candidate_identity",
        structural_candidate_identity(changed_candidate),
    )
    with pytest.raises(ProjectionRepositoryAdapterError, match="not reproducible"):
        validate_projection_repository_adapter_operation(tampered)


def test_structural_copy_is_valid_but_cannot_become_issuance_or_persistence_authority():
    _, _, projection = admitted()
    operation = tuple(tuple(pair) for pair in adapt(projection))
    # The operation is deliberately detached and structurally reproducible;
    # validation is not an issuer registry or admission claim.
    validated = validate_projection_repository_adapter_operation(operation)
    assert validated == operation
    assert validated is not operation
    assert dict(validated)["structural_candidate"] is not dict(operation)[
        "structural_candidate"
    ]

    def assert_detached(left, right):
        if type(left) is tuple:
            assert left is not right
            for left_item, right_item in zip(left, right, strict=True):
                assert_detached(left_item, right_item)

    assert_detached(
        dict(validated)["structural_candidate"],
        dict(operation)["structural_candidate"],
    )
    assert operation_map(operation)["source_admission_transferred"] is False
    assert candidate_map(operation)["annual_cash_identity_admitted"] is False
    assert candidate_map(operation)["persistence_authority"] is False


def test_rebinding_s3a_s3b_exports_and_adapter_globals_cannot_change_acceptance(
    monkeypatch,
):
    _, _, projection = admitted()
    monkeypatch.setattr(s3a, "annual_position_projection_identity", lambda _: "forged")
    monkeypatch.setattr(s3a, "validate_supersession_chain", lambda *a, **k: None)
    monkeypatch.setattr(s3b, "make_structural_candidate", lambda **k: ())
    monkeypatch.setattr(s3b, "structural_candidate_identity", lambda _: "forged")
    monkeypatch.setattr(subject, "ADAPTER_VERSION", "attacker")
    monkeypatch.setattr(subject, "ProjectionRepositoryAdapterError", RuntimeError)
    operation = adapt(projection)
    assert operation_map(operation)["adapter_version"] == ADAPTER_VERSION
    assert candidate_map(operation)["record_version"] == 1


def test_class_descriptor_masking_cannot_turn_reconstruction_into_admitted(
    monkeypatch,
):
    _, _, projection = admitted()
    reconstructed = AnnualPositionPersistenceProjection(*init_values(projection))
    monkeypatch.setattr(
        AnnualPositionPersistenceProjection,
        "annual_cash_identity_admitted",
        property(lambda _: True),
    )
    assert reconstructed.annual_cash_identity_admitted is True
    with pytest.raises(ProjectionRepositoryAdapterError, match="not admitted"):
        adapt(reconstructed)


def test_mutating_captured_upstream_code_or_closure_is_detected():
    _, _, projection = admitted()
    original_code = annual_position_projection_identity.__code__

    def make_forged_code():
        first = second = None

        def forged(_):
            return first, second

        return forged.__code__

    try:
        annual_position_projection_identity.__code__ = make_forged_code()
        with pytest.raises(ProjectionRepositoryAdapterError, match="altered"):
            adapt(projection)
    finally:
        annual_position_projection_identity.__code__ = original_code

    cell = dict(
        zip(
            annual_position_projection_identity.__code__.co_freevars,
            annual_position_projection_identity.__closure__,
            strict=True,
        )
    )["_validate_projection"]
    original = cell.cell_contents
    try:
        cell.cell_contents = lambda value: value
        with pytest.raises(ProjectionRepositoryAdapterError, match="altered"):
            adapt(projection)
    finally:
        cell.cell_contents = original


def test_mutable_callable_defaults_cannot_supply_missing_authority_facts():
    _, _, projection = admitted()
    fn = adapt_admitted_projection_to_structural_candidate
    original = fn.__kwdefaults__
    try:
        fn.__kwdefaults__ = {
            "projection": projection,
            "authenticated_user_id": projection.user_id,
            "authenticated_business_id": projection.business_id,
            "evaluated_on": projection.as_of,
            "previous_projection": None,
            "previous_structural_candidate": None,
        }
        with pytest.raises(TypeError, match="exact named call shape"):
            fn()
    finally:
        fn.__kwdefaults__ = original


def test_missing_extra_positional_and_malformed_call_shapes_fail_closed():
    _, _, projection = admitted()
    with pytest.raises(TypeError, match="exact named call shape"):
        adapt_admitted_projection_to_structural_candidate(projection)
    with pytest.raises(TypeError, match="exact named call shape"):
        adapt_admitted_projection_to_structural_candidate(projection=projection)
    values = {
        "projection": projection,
        "authenticated_user_id": projection.user_id,
        "authenticated_business_id": projection.business_id,
        "evaluated_on": projection.as_of,
        "previous_projection": None,
        "previous_structural_candidate": None,
        "extra": "not-allowed",
    }
    with pytest.raises(TypeError, match="exact named call shape"):
        adapt_admitted_projection_to_structural_candidate(**values)


def test_local_acceptance_graph_has_no_mutable_global_resolution_or_registry():
    roots = (
        adapt_admitted_projection_to_structural_candidate,
        validate_projection_repository_adapter_operation,
        extract_structural_candidate,
    )
    seen, stack = set(), list(roots)
    mutable_cells = []
    while stack:
        fn = stack.pop()
        if type(fn) is not types.FunctionType or id(fn) in seen:
            continue
        seen.add(id(fn))
        if fn.__module__ == subject.__name__:
            global_loads = {
                instruction.argval
                for instruction in dis.get_instructions(fn)
                if instruction.opname.startswith("LOAD_GLOBAL")
            }
            assert not global_loads, (fn.__qualname__, global_loads)
        for cell in fn.__closure__ or ():
            try:
                value = cell.cell_contents
            except ValueError:
                continue
            if type(value) is types.FunctionType:
                stack.append(value)
            elif type(value) in (dict, list, set, bytearray):
                mutable_cells.append((fn.__qualname__, type(value).__name__))
    assert not mutable_cells
    source = MODULE.read_text(encoding="utf-8")
    for forbidden in (
        "WeakValueDictionary",
        "registry =",
        "registries =",
        "issuer_token",
        "admission_authority = True",
        "persistence_authority = True",
    ):
        assert forbidden not in source


def test_module_is_pure_and_has_no_database_network_environment_or_credential_io():
    source = MODULE.read_text(encoding="utf-8")
    forbidden = (
        "import os",
        "import socket",
        "import subprocess",
        "import requests",
        "import flask",
        "import sqlite3",
        "import pathlib",
        "import tempfile",
        "import urllib",
        "open(",
        "os.environ",
        "getenv(",
        ".execute(",
        ".commit(",
        "migration",
    )
    # The word migration appears only in fixed denied-authority fields/doccopy.
    for token in forbidden[:-1]:
        assert token not in source, token
    assert "migration_authority" in source


def test_candidate_changes_only_the_three_new_w9_s3c_paths():
    import subprocess

    changed = subprocess.check_output(
        ["git", "diff", "--name-only", "HEAD"], cwd=ROOT, text=True
    ).splitlines()
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    assert set(changed + untracked) <= OWNED_PATHS


def test_evidence_document_preserves_every_residual_gate_and_non_authority():
    text = " ".join(DOCUMENT.read_text(encoding="utf-8").split())
    for phrase in (
        "no datastore",
        "no migration",
        "no persistence authority",
        "no retention or deletion authority",
        "no legal, credential, encryption or key-custody authority",
        "no target, activation, release or production authority",
        "source admission is not transferred",
        "field-by-field lifecycle",
        "authenticated runtime owner adapter",
        "physical schema",
        "durable read/write",
        "access audit",
        "whole-account erasure",
        "backup expiry",
        "raw-payslip deletion",
        "not W9-S3 completion",
        "not security or launch assurance",
    ):
        assert phrase in text


def test_public_api_is_exact_and_does_not_export_an_authority_minter():
    assert subject.__all__ == [
        "ADAPTER_VERSION",
        "AUTHORITY_STATUS",
        "SOURCE_S3A_COMMIT",
        "SOURCE_S3A_SHA256",
        "SOURCE_S3B_COMMIT",
        "SOURCE_S3B_SHA256",
        "ProjectionRepositoryAdapterError",
        "adapt_admitted_projection_to_structural_candidate",
        "validate_projection_repository_adapter_operation",
        "extract_structural_candidate",
    ]
    for name in subject.__all__:
        assert hasattr(subject, name)
    assert not hasattr(subject, "persist")
    assert not hasattr(subject, "write")
    assert not hasattr(subject, "activate")
