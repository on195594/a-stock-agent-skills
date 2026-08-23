from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "skills" / "a-stock-research"
MAIN = ROOT / "SKILL.md"
REFERENCES = {
    "cycle": ROOT / "references" / "cycle-assessment.md",
    "timing": ROOT / "references" / "timing-adjustments.md",
    "report": ROOT / "references" / "report-contract.md",
}


def test_research_skill_uses_three_progressive_disclosure_references() -> None:
    main = MAIN.read_text(encoding="utf-8")

    for path in REFERENCES.values():
        assert path.is_file()
        assert f"](references/{path.name})" in main

    assert "周期位置[阶段=" in REFERENCES["cycle"].read_text(encoding="utf-8")
    timing = REFERENCES["timing"].read_text(encoding="utf-8")
    assert "预期差分析" in timing
    assert "除权/除息贴权检查" in timing
    assert "市场风格适配" in timing
    report = REFERENCES["report"].read_text(encoding="utf-8")
    assert "标准评估卡" in report
    assert "操作建议禁止条款" in report


def test_research_skill_keeps_hard_boundaries_in_main_entrypoint() -> None:
    main = MAIN.read_text(encoding="utf-8")

    for marker in (
        "--confirm-write",
        "a-stock-fetch fetch <股票代码>",
        "禁止并行",
        "最新中报/季报冲突门",
        "industry_status=stale_cache",
        "估值项进入 `incomplete`",
        "raw = 估值分 + 市场情绪分 + 周期调整 + 预期差调整 + 除权/除息调整 + 市场风格调整 + 异动股调整",
        "唯一操作出口",
        "a-stock-qa",
    ):
        assert marker in main

    assert "## 第1.5步：周期位置判断" in main
    assert "## 第三步：择时评分" in main
    assert "## 输出格式" in main
