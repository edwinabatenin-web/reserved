# W10-S4D disabled-first offer-configuration contract

## Result and authority boundary

This package is a pure provider-neutral structural candidate under
`FD-W10-001`, the accepted W10-S1/S2B/S4A/S4B boundaries and `FD-OA-001`.
Its immutable source is commit
`961168dd5c17fbef7ba96ac1599a7f5888af1db3`, tree
`a7788d5d9fd5c11034045694df25eb8681ab86d0`.

The current accepted state is unchanged: the special-offer capability is
required, but the operational offer registry remains empty; promotions are
inactive; promotion codes are disabled; eligibility, duration, stacking and
discounted-price registries are empty; and partner offers are disabled and
unsupported. This package does not select or approve an offer.

`reserved/billing/offer_configuration_contract.py` can issue only an opaque
producer-issued handle in the inherited process lineage whose detached
primitive projection is labelled
`unadmitted_offer_configuration_candidate`. Structural validation is not
policy acceptance, runtime admission or action authority. Every direct runtime,
provider, provider-mapping, price, eligibility-decision, checkout, charge,
entitlement, approval, activation, persistence, display and reconciliation
authority flag is fixed to false.

## Exact structural input

Candidate creation has no positional input and requires the exact ordered,
complete named fact set. No default supplies a policy value:

- a Reserved-namespaced configuration identifier and caller-supplied future
  offer-policy version;
- the exact current catalogue authority version and one of the three exact base
  plan keys;
- a caller-supplied positive GBP amount in integer minor units that is below the
  exact rederived base amount;
- exact UTC availability start/end facts with a non-empty interval;
- a positive caller-supplied duration count and one structural unit from
  `calendar_days`, `calendar_months` or `billing_periods`;
- local eligibility- and stacking-policy record references;
- an exact immutable provenance record containing its schema, decision ID,
  matching policy version, decision owner, exact UTC decision time, local
  record/section reference and lowercase SHA-256 content digest;
- an exact UTC evaluation time and redacted `evidence:` reference.

The duration-unit vocabulary only carries caller-supplied structure. The
contract does not turn a count into dates, compare offer economics, derive a
percentage, calculate a price, decide eligibility, evaluate a customer or
interpret stacking.

Unknown catalogue versions, plan keys or currencies fail. Boolean, floating,
non-finite, zero, negative, base-equal and base-exceeding money fails. Empty or
contradictory time intervals, invalid duration facts, future-dated provenance,
partial/extra/reordered records, built-in subclasses, mutable provenance
containers, active/approved fields, promotion codes, partner flags, direct
eligibility decisions, entitlement/access fields, discount percentages or
algorithms, provider identifiers and secret-shaped material all fail closed.
Partner and reseller configurations are rejected, as are affiliate and
marketplace-shaped configurations; they are not merely projected inactive.

A single closure-bound finite-root validator covers every caller-controlled
configuration/policy/evidence identifier and every policy-provenance text
carrier. It case-folds and removes non-alphanumeric punctuation into one
canonical exclusion form, then rejects the finite literal roots `partner`,
`reseller`, `affiliate`, `marketplace` and `coupon` wherever they occur. This
includes adjacent alphanumeric IDs/names and punctuation inserted inside a
root. The same canonical form rejects the finite promotion-code forms
`promotioncode`,
`promotionscode`, `promocode` and `promoscode`. It does not infer synonyms,
intent or natural-language meaning. Configuration, policy and evidence
identifiers and provenance text reject the finite literal roots `customer`,
`user`, `member`, `account` and `segment` under the same canonicalization.

Two exact, case-insensitive, alphanumeric-bounded neutral words are masked
before canonicalization: `accounting` and `accountability`. The exception does
not cover a suffix in the same alphanumeric run or punctuation inserted inside
either word. The sole customer-subject exception below applies only to complete
policy references.

Eligibility, stacking and provenance record references must use the
provider-neutral `docs/` policy namespace, so a record such as
`customers/7.md#eligible` is rejected. A customer-, user- or member-bearing
record receives only one narrow generic-policy exception: its Markdown filename
must exactly follow `<subject>-(eligibility|access)-policy` (with an allowed
dot, underscore or hyphen separator) and its section must be a general or
standard rule/policy section. That complete-reference allowlist is evaluated
first. Every other reference containing the exact reserved roots `customer`,
`account`, `member`, `user` or `segment` is rejected case-insensitively, including
when an alphanumeric ID or name is directly adjacent to the root in a filename
or section. Account roots, plural subjects, additional filename suffixes and
subject-specific anchors therefore remain rejected. Thus
`docs/CUSTOMER_ELIGIBILITY_POLICY.md#general-rules` is structurally valid, while
`docs/CUSTOMER_ELIGIBILITY_7.md#policy` and
`docs/customer-eligibility-policy.md#account-7`,
`docs/customer7-eligibility-policy.md#general-rules` and
`docs/OFFER_POLICY.md#useracme` are not. This is an exact reserved-root and
complete-reference grammar, not a broad prose or NLP classifier.

## Identity, detachment and reconstruction

The candidate projection contains exact immutable built-ins only. It copies and
canonicalises every caller fact, rederives the base catalogue amount, converts
UTC datetimes to canonical text and derives a deterministic SHA-256 content
identity from the complete ordered content. Repeated evaluation of identical
facts produces equal content identities but distinct opaque handles.

Direct construction, `object.__new__` forgery, subclasses, ordinary copy,
deepcopy, pickle/reconstruction, a recreated projection and a recomputed
lookalike identity cannot become a producer-issued candidate. The saved
closure-bound validation/projector protocol does not trust rebound public
constants, functions, helpers, callable defaults or class properties. Each
issued handle contains a private constructor-gated integrity identity and seal
bound independently to that exact handle identity, exact projection object,
content identity and configuration ID. Validation contains no discoverable
mutable dict/list/set issuance registry, so coherently editing two registries
cannot substitute another candidate or enrol a forged handle.

The issuance boundary is intentionally described as the inherited process
lineage, not as strictly process-local. A POSIX fork inherits the live handle,
closure and seal, so the saved validator succeeds in the child; the result
is still the same unadmitted candidate with all thirteen authority flags false.
A fresh interpreter, reconstruction or module reload does not manufacture
issuance. A reloaded module validator rejects an old handle, while a saved old
validator remains tied to its old closure and seal. The seal is not an
operational offer registry, persistence mechanism, fork-resistant admission
mechanism or runtime authority.

This is a fail-closed structural integrity boundary against public construction,
ordinary mutation, projection reconstruction, copied integrity parts and the
reviewed coherent-registry attacks. Python code with unrestricted same-process
introspection and low-level object mutation is outside this package's trust
boundary; the contract does not claim to provide a security boundary against
arbitrary code execution in its interpreter.

## Compatibility and unchanged accepted boundaries

The static contract binds the exact current `FOUNDER_DECISIONS.md` and W10
completion-map blobs plus the accepted/current W10-S1, S2B, S4A and S4B source
and test blobs. Those bindings are assurance facts embedded at construction;
the module performs no runtime file reads.

The candidate is not accepted by the existing Checkout request contract: its
extra candidate field is rejected by that contract's exact input surface. It is
not a synthetic initial-payment authority and cannot be consumed by the local
Stripe initial-payment ingress.
Existing Stripe ingress continues to reject non-empty discount data.
That applies at invoice, invoice-line and subscription boundaries.
No accepted source or test is modified by this package.

## Later gates and residual limits

There is no actual offer, discount value selected by Reserved, percentage,
algorithm, customer segment, eligibility decision, promotion code, partner or
reseller path, VAT treatment, trial, tier, entitlement effect, provider mapping,
provider configuration, Checkout integration, customer presentation,
persistence, SDK, network access, credential, environment read, route, template,
database, file I/O or provider call.

A runtime consumer cannot exist on this contract alone.
It requires later accepted policy/version authority.
That authority must settle the exact amount,
availability, duration, eligibility and stacking outcomes. Later work also needs
independent review of a separately bounded runtime consumer; durable atomic
configuration and activation controls;
accepted provider mapping/configuration; Checkout, ingress, reconciliation and
entitlement evidence; applicable security/privacy/finance/tax/operations/target
assurance; and separate Founder production, release and go-live authority.

This contract does not complete W10-S4. It also does not complete W10-S2,
W10-S6, W10-S7, any terminal or threat gate, or W10. The accepted completion
status remains 0/8 slices and 0/13
terminal checks; W9 remains 0/5 and October remains not ready.

## Verification record

Executed locally on 5 September 2026 with `PYTHONDONTWRITEBYTECODE=1`, repository
pytest addopts cleared and the pytest cache provider disabled:

- corrected split-root matrices and neutral positives: 165 passed;
- focused hostile suite: 439 passed;
- authority-specified affected suite: 479 passed;
- final combined focused-plus-affected freeze: 918 passed;
- `git diff --check`: exit zero.

The optional Ruff check was not available in this interpreter (`No module named
ruff`); it is not part of the authority-required verification. These local
results are implementation evidence only. This document does not self-accept,
claim independent review, close a residual gate or authorize integration.
