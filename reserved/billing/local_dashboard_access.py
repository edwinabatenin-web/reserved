"""W10-S5 local dashboard access installer (explicit, non-production).

This module is the first *actual application consumer* of the already-reviewed
W10-S3C runtime-entitlement admission and W10-S5D paid-access guard.  It is not
another policy contract, repository composition fixture or detached decision
protocol.  It provides one explicitly-called, non-production installer that
wraps the already-registered ``v2.dashboard_view`` view function for a single
live Flask application instance.

Nothing happens on import.  The module has no application registration, no new
route, no environment-selected repository, no schema change, no payment action
and no default database path.  The default application is unchanged unless a
deployment composition root explicitly calls :func:`install_local_dashboard_access`.

Dependencies are explicit server bindings (functions supplied by the caller):

1. Existing signed-session identity plus an actual current synthetic-user lookup.
   The installer refuses non-exact, deleted or forged session identifiers before
   any financial work.
2. An explicit, independent owner/account/subscription membership resolver.  It
   is never derived from a URL, form, email, caller owner argument or repository
   contents.  For real users this resolver is intentionally unconfigured and
   returns ``None``; this package does not manufacture ``authenticated=True`` or
   authority from a stored row, hash, provider label or arbitrary caller tuple.
3. Accepted S3D current snapshot/journal identity and ordering, read for the
   authenticated owner and the exact resolved billing scope.
4. Separately validated live billing-fact evidence matching that snapshot,
   admitted through the unchanged W10-S3C adapter.  Structural rows/hashes are
   never treated as facts.
5. The unchanged W10-S5D guard authorises whether the real dashboard executes.

The installer refuses production using the established auth/config meaning,
rejects duplicate/late/ambiguous installation, and preserves the original
endpoint/authentication behaviour by reusing :func:`reserved.auth.require_auth`.
It exposes no alternate unguarded HTTP path and no general arbitrary-route
wrapper.  A denial is a bounded, value-free 403 with no-store behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

import reserved.billing.paid_access_guard as _paid_access_guard
import reserved.billing.runtime_entitlement_admission as _admission

__all__ = (
    "CONTRACT_VERSION",
    "FD_W10_004",
    "PROTECTED_ENDPOINT",
    "BillingSnapshot",
    "SnapshotEntry",
    "LocalDashboardAccessError",
    "LocalDashboardAccessHandle",
    "install_local_dashboard_access",
)

CONTRACT_VERSION = "reserved-w10-local-dashboard-access/1.0"
FD_W10_004 = "FD-W10-004"
PROTECTED_ENDPOINT = "v2.dashboard_view"
_EXTENSION_KEY = "reserved.billing.local_dashboard_access"


class LocalDashboardAccessError(ValueError):
    """Installation or evaluation failed closed (no sensitive detail emitted)."""


@dataclass(frozen=True, slots=True)
class SnapshotEntry:
    """Structural projection of one accepted S3D journal entry (never a fact).

    Carries the recorded outcome/meaning of the entry — the exact semantic
    fields that the separately admitted live billing fact must reproduce — so
    the installer can bind the fact's meaning/provenance to the structural
    entry without ever equating the S3D journal content identity with the S3C
    fact identity (different hash domains).
    """

    sequence: int
    content_identity: str
    predecessor_identity: str | None
    state: str
    derivation_kind: str
    withdrawal_attribution: str
    valid_from_inclusive: date
    valid_until_exclusive: date
    transition_effective_at_utc: datetime
    recovery_deadline_exclusive_at_utc: datetime | None


@dataclass(frozen=True, slots=True)
class BillingSnapshot:
    """Structural projection of one accepted S3D current snapshot/journal."""

    owner_id: str
    billing_account_id: str
    subscription_id: str
    head_identity: str
    head_sequence: int
    entries: tuple[SnapshotEntry, ...]


class LocalDashboardAccessHandle:
    """Opaque marker for one completed installation."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *args, **kwargs):
        raise TypeError("local dashboard access handles are installer-issued only")


def _denial_response():
    # Bounded, value-free denial: no identifier, provider payload or financial
    # fact in the body or headers.  The app after_request also reinforces
    # no-store for /v2/ and authenticated responses.
    from flask import make_response

    response = make_response("", 403)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _exact_scope(scope):
    if type(scope) is not tuple or len(scope) != 3:
        return None
    if not all(type(part) is str for part in scope):
        return None
    return scope


def _verify_snapshot(snapshot):
    if type(snapshot) is not BillingSnapshot:
        return False
    if not all(type(part) is str for part in (
        snapshot.owner_id,
        snapshot.billing_account_id,
        snapshot.subscription_id,
        snapshot.head_identity,
    )):
        return False
    if type(snapshot.head_sequence) is not int or snapshot.head_sequence <= 0:
        return False
    entries = snapshot.entries
    if type(entries) is not tuple or not entries:
        return False
    # Validate entry type before any attribute access so a malformed entry such
    # as ``(None,)`` fails closed instead of raising AttributeError.
    if any(type(entry) is not SnapshotEntry for entry in entries):
        return False
    if snapshot.head_sequence != len(entries):
        return False
    if entries[-1].sequence != snapshot.head_sequence:
        return False
    if entries[-1].content_identity != snapshot.head_identity:
        return False
    previous_identity = None
    for index, entry in enumerate(entries):
        if type(entry.sequence) is not int or entry.sequence != index + 1:
            return False
        if type(entry.content_identity) is not str or not entry.content_identity:
            return False
        if type(entry.state) is not str or not entry.state:
            return False
        if type(entry.derivation_kind) is not str or not entry.derivation_kind:
            return False
        if type(entry.withdrawal_attribution) is not str or not entry.withdrawal_attribution:
            return False
        if type(entry.valid_from_inclusive) is not date:
            return False
        if type(entry.valid_until_exclusive) is not date:
            return False
        if entry.valid_from_inclusive >= entry.valid_until_exclusive:
            return False
        if (
            type(entry.transition_effective_at_utc) is not datetime
            or entry.transition_effective_at_utc.tzinfo is not timezone.utc
        ):
            return False
        if entry.recovery_deadline_exclusive_at_utc is not None and (
            type(entry.recovery_deadline_exclusive_at_utc) is not datetime
            or entry.recovery_deadline_exclusive_at_utc.tzinfo is not timezone.utc
        ):
            return False
        if index == 0:
            if entry.predecessor_identity is not None:
                return False
        else:
            if entry.predecessor_identity != previous_identity:
                return False
        previous_identity = entry.content_identity
    return True


def _entry_binds_outcome(entry, projection, owner_id):
    """Compare the common fact/runtime outcome fields to the structural entry.

    The live fact is a different hash domain from the S3D journal entry, so the
    binding compares projected *meaning* (owner, sequence, state,
    derivation, attribution, validity window, transition and recovery deadline)
    against the recorded entry.  No S3D content identity is ever compared to an
    S3C fact identity.
    """
    return (
        projection.get("owner_id") == owner_id
        and projection.get("decision_sequence") == entry.sequence
        and projection.get("state") == entry.state
        and projection.get("derivation_kind") == entry.derivation_kind
        and projection.get("withdrawal_attribution") == entry.withdrawal_attribution
        and projection.get("valid_from_inclusive") == entry.valid_from_inclusive
        and projection.get("valid_until_exclusive") == entry.valid_until_exclusive
        and projection.get("transition_effective_at_utc") == entry.transition_effective_at_utc
        and projection.get("recovery_deadline_exclusive_at_utc")
        == entry.recovery_deadline_exclusive_at_utc
    )


def _entry_binds_fact(entry, projection, owner_id, billing_account_id, subscription_id):
    return (
        projection.get("billing_account_id") == billing_account_id
        and projection.get("subscription_id") == subscription_id
        and _entry_binds_outcome(entry, projection, owner_id)
    )


def _evaluate(access, *, evaluated_at_utc, endpoint=PROTECTED_ENDPOINT):
    """Authorise the exact paid endpoint (standalone dashboard by default).

    Every failure mode returns False and is collapsed into a bounded value-free
    403.  No exception detail, identifier or financial fact escapes.
    """
    from flask import g

    from reserved.database import get_user

    if type(endpoint) is not str or endpoint not in _paid_access_guard.PAID_ENDPOINTS:
        return False
    user_id = g.get("user_id")
    if type(user_id) is not int:
        return False
    try:
        user_row = get_user(user_id)
    except Exception:
        return False
    if user_row is None:
        return False

    try:
        scope = access.membership_resolver(user_id)
    except Exception:
        return False
    scope = _exact_scope(scope)
    if scope is None:
        return False
    owner_id, billing_account_id, subscription_id = scope

    try:
        snapshot = access.snapshot_reader(owner_id, billing_account_id, subscription_id)
    except Exception:
        return False
    if not _verify_snapshot(snapshot):
        return False
    if (
        snapshot.owner_id != owner_id
        or snapshot.billing_account_id != billing_account_id
        or snapshot.subscription_id != subscription_id
    ):
        return False

    # Admit the full live chain in snapshot order.  Each entry is resolved
    # separately by the live fact issuer and admitted through the unchanged
    # S3C adapter against its predecessor.  The head fact therefore carries the
    # whole lineage; structural rows/hashes are never treated as authority.
    #
    # Historical entries are admitted at their own transition instant so a chain
    # whose earlier validity windows have already closed still replays through
    # the unchanged S3C adapter.  Only the head is admitted at the request's
    # evaluation instant; the adapter's future/stale checks then bind the head to
    # the exact current boundary.
    admitted = []
    entry_count = len(snapshot.entries)
    for index, entry in enumerate(snapshot.entries):
        prior_runtime = admitted[-1] if admitted else None
        fact = None
        try:
            fact = access.live_fact_resolver(
                owner_id, billing_account_id, subscription_id,
                entry.content_identity, entry.sequence,
            )
        except Exception:
            return False
        if fact is None:
            return False
        # Bind the live fact's meaning/provenance to this exact structural entry
        # before any admission: the fact must reproduce the recorded scope,
        # sequence and outcome fields.  A valid but substituted same-scope/same-
        # sequence fact (e.g. paid/withdrawal_ambiguous substituted for the
        # recorded suspended/verified_full_withdrawal) is rejected here.
        try:
            projection = dict(access.project_admitted_billing_fact(fact))
        except Exception:
            return False
        if not _entry_binds_fact(
            entry, projection, owner_id, billing_account_id, subscription_id
        ):
            return False
        if index < entry_count - 1:
            fact_evaluated_at = projection["transition_effective_at_utc"]
        else:
            fact_evaluated_at = evaluated_at_utc
        try:
            runtime = _admission.admit_runtime_entitlement(
                access.admission_binding,
                authenticated_owner_id=owner_id,
                billing_account_id=billing_account_id,
                subscription_id=subscription_id,
                prior_runtime_entitlement=prior_runtime,
                admitted_billing_fact=fact,
                evaluated_at_utc=fact_evaluated_at,
            )
        except Exception:
            return False
        # Bind the immutable *admitted outcome*, not another read of the mutable
        # upstream fact. S3C independently enforces account/subscription and fact
        # predecessor scope inside admission; those fields are intentionally not
        # exposed in its runtime projection. Do not invent them or equate the
        # journal, fact and runtime identity domains. Check every chain member.
        try:
            outcome = dict(_admission.project_runtime_entitlement(runtime))
            predecessor = (
                dict(_admission.project_runtime_entitlement(prior_runtime))["decision_identity"]
                if prior_runtime is not None else None
            )
        except Exception:
            return False
        if not _entry_binds_outcome(entry, outcome, owner_id):
            return False
        if outcome.get("predecessor_identity") != predecessor:
            return False
        admitted.append(runtime)

    current_runtime = admitted[-1]
    prior_runtime = admitted[-2] if len(admitted) > 1 else None

    # Match the admitted head to the exact snapshot entry: sequence must agree
    # and the admitted owner must be the authenticated scope owner.
    try:
        current_projection = dict(_admission.project_runtime_entitlement(current_runtime))
    except Exception:
        return False
    if current_projection.get("decision_sequence") != snapshot.head_sequence:
        return False
    if current_projection.get("owner_id") != owner_id:
        return False

    # Revalidate the current source identity/order at this authoritative
    # evaluation.  If the repository head changed while we admitted evidence,
    # fail closed deterministically rather than honouring a stale positive grant.
    try:
        rechecked = access.snapshot_reader(
            owner_id, billing_account_id, subscription_id
        )
    except Exception:
        return False
    if not _verify_snapshot(rechecked):
        return False
    # Full scoped snapshot/chain consistency, not just head labels: the rechecked
    # snapshot must equal the originally admitted snapshot exactly (owner,
    # account, subscription and every entry's identity, predecessor and outcome).
    if rechecked != snapshot:
        return False

    try:
        decision = _paid_access_guard.evaluate_paid_access(
            access.guard,
            endpoint=endpoint,
            authenticated_owner_id=owner_id,
            prior_runtime_entitlement=prior_runtime,
            current_runtime_entitlement=current_runtime,
            evaluated_at_utc=evaluated_at_utc,
        )
        result = dict(_paid_access_guard.validate_paid_access_decision(decision))
    except Exception:
        return False
    return result.get("allowed") is True


def install_local_dashboard_access(
    app,
    *,
    membership_resolver,
    snapshot_reader,
    live_fact_resolver,
    validate_admitted_billing_fact,
    project_admitted_billing_fact,
    clock=None,
):
    """Wrap the registered ``v2.dashboard_view`` for ``app`` with the S5 gate.

    Explicitly called, never automatic.  Refuses production, duplicate, late and
    ambiguous installation.  Returns an opaque install handle.
    """
    from reserved.auth import is_production_environment, require_auth
    from reserved.web import v2

    if is_production_environment():
        raise LocalDashboardAccessError(
            "local dashboard access installer refuses production"
        )

    if type(app) is not _app_type():
        raise LocalDashboardAccessError("installer requires a Flask application")

    if getattr(app, "_got_first_request", False):
        raise LocalDashboardAccessError("installer refuses late installation")

    if _EXTENSION_KEY in app.extensions:
        raise LocalDashboardAccessError("installer refuses duplicate installation")

    view_functions = getattr(app, "view_functions", None)
    if not isinstance(view_functions, dict):
        raise LocalDashboardAccessError("installer refuses ambiguous application")

    original = view_functions.get(PROTECTED_ENDPOINT)
    if original is None or original is not v2.dashboard_view:
        raise LocalDashboardAccessError(
            "installer refuses ambiguous endpoint registration"
        )
    original_body = getattr(original, "__wrapped__", None)
    if not callable(original_body):
        raise LocalDashboardAccessError(
            "installer requires the registered require_auth-wrapped dashboard"
        )

    if not callable(membership_resolver) or not callable(snapshot_reader):
        raise LocalDashboardAccessError("installer requires explicit server bindings")
    if not callable(live_fact_resolver):
        raise LocalDashboardAccessError("installer requires a live fact resolver")

    admission_binding = _admission.bind_runtime_entitlement_admission(
        validate_admitted_billing_fact=validate_admitted_billing_fact,
        project_admitted_billing_fact=project_admitted_billing_fact,
    )
    guard = _paid_access_guard.bind_paid_access_guard(
        validate_runtime_entitlement=_admission.validate_runtime_entitlement,
        project_runtime_entitlement=_admission.project_runtime_entitlement,
    )
    effective_clock = clock if callable(clock) else lambda: datetime.now(timezone.utc)

    handle = object.__new__(LocalDashboardAccessHandle)

    class _Access:
        __slots__ = (
            "membership_resolver",
            "snapshot_reader",
            "live_fact_resolver",
            "admission_binding",
            "guard",
            "project_admitted_billing_fact",
        )

        def __init__(
            self,
            membership_resolver,
            snapshot_reader,
            live_fact_resolver,
            admission_binding,
            guard,
            project_admitted_billing_fact,
        ):
            self.membership_resolver = membership_resolver
            self.snapshot_reader = snapshot_reader
            self.live_fact_resolver = live_fact_resolver
            self.admission_binding = admission_binding
            self.guard = guard
            self.project_admitted_billing_fact = project_admitted_billing_fact

    access = _Access(
        membership_resolver=membership_resolver,
        snapshot_reader=snapshot_reader,
        live_fact_resolver=live_fact_resolver,
        admission_binding=admission_binding,
        guard=guard,
        project_admitted_billing_fact=project_admitted_billing_fact,
    )

    @require_auth
    def guarded_dashboard(*args, **kwargs):
        # Re-check the dual-production-signal lock at request time (not just at
        # install time): if either signal flipped after installation the request
        # must be denied before any financial read/render.
        if is_production_environment():
            return _denial_response()
        try:
            evaluated_at_utc = effective_clock()
        except Exception:
            return _denial_response()
        try:
            allowed = _evaluate(access, evaluated_at_utc=evaluated_at_utc)
        except Exception:
            allowed = False
        if not allowed:
            return _denial_response()
        return original_body(*args, **kwargs)

    view_functions[PROTECTED_ENDPOINT] = guarded_dashboard
    app.extensions[_EXTENSION_KEY] = handle
    return handle


def _app_type():
    from flask import Flask

    return Flask
