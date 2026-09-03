# W8-S2C annual/cash customer-handoff evidence

This bounded candidate adds one pure, network-inert handoff from the reviewed
annual-to-cash producer to the reviewed W2 customer-language and W8 public
result contracts. It adds no route, template, storage, provider access,
calculation, filing, payment authority or activation.

## Producer authority and provenance

The handoff accepts only an exact, live producer-issued `AnnualToCashPosition`.
It calls the public read-only `annual_to_cash_position_identity()` and
`annual_to_cash_position_provenance()` capabilities before reading any nested
facts, and calls both again before exposing a public result. Directly
constructed, replaced, copied, reconstructed, mutated and coherently forged
positions therefore fail closed. The handoff receives no issuance capability
and makes no claim against arbitrary interpreter, closure or frame access.

The customer-facing evidence tuple must exactly equal the complete ordered set
of opaque source identities supported by the producer graph and provenance:
annual evidence, deductions/credits evidence, prior-PoA evidence, payment
source identities, account charges/credits/allocations and set-aside evidence.
Where one upstream source record supports several distinct HMRC charges, its
source reference is retained once in deterministic first-occurrence order, as
required by the public W8 contract. Derived content digests are not
misrepresented as source references.

## Projection semantics

Only producer-issued actionable states may render. Review-required and
unresolved states return the categorical value-free result `None`. Both
actionable producer status names are presented as
`QUALIFIED_LOCAL_ESTIMATE`: the annual liability is locally calculated and is
never promoted to an HMRC-confirmed or exact claim.

The projection copies, without recalculation:

- final Self Assessment liability;
- each balancing-payment and Payment-on-Account amount and due date;
- deductions/credits, prior PoA, payments made and credit/refund position;
- exact funding gap, exact coverage or reserve surplus;
- the complete source-reference tuple.

The existing W2 language contract retains customer wording. The existing W8
public result retains supported geography, ownership, immutable-result and
no-payment/no-transfer controls. A surplus remains explicitly unavailable and
not spendable.

## Rebinding and hostile-state controls

The implementation closes over the genuine producer readers, public composer,
exact date/decimal types, constructors, enum members and monetary constants. Rebinding their
module names cannot rehabilitate an altered value or replace the public
composer. Exact top-level type rejection occurs before any hostile subtype
hook can run. Producer identity then validates the complete nested graph and
provenance before projection.

## Compatibility boundary

Exactly two compatibility consumers are adjusted. They allow the exact,
resolved regular file
`reserved/services/w8_annual_cash_customer_handoff.py` to reference only the
already-authorised annual-to-cash markers. Every other service, web, API,
database and model path remains prohibited, and persistence remains absent.

## Status

This is an implementation candidate for fresh independent review. Passing
tests do not establish acceptance, integrated W8-S2 completion, target-runtime
evidence or launch readiness.
