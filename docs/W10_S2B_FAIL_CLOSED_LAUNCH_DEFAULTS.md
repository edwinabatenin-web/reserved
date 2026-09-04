# W10-S2B fail-closed launch-default authority

## Result and boundary

W10-S2B is a contract-only, provider/runtime-neutral authority for four narrow
ordinary engineering defaults already supported by the accepted W10 lineage.
It does **not** claim that the Founder separately settled these details, and it
does not complete W10-S2. The overall status remains `policy_incomplete`.

The producer issues an opaque handle. Trusting consumers retain that handle and
use the captured validator/projector protocol. Its projection contains detached
exact built-in immutable values only. Public globals, class metadata,
descriptors, ordinary reconstruction hooks, or mutable registry entries cannot
reauthorise changed content.

## Exact accepted provenance

The contract binds the exact clean integration HEAD
`5bc29bcb30c95ea7a5a9430104653b366d709eb6` and these accepted artifacts:

| Slice | Integration identity | Source | SHA-256 | Authority/contract identity |
|---|---|---|---|---|
| W10-S1 | `9e8f94a9906f0c9d5c85b47223d20c34be499e1c` | `reserved/billing/contracts.py` | `9c5dce7a81652d58562ca339def95fba7cbb2d1c02f965618ebd8f40bcad202b` | `FD-W10-001/2026-09-02/v1` |
| W10-S2A | `5464bfac7bec6b3456d1895b2355a7e8ce86859b` | `reserved/billing/provider_lifecycle_authority.py` | `fc21c3a0f9d8d7eeb9a06bcbf5fc4a418568fe06aa5f65f47c325d8ecfde834a` | `FD-W10-002+FD-W10-003/2026-09-04/v1` |
| W10-S3A | `94bd87f019dc226ec8c73f32515229189500cf06` | `reserved/billing/entitlement_core.py` | `b46b797614b57047e64f6f6597b1c788b9ab15db90653b07add31b4bbb03cb3b` | `reserved-w10-entitlement-transition/1.0` |
| W10-S3B | `5bc29bcb30c95ea7a5a9430104653b366d709eb6` | `reserved/billing/event_inbox_contract.py` | `4dc0b6bb8b109854531dc1b9d492255e98dca805822cd5e0257f0fdf9b0ca8ed` | `reserved-w10-event-inbox-contract/1.0` |
| W10-S4A | `2ad4a63dd1f10ba38859050b47245c28390667d8` | `reserved/billing/stripe_disabled_first_contract.py` | `87a84c5ec77f25e12667b5466052b4a84ee6e01a6b075df643202d95aec98638` | `W10-S4A/2026-09-04/v1` |

The hashes are build-time provenance assertions, not runtime file reads. A
reviewed source change requires an explicit provenance refresh.

## Four fail-closed defaults

These outcomes are classified as ordinary engineering defaults under the
accepted fail-closed boundaries:

1. **Promotions and discounts:** future capability remains reserved, but there
   are no active promotions, codes, eligibility rules, durations, stacking
   rules, or discounted prices. Promotions have zero direct entitlement effect.
2. **Partner offers:** disabled and unsupported. There is no offer definition,
   marketplace, or reseller path and no direct entitlement effect.
3. **Plan changes and proration:** for ordinary product/customer plan-change and
   cancellation behaviour, mid-cycle changes, proration, and immediate
   cancellation are disabled. FD-W10-003's already-settled cancellation at the
   end of the paid period remains unchanged. The fixed
   `mandatory_statutory_and_consumer_rights_override=True` boundary means these
   ordinary defaults never displace mandatory statutory or consumer rights. It
   does not select a refund policy or any further legal outcome.
4. **Manual overrides:** no manual entitlement override or direct mutation is
   available. A future correction may only be an append-only observation and
   reconciliation input with zero direct entitlement effect.

Provider configuration is not policy authority and provider observations are
not entitlement decisions.

## Policy remains incomplete

The six S2A Founder-settled keys plus these four defaults still leave exactly
five unresolved keys:

- `refunds`;
- `tax_invoicing_and_additional_presentation`;
- `paid_access_surface`;
- `billing_account_recovery`;
- `post_settlement_dispute_chargeback_reversal_consequences`.

W10-S2B does not select an outcome for any of them. Specialist evidence and the
genuine Founder decisions identified by the W10-S2 reconciliation remain gates.

## Deliberate exclusions

There is no SDK or network use, credential/configuration input, provider
activation, database or file I/O, persistence, route or paid-access enforcement,
webhook handling, refund action, VAT/invoice outcome, account recovery,
post-settlement access consequence, or entitlement mutation. This component is
not an inbox, adapter, policy-complete S2, or launch implementation.

## Assurance

Focused tests bind the five source hashes and exact 15-key partition; prove all
four enabling controls remain off; preserve the five unresolved keys; and cover
direct construction, subclassing, public/global/class/descriptor rebinding,
ordinary and authoritative copying, pickle/reconstruction, validator-code
substitution, registry corruption, generation-safe weak-reference cleanup,
stale callback/id-reuse safety, detached immutable projections, absence of I/O,
and absence of provider/database/route dependencies. The build-time copy probes
and 1,000-copy stress regression both return the private registry to the single
live canonical handle; collected handle state is not retained.

## Post-entitlement-core reconciliation

The S3A row remains the exact historical source bound by this package. Its
accepted hardened source checkpoint is `b990d514a929c37b3f999137a0e383d05c37f0df`,
integrated as `48a97042fc0e17997bf2d23a4687e79c20b74b9e`, and current SHA-256 is
`201c92c1093b663b786a5e49a1c2ca0d714f3fe6fdaebf18c0c7d486ef25f415`.
The core now supplies only detached zero-authority structural lifecycle
candidates with fixed history/date behaviour. It changes no default, settles
none of Q1/Q2/Q3, and supplies no provider, target, persistence or activation
evidence.
