# Early W8 progressive integration assurance

Package: `reserved-early-w8-progressive-integration-assurance`

This bounded synthetic package exercises adjacent provider, annual/cash and
presentation safeguards on the same clean integration lineage. It is
coexistence and regression evidence, not an implemented cross-workstream data
flow. It does not connect or activate a provider, alter production code, create
a payment instruction, or declare launch readiness.

## Assured boundary

The focused tests establish that:

- QuickBooks observation and adapter evidence retains provider provenance,
  allocates £50 of an £80 payment, preserves the remaining £30 as unapplied, and
  derives partial settlement from the allocation rather than the provider's
  balance assertion;
- malformed or internally inconsistent provider evidence fails before it can
  become a canonical fact;
- the reviewed W1 annual-position to W2 obligation/funding chain produces dated
  obligations from complete synthetic evidence;
- discrepancies and explicit review-required states suppress customer-visible
  monetary results;
- reserve surplus remains labelled non-spendable and the presentation retains
  the no-payment-authority boundary.

## Deliberately unconnected boundary

The provider and W1/W2 tests construct separate synthetic facts; they do not
demonstrate an accounting-to-tax handoff or end-to-end provider data flow. The
canonical accounting package remains synthetic and provider-neutral. The
production tax engine does not consume `CanonicalAccountingTaxInput`, and the
provider implementations remain disabled. This is an existing fail-closed gate,
not an integration defect to repair inside early W8. A later, separately owned
and reviewed package must define any production accounting-to-tax handoff.

The W2 customer-language tests use the existing test-only copy adapter. There is
no production API, persistence or customer activation in this package. Provider
activation, customer data, filing, payment initiation, release and deployment
remain outside scope.

## Evidence interpretation

Passing tests are early integration evidence for contract compatibility and
fail-closed behaviour on this exact lineage. They are not evidence of live
provider behaviour, customer comprehension, production security, release
readiness or regulatory approval. Individual source checkpoint provenance must
remain intact during any later integration checkpoint.
