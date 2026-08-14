"""
Reserved West — engine-artefact adapter registry for RW3 literal fixtures.

These adapters are the *only* place where immutable fixture inputs meet the
engine.  They translate fixture inputs into engine-artefact calls and return
the engine's actual outputs verbatim.  They must never calculate, derive,
mutate or otherwise influence expected values.

Fail-closed contract
--------------------
Missing adapters and unsupported fixture types fail closed: the engine's
unsupported-state refusal is surfaced to the runner (which records ERROR)
rather than being converted into a partial or invented monetary figure.

The engine under test is the deterministic release artefact produced by
``scripts/build_engine_artefact.py`` (see ``reserved_west.artefact``).
"""
from __future__ import annotations

from decimal import Decimal as D

from .artefact import load_engine
from .literal_fixture_runner import load_corpus, run_pack

TAX_YEAR = "2026/27"


def _annual_income_tax(engine, inputs: dict) -> dict:
    """Translate ``annual_income_tax`` fixture inputs to engine outputs.

    Maps ``{income, gross_ras_pension}`` to the full-position income tax
    surface: adjusted net income, tapered Personal Allowance and total
    income tax at that position.
    """
    income = D(str(inputs["income"]))
    pension = D(str(inputs.get("gross_ras_pension", "0")))
    cfg = engine.tax_config.get_config(TAX_YEAR)
    adjusted_net_income = max(D("0"), income - pension)
    return {
        "adjusted_net_income": adjusted_net_income,
        "personal_allowance": engine.income_tax._personal_allowance(adjusted_net_income, cfg),
        "income_tax": engine.income_tax._total_income_tax(income, pension, cfg),
    }


def _incremental_liability(engine, inputs: dict) -> dict:
    """Translate ``incremental_liability`` fixture inputs to engine outputs."""
    return engine.estimate_incremental_liability(
        inputs["invoice_amount"],
        inputs["profile"],
        inputs.get("tax_year", TAX_YEAR),
    )


def build_adapters() -> tuple[dict, dict]:
    """Return ``(adapters, provenance)`` for the current release artefact."""
    engine, provenance = load_engine()
    adapters = {
        "annual_income_tax": lambda inputs: _annual_income_tax(engine, inputs),
        "incremental_liability": lambda inputs: _incremental_liability(engine, inputs),
    }
    return adapters, provenance


def run_engine_evidence(corpus_path) -> dict:
    """Run an RW3 corpus against the current engine artefact.

    Returns the engine provenance alongside the per-pack comparison results so
    the evidence records exactly which artefact produced the actual values.
    """
    adapters, provenance = build_adapters()
    corpus, packs = load_corpus(corpus_path)
    return {
        "engine_provenance": provenance,
        "corpus_id": corpus["corpus_id"],
        "pack_results": [run_pack(pack, adapters) for pack in packs],
    }
