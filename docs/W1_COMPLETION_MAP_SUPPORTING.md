# W1 annual-tax completeness — supporting completion map

Status: supporting cross-workstream map, not authoritative W1 state.
Evidence cut-off: 1 September 2026.

This map applies the rolling completion-map rule to the W1 boundary on which
W2-S6 depends. It was initially derived read-only from commit `066ed358...` and
reconciled after the independently reviewed W1-S4 correction at clean W1
checkpoint `413ee1312ba4ec8cf42912a9411f55b69a0a1d3e`. It does not alter
Founder Decisions, widen tax scope, reconcile the Founder Control Plane, or
declare any customer or launch purpose assured.

## Owned outcome and finite denominator

W1 owns one evidence-qualified annual Self Assessment position for the
Founder-confirmed v1 tax scope. The position must identify every included,
excluded and unsupported family, preserve provenance and uncertainty, and
provide a stable internal contract from which W2 can derive cash obligations
without inventing or double-counting liability.

W1 has exactly five implementation slices:

| Slice | Owned outcome | Evidence position |
|---|---|---|
| W1-S1 | Integrated annual Income Tax/Class 4/HICBC calculation for the explicitly supported internal scope, with unsupported cases withheld rather than treated as zero | Complete at the current W1 checkpoint for bounded internal use; not customer-purpose assured |
| W1-S2 | Annual student-loan/PGL reconciliation and typed internal composition with the annual tax result | Complete at the current W1 checkpoint for bounded internal use; the current composition deliberately does not aggregate money |
| W1-S3 | Fail-closed Blind Person's Allowance integration and compatibility corrections | Complete and independently post-commit verified at `066ed358f9dc231f3c424c7fc01123fce0bdee6b` |
| W1-S4 | Launch-supported-scope closure: every v1 input combination is either calculated under an independently supported rule or deterministically withheld with an explicit unsupported/uncertain reason | Complete and independently reviewed at `413ee1312ba4ec8cf42912a9411f55b69a0a1d3e`; two material property fail-close gaps were corrected |
| W1-S5 | Cash-ready annual-position contract: expose the complete supported annual liability components and separately classified student-loan/PGL amount for W2-S6, with purpose, dates, ruleset, evidence and prohibitions preserved | Complete, independently reviewed and post-checkpoint verified at `51b2e023a23c22dfbe61a6e607d81ab399d475b7` |

No W1-S6 implementation slice is currently justified. Customer presentation,
privacy, provider connectivity and integrated release assurance are terminal
gates or other workstream responsibilities, not additional W1 product slices.

## Closure record and remaining slice

### W1-S4 — launch-supported-scope closure (complete)

Reconcile the current engine against the existing v1 scope without silently
turning an unsupported tax treatment into zero. In particular:

- foreign-property cases requiring Foreign Tax Credit Relief;
- UK-property cases requiring the residential finance-cost reduction;
- HICBC cases with missing, stale, contradictory or ambiguous responsibility
  evidence;
- dividends/savings ordering at the eventual customer-connected boundary;
- PAYE tax-deducted-at-source and loan deductions, which are reconciliation
  evidence rather than interchangeable annual-liability inputs.

Completion does not require implementing every possible UK tax rule. It does
require a reviewed launch-supported subset and deterministic exclusion of any
case that cannot safely produce a complete position. Scottish tax, Capital
Gains Tax, full MTD filing and non-UK jurisdiction rules remain outside v1.

Independent review found and the focused package corrected two material gaps:
incomplete joint-property fact pairs and unsupported foreign-property losses.
The exact two-file correction is independently reviewed and post-checkpoint
verified at `413ee131...`; no additional tax-rule tranche was created.

### W1-S5 — cash-ready annual-position contract (complete)

Replace the present non-aggregating, non-customer internal link with a separate
purpose-specific contract suitable for W2-S6. The contract must:

- carry the supported annual tax subtotal and named components;
- carry student-loan/PGL remaining Self Assessment amounts separately;
- state which components enter final liability and which enter the PoA basis;
- keep PAYE/tax deducted, prior PoA, payments and HMRC credits outside the
  annual-liability total so W2 can apply each exactly once;
- preserve tax year, ruleset, calculation date, evidence identity,
  completeness, unsupported families, limitations and prohibited uses;
- fail closed when an upstream family is incomplete, stale, conflicting,
  unsupported or semantically incompatible;
- remove a reserve/cash-use prohibition only for the explicitly reviewed
  internal W2-S6 purpose, never by implication.

The completed contract uses exact SHA-256 content identities recorded by
independently reviewed upstream checkpoints. A changed tax, loan or no-loan
object cannot reuse the trusted identity. It supports Plan 2, Plan 2 + PGL and
explicit complete no-loan evidence, while exposing no PoA basis or payment
authority.

W1-S5 does not implement PoA, balancing payments, account reconciliation,
reserve arithmetic, UI, filing or payment. Those remain W2 or other-workstream
responsibilities.

## Dependencies, parallelism and collision rules

| Item | Dependency | May proceed now? | Collision control |
|---|---|---|---|
| W1-S4 evidence, correction and review | Existing Founder scope and current W1 contracts | Complete | Exact two-file correction; HICBC privacy/customer activation remained outside the package |
| W1-S5 contract and fixtures | Stable W1-S4 supported-family boundary | Complete at `51b2e02...` | Narrow purpose-specific contract; no rewrite of W2 S1-S5 contracts |
| HICBC customer activation | Privacy, retention, legal, security and customer-evidence gates | Parallel external gate | HICBC arithmetic may remain in W1; activation belongs to the HICBC/privacy workstreams |
| W2-S6 | Stable reviewed W1-S5 contract | Complete locally at W2 checkpoint `485b766...` | W2 consumes the exact W1 contract and did not invent a second annual tax model |
| UX and integrated assurance | Stable W1/W2 statuses and exact checkpoints | Prepare in parallel | Presentation evidence cannot upgrade engineering status by narrative |

Potential shared-file consumers must be enumerated before each submission,
including annual composition, internal snapshot, W2 adapter fixtures and their
exact regression tests. Directory-wide write permission is not justified.

## Terminal W1 completion gate

W1 is complete only when all of the following are true:

1. Every Founder-confirmed v1 income family is either calculated in the
   reviewed supported subset or explicitly withheld as unsupported.
2. Income Tax, Class 4 and applicable HICBC components reconcile to the named
   annual tax subtotal without hidden zero assumptions.
3. BPA and other supported allowances/reliefs are applied once, with eligibility
   and evidence limitations preserved.
4. Student-loan/PGL annual liability and evidenced deductions reconcile to a
   separately classified remaining Self Assessment amount.
5. FTCR, residential finance costs, ambiguous HICBC responsibility and other
   unsupported interactions cannot produce a misleading complete total.
6. The final contract distinguishes annual liability from tax deducted, prior
   PoA, payments, credits, refunds and dated HMRC obligations.
7. Tax year, ruleset, dates, provenance, completeness and uncertainty survive
   composition losslessly.
8. The W1 contract supplies the exact reviewed boundary required by W2-S6 and
   prevents double counting across that boundary.
9. Focused, compatibility and broader W1 regression tests pass at an exact
   clean local checkpoint.
10. A fresh independent post-checkpoint review confirms the supported scope,
    fail-close behaviour and W2-facing contract.

Current bounded position: W1-S1 through W1-S5 are complete as implementation
slices. This is 5 of 5 declared implementation slices (100%). The exact W1-S5
checkpoint passed 224 focused/adjacent tests and the broader suite passed 1,693
tests plus 7 subtests, with only the expected canonical-metadata freshness
failure after legitimate source advancement. Terminal-gate and launch status
must still be reported separately and must not be
inferred from the slice percentage or used as a launch-readiness claim.

## Out of scope

W1 does not own UI/UX implementation, provider-specific imports, HMRC filing,
payment initiation, production activation, Scottish tax, Capital Gains Tax,
full MTD return submission, legal/privacy approval, or post-launch tax
sophistication. New support for those areas requires its own authorised scope.

## Effort and next executable package

- W1 implementation remainder: none at the declared denominator.
- W2-S6 local integration and review: complete at local W2 checkpoint
  `485b766...`; the exact W1 content identity and separate cash evidence
  channels were retained.

Next gate: refresh integrated assurance metadata against the new source
checkpoint and complete the separately owned customer-language/UX evidence.
The local integration line remains unmerged and unpushed.
