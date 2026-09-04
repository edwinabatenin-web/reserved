# W8-S2C annual/cash presentation-handoff evidence

This integration-resolution candidate composes the independently reviewed
W8-S2C correction checkpoint
`67de691bf9bd447789027307473689ae59331c40` with the current clean integration
baseline `f25a90a98be39f41cbb71138d3d68bf3b96f6427`. It preserves the later
tax-year and geography provenance hardening already present on that baseline
(including the source/integration checkpoint lineages represented by
`a3164e7`/`16e586f` and `33aa569`/`afe1e9d`) rather than choosing either side
of the collision wholesale.

The candidate provides one pure, network-inert adapter from the accepted
`AnnualToCashPosition` graph to an explicitly **owner-unbound** presentation
handoff. It introduces no route, persistence, authentication, provider call,
calculation, wording, payment authority or activation.

The adapter accepts only the authentically reachable
`QUALIFIED_LOCAL_RESULT` state. Under the current upstream contract the annual
liability is always sourced as `LOCAL_ESTIMATE`; consequently this boundary
never relabels a locally calculated amount as HMRC-confirmed or HMRC-recorded.

The complete input graph is bounded for depth and node count and rejects
cycles, subtypes and undeclared state. The adapter recomputes the exact
`CashObligationReconciliation` and `CashFundingPosition` from their retained
upstream inputs and requires equality before copying amounts or dates. It also
requires the exact ordered set of opaque evidence references already present
in the snapshot.

The composer produces an exact frozen, content-bound value. Ordinary direct
construction, dataclass replacement, copying and pickling are rejected;
low-level mutation invalidates its integrity digest. The module-private issue
token and digest are **not** secrets, signatures, provenance or authenticity
proofs; they detect accidental/ordinary mutation only. Downstream acceptance
always uses the public exact-source validator/projector, and the public identity
routine also requires that validation rather than trusting the token or digest.
The value retains the exact
source position identity, annual-position reference, evidence references,
as-of date, tax year, admitted UK nation, ruleset and upstream contract
version. Nation and tax year are copied only from the exact revalidated source;
they are not caller-supplied. Missing, unsupported, mutated or coherently
reconstructed geography/tax-year state therefore fails closed. Its public
validator/projector requires the exact revalidated source snapshot, evidence
set and a caller-supplied expected as-of date before returning presentation
facts. A mismatched newer/older source context, replayed context or substituted
fact therefore fails closed.

The result contains no user or business identity and is fixed as
`owner_authoritative=False`. It prohibits owner-authoritative public use,
customer rendering and persistence until a separate accepted authenticated
owner/business boundary binds the presentation. It does not claim to solve
ownership or request-context authority. It also makes no claim that its source
is globally latest: the eventual authenticated state adapter must supply the
authoritative expected as-of date and current source snapshot.

Unresolved, review-required, forged-CALCULATED, malformed, mutated,
substituted, duplicated, incomplete, cyclic, over-deep, subtype-bearing and
unsupported graphs return `None` without projecting values. The implementation
catches only expected data/validation failures; it does not catch
`BaseException`.

This is a candidate for independent review only. It does not close ownership,
persistence, routing, target-runtime or HMRC-observation gates and does not
claim W8-S2 completion.

## Verification scope

The focused suite covers authentic classification, exact nested recomputation,
mutated amounts and dates, admission sealing, source-context substitution and
replay, copy/pickle/dataclass replacement, owner-unbound output, evidence
substitution, duplicate identities, cycles and depth bounds, plus all supported
launch nations and hostile geography/tax-year mutation and reconstruction. The affected
upstream W1/W2/W8 matrix and full suite are also run. The two historical
absence sentinels use exact AST allowlists for every import and call in this
named boundary, including only necessary safe standard-library and reviewed
upstream symbols. Negative source fixtures prove that relative, third-party,
host/process/network, aliased dynamic-loader, indirect-call, annual-calculation,
internal-composition, broader-engine and web/API/model/database expansion
remain forbidden.
