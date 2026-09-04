"""Pure W9-S3E authenticated owner-to-business membership contract.

The contract captures Reserved's signed-session owner boundary at import and
evaluates it against constructor-sealed, in-memory membership snapshots. A
requested business reference is only a selector. Provider organisation
identifiers are absent, and no result grants runtime, persistence, production,
sharing, or delegation authority.

This module performs no database, filesystem, network, credential,
environment, persistence, or activation I/O. A future physical repository and
runtime adapter must re-establish both current session ownership and membership
freshness before using a business reference for access.
"""

from __future__ import annotations

import hashlib as _hashlib
import json as _json
import re as _re
import weakref as _weakref
from dataclasses import dataclass as _dataclass
from dataclasses import field as _field
from enum import Enum as _Enum

import reserved.auth as _auth


CONTRACT_VERSION = "reserved-owner-business-membership/1.0"
AUTHENTICATED_OWNER_SOURCE = "reserved_signed_session_users.id"
OWNER_ROLE = "owner_only_no_sharing_or_delegation"
BUSINESS_REFERENCE_ROLE = "request_selector_not_access_authority"
FRESHNESS_ROLE = "detached_structural_decision_requires_current_snapshot_check"


class MembershipContractError(ValueError):
    """The local membership contract, snapshot, or decision is malformed."""


class MembershipStatus(_Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


class MembershipDecisionReason(_Enum):
    ACTIVE_OWNER_MEMBERSHIP = "active_owner_membership"
    AUTHENTICATED_OWNER_UNAVAILABLE = "authenticated_owner_unavailable"
    BUSINESS_REFERENCE_INVALID = "business_reference_invalid"
    MEMBERSHIP_MISSING = "membership_missing"
    MEMBERSHIP_REVOKED = "membership_revoked"
    MEMBERSHIP_AMBIGUOUS = "membership_ambiguous"


def _build_contract():
    """Capture the complete validation, session, and sealed-snapshot boundary."""

    typ, object_setattr = type, object.__setattr__
    T, S, I, B, Set, Dict = tuple, str, int, bool, set, dict
    length, any_fn, id_fn, range_fn, zip_fn = len, any, id, range, zip
    error, exception_type, attribute_error = (
        MembershipContractError,
        Exception,
        AttributeError,
    )
    sha256, dumps = _hashlib.sha256, _json.dumps
    compile_re = _re.compile
    weakref_ref = _weakref.ref

    contract_version = CONTRACT_VERSION
    authenticated_owner_source = AUTHENTICATED_OWNER_SOURCE
    owner_role = OWNER_ROLE
    business_reference_role = BUSINESS_REFERENCE_ROLE
    freshness_role = FRESHNESS_ROLE
    for label, value in (
        ("contract version", contract_version),
        ("authenticated owner source", authenticated_owner_source),
        ("owner role", owner_role),
        ("business reference role", business_reference_role),
        ("freshness role", freshness_role),
    ):
        if typ(value) is not S:
            raise RuntimeError(f"W9-S3E {label} must be an exact string")

    status_type = MembershipStatus
    reason_type = MembershipDecisionReason
    active_status = MembershipStatus.ACTIVE
    revoked_status = MembershipStatus.REVOKED
    active_reason = MembershipDecisionReason.ACTIVE_OWNER_MEMBERSHIP

    reference_pattern = compile_re(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
    snapshot_identity_pattern = compile_re(
        r"owner-business-membership-snapshot:sha256-[0-9a-f]{64}\Z"
    )
    decision_identity_pattern = compile_re(
        r"owner-business-membership:sha256-[0-9a-f]{64}\Z"
    )
    secret_markers = (
        "secret",
        "token",
        "password",
        "credential",
        "apikey",
        "api_key",
        "bearer",
        "private_key",
        "sk_live",
        "sk_test",
        "access_key",
    )

    # Mirror W9-S3D: capture the Flask proxy and key once, then reject any
    # rebinding of Reserved's authentication namespace before reading a request.
    session_proxy = _auth.session
    session_user_id_key = _auth._SK_USER_ID
    auth_namespace = _auth.__dict__
    if typ(session_user_id_key) is not S or session_user_id_key != "_v2_user_id":
        raise RuntimeError("Reserved authentication owner key is inconsistent")

    record_registry = {}
    fake_registry = {}
    record_slot_descriptors = ()
    fake_slot_descriptors = ()
    decision_slot_descriptors = ()

    record_field_names = (
        "membership_reference",
        "owner_users_id",
        "business_reference",
        "membership_version",
        "status",
    )
    fake_field_names = ("records", "snapshot_version", "snapshot_identity")
    decision_field_names = (
        "contract_version",
        "decision_identity",
        "allowed",
        "reason",
        "authenticated_owner_users_id",
        "business_reference",
        "membership_reference",
        "membership_version",
        "snapshot_version",
        "snapshot_identity",
        "authenticated_owner_source",
        "owner_role",
        "business_reference_role",
        "freshness_role",
        "current_snapshot_authority",
        "sharing_authority",
        "runtime_access_authority",
        "persistence_authority",
        "production_authority",
    )

    def raw_slots(value, owner, descriptors, names, label):
        if typ(value) is not owner:
            raise error(f"{label} must use the exact {owner.__name__} type")
        values = []
        for descriptor in descriptors:
            try:
                values.append(descriptor.__get__(value, owner))
            except attribute_error:
                raise error(f"{label} state is incomplete") from None
        if length(values) != length(names):
            raise error(f"{label} field boundary is inconsistent")
        return T(values)

    def valid_reference(value, label):
        if typ(value) is not S or reference_pattern.fullmatch(value) is None:
            raise error(f"{label} is invalid")
        lowered = value.casefold()
        if any_fn(marker in lowered for marker in secret_markers):
            raise error(f"{label} appears to contain secret material")
        return value

    def require_unsealed(registry, value, label):
        identity = id_fn(value)
        binding = registry.get(identity)
        if binding is None:
            return
        if typ(binding) is not T or length(binding) != 2:
            raise error(f"{label} seal registry is inconsistent")
        _, reference = binding
        current = reference()
        if current is value:
            raise error(f"{label} already has a live constructor seal")
        if current is not None:
            raise error(f"{label} seal identity collides with a live object")
        if registry.get(identity) is binding:
            registry.pop(identity, None)

    def register_sealed(registry, value, state, label):
        require_unsealed(registry, value, label)
        identity = id_fn(value)

        def remove(reference, expected_identity=identity):
            current = registry.get(expected_identity)
            if typ(current) is T and length(current) == 2 and current[1] is reference:
                registry.pop(expected_identity, None)

        reference = weakref_ref(value, remove)
        registry[identity] = (state, reference)

    def sealed_state(registry, value, expected_type, label):
        if typ(value) is not expected_type:
            raise error(f"{label} must use the exact {expected_type.__name__} type")
        binding = registry.get(id_fn(value))
        if typ(binding) is not T or length(binding) != 2:
            raise error(f"{label} was not constructor-sealed")
        state, reference = binding
        if reference() is not value:
            raise error(f"{label} seal is stale")
        return state

    def validate_record_values(values):
        membership_reference, owner_users_id, business_reference, version, status = values
        valid_reference(membership_reference, "membership reference")
        if typ(owner_users_id) is not I or owner_users_id <= 0:
            raise error("membership owner must be an exact positive users.id")
        valid_reference(business_reference, "membership business reference")
        if typ(version) is not I or version <= 0:
            raise error("membership version must be an exact positive integer")
        if typ(status) is not status_type:
            raise error("membership status must use the exact status type")
        return values

    def seal_record(record):
        require_unsealed(record_registry, record, "membership record")
        values = validate_record_values(
            raw_slots(
                record,
                OwnerBusinessMembershipRecord,
                record_slot_descriptors,
                record_field_names,
                "membership record",
            )
        )
        register_sealed(record_registry, record, values, "membership record")

    @_dataclass(frozen=True, slots=True, weakref_slot=True)
    class OwnerBusinessMembershipRecord:
        """One constructor-sealed fake-repository observation."""

        membership_reference: str
        owner_users_id: int
        business_reference: str
        membership_version: int
        status: MembershipStatus

        def __post_init__(self) -> None:
            seal_record(self)

    record_slot_descriptors = T(
        OwnerBusinessMembershipRecord.__dict__[name] for name in record_field_names
    )

    def record_state(record, *, require_public_match):
        state = sealed_state(
            record_registry,
            record,
            OwnerBusinessMembershipRecord,
            "membership record",
        )
        validate_record_values(state)
        if require_public_match:
            current = raw_slots(
                record,
                OwnerBusinessMembershipRecord,
                record_slot_descriptors,
                record_field_names,
                "membership record",
            )
            if current != state or any_fn(
                typ(current[index]) is not typ(state[index])
                for index in range_fn(length(state))
            ):
                raise error("membership record changed after construction")
        return state

    def snapshot_identity(snapshot_version, records):
        serialisable_records = T(
            values[:4] + (values[4].value,) for values in records
        )
        payload = (contract_version, snapshot_version, serialisable_records)
        encoded = dumps(payload, ensure_ascii=True, separators=(",", ":")).encode(
            "ascii"
        )
        return "owner-business-membership-snapshot:sha256-" + sha256(encoded).hexdigest()

    def validate_snapshot_uniqueness(records):
        membership_references = Set()
        business_owners = Dict()
        for values in records:
            membership_reference, owner_users_id, business_reference, _, _ = values
            if membership_reference in membership_references:
                raise error("membership references must be unique")
            membership_references.add(membership_reference)
            previous_owner = business_owners.setdefault(business_reference, owner_users_id)
            if previous_owner != owner_users_id:
                raise error(
                    "owner-only membership forbids a business reference shared across users"
                )

    def seal_fake(fake):
        # Refuse repeated public ``__post_init__`` calls before reading or
        # rewriting any public slot, especially ``snapshot_identity``.
        require_unsealed(fake_registry, fake, "membership snapshot")
        records, snapshot_version, public_identity = raw_slots(
            fake,
            InMemoryOwnerBusinessMembershipFake,
            fake_slot_descriptors,
            fake_field_names,
            "membership snapshot",
        )
        if typ(records) is not T:
            raise error("in-memory membership records must be an exact tuple")
        if typ(snapshot_version) is not I or snapshot_version <= 0:
            raise error("membership snapshot version must be an exact positive integer")
        if public_identity is not None:
            raise error("membership snapshot identity is constructor-controlled")
        canonical_records = T(
            record_state(record, require_public_match=True) for record in records
        )
        validate_snapshot_uniqueness(canonical_records)
        identity = snapshot_identity(snapshot_version, canonical_records)
        object_setattr(fake, "snapshot_identity", identity)
        register_sealed(
            fake_registry,
            fake,
            (snapshot_version, identity, canonical_records),
            "membership snapshot",
        )

    @_dataclass(frozen=True, slots=True, weakref_slot=True)
    class InMemoryOwnerBusinessMembershipFake:
        """Constructor-sealed, I/O-free membership snapshot."""

        records: tuple[OwnerBusinessMembershipRecord, ...]
        snapshot_version: int = 1
        snapshot_identity: str = _field(init=False, default=None, repr=True)

        def __post_init__(self) -> None:
            seal_fake(self)

    fake_slot_descriptors = T(
        InMemoryOwnerBusinessMembershipFake.__dict__[name] for name in fake_field_names
    )

    def snapshot_state(fake):
        state = sealed_state(
            fake_registry,
            fake,
            InMemoryOwnerBusinessMembershipFake,
            "membership snapshot",
        )
        version, identity, records = state
        if (
            typ(version) is not I
            or version <= 0
            or typ(identity) is not S
            or snapshot_identity_pattern.fullmatch(identity) is None
            or typ(records) is not T
            or identity != snapshot_identity(version, records)
        ):
            raise error("sealed membership snapshot is inconsistent")
        validate_snapshot_uniqueness(records)
        for values in records:
            validate_record_values(values)
        return state

    @_dataclass(frozen=True, slots=True)
    class OwnerBusinessMembershipDecision:
        """Detached structural decision, never a current access token."""

        contract_version: str
        decision_identity: str
        allowed: bool
        reason: MembershipDecisionReason
        authenticated_owner_users_id: int | None
        business_reference: str | None
        membership_reference: str | None
        membership_version: int | None
        snapshot_version: int
        snapshot_identity: str
        authenticated_owner_source: str
        owner_role: str
        business_reference_role: str
        freshness_role: str
        current_snapshot_authority: bool
        sharing_authority: bool
        runtime_access_authority: bool
        persistence_authority: bool
        production_authority: bool

        def __post_init__(self) -> None:
            validate_decision(self)

    decision_slot_descriptors = T(
        OwnerBusinessMembershipDecision.__dict__[name]
        for name in decision_field_names
    )

    def decision_payload(
        *, allowed, reason, owner_users_id, business_reference,
        membership_reference, membership_version, snapshot_version,
        snapshot_identity_value,
    ):
        return (
            contract_version,
            allowed,
            reason.value,
            owner_users_id,
            business_reference,
            membership_reference,
            membership_version,
            snapshot_version,
            snapshot_identity_value,
            authenticated_owner_source,
            owner_role,
            business_reference_role,
            freshness_role,
            False,
            False,
            False,
            False,
            False,
        )

    def decision_identity(payload):
        encoded = dumps(payload, ensure_ascii=True, separators=(",", ":")).encode(
            "ascii"
        )
        return "owner-business-membership:sha256-" + sha256(encoded).hexdigest()

    def make_decision(
        *, allowed, reason, owner_users_id, business_reference,
        membership_reference, membership_version, snapshot_version,
        snapshot_identity_value,
    ):
        payload = decision_payload(
            allowed=allowed,
            reason=reason,
            owner_users_id=owner_users_id,
            business_reference=business_reference,
            membership_reference=membership_reference,
            membership_version=membership_version,
            snapshot_version=snapshot_version,
            snapshot_identity_value=snapshot_identity_value,
        )
        return OwnerBusinessMembershipDecision(
            contract_version=contract_version,
            decision_identity=decision_identity(payload),
            allowed=allowed,
            reason=reason,
            authenticated_owner_users_id=owner_users_id,
            business_reference=business_reference,
            membership_reference=membership_reference,
            membership_version=membership_version,
            snapshot_version=snapshot_version,
            snapshot_identity=snapshot_identity_value,
            authenticated_owner_source=authenticated_owner_source,
            owner_role=owner_role,
            business_reference_role=business_reference_role,
            freshness_role=freshness_role,
            current_snapshot_authority=False,
            sharing_authority=False,
            runtime_access_authority=False,
            persistence_authority=False,
            production_authority=False,
        )

    def validate_decision(decision):
        values = raw_slots(
            decision,
            OwnerBusinessMembershipDecision,
            decision_slot_descriptors,
            decision_field_names,
            "membership decision",
        )
        mapped = Dict(zip_fn(decision_field_names, values, strict=True))
        for name, expected in (
            ("contract_version", contract_version),
            ("authenticated_owner_source", authenticated_owner_source),
            ("owner_role", owner_role),
            ("business_reference_role", business_reference_role),
            ("freshness_role", freshness_role),
        ):
            if typ(mapped[name]) is not S or mapped[name] != expected:
                raise error("membership decision authority metadata is invalid")
        if typ(mapped["decision_identity"]) is not S or (
            decision_identity_pattern.fullmatch(mapped["decision_identity"]) is None
        ):
            raise error("membership decision identity is invalid")
        if typ(mapped["allowed"]) is not B:
            raise error("membership decision allowed flag is invalid")
        if typ(mapped["reason"]) is not reason_type:
            raise error("membership decision reason is invalid")
        owner_users_id = mapped["authenticated_owner_users_id"]
        if owner_users_id is not None and (
            typ(owner_users_id) is not I or owner_users_id <= 0
        ):
            raise error("membership decision owner is invalid")
        for name in ("business_reference", "membership_reference"):
            value = mapped[name]
            if value is not None:
                valid_reference(value, f"membership decision {name}")
        membership_version = mapped["membership_version"]
        if membership_version is not None and (
            typ(membership_version) is not I or membership_version <= 0
        ):
            raise error("membership decision version is invalid")
        snapshot_version = mapped["snapshot_version"]
        if typ(snapshot_version) is not I or snapshot_version <= 0:
            raise error("membership decision snapshot version is invalid")
        snapshot_identity_value = mapped["snapshot_identity"]
        if typ(snapshot_identity_value) is not S or (
            snapshot_identity_pattern.fullmatch(snapshot_identity_value) is None
        ):
            raise error("membership decision snapshot identity is invalid")

        allowed_shape = (
            mapped["reason"] is active_reason
            and owner_users_id is not None
            and mapped["business_reference"] is not None
            and mapped["membership_reference"] is not None
            and membership_version is not None
        )
        denied_shape = (
            mapped["reason"] is not active_reason
            and mapped["membership_reference"] is None
            and membership_version is None
        )
        if mapped["allowed"] is not allowed_shape or (
            not mapped["allowed"] and not denied_shape
        ):
            raise error("membership decision outcome shape is inconsistent")
        for name in (
            "current_snapshot_authority",
            "sharing_authority",
            "runtime_access_authority",
            "persistence_authority",
            "production_authority",
        ):
            if typ(mapped[name]) is not B or mapped[name] is not False:
                raise error("membership decision authority boundary is invalid")

        payload = decision_payload(
            allowed=mapped["allowed"],
            reason=mapped["reason"],
            owner_users_id=owner_users_id,
            business_reference=mapped["business_reference"],
            membership_reference=mapped["membership_reference"],
            membership_version=membership_version,
            snapshot_version=snapshot_version,
            snapshot_identity_value=snapshot_identity_value,
        )
        if mapped["decision_identity"] != decision_identity(payload):
            raise error("membership decision identity is invalid")
        return decision

    def require_auth_namespace():
        if (
            auth_namespace.get("session") is not session_proxy
            or auth_namespace.get("_SK_USER_ID") is not session_user_id_key
            or typ(auth_namespace.get("_SK_USER_ID")) is not S
        ):
            raise error("captured authentication session boundary was altered")

    def evaluate_authenticated_owner_business_membership(
        *, membership_fake, requested_business_reference
    ):
        """Evaluate one request against the sealed owner-only snapshot."""

        snapshot_version, identity, records = snapshot_state(membership_fake)
        require_auth_namespace()
        try:
            owner_users_id = session_proxy.get(session_user_id_key)
        except exception_type:
            owner_users_id = None
        if typ(owner_users_id) is not I or owner_users_id <= 0:
            return make_decision(
                allowed=False,
                reason=MembershipDecisionReason.AUTHENTICATED_OWNER_UNAVAILABLE,
                owner_users_id=None,
                business_reference=None,
                membership_reference=None,
                membership_version=None,
                snapshot_version=snapshot_version,
                snapshot_identity_value=identity,
            )
        try:
            valid_reference(requested_business_reference, "requested business reference")
        except error:
            return make_decision(
                allowed=False,
                reason=MembershipDecisionReason.BUSINESS_REFERENCE_INVALID,
                owner_users_id=owner_users_id,
                business_reference=None,
                membership_reference=None,
                membership_version=None,
                snapshot_version=snapshot_version,
                snapshot_identity_value=identity,
            )

        matching = T(
            values
            for values in records
            if values[1] == owner_users_id
            and values[2] == requested_business_reference
        )
        if not matching:
            return make_decision(
                allowed=False,
                reason=MembershipDecisionReason.MEMBERSHIP_MISSING,
                owner_users_id=owner_users_id,
                business_reference=requested_business_reference,
                membership_reference=None,
                membership_version=None,
                snapshot_version=snapshot_version,
                snapshot_identity_value=identity,
            )
        if length(matching) != 1:
            return make_decision(
                allowed=False,
                reason=MembershipDecisionReason.MEMBERSHIP_AMBIGUOUS,
                owner_users_id=owner_users_id,
                business_reference=requested_business_reference,
                membership_reference=None,
                membership_version=None,
                snapshot_version=snapshot_version,
                snapshot_identity_value=identity,
            )

        membership_reference, _, business_reference, version, status = matching[0]
        if status is revoked_status:
            return make_decision(
                allowed=False,
                reason=MembershipDecisionReason.MEMBERSHIP_REVOKED,
                owner_users_id=owner_users_id,
                business_reference=requested_business_reference,
                membership_reference=None,
                membership_version=None,
                snapshot_version=snapshot_version,
                snapshot_identity_value=identity,
            )
        if status is not active_status:
            raise error("sealed membership status is unsupported")
        return make_decision(
            allowed=True,
            reason=active_reason,
            owner_users_id=owner_users_id,
            business_reference=business_reference,
            membership_reference=membership_reference,
            membership_version=version,
            snapshot_version=snapshot_version,
            snapshot_identity_value=identity,
        )

    def validate_owner_business_membership_decision(decision):
        """Validate detached structure without claiming current membership."""

        return validate_decision(decision)

    def assert_allowed_membership_decision_current(*, decision, membership_fake):
        """Raise unless an allowed decision exactly matches the supplied snapshot."""

        validate_decision(decision)
        values = raw_slots(
            decision,
            OwnerBusinessMembershipDecision,
            decision_slot_descriptors,
            decision_field_names,
            "membership decision",
        )
        mapped = Dict(zip_fn(decision_field_names, values, strict=True))
        if mapped["allowed"] is not True:
            raise error("only an allowed membership decision has freshness to verify")
        snapshot_version, identity, records = snapshot_state(membership_fake)
        if (
            mapped["snapshot_version"] != snapshot_version
            or mapped["snapshot_identity"] != identity
        ):
            raise error("allowed membership decision is stale for current snapshot")
        exact_active = T(
            values
            for values in records
            if values
            == (
                mapped["membership_reference"],
                mapped["authenticated_owner_users_id"],
                mapped["business_reference"],
                mapped["membership_version"],
                active_status,
            )
        )
        if length(exact_active) != 1:
            raise error("allowed membership decision is not current and active")
        return None

    return (
        OwnerBusinessMembershipRecord,
        InMemoryOwnerBusinessMembershipFake,
        OwnerBusinessMembershipDecision,
        evaluate_authenticated_owner_business_membership,
        validate_owner_business_membership_decision,
        assert_allowed_membership_decision_current,
    )


(
    OwnerBusinessMembershipRecord,
    InMemoryOwnerBusinessMembershipFake,
    OwnerBusinessMembershipDecision,
    evaluate_authenticated_owner_business_membership,
    validate_owner_business_membership_decision,
    assert_allowed_membership_decision_current,
) = _build_contract()
del _build_contract

for _public_type in (
    OwnerBusinessMembershipRecord,
    InMemoryOwnerBusinessMembershipFake,
    OwnerBusinessMembershipDecision,
):
    _public_type.__module__ = __name__
    _public_type.__qualname__ = _public_type.__name__
del _public_type


__all__ = [
    "CONTRACT_VERSION",
    "AUTHENTICATED_OWNER_SOURCE",
    "OWNER_ROLE",
    "BUSINESS_REFERENCE_ROLE",
    "FRESHNESS_ROLE",
    "MembershipContractError",
    "MembershipStatus",
    "MembershipDecisionReason",
    "OwnerBusinessMembershipRecord",
    "InMemoryOwnerBusinessMembershipFake",
    "OwnerBusinessMembershipDecision",
    "evaluate_authenticated_owner_business_membership",
    "validate_owner_business_membership_decision",
    "assert_allowed_membership_decision_current",
]
