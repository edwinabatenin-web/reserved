# Sandbox integration readiness

Status: implementation boundary prepared; no external account or credential was accessed.

The readiness harness in `reserved/providers/readiness.py` performs local,
value-blind checks only. It cannot call a provider. A connector is eligible for
an explicit sandbox test only when both credentials, an explicitly non-production
environment, and a safe registered callback URI are present.

| Provider | Required configuration names | Current implementation status | Next evidence needed |
|---|---|---|---|
| HMRC | `HMRC_CLIENT_ID`, `HMRC_CLIENT_SECRET`, `HMRC_ENVIRONMENT`, `HMRC_REDIRECT_URI` | Configuration and OAuth safety boundary only; PAYE evidence calculation remains local | User-restricted OAuth journey with a synthetic test user; subscribed endpoint contract tests; disconnect/expired-token tests |
| Yapily AIS | `YAPILY_APPLICATION_UUID`, `YAPILY_SECRET`, `YAPILY_ENVIRONMENT`, `YAPILY_CALLBACK_URI` | Existing fixture client and route tests; live HTTP methods are intentionally unimplemented | Confirm current AIS/Hosted Pages contract and callback/webhook security in Yapily sandbox; institution-specific consent and pagination evidence |
| FreeAgent | `FREEAGENT_OAUTH_IDENTIFIER`, `FREEAGENT_OAUTH_SECRET`, `FREEAGENT_ENVIRONMENT`, `FREEAGENT_REDIRECT_URI` | Canonical invoice boundary; provider adapter is a placeholder | OAuth code/refresh/revoke journey and synthetic invoice pagination/normalisation evidence |
| Xero | `XERO_CLIENT_ID`, `XERO_CLIENT_SECRET`, `XERO_ENVIRONMENT`, `XERO_REDIRECT_URI` | Canonical invoice boundary; provider adapter is a placeholder | OAuth tenant selection, refresh/revoke, rate-limit handling and demo-company invoice pagination evidence |
| QuickBooks | `QUICKBOOKS_CLIENT_ID`, `QUICKBOOKS_CLIENT_SECRET`, `QUICKBOOKS_ENVIRONMENT`, `QUICKBOOKS_REDIRECT_URI` | Canonical invoice boundary; provider adapter is a placeholder | OAuth `state`, sandbox `realmId`, refresh/revoke, 429 handling and paginated invoice-query evidence |

## Security gates

- Never silently select sandbox when credentials exist: environment must be explicit.
- Any partial credential pair disables network access.
- Production is blocked by this harness.
- OAuth callbacks use HTTPS, except localhost development callbacks.
- OAuth state is random, provider-bound, short-lived, stored as a digest and consumed once.
- Authorisation codes and tokens must be handled server-side, excluded from URLs after callback, encrypted at rest, redacted from logs, and deleted/revoked on disconnect.
- Provider business identifiers (Xero tenant, QuickBooks realm, FreeAgent company) must remain bound to the authorising Reserved user.
- Sandbox fixtures must remain visibly synthetic and segregated from production records.

## Important capability boundary

Configuration readiness does not mean an integration works. The placeholder
accounting adapters must not be shown as connected, and the Yapily fixture mode
must not be presented as a real bank connection. Each row above remains blocked
until its sandbox evidence is captured.

## Primary documentation checked 12 August 2026

- HMRC Developer Hub reference guide and OAuth credentials guidance
- Yapily official API/Hosted Pages documentation (contract must be reconfirmed before wiring the existing placeholder)
- FreeAgent official OAuth and API documentation
- Xero official OAuth 2.0 and limits documentation
- Intuit QuickBooks Online OAuth 2.0 and sandbox documentation
