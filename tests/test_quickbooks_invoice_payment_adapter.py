"""Adversarial tests for the deliberately narrow QuickBooks Q-S5A adapter."""

from copy import deepcopy
from datetime import datetime, timezone, tzinfo
from decimal import Decimal
import builtins
import socket

import pytest

from reserved.providers.accounting.contracts import (
    AccountingDocument, CanonicalDocumentState, EvidenceState,
    LineValueSemantics, SettlementState, TaxAmountSemantics,
)
from reserved.providers.accounting.normalisation import derive_settlement_state
from reserved.providers.accounting.quickbooks_invoice_payment_adapter import (
    InvoiceAdapterResult, QuickBooksAdapterError, adapt_invoice, adapt_payment,
)
from reserved.providers.accounting.quickbooks_oauth_contract import RealmBinding
from reserved.providers.accounting.quickbooks_observation_contract import (
    FrozenEvidence, FrozenEvidenceSequence, QuickBooksObservationError,
    observe_invoice, observe_payment,
)


NOW = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
BINDING = RealmBinding("user-1", "realm-1", "opaque-reference-1")


def invoice_raw():
    return {
        "Id": "invoice-1", "SyncToken": "7",
        "CustomerRef": {"value": "customer-1"},
        "TxnDate": "2026-08-10", "DueDate": "2026-09-10",
        "CurrencyRef": {"value": "GBP"},
        "GlobalTaxCalculation": "TaxExcluded",
        "Line": [
            {"Id": "line-1", "DetailType": "SalesItemLineDetail",
             "Amount": Decimal("100.00"),
             "SalesItemLineDetail": {
                 "ItemRef": {"value": "item-1"},
                 "TaxCodeRef": {"value": "TAX"},
             }},
            {"Id": "subtotal-1", "DetailType": "SubTotalLineDetail",
             "Amount": Decimal("100.00"), "SubTotalLineDetail": {}},
        ],
        "TxnTaxDetail": {
            "TotalTax": Decimal("20.00"),
            "TaxLine": [{
                "Amount": Decimal("20.00"), "DetailType": "TaxLineDetail",
                "TaxLineDetail": {
                    "TaxRateRef": {"value": "rate-20"},
                    "PercentBased": True, "TaxPercent": Decimal("20"),
                    "NetAmountTaxable": Decimal("100.00"),
                },
            }],
        },
        "TotalAmt": Decimal("120.00"), "Balance": Decimal("120.00"),
        "EmailStatus": "EmailSent",
    }


def multiline_invoice_raw():
    raw = invoice_raw()
    raw["Line"] = [
        {"Id": "line-1", "DetailType": "SalesItemLineDetail",
         "Amount": Decimal("40.00"), "SalesItemLineDetail": {
             "ItemRef": {"value": "item-1"}, "TaxCodeRef": {"value": "TAX"},
         }},
        {"Id": "line-2", "DetailType": "SalesItemLineDetail",
         "Amount": Decimal("60.00"), "SalesItemLineDetail": {
             "ItemRef": {"value": "item-2"}, "TaxCodeRef": {"value": "TAX"},
         }},
        {"Id": "subtotal-1", "DetailType": "SubTotalLineDetail",
         "Amount": Decimal("100.00"), "SubTotalLineDetail": {}},
    ]
    return raw


def payment_raw():
    return {
        "Id": "payment-1", "SyncToken": "2",
        "CustomerRef": {"value": "customer-1"},
        "TxnDate": "2026-08-15", "CurrencyRef": {"value": "GBP"},
        "TotalAmt": Decimal("80.00"), "UnappliedAmt": Decimal("30.00"),
        "Line": [{"Amount": Decimal("50.00"), "LinkedTxn": [
            {"TxnId": "invoice-1", "TxnType": "Invoice"}
        ]}],
    }


def observe_i(raw=None, *, binding=BINDING):
    return observe_invoice(
        invoice_raw() if raw is None else raw, binding=binding,
        user_id=binding.user_id, realm_id=binding.realm_id,
        credential_reference=binding.credential_reference, retrieved_at=NOW,
    )


def observe_p(raw=None, *, binding=BINDING):
    return observe_payment(
        payment_raw() if raw is None else raw, binding=binding,
        user_id=binding.user_id, realm_id=binding.realm_id,
        credential_reference=binding.credential_reference, retrieved_at=NOW,
    )


def mapped_invoice(raw=None, **kwargs):
    return adapt_invoice(
        observe_i(raw), binding=BINDING, import_run_id="run-1", **kwargs)


def test_exact_invoice_maps_to_canonical_v3_without_subtotal_double_counting():
    result = mapped_invoice()
    document = result.document
    assert isinstance(document, AccountingDocument)
    assert document.document_id == "invoice-1"
    assert document.business_id == "realm-1"
    assert document.connected_organisation_id == "opaque-reference-1"
    assert document.issue_date.isoformat() == "2026-08-10"
    assert document.due_date.isoformat() == "2026-09-10"
    assert document.currency == "GBP"
    assert (document.net_amount, document.vat_amount, document.gross_amount) == (
        Decimal("100.00"), Decimal("20.00"), Decimal("120.00"))
    assert len(document.lines) == 1
    line = document.lines[0]
    assert line.line_id == "line-1"
    assert line.money.original_amount == Decimal("120.00")
    assert line.tax.semantics is TaxAmountSemantics.EXCLUSIVE
    assert line.value_semantics is LineValueSemantics.EXCLUSIVE
    assert (line.tax.vat_code, line.provider_category_id, line.tax.vat_rate) == (
        "TAX", None, Decimal("0.20"))
    assert "rate-20" not in repr(line)
    assert document.provider_status == "EmailSent"
    assert document.canonical_state is CanonicalDocumentState.UNKNOWN
    assert document.provenance.revision_id == "7"
    assert document.provenance.source_record_digest == result.observation.provenance.source_record_digest


def test_bounded_same_code_multiline_invoice_maps_each_exact_tax_exclusive_line():
    result = mapped_invoice(multiline_invoice_raw())
    document = result.document
    assert (document.net_amount, document.vat_amount, document.gross_amount) == (
        Decimal("100.00"), Decimal("20.00"), Decimal("120.00"))
    assert [(line.line_id, line.tax.net_amount, line.tax.vat_amount,
             line.money.original_amount, line.tax.vat_code, line.tax.vat_rate)
            for line in document.lines] == [
        ("line-1", Decimal("40.00"), Decimal("8.00"), Decimal("48.00"),
         "TAX", Decimal("0.20")),
        ("line-2", Decimal("60.00"), Decimal("12.00"), Decimal("72.00"),
         "TAX", Decimal("0.20")),
    ]
    assert document.canonical_state is CanonicalDocumentState.UNKNOWN


@pytest.mark.parametrize("mutation", [
    lambda raw: raw["Line"][1]["SalesItemLineDetail"]["TaxCodeRef"].__setitem__("value", "OTHER"),
    lambda raw: raw["TxnTaxDetail"]["TaxLine"][0]["TaxLineDetail"].pop("TaxPercent"),
    lambda raw: raw["Line"][1].__setitem__("Id", "line-1"),
    lambda raw: raw["Line"].insert(2, {"Id": "line-3", "DetailType": "SalesItemLineDetail",
                                         "Amount": Decimal("1.00"), "SalesItemLineDetail": {
                                             "ItemRef": {"value": "item-3"},
                                             "TaxCodeRef": {"value": "TAX"}}}),
    lambda raw: raw["Line"].__setitem__(1, {"Id": "subtotal-middle",
                                               "DetailType": "SubTotalLineDetail",
                                               "Amount": Decimal("40.00"),
                                               "SubTotalLineDetail": {}}),
    lambda raw: raw["Line"][-1].__setitem__("Amount", Decimal("99.99")),
])
def test_multiline_mixed_ambiguous_or_out_of_bound_shapes_fail_closed(mutation):
    raw = multiline_invoice_raw(); mutation(raw)
    with pytest.raises(QuickBooksAdapterError):
        mapped_invoice(raw)


def test_payment_maps_once_preserves_unapplied_and_uses_allocation_settlement():
    invoice = mapped_invoice()
    result = adapt_payment(
        observe_p(), invoice=invoice, binding=BINDING, import_run_id="run-1")
    assert result.payment.money.original_amount == Decimal("80.00")
    assert result.payment.unapplied_amount == Decimal("30.00")
    assert result.payment.occurred_on.isoformat() == "2026-08-15"
    assert result.allocation.amount == Decimal("50.00")
    assert result.allocation.document_id == invoice.document.document_id
    assert derive_settlement_state(
        invoice.document, (result.allocation,),
        {result.payment.payment_id: result.payment},
    ) is SettlementState.PART_PAID


def test_invoice_balance_never_determines_settlement():
    raw = invoice_raw(); raw["Balance"] = Decimal("0.00")
    result = mapped_invoice(raw)
    assert result.document.provider_balance.balance == Decimal("0.00")
    assert result.document.settlement_state is SettlementState.UNKNOWN
    assert derive_settlement_state(result.document, ()) is SettlementState.UNPAID


@pytest.mark.parametrize("tax_mode", ["TaxInclusive", "NotApplicable"])
def test_nonexclusive_tax_modes_fail_closed(tax_mode):
    raw = invoice_raw(); raw["GlobalTaxCalculation"] = tax_mode
    with pytest.raises(QuickBooksAdapterError, match="TaxExcluded"):
        mapped_invoice(raw)


@pytest.mark.parametrize("currency", ["", "ZZZ", "unknown"])
def test_blank_or_unknown_invoice_currency_fails_closed(currency):
    raw = invoice_raw(); raw["CurrencyRef"]["value"] = currency
    with pytest.raises((QuickBooksAdapterError, QuickBooksObservationError)):
        mapped_invoice(raw)


@pytest.mark.parametrize("path", ["CurrencyRef", "TxnDate", "TotalAmt", "TxnTaxDetail"])
@pytest.mark.parametrize("replacement", ["missing", None])
def test_missing_or_null_invoice_essentials_fail(path, replacement):
    raw = invoice_raw()
    if replacement == "missing": raw.pop(path)
    else: raw[path] = None
    with pytest.raises((QuickBooksAdapterError, QuickBooksObservationError)):
        mapped_invoice(raw)


@pytest.mark.parametrize("lines", [
    [],
    [{"Id": "d", "DetailType": "DiscountLineDetail", "Amount": Decimal("1.00"),
      "DiscountLineDetail": {}}],
])
def test_zero_economic_or_discount_only_lines_fail(lines):
    raw = invoice_raw(); raw["Line"] = lines
    with pytest.raises((QuickBooksAdapterError, QuickBooksObservationError)):
        mapped_invoice(raw)


@pytest.mark.parametrize("detail", ["DiscountLineDetail"])
def test_second_nonterminal_or_extra_economic_roles_fail(detail):
    raw = invoice_raw()
    raw["Line"][1] = {"Id": "extra", "DetailType": detail,
                       "Amount": Decimal("100.00"), detail: {}}
    with pytest.raises(QuickBooksAdapterError): mapped_invoice(raw)


@pytest.mark.parametrize("detail", ["GroupLineDetail", "DescriptionOnlyLineDetail",
                                     "ShippingLineDetail"])
def test_unobserved_group_description_shipping_roles_fail_at_qs4(detail):
    raw = invoice_raw(); raw["Line"][0]["DetailType"] = detail
    raw["Line"][0][detail] = raw["Line"][0].pop("SalesItemLineDetail")
    with pytest.raises(QuickBooksObservationError): observe_i(raw)


@pytest.mark.parametrize("mutation", [
    lambda r: r["Line"][1].__setitem__("Amount", Decimal("99.99")),
    lambda r: r["TxnTaxDetail"].__setitem__("TaxLine", []),
    lambda r: r["TxnTaxDetail"]["TaxLine"].append(deepcopy(r["TxnTaxDetail"]["TaxLine"][0])),
    lambda r: r["TxnTaxDetail"]["TaxLine"][0].__setitem__("Amount", Decimal("19.99")),
    lambda r: r["TxnTaxDetail"]["TaxLine"][0]["TaxLineDetail"].__setitem__("NetAmountTaxable", Decimal("99.00")),
    lambda r: r["TxnTaxDetail"]["TaxLine"][0]["TaxLineDetail"].__setitem__("PercentBased", False),
    lambda r: r.__setitem__("TotalAmt", Decimal("119.99")),
])
def test_invoice_reconciliation_and_tax_shape_mismatches_fail(mutation):
    raw = invoice_raw(); mutation(raw)
    with pytest.raises(QuickBooksAdapterError): mapped_invoice(raw)


@pytest.mark.parametrize("field_path,bad", [
    (("Line", 0, "Amount"), Decimal("-1.00")),
    (("Line", 0, "Amount"), Decimal("NaN")),
    (("Line", 0, "Amount"), True),
    (("Line", 0, "Amount"), 100.0),
    (("Line", 0, "Amount"), Decimal("100.001")),
    (("TxnTaxDetail", "TotalTax"), Decimal("20.001")),
])
def test_bad_money_fails_in_observer_or_adapter(field_path, bad):
    raw = invoice_raw(); target = raw
    for key in field_path[:-1]: target = target[key]
    target[field_path[-1]] = bad
    with pytest.raises((QuickBooksAdapterError, QuickBooksObservationError)):
        mapped_invoice(raw)


@pytest.mark.parametrize("path", [
    ("Line", 0, "Id"), ("Line", 0, "SalesItemLineDetail", "TaxCodeRef", "value"),
    ("TxnTaxDetail", "TaxLine", 0, "TaxLineDetail", "TaxRateRef", "value"),
    ("CustomerRef", "value"),
])
@pytest.mark.parametrize("bad", ["", " duplicate space ", "bad:delimiter"])
def test_missing_or_hostile_invoice_identifiers_fail(path, bad):
    raw = invoice_raw(); target = raw
    for key in path[:-1]: target = target[key]
    target[path[-1]] = bad
    with pytest.raises((QuickBooksAdapterError, QuickBooksObservationError)):
        mapped_invoice(raw)


@pytest.mark.parametrize("path", ["TxnDate", "CurrencyRef"])
def test_missing_payment_date_or_currency_fails_closed(path):
    raw = payment_raw(); raw.pop(path)
    with pytest.raises(QuickBooksAdapterError):
        adapt_payment(observe_p(raw), invoice=mapped_invoice(), binding=BINDING,
                      import_run_id="run-1")


@pytest.mark.parametrize("mutation", [
    lambda r: r.__setitem__("Line", []),
    lambda r: r["Line"].append(deepcopy(r["Line"][0])),
    lambda r: r["Line"][0]["LinkedTxn"].append({"TxnId": "invoice-1", "TxnType": "Invoice"}),
    lambda r: r["Line"][0]["LinkedTxn"][0].__setitem__("TxnType", "CreditMemo"),
    lambda r: r["Line"][0]["LinkedTxn"][0].__setitem__("TxnId", "unknown-invoice"),
    lambda r: r["Line"][0].__setitem__("Amount", Decimal("49.99")),
])
def test_payment_line_link_identity_and_arithmetic_fail_closed(mutation):
    raw = payment_raw(); mutation(raw)
    with pytest.raises(QuickBooksAdapterError):
        adapt_payment(observe_p(raw), invoice=mapped_invoice(), binding=BINDING,
                      import_run_id="run-1")


def test_payment_currency_customer_realm_and_connected_org_mismatches_fail():
    invoice = mapped_invoice()
    variants = []
    raw = payment_raw(); raw["CurrencyRef"]["value"] = "USD"; variants.append(observe_p(raw))
    raw = payment_raw(); raw["CustomerRef"]["value"] = "customer-2"; variants.append(observe_p(raw))
    for binding in (
        RealmBinding("user-1", "realm-2", "opaque-reference-1"),
        RealmBinding("user-1", "realm-1", "opaque-reference-2"),
    ):
        variants.append(observe_p(binding=binding))
    for observed in variants:
        with pytest.raises(QuickBooksAdapterError):
            adapt_payment(observed, invoice=invoice, binding=BINDING,
                          import_run_id="run-1")


@pytest.mark.parametrize("field,bad", [
    ("TotalAmt", Decimal("NaN")), ("UnappliedAmt", Decimal("-1")),
    ("TotalAmt", True), ("TotalAmt", 80.0), ("TotalAmt", Decimal("80.001")),
])
def test_payment_bad_money_fails(field, bad):
    raw = payment_raw(); raw[field] = bad
    with pytest.raises((QuickBooksAdapterError, QuickBooksObservationError)):
        adapt_payment(observe_p(raw), invoice=mapped_invoice(), binding=BINDING,
                      import_run_id="run-1")


@pytest.mark.parametrize("state", [EvidenceState.CONFLICTING, EvidenceState.EXCLUDED])
def test_conflicting_or_excluded_source_evidence_fails(state):
    with pytest.raises(QuickBooksAdapterError):
        mapped_invoice(evidence_state=state)


def test_hand_built_lookalikes_and_provenance_mutation_fail():
    with pytest.raises(QuickBooksAdapterError, match="exact Q-S4"):
        adapt_invoice(object(), binding=BINDING, import_run_id="run-1")
    observed = observe_i()
    object.__setattr__(observed, "source_digest", "0" * 64)
    with pytest.raises(QuickBooksAdapterError, match="digest"):
        adapt_invoice(observed, binding=BINDING, import_run_id="run-1")


@pytest.mark.parametrize("field,value", [
    ("retrieved_at", NOW.replace(hour=11)),
    ("observation_attestation", "0" * 64),
])
def test_retrieval_or_attestation_mutation_fails_closed(field, value):
    observed = observe_i()
    object.__setattr__(observed, field, value)
    with pytest.raises(QuickBooksAdapterError) as caught:
        adapt_invoice(observed, binding=BINDING, import_run_id="run-1")
    assert "customer-1" not in str(caught.value)


class HostileEvidence(dict):
    def __iter__(self):
        raise RuntimeError("private-evidence-text")

    def __eq__(self, other):
        raise RuntimeError("private-evidence-text")


class HostileEquality:
    def __init__(self):
        self.invoked = False

    def __eq__(self, other):
        self.invoked = True
        raise RuntimeError("private-equality-text")


@pytest.mark.parametrize("factory,field", [
    (observe_i, "customer_reference_value"),
    (observe_p, "customer_reference_value"),
    (observe_p, "total_amount"),
])
def test_hostile_observation_equality_leaf_is_rejected_without_invocation(
        factory, field):
    observed = factory()
    hostile = HostileEquality()
    object.__setattr__(observed, field, hostile)
    with pytest.raises(QuickBooksAdapterError) as caught:
        if factory is observe_i:
            adapt_invoice(observed, binding=BINDING, import_run_id="run-1")
        else:
            adapt_payment(observed, invoice=mapped_invoice(), binding=BINDING,
                          import_run_id="run-1")
    assert hostile.invoked is False
    assert str(caught.value) == (
        "QuickBooks Q-S5A adapter: retained source evidence validation failed")
    assert "private-equality-text" not in str(caught.value)


@pytest.mark.parametrize("path", ["transformation", "document_id", "vat_code"])
def test_hostile_linked_result_leaf_is_rejected_without_invocation(path):
    invoice = mapped_invoice()
    hostile = HostileEquality()
    if path == "transformation":
        object.__setattr__(invoice.semantic_result, path, hostile)
    elif path == "document_id":
        object.__setattr__(invoice.document, path, hostile)
    else:
        object.__setattr__(invoice.document.lines[0].tax, path, hostile)
    with pytest.raises(QuickBooksAdapterError) as caught:
        adapt_payment(observe_p(), invoice=invoice, binding=BINDING,
                      import_run_id="run-1")
    assert hostile.invoked is False
    assert str(caught.value) == (
        "QuickBooks Q-S5A adapter: linked invoice result integrity check failed")
    assert "private-equality-text" not in str(caught.value)


def test_plain_and_hostile_source_container_substitution_is_non_echoing():
    for replacement in (dict(invoice_raw()), HostileEvidence(invoice_raw()),
                        list(invoice_raw())):
        observed = observe_i()
        object.__setattr__(observed, "source_evidence", replacement)
        with pytest.raises(QuickBooksAdapterError) as caught:
            adapt_invoice(observed, binding=BINDING, import_run_id="run-1")
        assert "private-evidence-text" not in str(caught.value)


def test_hostile_nested_container_is_rejected_without_traversal_or_echo():
    observed = observe_i()
    hostile = HostileEvidence({"value": "private-evidence-text"})
    root = FrozenEvidence({"Id": "invoice-1", "nested": hostile})
    object.__setattr__(observed, "source_evidence", root)
    with pytest.raises(QuickBooksAdapterError) as caught:
        adapt_invoice(observed, binding=BINDING, import_run_id="run-1")
    assert "private-evidence-text" not in str(caught.value)


def _assert_constant_evidence_rejection(root):
    observed = observe_i()
    object.__setattr__(observed, "source_evidence", root)
    with pytest.raises(QuickBooksAdapterError) as caught:
        adapt_invoice(observed, binding=BINDING, import_run_id="run-1")
    assert str(caught.value) == (
        "QuickBooks Q-S5A adapter: retained source evidence validation failed")


@pytest.mark.parametrize("container", [FrozenEvidence, FrozenEvidenceSequence])
def test_1200_level_exact_frozen_graph_is_bounded_without_recursion(container):
    nested = "leaf"
    for _ in range(1_200):
        nested = container({"next": nested} if container is FrozenEvidence
                           else [nested])
    _assert_constant_evidence_rejection(FrozenEvidence({"Id": nested}))


def test_overwide_exact_frozen_graph_hits_complete_node_ceiling():
    branches = [FrozenEvidenceSequence(list(range(25))) for _ in range(2_000)]
    _assert_constant_evidence_rejection(
        FrozenEvidence({"Id": "invoice-1", "wide":
                        FrozenEvidenceSequence(branches)}))


def test_forged_exact_frozen_cycle_and_alias_fail_closed():
    cyclic = FrozenEvidenceSequence([])
    object.__setattr__(cyclic, "_FrozenEvidenceSequence__values", (cyclic,))
    child = FrozenEvidence({"safe": "value"})
    for nested in (cyclic, FrozenEvidenceSequence([child, child])):
        _assert_constant_evidence_rejection(
            FrozenEvidence({"Id": "invoice-1", "nested": nested}))


def test_forged_exact_frozen_mapping_storage_does_not_invoke_protocols():
    forged = FrozenEvidence({})
    object.__setattr__(forged, "_FrozenEvidence__values",
                       HostileEvidence({"private": "value"}))
    _assert_constant_evidence_rejection(forged)


class HostileTimezone(tzinfo):
    def __init__(self):
        self.calls = {name: 0 for name in (
            "utcoffset", "dst", "tzname", "fromutc", "eq", "repr", "format")}

    def _called(self, name):
        self.calls[name] += 1
        raise RuntimeError("private-timezone-text")

    def utcoffset(self, value): return self._called("utcoffset")
    def dst(self, value): return self._called("dst")
    def tzname(self, value): return self._called("tzname")
    def fromutc(self, value): return self._called("fromutc")
    def __eq__(self, other): return self._called("eq")
    def __repr__(self): return self._called("repr")
    def __format__(self, spec): return self._called("format")


def test_forged_exact_datetime_hostile_timezone_is_rejected_without_hooks():
    observed = observe_i()
    hostile = HostileTimezone()
    object.__setattr__(observed, "retrieved_at",
                       datetime(2026, 9, 1, 10, 0, tzinfo=hostile))
    with pytest.raises(QuickBooksAdapterError) as caught:
        adapt_invoice(observed, binding=BINDING, import_run_id="run-1")
    assert all(count == 0 for count in hostile.calls.values())
    assert str(caught.value) == (
        "QuickBooks Q-S5A adapter: retained source evidence validation failed")


@pytest.mark.parametrize("path", ["observation", "document"])
def test_linked_provenance_datetime_hostile_timezone_is_rejected_without_hooks(path):
    invoice = mapped_invoice()
    hostile = HostileTimezone()
    provenance = (invoice.observation.provenance if path == "observation"
                  else invoice.document.provenance)
    object.__setattr__(provenance, "retrieved_at",
                       datetime(2026, 9, 1, 10, 0, tzinfo=hostile))
    with pytest.raises(QuickBooksAdapterError) as caught:
        adapt_payment(observe_p(), invoice=invoice, binding=BINDING,
                      import_run_id="run-1")
    assert all(count == 0 for count in hostile.calls.values())
    assert str(caught.value) == (
        "QuickBooks Q-S5A adapter: linked invoice result integrity check failed")
    assert "private-timezone-text" not in str(caught.value)


@pytest.mark.parametrize("field", [
    "user_id", "realm_id", "credential_reference",
])
def test_forged_realm_binding_hostile_field_is_rejected_without_equality(field):
    binding = RealmBinding("user-1", "realm-1", "opaque-reference-1")
    hostile = HostileEquality()
    object.__setattr__(binding, field, hostile)
    with pytest.raises(QuickBooksAdapterError) as caught:
        adapt_payment(observe_p(), invoice=mapped_invoice(), binding=binding,
                      import_run_id="run-1")
    assert hostile.invoked is False
    assert str(caught.value) == (
        "QuickBooks Q-S5A adapter: Q-S1 provenance binding validation failed")
    assert "private-equality-text" not in str(caught.value)


@pytest.mark.parametrize("field,value", [
    ("global_tax_calculation", "TaxInclusive"),
    ("transaction_date", None), ("due_date", None),
    ("customer_reference_value", "customer-2"),
    ("balance", Decimal("0.00")), ("total_amount", Decimal("999.00")),
])
def test_typed_invoice_mutation_fails_complete_qs4_replay(field, value):
    observed = observe_i()
    object.__setattr__(observed, field, value)
    with pytest.raises(QuickBooksAdapterError, match="replay"):
        adapt_invoice(observed, binding=BINDING, import_run_id="run-1")


@pytest.mark.parametrize("field,value", [
    ("amount", Decimal("99.00")),
    ("detail_type", "DiscountLineDetail"),
    ("present_fields", frozenset()),
    ("null_fields", frozenset({"Amount"})),
])
def test_typed_invoice_line_mutation_fails_complete_qs4_replay(field, value):
    observed = observe_i()
    object.__setattr__(observed.lines[0], field, value)
    with pytest.raises(QuickBooksAdapterError, match="replay"):
        adapt_invoice(observed, binding=BINDING, import_run_id="run-1")


@pytest.mark.parametrize("field,value", [
    ("transaction_date", None), ("customer_reference_value", "customer-2"),
    ("total_amount", Decimal("999.00")), ("unapplied_amount", Decimal("0.00")),
    ("lines", ()),
])
def test_typed_payment_mutation_fails_complete_qs4_replay(field, value):
    observed = observe_p()
    object.__setattr__(observed, field, value)
    with pytest.raises(QuickBooksAdapterError, match="replay"):
        adapt_payment(observed, invoice=mapped_invoice(), binding=BINDING,
                      import_run_id="run-1")


def test_typed_payment_amount_and_link_mutation_fail_complete_qs4_replay():
    observed = observe_p()
    object.__setattr__(observed.lines[0], "amount", Decimal("49.00"))
    with pytest.raises(QuickBooksAdapterError, match="replay"):
        adapt_payment(observed, invoice=mapped_invoice(), binding=BINDING,
                      import_run_id="run-1")
    observed = observe_p()
    object.__setattr__(observed.lines[0].links[0], "transaction_id", "other")
    with pytest.raises(QuickBooksAdapterError, match="replay"):
        adapt_payment(observed, invoice=mapped_invoice(), binding=BINDING,
                      import_run_id="run-1")


def test_forged_or_mutated_exact_invoice_result_fails_integrity_check():
    invoice = mapped_invoice()
    forged = InvoiceAdapterResult(
        invoice.source_observation, invoice.observation,
        invoice.semantic_result, invoice.document, "customer-2")
    with pytest.raises(QuickBooksAdapterError, match="integrity"):
        adapt_payment(observe_p(), invoice=forged, binding=BINDING,
                      import_run_id="run-1")
    object.__setattr__(invoice, "customer_reference_value", "customer-2")
    with pytest.raises(QuickBooksAdapterError, match="integrity"):
        adapt_payment(observe_p(), invoice=invoice, binding=BINDING,
                      import_run_id="run-1")


def test_forged_linked_result_nested_objects_fail_without_property_or_equality():
    invoice = mapped_invoice()
    for field in ("source_observation", "observation", "semantic_result", "document"):
        forged = mapped_invoice()
        object.__setattr__(forged, field, HostileEvidence())
        with pytest.raises(QuickBooksAdapterError) as caught:
            adapt_payment(observe_p(), invoice=forged, binding=BINDING,
                          import_run_id="run-1")
        assert "private-evidence-text" not in str(caught.value)


def test_tax_percent_must_reconcile_without_rounding():
    raw = invoice_raw()
    raw["TxnTaxDetail"]["TaxLine"][0]["TaxLineDetail"]["TaxPercent"] = Decimal("19.999")
    with pytest.raises(QuickBooksAdapterError, match="TaxPercent"):
        mapped_invoice(raw)


def test_absent_tax_percent_leaves_canonical_rate_unresolved():
    raw = invoice_raw()
    raw["TxnTaxDetail"]["TaxLine"][0]["TaxLineDetail"].pop("TaxPercent")
    assert mapped_invoice(raw).document.lines[0].tax.vat_rate is None
    observed = observe_i()
    object.__setattr__(observed, "realm_id", "realm-2")
    with pytest.raises(QuickBooksAdapterError, match="digest|identity|binding"):
        adapt_invoice(observed, binding=BINDING, import_run_id="run-1")


def test_observation_is_immutable_redacted_and_source_mutation_has_no_effect():
    raw = invoice_raw(); observed = observe_i(raw); digest = observed.source_digest
    raw["TotalAmt"] = Decimal("999.00")
    assert observed.source_digest == digest
    assert "customer-1" not in repr(observed)
    assert "customer-1" not in repr(observed.source_evidence)
    assert mapped_invoice().observation.raw_evidence_reference is None


def test_adapter_has_no_network_file_write_or_activation_behaviour(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("forbidden side effect")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(builtins, "open", forbidden)
    invoice = mapped_invoice()
    payment = adapt_payment(observe_p(), invoice=invoice, binding=BINDING,
                            import_run_id="run-1")
    assert payment.allocation.amount == Decimal("50.00")
    from reserved.providers.accounting.quickbooks import QuickBooksProvider
    with pytest.raises(NotImplementedError, match="not enabled"):
        QuickBooksProvider().list_invoices("opaque-reference-1")
