# Reserved Engine Architecture

*Reserved West Initiative 001 — internal architecture document.*
*Classification: internal. Not for public distribution.*

---

## Overview

Reserved's tax calculations are implemented in a self-contained engine package
(`reserved/engines/`) with no dependency on Flask, the web session, the
database, or any network service. The engine is deterministic: given the same
inputs it always produces the same outputs.

This document describes the planned three-component architecture that separates
calculation logic, the web application that uses it, and the independent
assurance harness that verifies it.

---

## The three components

```
┌─────────────────────────────────────────────────────────┐
│                   Reserved Engine                       │
│           reserved/engines/  (ENGINE_VERSION)           │
│                                                         │
│  Single source of calculation logic. Pure Python,       │
│  stdlib only, no web or database dependencies.          │
│  Versioned with semantic versioning.                    │
└────────────────┬──────────────────────┬─────────────────┘
                 │  pinned at version X  │  pinned at version X
                 ▼                       ▼
┌───────────────────────┐   ┌────────────────────────────┐
│       Reserved        │   │     Reserved West          │
│   (web application)   │   │  (assurance harness)       │
│                       │   │                            │
│ Flask web app.        │   │ Independent test project.  │
│ Imports the engine    │   │ Imports the same pinned    │
│ at a declared pin.    │   │ engine version as Reserved.│
│ Serves users.         │   │ Runs scenario library.     │
└───────────────────────┘   └────────────────────────────┘
```

### Reserved Engine

**Current location:** `reserved/engines/`
**Current status:** In-repo, imported directly. Extraction to a standalone
package is the goal of Initiative 001.

**Responsibilities:**
- All UK tax liability estimates (Income Tax, Class 4 NI, Student Loan,
  Capital Gains Tax)
- Gross-to-safe-to-spend allocation
- Multi-year rate configuration (2025/26, 2026/27)
- Rounding policy (ROUND_HALF_UP to the nearest penny)

**Does not:**
- Read from or write to any database
- Access the web session or Flask request context
- Make any network calls
- Read environment variables

### Reserved (web application)

**Current status:** Imports engine modules directly (monorepo).
**Future status:** Declares engine as a pinned package dependency.

Reserved is a consumer of the engine. It passes user-supplied profile data and
invoice amounts to the engine and presents the results. It does not contain any
tax calculation logic of its own.

### Reserved West (assurance harness)

**Current status:** Not yet built.
**Planned:** Separate Replit project.

Reserved West imports the engine at the same pin as the current Reserved
production release. It maintains:

- **Scenario library** — structured input sets covering typical, boundary, and
  unusual tax situations
- **Evidence store** — frozen expected outputs for each scenario, locked to a
  specific engine version
- **Test harness** — runs every scenario through the imported engine and
  compares against the evidence store
- **Report generator** — produces human-readable assurance reports documenting
  coverage and any deviations

When the engine version is bumped, Reserved West must explicitly update its
pin, re-run the scenario library, review any changed outputs against the
evidence store, update the store where the change is intentional, and produce
an updated assurance report before Reserved ships.

---

## Engine public API

All symbols are importable from `reserved.engines` directly.

### Income Tax, Class 4 NI, Student Loan

```python
from reserved.engines import estimate_incremental_liability

result = estimate_incremental_liability(
    invoice_amount,   # Decimal-coercible; gross invoice value
    profile,          # dict — see inputs table below
    tax_year,         # str; default "2026/27"
)
```

**Profile inputs:**

| Key | Type | Description |
|---|---|---|
| `day_job_salary` | Decimal-coercible | Annual PAYE employment income received this tax year |
| `ytd_freelance_profit` | Decimal-coercible | Sole-trader profit before this invoice |
| `personal_pension_contributions` | Decimal-coercible | Gross Relief-at-Source pension contributions |
| `student_loan_plans` | list | Active plan identifiers, e.g. `[2]` or `[1, "postgraduate"]` |

**Outputs (all Decimal, rounded to the nearest penny):**

| Key | Description |
|---|---|
| `income_tax` | Marginal Income Tax liability for this invoice |
| `national_insurance` | Marginal Class 4 NI liability |
| `student_loan` | Total student/postgraduate loan repayment |
| `total` | Sum of the above three |
| `tax_year` | Confirmed tax year used |
| `rules_version` | Identifier of the rate set used |
| `assumptions` | List of human-readable methodology notes |

### Capital Gains Tax

```python
from reserved.engines import CapitalDisposal, estimate_cgt

result = estimate_cgt(
    disposals,                    # Iterable[CapitalDisposal]
    taxable_income_before_gains=, # Decimal-coercible
    brought_forward_losses=0,     # Decimal-coercible; optional
    tax_already_paid=0,           # Decimal-coercible; optional
    tax_year="2026/27",           # str; optional
)
```

**Outputs (all Decimal):** `taxable_gains`, `estimated_cgt`,
`outstanding_reserve`, `annual_exempt_amount`, `total_gains`,
`current_year_losses`, `losses_used`, `tax_already_paid`, `tax_year`,
`rules_version`, `disposals` (list), `warnings` (list of strings).

### Allocation

```python
from reserved.engines import build_allocation

result = build_allocation(
    gross_amount,        # Decimal-coercible
    estimated_liability, # Decimal-coercible
    fee_rate="0.00",     # str; default zero (preview mode)
)
```

**Outputs:** `gross_amount`, `tax_reserve`, `platform_fee`, `safe_to_spend`
(all Decimal), `reconciles` (bool — always True when gross ≥ liability + fee).

### Configuration

```python
from reserved.engines import (
    get_income_tax_config,    # get_income_tax_config(tax_year) -> dict
    get_cgt_config,           # get_cgt_config(tax_year) -> dict
    SUPPORTED_TAX_YEARS,      # ["2025/26", "2026/27"]
    SUPPORTED_CGT_TAX_YEARS,  # ["2025/26", "2026/27"]
    ENGINE_VERSION,           # e.g. "1.0.0"
)
```

---

## Versioning and the pin contract

The engine uses semantic versioning exposed as `ENGINE_VERSION`.

| Bump | Meaning | Reserved action | Reserved West action |
|---|---|---|---|
| Patch (x.y.**Z**) | Docs / refactor / no numeric change | Update pin at next release | Re-run scenarios; confirm identical outputs |
| Minor (x.**Y**.0) | New optional param / new tax year | Update pin; test new feature | Extend scenario library; confirm existing outputs unchanged |
| Major (**X**.0.0) | Breaking change / numeric correction | Must review all outputs | Must re-baseline evidence store and produce new assurance report |

---

## Migration path (in-repo → standalone package)

Initiative 001 prepares the engine for extraction without performing it.
The extraction sequence when the time comes is:

1. Create a new `reserved-engine` repository.
2. Copy `reserved/engines/` verbatim — the directory is already clean.
3. Add `pyproject.toml` declaring zero runtime dependencies.
4. Move the `@pytest.mark.engine` tests into the new repo's `tests/`.
5. Tag `v1.0.0` and publish (privately or via git URL).
6. In Reserved, replace the local import path with:
   ```
   reserved-engine @ git+https://github.com/…/reserved-engine@v1.0.0
   ```
7. Create Reserved West as a new Replit project with the same pin.

Steps 1–5 can happen without touching any Reserved application code.
Steps 6–7 are a single coordinated deployment.

---

## Known methodology limitations

| ID | Description | Documented in |
|---|---|---|
| EL-001 | PA taper computed from end-state ANI; diverges when invoice crosses £100,000 ANI boundary | `docs/ASSUMPTIONS_AND_LIMITATIONS_REGISTER.md` |
| EL-002 | CGT BASIC_RATE_LIMIT was module-level; **resolved in ENGINE_VERSION 1.0.0** | `reserved/engines/CHANGELOG.md` |

---

*"We believe trust should be earned, not assumed. Every release of Reserved is
tested across thousands of realistic and unusual tax scenarios. Our goal isn't
simply to confirm that Reserved works. It's to continually challenge it, learn
from what we find, and improve it with every release."*
