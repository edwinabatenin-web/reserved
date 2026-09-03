# W8-S3B geography-provenance handoff evidence

## Status and immutable base

This is an implementation candidate for fresh independent review. It is not an
accepted checkpoint, provider activation, launch-readiness claim or production
evidence.

- Branch: `codex/w8-s3b-geography-provenance-handoff`
- Base commit: `3278909feb33251dfb114a2f4c8fa234b3803811`
- Base tree: `0b06cfd2b4aa325ff1b68a5e65f68263ef5c41d9`

## Implemented boundary

The annual calculator now returns the exact canonical admitted nation
(`England`, `Wales` or `Northern Ireland`) or `None` when geography was absent.
Its process-local issuance capability binds that nation and the complete annual
result to the exact live object, so mutation, copying, replacement, pickling or
reconstruction cannot confer producer provenance.

The accounting-to-annual entry point requires a caller-supplied exact canonical
customer nation. It injects that nation into the annual calculator, verifies
the returned live producer result and records the same value in immutable
handoff provenance. It never reads or infers a customer's tax nation from an
accounting provider company address or an umbrella `GB`/`UK` country value.

The nation is copied through `CashReadyAnnualPosition` and the producer-issued
`AnnualToCashPosition`. Those boundaries capture the original geography
readers and bind the full result content to a live issuance registry. Altering
or reconstructing either result, or rebinding public/module helper names, does
not create valid provenance.

The final W8 annual/cash customer handoff no longer accepts a `nation`
argument. It reads the nation only after validating the live annual-to-cash
producer identity. A result with absent or malformed geography is refused as
non-actionable. The three admitted nations reach the existing W8 customer
identity and deterministic API JSON unchanged.

## Compatibility and fail-close boundary

Geography-free annual, cash-ready and annual-to-cash artefacts remain available
for internal compatibility and carry `nation=None`; absence is not promoted to
a supported-nation claim. The customer handoff is the action boundary and
returns no result for such an artefact.

Scotland, Scottish variants, `GB-SCT`, umbrella `GB`/`UK` values, unknown
jurisdictions, malformed values and contradictory aliases are rejected by the
annual entry point before arithmetic. The accounting handoff accepts only the
three exact canonical strings and rejects missing, ambiguous, subclassed or
otherwise malformed nation inputs before deriving accounting amounts.

The geography normaliser invokes captured built-in `str.split`, `str.lower`
and a captured built-in join operation directly. A hostile `str` subclass
cannot override those methods to reinterpret underlying unsupported text (for
example, making `Scotland` split as `England`).

The annual-to-cash issuance capability captures its complete acceptance graph:
exact type checks, raw attribute access, Decimal/date/primitive types, object
identity, weak-reference creation, dataclass/enum inventory, failure classes,
serialization, hashing and comparison. Its canonicalizer, issuer, lookup and
secure content-reference functions perform no acceptance-critical lookup
through mutable module globals. Rebinding the module's `object.__getattribute__`
therefore cannot hide a post-issuance nation mutation or promote it to the W8
customer result.

Existing owner, accounting evidence, tax-year, no-payment, no-filing,
no-persistence and network-inert boundaries are unchanged. This package adds
no provider call, credential, route, persistence, tax policy, payment action,
customer wording or launch claim.

## Adversarial verification matrix

The focused tests cover:

- all supported names/codes and canonical exact-string preservation;
- missing geography versus zero/unknown/umbrella/contradictory geography;
- explicit accounting-entry geography and matching annual/provenance values;
- absence of provider-company-country inference;
- annual and cash-ready mutation, replacement, shallow/deep copy and pickle
  reconstruction;
- annual, cash-ready, annual-to-cash and customer helper/module rebinding;
- exact end-to-end preservation for England, Wales and Northern Ireland;
- geography-less internal compatibility and customer refusal;
- customer owner/evidence/tax-year/no-payment controls; and
- deterministic API serialization of the producer-issued nation.

Verification is run with bytecode generation and pytest cache disabled. Exact
results at candidate freeze are:

- focused plus directly affected matrix: **574 passed**;
- repository-wide suite: **5,912 passed, 11 failed, 84 errors, 7 subtests
  passed** from 6,007 collected tests; and
- `git diff --check`: clean.

Every full-suite failure/error is an existing artefact or release-assurance
test whose safety guard intentionally refuses to build from the uncommitted
modified engine sources. The final failure/error inventory is confined to
`test_artefact_verification.py`, `test_assurance_metadata.py`,
`test_engine_adapters.py`, `test_release_gate.py` and `test_rw3_gate.py`, all
with the same categorical dirty-source refusal. No product, handoff or API
test failed. This expected uncommitted-candidate guard is not presented as a
full-suite pass.

All final SHA-256 hashes are recorded in the implementation handoff after the
candidate and this evidence file are frozen.
