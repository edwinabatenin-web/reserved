"""Disabled-first trusted annual source for the bounded HICBC integration.

This is an application service, not an HTTP route or activation switch.  It
accepts no caller-supplied owner: the signed session supplies the only owner
identity.  A live annual producer result must be tied to the exact current
durable annual-to-cash projection before its ANI can be considered.

Linked-account facts are deliberately not composed here.  An active link
suppresses the result rather than reading partner data through a second,
separately-transactional path.  That gives link revocation a clear SQLite
``BEGIN IMMEDIATE`` linearization point and preserves the existing preview's
anti-probing rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from reserved import database
from reserved.annual_position_durable_repository import (
    DurableAnnualPositionError,
    DurableAnnualPositionRepository,
    RECORD_PURPOSE,
)
from reserved.annual_position_repository_contract import project_annual_position_record
from reserved.billing.event_inbox_contract import canonical_owner_id_from_users_id
from reserved.engines.annual_to_cash_integration import (
    AnnualToCashPosition, AnnualToCashStatus,
    annual_to_cash_position_identity,
)
from reserved.engines.cash_ready_annual_position import annual_position_identity
from reserved.engines.integrated_annual_position import (
    AnnualPositionResult,
    annual_position_geography,
)
from reserved.engines.hicbc_integration import PERSONALISED_ESTIMATE, integrate_hicbc
from reserved.web.hicbc import _responsibility_from_sources


@dataclass(frozen=True)
class DurableHicbcAnnualPreview:
    """Minimal result; never a payment, refund, reserve or source receipt."""

    tax_year: str
    calculation_status: str
    responsibility_status: str | None
    projected_user_hicbc: Decimal | None
    possible_charge_low: Decimal | None
    possible_charge_high: Decimal | None

    def public_value(self) -> dict[str, str | None]:
        """Return the deliberately minimal customer-safe projection."""
        return {
            "tax_year": self.tax_year,
            "calculation_status": self.calculation_status,
            "responsibility_status": self.responsibility_status,
            "projected_user_hicbc": (
                None if self.projected_user_hicbc is None else f"{self.projected_user_hicbc:.2f}"
            ),
            "possible_charge_low": (
                None if self.possible_charge_low is None else f"{self.possible_charge_low:.2f}"
            ),
            "possible_charge_high": (
                None if self.possible_charge_high is None else f"{self.possible_charge_high:.2f}"
            ),
        }


def _unavailable(tax_year: str) -> DurableHicbcAnnualPreview:
    return DurableHicbcAnnualPreview(
        tax_year=tax_year,
        calculation_status="insufficient_facts",
        responsibility_status=None,
        projected_user_hicbc=None,
        possible_charge_low=None,
        possible_charge_high=None,
    )


def _current_owner() -> int:
    from reserved.auth import current_user_id

    try:
        owner = current_user_id()
    except RuntimeError:
        raise ValueError("authenticated HICBC composition context is required") from None
    if type(owner) is not int or owner <= 0:
        raise ValueError("authenticated HICBC composition owner is invalid")
    return owner


def _atomic_hicbc_row(*, repository: DurableAnnualPositionRepository, owner: int,
                      business_reference: str, tax_year: str,
                      durable_record_identity: str, _after_read=None) -> tuple[dict | None, bool]:
    """Capture final authority + HICBC state in one SQLite write transaction.

    The transaction commit is the result's linearization point.  A revoke or
    membership change committed before it is observed here; one initiated after
    it applies only to subsequent compositions.
    """
    with database._connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            repository.assert_external_authority_available()
            repository._active_membership(conn, owner, business_reference)
        except DurableAnnualPositionError as exc:
            raise ValueError("current durable membership is unavailable") from exc
        record = conn.execute(
            "SELECT 1 FROM annual_position_records WHERE record_identity=? "
            "AND user_id=? AND business_reference=? AND state='current'",
            (durable_record_identity, owner, business_reference),
        ).fetchone()
        if record is None:
            raise ValueError("current durable annual record is unavailable")
        row = conn.execute(
            "SELECT * FROM hicbc_estimates WHERE user_id=? AND tax_year=?",
            (owner, tax_year),
        ).fetchone()
        active_link = conn.execute(
            "SELECT 1 FROM hicbc_links WHERE (user_low_id=? OR user_high_id=?) "
            "AND tax_year=? AND status='active'",
            (owner, owner, tax_year),
        ).fetchone() is not None
        if _after_read is not None:
            _after_read()
        return (None if row is None else dict(row)), active_link


def compose_durable_authenticated_hicbc_preview(
    *,
    repository: DurableAnnualPositionRepository,
    annual_position: AnnualToCashPosition,
    annual_tax_position: AnnualPositionResult,
    business_reference: str,
    tax_year: str,
    nation: str,
    as_of: date,
    audit_reference: str,
) -> DurableHicbcAnnualPreview:
    """Compose a minimal HICBC estimate from an exact durable/live annual pair.

    No caller can choose another owner or bypass a current externally-verified
    durable membership.  Any incomplete annual result, uncertain HICBC source,
    inactive durable record, or active linked account produces no actionable
    amount.  This function has no payment, refund, reserve, filing or route
    authority.
    """
    if type(repository) is not DurableAnnualPositionRepository:
        raise TypeError("exact durable annual-position repository is required")
    if type(annual_position) is not AnnualToCashPosition:
        raise TypeError("annual cash input must be an exact annual-to-cash position")
    if type(annual_tax_position) is not AnnualPositionResult:
        raise TypeError("annual tax input must be an exact annual producer result")
    if (type(business_reference) is not str or type(tax_year) is not str or type(nation) is not str
            or type(as_of) is not date):
        raise ValueError("durable HICBC scope is invalid")
    owner = _current_owner()
    if (annual_position.tax_year != tax_year or annual_position.nation != nation
            or annual_tax_position.tax_year != tax_year
            or annual_position_geography(annual_tax_position) != nation):
        raise ValueError("live annual source does not match requested durable scope")
    if (annual_position.considered_annual_position.annual_tax_reference
            != annual_position_identity(annual_tax_position)):
        raise ValueError("live annual tax source does not match annual-to-cash identity")

    try:
        repository.assert_external_authority_available()
        durable_record = repository.read_current(
            authenticated_user_id=owner,
            business_reference=business_reference,
            tax_year=tax_year,
            nation=nation,
            record_purpose=RECORD_PURPOSE,
            audit_reference=audit_reference,
        )
        durable_row = dict(project_annual_position_record(durable_record)[2])
    except (DurableAnnualPositionError, ValueError) as exc:
        raise ValueError("current durable annual position is unavailable") from exc

    annual_identity = annual_to_cash_position_identity(annual_position)
    if (durable_row.get("user_id") != canonical_owner_id_from_users_id(owner)
            or durable_row.get("business_id") != business_reference
            or durable_row.get("tax_year") != tax_year
            or durable_row.get("nation") != nation
            or durable_row.get("annual_cash_identity") != annual_identity):
        raise ValueError("durable annual position does not bind this HICBC composition")

    stored_as_of = durable_row.get("as_of")
    try:
        if type(stored_as_of) is str:
            stored_as_of = date.fromisoformat(stored_as_of)
        stale_after_days = durable_row["stale_after_days"]
    except (KeyError, TypeError, ValueError):
        return _unavailable(tax_year)
    if (type(stored_as_of) is not date or type(stale_after_days) is not int
            or stale_after_days < 0
            or annual_position.status is not AnnualToCashStatus.QUALIFIED_LOCAL_RESULT
            or annual_position.as_of != stored_as_of
            or as_of < annual_position.as_of
            or as_of > annual_position.as_of + timedelta(days=stale_after_days)):
        return _unavailable(tax_year)

    # The final transaction ties a still-current durable record, membership and
    # link state to the source row immediately before the result is returned.
    row, active_link = _atomic_hicbc_row(
        repository=repository,
        owner=owner,
        business_reference=business_reference,
        tax_year=tax_year,
        durable_record_identity=durable_row["record_identity"],
    )
    if active_link or annual_tax_position.calculation_status != "calculated":
        return _unavailable(tax_year)

    built = _responsibility_from_sources(
        annual_tax_position.adjusted_net_income, row, None, tax_year,
    )
    result = built["result"]
    contribution = integrate_hicbc(result, PERSONALISED_ESTIMATE)
    if not contribution.included:
        return _unavailable(tax_year)
    return DurableHicbcAnnualPreview(
        tax_year=tax_year,
        calculation_status=result.calculation_status,
        responsibility_status=result.responsibility_status,
        projected_user_hicbc=contribution.charge,
        possible_charge_low=contribution.charge_low,
        possible_charge_high=contribution.charge_high,
    )
