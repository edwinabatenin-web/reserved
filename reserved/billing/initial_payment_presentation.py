"""Detached, zero-authority W10-S6G initial-payment copy candidates.

The functions in this module validate only caller-supplied structural facts.
They do not authenticate those facts, contact a provider, render or deliver
customer content, create or retry a charge, grant access, or persist state.
"""

from __future__ import annotations

import re as _re_module
from datetime import datetime as _datetime_type
from datetime import timedelta as _timedelta_type


FACTS_VERSION = "reserved-w10-initial-payment-structural-facts/1.0"
PRESENTATION_VERSION = "reserved-w10-initial-payment-presentation/1.0"
STRUCTURAL_FRESHNESS_SECONDS = 300


def _build_initial_payment_presenter():
    """Capture the complete fixed contract without retaining caller input."""

    _type = type
    _tuple = tuple
    _dict = dict
    _set = set
    _zip = zip
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
    _secret_shape = _re_module.compile(
        r"(?:^|[._:/-])(?:"
        r"(?:sk|rk)[._:/-](?:live|test)|whsec|secret|credential|password|passwd|"
        r"bearer|authorization|api[._:/-]?key|access[._:/-]?token|"
        r"refresh[._:/-]?token|private[._:/-]?key|client[._:/-]?secret|"
        r"endpoint[._:/-]?secret|webhook[._:/-]?secret"
        r")(?:[._:/-]|$)",
        _re_module.IGNORECASE,
    ).search
    _provider_object_shape = _re_module.compile(
        r"^(?:acct|ch|cs|cus|evt|in|pi|pm|price|prod|re|seti|sub)_"
        r"[A-Za-z0-9][A-Za-z0-9._:/-]*$",
        _re_module.IGNORECASE,
    ).fullmatch

    _facts_version = "reserved-w10-initial-payment-structural-facts/1.0"
    _presentation_version = "reserved-w10-initial-payment-presentation/1.0"
    _freshness = _timedelta(seconds=300)
    _timestamp_pattern = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
    _fact_keys = (
        "schema_version",
        "owner_reference",
        "subscription_reference",
        "plan_reference",
        "state",
        "observed_at_utc",
        "evaluated_at_utc",
    )
    _reference_keys = (
        "owner_reference",
        "subscription_reference",
        "plan_reference",
    )
    _copy_keys = (
        "heading",
        "summary",
        "access_message",
        "next_step",
    )
    _authority_keys = (
        "upstream_admission_authority",
        "authentication_authority",
        "customer_render_authority",
        "delivery_authority",
        "notification_authority",
        "entitlement_authority",
        "access_authority",
        "provider_authority",
        "charge_authority",
        "refund_authority",
        "persistence_authority",
        "activation_authority",
    )
    _presentation_keys = (
        "schema_version",
        "classification",
        "kind",
        "verification_status",
        "observed_at_utc",
        "evaluated_at_utc",
        "structural_references",
        "copy",
        "authority",
    )
    _classification = "detached_zero_authority_copy_candidate"
    _states = (
        "initial_payment_pending",
        "initial_payment_failed",
    )
    _verification_statuses = (
        "unverified",
        "failed_verification",
    )
    _copy_by_state = (
        (
            (
                "heading",
                "We are verifying your subscription payment",
            ),
            (
                "summary",
                "Your initial subscription payment is still being verified.",
            ),
            (
                "access_message",
                "Paid access has not started.",
            ),
            (
                "next_step",
                "If you need help while verification is pending, contact support.",
            ),
        ),
        (
            (
                "heading",
                "We could not verify your subscription payment",
            ),
            (
                "summary",
                "Your initial subscription payment could not be verified.",
            ),
            (
                "access_message",
                "Paid access has not started.",
            ),
            (
                "next_step",
                "Contact support if you need help.",
            ),
        ),
    )

    def _detach(value):
        if _type(value) is _tuple:
            return _tuple(_detach(item) for item in value)
        if _type(value) in (_str, _bool):
            return value
        raise _ValueError("presentation contains a non-exact built-in value")

    def _validate_reference(value, field_name):
        if _type(value) is not _str or not value or _len(value) > 160:
            raise _ValueError(f"{field_name} must be a bounded exact string")
        if _any(_ord(character) < 33 or _ord(character) == 127 for character in value):
            raise _ValueError(f"{field_name} contains unsupported characters")
        if _secret_shape(value) is not None:
            raise _ValueError(f"{field_name} must not contain secret-shaped material")
        if _provider_object_shape(value) is not None:
            raise _ValueError(f"{field_name} must not be a provider object identifier")
        return value

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

    def _state_index(state):
        if _type(state) is not _str or state not in _states:
            raise _ValueError("unsupported initial-payment structural state")
        return 0 if state == _states[0] else 1

    def _authority_projection():
        return _tuple((key, False) for key in _authority_keys)

    def _validate_facts(
        value,
        expected_owner_reference,
        expected_subscription_reference,
        expected_plan_reference,
    ):
        if _type(value) is not _dict or _tuple(value) != _fact_keys:
            raise _TypeError("facts must be an exact ordered structural-facts dictionary")
        value = _dict(value)
        expected = (
            expected_owner_reference,
            expected_subscription_reference,
            expected_plan_reference,
        )
        for key, expected_value in _zip(_reference_keys, expected):
            expected_value = _validate_reference(expected_value, f"expected_{key}")
            supplied_value = _validate_reference(value[key], key)
            if supplied_value != expected_value:
                raise _ValueError(f"structural {key} does not match its expectation")
        if (
            _type(value["schema_version"]) is not _str
            or value["schema_version"] != _facts_version
        ):
            raise _ValueError("unsupported initial-payment structural-facts version")
        state_index = _state_index(value["state"])
        observed = _parse_timestamp(value["observed_at_utc"], "observed_at_utc")
        evaluated = _parse_timestamp(value["evaluated_at_utc"], "evaluated_at_utc")
        elapsed = evaluated - observed
        if elapsed < _timedelta(0):
            raise _ValueError("initial-payment structural facts are future or out of order")
        if elapsed >= _freshness:
            raise _ValueError("initial-payment structural facts are stale")
        references = _tuple((key, value[key]) for key in _reference_keys)
        return (
            state_index,
            references,
            value["observed_at_utc"],
            value["evaluated_at_utc"],
        )

    def build_initial_payment_presentation(*args, **kwargs):
        expected_names = {
            "facts",
            "expected_owner_reference",
            "expected_subscription_reference",
            "expected_plan_reference",
        }
        if args or _type(kwargs) is not _dict or _set(kwargs) != expected_names:
            raise _TypeError("facts and all expected references require exact keywords")
        state_index, references, observed_at_utc, evaluated_at_utc = _validate_facts(
            kwargs["facts"],
            kwargs["expected_owner_reference"],
            kwargs["expected_subscription_reference"],
            kwargs["expected_plan_reference"],
        )
        return _detach(
            (
                ("schema_version", _presentation_version),
                ("classification", _classification),
                ("kind", _states[state_index]),
                ("verification_status", _verification_statuses[state_index]),
                ("observed_at_utc", observed_at_utc),
                ("evaluated_at_utc", evaluated_at_utc),
                ("structural_references", references),
                ("copy", _copy_by_state[state_index]),
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

    def validate_initial_payment_presentation(value):
        detached = _detach(value)
        top = _validate_pairs(detached, _presentation_keys, "presentation")
        if top["schema_version"] != _presentation_version:
            raise _ValueError("unsupported initial-payment presentation version")
        if top["classification"] != _classification:
            raise _ValueError("presentation classification is not zero authority")
        state_index = _state_index(top["kind"])
        if top["verification_status"] != _verification_statuses[state_index]:
            raise _ValueError("presentation verification status is inconsistent")
        observed = _parse_timestamp(top["observed_at_utc"], "observed_at_utc")
        evaluated = _parse_timestamp(top["evaluated_at_utc"], "evaluated_at_utc")
        elapsed = evaluated - observed
        if elapsed < _timedelta(0) or elapsed >= _freshness:
            raise _ValueError("presentation structural freshness is invalid")
        references = _validate_pairs(
            top["structural_references"], _reference_keys, "structural references"
        )
        for key in _reference_keys:
            _validate_reference(references[key], key)
        _validate_pairs(top["copy"], _copy_keys, "presentation copy")
        if top["copy"] != _copy_by_state[state_index]:
            raise _ValueError("initial-payment presentation copy is inconsistent")
        authority = _validate_pairs(top["authority"], _authority_keys, "authority")
        if _any(_type(item) is not _bool or item for item in authority.values()):
            raise _ValueError("every presentation authority must remain exact false")
        return detached

    def project_initial_payment_presentation(value):
        return _detach(validate_initial_payment_presentation(value))

    def copy_initial_payment_presentation(value):
        return _detach(validate_initial_payment_presentation(value))

    return (
        build_initial_payment_presentation,
        validate_initial_payment_presentation,
        project_initial_payment_presentation,
        copy_initial_payment_presentation,
    )


(
    build_initial_payment_presentation,
    validate_initial_payment_presentation,
    project_initial_payment_presentation,
    copy_initial_payment_presentation,
) = _build_initial_payment_presenter()


__all__ = (
    "FACTS_VERSION",
    "PRESENTATION_VERSION",
    "STRUCTURAL_FRESHNESS_SECONDS",
    "build_initial_payment_presentation",
    "copy_initial_payment_presentation",
    "project_initial_payment_presentation",
    "validate_initial_payment_presentation",
)
