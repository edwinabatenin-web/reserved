# External dependencies

Founder update, 12 August 2026: sandbox applications and environment-scoped IDs/secrets have been created for HMRC, Yapily, FreeAgent, Xero and QuickBooks and stored in Replit Secrets. No secret values were provided to or recorded in this working copy. The actions below now concern configuration/scope verification and synthetic end-to-end use, not initial credential creation.

Implementation gate, 13 August 2026: configuration is not treated as integration readiness. All five provider definitions explicitly remain `configured_not_implemented` and network-disabled until provider-specific adapters and contracted flows are implemented, reviewed and deliberately enabled in code.

Accounting sync boundary, 13 August 2026: a provider-neutral collector now detects pagination loops, duplicates and backwards watermarks. Each provider adapter must still translate its own officially documented pagination response into that contract; no common endpoint or cursor behaviour is assumed.

Import completeness boundary, 13 August 2026: Reserved records payload-free
scope, count, terminal-page, watermark and redacted-evidence metadata. Where a
provider has no official independent total-count facility, a terminated import
is `unverified` rather than `complete`; adapters must not invent totals.

Provider schema boundary, 13 August 2026: reviewed adapter schemas now have a
network-inert drift contract. Missing or incompatible required fields quarantine
records; unknown additive fields are flagged for review. Provider-specific
field mappings still require official-schema and sandbox evidence and cannot be
invented by the common layer.

| Dependency | Action required | Owner | When required | What it blocks | Official process/documentation |
|---|---|---|---|---|---|
| HMRC PAYE sandbox | Confirm the Reserved application is subscribed to **Individual PAYE Test Support 2.0 beta** (`paye-des-stub`) and capture its exact fixture endpoint/payload contract; retain all secrets outside source control | Founder / engineering | Before stateful Individual Employment 1.2, Individual Income 1.2 or Individual Tax 1.1 sandbox tests | Synthetic employment/income/tax fixture setup | https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/paye-des-stub/2.0 |
| HMRC MTD sandbox | Retain **Self Assessment Test Support (MTD) 1.0 beta** only for deleting developer-supplied stateful MTD Self Assessment sandbox data where required; do not use it to seed PAYE evidence | Engineering | Before an MTD stateful journey needs controlled cleanup | Repeatable cleanup of developer-supplied MTD sandbox state | https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/mtd-sa-test-support-api/1.0 |
| HMRC | Complete production application and approval | Founder / engineering | Before any live HMRC pilot | Live user-authorised HMRC data | https://developer.service.hmrc.gov.uk/api-documentation/docs/using-the-hub |
| Yapily | Confirm AIS sandbox application and commercial/licensing route; do not enable PIS yet | Founder | Before sandbox end-to-end AIS test | Live-shaped consent journey | https://docs.yapily.com/concepts/licensing-and-registration |
| Money movement | Approve v1 scope and regulated/provider route | Founder / legal | Before payment implementation | Transfers or automated set-aside | https://docs.yapily.com/payments/vrps/introduction |
| FreeAgent | Verify callback, scopes and synthetic sandbox tenant | Engineering | Before provider end-to-end tests | OAuth end-to-end test; guarded HTTP boundary is complete | https://dev.freeagent.com/docs/oauth |
| Xero | Verify callback, scopes and demo/synthetic organisation | Engineering | Before provider end-to-end tests | OAuth end-to-end test; guarded HTTP boundary is complete | https://developer.xero.com/documentation/guides/oauth2/auth-flow/ |
| Intuit | Verify callback, scopes and synthetic sandbox company | Engineering | Before provider end-to-end tests | OAuth end-to-end test; guarded HTTP boundary is complete | https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0 |
| Google | Create OAuth application and approve redirect URIs | Founder | Before Google sign-in end-to-end test | Social sign-in | Official Google Identity documentation (to be verified in auth workstream) |
| Apple | Enrol/configure Services ID, key and relay domains | Founder | Before Apple sign-in end-to-end test | Apple sign-in | Official Apple Developer documentation (to be verified in auth workstream) |
| HMRC annual student-loan calculation | Future enhancement only: obtain explicit annual Self Assessment authority or controlled sandbox calculation evidence before supporting simultaneous undergraduate plan types | Tax-domain review / engineering | Before removing the founder-authorised unsupported-for-decision boundary or approving the three pending fixtures | Simultaneous-plan arithmetic support; does not block the scoped launch purpose while fail-closed controls remain | https://developer.service.hmrc.gov.uk/guides/tax-logic-service-guide/documentation/tax-calculation.html |

No credentials, live account identifiers or customer data should be added to this file.

HMRC clarification, 13 August 2026: the product/version ambiguity is resolved.
`paye-des-stub` is the technical service identifier for **Individual PAYE Test
Support**; current official pages identify **2.0 beta** as the Sandbox version
relevant to the subscribed Individual Employment 1.2, Individual Income 1.2 and
Individual Tax 1.1 stateful journeys. **Self Assessment Test Support (MTD) 1.0
beta** is separate and deletes developer-supplied stateful MTD sandbox data; it
does not seed PAYE evidence. Subscription and exact endpoint/payload contracts
still require verification before fixture calls. See
`docs/HMRC_ADAPTER_IMPLEMENTATION_DECISION.md`.
