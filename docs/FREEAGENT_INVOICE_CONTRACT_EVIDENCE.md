# FreeAgent invoice-list / company / pagination contract evidence

Observation date: 1 September 2026.

This record captures only what the current official FreeAgent developer
documentation establishes about the read-only company read, invoice list and
pagination contract. It is the evidence base for
`reserved/providers/accounting/freeagent_invoice_contract.py`. No FreeAgent
account, credential, customer record or sandbox request was used; no provider
API call was made. Public documentation reads were the only external access.

## Official sources observed

- [FreeAgent API introduction](https://dev.freeagent.com/docs/introduction)
  — request/response formats, HTTP verbs, access levels, pagination, rate limits.
- [FreeAgent invoices](https://dev.freeagent.com/docs/invoices)
  — invoice and invoice-item attributes, list endpoint, response examples,
  filters and sort orders.
- [FreeAgent company](https://dev.freeagent.com/docs/company)
  — company attributes and `GET /v2/company` response example.
- [FreeAgent quick start](https://dev.freeagent.com/docs/quick_start)
  — the minimal sandbox company probe example.
- [FreeAgent versioning](https://dev.freeagent.com/docs/versioning)
  — `X-Api-Version` header behaviour.

All five pages were reachable and read on the observation date. The invoice,
company and introduction pages are the direct authority for the facts below;
quick start and versioning corroborate the company probe and the versioned
request shape.

## Transport and format facts (introduction)

Documented facts:

- All API access is over HTTPS from `api.freeagent.com`.
- JSON and XML response formats are supported; the JSON examples use
  `Accept: application/json` and `Content-Type: application/json`.
- Four HTTP verbs are used: `GET`, `POST`, `PUT`, `DELETE`.
- A `user-agent` must be specified.
- Access levels are numeric `0` (No Access) through `8` (Full). The invoice
  resource documents a minimum access level of "Estimates and Invoices"; the
  company resource documents "Time".

### Exact API-origin validation (enforced)

Because the introduction states that all API access is over HTTPS from
`api.freeagent.com`, this module enforces that statement on every FreeAgent
API resource identity it treats as meaningful:

- FreeAgent API resource identities (`company.url`, invoice `url`, `contact`,
  `project`, `property`, `bank_account`, `recurring_invoice`) must be absolute
  HTTPS URLs on exactly `api.freeagent.com`, with no credentials/userinfo,
  no fragment and no non-default port, and an appropriate `/v2/` resource path
  (`/v2/company`, `/v2/invoices/<id>`, `/v2/contacts/<id>`,
  `/v2/projects/<id>`, `/v2/properties/<id>`, `/v2/bank_accounts/<id>`,
  `/v2/recurring_invoices/<id>`).
- Pagination `Link` relations (`prev`, `next`, `first`, `last`) must use the
  exact HTTPS FreeAgent origin and the `/v2/invoices` path; their query
  parameters are preserved verbatim and the module never constructs a next
  URL.
- Cross-origin, plain-HTTP, credential-bearing, fragmented and malformed
  targets are rejected, including authorities with an explicit empty or
  non-numeric port. An explicit default `:443` remains valid.
- `payment_url` is documented as an online payment URL (PayPal, GoCardless,
  Stripe or Tyl) and may legitimately point outside `api.freeagent.com`; it is
  validated only as a safe absolute HTTPS URI (including valid explicit-port
  syntax) and is **not** forced onto the FreeAgent origin. Valid numeric ports
  are preserved.

## Pagination facts (introduction)

Documented facts, encoded exactly:

- Requests that return multiple items are paginated and default to **25 items
  per page**.
- A client selects a page with the `page` parameter.
- A client changes the page size with the `per_page` parameter, which is
  **limited to 100 items per page**.
- The pagination information is carried in the `Link` header with exactly the
  following relation values: `prev`, `next`, `first`, `last`.
- The `X-Total-Count` header carries the total number of entries that it is
  possible to paginate over.

Example documented in the source:

```
GET https://api.freeagent.com/v2/invoices?page=5&per_page=50
Link: <https://api.freeagent.com/v2/invoices?page=4&per_page=50>; rel="prev",
      <https://api.freeagent.com/v2/invoices?page=6&per_page=50>; rel="next",
      <https://api.freeagent.com/v2/invoices?page=1&per_page=50>; rel="first",
      <https://api.freeagent.com/v2/invoices?page=10&per_page=50>; rel="last"
X-Total-Count: 26
```

The documented rate limits are 120 user requests/minute, 3600 user
requests/hour and 15 token refreshes/minute, with a `429` response and
`Retry-After` on throttling. These are recorded here but are **not** part of
this invoice-contract module's validation surface (no HTTP client exists).

## Company read contract (`GET /v2/company`)

### Envelope

Documented fact: the success response has a single top-level `company` object.

```
{ "company": { ... } }
```

### Company attribute kinds (documented)

The company attribute table has **no** explicit "required" marker column, so
only the `company` envelope key is treated as a strictly required structural
element. Every field in the table below is validated against its documented
Kind (String, Date, Boolean, Array, Integer, URI, Timestamp) or its exact
documented enum where one exists.

| Attribute | Kind | Documented meaning / enum |
|---|---|---|
| `url` | URI | API endpoint for the authenticated company |
| `id` | Integer | ID of the company (see discrepancy below) |
| `name` | String | Company name |
| `subdomain` | String | Company subdomain |
| `type` | String (enum) | One of the 11 types below |
| `currency` | String | Base accounting currency |
| `mileage_units` | String (enum) | `miles` or `kilometers` |
| `company_start_date` | Date | Date business/company was started, `YYYY-MM-DD` |
| `trading_start_date` | Date | Date company commenced trading |
| `first_accounting_year_end` | Date | First annual accounts year end |
| `annual_accounting_periods` | Array | Periods covered by each annual accounts set |
| `freeagent_start_date` | Date | Start date used for FreeAgent accounts |
| `address1`/`address2`/`address3` | String | Address lines |
| `town` | String | Town |
| `region` | String | Region or State |
| `postcode` | String | Post / Zip Code |
| `country` | String | Country |
| `company_registration_number` | String | Company registration number |
| `contact_email` | String | Contact email address |
| `contact_phone` | String | Contact phone number |
| `website` | String | Website address |
| `business_type` | String | Free-text description of the business |
| `business_category` | String | Company's business category |
| `short_date_format` | String (enum) | `dd mmm yy`, `dd-mm-yyyy`, `mm/dd/yyyy`, `yyyy-mm-dd` |
| `sales_tax_name` | String | Name of current sales tax |
| `sales_tax_registration_number` | String | Current sales tax registration number |
| `sales_tax_effective_date` | Date | When current sales tax took/will take effect |
| `sales_tax_rates` | Array | Current sales tax rates |
| `sales_tax_is_value_added` | Boolean | `true` if VAT applies |
| `cis_enabled` / `cis_subcontractor` | Boolean | CIS for subcontractors enabled (aliases) |
| `cis_contractor` | Boolean | CIS for contractors enabled |
| `locked_attributes` | Array | List of attributes that cannot be modified |
| `vat_first_return_period_ends_on` | Date | When the first VAT return period ends |
| `initial_vat_basis` | String (enum) | `Invoice` or `Cash` |
| `initially_on_frs` | Boolean | `true` if on Flat Rate Scheme at VAT registration |
| `initial_vat_frs_type` | String | Flat Rate Scheme registered under |
| `sales_tax_deregistration_effective_date` | Date | Date of VAT de-registration |
| `second_sales_tax_name` | String | Name of current second sales tax |
| `second_sales_tax_rates` | Array | Current second sales tax rates |
| `second_sales_tax_is_compound` | Boolean | `true` if applied on top of main sales tax |
| `created_at` / `updated_at` | Timestamp | Company resource create/update (UTC) |

The `type` attribute is documented as one of exactly:

`UkLimitedCompany`, `UkLimitedLiabilityPartnership`, `UkPartnership`,
`UkSoleTrader`, `UkUnincorporatedLandlord`, `UsLimitedLiabilityCompany`,
`UsPartnership`, `UsSoleProprietor`, `UsCCorp`, `UsSCorp`, `UniversalCompany`.

### Company schema validation (enforced)

Every field listed above is validated by the schema layer against its
documented kind or exact enum. String fields reject non-string values, Date
fields reject non-`YYYY-MM-DD` strings, Boolean fields reject non-booleans,
Array fields reject non-arrays, and the enum fields (`type`, `mileage_units`,
`short_date_format`, `initial_vat_basis`) reject values outside their exact
documented sets. Timestamps are validated only as non-empty strings, because
the exact timestamp wire grammar is not formally specified.

### Documented-fact vs inference notes (truthful labelling)

- The company attribute table has **no** explicit "required" marker column.
  Only the `company` envelope key is a documented structural requirement.
- `type` and `currency` are required by this module, but this is **not** a
  documented "required" fact: it is a conservative, fail-closed FA-S1
  inference from their consistent presence in both documented examples and
  from the fact that an invoice amount cannot be interpreted without a
  currency. Tests and this evidence record it as an inference, not an official
  required-field fact.
- The quick-start and company-page examples contain `type`, `currency`,
  `mileage_units`, `company_start_date`, `freeagent_start_date`,
  `first_accounting_year_end`, `annual_accounting_periods`,
  `company_registration_number`, `sales_tax_registration_number`,
  `cis_enabled`, `cis_subcontractor` and `cis_contractor`, plus
  `sales_tax_registration_status` (example-only).

### Company evidence discrepancies (recorded, not silently resolved)

1. `id` is documented with Kind `Integer`, yet the JSON example shows
   `"id":"12345"` (a JSON string). This module accepts either an integer or a
   non-empty numeric string for `id` and does **not** assert a single wire type.
2. `sales_tax_registration_status` appears in both the company-page and
   quick-start examples but is **not** present in the company attribute table.
   It is recorded as an additive/undocumented field for review and is not
   given any semantic meaning.

## Invoice list contract (`GET /v2/invoices`)

### Envelope

Documented fact: the list success response is:

```
{ "invoices": [ { ... }, ... ] }
```

### Invoice attribute kinds (documented)

The invoice attribute table has an explicit `Required` column. The following
are marked required (`✔`):

- `contact` — URI — "The contact being invoiced".
- `dated_on` — Date — "Date of invoice in YYYY-MM-DD format".
- `payment_terms_in_days` — Integer — "Set to zero to display 'Due on Receipt'
  on the invoice".

The following is conditional (`?`):

- `property` — URI — "The property pertaining to this invoice. Only accepted
  and required for companies with type UkUnincorporatedLandlord."

All other invoice attributes are optional in the attribute table. Every
attribute is validated against its documented kind or exact documented enum:

**URI family** (all FreeAgent API identities are origin-validated; `payment_url`
is validated only as a safe external HTTPS URI):

- `url` — URI — "The unique identifier for the invoice" (`/v2/invoices/<id>`).
- `contact` — URI — `/v2/contacts/<id>`.
- `project` — URI — `/v2/projects/<id>`.
- `property` — URI — `/v2/properties/<id>` (conditional, see below).
- `bank_account` — URI — `/v2/bank_accounts/<id>`.
- `recurring_invoice` — URI — `/v2/recurring_invoices/<id>`.
- `payment_url` — URI — online payment URL; may point outside the API origin.

**String family** (non-empty strings): `long_status`, `reference`, `currency`,
`comments`, `contact_name`, `client_contact_name`, `payment_terms`,
`po_reference`, `place_of_supply`.

**Enum family** (exact documented sets; nullable where documented):

- `status` — exactly `Draft`, `Scheduled To Email`, `Open`, `Zero Value`,
  `Overdue`, `Paid`, `Overpaid`, `Refunded`, `Written-off`,
  `Part written-off`.
- `ec_status` — exactly `UK/Non-EC`, `EC Goods`, `EC Services`,
  `Reverse Charge`, `EC VAT MOSS` (with dated restrictions, see below).
- `include_timeslips` — `null` or `billed_grouped_by_single_timeslip`,
  `billed_grouped_by_timeslip`, `billed_grouped_by_timeslip_task`,
  `billed_grouped_by_timeslip_date`.
- `include_expenses` — `null` or `billed_grouped_by_single_expense`,
  `billed_grouped_by_expense`.
- `include_estimates` — `null` or `billed_grouped_by_single_estimate`,
  `billed_grouped_by_estimate`.
- `cis_rate` — `null` or a non-empty CIS band name (documented as
  `String | null`).

**Date family** (non-empty `YYYY-MM-DD` strings): `dated_on`, `due_on`,
`paid_on`, `written_off_date`.

**Integer family**: `payment_terms_in_days`.

**Boolean family**: `omit_header`, `show_project_name`,
`always_show_bic_and_iban`, `send_new_invoice_emails`,
`send_reminder_emails`, `send_thank_you_emails`, `involves_sales_tax`,
`is_interim_uk_vat`.

**Array family**: `invoice_items`.

**Hash family**: `payment_methods` — an object whose documented method keys
(`paypal`, `gocardless_preauth`, `gocardless_instant_bank_pay`, `stripe`,
`tyl`) are booleans when present; unknown additive method keys are preserved
without being given semantics.

**Timestamp family** (`created_at`, `updated_at`): validated only as non-empty
strings, because the exact timestamp wire grammar is not formally specified.

**Decimal family** (validated as decimal-number strings, including string zero):
`net_value`, `sales_tax_value`, `second_sales_tax_value`, `total_value`,
`paid_value`, `due_value`, `exchange_rate`, `discount_percent`,
`cis_deduction_rate`, `cis_deduction`, `cis_deduction_suffered`.

### Invoice schema validation (enforced)

Every field above is validated by the schema layer. Nullable enum fields
(`include_timeslips`, `include_expenses`, `include_estimates`, `cis_rate`)
accept `null` only where the documentation explicitly allows it; all other
documented fields reject `null` rather than silently accepting an
incompatible shape. `payment_methods` checks that any present documented
method key is a boolean.

### Conditional constraints (documented, not adjudicated)

- `ec_status`: the documentation states that `EC Goods` and `EC Services` are
  no longer valid when the invoice is dated 1/1/2021 or later and the company
  is based in Great Britain (but not Northern Ireland), and that
  `Reverse Charge` is only valid when the invoice is dated 1/1/2021 or later.
  These are dated, jurisdiction-dependent restrictions that this isolated
  response validator cannot adjudicate without trusted company context, so
  they are recorded as documented conditional constraints rather than enforced.
- `property`: documented as "Only accepted and required for companies with
  type UkUnincorporatedLandlord." This is a landlord-only rule that likewise
  depends on trusted company type, so it is recorded, not enforced here.

### Documented-fact vs inference notes (truthful labelling)

- `url` is documented as "The unique identifier for the invoice", but it is
  **not** marked required in the attribute table's `Required` column. This
  module requires `url` on every list item as a conservative, fail-closed
  FA-S1 inference (duplicate/missing identity detection depends on it), and
  labels it as an inference, not an official required-field fact.

### Invoice amount fields (documented semantics, encoded verbatim)

These are all Kind `Decimal`. Their documented meanings are preserved exactly
and are **not** mapped to canonical tax concepts:

| Field | Documented meaning |
|---|---|
| `net_value` | Net value |
| `sales_tax_value` | Total value of sales tax |
| `second_sales_tax_value` | [Universal accounts only] Total value of second sales tax |
| `total_value` | Gross value |
| `paid_value` | Amount paid off so far |
| `due_value` | Amount yet to be paid |
| `exchange_rate` | Rate at which invoice amount is converted into the company's native currency |
| `discount_percent` | The discount applied across the whole invoice |
| `cis_deduction_rate` | Percentage of CIS deduction for the `cis_rate` set |
| `cis_deduction` | Total CIS deduction for this invoice, in its currency |
| `cis_deduction_suffered` | CIS deduction already paid for this invoice, in its currency |

The provider calls this `sales_tax_value`, not `vat_value`. This module retains
the provider's `sales_tax_*` vocabulary and does not assert that it is
canonically equivalent to a VAT/tax figure. `paid_value` and `due_value` are
retained as "amount paid off so far" and "amount yet to be paid" respectively;
no further settlement semantics are invented.

### JSON wire representation (documented examples)

The documented JSON examples are consistent about scalar representation and
are treated as the wire contract:

- Integer fields are JSON numbers: `"payment_terms_in_days": 30`.
- Boolean fields are JSON booleans: `"omit_header": false`.
- Decimal/amount fields are JSON strings: `"total_value": "200.0"`,
  `"net_value": "0.0"`, `"exchange_rate": "1.0"`.
- Date fields are JSON strings: `"dated_on": "2011-08-29"`.
- Timestamp fields are JSON strings: `"created_at": "2011-08-29T00:00:00Z"`.
- URI and String fields are JSON strings.

### List filters and sort orders (recorded; not a validation surface here)

Documented facts, retained for the later adapter but **not** encoded in this
network-inert module:

- `view` filter values include `all` (default), `recent_open_or_overdue`,
  `open`, `overdue`, `open_or_overdue`, `draft`, `paid`,
  `scheduled_to_email`, `thank_you_emails`, `reminder_emails`, `last_N_months`.
- `updated_since` date filter.
- `sort` orders `created_at` (default) and `updated_at`; prefix with `-` for
  descending.
- `nested_invoice_items=true` nests invoice items inside the list.
- `contact` and `project` URI filters.

## What this module deliberately does not encode

- No HTTP client, token, credential, persistence, adapter-enablement or
  canonical tax decision.
- No mapping of `sales_tax_value` to canonical `tax_amount`, or of `paid_value`
  / `due_value` to settlement/outstanding semantics beyond their documented
  wording.
- No assumed timestamp sub-second format (the example shows seconds with `Z`;
  the attribute table says only "Timestamp (UTC)").
- No page-URL construction: the documented guidance is to follow `Link`
  relations, never to build the next URL by assumption.
- No company `id` wire-type assertion (see discrepancy above).
- No cross-field adjudication of the dated `ec_status` restrictions or the
  landlord-only `property` rule, which need trusted company jurisdiction/type;
  these are recorded as documented conditional constraints only.

## Evidence gaps still open (do not silently fill)

- The official pages do not document a complete error response schema for the
  company or invoice endpoints.
- Exact timestamp wire format is illustrated but not formally specified;
  timestamps are therefore validated only as non-empty strings.
- `sales_tax_registration_status` is present in examples but absent from the
  company attribute table; it is preserved as an unknown additive field.
- The `id` attribute is declared `Integer` but illustrated as a JSON string;
  the validator accepts either and flags no single wire type.
- The dated `ec_status` restrictions and the landlord-only `property` rule are
  documented conditional constraints that a network-inert isolated response
  validator cannot adjudicate without trusted company context; they are
  recorded, not enforced.
- Null/omitted semantics for the optional amount fields are not stated
  explicitly; this module therefore preserves absent, explicit-null and zero
  states rather than collapsing any of them.
