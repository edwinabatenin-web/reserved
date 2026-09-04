"""Keep newly assured tax components internal until later product gates pass."""

import ast
from pathlib import Path


ROOT = Path(__file__).parents[1]
INTERNAL_MODULE_MARKERS = (
    "integrated_annual_position",
    "annual_loan_reconciliation",
    "annual_position_composition",
    "cash_ready_annual_position",
    "annual_to_cash_integration",
    "internal_snapshot",
    "internal_hicbc_scenario",
    "annual_loan_wp7u",
    "calculate_annual_position",
    "reconcile_annual_student_loans",
    "compose_internal_annual_position",
    "compose_cash_ready_annual_position",
    "compose_annual_to_cash_position",
    "encode_internal_snapshot",
    "decode_internal_snapshot",
    "compare_hicbc_scenario",
    "emit_annual_loan_wp7u_envelopes",
    "AnnualPositionResult",
    "AnnualLoanReconciliation",
    "InternalAnnualComposition",
    "CashReadyAnnualPosition",
    "AnnualToCashPosition",
    "InternalHicbcScenario",
)

_HANDOFF_ALLOWED_IMPORTS = {
    "__future__": {("annotations", None)},
    "dataclasses": {
        ("dataclass", None), ("field", None), ("fields", None),
        ("is_dataclass", None),
    },
    "datetime": {("date", None)},
    "decimal": {("Decimal", None)},
    "enum": {("Enum", None)},
    "reserved.engines": {
        ("cash_funding_position", "funding"),
        ("cash_obligation_reconciliation", "obligations"),
        ("payments_on_account", "poa"),
    },
    "reserved.engines.annual_to_cash_integration": {
        ("CONTRACT_VERSION", "ANNUAL_TO_CASH_VERSION"),
        ("AnnualToCashPosition", None),
        ("AnnualToCashStatus", None),
        ("cash_ready_annual_position_identity", None),
    },
    "reserved.services.w2_customer_language": {
        ("CONTRACT_VERSION", "W2_VERSION"),
        ("AdjustmentFact", None),
        ("AdjustmentKind", None),
        ("EvidenceClassification", None),
        ("FundingClassification", None),
        ("ObligationFact", None),
        ("ObligationKind", None),
        ("PresentationStatus", None),
        ("W2PresentationInput", None),
        ("present_w2_customer_language", None),
    },
}
_HANDOFF_ALLOWED_DIRECT_IMPORTS = {
    ("hashlib", None), ("hmac", None), ("json", None), ("re", None),
}
_HANDOFF_ALLOWED_CALL_TARGETS = {
    "AdjustmentFact", "Decimal", "ObligationFact", "TypeError",
    "UnboundAnnualCashPresentation", "ValueError", "W2PresentationInput",
    "_DIGEST_ID.fullmatch", "_IssueToken", "_SOURCE_ID.fullmatch",
    "_canonical", "_digest", "_exact_graph", "_expected_handoff_seal",
    "_handoff_components", "_money", "_recompute_nested",
    "_source_position_identity", "_source_references", "_validate",
    "_validate_exact_presentation_graph", "_validate_handoff_state",
    "active.add", "active.remove", "all", "any",
    "cash_ready_annual_position_identity",
    "compose_w8_annual_cash_customer_handoff", "dataclass", "field", "fields",
    "funding.compose_cash_funding_position", "hasattr", "hash",
    "hashlib.sha256", "hashlib.sha256().hexdigest", "hmac.compare_digest",
    "id", "is_dataclass", "isinstance", "json.dumps",
    "json.dumps().encode", "len", "object.__getattribute__",
    "object.__setattr__", "obligations.reconcile_cash_obligations",
    "present_w2_customer_language", "re.compile", "refs.extend", "set",
    "str", "tuple", "type", "type().__module__.split",
    "validate_w8_annual_cash_customer_handoff", "value.is_finite",
    "value.is_signed", "value.is_zero", "value.isoformat", "value.quantize",
    "value.source_position_identity.startswith", "vars", "visited.add",
}
_HANDOFF_ALLOWED_ENGINE_CALLS = {
    "funding.compose_cash_funding_position",
    "obligations.reconcile_cash_obligations",
    "cash_ready_annual_position_identity",
}
_HANDOFF_ALLOWED_ENGINE_ATTRIBUTES = {
    "funding": {
        "CashFundingPosition", "FundingBalance", "FundingComputationStatus",
        "compose_cash_funding_position",
    },
    "obligations": {
        "account", "CashObligationReconciliation", "CashObligationStatus",
        "reconcile_cash_obligations",
    },
    "poa": {"PoAAssessment", "BalancingPosition"},
}
_HANDOFF_FORBIDDEN_SYMBOLS = {
    "integrated_annual_position",
    "calculate_annual_position",
    "CashReadyAnnualPosition",
    "compose_annual_to_cash_position",
}


def _named_annual_cash_handoff_violations(source: str) -> list[str]:
    """Enforce the exact reviewed imports/calls of the W8-S2C boundary."""
    tree = ast.parse(source)
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                fact = (alias.name, alias.asname)
                if fact not in _HANDOFF_ALLOWED_DIRECT_IMPORTS:
                    violations.append(f"forbidden absolute import {fact}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            allowed = _HANDOFF_ALLOWED_IMPORTS.get(module)
            for alias in node.names:
                fact = (alias.name, alias.asname)
                if node.level != 0 or allowed is None or fact not in allowed:
                    violations.append(
                        f"forbidden from-import level={node.level} "
                        f"{module}.{alias.name} as {alias.asname}"
                    )
        if isinstance(node, (ast.Name, ast.Attribute)):
            symbol = node.id if isinstance(node, ast.Name) else node.attr
            if symbol in _HANDOFF_FORBIDDEN_SYMBOLS:
                violations.append(f"forbidden symbol {symbol}")
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            allowed_attributes = _HANDOFF_ALLOWED_ENGINE_ATTRIBUTES.get(node.value.id)
            if allowed_attributes is not None and node.attr not in allowed_attributes:
                violations.append(
                    f"forbidden engine attribute {node.value.id}.{node.attr}"
                )
        if isinstance(node, ast.Call):
            target = _handoff_call_target(node.func)
            if target not in _HANDOFF_ALLOWED_CALL_TARGETS:
                violations.append(f"forbidden call {target}")
    return violations


def _handoff_call_target(value: ast.expr) -> str:
    if isinstance(value, ast.Name):
        return value.id
    if isinstance(value, ast.Attribute):
        return f"{_handoff_call_target(value.value)}.{value.attr}"
    if isinstance(value, ast.Call):
        return f"{_handoff_call_target(value.func)}()"
    if isinstance(value, ast.Subscript):
        return f"{_handoff_call_target(value.value)}[]"
    return type(value).__name__


def test_internal_annual_components_are_not_imported_by_customer_layers():
    permitted_hicbc_source = ROOT / "reserved/services/hicbc_annual_source_runtime.py"
    assert permitted_hicbc_source.is_file() and not permitted_hicbc_source.is_symlink()
    assert permitted_hicbc_source.resolve(strict=True) == permitted_hicbc_source
    permitted_handoff = (
        ROOT / "reserved" / "services" / "w8_annual_cash_customer_handoff.py"
    )
    assert permitted_handoff.is_file() and not permitted_handoff.is_symlink()
    assert permitted_handoff.resolve(strict=True) == permitted_handoff
    customer_roots = (
        ROOT / "reserved" / "web",
        ROOT / "reserved" / "services",
        ROOT / "reserved" / "templates",
        ROOT / "reserved" / "static",
    )
    violations = []
    for root in customer_roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in {".py", ".html", ".js"}:
                continue
            text = path.read_text(errors="ignore")
            if path == permitted_handoff:
                violations.extend(_named_annual_cash_handoff_violations(text))
            elif path == permitted_hicbc_source:
                violations.extend(_named_hicbc_source_violations(text))
            else:
                for marker in INTERNAL_MODULE_MARKERS:
                    if marker in text:
                        violations.append(f"{path.relative_to(ROOT)} contains {marker}")
    assert not violations, (
        "Internal annual components require separate persistence/API/customer "
        "approval before exposure: " + "; ".join(violations)
    )


def _named_hicbc_source_violations(source):
    """One named annual-engine caller, never a directory-wide exception."""
    allowed_imports = {
        ("decimal", "Decimal", None),
        ("reserved.engines.integrated_annual_position", "calculate_annual_position", None),
    }
    allowed_calls = {
        "re.compile", "frozenset", "type", "set", "ValueError", "_MONEY.fullmatch",
        "calculate_annual_position", "ani.is_finite",
    }
    violations = []
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if [(a.name, a.asname) for a in node.names] != [("re", None)]:
                violations.append("unauthorised import")
        if isinstance(node, ast.ImportFrom):
            if node.level or any((node.module, a.name, a.asname) not in allowed_imports for a in node.names):
                violations.append("unauthorised from-import")
        if isinstance(node, ast.Call) and _handoff_call_target(node.func) not in allowed_calls:
            violations.append("unauthorised call")
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "result" and node.attr not in {"adjusted_net_income", "unsupported_families"}:
                violations.append("annual result exposure")
        if isinstance(node, ast.Return) and ast.unparse(node.value) != "ani":
            violations.append("only own ANI may leave source")
        if isinstance(node, ast.Name) and node.id in {"getattr", "globals", "locals", "__builtins__"}:
            violations.append("dynamic access")
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            parent = parents.get(node)
            if node.id == "result" and not isinstance(parent, ast.Attribute):
                violations.append("annual result escaped into alias or operand")
            if node.id == "calculate_annual_position" and not (
                isinstance(parent, ast.Call) and parent.func is node
            ):
                violations.append("annual producer aliased")
    return violations


def test_named_hicbc_source_rejects_extra_internal_calls_and_exposure():
    for mutation in (
        "from reserved.engines.integrated_annual_position import AnnualPositionResult",
        "from reserved.engines import integrated_annual_position as engine",
        "from .hidden import calculate_annual_position",
        "import importlib", "__import__('os')", "getattr(result, 'total_liability')",
        "jsonify(result)", "result.total_liability", "leak = result.__dict__",
        "def leak():\n return result", "other = calculate_annual_position\nother({})",
        "def leak():\n ani = result\n return ani",
    ):
        assert _named_hicbc_source_violations(mutation), mutation


def test_manual_annual_source_has_only_the_named_request_caller():
    source = ROOT / "reserved/services/hicbc_annual_source_runtime.py"
    caller = ROOT / "reserved/web/hicbc.py"
    for path in (ROOT / "reserved").rglob("*.py"):
        if path in {source, caller}:
            continue
        text = path.read_text()
        assert "own_ani_from_manual_annual" not in text, path
        assert "hicbc_annual_source_runtime" not in text, path
    tree = ast.parse(caller.read_text())
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == "own_ani_from_manual_annual"]
    preview = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                   and node.name == "annual_preview")
    assert len(calls) == 1 and calls[0] in list(ast.walk(preview))
    assert ast.unparse(calls[0]) == "own_ani_from_manual_annual(payload, tax_year)"


def test_named_annual_cash_handoff_rejects_expanded_imports_and_calls():
    forbidden_sources = (
        "from reserved.engines.integrated_annual_position import calculate_annual_position",
        "from reserved.engines.cash_ready_annual_position import CashReadyAnnualPosition",
        "from reserved.web.routes import index",
        "from reserved.api.w8_customer_result import get_customer_result",
        "from reserved.models import User",
        "from reserved import database",
        "calculate_annual_position()",
        "funding.unreviewed_engine_call()",
        "poa.assess_payments_on_account()",
        "__import__('reserved.web.routes')",
        "importlib.import_module('reserved.api.w8_customer_result')",
        "import os\nos.system('true')",
        "import requests\nrequests.get('https://example.test')",
        "from .nearby import hidden",
        "import importlib as il\nil.import_module('reserved.web.routes')",
        "loader = __import__\nloader('reserved.web.routes')",
        "getattr(__builtins__, 'open')('/tmp/probe')",
    )
    for source in forbidden_sources:
        assert _named_annual_cash_handoff_violations(source), source


def test_internal_annual_components_are_not_connected_to_persistence_models_or_api():
    connection_roots = (
        ROOT / "reserved" / "database.py",
        ROOT / "reserved" / "models",
        ROOT / "reserved" / "api",
    )
    violations = []
    for root in connection_roots:
        paths = (root,) if root.is_file() else tuple(root.rglob("*.py"))
        for path in paths:
            text = path.read_text(errors="ignore")
            for marker in INTERNAL_MODULE_MARKERS:
                if marker in text:
                    violations.append(f"{path.relative_to(ROOT)} contains {marker}")
    assert not violations, (
        "Internal annual results/snapshots require explicit persistence and API "
        "approval before connection: " + "; ".join(violations)
    )


def test_database_schema_has_no_internal_annual_snapshot_storage():
    database = (ROOT / "reserved" / "database.py").read_text().lower()
    prohibited_schema_terms = (
        "annual_position_snapshot",
        "annual_loan_reconciliation",
        "internal_annual_composition",
        "internal_snapshot_version",
    )
    assert not [term for term in prohibited_schema_terms if term in database]


def test_internal_annual_components_are_not_published_in_openapi_inventory():
    openapi = (ROOT / "docs" / "openapi.json").read_text()
    for marker in INTERNAL_MODULE_MARKERS:
        assert marker not in openapi
    assert "No complete annual tax-position API" in openapi
    assert "internal-preview-non-production" in openapi
