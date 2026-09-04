# W10 offline Stripe signature-verifier candidate

Implementation evidence only; pending separate independent review. This is a
bounded implementation within existing W10-S4, not a new completion-map slice
or completion of S4, BT-05, W10, or the October launch gate.

Base: `bb06354c597336dcff7ae963b5d2605ee14186cc`.
Founder Decisions remain unchanged (SHA-256
`78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f`).
Authority: FD-W10-002 disabled-first non-production implementation and the
owner's bounded `w10-stripe-signature-verifier-authority.md` package.
Only the new verifier, its tests, and this evidence file belong to this candidate.

## Actual implementation and protocol

`reserved/billing/stripe_signature_verifier.py` provides
`verify_stripe_signature(raw_body, signature_header, signing_keys, *, now)`.
It calculates HMAC-SHA256 over the original timestamp bytes, a period, and
the unchanged raw body; it compares binary digests with `hmac.compare_digest`.
Only v1 signatures contribute. Every bounded key/signature pair is compared,
without an early successful-match exit. Multiple v1 signatures and explicit
overlapping keys support a local rotation check.

Protocol references, checked 4 September 2026:
[Stripe manual signature verification](https://docs.stripe.com/webhooks#verify-signature)
and [raw-body signature troubleshooting](https://docs.stripe.com/webhooks/signature).
Stripe recommends its libraries and documents this manual protocol. No SDK,
endpoint or provider interaction is added here.

The return value is a plain boolean for this call. True means only that these
bytes match at least one supplied key and this local freshness rule. It does
not establish that a supplied key belongs to Stripe or that trusted endpoint
configuration, account, owner, mode, subscription or API-version checks exist.

## Deliberately conservative local input rules

- Body: exact `bytes`, at most 1,048,576 bytes; empty and non-JSON bodies are
  allowed by this cryptographic layer.
- Header: exact printable-ASCII `str`, 1 through 4,096 characters; at most
  32 comma-separated parts and eight v1 signatures.
- Keys: exact tuple of one through three exact `bytes` values, each 1 through
  512 bytes. These are explicit call inputs, never discovered from files,
  environment, settings, credentials or a provider.
- Timestamp: exactly one `t` element, one through 16 ASCII decimal digits.
  Leading zeros are signed as received, not converted back into another string.
- Known v1 elements must each contain exactly 64 hexadecimal characters;
  malformed v1 is refused even alongside a valid signature. Duplicate equal or
  conflicting timestamps are refused. Uppercase hexadecimal is accepted.
- Prefixes are exact `t` and `v1`; there is no whitespace normalization.
  Other schemes/elements are ignored and cannot authenticate a request.
- `now`: explicitly supplied trusted exact integer Unix seconds in
  0 through 9,999,999,999,999,999. Booleans and type subclasses are refused.
  Signed timestamp age must be 0 through 300 seconds inclusive; any future
  timestamp is refused. There is no adjustable tolerance or zero/off switch.

These size/count bounds and zero future allowance are engineering constraints,
not claims about Stripe provider limits or a newly accepted customer policy.
All admission checks precede HMAC construction. Work is bounded to at most
three body hashes and 24 digest comparisons. This is not a request rate limiter.

## Synthetic verification and observable diagnostics

Tests independently compose HMAC from SHA-256 inner/outer pads rather than
calling the production HMAC helper. That reference is checked against the first
two published [RFC 4231 known-answer cases](https://www.rfc-editor.org/rfc/rfc4231.html).
A literal synthetic Stripe-format expected MAC was independently cross-checked
once with local OpenSSL and frozen in the test; tests do not invoke OpenSSL.
All exercised keys and payloads are synthetic, never provider credentials or
customer data. No call input or derived key fingerprint is recorded here.

Coverage includes exact signed bytes (whitespace, newline, BOM and encodings),
timestamp spelling, wrong keys/schemes, rotation, malformed/duplicate fields,
freshness equality and future boundaries, numeric extremes, exact types,
hostile conversion methods, resource boundaries, and refusal before expensive
work. Valid signed non-JSON bytes and repeated valid delivery both succeed:
this explicitly demonstrates that neither event admission nor replay prevention
is supplied. Captured logs/stdout/stderr remain empty for exercised success and
failure cases; failure results have only the representation `False`. Invalid
supported call inputs do not raise or echo input values. Ordinary Python call
signature errors, such as an unsupported tolerance keyword, are not a bypass.

The module retains no inputs in global state, returns no input-bearing object,
and has no storage/logging/JSON/clock/ingress dependencies or runtime consumer.
Ordinary local variables and caller-owned inputs still exist in Python memory.
No secure memory erasure, hostile in-process isolation, traceback-local secrecy,
or total constant-time parsing/execution guarantee is asserted.

## Test disposition

The focused verifier suite contains 71 passing tests. The affected matrix is:

```text
tests/test_w10_stripe_signature_verifier.py
tests/test_w10_stripe_disabled_first_contract.py
tests/test_w10_event_inbox_contract.py
tests/test_w10_runtime_entitlement_admission.py
tests/test_w10_paid_access_guard.py
tests/test_w10_billing_threat_model.py
```

Actual candidate result: **335 passed, 1 failed**. The failure is
`test_w10_paid_access_guard.py::test_candidate_is_confined_to_exact_three_owned_paths_and_base`:
its historical dirty-worktree path allowance rejects this separately authorized
new three-file package. It remains unmodified and is not marked skipped or
expected-failing. The failure is not reported as a passing gate. No full
repository gate, live provider, production deployment or external/human
acceptance is established by these checks.

## Remaining boundaries

Existing S4A, S3B, S3C, S5D and threat-model files remain unchanged. No JSON parse,
provider-neutral admission, event inbox write, entitlement proof/handle or paid
access is produced. There is no ingress or activation; the offline function is
not a runtime paid-access guard. Trusted endpoint/key configuration,
verify-before-parse wiring, owner/account/mode/API-version/subscription checks,
durable atomic inbox admission, replay/order/reconciliation controls and
provider lifecycle testing remain unresolved. No provider, privacy, legal,
human acceptance or launch blocker is closed by this candidate.
