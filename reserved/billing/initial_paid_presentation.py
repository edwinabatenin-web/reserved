"""Detached, zero-authority W10-S6H initial-paid copy candidate.

The functions in this module validate caller-supplied structural facts only.
They do not authenticate or admit those facts, contact a provider, grant
entitlement or access, render or deliver copy, persist state, or activate
billing.
"""

from __future__ import annotations

import re as _re_module
from datetime import datetime as _datetime_type
from datetime import timedelta as _timedelta_type


FACTS_VERSION = "reserved-w10-initial-paid-structural-facts/1.0"
PRESENTATION_VERSION = "reserved-w10-initial-paid-presentation/1.0"
STRUCTURAL_FRESHNESS_SECONDS = 300


def _build_initial_paid_presenter():
    """Capture fixed validation and copy without retaining caller input."""

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

    _facts_version = "reserved-w10-initial-paid-structural-facts/1.0"
    _presentation_version = "reserved-w10-initial-paid-presentation/1.0"
    _freshness = _timedelta(seconds=300)
    _timestamp_pattern = r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
    _fact_keys = (
        "schema_version",
        "owner_reference",
        "subscription_reference",
        "plan_reference",
        "state",
        "successful_payment_observation_reconciled",
        "canonical_entitlement_state_observed",
        "renews_automatically",
        "payment_verified_at_utc",
        "entitlement_effective_at_utc",
        "paid_through_exclusive_utc",
        "next_renewal_at_utc",
        "evaluated_at_utc",
    )
    _reference_keys = (
        "owner_reference",
        "subscription_reference",
        "plan_reference",
    )
    _confirmation_keys = (
        "successful_payment_observation_reconciled",
        "canonical_entitlement_state_observed",
        "renews_automatically",
    )
    _copy_keys = (
        "heading",
        "summary",
        "renewal_message",
        "renewal_boundary_label",
        "renewal_boundary_display",
        "paid_through_exclusive_utc",
        "access_message",
        "renewal_caveat",
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
        "fact_status",
        "payment_verified_at_utc",
        "entitlement_effective_at_utc",
        "paid_through_exclusive_utc",
        "next_renewal_at_utc",
        "evaluated_at_utc",
        "structural_references",
        "structural_confirmations",
        "copy",
        "authority",
    )
    _classification = "detached_zero_authority_copy_candidate"
    _kind = "initial_payment_verified_paid"
    _fact_status = "unauthenticated_structural_facts_only"
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

    def _format_timestamp(value):
        if _type(value) is not _datetime:
            raise _ValueError("renewal boundary must be an exact parsed timestamp")
        return (
            f"{value.day} {_months[value.month]} {value.year} "
            f"at {value.hour:02d}:{value.minute:02d}:{value.second:02d} UTC"
        )

    def _copy_for_boundary(paid_through):
        boundary = _format_timestamp(paid_through)
        return (
            ("heading", "Your subscription payment is verified"),
            ("summary", "Your paid subscription has started."),
            (
                "renewal_message",
                f"Your selected plan is set to renew automatically at {boundary}.",
            ),
            ("renewal_boundary_label", "Next renewal boundary"),
            ("renewal_boundary_display", boundary),
            (
                "paid_through_exclusive_utc",
                paid_through.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ),
            (
                "access_message",
                "Access remains subject to Reserved's entitlement checks.",
            ),
            (
                "renewal_caveat",
                "Automatic renewal does not guarantee that a future payment will succeed.",
            ),
        )

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
            raise _ValueError("unsupported initial-paid structural-facts version")
        if _type(value["state"]) is not _str or value["state"] != _kind:
            raise _ValueError("structural state must be exactly initial_payment_verified_paid")
        for key in _confirmation_keys:
            if _type(value[key]) is not _bool or value[key] is not True:
                raise _ValueError(f"{key} must be exact true structural evidence")

        verified = _parse_timestamp(
            value["payment_verified_at_utc"], "payment_verified_at_utc"
        )
        effective = _parse_timestamp(
            value["entitlement_effective_at_utc"], "entitlement_effective_at_utc"
        )
        paid_through = _parse_timestamp(
            value["paid_through_exclusive_utc"], "paid_through_exclusive_utc"
        )
        next_renewal = _parse_timestamp(
            value["next_renewal_at_utc"], "next_renewal_at_utc"
        )
        evaluated = _parse_timestamp(value["evaluated_at_utc"], "evaluated_at_utc")
        if not verified <= effective <= evaluated:
            raise _ValueError("verified, effective and evaluated facts are out of order")
        if evaluated - verified >= _freshness:
            raise _ValueError("initial-paid structural facts are stale")
        if not evaluated < paid_through:
            raise _ValueError("paid-through boundary must be exact and future")
        if next_renewal != paid_through:
            raise _ValueError(
                "next-renewal and paid-through boundaries must match exactly"
            )
        references = _tuple((key, value[key]) for key in _reference_keys)
        confirmations = _tuple((key, value[key]) for key in _confirmation_keys)
        return (
            references,
            confirmations,
            value["payment_verified_at_utc"],
            value["entitlement_effective_at_utc"],
            value["paid_through_exclusive_utc"],
            value["next_renewal_at_utc"],
            value["evaluated_at_utc"],
            paid_through,
            next_renewal,
        )

    def build_initial_paid_presentation(*args, **kwargs):
        expected_names = {
            "facts",
            "expected_owner_reference",
            "expected_subscription_reference",
            "expected_plan_reference",
        }
        if args or _type(kwargs) is not _dict or _set(kwargs) != expected_names:
            raise _TypeError("facts and all expected references require exact keywords")
        (
            references,
            confirmations,
            verified_at,
            effective_at,
            paid_through_at,
            next_renewal_at,
            evaluated_at,
            paid_through,
            next_renewal,
        ) = _validate_facts(
            kwargs["facts"],
            kwargs["expected_owner_reference"],
            kwargs["expected_subscription_reference"],
            kwargs["expected_plan_reference"],
        )
        return _detach(
            (
                ("schema_version", _presentation_version),
                ("classification", _classification),
                ("kind", _kind),
                ("fact_status", _fact_status),
                ("payment_verified_at_utc", verified_at),
                ("entitlement_effective_at_utc", effective_at),
                ("paid_through_exclusive_utc", paid_through_at),
                ("next_renewal_at_utc", next_renewal_at),
                ("evaluated_at_utc", evaluated_at),
                ("structural_references", references),
                ("structural_confirmations", confirmations),
                ("copy", _copy_for_boundary(next_renewal)),
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

    def validate_initial_paid_presentation(value):
        detached = _detach(value)
        top = _validate_pairs(detached, _presentation_keys, "presentation")
        if top["schema_version"] != _presentation_version:
            raise _ValueError("unsupported initial-paid presentation version")
        if top["classification"] != _classification:
            raise _ValueError("presentation classification is not zero authority")
        if top["kind"] != _kind:
            raise _ValueError("presentation kind is not initial_payment_verified_paid")
        if top["fact_status"] != _fact_status:
            raise _ValueError("presentation facts must remain explicitly unauthenticated")

        verified = _parse_timestamp(
            top["payment_verified_at_utc"], "payment_verified_at_utc"
        )
        effective = _parse_timestamp(
            top["entitlement_effective_at_utc"], "entitlement_effective_at_utc"
        )
        paid_through = _parse_timestamp(
            top["paid_through_exclusive_utc"], "paid_through_exclusive_utc"
        )
        next_renewal = _parse_timestamp(
            top["next_renewal_at_utc"], "next_renewal_at_utc"
        )
        evaluated = _parse_timestamp(top["evaluated_at_utc"], "evaluated_at_utc")
        if not verified <= effective <= evaluated:
            raise _ValueError("presentation timestamps are out of order")
        if evaluated - verified >= _freshness:
            raise _ValueError("presentation structural freshness is invalid")
        if not evaluated < paid_through:
            raise _ValueError("presentation paid-through boundary is not future")
        if next_renewal != paid_through:
            raise _ValueError(
                "presentation renewal and paid-through boundaries are inconsistent"
            )

        references = _validate_pairs(
            top["structural_references"], _reference_keys, "structural references"
        )
        for key in _reference_keys:
            _validate_reference(references[key], key)
        confirmations = _validate_pairs(
            top["structural_confirmations"],
            _confirmation_keys,
            "structural confirmations",
        )
        if _any(_type(item) is not _bool or item is not True for item in confirmations.values()):
            raise _ValueError("every structural confirmation must remain exact true")
        _validate_pairs(top["copy"], _copy_keys, "presentation copy")
        if top["copy"] != _copy_for_boundary(next_renewal):
            raise _ValueError("initial-paid presentation copy is inconsistent")
        authority = _validate_pairs(top["authority"], _authority_keys, "authority")
        if _any(_type(item) is not _bool or item for item in authority.values()):
            raise _ValueError("every presentation authority must remain exact false")
        return detached

    def project_initial_paid_presentation(value):
        return _detach(validate_initial_paid_presentation(value))

    def copy_initial_paid_presentation(value):
        return _detach(validate_initial_paid_presentation(value))

    return (
        build_initial_paid_presentation,
        validate_initial_paid_presentation,
        project_initial_paid_presentation,
        copy_initial_paid_presentation,
    )


(
    build_initial_paid_presentation,
    validate_initial_paid_presentation,
    project_initial_paid_presentation,
    copy_initial_paid_presentation,
) = _build_initial_paid_presenter()


__all__ = (
    "FACTS_VERSION",
    "PRESENTATION_VERSION",
    "STRUCTURAL_FRESHNESS_SECONDS",
    "build_initial_paid_presentation",
    "copy_initial_paid_presentation",
    "project_initial_paid_presentation",
    "validate_initial_paid_presentation",
)
