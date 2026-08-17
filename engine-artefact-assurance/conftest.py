"""
Engine-artefact assurance — pytest bootstrap.

Ensures the deterministic release artefact is built and importable, and
exposes a session-scoped fixture returning ``(module, provenance)``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Build (if necessary) and import the artefact at collection time so test
# modules can import ``reserved_engine`` at module scope.
from reserved_west.artefact import load_engine  # noqa: E402

_ENGINE, _PROVENANCE = load_engine()


@pytest.fixture(scope="session")
def engine():
    """The built release artefact: ``(module, provenance)``."""
    return _ENGINE, _PROVENANCE
