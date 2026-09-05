"""Synthetic real FA-S1 -> observation -> mapping -> canonical normalisation."""
import ast
from copy import deepcopy
from dataclasses import fields, replace
from datetime import datetime, timedelta, timezone, tzinfo
from decimal import Decimal, localcontext
from hashlib import sha256
import json
from pathlib import Path

import pytest

from reserved.providers.accounting import freeagent_invoice_adapter as subject
from reserved.providers.accounting.contracts import (
    AccountingProviderName, CanonicalDocumentState, CorrectionLifecycle,
    EvidenceState, LineValueSemantics, SettlementState, TaxAmountSemantics,
)
from reserved.providers.accounting.freeagent import FreeAgentProvider
from reserved.providers.readiness import PROVIDERS


def fixtures():
    company = {"company": {
        "id": "123", "type": "UkSoleTrader", "currency": "GBP",
        "country": "United Kingdom", "cis_enabled": False,
        "cis_subcontractor": False, "cis_contractor": False,
    }}
    invoice = {"invoices": [{
        "url": "https://api.freeagent.com/v2/invoices/101",
        "contact": "https://api.freeagent.com/v2/contacts/201",
        "dated_on": "2026-09-01", "due_on": "2026-09-30", "payment_terms_in_days": 29,
        "currency": "GBP", "status": "Open", "net_value": "125.00",
        "total_value": "125.00", "sales_tax_value": "0.00", "discount_percent": "0",
        "involves_sales_tax": False, "is_interim_uk_vat": False, "ec_status": "UK/Non-EC",
        "paid_value": "25.00", "due_value": "100.00", "reference": "SYN-101",
        "invoice_items": [{"url": "https://api.freeagent.com/v2/invoice_items/301",
                           "item_type": "Services", "description": "Synthetic service",
                           "quantity": "2.5", "price": "50.00", "position": "1.0"}],
    }]}
    context = dict(user_id="users:1", connected_organisation_id="connection:1",
                   business_id="business:1", company_id="123", import_run_id="import:1",
                   retrieved_at=datetime(2026, 9, 5, 12, tzinfo=timezone.utc))
    return company, invoice, context


def mapped(company=None, invoice=None, context=None, observation=None):
    c, i, x = fixtures()
    c = c if company is None else company
    i = i if invoice is None else invoice
    x = x if context is None else context
    observed = subject.observe_invoice(c, i, **x) if observation is None else observation
    return subject.adapt_invoice(c, i, observation=observed, **x)


@pytest.mark.parametrize("path", [
    "invoices/999", "contacts/999", "bank_accounts/999", "invoices/101/pdf",
    "invoices/999/pdf", "invoices/101", "contacts/201", "bank_accounts/301",
])
def test_incompatible_item_resource_never_reaches_normalisation(path, monkeypatch):
    c, i, x = fixtures()
    i["invoices"][0]["invoice_items"][0]["url"] = "https://api.freeagent.com/v2/" + path
    observed = subject.observe_invoice(c, i, **x)
    def unexpected(**kwargs):
        pytest.fail("Incompatible item resource reached canonical normalisation")
    monkeypatch.setattr(subject, "normalise_document", unexpected)
    with pytest.raises(subject.FreeAgentInvoiceAdapterError, match="incompatible_item_resource"):
        subject.adapt_invoice(c, i, observation=observed, **x)


@pytest.mark.parametrize("item_type,item_id", [("Products", "302"), ("Services", "301")])
def test_supported_source_item_identity_is_preserved(item_type, item_id):
    c, i, x = fixtures()
    url = "https://api.freeagent.com/v2/invoice_items/" + item_id
    i["invoices"][0]["invoice_items"][0].update(url=url, item_type=item_type)
    result = mapped(c, i, x)
    assert result.document.lines[0].line_id == url
    assert result.document.gross_amount == Decimal("125.00")
    assert result.observation.evidence_state is EvidenceState.UNRESOLVED


@pytest.mark.parametrize("namespace", [
    "invoices", "contacts", "projects", "properties", "bank_accounts",
    "recurring_invoices", "company", "categories", "stock_items",
])
@pytest.mark.parametrize("suffix", ["", "/999", "/999/pdf", "/999/nested/301"])
def test_all_evidenced_non_item_namespaces_and_subpaths_rejected(namespace, suffix, monkeypatch):
    c, i, x = fixtures()
    i["invoices"][0]["invoice_items"][0]["url"] = (
        "https://api.freeagent.com/v2/" + namespace + suffix
    )
    observed = subject.observe_invoice(c, i, **x)
    def unexpected(**kwargs):
        pytest.fail("Known non-item namespace reached canonical normalisation")
    monkeypatch.setattr(subject, "normalise_document", unexpected)
    reason = "incompatible_item_resource" if suffix else "source_identity"
    with pytest.raises(subject.FreeAgentInvoiceAdapterError, match=reason):
        subject.adapt_invoice(c, i, observation=observed, **x)


def test_real_complete_positive_and_only_correction_finalization(monkeypatch):
    calls = []
    normalise = subject.normalise_document
    def capture(**kwargs):
        result = normalise(**kwargs)
        calls.append((kwargs, result))
        return result
    monkeypatch.setattr(subject, "normalise_document", capture)
    result = mapped()
    kwargs, intermediate = calls[0]
    assert len(calls) == 1
    assert kwargs["adapter_result"].missing_facts == ()
    assert kwargs["adapter_result"].unsupported_facts == ()
    assert kwargs["adapter_result"].document_candidate.lines
    doc = result.document
    assert intermediate.correction_lifecycle is CorrectionLifecycle.NONE
    assert doc == replace(intermediate, correction_lifecycle=CorrectionLifecycle.UNKNOWN)
    assert [field.name for field in fields(doc) if getattr(doc, field.name) != getattr(intermediate, field.name)] == ["correction_lifecycle"]
    assert not hasattr(result, "semantic_result")
    assert doc.gross_amount == doc.net_amount == Decimal("125.00")
    assert doc.vat_amount == Decimal("0.00")
    assert len(doc.lines) == 1 and doc.lines[0].money.original_amount == Decimal("125.00")
    assert doc.lines[0].line_id == "https://api.freeagent.com/v2/invoice_items/301"
    assert doc.provider_balance.amount_paid == Decimal("25.00")
    assert doc.provider_balance.amount_due == Decimal("100.00")
    assert doc.cash_candidate is doc.accrual_candidate is None
    assert doc.settlement_state is SettlementState.UNKNOWN
    assert doc.canonical_state is CanonicalDocumentState.UNKNOWN
    assert doc.evidence_state is EvidenceState.UNRESOLVED
    assert doc.lines[0].tax.semantics is TaxAmountSemantics.UNKNOWN
    assert doc.lines[0].value_semantics is LineValueSemantics.UNKNOWN
    assert doc.lines[0].provider_category_id is doc.lines[0].tax.vat_rate is None
    assert doc.provenance is result.observation.provenance


def test_source_digest_and_complete_context_are_independent_of_later_mapping():
    c, i, x = fixtures()
    result = mapped(c, i, x)
    encoded = json.dumps({"company_response": c, "invoice_response": i},
                         sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    assert result.observation.provenance.source_record_digest == sha256(encoded.encode("ascii")).hexdigest()
    identity = result.observation.provenance.identity
    assert (identity.user_id, identity.connected_organisation_id, identity.business_id,
            identity.import_run_id, identity.provider) == (
                "users:1", "connection:1", "business:1", "import:1", AccountingProviderName.FREEAGENT)
    assert 'company_id="123"' in result.observation.provenance.source_definitions
    assert "invoice_response.invoices[0].invoice_items[0].price" in result.observation.provenance.source_fields
    assert result.observation.raw_evidence_reference is None
    assert result.observation.provenance.revision_id is None
    assert "membership" in result.observation.evidence_reason


def test_mapping_uses_owned_snapshot_not_later_mutable_caller_state(monkeypatch):
    c, i, x = fixtures()
    observed = subject.observe_invoice(c, i, **x)
    parse = subject.parse_invoice_list
    def change_caller(payload):
        i["invoices"][0]["invoice_items"][0]["description"] = "Changed after snapshot"
        return parse(payload)
    monkeypatch.setattr(subject, "parse_invoice_list", change_caller)
    result = mapped(c, i, x, observed)
    assert result.document.lines[0].description == "Synthetic service"
    assert result.observation == observed


def test_integer_company_identity_stays_integer_and_new_retrieval_is_not_new_economic_event():
    c, i, x = fixtures()
    c["company"]["id"] = 123
    x["company_id"] = 123
    first = mapped(c, i, x)
    second = mapped(c, i, {**x, "retrieved_at": x["retrieved_at"] + timedelta(hours=1)})
    assert "company_id=123" in first.observation.provenance.source_definitions
    assert first.observation.observation_id != second.observation.observation_id
    assert first.document.economic_event_id == second.document.economic_event_id


@pytest.mark.parametrize("field,value", [
    ("user_id", "users:2"), ("connected_organisation_id", "connection:2"),
    ("business_id", "business:2"), ("import_run_id", "import:2"),
    ("retrieved_at", datetime(2026, 9, 5, 13, tzinfo=timezone.utc)),
])
def test_cross_context_and_stale_retrieval_observation_cannot_be_reused(field, value):
    c, i, x = fixtures()
    observed = subject.observe_invoice(c, i, **x)
    changed = {**x, field: value}
    assert subject.observe_invoice(c, i, **changed).observation_id != observed.observation_id
    with pytest.raises(subject.FreeAgentInvoiceAdapterError, match="replay_mismatch"):
        mapped(c, i, changed, observed)


def test_changed_source_or_company_context_cannot_reuse_identity():
    c, i, x = fixtures()
    observed = subject.observe_invoice(c, i, **x)
    i["invoices"][0]["reference"] = "SYN-CHANGED"
    with pytest.raises(subject.FreeAgentInvoiceAdapterError, match="replay_mismatch"):
        mapped(c, i, x, observed)
    c, i, x = fixtures()
    c["company"]["id"] = "456"
    with pytest.raises(subject.FreeAgentInvoiceAdapterError, match="company_context_mismatch"):
        mapped(c, i, x, observed)
    x["company_id"] = "456"
    with pytest.raises(subject.FreeAgentInvoiceAdapterError, match="replay_mismatch"):
        mapped(c, i, x, observed)


@pytest.mark.parametrize("change", [
    lambda o: replace(o, observation_id="self-stamped"),
    lambda o: replace(o, evidence_state=EvidenceState.SELECTED),
    lambda o: replace(o, provenance=replace(o.provenance, source_record_digest="0" * 64)),
    lambda o: replace(o, provenance=replace(o.provenance, retrieved_at=datetime(2026, 9, 4, tzinfo=timezone.utc))),
    lambda o: replace(o, provenance=replace(o.provenance, identity=replace(o.provenance.identity, user_id="users:2"))),
    lambda o: {"observation_id": o.observation_id},
])
def test_self_stamped_or_mutated_observation_is_not_trusted(change):
    c, i, x = fixtures()
    with pytest.raises(subject.FreeAgentInvoiceAdapterError, match="replay_mismatch"):
        mapped(c, i, x, change(subject.observe_invoice(c, i, **x)))


@pytest.mark.parametrize("field", ["net_value", "sales_tax_value", "total_value", "discount_percent",
                                   "currency", "involves_sales_tax", "is_interim_uk_vat", "ec_status", "status", "invoice_items"])
@pytest.mark.parametrize("missing", [True, False])
def test_required_unknown_is_not_zero(field, missing):
    c, i, x = fixtures()
    if missing:
        del i["invoices"][0][field]
    else:
        i["invoices"][0][field] = None
    with pytest.raises(subject.FreeAgentInvoiceAdapterError):
        mapped(c, i, x)


def test_explicit_zero_and_optional_balance_absent_null_zero_distinctions():
    c, i, x = fixtures()
    raw = i["invoices"][0]
    raw.update(net_value="0", total_value="0", status="Zero Value")
    raw["invoice_items"][0]["quantity"] = "0"
    assert mapped(c, i, x).document.gross_amount == Decimal("0")
    identities = []
    for value in ("absent", None, "0"):
        raw.pop("paid_value", None)
        if value != "absent":
            raw["paid_value"] = value
        result = mapped(c, i, x)
        identities.append(result.observation.observation_id)
        assert result.document.provider_balance.amount_paid == (Decimal("0") if value == "0" else None)
    assert len(set(identities)) == 3


@pytest.mark.parametrize("status", ["Open", "Overdue", "Paid", "Zero Value"])
def test_raw_status_and_paid_date_never_create_settlement_or_recognition(status):
    c, i, x = fixtures()
    i["invoices"][0].update(status=status, paid_on="2026-09-02")
    if status == "Zero Value":
        i["invoices"][0].update(net_value="0", total_value="0")
        i["invoices"][0]["invoice_items"][0]["quantity"] = "0"
    doc = mapped(c, i, x).document
    assert doc.provider_status == status
    assert doc.settlement_state is SettlementState.UNKNOWN
    assert doc.cash_candidate is doc.accrual_candidate is None


@pytest.mark.parametrize("field,value", [
    ("total_value", "200.00"), ("sales_tax_value", "20.00"), ("discount_percent", "10"),
    ("currency", "EUR"), ("involves_sales_tax", True), ("is_interim_uk_vat", True),
    ("ec_status", "Reverse Charge"), ("status", "Refunded"), ("status", "Written-off"),
    ("status", "Part written-off"), ("status", "Draft"), ("status", "Overpaid"),
    ("cis_deduction", "0"), ("second_sales_tax_value", "0"), ("exchange_rate", "1.0"),
    ("new_adjustment", "0"), ("property", "https://api.freeagent.com/v2/properties/4"),
])
def test_unsupported_or_ambiguous_header_never_emits_document(field, value):
    c, i, x = fixtures()
    i["invoices"][0][field] = value
    with pytest.raises(subject.FreeAgentInvoiceAdapterError):
        mapped(c, i, x)


def test_inconsistent_official_header_example_is_not_repaired():
    c, i, x = fixtures()
    i["invoices"][0].update(net_value="0.0", sales_tax_value="0.0", total_value="200.0")
    with pytest.raises(subject.FreeAgentInvoiceAdapterError, match="reconcile"):
        mapped(c, i, x)


@pytest.mark.parametrize("field,value", [
    ("type", "UkLimitedCompany"), ("type", "UkUnincorporatedLandlord"),
    ("currency", "USD"), ("country", "United States"), ("country", None),
    ("cis_enabled", True), ("cis_subcontractor", True), ("cis_contractor", True),
    ("unknown_semantics", False), ("id", "0123"), ("id", 123),
])
def test_company_scope_and_typed_identity_preserved(field, value):
    c, i, x = fixtures()
    c["company"][field] = value
    with pytest.raises(subject.FreeAgentInvoiceAdapterError):
        mapped(c, i, x)


@pytest.mark.parametrize("field,value", [
    ("price", "49.99"), ("price", None), ("quantity", None), ("item_type", "Discount"),
    ("item_type", "Credit"), ("item_type", "Comment"), ("item_type", "VAT"),
    ("item_type", "Stock"), ("item_type", "Hours"), ("description", ""),
    ("url", "https://evil.example/v2/invoice_items/301"),
    ("url", "https://api.freeagent.com/v2/invoices/101"),
    ("url", "https://api.freeagent.com/v2/invoice_items/301?changed=1"),
    ("position", "2"), ("sales_tax_rate", "0"), ("category", "not-admitted"),
])
def test_item_ambiguity_and_identity_fail_closed(field, value):
    c, i, x = fixtures()
    i["invoices"][0]["invoice_items"][0][field] = value
    with pytest.raises(subject.FreeAgentInvoiceAdapterError):
        mapped(c, i, x)


@pytest.mark.parametrize("field", ["url", "item_type", "description", "quantity", "price"])
def test_missing_item_fields_are_not_synthesised(field):
    c, i, x = fixtures()
    del i["invoices"][0]["invoice_items"][0][field]
    with pytest.raises(subject.FreeAgentInvoiceAdapterError):
        mapped(c, i, x)


@pytest.mark.parametrize("field", ["country", "cis_enabled", "cis_subcontractor", "cis_contractor"])
def test_missing_company_support_is_not_inferred(field):
    c, i, x = fixtures()
    del c["company"][field]
    with pytest.raises(subject.FreeAgentInvoiceAdapterError):
        mapped(c, i, x)


def test_nonzero_zero_value_status_is_conflicting():
    c, i, x = fixtures()
    i["invoices"][0]["status"] = "Zero Value"
    with pytest.raises(subject.FreeAgentInvoiceAdapterError, match="conflicts"):
        mapped(c, i, x)


@pytest.mark.parametrize("amount", ["1e99999999", "-0", "+1", " 1", "01", "NaN", "Infinity",
                                    "1.001", "10000000000", True, 1.0, Decimal("1")])
def test_decimal_bounds_precede_arithmetic(amount):
    c, i, x = fixtures()
    i["invoices"][0]["invoice_items"][0]["price"] = amount
    with pytest.raises(subject.FreeAgentInvoiceAdapterError):
        mapped(c, i, x)


def test_no_rounding_under_hostile_decimal_context():
    with localcontext() as context:
        context.prec = 1
        context.Emax = 1
        assert mapped().document.gross_amount == Decimal("125.00")
    c, i, x = fixtures()
    i["invoices"][0]["invoice_items"][0].update(quantity="0.333333", price="3.00")
    i["invoices"][0].update(net_value="1.00", total_value="1.00")
    with pytest.raises(subject.FreeAgentInvoiceAdapterError, match="reconcile"):
        mapped(c, i, x)


def test_graph_cycles_aliases_and_bounds_do_not_echo(caplog):
    for mode in ("cycle", "alias", "width", "depth", "text", "bytes"):
        c, i, x = fixtures()
        raw = i["invoices"][0]
        if mode == "cycle":
            raw["cycle"] = raw
        elif mode == "alias":
            raw["alias"] = raw["invoice_items"]
        elif mode == "width":
            raw["invoice_items"] = [{} for _ in range(101)]
        elif mode == "depth":
            value = {}
            raw["deep"] = value
            for _ in range(12):
                value["child"] = {}
                value = value["child"]
        elif mode == "text":
            raw["reference"] = "PRIVATE" * 400
        else:
            raw["many"] = ["PRIVATE" * 250 for _ in range(90)]
        with pytest.raises(subject.FreeAgentInvoiceAdapterError) as error:
            mapped(c, i, x)
        assert "PRIVATE" not in str(error.value) + caplog.text


def test_hostile_hooks_and_multiple_or_missing_lines_never_run():
    class Hostile(dict):
        def items(self):
            raise AssertionError("must not execute")
    c, i, x = fixtures()
    with pytest.raises(subject.FreeAgentInvoiceAdapterError):
        mapped(Hostile(c), i, x)
    for items in ([], [i["invoices"][0]["invoice_items"][0], {}]):
        changed = deepcopy(i)
        changed["invoices"][0]["invoice_items"] = items
        with pytest.raises(subject.FreeAgentInvoiceAdapterError):
            mapped(c, changed, x)


def test_utc_and_context_exact_types_before_hooks():
    class Hostile(tzinfo):
        def utcoffset(self, dt):
            raise AssertionError("must not execute")
    c, i, x = fixtures()
    for time in (datetime(2026, 9, 5), datetime(2026, 9, 5, tzinfo=Hostile()),
                 datetime(2026, 9, 5, tzinfo=timezone(timedelta(hours=1)))):
        with pytest.raises(subject.FreeAgentInvoiceAdapterError):
            mapped(c, i, {**x, "retrieved_at": time})
    with pytest.raises(subject.FreeAgentInvoiceAdapterError):
        mapped(c, i, {**x, "user_id": "<script>PRIVATE</script>"})


def test_no_provider_transport_storage_activation_or_runtime_imports():
    assert next(p for p in PROVIDERS if p.name == "freeagent").implementation_enabled is False
    with pytest.raises(NotImplementedError):
        FreeAgentProvider().list_invoices("synthetic-reference")
    source = Path(subject.__file__).read_text()
    imports = [node for node in ast.walk(ast.parse(source)) if isinstance(node, (ast.Import, ast.ImportFrom))]
    modules = {node.module if isinstance(node, ast.ImportFrom) else alias.name
               for node in imports for alias in node.names}
    assert not any(name.split(".")[0] in {"os", "requests", "httpx", "socket", "sqlite3", "flask"}
                   for name in modules)
    assert "open(" not in source and "getenv(" not in source
