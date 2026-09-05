# W8 completion map — progressive integration

Evidence cut-off: 4 September 2026. Historical integration identity:
`b8ce971f4dc6b8a1ced10e9b490be68d481752de` (tree
`7fcc5be531c5a4331e6a7ff65ce18a33e1772766`). This finite map governs
completion of W8; earlier W8-S2 planning evidence does not override the
subsequently reviewed and integrated production handoffs recorded below.

Narrow handoff/lifecycle reconciliation snapshot:
`c118dbdac2b03eeb43b386928c2416aa78fdafd3` (tree
`5ca34122142e846eb9b28a3b8553226cd11643a1`). These are immutable inspected
checkpoints, not a requirement that later integration HEAD remain fixed. This
map refresh changes no delivery state, denominator or terminal gate.

## Owned outcome and boundary

W8 owns a reviewed, fail-closed path from the already-reviewed accounting and
annual-tax contracts through annual-to-cash integration to an approved
customer-facing boundary, for the supported launch geography and enabled
providers. It must retain source identity, prohibit duplicate/double counting,
preserve HICBC and MTD uncertainty, and expose no internal tax object directly.

Out of scope are new tax policy, expanded geography or provider scope, filing,
payment initiation, billing, credential issue, production activation, and any
change to Founder authority. Live access, privacy/security assessment and
release/go-live approval are terminal evidence or authority gates, not delivery
slices.

## Assurance-state vocabulary

Every delivery slice advances monotonically through these distinct states:

- `planned` — boundary, dependencies and acceptance evidence are named.
- `implemented` — the owned production path exists.
- `locally_verified` — focused and affected local checks pass.
- `independently_reviewed` — a different reviewer accepts exact evidence.
- `integrated` — the slice is joined to its declared adjacent W8 boundaries.
- `launch_evidence_complete` — required target/live, privacy, security and
  release evidence for the slice is accepted where applicable.
- `launch_ready` — the overall terminal gate, including Founder release/go-live
  authority, has passed; this is an overall W8 state, not a local-test synonym.

`component_implemented` and `synthetic_coexistence_evidence` below describe
bounded assurance only and never advance a delivery slice.

## Achieved evidence boundaries

| Evidence boundary | Evidence state |
|---|---|
| Accounting evidence through annual tax and annual-to-cash composition, including source identity and duplicate/double-count controls | integrated |
| Approved annual/cash result through the customer/API boundary and bounded W9-S3A-D non-durable contract/adapter chain, including missing, stale, conflicting and discrepant evidence | integrated sub-boundary; persistence remains open |
| Supported-geography admission and exact geography provenance through the customer result | integrated |
| HICBC ambiguity is non-actionable and MTD incomplete evidence fails closed | synthetic_coexistence_evidence |
| Reviewed FreeAgent invoice record, Xero invoice/observation/adapter result and QuickBooks invoice observation/adapter result coexist in one synthetic process | synthetic_coexistence_evidence |
| Provider and business source-identity substitution is rejected using actual Xero and QuickBooks observations | synthetic_coexistence_evidence |
| `october_launch_candidate()` truthfully reports `not_ready` | component_implemented |

The historical coexistence evidence above proves only the unequal public
boundaries exercised at that checkpoint; it did not establish a FreeAgent
canonical adapter. Subsequently, FreeAgent's offline canonical mapper was
accepted through multiline source `bd68ab48e4394b06470c20c6035384b6f78cd1a4`,
followed by injected acquisition at `b3cd70ff93c74b679cbfce0a83f599fb0a4d9b26`.
Xero's injected acquisition component was accepted at
`7bd34870188d6150d35b0c6b77d2cdcbdba9c871`. Both are integrated at
`ea6a0fc217147471b5e247ffd9d9d220e93b37f6`. These executors use actual accepted
mapping/normalisation with synthetic dependencies; they establish neither
authenticated live acquisition nor the complete W8 customer journey.

QuickBooks injected acquisition source `bae7833982706848a210d36831a313288aefd773`
is subsequently independently accepted and integrated at
`c935df93f844af86eb820273d691827aac6e1e47`. It executes synthetic callback/full-set
rotation, CompanyInfo and Invoice requests through unchanged Q-S4/Q-S5B;
canonical ingestion remains prohibited and query mechanics remain unverified.
It must not be described as equivalent to FreeAgent/Xero canonical mapping.
This adds a bounded acquisition component, not an enabled W8 journey. Existing
W8 delivery states and denominators remain unchanged.

The W9-S3 persistence chain is now bounded through four independently reviewed
and integrated non-durable layers: S3A at
`c489c25bab669c64e1c11d28caf29fcde9678fdd`, S3B at
`110a90043dfc770c70059482be9d7b7e237749a6`, S3C integrated at
`5f5a948891e1e812a5c74ff6c7266d153bb492fa`, and S3D integrated at
`5f7b76408a5d72b71be71d0e5d6c7a6edde260b7`, followed by the exact source-
ancestry correction at `b8ce971f4dc6b8a1ced10e9b490be68d481752de`.
S3D supplies the signed-session runtime owner to S3C; it does not authenticate
or authorise the separately supplied business reference. The chain remains
pure/in-memory and does not select or operate a physical datastore, schema,
migration or durable I/O boundary.

The accepted owner-unbound W8 handoff and W9-S3A migration, source
`5ba53dccc8c608ff9c61a6913fa29704141c38a2`, are integrated at
`d3c0f53f785a4fca75e54c466032244ee2bbb2b3`. The handoff carries no user/business
identity and is `owner_authoritative=False`. S3A rejects non-exact source types
before property/descriptor access, validates the sealed handoff against exact
source/evidence/as-of/tax-year/geography context, and only then binds separately
supplied authenticated owner/business references. A caller-supplied owner-bound
customer result is not admission input. This supersedes the earlier handoff
description, not its historical evidence; it supplies neither caller
authentication nor physical persistence authority.

Accepted HICBC mutual-permission lifecycle source
`7674b2f756f621ae9a8d1fe18063f634be90c367` is integrated at
`91cb4c2f14bce089db1f92f656c8cbc1d85639b7`. Linking alone is not permission:
both users must separately affirm the four notices, with exact
link/cycle/user/year/notice/expiry binding. Current link/consent rows, not
lifecycle events, control use; withdrawal/unlink disables linked use and re-link
requires fresh mutual permission. This is bounded permission-lifecycle evidence,
not full HICBC calculation, privacy or launch acceptance; `HICBC_ENABLED` remains
disabled by default and privacy/retention/legal/target gates remain open.

The companion W9 lifecycle/handoff evidence refresh, source
`6c8703ddedbea7c6190408010bf4737062bf72cd`, is integrated at
`c118dbdac2b03eeb43b386928c2416aa78fdafd3`; see the
[W9 launch data-flow model](W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md) and
[decision dossier](W9_SECURITY_DECISION_DOSSIER.md). Its acceptance is evidence
reconciliation only. None of these three accepted packages completes W8 slice 2,
advances the HICBC/MTD synthetic-coexistence boundary, or closes membership,
physical persistence, custody, retention, provider, target, human or activation
gates.

Accepted early-W8/W10 lifecycle-composition evidence is integrated at
`584ff7f31009913706d3427c38a986bbfa6799d2`. It composes the detached S6E
payment-recovery, S6F cancellation, S6G initial pending/failed and S6H
initial-paid presentation contracts through test-only projection helpers. It
is local compatibility evidence only: it supplies no provider admission,
persistence, runtime access, customer delivery, target, accessibility or
release assurance. Neither this evidence nor the W9-S3A-D chain advances a W8
delivery-slice primary state.

Provider and geography evidence states do not advance at this cut-off. The
previously recorded provider and supported-geography boundaries retain their
existing state and every external/activation gate remains open.

## W8 delivery slices

### Subsequent accepted manual HICBC components

At clean integration `bed02d9ee30e1b18ecf6ceb50b03040aa549c736` (tree
`028119b7b769f6689a75f1369b5a04686c5dd93c`), the manual annual-source runtime
checkpoint `bb06354c597336dcff7ae963b5d2605ee14186cc` and explicit W8 boundary
correction `0e842e750daa30f94adb3f18b1e1b4f91b424aee` are integrated. Frontend
source `315248807667868ff52dffce2ab0dab599e651dc` is integrated at `bed02d9...`.
The authenticated, CSRF-protected, disabled-first non-production form submits
explicit own annual facts to the named annual-engine caller and renders only
the minimised manual HICBC view. It never publishes the internal annual result,
annual cash/reserve advice, or a stored annual position. Any active link refuses
this manual preview; linked annual-source and anti-probing work remain open.

Frontend independent re-review passed 326 affected tests, including 60 executed
JavaScript cases, and separately challenged 219 actual producer responses. Root
loopback-only synthetic browser verification exercised £703, native edit clearing
and missing-input refusal. Full internal canonical regression at `bed02d9...`
passed 7,934 root tests and all mandatory subgates; October remains `not_ready`
with 18 blockers. This does not establish human comprehension, accessibility,
privacy/legal/retention or target acceptance. The separately identified existing
claimant-`none` source-adapter defect still requires correction; it is not hidden
by this frontend acceptance. These are accepted partial components, not closure
of slice 2, the HICBC annual-integration gate, or any delivery denominator.

The stable delivery denominator is exactly **5** (denominator = 5). Terminal
checks are deliberately excluded. No slice may be added or split merely to
inflate progress; authoritative scope change is required to revise the
denominator.

| # | Smallest coherent delivery slice and why needed | Current state |
|---|---|---|
| 1 | Provider-neutral canonical accounting input → annual-tax handoff; joins reviewed canonical accounting evidence to the production calculation boundary without source loss or double counting | **integrated and independently reviewed**; contextual handoff is present at `5c17c62...`, with the current exact geography/provenance reinforcement at `33aa569...`; provider acquisition remains slice 4 |
| 2 | Approved annual/cash result → customer/API/persistence handoff; makes the integrated result usable while keeping internal tax objects non-public | **partial**; the historical public result/API and tax-year binding through `a3164e7...` are preserved; the accepted owner-unbound annual-cash handoff and S3A admission migration are integrated at `d3c0f53f785a4fca75e54c466032244ee2bbb2b3`. W9-S3A-D supplies the bounded non-durable projection/repository/adapter/runtime-owner chain through `b8ce971...` with that S3A migration, but authoritative physical owner-to-business membership, physical persistence and its lifecycle evidence remain open |
| 3 | Enforced geography admission before actionable calculation; rejects Scotland/Scottish and every unsupported jurisdiction instead of silently ignoring geography facts | **integrated and independently reviewed** at `33aa569...`; canonical artefact parity is corrected and passing at `be978a3...` |
| 4 | Enabled reviewed provider adapters and bounded customer journeys; provides the real acquisition path while preserving each provider's unequal reviewed contract | **partial, not integrated as an enabled journey**; provider contracts, canonical mapping, bounded FreeAgent/Xero injected acquisition executors and the QuickBooks observation/query-evidence executor are independently reviewed and locally integrated as components, but credential custody, authenticated transport, provider sandbox evidence and deliberate enablement remain open |
| 5 | End-to-end multi-provider/mixed-income assembly over slices 1–4; proves the complete W8 production path without duplicate economic events | **planned; correctly waiting for completed slices 2 and 4** |

Progress at the evidence cut-off is **2/5 delivery slices (40%)** at
`integrated` and independently reviewed. Slices 2 and 4 are partial and each
contributes zero until its complete boundary is accepted; slice 5 remains
planned. Synthetic/component evidence is reported separately and does not
round any remaining slice up.

## Dependencies and authority

- Slices 1 and 3 have satisfied their local implementation, review and
  integration dependencies on the current lineage. Slice 2's customer/API and
  bounded W9-S3A-D non-durable boundaries are integrated, but completion still
  depends on explicit authenticated owner-to-business membership; an approved
  physical datastore/schema and migration; atomic durable I/O; and accepted
  lifecycle/legal, retention/deletion, encryption/key-custody, access-audit,
  recovery and target-runtime evidence. Slice 4 depends on the separately
  governed provider-custody, authenticated-transport, sandbox and enablement
  gates recorded in the FreeAgent, Xero and QuickBooks completion maps. Slice 5
  depends on completed slices 2 and 4 and must not simulate either dependency
  away.
- External dependencies are provider sandbox availability, approved target
  runtime and production credentials. Their evidence is required by the
  terminal gate; this map grants none of them.
- Founder authority is required only for new/expanded scope, consequential tax
  or geography policy, material exceptions, production access or credential
  changes, and merge/release/go-live. Ordinary package sequencing, local tests
  and independent review are not Founder gates.

## Sequencing, parallelism and collision rules

- Slices 1 and 3 are complete at the integrated-engineering level and must
  remain regression-protected rather than reopened for ordinary later work.
  Slice 2's reviewed public and W9-S3A-D non-durable handoffs must remain
  protected while W9 owns the missing business-membership, physical datastore,
  durable implementation and lifecycle/target evidence.
- Provider-specific work inside slice 4 may run in parallel when it owns
  separate provider modules/tests. Changes to shared accounting contracts,
  canonical identity/normalisation or fixtures are serial and require one
  owner plus affected-provider review.
- Slice 5 is serial after slices 2 and 4 are integrated. Release evidence
  begins only on the assembled candidate.
- The annual entry point, canonical accounting contracts/normalisation,
  customer schema/persistence boundary and release gate are collision zones.
  A package touching any one must declare the owning slice and avoid concurrent
  edits to that shared surface.

## Effort and critical path

These are rough engineering ranges, not commitments. They assume existing
contracts remain stable, synthetic fixtures remain usable, and no new policy or
provider review defect is discovered. Elapsed time includes review queues but
excludes unbounded provider/Founder waits.

| Slice | Active effort | Plausible elapsed | Critical-path contribution |
|---|---:|---:|---:|
| 1 | 5–9 working days | 1–2 weeks | 5–8 working days |
| 2 | 5–9 working days | 1–2 weeks | 3–6 working days |
| 3 | 3–6 working days | 1–2 weeks | 2–5 working days |
| 4 | 15–30 working days | 4–8 weeks plus provider queues | 10–25 working days |
| 5 | 8–14 working days | 2–4 weeks | 7–12 working days |

The original effort ranges are retained as historical planning evidence. The
remaining W8 boundary spans the physical-persistence remainder of slice 2 plus slices
4–5: at most **28–53 working days** of the original active estimate before
crediting the already-complete non-persistent S2 work. Slice 4's provider and
security queues and W9's business-membership, datastore, lifecycle and target
evidence are the dominant elapsed-time risks. Completed work is not rebooked
as remaining effort.

## Geography closure

The earlier silent-ignore defect is closed on the current lineage. Exact
supported geography is admitted before actionable calculation, preserved in
the issued annual result and provenance, revalidated through accounting,
annual-to-cash and customer/API handoffs, and rejects Scotland/Scottish and
unsupported jurisdictions. Independent hostile-state review additionally
proved that a lying string subclass cannot promote Scotland as England and
that mutation/rebinding cannot turn an issued England result into an accepted
Wales result. This is integrated-engineering evidence, not authority to add
Scottish tax or evidence that provider source geography is complete.

## Overall W8 terminal completion gate

The terminal gate is **not passed**. W8 becomes `launch_ready` only when all of
these finite checks pass on one exact candidate:

1. All 5 delivery slices are `integrated` and independently reviewed.
2. Supported annual-to-cash, HICBC, MTD, provenance identity, duplicate and
   double-count fail-closed evidence passes on the assembled path.
3. Provider evidence exercises each actual enabled public contract/observation/
   adapter boundary; unsupported or disabled provider paths remain closed.
4. Geography admission rejects Scotland/Scottish and all other unsupported
   geography before any actionable result, with accepted scope positively
   tested.
5. Customer/API/persistence behavior uses only the approved public result,
   preserves the internal-tax non-exposure boundary and binds every durable
   access to authenticated owner-to-business membership.
6. Target-runtime and applicable provider-sandbox evidence passes with approved
   credentials and no synthetic-to-live inference.
7. Privacy and security review accepts data handling, secrets, access control,
   logging and retention for the exact candidate.
8. Full canonical regression and exact release-artifact parity pass on the
   current lineage; `october_launch_candidate()` no longer reports relevant W8
   blockers.
9. Independent final review accepts the combined evidence and residual risks;
   applicable human, customer-language, customer-journey and accessibility
   evidence is accepted for the exact candidate.
10. Founder authority for merge, release and go-live is explicit and traceable.

## Historical W8-S2 assurance package

The historical W8-S2 assurance package supplied planning evidence but is no
longer the immediate checkpoint action. Its synthetic claims do not override
the reviewed production evidence for slices 1–3 and do not advance slices 4–5.

## Immediate next action

Keep slices 1 and 3 and the non-persistent S2 handoff regression-protected.
Preserve the W9-S3A-D non-durable chain; do not redispatch a generic runtime-
owner adapter. Complete slice 2 only through separately reviewed owner-to-
business membership, physical datastore/schema/migration, durable I/O and the
remaining lifecycle/legal/custody/target-evidence gates.
Preserve accepted FreeAgent/Xero and QuickBooks injected executors with their
distinct mapping/observation boundaries; do not redispatch those
components. Complete the enabled slice-4 journey through the remaining exact
provider completion-map entry gates:
approved credential/token custody, authenticated disabled-first transport,
provider sandbox evidence and bounded customer journeys. Do not invent a
generic W8 adapter or begin slice 5 early to work around those gates. While
those boundaries are gated, continue other non-colliding launch-critical
packages that already have complete authority and evidence.
