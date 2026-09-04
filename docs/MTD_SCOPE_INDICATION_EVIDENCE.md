# MTD customer scope-indication evidence

## Status and base

`CORRECTED IMPLEMENTATION CANDIDATE READY FOR FRESH INDEPENDENT REVIEW`

- Branch: `codex/mtd-scope-indication`
- Immutable base: `be978a32a55954d6fe2888c830253a35fbf9852b`
- Base tree: `12410081e59630b0e2f00a43e86ebf35d5e7d2b3`
- Scope: one new service, one new focused test file and this evidence record.

This is not an accepted checkpoint, production activation, provider claim,
filing capability, credentialed check or launch-evidence claim.

## Service-owned boundary

The public service owns a single assess-and-present operation. It accepts only
an exact tuple of exact existing `IncomeSource` values, an exact supported
assessment year, an exact `MtdScopeCompleteness` envelope and exact
`bool`-or-`None` Self Assessment/exemption facts. It validates and detaches the
input graph before calling the captured existing `assess_mtd_readiness`.

Every completeness-envelope member must be exact `True`, confirming:

- supported residence circumstances;
- complete source inventory;
- complete source/assessment-period timing evidence;
- complete cessation facts; and
- a complete current-year annualisation basis, including confirmation that it
  is not applicable where that is the supported conclusion.

These are completeness/support confirmations, not new residence, cessation or
timing rules. Missing, `None`, false, non-boolean, subtype or mutated facts fail
to a generic **More information needed** result. An empty source tuple therefore
means zero only when the caller explicitly confirms the complete inventory and
all other support facts. Re-invoking this operation with the changed evidence
is the recheck boundary; the indication is not a stored continuing decision.

## Assessment and rule coherence

The exact engine result is immediately revalidated against:

- the process-start snapshot of the engine's current threshold rules;
- exact assessment and mandatory tax years;
- exact finite Decimal representations for threshold, total and distance;
- a fresh qualifying-gross-income total derived from detached sources;
- strict-more-than threshold and approaching-threshold coherence;
- exact source/business identity order, uniqueness and disjoint exclusions;
- exact data, eligibility and exemption coherence; and
- the exact independently expected current-engine status.

There is no `EXPECTED_NEXT_TAX_YEAR` relaxation. That status is not currently
issued by the captured engine path, so a forged result carrying it fails to the
generic presentation.

The effective start date is not maintained as another tax-rule table. For each
captured engine rule, it is deterministically derived from the exact mandatory
tax year and frozen in the same snapshot: `2026-27` becomes `2026-04-06`,
`2027-28` becomes `2027-04-06`, and `2028-29` becomes `2028-04-06`. The tax-year
shape and consecutive-year relationship are validated before service exposure.

## Customer language and safe descriptors

The exact feature label is **Could Making Tax Digital apply to you?**. Material
qualifying-income positions use **Worth reviewing** and say only that Making
Tax Digital may apply in a future tax year. Materiality is based on the
qualifying-income position, so an over-threshold, confirmed non-exempt result
remains material even when Self Assessment registration is false. A confirmed
exemption remains non-material and qualified. Unknown eligibility facts remain
**More information needed**.

The copy states that the threshold uses qualifying gross income before expenses
and distinguishes the local planning indication from HMRC's formal
determination. A below-material or coherently exempt result describes only what
the checked information currently indicates and expressly avoids promising an
exemption or future non-applicability. No filing action is exposed.

Opaque source and business identifiers are retained only during immediate
engine-result coherence checking. The customer mapping exposes bounded labels
and counts instead: included source categories/count, included business count,
and excluded material source categories/count. Provider or internal identifiers
are never projected.

## Projection, integrity and provenance limits

`MtdScopeIndication` is an opaque process-local handle with no customer fields.
The only supported public output API is the captured module-level
`as_mtd_scope_mapping(value)`, which validates exact type and live issuance and
returns a fresh read-only mapping. Rebinding a public class method cannot change
that projector. Direct construction, low-level reconstruction, copying,
deep-copying and pickle reconstruction do not transfer validity. There is no
claim that arbitrary Python introspection is impossible; raw class attributes
or attacker-added methods are outside the supported output API and carry no
trust semantics.

Acceptance-critical service dependencies are captured in closures. Rebinding
public module names cannot alter the captured operation or projector. Mutable
engine globals cannot silently promote a conclusion because the exact returned
graph must still match the independent captured rule/input coherence checks.

The engine does not provide durable issuance for standalone `MtdReadiness`, so
the service does not accept caller-supplied readiness results. The existing
immutable `IncomeSource` also has no construction-history token: structurally
exact copied or pickle-reconstructed source facts cannot be distinguished and
gain no provenance claim. They are fully validated and detached before use.

## Verification

Focused hostile coverage includes completeness omissions/mutations/subtypes,
empty inventory, every current threshold and one-penny boundary, material
unregistered/non-exempt and confirmed exemption paths, unknown eligibility,
rule-derived dates, opaque identifiers, category counts, malformed inputs,
source/result mutation and reconstruction, forged unsupported status, module
rebinding, opaque-handle reconstruction and public-class-method rebinding.

Tests run with bytecode generation and pytest cache disabled. Final results:

- required service/engine/literal matrix: **77 passed**;
- directly affected MTD/independence matrix: **113 passed**; and
- repository-wide suite: **6,096 passed, 7 subtests passed**.

`git diff --check` and final SHA-256 hashes are recorded after the final run;
this evidence file does not embed its own self-referential hash.

## Temporal-copy correction candidate — 5 September 2026

The preceding package identity, wording and verification record are historical
and retained unchanged. This bounded correction is on branch
`astra/mtd-temporal-copy`, base
`f29a5a8d4acde639fb108f8f9eeaaa833b59dc4b`, tree
`cd5293096cc592b0fd05d1d0c93d2811496daa6a`, under
`work/mtd-temporal-copy-authority.md`. It awaits a different independent
reviewer; it is not an acceptance or activation claim.

Copy contract `reserved-mtd-scope-indication/1.1` supersedes only the universal
future-start wording above. The material summary is now exactly **Making Tax
Digital may apply from the tax year shown.** The negative summary likewise
refers to **the tax year shown**, retaining **This is not a promise of exemption
or future non-applicability.** Unknown facts retain the unchanged incomplete
summary and suppressed monetary conclusions.

This avoids calling the existing 2024/25 assessment's 6 April 2026 start
unconditionally future. The 2025/26 and 2026/27 assessments still carry their
existing 6 April 2027 and 6 April 2028 starts, respectively. Thresholds remain
£50,000, £30,000 and £20,000; strict threshold, approaching, eligibility,
completeness and annualisation behavior is unchanged. There is no clock, new
rule table, source admission, forecast, route, persistence or filing behavior.

Authority references the owning task's primary-source check of
[HMRC eligibility and start dates](https://www.gov.uk/guidance/find-out-if-and-when-you-need-to-use-making-tax-digital-for-income-tax).
This implementation performed no external verification or provider access.
Founder Decisions remain byte-identical at SHA-256
`78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`.

The four-file MTD service/presentation/readiness/literal matrix passed **151**
tests. The expanded presentation/authentication/structural matrix passed
**408** tests, including those 151; exact commands are recorded in the companion
presentation evidence correction below. Historical full-suite counts above
were not rerun and are not counts for this candidate.

This correction supports but does not complete the missing authenticated,
source-supported MTD customer journey or close launch, privacy, target or
activation gates.
