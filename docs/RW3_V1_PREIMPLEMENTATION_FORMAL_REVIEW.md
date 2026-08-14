# RW3 v1 preimplementation fixture pack — formal independent review

Review date: 13 August 2026  
Reviewer: Codex independent second-person review stream  
Artifact: `docs/fixtures/RW3_V1_PREIMPLEMENTATION_FIXTURES.json`  
Decision: **APPROVED — independent validation**

## Review boundary

All 53 fixtures were reviewed against the official sources cited by the pack for source applicability, arithmetic, rounding, semantics and deliberate limitations under `docs/RESERVED_WEST_INDEPENDENCE_STANDARD.md`. The review used manual derivations from the published rules. It did not execute or inspect production calculation helpers, the West reference calculator, Optimise helpers, historical West assertions or shared expected-result formulas.

Approval is confined to the literal propositions expressed by these fixtures. In particular, it does not approve a residential-finance-cost reducer, Foreign Tax Credit Relief, residence inference, treaty treatment, split-year/remittance treatment, MTD exemption determination, legal ownership inference, or any unexpressed interaction.

## Official rule basis applied

- For 2026/27, Personal Allowance is £12,570, withdrawn by £1 for each £2 of adjusted net income over £100,000; the basic-rate band is £37,700.
- Savings follow non-savings income. The £5,000 starting-rate band is reduced pound-for-pound by taxable non-savings income; the Personal Savings Allowance is £1,000 for basic-rate, £500 for higher-rate and nil for additional-rate taxpayers.
- Dividends follow non-savings and savings income. The £500 Dividend Allowance is a nil-rate amount that still occupies band capacity; 2026/27 dividend rates are 10.75%, 35.75% and 39.35%.
- UK property-business results are aggregated; a property-business loss is carried forward within that business rather than set against employment. Residential finance costs for an individual are not ordinary deductible expenses and require the separate statutory tax-reduction limits.
- A full-year UK resident is normally chargeable on foreign income. Residence, treaty facts and credit-relief limits cannot be inferred merely from a foreign profit or foreign tax amount.
- 2026/27 Child Benefit is £27.05 weekly for an eldest or only child and £17.90 for each additional child. HICBC applies above £60,000 ANI at 1% for each complete £200, capped at 100% at £80,000. ITEPA 2003 s681C(3) requires staged downward rounding of the relevant total Child Benefit amount, the percentage and the calculated charge. The earlier review incompletely applied only percentage/final-charge rounding; the re-review below corrects that interpretation.
- MTD qualifying income is combined gross self-employment and property income before expenses. The tests are strictly “more than” £50,000 for 2024/25 (start 6 April 2026), £30,000 for 2025/26 (start 6 April 2027), and £20,000 for 2026/27 (start 6 April 2028), subject to scope and exemptions. Partnership timing remains to be set.

## Fixture decisions

| Fixture | Decision | Independent finding |
|---|---|---|
| RW3-SAV-001 | Supportable | £3,000 taxable non-savings gives £600; it reduces the starting-rate band to £2,000, and £4,000 savings after the £1,000 PSA gives £800. |
| RW3-SAV-002 | Supportable | £2,570 unused PA and £3,430 starting-rate capacity cover all £6,000 savings. |
| RW3-SAV-003 | Supportable | Full £5,000 starting-rate band plus £1,000 basic-rate PSA covers £6,000 savings. |
| RW3-SAV-004 | Supportable | £1 taxable employment and £1 taxable savings at 20% each give £0.40. |
| RW3-SAV-005 | Supportable | £37,200 taxable employment leaves £500 basic-band capacity; the £500 PSA occupies it and the remaining £500 interest at 40% gives £200. |
| RW3-SAV-006 | Supportable | Nil PA at ANI £126,140; non-savings tax is £42,516 and, with no PSA, £1,000 savings at 45% gives £450. |
| RW3-SAV-007 | Supportable | Savings makes ANI £100,500, reducing PA to £12,320. Non-savings tax is £27,332 and £500 interest after the higher-rate PSA at 40% gives £200. |
| RW3-DIV-001 | Supportable | Employment tax is £6,486; £4,500 dividends after the allowance remain in the basic band and give £483.75. |
| RW3-DIV-002 | Supportable | £500 dividends are wholly within the Dividend Allowance; total remains £6,486. |
| RW3-DIV-003 | Supportable | £4 above the £500 allowance at 10.75% gives exactly £0.43. |
| RW3-DIV-004 | Supportable | The allowance consumes remaining basic-band capacity; the remaining £500 at 35.75% gives £178.75. |
| RW3-DIV-005 | Supportable | Nil PA; £500 taxable dividends in the additional band at 39.35% gives £196.75. |
| RW3-DIV-006 | Supportable | Dividends make ANI £100,500 and PA £12,320; £500 taxable dividends at 35.75% gives £178.75. |
| RW3-DIV-007 | Supportable | After the allowance, £272 at 10.75% gives £29.24 and £728 at 35.75% gives £260.26; dividend tax is £289.50. |
| RW3-PROP-001 | Supportable | £40,000 combined non-savings less PA gives £27,430 at 20% = £5,486; property profit is not Class 4 trading profit. |
| RW3-PROP-002 | Supportable | £10,000 less £12,000 creates a £2,000 property-business loss carried forward, with no employment offset. |
| RW3-PROP-003 | Supportable | Aggregated UK lettings yield £3,000 profit; £20,430 taxable at 20% gives £4,086. |
| RW3-PROP-004 | Supportable | The supplied 50% taxable share produces £5,000 profit and £4,486 tax; ownership inference is expressly excluded. |
| RW3-PROP-005 | Supportable bounded status case | £8,000 profit before finance-cost reduction is correct. Null reducer/status properly avoids asserting the separately limited calculation. |
| RW3-FPROP-001 | Supportable bounded case | On the explicit full-year UK-resident/no-credit facts, £40,000 non-savings gives £5,486 tax. |
| RW3-FPROP-002 | Supportable status case | Unknown residence is material; declining to calculate UK tax is the supported result. |
| RW3-FPROP-003 | Supportable bounded status case | UK tax before credit is £5,486; recording £1,500 foreign tax without inferring allowable FTCR preserves treaty and limit uncertainty. |
| RW3-FPROP-004 | Supportable bounded case | £14,000 less £4,000 gives £10,000 foreign-property profit and £5,486 UK tax before any credit. |
| RW3-FPROP-005 | Supportable status case | The pack coherently declines to infer UK tax for a non-resident outside its bounded full-year resident case. |
| RW3-HICBC-001 | Supportable | £27.05 × 52 = £1,406.60; floor benefit to £1,406, then 50% is £703 and final flooring remains £703. |
| RW3-HICBC-002 | Supportable | £199 excess contains no complete £200 step, so the percentage and charge are nil. |
| RW3-HICBC-003 | Supportable | One complete step gives 1%; floor benefit to £1,406, then 1% is £14.06 and final flooring gives £14. |
| RW3-HICBC-004 | Supportable after correction | £19,999 gives 99 complete steps; floor benefit to £1,406, then 99% is £1,391.94 and final flooring gives **£1,391**, not the prior £1,392. |
| RW3-HICBC-005 | Supportable | At £80,000 the charge is 100%; £1,406.60 rounds down to £1,406. |
| RW3-HICBC-006 | Supportable | (£27.05 + £17.90) × 52 = £2,337.40; floor benefit to £2,337, then 50% is £1,168.50 and final flooring gives £1,168. |
| RW3-HICBC-007 | Supportable | £27.05 × 26 = £703.30; floor benefit to £703, then 50% is £351.50 and final flooring gives £351. |
| RW3-HICBC-008 | Supportable | £10,000 gross relief-at-source pension reduces ANI from £70,000 to £60,000; no charge. |
| RW3-HICBC-009 | Supportable | ANI below £60,000 produces no charge. |
| RW3-HICBC-010 | Supportable | ANI exactly £60,000 produces no charge. |
| RW3-HICBC-011 | Supportable | A £1 excess contains no complete £200 step, so no charge. |
| RW3-HICBC-012 | Supportable after correction | £19,800 gives 99%; floor benefit to £1,406, then 99% is £1,391.94 and final flooring gives **£1,391**, not the prior £1,392. |
| RW3-HICBC-013 | Supportable | Above £80,000 the percentage remains capped at 100%; charge £1,406. |
| RW3-HICBC-014 | Supportable | The higher-ANI partner is liable; floor benefit to £1,406, then 75% is £1,054.50 and final flooring gives £1,054. |
| RW3-HICBC-015 | Supportable bounded case | On the express fact that no payments were received, nil charge while entitlement is retained is coherent; it does not infer opt-out facts. |
| RW3-HICBC-016 | Supportable | £80,200 is above the cap point; 100% of £1,406.60 rounds down to £1,406. |
| RW3-MTD-001 | Supportable | Exactly £50,000 is not more than the threshold. |
| RW3-MTD-002 | Supportable | £50,001 is over the 2024/25 threshold and, with scope/exemption facts supplied, maps to 6 April 2026. |
| RW3-MTD-003 | Supportable | Exactly £30,000 is not more than the threshold. |
| RW3-MTD-004 | Supportable | £30,001 is over the 2025/26 threshold and maps to 6 April 2027, subject to stated conditions. |
| RW3-MTD-005 | Supportable | Exactly £20,000 is not more than the threshold. |
| RW3-MTD-006 | Supportable | £20,001 is over the 2026/27 threshold and maps to 6 April 2028, subject to stated conditions. |
| RW3-MTD-007 | Supportable status case | Missing Self Assessment registration and exemption facts prevent an unconditional date despite income exceeding the threshold. |
| RW3-MTD-008 | Supportable status case | A confirmed exemption prevents MTD while Self Assessment reporting continues. |
| RW3-MTD-009 | Supportable | Only £30,000 gross trade/property income qualifies; employment, savings and dividends are excluded from this threshold total. |
| RW3-MTD-010 | Supportable | Gross qualifying income is £50,001 before expenses; separate taxable profit is £16,001. |
| RW3-MTD-011 | Supportable semantic distinction | Statutory start and operational sign-up readiness are correctly separated; official guidance requires a return submitted in the last two years to sign up. |
| RW3-MTD-012 | Supportable bounded status case | Partnership income is not relabelled as sole-trade/property qualifying income; official guidance says partnership timing will be set later. |
| RW3-MIX-001 | Supportable | £5,486 non-savings + £200 savings + £483.75 dividends = £6,169.75; £10,000 trade profit is below the Class 4 lower profits limit. |

## Coverage and limitations assessment

The coverage is coherent for a v1 preimplementation pack: it tests ordering, nil-rate allowances, band edges, direct ANI-to-PA interactions, property aggregation/loss/share semantics, bounded foreign-property treatment, HICBC step/cap/partner/pension/period cases, and MTD threshold/scope/status distinctions. Deliberately unsupported calculations return null plus an explicit status rather than a fabricated number. Those cases validate safe bounded behaviour, not the omitted substantive tax calculation.

Material exclusions remain and must not be represented as validated: finance-cost reducer arithmetic, foreign tax credits and treaties, non-resident/split-year/remittance cases, property ownership determination, MTD exemption adjudication, and interactions not literally specified by the pack. These exclusions do not contradict the pack’s stated preimplementation purpose.

## Pack verdict

**APPROVED FOR INDEPENDENT VALIDATION AFTER HICBC CORRECTION.** Every fixture is supportable as now written, including the bounded null/status fixtures, and the coverage/limitations are internally coherent. RW3-HICBC-004 and RW3-HICBC-012 were deliberately corrected after independent staged re-derivation. Root cause was incomplete prior boundary coverage and an incorrect interpretation that omitted the first statutory benefit-floor stage; production output was not used to choose the corrected values. The integrity manifest must be deliberately refreshed for this reviewed change. This verdict does not extend beyond the literal scope above.
