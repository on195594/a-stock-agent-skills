#!/usr/bin/env python3
"""Minimal QA discovery/execution smoke with only the standard library."""
from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills" / "a-stock-qa" / "SKILL.md"
RUBRIC = ROOT / "skills" / "a-stock-qa" / "references" / "rubrics" / "a-stock-research.md"


def verdict(report: str, skill_type: str) -> str:
    if skill_type != "a-stock-research" or not RUBRIC.is_file():
        return "SKIP"
    required = ("数据", "评分", "报告")
    return "COMPLIANT" if all(token in report for token in required) else "NON_COMPLIANT"


def main() -> int:
    assert SKILL.is_file() and RUBRIC.is_file()
    assert "a_stock_agent_runtime" not in SKILL.read_text(encoding="utf-8")
    assert verdict("完整研究报告：数据完整，评分已记录", "a-stock-research") == "COMPLIANT"
    assert verdict("缺步骤", "a-stock-research") == "NON_COMPLIANT"
    assert verdict("anything", "a-stock-monitor") == "SKIP"
    assert not re.search(r"import (requests|pandas|a_stock_agent_runtime)", SKILL.read_text(encoding="utf-8"))
    print("qa standalone smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
