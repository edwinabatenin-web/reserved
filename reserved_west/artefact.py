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

Verified-byte loading
---------------------
The artefact is read once into immutable byte buffers, those exact buffers are
verified against the provenance content identity, and the ``reserved_engine``
package (and every submodule) is then constructed and executed **from those
verified buffers** through a narrowly scoped ``sys.meta_path`` finder.  The
normal source loader is never used, so there is no point at which a mutable
on-disk file can be reopened after verification and substituted for the bytes
that were executed.  A narrow finder remains installed only to service later
lazy imports of manifested submodules; it is bound to the active artefact,
removed on switch/failure, and can never service an unrelated import.

Each loaded module carries a synthetic, non-resolvable ``__file__`` so
tracebacks and source-inspection facilities can never read a later-mutated
on-disk copy back as if it were the executed code.  ``__loader__.get_source``
returns the verified in-memory source.

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
import importlib.abc
import importlib.util
import json
import linecache
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


def _read_verified_artefact(path: Path) -> tuple[dict, dict[str, bytes]]:
    """Read every manifested produced file once into immutable bytes and verify.

    The returned ``buffers`` are exactly the bytes whose aggregate identity
    matches the recorded provenance ``content_hash``; the caller can therefore
    compile/execute those buffers without ever reopening the mutable filesystem.
    """
    prov = provenance(path)
    if prov.get("schema") != "reserved-engine-artefact-provenance-1":
        raise RuntimeError(f"unrecognised artefact provenance schema: {prov.get('schema')!r}")

    source_files = prov.get("source_files")
    if not isinstance(source_files, dict) or not source_files:
        raise RuntimeError("engine artefact provenance has no source_files manifest")

    expected_names = set(source_files) | {"evidence_uncertainty.py"}
    buffers: dict[str, bytes] = {}
    for entry in sorted(path.iterdir()):
        if entry.name == "PROVENANCE.json":
            continue
        if entry.is_symlink():
            raise RuntimeError(f"artefact contains a symbolic link: {entry.name}")
        if entry.is_dir():
            raise RuntimeError(f"artefact contains an unsupported subdirectory: {entry.name}")
        if not entry.is_file():
            raise RuntimeError(f"artefact contains an unsupported filesystem object: {entry.name}")
        if entry.name.endswith(".pyc") or entry.name.endswith(".pyo"):
            raise RuntimeError(f"artefact contains unmanifested bytecode: {entry.name}")
        if entry.name not in expected_names:
            raise RuntimeError(f"artefact contains an unexpected file: {entry.name}")
        buffers[entry.name] = entry.read_bytes()

    missing = expected_names - set(buffers)
    if missing:
        raise RuntimeError(f"artefact is missing manifested file(s): {', '.join(sorted(missing))}")

    # Content identity is computed over exactly the captured buffers.
    hashes = {name: _sha256_bytes(data) for name, data in buffers.items()}
    actual_content_hash = _sha256_bytes(
        json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    if actual_content_hash != prov.get("content_hash"):
        raise RuntimeError(
            "engine artefact content identity mismatch (stale or tampered): "
            f"expected {prov.get('content_hash')}, computed {actual_content_hash}"
        )

    if _sha256_bytes(buffers["evidence_uncertainty.py"]) != prov.get("evidence_uncertainty_sha256"):
        raise RuntimeError("engine artefact evidence_uncertainty mismatch")

    return prov, buffers


def verify_artefact(path: Path) -> dict:
    """Verify the produced bytes against the recorded manifest.

    See ``_read_verified_artefact``; this wrapper returns only the provenance.
    """
    return _read_verified_artefact(path)[0]


# ── Verified-byte importer ───────────────────────────────────────────────────

def _virtual_filename(target: Path, name: str) -> str:
    """Synthetic, non-resolvable source path for a verified snapshot.

    Tracebacks and source-inspection facilities use this path; because it is
    clearly virtual (angle brackets and a colon) it can never resolve to — and
    therefore can never reopen — a mutable on-disk source file.
    """
    return f"<verified-artefact:{target}>/{name}"


def _build_module_map(buffers: dict[str, bytes], target: Path) -> dict[str, tuple]:
    """Map manifested ``.py`` buffers to ``{fullname: (bytes, is_package, filename)}``."""
    modules: dict[str, tuple] = {}
    for name, data in buffers.items():
        if not name.endswith(".py"):
            continue  # CHANGELOG.md etc. are identity-only, never importable
        filename = _virtual_filename(target, name)
        if name == "__init__.py":
            modules["reserved_engine"] = (data, True, filename)
        else:
            modules[f"reserved_engine.{name[:-3]}"] = (data, False, filename)
    return modules


class _SnapshotRegistry:
    """Opaque per-snapshot registry of exact loaders and loaded module objects.

    The registry is the single authority for one verified snapshot.  It maps
    each manifested module name to its exact ``_VerifiedLoader`` object and,
    after successful execution, to the exact module object the import system
    produced.  Trust is membership/identity based: a loaded module is trusted
    only when ``sys.modules[name]`` *is* the registered module object and its
    ``__loader__``/``__spec__.loader`` *are* the registered loader object.  A
    copyable token, class, name, filename or hash on an unregistered module is
    not sufficient.
    """

    def __init__(self, module_map: dict[str, tuple]):
        self.module_map = module_map
        self._loaders: dict[str, _VerifiedLoader] = {}
        self._modules: dict[str, object] = {}

    def loader_for(self, fullname: str) -> _VerifiedLoader | None:
        entry = self.module_map.get(fullname)
        if entry is None:
            return None
        loader = self._loaders.get(fullname)
        if loader is None:
            source_bytes, _is_package, filename = entry
            loader = _VerifiedLoader(fullname, source_bytes, filename, self)
            self._loaders[fullname] = loader
        return loader

    def module_for(self, fullname: str) -> object | None:
        return self._modules.get(fullname)

    def register_module(self, fullname: str, module: object) -> None:
        self._modules[fullname] = module


class _VerifiedLoader(importlib.abc.Loader):
    """Loads one ``reserved_engine`` module from an immutable verified byte buffer.

    The loader is bound to the snapshot registry that created it and registers
    the executed module object back onto that registry, so a module/loader pair
    can later be checked for exact snapshot membership.
    """

    def __init__(self, fullname: str, source_bytes: bytes, filename: str, registry: _SnapshotRegistry):
        self.fullname = fullname
        self._source_bytes = source_bytes
        self.filename = filename
        self._registry = registry

    def create_module(self, spec):
        return None  # let the import system create the module normally

    def exec_module(self, module) -> None:
        # ``spec_from_loader`` does not mark the spec as having a location, so
        # set the synthetic file path explicitly; it is never used to reopen a
        # file, only for tracebacks and (seeded) source inspection.
        module.__file__ = self.filename
        code = compile(self._source_bytes, self.filename, "exec")
        # Seed linecache with the verified source so tracebacks and inspection
        # present the verified snapshot, never a later-mutated on-disk copy.
        linecache.cache[self.filename] = (
            len(self._source_bytes),
            None,
            self._source_bytes.decode("utf-8").splitlines(keepends=True),
            self.filename,
        )
        exec(code, module.__dict__)
        # Only after successful execution is the exact module object registered
        # as belonging to this verified snapshot.
        self._registry.register_module(self.fullname, module)

    def get_source(self, fullname: str) -> str:
        return self._source_bytes.decode("utf-8")

    def get_code(self, fullname: str):
        return compile(self._source_bytes, self.filename, "exec")


class _VerifiedFinder(importlib.abc.MetaPathFinder):
    """Narrowly scoped finder serving only its own verified snapshot registry."""

    def __init__(self, registry: _SnapshotRegistry):
        self._registry = registry

    def find_spec(self, fullname: str, path=None, target=None):
        entry = self._registry.module_map.get(fullname)
        if entry is None:
            return None  # never service an unrelated or unmanifested import
        loader = self._registry.loader_for(fullname)
        _source_bytes, is_package, filename = entry
        return importlib.util.spec_from_loader(
            fullname, loader, origin=filename, is_package=is_package
        )


# Build-once, shared, verified artefact for the current release run.  The cache
# is bound to the canonical resolved artefact path AND its verified content
# identity, so a changed path or content can never silently return a stale module.
_LOADED: dict | None = None
_FINDER: _VerifiedFinder | None = None


def _purge_reserved_engine() -> None:
    """Remove every ``reserved_engine`` module and the active verified finder.

    Also invalidates the shared cache: after a purge (whether for a switch, a
    failed import, or post-import verification), the previously cached module
    graph is no longer usable and must never be returned as trusted.
    """
    global _FINDER, _LOADED
    for name in [name for name in sys.modules if name == "reserved_engine" or name.startswith("reserved_engine.")]:
        del sys.modules[name]
    # Remove every verified-artefact finder, not only the cached one: a stale
    # finder from a previous snapshot (or a substituted one) must never remain in
    # ``sys.meta_path`` to service a later import of a different snapshot.
    for finder in [f for f in sys.meta_path if isinstance(f, _VerifiedFinder)]:
        sys.meta_path.remove(finder)
    _FINDER = None
    _LOADED = None


def _loaded_offenders(registry: _SnapshotRegistry) -> list[str]:
    """Return descriptions of loaded ``reserved_engine`` modules not exactly bound to the snapshot.

    A module is trusted only when it is the exact module object registered for
    this snapshot, its ``__loader__``/``__spec__.loader`` are the exact
    registered loader object, and the registered loader's own name, filename and
    source bytes still equal the verified module-map entry.  A foreign, previously
    cached, lazily satisfied, substituted or internally-mutated module/loader is
    rejected by identity and value, not by type or naming.
    """
    offenders = []
    for name, mod in list(sys.modules.items()):
        if name != "reserved_engine" and not name.startswith("reserved_engine."):
            continue
        entry = registry.module_map.get(name)
        if entry is None:
            offenders.append(f"{name} -> unmanifested")
            continue
        source_bytes, _is_package, filename = entry
        loader = registry.loader_for(name)
        if loader is None:
            offenders.append(f"{name} -> no registered loader")
            continue
        if registry.module_for(name) is not mod:
            offenders.append(f"{name} -> unregistered module object")
        if getattr(mod, "__loader__", None) is not loader:
            offenders.append(f"{name} -> foreign loader ({type(getattr(mod, '__loader__', None)).__name__})")
        spec = getattr(mod, "__spec__", None)
        if spec is None:
            offenders.append(f"{name} -> missing __spec__")
        elif getattr(spec, "loader", None) is not loader:
            offenders.append(f"{name} -> spec.loader mismatch")
        # The exact registered loader's own fields must equal the verified entry.
        if loader.fullname != name:
            offenders.append(f"{name} -> loader name mismatch")
        if loader.filename != filename:
            offenders.append(f"{name} -> loader filename mismatch")
        if loader._source_bytes != source_bytes:
            offenders.append(f"{name} -> loader source bytes mismatch")
        if getattr(loader, "_registry", None) is not registry:
            offenders.append(f"{name} -> loader registry mismatch")
    return offenders


def _verify_loaded_modules(registry: _SnapshotRegistry) -> None:
    """Raise unless every loaded ``reserved_engine`` module is exactly bound to the snapshot."""
    offenders = _loaded_offenders(registry)
    if offenders:
        raise RuntimeError(
            "reserved_engine module(s) not loaded from the verified snapshot: "
            + "; ".join(offenders)
        )


def _import_from_verified_buffers(target: Path, prov: dict, buffers: dict[str, bytes]) -> object:
    global _FINDER

    module_map = _build_module_map(buffers, target)
    registry = _SnapshotRegistry(module_map)
    _purge_reserved_engine()

    finder = _VerifiedFinder(registry)
    sys.meta_path.insert(0, finder)
    _FINDER = finder

    prev_dont_write = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        module = importlib.import_module("reserved_engine")
        _verify_loaded_modules(registry)
    except Exception:
        _purge_reserved_engine()
        raise
    finally:
        sys.dont_write_bytecode = prev_dont_write

    return module


def load_engine(*, rebuild: bool = False) -> tuple[object, dict]:
    """Import the verified release artefact and return ``(module, provenance)``.

    The artefact is read once into verified byte buffers and executed from
    those buffers; the normal source loader is never used.  Any previously
    imported ``reserved_engine`` (for example the historical
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

    # Reading + verifying the artefact re-verifies content on every call, so a
    # changed, added or removed filesystem file fails here even on a repeat load.
    prov, buffers = _read_verified_artefact(target)
    module_map = _build_module_map(buffers, target)

    if (
        _LOADED is not None
        and _LOADED["path"] == target
        and _LOADED["content_hash"] == prov["content_hash"]
        and _cached_module_graph_is_sound(module_map, _LOADED["module"])
    ):
        return _LOADED["module"], _LOADED["prov"]

    module = _import_from_verified_buffers(target, prov, buffers)
    _reject_new_bytecode(target)

    _LOADED = {
        "path": target,
        "content_hash": prov["content_hash"],
        "module": module,
        "prov": prov,
    }
    return module, prov


def _cached_module_graph_is_sound(module_map: dict[str, tuple], cached_module: object) -> bool:
    """Return ``True`` only if the complete active import state is bound to the verified snapshot.

    A cached return is permitted only when the verified-artefact finder is still
    the first meta-path finder (the position it was installed at), still serves
    exactly the freshly-read verified module map, the top-level package is still
    the one the cache recorded, and every loaded ``reserved_engine`` module is
    the exact registered object with the exact registered loader.  Otherwise the
    graph may have been substituted, detached, reordered or purged, and the
    cache must not return it as trusted.
    """
    global _FINDER
    if not sys.meta_path or sys.meta_path[0] is not _FINDER:
        return False
    if not isinstance(_FINDER, _VerifiedFinder):
        return False
    registry = _FINDER._registry
    if registry.module_map != module_map:
        return False
    if sys.modules.get("reserved_engine") is not cached_module:
        return False
    return _loaded_offenders(registry) == []


def _reject_new_bytecode(target: Path) -> None:
    """Fail closed if bytecode or a cache directory appeared in the artefact."""
    for entry in target.iterdir():
        if entry.name == "__pycache__" or entry.name.endswith(".pyc") or entry.name.endswith(".pyo"):
            raise RuntimeError(f"bytecode appeared in the verified artefact: {entry.name}")
