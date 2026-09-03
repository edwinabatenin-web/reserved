# PAYE reconciliation trust and explicit-policy evidence

## Candidate boundary

`IMPLEMENTATION CANDIDATE — PENDING FRESH INDEPENDENT REVIEW`

- Branch: `codex/paye-reconciliation-trust-policy`
- Immutable base/HEAD: `d0f4d143eae2fe0078d5fa411da25888f49b188c`
- Base tree: `f252a360af226e2394ab692ace0918fa8d3e3989`
- Production scope: `reserved/engines/paye_reconciliation.py` only.
- Compatibility and hostile coverage is confined to the four exact authorised
  PAYE/independent test paths named for this package.

The package changes no Founder Decision, evidence-capture or extraction
producer, HMRC contract, provider, annual-tax/cash/MTD engine, route, template,
database, persistence, configuration, release metadata or completion map.

## Authority preserved

The implementation retains the six independently approved propositions in
`RW3_PAYE_EVIDENCE_FIXTURES.json` and its formal review:

1. two declared employment-cumulative observations sum once;
2. a same-period aggregate explicitly covering the same employment identities
   replaces, rather than adds to, those entity observations;
3. a material same-scope conflict remains unresolved with both candidates and
   its bounded alternatives retained;
4. missing PAYE evidence stays unknown, with exact zero only as a separately
   labelled conservative assumption;
5. tax deducted above an estimated liability yields a zero remaining amount
   and a separately qualified apparent overpayment, never a refund claim; and
6. stale evidence remains bounded to its represented period, with later effects
   partial and indeterminable.

HMRC has no unconditional precedence and there is no hard-coded source-kind
ordering. Selection considers represented scope, effective period,
observation date and completeness, then uses the exact validated evidence ID
as a source-neutral stable identity key. Source kind therefore cannot override
stronger facts or silently win an otherwise exact comparison. Bank inference
retains its approved low-confidence and last-resort warning semantics, but its
kind is not used to select it over another candidate. All considered
provenance is retained.

## No embedded operating-policy approval

`reconcile_paye` now requires an exact factory-issued
`PayeReconciliationPolicy` for every call. Direct class construction is not a
supported issuance path and fails closed. The closure-bound
`make_paye_reconciliation_policy` factory has no recency or
conflict-tolerance defaults and accepts exactly two positional inputs:

- a bounded exact integer `stale_after_days`; and
- a bounded, finite, non-negative exact two-decimal `Decimal`
  `conflict_tolerance`.

The values used by synthetic tests reproduce the historical examples only.
They are not asserted to be an approved universal 45-day or £1 rule. Changing
the explicit policy changes the classification at the exact boundary without
changing evidence facts. Evidence-type/tax-year-stage windows, materiality and
customer severity remain policy decisions outside this package.

The public reconciliation function manually accepts exactly two positional
facts plus exact keyword-only `tax_year`, `as_of` and `policy`, with no missing
or extra arguments. Its variadic implementation has no parameter default that
can acquire authority through mutable function metadata. Policy issuance uses
captured `object.__new__`, captured slot descriptors, validation and a private
identity/fingerprint registry. Changing class/metaclass `__call__`, `__new__`,
`__init__` or function default metadata can create at most an unregistered
object, which reconciliation and the authoritative projector reject. The
factory continues to issue valid policies under those class-dispatch attacks.

## Validated evidence graph

The reconciliation boundary accepts one exact tuple only; lists, generators
and one-shot iterables are rejected before iteration. Each `PayeEvidence` is
constructed and revalidated using captured exact dependencies and a
process-local identity/fingerprint:

- exact evidence, representation and completeness enums;
- ASCII consecutive `YYYY-YY` tax year and exact built-in dates;
- stable bounded ASCII evidence/employment/source identities;
- exact `Decimal` output representation for non-negative finite bounded
  amounts, preserving `None` separately from exact `0.00`;
- exact employment-cumulative identity or aggregate covered-employment tuple;
- unique evidence and covered-employment IDs;
- aggregate/entity coverage and effective-period coherence;
- one requested tax year, with future observations rejected; and
- no bool, float, subtype, non-finite, signed/negative, ambiguous or extreme
  numeric promotion.

Every scalar and nested field fingerprint records both its exact runtime type
and its exact representation. Equality-equal string, enum, date, Decimal and
tuple subtypes therefore invalidate evidence, policy, conflict or result state
rather than passing an equality-only digest check. Valid copy/deepcopy of
evidence, policy, conflict and result objects first revalidates issuance and
returns the same immutable object; mutation makes copying fail, and pickle is
refused through the unmodified convenience methods. These class methods are
not the authoritative trust surface under arbitrary in-process class mutation.

The exact tuple is defensively bounded to 10,000 evidence items before any
item traversal, and an aggregate is bounded to 1,000 exact covered-employment
identities before identity traversal. These are technical resource bounds, not
claims about how many employments a customer may have and not reconciliation
or tax policy. Values beyond either bound are rejected rather than truncated.

Aggregate and employment values are never added together. Mixed or unmatched
aggregate scopes fail closed. Same-scope aggregate/entity disagreement and
same-employment candidate disagreement use the explicit conflict policy and
retain alternatives. No evidence set is treated as proving that every
employment exists.

Considered evidence, multi-employment selections, selected IDs, reasons and
conflicts are canonicalised by exact validated identities. Reversing the input
tuple therefore produces equality-identical supported public state. A conflict
between observations outside the explicit recency window retains its known
amount alternatives but reports a partial range with an indeterminable later-
period effect.

## Issued state and authoritative projection

Successful `PayeReconciliation` values are opaque producer-issued handles.
Captured internal validators revalidate the issuance registry, immutable
state, nested conflicts and every selected/considered evidence fingerprint.
Direct construction and low-level reconstruction have no issuance, normal or
low-level mutation fails, `dataclasses.replace` cannot operate on the handle,
copy/deepcopy retain only the same validated instance, and pickle is refused.
Nested evidence or conflict mutation invalidates the whole result.

The only authoritative public read surfaces are the four captured functions:

- `project_paye_evidence`;
- `project_paye_conflict`;
- `project_paye_reconciliation_policy`; and
- `project_paye_reconciliation`.

Each accepts exactly one registered object, validates through captured
descriptors and registries, and returns a deterministic tuple of `(field,
value)` pairs. Nested result evidence and conflicts are recursively projected;
enums become fixed built-in strings, and every returned leaf is a built-in or
an immutable/copy-safe exact `Decimal`/`date`. No public PAYE class instance is
returned inside a projection.

Convenience attribute syntax remains for compatibility in an unmodified
process, but it is explicitly non-authoritative after arbitrary trusted code
uses `type.__setattr__` to replace class `__getattribute__`, properties or
methods. Combined `__getattribute__` and property replacement can make a raw
attribute look forged; it cannot change the captured projectors' registered
output or make mutated state validate. This is a process-local integrity
boundary, not a claim to resist arbitrary trusted projector-code, closure-
memory or interpreter modification.

The reconciliation operation captures all acceptance-critical validators,
types, primitives, policy descriptors, selection helpers and issuance state.
Ordinary module helper, public class, enum, primitive and callable-name
rebinding cannot promote evidence or alter an already captured operation. The
exported reconciliation closure and its reachable validation graph contain no
acceptance-critical `LOAD_GLOBAL` lookup. This does not claim protection from
arbitrary trusted-code closure rewriting or interpreter-memory modification.

## Explicit non-capabilities

This package adds no future-pay forecast, payroll calculation, MTD fact,
cross-endpoint HMRC join, customer copy, refund determination, source
acquisition, transport, OAuth/credential behavior, provider precedence,
persistence, route, payment action, activation, release or launch evidence.
The supplied total liability remains an external estimate whose statutory
correctness this reconciliation does not establish.

## Verification

All commands disabled bytecode generation and pytest caching:

- focused reconciliation/hostile matrix: **68 passed**;
- exact four owned test files: **292 passed, 7 subtests passed**;
- RW3 affected matrix (`test_literal_fixture_runner.py`, `test_rw3_gate.py`,
  `test_progressive_integration_assurance.py`,
  `test_w8_progressive_assurance_s2.py`): **61 passed, 3 failed**;
- release/artefact matrix (`test_release_gate.py`,
  `test_assurance_metadata.py`, `test_artefact_verification.py`,
  `test_engine_adapters.py`): **96 passed, 8 failed, 84 errors**; and
- full suite: **6,112 passed, 11 failed, 84 errors, 7 subtests passed**.

Every one of the 3 affected failures and all 92 release/artefact non-passes
has the same expected cause: the artefact builder refuses the deliberately
uncommitted modified `reserved/engines/paye_reconciliation.py` as a dirty
engine source. The full-suite 95 non-passes are the union of those same
dirty-source refusals; no implementation-specific test failed. The candidate
does not bypass that guard and does not claim release-gate success.

Static closure traversal examined all six exported factory/projector/
reconciliation roots. It found no `LOAD_GLOBAL` in the 3 factory-reachable, 7
evidence/conflict/policy-projector-reachable, 16 result-projector-reachable or
24 reconciliation-reachable functions. AST inspection also confirmed exactly
one `PayeEvidence.observed_on` declaration and one `reduce_confidence`
definition (two conditional returns and one fallback), with no duplicated
unreachable return. The same inspection found no source-priority table or
`source_priority` lookup. `git diff --check` is clean.
