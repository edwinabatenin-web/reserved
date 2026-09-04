# PAYE manual baseline — capture and review candidate

Base `f3729c21b681cf4e6b2d70ba63421f2d3a3dee7d`, tree
`a7de59d0ee1034a2bad9b16bfb338c5d6efa189c`; branch
`astra/paye-manual-baseline`. Founder SHA-256 remains
`78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`.
The owner's exact 13-path authority implements part of the settled manual PAYE
fallback journey. This candidate is pending a different independent reviewer,
not self-acceptance, launch readiness or activation.

## Implemented path

The enabled dashboard links to authenticated GET/POST
`/v2/paye/manual-baseline`. GET renders the actual form; POST constructs
`PayeEvidenceCapture(source=MANUAL)`, calls the existing
`normalise_paye_evidence`, and renders an allowlisted review. No JavaScript or
document processing is introduced. On successful POST the form is replaced by
the review and an ordinary clean GET link for correction/re-entry; financial
values are not stored in a URL or session to support that link.

The form collects cumulative gross pay, cumulative tax deducted, tax code,
frequency, pension treatment and an effective-through date, with a separate
affirmative single-employment cumulative confirmation. Unknown amounts/code
are None, and unknown frequency/pension use the existing UNKNOWN enums. Known
zero is preserved exactly. Nothing is populated from demo/profile or provider
facts. Every existing frequency and pension enum remains supported.

The review shows all supplied fact categories, the configured display tax year,
and the server observation date. It explicitly labels the source manual,
representation employment-cumulative, and completeness partial. Frequency and
pension are taken from the validated capture because the normalizer deliberately
does not retain them. The normalized item supplies the other review facts. No
source precedence or full-year completeness is asserted. Request-local UUID
labels are internal only; they establish no durable employment or owner identity.

The reviewed result is not saved and is explicitly not an annual tax estimate,
refund/tax-to-pay calculation, forecast or reserve recommendation. The existing
PAYE reconciliation template and all tax/reconciliation/forecast functions remain
outside this path. Tax paid greater than gross is not newly adjudicated here;
these are partial supplied facts, not payroll validation or a reconciled result.

## Admission and security

`PAYE_MANUAL_BASELINE_ENABLED` must equal exactly `1` at request time. Neither
demo mode nor HICBC/billing flags enable it. Both existing production signals
(FLASK_ENV production or live Clerk prefix) refuse the handler regardless of
the switch and hide its dashboard link. Existing authentication can redirect
before the handler, and global CSRF can reject before handler checks; not every
denial is a 404.

The signed-session owner must be an exact positive integer resolving to an
existing user. A deleted user, bool, string, float, object or forged field does
not establish access. The handler reads only user existence, not financial data.
It uses the existing Flask-WTF protection and `/v2/` no-store/Vary policy, with
no exemption. Production flags, credentials and environment configuration were
not changed outside synthetic tests.

POST accepts only URL-encoded forms up to 4096 bytes, no files/query parameters,
duplicate fields or unsupported fields. Global CSRF runs before these handler
checks. Each field is bounded at 64 characters; monetary strings allow at most
10 integer digits and two decimal places. Those bounds are engineering input
limits, not provider or tax rules. Commas, currency symbols, exponents, signs,
nonfinite/negative/overprecise amounts and forged identifiers/source/year fields
are refused. The existing capture additionally enforces its tax-code grammar,
32-character code bound and enum rules. Effective date must be exact ISO, within
the configured supported year and no later than server observation date. The
display YYYY/YY is deliberately converted to the capture's YYYY-YY; prior
supported years are not silently relabelled as the current year.

Validation errors render a bounded fixed message and blank form, never raw
exception text or request values. The review template autoescapes text. No raw
document, financial cookie/session, log, analytics or financial persistence is
introduced. Ordinary submitted/rendered values necessarily remain transiently
in process/browser memory; secure memory erasure is not claimed.

## Exact synthetic verification

New route suite: **60 passed**. It uses disposable SQLite, actual Flask session
and CSRF requests, parsed dashboard/form discovery, observed actual normalizer
invocation and full review-field assertions. It distinguishes missing/zero,
tests amount/date/year/enum boundaries, all frequency/pension choices,
duplicates/oversized/forged inputs, strict flags, both production signals,
malformed/deleted owners, no extra financial reads, no database/session mutation,
escaping and no calculation/forecast invocation. No live database or external
provider was used. Root's separate browser check and independent review remain
required; server HTML tests alone are not browser/accessibility/human acceptance.

Affected matrix: **737 passed, 1 failed**, using
`/private/tmp/reserved-venv/bin/python -m pytest` with:

```text
tests/test_paye_manual_baseline.py
tests/test_paye_evidence_capture.py
tests/test_paye_extraction_confirmation.py
tests/test_paye_reconciliation.py
tests/test_paye_reconciliation_presentation.py
tests/test_paye_future_pay_forecast.py
tests/test_dashboard.py
tests/test_auth.py
tests/test_auth_claims.py
tests/test_internal_tax_boundary.py
tests/test_w8_progressive_assurance_s2.py
tests/test_w10_paid_surface_inventory.py
tests/test_w10_internal_route_reconciliation.py
tests/test_w10_paid_access_guard.py
```

The single failure is the unchanged historical
`test_w10_paid_access_guard.py::test_candidate_is_confined_to_exact_three_owned_paths_and_base`.
Its dirty-path allowance rejects this independently authorized 13-path package.
It was not suppressed, skipped, changed or represented as passing; it must be
rechecked on the clean owner checkpoint. No full canonical gate was rerun.

S5A now records 45 always-registered routes and 54 with HICBC, including the
independently disabled manual baseline. Paid classification rises from 26 to
27 endpoints in the existing route-less kernel; no runtime paid guard is wired.
S5A/B current source bindings and applicable S5A/D exact expectations are updated.
Historical source pins and historical dirty-scope allowances remain untouched.

## Remaining work

This delivers a bounded capture/review UI, not durable capture/lifecycle,
replacement/deletion/retention, multiple-employment assembly, annual binding,
reconciliation, future-pay forecasting, uploads/extraction/deletion, provider
integration or final customer journey. Privacy/legal/security, completeness and
recency policy, customer/accessibility/target evidence and production enablement
remain open. No completion denominator, October blocker or activation authority
is changed. No commits, integration, provider calls or live operations were
performed by the implementer.
