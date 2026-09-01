from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "skills" / "a-stock-research"
MAIN = ROOT / "SKILL.md"
REFERENCES = {
    "data_cache": ROOT / "references" / "data-cache-contract.md",
    "execution": ROOT / "references" / "research-execution-flow.md",
    "cycle": ROOT / "references" / "cycle-assessment.md",
    "timing": ROOT / "references" / "timing-adjustments.md",
    "report": ROOT / "references" / "report-contract.md",
}


def test_research_skill_routes_each_progressive_disclosure_reference_once() -> None:
    main = MAIN.read_text(encoding="utf-8")

    for path in REFERENCES.values():
        assert path.is_file()
        assert main.count(f"](references/{path.name})") == 1

    assert "周期位置[阶段=" in REFERENCES["cycle"].read_text(encoding="utf-8")
    timing = REFERENCES["timing"].read_text(encoding="utf-8")
    assert "预期差分析" in timing
    assert "除权/除息贴权检查" in timing
    assert "市场风格适配" in timing
    report = REFERENCES["report"].read_text(encoding="utf-8")
    assert "标准评估卡" in report
    assert "操作建议禁止条款" in report
    assert "有界首版本身就是完整报告" in report


def test_analysis_hit_stops_before_full_research_flow() -> None:
    main = MAIN.read_text(encoding="utf-8")
    analysis_hit = main.split("`ANALYSIS_HIT`", 1)[1].split("`FUNDAMENTALS_HIT`", 1)[0]

    assert "终止流程" in analysis_hit
    assert "research-execution-flow.md" not in analysis_hit
    assert "FULL_MISS" in main
    assert "research-execution-flow.md" in main.split("FULL_MISS", 1)[1]


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


def test_research_skill_bounds_first_pass_source_work_and_qa_handoff() -> None:
    main = MAIN.read_text(encoding="utf-8")

    for marker in (
        "有界首版",
        "每批最多 4 个独立查询",
        "不得再探测其他实时行情 Provider",
        "停止新增非阻塞补充检索",
        "已触发的 `incomplete`",
        "price_change_5d",
        "不可变快照",
        "内容哈希",
        "交付副本",
        "本轮唯一临时目录",
        "QA verdict 返回前不得向用户交付完整报告正文",
        "不得轮询",
        "不得用 `sleep` 等待",
    ):
        assert marker in main


def test_a_framework_inputs_and_external_risk_contract_match_qa() -> None:
    main = MAIN.read_text(encoding="utf-8")
    framework_a = (ROOT / "references/frameworks/A.md").read_text(encoding="utf-8")

    assert "A框架每次都必须输出" in main
    assert "状态=正常|受限|重大" in main
    assert "异动、治理/政策与外部集中风险" in main
    assert "gross_margin_stable" in framework_a
    assert "补充指标 JSON" in framework_a
