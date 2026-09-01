"""Synthetic, network-free FreeAgent company / invoice-list / pagination tests."""

from decimal import Decimal
from urllib.parse import urlsplit, urlunsplit

import pytest

from reserved.providers.accounting.freeagent_invoice_contract import (
    COMPANY_ENDPOINT,
    COMPANY_INFERRED_REQUIRED_FIELDS,
    COMPANY_TYPES,
    FREEAGENT_API_BASE_URL,
    FREEAGENT_API_VERSION,
    INVOICES_ENDPOINT,
    INVOICE_EC_STATUSES,
    INVOICE_LIST_URL_IDENTITY_INFERENCE,
    INVOICE_REQUIRED_FIELDS,
    INVOICE_STATUSES,
    PAGINATION_DEFAULT_PER_PAGE,
    PAGINATION_LINK_RELATIONS,
    PAGINATION_MAX_PER_PAGE,
    FreeAgentCompanyRecord,
    FreeAgentInvoiceRecord,
    FreeAgentPagination,
    parse_company,
    parse_invoice_list,
    parse_link_header,
    validate_pagination,
)


def _invoice(**overrides):
    invoice = {
        "url": "https://api.freeagent.com/v2/invoices/1",
        "contact": "https://api.freeagent.com/v2/contacts/2",
        "dated_on": "2011-08-29",
        "due_on": "2011-09-28",
        "payment_terms_in_days": 30,
        "currency": "GBP",
        "status": "Open",
        "reference": "001",
        "net_value": "0.0",
        "sales_tax_value": "0.0",
        "total_value": "200.0",
        "paid_value": "50.0",
        "due_value": "150.0",
        "exchange_rate": "1.0",
        "omit_header": False,
        "created_at": "2011-08-29T00:00:00Z",
        "updated_at": "2011-08-29T00:00:00Z",
    }
    invoice.update(overrides)
    return invoice


def _invoice_list(*invoices):
    return {"invoices": list(invoices)}


def _company(**overrides):
    company = {
        "type": "UkLimitedCompany",
        "currency": "GBP",
        "id": "12345",
        "name": "My Company",
        "subdomain": "mycompany",
        "url": "https://api.freeagent.com/v2/company",
    }
    company.update(overrides)
    return {"company": company}


def _mutate_url(url, *, scheme=None, netloc=None, fragment=None):
    parts = urlsplit(url)
    if scheme is not None:
        parts = parts._replace(scheme=scheme)
    if netloc is not None:
        parts = parts._replace(netloc=netloc)
    if fragment is not None:
        parts = parts._replace(fragment=fragment)
    return urlunsplit(parts)


# ── Exact origins and documented enumerations ────────────────────────────────


def test_endpoints_are_exact_reviewed_origins():
    assert FREEAGENT_API_BASE_URL == "https://api.freeagent.com"
    assert FREEAGENT_API_VERSION == "v2"
    assert COMPANY_ENDPOINT == "https://api.freeagent.com/v2/company"
    assert INVOICES_ENDPOINT == "https://api.freeagent.com/v2/invoices"


def test_pagination_constants_match_documented_limits():
    assert PAGINATION_DEFAULT_PER_PAGE == 25
    assert PAGINATION_MAX_PER_PAGE == 100
    assert PAGINATION_LINK_RELATIONS == {"prev", "next", "first", "last"}


def test_invoice_statuses_are_exact_documented_set():
    assert INVOICE_STATUSES == {
        "Draft",
        "Scheduled To Email",
        "Open",
        "Zero Value",
        "Overdue",
        "Paid",
        "Overpaid",
        "Refunded",
        "Written-off",
        "Part written-off",
    }


def test_invoice_ec_statuses_are_exact_documented_set():
    assert INVOICE_EC_STATUSES == {"UK/Non-EC", "EC Goods", "EC Services", "Reverse Charge", "EC VAT MOSS"}


def test_company_types_are_exact_documented_set():
    assert COMPANY_TYPES == {
        "UkLimitedCompany",
        "UkLimitedLiabilityPartnership",
        "UkPartnership",
        "UkSoleTrader",
        "UkUnincorporatedLandlord",
        "UsLimitedLiabilityCompany",
        "UsPartnership",
        "UsSoleProprietor",
        "UsCCorp",
        "UsSCorp",
        "UniversalCompany",
    }


# ── Truthful inference labelling ─────────────────────────────────────────────


def test_url_identity_required_is_inference_not_documented_required():
    assert "url" not in INVOICE_REQUIRED_FIELDS
    assert INVOICE_LIST_URL_IDENTITY_INFERENCE == "required-and-unique"


def test_company_type_currency_required_are_fail_closed_inference():
    assert COMPANY_INFERRED_REQUIRED_FIELDS == {"type", "currency"}


# ── Company contract ─────────────────────────────────────────────────────────


def test_company_envelope_and_required_fields_are_validated():
    record = parse_company(_company())
    assert isinstance(record, FreeAgentCompanyRecord)
    assert record.type == "UkLimitedCompany"
    assert record.currency == "GBP"
    assert record.id == "12345"
    assert record.name == "My Company"
    assert record.subdomain == "mycompany"
    assert record.url == "https://api.freeagent.com/v2/company"


def test_company_id_is_preserved_as_string_or_integer_without_coercion():
    assert parse_company(_company(id="12345")).id == "12345"
    assert parse_company(_company(id=12345)).id == 12345


@pytest.mark.parametrize("payload", [
    {"company": []},
    "not-a-mapping",
])
def test_company_rejects_non_object_envelope(payload):
    with pytest.raises(ValueError):
        parse_company(payload)


def test_company_rejects_missing_envelope_key():
    with pytest.raises(ValueError):
        parse_company({})


@pytest.mark.parametrize("missing", ["type", "currency"])
def test_company_rejects_missing_required_fields(missing):
    company = _company()
    del company["company"][missing]
    with pytest.raises(ValueError):
        parse_company(company)


def test_company_rejects_undocumented_type():
    with pytest.raises(ValueError):
        parse_company(_company(type="NotARealCompanyType"))


@pytest.mark.parametrize("bad", [{"type": 1}, {"currency": ""}, {"currency": 5}])
def test_company_rejects_wrong_field_types(bad):
    with pytest.raises(ValueError):
        parse_company(_company(**bad))


@pytest.mark.parametrize("bad_id", [True, 1.5, [], {}])
def test_company_rejects_unusable_id_type(bad_id):
    with pytest.raises(ValueError):
        parse_company(_company(id=bad_id))


def test_company_rejects_non_uri_url_when_present():
    with pytest.raises(ValueError):
        parse_company(_company(url="not-a-uri"))


def test_company_records_additive_schema_drift_without_meaning():
    record = parse_company(_company(
        sales_tax_registration_status="Registered",
        some_future_field="present",
    ))
    assert "sales_tax_registration_status" in record.unknown_fields
    assert "some_future_field" in record.unknown_fields


def test_company_distinguishes_absent_from_null_optional_fields():
    no_name = _company()
    del no_name["company"]["name"]
    absent = parse_company(no_name)
    assert "name" in absent.absent_fields
    assert "name" not in absent.null_fields
    assert absent.name is None

    nulled = parse_company(_company(name=None))
    assert "name" in nulled.null_fields
    assert "name" not in nulled.absent_fields
    assert nulled.name is None


@pytest.mark.parametrize("bad_url", [
    "http://api.freeagent.com/v2/company",
    "https://evil.example.com/v2/company",
    "https://user:pass@api.freeagent.com/v2/company",
    "https://api.freeagent.com/v2/company#frag",
    "https://api.freeagent.com:8443/v2/company",
    "https://api.freeagent.com/v2/invoices",
])
def test_company_url_rejects_bad_targets(bad_url):
    with pytest.raises(ValueError):
        parse_company(_company(url=bad_url))


@pytest.mark.parametrize("port", [":", ":not-a-port"])
def test_company_url_rejects_malformed_explicit_port(port):
    with pytest.raises(ValueError):
        parse_company(_company(url=f"https://api.freeagent.com{port}/v2/company"))


@pytest.mark.parametrize("url", [
    "https://api.freeagent.com/v2/company",
    "https://api.freeagent.com:443/v2/company",
])
def test_company_url_preserves_no_port_and_explicit_https_port(url):
    assert parse_company(_company(url=url)).url == url


# ── Invoice list contract ────────────────────────────────────────────────────


def test_invoice_list_validates_documented_example_shape():
    records = parse_invoice_list(_invoice_list(_invoice()))
    assert len(records) == 1
    record = records[0]
    assert isinstance(record, FreeAgentInvoiceRecord)
    assert record.url == "https://api.freeagent.com/v2/invoices/1"
    assert record.contact == "https://api.freeagent.com/v2/contacts/2"
    assert record.dated_on == "2011-08-29"
    assert record.due_on == "2011-09-28"
    assert record.payment_terms_in_days == 30
    assert record.status == "Open"
    assert record.total_value == Decimal("200.0")
    assert record.paid_value == Decimal("50.0")
    assert record.due_value == Decimal("150.0")


def test_invoice_list_rejects_non_object_envelope():
    with pytest.raises(ValueError):
        parse_invoice_list({"invoices": {}})


def test_invoice_list_rejects_missing_envelope_key():
    with pytest.raises(ValueError):
        parse_invoice_list({})


@pytest.mark.parametrize("missing", ["contact", "dated_on", "payment_terms_in_days"])
def test_invoice_rejects_missing_required_fields(missing):
    invoice = _invoice()
    del invoice[missing]
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(invoice))


@pytest.mark.parametrize("field", ["contact", "dated_on", "payment_terms_in_days"])
def test_invoice_rejects_null_required_fields(field):
    invoice = _invoice()
    invoice[field] = None
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(invoice))


def test_invoice_rejects_non_uri_contact():
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(contact="not-a-uri")))


@pytest.mark.parametrize("bad_date", ["29/08/2011", "2011-8-29", "2011-02-30", "not-a-date"])
def test_invoice_rejects_invalid_dated_on(bad_date):
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(dated_on=bad_date)))


@pytest.mark.parametrize("bad_terms", ["30", 30.0, True, None])
def test_invoice_rejects_wrong_payment_terms_type(bad_terms):
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(payment_terms_in_days=bad_terms)))


def test_invoice_rejects_undocumented_status():
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(status="SuperPaid")))


def test_invoice_rejects_undocumented_ec_status():
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(ec_status="NotAnECStatus")))


@pytest.mark.parametrize("amount_field", ["total_value", "paid_value", "due_value", "net_value", "sales_tax_value", "exchange_rate"])
def test_invoice_rejects_non_string_amount(amount_field):
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(**{amount_field: 200.0})))


@pytest.mark.parametrize("bad_amount", ["NaN", "Infinity", "-Infinity", "abc", ""])
def test_invoice_rejects_non_finite_or_malformed_amount(bad_amount):
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(total_value=bad_amount)))


def test_invoice_preserves_zero_amount_distinct_from_missing_and_null():
    zero = parse_invoice_list(_invoice_list(_invoice(total_value="0.0")))[0]
    assert zero.total_value == Decimal("0.0")
    assert "total_value" not in zero.null_fields

    no_total = _invoice()
    del no_total["total_value"]
    missing = parse_invoice_list(_invoice_list(no_total))[0]
    assert "total_value" in missing.absent_fields
    assert missing.total_value is None

    nulled = parse_invoice_list(_invoice_list(_invoice(total_value=None)))[0]
    assert "total_value" in nulled.null_fields
    assert nulled.total_value is None


def test_invoice_rejects_wrong_boolean_type():
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(omit_header="false")))


def test_invoice_list_rejects_duplicate_url_identity():
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(), _invoice(url="https://api.freeagent.com/v2/invoices/1")))


def test_invoice_list_rejects_missing_url_identity():
    invoice = _invoice()
    del invoice["url"]
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(invoice))


def test_invoice_records_additive_schema_drift_without_meaning():
    record = parse_invoice_list(_invoice_list(_invoice(some_future_field="present")))[0]
    assert "some_future_field" in record.unknown_fields


# ── Exact FreeAgent API-origin validation ────────────────────────────────────

IDENTITY_FIELDS = [
    ("url", "https://api.freeagent.com/v2/invoices/1"),
    ("contact", "https://api.freeagent.com/v2/contacts/2"),
    ("project", "https://api.freeagent.com/v2/projects/3"),
    ("property", "https://api.freeagent.com/v2/properties/4"),
    ("bank_account", "https://api.freeagent.com/v2/bank_accounts/1"),
    ("recurring_invoice", "https://api.freeagent.com/v2/recurring_invoices/5"),
]


@pytest.mark.parametrize("field,good", IDENTITY_FIELDS)
@pytest.mark.parametrize("mutation", [
    pytest.param(lambda u: _mutate_url(u, scheme="http"), id="http"),
    pytest.param(lambda u: _mutate_url(u, netloc="evil.example.com"), id="cross-origin"),
    pytest.param(lambda u: _mutate_url(u, netloc="user:pass@api.freeagent.com"), id="userinfo"),
    pytest.param(lambda u: _mutate_url(u, fragment="frag"), id="fragment"),
    pytest.param(lambda u: _mutate_url(u, netloc="api.freeagent.com:8443"), id="non-default-port"),
])
def test_identity_urls_reject_transport_flaws(field, good, mutation):
    target = mutation(good)
    assert target != good  # the mutation must actually alter the target URL
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(**{field: target})))


@pytest.mark.parametrize("field,good", IDENTITY_FIELDS)
@pytest.mark.parametrize("port", [":", ":not-a-port"])
def test_identity_urls_reject_malformed_explicit_ports(field, good, port):
    target = _mutate_url(good, netloc=f"api.freeagent.com{port}")
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(**{field: target})))


@pytest.mark.parametrize("field,good", IDENTITY_FIELDS)
def test_identity_urls_accept_explicit_https_port(field, good):
    target = _mutate_url(good, netloc="api.freeagent.com:443")
    record = parse_invoice_list(_invoice_list(_invoice(**{field: target})))[0]
    if field in {"url", "contact"}:
        assert getattr(record, field) == target
    assert field not in record.unknown_fields


@pytest.mark.parametrize("field,url", [
    ("url", "https://api.freeagent.com/v2/contacts/1"),
    ("contact", "https://api.freeagent.com/v2/invoices/1"),
    ("project", "https://api.freeagent.com/v2/invoices/1"),
    ("property", "https://api.freeagent.com/v2/invoices/1"),
    ("bank_account", "https://api.freeagent.com/v2/invoices/1"),
    ("recurring_invoice", "https://api.freeagent.com/v2/invoices/1"),
])
def test_identity_urls_reject_wrong_resource_path(field, url):
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(**{field: url})))


@pytest.mark.parametrize("field", [f for f, _ in IDENTITY_FIELDS])
def test_identity_urls_reject_collection_path_without_id(field):
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(**{field: "https://api.freeagent.com/v2/invoices"})))


def test_external_https_payment_url_is_not_rejected():
    record = parse_invoice_list(_invoice_list(
        _invoice(payment_url="https://payments.paypal.com/checkout/abc")
    ))[0]
    assert "payment_url" not in record.absent_fields
    assert "payment_url" not in record.unknown_fields


def test_http_payment_url_is_rejected():
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(payment_url="http://paypal.com/checkout")))


def test_credential_bearing_payment_url_is_rejected():
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(
            _invoice(payment_url="https://user:pass@paypal.com/checkout")
        ))


@pytest.mark.parametrize("port", [":", ":not-a-port"])
def test_payment_url_rejects_malformed_explicit_port(port):
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(
            _invoice(payment_url=f"https://payments.example.com{port}/checkout")
        ))


@pytest.mark.parametrize("url", [
    "https://payments.example.com/checkout",
    "https://payments.example.com:8443/checkout",
])
def test_payment_url_preserves_no_port_and_valid_numeric_port(url):
    record = parse_invoice_list(_invoice_list(_invoice(payment_url=url)))[0]
    assert "payment_url" not in record.absent_fields


# ── Schema validation for previously-unvalidated documented fields ───────────


def test_company_string_field_rejects_non_string():
    with pytest.raises(ValueError):
        parse_company(_company(address1=123))


def test_company_date_field_rejects_non_date():
    with pytest.raises(ValueError):
        parse_company(_company(company_start_date="not-a-date"))


def test_company_boolean_field_rejects_non_boolean():
    with pytest.raises(ValueError):
        parse_company(_company(sales_tax_is_value_added="yes"))


def test_company_array_field_rejects_non_array():
    with pytest.raises(ValueError):
        parse_company(_company(annual_accounting_periods="x"))


def test_company_enum_field_rejects_undocumented_value():
    with pytest.raises(ValueError):
        parse_company(_company(mileage_units="parsecs"))


def test_invoice_string_field_rejects_non_string():
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(comments=123)))


def test_invoice_hash_field_rejects_non_mapping():
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(payment_methods="x")))


def test_invoice_array_field_rejects_non_array():
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(invoice_items="x")))


def test_invoice_include_enum_rejects_undocumented_value():
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(include_timeslips="nonsense")))


def test_invoice_cis_rate_rejects_non_string():
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(cis_rate=123)))


# ── Nullable enums accept null only where documented ─────────────────────────


def test_nullable_include_enum_accepts_null():
    record = parse_invoice_list(_invoice_list(_invoice(include_timeslips=None)))[0]
    assert "include_timeslips" in record.null_fields


def test_nullable_cis_rate_accepts_null():
    record = parse_invoice_list(_invoice_list(_invoice(cis_rate=None)))[0]
    assert "cis_rate" in record.null_fields


@pytest.mark.parametrize("field", ["status", "ec_status"])
def test_non_nullable_enum_rejects_null(field):
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(**{field: None})))


# ── Documented payment-method boolean values ─────────────────────────────────


def test_payment_methods_documented_booleans_are_accepted():
    parse_invoice_list(_invoice_list(_invoice(payment_methods={"paypal": True, "stripe": False})))


def test_payment_methods_reject_non_boolean_documented_key():
    with pytest.raises(ValueError):
        parse_invoice_list(_invoice_list(_invoice(payment_methods={"paypal": "yes"})))


def test_payment_methods_ignore_unknown_additive_keys():
    parse_invoice_list(_invoice_list(
        _invoice(payment_methods={"paypal": True, "future_method": "x"})
    ))


# ── Pagination contract ──────────────────────────────────────────────────────


DOCUMENTED_LINK = (
    '<https://api.freeagent.com/v2/invoices?page=4&per_page=50>; rel="prev", '
    '<https://api.freeagent.com/v2/invoices?page=6&per_page=50>; rel="next", '
    '<https://api.freeagent.com/v2/invoices?page=1&per_page=50>; rel="first", '
    '<https://api.freeagent.com/v2/invoices?page=10&per_page=50>; rel="last"'
)


def test_link_header_parses_documented_relations():
    links = parse_link_header(DOCUMENTED_LINK)
    assert links == {
        "prev": "https://api.freeagent.com/v2/invoices?page=4&per_page=50",
        "next": "https://api.freeagent.com/v2/invoices?page=6&per_page=50",
        "first": "https://api.freeagent.com/v2/invoices?page=1&per_page=50",
        "last": "https://api.freeagent.com/v2/invoices?page=10&per_page=50",
    }


@pytest.mark.parametrize("header", [
    '<https://api.freeagent.com/v2/invoices?page=2>; rel="up"',
    '<https://api.freeagent.com/v2/invoices?page=2>; rel="next", <https://api.freeagent.com/v2/invoices?page=2>; rel="next"',
    "not-a-link-header",
    "",
])
def test_link_header_fails_closed_on_undocumented_or_malformed(header):
    with pytest.raises(ValueError):
        parse_link_header(header)


@pytest.mark.parametrize("bad_link", [
    '<http://api.freeagent.com/v2/invoices?page=2>; rel="next"',
    '<https://evil.example.com/v2/invoices?page=2>; rel="next"',
    '<https://user:pass@api.freeagent.com/v2/invoices?page=2>; rel="next"',
    '<https://api.freeagent.com/v2/invoices?page=2#frag>; rel="next"',
    '<https://api.freeagent.com:8443/v2/invoices?page=2>; rel="next"',
    '<https://api.freeagent.com/v2/contacts?page=2>; rel="next"',
])
def test_pagination_link_rejects_bad_targets(bad_link):
    with pytest.raises(ValueError):
        parse_link_header(bad_link)


@pytest.mark.parametrize("port", [":", ":not-a-port"])
def test_pagination_link_rejects_malformed_explicit_port(port):
    with pytest.raises(ValueError):
        parse_link_header(
            f'<https://api.freeagent.com{port}/v2/invoices?page=2>; rel="next"'
        )


@pytest.mark.parametrize("url", [
    "https://api.freeagent.com/v2/invoices?page=2",
    "https://api.freeagent.com:443/v2/invoices?page=2",
])
def test_pagination_link_preserves_no_port_and_explicit_https_port(url):
    assert parse_link_header(f'<{url}>; rel="next"') == {"next": url}


def test_pagination_validates_documented_shape_and_terminal_page():
    pagination = validate_pagination(
        page=5,
        per_page=50,
        link_header=DOCUMENTED_LINK,
        total_count="26",
    )
    assert isinstance(pagination, FreeAgentPagination)
    assert pagination.page == 5
    assert pagination.per_page == 50
    assert pagination.total_count == 26
    assert pagination.next_url == "https://api.freeagent.com/v2/invoices?page=6&per_page=50"
    assert pagination.last_url == "https://api.freeagent.com/v2/invoices?page=10&per_page=50"


def test_pagination_terminal_page_has_no_next_url():
    pagination = validate_pagination(link_header='<https://api.freeagent.com/v2/invoices?page=1>; rel="first"')
    assert pagination.next_url is None


@pytest.mark.parametrize("kwargs", [
    {"per_page": 101},
    {"per_page": 0},
    {"page": 0},
    {"page": -1},
    {"total_count": -1},
])
def test_pagination_rejects_out_of_range_values(kwargs):
    with pytest.raises(ValueError):
        validate_pagination(**kwargs)


def test_pagination_rejects_wrong_types():
    with pytest.raises(ValueError):
        validate_pagination(per_page="fifty")
    with pytest.raises(ValueError):
        validate_pagination(total_count=True)


def test_module_contains_no_http_client_or_credentials():
    import reserved.providers.accounting.freeagent_invoice_contract as contract

    assert not hasattr(contract, "requests")
    assert not hasattr(contract, "httpx")
    assert not hasattr(contract, "urlopen")
