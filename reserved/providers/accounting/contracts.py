"""Provider-neutral accounting evidence contracts.

Enforced pipeline boundary::

    raw provider record
        -> SourceObservation        (immutable observed provider record)
        -> SemanticAdapterResult    (translated candidate facts; no decisions)
        -> canonical accounting objects (documents, payments, allocations)
        -> RecognitionDecision / AllowabilityDecision
        -> CanonicalAccountingTaxInput (only approved synthetic boundary)

Raw provider records never enter tax calculations. Missing is never zero; a
provider assertion is never settlement truth; a provider category/status is
never a tax decision.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class ValueEnum(str, Enum):
    pass


class AccountingProviderName(ValueEnum):
    FREEAGENT = "freeagent"; XERO = "xero"; QUICKBOOKS = "quickbooks"


class BusinessType(ValueEnum):
    TRADE = "trade"; UK_PROPERTY = "uk_property"; FOREIGN_PROPERTY = "foreign_property"
    UNSUPPORTED = "unsupported"; UNKNOWN = "unknown"


class AccountingMethod(ValueEnum):
    CASH = "cash"; TRADITIONAL_ACCRUAL = "traditional_accrual"; UNKNOWN = "unknown"


class MtdUpdatePeriodBasis(ValueEnum):
    STANDARD_TAX_YEAR = "standard_tax_year"; CALENDAR = "calendar"; UNKNOWN = "unknown"


class DocumentType(ValueEnum):
    INVOICE = "invoice"; BILL = "bill"; CREDIT_NOTE = "credit_note"
    SALES_RECEIPT = "sales_receipt"; REFUND = "refund"; WRITE_OFF = "write_off"; OTHER = "other"


class PaymentType(ValueEnum):
    PAYMENT = "payment"; RECEIPT = "receipt"; REFUND = "refund"; OVERPAYMENT = "overpayment"


class AllocationType(ValueEnum):
    PAYMENT = "payment"; CREDIT = "credit"; REFUND = "refund"; WRITE_OFF = "write_off"; REVERSAL = "reversal"


class VatRegistrationState(ValueEnum):
    REGISTERED = "registered"; NOT_REGISTERED = "not_registered"; UNKNOWN = "unknown"


class TaxAmountSemantics(ValueEnum):
    INCLUSIVE = "inclusive"; EXCLUSIVE = "exclusive"; NOT_APPLICABLE = "not_applicable"; UNKNOWN = "unknown"


class OwnershipConfidence(ValueEnum):
    CONFIRMED = "confirmed"; ESTIMATED = "estimated"; UNKNOWN = "unknown"


class AllowabilityOutcome(ValueEnum):
    ALLOWABLE = "allowable"; DISALLOWABLE = "disallowable"; MIXED_APPORTIONED = "mixed_apportioned"
    ADJUSTMENT_REQUIRED = "adjustment_required"; INSUFFICIENT_FACTS = "insufficient_facts"
    UNSUPPORTED = "unsupported"; UNRESOLVED = "unresolved"


class DecisionAuthority(ValueEnum):
    PROVIDER_ASSERTION = "provider_assertion"; RESERVED_RULE = "reserved_rule"
    CUSTOMER_CONFIRMATION = "customer_confirmation"; ADVISER_ADJUSTMENT = "adviser_adjustment"


class CorrectionLifecycle(ValueEnum):
    NONE = "none"; VOIDED = "voided"; DELETED = "deleted"; CREDITED = "credited"
    REFUNDED = "refunded"; REVERSED = "reversed"; RECLASSIFIED = "reclassified"
    UNKNOWN = "unknown"


class EvidenceState(ValueEnum):
    SELECTED = "selected"; CORROBORATING = "corroborating"; SUPERSEDED = "superseded"
    EXCLUDED = "excluded"; CONFLICTING = "conflicting"; UNRESOLVED = "unresolved"


class CompletenessState(ValueEnum):
    COMPLETE = "complete"; INCOMPLETE = "incomplete"; UNKNOWN = "unknown"; NOT_APPLICABLE = "not_applicable"


class UncertaintyKind(ValueEnum):
    MISSING = "missing"; STALE = "stale"; CONFLICTING = "conflicting"
    INCOMPLETE = "incomplete"; UNSUPPORTED = "unsupported"


# Controlled Reserved dimensions kept distinct from raw provider text.

class CanonicalDocumentState(ValueEnum):
    DRAFT = "draft"; ISSUED = "issued"; OPEN = "open"
    QUARANTINED = "quarantined"; UNKNOWN = "unknown"


class SettlementState(ValueEnum):
    UNPAID = "unpaid"; PART_PAID = "part_paid"; PAID = "paid"; OVERPAID = "overpaid"
    WRITTEN_OFF = "written_off"; UNKNOWN = "unknown"


class RecognitionDecisionOutcome(ValueEnum):
    CASH = "cash"; ACCRUAL = "accrual"; UNABLE_TO_SELECT = "unable_to_select"; UNSUPPORTED = "unsupported"


class OwnershipSubject(ValueEnum):
    BUSINESS = "business"; PROPERTY = "property"; OTHER = "other"


class VatCategory(ValueEnum):
    STANDARD = "standard"; REDUCED = "reduced"; ZERO_RATED = "zero_rated"
    EXEMPT = "exempt"; OUTSIDE_SCOPE = "outside_scope"; UNKNOWN = "unknown"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _finite(value):
    return value is None or (isinstance(value, Decimal) and value.is_finite())


def validate_effective_period(effective_from, effective_to):
    """Return an error string when the period is invalid, else ``None``."""
    if effective_to is not None and effective_to < effective_from:
        return "effective_to precedes effective_from"
    return None


@dataclass(frozen=True)
class ProviderCapabilities:
    businesses: bool = True
    invoices: bool = True
    expenses: bool = True
    bank_transactions: bool = True
    categories: bool = True
    webhooks: bool = False


@dataclass(frozen=True)
class SourceIdentity:
    user_id: str
    provider: AccountingProviderName
    connected_organisation_id: str
    business_id: str
    import_run_id: str


@dataclass(frozen=True)
class Provenance:
    identity: SourceIdentity
    api_name: str
    api_version: str
    resource: str
    record_id: str
    source_fields: tuple[str, ...]
    retrieved_at: datetime
    adapter_version: str
    source_record_digest: str
    source_definitions: tuple[str, ...] = ()
    source_schema_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    effective_at: datetime | None = None
    transformation: str | None = None
    rounding: str | None = None


@dataclass(frozen=True)
class SourceObservation:
    """Immutable observation of one raw provider record.

    ``provenance.source_fields`` records the *provider* field paths actually
    observed; ``provenance.source_record_digest`` is the integrity digest of the
    observed representation (not of any later canonical transformation). The raw
    payload itself is transient at the adapter boundary; only the digest, the
    retained field paths and a separately governed ``raw_evidence_reference``
    (never the payload) are kept here.
    """

    observation_id: str
    provenance: Provenance
    evidence_state: EvidenceState = EvidenceState.UNRESOLVED
    evidence_reason: str | None = None
    competing_observation_ids: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
    raw_evidence_reference: str | None = None


@dataclass(frozen=True)
class SemanticAdapterResult:
    """Provider-neutral translated candidate facts.

    This is *not* a canonical object and *not* a decision. It references the
    exact source observation, records the adapter version/transformation, and
    carries provider assertions separately from Reserved decisions. It may flag
    missing, unsupported and conflicting facts but never resolves them.
    """

    observation_id: str
    adapter_version: str
    transformation: str
    document_candidate: "DocumentCandidate | None" = None
    missing_facts: tuple[str, ...] = ()
    unsupported_facts: tuple[str, ...] = ()
    conflicting_facts: tuple[str, ...] = ()
    provider_assertions: tuple[str, ...] = ()


@dataclass(frozen=True)
class DocumentCandidate:
    """Translated, provider-neutral document facts emitted by a semantic adapter.

    Every fact is a candidate; nothing here is a final recognition or
    allowability decision. ``None`` means the fact was not supplied (missing),
    never zero.
    """

    document_id: str
    business_id: str
    document_type: DocumentType
    issue_date: date | None
    currency: str
    gross_amount: Decimal | None
    lines: tuple["AccountingLine", ...] = ()
    provider_status: str | None = None
    amount_paid: Decimal | None = None
    due_date: date | None = None
    document_number: str | None = None
    contact_name: str | None = None
    economic_event_id: str | None = None
    cash_candidate: "RecognitionCandidate | None" = None
    accrual_candidate: "RecognitionCandidate | None" = None
    fx: "FxProvenance | None" = None


@dataclass(frozen=True)
class FxProvenance:
    original_amount: Decimal
    original_currency: str
    base_amount: Decimal
    base_currency: str
    fx_rate: Decimal
    fx_rate_date: date
    fx_source: str
    rounding_method: str
    conversion_method: str
    observation_id: str

    def __post_init__(self):
        if not _finite(self.fx_rate) or not _finite(self.original_amount) or not _finite(self.base_amount):
            raise ValueError("FX amounts and rate must be finite decimals")
        if not self.original_currency or not self.base_currency:
            raise ValueError("FX conversion requires original and base currency identity")
        if self.original_currency == self.base_currency:
            raise ValueError("FX conversion requires distinct original and base currencies")
        if self.fx_rate <= 0:
            raise ValueError("FX rate must be positive")
        if self.fx_rate_date is None:
            raise ValueError("FX conversion requires a rate date")
        if not self.fx_source:
            raise ValueError("FX conversion requires a source")


@dataclass(frozen=True)
class EffectiveDatedAccountingMethod:
    business_id: str
    method: AccountingMethod
    effective_from: date
    effective_to: date | None = None
    evidence_observation_ids: tuple[str, ...] = ()

    def __post_init__(self):
        period_error = validate_effective_period(self.effective_from, self.effective_to)
        if period_error:
            raise ValueError(period_error)


@dataclass(frozen=True)
class MtdPeriodConfiguration:
    business_id: str
    basis: MtdUpdatePeriodBasis
    effective_from: date
    effective_to: date | None = None

    def __post_init__(self):
        period_error = validate_effective_period(self.effective_from, self.effective_to)
        if period_error:
            raise ValueError(period_error)


@dataclass(frozen=True)
class VatRegistrationPeriod:
    state: VatRegistrationState
    effective_from: date
    effective_to: date | None = None
    scheme: str | None = None
    basis: str | None = None

    def __post_init__(self):
        period_error = validate_effective_period(self.effective_from, self.effective_to)
        if period_error:
            raise ValueError(period_error)


@dataclass(frozen=True)
class Money:
    original_amount: Decimal
    original_currency: str
    base_amount: Decimal | None = None
    base_currency: str | None = None
    fx_rate: Decimal | None = None
    fx_rate_date: date | None = None
    fx_source: str | None = None
    rounding_method: str | None = None
    conversion_method: str | None = None

    def __post_init__(self):
        fx = (self.base_amount, self.base_currency, self.fx_rate, self.fx_rate_date, self.fx_source)
        if any(v is not None for v in fx) and not all(v is not None for v in fx):
            raise ValueError("FX conversion requires base amount/currency, rate, rate date and source")
        if not _finite(self.original_amount) or not _finite(self.base_amount) or not _finite(self.fx_rate):
            raise ValueError("money amounts and FX rate must be finite decimals")
        if not self.original_currency:
            raise ValueError("money requires an original currency")
        if self.base_currency is not None and self.base_currency == self.original_currency:
            raise ValueError("base currency must differ from original currency")


@dataclass(frozen=True)
class TaxBreakdown:
    net_amount: Decimal | None
    vat_amount: Decimal | None
    gross_amount: Decimal
    semantics: TaxAmountSemantics
    vat_code: str | None = None
    vat_rate: Decimal | None = None

    def __post_init__(self):
        for value in (self.net_amount, self.vat_amount, self.gross_amount):
            if value is not None and not _finite(value):
                raise ValueError("tax amounts must be finite decimals")
        if self.net_amount is not None and self.vat_amount is not None:
            if self.net_amount + self.vat_amount != self.gross_amount:
                raise ValueError("net_amount + vat_amount must equal gross_amount")
        if self.semantics is TaxAmountSemantics.NOT_APPLICABLE:
            if self.vat_amount not in (None, Decimal("0")):
                raise ValueError("not-applicable VAT semantics must not carry a non-zero VAT amount")
        if self.vat_rate is not None:
            if not _finite(self.vat_rate) or self.vat_rate < 0:
                raise ValueError("vat_rate must be a non-negative finite decimal")


@dataclass(frozen=True)
class OwnershipEvidence:
    subject_id: str
    subject_type: OwnershipSubject
    share: Decimal | None
    confidence: OwnershipConfidence
    effective_from: date
    effective_to: date | None = None
    source_observation_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if self.share is not None and not Decimal("0") <= self.share <= Decimal("1"):
            raise ValueError("ownership share must be between zero and one")
        if self.confidence is OwnershipConfidence.UNKNOWN and self.share is not None:
            raise ValueError("unknown ownership must not imply a share")
        if self.share is not None and not _finite(self.share):
            raise ValueError("ownership share must be a finite decimal")
        period_error = validate_effective_period(self.effective_from, self.effective_to)
        if period_error:
            raise ValueError(period_error)


@dataclass(frozen=True)
class AccountingLine:
    line_id: str
    money: Money
    tax: TaxBreakdown
    description: str | None = None
    provider_category_id: str | None = None
    provider_account_id: str | None = None
    property_allocation_id: str | None = None
    tracking_allocation_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecognitionCandidate:
    date: date | None
    amount: Decimal | None
    basis: AccountingMethod
    source_observation_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if self.amount is not None and not _finite(self.amount):
            raise ValueError("recognition candidate amount must be a finite decimal")


@dataclass(frozen=True)
class AccountingDocument:
    document_id: str
    business_id: str
    document_type: DocumentType
    issue_date: date
    currency: str
    gross_amount: Decimal
    lines: tuple[AccountingLine, ...]
    provenance: Provenance
    economic_event_id: str
    provider_status: str  # raw provider status, preserved as evidence (unrestricted)
    canonical_state: CanonicalDocumentState = CanonicalDocumentState.UNKNOWN
    settlement_state: SettlementState = SettlementState.UNKNOWN
    correction_lifecycle: CorrectionLifecycle = CorrectionLifecycle.NONE
    amount_paid: Decimal | None = None  # untrusted provider assertion, never settlement truth
    due_date: date | None = None
    document_number: str | None = None
    contact_name: str | None = None
    cash_candidate: RecognitionCandidate | None = None
    accrual_candidate: RecognitionCandidate | None = None
    replaces_document_id: str | None = None
    evidence_state: EvidenceState = EvidenceState.UNRESOLVED
    fx: FxProvenance | None = None

    def __post_init__(self):
        if not _finite(self.gross_amount):
            raise ValueError("document gross_amount must be a finite decimal")


# Kept as an alias only for compatibility. Prefer ``AccountingDocument``: the
# canonical document is no longer an "invoice"-only shape.
AccountingInvoice = AccountingDocument


@dataclass(frozen=True)
class AccountingPayment:
    payment_id: str
    business_id: str
    payment_type: PaymentType
    occurred_on: date
    money: Money
    provenance: Provenance
    economic_event_id: str
    correction_lifecycle: CorrectionLifecycle = CorrectionLifecycle.NONE


@dataclass(frozen=True)
class AllocationEdge:
    allocation_id: str
    business_id: str
    economic_event_id: str
    currency: str
    payment_id: str | None
    document_id: str
    allocation_type: AllocationType
    amount: Decimal  # non-negative magnitude; direction is carried by allocation_type
    effective_on: date
    reverses_allocation_id: str | None = None

    def __post_init__(self):
        if not _finite(self.amount) or self.amount < 0:
            raise ValueError("allocation amount must be a non-negative finite decimal")


@dataclass(frozen=True)
class SettlementSummary:
    document_id: str
    allocated_amount: Decimal
    outstanding_amount: Decimal
    overpayment_amount: Decimal


@dataclass(frozen=True)
class AllowabilityDecision:
    decision_id: str
    outcome: AllowabilityOutcome
    authority: DecisionAuthority
    decided_at: datetime
    reason: str
    allowable_fraction: Decimal | None = None
    provider_assertion: str | None = None
    source_observation_ids: tuple[str, ...] = ()

    def __post_init__(self):
        if self.outcome is AllowabilityOutcome.MIXED_APPORTIONED:
            if self.allowable_fraction is None or not Decimal("0") <= self.allowable_fraction <= Decimal("1"):
                raise ValueError("mixed/apportioned decisions require a fraction between zero and one")


@dataclass(frozen=True)
class RecognitionDecision:
    decision_id: str
    economic_event_id: str
    business_id: str
    method: AccountingMethod
    effective_from: date
    effective_to: date | None
    outcome: RecognitionDecisionOutcome
    authority: DecisionAuthority
    policy_version: str
    selected_candidate: RecognitionCandidate | None = None
    recognised_amount: Decimal | None = None
    recognised_date: date | None = None
    supporting_observation_ids: tuple[str, ...] = ()
    uncertainties: tuple["Uncertainty", ...] = ()
    permitted_uses: tuple[str, ...] = ()
    prohibited_uses: tuple[str, ...] = ()

    def __post_init__(self):
        period_error = validate_effective_period(self.effective_from, self.effective_to)
        if period_error:
            raise ValueError(period_error)
        if self.method is AccountingMethod.UNKNOWN and self.outcome in (
            RecognitionDecisionOutcome.CASH,
            RecognitionDecisionOutcome.ACCRUAL,
        ):
            raise ValueError("unknown accounting method cannot select cash or accrual")
        if self.outcome in (RecognitionDecisionOutcome.CASH, RecognitionDecisionOutcome.ACCRUAL):
            if self.selected_candidate is None:
                raise ValueError("a selected recognition outcome requires a selected candidate")
        if self.recognised_amount is not None and not _finite(self.recognised_amount):
            raise ValueError("recognised_amount must be a finite decimal")


@dataclass(frozen=True)
class Completeness:
    record_freshness: CompletenessState
    retrieval: CompletenessState
    bookkeeping: CompletenessState
    reconciliation: CompletenessState
    reason: str | None = None


@dataclass(frozen=True)
class Uncertainty:
    kind: UncertaintyKind
    field: str
    reason: str
    affected_identity: str | None = None
    minimum_effect: Decimal | None = None
    maximum_effect: Decimal | None = None
    competing_observation_ids: tuple[str, ...] = ()

    def __post_init__(self):
        for value in (self.minimum_effect, self.maximum_effect):
            if value is not None and not _finite(value):
                raise ValueError("uncertainty bounds must be finite decimals")
        if self.minimum_effect is not None or self.maximum_effect is not None:
            if self.minimum_effect is None or self.maximum_effect is None:
                raise ValueError("uncertainty range requires both minimum and maximum effect")
            if self.minimum_effect > self.maximum_effect:
                raise ValueError("uncertainty minimum_effect must not exceed maximum_effect")
        if self.kind is UncertaintyKind.CONFLICTING and not self.competing_observation_ids:
            raise ValueError("conflicting uncertainty requires competing observation references")


@dataclass(frozen=True)
class CanonicalAccountingEvent:
    economic_event_id: str
    business_id: str
    document_ids: tuple[str, ...] = ()
    payment_ids: tuple[str, ...] = ()
    evidence_observation_ids: tuple[str, ...] = ()
    evidence_state: EvidenceState = EvidenceState.UNRESOLVED
    evidence_reason: str | None = None
    competing_observation_ids: tuple[str, ...] = ()
    uncertainties: tuple[Uncertainty, ...] = ()


@dataclass(frozen=True)
class CanonicalAccountingTaxInput:
    """Approved synthetic accounting-to-tax boundary.

    Only this object crosses the accounting/tax boundary, and only when it was
    produced from a valid canonical event, recognition decision and allowability
    decision with adequate ownership/VAT/FX facts. It is not exposed through any
    route, persistence model, API or the production tax engine in this task.
    """

    input_id: str
    purpose: str
    scope: str
    business_id: str
    economic_event_id: str
    tax_year: str
    recognised_amount: Decimal
    recognised_date: date
    classification: str
    currency: str
    base_currency: str
    evidence_observation_ids: tuple[str, ...]
    recognition_decision_id: str
    allowability_decision_id: str | None
    policy_version: str
    ownership_adjustment: Decimal | None = None
    allowability: AllowabilityDecision | None = None
    uncertainty: Uncertainty | None = None
    permitted_uses: tuple[str, ...] = ()
    prohibited_uses: tuple[str, ...] = ()

    def __post_init__(self):
        if not _finite(self.recognised_amount):
            raise ValueError("canonical tax input recognised_amount must be a finite decimal")


@dataclass(frozen=True)
class AccountingEntry:
    """Deprecated flattened legacy model.

    This model collapses provider identity, document/payment relationships and
    canonical state. It must never be used as calculation evidence; new code must
    use SourceObservation + SemanticAdapterResult + canonical objects.
    """

    provider: AccountingProviderName
    external_business_id: str
    external_entry_id: str
    occurred_on: date
    currency: str
    amount: Decimal
    direction: str
    entry_type: str
    description: str | None = None
    category_id: str | None = None
    invoice_id: str | None = None
    source_updated_at: datetime | None = None


@dataclass(frozen=True)
class AccountingBusiness:
    provider: AccountingProviderName
    external_business_id: str
    name: str
    currency: str
    country_code: str | None = None
    business_type: BusinessType = BusinessType.UNKNOWN
    accounting_methods: tuple[EffectiveDatedAccountingMethod, ...] = ()
    mtd_period_configurations: tuple[MtdPeriodConfiguration, ...] = ()
    vat_history: tuple[VatRegistrationPeriod, ...] = ()


@dataclass(frozen=True)
class SyncPage:
    records: tuple[object, ...]
    next_cursor: str | None
    source_watermark: datetime | None = None


@dataclass(frozen=True)
class SyncStatus:
    provider: AccountingProviderName
    external_business_id: str
    last_success_at: datetime | None
    next_cursor: str | None
    last_error_code: str | None = None
    requires_reauthorisation: bool = False
    completeness: Completeness | None = None

