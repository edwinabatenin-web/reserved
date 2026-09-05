# HMRC PAYE mapping eligibility — local implementation evidence

Status: uncommitted, bounded review candidate only.

## Frozen authority and scope

This candidate was prepared from commit
`d4bb9a579c40e0f06710c84654efd98495513370`, tree
`0726d0376133f6e5ba7e27ce4cd396b8a9d0414e`, under the accepted specification
whose SHA-256 is
`5b7d55c9b00c3a387c657eaf9767250f8982847e56c281183baf77e4c1b69699`.

Only these paths are in the candidate:

- `reserved/providers/hmrc_paye_mapping_eligibility.py`
- `tests/test_hmrc_paye_mapping_eligibility.py`
- `docs/HMRC_PAYE_MAPPING_ELIGIBILITY_EVIDENCE.md`

The implementation is a pure, network-inert structural projection. Its only
public operation accepts exactly three positional-only exact source-evidence
bundles. It revalidates those bundles, applies the specified ordered refusal
categories, admits exactly one member per source, and returns the exact nested
tuple projection. It does not join employments or subjects and does not import,
construct, or emit canonical PAYE evidence.

## Preserved boundaries

The candidate keeps Employment, Income, and Tax facts in separate branches.
It preserves exact tax year, source contract labels, timestamps, optional
digest presence, reference text, employment-name and off-payroll presence, and
exact integer/Decimal representation. Required Income pay and Tax deducted
amounts receive only an equality-preserving two-decimal mechanical candidate.
Employment digest omission is revalidated from the source contract's retained
omission sentinel: a valid lowercase SHA-256 remains present, while a mutated
explicit retained `None` or any other invalid retained state refuses as an
invalid source bundle.

Unknown schema names, excluded pension/benefit/refund presence, the
`267/LS500` marker, unsupported cardinality, and incompatible money fail closed.
Matching PAYE references do not establish identity. Mapping completeness and
currentness remain `UNKNOWN`; every authority flag is fixed false.

The module has no filesystem, environment, database, credential, session,
membership, route, provider HTTP, transport, reconciliation, forecast,
customer-presentation, annual-calculation, cash, payment, or provider-enablement
dependency. HMRC remains disabled, configured-but-not-implemented, unable to
make sandbox calls, and blocked in production-like environments.

## Local verification

The focused suite implements the specification's 22-case acceptance matrix,
including exact call binding, fixed errors and precedence, cardinality,
tax-year syntax/coherence, unknown names, excluded presence including zero,
State Pension marker handling, money boundaries and representation, timestamps,
digests, immutable output order, non-authority flags, non-echoing failures,
dependency isolation, and provider-readiness invariants.

The matrix uses the actual successful Employment, Income, Tax, Benefits, Child
Benefit and Winter Fuel Test Support observation types, plus both exposed Tax
body-only compatibility parse results, and proves that every one refuses in
each mapper argument position. Cardinality checks cover zero, duplicate pairs,
distinct two-member inputs and distinct many-member inputs independently for
Employment, Income and Tax. A forward source-bundle construction sequence and
its genuine reverse produce an equal fixed-order projection. Three distinct
source timestamps are varied and asserted beside independently present and
absent digest states.

Local results at the frozen working-tree candidate:

- focused mapping-eligibility suite: `41 passed in 0.18s`;
- exact Employment/Income/Tax contract and source-evidence suites plus all six
  PAYE Test Support suites: `1744 passed in 0.94s`; and
- one combined focused and affected run, including PAYE reconciliation and its
  presentation compatibility, provider readiness, and all repository W8/W9
  test modules: `2334 passed in 3.57s`.

The final frozen per-file and temporary-index binary-diff digests belong in the
implementer handoff because recording this file's own final hash here would
change that hash.

## Limitations and stopping state

This is local implementation evidence, not independent acceptance or provider
evidence. It establishes no source issuer, same-subject or same-run proof,
stable employment identity, owner/business scope, effective date, currentness,
completeness/recency policy, canonical evidence, persistence/supersession,
transport, credentials, provider access, customer use, production activation,
release, or go-live authority.

The candidate is intentionally left uncommitted. A different fresh reviewer
must inspect the frozen working-tree candidate before any owning-task checkpoint
or integration decision.
