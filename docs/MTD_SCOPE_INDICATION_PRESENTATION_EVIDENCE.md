# MTD customer-indication HTML presentation evidence

## Candidate and authority

`IMPLEMENTATION CANDIDATE READY FOR FRESH INDEPENDENT REVIEW`

- Branch: `codex/mtd-scope-indication-presentation`
- Immutable base/HEAD: `a26c0badf0a19a4862c892cab30d966b70d27c74`
- Base tree: `61061a5f84d51e38ee993f29310fa375a1b7cb0b`
- Scope: one new renderer, one new template, one new focused test and this
  evidence record.

This package consumes the accepted customer MTD-indication boundary. It does
not change the MTD engine, service, Founder authority, route, persistence,
authentication, configuration, assurance metadata or release gate.

## Renderer boundary

`render_mtd_scope_indication(value) -> str` accepts only an exact live
`MtdScopeIndication` and calls the captured genuine `as_mtd_scope_mapping`.
The renderer validates the exact ordered 19-field approved mapping, including
exact built-in string key types, and renders only:

- the exact feature label **Could Making Tax Digital apply to you?**;
- the exact approved **More information needed**, **Worth reviewing**, or
  qualified **Not currently indicated** headline and matching summary;
- the exact gross-income-before-expenses and local-planning-versus-HMRC-formal-
  determination explanations;
- issued assessment, mandatory and effective date facts when present;
- issued monetary facts only when `information_complete` is exact `True`; and
- the closed source-category vocabulary and exact included, business and
  excluded counts, never opaque source or business identifiers.

The output contains no link, button, form, filing action, provider action,
network action or other authority. The action flag must be exact `False`.

## Core remains the only MTD rule authority

The renderer has no assessment-year-to-threshold or assessment-year-to-
mandatory-year table. It does not calculate an MTD status, qualifying income,
threshold, effective year or materiality decision. Those facts and decisions
must come from the exact accepted live handle through the genuine captured
projector.

Renderer validation is presentation-level only: conventional consecutive-year
tax-year shape, a mandatory start year strictly later than the assessment start
year, the effective `YYYY-04-06` date corresponding to the issued mandatory
year, exact finite Decimal representation, exact issued distance coherence,
complete-versus-incomplete visibility, closed copy, safe categories and
coherent non-negative counts. A complete result with no included source must
carry exact zero qualifying income; any non-zero qualifying income requires at
least one included source. Zero-income included sources remain valid.
Consequently a later accepted core rule-table change does not require a
renderer table edit. Any new mapping schema or copy contract still requires an
explicit reviewed renderer version change.

## Fail-closed and integrity behavior

The exact handle type, projector, schema, fixed copy, category vocabulary,
primitive operations and bound compiled-template renderer are captured at
import. Rebinding public class methods, module names, helper names, constants,
Jinja constructors or builtins cannot change the supported renderer.

Forged, reconstructed or subtyped handles; projector exceptions; non-proxy,
missing, extra or substituted mappings; type/subclass violations; unknown or
mismatched copy; unexpected action flags; malformed dates; unsafe categories;
incoherent counts or money; and render exceptions all return the same
pre-rendered generic **More information needed** fragment. It never includes
exception text or rejected values.

The Jinja template is loaded and compiled once at module import with HTML
autoescaping. Request-time rendering is deterministic and has no filesystem,
network, provider, persistence, database, authentication, route, logging,
scheduling or configuration behavior. The fragment uses a labelled heading and
`role="status"`, `aria-live="polite"`, `aria-atomic="true"` semantics.

## Explicit limitations and remaining gates

This is a renderer only. It does not acquire or orchestrate source facts,
establish residence/cessation/timing/annualisation completeness, schedule an
evidence recheck, add an authenticated route, persist an indication, perform
target browser or UX acceptance, activate a provider, close privacy/security
review, amend release evidence, deploy or authorise release/go-live.

Re-invocation of the accepted core on changed evidence remains the recheck
boundary. Route/source orchestration, target accessibility/UX evidence and the
applicable privacy, security and release decisions remain separate gates.

## Verification

All test commands disable bytecode generation and the pytest cache. Final
results:

- focused renderer: **45 passed**;
- required renderer + accepted MTD service/engine/literal matrix: **122 passed**;
- affected template/security compatibility matrix: **245 passed**; and
- full repository suite: **6,141 passed, 7 subtests passed**.

`git diff --check`, exact four-path scope, protected accepted-MTD hashes and
final SHA-256 hashes were checked at freeze:

- renderer: `038dcb61d070d8e3e08375b882499221190e038cbc4fbe6c157c27f30d3e7d86`;
- template: `7ac0dce07e0a70acc97ba15a2156f62cb448b7d75aaddd7df02fcf847606c151`;
  and
- tests: `ef5d8d1ac2cfa807ce344e899e1b4e437cb21f57e9d21c0dd776e69cd41c2fb8`.

This document omits its own self-referential hash; it is supplied with the
candidate handoff.
