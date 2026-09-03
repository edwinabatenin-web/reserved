"""Pure, fail-closed annual/cash to customer-result handoff for W8-S2C.

The handoff accepts only a live value issued by the reviewed annual-to-cash
producer.  It copies customer-safe facts into the existing W2/W8 presentation
contracts; it does not calculate tax, persist data, call a provider, or grant
payment authority.  Geography is read only from that producer and cannot be
supplied or changed by the handoff caller.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from reserved.engines import cash_funding_position as funding
from reserved.engines import cash_obligation_reconciliation as obligations
from reserved.engines.annual_to_cash_integration import (
    AnnualToCashInputProvenance,
    AnnualToCashPosition,
    AnnualToCashStatus,
    annual_to_cash_position_identity,
    annual_to_cash_position_provenance,
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
)
from reserved.services.w8_customer_result import (
    W8CustomerResult,
    compose_w8_customer_result,
)


_ZERO = Decimal("0.00")
_PENNY = Decimal("0.01")


def _make_handoff():
    """Capture the reviewed collaborators and fixed mappings once.

    Module-name rebinding must not turn an invalid producer value into a
    presentable result.  The producer's public read-only capabilities remain
    the sole authority for issuance identity and provenance.
    """

    identity_reader = annual_to_cash_position_identity
    provenance_reader = annual_to_cash_position_provenance
    public_composer = compose_w8_customer_result
    raw = object.__getattribute__
    decimal_type = Decimal
    date_type = date
    exact_type = type
    supported_nations = frozenset({"England", "Wales", "Northern Ireland"})

    annual_type = AnnualToCashPosition
    provenance_type = AnnualToCashInputProvenance
    annual_status_type = AnnualToCashStatus
    qualified = AnnualToCashStatus.QUALIFIED_LOCAL_RESULT
    calculated = AnnualToCashStatus.CALCULATED
    review_required = AnnualToCashStatus.REVIEW_REQUIRED
    unresolved = AnnualToCashStatus.UNRESOLVED

    balancing_kind = obligations.account.ChargeKind.BALANCING_PAYMENT
    poa_1_kind = obligations.account.ChargeKind.PAYMENT_ON_ACCOUNT_1
    poa_2_kind = obligations.account.ChargeKind.PAYMENT_ON_ACCOUNT_2
    funding_calculated = funding.FundingComputationStatus.CALCULATED
    funding_gap = funding.FundingBalance.GAP
    funding_exact = funding.FundingBalance.EXACT
    funding_surplus = funding.FundingBalance.SURPLUS

    obligation_fact = ObligationFact
    adjustment_fact = AdjustmentFact
    w2_input = W2PresentationInput
    presentation_ready = PresentationStatus.READY
    local_estimate = EvidenceClassification.QUALIFIED_LOCAL_ESTIMATE
    obligation_balancing = ObligationKind.BALANCING_PAYMENT
    obligation_poa_1 = ObligationKind.FIRST_PAYMENT_ON_ACCOUNT
    obligation_poa_2 = ObligationKind.SECOND_PAYMENT_ON_ACCOUNT
    adjustment_deductions = AdjustmentKind.DEDUCTIONS_AND_CREDITS
    adjustment_prior_poa = AdjustmentKind.PRIOR_PAYMENTS_ON_ACCOUNT
    adjustment_payments = AdjustmentKind.PAYMENTS_MADE
    adjustment_credit = AdjustmentKind.CREDIT_OR_REFUND
    funding_gap_public = FundingClassification.GAP
    funding_exact_public = FundingClassification.EXACT
    funding_surplus_public = FundingClassification.SURPLUS
    w2_version = W2_VERSION
    zero = _ZERO
    penny = _PENNY

    def money(value: object) -> bool:
        return (
            exact_type(value) is decimal_type
            and value.is_finite()
            and value >= zero
            and value == value.quantize(penny)
            and not (value.is_zero() and value.is_signed())
        )

    def evidence_references(
        value: AnnualToCashPosition,
        provenance: AnnualToCashInputProvenance,
    ) -> tuple[str, ...]:
        annual = raw(value, "considered_annual_position")
        reconciliation = raw(value, "obligation_reconciliation")
        position = raw(value, "funding_position")
        account = raw(reconciliation, "considered_account")

        refs = [*raw(annual, "evidence_ids")]
        refs.extend(raw(provenance, "deductions_credits_evidence_ids"))
        refs.extend(raw(provenance, "prior_poa_evidence_ids"))
        refs.extend(raw(provenance, "payment_source_ids"))
        for item in raw(account, "considered_charges"):
            refs.extend((raw(item, "charge_id"), raw(item, "source_reference")))
        for item in raw(account, "considered_credits"):
            refs.extend((raw(item, "credit_id"), raw(item, "source_reference")))
        for item in raw(account, "considered_allocations"):
            refs.extend((raw(item, "allocation_id"), raw(item, "source_reference")))
        set_aside = raw(position, "considered_set_aside")
        if set_aside is not None:
            refs.extend((raw(set_aside, "evidence_id"), raw(set_aside, "source_reference")))
            refs.extend(raw(item, "allocation_id") for item in raw(set_aside, "allocations"))
        if not refs or any(exact_type(item) is not str for item in refs):
            raise ValueError("annual/cash source identities are invalid")
        # A single source record may support several distinct HMRC charges.
        # The public W8 contract requires unique references, so preserve the
        # complete semantic source set in deterministic first-occurrence order.
        return tuple(dict.fromkeys(refs))

    def obligation_kind(value: object) -> ObligationKind:
        if value is balancing_kind:
            return obligation_balancing
        if value is poa_1_kind:
            return obligation_poa_1
        if value is poa_2_kind:
            return obligation_poa_2
        raise ValueError("annual/cash obligation kind is unsupported")

    def project(
        value: AnnualToCashPosition,
        *,
        user_id: str,
        business_id: str,
        evidence_references: tuple[str, ...],
    ) -> W8CustomerResult | None:
        """Return a customer-safe result, or ``None`` for any unsafe position.

        Ownership failures remain categorical ``ValueError`` results from the
        already-reviewed public-result boundary. Geography is producer-bound;
        malformed or absent geography fails closed as ``None``. No input value
        is included in failure text.
        """

        try:
            if exact_type(value) is not annual_type:
                raise ValueError("annual/cash position is unsupported")
            issued_identity = identity_reader(value)
            provenance = provenance_reader(value)
            if exact_type(issued_identity) is not str or exact_type(provenance) is not provenance_type:
                raise ValueError("annual/cash producer evidence is unsupported")
            tax_year = raw(value, "tax_year")
            nation = raw(value, "nation")
            if exact_type(nation) is not str or nation not in supported_nations:
                raise ValueError("annual/cash geography is unsupported")

            status = raw(value, "status")
            if exact_type(status) is not annual_status_type:
                raise ValueError("annual/cash status is unsupported")
            if status is review_required or status is unresolved:
                return None
            if status is not qualified and status is not calculated:
                raise ValueError("annual/cash status is unsupported")

            # Even a producer status named CALCULATED contains a locally
            # calculated annual liability.  It must never be promoted to an
            # HMRC-confirmed or exact customer claim.
            reconciliation = raw(value, "obligation_reconciliation")
            balancing = raw(value, "balancing_position")
            position = raw(value, "funding_position")
            if reconciliation is None or balancing is None or position is None:
                raise ValueError("annual/cash position is incomplete")
            if raw(position, "status") is not funding_calculated:
                raise ValueError("annual/cash funding is not actionable")

            expected_refs = evidence_references_for_value = evidence_references_fn(
                value, provenance
            )
            if (
                exact_type(evidence_references) is not tuple
                or any(exact_type(item) is not str for item in evidence_references)
                or evidence_references != expected_refs
            ):
                raise ValueError("source or evidence identities do not match")

            obligation_facts = []
            for item in raw(reconciliation, "expected_obligations"):
                amount = raw(item, "amount")
                due_on = raw(item, "due_date")
                if not money(amount) or exact_type(due_on) is not date_type:
                    raise ValueError("annual/cash obligation is invalid")
                obligation_facts.append(
                    obligation_fact(obligation_kind(raw(item, "kind")), amount, due_on)
                )
            facts = tuple(obligation_facts)
            if len(facts) != len({raw(item, "kind") for item in facts}):
                raise ValueError("annual/cash obligations are duplicated")

            deductions = raw(balancing, "deductions_credits")
            prior_poa = raw(balancing, "prior_poa")
            payments = raw(balancing, "payments_made_total")
            excess_credit = raw(balancing, "excess_credit")
            credit = zero if excess_credit is None else excess_credit
            amounts = (deductions, prior_poa, payments, credit)
            if not all(money(item) for item in amounts):
                raise ValueError("annual/cash adjustment is invalid")
            adjustments = (
                adjustment_fact(adjustment_deductions, deductions),
                adjustment_fact(adjustment_prior_poa, prior_poa),
                adjustment_fact(adjustment_payments, payments),
                adjustment_fact(adjustment_credit, credit),
            )

            balance = raw(position, "balance")
            if balance is funding_gap:
                funding_kind = funding_gap_public
                funding_amount = raw(position, "funding_gap")
                if not money(funding_amount) or funding_amount == zero:
                    raise ValueError("annual/cash funding gap is invalid")
            elif balance is funding_exact:
                funding_kind = funding_exact_public
                funding_amount = None
                if raw(position, "funding_gap") != zero or raw(position, "reserve_surplus") != zero:
                    raise ValueError("annual/cash exact funding is invalid")
            elif balance is funding_surplus:
                funding_kind = funding_surplus_public
                funding_amount = raw(position, "reserve_surplus")
                if not money(funding_amount) or funding_amount == zero:
                    raise ValueError("annual/cash funding surplus is invalid")
            else:
                raise ValueError("annual/cash funding state is unsupported")

            liability = raw(value, "final_self_assessment_liability")
            if not money(liability):
                raise ValueError("annual/cash liability is invalid")
            presentation = w2_input(
                w2_version,
                presentation_ready,
                local_estimate,
                liability,
                facts,
                adjustments,
                funding_kind,
                funding_amount,
                None,
            )
            # Detect any mutation between the first producer lookup and the
            # completed copy before exposing the public result.
            if identity_reader(value) != issued_identity or provenance_reader(value) is not provenance:
                raise ValueError("annual/cash producer identity changed")
        except (AttributeError, KeyError, TypeError, ValueError, ArithmeticError):
            return None

        return public_composer(
            presentation,
            nation=nation,
            tax_year=tax_year,
            user_id=user_id,
            business_id=business_id,
            evidence_references=evidence_references_for_value,
        )

    evidence_references_fn = evidence_references
    return project


compose_w8_annual_cash_customer_result = _make_handoff()
compose_w8_annual_cash_customer_result.__name__ = (
    "compose_w8_annual_cash_customer_result"
)
compose_w8_annual_cash_customer_result.__qualname__ = (
    "compose_w8_annual_cash_customer_result"
)
del _make_handoff
