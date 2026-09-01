# Yapily Y1 provisional AIS Hosted Consent evidence

Observation date: 2026-09-01. Status: independently reviewed provisional
engineering; not independently assured or production-ready.

## Authority and product boundary

The commercial evidence is an independently reviewed, populated but unsigned
draft order form. It identifies Whip Smart Technologies Ltd, UK territory, no
Sub-Clients, Yapily API and Yapily Data (including Get Accounts and Get
Transactions), a UK Yapily Connect licence, Implementation Services, Hosted
Pages and Standard support. It is not an executed entitlement or legal or
production approval.

Yapily Payments, PIS and VRP are not selected. Cristian Gheorghita's separate
email about Payments and a possible sweeping-VRP fit is not incorporated into
the draft order form and supplies no entitlement. No payment or money-movement
contract is implemented or implied here.

Official public sources supplied for this package and observed without network
access on 2026-09-01:

- <https://docs.yapily.com/api-reference/hosted-consent-pages/create-hosted-consent-request>
- <https://docs.yapily.com/api-reference/hosted-consent-pages/get-hosted-consent-request>
- <https://docs.yapily.com/tools-and-services/hosted-pages/payment-tutorial-hosted-data>
- <https://docs.yapily.com/resources/sandbox/test-cases>

Public examples are treated as examples, not exhaustive production schemas.

## Token-safe implemented boundary

`reserved/providers/banking/yapily_hosted_consent_contract.py` is a pure,
disabled-by-absence request-contract module aligned to the reviewed official
wire shape. It:

- constructs and strictly parses the deterministic Hosted Consent request with
  stable Reserved `applicationUserId`; an `institutionIdentifiers` object
  requiring `institutionCountryCode: "GB"` and permitting one optional
  `institutionId`; exact `userSettings` of `{"language":"en","location":"GB"}`;
  HTTPS `redirectUrl`; and exact `ACCOUNTS` plus `ACCOUNT_TRANSACTIONS` nested
  under `accountRequest.featureScope`; and
- constructs only `/hosted/consent-requests/{consentRequestId}` as a relative
  GET path, without retrieving or parsing the response.

The deterministic request includes documented `userSettings` rather than
omitting it. `applicationUserId` is Reserved's stable application-user identity;
the module does not model provider user, application, consent or request
response identifiers. The GET path parameter retains the documented
`consentRequestId` meaning.

The supplied current official sources conflict in a security-material way: at
least one Hosted Pages data tutorial shows a returned `hostedUrl` whose fragment
contains `#authToken=...`, while other create-response examples do not show that
secret-bearing URL shape. Weakening URL validation or accepting that value in
Y1 would cross an unreviewed custody boundary.

Y1 therefore accepts no provider response payload at all. It has no create or
status response parser, hosted-URL type, browser handoff, redacted credential
wrapper or token model. All provider response handling, browser handoff and
redirect, hosted URL/token custody, and GET status parsing are deferred together
to Y2. This is a deliberate fail-closed reduction, not an implementation failure.
Reserved's request `redirectUrl` remains strict HTTPS and rejects fragments.

The module has no transport, endpoint origin, environment access, credentials,
token custody, persistence, route activation, callback processing or webhook model.
A browser redirect remains a redirect, not a webhook. The module contains no
identity, balances, PIS, bulk-payment, VRP, sweeping, same-owner transfer or
other money-movement feature.

## Verification record

Commands used `PYTHONDONTWRITEBYTECODE=1` and pytest's `-p no:cacheprovider`.
No cache was deleted.

- Focused: `tests/test_yapily_hosted_consent_contract.py` — 49 passed in 0.30s.
- Directly related: the focused file plus `test_auth.py`, `test_matching.py`,
  `test_persistence.py`, `test_provider_http_boundary.py`, `test_release_gate.py`
  and `test_transaction_classification.py` — 391 passed in 5.02s.
- Full repository suite — 1,970 passed and 7 subtests passed in 18.78s.

The shell had no `pytest` command and system Python had no pytest module. Tests
used the pre-existing interpreter at
`/Users/edwinabatenin/Documents/Codex/2026-08-11/reserved-w1-bpa/.venv/bin/pytest`;
there was no install, download, network access or approval prompt.

SHA-256 at verification:

- contract module: `e6e1b87c8809988d4aa6ecd867c407bd481af83f1418c2c86a5faf0c4e271333`
- focused tests: `25b6a63ff4959f1998697b75b98b0960c540a75e15e7a8df6ebd3cc982efc491`

Documentation hashes are reported externally after final content is fixed, to
avoid a self-referential hash inside this evidence file.

## Assumptions, unresolved gaps and gates

This provisional contract assumes the supplied reviewed request shape remains
applicable to the contracted Hosted Pages/Data product. It assumes no
institution coverage from an optional restriction. Before any response is
handled, Y2 must establish a reviewed secret-bearing URL, custody, redaction and
logging boundary and confirm the exact response schema through approved sandbox
evidence.

Unresolved items include contract execution and legal review, provider product
confirmation, approved sandbox access, credential custody, redirect/state
binding, consent/token custody and deletion, institution-specific coverage,
real pagination/error/expiry behaviour, data retention and regulatory review.

Production and credentials remain explicitly gated: no credential may be put
through this module and no network or production activation is authorized.
Sandbox execution is gated on approved access and credential custody. PIS and
sweeping VRP each require later explicit contractual selection plus separate
legal, regulatory, security, custody, implementation and assurance gates.

## Rollback

Because Y1 adds only four isolated files and changes no routes or clients,
rollback is to remove those four Y1 files through an approved, recoverable
change. Do not alter the existing Yapily client or use reset/checkout to discard
unrelated work. Confirm the removal with `git status` and rerun the directly
related and full suites. No external state, credentials or provider resources
exist to unwind.

This candidate passed independent Codex review of the provisional evidence and
implementation after a final fail-closed correction for whitespace and path
segment confusion. That statement does not claim independent assurance,
executed entitlement or production readiness.
