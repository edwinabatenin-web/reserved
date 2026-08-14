"""
Reserved tax engine — stable public API.

Import from this package rather than from individual submodules to obtain a
stable, versioned surface that Reserved and future consumers (including
Reserved West) can depend on without coupling to internal module layout.

Version contract
----------------
``ENGINE_VERSION`` follows semantic versioning:
  - Patch bump  (x.y.Z): documentation, comments, internal refactor — no
    change to inputs, outputs, or calculation results.
  - Minor bump  (x.Y.0): additive change — new optional parameter, new
    supported tax year, or new output key.  Existing callers unaffected.
  - Major bump  (X.0.0): breaking change — removed parameter, changed
    output shape, or corrected calculation producing different numeric
    results.  Callers must review and re-pin.

See ``reserved/engines/CHANGELOG.md`` for the full history.
"""

ENGINE_VERSION: str = "3.0.0"

# ── Public calculation functions ──────────────────────────────────────────────

from .income_tax import estimate_incremental_liability
from .capital_gains import CapitalDisposal, estimate_cgt
from .allocation import build_allocation
from .optimise import (
    assess_opportunities,
    calculate_position,
    model_pension_scenario,
    Position,
    ScenarioResult,
    Opportunity,
)

# ── Configuration access ──────────────────────────────────────────────────────

from .tax_config import (
    get_config as get_income_tax_config,
    SUPPORTED_TAX_YEARS,
)
from .capital_gains_config import (
    get_cgt_config,
    SUPPORTED_CGT_TAX_YEARS,
)

# ── Arithmetic primitive ──────────────────────────────────────────────────────

from .utils import money, PENNY

# ── Explicit public surface ───────────────────────────────────────────────────

__all__ = [
    # Version
    "ENGINE_VERSION",
    # Income Tax, NI, Student Loan
    "estimate_incremental_liability",
    # Capital Gains Tax
    "CapitalDisposal",
    "estimate_cgt",
    # Allocation
    "build_allocation",
    # Configuration helpers
    "get_income_tax_config",
    "get_cgt_config",
    "SUPPORTED_TAX_YEARS",
    "SUPPORTED_CGT_TAX_YEARS",
    # Arithmetic
    "money",
    "PENNY",
]
