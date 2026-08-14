# HMRC adapter implementation decision

**Decision date:** 13 August 2026  
**Decision:** do not implement or enable an HMRC HTTP adapter from the evidence
currently stored in this repository

## Outcome

The repository establishes that three subscribed, user-restricted APIs can
support Reserved's PAYE evidence journey:

- Individual Employment 1.2 — employment records and employer identifiers;
- Individual Income 1.2 — employment income held for the tax year;
- Individual Tax 1.1 — tax deducted and relevant refunds/set-offs.

It does **not** retain the endpoint-level contracts required to implement those
calls safely. Existing documents link to the official API pages and summarise
capabilities, environments and limitations, but do not record exact paths,
path/query parameters, OAuth scopes, `Accept` media types, required headers,
response schemas, endpoint-specific error codes or sandbox test scenarios.
Those details must not be reconstructed from memory or inferred from API names.

Accordingly, `ProviderSpec("hmrc")` remains
`implementation_enabled=False`. No network code, route, provider endpoint or
response parser has been added.

## Existing implementation inventory

| Concern | Current evidence/code | Decision |
|---|---|---|
| Sandbox configuration | Value-blind checks for `HMRC_CLIENT_ID`, `HMRC_CLIENT_SECRET`, `HMRC_ENVIRONMENT`, `HMRC_REDIRECT_URI` | Retain; complete configuration reports `configured_not_implemented` |
| OAuth state/callback custody | Provider-neutral digest-backed state, callback validation, one-use code and opaque token-store contracts | Suitable foundation, but not proof of HMRC's exact authorization/token contract |
| HTTP safety | Exact non-live HTTPS origin guard and redacted summaries | Suitable foundation after official HMRC origins/paths are captured and reviewed |
| Token storage | Interface and atomic rotation contract only | Blocked pending approved encrypted store and external key custody |
| HMRC adapter/routes | None | Correctly absent |
| PAYE interpretation | Local evidence reconciliation with provenance, conflicts and no unconditional HMRC precedence | Available after a separate adapter produces reviewed normalised evidence |
| Sandbox fixtures | Current official read-API pages direct Individual Employment 1.2, Individual Income 1.2 and Individual Tax 1.1 to the **Individual PAYE Test Support API**. Its technical service identifier is `paye-des-stub`; the current sandbox version is **2.0 beta** | Use the named product/version only after confirming it is subscribed to the Reserved sandbox application; do not substitute Self Assessment Test Support (MTD) |
| Fraud-prevention headers | Requirement and Test API process recorded | Exact connection-method header set and applicability must be captured before any relevant call |

## Minimal first synthetic read journey

The proposed first journey is deliberately narrow:

1. Create/use one HMRC individual **sandbox test user** only.
2. Complete one user-restricted browser authorisation using Reserved's registered
   sandbox callback and the minimum scopes required for Individual Employment.
3. Retrieve that test user's employment records for one supported tax year.
4. Normalise only the stable employment identity/provenance fields confirmed by
   the current official response schema; do not calculate or display liability.
5. Record redacted evidence for success, empty result, invalid tax year or other
   documented validation error, expired/invalid token and user denial.
6. Disconnect/delete Reserved's stored sandbox credential and demonstrate that
   subsequent access fails safely.

Individual Employment should come first because employment identities are
needed to associate later income and tax-deduction evidence without combining
different employments or double counting an aggregate. Individual Income and
Individual Tax should be added only after the employment-identity mapping is
reviewed. This ordering is an architectural inference from Reserved's evidence
model, not an HMRC-mandated API sequence.

The journey is **selected but not implementation-ready**. Even the first read
must wait for the official endpoint evidence below.

## Exact official evidence still required

Capture a dated, reviewable local decision record from the current official
pages for each implemented version. Do not copy client secrets, tokens, test
NINOs or test-user credentials.

### HMRC authorization platform

- sandbox authorization endpoint and token endpoint;
- required authorization parameters and exact scope string for Individual
  Employment 1.2;
- redirect URI matching rules, state handling and user-denial callback fields;
- authorization-code lifetime/single-use rules;
- token request authentication/body, token response schema, access/refresh
  expiry and rotation/revocation behaviour;
- documented sandbox OAuth test-user journey;
- whether any HMRC-specific callback parameter differs from the existing
  provider-neutral callback contract.

### Individual Employment 1.2

- exact sandbox base origin, path and HTTP method for the chosen read;
- all required path/query parameters, including tax-year format and taxpayer
  identifier requirements;
- exact `Accept` media type/version header and any other mandatory headers;
- required OAuth scope;
- success schema and which fields are stable identifiers versus display text;
- documented empty/no-data representation;
- endpoint-specific 4xx/5xx codes and retry guidance;
- available sandbox/test-support scenarios and any stateful setup dependency;
- fraud-prevention-header applicability for Reserved's connection method.

### Later Individual Income 1.2 and Individual Tax 1.1

Repeat the endpoint evidence above, plus:

- exact employment/linking identifier semantics across the three APIs;
- representation of cumulative, annual or period-level amounts and dates;
- refunds/set-offs and negative/adjustment semantics;
- currency, decimals and rounding as represented by HMRC;
- evidence that aggregate and employment-level values can be distinguished to
  prevent double counting.

### PAYE test support

- exact subscribed status for the Reserved sandbox app;
- exact fixture-creation endpoints, payload schemas, scenario identifiers and
  cleanup/reset behaviour;
- whether created data is immediately visible to each read API and any delays.

The product/version ambiguity is resolved by current official HMRC pages:

- **Individual PAYE Test Support API 2.0 beta** is the relevant sandbox
  companion for Individual Employment 1.2, Individual Income 1.2 and Individual
  Tax 1.1. Each read-API page expressly says its stateful sandbox data can be
  set up with Individual PAYE Test Support. The technical documentation service
  identifier remains `paye-des-stub`; it is not a separate “DES stub” product
  that should be selected instead.
- Version 2.0 beta is available in Sandbox. Version 1.0 beta also remains listed
  in Sandbox, but it is not the current version to target for new evidence
  capture. A later 2.1 alpha listing, where exposed by the documentation index,
  is marked not applicable rather than Sandbox and must not be targeted.
- **Self Assessment Test Support (MTD) 1.0 beta** is a different sandbox-only
  API. Its stated purpose is deleting stateful test data supplied by developers
  for MTD Self Assessment APIs. It does not create PAYE data and is not the test
  support dependency for Individual Employment, Income or Tax.

Official sources:

- [Individual PAYE Test Support 2.0](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/paye-des-stub/2.0)
- [Individual Employment 1.2](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-employment/1.2)
- [Individual Income 1.2](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-income/1.2)
- [Individual Tax 1.1](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-tax/1.1)
- [Self Assessment Test Support (MTD) 1.0](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/mtd-sa-test-support-api/1.0)
- [HMRC sandbox stateful-testing guidance](https://developer.service.hmrc.gov.uk/api-documentation/docs/testing/test-users-test-data-stateful-behaviour)

## Sequenced implementation boundary after evidence capture

1. Confirm the Reserved sandbox application is subscribed to Individual PAYE
   Test Support 2.0 beta; create no fixture until its exact endpoint/payload
   contract is reviewed. Retain Self Assessment Test Support (MTD) 1.0 only for
   cleanup of developer-supplied stateful MTD data where the MTD journey uses it.
2. Approve the encrypted token-store/key-custody design and implement its
   tamper, wrong-key, rotation and recovery tests.
3. Record exact official sandbox and OAuth origins in an HMRC-specific policy;
   keep production origins impossible in the sandbox adapter.
4. Implement authorization URL construction from the recorded contract using
   `OAuthStateStore`; add literal parameter/scoping tests.
5. Implement callback through `validate_callback`, `exchange_and_store` and the
   secure token store. Ensure state is consumed before exchange and raw codes or
   tokens never enter logs/session/application records.
6. Implement one Individual Employment read through `GuardedTransport`; parse
   only the captured response fields using a versioned `SourceSchema`.
7. Produce an `ImportManifest` and purpose assessment for the one-tax-year
   employment identity import. Empty data remains known-empty only where the
   official response contract establishes that meaning.
8. Test documented errors, denial, state mismatch/replay, expiry/401, refresh
   rotation and disconnect with synthetic data.
9. Run the HMRC fraud-header Test API where applicable and retain only redacted
   status evidence; a correct result is not described as certification.
10. Obtain a deliberate review of sandbox evidence. Only then set HMRC's
    `implementation_enabled=True` for explicit sandbox execution.
11. Add Individual Income and Individual Tax separately, each with literal
    source schemas, purpose gates and cross-employment/double-count tests.

## Normalisation boundary for the first journey

The first adapter output should be a new transport-neutral employment-evidence
record, not `PayeEvidence` containing guessed money values. At minimum, after
official schema confirmation, it should preserve:

- opaque Reserved evidence ID;
- HMRC API name/version and redacted source reference;
- tax year and import/observation time;
- stable employment identity and employer identifier(s) explicitly supplied by
  the documented response;
- field-level presence/completeness and source-schema version;
- original redacted artefact hash where evidence retention is approved.

Income and tax-paid fields remain absent—not zero—until their separate APIs are
implemented and linked. HMRC evidence must not overwrite payslip, P45/P60,
manual or bank evidence, and connection failure must not delete earlier
provenance.

## Primary pages already referenced in the repository

- [HMRC authorization: user-restricted endpoints](https://developer.service.hmrc.gov.uk/api-documentation/docs/authorisation/user-restricted-endpoints)
- [Individual Employment 1.2](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-employment/1.2)
- [Individual Income 1.2](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-income/1.2)
- [Individual Tax 1.1](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/individual-tax/1.1)
- [Individual PAYE Test Support 2.0](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/paye-des-stub/2.0)
- [Self Assessment Test Support (MTD) 1.0](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/mtd-sa-test-support-api/1.0)
- [HMRC reference guide](https://developer.service.hmrc.gov.uk/api-documentation/docs/reference-guide)
- [HMRC development practices](https://developer.service.hmrc.gov.uk/api-documentation/docs/development-practices)
- [Fraud-prevention guidance](https://developer.service.hmrc.gov.uk/guides/fraud-prevention/)

These links identify the official material to capture. Their presence alone is
not endpoint-level implementation evidence.

## Individual PAYE Test Support 2.0 endpoint-contract capture — 13 August 2026

**Bounded outcome:** product selection is resolved, but the smallest fixture
request remains **not implementation-ready** because the current official
endpoint specification could not be captured in a reviewable form during this
step. No endpoint, field, scope or response behavior is inferred below.

### Exact official facts captured

The current official overview establishes only the following contract-level
facts usable here:

- product: **Individual PAYE Test Support API**;
- version/environment: **2.0 beta**, Sandbox;
- sandbox base origin: `https://test-api.service.hmrc.gov.uk`;
- purpose: set up test data for Individual Benefits, Individual Employment,
  Individual Income and Individual Tax;
- the three selected read APIs—Individual Employment 1.2, Individual Income
  1.2 and Individual Tax 1.1—each expressly direct developers to this product
  for stateful sandbox setup; and
- the HMRC sandbox guide confirms the architectural pattern: retrieval-only
  Individual Tax data can be created through its accompanying Individual PAYE
  Test Support API.

Primary sources:

- [Individual PAYE Test Support 2.0 overview](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/paye-des-stub/2.0)
- [Individual PAYE Test Support 2.0 endpoint specification page](https://developer.service.hmrc.gov.uk/api-documentation/docs/api/service/paye-des-stub/2.0/oas/page)
- [HMRC test users, test data and stateful behavior](https://developer.service.hmrc.gov.uk/api-documentation/docs/testing/test-users-test-data-stateful-behaviour)

### Smallest intended fixture and unresolved exact contract

The smallest useful fixture remains one employment identity for one synthetic
HMRC individual and one tax year, sufficient to verify a subsequent Individual
Employment 1.2 read before adding income or tax amounts. The accessible official
overview does not expose the endpoint-level OpenAPI content required to encode
that fixture safely. The endpoint specification page was located, but its
method/path/schema content was not available through the review reader.

The following are therefore still **unknown and must not be invented**:

1. the exact fixture endpoint name, HTTP method and path;
2. whether the NINO and tax year are path parameters, request fields or both,
   including their exact formats and supported years;
3. the exact `Accept` and request `Content-Type` media values;
4. whether the endpoint is application-restricted, user-restricted or otherwise
   authorised, and the exact subscribed OAuth scope if any;
5. all required/optional employment request fields, nesting, types, formats,
   enum values, cardinalities and omitted/null semantics;
6. the success status, response body schema (including whether it is empty) and
   visibility/consistency behavior before the subsequent read;
7. the complete documented 4xx/5xx statuses, error codes and response schemas;
8. duplicate-create/update/idempotency behavior and any cleanup/reset contract;
9. whether fraud-prevention headers apply to this test-support call; and
10. any fixture-specific `Gov-Test-Scenario` values.

### Actionable next step and stopping rule

An authorised reviewer should use the official page's **Download OpenAPI
specification** facility or another HMRC-published machine-readable export,
retain the unmodified 2.0 document with URL and observation date, and extract
only the single employment-setup operation. Verify its checksum and have a
second person compare the proposed literal request/response validator against
that source before implementation. If the Developer Hub exposes endpoint
details only after sign-in/subscription, inspect them in the Reserved sandbox
application without making a request and record no credentials or test-user
identifiers.

**Stopping rule applied:** the official overview proves which product to use but
not the wire contract. Writing a synthetic validator now would encode guessed
behavior. No test-support request model, endpoint policy or network code was
added.
