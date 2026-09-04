"""Minimised, provider-neutral, datastore-neutral annual/cash persistence contract.

This module defines the smallest structured persistence projection that can
durably represent the approved customer-facing annual/cash position without
recalculating tax. It is a *contract only*: it does not connect to a database,
run a migration, write a file, open a network connection, hold credentials,
select a datastore, choose encryption/key custody, or activate anything.

At admission it accepts only an exact, live producer-issued ``AnnualToCashPosition``
and the exact owner-unbound W8 handoff derived from it. It independently
validates their identities and coherence before binding the separately supplied
authenticated owner/business references inside this persistence authority
boundary. It then copies only the canonical minimal facts into an immutable
projection. The rendered customer copy is never stored: it is deterministically
reproduced from the minimal projection through the already-reviewed W2/W8
contracts.

Trust and admission are explicit. A projection built through the public
constructor, ``dataclasses.replace`` or pickle decoding is a *structural
reconstruction*: its ``annual_cash_identity`` is carried as an opaque reference
but is marked ``annual_cash_identity_admitted=False`` and therefore does not
claim that the calculation reference was issuance-validated. Ordinary copy and
deepcopy first revalidate and then return the same immutable object, preserving
but never minting its admission state. Only the admission function, which
re-proves the live producer and the derived customer result, mints a projection
with ``annual_cash_identity_admitted=True``.

The carried ``customer_result_limitations`` and ``customer_result_prohibited_uses``
describe the *reconstructed W8 customer result*, not the projection itself. In
particular ``persistence_or_storage`` is a W8 customer-result constraint and does
not prohibit persistence of this authorised minimised durable projection.

Deletion and account-erasure state are represented explicitly and honestly:
``deletion_state`` is ``not_deleted`` (this contract never claims deletion
occurred) and ``account_erasure_eligibility`` is ``unresolved`` (no retention
period or legal hold is invented here). All monetary facts are canonicalised to
one exact two-decimal representation; noncanonical exponents are rejected.

The content identity below is an *unkeyed SHA-256 digest* of the canonical
projection bytes. It is deterministic content identity for corruption/change
detection only, and is explicitly **not** authenticated writer integrity.
Authenticated storage integrity and key custody are deferred and recorded as
unresolved inputs.
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

from reserved.engines.annual_to_cash_integration import (
    AnnualToCashInputProvenance,
    AnnualToCashPosition,
    annual_to_cash_position_identity,
    annual_to_cash_position_provenance,
)
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
)
from reserved.services.w8_annual_cash_customer_handoff import (
    UnboundAnnualCashPresentation,
    validate_w8_annual_cash_customer_handoff,
)
from reserved.services.w8_customer_result import (
    SupportedNation,
    W8CustomerResult,
    compose_w8_customer_result,
    w8_customer_result_identity,
)

SCHEMA_VERSION = "reserved-annual-position-persistence/1.0"
RECORD_PURPOSE = "annual_cash_position_durable_projection"

# Fixed machine-readable constraints carried verbatim from the already-reviewed
# W8 public-result contract. They describe the *reconstructed customer result*,
# not the authorised minimised durable projection itself. They are revalidated
# on every read so no caller can weaken the supported boundary. In particular
# ``persistence_or_storage`` is a W8 customer-result constraint and must not be
# read as prohibiting persistence of this projection.
_CUSTOMER_RESULT_LIMITATIONS = (
    "presentation_facts_only",
    "not_a_current_hmrc_bill",
    "surplus_not_available_cash",
)
_CUSTOMER_RESULT_PROHIBITED_USES = (
    "no_payment_or_transfer_authority",
    "self_assessment_filing",
    "financial_advice",
    "persistence_or_storage",
    "production_or_provider_activation",
)

# Deletion and account-erasure state are explicit and honest. This contract
# never claims deletion has occurred and never invents a retention period,
# legal hold or erasure eligibility.
_DELETION_STATE = "not_deleted"
_ACCOUNT_ERASURE_ELIGIBILITY = "unresolved"

# Lifecycle/activation inputs that this contract explicitly does not decide.
_UNRESOLVED_INPUTS = (
    "legal_basis_for_retention_unresolved",
    "retention_period_unresolved",
    "legal_hold_unresolved",
    "backup_expiry_unresolved",
    "datastore_selection_unresolved",
    "encryption_at_rest_unresolved",
    "encryption_key_custody_unresolved",
    "production_access_unresolved",
    "activation_unresolved",
)


def _make_persistence_contract():
    # Capture every acceptance-critical collaborator, builtin, type, constant,
    # regex and validation/projector reference once so ordinary module/global/
    # helper/class/default/metadata rebinding cannot weaken the supported
    # boundary. The reachable acceptance graph must not rely on mutable
    # LOAD_GLOBAL names.
    raw = object.__getattribute__
    set_attr = object.__setattr__
    exact_type = type
    decimal_type = Decimal
    date_type = date
    int_type = int
    str_type = str
    bool_type = bool
    tuple_type = tuple
    sha256 = hashlib.sha256
    dumps = json.dumps
    compare = hmac.compare_digest
    dc_fields = fields
    dc_is_dataclass = is_dataclass
    enum_type = Enum
    any_fn = any
    set_type = set
    len_fn = len
    range_fn = range
    enumerate_fn = enumerate
    isinstance_fn = isinstance
    hash_fn = hash
    id_fn = id
    value_error = ValueError
    exception_type = Exception
    rebuild_fn = _rebuild_projection

    # Copy the accepted public constants into private closure state.  The
    # exported names remain useful documentation, but rebinding them after
    # import must not change construction or validation policy.
    schema_version = SCHEMA_VERSION
    record_purpose = RECORD_PURPOSE
    customer_result_limitations = tuple(_CUSTOMER_RESULT_LIMITATIONS)
    customer_result_prohibited_uses = tuple(_CUSTOMER_RESULT_PROHIBITED_USES)
    unresolved_inputs = tuple(_UNRESOLVED_INPUTS)
    deletion_state = _DELETION_STATE
    account_erasure_eligibility = _ACCOUNT_ERASURE_ELIGIBILITY

    zero = Decimal("0.00")
    penny = Decimal("0.01")

    reference_re = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
    source_id_re = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
    digest_reference_re = re.compile(r"^[a-z-]+:sha256-[0-9a-f]{64}$")
    tax_year_re = re.compile(r"^[0-9]{4}/[0-9]{2}$")
    annual_cash_identity_re = re.compile(r"^annual-to-cash-position:sha256-[0-9a-f]{64}$")
    customer_result_identity_re = re.compile(r"^w8-customer-result:sha256-[0-9a-f]{64}$")
    content_identity_re = re.compile(r"^annual-position-persistence:sha256-[0-9a-f]{64}$")

    secret_markers = (
        "secret", "token", "password", "credential", "apikey", "api_key",
        "bearer", "private_key", "sk_live", "sk_test", "access_key",
    )

    supported_nation_type = SupportedNation
    evidence_classification_type = EvidenceClassification
    funding_classification_type = FundingClassification
    obligation_fact_type = ObligationFact
    adjustment_fact_type = AdjustmentFact
    obligation_kind_type = ObligationKind
    adjustment_kind_type = AdjustmentKind
    w2_input_type = W2PresentationInput
    w2_version = W2_CONTRACT_VERSION
    presentation_ready = PresentationStatus.READY
    local_estimate = EvidenceClassification.QUALIFIED_LOCAL_ESTIMATE
    funding_exact = FundingClassification.EXACT
    funding_gap = FundingClassification.GAP
    funding_surplus = FundingClassification.SURPLUS

    projection_field_names = (
        "schema_version",
        "record_purpose",
        "record_version",
        "user_id",
        "business_id",
        "nation",
        "tax_year",
        "annual_cash_identity",
        "customer_result_identity",
        "evidence_classification",
        "annual_liability",
        "obligations",
        "adjustments",
        "funding",
        "funding_amount",
        "evidence_references",
        "ruleset_version",
        "as_of",
        "stale_after_days",
        "customer_result_limitations",
        "customer_result_prohibited_uses",
        "unresolved_inputs",
        "deletion_state",
        "account_erasure_eligibility",
        "predecessor_identity",
        "annual_cash_identity_admitted",
        "_integrity_seal",
    )
    projection_slot_descriptors = ()

    def _slot(value, name: str):
        """Read retained state through the original captured slot descriptor."""
        descriptor = projection_slot_descriptors[projection_field_names.index(name)]
        return descriptor.__get__(value, AnnualPositionPersistenceProjection)

    annual_position_type = AnnualToCashPosition
    provenance_type = AnnualToCashInputProvenance
    handoff_type = UnboundAnnualCashPresentation
    annual_cash_identity_reader = annual_to_cash_position_identity
    provenance_reader = annual_to_cash_position_provenance
    handoff_validator = validate_w8_annual_cash_customer_handoff
    w8_composer = compose_w8_customer_result
    w8_identity_reader = w8_customer_result_identity

    def _money(value: object) -> bool:
        return (
            exact_type(value) is decimal_type
            and value.is_finite()
            and value >= zero
            and value.as_tuple().exponent == -2
            and not (value.is_zero() and value.is_signed())
        )

    def _canonical_money(value: Decimal) -> Decimal:
        return value.quantize(penny)

    def _validate_owner(value: object, subject: str) -> None:
        if exact_type(value) is not str_type or not reference_re.fullmatch(value):
            raise value_error(f"invalid {subject} ownership reference")
        lowered = value.lower()
        if any_fn(marker in lowered for marker in secret_markers):
            raise value_error(f"invalid {subject} ownership reference")

    def _validate_tax_year(value: object) -> None:
        if exact_type(value) is not str_type or not tax_year_re.fullmatch(value):
            raise value_error("invalid projection tax year")
        if int_type(value[-2:]) != (int_type(value[:4]) + 1) % 100:
            raise value_error("invalid projection tax year")

    def _validate_evidence_references(value: object) -> None:
        if exact_type(value) is not tuple_type:
            raise value_error("projection evidence references must be a tuple")
        if not value:
            raise value_error("projection evidence references are required")
        seen = set_type()
        for item in value:
            if exact_type(item) is not str_type or not source_id_re.fullmatch(item):
                raise value_error("invalid projection evidence reference")
            if digest_reference_re.fullmatch(item):
                raise value_error("projection evidence reference provenance mismatch")
            lowered = item.lower()
            if any_fn(marker in lowered for marker in secret_markers):
                raise value_error("invalid projection evidence reference")
            if item in seen:
                raise value_error("duplicate projection evidence reference")
            seen.add(item)

    def _validate_fixed(value: object, expected: tuple, name: str) -> None:
        if exact_type(value) is not tuple_type or any_fn(
            exact_type(item) is not str_type for item in value
        ):
            raise value_error(f"projection {name} were altered")
        if value != expected:
            raise value_error(f"projection {name} were altered")

    def _reconstruct_w2_input(projection) -> W2PresentationInput:
        return w2_input_type(
            w2_version,
            presentation_ready,
            _slot(projection, "evidence_classification"),
            _slot(projection, "annual_liability"),
            _slot(projection, "obligations"),
            _slot(projection, "adjustments"),
            _slot(projection, "funding"),
            _slot(projection, "funding_amount"),
            None,
        )

    def _reconstruct_customer_result(projection) -> W8CustomerResult:
        result = w8_composer(
            _reconstruct_w2_input(projection),
            nation=_slot(projection, "nation").value,
            tax_year=_slot(projection, "tax_year"),
            user_id=_slot(projection, "user_id"),
            business_id=_slot(projection, "business_id"),
            evidence_references=_slot(projection, "evidence_references"),
        )
        if result is None:
            raise value_error(
                "projection facts do not reconstruct a presentable customer result"
            )
        return result

    def _validate_coherence(projection) -> None:
        reconstructed = _reconstruct_customer_result(projection)
        if w8_identity_reader(reconstructed) != _slot(projection, "customer_result_identity"):
            raise value_error("projection customer-result identity is not reproducible")

    @dataclass(frozen=True, slots=True, eq=False)
    class AnnualPositionPersistenceProjection:
        """Immutable, minimal, owner-bound annual/cash persistence projection.

        ``annual_cash_identity`` is an admission-bound opaque reference read from
        the live producer and cannot be recomputed from the stored facts; its
        truth was established only at admission. ``customer_result_identity`` is
        reproducible from the stored facts and is re-proven on every read. The
        rendered customer copy is intentionally absent.

        ``annual_cash_identity_admitted`` is explicit trust state. It is ``False``
        for any structural reconstruction (public construction, ``replace``,
        copy or pickle decode) and ``True`` only for a projection minted by the
        admission function.
        """

        schema_version: str
        record_purpose: str
        record_version: int
        user_id: str
        business_id: str
        nation: SupportedNation
        tax_year: str
        annual_cash_identity: str
        customer_result_identity: str
        evidence_classification: EvidenceClassification
        annual_liability: Decimal
        obligations: tuple[ObligationFact, ...]
        adjustments: tuple[AdjustmentFact, ...]
        funding: FundingClassification
        funding_amount: Decimal | None
        evidence_references: tuple[str, ...]
        ruleset_version: str
        as_of: date
        stale_after_days: int
        customer_result_limitations: tuple[str, ...]
        customer_result_prohibited_uses: tuple[str, ...]
        unresolved_inputs: tuple[str, ...]
        deletion_state: str
        account_erasure_eligibility: str
        predecessor_identity: str | None
        annual_cash_identity_admitted: bool = field(
            init=False, default=False, repr=False, compare=False
        )
        _integrity_seal: str = field(init=False, repr=False, compare=False)

        def __post_init__(self) -> None:
            _validate_projection_state(self)
            set_attr(self, "_integrity_seal", _expected_seal(self))
            _validate_projection(self)

        def __repr__(self) -> str:
            try:
                _validate_projection(self)
            except exception_type:
                return "AnnualPositionPersistenceProjection(<invalid-state>)"
            return "AnnualPositionPersistenceProjection(<validated>)"

        def __eq__(self, other: object) -> bool:
            _validate_projection(self)
            if exact_type(other) is not AnnualPositionPersistenceProjection:
                return False
            _validate_projection(other)
            return _projection_components(self) == _projection_components(other)

        def __hash__(self) -> int:
            _validate_projection(self)
            return hash_fn(_projection_components(self))

        def __copy__(self):
            _validate_projection(self)
            return self

        def __deepcopy__(self, memo: dict):
            _validate_projection(self)
            memo[id_fn(self)] = self
            return self

        def __reduce__(self):
            _validate_projection(self)
            return (rebuild_fn, _projection_components(self))

    # Dataclass slot descriptors are the only authority for retained state.
    # Capture them once before callers can rebind class attributes.
    projection_slot_descriptors = tuple_type(
        AnnualPositionPersistenceProjection.__dict__[name]
        for name in projection_field_names
    )

    def _projection_components(value) -> tuple:
        return tuple_type(_slot(value, name) for name in projection_field_names[:25])

    def _content_components(value) -> tuple:
        # Stable node identity: all durable facts and the supported version, but
        # not the chain link (predecessor). Excluding the predecessor keeps a
        # record's content identity independent of where it sits in a chain so
        # self-reference and cycles remain detectable by the chain validator.
        # The admission flag is also excluded: it is ephemeral trust state, not a
        # durable fact, so a persistence round-trip preserves content identity.
        return tuple_type(_slot(value, name) for name in projection_field_names[:24])

    def _seal_components(value) -> tuple:
        return _projection_components(value) + (
            _slot(value, "annual_cash_identity_admitted"),
        )

    def _canonical(value: object) -> object:
        if dc_is_dataclass(value) and not isinstance_fn(value, exact_type):
            return {
                "__dataclass__": exact_type(value).__name__,
                "__fields__": {
                    f.name: _canonical(raw(value, f.name))
                    for f in dc_fields(exact_type(value))
                },
            }
        if isinstance_fn(value, enum_type):
            return {"__enum__": f"{exact_type(value).__name__}:{value.value}"}
        if exact_type(value) is tuple_type:
            return [_canonical(item) for item in value]
        if exact_type(value) is decimal_type:
            return {"__decimal__": str_type(value)}
        if exact_type(value) is date_type:
            return {"__date__": value.isoformat()}
        if value is None or exact_type(value) in (str_type, bool_type, int_type):
            return value
        raise value_error("unsupported projection identity value type")

    def _content_digest(value) -> str:
        payload = dumps(
            _canonical(_content_components(value)),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return sha256(payload).hexdigest()

    def _seal_digest(value) -> str:
        payload = dumps(
            _canonical(_seal_components(value)),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        return sha256(payload).hexdigest()

    def _expected_seal(value) -> str:
        return f"annual-position-persistence-seal:sha256-{_seal_digest(value)}"

    def _validate_projection_state(value) -> AnnualPositionPersistenceProjection:
        if exact_type(value) is not AnnualPositionPersistenceProjection:
            raise value_error("projection must be an exact persistence projection")
        if exact_type(_slot(value, "schema_version")) is not str_type or _slot(value, "schema_version") != schema_version:
            raise value_error("unsupported projection schema version")
        if exact_type(_slot(value, "record_purpose")) is not str_type or _slot(value, "record_purpose") != record_purpose:
            raise value_error("unsupported projection purpose")
        if exact_type(_slot(value, "record_version")) is not int_type or _slot(value, "record_version") < 1:
            raise value_error("invalid projection record version")
        if exact_type(_slot(value, "annual_cash_identity_admitted")) is not bool_type:
            raise value_error("invalid projection admission state")
        _validate_owner(_slot(value, "user_id"), "user")
        _validate_owner(_slot(value, "business_id"), "business")
        if _slot(value, "user_id") == _slot(value, "business_id"):
            raise value_error("user and business ownership must be distinct")
        if exact_type(_slot(value, "nation")) is not supported_nation_type:
            raise value_error("unsupported projection geography")
        _validate_tax_year(_slot(value, "tax_year"))
        if exact_type(_slot(value, "annual_cash_identity")) is not str_type or not annual_cash_identity_re.fullmatch(
            _slot(value, "annual_cash_identity")
        ):
            raise value_error("invalid annual/cash identity")
        if exact_type(_slot(value, "customer_result_identity")) is not str_type or not customer_result_identity_re.fullmatch(
            _slot(value, "customer_result_identity")
        ):
            raise value_error("invalid customer-result identity")
        if _slot(value, "evidence_classification") is not local_estimate:
            raise value_error("projection evidence classification must be a local estimate")
        if not _money(_slot(value, "annual_liability")):
            raise value_error("invalid projection annual liability")

        obligations_value = _slot(value, "obligations")
        if exact_type(obligations_value) is not tuple_type or not obligations_value:
            raise value_error("invalid projection obligations")
        seen_kinds = set_type()
        for item in obligations_value:
            if exact_type(item) is not obligation_fact_type:
                raise value_error("invalid projection obligation")
            if (
                exact_type(item.kind) is not obligation_kind_type
                or not _money(item.amount)
                or exact_type(item.due_date) is not date_type
            ):
                raise value_error("invalid projection obligation")
            if item.kind in seen_kinds:
                raise value_error("duplicate projection obligation kind")
            seen_kinds.add(item.kind)

        adjustments_value = _slot(value, "adjustments")
        if exact_type(adjustments_value) is not tuple_type or not adjustments_value:
            raise value_error("invalid projection adjustments")
        seen_adj = set_type()
        for item in adjustments_value:
            if exact_type(item) is not adjustment_fact_type:
                raise value_error("invalid projection adjustment")
            if exact_type(item.kind) is not adjustment_kind_type or not _money(item.amount):
                raise value_error("invalid projection adjustment")
            if item.kind in seen_adj:
                raise value_error("duplicate projection adjustment kind")
            seen_adj.add(item.kind)

        funding_value = _slot(value, "funding")
        funding_amount_value = _slot(value, "funding_amount")
        if exact_type(funding_value) is not funding_classification_type:
            raise value_error("invalid projection funding classification")
        if funding_value is funding_exact:
            if funding_amount_value is not None:
                raise value_error("exact projection funding must have no amount")
        elif funding_value in (funding_gap, funding_surplus):
            if not _money(funding_amount_value) or funding_amount_value == zero:
                raise value_error("invalid projection funding amount")
        else:
            raise value_error("unsupported projection funding classification")

        _validate_evidence_references(_slot(value, "evidence_references"))

        if exact_type(_slot(value, "ruleset_version")) is not str_type or not reference_re.fullmatch(
            _slot(value, "ruleset_version")
        ):
            raise value_error("invalid projection ruleset version")
        if exact_type(_slot(value, "as_of")) is not date_type:
            raise value_error("invalid projection as-of date")
        if exact_type(_slot(value, "stale_after_days")) is not int_type or _slot(value, "stale_after_days") < 0:
            raise value_error("invalid projection freshness")

        _validate_fixed(
            _slot(value, "customer_result_limitations"),
            customer_result_limitations,
            "customer-result limitations",
        )
        _validate_fixed(
            _slot(value, "customer_result_prohibited_uses"),
            customer_result_prohibited_uses,
            "customer-result prohibited uses",
        )
        _validate_fixed(_slot(value, "unresolved_inputs"), unresolved_inputs, "unresolved inputs")

        if exact_type(_slot(value, "deletion_state")) is not str_type or _slot(value, "deletion_state") != deletion_state:
            raise value_error("invalid projection deletion state")
        if exact_type(_slot(value, "account_erasure_eligibility")) is not str_type or _slot(value, "account_erasure_eligibility") != account_erasure_eligibility:
            raise value_error("invalid projection account-erasure eligibility")

        predecessor = _slot(value, "predecessor_identity")
        if predecessor is not None:
            if (
                exact_type(predecessor) is not str_type
                or not content_identity_re.fullmatch(predecessor)
            ):
                raise value_error("invalid projection predecessor identity")

        _validate_coherence(value)
        return value

    def _validate_projection(value) -> AnnualPositionPersistenceProjection:
        result = _validate_projection_state(value)
        seal = _slot(result, "_integrity_seal")
        if exact_type(seal) is not str_type or not compare(seal, _expected_seal(result)):
            raise value_error("projection integrity mismatch")
        return result

    def _build_admitted_projection(
        annual_position,
        handoff,
        *,
        authenticated_user_id,
        authenticated_business_id,
        record_version: int,
        predecessor_identity,
    ) -> AnnualPositionPersistenceProjection:
        # Reject duck types and subclasses before any attribute, property or
        # descriptor access. The deeper handoff/source validator still proves
        # the complete exact source graph after this inert outer type gate.
        if exact_type(annual_position) is not annual_position_type:
            raise value_error(
                "persistence admission requires an exact annual/cash position"
            )

        # The W8 boundary is deliberately owner-unbound. Revalidate its exact
        # producer/source/evidence/as-of binding before consulting or binding
        # any owner reference. A structurally reconstructed or altered handoff
        # therefore cannot use this persistence boundary to mint authority.
        if exact_type(handoff) is not handoff_type:
            raise value_error("persistence admission requires an exact owner-unbound handoff")
        supplied_references = raw(handoff, "evidence_references")
        expected_as_of = raw(annual_position, "as_of")
        validated_handoff = handoff_validator(
            handoff,
            source_position=annual_position,
            evidence_references=supplied_references,
            expected_as_of=expected_as_of,
        )

        # These references are asserted by the already-authenticated caller;
        # the unbound W8 object is never allowed to carry or select them.
        _validate_owner(authenticated_user_id, "authenticated user")
        _validate_owner(authenticated_business_id, "authenticated business")
        if authenticated_user_id == authenticated_business_id:
            raise value_error("user and business ownership must be distinct")

        annual_identity = annual_cash_identity_reader(annual_position)
        if exact_type(annual_identity) is not str_type:
            raise value_error("annual/cash producer identity is unsupported")
        provenance = provenance_reader(annual_position)
        if exact_type(provenance) is not provenance_type:
            raise value_error("annual/cash producer provenance is unsupported")

        # Bind ownership only after exact handoff admission. The W8 public
        # result is an internal derived value, not an accepted caller input.
        customer_result = w8_composer(
            raw(validated_handoff, "presentation_input"),
            nation=raw(validated_handoff, "nation"),
            tax_year=raw(validated_handoff, "tax_year"),
            user_id=authenticated_user_id,
            business_id=authenticated_business_id,
            evidence_references=raw(validated_handoff, "evidence_references"),
        )
        if customer_result is None:
            raise value_error("authenticated owner binding did not produce a customer result")

        presentation = raw(customer_result, "presentation_input")
        evidence = raw(presentation, "evidence")
        annual_liability = _canonical_money(raw(presentation, "annual_liability"))
        obligations = tuple_type(
            obligation_fact_type(item.kind, _canonical_money(item.amount), item.due_date)
            for item in raw(presentation, "obligations")
        )
        adjustments = tuple_type(
            adjustment_fact_type(item.kind, _canonical_money(item.amount))
            for item in raw(presentation, "adjustments")
        )
        funding = raw(presentation, "funding")
        funding_amount = raw(presentation, "funding_amount")
        if funding_amount is not None:
            funding_amount = _canonical_money(funding_amount)

        # Recompute the customer-result identity from the canonical facts so the
        # stored identity remains reproducible by structural reconstruction even
        # when the live producer supplied a noncanonical decimal exponent.
        canonical_w2 = w2_input_type(
            w2_version,
            presentation_ready,
            evidence,
            annual_liability,
            obligations,
            adjustments,
            funding,
            funding_amount,
            None,
        )
        canonical_result = w8_composer(
            canonical_w2,
            nation=customer_result.nation.value,
            tax_year=customer_result.tax_year,
            user_id=customer_result.user_id,
            business_id=customer_result.business_id,
            evidence_references=customer_result.evidence_references,
        )
        if canonical_result is None:
            raise value_error("projection facts do not reconstruct a presentable customer result")
        customer_identity = w8_identity_reader(canonical_result)

        projection = AnnualPositionPersistenceProjection(
            schema_version,
            record_purpose,
            record_version,
            customer_result.user_id,
            customer_result.business_id,
            customer_result.nation,
            customer_result.tax_year,
            annual_identity,
            customer_identity,
            evidence,
            annual_liability,
            obligations,
            adjustments,
            funding,
            funding_amount,
            customer_result.evidence_references,
            raw(annual_position, "ruleset_version"),
            raw(annual_position, "as_of"),
            raw(provenance, "stale_after_days"),
            customer_result.limitations,
            customer_result.prohibited_uses,
            unresolved_inputs,
            deletion_state,
            account_erasure_eligibility,
            predecessor_identity,
        )
        set_attr(projection, "annual_cash_identity_admitted", True)
        set_attr(projection, "_integrity_seal", _expected_seal(projection))
        _validate_projection(projection)
        return projection

    def admit_annual_position_projection(
        annual_position,
        handoff,
        *,
        authenticated_user_id,
        authenticated_business_id,
    ) -> AnnualPositionPersistenceProjection:
        """Admit an exact unbound handoff, then bind authenticated ownership."""
        return _build_admitted_projection(
            annual_position,
            handoff,
            authenticated_user_id=authenticated_user_id,
            authenticated_business_id=authenticated_business_id,
            record_version=1,
            predecessor_identity=None,
        )

    def annual_position_projection_identity(projection) -> str:
        """Return the deterministic content identity of a projection.

        This is an unkeyed SHA-256 digest over the canonical projection bytes.
        It is deterministic content identity for corruption/change detection and
        is not authenticated writer integrity.
        """
        _validate_projection(projection)
        return f"annual-position-persistence:sha256-{_content_digest(projection)}"

    def _require_same_boundary(previous, successor) -> None:
        if _slot(successor, "record_purpose") != _slot(previous, "record_purpose"):
            raise value_error("supersession purpose changed")
        if _slot(successor, "user_id") != _slot(previous, "user_id"):
            raise value_error("supersession cross-user substitution")
        if _slot(successor, "business_id") != _slot(previous, "business_id"):
            raise value_error("supersession cross-business substitution")
        if _slot(successor, "tax_year") != _slot(previous, "tax_year"):
            raise value_error("supersession tax year changed")
        if _slot(successor, "nation") is not _slot(previous, "nation"):
            raise value_error("supersession geography changed")

    def supersede_annual_position_projection(
        previous,
        annual_position,
        handoff,
        *,
        authenticated_user_id,
        authenticated_business_id,
    ) -> AnnualPositionPersistenceProjection:
        """Admit a successor linked to the exact previous content identity.

        The public supersede operation rejects any owner/business/tax-year/
        nation/purpose boundary mismatch *before* returning a successor.
        """
        _validate_projection(previous)
        previous_identity = annual_position_projection_identity(previous)
        successor = _build_admitted_projection(
            annual_position,
            handoff,
            authenticated_user_id=authenticated_user_id,
            authenticated_business_id=authenticated_business_id,
            record_version=_slot(previous, "record_version") + 1,
            predecessor_identity=previous_identity,
        )
        _require_same_boundary(previous, successor)
        return successor

    def validate_supersession_chain(
        records,
        *,
        external_anchor=None,
    ) -> AnnualPositionPersistenceProjection:
        """Validate a finite supplied supersession chain; return the terminal record.

        This is datastore-neutral: it never queries or selects a datastore.
        """
        chain = tuple_type(records)
        if not chain:
            raise value_error("supersession chain is empty")
        identities = tuple_type(annual_position_projection_identity(r) for r in chain)
        if len_fn(set_type(identities)) != len_fn(identities):
            raise value_error("supersession chain repeats a record identity")

        first = chain[0]
        if external_anchor is None:
            if _slot(first, "predecessor_identity") is not None:
                raise value_error("first record must have no predecessor")
        else:
            if exact_type(external_anchor) is not str_type or not content_identity_re.fullmatch(
                external_anchor
            ):
                raise value_error("invalid external anchor")
            if _slot(first, "predecessor_identity") != external_anchor:
                raise value_error("first record does not reference the external anchor")

        base_user = _slot(first, "user_id")
        base_business = _slot(first, "business_id")
        base_tax_year = _slot(first, "tax_year")
        base_nation = _slot(first, "nation")
        base_purpose = _slot(first, "record_purpose")
        for i, record in enumerate_fn(chain):
            if _slot(record, "record_purpose") != base_purpose:
                raise value_error("supersession purpose changed")
            if _slot(record, "user_id") != base_user:
                raise value_error("supersession cross-user substitution")
            if _slot(record, "business_id") != base_business:
                raise value_error("supersession cross-business substitution")
            if _slot(record, "tax_year") != base_tax_year:
                raise value_error("supersession tax year changed")
            if _slot(record, "nation") is not base_nation:
                raise value_error("supersession geography changed")
            if _slot(record, "predecessor_identity") == identities[i]:
                raise value_error("supersession self-reference")

        for i in range_fn(1, len_fn(chain)):
            previous = chain[i - 1]
            current = chain[i]
            if _slot(current, "predecessor_identity") != identities[i - 1]:
                raise value_error(
                    "supersession successor does not reference the immediately preceding record"
                )
            if _slot(current, "record_version") != _slot(previous, "record_version") + 1:
                raise value_error("supersession version did not strictly progress")

        return chain[-1]

    def reconstruct_w8_customer_result(projection) -> W8CustomerResult:
        """Deterministically reproduce the customer result from minimal facts."""
        _validate_projection(projection)
        return _reconstruct_customer_result(projection)

    AnnualPositionPersistenceProjection.__module__ = __name__
    AnnualPositionPersistenceProjection.__qualname__ = "AnnualPositionPersistenceProjection"

    return (
        AnnualPositionPersistenceProjection,
        admit_annual_position_projection,
        annual_position_projection_identity,
        supersede_annual_position_projection,
        validate_supersession_chain,
        reconstruct_w8_customer_result,
    )


def _rebuild_projection(*values):
    """Rebuild a projection through the public constructor (pickle path)."""
    return AnnualPositionPersistenceProjection(*values)


(
    AnnualPositionPersistenceProjection,
    admit_annual_position_projection,
    annual_position_projection_identity,
    supersede_annual_position_projection,
    validate_supersession_chain,
    reconstruct_w8_customer_result,
) = _make_persistence_contract()
del _make_persistence_contract


__all__ = [
    "SCHEMA_VERSION",
    "RECORD_PURPOSE",
    "AnnualPositionPersistenceProjection",
    "admit_annual_position_projection",
    "annual_position_projection_identity",
    "supersede_annual_position_projection",
    "validate_supersession_chain",
    "reconstruct_w8_customer_result",
]
