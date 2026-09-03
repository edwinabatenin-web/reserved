# HMRC Individual Income 1.2 source-evidence boundary

## Authority and purpose

This package consumes only an exact successful observation from the integrated
transport-neutral `GET /individual-income/sa/{utr}/annual-summary/{taxYear}`
contract. The wire authority remains:

- `docs/HMRC_INDIVIDUAL_INCOME_1_2_ENDPOINT_EVIDENCE.md`
- `docs/HMRC_INDIVIDUAL_INCOME_1_2_CONTRACT_EVIDENCE.md`

It emits redacted source evidence for later independent mapping. It does not
call HMRC and is not canonical accounting/tax evidence, customer output,
liability, cash obligation, persistence, activation or transport behavior.

## Literal preservation

The bundle preserves without normalization or aggregation:

- API name `individual-income` and version `1.2`;
- source request-derived tax year;
- ordered employment items, including duplicates, with exact
  `employerPayeReference`, exact built-in `int` or `Decimal`
  `payFromEmployment`, and safe unknown member names;
- the four pensions/benefits members with exhaustive presence/absence,
  exact numbers where present, and safe unknown member names;
- top-level safe unknown member names;
- completeness exactly `UNVERIFIED`;
- a bounded non-empty opaque evidence/run reference;
- an aware built-in fixed-offset datetime; and
- when supplied, a lowercase SHA-256 digest of a separately redacted artefact.

Empty employment arrays and fully omitted benefit members remain valid source
shapes but stay completeness-unverified. Omission is retained as `None` plus an
absent-field name and is never converted to zero. Explicit source null remains
invalid. Decimal representation, including negative zero and exponent, is
preserved exactly when permitted by the source contract.

## Validation and redaction

The Income contract exposes one narrow public success-observation validator.
Its complete validation dependency graph (exact types, state shapes, request
constants, number bounds, Unicode/key rules and nested validators) is captured
before ordinary module-global rebinding. It rejects errors, subtypes, malformed
state, nested mutation, incoherent request/tax-year/source context and partial
substitution.

The source-evidence builder accepts only that validated exact observation. It
revalidates exact evidence result types, state shape, number bounds,
presence/absence coherence, unknown-name safety, reference, timestamp and
optional digest. Unknown source values were discarded by the source observer
and are never traversed here.

No UTR, request object, raw path, raw payload or provider error message is
retained. Repr and controlled validation failures are categorical and do not
echo employer references, amounts, evidence references or digest input.

Omission of the optional digest is distinct from presence; explicit `None` is
rejected. Constructors, dataclass replacement, copy, deepcopy and pickle all
re-enter closure-captured validation. Ordinary module constant, helper, regex,
type and callable-metadata substitution cannot promote invalid evidence. If a
public result-class binding is replaced, pickle fails closed because Python's
pickle identity check cannot resolve the original class. This boundary does not
claim resistance to arbitrary trusted code rewriting class methods or closure
cells, nor to coherent private-memory rewriting; those remain process/code-trust
controls.

## Explicit non-claims

Employment order and duplicates are evidence only. This boundary performs no
employer identity join, aggregation, double-count inference, sign/rounding or
currency policy, current-income claim, tax mapping, annual-liability or cash
composition, provider action, OAuth, credential access, routing, persistence,
networking, launch or customer presentation.

The candidate remains uncommitted pending independent review.
