# W2 completion map

Evidence cut-off: 1 September 2026. This map declares the endpoint of the
already-authorised Payments on Account and Self Assessment cash-obligation
workstream. It does not expand W2, alter Founder Decisions, or establish launch
readiness.

## Completed implementation slices

| Slice | Owned outcome | Local checkpoint | Current evidence state |
|---|---|---|---|
| S1 | PoA applicability, statutory tests, two dated instalments, balancing position and explicit prior-payment/credit composition | `3be75988fef3d34dd617d2621d66bfe97c30769e` | Implemented, independently reviewed and regression-tested as a bounded component |
| S2 | Fail-closed reconciliation of explicit Self Assessment charges, credits and allocations | `11bc8620241f16bc3acb15e4c2f62579057eebe8` | Implemented, independently reviewed and regression-tested as a bounded component |
| S3 | Exact comparison of local PoA/balancing expectations with explicit HMRC account charges | `c661b1abbfe25b3a4049fc3810dcf053d9bb0f93` | Implemented, independently reviewed and regression-tested as a bounded component |
| S4 | Customer-initiated claim-to-reduce guardrails, without recommending an amount or submitting a claim | `c08369307c161e1bcd939960cbf1a62d34d281f1` | Implemented, independently reviewed and regression-tested as a bounded component |
| S5 | Dated funding requirements and evidence-qualified reserve gap/exact/surplus composition | `69fb31576ec730ad49b8da4f0ebb3f5ed135ec98` | Implemented, independently reviewed and regression-tested as a bounded component |
| S6 | Exact W1 annual-position to W2 PoA, balancing, account-obligation and funding-position integration, with source-identity and double-count controls | `485b76696eacd0e9793414f983fb236f6cd7b11c` on local `integration/w1-w2-s6` | Implemented, independently reviewed, adversarially corrected and post-checkpoint regression-tested for bounded internal use |

These checkpoints are not, by themselves, evidence of customer validation,
provider readiness, refreshed integrated release assurance, Control Plane
reconciliation, or launch readiness.

## Remaining implementation slices

None. S6 consumed the exact reviewed W1 cash-ready contract on a dedicated
local integration branch and completed the declared six-slice implementation
denominator. No S7 implementation slice is justified. Customer testing,
refreshed integrated assurance and Control Plane reconciliation are completion
gates or other-workstream responsibilities, not new product slices.

## Dependencies and parallelism

| Item | W1 dependency | W2 dependency | External dependency | Sequencing |
|---|---|---|---|---|
| S5 | None; it consumes already-derived obligations | S1–S3 | None for the pure component | Complete at its independently reviewed local checkpoint |
| S6 contract fixtures | Exact W1-S5 contract | S1–S5 | None | Complete and independently reviewed |
| S6 final integration | Exact W1 source checkpoint `51b2e02...`, assembled locally without conflict | S1–S5 | Local branch-integration authority | Complete at `485b766...`; no merge to main, push or deployment occurred |
| Provider/HMRC journeys | None for W2 arithmetic | S2/S3 evidence contracts | Provider access and target evidence | Parallel, owned by provider workstreams |
| UX/customer testing | Stable W2 statuses and limitations | S1–S6 as relevant | Representative users/test environment | Prepare in parallel; final evidence follows S6 |
| Integrated assurance | Stable exact W1/W2 checkpoints | All slices | Independent reviewer and release environment | Prepare in parallel; execute after S6 |

Shared-file rule: S5 adds its own engine and tests. S6 owns the eventual adapter
and integration tests. Neither package may rewrite S1–S4 contracts without a
separately reviewed compatibility change.

## Terminal W2 completion gate

W2 is complete only when all of the following are true:

1. PoA applicability, fixed-amount and tax-deducted-at-source tests, instalment
   amounts and dates are implemented and reviewed.
2. Balancing payment, prior PoA, payments made, credits and excess-credit/refund
   boundaries are composed without double counting.
3. Explicit HMRC charges, credits and allocations are reconciled with preserved
   provenance and completeness.
4. Expected and observed obligations match exactly or return a deterministic,
   fail-closed discrepancy.
5. Claims to reduce remain a separate customer/HMRC act, never become an
   automatic recommendation, and retain the under-reduction warning.
6. Dated remaining funding requirements and reserve gap/surplus are composed
   from explicit evidence without treating a surplus as spendable cash.
7. First-year Self Assessment produces no invented prior-year PoA and its first
   balancing/PoA timeline is represented correctly when the required evidence
   exists.
8. The stable W1 annual position is connected to cash obligations without
   duplicating liabilities, deductions, payments or credits.
9. Local/manual estimates remain visibly distinct from HMRC-confirmed amounts.
10. Missing, stale, conflicting, incomplete and temporally impossible evidence
    suppresses unsafe point results.
11. The final exact diff is independently reviewed and the integrated W1/W2
    regression suite passes.
12. Required customer-language/UX evidence confirms that annual liability,
    HMRC bill, payment timing, set-aside gap and claim-to-reduce limitations are
    not misleading.

Current gate position: items 1–10 are satisfied at bounded internal-engineering
level. Item 11 is partially satisfied: the exact S6 diff passed fresh independent
review, 320/320 relevant tests, Git integrity checks and a post-checkpoint run
in which 1,920/1,921 integrated tests passed; the one expected failure says
canonical assurance metadata is stale after legitimate production-source
advancement. Item 12, customer-language/UX evidence, remains open. This is 6 of
6 declared implementation slices complete (100%) and 10 of 12 terminal checks
fully satisfied (83%). These percentages are denominators, not launch-readiness
claims, and the local integration branch has not been merged, pushed, released
or deployed.

## Out of scope

W2 does not own general UI implementation, provider-specific connectivity,
Self Assessment filing, autonomous payment or allocation, production
activation, interest/penalty calculation, professional tax advice, or
post-launch forecasting sophistication. Dependencies on those workstreams do
not move their implementation into W2.

## Effort and immediate action

- W2 implementation remainder: none at the six-slice denominator.
- terminal engineering assurance remainder: refresh canonical assurance
  metadata against the new exact source checkpoint and rerun its freshness gate.
- external completion remainder: customer-language/UX evidence, provider and
  launch assurance under their owning workstreams.

Immediate action: keep this local integration line unmerged while the refreshed
assurance and UX gates are completed; reconcile the bounded evidence into the
Founder Control Plane without upgrading launch readiness by implication.
