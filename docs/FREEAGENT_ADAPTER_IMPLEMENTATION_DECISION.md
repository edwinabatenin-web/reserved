# FreeAgent adapter implementation decision

**Decision date:** 13 August 2026  
**Decision:** FreeAgent is the best-supported accounting-provider candidate,
but the retained local evidence is insufficient for a correct invoice adapter;
keep it disabled and capture the exact official contracts first

## Why FreeAgent is first

Among the three accounting candidates, the repository retains the most concrete
FreeAgent sandbox information:

- OAuth 2.0 with a dedicated sandbox host, `api.sandbox.freeagent.com`;
- sandbox company setup before API use;
- access and refresh tokens per authorised account;
- a company read is identified as the first binding/probe operation;
- list pagination defaults to 25, supports `page` and `per_page` up to 100,
  exposes `Link` relations and `X-Total-Count`;
- exact official documentation links for OAuth, introduction/pagination,
  quick start, invoices and bank transactions are retained.

That is stronger local evidence than currently retained for Xero or QuickBooks.
It supports a provider decision and pagination-test design, but not a production
or sandbox HTTP implementation yet.

## Minimal proposed sandbox journey

1. Use one temporary, completed-setup FreeAgent sandbox company only.
2. Complete browser authorisation with Reserved's registered sandbox callback,
   provider-bound single-use state and server-side code exchange.
3. Call the documented company/profile read to bind the token reference to the
   correct sandbox company.
4. Retrieve synthetic invoices read-only, first with the default page and then
   with enough records to require multiple pages.
5. Follow `Link` relations; reconcile fetched identities against
   `X-Total-Count`; do not construct a next URL by assumption.
6. Apply a versioned FreeAgent source schema before canonical normalisation;
   quarantine missing/type-changed required fields and retain unknown field
   names for review.
7. Record a payload-free `ImportManifest` and assess it for the bounded purpose
   `synthetic_invoice_matching_input`.
8. Exercise denial, invalid/replayed state, expired access token, refresh-token
   rotation, insufficient user access, 429 and documented provider errors.
9. Remove/revoke sandbox authorisation where the exact official contract
   supports it, then prove reconnect-required behaviour.

This journey remains a design, not an implemented capability.

## Exact evidence missing before code

### OAuth and token lifecycle (historical gap list; partially superseded below)

The local pack records the sandbox host and general code/refresh flow, but an
adapter change must capture and review the current official details for:

- exact sandbox authorization and token URLs;
- authorization parameters, redirect URI matching, state round-trip and denial
  callback fields;
- whether the current FreeAgent implementation requires or recognises scopes,
  and the exact minimum request if so;
- token request content type/authentication and exact response schema;
- authorization-code expiry/single-use behaviour;
- access/refresh expiry and rotation behaviour;
- revocation/disconnection endpoint, method and response, if available;
- documented OAuth errors and safe retry/reauthorisation rules.

These details must be captured from
`https://dev.freeagent.com/docs/oauth`, not reconstructed from remembered OAuth
conventions.

### Company binding

The retained quick-start evidence identifies a sandbox company read, but the
repository does not retain:

- the exact current response schema and stable company identifier;
- whether a separate personal-profile read is required for ownership/audit;
- permission errors and incomplete-company-setup errors;
- which company fields may safely form Reserved's opaque business reference.

The adapter must bind the credential reference and business reference to the
authenticated Reserved user before importing invoices.

### Invoice endpoint and source schema

The repository deliberately does not retain exact invoice resource mappings.
Before implementation, capture:

- exact read-only list URL/method and supported filters;
- exact invoice response envelope and stable invoice identity;
- invoice number/reference, contact identity/name, dated-on/due-on fields;
- currency and amount fields, including whether values are strings/numbers and
  whether totals are gross, net, sales-tax inclusive/exclusive;
- payment/paid amount, paid date and status semantics;
- voided, draft, cancelled, credit-note, foreign-currency and overpayment cases;
- source-created/updated timestamps and incremental-read support;
- null/omitted field semantics;
- endpoint errors, access level required and documented rate-limit headers.

No FreeAgent `SourceSchema` should be committed until those field names and
kinds are copied into a dated review record from the official invoice page.

## Existing canonical-model discrepancy to resolve

During this review, `normalise_invoice()`'s stale docstring said adapters must
provide `customer_name`, `vat_amount` and `outstanding_amount`. The actual
`AccountingInvoice` contract accepts `contact_name`, `tax_amount` and computes
`outstanding_amount` from gross less paid. The docstring has been corrected to
match the code. Neither vocabulary is evidence of FreeAgent's source fields.

Before a FreeAgent mapping is reviewed:

- decide whether computed outstanding amount is adequate for the matching
  purpose when a provider reports adjustments/credits;
- define whether tax amount is required, optional or unsupported for a given
  invoice state;
- do not create provider field aliases by guessing that “VAT” and canonical
  `tax_amount` always have identical meaning.

## Sequenced implementation boundary

1. Capture the exact OAuth, company and invoice contracts listed above with
   observation date and official URL.
2. Approve and implement encrypted token custody with external key management;
   use only opaque `CredentialReference` values outside the adapter.
3. Add an exact FreeAgent sandbox `EndpointPolicy`; production origin remains
   impossible in the sandbox adapter.
4. Implement authorization and callback using `OAuthStateStore`,
   `validate_callback` and `exchange_and_store`; literal tests assert the
   captured official parameters without making network calls.
5. Implement company binding first; reject a credential/business association
   that does not belong to the current Reserved user.
6. Add a literal, versioned invoice `SourceSchema` from official fields and
   separately map it into `AccountingInvoice`.
7. Translate the documented `Link` pagination into `SyncPage`; pass pages to
   `collect_pages`. Do not guess page URLs or silently deduplicate.
8. Use `X-Total-Count` only as documented source-total evidence and produce an
   `ImportManifest`. A mismatch is inadequate; absence is not invented.
9. Add synthetic mapping cases for every supported status/currency/tax/payment
   representation and quarantine unsupported shapes.
10. Add documented error, permission, rate-limit, refresh and reconnect tests.
11. Execute the synthetic sandbox pack and obtain deliberate evidence review.
12. Only then set `implementation_enabled=True` for the FreeAgent provider in
    explicit sandbox configuration.

## Current code decision

No provider-specific code has been added. `FreeAgentProvider` continues to
raise `NotImplementedError`; its provider specification remains
`implementation_enabled=False`. Generic OAuth custody, guarded HTTP,
pagination, schema drift, import evidence and purpose-assessment contracts are
ready to be adopted after the missing official evidence is captured.

## Official pages already retained as references

- [FreeAgent OAuth](https://dev.freeagent.com/docs/oauth)
- [FreeAgent API introduction and pagination](https://dev.freeagent.com/docs/introduction)
- [FreeAgent sandbox quick start](https://dev.freeagent.com/docs/quick_start)
- [FreeAgent invoices](https://dev.freeagent.com/docs/invoices)
- [FreeAgent bank transactions](https://dev.freeagent.com/docs/bank_transactions)

The links identify the authoritative material. Their presence is not a
substitute for retaining and reviewing the exact endpoint/schema facts used by
the adapter.

## OAuth schema-contract reassessment — 13 August 2026

**Historical assessment — superseded by the later official contract capture
below.** It remains here to show why no provider-specific contract was initially
accepted; it is not the current OAuth evidence status.

**Bounded decision:** do not implement a FreeAgent-specific OAuth request or
response schema yet. The provider-neutral callback/state and token-custody
contracts remain usable, but the retained evidence still does not establish an
exact provider contract without inference.

This reassessment considered only the current official FreeAgent OAuth page
linked above and facts already retained from official FreeAgent material. No
credentials, sandbox company, live request, token, customer record or adapter
was used. The official page could be located during this review, but its exact
contract text was not available in a form that could be retained and checked
locally. A link or a general statement that FreeAgent uses OAuth 2.0 is not
sufficient evidence for validation-critical field names or wire encoding.

### Evidence threshold by contract element

| Contract element | Current exact evidence | Decision |
|---|---|---|
| Authorisation request field names and required/optional status | Not retained | Do not encode |
| Sandbox authorisation URL | Sandbox host retained, exact path not retained | Do not encode |
| Callback success and denial fields | Generic OAuth handling exists; FreeAgent-specific callback contract not retained | Keep provider-neutral only |
| Token endpoint URL and method | Not retained exactly | Do not encode |
| Code-exchange body fields and media type | Not retained exactly | Do not encode |
| Client authentication placement | Not retained exactly | Do not encode |
| Token success response fields, types and optionality | Access/refresh-token concepts retained; exact response schema not retained | Do not parse provider payload |
| Token error response fields/statuses | Not retained exactly | Fail closed at generic boundary only |
| Refresh request and rotation semantics | General refresh requirement retained; exact FreeAgent request/response contract not retained | Do not implement provider refresher |
| Scope syntax/defaults | Not retained exactly | Do not request or assume scopes |

### Why no synthetic provider-specific code was added

A network-disabled schema is still executable provider behavior: it fixes
field names, required values, encodings, optionality and accepted response
shapes. Encoding conventional OAuth names from memory would therefore invent a
FreeAgent capability even if the test never made a network call. The existing
`oauth_contracts.py` correctly stops before that boundary: it accepts a typed
token set only after a provider adapter has validated its documented response,
and it does not prescribe endpoints or wire fields.

### Smallest evidence capture that unlocks implementation

Create a dated, reviewer-readable extract from the official FreeAgent OAuth
page containing only:

1. the sandbox authorisation and token URLs;
2. the complete authorisation request parameter table and callback success/
   denial fields;
3. the code-exchange and refresh request examples, including method, media type
   and client authentication placement;
4. success and error response examples plus each field's documented type and
   optionality;
5. any documented expiry, refresh rotation, scope, revocation and retry rules.

Record the official URL, observation date and, if the page exposes one, its
version or last-updated marker. A second person should compare the proposed
literal contract with that extract before code is accepted. At that point the
safe next change is a pure FreeAgent request/response validator with synthetic
literals and no HTTP client; endpoint policy and any sandbox adapter remain
separate later gates.

**Stopping rule applied:** further generic OAuth tests would add theoretical
completeness but would not reduce the material provider-specific uncertainty.
No code or test was changed in this step.

## Official OAuth contract capture and network-inert boundary — 13 August 2026

Current official FreeAgent documentation was available in a reviewer-readable
form in this later bounded review. It now establishes:

- sandbox authorisation endpoint:
  `https://api.sandbox.freeagent.com/v2/approve_app`;
- required authorisation parameters `client_id`, `response_type=code` and
  `redirect_uri`, with optional `state` (Reserved requires state under its
  stronger provider-neutral security contract);
- approved callback fields `code` and, when sent, `state`;
- a 15-minute authorisation-code lifetime;
- sandbox token endpoint:
  `https://api.sandbox.freeagent.com/v2/token_endpoint`;
- HTTP Basic authentication using OAuth identifier/client ID as username and
  OAuth secret as password;
- code-exchange body fields `grant_type=authorization_code`, `code` and
  `redirect_uri` when it was supplied in the authorisation request;
- refresh body fields `grant_type=refresh_token` and `refresh_token`;
- token success fields `access_token`, `token_type` (`bearer`), `expires_in`,
  `refresh_token` and `refresh_token_expires_in`; the documented example uses
  integer expiry values and access-token lifetime 3600 seconds;
- bearer presentation in the `Authorization` header; and
- successful refresh returns both a new access token and refresh token, so the
  complete token set must be rotated atomically.

Sources observed 13 August 2026:

- [FreeAgent OAuth](https://dev.freeagent.com/docs/oauth)
- [FreeAgent sandbox quick start](https://dev.freeagent.com/docs/quick_start)

`reserved/providers/accounting/freeagent_oauth_contract.py` now captures only
this reviewed shape. It is network-inert: pure builders/validators, no HTTP
client, no credential reading, no storage and no adapter enablement. Synthetic
tests require the exact sandbox origin/path, exact request fields, typed token
response and rotated refresh-token preservation.

This does **not** make the FreeAgent adapter ready. The official page does not
document a complete error response schema, denial callback fields, revocation
contract or all token optionality/forward-compatibility rules in the retained
material. Encrypted token custody, owner/company binding, invoice source schema,
pagination/error mapping and sandbox execution remain separate gates.

**Bounded decision:** the OAuth success-path wire schema is now reviewable and
synthetically enforced, while the provider implementation remains disabled.
