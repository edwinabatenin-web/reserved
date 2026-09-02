# W8 completion map — progressive integration

Evidence cut-off: 2 September 2026. This finite map governs completion of W8;
the W8-S2 package is assurance evidence for the existing lineage and does not
itself deliver the missing production handoffs.

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
| Annual-to-cash composition, including source identity and duplicate/double-count controls | synthetic_coexistence_evidence |
| Missing, stale, conflicting and discrepant evidence fails closed | synthetic_coexistence_evidence |
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
| 1 | Provider/canonical accounting input → annual-tax handoff; joins reviewed accounting evidence to the production calculation boundary without source loss or double counting | planned |
| 2 | Approved annual/cash result → customer/API/persistence handoff; makes the integrated result usable while keeping internal tax objects non-public | planned |
| 3 | Enforced geography admission before actionable calculation; rejects Scotland/Scottish and every unsupported jurisdiction instead of silently ignoring geography facts | planned |
| 4 | Enabled reviewed provider adapters and bounded customer journeys; provides the real acquisition path while preserving each provider's unequal reviewed contract | planned |
| 5 | End-to-end multi-provider/mixed-income assembly over slices 1–4; proves the complete W8 production path without duplicate economic events | planned |

Progress at the evidence cut-off is **0/5 delivery slices** at `integrated` or
beyond. Synthetic/component evidence is reported separately and does not alter
that denominator.

## Dependencies and authority

- Slice 1 depends on the current canonical accounting tax-input/source-
  observation contracts and annual-position contract. Slice 2 depends on slice
  1 and the existing annual-to-cash output. Slice 3 depends on an authoritative
  supported-geography rule and must precede any actionable route. Slice 4
  depends on reviewed provider contracts plus approved credentials/sandboxes.
  Slice 5 depends on slices 1–4.
- External dependencies are provider sandbox availability, approved target
  runtime and production credentials. Their evidence is required by the
  terminal gate; this map grants none of them.
- Founder authority is required only for new/expanded scope, consequential tax
  or geography policy, material exceptions, production access or credential
  changes, and merge/release/go-live. Ordinary package sequencing, local tests
  and independent review are not Founder gates.

## Sequencing, parallelism and collision rules

- Slices 1 and 3 may proceed in parallel because their contract boundaries are
  independent. Slice 2 follows the stable output from slice 1.
- Provider-specific work inside slice 4 may run in parallel when it owns
  separate provider modules/tests. Changes to shared accounting contracts,
  canonical identity/normalisation or fixtures are serial and require one
  owner plus affected-provider review.
- Slice 5 is serial after slices 1–4 are integrated. Release evidence begins
  only on the assembled candidate.
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

Total active effort is approximately **36–68 working days**. With permitted
parallelism, the modeled critical path is **27–56 working days** and elapsed
delivery is roughly **8–16 weeks plus unresolved external queues**.

## Honest geography finding

`calculate_annual_position` accepts an open facts mapping. Direct execution
with each of `jurisdiction="Scotland"`, `country="Scotland"`,
`country_code="GB-SCT"`, `territory="Scotland"` and
`tax_regime="Scottish"` produces the same `calculated` result as the baseline
(`total_liability=3486.00`). Those keys are silently ignored; unsupported
geography does **not** fail closed. This is an unresolved launch blocker owned
by slice 3.

Existing concepts are narrower and do not solve that blocker: QuickBooks
`CompanyInfoObservation.country` and canonical
`AccountingBusiness.country_code` are retained structures; FreeAgent validates
the documented company `country` wire member but its current
`FreeAgentCompanyRecord` does not retain it; the reviewed public structures do
not expose a `territory` field. None is wired to annual-tax admission.

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

## W8-S2 package acceptance gate

This assurance-only package is ready for a different independent reviewer when
only the three enumerated paths are present, its focused 24-test suite, declared
affected matrix and actual-provider contract matrix pass with bytecode/cache
disabled, and the claims above match executable evidence. Acceptance advances
no delivery slice and cannot pass the W8 terminal gate.

## Immediate next action

Give the exact three-path W8-S2 correction candidate to a different independent
reviewer. If accepted, the owning Codex may make the checkpoint decision; no
product implementation, merge, release or Founder decision is implied.
