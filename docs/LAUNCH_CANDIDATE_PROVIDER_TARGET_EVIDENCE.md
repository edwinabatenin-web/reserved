# Launch-candidate provider and target evidence pass

Assessment date: 13 August 2026  
Boundary: local synthetic inspection only; no secrets, credentials, provider
accounts, live data or network sandboxes accessed

## Outcome

No provider sandbox journey is executable from this sanitised workspace today.
That is an expected fail-closed result, not evidence that a journey passed. The
repository can support independent review of its current boundaries and can
record future runs, including Google and Apple after the evidence-pack repair
made in this pass.

| Journey | Status | Exact dependency before execution |
|---|---|---|
| HMRC PAYE | **Blocked** | Reviewable official operation contracts/scopes for selected reads and Individual PAYE Test Support 2.0 fixture; confirmed subscription; approved encrypted custody; disabled-first adapter; HMRC synthetic test user; authorised runtime. |
| FreeAgent | **Later** | OAuth success contract exists, but encrypted custody, company/user binding, reviewed invoice/error/pagination mapping and disabled-first adapter must be completed; then use a fully set-up temporary sandbox company. |
| Xero | **Blocked** | Exact reviewed OAuth, tenant, invoice/query and error contracts; encrypted custody; tenant-bound adapter; demo company and authorised runtime. |
| QuickBooks | **Blocked** | Exact reviewed OAuth, realm, query/pagination and error contracts; encrypted custody; realm-bound adapter; sandbox company and authorised runtime. |
| Yapily AIS | **Blocked** | Confirm contracted AIS authorisation product and exact Hosted Consent/consent/webhook contract; encrypted consent custody; replace live `NotImplementedError` paths; configured Modelo sandbox institution. Payment initiation remains excluded. |
| Google sign-in | **Later** | Authorised test Clerk access; confirm Google connection, origin/callback and token-validation settings; synthetic identity and real-browser negative tests. |
| Apple sign-in | **Later** | Authorised Clerk and Apple test configuration; confirm Service ID/domain/return URL and account-change notification/deletion handling; synthetic identity and browser negative tests. |

`Later` means the external test environment is appropriate once the listed
bounded implementation/configuration work is complete. `Blocked` means a
provider-contract or product-selection prerequisite prevents safe execution;
credentials alone cannot remove it.

## Credential-free checks completed

- Parsed the evidence schema as JSON and confirmed it remains structurally
  closed (`additionalProperties: false`).
- Confirmed all five data-provider readiness specifications have
  `implementation_enabled=False`; synthetic complete configuration therefore
  yields `configured_not_implemented` and cannot authorise a call.
- Confirmed FreeAgent's network-inert OAuth contract pins the sandbox host and
  rejects substitution of the production authorisation origin.
- Confirmed accounting providers remain explicit `NotImplementedError`
  placeholders and Yapily network methods remain unimplemented/fixture-only.
- Confirmed Google/Apple readiness is configuration attestation only, not
  end-to-end evidence.

These checks establish safe non-execution and evidence-pack structure only.

## Evidence-pack and target-runtime readiness

The execution pack covers state/replay, exchange, owner binding, minimum-scope
read, refresh rotation, disconnect, negative paths, pagination/completeness,
redaction and human review. The schema records build/API versions, synthetic
dataset, timings, counts, correlations, hashed redacted artefacts, findings and
reviewer decision. It can record a provider run without retaining secrets.

The prior material omission was identity-provider coverage: Google and Apple
could not be represented by the schema and had no execution checklist. Both are
now included. The pack deliberately does not supply credentials, automate
browser consent or claim provider-specific test cases exist.

In the authorised target environment:

1. identify an immutable build reference and confirm the checkout is sanitised;
2. install pinned project dependencies in an isolated environment;
3. run the complete local suite and retain the command, interpreter/dependency
   versions, start/end time, exit status and unedited summary;
4. run focused provider/readiness/schema tests before enabling any deliberately
   reviewed sandbox adapter;
5. inspect readiness without printing environment values; a provider must still
   report `configured_not_implemented` until its gate deliberately changes;
6. execute one provider at a time with synthetic data, completing a separate
   schema-valid evidence record and secret scan; and
7. obtain human evidence review before describing a journey as passed.

The repository does not currently contain a pinned target-runtime lock or an
automated evidence-schema validation test. The reported full-suite pass should
therefore be repeated in the intended Replit/runtime image, with the exact
environment snapshot retained. This is a target-evidence gap, not permission to
alter dependencies during a provider run.

## Stopping decision

The safe local increment is complete. Further progress requires provider-
specific contracts, approved encrypted custody and/or authorised external test
configuration. No credential discovery or sandbox call is justified from this
workspace.
