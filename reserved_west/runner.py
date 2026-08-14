"""
Reserved West — Scenario Runner

Executes each scenario through both the independent reference calculator
and the Reserved engine, records variances, and classifies outcomes.

Outcome codes
-------------
PASS              All monetary variances are exactly £0.00.
PASS_PENNY        Max absolute variance ≤ £0.01 (statutory rounding; documented).
REGRESSION_EL001  Variance detected in a scenario whose income pattern matches the
                  EL-001 regression family.  This is a FAIL — it means the engine has
                  re-introduced the moving Personal Allowance defect that was resolved
                  in v2.0.0.  EL-001 must never be classified as KNOWN_LIMITATION.
FAIL              Variance > £0.01 in a non-EL-001 scenario.
UNSUPPORTED_EXPECTED  Scenario tests a feature explicitly declared out of scope; the
                  unsupported outcome is expected and is not a gate failure.
ERROR             An unexpected exception was raised.

EL-001 permanent regression family
------------------------------------
EL-001 — Moving Personal Allowance / Incremental Income Tax defect

The original defect occurred because the incremental Income Tax calculation
applied the Personal Allowance determined at the end of an income interval
across the entire interval.  This was invalid where the taxpayer's Personal
Allowance changed between the starting and ending tax positions.

The defect affected payments that:
  * entered the Personal Allowance taper (ANI crossing £100,000 from below);
  * remained wholly within the taper (£100,000 < ANI_start < ANI_end ≤ £125,140);
  * crossed the point where the Personal Allowance became zero (ANI crossing £125,140).

Resolved in engine v2.0.0 by computing:
  complete Income Tax liability at the ending tax position
  minus
  complete Income Tax liability at the starting tax position

Each complete tax position independently determines adjusted net income,
Personal Allowance, taxable income and tax-band allocation.

EL-001 is the first example of a broader risk class:
  An incremental calculation must not assume that allowances, reliefs,
  thresholds or tax treatment remain constant between the starting and
  ending tax positions.

Any future failure of the before-and-after liability invariant in the taper zone
is classified REGRESSION_EL001 and is a gate-blocking defect.

Terminology
-----------
Starting tax position:       complete cumulative tax position immediately before the new event.
Ending tax position:         complete cumulative tax position after the new event.
Incremental Income Tax:      IT at ending position minus IT at starting position.
Adjusted net income (ANI):   income after supported qualifying adjustments (e.g. pension).
Personal Allowance taper:    £1 reduction per £2 of ANI above taper threshold.
Moving allowance/threshold:  an allowance whose value differs between start and end positions.
EL-001 regression:           any future failure of the permanent EL-001 tests or the
                             before-and-after liability invariant.

Historic note: engine v1.0.0 classified taper-zone variance as KNOWN_LIMITATION.
This is no longer valid.  KNOWN_LIMITATION has been removed from the outcome set.
"""
from decimal import Decimal
from typing import Any

# Reference calculator (independent)
from reserved_west.reference_calculator import ref_estimate, ref_cgt, in_el001_zone

# Engine under test: the deterministic release artefact built from
# reserved/engines (see scripts/build_engine_artefact.py).  Reserved West must
# not import the mutable working tree directly, nor the historical
# reserved-engine-2.0.0 bundle.  Loading is lazy so that importing this module
# (e.g. to use _classify) does not force an artefact build.
from reserved_west.artefact import load_engine

_ENGINE = None
_PROVENANCE = None


def _engine_symbols():
    """Load the release artefact once and return the imported module."""
    global _ENGINE, _PROVENANCE
    if _ENGINE is None:
        _ENGINE, _PROVENANCE = load_engine()
    return _ENGINE


def engine_provenance() -> dict:
    """Return the provenance of the artefact currently under test."""
    _engine_symbols()
    return dict(_PROVENANCE or {})


PENNY = Decimal("0.01")
ZERO  = Decimal("0")


# ── Outcome classification ────────────────────────────────────────────────────

def _classify(variances: list[Decimal], el001: bool) -> str:
    """Classify the outcome of a scenario.

    REGRESSION_EL001 is returned whenever a variance is detected in the EL-001
    regression family — it is a FAIL, not a known limitation.  The el001
    flag is retained for diagnostic annotation only; it does not soften
    or suppress the failure.
    """
    if not variances:
        return "PASS"
    max_abs = max(abs(v) for v in variances)
    if max_abs == ZERO:
        return "PASS"
    if el001 and max_abs > ZERO:
        # REGRESSION_EL001 is a FAIL — this must be treated as gate-blocking.
        # EL-001 was resolved in v2.0.0.  Any recurrence is a regression defect.
        return "REGRESSION_EL001"
    if max_abs <= PENNY:
        return "PASS_PENNY"
    return "FAIL"


def _d(v: Any) -> Decimal:
    return Decimal(str(v or 0))


# ── Income-tax scenario runner ────────────────────────────────────────────────

def _run_income_tax(scenario: dict) -> dict:
    inputs   = scenario["inputs"]
    invoice  = inputs["invoice_amount"]
    profile  = inputs["profile"]
    tax_year = inputs["tax_year"]

    el001 = in_el001_zone(invoice, profile)

    try:
        ref    = ref_estimate(invoice, profile, tax_year)
        engine = _engine_symbols().estimate_incremental_liability(invoice, profile, tax_year)
    except Exception as exc:
        return {
            **_base(scenario),
            "outcome": "ERROR",
            "error": str(exc),
            "el001_zone": el001,
        }

    fields = ["income_tax", "national_insurance", "student_loan", "total"]
    variances = {}
    for f in fields:
        r = _d(ref.get(f, 0))
        e = _d(engine.get(f, 0))
        variances[f] = e - r   # positive = engine > reference

    total_var = variances["total"]
    outcome   = _classify(list(variances.values()), el001)

    return {
        **_base(scenario),
        "outcome":            outcome,
        "el001_zone":         el001,
        "engine_version":     engine.get("rules_version", "unknown"),
        "reference_version":  ref.get("rules_version", "unknown"),
        "expected": {
            "income_tax":         str(ref["income_tax"]),
            "national_insurance": str(ref["national_insurance"]),
            "student_loan":       str(ref["student_loan"]),
            "total":              str(ref["total"]),
        },
        "actual": {
            "income_tax":         str(engine["income_tax"]),
            "national_insurance": str(engine["national_insurance"]),
            "student_loan":       str(engine["student_loan"]),
            "total":              str(engine["total"]),
        },
        "variances": {k: str(v) for k, v in variances.items()},
        "primary_variance": str(total_var),
    }


# ── CGT scenario runner ───────────────────────────────────────────────────────

def _run_cgt(scenario: dict) -> dict:
    inputs = scenario["inputs"]
    tax_year  = inputs["tax_year"]
    raw_disps = inputs["disposals"]
    tib_gains = inputs["taxable_income_before_gains"]
    bf_losses = inputs.get("brought_forward_losses", 0)
    paid      = inputs.get("tax_already_paid", 0)

    # Build engine CapitalDisposal objects
    try:
        engine_mod    = _engine_symbols()
        CapitalDisposal = engine_mod.CapitalDisposal
        estimate_cgt    = engine_mod.estimate_cgt
        engine_disposals = [
            CapitalDisposal(
                asset_type       = d.get("asset_type", "shares"),
                description      = d.get("description", "disposal"),
                disposal_date    = d.get("disposal_date", "2026-01-01"),
                proceeds         = _d(d["proceeds"]),
                allowable_cost   = _d(d["allowable_cost"]),
            )
            for d in raw_disps
        ]
        # Reference disposals (dicts with gain_or_loss)
        ref_disposals = [
            {
                "proceeds":      _d(d["proceeds"]),
                "allowable_cost": _d(d["allowable_cost"]),
                "gain_or_loss":  _d(d.get("gain_or_loss",
                                          _d(d["proceeds"]) - _d(d["allowable_cost"]))),
            }
            for d in raw_disps
        ]

        ref_result    = ref_cgt(
            ref_disposals,
            taxable_income_before_gains = tib_gains,
            brought_forward_losses      = bf_losses,
            tax_already_paid            = paid,
            tax_year                    = tax_year,
        )
        engine_result = estimate_cgt(
            engine_disposals,
            taxable_income_before_gains = _d(tib_gains),
            brought_forward_losses      = _d(bf_losses),
            tax_already_paid            = _d(paid),
            tax_year                    = tax_year,
        )
    except Exception as exc:
        return {
            **_base(scenario),
            "outcome": "ERROR",
            "error": str(exc),
            "el001_zone": False,
        }

    cgt_fields = ["taxable_gains", "estimated_cgt", "outstanding_reserve"]
    variances  = {}
    for f in cgt_fields:
        r = _d(ref_result.get(f, 0))
        e = _d(engine_result.get(f, 0))
        variances[f] = e - r

    primary_var = variances["estimated_cgt"]
    outcome     = _classify(list(variances.values()), False)

    return {
        **_base(scenario),
        "outcome":           outcome,
        "el001_zone":        False,
        "engine_version":    engine_result.get("rules_version", "unknown"),
        "reference_version": ref_result.get("rules_version", "unknown"),
        "expected": {
            "taxable_gains":    str(ref_result["taxable_gains"]),
            "estimated_cgt":    str(ref_result["estimated_cgt"]),
            "outstanding_reserve": str(ref_result["outstanding_reserve"]),
        },
        "actual": {
            "taxable_gains":    str(engine_result["taxable_gains"]),
            "estimated_cgt":    str(engine_result["estimated_cgt"]),
            "outstanding_reserve": str(engine_result["outstanding_reserve"]),
        },
        "variances": {k: str(v) for k, v in variances.items()},
        "primary_variance": str(primary_var),
    }


# ── Dispatch ──────────────────────────────────────────────────────────────────

def _base(scenario: dict) -> dict:
    return {
        "scenario_id":   scenario["scenario_id"],
        "title":         scenario["title"],
        "groups":        scenario["groups"],
        "envelope":      scenario["envelope"],
        "scenario_type": scenario["scenario_type"],
        "description":   scenario["description"],
        "tax_year":      scenario["inputs"].get("tax_year", ""),
    }


def run_scenario(scenario: dict) -> dict:
    """Execute a single scenario and return a result dict."""
    # Scenarios explicitly declared as out-of-scope produce UNSUPPORTED_EXPECTED.
    if scenario.get("envelope") == "out_of_scope" or \
       scenario.get("expected_outcome") == "unsupported":
        return {
            **_base(scenario),
            "outcome": "UNSUPPORTED_EXPECTED",
            "error": scenario.get("notes", "Feature outside engine scope; unsupported outcome expected"),
            "el001_zone": False,
        }

    stype = scenario.get("scenario_type", "income_tax")
    if stype == "income_tax":
        return _run_income_tax(scenario)
    elif stype == "cgt":
        return _run_cgt(scenario)
    else:
        return {
            **_base(scenario),
            "outcome": "UNSUPPORTED_EXPECTED",
            "error": f"Scenario type {stype!r} is outside engine scope",
            "el001_zone": False,
        }


def run_all(scenarios: list[dict]) -> list[dict]:
    """Run all scenarios and return a list of result dicts."""
    return [run_scenario(s) for s in scenarios]
