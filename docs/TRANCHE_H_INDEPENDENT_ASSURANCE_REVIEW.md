# Independent assurance review — Tranche H candidate

**Artifact reviewed:** `docs/fixtures/TRANCHE_H_CANDIDATE.json`  
**Derivation reviewed:** `docs/WP7_TRANCHE_H_CANDIDATE_DERIVATION.md`  
**Review date:** 13 August 2026  
**Decision:** **do not admit any Tranche H fixture yet**  
**Change boundary:** review only; candidate, corpus, manifest and production
code were not modified

## Executive conclusion

The candidate is structurally well controlled and its displayed arithmetic is
internally consistent. It also maintains useful separations between annual
liability, foreign-tax evidence, PAYE/payroll-deduction evidence and
customer-presentation policy.

It is not yet fit for deliberate admission as independent validation evidence:

1. the cited rates page is not sufficient evidence for the mixed-income
   allocation/ordering and nil-rate-band interactions that determine the two
   Income Tax results;
2. the annual student-loan income basis in HMX-002 relies on material assumptions
   about gross relief-at-source pension deductions and unearned/property income
   that are stated but not independently evidenced at rule level;
3. HMX-003's evidence freshness and absence of conflict are assertions without
   the provenance/representation records needed for a reconciliation-purpose
   fixture;
4. HMX-003 depends numerically on the still-unapproved HMX-002 liabilities;
5. the reviewer and derivation metadata both identify Codex streams. This review
   is a separate role and used no production/West helpers, but it does not
   establish the second-person organisational independence required for final
   admission under the remediation plan.

The appropriate action is **remediate and re-review**, not reject the tranche's
concept or use it to unblock WP8.

## Independence and method

This review did not import, execute or inspect production calculation helpers,
Reserved West calculators, historical reference calculators or shared expected-
result generators. Arithmetic was recomputed from the candidate's literal
facts using first-principles decimal operations. Source applicability was
assessed from the source claims and official links retained in the artifacts;
no engine output was treated as evidence.

The candidate and derivation both state that derivation occurred outside the
production and historical West calculators. Their text contains no executable
imports or generated expected values. This is useful lineage evidence, but an
assertion in the artifact is not independently sufficient to prove lineage.
Existing structural/integrity controls should still be applied when a revised
candidate is proposed for admission.

## Structural/schema review

**Result: pass for review-pending candidate form.**

- JSON parses and contains three unique fixture IDs.
- IDs `RW3-HMX-001` to `003` satisfy the pack schema's ID pattern.
- Pack and fixture statuses remain `independent_fixture_review_pending`.
- Review identity/date are null and decision is pending, consistent with a
  candidate that has not been admitted.
- Tax year and territory match the schema.
- Every source uses HTTPS and includes a stated support claim.
- Every fixture contains inputs, literal expected values, derivation and
  limitations.
- The pack explicitly states that it is outside the assurance corpus and
  integrity manifest.

The generic schema permits arbitrary input/expected keys and therefore cannot
detect semantic omissions, inconsistent money-string formats or cross-fixture
dependencies. Structural validity is not an accuracy or fitness decision.

## Independent arithmetic recheck

### HMX-001

The literal arithmetic recomputes as stated:

- total income: `30,000 + 15,000 + 5,000 + 5,000 + 2,000 + 3,000 = 60,000`;
- ANI after stated £5,000 gross RaS contribution: `55,000`;
- non-savings taxable amount: `55,000 − 12,570 = 42,430`;
- displayed non-savings tax: `42,430 × 20% = 8,486.00`;
- displayed savings tax: `1,500 × 40% = 600.00`;
- displayed dividend tax: `2,500 × 35.75% = 893.75`;
- pre-credit Income Tax: `8,486 + 600 + 893.75 = 9,979.75`;
- Class 4: `(15,000 − 12,570) × 6% = 145.80`;
- ANI £55,000 is not over the stated £60,000 HICBC threshold.

No arithmetic discrepancy was found. However, the £600/£893.75 results depend
on statutory ordering and on how the Personal Savings Allowance and Dividend
Allowance occupy rate-band capacity after non-savings income. The candidate
describes that conclusion but cites only a general rates-and-allowances page.
Admission needs an exact official ordering/allocation source and a derivation
showing the remaining £270 of extended basic-rate capacity and its interaction
with the nil-rate savings band. Without that, the expected result is plausible
and internally consistent, but not sufficiently source-auditable.

`foreign_tax_credit: null` is appropriate as an explicit unsupported result.
It also means this fixture validates pre-credit components only and must never
be labelled a complete foreign-property liability or final amount due.

### HMX-002

The displayed core arithmetic also recomputes:

- total income: `113,000`;
- stated ANI after £10,000 gross RaS contribution: `103,000`;
- tapered PA: `12,570 − ((103,000 − 100,000) ÷ 2) = 11,070`;
- taxable non-savings: `110,000 − 11,070 = 98,930`;
- non-savings tax: `47,700 × 20% + 51,230 × 40% = 30,032.00`;
- pre-credit Income Tax: `30,032 + 200 + 536.25 = 30,768.25`;
- Class 4: `(20,000 − 12,570) × 6% = 445.80`;
- raw Plan 2 calculation on the stated basis:
  `(103,000 − 29,385) × 9% = 6,625.35`;
- raw PGL calculation: `(103,000 − 21,000) × 6% = 4,920.00`;
- displayed loan deductions and residual amounts reconcile arithmetically;
- the stated ANI is above £80,000, so the fixture's 100% HICBC percentage is
  consistent with its cited threshold premise;
- £1,406.60 floored to the stated £1,406 is arithmetically consistent with the
  pack's rounding declaration.

No displayed addition, subtraction or multiplication error was found.

Two rule-basis issues block admission:

1. The fixture assumes the £10,000 gross RaS contribution reduces the annual
   Self Assessment student-loan income basis. The retained sources support ANI
   reduction and general annual loan reconciliation, but the review artifact
   does not cite the exact official rule that makes the same deduction in the
   loan calculation.
2. The loan basis includes employment, sole trade, UK/foreign property,
   savings and dividends before subtracting the pension. The derivation does
   not identify the official unearned-income inclusion threshold or establish
   how the stated property/savings/dividend amounts enter the relevant annual
   loan basis.

These are material applicability questions: changing the basis changes both
annual loan expected values and the HMX-003 residual. They cannot remain merely
inside a limitations sentence if the values are admitted as validation-critical
expected results.

As with HMX-001, mixed-income Income Tax ordering requires a more precise
official ordering/allocation citation. `foreign_tax_credit: null` correctly
limits the fixture to pre-credit tax.

### HMX-003

The reconciliation arithmetic is correct:

- `30,768.25 − 15,000 = 15,768.25`;
- `11,545 − (3,000 + 1,800) = 6,745`;
- `15,768.25 + 6,745 + 445.80 + 1,406 = 24,365.05`.

The explicit `presentation_status: blocked_pending_policy_approval` and
`arithmetic_sum_not_approved_for_customer_presentation` are appropriate. The
fixture does not incorrectly call the sum an HMRC balance or final amount due.

It is nevertheless not fit for admission as reconciliation assurance:

- `evidence_freshness: confirmed_current` and `evidence_conflict_count: 0` are
  conclusions, not provenance-bearing evidence items;
- there are no evidence IDs, source observation dates, employment identities,
  annual/YTD representation labels, completeness states or selection reasons;
- the fixture therefore cannot independently demonstrate no double counting,
  currentness or representation compatibility;
- the inputs copy annual liabilities from HMX-002, whose loan-basis and
  mixed-income source applicability remain unresolved.

It may eventually serve as a narrowly labelled arithmetic-reconciliation case,
but that adds little assurance unless it is linked to approved liability
fixtures and provenance-rich deduction evidence. It must not be admitted as a
customer-presentation or remaining-amount validation fixture while the policy
gate is blocked.

## Source applicability findings

| Rule/component | Source position | Review result |
|---|---|---|
| 2026/27 PA, taper and headline rates | Direct official rates source identified | Adequate for headline values; exact observation/version should be retained at admission |
| Gross RaS pension and ANI | Official pension-relief and ANI pages identified | Adequate for the Income Tax/ANI premise; not by itself evidence for student-loan basis |
| Mixed non-savings/savings/dividend ordering and band occupation | No precise ordering/allocation source stated | Inadequate for admission; add exact official authority and expanded working |
| Class 4 threshold/rate | Direct official source identified and arithmetic transparent | Adequate for these simple stated-profit cases, subject to confirming 2026/27 applicability in the source snapshot |
| HICBC thresholds/partner premise | Direct official pages identified | Broadly adequate; retain exact charge-rounding support and benefit-period premise |
| Child Benefit annual amount | Weekly-rate source identified; £1,406.60 corresponds to 52 weeks at the stated rate | Adequate only for the expressly assumed full benefit period |
| Plan 2/PGL thresholds and rates | Employer Bulletin identified | Adequate for thresholds/rates, not the complete annual SA income-basis treatment |
| Annual SA loan basis, unearned income and pension deduction | General SA guidance identified but exact supporting propositions are not recorded | Inadequate for HMX-002 admission |
| Foreign tax | Evidence recorded; relief deliberately null | Appropriate limitation; validates no post-credit result |
| PAYE/payroll deductions | Literal amounts only, without provenance records | Adequate for subtraction arithmetic only; inadequate for reconciliation fitness |

## Supported-purpose assessment

| Fixture | Potential purpose | Current fitness | Reason |
|---|---|---|---|
| HMX-001 | Pre-credit mixed-income component arithmetic | **Unverified / hold** | Arithmetic passes, but ordering/band-allocation source evidence is incomplete |
| HMX-001 | Complete annual liability or reserve guidance | **Inadequate** | FTCR is unsupported and evidence reconciliation is not performed |
| HMX-002 | Pre-credit mixed-income/taper/HICBC arithmetic | **Unverified / hold** | Arithmetic passes; mixed-income ordering source and HICBC rounding evidence need tightening |
| HMX-002 | Annual student-loan liability | **Inadequate pending rule evidence** | Pension and unearned/property income-basis assumptions are validation-critical |
| HMX-002 | Final annual liability/reserve guidance | **Inadequate** | FTCR null; payments, evidence quality and collection position excluded |
| HMX-003 | Pure subtraction/addition arithmetic | **Sufficient but low assurance value** | Literal arithmetic is correct, but it validates no selection/provenance policy |
| HMX-003 | Reconciliation/customer presentation | **Inadequate / policy-blocked** | Missing provenance/representation evidence and policy approval; depends on HMX-002 |

“Sufficient” for HMX-003's arithmetic does not justify corpus admission: WP7
requires validation-critical coverage, and a calculator-independent addition
case with unresolved upstream values and policy adds little reliable coverage.

## Fixture admission decisions

### RW3-HMX-001 — **HOLD; do not admit**

Recalculate/re-document after adding exact mixed-income ordering and nil-rate
band-capacity authority. Preserve the fixture's narrow pre-FTCR purpose in an
explicit field or family name. After those changes, obtain a genuinely separate
reviewer and recheck all literals.

### RW3-HMX-002 — **HOLD; do not admit**

Obtain exact official support for the annual student-loan income basis,
including gross RaS pension and unearned/property components, before preserving
the Plan 2/PGL literals. Add exact ordering and HICBC rounding authority. If the
rule evidence yields a different loan basis, re-derive HMX-002 and every
dependent fixture rather than editing only the expected values.

### RW3-HMX-003 — **DEFER; do not admit**

Wait for HMX-002 approval and the product-policy decision. Replace conclusion-
only freshness/conflict inputs with provenance-rich evidence items or relabel
the fixture strictly as arithmetic plumbing outside accuracy/reconciliation
pass counts. A policy-blocked result must not be used to claim reconciliation
coverage.

## Required next action

1. Add exact official support for mixed-income ordering, nil-rate allowance
   band occupation and HICBC charge rounding.
2. Add exact official support for the annual Self Assessment loan income basis,
   especially gross RaS pension and unearned/property inclusion.
3. Re-derive HMX-002 if any basis assumption changes; cascade changes into
   HMX-003.
4. Convert HMX-003's evidence conclusions into dated, representation-aware,
   employment/plan-linked evidence items, or keep it outside validation counts
   as arithmetic-only.
5. Make each fixture's permitted purpose explicit: pre-FTCR component test,
   annual loan liability, or policy-blocked reconciliation—not “mixed income”
   generally.
6. Submit the revised artifact to a named second-person reviewer who is
   organisationally distinct from the derivation stream.
7. Only after approval should an authorised gate owner deliberately update the
   candidate status/review metadata, integrity manifest and corpus allowlist.

Until all applicable steps pass, Tranche H remains outside the assurance corpus
and must not unblock Integrated Annual Tax Position work.

---

## Supplemental independent re-review — 13 August 2026

**Scope:** `RW3-HMX-001` and `RW3-HMX-002` only  
**New authority reviewed:** `docs/TRANCHE_H_SOURCE_AUTHORITY_NOTE.md`,
`docs/ANNUAL_STUDENT_LOAN_SOURCE_AUTHORITY.md` and HMRC's current Tax Logic
service guide  
**Unchanged artifacts:** candidate pack, integrity manifest and assurance corpus  
**HMX-003:** remains held; not re-reviewed here

### Method and independence

This supplement rechecked the two literal fixtures and their original written
derivations against the source propositions in the authority note. It did not
import or execute production code, West code, historical reference calculators,
shared formula helpers or generated expected values. The arithmetic was
reperformed from the stated literals.

The authority note resolves the three source gaps identified by the first
review: section 16 ordering/nil-rate-band occupation, regulation 29 annual loan
basis (including the conditional pension deduction and all-or-nothing unearned-
income rule), and statutory HICBC whole-pound rounding.

### RW3-HMX-001 supplemental verdict

**Verdict: READY FOR A SEPARATE DELIBERATE ADMISSION STEP — not admitted by this
review.**

The recomputation remains unchanged:

- £60,000 total income and £55,000 ANI after the stated £5,000 gross qualifying
  RaS contribution;
- £42,430 taxable non-savings income and £8,486 non-savings tax;
- £270 extended basic-rate capacity remains before savings;
- the £500 PSA is a nil-rate savings slice that occupies the first £500 of the
  ordered savings income; the remaining £1,500 is higher-rate savings tax of
  £600;
- dividends sit above savings; the £500 dividend nil-rate slice is followed by
  £2,500 at 35.75%, or £893.75;
- pre-FTCR Income Tax is £9,979.75;
- Class 4 is £145.80 and HICBC is nil at the stated ANI.

Income Tax Act 2007 section 16 and HMRC SAIM1080/1090 now provide the missing
ordering and nil-rate-band support. No arithmetic or applicability discrepancy
remains within the fixture's expressly limited purpose.

Admission conditions are documentary/change-control conditions, not unresolved
arithmetic:

1. label the admitted purpose narrowly as **pre-FTCR mixed-income component
   validation**, not a complete annual bill, amount due or reserve figure;
2. preserve the assumptions that the UK/foreign property inputs are already
   valid taxable profits, the pension amount is gross and qualifies for relief,
   and no unmodelled losses/reliefs alter section 23 income;
3. preserve `foreign_tax_credit: null` and the prohibition on inferring a
   post-credit liability;
4. have a named, organisationally distinct gate reviewer record the admission
   decision/date and deliberately update integrity/corpus artifacts.

Subject to those controls, HMX-001 is fit to validate the literal components it
states. It is not fit for customer-facing final-liability or reserve guidance.

### RW3-HMX-002 supplemental verdict

**Verdict: READY FOR A SEPARATE DELIBERATE ADMISSION STEP — not admitted by this
review.**

The following now pass re-review:

- £113,000 total income;
- £103,000 ANI and stated annual loan basis after a £10,000 **gross qualifying**
  RaS pension amount;
- PA £11,070, extended basic-rate limit £47,700 and non-savings tax £30,032;
- ordered higher-rate savings tax £200 and dividend tax £536.25;
- pre-FTCR Income Tax £30,768.25;
- Class 4 £445.80;
- 100% HICBC at ANI above £80,000 and whole-pound charge £1,406 from the stated
  £1,406.60 benefit amount;
- raw Plan 2 amount £6,625.35 on the supported £103,000 basis;
- raw PGL amount £4,920.00;
- subtraction of separately stated payroll deductions and the £6,745 combined
  residual arithmetic.

Regulation 29 and HMRC CSLM8520/16035 support the £103,000 annual basis only on
the candidate's explicit facts: all property/savings/dividend amounts are valid
step-1 taxable amounts, total unearned income exceeds £2,000 so the whole
relevant amount is included, and the entire £10,000 pension amount actually
receives the qualifying statutory relief and was not already excluded. Those
must remain visible assumptions.

HMRC's current Tax Logic service guide directly resolves the remaining stage
question. Its Self Assessment student-loan pseudocode calculates, for the
applicable plan type, `repaymentAmount = roundDown(totalIncomeAboveThreshold *
rate, 0)` and only then derives the amount net of the relevant undergraduate or
postgraduate deduction. This is annual Self Assessment calculation authority,
not payroll-period inference. The guide also states that only the relevant
undergraduate or postgraduate deduction is present in each plan calculation,
so it supports separate plan rounding before the fixture combines the results.

Applying that rule independently:

- Plan 2: `roundDown((£103,000 - £29,385) × 9%, 0) = £6,625`; less the stated
  £3,000 undergraduate deduction gives £3,625;
- PGL: `roundDown((£103,000 - £21,000) × 6%, 0) = £4,920`; less the stated
  £1,800 postgraduate deduction gives £3,120;
- the separately rounded liabilities total £11,545 and the residuals total
  £6,745.

The expected literals therefore require no change. Admission conditions are
now documentary/change-control conditions rather than an unresolved rule:

1. retain the narrow pre-FTCR purpose and the qualifying-pension, valid taxable-
   income and full-period Child Benefit assumptions;
2. do not generalise this result to simultaneous multiple-undergraduate-plan
   cases, for which the annual plan-selection rule remains outside the reviewed
   authority;
3. retain the separately evidenced undergraduate and postgraduate deductions;
4. obtain named, organisationally distinct gate approval and deliberately
   update the integrity/corpus artifacts in a separate admission step.

No discrepancy remains in HMX-002 within this supplemental scope. This review
does not admit the fixture and does not make it fit for a complete post-FTCR
annual liability, amount-due or customer reserve purpose.

### HMX-003 unchanged hold

`RW3-HMX-003` remains held for the reasons in the original review: it lacks
provenance-rich, representation-aware PAYE/payroll evidence, depends on
HMX-002's annual liabilities and remains explicitly blocked for customer
presentation policy. This supplement supplies no basis to admit it or count it
as reconciliation coverage.
