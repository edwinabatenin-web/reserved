# HMRC Reference Register
**Reference calculator version:** ref-1.0.0
**Assurance cycle:** Reserved West Initiative 001
**Date:** 2026-08-06

This register documents the HMRC primary sources grounding each
calculation module in the independent reference calculator.

## Income tax

| Threshold / Rate | Value | Source |
|---|---|---|
| Personal Allowance | £12,570 | HMRC "Income Tax rates and Personal Allowances"; Finance Act 2022 (freeze to 2028) |
| Basic Rate Limit | £50,270 | Finance Act 2022 (frozen through 2028) |
| Additional Rate Threshold | £125,140 | Finance (No.2) Act 2023 s.5 |
| Basic rate | 20% | Income Tax Act 2007 s.10 |
| Higher rate | 40% | Income Tax Act 2007 s.11 |
| Additional rate | 45% | Income Tax Act 2007 s.12 |
| PA taper — start | £100,000 ANI | Income Tax Act 2007 s.35 |
| PA taper — rate | £1 per £2 excess | Income Tax Act 2007 s.35 |
| PA zero at | ANI ≥ £125,140 | Derived: 12,570 × 2 = £25,140 above £100,000 |

## Pension Relief at Source

| Rule | Source |
|---|---|
| Gross contributions reduce ANI | Finance Act 2004 s.192; HMRC SA150 |
| Gross contributions extend basic-rate band | HMRC Pensions Tax Manual PTM044100; HMRC IT Manual EIM45820 |
| Engine expects gross figure | HMRC "Pension tax relief"; basic-rate top-up claimed by provider |

## Class 4 National Insurance

| Threshold / Rate | Value | Source |
|---|---|---|
| Lower Profits Limit | £12,570 | HMRC "Self-employed NI rates"; SSCBA 1992 s.15; Finance Act 2022 (freeze) |
| Upper Profits Limit | £50,270 | Finance Act 2022 (freeze) |
| Main rate | 6% | HMRC NI rates 2024/25 onwards (reduced from 9%) |
| Upper rate | 2% | HMRC NI rates |

## Student loans

| Plan | 2025/26 Threshold | 2026/27 Threshold | Rate | Source |
|---|---|---|---|---|
| Plan 1 | £24,990 | £26,900 | 9% | SLC Annual Threshold Notice; SI 2009/470 |
| Plan 2 | £28,470 | £29,385 | 9% | SLC Annual Threshold Notice; SI 2009/470 |
| Plan 4 | £32,745 | £33,795 | 9% | SLC Annual Threshold Notice; SI 2009/470 |
| Plan 5 | £25,000 | £25,000 | 9% | Higher Education (Fee Limits) Act 2022; fixed to Apr 2027 |
| Postgraduate | £21,000 | £21,000 | 6% | SI 2009/470; fixed threshold |

## Capital Gains Tax

| Item | Value | Source |
|---|---|---|
| Annual Exempt Amount | £3,000 | Finance (No.2) Act 2023 s.8 (fixed from 2024/25) |
| Basic rate (shares, other) | 18% | Autumn Budget 2024 (revised from 10%, effective 30 Oct 2024) |
| Higher rate (shares, other) | 24% | Autumn Budget 2024 (revised from 20%) |
| Band split basis | BRL minus taxable income | TCGA 1992 s.4; HMRC CG10230 |
| Losses: current year | Offset before AEA | TCGA 1992 s.2 |
| Losses: brought forward | Offset before AEA (after current-year losses) | TCGA 1992 s.2A |
