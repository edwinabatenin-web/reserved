# Annual loan WP7U emission — final independent Gate U2 review

Review date: 13 August 2026  
Scope: WP9 annual-loan reconciliation emission into the adopted WP7U contract  
Decision: **PASS for WP9 Gate U2 only**

This review was limited to the two residual counterexamples in the established
stopping rule and regression of the already-passing focused scenarios. It does
not reopen statutory arithmetic assurance or approve persistence, APIs,
customer presentation or later WP7U gates.

## Final counterexample replay

### Calculated IDs without structured basis evidence

An income basis carrying `("E-BASIS",)` but no corresponding structured
`LoanBasisEvidence` now fails closed before component calculation. The producer
returns `insufficient_facts`; emission returns one inadequate,
`insufficient_facts` envelope with no point estimate. A structured evidence item
whose ID does not match the declared ID also fails closed.

A valid complete basis item is emitted with its stable ID, source reference,
subject, period and observation date. Its `original_value` and `unit` remain
null because the source record does not claim those fields; the calculated
aggregate income basis is no longer invented as the original value of each
source.

### Mixed valid plus future evidence

The producer now assigns the item-specific outside-period/timeline reason in
both rejection paths. The same future-observed item maps to `outside_period`
whether supplied alone or alongside sufficient valid evidence. Its original
amount, source and reason remain retained. Incomplete or incompatible evidence
continues to map separately to `incompatible_representation`.

## Regression evidence

All 89 focused tests passed across the WP7U adapter, reconciliation producer,
common evidence contract, composition, snapshot and internal exposure boundary.
The suite retains coverage of selected/superseded/duplicate evidence, missing
deductions, configurable stale evidence, conflict candidates and bounds,
unsupported multiple-undergraduate plans, excess-not-refund, separate Plan 2
and postgraduate envelopes, exact tax year, purpose/fitness/policy identity,
formal point/range/indeterminable effects, limitations and prohibitions.

The prior review also established that structured basis evidence and the
producer recency threshold survive composition and snapshot round-trip. The
focused regression remains green after the final remediation.

## Supported purpose and exclusions

The PASS permits the bounded WP9 component to emit separate annual Plan 2 and
postgraduate reconciliation envelopes into the adopted WP7U vocabulary for
internal integration. It covers the producer's fail-closed missing, stale,
conflicting, excess and unsupported-plan states and preserves material evidence
and limitations without a combined customer balance.

It does not approve simultaneous multiple-undergraduate calculation, a
confirmed HMRC balance, refund, filing, payment, reserve guidance, durable
persistence, public API or customer communication. Those remain prohibited or
subject to their own later gates.

## Stopping rule

The exact U2 defect set is exhausted: every supported calculation now requires
coherent structured basis provenance; unknown source values are not invented;
and exclusion classification is path-independent. Together with the 89 passing
focused cases, further review is unlikely to change this bounded component-
conformance decision.

Reopen review only if the evidence schema, selection or recency policy,
supported loan-plan scope, envelope contract/policy version, component
aggregation behavior or downstream limitations change, or a concrete
contradictory case is found.

## Verdict

**PASS for WP9 Gate U2 only.** No blocker remains within the declared internal
component-emission purpose and stopping rule.
