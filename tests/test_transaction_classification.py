"""
Tests for Workstream 3 — Transaction Intelligence & Tax Engine Foundations.

Covers:
- TransactionCategory enum and tax-relevance mapping
- RulesClassifier: one test per category (credit + debit)
- Edge cases: unknown description, amount direction disambiguation
- TransactionPipeline: custom pipeline, fallthrough to UNKNOWN
- ClassifiedTransaction properties
- ingestion.get_demo_transactions() — all demo transactions classify (no UNKNOWN leakage)
- ingestion.summarise() — totals are correct types and non-negative
"""

from decimal import Decimal

import pytest

from reserved.providers.banking.classifier import (
    ClassificationResult,
    ClassifiedTransaction,
    ClassifierBase,
    RulesClassifier,
    TransactionCategory,
    TransactionPipeline,
    TAX_RELEVANT,
    CATEGORY_LABELS,
)
from reserved.providers.banking.ingestion import get_demo_transactions, summarise


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _tx(description: str, amount: float, extra: dict | None = None) -> dict:
    """Build a minimal Yapily-format transaction dict."""
    base = {
        "id": "test-id",
        "date": "2026-07-01",
        "amount": amount,
        "currency": "GBP",
        "description": description,
        "transactionInformation": description,
        "proprietaryBankTransactionCode": "CREDIT" if amount > 0 else "DEBIT",
        "status": "BOOKED",
    }
    if extra:
        base.update(extra)
    return base


# ── TransactionCategory ───────────────────────────────────────────────────────

def test_all_categories_have_tax_relevance_entry():
    for cat in TransactionCategory:
        assert cat in TAX_RELEVANT, f"{cat} missing from TAX_RELEVANT"


def test_all_categories_have_label():
    for cat in TransactionCategory:
        assert cat in CATEGORY_LABELS, f"{cat} missing from CATEGORY_LABELS"


def test_income_categories_are_tax_relevant():
    income = [
        TransactionCategory.FREELANCE_INCOME,
        TransactionCategory.SALARY,
        TransactionCategory.DIVIDEND,
        TransactionCategory.INTEREST,
        TransactionCategory.RENTAL_INCOME,
        TransactionCategory.TAX_REFUND,
        TransactionCategory.TAX_PAYMENT,
        TransactionCategory.BUSINESS_EXPENSE,
        TransactionCategory.SUBSCRIPTION,
    ]
    for cat in income:
        assert TAX_RELEVANT[cat] is True, f"{cat} should be tax-relevant"


def test_personal_categories_are_not_tax_relevant():
    personal = [
        TransactionCategory.PERSONAL_SPENDING,
        TransactionCategory.RENT_PAYMENT,
        TransactionCategory.UTILITY,
        TransactionCategory.MORTGAGE,
        TransactionCategory.LOAN_REPAYMENT,
        TransactionCategory.TRANSFER_IN,
        TransactionCategory.TRANSFER_OUT,
        TransactionCategory.UNKNOWN,
    ]
    for cat in personal:
        assert TAX_RELEVANT[cat] is False, f"{cat} should not be tax-relevant"


# ── RulesClassifier — income ──────────────────────────────────────────────────

def test_classifies_hmrc_credit_as_tax_refund():
    clf = RulesClassifier()
    result = clf.classify(_tx("HMRC PAYE REFUND", 842.00))
    assert result.category == TransactionCategory.TAX_REFUND
    assert result.confidence >= 0.90


def test_classifies_hmrc_debit_as_tax_payment():
    clf = RulesClassifier()
    result = clf.classify(_tx("HMRC SELF ASSESSMENT", -2840.50))
    assert result.category == TransactionCategory.TAX_PAYMENT
    assert result.confidence >= 0.90


def test_classifies_hmrc_debit_sa300():
    clf = RulesClassifier()
    result = clf.classify(_tx("HMRC SA300 BALANCING PAYMENT", -1420.00))
    assert result.category == TransactionCategory.TAX_PAYMENT


def test_classifies_salary():
    clf = RulesClassifier()
    result = clf.classify(_tx("SALARY ACME CORP JULY", 3500.00))
    assert result.category == TransactionCategory.SALARY


def test_classifies_dividend():
    clf = RulesClassifier()
    result = clf.classify(_tx("VANGUARD DIVIDEND PMT", 210.00))
    assert result.category == TransactionCategory.DIVIDEND


def test_classifies_interest():
    clf = RulesClassifier()
    result = clf.classify(_tx("SAVINGS INTEREST CREDIT", 14.32))
    assert result.category == TransactionCategory.INTEREST


def test_classifies_freelance_invoice_number():
    clf = RulesClassifier()
    result = clf.classify(_tx("INV-2026-047 STUDIO CLIENT LTD", 3200.00))
    assert result.category == TransactionCategory.FREELANCE_INCOME


def test_classifies_freelance_invoice_keyword():
    clf = RulesClassifier()
    result = clf.classify(_tx("MERIDIAN GROUP CONSULTING FEE", 4500.00))
    assert result.category == TransactionCategory.FREELANCE_INCOME


def test_classifies_freelance_design_fee():
    clf = RulesClassifier()
    result = clf.classify(_tx("DESIGN FEE NORTHGATE LABS", 1200.00))
    assert result.category == TransactionCategory.FREELANCE_INCOME


def test_classifies_transfer_in():
    clf = RulesClassifier()
    result = clf.classify(_tx("TRANSFER FROM SAVINGS POT", 500.00))
    assert result.category == TransactionCategory.TRANSFER_IN


# ── RulesClassifier — debits ──────────────────────────────────────────────────

def test_classifies_rent_payment():
    clf = RulesClassifier()
    result = clf.classify(_tx("RENT 15 MARSH ROAD LANDLORD", -1350.00))
    assert result.category == TransactionCategory.RENT_PAYMENT


def test_classifies_mortgage():
    clf = RulesClassifier()
    result = clf.classify(_tx("BARCLAYS MORTGAGE PAYMENT", -1100.00))
    assert result.category == TransactionCategory.MORTGAGE


def test_classifies_student_loan():
    clf = RulesClassifier()
    result = clf.classify(_tx("SLC STUDENT LOAN REPAYMENT", -620.00))
    assert result.category == TransactionCategory.LOAN_REPAYMENT


def test_classifies_utility_energy():
    clf = RulesClassifier()
    result = clf.classify(_tx("OCTOPUS ENERGY", -68.40))
    assert result.category == TransactionCategory.UTILITY


def test_classifies_utility_council_tax():
    clf = RulesClassifier()
    result = clf.classify(_tx("COUNCIL TAX HACKNEY LBC", -178.00))
    assert result.category == TransactionCategory.UTILITY


def test_classifies_utility_water():
    clf = RulesClassifier()
    result = clf.classify(_tx("THAMES WATER BILL", -34.20))
    assert result.category == TransactionCategory.UTILITY


def test_classifies_utility_mobile():
    clf = RulesClassifier()
    result = clf.classify(_tx("VODAFONE MONTHLY BILL", -28.00))
    assert result.category == TransactionCategory.UTILITY


def test_classifies_subscription_adobe():
    clf = RulesClassifier()
    result = clf.classify(_tx("ADOBE CREATIVE CLOUD", -54.99))
    assert result.category == TransactionCategory.SUBSCRIPTION
    assert result.subcategory == "software"


def test_classifies_subscription_figma():
    clf = RulesClassifier()
    result = clf.classify(_tx("FIGMA", -14.00))
    assert result.category == TransactionCategory.SUBSCRIPTION


def test_classifies_subscription_aws():
    clf = RulesClassifier()
    result = clf.classify(_tx("AWS AMAZON WEB SERVICES", -22.47))
    assert result.category == TransactionCategory.SUBSCRIPTION


def test_classifies_business_travel_trainline():
    clf = RulesClassifier()
    result = clf.classify(_tx("TRAINLINE COM", -38.50))
    assert result.category == TransactionCategory.BUSINESS_EXPENSE
    assert result.subcategory == "travel"


def test_classifies_business_travel_tfl():
    clf = RulesClassifier()
    result = clf.classify(_tx("TFL TRAVEL", -12.60))
    assert result.category == TransactionCategory.BUSINESS_EXPENSE


def test_classifies_business_equipment_apple():
    clf = RulesClassifier()
    result = clf.classify(_tx("APPLE STORE", -349.00))
    assert result.category == TransactionCategory.BUSINESS_EXPENSE
    assert result.subcategory == "equipment"


def test_classifies_personal_card_payment():
    clf = RulesClassifier()
    result = clf.classify(_tx("CARD PAYMENT SAINSBURYS", -52.34))
    assert result.category == TransactionCategory.PERSONAL_SPENDING


def test_classifies_personal_contactless():
    clf = RulesClassifier()
    result = clf.classify(_tx("CARD PAYMENT MONMOUTH COFFEE", -6.80))
    assert result.category == TransactionCategory.PERSONAL_SPENDING


def test_classifies_transfer_out():
    clf = RulesClassifier()
    result = clf.classify(_tx("TRANSFER TO SAVINGS POT", -800.00))
    assert result.category == TransactionCategory.TRANSFER_OUT


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_unknown_for_unmatched_description():
    clf = RulesClassifier()
    result = clf.classify(_tx("BACS CREDIT REF 9X4K22", -45.00))
    assert result.category == TransactionCategory.UNKNOWN
    assert result.confidence == 0.0


def test_hmrc_credit_vs_debit_disambiguation():
    """HMRC credit → TAX_REFUND; HMRC debit → TAX_PAYMENT."""
    clf = RulesClassifier()
    refund = clf.classify(_tx("HMRC", 200.00))
    payment = clf.classify(_tx("HMRC", -200.00))
    assert refund.category == TransactionCategory.TAX_REFUND
    assert payment.category == TransactionCategory.TAX_PAYMENT


def test_rent_credit_vs_debit_disambiguation():
    """RENT credit → RENTAL_INCOME; RENT debit → RENT_PAYMENT."""
    clf = RulesClassifier()
    income = clf.classify(_tx("RENT RECEIVED FROM TENANT", 900.00))
    payment = clf.classify(_tx("RENT LANDLORD PAYMENT", -900.00))
    assert income.category == TransactionCategory.RENTAL_INCOME
    assert payment.category == TransactionCategory.RENT_PAYMENT


def test_transfer_credit_vs_debit():
    clf = RulesClassifier()
    tin = clf.classify(_tx("TRANSFER FROM SAVINGS", 500.00))
    tout = clf.classify(_tx("TRANSFER TO SAVINGS", -500.00))
    assert tin.category == TransactionCategory.TRANSFER_IN
    assert tout.category == TransactionCategory.TRANSFER_OUT


def test_zero_amount_does_not_match_credit_or_debit_only_rules():
    clf = RulesClassifier()
    # HMRC with zero amount — neither credit_only nor debit_only rule should fire
    result = clf.classify(_tx("HMRC ADJUSTMENT", 0.00))
    assert result.category == TransactionCategory.UNKNOWN


# ── ClassificationResult properties ──────────────────────────────────────────

def test_classification_result_tax_relevant_property():
    result = ClassificationResult(
        category=TransactionCategory.FREELANCE_INCOME,
        confidence=0.85,
        method="rules",
    )
    assert result.tax_relevant is True


def test_classification_result_label():
    result = ClassificationResult(
        category=TransactionCategory.TAX_PAYMENT,
        confidence=0.95,
        method="rules",
    )
    assert result.label == "Tax payment"


def test_classification_result_badge():
    result = ClassificationResult(
        category=TransactionCategory.FREELANCE_INCOME,
        confidence=0.85,
        method="rules",
    )
    assert result.badge == "income"


# ── ClassifiedTransaction properties ─────────────────────────────────────────

def test_classified_transaction_properties():
    raw = _tx("INV-001 CLIENT", 1000.00)
    clf = RulesClassifier()
    ct = ClassifiedTransaction(raw=raw, classification=clf.classify(raw))
    assert ct.amount == Decimal("1000.00")
    assert ct.is_credit is True
    assert ct.date == "2026-07-01"
    assert ct.currency == "GBP"
    assert ct.classification.category == TransactionCategory.FREELANCE_INCOME


# ── TransactionPipeline ───────────────────────────────────────────────────────

def test_pipeline_default_uses_rules_classifier():
    pipeline = TransactionPipeline()
    results = pipeline.process([_tx("INV-001 CLIENT", 1000.00)])
    assert len(results) == 1
    assert results[0].classification.method == "rules"


def test_pipeline_custom_classifier_overrides():
    """A classifier that always returns SALARY should override rules."""

    class AlwaysSalary(ClassifierBase):
        confidence_threshold = 0.0

        def classify(self, tx: dict) -> ClassificationResult:
            return ClassificationResult(
                category=TransactionCategory.SALARY,
                confidence=1.0,
                method="ai",
            )

    pipeline = TransactionPipeline(classifiers=[AlwaysSalary(), RulesClassifier()])
    result = pipeline.process([_tx("HMRC PAYMENT", -500.00)])[0]
    assert result.classification.category == TransactionCategory.SALARY
    assert result.classification.method == "ai"


def test_pipeline_falls_through_to_rules_when_ai_below_threshold():
    """A classifier below its threshold should not win; rules should take over."""

    class LowConfidenceClassifier(ClassifierBase):
        confidence_threshold = 0.99  # very high threshold

        def classify(self, tx: dict) -> ClassificationResult:
            return ClassificationResult(
                category=TransactionCategory.SALARY,
                confidence=0.5,  # below threshold
                method="ai",
            )

    pipeline = TransactionPipeline(
        classifiers=[LowConfidenceClassifier(), RulesClassifier()]
    )
    result = pipeline.process([_tx("HMRC PAYMENT", -500.00)])[0]
    # Rules classifier should have handled it
    assert result.classification.method == "rules"
    assert result.classification.category == TransactionCategory.TAX_PAYMENT


def test_pipeline_returns_unknown_when_all_classifiers_fail():
    class NeverMatchClassifier(ClassifierBase):
        confidence_threshold = 1.0

        def classify(self, tx: dict) -> ClassificationResult:
            return ClassificationResult(
                category=TransactionCategory.UNKNOWN,
                confidence=0.0,
                method="rules",
            )

    pipeline = TransactionPipeline(classifiers=[NeverMatchClassifier()])
    result = pipeline.process([_tx("BACS CREDIT REF 9X4K22", -45.00)])[0]
    assert result.classification.category == TransactionCategory.UNKNOWN


def test_pipeline_processes_multiple_transactions():
    pipeline = TransactionPipeline()
    txns = [
        _tx("INV-001 CLIENT", 1000.00),
        _tx("HMRC PAYMENT", -500.00),
        _tx("ADOBE CREATIVE CLOUD", -54.99),
    ]
    results = pipeline.process(txns)
    assert len(results) == 3
    assert results[0].classification.category == TransactionCategory.FREELANCE_INCOME
    assert results[1].classification.category == TransactionCategory.TAX_PAYMENT
    assert results[2].classification.category == TransactionCategory.SUBSCRIPTION


# ── Demo transactions ─────────────────────────────────────────────────────────

def test_demo_transactions_all_classify():
    classified = get_demo_transactions()
    assert len(classified) > 0
    for ct in classified:
        assert isinstance(ct.classification.category, TransactionCategory)
        assert 0.0 <= ct.classification.confidence <= 1.0


def test_demo_transactions_sorted_newest_first():
    classified = get_demo_transactions()
    dates = [ct.date for ct in classified]
    assert dates == sorted(dates, reverse=True)


def test_demo_transactions_cover_key_categories():
    classified = get_demo_transactions()
    categories = {ct.classification.category for ct in classified}
    required = {
        TransactionCategory.FREELANCE_INCOME,
        TransactionCategory.TAX_PAYMENT,
        TransactionCategory.SUBSCRIPTION,
        TransactionCategory.RENT_PAYMENT,
        TransactionCategory.UTILITY,
        TransactionCategory.PERSONAL_SPENDING,
        TransactionCategory.TRANSFER_OUT,
        TransactionCategory.INTEREST,
    }
    missing = required - categories
    assert not missing, f"Demo data missing categories: {missing}"


def test_demo_transactions_unknown_count_is_low():
    """At most 2 UNKNOWN transactions in the full demo set."""
    classified = get_demo_transactions()
    unknown = [ct for ct in classified if ct.classification.category == TransactionCategory.UNKNOWN]
    assert len(unknown) <= 2, f"Too many UNKNOWN: {[ct.description for ct in unknown]}"


# ── summarise() ──────────────────────────────────────────────────────────────

def test_summarise_totals_are_decimal():
    classified = get_demo_transactions()
    summary = summarise(classified)
    assert isinstance(summary["total_income"], Decimal)
    assert isinstance(summary["total_tax_payments"], Decimal)
    assert isinstance(summary["total_expenses"], Decimal)


def test_summarise_totals_are_non_negative():
    classified = get_demo_transactions()
    summary = summarise(classified)
    assert summary["total_income"] >= 0
    assert summary["total_tax_payments"] >= 0
    assert summary["total_expenses"] >= 0


def test_summarise_income_is_positive():
    """Demo data includes multiple invoices so income must be > 0."""
    classified = get_demo_transactions()
    summary = summarise(classified)
    assert summary["total_income"] > 0


def test_summarise_by_category_contains_expected_keys():
    classified = get_demo_transactions()
    summary = summarise(classified)
    by_cat = summary["by_category"]
    assert TransactionCategory.FREELANCE_INCOME in by_cat
    assert TransactionCategory.TAX_PAYMENT in by_cat
    assert TransactionCategory.SUBSCRIPTION in by_cat


def test_summarise_unclassified_count_is_integer():
    classified = get_demo_transactions()
    summary = summarise(classified)
    assert isinstance(summary["unclassified_count"], int)
    assert summary["unclassified_count"] >= 0
