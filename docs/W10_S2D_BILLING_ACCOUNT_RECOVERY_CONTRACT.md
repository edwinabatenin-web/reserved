# W10-S2D owner-bound billing-account recovery contract

**Status:** bounded contract candidate for independent review; disabled-first;
provider/runtime neutral; no authentication, persistence, provider session,
entitlement, payment or activation authority.

**Candidate base:** `26944b22dfc4287287827ee7cdabe849e8906531`
(tree `a072db4cfb9d22a32a9b41525098dbd110dcfeca`).

**Contract version:** `reserved-w10-billing-account-recovery-contract/1.0`.

## Outcome and authority boundary

This package implements the ordinary no-transfer engineering baseline classified
by accepted W10-S2C. The sole identity root is the exact, positive `users.id` of
the currently authenticated Reserved owner. Billing email, provider customer
ID, provider subscription ID, browser-selected owner, redirect parameter and
support assertion are never authentication or account-selection authority.

The module evaluates detached facts that a future authenticated adapter and an
atomic durable repository must supply. Producer issuance means only that the
output satisfies this local contract. It does **not** prove that Reserved
authenticated the owner, that a mapping came from a database, that a provider
account exists, or that any runtime may act.

A positive decision authorises only a structural candidate for a future,
short-lived provider-management-session request for the already-bound internal
billing account. It cannot create that session. Every decision fixes these
values to `false`:

- provider-session creation and network authority;
- entitlement mutation and manual entitlement grant;
- charge and refund authority; and
- transfer, merge and delegation authority.

Runtime activation remains `disabled` and separately gated. W10-S2 remains
incomplete because the required specialist evidence has not been accepted.
This package does not complete W10-S3 or start/complete W10-S5.

## Accepted authority and design provenance

| Source | Accepted identity | SHA-256 at this candidate base | Bounded fact consumed |
|---|---|---|---|
| `FOUNDER_DECISIONS.md` | Through `26944b22dfc4287287827ee7cdabe849e8906531` | `03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4` | FD-OA-001 permits bounded engineering; FD-W10-001–003 provide the catalogue/provider/lifecycle boundary but do not settle recovery by provider default. |
| `reserved/billing/provider_lifecycle_authority.py` | W10-S2A `5464bfac7bec6b3456d1895b2355a7e8ce86859b` | `fc21c3a0f9d8d7eeb9a06bcbf5fc4a418568fe06aa5f65f47c325d8ecfde834a` | Customer Portal is provisional and disabled-first; provider observations are not entitlement decisions. |
| `reserved/billing/fail_closed_launch_defaults.py` | W10-S2B `1033c9fbef008dcd33125a0b14e7fb18b8846d19` | `cd72be19d8180a52f2e09fec56cc3219347059b025ceb3f12086d7d8dde40715` | Manual entitlement override remains disabled; recovery was not closed by S2B. |
| `docs/W10_S2C_POLICY_EVIDENCE_DOSSIER.md` | W10-S2C `a07348976321df65bbd95c9170c906bcddd5baa5` | `db31ba2e7c0e51701bc62c6a7b4b489cbde072b5efaf1f09f7c67a5f75fd5dcd` | Current Reserved owner is the sole root; no email/customer-ID authority, lookup-by-email, transfer/merge/delegation/manual grant; ambiguity fails closed; no new Founder question for this baseline. |
| `reserved/billing/entitlement_core.py` | W10-S3A `94bd87f019dc226ec8c73f32515229189500cf06` | `b46b797614b57047e64f6f6597b1c788b9ab15db90653b07add31b4bbb03cb3b` | Entitlement transitions remain separate from management/recovery. |
| `reserved/billing/event_inbox_contract.py` | W10-S3B `5bc29bcb30c95ea7a5a9430104653b366d709eb6` | `4dc0b6bb8b109854531dc1b9d492255e98dca805822cd5e0257f0fdf9b0ca8ed` | Canonical owner is the positive exact `users.id`; billing account IDs are internal structural identifiers, not provider authority; no durable repository exists yet. |
| `reserved/billing/stripe_disabled_first_contract.py` | W10-S4A `2ad4a63dd1f10ba38859050b47245c28390667d8` | `87a84c5ec77f25e12667b5466052b4a84ee6e01a6b075df643202d95aec98638` | Provider edge remains disabled, network-inert and unable to create sessions or entitlement. |

The contract does not import or derive runtime authority from these mutable
modules. The identities above are design provenance for independent review.

## Exact detached inputs

Authentication, initiation and replay structures, and a mapping when present,
must be exact built-in `dict` values with only the listed keys. A missing
mapping is represented only by `None` and yields a denial. Keys and strings must
be exact built-ins; owner/version integers must be exact positive integers;
times must be exact `datetime` values using the built-in `timezone.utc`
singleton. Subclasses, stateful timezone objects, additional browser/provider
fields and credential-shaped retained values fail before a decision is issued.

### Authentication context

| Field | Rule |
|---|---|
| `schema_version` | Exact `reserved-authenticated-owner-context/1.0`. |
| `owner_user_id` | Exact positive Reserved `users.id`; must equal the function's authenticated owner argument. |
| `authentication_reference` | Redacted `evidence:...` reference only. |
| `authenticated_at` | Exact UTC authentication instant; cannot follow the initiation. |
| `authentication_valid_until` | Exact UTC boundary strictly after authentication and evaluation. |
| `trust_status` | Exact future-adapter marker; structural input, not authentication proof. |

Loss of the Reserved login is outside this contract and must use the separately
assured identity-recovery/support path. Billing recovery cannot bypass login.

### Owner-to-billing-account mapping snapshot

| Field group | Rule |
|---|---|
| Schema/owner | Exact schema, same `owner_user_id`, and canonical base-10 owner string. |
| Account | Sanitised internal `billing_account_id`; provider-like `cus_`, `sub_` and account identifiers are rejected. |
| Version/snapshot | Positive mapping version and opaque sanitised snapshot ID. |
| Evidence | Redacted `evidence:...` reference only. |
| Time | Exact UTC `observed_at` and strictly later `fresh_until`; observation cannot be in the future and freshness must extend beyond evaluation. |
| Cardinality/state | Exactly one active mapping is the only positive state. None, multiple, conflicting, stale or deleted states deny. |
| Trust marker | Explicitly identifies the future authenticated durable repository; it is not proof that one exists. |

The future repository must supply this mapping after owner authentication. The
browser, provider email, provider customer/subscription ID and redirect/return
parameters are absent from the accepted shape, so they cannot select another
account. A denied decision deliberately omits billing-account, mapping-snapshot
and mapping-version fields; it cannot echo a cross-owner or ambiguous selection.

### Initiation and replay snapshots

The initiation carries only exact schema, opaque request ID, opaque idempotency
key, exact UTC request time and the fixed purpose
`manage_existing_owner_bound_subscription_billing`. There is no owner, email,
customer, subscription, redirect or return-target field.

The replay snapshot binds the exact mapping snapshot, request ID and idempotency
key to a check performed at the exact evaluation instant. The only authorising
state is `unused_for_request` with no existing decision reference. An exact
request replay returns a fail-closed `return_existing_decision_reference_only`
disposition; it cannot create another request. Mapping reuse for a different
request and idempotency conflicts deny.

The contract itself retains no replay ledger. The future repository must
atomically compare-and-set the mapping/request/idempotency tuple and store the
deterministic decision identity before any adapter creates a provider session.
Repeated pure evaluation of identical unused facts returns the same decision
identity, not evidence that the compare-and-set happened.

## Decision semantics

`decide_billing_account_recovery` validates the owner, authentication interval,
unique active mapping, mapping freshness, request time and replay snapshot at one
exact UTC evaluation instant. Only when every predicate holds does it return
`future_provider_management_session_request_candidate_only`. Its
`decision_not_after` is the earlier of authentication expiry and mapping
freshness expiry, and it can never exceed five minutes after evaluation. This is
the local request-candidate lifetime, not a claim about a provider portal
session's duration. A future adapter must additionally impose its accepted
provider-session TTL and fixed allowlisted return target; it may narrow but
never extend the candidate bound.

Every other semantic outcome returns
`fail_closed_no_management_session_request`. Invalid structure or unsafe
retained input raises `TypeError`/`ValueError`. These are local contract results,
not customer copy or provider errors.

The public decision boundary accepts exactly the six required named inputs.
Mutable callable default metadata cannot supply or replace any of those facts.
When the supplied authentication context names a different owner, the denial
also suppresses that context's evidence reference (and any mapping reference),
so cross-owner evidence cannot be projected through a failed binding.

Decision handles are producer-issued, identity-registered and immutable by
construction. Exact-type and live-object checks reject `object.__new__`,
subclasses, equality/hash aliasing and stale identities. Generation-safe weakref
callbacks erase registry state after collection. Authoritative copy operations
revalidate and issue a fresh handle; pickle is prohibited. Projected state uses
only exact immutable built-in tuples/primitives and exact UTC datetimes.

## Threat/control matrix

| Threat | Contract treatment | Remaining evidence |
|---|---|---|
| Cross-owner substitution | Authenticated argument, auth context and unique mapping owner must agree exactly; denial exposes no account selection or conflicting-owner evidence reference. | Integrated negative tests against the real authentication and repository adapters. |
| Email/customer/subscription lookup | No accepted field or API argument; provider-shaped IDs rejected as internal accounts. | Route/request-schema and provider-adapter review. |
| Redirect/session swap | Redirect and return targets are absent; additional fields fail. | Fixed allowlist, CSRF/session integrity and target browser tests. |
| Missing/duplicate/conflicting/stale mapping | Fail-closed outcome. | Durable uniqueness constraints, migration and reconciliation procedure. |
| Replay/idempotency conflict | Exact atomic snapshot binding; replay creates no new candidate; deterministic identity. | Durable compare-and-set, concurrency and crash-recovery tests. |
| Time-of-check race | Replay `checked_at` must equal evaluation; owner and mapping validity must extend beyond evaluation. | One repository transaction and short provider-session TTL enforcement. |
| Secret or personal-data retention | Conservative identifier screening and redacted evidence references; no email/provider payload/credential fields. | Approved minimisation allowlist, log review, retention/erasure and backup treatment. |
| Mutable/subclass/stateful object attack | Exact built-in containers, field names, strings, integers, UTC datetimes and producer identities; exact call shape prevents mutable callable defaults supplying authority facts. | Independent hostile-runtime review. |
| Manual grant/transfer/merge/delegation | No API or output authority; all relevant flags permanently false. | Any future capability is new consequential scope and Founder authority. |
| Provider/session/network action | Permanently false runtime/provider/network flags and disabled activation. | Separate S4 adapter, sandbox, credentials, target and activation evidence. |

## Explicit unresolved launch gates

This candidate supplies none of the following:

1. an authenticated Reserved-owner adapter or identity-recovery assurance;
2. a durable, unique owner-to-billing-account repository, schema or migration;
3. atomic freshness/replay/idempotency compare-and-set and crash recovery;
4. target session, CSRF, return-target and browser assurance;
5. support least privilege, security/privacy review and misuse controls;
6. redacted audit, monitoring, incident and provider-outage runbooks;
7. account email-change/collision/deletion, erasure and retention behavior;
8. provider SDK, sandbox or target negative evidence;
9. independent integrated review and residual-risk acceptance; or
10. provider, production, release or Founder activation authority.

Until those applicable gates are accepted, management/recovery operations stay
disabled. No additional Founder question is needed for the bounded no-transfer
baseline. Transfer/merge, delegated/household/team billing, identity merger or a
manual entitlement grant would be new consequential scope and must not be
inferred from this contract.

## Verification scope

`tests/test_w10_billing_account_recovery_contract.py` uses synthetic, in-memory
facts only. It covers cross-owner substitution; forbidden email/customer/
subscription/redirect inputs; provider-shaped and credential-shaped IDs;
missing, ambiguous, conflicting, inactive and stale mappings; exact replay and
idempotency conflict; future/stale/non-atomic time cases; deterministic identity;
zero excess authority; post-evaluation input mutation; direct construction,
subclass, `object.__new__`, copy/pickle, public-global/class-metadata and
mutable-callable-default attacks; conflicting-owner evidence suppression;
stateful-timezone attacks; generation-safe registry cleanup; exact API exports;
standard-library-only implementation; and accepted-source hashes.

The tests perform no database, file persistence, migration, network, SDK,
credential, customer-data, route, entitlement or provider operation.
