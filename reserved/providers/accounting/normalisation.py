"""Fail-closed adapter-result to canonical-evidence conversion."""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json

from .contracts import (
    AccountingDocument, AccountingLine, AccountingMethod, AccountingProviderName,
    AllocationType, DocumentType, EvidenceState, Money, Provenance,
    RecognitionCandidate, SettlementSummary, SourceIdentity, TaxAmountSemantics,
    TaxBreakdown,
)


class CanonicalQuarantineError(ValueError):
    """A provider record cannot safely enter the canonical evidence store."""


def _required(payload, key):
    value = payload.get(key)
    if value is None or value == "":
        raise CanonicalQuarantineError(f"Missing required canonical document field: {key}")
    return value


def _date(value, field):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError) as exc:
        raise CanonicalQuarantineError(f"Invalid {field}") from exc


def _optional_date(value, field):
    return None if value in (None, "") else _date(value, field)


def _amount(value, field, *, allow_negative=False):
    try:
        result = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise CanonicalQuarantineError(f"Invalid {field}") from exc
    if result < 0 and not allow_negative:
        raise CanonicalQuarantineError(f"{field} cannot be negative")
    return result


def _datetime(value, field):
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise CanonicalQuarantineError(f"Invalid {field}") from exc


def _digest(payload):
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


def normalise_document(*, provider: str, payload: dict) -> AccountingDocument:
    provider_name = AccountingProviderName(provider)
    document_id = str(_required(payload, "external_document_id"))
    business_id = str(_required(payload, "external_business_id"))
    currency = str(_required(payload, "currency")).upper()
    gross = _amount(_required(payload, "gross_amount"), "gross_amount", allow_negative=True)
    amount_paid = (
        _amount(payload["amount_paid"], "amount_paid")
        if payload.get("amount_paid") is not None else None
    )
    retrieved_at = _datetime(_required(payload, "retrieved_at"), "retrieved_at")
    source_updated = payload.get("source_updated_at")
    provenance = Provenance(
        identity=SourceIdentity(
            str(_required(payload, "user_id")), provider_name,
            str(_required(payload, "connected_organisation_id")), business_id,
            str(_required(payload, "import_run_id")),
        ),
        api_name=str(_required(payload, "api_name")),
        api_version=str(_required(payload, "api_version")),
        resource=str(_required(payload, "resource")),
        record_id=document_id,
        source_fields=tuple(sorted(payload)),
        retrieved_at=retrieved_at,
        adapter_version=str(_required(payload, "adapter_version")),
        source_record_digest=_digest(payload),
        updated_at=_datetime(source_updated, "source_updated_at") if source_updated else None,
        transformation="provider adapter result to canonical accounting document",
        rounding="decimal quantized to 0.01 for monetary fields",
    )

    semantics = TaxAmountSemantics(payload.get("tax_semantics", "unknown"))
    lines_payload = payload.get("lines")
    if not isinstance(lines_payload, list) or not lines_payload:
        raise CanonicalQuarantineError("Missing required canonical document field: lines")
    lines = []
    for index, line in enumerate(lines_payload):
        line_gross = _amount(_required(line, "gross_amount"), f"lines[{index}].gross_amount", allow_negative=True)
        line_net = _amount(line["net_amount"], f"lines[{index}].net_amount", allow_negative=True) if line.get("net_amount") is not None else None
        line_vat = _amount(line["tax_amount"], f"lines[{index}].tax_amount", allow_negative=True) if line.get("tax_amount") is not None else None
        line_semantics = TaxAmountSemantics(line.get("tax_semantics", semantics.value))
        lines.append(AccountingLine(
            line_id=str(_required(line, "line_id")),
            money=Money(line_gross, currency),
            tax=TaxBreakdown(line_net, line_vat, line_gross, line_semantics,
                             line.get("vat_code"), Decimal(str(line["vat_rate"])) if line.get("vat_rate") is not None else None),
            description=line.get("description"),
            provider_category_id=line.get("provider_category_id"),
            provider_account_id=line.get("provider_account_id"),
            property_allocation_id=line.get("property_allocation_id"),
            tracking_allocation_ids=tuple(line.get("tracking_allocation_ids", ())),
        ))
    if sum((line.money.original_amount for line in lines), Decimal("0")) != gross:
        raise CanonicalQuarantineError("line gross amounts must equal document gross_amount")

    issue_date = _date(_required(payload, "issue_date"), "issue_date")
    return AccountingDocument(
        document_id=document_id,
        business_id=business_id,
        document_type=DocumentType(_required(payload, "document_type")),
        issue_date=issue_date,
        currency=currency,
        gross_amount=gross,
        lines=tuple(lines),
        provenance=provenance,
        economic_event_id=str(_required(payload, "economic_event_id")),
        status=str(_required(payload, "status")),
        amount_paid=amount_paid,
        due_date=_optional_date(payload.get("due_date"), "due_date"),
        document_number=payload.get("document_number"),
        contact_name=payload.get("contact_name"),
        cash_candidate=RecognitionCandidate(
            _optional_date(payload.get("cash_recognition_date"), "cash_recognition_date"),
            _amount(payload["cash_recognition_amount"], "cash_recognition_amount", allow_negative=True)
            if payload.get("cash_recognition_amount") is not None else None,
            AccountingMethod.CASH,
        ),
        accrual_candidate=RecognitionCandidate(issue_date, gross, AccountingMethod.TRADITIONAL_ACCRUAL),
        evidence_state=EvidenceState(payload.get("evidence_state", "unresolved")),
    )


def normalise_invoice(*, provider: str, payload: dict) -> AccountingDocument:
    """Compatibility name for complete canonical invoice documents."""
    converted = dict(payload)
    converted.setdefault("external_document_id", converted.get("external_invoice_id"))
    converted.setdefault("document_type", "invoice")
    converted.setdefault("document_number", converted.get("invoice_number"))
    return normalise_document(provider=provider, payload=converted)


def settlement_summary(document, allocations):
    relevant = [edge for edge in allocations if edge.document_id == document.document_id]
    reversed_ids = {edge.reverses_allocation_id for edge in relevant if edge.allocation_type is AllocationType.REVERSAL}
    total = sum((edge.amount for edge in relevant
                 if edge.allocation_type is not AllocationType.REVERSAL
                 and edge.allocation_id not in reversed_ids), Decimal("0"))
    return SettlementSummary(
        document.document_id,
        total,
        max(Decimal("0"), document.gross_amount - total),
        max(Decimal("0"), total - document.gross_amount),
    )


def select_recognition_candidate(document, method):
    if method is AccountingMethod.UNKNOWN:
        raise CanonicalQuarantineError("accounting method is unknown; recognition cannot be selected")
    return document.cash_candidate if method is AccountingMethod.CASH else document.accrual_candidate
