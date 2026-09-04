# Manual MTD scope indication — synthetic runtime evidence

## Candidate and boundary

Implementation candidate on `e6854d74a8f7aebc4f228769eb195c84a7962376`
(tree `e8714d14b623a32755c01961f39df2677db57116`), under the bounded
`work/mtd-manual-journey-authority.md` envelope. Founder Decisions remain
SHA-256 `78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`.
This is implementation evidence for different independent review, not acceptance
or a completed MTD/October launch gate.

The authenticated dashboard conditionally links to the actual GET/POST
`/v2/mtd/scope-indication`. GET renders a real HTML form with the application's
CSRF token. POST admits finite source facts, creates real `IncomeSource` rows,
calls the captured existing `present_mtd_scope_indication` issuer and passes
only its live handle to the captured existing `render_mtd_scope_indication`.
There is no browser JavaScript or caller-supplied result dictionary. No accepted
MTD engine, issuer, renderer or temporal-copy file is changed.

`MTD_MANUAL_SCOPE_ENABLED` must equal the exact string `1` at request time.
It defaults off. Either existing production signal (`FLASK_ENV=production` or
a live Clerk publishable-key signal) denies access even when enabled. The route
also requires an exact positive integer signed-session user that still exists.
These are application gates, not a new network-isolation mechanism. Root's
synthetic browser check must use a disposable loopback-only server.

## Exact request vocabulary

Only a bounded URL-encoded POST is admitted: at most 32,768 bytes, no files,
query arguments, duplicate form keys or unrecognised fields. CSRF is checked
by the existing global protection; `csrf_token` is not an admission fact.
Admission accepts only string field names and string values of at most 100
characters. Missing finite answers remain unknown. Malformed values and forged
authority fields produce a fixed bounded 400 result; raw values and exceptions
are not reflected.

The following fields have exactly these choices (blank is unknown):

| Field | Choices | Supported numeric subset |
|---|---|---|
| `assessment_year` | `2024-25`, `2025-26`; another well-formed year is unsupported | The two named completed years |
| `source_basis` | `submitted_return`, `records_only`, `draft_return`, `year_to_date`, `unknown` | `submitted_return` |
| `return_revision` | `original_unamended`, `amended`, `conflicting`, `unknown` | `original_unamended` |
| `registered_for_sa` | `yes`, `no`, `unknown` | `yes` |
| `acting_capacity` | `own_individual`, `representative_or_entity`, `unknown` | `own_individual` |
| `relevant_tax_region` | `england`, `wales`, `northern_ireland`, `other`, `unknown` | The three named regions |
| `residence` | `ordinary_uk`, `non_uk`, `dual_split_or_special`, `unknown` | `ordinary_uk`, independently of region |
| `ni_held_before_boundary` | `yes`, `no`, `unknown` | `yes`; no NI value collected |
| `hmrc_exemption_position` | `none_known`, `granted`, `pending`, `unclear` | `none_known`, not verified HMRC evidence |
| `prior_mtd_position` | `not_previously_enrolled_or_under_an_earlier_requirement`, `existing_or_previous_requirement`, `unknown` | First choice only |
| `all_sources_once`, `own_shares` | `yes`, `no`, `unknown` | `yes` for both |
| `vat_or_special_treatment`, `source_version_conflict` | `yes`, `no`, `unknown` | `no` for both |

`submitted_on` is an ISO date, strictly after the selected assessment year end
and on or before the earlier of server UTC as-of date and applicable mandatory
start. Start metadata comes from the existing accepted rule records, not a
second threshold/date policy. The form shows both assessment periods, applicable
start dates and actual NI/submission boundaries. It does not accept a client
clock, start date or threshold. No threshold comparison is implemented here.

There are eighteen distinct special-fact fields: each of `sa109`, `sa107`,
`averaging_care`, `minister_lloyds`, `bpa_mca`, `representative_exemption`, suffixed
with `_2024-25`, `_2025-26` or `_2026-27`. Each offers `yes`, `no`, `unknown` and
requires `no` for this simple subset. The form names each year and asks for
actual or relevant known/expected facts. No NI number, medical detail or reason
narrative is requested. A positive, missing or unknown answer means unsupported
here, never an exemption decision or automatic continuation into a later year.

The form has twelve optional source rows. Field names are
`source_<n>_<field>`, where `n` is 1–12 and field is:

| Row field | Exact meaning / accepted vocabulary |
|---|---|
| `kind` | `sole_trade`, `uk_property`, `foreign_property`, `unknown`; only first three numeric |
| `gross_income` | Own gross pounds before expenses; 1–10 integer digits and optional 1–2 decimal digits; no signs, commas, exponent, non-finite values or leading-zero ambiguity |
| `period_start`, `period_end` | ISO dates exactly covering the selected assessment year |
| `lifecycle` | `active_throughout_and_still_continuing`, `started_or_ceased`, `unknown`; only first numeric |
| `amount_basis` | `own_gross_before_expenses`, `whole_joint_or_net`, `special_or_uncertain`, `unknown`; only first numeric |

Missing amounts are unknown, not zero. Exact zero is admitted. Entirely blank
rows are unused; an explicitly confirmed empty complete inventory is zero.
Recognised rows numbered 13–99 make the request unsupported rather than being
silently truncated; other malformed row keys are 400. There may be at most one
combined UK-property and one combined foreign-property business. Equal amounts
in separate sole trades are not treated as duplicates. Explicit own-share and
complete/distinct-inventory declarations remain self-report, not ownership proof.
UUID row identities are server-created and request-local, never accepted from
the customer or exposed in the result. No excluded zero rows are fabricated.

## Derived completeness and presentation

The five issuer completeness booleans are not form fields:

- Residence support derives from own-individual capacity, supported region,
  ordinary residence, all eighteen special facts, SA registration, NI boundary
  confirmation and the simple none-known exemption position.
- Inventory support derives from all-sources-once/own-share declarations,
  resolved VAT/special-treatment and version facts, row bound, known kinds,
  present gross values, own-gross basis and property grouping.
- Timing support derives from completed assessment period, submitted/original
  return status, valid submission boundary and every active row's full period.
- Cessation support derives from no earlier/current requirement plus unchanged,
  still-continuing lifecycle for every active row.
- Annualisation-basis support means completed-year submitted actuals only;
  nothing is annualised or forecast.

Any failed support predicate yields the existing value-free **More information
needed** handle/rendered fragment, with fixed explanatory copy outside it.
Numeric output retains the accepted calm headline, source/business counts,
included categories, threshold, distance and actual start date. Both form and
result distinguish self-reported, unsaved planning from HMRC determination,
filing, annual tax, cash reserve and entitlement. Employment, dividends,
savings, gains and ordinary partnership profit remain visible exclusions.

Changing facts uses a fresh form and request. Source facts are not put in the
session, URL, logs or database. Existing no-store/Vary responses apply. This is
not a memory-erasure or hostile in-process-code guarantee, nor a claim about
browser history behaviour beyond the tested response headers.

## Synthetic verification and remaining work

`tests/test_mtd_manual_scope_journey.py`: **179 passed**. Tests parse the real
rendered form, follow real dashboard discovery, use actual session/CSRF requests
and inspect genuinely issued handles while executing the real renderer. Literal
money expectations cover zero and equality/one-penny boundaries for £50,000
(2024/25) and £30,000 (2025/26), with actual starts 2026-04-06 and 2027-04-06.
Every finite admission question's unsupported branch, all eighteen special-fact
questions, row facts, dates, unknown versus zero, source grouping, duplicate and
forged fields, malformed inputs, exact owner/auth/CSRF/production gates,
no-store, database/session/log non-retention and fresh-handle/source issuance
are exercised. Forbidden financial/provider reads are challenged on manual POST.
These are executable Flask tests, not human, visual or actual-browser acceptance.

Authorised S5A/B/D classification now records 46 always-registered routes, 55
with HICBC and 28 paid classifications. No runtime entitlement guard was wired.
Historical checkpoints and dirty-scope sentinels remain unchanged. The two S7A
SRC-16 live-v2 binding tests are expected to remain stale pending root's separate
accepted-source reconciliation. They must not be reported as passing here.

The affected matrix is **1,298 passed / 3 expected failures**, with no deselection:
the untouched S5D `test_candidate_is_confined_to_exact_three_owned_paths_and_base`
dirty-scope sentinel and S7A's
`test_exact_source_commit_hash_and_binding_register_is_not_substitutable` and
`test_paye_live_v2_preserves_distinct_historical_s5c_and_preview_blobs`.
The latter two compare the changed v2 source against the prior accepted PAYE
digest; historical blobs and the independent legacy-routes binding are intact.
The command was `/private/tmp/reserved-venv/bin/python -m pytest`
with `-o addopts='' -q` and these paths:
`tests/test_mtd_readiness.py`, `tests/test_mtd_scope_indication.py`,
`tests/test_mtd_scope_indication_presentation.py`,
`tests/test_mtd_approved_literal_audit.py`, `tests/test_paye*.py`,
`tests/test_dashboard.py`, `tests/test_hicbc*.py`,
`tests/test_internal_tax_boundary.py`, `tests/test_w8_progressive_assurance_s2.py`,
`tests/test_w10_paid_surface_inventory.py`,
`tests/test_w10_internal_route_reconciliation.py`,
`tests/test_w10_paid_access_guard.py`, `tests/test_w10_billing_threat_model.py`.
The separate new-journey command uses the same runtime/options with
`tests/test_mtd_manual_scope_journey.py`. No full-repository gate is claimed.

Exact frozen hashes accompany the candidate handoff. Independent review and
root's actual synthetic browser check remain
required before checkpoint. Production API/source verification, broader source
treatments, amendments, cessation and existing MTD continuation, current-year
annualisation, privacy/legal notices and production activation remain separate
unfinished work. This engineering-supported subset does not imply that other
circumstances are legally exempt or outside the programme. No wider MTD or
October denominator is closed.

Source basis is the unchanged Founder decision and the root-verified primary
guidance linked in `work/mtd-manual-journey-package-preparation.md`: HMRC's
[eligibility and start dates](https://www.gov.uk/guidance/find-out-if-and-when-you-need-to-use-making-tax-digital-for-income-tax),
[qualifying income](https://www.gov.uk/guidance/work-out-your-qualifying-income-for-making-tax-digital-for-income-tax),
[exemption guidance](https://www.gov.uk/guidance/find-out-if-you-can-get-an-exemption-from-making-tax-digital-for-income-tax)
and [source grouping](https://www.gov.uk/guidance/use-making-tax-digital-for-income-tax/add-or-cease-income-sources).
No new external research, provider call, credential, real customer data, storage
or policy has been introduced by this candidate.
