"""Provider-neutral accounting evidence contracts.

Raw provider payloads stop at SourceObservation. Only canonical events and
rules-layer decisions may be consumed by the tax engine. Missing is never zero.
"""
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


class LifecycleState(ValueEnum):
    ACTIVE = "active"; VOIDED = "voided"; DELETED = "deleted"; REVERSED = "reversed"
    REFUNDED = "refunded"; WRITTEN_OFF = "written_off"; RECLASSIFIED = "reclassified"


class EvidenceState(ValueEnum):
    SELECTED = "selected"; CORROBORATING = "corroborating"; SUPERSEDED = "superseded"
    EXCLUDED = "excluded"; CONFLICTING = "conflicting"; UNRESOLVED = "unresolved"


class CompletenessState(ValueEnum):
    COMPLETE = "complete"; INCOMPLETE = "incomplete"; UNKNOWN = "unknown"; NOT_APPLICABLE = "not_applicable"


class UncertaintyKind(ValueEnum):
    MISSING = "missing"; STALE = "stale"; CONFLICTING = "conflicting"
    INCOMPLETE = "incomplete"; UNSUPPORTED = "unsupported"


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
    created_at: datetime | None = None
    updated_at: datetime | None = None
    effective_at: datetime | None = None
    transformation: str | None = None
    rounding: str | None = None


@dataclass(frozen=True)
class SourceObservation:
    provenance: Provenance
    payload_digest: str
    evidence_state: EvidenceState = EvidenceState.UNRESOLVED
    evidence_reason: str | None = None
    competing_observation_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class EffectiveDatedAccountingMethod:
    business_id: str
    method: AccountingMethod
    effective_from: date
    effective_to: date | None = None
    evidence_observation_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class MtdPeriodConfiguration:
    business_id: str
    basis: MtdUpdatePeriodBasis
    effective_from: date
    effective_to: date | None = None


@dataclass(frozen=True)
class VatRegistrationPeriod:
    state: VatRegistrationState
    effective_from: date
    effective_to: date | None = None
    scheme: str | None = None
    basis: str | None = None


@dataclass(frozen=True)
class Money:
    original_amount: Decimal
    original_currency: str
    base_amount: Decimal | None = None
    base_currency: str | None = None
    fx_rate: Decimal | None = None
    fx_rate_date: date | None = None
    fx_source: str | None = None

    def __post_init__(self):
        fx = (self.base_amount, self.base_currency, self.fx_rate, self.fx_rate_date, self.fx_source)
        if any(v is not None for v in fx) and not all(v is not None for v in fx):
            raise ValueError("FX conversion requires base amount/currency, rate, rate date and source")


@dataclass(frozen=True)
class TaxBreakdown:
    net_amount: Decimal | None
    vat_amount: Decimal | None
    gross_amount: Decimal
    semantics: TaxAmountSemantics
    vat_code: str | None = None
    vat_rate: Decimal | None = None

    def __post_init__(self):
        if self.net_amount is not None and self.vat_amount is not None:
            if self.net_amount + self.vat_amount != self.gross_amount:
                raise ValueError("net_amount + vat_amount must equal gross_amount")


@dataclass(frozen=True)
class OwnershipEvidence:
    allocation_id: str
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
    status: str
    amount_paid: Decimal | None = None  # untrusted provider assertion, never settlement truth
    due_date: date | None = None
    document_number: str | None = None
    contact_name: str | None = None
    cash_candidate: RecognitionCandidate | None = None
    accrual_candidate: RecognitionCandidate | None = None
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE
    replaces_document_id: str | None = None
    evidence_state: EvidenceState = EvidenceState.UNRESOLVED


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
    lifecycle_state: LifecycleState = LifecycleState.ACTIVE


@dataclass(frozen=True)
class AllocationEdge:
    allocation_id: str
    payment_id: str | None
    document_id: str
    allocation_type: AllocationType
    amount: Decimal
    effective_on: date
    reverses_allocation_id: str | None = None


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
    minimum_effect: Decimal | None = None
    maximum_effect: Decimal | None = None
    competing_observation_ids: tuple[str, ...] = ()


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
class AccountingEntry:
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

