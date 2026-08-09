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


def test_research_routing_and_checklist_rubric_match_research_skill() -> None:
    rubric = (ROOT / "skills/a-stock-qa/references/rubrics/a-stock-research.md").read_text(
        encoding="utf-8"
    )
    research = (ROOT / "skills/a-stock-research/SKILL.md").read_text(encoding="utf-8")
    bank = (ROOT / "skills/a-stock-research/references/frameworks/B.md").read_text(
        encoding="utf-8"
    )

    assert "商业银行→B" in rubric
    assert "保险/券商/证券→不适用量化框架" in rubric
    assert "所有 A-F 量化框架" in rubric
    assert "B/D/E 框架不需要 checklist" not in rubric
    assert "不得套用 B 框架" in bank
    assert "保险/券商/证券" in research
    assert "静态PE（缓存字段 `pe_ttm`，不能作为真正 PE_TTM 用于 PEG）" in research
