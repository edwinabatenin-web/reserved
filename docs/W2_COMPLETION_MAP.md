# W2 completion map

Evidence cut-off: 31 August 2026. This map declares the endpoint of the
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

These checkpoints are not, by themselves, evidence of final W1 integration,
customer validation, provider readiness, Control Plane reconciliation, or
launch readiness.

## Remaining implementation slices

### S6 — final annual-to-cash integration contract

Own the narrow adapter/composition boundary from the stabilised W1 annual
position into S1 balancing/PoA and the S3/S5 cash-obligation outputs. It must
prevent double counting and retain the distinction between annual tax
liability, tax already deducted or paid, HMRC-recorded cash obligations, PoA,
and remaining funding requirement.

S6 must wait for the supported W1 annual-position scope and contract to be
stabilised. W2 must not invent a competing annual-liability model while it
waits. Contract fixtures and collision analysis may proceed in parallel, but
the final integration must consume the agreed W1 boundary.

No S7 implementation slice is currently justified. Customer testing,
integrated assurance and Control Plane reconciliation are completion gates, not
new product slices.

## Dependencies and parallelism

| Item | W1 dependency | W2 dependency | External dependency | Sequencing |
|---|---|---|---|---|
| S5 | None; it consumes already-derived obligations | S1–S3 | None for the pure component | Complete at its independently reviewed local checkpoint |
| S6 contract fixtures | Uses the current W1 shape provisionally | S1–S5 | None | May proceed read-only/in fixtures while W1 stabilises |
| S6 final integration | Stable supported W1 annual-position contract | S1–S5 | None | Serial after the W1 boundary is agreed |
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

Current gate position: items 1–6, 9 and 10 are satisfied at bounded-component
level; items 7–8 remain final integration work; items 11–12 remain final
assurance evidence. This is 5 of 6 declared implementation slices complete
(83%) and 8 of 12 terminal checks satisfied at their present required level
(67%). The percentages are denominators, not launch-readiness claims.

## Out of scope

W2 does not own general UI implementation, provider-specific connectivity,
Self Assessment filing, autonomous payment or allocation, production
activation, interest/penalty calculation, professional tax advice, or
post-launch forecasting sophistication. Dependencies on those workstreams do
not move their implementation into W2.

## Effort and immediate action

- S6: approximately 0.5–1.5 active days after the W1 contract stabilises.
- final integrated review/tests: approximately 0.5–1 active day and may be
  prepared in parallel.
- likely elapsed remainder: approximately 1–3 working days after the W1
  dependency is available; provider and customer evidence may extend launch
  elapsed time without extending W2 implementation.

Immediate action: prepare exact S6 contract fixtures and collision analysis
without changing W1 or freezing the adapter. Do not begin final S6 integration
until the W1 annual-position boundary is explicitly stable.
