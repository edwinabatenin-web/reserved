# Early-W8 / W10 subscription-lifecycle composition evidence

## Bounded result

This package proves deterministic local compatibility between the currently
accepted detached W10 entitlement-state candidate and the S6G initial
pending/failed, S6H initial-paid, S6E payment-recovery and S6F cancellation
presentation candidates. It exercises only their public APIs through explicit
**test-only projection** helpers. Those helpers are not production admission,
are not shipped runtime code and must not be copied into a live adapter.

The composition covers the authorised lifecycle from no entitlement, through a
structural initial-payment-success transition, paid and cancellable paid
postures, first failed-renewal recovery, a structural renewal-success after
recovery, and unresolved recovery expiry. It also verifies that
browser/provider labels, altered boundaries, inconsistent provenance and
cross-owner/subscription facts fail closed. Plan matching is tested only inside
S6H's presentation-local expectation contract; trusted selected-plan
provenance is unavailable in this composition.

This is early-W8 local contract evidence. It does not prove provider admission,
webhook authentication, persistence, runtime access control, customer delivery,
target-runtime behaviour, sandbox or production integration, external evidence,
release or launch readiness. It does not close W8 or W10 and preserves the
existing completion denominators.

## Exact integration baseline and sources

**Candidate base commit:** `8fdcc0414c72393c4f575f7597bd30850b707d35`

**Candidate base tree:** `773aea8429967dc086ac0ced2f38302b8998fc7c`

| Exact public source | Last integrated checkpoint at the base | SHA-256 at the base | Use in this package |
|---|---|---|---|
| `FOUNDER_DECISIONS.md` | `10fb93e2e6ab567a72d2370c1603768a7ac04bb5` | `03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4` | Exact FD-W10-003 initial access, renewal, recovery and cancellation boundary; never runtime authority |
| `reserved/billing/entitlement_core.py` | `48a97042fc0e17997bf2d23a4687e79c20b74b9e` | `201c92c1093b663b786a5e49a1c2ca0d714f3fe6fdaebf18c0c7d486ef25f415` | Detached structural lifecycle and ordinary-access candidates; never provider or runtime authority |
| `reserved/billing/initial_payment_presentation.py` | `2690c9335ca8073b1723846cccf33c15f9ff727f` | `009970f3217bee7dddc59471f02ce801d8992e7d92b951f41a7ee97cc2bd5451` | S6G fixed pending/failed copy with paid access not started |
| `reserved/billing/initial_paid_presentation.py` | `8fdcc0414c72393c4f575f7597bd30850b707d35` | `cdb3d75d109bcaabe281f07f22675b785d40406bca685f6892b3085c45208b6d` | S6H fixed paid-start and automatic-renewal copy |
| `reserved/billing/payment_recovery_presentation.py` | `11ea4cfea78ae31b633a9ac8d99477eb358e7f3b` | `48d49f28136690f5be8a6cdf0dd927f9e3f0d0ffa0972d1daa0b60f5f23c42e8` | S6E exact seven-day recovery boundary copy |
| `reserved/billing/cancellation_presentation.py` | `fd7f30dcdc3557ef70c9bdfc4b89e046e16c2bd0` | `0f8d252f6a5556333187856e527fcdf02197572baebef1a0edc4c71999d0946d` | S6F paid-period-end cancellation copy |

The hashes bind this evidence to the exact APIs reviewed together. They do not
authenticate any observation or caller and do not create runtime authority.

## Explicit test-local projection boundary

The entitlement candidate represents lifecycle facts as calendar dates. The
presentation candidates use exact UTC-second timestamps. To exercise the APIs,
the tests visibly invent all of the following synthetic timestamp facts:

- `entitlement_started_on` becomes both payment-verification and
  entitlement-effective time at `00:00:00Z`;
- the initial-paid evaluation time becomes that timestamp plus 4 minutes and
  59 seconds;
- inclusive `paid_through` becomes paid-through-exclusive and next-renewal at
  `00:00:00Z` on the following calendar day;
- recovery start, recovery deadline and the selected recovery evaluation date
  become `00:00:00Z` on their respective dates;
- the actual final `CANCELLATION_CONFIRMED` history date becomes the synthetic
  cancellation-verification time at `09:14:07Z`, and cancellation evaluation
  becomes `09:14:07Z` on a caller-requested date that may not predate that
  event; and
- `entitlement_started_on` becomes cancellation paid-period start at
  `00:00:00Z`, while cancellation effect uses the synthetic exclusive paid
  boundary above.

These are test inventions, not recovered provider facts or recommended
production derivations. No production code is changed. A future admitted
adapter must own and verify all timestamp semantics explicitly.

Every input derived from an entitlement candidate is first validated through
the entitlement module's public structural validator and checked to retain all
exact-false provider, provenance, persistence and runtime-access authorities.
The caller-selected recovery and cancellation evaluation dates, the S6H
synthetic exact-true prerequisites and the test plan reference are not derived
from `entitlement_core`. Presentation builders separately exact-validate those
synthetic inputs, but that validation supplies no provider, selected-plan or
provenance authority. Every resulting presentation is projected through its
public validator and checked to retain all exact-false presentation
authorities.

## Compatibility and fail-closed coverage

The focused package proves:

1. Each S6G pending and failed output says paid access has not started, carries
   zero authority and is rejected when supplied to either entitlement API.
   There is no admission or composition adapter between S6G and entitlement
   state in this package; no causal state effect is claimed.
2. An exact structural initial-success observation can produce the detached
   paid candidate, but entitlement core does not prove provider reconciliation,
   canonical observation, or plan provenance. The candidate remains explicitly
   unauthenticated and has no runtime-access authority. Browser returns,
   Checkout labels, generic `paid`/`active` labels and provider status strings
   cannot substitute for the exact S6H facts.
3. The test-only S6H helper additionally requires direct, sole
   `INITIAL_PAYMENT_CONFIRMED` history and rejects a paid state restored after
   recovery. It assumes S6H's exact-true reconciliation and canonical-state
   booleans solely as synthetic prerequisites for exercising that presentation
   API; it does not derive them from entitlement authority. S6H is compatible
   only with the exact paid, automatically-renewing posture and a future
   paid-through-exclusive timestamp that exactly equals the supplied
   next-renewal timestamp. Plan coverage proves only local equality with S6H's
   independently supplied expected reference; trusted selected-plan provenance
   remains unavailable.
4. Cancellation preserves the already-paid entitlement period while setting
   automatic renewal false. S6H then becomes ineligible; S6F alone describes
   the stopped-renewal structural posture before the exact exclusive boundary,
   and remains zero authority. The cancellation timestamp projection is bound
   to the actual final cancellation history date and cannot predate it. Both a
   later renewal success and failure are rejected, and the paid remainder
   materialises to suspended at its boundary.
5. The first failed renewal creates `payment_recovery` for exactly seven days.
   Duplicate application of the same event is idempotent and cannot extend the
   deadline. A distinct failure before the deadline also cannot move its start
   or deadline; distinct failures at and after the deadline suspend rather than
   extend recovery. Ordinary access is structurally true from recovery start
   through the day before the exclusive deadline and false at the deadline.
   S6E displays the identical exclusive boundary and remains zero authority.
6. A structurally valid later renewal-success observation restores paid state
   and clears recovery dates without turning the detached state into provider,
   persistence or runtime authority.
7. Materialising the unresolved recovery deadline suspends ordinary access.
   The S6E and S6F builders reject construction facts evaluated at their
   exclusive boundaries. Already-emitted S6E/S6F candidates do not retain an
   evaluation timestamp, accept an as-of time or become freshness-bearing when
   revalidated: projector success cannot establish replay freshness or safe
   rendering.
8. Presentation tuples cannot be supplied back to the entitlement transition
   or validator and every presentation authority field remains exact `false`.
9. Cross-owner and cross-subscription facts, S6H-local expected-plan mismatch,
   altered renewal boundaries and reused event IDs with changed provenance fail
   closed.

## Deliberate residual gates

`BillingObservationCandidate` is a structural shape, notwithstanding the
compatibility alias retained in its public API. This package does not establish
that a payment or cancellation occurred, that an observation was reconciled or
canonical, or which plan was selected. Exact-true S6H structural confirmations
are prerequisites to be established by a future independently admitted
adapter; the test-only projection assumes them solely to exercise S6H. The
entitlement candidate does not supply those authorities.

No presentation output grants access, changes entitlement, authenticates a
provider event, admits provenance, persists state, renders or delivers copy,
sends notifications, charges or refunds money, or activates billing. The local
ordinary-access value is itself a structural decision candidate whose
`runtime_access_authority` remains exact `false`.

S6E and S6F validate freshness only while constructing a candidate from input
facts. Their emitted candidates deliberately omit evaluation time. Revalidation
therefore checks deterministic structure, not current freshness, replay safety
or render eligibility. A future delivery boundary must re-establish current
admitted state and time; these outputs must not be treated as safely replayable
because a projector accepts them.

Still open are provider/webhook authentication, deterministic admitted-event
reconciliation, durable lifecycle persistence, live access-control integration,
customer authentication and delivery, Stripe sandbox evidence, provider/legal
activation evidence, target-runtime journeys, accessibility, broader W8/W9
assurance, release and go-live.

## Candidate ownership

Only these new paths are authorised:

- `tests/test_w8_w10_subscription_lifecycle_composition.py`
- `docs/W8_W10_SUBSCRIPTION_LIFECYCLE_COMPOSITION_EVIDENCE.md`

The candidate stops uncommitted for fresh independent review.
