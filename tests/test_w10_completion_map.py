"""Stable structural and provenance checks for the mutable W10 completion map."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MAP_RELATIVE_PATH = "docs/W10_SUBSCRIPTION_BILLING_COMPLETION_MAP.md"
MAP = ROOT / MAP_RELATIVE_PATH
TEXT = MAP.read_text(encoding="utf-8")
W9_MAP = ROOT / "docs/W9_COMPLETION_MAP.md"
W9_TEXT = W9_MAP.read_text(encoding="utf-8")
START = "<!-- W10-COMPLETION-MAP-RECONCILIATION-BEGIN -->"
END = "<!-- W10-COMPLETION-MAP-RECONCILIATION-END -->"

BASE = "fd7f30dcdc3557ef70c9bdfc4b89e046e16c2bd0"
BASE_TREE = "b2edd687819b5b0f95c44f1a68d746a85f7bd9c1"
BASE_PARENTS = (
    "109b5ec6e3ace82d8e41c98ece1baf7553eff039",
)
S2D_S5C_BASE = "85e1250f53180bb3c1aff111c17101b9e59df080"
S2D_S5C_TREE = "89a96da31b7a5dbe9bf55c01e875a0d611829e01"
WRONG_MAP_COMMIT = "81ae02044cccd921d98a0d1fc2360e1c4a983ab1"

EXPECTED_COMPONENTS = {
    "Founder-Decisions-W10-002-003": {
        "accepted_checkpoint": "14d5a253d6993044e026c4b862fa4a18708712da",
        "accepted_tree": "fc86cd3ffbb7279624763307ea2498be78521c84",
        "integration_commit": "10fb93e2e6ab567a72d2370c1603768a7ac04bb5",
        "integration_tree": "fc86cd3ffbb7279624763307ea2498be78521c84",
        "paths": ("FOUNDER_DECISIONS.md",),
    },
    "W10-S2D": {
        "accepted_checkpoint": "1d70e550f685b9c1a4636caf3be75debce500219",
        "accepted_tree": "d6cad612d010baa3a311a8ecd2eabd5f9f37c37e",
        "integration_commit": "509c5360d453e23a0732e4e9d4637385eef20ef6",
        "integration_tree": "f2c35dfaaad2bf408d39b23e84716d25a0794c74",
        "paths": (
            "docs/W10_S2D_BILLING_ACCOUNT_RECOVERY_CONTRACT.md",
            "reserved/billing/billing_account_recovery_contract.py",
            "tests/test_w10_billing_account_recovery_contract.py",
        ),
    },
    "W10-S5C-product": {
        "accepted_checkpoint": "3c63e64e478957ce04ee1154363c2eae94b82b30",
        "accepted_tree": "ac3eb6f3028ef2e60bbd1543c1ee92f94655a0b7",
        "integration_commit": S2D_S5C_BASE,
        "integration_tree": S2D_S5C_TREE,
        "paths": (
            "reserved/web/routes.py",
            "reserved/web/v2.py",
            "tests/test_auth.py",
            "tests/test_tax_year_context.py",
            "tests/test_unsupported_plan_rendering.py",
            "tests/test_w10_internal_route_hardening.py",
        ),
    },
    "W10-S5C-evidence": {
        "accepted_checkpoint": "e3959964ca08bd5afb6f75feab4ec0fdc83a9423",
        "accepted_tree": "6e2705c4948b3b843d034beec05aef36ffb8c8ba",
        "integration_commit": S2D_S5C_BASE,
        "integration_tree": S2D_S5C_TREE,
        "paths": (
            "docs/W10_S5A_PAID_SURFACE_INVENTORY.md",
            "docs/W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md",
            "docs/W10_S5C_INTERNAL_ROUTE_HARDENING_EVIDENCE.md",
            "docs/W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md",
            "docs/W9_SECURITY_DECISION_DOSSIER.md",
            "tests/test_w10_internal_route_reconciliation.py",
            "tests/test_w10_paid_surface_inventory.py",
            "tests/test_w10_s2c_policy_evidence.py",
            "tests/test_w9_security_evidence.py",
        ),
    },
    "W10-S7A": {
        "accepted_checkpoint": "699aba7facddf935b0b71797bca0abf17628dff9",
        "accepted_tree": "24771275bdea2c24bec6768c88f6206677a5bd47",
        "integration_commit": "54a82476939dce8f75af62d73aeb477e11a1260c",
        "integration_tree": "26b1aa6a1302195770534dc41caf099bcdd7cb06",
        "paths": (
            "docs/W10_S7A_BILLING_THREAT_MODEL.md",
            "tests/test_w10_billing_threat_model.py",
        ),
    },
    "W10-S7A-reconciliation": {
        "accepted_checkpoint": "06eec249369cd71c1b6ff8dfaec94bf32b4fbb67",
        "accepted_tree": "f942f27a7aae169c9fb6cbdf4797a80bd3df7288",
        "integration_commit": "1d91526d11b5291d5388c78940682ca02edeb61e",
        "integration_tree": "e2fc725961f816d80eed9e5373d738e5e21a024c",
        "paths": (
            "docs/W10_S7A_BILLING_THREAT_MODEL.md",
            "tests/test_w10_billing_threat_model.py",
        ),
    },
    "W10-S2E": {
        "accepted_checkpoint": "4511e45297dfcae980c606e4bb09b549510ea23f",
        "accepted_tree": "cd6bdf2f66878aa4baecd79d5e7c504dd13a4007",
        "integration_commit": "251deb1c39bbc4f5b4c7c3b1356a380cb0b9df04",
        "integration_tree": "ec382c130c4120fcab8b87a1711c696c0b661015",
        "paths": (
            "docs/W10_S2E_TAX_INVOICE_PREREQUISITE.md",
            "reserved/billing/tax_invoice_prerequisite_contract.py",
            "tests/test_w10_tax_invoice_prerequisite_contract.py",
        ),
    },
    "W9-S3C": {
        "accepted_checkpoint": "c9bdaa6538d68c0c64b2dcde97f224a69c089d30",
        "accepted_tree": "6d851e6010b8c143c57e63aea61afb8911b1bab1",
        "integration_commit": "5f5a948891e1e812a5c74ff6c7266d153bb492fa",
        "integration_tree": "639369d06a8da75e8318bec7933993c26e39ace6",
        "paths": (
            "docs/W9_S3C_PROJECTION_REPOSITORY_ADAPTER.md",
            "reserved/annual_position_projection_repository_adapter.py",
            "tests/test_annual_position_projection_repository_adapter.py",
        ),
    },
    "W10-S4B": {
        "accepted_checkpoint": "e5ba0ed4f5e3832fe4ef58af8009cc17217bc85d",
        "accepted_tree": "d697bf4af962e459f3ce43e146192c82e8d8b1d6",
        "integration_commit": "23f4d3dc742474d3a672388a1ebe99962505b234",
        "integration_tree": "b85207f9c7dd50042206a0aa43391300f69374b6",
        "paths": (
            "docs/W10_S4B_CHECKOUT_INTENT_CONTRACT.md",
            "reserved/billing/checkout_intent_contract.py",
            "tests/test_w10_checkout_intent_contract.py",
        ),
    },
    "W10-S4C": {
        "accepted_checkpoint": "b197c987b96dd9fca6296c41bb002baf74099e55",
        "accepted_tree": "4c43bd2afcfe40d18f58f3ac85e531f81477f7b8",
        "integration_commit": "67b52a66805e9d5c1317330b9f7b1f2a19d4172c",
        "integration_tree": "80406ea9aab57c0a3bebc55752ef60977a9de2b0",
        "paths": (
            "docs/W10_S4C_PORTAL_INTENT_CONTRACT.md",
            "reserved/billing/portal_intent_contract.py",
            "tests/test_w10_portal_intent_contract.py",
        ),
    },
    "W10-S6E": {
        "accepted_checkpoint": "ddd9dd298eb8c495402d06ca4ac921a34d885549",
        "accepted_tree": "83035e65132091bce86ed652a3d2970ada44804c",
        "integration_commit": "11ea4cfea78ae31b633a9ac8d99477eb358e7f3b",
        "integration_tree": "e6dc561505058e45cddb27bab4ad9d3c1605e4f9",
        "paths": (
            "docs/W10_S6E_PAYMENT_RECOVERY_PRESENTATION_EVIDENCE.md",
            "reserved/billing/payment_recovery_presentation.py",
            "tests/test_w10_payment_recovery_presentation.py",
        ),
    },
    "W10-S6F": {
        "accepted_checkpoint": "9c7b5c7b283134a471d5c5d7a720e4c10b1a16a6",
        "accepted_tree": BASE_TREE,
        "integration_commit": BASE,
        "integration_tree": BASE_TREE,
        "paths": (
            "docs/W10_S6F_CANCELLATION_PRESENTATION_EVIDENCE.md",
            "reserved/billing/cancellation_presentation.py",
            "tests/test_w10_cancellation_presentation.py",
        ),
    },
    "W10-S6E-test-scope-correction": {
        "accepted_checkpoint": "cd6f94bc5109d18cb229fa65396bb66677960543",
        "accepted_tree": "3c259ae83571fffbfbc3ba3591eedfdf5b3bb3ce",
        "integration_commit": "8043051a38f367ef66fd63034bc7a4fcbc7c9f3c",
        "integration_tree": "664955b5bc5a5604396a88e7f7bc6355aafc230c",
        "paths": ("tests/test_w10_payment_recovery_presentation.py",),
    },
    "W10-S3A-hardening": {
        "accepted_checkpoint": "b990d514a929c37b3f999137a0e383d05c37f0df",
        "accepted_tree": "78a9f59a238eea1316855ccef1784a2588ffb961",
        "integration_commit": "48a97042fc0e17997bf2d23a4687e79c20b74b9e",
        "integration_tree": "dbed2a8e3803325c952d822ad68477eecf837001",
        "paths": (
            "docs/W10_S3A_ENTITLEMENT_TRANSITION_EVIDENCE.md",
            "reserved/billing/entitlement_core.py",
            "tests/test_w10_entitlement_core.py",
        ),
    },
    "W9-W10-entitlement-evidence-reconciliation": {
        "accepted_checkpoint": "cd3f043e77b724d3f20b520e488b99d8514e5e3d",
        "accepted_tree": "47480505b30bd4fd90ce0ce23fb70587613374f3",
        "integration_commit": "4e1f226e2109257e46e5865fe471564df1758246",
        "integration_tree": "47480505b30bd4fd90ce0ce23fb70587613374f3",
        "paths": (
            "docs/W10_S2B_FAIL_CLOSED_LAUNCH_DEFAULTS.md",
            "docs/W10_S2C_POLICY_EVIDENCE_DOSSIER.md",
            "docs/W10_S2D_BILLING_ACCOUNT_RECOVERY_CONTRACT.md",
            "docs/W10_S4B_CHECKOUT_INTENT_CONTRACT.md",
            "docs/W10_S4C_PORTAL_INTENT_CONTRACT.md",
            "docs/W10_S6E_PAYMENT_RECOVERY_PRESENTATION_EVIDENCE.md",
            "docs/W10_S7A_BILLING_THREAT_MODEL.md",
            "docs/W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md",
            "tests/test_w10_billing_account_recovery_contract.py",
            "tests/test_w10_billing_threat_model.py",
            "tests/test_w10_checkout_intent_contract.py",
            "tests/test_w10_fail_closed_launch_defaults.py",
            "tests/test_w10_payment_recovery_presentation.py",
            "tests/test_w10_portal_intent_contract.py",
            "tests/test_w10_s2c_policy_evidence.py",
            "tests/test_w10_tax_invoice_prerequisite_contract.py",
            "tests/test_w9_security_evidence.py",
        ),
    },
    "W9-evidence-package-history-correction": {
        "accepted_checkpoint": "431a859731bc0b480e47feca643c299abbdfb003",
        "accepted_tree": "9d0588c3d6761c21724b27fcc6ff412e6447f285",
        "integration_commit": "109b5ec6e3ace82d8e41c98ece1baf7553eff039",
        "integration_tree": "9d0588c3d6761c21724b27fcc6ff412e6447f285",
        "paths": ("tests/test_w9_security_evidence.py",),
    },
}

EXPECTED_HISTORICAL_MAP_BINDINGS = (
    {
        "commit": "5612f7a33f27f09d1fa988f15dfdffbe77a72705",
        "tree": "4786614d7ea428e3aea1d61a72dc74d9aad6bd92",
        "sha256": "7af205f420c2cf3a9039fff7aad1af65e55221005231b2fabe3bd99c94f96c4d",
    },
    {
        "commit": "f9412b36adeb75dc7d5d5af56824c87235f28ce7",
        "tree": "1b648be16bdc2bc41311f7968f6d402a63d4c8a9",
        "sha256": "cd17168c04ed5c3b05044322daae2480973d57220f05c0419f539f6fdf14977d",
    },
)
ALLOWED_CANDIDATE_PATHS = {
    "docs/W9_COMPLETION_MAP.md",
    MAP_RELATIVE_PATH,
    "tests/test_w10_completion_map.py",
}


def run_git(*args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def git_text(*args: str) -> str:
    return run_git(*args).decode("utf-8").strip()


def git_blob_sha256(commit: str, relative_path: str) -> str:
    return hashlib.sha256(run_git("show", f"{commit}:{relative_path}")).hexdigest()


def assert_historical_sha256(
    commit: str, relative_path: str, expected_sha256: str
) -> None:
    assert git_blob_sha256(commit, relative_path) == expected_sha256


def changed_paths(commit: str) -> tuple[str, ...]:
    output = git_text("diff-tree", "--no-commit-id", "--name-only", "-r", commit)
    return tuple(output.splitlines()) if output else ()


def reconciliation() -> dict[str, object]:
    block = TEXT.split(START, 1)[1].split(END, 1)[0]
    payload = block.split("```json", 1)[1].split("```", 1)[0]
    return json.loads(payload)


def test_candidate_is_confined_to_the_authorised_map_and_dedicated_test() -> None:
    changed = git_text("diff", "--name-only", "HEAD").splitlines()
    untracked = git_text("ls-files", "--others", "--exclude-standard").splitlines()
    assert set(changed + untracked) <= ALLOWED_CANDIDATE_PATHS


def test_reconciliation_is_bound_to_exact_clean_merge_base_without_head_lock() -> None:
    data = reconciliation()
    assert data["schema_version"] == "W10-completion-map/2026-09-04/reconciliation-4"
    assert data["reconciliation_base"] == {
        "commit": BASE,
        "tree": BASE_TREE,
        "parents": list(BASE_PARENTS),
    }
    assert git_text("rev-parse", f"{BASE}^{{tree}}") == BASE_TREE
    assert tuple(git_text("show", "-s", "--format=%P", BASE).split()) == BASE_PARENTS
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE, "HEAD"],
        cwd=ROOT,
        check=True,
    )


def test_component_commits_trees_paths_and_historical_blobs_are_exact() -> None:
    components = reconciliation()["components"]
    assert set(components) == set(EXPECTED_COMPONENTS)

    for component_name, expected in EXPECTED_COMPONENTS.items():
        component = components[component_name]
        for key in (
            "accepted_checkpoint",
            "accepted_tree",
            "integration_commit",
            "integration_tree",
        ):
            assert component[key] == expected[key]

        checkpoint = expected["accepted_checkpoint"]
        integration_commit = expected["integration_commit"]
        assert git_text("rev-parse", f"{checkpoint}^{{tree}}") == expected["accepted_tree"]
        assert git_text("rev-parse", f"{integration_commit}^{{tree}}") == expected[
            "integration_tree"
        ]
        assert changed_paths(checkpoint) == expected["paths"]
        assert tuple(component["paths_sha256"]) == expected["paths"]
        for relative_path, expected_sha256 in component["paths_sha256"].items():
            assert_historical_sha256(checkpoint, relative_path, expected_sha256)

        # Accepted isolated checkpoints remain immutable Git objects. The
        # corresponding integration commit, rather than the checkpoint branch,
        # is the required current-lineage ancestor.
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", integration_commit, "HEAD"],
            cwd=ROOT,
            check=True,
        )


def test_cherry_picks_merge_resolution_and_live_refresh_are_not_conflated() -> None:
    components = reconciliation()["components"]

    for component_name in (
        "Founder-Decisions-W10-002-003",
        "W10-S2D",
        "W10-S7A",
        "W10-S7A-reconciliation",
        "W10-S2E",
    ):
        component = components[component_name]
        assert changed_paths(component["integration_commit"]) == tuple(
            component["paths_sha256"]
        )
        for relative_path, expected_sha256 in component["paths_sha256"].items():
            assert_historical_sha256(
                component["integration_commit"], relative_path, expected_sha256
            )

    product = components["W10-S5C-product"]
    for relative_path, expected_sha256 in product["paths_sha256"].items():
        assert_historical_sha256(BASE, relative_path, expected_sha256)

    evidence = components["W10-S5C-evidence"]
    assert git_text(
        "show", "-s", "--format=%P", evidence["accepted_checkpoint"]
    ) == product["accepted_checkpoint"]
    for checkpoint in (
        product["accepted_checkpoint"],
        evidence["accepted_checkpoint"],
    ):
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", checkpoint, BASE],
            cwd=ROOT,
            check=True,
        )
    assert evidence["merge_resolution_paths"] == [
        "tests/test_w10_internal_route_reconciliation.py",
        "tests/test_w10_s2c_policy_evidence.py",
    ]

    s7a_refresh = components["W10-S7A"][
        "post_merge_live_binding_values_requiring_reconciliation"
    ]
    assert set(s7a_refresh) == {
        "docs/W10_S7A_BILLING_THREAT_MODEL.md",
        "reserved/web/v2.py",
        "tests/test_w10_billing_threat_model.py",
    }
    for relative_path, expected_sha256 in s7a_refresh.items():
        assert_historical_sha256(S2D_S5C_BASE, relative_path, expected_sha256)


def test_mutable_historical_map_sources_use_exact_git_blobs_and_reject_forgery() -> None:
    bindings = reconciliation()["historical_map_bindings"]
    assert tuple(bindings) == EXPECTED_HISTORICAL_MAP_BINDINGS

    for binding in bindings:
        assert git_text("rev-parse", f"{binding['commit']}^{{tree}}") == binding["tree"]
        assert_historical_sha256(
            binding["commit"], MAP_RELATIVE_PATH, binding["sha256"]
        )

        with pytest.raises(AssertionError):
            assert_historical_sha256(
                binding["commit"], MAP_RELATIVE_PATH, "0" * 64
            )
        with pytest.raises(AssertionError):
            assert_historical_sha256(
                WRONG_MAP_COMMIT, MAP_RELATIVE_PATH, binding["sha256"]
            )


def test_new_decision_s7a_and_s2e_bindings_reject_wrong_blobs_and_lineage() -> None:
    components = reconciliation()["components"]
    for name in (
        "Founder-Decisions-W10-002-003",
        "W10-S7A-reconciliation",
        "W10-S2E",
    ):
        component = components[name]
        path, expected_sha256 = next(iter(component["paths_sha256"].items()))
        assert_historical_sha256(component["accepted_checkpoint"], path, expected_sha256)
        with pytest.raises(AssertionError):
            assert_historical_sha256(component["accepted_checkpoint"], path, "0" * 64)

    # The isolated S2E checkpoint is deliberately not accepted as current-lineage
    # evidence merely because it has the same patch: only its integration commit
    # is an ancestor of this reconciliation base.
    isolated = components["W10-S2E"]["accepted_checkpoint"]
    assert subprocess.run(
        ["git", "merge-base", "--is-ancestor", isolated, BASE],
        cwd=ROOT,
    ).returncode != 0
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", components["W10-S2E"]["integration_commit"], "HEAD"],
        cwd=ROOT,
        check=True,
    )


def test_post_entitlement_components_bind_exact_integration_blobs_and_paths() -> None:
    components = reconciliation()["components"]
    names = (
        "W9-S3C",
        "W10-S4B",
        "W10-S4C",
        "W10-S6E",
        "W10-S6F",
        "W10-S6E-test-scope-correction",
        "W10-S3A-hardening",
        "W9-W10-entitlement-evidence-reconciliation",
        "W9-evidence-package-history-correction",
    )

    for name in names:
        component = components[name]
        integration_commit = component["integration_commit"]
        assert changed_paths(integration_commit) == tuple(component["paths_sha256"])
        for relative_path, expected_sha256 in component["paths_sha256"].items():
            assert_historical_sha256(
                integration_commit, relative_path, expected_sha256
            )

        path, expected_sha256 = next(iter(component["paths_sha256"].items()))
        with pytest.raises(AssertionError):
            assert_historical_sha256(
                component["accepted_checkpoint"], path, "0" * 64
            )


def test_finite_slice_and_terminal_denominators_remain_structurally_exact() -> None:
    slice_rows = re.findall(r"(?m)^\| \*\*W10-S([1-8]) —", TEXT)
    assert slice_rows == [str(value) for value in range(1, 9)]

    terminal = TEXT.split("## Finite terminal W10 gate", 1)[1].split(
        "## Current next action", 1
    )[0]
    terminal_ids = re.findall(r"(?m)^(\d+)\.", terminal)
    assert terminal_ids == [str(value) for value in range(1, 14)]
    assert "0/8 slices complete" in TEXT
    assert "0/8 (0%)" in TEXT
    assert "terminal gate remains 0/13" in TEXT
    assert "W9 remains 0/5" in TEXT


def test_w9_map_records_s3c_without_moving_any_launch_gate() -> None:
    slice_rows = re.findall(r"(?m)^\| \*\*W9-S([1-5]) —", W9_TEXT)
    assert slice_rows == [str(value) for value in range(1, 6)]
    assert "**0/5 slices\nare complete (0%)**" in W9_TEXT
    assert "c9bdaa6538d68c0c64b2dcde97f224a69c089d30" in W9_TEXT
    assert "5f5a948891e1e812a5c74ff6c7266d153bb492fa" in W9_TEXT
    assert "three accepted non-durable\ncontract/adapter layers" in W9_TEXT
    assert "selected/verified datastore" in W9_TEXT
    assert "durable read/write implementation" in W9_TEXT
    assert "approved retention/legal-hold/backup-expiry" in W9_TEXT
    assert "encryption/key-custody implementation" in W9_TEXT
    assert "target evidence remain missing" in W9_TEXT
    assert "historical\n  accepted/integrated evidence at `a07348976321df65bbd95c9170c906bcddd5baa5`" in W9_TEXT
    assert "current HEAD remain evidence-only" not in W9_TEXT
    assert "validates the exact live admitted S3A projection" in W9_TEXT
    assert "caller-supplied expected owner/business references" in W9_TEXT
    assert "does not authenticate the runtime caller or issuer" in W9_TEXT
    assert "future authenticated runtime-owner adapter" in W9_TEXT
    assert "S3C authenticated non-durable adapter" not in W9_TEXT
    assert "authenticates an exact S3A projection" not in W9_TEXT
    assert "authenticates the exact S3A envelope" not in W9_TEXT
    assert "An authenticated adapter" not in W9_TEXT


def test_current_state_is_partial_non_authorising_and_keeps_every_gate_open() -> None:
    required = (
        "Q1 refunds, Q2 paid surface and Q3",
        "remain unanswered Founder questions",
        "Exactly five policy keys remain unresolved",
        "implements only the disabled-first, owner-bound, no-transfer local decision",
        "no authenticated adapter, durable",
        "S5C implements five bounded",
        "no paid-boundary or entitlement guard exists",
        "post-S2D/S5C reconciliation is integrated",
        "No threat is accepted closed",
        "all 21 threats remain open",
        "detached, structurally validated, non-authoritative tax/invoice prerequisite",
        "does not close the VAT/invoice policy key",
        "no security, privacy, operations, provider, target or launch assurance",
        "S4B disabled Checkout intent",
        "S4C disabled Customer Portal intent",
        "models the first verified failed renewal as `payment_recovery` for exactly seven calendar days",
        "Provider labels have zero direct authority",
        "S6E is accepted",
        "S6F is accepted",
        "detached zero-authority cancellation/end-of-paid-period view",
        "cannot cancel, mutate, persist or grant access",
        "W9 package-history sentinel is corrected at `109b5ec...`",
        "provider terms",
        "sandbox access",
        "approved credentials/key custody",
        "target hosting",
        "finance/tax",
        "Founder activation/release and launch authority",
    )
    for statement in required:
        assert statement in TEXT

    forbidden = (
        "S5 implementation remains not started",
        "S5 implementation not started",
        "S7A is current assurance",
        "S7A closes",
        "S2D closes the recovery key",
        "strict completion remains 1/8",
        "requires post-convergence reconciliation",
        "awaits current-lineage reconciliation",
        "S4A remains a disabled provider-edge contract",
    )
    for statement in forbidden:
        assert statement not in TEXT


def test_current_map_is_deliberately_not_self_hashed() -> None:
    data = reconciliation()
    assert "map_sha256" not in data
    assert MAP_RELATIVE_PATH not in {
        relative_path
        for component in data["components"].values()
        for relative_path in component.get("paths_sha256", {})
    }
