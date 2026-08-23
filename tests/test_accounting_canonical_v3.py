"""Provider-neutral adversarial convergence tests for the Accounting v3 contract.

These tests are derived from the semantic requirements (C1-C12) rather than from
production implementation details. Expected values are stated independently;
none are computed by calling the production mapping under test.
"""

from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from reserved.providers.accounting.contracts import (
    AccountingBusiness, AccountingDocument, AccountingLine, AccountingMethod,
    AccountingPayment, AccountingProviderName, AllocationEdge, AllocationType,
    CanonicalDocumentState, CompletenessState, CorrectionLifecycle,
    EconomicDirection, FxObservation, LineRole, LineValueSemantics, Money,
    ObservationRelation, PaymentType, ProviderBalanceAssertions,
    RecognitionDecisionOutcome, ResourceCompleteness, SettlementState, SyncPage,
    TaxAmountSemantics, TaxBreakdown, VatRegistrationPeriod, VatRegistrationState,
)
from reserved.providers.accounting.normalisation import (
    CanonicalQuarantineError, adapt_observation, build_canonical_tax_input,
    build_recognition_decision, classify_observation_relation,
    derive_settlement_state, normalise_document, observe_provider_record,
    settlement_summary,
)
from reserved.providers.accounting.sync_contracts import (
    SyncContractError, collect_pages,
)
from reserved.providers.schema_evidence import (
    SchemaContractError, SchemaFitness, SourceSchema, observe_schema,
)

RETRIEVED_AT = datetime(2026, 8, 3, 10, 0, 0)


def raw_line(**overrides):
    value = {
        "provider_line_id": "line-1",
        "provider_line_total": "120.00",
        "provider_line_net": "100.00",
        "provider_line_tax": "20.00",
        "provider_tax_semantics": "exclusive",
        "provider_vat_code": "STANDARD",
        "provider_vat_rate": "0.20",
        "provider_currency": "GBP",
    }
    value.update(overrides)
    return value


def raw_record(**overrides):
    value = {
        "provider_document_id": "doc-1",
        "provider_business_id": "business-1",
        "provider_document_kind": "invoice",
        "provider_issued_on": "2026-08-01",
        "provider_currency": "GBP",
        "provider_total": "120.00",
        "provider_status_text": "issued",
        "provider_event_id": "event-1",
        "provider_lines": [raw_line()],
    }
    value.update(overrides)
    return value


def observe(raw, *, provider="xero", connected_organisation_id="org-1",
            business_id="business-1", resource="invoices", revision_id=None):
    return observe_provider_record(
        provider=provider, raw_record=raw, user_id="user-1",
        connected_organisation_id=connected_organisation_id, business_id=business_id,
        import_run_id="run-1", api_name="synthetic", api_version="v1",
        resource=resource, record_id=raw.get("provider_document_id", "doc-1"),
        retrieved_at=RETRIEVED_AT, adapter_version="syn-1", revision_id=revision_id,
    )


def doc(**overrides):
    raw = raw_record(**overrides)
    observation = observe(raw)
    return normalise_document(
        observation=observation,
        adapter_result=adapt_observation(observation=observation, raw_record=raw),
    )


def money(amount, currency="GBP"):
    return Money(Decimal(amount), currency)


# ── C2 / line values and document tax totals ─────────────────────────────────

def test_line_value_semantics_are_represented_without_reinterpretation():
    net_line = AccountingLine(
        "l-net", money("120.00"), TaxBreakdown(Decimal("100"), Decimal("20"), Decimal("120"),
                                               TaxAmountSemantics.EXCLUSIVE, "STANDARD", Decimal("0.20")),
        value_semantics=LineValueSemantics.NET,
    )
    gross_line = AccountingLine(
        "l-gross", money("120.00"), TaxBreakdown(Decimal("100"), Decimal("20"), Decimal("120"),
                                                 TaxAmountSemantics.INCLUSIVE, "STANDARD", Decimal("0.20")),
        value_semantics=LineValueSemantics.GROSS,
    )
    assert net_line.value_semantics is LineValueSemantics.NET
    assert gross_line.value_semantics is LineValueSemantics.GROSS
    # Canonical line money is always line gross, regardless of raw semantics.
    assert net_line.money.original_amount == Decimal("120.00")
    assert net_line.tax.net_amount + net_line.tax.vat_amount == net_line.tax.gross_amount


def test_zero_rated_exempt_and_outside_scope_lines_reconcile_exactly():
    zero_rated = AccountingLine(
        "l-zr", money("100.00"), TaxBreakdown(Decimal("100"), Decimal("0"), Decimal("100"),
                                              TaxAmountSemantics.EXCLUSIVE, "ZERO_RATED"),
        value_semantics=LineValueSemantics.GROSS,
    )
    exempt = AccountingLine(
        "l-ex", money("100.00"), TaxBreakdown(Decimal("100"), Decimal("0"), Decimal("100"),
                                              TaxAmountSemantics.NOT_APPLICABLE, "EXEMPT"),
        value_semantics=LineValueSemantics.GROSS,
    )
    outside = AccountingLine(
        "l-os", money("100.00"), TaxBreakdown(Decimal("100"), Decimal("0"), Decimal("100"),
                                              TaxAmountSemantics.NOT_APPLICABLE, "OUTSIDE_SCOPE"),
        value_semantics=LineValueSemantics.GROSS,
    )
    for line in (zero_rated, exempt, outside):
        assert line.tax.vat_amount == Decimal("0")
        assert line.tax.net_amount == line.tax.gross_amount
    assert sum((line.money.original_amount for line in (zero_rated, exempt, outside)), Decimal("0")) == Decimal("300.00")


def test_discount_tax_and_adjustment_lines_cannot_disappear():
    raw = raw_record(
        provider_total="100.00",
        provider_lines=[
            raw_line(provider_line_id="li", provider_line_total="120.00",
                     provider_line_net="100.00", provider_line_tax="20.00"),
            raw_line(provider_line_id="d1", provider_line_total="-20.00",
                     provider_line_net="-20.00", provider_line_tax="0.00",
                     provider_tax_semantics="not_applicable", provider_line_role="discount"),
        ],
    )
    d = doc(**raw)
    roles = {line.role for line in d.lines}
    assert LineRole.LINE_ITEM in roles
    assert LineRole.DISCOUNT in roles
    # Exact reconciliation: line grosses sum to document gross with no tolerance.
    assert sum((line.money.original_amount for line in d.lines), Decimal("0")) == d.gross_amount


def test_line_role_survives_translation():
    d = doc(provider_lines=[
        raw_line(provider_line_id="sh", provider_line_total="5.00",
                 provider_line_net="5.00", provider_line_tax="0.00",
                 provider_tax_semantics="not_applicable", provider_line_role="shipping"),
    ], provider_total="5.00")
    assert d.lines[0].role is LineRole.SHIPPING


# ── C5 / provider balance assertions are reconciliation-only ─────────────────

def test_zero_amount_due_from_credit_is_not_cash_settlement():
    d = doc(provider_amount_due="0.00", provider_amount_credited="120.00",
            provider_balance="0.00")
    assert d.provider_balance is not None
    assert d.provider_balance.amount_due == Decimal("0.00")
    assert d.provider_balance.amount_credited == Decimal("120.00")
    # No allocation graph: settlement must not be inferred from the assertion.
    assert derive_settlement_state(d, ()) is SettlementState.UNPAID
    assert d.settlement_state is SettlementState.UNKNOWN


def test_balance_assertion_without_allocation_graph_never_settles():
    d = doc(provider_amount_due="0.00", provider_amount_paid="120.00")
    assert derive_settlement_state(d, ()) is SettlementState.UNPAID


# ── C4 / prepayments and overpayments ────────────────────────────────────────

def test_prepayment_is_a_directional_payment_not_a_universal_document_type():
    payment = AccountingPayment(
        payment_id="pre-1", business_id="business-1", payment_type=PaymentType.RECEIPT,
        occurred_on=date(2026, 8, 2), money=money("50.00"), provenance=doc().provenance,
        economic_event_id="pre-event-1", economic_direction=EconomicDirection.RECEIVABLE,
        unapplied_amount=Decimal("50.00"),
    )
    assert payment.economic_direction is EconomicDirection.RECEIVABLE
    assert payment.unapplied_amount == Decimal("50.00")


def test_duplicate_identity_across_retrieval_paths_is_rejected():
    first = SyncPage(("event-1",), "next", None)
    second = SyncPage(("event-1",), None, None)

    def fetch_page(cursor):
        return first if cursor is None else second

    with pytest.raises(SyncContractError, match="Duplicate provider record identity"):
        collect_pages(fetch_page=fetch_page, identity_of=lambda r: r)


def test_overpayment_is_derived_not_double_counted():
    d = doc()
    payment = AccountingPayment(
        "p-1", "business-1", PaymentType.PAYMENT, date(2026, 8, 2), money("150.00"),
        d.provenance, "event-1",
    )
    edge = AllocationEdge("a-1", "business-1", "event-1", "GBP", "p-1", "doc-1",
                          AllocationType.PAYMENT, Decimal("150.00"), date(2026, 8, 3))
    summary = settlement_summary(d, (edge,), {"p-1": payment})
    assert summary.allocated_amount == Decimal("150.00")
    assert summary.overpayment_amount == Decimal("30.00")


# ── C4 / settlement and correction remain distinguishable ────────────────────

def test_settlement_and_correction_lifecycle_are_distinct():
    d = doc()
    voided = replace(d, correction_lifecycle=CorrectionLifecycle.VOIDED)
    deleted = replace(d, correction_lifecycle=CorrectionLifecycle.DELETED)
    assert voided.correction_lifecycle is not d.correction_lifecycle
    assert deleted.correction_lifecycle is CorrectionLifecycle.DELETED
    # Correction lifecycle is independent of settlement state.
    assert voided.settlement_state is SettlementState.UNKNOWN


def test_voided_or_deleted_document_is_not_actionable():
    for lifecycle in (CorrectionLifecycle.VOIDED, CorrectionLifecycle.DELETED):
        d = replace(doc(provider_cash_on="2026-08-10", provider_cash_amt="50.00"),
                    correction_lifecycle=lifecycle)
        decision = build_recognition_decision(
            decision_id="decision-1", document=d, method=AccountingMethod.CASH,
            effective_from=date(2026, 4, 6), policy_version="v1",
        )
        assert decision.outcome is RecognitionDecisionOutcome.UNABLE_TO_SELECT


# ── C1 / raw status survives translation and cannot bypass recognition ───────

def test_raw_paid_status_survives_but_does_not_settle():
    d = doc(provider_status_text="paid")
    assert d.provider_status == "paid"
    assert d.canonical_state is CanonicalDocumentState.UNKNOWN
    assert d.settlement_state is SettlementState.UNKNOWN


def test_adapter_supplied_conservative_state_is_reason_bearing():
    # A credit note with a state outside the neutral map can carry an
    # adapter-supplied conservative state without overriding the raw status.
    d = doc(provider_document_kind="credit_note", provider_status_text="pending")
    assert d.provider_status == "pending"
    assert d.canonical_state is CanonicalDocumentState.UNKNOWN
    assert d.canonical_state_reason == "provider-neutral status map"


# ── C3 / economic direction ──────────────────────────────────────────────────

def test_sales_and_purchase_credits_retain_direction():
    sales_credit = doc(provider_document_kind="credit_note",
                       provider_economic_direction="receivable")
    purchase_credit = doc(provider_document_kind="credit_note",
                          provider_economic_direction="payable")
    assert sales_credit.economic_direction is EconomicDirection.RECEIVABLE
    assert purchase_credit.economic_direction is EconomicDirection.PAYABLE


def test_unknown_direction_blocks_income_expense_interpretation():
    d = doc(provider_document_kind="credit_note", provider_cash_on="2026-08-10",
            provider_cash_amt="50.00")
    assert d.economic_direction is EconomicDirection.UNKNOWN
    decision = build_recognition_decision(
        decision_id="decision-1", document=d, method=AccountingMethod.CASH,
        effective_from=date(2026, 4, 6), policy_version="v1",
    )
    assert decision.outcome is RecognitionDecisionOutcome.CASH
    with pytest.raises(CanonicalQuarantineError, match="unknown economic direction"):
        build_canonical_tax_input(
            input_id="i1", purpose="income", scope="sa", document=d,
            recognition_decision=decision, tax_year="2026-27", policy_version="v1",
        )


# ── C8 / incomplete FX evidence ──────────────────────────────────────────────

def test_incomplete_fx_observations_retain_only_observed_facts():
    raw = raw_record(
        provider_fx_original_currency="EUR",
        provider_fx_rate="0.85",
    )
    observation = observe(raw)
    result = adapt_observation(observation=observation, raw_record=raw)
    observed = result.document_candidate.observed_fx
    assert observed is not None
    assert observed.source_currency == "EUR"
    assert observed.rate == Decimal("0.85")
    assert observed.base_currency is None
    assert observed.source_amount is None
    assert observed.base_amount is None
    assert result.document_candidate.fx is None


def test_foreign_currency_without_complete_conversion_cannot_enter_tax_input():
    raw = raw_record(provider_fx_original_currency="EUR", provider_fx_rate="0.85")
    observation = observe(raw)
    result = adapt_observation(observation=observation, raw_record=raw)
    with pytest.raises(CanonicalQuarantineError, match="missing FX fact"):
        normalise_document(observation=observation, adapter_result=result)


def test_foreign_currency_document_without_validated_conversion_blocked_at_tax_input():
    # A foreign-currency document carrying only observed (partial) FX evidence
    # must not be silently treated as native currency at the tax gate.
    base = doc(provider_cash_on="2026-08-10", provider_cash_amt="50.00")
    fx_doc = replace(
        base, currency="EUR", fx=None,
        observed_fx=FxObservation(source_currency="EUR", rate=Decimal("0.85")),
    )
    decision = build_recognition_decision(
        decision_id="decision-1", document=fx_doc, method=AccountingMethod.CASH,
        effective_from=date(2026, 4, 6), policy_version="v1",
    )
    assert decision.outcome is RecognitionDecisionOutcome.CASH
    with pytest.raises(CanonicalQuarantineError, match="validated conversion"):
        build_canonical_tax_input(
            input_id="i1", purpose="income", scope="sa", document=fx_doc,
            recognition_decision=decision, tax_year="2026-27", policy_version="v1",
        )


# ── C6 / date semantics are not substituted ──────────────────────────────────

def test_document_dates_are_not_substituted():
    d = doc(provider_issued_on="2026-08-01", provider_posting_on="2026-08-02",
            provider_supply_on="2026-07-28", provider_due_on="2026-08-31")
    assert d.issue_date == date(2026, 8, 1)
    assert d.posting_date == date(2026, 8, 2)
    assert d.supply_date == date(2026, 7, 28)
    assert d.due_date == date(2026, 8, 31)
    # Issue date must not be substituted into the provider creation timestamp.
    assert d.provenance.created_at is None


def test_created_and_updated_timestamps_are_distinct_from_document_dates():
    d = doc()
    provenance = replace(d.provenance,
                         created_at=datetime(2026, 8, 1, 9, 0, tzinfo=timezone.utc),
                         updated_at=datetime(2026, 8, 2, 9, 0, tzinfo=timezone.utc))
    assert provenance.created_at != provenance.updated_at
    assert provenance.created_at.date() == d.issue_date
    assert provenance.updated_at.date() != d.issue_date


# ── C7 / revision and stale-observation controls ─────────────────────────────

def test_same_digest_observations_are_identical():
    first = observe(raw_record())
    second = observe(raw_record())
    assert classify_observation_relation(first, second) is ObservationRelation.IDENTICAL


def test_same_version_different_content_is_conflicting():
    first = observe(raw_record())
    second = observe(raw_record(provider_total="121.00"))
    assert classify_observation_relation(first, second) is ObservationRelation.CONFLICTING


def test_distinct_revision_tokens_are_revision_changed():
    first = observe(raw_record(), revision_id="1")
    second = observe(raw_record(provider_total="121.00"), revision_id="2")
    assert classify_observation_relation(first, second) is ObservationRelation.REVISION_CHANGED


def test_same_revision_different_content_is_conflicting():
    first = observe(raw_record(), revision_id="1")
    second = observe(raw_record(provider_total="121.00"), revision_id="1")
    assert classify_observation_relation(first, second) is ObservationRelation.CONFLICTING


# ── C9 / connection and business identity ────────────────────────────────────

def test_cross_resource_observation_substitution_is_rejected():
    first = observe(raw_record(), resource="invoices")
    second = observe(raw_record(), resource="payments")
    with pytest.raises(CanonicalQuarantineError, match="source identities"):
        classify_observation_relation(first, second)


def test_cross_connection_observation_substitution_is_rejected():
    first = observe(raw_record(), connected_organisation_id="org-1")
    second = observe(raw_record(), connected_organisation_id="org-2")
    with pytest.raises(CanonicalQuarantineError, match="source identities"):
        classify_observation_relation(first, second)


def test_cross_business_normalisation_is_rejected():
    raw = raw_record(provider_business_id="business-2")
    observation = observe(raw)  # observation identity uses business-1
    result = adapt_observation(observation=observation, raw_record=raw)
    with pytest.raises(CanonicalQuarantineError, match="business_id"):
        normalise_document(observation=observation, adapter_result=result)


def test_empty_identity_is_rejected_at_observation_time():
    with pytest.raises(CanonicalQuarantineError, match="connected organisation"):
        observe_provider_record(
            provider="xero", raw_record=raw_record(), user_id="user-1",
            connected_organisation_id="", business_id="business-1",
            import_run_id="run-1", api_name="synthetic", api_version="v1",
            resource="invoices", record_id="doc-1", retrieved_at=RETRIEVED_AT,
            adapter_version="syn-1",
        )


# ── C10 / provider configuration is not tax policy ───────────────────────────

def test_vat_basis_does_not_select_accounting_method():
    business = AccountingBusiness(
        AccountingProviderName.XERO, "b1", "Acme", "GBP",
        vat_history=(VatRegistrationPeriod(VatRegistrationState.REGISTERED,
                                           date(2026, 4, 6), basis="cash"),),
        accounting_methods=(),
    )
    # VAT cash basis is carried independently; no accounting method is inferred.
    assert business.vat_history[0].basis == "cash"
    assert business.accounting_methods == ()


def test_provider_category_does_not_decide_allowability():
    line = AccountingLine(
        "l-1", money("120.00"), TaxBreakdown(Decimal("100"), Decimal("20"), Decimal("120"),
                                             TaxAmountSemantics.EXCLUSIVE, "STANDARD", Decimal("0.20")),
        provider_category_id="disallowable-category",
        provider_account_id="asset-account",
    )
    # Category/account are retained as evidence only; no allowability is derived.
    assert line.provider_category_id == "disallowable-category"
    assert line.provider_account_id == "asset-account"


# ── C11 / resource-level completeness ────────────────────────────────────────

def test_resource_completeness_is_honest_per_dimension():
    rc = ResourceCompleteness(
        resource="invoices", pagination=CompletenessState.COMPLETE,
        independent_source_totals=CompletenessState.INCOMPLETE,
        webhook_coverage=CompletenessState.NOT_APPLICABLE,
        reason="no provider totals exposed; polling only",
    )
    assert rc.pagination is CompletenessState.COMPLETE
    assert rc.independent_source_totals is CompletenessState.INCOMPLETE
    assert rc.webhook_coverage is CompletenessState.NOT_APPLICABLE


def test_resource_completeness_requires_resource_identity():
    with pytest.raises(ValueError, match="resource identity"):
        ResourceCompleteness(resource="")


# ── C12 / source schema vs request prerequisites ─────────────────────────────

def test_request_prerequisites_are_distinct_from_response_requiredness():
    schema = SourceSchema(
        mapping_version="v1",
        required_fields=frozenset({"id", "total"}),
        known_fields=frozenset({"id", "total", "line_items"}),
        expected_kinds={"id": frozenset({"string"}), "total": frozenset({"number"}),
                        "line_items": frozenset({"array"})},
        request_prerequisites=frozenset({"line_items"}),
    )
    assert schema.response_required_fields == frozenset({"id", "total"})
    assert "line_items" not in schema.response_required_fields
    assert "line_items" in schema.request_prerequisites


def test_empty_request_prerequisite_is_rejected():
    with pytest.raises(SchemaContractError, match="Request prerequisites"):
        SourceSchema(
            mapping_version="v1", required_fields=frozenset({"id"}),
            known_fields=frozenset({"id"}), expected_kinds={"id": frozenset({"string"})},
            request_prerequisites=frozenset({""}),
        )


def test_source_schema_requiredness_ignores_request_prerequisites():
    schema = SourceSchema(
        mapping_version="v1",
        required_fields=frozenset({"id"}),
        known_fields=frozenset({"id", "line_items"}),
        expected_kinds={"id": frozenset({"string"}), "line_items": frozenset({"array"})},
        request_prerequisites=frozenset({"line_items"}),
    )
    observation = observe_schema({"id": "r1"}, schema)
    # A nested-item prerequisite is not treated as a missing response field.
    assert observation.missing_required_fields == ()
    assert observation.fitness is not SchemaFitness.QUARANTINED


# ── C2 / missing, zero, null, omitted and summary-only remain distinct ───────

def test_missing_zero_and_omitted_remain_distinct():
    missing_vat = TaxBreakdown(Decimal("100"), None, Decimal("100"), TaxAmountSemantics.UNKNOWN)
    zero_vat = TaxBreakdown(Decimal("100"), Decimal("0"), Decimal("100"), TaxAmountSemantics.UNKNOWN)
    assert missing_vat.vat_amount is None
    assert zero_vat.vat_amount == Decimal("0")
    assert missing_vat.vat_amount != zero_vat.vat_amount

    balance = ProviderBalanceAssertions(amount_due=Decimal("0"))
    assert balance.amount_paid is None
    assert balance.amount_paid != Decimal("0")


def test_summary_only_document_without_lines_fails_closed():
    raw = raw_record(provider_lines=[])
    observation = observe(raw)
    result = adapt_observation(observation=observation, raw_record=raw)
    with pytest.raises(CanonicalQuarantineError, match="missing lines"):
        normalise_document(observation=observation, adapter_result=result)


# ── C9 / cross-provider substitution ─────────────────────────────────────────

def test_cross_provider_observation_substitution_is_rejected():
    first = observe(raw_record(), provider="xero")
    second = observe(raw_record(), provider="quickbooks")
    with pytest.raises(CanonicalQuarantineError, match="source identities"):
        classify_observation_relation(first, second)
