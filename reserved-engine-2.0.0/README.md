# Reserved Engine — v2.0.0

Standalone UK tax computation package extracted from the Reserved web application.

Zero runtime dependencies. Pure Python stdlib (decimal, dataclasses, typing). Requires Python ≥ 3.11.

---

## What's new in v2.0.0

**EL-001 resolved** — Personal Allowance taper handling corrected.

The income-tax component now computes the true before/after differential:

```
income_tax = total_income_tax(end_position) − total_income_tax(start_position)
```

Each call independently determines the Personal Allowance at its own income level.
Results are numerically unchanged for users with income firmly below £100,000 or
above £125,140.  Users with income near the PA taper zone receive the correct
(higher) estimate.  See `reserved_engine/CHANGELOG.md` for full details.

---

## What this package contains

| Path | Description |
|---|---|
| `reserved_engine/` | The complete engine package |
| `reserved_engine/__init__.py` | Public API surface (`ENGINE_VERSION`, all symbols) |
| `reserved_engine/income_tax.py` | Marginal Income Tax, Class 4 NI, Student Loan estimator |
| `reserved_engine/capital_gains.py` | CGT estimator across multiple disposals |
| `reserved_engine/allocation.py` | Gross-to-safe-to-spend bucket split |
| `reserved_engine/tax_config.py` | IT/NI/SL configuration registry (2025/26, 2026/27) |
| `reserved_engine/capital_gains_config.py` | CGT configuration registry (2025/26, 2026/27) |
| `reserved_engine/utils.py` | `money()` — ROUND_HALF_UP penny quantizer |
| `reserved_engine/CHANGELOG.md` | Version history |
| `tests/` | 152 engine-only tests (verbatim from Reserved, imports updated) |
| `docs/ENGINE_ARCHITECTURE.md` | Three-component architecture; versioning contract |
| `docs/ASSUMPTIONS_AND_LIMITATIONS_REGISTER.md` | Defect register, resolved EL-001, sign-off checklist |
| `MANIFEST.json` | SHA-256 source hashes + golden expected outputs for parity verification |
| `pyproject.toml` | Standalone package metadata |

---

## Parity guarantee

The source files in `reserved_engine/` are **byte-for-byte identical** to the originals in
`reserved/engines/` of the Reserved project (verified via SHA-256 — see `MANIFEST.json`).

The only differences in this bundle are:

1. **`reserved_engine/__init__.py`** — docstring updated to reflect standalone context;
   all `from .` relative imports are identical.
2. **`tests/test_*.py`** — import paths changed from `reserved.engines.*` to
   `reserved_engine.*`. All test logic, assertions, and golden values are unchanged.

---

## Installation

```bash
# Option A — install directly from the uploaded directory
pip install -e /path/to/reserved-engine-2.0.0

# Option B — install from git URL (after pushing to a repo)
pip install git+https://github.com/…/reserved-engine@v2.0.0

# Option C — copy reserved_engine/ into your project and add to sys.path
```

### Verify parity before use

```bash
python - <<'EOF'
import hashlib, json, pathlib

manifest = json.loads(pathlib.Path("MANIFEST.json").read_text())
for entry in manifest["source_files"]:
    if "sha256" not in entry:
        continue
    actual = hashlib.sha256(pathlib.Path(entry["bundle_path"]).read_bytes()).hexdigest()
    if actual != entry["sha256"]:
        print(f"MISMATCH: {entry['bundle_path']}")
        print(f"  expected: {entry['sha256']}")
        print(f"  actual:   {actual}")
    else:
        print(f"OK: {entry['bundle_path']}")
EOF
```

---

## Running the tests

```bash
# Install dev dependencies
pip install pytest

# Run all 152 engine tests
pytest

# Run with verbose output
pytest -v
```

Expected: **152 passed** in < 1 second.

---

## Quick-start usage

```python
from reserved_engine import (
    estimate_incremental_liability,   # Income Tax + NI + Student Loan
    estimate_cgt, CapitalDisposal,    # Capital Gains Tax
    build_allocation,                 # Gross-to-safe-to-spend split
    ENGINE_VERSION,
    SUPPORTED_TAX_YEARS,
)

# Income Tax, Class 4 NI, Student Loan — marginal cost of a single invoice
result = estimate_incremental_liability(
    invoice_amount="10000",
    profile={
        "day_job_salary": "40000",
        "ytd_freelance_profit": "15000",
        "personal_pension_contributions": "5000",   # gross, Relief at Source
        "student_loan_plans": [2],
    },
    tax_year="2026/27",   # or "2025/26"
)
# result["total"] → Decimal("5446.00")

# Allocation
allocation = build_allocation(gross_amount="10000", estimated_liability=result["total"])
# allocation["safe_to_spend"] → Decimal("4554.00")

# Capital Gains Tax
cgt = estimate_cgt(
    disposals=[
        CapitalDisposal(
            asset_type="shares",
            description="ABC Ltd shares",
            disposal_date="2026-09-01",
            proceeds=Decimal("18000"),
            allowable_cost=Decimal("3000"),
        )
    ],
    taxable_income_before_gains=46000,
    tax_year="2026/27",
)
# cgt["estimated_cgt"] → Decimal("2623.80")
```

---

## Engine version contract

`ENGINE_VERSION` follows semantic versioning:

| Bump | Meaning |
|---|---|
| Patch (x.y.**Z**) | Docs / refactor — no numeric change |
| Minor (x.**Y**.0) | New optional param / new tax year |
| Major (**X**.0.0) | Breaking change or numeric correction |

Any change that produces different outputs is a **major bump**.

See `docs/ENGINE_ARCHITECTURE.md` for the full versioning and Reserved West pin contract.

---

## Defect history

| ID | Description | Status |
|---|---|---|
| EL-001 | Moving PA taper — engine applied end-state PA across full invoice range | ✅ Resolved in v2.0.0 |
| EL-002 | CGT BASIC_RATE_LIMIT from module-level constant instead of versioned config | ✅ Resolved in v1.0.0 |

Full details in `docs/ASSUMPTIONS_AND_LIMITATIONS_REGISTER.md`.
