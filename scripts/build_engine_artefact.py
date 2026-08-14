#!/usr/bin/env python3
"""
Deterministic engine release-artefact generator.

Builds a self-contained, importable copy of the maintained tax engine
(``reserved/engines``) together with its single stdlib-only external
dependency (``reserved/evidence_uncertainty.py``), and records immutable
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
in a fixed order, the single permitted absolute import is rewritten in a
stable way, and the ``generated_on`` timestamp is taken from
``SOURCE_DATE_EPOCH`` (reproducible-builds convention) or, failing that, the
source commit's committer timestamp.

Provenance
----------
``PROVENANCE.json`` records the source commit, engine/rules versions, the
sha256 of every source file, a deterministic ``content_hash`` fingerprint of
the whole artefact, and the build timestamp.

Fail-closed behaviour
---------------------
Any absolute ``reserved.*`` import in the engine source (other than the one
known stdlib-only dependency that is explicitly rewritten) aborts the build,
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

# The one absolute import that must be rewritten so the artefact is
# self-contained (annual_loan_wp7u imports reserved.evidence_uncertainty).
REWRITE_ABS_IMPORT_FROM = "from reserved.evidence_uncertainty import"
REWRITE_ABS_IMPORT_TO   = "from .evidence_uncertainty import"

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


def _abs_import_lines(text: str) -> list[str]:
    """Return lines containing absolute ``reserved.*`` imports."""
    out: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("from reserved.") or stripped.startswith("import reserved."):
            out.append(line)
    return out


def _copy_and_rewrite(src: Path, dst: Path) -> None:
    """Copy a source module, rewriting the single permitted absolute import."""
    text = src.read_text(encoding="utf-8")
    abs_imports = _abs_import_lines(text)
    for line in abs_imports:
        stripped = line.strip()
        if stripped.startswith(REWRITE_ABS_IMPORT_FROM):
            text = text.replace(REWRITE_ABS_IMPORT_FROM, REWRITE_ABS_IMPORT_TO)
            continue
        raise SystemExit(
            f"{src}: artefact is not self-contained (absolute reserved.* import): {line!r}"
        )
    dst.write_text(text, encoding="utf-8")


def build(source: Path, out: Path) -> dict:
    """Build the artefact and return its provenance mapping."""
    source = source.resolve()
    if not (source / "__init__.py").exists():
        raise SystemExit(f"source package missing __init__.py: {source}")

    evidence = (_repo_root() / EVIDENCE_UNCERTAINTY_SOURCE).resolve()
    if not evidence.exists():
        raise SystemExit(f"missing evidence_uncertainty dependency: {evidence}")

    engine_version = _module_constant(source / "__init__.py", "ENGINE_VERSION")
    rules_version = _module_constant(source / "tax_config.py", "RULES_VERSION")
    commit = _source_commit()

    source_files: dict[str, str] = {}
    for path in sorted(source.glob("*.py")):
        source_files[path.name] = _sha256_bytes(path.read_bytes())
    if (source / "CHANGELOG.md").exists():
        source_files["CHANGELOG.md"] = _sha256_bytes((source / "CHANGELOG.md").read_bytes())
    evidence_hash = _sha256_bytes(evidence.read_bytes())

    content_hash = _sha256_bytes(
        json.dumps(
            {"source_files": source_files, "evidence_uncertainty": evidence_hash},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )

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

        provenance = {
            "schema": PROVENANCE_SCHEMA,
            "source_commit": commit,
            "engine_version": engine_version,
            "rules_version": rules_version,
            "generated_on": _generated_on(),
            "content_hash": content_hash,
            "source_files": source_files,
            "evidence_uncertainty_source": EVIDENCE_UNCERTAINTY_SOURCE,
            "evidence_uncertainty_sha256": evidence_hash,
        }
        (pkg / "PROVENANCE.json").write_text(
            json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

        out = out.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            shutil.rmtree(out)
        shutil.move(str(pkg), str(out))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return provenance


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
    args = parser.parse_args(argv)

    provenance = build(Path(args.source), Path(args.out))
    json.dump(provenance, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
