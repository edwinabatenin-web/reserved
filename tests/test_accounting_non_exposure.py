"""Architecture / non-exposure boundary checks for accounting contracts.

Prevents the accounting contracts or the synthetic tax-input boundary from being
consumed by the production tax engine, routes, persistence or API before a
separate approval gate. Providers must remain disabled.
"""
import ast
from pathlib import Path

import pytest

from reserved.providers.accounting.base import AccountingProvider
from reserved.providers.accounting.contracts import (
    AccountingEntry, AccountingInvoice, AccountingDocument,
    CanonicalAccountingTaxInput, SourceObservation,
)
from reserved.providers.accounting.freeagent import FreeAgentProvider
from reserved.providers.accounting.quickbooks import QuickBooksProvider
from reserved.providers.accounting.xero import XeroProvider

REPO = Path(__file__).resolve().parents[1]
ACCOUNTING_PKG = REPO / "reserved" / "providers" / "accounting"


def _production_python_files():
    """Every production Python module outside the accounting package itself."""
    files = []
    for path in (REPO / "reserved").rglob("*.py"):
        if ACCOUNTING_PKG in path.parents:
            continue
        files.append(path)
    return files


def _imported_names(path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module)
            for alias in node.names:
                names.add(alias.name)
    return names


def test_no_production_module_imports_accounting_contracts():
    offenders = []
    for path in _production_python_files():
        names = _imported_names(path)
        if any(
            name == "reserved.providers.accounting"
            or name.startswith("reserved.providers.accounting.")
            or name in {"SourceObservation", "SemanticAdapterResult",
                        "CanonicalAccountingTaxInput", "AccountingEntry",
                        "normalise_document", "AccountingInvoice"}
            for name in names
        ):
            offenders.append(str(path.relative_to(REPO)))
    assert offenders == [], f"accounting contracts leaked into production: {offenders}"


def test_providers_remain_disabled():
    for provider_cls in (FreeAgentProvider, XeroProvider, QuickBooksProvider):
        provider = provider_cls()
        with pytest.raises(NotImplementedError):
            provider.authorisation_url("user-1", "https://example.com/cb")
        with pytest.raises(NotImplementedError):
            provider.exchange_code("code", "https://example.com/cb")
        with pytest.raises(NotImplementedError):
            provider.list_invoices("credential-ref")


def test_accounting_invoice_alias_is_the_canonical_document():
    assert AccountingInvoice is AccountingDocument


def test_legacy_entry_and_tax_input_are_not_the_same_shape():
    # The flattened legacy entry must never be accepted where a canonical tax
    # input is required, and vice versa.
    assert AccountingEntry is not CanonicalAccountingTaxInput
    assert AccountingEntry is not SourceObservation
