# WP7 scoped gate review — simultaneous undergraduate plans

Review date: 13 August 2026  
Reviewer position: independent gate review; no production or West calculation helper used as a correctness oracle  
Corpus reviewed: 107 fixtures — 104 approved, 3 pending  
Decision: **NOT READY — scoped PASS is not currently justified**

## Question

Could WP7 issue a responsible-launch scoped PASS while preserving the three
simultaneous-multiple-undergraduate annual Self Assessment fixtures as pending
and treating that state as explicitly unsupported and fail-closed?

In principle, a scoped PASS may tolerate an expressly unsupported treatment
when the treatment is outside the approved launch scope, is detected reliably,
returns no plausible point result, is disclosed to the customer and cannot be
used for reserve guidance, reconciliation, filing, payment or refund claims.
That principle does not permit an assurance reviewer to remove a founder-
confirmed capability or to describe a currently calculated state as fail-closed.

## Confirmed v1 scope finding

The governing `docs/V1_TAX_SCOPE.md` includes “student and postgraduate loan
liability, reconciled with deductions evidenced to date.” It does not expressly
exclude simultaneous undergraduate plans. More decisively,
`RESERVED_NEW_AGENT_HANDOVER.md` records as a
scope/correctness requirement that multiple undergraduate plans were added and
that the applicable lowest threshold is used once, with postgraduate repayment
additionally where relevant. `docs/WP7_ASSURANCE_REMEDIATION_PLAN.md` likewise
sets “multiple undergraduate selection” as minimum Tranche B coverage.

Accordingly, an assurance review cannot silently reclassify this capability as
outside v1. Doing so requires an explicit founder scope decision and consistent
changes to the governing scope, product contract and customer journey. The three
pending fixtures must remain admitted and must never count among the 104
approved fixtures unless independently approved later.

## Current fail-closed finding

The required fail-closed boundary is not present. By inspection, the incremental
annual-liability path accepts an array of `student_loan_plans` and passes it to
the student-loan calculation. Repository tests explicitly expect Plan 1 + Plan 2
and Plan 1 + Plan 2 + postgraduate inputs to produce calculated amounts using
the lowest undergraduate threshold once. The output is labelled
`annual_self_assessment_liability`; it does not return `unsupported_rule`, null
the affected student-loan component or prohibit customer reliance for this
state.

This inspection is not used to judge whether the calculated amount is correct.
It establishes only that the proposed operational exclusion is not technically
enforced. A documentation limitation alone would be insufficient because a
plausible monetary result can still be emitted for the unsupported state.

The integrated annual-position envelope supports unsupported-family/status
semantics generally, but the inspected path does not establish a multiple-
undergraduate detector and fail-closed result. The approved Tranche H fixtures
also expressly refuse generalisation to simultaneous undergraduate plans; they
do not close this gap.

## Corpus assessment

- The methodology and independence framework remain **FIT**.
- 104 approved fixtures can support implementation and accuracy claims only for
  their literal bounded propositions.
- The three pending fixtures (`RW3-SL-001`, `RW3-SL-002`, `RW3-SL-009`) remain
  arithmetically plausible but lack explicit official annual-SA authority for
  simultaneous undergraduate plan selection.
- Their isolation is sound evidence governance: they remain in the corpus and
  integrity manifest but contribute zero approved pass counts.
- The 104/107 approval ratio is not itself a launch threshold and cannot waive
  an expressly required, high-consequence deterministic branch.

## Gate decision

**WP7 remains NOT READY.** A responsible-launch scoped PASS cannot be issued on
the stated premise because simultaneous undergraduate plans are an expressly
retained v1 capability and the current product does not fail closed on that
state. The blocker is narrow but material: the unsupported branch can produce a
plausible annual liability and influence money set aside.

This decision does not invalidate the 104 approved fixtures or block controlled
implementation against them. It blocks launch/customer reliance, general v1
accuracy claims and any claim that simultaneous undergraduate annual-SA
treatment is validated.

## Smallest safe path

### Path A — retain the confirmed v1 capability

This is the smallest path that preserves current founder scope:

1. Obtain explicit annual Self Assessment authority for simultaneous
   undergraduate plan selection. Acceptable evidence is direct HMRC annual-
   calculation documentation, authoritative Tax Logic evidence for the state,
   or another applicable primary annual-SA source; payroll-only lowest-threshold
   guidance is not sufficient by inference.
2. Freshly review the three immutable pending fixtures against that authority.
   Promote them only if every literal and derivation is supported, with a
   deliberate manifest update.
3. Run the formula-free fixture runner against the implementation. Any mismatch
   remains a defect; fixture values must not be changed to match engine output.
4. Verify component and integrated behavior for multiple undergraduate plans,
   undergraduate plus postgraduate liability, and reconciliation with evidenced
   payroll deductions while preserving their different bases.
5. Verify customer communication names the annual estimate and evidenced
   deductions separately and does not imply a confirmed HMRC balance.
6. Perform a final WP7 gate review. Only then may this blocker contribute to an
   unqualified v1 PASS.

### Path B — founder explicitly narrows launch scope

If timely annual authority cannot be obtained, the founder may deliberately
defer simultaneous undergraduate combinations. This is a product-scope change,
not an assurance workaround. Before a scoped PASS could be reconsidered, all of
the following gates are mandatory:

1. **Founder/product gate:** record an explicit decision that v1 supports zero
   or one undergraduate plan, optionally plus one postgraduate plan, and defers
   simultaneous undergraduate plans. Update the governing v1 scope and audit
   brief consistently.
2. **Input gate:** detect more than one distinct undergraduate plan at every
   ingress and persisted-profile path. Duplicate aliases must be normalised;
   unknown plan values must also fail closed.
3. **Calculation gate:** return a null student-loan liability with
   `unsupported_rule` for the affected component. Do not calculate a fallback,
   select a threshold, emit a total that silently excludes the component or
   reuse the existing plausible result.
4. **Envelope gate:** list the student-loan treatment in
   `unsupported_families`, attach a stable limitation/policy reference and mark
   any aggregate total partial or unavailable. Prohibit reserve guidance,
   reconciliation, filing, payment, refund and confirmed-balance uses.
5. **Customer gate:** clearly state that Reserved cannot estimate this loan
   combination, explain that the displayed tax position is incomplete, and
   direct the customer to confirm the position. The limitation must be textual,
   persistent and not dismissible into a misleading point estimate.
6. **Validation gate:** add independently derived fail-closed fixtures for Plan
   1+2, Plan 1+5, another distinct undergraduate pair, and undergraduate pair
   plus PGL across direct, persisted and integrated paths. Preserve the existing
   three arithmetic candidates as pending evidence and never count them as
   approved.
7. **Claim gate:** constrain launch claims to the narrowed scope. “Student loans
   supported” without the combination limitation is prohibited.
8. **Final independent gate:** demonstrate technical and textual prevention of
   unsupported use, then obtain a fresh scoped WP7 decision and explicit
   residual-risk acceptance by the accountable launch authority.

## Stopping rule

No further broad fixture expansion is required to resolve this decision. WP7 may
stop when either Path A is independently approved end to end, or Path B has an
explicit founder scope decision plus verified fail-closed product behavior and
customer restrictions. Until one path is complete, the precise gate result is
**NOT READY**, not conditional PASS.

---

## Founder-authorised bounded treatment — fresh independent reassessment, 13 August 2026

### Final proportionate official-source attempt

A final narrow search was made for an explicit annual Self Assessment rule for
simultaneous undergraduate plan types. It reviewed current HMRC Tax Logic
material, Self Assessment/Collection of Student Loans manuals and guidance,
2026/27 terms and conditions, and legislation search results. Payroll-only
lowest-threshold instructions were deliberately excluded as annual authority.

No new source closed the gap. HMRC Tax Logic continues to model singular
`planType`, threshold and rate and says to use the correct values for that plan.
Current annual guidance says Self Assessment uses income above the threshold
for “your loan”. The general borrower terms connect annual Self Assessment to a
borrower's threshold but do not expressly specify the annual selection or
allocation rule where two undergraduate plan types coexist. The only explicit
lowest-threshold instruction found remains directed to employers/payroll
agents. This remains absence of a public explicit proposition, not proof about
HMRC's internal calculation.

Applicable official sources remain:

- HMRC Tax Logic service guide — annual Self Assessment basis, singular plan
  configuration and whole-pound calculation;
- current GOV.UK Self Assessment student-loan guidance and 2026/27 terms and
  conditions — annual collection and plan-threshold context;
- Education (Student Loans) (Repayment) Regulations 2009 and amendments — loan
  repayment framework, but no sufficiently explicit public annual multi-plan
  selection proposition located in this review; and
- Agent Update 140 — explicit lowest-threshold treatment for payroll only and
  therefore not used as annual arithmetic evidence.

Further general public searching is no longer proportionate. Admissible future
arithmetic evidence remains an explicit annual rule/configuration or controlled
HMRC calculation observation independently reviewed for that narrow behavior.

### Founder decision and assurance classification

The founder has now authorised a bounded launch treatment: zero or one
undergraduate plan, optionally plus a postgraduate plan, may be calculated;
simultaneous undergraduate combinations require verification and are not a
supported annual-SA calculation. This is a deliberate supported-purpose limit,
not a finding that the pending expected amounts are correct.

Accordingly, `RW3-SL-001`, `RW3-SL-002` and `RW3-SL-009` remain unchanged in
`RW3_CORE_MULTI_UNDERGRADUATE_PENDING_FIXTURES.json` with
`independent_fixture_review_pending` status. They remain provenance/history for
future arithmetic review, contribute zero approved-fixture count and must not be
run or cited as correctness evidence. Their gate classification is
**arithmetic verification required / unsupported for decision**, not approved,
rejected arithmetic or silently deleted evidence. No corpus or integrity change
is warranted for that policy classification.

### Controls now evidenced

- The direct incremental calculation detects more than one distinct known
  undergraduate plan and raises `UnsupportedStudentLoanPlanCombination` before
  returning student-loan or aggregate money.
- The stored-profile dashboard catches that state and returns
  `unsupported_rule`, null income tax, NI, student loan and total, null
  allocation and no reserve construction.
- Annual reconciliation returns `unsupported_plan_combination`, no income basis
  or components, retains unsupported plan identity and prohibits combined
  balance, filing, payment and refund uses.
- The passed WP7U adapter emits a reconciliation-purpose inadequate envelope,
  `unsupported_rule`, no point or bounds, the unsupported family, a known
  `NOT_DETERMINABLE` effect and prohibitions covering combined balance, reserve,
  filing, payment and refund.
- Focused founder-scope, reconciliation, WP7U, boundary and independent fixture
  tests pass (54 tests in this reassessment).

These controls are sufficient to classify the known combination as unsupported
without substituting zero, selecting a payroll threshold or producing a partial
monetary answer.

### Remaining launch blockers

Two exact Path B controls are not yet demonstrated:

1. **Unknown plan values do not fail closed in the incremental path.** The
   current undergraduate-plan filter considers only keys found in configured
   student-loan plans. An unrecognised value can therefore be ignored rather
   than producing verification-required/unsupported status. Every input and
   persisted-profile ingress must normalise supported aliases and reject an
   unknown value before any monetary result.
2. **Customer qualification is not evidenced.** The internal dashboard service
   has the correct unavailable state, but no inspected customer template or
   response contract proves persistent plain-language wording that Reserved
   cannot estimate simultaneous undergraduate plans, that no displayed amount
   is a complete position, and that the customer must confirm the applicable
   plan treatment with HMRC or a suitably qualified adviser. The warning must
   not be dismissible into a monetary point and the general claim “student
   loans supported” must be qualified.

The governing scope and audit language must also record the founder's bounded
decision consistently before launch; this review does not edit shared scope or
handover records.

### Proportionate policy-fixture matrix

The minimum independent product-policy matrix is:

| Case | Required result |
|---|---|
| Plan 1 + Plan 2 | `unsupported_rule`; no component/aggregate money; verification action |
| Plan 1 + Plan 5 | same |
| Another distinct pair, including Plan 4 | same |
| Two undergraduate plans + PGL | whole combination unavailable; do not emit even a plausible PGL-only aggregate |
| Duplicate aliases of one undergraduate plan | normalise to one plan or fail input validation consistently; never misclassify as two balances |
| Unknown plan value alone or mixed with a known plan | `unsupported_rule`/verification required; no money |
| Persisted affected profile | same null state after reload; no allocation or reserve |
| WP7U boundary | inadequate reconciliation envelope; null point/bounds; named unsupported family; effect not determinable; policy/provenance and prohibitions retained |
| Customer surface | explicit unsupported combination, incomplete position and HMRC/qualified-adviser confirmation action |

These are product-policy expected outcomes and must be reviewed against the
founder decision/policy version, separately from statutory arithmetic fixtures.
They must not replace or promote the three pending literals.

### Revised gate decision

The founder decision removes the earlier scope-authority blocker to a future
scoped WP7 PASS: WP7 need not prove arithmetic for a deliberately unsupported
case if the unsupported state is comprehensively and truthfully prevented from
producing a decision-relevant estimate.

**Current decision remains NOT READY for a scoped launch purpose.** The reason
is no longer missing permission to narrow scope; it is the two concrete
implementation/presentation gaps above. A documentation-only limitation is not
enough while unknown values may still yield money and the customer qualification
has not been demonstrated.

WP7 may issue a **scoped PASS** once the following bounded stopping rule passes:

1. unknown and simultaneous undergraduate plan inputs fail closed at every
   direct and persisted ingress;
2. no affected route, service, envelope, allocation, reserve or cached output
   exposes component or aggregate money;
3. the WP7U unsupported envelope retains plan/input provenance, named scope,
   `NOT_DETERMINABLE` effect, policy version, customer action and prohibited
   uses;
4. customer wording is persistent, accessible and tested for the exact
   verification-required message and qualified product claim;
5. the policy matrix above passes independently, the founder/delegated launch
   authority accepts the residual risk, and governing scope/claims consistently
   state the limit; and
6. the three arithmetic candidates remain pending and excluded from the
   approved count.

At that point WP7 can pass for the explicitly bounded purpose of calculations
covering at most one undergraduate plan plus optional PGL, with unsupported
combinations producing no decision-capable estimate. That would be a scoped
PASS, not validation of simultaneous-plan arithmetic and not by itself a final
WP20 launch approval.

---

## Final two-case independent check — 13 August 2026

Reviewer position: fresh non-implementing review; no production or West output
used as an arithmetic oracle  
Purpose reviewed: founder-authorised unsupported treatment only  
Decision: **NOT FIT for the scoped launch purpose**  
Arithmetic decision: **not reviewed and not approved**

### Review boundary

This check replayed two policy cases through the available direct estimator,
stored-profile dashboard, WP9 annual reconciliation, U2 envelope/composition
and customer wording:

1. an unknown plan alone and an unknown plan mixed with one known undergraduate
   plan; and
2. simultaneous distinct undergraduate plans, including an undergraduate pair
   with PGL.

The review asked only whether every case is truthfully classified as
unsupported for decision and prevented from producing consequential money. It
did not calculate, inspect or endorse the pending expected amounts.

### Controls that pass

- **Direct estimator:** both policy cases raise
  `UnsupportedStudentLoanPlanCombination` before returning student-loan or
  aggregate money. The exception carries `unsupported_rule`,
  `not_determinable`, a verification action and a no-money limitation.
- **Dashboard/persisted profile service:** both cases return null Income Tax,
  NI, student loan and total, null allocation, null protected/annual target/
  funding percentage, no chart and no activity. The supplied plans survive in
  `student_loan_plans_supplied` and the HMRC/qualified-adviser action survives.
- **WP9 reconciliation:** both cases return
  `unsupported_plan_combination`, no income-basis amount and no components.
  Unknown plan values survive in `unsupported_plans`; no PGL-only or other
  partial monetary component is emitted.
- **Composition:** an unsupported WP9 result propagates to
  `unsupported_rule`, retains no loan components and cannot become a complete
  combined position. Top-level composition prohibits customer presentation,
  reserve guidance, filing, payment and refund.
- **Money/reserve boundary:** no reviewed affected path emits a point, range,
  partial total, allocation, set-aside or reserve-guidance amount.
- **Customer wording:** both dashboard templates place the unsupported branch
  before all monetary content, use a persistent live-region panel, state that
  no student-loan amount, total, allocation or set-aside figure was calculated,
  and render the HMRC/qualified-adviser verification action.
- **Arithmetic isolation:** `RW3-SL-001`, `RW3-SL-002` and `RW3-SL-009` remain
  in `RW3_CORE_MULTI_UNDERGRADUATE_PENDING_FIXTURES.json` with pack status
  `independent_fixture_review_pending`, reviewer null and decision pending. Its
  SHA-256 remains
  `cec581a53e962c4436c4faa7b72f504f0f38ed455dc11020c335b81903e25586`,
  matching the integrity manifest. The approved count remains 104 of 107.

### Exact blockers

1. **The formal U2 purpose is wrong for the authorised treatment.**
   `emit_annual_loan_wp7u_envelopes()` emits the unsupported object with
   `EstimatePurpose.RECONCILIATION`. The adopted standard defines
   `unsupported_for_decision` for precisely this state. A reconciliation-
   purpose envelope that is inadequate and prohibited is conservative, but it
   does not satisfy the explicit formal-purpose gate requested for launch.
2. **Unknown-plan provenance and scope are collapsed.** The WP9 result retains
   the literal unknown plan, but the U2 envelope discards `unsupported_plans`
   and always names `simultaneous_multiple_undergraduate_plans`. Consequently
   an unknown-only or known-plus-unknown case is represented as a different
   unsupported family. Its uncertainty references annual-basis evidence only,
   not a stable representation/reference for the supplied plan input. The
   customer action survives, but the reason/provenance is not lossless.
3. **The customer branch is not exercised by a rendered route/template test in
   the focused evidence inspected.** Service tests prove the unavailable data
   shape and static template inspection proves the intended branch, but a
   launch gate still needs a rendered test for both policy cases showing that
   no monetary dashboard subtree is present and the wording/action is
   accessible. This is a narrower evidence gap than the two semantic defects
   above, not evidence that money is currently rendered.

### Founder residual-risk acceptance

The founder-authorised residual risk is applied: Reserved may launch without
calculating simultaneous undergraduate arithmetic if the case is detected,
withheld and truthfully presented as unsupported. That acceptance permits the
three arithmetic fixtures to remain pending and excluded; it does not permit a
known unsupported input to be assigned the wrong formal purpose/family or lose
its provenance. Those are deterministic contract defects within the chosen
Path B control, not unavoidable residual uncertainty.

### Scoped verdict and stopping condition

**NOT FIT for the scoped launch purpose.** The reviewed paths successfully
withhold all consequential money, which materially reduces immediate harm, but
the explicit `unsupported_for_decision` and lossless provenance conditions do
not pass. Customer rendering also lacks the final focused evidence.

The smallest closure is to emit a purpose-inadequate
`unsupported_for_decision` envelope, distinguish unknown-plan input from
simultaneous known undergraduate plans while preserving the supplied-plan
provenance/action/prohibitions, and add rendered customer tests for the two
cases. A fresh review may then issue a scoped PASS under the founder's accepted
residual risk. That future PASS would still exclude and not approve the three
pending arithmetic fixtures.

---

## Final exact three-blocker recheck — 13 August 2026

Reviewer position: fresh non-implementing review limited to the three blockers
above  
Decision: **SCOPED PASS for the founder-authorised launch purpose**  
Arithmetic decision: **simultaneous-plan arithmetic remains unreviewed,
unapproved and outside this PASS**

### Blocker closure

1. **Formal purpose — closed.** Unsupported WP9 results now emit
   `EstimatePurpose.UNSUPPORTED_FOR_DECISION`, `PurposeFitness.INADEQUATE` and
   `CalculationStatus.UNSUPPORTED_RULE`, with no point or bounds and a
   `NOT_DETERMINABLE` effect. The action and prohibitions for combined balance,
   reserve guidance, filing, payment and refund remain present. Supported Plan
   2 and Plan 2/PGL results continue through the ordinary
   `EstimatePurpose.RECONCILIATION` component path; the unsupported-purpose
   change does not reclassify valid reconciliation.
2. **Family and input provenance — closed.** The producer now retains every
   supplied plan literal for an unsupported result and supplies a distinct
   limitation family for unknown-only, mixed known/unknown, simultaneous known
   undergraduate and unsupported single-undergraduate cases. U2 maps that
   family without substitution and creates stable ordered declared-input
   evidence (`student-loan-plan-input:<index>`) carrying the original value,
   tax year, observation date, manual-assertion representation and incompatible-
   representation selection. The uncertainty references both annual-basis and
   declared-plan evidence. Unknown-only is no longer described as simultaneous.
3. **Rendered customer evidence — closed.** The focused rendered tests exercise
   both `['mystery']` and `[1, 2]` against the legacy `/calculate` route and the
   authenticated v2 dashboard. They require the live-region unsupported panel,
   the HMRC/qualified-adviser action, the explicit statement that no student-
   loan amount, total, allocation or set-aside figure was calculated, and no
   currency output within the panel. Both templates branch to that panel before
   their monetary dashboard trees. Static customer-language tripwires cover the
   same wording in both templates.

The new focused modules compile in this review environment. Their pytest run
could not be repeated here because the available system Python does not include
pytest/Flask; this is recorded as an execution-environment limitation, not
replaced with an invented pass count. The reviewed assertions directly cover
the three prior blockers, and no contrary path was found within this exact
scope.

### Pending arithmetic evidence reverified

`RW3-SL-001`, `RW3-SL-002` and `RW3-SL-009` remain the only three fixtures in
`RW3_CORE_MULTI_UNDERGRADUATE_PENDING_FIXTURES.json`. The pack remains
`independent_fixture_review_pending`; reviewer remains null and decision
remains pending. Its SHA-256 remains
`cec581a53e962c4436c4faa7b72f504f0f38ed455dc11020c335b81903e25586`,
exactly matching `WP7_FIXTURE_INTEGRITY.json`. They remain excluded from the
104 approved fixtures and contribute no arithmetic correctness evidence.

### Scoped decision

Applying the founder's explicit residual-risk acceptance, WP7 **PASSES for the
bounded launch purpose** of supporting the approved calculation scope while
detecting the reviewed unsupported student-loan plan inputs, returning no
decision-capable money and directing the customer to external verification.
The chosen unsupported treatment is now formal, provenance-bearing,
purpose-inadequate and enforced at the rendered customer boundary.

This PASS does not validate the three pending expected results, establish the
annual Self Assessment selection rule for simultaneous undergraduate plans,
approve an unqualified “all student loans supported” claim, approve persistence
or public API use, or constitute final launch approval. Any future attempt to
calculate simultaneous-plan arithmetic reopens the applicable-authority,
independent-fixture and implementation gates.
