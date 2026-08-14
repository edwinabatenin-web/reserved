# Accounting-Assisted Income Matching

Accounting integrations provide context that Open Banking cannot reliably infer.

The current provider classes are implementation placeholders. The canonical
contracts in `reserved/providers/accounting/contracts.py` now preserve business
identity, provider identity, pagination cursor, source update time and sync
status across FreeAgent, Xero and QuickBooks. Raw access/refresh tokens are not
part of canonical records.

Reserved's canonical flow is:

1. Import an invoice from FreeAgent, Xero or QuickBooks.
2. Normalise it into Reserved's invoice schema.
3. Observe a bank credit through Open Banking.
4. score possible invoice matches using amount, date, payer, reference and provider payment records.
5. Auto-match only when confidence is high and the result is unambiguous.
6. Ask the user to confirm ambiguous matches.
7. Use the relevant accounting basis to determine tax timing.

For cash-basis sole traders, payment timing will normally drive the income
estimate. Invoice and service dates remain valuable for matching, forecasting
and overdue-payment insight.

## Verified provider constraints (12 August 2026)

| Provider | OAuth / test environment | Pagination / limits | Implementation boundary |
|---|---|---|---|
| FreeAgent | OAuth 2.0; sandbox host `api.sandbox.freeagent.com`; access and refresh tokens per authorised account | Default 25, maximum 100 per page using `page`/`per_page`; Link and `X-Total-Count` headers; 120 user requests/minute, 3,600/hour, 15 refreshes/minute | Company, invoices and related records can be adapted after sandbox app credentials/callback are configured |
| Xero | OAuth 2.0 and demo company | Invoices and bank transactions support pagination; 5 concurrent calls, 60/minute per tenant, daily tier limits and `Retry-After` on 429 | Tenant selection and token refresh are required; connector must queue/back off rather than promise immediate full history |
| QuickBooks Online | OAuth 2.0 and sandbox company | Query responses capped at 1,000 entities; sandbox/production REST limits include 500/minute per realm and 10/second per realm/app; webhooks available | Preserve Realm/business ID, paginate explicitly, verify webhooks, back off on 429 |

Official sources:

- https://dev.freeagent.com/docs/oauth
- https://dev.freeagent.com/docs/introduction
- https://developer.xero.com/documentation/getting-started-guide/
- https://developer.xero.com/documentation/guides/oauth2/limits
- https://developer.intuit.com/app/developer/qbo/docs/learn/limits-and-throttles
- https://developer.intuit.com/app/developer/qbo/docs/develop/webhooks

Exact resource field mappings, webhook event coverage and app-review requirements
must be verified against each official resource reference during adapter
implementation; capabilities are not inferred merely from the normalised model.
