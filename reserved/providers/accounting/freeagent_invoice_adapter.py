"""Offline, unresolved-context FreeAgent invoice mapping; no provider authority.

Raw envelopes are bounded and replayed through FA-S1. An observation is a
content/context identity, not authentication or company membership evidence.
Only one explicitly non-sales-tax GBP economic item is currently supported.
"""
from dataclasses import dataclass, fields, is_dataclass, replace
from datetime import date, datetime, timezone
from decimal import Context, Decimal, localcontext
from enum import Enum
from hashlib import sha256
import json
import re
import unicodedata
from urllib.parse import urlsplit

from .freeagent_invoice_contract import parse_company, parse_invoice_list
from .contracts import (
    AccountingDocument, AccountingLine, AccountingProviderName, CanonicalDocumentState,
    CorrectionLifecycle, DocumentCandidate, DocumentType, EconomicDirection, LineValueSemantics, Money,
    Provenance, ProviderBalanceAssertions, SemanticAdapterResult, SourceIdentity,
    SourceObservation, TaxAmountSemantics, TaxBreakdown,
)
from .normalisation import normalise_document

ADAPTER_VERSION = "freeagent-offline-invoice/1.0"
SCHEMA_ID = "freeagent-fa-s1-plus-single-non-sales-tax-item/1.0"
MAX_BYTES = 65536
MAX_NODES = 1024
MAX_DEPTH = 8
MAX_TEXT = 2048
_INVOICE_FIELDS = frozenset({
    "url", "contact", "dated_on", "payment_terms_in_days", "currency", "status",
    "net_value", "total_value", "sales_tax_value", "involves_sales_tax",
    "discount_percent", "ec_status", "is_interim_uk_vat", "invoice_items",
    "reference", "contact_name", "long_status", "due_on", "paid_on",
    "paid_value", "due_value", "created_at", "updated_at",
})
_ITEM_FIELDS = frozenset({"url", "position", "item_type", "quantity", "price", "description"})
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")


class FreeAgentInvoiceAdapterError(ValueError):
    """Fixed, payload-free failure in the supported mapping subset."""


def _fail(reason):
    return FreeAgentInvoiceAdapterError("FreeAgent invoice mapping: " + reason)


def _bounded_payload(value):
    """Establish exact built-in JSON graph bounds before parsing or arithmetic."""
    seen = set()
    nodes, text_bytes = 0, 0

    def visit(item, depth):
        nonlocal nodes, text_bytes
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            raise _fail("payload_bounds")
        kind = type(item)
        if kind in (dict, list):
            if id(item) in seen or len(item) > 100:
                raise _fail("payload_graph")
            seen.add(id(item))
            if kind is dict:
                copied = {}
                for key, child in item.items():
                    if type(key) is not str:
                        raise _fail("payload_key")
                    visit(key, depth + 1)
                    copied[key] = visit(child, depth + 1)
                return copied
            else:
                return [visit(child, depth + 1) for child in item]
        elif kind is str:
            if len(item) > MAX_TEXT or any(unicodedata.category(c).startswith("C") for c in item):
                raise _fail("payload_text")
            text_bytes += len(item.encode("utf-8"))
            if text_bytes > MAX_BYTES:
                raise _fail("payload_bounds")
        elif kind is int:
            if abs(item) > 9999999999:
                raise _fail("payload_integer")
        elif item is not None and kind is not bool:
            raise _fail("payload_scalar")
        return item

    copied = visit(value, 0)
    encoded = json.dumps(copied, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    if len(encoded) > MAX_BYTES:
        raise _fail("payload_bounds")
    return encoded


def _required(record, name):
    if name not in record:
        raise _fail("missing_" + name)
    if record[name] is None:
        raise _fail("null_" + name)
    return record[name]


def _decimal(value, *, places=2):
    if type(value) is not str or re.fullmatch(
        rf"(?:0|[1-9][0-9]{{0,9}})(?:\.[0-9]{{1,{places}}})?", value
    ) is None:
        raise _fail("bounded_exact_decimal_required")
    return Decimal(value)


def _identity(value):
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise _fail("context_identity")
    return value


def _company_identity(value):
    if type(value) is int and 0 < value <= 9999999999:
        return value
    if type(value) is str and re.fullmatch(r"[1-9][0-9]{0,9}", value):
        return value
    raise _fail("company_identity")


def _utc(value):
    if type(value) is not datetime or value.tzinfo is not timezone.utc:
        raise _fail("exact_utc_retrieval_required")
    return value


def _uri(value, *, resource=None):
    if type(value) is not str or len(value) > 256:
        raise _fail("source_identity")
    try:
        parsed = urlsplit(value)
    except ValueError:
        raise _fail("source_identity") from None
    # Resource paths are never used to make a request. Item URLs remain the
    # source's own identifiers; no positional or balancing identity is invented.
    if (parsed.scheme != "https" or parsed.netloc != "api.freeagent.com"
            or parsed.query or parsed.fragment or "%" in parsed.path
            or re.fullmatch(r"/v2/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)+", parsed.path) is None):
        raise _fail("source_identity")
    if resource and re.fullmatch(rf"/v2/{resource}/[A-Za-z0-9_-]+", parsed.path) is None:
        raise _fail("source_identity")
    if resource is None and parsed.path.split("/")[2] in (
        "invoices", "contacts", "projects", "properties", "bank_accounts",
        "recurring_invoices", "company", "categories", "stock_items",
    ):
        # FA-S1 resource validators and documented item category/stock references
        # distinguish these provider resource namespaces from invoice items
        # (including invoice PDF/action paths). This is a limited exclusion,
        # not a universal item-URL grammar or authenticated source identity.
        raise _fail("incompatible_item_resource")
    return value


def _source_paths(value, prefix=""):
    result = []
    if type(value) is dict:
        for key in sorted(value):
            path = f"{prefix}.{key}" if prefix else key
            result.append(path)
            result.extend(_source_paths(value[key], path))
    elif type(value) is list:
        for index, item in enumerate(value):
            result.extend(_source_paths(item, f"{prefix}[{index}]"))
    return tuple(result)


def _observe_snapshot(company_payload, invoice_payload, *, user_id,
                    connected_organisation_id, business_id, company_id,
                    import_run_id, retrieved_at):
    """Identify supplied source/context; this does not authenticate any fact."""
    context = [_identity(value) for value in
               (user_id, connected_organisation_id, business_id, import_run_id)]
    company_id = _company_identity(company_id)
    retrieved_at = _utc(retrieved_at)
    combined = {"company_response": company_payload, "invoice_response": invoice_payload}
    encoded = _bounded_payload(combined)
    # All validation and later mapping use this owned snapshot, not mutable
    # caller references after the content identity has been calculated.
    combined = json.loads(encoded)
    company_payload = combined["company_response"]
    invoice_payload = combined["invoice_response"]
    if (type(company_payload) is not dict or set(company_payload) != {"company"}
            or type(invoice_payload) is not dict or set(invoice_payload) != {"invoices"}
            or type(company_payload["company"]) is not dict
            or type(invoice_payload["invoices"]) is not list
            or len(invoice_payload["invoices"]) != 1
            or type(invoice_payload["invoices"][0]) is not dict):
        raise _fail("exact_envelopes_required")
    raw = invoice_payload["invoices"][0]
    # Reject uninterpreted financial fields before FA-S1 can parse arbitrary
    # decimal exponents. Other present company fields still pass its schema.
    if set(raw) - _INVOICE_FIELDS:
        raise _fail("unsupported_invoice_fields")
    for name in ("net_value", "total_value", "sales_tax_value", "discount_percent", "paid_value", "due_value"):
        if name in raw and raw[name] is not None:
            _decimal(raw[name])
    try:
        company = parse_company(company_payload)
        invoice, = parse_invoice_list(invoice_payload)
    except (ValueError, TypeError, OverflowError):
        raise _fail("source_schema_invalid") from None
    if company.unknown_fields or invoice.unknown_fields:
        raise _fail("additive_source_fields")
    actual_id = _company_identity(company.id)
    if type(actual_id) is not type(company_id) or actual_id != company_id:
        raise _fail("company_context_mismatch")
    _uri(invoice.url, resource="invoices")
    _uri(invoice.contact, resource="contacts")
    digest = sha256(encoded.encode("ascii")).hexdigest()
    identity_material = json.dumps([ADAPTER_VERSION, digest, context,
                                    company_id, retrieved_at.isoformat()], separators=(",", ":"))
    observation_id = "freeagent-invoice:" + sha256(identity_material.encode("ascii")).hexdigest()
    observed = SourceObservation(
        observation_id, Provenance(
            SourceIdentity(user_id, AccountingProviderName.FREEAGENT,
                           connected_organisation_id, business_id, import_run_id),
            "FreeAgent API", "v2", "invoices", invoice.url,
            _source_paths(combined), retrieved_at, ADAPTER_VERSION, digest,
            source_definitions=("company_and_invoice_snapshot_digest",
                                "company_id=" + json.dumps(company_id),
                                "caller_context_not_authenticated_membership"),
            source_schema_id=SCHEMA_ID, rounding="none",
        ),
        evidence_reason="Supplied source and context only; membership and freshness unverified",
    )
    return observed, company_payload["company"], raw


def observe_invoice(company_payload, invoice_payload, *, user_id,
                    connected_organisation_id, business_id, company_id,
                    import_run_id, retrieved_at):
    """Capture unresolved source/context evidence, never membership authority."""
    return _observe_snapshot(
        company_payload, invoice_payload, user_id=user_id,
        connected_organisation_id=connected_organisation_id, business_id=business_id,
        company_id=company_id, import_run_id=import_run_id, retrieved_at=retrieved_at,
    )[0]


def _exact_match(actual, expected):
    """No polymorphic hooks or self-stamped dataclass state crosses replay."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, Enum):
        return actual is expected
    if is_dataclass(expected):
        return all(_exact_match(getattr(actual, field.name, None), getattr(expected, field.name))
                   for field in fields(expected))
    if type(expected) is tuple:
        return len(actual) == len(expected) and all(_exact_match(a, b) for a, b in zip(actual, expected))
    if type(expected) is datetime:
        return actual.tzinfo is timezone.utc and actual == expected
    return actual == expected


@dataclass(frozen=True, repr=False)
class FreeAgentInvoiceMapping:
    observation: SourceObservation
    document: AccountingDocument


def adapt_invoice(company_payload, invoice_payload, *, observation, user_id,
                  connected_organisation_id, business_id, company_id,
                  import_run_id, retrieved_at):
    """Replay exact source/context, then map the supported non-tax item."""
    expected, company, raw = _observe_snapshot(
        company_payload, invoice_payload, user_id=user_id,
        connected_organisation_id=connected_organisation_id, business_id=business_id,
        company_id=company_id, import_run_id=import_run_id, retrieved_at=retrieved_at,
    )
    if not _exact_match(observation, expected):
        raise _fail("source_or_context_replay_mismatch")
    if (company["type"] != "UkSoleTrader" or company["currency"] != "GBP"
            or _required(company, "country") != "United Kingdom"
            or any(_required(company, field) is not False
                   for field in ("cis_enabled", "cis_subcontractor", "cis_contractor"))):
        raise _fail("unsupported_company_context")
    if (_required(raw, "currency") != "GBP"
            or _required(raw, "involves_sales_tax") is not False
            or _required(raw, "is_interim_uk_vat") is not False
            or _required(raw, "ec_status") != "UK/Non-EC"
            or _required(raw, "status") not in ("Open", "Overdue", "Paid", "Zero Value")):
        raise _fail("unsupported_invoice_context")
    net, tax, gross, discount = (_decimal(_required(raw, name)) for name in
                                 ("net_value", "sales_tax_value", "total_value", "discount_percent"))
    if tax != 0 or discount != 0 or net != gross:
        raise _fail("non_tax_totals_do_not_reconcile")
    if raw["status"] == "Zero Value" and gross != 0:
        raise _fail("zero_value_status_conflicts_with_gross")
    items = _required(raw, "invoice_items")
    if type(items) is not list or len(items) != 1 or type(items[0]) is not dict:
        raise _fail("one_economic_item_required")
    item = items[0]
    if set(item) - _ITEM_FIELDS:
        raise _fail("unsupported_item_fields")
    item_id = _uri(_required(item, "url"))
    if item_id in (raw["url"], raw["contact"]):
        raise _fail("item_identity_collision")
    if _required(item, "item_type") not in ("Products", "Services"):
        raise _fail("unsupported_item_type")
    description = _required(item, "description")
    if type(description) is not str or not description.strip():
        raise _fail("item_description")
    quantity = _decimal(_required(item, "quantity"), places=6)
    price = _decimal(_required(item, "price"))
    if "position" in item and _decimal(_required(item, "position"), places=6) != 1:
        raise _fail("item_position")
    # Fixed precision exceeds the bounded product's maximum 32 significant
    # digits; no rounding or caller-controlled decimal context is inherited.
    with localcontext(Context(prec=64)):
        amount = quantity * price
        if amount != gross:
            raise _fail("item_totals_do_not_reconcile")
        line = AccountingLine(item_id, Money(amount, "GBP"),
                              TaxBreakdown(net, tax, gross, TaxAmountSemantics.UNKNOWN),
                              description=description, value_semantics=LineValueSemantics.UNKNOWN)
        balance = ProviderBalanceAssertions(
            amount_paid=None if raw.get("paid_value") is None else _decimal(raw["paid_value"]),
            amount_due=None if raw.get("due_value") is None else _decimal(raw["due_value"]),
        )
        event_material = json.dumps([user_id, connected_organisation_id, business_id,
                                     company_id, raw["url"]], separators=(",", ":"))
        candidate = DocumentCandidate(
            raw["url"], business_id, connected_organisation_id, DocumentType.INVOICE,
            date.fromisoformat(raw["dated_on"]), "GBP", gross, (line,),
            provider_status=raw["status"], canonical_state=CanonicalDocumentState.UNKNOWN,
            canonical_state_reason="Raw status is not a Reserved lifecycle decision",
            net_amount=net, vat_amount=tax, economic_direction=EconomicDirection.RECEIVABLE,
            due_date=None if raw.get("due_on") is None else date.fromisoformat(raw["due_on"]),
            document_number=raw.get("reference"), contact_name=raw.get("contact_name"),
            economic_event_id="freeagent-invoice-event:" + sha256(event_material.encode("ascii")).hexdigest(),
            provider_balance=balance,
        )
        semantic = SemanticAdapterResult(
            expected.observation_id, ADAPTER_VERSION,
            "One non-sales-tax item; exact quantity times price, no rounding",
            document_candidate=candidate,
            provider_assertions=("raw_status=" + raw["status"],
                                 "paid_value_and_due_value_are_provider_assertions_only",
                                 "company_context_is_not_authenticated_membership"),
        )
        document = normalise_document(observation=expected, adapter_result=semantic)
        # Shared normalisation currently defaults to NONE (no correction
        # recorded), not verified absence. This adapter has no correction
        # evidence, so its public canonical result explicitly says UNKNOWN.
        # The semantic candidate is internal, not a round-trip public contract.
        document = replace(document, correction_lifecycle=CorrectionLifecycle.UNKNOWN)
    return FreeAgentInvoiceMapping(expected, document)
