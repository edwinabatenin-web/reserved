# W1-S4 launch-supported-scope closure — read-only pre-flight

Status: completed with one focused, independently reviewed correction.
Source: clean W1 checkpoint
`066ed358f9dc231f3c424c7fc01123fce0bdee6b` on
`feature/w1-bpa`, inspected 31 August 2026.

## Bounded question

Does W1 still require another tax-formula implementation tranche before its
cash-ready annual contract can be built, or does the current annual engine
already calculate the reviewed subset and fail closed for the unsupported
cases?

## Evidence-based answer

No further tax formula is presently justified by the inspected evidence.

The current `AnnualPositionResult` already exposes a single purpose-specific
completion boundary:

- `total_liability` exists only when every applicable requested family is
  supported and sufficiently evidenced;
- non-savings income consumes bands before savings, and savings before
  dividends;
- Foreign Tax Credit Relief and the residential finance-cost reduction produce
  named unsupported families, preserve the pre-limitation figure and suppress
  the complete total;
- unsupported residence facts suppress foreign-property inclusion;
- missing or contradictory HICBC responsibility facts suppress HICBC and the
  complete total;
- absent or incomplete BPA facts suppress the complete total rather than
  assuming no entitlement;
- PAYE reconciliation and student loans are named as not performed and are not
  silently folded into the annual tax subtotal.

The focused annual calculation/composition/snapshot set was then expanded to
all of the direct consumers listed below: 203 tests collected and passed at the
pinned checkpoint with bytecode and pytest-cache writes disabled. The suite
includes explicit savings/dividend ordering, FTCR, residential-finance-cost,
HICBC, BPA, composition, snapshot and isolation cases.

This supports treating W1-S4 as a fresh independent scope-boundary assurance
package. It does not by itself provide that independent assurance or make the
result customer/launch ready.

## Exact S4 review package

Review these production artifacts without modifying them first:

- `reserved/engines/integrated_annual_position.py`;
- `reserved/engines/tax_config.py`;
- `reserved/engines/annual_loan_reconciliation.py`;
- `reserved/engines/annual_position_composition.py`;
- `reserved/engines/internal_snapshot.py`.

Review these direct and mechanical consumers:

- `tests/test_integrated_annual_position.py`;
- `tests/test_integrated_annual_position_pension.py`;
- `tests/test_integrated_hicbc_staged_rounding.py`;
- `tests/test_hicbc_bounded_evidence_adequacy.py`;
- `tests/test_blind_persons_allowance.py`;
- `tests/test_annual_loan_reconciliation.py`;
- `tests/test_annual_position_composition.py`;
- `tests/test_internal_snapshot.py`;
- `tests/test_internal_tax_boundary.py`;
- the canonical assurance-metadata freshness gate.

The review must independently confirm all of the following cases:

1. ordinary PAYE/trading/property/savings/dividend inputs in the supported
   2026/27 England/Wales/Northern Ireland subset;
2. savings starting-rate and Personal Savings Allowance boundaries;
3. dividends after non-savings and savings band consumption;
4. Personal Allowance taper and Relief at Source band extension;
5. supported UK and foreign property cases without silently inferring
   residence, ownership, treaty relief or finance-cost treatment;
6. FTCR and residential-finance-cost cases return no complete total;
7. complete, incomplete, contradictory and other-person HICBC responsibility;
8. complete, absent, partial and contradictory BPA evidence;
9. annual student-loan/PGL reconciliation remains separate and complete only
   with adequate basis/deduction evidence;
10. the internal composition remains non-aggregating and prohibited from
    customer, reserve, filing and payment use.

If every case passes, close W1-S4 by durable independent review evidence; do
not create a code commit merely to make the slice appear active. If a concrete
defect is found, issue one focused correction package naming only the exact
defective artifact and its enumerated consumers.

## Stale statements to adjudicate, not obey blindly

Some historical documents still say dividends/savings ordering is outstanding
or describe earlier annual-family gaps. The current engine and tests contain
the ordering and annual-family implementation. The reviewer must reconcile
those statements against the exact checkpoint and classify them as either a
real customer-connection gap or stale narrative. Narrative alone must not
reopen a completed calculation.

HICBC privacy, retention, legal, customer-evidence and activation gates remain
real, but they belong to HICBC/privacy/customer integration. They do not justify
adding another W1 arithmetic slice or bypassing W1's current fail-close result.

## Next substantive W1 package after S4 assurance

Proceed to W1-S5: one cash-ready annual-position contract for the internal
W2-S6 purpose. The expected minimal change set is:

- one new narrowly named contract/composition module;
- one new focused test module;
- no edits to current tax formulas, S1-S5 W2 contracts, UI, persistence,
  providers, filing or payments unless independent review identifies a precise
  compatibility requirement first.

Before submission, enumerate `annual_position_composition`, `internal_snapshot`,
the W2-S6 fixture package and the internal-boundary tests as consumers even if
the intended diff does not change them. Any required consumer edit must be
added by exact path rather than widening the envelope.

## Stop conditions

Stop for a genuine Founder gate only if the independent review concludes that
the existing Founder-confirmed v1 scope cannot be met by the reviewed supported
subset plus deterministic fail-close exclusions. Do not infer a request to
support Scottish tax, CGT, full filing, treaty logic or other new scope.

Otherwise, S4 assurance and S5 implementation are already-authorised
engineering steps and should continue without Founder intervention.

## Completed outcome — 1 September 2026

Fresh independent review found two material fail-close defects not covered by
the original 203 tests: incomplete joint-property fact pairs could silently
default the ownership share to zero, and a negative foreign-property result
could offset general income despite foreign-loss treatment being unsupported.

The correction changed exactly:

- `reserved/engines/integrated_annual_position.py`;
- `tests/test_integrated_annual_position.py`.

Independent re-review found no remaining issue. Post-checkpoint evidence at
`413ee1312ba4ec8cf42912a9411f55b69a0a1d3e` is:

- 206 direct-consumer tests passed;
- 1,675 broader tests passed plus 7 subtests;
- one expected assurance-metadata freshness failure because production source
  legitimately advanced;
- clean worktree and successful Git integrity check.

W1-S4 is therefore closed for bounded internal scope assurance. This does not
establish customer or launch readiness. W1-S5 is the sole remaining W1
implementation slice before W2-S6 can cross its entry gate.
