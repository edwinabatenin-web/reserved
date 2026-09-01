# W2-S6 exact integration handoff

Status: fulfilled on the authorised local integration line.
Evidence cut-off: 1 September 2026.

## Reviewed inputs

- W1 cash-ready annual contract checkpoint:
  `51b2e023a23c22dfbe61a6e607d81ab399d475b7`
- W1-S4 property fail-close parent:
  `413ee1312ba4ec8cf42912a9411f55b69a0a1d3e`
- W2 S1-S5 and preparation line: current
  `feature/w2-sa-account-reconciliation` history through this handoff
- W2-S5 checkpoint:
  `69fb31576ec730ad49b8da4f0ebb3f5ed135ec98`

The W1 checkpoint is independently reviewed and post-checkpoint verified. Its
new contract files are `reserved/engines/cash_ready_annual_position.py` and
`tests/test_cash_ready_annual_position.py`, with an internal-boundary marker in
`tests/test_internal_tax_boundary.py`.

## Integration rule

Do not retype or copy the W1 contract shape into W2. Assemble the exact reviewed
W1 and W2 histories using the authorised local branch-integration procedure,
verify both expected trees/parents, and keep the integration local. No push,
release, deployment, production access or Control Plane readiness change is
authorised by this handoff.

After assembly, implement exactly one S6 adapter/composition module and one
focused test module unless the predeclared compatibility scan proves another
exact consumer must change. The adapter must consume the W1 contract and W2
S1-S5 contracts; it must not rewrite them.

## Required S6 behavior

1. Accept only the exact SHA-256-bound W1 cash-ready annual result.
2. Use `final_self_assessment_liability` for balancing composition while
   preserving the named annual-tax and student-loan components.
3. Never use the current W1 forecast as an HMRC-issued prior-year PoA basis.
4. Obtain PoA basis, tax deducted, prior PoA, payments and credits only from
   their separate W2 evidence channels.
5. Reject any duplicated evidence identity or liability/credit channel.
6. Preserve first-year SA behavior without inventing prior-year PoA.
7. Feed the resulting expected dated obligations through S3 reconciliation and
   S5 funding position without treating a surplus as spendable cash.
8. Return unresolved for mismatched tax year/ruleset/date, unsupported W1
   family, untrusted content identity, incomplete HMRC evidence or any
   double-count ambiguity.

Use the 12-case fixture matrix in
`docs/W2_S6_ANNUAL_TO_CASH_CONTRACT_PREPARATION.md`. Expected values must remain
independently derived.

## Completion sequence

1. authorised local history assembly;
2. exact pre-state and shared-consumer scan;
3. S6 implementation and focused tests;
4. independent exact-diff review;
5. focused correction only if required;
6. one reviewed bounded local checkpoint;
7. post-checkpoint W1/W2 regression and Git integrity verification;
8. W1/W2 completion-map reconciliation.

Stop for a genuine Founder gate if local branch integration is not authorised
or if assembly reveals a material contract conflict. Do not work around that
gate by duplicating source files.

## Fulfilment

The reviewed W1 changes assembled cleanly with the W2 S1-S5 history on local
branch `integration/w1-w2-s6`. The final S6 adapter was independently reviewed,
corrected only within its three-file scope and checkpointed at
`485b76696eacd0e9793414f983fb236f6cd7b11c`. Its exact post-checkpoint tree is
`7c9ebc0921a1c33b8b2c330983e9e0dcedc68e25`.

All eight required behaviours are covered by the independently reviewed
fixture/adversarial suite. The local branch remains unmerged and unpushed; this
handoff does not establish customer, provider, release or launch readiness.
