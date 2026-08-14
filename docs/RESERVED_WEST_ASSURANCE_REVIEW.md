# WP7 — Reserved West Assurance Review

Review date: 13 August 2026  
Reviewer position: independent assessment of the framework evidence, not execution of the production or West calculators  
Gate decision: **NOT FIT — WP8 promotion/customer reliance remains blocked**

Scoped-gate update, 13 August 2026: the current corpus contains 107 admitted
fixtures, of which 104 are approved and three simultaneous-multiple-
undergraduate annual-SA fixtures remain pending. A scoped responsible-launch
PASS is **not currently justified**. Founder-confirmed records retain multiple
undergraduate handling as a v1 capability, and the current incremental path
calculates that state rather than failing closed with `unsupported_rule`.
Excluding it would therefore require an explicit founder scope change plus
verified technical and customer restrictions; an assurance reviewer cannot
infer the exclusion. See `docs/WP7_SCOPED_GATE_REVIEW.md` for the exact two safe
paths and operational gates. The three pending fixtures remain admitted and
must never count as approved.

Remediation update, 13 August 2026: fresh re-review finds the **methodology/framework FIT** for validating future development after runner, schema, provenance, approval, integrity and historical-exclusion controls were repaired. Formal review has approved 104 of 107 admitted fixtures, including narrowly scoped HMX-001/HMX-002. The unqualified arithmetic corpus remains incomplete because three simultaneous-multiple-undergraduate annual-SA fixtures lack explicit annual plan-selection authority and remain isolated in a pending pack. A later founder-authorised review in `WP7_SCOPED_GATE_REVIEW.md` issues a **SCOPED PASS** for at most one undergraduate plan plus optional PGL, with simultaneous/unknown combinations failing closed as unsupported-for-decision. That later product-scope decision does not approve or promote the three arithmetic fixtures.

## 1. Question and review boundary

This review asks whether the revised Reserved West methodology and its existing evidence are sufficiently independent, comprehensive and reliable to validate subsequent v1 tax-engine development.

No production calculation helper, West calculator, Optimise reference helper, shared tax configuration, generated West expected result or West assertion of independence was used as an accuracy oracle. Official primary sources and manually derived fixed results were used for the representative sample.

## 2. Original West scope compared with confirmed v1

Original West certified Income Tax, Class 4 NI, pension Relief at Source, student loans and CGT for 2025/26 and 2026/27. It explicitly excluded dividends, savings, PAYE adjustments and Scottish Income Tax.

Confirmed v1 requires England/Wales/NI PAYE and multiple employment, sole trade, dividends, savings, UK property, foreign property, student loans, HICBC and MTD readiness. CGT is outside v1.

The original framework therefore cannot be comprehensive for v1: it gives substantial weight to an excluded family and has no calculation assurance for several required families.

## 3. Evidence classification

| V1 calculation family | Existing West evidence | Classification | Review finding |
|---|---|---|---|
| Non-savings Income Tax and PA | Runtime West calculator comparisons and engine regressions | **Shared-lineage / regression-only** | Reference copied the same gross-income band model and missed the PA-taper defect |
| PA taper and marginal movement | EL-001 scenario families | **Shared-lineage / regression-only** | Correctly tested before/after consistency, but asserted incorrect full-position amounts |
| Pension Relief at Source / ANI | West and Optimise runtime references | **Shared-lineage / regression-only** | Same band-coordinate model; old £3,000 saving at £110k was wrong |
| Class 4 NI | Runtime reference comparisons | **Independent method not demonstrated; review sample agrees** | Simple rules appear correctly represented, but runtime copied formula is not a permitted oracle |
| Student loans — individual plans | Runtime reference comparisons | **Independent method not demonstrated; review sample agrees** | Threshold/rate cases need fixed source-backed fixtures |
| Multiple student-loan plans | West capability and runtime reference | **Inadequate / incorrect** | West summed undergraduate plans independently; official treatment uses one plan with the lowest threshold, plus PGL separately |
| PAYE / multiple employment reconciliation | Not in original West | **Missing** | Required v1 family |
| Dividends and income ordering | Explicitly excluded | **Missing** | Required v1 family; 2026/27 rates changed |
| Savings, starting rate and PSA | Explicitly excluded | **Missing** | Required v1 family |
| UK property | No dedicated calculation evidence | **Missing** | Required v1 family |
| Foreign property and relief boundaries | No evidence | **Missing / requirements incomplete** | Required v1 family; facts and double-tax-relief boundary need specification |
| HICBC liability | Separate Optimise assurance only | **Shared-lineage / incomplete** | Scenario code exists; original West certificate does not cover actual v1 liability integration |
| MTD readiness | No West calculation evidence | **Missing** | Required v1 readiness family, though filing is outside v1 |
| CGT | Extensive West evidence | **Outside current v1** | Must not contribute to the v1 assurance gate |

Existing unit tests that assert internal invariants or stable outputs remain valuable regression evidence. They are not discarded; they are relabelled accurately.

## 4. Representative independent recalculation

The fixed expected values and derivations are recorded in `docs/fixtures/WP7_INDEPENDENT_SAMPLE.json`. The sample was chosen from official thresholds and interaction boundaries, not from production branches.

| Case | Independently derived expected result | Existing-framework implication |
|---|---:|---|
| Income Tax at £99,999, no pension | £27,431.60 | Baseline immediately below taper |
| Income Tax at £100,000 | £27,432.00 | Full PA at threshold |
| Income Tax at £100,001 | £27,432.60 | 60p marginal effect in taper; old West expected £27,432.50 |
| Income Tax at £110,000 | £33,432.00 | Old West/production reference expected £32,432 |
| Income Tax at £125,140 | £42,516.00 | Old West/production reference expected £40,002 |
| £110k income with £10k gross RaS pension | £29,432.00; £4,000 reduction | Old Optimise assurance expected £3,000 reduction |
| Class 4 NI on £60,000 sole-trade profit | £2,456.60 | Agrees with recorded behaviour; needs independent reviewed fixture |
| Plan 1 + Plan 2 at £40,000 | £1,179.00, once using Plan 1 threshold | Contradicts old West “summed independently” claim |
| Plan 1 + Plan 2 + PGL at £40,000 | £2,319.00 | Undergraduate 9% once plus PGL 6% |
| HICBC at £70,000 ANI, one child | £703.00 | 50% of 2026/27 £1,406.60 benefit, then statutory whole-pound rounding |
| £30k non-savings + £10k savings | £5,286.00 total Income Tax | No West coverage: ordering, starting-rate and PSA fixture needed |
| £45k non-savings + £5k dividends | £6,969.75 total Income Tax | No West coverage: £500 allowance and 10.75% rate fixture needed |

These samples confirm that the repaired production taper result now agrees with independently derived literals, but they do not retrospectively make the historical West suite independent.

## 5. Methodology assessment

### Latest 105-fixture corpus

A fresh read-only review found no definite arithmetic or methodological defect
in the newly added bounded property, foreign-property, MTD, HICBC or revised
dividend cases. Tranches F and G now appear sufficient for their deliberately
limited claims, subject to independent approval. The overall result remains:
**methodology FIT; corpus NOT FIT / NOT READY**. The 53-fixture v1
pre-implementation pack is independently approved; the 46-fixture core pack
and six-fixture PAYE-evidence pack remain pending. Tranche H has a separate three-case candidate matrix, but it
is deliberately outside the accuracy corpus pending review. The latest admitted additions
complete the explicit annual Self Assessment loan threshold sides for Plans 1,
2, 4 and 5 and postgraduate loans; add direct savings/dividend ANI taper cases,
a taxable dividend basic/higher split and the HICBC upper-cap continuation.
Their expected literals were derived before implementation comparison and do
not use production or West calculation helpers.

A final gate review verified all 105 fixture entries, all three manifest hashes,
the exact corpus allowlist and fail-closed rejection of pending packs. Formal
second-person review subsequently approved all 53 v1 pre-implementation
fixtures and recorded individual decisions in
`docs/RW3_V1_PREIMPLEMENTATION_FORMAL_REVIEW.md`. The remaining 52 fixtures
retain blank reviewer/date fields and cannot contribute to an approved claim.

The PAYE evidence pack is policy assurance rather than statutory calculation
assurance. Its API citations establish available evidence fields but cannot
approve Reserved's precedence or confidence rules. Those expectations remain
review-pending until an independent product-policy decision is recorded; they
must not be counted as tax-accuracy evidence merely because the arithmetic
reconciles. A stale-evidence candidate now makes the unresolved product-policy
choice explicit with `founder_approval_required`; it is not an approved oracle.

The smallest remaining gate blockers are: second-person approval of the core and PAYE-evidence packs;
founder/product-policy approval or exclusion of PAYE precedence, confidence and
staleness rules; completion of Tranche H across PAYE, trade, property, savings,
dividends, taper, pension, HICBC and student-loan liability/deduction interactions;
and an explicit limitation or separately approved model for payroll-period
student-loan deductions. No pending fixture may contribute to an accuracy PASS.

The isolated `TRANCHE_H_CANDIDATE.json` covers mixed PAYE, trade, UK and foreign
property, savings, dividends, pension/ANI, PA taper, HICBC, Class 4 and annual
Plan 2/PGL liability versus evidenced deductions. Its derivation note explicitly
excludes Foreign Tax Credit Relief and periodic payroll-loan calculation and
labels combined customer presentation as policy-dependent. It validates against
the pack schema but is not in the integrity manifest or assurance corpus.

### Strengths retained

- progressive representative, boundary, interaction and tolerance grouping;
- explicit operating envelope and unsupported-case recording;
- scenario identifiers, evidence registers and gate records;
- separation of calculation and runner namespaces;
- useful regression families and reproducible synthetic inputs.

### Gate-blocking weaknesses

1. **Algorithmic lineage:** absence of imports did not prevent copied production concepts and formulas.
2. **Runtime oracle:** expected values were produced by a mutable calculator rather than reviewed fixed fixtures.
3. **Circular evidence:** engine and reference agreement was treated as accuracy even after both shared the same defect.
4. **No fixture provenance:** scenario rows lack independent derivation author/reviewer records and immutable expected literals.
5. **Scope mismatch:** major v1 families are missing, while CGT is prominent but outside v1.
6. **Known incorrect evidence:** PA taper, pension interaction and multiple-loan evidence contain materially wrong expectations or claims.
7. **Superseded certificate:** the certificate covers engine 2.0.1, not repaired engine 3.0.0, and its independence claim does not meet the adopted standard.

## 6. Required remediation before re-review

- Mark RW-001-CERT and all pre-3.0 PA/pension/multiple-loan accuracy claims as superseded and non-transferable.
- Replace runtime-generated validation outcomes with immutable, primary-source-backed expected fixtures carrying derivation and review provenance.
- Remove production/West shared formula lineage from validation-critical oracles; use manual fixtures or a genuinely external authoritative source.
- Rebuild representative and boundary coverage for non-savings tax, PA taper, pensions, NI and student loans.
- Add v1 fixture families for PAYE reconciliation, dividends, savings, UK property, defined foreign-property cases, HICBC and MTD readiness.
- Add mixed-income ordering and threshold-interaction matrices before engine implementation begins.
- Require separate review of fixture changes and engine changes and prevent the engine implementer from approving expected results.
- Re-run the assurance review against the rebuilt evidence and issue an explicit PASS before WP8 opens.

## 7. Gate decision

**NOT FIT.** The methodology has useful structure, and the new Independence Standard is appropriate, but the current evidence corpus does not satisfy it and is not comprehensive for confirmed v1. WP8 must not begin.

The next tax-assurance activity is remediation of the evidence framework followed by a fresh WP7 gate review. Unrelated integration, authentication, security, accessibility and documentation work may continue under the non-overlap coordination rule.

### Post-remediation distinction

- Methodology/framework fitness: **FIT**.
- Current fixture corpus approval and coverage: **NOT FIT / NOT READY**.
- Overall WP7 gate: **NOT PASSED**; WP8 promotion, customer reliance and readiness claims remain blocked. Isolated implementation against approved evidence may proceed.

The re-review confirmed sample arithmetic was sound and the repaired architecture can support independent validation. It did not approve builder-authored fixtures or waive the published coverage minima.

## 8. Primary sources used

- GOV.UK, Income Tax rates and allowances for 2026/27
- HMRC, 2026/27 tax tables: taxable basic-rate band £37,700
- GOV.UK, Class 4 National Insurance thresholds and rates
- HMRC Employer Bulletin and Agent Update: 2026/27 student-loan thresholds and lowest-threshold treatment
- GOV.UK, Child Benefit and High Income Child Benefit Charge rules
- GOV.UK/HMRC Income Tax ordering material for earnings, savings and dividends
