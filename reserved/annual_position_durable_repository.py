"""Mutable local persistence for reviewed, minimised annual-position records.

This is the physical counterpart to W9-S3A--E.  It uses Reserved's normal
SQLite database, stores only the S3B canonical envelope and evidence references,
and has no HTTP route or import-time side effect.  It is deliberately fail
closed: callers must provide all still-external governance identities, and an
erasure cannot execute without an explicit, separately recorded hold/backup
clearance.  It does not select a production datastore, key provider, retention
period, lawful basis, or target runtime.

The external-authority adapter below is a disabled composition seam, not a
verified trust anchor by itself.  An arbitrary in-process adapter can claim a
record is valid; production use therefore remains disabled until a separately
owned verifier and invocation boundary are supplied and independently accepted.
"""

from __future__ import annotations

import hashlib
import json
import re
import weakref
from dataclasses import dataclass
from datetime import datetime, timezone

from reserved import database
from reserved.annual_position_repository_contract import (
    RepositoryContractError,
    bind_governance_inputs,
    decode_annual_position_record,
    project_annual_position_record,
    repository_record_identity,
)
from reserved.billing.event_inbox_contract import canonical_owner_id_from_users_id


class DurableAnnualPositionError(ValueError):
    """The authenticated durable annual-position boundary failed closed."""


class DurablePayeReadSnapshot:
    """Opaque, transaction-issued annual/PAYE authorization snapshot."""
    __slots__ = ("__weakref__",)

    def __new__(cls, *args, **kwargs):
        raise TypeError("durable PAYE snapshots are repository-issued only")


_PAYE_SNAPSHOTS: dict[int, tuple[weakref.ReferenceType, int, str, str, str, object, tuple[dict, ...]]] = {}


def _issue_paye_snapshot(*, owner, business, tax_year, nation, record, entries):
    snapshot = object.__new__(DurablePayeReadSnapshot)
    key = id(snapshot)

    def discard(_):
        _PAYE_SNAPSHOTS.pop(key, None)

    _PAYE_SNAPSHOTS[key] = (
        weakref.ref(snapshot, discard), owner, business, tax_year, nation,
        record, tuple(dict(entry) for entry in entries),
    )
    return snapshot


def project_durable_paye_snapshot(snapshot, *, authenticated_user_id, business_reference,
                                  tax_year, nation):
    """Return the exact captured record/rows or reject replay/substitution."""
    if type(snapshot) is not DurablePayeReadSnapshot:
        raise DurableAnnualPositionError("durable PAYE snapshot is not repository-issued")
    binding = _PAYE_SNAPSHOTS.get(id(snapshot))
    if (binding is None or binding[0]() is not snapshot
            or binding[1:5] != (authenticated_user_id, business_reference, tax_year, nation)):
        raise DurableAnnualPositionError("durable PAYE snapshot scope is unavailable")
    return binding[5], [dict(row) for row in binding[6]]


_REFERENCE = re.compile(r"^[a-z][a-z0-9_-]{1,31}:[A-Za-z0-9][A-Za-z0-9._/-]{0,95}$")
_AUDIT = re.compile(r"^audit:[A-Za-z0-9][A-Za-z0-9._/-]{0,95}$")
_IDENTITY = re.compile(r"^annual-position-structural:sha256-[0-9a-f]{64}$")
_CLEARANCE = re.compile(r"^(?:legal-hold|backup-expiry):cleared-[A-Za-z0-9][A-Za-z0-9._/-]{0,95}$")
_INTERNAL_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_UNSAFE_MARKERS = ("secret", "token", "password", "credential", "apikey", "api_key", "bearer", "private_key")
RECORD_PURPOSE = "annual_cash_position_durable_projection"
def _utc(value: str, label: str) -> datetime:
    if type(value) is not str:
        raise DurableAnnualPositionError(f"{label} must be an exact UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise DurableAnnualPositionError(f"{label} must be an exact UTC timestamp") from exc
    if parsed.tzinfo is not timezone.utc or parsed.isoformat() != value:
        raise DurableAnnualPositionError(f"{label} must be an exact UTC timestamp")
    return parsed


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True)


def _tuplify(value: object):
    """Recover the contract's exact immutable primitive graph from JSON."""
    if type(value) is list:
        return tuple(_tuplify(item) for item in value)
    if type(value) in (str, int, bool) or value is None:
        return value
    raise DurableAnnualPositionError("stored annual position contains a non-primitive JSON value")


def _reference(value: str, prefix: str) -> str:
    if type(value) is not str or not _REFERENCE.fullmatch(value) or not value.startswith(prefix):
        raise DurableAnnualPositionError(f"invalid {prefix[:-1]} governance reference")
    if any(word in value.casefold() for word in ("pending", "unknown", "unresolved", "placeholder") + _UNSAFE_MARKERS):
        raise DurableAnnualPositionError("governance reference is unresolved or unsafe")
    return value


@dataclass(frozen=True, slots=True)
class DurableGovernance:
    """Opaque accepted-policy identities; values are never invented by this module."""

    retention_policy_version: str
    erasure_disposition: str
    crypto_key_version: str
    target_profile: str

    def contract_handle(self):
        try:
            return bind_governance_inputs(
                retention_policy_version=_reference(self.retention_policy_version, "retention:"),
                erasure_disposition=_reference(self.erasure_disposition, "erasure:"),
                crypto_key_version=_reference(self.crypto_key_version, "crypto:"),
                target_profile=_reference(self.target_profile, "target:"),
            )
        except RepositoryContractError as exc:
            raise DurableAnnualPositionError("governance configuration is not complete") from exc

    @property
    def fingerprint(self) -> str:
        raw = _canonical((self.retention_policy_version, self.erasure_disposition,
                          self.crypto_key_version, self.target_profile)).encode("ascii")
        return "annual-position-governance:sha256-" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True, weakref_slot=True)
class MembershipAuthorityEvidence:
    issuer_reference: str
    owner_user_id: int
    business_reference: str
    membership_reference: str
    membership_version: int
    state: str
    issued_at: str
    expires_at: str
    revoked_at: str | None = None


@dataclass(frozen=True, slots=True, weakref_slot=True)
class AccountErasureClearance:
    issuer_reference: str
    clearance_kind: str
    purpose: str
    owner_user_id: int
    account_reference: str
    issued_at: str
    expires_at: str
    state: str
    revoked_at: str | None = None


@dataclass(frozen=True, slots=True)
class LocalTaxDataErasureResult:
    """Counts of locally deleted tax-data rows.

    This is deliberately narrower than a representation of a completed
    account deletion.  It says nothing about backups, an identity provider,
    other product data, or physical media sanitisation.
    """

    annual_position_records: int
    paye_manual_entries: int


@dataclass(frozen=True, slots=True, weakref_slot=True)
class ApprovedEvidenceReferencePolicy:
    issuer_reference: str
    policy_version: str
    allowed_references: tuple[str, ...]


class ExternalAuthorityAdapter:
    """Capability supplied by a separately owned authority-verification boundary.

    This module deliberately provides no issuer, signing key, factory, or local
    fallback.  Deployments must inject an implementation which independently
    verifies the immutable records against the applicable authoritative source.
    Without one, membership and erasure operations remain unavailable.
    """

    authority_identity: str

    def verify_membership_authority(self, evidence: MembershipAuthorityEvidence) -> bool:
        raise NotImplementedError

    def verify_account_erasure_clearance(self, clearance: AccountErasureClearance) -> bool:
        raise NotImplementedError

    def verify_evidence_reference_policy(self, policy: ApprovedEvidenceReferencePolicy) -> bool:
        raise NotImplementedError


def _validate_membership_evidence(value: MembershipAuthorityEvidence) -> None:
    if type(value) is not MembershipAuthorityEvidence:
        raise DurableAnnualPositionError("membership authority evidence is malformed")
    _reference(value.issuer_reference, "membership:")
    if type(value.owner_user_id) is not int or value.owner_user_id <= 0 or value.state not in ("active", "revoked"):
        raise DurableAnnualPositionError("membership authority evidence is invalid")
    if _INTERNAL_REFERENCE.fullmatch(value.business_reference) is None or _INTERNAL_REFERENCE.fullmatch(value.membership_reference) is None:
        raise DurableAnnualPositionError("membership authority references are invalid")
    issued, expiry = _utc(value.issued_at, "membership issued-at"), _utc(value.expires_at, "membership expiry")
    if issued >= expiry or type(value.membership_version) is not int or value.membership_version < 1:
        raise DurableAnnualPositionError("membership authority timing or version is invalid")
    if value.state == "active" and value.revoked_at is not None:
        raise DurableAnnualPositionError("active membership authority cannot be revoked")
    if value.state == "revoked" and (value.revoked_at is None or _utc(value.revoked_at, "membership revoked-at") < issued):
        raise DurableAnnualPositionError("revoked membership authority is invalid")


def _validate_erasure_clearance(value: AccountErasureClearance) -> None:
    if type(value) is not AccountErasureClearance:
        raise DurableAnnualPositionError("account erasure clearance is malformed")
    _reference(value.issuer_reference, "lifecycle:")
    if (value.clearance_kind not in ("legal_hold_clear", "backup_expiry_confirmed")
            or value.purpose != "account_erasure" or type(value.owner_user_id) is not int
            or value.owner_user_id <= 0 or value.account_reference != str(value.owner_user_id)
            or value.state not in ("current", "revoked")):
        raise DurableAnnualPositionError("account erasure clearance is invalid")
    issued, expiry = _utc(value.issued_at, "clearance issued-at"), _utc(value.expires_at, "clearance expiry")
    if issued >= expiry:
        raise DurableAnnualPositionError("account erasure clearance timing is invalid")
    if value.state == "current" and value.revoked_at is not None:
        raise DurableAnnualPositionError("current clearance cannot be revoked")
    if value.state == "revoked" and (value.revoked_at is None or _utc(value.revoked_at, "clearance revoked-at") < issued):
        raise DurableAnnualPositionError("revoked clearance is invalid")


def _validate_evidence_policy(value: ApprovedEvidenceReferencePolicy) -> None:
    if type(value) is not ApprovedEvidenceReferencePolicy:
        raise DurableAnnualPositionError("evidence-reference policy is malformed")
    _reference(value.issuer_reference, "evidence-policy:")
    if type(value.policy_version) is not str or _INTERNAL_REFERENCE.fullmatch(value.policy_version) is None:
        raise DurableAnnualPositionError("evidence-reference policy version is invalid")
    if type(value.allowed_references) is not tuple or not value.allowed_references:
        raise DurableAnnualPositionError("evidence-reference policy is empty")
    if len(set(value.allowed_references)) != len(value.allowed_references):
        raise DurableAnnualPositionError("evidence-reference policy is ambiguous")
    for reference in value.allowed_references:
        if type(reference) is not str or _REFERENCE.fullmatch(reference) is None or ":" not in reference:
            raise DurableAnnualPositionError("evidence reference must have an approved issuer and field")


class DurableAnnualPositionRepository:
    """Owner-bound, transactional repository over Reserved's application database."""

    def __init__(self, governance: DurableGovernance, *, evidence_reference_policy,
                 membership_issuer_reference: str, lifecycle_issuer_reference: str,
                 external_authority_adapter: ExternalAuthorityAdapter | None = None):
        if type(governance) is not DurableGovernance:
            raise DurableAnnualPositionError("exact governance configuration is required")
        self._governance = governance
        self._contract_governance = governance.contract_handle()
        _validate_evidence_policy(evidence_reference_policy)
        if external_authority_adapter is None:
            self._external_authority_available = False
            self._verify_membership_authority = None
            self._verify_account_erasure_clearance = None
            self._verify_evidence_reference_policy = None
            self._evidence_reference_policy = evidence_reference_policy
            self._membership_issuer_reference = _reference(membership_issuer_reference, "membership:")
            self._lifecycle_issuer_reference = _reference(lifecycle_issuer_reference, "lifecycle:")
            return
        if not isinstance(external_authority_adapter, ExternalAuthorityAdapter):
            raise DurableAnnualPositionError("independently verifiable external authority adapter is required")
        identity = getattr(external_authority_adapter, "authority_identity", None)
        _reference(identity, "authority:")
        self._verify_membership_authority = external_authority_adapter.verify_membership_authority
        self._verify_account_erasure_clearance = external_authority_adapter.verify_account_erasure_clearance
        self._verify_evidence_reference_policy = external_authority_adapter.verify_evidence_reference_policy
        if any(type(method) is not type(self._verify_membership_authority) for method in (
                self._verify_account_erasure_clearance, self._verify_evidence_reference_policy)):
            raise DurableAnnualPositionError("external authority adapter is incomplete")
        try:
            policy_verified = self._verify_evidence_reference_policy(evidence_reference_policy)
        except Exception as exc:
            raise DurableAnnualPositionError("evidence-reference policy authority is unavailable") from exc
        if policy_verified is not True:
            raise DurableAnnualPositionError("evidence-reference policy lacks external authority")
        self._external_authority_available = True
        self._evidence_reference_policy = evidence_reference_policy
        self._membership_issuer_reference = _reference(membership_issuer_reference, "membership:")
        self._lifecycle_issuer_reference = _reference(lifecycle_issuer_reference, "lifecycle:")

    def assert_external_authority_available(self) -> None:
        """Fail closed unless a separately supplied verifier is configured.

        This proves capability presence only.  It does not convert an
        in-process adapter into production authority; callers still need their
        separately accepted invocation boundary and target evidence.
        """
        self._require_external_authority()

    def _require_external_authority(self) -> None:
        if not self._external_authority_available:
            raise DurableAnnualPositionError("external authority verifier is not configured; operation is disabled")

    def _require_current_erasure_clearances(self, *, authenticated_user_id: int,
                                            legal_hold_clearance: AccountErasureClearance,
                                            backup_expiry_clearance: AccountErasureClearance) -> None:
        """Verify the two independently-issued lifecycle clearances.

        The local repository can only establish that the supplied external
        verifier accepted current clearances.  It cannot itself establish
        backup expiry, legal status, or erasure outside this SQLite store.
        """
        self._require_external_authority()
        _validate_erasure_clearance(legal_hold_clearance)
        _validate_erasure_clearance(backup_expiry_clearance)
        for clearance in (legal_hold_clearance, backup_expiry_clearance):
            try:
                verified = self._verify_account_erasure_clearance(clearance)
            except Exception as exc:
                raise DurableAnnualPositionError("account erasure authority verification is unavailable") from exc
            if verified is not True:
                raise DurableAnnualPositionError("account erasure clearance lacks independent verification")
        now_value = datetime.now(timezone.utc)
        for clearance, kind in ((legal_hold_clearance, "legal_hold_clear"),
                                (backup_expiry_clearance, "backup_expiry_confirmed")):
            if (clearance.issuer_reference != self._lifecycle_issuer_reference
                    or clearance.clearance_kind != kind
                    or clearance.owner_user_id != authenticated_user_id
                    or clearance.account_reference != str(authenticated_user_id)
                    or clearance.state != "current"
                    or _utc(clearance.expires_at, "clearance expiry") <= now_value):
                raise DurableAnnualPositionError("account erasure clearance is not current and account-bound")

    @staticmethod
    def _audit(value: str) -> str:
        if type(value) is not str or _AUDIT.fullmatch(value) is None:
            raise DurableAnnualPositionError("a redacted audit reference is required")
        if any(marker in value.casefold() for marker in _UNSAFE_MARKERS):
            raise DurableAnnualPositionError("audit reference appears to contain secret material")
        return value

    @staticmethod
    def _require_user(conn, user_id: int) -> str:
        try:
            owner = canonical_owner_id_from_users_id(user_id)
        except ValueError as exc:
            raise DurableAnnualPositionError("authenticated users.id is invalid") from exc
        if conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
            raise DurableAnnualPositionError("authenticated user no longer exists")
        return owner

    @staticmethod
    def _active_membership(conn, user_id: int, business_reference: str) -> None:
        row = conn.execute(
            "SELECT membership_version,authority_expires_at FROM owner_business_memberships "
            "WHERE user_id = ? AND business_reference = ? AND status = 'active'",
            (user_id, business_reference),
        ).fetchall()
        if len(row) != 1:
            raise DurableAnnualPositionError("active owner-to-business membership is required")
        expiry = row[0][1]
        if expiry is None or _utc(expiry, "membership authority expiry") <= datetime.now(timezone.utc):
            raise DurableAnnualPositionError("owner-to-business membership authority has expired")

    @classmethod
    def _all_record_memberships_current(cls, conn, user_id: int) -> None:
        businesses = conn.execute(
            "SELECT DISTINCT business_reference FROM annual_position_records "
            "WHERE user_id=? AND state != 'deleted'", (user_id,)
        ).fetchall()
        for (business_reference,) in businesses:
            cls._active_membership(conn, user_id, business_reference)

    def register_owner_business_membership(self, *, user_id: int, business_reference: str,
                                           membership_authority: MembershipAuthorityEvidence,
                                           audit_reference: str) -> None:
        """Create the one-owner membership row; callers must already own the user id.

        This low-level primitive has no HTTP exposure.  A future business
        lifecycle must decide who is authorised to call it.
        """
        self._audit(audit_reference)
        self._require_external_authority()
        _validate_membership_evidence(membership_authority)
        try:
            verified = self._verify_membership_authority(membership_authority)
        except Exception as exc:
            raise DurableAnnualPositionError("membership authority verification is unavailable") from exc
        if verified is not True:
            raise DurableAnnualPositionError("membership authority lacks independent verification")
        if (membership_authority.issuer_reference != self._membership_issuer_reference
                or membership_authority.owner_user_id != user_id
                or membership_authority.business_reference != business_reference
                or membership_authority.state != "active"
                or _utc(membership_authority.expires_at, "membership expiry") <= datetime.now(timezone.utc)):
            raise DurableAnnualPositionError("membership authority is not current for this owner and business")
        with database._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._require_user(conn, user_id)
            current = conn.execute(
                "SELECT user_id, membership_reference, membership_version, status, authority_expires_at FROM owner_business_memberships "
                "WHERE business_reference = ?", (business_reference,)
            ).fetchall()
            if current:
                if (len(current) != 1 or current[0][0] != user_id
                        or current[0][1] != membership_authority.membership_reference
                        or current[0][2] != membership_authority.membership_version
                        or current[0][3] != "active"
                        or current[0][4] != membership_authority.expires_at
                        or _utc(current[0][4], "stored membership expiry") <= datetime.now(timezone.utc)):
                    raise DurableAnnualPositionError("business membership is already owned or unavailable")
                return
            conn.execute(
                "INSERT INTO owner_business_memberships "
                "(user_id,business_reference,membership_reference,membership_version,status,authority_expires_at,created_at) "
                "VALUES (?,?,?,?, 'active', ?, ?)",
                (user_id, business_reference, membership_authority.membership_reference,
                 membership_authority.membership_version, membership_authority.expires_at, _utc_now()),
            )

    def renew_owner_business_membership(self, *, user_id: int, business_reference: str,
                                        membership_authority: MembershipAuthorityEvidence,
                                        audit_reference: str) -> None:
        """Atomically replace only a live membership with a newer verified authority."""
        self._audit(audit_reference)
        self._require_external_authority()
        _validate_membership_evidence(membership_authority)
        try:
            verified = self._verify_membership_authority(membership_authority)
        except Exception as exc:
            raise DurableAnnualPositionError("membership authority verification is unavailable") from exc
        if (verified is not True or membership_authority.issuer_reference != self._membership_issuer_reference
                or membership_authority.owner_user_id != user_id
                or membership_authority.business_reference != business_reference
                or membership_authority.state != "active"
                or _utc(membership_authority.expires_at, "membership expiry") <= datetime.now(timezone.utc)):
            raise DurableAnnualPositionError("membership renewal authority is not current and exact")
        with database._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._require_user(conn, user_id)
            current = conn.execute(
                "SELECT membership_version,authority_expires_at,status FROM owner_business_memberships "
                "WHERE user_id=? AND business_reference=?", (user_id, business_reference),
            ).fetchall()
            if len(current) != 1 or current[0][2] != "active":
                raise DurableAnnualPositionError("membership renewal is revoked or unavailable")
            old_version, old_expiry, _ = current[0]
            if old_expiry is None or _utc(old_expiry, "stored membership expiry") <= datetime.now(timezone.utc):
                raise DurableAnnualPositionError("expired membership cannot be renewed without a separate restoration authority")
            if membership_authority.membership_version <= old_version:
                raise DurableAnnualPositionError("membership renewal version is stale")
            changed = conn.execute(
                "UPDATE owner_business_memberships SET membership_reference=?,membership_version=?,authority_expires_at=? "
                "WHERE user_id=? AND business_reference=? AND membership_version=? AND status='active'",
                (membership_authority.membership_reference, membership_authority.membership_version,
                 membership_authority.expires_at, user_id, business_reference, old_version),
            ).rowcount
            if changed != 1:
                raise DurableAnnualPositionError("membership renewal lost the revocation race")

    def revoke_owner_business_membership(self, *, user_id: int, business_reference: str,
                                         membership_authority: MembershipAuthorityEvidence,
                                         audit_reference: str) -> None:
        """Apply only a current, issuer-bound revocation for the exact membership."""
        self._audit(audit_reference)
        self._require_external_authority()
        _validate_membership_evidence(membership_authority)
        try:
            verified = self._verify_membership_authority(membership_authority)
        except Exception as exc:
            raise DurableAnnualPositionError("membership authority verification is unavailable") from exc
        if verified is not True:
            raise DurableAnnualPositionError("membership revocation lacks independent verification")
        if (membership_authority.issuer_reference != self._membership_issuer_reference
                or membership_authority.owner_user_id != user_id
                or membership_authority.business_reference != business_reference
                or membership_authority.state != "revoked"
                or _utc(membership_authority.expires_at, "membership expiry") <= datetime.now(timezone.utc)
                or _utc(membership_authority.revoked_at, "membership revoked-at") > datetime.now(timezone.utc)):
            raise DurableAnnualPositionError("membership revocation authority is not exact")
        with database._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._require_user(conn, user_id)
            changed = conn.execute(
                "UPDATE owner_business_memberships SET status='revoked', revoked_at=? "
                "WHERE user_id=? AND business_reference=? AND membership_reference=? AND membership_version=? AND status='active'",
                (_utc_now(), user_id, business_reference, membership_authority.membership_reference,
                 membership_authority.membership_version),
            ).rowcount
            if changed != 1:
                raise DurableAnnualPositionError("membership revocation is stale or unavailable")

    def _decode_owned(self, *, user_id: int, business_reference: str, record):
        try:
            envelope = project_annual_position_record(record)
            decoded = decode_annual_position_record(envelope, self._contract_governance, "audit:durable-decode")
            identity = repository_record_identity(decoded)
        except RepositoryContractError as exc:
            raise DurableAnnualPositionError("annual-position record failed canonical integrity validation") from exc
        row = dict(envelope[2])
        if row["user_id"] != canonical_owner_id_from_users_id(user_id) or row["business_id"] != business_reference:
            raise DurableAnnualPositionError("record crossed authenticated owner or business boundary")
        if identity != row["record_identity"]:
            raise DurableAnnualPositionError("record identity changed during decode")
        if any(reference not in self._evidence_reference_policy.allowed_references
               for reference in row["evidence_references"]):
            raise DurableAnnualPositionError("record contains an unapproved evidence issuer or field")
        encoded = _canonical(envelope)
        return row, envelope, encoded, hashlib.sha256(encoded.encode("ascii")).hexdigest()

    def create_or_read(self, *, authenticated_user_id: int, business_reference: str,
                       record, audit_reference: str) -> str:
        """Atomically create a version-one record or return its exact replay identity."""
        self._audit(audit_reference)
        with database._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._require_user(conn, authenticated_user_id)
            self._active_membership(conn, authenticated_user_id, business_reference)
            row, envelope, encoded, digest = self._decode_owned(
                user_id=authenticated_user_id, business_reference=business_reference, record=record)
            if row["record_version"] != 1 or row["predecessor_identity"] is not None:
                raise DurableAnnualPositionError("initial create requires version one without predecessor")
            existing = conn.execute(
                "SELECT envelope_sha256 FROM annual_position_records WHERE record_identity = ?",
                (row["record_identity"],),
            ).fetchone()
            if existing is not None:
                if existing[0] != digest:
                    raise DurableAnnualPositionError("record identity conflicts with different content")
                return row["record_identity"]
            duplicate = conn.execute(
                "SELECT record_identity FROM annual_position_records WHERE user_id=? AND business_reference=? "
                "AND tax_year=? AND nation=? AND record_purpose=? AND state='current'",
                (authenticated_user_id, business_reference, row["tax_year"], row["nation"], row["record_purpose"]),
            ).fetchone()
            if duplicate is not None:
                raise DurableAnnualPositionError("current annual position already exists; use supersession CAS")
            self._insert_record(conn, row, envelope, digest, authenticated_user_id, "created", audit_reference)
            return row["record_identity"]

    def supersede(self, *, authenticated_user_id: int, business_reference: str, record,
                  expected_current_identity: str, audit_reference: str) -> str:
        """Atomically replace the current record only when its identity still matches."""
        self._audit(audit_reference)
        if type(expected_current_identity) is not str or _IDENTITY.fullmatch(expected_current_identity) is None:
            raise DurableAnnualPositionError("exact expected current identity is required")
        with database._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._require_user(conn, authenticated_user_id)
            self._active_membership(conn, authenticated_user_id, business_reference)
            row, envelope, _encoded, digest = self._decode_owned(
                user_id=authenticated_user_id, business_reference=business_reference, record=record)
            current = conn.execute(
                "SELECT record_identity,record_version,tax_year,nation,record_purpose FROM annual_position_records "
                "WHERE user_id=? AND business_reference=? AND tax_year=? AND nation=? AND record_purpose=? AND state='current'",
                (authenticated_user_id, business_reference, row["tax_year"], row["nation"], row["record_purpose"]),
            ).fetchone()
            if current is None or current[0] != expected_current_identity:
                raise DurableAnnualPositionError("supersession compare-and-swap conflict")
            if row["record_version"] != current[1] + 1 or row["predecessor_identity"] != current[0]:
                raise DurableAnnualPositionError("successor lineage is not exactly current")
            conn.execute("UPDATE annual_position_records SET state='superseded' WHERE record_identity=?", (current[0],))
            self._insert_record(conn, row, envelope, digest, authenticated_user_id, "superseded", audit_reference)
            return row["record_identity"]

    def _insert_record(self, conn, row, envelope, digest: str, user_id: int, event: str, audit: str) -> None:
        conn.execute(
            "INSERT INTO annual_position_records "
            "(record_identity,user_id,business_reference,tax_year,nation,record_purpose,record_version,predecessor_identity,"
            "governance_fingerprint,envelope_json,envelope_sha256,state,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,'current',?)",
            (row["record_identity"], user_id, row["business_id"], row["tax_year"], row["nation"], row["record_purpose"],
             row["record_version"], row["predecessor_identity"], self._governance.fingerprint,
             _canonical(envelope), digest, _utc_now()),
        )
        for position, evidence in enumerate(row["evidence_references"]):
            conn.execute("INSERT INTO annual_position_evidence_references VALUES (?,?,?)",
                         (row["record_identity"], position, evidence))
        conn.execute(
            "INSERT INTO annual_position_lifecycle_events (record_identity,user_id,event_kind,audit_reference,occurred_at) "
            "VALUES (?,?,?,?,?)", (row["record_identity"], user_id, event, audit, _utc_now()),
        )

    def read_current(self, *, authenticated_user_id: int, business_reference: str,
                     tax_year: str, nation: str, record_purpose: str,
                     audit_reference: str):
        self._audit(audit_reference)
        if type(record_purpose) is not str or record_purpose != RECORD_PURPOSE:
            raise DurableAnnualPositionError("annual-position record purpose is unavailable")
        with database._connection() as conn:
            self._require_user(conn, authenticated_user_id)
            self._active_membership(conn, authenticated_user_id, business_reference)
            found = conn.execute(
                "SELECT record_identity,record_purpose,governance_fingerprint,envelope_json,envelope_sha256 "
                "FROM annual_position_records WHERE user_id=? AND business_reference=? "
                "AND tax_year=? AND nation=? AND record_purpose=? AND state='current'",
                (authenticated_user_id, business_reference, tax_year, nation, record_purpose),
            ).fetchall()
            if len(found) != 1:
                raise DurableAnnualPositionError("current annual position is unavailable")
            identity, stored_purpose, stored_governance, raw, expected = found[0]
            if stored_purpose != record_purpose:
                raise DurableAnnualPositionError("stored annual position purpose changed")
            if stored_governance != self._governance.fingerprint:
                raise DurableAnnualPositionError("stored annual position governance profile changed")
            if hashlib.sha256(raw.encode("ascii")).hexdigest() != expected:
                raise DurableAnnualPositionError("stored annual position integrity check failed")
            try:
                decoded = decode_annual_position_record(
                    _tuplify(json.loads(raw)), self._contract_governance, "audit:durable-read"
                )
                if dict(project_annual_position_record(decoded)[2])["record_purpose"] != record_purpose:
                    raise DurableAnnualPositionError("stored annual position purpose integrity check failed")
                conn.execute(
                    "INSERT INTO annual_position_read_audit "
                    "(record_identity,user_id,business_reference,audit_reference,occurred_at) VALUES (?,?,?,?,?)",
                    (identity, authenticated_user_id, business_reference, audit_reference, _utc_now()),
                )
                return decoded
            except (ValueError, RepositoryContractError) as exc:
                raise DurableAnnualPositionError("stored annual position failed canonical validation") from exc

    def read_current_paye_snapshot(self, *, authenticated_user_id: int, business_reference: str,
                                   tax_year: str, nation: str, record_purpose: str,
                                   audit_reference: str):
        """Atomically capture membership, current annual record and active PAYE rows.

        ``BEGIN IMMEDIATE`` serialises this authorization read with membership
        revocation and PAYE replacement/deletion writes. Consumers must use the
        returned opaque snapshot rather than separately re-reading either
        boundary.
        """
        self._audit(audit_reference)
        if type(record_purpose) is not str or record_purpose != RECORD_PURPOSE:
            raise DurableAnnualPositionError("annual-position record purpose is unavailable")
        with database._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._require_user(conn, authenticated_user_id)
            self._active_membership(conn, authenticated_user_id, business_reference)
            found = conn.execute(
                "SELECT record_identity,record_purpose,governance_fingerprint,envelope_json,envelope_sha256 "
                "FROM annual_position_records WHERE user_id=? AND business_reference=? "
                "AND tax_year=? AND nation=? AND record_purpose=? AND state='current'",
                (authenticated_user_id, business_reference, tax_year, nation, record_purpose),
            ).fetchall()
            if len(found) != 1:
                raise DurableAnnualPositionError("current annual position is unavailable")
            identity, stored_purpose, stored_governance, raw, expected = found[0]
            if (stored_purpose != record_purpose or stored_governance != self._governance.fingerprint
                    or hashlib.sha256(raw.encode("ascii")).hexdigest() != expected):
                raise DurableAnnualPositionError("stored annual position integrity check failed")
            try:
                decoded = decode_annual_position_record(
                    _tuplify(json.loads(raw)), self._contract_governance, "audit:durable-paye-read"
                )
                if dict(project_annual_position_record(decoded)[2])["record_purpose"] != record_purpose:
                    raise DurableAnnualPositionError("stored annual position purpose integrity check failed")
            except (ValueError, RepositoryContractError) as exc:
                raise DurableAnnualPositionError("stored annual position failed canonical validation") from exc
            rows = [dict(row) for row in conn.execute(
                "SELECT * FROM paye_manual_entries WHERE user_id=? AND tax_year=? "
                "AND replaced_at IS NULL AND deleted_at IS NULL ORDER BY employment_slot,id",
                (authenticated_user_id, tax_year),
            ).fetchall()]
            conn.execute(
                "INSERT INTO annual_position_read_audit "
                "(record_identity,user_id,business_reference,audit_reference,occurred_at) VALUES (?,?,?,?,?)",
                (identity, authenticated_user_id, business_reference, audit_reference, _utc_now()),
            )
            return _issue_paye_snapshot(
                owner=authenticated_user_id, business=business_reference, tax_year=tax_year,
                nation=nation, record=decoded, entries=rows,
            )

    def plan_account_erasure(self, *, authenticated_user_id: int, audit_reference: str) -> tuple[str, ...]:
        """Return only the owned records that require separately-cleared erasure execution."""
        self._audit(audit_reference)
        with database._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._require_user(conn, authenticated_user_id)
            # Account erasure is a lifecycle right for the historically
            # authenticated owner, not ordinary business access.  A revoked or
            # expired membership must not strand the owner's minimised records.
            rows = conn.execute(
                "SELECT record_identity FROM annual_position_records WHERE user_id=? AND state != 'deleted' ORDER BY record_identity",
                (authenticated_user_id,),
            ).fetchall()
            for (identity,) in rows:
                conn.execute("INSERT INTO annual_position_lifecycle_events (record_identity,user_id,event_kind,audit_reference,occurred_at) VALUES (?,?,?,?,?)",
                             (identity, authenticated_user_id, "erasure_planned", audit_reference, _utc_now()))
            return tuple(row[0] for row in rows)

    def execute_account_erasure(self, *, authenticated_user_id: int, audit_reference: str,
                                legal_hold_clearance: AccountErasureClearance,
                                backup_expiry_clearance: AccountErasureClearance) -> int:
        """Delete only after current immutable legal-hold and backup clearances."""
        self._audit(audit_reference)
        self._require_current_erasure_clearances(
            authenticated_user_id=authenticated_user_id,
            legal_hold_clearance=legal_hold_clearance,
            backup_expiry_clearance=backup_expiry_clearance,
        )
        with database._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._require_user(conn, authenticated_user_id)
            # See plan_account_erasure: clearance-based lifecycle deletion is
            # deliberately independent of current business membership.
            rows = conn.execute("SELECT record_identity FROM annual_position_records WHERE user_id=? AND state != 'deleted'",
                                (authenticated_user_id,)).fetchall()
            now = _utc_now()
            for (identity,) in rows:
                conn.execute("DELETE FROM annual_position_evidence_references WHERE record_identity=?", (identity,))
                conn.execute("UPDATE annual_position_records SET envelope_json='{}', envelope_sha256='', state='deleted', deleted_at=? WHERE record_identity=?",
                             (now, identity))
                conn.execute("INSERT INTO annual_position_lifecycle_events (record_identity,user_id,event_kind,audit_reference,occurred_at) VALUES (?,?,?,?,?)",
                             (identity, authenticated_user_id, "erased", audit_reference, now))
            return len(rows)

    def execute_local_tax_data_erasure(self, *, authenticated_user_id: int, audit_reference: str,
                                       legal_hold_clearance: AccountErasureClearance,
                                       backup_expiry_clearance: AccountErasureClearance) -> LocalTaxDataErasureResult:
        """Physically delete local PAYE and annual-position rows after clearance.

        This is the bounded local-data portion of an account-erasure lifecycle.
        It deletes every structured PAYE row (including replaced or soft-removed
        rows) and every durable annual-position row owned by the authenticated
        user, plus their local evidence, audit, and lifecycle rows.  It does
        not delete the user identity, assert that other product stores are
        empty, or claim that backups have been erased; backup expiry remains an
        independently verified prerequisite.
        """
        self._audit(audit_reference)
        self._require_current_erasure_clearances(
            authenticated_user_id=authenticated_user_id,
            legal_hold_clearance=legal_hold_clearance,
            backup_expiry_clearance=backup_expiry_clearance,
        )
        with database._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._require_user(conn, authenticated_user_id)
            identities = tuple(row[0] for row in conn.execute(
                "SELECT record_identity FROM annual_position_records WHERE user_id=?",
                (authenticated_user_id,),
            ).fetchall())
            if identities:
                placeholders = ",".join("?" for _ in identities)
                conn.execute(
                    f"DELETE FROM annual_position_read_audit WHERE record_identity IN ({placeholders})",
                    identities,
                )
            # Lifecycle events may already have record_identity=NULL because
            # that FK uses ON DELETE SET NULL.  User ownership, not the
            # presently-readable record identity, is therefore the complete
            # erasure scope for this table.
            conn.execute(
                "DELETE FROM annual_position_lifecycle_events WHERE user_id=?",
                (authenticated_user_id,),
            )
            annual_count = conn.execute(
                "DELETE FROM annual_position_records WHERE user_id=?", (authenticated_user_id,)
            ).rowcount
            paye_count = conn.execute(
                "DELETE FROM paye_manual_entries WHERE user_id=?", (authenticated_user_id,)
            ).rowcount
            return LocalTaxDataErasureResult(
                annual_position_records=annual_count,
                paye_manual_entries=paye_count,
            )


__all__ = [
    "AccountErasureClearance",
    "ApprovedEvidenceReferencePolicy",
    "DurableAnnualPositionError",
    "DurableGovernance",
    "DurableAnnualPositionRepository",
    "ExternalAuthorityAdapter",
    "LocalTaxDataErasureResult",
    "MembershipAuthorityEvidence",
    "RECORD_PURPOSE",
]
