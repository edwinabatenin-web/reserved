"""Keep newly assured tax components internal until later product gates pass."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
INTERNAL_MODULE_MARKERS = (
    "integrated_annual_position",
    "annual_loan_reconciliation",
    "annual_position_composition",
    "cash_ready_annual_position",
    "internal_snapshot",
    "internal_hicbc_scenario",
    "annual_loan_wp7u",
    "calculate_annual_position",
    "reconcile_annual_student_loans",
    "compose_internal_annual_position",
    "compose_cash_ready_annual_position",
    "encode_internal_snapshot",
    "decode_internal_snapshot",
    "compare_hicbc_scenario",
    "emit_annual_loan_wp7u_envelopes",
    "AnnualPositionResult",
    "AnnualLoanReconciliation",
    "InternalAnnualComposition",
    "CashReadyAnnualPosition",
    "InternalHicbcScenario",
)


def test_internal_annual_components_are_not_imported_by_customer_layers():
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
            for marker in INTERNAL_MODULE_MARKERS:
                if marker in text:
                    violations.append(f"{path.relative_to(ROOT)} contains {marker}")
    assert not violations, (
        "Internal annual components require separate persistence/API/customer "
        "approval before exposure: " + "; ".join(violations)
    )


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
