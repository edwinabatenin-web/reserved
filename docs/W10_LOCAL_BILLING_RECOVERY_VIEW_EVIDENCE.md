# W10 local admitted recovery panel

Candidate for independent review, not acceptance, activation or full S6 closure.
Base `c165544f5e3d37d6d46b3cc74a39eba486af5c17`, tree
`47feb279ee2324650249ef5f3c2408cdebc8af01`; version
`reserved-w10-local-billing-recovery-view/1.0`.
Authority: root `work/w10-local-billing-recovery-authority.md`, current Founder
FD-W10-003 and FD-W10-004, unchanged S6E presenter and S3C admission semantics.
Founder SHA-256:
`78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`.

## Real request composition

Explicit `install_local_billing_recovery_view` installs a local
`before_render_template` supplier, scoped to the exact authenticated
`v2.billing_plans` GET and `v2/plans.html`. It does not replace the pinned route
closure, register a route, include plans in paid endpoints, or activate itself.
Installation refuses production, late/duplicate installation, changed routes,
aliases, method changes and invalid dependencies before publishing a supplier.
The supplier rechecks exact route registration at render time, removes conflicting
values in its reserved context key and refuses a claim on conflict. It composes
with the accepted paid-set installer in either order.

The shared dashboard path now factors out only its full rechecked admission
stage. Current synthetic user lookup, independent membership, exact scoped
journal, each separately live issued fact, original S3C admission, per-entry
immutable admitted-outcome matching and complete scoped snapshot reread are
unchanged. It returns the independently resolved scope and admitted handles,
not an entitlement derived from a row. Dashboard/paid callers still use the
same exact endpoint validation and original S5D decision after this stage.

The recovery supplier projects the immutable admitted current handle only after
that recheck. It requires `payment_recovery`, `verified_renewal_failure`, ordinary
access and the correct owner. It checks the full UTC request instant against
the admitted start and exclusive deadline before formatting S6E's second strings;
microseconds cannot make future or expired evidence eligible. The recorded
start/deadline are not recomputed or extended. Ordered S6E facts contain only
these admitted fields and independent scope; both original builder and validator
run. The resulting fixed-copy deadline must also equal the admitted deadline.
Every S6E authority flag remains false. Only fixed copy enters the autoescaped
template context, never membership identifiers, journal/fact identities or handles.

Missing, malformed, stale, unadmitted, changed or cross-scope evidence yields no
status claim. No paid/suspended/recovered claim is invented. Prices, plan links,
the purchasing-unavailable notice and existing auth/no-store controls remain.
The panel introduces no action, form, modifying method or notification.

## Synthetic evidence

New tests reuse existing disposable application/S3D database and live synthetic
issuer fixtures. They execute the actual signed Flask request and unchanged S3C,
not a successful-admission stub:

- Recovery history renders fixed recovery wording and the exact exclusive
  `8 November 2026 at 00:00:00 UTC` deadline beside all three existing prices.
- Before/start/after-start, microsecond-before-expiry, exact/after-expiry,
  malformed and naive clocks are tested. Repeated requests do not cache a claim.
- Verified successful renewal and current-period withdrawal remove the prior
  recovery panel. Paid, suspended, reinstated and ambiguous paid histories do
  not masquerade as recovery. Duplicate failed-renewal insertion preserves the
  existing deadline. Unsupported ambiguous recovery evidence is not coerced into
  a new shared admission policy or extended window.
- Missing/deleted/forged/anonymous users, owner/account/subscription mismatch,
  request-supplied scope, structural-only data, source identity mismatch,
  malformed/changed rereads and dependency exceptions produce no claim.
- A tracing hook changes fact lineage at entry to the unchanged live validator;
  original S3C refuses the mutated lineage. Existing dashboard tests additionally
  retain the admitted-success mutation regression for immutable post-admission
  outcome binding. No validator/projector is replaced with a success shortcut.
- Hostile fixed-copy substitution and a coherent but different valid S6E
  deadline are rejected. Supplemental template checks prove HTML/attribute
  escaping, not independent admission. Conflicting context is removed rather
  than rendered. Different template/endpoint, HEAD and production toggles do
  not render a panel.
- Both paid-set installation orders preserve the original plans function and
  allow recovery plans while denying ordinary paid access at expiry. Existing
  actual settings CSRF tests run unchanged in the focused/affected matrix.

These are local executable request/template tests, not browser, human or visual
acceptance. Installation checks do not sandbox arbitrary hostile in-process code.
No provider-facing handlers, network, credentials or default database are used.

## Verification

All commands use `PYTHONDONTWRITEBYTECODE=1 /private/tmp/reserved-venv/bin/python
-m pytest` and `-o addopts='' -q -p no:cacheprovider`.

- `tests/test_w10_local_billing_recovery_view.py
  tests/test_w10_local_dashboard_access.py
  tests/test_w10_local_paid_surface_access.py`: 209 passed (49 new recovery,
  45 unchanged dashboard and 115 unchanged paid-set tests), 4.83 seconds.
- `tests/test_w10*.py tests/test_auth.py tests/test_auth_claims.py
  tests/test_ws7.py tests/test_hicbc*.py`: 2,208 passed and six historical
  dirty-path sentinel failures, 26.37 seconds; no errors or skips reported.
  The unsuppressed historical dirty-candidate failures are the path allowlists in
  `test_w10_completion_map`, `test_w10_initial_paid_presentation`,
  `test_w10_initial_payment_presentation`, `test_w10_internal_route_hardening`,
  `test_w10_paid_access_guard`, and `test_w10_q1_q2_policy_closure`. Their older
  package paths do not include this separately authorised package. No allowlist,
  historical identity or source pin is edited or suppressed.

Exact hashes and diff are supplied separately. No canonical/full-repository
result is claimed for this candidate. Only the five authorised paths change.

## Gates retained

This is non-production synthetic recovery rendering only, not a default billing
status service or full S6/W10/October completion. Live membership, authenticated
provider ingress, custody, global durability, hosting/activation, legal/finance
and target-environment gates remain. No initial-payment, cancellation or
selected-plan status authority is inferred. Existing pricing, paid classes,
CSRF, database, provider and completion-map sources are protected. Root retains
independent review, checkpoint and integration authority.
