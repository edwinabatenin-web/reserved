"""Network-inert FreeAgent company, invoice-list and pagination source contracts.

This module only validates the retained, documented read-only response shapes.
It owns no HTTP client, credentials, token storage, persistence,
adapter-enablement path or canonical tax decision. Amount fields keep their
documented FreeAgent names and meanings; nothing here is mapped into canonical
tax, VAT, payment or outstanding semantics.

Every field this module treats as documented/known is validated against its
documented wire kind or, where the official documentation publishes a closed
set, its exact documented enum. Unknown additive fields are preserved for
review without being assigned any meaning.

Authority observed 2026-09-01:
https://dev.freeagent.com/docs/introduction
https://dev.freeagent.com/docs/invoices
https://dev.freeagent.com/docs/company
https://dev.freeagent.com/docs/quick_start
https://dev.freeagent.com/docs/versioning

See docs/FREEAGENT_INVOICE_CONTRACT_EVIDENCE.md for the exact documented facts,
the documented-fact/inference split and the recorded evidence gaps.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import partial
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

FREEAGENT_API_BASE_URL = "https://api.freeagent.com"
FREEAGENT_API_VERSION = "v2"
COMPANY_ENDPOINT = f"{FREEAGENT_API_BASE_URL}/{FREEAGENT_API_VERSION}/company"
INVOICES_ENDPOINT = f"{FREEAGENT_API_BASE_URL}/{FREEAGENT_API_VERSION}/invoices"

PAGINATION_DEFAULT_PER_PAGE = 25
PAGINATION_MAX_PER_PAGE = 100
PAGINATION_LINK_RELATIONS = frozenset({"prev", "next", "first", "last"})

INVOICE_STATUSES = frozenset({
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
})

INVOICE_EC_STATUSES = frozenset({
    "UK/Non-EC",
    "EC Goods",
    "EC Services",
    "Reverse Charge",
    "EC VAT MOSS",
})

COMPANY_TYPES = frozenset({
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
})

# Exact documented closed sets for company String fields that are not ``type``.
MILEAGE_UNITS = frozenset({"miles", "kilometers"})
SHORT_DATE_FORMATS = frozenset({"dd mmm yy", "dd-mm-yyyy", "mm/dd/yyyy", "yyyy-mm-dd"})
INITIAL_VAT_BASIS = frozenset({"Invoice", "Cash"})

# Exact documented closed sets for invoice ``include_*`` String fields. The
# documentation lists ``null`` alongside these values, so ``null`` is accepted
# for these three fields only.
INVOICE_INCLUDE_TIMESLIPS = frozenset({
    "billed_grouped_by_single_timeslip",
    "billed_grouped_by_timeslip",
    "billed_grouped_by_timeslip_task",
    "billed_grouped_by_timeslip_date",
})
INVOICE_INCLUDE_EXPENSES = frozenset({
    "billed_grouped_by_single_expense",
    "billed_grouped_by_expense",
})
INVOICE_INCLUDE_ESTIMATES = frozenset({
    "billed_grouped_by_single_estimate",
    "billed_grouped_by_estimate",
})

# Documented payment-method keys (all Kind Boolean). Unknown additive keys in a
# ``payment_methods`` hash are preserved/ignored and never acquire semantics.
PAYMENT_METHOD_BOOLEAN_KEYS = frozenset({
    "paypal",
    "gocardless_preauth",
    "gocardless_instant_bank_pay",
    "stripe",
    "tyl",
})

# Documented "Required" column for the invoice attribute table.
INVOICE_REQUIRED_FIELDS = frozenset({"contact", "dated_on", "payment_terms_in_days"})

# FA-S1 fail-closed inference (NOT a documented "Required" marker). The company
# attribute table has no Required column, but ``type`` and ``currency`` appear in
# both documented examples and are necessary to interpret invoice amounts, so
# this validator requires them locally.
COMPANY_INFERRED_REQUIRED_FIELDS = frozenset({"type", "currency"})

# FA-S1 fail-closed inference (NOT a documented "Required" marker). The invoice
# attribute table documents ``url`` as "the unique identifier for the invoice";
# this validator therefore requires a unique ``url`` in the list context to
# avoid silently overwriting identities under unstable pagination.
INVOICE_LIST_URL_IDENTITY_INFERENCE = "required-and-unique"

# Attribute-table field universe. ``sales_tax_registration_status`` is
# deliberately absent from the company universe: it appears in the documented
# response examples but is not present in the company attribute table, so this
# module records it as additive schema drift rather than assigning it meaning.
COMPANY_DOCUMENTED_FIELDS = frozenset({
    "url", "id", "name", "subdomain", "type", "currency", "mileage_units",
    "company_start_date", "trading_start_date", "first_accounting_year_end",
    "annual_accounting_periods", "freeagent_start_date", "address1", "address2",
    "address3", "town", "region", "postcode", "country",
    "company_registration_number", "contact_email", "contact_phone", "website",
    "business_type", "business_category", "short_date_format",
    "sales_tax_name", "sales_tax_registration_number",
    "sales_tax_effective_date", "sales_tax_rates", "sales_tax_is_value_added",
    "cis_enabled", "cis_subcontractor", "cis_contractor", "locked_attributes",
    "created_at", "updated_at",
    "vat_first_return_period_ends_on", "initial_vat_basis",
    "initially_on_frs", "initial_vat_frs_type",
    "sales_tax_deregistration_effective_date",
    "second_sales_tax_name", "second_sales_tax_rates",
    "second_sales_tax_is_compound",
})

INVOICE_DOCUMENTED_FIELDS = frozenset({
    "url", "status", "long_status", "contact", "project", "property",
    "include_timeslips", "include_expenses", "include_estimates", "reference",
    "dated_on", "due_on", "payment_terms_in_days", "currency", "cis_rate",
    "cis_deduction_rate", "cis_deduction", "cis_deduction_suffered", "comments",
    "send_new_invoice_emails", "send_reminder_emails", "send_thank_you_emails",
    "discount_percent", "contact_name", "client_contact_name", "payment_terms",
    "po_reference", "bank_account", "omit_header", "show_project_name",
    "always_show_bic_and_iban", "ec_status", "place_of_supply", "net_value",
    "exchange_rate", "involves_sales_tax", "sales_tax_value",
    "second_sales_tax_value", "total_value", "paid_value", "due_value",
    "is_interim_uk_vat", "paid_on", "written_off_date", "recurring_invoice",
    "payment_url", "payment_methods", "invoice_items", "created_at", "updated_at",
})

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_LINK_VALUE_RE = re.compile(r'<([^>]+)>\s*;\s*rel="([^"]+)"')


@dataclass(frozen=True)
class FreeAgentCompanyRecord:
    """Validated facts from a documented ``GET /v2/company`` response.

    ``id`` is retained as ``str | int`` rather than a single coerced type
    because the attribute table declares Kind ``Integer`` while the JSON
    example shows ``"id":"12345"``. The value is preserved exactly.
    """

    type: str
    currency: str
    id: str | int | None = None
    name: str | None = None
    subdomain: str | None = None
    url: str | None = None
    absent_fields: frozenset[str] = frozenset()
    null_fields: frozenset[str] = frozenset()
    unknown_fields: frozenset[str] = frozenset()


@dataclass(frozen=True)
class FreeAgentInvoiceRecord:
    """Validated facts from one element of ``GET /v2/invoices``.

    Amount attributes carry the provider's documented names and meanings and
    are never reinterpreted. ``None`` for an optional field means absent or
    explicit null; ``absent_fields`` and ``null_fields`` disambiguate the two,
    so missing, null and zero (``Decimal("0.0")``) remain distinct.
    """

    contact: str
    dated_on: str
    payment_terms_in_days: int
    url: str | None = None
    status: str | None = None
    reference: str | None = None
    due_on: str | None = None
    currency: str | None = None
    long_status: str | None = None
    ec_status: str | None = None
    contact_name: str | None = None
    net_value: Decimal | None = None
    sales_tax_value: Decimal | None = None
    second_sales_tax_value: Decimal | None = None
    total_value: Decimal | None = None
    paid_value: Decimal | None = None
    due_value: Decimal | None = None
    exchange_rate: Decimal | None = None
    discount_percent: Decimal | None = None
    cis_deduction_rate: Decimal | None = None
    cis_deduction: Decimal | None = None
    cis_deduction_suffered: Decimal | None = None
    created_at: str | None = None
    updated_at: str | None = None
    absent_fields: frozenset[str] = frozenset()
    null_fields: frozenset[str] = frozenset()
    unknown_fields: frozenset[str] = frozenset()


@dataclass(frozen=True)
class FreeAgentPagination:
    """Validated pagination metadata from the documented ``Link`` header and
    ``X-Total-Count`` header. Absence of ``next_url`` marks a terminal page."""

    page: int | None
    per_page: int | None
    next_url: str | None
    prev_url: str | None
    first_url: str | None
    last_url: str | None
    total_count: int | None


# ── Kind validators ──────────────────────────────────────────────────────────


def _parse_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"FreeAgent {field} must be a non-empty string")
    return value


def _parse_date_string(value: Any, field: str) -> str:
    text = _parse_nonempty_string(value, field)
    if not _DATE_RE.match(text):
        raise ValueError(f"FreeAgent {field} must be a date in YYYY-MM-DD format")
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"FreeAgent {field} is not a valid calendar date") from exc
    return text


def _parse_integer(value: Any, field: str) -> int:
    if isinstance(value, bool) or type(value) is not int:
        raise ValueError(f"FreeAgent {field} must be an integer")
    return value


def _parse_boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"FreeAgent {field} must be a boolean")
    return value


def _parse_decimal_string(value: Any, field: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError(f"FreeAgent {field} must be a JSON string (decimal)")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"FreeAgent {field} is not a valid decimal string") from exc
    if not parsed.is_finite():
        raise ValueError(f"FreeAgent {field} must be a finite decimal")
    return parsed


def _parse_enum(value: Any, field: str, allowed: frozenset[str]) -> str:
    text = _parse_nonempty_string(value, field)
    if text not in allowed:
        raise ValueError(f"FreeAgent {field} value {text!r} is not documented")
    return text


def _parse_nullable_enum(value: Any, field: str, allowed: frozenset[str]) -> str | None:
    """Accept ``null`` only for fields whose documented closed set lists it."""
    if value is None:
        return None
    return _parse_enum(value, field, allowed)


def _parse_nullable_string(value: Any, field: str) -> str | None:
    """``cis_rate`` is documented as ``String | null``."""
    if value is None:
        return None
    return _parse_nonempty_string(value, field)


def _parse_company_id(value: Any, field: str) -> str | int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"FreeAgent {field} must be an integer or string")
    if isinstance(value, int) or (isinstance(value, str) and value.strip()):
        return value
    raise ValueError(f"FreeAgent {field} must be an integer or string")


def _require_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"FreeAgent {field} must be a JSON array")
    return value


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"FreeAgent {field} must be a JSON object")
    return value


def _parse_payment_methods(value: Any, field: str) -> Mapping[str, Any] | None:
    """Validate a documented ``payment_methods`` hash.

    Documented method keys, when present, must be booleans. Unknown additive
    method keys are preserved/ignored and never acquire semantics.
    """
    if value is None:
        return None
    mapping = _require_mapping(value, field)
    for key, val in mapping.items():
        if key in PAYMENT_METHOD_BOOLEAN_KEYS and not isinstance(val, bool):
            raise ValueError(f"FreeAgent {field}.{key} must be a boolean")
    return mapping


# ── URI / origin validators ──────────────────────────────────────────────────


def _parse_explicit_port(parsed, field: str) -> int | None:
    """Reject malformed or explicitly empty authority ports."""
    authority = parsed.netloc.rsplit("@", 1)[-1]
    if authority.endswith(":"):
        raise ValueError(f"FreeAgent {field} must not contain an empty port")
    try:
        return parsed.port
    except ValueError as exc:
        raise ValueError(f"FreeAgent {field} must contain a valid numeric port") from exc


def _require_freeagent_origin(parsed, field: str) -> None:
    """Require the exact documented HTTPS FreeAgent origin for API resources."""
    if parsed.scheme != "https":
        raise ValueError(f"FreeAgent {field} must use the https scheme")
    if parsed.hostname != "api.freeagent.com":
        raise ValueError(f"FreeAgent {field} must target api.freeagent.com")
    if _parse_explicit_port(parsed, field) not in (None, 443):
        raise ValueError(f"FreeAgent {field} must not use a non-default port")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"FreeAgent {field} must not contain userinfo/credentials")
    if parsed.fragment:
        raise ValueError(f"FreeAgent {field} must not contain a fragment")


def _parse_freeagent_item_uri(value: Any, field: str, resource: str) -> str:
    """Validate a FreeAgent API resource identity URI (``/v2/{resource}/{id}``)."""
    text = _parse_nonempty_string(value, field)
    parsed = urlparse(text)
    _require_freeagent_origin(parsed, field)
    prefix = f"/{FREEAGENT_API_VERSION}/{resource}/"
    path = parsed.path
    if not path.startswith(prefix):
        raise ValueError(f"FreeAgent {field} must target a /v2/{resource} resource path")
    remainder = path[len(prefix):].rstrip("/")
    if not remainder or "/" in remainder:
        raise ValueError(f"FreeAgent {field} must identify a single /v2/{resource} resource")
    return text


def _parse_freeagent_company_uri(value: Any, field: str) -> str:
    text = _parse_nonempty_string(value, field)
    parsed = urlparse(text)
    _require_freeagent_origin(parsed, field)
    if parsed.path.rstrip("/") != f"/{FREEAGENT_API_VERSION}/company":
        raise ValueError(f"FreeAgent {field} must target the /v2/company resource")
    return text


def _parse_freeagent_pagination_uri(value: Any, field: str) -> str:
    """Validate a pagination ``Link`` target without constructing its URL.

    The raw URL (including its query string) is preserved verbatim.
    """
    text = _parse_nonempty_string(value, field)
    parsed = urlparse(text)
    _require_freeagent_origin(parsed, field)
    if parsed.path.rstrip("/") != f"/{FREEAGENT_API_VERSION}/invoices":
        raise ValueError(f"FreeAgent {field} must target the /v2/invoices collection")
    return text


def _parse_safe_https_uri(value: Any, field: str) -> str:
    """Validate an external URI such as the online ``payment_url``.

    These may legitimately point outside ``api.freeagent.com``, so no
    FreeAgent-origin requirement is invented; only a safe absolute HTTPS URI
    with no embedded credentials is required.
    """
    text = _parse_nonempty_string(value, field)
    parsed = urlparse(text)
    if parsed.scheme != "https":
        raise ValueError(f"FreeAgent {field} must be an absolute HTTPS URI")
    if not parsed.hostname:
        raise ValueError(f"FreeAgent {field} must be an absolute HTTPS URI with a host")
    _parse_explicit_port(parsed, field)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"FreeAgent {field} must not contain userinfo/credentials")
    return text


# ── Schema layer ─────────────────────────────────────────────────────────────


def _nullok(parser: Callable[[Any, str], Any]) -> Callable[[Any, str], Any]:
    """Wrap a validator so a present ``null`` is accepted as an explicit-null state.

    For closed enum fields whose documented set does not include ``null`` the
    strict validator is used directly, so ``null`` is rejected there.
    """

    def wrapper(value: Any, field: str) -> Any:
        if value is None:
            return None
        return parser(value, field)

    return wrapper


_optional_string = _nullok(_parse_nonempty_string)
_optional_date = _nullok(_parse_date_string)
_optional_boolean = _nullok(_parse_boolean)
_optional_decimal = _nullok(_parse_decimal_string)
_optional_list = _nullok(_require_list)
_optional_mapping = _nullok(_require_mapping)


_COMPANY_FIELD_VALIDATORS: dict[str, Callable[[Any, str], Any]] = {
    "url": _nullok(_parse_freeagent_company_uri),
    "id": _parse_company_id,
    "name": _optional_string,
    "subdomain": _optional_string,
    "type": partial(_parse_enum, allowed=COMPANY_TYPES),
    "currency": _parse_nonempty_string,
    "mileage_units": partial(_parse_enum, allowed=MILEAGE_UNITS),
    "company_start_date": _optional_date,
    "trading_start_date": _optional_date,
    "first_accounting_year_end": _optional_date,
    "annual_accounting_periods": _optional_list,
    "freeagent_start_date": _optional_date,
    "address1": _optional_string,
    "address2": _optional_string,
    "address3": _optional_string,
    "town": _optional_string,
    "region": _optional_string,
    "postcode": _optional_string,
    "country": _optional_string,
    "company_registration_number": _optional_string,
    "contact_email": _optional_string,
    "contact_phone": _optional_string,
    "website": _optional_string,
    "business_type": _optional_string,
    "business_category": _optional_string,
    "short_date_format": partial(_parse_enum, allowed=SHORT_DATE_FORMATS),
    "sales_tax_name": _optional_string,
    "sales_tax_registration_number": _optional_string,
    "sales_tax_effective_date": _optional_date,
    "sales_tax_rates": _optional_list,
    "sales_tax_is_value_added": _optional_boolean,
    "cis_enabled": _optional_boolean,
    "cis_subcontractor": _optional_boolean,
    "cis_contractor": _optional_boolean,
    "locked_attributes": _optional_list,
    "created_at": _optional_string,
    "updated_at": _optional_string,
    "vat_first_return_period_ends_on": _optional_date,
    "initial_vat_basis": partial(_parse_enum, allowed=INITIAL_VAT_BASIS),
    "initially_on_frs": _optional_boolean,
    "initial_vat_frs_type": _optional_string,
    "sales_tax_deregistration_effective_date": _optional_date,
    "second_sales_tax_name": _optional_string,
    "second_sales_tax_rates": _optional_list,
    "second_sales_tax_is_compound": _optional_boolean,
}

_INVOICE_FIELD_VALIDATORS: dict[str, Callable[[Any, str], Any]] = {
    "url": _nullok(partial(_parse_freeagent_item_uri, resource="invoices")),
    "status": partial(_parse_enum, allowed=INVOICE_STATUSES),
    "long_status": _optional_string,
    "contact": partial(_parse_freeagent_item_uri, resource="contacts"),
    "project": _nullok(partial(_parse_freeagent_item_uri, resource="projects")),
    "property": _nullok(partial(_parse_freeagent_item_uri, resource="properties")),
    "include_timeslips": partial(_parse_nullable_enum, allowed=INVOICE_INCLUDE_TIMESLIPS),
    "include_expenses": partial(_parse_nullable_enum, allowed=INVOICE_INCLUDE_EXPENSES),
    "include_estimates": partial(_parse_nullable_enum, allowed=INVOICE_INCLUDE_ESTIMATES),
    "reference": _optional_string,
    "dated_on": _parse_date_string,
    "due_on": _optional_date,
    "payment_terms_in_days": _parse_integer,
    "currency": _optional_string,
    "cis_rate": _parse_nullable_string,
    "cis_deduction_rate": _optional_decimal,
    "cis_deduction": _optional_decimal,
    "cis_deduction_suffered": _optional_decimal,
    "comments": _optional_string,
    "send_new_invoice_emails": _optional_boolean,
    "send_reminder_emails": _optional_boolean,
    "send_thank_you_emails": _optional_boolean,
    "discount_percent": _optional_decimal,
    "contact_name": _optional_string,
    "client_contact_name": _optional_string,
    "payment_terms": _optional_string,
    "po_reference": _optional_string,
    "bank_account": _nullok(partial(_parse_freeagent_item_uri, resource="bank_accounts")),
    "omit_header": _optional_boolean,
    "show_project_name": _optional_boolean,
    "always_show_bic_and_iban": _optional_boolean,
    "ec_status": partial(_parse_enum, allowed=INVOICE_EC_STATUSES),
    "place_of_supply": _optional_string,
    "net_value": _optional_decimal,
    "exchange_rate": _optional_decimal,
    "involves_sales_tax": _optional_boolean,
    "sales_tax_value": _optional_decimal,
    "second_sales_tax_value": _optional_decimal,
    "total_value": _optional_decimal,
    "paid_value": _optional_decimal,
    "due_value": _optional_decimal,
    "is_interim_uk_vat": _optional_boolean,
    "paid_on": _optional_date,
    "written_off_date": _optional_date,
    "recurring_invoice": _nullok(partial(_parse_freeagent_item_uri, resource="recurring_invoices")),
    "payment_url": _nullok(_parse_safe_https_uri),
    "payment_methods": _parse_payment_methods,
    "invoice_items": _optional_list,
    "created_at": _optional_string,
    "updated_at": _optional_string,
}


def _validate_schema(mapping: Mapping[str, Any], validators: Mapping[str, Callable[[Any, str], Any]]) -> None:
    """Validate every present documented field against its documented kind/enum."""
    for field, validator in validators.items():
        if field in mapping:
            validator(mapping[field], field)


def _require_present_and_non_null(mapping: Mapping[str, Any], required: frozenset[str]) -> None:
    for field in required:
        if field not in mapping:
            raise ValueError(f"FreeAgent response is missing required field {field!r}")
        if mapping[field] is None:
            raise ValueError(f"FreeAgent required field {field!r} must not be null")


def _classify(mapping: Mapping[str, Any], documented: frozenset[str]) -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    absent = frozenset(field for field in documented if field not in mapping)
    null_fields = frozenset(field for field in documented if field in mapping and mapping[field] is None)
    unknown = frozenset(field for field in mapping if field not in documented)
    return absent, null_fields, unknown


def _optional(record: Mapping[str, Any], field: str, parser) -> Any:
    if field not in record or record[field] is None:
        return None
    return parser(record[field], field)


def _coerce_header_integer(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"FreeAgent {field} must be an integer")
    if type(value) is int:
        return value
    if isinstance(value, str) and value.strip():
        text = value.strip()
        if re.fullmatch(r"-?\d+", text):
            return int(text)
    raise ValueError(f"FreeAgent {field} must be an integer")


# ── Company ──────────────────────────────────────────────────────────────────


def _company_envelope(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("FreeAgent company response must be a JSON object")
    if "company" not in payload:
        raise ValueError("FreeAgent company response is missing the company envelope")
    company = payload["company"]
    if not isinstance(company, Mapping):
        raise ValueError("FreeAgent company envelope must be a JSON object")
    return company


def parse_company(payload: Mapping[str, Any]) -> FreeAgentCompanyRecord:
    """Validate a documented ``GET /v2/company`` response envelope.

    ``type`` and ``currency`` are required as an FA-S1 fail-closed inference:
    the company attribute table has no Required column, but both appear in the
    documented examples and are necessary to interpret any invoice amount.
    Every documented field is validated against its documented wire kind or
    exact documented enum. Unknown additive fields are recorded for review.
    """
    company = _company_envelope(payload)
    _require_present_and_non_null(company, COMPANY_INFERRED_REQUIRED_FIELDS)
    _validate_schema(company, _COMPANY_FIELD_VALIDATORS)

    absent, null_fields, unknown = _classify(company, COMPANY_DOCUMENTED_FIELDS)
    return FreeAgentCompanyRecord(
        type=_parse_enum(company["type"], "company type", COMPANY_TYPES),
        currency=_parse_nonempty_string(company["currency"], "company currency"),
        id=_parse_company_id(company.get("id"), "company id"),
        name=_optional(company, "name", _parse_nonempty_string),
        subdomain=_optional(company, "subdomain", _parse_nonempty_string),
        url=_optional(company, "url", _parse_freeagent_company_uri),
        absent_fields=absent,
        null_fields=null_fields,
        unknown_fields=unknown,
    )


# ── Invoice list ─────────────────────────────────────────────────────────────


def _invoice_envelope(payload: Mapping[str, Any]) -> list[Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("FreeAgent invoice list response must be a JSON object")
    if "invoices" not in payload:
        raise ValueError("FreeAgent invoice list response is missing the invoices envelope")
    invoices = payload["invoices"]
    if not isinstance(invoices, list):
        raise ValueError("FreeAgent invoices envelope must be a JSON array")
    return invoices


def _parse_invoice_record(record: Any) -> FreeAgentInvoiceRecord:
    if not isinstance(record, Mapping):
        raise ValueError("FreeAgent invoice must be a JSON object")

    _require_present_and_non_null(record, INVOICE_REQUIRED_FIELDS)
    _validate_schema(record, _INVOICE_FIELD_VALIDATORS)

    contact = _parse_freeagent_item_uri(record["contact"], "invoice contact", "contacts")
    dated_on = _parse_date_string(record["dated_on"], "invoice dated_on")
    payment_terms_in_days = _parse_integer(record["payment_terms_in_days"], "invoice payment_terms_in_days")

    url = _optional(record, "url", partial(_parse_freeagent_item_uri, resource="invoices"))
    status = _optional(record, "status", partial(_parse_enum, allowed=INVOICE_STATUSES))
    reference = _optional(record, "reference", _parse_nonempty_string)
    due_on = _optional(record, "due_on", _parse_date_string)
    currency = _optional(record, "currency", _parse_nonempty_string)
    long_status = _optional(record, "long_status", _parse_nonempty_string)
    ec_status = _optional(record, "ec_status", partial(_parse_enum, allowed=INVOICE_EC_STATUSES))
    contact_name = _optional(record, "contact_name", _parse_nonempty_string)
    created_at = _optional(record, "created_at", _parse_nonempty_string)
    updated_at = _optional(record, "updated_at", _parse_nonempty_string)

    amounts = {field: _optional(record, field, _parse_decimal_string) for field in (
        "net_value", "sales_tax_value", "second_sales_tax_value", "total_value",
        "paid_value", "due_value", "exchange_rate", "discount_percent",
        "cis_deduction_rate", "cis_deduction", "cis_deduction_suffered",
    )}

    absent, null_fields, unknown = _classify(record, INVOICE_DOCUMENTED_FIELDS)
    return FreeAgentInvoiceRecord(
        contact=contact,
        dated_on=dated_on,
        payment_terms_in_days=payment_terms_in_days,
        url=url,
        status=status,
        reference=reference,
        due_on=due_on,
        currency=currency,
        long_status=long_status,
        ec_status=ec_status,
        contact_name=contact_name,
        net_value=amounts["net_value"],
        sales_tax_value=amounts["sales_tax_value"],
        second_sales_tax_value=amounts["second_sales_tax_value"],
        total_value=amounts["total_value"],
        paid_value=amounts["paid_value"],
        due_value=amounts["due_value"],
        exchange_rate=amounts["exchange_rate"],
        discount_percent=amounts["discount_percent"],
        cis_deduction_rate=amounts["cis_deduction_rate"],
        cis_deduction=amounts["cis_deduction"],
        cis_deduction_suffered=amounts["cis_deduction_suffered"],
        created_at=created_at,
        updated_at=updated_at,
        absent_fields=absent,
        null_fields=null_fields,
        unknown_fields=unknown,
    )


def parse_invoice_list(payload: Mapping[str, Any]) -> tuple[FreeAgentInvoiceRecord, ...]:
    """Validate a documented ``GET /v2/invoices`` list response.

    Every invoice must carry a unique ``url`` identity. This is an FA-S1
    fail-closed inference (``url`` is documented as "the unique identifier for
    the invoice", not as a Required field); duplicates are rejected rather than
    silently overwritten because they may indicate unstable pagination.
    """
    invoices = _invoice_envelope(payload)
    records: list[FreeAgentInvoiceRecord] = []
    identities: set[str] = set()
    for item in invoices:
        record = _parse_invoice_record(item)
        if record.url is None:
            raise ValueError(
                "FreeAgent invoice list record is missing its url identity "
                f"({INVOICE_LIST_URL_IDENTITY_INFERENCE})"
            )
        if record.url in identities:
            raise ValueError("FreeAgent invoice list contains a duplicate url identity")
        identities.add(record.url)
        records.append(record)
    return tuple(records)


# ── Pagination ───────────────────────────────────────────────────────────────


def parse_link_header(value: str) -> dict[str, str]:
    """Parse the documented FreeAgent pagination ``Link`` header.

    Only the documented relation values ``prev``, ``next``, ``first`` and
    ``last`` are accepted; unknown or repeated relations fail closed. Each
    target is validated against the exact HTTPS FreeAgent origin and the
    ``/v2/invoices`` collection path; its query string is preserved verbatim.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError("FreeAgent Link header must be a non-empty string")

    links: dict[str, str] = {}
    cursor = 0
    for match in _LINK_VALUE_RE.finditer(value):
        separator = value[cursor:match.start()]
        if separator.strip().strip(","):
            raise ValueError("FreeAgent Link header contains an unrecognised segment")
        url, rel = match.group(1), match.group(2)
        if rel not in PAGINATION_LINK_RELATIONS:
            raise ValueError(f"FreeAgent Link header has an undocumented rel {rel!r}")
        if rel in links:
            raise ValueError(f"FreeAgent Link header repeats rel {rel!r}")
        _parse_freeagent_pagination_uri(url, f"Link rel {rel!r}")
        links[rel] = url
        cursor = match.end()

    tail = value[cursor:].strip().strip(",")
    if tail:
        raise ValueError("FreeAgent Link header contains an unrecognised segment")
    return links


def validate_pagination(
    *,
    page: Any = None,
    per_page: Any = None,
    link_header: str | None = None,
    total_count: Any = None,
) -> FreeAgentPagination:
    """Validate documented pagination parameters and response headers.

    ``per_page`` is constrained to the documented maximum of 100; ``page`` must
    be positive; ``total_count`` (``X-Total-Count``) must be non-negative.
    """
    if page is not None:
        page = _coerce_header_integer(page, "page")
        if page <= 0:
            raise ValueError("FreeAgent page must be a positive integer")
    if per_page is not None:
        per_page = _coerce_header_integer(per_page, "per_page")
        if per_page <= 0 or per_page > PAGINATION_MAX_PER_PAGE:
            raise ValueError(f"FreeAgent per_page must be between 1 and {PAGINATION_MAX_PER_PAGE}")
    if total_count is not None:
        total_count = _coerce_header_integer(total_count, "total_count")
        if total_count < 0:
            raise ValueError("FreeAgent total_count must be a non-negative integer")

    links = parse_link_header(link_header) if link_header is not None else {}
    return FreeAgentPagination(
        page=page,
        per_page=per_page,
        next_url=links.get("next"),
        prev_url=links.get("prev"),
        first_url=links.get("first"),
        last_url=links.get("last"),
        total_count=total_count,
    )
