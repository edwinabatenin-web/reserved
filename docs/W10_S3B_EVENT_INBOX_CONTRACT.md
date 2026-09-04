# W10-S3B event-inbox contract candidate

## Status and exact scope

This candidate is based on clean integration commit
`3079553c3b4d7f69eede6887a5b199b8cb80caac`. It is a pure, immutable contract
for the shape and fail-closed invariants of a future owner-bound billing account,
subscription, event inbox, receipt and append-only disposition boundary.

It is **not** a database schema, migration, repository, webhook, verified event
source, provider adapter, entitlement store or implemented event inbox. It does
not complete W10-S3 or authorise provider/runtime activation.

The package is confined to:

- `reserved/billing/event_inbox_contract.py`;
- `tests/test_w10_event_inbox_contract.py`; and
- this evidence document.

## Authority and provenance

The contract records exact local provenance rather than copying mutable module
metadata:

- `FD-W9-001`, with datastore, retention, erasure and custody still gated;
- W9 contract integration `c489c25bab669c64e1c11d28caf29fcde9678fdd`;
- W10-S1 integration `9e8f94a9906f0c9d5c85b47223d20c34be499e1c`;
- W10-S2A integration `5464bfac7bec6b3456d1895b2355a7e8ce86859b`;
- W10-S3A integration `94bd87f019dc226ec8c73f32515229189500cf06`;
- W10-S4A integration `2ad4a63dd1f10ba38859050b47245c28390667d8`;
- Founder Decisions `FD-W10-001`, `FD-W10-002` and `FD-W10-003`.

S1 supplies the catalogue authority and three initial plan keys. S2A supplies
only the provisional disabled-first provider boundary and five settled lifecycle
policies plus no-trial/free-access. S3A supplies the four provider-neutral
canonical observation kinds and their fail-closed order/idempotency semantics.
S4A supplies the future edge requirements: raw-body signature verification,
duplicate and unordered delivery handling, API-version and owner binding, an
atomic inbox and replay-safe reconciliation. This contract implements none of
those external or durable capabilities.

## Producer-issued structural records

All handles are opaque and producer-issued. Public construction and forged
`object.__new__` values fail validation. Copy/deepcopy revalidate and issue a new
immutable alias; pickle is rejected. Issuance proves only exact structural
construction by this module. Every event retains
`producer_issued_structure_not_provider_verified`; no factory can mint provider
authenticity.

The pure record projections are:

1. `BillingAccountRecord`: exact positive internal `users.id`, its canonical
   base-10 string, an internal billing-account ID, the S1 catalogue authority,
   purpose and structural trust status.
2. `BillingSubscriptionRecord`: the same owner/account boundary, internal
   subscription ID, exact catalogue version and one settled initial plan key.
3. `BillingEventRecord`: owner/account/subscription boundary, immutable source
   namespace/event identity, API version, provider object/type observation,
   effective/paid-through dates, bounded evidence reference, exact source-byte
   SHA-256 digest, canonical observation kind, trust/entitlement semantics and a
   deterministic unkeyed content fingerprint.
4. `BillingEventReceiptRecord`: receipt identity/time, candidate identity and
   fingerprint, pure admission classification and an invariant
   `entitlement_mutation_allowed == False`.
5. `BillingEventDispositionRecord`: one append-only event chain with sequence,
   predecessor identity, kind, evidence, time, optional correction target and
   `entitlement_mutation_allowed == False`.

Receipt and disposition times accept only an exact built-in `datetime` whose
`tzinfo` is the captured `datetime.timezone.utc` singleton. Caller-owned or
custom timezone implementations are executable mutable objects and are rejected
without calling `utcoffset()`. Projected times therefore remain exact immutable
built-in UTC datetimes rather than retaining a stateful timezone collaborator.

The content fingerprints are unkeyed deterministic identities, not MACs,
signatures, provider evidence or authenticated storage integrity.

## Owner adaptation

The future database boundary must use the authoritative positive exact integer
`users.id`. `canonical_owner_id_from_users_id` converts that value to its
base-10 string for compatibility with S3A's provider-neutral string owner field.
It rejects booleans, strings, zero, negative values and values beyond signed
64-bit range. A Clerk subject, provider customer ID, session key or other
external identifier must never be substituted for this explicit adapter.

## Admission and reconciliation invariants

`classify_event_admission` is a pure classification over producer-issued
structural events. It neither inserts nor processes anything. Its precedence is:

1. the same `(source_namespace, source_event_id)` and same fingerprint is an
   exact replay;
2. the same immutable identity with different content is an identity conflict;
3. another event ID with the same namespace/provider-object/event-type is a
   secondary duplicate requiring reconciliation, not a hard duplicate identity;
4. a distinct event whose effective date is older than or equal to an existing
   event for the same owner/account/subscription requires reconciliation;
5. unknown/refund/dispute/chargeback/reversal observations are retained only as
   unresolved-policy observations with zero entitlement effect; and
6. otherwise the value remains a structural candidate pending future verified
   admission.

The existing-event input itself must contain unique immutable identities. A
corrupt duplicate set fails closed.

`append_event_disposition` validates the complete supplied chain on every append.
Sequence and predecessor links must be contiguous and event-bound. Disposition
IDs must be unique within the chain and exact UTC `recorded_at` values must
strictly increase; a duplicate ID, backdated/equal new entry, or copied/corrupt
existing chain fails closed. Corrections append a new disposition referencing an
existing disposition identity; they do not mutate or replace the prior event or
disposition. Manual override authority is not created.

The four S3A observation kinds are only canonical candidates. Even they cannot
directly mutate entitlement. Unknown, refund, dispute, chargeback and reversal
observations are always marked `reconciliation_only_zero_entitlement_effect`.

## Minimisation and excluded behavior

The event factory deliberately has no parameter for a raw payload/request body,
signature header, endpoint secret, credential, API key or complete provider
object. Only a `sha256:<64 lowercase hex>` source-byte digest and bounded
sanitised structural facts can appear. A digest is not proof of provider origin.

Every caller-supplied retained identifier/reference is checked by a
closure-captured lexical guard. Values must be 1–160 ASCII characters, start
alphanumerically and thereafter contain only alphanumerics plus `.`, `_`, `:`,
`/` or `-`. Field-aware validators apply this grammar to internal account,
subscription, receipt and disposition IDs; source namespace/event/object IDs;
API version and event type metadata; and event/disposition evidence references.
They additionally reject separated credential-shaped terms and well-known
secret prefixes, including `sk_live`, `rk_live`, `whsec`, `secret`,
`credential`, password/bearer/authorization terms, API keys, access/refresh
tokens, private/secret keys and client/webhook/endpoint secrets. Thus ordinary
identifiers containing innocuous substrings such as `secretary-record`,
`tokenization-event` or `monkey-account` remain representable.

Before marker matching, every permitted separator (`.`, `_`, `:`, `/` and `-`)
is collapsed to the same private screening separator. Consequently `api.key`,
`api/key`, `api:key`, `api_key` and `api-key` cannot receive different safety
outcomes, and compound forms such as `sk.live` or `refresh:token` cannot bypass
the lexical guard.

This bounded denylist is defence in depth, not an entropy detector, DLP system
or proof that an opaque provider identifier contains no sensitive material. The
future approved field allowlist, producer-side redaction and independent privacy
review remain explicit gates. A value that merely passes the lexical guard has
no provider authenticity or retention authority.

The module imports no database, provider SDK, networking, filesystem,
configuration or credential facility. It performs no I/O, environment access,
webhook parsing/signature verification, persistence, migration, entitlement
mutation, route enforcement, checkout/portal operation, charge, erasure,
retention execution or activation.

## Explicit unresolved gates

Durable S3B remains blocked until accepted evidence settles:

- datastore and migration rules, with exclusive ownership of shared migrations;
- encryption at rest, authenticated integrity and key custody;
- field-level purpose/minimisation and the sanitised evidence allowlist;
- retention, account erasure, legal hold and backup expiry;
- provider source-binding and immutable event-namespace identity;
- authenticated raw-body signature verification and provider-to-owner
  reconciliation;
- refund/dispute/chargeback/reversal translation and consequences;
- manual correction/override authority; and
- independent schema, security, privacy and integrated review.

No unresolved gate is encoded as a default. The contract projection exposes all
of them as machine-readable constraints.

## Focused verification

The focused suite covers exact owner adaptation and binding; exact replay versus
identity conflict; secondary object/type duplicate detection; older and same-day
reconciliation; zero entitlement effect for unresolved observations; append-only
correction; corrupt-chain rejection; public construction and `object.__new__`
forgery; copy/deepcopy/pickle; module-global, exported-class and public-function
rebinding; mutable-global bytecode resolution; absence of raw/secret parameters;
hostile credential-shaped values across every retained field; avoidance of
mechanical substring blocking; duplicate/backdated/non-increasing disposition
entries and copied-chain corruption; separator-equivalent secret forms; rejection
of mutable custom timezone objects without executing them; exact immutable
built-in UTC projections; and operation with file I/O disabled.

Run:

```bash
python3 -m pytest -p no:cacheprovider tests/test_w10_event_inbox_contract.py -q
python3 -m pytest -p no:cacheprovider \
  tests/test_billing_contracts.py \
  tests/test_w10_provider_lifecycle_authority.py \
  tests/test_w10_entitlement_core.py \
  tests/test_w10_stripe_disabled_first_contract.py -q
python3 -m py_compile reserved/billing/event_inbox_contract.py
git diff --check
```
