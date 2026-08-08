from __future__ import annotations

import json
from pathlib import Path

from scripts.compare_shadow_results import compare


def test_shadow_comparison_ignores_prose(tmp_path: Path) -> None:
    payload = {"framework": "A", "hard_score": 60, "red_lines": [], "data_gaps": [], "fail_closed": False}
    for client in ("claude", "codex", "hermes"):
        directory = tmp_path / client
        directory.mkdir()
        (directory / "invariants.json").write_text(json.dumps({**payload, "prose": client}), encoding="utf-8")
    assert compare(tmp_path) == []
