"""W8-S1 canonical accounting-to-annual-tax handoff boundary.

This module is the single production consumer of the approved synthetic
``CanonicalAccountingTaxInput`` boundary and its exact ``SourceObservation``
evidence. It derives one supported business-income fact set, invokes the
existing annual-position calculation, and returns an immutable internal result
that carries the calculated ``AnnualPositionResult`` together with
deterministic provenance.

It deliberately does not activate a provider, claim live completeness, expose a
customer result, persist anything, or change tax policy. Provider sync
completeness, W8-S3 geography/customer admission, other income-family assembly,
customer presentation, persistence, filing, payment, production/provider
activation and release all remain prohibited or unproven.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, fields
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, DecimalException, ROUND_HALF_UP
from types import MappingProxyType
from typing import Mapping

from .integrated_annual_position import (
    AnnualPositionResult,
    calculate_annual_position,
)
from reserved.providers.accounting.contracts import (
    CanonicalAccountingTaxInput,
    SourceObservation,
)

# ── Pinned boundary vocabulary ────────────────────────────────────────────────

_SUPPORTED_TAX_YEAR = "2026/27"
_TAX_ESTIMATE_USE = "tax_estimate"
_SUPPORTED_PURPOSE = "income"
_SUPPORTED_SCOPE = "self-assessment"
_SUPPORTED_CURRENCY = "GBP"

_TAX_YEAR_START = date(2026, 4, 6)
_TAX_YEAR_END = date(2027, 4, 5)

_SUPPORTED_BUSINESS_TYPES = frozenset({"trade", "uk_property", "foreign_property"})

_TURNOVER = "turnover"
_EXPENSE = "expense"
_REJECTED_CLASSIFICATIONS = frozenset({"credit_note", "refund", "write_off"})

_ALLOWABLE = "allowable"
_DISALLOWABLE = "disallowable"
_MIXED_APPORTIONED = "mixed_apportioned"

ZERO = Decimal("0")
ONE = Decimal("1")
PENNY = Decimal("0.01")

# The annual engine quantizes monetary values to whole pence. A value that
# cannot be represented to the penny (for example ``Decimal("1e999999")``) must
# be rejected categorically at this boundary rather than escaping as a
# ``decimal.DecimalException`` from the annual engine. The complete ordinary
# ``DecimalException`` family is caught so a hostile context that traps
# ``Inexact``/``Rounded``/``Subnormal``/``Clamped``/``FloatOperation`` also
# fails closed instead of leaking.
_DECIMAL_ARITHMETIC_ERRORS = (DecimalException,)

# ``datetime.utcoffset()`` must be strictly inside this range (as the stdlib
# enforces); anything outside is a hostile/unusable offset.
_MAX_UTC_OFFSET = timedelta(hours=24)

# Standing limitations of this boundary. These are always recorded, whether or
# not the current bundle exercises them, because they describe what this package
# may not do yet rather than what the supplied inputs happened to contain.
_HANDOFF_LIMITATIONS = (
    "provider_sync_completeness_unproven",
    "w8_s3_geography_customer_admission_prohibited",
    "other_income_family_assembly_unproven",
    "customer_presentation_prohibited",
    "persistence_prohibited",
    "filing_payment_prohibited",
    "production_provider_activation_prohibited",
    "release_prohibited",
    "credit_note_refund_write_off_matching_unsupported",
)


class AccountingTaxHandoffError(ValueError):
    """Categorical, value-free failure at the accounting-to-tax boundary."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _reject(code: str) -> None:
    raise AccountingTaxHandoffError(code)


def _derive_contracts_module(*roots: object) -> str:
    """Derive the canonical contracts module identity from imported roots.

    The production import must stay an absolute
    ``reserved.providers.accounting.contracts`` import; this function makes the
    *runtime* type-identity authority follow the actually imported classes
    rather than a literal module string. A later artefact builder may rewrite
    that import to an artefact-local copy with a different, truthful module
    name, and this check will then still resolve the correct identity without
    failing those verified artefact-native objects.
    """
    module: str | None = None
    for root in roots:
        candidate = getattr(root, "__module__", None)
        if type(candidate) is not str or candidate == "":
            raise AccountingTaxHandoffError("contract_root_module_invalid")
        if module is None:
            module = candidate
        elif candidate != module:
            raise AccountingTaxHandoffError("contract_root_module_mismatch")
    if module is None:
        raise AccountingTaxHandoffError("contract_root_module_invalid")
    return module


_ACCOUNTING_CONTRACTS_MODULE = _derive_contracts_module(
    CanonicalAccountingTaxInput,
    SourceObservation,
)

_CONTRACT_IDENTITY_NAMES = (
    "AccountingProviderName",
    "AllowabilityDecision",
    "AllowabilityOutcome",
    "BusinessType",
    "DecisionAuthority",
    "EvidenceState",
    "Provenance",
    "SourceIdentity",
)


def _derive_contract_identity() -> Mapping[str, type]:
    """Resolve every trusted canonical type from the two imported roots.

    The boundary may explicitly import only ``CanonicalAccountingTaxInput`` and
    ``SourceObservation``, so the remaining canonical enum/dataclass types are
    resolved from the single module that defines those roots, via the
    already-imported module registry. Each resolved symbol must itself live in
    that exact module, so a renamed, forged or artefact-mismatched class fails
    closed rather than being accepted by name.
    """
    module = sys.modules.get(_ACCOUNTING_CONTRACTS_MODULE)
    if module is None:
        raise AccountingTaxHandoffError("contract_module_unavailable")
    table: dict[str, type] = {}
    for name in _CONTRACT_IDENTITY_NAMES:
        candidate = getattr(module, name, None)
        if (
            not isinstance(candidate, type)
            or getattr(candidate, "__module__", None) != _ACCOUNTING_CONTRACTS_MODULE
        ):
            raise AccountingTaxHandoffError("contract_identity_table_invalid")
        table[name] = candidate
    return table


_CONTRACT_IDENTITY = _derive_contract_identity()
AccountingProviderName = _CONTRACT_IDENTITY["AccountingProviderName"]
AllowabilityDecision = _CONTRACT_IDENTITY["AllowabilityDecision"]
AllowabilityOutcome = _CONTRACT_IDENTITY["AllowabilityOutcome"]
BusinessType = _CONTRACT_IDENTITY["BusinessType"]
DecisionAuthority = _CONTRACT_IDENTITY["DecisionAuthority"]
EvidenceState = _CONTRACT_IDENTITY["EvidenceState"]
Provenance = _CONTRACT_IDENTITY["Provenance"]
SourceIdentity = _CONTRACT_IDENTITY["SourceIdentity"]


# ── Exact type validation (fail closed on subclasses / hostile containers) ────

# Exact dataclass field sets, derived from the imported canonical classes so a
# missing/extra forged field is rejected categorically rather than leaking an
# ``AttributeError`` or silently accepting forged nested state.
_DATACLASS_FIELDS = {
    CanonicalAccountingTaxInput: frozenset(f.name for f in fields(CanonicalAccountingTaxInput)),
    SourceObservation: frozenset(f.name for f in fields(SourceObservation)),
    Provenance: frozenset(f.name for f in fields(Provenance)),
    SourceIdentity: frozenset(f.name for f in fields(SourceIdentity)),
    AllowabilityDecision: frozenset(f.name for f in fields(AllowabilityDecision)),
    AnnualPositionResult: frozenset(f.name for f in fields(AnnualPositionResult)),
}


# Closed annual-result contract. Every ``AnnualPositionResult`` field is checked
# against one of the explicit groups below; a value of the wrong built-in type, a
# non-finite/unrepresentable money value, a malformed optional value, an
# out-of-range percentage, or a forged family/limitation collection fails closed
# to a fixed, value-free code rather than leaking its type, text or exception.
_ANNUAL_CONTRACT_VERSION = "reserved-estimate-envelope/1.1-internal"
_ANNUAL_RULESET_VERSION = "uk-2026-27-v4"
_ANNUAL_CALCULATION_STATUSES = frozenset({"calculated", "unsupported_rule", "insufficient_facts"})

_ANNUAL_REQUIRED_TEXT_FIELDS = (
    "contract_version",
    "tax_year",
    "ruleset_version",
    "calculation_status",
)

_ANNUAL_REQUIRED_MONEY_FIELDS = (
    "adjusted_net_income",
    "personal_allowance",
    "non_savings_tax",
    "savings_tax",
    "dividend_tax",
    "class_4_ni",
    "personal_savings_allowance",
    "dividend_allowance",
    "uk_property_profit",
    "uk_property_loss_to_carry_forward",
    "foreign_tax_paid_recorded",
)

_ANNUAL_OPTIONAL_MONEY_FIELDS = (
    "blind_persons_allowance",
    "hicbc",
    "hicbc_household_charge",
    "child_benefit_amount",
    "total_liability",
)

_ANNUAL_HICBC_CHARGE_PERCENTAGE_MIN = 0
_ANNUAL_HICBC_CHARGE_PERCENTAGE_MAX = 100

_ANNUAL_HICBC_LIABLE_PERSONS = frozenset({"person", "partner"})

_ANNUAL_INCLUDED_FAMILY_ORDERS = frozenset({
    ("income_tax", "class_4_ni"),
    ("income_tax", "class_4_ni", "hicbc"),
})

_ANNUAL_UNSUPPORTED_FAMILIES = frozenset({
    "residential_finance_cost_reduction",
    "foreign_property_loss_treatment",
    "foreign_property_residence",
    "foreign_tax_credit_relief",
    "hicbc",
})

_ANNUAL_LIMITATIONS = frozenset({
    "paye_reconciliation_not_performed",
    "student_loan_not_calculated",
    "income_tax_is_before_residential_finance_cost_reduction",
    "foreign_property_loss_relief_not_supported",
    "residence_facts_incomplete",
    "outside_supported_uk_resident_case",
    "income_tax_is_before_foreign_tax_credit_relief",
    "blind_persons_allowance_facts_incomplete",
    "hicbc_facts_incomplete",
    "hicbc_responsibility_facts_ambiguous",
    "hicbc_liability_belongs_to_higher_ani_partner",
    "hicbc_liability_belongs_to_child_benefit_claimant",
    "no_child_benefit_payments_to_charge",
})

_ANNUAL_LIMITATION_ORDER_PREFIX = ("paye_reconciliation_not_performed", "student_loan_not_calculated")

# Canonical append order for unsupported families, taken directly from the
# protected ``calculate_annual_position`` implementation. ``unsupported_families``
# must be an ordered unique subsequence of this order.
_ANNUAL_UNSUPPORTED_FAMILY_ORDER = (
    "residential_finance_cost_reduction",
    "foreign_property_loss_treatment",
    "foreign_property_residence",
    "foreign_tax_credit_relief",
    "hicbc",
)

# Canonical append order for limitations, grouped into stages. Alternatives
# within one stage are mutually exclusive and may appear at most once; a later
# stage may never appear before an earlier one. ``no_child_benefit_payments_to_charge``
# is its own trailing stage because it may follow a supported or ambiguous HICBC
# responsibility outcome.
_ANNUAL_LIMITATION_STAGES = (
    ("paye_reconciliation_not_performed",),
    ("student_loan_not_calculated",),
    ("income_tax_is_before_residential_finance_cost_reduction",),
    ("foreign_property_loss_relief_not_supported",),
    ("residence_facts_incomplete", "outside_supported_uk_resident_case"),
    ("income_tax_is_before_foreign_tax_credit_relief",),
    ("blind_persons_allowance_facts_incomplete",),
    (
        "hicbc_facts_incomplete",
        "hicbc_responsibility_facts_ambiguous",
        "hicbc_liability_belongs_to_higher_ani_partner",
        "hicbc_liability_belongs_to_child_benefit_claimant",
    ),
    ("no_child_benefit_payments_to_charge",),
)

_ANNUAL_UNSUPPORTED_FAMILY_INDEX = {
    name: index for index, name in enumerate(_ANNUAL_UNSUPPORTED_FAMILY_ORDER)
}

_ANNUAL_LIMITATION_STAGE_INDEX = {
    name: index
    for index, stage in enumerate(_ANNUAL_LIMITATION_STAGES)
    for name in stage
}


def _exact_nonempty_str(value: object, code: str) -> str:
    if type(value) is not str or value == "":
        _reject(code)
    return value


def _exact_optional_str(value: object, code: str) -> str | None:
    if value is not None and (type(value) is not str or value == ""):
        _reject(code)
    return value


def _exact_str_tuple(value: object, code: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if type(value) is not tuple:
        _reject(code)
    if not allow_empty and not value:
        _reject(code)
    for item in value:
        if type(item) is not str or item == "":
            _reject(code)
    return tuple(value)


def _exact_unique_str_tuple(value: object, code: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    result = _exact_str_tuple(value, code, allow_empty=allow_empty)
    if len(result) != len(set(result)):
        _reject(code)
    return result


def _exact_finite_decimal(value: object, code: str) -> Decimal:
    if type(value) is not Decimal or not value.is_finite():
        _reject(code)
    return value


def _exact_positive_decimal(value: object, code: str) -> Decimal:
    if type(value) is not Decimal or not value.is_finite() or value <= ZERO:
        _reject(code)
    return value


def _exact_date(value: object, code: str) -> date:
    if type(value) is not date:
        _reject(code)
    return value


def _normalise_aware_datetime(value: object, code: str) -> datetime:
    """Return a verified, unambiguous UTC instant or fail categorically.

    The caller's ``tzinfo`` is interrogated exactly once. A naive value, a
    raising ``utcoffset()`` callback, a ``None``/non-``timedelta`` offset, an
    out-of-range offset, or an underflow/overflow during ``replace``, offset
    subtraction or UTC reconstruction all collapse to the single value-free
    ``code`` rather than leaking arbitrary exception text. The result is rebuilt
    onto the fixed ``datetime.timezone.utc`` so no caller-owned (possibly
    hostile) ``tzinfo`` object is retained or re-trusted.
    """
    if type(value) is not datetime:
        _reject(code)
    if value.tzinfo is None:
        _reject(code)
    try:
        offset = value.utcoffset()
        if type(offset) is not timedelta:
            _reject(code)
        if not (-_MAX_UTC_OFFSET < offset < _MAX_UTC_OFFSET):
            _reject(code)
        naive = value.replace(tzinfo=None)
        return (naive - offset).replace(tzinfo=timezone.utc)
    except AccountingTaxHandoffError:
        raise
    except Exception:
        _reject(code)


def _exact_datetime(value: object, code: str) -> datetime:
    return _normalise_aware_datetime(value, code)


def _exact_optional_datetime(value: object, code: str) -> datetime | None:
    if value is None:
        return None
    return _normalise_aware_datetime(value, code)


def _exact_type(value: object, expected: type, code: str):
    """Accept only an exact instance of ``expected`` (reject subclasses/spoofs)."""
    if type(value) is not expected:
        _reject(code)
    return value


def _exact_dataclass(value: object, expected: type, code: str):
    """Accept only an exact ``expected`` dataclass with its exact field set."""
    if type(value) is not expected:
        _reject(code)
    if set(vars(value)) != _DATACLASS_FIELDS[expected]:
        _reject(code)
    return value


def _derive_monetary(value: Decimal, code: str) -> Decimal:
    """Validate a monetary value is finite and annual-engine representable."""
    if type(value) is not Decimal or not value.is_finite():
        _reject(code)
    try:
        value.quantize(PENNY, rounding=ROUND_HALF_UP)
    except _DECIMAL_ARITHMETIC_ERRORS:
        _reject(code)
    return value


def _add_monetary(left: Decimal, right: Decimal, code: str) -> Decimal:
    try:
        total = left + right
    except _DECIMAL_ARITHMETIC_ERRORS:
        _reject(code)
    return _derive_monetary(total, code)


def _subtract_monetary(left: Decimal, right: Decimal, code: str) -> Decimal:
    try:
        result = left - right
    except _DECIMAL_ARITHMETIC_ERRORS:
        _reject(code)
    return _derive_monetary(result, code)


def _derive_annual_monetary(value: object, code: str) -> Decimal:
    """Validate an annual-result monetary value is non-negative and penny-exact.

    Annual-engine outputs are already quantised to whole pence. A forged result
    carrying a negative or sub-penny amount must be rejected rather than silently
    rounded, and the full ``DecimalException`` family is contained so a hostile
    context that traps ``Inexact``/``Rounded``/``Subnormal``/``Clamped`` fails
    closed.
    """
    if type(value) is not Decimal or not value.is_finite():
        _reject(code)
    if value < ZERO:
        _reject(code)
    try:
        if value != value.quantize(PENNY, rounding=ROUND_HALF_UP):
            _reject(code)
    except _DECIMAL_ARITHMETIC_ERRORS:
        _reject(code)
    return value


def _derive_annual_signed_monetary(value: object, code: str) -> Decimal:
    """Validate a signed annual-result monetary value is penny-exact.

    ``foreign_property_profit`` is the only signed annual-result monetary field:
    the annual engine deliberately reports a foreign loss while recording the
    unsupported loss-treatment limitation. It must still be an exact, finite,
    penny-exact ``Decimal``.
    """
    if type(value) is not Decimal or not value.is_finite():
        _reject(code)
    try:
        if value != value.quantize(PENNY, rounding=ROUND_HALF_UP):
            _reject(code)
    except _DECIMAL_ARITHMETIC_ERRORS:
        _reject(code)
    return value


def _validate_annual_position_result(result: object) -> AnnualPositionResult:
    """Validate the annual engine produced an exact, fully typed result.

    The annual engine is trusted code, but it is still an external boundary. An
    exact ``AnnualPositionResult`` whose any field violates the closed contract
    (wrong built-in type, non-finite/unrepresentable money, malformed optional,
    out-of-range percentage, forged family/limitation collection, or a
    cross-field contradiction the protected engine cannot emit) must fail closed
    to a fixed, value-free code rather than be passed through as success.
    """
    result = _exact_dataclass(result, AnnualPositionResult, "annual_position_result_invalid")
    try:
        _validate_annual_text_fields(result)
        for field_name in _ANNUAL_REQUIRED_MONEY_FIELDS:
            _derive_annual_monetary(getattr(result, field_name), "annual_position_monetary_invalid")
        for field_name in _ANNUAL_OPTIONAL_MONEY_FIELDS:
            value = getattr(result, field_name)
            if value is not None:
                _derive_annual_monetary(value, "annual_position_monetary_invalid")
        # ``income_tax_before_limitations`` and ``foreign_property_profit`` are
        # annotated optional but are always present in the current implementation.
        _derive_annual_monetary(result.income_tax_before_limitations, "annual_position_monetary_invalid")
        _derive_annual_signed_monetary(result.foreign_property_profit, "annual_position_monetary_invalid")
        _validate_annual_percentage(result.hicbc_charge_percentage)
        _validate_annual_liable_person(result.hicbc_liable_person)
        _validate_annual_collections(result)
        _validate_annual_coherence(result)
    except AccountingTaxHandoffError:
        raise
    except Exception:
        _reject("annual_position_field_invalid")
    return result


def _validate_annual_text_fields(result: AnnualPositionResult) -> None:
    for field_name in _ANNUAL_REQUIRED_TEXT_FIELDS:
        value = _exact_nonempty_str(getattr(result, field_name), "annual_position_field_invalid")
        if field_name == "contract_version":
            if value != _ANNUAL_CONTRACT_VERSION:
                _reject("annual_position_field_invalid")
        elif field_name == "tax_year":
            if value != _SUPPORTED_TAX_YEAR:
                _reject("annual_position_field_invalid")
        elif field_name == "ruleset_version":
            if value != _ANNUAL_RULESET_VERSION:
                _reject("annual_position_field_invalid")
        elif field_name == "calculation_status":
            if value not in _ANNUAL_CALCULATION_STATUSES:
                _reject("annual_position_field_invalid")


def _validate_annual_percentage(value: object) -> None:
    if value is None:
        return
    if type(value) is not int:
        _reject("annual_position_field_invalid")
    if not (_ANNUAL_HICBC_CHARGE_PERCENTAGE_MIN <= value <= _ANNUAL_HICBC_CHARGE_PERCENTAGE_MAX):
        _reject("annual_position_field_invalid")


def _validate_annual_liable_person(value: object) -> None:
    if value is None:
        return
    value = _exact_nonempty_str(value, "annual_position_field_invalid")
    if value not in _ANNUAL_HICBC_LIABLE_PERSONS:
        _reject("annual_position_field_invalid")


def _validate_annual_collections(result: AnnualPositionResult) -> None:
    included = result.included_families
    if type(included) is not tuple or included not in _ANNUAL_INCLUDED_FAMILY_ORDERS:
        _reject("annual_position_field_invalid")
    _validate_annual_unsupported_families(result.unsupported_families)
    _validate_annual_limitations(result.limitations)


def _validate_annual_unsupported_families(value: object) -> None:
    if type(value) is not tuple:
        _reject("annual_position_field_invalid")
    for item in value:
        if type(item) is not str or item == "" or item not in _ANNUAL_UNSUPPORTED_FAMILIES:
            _reject("annual_position_field_invalid")
    if len(value) != len(set(value)):
        _reject("annual_position_field_invalid")
    if not _is_ordered_subsequence(value, _ANNUAL_UNSUPPORTED_FAMILY_INDEX):
        _reject("annual_position_field_invalid")


def _validate_annual_limitations(value: object) -> None:
    if type(value) is not tuple:
        _reject("annual_position_field_invalid")
    for item in value:
        if type(item) is not str or item == "" or item not in _ANNUAL_LIMITATIONS:
            _reject("annual_position_field_invalid")
    if len(value) != len(set(value)):
        _reject("annual_position_field_invalid")
    prefix = _ANNUAL_LIMITATION_ORDER_PREFIX
    if len(value) < len(prefix) or value[:len(prefix)] != prefix:
        _reject("annual_position_field_invalid")
    if not _is_ordered_subsequence(value[len(prefix):], _ANNUAL_LIMITATION_STAGE_INDEX):
        _reject("annual_position_field_invalid")


def _is_ordered_subsequence(value: tuple[str, ...], index_map: dict[str, int]) -> bool:
    last = -1
    for item in value:
        index = index_map.get(item)
        if index is None or index <= last:
            return False
        last = index
    return True


def _validate_annual_coherence(result: AnnualPositionResult) -> None:
    _validate_annual_status_coherence(result)
    _validate_annual_bpa_coherence(result)
    _validate_annual_monetary_identity(result)
    _validate_annual_unsupported_limitation_pairings(result)
    _validate_annual_hicbc_coherence(result)


def _validate_annual_status_coherence(result: AnnualPositionResult) -> None:
    status = result.calculation_status
    unsupported = set(result.unsupported_families)
    limitations = set(result.limitations)
    total_present = result.total_liability is not None
    unsupported_empty = not unsupported
    bpa_incomplete = "blind_persons_allowance_facts_incomplete" in limitations

    unsupported_rule_trigger = (
        "foreign_tax_credit_relief" in unsupported
        or "foreign_property_loss_treatment" in unsupported
        or "residential_finance_cost_reduction" in unsupported
        or "outside_supported_uk_resident_case" in limitations
    )

    # Derive the single status the protected engine would emit from this shape,
    # then require the reported status (and total-liability presence) to match.
    # This makes the forward rules bidirectional instead of only one way.
    complete = unsupported_empty and not bpa_incomplete
    if complete:
        required_status = "calculated"
    elif unsupported_rule_trigger:
        required_status = "unsupported_rule"
    else:
        required_status = "insufficient_facts"

    if total_present != complete:
        _reject("annual_position_field_invalid")
    if status != required_status:
        _reject("annual_position_field_invalid")


def _validate_annual_bpa_coherence(result: AnnualPositionResult) -> None:
    bpa_incomplete = "blind_persons_allowance_facts_incomplete" in result.limitations
    if (result.blind_persons_allowance is None) != bpa_incomplete:
        _reject("annual_position_field_invalid")


def _validate_annual_monetary_identity(result: AnnualPositionResult) -> None:
    try:
        income_tax_sum = result.non_savings_tax + result.savings_tax + result.dividend_tax
    except _DECIMAL_ARITHMETIC_ERRORS:
        _reject("annual_position_field_invalid")
    if result.income_tax_before_limitations != income_tax_sum:
        _reject("annual_position_field_invalid")
    if result.calculation_status == "calculated":
        hicbc_term = result.hicbc if result.hicbc is not None else ZERO
        try:
            expected_total = result.income_tax_before_limitations + result.class_4_ni + hicbc_term
        except _DECIMAL_ARITHMETIC_ERRORS:
            _reject("annual_position_field_invalid")
        if result.total_liability != expected_total:
            _reject("annual_position_field_invalid")


def _validate_annual_unsupported_limitation_pairings(result: AnnualPositionResult) -> None:
    unsupported = set(result.unsupported_families)
    limitations = set(result.limitations)

    residential_family = "residential_finance_cost_reduction" in unsupported
    residential_lim = "income_tax_is_before_residential_finance_cost_reduction" in limitations
    if residential_family != residential_lim:
        _reject("annual_position_field_invalid")

    loss_family = "foreign_property_loss_treatment" in unsupported
    loss_lim = "foreign_property_loss_relief_not_supported" in limitations
    if loss_family != loss_lim:
        _reject("annual_position_field_invalid")

    residence_family = "foreign_property_residence" in unsupported
    residence_incomplete = "residence_facts_incomplete" in limitations
    residence_outside = "outside_supported_uk_resident_case" in limitations
    if residence_family != (residence_incomplete != residence_outside):
        _reject("annual_position_field_invalid")

    if loss_family and residence_family:
        _reject("annual_position_field_invalid")

    ftcr_family = "foreign_tax_credit_relief" in unsupported
    ftcr_lim = "income_tax_is_before_foreign_tax_credit_relief" in limitations
    if ftcr_family != ftcr_lim:
        _reject("annual_position_field_invalid")

    # Reverse bind the foreign-property monetary sign to its mandatory marker.
    # A negative profit is only ever reported together with the unsupported
    # loss-treatment family; a non-negative profit can never carry that marker.
    # The residence marker is deliberately NOT reverse-bound from the result
    # alone: a positive profit with no residence family is the genuine
    # UK-resident case, whose provenance is only recoverable from the trusted
    # handoff facts, not from adjusted net income.
    foreign_profit = result.foreign_property_profit
    if foreign_profit < ZERO:
        if not loss_family or residence_family:
            _reject("annual_position_field_invalid")
    elif foreign_profit == ZERO:
        if loss_family or residence_family:
            _reject("annual_position_field_invalid")
    elif loss_family:
        _reject("annual_position_field_invalid")


def _validate_annual_hicbc_coherence(result: AnnualPositionResult) -> None:
    unsupported = set(result.unsupported_families)
    limitations = set(result.limitations)
    included = result.included_families

    hicbc_unsupported = "hicbc" in unsupported
    hicbc_included = "hicbc" in included
    child_benefit_present = result.child_benefit_amount is not None
    liable_person = result.hicbc_liable_person

    # HICBC is included exactly when a child-benefit amount is present and HICBC
    # is supported (not unsupported).
    if hicbc_included != (child_benefit_present and not hicbc_unsupported):
        _reject("annual_position_field_invalid")

    hicbc_facts_incomplete = "hicbc_facts_incomplete" in limitations
    hicbc_ambiguous = "hicbc_responsibility_facts_ambiguous" in limitations
    if hicbc_unsupported != (hicbc_facts_incomplete != hicbc_ambiguous):
        _reject("annual_position_field_invalid")
    if hicbc_facts_incomplete and child_benefit_present:
        _reject("annual_position_field_invalid")
    if hicbc_ambiguous and not child_benefit_present:
        _reject("annual_position_field_invalid")

    # A liable person is present exactly when a supported HICBC charge is present.
    if (liable_person is not None) != (child_benefit_present and not hicbc_unsupported):
        _reject("annual_position_field_invalid")

    higher_partner = "hicbc_liability_belongs_to_higher_ani_partner" in limitations
    claimant = "hicbc_liability_belongs_to_child_benefit_claimant" in limitations

    if liable_person is None:
        if (
            result.hicbc is not None
            or result.hicbc_household_charge is not None
            or result.hicbc_charge_percentage is not None
        ):
            _reject("annual_position_field_invalid")
    else:
        if (
            result.hicbc is None
            or result.hicbc_household_charge is None
            or result.hicbc_charge_percentage is None
        ):
            _reject("annual_position_field_invalid")
        if liable_person == "person":
            if result.hicbc != result.hicbc_household_charge:
                _reject("annual_position_field_invalid")
        elif liable_person == "partner":
            if result.hicbc != ZERO:
                _reject("annual_position_field_invalid")
            if higher_partner == claimant:
                _reject("annual_position_field_invalid")

    # A partner-responsibility outcome marker is emitted only by the exact
    # partner-liable HICBC branch. Forbid it for every other HICBC shape.
    if (higher_partner or claimant) and liable_person != "partner":
        _reject("annual_position_field_invalid")

    if "no_child_benefit_payments_to_charge" in limitations:
        if hicbc_facts_incomplete:
            _reject("annual_position_field_invalid")
        if result.child_benefit_amount != ZERO:
            _reject("annual_position_field_invalid")


def _derive_foreign_property_profit(receipts: Decimal, expenses: Decimal) -> Decimal:
    """Reproduce the annual engine's foreign-property profit derivation.

    The handoff passes ``receipts`` and ``expenses`` verbatim as the engine's
    ``foreign_property_gross_receipts`` and ``foreign_property_allowable_expenses``
    facts, so this mirrors the engine's subtract-then-quantise-to-the-penny
    pipeline exactly.
    """
    try:
        raw = receipts - expenses
        return raw.quantize(PENNY, rounding=ROUND_HALF_UP)
    except _DECIMAL_ARITHMETIC_ERRORS:
        _reject("monetary_value_unrepresentable")


def _validate_handoff_context(
    result: AnnualPositionResult,
    business_kind: str,
    turnover_total: Decimal,
    allowable_expense_total: Decimal,
) -> None:
    """Bind the annual result back to the exact facts this handoff derived.

    Runs after ``_validate_annual_position_result`` at the public consumption
    boundary. The handoff has no authority to invent a geography or residence
    fact, so for ``foreign_property`` it requires the protected engine's
    truthful residence-incomplete shape for positive profit (the engine's
    ``uk_resident`` fact is never supplied). Other business kinds must not
    acquire foreign-property values or markers from a forged engine return.
    """
    if business_kind == "foreign_property":
        expected_profit = _derive_foreign_property_profit(turnover_total, allowable_expense_total)
        _validate_foreign_property_context(result, expected_profit)
    else:
        _validate_non_foreign_context(result)


def _validate_foreign_property_context(result: AnnualPositionResult, expected_profit: Decimal) -> None:
    if result.foreign_property_profit != expected_profit:
        _reject("annual_position_field_invalid")

    unsupported = set(result.unsupported_families)
    limitations = set(result.limitations)
    loss_family = "foreign_property_loss_treatment" in unsupported
    residence_family = "foreign_property_residence" in unsupported
    residence_incomplete = "residence_facts_incomplete" in limitations
    residence_outside = "outside_supported_uk_resident_case" in limitations

    if expected_profit < ZERO:
        if not loss_family or residence_family:
            _reject("annual_position_field_invalid")
    elif expected_profit > ZERO:
        # No ``uk_resident`` fact is ever supplied, so the engine must report
        # the truthful residence-incomplete marker (never the outside-UK case
        # and never the loss-treatment marker) for positive profit.
        if not residence_family or not residence_incomplete or residence_outside or loss_family:
            _reject("annual_position_field_invalid")
    else:
        if loss_family or residence_family:
            _reject("annual_position_field_invalid")


def _validate_non_foreign_context(result: AnnualPositionResult) -> None:
    if result.foreign_property_profit != ZERO:
        _reject("annual_position_field_invalid")
    unsupported = set(result.unsupported_families)
    if "foreign_property_loss_treatment" in unsupported or "foreign_property_residence" in unsupported:
        _reject("annual_position_field_invalid")
    limitations = set(result.limitations)
    if (
        "foreign_property_loss_relief_not_supported" in limitations
        or "residence_facts_incomplete" in limitations
        or "outside_supported_uk_resident_case" in limitations
    ):
        _reject("annual_position_field_invalid")


# ── Normalised internal shapes (reconstructed, never aliased to inputs) ───────

@dataclass(frozen=True)
class _NormalisedObservation:
    observation_id: str
    user_id: str
    provider: str
    connected_organisation_id: str
    business_id: str
    import_run_id: str
    api_name: str
    api_version: str
    resource: str
    adapter_version: str
    record_id: str
    source_record_digest: str
    source_fields: tuple[str, ...]
    source_definitions: tuple[str, ...]
    source_schema_id: str | None
    revision_id: str | None
    retrieved_at: datetime
    created_at: datetime | None
    updated_at: datetime | None
    effective_at: datetime | None
    transformation: str | None
    rounding: str | None

    @property
    def source_record_key(self) -> tuple:
        """Canonical stable source-record identity from the normalisation contract.

        Two distinct observations that resolve to the same underlying provider
        source record share this key and must be rejected as double counting,
        even when import run, digest, revision, schema, adapter/API version,
        timestamps or source field/definition snapshots differ. The already
        enforced shared user/provider/connection/business identity keeps the user
        consistent, so only provider, connection, business, resource and record
        identify the underlying record.
        """
        return (
            self.provider,
            self.connected_organisation_id,
            self.business_id,
            self.resource,
            self.record_id,
        )


@dataclass(frozen=True)
class _NormalisedInput:
    input_id: str
    economic_event_id: str
    classification: str
    recognised_amount: Decimal
    evidence_observation_ids: tuple[str, ...]
    contributed_amount: Decimal
    allowable_fraction: Decimal
    prohibited_uses: tuple[str, ...]


def _normalise_observation(obs: object) -> _NormalisedObservation:
    obs = _exact_dataclass(obs, SourceObservation, "observation_type_invalid")

    observation_id = _exact_nonempty_str(obs.observation_id, "observation_id_invalid")

    provenance = _exact_dataclass(obs.provenance, Provenance, "observation_provenance_invalid")
    identity = _exact_dataclass(provenance.identity, SourceIdentity, "observation_identity_invalid")

    user_id = _exact_nonempty_str(identity.user_id, "observation_user_id_invalid")
    provider = _exact_type(identity.provider, AccountingProviderName, "observation_provider_invalid")
    connected_organisation_id = _exact_nonempty_str(
        identity.connected_organisation_id, "observation_connection_invalid"
    )
    business_id = _exact_nonempty_str(identity.business_id, "observation_business_invalid")
    import_run_id = _exact_nonempty_str(identity.import_run_id, "observation_import_run_invalid")

    record_id = _exact_nonempty_str(provenance.record_id, "observation_record_id_invalid")
    source_record_digest = _exact_nonempty_str(
        provenance.source_record_digest, "observation_source_digest_invalid"
    )
    api_name = _exact_nonempty_str(provenance.api_name, "observation_api_name_invalid")
    api_version = _exact_nonempty_str(provenance.api_version, "observation_api_version_invalid")
    resource = _exact_nonempty_str(provenance.resource, "observation_resource_invalid")
    adapter_version = _exact_nonempty_str(
        provenance.adapter_version, "observation_adapter_version_invalid"
    )
    retrieved_at = _exact_datetime(provenance.retrieved_at, "observation_retrieved_at_invalid")
    source_fields = _exact_str_tuple(
        provenance.source_fields, "observation_source_fields_invalid", allow_empty=False
    )
    source_definitions = _exact_str_tuple(
        provenance.source_definitions, "observation_source_definitions_invalid", allow_empty=True
    )
    source_schema_id = _exact_optional_str(
        provenance.source_schema_id, "observation_source_schema_invalid"
    )
    transformation = _exact_optional_str(
        provenance.transformation, "observation_transformation_invalid"
    )
    rounding = _exact_optional_str(provenance.rounding, "observation_rounding_invalid")
    revision_id = _exact_optional_str(provenance.revision_id, "observation_revision_invalid")
    created_at = _exact_optional_datetime(provenance.created_at, "observation_created_at_invalid")
    updated_at = _exact_optional_datetime(provenance.updated_at, "observation_updated_at_invalid")
    effective_at = _exact_optional_datetime(provenance.effective_at, "observation_effective_at_invalid")

    evidence_state = _exact_type(obs.evidence_state, EvidenceState, "observation_evidence_state_invalid")
    if evidence_state is not EvidenceState.SELECTED:
        _reject("observation_evidence_not_selected")
    _exact_optional_str(obs.evidence_reason, "observation_evidence_reason_invalid")
    _exact_optional_str(obs.raw_evidence_reference, "observation_raw_evidence_reference_invalid")
    if _exact_str_tuple(obs.missing_fields, "observation_missing_fields_invalid", allow_empty=True):
        _reject("observation_evidence_incomplete")
    if _exact_str_tuple(
        obs.competing_observation_ids, "observation_competing_ids_invalid", allow_empty=True
    ):
        _reject("observation_evidence_conflicting")

    return _NormalisedObservation(
        observation_id=observation_id,
        user_id=user_id,
        provider=provider.value,
        connected_organisation_id=connected_organisation_id,
        business_id=business_id,
        import_run_id=import_run_id,
        api_name=api_name,
        api_version=api_version,
        resource=resource,
        adapter_version=adapter_version,
        record_id=record_id,
        source_record_digest=source_record_digest,
        source_fields=source_fields,
        source_definitions=source_definitions,
        source_schema_id=source_schema_id,
        revision_id=revision_id,
        retrieved_at=retrieved_at,
        created_at=created_at,
        updated_at=updated_at,
        effective_at=effective_at,
        transformation=transformation,
        rounding=rounding,
    )


def _normalise_input(input_: object, tax_year: str, business_id: str) -> _NormalisedInput:
    input_ = _exact_dataclass(input_, CanonicalAccountingTaxInput, "input_type_invalid")

    input_id = _exact_nonempty_str(input_.input_id, "input_id_invalid")
    economic_event_id = _exact_nonempty_str(input_.economic_event_id, "economic_event_id_invalid")

    purpose = _exact_nonempty_str(input_.purpose, "purpose_invalid")
    if purpose != _SUPPORTED_PURPOSE:
        _reject("purpose_unsupported")
    scope = _exact_nonempty_str(input_.scope, "scope_invalid")
    if scope != _SUPPORTED_SCOPE:
        _reject("scope_unsupported")

    input_business_id = _exact_nonempty_str(input_.business_id, "input_business_id_invalid")
    if input_business_id != business_id:
        _reject("business_identity_mismatch")

    input_tax_year = input_.tax_year
    if type(input_tax_year) is not str or input_tax_year != tax_year:
        _reject("tax_year_mismatch")

    classification = _exact_nonempty_str(input_.classification, "classification_invalid")
    if classification in _REJECTED_CLASSIFICATIONS or classification not in (_TURNOVER, _EXPENSE):
        _reject("classification_unsupported")

    recognised_amount = _exact_positive_decimal(input_.recognised_amount, "recognised_amount_invalid")
    recognised_amount = _derive_monetary(recognised_amount, "monetary_value_unrepresentable")
    recognised_date = _exact_date(input_.recognised_date, "recognised_date_invalid")
    if not (_TAX_YEAR_START <= recognised_date <= _TAX_YEAR_END):
        _reject("recognised_date_out_of_period")
    currency = _exact_nonempty_str(input_.currency, "currency_invalid")
    base_currency = _exact_nonempty_str(input_.base_currency, "base_currency_invalid")
    if currency != base_currency:
        _reject("currency_base_currency_mismatch")
    if currency != _SUPPORTED_CURRENCY:
        _reject("currency_unsupported")
    _exact_nonempty_str(input_.recognition_decision_id, "recognition_decision_id_invalid")
    _exact_nonempty_str(input_.policy_version, "policy_version_invalid")

    evidence_observation_ids = _exact_str_tuple(
        input_.evidence_observation_ids, "evidence_observation_ids_invalid", allow_empty=False
    )

    permitted_uses = _exact_str_tuple(
        input_.permitted_uses, "permitted_uses_invalid", allow_empty=False
    )
    if _TAX_ESTIMATE_USE not in permitted_uses:
        _reject("purpose_not_permitted")
    prohibited_uses = _exact_str_tuple(
        input_.prohibited_uses, "prohibited_uses_invalid", allow_empty=True
    )
    if _TAX_ESTIMATE_USE in prohibited_uses:
        _reject("purpose_prohibited")

    if input_.ownership_adjustment is not None:
        _reject("ownership_adjustment_unsupported")
    if input_.uncertainty is not None:
        _reject("input_uncertainty_unsupported")

    if classification == _TURNOVER:
        if input_.allowability is not None or input_.allowability_decision_id is not None:
            _reject("turnover_unexpected_allowability")
        fraction = ONE
        contributed = recognised_amount
    else:
        decision = input_.allowability
        if decision is None:
            _reject("expense_missing_allowability")
        decision = _exact_dataclass(decision, AllowabilityDecision, "allowability_invalid")

        decision_id = _exact_nonempty_str(decision.decision_id, "allowability_decision_id_invalid")
        supplied_decision_id = input_.allowability_decision_id
        if type(supplied_decision_id) is not str or supplied_decision_id != decision_id:
            _reject("allowability_id_contradiction")

        outcome = _exact_type(decision.outcome, AllowabilityOutcome, "allowability_outcome_invalid")
        authority = _exact_type(decision.authority, DecisionAuthority, "allowability_authority_invalid")
        if authority is not DecisionAuthority.RESERVED_RULE:
            _reject("allowability_authority_unsupported")
        _exact_datetime(decision.decided_at, "allowability_decided_at_invalid")
        _exact_nonempty_str(decision.reason, "allowability_reason_invalid")
        if decision.provider_assertion is not None:
            _reject("allowability_provider_assertion_unsupported")

        decision_source_ids = _exact_unique_str_tuple(
            decision.source_observation_ids, "allowability_source_observation_ids_invalid",
            allow_empty=True,
        )
        if decision_source_ids != evidence_observation_ids:
            _reject("allowability_evidence_unbound")

        outcome_value = outcome.value
        if outcome_value == _ALLOWABLE:
            if decision.allowable_fraction is not None:
                _reject("allowability_fraction_invalid")
            fraction = ONE
        elif outcome_value == _DISALLOWABLE:
            if decision.allowable_fraction is not None:
                _reject("allowability_fraction_invalid")
            fraction = ZERO
        elif outcome_value == _MIXED_APPORTIONED:
            raw_fraction = decision.allowable_fraction
            if (
                type(raw_fraction) is not Decimal
                or not raw_fraction.is_finite()
                or not (ZERO < raw_fraction < ONE)
            ):
                _reject("allowability_fraction_invalid")
            fraction = raw_fraction
        else:
            _reject("allowability_outcome_unsupported")
        try:
            contributed = recognised_amount * fraction
        except _DECIMAL_ARITHMETIC_ERRORS:
            _reject("monetary_value_unrepresentable")

    contributed = _derive_monetary(contributed, "monetary_value_unrepresentable")

    return _NormalisedInput(
        input_id=input_id,
        economic_event_id=economic_event_id,
        classification=classification,
        recognised_amount=recognised_amount,
        evidence_observation_ids=evidence_observation_ids,
        contributed_amount=contributed,
        allowable_fraction=fraction,
        prohibited_uses=prohibited_uses,
    )


# ── Public internal result types ──────────────────────────────────────────────

@dataclass(frozen=True)
class HandoffFact:
    """One emitted aggregate fact passed to the annual engine."""

    name: str
    value: Decimal


@dataclass(frozen=True)
class HandoffContribution:
    """One input's resolved, de-duplicated contribution to the fact set."""

    input_id: str
    economic_event_id: str
    classification: str
    recognised_amount: Decimal
    allowable_fraction: Decimal
    contributed_amount: Decimal


@dataclass(frozen=True)
class HandoffSourceRecord:
    """Complete immutable evidence identity that supported one observation.

    Every field is a reconstructed immutable value derived from the validated
    ``SourceIdentity``/``Provenance``; no caller-owned object is retained, so
    the result's provenance, equality and hash fully reflect a change to any
    part of the validated evidence identity.
    """

    observation_id: str
    user_id: str
    provider: str
    connected_organisation_id: str
    business_id: str
    import_run_id: str
    api_name: str
    api_version: str
    resource: str
    adapter_version: str
    record_id: str
    source_record_digest: str
    source_fields: tuple[str, ...]
    source_definitions: tuple[str, ...]
    source_schema_id: str | None
    revision_id: str | None
    retrieved_at: datetime
    created_at: datetime | None
    updated_at: datetime | None
    effective_at: datetime | None
    transformation: str | None
    rounding: str | None


@dataclass(frozen=True)
class HandoffInputEvidence:
    """Per-input binding to its exact evidence observations and source records."""

    input_id: str
    economic_event_id: str
    observation_ids: tuple[str, ...]
    source_records: tuple[HandoffSourceRecord, ...]


@dataclass(frozen=True)
class AccountingTaxHandoffProvenance:
    """Immutable, deterministic provenance for the handoff result."""

    business_id: str
    user_id: str
    connected_organisation_id: str
    provider: str
    tax_year: str
    input_ids: tuple[str, ...]
    economic_event_ids: tuple[str, ...]
    observation_ids: tuple[str, ...]
    input_evidence: tuple[HandoffInputEvidence, ...]
    limitations: tuple[str, ...]
    prohibited_uses: tuple[str, ...]


@dataclass(frozen=True)
class AccountingTaxHandoffResult:
    """Calculated annual position plus immutable, deterministic provenance."""

    annual_position: AnnualPositionResult
    facts: tuple[HandoffFact, ...]
    contributions: tuple[HandoffContribution, ...]
    provenance: AccountingTaxHandoffProvenance

    def facts_mapping(self) -> Mapping[str, Decimal]:
        """Return the emitted facts as a read-only mapping."""
        return MappingProxyType({fact.name: fact.value for fact in self.facts})


# ── Public boundary function ──────────────────────────────────────────────────

def calculate_annual_position_from_accounting(
    *,
    tax_year: str,
    business_type: object,
    inputs: object,
    observations: object,
) -> AccountingTaxHandoffResult:
    """Derive one supported business-income fact set and calculate the position.

    ``business_type`` must be the exact ``BusinessType`` enum; ``inputs`` and
    ``observations`` must be finite non-empty built-in containers of exact
    ``CanonicalAccountingTaxInput`` and ``SourceObservation`` values. Every
    cross-user, cross-connection, cross-business, cross-provider, forged,
    duplicated, unresolved or unsupported input fails closed.
    """
    if type(tax_year) is not str or tax_year != _SUPPORTED_TAX_YEAR:
        _reject("tax_year_unsupported")

    # Exact BusinessType enum only; strings, subclasses and unsupported values
    # fail closed. This declaration is never inferred from provider text.
    business_kind = _exact_type(business_type, BusinessType, "business_type_invalid")
    if business_kind.value not in _SUPPORTED_BUSINESS_TYPES:
        _reject("business_type_unsupported")
    business_kind = business_kind.value

    if type(inputs) not in (tuple, list):
        _reject("inputs_container_invalid")
    inputs = tuple(inputs)
    if not inputs:
        _reject("inputs_empty")

    if type(observations) not in (tuple, list):
        _reject("observations_container_invalid")
    observations = tuple(observations)

    # Resolve observations first: their identity is the single source of
    # user/connection/provider identity for the whole bundle.
    observation_by_id: dict[str, _NormalisedObservation] = {}
    seen_source_keys: set[tuple] = set()
    shared_identity: tuple[str, str, str, str] | None = None
    for obs in observations:
        normalised = _normalise_observation(obs)
        if normalised.observation_id in observation_by_id:
            _reject("observation_id_duplicate")
        source_key = normalised.source_record_key
        if source_key in seen_source_keys:
            _reject("source_record_duplicate")
        seen_source_keys.add(source_key)
        observation_by_id[normalised.observation_id] = normalised
        identity = (
            normalised.user_id,
            normalised.provider,
            normalised.connected_organisation_id,
            normalised.business_id,
        )
        if shared_identity is None:
            shared_identity = identity
        elif identity != shared_identity:
            _reject("observation_identity_mismatch")

    if shared_identity is None:
        _reject("observations_empty")
    user_id, provider, connected_organisation_id, business_id = shared_identity

    # Normalise inputs and derive the single supported fact set.
    seen_input_ids: set[str] = set()
    seen_event_ids: set[str] = set()
    all_evidence_ids: list[str] = []
    normalised_inputs: list[_NormalisedInput] = []
    turnover_total = ZERO
    allowable_expense_total = ZERO
    prohibited_uses: set[str] = set()

    for input_ in inputs:
        normalised = _normalise_input(input_, tax_year, business_id)
        if normalised.input_id in seen_input_ids:
            _reject("input_id_duplicate")
        if normalised.economic_event_id in seen_event_ids:
            _reject("economic_event_id_duplicate")
        seen_input_ids.add(normalised.input_id)
        seen_event_ids.add(normalised.economic_event_id)
        all_evidence_ids.extend(normalised.evidence_observation_ids)
        normalised_inputs.append(normalised)
        prohibited_uses.update(normalised.prohibited_uses)

        if normalised.classification == _TURNOVER:
            turnover_total = _add_monetary(
                turnover_total, normalised.recognised_amount, "monetary_value_unrepresentable"
            )
        else:
            allowable_expense_total = _add_monetary(
                allowable_expense_total, normalised.contributed_amount, "monetary_value_unrepresentable"
            )

    # Resolve evidence: every reference maps to exactly one supplied observation,
    # the set is complete, and no IDs are duplicated or unreferenced.
    if len(all_evidence_ids) != len(set(all_evidence_ids)):
        _reject("evidence_id_duplicate")
    evidence_set = set(all_evidence_ids)
    observation_set = set(observation_by_id)
    if evidence_set != observation_set:
        if evidence_set - observation_set:
            _reject("observation_missing")
        _reject("observation_extra")

    if business_kind == "trade":
        profit = _subtract_monetary(
            turnover_total, allowable_expense_total, "monetary_value_unrepresentable"
        )
        if profit < ZERO:
            _reject("trade_loss_unsupported")
        facts: dict[str, Decimal] = {"sole_trade_profit": profit}
    elif business_kind == "uk_property":
        facts = {
            "uk_property_receipts": turnover_total,
            "uk_property_allowable_expenses": allowable_expense_total,
        }
    else:  # foreign_property
        facts = {
            "foreign_property_gross_receipts": turnover_total,
            "foreign_property_allowable_expenses": allowable_expense_total,
        }

    for fact_value in facts.values():
        _derive_monetary(fact_value, "monetary_value_unrepresentable")

    try:
        annual_position = calculate_annual_position(facts, tax_year)
    except Exception:
        _reject("annual_position_engine_failure")
    annual_position = _validate_annual_position_result(annual_position)
    _validate_handoff_context(
        annual_position, business_kind, turnover_total, allowable_expense_total
    )

    emitted_facts = tuple(
        HandoffFact(name=name, value=value) for name, value in sorted(facts.items())
    )
    contributions = tuple(
        HandoffContribution(
            input_id=item.input_id,
            economic_event_id=item.economic_event_id,
            classification=item.classification,
            recognised_amount=item.recognised_amount,
            allowable_fraction=item.allowable_fraction,
            contributed_amount=item.contributed_amount,
        )
        for item in sorted(normalised_inputs, key=lambda item: item.input_id)
    )
    input_evidence = tuple(
        HandoffInputEvidence(
            input_id=item.input_id,
            economic_event_id=item.economic_event_id,
            observation_ids=tuple(sorted(item.evidence_observation_ids)),
            source_records=tuple(
                HandoffSourceRecord(
                    observation_id=observation_id,
                    user_id=observation_by_id[observation_id].user_id,
                    provider=observation_by_id[observation_id].provider,
                    connected_organisation_id=observation_by_id[observation_id].connected_organisation_id,
                    business_id=observation_by_id[observation_id].business_id,
                    import_run_id=observation_by_id[observation_id].import_run_id,
                    api_name=observation_by_id[observation_id].api_name,
                    api_version=observation_by_id[observation_id].api_version,
                    resource=observation_by_id[observation_id].resource,
                    adapter_version=observation_by_id[observation_id].adapter_version,
                    record_id=observation_by_id[observation_id].record_id,
                    source_record_digest=observation_by_id[observation_id].source_record_digest,
                    source_fields=observation_by_id[observation_id].source_fields,
                    source_definitions=observation_by_id[observation_id].source_definitions,
                    source_schema_id=observation_by_id[observation_id].source_schema_id,
                    revision_id=observation_by_id[observation_id].revision_id,
                    retrieved_at=observation_by_id[observation_id].retrieved_at,
                    created_at=observation_by_id[observation_id].created_at,
                    updated_at=observation_by_id[observation_id].updated_at,
                    effective_at=observation_by_id[observation_id].effective_at,
                    transformation=observation_by_id[observation_id].transformation,
                    rounding=observation_by_id[observation_id].rounding,
                )
                for observation_id in sorted(item.evidence_observation_ids)
            ),
        )
        for item in sorted(normalised_inputs, key=lambda item: item.input_id)
    )
    provenance = AccountingTaxHandoffProvenance(
        business_id=business_id,
        user_id=user_id,
        connected_organisation_id=connected_organisation_id,
        provider=provider,
        tax_year=tax_year,
        input_ids=tuple(sorted(seen_input_ids)),
        economic_event_ids=tuple(sorted(seen_event_ids)),
        observation_ids=tuple(sorted(observation_set)),
        input_evidence=input_evidence,
        limitations=_HANDOFF_LIMITATIONS,
        prohibited_uses=tuple(sorted(prohibited_uses)),
    )

    return AccountingTaxHandoffResult(
        annual_position=annual_position,
        facts=emitted_facts,
        contributions=contributions,
        provenance=provenance,
    )
