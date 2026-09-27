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
HEAD = "85e1250f53180bb3c1aff111c17101b9e59df080"
TREE = "89a96da31b7a5dbe9bf55c01e875a0d611829e01"
S2D_SOURCE = "1d70e550f685b9c1a4636caf3be75debce500219"
S2D_INTEGRATED = "509c5360d453e23a0732e4e9d4637385eef20ef6"
S5C_PRODUCT = "3c63e64e478957ce04ee1154363c2eae94b82b30"
S5C_EVIDENCE = "e3959964ca08bd5afb6f75feab4ec0fdc83a9423"
CURRENT_ROUTES_COMMIT = "c5e560045ed3d62f02c894e931464c3d7294e99f"
PAYE_V2_COMMIT = "f29a5a8d4acde639fb108f8f9eeaaa833b59dc4b"
PAYE_V2_SHA256 = "be6247e5f9aa91cfbdc3a4d028fbf4b3c4911eaf98dcd1f7b383b28998838236"
MTD_V2_COMMIT = "730db03e9d952a43df2f6d7b638b5a893600ec89"
CURRENT_V2_COMMIT = "318fe2dabcef359dd4066fc207ad8a07395bbefd"
CURRENT_V2_SHA256 = "e2940b780b73fe8e583142fc35cbef53c983f2a0abdb2271bfd90e76e5ac6d16"
MTD_V2_SHA256 = "15b0893514d4e6a5daab935d602aa1d2aa899617f401ed7dbabc704ab91ef563"

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
        "historical_at_cutoff",
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
        CURRENT_V2_COMMIT,
        CURRENT_V2_SHA256,
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
    "SRC-20": (
        "docs/W10_S2D_BILLING_ACCOUNT_RECOVERY_CONTRACT.md",
        S2D_INTEGRATED,
        "214e6fab5dcea9776faa8dc1cb425cbcd622698b8d62d1e0b710e11ec859f445",
        "historical_at_cutoff",
    ),
    "SRC-21": (
        "reserved/billing/billing_account_recovery_contract.py",
        S2D_INTEGRATED,
        "b3bfc4501bdb3631bd87c9dc4aea0984b899fdd3afb535f1414cedd721f4ae06",
        "live",
    ),
    "SRC-22": (
        "tests/test_w10_billing_account_recovery_contract.py",
        S2D_INTEGRATED,
        "7220d1d13b362d9c0c83d3e1ee37baae1fe83dc9bf3950605b919ff2d76213ee",
        "historical_at_cutoff",
    ),
    "SRC-23": (
        "docs/W10_S5C_INTERNAL_ROUTE_HARDENING_EVIDENCE.md",
        S5C_EVIDENCE,
        "221b244e687611dfa3e55e67051cb9ffab59ef6fcd9f02d8c5c865611439d1f5",
        "historical_at_cutoff",
    ),
    "SRC-24": (
        "reserved/web/routes.py",
        CURRENT_ROUTES_COMMIT,
        "cbac0af6c8e7fa7ef43017ba54dab0186330b556a6c9dd946e8cfcbd3fa0e9fd",
        "live",
    ),
    "SRC-25": (
        "tests/test_w10_internal_route_hardening.py",
        S5C_PRODUCT,
        "20a754059b817eb33e5c83ae3edbe551c92c2bafbbbeeca39ed2c709900db3c8",
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
    return register_from_text(text)


def register_from_text(text: str):
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


def is_ancestor(commit: str, descendant: str = HEAD) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, descendant],
        cwd=ROOT,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


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


def test_exact_s2d_and_s5c_checkpoint_integration_topology_is_not_flattened():
    data = register()
    assert data["accepted_package_topology"] == {
        "W10-S2D": {
            "source_checkpoint_commit": S2D_SOURCE,
            "integrated_commit": S2D_INTEGRATED,
            "relationship": (
                "parallel_reviewed_source_checkpoint_with_exact_package_blobs_"
                "integrated_at_integrated_commit"
            ),
        },
        "W10-S5C": {
            "product_checkpoint_commit": S5C_PRODUCT,
            "evidence_checkpoint_commit": S5C_EVIDENCE,
            "relationship": (
                "product_then_evidence_ancestors_preserved_by_repository_head_merge"
            ),
        },
    }
    assert not is_ancestor(S2D_SOURCE)
    assert is_ancestor(S2D_INTEGRATED)
    assert is_ancestor(S5C_PRODUCT)
    assert is_ancestor(S5C_EVIDENCE)

    s2d_paths = (
        "docs/W10_S2D_BILLING_ACCOUNT_RECOVERY_CONTRACT.md",
        "reserved/billing/billing_account_recovery_contract.py",
        "tests/test_w10_billing_account_recovery_contract.py",
    )
    for path in s2d_paths:
        assert git_blob_sha256(S2D_SOURCE, path) == git_blob_sha256(
            S2D_INTEGRATED, path
        )

    # A substituted topology cannot inherit the reviewed checkpoint's
    # authority merely by naming that checkpoint elsewhere in the register.
    assert S2D_INTEGRATED != S5C_PRODUCT
    assert not is_ancestor(S2D_SOURCE, S2D_INTEGRATED)


def assert_exact_source_register(data):
    sources = {
        item["id"]: (
            item["path"],
            item["accepted_commit"],
            item["sha256"],
            item["binding"],
        )
        for item in data["sources"]
    }
    assert sources == EXPECTED_SOURCES

    for source_id, (path, accepted_commit, expected_hash, binding) in sources.items():
        # MTD v2 and legacy routes have independent accepted live anchors;
        # neither is relabelled as assurance from the other's checkpoint.
        descendant = (CURRENT_V2_COMMIT if source_id == "SRC-16" else CURRENT_ROUTES_COMMIT) if binding == "live" else HEAD
        assert is_ancestor(
            accepted_commit, descendant
        ), f"non-ancestor evidence source: {source_id}"
        if binding == "live":
            assert is_ancestor(descendant, "HEAD")
            assert_git_blob_sha256(accepted_commit, path, expected_hash)
        actual_hash = (
            hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            if binding == "live"
            else git_blob_sha256(accepted_commit, path)
        )
        assert actual_hash == expected_hash, f"stale evidence source: {source_id} {path}"


def test_exact_source_commit_hash_and_binding_register_is_not_substitutable():
    assert_exact_source_register(register())


def test_mtd_live_register_rejects_substituted_hash_commit_and_binding():
    for field, value in (
        ("sha256", "0" * 64),
        ("sha256", "dd4bcc1ec49793065da525fefd26709522ce12f5560fd3ee6af7b72ca27ae228"),
        ("sha256", PAYE_V2_SHA256),
        ("accepted_commit", S5C_PRODUCT),
        ("accepted_commit", CURRENT_ROUTES_COMMIT),
        ("accepted_commit", PAYE_V2_COMMIT),
        ("binding", "historical_at_cutoff"),
    ):
        changed = register()
        next(item for item in changed["sources"] if item["id"] == "SRC-16")[field] = value
        try:
            assert_exact_source_register(changed)
        except AssertionError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"substituted MTD source {field} was accepted")


def test_mtd_paid_boundary_is_the_only_register_delta_from_prior_paye_binding():
    previous = register_from_text(subprocess.run(
        ["git", "show", "6bba5575a69eaa3f60d23c9afa5cfd1b77fa4068:docs/W10_S7A_BILLING_THREAT_MODEL.md"],
        cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    ).stdout)
    current = register()
    row = next(item for item in current["sources"] if item["id"] == "SRC-16")
    assert row["accepted_commit"] == CURRENT_V2_COMMIT
    assert row["sha256"] == EXPECTED_SOURCES["SRC-16"][2]
    row.update(
        accepted_commit="6f7ae44c4a037431b58ec0d8e5c4016278fa8b6a",
        sha256="9798dc5d489f4cb1e830dd444c1d40946588409607ad71f6c05b75b975247dc6",
    )
    assert current == previous  # Every other source, topology, threat and gate is unchanged.


def test_valid_historical_pairs_cannot_substitute_for_current_or_legacy_source():
    for source_id, commit, digest in (
        ("SRC-16", PAYE_V2_COMMIT, PAYE_V2_SHA256),
        ("SRC-16", S5C_PRODUCT, "dd4bcc1ec49793065da525fefd26709522ce12f5560fd3ee6af7b72ca27ae228"),
        ("SRC-24", MTD_V2_COMMIT, EXPECTED_SOURCES["SRC-24"][2]),
    ):
        changed = register()
        row = next(item for item in changed["sources"] if item["id"] == source_id)
        # Each pair really identifies that path's blob, but it is not its approved anchor.
        assert_git_blob_sha256(commit, row["path"], digest)
        row.update(accepted_commit=commit, sha256=digest)
        try:
            assert_exact_source_register(changed)
        except AssertionError:
            pass
        else:  # pragma: no cover
            raise AssertionError("a genuine but wrong source checkpoint was accepted")


def test_live_routes_binding_does_not_rewrite_historical_s5c_provenance():
    path, accepted_commit, expected_hash, binding = EXPECTED_SOURCES["SRC-24"]
    historical_hash = (
        "f1d8f6ea3730c8962899a0ffa4d7a78b8c8791693ca03c0d19e0feb8cec42bed"
    )

    assert accepted_commit == CURRENT_ROUTES_COMMIT
    assert binding == "live"
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected_hash
    assert git_blob_sha256(S5C_PRODUCT, path) == historical_hash
    assert expected_hash != historical_hash


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


def test_mtd_live_v2_preserves_distinct_historical_paye_s5c_and_preview_blobs():
    path = "reserved/web/v2.py"
    expected = EXPECTED_SOURCES["SRC-16"][2]
    old_preview_commit = "46e2141c421fa80e39b60cd5b6bb955f44dfd863"

    historical_hash = "dd4bcc1ec49793065da525fefd26709522ce12f5560fd3ee6af7b72ca27ae228"
    assert EXPECTED_SOURCES["SRC-16"][1] == CURRENT_V2_COMMIT
    assert_git_blob_sha256(S5C_PRODUCT, path, historical_hash)
    assert historical_hash != expected
    assert_git_blob_sha256(PAYE_V2_COMMIT, path, PAYE_V2_SHA256)
    assert_git_blob_sha256(MTD_V2_COMMIT, path, MTD_V2_SHA256)
    assert_git_blob_sha256(CURRENT_V2_COMMIT, path, expected)
    assert PAYE_V2_SHA256 not in (historical_hash, expected)
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
    assert git_blob_sha256(old_preview_commit, path) != expected
    assert is_ancestor(S5C_PRODUCT, PAYE_V2_COMMIT)
    assert is_ancestor(CURRENT_ROUTES_COMMIT, PAYE_V2_COMMIT)
    assert is_ancestor(PAYE_V2_COMMIT, MTD_V2_COMMIT)
    assert_git_blob_sha256(old_preview_commit, path, "d91434e2fcf804c74a4154716cab5b1f4ac1642b8f3c90f895a7cf23428b0ca0")
    for commit, digest in ((S5C_PRODUCT, expected), (PAYE_V2_COMMIT, historical_hash),
                           (PAYE_V2_COMMIT, expected), (MTD_V2_COMMIT, PAYE_V2_SHA256),
                           (MTD_V2_COMMIT, expected), (CURRENT_V2_COMMIT, MTD_V2_SHA256)):
        try:
            assert_git_blob_sha256(commit, path, digest)
        except AssertionError:
            pass
        else:  # pragma: no cover
            raise AssertionError("historical and live v2 source identities were interchangeable")

    try:
        assert_git_blob_sha256(old_preview_commit, path, expected)
    except AssertionError:
        pass
    else:  # pragma: no cover - explicit negative-control failure path
        raise AssertionError("the old preview commit was accepted for current v2.py")


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


def test_reconciliation_changes_only_the_three_authorised_threat_rows():
    previous_text = subprocess.run(
        ["git", "show", f"{HEAD}:docs/W10_S7A_BILLING_THREAT_MODEL.md"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout
    previous = {
        item["id"]: item for item in register_from_text(previous_text)["threats"]
    }
    current = {item["id"]: item for item in register()["threats"]}
    assert {
        threat_id for threat_id in current if current[threat_id] != previous[threat_id]
    } == {"BT-04", "BT-08", "BT-20"}


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
    assert by_id["BT-04"]["control_strength"] == (
        "implemented_owner_bound_recovery_decision_contract_without_runtime_auth_"
        "repository_or_provider_session"
    )
    assert by_id["BT-08"]["control_strength"] == (
        "implemented_owner_mapping_decision_contract_without_durable_mapping_or_"
        "authenticated_adapter"
    )
    assert by_id["BT-20"]["control_strength"] == (
        "implemented_five_route_legacy_internal_hardening_without_paid_entitlement_gate"
    )
    assert "portal/recovery remains disabled" in by_id["BT-04"][
        "current_fail_closed_state"
    ]
    assert "Q2 remains unanswered" in by_id["BT-20"]["current_fail_closed_state"]
    assert "No checkout is offered" in by_id["BT-18"]["current_fail_closed_state"]
    assert "No billing provider SDK" in by_id["BT-21"]["current_fail_closed_state"]


def test_reconciled_rows_bind_exact_new_evidence_and_preserved_open_gaps():
    by_id = {item["id"]: item for item in register()["threats"]}
    assert {
        threat_id: (
            row["current_evidence"],
            row["exact_missing_evidence"],
        )
        for threat_id, row in by_id.items()
        if threat_id in {"BT-04", "BT-08", "BT-20"}
    } == {
        "BT-04": (
            ["SRC-06", "SRC-08", "SRC-09", "SRC-10", "SRC-20", "SRC-21", "SRC-22"],
            [
                "authenticated_reserved_owner_adapter",
                "durable_unique_owner_to_billing_account_mapping",
                "atomic_freshness_replay_idempotency_and_crash_recovery",
                "fixed_allowlisted_return_target_and_short_lived_provider_session_adapter",
                "support_least_privilege_and_identity_recovery_evidence",
                "target_cross_owner_email_collision_session_swap_and_return_integrity_tests",
            ],
        ),
        "BT-08": (
            [
                "SRC-06",
                "SRC-08",
                "SRC-10",
                "SRC-17",
                "SRC-18",
                "SRC-20",
                "SRC-21",
                "SRC-22",
            ],
            [
                "durable_unique_owner_mapping_schema_migration_and_authenticated_repository_adapter",
                "foreign_key_or_equivalent_owner_integrity_and_atomic_compare_and_set",
                "runtime_no_email_lookup_no_transfer_merge_or_delegation_enforcement",
                "target_cross_owner_enumeration_deletion_recreation_and_support_misuse_tests",
            ],
        ),
        "BT-20": (
            [
                "SRC-06",
                "SRC-10",
                "SRC-11",
                "SRC-14",
                "SRC-15",
                "SRC-16",
                "SRC-23",
                "SRC-24",
                "SRC-25",
            ],
            [
                "answered_Q2_against_accepted_S5A_inventory",
                "central_server_side_default_deny_entitlement_guard_on_every_approved_paid_surface",
                "refreshed_post_Q2_route_inventory_and_all_method_direct_url_api_content_type_feature_flag_tests",
                "admin_customer_separation_and_target_bypass_review",
            ],
        ),
    }


def test_w9_is_referenced_as_dependency_without_copying_general_registers():
    text = DOCUMENT.read_text(encoding="utf-8")
    assert "does not reproduce, W9's general" in text
    assert '"w9_general_model_reproduced": false' in text
    assert not re.search(r"^### FLOW-\d+", text, flags=re.MULTILINE)
    assert not re.search(r"^### TH-\d+", text, flags=re.MULTILINE)


def test_narrative_preserves_historical_cutoff_and_current_no_assurance_boundary():
    text = " ".join(DOCUMENT.read_text(encoding="utf-8").split())
    required = (
        "not security assurance, launch assurance, provider acceptance or activation",
        "Q1** (refund promise/full-refund access)",
        "Q2** (exact paid surface)",
        "Q3** (verified post-settlement loss/restoration consequence)",
        "VAT/invoice treatment and owner-bound no-transfer recovery remain specialist gates",
        "changes no runtime and closes no row",
        "did not answer Q1, Q2 or Q3",
        "does not select a datastore",
        "did not implement or expose checkout, portal, webhook, billing recovery, refund, admin, entitlement or paid-route behavior",
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


def test_current_full_withdrawal_reconciliation_narrows_only_open_threats():
    text = " ".join(DOCUMENT.read_text(encoding="utf-8").split())
    for phrase in (
        "Post-full-withdrawal runtime reconciliation",
        "d471704ed4beaf0d663a1a88dbf6f38b9402c14d",
        "f772c39d481dbd01bbd18cb9c9ecc2b10527170f",
        "Every BT/BG row remains `open_not_security_or_launch_assurance`",
        "BT-06 / BG-06",
        "BT-07 / BG-07",
        "BT-09 / BG-09 and BT-10 / BG-10",
        "BT-12 / BG-12",
        "BT-13 / BG-13",
        "BT-20 / BG-20",
        "denies all **28** settled paid routes",
        "exactly **27** non-paid routes",
        "Restoration is not implemented",
        "No restoration capability or provider-observed entitlement authority is claimed",
    ):
        assert phrase in text


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
