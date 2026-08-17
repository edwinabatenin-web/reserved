# HICBC partner support — post-v1 capability

Status: authorised post-v1 work (founder decision 17 August 2026).  This is
**not** part of the October v1 supported tax total, reserve/set-aside guidance,
payment initiation, filing or launch claims.

## Purpose

Improve the accuracy of the High Income Child Benefit Charge (HICBC)
responsibility determination where partner information is available, while:

- calculating HICBC from each individual's adjusted net income (ANI), never a
  combined household income;
- providing a bounded manual partner-estimate journey;
- defining a narrow privacy-preserving interface for a future linked-partner
  source;
- preserving material uncertainty rather than inventing certainty;
- never disclosing or implying a linked partner's precise ANI, income band,
  bonus, relative salary or calculated personal tax.

## Supported tax years and authority

- 2025/26 and 2026/27 (the engine's `SUPPORTED_TAX_YEARS`).
- ITEPA 2003 s.681B–681C; Finance Act 2012 Sch. 1; Finance (No. 2) Act 2024 s.5;
  HMRC PAYE14015.
- Threshold £60,000, cap £80,000, £200 per whole percentage point (2024/25
  onwards).  Staged downward rounding: floor the relevant Child Benefit total,
  apply the whole complete-£200 percentage (capped at 100%), then floor the
  charge.

## Responsibility model

The charge falls on the person in the household with the higher ANI.  The engine
returns a single coherent result (`HicbcResponsibilityResult`) separating:

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
6. Equal ANI → ambiguous (no statutory "higher" person; no tie-break invented).
7. Overlapping or uncertain partner range → ambiguous; the possible user charge
   is bounded between £0 and the user's full charge rather than collapsed.
8. Missing, incomplete, stale, revoked or conflicting partner evidence →
   explicit uncertainty or insufficient facts, never an assumed user liability
   and never zero.
9. Changes in either ANI → automatic recomputation; responsibility can move
   between partners (reported as a household change status).

## Manual partner-estimate path

`reserved/web/hicbc.py` exposes a bounded, authenticated manual path at
`/v2/hicbc`:

- state whether they receive Child Benefit (yes/no/unknown) and, if so, the
  number of children or an explicit annual total;
- state whether they have a relevant partner for HICBC purposes;
- provide a partner ANI point or a low/high range;
- update, replace or remove the estimate.

The minimum information necessary is collected.  The partner's name, email,
National Insurance number, employer, bank information and underlying income
breakdown are never asked for or persisted.

## Uncertainty and freshness

Manual partner estimates retain provenance: a stable evidence ID, source kind,
tax year, effective period, observation/confirmation date, point/range
representation, completeness, recency state, selection reason, and an
uncertainty issue with a determinable point/range/not-determinable effect.  No
universal staleness period is hard-coded; observation date, effective period,
source, completeness and confirmation state are preserved so a versioned
freshness policy can be introduced later.  Zero, unknown, omitted and
not-applicable remain distinct.

## Privacy and data retention

`reserved/database.py` persists one `hicbc_estimates` row per
`(user_id, tax_year)`.  Money/ANI values are stored as canonical Decimal strings
(TEXT), never binary floating point.  Reads and writes are scoped to the
authenticated user; there is no cross-user access.  State-changing requests are
CSRF-protected.  Raw partner values are never returned in the customer JSON view
or rendered in the result section, and are not logged.  The privacy notice and
retention schedule require review before production activation.

## Future linked-partner hook

`reserved/engines/hicbc_partner.py` defines `PartnerEvidence` (source-neutral)
and a `LinkedPartnerEvidenceProvider` protocol so a future authorised linked
source can supply privacy-minimised, provenance-bearing comparison evidence
without exposing the other user's raw financial data.  A synthetic provider
proves the interface and privacy boundary.  No account linking, invitations,
discovery, consent screens or cross-account database access are implemented.

## Explicitly not built / remaining approvals

- account linking, partner discovery, invitations, consent screens;
- relationship history, split-year and multiple-partner cases;
- automatic staleness cut-offs;
- production activation of the manual path (privacy notice, retention and
  legal review outstanding);
- any inclusion of HICBC in v1 totals, reserve guidance, payments or launch
  claims.
