# HICBC manual annual-source runtime — review candidate

## Authority and disposition

Base `5d91ae0c83bf696cb650d90daa8d25417e466157`; branch
`astra/hicbc-annual-source-runtime`. Governing Founder Decisions SHA-256:
`78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`.
The owning task authorised this named internal annual-engine caller and the
13-path package. No applicable AGENTS instructions were found. This is an
implementation candidate for a different independent reviewer, not acceptance
by its author, launch assurance, or activation.

## Actual request path and controls

POST `/v2/hicbc/annual-preview` is registered only with the existing HICBC
blueprint. After the existing `require_auth` session guard, it independently
checks the current HICBC gate and `HICBC_ANNUAL_PREVIEW_ENABLED`. The new switch
is disabled unless its environment value is exactly `1`; it is not inferred
from another flag. The existing authoritative production detector denies the
handler with 404 when either FLASK_ENV identifies production or a live Clerk
publishable-key prefix is configured, regardless of both switches. These
checks precede the new annual source or database read. No environment values,
credentials or live flags are changed by this package.

Global Flask-WTF CSRF protection is not exempted: missing/invalid tokens fail
before handler execution, and an unauthenticated request with valid CSRF is
redirected by the existing authentication guard. Therefore not every denied
request has a 404 response: CSRF/authentication can reject first. The global
`/v2/` response policy preserves no-store and Vary: Cookie for results and errors.

The handler accepts only a bounded JSON body (at most 8192 bytes), rejects query
parameters, duplicate keys and malformed/deep JSON, and validates the exact
canonical schema. Error responses use the existing indeterminate HICBC view,
not exception text or reflected request facts. It passes admitted first-person
facts to the named source service, which calls the existing annual engine once
and returns only engine-derived own ANI internally. The handler then reuses
the existing responsibility/evidence/customer-view logic. It publishes neither
the annual result nor ANI, personal annual tax, evidence IDs, reserve/payment
recommendations or a new public tax-result interface.

## Explicit manual schema

Every listed key is required; unknown, null, absent or additional keys fail
closed rather than becoming zero. Monetary values must be canonical,
non-negative decimal strings with up to eight integer digits and two decimal
places, e.g. `0`, `70000` or `70000.00`. The size limit is a bounded input
constraint, not a tax rule. JSON numbers, booleans, exponents, NaN/Infinity,
negative or over-precise monetary values are rejected.

- `schema_version`: `hicbc-manual-annual/1`.
- `tax_year`: the configured year and the current annual engine's supported
  `2026/27` boundary must both match.
- `country`: England, Wales or Northern Ireland, explicitly.
- `full_tax_year_including_known_future`: literal true, covering all required
  groups and known future amounts; YTD/partial facts are not annualised here.
- `employment_basis`: `all_jobs_taxable_after_salary_sacrifice_and_net_pay`.
  `employment_income` is the aggregate full-year taxable employment amount,
  already reflecting those arrangements; this service does not subtract them
  again. `gross_ras_pension` is separately stated gross relief-at-source
  pension. Ambiguous gross/net/pension treatment is rejected.
- `uk_resident`: literal true for this bounded source.
- `other_ani_adjustments`: `none`. Other adjustments/reliefs, including an
  unresolved loss-relief or Gift Aid position, require another supported
  evidence path; this service does not invent their treatment.
- `employment_income`, `sole_trade_profit`, `savings_interest`, `dividends`.
- `uk_property_receipts`, `uk_property_allowable_expenses`,
  `brought_forward_uk_property_loss` for the person's own property share.
- `foreign_property_gross_receipts`, `foreign_property_allowable_expenses`.
- `gross_ras_pension`, `residential_finance_costs`, `foreign_tax_paid`.

The residential-finance field means individual residential-landlord costs;
other finance/ownership cases are not represented by this schema. Applicable
amounts must be explicitly supplied; irrelevant groups must explicitly be zero.
Unsupported foreign losses/residence affecting ANI fail closed. Existing
residential-finance or foreign-tax-credit limitations affect annual tax totals,
not this own-ANI operand, and are not relabelled as resolved. Incomplete BPA,
PAYE reconciliation and student-loan total limitations likewise are not claimed
to be solved. No annual tax total is returned. Caller ANI, HICBC, trust/current/
admitted flags, aliases, owner/business IDs and permission state are rejected.

This is fresh first-person manual estimate input, not independently verified
payroll or prior-return evidence. It is not retained, and it does not create
provider ingestion or source-priority/reconciliation policy. It does not
replace a complete customer-facing acquisition/confirmation UI.

## Owner/year consistency and linked-account refusal

The new narrow database context checks the authenticated owner exists, reads
only that owner's estimate for the configured tax year and checks for any
active link in that year. BEGIN IMMEDIATE serialises these reads and result
construction with estimate writes, revocation and relinking. It writes no
rows and reads no linked profile/financial operands. The short transaction
closes before response delivery; the guarantee is linearised result
construction, not cancellation of an already completed response.

Any active link refuses this manual preview with 409 and the existing
indeterminate view, regardless of permission, notice version, partial evidence
or supplied own-income scenario. It does not fall back to a determinate manual
estimate while linked. This conservative boundary was explicitly confirmed by
the owning task after identifying that varying fresh own-income facts against
linked operands would create a probing surface. It invents no rate-limit,
privacy or legal policy. The linked annual-source/anti-probing engineering
remains unresolved.

After revocation commits, a subsequent request may use separately supported
manual evidence; after relinking commits it must refuse again. Existing linked
routes remain unchanged: consent is not completeness, profile-derived linked
evidence remains partial/unconfirmed, manual/linked conflicts retain their
existing uncertainty, and old permission cannot revive across relinking.
The new source uses no legacy own-profile total as full annual ANI.

## Verification and boundaries

Author-run tests use synthetic users and temporary SQLite databases with actual
Flask requests and genuine Flask-WTF tokens. They cover the two switches and
both production signals, CSRF/auth distinction, complete mixed facts, exact
£70,000 engine ANI and £703 own HICBC, every missing schema key, malformed/
unsupported/forged inputs, wrong configured year, owner/year isolation,
no-store/privacy, whole-database nonmutation, manual range/stale/partial states,
active-link non-probing, revocation/relink, and real requests racing link changes.

The mixed literal source is £60,000 employment + £5,000 trade + £1,000 interest
+ £1,000 dividends + (£10,000 UK receipts − £4,000 expenses − £1,000 carried
loss) + (£3,000 foreign receipts − £1,000 expenses) − £4,000 gross RAS = £70,000.
The £703 charge for £1,406.60 Child Benefit is the already settled HICBC fixture;
no statutory formula or independent tax rule is added by the source adapter.

The internal-boundary test has one exact-file exception with import/call/result
access allowlists and hostile alias/import/exposure mutations. No directory-
wide engine exemption is created. S5A records 53 routes with HICBC enabled,
including the independently disabled preview; the paid class/kernel inventory
now has 26 endpoints. This is classification only: the paid kernel remains
route-less and runtime entitlement wiring remains absent. Historical S5A/S5B/
S5D source identities stay historical; only applicable live bindings change.

No full canonical gate was rerun. The October decision remains not ready and
all 18 blockers remain unclosed. Production activation, privacy/retention/legal
review, actual customer comprehension, broader annual acquisition, linked annual
source, annual/reserve/payment integration, durable owner-bound positions,
provider/target evidence and runtime paid access remain separate gates.

Author-run verification uses `/private/tmp/reserved-venv/bin/python`:

- New runtime suite: 74 cases (real-request and boundary fixtures).
- Additional existing HICBC partner/integration, annual arithmetic and accepted
  annual/cash synthetic journey suites: 188 passed.
- The requested wider matrix includes HICBC activation/privacy/consent/lifecycle,
  internal-tax boundary, S5A/S5B/S5D, Q1/Q2, S2C, billing threat model, W10 map
  and internal route hardening. Its three historical dirty-worktree ownership
  sentinels reject this unrelated package's 13 paths. These failures are not
  product behavior failures and were not suppressed or edited out of scope:
  `test_candidate_is_confined_to_three_new_non_colliding_paths`,
  `test_candidate_is_confined_to_the_authorised_map_and_dedicated_test`, and
  `test_candidate_changes_only_authorised_route_and_test_paths`.

Exact final counts and file/diff identities are delivered with the frozen
candidate, including those failures; none is rounded up to a canonical pass.
