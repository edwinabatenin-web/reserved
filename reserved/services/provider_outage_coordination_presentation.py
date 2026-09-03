"""Pure customer-safe presentation of coordinated provider outage status.

The supported operation invokes the import-bound W9-S4C coordinator directly
from exact owner-bound route statuses, accepts only its bounded public
projection, and renders a template loaded once at import.  It performs no
request-time filesystem, network, provider, retry, reconnect, persistence,
monitoring, logging, scheduling or route-activation work.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from reserved.services.provider_outage_coordination import (
    ProviderOutageCoordination,
    coordinate_provider_outage,
)


_CLOSED_MODEL = (
    "Service unavailable",
    "We cannot show this information right now.",
    "No action is available here.",
    (),
)

_ACTIONABLE_GUIDANCE = "Follow each applicable step below."
_NO_ACTION_GUIDANCE = "No action is required right now."

# Exact aggregate state/message pairs emitted by W9-S4C.  Copy is fixed here;
# provider text, route data and exception content never enter the template.
_COPY_BY_AGGREGATE = {
    ("temporarily_unavailable", "temporarily_unavailable"): (
        "Information temporarily unavailable",
        "Some information is not currently available.",
    ),
    ("authorisation_required", "reconnect_required"): (
        "Connection needs attention",
        "Some information is not current because a connection needs attention.",
    ),
    ("schema_incompatible", "data_format_changed"): (
        "Information temporarily unavailable",
        "Some information is not current because its format has changed.",
    ),
    ("evidence_inadequate", "information_incomplete"): (
        "More information needed",
        "Some information is incomplete and cannot be used as current.",
    ),
    ("stale", "information_out_of_date"): (
        "Information out of date",
        "Some retained information is out of date and cannot be used as current.",
    ),
    ("recovery_pending", "recovery_in_progress"): (
        "Information update in progress",
        "Refreshed information is still being checked and is not yet usable.",
    ),
}

# The tuple order is the W9-S4C canonical action order with NONE omitted.
_ACTION_COPY = (
    ("retry_later", "Try again later."),
    ("reconnect", "Reconnect the affected account."),
    ("provide_evidence", "Provide the required information."),
    ("refresh", "Refresh your information."),
)


def _bind_renderer(
    *,
    coordinator=coordinate_provider_outage,
    result_type: type = ProviderOutageCoordination,
    copy_by_aggregate: dict = _COPY_BY_AGGREGATE,
    action_copy: tuple = _ACTION_COPY,
    closed_model: tuple = _CLOSED_MODEL,
    actionable_guidance: str = _ACTIONABLE_GUIDANCE,
    no_action_guidance: str = _NO_ACTION_GUIDANCE,
    environment_type: type = Environment,
    loader_type: type = FileSystemLoader,
    autoescape_selector=select_autoescape,
    template_root: Path = Path(__file__).resolve().parents[1] / "templates",
):
    """Capture coordinator, validation surface, vocabulary and template."""

    projection_method = result_type.customer_projection
    aggregate_copy = tuple(
        (state, message, heading, body)
        for (state, message), (heading, body) in copy_by_aggregate.items()
    )
    canonical_actions = tuple(action for action, _copy in action_copy)
    action_text = tuple(action_copy)
    environment = environment_type(
        loader=loader_type(template_root),
        autoescape=autoescape_selector(("html",)),  # type: ignore[operator]
    )
    template = environment.get_template(
        "v2/_provider_outage_coordination_status.html"
    )
    closed_html = template.render(model=tuple(closed_model))

    def render_coordinated_provider_outage_status(
        *, routes: object, owner: object, as_of: object = None
    ) -> str:
        """Render one deterministic aggregate or fixed generic refusal HTML."""

        try:
            result = coordinator(routes=routes, owner=owner, as_of=as_of)
            if type(result) is not result_type:
                return closed_html
            projection = projection_method(result)
            if type(projection) is not dict or set(projection) != {
                "aggregate_state",
                "customer_message_key",
                "customer_actions",
            }:
                return closed_html

            state = projection.get("aggregate_state")
            message = projection.get("customer_message_key")
            actions = projection.get("customer_actions")
            if type(state) is not str or type(message) is not str:
                return closed_html
            if type(actions) is not tuple or any(
                type(action) is not str for action in actions
            ):
                return closed_html
            if len(actions) != len(set(actions)):
                return closed_html
            expected_actions = tuple(
                action for action in canonical_actions if action in actions
            )
            if actions != expected_actions:
                return closed_html

            if state == "available":
                return "" if message == "available" and actions == () else closed_html

            for (
                expected_state,
                expected_message,
                heading,
                body,
            ) in aggregate_copy:
                if state == expected_state:
                    if message != expected_message:
                        return closed_html
                    rendered_actions = tuple(
                        text
                        for action, text in action_text
                        if action in expected_actions
                    )
                    guidance = (
                        actionable_guidance
                        if rendered_actions
                        else no_action_guidance
                    )
                    return template.render(
                        model=(heading, body, guidance, rendered_actions)
                    )
            return closed_html
        except Exception:
            return closed_html

    return render_coordinated_provider_outage_status


render_coordinated_provider_outage_status = _bind_renderer()

__all__ = ("render_coordinated_provider_outage_status",)
