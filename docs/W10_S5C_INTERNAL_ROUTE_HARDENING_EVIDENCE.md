# W10-S5C internal and legacy route hardening evidence

## Status and authority boundary

**Evidence cut-off:** 4 September 2026

**Accepted product checkpoint:**
`3c63e64e478957ce04ee1154363c2eae94b82b30`

**Accepted product tree:**
`ac3eb6f3028ef2e60bbd1543c1ee92f94655a0b7`

**Product disposition:** independently reviewed, accepted and integrated.

**This document:** evidence-refresh candidate requiring independent review and
integration. It changes no product route, guard, template or runtime behavior.

The accepted S5B reconciliation, not Founder Q2, authorised this bounded
fail-closed prerequisite. S5C removes legacy/internal bypasses without deciding
which authenticated customer product surfaces are paid. The prerequisite route
hardening is implemented. The paid-boundary decision and paid-entitlement
enforcement remain **not started**, and W10-S5 remains incomplete.

## Exact product checkpoint

The accepted product commit changed exactly these six paths:

| Path | SHA-256 | Accepted effect |
|---|---|---|
| `reserved/web/routes.py` | `f1d8f6ea3730c8962899a0ffa4d7a78b8c8791693ca03c0d19e0feb8cec42bed` | Legacy and internal route treatment only. |
| `reserved/web/v2.py` | `dd4bcc1ec49793065da525fefd26709522ce12f5560fd3ee6af7b72ca27ae228` | Production-only sandbox checklist fail-close using the existing production authority. |
| `tests/test_auth.py` | `5dd2284eeb57dbed40119936ada5bde9c3902b21d0c0bf44cb61e55275d7b974` | Canonical authenticated settings expectations. |
| `tests/test_tax_year_context.py` | `f01625359c365ca0085064e264d747e6d9d4007db0c6a34281f7666fff1d37fd` | Canonical authenticated settings tax-year coverage. |
| `tests/test_unsupported_plan_rendering.py` | `5e2eae15e80a876a17bd0339526a798def1c238fbf84457178822710ef196c49` | Retired legacy calculation fail-close coverage. |
| `tests/test_w10_internal_route_hardening.py` | `20a754059b817eb33e5c83ae3edbe551c92c2bafbbbeeca39ed2c709900db3c8` | Focused hostile route/security checks. |

Founder routes were not edited. `web.capital_gains` remained byte-stable at
the function level and hard-404. No billing, entitlement, provider, HICBC,
database, persistence, credential, configuration or activation path changed.

## Machine-checkable checkpoint

<!-- W10-S5C-EVIDENCE-BEGIN -->
```json
{
  "schema_version": "W10-S5C/2026-09-04/v1",
  "accepted_product_commit": "3c63e64e478957ce04ee1154363c2eae94b82b30",
  "accepted_product_tree": "ac3eb6f3028ef2e60bbd1543c1ee92f94655a0b7",
  "accepted_product_disposition": "independently_reviewed_accepted_and_integrated",
  "evidence_refresh_status": "candidate_requires_independent_review",
  "s5_status": "incomplete_prerequisite_route_hardening_implemented",
  "paid_boundary_status": "unresolved_existing_s5a_founder_question",
  "paid_entitlement_enforcement_status": "not_started",
  "product_changed_paths_sha256": {
    "reserved/web/routes.py": "f1d8f6ea3730c8962899a0ffa4d7a78b8c8791693ca03c0d19e0feb8cec42bed",
    "reserved/web/v2.py": "dd4bcc1ec49793065da525fefd26709522ce12f5560fd3ee6af7b72ca27ae228",
    "tests/test_auth.py": "5dd2284eeb57dbed40119936ada5bde9c3902b21d0c0bf44cb61e55275d7b974",
    "tests/test_tax_year_context.py": "f01625359c365ca0085064e264d747e6d9d4007db0c6a34281f7666fff1d37fd",
    "tests/test_unsupported_plan_rendering.py": "5e2eae15e80a876a17bd0339526a798def1c238fbf84457178822710ef196c49",
    "tests/test_w10_internal_route_hardening.py": "20a754059b817eb33e5c83ae3edbe551c92c2bafbbbeeca39ed2c709900db3c8"
  },
  "implemented_route_treatments": {
    "web.calculate": {
      "guard": "always_404",
      "reachability": "valid_csrf_post_is_404_before_profile_calculation_or_render",
      "treatment": "registered_post_hard_404_before_profile_calculation_or_render"
    },
    "web.connections": {
      "guard": "redirect_to_customer_session_guarded_v2_equivalent",
      "reachability": "public_get_redirects_exactly_to_customer_session_guarded_v2_connections",
      "treatment": "get_redirects_exactly_to_customer_session_guarded_v2_connections_with_no_independent_content"
    },
    "web.settings": {
      "guard": "get_redirect_to_customer_session_guarded_v2_equivalent_post_always_404",
      "reachability": "public_get_redirects_exactly_to_customer_session_guarded_v2_settings_and_valid_csrf_post_is_404_before_mutation",
      "treatment": "get_redirects_exactly_to_customer_session_guarded_v2_settings_and_valid_csrf_post_hard_404s_before_mutation"
    },
    "web.tax_assurance": {
      "guard": "always_404",
      "reachability": "get_is_404_before_metadata_read_or_render_in_all_environments_and_auth_states",
      "treatment": "hard_404_before_metadata_read_or_render_in_all_environments_and_auth_states"
    },
    "v2.sandbox_checklist": {
      "guard": "production_404_nonproduction_customer_session",
      "reachability": "production_404_before_customer_auth_or_provider_construction_nonproduction_customer_session_required",
      "treatment": "production_404_before_customer_auth_or_provider_construction_nonproduction_existing_customer_session_guard_preserved"
    }
  },
  "preserved_boundaries": {
    "founder_routes": "unchanged_separate_privileged_session_boundary",
    "capital_gains": "unchanged_hard_404",
    "csrf": "preserved_global_state_changing_request_protection",
    "no_store": "preserved_for_v2_and_founder_prefixes",
    "entitlement": "not_decided_not_enforced",
    "provider_and_billing": "not_activated_not_called_not_modified"
  },
  "verification": {
    "accepted_product_focused": "38_passed",
    "accepted_product_affected": "354_passed",
    "pre_refresh_clean_checkpoint_freshness": "3_expected_failures_for_stale_s5a_s5b_source_guard_and_reachability_evidence",
    "refreshed_evidence_focused": "28_passed",
    "expanded_evidence_affected": "62_passed_with_one_dirty_worktree_scope_sentinel_deselected",
    "unfiltered_candidate_full": "6594_passed_2_expected_dirty_worktree_scope_sentinel_failures_7_subtests_passed",
    "substantive_candidate_full": "6594_passed_2_dirty_worktree_scope_sentinels_deselected_7_subtests_passed",
    "post_commit_unfiltered_expectation": "6596_passed_7_subtests_passed_with_clean_worktree_and_exact_one_generation_history_allowance"
  }
}
```
<!-- W10-S5C-EVIDENCE-END -->

## Route outcomes

- `/calculate` keeps its POST registration and global CSRF path, then hard-404s
  before profile access, calculation or rendering.
- `/connections` contains no legacy product content and redirects exactly to
  authenticated `/v2/connections`.
- `/settings` GET redirects exactly to authenticated `/v2/settings`; legacy
  valid-CSRF POST hard-404s before session or owner-profile mutation.
- `/tax-assurance` hard-404s before local metadata access or rendering in every
  environment and customer-authentication state because no separate staff
  boundary exists.
- `/v2/sandbox-checklist` hard-404s in production before customer-session
  handling or provider-client construction. Non-production retains the existing
  customer-session guard and gains no staff or readiness authority.

## Verification history and expected freshness failures

The accepted product candidate recorded `38 passed` focused hostile S5C tests
and `354 passed` across its affected route/auth/security set. Its pre-refresh
full run recorded `6,588 passed`, `7 subtests passed` and four failures: the
three S5A/S5B freshness/reachability tests correctly rejected the newly changed
route sources, while the W9 dirty-worktree sentinel correctly rejected the
then-uncommitted product candidate. At the subsequent clean accepted product
checkpoint, the focused evidence run had only the three expected S5A/S5B stale
evidence failures. Those failures were the reason for this separate refresh,
not product-test exceptions or waived controls.

The refreshed S5A/S5B evidence suite recorded `28 passed`. The expanded
S5A/S5B/S2C/W9 evidence set recorded `62 passed` with only the W9-S1B
dirty-worktree scope sentinel deselected. The final unfiltered refresh run
recorded `6,594 passed`, `7 subtests passed` and only two expected
dirty-worktree scope-sentinel failures because this authorized evidence package
is intentionally outside the earlier S5C product and W9-S1B path sets. No test
was deselected and no hidden test flag was used for that unfiltered run. With
only those two sentinels deselected for the uncommitted candidate, the full
suite recorded `6,594 passed`, `2 deselected` and `7 subtests passed`. Both
sentinels are expected to pass after this independently reviewed evidence
checkpoint is committed directly on the bound S5C product checkpoint and the
worktree is clean. The exact post-commit expectation is therefore `6,596
passed`, `7 subtests passed`; the W9 history guard permits only this exact
nine-path, one-generation evidence dependency refresh.

## Remaining gate

Founder Q2 in the accepted S5A inventory remains exact and unanswered. S5C
does not determine whether `/v2/`, dashboard, optimisation, transactions,
invoices, review, settings, connections, banking-consent or feature-gated HICBC
customer surfaces require paid entitlement. No server-side entitlement
enforcement has started. W10-S5 is incomplete and this evidence is not launch,
provider, target, privacy, security or billing activation assurance.
