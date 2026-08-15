"""
Reserved West — engine release-artefact loader.

Reserved West must test an *explicitly identified current release artefact*,
not a hand-synchronised mutable copy (the historical ``reserved-engine-2.0.0``
bundle) and not an implicit import from the mutable production working tree
(``reserved.engines``).

This module builds (if necessary) and imports the deterministic artefact
produced by ``scripts/build_engine_artefact.py``, and returns it together
with its immutable provenance so downstream evidence can record exactly what
was under test.

Behaviour
---------
* ``RESERVED_ENGINE_ARTEFACT`` (env) overrides the artefact directory;
  the default is ``<repo>/dist/reserved_engine``.
* If the artefact is absent, it is built deterministically from the current
  source.  Once built it is treated as immutable: ``load_engine`` will not
  silently rebuild it and will report the provenance it was built from.
* ``rebuild=True`` (or ``RESERVED_ENGINE_REBUILD=1``) forces a fresh build.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def artefact_dir() -> Path:
    override = os.environ.get("RESERVED_ENGINE_ARTEFACT")
    if override:
        return Path(override)
    return _repo_root() / "dist" / "reserved_engine"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _produced_content_hash(directory: Path) -> str:
    """Content identity over the produced artefact bytes (see build script).

    The artefact format is flat (top-level files only); any subdirectory is
    rejected rather than silently omitted from the identity.
    """
    hashes: dict[str, str] = {}
    for path in sorted(directory.iterdir()):
        if path.name == "PROVENANCE.json" or path.name == "__pycache__":
            continue
        if path.is_dir():
            raise RuntimeError(f"artefact contains an unsupported subdirectory: {path.name}")
        hashes[path.name] = _sha256_bytes(path.read_bytes())
    return _sha256_bytes(
        json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _build() -> None:
    script = _repo_root() / "scripts" / "build_engine_artefact.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--out", str(artefact_dir())],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"engine artefact build failed (exit {proc.returncode}):\n{proc.stderr}"
        )


def provenance(path: Path) -> dict:
    prov_file = path / "PROVENANCE.json"
    if not prov_file.exists():
        raise RuntimeError(f"engine artefact missing provenance: {prov_file}")
    return json.loads(prov_file.read_text(encoding="utf-8"))


def verify_artefact(path: Path) -> dict:
    """Verify the produced bytes against the recorded manifest.

    Recompute the content identity over the produced files (excluding the
    provenance file that records it) and require it to match, and require the
    shipped ``evidence_uncertainty.py`` to match its recorded hash.  Any
    mismatch means the artefact is stale, tampered, or built by a different
    process, and must be rejected rather than silently loaded.
    """
    prov = provenance(path)
    if prov.get("schema") != "reserved-engine-artefact-provenance-1":
        raise RuntimeError(f"unrecognised artefact provenance schema: {prov.get('schema')!r}")

    actual_content_hash = _produced_content_hash(path)
    if actual_content_hash != prov.get("content_hash"):
        raise RuntimeError(
            "engine artefact content identity mismatch (stale or tampered): "
            f"expected {prov.get('content_hash')}, computed {actual_content_hash}"
        )

    evidence_file = path / "evidence_uncertainty.py"
    if not evidence_file.exists():
        raise RuntimeError("engine artefact missing evidence_uncertainty.py")
    if _sha256_bytes(evidence_file.read_bytes()) != prov.get("evidence_uncertainty_sha256"):
        raise RuntimeError("engine artefact evidence_uncertainty mismatch")

    return prov


# Build-once, shared, verified artefact for the current release run.
_LOADED: tuple[object, dict] | None = None


def _purge_reserved_engine() -> None:
    for name in [name for name in sys.modules if name == "reserved_engine" or name.startswith("reserved_engine.")]:
        del sys.modules[name]


def _import_reserved_engine(target: Path) -> object:
    parent = str(target.parent)
    # Remove any stale artefact parent from sys.path so a changed artefact
    # location cannot silently resolve to a previous build.
    sys.path[:] = [p for p in sys.path if p != parent]
    sys.path.insert(0, parent)
    module = importlib.import_module("reserved_engine")
    module_file = Path(getattr(module, "__file__", "") or "").resolve()
    if not module_file.is_relative_to(target.resolve()):
        raise RuntimeError(
            "reserved_engine module did not resolve beneath the verified artefact: "
            f"{module_file} (expected {target})"
        )
    return module


def load_engine(*, rebuild: bool = False) -> tuple[object, dict]:
    """Import the verified release artefact and return ``(module, provenance)``.

    The artefact is built at most once per process, verified against its
    recorded manifest, and shared by every caller.  It is imported under the
    package name ``reserved_engine`` and must therefore not collide with any
    other ``reserved_engine`` already on ``sys.path``.  Any previously imported
    ``reserved_engine`` (for example the historical
    ``reserved-engine-2.0.0`` bundle) is purged before import so a cached or
    foreign module can never be returned alongside current-artefact provenance.
    """
    global _LOADED
    if _LOADED is not None and not rebuild:
        return _LOADED

    target = artefact_dir()
    if rebuild or os.environ.get("RESERVED_ENGINE_REBUILD") == "1":
        _build()
    elif not (target / "__init__.py").exists() or not (target / "PROVENANCE.json").exists():
        _build()

    prov = verify_artefact(target)

    # Always purge before import — not only on rebuild — so a foreign or
    # historical ``reserved_engine`` already in ``sys.modules`` cannot be
    # returned with provenance that describes the current verified artefact.
    _purge_reserved_engine()
    module = _import_reserved_engine(target)

    _LOADED = (module, prov)
    return _LOADED
