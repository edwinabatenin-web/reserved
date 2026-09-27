"""Disabled-first linked-HICBC composition over exact durable annual sources.

This service has no route or feature switch and cannot activate linked HICBC.
It derives the partner only from a unique current same-year link, asks a trusted
producer for that derived participant's live annual source, and releases only
the authenticated user's bounded HICBC result.  The final calculation is held
inside the same SQLite transaction that rechecks the link, permission cycle,
current notice-version consents, memberships and both durable source heads.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from typing import Callable

from reserved import database
from reserved.annual_position_durable_repository import (
    DurableAnnualPositionError,
    DurableAnnualPositionRepository,
    RECORD_PURPOSE,
)
from reserved.annual_position_repository_contract import (
    RepositoryContractError,
    decode_annual_position_record,
    project_annual_position_record,
)
from reserved.engines.annual_to_cash_integration import (
    AnnualToCashPosition,
    AnnualToCashStatus,
    annual_to_cash_position_identity,
)
from reserved.engines.cash_ready_annual_position import annual_position_identity
from reserved.engines.hicbc_integration import PERSONALISED_ESTIMATE, integrate_hicbc
from reserved.engines.hicbc_partner import ANI_COMPONENT_WHOLE, PartnerEvidence
from reserved.engines.integrated_annual_position import (
    AnnualPositionResult,
    annual_position_geography,
)
from reserved.hicbc_durable_annual_bridge import (
    DurableHicbcAnnualPreview,
    _assert_exact_durable_customer_composition,
    _current_owner,
    _is_fresh,
    _unavailable,
)
from reserved.web.hicbc import (
    _partner_evidence_from_row,
    _responsibility_from_sources,
)


@dataclass(frozen=True, slots=True)
class LinkedAnnualLiveSource:
    """Exact producer objects; participant and business are derived elsewhere."""

    annual_position: AnnualToCashPosition
    annual_tax_position: AnnualPositionResult


@dataclass(frozen=True, slots=True)
class _LinkedScope:
    link_id: int
    permission_cycle: int
    owner_id: int
    partner_id: int
    owner_business: str
    partner_business: str
    owner_record_identity: str
    partner_record_identity: str


def _server_date() -> date:
    return date.today()


def _tuplify(value):
    if isinstance(value, list):
        return tuple(_tuplify(item) for item in value)
    return value


def _project_record(repository: DurableAnnualPositionRepository, stored) -> dict:
    raw = stored["envelope_json"]
    if (type(raw) is not str
            or hashlib.sha256(raw.encode("ascii")).hexdigest() != stored["envelope_sha256"]
            or stored["governance_fingerprint"] != repository._governance.fingerprint):
        raise ValueError("durable annual source integrity is unavailable")
    try:
        record = decode_annual_position_record(
            _tuplify(json.loads(raw)), repository._contract_governance,
            "audit:linked-hicbc-contract-read",
        )
        return dict(project_annual_position_record(record)[2])
    except (UnicodeError, ValueError, TypeError, RepositoryContractError) as exc:
        raise ValueError("durable annual source integrity is unavailable") from exc


def _one_current_record(conn, *, user_id: int, tax_year: str, nation: str):
    rows = conn.execute(
        "SELECT * FROM annual_position_records WHERE user_id=? AND tax_year=? "
        "AND nation=? AND record_purpose=? AND state='current'",
        (user_id, tax_year, nation, RECORD_PURPOSE),
    ).fetchall()
    return rows[0] if len(rows) == 1 else None


def _capture_scope(
    conn,
    *,
    repository: DurableAnnualPositionRepository,
    owner_id: int,
    owner_business: str,
    tax_year: str,
    nation: str,
) -> tuple[_LinkedScope, dict, dict, dict] | None:
    links = conn.execute(
        "SELECT * FROM hicbc_links WHERE (user_low_id=? OR user_high_id=?) "
        "AND tax_year=? AND status='active'",
        (owner_id, owner_id, tax_year),
    ).fetchall()
    if len(links) != 1:
        return None
    link = links[0]
    participants = {link["user_low_id"], link["user_high_id"]}
    if owner_id not in participants or len(participants) != 2:
        return None
    partner_id = next(iter(participants - {owner_id}))
    consents = conn.execute(
        "SELECT user_id,notice_version FROM hicbc_link_consents "
        "WHERE link_id=? AND withdrawn_at IS NULL",
        (link["id"],),
    ).fetchall()
    if ({row["user_id"] for row in consents} != participants
            or len(consents) != 2
            or any(row["notice_version"] != database.HICBC_NOTICE_VERSION for row in consents)):
        return None
    cycle = link["permission_cycle"]
    if type(cycle) is not int or cycle <= 0:
        return None

    owner_record = _one_current_record(
        conn, user_id=owner_id, tax_year=tax_year, nation=nation,
    )
    partner_record = _one_current_record(
        conn, user_id=partner_id, tax_year=tax_year, nation=nation,
    )
    if (owner_record is None or partner_record is None
            or owner_record["business_reference"] != owner_business):
        return None
    try:
        repository._active_membership(conn, owner_id, owner_business)
        repository._active_membership(
            conn, partner_id, partner_record["business_reference"],
        )
    except DurableAnnualPositionError:
        return None
    facts = conn.execute(
        "SELECT * FROM hicbc_estimates WHERE user_id=? AND tax_year=?",
        (owner_id, tax_year),
    ).fetchall()
    if len(facts) != 1:
        return None
    scope = _LinkedScope(
        link_id=link["id"],
        permission_cycle=cycle,
        owner_id=owner_id,
        partner_id=partner_id,
        owner_business=owner_business,
        partner_business=partner_record["business_reference"],
        owner_record_identity=owner_record["record_identity"],
        partner_record_identity=partner_record["record_identity"],
    )
    return scope, dict(owner_record), dict(partner_record), dict(facts[0])


def _validate_source(
    *,
    source: LinkedAnnualLiveSource,
    durable_row: dict,
    owner_id: int,
    business_reference: str,
    tax_year: str,
    nation: str,
    as_of: date,
) -> bool:
    if (type(source) is not LinkedAnnualLiveSource
            or type(source.annual_position) is not AnnualToCashPosition
            or type(source.annual_tax_position) is not AnnualPositionResult):
        raise TypeError("exact linked annual source is required")
    annual = source.annual_position
    tax = source.annual_tax_position
    if (annual.tax_year != tax_year or annual.nation != nation
            or tax.tax_year != tax_year or annual_position_geography(tax) != nation
            or annual.considered_annual_position.annual_tax_reference
            != annual_position_identity(tax)):
        return False
    if (durable_row.get("user_id") != str(owner_id)
            or durable_row.get("business_id") != business_reference
            or durable_row.get("tax_year") != tax_year
            or durable_row.get("nation") != nation
            or durable_row.get("annual_cash_identity")
            != annual_to_cash_position_identity(annual)):
        return False
    try:
        _assert_exact_durable_customer_composition(
            annual_position=annual,
            durable_row=durable_row,
            owner=owner_id,
            business_reference=business_reference,
        )
        stored_as_of = date.fromisoformat(durable_row["as_of"])
        stale_after_days = durable_row["stale_after_days"]
    except (KeyError, TypeError, ValueError):
        return False
    return (
        annual.status is AnnualToCashStatus.QUALIFIED_LOCAL_RESULT
        and tax.calculation_status == "calculated"
        and _is_fresh(
            annual_as_of=annual.as_of,
            stored_as_of=stored_as_of,
            stale_after_days=stale_after_days,
            now=as_of,
        )
    )


def _manual_partner_fact_conflicts(row: dict, partner_ani: Decimal) -> bool:
    """A retained manual assertion may corroborate, but never replace, linked ANI."""
    try:
        manual = _partner_evidence_from_row(row)
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return True
    if manual is None:
        return False
    if manual.has_material_uncertainty:
        return True
    low = manual.low if manual.is_range else manual.point
    high = manual.high if manual.is_range else manual.point
    return low is None or high is None or not (low <= partner_ani <= high)


def _linked_only_row(row: dict) -> dict:
    value = dict(row)
    value.update({
        "representation": None,
        "partner_ani_point": None,
        "partner_ani_low": None,
        "partner_ani_high": None,
    })
    return value


def compose_linked_durable_authenticated_hicbc_preview(
    *,
    repository: DurableAnnualPositionRepository,
    owner_source: LinkedAnnualLiveSource,
    partner_source_provider: Callable[[int, str, str], LinkedAnnualLiveSource],
    owner_business_reference: str,
    tax_year: str,
    nation: str,
) -> DurableHicbcAnnualPreview:
    """Return only the signed-in user's own linked-source HICBC consequence.

    There is deliberately no partner identifier or source selector in this
    interface.  Missing, stale, conflicting or concurrently changed authority
    returns the same fixed insufficient-facts result.
    """
    if type(repository) is not DurableAnnualPositionRepository:
        raise TypeError("exact durable annual-position repository is required")
    if not callable(partner_source_provider):
        raise TypeError("trusted linked annual source provider is required")
    if (type(owner_business_reference) is not str or not owner_business_reference
            or type(tax_year) is not str or type(nation) is not str):
        raise ValueError("linked HICBC scope is invalid")
    owner_id = _current_owner()
    try:
        repository.assert_external_authority_available()
        initial_date = _server_date()
    except Exception as exc:
        raise ValueError("linked HICBC authority is unavailable") from exc
    if type(initial_date) is not date:
        raise ValueError("trusted linked HICBC server clock is invalid")

    with database._connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        captured = _capture_scope(
            conn,
            repository=repository,
            owner_id=owner_id,
            owner_business=owner_business_reference,
            tax_year=tax_year,
            nation=nation,
        )
    if captured is None:
        return _unavailable(tax_year)
    initial_scope = captured[0]
    partner_source = partner_source_provider(initial_scope.partner_id, tax_year, nation)

    try:
        final_date = _server_date()
    except Exception as exc:
        raise ValueError("trusted linked HICBC server clock is unavailable") from exc
    if type(final_date) is not date:
        raise ValueError("trusted linked HICBC server clock is invalid")

    with database._connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        captured = _capture_scope(
            conn,
            repository=repository,
            owner_id=owner_id,
            owner_business=owner_business_reference,
            tax_year=tax_year,
            nation=nation,
        )
        if captured is None or captured[0] != initial_scope:
            return _unavailable(tax_year)
        scope, owner_stored, partner_stored, owner_facts = captured
        owner_durable = _project_record(repository, owner_stored)
        partner_durable = _project_record(repository, partner_stored)
        if (not _validate_source(
                source=owner_source,
                durable_row=owner_durable,
                owner_id=scope.owner_id,
                business_reference=scope.owner_business,
                tax_year=tax_year,
                nation=nation,
                as_of=final_date,
            ) or not _validate_source(
                source=partner_source,
                durable_row=partner_durable,
                owner_id=scope.partner_id,
                business_reference=scope.partner_business,
                tax_year=tax_year,
                nation=nation,
                as_of=final_date,
            )):
            return _unavailable(tax_year)

        partner_ani = partner_source.annual_tax_position.adjusted_net_income
        if _manual_partner_fact_conflicts(owner_facts, partner_ani):
            return _unavailable(tax_year)
        linked_evidence = PartnerEvidence(
            evidence_id=f"linked-annual-{scope.link_id}-{scope.permission_cycle}",
            source_kind="linked_partner_source",
            source_reference=f"linked-annual:{scope.link_id}:{scope.permission_cycle}",
            subject_reference="linked_partner",
            tax_year=tax_year,
            representation="point",
            point=partner_ani,
            low=None,
            high=None,
            effective_period=tax_year,
            observed_at=partner_source.annual_position.as_of.isoformat(),
            confirmed_at=partner_source.annual_position.as_of.isoformat(),
            completeness="complete_for_purpose",
            recency_state="current",
            consent_state="consented",
            ani_components=(ANI_COMPONENT_WHOLE,),
        )
        built = _responsibility_from_sources(
            owner_source.annual_tax_position.adjusted_net_income,
            _linked_only_row(owner_facts),
            linked_evidence,
            tax_year,
        )
        contribution = integrate_hicbc(built["result"], PERSONALISED_ESTIMATE)
        if not contribution.included:
            return _unavailable(tax_year)
        # "partner_liable" is an engine fact, not a customer-safe linked
        # output.  The receiving user's consequence is simply no own charge.
        public_responsibility = built["result"].responsibility_status
        if public_responsibility == "partner_liable":
            public_responsibility = "no_charge"
        return DurableHicbcAnnualPreview(
            tax_year=tax_year,
            calculation_status=built["result"].calculation_status,
            responsibility_status=public_responsibility,
            projected_user_hicbc=contribution.charge,
            possible_charge_low=contribution.charge_low,
            possible_charge_high=contribution.charge_high,
        )
