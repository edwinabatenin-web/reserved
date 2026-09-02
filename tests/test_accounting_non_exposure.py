"""Architecture / non-exposure boundary checks for accounting contracts.

Prevents the accounting contracts or the synthetic tax-input boundary from being
consumed by the production tax engine, routes, persistence or API before a
separate approval gate. Providers must remain disabled.

Exactly one production consumer is authorised: the named W8-S1 accounting-to-tax
handoff ``reserved/engines/accounting_tax_handoff.py``. It may consume only the
canonical tax-input contract; every other production module must not import the
accounting package, any of its submodules, or the protected contract symbols.
"""
import ast
import stat
from dataclasses import dataclass
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

# The single authorised production consumer of the accounting-to-tax boundary.
PERMITTED_ACCOUNTING_CONSUMER = REPO / "reserved" / "engines" / "accounting_tax_handoff.py"

# Protected accounting contract symbols already covered by the non-exposure gate.
ACCOUNTING_CONTRACT_SYMBOLS = frozenset({
    "SourceObservation", "SemanticAdapterResult", "CanonicalAccountingTaxInput",
    "AccountingEntry", "normalise_document", "AccountingInvoice",
})

# The canonical accounting-to-tax boundary the handoff may consume. This is the
# exact approved synthetic tax input and the module that defines it; broader
# accounting imports (provider adapters, raw records, normalisation builders,
# the deprecated flattened entry) remain rejected even inside the handoff.
CANONICAL_HANDOFF_SYMBOLS = frozenset({
    "CanonicalAccountingTaxInput",
    "SourceObservation",
})
CANONICAL_HANDOFF_MODULE = "reserved.providers.accounting.contracts"


@dataclass(frozen=True)
class ImportFact:
    kind: str
    module: str | None
    symbol: str | None = None
    alias: str | None = None
    level: int = 0


def _production_python_files():
    """Every production Python module outside the accounting package itself."""
    files = []
    for path in (REPO / "reserved").rglob("*.py"):
        if ACCOUNTING_PKG in path.parents:
            continue
        files.append(path)
    return files


def _facts_from_tree(tree):
    facts = []
    import_module_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                facts.append(ImportFact("import", alias.name, alias=alias.asname))
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                facts.append(ImportFact(
                    "from", node.module, alias.name, alias.asname, node.level
                ))
                if node.level == 0 and (
                    (node.module == "importlib" and alias.name == "import_module")
                    or (node.module == "builtins" and alias.name == "__import__")
                ):
                    import_module_names.add(alias.asname or alias.name)

    # Follow the simple aliasing shapes commonly used to conceal a dynamic
    # import call. More complex/unresolved call targets are caught below when
    # expressed through getattr or a direct import API attribute.
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        is_loader = (
            isinstance(value, ast.Name)
            and value.id in ({"__import__"} | import_module_names)
        ) or (
            isinstance(value, ast.Attribute)
            and value.attr in {"import_module", "__import__"}
        ) or (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "getattr"
            and len(value.args) >= 2
            and isinstance(value.args[1], ast.Constant)
            and value.args[1].value in {"import_module", "__import__"}
        )
        if not is_loader:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        import_module_names.update(
            target.id for target in targets if isinstance(target, ast.Name)
        )

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        is_dynamic = (
            isinstance(node.func, ast.Name)
            and node.func.id in ({"__import__"} | import_module_names)
        ) or (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in {"import_module", "__import__"}
        ) or (
            isinstance(node.func, ast.Call)
            and isinstance(node.func.func, ast.Name)
            and node.func.func.id == "getattr"
            and len(node.func.args) >= 2
            and isinstance(node.func.args[1], ast.Constant)
            and node.func.args[1].value in {"import_module", "__import__"}
        )
        if is_dynamic:
            target = None
            if node.args and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str):
                target = node.args[0].value
            facts.append(ImportFact("dynamic", target))
    return tuple(facts)


def _facts_from_source(source):
    return _facts_from_tree(ast.parse(source))


def _inspect_imports(path):
    if path.is_symlink():
        raise ValueError("symlink is not an inspectable regular file")
    try:
        mode = path.stat().st_mode
        if not stat.S_ISREG(mode):
            raise ValueError("path is not a regular file")
        resolved = path.resolve(strict=True)
        resolved.relative_to(REPO.resolve(strict=True))
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"cannot safely inspect imports: {exc}") from exc
    return _facts_from_tree(tree)


def _module_is_accounting(module):
    return module == "reserved.providers.accounting" or (
        module is not None and module.startswith("reserved.providers.accounting.")
    )


def _touches_accounting(fact):
    if fact.kind == "dynamic":
        # An unresolved dynamic target cannot prove non-access and fails closed.
        return (
            fact.module is None
            or fact.module.startswith(".")
            or _module_is_accounting(fact.module)
        )
    qualified_from_target = (
        f"{fact.module}.{fact.symbol}"
        if fact.kind == "from" and fact.module and fact.symbol
        else None
    )
    relative_accounting_target = fact.level > 0 and (
        "accounting" in (fact.module or "").split(".")
        or fact.symbol == "accounting"
        or fact.symbol in ACCOUNTING_CONTRACT_SYMBOLS
    )
    return (
        _module_is_accounting(fact.module)
        or _module_is_accounting(qualified_from_target)
        or relative_accounting_target
        or fact.symbol in ACCOUNTING_CONTRACT_SYMBOLS
    )


def _describe_fact(fact):
    if fact.kind == "from":
        dots = "." * fact.level
        alias = f" as {fact.alias}" if fact.alias else ""
        return f"from {dots}{fact.module or ''} import {fact.symbol}{alias}"
    if fact.kind == "import":
        alias = f" as {fact.alias}" if fact.alias else ""
        return f"import {fact.module}{alias}"
    return f"dynamic import of {fact.module or '<unresolved target>'}"


def _handoff_import_offences(facts):
    offences = []
    for fact in facts:
        if not _touches_accounting(fact):
            continue
        permitted = (
            fact.kind == "from"
            and fact.level == 0
            and fact.module == CANONICAL_HANDOFF_MODULE
            and fact.symbol in CANONICAL_HANDOFF_SYMBOLS
            and fact.alias is None
        )
        if not permitted:
            offences.append(_describe_fact(fact))
    return offences


def _is_exact_permitted_consumer(path):
    if path != PERMITTED_ACCOUNTING_CONSUMER or path.is_symlink():
        return False
    try:
        return (
            stat.S_ISREG(path.stat().st_mode)
            and path.resolve(strict=True)
            == PERMITTED_ACCOUNTING_CONSUMER.resolve(strict=True)
        )
    except OSError:
        return False


def _accounting_offence(path):
    """Return a human-readable offence for one file, or ``None`` when clean."""
    try:
        facts = _inspect_imports(path)
    except ValueError as exc:
        return f"{path.relative_to(REPO)}: {exc}"
    accounting_facts = tuple(fact for fact in facts if _touches_accounting(fact))
    if path == PERMITTED_ACCOUNTING_CONSUMER:
        if not _is_exact_permitted_consumer(path):
            return f"{path.relative_to(REPO)} is not the exact resolved regular consumer"
        broader = _handoff_import_offences(facts)
        if broader:
            return (f"{path.relative_to(REPO)} imports broader accounting: {broader}")
        return None
    if accounting_facts:
        return str(path.relative_to(REPO))
    return None


def test_no_production_module_imports_accounting_contracts():
    offenders = []
    for path in _production_python_files():
        offence = _accounting_offence(path)
        if offence:
            offenders.append(offence)
    assert offenders == [], f"accounting contracts leaked into production: {offenders}"


def test_authorised_handoff_may_explicitly_import_only_both_boundary_symbols():
    facts = _facts_from_source(
        "from reserved.providers.accounting.contracts import "
        "CanonicalAccountingTaxInput, SourceObservation\n"
    )
    assert _handoff_import_offences(facts) == []


def test_second_production_consumer_is_rejected():
    facts = _facts_from_source(
        "from reserved.providers.accounting.contracts import CanonicalAccountingTaxInput\n"
    )
    assert any(_touches_accounting(fact) for fact in facts)


def test_handoff_rejects_broader_provider_adapter_import():
    offences = _handoff_import_offences(_facts_from_source(
        "import reserved.providers.accounting.freeagent\n"
    ))
    assert offences == ["import reserved.providers.accounting.freeagent"]


def test_handoff_rejects_deprecated_legacy_entry_symbol():
    offences = _handoff_import_offences(_facts_from_source(
        "from reserved.providers.accounting.contracts import AccountingEntry\n"
    ))
    assert offences == [
        "from reserved.providers.accounting.contracts import AccountingEntry"
    ]


@pytest.mark.parametrize("source", [
    "import reserved.providers.accounting.contracts",
    "import reserved.providers.accounting.contracts as contracts",
    "from reserved.providers import accounting",
    "from reserved.providers.accounting import contracts",
    "from ..providers import accounting",
    "from ..providers.accounting import contracts",
    "from ..providers.accounting.contracts import CanonicalAccountingTaxInput",
    "from reserved.providers.accounting import CanonicalAccountingTaxInput",
    "from reserved.providers.accounting.contracts import *",
    "from reserved.providers.accounting.contracts import CanonicalAccountingTaxInput as TaxInput",
    "import importlib as il\nil.import_module('reserved.providers.accounting.contracts')",
    "from importlib import import_module as load\nload('reserved.providers.accounting.contracts')",
    "import importlib\nload = importlib.import_module\nload('reserved.providers.accounting.contracts')",
    "import importlib\ngetattr(importlib, 'import_module')('reserved.providers.accounting.contracts')",
    "import importlib\nload = getattr(importlib, 'import_module')\nload('reserved.providers.accounting.contracts')",
    "import builtins\nload = getattr(builtins, '__import__')\nload('reserved.providers.accounting.contracts')",
    "import builtins\nbuiltins.__import__('reserved.providers.accounting.contracts')",
    "__import__('reserved.providers.accounting.contracts')",
    "__import__(module_name)",
    "import importlib\nimportlib.import_module('.contracts', package_name)",
])
def test_handoff_rejects_module_star_alias_and_dynamic_import_evasion(source):
    assert _handoff_import_offences(_facts_from_source(source))


def test_unparseable_file_fails_closed(tmp_path):
    candidate = tmp_path / "broken.py"
    candidate.write_text("from reserved.providers.accounting.contracts import (", encoding="utf-8")
    with pytest.raises(ValueError, match="cannot safely inspect imports"):
        _inspect_imports(candidate)


def test_symlink_cannot_claim_permitted_consumer_identity(tmp_path):
    target = tmp_path / "target.py"
    target.write_text(
        "from reserved.providers.accounting.contracts import SourceObservation\n",
        encoding="utf-8",
    )
    link = tmp_path / "accounting_tax_handoff.py"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        _inspect_imports(link)
    assert not _is_exact_permitted_consumer(link)


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
