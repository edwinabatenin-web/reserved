"""Adversarial tests for the pure QuickBooks Q-S4 observation boundary."""

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone, tzinfo
from decimal import Decimal
import ast
from collections.abc import Mapping
from pathlib import Path

import pytest

from reserved.providers.accounting.quickbooks import QuickBooksProvider
from reserved.providers.accounting.quickbooks_oauth_contract import RealmBinding
from reserved.providers.accounting.quickbooks_observation_contract import (
    CompanyInfoObservation, GLOBAL_TAX_CALCULATIONS, LINE_DETAIL_TYPES,
    PaymentObservation, QuickBooksObservationError, observe_company_info,
    observe_invoice, observe_payment,
)


NOW = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
BINDING = RealmBinding("user-1", "realm-1", "opaque-reference-1")


def identity(**changes):
    result = dict(binding=BINDING, user_id="user-1", realm_id="realm-1",
                  credential_reference="opaque-reference-1", retrieved_at=NOW)
    result.update(changes)
    return result


def company(**changes):
    result = {
        "Id": "company-1", "SyncToken": "2", "CompanyName": "Example Ltd",
        "LegalName": None, "Country": "United Kingdom", "CompanyStartDate": "2020-02-29",
        "MetaData": {"CreateTime": "2020-01-01T01:02:03Z"},
        "NameValue": [{"Name": "context", "Value": "evidence"}],
    }
    result.update(changes)
    return result


def line(**changes):
    result = {"Id": "1", "DetailType": "SalesItemLineDetail",
              "Amount": Decimal("12.3400"),
              "SalesItemLineDetail": {"ItemRef": {"value": "item-1"}}}
    result.update(changes)
    return result


def invoice(**changes):
    result = {
        "Id": "invoice-1", "SyncToken": "7",
        "CustomerRef": {"value": "customer-1", "name": "Private customer"},
        "Line": [line()], "TxnDate": "2026-08-31", "DueDate": "2026-09-30",
        "TotalAmt": Decimal("12.3400"), "Balance": "12.34",
        "CurrencyRef": None, "GlobalTaxCalculation": "TaxExcluded",
        "TxnTaxDetail": {"TotalTax": Decimal("0")}, "LinkedTxn": [],
        "MetaData": {"LastUpdatedTime": "2026-09-01T09:59:00+00:00"},
        "future": {"preserved": True},
    }
    result.update(changes)
    return result


def payment_link(**changes):
    result = {"TxnId": "invoice-1", "TxnType": "Invoice",
              "future": {"retained": True}}
    result.update(changes)
    return result


def payment_line(**changes):
    result = {"Amount": Decimal("12.3400"),
              "LinkedTxn": [payment_link()], "future": ["evidence"]}
    result.update(changes)
    return result


def payment(**changes):
    result = {
        "Id": "payment-1", "SyncToken": "8",
        "CustomerRef": {"value": "customer-1", "name": "Private customer"},
        "TxnDate": "2026-08-31", "TotalAmt": Decimal("12.3400"),
        "UnappliedAmt": Decimal("0.00"), "CurrencyRef": {"value": "GBP"},
        "Line": [payment_line()],
        "MetaData": {"LastUpdatedTime": "2026-09-01T09:59:00Z"},
        "future": {"preserved": True},
    }
    result.update(changes)
    return result


def test_positive_company_and_invoice_are_bound_frozen_and_observational():
    source = company()
    observed = observe_company_info(source, **identity())
    assert isinstance(observed, CompanyInfoObservation)
    assert observed.entity_id == "company-1" and observed.company_start_date.isoformat() == "2020-02-29"
    assert observed.user_id == "user-1" and observed.realm_id == "realm-1"
    source["CompanyName"] = "mutated"
    source["NameValue"][0]["Value"] = "mutated"
    assert observed.company_name == "Example Ltd"
    assert observed.source_evidence["NameValue"][0]["Value"] == "evidence"
    with pytest.raises(TypeError):
        observed.source_evidence["new"] = True
    with pytest.raises(FrozenInstanceError):
        observed.company_name = "mutated"

    result = observe_invoice(invoice(), **identity())
    assert result.lines[0].amount == Decimal("12.3400")
    assert result.total_amount == Decimal("12.3400")
    assert result.balance == Decimal("12.34")
    assert result.currency_ref_present and result.transaction_tax_detail_present
    forbidden = {"paid", "fully_paid", "tax_liability", "canonical", "launch_ready", "owner"}
    assert forbidden.isdisjoint(result.__dataclass_fields__)


@pytest.mark.parametrize("change", [
    {"user_id": "user-2"}, {"realm_id": "realm-2"},
    {"credential_reference": "opaque-reference-2"},
    {"binding": object()},
])
def test_identity_substitution_fails_without_echo(change):
    with pytest.raises(QuickBooksObservationError) as caught:
        observe_company_info(company(), **identity(**change))
    assert "user-2" not in str(caught.value)
    assert "realm-2" not in str(caught.value)
    assert "opaque-reference-2" not in str(caught.value)


@pytest.mark.parametrize("field", ["Id", "SyncToken", "CompanyName"])
@pytest.mark.parametrize("bad", [None, "", "  "])
def test_company_required_identity_is_non_blank(field, bad):
    with pytest.raises(QuickBooksObservationError):
        observe_company_info(company(**{field: bad}), **identity())


@pytest.mark.parametrize("field", ["Id", "SyncToken"])
@pytest.mark.parametrize("bad", [None, "", "  "])
def test_invoice_required_identity_is_non_blank(field, bad):
    with pytest.raises(QuickBooksObservationError):
        observe_invoice(invoice(**{field: bad}), **identity())


@pytest.mark.parametrize("bad", [None, {}, {"value": None}, {"value": " "}])
def test_customer_reference_is_required(bad):
    with pytest.raises(QuickBooksObservationError):
        observe_invoice(invoice(CustomerRef=bad), **identity())


@pytest.mark.parametrize("lines", [None, [], [line()] * 751])
def test_invoice_line_bounds(lines):
    with pytest.raises(QuickBooksObservationError):
        observe_invoice(invoice(Line=lines), **identity())


def test_all_and_only_observed_line_categories_are_accepted():
    assert LINE_DETAIL_TYPES == {"SalesItemLineDetail", "DiscountLineDetail",
                                 "SubTotalLineDetail"}
    for category in LINE_DETAIL_TYPES:
        candidate = line(DetailType=category)
        candidate.pop("SalesItemLineDetail")
        candidate[category] = {}
        assert observe_invoice(invoice(Line=[candidate]), **identity()).lines
    for secret in ["UnsupportedSecretCategory", "GroupLineDetail",
                   "DescriptionLineDetail"]:
        with pytest.raises(QuickBooksObservationError) as caught:
            observe_invoice(invoice(Line=[line(DetailType=secret)]), **identity())
        assert secret not in str(caught.value)


@pytest.mark.parametrize("candidate", [
    line(SalesItemLineDetail=None),
    {"Id": "1", "DetailType": "SalesItemLineDetail"},
    line(DetailType="DiscountLineDetail"),
    line(DiscountLineDetail={}),
    line(DescriptionLineDetail={}),
])
def test_line_detail_member_must_be_exactly_matching_plain_object(candidate):
    with pytest.raises(QuickBooksObservationError) as caught:
        observe_invoice(invoice(Line=[candidate]), **identity())
    assert "customer" not in str(caught.value)


def test_company_country_is_a_bounded_name_without_iso_interpretation():
    assert observe_company_info(company(Country="United Kingdom"), **identity()).country == "United Kingdom"


def test_absent_null_and_additive_fields_are_distinct_and_preserved():
    absent = company(); absent.pop("LegalName")
    a = observe_company_info(absent, **identity())
    n = observe_company_info(company(LegalName=None), **identity())
    assert "LegalName" not in a.present_fields and "LegalName" not in a.null_fields
    assert "LegalName" in n.present_fields and "LegalName" in n.null_fields
    assert "NameValue" in a.source_evidence
    assert a.source_digest != n.source_digest


def test_digest_is_deterministic_order_independent_and_type_preserving():
    first = invoice(future={"a": Decimal("1.0"), "b": "1.0"})
    second = dict(reversed(list(first.items())))
    assert observe_invoice(first, **identity()).source_digest == observe_invoice(second, **identity()).source_digest
    assert observe_invoice(first, **identity()).source_digest != observe_invoice(
        invoice(future={"a": Decimal("1.00"), "b": "1.0"}), **identity()).source_digest
    assert observe_invoice(first, **identity()).source_digest != observe_invoice(
        invoice(future={"a": "1.0", "b": "1.0"}), **identity()).source_digest


def test_attestation_is_order_stable_and_binds_retrieval_identity_and_source():
    raw = invoice(future={"a": Decimal("1.0"), "b": "one"})
    reordered = dict(reversed(list(raw.items())))
    first = observe_invoice(raw, **identity())
    second = observe_invoice(reordered, **identity())
    assert first.observation_attestation == second.observation_attestation
    assert first.source_digest == second.source_digest
    variants = [
        observe_invoice(raw, **identity(retrieved_at=NOW.replace(hour=11))),
        observe_invoice(raw, **identity(
            binding=RealmBinding("user-2", "realm-1", "opaque-reference-1"),
            user_id="user-2")),
        observe_invoice(invoice(future={"a": Decimal("1.0"), "b": "two"}),
                        **identity()),
    ]
    assert all(item.observation_attestation != first.observation_attestation
               for item in variants)


class HostileTimezone(tzinfo):
    def __init__(self):
        self.calls = {name: 0 for name in (
            "utcoffset", "dst", "tzname", "fromutc", "eq", "repr")}

    def _called(self, name):
        self.calls[name] += 1
        raise RuntimeError("private-timezone-text")

    def utcoffset(self, value): return self._called("utcoffset")
    def dst(self, value): return self._called("dst")
    def tzname(self, value): return self._called("tzname")
    def fromutc(self, value): return self._called("fromutc")
    def __eq__(self, other): return self._called("eq")
    def __repr__(self): return self._called("repr")


def test_hostile_retrieval_timezone_is_rejected_without_invoking_hooks():
    hostile = HostileTimezone()
    when = datetime(2026, 9, 1, 10, 0, tzinfo=hostile)
    with pytest.raises(QuickBooksObservationError) as caught:
        observe_invoice(invoice(), **identity(retrieved_at=when))
    assert all(count == 0 for count in hostile.calls.values())
    assert str(caught.value) == (
        "QuickBooks observation contract: retrieved_at must use a fixed-offset timezone")


def test_exact_fixed_offset_retrieval_time_normalizes_to_stable_utc_attestation():
    fixed = datetime(2026, 9, 1, 11, 0,
                     tzinfo=timezone(timedelta(hours=1)))
    utc = observe_invoice(invoice(), **identity())
    offset = observe_invoice(invoice(), **identity(retrieved_at=fixed))
    assert offset.retrieved_at == NOW
    assert offset.retrieved_at.tzinfo is timezone.utc
    assert offset.observation_attestation == utc.observation_attestation


class HostileBindingEquality:
    def __init__(self):
        self.invoked = False

    def __eq__(self, other):
        self.invoked = True
        raise RuntimeError("private-binding-text")


@pytest.mark.parametrize("field", [
    "user_id", "realm_id", "credential_reference",
])
def test_hostile_realm_binding_field_is_rejected_without_equality(field):
    binding = RealmBinding("user-1", "realm-1", "opaque-reference-1")
    hostile = HostileBindingEquality()
    object.__setattr__(binding, field, hostile)
    with pytest.raises(QuickBooksObservationError) as caught:
        observe_invoice(invoice(), **identity(binding=binding))
    assert hostile.invoked is False
    assert str(caught.value) == (
        "QuickBooks observation contract: realm binding identity is invalid")
    assert "private-binding-text" not in str(caught.value)


@pytest.mark.parametrize("bad", [True, 1.2, Decimal("NaN"), Decimal("Infinity"),
    Decimal("1e100"), Decimal("0.0000000000001"), "1e2", "NaN",
    "1000000000000000001"])
def test_money_rejects_inexact_nonfinite_exponent_and_excess(bad):
    with pytest.raises(QuickBooksObservationError):
        observe_invoice(invoice(TotalAmt=bad), **identity())


@pytest.mark.parametrize("field,bad", [
    ("TxnDate", "2026-02-29"), ("DueDate", "01/09/2026"),
    ("TxnDate", "2026-01-01T00:00:00Z"),
])
def test_dates_are_strict(field, bad):
    with pytest.raises(QuickBooksObservationError):
        observe_invoice(invoice(**{field: bad}), **identity())


@pytest.mark.parametrize("bad", ["2026-01-01", "2026-01-01T00:00:00",
                                  "2026-13-01T00:00:00Z"])
def test_metadata_timestamps_are_strict(bad):
    with pytest.raises(QuickBooksObservationError):
        observe_company_info(company(MetaData={"CreateTime": bad}), **identity())


def test_unicode_surrogates_fail_with_controlled_non_echoing_error():
    secret = "private\ud800value"
    with pytest.raises(QuickBooksObservationError) as caught:
        observe_company_info(company(future=secret), **identity())
    assert "private" not in str(caught.value)


def test_every_mapping_key_is_validated_before_sorting_or_freezing():
    for bad in [{1: "private"}, {"ok": 1, 2: "private"}]:
        with pytest.raises(QuickBooksObservationError):
            observe_company_info(company(future=bad), **identity())


class DictSubclass(dict):
    pass


class ListSubclass(list):
    pass


class HostileMapping(Mapping):
    def __getitem__(self, key):
        raise RuntimeError("synthetic-customer-secret")

    def __iter__(self):
        raise RuntimeError("synthetic-customer-secret")

    def __len__(self):
        raise RuntimeError("synthetic-customer-secret")


@pytest.mark.parametrize("bad", [DictSubclass(), HostileMapping(), (),
                                  ListSubclass(), [()]])
def test_only_exact_json_objects_and_arrays_enter_the_graph(bad):
    with pytest.raises(QuickBooksObservationError) as caught:
        observe_company_info(bad if bad != [()] else company(future=bad), **identity())
    assert "synthetic-customer-secret" not in str(caught.value)


@pytest.mark.parametrize("bad", [DictSubclass(company()),
                                  company(future=DictSubclass()),
                                  company(future=ListSubclass()),
                                  company(future=(1, 2))])
def test_container_subclasses_and_tuples_fail_at_nested_boundaries(bad):
    with pytest.raises(QuickBooksObservationError):
        observe_company_info(bad, **identity())


def test_resource_bounds_fail_as_contract_errors_not_runtime_errors():
    deep = None
    for _ in range(30):
        deep = {"x": deep}
    cases = [
        company(future=deep),
        company(future={str(i): i for i in range(2001)}),
        company(future="x" * 4097),
        company(future=b"x" * 2_000_001),
        company(future=[None] * 2001),
    ]
    for raw in cases:
        with pytest.raises(QuickBooksObservationError):
            observe_company_info(raw, **identity())


def test_node_and_overall_payload_bounds_are_enforced():
    # Width stays legal at each level while aggregate nodes/payload exceed bounds.
    with pytest.raises(QuickBooksObservationError):
        observe_company_info(company(future=[[None] * 2000 for _ in range(30)]), **identity())
    with pytest.raises(QuickBooksObservationError):
        observe_company_info(company(future=["x" * 4000 for _ in range(600)]), **identity())


def test_reprs_and_errors_do_not_disclose_source_or_credentials():
    secret = "sensitive-customer@example.invalid"
    result = observe_invoice(invoice(CustomerRef={"value": secret}), **identity())
    assert secret not in repr(result) and "opaque-reference-1" not in repr(result)
    assert secret not in repr(result.lines[0])
    assert secret not in repr(result.source_evidence)
    assert secret not in repr(result.source_evidence["CustomerRef"])
    nested = observe_company_info(company(future=[[secret], ["safe"]]), **identity())
    retained = nested.source_evidence["future"]
    assert secret not in repr(retained)
    assert secret not in repr(retained[0])
    assert secret not in repr(retained[:1])
    assert list(retained[0]) == [secret]
    with pytest.raises(QuickBooksObservationError) as caught:
        observe_invoice(invoice(Line=[line(DetailType=secret)]), **identity())
    assert secret not in str(caught.value) and secret not in repr(caught.value)


def test_tax_values_are_only_closed_source_observations():
    assert GLOBAL_TAX_CALCULATIONS == {"TaxExcluded", "TaxInclusive", "NotApplicable"}
    for value in GLOBAL_TAX_CALCULATIONS:
        result = observe_invoice(invoice(GlobalTaxCalculation=value), **identity())
        assert result.global_tax_calculation == value
    with pytest.raises(QuickBooksObservationError):
        observe_invoice(invoice(GlobalTaxCalculation="Calculated"), **identity())


def test_module_imports_have_no_network_or_runtime_capabilities():
    path = Path(__file__).parents[1] / "reserved/providers/accounting/quickbooks_observation_contract.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {alias.name.split(".")[0] for node in ast.walk(tree)
               if isinstance(node, ast.Import) for alias in node.names}
    imports |= {node.module.split(".")[0] for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module and node.level == 0}
    assert imports.isdisjoint({"requests", "httpx", "urllib", "socket", "ssl",
                               "os", "subprocess", "logging", "sqlite3"})
    text = path.read_text(encoding="utf-8").lower()
    assert "getenv" not in text and "authorisation_url(" not in text


def test_disabled_provider_placeholder_is_unchanged_in_behaviour():
    provider = QuickBooksProvider()
    with pytest.raises(NotImplementedError, match="not enabled"):
        provider.authorisation_url("user", "https://example.invalid/callback")
    with pytest.raises(NotImplementedError, match="not enabled"):
        provider.list_invoices("opaque")


def test_applied_payment_is_bound_frozen_and_observational():
    source = payment()
    observed = observe_payment(source, **identity())
    assert isinstance(observed, PaymentObservation)
    assert observed.entity_id == "payment-1" and observed.sync_token == "8"
    assert observed.customer_reference_value == "customer-1"
    assert observed.transaction_date.isoformat() == "2026-08-31"
    assert observed.total_amount == Decimal("12.3400")
    assert observed.unapplied_amount == Decimal("0.00")
    assert observed.lines[0].amount == Decimal("12.3400")
    assert observed.lines[0].links[0].transaction_id == "invoice-1"
    assert observed.lines[0].links[0].transaction_type == "Invoice"
    source["Line"][0]["Amount"] = Decimal("999")
    source["Line"][0]["LinkedTxn"][0]["TxnId"] = "mutated"
    assert observed.source_evidence["Line"][0]["Amount"] == Decimal("12.3400")
    assert observed.lines[0].links[0].transaction_id == "invoice-1"
    with pytest.raises(FrozenInstanceError):
        observed.entity_id = "mutated"


def test_unapplied_payment_preserves_empty_lines_and_absent_date_currency():
    raw = payment(Line=[], UnappliedAmt="12.34")
    raw.pop("TxnDate")
    raw.pop("CurrencyRef")
    observed = observe_payment(raw, **identity())
    assert observed.lines == () and observed.transaction_date is None
    assert not observed.currency_ref_present and not observed.currency_ref_null
    assert "TxnDate" not in observed.present_fields
    assert observed.unapplied_amount == Decimal("12.34")


def test_payment_retains_ordered_multiple_lines_and_links_without_decisions():
    raw = payment(Line=[
        payment_line(Amount="2.00", LinkedTxn=[
            payment_link(TxnId="invoice-2"),
            payment_link(TxnId="credit-1", TxnType="CreditMemo")]),
        payment_line(Amount="10.34", LinkedTxn=[]),
    ])
    observed = observe_payment(raw, **identity())
    assert [line.amount for line in observed.lines] == [Decimal("2.00"), Decimal("10.34")]
    assert [link.transaction_id for link in observed.lines[0].links] == ["invoice-2", "credit-1"]
    assert observed.lines[1].links == ()
    forbidden = {"allocation", "allocated", "settled", "paid", "canonical",
                 "supported", "reconciled", "launch_ready"}
    assert forbidden.isdisjoint(observed.__dataclass_fields__)


def test_payment_absence_and_explicit_null_are_distinct():
    absent = payment(); absent.pop("TxnDate"); absent.pop("CurrencyRef")
    null = payment(TxnDate=None, CurrencyRef=None)
    a = observe_payment(absent, **identity())
    n = observe_payment(null, **identity())
    assert "TxnDate" not in a.present_fields and "TxnDate" not in a.null_fields
    assert "TxnDate" in n.present_fields and "TxnDate" in n.null_fields
    assert not a.currency_ref_present and not a.currency_ref_null
    assert n.currency_ref_present and n.currency_ref_null
    assert a.source_digest != n.source_digest


def test_payment_digest_preserves_type_scale_order_and_revision_identity():
    first = payment(future={"a": Decimal("1.0"), "b": "1.0"})
    reordered_object = dict(reversed(list(first.items())))
    assert observe_payment(first, **identity()).source_digest == observe_payment(
        reordered_object, **identity()).source_digest
    assert observe_payment(first, **identity()).source_digest != observe_payment(
        payment(future={"a": Decimal("1.00"), "b": "1.0"}), **identity()).source_digest
    assert observe_payment(first, **identity()).source_digest != observe_payment(
        payment(future={"a": "1.0", "b": "1.0"}), **identity()).source_digest
    assert observe_payment(first, **identity()).source_digest != observe_payment(
        payment(Line=list(reversed(first["Line"])) + [payment_line(Amount="0")]),
        **identity()).source_digest
    assert observe_payment(payment(SyncToken="9"), **identity()).sync_token == "9"


@pytest.mark.parametrize("field", ["Id", "SyncToken"])
@pytest.mark.parametrize("bad", [None, "", "  "])
def test_payment_required_identity_is_nonblank(field, bad):
    with pytest.raises(QuickBooksObservationError):
        observe_payment(payment(**{field: bad}), **identity())


@pytest.mark.parametrize("bad", [None, {}, {"value": None}, {"value": " "}])
def test_payment_customer_reference_is_required(bad):
    with pytest.raises(QuickBooksObservationError):
        observe_payment(payment(CustomerRef=bad), **identity())


@pytest.mark.parametrize("field,bad", [
    ("Line", None), ("Line", {}), ("Line", [payment_line()] * 751),
])
def test_payment_line_type_and_bounds_fail(field, bad):
    with pytest.raises(QuickBooksObservationError):
        observe_payment(payment(**{field: bad}), **identity())


@pytest.mark.parametrize("bad", [None, {}, [payment_link()] * 751])
def test_payment_link_type_and_bounds_fail(bad):
    with pytest.raises(QuickBooksObservationError):
        observe_payment(payment(Line=[payment_line(LinkedTxn=bad)]), **identity())


@pytest.mark.parametrize("raw_line", [None, [], DictSubclass()])
def test_payment_line_entries_must_be_plain_objects(raw_line):
    with pytest.raises(QuickBooksObservationError):
        observe_payment(payment(Line=[raw_line]), **identity())


@pytest.mark.parametrize("raw_link", [None, [], DictSubclass()])
def test_payment_link_entries_must_be_plain_objects(raw_link):
    with pytest.raises(QuickBooksObservationError):
        observe_payment(payment(Line=[payment_line(LinkedTxn=[raw_link])]), **identity())


@pytest.mark.parametrize("field,bad", [
    ("TxnId", None), ("TxnId", ""), ("TxnId", "  "),
    ("TxnType", None), ("TxnType", ""), ("TxnType", "  "),
])
def test_present_payment_link_identifiers_are_bounded_nonblank(field, bad):
    with pytest.raises(QuickBooksObservationError):
        observe_payment(payment(Line=[payment_line(
            LinkedTxn=[payment_link(**{field: bad})])]), **identity())


@pytest.mark.parametrize("field", ["TotalAmt", "UnappliedAmt"])
@pytest.mark.parametrize("bad", [True, 1.2, Decimal("NaN"), Decimal("Infinity"),
    Decimal("1e100"), Decimal("0.0000000000001"), "1e2", "NaN",
    "1000000000000000001", Decimal("-0.01")])
def test_payment_money_is_exact_bounded_and_nonnegative(field, bad):
    with pytest.raises(QuickBooksObservationError):
        observe_payment(payment(**{field: bad}), **identity())


@pytest.mark.parametrize("bad", [True, 1.2, "1e2", Decimal("-0.01")])
def test_payment_line_amount_is_exact_and_nonnegative(bad):
    with pytest.raises(QuickBooksObservationError):
        observe_payment(payment(Line=[payment_line(Amount=bad)]), **identity())


def test_payment_rejects_bad_dates_timestamps_graphs_binding_and_disclosure():
    secret = "sensitive-customer@example.invalid"
    cases = [
        (payment(TxnDate="2026-02-29"), identity()),
        (payment(MetaData={"CreateTime": "2026-01-01"}), identity()),
        (payment(future=DictSubclass()), identity()),
        (payment(future=b"private"), identity()),
        (payment(future={1: secret}), identity()),
        (payment(), identity(realm_id=secret)),
    ]
    for raw, bound_identity in cases:
        with pytest.raises(QuickBooksObservationError) as caught:
            observe_payment(raw, **bound_identity)
        assert secret not in str(caught.value) and secret not in repr(caught.value)
    observed = observe_payment(payment(CustomerRef={"value": secret}), **identity())
    assert secret not in repr(observed)
    assert secret not in repr(observed.lines[0])
    assert secret not in repr(observed.lines[0].links[0])
    assert secret not in repr(observed.source_evidence)
