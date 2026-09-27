"""Pure, fail-closed W8-S2C annual/cash presentation handoff.

The output is deliberately *not* an owner-authoritative public result. A
separate authenticated owner/business boundary must bind it first.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import date
from decimal import Decimal
from enum import Enum
import hashlib
import hmac
import json
import re

from reserved.engines import cash_funding_position as funding
from reserved.engines import cash_obligation_reconciliation as obligations
from reserved.engines import payments_on_account as poa
from reserved.engines.annual_to_cash_integration import (
    CONTRACT_VERSION as ANNUAL_TO_CASH_VERSION,
    AnnualToCashPosition,
    AnnualToCashStatus,
    cash_ready_annual_position_identity,
)
from reserved.services.w2_customer_language import (
    CONTRACT_VERSION as W2_VERSION,
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


CONTRACT_VERSION = "reserved-w8-annual-cash-presentation-handoff/1.0"
_ZERO = Decimal("0.00")
_PENNY = Decimal("0.01")
_SOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")
_DIGEST_ID = re.compile(r"^[a-z0-9-]+:sha256-[0-9a-f]{64}$")
_SUPPORTED_NATIONS = ("England", "Wales", "Northern Ireland")
_MAX_GRAPH_DEPTH = 64
_MAX_GRAPH_NODES = 4096
_LIMITATIONS = (
    "qualified_local_estimate_not_hmrc_recorded_amount",
    "requires_separate_authenticated_owner_business_binding",
)
_PROHIBITED_USES = (
    "owner_authoritative_public_result",
    "present_as_current_hmrc_bill",
    "persistence_or_customer_rendering",
    "payment_or_transfer_action",
)
_OBLIGATION_KIND = {
    obligations.account.ChargeKind.BALANCING_PAYMENT: ObligationKind.BALANCING_PAYMENT,
    obligations.account.ChargeKind.PAYMENT_ON_ACCOUNT_1:
        ObligationKind.FIRST_PAYMENT_ON_ACCOUNT,
    obligations.account.ChargeKind.PAYMENT_ON_ACCOUNT_2:
        ObligationKind.SECOND_PAYMENT_ON_ACCOUNT,
}
_FUNDING_KIND = {
    funding.FundingBalance.GAP: FundingClassification.GAP,
    funding.FundingBalance.EXACT: FundingClassification.EXACT,
    funding.FundingBalance.SURPLUS: FundingClassification.SURPLUS,
}


class _IssueToken:
    """Private construction convention; not a secret or authenticity proof."""


_ISSUE_TOKEN = _IssueToken()


@dataclass(frozen=True, slots=True, eq=False, init=False)
class UnboundAnnualCashPresentation:
    """Content-bound presentation facts awaiting authenticated ownership."""

    presentation_input: W2PresentationInput
    evidence_references: tuple[str, ...]
    as_of: date
    tax_year: str
    nation: str
    ruleset_version: str
    annual_to_cash_contract_version: str
    source_position_identity: str
    annual_position_reference: str
    contract_version: str = field(init=False, default=CONTRACT_VERSION)
    owner_authoritative: bool = field(init=False, default=False)
    limitations: tuple[str, ...] = field(init=False, default=_LIMITATIONS)
    prohibited_uses: tuple[str, ...] = field(init=False, default=_PROHIBITED_USES)
    _integrity_seal: str = field(init=False, repr=False, compare=False)

    def __init__(
        self,
        presentation_input: W2PresentationInput,
        evidence_references: tuple[str, ...],
        as_of: date,
        tax_year: str,
        nation: str,
        ruleset_version: str,
        annual_to_cash_contract_version: str,
        source_position_identity: str,
        annual_position_reference: str,
        *,
        _issue_token: object = None,
    ) -> None:
        if _issue_token is not _ISSUE_TOKEN:
            raise ValueError("unbound annual/cash handoffs may be issued only by the composer")
        for name, value in (
            ("presentation_input", presentation_input),
            ("evidence_references", evidence_references),
            ("as_of", as_of),
            ("tax_year", tax_year),
            ("nation", nation),
            ("ruleset_version", ruleset_version),
            ("annual_to_cash_contract_version", annual_to_cash_contract_version),
            ("source_position_identity", source_position_identity),
            ("annual_position_reference", annual_position_reference),
        ):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "contract_version", CONTRACT_VERSION)
        object.__setattr__(self, "owner_authoritative", False)
        object.__setattr__(self, "limitations", _LIMITATIONS)
        object.__setattr__(self, "prohibited_uses", _PROHIBITED_USES)
        _validate_handoff_state(self, require_seal=False)
        object.__setattr__(self, "_integrity_seal", _expected_handoff_seal(self))
        _validate_handoff_state(self, require_seal=True)

    def __repr__(self) -> str:
        try:
            _validate_handoff_state(self, require_seal=True)
        except (AttributeError, TypeError, ValueError):
            return "UnboundAnnualCashPresentation(<invalid-state>)"
        return "UnboundAnnualCashPresentation(<validated-owner-unbound>)"

    def __eq__(self, other: object) -> bool:
        _validate_handoff_state(self, require_seal=True)
        if type(other) is not UnboundAnnualCashPresentation:
            return False
        _validate_handoff_state(other, require_seal=True)
        return _handoff_components(self) == _handoff_components(other)

    def __hash__(self) -> int:
        _validate_handoff_state(self, require_seal=True)
        return hash(_handoff_components(self))

    def __copy__(self):
        raise TypeError("unbound annual/cash handoffs cannot be copied")

    def __deepcopy__(self, memo):
        raise TypeError("unbound annual/cash handoffs cannot be copied")

    def __reduce__(self):
        raise TypeError("unbound annual/cash handoffs cannot be pickled")


def _canonical(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "type": f"{type(value).__module__}.{type(value).__qualname__}",
            "fields": {
                item.name: _canonical(object.__getattribute__(value, item.name))
                for item in fields(type(value))
                if item.name != "_integrity_seal"
            },
        }
    if type(value) is Decimal:
        return {"decimal": str(value)}
    if type(value) is date:
        return {"date": value.isoformat()}
    if isinstance(value, Enum):
        return {
            "enum": f"{type(value).__module__}.{type(value).__qualname__}:{value.value}"
        }
    if type(value) is tuple:
        return [_canonical(item) for item in value]
    if value is None or type(value) in (str, int, bool):
        return value
    raise ValueError(f"unsupported identity type: {type(value).__name__}")


def _digest(value: object) -> str:
    encoded = json.dumps(
        _canonical(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _handoff_components(value: UnboundAnnualCashPresentation) -> tuple[object, ...]:
    return (
        value.contract_version,
        value.presentation_input,
        value.evidence_references,
        value.as_of,
        value.tax_year,
        value.nation,
        value.ruleset_version,
        value.annual_to_cash_contract_version,
        value.source_position_identity,
        value.annual_position_reference,
        value.owner_authoritative,
        value.limitations,
        value.prohibited_uses,
    )


def _expected_handoff_seal(value: UnboundAnnualCashPresentation) -> str:
    return _digest(_handoff_components(value))


def _validate_exact_presentation_graph(
    value: object,
    *,
    active: set[int] | None = None,
    visited: set[int] | None = None,
    depth: int = 0,
) -> None:
    if depth > _MAX_GRAPH_DEPTH:
        raise ValueError("handoff presentation graph exceeds the depth limit")
    active = set() if active is None else active
    visited = set() if visited is None else visited
    allowed_dataclasses = {W2PresentationInput, ObligationFact, AdjustmentFact}
    traversable = (
        is_dataclass(value) and not isinstance(value, type)
    ) or type(value) is tuple
    if traversable:
        identity = id(value)
        if identity in active:
            raise ValueError("handoff presentation graph contains a cycle")
        if identity in visited:
            return
        if len(visited) >= _MAX_GRAPH_NODES:
            raise ValueError("handoff presentation graph exceeds the node limit")
        active.add(identity)
        visited.add(identity)
        try:
            if type(value) is tuple:
                for item in value:
                    _validate_exact_presentation_graph(
                        item, active=active, visited=visited, depth=depth + 1
                    )
                return
            if type(value) not in allowed_dataclasses:
                raise ValueError("handoff presentation contains an unsupported contract")
            expected = {item.name for item in fields(type(value))}
            if not hasattr(value, "__dict__") or set(vars(value)) != expected:
                raise ValueError("handoff presentation contains undeclared state")
            for item in fields(type(value)):
                _validate_exact_presentation_graph(
                    object.__getattribute__(value, item.name),
                    active=active,
                    visited=visited,
                    depth=depth + 1,
                )
            return
        finally:
            active.remove(identity)
    if isinstance(value, Enum):
        if type(value).__module__ != "reserved.services.w2_customer_language":
            raise ValueError("handoff presentation contains an unsupported enum")
        return
    if type(value) in (str, bool, date, Decimal) or value is None:
        return
    raise ValueError("handoff presentation contains unsupported state")


def _validate_handoff_state(
    value: object, *, require_seal: bool
) -> UnboundAnnualCashPresentation:
    if type(value) is not UnboundAnnualCashPresentation:
        raise ValueError("handoff must be an exact UnboundAnnualCashPresentation")
    _validate_exact_presentation_graph(value.presentation_input)
    if (
        value.contract_version != CONTRACT_VERSION
        or value.owner_authoritative is not False
        or value.limitations != _LIMITATIONS
        or value.prohibited_uses != _PROHIBITED_USES
        or type(value.presentation_input) is not W2PresentationInput
        or present_w2_customer_language(value.presentation_input).safe_to_present is not True
        or type(value.evidence_references) is not tuple
        or not value.evidence_references
        or any(
            type(item) is not str or not _SOURCE_ID.fullmatch(item)
            for item in value.evidence_references
        )
        or len(value.evidence_references) != len(set(value.evidence_references))
        or type(value.as_of) is not date
        or type(value.tax_year) is not str
        or not value.tax_year
        or type(value.nation) is not str
        or value.nation not in _SUPPORTED_NATIONS
        or type(value.ruleset_version) is not str
        or not value.ruleset_version
        or value.annual_to_cash_contract_version != ANNUAL_TO_CASH_VERSION
        or type(value.source_position_identity) is not str
        or not _DIGEST_ID.fullmatch(value.source_position_identity)
        or not value.source_position_identity.startswith("annual-to-cash-position:")
        or type(value.annual_position_reference) is not str
        or not _DIGEST_ID.fullmatch(value.annual_position_reference)
    ):
        raise ValueError("unbound annual/cash handoff state is invalid")
    if require_seal:
        seal = object.__getattribute__(value, "_integrity_seal")
        if type(seal) is not str or not hmac.compare_digest(
            seal, _expected_handoff_seal(value)
        ):
            raise ValueError("unbound annual/cash handoff integrity mismatch")
    return value


def _money(value: object) -> bool:
    return (
        type(value) is Decimal and value.is_finite() and value >= _ZERO
        and value == value.quantize(_PENNY)
        and not (value.is_zero() and value.is_signed())
    )


def _exact_graph(
    value: object,
    *,
    active: set[int] | None = None,
    visited: set[int] | None = None,
    depth: int = 0,
) -> None:
    """Reject subtypes, undeclared state, cycles and unbounded graphs."""
    if depth > _MAX_GRAPH_DEPTH:
        raise ValueError("annual/cash input graph exceeds the depth limit")
    active = set() if active is None else active
    visited = set() if visited is None else visited
    traversable = (
        is_dataclass(value) and not isinstance(value, type)
    ) or type(value) is tuple
    if traversable:
        identity = id(value)
        if identity in active:
            raise ValueError("annual/cash input graph contains a cycle")
        if identity in visited:
            return
        if len(visited) >= _MAX_GRAPH_NODES:
            raise ValueError("annual/cash input graph exceeds the node limit")
        active.add(identity)
        visited.add(identity)
        try:
            if type(value) is tuple:
                for item in value:
                    _exact_graph(
                        item, active=active, visited=visited, depth=depth + 1
                    )
                return
            expected = {item.name for item in fields(type(value))}
            if not hasattr(value, "__dict__") or set(vars(value)) != expected:
                raise ValueError("annual/cash input is not an exact validated snapshot")
            if type(value).__module__.split(".")[:2] != ["reserved", "engines"]:
                raise ValueError("annual/cash input contains an unsupported contract")
            for item in fields(type(value)):
                _exact_graph(
                    object.__getattribute__(value, item.name),
                    active=active,
                    visited=visited,
                    depth=depth + 1,
                )
            return
        finally:
            active.remove(identity)
    if isinstance(value, Enum):
        if type(value).__module__.split(".")[:2] != ["reserved", "engines"]:
            raise ValueError("annual/cash input contains an unsupported enum")
        return
    if type(value) in (str, int, bool, date, Decimal) or value is None:
        if type(value) is Decimal and not value.is_finite():
            raise ValueError("annual/cash input contains non-finite numeric state")
        return
    raise ValueError("annual/cash input contains unsupported state")


def _source_references(value: AnnualToCashPosition) -> tuple[str, ...]:
    annual = value.considered_annual_position
    reconciliation = value.obligation_reconciliation
    position = value.funding_position
    assert reconciliation is not None and position is not None
    account = reconciliation.considered_account
    refs = [*annual.evidence_ids]
    for item in account.considered_charges:
        refs.extend((item.charge_id, item.source_reference))
    for item in account.considered_credits:
        refs.extend((item.credit_id, item.source_reference))
    for item in account.considered_allocations:
        refs.extend((item.allocation_id, item.source_reference))
    evidence = position.considered_set_aside
    if evidence is not None:
        refs.extend((evidence.evidence_id, evidence.source_reference))
        refs.extend(item.allocation_id for item in evidence.allocations)
    if (
        any(type(item) is not str or not _SOURCE_ID.fullmatch(item) for item in refs)
        or len(refs) != len(set(refs))
    ):
        raise ValueError("annual/cash source identities are invalid or duplicated")
    return tuple(refs)


def _recompute_nested(value: AnnualToCashPosition) -> None:
    assessed = value.poa_assessment
    balancing = value.balancing_position
    reconciliation = value.obligation_reconciliation
    position = value.funding_position
    assert assessed is not None and balancing is not None
    assert reconciliation is not None and position is not None
    recomputed_reconciliation = obligations.reconcile_cash_obligations(
        account_reconciliation=reconciliation.considered_account,
        poa_assessment=assessed,
        balancing_position=balancing,
    )
    if recomputed_reconciliation != reconciliation:
        raise ValueError("cash-obligation reconciliation does not match upstream inputs")
    evidence = position.considered_set_aside
    if evidence is None or type(evidence.observed_on) is not date:
        raise ValueError("calculated funding requires exact set-aside evidence")
    evidence_age = (value.as_of - evidence.observed_on).days
    if evidence_age < 0:
        raise ValueError("set-aside evidence cannot be observed in the future")
    recomputed_position = funding.compose_cash_funding_position(
        obligation_reconciliation=reconciliation,
        set_aside_evidence=evidence,
        as_of=value.as_of,
        # For an already-calculated result, output is independent of the
        # original unretained threshold at this minimum non-stale boundary.
        stale_after_days=evidence_age,
    )
    if recomputed_position != position:
        raise ValueError("cash-funding position does not match upstream inputs")


def _validate(value: object, supplied_references: object) -> AnnualToCashPosition:
    if type(value) is not AnnualToCashPosition:
        raise ValueError("annual/cash input must be an exact AnnualToCashPosition")
    _exact_graph(value)
    # The accepted upstream 1.0 composer always sources the final liability as
    # LOCAL_ESTIMATE. CALCULATED cannot authenticate exact HMRC provenance.
    if (
        value.contract_version != ANNUAL_TO_CASH_VERSION
        or value.status is not AnnualToCashStatus.QUALIFIED_LOCAL_RESULT
        or "annual_liability_is_local_estimate_not_hmrc_issued" not in value.limitations
        or type(value.as_of) is not date
        or value.tax_year != value.considered_annual_position.tax_year
        or type(value.nation) is not str
        or value.nation not in _SUPPORTED_NATIONS
        or value.nation != value.considered_annual_position.nation
        or value.ruleset_version != value.considered_annual_position.ruleset_version
        or value.as_of < value.considered_annual_position.as_of
        or value.annual_position_reference
           != cash_ready_annual_position_identity(value.considered_annual_position)
        or type(value.limitations) is not tuple
        or type(value.prohibited_uses) is not tuple
        or "present_surplus_as_available_or_safe_to_spend" not in value.prohibited_uses
    ):
        raise ValueError("annual/cash input is inconsistent or unsupported")
    assessed, balancing = value.poa_assessment, value.balancing_position
    reconciliation, position = value.obligation_reconciliation, value.funding_position
    if not all(item is not None for item in (assessed, balancing, reconciliation, position)):
        raise ValueError("annual/cash input is incomplete")
    assert assessed is not None and balancing is not None
    assert reconciliation is not None and position is not None
    if (
        type(assessed) is not poa.PoAAssessment
        or type(balancing) is not poa.BalancingPosition
        or type(reconciliation) is not obligations.CashObligationReconciliation
        or type(position) is not funding.CashFundingPosition
        or reconciliation.considered_poa is not assessed
        or reconciliation.considered_balancing is not balancing
        or position.considered_obligations is not reconciliation
        or position.as_of != value.as_of
        or position.status is not funding.FundingComputationStatus.CALCULATED
        or reconciliation.status not in {
            obligations.CashObligationStatus.ALIGNED,
            obligations.CashObligationStatus.OBSERVATION_NOT_HMRC_CONFIRMED,
        }
        or reconciliation.discrepancies
        or value.final_self_assessment_liability != balancing.final_liability
        or not _money(value.final_self_assessment_liability)
    ):
        raise ValueError("annual/cash nested state is inconsistent")
    _recompute_nested(value)
    expected_refs = _source_references(value)
    if type(supplied_references) is not tuple or supplied_references != expected_refs:
        raise ValueError("source or evidence identities do not match the annual/cash snapshot")
    return value


def _source_position_identity(value: AnnualToCashPosition) -> str:
    return f"annual-to-cash-position:sha256-{_digest(value)}"


def annual_to_cash_source_identity(
    value: AnnualToCashPosition,
    *,
    evidence_references: tuple[str, ...],
) -> str:
    """Return the identity of one fully revalidated upstream snapshot."""
    validated = _validate(value, evidence_references)
    return _source_position_identity(validated)


def annual_to_cash_evidence_references(
    value: AnnualToCashPosition,
) -> tuple[str, ...]:
    """Return the exact source identities carried by a complete snapshot.

    This does not admit the snapshot or translate the identities into a
    persistence policy.  It exposes the already-validated source inventory so
    an authenticated adapter can prove that a handoff came from the same live
    annual/cash object while retaining separately approved durable aliases.
    """
    references = _source_references(value)
    _validate(value, references)
    return references


def compose_w8_annual_cash_customer_handoff(
    value: AnnualToCashPosition,
    *,
    evidence_references: tuple[str, ...],
) -> UnboundAnnualCashPresentation | None:
    """Project reviewed facts into an explicitly owner-unbound handoff."""
    try:
        value = _validate(value, evidence_references)
        balancing = value.balancing_position
        reconciliation = value.obligation_reconciliation
        position = value.funding_position
        assert balancing is not None and reconciliation is not None and position is not None
        facts = tuple(
            ObligationFact(_OBLIGATION_KIND[item.kind], item.amount, item.due_date)
            for item in reconciliation.expected_obligations
        )
        if len(facts) != len({item.kind for item in facts}):
            raise ValueError("annual/cash obligations are duplicated or unsupported")
        adjustments = (
            AdjustmentFact(AdjustmentKind.DEDUCTIONS_AND_CREDITS, balancing.deductions_credits),
            AdjustmentFact(AdjustmentKind.PRIOR_PAYMENTS_ON_ACCOUNT, balancing.prior_poa),
            AdjustmentFact(AdjustmentKind.PAYMENTS_MADE, balancing.payments_made_total),
            AdjustmentFact(
                AdjustmentKind.CREDIT_OR_REFUND,
                balancing.excess_credit if balancing.excess_credit is not None else _ZERO,
            ),
        )
        if not all(_money(item.amount) for item in (*facts, *adjustments)):
            raise ValueError("annual/cash projection contains invalid money")
        funding_kind = _FUNDING_KIND[position.balance]
        funding_amount = {
            FundingClassification.GAP: position.funding_gap,
            FundingClassification.EXACT: None,
            FundingClassification.SURPLUS: position.reserve_surplus,
        }[funding_kind]
        presentation = W2PresentationInput(
            W2_VERSION, PresentationStatus.READY,
            EvidenceClassification.QUALIFIED_LOCAL_ESTIMATE,
            value.final_self_assessment_liability, facts, adjustments,
            funding_kind, funding_amount, None,
        )
        if present_w2_customer_language(presentation).safe_to_present is not True:
            raise ValueError("annual/cash projection is not presentable")
        return UnboundAnnualCashPresentation(
            presentation,
            evidence_references,
            value.as_of,
            value.tax_year,
            value.nation,
            value.ruleset_version,
            value.contract_version,
            _source_position_identity(value),
            value.annual_position_reference,
            _issue_token=_ISSUE_TOKEN,
        )
    except (AttributeError, KeyError, TypeError, ValueError, ArithmeticError):
        return None


def validate_w8_annual_cash_customer_handoff(
    value: UnboundAnnualCashPresentation,
    *,
    source_position: AnnualToCashPosition,
    evidence_references: tuple[str, ...],
    expected_as_of: date,
) -> UnboundAnnualCashPresentation:
    """Revalidate one handoff against exact caller-supplied source context.

    ``expected_as_of`` must come from the eventual authenticated request/state
    adapter. This pure boundary deliberately makes no global latest-state claim.
    """
    if type(expected_as_of) is not date:
        raise ValueError("expected_as_of must be an exact date")
    handoff = _validate_handoff_state(value, require_seal=True)
    source = _validate(source_position, evidence_references)
    if (
        source.as_of != expected_as_of
        or handoff.as_of != expected_as_of
        or handoff.tax_year != source.tax_year
        or handoff.nation != source.nation
        or handoff.ruleset_version != source.ruleset_version
        or handoff.annual_to_cash_contract_version != source.contract_version
        or handoff.source_position_identity != _source_position_identity(source)
        or handoff.annual_position_reference != source.annual_position_reference
        or handoff.evidence_references != evidence_references
    ):
        raise ValueError("handoff does not match the exact expected source context")
    expected = compose_w8_annual_cash_customer_handoff(
        source, evidence_references=evidence_references
    )
    if expected is None or _handoff_components(handoff) != _handoff_components(expected):
        raise ValueError("handoff was not derived from the exact source snapshot")
    return handoff


def project_w8_annual_cash_presentation(
    value: UnboundAnnualCashPresentation,
    *,
    source_position: AnnualToCashPosition,
    evidence_references: tuple[str, ...],
    expected_as_of: date,
) -> W2PresentationInput:
    """Return only the still-owner-unbound facts after exact source admission."""
    return validate_w8_annual_cash_customer_handoff(
        value,
        source_position=source_position,
        evidence_references=evidence_references,
        expected_as_of=expected_as_of,
    ).presentation_input


def w8_annual_cash_customer_handoff_identity(
    value: UnboundAnnualCashPresentation,
    *,
    source_position: AnnualToCashPosition,
    evidence_references: tuple[str, ...],
    expected_as_of: date,
) -> str:
    """Return identity only after exact source admission, never from seal alone."""
    handoff = validate_w8_annual_cash_customer_handoff(
        value,
        source_position=source_position,
        evidence_references=evidence_references,
        expected_as_of=expected_as_of,
    )
    return f"w8-annual-cash-handoff:sha256-{_digest(_handoff_components(handoff))}"
