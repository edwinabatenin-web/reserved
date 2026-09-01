# W2-S6 annual-to-cash contract preparation

Status: implemented and independently verified on the dedicated local integration line.
Evidence cut-off: 1 September 2026.

## Purpose

S6 is the final W2 implementation slice. It will connect the stabilised W1
annual-position boundary to the existing W2 PoA, balancing, account,
cash-obligation and funding-position contracts without creating a second annual
tax model.

W1 now supplies `reserved-cash-ready-annual-position/1.0` at exact reviewed
checkpoint `51b2e023a23c22dfbe61a6e607d81ab399d475b7`. The contract binds annual
tax and loan/no-loan inputs to exact SHA-256 content identities, classifies
student-loan/PGL outside the PoA basis and prohibits using a current forecast as
an HMRC-issued PoA basis.

The earlier W1 `InternalAnnualComposition` deliberately links annual tax and
student-loan results without aggregating them. It explicitly prohibits customer
balance, reserve, filing and payment use. S6 must not bypass that boundary or
turn the current linked composition into a cash amount before W1 declares the
relevant component set stable and suitable for this purpose.

## Entry gate for implementation

The following entry conditions are now pinned by W1-S5:

1. exact W1 checkpoint and tree;
2. supported annual-position contract and ruleset version;
3. complete list of liability families entering the balancing amount;
4. complete list of families entering the PoA basis;
5. explicit exclusions from the PoA basis;
6. student-loan/PGL treatment in the final Self Assessment amount;
7. authoritative channels for tax deducted at source, prior PoA, other payments
   and HMRC credits;
8. provenance, effective/retrieval dates, completeness and uncertainty for each
   channel;
9. removal or replacement of any upstream prohibition that currently prevents
   reserve guidance, supported by independent review rather than assumption.

If any item remains unknown, S6 must return an unresolved result rather than
infer zero or reuse a headline annual total for a different purpose.

## Provisional field mapping

| Cash concept | Candidate upstream field/evidence | Required control |
|---|---|---|
| Income Tax/Class 4/HICBC annual tax subtotal | W1 `AnnualPositionResult.total_liability` and named component fields | Accept only a calculated, semantically valid, supported-scope W1 result; preserve component identity |
| Student-loan/PGL amount remaining for Self Assessment | Each complete W1 annual-loan component's `remaining_self_assessment_amount` | Keep outside the PoA basis; include in final balancing liability only if W1 confirms that ownership |
| Other final-liability families | Future stable W1 component list | No implicit inclusion; each family must be explicitly classified |
| PoA basis | S1 `PriorYearEvidence` income tax/HICBC/Class 4 channels | Never substitute a current-year forecast for an HMRC-issued prior-year amount |
| Tax deducted at source | Explicit purpose-specific evidence | Apply once to the PoA statutory test and once to balancing only where the respective contracts require it; prevent duplicate crediting |
| Prior PoA | S1 `BalanceItem`/explicit HMRC evidence | One aggregate channel only; reject the same entries in `payments_made` |
| Other payments and HMRC credits | S1 payment evidence and S2 reconciled account evidence | Bind stable identities and reject duplicated evidence across channels |
| Dated actual obligations | S3 reconciliation | Preserve local expectation versus HMRC-confirmed distinction |
| Set-aside gap/exact/surplus | S5 funding position | Never present surplus as available cash or authorise payment |

This table is provisional. It constrains S6 preparation but does not change W1
ownership or declare its current fields fit for customer reliance.

## Double-count invariants

The S6 adapter must fail closed if:

- HICBC is present both inside an income-tax subtotal and as a separate amount;
- student-loan/PGL is included in both annual tax total and a separate loan
  component;
- prior PoA is supplied through both the aggregate prior-PoA channel and payment
  history;
- PAYE/tax deducted at source or an HMRC credit appears through more than one
  evidence identity;
- a current-year forecast is labelled as an HMRC-issued prior-year PoA basis;
- an S2 account credit is treated both as an applied account allocation and an
  additional balancing deduction;
- two results use different tax years, rulesets, effective dates or incompatible
  completeness purposes;
- an unsupported, stale, conflicting or incomplete W1 family is treated as
  zero.

## Required fixture matrix

The final S6 package must include independently reviewed fixtures for at least:

1. complete annual tax, no student loan, no prior PoA and no other payments;
2. complete annual tax plus one supported student-loan/PGL component with
   evidenced deductions;
3. first Self Assessment return: no invented prior-year PoA, followed by a
   balancing amount and first valid following-year PoA sharing 31 January where
   the confirmed contracts require it;
4. established taxpayer with two PoA instalments, prior PoA already paid and a
   remaining balancing amount;
5. excess-credit/refund candidate, retained as non-spendable and non-payment
   evidence;
6. tax deducted at source near the PoA applicability boundary;
7. duplicated prior payment/credit identity, which must fail closed;
8. local estimate versus HMRC-issued evidence with identical arithmetic but
   different qualification;
9. incomplete or unsupported W1 family, which must suppress the cash point
   result;
10. stale, future-dated and conflicting evidence;
11. exact S3 obligation reconciliation feeding exact, gap and surplus S5
    positions;
12. forged or version-mismatched upstream dataclasses, which must be
    independently recomputed or rejected.

Expected values must be independently derived. Production output must not be
used to backfill fixture expectations.

## File ownership and collision rule

The eventual S6 package should add one narrowly named adapter/composition module
and its tests. It must consume, not rewrite, the current S1–S5 contracts. Any
required change to W1, `annual_position_composition.py`, internal snapshot
semantics, or an S1–S5 contract is a separate compatibility package with an
explicit file list and independent review.

Provider adapters, UI, persistence, payments, filing, production activation and
Control Plane state remain outside S6.

## Original prepared action (completed)

Assemble exact W1 checkpoint `51b2e02...` with the reviewed W2 S1-S5 history on
one authorised local integration line. Reconcile this mapping against the
actual imported contract, retain the upstream content identities as evidence,
approve independent fixture expectations, and implement S6 as the single
remaining W2 slice. No further W1 product design is required.

## Completion record

The prepared action was completed without a contract conflict. The exact W1
S4/S5 changes were assembled on local branch `integration/w1-w2-s6`; S6 was
implemented at `485b76696eacd0e9793414f983fb236f6cd7b11c` with parent
`247dfe912178d8d6ef40ac92ddc59e73c567ac7a` and tree
`7c9ebc0921a1c33b8b2c330983e9e0dcedc68e25`.

The implementation binds complete W1 annual content, each balance channel and
its source evidence identities, prior-year evidence and payment content. It
reconstructs typed evidence at the trust boundary, rejects first-year prior
PoA, mismatched periods, forged/sub-penny content and duplicated evidence, and
feeds only validated results into the existing S1, S3 and S5 contracts.

Fresh independent review closed all identified corrections and reported no
remaining findings. Post-checkpoint integrated regression passed 1,920 tests;
the sole expected failure is the canonical-metadata freshness gate following
legitimate source advancement. No main-branch merge, push, release, deployment,
production access, filing or payment action occurred.
