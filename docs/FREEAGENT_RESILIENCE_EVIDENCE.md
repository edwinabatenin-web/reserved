# FreeAgent resilience / state-contract evidence (FA-S4 slice)

Observation date: 1 September 2026.

This record is the evidence base for
`reserved/providers/accounting/freeagent_resilience.py`. It separates
documented FreeAgent facts, existing Reserved invariants and bounded
implementation inference, and it records what the slice deliberately does not
support. No account, credential, customer record, sandbox request or provider
API call was used to produce this slice; the module is network-inert.

## Non-invention rule

The slice may describe safe next states/decisions over already-validated
inputs only. It performs no HTTP, credential access, secret storage,
persistence, sleeping, retry loop, provider enablement, payment action or
canonical accounting mapping. Unknown provider error, revocation and
disconnect semantics are not guessed: they remain explicitly unsupported and
fail closed.

## 1. Documented FreeAgent facts

### 1.1 Pagination

Source: FreeAgent API introduction
(`https://dev.freeagent.com/docs/introduction`), already captured verbatim in
`docs/FREEAGENT_INVOICE_CONTRACT_EVIDENCE.md` and enforced by
`reserved/providers/accounting/freeagent_invoice_contract.py`.

- Requests that return multiple items are paginated and default to **25 items
  per page**.
- A client selects a page with `page` and changes page size with `per_page`,
  which is **limited to 100 items per page**.
- Pagination information is carried in the `Link` header with exactly
  `prev`, `next`, `first`, `last` relations.
- `X-Total-Count` carries the total number of entries it is possible to
  paginate over.
- The documented example preserves the full next-page URL, including its query
  string; the slice preserves the URL verbatim and never constructs a next URL.

### 1.2 Rate limits and 429 handling

Source: FreeAgent API introduction, already recorded in
`docs/FREEAGENT_INVOICE_CONTRACT_EVIDENCE.md`.

- 120 user requests/minute.
- 3600 user requests/hour.
- 15 token refreshes/minute.
- Throttling uses a `429` response with `Retry-After`.

Only the `429`/`Retry-After` fact is encoded in this slice. The numeric limits
are retained as constants so the evidence is auditable, but no live limiter is
implemented (there is no HTTP client and no sleep).

### 1.3 OAuth refresh and the complete token set

Source: `reserved/providers/accounting/freeagent_oauth_contract.py`, authority
observed 2026-08-13 (`https://dev.freeagent.com/docs/oauth`).

- A refresh request is `grant_type=refresh_token` plus the refresh token.
- The documented token response carries exactly five fields: `access_token`,
  `token_type` (exact `bearer`), `expires_in` (positive integer),
  `refresh_token`, and `refresh_token_expires_in` (positive integer).
- The existing validator requires all five fields present and valid; a partial
  set is rejected rather than accepted.

The slice models a refresh decision over this complete, already-validated
`FreeAgentTokenSet`. It never retains or exposes the `access_token` or
`refresh_token` strings. The caller-supplied `old_reference` is a non-secret
opaque identifier in a fixed format (see section 3); it is not a token, not a
storage handle, and no storage or prior existence of the reference is claimed.

## 2. Existing Reserved invariants

### 2.1 Provider-neutral sync collector

Source: `reserved/providers/accounting/sync_contracts.py`.

- `collect_pages` bounds iteration with `max_pages` (default **1000**) and
  fails closed when the limit is exceeded.
- A cursor-based walk rejects a repeated next cursor (either equal to the
  current cursor or already requested) rather than looping silently.
- Duplicate record identities across pages are rejected rather than overwritten.
- A source watermark that moves backwards is rejected.
- A page with no next cursor terminates the walk.

The slice's pagination decision is designed to be the FreeAgent-specific,
network-inert complement to this collector: it validates one page at a time and
returns either the preserved next URL or a terminal decision.

### 2.2 Fail-closed external-data handling

Source: existing Founder external-data/resilience decisions
(`docs/EXTERNAL_DATA_SPECIFICATIONS.md`).

- External data must not leak secrets into logs or results; token strings never
  enter result representations or errors.
- Unknown or malformed external state must fail closed rather than be guessed.
- Provider assertions never become tax decisions.

These drive the slice's redacted refresh-decision representation, its
conservative error classification and its requirement that every input be an
exact, already-validated type. The `old_reference` accepted by
`decide_refresh_rotation` is therefore restricted to a non-secret opaque
identifier format; rejected values are never echoed.

## 3. Bounded implementation inference

These values are **not** documented FreeAgent facts; they are deliberate,
bounded choices recorded so they can be reviewed or revised.

- `DEFAULT_MAX_PAGES = 1000` matches the shared sync collector default so a
  FreeAgent adapter can share one configured ceiling. It is a page/request
  accounting bound, not a provider claim.
- `DEFAULT_MAX_WAIT_SECONDS = 300` is a conservative cap on `Retry-After`.
  A `429` wait above this bound fails closed rather than being silently
  clamped or slept through.
- Digit-only `Retry-After` text is lexically bounded before integer conversion,
  so pathological numeric strings remain a controlled fail-closed result rather
  than escaping through the runtime's integer-conversion limit.
- `DISCONNECT_IS_LOCAL_ONLY = True`: the local-disconnected state is a local
  state only. No provider-side revocation call is performed or claimed. The
  FreeAgent evidence retained here documents no disconnect/revocation endpoint,
  so none is invented.
- `OLD_REFERENCE_NAMESPACE = "freeagent.ref"` and
  `OLD_REFERENCE_IDENTITY_LENGTH = 32`: the only accepted `old_reference` is
  `freeagent.ref.<32 lowercase hexadecimal digits>`. This is a non-secret
  opaque correlation identifier, not a token and not a credential-storage
  handle; token-like values, whitespace, readable slugs and malformed values are
  rejected without being echoed, and no storage or prior existence is claimed.

## 4. Behavioural mapping (fact + invariant + inference)

| Decision | Documented fact | Reserved invariant | Bounded inference |
|---|---|---|---|
| `decide_pagination` | Link relations, `X-Total-Count`, exact origin/path for `/v2/invoices` | no repeated/cyclic cursor; page bound | page counter vs `page` metadata; exact current/seen cursor-history coherence; count-coherence and next-at-limit fail-closed rules |
| `decide_refresh_rotation` | complete five-field token set | never leak tokens; never claim storage | atomic replacement requires the entire validated set; strict non-secret `old_reference` format |
| `classify_connection_state` / `transition_connection` | access/refresh expiry are valid/invalid facts | fail closed; no automatic reconnect | any known invalid refresh token requires reauthorisation; the transition boundary itself revalidates the complete token set and non-secret old reference before restoring `CONNECTED`; four-state model; local-only disconnect |
| `decide_rate_limit_retry` | `429` + `Retry-After` | no sleeping/unbounded retry | max-wait cap; single documented retryable status |
| `classify_provider_error` | only `429` is a documented retryable status | unknowns are review-required | non-`429` statuses are `UNKNOWN` |

## 5. Explicitly unsupported

The following are not implemented and are not guessed:

- Provider-side revocation or disconnect semantics (no endpoint is retained in
  evidence, so none is invented).
- Retryability of any status other than a valid `429`.
- Refresh loops or automatic reconnect; the slice only classifies states and
  returns single decisions. A caller-constructed summary decision cannot restore
  `CONNECTED`; the transition boundary requires and revalidates the complete
  token set while retaining none of its secret values.
- Token storage or credential mutation; `stored` is always `False`.
- Provider enablement, payment action, persistence or sleeping.

## 6. Files

- `reserved/providers/accounting/freeagent_resilience.py` — the slice.
- `tests/test_freeagent_resilience.py` — synthetic positive/negative/adversarial
  and property tests.
- `docs/FREEAGENT_RESILIENCE_EVIDENCE.md` — this dated fact/inference record.
- `docs/FREEAGENT_COMPLETION_MAP.md` — FA-S4 scope/status update only.
