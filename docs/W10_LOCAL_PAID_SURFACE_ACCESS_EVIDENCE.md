# W10 settled paid surfaces — explicit local request wiring

Candidate for independent review, not self-acceptance or production activation.
Immutable base: `c935df93f844af86eb820273d691827aac6e1e47`; base tree:
`ba8ad31114a400dc7f63873d4d0b4e84cb982686`. Implementation version:
`reserved-w10-local-paid-surface-access/1.0`.
Authority: root `work/w10-local-paid-surfaces-authority.md`, existing Founder
FD-W10-002/003/004, S2F, S5A and the exact S5D `PAID_ENDPOINTS` class.
Founder source SHA-256 remains
`78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`.

## Actual implementation boundary

`install_local_paid_surface_access(app, ...explicit dependencies...)` is called
only by a local synthetic composition root, before the first request. Importing
the module installs nothing. The exact 19 v2 endpoints and, only when already
registered by the existing feature gate, nine HICBC endpoints are validated as
one set before any view replacement. It neither registers HICBC nor changes an
environment flag. Names alone are insufficient: original decorated function
identity, wrapper code, exact URL/method rules and duplicate/alias checks are
validated. Missing/partial/changed registration, duplicate/late installation and
conflict with the standalone dashboard installer refuse without view mutations.

The original decorated handlers run intact after admission. Authentication is
also required before the shared evaluation; authentication, feature guards,
existing CSRF exemptions and Flask's method dispatch are not unwrapped away.
No routes, templates, app defaults, policy classes, database schemas or shared
S3C/S3D/S5D contracts change. Standalone dashboard evaluation defaults to its
original endpoint; the new caller supplies an exact S5D endpoint. The narrow
shared change rejects any other endpoint before reading membership or billing.

Signed synthetic session → current user lookup → independent synthetic
membership → full disposable S3D journal → live synthetic fact authority → real
S3C admission for every entry → immutable admitted-outcome/journal binding →
full scoped journal recheck → real S5D decision → original handler. Structural
journal hashes are not live fact authority, S3D/S3C identities remain separate,
and account/subscription scope is still checked by S3C. All accepted dashboard
admission-race protections remain in this shared path. Both existing production
signals refuse installation and are rechecked during requests; failures return
the existing empty no-store denial. There is no cached grant.

## Executed synthetic request evidence

`tests/test_w10_local_paid_surface_access.py` reuses the existing dashboard
tests' synthetic issuer and repository fixtures, not an admission-success stub.
Both application and billing databases are disposable temporary files.

- All 28 actual registered endpoints have missing, expired and withdrawn access
  requests (84 cases). A trace tripwire on each original handler body proves it
  is not entered. Withdrawn cases additionally observe the exact endpoint passed
  into unchanged S5D evaluation. Provider-facing bodies cannot execute in these
  negative requests; no live provider calls are used.
- Paid settings GET renders the real form token; missing/forged tokens reject
  real POSTs without profile mutation; the valid token saves the actual scoped
  profile and redirects to the real dashboard. JSON pension calculation invokes
  the existing engine; scenario POST/save and DELETE run the actual database
  handlers, with existing exemptions unchanged. A different user's saved row
  survives the paid user's DELETE. HICBC result JSON executes while disabled
  annual-preview, PAYE and MTD preview controls remain closed.
- Registration tests preserve original wrapper chains, excluded functions,
  URL rules, unsupported-method rejection, automatic OPTIONS and anonymous
  authentication. Both pre-existing HICBC registration sets are tested (28/19),
  including rejection of partial HICBC registration. Aliases of decorated views,
  their direct bodies and wrapped aliases are rejected at installation.
- Recovery permits within the existing window and denies at the exact exclusive
  midnight boundary; withdrawal invalidates a previous grant; verified
  restoration permits again; ambiguous preservation cannot extend expiry.
- Missing membership, cross-owner/account/subscription facts, deleted users,
  lookup errors, malformed journal and changed recheck scope deny. An actual
  admission-time data mutation changes the withdrawal fact to a same-scope,
  identity-recomputed ambiguous paid fact: unchanged S3C genuinely admits it,
  but post-admission journal binding denies the settings request. No validator,
  projector or admission result is replaced with a successful stub.

The executable tests are local Flask request evidence, not browser/visual or
human acceptance. Positive coverage is representative, not positive execution
of every provider-facing handler. Automatic OPTIONS does not enter financial
handlers and retains existing behavior. Existing CSRF exemptions are preserved,
not endorsed as a new security policy. Function/wrapper checks are installation
consistency checks, not a sandbox against arbitrary hostile in-process code or
permission to modify registrations after installation.

## Verification disposition

Commands use `PYTHONDONTWRITEBYTECODE=1 /private/tmp/reserved-venv/bin/python -m
pytest`, with `-o addopts='' -q -p no:cacheprovider`:

- New test file plus unchanged `tests/test_w10_local_dashboard_access.py`:
  160 passed (115 new and 45 standalone dashboard).
- `tests/test_w10*.py tests/test_auth.py tests/test_auth_claims.py
  tests/test_ws7.py tests/test_hicbc*.py`: 2,159 passed, six failures. These six
  unsuppressed historical dirty-candidate allowlists reject this separately
  authorised four-path package, not request/admission behavior:
  `test_w10_completion_map::test_candidate_is_confined_to_the_authorised_map_and_dedicated_test`,
  `test_w10_initial_paid_presentation::test_diff_is_confined_to_exact_package_paths`,
  `test_w10_initial_payment_presentation::test_git_diff_is_limited_to_exact_authorised_paths`,
  `test_w10_internal_route_hardening::test_candidate_changes_only_authorised_route_and_test_paths`,
  `test_w10_paid_access_guard::test_candidate_is_confined_to_exact_three_owned_paths_and_base`,
  `test_w10_q1_q2_policy_closure::test_candidate_is_confined_to_three_new_non_colliding_paths`.
  No sentinel, source pin or inventory is weakened or suppressed.

No full-repository or canonical gate result is claimed for this candidate.
Final file/diff hashes are supplied separately to avoid self-referential hashes.

## Gates deliberately still open

This is explicit non-production local composition, not default application
wiring or full W10-S5 completion. Live user/billing membership, authenticated
billing ingress, provider custody, credentials, deployment/hosting and production
activation remain unconfigured and gated. Synthetic callables do not establish
any of these authorities. No new retention, annual-position persistence,
provider, payment, consent or pricing policy is introduced. Full October gates
and all completion-map denominators remain untouched. Root alone retains
independent review, checkpoint, integration and launch decisions.
