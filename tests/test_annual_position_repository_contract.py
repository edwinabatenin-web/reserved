"""Focused acceptance tests for the detached W9-S3B structural contract."""

from __future__ import annotations

import copy
import dis
import gc
import hashlib
import json
import pickle
import subprocess
import sys
import textwrap
import types
import weakref
from pathlib import Path

import pytest

import reserved.annual_position_repository_contract as module
from reserved.annual_position_repository_contract import (
    SOURCE_S3A_COMMIT,
    SOURCE_S3A_SHA256,
    STRUCTURAL_STATUS,
    AnnualPositionRecordHandle,
    RepositoryContractError,
    bind_governance_inputs,
    copy_annual_position_record,
    decide_initial_create,
    decide_supersession_cas,
    decode_annual_position_record,
    governance_gate,
    make_structural_candidate,
    plan_account_deletion,
    prepare_annual_position_record,
    prepare_supersession,
    project_annual_position_record,
    project_deletion_plan,
    project_governance_inputs,
    project_operation_plan,
    project_read_result,
    read_owned_record,
    reconstruct_read_structural_candidate,
    repository_record_identity,
    structural_candidate_identity,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reserved" / "annual_position_repository_contract.py"


def _governance(suffix="v1"):
    return bind_governance_inputs(
        retention_policy_version=f"retention:{suffix}",
        erasure_disposition=f"erasure:{suffix}",
        crypto_key_version=f"crypto:{suffix}",
        target_profile=f"target:{suffix}",
    )


def _candidate(*, user_id="user-1", annual_liability="3486.00", record_version=1,
               predecessor_identity=None, cash_suffix="a", result_suffix="b"):
    return make_structural_candidate(
        record_version=record_version,
        user_id=user_id,
        business_id="business-1",
        tax_year="2026/27",
        nation="England",
        annual_cash_identity="annual-to-cash-position:sha256-" + cash_suffix * 64,
        customer_result_identity="w8-customer-result:sha256-" + result_suffix * 64,
        evidence_classification="qualified_local_estimate",
        annual_liability=annual_liability,
        obligations=(
            ("balancing_payment", annual_liability, "2028-01-31"),
            ("first_payment_on_account", "600.00", "2028-01-31"),
            ("second_payment_on_account", "600.00", "2028-07-31"),
        ),
        adjustments=(
            ("deductions_and_credits", "0.00"),
            ("prior_payments_on_account", "0.00"),
            ("payments_made", "0.00"),
            ("credit_or_refund", "0.00"),
        ),
        funding="exact",
        funding_amount=None,
        evidence_references=("annual-no-loan", "cash:deductions-credits", "charge-balancing"),
        ruleset_version="uk-2026-27-v4",
        as_of="2027-04-05",
        stale_after_days=45,
        predecessor_identity=predecessor_identity,
    )


def _record(*, governance=None, **candidate_kwargs):
    governance = governance or _governance()
    candidate = _candidate(**candidate_kwargs)
    return candidate, prepare_annual_position_record(candidate, governance), governance


def _replace_pair(value, name, replacement):
    return tuple((key, replacement if key == name else old) for key, old in value)


def _repack(envelope, *, row=None, evidence=None, version=None):
    row = envelope[2] if row is None else row
    evidence = envelope[3] if evidence is None else evidence
    payload = json.dumps((row, evidence), separators=(",", ":"), ensure_ascii=True).encode()
    digest = "annual-position-record:sha256-" + hashlib.sha256(payload).hexdigest()
    return (envelope[0] if version is None else version, digest, row, evidence)


def test_s3a_pins_are_design_provenance_only():
    assert SOURCE_S3A_COMMIT == "c489c25bab669c64e1c11d28caf29fcde9678fdd"
    assert SOURCE_S3A_SHA256 == "da68058811e1f1f3974851f3f85703c7b2d79e05695ed88c2980251a3c649469"
    source = ROOT / "reserved" / "annual_position_persistence_contract.py"
    assert hashlib.sha256(source.read_bytes()).hexdigest() == SOURCE_S3A_SHA256
    text = SOURCE.read_text()
    assert "import reserved.annual_position_persistence_contract" not in text
    assert "from reserved.annual_position_persistence_contract" not in text
    assert "marshal" not in text and "__closure__" not in text and "co_freevars" not in text


def test_arbitrary_s3a_exports_functions_and_closure_cells_are_never_consumed():
    script = textwrap.dedent(
        """
        import sys, types
        fake = types.ModuleType("reserved.annual_position_persistence_contract")
        class FakeProjection:
            annual_cash_identity_admitted = True
        def factory():
            captured = "original"
            def fake_identity(value):
                return captured, value
            return fake_identity
        fake_identity = factory()
        fake_identity.__closure__[0].cell_contents = "mutated-closure"
        fake.AnnualPositionPersistenceProjection = FakeProjection
        fake.annual_position_projection_identity = fake_identity
        fake.validate_supersession_chain = lambda *args: True
        fake.supersede_annual_position_projection = lambda *args: FakeProjection()
        fake.admit_annual_position_projection = lambda *args: FakeProjection()
        sys.modules[fake.__name__] = fake
        import reserved.annual_position_repository_contract as contract
        governance = contract.bind_governance_inputs(
            retention_policy_version="retention:v1", erasure_disposition="erasure:v1",
            crypto_key_version="crypto:v1", target_profile="target:v1")
        candidate = contract.make_structural_candidate(
            record_version=1, user_id="user-1", business_id="business-1",
            tax_year="2026/27", nation="England",
            annual_cash_identity="annual-to-cash-position:sha256-" + "a" * 64,
            customer_result_identity="w8-customer-result:sha256-" + "b" * 64,
            evidence_classification="qualified_local_estimate", annual_liability="1.00",
            obligations=(("balancing_payment", "1.00", "2028-01-31"),),
            adjustments=(("deductions_and_credits", "0.00"),), funding="exact",
            funding_amount=None, evidence_references=("evidence:one",),
            ruleset_version="rules-v1", as_of="2027-04-05", stale_after_days=45)
        assert dict(candidate)["annual_cash_identity_admitted"] is False
        contract.prepare_annual_position_record(candidate, governance)
        for forged in (FakeProjection(), (("annual_cash_identity_admitted", True),)):
            try: contract.prepare_annual_position_record(forged, governance)
            except Exception: pass
            else: raise AssertionError("forged runtime or primitive input was accepted")
        """
    )
    subprocess.run([sys.executable, "-c", script], cwd=ROOT, check=True, capture_output=True)


def test_valid_detached_fixture_is_explicitly_non_admitted_and_has_no_persistence_authority():
    candidate, record, _ = _record()
    cm = dict(candidate); row = dict(project_annual_position_record(record)[2])
    assert cm["authority_status"] == row["authority_status"] == STRUCTURAL_STATUS
    assert cm["annual_cash_identity_admitted"] is False
    assert cm["persistence_authority"] is row["persistence_authority"] is False


def test_governance_is_required_and_never_grants_storage_authority():
    assert dict(governance_gate())["status"] == "blocked"
    projected = dict(project_governance_inputs(_governance()))
    assert projected["authority_status"] == STRUCTURAL_STATUS
    assert projected["persistence_authority"] is False
    assert projected["storage_authority"] is False
    with pytest.raises(RepositoryContractError):
        prepare_annual_position_record(_candidate(), None)


@pytest.mark.parametrize("field,value", [
    ("retention_policy_version", "retention:pending"),
    ("erasure_disposition", "retention:v1"),
    ("crypto_key_version", "crypto:secret-value"),
    ("target_profile", "target:tbd"),
])
def test_unresolved_swapped_or_secret_governance_fails(field, value):
    values = dict(retention_policy_version="retention:v1", erasure_disposition="erasure:v1",
                  crypto_key_version="crypto:v1", target_profile="target:v1")
    values[field] = value
    with pytest.raises(RepositoryContractError): bind_governance_inputs(**values)


def test_exact_builtin_shape_rejects_objects_lists_and_authority_forgery():
    governance = _governance(); candidate = _candidate()
    class Fake: annual_cash_identity_admitted = True
    for forged in (Fake(), list(candidate), _replace_pair(candidate, "annual_cash_identity_admitted", True),
                   _replace_pair(candidate, "persistence_authority", True)):
        with pytest.raises(RepositoryContractError): prepare_annual_position_record(forged, governance)


@pytest.mark.parametrize("field,value", [
    ("user_id", "bad user"), ("business_id", "user-1"), ("tax_year", "2026/29"),
    ("nation", "GB"), ("record_purpose", "different"), ("annual_liability", "1.0"),
    ("as_of", "2027-02-30"), ("stale_after_days", True),
])
def test_forged_structural_primitives_fail_local_validation(field, value):
    with pytest.raises(RepositoryContractError):
        prepare_annual_position_record(_replace_pair(_candidate(), field, value), _governance())


def test_duplicate_or_malformed_evidence_and_facts_fail():
    candidate = _candidate(); governance = _governance()
    bad_values = (
        _replace_pair(candidate, "evidence_references", ("same", "same")),
        _replace_pair(candidate, "obligations", (("unknown", "1.00", "2028-01-31"),)),
        _replace_pair(candidate, "adjustments", (("deductions_and_credits", "-1.00"),)),
    )
    for bad in bad_values:
        with pytest.raises(RepositoryContractError): prepare_annual_position_record(bad, governance)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: _replace_pair(c, "evidence_classification", "hmrc_confirmed_exact"),
        lambda c: _replace_pair(
            _replace_pair(c, "funding", "gap"), "funding_amount", "0.00"
        ),
        lambda c: _replace_pair(
            _replace_pair(c, "funding", "surplus"), "funding_amount", "0.00"
        ),
        lambda c: _replace_pair(c, "funding_amount", "0.00"),
        lambda c: _replace_pair(c, "evidence_references", ("sk_live_customer_secret",)),
        lambda c: _replace_pair(
            c, "evidence_references", ("source:sha256-" + "a" * 64,)
        ),
        lambda c: _replace_pair(c, "user_id", "credential_customer_1"),
        lambda c: _replace_pair(c, "business_id", "access_key_business_1"),
        lambda c: _replace_pair(c, "ruleset_version", "rules/unsafe"),
        lambda c: _replace_pair(c, "stale_after_days", -1),
    ],
    ids=(
        "only-qualified-local-estimate",
        "gap-must-be-nonzero",
        "surplus-must-be-nonzero",
        "exact-funding-has-no-amount",
        "secret-evidence-reference",
        "digest-provenance-reference",
        "credential-owner",
        "access-key-business",
        "ruleset-slash",
        "negative-staleness",
    ),
)
def test_locally_mirrored_s3a_minimisation_invariants_reject_drift(mutate):
    with pytest.raises(RepositoryContractError):
        prepare_annual_position_record(mutate(_candidate()), _governance())


@pytest.mark.parametrize(
    "candidate",
    [
        _replace_pair(_candidate(), "stale_after_days", 0),
        _replace_pair(
            _replace_pair(_candidate(), "funding", "gap"),
            "funding_amount",
            "0.01",
        ),
        _replace_pair(
            _replace_pair(_candidate(), "funding", "surplus"),
            "funding_amount",
            "1.00",
        ),
        _replace_pair(_candidate(), "ruleset_version", "rules.safe:1"),
        _replace_pair(_candidate(), "evidence_references", ("x" * 160,)),
    ],
    ids=(
        "zero-staleness-is-source-valid",
        "positive-gap",
        "positive-surplus",
        "ruleset-reference-grammar",
        "source-reference-max-length",
    ),
)
def test_locally_mirrored_s3a_boundary_values_are_accepted(candidate):
    record = prepare_annual_position_record(candidate, _governance())
    assert dict(project_annual_position_record(record)[2])["persistence_authority"] is False


def test_exact_money_changes_structural_identity_without_float_conversion():
    first = _candidate(annual_liability="1.00"); second = _candidate(annual_liability="1.01")
    assert structural_candidate_identity(first) != structural_candidate_identity(second)
    assert dict(first)["annual_liability"] == "1.00"


def test_record_and_evidence_rows_preserve_owner_boundaries():
    candidate, record, _ = _record(); envelope = project_annual_position_record(record)
    row = dict(envelope[2]); evidence = envelope[3]
    assert row["record_identity"] == structural_candidate_identity(candidate)
    assert all(item[0] == row["record_identity"] for item in evidence)
    assert all(item[2:4] == ("user-1", "business-1") for item in evidence)


def test_unknown_schema_and_recomputed_tamper_fail_closed():
    _, record, governance = _record(); env = project_annual_position_record(record)
    row = _replace_pair(env[2], "repository_contract_version", "unknown/9")
    with pytest.raises(RepositoryContractError): decode_annual_position_record(_repack(env, row=row), governance, "audit:schema")
    with pytest.raises(RepositoryContractError): decode_annual_position_record(_repack(env, version="unknown/9"), governance, "audit:envelope")
    evidence = list(env[3]); evidence[0] = (evidence[0][0], 0, "user-2", evidence[0][3], evidence[0][4])
    with pytest.raises(RepositoryContractError): decode_annual_position_record(_repack(env, evidence=tuple(evidence)), governance, "audit:evidence")


def test_governance_profile_change_blocks_decode():
    _, record, governance = _record()
    with pytest.raises(RepositoryContractError):
        decode_annual_position_record(project_annual_position_record(record), _governance("v2"), "audit:profile")


def test_initial_create_is_insert_then_idempotent_and_conflict_is_rejected():
    _, record, governance = _record()
    first = dict(project_operation_plan(decide_initial_create((), record, governance, "audit:create")))
    assert first["status"] == "insert_structural_candidate"
    assert first["persistence_authority"] is False
    same = copy_annual_position_record(record)
    assert dict(project_operation_plan(decide_initial_create((same,), record, governance, "audit:same")))["status"] == "idempotent_existing"
    _, different, _ = _record(governance=governance, annual_liability="1.00")
    with pytest.raises(RepositoryContractError): decide_initial_create((record,), different, governance, "audit:conflict")


def test_optimistic_supersession_is_structural_cas_only():
    first_candidate, first, governance = _record()
    successor = _candidate(record_version=2, predecessor_identity=structural_candidate_identity(first_candidate), cash_suffix="c")
    plan = prepare_supersession(first, successor, expected_record_version=1, governance=governance, audit_reference="audit:supersede")
    apply = dict(project_operation_plan(decide_supersession_cas(first, plan, governance)))
    assert apply["status"] == "cas_apply_contract_only" and apply["persistence_authority"] is False
    second = decode_annual_position_record(apply["candidate_record"], governance, "audit:second")
    assert dict(project_operation_plan(decide_supersession_cas(second, plan, governance)))["status"] == "cas_conflict"


def test_stale_version_and_cross_boundary_supersession_fail():
    candidate, record, governance = _record()
    successor = _candidate(record_version=2, predecessor_identity=structural_candidate_identity(candidate))
    with pytest.raises(RepositoryContractError): prepare_supersession(record, successor, expected_record_version=2, governance=governance, audit_reference="audit:stale")
    crossed = _replace_pair(successor, "user_id", "user-2")
    with pytest.raises(RepositoryContractError): prepare_supersession(record, crossed, expected_record_version=1, governance=governance, audit_reference="audit:crossed")


def test_owner_read_returns_only_non_admitted_structural_candidate():
    candidate, record, governance = _record(); identity = repository_record_identity(record)
    read = read_owned_record((record,), requester_user_id="user-1", record_identity=identity, governance=governance, audit_reference="audit:read")
    rebuilt = reconstruct_read_structural_candidate(read)
    assert rebuilt == candidate and dict(rebuilt)["annual_cash_identity_admitted"] is False
    assert dict(project_read_result(read))["database_read_performed"] is False
    with pytest.raises(RepositoryContractError): read_owned_record((record,), requester_user_id="user-2", record_identity=identity, governance=governance, audit_reference="audit:cross-owner")


def test_deletion_planning_claims_no_deletion_backup_or_persistence():
    _, record, governance = _record(); identity = repository_record_identity(record)
    plan = plan_account_deletion((record,), requester_user_id="user-1", requested_record_identities=(identity,), governance=governance, audit_reference="audit:delete")
    state = dict(project_deletion_plan(plan))
    assert state["deletion_performed"] is state["backup_deletion_claimed"] is False
    assert state["persistence_authority"] is state["storage_authority"] is False


def test_unsafe_audit_reference_fails():
    _, record, governance = _record()
    for value in ("email address", "audit:token-value", "audit:pending"):
        with pytest.raises(RepositoryContractError): decide_initial_create((), record, governance, value)


def test_handle_forgery_copy_and_pickle_boundaries():
    _, record, _ = _record(); forged = object.__new__(AnnualPositionRecordHandle)
    with pytest.raises(RepositoryContractError): project_annual_position_record(forged)
    assert project_annual_position_record(copy.copy(record)) == project_annual_position_record(record)
    assert project_annual_position_record(copy.deepcopy(record)) == project_annual_position_record(record)
    with pytest.raises(RepositoryContractError): pickle.dumps(record)


def _all_handles():
    governance = _governance(); _, record, _ = _record(governance=governance)
    identity = repository_record_identity(record)
    operation = decide_initial_create((), record, governance, "audit:handles-operation")
    read = read_owned_record((record,), requester_user_id="user-1", record_identity=identity, governance=governance, audit_reference="audit:handles-read")
    deletion = plan_account_deletion((record,), requester_user_id="user-1", requested_record_identities=(identity,), governance=governance, audit_reference="audit:handles-delete")
    return governance, record, operation, read, deletion


def test_identity_dispatch_resists_hash_equality_constructor_and_descriptor_mutation(monkeypatch):
    handles = _all_handles()
    projectors = (project_governance_inputs, project_annual_position_record, project_operation_plan, project_read_result, project_deletion_plan)
    for handle in handles:
        cls = type(handle)
        monkeypatch.setattr(cls, "__hash__", lambda self: 1, raising=False)
        monkeypatch.setattr(cls, "__eq__", lambda self, other: True, raising=False)
        monkeypatch.setattr(cls, "__new__", lambda cls, *args: object.__new__(cls))
        monkeypatch.setattr(cls, "metadata", property(lambda self: "forged"), raising=False)
    for handle, projector in zip(handles, projectors):
        projector(handle)
        for forged in (type(handle)(), object.__new__(type(handle))):
            with pytest.raises(RepositoryContractError): projector(forged)


def test_all_handle_state_is_gc_cleaned_and_generation_safe():
    handles = _all_handles()
    roots = (module.copy_governance_inputs, copy_annual_position_record) + tuple(type(h).__dict__["__copy__"] for h in handles[2:])
    registry_names = (
        ("gs", "gl", "gr"), ("rs", "rl", "rr"), ("os", "ol", "ore"),
        ("qs", "ql", "qr"), ("ds", "dl", "dr"),
    )
    def cells(root):
        found, pending, seen = {}, [root], set()
        while pending:
            fn = pending.pop()
            if not isinstance(fn, types.FunctionType) or id(fn) in seen: continue
            seen.add(id(fn))
            for name, cell in zip(fn.__code__.co_freevars, fn.__closure__ or (), strict=True):
                value = cell.cell_contents; found.setdefault(name, value)
                if isinstance(value, types.FunctionType): pending.append(value)
        return found
    gc.collect()
    for original, root, names in zip(handles, roots, registry_names):
        found = cells(root); states, live, refs = (found[name] for name in names)
        baseline = (len(states), len(live), len(refs))
        generated = [copy.copy(original) for _ in range(100)]; ids = tuple(id(x) for x in generated)
        weak = tuple(weakref.ref(x) for x in generated); del generated; gc.collect()
        assert all(ref() is None for ref in weak)
        assert all(identity not in states and identity not in live and identity not in refs for identity in ids)
        assert (len(states), len(live), len(refs)) == baseline
        old, new = copy.copy(original), copy.copy(original); old_id, new_id = id(old), id(new)
        old_state, old_ref = states[old_id], refs[old_id]
        states[old_id], live[old_id], refs[old_id] = states[new_id], new, refs[new_id]
        old_ref.__callback__(old_ref)
        assert live[old_id] is new and refs[old_id] is refs[new_id]
        states[old_id], live[old_id], refs[old_id] = old_state, old, old_ref
        del old, new; gc.collect(); assert old_id not in states and new_id not in states


def test_local_acceptance_graph_has_no_runtime_global_lookup():
    seen, pending = set(), [make_structural_candidate, prepare_annual_position_record,
                           decode_annual_position_record, decide_initial_create,
                           prepare_supersession, read_owned_record, plan_account_deletion]
    while pending:
        value = pending.pop()
        if id(value) in seen: continue
        seen.add(id(value))
        if isinstance(value, types.FunctionType):
            if Path(value.__code__.co_filename).resolve() == SOURCE.resolve():
                assert not [i for i in dis.get_instructions(value) if i.opname in {"LOAD_GLOBAL", "STORE_GLOBAL", "DELETE_GLOBAL"}], value.__qualname__
            pending.extend(cell.cell_contents for cell in value.__closure__ or ())
        elif isinstance(value, type) and value.__module__ == module.__name__:
            pending.extend(value.__dict__.values())
        elif isinstance(value, (tuple, list)): pending.extend(value)
        elif isinstance(value, dict): pending.extend(value.values())


def test_no_database_io_migration_retention_or_provider_implementation():
    text = SOURCE.read_text().casefold()
    for forbidden in ("import os", "import sqlite", "from pathlib", "open(", "create table",
                      "insert into", "database_url", "retention_days =", "kms", "boto"):
        assert forbidden not in text
