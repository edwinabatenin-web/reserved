# W9-S3A — annual-position persistence contract

Recovery job: fresh correction of the W9-S3A annual-position persistence
contract. Immutable base/HEAD `10fb93e2e6ab567a72d2370c1603768a7ac04bb5`.

Scope: bounded production contract, focused tests and evidence documentation.
This artifact defines a **minimised
primitive structured projection** of a reconstructed customer result for one
annual-position record. It performs **no database, network, configuration,
credential or activation I/O** and must not be committed until independently
reviewed.

Three authorised paths only:

- `reserved/annual_position_persistence_contract.py`
- `tests/test_annual_position_persistence_contract.py`
- `docs/W9_S3A_ANNUAL_POSITION_PERSISTENCE_CONTRACT.md` (this document)

## 1. Bounded conclusion

The contract reduces a live, integrated annual-position customer result to an
exact set of minimised primitive facts and re-derives the corresponding W8
customer result on demand. The projection is **not** a live
`W8CustomerResult`, a display object, or a pickle blob; it is an immutable,
frozen, slots dataclass whose fields are plain primitives, enums, tuples of
frozen primitives, or fixed-precision `Decimal` values.

The projection is an **admission-sealed** structure. A record is
`annual_cash_identity_admitted` only when it was produced by the single public
admission authority (`admit_annual_position_projection`). Public construction,
`dataclasses.replace` and `pickle` round-trips are **structural
reconstruction** only and can never mint an admission-sealed record. Ordinary
`copy.copy` and `copy.deepcopy` of an already validated immutable projection
return the same object: they are immutable admitted aliases, not a new
reconstruction or a way to mint authority. This separates issuance authority
from untrusted reconstruction and makes the trust state explicit and
fail-closed.

## 2. Trust / admission model

- **Admission authority.** `admit_annual_position_projection(annual_cash,
  result)` is the only path that yields a projection with
  `annual_cash_identity_admitted is True`. It validates the live producer facts
  and the reconstructed customer result, canonicalises money, then seals the
  record.
- **Structural reconstruction.** `AnnualPositionPersistenceProjection(*fields)`
  and `dataclasses.replace(...)` produce a structurally valid projection with
  `annual_cash_identity_admitted is False`. A decoded structural projection can
  carry the same `annual_cash_identity` value as an admitted record, but it is
  explicitly unadmitted: it never claims that an arbitrary calculation reference
  was issuance-validated.
- **Unpickling.** `pickle.loads` reconstructs through the captured rebuild
  helper and re-runs the full `__post_init__` validation, producing an
  unadmitted structural projection.
- **Immutable aliases.** `copy.copy` and `copy.deepcopy` first revalidate the
  complete sealed state and then return the same immutable object. They retain
  the source object's admitted/unadmitted state but create no new authority.
- **Fail closed.** Tampering with any field, corrupting the content identity,
  or rebinding a helper that reconstruction depends on raises rather than
  silently yielding a trusted record.

## 3. Data model (minimised primitive projection)

`AnnualPositionPersistenceProjection` is a `@dataclass(frozen=True, slots=True)`
with a fixed field order and a bounded, primitive value grammar. Every field is
either a plain primitive (`str`, `int`, `date`), a fixed-precision `Decimal`, an
exact enum member, or a tuple of frozen primitive/enum/`Decimal` facts.

Identity / authority fields:

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | `str` | Contract schema version (`SCHEMA_VERSION` = `reserved-annual-position-persistence/1.0`). |
| `record_purpose` | `str` | Fixed record purpose (`RECORD_PURPOSE` = `annual_cash_position_durable_projection`). |
| `record_version` | `int` | Monotonic version within a supersession chain; `1` for the first record. |
| `predecessor_identity` | `str \| None` | Content identity of the immediately preceding record, or `None` for the first record. |
| `annual_cash_identity` | `str` | Admission-bound opaque reference read from the live producer; it cannot be recomputed from the stored facts. |
| `annual_cash_identity_admitted` | `bool` | `True` only for admission-sealed records; `False` for any structural reconstruction. |
| `customer_result_identity` | `str` | Reproducible W8 customer-result content identity, re-proven on every read. |

Owner/business/tax-year/nation/purpose isolation fields:

| Field | Type | Meaning |
|---|---|---|
| `user_id` | `str` | Non-empty owner reference. |
| `business_id` | `str` | Non-empty business reference. |
| `tax_year` | `str` | `YYYY/YY` tax year. |
| `nation` | `SupportedNation` | Nation, held by the exact enum member (not a string). |
| `record_purpose` | `str` | Fixed purpose, revalidated against `RECORD_PURPOSE`. |

Reconstructed monetary / classification / provenance facts:

| Field | Type | Meaning |
|---|---|---|
| `evidence_classification` | `EvidenceClassification` | Exact evidence-classification enum member. |
| `annual_liability` | `Decimal` | Exactly two-decimal money. |
| `obligations` | `tuple[ObligationFact, ...]` | Frozen obligation facts (canonical money). |
| `adjustments` | `tuple[AdjustmentFact, ...]` | Frozen adjustment facts (canonical money). |
| `funding` | `FundingClassification` | Exact funding-classification enum member. |
| `funding_amount` | `Decimal \| None` | Exactly two-decimal money, or `None`. |
| `evidence_references` | `tuple[str, ...]` | Frozen, non-empty evidence references (strings). |
| `ruleset_version` | `str` | Producer ruleset version, pinned verbatim. |
| `as_of` | `date` | As-of date. |
| `stale_after_days` | `int` | Staleness horizon in days. |

Constraints and deletion/erasure state:

| Field | Type | Meaning |
|---|---|---|
| `customer_result_limitations` | `tuple[str, ...]` | Carried W8 limitations, renamed as reconstructed customer-result constraints. |
| `customer_result_prohibited_uses` | `tuple[str, ...]` | Carried W8 prohibited uses, renamed as reconstructed customer-result constraints. |
| `deletion_state` | `str` | Explicit, honest deletion state (`"not_deleted"`). |
| `account_erasure_eligibility` | `str` | Explicit erasure-eligibility state (`"unresolved"`). |
| `unresolved_inputs` | `tuple[str, ...]` | Explicitly unresolved governance inputs (retention, legal hold, encryption/key custody, activation). |

`ObligationFact` and `AdjustmentFact` are the already-reviewed frozen facts from
`reserved.services.w2_customer_language`; their money fields are canonical
two-decimal `Decimal` values. An internal `_integrity_seal` field (not a
constructor argument, excluded from repr/compare) re-binds the validated state
so tampering is detected on every read.

## 4. Identity model

`annual_position_projection_identity(projection)` computes a deterministic,
content-derived, **unkeyed and non-authenticating** SHA-256 digest over the
canonical representation of every durable fact **except** `predecessor_identity`
(the chain link) and `annual_cash_identity_admitted` (ephemeral trust state).
The digest prefix `annual-position-persistence:sha256-` and the module's
explicit wording state plainly that this is corruption/change detection only —
not a MAC, signature, or authenticity proof. Authenticated storage integrity and
key custody remain unresolved inputs.

- Equal facts always produce equal identities.
- Different facts (including different record versions, owners, businesses, tax
  years, nations, purposes, or money values) produce different identities.
- `hash(projection)` and `repr(projection)` are derived from the same validated
  content state and fail closed on a corrupted or tampered record.

## 5. Reconstruction

`reconstruct_w8_customer_result(projection)` rebuilds a live
`W8CustomerResult` from the exact minimised facts when the projection is
internally coherent. It is used by admission to verify that the stored
`customer_result_identity` actually reproduces from the stored facts, and it is
available for structural (unadmitted) projections as well. Genuine W8 identity
support is preserved: reconstruction of a compatible W8 result from exact facts
is retained, while the persistence projection itself remains a primitive
minimised structure.

## 6. Supersession and finite full-chain traversal

`supersede_annual_position_projection(predecessor, annual_cash, result)`
creates an admission-sealed successor and **rejects any boundary mismatch before
returning it**. Cross-user, cross-business, cross-tax-year, cross-nation, or
cross-purpose successors raise `ValueError` at the supersede boundary rather
than being returned for later validation.

`validate_supersession_chain(chain)` performs full finite-chain traversal:

- the first record must have no predecessor;
- every record must match the same owner/business/tax-year/nation/purpose
  boundary as the first record;
- no record may reference itself as its own predecessor;
- content identities must be unique (no replay/repeat);
- each successor must reference the immediately preceding record's identity and
  advance `record_version` by exactly one;
- the terminal record is returned.

The chain is finite and each supplied link is verified edge-by-edge. Focused
tests cover self-reference, repeated identity, broken adjacency, version skips,
chain lengths one through five and each supported cross-boundary mismatch. The
contract does not claim an exhaustive proof over every theoretically possible
cycle representation.

## 7. Canonical money

All monetary facts (annual liability, obligation/adjustment line amounts,
funding amount) are canonicalised to exactly two decimal places, or the input is
rejected. `Decimal('1.0')` and `Decimal('1.00')` can therefore never coexist as
different identities: the noncanonical exponent is rejected, and admission
canonicalises producer values such as `Decimal('0')` to `Decimal('0.00')`.

## 8. Reconstructed customer-result constraints

The carried W8 fields `limitations` and `prohibited_uses` are renamed to
`customer_result_limitations` and `customer_result_prohibited_uses`. This makes
clear that they constrain the **reconstructed customer result** (the underlying
W8 result), not the minimised durable projection itself. The projection is an
authorised minimised durable structure and is not falsely described as
prohibited from persistence.

## 9. Deletion / account-erasure state

Deletion and account-erasure eligibility are represented explicitly and honestly
without inventing retention periods, legal holds, or claiming deletion occurred:

- `deletion_state == "not_deleted"`;
- `account_erasure_eligibility == "unresolved"`;
- `unresolved_inputs` records `"retention_period_unresolved"` and
  `"legal_hold_unresolved"`.

No retention duration or legal basis is fabricated; those remain external
decisions.

## 10. Rebinding resistance

The local acceptance graph captures its exact primitives, policy constants,
original projection slot descriptors, and error types
at import time (`type`, `object.__getattribute__`, `object.__setattr__`, `range`,
`len`, `set`, `enumerate`, `any`, `isinstance`, `hash`, `tuple`, `str`, `int`,
`bool`, `Decimal`, `date`, `Enum`, `ValueError`, `Exception`, `hashlib.sha256`,
`json.dumps`, `hmac.compare_digest`, the dataclass helpers, the
producer/handoff/reconstruction types, and the public entry points). The
public constructors, validation, identity, reconstruction and full-chain
traversal therefore do not consult mutable `LOAD_GLOBAL` names for these
primitives. Rebinding module-level `range`, `len`, `set`, `enumerate`, `any`,
`isinstance`, `hash`, `tuple`, or `str`, or rebinding the module-level error
types, cannot bypass invalid-chain detection or change the exception type raised.

Every acceptance-critical projection read uses the original slot descriptor
captured when the class was created. Replacing a public class descriptor with a
property therefore cannot mask forged retained slot state. The focused suite
also recursively audits the locally reachable closure graph rather than merely
checking one entry point.

The already-reviewed annual-to-cash and W8 producer contracts remain explicit
external admission boundaries. Their live issuer/identity functions are
captured once, while this package independently copies, canonicalises and seals
only the supported primitive projection. This package does not claim that the
entire transitive implementation graph of those separate contracts contains no
mutable globals; nor can later rebinding of W9's exported constants or public
descriptors alter an already sealed W9 projection. Changes to those upstream
contracts require their own review and compatibility assurance.

The pickle rebuild helper is captured; if it is rebound after import, pickling
fails closed rather than silently serialising an attacker-controlled
reconstructor.

## 11. Bounded imports and no I/O

The module imports only standard library data primitives (`hashlib`, `json`,
`re`, `dataclasses`, `datetime`, `decimal`, `enum`) and the existing reserved
types it must stay compatible with (`annual_to_cash_integration`,
`w2_customer_language`, `w8_annual_cash_customer_handoff`,
`w8_customer_result`). It performs no file, socket, database, configuration,
credential, subprocess, environment, or activation access.

## 12. Independently reproduced defects → fail-closed mapping

| # | Defect | Fail-closed behaviour | Test |
|---|---|---|---|
| 1 | Public construction / `replace` can mint an admitted projection | `annual_cash_identity_admitted` is `False` for any structurally reconstructed record; only admission seals it. | `test_public_construction_is_structural_and_unadmitted`, `test_replace_cannot_mint_an_admitted_projection`, `test_pickle_decode_is_structural_and_unadmitted` |
| 2 | `supersede_annual_position_projection` returns cross-boundary successors | Supersede rejects cross-user/business/tax-year/nation/purpose before returning. | `test_supersede_rejects_cross_user`, `test_supersede_rejects_cross_business`, `test_supersede_rejects_cross_nation` |
| 3 | Mutable global/builtin/helper/class rebinding bypasses detection | Captured primitives, policy constants, original slot descriptors and error types keep detection intact; rebound helper fails closed. | `test_rebinding_primitives_cannot_bypass_chain_detection`, `test_rebinding_error_types_cannot_bypass_fail_closed`, `test_rebinding_rebuild_helper_and_class_cannot_bypass_admission`, `test_original_slot_descriptors_defeat_class_descriptor_masking`, `test_rebinding_exported_policy_constants_cannot_change_acceptance`, `test_local_acceptance_graph_has_no_mutable_global_resolution` |
| 4 | Missing focused test and evidence document | This suite and document cover the demonstrated hostile admission, reconstruction, representation, immutable copy aliases, replace/pickle reconstruction, supersession, finite-chain traversal cases, cross-boundary links, local rebinding cases, exclusions and no-I/O. | whole suite |
| 5 | Carried `limitations`/`prohibited_uses` imply the projection itself is prohibited | Renamed as customer-result constraints. | `test_carried_constraints_are_customer_result_constraints` |
| 6 | Deletion/erasure state inventing retention/holds/claims | Explicit, honest state with unresolved markers only. | `test_deletion_and_erasure_state_are_explicit_and_honest` |
| 7 | Equal amounts gain different identities from exponent differences | Noncanonical exponents rejected; admission canonicalises to two decimals. | `test_noncanonical_money_exponent_is_rejected`, `test_admission_canonicalises_producer_money` |

## 13. Verification

Run:

```bash
python3 -m pytest tests/test_annual_position_persistence_contract.py -q
python3 -m pytest tests/test_w8_customer_result.py tests/test_annual_to_cash_integration.py tests/test_w8_annual_cash_customer_handoff.py -q
git diff --check
python3 -m py_compile reserved/annual_position_persistence_contract.py
```

The focused suite demonstrates all seven defects now fail closed. The projection
performs no database/network/configuration/credential/activation I/O.

## 14. Stopping criterion

This is a pure network/database/credential/activation-inert contract. It defines
the minimised durable projection and its admission/identity/supersession
semantics, and deliberately stops at the persistence boundary: storage schema,
retention durations, encryption/key custody, and account-erasure workflows
remain external decisions not invented here.
