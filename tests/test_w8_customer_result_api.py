"""Adversarial acceptance for the W8-S2B deterministic customer API payload."""
from __future__ import annotations

import inspect
import json
import pickle
import re
from copy import copy, deepcopy
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from reserved.api import w8_customer_result as api
from reserved.api.w8_customer_result import (
    PAYLOAD_SCHEMA_VERSION,
    w8_customer_result_payload_json,
)
from reserved.services.w2_customer_language import (
    CONTRACT_VERSION as W2_CONTRACT_VERSION,
    EvidenceClassification,
    FundingClassification,
    ObligationFact,
    ObligationKind,
    PresentationStatus,
    W2PresentationInput,
    present_w2_customer_language,
)
from reserved.services.w8_customer_result import (
    SupportedNation,
    W8CustomerResult,
    compose_w8_customer_result,
    w8_customer_result_identity,
)
from tests.test_annual_to_cash_integration import annual_position, compose
from tests.test_w8_annual_cash_customer_handoff import project

ROOT = Path(__file__).resolve().parents[1]
MODULE_SOURCE = (ROOT / "reserved" / "api" / "w8_customer_result.py").read_text()

USER_ID = "user-england-001"
BUSINESS_ID = "business-england-001"
PAYLOAD_REFUSED = "customer API payload refused"
_DIGEST_SHAPE = re.compile(r"^w8-customer-result:sha256-[0-9a-f]{64}$")


@pytest.mark.parametrize("nation", ["England", "Wales", "Northern Ireland"])
def test_api_serialises_the_end_to_end_producer_issued_nation(nation):
    annual_cash = compose(annual=annual_position(nation))
    customer_result = project(annual_cash)
    assert customer_result is not None
    payload = json.loads(
        w8_customer_result_payload_json(
            customer_result, user_id="user-1", business_id="business-1"
        )
    )
    assert payload["nation"] == nation
    assert payload["tax_year"] == "2026/27"


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


def _compose_result(**overrides) -> W8CustomerResult:
    base = dict(
        value=_w2_input(),
        nation="England",
        tax_year="2026/27",
        user_id=USER_ID,
        business_id=BUSINESS_ID,
        evidence_references=("annual:source-england-001", "cash:obligation-england-001"),
    )
    base.update(overrides)
    return compose_w8_customer_result(**base)


def _render(result=None, **owner_overrides) -> str:
    result = result if result is not None else _compose_result()
    return w8_customer_result_payload_json(
        result,
        user_id=owner_overrides.get("user_id", USER_ID),
        business_id=owner_overrides.get("business_id", BUSINESS_ID),
    )


def _money(value) -> dict[str, str | None]:
    return {"label": value.label, "amount": value.amount, "due_date": value.due_date}


def _expected_view(view) -> dict:
    return {
        "contract_version": view.contract_version,
        "safe_to_present": view.safe_to_present,
        "status_tone": view.status_tone,
        "status_heading": view.status_heading,
        "status_message": view.status_message,
        "evidence_label": view.evidence_label,
        "annual_liability": _money(view.annual_liability),
        "obligations": [_money(item) for item in view.obligations],
        "account_adjustments": [_money(item) for item in view.account_adjustments],
        "funding_heading": view.funding_heading,
        "funding_message": view.funding_message,
        "claim_to_reduce_heading": view.claim_to_reduce_heading,
        "claim_to_reduce_message": view.claim_to_reduce_message,
        "claim_to_reduce_warning": view.claim_to_reduce_warning,
        "no_payment_authority": view.no_payment_authority,
    }


def _assert_primitive_only(value, path="$"):
    if value is None or type(value) in (str, bool):
        return
    if type(value) is tuple:
        for index, item in enumerate(value):
            _assert_primitive_only(item, f"{path}[{index}]")
        return
    raise AssertionError(f"captured value is not an immutable primitive at {path}: {type(value).__name__}")


def _build_test_renderer(**overrides):
    """Build a private renderer with injected collaborators for hostile tests."""
    return api._build_renderer(**overrides)



class _StringSubclass(str):
    """A hostile str subtype that compares equal to canonical text."""


class _SubclassResult(W8CustomerResult):
    """A root subtype used to prove exact root-type enforcement."""


# ── 0. No caller-mintable or caller-resealable payload surface ──────────────

def test_no_public_payload_type_compose_or_render_callable_exists():
    for name in (
        "W8CustomerResultPayload",
        "compose_w8_customer_result_payload",
        "render_w8_customer_result_payload",
    ):
        assert not hasattr(api, name), f"unexpected public payload surface: {name}"


def test_single_public_operation_has_no_identity_or_view_parameters():
    signature = inspect.signature(w8_customer_result_payload_json)
    assert list(signature.parameters) == ["result", "user_id", "business_id"]
    assert signature.parameters["user_id"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["business_id"].kind is inspect.Parameter.KEYWORD_ONLY


def test_only_public_callable_is_the_single_atomic_operation():
    public_callables = [
        name for name in dir(api)
        if not name.startswith("_") and callable(getattr(api, name))
    ]
    assert public_callables == ["w8_customer_result_payload_json"]


def test_fabricated_well_shaped_result_identity_cannot_be_injected():
    result = _compose_result()
    true_identity = w8_customer_result_identity(result)
    parsed = json.loads(_render(result))
    assert parsed["w8_customer_result_identity"] == true_identity
    assert _DIGEST_SHAPE.fullmatch(parsed["w8_customer_result_identity"])
    with pytest.raises(ValueError) as exc:
        w8_customer_result_payload_json(  # type: ignore[call-arg]
            result,
            user_id=USER_ID,
            business_id=BUSINESS_ID,
            w8_customer_result_identity="w8-customer-result:sha256-" + "0" * 64,
        )
    assert str(exc.value) == PAYLOAD_REFUSED


def test_dataclasses_replace_cannot_mint_or_reseal_a_payload():
    # The separately constructible payload was removed entirely, so
    # ``dataclasses.replace`` has no accepted payload to reseal.
    assert not hasattr(api, "W8CustomerResultPayload")
    assert not hasattr(api, "render_w8_customer_result_payload")


def test_object_new_and_low_level_mutation_cannot_produce_renderable_state():
    forged = object.__new__(W8CustomerResult)
    with pytest.raises(ValueError) as exc:
        w8_customer_result_payload_json(
            forged, user_id=USER_ID, business_id=BUSINESS_ID
        )
    assert str(exc.value) == PAYLOAD_REFUSED

    result = _compose_result()
    object.__setattr__(
        result, "view", replace(result.view, status_message="Transfer hostile funds now")
    )
    with pytest.raises(ValueError) as exc:
        _render(result)
    assert str(exc.value) == PAYLOAD_REFUSED


def test_no_payload_object_exists_to_copy_deepcopy_or_pickle():
    assert not hasattr(api, "W8CustomerResultPayload")


@pytest.mark.parametrize("hostile_copy", [
    "Transfer hostile funds now",
    "This authorises a payment or transfer",
    "secret bearer token",
    "/etc/passwd",
    "C:\\Windows\\System32",
])
def test_arbitrary_or_hostile_customer_copy_cannot_be_introduced(hostile_copy):
    result = _compose_result()
    object.__setattr__(result, "view", replace(result.view, status_message=hostile_copy))
    with pytest.raises(ValueError) as exc:
        _render(result)
    assert str(exc.value) == PAYLOAD_REFUSED
    assert hostile_copy not in str(exc.value)


# ── 1. Determinism across repetitions and supported reconstruction ──────────

def test_payload_json_is_byte_string_identical_across_repetitions():
    result = _compose_result()
    rendered = [
        w8_customer_result_payload_json(
            result, user_id=USER_ID, business_id=BUSINESS_ID
        )
        for _ in range(5)
    ]
    assert all(item == rendered[0] for item in rendered)
    assert rendered[0] == _render(result)


def test_payload_json_is_ascii_stable_with_sorted_keys_and_fixed_separators():
    rendered = _render()
    assert rendered.isascii()
    parsed = json.loads(rendered)
    assert list(parsed.keys()) == sorted(parsed.keys())
    assert rendered == json.dumps(parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


# ── 2. Exact preservation of schema, nation, identity and view fields ───────

def test_schema_version_nation_and_result_identity_are_preserved_exactly():
    result = _compose_result()
    parsed = json.loads(_render(result))

    assert parsed["schema_version"] == PAYLOAD_SCHEMA_VERSION
    assert parsed["nation"] == result.nation.value
    assert parsed["nation"] == SupportedNation.ENGLAND.value
    assert parsed["tax_year"] == result.tax_year == "2026/27"
    assert parsed["w8_customer_result_identity"] == w8_customer_result_identity(result)
    assert _DIGEST_SHAPE.fullmatch(parsed["w8_customer_result_identity"])


def test_mutated_or_malformed_result_tax_year_is_refused_atomically():
    result = _compose_result()
    object.__setattr__(result, "tax_year", "2027/28")
    with pytest.raises(ValueError) as exc:
        _render(result)
    assert str(exc.value) == PAYLOAD_REFUSED


def test_rebound_tax_year_helper_or_grammar_cannot_revalidate_malformed_state(monkeypatch):
    import reserved.services.w8_customer_result as result_module

    result = _compose_result()
    object.__setattr__(result, "tax_year", "not-a-tax-year")
    monkeypatch.setattr(result_module, "_validate_tax_year", lambda value: value)
    monkeypatch.setattr(result_module, "_TAX_YEAR", re.compile(r".*"))
    with pytest.raises(ValueError) as exc:
        _render(result)
    assert str(exc.value) == PAYLOAD_REFUSED

    malformed = _compose_result()
    object.__setattr__(malformed, "tax_year", "2026/26")
    with pytest.raises(ValueError) as exc:
        _render(malformed)
    assert str(exc.value) == PAYLOAD_REFUSED


def test_every_reviewed_presentation_field_is_preserved_exactly():
    result = _compose_result()
    parsed = json.loads(_render(result))
    assert parsed["view"] == _expected_view(result.view)
    assert parsed["view"] == _expected_view(present_w2_customer_language(_w2_input()))


def test_fixed_limitations_and_prohibited_uses_are_preserved_exactly():
    result = _compose_result()
    parsed = json.loads(_render(result))
    assert parsed["limitations"] == list(result.limitations)
    assert parsed["prohibited_uses"] == list(result.prohibited_uses)
    assert parsed["limitations"] == [
        "presentation_facts_only",
        "not_a_current_hmrc_bill",
        "surplus_not_available_cash",
    ]
    assert parsed["prohibited_uses"] == [
        "no_payment_or_transfer_authority",
        "self_assessment_filing",
        "financial_advice",
        "persistence_or_storage",
        "production_or_provider_activation",
    ]


@pytest.mark.parametrize("nation", ["England", "Wales", "Northern Ireland"])
def test_each_supported_nation_is_rendered_without_internal_enum(nation):
    result = compose_w8_customer_result(
        _w2_input(),
        nation=nation,
        tax_year="2026/27",
        user_id=f"user-{nation.replace(' ', '-').lower()}",
        business_id=f"business-{nation.replace(' ', '-').lower()}",
        evidence_references=("annual:source-england-001",),
    )
    parsed = json.loads(_render(result, user_id=result.user_id, business_id=result.business_id))
    assert parsed["nation"] == nation
    assert type(parsed["nation"]) is str


# ── 3. Output is JSON-native and contains no internal object ─────────────────

def _assert_json_native(value, path="$"):
    if value is None or type(value) in (bool, int, str):
        return
    if type(value) is list:
        for index, item in enumerate(value):
            _assert_json_native(item, f"{path}[{index}]")
        return
    if type(value) is dict:
        for key, item in value.items():
            assert type(key) is str, f"non-string JSON key at {path}"
            _assert_json_native(item, f"{path}.{key}")
        return
    raise AssertionError(f"non-JSON-native value at {path}: {type(value).__name__}")


def test_output_graph_is_entirely_json_native():
    parsed = json.loads(_render())
    _assert_json_native(parsed)


def test_output_contains_no_internal_type_or_repr_markers():
    rendered = _render()
    forbidden_markers = (
        "Decimal", "datetime", "date(", "__dataclass__", "__enum__", "__decimal__",
        "__date__", "SupportedNation", "MoneyLine", "W2CustomerLanguageView",
        "W8CustomerResult", "W2PresentationInput", "object at 0x", "_integrity_seal",
    )
    assert not [marker for marker in forbidden_markers if marker in rendered]


# ── 4. No owner IDs, raw evidence, source state or secrets leak ──────────────

def test_no_owner_references_or_raw_evidence_leak_into_output():
    rendered = _render()
    assert USER_ID not in rendered
    assert BUSINESS_ID not in rendered
    assert "annual:source-england-001" not in rendered
    assert "cash:obligation-england-001" not in rendered
    assert "presentation_input" not in rendered
    assert "evidence_references" not in rendered


@pytest.mark.parametrize("marker", [
    "secret", "token", "password", "credential", "apikey", "api_key",
    "bearer", "private_key", "sk_live", "sk_test", "access_key",
])
def test_no_secret_marker_leaks_into_output(marker):
    assert marker not in _render()


# ── 5. Wrong / swapped / malformed owner refs and subclasses fail identically ─

@pytest.mark.parametrize(
    "user_id, business_id",
    [
        ("user-wrong", BUSINESS_ID),
        (USER_ID, "business-wrong"),
        (BUSINESS_ID, USER_ID),  # swapped identities
        ("user-wrong", "business-wrong"),
        (None, BUSINESS_ID),
        (USER_ID, None),
        ("", BUSINESS_ID),
        (USER_ID, ""),
        (" bad id", BUSINESS_ID),
        (USER_ID, "business "),
        ("user:secret-token", BUSINESS_ID),
        (USER_ID, "business:password"),
    ],
)
def test_wrong_swapped_or_malformed_owner_refs_fail_identically_and_value_free(user_id, business_id):
    result = _compose_result()
    with pytest.raises(ValueError) as exc:
        w8_customer_result_payload_json(
            result, user_id=user_id, business_id=business_id
        )
    assert str(exc.value) == PAYLOAD_REFUSED
    assert repr(user_id) not in str(exc.value)
    assert repr(business_id) not in str(exc.value)


@pytest.mark.parametrize(
    "user_id, business_id",
    [
        (_StringSubclass(USER_ID), BUSINESS_ID),
        (USER_ID, _StringSubclass(BUSINESS_ID)),
        (_StringSubclass(USER_ID), _StringSubclass(BUSINESS_ID)),
    ],
)
def test_owner_reference_subclasses_fail_identically(user_id, business_id):
    result = _compose_result()
    with pytest.raises(ValueError) as exc:
        w8_customer_result_payload_json(
            result, user_id=user_id, business_id=business_id
        )
    assert str(exc.value) == PAYLOAD_REFUSED


# ── 6. Forged / mutated / subclassed / incomplete result state fails early ───

def test_forged_root_subclass_fails_before_serialization():
    hostile = object.__new__(_SubclassResult)
    with pytest.raises(ValueError) as exc:
        w8_customer_result_payload_json(
            hostile, user_id=USER_ID, business_id=BUSINESS_ID
        )
    assert str(exc.value) == PAYLOAD_REFUSED


def test_duck_typed_result_is_rejected_before_serialization():
    with pytest.raises(ValueError) as exc:
        w8_customer_result_payload_json(
            object(), user_id=USER_ID, business_id=BUSINESS_ID  # type: ignore[arg-type]
        )
    assert str(exc.value) == PAYLOAD_REFUSED


def test_mutated_view_fails_before_serialization():
    result = _compose_result()
    object.__setattr__(
        result, "view", replace(result.view, status_message="Transfer hostile funds now")
    )
    with pytest.raises(ValueError) as exc:
        _render(result)
    assert str(exc.value) == PAYLOAD_REFUSED


def test_incomplete_nested_dataclass_state_fails_before_serialization():
    result = _compose_result()
    object.__setattr__(result.view.annual_liability, "attacker_state", "payload")
    with pytest.raises(ValueError) as exc:
        _render(result)
    assert str(exc.value) == PAYLOAD_REFUSED


def test_nested_view_string_subclass_fails_before_serialization():
    result = _compose_result()
    object.__setattr__(
        result, "view", replace(result.view, status_heading=_StringSubclass(result.view.status_heading))
    )
    with pytest.raises(ValueError) as exc:
        _render(result)
    assert str(exc.value) == PAYLOAD_REFUSED


# ── 7. Duplicate / reordered / altered view or constraints cannot be emitted ─

def test_reordered_obligations_cannot_be_emitted():
    result = _compose_result()
    reordered = replace(result.view, obligations=tuple(reversed(result.view.obligations)))
    object.__setattr__(result, "view", reordered)
    with pytest.raises(ValueError) as exc:
        _render(result)
    assert str(exc.value) == PAYLOAD_REFUSED


def test_altered_constraints_cannot_be_emitted():
    result = _compose_result()
    object.__setattr__(result, "prohibited_uses", ("self_assessment_filing",))
    with pytest.raises(ValueError) as exc:
        _render(result)
    assert str(exc.value) == PAYLOAD_REFUSED


def test_duplicate_obligation_kind_cannot_be_emitted():
    value = _w2_input()
    duplicate = replace(value.obligations[1], kind=value.obligations[0].kind)
    bad = replace(value, obligations=(value.obligations[0], duplicate, value.obligations[2]))
    assert compose_w8_customer_result(
        bad,
        nation="England",
        tax_year="2026/27",
        user_id=USER_ID,
        business_id=BUSINESS_ID,
        evidence_references=("annual:source-england-001",),
    ) is None


def test_forged_view_or_constraints_fail_atomically():
    result = _compose_result()
    object.__setattr__(
        result, "view", replace(result.view, status_message="Hostile customer copy")
    )
    with pytest.raises(ValueError) as exc:
        _render(result)
    assert str(exc.value) == PAYLOAD_REFUSED


# ── 8. Bad money is rejected through full upstream revalidation ─────────────

@pytest.mark.parametrize("signed_zero", ["-0", "-0.0", "-0.00", "-0.000", "-0E+3"])
def test_signed_zero_money_is_rejected_through_upstream_revalidation(signed_zero):
    amount = Decimal(signed_zero)
    result = _compose_result()
    bad_input = _w2_input(annual_liability=amount)
    object.__setattr__(result, "presentation_input", bad_input)
    object.__setattr__(result, "view", present_w2_customer_language(bad_input))
    with pytest.raises(ValueError) as exc:
        _render(result)
    assert str(exc.value) == PAYLOAD_REFUSED


@pytest.mark.parametrize("bad_money", [Decimal("NaN"), Decimal("Infinity"), Decimal("-0.01")])
def test_non_finite_or_negative_money_is_rejected(bad_money):
    result = _compose_result()
    bad_input = _w2_input(annual_liability=bad_money)
    object.__setattr__(result, "presentation_input", bad_input)
    object.__setattr__(result, "view", present_w2_customer_language(bad_input))
    with pytest.raises(ValueError) as exc:
        _render(result)
    assert str(exc.value) == PAYLOAD_REFUSED


# ── 9. Identity and JSON are stable across copy / deepcopy / pickle of result ─

def test_identity_and_json_are_stable_across_result_reconstruction():
    result = _compose_result()
    identity = w8_customer_result_identity(result)
    rendered = _render(result)
    for transformed in (copy(result), deepcopy(result), pickle.loads(pickle.dumps(result))):
        assert w8_customer_result_identity(transformed) == identity
        assert _render(transformed) == rendered


# ── 10. Source / import audit proves prohibited dependencies are absent ─────

def test_module_imports_no_internal_network_persistence_or_auth_boundaries():
    forbidden = (
        "reserved.engines",
        "reserved.providers",
        "reserved.database",
        "reserved.web",
        "reserved.models",
        "reserved.auth",
        "reserved.config",
        "reserved.billing",
        "reserved.repositories",
        "reserved.extensions",
        "import requests",
        "import urllib",
        "import socket",
        "import subprocess",
        "from flask",
        "import flask",
        "Flask",
        "Blueprint",
        "jsonify",
    )
    assert not [token for token in forbidden if token in MODULE_SOURCE]


def test_module_imports_only_the_reviewed_w8_and_w2_contracts():
    imports = re.findall(r"^from\s+(reserved\S*)\s+import", MODULE_SOURCE, flags=re.MULTILINE)
    assert set(imports) == {
        "reserved.services.w2_customer_language",
        "reserved.services.w8_customer_result",
    }, f"unexpected reserved imports: {imports}"


# ── 11. Atomic projection correction: race, rebinding and hostile leakage ───


class _LyingValueError(ValueError):
    """A hostile ValueError subtype whose ``__str__`` lies about its payload."""

    def __str__(self) -> str:
        return "HOSTILE secret bearer token"


class _RaisingValueError(ValueError):
    """A hostile ValueError subtype whose ``__str__`` raises another error."""

    def __str__(self) -> str:
        raise RuntimeError("distinguishable __str__ explosion")


def _raiser(exc: Exception):
    def raise_(value: object):
        raise exc

    return raise_


def test_trace_hook_mutation_after_first_identity_validation_refuses():
    result = _compose_result()
    original_identity = api._identity
    calls = {"count": 0}

    def traced_identity(value):
        computed = original_identity(value)
        calls["count"] += 1
        if calls["count"] == 1:
            object.__setattr__(
                value,
                "view",
                replace(value.view, status_message="Transfer hostile funds now"),
            )
        return computed

    renderer = _build_test_renderer(identity=traced_identity)
    with pytest.raises(ValueError) as exc:
        renderer(result, user_id=USER_ID, business_id=BUSINESS_ID)
    assert str(exc.value) == PAYLOAD_REFUSED
    assert "Transfer hostile funds now" not in str(exc.value)


def test_mutation_during_serialization_cannot_alter_detached_output():
    result = _compose_result()
    expected = _render(result)
    original_serialize = api._json.dumps

    def mutating_serialize(graph, **kwargs):
        original_view = result.view
        object.__setattr__(
            result,
            "view",
            replace(result.view, status_message="Transfer hostile funds now"),
        )
        try:
            return original_serialize(graph, **kwargs)
        finally:
            object.__setattr__(result, "view", original_view)

    renderer = _build_test_renderer(serialize=mutating_serialize)
    rendered = renderer(result, user_id=USER_ID, business_id=BUSINESS_ID)

    assert rendered == expected
    assert "Transfer hostile funds now" not in rendered


def test_persistent_mutation_during_serialization_fails_closed():
    result = _compose_result()
    original_serialize = api._json.dumps

    def mutating_serialize(graph, **kwargs):
        object.__setattr__(
            result,
            "view",
            replace(result.view, status_message="Transfer hostile funds now"),
        )
        return original_serialize(graph, **kwargs)

    renderer = _build_test_renderer(serialize=mutating_serialize)
    with pytest.raises(ValueError) as exc:
        renderer(result, user_id=USER_ID, business_id=BUSINESS_ID)
    assert str(exc.value) == PAYLOAD_REFUSED


def test_rebinding_identity_collaborator_cannot_forge_identity(monkeypatch):
    result = _compose_result()
    forged = "w8-customer-result:sha256-" + "0" * 64
    monkeypatch.setattr(api, "_identity", lambda value: forged)
    parsed = json.loads(_render(result))
    assert parsed["w8_customer_result_identity"] == w8_customer_result_identity(result)
    assert parsed["w8_customer_result_identity"] != forged


def test_rebinding_owner_collaborator_cannot_accept_wrong_owners(monkeypatch):
    result = _compose_result()
    monkeypatch.setattr(api, "_owner_matches", lambda candidate, expected: True)
    with pytest.raises(ValueError) as exc:
        w8_customer_result_payload_json(
            result, user_id="user-wrong", business_id=BUSINESS_ID
        )
    assert str(exc.value) == PAYLOAD_REFUSED


def test_rebinding_projection_collaborator_cannot_emit_attacker_content(monkeypatch):
    result = _compose_result()
    monkeypatch.setattr(api, "_project_view", lambda value: {"status_message": "attacker-selected"})
    rendered = _render(result)
    assert "attacker-selected" not in rendered
    assert json.loads(rendered)["view"] == _expected_view(result.view)


def test_rebinding_serializer_collaborator_cannot_emit_attacker_content(monkeypatch):
    result = _compose_result()

    class _HostileJSON:
        @staticmethod
        def dumps(obj, **kwargs):
            return '"attacker-selected"'

    monkeypatch.setattr(api, "_json", _HostileJSON)
    rendered = _render(result)
    assert "attacker-selected" not in rendered
    assert json.loads(rendered)["view"] == _expected_view(result.view)


def test_hostile_value_error_subtype_is_collapsed_to_exact_builtin():
    result = _compose_result()
    hostile_exceptions = (
        _LyingValueError("hostile secret bearer token"),
        _RaisingValueError("hostile secret bearer token"),
    )
    for hostile in hostile_exceptions:
        renderer = _build_test_renderer(identity=_raiser(hostile))
        with pytest.raises(ValueError) as exc:
            renderer(result, user_id=USER_ID, business_id=BUSINESS_ID)
        caught = exc.value
        assert type(caught) is ValueError
        assert caught.args == (PAYLOAD_REFUSED,)
        assert str(caught) == PAYLOAD_REFUSED
        assert repr(caught) == "ValueError('customer API payload refused')"
        assert "hostile" not in str(caught)
        assert "secret" not in str(caught)
        assert "hostile" not in repr(caught)
        assert "secret" not in repr(caught)


def test_signature_level_invalid_calls_are_categorical():
    result = _compose_result()
    calls = [
        lambda: w8_customer_result_payload_json(result),
        lambda: w8_customer_result_payload_json(result, user_id=USER_ID),
        lambda: w8_customer_result_payload_json(result, business_id=BUSINESS_ID),
        lambda: w8_customer_result_payload_json(result, USER_ID, BUSINESS_ID),
        lambda: w8_customer_result_payload_json(
            result, user_id=USER_ID, business_id=BUSINESS_ID, unexpected=1
        ),
        lambda: w8_customer_result_payload_json(
            result,
            user_id=USER_ID,
            business_id=BUSINESS_ID,
            w8_customer_result_identity="w8-customer-result:sha256-" + "0" * 64,
        ),
    ]
    for call in calls:
        with pytest.raises(ValueError) as exc:
            call()
        assert str(exc.value) == PAYLOAD_REFUSED


def test_result_may_be_supplied_by_keyword_as_documented():
    result = _compose_result()
    assert w8_customer_result_payload_json(
        result=result, user_id=USER_ID, business_id=BUSINESS_ID
    ) == _render(result)


def test_direct_payload_construction_or_reconstruction_remains_unavailable():
    assert not hasattr(api, "W8CustomerResultPayload")
    assert not hasattr(api, "compose_w8_customer_result_payload")
    assert not hasattr(api, "render_w8_customer_result_payload")


def test_valid_output_remains_byte_deterministic_and_preserves_all_fields():
    result = _compose_result()
    rendered = [_render(result) for _ in range(3)]
    assert all(item == rendered[0] for item in rendered)
    parsed = json.loads(rendered[0])
    assert parsed["view"] == _expected_view(result.view)
    assert parsed["limitations"] == list(result.limitations)
    assert parsed["prohibited_uses"] == list(result.prohibited_uses)
    assert parsed["nation"] == result.nation.value
    assert parsed["w8_customer_result_identity"] == w8_customer_result_identity(result)


# ── 12. Detached snapshot correction: mutation, aliasing and rebinding ───────


def test_transient_user_id_mutation_during_owner_handling_cannot_authorize_wrong_owner():
    result = _compose_result()
    original_owner = api._owner_matches
    fired = {"count": 0}

    def mutating_owner(candidate, expected):
        # Transiently rewrite the live source owner to match the candidate, then
        # restore it before the post-capture identity check. If owner comparison
        # read the live source, a wrong owner would be authorised.
        fired["count"] += 1
        object.__setattr__(result, "user_id", candidate)
        try:
            return original_owner(candidate, expected)
        finally:
            object.__setattr__(result, "user_id", USER_ID)

    renderer = _build_test_renderer(owner_matches=mutating_owner)
    with pytest.raises(ValueError) as exc:
        renderer(result, user_id="user-wrong", business_id=BUSINESS_ID)
    assert str(exc.value) == PAYLOAD_REFUSED
    assert fired["count"] >= 1


def test_transient_view_field_mutation_during_projection_cannot_enter_json():
    result = _compose_result()
    expected_view = _expected_view(result.view)
    hostile = "Transfer hostile funds now"
    original_project = api._project_view
    fired = {"count": 0}

    def mutating_project(view_primitives):
        # Transiently rewrite the live source view's status_message; projection
        # must still read the immutable primitive capture, never the live source.
        fired["count"] += 1
        object.__setattr__(result.view, "status_message", hostile)
        try:
            return original_project(view_primitives)
        finally:
            object.__setattr__(
                result.view, "status_message", expected_view["status_message"]
            )

    renderer = _build_test_renderer(project_view=mutating_project)
    rendered = renderer(result, user_id=USER_ID, business_id=BUSINESS_ID)

    assert fired["count"] == 1
    assert hostile not in rendered
    assert json.loads(rendered)["view"] == expected_view


def test_coordinated_transient_mutations_during_capture_cannot_produce_accepted_output():
    result = _compose_result()
    original_capture = api._capture_snapshot
    fired = {"count": 0}

    def mutating_capture(source):
        # Coordinated mutation: replace both the presentation input and its
        # derived view with a consistently derived alternative so the primitive
        # capture would be internally valid but identity-distinct, then restore.
        fired["count"] += 1
        hostile_input = _w2_input(annual_liability=Decimal("9999.00"))
        hostile_view = present_w2_customer_language(hostile_input)
        original_input = source.presentation_input
        original_view = source.view
        object.__setattr__(source, "presentation_input", hostile_input)
        object.__setattr__(source, "view", hostile_view)
        try:
            return original_capture(source)
        finally:
            object.__setattr__(source, "presentation_input", original_input)
            object.__setattr__(source, "view", original_view)

    renderer = _build_test_renderer(capture_snapshot=mutating_capture)
    with pytest.raises(ValueError) as exc:
        renderer(result, user_id=USER_ID, business_id=BUSINESS_ID)
    assert str(exc.value) == PAYLOAD_REFUSED
    assert fired["count"] == 1


def test_capture_contains_only_immutable_primitives():
    result = _compose_result()
    capture = api._capture_snapshot(result)
    _assert_primitive_only(capture)
    assert capture[0][2] == result.tax_year


def test_mutating_reconstructed_snapshot_view_after_identity_cannot_enter_json():
    result = _compose_result()
    hostile = "Transfer hostile funds now"
    original_identity = api._identity

    def traced_identity(value):
        computed = original_identity(value)
        if value is not result:
            object.__setattr__(value.view, "status_message", hostile)
        return computed

    renderer = _build_test_renderer(identity=traced_identity)
    rendered = renderer(result, user_id=USER_ID, business_id=BUSINESS_ID)

    assert hostile not in rendered
    assert json.loads(rendered)["view"] == _expected_view(result.view)


def test_mutating_reconstructed_snapshot_owner_after_identity_cannot_authorize_wrong_owner():
    result = _compose_result()
    original_identity = api._identity

    def traced_identity(value):
        computed = original_identity(value)
        if value is not result:
            object.__setattr__(value, "user_id", "user-wrong")
        return computed

    renderer = _build_test_renderer(identity=traced_identity)
    with pytest.raises(ValueError) as exc:
        renderer(result, user_id="user-wrong", business_id=BUSINESS_ID)
    assert str(exc.value) == PAYLOAD_REFUSED


def test_mutation_during_final_identity_comparison_fails_closed():
    result = _compose_result()
    original_identity = api._identity
    calls = {"count": 0}

    def traced_identity(value):
        calls["count"] += 1
        if calls["count"] == 3 and value is result:
            # Mutate the live source before the post-serialization identity is
            # computed, so the final integrity comparison observes tampering.
            object.__setattr__(value, "user_id", "user-wrong")
        return original_identity(value)

    renderer = _build_test_renderer(identity=traced_identity)
    with pytest.raises(ValueError) as exc:
        renderer(result, user_id=USER_ID, business_id=BUSINESS_ID)
    assert str(exc.value) == PAYLOAD_REFUSED


def test_source_and_reconstructed_identities_agree_with_returned_content():
    result = _compose_result()
    source_identity = w8_customer_result_identity(result)
    capture = api._capture_snapshot(result)
    reconstructed = api._reconstruct_result(capture)
    assert w8_customer_result_identity(reconstructed) == source_identity
    rendered = _render(result)
    assert json.loads(rendered)["w8_customer_result_identity"] == source_identity


def test_public_callable_has_no_security_critical_writable_state():
    fn = w8_customer_result_payload_json
    assert fn.__defaults__ is None or fn.__defaults__ == ()
    assert fn.__kwdefaults__ is None or fn.__kwdefaults__ == {}
    security_critical = {
        "identity", "owner_matches", "capture_snapshot", "reconstruct_result",
        "project_view", "serialize", "schema_version", "refused", "render",
    }
    for key in security_critical:
        assert key not in getattr(fn, "__dict__", {})


def test_mutation_of_public_function_attributes_cannot_change_behaviour():
    result = _compose_result()
    fn = w8_customer_result_payload_json
    original_defaults = fn.__defaults__
    original_kwdefaults = fn.__kwdefaults__
    original_dict = dict(fn.__dict__)
    try:
        fn.__defaults__ = ("attacker",)
        fn.__kwdefaults__ = {"refused": "attacker-refusal", "render": lambda *a, **k: '"attacker"'}
        fn.__dict__["render"] = lambda *a, **k: '"attacker-selected"'
        fn.__dict__["refused"] = "attacker-refusal"
        fn.__dict__["owner_matches"] = lambda candidate, expected: True
        fn.__dict__["project_view"] = lambda value: {"status_message": "attacker-selected"}

        rendered = _render(result)
        assert "attacker-selected" not in rendered
        assert json.loads(rendered)["view"] == _expected_view(result.view)

        with pytest.raises(ValueError) as exc:
            w8_customer_result_payload_json(
                result, user_id="user-wrong", business_id=BUSINESS_ID
            )
        assert type(exc.value) is ValueError
        assert exc.value.args == (PAYLOAD_REFUSED,)
    finally:
        fn.__defaults__ = original_defaults
        fn.__kwdefaults__ = original_kwdefaults
        fn.__dict__.clear()
        fn.__dict__.update(original_dict)


def test_rebinding_outer_renderer_cannot_emit_attacker_content(monkeypatch):
    result = _compose_result()
    monkeypatch.setattr(api, "_render_payload_json", lambda *a, **k: '"attacker-selected"')
    rendered = _render(result)
    assert "attacker-selected" not in rendered
    assert json.loads(rendered)["view"] == _expected_view(result.view)


def test_rebinding_schema_constant_cannot_change_emitted_schema(monkeypatch):
    result = _compose_result()
    monkeypatch.setattr(api, "PAYLOAD_SCHEMA_VERSION", "attacker-schema")
    rendered = _render(result)
    assert json.loads(rendered)["schema_version"] == "reserved-w8-customer-api-payload/1.0"
    assert "attacker-schema" not in rendered


def test_rebinding_refusal_constant_cannot_change_fixed_refusal(monkeypatch):
    result = _compose_result()
    monkeypatch.setattr(api, "_PAYLOAD_REFUSED", "attacker-refusal")

    with pytest.raises(ValueError) as exc:
        w8_customer_result_payload_json(
            result, user_id="user-wrong", business_id=BUSINESS_ID
        )
    assert type(exc.value) is ValueError
    assert exc.value.args == (PAYLOAD_REFUSED,)
    assert str(exc.value) == PAYLOAD_REFUSED

    with pytest.raises(ValueError) as exc:
        w8_customer_result_payload_json(result)  # missing owners -> same refusal
    assert str(exc.value) == PAYLOAD_REFUSED


def test_rebinding_snapshot_helper_cannot_change_snapshot(monkeypatch):
    result = _compose_result()
    forged = _compose_result(value=_w2_input(annual_liability=Decimal("9999.00")))
    monkeypatch.setattr(api, "_capture_snapshot", lambda source: forged)
    rendered = _render(result)
    assert json.loads(rendered)["view"] == _expected_view(result.view)
    assert (
        json.loads(rendered)["w8_customer_result_identity"]
        == w8_customer_result_identity(result)
    )


def test_malformed_binding_refusal_is_exact_builtin_valueerror():
    result = _compose_result()
    calls = [
        lambda: w8_customer_result_payload_json(result),
        lambda: w8_customer_result_payload_json(result, user_id=USER_ID),
        lambda: w8_customer_result_payload_json(result, business_id=BUSINESS_ID),
        lambda: w8_customer_result_payload_json(result, USER_ID, BUSINESS_ID),
        lambda: w8_customer_result_payload_json(
            result, user_id=USER_ID, business_id=BUSINESS_ID, unexpected=1
        ),
    ]
    for call in calls:
        with pytest.raises(ValueError) as exc:
            call()
        assert type(exc.value) is ValueError
        assert exc.value.args == (PAYLOAD_REFUSED,)
        assert repr(exc.value) == "ValueError('customer API payload refused')"
