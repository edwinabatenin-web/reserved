# PAYE reconciliation customer-evidence presentation

## Candidate boundary

`IMPLEMENTATION CANDIDATE — PENDING FRESH INDEPENDENT REVIEW`

- Branch: `codex/paye-reconciliation-presentation`
- Immutable base/HEAD: `c23d343032a3bfd94e8ba1bda45cc5361b3fff40`
- Base tree: `bb2648ee992f1acbcced632eb049928a67da400b`
- New service: `reserved/services/paye_reconciliation_presentation.py`
- New template: `reserved/templates/v2/_paye_reconciliation.html`
- New hostile tests: `tests/test_paye_reconciliation_presentation.py`
- Completion-map change: this exact sub-boundary only.

No PAYE engine, capture/extraction producer, HMRC/provider contract, annual or
cash engine, MTD boundary, route, database, persistence, configuration,
credential, Founder Decision, release metadata or other completion map changes.

## Trusted input and fail-closed shape

`render_paye_reconciliation` accepts only an exact live producer-issued
`PayeReconciliation`. It never reads result attributes. The renderer captures
the genuine `project_paye_reconciliation` at import and validates the exact
ordered 21-field projection, including exact built-in types and representations,
nested evidence/conflict schemas, tax year, identifiers, money, dates,
provenance, counts, selection correspondence, source-neutral selected kind,
confidence, warning order and each status-specific invariant.

The tax year must also produce exact statutory 6 April through 5 April bounds
using the captured date constructor. Every nested effective date must fall
inside those bounds, and every observation must be no later than the tax-year
end because the engine's accepted `as_of` is itself inside the year. Where an
effective date exists, the observation must not precede it. This retains the
engine's support for pre-year observations that have no asserted effective
date while rejecting impossible years and cross-year selected evidence.

Missing, extra, reordered, subtyped, malformed, reconstructed, mutated,
future-status or incoherent state returns one byte-identical generic refusal.
Projector errors, non-tuple projections, renderer errors and non-text template
results return that same refusal without echoing a source value or exception.
Module/class/helper rebinding and combined result attribute-dispatch mutation do
not replace the captured projector or trusted renderer graph.

## Customer-safe presentation

Exactly four current reconciliation states are supported:

- `calculated`;
- `calculated_with_material_uncertainty`;
- `conflict_requires_review`; and
- `insufficient_facts`.

Confidence becomes only fixed copy saying that evidence looks reliable, looks
fairly reliable, or needs more information. The renderer never describes the
annual liability as HMRC-confirmed and never calls the derived figure tax owed,
a bill, future payroll, a set-aside or a payment. When a direct point is safe,
it is labelled only as the annual estimate supplied to Reserved less tax
currently evidenced as deducted, before future payroll deductions.

Bank inference shows its safe category, suppresses tax-deducted and derived
point amounts, and asks for direct PAYE evidence. Conflicts show no point result;
a range appears only for exact complete identified uncertainty with no
indeterminable effect. Stale/partial state is visible. An apparent overpayment
is explicitly provisional and neither a confirmed nor available refund.

Only the customer-safe tax year, fixed source category, evidence date/status
and approved money labels are rendered. Employment, evidence and source IDs,
selection reasons, policy, digests and raw warnings are validated but never
placed in the model or HTML.

## Rendering and non-capabilities

The Jinja template is compiled once at import with HTML autoescaping. The
request-time closure has no filesystem, network, provider, logging,
persistence, route or action behavior. The template uses accessible status and
description-list semantics and has no form, link, button or script.

This is renderer-only evidence. It does not provide source orchestration,
upload/OCR/confirmation, deletion/retention, authentication, routing,
persistence, forecast, payment, provider access, activation, target-user UX
acceptance, release evidence or launch readiness.

## Verification

All commands disabled bytecode generation and pytest caching:

- focused presentation tests: **38 passed**;
- presentation plus PAYE reconciliation, capture, extraction, independent-v1,
  customer-language and template/security compatibility: **392 passed, 7
  subtests passed**;
- release, artefact, RW3 and progressive-assurance matrix: **244 passed**; and
- complete repository suite: **6,245 passed, 7 subtests passed**.

Recursive disassembly of the request-time renderer and its 26 reachable
closure functions found no `LOAD_GLOBAL`. Static source inspection confirms
that template/environment/path construction occurs only at import, while the
request-time renderer calls only captured validation, projector and compiled
template collaborators. `git diff --check` is clean. These synthetic results
do not constitute target-user UX, production security, release or launch
evidence.
