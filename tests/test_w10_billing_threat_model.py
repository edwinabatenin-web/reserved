"""Integrity tests for the evidence-only W10-S7A billing threat model."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "docs" / "W10_S7A_BILLING_THREAT_MODEL.md"
START = "<!-- W10-S7A-REGISTER-BEGIN -->"
END = "<!-- W10-S7A-REGISTER-END -->"
HEAD = "f9412b36adeb75dc7d5d5af56824c87235f28ce7"
TREE = "1b648be16bdc2bc41311f7968f6d402a63d4c8a9"

EXPECTED_SOURCES = {
    "SRC-01": (
        "FOUNDER_DECISIONS.md",
        "10fb93e2e6ab567a72d2370c1603768a7ac04bb5",
        "03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4",
        "historical_at_cutoff",
    ),
    "SRC-02": (
        "docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md",
        HEAD,
        "cd17168c04ed5c3b05044322daae2480973d57220f05c0419f539f6fdf14977d",
        "historical_at_cutoff",
    ),
    "SRC-03": (
        "reserved/billing/contracts.py",
        "9e8f94a9906f0c9d5c85b47223d20c34be499e1c",
        "9c5dce7a81652d58562ca339def95fba7cbb2d1c02f965618ebd8f40bcad202b",
        "live",
    ),
    "SRC-04": (
        "reserved/billing/provider_lifecycle_authority.py",
        "5464bfac7bec6b3456d1895b2355a7e8ce86859b",
        "fc21c3a0f9d8d7eeb9a06bcbf5fc4a418568fe06aa5f65f47c325d8ecfde834a",
        "live",
    ),
    "SRC-05": (
        "reserved/billing/fail_closed_launch_defaults.py",
        "1033c9fbef008dcd33125a0b14e7fb18b8846d19",
        "cd72be19d8180a52f2e09fec56cc3219347059b025ceb3f12086d7d8dde40715",
        "live",
    ),
    "SRC-06": (
        "docs/W10_S2C_POLICY_EVIDENCE_DOSSIER.md",
        "a07348976321df65bbd95c9170c906bcddd5baa5",
        "db31ba2e7c0e51701bc62c6a7b4b489cbde072b5efaf1f09f7c67a5f75fd5dcd",
        "historical_at_cutoff",
    ),
    "SRC-07": (
        "reserved/billing/entitlement_core.py",
        "94bd87f019dc226ec8c73f32515229189500cf06",
        "b46b797614b57047e64f6f6597b1c788b9ab15db90653b07add31b4bbb03cb3b",
        "live",
    ),
    "SRC-08": (
        "reserved/billing/event_inbox_contract.py",
        "5bc29bcb30c95ea7a5a9430104653b366d709eb6",
        "4dc0b6bb8b109854531dc1b9d492255e98dca805822cd5e0257f0fdf9b0ca8ed",
        "live",
    ),
    "SRC-09": (
        "reserved/billing/stripe_disabled_first_contract.py",
        "2ad4a63dd1f10ba38859050b47245c28390667d8",
        "87a84c5ec77f25e12667b5466052b4a84ee6e01a6b075df643202d95aec98638",
        "live",
    ),
    "SRC-10": (
        "docs/W10_S5A_PAID_SURFACE_INVENTORY.md",
        "9c0760192bb2420b90e57ec7313f69bbe52cbf74",
        "abf7b01158993f404d28eb29f7cd62b38f6f3d86b4ebdd3be9174c342bf198f8",
        "historical_at_cutoff",
    ),
    "SRC-11": (
        "docs/W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md",
        "051ae665a0cc94f6e9cdbbc728c621825c7769fe",
        "d1b8a3b836006bba8e688f0c9388b6855f61784a4a0acb18d20a3a215c7b92a1",
        "historical_at_cutoff",
    ),
    "SRC-12": (
        "reserved/services/w10_billing_presentation.py",
        "45ade8e356716b320b0f984cf33882abf505fb7d",
        "2812f2e2bccd968b7286c47c59a1b881f6b6a4b9913250019ff3eb416f2e1c88",
        "live",
    ),
    "SRC-13": (
        "reserved/services/w10_billing_page.py",
        "23d04a6eec09909b1315797adc4fd1aa5ba9bdd0",
        "cbfa21ff44bece691b0049c29dbcd33bc7ae4b15216bdbd3e5a2fd1631bec8b4",
        "live",
    ),
    "SRC-14": (
        "docs/W10_S6C_AUTHENTICATED_PLAN_QUOTE_EVIDENCE.md",
        "3e05fb7f3149ee7030be768909eb6fe4f50e0b75",
        "c424c0ca999ef18568dfc1b86f79d9f0e27af1d05e7f9167ef9de43b344b3bb1",
        "historical_at_cutoff",
    ),
    "SRC-15": (
        "docs/W10_S6D_PLAN_SELECTION_PREVIEW_EVIDENCE.md",
        "46e2141c421fa80e39b60cd5b6bb955f44dfd863",
        "d7306da9e1e163420e345567800c6789d8422619ceaf9b91d925458d0a136790",
        "historical_at_cutoff",
    ),
    "SRC-16": (
        "reserved/web/v2.py",
        "46e2141c421fa80e39b60cd5b6bb955f44dfd863",
        "dd4bcc1ec49793065da525fefd26709522ce12f5560fd3ee6af7b72ca27ae228",
        "live",
    ),
    "SRC-17": (
        "docs/W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md",
        "587828337e01f269320048847b3250a690ce6133",
        "8dd542319b301da6153b5695d3fcfc64f1f30794972d8324967dc1b55880fe92",
        "historical_at_cutoff",
    ),
    "SRC-18": (
        "docs/W9_SECURITY_OPERATIONS_GAP_REGISTER.md",
        "587828337e01f269320048847b3250a690ce6133",
        "4d57107306bf78e5bf32ee2f2de24bf49531abbc1cb2dddf20595ae907893647",
        "historical_at_cutoff",
    ),
    "SRC-19": (
        "docs/W9_SECURITY_DECISION_DOSSIER.md",
        "587828337e01f269320048847b3250a690ce6133",
        "8828333aa53c92899f02df0ca9a64c04b3e7811b51fb3f154a01f2882da7446c",
        "historical_at_cutoff",
    ),
}

EXPECTED_TITLES = (
    "price_plan_or_currency_tamper",
    "promotion_discount_or_partner_offer_tamper",
    "checkout_return_or_session_confusion",
    "customer_portal_or_billing_recovery_confusion",
    "webhook_authenticity_bypass",
    "webhook_replay_duplicate_or_idempotency_failure",
    "event_order_object_or_subscription_substitution",
    "cross_owner_billing_account_mapping",
    "unauthorised_entitlement_grant",
    "entitlement_revocation_recovery_or_concurrency_race",
    "payment_recovery_deadline_extension_or_clock_abuse",
    "refund_state_amount_or_access_ambiguity",
    "dispute_chargeback_or_reversal_consequence_ambiguity",
    "admin_support_correction_or_override_abuse",
    "billing_credentials_signing_secret_or_key_rotation_failure",
    "billing_log_pii_payload_or_secret_leakage",
    "event_inbox_database_integrity_or_concurrency_failure",
    "provider_outage_backlog_or_reconciliation_failure",
    "billing_deletion_retention_legal_hold_or_backup_expiry_failure",
    "direct_url_api_or_route_classification_bypass",
    "unsafe_target_provider_or_production_activation",
)

THREAT_FIELDS = {
    "id",
    "title",
    "assets",
    "attack_or_failure",
    "current_evidence",
    "control_id",
    "implemented_control",
    "control_strength",
    "current_fail_closed_state",
    "gap_id",
    "exact_missing_evidence",
    "closure_owner_slices",
    "status",
}


def register():
    text = DOCUMENT.read_text(encoding="utf-8")
    assert text.count(START) == text.count(END) == 1
    payload = text.split(START, 1)[1].split(END, 1)[0].strip()
    assert payload.startswith("```json\n") and payload.endswith("```")
    return json.loads(payload.removeprefix("```json\n").removesuffix("```").strip())


def git_blob_sha256(commit: str, relative_path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return hashlib.sha256(result.stdout).hexdigest()


def assert_git_blob_sha256(commit: str, relative_path: str, expected_hash: str):
    actual_hash = git_blob_sha256(commit, relative_path)
    assert actual_hash == expected_hash, (
        f"historical source mismatch: {commit}:{relative_path}"
    )


def test_exact_repository_identity_and_non_authority_flags_are_fixed():
    data = register()
    assert data["schema_version"] == "W10-S7A/2026-09-04/v1"
    assert data["repository_head"] == HEAD
    assert data["repository_tree"] == TREE
    assert data["scope"] == "october_subscription_billing_security_privacy_operations_delta"
    assert data["w9_general_model_reproduced"] is False
    assert data["security_assurance"] is False
    assert data["launch_assurance"] is False
    assert data["provider_activation_authority"] is False


def test_exact_source_commit_hash_and_binding_register_is_not_substitutable():
    sources = {
        item["id"]: (
            item["path"],
            item["accepted_commit"],
            item["sha256"],
            item["binding"],
        )
        for item in register()["sources"]
    }
    assert sources == EXPECTED_SOURCES

    for source_id, (path, accepted_commit, expected_hash, binding) in sources.items():
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", accepted_commit, HEAD],
            cwd=ROOT,
            check=False,
        )
        assert ancestor.returncode == 0, f"non-ancestor evidence source: {source_id}"
        actual_hash = (
            hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            if binding == "live"
            else git_blob_sha256(accepted_commit, path)
        )
        assert actual_hash == expected_hash, f"stale evidence source: {source_id} {path}"


def test_historical_binding_survives_descendant_change_and_rejects_wrong_provenance():
    path = "docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md"
    accepted_commit = "5612f7a33f27f09d1fa988f15dfdffbe77a72705"
    accepted_hash = "7af205f420c2cf3a9039fff7aad1af65e55221005231b2fabe3bd99c94f96c4d"

    # The descendant reconciles this mutable map, but cannot rewrite what the
    # earlier evidence package actually reviewed.
    assert_git_blob_sha256(accepted_commit, path, accepted_hash)
    assert git_blob_sha256(HEAD, path) != accepted_hash

    try:
        assert_git_blob_sha256(HEAD, path, accepted_hash)
    except AssertionError:
        pass
    else:  # pragma: no cover - explicit negative-control failure path
        raise AssertionError("a wrong historical source commit was accepted")

    try:
        assert_git_blob_sha256(accepted_commit, path, "0" * 64)
    except AssertionError:
        pass
    else:  # pragma: no cover - explicit negative-control failure path
        raise AssertionError("a wrong historical source digest was accepted")


def test_exact_finite_threat_control_and_gap_denominator():
    data = register()
    expected_ids = [f"BT-{index:02d}" for index in range(1, 22)]
    expected_controls = [f"BC-{index:02d}" for index in range(1, 22)]
    expected_gaps = [f"BG-{index:02d}" for index in range(1, 22)]
    threats = data["threats"]

    assert data["threat_denominator"] == 21
    assert data["threat_ids"] == expected_ids
    assert [item["id"] for item in threats] == expected_ids
    assert [item["control_id"] for item in threats] == expected_controls
    assert [item["gap_id"] for item in threats] == expected_gaps
    assert tuple(item["title"] for item in threats) == EXPECTED_TITLES
    assert len(threats) == 21


def test_every_row_has_exact_machine_fields_evidence_gap_owner_and_open_status():
    data = register()
    source_ids = set(EXPECTED_SOURCES)
    allowed_owners = {
        "W9-S2",
        "W9-S3",
        "W9-S4",
        "W9-S5",
        "W10-S2",
        "W10-S3",
        "W10-S4",
        "W10-S5",
        "W10-S6",
        "W10-S7",
        "W10-S8",
    }
    used_sources = set()
    for threat in data["threats"]:
        assert set(threat) == THREAT_FIELDS
        assert len(threat["assets"]) >= 3
        assert len(threat["attack_or_failure"]) >= 40
        assert len(threat["implemented_control"]) >= 40
        assert len(threat["current_fail_closed_state"]) >= 40
        assert len(threat["exact_missing_evidence"]) >= 3
        assert len(threat["exact_missing_evidence"]) == len(
            set(threat["exact_missing_evidence"])
        )
        assert set(threat["current_evidence"]) <= source_ids
        assert threat["current_evidence"]
        used_sources.update(threat["current_evidence"])
        assert set(threat["closure_owner_slices"]) <= allowed_owners
        assert "W10-S7" in threat["closure_owner_slices"]
        assert threat["status"] == "open_not_security_or_launch_assurance"
    assert used_sources == source_ids


def test_all_required_october_billing_threat_classes_are_explicit():
    titles = {item["title"] for item in register()["threats"]}
    required_fragments = (
        "price_plan",
        "promotion_discount",
        "checkout_return",
        "customer_portal",
        "webhook_authenticity",
        "webhook_replay_duplicate",
        "event_order_object",
        "cross_owner",
        "unauthorised_entitlement_grant",
        "revocation_recovery",
        "payment_recovery_deadline",
        "refund",
        "dispute_chargeback",
        "admin_support",
        "credentials_signing_secret",
        "log_pii_payload",
        "event_inbox_database",
        "outage_backlog",
        "deletion_retention",
        "direct_url_api",
        "target_provider",
    )
    for fragment in required_fragments:
        assert any(fragment in title for title in titles), fragment


def test_q1_q2_q3_and_specialist_gates_remain_exactly_unresolved():
    data = register()
    assert data["founder_questions"] == {
        "Q1": "unanswered_refund_and_confirmed_full_refund_access_consequence",
        "Q2": "unanswered_exact_paid_access_surface",
        "Q3": "unanswered_verified_post_settlement_loss_and_restoration_consequence",
    }
    assert data["specialist_gates_not_new_founder_questions"] == [
        "tax_invoicing_and_additional_vat_presentation",
        "owner_bound_no_transfer_billing_account_recovery",
    ]
    by_id = {item["id"]: item for item in data["threats"]}
    assert "answered_Q1" in by_id["BT-12"]["exact_missing_evidence"]
    assert "answered_Q3" in by_id["BT-13"]["exact_missing_evidence"]
    assert "answered_Q2_against_accepted_S5A_inventory" in (
        by_id["BT-20"]["exact_missing_evidence"]
    )


def test_contract_evidence_is_not_misreported_as_runtime_or_target_control():
    by_id = {item["id"]: item for item in register()["threats"]}
    assert by_id["BT-05"]["control_strength"] == "disabled_provider_edge_contract_only"
    assert by_id["BT-06"]["control_strength"] == "pure_contract_no_durable_deduplication"
    assert by_id["BT-17"]["control_strength"] == "datastore_neutral_contract_no_database"
    assert "auth-only" in by_id["BT-09"]["current_fail_closed_state"]
    assert "blocks launch" in by_id["BT-09"]["current_fail_closed_state"]
    assert "auth-only" in by_id["BT-20"]["current_fail_closed_state"]
    assert "No checkout is offered" in by_id["BT-18"]["current_fail_closed_state"]
    assert "No billing provider SDK" in by_id["BT-21"]["current_fail_closed_state"]


def test_w9_is_referenced_as_dependency_without_copying_general_registers():
    text = DOCUMENT.read_text(encoding="utf-8")
    assert "does not reproduce, W9's general" in text
    assert '"w9_general_model_reproduced": false' in text
    assert not re.search(r"^### FLOW-\d+", text, flags=re.MULTILINE)
    assert not re.search(r"^### TH-\d+", text, flags=re.MULTILINE)


def test_narrative_preserves_no_change_no_assurance_and_no_activation_boundary():
    text = " ".join(DOCUMENT.read_text(encoding="utf-8").split())
    required = (
        "not security assurance, launch assurance, provider acceptance or activation",
        "Q1** (refund promise/full-refund access)",
        "Q2** (exact paid surface)",
        "Q3** (verified post-settlement loss/restoration consequence)",
        "VAT/invoice treatment and owner-bound no-transfer recovery remain specialist gates",
        "changes no runtime and closes no row",
        "does not answer Q1, Q2 or Q3",
        "does not select a datastore",
        "does not implement or expose checkout, portal, webhook, billing recovery, refund, admin, entitlement or paid-route behavior",
        "does not answer Q1, Q2 or Q3, amend Founder Decisions or completion maps",
    )
    for phrase in required:
        assert phrase in text
    forbidden = (
        "W10-S7 is complete",
        "security assurance is complete",
        "Status: launch-ready",
        "Q1 is answered",
        "Q2 is answered",
        "Q3 is answered",
    )
    for phrase in forbidden:
        assert phrase not in text


def test_test_module_is_repository_local_standard_library_plus_pytest_free():
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".", 1)[0])
    assert imports == {
        "__future__",
        "ast",
        "hashlib",
        "json",
        "pathlib",
        "re",
        "subprocess",
    }
