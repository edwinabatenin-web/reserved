"""Disabled-first, provider-neutral W10-S4D offer-configuration contract.

The accepted operating state is an empty offer registry.  This module can form
only an opaque producer-issued handle for a structurally complete future-policy
candidate.  Issuance is retained in the creating process lineage, including a
POSIX-fork child that inherits the live handle and its private integrity seal.
Validation returns a detached immutable primitive projection whose runtime,
provider, price, eligibility, checkout, charge and entitlement authority is
always false.

It does not select an offer, calculate a discount, evaluate a customer, persist
configuration, display a price, call a provider or make a candidate operational.
Reconstruction and serialisation do not preserve producer issuance.  A future
runtime consumer requires separate accepted policy/version authority and is not
implemented here.
"""

from __future__ import annotations

import hashlib as _hashlib_module
import json as _json_module
import re as _re_module
from datetime import datetime as _datetime_type
from datetime import timezone as _timezone_type


def _build_offer_configuration_contract():
    """Build the closure-bound, I/O-free structural contract."""

    _type = type
    _object = object
    _object_new = object.__new__
    _tuple = tuple
    _tuple_new = tuple.__new__
    _dict = dict
    _set = set
    _len = len
    _str = str
    _int = int
    _bool = bool
    _all = all
    _any = any
    _TypeError = TypeError
    _ValueError = ValueError
    _RuntimeError = RuntimeError
    _AttributeError = AttributeError
    _Datetime = _datetime_type
    _UTC = _timezone_type.utc
    _sha256 = _hashlib_module.sha256
    _json_dumps = _json_module.dumps

    _contract_version = "reserved-w10-offer-configuration-contract/1.0"
    _candidate_base_commit = "961168dd5c17fbef7ba96ac1599a7f5888af1db3"
    _candidate_base_tree = "a7788d5d9fd5c11034045694df25eb8681ab86d0"
    _catalogue_authority_version = "FD-W10-001/2026-09-02/v1"
    _candidate_schema = "reserved-offer-configuration-candidate/1.0"
    _provenance_schema = "reserved-offer-policy-provenance/1.0"
    _candidate_status = "unadmitted_offer_configuration_candidate"
    _policy_acceptance_status = "later_accepted_policy_version_authority_required"

    _identifier = _re_module.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$").fullmatch
    _policy_decision_id = _re_module.compile(
        r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+){2,}$"
    ).fullmatch
    _record_reference = _re_module.compile(
        r"^(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+#[A-Za-z0-9_.:-]+$"
    ).fullmatch
    _digest = _re_module.compile(r"^sha256:[0-9a-f]{64}$").fullmatch
    _provider_identifier = _re_module.compile(
        r"(?:^|[^a-z0-9])(?:prod|price|cus|sub|cs|promo|coupon|in|pi|si|il)_"
        r"[a-z0-9]",
        _re_module.IGNORECASE,
    ).search
    _separator = _re_module.compile(r"[._:/-]+").sub
    _non_alphanumeric = _re_module.compile(r"[^A-Za-z0-9]+").sub
    _neutral_account_vocabulary = _re_module.compile(
        r"(?<![A-Za-z0-9])(?:accounting|accountability)(?![A-Za-z0-9])",
        _re_module.IGNORECASE,
    ).sub
    _generic_subject_policy_reference = _re_module.compile(
        r"^docs/(?:customer|user|member)[._-](?:eligibility|access)"
        r"[._-]policy\.md#(?:general|standard)[._:-](?:rule|rules|policy)$",
        _re_module.IGNORECASE,
    ).fullmatch
    _reserved_subject_root = _re_module.compile(
        r"(?:customer|account|member|user|segment)",
        _re_module.IGNORECASE,
    ).search

    _catalogue = (
        ("standard_monthly", 999, "GBP"),
        ("premium_monthly", 1999, "GBP"),
        ("free_tier_under_25", 0, "GBP"),
        ("launch_offer_month_1", 0, "GBP"),
        ("launch_offer_months_2_6", 499, "GBP"),
    )
    _duration_units = ("calendar_days", "calendar_months", "billing_periods")
    _source_bindings = (
        (
            "current_founder_authority",
            "FOUNDER_DECISIONS.md",
            "78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f",
            _candidate_base_commit,
        ),
        (
            "current_completion_map",
            "docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md",
            "c38aa651bcfb617fc5c77cb233d3043815ddc687bf2839cdd506504c4220b939",
            _candidate_base_commit,
        ),
        (
            "accepted_w10_s1_source",
            "reserved/billing/contracts.py",
            "9c5dce7a81652d58562ca339def95fba7cbb2d1c02f965618ebd8f40bcad202b",
            "9e8f94a9906f0c9d5c85b47223d20c34be499e1c",
        ),
        (
            "accepted_w10_s1_tests",
            "tests/test_billing_contracts.py",
            "0344c7e098f20f02fbf91fa43457ec5c24ddd7825f9fc32706103c7652992abf",
            _candidate_base_commit,
        ),
        (
            "accepted_w10_s2b_source",
            "reserved/billing/fail_closed_launch_defaults.py",
            "cd72be19d8180a52f2e09fec56cc3219347059b025ceb3f12086d7d8dde40715",
            "1033c9fbef008dcd33125a0b14e7fb18b8846d19",
        ),
        (
            "accepted_w10_s2b_tests",
            "tests/test_w10_fail_closed_launch_defaults.py",
            "cb40ef6f6d6967e6c99a586a87e49c91bf7c1507acf1c869da3220f3db667dab",
            _candidate_base_commit,
        ),
        (
            "accepted_w10_s4a_source",
            "reserved/billing/stripe_disabled_first_contract.py",
            "87a84c5ec77f25e12667b5466052b4a84ee6e01a6b075df643202d95aec98638",
            "2ad4a63dd1f10ba38859050b47245c28390667d8",
        ),
        (
            "accepted_w10_s4a_tests",
            "tests/test_w10_stripe_disabled_first_contract.py",
            "d032ea88bc7845fa92dc200f60edad4b26324ad97c14d1be78a131a4de2aac11",
            _candidate_base_commit,
        ),
        (
            "accepted_w10_s4b_source",
            "reserved/billing/checkout_intent_contract.py",
            "ff805233b46aabc1f18a1b3def0b849ecd88f6f86e2b5d4b35ae96729b6fb7e0",
            "23f4d3dc742474d3a672388a1ebe99962505b234",
        ),
        (
            "accepted_w10_s4b_tests",
            "tests/test_w10_checkout_intent_contract.py",
            "93b4a0b9363464eeb3b5d9dc10c92aacb90c60f549c7cdda1550355ac1cf6b91",
            _candidate_base_commit,
        ),
    )
    _accepted_operating_state = (
        ("offer_capability_required", True),
        ("operational_offer_registry", ()),
        ("promotions_active", False),
        ("promotion_codes_enabled", False),
        ("promotion_codes", ()),
        ("eligibility_rules", ()),
        ("duration_rules", ()),
        ("stacking_rules", ()),
        ("discounted_prices", ()),
        ("partner_offers_enabled", False),
        ("partner_offers_supported", False),
        ("partner_offer_definitions", ()),
    )
    _authority_flags = (
        ("runtime_authority", False),
        ("provider_authority", False),
        ("provider_mapping_authority", False),
        ("price_authority", False),
        ("eligibility_decision_authority", False),
        ("checkout_authority", False),
        ("charge_authority", False),
        ("entitlement_authority", False),
        ("approval_authority", False),
        ("activation_authority", False),
        ("persistence_authority", False),
        ("display_authority", False),
        ("reconciliation_authority", False),
    )
    _later_gates = (
        "accepted_versioned_offer_policy_and_provenance",
        "accepted_exact_amount_availability_duration_eligibility_and_stacking_outcomes",
        "independently_reviewed_runtime_consumer_contract",
        "durable_configuration_repository_and_atomic_activation_control",
        "approved_provider_mapping_and_provider_configuration",
        "checkout_ingress_reconciliation_and_entitlement_evidence",
        "security_privacy_finance_tax_operations_and_target_assurance",
        "separate_founder_production_activation_release_and_go_live_authority",
    )
    _create_fields = (
        "offer_configuration_id",
        "offer_policy_version",
        "catalogue_authority_version",
        "base_plan_key",
        "proposed_unit_amount_minor",
        "currency",
        "availability_starts_at",
        "availability_ends_at",
        "duration_count",
        "duration_unit",
        "eligibility_policy_reference",
        "stacking_policy_reference",
        "policy_provenance",
        "evaluated_at",
        "evidence_reference",
    )
    _provenance_fields = (
        "schema_version",
        "decision_id",
        "policy_version",
        "decided_by",
        "decided_at",
        "record_reference",
        "record_sha256",
    )
    _candidate_fields = (
        "schema_version",
        "candidate_status",
        "content_identity",
        "offer_configuration_id",
        "offer_policy_version",
        "policy_acceptance_status",
        "catalogue_authority_version",
        "base_plan_key",
        "base_unit_amount_minor",
        "proposed_unit_amount_minor",
        "currency",
        "availability_starts_at",
        "availability_ends_at",
        "duration_count",
        "duration_unit",
        "eligibility_policy_reference",
        "stacking_policy_reference",
        "policy_provenance",
        "evaluated_at",
        "evidence_reference",
        "operational_registry_entry_created",
        "accepted_operating_state",
        "authority_flags",
        "later_acceptance_gates",
    )
    _secret_markers = (
        "secret",
        "credential",
        "password",
        "passwd",
        "bearer",
        "authorization",
        "api_key",
        "access_token",
        "refresh_token",
        "private_key",
        "client_secret",
        "endpoint_secret",
        "webhook_secret",
        "sk_live",
        "sk_test",
        "rk_live",
        "rk_test",
        "whsec",
    )
    _excluded_offer_roots = (
        "partner",
        "reseller",
        "affiliate",
        "marketplace",
        "coupon",
    )
    _promotion_code_roots = (
        "promotioncode",
        "promotionscode",
        "promocode",
        "promoscode",
    )
    def _clone(value):
        if _type(value) is _tuple:
            return _tuple(_clone(item) for item in value)
        if _type(value) in (_str, _int, _bool):
            return value
        raise _RuntimeError("offer contract projection contains a non-built-in value")

    def _exact_call(args, kwargs, positional_count, named_fields, context):
        if _type(args) is not _tuple or _len(args) != positional_count:
            raise _TypeError(
                f"{context} requires exactly {positional_count} positional input(s)"
            )
        if _type(kwargs) is not _dict:
            raise _TypeError(f"{context} named facts must be an exact dict")
        keys = _tuple(kwargs.keys())
        if not _all(_type(key) is _str for key in keys):
            raise _TypeError(f"{context} names must be exact strings")
        if keys != named_fields:
            unexpected = _tuple(key for key in keys if key not in _set(named_fields))
            if unexpected:
                raise _TypeError(f"{context} received unsupported fact {unexpected[0]}")
            raise _TypeError(f"{context} requires the exact ordered complete named fact set")
        return args, _tuple(kwargs[field] for field in named_fields)

    def _exact_record(value, fields, context):
        if _type(value) is not _tuple or _len(value) != _len(fields):
            raise _TypeError(f"{context} must be an exact complete tuple")
        if not _all(
            _type(item) is _tuple
            and _len(item) == 2
            and _type(item[0]) is _str
            for item in value
        ):
            raise _ValueError(f"{context} fields must be exact string-keyed pairs")
        if _tuple(item[0] for item in value) != fields:
            raise _ValueError(f"{context} fields are missing, extra or reordered")
        return _tuple(item[1] for item in value)

    def _bounded_text(value, label, maximum=160):
        if _type(value) is not _str:
            raise _TypeError(f"{label} must be an exact string")
        if not value or value != value.strip() or _len(value) > maximum:
            raise _ValueError(f"{label} must be non-empty, trimmed and bounded")
        if not value.isascii() or not value.isprintable():
            raise _ValueError(f"{label} must contain printable ASCII only")
        return value

    def _reject_secret_shape(value, label):
        normalised = _separator("_", value.casefold())
        padded = f"_{normalised}_"
        if _any(f"_{marker}_" in padded for marker in _secret_markers):
            raise _ValueError(f"{label} must not contain secret-shaped material")
        if _provider_identifier(value) is not None:
            raise _ValueError(f"{label} must not contain a provider identifier")
        return value

    def _reject_excluded_semantics(value, label, purpose):
        """Reject finite prohibited roots without inferring semantic synonyms."""
        folded = value.casefold()
        neutralised = _neutral_account_vocabulary("neutral", folded)
        canonical = _non_alphanumeric("", neutralised)
        if _any(root in canonical for root in _excluded_offer_roots):
            raise _ValueError(f"{label} carries excluded offer semantics")
        if _any(root in canonical for root in _promotion_code_roots):
            raise _ValueError(f"{label} carries excluded promotion-code semantics")
        if (
            purpose == "policy_reference"
            and _generic_subject_policy_reference(value) is not None
        ):
            return value
        if _reserved_subject_root(canonical) is not None:
            raise _ValueError(f"{label} carries customer-specific semantics")
        return value

    def _safe_identifier(value, label, prefix):
        value = _bounded_text(value, label)
        if _identifier(value) is None or not value.startswith(prefix):
            raise _ValueError(f"{label} must use the required bounded namespace")
        _reject_excluded_semantics(value, label, "identifier")
        return _reject_secret_shape(value, label)

    def _offer_configuration_identifier(value):
        return _safe_identifier(value, "offer_configuration_id", "offer_config:")

    def _local_record_reference(value, label):
        value = _bounded_text(value, label, maximum=256)
        if _record_reference(value) is None:
            raise _ValueError(f"{label} must identify a local record and section")
        path, _section = value.rsplit("#", 1)
        if _any(segment in (".", "..") for segment in path.split("/")):
            raise _ValueError(f"{label} path must not contain dot segments")
        if not path.startswith("docs/"):
            raise _ValueError(f"{label} must use the provider-neutral docs policy namespace")
        _reject_excluded_semantics(value, label, "policy_reference")
        return _reject_secret_shape(value, label)

    def _utc(value, label):
        if _type(value) is not _Datetime or value.tzinfo is not _UTC:
            raise _TypeError(f"{label} must be an exact datetime using timezone.utc")
        return value

    def _timestamp(value):
        return (
            f"{value.year:04d}-{value.month:02d}-{value.day:02d}"
            f"T{value.hour:02d}:{value.minute:02d}:{value.second:02d}."
            f"{value.microsecond:06d}Z"
        )

    def _parse_timestamp(value, label):
        if _type(value) is not _str:
            raise _TypeError(f"{label} must be an exact string")
        try:
            parsed = _Datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
                tzinfo=_UTC
            )
        except ValueError as exc:
            raise _ValueError(f"{label} must be a canonical UTC timestamp") from exc
        if _timestamp(parsed) != value:
            raise _ValueError(f"{label} must be a canonical UTC timestamp")
        return parsed

    def _plan(value, authority_version):
        if _type(authority_version) is not _str or authority_version != (
            _catalogue_authority_version
        ):
            raise _ValueError("catalogue authority version is unsupported")
        if _type(value) is not _str:
            raise _TypeError("base_plan_key must be an exact string")
        for plan in _catalogue:
            if plan[0] == value:
                return plan
        raise _ValueError("base_plan_key is not in the accepted initial catalogue")

    def _money(value, base_amount):
        if _type(value) is not _int or _type(value) is _bool:
            raise _TypeError("proposed_unit_amount_minor must be an exact integer")
        if value <= 0 or value >= base_amount:
            raise _ValueError(
                "proposed_unit_amount_minor must be positive and below the exact base amount"
            )
        return value

    def _positive_count(value):
        if _type(value) is not _int or _type(value) is _bool:
            raise _TypeError("duration_count must be an exact integer")
        if value <= 0 or value > 1_000_000:
            raise _ValueError("duration_count must be positive and bounded")
        return value

    def _duration_unit(value):
        if _type(value) is not _str:
            raise _TypeError("duration_unit must be an exact string")
        if value not in _duration_units:
            raise _ValueError("duration_unit is unsupported")
        return value

    def _validate_provenance_input(value, expected_policy_version):
        (
            schema_version,
            decision_id,
            policy_version,
            decided_by,
            decided_at,
            record_reference,
            record_sha256,
        ) = _exact_record(value, _provenance_fields, "policy_provenance")
        if _type(schema_version) is not _str or schema_version != _provenance_schema:
            raise _ValueError("policy provenance schema is unsupported")
        decision_id = _bounded_text(decision_id, "decision_id", maximum=128)
        if _policy_decision_id(decision_id) is None:
            raise _ValueError("decision_id must be an uppercase hyphenated identifier")
        _reject_excluded_semantics(decision_id, "decision_id", "identifier")
        _reject_secret_shape(decision_id, "decision_id")
        policy_version = _safe_identifier(
            policy_version, "provenance policy_version", "offer_policy:"
        )
        if policy_version != expected_policy_version:
            raise _ValueError("policy provenance does not bind the offered policy version")
        decided_by = _bounded_text(decided_by, "decided_by", maximum=128)
        _reject_excluded_semantics(decided_by, "decided_by", "identifier")
        _reject_secret_shape(decided_by, "decided_by")
        decided_at = _utc(decided_at, "decided_at")
        record_reference = _local_record_reference(record_reference, "record_reference")
        if _type(record_sha256) is not _str or _digest(record_sha256) is None:
            raise _ValueError("record_sha256 must be an exact lowercase SHA-256 digest")
        return (
            ("schema_version", _provenance_schema),
            ("decision_id", decision_id),
            ("policy_version", policy_version),
            ("decided_by", decided_by),
            ("decided_at", _timestamp(decided_at)),
            ("record_reference", record_reference),
            ("record_sha256", record_sha256),
        ), decided_at

    def _validate_provenance_projection(value, expected_policy_version):
        values = _exact_record(value, _provenance_fields, "policy_provenance")
        rebuilt_input = (
            ("schema_version", values[0]),
            ("decision_id", values[1]),
            ("policy_version", values[2]),
            ("decided_by", values[3]),
            ("decided_at", _parse_timestamp(values[4], "decided_at")),
            ("record_reference", values[5]),
            ("record_sha256", values[6]),
        )
        canonical, decided_at = _validate_provenance_input(
            rebuilt_input, expected_policy_version
        )
        if canonical != value:
            raise _ValueError("policy provenance is not canonical")
        return canonical, decided_at

    def _identity(state_without_identity):
        payload = _json_dumps(
            state_without_identity,
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("ascii")
        return "offer-configuration:sha256-" + _sha256(payload).hexdigest()

    def _static_contract():
        return (
            ("contract_version", _contract_version),
            ("candidate_base_commit", _candidate_base_commit),
            ("candidate_base_tree", _candidate_base_tree),
            ("candidate_schema", _candidate_schema),
            ("catalogue_authority_version", _catalogue_authority_version),
            ("source_bindings", _source_bindings),
            ("gross_catalogue", _catalogue),
            ("accepted_operating_state", _accepted_operating_state),
            ("duration_units_are_structural_vocabulary_only", _duration_units),
            ("authority_flags", _authority_flags),
            ("later_acceptance_gates", _later_gates),
            (
                "assurance_status",
                "contract_only_not_offer_policy_runtime_provider_checkout_"
                "entitlement_or_s4_completion",
            ),
        )

    _token = _object()

    class _CandidateIntegritySeal(_tuple):
        """Private immutable issuance facts; not a runtime authority object."""

        __slots__ = ()

        def __new__(cls, *args, **kwargs):
            raise _TypeError(
                "offer candidate integrity seals are producer-issued only"
            )

    class OfferConfigurationCandidate:
        """Opaque producer-issued handle; all semantic output is detached."""

        __slots__ = ("__projection", "__seal", "__integrity_identity")

        def __new__(cls, _producer_token=None):
            if (
                cls is not OfferConfigurationCandidate
                or _producer_token is not _token
            ):
                raise _TypeError("offer configuration candidates are producer-issued only")
            return _object_new(cls)

        def __setattr__(self, name, value):
            raise _TypeError("offer configuration candidates are immutable")

        def __delattr__(self, name):
            raise _TypeError("offer configuration candidates are immutable")

        def __copy__(self):
            raise _TypeError("offer configuration candidates are not reconstructable")

        def __deepcopy__(self, memo):
            raise _TypeError("offer configuration candidates are not reconstructable")

        def __reduce__(self):
            raise _TypeError("offer configuration candidates are not serialisable")

        def __reduce_ex__(self, protocol):
            raise _TypeError("offer configuration candidates are not serialisable")

    _Seal = _CandidateIntegritySeal
    _Candidate = OfferConfigurationCandidate
    _candidate_projection_slot = _Candidate.__dict__[
        "_OfferConfigurationCandidate__projection"
    ]
    _candidate_seal_slot = _Candidate.__dict__["_OfferConfigurationCandidate__seal"]
    _candidate_integrity_identity_slot = _Candidate.__dict__[
        "_OfferConfigurationCandidate__integrity_identity"
    ]

    def _issue_candidate(projection):
        candidate = _object_new(_Candidate)
        integrity_identity = _object()
        view = _dict(projection)
        seal = _tuple_new(
            _Seal,
            (
                _token,
                integrity_identity,
                candidate,
                projection,
                view["content_identity"],
                view["offer_configuration_id"],
            ),
        )
        _candidate_projection_slot.__set__(candidate, projection)
        _candidate_seal_slot.__set__(candidate, seal)
        _candidate_integrity_identity_slot.__set__(candidate, integrity_identity)
        return candidate

    def _validate_candidate_projection(value):
        values = _exact_record(value, _candidate_fields, "candidate")
        view = _dict(value)
        if _type(view["schema_version"]) is not _str or view["schema_version"] != (
            _candidate_schema
        ):
            raise _ValueError("candidate schema is unsupported")
        if _type(view["candidate_status"]) is not _str or view["candidate_status"] != (
            _candidate_status
        ):
            raise _ValueError("candidate status cannot confer authority")
        configuration_id = _offer_configuration_identifier(view["offer_configuration_id"])
        policy_version = _safe_identifier(
            view["offer_policy_version"], "offer_policy_version", "offer_policy:"
        )
        if view["policy_acceptance_status"] != _policy_acceptance_status:
            raise _ValueError("candidate cannot assert accepted policy authority")
        plan = _plan(view["base_plan_key"], view["catalogue_authority_version"])
        if (
            _type(view["base_unit_amount_minor"]) is not _int
            or _type(view["base_unit_amount_minor"]) is _bool
            or view["base_unit_amount_minor"] != plan[1]
        ):
            raise _ValueError("candidate base amount is not the accepted catalogue amount")
        _money(view["proposed_unit_amount_minor"], plan[1])
        if _type(view["currency"]) is not _str or view["currency"] != "GBP":
            raise _ValueError("currency must be exact GBP")
        available_from = _parse_timestamp(
            view["availability_starts_at"], "availability_starts_at"
        )
        available_until = _parse_timestamp(
            view["availability_ends_at"], "availability_ends_at"
        )
        evaluated_at = _parse_timestamp(view["evaluated_at"], "evaluated_at")
        if not available_from < available_until:
            raise _ValueError("availability interval is empty or contradictory")
        if evaluated_at >= available_until:
            raise _ValueError("candidate evaluation is not before availability end")
        _positive_count(view["duration_count"])
        _duration_unit(view["duration_unit"])
        _local_record_reference(
            view["eligibility_policy_reference"], "eligibility_policy_reference"
        )
        _local_record_reference(
            view["stacking_policy_reference"], "stacking_policy_reference"
        )
        _provenance, decided_at = _validate_provenance_projection(
            view["policy_provenance"], policy_version
        )
        if decided_at > evaluated_at:
            raise _ValueError("policy provenance post-dates candidate evaluation")
        _safe_identifier(view["evidence_reference"], "evidence_reference", "evidence:")
        if view["operational_registry_entry_created"] is not False:
            raise _ValueError("a structural candidate cannot enter the operational registry")
        if view["accepted_operating_state"] != _accepted_operating_state:
            raise _ValueError("candidate changes the accepted disabled operating state")
        if view["authority_flags"] != _authority_flags or _any(
            _type(flag) is not _bool or flag is not False
            for _name, flag in view["authority_flags"]
        ):
            raise _ValueError("every candidate authority flag must remain false")
        if view["later_acceptance_gates"] != _later_gates:
            raise _ValueError("candidate cannot remove later acceptance gates")
        state_without_identity = _tuple(
            item for item in value if item[0] != "content_identity"
        )
        expected_identity = _identity(state_without_identity)
        if _type(view["content_identity"]) is not _str or (
            view["content_identity"] != expected_identity
        ):
            raise _ValueError("candidate identity does not match exact content")
        if configuration_id != view["offer_configuration_id"]:
            raise _RuntimeError("candidate identifier canonicalisation mismatch")
        return _clone(value)

    def _validate_issued(value):
        if _type(value) is not _Candidate:
            raise _TypeError("value must be an exact producer-issued offer candidate")
        try:
            projection = _candidate_projection_slot.__get__(value, _Candidate)
            seal = _candidate_seal_slot.__get__(value, _Candidate)
            integrity_identity = _candidate_integrity_identity_slot.__get__(
                value, _Candidate
            )
        except _AttributeError as exc:
            raise _ValueError("offer candidate is not producer-issued") from exc
        if _type(seal) is not _Seal or _len(seal) != 6:
            raise _ValueError("offer candidate integrity seal is invalid")
        (
            issuer,
            sealed_integrity_identity,
            sealed_handle,
            sealed_projection,
            content_identity,
            configuration_id,
        ) = seal
        if issuer is not _token:
            raise _ValueError("offer candidate integrity issuer is invalid")
        if sealed_integrity_identity is not integrity_identity:
            raise _ValueError("offer candidate integrity identity is invalid")
        if sealed_handle is not value:
            raise _ValueError("offer candidate handle identity is invalid")
        if sealed_projection is not projection:
            raise _ValueError("offer candidate projection binding is invalid")
        validated = _validate_candidate_projection(projection)
        validated_view = _dict(validated)
        if (
            content_identity != validated_view["content_identity"]
            or configuration_id != validated_view["offer_configuration_id"]
        ):
            raise _ValueError("offer candidate sealed content binding is invalid")
        return validated

    def project_offer_configuration_contract(*args, **kwargs):
        _exact_call(args, kwargs, 0, (), "contract projection")
        return _clone(_static_contract())

    def create_unadmitted_offer_configuration_candidate(*args, **kwargs):
        _positional, facts = _exact_call(
            args, kwargs, 0, _create_fields, "offer candidate creation"
        )
        (
            configuration_id,
            policy_version,
            authority_version,
            plan_key,
            proposed_amount,
            currency,
            available_from,
            available_until,
            duration_count,
            duration_unit,
            eligibility_reference,
            stacking_reference,
            policy_provenance,
            evaluated_at,
            evidence_reference,
        ) = facts
        configuration_id = _offer_configuration_identifier(configuration_id)
        policy_version = _safe_identifier(
            policy_version, "offer_policy_version", "offer_policy:"
        )
        plan = _plan(plan_key, authority_version)
        proposed_amount = _money(proposed_amount, plan[1])
        if _type(currency) is not _str or currency != "GBP":
            raise _ValueError("currency must be exact GBP")
        available_from = _utc(available_from, "availability_starts_at")
        available_until = _utc(available_until, "availability_ends_at")
        evaluated_at = _utc(evaluated_at, "evaluated_at")
        if not available_from < available_until:
            raise _ValueError("availability interval is empty or contradictory")
        if evaluated_at >= available_until:
            raise _ValueError("candidate evaluation is not before availability end")
        duration_count = _positive_count(duration_count)
        duration_unit = _duration_unit(duration_unit)
        eligibility_reference = _local_record_reference(
            eligibility_reference, "eligibility_policy_reference"
        )
        stacking_reference = _local_record_reference(
            stacking_reference, "stacking_policy_reference"
        )
        provenance, decided_at = _validate_provenance_input(
            policy_provenance, policy_version
        )
        if decided_at > evaluated_at:
            raise _ValueError("policy provenance post-dates candidate evaluation")
        evidence_reference = _safe_identifier(
            evidence_reference, "evidence_reference", "evidence:"
        )
        state_without_identity = (
            ("schema_version", _candidate_schema),
            ("candidate_status", _candidate_status),
            ("offer_configuration_id", configuration_id),
            ("offer_policy_version", policy_version),
            ("policy_acceptance_status", _policy_acceptance_status),
            ("catalogue_authority_version", _catalogue_authority_version),
            ("base_plan_key", plan[0]),
            ("base_unit_amount_minor", plan[1]),
            ("proposed_unit_amount_minor", proposed_amount),
            ("currency", "GBP"),
            ("availability_starts_at", _timestamp(available_from)),
            ("availability_ends_at", _timestamp(available_until)),
            ("duration_count", duration_count),
            ("duration_unit", duration_unit),
            ("eligibility_policy_reference", eligibility_reference),
            ("stacking_policy_reference", stacking_reference),
            ("policy_provenance", provenance),
            ("evaluated_at", _timestamp(evaluated_at)),
            ("evidence_reference", evidence_reference),
            ("operational_registry_entry_created", False),
            ("accepted_operating_state", _accepted_operating_state),
            ("authority_flags", _authority_flags),
            ("later_acceptance_gates", _later_gates),
        )
        content_identity = _identity(state_without_identity)
        projection = (
            state_without_identity[0],
            state_without_identity[1],
            ("content_identity", content_identity),
            *state_without_identity[2:],
        )
        _validate_candidate_projection(projection)
        return _issue_candidate(projection)

    def validate_offer_configuration_candidate(*args, **kwargs):
        positional, _facts = _exact_call(
            args, kwargs, 1, (), "offer candidate validation"
        )
        return _clone(_validate_issued(positional[0]))

    def project_offer_configuration_candidate(*args, **kwargs):
        positional, _facts = _exact_call(
            args, kwargs, 1, (), "offer candidate projection"
        )
        return _clone(_validate_issued(positional[0]))

    return (
        _contract_version,
        _catalogue_authority_version,
        OfferConfigurationCandidate,
        project_offer_configuration_contract,
        create_unadmitted_offer_configuration_candidate,
        validate_offer_configuration_candidate,
        project_offer_configuration_candidate,
    )


(
    CONTRACT_VERSION,
    CATALOGUE_AUTHORITY_VERSION,
    OfferConfigurationCandidate,
    project_offer_configuration_contract,
    create_unadmitted_offer_configuration_candidate,
    validate_offer_configuration_candidate,
    project_offer_configuration_candidate,
) = _build_offer_configuration_contract()

OfferConfigurationCandidate.__module__ = __name__
OfferConfigurationCandidate.__qualname__ = OfferConfigurationCandidate.__name__

__all__ = (
    "CONTRACT_VERSION",
    "CATALOGUE_AUTHORITY_VERSION",
    "OfferConfigurationCandidate",
    "project_offer_configuration_contract",
    "create_unadmitted_offer_configuration_candidate",
    "validate_offer_configuration_candidate",
    "project_offer_configuration_candidate",
)
