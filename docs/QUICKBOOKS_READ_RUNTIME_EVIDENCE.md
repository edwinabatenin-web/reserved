# QuickBooks injected acquisition execution

Status: uncommitted candidate requiring different independent review and root
checkpoint/integration. Not an acceptance or provider activation. Immutable base
`ea6a0fc217147471b5e247ffd9d9d220e93b37f6`, tree
`a1c20a7861e1cb6056bd6a38a2e09a6441943eb9`;
version `quickbooks-injected-read/1.0`.

## Authority and executable endpoint

The Founder October read-only accounting target and W9-S2 opaque-reference
permission are implemented only to the extent explicitly dispatched in
`work/quickbooks-read-runtime-authority.md`. Founder Decisions SHA-256 remains
`78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`.
Only the new runtime, its test, this evidence and the QuickBooks completion map
change. No shared OAuth, HTTP, Q-S1/Q-S4/Q-S5 source, canonical mapping, provider
registry, route, configuration, database or billing file changes.

`InjectedQuickBooksRuntime` executes a real sequence through an explicitly
injected synthetic transport: callback state consumption, Q-S1 callback parsing,
code exchange, full token-set put, atomic full-set refresh, CompanyInfo read,
bounded Invoice query pages, real Q-S4 observation and Q-S5B query validation.
There are no precomputed successful observations, network client, socket,
provider sessions, SDK, credentials, default database or successful fallback.
The literal sandbox origin is request data, not permission to contact it.

Only the exact `injected_test` profile runs. Production and other profiles are
refused before dependencies; the profile is rechecked around calls and clocks.
These checks are local call-result controls, not an in-process sandbox or proof
that an arbitrarily supplied dependency is safe. The application caller still
needs authentic user/session ownership and authorised custody before live use.

## State, custody and operation lifetime

A separately supplied current `FixtureBinding` contains owner, numeric realm,
opaque QuickBooks reference, revision, lifecycle and expiry. Initial exchange
requires pending state; refresh accepts active/refresh-required; reads require
active. CompanyInfo.Id may be `1` while the selected realm differs: provider
labels are never membership proof. Bound realm is used in both URI positions.

The exact neutral OAuthStateStore consumes provider-bound, short-lived state
before the neutral one-use code is consumed and Q-S1 parses the disjoint callback.
Later realm/parse/exchange failures cannot redeem that state again. This is not
a new durable/global provider-code replay ledger, nor caller authentication.

Injected custody supplies Basic client auth, full `FixtureTokenRecord` loads,
and `put`/`replace`. A load is conditioned on current revision. Each write takes
the expected complete binding and must atomically install the entire unchanged
Q-S1 QuickBooksTokenSet, receipt time and active binding at exactly revision + 1.
The fixture implements that compare-and-swap; runtime checks the returned opaque
reference, current binding and full stored record afterwards. Never delete old
first. The smaller neutral OAuthTokenSet is deliberately not substituted because
it would lose QuickBooks refresh expiry metadata. Both refresh expiry fields
remain intact; additive token-response fields retain no invented meaning.

Every operation uses one nondecreasing UTC clock baseline through initial
snapshot, dependency calls and finalization, including the expected revision
transition. Access expiry, refresh expiry, supplied hard expiry and lifecycle
expiry are checked for the relevant operation. New tokens' receipt time is
retained. The runtime does not infer an undocumented hard-expiry continuity rule
across rotated provider responses. A committed write followed by refusal can
remain committed: no rollback, erasure, recovery or live atomicity is claimed.

## Wire evidence and local translation

Public sources below were rendered/read by root on 5 September 2026 and retained
in the dispatch authority; this candidate did not make provider calls.

- [Official OAuth](https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0):
  POST token exchange/refresh, Basic client auth, form body, JSON Accept; Bearer
  for API reads. Unchanged Q-S1 builders/parser provide provider-specific fields.
- [CompanyInfo READ](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/companyinfo):
  realm-scoped company URI and CompanyInfo/time JSON wrapper. Id is not realmId.
- [Data queries](https://developer.intuit.com/app/developer/qbo/docs/learn/explore-the-quickbooks-online-api/data-queries):
  GET query with encoded SELECT, one-based STARTPOSITION and bounded MAXRESULTS.
  Requests use fixed Invoice SELECT, page size 25 and minorversion 75. No caller
  query, origin, filters, links or URLs are accepted.
- [Invoice Query JSON](https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/invoice):
  root read the complete JSON-selected example with outer QueryResponse/time,
  Invoice array, startPosition, maxResults and totalCount. The example is not
  evidence that every metadata field is mandatory or that totalCount is absent
  outside COUNT queries.
- [Intuit mock guidance](https://github.com/intuit/quickbooks-online-mcp-server/blob/main/docs/TESTING.md):
  empty search `{QueryResponse:{}}` is fixture guidance, not a live Invoice
  terminal-page capture.
- [Official SDK schema](https://static.developer.intuit.com/sdkdocs/qbv3doc/ipp-v3-java-devkit-javadoc/com/intuit/ipp/data/QueryResponse.html):
  XML-derived optional pagination metadata/absent objects supports preserving
  absence, not a universal JSON required-key schema.
- [General REST features](https://developer.intuit.com/app/developer/qbo/docs/learn/rest-api-features):
  JSON/UTF-8, ordinary response metadata and tracing headers. Bounded ordinary
  headers, including `intuit_tid`, are tolerated without authority or retention.

The bounded envelope subset accepts CompanyInfo or QueryResponse plus optional
offset timestamp `time`; unknown outer/query keys, Faults and malformed values
refuse. A QueryResponse missing Invoice is accepted only if exactly empty.
Invoice when present must be an exact array. Supplied position must equal the
sent position; supplied maxResults must equal the actual array count. Supplied
totalCount must be a nonnegative exact integer at least as large as that page's
array count. It is retained per response only, not equated across pages or
passed as an independently observed global total. No undocumented global-count
semantics or snapshot guarantee is inferred.

Every page retains the exact wire SHA-256, request identity, sent position,
locally counted records, provider metadata values/absence, provider timestamp
and local retrieval time. Position/count origin labels distinguish provider
cross-checks from request-derived/array-counted local values. The unchanged
Q-S5B wrapper receives those explicit local mechanics; `requestIdentity` is not
invented provider data. Q-S4 retains the exact accepted source graph and its
independent type-preserving digest/attestation. Wire and entity digests differ
deliberately. No token response or sensitive HTTP header is included in outcomes.

Empty/short pages terminate only the bounded local traversal. Q-S5B keeps
`canonical_ingestion` prohibited, fitness UNVERIFIED, source total absent and
snapshot/order/completeness limitations. No canonical document, accounting
recognition, tax/settlement decision, annual estimate or customer output follows.

## Failure limits and executable tests

Bounds: 20 pages, 250 records, 262144 bytes per body, 2097152 aggregate read
bytes, JSON nesting 16, 15000 graph nodes, width 1000, strings 4096. Numeric
lexemes have at most 18 integer digits/12 decimal places/32 total characters;
decimal values never pass through floats. Only UTF-8 bytes are decoded;
duplicate keys, nonfinite/exponent/overprecision values and unsafe Unicode fail.
32 bounded response headers are permitted; duplicate names, content encoding,
redirect location, wrong content type and non-200 status refuse. No retry,
redirect following, cookie store or Link-derived requests.

All failing page operations discard the successful-run outputs. Tests execute
the full chain and independently compare actual observer output, literal money,
wire digest and precise outgoing requests. They cover metadata-bearing and
strict empty pages, Q-S4/Q-S5B refusal, duplicates/gaps/count contradiction,
wrong envelope/entity/identity, malformed bytes/graphs, headers/status failures,
aggregate bounds, callback replay/provider/expiry, full latest-token rotation,
CAS ambiguity, disconnect/revocation/generation changes during each request,
production toggles inside dependencies and every acquisition clock tick,
rollback through storage transitions and token expiry at the final clock tick.

Verification commands (synthetic only):

```
PYTHONDONTWRITEBYTECODE=1 /private/tmp/reserved-venv/bin/python -m pytest tests/test_quickbooks_read_runtime.py -o addopts='' -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 /private/tmp/reserved-venv/bin/python -m pytest tests/test_quickbooks*.py tests/test_oauth_contracts.py tests/test_provider*.py tests/test_import_evidence.py tests/test_accounting*.py tests/test_freeagent*.py tests/test_xero*.py -o addopts='' -q -p no:cacheprovider
```

Focused final source: 186 passed; affected matrix: 2181 passed, no failures or
skips (exit 0). Initial tests caught a too-narrow header-name
validator; a later final-clock regression drove token deadline checks through
the last return check. Neither earlier green tests nor these tests constitute
independent acceptance. No full canonical gate or live/browserverified claim.

Q-S2 real custody/transport/revocation, Q-S3 authenticated routes and lifecycle,
full Q-S5 canonical ingestion and UK VAT QBO-01, and Q-S6 sandbox/operational,
privacy/security and activation gates remain open. Storage policy, credentials,
production enablement and launch authority are unchanged.

## Focused independent-review correction

The initial independent review reproduced a P2 aliasing defect despite the
186/2181 green tests: dependency-owned binding and token records were retained
as comparison baselines, and custody received the same expected objects used
for verification. In-place fixture mutation could therefore produce mixed-realm
observations, rewrite returned binding evidence, or conceal token-set changes.

The focused correction detaches and validates complete binding/reference and
token-record/token-set snapshots. Custody receives separate copies rather than
the retained expected values. Stored results are checked against those private
values; a committed-but-refused write still makes no rollback claim. This is
protection against supplied-object aliasing at the declared dependency boundary,
not a sandbox against arbitrary runtime-code modification.

Eleven new regression cases cover in-place realm/state/revision changes,
post-return nested-reference mutation, previous token/record/receipt mutation,
callback binding changes, mutated expected CAS arguments, and hard-expiry
removal after put/replace. Focused corrected tests: 197 passed; the same affected
matrix above passed 2192 tests with no failures or skips. Independent
re-review of this correction remains required; no acceptance is inferred.
