"""Post-v1 HICBC partner-estimate manual path.

This blueprint is a bounded, clearly-labelled post-v1 preview.  It is **not**
part of the October v1 customer tax total, reserve/set-aside guidance, payment
initiation, filing or launch claim, and it does not alter the Personal Allowance
Explore-your-options result.

Privacy boundary
----------------
The partner's raw ANI, income band, range operands and calculated personal tax
are never rendered into customer-facing payloads, templates, logs, analytics or
notifications.  The internal :class:`PartnerEvidence` holds the raw figure only
to perform the comparison; the customer view exposes responsibility/uncertainty
and neutral household messaging only.
"""

from __future__ import annotations

import hashlib
import logging
from decimal import Decimal, InvalidOperation

from flask import Blueprint, g, jsonify, redirect, render_template, request, session, url_for

from reserved.auth import require_auth
from reserved.database import (
    accept_hicbc_link_invitation,
    create_hicbc_link_invitation,
    delete_hicbc_estimate,
    get_active_hicbc_link,
    get_hicbc_estimate,
    get_hicbc_link_partner_id,
    get_profile_by_user,
    revoke_hicbc_link,
    save_hicbc_estimate,
)
from reserved.engines.hicbc_partner import (
    HOUSEHOLD_CHANGED,
    HOUSEHOLD_MOVED_TO_PARTNER,
    HOUSEHOLD_MOVED_TO_PERSON,
    SOURCE_LINKED_PARTNER,
    PartnerEvidence,
    annual_child_benefit_amount,
    customer_view,
    determine_hicbc_responsibility,
    household_change_status,
)
from reserved.engines.optimise import _resolve_annual_income, _resolve_pension
from reserved.tax_year_context import configured_tax_year, resolve_tax_year

log = logging.getLogger(__name__)

hicbc = Blueprint("hicbc", __name__, url_prefix="/v2/hicbc")

_SOURCE_KIND = "user_supplied_partner_estimate"
_MERGED_SOURCE_KIND = "multiple_partner_sources"

# Server-side session key holding a one-shot household responsibility transition.
_TRANSITION_SESSION_KEY = "_hicbc_responsibility_transition"

# Transitions that are surfaced to the customer as a neutral change notification.
_SURFACED_TRANSITIONS = frozenset({
    HOUSEHOLD_CHANGED,
    HOUSEHOLD_MOVED_TO_PARTNER,
    HOUSEHOLD_MOVED_TO_PERSON,
})


def _user_ani_from_profile(profile: dict) -> Decimal:
    """Derive the user's projected adjusted net income from their profile."""
    income = _resolve_annual_income(profile)
    pension = _resolve_pension(profile)
    return max(Decimal("0"), income - pension)


def _tri(raw) -> int | None:
    """Map a form/JSON tri-state to None/0/1."""
    if raw is None:
        return None
    text = str(raw).strip().lower()
    if text in ("", "none", "null", "unknown"):
        return None
    if text in ("yes", "true", "1", "y"):
        return 1
    if text in ("no", "false", "0", "n"):
        return 0
    return None


def _decimal(raw, name: str, *, allow_zero: bool = True) -> Decimal | None:
    if raw is None or str(raw).strip() == "":
        return None
    if isinstance(raw, bool):
        raise ValueError(f"{name} must be numeric, not boolean")
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{name} must be numeric") from None
    if not value.is_finite() or value < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    if not allow_zero and value == 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _partner_evidence_from_row(row: dict) -> PartnerEvidence | None:
    """Build a :class:`PartnerEvidence` from a persisted estimate row."""
    representation = row.get("representation")
    if representation not in ("point", "range"):
        return None
    tax_year = row["tax_year"]
    common = dict(
        evidence_id=row["evidence_id"],
        source_kind=row.get("source_kind") or _SOURCE_KIND,
        source_reference=row["evidence_id"],
        subject_reference="partner",
        tax_year=tax_year,
        effective_period=tax_year,
        observed_at=row["observed_at"],
        confirmed_at=row.get("confirmed_at"),
        completeness=row.get("completeness") or "complete_for_purpose",
        recency_state=row.get("recency_state") or "current",
        consent_state="not_required",
    )
    if representation == "point":
        point = _decimal(row.get("partner_ani_point"), "partner_ani_point")
        if point is None:
            return None
        return PartnerEvidence(representation="point", point=point, low=None, high=None, **common)
    low = _decimal(row.get("partner_ani_low"), "partner_ani_low")
    high = _decimal(row.get("partner_ani_high"), "partner_ani_high")
    if low is None or high is None:
        return None
    return PartnerEvidence(representation="range", point=None, low=low, high=high, **common)


def _child_benefit_amount_from_row(row: dict | None, tax_year: str) -> Decimal | None:
    if row is None:
        return None
    receives = row.get("receives_child_benefit")
    if receives == 0:
        return Decimal("0")
    if receives != 1:
        return None
    annual_override = row.get("child_benefit_annual")
    children = int(row.get("child_benefit_children") or 0)
    return annual_child_benefit_amount(
        children=children, annual_override=annual_override, tax_year=tax_year,
    )


def _opaque_subject_reference(partner_id: int) -> str:
    """Return an opaque, stable reference that does not expose the raw user id."""
    digest = hashlib.sha256(str(partner_id).encode("utf-8")).hexdigest()[:16]
    return f"linked_partner:{digest}"


def _linked_partner_evidence(user_id: int, tax_year: str) -> PartnerEvidence | None:
    """Return privacy-minimised linked partner evidence for an active link.

    Reads the linked partner's own ANI only for the internal responsibility
    comparison, under an active, mutually consented, HICBC-only link.  The raw
    value is held inside :class:`PartnerEvidence` and never reaches a customer
    payload (``customer_view`` strips it).
    """
    partner_id = get_hicbc_link_partner_id(user_id, tax_year)
    if partner_id is None:
        return None
    partner_profile = get_profile_by_user(partner_id) or {}
    partner_ani = _user_ani_from_profile(partner_profile)
    link = get_active_hicbc_link(user_id, tax_year)
    link_id = link["id"] if link else 0
    now = _now_iso()
    return PartnerEvidence(
        evidence_id=f"linked_{link_id}_{tax_year.replace('/', '-')}",
        source_kind=SOURCE_LINKED_PARTNER,
        source_reference=f"link:{link_id}",
        subject_reference=_opaque_subject_reference(partner_id),
        tax_year=tax_year,
        representation="point",
        point=partner_ani,
        low=None,
        high=None,
        effective_period=tax_year,
        observed_at=now,
        confirmed_at=None,
        completeness="complete_for_purpose",
        recency_state="current",
        consent_state="consented",
    )


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _evidence_bounds(evidence: PartnerEvidence) -> tuple[Decimal, Decimal]:
    if evidence.is_range:
        return evidence.low, evidence.high
    return evidence.point, evidence.point


def _merge_partner_evidence(
    manual: PartnerEvidence, linked: PartnerEvidence
) -> tuple[PartnerEvidence, bool]:
    """Merge manual and linked partner evidence into one comparison operand.

    Neither source has precedence.  The two are merged into a range spanning both
    (or a point when they agree exactly); ``conflict`` is True only when the two
    sources do not overlap, so the caller can record the disagreement.
    """
    mlow, mhigh = _evidence_bounds(manual)
    llow, lhigh = _evidence_bounds(linked)
    conflict = (mhigh < llow) or (lhigh < mhigh)
    low = min(mlow, llow)
    high = max(mhigh, lhigh)
    tax_year = manual.tax_year
    now = _now_iso()
    common = dict(
        evidence_id=f"merged_{manual.evidence_id[:8]}_{linked.evidence_id[:8]}",
        source_kind=_MERGED_SOURCE_KIND,
        source_reference=f"merged:{manual.evidence_id}:{linked.evidence_id}",
        subject_reference="partner",
        tax_year=tax_year,
        effective_period=tax_year,
        observed_at=now,
        confirmed_at=None,
        completeness="partial",
        recency_state="current",
        consent_state="consented",
    )
    if low == high:
        return PartnerEvidence(representation="point", point=low, low=None, high=None, **common), conflict
    return PartnerEvidence(representation="range", point=None, low=low, high=high, **common), conflict


def build_responsibility(user_id: int, tax_year: str) -> dict:
    """Compute the HICBC responsibility result + privacy-minimised customer view.

    Combines the user's manual partner estimate (if any) with linked partner
    evidence (if any) without giving either source precedence.  Returns
    ``{"result": HicbcResponsibilityResult, "view": dict, "user_ani": Decimal}``.
    """
    profile = get_profile_by_user(user_id) or {}
    user_ani = _user_ani_from_profile(profile)
    row = get_hicbc_estimate(user_id, tax_year)

    has_partner = None
    manual_evidence = None
    if row is not None:
        has_partner = row.get("has_relevant_partner")
        if has_partner == 1:
            manual_evidence = _partner_evidence_from_row(row)

    linked_evidence = _linked_partner_evidence(user_id, tax_year)
    if linked_evidence is not None:
        has_partner = True  # an active, mutually consented link affirms a partner

    partner_evidence = None
    additional_evidence: tuple[PartnerEvidence, ...] = ()
    if manual_evidence is not None and linked_evidence is not None:
        partner_evidence, _conflict = _merge_partner_evidence(manual_evidence, linked_evidence)
        additional_evidence = (manual_evidence, linked_evidence)
    elif manual_evidence is not None:
        partner_evidence = manual_evidence
    elif linked_evidence is not None:
        partner_evidence = linked_evidence

    child_benefit_amount = _child_benefit_amount_from_row(row, tax_year)

    result = determine_hicbc_responsibility(
        user_ani=user_ani,
        child_benefit_amount=child_benefit_amount,
        has_relevant_partner=has_partner,
        partner_evidence=partner_evidence,
        additional_evidence=additional_evidence,
        tax_year=tax_year,
    )
    return {"result": result, "view": customer_view(result), "user_ani": user_ani}


def _tax_year_from_form_or_context() -> str:
    raw = (request.form.get("tax_year") or "").strip()
    if not raw:
        return configured_tax_year()
    return resolve_tax_year(result_tax_year=raw, context_tax_year=configured_tax_year())


@hicbc.get("/")
@require_auth
def index():
    tax_year = configured_tax_year()
    built = build_responsibility(g.user_id, tax_year)
    row = get_hicbc_estimate(g.user_id, tax_year)
    transition = session.pop(_TRANSITION_SESSION_KEY, None)
    household_change = bool(transition)
    return render_template(
        "v2/hicbc.html",
        view=built["view"],
        user_ani=built["user_ani"],
        row=row,
        tax_year=tax_year,
        household_change=household_change,
    )


@hicbc.get("/result")
@require_auth
def result_json():
    tax_year = configured_tax_year()
    built = build_responsibility(g.user_id, tax_year)
    return jsonify(built["view"])


@hicbc.post("/estimate")
@require_auth
def save_estimate():
    tax_year = _tax_year_from_form_or_context()

    # ── Server-side validation (fail closed, no raw values logged) ───────────
    errors = []
    receives_cb = _tri(request.form.get("receives_child_benefit"))
    children_raw = (request.form.get("child_benefit_children") or "0").strip()
    try:
        children = int(children_raw)
        if children < 0:
            raise ValueError
    except (ValueError, TypeError):
        children = None
        errors.append("Number of children must be a whole number of zero or more.")

    annual_override = None
    annual_raw = (request.form.get("child_benefit_annual") or "").strip()
    if annual_raw:
        try:
            annual_override = _decimal(annual_raw, "child_benefit_annual", allow_zero=False)
        except ValueError as exc:
            errors.append(str(exc))

    has_partner = _tri(request.form.get("has_relevant_partner"))
    representation = (request.form.get("representation") or "").strip()
    partner_point = partner_low = partner_high = None

    if has_partner == 1:
        if representation not in ("point", "range"):
            errors.append("Choose a partner income estimate type (a single amount or a range).")
        else:
            try:
                if representation == "point":
                    partner_point = _decimal(request.form.get("partner_ani_point"), "partner_ani_point", allow_zero=False)
                    if partner_point is None:
                        errors.append("Enter the partner's estimated adjusted net income.")
                else:
                    partner_low = _decimal(request.form.get("partner_ani_low"), "partner_ani_low", allow_zero=False)
                    partner_high = _decimal(request.form.get("partner_ani_high"), "partner_ani_high", allow_zero=False)
                    if partner_low is None or partner_high is None:
                        errors.append("Enter both a lower and upper partner income estimate.")
                    elif partner_low > partner_high:
                        errors.append("The lower partner income estimate must not exceed the upper estimate.")
            except ValueError as exc:
                errors.append(str(exc))
    else:
        representation = None

    if errors:
        return render_template(
            "v2/hicbc.html",
            view={"headline": "Please correct the highlighted fields."},
            user_ani=Decimal("0"),
            row=None,
            tax_year=tax_year,
            errors=errors,
        ), 400

    old_result = build_responsibility(g.user_id, tax_year)["result"]

    save_hicbc_estimate(g.user_id, {
        "tax_year": tax_year,
        "receives_child_benefit": receives_cb,
        "child_benefit_children": children or 0,
        "child_benefit_annual": str(annual_override) if annual_override is not None else None,
        "has_relevant_partner": has_partner,
        "representation": representation,
        "partner_ani_point": str(partner_point) if partner_point is not None else None,
        "partner_ani_low": str(partner_low) if partner_low is not None else None,
        "partner_ani_high": str(partner_high) if partner_high is not None else None,
        "source_kind": _SOURCE_KIND,
        "completeness": "complete_for_purpose",
        "recency_state": "current",
    })

    new_result = build_responsibility(g.user_id, tax_year)["result"]
    change = household_change_status(
        old_result.responsibility_status, new_result.responsibility_status
    )
    if change in _SURFACED_TRANSITIONS:
        # Server-derived, one-shot transition. Stored in the signed session (not
        # a customer-supplied query parameter) so a stale or replayed parameter
        # cannot fabricate a change notification, and popped on read so it is
        # shown exactly once.
        session[_TRANSITION_SESSION_KEY] = {
            "from": old_result.responsibility_status,
            "to": new_result.responsibility_status,
        }
    return redirect(url_for("hicbc.index"))


@hicbc.post("/delete")
@require_auth
def delete_estimate():
    tax_year = _tax_year_from_form_or_context()
    delete_hicbc_estimate(g.user_id, tax_year)
    return redirect(url_for("hicbc.index"))


# ── Linked-account consent (HICBC-only) ────────────────────────────────────────

def _link_view(user_id: int, tax_year: str, *, message: str | None = None) -> dict:
    link = get_active_hicbc_link(user_id, tax_year)
    return {
        "tax_year": tax_year,
        "link": link,
        "linked": link is not None,
        "message": message,
    }


@hicbc.get("/link")
@require_auth
def link_page():
    tax_year = configured_tax_year()
    message = session.pop("_hicbc_link_message", None)
    return render_template(
        "v2/hicbc_link.html",
        view=_link_view(g.user_id, tax_year, message=message),
    )


@hicbc.post("/link/invite")
@require_auth
def link_invite():
    tax_year = _tax_year_from_form_or_context()
    token = create_hicbc_link_invitation(g.user_id, tax_year)
    # The raw token is returned exactly once to the creating user; it is never
    # stored, logged or rendered to anyone else.
    return render_template(
        "v2/hicbc_link.html",
        view=_link_view(g.user_id, tax_year),
        invitation_token=token,
    )


@hicbc.post("/link/accept")
@require_auth
def link_accept():
    tax_year = _tax_year_from_form_or_context()
    token = (request.form.get("invitation_token") or "").strip()
    result = accept_hicbc_link_invitation(g.user_id, token, tax_year) if token else None
    if result is None:
        session["_hicbc_link_message"] = (
            "We could not complete that link. The invitation may be invalid, "
            "expired or already used."
        )
    else:
        session["_hicbc_link_message"] = "Your accounts are now linked for Child Benefit charge purposes."
    return redirect(url_for("hicbc.link_page"))


@hicbc.post("/link/revoke")
@require_auth
def link_revoke():
    tax_year = _tax_year_from_form_or_context()
    revoke_hicbc_link(g.user_id, tax_year)
    session["_hicbc_link_message"] = "The link has been removed."
    return redirect(url_for("hicbc.link_page"))
