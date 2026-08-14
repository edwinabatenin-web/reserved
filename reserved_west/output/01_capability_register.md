# Reserved Engine — Capability Register
**Engine version:** 2.0.1
**Assurance cycle:** Reserved West Initiative 001
**Date:** 2026-08-07

## Supported capabilities

| Capability | Status | Notes |
|---|---|---|
| Income tax — England/Wales/NI | ✅ Supported | Marginal before/after differential |
| Income tax — Scotland | ❌ Not supported | Different band rates; out of scope |
| Personal Allowance | ✅ Supported | Full PA of £12,570 applied |
| Personal Allowance taper (ANI > £100k) | ✅ Supported | Correct differential: total_tax(end) − total_tax(start); EL-001 resolved in v2.0.0; EL-003 cap resolved in v2.0.1 |
| Basic rate (20%) | ✅ Supported | |
| Higher rate (40%) | ✅ Supported | |
| Additional rate (45%) | ✅ Supported | ART £125,140 |
| Class 4 NI — main rate (6%) | ✅ Supported | On freelance profit only |
| Class 4 NI — upper rate (2%) | ✅ Supported | Above UPL £50,270 |
| Class 1 NI (employment) | ℹ️ Not re-calculated | Assumed handled via PAYE |
| Pension Relief at Source | ✅ Supported | Gross contribution extends BRL and reduces ANI |
| Pension — employer / salary sacrifice | ❌ Not supported | Out of scope |
| Student Loan Plan 1 | ✅ Supported | 2025/26 and 2026/27 thresholds |
| Student Loan Plan 2 | ✅ Supported | 2025/26 and 2026/27 thresholds |
| Student Loan Plan 4 | ✅ Supported | 2025/26 and 2026/27 thresholds |
| Student Loan Plan 5 | ✅ Supported | Fixed threshold £25,000 |
| Postgraduate Loan | ✅ Supported | Fixed threshold £21,000; rate 6% |
| Multiple loan plans simultaneously | ✅ Supported | Summed independently |
| CGT — shares, crypto, other assets | ✅ Supported | Post-Oct 2024 rates (18%/24%) |
| CGT — residential property | ⚠️ Warning issued | Rates now unified; disclaimer shown |
| CGT — Annual Exempt Amount | ✅ Supported | £3,000 from 2024/25 |
| CGT — brought-forward losses | ✅ Supported | |
| CGT — basic/higher rate split | ✅ Supported | Based on taxable income before gains |
| CGT — BADR / Investors' Relief | ❌ Not supported | Warning issued |
| CGT — share pooling / 30-day matching | ❌ Not supported | Warning issued |
| Dividend income | ❌ Not supported | Out of scope |
| Savings income | ❌ Not supported | Out of scope |
| Tax year 2025/26 | ✅ Supported | Confirmed HMRC rates |
| Tax year 2026/27 | ✅ Supported | Confirmed HMRC rates |
| Allocation (gross → reserve + spend) | ✅ Supported | Zero platform fee in preview |

## Defect history

| ID | Summary | Status | Resolved in |
|---|---|---|---|
| EL-001 | Moving Personal Allowance — incremental IT applied end-state PA across full interval | ✅ Resolved | Engine v2.0.0 |
| EL-002 | CGT BASIC_RATE_LIMIT sourced from module-level constant instead of versioned config | ✅ Resolved | Engine v1.0.0 |
| EL-003 | Extended BRL not capped at ART when pension > £74,870 — suppressed 45% additional rate | ✅ Resolved | Engine v2.0.1 |

## EL-001 permanent regression family

EL-001 is archived as a permanent regression family.  Any future variance in an
EL-001 zone scenario is classified **REGRESSION_EL001** and is a gate-blocking defect.

The broader principle: an incremental calculation must not assume that allowances,
reliefs, thresholds or tax treatment remain constant between the starting and ending
tax positions.  See `reserved_west/runner.py` for the formal definition.

## EL-003 permanent regression family

EL-003 is archived as a permanent regression family.  Any future variance on a
scenario where pension RaS > £74,870 is classified **REGRESSION_EL003** and is
a gate-blocking defect.

The root cause was that `extended_basic_rate_limit = BRL + pension` lacked a cap
at ART.  When pension > £74,870 (= ART − BRL = £125,140 − £50,270), the uncapped
eBRL exceeded ART, causing `_income_tax_between` to silently absorb the ART and
additional-rate band into the 20% basic-rate slice.

The fix: `extended_basic_rate_limit = min(BRL + pension, ART)` — applied identically
in both `reserved/engines/income_tax.py` and the bundled copy.  37 regression tests
confirm the fix (24 workspace-side, 13 bundle-native).

## Out-of-scope catalogue

The following are explicitly outside scope and must never be counted
as calculation failures in the evidence register:

- Scottish income tax
- Dividend income and savings income (different ordering rules)
- Non-UK-resident cases
- Non-domicile rules
- PAYE coding adjustments
- Employer pension contributions / salary sacrifice
- BADR / Investors' Relief
- CGT share pooling and matching rules
- Carried-interest rules
