"""W8 S2 progressive-integration assurance over already-integrated contracts.

This module is self-contained: it imports production/public contracts directly
and does not import fixtures or helpers from any other test module.  It proves
coexistence and fail-closed behaviour on the existing integrated lineage. The
provider-to-tax handoff is asserted to be confined to its exact named boundary
rather than fabricated or globally absent; the presentation/persistence and
geography-admission handoffs are exercised at their integrated bounded states,
while physical persistence and provider activation remain non-passing gates.
"""

from __future__ import annotations

import ast
import re
import subprocess
from dataclasses import dataclass, fields
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from reserved.engines import cash_funding_position as funding
from reserved.engines import cash_obligation_reconciliation as obligations
from reserved.engines import payments_on_account as poa
from reserved.engines import sa_account_reconciliation as account
from reserved.engines.annual_to_cash_integration import (
    AnnualToCashStatus,
    balance_item_identity,
    cash_ready_annual_position_identity,
    compose_annual_to_cash_position,
    payment_made_identity,
    prior_year_evidence_identity,
)
from reserved.engines.cash_ready_annual_position import (
    NoStudentLoanEvidence,
    annual_position_identity,
    compose_cash_ready_annual_position,
    student_loan_position_identity,
)
from reserved.engines.hicbc_integration import (
    INFORMATIONAL,
    PAYMENT,
    PERSONALISED_ESTIMATE,
    RESERVE_GUIDANCE,
    integrate_hicbc,
)
from reserved.engines.hicbc_partner import (
    ANI_COMPONENT_WHOLE,
    CLAIMANT_PERSON,
    PartnerEvidence,
    determine_hicbc_responsibility,
)
from reserved.engines.integrated_annual_position import calculate_annual_position
from reserved.engines.mtd_readiness import (
    IncomeKind,
    IncomeSource,
    MtdStatus,
    assess_mtd_readiness,
)
from reserved.providers.accounting.contracts import (
    AccountingBusiness,
    AccountingProviderName,
    SemanticAdapterResult,
    SourceObservation,
)
from reserved.providers.accounting.freeagent_invoice_contract import (
    COMPANY_DOCUMENTED_FIELDS,
    FreeAgentCompanyRecord,
    FreeAgentInvoiceRecord,
    parse_company,
    parse_invoice_list,
)
from reserved.providers.accounting.normalisation import (
    CanonicalQuarantineError,
    classify_observation_relation,
)
from reserved.providers.accounting.quickbooks_invoice_payment_adapter import (
    InvoiceAdapterResult,
    adapt_invoice,
)
from reserved.providers.accounting.quickbooks_oauth_contract import RealmBinding
from reserved.providers.accounting.quickbooks_observation_contract import (
    CompanyInfoObservation,
    InvoiceObservation,
    observe_company_info,
    observe_invoice,
)
from reserved.providers.accounting.xero_invoice_contract import (
    XeroInvoice,
    XeroInvoiceMapping,
    map_detailed_invoice_response,
)
from reserved_west import release_gate as rg

AS_OF = date(2027, 4, 5)
RETRIEVED_AT = datetime(2026, 8, 3, 10, 0, 0, tzinfo=timezone.utc)

# A complete, explicitly closed Blind Person's Allowance fact group so the
# annual position is not needlessly treated as fact-incomplete.
BPA = {
    "blind_persons_allowance_entitled": False,
    "blind_persons_allowance_transferred_in": "0",
    "blind_persons_allowance_transferred_out": "0",
}


# ── Annual-to-cash construction helpers (production contracts only) ─────────

def mixed_annual_position():
    """A mixed, fully supported annual income feeding W1 -> cash-ready W2."""
    annual_tax = calculate_annual_position({
        "employment_income": "30000",
        "sole_trade_profit": "15000",
        "savings_interest": "2000",
        "dividends": "3000",
        **BPA,
    })
    assert annual_tax.calculation_status == "calculated"
    assert set(annual_tax.included_families) == {"income_tax", "class_4_ni"}
    no_loans = NoStudentLoanEvidence(
        "annual-no-loan", "2026/27", "uk-2026-27-v4", AS_OF,
        "person-a", "synthetic", "synthetic:no-loan", True,
    )
    return compose_cash_ready_annual_position(
        annual_tax,
        no_loans,
        annual_tax_reference=annual_position_identity(annual_tax),
        student_loan_reference=student_loan_position_identity(no_loans),
        as_of=AS_OF,
    )


def prior_year(*, amount="1200.00", effective=AS_OF, retrieved=AS_OF,
               uncertainty=()):
    return poa.PriorYearEvidence(
        tax_year="2026/27",
        source=poa.SourceKind.HMRC_ISSUED,
        effective_date=effective,
        retrieval_date=retrieved,
        completeness=poa.Completeness.COMPLETE_FOR_PURPOSE,
        income_tax=Decimal(amount),
        hicbc=Decimal("0.00"),
        class_4_nic=Decimal("0.00"),
        tax_deducted_at_source=Decimal("0.00"),
        uncertainty=uncertainty,
    )


def balance_item(amount, source=poa.SourceKind.HMRC_ISSUED, retrieved=AS_OF):
    return poa.BalanceItem(
        Decimal(amount), source, poa.Completeness.COMPLETE_FOR_PURPOSE, retrieved
    )


def payment(amount="100.00", *, reference="cash:payment-1"):
    return poa.PaymentMade(
        poa.PaymentKind.BALANCING_PAYMENT,
        Decimal(amount),
        poa.SourceKind.HMRC_ISSUED,
        AS_OF,
        AS_OF,
        reference=reference,
    )


def _observed_account(assessed, balancing, *, hmrc=True, mismatch=False):
    source = account.EvidenceSource.HMRC_ONLINE if hmrc else account.EvidenceSource.MANUAL
    charges = []
    for instalment in assessed.instalments:
        kind = {
            "payment_on_account_1": account.ChargeKind.PAYMENT_ON_ACCOUNT_1,
            "payment_on_account_2": account.ChargeKind.PAYMENT_ON_ACCOUNT_2,
        }[instalment.label]
        amount = instalment.amount + (Decimal("1.00") if mismatch and not charges else Decimal("0"))
        charges.append(account.AccountCharge(
            f"charge-{instalment.label}", kind, assessed.poa_tax_year, amount,
            instalment.due_date, AS_OF, AS_OF, source,
            account.Completeness.COMPLETE_FOR_PURPOSE, f"account:{instalment.label}",
        ))
    if balancing.status is poa.BalanceStatus.REMAINING_BALANCE and balancing.remaining_balance:
        charges.append(account.AccountCharge(
            "charge-balancing", account.ChargeKind.BALANCING_PAYMENT,
            balancing.tax_year, balancing.remaining_balance, balancing.due_date,
            AS_OF, AS_OF, source, account.Completeness.COMPLETE_FOR_PURPOSE,
            "account:balancing",
        ))
    credits = ()
    if not charges:
        credits = (account.AccountCredit(
            "credit-evidence", account.CreditKind.HMRC_CREDIT, Decimal("1.00"),
            AS_OF, AS_OF, source, account.Completeness.COMPLETE_FOR_PURPOSE,
            "account:credit-evidence",
        ),)
    return account.reconcile_sa_account(
        charges, credits, (), as_of=AS_OF,
        coverage=account.Completeness.COMPLETE_FOR_PURPOSE,
    )


def _set_aside_for(assessed, balancing, amount=None):
    expected = obligations.reconcile_cash_obligations(
        account_reconciliation=_observed_account(assessed, balancing),
        poa_assessment=assessed,
        balancing_position=balancing,
    ).expected_obligations
    total = sum((item.amount for item in expected), Decimal("0.00"))
    selected = total if amount is None else Decimal(amount)
    allocations = []
    remaining = selected
    for index, item in enumerate(expected):
        allocated = min(item.amount, remaining)
        if allocated:
            allocations.append(funding.SetAsideAllocation(
                f"set-aside-allocation-{index}", item.obligation_id, allocated
            ))
        remaining -= allocated
    return funding.SetAsideEvidence(
        "set-aside-evidence", selected, AS_OF, AS_OF,
        funding.SetAsideSource.CUSTOMER_RECORDED,
        funding.EvidenceCompleteness.COMPLETE_FOR_PURPOSE,
        "set-aside:source", tuple(allocations), (),
    )


def compose(annual=None, *, prior=None, deductions=None, prior_poa=None,
            payments=(), hmrc=True, mismatch=False, set_aside="exact",
            annual_reference=None, deductions_evidence_ids=("cash:deductions-credits",),
            prior_poa_evidence_ids=("cash:prior-poa",)):
    annual = annual if annual is not None else mixed_annual_position()
    prior = prior if prior is not None else prior_year()
    deductions = deductions if deductions is not None else balance_item("0.00")
    prior_poa = prior_poa if prior_poa is not None else balance_item("0.00")
    assessed = poa.assess_payments_on_account(
        preceding_year_status=poa.PrecedingYearStatus.ESTABLISHED,
        prior_year=prior,
        as_of=AS_OF,
    )
    balancing = poa.compose_balancing_position(
        tax_year=annual.tax_year,
        final_liability=poa.BalanceItem(
            annual.final_self_assessment_liability,
            poa.SourceKind.LOCAL_ESTIMATE,
            poa.Completeness.COMPLETE_FOR_PURPOSE,
            AS_OF,
        ),
        deductions_credits=deductions,
        prior_poa=prior_poa,
        payments_made=payments,
        as_of=AS_OF,
    )
    account_result = _observed_account(assessed, balancing, hmrc=hmrc, mismatch=mismatch)
    evidence = None if set_aside is None else _set_aside_for(
        assessed, balancing, None if set_aside == "exact" else set_aside
    )
    return compose_annual_to_cash_position(
        annual_position=annual,
        annual_position_reference=annual_reference or cash_ready_annual_position_identity(annual),
        preceding_year_status=poa.PrecedingYearStatus.ESTABLISHED,
        prior_year_evidence=prior,
        prior_year_reference=prior_year_evidence_identity(prior),
        deductions_credits=deductions,
        deductions_credits_reference=balance_item_identity(
            deductions, channel="deductions-credits", evidence_ids=deductions_evidence_ids
        ),
        deductions_credits_evidence_ids=deductions_evidence_ids,
        prior_poa=prior_poa,
        prior_poa_reference=balance_item_identity(
            prior_poa, channel="prior-poa", evidence_ids=prior_poa_evidence_ids
        ),
        prior_poa_evidence_ids=prior_poa_evidence_ids,
        payments_made=payments,
        payment_content_references=tuple(payment_made_identity(item) for item in payments),
        account_reconciliation=account_result,
        set_aside_evidence=evidence,
        as_of=AS_OF,
    )


# ── 1. Mixed supported annual income feeds annual-to-cash composition ────────

def test_mixed_supported_income_composes_annual_to_cash():
    result = compose()
    assert result.status is AnnualToCashStatus.QUALIFIED_LOCAL_RESULT
    assert result.final_self_assessment_liability is not None
    assert result.poa_assessment.status is poa.PoAStatus.APPLICABLE
    assert len(result.poa_assessment.instalments) == 2
    assert result.obligation_reconciliation.status is obligations.CashObligationStatus.ALIGNED
    assert result.funding_position.status is funding.FundingComputationStatus.CALCULATED
    assert result.funding_position.balance is funding.FundingBalance.EXACT
    # Annual tax and Class 4 remain distinct and both contributed to the total.
    assert result.considered_annual_position.annual_tax_families == ("income_tax", "class_4_ni")
    assert result.considered_annual_position.final_self_assessment_liability > Decimal("0")


# ── 2. Missing, stale and conflicting evidence fails closed ──────────────────

def test_missing_set_aside_evidence_suppresses_funding_point_result():
    result = compose(set_aside=None)
    assert result.status is AnnualToCashStatus.UNRESOLVED
    assert result.final_self_assessment_liability is None
    assert result.funding_position.status is funding.FundingComputationStatus.INSUFFICIENT_FACTS


def test_stale_prior_year_evidence_fails_closed():
    from datetime import timedelta

    stale = compose(prior=prior_year(
        effective=AS_OF - timedelta(days=60),
        retrieved=AS_OF - timedelta(days=46),
    ))
    assert stale.status is AnnualToCashStatus.UNRESOLVED
    assert stale.poa_assessment.status is poa.PoAStatus.STALE_REQUIRES_REVIEW
    assert stale.final_self_assessment_liability is None


def test_conflicting_prior_year_evidence_fails_closed():
    conflicting = compose(prior=prior_year(uncertainty=("conflicting",)))
    assert conflicting.status is AnnualToCashStatus.UNRESOLVED
    assert conflicting.poa_assessment.status is poa.PoAStatus.CONFLICT_REQUIRES_REVIEW
    assert conflicting.final_self_assessment_liability is None


def test_account_discrepancy_requires_review_and_suppresses_final_point_result():
    result = compose(mismatch=True)
    assert result.status is AnnualToCashStatus.REVIEW_REQUIRED
    assert result.final_self_assessment_liability is None
    assert result.obligation_reconciliation.discrepancies


# ── 3. Duplicate / source-substitution / double-count protections ────────────

def test_duplicate_payment_identity_fails_closed_before_arithmetic():
    duplicate = payment("100.00")
    result = compose(payments=(duplicate, duplicate))
    assert result.status is AnnualToCashStatus.UNRESOLVED
    assert "evidence_identity_reused_across_cash_channels" in result.limitations


def test_reused_source_identity_across_cash_channels_fails_closed():
    result = compose(deductions_evidence_ids=("account:balancing",))
    assert result.status is AnnualToCashStatus.UNRESOLVED
    assert "evidence_identity_reused_in_account_channel" in result.limitations


def test_cross_provider_source_substitution_is_rejected():
    first = _xero_mapping().observation
    second = _quickbooks_mapping().observation
    with pytest.raises(CanonicalQuarantineError, match="source identities"):
        classify_observation_relation(first, second)


def test_cross_business_source_substitution_is_rejected():
    first = _xero_mapping(tenant_id="business-1").observation
    second = _xero_mapping(tenant_id="business-2").observation
    with pytest.raises(CanonicalQuarantineError, match="source identities"):
        classify_observation_relation(first, second)


# ── 4. HICBC and MTD uncertainty / fail-close boundaries ─────────────────────

def test_hicbc_ambiguous_result_is_excluded_from_actionable_purposes():
    result = _hicbc_result(user_ani=70000, partner=_evidence(low="65000", high="75000"))
    assert result.responsibility_status == "ambiguous"
    for purpose in (PERSONALISED_ESTIMATE, RESERVE_GUIDANCE, PAYMENT):
        contribution = integrate_hicbc(result, purpose)
        assert not contribution.included
        assert not contribution.actionable
        assert contribution.charge is None


def test_hicbc_payment_is_never_actionable_even_when_determinate():
    result = _hicbc_result(user_ani=70000, partner=_evidence(point="50000"))
    info = integrate_hicbc(result, INFORMATIONAL)
    assert info.included and info.charge == Decimal("703.00")
    payment_contribution = integrate_hicbc(result, PAYMENT)
    assert payment_contribution.included is False
    assert payment_contribution.actionable is False
    assert "not independently approved" in payment_contribution.reason


def test_mtd_over_threshold_with_unknown_eligibility_fails_closed():
    result = assess_mtd_readiness(
        [IncomeSource("trade", IncomeKind.SOLE_TRADE, "51000")],
        assessment_tax_year="2024-25",
    )
    assert result.status is MtdStatus.MTD_DATA_INCOMPLETE
    assert result.eligibility_complete is False


def test_mtd_incomplete_source_fails_closed_over_threshold():
    result = assess_mtd_readiness(
        [IncomeSource("trade", IncomeKind.SOLE_TRADE, "51000", complete=False)],
        assessment_tax_year="2024-25",
    )
    assert result.status is MtdStatus.MTD_DATA_INCOMPLETE
    assert result.data_complete is False


# ── 5. Actual reviewed provider contract/type coexistence ────────────────────

def test_reviewed_freeagent_xero_and_quickbooks_public_contracts_coexist():
    # Exercise the provider-specific public contracts in one process. FreeAgent
    # currently stops at its reviewed invoice record; Xero reaches its reviewed
    # invoice mapping; QuickBooks reaches its observation and canonical adapter.
    # The assertions preserve those unequal boundaries rather than inventing a
    # common semantic capability.
    freeagent = _freeagent_invoice_records()[0]
    xero = _xero_mapping()
    quickbooks_source = _quickbooks_observation()
    quickbooks = adapt_invoice(
        quickbooks_source,
        binding=_quickbooks_binding(),
        import_run_id="run-1",
    )

    assert isinstance(freeagent, FreeAgentInvoiceRecord)
    assert freeagent.url == "https://api.freeagent.com/v2/invoices/1"
    assert isinstance(xero, XeroInvoiceMapping)
    assert isinstance(xero.invoice, XeroInvoice)
    assert isinstance(xero.observation, SourceObservation)
    assert isinstance(xero.adapter_result, SemanticAdapterResult)
    assert xero.observation.provenance.identity.provider is AccountingProviderName.XERO
    assert isinstance(quickbooks_source, InvoiceObservation)
    assert isinstance(quickbooks, InvoiceAdapterResult)
    assert isinstance(quickbooks.observation, SourceObservation)
    assert isinstance(quickbooks.semantic_result, SemanticAdapterResult)
    assert quickbooks.document.provenance.identity.provider is AccountingProviderName.QUICKBOOKS
    assert xero.invoice.invoice_id == quickbooks.source_observation.entity_id == "invoice-1"
    assert type(freeagent) is not type(xero.invoice)
    assert type(xero) is not type(quickbooks)


def test_transport_provider_activation_remains_non_passing():
    # Reviewed provider data contracts coexist, but the transport-facing
    # provider classes remain disabled. This test does not infer credentials,
    # network support or equal adapter depth from the contract evidence above.
    from reserved.providers.accounting.freeagent import FreeAgentProvider
    from reserved.providers.accounting.quickbooks import QuickBooksProvider
    from reserved.providers.accounting.xero import XeroProvider

    for provider_cls in (FreeAgentProvider, XeroProvider, QuickBooksProvider):
        instance = provider_cls()
        with pytest.raises(NotImplementedError):
            instance.list_invoices("credential-reference")
        with pytest.raises(NotImplementedError):
            instance.authorisation_url("user-1", "https://example.test/callback")


# ── 6. Absent handoffs are expressed as non-passing gates ────────────────────

def test_october_launch_candidate_is_truthfully_not_ready():
    octo = rg.october_launch_candidate()
    assert octo["status"] == "not_ready"
    blockers = {b["id"] for b in octo["blocking_components"]}
    assert {"freeagent_integration", "xero_integration", "quickbooks_integration",
            "mtd_indication"} <= blockers


def test_provider_to_tax_handoff_is_confined_to_named_boundary():
    # The handoff is no longer asserted absent. It may exist, but only at the
    # exact authorised file; every accounting-contract import outside the
    # provider package must occur solely in that named boundary.
    root = _root()
    permitted = root / "reserved" / "engines" / "accounting_tax_handoff.py"
    accounting_pkg = root / "reserved" / "providers" / "accounting"
    accounting_symbols = {
        "SourceObservation", "SemanticAdapterResult",
        "CanonicalAccountingTaxInput", "AccountingEntry",
        "normalise_document", "AccountingInvoice",
    }
    consumers = []
    invalid_handoff_imports = []
    for path in (root / "reserved").rglob("*.py"):
        if accounting_pkg in path.parents:
            continue
        try:
            facts = _import_facts_in_file(path)
        except ValueError as exc:
            pytest.fail(f"cannot safely inspect {path.relative_to(root)}: {exc}")
        accounting_facts = tuple(
            fact for fact in facts
            if _w8_fact_touches_accounting(fact, accounting_symbols)
        )
        if accounting_facts:
            consumers.append(path)
            if path == permitted:
                if path.is_symlink() or path.resolve(strict=True) != permitted.resolve(strict=True):
                    invalid_handoff_imports.append("consumer path is not exact/resolved/regular")
                for fact in accounting_facts:
                    if not (
                        fact.kind == "from"
                        and fact.level == 0
                        and fact.module == "reserved.providers.accounting.contracts"
                        and fact.symbol in {
                            "CanonicalAccountingTaxInput", "SourceObservation"
                        }
                        and fact.alias is None
                    ):
                        invalid_handoff_imports.append(repr(fact))
    assert set(consumers) <= {permitted}, (
        "accounting contracts may be consumed only by "
        "reserved/engines/accounting_tax_handoff.py; found "
        f"{[p.relative_to(root) for p in consumers]}"
    )
    assert invalid_handoff_imports == [], (
        "the named handoff may use only explicit unaliased from-imports of "
        "CanonicalAccountingTaxInput and SourceObservation from the exact "
        f"contracts module; found {invalid_handoff_imports}"
    )


def test_presentation_and_persistence_handoffs_are_absent():
    internal_markers = (
        "integrated_annual_position", "annual_to_cash_integration",
        "compose_annual_to_cash_position", "AnnualToCashPosition",
        "CashReadyAnnualPosition",
    )
    layers = (
        _root() / "reserved" / "web",
        _root() / "reserved" / "services",
        _root() / "reserved" / "api",
        _root() / "reserved" / "database.py",
        _root() / "reserved" / "models",
    )
    permitted_handoff = (
        _root() / "reserved" / "services" / "w8_annual_cash_customer_handoff.py"
    )
    assert permitted_handoff.is_file() and not permitted_handoff.is_symlink()
    assert permitted_handoff.resolve(strict=True) == permitted_handoff
    permitted_hicbc = _root() / "reserved/services/hicbc_annual_source_runtime.py"
    assert permitted_hicbc.is_file() and not permitted_hicbc.is_symlink()
    assert permitted_hicbc.resolve(strict=True) == permitted_hicbc
    violations = []
    for layer in layers:
        paths = (layer,) if layer.is_file() else tuple(layer.rglob("*.py"))
        for path in paths:
            text = path.read_text(errors="ignore")
            violations.extend(_hicbc_boundary_source_violations(path, text))
            if path == permitted_handoff:
                violations.extend(_annual_cash_handoff_source_violations(text))
            elif path == permitted_hicbc:
                # One already-authorised caller; its AST is checked above.
                # No other annual/persistence/customer exposure is admitted.
                continue
            else:
                for marker in internal_markers:
                    if marker in text:
                        violations.append(f"{path.relative_to(_root())} contains {marker}")
    assert violations == [], "internal annual components leaked into customer/persistence layers"


def _hicbc_boundary_source_violations(path: Path, source: str) -> list[str]:
    """Local mirror of the accepted HICBC AST barrier, not a test-helper import."""
    permitted = _root() / "reserved/services/hicbc_annual_source_runtime.py"
    caller = _root() / "reserved/web/hicbc.py"
    service = "reserved.services.hicbc_annual_source_runtime"
    symbol = "own_ani_from_manual_annual"
    if path != permitted:
        if path != caller:
            return ["additional HICBC annual-source consumer"] if (
                symbol in source or "hicbc_annual_source_runtime" in source
            ) else []
        tree = ast.parse(source)
        imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
                   and node.module == service]
        if len(imports) != 1 or imports[0].level or [
            (alias.name, alias.asname) for alias in imports[0].names
        ] != [(symbol, None)]:
            return ["HICBC caller requires exact unaliased source import"]
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == symbol]
        previews = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == "annual_preview"]
        if (len(calls) != 1 or len(previews) != 1
                or calls[0] not in list(ast.walk(previews[0]))
                or ast.unparse(calls[0]) != "own_ani_from_manual_annual(payload, tax_year)"):
            return ["HICBC source may be called only by the named preview"]
        parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in {
                symbol, "hicbc_annual_source_runtime"
            }:
                return ["HICBC source module/function attribute is forbidden"]
            if isinstance(node, ast.Import) and any(
                "hicbc_annual_source_runtime" in alias.name for alias in node.names
            ):
                return ["HICBC source module import/alias is forbidden"]
            if isinstance(node, ast.ImportFrom) and node not in imports and (
                "hicbc_annual_source_runtime" in (node.module or "")
                or any(alias.name in {symbol, "hicbc_annual_source_runtime"}
                       for alias in node.names)
            ):
                return ["additional HICBC source import is forbidden"]
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and (
                "hicbc_annual_source_runtime" in node.value or symbol in node.value
            ):
                return ["dynamic HICBC source reference is forbidden"]
            if isinstance(node, ast.Name) and node.id == symbol and isinstance(node.ctx, ast.Load):
                parent = parents.get(node)
                if not (isinstance(parent, ast.Call) and parent.func is node):
                    return ["HICBC source function alias is forbidden"]
        return []

    allowed_imports = {
        ("decimal", "Decimal", None),
        ("reserved.engines.integrated_annual_position", "calculate_annual_position", None),
    }
    allowed_calls = {
        "re.compile", "frozenset", "type", "set", "ValueError", "_MONEY.fullmatch",
        "calculate_annual_position", "ani.is_finite",
    }
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    violations = []
    # Naming a returned whole result ``ani`` must not bypass the scalar boundary.
    producer_calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                      and isinstance(node.func, ast.Name)
                      and node.func.id == "calculate_annual_position"]
    if len(producer_calls) != 1:
        violations.append("exactly one annual producer is required")
    elif not (
        isinstance(parents.get(producer_calls[0]), ast.Assign)
        and ast.unparse(parents[producer_calls[0]])
        == "result = calculate_annual_position(facts, tax_year=tax_year)"
    ):
        violations.append("annual producer must bind only the reviewed result")
    for name, expected in (
        ("result", "result = calculate_annual_position(facts, tax_year=tax_year)"),
        ("ani", "ani = result.adjusted_net_income"),
    ):
        writes = [node for node in ast.walk(tree) if isinstance(node, ast.Name)
                  and node.id == name and isinstance(node.ctx, ast.Store)]
        if (len(writes) != 1 or not isinstance(parents.get(writes[0]), ast.Assign)
                or ast.unparse(parents[writes[0]]) != expected):
            violations.append(f"{name} requires its single reviewed binding")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if [(a.name, a.asname) for a in node.names] != [("re", None)]:
                violations.append("unauthorised import")
        if isinstance(node, ast.ImportFrom):
            if node.level or any((node.module, a.name, a.asname) not in allowed_imports for a in node.names):
                violations.append("unauthorised from-import")
        if isinstance(node, ast.Call) and _annual_cash_call_target(node.func) not in allowed_calls:
            violations.append("unauthorised call")
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "result" and node.attr not in {"adjusted_net_income", "unsupported_families"}:
                violations.append("annual result exposure")
        if isinstance(node, ast.Return) and (node.value is None or ast.unparse(node.value) != "ani"):
            violations.append("only own ANI may leave source")
        if isinstance(node, ast.Name) and node.id in {"getattr", "globals", "locals", "__builtins__"}:
            violations.append("dynamic access")
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            parent = parents.get(node)
            if node.id == "result" and not isinstance(parent, ast.Attribute):
                violations.append("annual result escaped into alias or operand")
            if node.id == "calculate_annual_position" and not (
                isinstance(parent, ast.Call) and parent.func is node
            ):
                violations.append("annual producer aliased")
    return violations


def test_hicbc_named_source_exception_rejects_expansion_and_result_exposure():
    path = _root() / "reserved/services/hicbc_annual_source_runtime.py"
    for source in (
        "from reserved.engines.integrated_annual_position import AnnualPositionResult",
        "from reserved.engines.integrated_annual_position import calculate_annual_position as calculate",
        "from reserved.engines import integrated_annual_position as engine",
        "from .hidden import calculate_annual_position",
        "import importlib as loader\nloader.import_module('os')",
        "__import__('os')", "getattr(result, 'total_liability')", "jsonify(result)",
        "result.total_liability", "leak = result.__dict__", "def leak():\n return result",
        "other = calculate_annual_position\nother({})", "def leak():\n ani = result\n return ani",
    ):
        assert _hicbc_boundary_source_violations(path, source), source


def test_hicbc_source_exception_does_not_admit_additional_consumers():
    import_line = "from reserved.services.hicbc_annual_source_runtime import own_ani_from_manual_annual"
    for relative in ("reserved/services/another.py", "reserved/web/another.py",
                     "reserved/api/another.py", "reserved/models/another.py", "reserved/database.py"):
        for source in (import_line, import_line + " as calculate",
                       "loader('reserved.services.hicbc_annual_source_runtime')"):
            assert _hicbc_boundary_source_violations(_root() / relative, source)
    caller = _root() / "reserved/web/hicbc.py"
    valid_caller = import_line + "\ndef annual_preview():\n return own_ani_from_manual_annual(payload, tax_year)\n"
    assert not _hicbc_boundary_source_violations(caller, valid_caller)
    for source in (
        import_line + " as calculate",
        import_line + "\ndef other():\n return own_ani_from_manual_annual(payload, tax_year)",
        import_line + "\ndef annual_preview():\n return own_ani_from_manual_annual(payload, tax_year)\n"
                      "def other():\n return own_ani_from_manual_annual(payload, tax_year)",
    ):
        assert _hicbc_boundary_source_violations(caller, source)
    for extra in (
        "alias = own_ani_from_manual_annual",
        "import reserved.services.hicbc_annual_source_runtime as source",
        "from reserved.services import hicbc_annual_source_runtime as extra\n"
        "def other():\n return extra.own_ani_from_manual_annual(payload, tax_year)",
        "from reserved import services as alternate\n"
        "def other():\n return alternate.hicbc_annual_source_runtime.own_ani_from_manual_annual(payload, tax_year)",
        "from .hicbc_annual_source_runtime import own_ani_from_manual_annual as other",
        "loader('reserved.services.hicbc_annual_source_runtime')",
    ):
        assert _hicbc_boundary_source_violations(caller, valid_caller + extra)


def test_hicbc_source_must_return_the_single_scalar_projection():
    path = _root() / "reserved/services/hicbc_annual_source_runtime.py"
    source = path.read_text()
    assert not _hicbc_boundary_source_violations(path, source)
    mutations = (
        source.replace("result = calculate_annual_position", "ani = calculate_annual_position")
              .replace("ani = result.adjusted_net_income", "result = ani"),
        source.replace("ani = result.adjusted_net_income", "ani = result"),
        source.replace("return ani", "ani = calculate_annual_position(facts, tax_year=tax_year)\n    return ani"),
        source.replace("ani = result.adjusted_net_income", "ani = result.total_liability"),
        "from reserved.engines.integrated_annual_position import calculate_annual_position\n"
        "def own_ani_from_manual_annual(payload, tax_year):\n"
        " ani = calculate_annual_position(payload, tax_year=tax_year)\n return ani\n",
    )
    for mutation in mutations:
        assert mutation != source
        assert _hicbc_boundary_source_violations(path, mutation)


def test_named_presentation_handoff_rejects_forbidden_source_fixtures():
    forbidden_sources = (
        "from reserved.engines.integrated_annual_position import calculate_annual_position",
        "from reserved.engines.cash_ready_annual_position import CashReadyAnnualPosition",
        "from reserved.web.routes import index",
        "from reserved.api.w8_customer_result import get_customer_result",
        "from reserved.models import User",
        "from reserved import database",
        "calculate_annual_position()",
        "funding.unreviewed_engine_call()",
        "poa.assess_payments_on_account()",
        "__import__('reserved.web.routes')",
        "importlib.import_module('reserved.api.w8_customer_result')",
        "import os\nos.system('true')",
        "import requests\nrequests.get('https://example.test')",
        "from .nearby import hidden",
        "import importlib as il\nil.import_module('reserved.web.routes')",
        "loader = __import__\nloader('reserved.web.routes')",
        "getattr(__builtins__, 'open')('/tmp/probe')",
    )
    for source in forbidden_sources:
        assert _annual_cash_handoff_source_violations(source), source


def test_geography_and_jurisdiction_references_are_recorded_honestly():
    # Validate actual public structures, including their limitations. The
    # FreeAgent wire contract recognises country but its public record does not
    # retain it; QuickBooks retains Country, and the canonical business type
    # exposes country_code. None of these facts is an annual-tax admission gate.
    income_tax = (_root() / "reserved" / "engines" / "income_tax.py").read_text()
    optimise = (_root() / "reserved" / "engines" / "optimise.py").read_text()
    routes = (_root() / "reserved" / "web" / "routes.py").read_text()

    assert "Scottish income tax" in income_tax
    assert "Scottish income tax" in optimise
    assert "Scottish Income Tax" in routes
    assert "England, Wales and Northern Ireland" in routes
    freeagent = parse_company(_freeagent_company(country="Scotland"))
    assert isinstance(freeagent, FreeAgentCompanyRecord)
    assert "country" in COMPANY_DOCUMENTED_FIELDS
    assert "country" not in {item.name for item in fields(FreeAgentCompanyRecord)}

    binding = _quickbooks_binding()
    quickbooks = observe_company_info(
        {
            "Id": "company-1",
            "SyncToken": "1",
            "CompanyName": "Synthetic Company",
            "Country": "Scotland",
        },
        binding=binding,
        user_id=binding.user_id,
        realm_id=binding.realm_id,
        credential_reference=binding.credential_reference,
        retrieved_at=RETRIEVED_AT,
    )
    business = AccountingBusiness(
        AccountingProviderName.QUICKBOOKS,
        "realm-1",
        "Synthetic Company",
        "GBP",
        country_code="GB-SCT",
    )
    assert isinstance(quickbooks, CompanyInfoObservation)
    assert quickbooks.country == "Scotland"
    assert business.country_code == "GB-SCT"
    reviewed_fields = {
        item.name
        for contract in (FreeAgentCompanyRecord, CompanyInfoObservation, AccountingBusiness)
        for item in fields(contract)
    }
    assert "territory" not in reviewed_fields


def test_unsupported_scottish_geography_fails_closed_at_annual_entry_point():
    # W8-S3 closes the previously evidenced silent-ignore gap. Each unsupported
    # Scottish geography spelling must now be rejected at the annual-position
    # entry point rather than producing the same actionable result as a facts
    # mapping with no geography evidence.
    facts = {"employment_income": "30000", **BPA}
    baseline = calculate_annual_position(facts)
    assert baseline.calculation_status == "calculated"
    assert baseline.total_liability == Decimal("3486.00")
    for field, value in (
        ("jurisdiction", "Scotland"),
        ("country", "Scotland"),
        ("country_code", "GB-SCT"),
        ("territory", "Scotland"),
        ("tax_regime", "Scottish"),
    ):
        with pytest.raises(ValueError, match="Unsupported geography"):
            calculate_annual_position({**facts, field: value})


# ── 7. W8 completion-map invariants (test-enforced, conservative) ─────────────

def _w8_map_text() -> str:
    return (_root() / "docs" / "W8_COMPLETION_MAP.md").read_text()


def _w8_map_section(heading: str) -> str:
    text = _w8_map_text()
    marker = f"## {heading}"
    start = text.index(marker)
    after = text[start + len(marker):]
    next_heading = after.find("\n## ")
    return after if next_heading == -1 else after[:next_heading]


def test_w8_map_declares_stable_denominator_and_numbered_slices():
    text = _w8_map_text()
    match = re.search(r"denominator\s*=\s*(\d+)", text)
    assert match, "W8 map must declare a numeric delivery denominator"
    denominator = int(match.group(1))

    section = _w8_map_section("W8 delivery slices")
    numbers = [int(n) for n in re.findall(r"^\|\s*(\d+)\s*\|", section, flags=re.MULTILINE)]
    assert numbers, "W8 delivery slices must be a numbered table"
    assert numbers == list(range(1, denominator + 1)), (
        f"numbered slices {numbers} must be exactly 1..{denominator}"
    )


def test_w8_map_each_delivery_slice_has_one_truthful_primary_state():
    section = _w8_map_section("W8 delivery slices")
    rows = [
        tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        for line in section.splitlines()
        if re.match(r"^\|\s*\d+\s*\|", line)
    ]
    assert [int(row[0]) for row in rows] == [1, 2, 3, 4, 5]
    assert all(len(row) == 3 for row in rows)
    states = []
    for row in rows:
        marked = re.findall(r"\*\*(.+?)\*\*", row[2])
        assert len(marked) == 1, f"slice {row[0]} must have one bold primary state"
        states.append(marked[0])
    assert states == [
        "integrated and independently reviewed",
        "partial",
        "integrated and independently reviewed",
        "partial, not integrated as an enabled journey",
        "planned; correctly waiting for completed slices 2 and 4",
    ]


def test_w8_map_separates_achieved_boundaries_from_delivery_slices():
    text = _w8_map_text()
    assert text.index("## Achieved evidence boundaries") < text.index("## W8 delivery slices"), (
        "achieved evidence boundaries must be listed separately, before delivery slices"
    )
    section = _w8_map_section("Achieved evidence boundaries")
    rows = [
        tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        for line in section.splitlines()
        if line.startswith("|") and not line.startswith("|---")
        and not line.startswith("| Evidence boundary")
    ]
    assert all(len(row) == 2 for row in rows)
    states = [row[1] for row in rows]
    assert states == [
        "integrated",
        "integrated sub-boundary; persistence remains open",
        "integrated",
        "synthetic_coexistence_evidence",
        "synthetic_coexistence_evidence",
        "synthetic_coexistence_evidence",
        "component_implemented",
    ]


def test_w8_terminal_gate_is_distinct_from_historical_s2_assurance():
    text = _w8_map_text()
    assert "## Overall W8 terminal completion gate" in text
    assert "## Historical W8-S2 assurance package" in text
    assert "## W8-S2 package acceptance gate" not in text
    terminal = _w8_map_section("Overall W8 terminal completion gate")
    package = _w8_map_section("Historical W8-S2 assurance package")
    assert terminal.strip() != package.strip(), (
        "the W8 terminal gate and historical W8-S2 evidence must be distinct sections"
    )
    assert "do not advance" in package.lower()
    assert "not passed" in terminal.lower()
    for required in (
        "target-runtime", "privacy", "security", "release", "Founder",
        "geography", "provider",
    ):
        assert required.lower() in terminal.lower()
    for required_section in (
        "Dependencies and authority",
        "Sequencing, parallelism and collision rules",
        "Effort and critical path",
        "Immediate next action",
    ):
        assert f"## {required_section}" in text
    for assurance_state in (
        "planned", "implemented", "locally_verified", "independently_reviewed",
        "integrated", "launch_evidence_complete", "launch_ready",
    ):
        assert f"`{assurance_state}`" in text


def test_w8_map_records_post_s3d_sources_without_advancing_primary_states():
    text = _w8_map_text()
    normalised = " ".join(text.split())
    assert "Evidence cut-off: 4 September 2026" in text
    assert "7fcc5be531c5a4331e6a7ff65ce18a33e1772766" in text
    expected_ancestors = (
        "c489c25bab669c64e1c11d28caf29fcde9678fdd",
        "110a90043dfc770c70059482be9d7b7e237749a6",
        "5f5a948891e1e812a5c74ff6c7266d153bb492fa",
        "584ff7f31009913706d3427c38a986bbfa6799d2",
        "5f7b76408a5d72b71be71d0e5d6c7a6edde260b7",
        "b8ce971f4dc6b8a1ced10e9b490be68d481752de",
    )
    for commit in expected_ancestors:
        assert commit in text
        assert subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=_root(),
            check=False,
            capture_output=True,
            text=True,
        ).returncode == 0, f"documented source {commit} must be in current ancestry"

    assert "W9-S3A-D non-durable" in text
    assert "S3D supplies the signed-session runtime owner" in text
    assert (
        "does not authenticate or authorise the separately supplied business reference"
        in normalised
    )
    assert (
        "S6E payment-recovery, S6F cancellation, S6G initial pending/failed and S6H"
        in normalised
    )
    assert (
        "Neither this evidence nor the W9-S3A-D chain advances a W8 delivery-slice "
        "primary state"
        in normalised
    )
    assert "future authenticated runtime-owner adapter" not in text


def test_w8_map_preserves_post_s3d_gates_and_finite_completion_counts():
    text = _w8_map_text()
    for gate in (
        "authenticated owner-to-business membership",
        "physical datastore/schema and migration",
        "atomic durable I/O",
        "lifecycle/legal",
        "encryption/key-custody",
        "target-runtime evidence",
        "provider-custody",
        "authenticated-transport",
        "provider sandbox",
        "Founder authority for merge, release and go-live",
    ):
        assert gate in text

    assert "Progress at the evidence cut-off is **2/5 delivery slices (40%)**" in text
    terminal = _w8_map_section("Overall W8 terminal completion gate")
    terminal_numbers = re.findall(r"(?m)^(\d+)\.", terminal)
    assert terminal_numbers == [str(number) for number in range(1, 11)]
    assert "The terminal gate is **not passed**" in terminal
    for human_gate in (
        "human",
        "customer-language",
        "customer-journey",
        "accessibility",
    ):
        assert human_gate in terminal
    assert "Provider and geography evidence states do not advance" in text


# ── Local helpers (production contracts only) ────────────────────────────────

_ANNUAL_CASH_ALLOWED_IMPORTS = {
    "__future__": {("annotations", None)},
    "dataclasses": {
        ("dataclass", None), ("field", None), ("fields", None),
        ("is_dataclass", None),
    },
    "datetime": {("date", None)},
    "decimal": {("Decimal", None)},
    "enum": {("Enum", None)},
    "reserved.engines": {
        ("cash_funding_position", "funding"),
        ("cash_obligation_reconciliation", "obligations"),
        ("payments_on_account", "poa"),
    },
    "reserved.engines.annual_to_cash_integration": {
        ("CONTRACT_VERSION", "ANNUAL_TO_CASH_VERSION"),
        ("AnnualToCashPosition", None),
        ("AnnualToCashStatus", None),
        ("cash_ready_annual_position_identity", None),
    },
    "reserved.services.w2_customer_language": {
        ("CONTRACT_VERSION", "W2_VERSION"),
        ("AdjustmentFact", None),
        ("AdjustmentKind", None),
        ("EvidenceClassification", None),
        ("FundingClassification", None),
        ("ObligationFact", None),
        ("ObligationKind", None),
        ("PresentationStatus", None),
        ("W2PresentationInput", None),
        ("present_w2_customer_language", None),
    },
}
_ANNUAL_CASH_ALLOWED_DIRECT_IMPORTS = {
    ("hashlib", None), ("hmac", None), ("json", None), ("re", None),
}
_ANNUAL_CASH_ALLOWED_CALL_TARGETS = {
    "AdjustmentFact", "Decimal", "ObligationFact", "TypeError",
    "UnboundAnnualCashPresentation", "ValueError", "W2PresentationInput",
    "_DIGEST_ID.fullmatch", "_IssueToken", "_SOURCE_ID.fullmatch",
    "_canonical", "_digest", "_exact_graph", "_expected_handoff_seal",
    "_handoff_components", "_money", "_recompute_nested",
    "_source_position_identity", "_source_references", "_validate",
    "_validate_exact_presentation_graph", "_validate_handoff_state",
    "active.add", "active.remove", "all", "any",
    "cash_ready_annual_position_identity",
    "compose_w8_annual_cash_customer_handoff", "dataclass", "field", "fields",
    "funding.compose_cash_funding_position", "hasattr", "hash",
    "hashlib.sha256", "hashlib.sha256().hexdigest", "hmac.compare_digest",
    "id", "is_dataclass", "isinstance", "json.dumps",
    "json.dumps().encode", "len", "object.__getattribute__",
    "object.__setattr__", "obligations.reconcile_cash_obligations",
    "present_w2_customer_language", "re.compile", "refs.extend", "set",
    "str", "tuple", "type", "type().__module__.split",
    "validate_w8_annual_cash_customer_handoff", "value.is_finite",
    "value.is_signed", "value.is_zero", "value.isoformat", "value.quantize",
    "value.source_position_identity.startswith", "vars", "visited.add",
}
_ANNUAL_CASH_ALLOWED_ENGINE_CALLS = {
    "funding.compose_cash_funding_position",
    "obligations.reconcile_cash_obligations",
    "cash_ready_annual_position_identity",
}
_ANNUAL_CASH_ALLOWED_ENGINE_ATTRIBUTES = {
    "funding": {
        "CashFundingPosition", "FundingBalance", "FundingComputationStatus",
        "compose_cash_funding_position",
    },
    "obligations": {
        "account", "CashObligationReconciliation", "CashObligationStatus",
        "reconcile_cash_obligations",
    },
    "poa": {"PoAAssessment", "BalancingPosition"},
}
_ANNUAL_CASH_FORBIDDEN_SYMBOLS = {
    "integrated_annual_position", "calculate_annual_position",
    "CashReadyAnnualPosition", "compose_annual_to_cash_position",
}


def _annual_cash_handoff_source_violations(source: str) -> list[str]:
    tree = ast.parse(source)
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                fact = (alias.name, alias.asname)
                if fact not in _ANNUAL_CASH_ALLOWED_DIRECT_IMPORTS:
                    violations.append(f"forbidden absolute import {fact}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            allowed = _ANNUAL_CASH_ALLOWED_IMPORTS.get(module)
            for alias in node.names:
                if (
                    node.level != 0
                    or allowed is None
                    or (alias.name, alias.asname) not in allowed
                ):
                    violations.append(
                        f"forbidden from-import level={node.level} "
                        f"{module}.{alias.name} as {alias.asname}"
                    )
        if isinstance(node, (ast.Name, ast.Attribute)):
            symbol = node.id if isinstance(node, ast.Name) else node.attr
            if symbol in _ANNUAL_CASH_FORBIDDEN_SYMBOLS:
                violations.append(f"forbidden symbol {symbol}")
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            allowed_attributes = _ANNUAL_CASH_ALLOWED_ENGINE_ATTRIBUTES.get(node.value.id)
            if allowed_attributes is not None and node.attr not in allowed_attributes:
                violations.append(
                    f"forbidden engine attribute {node.value.id}.{node.attr}"
                )
        if isinstance(node, ast.Call):
            target = _annual_cash_call_target(node.func)
            if target not in _ANNUAL_CASH_ALLOWED_CALL_TARGETS:
                violations.append(f"forbidden call {target}")
    return violations


def _annual_cash_call_target(value: ast.expr) -> str:
    if isinstance(value, ast.Name):
        return value.id
    if isinstance(value, ast.Attribute):
        return f"{_annual_cash_call_target(value.value)}.{value.attr}"
    if isinstance(value, ast.Call):
        return f"{_annual_cash_call_target(value.func)}()"
    if isinstance(value, ast.Subscript):
        return f"{_annual_cash_call_target(value.value)}[]"
    return type(value).__name__

def _root() -> Path:
    return Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class _W8ImportFact:
    kind: str
    module: str | None
    symbol: str | None = None
    alias: str | None = None
    level: int = 0


def _import_facts_in_file(path: Path) -> tuple[_W8ImportFact, ...]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("path is not a resolved regular file")
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        path.resolve(strict=True).relative_to(_root().resolve(strict=True))
    except (OSError, SyntaxError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"import inspection failed: {exc}") from exc
    facts: list[_W8ImportFact] = []
    import_module_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                facts.append(_W8ImportFact("import", alias.name, alias=alias.asname))
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                facts.append(_W8ImportFact(
                    "from", node.module, alias.name, alias.asname, node.level
                ))
                if node.level == 0 and (
                    (node.module == "importlib" and alias.name == "import_module")
                    or (node.module == "builtins" and alias.name == "__import__")
                ):
                    import_module_names.add(alias.asname or alias.name)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        is_loader = (
            isinstance(value, ast.Name)
            and value.id in ({"__import__"} | import_module_names)
        ) or (
            isinstance(value, ast.Attribute)
            and value.attr in {"import_module", "__import__"}
        ) or (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "getattr"
            and len(value.args) >= 2
            and isinstance(value.args[1], ast.Constant)
            and value.args[1].value in {"import_module", "__import__"}
        )
        if not is_loader:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        import_module_names.update(
            target.id for target in targets if isinstance(target, ast.Name)
        )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        is_dynamic = (
            isinstance(node.func, ast.Name)
            and node.func.id in ({"__import__"} | import_module_names)
        ) or (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in {"import_module", "__import__"}
        ) or (
            isinstance(node.func, ast.Call)
            and isinstance(node.func.func, ast.Name)
            and node.func.func.id == "getattr"
            and len(node.func.args) >= 2
            and isinstance(node.func.args[1], ast.Constant)
            and node.func.args[1].value in {"import_module", "__import__"}
        )
        if is_dynamic:
            target = None
            if node.args and isinstance(node.args[0], ast.Constant) \
                    and isinstance(node.args[0].value, str):
                target = node.args[0].value
            facts.append(_W8ImportFact("dynamic", target))
    return tuple(facts)


def _w8_fact_touches_accounting(fact, protected_symbols):
    module_is_accounting = fact.module == "reserved.providers.accounting" or (
        fact.module is not None
        and fact.module.startswith("reserved.providers.accounting.")
    )
    if fact.kind == "dynamic":
        return fact.module is None or fact.module.startswith(".") or module_is_accounting
    qualified_from_target = (
        f"{fact.module}.{fact.symbol}"
        if fact.kind == "from" and fact.module and fact.symbol
        else None
    )
    qualified_is_accounting = qualified_from_target == "reserved.providers.accounting" or (
        qualified_from_target is not None
        and qualified_from_target.startswith("reserved.providers.accounting.")
    )
    relative_accounting_target = fact.level > 0 and (
        "accounting" in (fact.module or "").split(".")
        or fact.symbol == "accounting"
        or fact.symbol in protected_symbols
    )
    return (
        module_is_accounting
        or qualified_is_accounting
        or relative_accounting_target
        or fact.symbol in protected_symbols
    )


def _freeagent_company(**overrides):
    company = {
        "type": "UkLimitedCompany",
        "currency": "GBP",
        "id": "company-1",
        "name": "Synthetic Company",
        "url": "https://api.freeagent.com/v2/company",
    }
    company.update(overrides)
    return {"company": company}


def _freeagent_invoice_records():
    return parse_invoice_list({
        "invoices": [{
            "url": "https://api.freeagent.com/v2/invoices/1",
            "contact": "https://api.freeagent.com/v2/contacts/2",
            "dated_on": "2026-08-31",
            "due_on": "2026-09-30",
            "payment_terms_in_days": 30,
            "currency": "GBP",
            "status": "Open",
            "reference": "INV-001",
            "net_value": "100.00",
            "sales_tax_value": "20.00",
            "total_value": "120.00",
            "paid_value": "0.00",
            "due_value": "120.00",
        }],
    })


def _xero_mapping(*, tenant_id="tenant-1"):
    line = {
        "LineItemID": "line-1",
        "Description": "Synthetic reviewed work",
        "Quantity": Decimal("2"),
        "UnitAmount": Decimal("50.0000"),
        "AccountCode": "200",
        "TaxType": "OUTPUT",
        "TaxAmount": Decimal("20.00"),
        "LineAmount": Decimal("100.00"),
        "Tracking": [],
    }
    invoice = {
        "InvoiceID": "invoice-1",
        "InvoiceNumber": "INV-001",
        "Type": "ACCREC",
        "Contact": {"ContactID": "contact-1", "Name": "Synthetic Contact"},
        "Date": "2026-08-31",
        "DueDate": "2026-09-30",
        "Status": "AUTHORISED",
        "LineAmountTypes": "Exclusive",
        "LineItems": [line],
        "SubTotal": Decimal("100.00"),
        "TotalTax": Decimal("20.00"),
        "Total": Decimal("120.00"),
        "CurrencyCode": "GBP",
    }
    return map_detailed_invoice_response(
        {"Invoices": [invoice]},
        user_id="user-1",
        connected_organisation_id="connection-1",
        tenant_id=tenant_id,
        import_run_id="run-1",
        retrieved_at=RETRIEVED_AT,
    )


def _quickbooks_binding():
    return RealmBinding("user-1", "realm-1", "opaque-reference-1")


def _quickbooks_invoice_raw():
    return {
        "Id": "invoice-1",
        "SyncToken": "7",
        "CustomerRef": {"value": "customer-1"},
        "TxnDate": "2026-08-10",
        "DueDate": "2026-09-10",
        "CurrencyRef": {"value": "GBP"},
        "GlobalTaxCalculation": "TaxExcluded",
        "Line": [
            {
                "Id": "line-1",
                "DetailType": "SalesItemLineDetail",
                "Amount": Decimal("100.00"),
                "SalesItemLineDetail": {
                    "ItemRef": {"value": "item-1"},
                    "TaxCodeRef": {"value": "TAX"},
                },
            },
            {
                "Id": "subtotal-1",
                "DetailType": "SubTotalLineDetail",
                "Amount": Decimal("100.00"),
                "SubTotalLineDetail": {},
            },
        ],
        "TxnTaxDetail": {
            "TotalTax": Decimal("20.00"),
            "TaxLine": [{
                "Amount": Decimal("20.00"),
                "DetailType": "TaxLineDetail",
                "TaxLineDetail": {
                    "TaxRateRef": {"value": "rate-20"},
                    "PercentBased": True,
                    "TaxPercent": Decimal("20"),
                    "NetAmountTaxable": Decimal("100.00"),
                },
            }],
        },
        "TotalAmt": Decimal("120.00"),
        "Balance": Decimal("120.00"),
        "EmailStatus": "EmailSent",
    }


def _quickbooks_observation():
    binding = _quickbooks_binding()
    return observe_invoice(
        _quickbooks_invoice_raw(),
        binding=binding,
        user_id=binding.user_id,
        realm_id=binding.realm_id,
        credential_reference=binding.credential_reference,
        retrieved_at=RETRIEVED_AT,
    )


def _quickbooks_mapping():
    return adapt_invoice(
        _quickbooks_observation(),
        binding=_quickbooks_binding(),
        import_run_id="run-1",
    )


def _evidence(point=None, low=None, high=None, *, completeness="complete_for_purpose",
              recency="current"):
    common = dict(
        evidence_id="e1", source_kind="manual", source_reference="ref",
        subject_reference="partner", tax_year="2026/27",
        effective_period="2026/27", observed_at="2026-08-17T10:00:00+00:00",
        confirmed_at=None, completeness=completeness, recency_state=recency,
        consent_state="not_required", ani_components=(ANI_COMPONENT_WHOLE,),
    )
    if point is not None:
        return PartnerEvidence(representation="point", point=Decimal(point),
                               low=None, high=None, **common)
    return PartnerEvidence(representation="range", point=None, low=Decimal(low),
                           high=Decimal(high), **common)


def _hicbc_result(user_ani, partner):
    return determine_hicbc_responsibility(
        user_ani=user_ani,
        child_benefit_amount=Decimal("1406.60"),
        has_relevant_partner=True,
        claimant=CLAIMANT_PERSON,
        partner_evidence=partner,
        tax_year="2026/27",
    )
