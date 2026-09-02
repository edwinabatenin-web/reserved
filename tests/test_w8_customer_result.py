"""Adversarial acceptance for the W8-S2A public result projection contract."""
from __future__ import annotations

import re
import pickle
from copy import copy, deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from reserved.services.w2_customer_language import (
    CONTRACT_VERSION as W2_CONTRACT_VERSION,
    AdjustmentFact,
    AdjustmentKind,
    EvidenceClassification,
    FundingClassification,
    ObligationFact,
    ObligationKind,
    PresentationStatus,
    W2PresentationInput,
    present_w2_customer_language,
)
from reserved.services.w8_customer_result import (
    CONTRACT_VERSION,
    SupportedNation,
    W8CustomerResult,
    compose_w8_customer_result,
    w8_customer_result_identity,
)
from tests.test_internal_tax_boundary import INTERNAL_MODULE_MARKERS

ROOT = Path(__file__).resolve().parents[1]
MODULE_SOURCE = (ROOT / "reserved" / "services" / "w8_customer_result.py").read_text()

_DIGEST_SHAPE = re.compile(r"^w8-customer-result:sha256-[0-9a-f]{64}$")


def _w2_input(**overrides) -> W2PresentationInput:
    base = dict(
        contract_version=W2_CONTRACT_VERSION,
        status=PresentationStatus.READY,
        evidence=EvidenceClassification.HMRC_CONFIRMED_EXACT,
        annual_liability=Decimal("3486.00"),
        obligations=(
            ObligationFact(ObligationKind.BALANCING_PAYMENT, Decimal("1286.00"), date(2027, 1, 31)),
            ObligationFact(ObligationKind.FIRST_PAYMENT_ON_ACCOUNT, Decimal("1100.00"), date(2027, 1, 31)),
            ObligationFact(ObligationKind.SECOND_PAYMENT_ON_ACCOUNT, Decimal("1100.00"), date(2027, 7, 31)),
        ),
        adjustments=(),
        funding=FundingClassification.EXACT,
        funding_amount=None,
        claim_to_reduce=None,
    )
    base.update(overrides)
    return W2PresentationInput(**base)


def _kwargs(**overrides) -> dict:
    base = dict(
        value=_w2_input(),
        nation="England",
        user_id="user-england-001",
        business_id="business-england-001",
        evidence_references=("annual:source-england-001", "cash:obligation-england-001"),
    )
    base.update(overrides)
    return base


def _compose(**overrides) -> W8CustomerResult | None:
    return compose_w8_customer_result(**_kwargs(**overrides))


class _GeographyString(str):
    """A str subclass used to prove geography subclasses are rejected."""


class _SubclassInput(W2PresentationInput):
    """A W2 input subclass used to prove exact-type enforcement."""


class _StringSubclass(str):
    """A hostile string subtype that compares equal to canonical text."""


class _TupleSubclass(tuple):
    """A hostile tuple subtype that compares equal to canonical constraints."""


def _direct_result(result: W8CustomerResult, **overrides) -> W8CustomerResult:
    values = dict(
        contract_version=result.contract_version,
        nation=result.nation,
        user_id=result.user_id,
        business_id=result.business_id,
        presentation_input=result.presentation_input,
        view=result.view,
        evidence_references=result.evidence_references,
        limitations=result.limitations,
        prohibited_uses=result.prohibited_uses,
    )
    values.update(overrides)
    return W8CustomerResult(**values)


# ── 1. Supported nations yield an immutable result carrying the exact W2 view ──

@pytest.mark.parametrize("nation", ["England", "Wales", "Northern Ireland"])
def test_supported_nations_yield_result_with_exact_w2_view(nation):
    result = _compose(nation=nation)
    assert isinstance(result, W8CustomerResult)
    assert result.nation is SupportedNation(nation)
    assert result.view == present_w2_customer_language(_w2_input())
    assert result.view.safe_to_present is True


def test_result_is_frozen_and_slotted():
    result = _compose()
    assert hasattr(W8CustomerResult, "__slots__")
    with pytest.raises((FrozenInstanceError, AttributeError)):
        result.nation = SupportedNation.WALES  # type: ignore[misc]


# ── 2. Unsupported / ambiguous geography fails closed without value leakage ──

@pytest.mark.parametrize(
    "value",
    [
        "Scotland",
        "Scottish",
        "scottish",
        "SCOTLAND",
        "UK",
        "GB",
        "United Kingdom",
        "Ireland",
        "IE",
        "england",
        "England ",
        " Northern Ireland",
        "",
        "   ",
        "GB-ENG",
        "France",
        None,
    ],
)
def test_unsupported_or_ambiguous_geography_fails_closed(value):
    with pytest.raises(ValueError) as exc:
        _compose(nation=value)
    assert "unsupported geography" in str(exc.value).lower()
    assert repr(value) not in str(exc.value)


@pytest.mark.parametrize(
    "value",
    [True, False, 1, 0, 123, -1, 3.5, ["England"], {"country": "England"}, ("England",)],
)
def test_hostile_geography_fails_without_value_leakage(value):
    with pytest.raises(ValueError) as exc:
        _compose(nation=value)
    assert repr(value) not in str(exc.value)


def test_geography_subclass_is_rejected():
    with pytest.raises(ValueError):
        _compose(nation=_GeographyString("England"))


# ── 3. Ownership binding: missing, conflicting and cross-owner facts fail ────

def test_user_business_equality_is_cross_owner_and_fails():
    with pytest.raises(ValueError, match="must be distinct"):
        _compose(user_id="same-owner", business_id="same-owner")


@pytest.mark.parametrize(
    "field, value",
    [
        ("user_id", None),
        ("user_id", ""),
        ("user_id", "bad id"),
        ("user_id", "user:secret-token"),
        ("business_id", None),
        ("business_id", ""),
        ("business_id", "business:password"),
    ],
)
def test_missing_conflicting_or_secret_ownership_fails(field, value):
    with pytest.raises(ValueError):
        _compose(**{field: value})


def test_cross_owner_substitution_changes_identity():
    original = _compose()
    swapped = _compose(user_id="user-england-002")
    assert w8_customer_result_identity(original) != w8_customer_result_identity(swapped)


# ── 4. Evidence references: duplicates, missing, malformed, payloads, secrets ─

def test_duplicate_evidence_reference_fails():
    with pytest.raises(ValueError, match="duplicate"):
        _compose(
            evidence_references=("annual:source-england-001", "annual:source-england-001")
        )


@pytest.mark.parametrize("value", [(), None, []])
def test_missing_evidence_references_fail(value):
    with pytest.raises(ValueError):
        _compose(evidence_references=value)


@pytest.mark.parametrize(
    "value",
    [
        (""),
        (" "),
        ("has space"),
        ("bad{payload}"),
        ("bad\u0000ref"),
        (""),
        (1,),
        (None,),
    ],
)
def test_malformed_evidence_reference_fails(value):
    with pytest.raises(ValueError):
        _compose(evidence_references=value)


def test_raw_payload_mapping_evidence_fails():
    with pytest.raises(ValueError):
        _compose(evidence_references=({"annual": "source"},))
    with pytest.raises(ValueError):
        _compose(evidence_references=(["annual:source"],))


def test_digest_reference_evidence_is_provenance_mismatch():
    with pytest.raises(ValueError, match="provenance mismatch"):
        _compose(
            evidence_references=("annual:source-england-001", "annual:sha256-" + "a" * 64)
        )


def test_secret_evidence_reference_fails():
    with pytest.raises(ValueError):
        _compose(evidence_references=("annual:source-england-001", "cash:sk_live_abc"))


# ── 5. W2 input: bool/float/non-finite money, malformed dates, hostile state ─

@pytest.mark.parametrize(
    "overrides",
    [
        {"annual_liability": Decimal("NaN")},
        {"annual_liability": Decimal("Infinity")},
        {"annual_liability": Decimal("-0.01")},
        {"annual_liability": 3486.00},
        {"annual_liability": True},
        {"evidence": None},
        {"status": PresentationStatus.REVIEW_REQUIRED},
        {"obligations": list(_w2_input().obligations)},
        {"funding": FundingClassification.GAP, "funding_amount": Decimal("0.00")},
    ],
)
def test_w2_input_fails_closed_and_returns_none(overrides):
    value = _w2_input(**overrides)
    assert present_w2_customer_language(value).safe_to_present is False
    assert compose_w8_customer_result(**_kwargs(value=value)) is None


def test_malformed_obligation_date_returns_none():
    facts = _w2_input()
    bad = replace(facts.obligations[0], due_date="2027-01-31")
    value = replace(facts, obligations=(bad,) + facts.obligations[1:])
    assert compose_w8_customer_result(**_kwargs(value=value)) is None


def test_duplicate_obligation_kind_returns_none():
    facts = _w2_input()
    duplicate = replace(facts.obligations[1], kind=facts.obligations[0].kind)
    value = replace(facts, obligations=(facts.obligations[0], duplicate, facts.obligations[2]))
    assert compose_w8_customer_result(**_kwargs(value=value)) is None


def test_w2_input_subclass_is_rejected():
    subclassed = _SubclassInput(
        W2_CONTRACT_VERSION,
        PresentationStatus.READY,
        EvidenceClassification.HMRC_CONFIRMED_EXACT,
        Decimal("3486.00"),
        _w2_input().obligations,
        (),
        FundingClassification.EXACT,
        None,
        None,
    )
    assert compose_w8_customer_result(**_kwargs(value=subclassed)) is None


# ── 6. Valid copy/deepcopy/pickle preserve identity only where supported ─────

def test_valid_copy_deepcopy_and_pickle_preserve_identity():
    result = _compose()
    identity = w8_customer_result_identity(result)
    assert w8_customer_result_identity(copy(result)) == identity
    assert w8_customer_result_identity(deepcopy(result)) == identity
    assert w8_customer_result_identity(pickle.loads(pickle.dumps(result))) == identity


@pytest.mark.parametrize("protocol", ["copy", "deepcopy", "pickle", "identity", "hash"])
def test_hostile_mutated_constraints_are_rejected_by_all_public_protocols(protocol):
    result = _compose()
    object.__setattr__(result, "prohibited_uses", ("self_assessment_filing",))

    with pytest.raises(ValueError, match="prohibited uses"):
        if protocol == "copy":
            copy(result)
        elif protocol == "deepcopy":
            deepcopy(result)
        elif protocol == "pickle":
            pickle.dumps(result)
        elif protocol == "identity":
            w8_customer_result_identity(result)
        else:
            hash(result)


# ── 7. Identity is deterministic and content-sensitive ───────────────────────

def test_identity_is_a_deterministic_digest_reference():
    result = _compose()
    identity = w8_customer_result_identity(result)
    assert _DIGEST_SHAPE.fullmatch(identity)
    assert w8_customer_result_identity(_compose()) == identity


@pytest.mark.parametrize(
    "overrides",
    [
        {"nation": "Wales"},
        {"user_id": "user-wales-001"},
        {"business_id": "business-wales-001"},
        {"evidence_references": ("annual:source-wales-001",)},
    ],
)
def test_identity_changes_with_geography_owner_or_evidence(overrides):
    assert w8_customer_result_identity(_compose()) != w8_customer_result_identity(
        _compose(**overrides)
    )


def test_identity_changes_with_amount_obligation_and_classification():
    base = w8_customer_result_identity(_compose())

    changed_amount = _w2_input(annual_liability=Decimal("9999.00"))
    changed_obligation = _w2_input(
        obligations=(
            ObligationFact(ObligationKind.BALANCING_PAYMENT, Decimal("9999.00"), date(2027, 1, 31)),
            _w2_input().obligations[1],
            _w2_input().obligations[2],
        )
    )
    changed_classification = _w2_input(evidence=EvidenceClassification.QUALIFIED_LOCAL_ESTIMATE)

    for value in (changed_amount, changed_obligation, changed_classification):
        result = compose_w8_customer_result(**_kwargs(value=value))
        assert w8_customer_result_identity(result) != base


# ── 8. Limitations and prohibited uses are fixed machine-readable constraints ─

def test_limitations_and_prohibited_uses_are_fixed():
    result = _compose()
    assert result.prohibited_uses == (
        "no_payment_or_transfer_authority",
        "self_assessment_filing",
        "financial_advice",
        "persistence_or_storage",
        "production_or_provider_activation",
    )
    assert result.limitations == (
        "presentation_facts_only",
        "not_a_current_hmrc_bill",
        "surplus_not_available_cash",
    )


def test_forged_weakened_limitations_fail_closed():
    result = _compose()
    with pytest.raises(ValueError):
        _direct_result(result, prohibited_uses=("self_assessment_filing",))


def test_forged_w2_wording_is_rejected_by_direct_construction_and_replace():
    result = _compose()
    forged_view = replace(
        result.view,
        status_heading="Pay now",
        status_message="Transfer the amount immediately.",
    )

    with pytest.raises(ValueError, match="not derived"):
        _direct_result(result, view=forged_view)
    with pytest.raises(ValueError, match="not derived"):
        replace(result, view=forged_view)


def test_forged_w2_wording_cannot_receive_identity_after_low_level_mutation():
    result = _compose()
    object.__setattr__(
        result,
        "view",
        replace(result.view, status_message="Transfer the amount immediately."),
    )
    with pytest.raises(ValueError, match="not derived"):
        w8_customer_result_identity(result)


@pytest.mark.parametrize("field", ["limitations", "prohibited_uses"])
def test_constraint_tuple_subclasses_are_rejected(field):
    result = _compose()
    with pytest.raises(ValueError, match=field.replace("_", " ")):
        _direct_result(result, **{field: _TupleSubclass(getattr(result, field))})


def test_result_contract_version_string_subclass_is_rejected():
    result = _compose()
    with pytest.raises(ValueError, match="contract version"):
        _direct_result(result, contract_version=_StringSubclass(CONTRACT_VERSION))


def test_w2_input_contract_version_string_subclass_fails_closed():
    value = replace(
        _w2_input(), contract_version=_StringSubclass(W2_CONTRACT_VERSION)
    )
    assert compose_w8_customer_result(**_kwargs(value=value)) is None


def test_w2_input_tuple_subclass_fails_closed():
    value = replace(
        _w2_input(), obligations=_TupleSubclass(_w2_input().obligations)
    )
    assert compose_w8_customer_result(**_kwargs(value=value)) is None


def test_nested_w2_view_string_subclass_is_rejected_even_when_text_matches():
    result = _compose()
    forged_view = replace(
        result.view, status_heading=_StringSubclass(result.view.status_heading)
    )
    with pytest.raises(ValueError, match="status_heading"):
        _direct_result(result, view=forged_view)


@pytest.mark.parametrize("target", ["input", "view", "money_line"])
def test_undeclared_nested_dataclass_state_is_rejected(target):
    result = _compose()
    if target == "input":
        object.__setattr__(result.presentation_input, "attacker_state", "payload")
    elif target == "view":
        object.__setattr__(result.view, "attacker_state", "payload")
    else:
        object.__setattr__(result.view.annual_liability, "attacker_state", "payload")
    with pytest.raises(ValueError, match="shape"):
        w8_customer_result_identity(result)


@pytest.mark.parametrize(
    "protocol", ["identity", "equality", "hash", "copy", "deepcopy", "pickle"]
)
def test_coherent_in_place_input_and_view_rewrite_fails_integrity(protocol):
    result = _compose()
    rewritten_input = _w2_input(annual_liability=Decimal("9999.00"))
    object.__setattr__(result, "presentation_input", rewritten_input)
    object.__setattr__(result, "view", present_w2_customer_language(rewritten_input))

    with pytest.raises(ValueError, match="integrity mismatch"):
        if protocol == "identity":
            w8_customer_result_identity(result)
        elif protocol == "equality":
            result == _compose()
        elif protocol == "hash":
            hash(result)
        elif protocol == "copy":
            copy(result)
        elif protocol == "deepcopy":
            deepcopy(result)
        else:
            pickle.dumps(result)


def test_fresh_coherent_distinct_result_construction_is_valid_and_distinct():
    original = _compose()
    distinct_input = _w2_input(annual_liability=Decimal("9999.00"))
    distinct = _direct_result(
        original,
        presentation_input=distinct_input,
        view=present_w2_customer_language(distinct_input),
    )
    assert w8_customer_result_identity(distinct) != w8_customer_result_identity(original)


def test_integrity_seal_is_not_a_public_constructor_or_replace_input():
    result = _compose()
    with pytest.raises(TypeError):
        _direct_result(result, _integrity_seal="attacker-controlled")
    with pytest.raises(TypeError, match="init=False"):
        replace(result, _integrity_seal="attacker-controlled")


def test_invalid_self_is_validated_before_equality_type_dispatch():
    result = _compose()
    object.__setattr__(result, "view", replace(result.view, status_message="hostile"))
    with pytest.raises(ValueError):
        result == None  # noqa: E711 - intentionally exercises unrelated-type dispatch


def test_repr_is_categorical_and_never_discloses_invalid_state():
    result = _compose()
    assert repr(result) == "W8CustomerResult(<validated>)"
    object.__setattr__(result, "user_id", "user:secret-attacker-identifier")
    object.__setattr__(
        result, "view", replace(result.view, status_message="Transfer hostile funds now")
    )
    rendered = repr(result)
    assert rendered == "W8CustomerResult(<invalid-state>)"
    assert "secret" not in rendered
    assert "Transfer" not in rendered
    assert "self_assessment_filing" not in rendered


@pytest.mark.parametrize("signed_zero", ["-0", "-0.0", "-0.00", "-0.000", "-0E+3"])
@pytest.mark.parametrize("position", ["annual", "obligation", "adjustment", "funding"])
def test_every_w2_monetary_signed_zero_family_fails_closed(signed_zero, position):
    amount = Decimal(signed_zero)
    base = _w2_input()
    if position == "annual":
        value = replace(base, annual_liability=amount)
    elif position == "obligation":
        obligation = replace(base.obligations[0], amount=amount)
        value = replace(base, obligations=(obligation,) + base.obligations[1:])
    elif position == "adjustment":
        adjustment = AdjustmentFact(AdjustmentKind.PAYMENTS_MADE, amount)
        value = replace(base, adjustments=(adjustment,))
    else:
        value = replace(
            base, funding=FundingClassification.GAP, funding_amount=amount
        )
    assert compose_w8_customer_result(**_kwargs(value=value)) is None
    with pytest.raises(ValueError, match="presentation input"):
        _direct_result(
            _compose(),
            presentation_input=value,
            view=present_w2_customer_language(value),
        )


# ── 9. Customer wording is sourced from W2 and no new advice is introduced ───

def test_customer_wording_is_sourced_from_w2_contract():
    result = _compose()
    expected = present_w2_customer_language(_w2_input())
    assert result.view == expected
    assert result.view.no_payment_authority == "This view does not authorise a payment or transfer."
    # Ownership and evidence identifiers are bound, not rendered as customer copy.
    assert "user-england-001" not in result.view.status_message
    assert "annual:source-england-001" not in result.view.status_message


# ── 10. No internal, network, persistence, route or provider side effect ─────

def test_module_imports_no_internal_or_network_boundaries():
    forbidden = (
        "reserved.engines",
        "reserved.providers",
        "reserved.database",
        "reserved.web",
        "reserved.models",
        "reserved.auth",
        "reserved.config",
        "import requests",
        "import urllib",
        "import socket",
        "import subprocess",
    )
    assert not [token for token in forbidden if token in MODULE_SOURCE]


def test_module_contains_no_internal_annual_markers():
    assert not [marker for marker in INTERNAL_MODULE_MARKERS if marker in MODULE_SOURCE]


def test_builder_is_pure_and_deterministic():
    first = _compose()
    second = _compose()
    assert first == second
    assert w8_customer_result_identity(first) == w8_customer_result_identity(second)
