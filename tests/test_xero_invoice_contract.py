"""Synthetic, network-free Xero detailed-invoice boundary tests."""

from dataclasses import FrozenInstanceError
from datetime import date, datetime
from decimal import Decimal

import pytest

from reserved.providers.accounting.contracts import (
    AccountingProviderName, DocumentType, EconomicDirection, LineValueSemantics,
    TaxAmountSemantics,
)
from reserved.providers.accounting.xero_invoice_contract import (
    INVOICE_STATUSES, INVOICE_TYPES, LINE_AMOUNT_TYPES,
    XERO_API_NAME, XERO_API_VERSION, XERO_INVOICE_ADAPTER_VERSION,
    XERO_INVOICE_RESOURCE, map_detailed_invoice_response,
    parse_detailed_invoice_response,
)


RETRIEVED_AT = datetime(2026, 9, 1, 9, 30)


def line(**changes):
    value = {
        "LineItemID": "line-1",
        "Description": "Synthetic reviewed work",
        "Quantity": Decimal("2"),
        "UnitAmount": Decimal("50.0000"),
        "AccountCode": "200",
        "TaxType": "OUTPUT",
        "TaxAmount": Decimal("20.00"),
        "LineAmount": Decimal("100.00"),
        "Tracking": [],
    }
    value.update(changes)
    return value


def invoice(**changes):
    value = {
        "InvoiceID": "invoice-1",
        "InvoiceNumber": "INV-001",
        "Type": "ACCREC",
        "Contact": {"ContactID": "contact-1", "Name": "Synthetic Contact"},
        "Date": "2026-08-31",
        "DueDate": "2026-09-30",
        "Status": "AUTHORISED",
        "LineAmountTypes": "Exclusive",
        "LineItems": [line()],
        "SubTotal": Decimal("100.00"),
        "TotalTax": Decimal("20.00"),
        "Total": Decimal("120.00"),
        "CurrencyCode": "GBP",
    }
    value.update(changes)
    return value


def response(*records):
    return {"Invoices": list(records)}


def mapped(raw=None, **identity):
    values = {
        "user_id": "user-1", "connected_organisation_id": "connection-1",
        "tenant_id": "tenant-1", "import_run_id": "run-1",
        "retrieved_at": RETRIEVED_AT,
    }
    values.update(identity)
    return map_detailed_invoice_response(response(raw or invoice()), **values)


def test_reviewed_constants_are_exact_and_network_surface_is_absent():
    assert INVOICE_TYPES == {"ACCREC", "ACCPAY"}
    assert INVOICE_STATUSES == {"DRAFT", "SUBMITTED", "DELETED", "AUTHORISED", "PAID", "VOIDED"}
    assert LINE_AMOUNT_TYPES == {"Exclusive", "Inclusive", "NoTax"}
    assert XERO_API_NAME == "Xero Accounting API"
    assert XERO_API_VERSION == "2.0"
    assert XERO_INVOICE_RESOURCE == "Invoices"
    assert XERO_INVOICE_ADAPTER_VERSION == "xero-xs2-v1"


def test_positive_sales_invoice_maps_to_neutral_observation_and_candidate():
    result = mapped()
    candidate = result.adapter_result.document_candidate
    assert result.invoice.issue_date == date(2026, 8, 31)
    assert candidate.document_type is DocumentType.INVOICE
    assert candidate.economic_direction is EconomicDirection.RECEIVABLE
    assert candidate.gross_amount == Decimal("120.00")
    assert candidate.net_amount == Decimal("100.00")
    assert candidate.vat_amount == Decimal("20.00")
    assert candidate.cash_candidate is None
    assert candidate.accrual_candidate is None
    assert candidate.provider_balance is None
    assert result.observation.provenance.identity.provider is AccountingProviderName.XERO
    assert result.observation.provenance.identity.connected_organisation_id == "connection-1"
    assert result.observation.provenance.identity.business_id == "tenant-1"
    assert result.observation.provenance.record_id == "invoice-1"
    assert result.adapter_result.observation_id == result.observation.observation_id


def test_purchase_bill_is_distinct_and_payable():
    candidate = mapped(invoice(Type="ACCPAY")).adapter_result.document_candidate
    assert candidate.document_type is DocumentType.BILL
    assert candidate.economic_direction is EconomicDirection.PAYABLE


@pytest.mark.parametrize("field,bad", [
    ("Type", "CREDIT"), ("Status", "SETTLED"), ("LineAmountTypes", "Gross"),
])
def test_unknown_closed_values_fail_without_echo(field, bad):
    with pytest.raises(ValueError) as caught:
        mapped(invoice(**{field: bad}))
    assert bad not in str(caught.value)


@pytest.mark.parametrize("payload", [
    {}, {"Invoices": []}, {"Invoices": [invoice(), invoice(InvoiceID="invoice-2")]},
    {"Invoices": [invoice()], "extra": True},
])
def test_collection_and_ambiguous_envelopes_are_rejected(payload):
    with pytest.raises(ValueError):
        parse_detailed_invoice_response(payload)


def test_summary_only_or_collection_summary_cannot_masquerade_as_detail():
    summary = invoice()
    del summary["LineItems"]
    with pytest.raises(ValueError, match="LineItems"):
        parse_detailed_invoice_response(response(summary))
    with pytest.raises(ValueError, match="non-empty LineItems"):
        parse_detailed_invoice_response(response(invoice(LineItems=[])))


@pytest.mark.parametrize("missing", [
    "InvoiceID", "Type", "Contact", "Date", "Status", "LineAmountTypes",
    "LineItems", "SubTotal", "TotalTax", "Total", "CurrencyCode",
])
def test_missing_and_null_required_invoice_facts_fail_closed(missing):
    raw = invoice()
    del raw[missing]
    with pytest.raises(ValueError):
        mapped(raw)
    raw = invoice(**{missing: None})
    with pytest.raises(ValueError):
        mapped(raw)


def test_optional_due_date_missing_null_and_value_remain_distinct():
    missing = invoice()
    del missing["DueDate"]
    parsed_missing = parse_detailed_invoice_response(response(missing))
    parsed_null = parse_detailed_invoice_response(response(invoice(DueDate=None)))
    parsed_value = parse_detailed_invoice_response(response(invoice()))
    assert parsed_missing.due_date is None and "DueDate" in parsed_missing.absent_fields
    assert parsed_null.due_date is None and "DueDate" in parsed_null.null_fields
    assert parsed_value.due_date == date(2026, 9, 30)


def test_optional_tracking_missing_null_and_empty_are_immutable_and_distinct():
    missing_line = line()
    del missing_line["Tracking"]
    missing = parse_detailed_invoice_response(response(invoice(LineItems=[missing_line]))).line_items[0]
    null = parse_detailed_invoice_response(response(invoice(LineItems=[line(Tracking=None)]))).line_items[0]
    empty = parse_detailed_invoice_response(response(invoice(LineItems=[line(Tracking=[])]))).line_items[0]
    assert missing.tracking == null.tracking == empty.tracking == ()
    assert "Tracking" in missing.absent_fields
    assert "Tracking" in null.null_fields
    assert "Tracking" not in empty.absent_fields | empty.null_fields


def test_zero_is_preserved_and_not_treated_as_missing():
    raw = invoice(
        LineAmountTypes="NoTax", LineItems=[line(LineAmount=Decimal("0.00"), TaxAmount=Decimal("0.00"))],
        SubTotal=Decimal("0.00"), TotalTax=Decimal("0.00"), Total=Decimal("0.00"),
    )
    result = mapped(raw)
    assert result.invoice.total == Decimal("0.00")
    assert result.adapter_result.document_candidate.lines[0].money.original_amount == Decimal("0.00")
    assert result.adapter_result.document_candidate.lines[0].tax.semantics is TaxAmountSemantics.NOT_APPLICABLE


def test_inclusive_mapping_preserves_gross_and_tax_without_float_math():
    raw = invoice(
        LineAmountTypes="Inclusive", LineItems=[line(LineAmount=Decimal("120.00"))],
    )
    candidate = mapped(raw).adapter_result.document_candidate
    assert candidate.lines[0].money.original_amount == Decimal("120.00")
    assert candidate.lines[0].tax.net_amount == Decimal("100.00")
    assert candidate.lines[0].value_semantics is LineValueSemantics.INCLUSIVE


@pytest.mark.parametrize("field,value", [
    ("Total", 120.0), ("SubTotal", "100.00"), ("TotalTax", Decimal("NaN")),
    ("Total", Decimal("1000000000000000001")), ("Total", Decimal("120.001")),
])
def test_money_rejects_float_string_nonfinite_out_of_bounds_and_excess_precision(field, value):
    with pytest.raises(ValueError):
        mapped(invoice(**{field: value}))


@pytest.mark.parametrize("unit", [Decimal("1.00001"), 1.25, "1.2500"])
def test_unit_amount_enforces_exact_numeric_shape_and_four_places(unit):
    with pytest.raises(ValueError):
        mapped(invoice(LineItems=[line(UnitAmount=unit)]))


def test_negative_credit_like_amounts_are_preserved_not_relabelled():
    raw = invoice(
        LineItems=[line(LineAmount=Decimal("-100.00"), TaxAmount=Decimal("-20.00"))],
        SubTotal=Decimal("-100.00"), TotalTax=Decimal("-20.00"), Total=Decimal("-120.00"),
    )
    candidate = mapped(raw).adapter_result.document_candidate
    assert candidate.gross_amount == Decimal("-120.00")
    assert candidate.document_type is DocumentType.INVOICE


@pytest.mark.parametrize("change", [
    {"Total": Decimal("121.00")},
    {"SubTotal": Decimal("99.00")},
    {"LineItems": [line(TaxAmount=Decimal("19.00"))]},
    {"LineItems": [line(), line()]},
])
def test_totals_and_line_identity_must_reconcile_exactly(change):
    with pytest.raises(ValueError):
        mapped(invoice(**change))


def test_line_content_and_optional_unknowns_are_retained_without_semantics():
    parsed = parse_detailed_invoice_response(response(invoice(LineItems=[line(
        AccountID="account-id", Item={"ItemID": "item-id"}, FutureField="future",
        Description=None,
    )], FutureInvoiceField="future")))
    item = parsed.line_items[0]
    assert item.description is None and "Description" in item.null_fields
    assert "FutureField" in item.unknown_fields
    assert "FutureInvoiceField" in parsed.unknown_fields
    assert item.account_id == "account-id"
    assert item.item == (("ItemID", "item-id"),)


def test_documented_account_id_spelling_is_retained_and_ambiguity_rejected():
    parsed = parse_detailed_invoice_response(response(invoice(LineItems=[line(AccountId="account-id")])))
    assert parsed.line_items[0].account_id == "account-id"
    with pytest.raises(ValueError, match="ambiguous account identity"):
        parse_detailed_invoice_response(response(invoice(LineItems=[line(AccountID="one", AccountId="two")])))


@pytest.mark.parametrize("bad", ["", " ", "GBP\n", "x" * 513])
def test_hostile_identifiers_are_rejected_without_echo(bad):
    with pytest.raises(ValueError) as caught:
        mapped(invoice(InvoiceID=bad))
    if bad.strip():
        assert bad not in str(caught.value)


@pytest.mark.parametrize("bad", ["gbp", "GB", "GBPP", "12A", "£££"])
def test_currency_is_conservatively_bounded(bad):
    with pytest.raises(ValueError):
        mapped(invoice(CurrencyCode=bad))


@pytest.mark.parametrize("bad", ["31/08/2026", "2026-02-30", "2026-8-1"])
def test_dates_require_valid_iso_calendar_shape(bad):
    with pytest.raises(ValueError):
        mapped(invoice(Date=bad))


def test_source_digest_and_observation_identity_change_with_source_evidence():
    first = mapped().observation
    second = mapped(invoice(InvoiceNumber="INV-002")).observation
    assert first.provenance.source_record_digest != second.provenance.source_record_digest
    assert first.observation_id != second.observation_id


@pytest.mark.parametrize("left,right", [
    ("1.00", Decimal("1.00")),
    (1, Decimal("1")),
    (True, 1),
    (Decimal("1.0"), Decimal("1.00")),
])
def test_source_digest_is_type_and_decimal_representation_preserving(left, right):
    first = mapped(invoice(LineItems=[line(Item={"Value": left})])).observation
    second = mapped(invoice(LineItems=[line(Item={"Value": right})])).observation
    assert first.provenance.source_record_digest != second.provenance.source_record_digest
    assert first.observation_id != second.observation_id


def test_source_digest_is_canonical_across_mapping_insertion_order():
    first = mapped(invoice(LineItems=[line(Item={"A": 1, "B": Decimal("2.00")})])).observation
    second = mapped(invoice(LineItems=[line(Item={"B": Decimal("2.00"), "A": 1})])).observation
    assert first.provenance.source_record_digest == second.provenance.source_record_digest
    assert first.observation_id == second.observation_id


@pytest.mark.parametrize("location", ["invoice", "contact", "line"])
@pytest.mark.parametrize("hostile_kind", ["huge_integer", "oversized_string"])
def test_unknown_additive_source_values_are_bounded_without_runtime_escape(
    location, hostile_kind,
):
    hostile = 10 ** 5000 if hostile_kind == "huge_integer" else "x" * 4_097
    raw = invoice()
    if location == "invoice":
        raw["FutureField"] = hostile
    elif location == "contact":
        raw["Contact"] = dict(raw["Contact"], FutureField=hostile)
    else:
        raw["LineItems"] = [line(FutureField=hostile)]
    with pytest.raises(ValueError) as caught:
        mapped(raw)
    message = str(caught.value)
    assert "Xero invoice contract" in message
    assert "FutureField" not in message


def test_unknown_additive_source_container_is_bounded():
    raw = invoice(FutureField=[None] * 10_001)
    with pytest.raises(ValueError, match="oversized container"):
        mapped(raw)


def test_valid_multibyte_description_respects_character_contract():
    description = "🙂" * 2_000
    result = mapped(invoice(LineItems=[line(Description=description)]))
    assert result.invoice.line_items[0].description == description


@pytest.mark.parametrize("location", ["value", "key"])
def test_invalid_unicode_fails_as_controlled_non_echoing_contract_error(location):
    surrogate = chr(0xD800)
    raw = invoice()
    if location == "value":
        raw["FutureField"] = surrogate
    else:
        raw[surrogate] = None
    with pytest.raises(ValueError) as caught:
        mapped(raw)
    message = str(caught.value)
    assert "Xero invoice contract" in message
    assert "invalid Unicode" in message


@pytest.mark.parametrize("payload_factory", [
    lambda key: {"Invoices": [invoice()], key: None},
    lambda key: {"Invoices": [dict(invoice(), **{}) | {key: None}]},
    lambda key: response(invoice(Contact={"ContactID": "contact-1", key: None})),
    lambda key: response(invoice(LineItems=[line() | {key: None}])),
    lambda key: response(invoice(LineItems=[line(Item={key: None})])),
    lambda key: response(invoice(LineItems=[line(Tracking=[{key: None}])])),
])
def test_all_mapping_boundaries_reject_non_string_keys_without_echo(payload_factory):
    hostile_key = 8675309
    with pytest.raises(ValueError) as caught:
        parse_detailed_invoice_response(payload_factory(hostile_key))
    assert str(hostile_key) not in str(caught.value)


def test_opaque_evidence_rejects_excessive_depth_without_recursion_escape():
    nested = None
    for _ in range(18):
        nested = [nested]
    with pytest.raises(ValueError, match="bounded opaque depth"):
        mapped(invoice(LineItems=[line(Item={"Nested": nested})]))


@pytest.mark.parametrize("opaque", [
    {str(index): None for index in range(1_001)},
    {"Text": "x" * 4_097},
    {"Value": Decimal("NaN")},
    {"Value": Decimal("Infinity")},
    {"Value": Decimal("1000000000000000001")},
])
def test_opaque_evidence_rejects_width_strings_and_invalid_decimals_without_echo(opaque):
    with pytest.raises(ValueError) as caught:
        mapped(invoice(LineItems=[line(Item=opaque)]))
    assert "Infinity" not in str(caught.value)
    assert "1000000000000000001" not in str(caught.value)


def test_raw_status_is_only_an_assertion_not_settlement_or_tax_decision():
    result = mapped(invoice(Status="PAID"))
    candidate = result.adapter_result.document_candidate
    assert candidate.provider_status == "PAID"
    assert candidate.canonical_state is None
    assert candidate.cash_candidate is None
    assert not hasattr(result.adapter_result, "recognition_decision")
    assert "xero_status=PAID" in result.adapter_result.provider_assertions


def test_records_are_immutable_and_do_not_retain_raw_payload():
    result = mapped()
    assert not hasattr(result.invoice, "raw_payload")
    with pytest.raises(FrozenInstanceError):
        result.invoice.status = "DRAFT"


@pytest.mark.parametrize("field", [
    "user_id", "connected_organisation_id", "tenant_id", "import_run_id",
])
def test_provenance_identity_is_required(field):
    with pytest.raises(ValueError):
        mapped(**{field: ""})


def test_error_messages_do_not_echo_hostile_or_secret_like_values():
    secret = "secret-token-material"
    with pytest.raises(ValueError) as caught:
        mapped(invoice(Status=secret))
    assert secret not in str(caught.value)
