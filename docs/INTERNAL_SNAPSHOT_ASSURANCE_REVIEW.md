# Internal snapshot — final narrow independent re-review

Review date: 13 August 2026  
Artifacts: `reserved/engines/internal_snapshot.py` and focused tests  
Decision: **PASS for decoded ephemeral internal handoff only**

## Final remediation verified

- The decoder now reapplies the composition producer's exact reference suffix
  grammar: `[A-Za-z0-9][A-Za-z0-9._-]{0,127}` after the required
  `annual-position:` or `loan-reconciliation:` namespace.
- Both standalone producer roots and both referenced components in a composition
  are pinned to the supported `uk-2026-27-v3` ruleset. With the current single
  supported ruleset, this also enforces cross-producer compatibility.
- The former accepted counterexamples, `annual-position:../../ customer` and
  `loan-reconciliation:bad/id`, now fail closed.
- Direct hostile replay also rejected wrong and empty namespaces, a 129-character
  identifier, hostile standalone annual-position and loan rulesets, and hostile
  nested annual-tax and loan rulesets. A legal 128-character identifier remained
  accepted, confirming the boundary is not over-restricted.
- All 35 focused snapshot tests pass, including lossless JSON round-trip for all
  three approved roots and the prior exact-shape, typed-value, semantic-coherence,
  prohibition and combined-money hostile cases.

## Supported purpose and limitations

The snapshot is fit as a strict, decoded wire representation for transient
internal handoff of the three approved 2026/27 result roots under the versions
and ruleset explicitly recognised by this decoder. It preserves Decimal, date,
enum, tuple, provenance, limitations and prohibitions without adding a combined
customer monetary result.

This PASS does **not** approve files, databases, queues, caches, durable
persistence, public or partner APIs, customer presentation, filing, payment,
refund or reserve guidance. It does not assess tax arithmetic anew and does not
make the internal producer results customer-ready. Any new root, tax year,
producer contract version, ruleset, status, field, permitted reference grammar,
or use beyond decoded ephemeral internal handoff requires an explicit contract
change and fresh proportionate review.

## Stopping rule

The previously bounded defect set is exhausted: exact producer reference grammar
and supported/compatible producer rulesets are enforced, while all established
round-trip and hostile regressions pass. Under the agreed credible stopping rule,
no further scope search is required for this ephemeral-handoff decision. Review
reopens only if one of the contract/version/scope conditions above changes or a
concrete contradictory case is found.

## Verdict

**PASS for decoded ephemeral internal handoff only.** No residual blocker remains
within that bounded purpose. The exclusions above remain mandatory.
