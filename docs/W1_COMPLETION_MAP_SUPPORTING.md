# W1 annual-tax completeness — supporting completion map

Status: supporting cross-workstream map, not authoritative W1 state.
Evidence cut-off: 31 August 2026.

This map applies the rolling completion-map rule to the W1 boundary on which
W2-S6 depends. It was derived read-only from the clean W1 worktree at commit
`066ed358f9dc231f3c424c7fc01123fce0bdee6b`. It does not edit W1, alter
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
| W1-S4 | Launch-supported-scope closure: every v1 input combination is either calculated under an independently supported rule or deterministically withheld with an explicit unsupported/uncertain reason | Remaining |
| W1-S5 | Cash-ready annual-position contract: expose the complete supported annual liability components and separately classified student-loan/PGL amount for W2-S6, with purpose, dates, ruleset, evidence and prohibitions preserved | Remaining; serial after W1-S4 |

No W1-S6 implementation slice is currently justified. Customer presentation,
privacy, provider connectivity and integrated release assurance are terminal
gates or other workstream responsibilities, not additional W1 product slices.

## Remaining slices

### W1-S4 — launch-supported-scope closure

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

This slice should be one bounded scope-closure package, not one package per tax
edge case. Split it only if an independently evidenced rule implementation is
materially larger than the fail-close/customer-eligibility boundary.

### W1-S5 — cash-ready annual-position contract

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

W1-S5 must not implement PoA, balancing payments, account reconciliation,
reserve arithmetic, UI, filing or payment. Those remain W2 or other-workstream
responsibilities.

## Dependencies, parallelism and collision rules

| Item | Dependency | May proceed now? | Collision control |
|---|---|---|---|
| W1-S4 evidence/fixture inventory | Existing Founder scope and current W1 contracts | Yes | Read-only inventory first; enumerate exact engine, contract and regression consumers before editing |
| W1-S4 implementation | Independent rule evidence or an explicit fail-close eligibility boundary | Yes, in a W1-rooted worktree | Do not mix HICBC privacy/customer activation or provider work into the package |
| W1-S5 fixtures and field mapping | Current W1 composition plus W2 S6 preparation | Yes | Fixture preparation may run in parallel; do not freeze the adapter before W1-S4 |
| W1-S5 implementation | Stable W1-S4 supported-family boundary | No, serial after W1-S4 | Add a narrow purpose-specific contract; do not rewrite W2 S1-S5 contracts |
| HICBC customer activation | Privacy, retention, legal, security and customer-evidence gates | Parallel external gate | HICBC arithmetic may remain in W1; activation belongs to the HICBC/privacy workstreams |
| W2-S6 | Stable reviewed W1-S5 contract | Fixtures now; implementation later | W2 consumes the W1 contract and must not invent a second annual tax model |
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

Current bounded position: W1-S1 through W1-S3 are complete as implementation
slices; W1-S4 and W1-S5 remain. This is 3 of 5 declared implementation slices
(60%). Terminal-gate progress must be reported separately and must not be
inferred from the slice percentage or used as a launch-readiness claim.

## Out of scope

W1 does not own UI/UX implementation, provider-specific imports, HMRC filing,
payment initiation, production activation, Scottish tax, Capital Gains Tax,
full MTD return submission, legal/privacy approval, or post-launch tax
sophistication. New support for those areas requires its own authorised scope.

## Effort and next executable package

- W1-S4: roughly 1–3 active days, depending on whether existing evidence
  supports bounded rule arithmetic or confirms fail-close eligibility only.
- W1-S5: roughly 0.5–1.5 active days after W1-S4 stabilises.
- independent review and compatibility regression: roughly 0.5–1 active day,
  partially parallel with W2-S6 fixture review.
- likely critical path to W2-S6 entry: roughly 2–5 working days, excluding
  external HICBC/privacy/customer-evidence elapsed time.

Next package: in the W1-rooted task, perform a short read-only W1-S4 pre-flight
that enumerates the exact launch-supported cases, unsupported cases, evidence
sources, intended files and mechanical test consumers. Then implement the
smallest coherent scope-closure diff and obtain independent review. W2-S6
fixtures may continue in parallel, but final integration remains gated on the
reviewed W1-S5 contract.
