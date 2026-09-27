"""Narrow, network-inert QuickBooks invoice/payment canonical adapter.

Only exact Q-S4 observations inside the reviewed Q-S5A shape are accepted.
There is deliberately no transport, credential, persistence, activation or
general QuickBooks ingestion capability in this module.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
import re
from typing import Any, Mapping

from .contracts import (
    AccountingDocument, AccountingLine, AccountingPayment,
    AccountingProviderName, AllocationEdge, AllocationType,
    CanonicalDocumentState, DocumentCandidate, DocumentType,
    CorrectionLifecycle, EconomicDirection, EvidenceState, LineRole,
    LineValueSemantics, Money, PaymentType, SettlementState,
    Provenance, ProviderBalanceAssertions, SemanticAdapterResult,
    SourceIdentity, SourceObservation, TaxAmountSemantics, TaxBreakdown,
)
from .normalisation import normalise_document, validate_allocations
from .quickbooks_observation_contract import (
    FrozenEvidence, FrozenEvidenceSequence, InvoiceObservation,
    InvoiceLineObservation, PaymentLineObservation, PaymentLinkObservation,
    PaymentObservation, _digest, _thaw_retained_evidence,
    observation_attestation, observe_invoice, observe_payment,
)
from .quickbooks_oauth_contract import RealmBinding


ADAPTER_VERSION = "quickbooks-qs5a-v2"
SCHEMA_ID = "quickbooks-qbo-qs4-observation-qs5a-2026-09-01"
API_NAME = "QuickBooks Online Accounting API"
API_VERSION = "v3/minorversion-75"
_SAFE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,511}\Z")
_MAX_INTEGRITY_NODES = 100_000
_MAX_BINDING_TEXT = 512
_MAX_SALES_LINES = 3


class QuickBooksAdapterError(ValueError):
    """Fail-closed adapter rejection; messages never contain source values."""


@dataclass(frozen=True)
class InvoiceAdapterResult:
    source_observation: InvoiceObservation
    observation: SourceObservation
    semantic_result: SemanticAdapterResult
    document: AccountingDocument
    customer_reference_value: str


@dataclass(frozen=True)
class PaymentAdapterResult:
    payment: AccountingPayment
    allocation: AllocationEdge


def _fail(rule: str) -> QuickBooksAdapterError:
    return QuickBooksAdapterError(f"QuickBooks Q-S5A adapter: {rule}")


def _safe_id(value: Any, field: str) -> str:
    if type(value) is not str or _SAFE_ID.fullmatch(value) is None:
        raise _fail(f"{field} is not a stable safe identifier")
    return value


def _money(value: Any, field: str) -> Decimal:
    if type(value) not in (int, Decimal):
        raise _fail(f"{field} is not exact money")
    result = Decimal(value)
    if not result.is_finite() or result < 0:
        raise _fail(f"{field} must be nonnegative finite money")
    if result.as_tuple().exponent < -2:
        raise _fail(f"{field} exceeds two decimal places")
    return result


def _decimal(value: Any, field: str) -> Decimal:
    if type(value) not in (int, Decimal):
        raise _fail(f"{field} is not an exact number")
    result = Decimal(value)
    if not result.is_finite() or result < 0:
        raise _fail(f"{field} must be nonnegative and finite")
    return result


def _percent_rate(value: Decimal) -> Decimal:
    """Divide a finite Decimal percentage by 100 without context rounding."""
    sign, digits, exponent = value.as_tuple()
    return Decimal((sign, digits, exponent - 2))


def _exact_product(left: Decimal, right: Decimal) -> Decimal:
    """Multiply bounded Decimal inputs with enough precision for every digit."""
    precision = max(1, len(left.as_tuple().digits) + len(right.as_tuple().digits))
    with localcontext() as context:
        context.prec = precision
        return left * right


def _derived_money(value: Decimal, field: str) -> Decimal:
    """Normalize only representational trailing zeroes; never round a value."""
    _, digits, exponent = value.as_tuple()
    with localcontext() as context:
        context.prec = max(1, len(digits) + max(0, exponent + 2))
        pennies = value.quantize(Decimal("0.01"))
    if pennies != value:
        raise _fail(f"{field} requires rounding")
    return _money(pennies, field)


def _object(value: Any, field: str) -> FrozenEvidence:
    if type(value) is not FrozenEvidence:
        raise _fail(f"{field} must be retained object evidence")
    return value


def _sequence(value: Any, field: str) -> tuple[Any, ...]:
    if type(value) is not FrozenEvidenceSequence:
        raise _fail(f"{field} must be retained array evidence")
    return tuple(value)


def _member(obj: Mapping[str, Any], field: str) -> Any:
    if field not in obj or obj[field] is None:
        raise _fail(f"{field} must be explicit and non-null")
    return obj[field]


def _currency(raw: Mapping[str, Any]) -> str:
    ref = _object(_member(raw, "CurrencyRef"), "CurrencyRef")
    currency = _safe_id(_member(ref, "value"), "CurrencyRef.value")
    # GBP is the only currency represented by the reviewed non-US tax example.
    # Do not turn syntactically plausible unknown codes into supported facts.
    if currency != "GBP":
        raise _fail("currency is outside the reviewed GBP boundary")
    return currency


def _plain(value: Any) -> Any:
    """Reconstruct observer input from the retained immutable evidence only."""
    try:
        return _thaw_retained_evidence(value)
    except Exception:
        raise _fail("retained source evidence validation failed") from None


_INTEGRITY_DATACLASSES = frozenset({
    InvoiceObservation, InvoiceLineObservation, PaymentObservation,
    PaymentLineObservation, PaymentLinkObservation, InvoiceAdapterResult,
    SourceObservation, Provenance, SourceIdentity, SemanticAdapterResult,
    DocumentCandidate, AccountingDocument, AccountingLine, Money, TaxBreakdown,
    ProviderBalanceAssertions,
})
_INTEGRITY_ENUMS = frozenset({
    AccountingProviderName, AllocationType, CanonicalDocumentState,
    CorrectionLifecycle, DocumentType, EconomicDirection, EvidenceState,
    LineRole, LineValueSemantics, PaymentType, SettlementState,
    TaxAmountSemantics,
})


def _assert_exact_graph(root: Any, rule: str) -> None:
    """Preflight an integrity graph without invoking supplied protocols."""
    stack = [root]
    nodes = 0
    while stack:
        value = stack.pop()
        nodes += 1
        if nodes > _MAX_INTEGRITY_NODES:
            raise _fail(rule)
        value_type = type(value)
        if value_type is datetime:
            if object.__getattribute__(value, "tzinfo") is not timezone.utc:
                raise _fail(rule)
            continue
        if value is None or value_type in (bool, str, int, Decimal, date):
            continue
        if value_type in _INTEGRITY_ENUMS:
            continue
        if value_type is tuple:
            stack.extend(value)
            continue
        if value_type is frozenset:
            stack.extend(value)
            continue
        if value_type is FrozenEvidence:
            _plain(value)
            continue
        if value_type in _INTEGRITY_DATACLASSES:
            stack.extend(object.__getattribute__(value, item.name)
                         for item in fields(value_type))
            continue
        raise _fail(rule)


def _exact_optional(value: Any, allowed: type) -> bool:
    return value is None or type(value) is allowed


def _exact_string_set(value: Any) -> bool:
    return type(value) is frozenset and all(type(item) is str for item in value)


def _assert_observation_schema(observation: Any) -> None:
    common_strings = ("user_id", "realm_id", "credential_reference", "entity_id",
                      "sync_token", "source_digest", "observation_attestation",
                      "customer_reference_value")
    if (any(type(object.__getattribute__(observation, name)) is not str
            for name in common_strings)
            or type(object.__getattribute__(observation, "retrieved_at")) is not datetime
            or object.__getattribute__(
                object.__getattribute__(observation, "retrieved_at"), "tzinfo"
            ) is not timezone.utc
            or not _exact_optional(object.__getattribute__(observation,
                                                           "transaction_date"), date)
            or any(not _exact_string_set(object.__getattribute__(observation, name))
                   for name in ("present_fields", "null_fields"))):
        raise _fail("retained source evidence validation failed")
    lines = object.__getattribute__(observation, "lines")
    if type(lines) is not tuple:
        raise _fail("retained source evidence validation failed")
    if type(observation) is InvoiceObservation:
        if (not _exact_optional(object.__getattribute__(observation, "due_date"), date)
                or any(not _exact_optional(object.__getattribute__(observation, name), Decimal)
                       for name in ("total_amount", "balance"))
                or type(object.__getattribute__(observation,
                                                "currency_ref_present")) is not bool
                or not _exact_optional(object.__getattribute__(
                    observation, "global_tax_calculation"), str)
                or type(object.__getattribute__(
                    observation, "transaction_tax_detail_present")) is not bool):
            raise _fail("retained source evidence validation failed")
        for line in lines:
            if (type(line) is not InvoiceLineObservation
                    or type(object.__getattribute__(line, "detail_type")) is not str
                    or not _exact_optional(object.__getattribute__(line, "amount"), Decimal)
                    or not _exact_string_set(object.__getattribute__(line, "present_fields"))
                    or not _exact_string_set(object.__getattribute__(line, "null_fields"))):
                raise _fail("retained source evidence validation failed")
    else:
        if (any(not _exact_optional(object.__getattribute__(observation, name), Decimal)
                for name in ("total_amount", "unapplied_amount"))
                or any(type(object.__getattribute__(observation, name)) is not bool
                       for name in ("currency_ref_present", "currency_ref_null"))):
            raise _fail("retained source evidence validation failed")
        for line in lines:
            if (type(line) is not PaymentLineObservation
                    or not _exact_optional(object.__getattribute__(line, "amount"), Decimal)
                    or type(object.__getattribute__(line, "links")) is not tuple
                    or not _exact_string_set(object.__getattribute__(line, "present_fields"))
                    or not _exact_string_set(object.__getattribute__(line, "null_fields"))):
                raise _fail("retained source evidence validation failed")
            for link in object.__getattribute__(line, "links"):
                if (type(link) is not PaymentLinkObservation
                        or not _exact_optional(object.__getattribute__(
                            link, "transaction_id"), str)
                        or not _exact_optional(object.__getattribute__(
                            link, "transaction_type"), str)
                        or not _exact_string_set(object.__getattribute__(link, "present_fields"))
                        or not _exact_string_set(object.__getattribute__(link, "null_fields"))):
                    raise _fail("retained source evidence validation failed")


def _assert_matching_types(expected: Any, supplied: Any, rule: str) -> None:
    """Match a supplied graph to a freshly built trusted graph without equality."""
    stack = [(expected, supplied)]
    nodes = 0
    while stack:
        trusted, value = stack.pop()
        nodes += 1
        if nodes > _MAX_INTEGRITY_NODES or type(value) is not type(trusted):
            raise _fail(rule)
        value_type = type(value)
        if value_type is datetime:
            if object.__getattribute__(value, "tzinfo") is not timezone.utc:
                raise _fail(rule)
            continue
        if (value is None or value_type in (bool, str, int, Decimal, date)
                or value_type in _INTEGRITY_ENUMS):
            continue
        if value_type is tuple:
            if len(value) != len(trusted):
                raise _fail(rule)
            stack.extend(zip(trusted, value))
            continue
        if value_type is frozenset:
            # Q-S5A frozensets are exact string presence/null-field sets.
            if not all(type(item) is str for item in value):
                raise _fail(rule)
            continue
        if value_type is FrozenEvidence:
            _plain(value)
            continue
        if value_type in _INTEGRITY_DATACLASSES:
            stack.extend((object.__getattribute__(trusted, item.name),
                          object.__getattribute__(value, item.name))
                         for item in fields(value_type))
            continue
        raise _fail(rule)


def _assert_observation(observation: Any, expected_type: type,
                        evidence_state: EvidenceState,
                        binding: RealmBinding) -> Mapping[str, Any]:
    if type(observation) is not expected_type:
        raise _fail("input was not validated by the exact Q-S4 observation contract")
    # Validate every replay-compared leaf before binding checks, digesting or
    # dataclass equality can dispatch to a supplied object protocol.
    _assert_exact_graph(observation, "retained source evidence validation failed")
    _assert_observation_schema(observation)
    if type(evidence_state) is not EvidenceState:
        raise _fail("source evidence state is invalid")
    if evidence_state in (EvidenceState.CONFLICTING, EvidenceState.EXCLUDED):
        raise _fail("source evidence is conflicting or excluded")
    try:
        if type(binding) is not RealmBinding:
            raise _fail("Q-S1 provenance binding validation failed")
        binding_values = tuple(object.__getattribute__(binding, name) for name in (
            "user_id", "realm_id", "credential_reference"))
        if any(type(value) is not str or not value.strip()
               or len(value) > _MAX_BINDING_TEXT for value in binding_values):
            raise _fail("Q-S1 provenance binding validation failed")
        if (binding_values[0] != observation.user_id
                or binding_values[1] != observation.realm_id
                or binding_values[2] != observation.credential_reference):
            raise _fail("Q-S1 provenance binding mismatch")
        raw = object.__getattribute__(observation, "source_evidence")
        plain = _plain(raw)
        digest = _digest(plain)
        if digest != observation.source_digest:
            raise _fail("source digest mismatch")
        expected_attestation = observation_attestation(
            expected_type.__name__, observation.source_digest,
            observation.user_id, observation.realm_id,
            observation.credential_reference, observation.retrieved_at)
        if expected_attestation != observation.observation_attestation:
            raise _fail("observation attestation mismatch")
        if plain.get("Id") != observation.entity_id or plain.get("SyncToken") != observation.sync_token:
            raise _fail("source identity or revision mismatch")
        if not observation.user_id or not observation.realm_id or not observation.credential_reference:
            raise _fail("source binding is incomplete")
        _safe_id(observation.entity_id, "Id")
        _safe_id(observation.sync_token, "SyncToken")
        _safe_id(observation.realm_id, "realm binding")
        observer = observe_invoice if expected_type is InvoiceObservation else observe_payment
        replayed = observer(
            plain, binding=binding, user_id=observation.user_id,
            realm_id=observation.realm_id,
            credential_reference=observation.credential_reference,
            retrieved_at=observation.retrieved_at,
        )
        if replayed != observation:
            raise _fail("complete Q-S4 observation replay mismatch")
    except QuickBooksAdapterError:
        raise
    except Exception:
        raise _fail("retained source evidence validation failed") from None
    return raw


def _assert_linked_invoice_shape(invoice: Any) -> None:
    """Reject malformed exact outer dataclasses before any dereference/equality."""
    if type(invoice) is not InvoiceAdapterResult:
        raise _fail("linked invoice result integrity check failed")
    try:
        _assert_exact_graph(invoice, "linked invoice result integrity check failed")
        source_observation = object.__getattribute__(invoice, "source_observation")
        source = object.__getattribute__(invoice, "observation")
        semantic = object.__getattribute__(invoice, "semantic_result")
        document = object.__getattribute__(invoice, "document")
        if (type(source_observation)
                is not InvoiceObservation
                or type(source) is not SourceObservation
                or type(semantic) is not SemanticAdapterResult
                or type(document) is not AccountingDocument
                or type(object.__getattribute__(invoice, "customer_reference_value"))
                is not str):
            raise _fail("linked invoice result integrity check failed")
        source_provenance = object.__getattribute__(source, "provenance")
        document_provenance = object.__getattribute__(document, "provenance")
        candidate = object.__getattribute__(semantic, "document_candidate")
        if (type(source_provenance) is not Provenance
                or type(document_provenance) is not Provenance
                or type(object.__getattribute__(source_provenance, "identity"))
                is not SourceIdentity
                or type(object.__getattribute__(document_provenance, "identity"))
                is not SourceIdentity
                or type(candidate) is not DocumentCandidate):
            raise _fail("linked invoice result integrity check failed")
        for lines in (object.__getattribute__(candidate, "lines"),
                      object.__getattribute__(document, "lines")):
            if type(lines) is not tuple:
                raise _fail("linked invoice result integrity check failed")
            for line in lines:
                if (type(line) is not AccountingLine
                        or type(object.__getattribute__(line, "money")) is not Money
                        or type(object.__getattribute__(line, "tax")) is not TaxBreakdown):
                    raise _fail("linked invoice result integrity check failed")
    except QuickBooksAdapterError:
        raise
    except Exception:
        raise _fail("linked invoice result integrity check failed") from None


def _provenance(observation: Any, raw: Mapping[str, Any], import_run_id: str,
                resource: str) -> Provenance:
    _safe_id(import_run_id, "import_run_id")
    return Provenance(
        identity=SourceIdentity(
            observation.user_id, AccountingProviderName.QUICKBOOKS,
            observation.credential_reference, observation.realm_id,
            import_run_id,
        ),
        api_name=API_NAME, api_version=API_VERSION, resource=resource,
        record_id=observation.entity_id, source_fields=tuple(sorted(raw)),
        retrieved_at=observation.retrieved_at, adapter_version=ADAPTER_VERSION,
        source_record_digest=observation.source_digest,
        source_schema_id=SCHEMA_ID, revision_id=observation.sync_token,
        transformation="exact Q-S4 evidence to narrow Q-S5A canonical mapping",
        rounding="none",
    )


def adapt_invoice(observation: InvoiceObservation, *, binding: RealmBinding,
                  import_run_id: str,
                  evidence_state: EvidenceState = EvidenceState.SELECTED
                  ) -> InvoiceAdapterResult:
    """Map the bounded reviewed tax-exclusive invoice shape or fail closed."""
    raw = _assert_observation(
        observation, InvoiceObservation, evidence_state, binding)
    _safe_id(observation.customer_reference_value, "CustomerRef.value")
    if observation.global_tax_calculation != "TaxExcluded":
        raise _fail("only exact TaxExcluded invoices are supported")
    if observation.transaction_date is None or "TxnDate" not in raw:
        raise _fail("TxnDate is mandatory")
    currency = _currency(raw)
    total = _money(_member(raw, "TotalAmt"), "TotalAmt")
    if observation.total_amount != total:
        raise _fail("observed TotalAmt mismatch")

    raw_lines = _sequence(_member(raw, "Line"), "Line")
    has_subtotal = _object(raw_lines[-1], "last line").get("DetailType") == "SubTotalLineDetail"
    sales_lines = raw_lines[:-1] if has_subtotal else raw_lines
    if not 1 <= len(sales_lines) <= _MAX_SALES_LINES:
        raise _fail("one to three sales lines and optional subtotal are required")
    parsed_sales: list[tuple[str, Decimal, str]] = []
    for raw_sales in sales_lines:
        sales = _object(raw_sales, "SalesItem line")
        if sales.get("DetailType") != "SalesItemLineDetail":
            raise _fail("each economic line must be SalesItemLineDetail")
        line_id = _safe_id(_member(sales, "Id"), "Line.Id")
        line_net = _money(_member(sales, "Amount"), "Line.Amount")
        sales_detail = _object(_member(sales, "SalesItemLineDetail"),
                               "SalesItemLineDetail")
        tax_code = _safe_id(_member(_object(_member(sales_detail, "TaxCodeRef"),
                                            "TaxCodeRef"), "value"),
                            "TaxCodeRef.value")
        parsed_sales.append((line_id, line_net, tax_code))
    if len({line_id for line_id, _, _ in parsed_sales}) != len(parsed_sales):
        raise _fail("duplicate sales line identifiers are unsupported")
    net = sum((line_net for _, line_net, _ in parsed_sales), Decimal("0"))
    tax_code = parsed_sales[0][2]
    if any(line_tax_code != tax_code for _, _, line_tax_code in parsed_sales):
        raise _fail("mixed sales TaxCodeRef values are unsupported")
    if has_subtotal:
        subtotal = _object(raw_lines[-1], "subtotal line")
        if subtotal.get("DetailType") != "SubTotalLineDetail":
            raise _fail("last line must be a terminal SubTotalLineDetail")
        subtotal_id = _safe_id(_member(subtotal, "Id"), "subtotal Line.Id")
        if subtotal_id in {line_id for line_id, _, _ in parsed_sales}:
            raise _fail("subtotal identifier duplicates a sales line identifier")
        if _money(_member(subtotal, "Amount"), "subtotal Amount") != net:
            raise _fail("subtotal does not equal the sales-line sum")

    tax_detail = _object(_member(raw, "TxnTaxDetail"), "TxnTaxDetail")
    total_tax = _money(_member(tax_detail, "TotalTax"), "TotalTax")
    tax_lines = _sequence(_member(tax_detail, "TaxLine"), "TaxLine")
    if len(tax_lines) != 1:
        raise _fail("exactly one TaxLine is required")
    tax_line = _object(tax_lines[0], "TaxLine")
    tax_amount = _money(_member(tax_line, "Amount"), "TaxLine.Amount")
    if tax_line.get("DetailType") != "TaxLineDetail":
        raise _fail("TaxLine detail type is unsupported")
    detail = _object(_member(tax_line, "TaxLineDetail"), "TaxLineDetail")
    if detail.get("PercentBased") is not True:
        raise _fail("TaxLine PercentBased must be exact true")
    taxable = _money(_member(detail, "NetAmountTaxable"), "NetAmountTaxable")
    tax_rate_ref = _safe_id(_member(_object(_member(detail, "TaxRateRef"),
                                           "TaxRateRef"), "value"),
                            "TaxRateRef.value")
    rate = None
    if "TaxPercent" in detail:
        provider_percent = _decimal(_member(detail, "TaxPercent"), "TaxPercent")
        rate = _percent_rate(provider_percent)
        if _exact_product(taxable, rate) != tax_amount:
            raise _fail("TaxPercent does not reconcile exactly")
    if len(parsed_sales) > 1 and rate is None:
        raise _fail("multiple sales lines require exact TaxPercent")
    if taxable != net or tax_amount != total_tax or net + total_tax != total:
        raise _fail("invoice tax arithmetic does not reconcile exactly")

    lines = []
    for line_id, line_net, _ in parsed_sales:
        # Multi-line tax allocation is accepted only when the one explicit rate
        # produces an exact, two-decimal amount for every source sales line.
        line_tax = (total_tax if len(parsed_sales) == 1
                    else _derived_money(_exact_product(line_net, rate),
                                        "derived line tax"))
        line_gross = _derived_money(line_net + line_tax, "derived line gross")
        lines.append(AccountingLine(
            line_id=line_id, money=Money(line_gross, currency),
            tax=TaxBreakdown(line_net, line_tax, line_gross,
                             TaxAmountSemantics.EXCLUSIVE,
                             vat_code=tax_code, vat_rate=rate),
            provider_category_id=None,
            value_semantics=LineValueSemantics.EXCLUSIVE,
        ))
    if sum((line.tax.vat_amount for line in lines), Decimal("0")) != total_tax:
        raise _fail("per-line tax allocation does not reconcile")
    provenance = _provenance(observation, raw, import_run_id, "Invoice")
    source = SourceObservation(
        f"quickbooks:invoice:{observation.entity_id}:{observation.source_digest[:16]}",
        provenance, evidence_state=evidence_state,
    )
    provider_status = raw.get("EmailStatus", "")
    if provider_status != "":
        provider_status = _safe_id(provider_status, "EmailStatus")
    candidate = DocumentCandidate(
        document_id=observation.entity_id, business_id=observation.realm_id,
        connected_organisation_id=observation.credential_reference,
        document_type=DocumentType.INVOICE,
        issue_date=observation.transaction_date, due_date=observation.due_date,
        currency=currency, gross_amount=total, net_amount=net,
        vat_amount=total_tax, lines=tuple(lines), provider_status=provider_status,
        canonical_state=CanonicalDocumentState.UNKNOWN,
        canonical_state_reason="Q-S5A does not infer lifecycle from balance",
        economic_direction=EconomicDirection.RECEIVABLE,
        economic_event_id=(f"quickbooks-invoice-{observation.realm_id}-"
                           f"{observation.entity_id}"),
        provider_balance=(ProviderBalanceAssertions(balance=observation.balance)
                          if observation.balance is not None else None),
    )
    semantic = SemanticAdapterResult(
        source.observation_id, ADAPTER_VERSION,
        "one to three tax-exclusive same-code sales lines; subtotal non-economic",
        document_candidate=candidate,
        provider_assertions=(("Balance retained as corroboration only",)
                             if observation.balance is not None else ()),
    )
    document = normalise_document(observation=source, adapter_result=semantic)
    # TaxRateRef is deliberately retained only in the source/provenance evidence;
    # it is not an accounting/item category.
    return InvoiceAdapterResult(
        observation, source, semantic, document,
        observation.customer_reference_value)


def adapt_payment(observation: PaymentObservation, *, invoice: InvoiceAdapterResult,
                  binding: RealmBinding, import_run_id: str,
                  evidence_state: EvidenceState = EvidenceState.SELECTED
                  ) -> PaymentAdapterResult:
    """Map one exact Invoice allocation against its already-canonical invoice."""
    raw = _assert_observation(
        observation, PaymentObservation, evidence_state, binding)
    _safe_id(observation.customer_reference_value, "CustomerRef.value")
    _assert_linked_invoice_shape(invoice)
    try:
        replayed_invoice = adapt_invoice(
            invoice.source_observation, binding=binding,
            import_run_id=invoice.document.provenance.identity.import_run_id,
            evidence_state=invoice.observation.evidence_state,
        )
        _assert_matching_types(
            replayed_invoice, invoice, "linked invoice result integrity check failed")
        if replayed_invoice != invoice:
            raise _fail("linked invoice result integrity check failed")
    except QuickBooksAdapterError:
        raise
    except Exception:
        raise _fail("linked invoice result integrity check failed") from None
    document = invoice.document
    if observation.entity_id == document.document_id:
        raise _fail("payment and invoice identifiers must be distinct")
    if document.provenance.identity.provider is not AccountingProviderName.QUICKBOOKS:
        raise _fail("linked invoice provider mismatch")
    if document.business_id != observation.realm_id:
        raise _fail("payment and invoice business/realm mismatch")
    if document.connected_organisation_id != observation.credential_reference:
        raise _fail("payment and invoice connected-organisation mismatch")
    if document.provenance.identity.user_id != observation.user_id:
        raise _fail("payment and invoice user mismatch")
    if observation.customer_reference_value != invoice.customer_reference_value:
        raise _fail("payment and invoice customer mismatch")
    if observation.transaction_date is None or "TxnDate" not in raw:
        raise _fail("payment TxnDate is mandatory")
    currency = _currency(raw)
    if currency != document.currency:
        raise _fail("payment and invoice currency mismatch")
    total = _money(_member(raw, "TotalAmt"), "Payment.TotalAmt")
    unapplied = _money(_member(raw, "UnappliedAmt"), "Payment.UnappliedAmt")
    if observation.total_amount != total or observation.unapplied_amount != unapplied:
        raise _fail("observed payment totals mismatch")
    lines = _sequence(_member(raw, "Line"), "Payment.Line")
    if len(lines) != 1:
        raise _fail("exactly one Payment line is required")
    line = _object(lines[0], "Payment line")
    applied = _money(_member(line, "Amount"), "Payment.Line.Amount")
    links = _sequence(_member(line, "LinkedTxn"), "LinkedTxn")
    if len(links) != 1:
        raise _fail("exactly one Payment link is required")
    link = _object(links[0], "LinkedTxn")
    if link.get("TxnType") != "Invoice":
        raise _fail("only Invoice payment links are supported")
    linked_id = _safe_id(_member(link, "TxnId"), "LinkedTxn.TxnId")
    if linked_id != document.document_id:
        raise _fail("unknown or mismatched linked invoice id")
    if applied + unapplied != total:
        raise _fail("payment allocation arithmetic does not reconcile")
    provenance = _provenance(observation, raw, import_run_id, "Payment")
    payment = AccountingPayment(
        payment_id=observation.entity_id, business_id=document.business_id,
        payment_type=PaymentType.PAYMENT,
        occurred_on=observation.transaction_date, money=Money(total, currency),
        provenance=provenance, economic_event_id=document.economic_event_id,
        economic_direction=EconomicDirection.RECEIVABLE,
        unapplied_amount=unapplied,
    )
    allocation = AllocationEdge(
        allocation_id=f"quickbooks-payment-{observation.entity_id}-invoice-{linked_id}",
        business_id=document.business_id,
        economic_event_id=document.economic_event_id, currency=currency,
        payment_id=payment.payment_id, document_id=document.document_id,
        allocation_type=AllocationType.PAYMENT, amount=applied,
        effective_on=observation.transaction_date,
    )
    errors = validate_allocations(document, (allocation,), {payment.payment_id: payment})
    if errors:
        raise _fail("canonical allocation validation failed")
    return PaymentAdapterResult(payment, allocation)
