"""Adversarial tests for the W10-S2E tax/invoice prerequisite contract."""

from __future__ import annotations

import ast
import builtins
import hashlib
import inspect
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path

import pytest

import reserved.billing.tax_invoice_prerequisite_contract as subject


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reserved" / "billing" / "tax_invoice_prerequisite_contract.py"
DOC = ROOT / "docs" / "W10_S2E_TAX_INVOICE_PREREQUISITE.md"

EXPECTED_REPOSITORY_SOURCES = (
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
EXPECTED_PRICES = (
    {
        "plan_key": "monthly",
        "gross_amount_minor": 2900,
        "currency": "GBP",
        "cadence_count": 1,
        "cadence_unit": "month",
        "simplified_invoice_amount_limb": True,
        "simplified_invoice_authority": False,
    },
    {
        "plan_key": "six_month",
        "gross_amount_minor": 15600,
        "currency": "GBP",
        "cadence_count": 6,
        "cadence_unit": "month",
        "simplified_invoice_amount_limb": True,
        "simplified_invoice_authority": False,
    },
    {
        "plan_key": "yearly",
        "gross_amount_minor": 28800,
        "currency": "GBP",
        "cadence_count": 1,
        "cadence_unit": "year",
        "simplified_invoice_amount_limb": False,
        "simplified_invoice_authority": False,
    },
)
EXPECTED_FALSE_AUTHORITIES = (
    "vat_calculation_authority",
    "net_amount_derivation_authority",
    "vat_amount_derivation_authority",
    "vat_invoice_issuance_authority",
    "simplified_invoice_issuance_authority",
    "stripe_tax_activation_authority",
    "refund_credit_note_tax_disposition_authority",
    "live_receipt_render_or_delivery_authority",
    "provider_observation_direct_tax_document_effect",
    "provider_observation_direct_entitlement_effect",
    "document_candidate_direct_entitlement_effect",
)
EXPECTED_PROHIBITED = (
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


def authority_tuple():
    return subject.project_tax_invoice_prerequisite(
        subject.TAX_INVOICE_PREREQUISITE
    )


def authority():
    return dict(authority_tuple())


def candidate_facts(**overrides):
    values = {
        "document_id": "document.001",
        "document_kind": "payment_receipt_candidate",
        "owner_reference": "owner.001",
        "plan_key": "monthly",
        "gross_amount_minor": 2900,
        "currency": "GBP",
        "recorded_at": datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc),
        "evidence_reference": "billing.observation.001",
    }
    values.update(overrides)
    return values


def make_candidate(**overrides):
    return subject.create_billing_document_candidate(
        subject.TAX_INVOICE_PREREQUISITE, **candidate_facts(**overrides)
    )


def exact_builtin_walk(value):
    if type(value) is tuple:
        for item in value:
            exact_builtin_walk(item)
        return
    assert type(value) in (str, int, bool)


def test_exact_contract_identity_tree_and_repository_source_hashes():
    projected = authority()
    assert projected["contract_version"] == "W10-S2E/2026-09-04/v1"
    assert projected["integration_head"] == (
        "54a82476939dce8f75af62d73aeb477e11a1260c"
    )
    assert projected["integration_tree"] == (
        "26b1aa6a1302195770534dc41caf099bcdd7cb06"
    )
    assert projected["repository_sources"] == EXPECTED_REPOSITORY_SOURCES
    for _, relative_path, expected_hash, _ in EXPECTED_REPOSITORY_SOURCES:
        actual = hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest()
        assert actual == expected_hash


def test_exact_settled_gross_catalogue_and_qualified_copy_only():
    projected = authority()
    assert projected["gross_price_statement"] == (
        "inclusive of VAT where applicable"
    )
    assert subject.GROSS_PRICE_STATEMENT == "inclusive of VAT where applicable"
    assert tuple(dict(item) for item in projected["gross_catalogue"]) == EXPECTED_PRICES
    text = repr(projected["gross_catalogue"])
    assert "20%" not in text
    assert "580" not in text
    assert "2600" not in text
    assert "2400" not in text


def test_every_tax_provider_document_and_entitlement_authority_is_false():
    flags = dict(authority()["authority_flags"])
    assert tuple(flags) == EXPECTED_FALSE_AUTHORITIES
    assert set(flags.values()) == {False}


def test_amount_limb_is_explicitly_insufficient_for_all_three_plans():
    plans = {item["plan_key"]: item for item in EXPECTED_PRICES}
    assert plans["monthly"]["simplified_invoice_amount_limb"] is True
    assert plans["six_month"]["simplified_invoice_amount_limb"] is True
    assert plans["yearly"]["simplified_invoice_amount_limb"] is False
    assert all(not item["simplified_invoice_authority"] for item in plans.values())
    assert dict(authority()["authority_flags"])[
        "simplified_invoice_issuance_authority"
    ] is False


def test_neutral_document_concepts_are_distinct_and_never_live_or_entitling():
    concepts = dict(authority()["document_concepts"])
    assert tuple(concepts) == (
        "payment_receipt_candidate",
        "invoice_candidate",
        "credit_note_candidate",
    )
    assert len(set(dict(value)["meaning"] for value in concepts.values())) == 3
    for details in concepts.values():
        values = dict(details)
        assert values["live_render_or_delivery_authority"] is False
        assert values["direct_entitlement_effect"] is False
    assert dict(concepts["payment_receipt_candidate"])["vat_invoice_status"] is False
    assert dict(concepts["invoice_candidate"])["vat_invoice_status"] is False
    assert dict(concepts["credit_note_candidate"])["vat_credit_note_status"] is False


def test_specialist_inputs_are_future_not_accepted_and_q1_q2_q3_are_preserved():
    projected = authority()
    assert projected["future_specialist_inputs"] == (
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
    assert projected["preserved_founder_questions"] == (
        ("Q1", "refunds", "unresolved"),
        ("Q2", "paid_access_surface", "unresolved"),
        (
            "Q3",
            "post_settlement_dispute_chargeback_reversal_consequences",
            "unresolved",
        ),
    )
    assert projected["assurance_status"] == (
        "contract_only_not_legal_tax_assurance_s2_completion_or_s6_implementation"
    )


def test_production_and_w9_gates_remain_exact():
    assert authority()["production_gates"] == (
        "accepted_finance_accounting_vat_profile",
        "accepted_tax_legal_supply_customer_and_geography_classification",
        "accepted_invoice_receipt_credit_note_schema_and_customer_copy",
        "accepted_privacy_security_data_minimisation_and_retention_design",
        "accepted_w9_retention_erasure_legal_hold_backup_and_custody_evidence",
        "reviewed_stripe_sandbox_configuration_and_sample_artifacts",
        "target_reconciliation_audit_access_recovery_and_operational_evidence",
        "separate_founder_production_activation_and_release_authority",
    )


def test_official_sources_are_exact_urls_with_bounded_findings():
    sources = dict((name, (url, finding)) for name, url, finding in authority()["official_sources"])
    assert sources["hmrc_vat_invoices"][0] == (
        "https://www.gov.uk/guidance/vat-guide-notice-700"
    )
    assert sources["hmrc_vat_records"][0] == (
        "https://www.gov.uk/charge-reclaim-record-vat/keeping-vat-records"
    )
    assert sources["hmrc_digital_services"][0] == (
        "https://www.gov.uk/guidance/the-vat-rules-if-you-supply-digital-services-to-private-consumers"
    )
    assert sources["stripe_tax_capability"][0] == (
        "https://docs.stripe.com/tax/set-up"
    )
    assert all(url.startswith("https://") and finding for url, finding in sources.values())


@pytest.mark.parametrize(
    ("plan_key", "amount", "limb"),
    (("monthly", 2900, True), ("six_month", 15600, True), ("yearly", 28800, False)),
)
def test_candidate_factory_retains_only_exact_gross_plan_facts(plan_key, amount, limb):
    handle = make_candidate(plan_key=plan_key, gross_amount_minor=amount)
    projected = dict(subject.project_billing_document_candidate(handle))
    assert projected["plan_key"] == plan_key
    assert projected["gross_amount_minor"] == amount
    assert projected["currency"] == "GBP"
    assert projected["gross_price_statement"] == "inclusive of VAT where applicable"
    assert projected["simplified_invoice_amount_limb"] is limb
    assert projected["simplified_invoice_authority"] is False
    assert projected["vat_invoice_status"] is False
    assert projected["live_render_or_delivery_authority"] is False
    assert projected["provider_observation_direct_tax_document_effect"] is False
    assert projected["direct_entitlement_effect"] is False


def test_receipt_and_invoice_candidates_are_neutral_and_credit_note_requires_linked_append():
    receipt = dict(subject.project_billing_document_candidate(make_candidate()))
    invoice = dict(
        subject.project_billing_document_candidate(
            make_candidate(document_id="document.002", document_kind="invoice_candidate")
        )
    )
    assert receipt["document_kind"] == "payment_receipt_candidate"
    assert invoice["document_kind"] == "invoice_candidate"
    with pytest.raises(ValueError, match="document_kind"):
        make_candidate(document_kind="credit_note_candidate")
    with pytest.raises(ValueError, match="document_kind"):
        make_candidate(document_kind="VAT invoice")


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("vat_rate", 20),
        ("net_amount", 2417),
        ("vat_amount", 483),
        ("supplier_vat_registration_id", "GB123456789"),
        ("customer_vat_registration_id", "GB987654321"),
        ("customer_tax_status", "VAT registered"),
        ("customer_location", "GB"),
        ("place_of_supply", "UK"),
        ("provider_zero_tax_result", True),
        ("vat_invoice_label", "VAT invoice"),
        ("vat_credit_note_label", "VAT credit note"),
        ("entitlement_effect", True),
    ),
)
def test_factory_rejects_extra_tax_identity_location_provider_and_access_inputs(field, value):
    assert field in authority()["prohibited_inputs"]
    with pytest.raises(TypeError, match=field):
        make_candidate(**{field: value})


@pytest.mark.parametrize(
    "overrides",
    (
        {"gross_amount_minor": 3480},
        {"gross_amount_minor": True},
        {"currency": "USD"},
        {"plan_key": "monthly_discounted"},
        {"document_kind": "receipt"},
    ),
)
def test_factory_rejects_added_tax_discount_wrong_currency_or_ambiguous_labels(overrides):
    with pytest.raises((TypeError, ValueError)):
        make_candidate(**overrides)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("document_id", "sk.live.123"),
        ("owner_reference", "credential_api_key_123"),
        ("evidence_reference", "access/token/123"),
        ("evidence_reference", "whsec_endpointsecret"),
    ),
)
def test_retained_identifiers_reject_secret_or_credential_shaped_material(field, value):
    with pytest.raises(ValueError):
        make_candidate(**{field: value})


def test_innocuous_secret_substrings_are_not_mechanically_blocked():
    candidate = make_candidate(
        document_id="secretariat.001",
        owner_reference="tokenisation.001",
        evidence_reference="keynote.001",
    )
    projected = dict(subject.project_billing_document_candidate(candidate))
    assert projected["document_id"] == "secretariat.001"


class StatefulTimezone(tzinfo):
    def __init__(self):
        self.calls = 0

    def utcoffset(self, value):
        self.calls += 1
        return timedelta(0 if self.calls == 1 else -1)

    def dst(self, value):
        return timedelta(0)


def test_datetime_inputs_require_exact_builtin_timezone_utc_and_project_stably():
    hostile = StatefulTimezone()
    with pytest.raises(TypeError, match="timezone.utc"):
        make_candidate(recorded_at=datetime(2026, 9, 4, 12, 0, tzinfo=hostile))
    assert hostile.calls == 0

    class DateTimeSubclass(datetime):
        pass

    with pytest.raises(TypeError, match="exact datetime"):
        make_candidate(
            recorded_at=DateTimeSubclass(2026, 9, 4, 12, 0, tzinfo=timezone.utc)
        )
    candidate = make_candidate()
    first = dict(subject.project_billing_document_candidate(candidate))["recorded_at"]
    second = dict(subject.project_billing_document_candidate(candidate))["recorded_at"]
    assert first == second == "2026-09-04T12:00:00.000000Z"


@pytest.mark.parametrize(
    "invalid",
    (
        "2026-13-01T00:00:00.000000Z",
        "2026-04-31T00:00:00.000000Z",
        "2026-01-01T24:00:00.000000Z",
        "2026-01-01T00:60:00.000000Z",
        "2026-01-01T00:00:60.000000Z",
        "0000-01-01T00:00:00.000000Z",
        "2025-02-29T00:00:00.000000Z",
    ),
)
def test_detached_candidate_rejects_impossible_calendar_and_time_values(invalid):
    detached = tuple(
        (key, invalid) if key == "recorded_at" else (key, value)
        for key, value in make_candidate()
    )
    with pytest.raises(ValueError, match="valid UTC timestamp"):
        subject.validate_billing_document_candidate(detached)


@pytest.mark.parametrize(
    "invalid",
    (
        "2026-99-01T00:00:00.000000Z",
        "2026-02-30T00:00:00.000000Z",
        "2026-01-01T99:00:00.000000Z",
        "2026-01-01T00:99:00.000000Z",
        "2026-01-01T00:00:99.000000Z",
        "0000-12-31T23:59:59.999999Z",
        "2100-02-29T00:00:00.000000Z",
    ),
)
def test_detached_correction_rejects_impossible_calendar_and_time_values(invalid):
    corrected = subject.append_document_correction(
        subject.TAX_INVOICE_PREREQUISITE,
        make_candidate(),
        correction_id="correction.001",
        original_document_id="document.001",
        recorded_at=datetime(2026, 9, 4, 12, 1, tzinfo=timezone.utc),
        evidence_reference="billing.observation.002",
    )
    corrections = dict(corrected)["corrections"]
    forged_correction = tuple(
        (key, invalid) if key == "recorded_at" else (key, value)
        for key, value in corrections[0]
    )
    detached = tuple(
        (key, (forged_correction,)) if key == "corrections" else (key, value)
        for key, value in corrected
    )
    with pytest.raises(ValueError, match="valid UTC timestamp"):
        subject.validate_billing_document_candidate(detached)


def test_detached_timestamp_validation_accepts_valid_leap_day_and_canonical_boundary():
    leap = make_candidate(
        recorded_at=datetime(2024, 2, 29, 23, 59, 59, 999999, tzinfo=timezone.utc)
    )
    assert dict(subject.validate_billing_document_candidate(leap))["recorded_at"] == (
        "2024-02-29T23:59:59.999999Z"
    )
    corrected = subject.append_document_correction(
        subject.TAX_INVOICE_PREREQUISITE,
        leap,
        correction_id="correction.001",
        original_document_id="document.001",
        recorded_at=datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc),
        evidence_reference="billing.observation.002",
    )
    correction = dict(dict(corrected)["corrections"][0])
    assert correction["recorded_at"] == "2024-03-01T00:00:00.000000Z"


def test_append_only_correction_is_linked_strictly_later_and_non_entitling():
    original = make_candidate()
    corrected = subject.append_document_correction(
        subject.TAX_INVOICE_PREREQUISITE,
        original,
        correction_id="correction.001",
        original_document_id="document.001",
        recorded_at=datetime(2026, 9, 4, 12, 1, tzinfo=timezone.utc),
        evidence_reference="billing.observation.002",
    )
    assert dict(subject.project_billing_document_candidate(original))["corrections"] == ()
    correction = dict(
        dict(subject.project_billing_document_candidate(corrected))["corrections"][0]
    )
    assert correction == {
        "correction_id": "correction.001",
        "document_kind": "credit_note_candidate",
        "original_document_id": "document.001",
        "recorded_at": "2026-09-04T12:01:00.000000Z",
        "evidence_reference": "billing.observation.002",
        "vat_credit_note_status": False,
        "refund_credit_note_tax_disposition_authority": False,
        "live_render_or_delivery_authority": False,
        "provider_observation_direct_tax_document_effect": False,
        "direct_entitlement_effect": False,
    }


def test_correction_rejects_unlinked_backdated_equal_time_and_duplicate_id():
    original = make_candidate()
    with pytest.raises(ValueError, match="exact original"):
        subject.append_document_correction(
            subject.TAX_INVOICE_PREREQUISITE,
            original,
            correction_id="correction.001",
            original_document_id="document.other",
            recorded_at=datetime(2026, 9, 4, 12, 1, tzinfo=timezone.utc),
            evidence_reference="billing.observation.002",
        )
    for timestamp in (
        datetime(2026, 9, 4, 11, 59, tzinfo=timezone.utc),
        datetime(2026, 9, 4, 12, 0, tzinfo=timezone.utc),
    ):
        with pytest.raises(ValueError, match="strictly later"):
            subject.append_document_correction(
                subject.TAX_INVOICE_PREREQUISITE,
                original,
                correction_id="correction.001",
                original_document_id="document.001",
                recorded_at=timestamp,
                evidence_reference="billing.observation.002",
            )
    first = subject.append_document_correction(
        subject.TAX_INVOICE_PREREQUISITE,
        original,
        correction_id="correction.001",
        original_document_id="document.001",
        recorded_at=datetime(2026, 9, 4, 12, 1, tzinfo=timezone.utc),
        evidence_reference="billing.observation.002",
    )
    with pytest.raises(ValueError, match="unique"):
        subject.append_document_correction(
            subject.TAX_INVOICE_PREREQUISITE,
            first,
            correction_id="correction.001",
            original_document_id="document.001",
            recorded_at=datetime(2026, 9, 4, 12, 2, tzinfo=timezone.utc),
            evidence_reference="billing.observation.003",
        )
    with pytest.raises(ValueError, match="strictly later"):
        subject.append_document_correction(
            subject.TAX_INVOICE_PREREQUISITE,
            first,
            correction_id="correction.002",
            original_document_id="document.001",
            recorded_at=datetime(2026, 9, 4, 12, 0, 30, tzinfo=timezone.utc),
            evidence_reference="billing.observation.003",
        )


def test_projections_are_detached_exact_immutable_builtins_only():
    first = authority_tuple()
    second = authority_tuple()
    assert first == second
    assert first is not second
    exact_builtin_walk(first)
    candidate = make_candidate()
    candidate_first = subject.project_billing_document_candidate(candidate)
    candidate_second = subject.project_billing_document_candidate(candidate)
    assert candidate_first == candidate_second
    assert candidate_first is not candidate_second
    exact_builtin_walk(candidate_first)
    with pytest.raises(TypeError):
        candidate_first[0] = ("document_id", "forged")


def test_values_are_detached_structures_and_validation_is_not_issuance_authority():
    authority_value = subject.TAX_INVOICE_PREREQUISITE
    clone = subject.copy_tax_invoice_prerequisite(authority_value)
    assert type(authority_value) is tuple
    assert clone == authority_value and clone is not authority_value
    assert subject.validate_tax_invoice_prerequisite(tuple(authority_value)) == authority_tuple()
    candidate = make_candidate()
    rebuilt = tuple((key, value) for key, value in candidate)
    validated = subject.validate_billing_document_candidate(rebuilt)
    assert validated == candidate and validated is not candidate
    assert dict(validated)["vat_invoice_status"] is False
    assert dict(validated)["direct_entitlement_effect"] is False


def test_saved_protocol_resists_public_global_rebinding(monkeypatch):
    authority_handle = subject.TAX_INVOICE_PREREQUISITE
    project_authority = subject.project_tax_invoice_prerequisite
    create_candidate = subject.create_billing_document_candidate
    project_candidate = subject.project_billing_document_candidate
    copy_candidate = subject.copy_billing_document_candidate
    expected = project_authority(authority_handle)
    candidate = make_candidate()
    candidate_expected = project_candidate(candidate)

    monkeypatch.setattr(subject, "GROSS_PRICE_STATEMENT", "VAT included at 20%")
    monkeypatch.setattr(subject, "TAX_INVOICE_PREREQUISITE", object())
    monkeypatch.setattr(subject, "dict", lambda value: {"forged": True}, raising=False)
    monkeypatch.setattr(subject, "tuple", list, raising=False)

    assert project_authority(authority_handle) == expected
    assert project_candidate(candidate) == candidate_expected
    clone = copy_candidate(candidate)
    assert project_candidate(clone) == candidate_expected
    new_candidate = create_candidate(
        authority_handle,
        document_id="document.002",
        document_kind="invoice_candidate",
        owner_reference="owner.001",
        plan_key="yearly",
        gross_amount_minor=28800,
        currency="GBP",
        recorded_at=datetime(2026, 9, 4, 13, 0, tzinfo=timezone.utc),
        evidence_reference="billing.observation.002",
    )
    assert dict(project_candidate(new_candidate))["vat_invoice_status"] is False


def test_mutable_callable_defaults_cannot_supply_candidate_or_correction_facts():
    create = subject.create_billing_document_candidate
    append = subject.append_document_correction
    original = make_candidate()
    create_defaults = create.__defaults__
    create_keyword_defaults = create.__kwdefaults__
    append_defaults = append.__defaults__
    append_keyword_defaults = append.__kwdefaults__
    try:
        create.__defaults__ = (subject.TAX_INVOICE_PREREQUISITE,)
        create.__kwdefaults__ = candidate_facts(
            document_id="document.metadata",
            document_kind="invoice_candidate",
        )
        append.__defaults__ = (subject.TAX_INVOICE_PREREQUISITE, original)
        append.__kwdefaults__ = {
            "correction_id": "correction.metadata",
            "original_document_id": "document.001",
            "recorded_at": datetime(2026, 9, 4, 12, 1, tzinfo=timezone.utc),
            "evidence_reference": "billing.observation.metadata",
        }

        with pytest.raises(TypeError, match="exactly 1 positional"):
            create()
        with pytest.raises(TypeError, match="exactly 2 positional"):
            append()
    finally:
        create.__defaults__ = create_defaults
        create.__kwdefaults__ = create_keyword_defaults
        append.__defaults__ = append_defaults
        append.__kwdefaults__ = append_keyword_defaults


def test_candidate_and_correction_issuers_require_exact_call_shape():
    authority_handle = subject.TAX_INVOICE_PREREQUISITE
    facts = candidate_facts()
    original = make_candidate()
    correction_facts = {
        "correction_id": "correction.001",
        "original_document_id": "document.001",
        "recorded_at": datetime(2026, 9, 4, 12, 1, tzinfo=timezone.utc),
        "evidence_reference": "billing.observation.002",
    }

    with pytest.raises(TypeError, match="exactly 1 positional"):
        subject.create_billing_document_candidate()
    with pytest.raises(TypeError, match="exactly 1 positional"):
        subject.create_billing_document_candidate(authority_handle, "document.001", **facts)
    with pytest.raises(TypeError, match="exact named facts"):
        subject.create_billing_document_candidate(
            authority_handle,
            **{key: value for key, value in facts.items() if key != "evidence_reference"},
        )
    with pytest.raises(TypeError, match="unsupported named fact authority"):
        subject.create_billing_document_candidate(
            authority_handle,
            **(facts | {"authority": authority_handle}),
        )

    with pytest.raises(TypeError, match="exactly 2 positional"):
        subject.append_document_correction(authority_handle, **correction_facts)
    with pytest.raises(TypeError, match="exactly 2 positional"):
        subject.append_document_correction(
            authority_handle, original, "correction.001", **correction_facts
        )
    with pytest.raises(TypeError, match="exact named facts"):
        subject.append_document_correction(
            authority_handle,
            original,
            **{
                key: value
                for key, value in correction_facts.items()
                if key != "evidence_reference"
            },
        )
    with pytest.raises(TypeError, match="unsupported named fact document"):
        subject.append_document_correction(
            authority_handle,
            original,
            **(correction_facts | {"document": original}),
        )


def test_no_mutable_admission_registries_exist_for_either_structural_value():
    source = SOURCE.read_text(encoding="utf-8")
    assert "_authority_registry" not in source
    assert "_document_registry" not in source
    assert "_authority_live" not in source
    assert "_document_live" not in source
    assert "producer-issued" not in source


def test_hostile_reconstruction_cannot_enable_authority_for_either_value_type():
    authority_value = list(authority_tuple())
    flags_index = next(
        index for index, item in enumerate(authority_value) if item[0] == "authority_flags"
    )
    flags = list(authority_value[flags_index][1])
    flags[0] = ("vat_calculation_authority", True)
    authority_value[flags_index] = ("authority_flags", tuple(flags))
    with pytest.raises(ValueError, match="prerequisite structure"):
        subject.validate_tax_invoice_prerequisite(tuple(authority_value))

    document_value = list(make_candidate())
    status_index = next(
        index for index, item in enumerate(document_value) if item[0] == "vat_invoice_status"
    )
    document_value[status_index] = ("vat_invoice_status", True)
    with pytest.raises(ValueError, match="must remain false"):
        subject.validate_billing_document_candidate(tuple(document_value))


def test_supported_protocol_performs_no_file_io(monkeypatch):
    project = subject.project_tax_invoice_prerequisite
    create = subject.create_billing_document_candidate

    def forbidden_open(*args, **kwargs):
        raise AssertionError("S2E contract attempted file I/O")

    monkeypatch.setattr(builtins, "open", forbidden_open)
    projected = dict(project(subject.TAX_INVOICE_PREREQUISITE))
    assert dict(projected["authority_flags"])["vat_calculation_authority"] is False
    candidate = create(
        subject.TAX_INVOICE_PREREQUISITE,
        document_id="document.099",
        document_kind="invoice_candidate",
        owner_reference="owner.001",
        plan_key="monthly",
        gross_amount_minor=2900,
        currency="GBP",
        recorded_at=datetime(2026, 9, 4, 14, 0, tzinfo=timezone.utc),
        evidence_reference="billing.observation.099",
    )
    assert dict(subject.project_billing_document_candidate(candidate))[
        "live_render_or_delivery_authority"
    ] is False


def test_module_has_no_runtime_provider_database_route_or_entitlement_dependencies():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported_roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_roots.update(
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )
    assert imported_roots <= {"__future__", "datetime", "re"}
    assert not imported_roots.intersection(
        {
            "stripe",
            "requests",
            "httpx",
            "socket",
            "sqlite3",
            "flask",
            "os",
            "reserved",
        }
    )
    signatures = {
        name: tuple(inspect.signature(getattr(subject, name)).parameters)
        for name in subject.__all__
        if callable(getattr(subject, name))
    }
    assert signatures["create_billing_document_candidate"] == ("args", "kwargs")
    assert signatures["append_document_correction"] == ("args", "kwargs")


def test_document_records_exact_scope_and_non_authority_language():
    text = DOC.read_text(encoding="utf-8")
    for phrase in (
        "inclusive of VAT where applicable",
        "amount limb only",
        "not legal or tax assurance",
        "Q1",
        "Q2",
        "Q3",
        "zero direct entitlement effect",
        "no VAT rate, net amount, or VAT amount",
        "does not implement W10-S6",
    ):
        assert phrase.lower() in text.lower()
    for url in (
        "https://www.gov.uk/register-for-vat",
        "https://www.gov.uk/guidance/vat-guide-notice-700",
        "https://www.gov.uk/charge-reclaim-record-vat/keeping-vat-records",
        "https://docs.stripe.com/tax/set-up",
    ):
        assert url in text
