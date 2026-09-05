# Xero injected acquisition — candidate 1.0

Uncommitted and pending different independent review. Exact base
`bd68ab48e4394b06470c20c6035384b6f78cd1a4`, tree
`2a8f3b6d0078c92f807fef8360440497a65cf146`; Founder SHA-256
`78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`.
Authority: `work/xero-read-runtime-authority.md`; preparation:
`work/xero-acquisition-preparation.md`. Version `xero-injected-read/1.0`.

## Actual executable sequence

`InjectedXeroRuntime` has no default transport, store, binding source, clock or
environment. The synthetic caller composes three operations:

1. `complete_callback` validates provider-bound state internally, consumes the
   resulting one-use code through `exchange_and_store`, posts the accepted
   X-S1 exchange form, parses the returned token set and calls the opaque store.
   It returns only a validated Xero credential reference after checking its
   independently supplied owner binding, never raw tokens or a code.
2. `refresh` resolves the usable reference/binding, posts the accepted refresh
   form, validates the complete new token set and calls neutral
   `refresh_and_rotate` through a guarded replacement boundary. It never deletes
   the old set first. The fixture must atomically publish the complete pair and
   a later binding revision; matching owner/connection/tenant/event/reference
   and active state are rechecked after replacement.
3. `acquire` requests connections, uses X-S1 explicit event-and-tenant selection,
   checks its connection ID against the independent binding, then requests
   successive detailed invoice pages. Every record goes through unchanged
   `map_detailed_invoice_response` and actual `normalise_document`. Only a final
   empty page returns documents, observations and a bounded import manifest.

No precomputed import or mocked normalisation result is used in the positive
test. The recorded sequence includes two token POSTs, connections GET, two
nonempty invoice GETs and an empty third invoice page. Independently specified
JSON amounts yield £100 net + £20 tax = £120 gross on each of three documents.

## Source facts and engineering restrictions

Existing `XERO_XS1_OAUTH_CONTRACT_EVIDENCE.md` and
`XERO_INVOICE_CONTRACT_EVIDENCE.md` govern endpoints, Basic/Bearer placement,
read-only scope, connection selection and invoice semantics. The runtime uses
those builders/parsers unchanged. Root separately inspected the rendered
[official paging page](https://developer.xero.com/documentation/best-practices/api-call-efficiencies/paging/)
on 5 September 2026, recorded in the preparation above: paged Invoices include
detail, `page`/`pageSize` are supported, default size 100 and maximum 1,000,
and traversal continues until an empty page. No new web/provider calls were made
by this implementation.

This executor deliberately selects pageSize 25, maximum 20 pages including the
terminal empty page, 250 invoices, 256 KiB per response and 2 MiB combined
connection/invoice response bytes. Short nonempty pages do not terminate.
No total count, source watermark, stable ordering or atomic snapshot is invented.
Even successful manifest status is UNVERIFIED; page exhaustion is not complete
annual income, freshness or fitness for a tax purpose.

Exact fixed request kinds construct only Basic-authenticated form POSTs to the
accepted token endpoint, Bearer connections GETs and Bearer invoice GETs with
explicit `xero-tenant-id` and generated sequential `page`/`pageSize`. No caller
URL, next-link, summaryOnly, alternate filter, redirect or retry is delegated.
Basic syntax is checked as bounded valid base64 with nonempty client/secret
parts, not verified against a real registration. All destinations pass the
neutral origin guard as well. `injected_test` is required; production, sandbox,
test and absent selections refuse before initial transport/custody. Environment
is rechecked during execution; no distinct Xero sandbox origin is invented.
These URLs are request data for explicit fixtures, not network authorization.

Responses require exact ProviderResponse objects, integer status 200 and only
a supported JSON Content-Type header. Redirect, rate-limit and extra headers
are not interpreted. Non-success 401/403/429/5xx have bounded literal status
classifications, not inferred retry/grace/revocation policy. Other failures use
fixed generic classifications; exception text is never copied. There is no
sleep, retry, redirect follow, refresh grace-period replay or provider delete.

JSON is decoded from bounded exact bytes with duplicate-key rejection. Nesting
is checked before decoding (12), then node count (10,000), container width (250)
and string length (4,096). Decimal numbers are preserved as Decimal, not float;
the conservative lexer admits at most 18 integer digits and 8 fractional digits,
no exponent/non-finite forms. X-S2 further enforces its own amount precision,
date, field and source bounds. A private 64-digit arithmetic context protects
accepted mapping/normalisation from caller precision and exponent settings.
Unexpected envelopes and unsupported/missing detail reject; no balancing,
rounding repair, zero default or silent unsupported-record drop is performed.

## Trust, mutation and custody limitations

`FixtureBinding` explicitly supplies owner, connection, tenant, auth event,
reference, revision, lifecycle state and expiry independently of provider names.
Exact primitive copies avoid ordinary mutable dependency objects changing the
initial binding silently. Acquisition checks identity, active/unexpired state,
revision and a nondecreasing UTC clock around requests and after mapping, including
finalization. Changing bindings, duplicate/conflicting invoice IDs or any partial
failure return no documents, observations, manifest, tenant or successful grant.
No previous result is cached for a later failed/revoked/disconnected call.

Independent review found the original clock checks reset their baseline after
initial acquisition binding and bypassed that baseline after refresh replacement.
The exact two reproductions failed before correction. Each callback, refresh and
acquisition now creates one operation-scoped clock tracker, beginning before its
initial state/binding check and retained through requests, retrieval evidence and
post-store/finalization checks. Expected refresh revision advancement does not
reset time. Initial expiry cannot be undone by a later clock rollback. The
manifest starts at the operation's first reading. This consistency check does
not authenticate the supplied clock or detect changes between observations.
Post-store refusal does not claim token rollback or erasure when the fixture
already committed; explicit tests retain and inspect those committed tokens.

The state store must be exact OAuthStateStore with TTL no greater than the
documented five-minute code window. The application still owes authenticated
session ownership, registered redirect matching, trustworthy state issuance and
current-event binding. There is no API accepting a raw code or externally created
ValidatedAuthorizationCode as proof. Internal callback composition prevents that
shortcut, but does not authenticate an arbitrary in-process caller or store.

Synthetic custody implements neutral put/replace and fixture-only
basic_authorization/access_authorization/refresh_token accessors. No real secret,
default database, persistence backend or encryption/key custody is selected.
It must report reference/token usability accurately and publish atomic rotation
with a monotonically advancing binding generation. Tests prove the executor's
ordering and whole-token-set handoff against a cooperative atomic fixture, not
actual production transactions, cross-process CAS or provider revocation.
A store that commits then throws yields refusal with potentially indeterminate
storage, not a claim of rollback or deletion. Failed writes are never repaired
by deleting old credentials. Changes-and-reversions between checks, hostile
in-process code and memory erasure are not solved by immutable dataclasses.

Canonical results retain supported private source information for review, not
customer rendering/logging. Outcome repr and diagnostics omit tokens, codes,
Basic/Bearer headers, bodies, tenant/company/owner labels and references. Success
records exact tenant/connection/event, binding revision, per-response digests and
retrieval times plus accepted per-invoice provenance. X-S2/shared canonical
semantics remain untouched: correction NONE means the existing default/no
correction recorded, not verified absence. No FreeAgent UNKNOWN finalization is
transferred here. No cash/accrual, settlement, allowability or tax decision is
manufactured, and opaque references do not authenticate membership.

## Verification and remaining gates

Focused: **113 passed**. Affected: **1,876 passed**, no failures:

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/reserved-venv/bin/python -m pytest \
  tests/test_xero_read_runtime.py tests/test_xero*.py tests/test_accounting*.py \
  tests/test_provider*.py tests/test_oauth_contracts.py tests/test_import_evidence.py \
  tests/test_schema_evidence.py tests/test_freeagent*.py tests/test_quickbooks*.py \
  -o addopts='' -q -p no:cacheprovider
```

Focused used the same options with only the new runtime test. Coverage includes
real exchange/rotation/acquisition, callback replay and provider/state ordering,
wrong/ambiguous selection, failed storage/refresh, lifecycle changes at each
request and normalisation, empty-page termination, bounds, duplicate IDs/keys,
decimal/encoding/header hostility, status failures and no production/default
provider activation. No full canonical or independent acceptance is claimed.
The original 103/1,866 passing candidate was not accepted: the operation-clock
finding required correction. Ten added regressions cover the two reproductions,
callback/post-store boundaries, expired-state non-revival, forward expiry after
replacement and a continuously advancing successful operation. Corrected
independent re-review remains pending.

Real custody, authenticated transport and physical owner/tenant membership,
registered application/session integration, real response/date/envelope/header
compatibility, provider sandbox, general income completeness, customer routes,
privacy/security/target and activation evidence remain open. This advances a
local X-S3 executable component only. X-S3 is incomplete; the denominator stays
2/5 integrated and 0/5 launch-evidence-complete.
