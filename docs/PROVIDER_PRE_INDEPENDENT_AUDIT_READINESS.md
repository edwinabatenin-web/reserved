# Provider evidence — pre-independent-audit readiness assessment

Assessment date: 13 August 2026  
Scope: HMRC, FreeAgent, Xero, QuickBooks, Yapily AIS, Google and Apple sign-in  
Verdict: **READY FOR INDEPENDENT AUDIT OF THE CURRENT INCOMPLETE STATE; NOT
READY FOR SANDBOX OR LAUNCH ASSURANCE**

## Decision

The repository now gives an independent auditor enough accurate, bounded
evidence to assess the provider architecture, disabled state and material gaps.
No remaining repo-local documentation or generic-contract defect prevents that
assessment. The principal missing evidence is external/runtime evidence: exact
provider contracts not yet retained for every adapter, approved encrypted token
custody, configured synthetic environments and executed end-to-end sandbox
journeys.

An auditor must not interpret this verdict as provider readiness. All five HMRC,
accounting and Yapily provider specifications remain
`implementation_enabled=False`; accounting adapters and live Yapily methods
remain explicit placeholders; HMRC has no HTTP adapter; Google and Apple are
not launch-verified. Credentials being present can produce only
`configured_not_implemented`, never permission to call a sandbox.

## Evidence available to the auditor

| Area | Repo-local evidence now assessable | Material evidence still absent |
|---|---|---|
| Common provider boundary | Provider-bound, expiring, single-use OAuth state; callback/code custody; opaque credential references; atomic refresh-store contract; sandbox-confined injected HTTP boundary; schema drift, pagination and payload-free import-evidence contracts; value-blind fail-closed readiness state. | Approved encrypted token store and external key custody; deployment ownership isolation; runtime log/redaction and backup/restore evidence. |
| HMRC | Correct separation of PAYE DES test support from MTD Self Assessment Test Support; relevant PAYE product/version and official source trail; minimum employment-first journey; exact non-inventable endpoint/schema gaps. | Reviewable Individual PAYE Test Support 2.0 OpenAPI operation, exact selected read endpoint/scopes/errors; subscription confirmation; adapter; synthetic test user and end-to-end evidence. |
| FreeAgent | Current official sandbox OAuth success-path URLs, request fields, Basic authentication placement, token response and refresh rotation captured in a network-inert contract; official invoice/pagination sources and an exact staged journey. | Complete error/denial/revocation contract and optionality; encrypted custody and company ownership binding; reviewed invoice source mapping; adapter and sandbox run. |
| Xero | Disabled placeholder, provider-neutral invoice/import contracts and an execution checklist that requires tenant discovery/binding, pagination and rate-limit evidence. | Exact reviewed OAuth/tenant/invoice adapter contract, custody, implementation and demo-company end-to-end evidence. |
| QuickBooks | Disabled placeholder and checklist that requires callback `realmId` ownership binding, explicit sandbox origin, pagination and rotated refresh-token handling. | Exact reviewed OAuth/query/error schemas, custody, implementation and sandbox-company end-to-end evidence. |
| Yapily AIS | Fixture/live distinction, explicit `NotImplementedError` live methods, payment-initiation separation, synthetic route/security tests and AIS execution requirements. | Confirmed contracted AIS product and exact current Hosted Pages/consent/webhook contracts, encrypted consent custody, institution-specific implementation and sandbox evidence. Fixture success is not provider evidence. |
| Google/Apple via Clerk | Brokered-identity architecture, environment/configuration checks and explicit acceptance criteria for issuer/audience/session and provider setup. | Proof of correct provider enablement/configuration in the intended Clerk instance; synthetic browser/token failure journeys; Apple notification/account-deletion and policy evidence. |

## Material consistency check

One chronology issue could have misled an auditor: the FreeAgent decision kept
an earlier “exact OAuth evidence unavailable” assessment above a later successful
official contract capture. The older section is now explicitly labelled
historical and superseded. The current headline remains correct because the
invoice adapter, custody, binding, error handling and sandbox execution are
still incomplete.

No other material contradiction was found:

- readiness documents consistently distinguish configuration from an enabled
  adapter and from executed end-to-end evidence;
- the sandbox execution pack labels provider assertions as future evidence
  requirements, not implemented capability;
- HMRC documentation explicitly withholds unverified endpoints and schemas;
- provider-neutral contracts do not claim provider-specific correctness;
- Yapily fixture behavior is visibly synthetic and must not count as a bank
  connection or sandbox pass; and
- authentication readiness explicitly withholds Google/Apple launch
  attestation.

## Auditor starting set

Use these as the governing provider evidence set:

- `docs/PROVIDER_BOUNDARY_ADOPTION.md`
- `docs/SANDBOX_INTEGRATION_READINESS.md`
- `docs/SANDBOX_E2E_EXECUTION_PACK.md`
- `docs/HMRC_ADAPTER_IMPLEMENTATION_DECISION.md`
- `docs/FREEAGENT_ADAPTER_IMPLEMENTATION_DECISION.md`
- `docs/ACCOUNTING_INTEGRATIONS.md`
- `docs/YAPILY_INTEGRATION_SPEC.md`
- `docs/AUTHENTICATION_READINESS.md`
- `reserved/providers/readiness.py`

The auditor should verify that disabled behavior is fail-closed, challenge the
generic/provider boundary, and judge whether the listed execution evidence is
proportionate. They cannot assess real provider correctness, resilience,
consent lifecycle or data completeness until the external sandbox journeys
exist.

## Reassessment trigger and stopping rule

Reassess this provider evidence set when any adapter is implemented, a token
store is selected, or the first synthetic sandbox journey is recorded. At that
point attach exact reviewed provider contracts, redacted evidence records and a
snapshot identifier.

Further generic infrastructure or planning would not materially improve the
current independent audit. The next useful work is provider-specific contract
capture and synthetic execution in an approved runtime; this review therefore
stops without inventing APIs or enabling networking.
