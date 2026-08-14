"""Strict, persistence-neutral snapshots for bounded internal tax results.

This is a deterministic primitive wire representation for tests and internal
handoff only. It is not a database schema, persistence approval, public API or
customer contract. Unknown/missing fields fail closed and no combined monetary
field is permitted.
"""

from dataclasses import fields, is_dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from enum import Enum
import re
import types
from typing import Any, get_args, get_origin, get_type_hints

from .annual_loan_reconciliation import (
    AnnualLoanComponentResult,
    AnnualLoanReconciliation,
    LoanBasisEvidence,
    LoanComponent,
    LoanEvidenceDecision,
)
from .annual_position_composition import (
    InternalAnnualComposition,
    ReferencedAnnualLoanComponents,
    ReferencedAnnualTaxComponents,
    ReferencedLoanComponent,
)
from .integrated_annual_position import AnnualPositionResult


SNAPSHOT_VERSION = "reserved-internal-snapshot/1.0"

_TYPES = {
    cls.__name__: cls for cls in (
        AnnualPositionResult,
        AnnualLoanComponentResult,
        AnnualLoanReconciliation,
        LoanBasisEvidence,
        LoanEvidenceDecision,
        ReferencedAnnualTaxComponents,
        ReferencedLoanComponent,
        ReferencedAnnualLoanComponents,
        InternalAnnualComposition,
    )
}
_ROOT_TYPES = {AnnualPositionResult.__name__, AnnualLoanReconciliation.__name__, InternalAnnualComposition.__name__}
_ENUMS = {LoanComponent.__name__: LoanComponent}
_FORBIDDEN_KEYS = {"combined_total", "combined_balance", "amount_due", "customer_balance"}
_TAX_STATUSES = {"calculated", "insufficient_facts", "unsupported_rule"}
_LOAN_STATUSES = {
    "calculated", "calculated_with_material_uncertainty", "insufficient_facts",
    "conflict_requires_review", "unsupported_plan_combination",
}
_COMPOSITION_STATUSES = {
    "components_available", "calculated_with_material_uncertainty",
    "insufficient_facts", "conflict_requires_review", "unsupported_rule",
}
_LOAN_PROHIBITIONS = {"customer_combined_balance", "filing", "payment", "refund"}
_COMPOSITION_PROHIBITIONS = {"customer_presentation", "reserve_guidance", "filing", "payment", "refund"}
_COMPOSITION_LIMITATIONS = {"components_are_linked_not_aggregated", "no_combined_customer_balance_or_amount_due"}
_REFERENCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SUPPORTED_RULESET = "uk-2026-27-v3"


def _encode(value: Any) -> Any:
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Snapshot decimals must be finite")
        return {"$decimal": str(value)}
    if isinstance(value, date):
        return {"$date": value.isoformat()}
    if isinstance(value, Enum):
        return {"$enum": value.__class__.__name__, "value": value.value}
    if is_dataclass(value):
        if value.__class__.__name__ not in _TYPES:
            raise TypeError(f"Unsupported snapshot dataclass: {value.__class__.__name__}")
        return {
            "$type": value.__class__.__name__,
            "fields": {field.name: _encode(getattr(value, field.name)) for field in fields(value)},
        }
    if isinstance(value, tuple):
        return {"$tuple": [_encode(item) for item in value]}
    if value is None or isinstance(value, (str, bool, int)):
        return value
    raise TypeError(f"Unsupported snapshot value: {type(value).__name__}")


def _exact_keys(value: dict, expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ValueError(
            f"{label} fields mismatch; missing={sorted(expected - actual)}, "
            f"unknown={sorted(actual - expected)}"
        )


def _decode(value: Any) -> Any:
    if isinstance(value, list):
        raise ValueError("Lists are not valid snapshot values; tuples must be tagged")
    if not isinstance(value, dict):
        if value is None or isinstance(value, (str, bool, int)):
            return value
        raise ValueError("Snapshot contains an unsupported primitive")
    if set(value) & _FORBIDDEN_KEYS:
        raise ValueError("Combined monetary fields are prohibited")
    if "$decimal" in value:
        _exact_keys(value, {"$decimal"}, "decimal")
        try:
            result = Decimal(value["$decimal"])
        except (InvalidOperation, TypeError):
            raise ValueError("Invalid decimal snapshot value") from None
        if not result.is_finite():
            raise ValueError("Snapshot decimals must be finite")
        return result
    if "$date" in value:
        _exact_keys(value, {"$date"}, "date")
        try:
            return date.fromisoformat(value["$date"])
        except (TypeError, ValueError):
            raise ValueError("Invalid ISO date snapshot value") from None
    if "$enum" in value:
        _exact_keys(value, {"$enum", "value"}, "enum")
        enum_type = _ENUMS.get(value["$enum"])
        if enum_type is None:
            raise ValueError("Unknown snapshot enum")
        try:
            return enum_type(value["value"])
        except ValueError:
            raise ValueError("Unknown snapshot enum value") from None
    if "$tuple" in value:
        _exact_keys(value, {"$tuple"}, "tuple")
        if not isinstance(value["$tuple"], list):
            raise ValueError("Tagged tuple payload must be a list")
        return tuple(_decode(item) for item in value["$tuple"])
    _exact_keys(value, {"$type", "fields"}, "dataclass")
    cls = _TYPES.get(value["$type"])
    if cls is None or not isinstance(value["fields"], dict):
        raise ValueError("Unknown or malformed snapshot dataclass")
    expected = {field.name for field in fields(cls)}
    _exact_keys(value["fields"], expected, value["$type"])
    decoded = {name: _decode(item) for name, item in value["fields"].items()}
    hints = get_type_hints(cls)
    for name, item in decoded.items():
        if not _matches_type(item, hints[name]):
            raise ValueError(f"{value['$type']}.{name} has the wrong encoded type")
    return cls(**decoded)


def _matches_type(value: Any, annotation: Any) -> bool:
    if annotation is Any:
        return True
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (types.UnionType,):
        return any(_matches_type(value, item) for item in args)
    if origin is tuple:
        return isinstance(value, tuple) and all(_matches_type(item, args[0]) for item in value)
    if annotation is bool:
        return type(value) is bool
    if annotation is int:
        return type(value) is int
    return isinstance(value, annotation)


def encode_internal_snapshot(value: Any) -> dict[str, Any]:
    """Encode one approved root result into JSON-safe primitives."""
    type_name = value.__class__.__name__
    if type_name not in _ROOT_TYPES:
        raise TypeError("Snapshot root must be an approved internal result")
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "root_type": type_name,
        "purpose": "internal_ephemeral_handoff_not_persistence_approval",
        "payload": _encode(value),
    }


def decode_internal_snapshot(snapshot: dict[str, Any]) -> Any:
    """Strictly decode and reconstruct an approved internal result."""
    if not isinstance(snapshot, dict):
        raise ValueError("Snapshot must be an object")
    _exact_keys(snapshot, {"snapshot_version", "root_type", "purpose", "payload"}, "snapshot")
    if snapshot["snapshot_version"] != SNAPSHOT_VERSION:
        raise ValueError("Unsupported snapshot version")
    if snapshot["purpose"] != "internal_ephemeral_handoff_not_persistence_approval":
        raise ValueError("Unsupported snapshot purpose")
    if snapshot["root_type"] not in _ROOT_TYPES:
        raise ValueError("Unsupported snapshot root type")
    result = _decode(snapshot["payload"])
    if result.__class__.__name__ != snapshot["root_type"]:
        raise ValueError("Snapshot root type does not match payload")
    _validate_semantics(result)
    return result


def _validate_semantics(result: Any) -> None:
    if isinstance(result, AnnualPositionResult):
        if result.tax_year != "2026/27":
            raise ValueError("Unsupported annual-position tax year")
        if result.contract_version != "reserved-estimate-envelope/1.0-internal":
            raise ValueError("Unsupported annual-position producer contract version")
        if result.ruleset_version != _SUPPORTED_RULESET:
            raise ValueError("Unsupported annual-position ruleset version")
        if result.calculation_status not in _TAX_STATUSES:
            raise ValueError("Unknown annual-position calculation status")
        if (result.calculation_status == "calculated") != (result.total_liability is not None):
            raise ValueError("Annual-position status and total availability contradict")
    elif isinstance(result, AnnualLoanReconciliation):
        if result.tax_year != "2026/27":
            raise ValueError("Unsupported annual-loan tax year")
        if result.contract_version != "reserved-annual-loan-reconciliation/1.0":
            raise ValueError("Unsupported annual-loan producer contract version")
        if result.ruleset_version != _SUPPORTED_RULESET:
            raise ValueError("Unsupported annual-loan ruleset version")
        if result.calculation_status not in _LOAN_STATUSES:
            raise ValueError("Unknown annual-loan calculation status")
        if not _LOAN_PROHIBITIONS.issubset(result.prohibited_uses):
            raise ValueError("Annual-loan snapshot weakens mandatory prohibitions")
        if result.calculation_status == "calculated" and (
            not result.components or any(item.calculation_status != "calculated" for item in result.components)
        ):
            raise ValueError("Calculated annual-loan snapshot requires fully calculated components")
    elif isinstance(result, InternalAnnualComposition):
        if result.tax_year != "2026/27":
            raise ValueError("Unsupported composition tax year")
        if result.contract_version != "reserved-internal-annual-composition/1.0":
            raise ValueError("Unsupported composition producer contract version")
        if result.composition_status not in _COMPOSITION_STATUSES:
            raise ValueError("Unknown composition status")
        if not _COMPOSITION_PROHIBITIONS.issubset(result.prohibited_uses):
            raise ValueError("Composition snapshot weakens mandatory prohibitions")
        if not _COMPOSITION_LIMITATIONS.issubset(result.limitations):
            raise ValueError("Composition snapshot weakens mandatory limitations")
        if not _LOAN_PROHIBITIONS.issubset(result.student_loans.prohibited_uses):
            raise ValueError("Nested annual-loan snapshot weakens mandatory prohibitions")
        if result.component_set_complete != (result.composition_status == "components_available"):
            raise ValueError("Composition completeness and status contradict")
        if result.annual_tax.calculation_status not in _TAX_STATUSES:
            raise ValueError("Unknown nested annual-position status")
        if result.student_loans.calculation_status not in _LOAN_STATUSES:
            raise ValueError("Unknown nested annual-loan status")
        for reference, namespace in (
            (result.annual_tax.reference, "annual-position"),
            (result.student_loans.reference, "loan-reconciliation"),
        ):
            prefix = f"{namespace}:"
            if not reference.startswith(prefix) or not _REFERENCE_ID.fullmatch(reference[len(prefix):]):
                raise ValueError(f"Nested {namespace} reference is not a stable typed reference")
        if result.annual_tax.ruleset_version != _SUPPORTED_RULESET:
            raise ValueError("Unsupported nested annual-position ruleset version")
        if result.student_loans.ruleset_version != _SUPPORTED_RULESET:
            raise ValueError("Unsupported nested annual-loan ruleset version")
