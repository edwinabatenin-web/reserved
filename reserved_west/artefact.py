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


def load_engine(*, rebuild: bool = False) -> tuple[object, dict]:
    """Import the release artefact and return ``(module, provenance)``.

    The artefact is imported under the package name ``reserved_engine`` and
    must therefore not collide with any other ``reserved_engine`` already on
    ``sys.path``.  The stale historical bundle lives in
    ``reserved-engine-2.0.0/`` and is *not* added to ``sys.path`` here.
    """
    target = artefact_dir()
    if rebuild or os.environ.get("RESERVED_ENGINE_REBUILD") == "1":
        _build()
    elif not (target / "__init__.py").exists() or not (target / "PROVENANCE.json").exists():
        _build()

    parent = str(target.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)

    module = importlib.import_module("reserved_engine")
    return module, provenance(target)
