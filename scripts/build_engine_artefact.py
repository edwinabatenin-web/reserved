#!/usr/bin/env python3
"""
Deterministic engine release-artefact generator.

Builds a self-contained, importable copy of the maintained tax engine
(``reserved/engines``) together with its stdlib-only external dependencies
(``reserved/evidence_uncertainty.py`` and
``reserved/providers/accounting/contracts.py``), and records immutable
provenance in ``PROVENANCE.json``.

Why this exists
---------------
The maintained calculation source is ``reserved/engines``.  Releases must be
a *deterministic, immutable, versioned artefact* produced from an
identifiable source commit/tag — not a hand-synchronised mutable copy and not
an implicit import from the mutable working tree.  This script is that build
step.

Determinism
-----------
For identical source content the artefact is byte-identical: files are copied
in a fixed order, the permitted absolute imports are rewritten in a stable
way, and the ``generated_on`` timestamp is taken from
``SOURCE_DATE_EPOCH`` (reproducible-builds convention) or, failing that, the
source commit's committer timestamp.

Provenance
----------
``PROVENANCE.json`` records the source commit, engine/rules versions, the
sha256 of every source file, a deterministic ``content_hash`` fingerprint of
the whole artefact, and the build timestamp.

Fail-closed behaviour
---------------------
Any absolute ``reserved.*`` import in the engine source (other than the known
stdlib-only dependencies that are explicitly rewritten) aborts the build,
so a non-self-contained artefact can never be silently produced.

Usage
-----
    python scripts/build_engine_artefact.py [--source DIR] [--out DIR]

Defaults: ``--source reserved/engines``, ``--out dist/reserved_engine``.
The output directory (``dist/``) is git-ignored build output.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# ── Build constants ───────────────────────────────────────────────────────────
EVIDENCE_UNCERTAINTY_SOURCE = "reserved/evidence_uncertainty.py"
EVIDENCE_UNCERTAINTY_TARGET = "evidence_uncertainty.py"

ACCOUNTING_CONTRACTS_SOURCE = "reserved/providers/accounting/contracts.py"
ACCOUNTING_CONTRACTS_TARGET = "accounting_contracts.py"

# Absolute ``reserved.*`` imports that must be rewritten so the artefact is
# self-contained.  Each engine dependency is copied into the flat artefact and
# its import is rewritten to the artefact-local module name.
REWRITE_RULES = (
    ("from reserved.evidence_uncertainty import", "from .evidence_uncertainty import"),
    (
        "from reserved.providers.accounting.contracts import",
        "from .accounting_contracts import",
    ),
)

PROVENANCE_SCHEMA = "reserved-engine-artefact-provenance-1"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _git(args: list[str], default: str | None = None) -> str | None:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=_repo_root(),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return default
    if proc.returncode != 0:
        return default
    value = proc.stdout.strip()
    return value or default


def _source_commit() -> str:
    return _git(["rev-parse", "HEAD"], default="unversioned")


def _generated_on() -> str:
    """Deterministic ISO-8601 timestamp for the build."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch:
        try:
            return datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        except (ValueError, OSError):
            pass
    commit_epoch = _git(["log", "-1", "--format=%ct"])
    if commit_epoch:
        try:
            return datetime.fromtimestamp(int(commit_epoch), tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        except (ValueError, OSError):
            pass
    return datetime.fromtimestamp(0, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _module_constant(path: Path, name: str) -> str:
    """Extract a module-level string constant without importing the package."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        target = None
        value_node = None
        if isinstance(node, ast.Assign):
            if len(node.targets) == 1:
                target = node.targets[0]
            value_node = node.value
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            value_node = node.value
        if isinstance(target, ast.Name) and target.id == name and value_node is not None:
            value = ast.literal_eval(value_node)
            if isinstance(value, str):
                return value
    raise SystemExit(f"Could not resolve {name!r} in {path}")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _produced_content_hash(directory: Path, expected_names: set[str]) -> str:
    """Content identity over exactly the manifested produced files.

    ``expected_names`` is the set of top-level filenames the artefact must ship
    (excluding ``PROVENANCE.json``, which records this value).  Every entry in
    ``directory`` must be one of those names and a regular file: symbolic links,
    subdirectories (including ``__pycache__``), bytecode (``.pyc``/``.pyo``),
    unexpected files and other filesystem object types are rejected rather than
    silently omitted from the identity.  Missing manifested files are also
    rejected.
    """
    hashes: dict[str, str] = {}
    for path in sorted(directory.iterdir()):
        if path.name == "PROVENANCE.json":
            continue
        if path.is_symlink():
            raise SystemExit(f"artefact contains a symbolic link: {path.name}")
        if path.is_dir():
            raise SystemExit(f"artefact contains an unsupported subdirectory: {path.name}")
        if not path.is_file():
            raise SystemExit(f"artefact contains an unsupported filesystem object: {path.name}")
        if path.name.endswith(".pyc") or path.name.endswith(".pyo"):
            raise SystemExit(f"artefact contains unmanifested bytecode: {path.name}")
        if path.name not in expected_names:
            raise SystemExit(f"artefact contains an unexpected file: {path.name}")
        hashes[path.name] = _sha256_bytes(path.read_bytes())
    missing = expected_names - set(hashes)
    if missing:
        raise SystemExit(f"artefact is missing manifested file(s): {', '.join(sorted(missing))}")
    return _sha256_bytes(
        json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _dirty_source_paths(*paths: Path) -> list[str]:
    """Return uncommitted/changed paths under the supplied source/dependency paths."""
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--", *(str(p) for p in paths)],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        # Not a git repository or git unavailable: report as unknown, not dirty.
        return []
    return [line[3:].strip() for line in proc.stdout.splitlines() if line.strip()]


def _abs_import_lines(text: str) -> list[str]:
    """Return lines containing absolute ``reserved.*`` imports."""
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("from reserved.") or stripped.startswith("import reserved."):
            out.append(line)
    return out


def _copy_and_rewrite(src: Path, dst: Path) -> None:
    """Copy a source module, rewriting the permitted absolute imports."""
    text = src.read_text(encoding="utf-8")
    abs_imports = _abs_import_lines(text)
    for line in abs_imports:
        stripped = line.strip()
        matched = False
        for rewrite_from, rewrite_to in REWRITE_RULES:
            if stripped.startswith(rewrite_from):
                text = text.replace(rewrite_from, rewrite_to)
                matched = True
                break
        if not matched:
            raise SystemExit(
                f"{src}: artefact is not self-contained (absolute reserved.* import): {line!r}"
            )
    dst.write_text(text, encoding="utf-8")


def _require_engine_package(source: Path) -> None:
    """Reject an unsupported/unknown source rather than silently accepting it."""
    required = ("__init__.py", "income_tax.py", "tax_config.py")
    missing = [name for name in required if not (source / name).exists()]
    if missing:
        raise SystemExit(
            f"source is not a recognised engine package (missing {', '.join(missing)}): {source}"
        )


def _make_readonly(path: Path) -> None:
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            os.chmod(os.path.join(root, name), 0o444)
        for name in dirs:
            os.chmod(os.path.join(root, name), 0o555)
    # The top-level package directory itself must also be non-writable so Python
    # cannot create ``__pycache__``; individual read-only files are insufficient.
    os.chmod(path, 0o555)


def _make_writable(path: Path) -> None:
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            os.chmod(os.path.join(root, name), 0o644)
        for name in dirs:
            os.chmod(os.path.join(root, name), 0o755)
    os.chmod(path, 0o755)


def build(source: Path, out: Path, *, allow_dirty: bool = False) -> dict:
    """Build the artefact and return its provenance mapping."""
    source = source.resolve()
    _require_engine_package(source)

    evidence = (_repo_root() / EVIDENCE_UNCERTAINTY_SOURCE).resolve()
    if not evidence.exists():
        raise SystemExit(f"missing evidence_uncertainty dependency: {evidence}")

    accounting_contracts = (_repo_root() / ACCOUNTING_CONTRACTS_SOURCE).resolve()
    if not accounting_contracts.exists():
        raise SystemExit(f"missing accounting_contracts dependency: {accounting_contracts}")

    if not allow_dirty:
        dirty = _dirty_source_paths(source, evidence, accounting_contracts)
        if dirty:
            raise SystemExit(
                "refusing to build from a dirty source; commit or revert "
                f"these paths (or pass --allow-dirty): {', '.join(sorted(set(dirty)))}"
            )

    engine_version = _module_constant(source / "__init__.py", "ENGINE_VERSION")
    rules_version = _module_constant(source / "tax_config.py", "RULES_VERSION")
    commit = _source_commit()

    source_files: dict[str, str] = {}
    for path in sorted(source.glob("*.py")):
        source_files[path.name] = _sha256_bytes(path.read_bytes())
    if (source / "CHANGELOG.md").exists():
        source_files["CHANGELOG.md"] = _sha256_bytes((source / "CHANGELOG.md").read_bytes())
    evidence_hash = _sha256_bytes(evidence.read_bytes())
    accounting_contracts_hash = _sha256_bytes(accounting_contracts.read_bytes())

    # Build into a temp directory, then atomically publish.
    tmp = Path(tempfile.mkdtemp(prefix="reserved-engine-artefact-"))
    try:
        pkg = tmp / "reserved_engine"
        pkg.mkdir()
        for path in sorted(source.glob("*.py")):
            _copy_and_rewrite(path, pkg / path.name)
        if (source / "CHANGELOG.md").exists():
            shutil.copy2(source / "CHANGELOG.md", pkg / "CHANGELOG.md")
        shutil.copy2(evidence, pkg / EVIDENCE_UNCERTAINTY_TARGET)
        shutil.copy2(accounting_contracts, pkg / ACCOUNTING_CONTRACTS_TARGET)

        # Content identity is computed over the produced bytes (the shipped
        # files), not over the source-hash metadata.  The expected file set is
        # the source files plus the copied dependencies.
        expected_names = set(source_files) | {
            EVIDENCE_UNCERTAINTY_TARGET,
            ACCOUNTING_CONTRACTS_TARGET,
        }
        content_hash = _produced_content_hash(pkg, expected_names)

        provenance = {
            "schema": PROVENANCE_SCHEMA,
            "source_commit": commit,
            "source_path": str(_repo_relative(source)),
            "engine_version": engine_version,
            "rules_version": rules_version,
            "generated_on": _generated_on(),
            "content_hash": content_hash,
            "source_files": source_files,
            "evidence_uncertainty_source": EVIDENCE_UNCERTAINTY_SOURCE,
            "evidence_uncertainty_sha256": evidence_hash,
            "accounting_contracts_source": ACCOUNTING_CONTRACTS_SOURCE,
            "accounting_contracts_sha256": accounting_contracts_hash,
        }
        (pkg / "PROVENANCE.json").write_text(
            json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        out = out.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            _make_writable(out)
            shutil.rmtree(out)
        shutil.move(str(pkg), str(out))

        # The published artefact is immutable and read-only (including the
        # top-level package directory, which must be non-writable so Python
        # cannot create ``__pycache__``).
        _make_readonly(out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return provenance


def _repo_relative(path: Path) -> Path:
    try:
        return path.relative_to(_repo_root())
    except ValueError:
        return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=str(_repo_root() / "reserved" / "engines"),
        help="Maintained engine package directory (default: reserved/engines)",
    )
    parser.add_argument(
        "--out",
        default=str(_repo_root() / "dist" / "reserved_engine"),
        help="Output artefact directory (default: dist/reserved_engine)",
    )
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="Allow building from an uncommitted/dirty source (default: refuse)",
    )
    args = parser.parse_args(argv)

    provenance = build(Path(args.source), Path(args.out), allow_dirty=args.allow_dirty)
    json.dump(provenance, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
