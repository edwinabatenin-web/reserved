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
            raise RuntimeError(f"artefact contains a symbolic link: {path.name}")
        if path.is_dir():
            raise RuntimeError(f"artefact contains an unsupported subdirectory: {path.name}")
        if not path.is_file():
            raise RuntimeError(f"artefact contains an unsupported filesystem object: {path.name}")
        if path.name.endswith(".pyc") or path.name.endswith(".pyo"):
            raise RuntimeError(f"artefact contains unmanifested bytecode: {path.name}")
        if path.name not in expected_names:
            raise RuntimeError(f"artefact contains an unexpected file: {path.name}")
        hashes[path.name] = _sha256_bytes(path.read_bytes())
    missing = expected_names - set(hashes)
    if missing:
        raise RuntimeError(f"artefact is missing manifested file(s): {', '.join(sorted(missing))}")
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

    The set of files the artefact must ship is derived from the provenance
    manifest (``source_files`` plus the copied ``evidence_uncertainty.py``).
    Any file outside that set — cached bytecode, an added module, a symbolic
    link, a subdirectory, or any other object — is rejected.  The content
    identity is recomputed over those manifested files and must match, and the
    shipped ``evidence_uncertainty.py`` must match its recorded hash.  Any
    mismatch means the artefact is stale, tampered, or built by a different
    process, and must be rejected rather than silently loaded.
    """
    prov = provenance(path)
    if prov.get("schema") != "reserved-engine-artefact-provenance-1":
        raise RuntimeError(f"unrecognised artefact provenance schema: {prov.get('schema')!r}")

    source_files = prov.get("source_files")
    if not isinstance(source_files, dict) or not source_files:
        raise RuntimeError("engine artefact provenance has no source_files manifest")

    expected_names = set(source_files) | {"evidence_uncertainty.py"}
    actual_content_hash = _produced_content_hash(path, expected_names)
    if actual_content_hash != prov.get("content_hash"):
        raise RuntimeError(
            "engine artefact content identity mismatch (stale or tampered): "
            f"expected {prov.get('content_hash')}, computed {actual_content_hash}"
        )

    evidence_file = path / "evidence_uncertainty.py"
    if _sha256_bytes(evidence_file.read_bytes()) != prov.get("evidence_uncertainty_sha256"):
        raise RuntimeError("engine artefact evidence_uncertainty mismatch")

    return prov


# Build-once, shared, verified artefact for the current release run.  The cache
# is bound to the canonical resolved artefact path AND its verified content
# identity, so a changed path or content can never silently return a stale module.
_LOADED: dict | None = None


def _purge_reserved_engine() -> None:
    for name in [name for name in sys.modules if name == "reserved_engine" or name.startswith("reserved_engine.")]:
        del sys.modules[name]


def _verify_loaded_modules(target: Path) -> None:
    """Ensure every loaded ``reserved_engine`` module resolves beneath ``target``.

    This guards against a foreign, previously cached or lazily imported module
    being satisfied from somewhere other than the selected verified artefact.
    """
    resolved = target.resolve()
    offenders = []
    for name, mod in list(sys.modules.items()):
        if name != "reserved_engine" and not name.startswith("reserved_engine."):
            continue
        mod_file = Path(getattr(mod, "__file__", "") or "").resolve()
        if not mod_file.is_relative_to(resolved):
            offenders.append(f"{name} -> {mod_file}")
    if offenders:
        raise RuntimeError(
            "reserved_engine module(s) resolved outside the verified artefact: "
            + "; ".join(offenders)
        )


def _import_reserved_engine(target: Path) -> object:
    # Import by exact package name; the parent of the artefact package is placed
    # at the front of sys.path and any previously inserted artefact parent is
    # removed so switching artefacts cannot leave stale parents or a mixed
    # module graph from two different artefacts.
    parent = str(target.parent)
    if _LOADED is not None:
        old_parent = _LOADED.get("parent")
        if old_parent is not None and old_parent != parent:
            sys.path[:] = [p for p in sys.path if p != old_parent]
    sys.path[:] = [p for p in sys.path if p != parent]
    sys.path.insert(0, parent)

    module = importlib.import_module("reserved_engine")
    _verify_loaded_modules(target)
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

    Bytecode creation is suppressed for the duration of the import and the
    verified package directory is treated as immutable; after loading, the
    artefact directory is re-checked to prove no ``__pycache__``, ``.pyc`` or
    other new executable content has appeared.
    """
    global _LOADED

    target = artefact_dir().resolve()
    if rebuild or os.environ.get("RESERVED_ENGINE_REBUILD") == "1":
        _build()
    elif not (target / "__init__.py").exists() or not (target / "PROVENANCE.json").exists():
        _build()

    prov = verify_artefact(target)

    # Bound the cache to path + verified content identity.  A change in either
    # triggers a fresh (purged, verified) import rather than a silent stale hit.
    if (
        _LOADED is not None
        and _LOADED["path"] == target
        and _LOADED["content_hash"] == prov["content_hash"]
    ):
        return _LOADED["module"], _LOADED["prov"]

    _purge_reserved_engine()

    prev_dont_write = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        module = _import_reserved_engine(target)
    finally:
        sys.dont_write_bytecode = prev_dont_write

    _reject_new_bytecode(target)

    _LOADED = {
        "path": target,
        "parent": str(target.parent),
        "content_hash": prov["content_hash"],
        "module": module,
        "prov": prov,
    }
    return module, prov


def _reject_new_bytecode(target: Path) -> None:
    """Fail closed if bytecode or a cache directory appeared in the artefact."""
    for entry in target.iterdir():
        if entry.name == "__pycache__" or entry.name.endswith(".pyc") or entry.name.endswith(".pyo"):
            raise RuntimeError(f"bytecode appeared in the verified artefact: {entry.name}")
