# HICBC partner support and linked accounts — October v1 integration package

Status: authorised October v1 launch target (founder decision 17 August 2026),
feature-gated and not yet launch-ready.  HICBC may contribute to a customer
total, reserve or payment figure only where its evidence is adequate for that
purpose and the applicable privacy, retention, legal, security and
calculation-assurance gates have passed.  Neither the manual nor the linked
route may be activated or counted as launch-ready yet.

## Purpose

Determine High Income Child Benefit Charge (HICBC) responsibility using partner
information, while:

- calculating HICBC from each individual's adjusted net income (ANI), never a
  combined household income;
- providing a bounded manual partner-estimate journey;
- providing a privacy-preserving, mutually consented linked-account route;
- preserving material uncertainty rather than inventing certainty;
- never disclosing or implying a linked partner's precise ANI, income band,
  bonus, relative salary or calculated personal tax.

## Feature gate

Both the manual and linked routes live behind a single explicit feature gate.
`reserved/config.py` reads `HICBC_ENABLED`; only an explicit true value
(`1`/`true`/`yes`/`on`/`enabled`, case-insensitive) enables registration of the
`hicbc` blueprint in `create_app()`.  Absent, empty, malformed or false values
leave the feature disabled and the routes return the normal unavailable/404
behaviour.  The gate is never inferred from database rows, credentials, the
environment name or any other feature flag.

## Supported tax years and authority

- 2025/26 and 2026/27 (the engine's `SUPPORTED_TAX_YEARS`).
- ITEPA 2003 s.681B–681C; Finance Act 2012 Sch. 1; Finance (No. 2) Act 2024 s.5;
  HMRC PAYE14015.
- Threshold £60,000, cap £80,000, £200 per whole percentage point (2024/25
  onwards).  Staged downward rounding: floor the relevant Child Benefit total,
  apply the whole complete-£200 percentage (capped at 100%), then floor the
  charge.

## Responsibility model

The charge falls on the person in the household with the higher ANI; where the
two ANIs are equal, ITEPA 2003 s.681B places the charge on the Child Benefit
claimant (condition A under s.681B(2) and condition B under s.681B(3)).  The
engine returns a single coherent result (`HicbcResponsibilityResult`) separating:

- the user's individual ANI;
- partner evidence used only for comparison;
- responsibility status (`no_charge`, `person_liable`, `partner_liable`,
  `ambiguous`, `insufficient_facts`);
- the user's own projected HICBC (zero when the partner is liable);
- a bounded possible charge where responsibility is ambiguous;
- household change status;
- evidence provenance and uncertainty;
- tax year, ruleset version, permitted and prohibited uses.

Cases:

1. Neither above threshold → no projected HICBC.
2. User above, partner below → user carries the charge.
3. Partner above, user below → user does not carry the charge.
4. Both above, user higher → user carries the charge.
5. Both above, partner higher → partner carries responsibility; the partner's
   ANI and calculated personal tax are not exposed to the user.
6. Equal ANI → the charge follows the Child Benefit claimant: the user is liable
   when the user is the claimant, and the partner is liable when the partner is
   the claimant; an unknown claimant fails safe as insufficient facts.
7. Overlapping or uncertain partner range → ambiguous; the possible user charge
   is bounded between £0 and the user's full charge rather than collapsed.
8. Missing, incomplete, stale, revoked or conflicting partner evidence →
   explicit uncertainty or insufficient facts, never an assumed user liability
   and never zero.
9. Changes in either ANI → automatic recomputation; responsibility can move
   between partners (reported as a household change status).
10. Claimant identity alone does **not** establish a personal charge: it only
    breaks an equal-ANI tie.  A determinate personal charge additionally requires
    an explicit no-partner-for-the-period fact, adequate partner ANI evidence, or
    an explicit valid responsibility fact (for example
    `taxpayer_is_higher_ani_partner=True`).  A false, unknown, malformed or
    contradictory `taxpayer_is_higher_ani_partner` value is not ignored and is
    not relabelled as user liability.

### Single-claimant model

The bounded v1 model supports a single Child Benefit claimant per household
(person, partner, or none).  It does **not** support the two partners separately
claiming Child Benefit for different children: there is no input channel for a
second claimant, and the engine never reduces two claims to one invented
claimant.  A dual-claimant case is explicitly unsupported and must be rejected
(fail closed) rather than silently assigned a single claimant.

## Manual partner-estimate path

`reserved/web/hicbc.py` exposes a bounded, authenticated manual path at
`/v2/hicbc`:

- state whether they receive Child Benefit (yes/no/unknown) and, if so, the
  number of children and entitlement weeks, or an explicit annual total;
- state whether they have a relevant partner for HICBC purposes, together with
  whether that preceding partner-status answer was true for the whole tax year;
- provide a partner ANI point or a low/high range;
- update, replace or remove the estimate.

Omitted entitlement weeks remain unknown and are never silently treated as a
52-week amount.  `relationship_covers_full_year` records whether the preceding
`has_relevant_partner` answer held for the whole tax year: `1` means the answer
was true throughout, `0` means the status changed during the year, and `NULL`
means unknown.  It does not mean that a relationship existed for the whole
year.  Thus `no` plus `1` establishes no relevant partner throughout the year,
while either partner answer plus `0` is a changed-status case requiring adequate
period evidence before a full-year point result is possible.

Schema version 10 adds `partner_status_period_semantics`.  New customer saves
record `status_answer_full_year`; pre-correction rows retain `NULL` and are
treated as unknown until the customer reconfirms.  This compatibility boundary
is necessary because the repository proves the feature is disabled by default
and declared not activated, but—without accessing live deployment data—it
cannot prove that no explicit non-production enablement ever persisted a row.
No old ambiguous value is silently reinterpreted.

The minimum information necessary is collected.  The partner's name, email,
National Insurance number, employer, bank information and underlying income
breakdown are never asked for or persisted.

A responsibility transition is surfaced as a neutral, server-derived, one-shot
message ("Your household tax position has changed.") stored in the signed
session and popped on read.  It is never driven by a customer-supplied query
parameter, so a stale or replayed parameter cannot fabricate a change
notification.

## Uncertainty and freshness

Manual partner estimates retain provenance: a stable evidence ID, source kind,
tax year, effective period, observation/confirmation date, point/range
representation, completeness, recency state, selection reason, and an
uncertainty issue with a determinable point/range/not-determinable effect.  No
universal staleness period is hard-coded; observation date, effective period,
source, completeness and confirmation state are preserved so a versioned
freshness policy can be introduced later.  Zero, unknown, omitted and
not-applicable remain distinct.

## Linked-account consent

`reserved/database.py` adds two HICBC-only tables, `hicbc_links` and
`hicbc_link_invitations` (schema version 7).  The flow is:

1. A signed-in user creates a single-use invitation.  Only the SHA-256 hash of a
   high-entropy token is stored; the raw token is returned to the creator once
   for out-of-band sharing.
2. The other user accepts the invitation while signed in to their own account.
   Acceptance establishes (or re-activates after revocation) one normalised,
   active `hicbc_links` row for the pair and tax year.
3. Either participant may revoke/unlink at any time; the row is retained as
   minimal audit evidence (`status='revoked'`) and never used again for
   cross-account access.

Consent is mutual, purpose-limited to `hicbc_responsibility`, short-lived and
single-use.  Self-links, duplicate active links, expired tokens and invalid
tokens all fail closed.  No partner financial value is stored in a link row; the
linked partner's ANI is derived from their own profile at read time and held
only inside the internal comparison.

### Manual vs linked evidence

Neither manual nor linked evidence has automatic precedence.  Where both exist
the engine merges them into a range spanning both sources (or a point when they
agree exactly) and retains both provenance records; a material disagreement
degrades responsibility to a bounded/ambiguous state rather than silently
selecting one source.  Where only linked evidence exists, an active link affirms
the partner and the partner's own ANI supplies the comparison.

## Privacy, retention and deletion

- `hicbc_estimates` persists one manual row per `(user_id, tax_year)`; the
  period field qualifies the preceding partner-status answer and its semantics
  marker distinguishes reconfirmed rows from legacy ambiguous rows; money/ANI
  values are stored as canonical Decimal strings (TEXT), never binary floating
  point.
- `hicbc_links` and `hicbc_link_invitations` store identity, consent state,
  purpose, relationship-period facts and timestamps only — no partner financial
  value.
- Reads and writes are scoped to the authenticated user; cross-account access is
  available only through an active, mutually consented link and only for the
  internal comparison.
- State-changing requests are CSRF-protected; sensitive responses are no-store.
- Raw partner values are never returned in the customer JSON view, rendered in
  the result section, or logged.
- The partner-liable customer headline describes only the receiving user's own
  consequence ("Reserved has not included a High Income Child Benefit Charge in
  your estimate."); it never states or implies that the partner earns more, is
  liable, carries the charge, or discloses the partner's ANI, band or tax.
- Manual partner evidence is labelled as user-supplied; linked evidence is
  described as shared through a linked account and is never falsely labelled as
  user-supplied.
- `delete_all_hicbc_estimates_for_user(user_id)` and
  `delete_all_hicbc_links_for_user(user_id)` are the repository deletion hooks
  that a later account-deletion workflow must invoke.

The manual route's privacy notice, lawful basis and retention schedule, and the
linked route's consent and cross-account authorisation/security evidence, still
require independent privacy/retention/legal review before production
activation.

## Purpose-aware integration boundary

`reserved/engines/hicbc_integration.py` gates an already computed
`HicbcResponsibilityResult` by customer purpose:

- `informational_rule`: a qualified point or bounded range may be shown, never
  as an actionable amount;
- `personalised_estimate`: HICBC enters the estimated total only when
  responsibility and Child Benefit evidence are adequate (determinate, no
  material uncertainty);
- `reserve_guidance`: the same determinate requirement, never when the effect is
  indeterminable or responsibility is ambiguous;
- `payment`: never actionable in this package — payment integration has no
  independent approval yet.

An ambiguous, uncertain or insufficient result can therefore never be promoted
into an actionable total, reserve or payment figure.

## Remaining approvals / explicitly not built

- production activation of the manual path (privacy notice, retention and legal
  review outstanding);
- production activation of the linked path (consent, cross-account
  authorisation, privacy and security review outstanding);
- independent assurance of HICBC annual-total/reserve/payment integration;
- HICBC payment initiation (PIS/VRP) integration — not connected here;
- relationship history, split-year and multiple-partner cases.
