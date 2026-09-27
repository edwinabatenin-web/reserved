"""Application-integration bridge from owner-bound PAYE facts to annual composition.

This bridge does not discover an owner, business, annual position, policy or
future-pay fact. Callers must supply each already-admitted dependency. It only
composes facts after proving that the current membership decision, persisted
annual projection and live annual-to-cash result describe the same owner,
business and tax year.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import weakref

from reserved.annual_position_persistence_contract import AnnualPositionPersistenceProjection
from reserved.billing.event_inbox_contract import canonical_owner_id_from_users_id
from reserved.engines.annual_to_cash_integration import (
    AnnualToCashPosition, annual_to_cash_position_identity,
)
from reserved.engines.paye_reconciliation import (
    Completeness, EvidenceKind, EvidenceRepresentation, PayeEvidence,
    PayeReconciliationPolicy, reconcile_paye,
)
from reserved.owner_business_membership_contract import (
    OwnerBusinessMembershipDecision, assert_allowed_membership_decision_current,
    validate_owner_business_membership_decision,
)
from reserved.services.paye_future_pay_forecast import (
    ConfirmedFuturePayFact, FuturePayForecastPolicy, PayeFuturePayForecast,
    compose_paye_future_pay_forecast,
)


@dataclass(frozen=True)
class AuthenticatedPayeAnnualBridge:
    """A qualified composition, never a payment, refund or activation authority."""

    annual_cash_identity: str
    membership_identity: str
    reconciliation: object
    future_pay_forecast: PayeFuturePayForecast | None


class OwnerBoundPayeEvidenceBatch:
    """Opaque snapshot issued only by the owner-scoped persistence reader."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *args, **kwargs):
        raise TypeError("PAYE evidence batches are repository-issued only")


_BATCHES: dict[int, tuple[weakref.ReferenceType, int, str, tuple[dict, ...]]] = {}


def read_owner_bound_manual_paye_evidence(
    *, authenticated_owner_user_id: int, tax_year: str
) -> OwnerBoundPayeEvidenceBatch:
    """Read current rows for one exact owner/year and issue an opaque snapshot."""
    from reserved import database
    from reserved.auth import current_user_id

    if (type(authenticated_owner_user_id) is not int or authenticated_owner_user_id <= 0
            or type(tax_year) is not str or len(tax_year) != 7 or tax_year[4] != "/"):
        raise ValueError("PAYE evidence owner/year is invalid")
    try:
        session_owner = current_user_id()
    except RuntimeError:
        raise ValueError("authenticated PAYE request context is required") from None
    if type(session_owner) is not int or session_owner != authenticated_owner_user_id:
        raise ValueError("PAYE evidence read is not bound to authenticated owner")
    rows = database.list_active_paye_manual_entries(authenticated_owner_user_id, tax_year)
    seen_slots: set[int] = set()
    seen_ids: set[str] = set()
    snapshot = []
    for row in rows:
        if type(row) is not dict or row.get("user_id") != authenticated_owner_user_id:
            raise ValueError("PAYE repository returned cross-owner evidence")
        slot, evidence_id = row.get("employment_slot"), row.get("evidence_id")
        if slot in seen_slots or evidence_id in seen_ids:
            raise ValueError("PAYE repository returned duplicate evidence")
        seen_slots.add(slot)
        seen_ids.add(evidence_id)
        snapshot.append(dict(row))
    batch = object.__new__(OwnerBoundPayeEvidenceBatch)
    key = id(batch)

    def discard(_):
        _BATCHES.pop(key, None)

    _BATCHES[key] = (weakref.ref(batch, discard), authenticated_owner_user_id, tax_year, tuple(snapshot))
    return batch


def _batch_rows(
    batch: OwnerBoundPayeEvidenceBatch, *, authenticated_owner_user_id: int, tax_year: str
) -> list[dict]:
    if type(batch) is not OwnerBoundPayeEvidenceBatch:
        raise TypeError("PAYE evidence must be an owner-bound repository batch")
    binding = _BATCHES.get(id(batch))
    if (binding is None or binding[0]() is not batch or binding[1] != authenticated_owner_user_id
            or binding[2] != tax_year):
        raise ValueError("PAYE evidence batch is not bound to authenticated owner/year")
    return [dict(row) for row in binding[3]]


def _engine_tax_year(value: str) -> str:
    if type(value) is not str or len(value) != 7 or value[4] != "/":
        raise ValueError("annual input tax year is invalid")
    return value[:4] + "-" + value[5:]


def _manual_evidence(
    entries: list[dict], *, engine_tax_year: str, authenticated_owner_user_id: int
) -> tuple[PayeEvidence, ...]:
    evidence = []
    seen_slots: set[int] = set()
    seen_evidence_ids: set[str] = set()
    for row in entries:
        if type(row) is not dict or row.get("tax_year") != engine_tax_year.replace("-", "/"):
            raise ValueError("PAYE evidence tax year is not bound to annual input")
        if type(row.get("user_id")) is not int or row["user_id"] != authenticated_owner_user_id:
            raise ValueError("PAYE evidence owner is not bound to authenticated membership")
        if row.get("source_kind") != "customer_confirmed_manual" or row.get("completeness") != "partial":
            raise ValueError("PAYE evidence provenance is not admitted")
        slot = row.get("employment_slot")
        if type(slot) is not int or not 1 <= slot <= 20:
            raise ValueError("PAYE employment scope is invalid")
        evidence_id = row.get("evidence_id")
        if slot in seen_slots or evidence_id in seen_evidence_ids:
            raise ValueError("PAYE employment evidence is duplicated")
        seen_slots.add(slot)
        seen_evidence_ids.add(evidence_id)
        evidence.append(PayeEvidence(
            kind=EvidenceKind.MANUAL,
            tax_year=engine_tax_year,
            tax_paid_to_date=row.get("tax_paid_to_date"),
            gross_pay_to_date=row.get("gross_to_date"),
            employment_id=f"manual-employment-{slot}",
            tax_code=row.get("tax_code"),
            observed_on=date.fromisoformat(row["observed_on"]),
            effective_through=date.fromisoformat(row["effective_through"]),
            evidence_id=evidence_id,
            source_reference=row["provenance"],
            representation=EvidenceRepresentation.EMPLOYMENT_CUMULATIVE,
            completeness=Completeness.PARTIAL,
        ))
    return tuple(evidence)


def compose_authenticated_manual_paye(
    *,
    evidence_batch: OwnerBoundPayeEvidenceBatch,
    annual_position: AnnualToCashPosition,
    annual_projection: AnnualPositionPersistenceProjection,
    membership_decision: OwnerBusinessMembershipDecision,
    current_membership_snapshot: object,
    reconciliation_policy: PayeReconciliationPolicy,
    future_pay_facts: tuple[ConfirmedFuturePayFact, ...] = (),
    future_pay_policy: FuturePayForecastPolicy | None = None,
) -> AuthenticatedPayeAnnualBridge:
    """Compose only exact, current and mutually bound annual/PAYE inputs.

    Any absent annual liability, stale/revoked membership, cross-owner business
    substitution, mismatched annual identity, foreign tax year or unconfirmed
    future fact raises. No fallback point result is made.
    """
    if type(annual_position) is not AnnualToCashPosition:
        raise TypeError("annual input must be an exact annual-to-cash position")
    if type(annual_projection) is not AnnualPositionPersistenceProjection:
        raise TypeError("annual projection must be an exact admitted projection")
    validate_owner_business_membership_decision(membership_decision)
    from reserved.auth import current_user_id
    try:
        session_owner = current_user_id()
    except RuntimeError:
        raise ValueError("authenticated PAYE composition context is required") from None
    if (type(session_owner) is not int
            or session_owner != membership_decision.authenticated_owner_users_id):
        raise ValueError("PAYE composition is not bound to current authenticated owner")
    assert_allowed_membership_decision_current(
        decision=membership_decision, membership_fake=current_membership_snapshot
    )
    if membership_decision.allowed is not True:
        raise ValueError("membership is not allowed")
    if not annual_projection.annual_cash_identity_admitted:
        raise ValueError("annual projection is not admitted")
    annual_identity = annual_to_cash_position_identity(annual_position)
    if annual_projection.annual_cash_identity != annual_identity:
        raise ValueError("annual input does not match admitted projection")
    if membership_decision.authenticated_owner_users_id != int(annual_projection.user_id):
        raise ValueError("membership owner does not match annual projection")
    if membership_decision.business_reference != annual_projection.business_id:
        raise ValueError("membership business does not match annual projection")
    if annual_position.tax_year != annual_projection.tax_year:
        raise ValueError("annual position tax year does not match projection")
    if type(annual_position.as_of) is not date or type(annual_position.final_self_assessment_liability) is not Decimal:
        raise ValueError("annual input does not provide an exact liability")
    engine_tax_year = _engine_tax_year(annual_position.tax_year)
    entries = _batch_rows(
        evidence_batch,
        authenticated_owner_user_id=membership_decision.authenticated_owner_users_id,
        tax_year=annual_position.tax_year,
    )
    reconciliation = reconcile_paye(
        annual_position.final_self_assessment_liability,
        _manual_evidence(
            entries,
            engine_tax_year=engine_tax_year,
            authenticated_owner_user_id=membership_decision.authenticated_owner_users_id,
        ),
        tax_year=engine_tax_year,
        as_of=annual_position.as_of,
        policy=reconciliation_policy,
    )
    if type(future_pay_facts) is not tuple:
        raise TypeError("future PAYE facts must be an exact tuple")
    future = None
    if future_pay_facts:
        if future_pay_policy is None:
            raise ValueError("future PAYE facts require an exact policy")
        owner = canonical_owner_id_from_users_id(membership_decision.authenticated_owner_users_id)
        future = compose_paye_future_pay_forecast(
            reconciliation, future_pay_facts, owner_id=owner,
            business_id=membership_decision.business_reference,
            tax_year=engine_tax_year, as_of=annual_position.as_of,
            policy=future_pay_policy,
        )
    return AuthenticatedPayeAnnualBridge(
        annual_cash_identity=annual_identity,
        membership_identity=membership_decision.decision_identity,
        reconciliation=reconciliation,
        future_pay_forecast=future,
    )
