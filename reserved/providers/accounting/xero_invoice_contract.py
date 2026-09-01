"""Pure, network-inert validation and mapping for reviewed Xero invoices.

Only the documented invoice response is accepted.  This module performs no
HTTP, configuration, credential, persistence, tax or settlement work.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from typing import Any, Mapping

from .contracts import (
    AccountingLine, AccountingProviderName,
    DocumentCandidate,
    DocumentType,
    EconomicDirection,
    LineValueSemantics,
    Money,
    Provenance, SemanticAdapterResult, SourceIdentity,
    SourceObservation,
    TaxAmountSemantics,
    TaxBreakdown,
)


XERO_API_NAME = "Xero Accounting API"
XERO_API_VERSION = "2.0"
XERO_INVOICE_RESOURCE = "Invoices"
XERO_INVOICE_SCHEMA_ID = "xero-accounting-invoice-xs2-2026-09-01"
XERO_INVOICE_ADAPTER_VERSION = "xero-xs2-v1"

INVOICE_TYPES = frozenset({"ACCREC", "ACCPAY"})
INVOICE_STATUSES = frozenset(
    {"DRAFT", "SUBMITTED", "DELETED", "AUTHORISED", "PAID", "VOIDED"}
)
LINE_AMOUNT_TYPES = frozenset({"Exclusive", "Inclusive", "NoTax"})

_REQUIRED_INVOICE_FIELDS = (
    "InvoiceID", "Type", "Contact", "Date", "Status", "LineAmountTypes",
    "LineItems", "SubTotal", "TotalTax", "Total", "CurrencyCode",
)
_REQUIRED_LINE_FIELDS = ("LineItemID", "LineAmount", "TaxAmount")
_MAX_IDENTIFIER = 512
_MAX_TEXT = 4096
_MAX_LINES = 10_000
_MAX_ABS_DECIMAL = Decimal("1000000000000000000")
_MAX_OPAQUE_DEPTH = 16
_MAX_OPAQUE_NODES = 10_000
_MAX_OPAQUE_CONTAINER = 1_000
_MAX_OPAQUE_STRING = 4_096
_MAX_SOURCE_DEPTH = 64
_MAX_SOURCE_NODES = 250_000
_MAX_SOURCE_CONTAINER = 10_000
_MAX_SOURCE_STRING_CHARACTERS = 4_096
_MAX_SOURCE_STRING_BYTES = _MAX_SOURCE_STRING_CHARACTERS * 4
_MAX_SOURCE_ENCODED_BYTES = 16_000_000


@dataclass(frozen=True)
class XeroLineItem:
    line_item_id: str
    line_amount: Decimal
    tax_amount: Decimal
    description: str | None
    quantity: Decimal | None
    unit_amount: Decimal | None
    item_code: str | None
    account_code: str | None
    account_id: str | None
    tax_type: str | None
    discount_rate: Decimal | None
    item: tuple[tuple[str, Any], ...] | None
    tracking: tuple[tuple[tuple[str, Any], ...], ...]
    absent_fields: frozenset[str]
    null_fields: frozenset[str]
    unknown_fields: frozenset[str]


@dataclass(frozen=True)
class XeroInvoice:
    invoice_id: str
    invoice_type: str
    contact_id: str
    contact_name: str | None
    issue_date: date
    due_date: date | None
    status: str
    line_amount_type: str
    currency: str
    subtotal: Decimal
    total_tax: Decimal
    total: Decimal
    line_items: tuple[XeroLineItem, ...]
    invoice_number: str | None
    absent_fields: frozenset[str]
    null_fields: frozenset[str]
    unknown_fields: frozenset[str]


@dataclass(frozen=True)
class XeroInvoiceMapping:
    invoice: XeroInvoice
    observation: SourceObservation
    adapter_result: SemanticAdapterResult


def _error(message: str) -> ValueError:
    # Error text deliberately identifies only the field/rule, never its value.
    return ValueError(f"Xero invoice contract: {message}")


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _error(f"{field} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise _error(f"{field} object keys must be strings")
    return value


def _string(value: Any, field: str, *, maximum: int = _MAX_IDENTIFIER) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise _error(f"{field} must be a bounded non-empty string")
    if any(ord(character) < 32 for character in value):
        raise _error(f"{field} contains control characters")
    return value


def _optional_string(container: Mapping[str, Any], field: str, *, maximum=_MAX_TEXT):
    if field not in container or container[field] is None:
        return None
    return _string(container[field], field, maximum=maximum)


def _day(value: Any, field: str) -> date:
    text = _string(value, field, maximum=10)
    if len(text) != 10:
        raise _error(f"{field} must be an ISO calendar date")
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise _error(f"{field} must be an ISO calendar date") from exc
    return parsed


def _decimal(value: Any, field: str, *, places: int | None) -> Decimal:
    # JSON integers and Decimal(parse_float=Decimal) are the accepted numeric
    # boundary. float is rejected so an earlier binary approximation cannot be
    # mistaken for source evidence.
    if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
        raise _error(f"{field} must be an exact JSON number")
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise _error(f"{field} must be a finite bounded decimal") from exc
    if not parsed.is_finite() or abs(parsed) > _MAX_ABS_DECIMAL:
        raise _error(f"{field} must be a finite bounded decimal")
    if places is not None and parsed.as_tuple().exponent < -places:
        raise _error(f"{field} exceeds reviewed decimal precision")
    return parsed


def _presence(container: Mapping[str, Any], known: frozenset[str]):
    absent = frozenset(known - container.keys())
    nulls = frozenset(key for key in known if key in container and container[key] is None)
    unknown = frozenset(container.keys() - known)
    return absent, nulls, unknown


def _freeze_json(
    value: Any, field: str, *, _depth: int = 0, _budget: list[int] | None = None,
) -> Any:
    """Retain documented opaque JSON without leaving mutable source objects."""
    if _budget is None:
        _budget = [0]
    _budget[0] += 1
    if _budget[0] > _MAX_OPAQUE_NODES:
        raise _error(f"{field} exceeds the bounded opaque node count")
    if _depth > _MAX_OPAQUE_DEPTH:
        raise _error(f"{field} exceeds the bounded opaque depth")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        if len(value) > _MAX_OPAQUE_STRING:
            raise _error(f"{field} contains an oversized string")
        return value
    if isinstance(value, int):
        if abs(value) > _MAX_ABS_DECIMAL:
            raise _error(f"{field} contains an out-of-bounds number")
        return value
    if isinstance(value, Decimal):
        if not value.is_finite() or abs(value) > _MAX_ABS_DECIMAL:
            raise _error(f"{field} contains a non-finite or out-of-bounds decimal")
        return value
    if isinstance(value, list):
        if len(value) > _MAX_OPAQUE_CONTAINER:
            raise _error(f"{field} contains an oversized container")
        return tuple(
            _freeze_json(item, field, _depth=_depth + 1, _budget=_budget)
            for item in value
        )
    if isinstance(value, Mapping):
        object_value = _mapping(value, field)
        if len(object_value) > _MAX_OPAQUE_CONTAINER:
            raise _error(f"{field} contains an oversized container")
        if any(len(key) > _MAX_OPAQUE_STRING for key in object_value):
            raise _error(f"{field} contains an oversized string")
        return tuple(sorted(
            (key, _freeze_json(item, field, _depth=_depth + 1, _budget=_budget))
            for key, item in object_value.items()
        ))
    raise _error(f"{field} contains an unsupported JSON shape")


def _digest_source(value: Any) -> str:
    """Hash source JSON with injective type and boundary encoding."""
    digest = sha256()
    nodes = 0
    encoded_bytes = 0

    def write(material: bytes) -> None:
        nonlocal encoded_bytes
        encoded_bytes += len(material)
        if encoded_bytes > _MAX_SOURCE_ENCODED_BYTES:
            raise _error("source representation exceeds the encoded byte bound")
        digest.update(material)

    def emit(raw: Any, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > _MAX_SOURCE_NODES or depth > _MAX_SOURCE_DEPTH:
            raise _error("source representation exceeds canonical digest bounds")
        if raw is None:
            write(b"n;")
        elif isinstance(raw, bool):
            write(b"b1;" if raw else b"b0;")
        elif isinstance(raw, int):
            if abs(raw) > _MAX_ABS_DECIMAL:
                raise _error("source representation contains an out-of-bounds integer")
            write(b"i" + str(raw).encode("ascii") + b";")
        elif isinstance(raw, Decimal):
            if not raw.is_finite() or abs(raw) > _MAX_ABS_DECIMAL:
                raise _error("source representation contains an invalid decimal")
            decimal_tuple = raw.as_tuple()
            digits = bytes(decimal_tuple.digits)
            write(
                b"d" + str(decimal_tuple.sign).encode("ascii") + b":"
                + str(decimal_tuple.exponent).encode("ascii") + b":"
                + str(len(digits)).encode("ascii") + b":" + digits + b";"
            )
        elif isinstance(raw, str):
            if len(raw) > _MAX_SOURCE_STRING_CHARACTERS:
                raise _error("source representation contains an oversized string")
            try:
                encoded = raw.encode("utf-8")
            except UnicodeEncodeError as exc:
                raise _error("source representation contains invalid Unicode") from exc
            if len(encoded) > _MAX_SOURCE_STRING_BYTES:
                raise _error("source representation contains an oversized string")
            write(b"s" + str(len(encoded)).encode("ascii") + b":" + encoded + b";")
        elif isinstance(raw, list):
            if len(raw) > _MAX_SOURCE_CONTAINER:
                raise _error("source representation contains an oversized container")
            write(b"l" + str(len(raw)).encode("ascii") + b"[")
            for entry in raw:
                emit(entry, depth + 1)
            write(b"]")
        elif isinstance(raw, Mapping):
            object_value = _mapping(raw, "source representation")
            if len(object_value) > _MAX_SOURCE_CONTAINER:
                raise _error("source representation contains an oversized container")
            write(b"m" + str(len(object_value)).encode("ascii") + b"{")
            for key in sorted(object_value):
                emit(key, depth + 1)
                emit(object_value[key], depth + 1)
            write(b"}")
        else:
            raise _error("source representation contains an unsupported JSON shape")

    emit(value, 0)
    return digest.hexdigest()


def _observe_invoice(
    raw: Mapping[str, Any], *, user_id: str, connected_organisation_id: str,
    tenant_id: str, import_run_id: str, retrieved_at: datetime, record_id: str,
) -> SourceObservation:
    source_digest = _digest_source(raw)
    present = {key for key, value in raw.items() if value is not None and value != ""}
    missing = tuple(key for key in _REQUIRED_INVOICE_FIELDS if key not in present)
    provenance = Provenance(
        identity=SourceIdentity(
            user_id, AccountingProviderName.XERO, connected_organisation_id,
            tenant_id, import_run_id,
        ),
        api_name=XERO_API_NAME,
        api_version=XERO_API_VERSION,
        resource=XERO_INVOICE_RESOURCE,
        record_id=record_id,
        source_fields=tuple(sorted(raw)),
        retrieved_at=retrieved_at,
        adapter_version=XERO_INVOICE_ADAPTER_VERSION,
        source_record_digest=source_digest,
        source_schema_id=XERO_INVOICE_SCHEMA_ID,
    )
    return SourceObservation(
        observation_id=f"xero:{record_id}:{source_digest[:16]}",
        provenance=provenance,
        missing_fields=missing,
    )


_LINE_FIELDS = frozenset({
    "Description", "Quantity", "UnitAmount", "ItemCode", "AccountCode",
    "AccountID", "AccountId", "Item", "LineItemID", "TaxType", "TaxAmount", "LineAmount",
    "DiscountRate", "Tracking",
})
_INVOICE_FIELDS = frozenset({
    "InvoiceID", "Type", "Contact", "Date", "DueDate", "Status",
    "LineAmountTypes", "LineItems", "SubTotal", "TotalTax", "Total",
    "CurrencyCode", "InvoiceNumber",
})


def _parse_line(raw: Any) -> XeroLineItem:
    item = _mapping(raw, "LineItems item")
    for field in _REQUIRED_LINE_FIELDS:
        if field not in item or item[field] is None:
            raise _error(f"detailed line is missing required {field}")
    tracking_raw = item.get("Tracking")
    if tracking_raw is None:
        tracking = ()
    elif isinstance(tracking_raw, list) and all(isinstance(entry, Mapping) for entry in tracking_raw):
        tracking = _freeze_json(tracking_raw, "Tracking")
    else:
        raise _error("Tracking must be an array of objects or null")
    absent, nulls, unknown = _presence(item, _LINE_FIELDS)
    if item.get("AccountID") is not None and item.get("AccountId") is not None:
        raise _error("line contains ambiguous account identity fields")
    account_identity = item.get("AccountID") if item.get("AccountID") is not None else item.get("AccountId")
    return XeroLineItem(
        line_item_id=_string(item["LineItemID"], "LineItemID"),
        line_amount=_decimal(item["LineAmount"], "LineAmount", places=2),
        tax_amount=_decimal(item["TaxAmount"], "TaxAmount", places=2),
        description=_optional_string(item, "Description"),
        quantity=None if item.get("Quantity") is None else _decimal(item["Quantity"], "Quantity", places=None),
        unit_amount=None if item.get("UnitAmount") is None else _decimal(item["UnitAmount"], "UnitAmount", places=4),
        item_code=_optional_string(item, "ItemCode"),
        account_code=_optional_string(item, "AccountCode"),
        account_id=None if account_identity is None else _string(account_identity, "account identity"),
        tax_type=_optional_string(item, "TaxType"),
        discount_rate=None if item.get("DiscountRate") is None else _decimal(item["DiscountRate"], "DiscountRate", places=None),
        item=None if item.get("Item") is None else _freeze_json(_mapping(item["Item"], "Item"), "Item"),
        tracking=tracking,
        absent_fields=absent,
        null_fields=nulls,
        unknown_fields=unknown,
    )


def parse_detailed_invoice_response(payload: Any) -> XeroInvoice:
    """Validate one detailed invoice response; summaries never pass as detail."""
    envelope = _mapping(payload, "response")
    if set(envelope) != {"Invoices"} or not isinstance(envelope["Invoices"], list):
        raise _error("response must contain only an Invoices array")
    if len(envelope["Invoices"]) != 1:
        raise _error("response must contain exactly one detailed invoice")
    raw = _mapping(envelope["Invoices"][0], "Invoices item")
    for field in _REQUIRED_INVOICE_FIELDS:
        if field not in raw or raw[field] is None:
            raise _error(f"detailed invoice is missing required {field}")
    if not isinstance(raw["LineItems"], list) or not raw["LineItems"]:
        raise _error("detailed invoice requires a non-empty LineItems array")
    if len(raw["LineItems"]) > _MAX_LINES:
        raise _error("LineItems exceeds the bounded line count")

    invoice_type = _string(raw["Type"], "Type")
    status = _string(raw["Status"], "Status")
    amount_type = _string(raw["LineAmountTypes"], "LineAmountTypes")
    if invoice_type not in INVOICE_TYPES:
        raise _error("Type is outside the reviewed set")
    if status not in INVOICE_STATUSES:
        raise _error("Status is outside the reviewed set")
    if amount_type not in LINE_AMOUNT_TYPES:
        raise _error("LineAmountTypes is outside the reviewed set")
    contact = _mapping(raw["Contact"], "Contact")
    if "ContactID" not in contact or contact["ContactID"] is None:
        raise _error("Contact requires ContactID")
    currency = _string(raw["CurrencyCode"], "CurrencyCode", maximum=3)
    if len(currency) != 3 or not currency.isascii() or not currency.isalpha() or not currency.isupper():
        raise _error("CurrencyCode must be three uppercase ASCII letters")

    lines = tuple(_parse_line(item) for item in raw["LineItems"])
    identities = [line.line_item_id for line in lines]
    if len(set(identities)) != len(identities):
        raise _error("LineItems contains duplicate LineItemID")
    subtotal = _decimal(raw["SubTotal"], "SubTotal", places=2)
    total_tax = _decimal(raw["TotalTax"], "TotalTax", places=2)
    total = _decimal(raw["Total"], "Total", places=2)
    if subtotal + total_tax != total:
        raise _error("SubTotal plus TotalTax must equal Total exactly")
    line_amount_sum = sum((line.line_amount for line in lines), Decimal(0))
    line_tax_sum = sum((line.tax_amount for line in lines), Decimal(0))
    if amount_type in {"Exclusive", "NoTax"} and line_amount_sum != subtotal:
        raise _error("line amounts do not reconcile to SubTotal")
    if amount_type == "Inclusive" and line_amount_sum != total:
        raise _error("inclusive line amounts do not reconcile to Total")
    if line_tax_sum != total_tax:
        raise _error("line tax amounts do not reconcile to TotalTax")
    if amount_type == "NoTax" and (total_tax != 0 or any(line.tax_amount != 0 for line in lines)):
        raise _error("NoTax evidence cannot carry non-zero tax amounts")

    absent, nulls, unknown = _presence(raw, _INVOICE_FIELDS)
    return XeroInvoice(
        invoice_id=_string(raw["InvoiceID"], "InvoiceID"),
        invoice_type=invoice_type,
        contact_id=_string(contact["ContactID"], "Contact.ContactID"),
        contact_name=_optional_string(contact, "Name"),
        issue_date=_day(raw["Date"], "Date"),
        due_date=None if raw.get("DueDate") is None else _day(raw["DueDate"], "DueDate"),
        status=status,
        line_amount_type=amount_type,
        currency=currency,
        subtotal=subtotal,
        total_tax=total_tax,
        total=total,
        line_items=lines,
        invoice_number=_optional_string(raw, "InvoiceNumber"),
        absent_fields=absent,
        null_fields=nulls,
        unknown_fields=unknown,
    )


def _canonical_line(line: XeroLineItem, amount_type: str, currency: str) -> AccountingLine:
    if amount_type == "Inclusive":
        gross, net = line.line_amount, line.line_amount - line.tax_amount
        semantics, value_semantics = TaxAmountSemantics.INCLUSIVE, LineValueSemantics.INCLUSIVE
    elif amount_type == "Exclusive":
        net, gross = line.line_amount, line.line_amount + line.tax_amount
        semantics, value_semantics = TaxAmountSemantics.EXCLUSIVE, LineValueSemantics.EXCLUSIVE
    else:
        net = gross = line.line_amount
        semantics, value_semantics = TaxAmountSemantics.NOT_APPLICABLE, LineValueSemantics.GROSS
    return AccountingLine(
        line_id=line.line_item_id,
        money=Money(gross, currency),
        tax=TaxBreakdown(net, line.tax_amount, gross, semantics, line.tax_type),
        description=line.description,
        provider_category_id=line.item_code,
        provider_account_id=line.account_id or line.account_code,
        value_semantics=value_semantics,
    )


def map_detailed_invoice_response(
    payload: Any,
    *,
    user_id: str,
    connected_organisation_id: str,
    tenant_id: str,
    import_run_id: str,
    retrieved_at: datetime,
) -> XeroInvoiceMapping:
    """Validate and map one invoice to an observation and candidate facts."""
    for value, field in (
        (user_id, "user identity"),
        (connected_organisation_id, "connected organisation identity"),
        (tenant_id, "tenant identity"),
        (import_run_id, "import run identity"),
    ):
        _string(value, field)
    if not isinstance(retrieved_at, datetime):
        raise _error("retrieved_at must be a datetime")
    invoice = parse_detailed_invoice_response(payload)
    raw = dict(_mapping(payload, "response")["Invoices"][0])
    observation = _observe_invoice(
        raw,
        user_id=user_id,
        connected_organisation_id=connected_organisation_id,
        tenant_id=tenant_id,
        import_run_id=import_run_id,
        record_id=invoice.invoice_id,
        retrieved_at=retrieved_at,
    )
    lines = tuple(_canonical_line(line, invoice.line_amount_type, invoice.currency) for line in invoice.line_items)
    candidate = DocumentCandidate(
        document_id=invoice.invoice_id,
        business_id=tenant_id,
        connected_organisation_id=connected_organisation_id,
        document_type=DocumentType.INVOICE if invoice.invoice_type == "ACCREC" else DocumentType.BILL,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        currency=invoice.currency,
        gross_amount=invoice.total,
        net_amount=invoice.subtotal,
        vat_amount=invoice.total_tax,
        lines=lines,
        provider_status=invoice.status,
        economic_direction=(EconomicDirection.RECEIVABLE if invoice.invoice_type == "ACCREC" else EconomicDirection.PAYABLE),
        document_number=invoice.invoice_number,
        contact_name=invoice.contact_name,
        economic_event_id=f"xero-invoice:{invoice.invoice_id}",
        provider_balance=None,
    )
    result = SemanticAdapterResult(
        observation_id=observation.observation_id,
        adapter_version=XERO_INVOICE_ADAPTER_VERSION,
        transformation="reviewed Xero detailed invoice to provider-neutral candidate facts",
        document_candidate=candidate,
        provider_assertions=(
            f"xero_type={invoice.invoice_type}",
            f"xero_status={invoice.status}",
            f"xero_line_amount_type={invoice.line_amount_type}",
            f"xero_contact_id={invoice.contact_id}",
        ),
    )
    return XeroInvoiceMapping(invoice, observation, result)
