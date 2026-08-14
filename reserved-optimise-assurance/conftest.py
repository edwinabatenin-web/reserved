"""
Initiative 002 — pytest configuration.

Test discovery: run from workspace root with
    PYTHONPATH=. pytest reserved-optimise-assurance/tests/ -v

Or from inside the directory:
    PYTHONPATH=reserved-optimise-assurance:. pytest tests/ -v
"""
import sys
from pathlib import Path

# Ensure the assurance package and the workspace root are on the path
# so both reference/ imports and reserved.engines imports work.
HERE = Path(__file__).parent
WORKSPACE = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(WORKSPACE))
