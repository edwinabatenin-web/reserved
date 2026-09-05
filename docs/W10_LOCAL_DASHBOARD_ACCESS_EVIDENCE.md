# W10-S5 local dashboard access enforcement

## Status

**Evidence cut-off:** 5 September 2026

**Candidate status:** IMPLEMENTATION CANDIDATE READY FOR A DIFFERENT INDEPENDENT
REVIEWER. This is an uncommitted, review-ready candidate only. It is **not** a
claim of W10 completion, production custody, provider authenticity, launch
readiness, all-paid-route wiring or independent acceptance.

**Writable candidate paths (the only paths touched):**

- `reserved/billing/local_dashboard_access.py`
- `tests/test_w10_local_dashboard_access.py`
- `docs/W10_LOCAL_DASHBOARD_ACCESS_EVIDENCE.md`

All other paths are read-only during this work, including the app factory/auth/
config/database/routes, existing billing sources (S3C/S5D and the integrated
S3D repository), MTD/PAYE/HICBC runtime and templates, all existing tests,
Founder Decisions, maps and assurance metadata. No source checkpoint, network
tool, model/provider configuration, provider call, credential or production
data is touched.

## Boundary

`reserved/billing/local_dashboard_access.py` is the first actual application
consumer of the already-reviewed W10-S3C runtime-entitlement admission and
W10-S5D paid-access guard. It supplies one explicitly-called, non-production
installer that wraps the already-registered `v2.dashboard_view` view function
for one live Flask application instance.

It is **not** another policy contract, repository composition fixture, detached
decision protocol, new route, environment-selected repository, app schema or
payment action. Nothing happens on import: no application registration, no new
route, no default database path and no side effects. The default application is
unchanged unless a deployment composition root explicitly calls
`install_local_dashboard_access`.

## Effective bindings (explicit server dependencies)

The installer requires five distinct callable dependencies and one optional
clock. It manufactures none of them:

1. **Signed-session identity plus current synthetic-user lookup.** The wrapped
   view reuses `reserved.auth.require_auth` (the original endpoint's own
   authentication decorator) and then re-checks `g.user_id` is an exact `int`
   and that `reserved.database.get_user(user_id)` returns a live row. Deleted,
   missing, non-exact (`str`) or forged session identifiers fail closed before
   any financial read.

2. **Independent owner/account/subscription membership resolver**
   (`membership_resolver`). It is called only with the authenticated user id and
   must return an exact three-`str` tuple. It is never derived from URL, form,
   email, a caller owner argument or repository contents. A non-callable, empty
   or non-exact return denies.

3. **Accepted S3D snapshot/journal identity and ordering** (`snapshot_reader`).
   Must return a `BillingSnapshot` whose `head_identity`/`head_sequence` match
   its last ordered entry, whose entry sequences are exactly `1..N`, and whose
   predecessor links form one contiguous chain. Read only for the authenticated
   owner and the exact resolved billing scope.

4. **Separately validated live billing-fact evidence** (`live_fact_resolver`).
   Resolves each snapshot entry (owner, account, subscription, content identity,
   sequence) to a live fact admitted through the unchanged W10-S3C adapter.
   Structural rows, hashes, provider labels or arbitrary caller tuples are never
   treated as facts; a resolver returning them is denied.

5. **Unchanged S5D decision** (`_paid_access_guard`). The guard is bound with
   `_admission.validate_runtime_entitlement` and
   `_admission.project_runtime_entitlement`, and its decision authorises whether
   the real dashboard executes.

The `validate_admitted_billing_fact` / `project_admitted_billing_fact` pair is
bound through the unchanged S3C `bind_runtime_entitlement_admission`; the module
does not invent another entitlement-decision protocol. The trusted membership
resolver and live fact issuer exist only in synthetic test fixtures. The product
module honestly remains unconfigured for real users: it can bind explicit
functions under the existing engineering composition rules but does not
manufacture `authenticated=True` or authority from a stored row, hash, provider
label or arbitrary caller tuple.

## Snapshot and evaluation limits

- The head chain is admitted in snapshot order. Historical entries are admitted
  at their own exact UTC transition instant so a chain whose earlier validity
  windows have already closed still replays through the unchanged S3C adapter;
  only the head is admitted at the request's evaluation instant. The adapter's
  own future/stale/out-of-order checks therefore bind the head to the exact
  current boundary.
- After each S3C admission, the immutable runtime projection's owner, sequence,
  state, derivation, withdrawal attribution, validity window, transition and
  recovery deadline are matched to that exact structural entry. Its predecessor
  runtime identity must equal the prior admitted runtime identity. This applies
  to every historical entry and the head, not only to the head sequence/owner.
  Account/subscription and fact-predecessor binding remain enforced inside
  unchanged S3C admission against the explicitly resolved scope. These are not
  public runtime projection fields and are not fabricated into that projection.
  The earlier pre-admission fact comparison remains a preliminary check, not
  evidence that the later admitted outcome cannot differ.
- The full scoped snapshot is revalidated at the same authoritative evaluation
  (`snapshot_reader` is read again) and compared field-for-field: owner, account,
  subscription, every entry's content identity, predecessor link and recorded
  outcome/state. If any of these — not merely the head identity/sequence — changed
  during resolution/admission, the grant fails closed. There is no cached positive
  grant, no stale fallback and no retry loop.
- Every failure path collapses into a bounded, value-free `403` with
  `Cache-Control: no-store`, `Pragma: no-cache` and `Expires: 0`. No sensitive
  identifier, provider payload or financial fact appears in the body, headers,
  errors or logs.
- There is no infinite retry. Restart/lost live evidence cannot rehydrate
  positive authority from SQLite alone; the unchanged S3C adapter still requires
  an admitted live fact for each entry.

## Actual-request tests (real Flask route, not a pure helper assertion)

`tests/test_w10_local_dashboard_access.py` drives the real registered
`v2.dashboard_view` through `app.test_client()` with disposable synthetic
SQLite databases in temporary directories. Coverage:

- **Default app untouched / installer contract** — import has no application
  side effects; installer refuses production (`is_production_environment`),
  duplicate, late (`_got_first_request`) and ambiguous (`v2.dashboard_view` no
  longer the registered require_auth-wrapped view) installation; installation
  creates no files.
- **Real authenticated synthetic user** — an exact signed-session user with a
  synthetic `initial_payment_confirmed` fact reaches `200`; absent evidence
  denies `403` with a tripwire proving the dashboard's first financial read
  (`list_connections_for_user`) never runs.
- **Identity denial** — unresolved membership, deleted DB user, forged
  (string) session identifier and a resolver returning a raw structural
  tuple/provider label all deny before financial work.
- **Paid / seven-day recovery** — an independently admitted paid fact followed
  by an admitted `verified_renewal_failure` `payment_recovery` fact (exact
  seven-calendar-day deadline) reaches `200`; the exact recovery expiry
  instant denies `403`.
- **Full current-period withdrawal** — a verified full withdrawal attributable
  to the current subscription period denies `403`.
- **Competing successor / race / replay / fork / cross-scope** — a committed
  withdrawal successor invalidates a previous `200` on the next request (no
  cache); a change between snapshot read and recheck fails closed even when the
  head identity/sequence is retained but the owner/account/subscription or a
  preceding entry's content identity/predecessor/outcome changed; a replayed
  (duplicate-sequence) live fact is never re-admitted; a forked predecessor (an
  entry whose predecessor is not the previous entry) denies; a backwards head
  denies; a different owner/account/subscription denies.
- **Live-fact meaning/provenance binding** — a substituted, independently issued
  same-scope/sequence S3C fact (`paid`/`withdrawal_ambiguous`) is never equated
  to the recorded S3D `paid`→`suspended`/`verified_full_withdrawal` journal entry
  because the two are different hash domains; the mismatch denies `403`.
  An admission-time mutation regression also changes only the issued fact data
  at entry to the original validator after the precheck. Original validator,
  projector and S3C functions are unchanged. A deterministic tracing hook
  schedules that race and observes the actual S3C return: valid paid runtime
  outcomes are issued, but mismatches against the withdrawal journal or an
  earlier paid validity window deny `403` before financial reads/rendering.
- **Malformed or unavailable dependencies fail closed** — malformed snapshot
  entries (`entries=(None,)`), a current-user lookup exception and a clock
  exception each collapse into a value-free no-store `403` before any financial
  read, without exposing exception details.
- **Ambiguous preservation / restoration** — real independently admitted
  ambiguous-withdrawal preservation returns `200` while valid and `403` once
  expired; verified reinstatement after an admitted withdrawal restores `200`;
  prohibited reinstatement (no suspended lineage) and ambiguous extension of an
  existing grant both deny `403`.
- **Corruption / lock / reopen / restart / lost authority** — a corrupted SQLite
  file, a SQLite busy-lock, a closed repository, a reopen after close (which
  recomputes, never caches, the grant) and a lost live-fact resolver all deny or
  fail closed; no positive authority is rehydrated from rows alone.
  The reopen regression now actually closes the first repository, checks its
  old installed consumer denies, then opens the same journal with a fresh app
  and live evidence. This is a close/reopen test, not a process-restart or
  production-recovery experiment.
- **Request-time production denial** — flipping either production signal
  (`FLASK_ENV` or a live `pk_live_` Clerk key) after installation denies the next
  request `403`; the default app stays unmodified and nothing auto-registers.
- **Excluded surfaces** — unauthenticated visitors still redirect to
  `/v2/demo-login`; denial carries no-store headers; the CSRF exemption set is
  left unchanged (the wrapped dashboard is never added to it); the overview
  `/v2/` remains open (only the dashboard endpoint is gated, and every paid
  route is not claimed as wired).
  With Flask-WTF enabled, actual existing `/v2/settings` POSTs with absent or
  forged CSRF tokens return 400 without a profile write; a token obtained from
  the rendered settings form permits the real synthetic profile save/redirect.
  The dashboard remains denied without billing evidence. Dashboard itself is
  GET-only; this tests preservation of an existing modifying surface's controls,
  not a newly protected settings route or all-surface CSRF assurance.

Ambiguous-withdrawal preservation, verified-restoration and
withdrawal-attribution policy is owned by the unchanged S3C/S5D admission and
guard tests (`tests/test_w10_runtime_entitlement_admission.py`,
`tests/test_w10_paid_access_guard.py`); this package only exercises that policy
through the real dashboard-request boundary above and does not re-declare it as
new policy.

## Source identities

- Base commit (clean, immutable): `26831400fcb0ee638761b589b3bbbf0e239427dd`
- Base tree: `2f717f551e91ae95819a5f981902bacdfac12ad9`
- Founder Decisions SHA-256:
  `78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`
- Unchanged W10-S3C source blob (bound by this package):
  `reserved/billing/runtime_entitlement_admission.py` → `3cf09abf3662aa101399bbcbda5751e6da075127`
- Unchanged W10-S5D source blob (bound by this package):
  `reserved/billing/paid_access_guard.py` → `023ca80b3a8f00ca01318fe9f92e0cdd6fdda2e2`
- Integrated W10-S3D source blob (read-only):
  `reserved/billing/local_billing_repository.py` → `ef5627234a20ce2daa803d14595a1691755b08eb`
- Read-only auth/database/web surfaces:
  `reserved/auth.py` → `9bd231a03960ea7f625eff66056a7a6e076681a2`;
  `reserved/database.py` → `52e8a9009e1af1d57595a609bece2983cbddad0f`;
  `reserved/web/v2.py` → `c46246e173be39c14921681bdb8db2ef92e9cc4a`.

The Founder Decision authorities enforced here are FD-W10-003 (seven-calendar-day
`payment_recovery`, no extension) and FD-W10-004 (verified full current-period
withdrawal suspends at the next authoritative evaluation without deleting the
account or its history); FD-W10-001/002 and FD-OA-001 bound scope and authority
without being re-implemented by this package.

## Remaining real custody / provider / membership gaps

This package deliberately does not solve, and must not conceal:

- the real trusted membership resolver (authenticated owner → account →
  subscription) for production users;
- the real live billing-fact issuer / provider-event admission boundary that
  would supply authenticated facts (Stripe observation admission remains a
  separate disabled-first gate under FD-W10-002);
- production custody, signed storage integrity, retention/legal-hold, backups
  and migration authority (the S3D repository is a disposable-local engineering
  datastore only);
- wiring the remaining 27 paid endpoints — this package gates exactly one
  dashboard endpoint and does not claim every paid route is wired.

## All-paid-route wiring

Only `v2.dashboard_view` is wrapped. The other S5A-paid endpoints remain under
their existing (mostly unenforced) registration and are not changed by this
installer. `PROTECTED_ENDPOINT` is a single exact endpoint; there is no
alternate unguarded HTTP path and no general arbitrary-route wrapper.

## Production / launch gates

The installer refuses production using the established
`reserved.auth.is_production_environment` dual-lock (`FLASK_ENV=production` or a
live `pk_live_` Clerk key). The wrapped view re-checks that same dual lock on
every request, so flipping either production signal after installation still
denies request execution (value-free `403`, no financial read). It never performs
an irreversible account action and does not grant launch, release or go-live
authority. It is explicitly called, never automatic, so the default application
remains unchanged and nothing auto-registers in the absence of a composition
root.

## Exact candidate paths

- `reserved/billing/local_dashboard_access.py`
- `tests/test_w10_local_dashboard_access.py`
- `docs/W10_LOCAL_DASHBOARD_ACCESS_EVIDENCE.md`

## Prior recovered candidate hashes (SHA-256; superseded, not accepted)

- `reserved/billing/local_dashboard_access.py`
  `76be57a8611a840f317eed42f1dcee76a59ac44227ef779d158e391330b101a0`
- `tests/test_w10_local_dashboard_access.py`
  `2fa414fff1f852e04a32b61d266824564b9d461f9b8432ba46a98b6162247411`
- `docs/W10_LOCAL_DASHBOARD_ACCESS_EVIDENCE.md`
  `919feef711c6506fe92d065699c16b7a06577be701cb859b1601cd712039096c`

## Final output

IMPLEMENTATION CANDIDATE READY FOR A DIFFERENT INDEPENDENT REVIEWER (uncommitted,
review-ready; not self-assurance, not a completion or launch claim).

## Focused local correction after Cicero's residual P1

The root-authorised local correction is separate from bridge job
`596ca6ca-941e-47ad-aea3-cc45b937dac8`, whose `execution_unverified` classification
and durable routing record remain unchanged. No job replay or runtime success
was inferred. This correction adds the post-admission per-entry binding and
the actual close/reopen and modifying-request CSRF regressions described above.
It changes no shared S3C/S3D/S5D source, identity domain, route or launch gate.

Focused command:
`PYTHONDONTWRITEBYTECODE=1 /private/tmp/reserved-venv/bin/python -m pytest tests/test_w10_local_dashboard_access.py -o addopts='' -q -p no:cacheprovider`

Affected command:
`PYTHONDONTWRITEBYTECODE=1 /private/tmp/reserved-venv/bin/python -m pytest tests/test_w10*.py tests/test_auth.py tests/test_ws7.py -o addopts='' -q -p no:cacheprovider`

Focused result: 45 passed. Affected command: 1547 passed and six failures,
all the pre-existing historical dirty-path sentinels listed below. Additional
`tests/test_dashboard.py tests/test_auth_claims.py` run with the same options:
38 passed. No skips or suppressed failures; no allowlist or source pin changed.
The expected sentinel failures reject these three untracked candidate paths
because their own historical package allowlists do not include this package:

- `test_w10_completion_map.py::test_candidate_is_confined_to_the_authorised_map_and_dedicated_test`
- `test_w10_initial_paid_presentation.py::test_diff_is_confined_to_exact_package_paths`
- `test_w10_initial_payment_presentation.py::test_git_diff_is_limited_to_exact_authorised_paths`
- `test_w10_internal_route_hardening.py::test_candidate_changes_only_authorised_route_and_test_paths`
- `test_w10_paid_access_guard.py::test_candidate_is_confined_to_exact_three_owned_paths_and_base`
- `test_w10_q1_q2_policy_closure.py::test_candidate_is_confined_to_three_new_non_colliding_paths`

The broad command therefore exits 1, not an overall pass. No unexpected
behavioural test failure remains. Corrected exact three-file hashes accompany
the frozen handoff; independent re-review remains required.
