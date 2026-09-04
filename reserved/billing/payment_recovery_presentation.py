"""Detached, zero-authority W10-S6E payment-recovery copy candidate.

This module validates untrusted structural facts and produces recursively
detached built-in data. It does not admit upstream entitlement evidence or
authorise customer rendering, delivery, notification, access, persistence,
provider activity, or activation.
"""

from __future__ import annotations

import re as _re_module
from datetime import datetime as _datetime_type
from datetime import timedelta as _timedelta_type


FACTS_VERSION = "reserved-w10-payment-recovery-structural-facts/1.0"
PRESENTATION_VERSION = "reserved-w10-payment-recovery-presentation/2.0"


def _build_payment_recovery_presenter():
    """Capture fixed copy and exact structural validation without admission."""

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
    _timedelta = _timedelta_type
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
        "recovery_started_at_utc",
        "recovery_deadline_exclusive_utc",
        "evaluated_at_utc",
    )
    _copy_keys = (
        "heading",
        "summary",
        "access_message",
        "deadline_label",
        "deadline_display",
        "deadline_exclusive_utc",
        "deadline_consequence",
        "verified_recovery_consequence",
    )
    _authority_keys = (
        "upstream_admission_authority",
        "customer_render_authority",
        "delivery_authority",
        "notification_authority",
        "entitlement_authority",
        "provider_authority",
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
            raise _ValueError("deadline must be an exact parsed timestamp")
        return (
            f"{value.day} {_months[value.month]} {value.year} "
            f"at {value.hour:02d}:{value.minute:02d}:{value.second:02d} UTC"
        )

    def _copy_for_deadline(deadline):
        deadline_display = _format_timestamp(deadline)
        return (
            ("heading", "Your subscription payment is being recovered"),
            (
                "summary",
                (
                    "We could not verify your renewal payment. Your subscription "
                    "is in payment recovery."
                ),
            ),
            (
                "access_message",
                (
                    "You can continue using Reserved only before "
                    f"{deadline_display} during this recovery period."
                ),
            ),
            ("deadline_label", "Ordinary access continues before"),
            ("deadline_display", deadline_display),
            ("deadline_exclusive_utc", deadline.strftime("%Y-%m-%dT%H:%M:%SZ")),
            (
                "deadline_consequence",
                (
                    f"Starting {deadline_display}, ordinary access is suspended "
                    "unless payment recovery has been verified."
                ),
            ),
            (
                "verified_recovery_consequence",
                (
                    "If payment recovery is verified, the subscription can "
                    "return to its paid state after reconciliation."
                ),
            ),
        )

    def _authority_projection():
        return _tuple((key, False) for key in _authority_keys)

    def _validate_facts(value, expected_owner_reference):
        if _type(value) is not _dict or _tuple(value) != _fact_keys:
            raise _TypeError("facts must be an exact ordered structural-facts dictionary")
        # Detach the exact built-in input before semantic checks. The caller's
        # dictionary is neither retained nor returned as authority.
        value = _dict(value)
        if _type(expected_owner_reference) is not _str:
            raise _TypeError("expected_owner_reference must be an exact string")
        expected_owner_reference = _validate_reference(
            expected_owner_reference, "expected_owner_reference"
        )
        if (
            _type(value["schema_version"]) is not _str
            or value["schema_version"] != _facts_version
        ):
            raise _ValueError("unsupported payment-recovery structural-facts version")
        for name in (
            "owner_reference",
            "billing_account_reference",
            "subscription_reference",
        ):
            _validate_reference(value[name], name)
        if value["owner_reference"] != expected_owner_reference:
            raise _ValueError("structural owner does not match the expected owner")
        if _type(value["state"]) is not _str or value["state"] != "payment_recovery":
            raise _ValueError("structural state must be exactly payment_recovery")

        started = _parse_timestamp(
            value["recovery_started_at_utc"], "recovery_started_at_utc"
        )
        deadline = _parse_timestamp(
            value["recovery_deadline_exclusive_utc"],
            "recovery_deadline_exclusive_utc",
        )
        evaluated = _parse_timestamp(value["evaluated_at_utc"], "evaluated_at_utc")
        if not started < deadline:
            raise _ValueError("payment-recovery structural window is contradictory")
        if deadline - started != _timedelta(days=7):
            raise _ValueError(
                "payment-recovery structural window must be exactly seven calendar days"
            )
        if not started <= evaluated < deadline:
            raise _ValueError("payment-recovery structural window is stale or not effective")
        return deadline

    def build_payment_recovery_presentation(*args, **kwargs):
        if args or _type(kwargs) is not _dict or _set(kwargs) != {
            "facts",
            "expected_owner_reference",
        }:
            raise _TypeError(
                "facts and expected_owner_reference must be supplied by exact keyword"
            )
        deadline = _validate_facts(
            kwargs["facts"], kwargs["expected_owner_reference"]
        )
        return _detach(
            (
                ("schema_version", _presentation_version),
                ("classification", "detached_zero_authority_copy_candidate"),
                ("kind", "payment_recovery"),
                ("copy", _copy_for_deadline(deadline)),
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

    def validate_payment_recovery_presentation(value):
        detached = _detach(value)
        top = _validate_pairs(detached, _presentation_keys, "presentation")
        if top["schema_version"] != _presentation_version:
            raise _ValueError("unsupported payment-recovery presentation version")
        if top["classification"] != "detached_zero_authority_copy_candidate":
            raise _ValueError("presentation classification is not zero authority")
        if top["kind"] != "payment_recovery":
            raise _ValueError("presentation kind is not payment_recovery")
        copy_values = _validate_pairs(top["copy"], _copy_keys, "presentation copy")
        deadline = _parse_timestamp(
            copy_values["deadline_exclusive_utc"], "deadline_exclusive_utc"
        )
        if top["copy"] != _copy_for_deadline(deadline):
            raise _ValueError("payment-recovery presentation copy is inconsistent")
        authority = _validate_pairs(top["authority"], _authority_keys, "authority")
        if _any(_type(item) is not _bool or item for item in authority.values()):
            raise _ValueError("every presentation authority must remain exact false")
        return detached

    def project_payment_recovery_presentation(value):
        return _detach(validate_payment_recovery_presentation(value))

    def copy_payment_recovery_presentation(value):
        return _detach(validate_payment_recovery_presentation(value))

    return (
        build_payment_recovery_presentation,
        validate_payment_recovery_presentation,
        project_payment_recovery_presentation,
        copy_payment_recovery_presentation,
    )


(
    build_payment_recovery_presentation,
    validate_payment_recovery_presentation,
    project_payment_recovery_presentation,
    copy_payment_recovery_presentation,
) = _build_payment_recovery_presenter()


__all__ = (
    "FACTS_VERSION",
    "PRESENTATION_VERSION",
    "build_payment_recovery_presentation",
    "copy_payment_recovery_presentation",
    "project_payment_recovery_presentation",
    "validate_payment_recovery_presentation",
)
