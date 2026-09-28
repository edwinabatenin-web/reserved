"""W10-S2E fail-closed tax/invoice prerequisite evidence contract.

This module records only settled gross catalogue presentation and the gates a
future tax/document implementation must satisfy.  It is deliberately pure and
I/O-free: it does not calculate VAT, issue an invoice or receipt, activate
Stripe Tax, accept tax facts, persist records, or affect entitlement.

Values are detached immutable structures. Validation establishes only local
semantic consistency with this contract; it is not proof of provenance,
authentication, issuance, or authority.
"""

from __future__ import annotations

import re as _re_module
from datetime import datetime as _datetime_type
from datetime import timezone as _timezone_type


def _build_tax_invoice_prerequisite_contract():
    """Build the closure-bound, runtime-neutral S2E evidence contract."""

    _type = type
    _tuple = tuple
    _dict = dict
    _len = len
    _set = set
    _all = all
    _str = str
    _int = int
    _bool = bool
    _TypeError = TypeError
    _ValueError = ValueError
    _RuntimeError = RuntimeError
    _Datetime = _datetime_type
    _utc_timezone = _timezone_type.utc
    _identifier_match = _re_module.compile(
        r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"
    ).fullmatch
    _timestamp_match = _re_module.compile(
        r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z$"
    ).fullmatch
    _separator_match = _re_module.compile(r"[_.:/-]+").sub

    _contract_version = "W10-S2E/2026-09-04/v1"
    _integration_head = "54a82476939dce8f75af62d73aeb477e11a1260c"
    _integration_tree = "26b1aa6a1302195770534dc41caf099bcdd7cb06"
    _vat_copy = "inclusive of VAT where applicable"

    _repository_sources = (
        (
            "founder_authority",
            "FOUNDER_DECISIONS.md",
            "03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4",
            "FD-W10-001/2026-09-02/v1",
        ),
        (
            "catalogue_contract",
            "reserved/billing/contracts.py",
            "9c5dce7a81652d58562ca339def95fba7cbb2d1c02f965618ebd8f40bcad202b",
            "W10-S1A",
        ),
        (
            "authority_boundary",
            "docs/W10_BILLING_AUTHORITY_AND_POLICY_CONTRACT.md",
            "e5911c70199727beba888175f5f31a208a4418eb16cae7978e8b52fa57d688ce",
            "contract_only_no_vat_calculation",
        ),
        (
            "specialist_gate_dossier",
            "docs/W10_S2C_POLICY_EVIDENCE_DOSSIER.md",
            "db31ba2e7c0e51701bc62c6a7b4b489cbde072b5efaf1f09f7c67a5f75fd5dcd",
            "candidate_evidence_not_tax_assurance",
        ),
    )
    _catalogue = (
        (
            ("plan_key", "standard_monthly"),
            ("gross_amount_minor", 999),
            ("currency", "GBP"),
            ("cadence_count", 1),
            ("cadence_unit", "month"),
            ("simplified_invoice_amount_limb", True),
            ("simplified_invoice_authority", False),
        ),
        (
            ("plan_key", "premium_monthly"),
            ("gross_amount_minor", 1999),
            ("currency", "GBP"),
            ("cadence_count", 1),
            ("cadence_unit", "month"),
            ("simplified_invoice_amount_limb", True),
            ("simplified_invoice_authority", False),
        ),
        (
            ("plan_key", "free_tier_under_25"),
            ("gross_amount_minor", 0),
            ("currency", "GBP"),
            ("cadence_count", 12),
            ("cadence_unit", "month"),
            ("simplified_invoice_amount_limb", True),
            ("simplified_invoice_authority", False),
        ),
        (
            ("plan_key", "launch_offer_month_1"),
            ("gross_amount_minor", 0),
            ("currency", "GBP"),
            ("cadence_count", 1),
            ("cadence_unit", "month"),
            ("simplified_invoice_amount_limb", True),
            ("simplified_invoice_authority", False),
        ),
        (
            ("plan_key", "launch_offer_months_2_6"),
            ("gross_amount_minor", 499),
            ("currency", "GBP"),
            ("cadence_count", 5),
            ("cadence_unit", "month"),
            ("simplified_invoice_amount_limb", True),
            ("simplified_invoice_authority", False),
        ),
    )
    _catalogue_by_key = _tuple(
        (_dict(item)["plan_key"], item) for item in _catalogue
    )
    _document_concepts = (
        (
            "payment_receipt_candidate",
            (
                ("meaning", "neutral_acknowledgement_candidate_for_verified_payment"),
                ("live_render_or_delivery_authority", False),
                ("vat_invoice_status", False),
                ("direct_entitlement_effect", False),
            ),
        ),
        (
            "invoice_candidate",
            (
                ("meaning", "neutral_invoice_shape_candidate_not_a_vat_invoice"),
                ("live_render_or_delivery_authority", False),
                ("vat_invoice_status", False),
                ("direct_entitlement_effect", False),
            ),
        ),
        (
            "credit_note_candidate",
            (
                ("meaning", "append_only_linked_correction_candidate_not_a_vat_credit_note"),
                ("live_render_or_delivery_authority", False),
                ("vat_credit_note_status", False),
                ("direct_entitlement_effect", False),
            ),
        ),
    )
    _authority_flags = (
        ("vat_calculation_authority", False),
        ("net_amount_derivation_authority", False),
        ("vat_amount_derivation_authority", False),
        ("vat_invoice_issuance_authority", False),
        ("simplified_invoice_issuance_authority", False),
        ("stripe_tax_activation_authority", False),
        ("refund_credit_note_tax_disposition_authority", False),
        ("live_receipt_render_or_delivery_authority", False),
        ("provider_observation_direct_tax_document_effect", False),
        ("provider_observation_direct_entitlement_effect", False),
        ("document_candidate_direct_entitlement_effect", False),
    )
    _prohibited_inputs = (
        "vat_rate",
        "net_amount",
        "vat_amount",
        "supplier_vat_registration_id",
        "customer_vat_registration_id",
        "customer_tax_status",
        "customer_location",
        "place_of_supply",
        "provider_zero_tax_result",
        "vat_invoice_label",
        "vat_credit_note_label",
        "entitlement_effect",
    )
    _future_specialist_inputs = (
        "contracting_supplier_entity_and_address",
        "establishment_and_vat_registration_status_number_and_effective_dates",
        "supply_taxability_rate_and_digital_service_classification",
        "customer_business_or_private_status_and_evidence",
        "customer_location_place_of_supply_and_supported_geography",
        "tax_point_and_accounting_scheme_treatment",
        "invoice_receipt_credit_note_fields_numbering_timing_and_request_policy",
        "stripe_registration_tax_code_price_behaviour_and_location_configuration",
        "field_level_retention_erasure_legal_hold_and_backup_expiry_policy",
    )
    _preserved_questions = (
        ("Q1", "refunds", "unresolved"),
        ("Q2", "paid_access_surface", "unresolved"),
        (
            "Q3",
            "post_settlement_dispute_chargeback_reversal_consequences",
            "unresolved",
        ),
    )
    _production_gates = (
        "accepted_finance_accounting_vat_profile",
        "accepted_tax_legal_supply_customer_and_geography_classification",
        "accepted_invoice_receipt_credit_note_schema_and_customer_copy",
        "accepted_privacy_security_data_minimisation_and_retention_design",
        "accepted_w9_retention_erasure_legal_hold_backup_and_custody_evidence",
        "reviewed_stripe_sandbox_configuration_and_sample_artifacts",
        "target_reconciliation_audit_access_recovery_and_operational_evidence",
        "separate_founder_production_activation_and_release_authority",
    )
    _official_sources = (
        (
            "uk_price_transparency",
            "https://www.gov.uk/government/publications/price-transparency-cma209/providing-clear-and-accurate-information-about-prices-summary",
            "consumer_total_price_includes_reasonably_calculable_mandatory_taxes_and_periodic_price_or_term_total",
        ),
        (
            "uk_vat_registration",
            "https://www.gov.uk/register-for-vat",
            "registration_depends_on_actual_turnover_forecast_establishment_and_voluntary_status",
        ),
        (
            "hmrc_vat_invoices",
            "https://www.gov.uk/guidance/vat-guide-notice-700",
            "vat_invoice_duty_content_timing_simplified_amount_conditions_and_credit_note_rules_are_conditional",
        ),
        (
            "hmrc_vat_records",
            "https://www.gov.uk/charge-reclaim-record-vat/keeping-vat-records",
            "only_vat_registered_businesses_issue_vat_invoices_and_retention_depends_on_applicable_scheme",
        ),
        (
            "hmrc_continuous_supply_tax_point",
            "https://www.gov.uk/guidance/vat-instalments-deposits-credit-sales",
            "continuous_service_tax_point_is_invoice_or_payment_whichever_is_earlier_if_that_classification_applies",
        ),
        (
            "hmrc_digital_services",
            "https://www.gov.uk/guidance/the-vat-rules-if-you-supply-digital-services-to-private-consumers",
            "treatment_depends_on_service_customer_status_and_location_with_cross_border_evidence_requirements",
        ),
        (
            "hmrc_electronic_invoicing",
            "https://www.gov.uk/guidance/electronic-invoicing-notice-70063",
            "electronic_invoice_authenticity_integrity_legibility_agreement_audit_and_storage_controls_are_conditional",
        ),
        (
            "stripe_tax_capability",
            "https://docs.stripe.com/tax/set-up",
            "provider_can_calculate_tax_after_merchant_supplies_registrations_tax_code_price_behaviour_and_location_facts",
        ),
        (
            "stripe_hosted_invoice_capability",
            "https://docs.stripe.com/invoicing/hosted-invoice-page",
            "provider_can_host_invoice_and_receipt_pdfs_but_does_not_supply_reserved_tax_authority",
        ),
        (
            "stripe_tax_id_capability",
            "https://docs.stripe.com/tax/invoicing/tax-ids",
            "provider_can_render_tax_ids_but_provider_configuration_is_not_legal_or_tax_acceptance",
        ),
    )
    _scope_exclusions = (
        "vat_or_net_calculation",
        "tax_fact_acceptance_or_legal_tax_assurance",
        "invoice_receipt_or_credit_note_issuance_delivery_or_storage",
        "provider_sdk_network_credentials_configuration_or_activation",
        "database_file_or_runtime_io",
        "refund_discount_or_credit_note_policy",
        "route_template_checkout_or_customer_journey",
        "entitlement_access_or_paid_surface_enforcement",
        "founder_question_answer_or_w10_completion",
    )
    _projection = (
        ("contract_version", _contract_version),
        ("integration_head", _integration_head),
        ("integration_tree", _integration_tree),
        ("repository_sources", _repository_sources),
        ("gross_price_statement", _vat_copy),
        ("gross_catalogue", _catalogue),
        ("document_concepts", _document_concepts),
        ("authority_flags", _authority_flags),
        ("prohibited_inputs", _prohibited_inputs),
        ("future_specialist_inputs", _future_specialist_inputs),
        ("preserved_founder_questions", _preserved_questions),
        ("production_gates", _production_gates),
        ("official_sources", _official_sources),
        ("scope_exclusions", _scope_exclusions),
        (
            "assurance_status",
            "contract_only_not_legal_tax_assurance_s2_completion_or_s6_implementation",
        ),
    )

    _secret_single_markers = _set(
        ("secret", "credential", "password", "bearer", "privatekey")
    )
    _secret_compound_markers = _set(
        (
            "api_key",
            "access_token",
            "refresh_token",
            "private_key",
            "client_secret",
            "endpoint_secret",
            "sk_live",
            "sk_test",
            "rk_live",
            "rk_test",
            "whsec",
        )
    )
    _document_keys = (
        "document_id",
        "document_kind",
        "owner_reference",
        "plan_key",
        "gross_amount_minor",
        "currency",
        "gross_price_statement",
        "recorded_at",
        "evidence_reference",
        "simplified_invoice_amount_limb",
        "simplified_invoice_authority",
        "vat_invoice_status",
        "live_render_or_delivery_authority",
        "provider_observation_direct_tax_document_effect",
        "direct_entitlement_effect",
        "corrections",
    )
    _correction_keys = (
        "correction_id",
        "document_kind",
        "original_document_id",
        "recorded_at",
        "evidence_reference",
        "vat_credit_note_status",
        "refund_credit_note_tax_disposition_authority",
        "live_render_or_delivery_authority",
        "provider_observation_direct_tax_document_effect",
        "direct_entitlement_effect",
    )
    _create_candidate_input_fields = (
        "document_id",
        "document_kind",
        "owner_reference",
        "plan_key",
        "gross_amount_minor",
        "currency",
        "recorded_at",
        "evidence_reference",
    )
    _append_correction_input_fields = (
        "correction_id",
        "original_document_id",
        "recorded_at",
        "evidence_reference",
    )

    def _clone_builtin(value):
        if _type(value) is _tuple:
            return _tuple(_clone_builtin(item) for item in value)
        if _type(value) in (_str, _int, _bool):
            return value
        raise _RuntimeError("S2E projection contains a non-built-in value")

    def _safe_identifier(value, field):
        if _type(value) is not _str:
            raise _TypeError(f"{field} must be an exact string")
        if _identifier_match(value) is None:
            raise _ValueError(
                f"{field} must be 1-128 ASCII identifier characters"
            )
        normalised = _separator_match("_", value.casefold())
        tokens = normalised.split("_")
        if _set(tokens).intersection(_secret_single_markers):
            raise _ValueError(f"{field} must not retain secret-shaped material")
        index = 0
        while index < _len(tokens):
            if tokens[index] in _secret_compound_markers:
                raise _ValueError(f"{field} must not retain secret-shaped material")
            if index + 1 < _len(tokens):
                pair = tokens[index] + "_" + tokens[index + 1]
                if pair in _secret_compound_markers:
                    raise _ValueError(
                        f"{field} must not retain secret-shaped material"
                    )
            index += 1
        return value

    def _exact_call(args, kwargs, positional_count, fields, context):
        if _type(args) is not _tuple or _len(args) != positional_count:
            raise _TypeError(
                f"{context} requires exactly {positional_count} positional "
                "structural input(s)"
            )
        if _type(kwargs) is not _dict:
            raise _TypeError(f"{context} keyword inputs must be an exact dict")
        keys = _tuple(kwargs.keys())
        if not _all(_type(key) is _str for key in keys):
            raise _TypeError(f"{context} keyword names must be exact strings")
        allowed = _set(fields)
        supplied = _set(keys)
        unexpected = _tuple(key for key in keys if key not in allowed)
        if unexpected:
            raise _TypeError(
                f"{context} received unsupported named fact {unexpected[0]}"
            )
        if _len(keys) != _len(fields) or supplied != allowed:
            raise _TypeError(f"{context} requires only the exact named facts")
        return args, _tuple(kwargs[field] for field in fields)

    def _utc_text(value, field):
        if _type(value) is not _Datetime or value.tzinfo is not _utc_timezone:
            raise _TypeError(
                f"{field} must be an exact datetime using timezone.utc"
            )
        detached = _Datetime(
            value.year,
            value.month,
            value.day,
            value.hour,
            value.minute,
            value.second,
            value.microsecond,
            tzinfo=_utc_timezone,
            fold=value.fold,
        )
        return (
            f"{detached.year:04d}-{detached.month:02d}-{detached.day:02d}"
            f"T{detached.hour:02d}:{detached.minute:02d}:{detached.second:02d}."
            f"{detached.microsecond:06d}Z"
        )

    def _catalogue_item(plan_key):
        if _type(plan_key) is not _str:
            raise _TypeError("plan_key must be an exact string")
        for key, item in _catalogue_by_key:
            if key == plan_key:
                return item
        raise _ValueError("plan_key is not in the settled gross catalogue")

    def _canonical_timestamp_text(value, field):
        if _type(value) is not _str or _timestamp_match(value) is None:
            raise _ValueError(f"{field} is not a canonical UTC timestamp")
        try:
            detached = _Datetime(
                _int(value[0:4]),
                _int(value[5:7]),
                _int(value[8:10]),
                _int(value[11:13]),
                _int(value[14:16]),
                _int(value[17:19]),
                _int(value[20:26]),
                tzinfo=_utc_timezone,
            )
        except _ValueError as error:
            raise _ValueError(f"{field} is not a valid UTC timestamp") from error
        canonical = (
            f"{detached.year:04d}-{detached.month:02d}-{detached.day:02d}"
            f"T{detached.hour:02d}:{detached.minute:02d}:{detached.second:02d}."
            f"{detached.microsecond:06d}Z"
        )
        if canonical != value:
            raise _ValueError(f"{field} is not a canonical UTC timestamp")
        return value

    def _validate_document_state(state):
        if _type(state) is not _tuple or _len(state) != _len(_document_keys):
            raise _ValueError("document candidate state is invalid")
        if _tuple(item[0] for item in state) != _document_keys:
            raise _ValueError("document candidate field order is invalid")
        view = _dict(state)
        document_id = _safe_identifier(view["document_id"], "document_id")
        kind = view["document_kind"]
        if _type(kind) is not _str or kind not in (
            "payment_receipt_candidate",
            "invoice_candidate",
        ):
            raise _ValueError("document candidate kind is invalid")
        owner = _safe_identifier(view["owner_reference"], "owner_reference")
        plan_key = view["plan_key"]
        item = _dict(_catalogue_item(plan_key))
        amount = view["gross_amount_minor"]
        if _type(amount) is not _int or _type(amount) is _bool:
            raise _TypeError("gross_amount_minor must be an exact integer")
        if amount != item["gross_amount_minor"]:
            raise _ValueError("document gross amount is not the settled price")
        if _type(view["currency"]) is not _str or view["currency"] != "GBP":
            raise _ValueError("document currency is not exact GBP")
        if view["gross_price_statement"] != _vat_copy:
            raise _ValueError("document gross-price statement is invalid")
        timestamp = _canonical_timestamp_text(view["recorded_at"], "recorded_at")
        evidence = _safe_identifier(view["evidence_reference"], "evidence_reference")
        if (
            _type(view["simplified_invoice_amount_limb"]) is not _bool
            or view["simplified_invoice_amount_limb"]
            is not item["simplified_invoice_amount_limb"]
        ):
            raise _ValueError("simplified-invoice amount limb is invalid")
        for field in (
            "simplified_invoice_authority",
            "vat_invoice_status",
            "live_render_or_delivery_authority",
            "provider_observation_direct_tax_document_effect",
            "direct_entitlement_effect",
        ):
            if _type(view[field]) is not _bool or view[field] is not False:
                raise _ValueError(f"{field} must remain false")
        corrections = view["corrections"]
        if _type(corrections) is not _tuple:
            raise _TypeError("corrections must be an exact tuple")
        last_timestamp = timestamp
        correction_ids = _set()
        rebuilt_corrections = ()
        for correction in corrections:
            if (
                _type(correction) is not _tuple
                or _len(correction) != _len(_correction_keys)
                or _tuple(item[0] for item in correction) != _correction_keys
            ):
                raise _ValueError("correction candidate state is invalid")
            correction_view = _dict(correction)
            correction_id = _safe_identifier(
                correction_view["correction_id"], "correction_id"
            )
            if correction_id == document_id or correction_id in correction_ids:
                raise _ValueError("correction IDs must be unique within the chain")
            correction_ids.add(correction_id)
            if correction_view["document_kind"] != "credit_note_candidate":
                raise _ValueError("correction kind must remain credit_note_candidate")
            if correction_view["original_document_id"] != document_id:
                raise _ValueError("correction must link the exact original document")
            correction_timestamp = _canonical_timestamp_text(
                correction_view["recorded_at"], "correction recorded_at"
            )
            if correction_timestamp <= last_timestamp:
                raise _ValueError("correction timestamps must be strictly increasing")
            last_timestamp = correction_timestamp
            _safe_identifier(
                correction_view["evidence_reference"], "evidence_reference"
            )
            for field in (
                "vat_credit_note_status",
                "refund_credit_note_tax_disposition_authority",
                "live_render_or_delivery_authority",
                "provider_observation_direct_tax_document_effect",
                "direct_entitlement_effect",
            ):
                if (
                    _type(correction_view[field]) is not _bool
                    or correction_view[field] is not False
                ):
                    raise _ValueError(f"correction {field} must remain false")
            rebuilt_corrections += (_clone_builtin(correction),)
        return (
            ("document_id", document_id),
            ("document_kind", kind),
            ("owner_reference", owner),
            ("plan_key", plan_key),
            ("gross_amount_minor", amount),
            ("currency", "GBP"),
            ("gross_price_statement", _vat_copy),
            ("recorded_at", timestamp),
            ("evidence_reference", evidence),
            (
                "simplified_invoice_amount_limb",
                item["simplified_invoice_amount_limb"],
            ),
            ("simplified_invoice_authority", False),
            ("vat_invoice_status", False),
            ("live_render_or_delivery_authority", False),
            ("provider_observation_direct_tax_document_effect", False),
            ("direct_entitlement_effect", False),
            ("corrections", rebuilt_corrections),
        )

    def _validate_authority(value):
        if _type(value) is not _tuple or value != _projection:
            raise _ValueError("S2E prerequisite structure is invalid")
        return _clone_builtin(value)

    def _validate_document(value):
        return _validate_document_state(value)

    def validate_tax_invoice_prerequisite(value):
        return _validate_authority(value)

    def project_tax_invoice_prerequisite(value):
        return _clone_builtin(_validate_authority(value))

    def copy_tax_invoice_prerequisite(value):
        return _clone_builtin(_validate_authority(value))

    def create_billing_document_candidate(*args, **kwargs):
        """Create a neutral gross-only receipt or invoice candidate."""

        positional, facts = _exact_call(
            args,
            kwargs,
            1,
            _create_candidate_input_fields,
            "document candidate creation",
        )
        prerequisite = positional[0]
        (
            document_id,
            document_kind,
            owner_reference,
            plan_key,
            gross_amount_minor,
            currency,
            recorded_at,
            evidence_reference,
        ) = facts

        _validate_authority(prerequisite)
        if _type(document_kind) is not _str or document_kind not in (
            "payment_receipt_candidate",
            "invoice_candidate",
        ):
            raise _ValueError(
                "document_kind must be payment_receipt_candidate or invoice_candidate"
            )
        item = _catalogue_item(plan_key)
        item_view = _dict(item)
        if _type(gross_amount_minor) is not _int or _type(gross_amount_minor) is _bool:
            raise _TypeError("gross_amount_minor must be an exact integer")
        if gross_amount_minor != item_view["gross_amount_minor"]:
            raise _ValueError("gross_amount_minor must equal the settled gross price")
        if _type(currency) is not _str or currency != "GBP":
            raise _ValueError("currency must be exact GBP")
        timestamp = _utc_text(recorded_at, "recorded_at")
        state = (
            ("document_id", _safe_identifier(document_id, "document_id")),
            ("document_kind", document_kind),
            ("owner_reference", _safe_identifier(owner_reference, "owner_reference")),
            ("plan_key", plan_key),
            ("gross_amount_minor", gross_amount_minor),
            ("currency", currency),
            ("gross_price_statement", _vat_copy),
            ("recorded_at", timestamp),
            (
                "evidence_reference",
                _safe_identifier(evidence_reference, "evidence_reference"),
            ),
            (
                "simplified_invoice_amount_limb",
                item_view["simplified_invoice_amount_limb"],
            ),
            ("simplified_invoice_authority", False),
            ("vat_invoice_status", False),
            ("live_render_or_delivery_authority", False),
            ("provider_observation_direct_tax_document_effect", False),
            ("direct_entitlement_effect", False),
            ("corrections", ()),
        )
        return _validate_document_state(state)

    def append_document_correction(*args, **kwargs):
        """Append a linked, non-tax, non-entitling correction candidate."""

        positional, facts = _exact_call(
            args,
            kwargs,
            2,
            _append_correction_input_fields,
            "document correction append",
        )
        prerequisite, document = positional
        (
            correction_id,
            original_document_id,
            recorded_at,
            evidence_reference,
        ) = facts

        _validate_authority(prerequisite)
        state = _validate_document(document)
        view = _dict(state)
        expected_original = view["document_id"]
        original = _safe_identifier(original_document_id, "original_document_id")
        if original != expected_original:
            raise _ValueError("correction must link the exact original document")
        identifier = _safe_identifier(correction_id, "correction_id")
        existing = view["corrections"]
        existing_ids = _set(_dict(item)["correction_id"] for item in existing)
        if identifier == expected_original or identifier in existing_ids:
            raise _ValueError("correction_id must be unique within the document chain")
        timestamp = _utc_text(recorded_at, "recorded_at")
        last_timestamp = view["recorded_at"]
        if existing:
            last_timestamp = _dict(existing[-1])["recorded_at"]
        if timestamp <= last_timestamp:
            raise _ValueError(
                "correction recorded_at must be strictly later than the chain"
            )
        correction = (
            ("correction_id", identifier),
            ("document_kind", "credit_note_candidate"),
            ("original_document_id", original),
            ("recorded_at", timestamp),
            (
                "evidence_reference",
                _safe_identifier(evidence_reference, "evidence_reference"),
            ),
            ("vat_credit_note_status", False),
            ("refund_credit_note_tax_disposition_authority", False),
            ("live_render_or_delivery_authority", False),
            ("provider_observation_direct_tax_document_effect", False),
            ("direct_entitlement_effect", False),
        )
        replaced = _tuple(
            (key, existing + (correction,)) if key == "corrections" else (key, value)
            for key, value in state
        )
        return _validate_document_state(replaced)

    def validate_billing_document_candidate(value):
        return _validate_document(value)

    def project_billing_document_candidate(value):
        return _clone_builtin(_validate_document(value))

    def copy_billing_document_candidate(value):
        return _clone_builtin(_validate_document(value))

    authority = _clone_builtin(_projection)

    return (
        _contract_version,
        _vat_copy,
        authority,
        validate_tax_invoice_prerequisite,
        project_tax_invoice_prerequisite,
        copy_tax_invoice_prerequisite,
        create_billing_document_candidate,
        append_document_correction,
        validate_billing_document_candidate,
        project_billing_document_candidate,
        copy_billing_document_candidate,
    )


(
    CONTRACT_VERSION,
    GROSS_PRICE_STATEMENT,
    TAX_INVOICE_PREREQUISITE,
    validate_tax_invoice_prerequisite,
    project_tax_invoice_prerequisite,
    copy_tax_invoice_prerequisite,
    create_billing_document_candidate,
    append_document_correction,
    validate_billing_document_candidate,
    project_billing_document_candidate,
    copy_billing_document_candidate,
) = _build_tax_invoice_prerequisite_contract()

__all__ = (
    "CONTRACT_VERSION",
    "GROSS_PRICE_STATEMENT",
    "TAX_INVOICE_PREREQUISITE",
    "validate_tax_invoice_prerequisite",
    "project_tax_invoice_prerequisite",
    "copy_tax_invoice_prerequisite",
    "create_billing_document_candidate",
    "append_document_correction",
    "validate_billing_document_candidate",
    "project_billing_document_candidate",
    "copy_billing_document_candidate",
)
