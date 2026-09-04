"""Focused hostile tests for the pure W9-S3E membership contract."""

from __future__ import annotations

import ast
import dataclasses
import inspect
from pathlib import Path

import pytest
from flask import Flask, globals as flask_globals

import reserved.auth as auth
import reserved.owner_business_membership_contract as subject


ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "reserved" / "owner_business_membership_contract.py"
DOCUMENT = ROOT / "docs" / "W9_S3E_OWNER_BUSINESS_MEMBERSHIP_CONTRACT.md"
OWNED_PATHS = {
    "reserved/owner_business_membership_contract.py",
    "tests/test_owner_business_membership_contract.py",
    "docs/W9_S3E_OWNER_BUSINESS_MEMBERSHIP_CONTRACT.md",
}


@pytest.fixture
def app():
    application = Flask(__name__)
    application.config.update(SECRET_KEY="synthetic-w9-s3e-only", TESTING=True)
    return application


def record(
    membership_reference="membership-41-a",
    owner_users_id=41,
    business_reference="business-41-a",
    membership_version=1,
    status=subject.MembershipStatus.ACTIVE,
):
    return subject.OwnerBusinessMembershipRecord(
        membership_reference=membership_reference,
        owner_users_id=owner_users_id,
        business_reference=business_reference,
        membership_version=membership_version,
        status=status,
    )


def fake(*records, snapshot_version=1):
    return subject.InMemoryOwnerBusinessMembershipFake(
        tuple(records), snapshot_version=snapshot_version
    )


def evaluate(source, business="business-41-a"):
    return subject.evaluate_authenticated_owner_business_membership(
        membership_fake=source,
        requested_business_reference=business,
    )


def signed_session(app, owner=41):
    context = app.test_request_context("/")
    context.push()
    auth.set_user_session(owner, f"user_{owner}")
    return context


def assert_denied(decision, reason):
    assert subject.validate_owner_business_membership_decision(decision) is decision
    assert decision.allowed is False
    assert decision.reason is reason
    assert decision.membership_reference is None
    assert decision.membership_version is None
    assert decision.current_snapshot_authority is False
    assert decision.runtime_access_authority is False
    assert decision.persistence_authority is False
    assert decision.production_authority is False
    assert decision.sharing_authority is False


def test_exact_named_boundary_has_no_client_owner_membership_or_provider_argument():
    signature = inspect.signature(subject.evaluate_authenticated_owner_business_membership)
    assert tuple(signature.parameters) == (
        "membership_fake",
        "requested_business_reference",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    with pytest.raises(TypeError):
        subject.evaluate_authenticated_owner_business_membership(
            membership_fake=fake(record()),
            requested_business_reference="business-41-a",
            owner_users_id=41,
        )
    with pytest.raises(TypeError):
        subject.evaluate_authenticated_owner_business_membership(
            membership_fake=fake(record()),
            requested_business_reference="business-41-a",
            provider_organisation_id="provider-org-41",
        )


def test_current_signed_session_users_id_matches_one_active_owner_record(app):
    source = fake(record())
    context = signed_session(app)
    try:
        first = evaluate(source)
        second = evaluate(source)
    finally:
        context.pop()
    assert first == second
    assert hash(first) == hash(second)
    assert first.allowed is True
    assert first.reason is subject.MembershipDecisionReason.ACTIVE_OWNER_MEMBERSHIP
    assert first.authenticated_owner_users_id == 41
    assert first.business_reference == "business-41-a"
    assert first.membership_reference == "membership-41-a"
    assert first.membership_version == 1
    assert first.snapshot_version == 1
    assert first.snapshot_identity == source.snapshot_identity
    assert first.authenticated_owner_source == "reserved_signed_session_users.id"
    assert first.owner_role == "owner_only_no_sharing_or_delegation"
    assert first.business_reference_role == "request_selector_not_access_authority"
    assert first.freshness_role == (
        "detached_structural_decision_requires_current_snapshot_check"
    )
    assert first.current_snapshot_authority is False
    assert first.runtime_access_authority is False
    assert first.persistence_authority is False
    assert first.production_authority is False
    assert first.sharing_authority is False
    assert subject.validate_owner_business_membership_decision(first) is first
    assert (
        subject.assert_allowed_membership_decision_current(
            decision=first, membership_fake=source
        )
        is None
    )


def test_no_request_or_authenticated_owner_denies_without_querying_by_business(app):
    source = fake(record())
    assert_denied(
        evaluate(source),
        subject.MembershipDecisionReason.AUTHENTICATED_OWNER_UNAVAILABLE,
    )
    with app.test_request_context("/"):
        assert_denied(
            evaluate(source),
            subject.MembershipDecisionReason.AUTHENTICATED_OWNER_UNAVAILABLE,
        )


@pytest.mark.parametrize("owner", [None, True, False, 0, -1, "41", 41.0])
def test_owner_must_be_exact_positive_authenticated_users_id(app, owner):
    context = app.test_request_context("/")
    context.push()
    try:
        auth.session[auth._SK_USER_ID] = owner
        assert_denied(
            evaluate(fake(record())),
            subject.MembershipDecisionReason.AUTHENTICATED_OWNER_UNAVAILABLE,
        )
    finally:
        context.pop()


def test_client_business_string_alone_never_grants_membership(app):
    context = signed_session(app)
    try:
        decision = evaluate(fake())
    finally:
        context.pop()
    assert_denied(decision, subject.MembershipDecisionReason.MEMBERSHIP_MISSING)
    assert decision.business_reference == "business-41-a"


def test_cross_owner_business_is_indistinguishable_from_missing(app):
    source = fake(record(owner_users_id=42, business_reference="business-42-a"))
    context = signed_session(app, 41)
    try:
        decision = evaluate(source, "business-42-a")
    finally:
        context.pop()
    assert_denied(decision, subject.MembershipDecisionReason.MEMBERSHIP_MISSING)
    assert decision.membership_reference is None


def test_revoked_membership_explicitly_denies(app):
    source = fake(record(status=subject.MembershipStatus.REVOKED))
    context = signed_session(app)
    try:
        decision = evaluate(source)
    finally:
        context.pop()
    assert_denied(decision, subject.MembershipDecisionReason.MEMBERSHIP_REVOKED)


def test_duplicate_owner_business_memberships_are_ambiguous_and_deny(app):
    source = fake(
        record(),
        record(membership_reference="membership-41-a-duplicate", membership_version=2),
    )
    context = signed_session(app)
    try:
        decision = evaluate(source)
    finally:
        context.pop()
    assert_denied(decision, subject.MembershipDecisionReason.MEMBERSHIP_AMBIGUOUS)


def test_active_plus_revoked_history_is_ambiguous_not_silently_active(app):
    source = fake(
        record(),
        record(
            membership_reference="membership-41-a-old",
            membership_version=2,
            status=subject.MembershipStatus.REVOKED,
        ),
    )
    context = signed_session(app)
    try:
        decision = evaluate(source)
    finally:
        context.pop()
    assert_denied(decision, subject.MembershipDecisionReason.MEMBERSHIP_AMBIGUOUS)


def test_owner_only_fake_rejects_shared_business_and_duplicate_membership_ids():
    with pytest.raises(subject.MembershipContractError, match="shared across users"):
        fake(
            record(),
            record(
                membership_reference="membership-42-a",
                owner_users_id=42,
                business_reference="business-41-a",
            ),
        )
    with pytest.raises(subject.MembershipContractError, match="must be unique"):
        fake(record(), record())


class Text(str):
    pass


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"membership_reference": ""}, "membership reference"),
        ({"membership_reference": Text("membership-41-a")}, "membership reference"),
        ({"owner_users_id": True}, "exact positive users.id"),
        ({"owner_users_id": 0}, "exact positive users.id"),
        ({"business_reference": "token:business"}, "secret material"),
        ({"business_reference": Text("business-41-a")}, "business reference"),
        ({"membership_version": True}, "positive integer"),
        ({"membership_version": 0}, "positive integer"),
        ({"status": "active"}, "exact status"),
    ],
)
def test_record_inputs_are_exact_and_bounded(changes, message):
    values = {
        "membership_reference": "membership-41-a",
        "owner_users_id": 41,
        "business_reference": "business-41-a",
        "membership_version": 1,
        "status": subject.MembershipStatus.ACTIVE,
    }
    values.update(changes)
    with pytest.raises(subject.MembershipContractError, match=message):
        subject.OwnerBusinessMembershipRecord(**values)


def test_requested_business_reference_requires_exact_bounded_string(app):
    context = signed_session(app)
    try:
        for value in (
            None,
            True,
            41,
            "",
            "has spaces",
            "credential-business-41-a",
            Text("business-41-a"),
        ):
            decision = evaluate(fake(record()), value)
            assert_denied(
                decision,
                subject.MembershipDecisionReason.BUSINESS_REFERENCE_INVALID,
            )
            assert decision.business_reference is None
    finally:
        context.pop()


def test_constructor_seals_record_and_whole_snapshot_against_low_level_mutation(app):
    first_record = record()
    second_record = record(
        membership_reference="membership-42-a",
        owner_users_id=42,
        business_reference="business-42-a",
    )
    source = fake(first_record, second_record)
    with pytest.raises(dataclasses.FrozenInstanceError):
        source.records = ()
    with pytest.raises(dataclasses.FrozenInstanceError):
        source.records[0].status = subject.MembershipStatus.REVOKED

    context = signed_session(app)
    try:
        before = evaluate(source)
        assert before.allowed is True

        object.__setattr__(first_record, "owner_users_id", 42)
        object.__setattr__(first_record, "business_reference", "business-42-a")
        object.__setattr__(first_record, "status", subject.MembershipStatus.REVOKED)
        object.__setattr__(second_record, "business_reference", "business-41-a")
        object.__setattr__(source, "records", ())
        object.__setattr__(source, "snapshot_version", 999)
        object.__setattr__(source, "snapshot_identity", "forged")

        assert evaluate(source) == before
    finally:
        context.pop()

    with pytest.raises(subject.MembershipContractError, match="changed after construction"):
        fake(first_record)


def test_live_record_seal_is_first_write_after_mutation(app):
    membership = record()
    source = fake(membership)
    context = signed_session(app)
    try:
        original = evaluate(source)
        object.__setattr__(membership, "owner_users_id", 42)
        object.__setattr__(membership, "business_reference", "business-42-a")

        with pytest.raises(
            subject.MembershipContractError, match="already has a live constructor seal"
        ):
            membership.__post_init__()

        assert evaluate(source) == original
        with pytest.raises(
            subject.MembershipContractError, match="changed after construction"
        ):
            fake(membership)
        assert (
            subject.assert_allowed_membership_decision_current(
                decision=original, membership_fake=source
            )
            is None
        )
    finally:
        context.pop()


def test_live_snapshot_seal_is_first_write_after_records_replacement(app):
    source = fake(record())
    replacement = record(
        membership_reference="membership-42-a",
        owner_users_id=42,
        business_reference="business-42-a",
    )
    context = signed_session(app)
    try:
        original = evaluate(source)
        original_identity = original.snapshot_identity
        object.__setattr__(source, "records", (replacement,))
        object.__setattr__(source, "snapshot_identity", None)

        with pytest.raises(
            subject.MembershipContractError, match="already has a live constructor seal"
        ):
            source.__post_init__()

        current = evaluate(source)
        assert current == original
        assert current.snapshot_identity == original_identity
    finally:
        context.pop()


def test_snapshot_identity_mutation_cannot_be_resealed_or_change_authority(app):
    source = fake(record())
    context = signed_session(app)
    try:
        original = evaluate(source)
        object.__setattr__(source, "snapshot_version", 999)
        object.__setattr__(source, "snapshot_identity", None)

        with pytest.raises(
            subject.MembershipContractError, match="already has a live constructor seal"
        ):
            source.__post_init__()

        assert source.snapshot_identity is None
        assert evaluate(source) == original
        assert (
            subject.assert_allowed_membership_decision_current(
                decision=original, membership_fake=source
            )
            is None
        )
    finally:
        context.pop()


def test_unchanged_live_record_and_snapshot_cannot_be_registered_twice():
    membership = record()
    source = fake(membership)

    for value in (membership, source):
        with pytest.raises(
            subject.MembershipContractError, match="already has a live constructor seal"
        ):
            value.__post_init__()


def test_seal_registries_do_not_keep_collected_objects_alive():
    import gc
    import weakref

    membership = record()
    source = fake(membership)
    membership_reference = weakref.ref(membership)
    source_reference = weakref.ref(source)

    del source
    del membership
    gc.collect()

    assert source_reference() is None
    assert membership_reference() is None
    assert fake(record()).snapshot_identity.startswith(
        "owner-business-membership-snapshot:sha256-"
    )


def test_snapshot_identity_seals_whole_content_version_and_uniqueness():
    first = fake(record(), snapshot_version=7)
    equivalent = fake(record(), snapshot_version=7)
    revoked = fake(
        record(status=subject.MembershipStatus.REVOKED), snapshot_version=7
    )
    next_version = fake(record(), snapshot_version=8)

    assert first.snapshot_identity == equivalent.snapshot_identity
    assert first.snapshot_identity != revoked.snapshot_identity
    assert first.snapshot_identity != next_version.snapshot_identity
    assert type(first.snapshot_identity) is str


def test_decision_tamper_and_forgery_fail_validation(app):
    context = signed_session(app)
    try:
        decision = evaluate(fake(record()))
    finally:
        context.pop()

    with pytest.raises(subject.MembershipContractError, match="authority boundary"):
        dataclasses.replace(decision, production_authority=True)
    with pytest.raises(subject.MembershipContractError, match="identity"):
        dataclasses.replace(decision, business_reference="business-elsewhere")
    with pytest.raises(subject.MembershipContractError, match="outcome shape"):
        dataclasses.replace(
            decision,
            allowed=False,
            reason=subject.MembershipDecisionReason.MEMBERSHIP_MISSING,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("contract_version", Text(subject.CONTRACT_VERSION), "authority metadata"),
        (
            "authenticated_owner_source",
            Text(subject.AUTHENTICATED_OWNER_SOURCE),
            "authority metadata",
        ),
        ("owner_role", Text(subject.OWNER_ROLE), "authority metadata"),
        (
            "business_reference_role",
            Text(subject.BUSINESS_REFERENCE_ROLE),
            "authority metadata",
        ),
        ("freshness_role", Text(subject.FRESHNESS_ROLE), "authority metadata"),
        ("snapshot_identity", Text("x"), "snapshot identity"),
        ("decision_identity", Text("x"), "decision identity"),
    ],
)
def test_decision_authority_metadata_requires_exact_strings(app, field, value, message):
    source = fake(record())
    context = signed_session(app)
    try:
        decision = evaluate(source)
    finally:
        context.pop()
    object.__setattr__(decision, field, value)
    with pytest.raises(subject.MembershipContractError, match=message):
        subject.validate_owner_business_membership_decision(decision)


def test_captured_auth_namespace_rejects_session_and_key_rebinding(app, monkeypatch):
    source = fake(record())
    context = signed_session(app)
    try:
        monkeypatch.setattr(auth, "session", {auth._SK_USER_ID: 41})
        with pytest.raises(subject.MembershipContractError, match="boundary was altered"):
            evaluate(source)
        monkeypatch.undo()

        monkeypatch.setattr(auth, "_SK_USER_ID", Text("_v2_user_id"))
        with pytest.raises(subject.MembershipContractError, match="boundary was altered"):
            evaluate(source)
    finally:
        context.pop()


def test_out_of_request_synthetic_session_cannot_supply_owner(monkeypatch):
    monkeypatch.setattr(auth, "session", {auth._SK_USER_ID: 41})
    with pytest.raises(subject.MembershipContractError, match="boundary was altered"):
        evaluate(fake(record()))


def test_captured_session_owner_is_read_exactly_once(app, monkeypatch):
    class ChangingSession:
        def __init__(self):
            self.reads = 0

        def get(self, key):
            assert key == auth._SK_USER_ID
            self.reads += 1
            return 41 if self.reads == 1 else 42

    session_source = ChangingSession()
    context = app.test_request_context("/")
    context.push()
    try:
        monkeypatch.setattr(flask_globals._cv_request.get(), "session", session_source)
        decision = evaluate(fake(record()))
    finally:
        context.pop()
    assert session_source.reads == 1
    assert decision.allowed is True


def test_allowed_decision_must_be_rechecked_against_current_snapshot(app):
    original = fake(record(), snapshot_version=4)
    context = signed_session(app)
    try:
        decision = evaluate(original)
    finally:
        context.pop()

    assert subject.validate_owner_business_membership_decision(decision) is decision
    assert decision.current_snapshot_authority is False
    assert (
        subject.assert_allowed_membership_decision_current(
            decision=decision, membership_fake=original
        )
        is None
    )

    revoked = fake(
        record(status=subject.MembershipStatus.REVOKED), snapshot_version=5
    )
    replacement = fake(record(membership_version=2), snapshot_version=5)
    for current in (revoked, replacement):
        with pytest.raises(subject.MembershipContractError, match="stale"):
            subject.assert_allowed_membership_decision_current(
                decision=decision, membership_fake=current
            )


@pytest.mark.parametrize(
    "marker",
    [
        "secret-business-41",
        "token:business-41",
        "password-business-41",
        "credential-business-41",
        "apikey-business-41",
        "api_key-business-41",
        "bearer-business-41",
        "private_key-business-41",
        "sk_live_business-41",
        "sk_test_business-41",
        "access_key-business-41",
    ],
)
def test_secret_shaped_membership_and_business_references_are_rejected(marker):
    with pytest.raises(subject.MembershipContractError, match="secret material"):
        record(membership_reference=marker)
    with pytest.raises(subject.MembershipContractError, match="secret material"):
        record(business_reference=marker)


def test_module_is_bounded_to_standard_library_and_auth_with_no_io_calls():
    tree = ast.parse(MODULE.read_text())
    imported = set()
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
    assert imported <= {
        "__future__",
        "hashlib",
        "json",
        "re",
        "weakref",
        "dataclasses",
        "enum",
        "reserved.auth",
    }
    assert not calls.intersection(
        {
            "open",
            "connect",
            "execute",
            "request",
            "urlopen",
            "getenv",
            "system",
            "run",
            "Popen",
        }
    )


def test_evidence_document_and_exact_three_path_boundary_exist():
    text = DOCUMENT.read_text()
    for marker in (
        "users.id",
        "owner-only",
        "client-supplied",
        "provider organisation",
        "membership_missing",
        "membership_revoked",
        "membership_ambiguous",
        "no runtime, persistence or production authority",
        "No database, filesystem, network, environment or credential I/O",
        "Residual gates",
    ):
        assert marker in text
    assert OWNED_PATHS == {
        str(MODULE.relative_to(ROOT)),
        str(Path(__file__).resolve().relative_to(ROOT)),
        str(DOCUMENT.relative_to(ROOT)),
    }
