"""Owner-bound, provider-neutral presentation of operational route status.

The template is loaded once at import.  The supported operation is pure and
performs no request-time filesystem, network, persistence, or provider work.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from reserved.providers.operational_resilience import (
    CustomerAction,
    CustomerMessage,
    EvidenceRouteIdentity,
    EvidenceRouteStatus,
    OperationalState,
)


_CLOSED_MODEL = (
    "Service unavailable",
    "We cannot show this information right now.",
    "No action is available here.",
)

_COPY_BY_STATE = {
    OperationalState.TEMPORARILY_UNAVAILABLE: (
        CustomerMessage.TEMPORARILY_UNAVAILABLE,
        CustomerAction.RETRY_LATER,
        "Information temporarily unavailable",
        "This information is not currently available.",
        "Please try again later.",
    ),
    OperationalState.AUTHORISATION_REQUIRED: (
        CustomerMessage.RECONNECT_REQUIRED,
        CustomerAction.RECONNECT,
        "Connection needs attention",
        "This information is not current because the connection needs attention.",
        "Please reconnect your account to continue.",
    ),
    OperationalState.SCHEMA_INCOMPATIBLE: (
        CustomerMessage.DATA_FORMAT_CHANGED,
        CustomerAction.NONE,
        "Information temporarily unavailable",
        "This information is not current because its format has changed.",
        "You do not need to do anything right now.",
    ),
    OperationalState.EVIDENCE_INADEQUATE: (
        CustomerMessage.INFORMATION_INCOMPLETE,
        CustomerAction.PROVIDE_EVIDENCE,
        "More information needed",
        "This information is incomplete and cannot be used as current.",
        "Please provide the required information.",
    ),
    OperationalState.STALE: (
        CustomerMessage.INFORMATION_OUT_OF_DATE,
        CustomerAction.REFRESH,
        "Information out of date",
        "The retained information is out of date and cannot be used as current.",
        "Please refresh your information.",
    ),
    OperationalState.RECOVERY_PENDING: (
        CustomerMessage.RECOVERY_IN_PROGRESS,
        CustomerAction.NONE,
        "Information update in progress",
        "Refreshed information is still being checked and is not yet usable.",
        "You do not need to do anything right now.",
    ),
}


def _bind_supported_renderer(
    *,
    status_type: type = EvidenceRouteStatus,
    identity_type: type = EvidenceRouteIdentity,
    state_type: type = OperationalState,
    message_type: type = CustomerMessage,
    action_type: type = CustomerAction,
    copy_by_state: dict = _COPY_BY_STATE,
    closed_model: tuple[str, str, str] = _CLOSED_MODEL,
    environment_type: type = Environment,
    loader_type: type = FileSystemLoader,
    autoescape_selector: object = select_autoescape,
    datetime_type: type = datetime,
    template_root: Path = Path(__file__).resolve().parents[1] / "templates",
):
    """Capture every collaborator before public module globals can be rebound."""
    canonical = tuple(
        (state, message, action, heading, body, guidance)
        for state, (message, action, heading, body, guidance) in copy_by_state.items()
    )
    environment = environment_type(
        loader=loader_type(template_root),
        autoescape=autoescape_selector(("html",)),  # type: ignore[operator]
    )
    template = environment.get_template("v2/_provider_outage_status.html")
    closed_html = template.render(model=closed_model)
    safe_identifier_characters = frozenset(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-"
    )

    def exact_identifier(value: object, *, nullable: bool = False) -> bool:
        if nullable and value is None:
            return True
        return (
            type(value) is str
            and 1 <= len(value) <= 160
            and all(character in safe_identifier_characters for character in value)
        )

    def exact_timestamp(value: object) -> bool:
        return value is None or type(value) is datetime_type

    def exact_identity_binding(binding: object, identity: object) -> bool:
        if type(binding) is not tuple or len(binding) != 3:
            return False
        provider = object.__getattribute__(identity, "provider")
        route = object.__getattribute__(identity, "route")
        owner = object.__getattribute__(identity, "owner_scope")
        return (
            exact_identifier(provider)
            and exact_identifier(route)
            and exact_identifier(owner, nullable=True)
            and exact_identifier(binding[0])
            and exact_identifier(binding[1])
            and exact_identifier(binding[2], nullable=True)
            and binding[0] == provider
            and binding[1] == route
            and (
                binding[2] is None
                if owner is None
                else binding[2] is not None and binding[2] == owner
            )
        )

    def exact_status_binding(binding: object, identity: object) -> bool:
        if type(binding) is not tuple or len(binding) != 8:
            return False
        identity_binding = object.__getattribute__(identity, "_identity_binding")
        state = binding[1]
        return (
            exact_identity_binding(identity_binding, identity)
            and exact_identity_binding(binding[0], identity)
            and type(state) is state_type
            and all(exact_timestamp(binding[index]) for index in (2, 3, 4, 6, 7))
            and type(binding[5]) is bool
            and all(
                left == right
                for left, right in zip(binding[0], identity_binding)
                if left is not None and right is not None
            )
            and all(
                left is right
                for left, right in zip(binding[0], identity_binding)
                if left is None or right is None
            )
        )

    def exact_current_status(status: object, identity: object, state: object) -> bool:
        binding = object.__getattribute__(status, "_status_binding")
        fields = (
            object.__getattribute__(status, "observed_at"),
            object.__getattribute__(status, "retrieved_at"),
            object.__getattribute__(status, "last_verified_at"),
            object.__getattribute__(status, "required_fields_validated"),
            object.__getattribute__(status, "last_transition_at"),
            object.__getattribute__(status, "last_accepted_observed_at"),
        )
        if not exact_status_binding(binding, identity):
            return False
        return (
            binding[1] is state
            and all(exact_timestamp(fields[index]) for index in (0, 1, 2, 4, 5))
            and type(fields[3]) is bool
            and all(binding[index] == fields[index - 2] for index in (2, 3, 4, 6, 7))
            and binding[5] is fields[3]
        )

    def exact_recovery_binding(status: object, identity: object) -> bool:
        recovery = object.__getattribute__(status, "_recovery_binding")
        if type(recovery) is not tuple or len(recovery) != 3:
            return False
        current, observation = recovery[1], recovery[2]
        if not exact_status_binding(current, identity):
            return False
        if type(observation) is not tuple or len(observation) != 3:
            return False
        if not exact_identity_binding(observation[0], identity):
            return False
        if type(observation[1]) is not datetime_type or type(observation[2]) is not datetime_type:
            return False
        identity_binding = object.__getattribute__(identity, "_identity_binding")
        observed = object.__getattribute__(status, "observed_at")
        retrieved = object.__getattribute__(status, "retrieved_at")
        verified = object.__getattribute__(status, "last_verified_at")
        transitioned = object.__getattribute__(status, "last_transition_at")
        accepted = object.__getattribute__(status, "last_accepted_observed_at")
        return (
            all(left == right for left, right in zip(current[0], identity_binding))
            and all(left == right for left, right in zip(observation[0], identity_binding))
            and observation[1] == observed
            and observation[2] == retrieved
            and current[4] == verified
            and current[6] == transitioned
            and current[7] == accepted
        )

    def render_provider_outage_status(status: object, owner_scope: object) -> str:
        """Return deterministic HTML only for an intact, exactly owner-bound status."""
        try:
            if type(status) is not status_type or type(owner_scope) is not str:
                return closed_html
            if not owner_scope:
                return closed_html
            identity = object.__getattribute__(status, "identity")
            if type(identity) is not identity_type:
                return closed_html
            identity_binding = object.__getattribute__(identity, "_identity_binding")
            if not exact_identity_binding(identity_binding, identity):
                return closed_html
            bound_owner = object.__getattribute__(identity, "owner_scope")
            if not exact_identifier(bound_owner) or owner_scope != bound_owner:
                return closed_html
            state = object.__getattribute__(status, "state")
            if type(state) is not state_type:
                return closed_html
            if not exact_current_status(status, identity, state):
                return closed_html
            if state is state_type.RECOVERY_PENDING:
                if not exact_recovery_binding(status, identity):
                    return closed_html
                status_type._assert_recovery_binding(status)
            else:
                status_type._assert_integrity(status)
            may_use = status_type.may_use_as_current.fget(status)
            message = status_type.customer_message_key.fget(status)
            action = status_type.customer_action.fget(status)
            if type(may_use) is not bool or type(message) is not message_type or type(action) is not action_type:
                return closed_html
            if state is state_type.AVAILABLE:
                return "" if may_use is True and message is message_type.AVAILABLE and action is action_type.NONE else closed_html
            if may_use is not False:
                return closed_html
            for expected_state, expected_message, expected_action, heading, body, guidance in canonical:
                if state is expected_state:
                    if message is not expected_message or action is not expected_action:
                        return closed_html
                    return template.render(model=(heading, body, guidance))
            return closed_html
        except Exception:
            return closed_html

    return render_provider_outage_status


render_provider_outage_status = _bind_supported_renderer()

__all__ = ("render_provider_outage_status",)
