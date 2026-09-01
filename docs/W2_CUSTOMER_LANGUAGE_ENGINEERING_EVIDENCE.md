# W2 customer-language engineering evidence

Evidence date: 1 September 2026. This is an uncommitted engineering
presentation candidate. It is not representative-customer validation, UX or
W2 completion, launch readiness, assurance, or Control Plane authority.

## Identity and bounded scope

- Worktree: `/Users/edwinabatenin/Documents/Codex/2026-08-11/referenced-chatgpt-conversation-this-is-an/codex-cli-w2-ux`
- Branch: `codex-cli/ux-w2-customer-language`
- Starting and ending HEAD: `e4a561247fd616f9cab787fbe2b3369f1b439f47`
- Exactly four authorised untracked candidate paths; nothing staged or committed
- No network, installation, production access, persistence/API/route wiring,
  payment action, merge, push, deployment or release

The customer service now defines a self-contained immutable presentation-input
contract. It imports no engine module and contains no conversion from internal
objects. The only conversion used for engineering tests is a test-local copy
adapter in `tests/test_w2_customer_language_contract.py`. It establishes no
production integration boundary.

## Independent finding and correction 2

Independent pinned-environment verification reported that the focused plus
directly consumed tests passed before correction 2. The full suite then had one
failure only:

`tests/test_internal_tax_boundary.py::test_internal_annual_components_are_not_imported_by_customer_layers`

The cause was the customer service importing and naming a prohibited internal
contract. Correction 2 removes all `reserved.engines` imports and all boundary
markers from the service. It replaces them with strict local dataclasses and
enums for evidence class, annual liability, three obligation kinds, four
adjustment kinds, funding class/appropriate amount, and claim state. Unknown or
incoherent types, duplicate kinds, unsupported versions, and malformed money
fail the whole view closed.

## Focused funding-coherence correction

Independent review then found that GAP and SURPLUS accepted an exact zero
amount and could therefore render contradictory customer language. The input
contract now requires GAP and SURPLUS to carry a strictly positive exact-penny
amount. Zero GAP and zero SURPLUS fail the whole presentation closed. EXACT
continues to require `funding_amount=None`, and any amount supplied for EXACT
continues to fail closed. Focused regressions preserve positive exact-penny GAP
and SURPLUS presentation and the existing EXACT contract. No template change
was required.

## Current file identities

| Path | SHA-256 |
|---|---|
| `reserved/services/w2_customer_language.py` | `ad7f47346d81a50d9a7d8cb15a22d1c9370cf67a8101e05ce3ecb2ac90baa540` |
| `reserved/templates/v2/_w2_cash_obligations.html` | `1ca9be98baf004a49114dd41f2247fbb88b87afd2628cac23466c222556aa24b` |
| `tests/test_w2_customer_language_contract.py` | `cb099324a3e022ed99f2b6e1869e3a924eecb674805b724a70b702e7c1812894` |
| `docs/W2_CUSTOMER_LANGUAGE_ENGINEERING_EVIDENCE.md` | Self-identity is recorded in the completion response because embedding it would change it. |

Recalculate all final identities with:

```sh
shasum -a 256 reserved/services/w2_customer_language.py reserved/templates/v2/_w2_cash_obligations.html tests/test_w2_customer_language_contract.py docs/W2_CUSTOMER_LANGUAGE_ENGINEERING_EVIDENCE.md
```

## Fresh offline verification

Syntax and whitespace:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m py_compile reserved/services/w2_customer_language.py tests/test_w2_customer_language_contract.py
git diff --check
```

Observed: both exited 0; two files compiled, zero syntax failures, and zero
whitespace errors. Combined correction check completed in 0.2 seconds.

The exact existing customer-layer boundary function was loaded without pytest
collection and invoked directly:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import runpy, sys, types
sys.modules['pytest'] = types.ModuleType('pytest')
checks = runpy.run_path('tests/test_internal_tax_boundary.py')
checks['test_internal_annual_components_are_not_imported_by_customer_layers']()
PY
```

Observed: 1/1 boundary scan passed in 0.1 seconds.

A dependency-free harness instantiated the new self-contained safe input and
covered three fixed obligation labels; unknown kinds; NaN, infinite and
negative values in annual, obligation, adjustment and funding families;
wrong enum representations; incoherent exact-funding amounts; duplicate kinds;
and exact-zero gap behavior. Observed: 21/21 passed in 0.2 seconds.

Repository-root import discovery resolved both package-qualified fixture
modules to this worktree. Actual focused test collection and Jinja rendering
remain part of pinned-environment verification.

The local pytest attempt was:

```sh
PYTHONDONTWRITEBYTECODE=1 /usr/bin/time -p python3 -m pytest -q tests/test_w2_customer_language_contract.py tests/test_internal_tax_boundary.py
```

It stopped before collection with `No module named pytest`; zero tests were
collected, the runner invocation failed, and real elapsed time was 0.01
seconds. No dependency was installed or downloaded.

## Independent pinned-environment verification

After correction 2, the owning Codex reviewer used the repository's existing
offline pinned environment with bytecode generation disabled. No dependency
was installed and no network access was used.

After the focused funding-coherence correction, the focused contract,
internal-boundary, directly consumed S1–S6, customer-language and
money-movement verification was rerun:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/edwinabatenin/Documents/Codex/2026-08-11/referenced-chatgpt-conversation-this-is-an/reserved-w2-poa/.venv-w2/bin/python -m pytest -p no:cacheprovider -q tests/test_w2_customer_language_contract.py tests/test_internal_tax_boundary.py tests/test_payments_on_account.py tests/test_sa_account_reconciliation.py tests/test_cash_obligation_reconciliation.py tests/test_poa_reduction_guardrail.py tests/test_cash_funding_position.py tests/test_annual_to_cash_integration.py tests/test_customer_language.py tests/test_money_movement_boundary.py
```

Observed: 284/284 collected tests passed.

Complete repository regression:

```sh
PYTHONDONTWRITEBYTECODE=1 /Users/edwinabatenin/Documents/Codex/2026-08-11/referenced-chatgpt-conversation-this-is-an/reserved-w2-poa/.venv-w2/bin/python -m pytest -p no:cacheprovider -q
```

Observed: 1,965/1,965 collected tests passed; zero failures or errors.

Final correction audit confirmed the branch and HEAD were unchanged, nothing
was staged, there were exactly four untracked candidate paths, and there were
no `__pycache__`, `.pyc`, or `.pyo` artifacts. It also found an ignored
`.pytest_cache` directory created at 02:06 and last modified at 02:18 on
1 September 2026, hours before this correction verification. Both correction
runs used `-p no:cacheprovider` and did not modify it. The exact allowed-path
rule prevented deleting or otherwise touching that pre-existing fifth path, so
the requested absolute no-cache confirmation remains a bounded issue.

The reviewer also inspected the exact four-path candidate, confirmed the
customer service and template contain no prohibited internal marker or engine
import, confirmed the conversion remains test-only, confirmed HEAD is
unchanged and nothing is staged or committed, and recalculated the final file
identities. These results support an engineering review-ready candidate only;
they do not supply representative-customer validation, UX approval, a
production integration boundary, W2 completion, launch readiness or assurance.
