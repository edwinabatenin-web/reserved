# HMRC PAYE Test Support 2.1 tax contract — implementation evidence

Status: **implementation-derived evidence; candidate for independent review**.
Date: **2 September 2026**.

## Boundary implemented

`reserved/providers/hmrc_paye_test_support_tax_contract.py` implements a
dependency-free, network-inert typed boundary for the documented HTTP 201 body
of:

`POST /individual-paye-test-support/sa/{utr}/tax/annual-summary/{taxYear}`

Provider facts are taken only from
`docs/HMRC_PAYE_TEST_SUPPORT_2_1_ENDPOINT_EVIDENCE.md`. The implementation:

- accepts only exact integer status `201` and scenarios `HAPPY_PATH_1` or
  `HAPPY_PATH_2`; omission alone selects `HAPPY_PATH_1`, while explicit null is
  invalid;
- requires the three documented top-level members and both documented members
  of every employment item;
- retains numeric values only as exact built-in `int` or finite `Decimal`, with
  defensive magnitude, digit and scale bounds and no rounding or coercion;
- records optional-field presence separately from the value, preserving the
  distinction between omission and exact zero and rejecting explicit null;
- retains open-schema extensions only as bounded immutable member-name sets at
  all four object layers; extension values are not read, traversed, copied,
  represented or retained;
- uses frozen dataclasses whose constructors validate their own complete state,
  including documented-name exclusion from `unknown_names`; and
- bounds object members, unknown names, member/string lengths, number shapes
  and employment count. Retained names and employer references reject every
  Unicode general-category C character. Empty and ordinary-space employer
  references remain accepted because the provider evidence states no regex or
  minimum length.

The response value retains no UTR. Array position is retained solely as source
shape and conveys no identity, precedence or chronology.

## Tests

Focused tests are in
`tests/test_hmrc_paye_test_support_tax_contract.py`. They cover both scenarios,
default omission and explicit-null rejection; exact status typing; empty,
single and multiple employment arrays; required containers/members; optional
presence and zero; exact decimals and invalid numeric forms; open-schema names
and hostile extension values; unsafe/bounded strings and names; direct
construction, `dataclasses.replace`, copy/deepcopy and pickle; and import/
network/credential isolation.

Executed commands and results:

- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider tests/test_hmrc_paye_test_support_tax_contract.py -q`
  — **39 passed**.
- `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider tests/test_hmrc_individual_tax_contract.py tests/test_hmrc_individual_income_contract.py tests/test_hmrc_individual_employment_contract.py -q`
  — **557 passed**.

No complete repository suite was run; the focused file and smallest relevant
neighbouring HMRC contract matrix passed.

## Limitations and activation gates

This component is a parser/value boundary for synthetic sandbox evidence only.
It does not make an HTTP call, construct a sendable request, handle OAuth or
credentials, persist data, activate an HMRC product, interpret extensions,
map into product engines, or establish that a later read succeeds. It supplies
no pagination, error-body model, named OAuth scope, retry/idempotency rule,
reset/replacement semantics, visibility timing, ordering semantics or
cross-product identity authority.

No provider or sandbox call was made. Subscription/access approval, credential
custody, transport implementation, visibility and re-POST behaviour, reset or
cleanup, cross-API linkage and any activation decision remain hard gates.

This evidence does not claim sandbox verification, provider activation, launch
readiness, assurance or independent review. The owning Codex task must review
the exact diff before acceptance.
