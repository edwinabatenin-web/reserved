# Reserved Yapily provisional contract evidence matrix

Observation date: **1 September 2026**. Status: **documentation-only candidate;
unsigned agreement; Rory legal review outstanding**.

This matrix now distinguishes three evidence classes rather than combining them:

1. **Unsigned draft order form and service terms** — `Juro | App.pdf`, 74 pages,
   captured 25 August 2026, SHA-256
   `da93dad15afd14b9ea77961a17a4c93efbcbcbf74dbc86bc50961068bcf5affc`.
2. **Provider commercial/technical correspondence** — Cristian Gheorghita's
   14 August 2026 email thread, SHA-256
   `4cd351713c2fbd049705fad1451d47185828c89b4c429d72fa41c71b81cdb47b`.
3. **Current public official technical documentation** — the linked Yapily
   pages observed on 1 September 2026.

The draft is populated but unsigned: the signature timestamps and Customer
signatory remain empty. It is therefore evidence of proposed scope, not an
executed entitlement. Provider correspondence is evidence of a representation
or offer, not incorporated contractual wording. Public documentation describes
available technology, not Reserved's entitlement, production or sandbox
behaviour, institution-specific capability, or implementation assurance.

## Recovered draft scope and material delta

| Topic | Draft order form | Provider correspondence | Provisional engineering consequence |
|---|---|---|---|
| Customer / term / territory | Whip Smart Technologies Ltd; UK; billing start 1 September 2026; 24-month initial term; 12-month renewals; no Sub-Clients. | Earlier email described a 24-month minimum and possible later European expansion. | Treat UK/no-Sub-Clients as the provisional design boundary. Do not encode an effective contract date while unsigned. |
| Selected products | Yapily API and **Yapily Data**, expressly including Get Accounts and Get Transactions; UK Yapily Connect licence; Implementation Services; Hosted Pages; Standard support. EU licence is not selected. | Data API access was offered. | A disabled-by-default, non-production AIS/Hosted Consent contract slice may proceed. Live calls, credentials and production activation remain gated. |
| Payments / PIS / VRP | **Yapily Payments is not selected in the order form.** Generic annex definitions and clauses mentioning single, bulk and VRP describe optional services only where selected or permitted by the Order Form. | Email offered Payments access and stated Reserved's same-owner, same- or different-bank use case matched sweeping VRP criteria. | Do not treat the draft as PIS/VRP entitlement. Provider-neutral disabled interfaces and fixtures may proceed; Yapily-specific PIS/VRP wiring remains gated on an amended order form or explicit written contractual confirmation. |
| Commercials | GBP; £750 total monthly fee, comprising £250 Connect licence plus £500 Yapily Data; 500 consents included; £0.45 per consent above 500; £4,500 deposit; Hosted Pages and implementation fee waived. | Earlier offer stated £750 Data, £500 Payments, six-month deposit over monthly fees, £1,000 implementation and £250 European licence. | Record the mismatch for commercial/legal review. Never encode these figures into runtime behaviour or infer Payments entitlement from the email. |
| Regulatory/user journey | Customer stated not regulated to provide UK AIS; Yapily Connect UK selected. Connect terms require End User Terms, clear redirection/disclosure, applicable consent controls and current user-journey guidance. | Email said no regulatory application was needed for the discussed dashboard use case. | Treat the regulatory conclusion as provisional and subject to Rory/provider confirmation. Implement fail-closed consent/user-journey contracts only; make no customer-facing regulatory representation. |

The order form controls over generic annex language if the draft is later
executed in this form. A generic annex reference to Payments or VRP is not a
selected service. This distinction is a hard boundary for every package.

## Six-slice finite completion denominator

The corrected pre-flight denominator is exactly six adjudication slices:
**(1) AIS, (2) Single Payment/PIS, (3) sweeping VRP, (4) sandbox, (5) webhooks,
and (6) cross-cutting custody/ownership**. A slice is complete only when its
contract-specific gates and evidence are resolved; public observations merely
seed that adjudication. Do not add an implied seventh provider-code slice or
claim percentage completion from this evidence capture.

## Evidence matrix

| Slice | Public official observation | What remains unresolved for Reserved |
|---|---|---|
| AIS / Hosted Consent Pages | The unsigned draft selects Yapily Data, Get Accounts, Get Transactions, UK Yapily Connect and Hosted Pages. [`POST https://api.yapily.com/hosted/consent-requests`](https://docs.yapily.com/api-reference/hosted-consent-pages/create-hosted-consent-request) uses HTTP Basic Authentication with Application ID and Application Secret. `redirectUrl` and `institutionIdentifiers.institutionCountryCode` are required; either `userId` or `applicationUserId` is required. An account request carries explicit feature scope, expiry, and transaction range. `oneTimeToken` can request a one-time token instead of returning a consent token at the redirect URL. [`GET /hosted/consent-requests/{consentRequestId}`](https://docs.yapily.com/api-reference/hosted-consent-pages/get-hosted-consent-request) exposes hosted-request status/consent association. | Execution/legal status of the draft; exact enabled sandbox/production schemas and product flags; target-institution/account coverage; credential, token and consent custody; callback handling; provider onboarding; and retained sandbox proof. |
| Single Payment / PIS | The draft order form does **not** select Yapily Payments. Cristian's email offered Payments access, while the [direct single-payment flow](https://docs.yapily.com/payments/tutorial-single-payment) and [`POST /payments`](https://docs.yapily.com/api-reference/payments/create-payment) document public technical behaviour. | An amended order form or explicit written contractual confirmation of the exact Payments product, fees and UK Connect PIS scope; direct versus hosted route; exact schemas and exceptional/terminal behaviour; status reconciliation; idempotency ownership; institution/payment coverage; same-owner controls; and sandbox proof. Public docs and correspondence do not create entitlement. |
| Sweeping VRP | The draft order form does **not** select Yapily Payments or expressly permit the VRP endpoint. Cristian's email states the discussed same-owner current-account-to-savings use case, including different banks, matched sweeping VRP criteria. Public docs describe Sweeping VRP as transfers between accounts belonging to the same person/business and show mandate limits, consent, execution and status flows. | An amended order form or explicit written contractual confirmation of sweeping VRP access; target-bank/account coverage; exact mandate/payment/status/error schemas; funds-confirmation semantics; same-owner evidence and enforcement; idempotency; revocation/expiry/exception handling; commercials; and sandbox proof. Generic annex references apply only where the Order Form permits the service. |
| Sandbox | [Public test guidance](https://docs.yapily.com/resources/sandbox/test-cases) identifies `modelo-sandbox`, data/payment test capabilities, and a stated short AIS-consent expiry in the test environment. | This is synthetic evidence only, not production behaviour. Required sandbox applications/accounts, credentials, enabled products, representative institutions, exact test cases, retained results, and independent review remain unresolved. |
| Webhooks | [Public webhook guidance](https://docs.yapily.com/tools-and-services/webhooks/get-started) describes Private Beta access. Registration returns a secret that must be stored for signature verification. Events use HMAC-SHA256; the raw body must be validated before structural transformation using `webhook-signature` and, where applicable, the rotation header. A secure public HTTPS endpoint and timely success response are required. | Contracted webhook entitlement, registration/rotation procedure, exact event catalogue and retry/delivery semantics, endpoint operations, secret custody, replay controls, failure handling, monitoring, and sandbox evidence. |
| Cross-cutting custody / ownership | **Public evidence supplies no Reserved-specific assurance for this slice.** AIS authorisation, payment authorisation, mandates, notifications, and provider credentials are distinct security and lifecycle objects. | Credentials and secret/token/consent custody; encryption, access, rotation, revocation and deletion; customer/account binding; same-owner evidence mechanism and fail-closed enforcement; audit trail; privacy, security and operational approval; incident response; retention; legal/regulatory review; and independent assurance. |

## Non-negotiable boundaries

- AIS consent must **never** be treated as payment consent.
- A redirect callback is a browser return in an authorisation journey; an
  authenticated webhook is a server-to-server event whose authenticity must be
  verified. Neither is evidence for the other's contract or security model.
- The repository's older `account-auth-requests` AIS flow, query-parameter
  assumptions, 90-day lifetime, mock statuses, fixture schemas, and
  callback/webhook assumptions remain unverified and **must not be wired**.
- Founder policy is invariant: Single Payment/PIS is the primary journey;
  sweeping VRP is explicit opt-in and never default, preselected, or implied;
  no money moves without customer authorisation and the bank's required
  authentication/consent; same-owner controls are required; Reserved does not
  hold customer funds.

## Contract-specific gates

Before any enablement, obtain and independently adjudicate: entitlement and
product selection; current contracted documentation; institution, account and
payment coverage; exact request/response/error/status/event schemas; the
same-owner evidence mechanism; commercials; legal and regulatory approval;
credential, consent, token, webhook-secret and idempotency custody/ownership;
sandbox applications/accounts and representative proof; privacy, security and
operational controls; and independent contract, implementation and evidence
review.

## Contract-delta register for Rory/provider confirmation

| Assumption | Current support | Classification | Technical response if changed |
|---|---|---|---|
| UK AIS through Yapily Connect for Data/Get Accounts/Get Transactions | Selected in unsigned draft; supported by public docs | Provisional; implementation-impacting | Adjust only the AIS product/consent boundary and focused tests. |
| Hosted Pages for AIS | Selected and fee-waived in unsigned draft; public flow documented | Provisional; implementation-impacting | Keep adapter disabled until exact enabled flow/schema is confirmed; change only hosted-consent boundary if needed. |
| No Sub-Clients | Expressly stated in draft | Provisional; production-gating and architecture boundary | Do not add sub-application/reseller behaviour. Re-review tenancy and disclosure boundaries if changed. |
| UK-only territory | Expressly stated in draft; EU licence unselected | Provisional; production-gating | Fail closed outside GB; do not add EU flows until varied. |
| PIS/Payments entitlement | Email offer and public docs only; not selected in draft order form | **Unresolved**; implementation-impacting | Keep all Yapily-specific PIS wiring absent/disabled until written contractual confirmation. |
| Sweeping VRP entitlement and use-case eligibility | Eligibility confirmed by email; generic draft annex and public docs; not selected in order form | **Unresolved**; implementation-impacting | Preserve provider-neutral opt-in contracts only; no Yapily VRP calls or activation. |
| End User Terms and Yapily Connect disclosure/user journey | Draft Connect terms; referenced terms/guidance may change over time | Provisional; implementation-impacting | Snapshot and legally review the operative versions before customer activation; keep disclosures feature-gated. |
| Data use, retention/deletion and onward processing | Draft incorporates an online Data Processing Agreement “from time to time”; exact operative DPA and lawful-retention design are not adjudicated here | **Unresolved**; implementation-impacting | Minimise captured fields; keep raw-data retention/export/deletion decisions gated; do not infer rights from API availability. |
| Credential/consent/token security | Draft requires confidential, secure handling and prompt revocation/incident notice; technical custody design unassured | Provisional; production-gating | No real credentials in source/tests; require approved encrypted custody, rotation, revocation and incident controls before network use. |
| Regulatory responsibility | Draft allocates customer application, consent and user-interest duties while Yapily Connect provides selected regulated service; earlier email says no application needed for discussed use case | Provisional; legal-review required | Make no regulatory claim in product copy; gate activation and user journey on Rory/provider confirmation. |
| SLA/support | Standard support selected; target first-reply times are objectives, not resolution guarantees | Production-gating only unless resilience design assumes more | Keep timeouts, retries, degraded states and manual fallback independent of SLA. |
| Commercial values | Draft and earlier email materially differ | Legal/commercial unresolved; not runtime | Never encode prices, deposit, term or liability into product behaviour. |

Rory's delta review should answer only whether his comments alter the permitted
data scope, payment/VRP entitlement, consent/user journey, data use/retention,
regulatory allocation, territory, Sub-Client boundary, security obligations, or
activation conditions. Unaffected engineering should not be reopened.

## Next-package decision table

| Potential next engineering package | Decision | Reason |
|---|---|---|
| Contract/product adjudication and gap closure | **READY** | Primary draft and correspondence are now identified and separated; Rory/provider deltas remain. |
| Provider-neutral interfaces and threat-model design, with no Yapily wiring | **CONDITIONALLY READY** | Only if it preserves AIS/payment separation, PIS-first and VRP-opt-in policy, portability, fail-closed same-owner controls, and marks provider schemas unresolved. |
| AIS Hosted Consent request contract, disabled by absence and without live calls or provider-response handling | **COMPLETE AS PROVISIONAL Y1 CANDIDATE** | The unsigned draft expressly selects Data/AIS and Hosted Pages, and current official docs provide a bounded request shape. Independent review deliberately deferred hosted URLs, tokens, response parsing, browser handoff, credentials, network execution and activation to the gated Y2 boundary. |
| AIS sandbox network execution | **BLOCKED** | Requires approved sandbox application/access, credentials, exact enabled product confirmation, safe credential custody, retained evidence and independent review. |
| Yapily-specific Single Payment/PIS implementation | **BLOCKED** | Payments is offered in correspondence but not selected in the unsigned order form. Contractual product choice, exact direct/hosted contract, payment/status/error behaviour, same-owner mechanism, commercials and sandbox proof remain unresolved. |
| Yapily-specific Sweeping VRP implementation | **BLOCKED** | The provider confirmed use-case eligibility by email, but the unsigned order form does not select Payments/VRP. Exact entitlement, mandate/payment contract, bank/account coverage, same-owner evidence, commercials and sandbox proof remain unresolved; VRP must remain opt-in. |
| Webhook endpoint or callback/webhook rewiring | **BLOCKED** | Private Beta entitlement and exact registration, event, rotation, retry and operational contracts are absent; redirect and webhook semantics cannot be conflated. |
| Synthetic sandbox execution package | **CONDITIONALLY READY** | Ready only after sandbox accounts, credentials, products, exact contracted schemas and approved test scope exist; results cannot prove production behaviour. |
| Production enablement or launch assurance | **BLOCKED** | Public evidence does not prove Reserved's entitlement, target-institution behaviour, operational safety or independent assurance. |

## Conclusion

The combined evidence safely supports one provisional, disabled-by-default AIS
Hosted Consent **contract-model** slice with no live calls or credentials. It
does not prove executed entitlement, institution-specific behaviour, sandbox
success, production behaviour, PIS/VRP access, or launch readiness. Keep
provider networking disabled until every applicable gate is evidenced and
independently reviewed.
