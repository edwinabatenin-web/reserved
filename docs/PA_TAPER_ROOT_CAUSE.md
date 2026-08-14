# Personal Allowance taper defect — root-cause record

Date investigated: 13 August 2026.

## Classification

The defect is **(c) incomplete earlier test coverage combined with (d) duplicate calculation logic**. It is not an unpromoted Reserved West fix and not a regression of the earlier EL-001 correction.

## What the earlier fix did

EL-001 correctly replaced an interval calculation using one end-state Personal Allowance with `total_tax(end) - total_tax(start)`. That correction was promoted into the main engine and tested invoices entering and crossing the taper.

## What it did not fix

Each full-position calculation still treated £50,270 as a taxable-band ceiling measured from gross income. When Personal Allowance fell, that widened the basic-rate slice above its statutory £37,700 width. At £110,000, for example, £42,700 was incorrectly taxed at 20%.

The correct coordinate system is:

- calculate Personal Allowance from adjusted net income;
- deduct that allowance to obtain taxable income;
- apply the £37,700 basic-rate band to taxable income;
- extend that taxable band by gross Relief-at-Source pension contributions;
- apply the additional rate above £125,140 taxable income.

## Why Reserved West did not catch it

The main engine, packaged prior implementation, Reserved West reference calculator and Optimise assurance reference all encoded the same gross-income-ceiling model. Their tests asserted values produced from that model, including £32,432 at £110,000 instead of £33,432. “Zero variance” was therefore circular agreement, not independent validation.

Earlier boundary tests checked that the allowance itself tapered correctly and that before/after calculations were internally consistent. They did not independently assert the invariant that the basic-rate band remains £37,700 of taxable income as the allowance falls.

## Correction and recurrence controls

- Added an explicit versioned `BASIC_RATE_BAND = £37,700` rule.
- Changed the authoritative engine to tax `income - Personal Allowance` using taxable-income band widths.
- Corrected the packaged duplicate and both assurance/reference calculation paths so future comparisons do not preserve the known defect.
- Added literal regression fixtures at £99,999, £100,000, £100,001, through the midpoint and £125,140, and above it.
- Added £1 marginal checks throughout the taper (60p), the first £1 above it (45p), and pension/ANI cases on both sides of the thresholds.

Historical Reserved West evidence generated before this correction must not be cited as validation of PA-taper tax amounts. It should be regenerated only after its expected fixtures have been independently corrected.

The mandatory independence rule introduced in response is recorded in `docs/RESERVED_WEST_INDEPENDENCE_STANDARD.md`.
