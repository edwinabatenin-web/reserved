"""Fail-closed provider-neutral normalisation.

Executable pipeline boundary::

    observe_provider_record()  -> SourceObservation      (raw provider record)
    adapt_observation()        -> SemanticAdapterResult  (synthetic translation)
    normalise_document()       -> AccountingDocument     (canonical, fail-closed)

Only an approved canonical object or rules-layer decision crosses the
accounting/tax boundary. Missing is never zero.
"""
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json

from .contracts import (
    AccountingDocument, AccountingLine, AccountingMethod, AccountingProviderName,
    AllocationEdge, AllocationType, AllowabilityDecision, CanonicalAccountingTaxInput,
    CanonicalDocumentState, DecisionAuthority, DocumentCandidate, DocumentType,
    EvidenceState, FxProvenance, Money, Provenance, RecognitionCandidate,
    RecognitionDecision, RecognitionDecisionOutcome, SemanticAdapterResult,
    SettlementState, SettlementSummary, SourceIdentity, SourceObservation,
    TaxAmountSemantics, TaxBreakdown,
)


class CanonicalQuarantineError(ValueError):
    """A provider record cannot safely enter the canonical evidence store."""


def _digest(payload):
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()


# ── Synthetic observation boundary ───────────────────────────────────────────

_SYNTHETIC_REQUIRED_FIELDS = (
    "provider_document_id", "provider_business_id", "provider_document_kind",
    "provider_currency", "provider_total",
)


def observe_provider_record(
    *,
    provider: str,
    raw_record: dict,
    user_id: str,
    connected_organisation_id: str,
    business_id: str,
    import_run_id: str,
    api_name: str,
    api_version: str,
    resource: str,
    record_id: str,
    retrieved_at: datetime,
    adapter_version: str,
    source_schema_id: str | None = None,
    required_fields: tuple[str, ...] = _SYNTHETIC_REQUIRED_FIELDS,
) -> SourceObservation:
    """Build an immutable observation of one raw provider record.

    ``source_record_digest`` is the digest of the *observed* representation only;
    ``source_fields`` records the observed provider field paths (never canonical
    keys). The raw payload is transient and is not retained here.
    """
    source_digest = _digest(raw_record)
    present = {key for key, value in raw_record.items() if value not in (None, "")}
    missing_fields = tuple(key for key in required_fields if key not in present)
    observation_id = f"{provider}:{record_id}:{source_digest[:16]}"
    provenance = Provenance(
        identity=SourceIdentity(
            user_id, AccountingProviderName(provider), connected_organisation_id,
            business_id, import_run_id,
        ),
        api_name=api_name,
        api_version=api_version,
        resource=resource,
        record_id=record_id,
        source_fields=tuple(sorted(raw_record)),
        retrieved_at=retrieved_at,
        adapter_version=adapter_version,
        source_record_digest=source_digest,
        source_schema_id=source_schema_id,
    )
    return SourceObservation(
        observation_id=observation_id,
        provenance=provenance,
        missing_fields=missing_fields,
    )


# ── Synthetic semantic adapter ───────────────────────────────────────────────

def _as_str(value):
    return None if value in (None, "") else str(value)


def _as_date(value):
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def _as_amount(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _as_enum(enum_cls, value):
    try:
        return enum_cls(value if value not in (None, "") else "unknown")
    except (ValueError, TypeError):
        return None


def _cash_candidate(raw_record, observation):
    raw_on = _as_date(raw_record.get("provider_cash_on"))
    raw_amt = _as_amount(raw_record.get("provider_cash_amt"))
    if raw_on is None and raw_amt is None:
        return None
    return RecognitionCandidate(raw_on, raw_amt, AccountingMethod.CASH, (observation.observation_id,))


def _accrual_candidate(raw_record, observation):
    raw_on = _as_date(raw_record.get("provider_accrual_on"))
    raw_amt = _as_amount(raw_record.get("provider_accrual_amt"))
    if raw_on is None and raw_amt is None:
        return None
    return RecognitionCandidate(raw_on, raw_amt, AccountingMethod.TRADITIONAL_ACCRUAL, (observation.observation_id,))


def _fx_from_raw(raw_record, observation):
    if not any(key in raw_record for key in (
        "provider_fx_rate", "provider_fx_base_amount", "provider_fx_base_currency",
    )):
        return None
    return FxProvenance(
        original_amount=_as_amount(raw_record.get("provider_fx_original_amount")) or Decimal("0"),
        original_currency=_as_str(raw_record.get("provider_fx_original_currency")) or "",
        base_amount=_as_amount(raw_record.get("provider_fx_base_amount")) or Decimal("0"),
        base_currency=_as_str(raw_record.get("provider_fx_base_currency")) or "",
        fx_rate=_as_amount(raw_record.get("provider_fx_rate")) or Decimal("0"),
        fx_rate_date=_as_date(raw_record.get("provider_fx_rate_date")),
        fx_source=_as_str(raw_record.get("provider_fx_source")) or "",
        rounding_method=_as_str(raw_record.get("provider_fx_rounding")) or "unspecified",
        conversion_method=_as_str(raw_record.get("provider_fx_conversion")) or "unspecified",
        observation_id=observation.observation_id,
    )


def _line_from_raw(line: dict) -> AccountingLine | None:
    line_id = _as_str(line.get("provider_line_id"))
    if not line_id:
        return None
    gross = _as_amount(line.get("provider_line_total"))
    if gross is None:
        return None
    net = _as_amount(line.get("provider_line_net"))
    vat = _as_amount(line.get("provider_line_tax"))
    semantics = _as_enum(TaxAmountSemantics, line.get("provider_tax_semantics")) or TaxAmountSemantics.UNKNOWN
    vat_rate = _as_amount(line.get("provider_vat_rate"))
    currency = (_as_str(line.get("provider_currency")) or "").upper()
    money = Money(gross, currency)
    tax = TaxBreakdown(net, vat, gross, semantics, line.get("provider_vat_code"), vat_rate)
    return AccountingLine(
        line_id=line_id,
        money=money,
        tax=tax,
        description=_as_str(line.get("provider_line_description")),
        provider_category_id=_as_str(line.get("provider_category")),
        provider_account_id=_as_str(line.get("provider_account")),
        property_allocation_id=_as_str(line.get("provider_property")),
        tracking_allocation_ids=tuple(line.get("provider_tracking") or ()),
    )


def adapt_observation(*, observation: SourceObservation, raw_record: dict) -> SemanticAdapterResult:
    """Synthetic semantic adapter: translate a raw record into candidate facts.

    This is a *synthetic* provider-neutral adapter used to prove the boundary.
    It never produces a final recognition or allowability decision and never
    retains raw provider objects.
    """
    document_id = _as_str(raw_record.get("provider_document_id"))
    business_id = _as_str(raw_record.get("provider_business_id"))
    document_type = _as_enum(DocumentType, raw_record.get("provider_document_kind"))
    currency = (_as_str(raw_record.get("provider_currency")) or "").upper()
    gross = _as_amount(raw_record.get("provider_total"))
    issue_date = _as_date(raw_record.get("provider_issued_on"))
    raw_lines = raw_record.get("provider_lines")
    lines = tuple(
        line for line in (_line_from_raw(item) for item in raw_lines)
        if line is not None
    ) if isinstance(raw_lines, list) else ()

    candidate = DocumentCandidate(
        document_id=document_id or "",
        business_id=business_id or "",
        document_type=document_type,
        issue_date=issue_date,
        currency=currency,
        gross_amount=gross,
        lines=lines,
        provider_status=_as_str(raw_record.get("provider_status_text")),
        amount_paid=_as_amount(raw_record.get("provider_paid_total")),
        due_date=_as_date(raw_record.get("provider_due_on")),
        document_number=_as_str(raw_record.get("provider_reference")),
        contact_name=_as_str(raw_record.get("provider_contact_name")),
        economic_event_id=_as_str(raw_record.get("provider_event_id")),
        cash_candidate=_cash_candidate(raw_record, observation),
        accrual_candidate=_accrual_candidate(raw_record, observation),
        fx=_fx_from_raw(raw_record, observation),
    )
    return SemanticAdapterResult(
        observation_id=observation.observation_id,
        adapter_version=observation.provenance.adapter_version,
        transformation="synthetic provider record to candidate facts",
        document_candidate=candidate,
        missing_facts=observation.missing_fields,
        provider_assertions=(("amount_paid=" + str(raw_record["provider_paid_total"]),)
            if raw_record.get("provider_paid_total") not in (None, "") else ()),
    )


# ── Provider status mapping (fail-closed) ────────────────────────────────────

_PROVIDER_STATUS_MAP = {
    "draft": CanonicalDocumentState.DRAFT,
    "issued": CanonicalDocumentState.ISSUED,
    "open": CanonicalDocumentState.OPEN,
}


def map_provider_status(status: str | None) -> CanonicalDocumentState:
    """Map a provider-reported status to a controlled canonical state.

    Unknown statuses fail closed to ``UNKNOWN``; they never silently map to an
    active, unpaid or settled state.
    """
    if status in (None, ""):
        return CanonicalDocumentState.UNKNOWN
    return _PROVIDER_STATUS_MAP.get(str(status).lower(), CanonicalDocumentState.UNKNOWN)


# ── Canonical normalisation ──────────────────────────────────────────────────

def normalise_document(*, observation: SourceObservation, adapter_result: SemanticAdapterResult) -> AccountingDocument:
    """Convert an observation + adapter result into a canonical document.

    Fails closed when the adapter result does not reference the observation,
    when required candidate facts are missing, or when line totals are
    inconsistent. It never invents a recognition candidate: cash/accrual
    candidates exist only if the adapter supplied them.
    """
    if not isinstance(observation, SourceObservation):
        raise CanonicalQuarantineError("normalisation requires a source observation")
    if not isinstance(adapter_result, SemanticAdapterResult):
        raise CanonicalQuarantineError("normalisation requires a semantic adapter result")
    if adapter_result.observation_id != observation.observation_id:
        raise CanonicalQuarantineError("adapter result does not reference the source observation")
    candidate = adapter_result.document_candidate
    if candidate is None:
        raise CanonicalQuarantineError("adapter result has no document candidate")
    if adapter_result.missing_facts:
        raise CanonicalQuarantineError("missing provider facts: " + ", ".join(adapter_result.missing_facts))

    if not candidate.document_id:
        raise CanonicalQuarantineError("missing document_id")
    if not candidate.business_id:
        raise CanonicalQuarantineError("missing business_id")
    if candidate.document_type is None:
        raise CanonicalQuarantineError("missing document_type")
    if not candidate.currency:
        raise CanonicalQuarantineError("missing currency")
    if candidate.gross_amount is None:
        raise CanonicalQuarantineError("missing gross_amount")
    if candidate.issue_date is None:
        raise CanonicalQuarantineError("missing issue_date")
    if not candidate.economic_event_id:
        raise CanonicalQuarantineError("missing economic_event_id")
    if not candidate.lines:
        raise CanonicalQuarantineError("missing lines")

    line_total = sum((line.money.original_amount for line in candidate.lines), Decimal("0"))
    if line_total != candidate.gross_amount:
        raise CanonicalQuarantineError("line gross amounts must equal document gross_amount")

    return AccountingDocument(
        document_id=candidate.document_id,
        business_id=candidate.business_id,
        document_type=candidate.document_type,
        issue_date=candidate.issue_date,
        currency=candidate.currency,
        gross_amount=candidate.gross_amount,
        lines=tuple(candidate.lines),
        provenance=observation.provenance,
        economic_event_id=candidate.economic_event_id,
        provider_status=candidate.provider_status or "",
        canonical_state=map_provider_status(candidate.provider_status),
        amount_paid=candidate.amount_paid,
        due_date=candidate.due_date,
        document_number=candidate.document_number,
        contact_name=candidate.contact_name,
        cash_candidate=candidate.cash_candidate,
        accrual_candidate=candidate.accrual_candidate,
        fx=candidate.fx,
    )


# ── Allocation validation and settlement ─────────────────────────────────────

_ALLOCATION_DIRECTION = {
    AllocationType.PAYMENT: Decimal("1"),
    AllocationType.CREDIT: Decimal("1"),
    AllocationType.WRITE_OFF: Decimal("1"),
    AllocationType.REFUND: Decimal("-1"),
}


def validate_allocations(document, allocations, payments=None) -> list[str]:
    """Return every invariant violation in an allocation set (empty == valid).

    Validates sign, references, business/event/currency compatibility, duplicate
    identity, duplicate payment application, reversal target existence,
    reversal-to-reversal, repeated reversal and reversal amount compatibility.
    When ``payments`` is supplied, cross-object payment compatibility is also
    checked. Reversal edges must reverse a compatible non-reversal edge of equal
    amount.
    """
    errors: list[str] = []
    by_id = {edge.allocation_id: edge for edge in allocations}
    seen_ids: set[str] = set()
    reversed_targets: set[str] = set()

    for edge in allocations:
        if edge.document_id != document.document_id:
            errors.append(f"allocation {edge.allocation_id} references a different document")
        if edge.business_id != document.business_id:
            errors.append(f"allocation {edge.allocation_id} references a different business")
        if edge.economic_event_id != document.economic_event_id:
            errors.append(f"allocation {edge.allocation_id} references a different economic event")
        if edge.currency != document.currency:
            errors.append(f"allocation {edge.allocation_id} has incompatible currency")
        if edge.allocation_id in seen_ids:
            errors.append(f"duplicate allocation identity: {edge.allocation_id}")
        seen_ids.add(edge.allocation_id)
        if edge.amount <= 0:
            errors.append(f"allocation {edge.allocation_id} must have a positive amount")

        if edge.allocation_type in (AllocationType.PAYMENT, AllocationType.REFUND):
            if not edge.payment_id:
                errors.append(f"allocation {edge.allocation_id} has no payment reference")
        elif edge.allocation_type in (AllocationType.CREDIT, AllocationType.WRITE_OFF):
            if edge.payment_id is not None:
                errors.append(f"allocation {edge.allocation_id} must not reference a payment")

        if edge.allocation_type is AllocationType.REVERSAL:
            target_id = edge.reverses_allocation_id
            if not target_id:
                errors.append(f"reversal {edge.allocation_id} has no target")
                continue
            target = by_id.get(target_id)
            if target is None:
                errors.append(f"reversal {edge.allocation_id} references a missing allocation")
                continue
            if target.allocation_type is AllocationType.REVERSAL:
                errors.append(f"reversal {edge.allocation_id} targets another reversal")
            if target.document_id != document.document_id:
                errors.append(f"reversal {edge.allocation_id} targets a different document")
            if target.amount != edge.amount:
                errors.append(f"reversal {edge.allocation_id} amount differs from its target")
            if target_id in reversed_targets:
                errors.append(f"allocation {target_id} is reversed more than once")
            reversed_targets.add(target_id)

    application_seen: set[tuple] = set()
    for edge in allocations:
        if edge.allocation_type in (AllocationType.PAYMENT, AllocationType.REFUND) and edge.payment_id:
            key = (edge.payment_id, edge.document_id)
            if key in application_seen:
                errors.append(f"payment {edge.payment_id} applied more than once to {edge.document_id}")
            application_seen.add(key)

    if payments is not None:
        for edge in allocations:
            if edge.allocation_type in (AllocationType.PAYMENT, AllocationType.REFUND) and edge.payment_id:
                payment = payments.get(edge.payment_id)
                if payment is None:
                    errors.append(f"allocation {edge.allocation_id} references an unknown payment")
                else:
                    if payment.business_id != document.business_id:
                        errors.append(f"allocation {edge.allocation_id} payment belongs to a different business")
                    if payment.economic_event_id != document.economic_event_id:
                        errors.append(f"allocation {edge.allocation_id} payment belongs to a different economic event")
                    if payment.money.original_currency != document.currency:
                        errors.append(f"allocation {edge.allocation_id} payment has incompatible currency")

    return errors


def settlement_summary(document, allocations, payments=None) -> SettlementSummary:
    """Compute settlement from validated allocation edges, failing closed.

    Direction is carried by ``allocation_type`` (never inferred from arbitrary
    signs): payments/credits/write-offs settle (reduce outstanding) and refunds
    un-settle (increase outstanding). Reversals neutralise their target edge.
    """
    errors = validate_allocations(document, allocations, payments)
    if errors:
        raise CanonicalQuarantineError("invalid allocations: " + "; ".join(errors))
    reversed_ids = {edge.reverses_allocation_id for edge in allocations
                    if edge.allocation_type is AllocationType.REVERSAL}
    total = Decimal("0")
    for edge in allocations:
        if edge.allocation_type is AllocationType.REVERSAL:
            continue
        if edge.allocation_id in reversed_ids:
            continue
        total += _ALLOCATION_DIRECTION[edge.allocation_type] * edge.amount
    return SettlementSummary(
        document.document_id,
        total,
        max(Decimal("0"), document.gross_amount - total),
        max(Decimal("0"), total - document.gross_amount),
    )


def derive_settlement_state(document, allocations, payments=None) -> SettlementState:
    summary = settlement_summary(document, allocations, payments)
    has_write_off = any(edge.allocation_type is AllocationType.WRITE_OFF for edge in allocations)
    if summary.overpayment_amount > 0:
        return SettlementState.OVERPAID
    if summary.outstanding_amount == 0:
        if summary.allocated_amount == 0:
            return SettlementState.UNPAID
        return SettlementState.WRITTEN_OFF if has_write_off else SettlementState.PAID
    return SettlementState.PART_PAID if summary.allocated_amount > 0 else SettlementState.UNPAID


# ── Recognition and allowability decisions ───────────────────────────────────

def select_recognition_candidate(document, method) -> RecognitionCandidate | None:
    if method is AccountingMethod.UNKNOWN:
        raise CanonicalQuarantineError("accounting method is unknown; recognition cannot be selected")
    return document.cash_candidate if method is AccountingMethod.CASH else document.accrual_candidate


def build_recognition_decision(
    *,
    decision_id: str,
    document: AccountingDocument,
    method: AccountingMethod,
    effective_from: date,
    effective_to: date | None = None,
    authority: DecisionAuthority = DecisionAuthority.RESERVED_RULE,
    policy_version: str,
) -> RecognitionDecision:
    """Build an explicit, evidence-linked recognition decision.

    Unknown method and missing candidates fail closed to ``UNABLE_TO_SELECT``;
    the decision never invents a recognised amount or date.
    """
    if method is AccountingMethod.UNKNOWN:
        return RecognitionDecision(
            decision_id, document.economic_event_id, document.business_id, method,
            effective_from, effective_to, RecognitionDecisionOutcome.UNABLE_TO_SELECT,
            authority, policy_version,
        )
    candidate = select_recognition_candidate(document, method)
    if candidate is None or candidate.amount is None or candidate.date is None:
        return RecognitionDecision(
            decision_id, document.economic_event_id, document.business_id, method,
            effective_from, effective_to, RecognitionDecisionOutcome.UNABLE_TO_SELECT,
            authority, policy_version, supporting_observation_ids=tuple(
                document.cash_candidate.source_observation_ids if document.cash_candidate else ()
            ) or tuple(document.accrual_candidate.source_observation_ids if document.accrual_candidate else ()),
        )
    outcome = RecognitionDecisionOutcome.CASH if method is AccountingMethod.CASH else RecognitionDecisionOutcome.ACCRUAL
    return RecognitionDecision(
        decision_id, document.economic_event_id, document.business_id, method,
        effective_from, effective_to, outcome, authority, policy_version,
        selected_candidate=candidate,
        recognised_amount=candidate.amount,
        recognised_date=candidate.date,
        supporting_observation_ids=candidate.source_observation_ids,
        permitted_uses=("tax_timing",),
        prohibited_uses=("allowability", "ownership"),
    )


def build_canonical_tax_input(
    *,
    input_id: str,
    purpose: str,
    scope: str,
    document: AccountingDocument,
    recognition_decision: RecognitionDecision,
    tax_year: str,
    allowability: AllowabilityDecision | None = None,
    ownership_adjustment: Decimal | None = None,
    policy_version: str,
) -> CanonicalAccountingTaxInput:
    """Produce the only approved synthetic accounting-to-tax input.

    Refuses to produce an input unless the recognition decision selected a
    candidate, and refuses cross-business/cross-event decisions.
    """
    if recognition_decision.outcome not in (
        RecognitionDecisionOutcome.CASH,
        RecognitionDecisionOutcome.ACCRUAL,
    ):
        raise CanonicalQuarantineError("cannot produce a canonical tax input without a selected recognition decision")
    if recognition_decision.recognised_amount is None or recognition_decision.recognised_date is None:
        raise CanonicalQuarantineError("recognition decision has no recognised amount or date")
    if recognition_decision.economic_event_id != document.economic_event_id:
        raise CanonicalQuarantineError("recognition decision belongs to a different economic event")
    if recognition_decision.business_id != document.business_id:
        raise CanonicalQuarantineError("recognition decision belongs to a different business")

    return CanonicalAccountingTaxInput(
        input_id=input_id,
        purpose=purpose,
        scope=scope,
        business_id=document.business_id,
        economic_event_id=document.economic_event_id,
        tax_year=tax_year,
        recognised_amount=recognition_decision.recognised_amount,
        recognised_date=recognition_decision.recognised_date,
        classification="turnover" if document.gross_amount >= 0 else "credit",
        currency=document.currency,
        base_currency=document.fx.base_currency if document.fx else document.currency,
        evidence_observation_ids=recognition_decision.supporting_observation_ids,
        recognition_decision_id=recognition_decision.decision_id,
        allowability_decision_id=allowability.decision_id if allowability else None,
        policy_version=policy_version,
        ownership_adjustment=ownership_adjustment,
        allowability=allowability,
        permitted_uses=("tax_estimate",),
        prohibited_uses=("settlement", "write_back"),
    )


# ── Effective-period overlap validation ──────────────────────────────────────

def validate_effective_period_records(records, *, subject_attr="business_id") -> list[str]:
    """Reject contradictory overlapping effective periods for the same subject.

    Legitimate succession (``effective_to == next effective_from``) is permitted.
    ``records`` must be objects exposing ``subject_attr``, ``effective_from`` and
    ``effective_to``.
    """
    errors: list[str] = []
    grouped: dict[str, list] = {}
    for record in records:
        grouped.setdefault(getattr(record, subject_attr), []).append(record)
    for subject, group in grouped.items():
        ordered = sorted(group, key=lambda r: r.effective_from)
        for i, current in enumerate(ordered):
            for later in ordered[i + 1:]:
                if later.effective_from < (current.effective_to or later.effective_from):
                    if current.effective_to != later.effective_from:
                        errors.append(f"overlapping effective periods for {subject}: {current.effective_from}..{current.effective_to} and {later.effective_from}..{later.effective_to}")
                if later.effective_from == current.effective_from:
                    errors.append(f"duplicate effective period start for {subject}: {current.effective_from}")
    return errors
