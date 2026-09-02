"""Provider-neutral, network-inert operational-resilience contract.

This module owns only the local classification of one evidence route during an
outage or safe-degradation event. It models provider-neutral facts, not any
provider API, and performs no network call, credential access, token handling,
persistence, customer-record read, provider activation or scheduling. A route is
identified by a bounded non-secret ``EvidenceRouteIdentity``; its current
operational classification is an immutable ``EvidenceRouteStatus``.

The contract deliberately keeps recovery two-step: a fresh observation must
first be *received* (``begin_recovery``) and then *verified* (``complete_recovery``)
before a route can become ``AVAILABLE``. A status flag or a stale observation is
never enough to restore currency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class OperationalResilienceError(ValueError):
    """Operational-resilience state failed closed without side effects."""


class OperationalState(str, Enum):
    """Provider-neutral operational classification of one evidence route."""

    AVAILABLE = "available"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    AUTHORISATION_REQUIRED = "authorisation_required"
    SCHEMA_INCOMPATIBLE = "schema_incompatible"
    EVIDENCE_INADEQUATE = "evidence_inadequate"
    STALE = "stale"
    RECOVERY_PENDING = "recovery_pending"


class OutageEvent(str, Enum):
    """Bounded provider-neutral outage causes that map to a degraded state."""

    TIMEOUT = "timeout"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    AUTHORISATION_EXPIRED = "authorisation_expired"
    AUTHORISATION_REVOKED = "authorisation_revoked"
    SCHEMA_INCOMPATIBLE = "schema_incompatible"
    REQUIRED_FIELDS_MISSING = "required_fields_missing"
    REQUIRED_FIELDS_INVALID = "required_fields_invalid"
    EVIDENCE_STALE = "evidence_stale"


class CustomerAction(str, Enum):
    """Whether a customer refresh/reconnect/manual-evidence action applies."""

    NONE = "none"
    RETRY_LATER = "retry_later"
    RECONNECT = "reconnect"
    PROVIDE_EVIDENCE = "provide_evidence"
    REFRESH = "refresh"


class CustomerMessage(str, Enum):
    """Bounded customer-safe message key, never free-form provider text."""

    AVAILABLE = "available"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    RECONNECT_REQUIRED = "reconnect_required"
    DATA_FORMAT_CHANGED = "data_format_changed"
    INFORMATION_INCOMPLETE = "information_incomplete"
    INFORMATION_OUT_OF_DATE = "information_out_of_date"
    RECOVERY_IN_PROGRESS = "recovery_in_progress"


_SAFE_REFERENCE = re.compile(r"^[A-Za-z0-9._:-]{1,160}$")

_EVENT_STATE = {
    OutageEvent.TIMEOUT: OperationalState.TEMPORARILY_UNAVAILABLE,
    OutageEvent.TEMPORARILY_UNAVAILABLE: OperationalState.TEMPORARILY_UNAVAILABLE,
    OutageEvent.AUTHORISATION_EXPIRED: OperationalState.AUTHORISATION_REQUIRED,
    OutageEvent.AUTHORISATION_REVOKED: OperationalState.AUTHORISATION_REQUIRED,
    OutageEvent.SCHEMA_INCOMPATIBLE: OperationalState.SCHEMA_INCOMPATIBLE,
    OutageEvent.REQUIRED_FIELDS_MISSING: OperationalState.EVIDENCE_INADEQUATE,
    OutageEvent.REQUIRED_FIELDS_INVALID: OperationalState.EVIDENCE_INADEQUATE,
    OutageEvent.EVIDENCE_STALE: OperationalState.STALE,
}

_ACTION_BY_STATE = {
    OperationalState.AVAILABLE: CustomerAction.NONE,
    OperationalState.TEMPORARILY_UNAVAILABLE: CustomerAction.RETRY_LATER,
    OperationalState.AUTHORISATION_REQUIRED: CustomerAction.RECONNECT,
    OperationalState.SCHEMA_INCOMPATIBLE: CustomerAction.NONE,
    OperationalState.EVIDENCE_INADEQUATE: CustomerAction.PROVIDE_EVIDENCE,
    OperationalState.STALE: CustomerAction.REFRESH,
    OperationalState.RECOVERY_PENDING: CustomerAction.NONE,
}

_MESSAGE_BY_STATE = {
    OperationalState.AVAILABLE: CustomerMessage.AVAILABLE,
    OperationalState.TEMPORARILY_UNAVAILABLE: CustomerMessage.TEMPORARILY_UNAVAILABLE,
    OperationalState.AUTHORISATION_REQUIRED: CustomerMessage.RECONNECT_REQUIRED,
    OperationalState.SCHEMA_INCOMPATIBLE: CustomerMessage.DATA_FORMAT_CHANGED,
    OperationalState.EVIDENCE_INADEQUATE: CustomerMessage.INFORMATION_INCOMPLETE,
    OperationalState.STALE: CustomerMessage.INFORMATION_OUT_OF_DATE,
    OperationalState.RECOVERY_PENDING: CustomerMessage.RECOVERY_IN_PROGRESS,
}

_RECOVERABLE_STATES = frozenset(
    {
        OperationalState.TEMPORARILY_UNAVAILABLE,
        OperationalState.AUTHORISATION_REQUIRED,
        OperationalState.SCHEMA_INCOMPATIBLE,
        OperationalState.EVIDENCE_INADEQUATE,
        OperationalState.STALE,
    }
)
_RECOVERY_AUTHORITY = object()


def _reject_serialisation() -> None:
    raise OperationalResilienceError(
        "operational-resilience values are intentionally not serialisable"
    )


def _safe_identity_part(value: object, field: str) -> str:
    if type(value) is not str or _SAFE_REFERENCE.fullmatch(value) is None:
        raise OperationalResilienceError(
            f"{field} must be an opaque bounded identifier without "
            "whitespace or URL/query characters"
        )
    return value


def _aware_utc(value: object, field: str) -> datetime | None:
    if value is None:
        return None
    if type(value) is not datetime:
        raise OperationalResilienceError(f"{field} must be a timezone-aware datetime")
    try:
        offset = value.utcoffset()
    except Exception:
        raise OperationalResilienceError(f"{field} must be timezone-aware") from None
    if offset is None:
        raise OperationalResilienceError(f"{field} must be timezone-aware")
    try:
        return value.astimezone(timezone.utc)
    except Exception:
        raise OperationalResilienceError(f"{field} must be timezone-aware") from None


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    try:
        return value.isoformat()
    except Exception:
        return None


@dataclass(frozen=True, repr=False)
class EvidenceRouteIdentity:
    """Bounded non-secret identity of one provider evidence route."""

    provider: str
    route: str
    owner_scope: str | None = None
    _identity_binding: tuple[str, str, str | None] = field(
        init=False, repr=False, compare=False, hash=False
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "provider", _safe_identity_part(self.provider, "provider"))
        object.__setattr__(self, "route", _safe_identity_part(self.route, "route"))
        if self.owner_scope is not None:
            object.__setattr__(
                self, "owner_scope", _safe_identity_part(self.owner_scope, "owner_scope")
            )
        object.__setattr__(
            self,
            "_identity_binding",
            (self.provider, self.route, self.owner_scope),
        )

    def _assert_integrity(self) -> None:
        if type(self) is not EvidenceRouteIdentity:
            raise OperationalResilienceError("identity must be an EvidenceRouteIdentity")
        provider = _safe_identity_part(self.provider, "provider")
        route = _safe_identity_part(self.route, "route")
        owner = self.owner_scope
        if owner is not None:
            owner = _safe_identity_part(owner, "owner_scope")
        expected = (provider, route, owner)
        binding = getattr(self, "_identity_binding", None)
        if type(binding) is not tuple or binding != expected:
            raise OperationalResilienceError("evidence route identity integrity check failed")

    def __repr__(self) -> str:
        try:
            provider = _safe_identity_part(self.provider, "provider")
            route = _safe_identity_part(self.route, "route")
            owner = self.owner_scope
            if owner is not None:
                owner = _safe_identity_part(owner, "owner_scope")
            return (
                "EvidenceRouteIdentity("
                f"provider={provider!r}, route={route!r}, owner_scope={owner!r})"
            )
        except Exception:
            return "EvidenceRouteIdentity([INVALID])"

    def __copy__(self) -> "EvidenceRouteIdentity":
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> "EvidenceRouteIdentity":
        memo[id(self)] = self
        return self

    def __reduce__(self) -> object:
        _reject_serialisation()
        return ()


@dataclass(frozen=True, repr=False)
class RecoveryObservation:
    """A freshly retrieved observation offered for one evidence route.

    It carries only identity and timestamps; required-field and schema validity
    are decided later by ``complete_recovery``.
    """

    identity: EvidenceRouteIdentity
    observed_at: datetime
    retrieved_at: datetime
    _observation_binding: tuple[tuple[str, str, str | None], datetime, datetime] = field(
        init=False, repr=False, compare=False, hash=False
    )

    def __post_init__(self) -> None:
        if type(self.identity) is not EvidenceRouteIdentity:
            raise OperationalResilienceError("identity must be an EvidenceRouteIdentity")
        self.identity._assert_integrity()
        observed = _aware_utc(self.observed_at, "observed_at")
        retrieved = _aware_utc(self.retrieved_at, "retrieved_at")
        if observed is None or retrieved is None:
            raise OperationalResilienceError("recovery observation requires timestamps")
        if observed > retrieved:
            raise OperationalResilienceError("observed_at must not follow retrieved_at")
        object.__setattr__(self, "observed_at", observed)
        object.__setattr__(self, "retrieved_at", retrieved)
        object.__setattr__(
            self,
            "_observation_binding",
            (self.identity._identity_binding, observed, retrieved),
        )

    def _assert_integrity(self) -> None:
        if type(self) is not RecoveryObservation:
            raise OperationalResilienceError("observation must be a RecoveryObservation")
        self.identity._assert_integrity()
        observed = _aware_utc(self.observed_at, "observed_at")
        retrieved = _aware_utc(self.retrieved_at, "retrieved_at")
        if observed is None or retrieved is None or observed > retrieved:
            raise OperationalResilienceError("recovery observation integrity check failed")
        expected = (self.identity._identity_binding, observed, retrieved)
        binding = getattr(self, "_observation_binding", None)
        if type(binding) is not tuple or binding != expected:
            raise OperationalResilienceError("recovery observation integrity check failed")

    def __repr__(self) -> str:
        try:
            return (
                "RecoveryObservation("
                f"identity={self.identity!r}, observed_at={_iso(self.observed_at)!r}, "
                f"retrieved_at={_iso(self.retrieved_at)!r})"
            )
        except Exception:
            return "RecoveryObservation([INVALID])"

    def __copy__(self) -> "RecoveryObservation":
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> "RecoveryObservation":
        memo[id(self)] = self
        return self

    def __reduce__(self) -> object:
        _reject_serialisation()
        return ()


@dataclass(frozen=True, repr=False)
class EvidenceRouteStatus:
    """Immutable operational classification of one evidence route.

    ``may_use_as_current`` and ``may_show_stale_context`` are derived facts; the
    stored ``state`` label alone never grants currency.
    """

    identity: EvidenceRouteIdentity
    state: OperationalState
    observed_at: datetime | None = None
    retrieved_at: datetime | None = None
    last_verified_at: datetime | None = None
    required_fields_validated: bool = False
    last_transition_at: datetime | None = None
    last_accepted_observed_at: datetime | None = None
    _status_binding: tuple[object, ...] = field(
        init=False, repr=False, compare=False, hash=False
    )
    _recovery_binding: (
        tuple[object, tuple[object, ...], tuple[object, ...]] | None
    ) = field(
        init=False, default=None, repr=False, compare=True, hash=True
    )

    def __post_init__(self) -> None:
        if type(self.identity) is not EvidenceRouteIdentity:
            raise OperationalResilienceError("identity must be an EvidenceRouteIdentity")
        self.identity._assert_integrity()
        if type(self.state) is not OperationalState:
            raise OperationalResilienceError("state must be an OperationalState")
        if type(self.required_fields_validated) is not bool:
            raise OperationalResilienceError("required_fields_validated must be a boolean")

        observed = _aware_utc(self.observed_at, "observed_at")
        retrieved = _aware_utc(self.retrieved_at, "retrieved_at")
        verified = _aware_utc(self.last_verified_at, "last_verified_at")
        transitioned = _aware_utc(self.last_transition_at, "last_transition_at")
        accepted_observed = _aware_utc(
            self.last_accepted_observed_at, "last_accepted_observed_at"
        )

        if observed is not None and retrieved is not None and observed > retrieved:
            raise OperationalResilienceError("observed_at must not follow retrieved_at")
        if self.state is OperationalState.AVAILABLE:
            if not self.required_fields_validated:
                raise OperationalResilienceError(
                    "available evidence requires validated required fields"
                )
            if observed is None or retrieved is None or verified is None:
                raise OperationalResilienceError(
                    "available evidence requires complete provenance timestamps"
                )
            if retrieved > verified:
                raise OperationalResilienceError(
                    "retrieved_at must not follow last_verified_at"
                )
            if accepted_observed is None:
                accepted_observed = observed
            elif accepted_observed != observed:
                raise OperationalResilienceError(
                    "available observation must match its accepted observation watermark"
                )
        elif self.state is OperationalState.STALE:
            if not self.required_fields_validated:
                raise OperationalResilienceError(
                    "stale evidence requires a previously validated observation"
                )
            if observed is None or retrieved is None or verified is None:
                raise OperationalResilienceError(
                    "stale evidence requires retained observation timestamps"
                )
            if retrieved > verified:
                raise OperationalResilienceError(
                    "retrieved_at must not follow last_verified_at"
                )
            if accepted_observed is None:
                accepted_observed = observed
            elif accepted_observed != observed:
                raise OperationalResilienceError(
                    "stale observation must match its accepted observation watermark"
                )
        elif self.state is OperationalState.RECOVERY_PENDING:
            if self.required_fields_validated:
                raise OperationalResilienceError(
                    "recovery pending must not claim validated fields"
                )
            if observed is None or retrieved is None:
                raise OperationalResilienceError(
                    "recovery pending requires a fresh observation"
                )
            if verified is not None and retrieved <= verified:
                raise OperationalResilienceError(
                    "recovery retrieval must follow the prior verified watermark"
                )
            if transitioned is not None and retrieved <= transitioned:
                raise OperationalResilienceError(
                    "recovery retrieval must follow the latest route transition"
                )
            if accepted_observed is not None and observed <= accepted_observed:
                raise OperationalResilienceError(
                    "recovery observation must follow the last accepted observation"
                )
        else:
            if self.required_fields_validated:
                raise OperationalResilienceError(
                    "degraded state must not claim validated fields"
                )
            if observed is not None or retrieved is not None:
                raise OperationalResilienceError(
                    "degraded failure state must not carry a current observation"
                )
            if (
                accepted_observed is not None
                and verified is not None
                and accepted_observed > verified
            ):
                raise OperationalResilienceError(
                    "accepted observation watermark must not follow verification"
                )

        object.__setattr__(self, "observed_at", observed)
        object.__setattr__(self, "retrieved_at", retrieved)
        object.__setattr__(self, "last_verified_at", verified)
        object.__setattr__(self, "last_transition_at", transitioned)
        object.__setattr__(self, "last_accepted_observed_at", accepted_observed)
        object.__setattr__(self, "_status_binding", self._binding_values())

    def _binding_values(self) -> tuple[object, ...]:
        return (
            self.identity._identity_binding,
            self.state,
            self.observed_at,
            self.retrieved_at,
            self.last_verified_at,
            self.required_fields_validated,
            self.last_transition_at,
            self.last_accepted_observed_at,
        )

    def _assert_integrity(self) -> None:
        if type(self) is not EvidenceRouteStatus:
            raise OperationalResilienceError("status must be an EvidenceRouteStatus")
        self.identity._assert_integrity()
        if type(self.state) is not OperationalState:
            raise OperationalResilienceError("state must be an OperationalState")
        if type(self.required_fields_validated) is not bool:
            raise OperationalResilienceError("required_fields_validated must be a boolean")
        # Reconstruction applies every constructor invariant to the current deep
        # state. The stored binding then detects direct frozen-object mutation.
        reconstructed = EvidenceRouteStatus(
            identity=self.identity,
            state=self.state,
            observed_at=self.observed_at,
            retrieved_at=self.retrieved_at,
            last_verified_at=self.last_verified_at,
            required_fields_validated=self.required_fields_validated,
            last_transition_at=self.last_transition_at,
            last_accepted_observed_at=self.last_accepted_observed_at,
        )
        expected = reconstructed._status_binding
        binding = getattr(self, "_status_binding", None)
        if type(binding) is not tuple or binding != expected:
            raise OperationalResilienceError("route status integrity check failed")

    def _assert_recovery_binding(self) -> None:
        self._assert_integrity()
        if self.state is not OperationalState.RECOVERY_PENDING:
            raise OperationalResilienceError("status is not a pending recovery")
        binding = getattr(self, "_recovery_binding", None)
        if type(binding) is not tuple or len(binding) != 3:
            raise OperationalResilienceError(
                "pending recovery is not bound to a validated transition"
            )
        authority, current_binding, observation_binding = binding
        if authority is not _RECOVERY_AUTHORITY:
            raise OperationalResilienceError("pending recovery authority is invalid")
        if type(current_binding) is not tuple or type(observation_binding) is not tuple:
            raise OperationalResilienceError("pending recovery binding is invalid")
        if len(current_binding) != 8 or len(observation_binding) != 3:
            raise OperationalResilienceError("pending recovery binding is invalid")
        if current_binding[0] != observation_binding[0]:
            raise OperationalResilienceError("pending recovery route binding is invalid")
        if self.identity._identity_binding != observation_binding[0]:
            raise OperationalResilienceError("pending recovery route binding is invalid")
        if (self.observed_at, self.retrieved_at) != observation_binding[1:]:
            raise OperationalResilienceError("pending recovery observation binding is invalid")
        if self.last_verified_at != current_binding[4]:
            raise OperationalResilienceError("pending recovery watermark binding is invalid")
        if self.last_transition_at != current_binding[6]:
            raise OperationalResilienceError("pending recovery transition binding is invalid")
        if self.last_accepted_observed_at != current_binding[7]:
            raise OperationalResilienceError(
                "pending recovery observation watermark binding is invalid"
            )
        if current_binding[1] not in _RECOVERABLE_STATES:
            raise OperationalResilienceError("pending recovery source state is invalid")
        source = EvidenceRouteStatus(
            identity=self.identity,
            state=current_binding[1],
            observed_at=current_binding[2],
            retrieved_at=current_binding[3],
            last_verified_at=current_binding[4],
            required_fields_validated=current_binding[5],
            last_transition_at=current_binding[6],
            last_accepted_observed_at=current_binding[7],
        )
        if source._status_binding != current_binding:
            raise OperationalResilienceError("pending recovery source binding is invalid")
        observation = RecoveryObservation(
            identity=self.identity,
            observed_at=observation_binding[1],
            retrieved_at=observation_binding[2],
        )
        if observation._observation_binding != observation_binding:
            raise OperationalResilienceError("pending recovery observation binding is invalid")

    @property
    def may_use_as_current(self) -> bool:
        self._assert_integrity()
        if self.state is not OperationalState.AVAILABLE:
            return False
        return (
            self.required_fields_validated is True
            and self.observed_at is not None
            and self.retrieved_at is not None
            and self.last_verified_at is not None
            and self.observed_at <= self.retrieved_at <= self.last_verified_at
        )

    @property
    def may_show_stale_context(self) -> bool:
        self._assert_integrity()
        if self.state is OperationalState.AVAILABLE:
            return False
        return self.last_verified_at is not None

    @property
    def customer_action(self) -> CustomerAction:
        self._assert_integrity()
        return _ACTION_BY_STATE[self.state]

    @property
    def customer_message_key(self) -> CustomerMessage:
        self._assert_integrity()
        return _MESSAGE_BY_STATE[self.state]

    def evidence_summary(self) -> dict:
        """Return a one-way, safe summary. It is not a reconstruction format."""
        if self.state is OperationalState.RECOVERY_PENDING:
            self._assert_recovery_binding()
        else:
            self._assert_integrity()
        return {
            "provider": self.identity.provider,
            "route": self.identity.route,
            "owner_scope": self.identity.owner_scope,
            "state": self.state.value,
            "may_use_as_current": self.may_use_as_current,
            "may_show_stale_context": self.may_show_stale_context,
            "customer_action": self.customer_action.value,
            "customer_message_key": self.customer_message_key.value,
            "observed_at": _iso(self.observed_at),
            "retrieved_at": _iso(self.retrieved_at),
            "last_verified_at": _iso(self.last_verified_at),
            "last_transition_at": _iso(self.last_transition_at),
            "last_accepted_observed_at": _iso(self.last_accepted_observed_at),
            "required_fields_validated": self.required_fields_validated,
        }

    def __repr__(self) -> str:
        try:
            return (
                "EvidenceRouteStatus("
                f"identity={self.identity!r}, state={self.state.value!r}, "
                f"may_use_as_current={self.may_use_as_current}, "
                f"may_show_stale_context={self.may_show_stale_context}, "
                f"customer_action={self.customer_action.value!r}, "
                f"customer_message_key={self.customer_message_key.value!r}, "
                f"observed_at={_iso(self.observed_at)!r}, "
                f"retrieved_at={_iso(self.retrieved_at)!r}, "
                f"last_verified_at={_iso(self.last_verified_at)!r}, "
                f"required_fields_validated={self.required_fields_validated})"
            )
        except Exception:
            return "EvidenceRouteStatus([INVALID])"

    def __copy__(self) -> "EvidenceRouteStatus":
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> "EvidenceRouteStatus":
        memo[id(self)] = self
        return self

    def __reduce__(self) -> object:
        _reject_serialisation()
        return ()


def classify_outage(
    *,
    identity: EvidenceRouteIdentity,
    event: OutageEvent,
    occurred_at: datetime,
    prior: EvidenceRouteStatus | None = None,
) -> EvidenceRouteStatus:
    """Classify one outage event into a degraded route status.

    ``occurred_at`` is when the outage was observed. A late or repeated event
    (one not newer than the existing verified watermark) is rejected rather than
    allowed to overwrite a newer verified state.
    """
    if type(identity) is not EvidenceRouteIdentity:
        raise OperationalResilienceError("identity must be an EvidenceRouteIdentity")
    identity._assert_integrity()
    if type(event) is not OutageEvent:
        raise OperationalResilienceError("event must be an OutageEvent")
    occurred = _aware_utc(occurred_at, "occurred_at")
    if occurred is None:
        raise OperationalResilienceError("occurred_at is required")

    if prior is not None:
        if type(prior) is not EvidenceRouteStatus:
            raise OperationalResilienceError("prior must be an EvidenceRouteStatus")
        if prior.state is OperationalState.RECOVERY_PENDING:
            prior._assert_recovery_binding()
        else:
            prior._assert_integrity()
        if prior.identity != identity:
            raise OperationalResilienceError(
                "outage event does not match the prior evidence route"
            )
        watermark = max(
            value
            for value in (
                prior.last_verified_at,
                prior.last_transition_at,
                prior.retrieved_at,
            )
            if value is not None
        ) if any(
            value is not None
            for value in (
                prior.last_verified_at,
                prior.last_transition_at,
                prior.retrieved_at,
            )
        ) else None
        if watermark is not None and occurred <= watermark:
            raise OperationalResilienceError(
                "outage event is not newer than the existing verified state"
            )

    target_state = _EVENT_STATE[event]

    if event is OutageEvent.EVIDENCE_STALE:
        if prior is None:
            raise OperationalResilienceError(
                "stale evidence requires a prior verified observation"
            )
        if (
            prior.observed_at is None
            or prior.retrieved_at is None
            or prior.last_verified_at is None
        ):
            raise OperationalResilienceError(
                "stale evidence requires a prior verified observation with timestamps"
            )
        return EvidenceRouteStatus(
            identity=identity,
            state=OperationalState.STALE,
            observed_at=prior.observed_at,
            retrieved_at=prior.retrieved_at,
            last_verified_at=prior.last_verified_at,
            required_fields_validated=True,
            last_transition_at=occurred,
            last_accepted_observed_at=prior.last_accepted_observed_at,
        )

    return EvidenceRouteStatus(
        identity=identity,
        state=target_state,
        observed_at=None,
        retrieved_at=None,
        last_verified_at=prior.last_verified_at if prior is not None else None,
        required_fields_validated=False,
        last_transition_at=occurred,
        last_accepted_observed_at=(
            prior.last_accepted_observed_at if prior is not None else None
        ),
    )


def begin_recovery(
    *,
    current: EvidenceRouteStatus,
    observation: RecoveryObservation,
    now: datetime | None = None,
) -> EvidenceRouteStatus:
    """Receive a fresh observation for the route's current identity.

    The observation must belong to exactly the same route and must be newer than
    the existing verified watermark. This returns ``RECOVERY_PENDING``; it never
    returns ``AVAILABLE``.
    """
    if type(current) is not EvidenceRouteStatus:
        raise OperationalResilienceError("current must be an EvidenceRouteStatus")
    current._assert_integrity()
    if current.state not in _RECOVERABLE_STATES:
        raise OperationalResilienceError(
            "recovery may begin only from a validated degraded route state"
        )
    if type(observation) is not RecoveryObservation:
        raise OperationalResilienceError("observation must be a RecoveryObservation")
    observation._assert_integrity()
    if observation.identity != current.identity:
        raise OperationalResilienceError(
            "recovery observation does not match the evidence route"
        )

    reference_now = _aware_utc(now if now is not None else datetime.now(timezone.utc), "now")
    if reference_now is None:
        raise OperationalResilienceError("now is required")
    if observation.observed_at > reference_now or observation.retrieved_at > reference_now:
        raise OperationalResilienceError(
            "recovery observation timestamps must not be in the future"
        )

    watermark = max(
        value
        for value in (
            current.last_verified_at,
            current.last_transition_at,
            current.retrieved_at,
        )
        if value is not None
    ) if any(
        value is not None
        for value in (
            current.last_verified_at,
            current.last_transition_at,
            current.retrieved_at,
        )
    ) else None
    if watermark is not None and observation.retrieved_at <= watermark:
        raise OperationalResilienceError(
            "recovery observation is not newer than the existing verified state"
        )
    if (
        current.last_accepted_observed_at is not None
        and observation.observed_at <= current.last_accepted_observed_at
    ):
        raise OperationalResilienceError(
            "recovery observation is not newer than the last accepted observation"
        )

    pending = EvidenceRouteStatus(
        identity=current.identity,
        state=OperationalState.RECOVERY_PENDING,
        observed_at=observation.observed_at,
        retrieved_at=observation.retrieved_at,
        last_verified_at=current.last_verified_at,
        required_fields_validated=False,
        last_transition_at=current.last_transition_at,
        last_accepted_observed_at=current.last_accepted_observed_at,
    )
    object.__setattr__(
        pending,
        "_recovery_binding",
        (_RECOVERY_AUTHORITY, current._status_binding, observation._observation_binding),
    )
    return pending


def complete_recovery(
    *,
    pending: EvidenceRouteStatus,
    required_fields_validated: bool,
    schema_compatible: bool,
    verified_at: datetime,
    now: datetime | None = None,
) -> EvidenceRouteStatus:
    """Verify a pending recovery and, only if valid, restore ``AVAILABLE``.

    A non-compatible schema or invalid required fields degrade rather than
    recover; a status flag alone is never sufficient.
    """
    if type(pending) is not EvidenceRouteStatus:
        raise OperationalResilienceError("pending must be an EvidenceRouteStatus")
    pending._assert_recovery_binding()
    if pending.state is not OperationalState.RECOVERY_PENDING:
        raise OperationalResilienceError(
            "recovery completion requires a pending recovery state"
        )
    if type(required_fields_validated) is not bool:
        raise OperationalResilienceError("required_fields_validated must be a boolean")
    if type(schema_compatible) is not bool:
        raise OperationalResilienceError("schema_compatible must be a boolean")
    verified = _aware_utc(verified_at, "verified_at")
    if verified is None:
        raise OperationalResilienceError("verified_at is required")
    reference_now = _aware_utc(now if now is not None else datetime.now(timezone.utc), "now")
    if reference_now is None:
        raise OperationalResilienceError("now is required")
    if verified > reference_now:
        raise OperationalResilienceError("verified_at must not be in the future")
    if pending.retrieved_at is None or verified < pending.retrieved_at:
        raise OperationalResilienceError("verified_at must not precede retrieval")

    if not schema_compatible:
        return EvidenceRouteStatus(
            identity=pending.identity,
            state=OperationalState.SCHEMA_INCOMPATIBLE,
            observed_at=None,
            retrieved_at=None,
            last_verified_at=pending.last_verified_at,
            required_fields_validated=False,
            last_transition_at=verified,
            last_accepted_observed_at=pending.last_accepted_observed_at,
        )
    if not required_fields_validated:
        return EvidenceRouteStatus(
            identity=pending.identity,
            state=OperationalState.EVIDENCE_INADEQUATE,
            observed_at=None,
            retrieved_at=None,
            last_verified_at=pending.last_verified_at,
            required_fields_validated=False,
            last_transition_at=verified,
            last_accepted_observed_at=pending.last_accepted_observed_at,
        )
    return EvidenceRouteStatus(
        identity=pending.identity,
        state=OperationalState.AVAILABLE,
        observed_at=pending.observed_at,
        retrieved_at=pending.retrieved_at,
        last_verified_at=verified,
        required_fields_validated=True,
        last_transition_at=verified,
        last_accepted_observed_at=pending.observed_at,
    )
