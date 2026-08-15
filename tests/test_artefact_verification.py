"""
Tests for the verified, build-once, shared release artefact.

Covers the H3 guarantees:
  * the produced bytes are verified against the recorded manifest before use;
  * content identity is computed over the produced bytes, not source hashes;
  * unsupported/unknown/dirty sources are rejected, and the source is exposed;
  * the artefact is immutable/read-only;
  * a single verified artefact is shared, never silently reused or rebuilt;
  * parity is meaningful (the artefact is distinct from production).
"""
import importlib
import importlib.util
import json
import stat
import sys
from pathlib import Path

import pytest

from reserved_west import artefact as art
from reserved_west.artefact import (
    _produced_content_hash,
    artefact_dir,
    load_engine,
    verify_artefact,
)

ROOT = Path(__file__).resolve().parents[1]


def _load_build_module():
    spec = importlib.util.spec_from_file_location(
        "build_engine_artefact", ROOT / "scripts" / "build_engine_artefact.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILD = _load_build_module()


@pytest.fixture()
def built(tmp_path):
    """Build a fresh artefact into a temp directory and return its provenance."""
    out = tmp_path / "reserved_engine"
    prov = BUILD.build(ROOT / "reserved" / "engines", out, allow_dirty=True)
    return out, prov


def _expected_names(prov):
    return set(prov["source_files"]) | {"evidence_uncertainty.py"}


# ── Content identity over produced bytes ─────────────────────────────────────

def test_build_and_loader_content_hash_agree(built):
    out, prov = built
    assert _produced_content_hash(out, _expected_names(prov)) == prov["content_hash"]


def test_content_hash_covers_produced_bytes_not_source_hashes(built):
    out, prov = built
    # The content hash is over the produced (shipped) files, not the recorded
    # source-hash metadata.  Recomputing from produced bytes matches; the
    # source_files metadata is a separate, independent record.
    produced = {}
    for path in sorted(out.iterdir()):
        if path.is_file() and path.name != "PROVENANCE.json":
            produced[path.name] = art._sha256_bytes(path.read_bytes())
    from hashlib import sha256
    expected = sha256(json.dumps(produced, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert expected == prov["content_hash"]
    # The legacy content identity (hash of source-hash metadata) is not the
    # current content identity.
    legacy = sha256(json.dumps(
        {"source_files": prov["source_files"], "evidence_uncertainty": prov["evidence_uncertainty_sha256"]},
        sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    assert legacy != prov["content_hash"]


# ── Verification ─────────────────────────────────────────────────────────────

def test_verify_artefact_accepts_valid_build(built):
    out, prov = built
    assert verify_artefact(out) == prov


def test_verify_artefact_rejects_content_drift(built, tmp_path):
    out, _ = built
    # The artefact is read-only, so make the victim writable before tampering.
    victim = out / "income_tax.py"
    victim.chmod(0o644)
    victim.write_text(victim.read_text() + "\n# tampered\n")
    with pytest.raises(RuntimeError, match="content identity mismatch"):
        verify_artefact(out)


def test_verify_artefact_rejects_provenance_mismatch(built):
    out, _ = built
    prov_file = out / "PROVENANCE.json"
    prov_file.chmod(0o644)
    prov = json.loads(prov_file.read_text())
    prov["content_hash"] = "0" * 64
    prov_file.write_text(json.dumps(prov, indent=2, sort_keys=True) + "\n")
    with pytest.raises(RuntimeError, match="content identity mismatch"):
        verify_artefact(out)


def test_verify_artefact_rejects_unknown_schema(built):
    out, _ = built
    prov_file = out / "PROVENANCE.json"
    prov_file.chmod(0o644)
    prov = json.loads(prov_file.read_text())
    prov["schema"] = "not-a-known-schema"
    prov_file.write_text(json.dumps(prov, indent=2, sort_keys=True) + "\n")
    with pytest.raises(RuntimeError, match="schema"):
        verify_artefact(out)


def test_verify_artefact_rejects_subdirectory(built):
    # The artefact format is flat.  A tampered subdirectory must be rejected,
    # not silently omitted from the content identity (which would let a hidden
    # subpackage evade detection).
    out, _ = built
    out.chmod(0o755)  # make the package dir writable to plant a subdirectory
    subdir = out / "evil"
    subdir.mkdir()
    (subdir / "__init__.py").write_text("# tampered\n")
    with pytest.raises(RuntimeError, match="unsupported subdirectory"):
        verify_artefact(out)


# ── Source selection ─────────────────────────────────────────────────────────

def test_build_exposes_selected_source(built):
    _, prov = built
    assert prov["source_path"] == "reserved/engines"


def test_build_rejects_unknown_source(tmp_path):
    bogus = tmp_path / "bogus"
    bogus.mkdir()
    with pytest.raises(SystemExit, match="not a recognised engine package"):
        BUILD.build(bogus, tmp_path / "out", allow_dirty=True)


def test_build_rejects_dirty_source(monkeypatch, tmp_path):
    monkeypatch.setattr(
        BUILD, "_dirty_source_paths", lambda source, evidence: ["reserved/engines/income_tax.py"]
    )
    with pytest.raises(SystemExit, match="dirty source"):
        BUILD.build(ROOT / "reserved" / "engines", tmp_path / "out")


# ── Immutability ─────────────────────────────────────────────────────────────

def test_built_artefact_files_are_read_only(built):
    out, _ = built
    for path in out.iterdir():
        if path.is_file():
            mode = stat.S_IMODE(path.stat().st_mode)
            assert mode & 0o222 == 0, f"{path.name} is writable ({oct(mode)})"


# ── Build-once, shared, verified ─────────────────────────────────────────────

def test_load_engine_shares_one_verified_artefact(monkeypatch):
    # Reset the module cache so this test observes a fresh load.
    import reserved_west.artefact as a
    monkeypatch.setattr(a, "_LOADED", None)
    module_a, prov_a = load_engine()
    module_b, prov_b = load_engine()
    assert module_a is module_b
    assert prov_a == prov_b
    assert prov_a["content_hash"] == _produced_content_hash(
        artefact_dir(), _expected_names(prov_a)
    )


def test_artefact_is_distinct_from_production():
    # Parity is meaningful only if the artefact is a distinct module from the
    # mutable production tree — not the same object passed through.
    load_engine()  # ensure dist/ is on sys.path and reserved_engine is importable
    import reserved.engines as prod
    import reserved_engine as released

    assert prod.__file__ != released.__file__
    assert Path(released.__file__).resolve().is_relative_to(artefact_dir().resolve())


# ── Loader identity: a preloaded foreign module must never be returned ───────

def test_load_engine_rejects_preloaded_foreign_module(tmp_path, monkeypatch):
    # A foreign/historical ``reserved_engine`` already in ``sys.modules`` must
    # not be returned by the first ordinary ``load_engine()`` call, and must
    # not be able to bypass artefact verification.
    foreign = tmp_path / "foreign"
    pkg = foreign / "reserved_engine"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("MARKER = 'FOREIGN'\n")
    monkeypatch.syspath_prepend(str(foreign))
    foreign_module = importlib.import_module("reserved_engine")

    monkeypatch.setattr(art, "_LOADED", None)
    module, prov = load_engine()

    assert module is not foreign_module
    assert not hasattr(module, "MARKER")
    assert Path(module.__file__).resolve().is_relative_to(artefact_dir().resolve())
    assert prov["engine_version"] == module.ENGINE_VERSION


def test_load_engine_switches_artefact_in_one_process(tmp_path, monkeypatch):
    # Two different valid artefacts loaded in sequence must each resolve to the
    # correct module, never the cached module from the previous location.
    # The artefact package directory must be named ``reserved_engine`` (the
    # loader inserts its parent on sys.path and imports by that package name).
    out_a = tmp_path / "a" / "reserved_engine"
    prov_a = BUILD.build(ROOT / "reserved" / "engines", out_a, allow_dirty=True)

    src_b = tmp_path / "src_b"
    src_b.mkdir()
    for py in (ROOT / "reserved" / "engines").glob("*.py"):
        (src_b / py.name).write_text(py.read_text())
    (src_b / "CHANGELOG.md").write_text((ROOT / "reserved" / "engines" / "CHANGELOG.md").read_text())
    init = src_b / "__init__.py"
    init.write_text(init.read_text() + "\nARTEFACT_B_MARKER = 'B'\n")
    out_b = tmp_path / "b" / "reserved_engine"
    BUILD.build(src_b, out_b, allow_dirty=True)

    try:
        monkeypatch.setattr(art, "_LOADED", None)
        monkeypatch.setenv("RESERVED_ENGINE_ARTEFACT", str(out_a))
        mod_a, _ = load_engine()
        assert Path(mod_a.__file__).resolve().is_relative_to(out_a.resolve())
        assert not hasattr(mod_a, "ARTEFACT_B_MARKER")

        monkeypatch.setattr(art, "_LOADED", None)
        monkeypatch.setenv("RESERVED_ENGINE_ARTEFACT", str(out_b))
        mod_b, prov_b = load_engine()
        assert Path(mod_b.__file__).resolve().is_relative_to(out_b.resolve())
        assert hasattr(mod_b, "ARTEFACT_B_MARKER")
        assert mod_b is not mod_a
        assert prov_b["content_hash"] != prov_a["content_hash"]
    finally:
        # Restore a clean loader state so later tests observe a fresh default load.
        art._purge_reserved_engine()
        art._LOADED = None


# ── A1: reject unverified executable content ─────────────────────────────────

def _writable(out):
    out.chmod(0o755)
    for child in out.iterdir():
        if child.is_file():
            child.chmod(0o644)


def test_verify_artefact_rejects_pycache(built):
    out, _ = built
    _writable(out)
    cache = out / "__pycache__"
    cache.mkdir()
    (cache / "evil.cpython-313.pyc").write_bytes(b"\x00")
    with pytest.raises(RuntimeError, match="subdirectory"):
        verify_artefact(out)


def test_verify_artefact_rejects_pyc_file(built):
    out, _ = built
    _writable(out)
    (out / "extra.pyc").write_bytes(b"\x00")
    with pytest.raises(RuntimeError, match="unmanifested bytecode"):
        verify_artefact(out)


def test_verify_artefact_rejects_unexpected_file(built):
    out, _ = built
    _writable(out)
    (out / "extra_module.py").write_text("# surprise\n")
    with pytest.raises(RuntimeError, match="unexpected file"):
        verify_artefact(out)


def test_verify_artefact_rejects_symlink(built):
    out, _ = built
    _writable(out)
    victim = out / "income_tax.py"
    link = out / "link.py"
    link.symlink_to(victim.name)
    with pytest.raises(RuntimeError, match="symbolic link"):
        verify_artefact(out)


def test_verify_artefact_rejects_missing_manifested_file(built):
    out, _ = built
    _writable(out)
    (out / "income_tax.py").unlink()
    with pytest.raises(RuntimeError, match="missing manifested file"):
        verify_artefact(out)


# ── A2: bytecode is never created in the artefact ────────────────────────────

def test_load_engine_does_not_create_bytecode(built, monkeypatch):
    out, _ = built
    before = sys.dont_write_bytecode
    monkeypatch.setattr(art, "_LOADED", None)
    monkeypatch.setenv("RESERVED_ENGINE_ARTEFACT", str(out))
    load_engine()
    names = {p.name for p in out.iterdir()}
    assert "__pycache__" not in names
    assert not any(n.endswith(".pyc") or n.endswith(".pyo") for n in names)
    assert sys.dont_write_bytecode == before  # global interpreter state restored


def test_built_artefact_package_directory_is_not_writable(built):
    out, _ = built
    mode = stat.S_IMODE(out.stat().st_mode)
    assert mode & 0o222 == 0, f"package directory is writable ({oct(mode)})"


# ── A3: every imported module resolves beneath the artefact ──────────────────

def test_load_engine_verifies_submodules_resolve_beneath_artefact(built, monkeypatch):
    out, _ = built
    monkeypatch.setattr(art, "_LOADED", None)
    monkeypatch.setenv("RESERVED_ENGINE_ARTEFACT", str(out))
    module, _ = load_engine()
    # A lazy import after initial verification must resolve inside the artefact.
    import importlib
    sub = importlib.import_module("reserved_engine.income_tax")
    assert Path(sub.__file__).resolve().is_relative_to(out.resolve())
    assert module.__file__.endswith("__init__.py")


def test_load_engine_rejects_foreign_submodule(tmp_path, monkeypatch):
    # A foreign submodule already present under the package name must not
    # survive a fresh load, and must not be satisfied lazily afterwards.
    foreign = tmp_path / "foreign"
    pkg = foreign / "reserved_engine"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("MARKER = 'FOREIGN'\n")
    (pkg / "income_tax.py").write_text("SUBMARKER = 'FOREIGN_SUB'\n")
    monkeypatch.syspath_prepend(str(foreign))
    import reserved_engine.income_tax  # noqa: F401 — preload foreign submodule

    monkeypatch.setattr(art, "_LOADED", None)
    module, _ = load_engine()
    assert not hasattr(module, "MARKER")
    import reserved_engine.income_tax as sub
    assert not hasattr(sub, "SUBMARKER")
    assert Path(sub.__file__).resolve().is_relative_to(artefact_dir().resolve())


# ── A4: loader cache bound to path + content identity ────────────────────────

def _build_marked(tmp_path, marker):
    src = tmp_path / f"src_{marker}"
    src.mkdir()
    for py in (ROOT / "reserved" / "engines").glob("*.py"):
        (src / py.name).write_text(py.read_text())
    (src / "CHANGELOG.md").write_text((ROOT / "reserved" / "engines" / "CHANGELOG.md").read_text())
    (src / "__init__.py").write_text((src / "__init__.py").read_text() + f"\nMARK = '{marker}'\n")
    out = tmp_path / marker / "reserved_engine"
    BUILD.build(src, out, allow_dirty=True)
    return out


def test_load_engine_switches_a_to_b_and_back_without_manual_cache_clear(tmp_path, monkeypatch):
    out_a = _build_marked(tmp_path, "a")
    out_b = _build_marked(tmp_path, "b")

    monkeypatch.setattr(art, "_LOADED", None)
    monkeypatch.setenv("RESERVED_ENGINE_ARTEFACT", str(out_a))
    mod_a, _ = load_engine()
    assert mod_a.MARK == "a"

    # Switching the configured path must load B, not silently return A.
    monkeypatch.setenv("RESERVED_ENGINE_ARTEFACT", str(out_b))
    mod_b, _ = load_engine()
    assert mod_b.MARK == "b"
    assert mod_b is not mod_a

    # And back to A.
    monkeypatch.setenv("RESERVED_ENGINE_ARTEFACT", str(out_a))
    mod_a2, _ = load_engine()
    assert mod_a2.MARK == "a"


def test_load_engine_rejects_same_path_with_modified_content(built, monkeypatch):
    out, prov = built
    monkeypatch.setattr(art, "_LOADED", None)
    monkeypatch.setenv("RESERVED_ENGINE_ARTEFACT", str(out))
    load_engine()

    _writable(out)
    victim = out / "income_tax.py"
    victim.write_text(victim.read_text() + "\n# tampered\n")

    with pytest.raises(RuntimeError, match="content identity mismatch"):
        load_engine()


def test_load_engine_rejects_same_path_with_added_file(built, monkeypatch):
    out, _ = built
    monkeypatch.setattr(art, "_LOADED", None)
    monkeypatch.setenv("RESERVED_ENGINE_ARTEFACT", str(out))
    load_engine()

    _writable(out)
    (out / "new_module.py").write_text("# added\n")

    with pytest.raises(RuntimeError, match="unexpected file"):
        load_engine()


def test_load_engine_rejects_same_path_with_missing_file(built, monkeypatch):
    out, _ = built
    monkeypatch.setattr(art, "_LOADED", None)
    monkeypatch.setenv("RESERVED_ENGINE_ARTEFACT", str(out))
    load_engine()

    _writable(out)
    (out / "income_tax.py").unlink()

    with pytest.raises(RuntimeError, match="missing manifested file"):
        load_engine()


def test_load_engine_rejects_changed_manifest(built, monkeypatch):
    out, _ = built
    monkeypatch.setattr(art, "_LOADED", None)
    monkeypatch.setenv("RESERVED_ENGINE_ARTEFACT", str(out))
    load_engine()

    _writable(out)
    prov_file = out / "PROVENANCE.json"
    prov = json.loads(prov_file.read_text())
    prov["content_hash"] = "0" * 64
    prov_file.write_text(json.dumps(prov, indent=2, sort_keys=True) + "\n")

    with pytest.raises(RuntimeError, match="content identity mismatch"):
        load_engine()


def test_load_engine_does_not_leave_stale_artefact_parent_in_sys_path(tmp_path, monkeypatch):
    out_a = _build_marked(tmp_path, "a")
    out_b = _build_marked(tmp_path, "b")

    monkeypatch.setattr(art, "_LOADED", None)
    monkeypatch.setenv("RESERVED_ENGINE_ARTEFACT", str(out_a))
    load_engine()
    assert str(out_a.parent) in sys.path

    monkeypatch.setenv("RESERVED_ENGINE_ARTEFACT", str(out_b))
    load_engine()
    # The previous artefact's parent must not remain on sys.path.
    assert str(out_a.parent) not in sys.path
    assert str(out_b.parent) in sys.path
