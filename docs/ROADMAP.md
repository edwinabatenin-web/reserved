# Reserved™ Roadmap

## October 2026 launch

One coherent launch version, rather than separate Alpha and Beta products:

- polished responsive dashboard and settings;
- proper authentication before live financial connections;
- sole-trader income and liability estimates;
- bank connection and transaction ingestion through approved Yapily scope;
- payment initiation through the founder-approved provider architecture, with
  provider-specific implementation and verification separately gated; Stripe
  Connect remains a historical unselected option only;
- immutable reconciliation records;
- external API failure and resilience controls across HMRC, Yapily, FreeAgent,
  Xero and QuickBooks:
  - isolate each provider behind its own adapter and the canonical Reserved data
    model;
  - pin provider/API versions where supported;
  - maintain contract tests and validate response schemas;
  - fail closed when required fields are missing, renamed or incompatible;
  - monitor provider changelogs and deprecation notices;
  - localise provider failures so unrelated functionality remains available;
  - retain last-known-good data with its timestamp where safe and appropriate;
  - test source reconciliation and detect material divergence;
  - monitor and alert on connection, authentication, schema and data-volume
    health;
  - combine webhooks with periodic reconciliation rather than relying on
    webhooks alone;
  - run automated regression tests for provider and API-version changes;
- clear limitations and user confirmations;
- private-beta monitoring and support processes.

## Immediately after launch

- any accounting-provider capability not admitted by the October provider
  readiness gate;
- canonical invoice and payment matching refinements beyond the admitted
  October scope;
- improved VAT support;
- limited-company and Corporation Tax forecasting.

## Later platform modules

- Capital Gains support;
- investment and crypto transaction ingestion;
- pension and retirement readiness;
- mortgage preparedness;
- predictive cash-flow insights;
- broader jurisdictions and currencies.
