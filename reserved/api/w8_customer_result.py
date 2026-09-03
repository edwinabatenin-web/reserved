"""Fail-closed W8-S2B deterministic customer API payload projection.

This module is the smallest pure, network-inert JSON projection boundary that
consumes the already-reviewed
``reserved.services.w8_customer_result.W8CustomerResult`` and returns one
deterministic JSON-safe customer response only after the result has been reduced
to a fully validated, immutable primitive capture and matched to the exact owner
pair.

It copies only the reviewed customer-facing W2 view fields (without
recalculating or reinterpreting them), the supported ``nation``, the exact
producer-bound ``tax_year``, the
deterministic ``w8_customer_result_identity`` and the fixed customer-safe
``limitations`` / ``prohibited_uses`` already carried by the reviewed result.
It never exposes ``user_id``, ``business_id``, ``presentation_input``, raw
evidence references, provider/source payloads, internal dataclasses/Enums/
Decimals/dates, engine objects, secrets, paths or implementation
representations in its JSON graph.

There is exactly one public operation,
``w8_customer_result_payload_json(result, *, user_id, business_id)``.

Atomic projection design
~~~~~~~~~~~~~~~~~~~~~~~~

The operation never keeps reading a detached (but still mutable) dataclass
snapshot after that snapshot's identity has been fixed. It instead reduces the
live source to an immutable primitive-only capture (exact strings, booleans,
``None`` and tuples -- never dataclass/enum/Decimal/date objects) and derives
every decision from that capture:

1. record the live source identity before capture;
2. build the immutable primitive capture from the live source;
3. reconstruct a fully validated ``W8CustomerResult`` from the capture and
   record its identity before projection;
4. compare owners and project the response exclusively from the immutable
   capture;
5. serialise the projected graph into a detached JSON string;
6. reconstruct the capture again and record the live source identity after
   projection, then require every recorded identity to agree before returning
   the already-detached string.

A transient mutation during capture, projection, serialisation or the final
integrity comparison either invalidates the reconstructed result or changes one
of the recorded identities and therefore fails closed. A mutation after
serialisation cannot alter the already-detached output and cannot authorise a
wrong owner, because the owner decision was taken from the immutable capture.

Security-critical collaborators (complete result identity, exact owner
comparison, primitive capture, reconstruction/validation, exact reviewed-field
projection and standard-library JSON serialisation), the public outer renderer
and the fixed security/policy constants are bound in private closure state at
module construction. They are not stored in the public callable's writable
``__defaults__``, ``__kwdefaults__`` or ``__dict__``, so ordinary rebinding of
module-global helper names or mutation of ordinary writable function attributes
cannot replace them.

This is a service-to-API contract only: it adds no route, connects no web
framework integration, persists nothing, performs no authentication and
activates no provider or network path.
"""
from __future__ import annotations

import hmac as _hmac
import inspect as _inspect
import json as _json
from datetime import date as _date
from decimal import Decimal as _Decimal

from reserved.services.w2_customer_language import (
    AdjustmentFact as _AdjustmentFact,
    AdjustmentKind as _AdjustmentKind,
    ClaimToReduceState as _ClaimToReduceState,
    EvidenceClassification as _EvidenceClassification,
    FundingClassification as _FundingClassification,
    MoneyLine as _MoneyLine,
    ObligationFact as _ObligationFact,
    ObligationKind as _ObligationKind,
    PresentationStatus as _PresentationStatus,
    W2CustomerLanguageView as _W2CustomerLanguageView,
    W2PresentationInput as _W2PresentationInput,
)
from reserved.services.w8_customer_result import (
    SupportedNation as _SupportedNation,
    W8CustomerResult as _W8CustomerResult,
    w8_customer_result_identity as _identity,
)

PAYLOAD_SCHEMA_VERSION = "reserved-w8-customer-api-payload/1.0"

# Single categorical, value-free closed outcome for every invalid result or
# owner mismatch. It intentionally does not reveal whether the result, the
# user reference or the business reference failed, nor which specific check.
_PAYLOAD_REFUSED = "customer API payload refused"

_OWNER_MAX_LENGTH = 128


def _make_owner_matches(compare_digest, max_length):
    """Build the owner comparison with its primitives bound at construction."""

    def owner_matches(candidate, expected):
        # The candidate must be an exact ``str`` (subclasses rejected), non-empty,
        # trimmed, printable and bounded before constant-time comparison to the
        # already validated result reference.
        if type(candidate) is not str or not candidate or candidate != candidate.strip():
            return False
        if len(candidate) > max_length or not candidate.isprintable():
            return False
        return compare_digest(candidate, expected)

    return owner_matches


_owner_matches = _make_owner_matches(_hmac.compare_digest, _OWNER_MAX_LENGTH)


def _money_to_primitives(item):
    if item is None:
        return None
    return (item.label, item.amount, item.due_date)


def _capture_snapshot(source):
    """Reduce the live source to an immutable primitive-only capture.

    Every leaf is an exact ``str``, ``bool`` or ``None`` and every container is
    an exact ``tuple``. No dataclass, Enum, Decimal or date object is retained,
    so a later mutation of the caller's source graph (or of any detached
    dataclass reconstruction) cannot change the captured content.
    """
    view = source.view
    presentation_input = source.presentation_input

    scalars = (
        source.contract_version,
        source.nation.value,
        source.tax_year,
        source.user_id,
        source.business_id,
        tuple(source.evidence_references),
        tuple(source.limitations),
        tuple(source.prohibited_uses),
    )

    input_primitives = (
        presentation_input.contract_version,
        presentation_input.status.value,
        presentation_input.evidence.value if presentation_input.evidence is not None else None,
        str(presentation_input.annual_liability) if presentation_input.annual_liability is not None else None,
        tuple(
            (item.kind.value, str(item.amount), item.due_date.isoformat())
            for item in presentation_input.obligations
        ),
        tuple(
            (item.kind.value, str(item.amount))
            for item in presentation_input.adjustments
        ),
        presentation_input.funding.value if presentation_input.funding is not None else None,
        str(presentation_input.funding_amount) if presentation_input.funding_amount is not None else None,
        presentation_input.claim_to_reduce.value if presentation_input.claim_to_reduce is not None else None,
    )

    view_primitives = (
        view.contract_version,
        view.safe_to_present,
        view.status_tone,
        view.status_heading,
        view.status_message,
        view.evidence_label,
        _money_to_primitives(view.annual_liability),
        tuple(_money_to_primitives(item) for item in view.obligations),
        tuple(_money_to_primitives(item) for item in view.account_adjustments),
        view.funding_heading,
        view.funding_message,
        view.claim_to_reduce_heading,
        view.claim_to_reduce_message,
        view.claim_to_reduce_warning,
        view.no_payment_authority,
    )

    return (scalars, input_primitives, view_primitives)


def _reconstruct_input(input_primitives):
    """Rebuild a fresh W2 presentation input from the primitive capture."""
    (
        contract_version,
        status,
        evidence,
        annual_liability,
        obligations,
        adjustments,
        funding,
        funding_amount,
        claim_to_reduce,
    ) = input_primitives

    return _W2PresentationInput(
        contract_version,
        _PresentationStatus(status),
        _EvidenceClassification(evidence) if evidence is not None else None,
        _Decimal(annual_liability) if annual_liability is not None else None,
        tuple(
            _ObligationFact(_ObligationKind(kind), _Decimal(amount), _date.fromisoformat(due))
            for (kind, amount, due) in obligations
        ),
        tuple(
            _AdjustmentFact(_AdjustmentKind(kind), _Decimal(amount))
            for (kind, amount) in adjustments
        ),
        _FundingClassification(funding) if funding is not None else None,
        _Decimal(funding_amount) if funding_amount is not None else None,
        _ClaimToReduceState(claim_to_reduce) if claim_to_reduce is not None else None,
    )


def _reconstruct_view(view_primitives):
    """Rebuild a fresh W2 customer-language view from the primitive capture."""

    def money(item):
        if item is None:
            return None
        label, amount, due_date = item
        return _MoneyLine(label, amount, due_date)

    (
        contract_version,
        safe_to_present,
        status_tone,
        status_heading,
        status_message,
        evidence_label,
        annual_liability,
        obligations,
        account_adjustments,
        funding_heading,
        funding_message,
        claim_to_reduce_heading,
        claim_to_reduce_message,
        claim_to_reduce_warning,
        no_payment_authority,
    ) = view_primitives

    return _W2CustomerLanguageView(
        contract_version,
        safe_to_present,
        status_tone,
        status_heading,
        status_message,
        evidence_label,
        money(annual_liability),
        tuple(money(item) for item in obligations),
        tuple(money(item) for item in account_adjustments),
        funding_heading,
        funding_message,
        claim_to_reduce_heading,
        claim_to_reduce_message,
        claim_to_reduce_warning,
        no_payment_authority,
    )


def _reconstruct_result(capture):
    """Reconstruct and fully validate a result from the primitive capture.

    The ordinary ``W8CustomerResult`` constructor revalidates every field,
    re-derives the view from the reconstructed input and recomputes the private
    integrity seal, so an inconsistent or tampered capture fails closed here.
    """
    (scalars, input_primitives, view_primitives) = capture
    (
        contract_version,
        nation_value,
        tax_year,
        user_id,
        business_id,
        evidence_references,
        limitations,
        prohibited_uses,
    ) = scalars

    return _W8CustomerResult(
        contract_version,
        _SupportedNation(nation_value),
        tax_year,
        user_id,
        business_id,
        _reconstruct_input(input_primitives),
        _reconstruct_view(view_primitives),
        evidence_references,
        limitations,
        prohibited_uses,
    )


def _project_view(view_primitives):
    """Project the immutable view capture into a detached JSON-native mapping."""

    def money(item):
        if item is None:
            return None
        label, amount, due_date = item
        return {"label": label, "amount": amount, "due_date": due_date}

    (
        contract_version,
        safe_to_present,
        status_tone,
        status_heading,
        status_message,
        evidence_label,
        annual_liability,
        obligations,
        account_adjustments,
        funding_heading,
        funding_message,
        claim_to_reduce_heading,
        claim_to_reduce_message,
        claim_to_reduce_warning,
        no_payment_authority,
    ) = view_primitives

    return {
        "contract_version": contract_version,
        "safe_to_present": safe_to_present,
        "status_tone": status_tone,
        "status_heading": status_heading,
        "status_message": status_message,
        "evidence_label": evidence_label,
        "annual_liability": money(annual_liability),
        "obligations": [money(item) for item in obligations],
        "account_adjustments": [money(item) for item in account_adjustments],
        "funding_heading": funding_heading,
        "funding_message": funding_message,
        "claim_to_reduce_heading": claim_to_reduce_heading,
        "claim_to_reduce_message": claim_to_reduce_message,
        "claim_to_reduce_warning": claim_to_reduce_warning,
        "no_payment_authority": no_payment_authority,
    }


def _build_renderer(
    *,
    identity=_identity,
    owner_matches=_owner_matches,
    capture_snapshot=_capture_snapshot,
    reconstruct_result=_reconstruct_result,
    project_view=_project_view,
    serialize=_json.dumps,
    schema_version=PAYLOAD_SCHEMA_VERSION,
    refused=_PAYLOAD_REFUSED,
):
    """Build a renderer with its collaborators bound in private closure state."""

    def render(result, *, user_id, business_id):
        try:
            identity_before = identity(result)

            capture = capture_snapshot(result)

            snapshot = reconstruct_result(capture)
            snapshot_identity = identity(snapshot)

            if identity_before != snapshot_identity:
                raise ValueError(refused)

            (
                (_contract_version, nation_value, tax_year, owner_user_id, owner_business_id,
                 _evidence_references, limitations, prohibited_uses),
                _input_primitives,
                view_primitives,
            ) = capture

            if not owner_matches(user_id, owner_user_id):
                raise ValueError(refused)
            if not owner_matches(business_id, owner_business_id):
                raise ValueError(refused)

            graph = {
                "schema_version": schema_version,
                "nation": nation_value,
                "tax_year": tax_year,
                "w8_customer_result_identity": snapshot_identity,
                "view": project_view(view_primitives),
                "limitations": list(limitations),
                "prohibited_uses": list(prohibited_uses),
            }

            payload = serialize(
                graph,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )

            identity_after = identity(result)

            revalidated = reconstruct_result(capture)
            revalidated_identity = identity(revalidated)

            if not (
                identity_before == snapshot_identity
                and snapshot_identity == revalidated_identity
                and revalidated_identity == identity_after
            ):
                raise ValueError(refused)

            return payload
        except Exception:
            raise ValueError(refused) from None

    return render


_render_payload_json = _build_renderer()


def _build_public_callable(render, refused):
    """Build the single public operation with its renderer bound at import.

    The renderer and categorical refusal value are captured in private closure
    state so that later rebinding of the module-global ``_render_payload_json``
    or ``_PAYLOAD_REFUSED`` names cannot change what the public callable invokes
    or emits.
    """

    def _public(*args, **kwargs):
        try:
            if "result" in kwargs:
                if args:
                    raise ValueError(refused)
                result = kwargs.pop("result")
            else:
                if len(args) != 1:
                    raise ValueError(refused)
                (result,) = args
            if set(kwargs) != {"user_id", "business_id"}:
                raise ValueError(refused)
            user_id = kwargs["user_id"]
            business_id = kwargs["business_id"]
        except Exception:
            raise ValueError(refused) from None

        return render(result, user_id=user_id, business_id=business_id)

    _public.__signature__ = _inspect.Signature(  # type: ignore[attr-defined]
        parameters=[
            _inspect.Parameter("result", _inspect.Parameter.POSITIONAL_OR_KEYWORD),
            _inspect.Parameter("user_id", _inspect.Parameter.KEYWORD_ONLY),
            _inspect.Parameter("business_id", _inspect.Parameter.KEYWORD_ONLY),
        ]
    )
    return _public


w8_customer_result_payload_json = _build_public_callable(
    _render_payload_json, _PAYLOAD_REFUSED
)
