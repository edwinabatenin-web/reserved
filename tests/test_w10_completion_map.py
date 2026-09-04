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
START = "<!-- W10-COMPLETION-MAP-RECONCILIATION-BEGIN -->"
END = "<!-- W10-COMPLETION-MAP-RECONCILIATION-END -->"

BASE = "85e1250f53180bb3c1aff111c17101b9e59df080"
BASE_TREE = "89a96da31b7a5dbe9bf55c01e875a0d611829e01"
BASE_PARENTS = (
    "54a82476939dce8f75af62d73aeb477e11a1260c",
    "e3959964ca08bd5afb6f75feab4ec0fdc83a9423",
)
WRONG_MAP_COMMIT = "81ae02044cccd921d98a0d1fc2360e1c4a983ab1"

EXPECTED_COMPONENTS = {
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
        "integration_commit": BASE,
        "integration_tree": BASE_TREE,
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
        "integration_commit": BASE,
        "integration_tree": BASE_TREE,
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
    assert data["schema_version"] == "W10-completion-map/2026-09-04/reconciliation-1"
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

    for component_name in ("W10-S2D", "W10-S7A"):
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
        assert_historical_sha256(BASE, relative_path, expected_sha256)


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


def test_current_state_is_partial_non_authorising_and_keeps_every_gate_open() -> None:
    required = (
        "Q1 refunds, Q2 paid surface and Q3",
        "remain unanswered Founder questions",
        "Exactly five policy keys remain unresolved",
        "implements only the disabled-first, owner-bound, no-transfer local decision",
        "no authenticated adapter, durable",
        "S5C implements five bounded",
        "no paid-boundary or entitlement guard exists",
        "requires post-convergence evidence reconciliation",
        "No threat is accepted closed",
        "no security, privacy, operations, provider, target or launch assurance",
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
