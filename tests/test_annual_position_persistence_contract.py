"""Focused acceptance tests for the W9-S3A annual-position persistence contract.

The suite reproduces the seven independently-reported defects and demonstrates
that each now fails closed:

1. Public construction and ``dataclasses.replace`` cannot mint an
   issuance-validated projection (admission trust is explicit).
2. ``supersede_annual_position_projection`` rejects cross-boundary successors.
3. Rebounding module/builtin/helper/class names cannot bypass detection.
4. Hostile admission, structural reconstruction, representation,
   copy/replace/pickle, supersession, full finite-chain traversal, cross-boundary
   links, exclusions and no-I/O are all covered.
5. The carried W8 constraints are renamed as reconstructed customer-result
   constraints and never prohibit persistence of the projection.
6. Deletion/account-erasure state is explicit and honest.
7. Monetary values use one exact two-decimal representation (noncanonical
   exponents are rejected).
"""
from __future__ import annotations

import copy
import dataclasses
import dis
import pickle
import types
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

import reserved.annual_position_persistence_contract as contract_module
import reserved.services.w8_annual_cash_customer_handoff as handoff_module
from reserved.annual_position_persistence_contract import (
    RECORD_PURPOSE,
    SCHEMA_VERSION,
    AnnualPositionPersistenceProjection,
    admit_annual_position_projection,
    annual_position_projection_identity,
    reconstruct_w8_customer_result,
    supersede_annual_position_projection,
    validate_supersession_chain,
)
from reserved.services.w2_customer_language import (
    CONTRACT_VERSION as W2_CONTRACT_VERSION,
    PresentationStatus,
    W2PresentationInput,
)
from reserved.services.w8_customer_result import (
    SupportedNation,
    compose_w8_customer_result,
    w8_customer_result_identity,
)
from tests.test_annual_to_cash_integration import annual_position, compose
from tests.test_w8_annual_cash_customer_handoff import (
    handoff as make_handoff,
    project as make_legacy_result,
    references,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE_SOURCE = (ROOT / "reserved" / "annual_position_persistence_contract.py").read_text()

USER_ID = "user-1"
BUSINESS_ID = "business-1"
FORGED_ANNUAL_IDENTITY = "annual-to-cash-position:sha256-" + "0" * 64
FORGED_CONTENT_IDENTITY = "annual-position-persistence:sha256-" + "f" * 64


def _admitted(nation="England", user_id=USER_ID, business_id=BUSINESS_ID):
    annual_cash = compose() if nation == "England" else compose(annual=annual_position(nation))
    handoff = make_handoff(annual_cash)
    assert handoff is not None
    projection = admit_annual_position_projection(
        annual_cash,
        handoff,
        authenticated_user_id=user_id,
        authenticated_business_id=business_id,
    )
    return annual_cash, handoff, projection


def _supersede(previous, annual_cash, handoff, *, user_id=None, business_id=None):
    return supersede_annual_position_projection(
        previous,
        annual_cash,
        handoff,
        authenticated_user_id=previous.user_id if user_id is None else user_id,
        authenticated_business_id=(
            previous.business_id if business_id is None else business_id
        ),
    )


def _init_values(projection):
    return tuple(
        getattr(projection, f.name)
        for f in dataclasses.fields(projection)
        if f.init
    )


def _chain(length):
    annual_cash, result, first = _admitted()
    chain = [first]
    for _ in range(length - 1):
        chain.append(_supersede(chain[-1], annual_cash, result))
    return annual_cash, result, chain


# ── 0. Owner-unbound handoff admission and authenticated binding ─────────────

def test_admission_rejects_removed_owner_bound_w8_result_input():
    annual_cash = compose()
    owner_bound = make_legacy_result(
        annual_cash, user_id=USER_ID, business_id=BUSINESS_ID
    )
    with pytest.raises(ValueError, match="owner-unbound handoff"):
        admit_annual_position_projection(
            annual_cash,
            owner_bound,
            authenticated_user_id=USER_ID,
            authenticated_business_id=BUSINESS_ID,
        )


def test_duck_typed_annual_position_is_rejected_without_descriptor_access():
    accessed = []

    class HostileDuck:
        @property
        def as_of(self):
            accessed.append("as_of")
            raise AssertionError("hostile descriptor executed")

    annual_cash = compose()
    with pytest.raises(ValueError, match="exact annual/cash position"):
        admit_annual_position_projection(
            HostileDuck(),
            make_handoff(annual_cash),
            authenticated_user_id=USER_ID,
            authenticated_business_id=BUSINESS_ID,
        )
    assert accessed == []


def test_annual_position_subclass_is_rejected_without_descriptor_access():
    annual_cash = compose()
    accessed = []

    class HostileSubclass(type(annual_cash)):
        @property
        def as_of(self):
            accessed.append("as_of")
            raise AssertionError("hostile descriptor executed")

    hostile = object.__new__(HostileSubclass)
    with pytest.raises(ValueError, match="exact annual/cash position"):
        admit_annual_position_projection(
            hostile,
            make_handoff(annual_cash),
            authenticated_user_id=USER_ID,
            authenticated_business_id=BUSINESS_ID,
        )
    assert accessed == []


def test_admission_validates_handoff_before_binding_authenticated_owner():
    annual_cash = compose()
    valid = make_handoff(annual_cash)
    altered_presentation = replace(
        valid.presentation_input, annual_liability=Decimal("1.00")
    )
    reconstructed = handoff_module.UnboundAnnualCashPresentation(
        altered_presentation,
        references(annual_cash),
        annual_cash.as_of,
        annual_cash.tax_year,
        annual_cash.nation,
        annual_cash.ruleset_version,
        annual_cash.contract_version,
        valid.source_position_identity,
        annual_cash.annual_position_reference,
        _issue_token=handoff_module._ISSUE_TOKEN,
    )
    with pytest.raises(ValueError, match="not derived from the exact source"):
        admit_annual_position_projection(
            annual_cash,
            reconstructed,
            authenticated_user_id=USER_ID,
            authenticated_business_id=BUSINESS_ID,
        )


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("tax_year", "2027/28"),
        ("nation", "Wales"),
        ("evidence_references", ("forged-source",)),
        ("as_of", date(2028, 1, 1)),
        ("source_position_identity", "annual-to-cash-position:sha256-" + "0" * 64),
    ],
)
def test_altered_handoff_identity_context_fails_closed(field_name, replacement):
    annual_cash = compose()
    altered = make_handoff(annual_cash)
    object.__setattr__(altered, field_name, replacement)
    with pytest.raises(ValueError):
        admit_annual_position_projection(
            annual_cash,
            altered,
            authenticated_user_id=USER_ID,
            authenticated_business_id=BUSINESS_ID,
        )


def test_stale_or_mismatched_handoff_cannot_bind_to_another_source_snapshot():
    prior = compose(set_aside="0.00")
    current = compose(set_aside="99999.00")
    prior_handoff = make_handoff(prior)
    with pytest.raises(ValueError, match="source|expected source context"):
        admit_annual_position_projection(
            current,
            prior_handoff,
            authenticated_user_id=USER_ID,
            authenticated_business_id=BUSINESS_ID,
        )


def test_valid_handoff_binds_only_explicit_authenticated_owner_references():
    annual_cash = compose()
    unbound = make_handoff(annual_cash)
    assert unbound.owner_authoritative is False
    assert not hasattr(unbound, "user_id")
    projection = admit_annual_position_projection(
        annual_cash,
        unbound,
        authenticated_user_id="authenticated-user",
        authenticated_business_id="authenticated-business",
    )
    assert projection.user_id == "authenticated-user"
    assert projection.business_id == "authenticated-business"
    assert reconstruct_w8_customer_result(projection).user_id == "authenticated-user"


def test_supersession_rejects_cross_owner_binding_from_same_valid_handoff():
    annual_cash, unbound, projection = _admitted()
    with pytest.raises(ValueError, match="cross-user"):
        _supersede(
            projection,
            annual_cash,
            unbound,
            user_id="different-authenticated-user",
        )


# ── 1. Admission is explicit and public construction fails closed ─────────────

def test_admitted_projection_marks_identity_as_issuance_validated():
    annual_cash, result, projection = _admitted()
    assert projection.annual_cash_identity_admitted is True


def test_public_construction_is_structural_and_unadmitted():
    annual_cash, result, projection = _admitted()
    rebuilt = AnnualPositionPersistenceProjection(*_init_values(projection))
    assert rebuilt.annual_cash_identity_admitted is False
    assert rebuilt.annual_cash_identity == projection.annual_cash_identity
    assert annual_position_projection_identity(rebuilt) == annual_position_projection_identity(projection)


def test_replace_cannot_mint_an_admitted_projection():
    annual_cash, result, projection = _admitted()
    forged = replace(projection, annual_cash_identity=FORGED_ANNUAL_IDENTITY)
    assert forged.annual_cash_identity is not None
    assert forged.annual_cash_identity == FORGED_ANNUAL_IDENTITY
    assert forged.annual_cash_identity_admitted is False


def test_pickle_decode_is_structural_and_unadmitted():
    annual_cash, result, projection = _admitted()
    decoded = pickle.loads(pickle.dumps(projection))
    assert decoded.annual_cash_identity_admitted is False
    assert decoded.annual_cash_identity == projection.annual_cash_identity
    assert annual_position_projection_identity(decoded) == annual_position_projection_identity(projection)


# ── 2. Supersession rejects cross-boundary successors before returning ────────

def test_supersede_rejects_cross_user():
    annual_cash, result, projection = _admitted()
    with pytest.raises(ValueError, match="cross-user"):
        _supersede(projection, annual_cash, result, user_id="user-2")


def test_supersede_rejects_cross_business():
    annual_cash, result, projection = _admitted()
    with pytest.raises(ValueError, match="cross-business"):
        _supersede(projection, annual_cash, result, business_id="business-2")


def test_supersede_rejects_cross_nation():
    annual_cash, result, projection = _admitted(nation="England")
    wales_cash = compose(annual=annual_position("Wales"))
    wales_result = make_handoff(wales_cash)
    with pytest.raises(ValueError, match="geography"):
        _supersede(projection, wales_cash, wales_result)


def test_supersede_produces_a_boundary_matched_admitted_successor():
    annual_cash, result, projection = _admitted()
    successor = _supersede(projection, annual_cash, result)
    assert successor.annual_cash_identity_admitted is True
    assert successor.record_version == projection.record_version + 1
    assert successor.predecessor_identity == annual_position_projection_identity(projection)
    assert successor.user_id == projection.user_id
    assert successor.business_id == projection.business_id
    assert successor.tax_year == projection.tax_year
    assert successor.nation is projection.nation


# ── 3. Mutable global/builtin/helper/class rebinding cannot bypass detection ──

def test_rebinding_primitives_cannot_bypass_chain_detection(monkeypatch):
    annual_cash, result, projection = _admitted()
    successor = _supersede(projection, annual_cash, result)
    broken = replace(successor, predecessor_identity=FORGED_CONTENT_IDENTITY)

    monkeypatch.setattr(contract_module, "range", lambda *a, **k: (), raising=False)
    monkeypatch.setattr(contract_module, "len", lambda *a, **k: 0, raising=False)
    monkeypatch.setattr(contract_module, "set", lambda *a, **k: set(), raising=False)
    monkeypatch.setattr(contract_module, "enumerate", lambda *a, **k: (), raising=False)
    monkeypatch.setattr(contract_module, "any", lambda *a, **k: False, raising=False)
    monkeypatch.setattr(contract_module, "isinstance", lambda *a, **k: True, raising=False)
    monkeypatch.setattr(contract_module, "hash", lambda *a, **k: 0, raising=False)
    monkeypatch.setattr(contract_module, "tuple", lambda *a, **k: (), raising=False)
    monkeypatch.setattr(contract_module, "str", lambda *a, **k: "attacker", raising=False)

    with pytest.raises(ValueError, match="preceding record"):
        validate_supersession_chain([projection, broken])


def test_rebinding_error_types_cannot_bypass_fail_closed(monkeypatch):
    annual_cash, result, projection = _admitted()

    monkeypatch.setattr(contract_module, "ValueError", RuntimeError, raising=False)
    monkeypatch.setattr(contract_module, "Exception", BaseException, raising=False)

    # The contract captured its own error types; it still raises a real
    # ValueError, so callers cannot be fed a different exception class.
    assert annual_position_projection_identity(projection).startswith(
        "annual-position-persistence:sha256-"
    )
    with pytest.raises(ValueError):
        validate_supersession_chain([])


def test_rebinding_rebuild_helper_and_class_cannot_bypass_admission(monkeypatch):
    annual_cash, result, projection = _admitted()

    def hostile_rebuild(*values):
        raise RuntimeError("rebound helper")

    monkeypatch.setattr(contract_module, "_rebuild_projection", hostile_rebuild)
    monkeypatch.setattr(contract_module, "AnnualPositionPersistenceProjection", None)

    # The captured admission path still works even though the module-level names
    # were rebound after import.
    again = admit_annual_position_projection(
        annual_cash,
        result,
        authenticated_user_id=projection.user_id,
        authenticated_business_id=projection.business_id,
    )
    assert again.annual_cash_identity_admitted is True
    assert type(again).__name__ == "AnnualPositionPersistenceProjection"
    # Pickle fails closed instead of silently using the rebound helper.
    with pytest.raises(Exception):
        pickle.dumps(again)


@pytest.mark.parametrize(
    ("field_name", "forged"),
    [
        ("annual_cash_identity", FORGED_ANNUAL_IDENTITY),
        ("user_id", "forged-user"),
        ("record_version", 99),
    ],
)
def test_original_slot_descriptors_defeat_class_descriptor_masking(
    monkeypatch, field_name, forged
):
    _, _, projection = _admitted()
    original = getattr(projection, field_name)
    original_descriptor = AnnualPositionPersistenceProjection.__dict__[field_name]

    # Reproduce the hostile sequence exactly: mutate retained slot state first,
    # then mask the public class attribute with a property returning the old
    # value. Validation must consult the captured original descriptor.
    original_descriptor.__set__(projection, forged)
    monkeypatch.setattr(
        AnnualPositionPersistenceProjection,
        field_name,
        property(lambda self, value=original: value),
    )
    assert getattr(projection, field_name) == original
    with pytest.raises(ValueError):
        annual_position_projection_identity(projection)


def test_rebinding_exported_policy_constants_cannot_change_acceptance(monkeypatch):
    annual_cash, result, projection = _admitted()
    monkeypatch.setattr(contract_module, "SCHEMA_VERSION", "attacker-schema/9")
    monkeypatch.setattr(contract_module, "RECORD_PURPOSE", "attacker-purpose")
    monkeypatch.setattr(contract_module, "_UNRESOLVED_INPUTS", ("activation_resolved",))
    monkeypatch.setattr(contract_module, "_DELETION_STATE", "deleted")
    monkeypatch.setattr(contract_module, "_ACCOUNT_ERASURE_ELIGIBILITY", "eligible")

    again = admit_annual_position_projection(
        annual_cash,
        result,
        authenticated_user_id=projection.user_id,
        authenticated_business_id=projection.business_id,
    )
    assert again.schema_version == SCHEMA_VERSION
    assert again.record_purpose == RECORD_PURPOSE
    assert again.unresolved_inputs == projection.unresolved_inputs
    with pytest.raises(ValueError, match="schema"):
        replace(projection, schema_version="attacker-schema/9")
    with pytest.raises(ValueError, match="unresolved"):
        replace(projection, unresolved_inputs=("activation_resolved",))


def test_local_acceptance_graph_has_no_mutable_global_resolution():
    """Audit local closure dependencies recursively; external reviewed contracts
    remain explicit admission boundaries rather than silently being called local
    sealing logic.
    """

    roots = (
        admit_annual_position_projection,
        annual_position_projection_identity,
        supersede_annual_position_projection,
        validate_supersession_chain,
        reconstruct_w8_customer_result,
    )
    seen = set()
    stack = list(roots)
    while stack:
        fn = stack.pop()
        if not isinstance(fn, types.FunctionType) or id(fn) in seen:
            continue
        seen.add(id(fn))
        if fn.__module__ == contract_module.__name__:
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
            if isinstance(value, types.FunctionType):
                stack.append(value)

    # All locally captured helpers reached from the public authorities were
    # inspected; this prevents a shallow one-function audit.
    assert len(seen) >= 20


# ── 4. Structural reconstruction, representation and copy/replace/pickle ──────

def test_reconstruct_w8_customer_result_from_admitted_and_reconstructed_projection():
    annual_cash, result, projection = _admitted()
    rebuilt = AnnualPositionPersistenceProjection(*_init_values(projection))
    for source in (projection, rebuilt):
        reproduced = reconstruct_w8_customer_result(source)
        assert reproduced is not None
        assert w8_customer_result_identity(reproduced) == source.customer_result_identity


def test_representation_is_constant_and_state_dependent():
    annual_cash, result, projection = _admitted()
    assert repr(projection) == "AnnualPositionPersistenceProjection(<validated>)"
    tampered = AnnualPositionPersistenceProjection(*_init_values(projection))
    object.__setattr__(tampered, "user_id", "forged")
    assert repr(tampered) == "AnnualPositionPersistenceProjection(<invalid-state>)"


def test_copy_and_deepcopy_preserve_identity_and_admission():
    annual_cash, result, projection = _admitted()
    assert copy.copy(projection) is projection
    assert copy.deepcopy(projection) is projection


def test_identity_is_deterministic_and_content_sensitive():
    annual_cash, result, projection = _admitted()
    assert annual_position_projection_identity(projection) == annual_position_projection_identity(projection)
    rebuilt = AnnualPositionPersistenceProjection(*_init_values(projection))
    assert annual_position_projection_identity(rebuilt) == annual_position_projection_identity(projection)


def test_hostile_field_mutation_is_rejected_by_all_protocols():
    annual_cash, result, projection = _admitted()
    tampered = AnnualPositionPersistenceProjection(*_init_values(projection))
    object.__setattr__(tampered, "annual_cash_identity", FORGED_ANNUAL_IDENTITY)
    with pytest.raises(ValueError, match="integrity"):
        annual_position_projection_identity(tampered)
    with pytest.raises(ValueError, match="integrity"):
        hash(tampered)
    with pytest.raises(ValueError, match="integrity"):
        pickle.dumps(tampered)
    with pytest.raises(ValueError, match="integrity"):
        copy.copy(tampered)


# ── 5. Renamed reconstructed customer-result constraints ──────────────────────

def test_carried_constraints_are_customer_result_constraints():
    annual_cash, result, projection = _admitted()
    reconstructed = reconstruct_w8_customer_result(projection)
    assert not hasattr(projection, "limitations")
    assert not hasattr(projection, "prohibited_uses")
    assert projection.customer_result_limitations == reconstructed.limitations
    assert projection.customer_result_prohibited_uses == reconstructed.prohibited_uses
    assert "persistence_or_storage" in projection.customer_result_prohibited_uses
    # The projection itself is an authorised durable projection, not prohibited.
    assert projection.record_purpose == RECORD_PURPOSE
    assert projection.schema_version == SCHEMA_VERSION


# ── 6. Explicit deletion/account-erasure state ────────────────────────────────

def test_deletion_and_erasure_state_are_explicit_and_honest():
    annual_cash, result, projection = _admitted()
    assert projection.deletion_state == "not_deleted"
    assert projection.account_erasure_eligibility == "unresolved"
    # Retention period and legal hold are recorded as unresolved, never invented.
    assert "retention_period_unresolved" in projection.unresolved_inputs
    assert "legal_hold_unresolved" in projection.unresolved_inputs
    assert projection.deletion_state != "deleted"


# ── 7. Canonical monetary representation ──────────────────────────────────────

def test_noncanonical_money_exponent_is_rejected():
    annual_cash, result, projection = _admitted()
    with pytest.raises(ValueError, match="annual liability"):
        replace(projection, annual_liability=Decimal("1.0"))
    with pytest.raises(ValueError):
        replace(projection, annual_liability=Decimal("1"))


def test_admission_canonicalises_producer_money():
    # The live producer emits a noncanonical `Decimal('0')` for the
    # payments-made adjustment; admission canonicalises it so every monetary
    # fact in the projection carries exactly two decimal places.
    annual_cash = compose()
    result = make_handoff(annual_cash)
    projection = admit_annual_position_projection(
        annual_cash,
        result,
        authenticated_user_id=USER_ID,
        authenticated_business_id=BUSINESS_ID,
    )
    for item in projection.adjustments:
        assert item.amount.as_tuple().exponent == -2
    for item in projection.obligations:
        assert item.amount.as_tuple().exponent == -2
    assert projection.annual_liability.as_tuple().exponent == -2
    if projection.funding_amount is not None:
        assert projection.funding_amount.as_tuple().exponent == -2


# ── 8. Full finite-chain traversal and cycle lengths ──────────────────────────

def test_single_record_chain_is_terminal():
    annual_cash, result, chain = _chain(1)
    assert validate_supersession_chain(chain) is chain[0]


@pytest.mark.parametrize("length", [2, 3, 4, 5])
def test_full_finite_chain_traversal(length):
    annual_cash, result, chain = _chain(length)
    terminal = validate_supersession_chain(chain)
    assert terminal is chain[-1]
    assert terminal.record_version == length


def test_chain_rejects_self_reference():
    annual_cash, result, projection = _admitted()
    # A record whose predecessor link equals its own content identity (the
    # predecessor is excluded from content identity, so this is constructible).
    template = replace(projection, record_version=2, predecessor_identity=None)
    self_linked = replace(
        template,
        predecessor_identity=annual_position_projection_identity(template),
    )
    assert self_linked.predecessor_identity == annual_position_projection_identity(self_linked)
    with pytest.raises(ValueError, match="self-reference"):
        validate_supersession_chain([projection, self_linked])


def test_chain_rejects_repeated_identity():
    annual_cash, result, projection = _admitted()
    with pytest.raises(ValueError, match="repeats"):
        validate_supersession_chain([projection, projection])


def test_chain_rejects_broken_successor_link():
    annual_cash, result, projection = _admitted()
    successor = _supersede(projection, annual_cash, result)
    broken = replace(successor, predecessor_identity=FORGED_CONTENT_IDENTITY)
    with pytest.raises(ValueError, match="preceding record"):
        validate_supersession_chain([projection, broken])


def test_chain_rejects_version_skip():
    annual_cash, result, projection = _admitted()
    successor = _supersede(projection, annual_cash, result)
    skipped = replace(successor, record_version=3)
    with pytest.raises(ValueError, match="strictly progress"):
        validate_supersession_chain([projection, skipped])


# ── 9. Cross-boundary links in the chain validator ────────────────────────────

def _link(successor_base, previous, version):
    return replace(
        successor_base,
        record_version=version,
        predecessor_identity=annual_position_projection_identity(previous),
    )


def test_chain_rejects_cross_user_link():
    annual_cash, result, prev = _admitted(user_id="user-1")
    _, _, other = _admitted(user_id="user-2")
    linked = _link(other, prev, prev.record_version + 1)
    with pytest.raises(ValueError, match="cross-user"):
        validate_supersession_chain([prev, linked])


def test_chain_rejects_cross_business_link():
    annual_cash, result, prev = _admitted(business_id="business-1")
    _, _, other = _admitted(business_id="business-2")
    linked = _link(other, prev, prev.record_version + 1)
    with pytest.raises(ValueError, match="cross-business"):
        validate_supersession_chain([prev, linked])


def test_chain_rejects_cross_nation_link():
    annual_cash, result, prev = _admitted(nation="England")
    _, _, other = _admitted(nation="Wales")
    linked = _link(other, prev, prev.record_version + 1)
    with pytest.raises(ValueError, match="geography"):
        validate_supersession_chain([prev, linked])


def test_chain_rejects_cross_tax_year_link():
    annual_cash, result, prev = _admitted()
    w2 = W2PresentationInput(
        W2_CONTRACT_VERSION,
        PresentationStatus.READY,
        prev.evidence_classification,
        prev.annual_liability,
        prev.obligations,
        prev.adjustments,
        prev.funding,
        prev.funding_amount,
        None,
    )
    reproduced = compose_w8_customer_result(
        w2,
        nation=prev.nation.value,
        tax_year="2027/28",
        user_id=prev.user_id,
        business_id=prev.business_id,
        evidence_references=prev.evidence_references,
    )
    other = replace(
        prev,
        tax_year="2027/28",
        customer_result_identity=w8_customer_result_identity(reproduced),
    )
    linked = _link(other, prev, prev.record_version + 1)
    with pytest.raises(ValueError, match="tax year"):
        validate_supersession_chain([prev, linked])


# ── 10. Bounded imports and no I/O ────────────────────────────────────────────

def test_module_imports_are_bounded():
    allowed = (
        "from __future__",
        "import hashlib",
        "import hmac",
        "import json",
        "import re",
        "from dataclasses import",
        "from datetime import",
        "from decimal import",
        "from enum import",
        "from reserved.engines.annual_to_cash_integration import",
        "from reserved.services.w2_customer_language import",
        "from reserved.services.w8_annual_cash_customer_handoff import",
        "from reserved.services.w8_customer_result import",
    )
    for line in MODULE_SOURCE.splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            assert any(stripped.startswith(prefix) for prefix in allowed), stripped


def test_module_performs_no_database_network_or_credential_io():
    forbidden = (
        "import os",
        "import sys",
        "import socket",
        "import subprocess",
        "import requests",
        "import flask",
        "import sqlite3",
        "import pathlib",
        "import shutil",
        "import tempfile",
        "import urllib",
        "import openai",
        "import psycopg",
        "import pymongo",
        "open(",
        "print(",
        "requests.",
        "sqlite3.",
        "socket.",
        "subprocess.",
        "os.environ",
        "environ[",
        "getenv(",
        "urlopen",
        ".execute(",
    )
    for token in forbidden:
        assert token not in MODULE_SOURCE, token
