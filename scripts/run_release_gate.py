#!/usr/bin/env python3
"""
Reserved — canonical release gate CLI.

Runs the single canonical gate (``reserved_west.release_gate``), renders its
structured result, persists it to ``dist/release_gate_result.json`` for the
metadata generator to consume, and exits non-zero on failure.

This CLI does not maintain its own suite inventory or decision logic: both live
in ``reserved_west.release_gate`` so the CLI and the metadata generator can
never drift apart.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULT_PATH = ROOT / "dist" / "release_gate_result.json"


def main() -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from reserved_west.release_gate import render_result, run_canonical_gate

    result = run_canonical_gate()

    RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(render_result(result))
    return 0 if result["overall_decision"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
