# W8-S2C0 Annual-to-cash identity evidence

## Scope

`compose_annual_to_cash_position` issues each successfully returned
`AnnualToCashPosition` into a process-local registry held in closure state. The
registry writer is bound only into the public composer's
closure: it is not an ordinary public or private module attribute. All composer
outcomes, including every early unresolved return, pass through that same bound
writer after inputs and fail-closed status decisions have been captured.
Qualified, review-required and unresolved results can therefore be traced
internally; issuance does not make any result customer-presentable or accepted.

The public `AnnualToCashPosition` field list, constructor, equality, repr and
`asdict` representation are unchanged. Issuance is not stored on the dataclass.

## Bound provenance

The immutable `AnnualToCashInputProvenance` records:

- the annual-position content reference and preceding-year status;
- the optional prior-year reference, preserving absence versus presence;
- deductions/credits and prior-PoA content references plus their exact ordered
  source evidence IDs;
- ordered payment content references and ordered payment source IDs;
- a deterministic account-reconciliation content reference;
- an optional set-aside-evidence content reference, preserving absence versus
  presence;
- `as_of` and `stale_after_days`.

References are canonical SHA-256 references. The public position identity binds
the complete position graph and the complete provenance record, including
semantic Python type names, dataclass fields, enum values, dates, tuple order,
`None`, booleans, strings, integers, and Decimal sign/scale as represented by the
upstream contracts.

## Verification contract

`annual_to_cash_position_identity(value)` and
`annual_to_cash_position_provenance(value)` accept only the exact live object
issued by this producer in this process. Every access checks:

1. exact `AnnualToCashPosition` type before graph inspection;
2. an identity-keyed registry entry;
3. the registry weak reference points to the same live object (preventing stale
   entry and object-ID reuse inheritance);
4. two independently captured current canonical digests agree; and
5. the current digest matches the issued digest with constant-time comparison.

All failures use one categorical, value-free `ValueError`. Exact-type,
allow-listed canonicalisation avoids equality, hash, repr, property and generic
dataclass/introspection hooks on attacker-controlled types. Hashing,
serialization, canonicalisation, comparison, locking and registry state are
captured in closure state when the module is constructed. No callable writer,
writer token, registry, or registry-writing factory remains in module attributes,
function defaults, keyword defaults, or function dictionaries. Rebinding or
calling ordinary module globals, including with provenance copied from a
legitimate result, therefore cannot confer issuance. Identity and provenance
accessors retain only read paths into the registry.

The raw `_compose_annual_to_cash_position` global is deleted after the public
closure-bound composer is created. The raw composer remains reachable only as
the intended private closure reference used by that public composer.

Direct construction, `object.__new__`, dataclass replacement, shallow/deep copy,
pickle reconstruction, equal graph reconstruction, state transplantation and
subclassing do not copy or create a registry entry. A deterministic digest may
be shared by separately issued objects with identical content and provenance;
each object still requires its own live registry entry.

## Security boundary and residual limits

This mechanism provides process-local producer integrity for ordinary API
consumers. It is not authentication, durable provenance, process isolation,
customer-handoff approval, durable audit evidence, or cross-process
verification. Serialized or reconstructed values are deliberately unissued.
A future durable provenance contract requires separate authorization and a
cryptographic trust/key design.

SHA-256 collision resistance is assumed. As with any in-process Python control,
Python closure contents are introspectable: code authorised to inspect arbitrary
interpreter objects can read a public function's `__closure__` cells and invoke
a captured writer. Such code is already inside the producer's trust boundary;
it must be controlled through code review and execution isolation. This design
does not claim capability secrecy from that code. Ordinary module-attribute and
function-metadata inspection remains within the tested API-consumer boundary and
exposes no writer through module globals, module attributes, defaults, keyword
defaults, or function dictionaries. Concurrent out-of-band mutation is checked
using repeated complete captures, but this mechanism is not a substitute for
process or interpreter isolation.

## Downstream handoff

The intended W8 customer-handoff service can receive the live producer result
plus only the public `annual_to_cash_position_identity` and
`annual_to_cash_position_provenance` readers. It can validate identity and bound
input provenance without receiving `compose_annual_to_cash_position` or any
other issuance API. This is a process-local validation handoff, not proof of
authentication or durable provenance.

Passing tests demonstrate implementation behavior; they are not independent
assurance or release approval.
