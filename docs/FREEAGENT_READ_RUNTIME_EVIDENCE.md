# FreeAgent injected acquisition executor — candidate 1.0

Pending different independent review; uncommitted on immutable base
`bd68ab48e4394b06470c20c6035384b6f78cd1a4`, tree
`2a8f3b6d0078c92f807fef8360440497a65cf146`. Authority:
`work/freeagent-read-runtime-authority.md`. Founder SHA-256 remains
`78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`.
Runtime version: `freeagent-injected-read/1.0`.

## Implemented endpoint and reused evidence

`acquire_invoices` actually resolves the supplied opaque credential reference
against an injected binding source, requests company data, validates exact typed
company identity, requests invoice pages, validates pagination, maps every
supported invoice with the accepted 1.1 mapper and returns canonical documents
plus source observations and import evidence. It is not a precomputed successful
fixture or a detached decision contract. Tests record each real request object.

Existing FA-S1 source validation, FA-S4 pagination decisions, neutral guarded
transport/request/response and import manifest are reused unchanged. The mapper
still calls shared normalisation and finalizes only correction lifecycle to
UNKNOWN. Its evidence-limited item URI support, ordinary non-sales-tax GBP
subset, unknown tax/value semantics and no cash/accrual/settlement authority
remain unchanged. Source facts are those in the accepted FreeAgent invoice,
resilience and adapter evidence documents, principally
[official invoices](https://dev.freeagent.com/docs/invoices); this package made
no additional network request or provider observation.

## Fixture binding, not authentication or custody

`FixtureBinding` contains independently supplied owner, connection, business,
typed company ID, exact FreeAgent `CredentialReference`, revision, state and
expiry. `binding_source.resolve(reference)` is the explicit reference boundary.
The executor does not populate that source from matching display names, a company
URL or caller claims. Owner/connection/reference must match the request; company
ID must match the separately retrieved company with its exact integer/string
type. Exact primitive snapshots prevent ordinary subsequent mutation of the
dependency's binding object from silently changing the admitted initial binding.

The supplied binding source and transport are **test dependencies**, not newly
authenticated services. The transport implements the existing `send(request)`
interface; it is not associated with a real credential or identity by this code.
No token is resolved, generated, stored, attached to a header, exchanged or
refreshed. Real credential-to-transport authentication remains missing, not
implicitly supplied by an opaque reference. No physical membership repository,
custody mechanism or authenticated company selection is created.

Binding state/revision/identity and an exact monotonic UTC clock are checked
before and after every request, after each mapped page and at finalization.
Only `active`, unexpired bindings can proceed. Disconnect, revocation,
refresh-required/failure, expiry or changed revision/identity refuse. This
neither performs refresh nor revokes the provider. The fixture source must
report lifecycle changes coherently; an undetectable change-and-reversion
between checks is not solved by equality. Results are call-time evidence, not
live/revocable access capabilities. Arbitrary in-process hostile code, malicious
transport execution and memory erasure are outside the claimed boundary.

## Environment and bounded request execution

Only explicit `injected_test` is accepted. Documented `api.freeagent.com` URLs
are request data sent to the caller's injected transport; there is no default
transport, HTTP client, socket, route, provider registration or activation.
The neutral endpoint policy uses its literal `test` environment, never sandbox.
The different OAuth sandbox origin is not substituted and response identities
are not rewritten. Live sandbox identity/response compatibility remains an
explicit later evidence and implementation prerequisite.

Every destination is checked before delegation: exact HTTPS API origin,
company singleton or invoice collection; invoice queries are restricted to
singular positive `page` and `per_page` parameters within the finite limits.
Next links must supply an explicit page number agreeing with sequential progress;
no later page identity is defaulted from the loop counter. Every requested invoice
destination, including the initial collection URL, is tracked and repeats are
rejected before delegation. All pagination
relation URLs are checked, not only `next`. Extra filters, encoded components,
ports, fragments, unexpected paths or query keys refuse. These are conservative
support restrictions, not universal provider URI grammar. Requests are GET
with only `Accept: application/json`; there is no redirect following or retry.

The requested page size is enforced against returned record count: default 25
from the accepted API introduction evidence, or the explicit `per_page` value.
An oversized page refuses without truncation or partial output. Supplied first,
previous and last relation page identities must be coherent with the current
and next page; absent optional relations are not invented. Page-size changes
alone are not rejected as an undocumented provider violation. These checks do
not establish stable ordering, an atomic snapshot or annual-income completeness.
Terminal success additionally requires a supplied last-page identity to equal
the current page; absence of next does not override contradictory last evidence.

Responses require exact neutral response objects, integer status 200, bounded
unique case-insensitive headers and an explicit supported JSON content type.
Only Content-Type, Link and X-Total-Count are supported; real-server additional
headers are not presumed compatible. Company responses cannot carry pagination
headers. Bodies are exact bytes, at most 64 KiB; aggregate bodies at most 1 MiB;
at most 20 invoice pages and 500 records. JSON depth is bounded before decoding,
then graph nodes (5,000), container entries (100), strings (2,048), integer digits
and duplicate keys are checked. Floating JSON numbers/constants are unsupported;
provider decimal strings remain the accepted mapper's bounded responsibility.
Existing per-document mapper bounds still apply independently.

## Import disposition and privacy

Across-page duplicate/conflicting document IDs, contradictory/changing counts,
absent count after an earlier count, cycles, unsupported records and any failed
dependency discard the entire candidate. There is no silent deduplication or
unsupported-record dropping. Refusals have no documents, manifest or source
digests; a prior successful call is never cached or returned after a later
failure. Fixed allowlisted reasons can identify unsupported invoices or binding
failures; other exceptions yield a generic refusal, never their text.

Successful results preserve per-document observations/provenance, exact company
and page byte digests, company/page retrieval times, binding revision and exact
page/fetched/unique counts. `ImportManifest.status=complete` means **pagination
count consistency only**. Absent source total is `unverified`; no source
watermark or stable provider snapshot is invented. Concurrent provider changes,
omissions, annual-income inventory and purpose fitness remain unverified.
`annual_income_complete` and `authenticated_membership` remain false.

The canonical result deliberately contains supported source data for subsequent
review, not a customer-safe presentation. It is not logged. Diagnostic summaries
contain fixed status/reason, counts and non-authority flags only; they do not use
the broader manifest summary, raw URLs/bodies/headers, private labels, owner/
business/company references, credential-like values or dependency exceptions.

## Synthetic verification and remaining gates

**126 focused passed; 1,889 affected passed**, zero failures after the final
terminal-relation correction. Prior freezes passed 1,870 and 1,881 affected.

```sh
PYTHONDONTWRITEBYTECODE=1 /private/tmp/reserved-venv/bin/python -m pytest \
  tests/test_freeagent_read_runtime.py tests/test_freeagent_invoice_adapter.py \
  tests/test_freeagent_invoice_contract.py tests/test_freeagent_resilience.py \
  tests/test_freeagent_oauth_contract.py tests/test_accounting*.py \
  tests/test_provider*.py tests/test_xero*.py tests/test_quickbooks*.py \
  tests/test_oauth_contracts.py tests/test_import_evidence.py tests/test_schema_evidence.py \
  -o addopts='' -q -p no:cacheprovider
```

The focused run used only the new test file with identical interpreter/options.
Independent review of the original 105/1,868 passing candidate found that an
initial-URL next link or a per_page-only next link could be fetched and counted
as a later page. Both exact regressions failed before this correction. They now
assert refusal with no partial result and no invalid second invoice request.
The original passing counts were not acceptance; this corrected candidate still
requires different independent re-review.
That re-review confirmed the first correction but reproduced oversized default/
explicit pages and contradictory supplied first/previous/last relations. The
owning Codex made this second bounded correction; the independent reviewer
remains separate. Eleven new boundary tests cover those cases and valid limits.
Neither the earlier passing tests nor this correction is independent acceptance.
The subsequent independent re-review found one remaining terminal/last relation
edge; root corrected it and added eight initial/later-page boundary cases. This
exact final candidate still requires independent re-review before acceptance.
Tests execute company plus multiple pages/documents, exact multiline amounts,
the 20-page terminal boundary, budget refusals, binding mutation/finalization,
same-label/wrong-ID and typed-ID rejection, duplicate/conflicting records,
unsupported mixed items, JSON/header/origin/query hostility, failed final pages,
clock/expiry, disconnect and redacted diagnostics. Aggregate budget tests also
lower ceilings to prove the boundary without creating large data fixtures.
One initial test used the wrong registry container access; it was corrected
to the existing tuple lookup without changing registry or product behavior.

No full canonical, independent acceptance, provider sandbox, customer/browser,
production or target evidence is claimed for this candidate. FA-S2 custody and
authenticated membership/transport, OAuth lifecycle, live environment schemas,
broader ingestion and completeness, privacy/security, target evidence and
activation remain open. This advances FA-S3 executable local orchestration,
not a complete provider or launch slice; denominators remain 1/6 and 2/8.
