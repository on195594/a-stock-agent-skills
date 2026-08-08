from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_qa_is_runtime_independent() -> None:
    skill = (ROOT / "skills/a-stock-qa/SKILL.md").read_text(encoding="utf-8")
    assert "Python" not in skill.split("---", 2)[1]
    assert "a_stock_agent_runtime" not in skill
    assert "research rubric" in skill


def test_standalone_smoke_uses_isolated_python() -> None:
    result = subprocess.run(
        [sys.executable, "-I", str(ROOT / "tests/qa/standalone_smoke.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
