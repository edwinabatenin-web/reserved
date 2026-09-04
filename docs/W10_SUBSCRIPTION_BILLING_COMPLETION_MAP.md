# W10 subscription and billing completion map

## Status and authority

**Evidence cut-off:** 4 September 2026

**Original planning commit:** `b15d3fcfa423192e1a8a2e8d0a49851b366518f4`

**Current integration reconciliation point:**
`85e1250f53180bb3c1aff111c17101b9e59df080` (tree
`89a96da31b7a5dbe9bf55c01e875a0d611829e01`)

**Current status:** **S1 independently reviewed and integrated; S2A's
provider/runtime-neutral authority, S2B's four fail-closed engineering defaults,
S2C's specialist-evidence/decision classification and S2D's disabled-first
owner-bound recovery contract,
S3A's provider-neutral entitlement transition policy, S3B's detached event-inbox
contract, S4A's disabled-first Stripe edge contract, S5A's exact paid-surface
inventory, S5B's exact eleven-route reconciliation evidence and S5C's five
bounded route-hardening treatments are independently reviewed and integrated;
the initial S7A billing threat register was independently reviewed and integrated
but now requires post-convergence evidence reconciliation; S2 partially implemented;
S3, S4, S5, S6 and S7 remain partial;
0/8 slices complete on the strict accepted-evidence denominator and 0/13 terminal
checks complete; W9 remains 0/5; not launch-ready.**

This map gives the October-launch subscription and billing workstream a finite
endpoint. It is a planning and assurance control, not a provider decision,
billing policy, implementation approval, production-access request or launch
approval. `FOUNDER_DECISIONS.md` is authoritative where older material differs.

### Reconciliation provenance

This mutable map is not self-hashed. The block below binds this reconciliation
to its exact clean integration base and to immutable historical component blobs.
Later truthful map updates may preserve this block without pretending that an
older review inspected the later map text. Existing live product-source guards
remain live; this record neither replaces nor weakens them.

<!-- W10-COMPLETION-MAP-RECONCILIATION-BEGIN -->
```json
{
  "schema_version": "W10-completion-map/2026-09-04/reconciliation-1",
  "reconciliation_base": {
    "commit": "85e1250f53180bb3c1aff111c17101b9e59df080",
    "tree": "89a96da31b7a5dbe9bf55c01e875a0d611829e01",
    "parents": [
      "54a82476939dce8f75af62d73aeb477e11a1260c",
      "e3959964ca08bd5afb6f75feab4ec0fdc83a9423"
    ]
  },
  "components": {
    "W10-S2D": {
      "accepted_checkpoint": "1d70e550f685b9c1a4636caf3be75debce500219",
      "accepted_tree": "d6cad612d010baa3a311a8ecd2eabd5f9f37c37e",
      "integration_commit": "509c5360d453e23a0732e4e9d4637385eef20ef6",
      "integration_tree": "f2c35dfaaad2bf408d39b23e84716d25a0794c74",
      "paths_sha256": {
        "docs/W10_S2D_BILLING_ACCOUNT_RECOVERY_CONTRACT.md": "214e6fab5dcea9776faa8dc1cb425cbcd622698b8d62d1e0b710e11ec859f445",
        "reserved/billing/billing_account_recovery_contract.py": "b3bfc4501bdb3631bd87c9dc4aea0984b899fdd3afb535f1414cedd721f4ae06",
        "tests/test_w10_billing_account_recovery_contract.py": "7220d1d13b362d9c0c83d3e1ee37baae1fe83dc9bf3950605b919ff2d76213ee"
      }
    },
    "W10-S5C-product": {
      "accepted_checkpoint": "3c63e64e478957ce04ee1154363c2eae94b82b30",
      "accepted_tree": "ac3eb6f3028ef2e60bbd1543c1ee92f94655a0b7",
      "integration_commit": "85e1250f53180bb3c1aff111c17101b9e59df080",
      "integration_tree": "89a96da31b7a5dbe9bf55c01e875a0d611829e01",
      "paths_sha256": {
        "reserved/web/routes.py": "f1d8f6ea3730c8962899a0ffa4d7a78b8c8791693ca03c0d19e0feb8cec42bed",
        "reserved/web/v2.py": "dd4bcc1ec49793065da525fefd26709522ce12f5560fd3ee6af7b72ca27ae228",
        "tests/test_auth.py": "5dd2284eeb57dbed40119936ada5bde9c3902b21d0c0bf44cb61e55275d7b974",
        "tests/test_tax_year_context.py": "f01625359c365ca0085064e264d747e6d9d4007db0c6a34281f7666fff1d37fd",
        "tests/test_unsupported_plan_rendering.py": "5e2eae15e80a876a17bd0339526a798def1c238fbf84457178822710ef196c49",
        "tests/test_w10_internal_route_hardening.py": "20a754059b817eb33e5c83ae3edbe551c92c2bafbbbeeca39ed2c709900db3c8"
      }
    },
    "W10-S5C-evidence": {
      "accepted_checkpoint": "e3959964ca08bd5afb6f75feab4ec0fdc83a9423",
      "accepted_tree": "6e2705c4948b3b843d034beec05aef36ffb8c8ba",
      "integration_commit": "85e1250f53180bb3c1aff111c17101b9e59df080",
      "integration_tree": "89a96da31b7a5dbe9bf55c01e875a0d611829e01",
      "merge_resolution_paths": [
        "tests/test_w10_internal_route_reconciliation.py",
        "tests/test_w10_s2c_policy_evidence.py"
      ],
      "paths_sha256": {
        "docs/W10_S5A_PAID_SURFACE_INVENTORY.md": "5d1d957f53edf04898df8064ee5825a5ab9a55091daf2fed8b292f54db596601",
        "docs/W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md": "4ba7324883e6aa27081e47ffa6f1c0a1fde99a5f175375a4aae289ce5b7a5917",
        "docs/W10_S5C_INTERNAL_ROUTE_HARDENING_EVIDENCE.md": "221b244e687611dfa3e55e67051cb9ffab59ef6fcd9f02d8c5c865611439d1f5",
        "docs/W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md": "301b5e882473703acc0b0415bb492139c5ebd9dd8fcb82380517772675098ec9",
        "docs/W9_SECURITY_DECISION_DOSSIER.md": "86a2f5280786571f3afe887b5a5dcbfb6e8d37fc26b9a702d3cba4bc33cc07d6",
        "tests/test_w10_internal_route_reconciliation.py": "72574710e3d1b1f94014bf5f23eadc87f2bc4c6c80041c133e08c4190e5c6982",
        "tests/test_w10_paid_surface_inventory.py": "adf2044d4c72bb7985e4fed90ecb771aa1d88719bb39aac9ce47c70c4371b512",
        "tests/test_w10_s2c_policy_evidence.py": "3073b21cf5fdef1aaaa2178cde3dbed0b90656269fb4fe817bcb02ad2d46a781",
        "tests/test_w9_security_evidence.py": "4f114c70dd8f93d868f8a81fa2c71fcb326c63a2bbf7460671536248d7ce5397"
      }
    },
    "W10-S7A": {
      "accepted_checkpoint": "699aba7facddf935b0b71797bca0abf17628dff9",
      "accepted_tree": "24771275bdea2c24bec6768c88f6206677a5bd47",
      "integration_commit": "54a82476939dce8f75af62d73aeb477e11a1260c",
      "integration_tree": "26b1aa6a1302195770534dc41caf099bcdd7cb06",
      "paths_sha256": {
        "docs/W10_S7A_BILLING_THREAT_MODEL.md": "7a5fc31ac4569e57e91784d70a7584f7fe8f4cd702e9d2363b12b008bca38a5b",
        "tests/test_w10_billing_threat_model.py": "77b9ec4feffecd0acd8383165da8e92faffa200122479fd94a8da00879e1355b"
      },
      "post_merge_live_binding_values_requiring_reconciliation": {
        "docs/W10_S7A_BILLING_THREAT_MODEL.md": "d40a84890ae8b244d86501efda5a47e0ad51e98975139ec9000d0d7202ca8eee",
        "reserved/web/v2.py": "dd4bcc1ec49793065da525fefd26709522ce12f5560fd3ee6af7b72ca27ae228",
        "tests/test_w10_billing_threat_model.py": "89bc0d0e53d7d9eed292b7e3c351c2441722598f3a2dbcb7eb248ebe01f5b270"
      }
    }
  },
  "historical_map_bindings": [
    {
      "commit": "5612f7a33f27f09d1fa988f15dfdffbe77a72705",
      "tree": "4786614d7ea428e3aea1d61a72dc74d9aad6bd92",
      "sha256": "7af205f420c2cf3a9039fff7aad1af65e55221005231b2fabe3bd99c94f96c4d"
    },
    {
      "commit": "f9412b36adeb75dc7d5d5af56824c87235f28ce7",
      "tree": "1b648be16bdc2bc41311f7968f6d402a63d4c8a9",
      "sha256": "cd17168c04ed5c3b05044322daae2480973d57220f05c0419f539f6fdf14977d"
    }
  ]
}
```
<!-- W10-COMPLETION-MAP-RECONCILIATION-END -->

### Settled Founder authority (`FD-W10-001`)

- Reserved is a paid subscription product at the October launch.
- Initial customer-facing prices are **£29 monthly**, **£156 for six months**
  and **£288 yearly**, inclusive of VAT where applicable.
- These are initial, changeable prices rather than permanent price promises; a
  later change requires a later Founder Decision.
- The minimum ability to sell, grant and administer access is in October scope.
- Special discounts and offers must be supportable.
- Unrelated commerce, marketplace and reseller scope is not authorised.

### Settled provisional provider and lifecycle authority (`FD-W10-002` / `FD-W10-003`)

- Stripe Billing, Stripe Checkout and Stripe Customer Portal form the
  provisional disabled-first subscription baseline; Stripe Connect is excluded.
- Paid access starts only after verified successful initial payment and renews
  automatically for the selected paid plan.
- Cancellation stops future renewal while ordinary access continues through the
  already-paid period.
- The first verified failed-renewal observation enters the explicit canonical
  `payment_recovery` state for exactly seven calendar days. Ordinary access may
  continue during that bounded state; duplicate/repeated failures cannot extend
  it; verified recovery returns to ordinary paid state; unresolved expiry
  suspends ordinary access.
- No October free trial or free tier is authorised.
- Provider events and labels are observations, never direct entitlement flags.
- This authority remains provisional and does not accept provider terms, approve
  credentials, activate billing, settle VAT/invoice treatment or authorise a
  charge.

### Fail-closed defaults and genuinely unresolved subordinate policy

Six Founder-settled policy keys are explicit. Integrated S2B at
`1033c9fbef008dcd33125a0b14e7fb18b8846d19` closes four further keys only as
ordinary engineering defaults under the accepted fail-closed boundaries:
promotions/discounts remain a reserved capability but inactive; partner offers
are disabled and unsupported; ordinary mid-cycle plan changes, proration and
immediate cancellation are disabled while paid-period-end cancellation and the
mandatory statutory/consumer-rights override are preserved; and no manual
entitlement override exists, with corrections limited to append-only observation
and reconciliation with zero direct entitlement effect. These details are not
represented as separately Founder-settled policy.

For historical continuity, the preceding S2A checkpoint described
six settled policy keys and nine policy keys unresolved. The accepted S2B defaults reduce
that current unresolved remainder to five; they do not retroactively expand
Founder authority.

Exactly five policy keys remain unresolved: refunds; tax invoicing/additional VAT
presentation; the exact paid-access surface; billing-account recovery; and
post-settlement dispute, chargeback or reversal consequences. None may be
silently inferred from a provider default. They require the appropriate product,
finance/tax, legal, security and operational evidence or decision. Escalate new
scope, consequential external commitments, material exceptions and high-risk
business judgement for Founder authority; ordinary implementation detail and
review are not Founder gates.

Integrated S2C at `a07348976321df65bbd95c9170c906bcddd5baa5`
independently classifies that remainder but does not answer or close it. Exactly
three consequential customer-treatment choices require Founder answers: **Q1**,
the discretionary-refund promise and confirmed-full-refund access consequence;
**Q2**, the exact paid-access class boundary against accepted S5A; and **Q3**,
the verified post-settlement loss/restoration access consequence. Tax
invoicing/additional VAT presentation requires accepted finance/tax/legal
evidence. The owner-bound no-transfer billing-account-recovery baseline requires
accepted security/privacy/operations and target evidence. Those latter two are
specialist gates under existing authority, not new Founder questions. Until Q1,
Q2 and Q3 are answered and all applicable evidence is accepted, all five keys
remain unresolved and S2 remains incomplete.

Integrated S2D at `509c5360d453e23a0732e4e9d4637385eef20ef6`
implements only the disabled-first, owner-bound, no-transfer local decision
contract for the recovery baseline. It creates no authenticated adapter, durable
mapping, provider session, network action, entitlement, charge, refund,
transfer, merge, delegation, persistence or activation authority. Its local
contract evidence therefore narrows later implementation but does not satisfy
the remaining security/privacy/operations/target evidence or close the recovery
key.

## Baseline finding and owned outcome

W10 owns a customer-to-billing-account-to-entitlement path that can quote one
of the three authorised plans, apply an explicitly configured offer, collect
and reconcile subscription payment through a selected provider, and enforce
and administer access according to approved lifecycle policy. It must be
owner-scoped, auditable, replay/idempotency safe, fail closed under ambiguity,
and independently demonstrated in the target environment.

The repository currently has a stable authenticated `users.id` boundary and
owner-isolation tests, but authentication alone grants every protected V2 route.
The integrated S1 catalogue/authority, S2B defaults, S2D local recovery
contract, S3A lifecycle transition policy and S3B event-inbox contract now have
focused billing tests, but S2D and S3B remain detached local contracts: there is
still no durable subscription/billing or owner-to-billing-account schema,
implemented event inbox, authenticated recovery adapter, provider authenticity
or persistence, provider-verified entitlement decision, server-side paid-access
gate, provider-backed checkout/customer-portal route, billing webhook or
provider SDK. Authentication itself still lacks target-provider launch evidence.
Integrated S5A at `9c076019...` inventories the exact current route surface and
its observed access controls. Integrated S5B at `051ae665...` reconciles the
eleven internal/admin/legacy/unknown entries to bounded fail-closed treatments:
preserve five Founder-only routes and the Capital Gains hard-404, retire or
redirect three legacy public paths, and make two internal assurance/provider
pages production-404. Integrated S5C product checkpoint `3c63e64...` plus
evidence checkpoint `e395996...`, preserved through merge `85e1250...`, implements
the five bounded legacy/internal route treatments. It does not decide or enforce
the paid boundary. The initial S7A checkpoint integrated at `54a8247...`
recorded 21 open W10 billing threat/control gaps. At reconciliation base
`85e1250...`, that evidence predates S2D/S5C convergence and requires a focused
post-convergence refresh; it is not current assurance and supplies no security,
provider, target or launch assurance.

`docs/STRIPE_CONNECT_SPEC.md`, `reserved/providers/payments/base.py` and
`reserved/providers/payments/stripe_connect.py` concern the separate movement
of a customer's set-aside money. Stripe Connect is historical and unselected;
the disabled stub neither selects Stripe for subscriptions nor supplies billing
capability. Transaction-classifier uses of the word `subscription` describe a
customer's business expenses and are also unrelated. W10 may reuse general
security lessons such as signed webhooks, idempotency and reconciliation, but
must not reuse either domain contract as if it were subscription billing.

## Finite slices and evidence

| Slice | Smallest coherent outcome | Current state | Dependencies and completion evidence |
|---|---|---|---|
| **W10-S1 — authority and provider-neutral contract** | Encode the versioned initial plan catalogue and a fail-closed inventory of required policy inputs, while representing discounts/offers only as a required capability. | **Independently reviewed, checkpointed and integrated at `9e8f94a...`.** Exact authority, billing boundary, adversarial integrity and affected/full regression evidence passed. The slice remains short of launch-evidence-complete because later provider/target evidence is outside S1. | Preserve the exact integrated S1 authority and its 15-key denominator. S2 must consume its closure-bound validation/projector protocol, never mutable raw attributes or provider defaults. |
| **W10-S2 — provider and policy closure** | Record the selected billing provider and every launch lifecycle/access/promotion/invoice and post-settlement dispute/chargeback/reversal policy needed by later slices, with decision owner and rationale. | **S2A, S2B, S2C and S2D are independently reviewed, checkpointed and integrated at `5464bfac7bec6b3456d1895b2355a7e8ce86859b`, `1033c9fbef008dcd33125a0b14e7fb18b8846d19`, `a07348976321df65bbd95c9170c906bcddd5baa5` and `509c5360d453e23a0732e4e9d4637385eef20ef6`.** S2A encodes six Founder-settled keys and the provisional Stripe capability boundary. S2B closes only four ordinary fail-closed engineering defaults. S2C classifies the exact five-key remainder and supplies evidence-backed recommendations/questions, but answers none: Q1 refunds, Q2 paid-access surface and Q3 post-settlement consequences remain Founder gates; VAT/invoice and no-transfer billing-account recovery remain specialist-evidence gates. S2D implements only a disabled-first owner-bound recovery decision contract, with no runtime/provider/persistence authority or accepted specialist/target evidence. S2 remains incomplete. | Obtain authoritative answers to Q1/Q2/Q3 and accepted legal/finance evidence for refunds/post-settlement treatment, finance/tax/legal evidence for VAT/invoices, and security/privacy/operations/target evidence plus durable authenticated implementation for owner-bound recovery. Provider terms/DPA/fees also remain open. Complete only when every key is versioned and accepted and no runtime behaviour relies on an undocumented provider default. |
| **W10-S3 — durable billing and entitlement core** | Implement the owner-bound catalogue/version reference, billing account, subscription and settlement observations, event inbox, audit/reconciliation record and policy-derived entitlement boundary, including post-settlement dispute/chargeback/reversal observations without assuming their access consequence. | **S3A and S3B are independently reviewed, checkpointed and integrated at `94bd87f019dc226ec8c73f32515229189500cf06` and `5bc29bcb30c95ea7a5a9430104653b366d709eb6`.** S3A defines the provider-neutral lifecycle transition policy. S3B defines detached immutable shapes and fail-closed admission/reconciliation invariants for future owner-bound billing account, subscription, event, receipt and disposition records. S3 remains incomplete: S3B is contract-only and supplies no database schema, migration, implemented durable inbox, provider authenticity, persistence or entitlement decision. | S1 and the relevant S2 policies; accepted S3A/S3B semantics; W9 datastore, retention, encryption/key-custody and erasure decisions. Still required: durable billing-account/subscription/event-inbox/audit/reconciliation records; migrations; exclusive shared-file ownership and concurrency controls; authenticated event source; dispute/chargeback/reversal and correction/deletion/retention tests; independent schema/security/privacy review. |
| **W10-S4 — provider adapter and collection lifecycle** | Implement disabled-first provider customer/checkout/management, verified webhooks, reconciliation and offer primitives against the provider-neutral core. | **S4A independently reviewed, checkpointed and integrated at `2ad4a63dd1f10ba38859050b47245c28390667d8`: the current official Stripe Checkout, Customer Portal, webhook integrity, duplicate/order and subscription-status semantics are encoded as a disabled, network-inert, non-entitling edge contract. S4 remains incomplete.** No SDK, credential, webhook endpoint, persistence, session creation, charge or provider activation is present. | Preserve S4A's exact disabled-first boundary. Completion still requires applicable S2 policies, S3B-compatible durable identities/event inbox, approved credential custody, accepted provider terms/security boundary and sandbox access. Synthetic and sandbox tests must cover successful, declined, delayed, duplicate, replayed, out-of-order, forged, refunded, post-settlement disputed/charged-back/reversed and recovered cases. No configuration or credential alone may enable it. |
| **W10-S5 — server-side access and administration** | Apply the approved entitlement decision, including explicitly approved post-settlement dispute/chargeback/reversal consequences, to every in-scope paid surface and supply least-privilege, audited support/admin correction tools. | **S5A and S5B are independently reviewed, checkpointed and integrated at `9c0760192bb2420b90e57ec7313f69bbe52cbf74` and `051ae665a0cc94f6e9cdbbc728c621825c7769fe`; S5C product `3c63e64e478957ce04ee1154363c2eae94b82b30` and evidence `e3959964ca08bd5afb6f75feab4ec0fdc83a9423` are preserved through integration merge `85e1250f53180bb3c1aff111c17101b9e59df080`.** S5A source-binds the exact 44 always-registered and 8 HICBC-conditional routes and their provisional classes. S5B source-binds exact treatment of all 11 internal/admin/legacy/unknown entries. S5C implements five bounded legacy/internal route-hardening treatments without deciding customer paid scope. S5 is partially implemented but incomplete: Q2 remains unanswered and no paid-boundary or entitlement guard exists. | Preserve S5C's route closures. Actual paid-boundary enforcement must await the exact Q2 Founder answer against accepted S5A plus the applicable S2 policies and S3 entitlement API. Test cross-user, stale/unknown, revocation, cache, concurrency, direct-URL/API bypass and admin separation; authentication/client hiding never substitutes for server enforcement. |
| **W10-S6 — customer billing journeys** | Deliver truthful plan/offer presentation and the approved checkout, success/pending/failure, renewal/cancellation, invoice/receipt/refund, post-settlement dispute/chargeback/reversal and account-management journeys. | **Partial local implementation.** Integrated S6A–D work provides plan presentation, a safe renderer, an authenticated plans preview and an authenticated plan-selection preview (`45ade8e...`, `23d04a6...`, `3e05fb7...`, `46e2141...`). It does not provide provider-backed checkout or lifecycle journeys and is not counted complete. | Preserve those components. Completion still requires S1 catalogue; relevant S2 policy; stable S3-S5 contracts; provider-backed checkout/account-management states; exact price/VAT copy review; accessibility/browser evidence; no surprise renewal or invented refund/grace/dispute outcome; and clear recovery/support paths. |
| **W10-S7 — billing security, privacy and operations** | Close W10-specific abuse, privacy, reconciliation, monitoring, support, recovery and incident controls without duplicating W9's general control plane. | **The initial S7A checkpoint was independently reviewed and integrated at `54a82476939dce8f75af62d73aeb477e11a1260c`; post-S2D/S5C convergence evidence reconciliation is required.** S7A is an open 21-item billing threat/control/gap register only. No threat is accepted closed and no security, privacy, operations, provider, target or launch assurance is supplied; S7 implementation remains not started and the slice is incomplete. | First reconcile S7A to the current S2D/S5C lineage without converting local controls into assurance. Closure still requires S2-S6 plus W9 custody, retention, monitoring, incident and target-runtime controls; W9 itself remains 0/5. Exercise webhook/credential rotation, alerting, ledger-provider and dispute/chargeback/reversal reconciliation, outage/backlog recovery, account erasure/retention and support runbooks with redacted evidence. |
| **W10-S8 — integrated target assurance and activation** | Prove the complete paid-access journey in the launch candidate and assemble the W10 release evidence. | **Not started.** | S1-S7, launch identity and target runtime, provider sandbox/production-capable configuration and independent reviewer. End-to-end positive and failure-path evidence, final privacy/security/finance-tax review, residual-risk disposition and separate Founder authorisation for production activation/release/go-live. |

## Assurance states and stable denominator

Each slice is tracked separately as **planned**, **implemented**, **locally
verified**, **independently reviewed**, **integrated**, **launch-evidence-complete**
and **launch-ready**. “Integrated” means present in the exact launch-candidate
lineage with applicable regressions passing; it does not prove provider or
target-runtime behaviour. “Launch-evidence-complete” requires the slice's
applicable target, security/privacy, operational and commercial evidence.
“Launch-ready” additionally requires all dependent slices and the final
activation/release authority.

The stable delivery denominator is the eight slices above. A slice contributes
one only when all of its stated completion evidence is accepted; partial work
does not round up. At this cut-off **0/8 (0%)** are complete. Existing auth and
payment-boundary foundations are dependencies, not partial W10 slices. Terminal
checks are a separate **0/13** and must not be combined with the delivery
percentage. Change either denominator only if authoritative scope changes or
new evidence proves that a launch-critical outcome is absent; record the reason
rather than growing the map for ordinary fixes.

## Dependencies, parallelism and collision boundaries

1. Preserve the independently reviewed integrated S1, S2A, S2B, S2C, S2D,
   S3A, S3B, S4A, S5A, S5B and S5C boundaries. Preserve initial S7A provenance
   while its post-convergence evidence is reconciled. S2A encodes the six Founder-settled
   provider/lifecycle inputs;
   S2B closes only four fail-closed engineering defaults and leaves exactly five
   keys unresolved. S2C classifies Q1/Q2/Q3 as consequential Founder choices and
   VAT/invoice plus no-transfer recovery as specialist gates, but supplies no
   answer or external acceptance, so it does not close S2. S2D narrows recovery
   to a local owner-bound no-transfer contract but supplies no authenticated
   adapter, durable mapping or specialist/target acceptance. S3A encodes the bounded
   transition policy without claiming provider verification, persistence or enforcement.
   S3B encodes detached structural record and reconciliation invariants, not a
   durable inbox, authenticated source, persistence layer or entitlement
   decision. S4A encodes only the disabled provider edge and cannot verify a
   callback or emit entitlement. S5A is inventory evidence only; S5B reconciles
   its 11 internal/admin/legacy/unknown entries; S5C implements five bounded
   legacy/internal route treatments. None approves or enforces a paid boundary.
   Initial S7A records open threats and awaits current-lineage reconciliation.
   Provider diligence, specialist evidence
   and the three Founder answers may run in parallel, but S2 closes only through
   explicit accepted evidence.
2. Durable S3 implementation follows the relevant S1/S2 contracts and must
   preserve S3A/S3B. S4 and S5 can then run in parallel: S4 owns authenticated
   provider translation, while S5 consumes only synthetic or canonical billing
   observations and entitlement decisions. Neither may treat S3B structural
   issuance as provider authenticity or durable admission.
3. Preserve S6A–D's integrated presentation and authenticated preview work.
   Binding customer actions and the remaining provider-backed lifecycle journeys
   wait for stable S2-S5 contracts. S7 develops alongside S3-S6 and is exercised
   against their integrated result. S8 is the final serial gate.
4. One owner at a time controls `reserved/database.py` migrations and shared
   user/account deletion. Billing code should start in a new `reserved/billing/`
   boundary; provider-specific code must translate at its edge and must not
   write access flags directly.
5. Changes to `reserved/auth.py`, `reserved/web/v2.py`, shared templates/nav,
   `reserved/__init__.py`, CSP/configuration, W9 controls or release metadata
   require an enumerated integration package and the relevant workstream owner.
   No parallel package may edit the same route, migration, entitlement contract
   or price-authority record. Provider product/price IDs and secrets remain
   deployment configuration/custody concerns, never Founder authority.

Upstream contracts are the Founder authority snapshot, authenticated stable user
identity and the W9 custody/data-lifecycle/operations boundaries. External
dependencies are acceptance of Stripe terms and onboarding under the provisional
baseline (or an expressly authorised replacement), current provider documentation,
sandbox access, approved credentials/key custody, target hosting, finance/tax
review of billing VAT/invoices and independent target review. W10 is independent
of Yapily PIS/VRP and the tax calculation engine except for shared identity,
security, UI and release surfaces.

## Effort and critical path

These are planning ranges, not delivery promises. They assume two engineers can
work in parallel, prompt policy decisions, one reviewer, an established billing
provider with usable sandbox tooling, and reuse of the existing auth/W9
foundations. “Critical-path” is the likely serial contribution in working days;
external contracting/onboarding queues can extend elapsed time beyond it.

| Slice | Active effort | Likely elapsed | Critical-path contribution |
|---|---:|---:|---:|
| S1 | 2–3 person-days | 2–4 working days | 2–3 days |
| S2 | 2–5 person-days plus decision time | 3–10 working days | 3–10 days |
| S3 | 5–8 person-days | 1–2 weeks | 5–8 days |
| S4 | 6–10 person-days | 2–4 weeks | 6–10 days |
| S5 | 4–7 person-days | 1–2 weeks | 2–5 days after parallelism |
| S6 | 4–7 person-days | 1–2 weeks | 2–5 days after parallelism |
| S7 | 4–7 person-days | 1–2 weeks | 2–5 days after parallelism |
| S8 | 5–8 person-days | 1–3 weeks | 7–12 days |

Total active effort is roughly **32–55 person-days**. A conservative elapsed
range is **7–14 weeks** with the assumed parallelism; the serial critical path
is roughly **29–58 working days** before any longer external queue is known.
Provider terms/final acceptance and onboarding, credentials or sandbox queues are the largest
schedule risks and may extend elapsed time beyond fourteen weeks; they are not
disguised inside the engineering estimate.

## Finite terminal W10 gate

W10 is complete only when all thirteen checks pass:

1. The three current plans and customer-facing prices match the applicable
   Founder authority version, use GBP exact-money representation, and show VAT
   inclusion where applicable without inventing a VAT rate or applicability.
2. Every required renewal, cancellation, failed-payment/grace, entitlement,
   refund, post-settlement dispute/chargeback/reversal, invoice, offer/discount,
   partner-offer, access and override behaviour is explicit and approved by its
   appropriate owner.
3. A billing provider is explicitly selected and its commercial, legal,
   technical, security and data-processing boundary is accepted; historical
   Stripe Connect or Yapily payment material is not treated as that selection.
4. Billing accounts, events, subscriptions, settlement reversals/disputes and
   entitlements are owner-bound, versioned, auditable, idempotent, order-safe
   and reconcilable; provider state is never copied directly into an unaudited
   access flag.
5. Signed provider callbacks, checkout/management returns and reconciliation,
   including post-settlement dispute/chargeback/reversal events, resist forgery,
   replay, duplication, delay, reordering, cross-user access and uncertain
   status, and fail closed without losing recoverability.
6. Every paid launch surface is enforced server-side under the approved access
   policy, including the approved consequences of a post-settlement dispute,
   chargeback or reversal and access through direct URLs and APIs; support/admin
   access and corrections are least-privilege and auditable.
7. Purchase, offer, pending, success, renewal, cancellation, failure, recovery,
   invoice/receipt, refund and post-settlement dispute/chargeback/reversal
   journeys behave and communicate exactly according to approved policy across
   supported browsers and accessibility checks.
8. Special discounts/offers are demonstrated without allowing unapproved price,
   duration, stacking, eligibility or entitlement consequences; partner offers
   remain disabled until their handling is explicit.
9. Billing VAT determination, customer presentation, invoice/receipt content,
   finance reconciliation and refund/dispute/chargeback/reversal accounting pass
   the applicable finance/tax review; VAT-inclusive price authority alone is not
   treated as tax advice.
10. Billing personal data, provider identifiers and credentials follow approved
    minimisation, retention, erasure, encryption/custody, log-redaction and
    account-recovery controls.
11. Monitoring, alerting, webhook backlog recovery, provider-ledger and
    post-settlement dispute/chargeback/reversal reconciliation, outage
    degradation, credential rotation and incident/support runbooks are exercised
    in the intended environment.
12. The exact launch candidate passes local regression, provider sandbox,
    end-to-end identity-to-access, negative/failure, privacy, security and
    operational assurance with traceable redacted evidence and independent
    review.
13. Residual risks are explicitly accepted and the separate Founder gates for
    production access, payment authority, activation, merge/release and go-live
    are recorded. No credential, provider dashboard setting or green local test
    can grant launch status by itself.

## Current next action

W10-S1, S2A, S2B, S2C, S2D, S3A, S3B, S4A, S5A, S5B and S5C are independently
reviewed and integrated. The initial S7A checkpoint is integrated, but its
evidence predates S2D/S5C convergence and must be reconciled before it can be
treated as the current W10 billing threat register.
S2A records the six Founder-settled provider and paid-lifecycle decisions. S2B
closes only the four accepted fail-closed engineering defaults and preserves the
exact five unresolved keys. S2C classifies the remaining evidence and decision
owners without answering or closing a policy: Q1 refunds, Q2 paid surface and Q3
post-settlement consequences remain unanswered Founder questions; VAT/invoice
treatment and owner-bound no-transfer billing-account recovery remain specialist
evidence gates rather than new Founder questions. S2D supplies the bounded local
owner-bound recovery contract, not its authenticated/durable adapter or external
acceptance. S3A remains the provider-neutral transition policy;
S3B is only the detached record/admission/reconciliation contract and provides
no durable inbox, provider authenticity, persistence or entitlement decision.
S4A remains a disabled provider-edge contract with no runtime adapter, signature
verification or activation. S5A supplies the exact source-bound route inventory
and minimal paid-surface decision question, but no boundary approval or
server-side entitlement enforcement. S5B supplies the exact source-bound
reconciliation of its 11 internal/admin/legacy/unknown routes and no new Founder
question, but changes no route and does not start S5.

S5C has now implemented the five accepted legacy/internal hardening treatments
without changing Founder-only scope, choosing a paid boundary or enforcing
entitlement. This makes S5 partial, not complete. The focused S7A evidence
reconciliation is the immediate documentation dependency created by the merged
S2D/S5C lineage; it must retain all 21 threats as open unless separate accepted
evidence closes one.

The next S2 work is accepted specialist evidence for the enumerated refund,
VAT/invoice, recovery and post-settlement gates plus authoritative answers to
Q1, Q2 and Q3, followed by one versioned closure record for all 15 keys. The
pre-Q2 route cleanup is complete at S5C and is not redispatch authority. After Q2
and the applicable S2/S3 dependencies, the smallest
server-side paid-boundary design may consume a synthetic canonical entitlement
decision; it still implements no provider path. A
durable S3 implementation may proceed only when its datastore, migration
ownership, retention/erasure, key-custody, minimisation, authenticated-source and
independent-review dependencies are accepted; it must implement rather than
merely relabel S3B. Further provider-edge S4 implementation must preserve S4A,
proceed only against current authoritative technical evidence and remain
disabled-first.

No provider adapter, credential, persistence migration, access grant or checkout
package follows merely from the S1 contract. Provider-specific implementation
waits for a selected provisional provider boundary and applicable external
evidence. Preserve the accepted non-durable S3A/S3B contracts. Further durable
entitlement/event-inbox implementation requires the approved W9
custody/data-lifecycle boundary as well as the explicit lifecycle decisions.

## Explicitly out of scope

This map does not authorise set-aside PIS/VRP or other customer money movement,
marketplace/reseller/affiliate commerce, merchant acquiring for third parties,
multi-currency or non-UK expansion, tax-return/VAT-return functionality, a free
tier or trial, account sharing/team seats, bespoke enterprise billing, dunning
optimisation, or post-launch pricing experiments. It does not select a provider,
amend Founder Decisions, modify the Control Plane, access production or sandbox
accounts, handle credentials, charge money, merge, deploy or go live. A required
launch policy may describe a deliberately unsupported case; unsupported
sophistication does not create another slice unless authoritative scope changes.

**Map disposition:** **S1 independently reviewed and integrated; S2 partially
implemented with independently reviewed/integrated S2A, S2B, evidence-only S2C
and contract-only S2D, six Founder-settled keys, four fail-closed engineering
defaults and exactly five policy keys unresolved, with Q1/Q2/Q3 unanswered and
VAT/invoice plus no-transfer recovery still awaiting specialist acceptance;
S3 partially
implemented with independently
reviewed/integrated S3A and detached contract-only S3B but no durable inbox,
provider-authenticated source, persistence or enforcement boundary; S4 partially
implemented with independently reviewed/integrated S4A but no runtime adapter,
signature verification, persistence or activation; S5 partially implemented,
with independently reviewed/integrated S5A inventory, S5B 11-route reconciliation
and S5C five-treatment hardening, but no approved paid boundary or enforcement;
S6 partially implemented/integrated; initial S7A is integrated open-gap evidence
requiring post-convergence reconciliation and supplies no assurance; strict
completion remains 0/8 and the terminal gate remains 0/13 pending S2 policy
closure and every slice's remaining completion evidence.** W9 remains 0/5.
Provider, target,
specialist-review, residual-risk, Founder activation/release and launch authority
gates remain open.
