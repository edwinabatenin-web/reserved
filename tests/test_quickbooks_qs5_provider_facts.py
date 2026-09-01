"""Strict mechanical validation for the synthetic, network-inert Q-S5 facts."""

from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import re

import pytest

from reserved.providers.accounting.quickbooks_oauth_contract import RealmBinding
from reserved.providers.accounting.quickbooks_observation_contract import (
    QuickBooksObservationError, observe_invoice,
)


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/QUICKBOOKS_QS5_PROVIDER_FACTS.md"
FIXTURES = ROOT / "tests/fixtures/quickbooks_qs5"
FIXTURE_NAMES = ("invoice_payment_page.json", "unapplied_payment.json", "cdc_page_with_deletion.json")
NOW = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
BINDING = RealmBinding("user-1", "realm-1", "opaque-reference-1")
SECRET_KEY = re.compile(r"(?:access[_-]?token|refresh[_-]?token|client[_-]?secret|authorization|credential|password|email|phone|webaddr|api[_-]?key)", re.I)
SECRET_VALUE = re.compile(r"(?:https?://|bearer\s|basic\s|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})", re.I)


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def strict_loads(text):
    return json.loads(text, parse_float=Decimal, object_pairs_hook=reject_duplicate_keys)


def load(name):
    return strict_loads((FIXTURES / name).read_text(encoding="utf-8"))


def contract():
    text = DOC.read_text(encoding="utf-8")
    matches = re.findall(r"```json provider-facts-contract\n(.*?)\n```", text, re.S)
    if len(matches) != 1:
        raise ValueError("facts document must contain one contract")
    return strict_loads(matches[0])


def validate_contract(facts):
    if type(facts) is not dict:
        raise ValueError("facts contract must be an object")
    exact_int(facts.get("minorversion"), 75, "minorversion")
    expected_bounds = {"query_max_results": 1000, "cdc_max_objects": 1000,
                       "cdc_lookback_days": 30}
    if type(facts.get("bounds")) is not dict or set(facts["bounds"]) != set(expected_bounds):
        raise ValueError("facts bounds are malformed")
    for field, expected in expected_bounds.items():
        exact_int(facts["bounds"][field], expected, field)


def exact_int(value, expected, field):
    if type(value) is not int or value != expected:
        raise ValueError(f"{field} must be exact integer {expected}")


def nonnegative_money(value, field):
    if type(value) not in (int, Decimal) or not Decimal(value).is_finite() or value < 0:
        raise ValueError(f"{field} must be non-negative numeric money")
    return Decimal(value)


def validate_safe_synthetic(root):
    if type(root) is not dict or root.get("synthetic") is not True:
        raise ValueError("fixture root must be a synthetic object")
    exact_int(root.get("minorversion"), 75, "minorversion")
    ids = set()

    def walk(value, key=None):
        if key is not None and SECRET_KEY.search(key) and key != "SyncToken":
            raise ValueError("secret-shaped field")
        if type(value) is dict:
            entity_id = value.get("Id")
            if entity_id is not None and ("SyncToken" in value or "status" in value):
                if type(entity_id) is not str or not entity_id.startswith("synthetic-"):
                    raise ValueError("non-synthetic identity")
                if entity_id in ids:
                    raise ValueError("duplicate entity ID")
                ids.add(entity_id)
            for child_key, child in value.items():
                walk(child, child_key)
        elif type(value) is list:
            for child in value:
                walk(child)
        elif type(value) is str and SECRET_VALUE.search(value):
            raise ValueError("secret-shaped or external value")
    walk(root)


def validate_query_fixture(root):
    validate_safe_synthetic(root)
    expected = (("InvoiceQueryResponse", "Invoice"), ("PaymentQueryResponse", "Payment"))
    if set(root) != {"synthetic", "minorversion", *(name for name, _ in expected)}:
        raise ValueError("malformed query bundle root")
    for response_name, entity_name in expected:
        response = root[response_name]
        if type(response) is not dict or set(response) != {"startPosition", "maxResults", "totalCount", entity_name}:
            raise ValueError("query response must be entity-specific")
        exact_int(response["startPosition"], 1, "startPosition")
        exact_int(response["maxResults"], 1, "maxResults")
        exact_int(response["totalCount"], 1, "totalCount")
        if type(response[entity_name]) is not list or len(response[entity_name]) != 1:
            raise ValueError("entity count does not reconcile")
    invoice = root["InvoiceQueryResponse"]["Invoice"][0]
    payment = root["PaymentQueryResponse"]["Payment"][0]
    if invoice.get("CurrencyRef") != payment.get("CurrencyRef") or invoice.get("CurrencyRef") != {"value": "GBP"}:
        raise ValueError("linked currency must be explicit and consistent")
    if invoice.get("LinkedTxn") != [{"TxnId": payment.get("Id"), "TxnType": "Payment"}]:
        raise ValueError("invoice/payment link does not reconcile")
    lines = payment.get("Line")
    if type(lines) is not list:
        raise ValueError("Payment Line must be a list")
    applied = Decimal(0)
    for line in lines:
        if type(line) is not dict or "Amount" not in line:
            raise ValueError("supported Payment line requires Amount")
        amount = nonnegative_money(line["Amount"], "Line.Amount")
        links = line.get("LinkedTxn")
        if type(links) is not list or len(links) != 1:
            raise ValueError("supported Payment line requires exactly one link")
        if links[0] != {"TxnId": invoice.get("Id"), "TxnType": "Invoice"}:
            raise ValueError("unsupported or wrong allocation link")
        applied += amount
    total = nonnegative_money(payment.get("TotalAmt"), "Payment.TotalAmt")
    unapplied = nonnegative_money(payment.get("UnappliedAmt"), "Payment.UnappliedAmt")
    if applied > total or applied + unapplied != total:
        raise ValueError("Payment allocation does not reconcile")
    if nonnegative_money(invoice.get("TotalAmt"), "Invoice.TotalAmt") - applied != nonnegative_money(invoice.get("Balance"), "Invoice.Balance"):
        raise ValueError("Invoice balance does not corroborate allocation")


def validate_unapplied_fixture(root):
    validate_safe_synthetic(root)
    if set(root) != {"synthetic", "minorversion", "Payment"} or type(root["Payment"]) is not dict:
        raise ValueError("malformed unapplied fixture root")
    payment = root["Payment"]
    if {"TxnDate", "CurrencyRef", "GlobalTaxCalculation", "TxnTaxDetail"} & set(payment):
        raise ValueError("absent retained date, currency, and tax must remain absent")
    if payment.get("Line") != []:
        raise ValueError("unapplied Payment must have no allocation lines")
    if nonnegative_money(payment.get("UnappliedAmt"), "UnappliedAmt") != nonnegative_money(payment.get("TotalAmt"), "TotalAmt"):
        raise ValueError("unapplied amount does not reconcile")


def cdc_entities(root):
    try:
        groups = root["CDCResponse"]
        responses = groups[0]["QueryResponse"]
    except (KeyError, IndexError, TypeError):
        raise ValueError("malformed CDC root") from None
    if type(groups) is not list or len(groups) != 1 or type(responses) is not list or len(responses) != 1:
        raise ValueError("malformed CDC root")
    response = responses[0]
    if type(response) is not dict or set(response) != {"Invoice"} or type(response["Invoice"]) is not list:
        raise ValueError("malformed CDC entity group")
    return response["Invoice"]


def validate_cdc_fixture(root):
    validate_safe_synthetic(root)
    if set(root) != {"synthetic", "minorversion", "CDCResponse"}:
        raise ValueError("malformed CDC fixture root")
    entities = cdc_entities(root)
    if len(entities) > 1000:
        raise ValueError("CDC actual object count exceeds 1000")
    if not entities:
        raise ValueError("representative CDC fixture must not be empty")
    for entity in entities:
        deleted = entity.get("status") == "Deleted"
        live_fields = {"SyncToken", "CustomerRef", "CurrencyRef", "Line", "TotalAmt", "Balance"}
        if deleted and (set(entity) != {"Id", "status", "MetaData"} or live_fields & set(entity)):
            raise ValueError("tombstone cannot masquerade as live")
        if not deleted and ("status" in entity or not live_fields <= set(entity)):
            raise ValueError("live/tombstone ambiguity")


def observed(invoice):
    return observe_invoice(invoice, binding=BINDING, user_id="user-1", realm_id="realm-1", credential_reference="opaque-reference-1", retrieved_at=NOW)


def test_contract_sources_decisions_and_exact_bounds_are_retained():
    facts = contract()
    validate_contract(facts)
    assert facts["inspection_date"] == "2026-09-01"
    assert facts["sources"] == {
        "minor_versions": "https://developer.intuit.com/app/developer/qbo/docs/learn/explore-the-quickbooks-online-api/minor-versions",
        "invoice": "https://developer.intuit.com/app/developer/qbo/docs/api/accounting/most-commonly-used/invoice",
        "payment": "https://developer.intuit.com/app/developer/qbo/docs/api/accounting/most-commonly-used/payment",
        "query": "https://developer.intuit.com/app/developer/qbo/docs/learn/explore-the-quickbooks-online-api/data-queries",
        "cdc": "https://developer.intuit.com/app/developer/qbo/docs/learn/explore-the-quickbooks-online-api/change-data-capture",
    }
    assert facts["decisions"] == {"settlement_evidence": "balance_corroborated_by_payment_allocations", "allocation_evidence": "payment_required", "unapplied_amount": "preserve", "absent_date_currency_tax": "remain_absent", "incomplete_pagination_or_cdc": "fail_closed", "unknown_link_type": "fail_closed", "query_snapshot_stability": "not_assumed"}
    assert facts["bounds"] == {"query_max_results": 1000, "cdc_max_objects": 1000, "cdc_lookback_days": 30}
    assert facts["documented_payment_link_types"] == ["Invoice", "CreditMemo", "Expense", "Check", "CreditCardCredit", "JournalEntry"]
    assert facts["qs5_supported_allocation_link_types"] == ["Invoice"]


@pytest.mark.parametrize("field,bad", [
    ("query_max_results", True), ("cdc_max_objects", 1000.0),
    ("cdc_lookback_days", "30"),
])
def test_contract_limit_wrong_json_types_fail(field, bad):
    facts = contract(); facts["bounds"][field] = bad
    with pytest.raises(ValueError, match="exact integer"):
        validate_contract(facts)


def test_all_positive_fixtures_pass_strict_reusable_validators():
    validate_query_fixture(load(FIXTURE_NAMES[0])); validate_unapplied_fixture(load(FIXTURE_NAMES[1])); validate_cdc_fixture(load(FIXTURE_NAMES[2]))


def test_every_live_invoice_composes_through_qs4_and_tombstone_does_not():
    query_live = load(FIXTURE_NAMES[0])["InvoiceQueryResponse"]["Invoice"]
    cdc = cdc_entities(load(FIXTURE_NAMES[2])); cdc_live = [x for x in cdc if x.get("status") != "Deleted"]; tombstones = [x for x in cdc if x.get("status") == "Deleted"]
    assert len(query_live) == len(cdc_live) == len(tombstones) == 1
    assert all(observed(item).lines for item in query_live + cdc_live)
    with pytest.raises(QuickBooksObservationError): observed(tombstones[0])


@pytest.mark.parametrize("bad", [True, 75.0, "75"])
def test_minorversion_wrong_json_types_fail(bad):
    value = load(FIXTURE_NAMES[0]); value["minorversion"] = bad
    with pytest.raises(ValueError, match="exact integer"): validate_query_fixture(value)


@pytest.mark.parametrize("field,bad", [("startPosition", True), ("maxResults", 1.0), ("totalCount", "1")])
def test_query_limit_wrong_json_types_fail(field, bad):
    value = load(FIXTURE_NAMES[0]); value["InvoiceQueryResponse"][field] = bad
    with pytest.raises(ValueError, match="exact integer"): validate_query_fixture(value)


def test_duplicate_json_keys_are_rejected_before_validation():
    with pytest.raises(ValueError, match="duplicate JSON key"): strict_loads('{"synthetic":true,"minorversion":75,"minorversion":75}')


@pytest.mark.parametrize("validator,bad", [(validate_query_fixture, []), (validate_unapplied_fixture, {"synthetic": True, "minorversion": 75}), (validate_cdc_fixture, {"synthetic": True, "minorversion": 75, "CDCResponse": {}})])
def test_malformed_roots_fail(validator, bad):
    with pytest.raises(ValueError): validator(bad)


def mutate_query(change):
    value = load(FIXTURE_NAMES[0]); change(value); return value


@pytest.mark.parametrize("change", [
    lambda x: x["PaymentQueryResponse"]["Payment"][0].__setitem__("Id", x["InvoiceQueryResponse"]["Invoice"][0]["Id"]),
    lambda x: x["PaymentQueryResponse"]["Payment"][0]["Line"][0].__setitem__("Amount", Decimal("81")),
    lambda x: x["PaymentQueryResponse"]["Payment"][0]["Line"][0]["LinkedTxn"][0].__setitem__("TxnId", "synthetic-invoice-wrong-999"),
    lambda x: x["PaymentQueryResponse"]["Payment"][0].__setitem__("CurrencyRef", {"value": "USD"}),
    lambda x: x["PaymentQueryResponse"]["Payment"][0]["Line"][0]["LinkedTxn"][0].__setitem__("TxnType", "CreditMemo"),
    lambda x: x["PaymentQueryResponse"]["Payment"][0]["Line"][0].pop("Amount"),
    lambda x: x["PaymentQueryResponse"]["Payment"][0]["Line"][0].__setitem__("Amount", Decimal("-1")),
    lambda x: x["PaymentQueryResponse"]["Payment"][0]["Line"][0].__setitem__("Amount", "50"),
    lambda x: x["PaymentQueryResponse"]["Payment"][0]["Line"][0]["LinkedTxn"].append({"TxnId": "synthetic-invoice-other-999", "TxnType": "Invoice"}),
])
def test_adversarial_allocation_identity_link_currency_and_amount_cases_fail(change):
    with pytest.raises(ValueError): validate_query_fixture(mutate_query(change))


def test_invented_date_in_intentionally_dateless_payment_fails():
    value = load(FIXTURE_NAMES[1]); value["Payment"]["TxnDate"] = "2026-09-01"
    with pytest.raises(ValueError, match="remain absent"): validate_unapplied_fixture(value)


@pytest.mark.parametrize("field,value", [("access_token", "synthetic"), ("memo", "Bearer synthetic"), ("email", "person@example.com")])
def test_secret_shaped_fields_and_values_fail(field, value):
    fixture = load(FIXTURE_NAMES[1]); fixture["Payment"][field] = value
    with pytest.raises(ValueError, match="secret-shaped"): validate_unapplied_fixture(fixture)


def test_live_tombstone_ambiguity_fails():
    value = load(FIXTURE_NAMES[2]); value["CDCResponse"][0]["QueryResponse"][0]["Invoice"][0]["status"] = "Deleted"
    with pytest.raises(ValueError, match="tombstone"): validate_cdc_fixture(value)


def test_cdc_actual_object_count_above_1000_fails_without_page_metadata():
    value = load(FIXTURE_NAMES[2]); live = value["CDCResponse"][0]["QueryResponse"][0]["Invoice"][0]
    value["CDCResponse"][0]["QueryResponse"][0]["Invoice"] = [deepcopy(live) for _ in range(1001)]
    for index, item in enumerate(value["CDCResponse"][0]["QueryResponse"][0]["Invoice"]): item["Id"] = f"synthetic-invoice-live-{index:04d}"
    with pytest.raises(ValueError, match="actual object count exceeds 1000"): validate_cdc_fixture(value)
