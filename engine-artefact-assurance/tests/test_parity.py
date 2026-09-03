"""
Production ↔ artefact parity gate.

Detects semantic drift between the maintained production engine
(``reserved.engines``) and the generated release artefact (``reserved_engine``
built from it).  Packaging parity is *not* independent tax validation: it
guards against the artefact silently diverging from production (e.g. a stale
build or an in-place edit), which is what let the historical bundle drift on
Student Loan behaviour.

The gate compares material public behaviour and version/configuration
identity without coupling to private implementation layout.
"""
from datetime import date, datetime, timezone
from decimal import Decimal as D

import pytest

from reserved import engines as prod
from reserved_engine import (
    estimate_incremental_liability as art_estimate,
    build_allocation as art_allocate,
    estimate_cgt as art_cgt,
    CapitalDisposal as ArtDisposal,
)

P_ESTIMATE = prod.estimate_incremental_liability
P_ALLOCATE = prod.build_allocation
P_CGT = prod.estimate_cgt
P_DISPOSAL = prod.CapitalDisposal


def _normalise(value):
    """Convert Decimals/dataclasses/dicts to plain comparable structures."""
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {k: _normalise(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalise(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        from dataclasses import asdict
        return _normalise(asdict(value))
    return value


def _call(fn, *args, **kwargs):
    """Return a canonical triple describing either the result or the exception."""
    try:
        return ("ok", _normalise(fn(*args, **kwargs)))
    except Exception as exc:  # noqa: BLE001 — we are intentionally comparing behaviour
        return ("raise", type(exc).__name__, str(exc))


def _profile(**overrides):
    base = {
        "day_job_salary": "0",
        "ytd_freelance_profit": "0",
        "personal_pension_contributions": "0",
    }
    base.update(overrides)
    return base


# ── Version / configuration identity ─────────────────────────────────────────

def test_engine_version_identity():
    assert prod.ENGINE_VERSION == "4.0.0"
    assert prod.ENGINE_VERSION == __import__("reserved_engine").ENGINE_VERSION


def test_rules_version_identity():
    from reserved.engines.tax_config import RULES_VERSION as prod_rules
    from reserved_engine.tax_config import RULES_VERSION as art_rules
    assert prod_rules == art_rules


def test_income_tax_config_identity():
    from reserved.engines.tax_config import get_config as prod_cfg
    from reserved_engine.tax_config import get_config as art_cfg
    for year in ("2025/26", "2026/27"):
        assert prod_cfg(year) == art_cfg(year)


def test_supported_years_identity():
    from reserved.engines.tax_config import SUPPORTED_TAX_YEARS as prod_years
    from reserved_engine.tax_config import SUPPORTED_TAX_YEARS as art_years
    assert prod_years == art_years


# ── Incremental liability parity (IT / NI / Student Loan) ────────────────────

@pytest.mark.parametrize("invoice,tax_year,plans", [
    ("5000", "2026/27", None),
    ("5000", "2025/26", None),
    ("100", "2026/27", None),
    ("150000", "2026/27", None),
    ("29386", "2026/27", [2]),       # SL whole-pound floor → £0.00
    ("29397", "2026/27", [2]),       # SL whole-pound floor → £1.00
    ("26912", "2026/27", [1]),       # Plan 1 floor → £1.00
    ("5000", "2026/27", ["postgraduate"]),
    ("40000", "2026/27", [2, "postgraduate"]),  # single undergrad + PGL supported
])
def test_incremental_liability_parity(invoice, tax_year, plans):
    profile = _profile(student_loan_plans=plans) if plans else _profile()
    assert _call(P_ESTIMATE, invoice, profile, tax_year) == \
           _call(art_estimate, invoice, profile, tax_year)


@pytest.mark.parametrize("plans", [
    [1, 2],                    # simultaneous undergraduate plans
    ["mystery"],               # unknown plan identifier
    [1, "postgraduate", 2],    # multiple undergraduate plans + PGL
])
def test_student_loan_unsupported_states_fail_closed_identically(plans):
    profile = _profile(student_loan_plans=plans)
    prod_out = _call(P_ESTIMATE, "40000", profile, "2026/27")
    art_out = _call(art_estimate, "40000", profile, "2026/27")
    assert prod_out[0] == "raise", f"production did not fail closed for {plans}"
    assert prod_out == art_out


# ── Allocation parity ─────────────────────────────────────────────────────────

def test_allocation_parity():
    liability = {"income_tax": D("2000.00"), "national_insurance": D("600.00"),
                 "student_loan": D("0.00"), "total": D("2600.00")}
    assert _call(P_ALLOCATE, "10000.00", liability) == \
           _call(art_allocate, "10000.00", liability)


# ── Capital Gains parity ──────────────────────────────────────────────────────

def test_cgt_parity():
    def _run(disposal_cls, cgt_fn):
        disposals = [disposal_cls(
            asset_type="shares", description="x", disposal_date="2026-01-01",
            proceeds=D("20000"), allowable_cost=D("5000"),
        )]
        return cgt_fn(disposals, taxable_income_before_gains=D("30000"),
                      tax_year="2026/27")

    assert _call(lambda *a: _run(P_DISPOSAL, P_CGT)) == \
           _call(lambda *a: _run(ArtDisposal, art_cgt))


# ── Optimise parity ───────────────────────────────────────────────────────────

def test_optimise_parity():
    from reserved.engines.optimise import calculate_position as prod_pos
    from reserved_engine.optimise import calculate_position as art_pos
    for income, pension in [(D("110000"), D("0")), (D("70000"), D("0")),
                            (D("200000"), D("80000"))]:
        assert _call(prod_pos, income, pension) == _call(art_pos, income, pension)


# ── W8-S1 accounting-to-tax handoff parity ────────────────────────────────────

_HANDOFF_RETRIEVED_AT = datetime(2026, 8, 3, 10, 0, 0, tzinfo=timezone.utc)


def _handoff_bundle(c):
    """Build an identical synthetic accounting bundle from a contracts module."""
    def _identity(**overrides):
        kwargs = dict(user_id="user-1", provider=c.AccountingProviderName.XERO,
                      connected_organisation_id="org-1", business_id="business-1",
                      import_run_id="run-1")
        kwargs.update(overrides)
        return c.SourceIdentity(kwargs["user_id"], kwargs["provider"],
                                kwargs["connected_organisation_id"],
                                kwargs["business_id"], kwargs["import_run_id"])

    def _provenance(record_id, **identity_kwargs):
        return c.Provenance(
            identity=_identity(**identity_kwargs),
            api_name="synthetic",
            api_version="v1",
            resource="invoices",
            record_id=record_id,
            source_fields=("provider_document_id",),
            retrieved_at=_HANDOFF_RETRIEVED_AT,
            adapter_version="syn-1",
            source_record_digest="digest",
        )

    def _observation(observation_id):
        return c.SourceObservation(
            observation_id=observation_id,
            provenance=_provenance(record_id=observation_id),
            evidence_state=c.EvidenceState.SELECTED,
        )

    def _tax_input(input_id, economic_event_id, classification, amount,
                   evidence_observation_ids, allowability=None,
                   allowability_decision_id=None):
        return c.CanonicalAccountingTaxInput(
            input_id=input_id,
            purpose="income",
            scope="self-assessment",
            business_id="business-1",
            economic_event_id=economic_event_id,
            tax_year="2026/27",
            recognised_amount=D(amount),
            recognised_date=date(2026, 8, 10),
            classification=classification,
            currency="GBP",
            base_currency="GBP",
            evidence_observation_ids=evidence_observation_ids,
            recognition_decision_id="recognition-1",
            allowability_decision_id=allowability_decision_id,
            policy_version="v1",
            allowability=allowability,
            permitted_uses=("tax_estimate",),
            prohibited_uses=("settlement", "write_back"),
        )

    o1 = _observation("o1")
    o2 = _observation("o2")
    allow = c.AllowabilityDecision(
        "a1", c.AllowabilityOutcome.ALLOWABLE,
        c.DecisionAuthority.RESERVED_RULE, _HANDOFF_RETRIEVED_AT,
        "business expense", allowable_fraction=None, source_observation_ids=("o2",),
    )
    i1 = _tax_input("i1", "e1", "turnover", "10000", ("o1",))
    i2 = _tax_input("i2", "e2", "expense", "2000", ("o2",),
                    allowability=allow, allowability_decision_id="a1")
    return [i1, i2], [o1, o2]


@pytest.mark.parametrize("business_type_attr", [
    "TRADE", "UK_PROPERTY", "FOREIGN_PROPERTY",
])
def test_accounting_tax_handoff_parity(business_type_attr):
    from reserved.engines.accounting_tax_handoff import (
        calculate_annual_position_from_accounting as prod_handoff,
    )
    from reserved_engine.accounting_tax_handoff import (
        calculate_annual_position_from_accounting as art_handoff,
    )
    import reserved.providers.accounting.contracts as prod_contracts
    import reserved_engine.accounting_contracts as art_contracts

    prod_inputs, prod_obs = _handoff_bundle(prod_contracts)
    art_inputs, art_obs = _handoff_bundle(art_contracts)
    prod_business = getattr(prod_contracts.BusinessType, business_type_attr)
    art_business = getattr(art_contracts.BusinessType, business_type_attr)

    prod_out = _call(prod_handoff, tax_year="2026/27", business_type=prod_business,
                     inputs=prod_inputs, observations=prod_obs)
    art_out = _call(art_handoff, tax_year="2026/27", business_type=art_business,
                    inputs=art_inputs, observations=art_obs)
    assert prod_out[0] == "ok", f"production failed for {business_type_attr}: {prod_out}"
    assert prod_out == art_out


def test_accounting_tax_handoff_unsupported_business_type_fails_closed_identically():
    from reserved.engines.accounting_tax_handoff import (
        calculate_annual_position_from_accounting as prod_handoff,
    )
    from reserved_engine.accounting_tax_handoff import (
        calculate_annual_position_from_accounting as art_handoff,
    )
    import reserved.providers.accounting.contracts as prod_contracts
    import reserved_engine.accounting_contracts as art_contracts

    prod_inputs, prod_obs = _handoff_bundle(prod_contracts)
    art_inputs, art_obs = _handoff_bundle(art_contracts)

    prod_out = _call(prod_handoff, tax_year="2026/27",
                     business_type=prod_contracts.BusinessType.UNSUPPORTED,
                     inputs=prod_inputs, observations=prod_obs)
    art_out = _call(art_handoff, tax_year="2026/27",
                    business_type=art_contracts.BusinessType.UNSUPPORTED,
                    inputs=art_inputs, observations=art_obs)
    assert prod_out[0] == "raise", f"production did not fail closed: {prod_out}"
    assert prod_out == art_out
