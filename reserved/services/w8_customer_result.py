"""Fail-closed W8-S2A public result projection contract.

This module is the smallest pure, network-inert customer-facing projection
boundary for an eventual approved annual/cash result. It exposes only
deliberately copied presentation facts, reuses the already-reviewed W2
customer-language contract, binds the supported launch geography and opaque
source/evidence identities, and fails closed without importing or serialising
any internal tax-engine object.

It does not connect the provider/canonical-to-annual-tax handoff, add a route,
persist a result, activate a provider, calculate tax or cash, or invent new
customer wording. It is a view-model sub-boundary only. This value contract
detects inconsistent, subtype-bearing and post-construction rewritten state.
It is not a tamper-proof boundary against arbitrary in-process code capable of
rewriting every protected field, including the private integrity seal.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from reserved.services.w2_customer_language import (
    AdjustmentFact,
    AdjustmentKind,
    ClaimToReduceState,
    EvidenceClassification,
    FundingClassification,
    MoneyLine,
    ObligationFact,
    ObligationKind,
    PresentationStatus,
    W2CustomerLanguageView,
    W2PresentationInput,
    present_w2_customer_language,
)


CONTRACT_VERSION = "reserved-w8-customer-result/1.0"

# Reused repository identity grammars. These are the exact conventions already
# reviewed for opaque source/evidence and ownership references; this package
# must not invent a new permissive grammar.
_REFERENCE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
# A derived content identity is not an opaque source reference; substituting it
# for one is a provenance mismatch.
_DIGEST_REFERENCE = re.compile(r"^[a-z-]+:sha256-[0-9a-f]{64}$")
_TAX_YEAR = re.compile(r"^[0-9]{4}/[0-9]{2}$")

# Fixed machine-readable constraints. They are retained verbatim and must not
# be removed or weakened by any caller.
_LIMITATIONS = (
    "presentation_facts_only",
    "not_a_current_hmrc_bill",
    "surplus_not_available_cash",
)
_PROHIBITED_USES = (
    "no_payment_or_transfer_authority",
    "self_assessment_filing",
    "financial_advice",
    "persistence_or_storage",
    "production_or_provider_activation",
)

_SECRET_MARKERS = (
    "secret",
    "token",
    "password",
    "credential",
    "apikey",
    "api_key",
    "bearer",
    "private_key",
    "sk_live",
    "sk_test",
    "access_key",
)


class SupportedNation(str, Enum):
    """The exact closed October geography vocabulary accepted by W8-S3."""

    ENGLAND = "England"
    WALES = "Wales"
    NORTHERN_IRELAND = "Northern Ireland"


_NATION_BY_NAME = {member.value: member for member in SupportedNation}


@dataclass(frozen=True, slots=True, eq=False)
class W8CustomerResult:
    """Immutable provider-neutral public result projection.

    ``tax_year`` preserves the exact annual/cash producer period.
    ``user_id`` and ``business_id`` bind ownership for identity and provenance
    checks only; they are never customer copy. ``view`` is the exact reviewed
    W2 customer-language view. ``presentation_input`` retains the exact,
    customer-safe facts from which that view was derived so public construction
    and protocol reconstruction can prove the view was not forged.
    ``limitations`` and ``prohibited_uses`` are fixed machine-readable
    constraints.
    """

    contract_version: str
    nation: SupportedNation
    tax_year: str
    user_id: str
    business_id: str
    presentation_input: W2PresentationInput
    view: W2CustomerLanguageView
    evidence_references: tuple[str, ...]
    limitations: tuple[str, ...]
    prohibited_uses: tuple[str, ...]
    _integrity_seal: str = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        _validate_result_state(self)
        object.__setattr__(self, "_integrity_seal", _expected_integrity_seal(self))
        _validate_result(self)

    def __repr__(self) -> str:
        try:
            _validate_result(self)
        except Exception:
            return "W8CustomerResult(<invalid-state>)"
        return "W8CustomerResult(<validated>)"

    def __copy__(self) -> W8CustomerResult:
        _validate_result(self)
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> W8CustomerResult:
        _validate_result(self)
        memo[id(self)] = self
        return self

    def __reduce__(self) -> tuple[object, tuple[object, ...]]:
        # Pickle/copy reconstruction must pass through the same public
        # constructor and complete validation as ordinary construction.
        _validate_result(self)
        return (_rebuild_result, _result_components(self))

    def __eq__(self, other: object) -> bool:
        _validate_result(self)
        if type(other) is not W8CustomerResult:
            return False
        _validate_result(other)
        return _result_components(self) == _result_components(other)

    def __hash__(self) -> int:
        _validate_result(self)
        return hash(_result_components(self))


def _validate_exact_optional_string(value: object, field_name: str) -> None:
    if value is not None and type(value) is not str:
        raise ValueError(f"invalid W2 view {field_name}")


def _validate_dataclass_shape(value: object, expected_type: type, field_name: str) -> None:
    """Reject undeclared state attached through low-level in-process mutation."""
    if type(value) is not expected_type:
        raise ValueError(f"invalid {field_name}")
    expected_fields = {field.name for field in fields(expected_type)}
    if set(vars(value)) != expected_fields:
        raise ValueError(f"invalid {field_name} shape")


def _validate_money_line(value: object, field_name: str) -> None:
    _validate_dataclass_shape(value, MoneyLine, f"W2 view {field_name}")
    if type(value.label) is not str or type(value.amount) is not str:
        raise ValueError(f"invalid W2 view {field_name}")
    _validate_exact_optional_string(value.due_date, field_name)


def _validate_w2_input(value: object) -> W2PresentationInput:
    """Require exact built-ins throughout the reviewed W2 input graph."""
    _validate_dataclass_shape(
        value, W2PresentationInput, "W2 presentation input"
    )
    if type(value.contract_version) is not str:
        raise ValueError("invalid W2 presentation input contract version")
    if type(value.status) is not PresentationStatus:
        raise ValueError("invalid W2 presentation input status")
    if value.evidence is not None and type(value.evidence) is not EvidenceClassification:
        raise ValueError("invalid W2 presentation input evidence")
    if value.annual_liability is not None and type(value.annual_liability) is not Decimal:
        raise ValueError("invalid W2 presentation input annual liability")
    _reject_signed_zero(value.annual_liability, "annual liability")
    if type(value.obligations) is not tuple or type(value.adjustments) is not tuple:
        raise ValueError("invalid W2 presentation input collections")
    for item in value.obligations:
        _validate_dataclass_shape(item, ObligationFact, "W2 presentation input obligation")
        if (
            type(item.kind) is not ObligationKind
            or type(item.amount) is not Decimal
            or type(item.due_date) is not date
        ):
            raise ValueError("invalid W2 presentation input obligation")
        _reject_signed_zero(item.amount, "obligation amount")
    for item in value.adjustments:
        _validate_dataclass_shape(item, AdjustmentFact, "W2 presentation input adjustment")
        if (
            type(item.kind) is not AdjustmentKind
            or type(item.amount) is not Decimal
        ):
            raise ValueError("invalid W2 presentation input adjustment")
        _reject_signed_zero(item.amount, "adjustment amount")
    if value.funding is not None and type(value.funding) is not FundingClassification:
        raise ValueError("invalid W2 presentation input funding")
    if value.funding_amount is not None and type(value.funding_amount) is not Decimal:
        raise ValueError("invalid W2 presentation input funding amount")
    _reject_signed_zero(value.funding_amount, "funding amount")
    if value.claim_to_reduce is not None and type(value.claim_to_reduce) is not ClaimToReduceState:
        raise ValueError("invalid W2 presentation input claim state")

    # The reviewed W2 boundary owns value-level validation. Requiring its exact
    # successful result avoids copying that policy or any customer wording here.
    expected = present_w2_customer_language(value)
    if type(expected) is not W2CustomerLanguageView or expected.safe_to_present is not True:
        raise ValueError("public result requires a presentable W2 input")
    return value


def _reject_signed_zero(value: object, field_name: str) -> None:
    if type(value) is Decimal and value.is_zero() and value.is_signed():
        raise ValueError(f"invalid W2 presentation input {field_name}")


def _validate_w2_view(value: object) -> W2CustomerLanguageView:
    """Reject subtype-bearing or otherwise non-canonical W2 view graphs."""
    _validate_dataclass_shape(value, W2CustomerLanguageView, "W2 view")
    if type(value.contract_version) is not str or type(value.safe_to_present) is not bool:
        raise ValueError("invalid W2 view contract state")
    for field_name in (
        "status_tone",
        "status_heading",
        "status_message",
        "evidence_label",
        "no_payment_authority",
    ):
        if type(getattr(value, field_name)) is not str:
            raise ValueError(f"invalid W2 view {field_name}")
    for field_name in (
        "funding_heading",
        "funding_message",
        "claim_to_reduce_heading",
        "claim_to_reduce_message",
        "claim_to_reduce_warning",
    ):
        _validate_exact_optional_string(getattr(value, field_name), field_name)
    if value.annual_liability is not None:
        _validate_money_line(value.annual_liability, "annual_liability")
    if type(value.obligations) is not tuple or type(value.account_adjustments) is not tuple:
        raise ValueError("invalid W2 view collections")
    for item in value.obligations:
        _validate_money_line(item, "obligations")
    for item in value.account_adjustments:
        _validate_money_line(item, "account_adjustments")
    return value


def _validate_fixed_constraints(
    value: object, expected: tuple[str, ...], field_name: str
) -> None:
    if type(value) is not tuple or any(type(item) is not str for item in value):
        raise ValueError(f"public result {field_name} were altered")
    if value != expected:
        raise ValueError(f"public result {field_name} were altered")


def _validate_tax_year(
    value: object,
    *,
    _pattern: re.Pattern[str] = _TAX_YEAR,
    _integer: type[int] = int,
) -> str:
    """Require conventional UK ``YYYY/YY`` using import-bound primitives."""
    if type(value) is not str or not _pattern.fullmatch(value):
        raise ValueError("invalid public result tax year")
    if _integer(value[-2:]) != (_integer(value[:4]) + 1) % 100:
        raise ValueError("invalid public result tax year")
    return value


def _validate_result_state(
    value: object,
    _tax_year_validator: object = _validate_tax_year,
) -> W8CustomerResult:
    """Validate all public result state without relying on the private seal."""
    if type(value) is not W8CustomerResult:
        raise ValueError("public result must be an exact W8CustomerResult")
    if type(value.contract_version) is not str or value.contract_version != CONTRACT_VERSION:
        raise ValueError("unsupported public result contract version")
    if type(value.nation) is not SupportedNation:
        raise ValueError("unsupported public result geography")
    _tax_year_validator(value.tax_year)  # type: ignore[operator]
    _validate_owner_reference(value.user_id, "user")
    _validate_owner_reference(value.business_id, "business")
    if value.user_id == value.business_id:
        raise ValueError("user and business ownership must be distinct")

    presentation_input = _validate_w2_input(value.presentation_input)
    view = _validate_w2_view(value.view)
    expected_view = present_w2_customer_language(presentation_input)
    if view.safe_to_present is not True or view != expected_view:
        raise ValueError("public result view was not derived from its W2 input")

    _validate_evidence_references(value.evidence_references)
    _validate_fixed_constraints(value.limitations, _LIMITATIONS, "limitations")
    _validate_fixed_constraints(value.prohibited_uses, _PROHIBITED_USES, "prohibited uses")
    return value


def _validate_result(value: object) -> W8CustomerResult:
    """Central complete validation for construction, protocols and identity."""
    result = _validate_result_state(value)
    seal = getattr(result, "_integrity_seal", None)
    if type(seal) is not str or not hmac.compare_digest(
        seal, _expected_integrity_seal(result)
    ):
        raise ValueError("public result integrity mismatch")
    return result


def _result_components(value: W8CustomerResult) -> tuple[object, ...]:
    return (
        value.contract_version,
        value.nation,
        value.tax_year,
        value.user_id,
        value.business_id,
        value.presentation_input,
        value.view,
        value.evidence_references,
        value.limitations,
        value.prohibited_uses,
    )


def _rebuild_result(*values: object) -> W8CustomerResult:
    return W8CustomerResult(*values)  # type: ignore[arg-type]


def _validate_nation(value: object) -> SupportedNation:
    if type(value) is not str:
        raise ValueError("unsupported geography for the public result")
    nation = _NATION_BY_NAME.get(value)
    if nation is None:
        raise ValueError("unsupported geography for the public result")
    return nation


def _validate_owner_reference(value: object, subject: str) -> None:
    if type(value) is not str or not _REFERENCE.fullmatch(value):
        raise ValueError(f"invalid {subject} ownership reference")
    lowered = value.lower()
    if any(marker in lowered for marker in _SECRET_MARKERS):
        raise ValueError(f"invalid {subject} ownership reference")


def _validate_evidence_references(value: object) -> None:
    if type(value) is not tuple:
        raise ValueError("source or evidence references must be a tuple")
    if not value:
        raise ValueError("source or evidence references are required")
    seen: set[str] = set()
    for item in value:
        if type(item) is not str or not _SOURCE_ID.fullmatch(item):
            raise ValueError("invalid source or evidence reference")
        if _DIGEST_REFERENCE.fullmatch(item):
            raise ValueError("source or evidence reference provenance mismatch")
        lowered = item.lower()
        if any(marker in lowered for marker in _SECRET_MARKERS):
            raise ValueError("invalid source or evidence reference")
        if item in seen:
            raise ValueError("duplicate source or evidence reference")
        seen.add(item)


def _compose_w8_customer_result_impl(
    value: W2PresentationInput,
    *,
    nation: str,
    tax_year: str,
    user_id: str,
    business_id: str,
    evidence_references: tuple[str, ...],
    _tax_year_validator: object,
) -> W8CustomerResult | None:
    """Build a public result projection, or return ``None`` when W2 fails closed.

    Customer wording and view state are obtained solely through the reviewed
    W2 customer-language contract. Geography, ownership and evidence references
    are revalidated here and reject invalid input with categorical, value-free
    errors. When the W2 language boundary itself fails closed, no public result
    is produced.
    """
    try:
        _validate_w2_input(value)
    except ValueError:
        return None
    view = present_w2_customer_language(value)

    canonical_nation = _validate_nation(nation)
    canonical_tax_year = _tax_year_validator(tax_year)  # type: ignore[operator]
    _validate_owner_reference(user_id, "user")
    _validate_owner_reference(business_id, "business")
    if user_id == business_id:
        raise ValueError("user and business ownership must be distinct")
    _validate_evidence_references(evidence_references)

    return W8CustomerResult(
        CONTRACT_VERSION,
        canonical_nation,
        canonical_tax_year,
        user_id,
        business_id,
        value,
        view,
        evidence_references,
        _LIMITATIONS,
        _PROHIBITED_USES,
    )


def _make_public_composer(implementation, tax_year_validator):
    """Capture the tax-year authority outside mutable module-global names."""

    def compose_w8_customer_result(
        value: W2PresentationInput,
        *,
        nation: str,
        tax_year: str,
        user_id: str,
        business_id: str,
        evidence_references: tuple[str, ...],
    ) -> W8CustomerResult | None:
        return implementation(
            value,
            nation=nation,
            tax_year=tax_year,
            user_id=user_id,
            business_id=business_id,
            evidence_references=evidence_references,
            _tax_year_validator=tax_year_validator,
        )

    return compose_w8_customer_result


compose_w8_customer_result = _make_public_composer(
    _compose_w8_customer_result_impl, _validate_tax_year
)


def _canonical(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "__dataclass__": type(value).__name__,
            "__fields__": {
                field.name: _canonical(getattr(value, field.name))
                for field in fields(value)
            },
        }
    if isinstance(value, Enum):
        return {"__enum__": f"{type(value).__name__}:{value.value}"}
    if type(value) is tuple:
        return [_canonical(item) for item in value]
    if type(value) is Decimal:
        return {"__decimal__": str(value)}
    if type(value) is date:
        return {"__date__": value.isoformat()}
    if value is None or type(value) in (str, bool, int):
        return value
    raise ValueError("unsupported public result identity value type")


def _content_digest(value: W8CustomerResult) -> str:
    canonical = _canonical(_result_components(value))
    payload = json.dumps(
        canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _expected_integrity_seal(value: W8CustomerResult) -> str:
    return f"w8-result-seal:sha256-{_content_digest(value)}"


def w8_customer_result_identity(value: W8CustomerResult) -> str:
    """Return the deterministic immutable identity of a public result."""
    _validate_result(value)
    return f"w8-customer-result:sha256-{_content_digest(value)}"
