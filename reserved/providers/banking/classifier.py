"""
Transaction classification engine for Reserved™.

Architecture
------------
Designed to support AI-assisted classification as a future drop-in.
To add an AI classifier: implement ClassifierBase, then insert it
into the TransactionPipeline.classifiers list ahead of RulesClassifier.
The pipeline stops at the first result whose confidence meets the
classifier's threshold, so the AI classifier can override or fall
through to the rules layer.

Rule evaluation order matters — rules are checked top-to-bottom and
the first match wins. Higher-confidence, more-specific rules are listed
first. The catch-all personal-spending rule sits last.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


# ── Categories ───────────────────────────────────────────────────────────────

class TransactionCategory(str, Enum):
    # Income (potentially taxable)
    FREELANCE_INCOME = "freelance_income"
    SALARY = "salary"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    RENTAL_INCOME = "rental_income"
    TAX_REFUND = "tax_refund"

    # Tax payments
    TAX_PAYMENT = "tax_payment"

    # Neutral transfers
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"

    # Business expenses (potentially deductible)
    BUSINESS_EXPENSE = "business_expense"
    SUBSCRIPTION = "subscription"

    # Personal / non-deductible
    LOAN_REPAYMENT = "loan_repayment"
    MORTGAGE = "mortgage"
    RENT_PAYMENT = "rent_payment"
    UTILITY = "utility"
    PERSONAL_SPENDING = "personal_spending"

    # Unresolved
    UNKNOWN = "unknown"


# Tax relevance for UK sole-trader context
TAX_RELEVANT: dict[TransactionCategory, bool] = {
    TransactionCategory.FREELANCE_INCOME: True,
    TransactionCategory.SALARY: True,
    TransactionCategory.DIVIDEND: True,
    TransactionCategory.INTEREST: True,
    TransactionCategory.RENTAL_INCOME: True,
    TransactionCategory.TAX_REFUND: True,
    TransactionCategory.TAX_PAYMENT: True,
    TransactionCategory.BUSINESS_EXPENSE: True,
    TransactionCategory.SUBSCRIPTION: True,  # potentially deductible
    TransactionCategory.TRANSFER_IN: False,
    TransactionCategory.TRANSFER_OUT: False,
    TransactionCategory.LOAN_REPAYMENT: False,
    TransactionCategory.MORTGAGE: False,
    TransactionCategory.RENT_PAYMENT: False,
    TransactionCategory.UTILITY: False,
    TransactionCategory.PERSONAL_SPENDING: False,
    TransactionCategory.UNKNOWN: False,
}

CATEGORY_LABELS: dict[TransactionCategory, str] = {
    TransactionCategory.FREELANCE_INCOME: "Freelance income",
    TransactionCategory.SALARY: "Salary",
    TransactionCategory.DIVIDEND: "Dividend",
    TransactionCategory.INTEREST: "Interest",
    TransactionCategory.RENTAL_INCOME: "Rental income",
    TransactionCategory.TAX_REFUND: "Tax refund",
    TransactionCategory.TAX_PAYMENT: "Tax payment",
    TransactionCategory.TRANSFER_IN: "Transfer in",
    TransactionCategory.TRANSFER_OUT: "Transfer out",
    TransactionCategory.BUSINESS_EXPENSE: "Business expense",
    TransactionCategory.SUBSCRIPTION: "Subscription",
    TransactionCategory.LOAN_REPAYMENT: "Loan repayment",
    TransactionCategory.MORTGAGE: "Mortgage",
    TransactionCategory.RENT_PAYMENT: "Rent",
    TransactionCategory.UTILITY: "Utility",
    TransactionCategory.PERSONAL_SPENDING: "Personal spending",
    TransactionCategory.UNKNOWN: "Unknown",
}

# ── Subscription subcategories ───────────────────────────────────────────────
#
# Canonical subcategory slugs for TransactionCategory.SUBSCRIPTION.
# These are documentation + validation aids — the engine does not enforce them,
# but new subscription rules should use a slug from this dict.
#
# To add a future category: add the slug + description here, then add a Rule
# in the RULES list following the extension guide in the Subscriptions section.
#
SUBSCRIPTION_SUBCATEGORIES: dict[str, str] = {
    "software":     "SaaS tools, cloud services, developer platforms (already implemented)",
    "membership":   "Professional bodies, trade associations, co-working spaces",
    "insurance":    "Professional indemnity, public liability, equipment cover",
    "media":        "Streaming services, news, stock assets used for business",
    "learning":     "Online courses, certifications, training platforms",
    "other":        "Recurring debit not covered by the above subcategories",
}


# Badge colour tokens (maps to CSS classes in v2.css)
CATEGORY_BADGE: dict[TransactionCategory, str] = {
    TransactionCategory.FREELANCE_INCOME: "income",
    TransactionCategory.SALARY: "income",
    TransactionCategory.DIVIDEND: "income",
    TransactionCategory.INTEREST: "income",
    TransactionCategory.RENTAL_INCOME: "income",
    TransactionCategory.TAX_REFUND: "income",
    TransactionCategory.TAX_PAYMENT: "tax",
    TransactionCategory.TRANSFER_IN: "neutral",
    TransactionCategory.TRANSFER_OUT: "neutral",
    TransactionCategory.BUSINESS_EXPENSE: "expense",
    TransactionCategory.SUBSCRIPTION: "expense",
    TransactionCategory.LOAN_REPAYMENT: "neutral",
    TransactionCategory.MORTGAGE: "neutral",
    TransactionCategory.RENT_PAYMENT: "neutral",
    TransactionCategory.UTILITY: "neutral",
    TransactionCategory.PERSONAL_SPENDING: "personal",
    TransactionCategory.UNKNOWN: "unknown",
}


# ── Result types ─────────────────────────────────────────────────────────────

@dataclass
class ClassificationResult:
    category: TransactionCategory
    confidence: float       # 0.0–1.0
    method: str             # "rules" | "ai" | "manual"
    subcategory: str | None = None
    notes: str | None = None

    @property
    def tax_relevant(self) -> bool:
        return TAX_RELEVANT.get(self.category, False)

    @property
    def label(self) -> str:
        return CATEGORY_LABELS.get(self.category, self.category.value)

    @property
    def badge(self) -> str:
        return CATEGORY_BADGE.get(self.category, "unknown")


@dataclass
class ClassifiedTransaction:
    """A raw Yapily transaction dict paired with its classification."""

    raw: dict
    classification: ClassificationResult

    @property
    def amount(self) -> Decimal:
        return Decimal(str(self.raw["amount"]))

    @property
    def date(self) -> str:
        return self.raw["date"]

    @property
    def description(self) -> str:
        return (
            self.raw.get("description")
            or self.raw.get("transactionInformation")
            or ""
        )

    @property
    def is_credit(self) -> bool:
        return self.amount > 0

    @property
    def currency(self) -> str:
        return self.raw.get("currency", "GBP")

    @property
    def id(self) -> str:
        return self.raw.get("id", "")


# ── Classifier base class (extensibility point) ───────────────────────────────

class ClassifierBase(ABC):
    """
    Implement this class to add a new classifier (e.g. AI-assisted).

    Insert instances into TransactionPipeline.classifiers in priority order.
    The pipeline stops at the first result whose confidence >= confidence_threshold.
    """
    confidence_threshold: float = 0.70

    @abstractmethod
    def classify(self, tx: dict) -> ClassificationResult:
        """Classify a single raw Yapily transaction dict."""
        ...


# ── Rule engine ───────────────────────────────────────────────────────────────

@dataclass
class Rule:
    """One deterministic classification rule."""

    name: str
    patterns: list[str]        # regex patterns — any match fires the rule
    category: TransactionCategory
    confidence: float
    subcategory: str | None = None
    notes: str | None = None
    credit_only: bool = False   # only fire when amount > 0
    debit_only: bool = False    # only fire when amount < 0
    _compiled: list = field(default_factory=list, init=False, repr=False)

    def __post_init__(self) -> None:
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.patterns]

    def matches(self, tx: dict) -> bool:
        amount = Decimal(str(tx.get("amount", 0)))
        if self.credit_only and amount <= 0:
            return False
        if self.debit_only and amount >= 0:
            return False
        text = _tx_text(tx)
        return any(rx.search(text) for rx in self._compiled)


def _tx_text(tx: dict) -> str:
    """Concatenate all searchable text fields from a Yapily transaction dict."""
    merchant_name = ""
    if isinstance(tx.get("merchant"), dict):
        merchant_name = tx["merchant"].get("name", "")
    return " ".join(filter(None, [
        tx.get("description", ""),
        tx.get("transactionInformation", ""),
        tx.get("proprietaryBankTransactionCode", ""),
        merchant_name,
    ]))


# Rules evaluated top-to-bottom; first match wins.
# More specific / higher-confidence rules are listed first.
RULES: list[Rule] = [

    # ── HMRC ─────────────────────────────────────────────────────────────────
    Rule(
        name="hmrc_refund",
        patterns=[r"\bHMRC\b", r"\bHM\s*REVENUE\b"],
        category=TransactionCategory.TAX_REFUND,
        confidence=0.95,
        notes="HMRC credit — likely tax or VAT refund",
        credit_only=True,
    ),
    Rule(
        name="hmrc_payment",
        patterns=[r"\bHMRC\b", r"\bHM\s*REVENUE\b", r"\bSELF\s*ASSESSMENT\b", r"\bSA[0-9]{3}\b"],
        category=TransactionCategory.TAX_PAYMENT,
        confidence=0.95,
        notes="HMRC debit — likely SA, NI, VAT, or PAYE payment",
        debit_only=True,
    ),

    # ── Employment income ─────────────────────────────────────────────────────
    Rule(
        name="salary",
        patterns=[r"\bSALARY\b", r"\bPAYROLL\b", r"\bWAGES\b", r"\bSTAFF\s*PAY\b", r"\bEMPLOYER\s*PAY\b"],
        category=TransactionCategory.SALARY,
        confidence=0.90,
        credit_only=True,
    ),

    # ── Investment income ──────────────────────────────────────────────────────
    Rule(
        name="dividend",
        patterns=[r"\bDIVIDEND\b", r"\bDIV\s+PMT\b"],
        category=TransactionCategory.DIVIDEND,
        confidence=0.92,
        credit_only=True,
    ),
    Rule(
        name="interest",
        patterns=[r"\bINTEREST\s+PAID\b", r"\bINTEREST\s+CREDIT\b", r"\bSAVINGS\s+INTEREST\b"],
        category=TransactionCategory.INTEREST,
        confidence=0.90,
        credit_only=True,
    ),

    # ── Rental income ─────────────────────────────────────────────────────────
    Rule(
        name="rental_income",
        patterns=[r"\bRENT\s+(RECEIVED|INCOME|PMT)\b", r"\bTENANT\b", r"\bLET\s*PROPERTY\b"],
        category=TransactionCategory.RENTAL_INCOME,
        confidence=0.85,
        credit_only=True,
    ),

    # ── Freelance / self-employment income ────────────────────────────────────
    Rule(
        name="freelance_invoice",
        patterns=[
            r"\bINV[-\s]?\d+\b",
            r"\bINVOICE\b",
            r"\bFREELANCE\b",
            r"\bCONSULT(ING|ANCY)?\b",
            r"\bCONTRACT\s*(FEE|PAY|PAYMENT)\b",
            r"\bPROJECT\s*FEE\b",
            r"\bDESIGN\s*(FEE|PAYMENT)\b",
            r"\bCLIENT\s*PAY",
        ],
        category=TransactionCategory.FREELANCE_INCOME,
        confidence=0.85,
        credit_only=True,
    ),

    # ── Own-account transfers ─────────────────────────────────────────────────
    Rule(
        name="transfer_in",
        patterns=[r"\bTRANSFER\b", r"\bTRF\b", r"\bSAVINGS\s*POT\b", r"\bMOVED\s*FROM\b"],
        category=TransactionCategory.TRANSFER_IN,
        confidence=0.75,
        credit_only=True,
    ),
    Rule(
        name="transfer_out",
        patterns=[r"\bTRANSFER\b", r"\bTRF\b", r"\bSAVINGS\s*POT\b", r"\bMOVED\s*TO\b"],
        category=TransactionCategory.TRANSFER_OUT,
        confidence=0.75,
        debit_only=True,
    ),

    # ── Mortgage ──────────────────────────────────────────────────────────────
    Rule(
        name="mortgage",
        patterns=[r"\bMORTGAGE\b", r"\bHOME\s*LOAN\b", r"\bMTG\b"],
        category=TransactionCategory.MORTGAGE,
        confidence=0.95,
        debit_only=True,
    ),

    # ── Loans ─────────────────────────────────────────────────────────────────
    Rule(
        name="loan_repayment",
        patterns=[
            r"\bSLC\b", r"\bSTUDENT\s*(LOAN|FINANCE)\b",
            r"\bLOAN\s*(REPAY|PMT|PAYMENT)\b",
            r"\bFINANCE\s*REPAY",
            r"\bHIRE\s*PURCHASE\b",
        ],
        category=TransactionCategory.LOAN_REPAYMENT,
        confidence=0.88,
        debit_only=True,
    ),

    # ── Rent ──────────────────────────────────────────────────────────────────
    Rule(
        name="rent_payment",
        patterns=[
            r"\bRENT\b", r"\bRENTAL\b", r"\bLANDLORD\b",
            r"\bFOXTONS\b", r"\bPURPLEBRICKS\b", r"\bRIGHTMOVE\b",
        ],
        category=TransactionCategory.RENT_PAYMENT,
        confidence=0.85,
        debit_only=True,
    ),

    # ── Utilities ─────────────────────────────────────────────────────────────
    Rule(
        name="utility",
        patterns=[
            r"\bBRITISH\s*GAS\b", r"\bOCTOPUS\s*(ENERGY|ELECTRIC)\b",
            r"\bE\.?ON\b", r"\bSSE\b", r"\bEDF\s*ENERGY\b",
            r"\bTHAMES\s*WATER\b", r"\bSEVERN\s*TRENT\b", r"\bANGLIAN\s*WATER\b",
            r"\bBT\s*(GROUP|BROADBAND|BUSINESS)\b",
            r"\bSKY\s*(BROAD|TV|MOBILE|DIGITAL)\b",
            r"\bVIRGIN\s*MEDIA\b", r"\bTALKTALK\b",
            r"\bVODAFONE\b", r"\bEE\b", r"\bO2\b", r"\bTHREE\b",
            r"\bCOUNCIL\s*TAX\b", r"\bWATER\s*(BILL|CHARGE|SERV)\b",
        ],
        category=TransactionCategory.UTILITY,
        confidence=0.90,
        debit_only=True,
    ),

    # ── Subscriptions ─────────────────────────────────────────────────────────
    #
    # Extension guide — adding a new subscription subcategory
    # --------------------------------------------------------
    # 1. Choose a subcategory slug from SUBSCRIPTION_SUBCATEGORIES (below).
    # 2. Create a new Rule with:
    #      category    = TransactionCategory.SUBSCRIPTION
    #      subcategory = "<slug>"           # from SUBSCRIPTION_SUBCATEGORIES
    #      debit_only  = True               # subscriptions are outgoing payments
    #      confidence  = 0.85–0.95          # high for named merchants; lower for generic terms
    # 3. Insert it in this section, BEFORE the generic personal_card_spend catch-all.
    #    More-specific (higher-confidence) rules should appear first.
    # 4. Add representative patterns to tests/test_transaction_classification.py.
    #
    # Do NOT introduce new TransactionCategory values for subscription subcategories —
    # the subcategory field on ClassificationResult and Rule carries that granularity.
    # This keeps the top-level category set stable while allowing fine-grained tagging.

    Rule(
        name="subscription_software",
        patterns=[
            r"\bADOBE\b", r"\bFIGMA\b", r"\bNOTION\b", r"\bSLACK\b",
            r"\bGITHUB\b", r"\bGITLAB\b", r"\bDROPBOX\b",
            r"\bGOOGLE\s*(ONE|WORKSPACE|STORAGE)\b",
            r"\bMICROSOFT\s*365\b", r"\bOFFICE\s*365\b",
            r"\b1PASSWORD\b", r"\bLINEAR\b", r"\bVERCEL\b",
            r"\bNETLIFY\b", r"\bAWS\b", r"\bAMAZON\s*WEB\s*SERVICES\b",
            r"\bHEROKU\b", r"\bDIGITAL\s*OCEAN\b", r"\bCLOUDFLARE\b",
            r"\bZOOM\b", r"\bLOOM\b", r"\bHOTJAR\b", r"\bINTERCOM\b",
            r"\bSUBSTACK\b", r"\bMAILCHIMP\b", r"\bCONVERTKIT\b",
            r"\bMIDJOURNEY\b", r"\bOPENAI\b", r"\bCURSOR\b",
            r"\bSPOTIFY\b.*\bBUSINESS\b",
        ],
        category=TransactionCategory.SUBSCRIPTION,
        subcategory="software",
        confidence=0.90,
        debit_only=True,
    ),

    # ── Business travel ───────────────────────────────────────────────────────
    Rule(
        name="business_travel",
        patterns=[
            r"\bTRAINLINE\b", r"\bNATIONAL\s*RAIL\b", r"\bTFL\b",
            r"\bEUROSTAR\b", r"\bBUSINESS\s*TRAVEL\b",
        ],
        category=TransactionCategory.BUSINESS_EXPENSE,
        subcategory="travel",
        confidence=0.72,
        notes="Possibly business travel — confirm before claiming",
        debit_only=True,
    ),

    # ── Business equipment ────────────────────────────────────────────────────
    Rule(
        name="business_equipment",
        patterns=[
            r"\bAPPLE\s*STORE\b", r"\bAPPLE\.COM\b",
            r"\bMICROSOFT\s*STORE\b", r"\bCURRYS\b",
            r"\bB&H\b", r"\bBHPHOTO\b", r"\bSTUDIO\s*EQUIP\b",
        ],
        category=TransactionCategory.BUSINESS_EXPENSE,
        subcategory="equipment",
        confidence=0.65,
        notes="Possible equipment — confirm business use",
        debit_only=True,
    ),

    # ── Personal spending (low-confidence catch-all for card debits) ──────────
    Rule(
        name="personal_card_spend",
        patterns=[
            r"\bCARD\s*PAYMENT\b", r"\bCONTACTLESS\b",
            r"\bDEBIT\s*CARD\b", r"\bPOS\b",
        ],
        category=TransactionCategory.PERSONAL_SPENDING,
        confidence=0.55,
        debit_only=True,
    ),
]


# ── Classifiers ───────────────────────────────────────────────────────────────

class RulesClassifier(ClassifierBase):
    """
    Deterministic rule-based classifier.

    Iterates RULES in order and returns the first match whose confidence
    meets the threshold. Falls through to UNKNOWN if no rule matches.
    """

    confidence_threshold: float = 0.50  # accept even low-confidence rule matches

    def classify(self, tx: dict) -> ClassificationResult:
        for rule in RULES:
            if rule.matches(tx):
                return ClassificationResult(
                    category=rule.category,
                    confidence=rule.confidence,
                    method="rules",
                    subcategory=rule.subcategory,
                    notes=rule.notes,
                )
        return ClassificationResult(
            category=TransactionCategory.UNKNOWN,
            confidence=0.0,
            method="rules",
            notes="No rule matched",
        )


# ── Pipeline ──────────────────────────────────────────────────────────────────

class TransactionPipeline:
    """
    Runs a list of classifiers in order against each transaction.

    The first classifier whose result confidence >= its threshold wins.
    This is the primary extensibility point: insert an AI classifier
    before RulesClassifier to let it handle high-confidence cases,
    with rules acting as fallback.

    Example (future):
        pipeline = TransactionPipeline(classifiers=[
            AIClassifier(model="gpt-4o"),   # handles ambiguous cases
            RulesClassifier(),               # fallback
        ])
    """

    def __init__(self, classifiers: list[ClassifierBase] | None = None) -> None:
        self.classifiers: list[ClassifierBase] = classifiers or [RulesClassifier()]

    def process(self, transactions: list[dict]) -> list[ClassifiedTransaction]:
        return [self._classify_one(tx) for tx in transactions]

    def _classify_one(self, tx: dict) -> ClassifiedTransaction:
        for classifier in self.classifiers:
            result = classifier.classify(tx)
            if result.confidence >= classifier.confidence_threshold:
                return ClassifiedTransaction(raw=tx, classification=result)
        # All classifiers fell through
        return ClassifiedTransaction(
            raw=tx,
            classification=ClassificationResult(
                category=TransactionCategory.UNKNOWN,
                confidence=0.0,
                method="rules",
                notes="No classifier reached threshold",
            ),
        )
