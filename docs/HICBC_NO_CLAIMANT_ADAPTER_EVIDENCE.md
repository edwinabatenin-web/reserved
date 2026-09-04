# HICBC no-claimant adapter — bounded correction candidate

Base `315248807667868ff52dffce2ab0dab599e651dc`, tree
`f664b0a666b34b492e0fdc60e62d5c86946ad57e`, branch
`astra/hicbc-no-claimant-adapter`. Founder Decisions SHA-256 remains
`78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`.
This is implementation evidence pending another independent reviewer, not
self-acceptance, integration, production activation or launch readiness.

## Defect and exact repair

The UI and stored estimate use claimant `none` for the affirmative “No one”
answer. The engine accepts only person, partner or Python None. Previously the
shared builder passed the literal string through, causing GET/result/save-read
errors and a closed 400 annual preview. No statutory calculation or engine enum
change is needed: the existing engine already supports claimant None plus known
zero entitlement and established own ANI as a no-charge result.

The shared web adapter now translates stored/UI `none` to engine None, without
changing the stored answer. Its amount adapter establishes zero only when the
affirmative answer has no contradictory or malformed entitlement facts:

- Annual override, children receiving Child Benefit and entitlement weeks must
  each be absent/blank or a valid non-negative zero.
- Any positive annual amount, positive receipt-child count or positive
  entitlement weeks contradicts no household entitlement. An explicit zero
  annual override does not erase positive count/week evidence, nor vice versa.
- Present legacy receipt information must normalize to the existing negative
  answer. Positive or malformed legacy receipt information does not establish
  unambiguous zero.
- Malformed, non-finite or negative amount/count/week data becomes an unknown
  amount in the shared builder, not zero or an echoed exception.

The engine receives None/zero only for the admitted absence; conflicting or
malformed evidence reaches its existing None/unknown insufficient-facts path.
Unknown own ANI remains insufficient even when zero entitlement is established.
Unknown claimant/amount is never converted into affirmative absence. This is
explicit conflict refusal, not new entitlement or customer policy.

The saved form now accepts an explicit zero annual override for claimant `none`
only; other form validation is unchanged. Positive contradictory facts may
remain saved for correction, but neither read path publishes a zero or other
point from them. Malformed form submissions remain rejected before any write.
No row is rewritten during read/preview, and no migration or replacement of the
existing ambiguous legacy receipt normalization is performed.

The engine, frontend, schema, configuration, route/auth/CSRF boundaries and
annual preview/link checks are unchanged. Only the current `hicbc.py` hash in
S5A and current S5A hash references in S5B are refreshed. No historical source
pin, route/class count, status or completion denominator changes.

## Synthetic verification

New suite: **32 passed**. Requested affected matrix: **415 passed, zero failed**:

```text
tests/test_hicbc_no_claimant_adapter.py
tests/test_hicbc_partner.py
tests/test_hicbc_annual_source_runtime.py
tests/test_hicbc_annual_preview_frontend.py
tests/test_hicbc_partner_privacy.py
tests/test_hicbc_linked_account.py
tests/test_hicbc_linked_corrections.py
tests/test_internal_tax_boundary.py
tests/test_w8_progressive_assurance_s2.py
tests/test_w10_paid_surface_inventory.py
tests/test_w10_internal_route_reconciliation.py
```

Run with `/private/tmp/reserved-venv/bin/python -m pytest` plus those paths.
The new tests reuse the accepted synthetic Flask fixture, canonical annual
fixture and executable Node frontend harness; they do not replace the producer
or adapter with mocks. Actual session/CSRF form POST, page GET, result GET,
annual POST and executable response rendering now produce the settled £0 view
for affirmative absence, including explicit zero or a blank annual override.
Positive person/partner fixtures retain the existing £703/£0 outcomes.

Contradiction fixtures cover positive annual/count/week evidence, zero override
with positive receipt evidence, negative/non-finite/malformed values, unknown
own ANI and claimant/amount, and legacy receipt zero without inferring partner
claimancy. Corrupt child-count fixtures are explicitly injected into disposable
SQLite rows because the current writer already integer-validates those values.
Read/preview snapshots verify no database mutation. Malformed form submissions
leave the previous row untouched; valid-but-contradictory saved facts remain
available rather than being silently erased.

The active-link annual preview still returns 409 and no charge amount. CSRF,
authentication, owner isolation, no-store/Vary, and private operand/error-text
exclusions remain covered. The accepted full frontend suite retains its
legitimate response-shape and hostile-response regressions. No protected tests
were edited or suppressed. These are local synthetic request and executable-JS
tests, not a new browser/visual/human acceptance claim or the full canonical gate.

## Remaining gates

This corrects the previously reported no-claimant source adapter defect only.
Independent exact-candidate review, privacy/retention/legal/security acceptance,
human comprehension/accessibility and target evidence remain separate gates.
Linked annual-source/anti-probing engineering remains unresolved and its refusal
is retained. No annual total, reserve/payment publication, durable annual
position, provider interaction, paid entitlement or October launch completion
is supplied. No commit, integration, credential or live configuration change
was performed by the implementer.
