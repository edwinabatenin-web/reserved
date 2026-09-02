# W8 progressive integration assurance S2 — correction evidence

Package: `ohds-w8-progressive-assurance-s2`. This remains an assurance-only,
network-inert correction; no production code changed.

## 1. Frozen correction input

- Branch: `ohds/w8-progressive-assurance-s2`
- HEAD: `b2c216294b83c1fbaaa09259f671ae5bf7708e06`
- Tree: `2ba2ce52b389f76c5d6d2ae7ab032763f2e6e1b5`
- Tracked/staged state: no changes.
- Exactly three untracked inputs:
  - `docs/W8_COMPLETION_MAP.md` —
    `dd5058c3848b8d59e1cbace59d953da9b655923093fdcac722e039ef361d4aeb`
  - `docs/W8_PROGRESSIVE_ASSURANCE_S2_EVIDENCE.md` —
    `837616f0541fdfefefb9e61efba6dd496a5d94a2e3acc462e12a29b6aee0323f`
  - `tests/test_w8_progressive_assurance_s2.py` —
    `abc1ecdea926489853ce15da77b878c7bea5a2c9f3cc3553fefa2555d00e8a8b`

## 2. Correction scope and final paths

Only the same three untracked paths were edited:

- `docs/W8_COMPLETION_MAP.md`
- `docs/W8_PROGRESSIVE_ASSURANCE_S2_EVIDENCE.md`
- `tests/test_w8_progressive_assurance_s2.py`

Final per-file SHA-256 (this evidence record's own hash is omitted to avoid a
self-referential checksum):

- `tests/test_w8_progressive_assurance_s2.py` →
  `4dbd80fc4451a6459f83c0bcfdc3e49b66e7200f5b484ffc343369aee420b591`
- `docs/W8_COMPLETION_MAP.md` →
  `bcda59cbb49ae2268accb2bdf99fb7ff1ae5ff7534a8d4c85825a56e92c344db`

No product, existing-test, Founder-decision, provider, configuration, release
or integration file changed. Nothing was staged, committed, pushed or fetched.

## 3. Executed verification

Every run disabled bytecode generation and pytest cache:

```text
PYTHONDONTWRITEBYTECODE=1 python3 -B -m pytest -p no:cacheprovider ...
```

### Focused baseline

```text
tests/test_w8_progressive_assurance_s2.py
24 passed
```

### Declared affected matrix

```text
tests/test_w8_progressive_assurance_s2.py
tests/test_integrated_annual_position.py
tests/test_annual_position_composition.py
tests/test_cash_ready_annual_position.py
tests/test_annual_to_cash_integration.py
tests/test_accounting_contracts.py
tests/test_accounting_canonical_v3.py
tests/test_accounting_non_exposure.py
tests/test_accounting_sync_contracts.py
tests/test_hicbc_integration.py
tests/test_hicbc_partner.py
tests/test_mtd_readiness.py
tests/test_internal_tax_boundary.py
tests/test_release_gate.py
tests/test_progressive_integration_assurance.py
tests/test_payments_on_account.py
tests/test_sa_account_reconciliation.py
tests/test_cash_funding_position.py
tests/test_cash_obligation_reconciliation.py
585 passed
```

### Actual-provider contract matrix

```text
tests/test_freeagent_invoice_contract.py
tests/test_xero_invoice_contract.py
tests/test_quickbooks_observation_contract.py
tests/test_quickbooks_invoice_payment_adapter.py
506 passed
```

No provider network, credential, customer data or external state was used.

## 4. Executable evidence established

The corrected self-contained module imports public production contracts and
uses minimal synthetic provider objects; it imports no fixture/helper from
another test module.

1. Mixed supported employment, sole-trade, savings and dividend income composes
   through annual position, cash-ready annual position and annual-to-cash. It
   preserves PoA, balancing, HMRC-account reconciliation, dated obligations and
   reserve funding.
2. Missing, stale, conflicting or discrepant evidence suppresses the final
   point result; HICBC ambiguity stays non-actionable; MTD unknown eligibility
   or incomplete evidence fails closed.
3. Duplicate payment/source identity, cross-channel reuse, cross-provider
   substitution and cross-business substitution are rejected before arithmetic.
   The substitution checks now use actual Xero and QuickBooks public
   `SourceObservation` results rather than generic provider-name strings.
4. Actual reviewed provider boundaries coexist in one process:
   - FreeAgent `parse_invoice_list` returns `FreeAgentInvoiceRecord` with the
     reviewed invoice URL identity;
   - Xero `map_detailed_invoice_response` returns `XeroInvoiceMapping` carrying
     `XeroInvoice`, `SourceObservation` and `SemanticAdapterResult`, whose
     provider identity is Xero;
   - QuickBooks `observe_invoice` and `adapt_invoice` return
     `InvoiceObservation` and `InvoiceAdapterResult`, carrying the canonical
     observation/semantic result and QuickBooks provenance identity.
   The test explicitly keeps these boundaries unequal. It assigns no missing
   FreeAgent adapter semantics and does not imply provider activation.
5. Direct public behavior exposes a geography blocker. A baseline employment
   result is `calculated` with `total_liability=3486.00`; adding each of
   `jurisdiction="Scotland"`, `country="Scotland"`,
   `country_code="GB-SCT"`, `territory="Scotland"` or
   `tax_regime="Scottish"` returns exactly the same result. The open facts
   mapping silently ignores every variant instead of failing closed.
6. Geography structures are checked as structures, not naive source-substring
   absence. QuickBooks `CompanyInfoObservation.country` retains `Scotland` and
   canonical `AccountingBusiness.country_code` retains `GB-SCT`. The FreeAgent
   public field universe validates a company `country` wire member but
   `FreeAgentCompanyRecord` has no retained `country` field. The three reviewed
   public structures expose no `territory` field. None is wired to annual-tax
   admission.
7. Internal annual objects remain absent from the inspected customer/API/
   persistence layers, and `october_launch_candidate()` remains truthfully
   `not_ready` with the named provider/MTD blockers.

## 5. Claims expressly not established

- Geography is not fail-closed. This is a launch blocker, not a passing check.
- There is no provider/canonical-to-annual-tax production handoff.
- The FreeAgent invoice contract is not a canonical adapter; transport-facing
  FreeAgent, Xero and QuickBooks provider classes remain disabled.
- There is no customer/API/persistence handoff, live provider journey,
  credential, network, real multi-provider flow or customer-data evidence.
- There is no target-runtime/provider-sandbox, privacy/security, release-
  artifact parity, independent-final-review or Founder release/go-live evidence.

Synthetic/component assurance is not delivery, integration or launch readiness.

## 6. Finite W8 delivery position

The corrected completion map has a stable denominator of five product-delivery
slices, all currently `planned`:

1. provider/canonical accounting input → annual-tax handoff;
2. annual/cash result → customer/API/persistence handoff;
3. enforced geography admission before actionable calculation;
4. enabled reviewed provider adapters and bounded customer journeys;
5. end-to-end multi-provider/mixed-income assembly over slices 1–4.

Progress is 0/5 at `integrated` or beyond. Target-runtime/provider-sandbox,
privacy/security, canonical/release parity, independent final review and
Founder merge/release/go-live authority are separately testable terminal checks,
not disguised delivery slices.

## 7. Corrections made

1. Replaced generic provider-name coexistence evidence with actual FreeAgent,
   Xero and QuickBooks public invoice/observation/adapter contract interactions.
   Retained the truthful boundary that transport activation is absent.
2. Replaced signature inspection and lexical geography inference with direct
   calls through the open annual facts mapping and structural field checks. The
   observed silent-ignore behavior is explicitly an unresolved launch blocker.
3. Rebuilt the W8 map around five coherent product slices, a stable denominator,
   dependencies, serial/parallel and collision controls, complete assurance
   states, effort/elapsed/critical-path assumptions, a distinct finite terminal
   gate, explicit out-of-scope boundary and one immediate bounded action.

No production defect was fixed under this package. The geography behavior is a
real unresolved product/launch blocker to be addressed only by its separately
owned delivery slice.

## 8. Review disposition

- HEAD/tree remain at the frozen base; only the three untracked paths exist.
- Focused: 24 passed. Declared affected: 585 passed. Actual-provider contracts:
  506 passed.
- The correction is ready for a different independent reviewer.
- W8 is not complete and not launch-ready; no merge/release decision is made.

W8-S2 CORRECTION READY FOR INDEPENDENT REVIEW
