# QuickBooks Q-S4 observation-contract evidence

Status: uncommitted candidate for independent review. QuickBooks remains
disabled. Observation is not transport, authentication integration, canonical
normalisation, sandbox evidence, activation, or a launch decision.

## Scope and authority

The owning reviewer supplied observations from the rendered official Intuit
Developer `Invoice` and `CompanyInfo` reference pages on 1 September 2026 and
the separately retained pre-Q-S5 `Payment` facts. This
candidate did not browse those pages or add provider semantics beyond the
reviewer-supplied facts. The implementation is confined to
`reserved/providers/accounting/quickbooks_observation_contract.py`; its focused
tests are in `tests/test_quickbooks_observation_contract.py`.

The implementation accepts already-retrieved source values only. It imports
Q-S1's immutable `RealmBinding` and requires exact user, realm, and opaque
credential-reference agreement. `CompanyInfo` is therefore evidence about the
bound realm, never independent proof of Reserved user ownership.

## Encoded provider observations

`CompanyInfo` requires exact non-blank `Id`, `SyncToken`, and `CompanyName`
(bounded to the documented 1024 characters). It preserves `LegalName`,
`Country`, `FiscalYearStartMonth`, `CompanyStartDate`, `MetaData`, additive
`NameValue` pairs, and any other bounded source evidence without assigning new
meaning. A supplied `CompanyInfo.Country` is retained only as a bounded
non-blank country-name string used by the provider for financial calculations;
it is not interpreted as the ISO three-letter rule documented for address
country fields.

`Invoice` requires exact non-blank `Id`, `SyncToken`, `CustomerRef.value`, and
one to 750 `Line` objects. This bounded slice accepts exactly the three
discriminator/member pairs directly verified in rendered official JSON:
`SalesItemLineDetail`, `DiscountLineDetail`, and `SubTotalLineDetail`. Each line
must contain exactly its matching non-null plain-object member and no other key
ending in `LineDetail`. Provider prose describes group and description
categories, but their exact JSON discriminator/member spellings have not been
retained as evidence; they therefore fail closed pending that evidence rather
than being treated as nonexistent provider categories. A supplied line `Amount`
is retained as an exact bounded decimal. `TxnDate`, `DueDate`, `TotalAmt`, `Balance`, currency and transaction
tax presence, `GlobalTaxCalculation`, and complete bounded source evidence are
recorded. `GlobalTaxCalculation` is closed to `TaxExcluded`, `TaxInclusive`,
and `NotApplicable`.

`Payment` requires exact non-blank `Id`, `SyncToken`, and
`CustomerRef.value`. It retains optional `TxnDate`, exact nonnegative bounded
`TotalAmt` and `UnappliedAmt`, explicit `CurrencyRef` presence/null state, and
the complete bounded raw graph. A supplied `Line` must be an ordered built-in
list of zero to 750 plain objects; absence is also retained. Each optional line
`Amount` is an exact nonnegative bounded decimal. A supplied `LinkedTxn` must
be an ordered built-in list of zero to 750 plain objects. Present `TxnId` and
`TxnType` members must be bounded non-blank strings, while absent members and
all additive link/line evidence remain intact. No link type is classified as
supported or unsupported at this boundary.

The values do not derive invoice status, paid status, payment matching,
allocation, settlement,
liability, tax treatment, ownership, accounting recognition, canonical
documents, launch readiness, or activation. In particular, observed `Balance`
and `TotalAmt` remain provider fields, and absent `TxnDate` is not replaced with
a local or server date.

## Integrity and resource controls

Every observation binds the Q-S1 identity, exact provider entity ID and
`SyncToken`, an aware retrieval timestamp supplied by the caller, and a SHA-256
digest of the accepted source graph. The digest encoding distinguishes null,
boolean, integer, `Decimal` (including scale), string, array, and object types;
object ordering does not affect identity.

`source_digest` remains solely the raw-source digest. A separate deterministic
`observation_attestation` binds the observation kind and schema, raw-source
digest, exact user, realm, opaque credential reference, and retrieval timestamp
normalized to UTC. The exact observer computes and immutably carries it for
independent recomputation; this is an integrity checksum, not a secret,
signature, custody mechanism, persistence service, or proof against a party
able to replace both data and digest.
Retrieval timestamps accept only an exact built-in fixed-offset `timezone`;
timezone subclasses are rejected before hooks can run, and accepted values are
stored as exact UTC datetimes.

Presence and explicit null sets are retained separately. Source inputs are an
exact JSON-like graph boundary: only built-in `dict` objects and built-in `list`
arrays are accepted at every level; tuples, arbitrary mappings, subclasses, and
unsupported objects fail before traversal. The complete source graph and every
line are recursively copied into immutable redacted mapping and sequence
wrappers, so later caller mutation cannot change an observation and every
reachable retained container repr is non-disclosing. The typed observation
`lines` remain tuples of redacted invoice or payment line observations, and
payment links remain tuples of redacted link observations.

Before sorting, freezing, or digesting, an iterative preflight validates every
mapping key and enforces maximum depth 24, 50,000 total nodes, width 2,000 per
container, 4,096 characters per string, and 2,000,000 aggregate source bytes.
Byte-like material is unsupported and rejected after a bounded length check.
Invoice and payment lines, and each payment line's links, have the stricter
750-entry provider-evidence cap.
Q-S5A applies the same bounds to the complete retained wrapper graph before
reconstruction, rejects cycles and aliases, and reconstructs iteratively.

Money conversion accepts exact integers, `Decimal` values, and plain decimal
strings. It rejects booleans, floats, exponent notation in strings, non-finite
values, values above 10^18, more than 38 significant digits, and more than 12
decimal places. No rounding occurs. Interpreted dates are strict ISO calendar
dates. Interpreted metadata timestamps require ISO date-time syntax with an
explicit `Z` or numeric offset.

All contract failures use bounded rule descriptions and never interpolate raw
source values. Adversarial coverage includes malformed containers and keys,
identity substitution, missing identity, empty/oversized lines, unknown line
categories, mutable aliases, absent/null distinctions, type-preserving digest
identity, stable attestation across mapping order and distinct attestation
across retrieval/binding/source changes, hostile decimals, dates/timestamps,
Unicode surrogates, all resource
bounds, repr/error disclosure, import capability, unchanged disabled-provider
behaviour, and absence of canonical/tax/payment/launch decisions.

## Deliberate non-capabilities and residual gates

The module exposes only direct observers over already-retrieved exact entity
payloads; it does not define or parse a `QueryResponse` envelope. It contains no HTTP/SDK, URL construction, credential access,
environment/configuration, logging, persistence, route, callback, query,
provider enablement, or canonical mapping capability. The existing disabled
`QuickBooksProvider` placeholder and shared provider contracts are unchanged.

The Payment extension is an uncommitted prerequisite candidate requiring
independent review and checkpointing. Q-S2 HTTP and
secret custody, Q-S3 callback/route lifecycle, Q-S5 canonical normalisation and
sync semantics, and Q-S6 sandbox, operational, privacy/security, enablement,
and launch evidence all remain separate open gates.
