"""Detached, zero-authority W10-S6F cancellation copy candidate.

The module validates exact structural facts about a cancellation already
verified elsewhere and emits fixed, recursively detached customer copy.  It
does not authenticate those facts, decide entitlement, contact a provider,
persist, render, deliver, notify, refund, cancel, or activate anything.
"""

from __future__ import annotations

import re as _re_module
from datetime import datetime as _datetime_type


FACTS_VERSION = "reserved-w10-cancellation-structural-facts/1.0"
PRESENTATION_VERSION = "reserved-w10-cancellation-presentation/1.0"


def _build_cancellation_presenter():
    """Capture the complete fixed structural contract without admission."""

    _type = type
    _tuple = tuple
    _dict = dict
    _set = set
    _len = len
    _str = str
    _bool = bool
    _any = any
    _ord = ord
    _TypeError = TypeError
    _ValueError = ValueError
    _datetime = _datetime_type
    _fullmatch = _re_module.fullmatch
    _facts_version = FACTS_VERSION
    _presentation_version = PRESENTATION_VERSION
    _timestamp_pattern = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
    _months = (
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    )
    _fact_keys = (
        "schema_version",
        "owner_reference",
        "billing_account_reference",
        "subscription_reference",
        "state",
        "future_renewal_stopped",
        "paid_period_started_at_utc",
        "cancellation_verified_at_utc",
        "paid_through_exclusive_utc",
        "cancellation_effective_at_utc",
        "evaluated_at_utc",
    )
    _copy_keys = (
        "heading",
        "summary",
        "renewal_message",
        "paid_period_message",
        "paid_through_label",
        "paid_through_display",
        "paid_through_exclusive_utc",
        "boundary_message",
        "rights_message",
    )
    _authority_keys = (
        "upstream_admission_authority",
        "customer_render_authority",
        "delivery_authority",
        "notification_authority",
        "entitlement_authority",
        "access_decision_authority",
        "provider_authority",
        "cancellation_authority",
        "refund_authority",
        "persistence_authority",
        "activation_authority",
    )
    _presentation_keys = (
        "schema_version",
        "classification",
        "kind",
        "copy",
        "authority",
    )

    def _detach(value):
        if _type(value) is _tuple:
            return _tuple(_detach(item) for item in value)
        if _type(value) in (_str, _bool):
            return value
        raise _ValueError("presentation contains a non-exact built-in value")

    def _parse_timestamp(value, field_name):
        if _type(value) is not _str or _fullmatch(_timestamp_pattern, value) is None:
            raise _ValueError(f"{field_name} must be an exact UTC second timestamp")
        try:
            parsed = _datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as error:
            raise _ValueError(f"{field_name} is not a valid UTC timestamp") from error
        if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
            raise _ValueError(f"{field_name} is not canonical")
        return parsed

    def _validate_reference(value, field_name):
        if _type(value) is not _str or not value or _len(value) > 160:
            raise _ValueError(f"{field_name} must be a bounded exact string")
        if _any(_ord(character) < 33 or _ord(character) == 127 for character in value):
            raise _ValueError(f"{field_name} contains unsupported characters")
        return value

    def _format_timestamp(value):
        if _type(value) is not _datetime:
            raise _ValueError("paid-through boundary must be an exact parsed timestamp")
        return (
            f"{value.day} {_months[value.month]} {value.year} "
            f"at {value.hour:02d}:{value.minute:02d}:{value.second:02d} UTC"
        )

    def _copy_for_boundary(boundary):
        display = _format_timestamp(boundary)
        return (
            ("heading", "Your subscription will not renew"),
            (
                "summary",
                "Your cancellation has been recorded for the end of your current paid period.",
            ),
            ("renewal_message", "Future automatic renewals are stopped."),
            (
                "paid_period_message",
                (
                    "Subject to Reserved's entitlement checks, you can continue using "
                    f"Reserved before {display} under your already-paid period."
                ),
            ),
            ("paid_through_label", "Already-paid period ends at"),
            ("paid_through_display", display),
            ("paid_through_exclusive_utc", boundary.strftime("%Y-%m-%dT%H:%M:%SZ")),
            (
                "boundary_message",
                (
                    f"Starting {display}, this message does not promise or grant access. "
                    "Reserved's entitlement policy determines access."
                ),
            ),
            (
                "rights_message",
                "This does not affect any mandatory consumer or statutory rights.",
            ),
        )

    def _authority_projection():
        return _tuple((key, False) for key in _authority_keys)

    def _validate_facts(value, expected_owner_reference, expected_subscription_reference):
        if _type(value) is not _dict or _tuple(value) != _fact_keys:
            raise _TypeError("facts must be an exact ordered structural-facts dictionary")
        value = _dict(value)
        expected_owner_reference = _validate_reference(
            expected_owner_reference, "expected_owner_reference"
        )
        expected_subscription_reference = _validate_reference(
            expected_subscription_reference, "expected_subscription_reference"
        )
        if (
            _type(value["schema_version"]) is not _str
            or value["schema_version"] != _facts_version
        ):
            raise _ValueError("unsupported cancellation structural-facts version")
        for name in (
            "owner_reference",
            "billing_account_reference",
            "subscription_reference",
        ):
            _validate_reference(value[name], name)
        if value["owner_reference"] != expected_owner_reference:
            raise _ValueError("structural owner does not match the expected owner")
        if value["subscription_reference"] != expected_subscription_reference:
            raise _ValueError(
                "structural subscription does not match the expected subscription"
            )
        if (
            _type(value["state"]) is not _str
            or value["state"] != "cancellation_confirmed_end_of_paid_period"
        ):
            raise _ValueError("structural cancellation state is unsupported")
        if (
            _type(value["future_renewal_stopped"]) is not _bool
            or value["future_renewal_stopped"] is not True
        ):
            raise _ValueError("future_renewal_stopped must be exact true")

        paid_start = _parse_timestamp(
            value["paid_period_started_at_utc"], "paid_period_started_at_utc"
        )
        verified = _parse_timestamp(
            value["cancellation_verified_at_utc"], "cancellation_verified_at_utc"
        )
        paid_through = _parse_timestamp(
            value["paid_through_exclusive_utc"], "paid_through_exclusive_utc"
        )
        effective = _parse_timestamp(
            value["cancellation_effective_at_utc"], "cancellation_effective_at_utc"
        )
        evaluated = _parse_timestamp(value["evaluated_at_utc"], "evaluated_at_utc")
        if not paid_start < paid_through:
            raise _ValueError("paid period is contradictory")
        if effective != paid_through:
            raise _ValueError(
                "cancellation effective boundary must equal paid-through boundary"
            )
        if not paid_start <= verified < paid_through:
            raise _ValueError("cancellation verification is outside the paid period")
        if not verified <= evaluated < paid_through:
            raise _ValueError("cancellation presentation facts are stale or not effective")
        return paid_through

    def build_cancellation_presentation(*args, **kwargs):
        if args or _type(kwargs) is not _dict or _set(kwargs) != {
            "facts",
            "expected_owner_reference",
            "expected_subscription_reference",
        }:
            raise _TypeError(
                "facts, expected_owner_reference and expected_subscription_reference "
                "must be supplied by exact keyword"
            )
        boundary = _validate_facts(
            kwargs["facts"],
            kwargs["expected_owner_reference"],
            kwargs["expected_subscription_reference"],
        )
        return _detach(
            (
                ("schema_version", _presentation_version),
                ("classification", "detached_zero_authority_copy_candidate"),
                ("kind", "cancellation_at_paid_period_end"),
                ("copy", _copy_for_boundary(boundary)),
                ("authority", _authority_projection()),
            )
        )

    def _validate_pairs(value, expected_keys, label):
        if _type(value) is not _tuple or _len(value) != _len(expected_keys):
            raise _ValueError(f"{label} has an invalid shape")
        for pair in value:
            if (
                _type(pair) is not _tuple
                or _len(pair) != 2
                or _type(pair[0]) is not _str
            ):
                raise _ValueError(f"{label} contains an invalid field")
        if _tuple(pair[0] for pair in value) != expected_keys:
            raise _ValueError(f"{label} fields are inconsistent")
        return _dict(value)

    def validate_cancellation_presentation(value):
        detached = _detach(value)
        top = _validate_pairs(detached, _presentation_keys, "presentation")
        if top["schema_version"] != _presentation_version:
            raise _ValueError("unsupported cancellation presentation version")
        if top["classification"] != "detached_zero_authority_copy_candidate":
            raise _ValueError("presentation classification is not zero authority")
        if top["kind"] != "cancellation_at_paid_period_end":
            raise _ValueError("presentation kind is not cancellation at paid-period end")
        copy_values = _validate_pairs(top["copy"], _copy_keys, "presentation copy")
        boundary = _parse_timestamp(
            copy_values["paid_through_exclusive_utc"],
            "paid_through_exclusive_utc",
        )
        if top["copy"] != _copy_for_boundary(boundary):
            raise _ValueError("cancellation presentation copy is inconsistent")
        authority = _validate_pairs(top["authority"], _authority_keys, "authority")
        if _any(_type(item) is not _bool or item for item in authority.values()):
            raise _ValueError("every presentation authority must remain exact false")
        return detached

    def project_cancellation_presentation(value):
        return _detach(validate_cancellation_presentation(value))

    def copy_cancellation_presentation(value):
        return _detach(validate_cancellation_presentation(value))

    return (
        build_cancellation_presentation,
        validate_cancellation_presentation,
        project_cancellation_presentation,
        copy_cancellation_presentation,
    )


(
    build_cancellation_presentation,
    validate_cancellation_presentation,
    project_cancellation_presentation,
    copy_cancellation_presentation,
) = _build_cancellation_presenter()


__all__ = (
    "FACTS_VERSION",
    "PRESENTATION_VERSION",
    "build_cancellation_presentation",
    "copy_cancellation_presentation",
    "project_cancellation_presentation",
    "validate_cancellation_presentation",
)
