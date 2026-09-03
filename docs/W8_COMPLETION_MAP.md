# W8 completion map — progressive integration

Evidence cut-off: 3 September 2026. Current integration identity:
`be978a32a55954d6fe2888c830253a35fbf9852b`. This finite map governs
completion of W8; earlier W8-S2 planning evidence does not override the
subsequently reviewed and integrated production handoffs recorded below.

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
| Approved annual/cash result through the non-persistent customer/API boundary, including missing, stale, conflicting and discrepant evidence | integrated sub-boundary; persistence remains open |
| Supported-geography admission and exact geography provenance through the customer result | integrated |
| HICBC ambiguity is non-actionable and MTD incomplete evidence fails closed | synthetic_coexistence_evidence |
| Reviewed FreeAgent invoice record, Xero invoice/observation/adapter result and QuickBooks invoice observation/adapter result coexist in one synthetic process | synthetic_coexistence_evidence |
| Provider and business source-identity substitution is rejected using actual Xero and QuickBooks observations | synthetic_coexistence_evidence |
| `october_launch_candidate()` truthfully reports `not_ready` | component_implemented |

The provider evidence proves only each unequal reviewed public boundary. It
does not claim a FreeAgent canonical adapter, enabled transport, credential,
network, customer or production capability.

## W8 delivery slices

The stable delivery denominator is exactly **5** (denominator = 5). Terminal
checks are deliberately excluded. No slice may be added or split merely to
inflate progress; authoritative scope change is required to revise the
denominator.

| # | Smallest coherent delivery slice and why needed | Current state |
|---|---|---|
| 1 | Provider-neutral canonical accounting input → annual-tax handoff; joins reviewed canonical accounting evidence to the production calculation boundary without source loss or double counting | **integrated and independently reviewed**; contextual handoff is present at `5c17c62...`, with the current exact geography/provenance reinforcement at `33aa569...`; provider acquisition remains slice 4 |
| 2 | Approved annual/cash result → customer/API/persistence handoff; makes the integrated result usable while keeping internal tax objects non-public | **partial**; the public result/API, annual-cash customer handoff and tax-year binding are integrated and independently reviewed through `a3164e7...`, but approved durable persistence is intentionally absent pending the W9 data-lifecycle boundary |
| 3 | Enforced geography admission before actionable calculation; rejects Scotland/Scottish and every unsupported jurisdiction instead of silently ignoring geography facts | **integrated and independently reviewed** at `33aa569...`; canonical artefact parity is corrected and passing at `be978a3...` |
| 4 | Enabled reviewed provider adapters and bounded customer journeys; provides the real acquisition path while preserving each provider's unequal reviewed contract | **partial, not integrated as an enabled journey**; provider contracts and several network-inert adapters are reviewed, but credential custody, authenticated transport, provider sandbox evidence and deliberate enablement remain open |
| 5 | End-to-end multi-provider/mixed-income assembly over slices 1–4; proves the complete W8 production path without duplicate economic events | **planned; correctly waiting for completed slices 2 and 4** |

Progress at the evidence cut-off is **2/5 delivery slices (40%)** at
`integrated` and independently reviewed. Slices 2 and 4 are partial and each
contributes zero until its complete boundary is accepted; slice 5 remains
planned. Synthetic/component evidence is reported separately and does not
round any remaining slice up.

## Dependencies and authority

- Slices 1 and 3 have satisfied their local implementation, review and
  integration dependencies on the current lineage. Slice 2's non-persistent
  customer/API boundary is integrated, but its persistence boundary depends on
  the approved W9 durable-data lifecycle. Slice 4 depends on the separately
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
  Slice 2's reviewed non-persistent handoff must remain protected while W9 owns
  the missing durable-data decision and implementation.
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
remaining W8 boundary spans the persistence remainder of slice 2 plus slices
4–5: at most **28–53 working days** of the original active estimate before
crediting the already-complete non-persistent S2 work. Slice 4's provider and
security queues and W9's persistence decision are the dominant elapsed-time
risks. Completed work is not rebooked as remaining effort.

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
5. Customer/API/persistence behavior uses only the approved public result and
   preserves the internal-tax non-exposure boundary.
6. Target-runtime and applicable provider-sandbox evidence passes with approved
   credentials and no synthetic-to-live inference.
7. Privacy and security review accepts data handling, secrets, access control,
   logging and retention for the exact candidate.
8. Full canonical regression and exact release-artifact parity pass on the
   current lineage; `october_launch_candidate()` no longer reports relevant W8
   blockers.
9. Independent final review accepts the combined evidence and residual risks.
10. Founder authority for merge, release and go-live is explicit and traceable.

## Historical W8-S2 assurance package

The historical W8-S2 assurance package supplied planning evidence but is no
longer the immediate checkpoint action. Its synthetic claims do not override
the reviewed production evidence for slices 1–3 and do not advance slices 4–5.

## Immediate next action

Keep slices 1 and 3 and the non-persistent S2 handoff regression-protected.
Complete slice 2 persistence only through W9's approved durable-data lifecycle.
Resume slice 4 only through the exact provider completion-map entry gates:
approved credential/token custody, authenticated disabled-first transport,
provider sandbox evidence and bounded customer journeys. Do not invent a
generic W8 adapter or begin slice 5 early to work around those gates. While
those boundaries are gated, continue other non-colliding launch-critical
packages that already have complete authority and evidence.
