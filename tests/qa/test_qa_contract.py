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
    assert "monitoring report" not in skill
    assert "a-stock-monitor report" not in skill


def test_research_qa_routing_is_host_neutral() -> None:
    research = (ROOT / "skills/a-stock-research/SKILL.md").read_text(encoding="utf-8")
    assert "a-stock-qa" in research
    for client_command in ("agy --", "codex:", "claude:", "hermes:"):
        assert client_command not in research.lower()


def test_qa_verdict_is_bound_to_an_immutable_report_snapshot() -> None:
    qa_skill = (ROOT / "skills/a-stock-qa/SKILL.md").read_text(encoding="utf-8")

    assert "不可变快照" in qa_skill
    assert "唯一版本路径" in qa_skill
    assert "仅适用于该快照" in qa_skill
    assert "新快照" in qa_skill and "重新执行 QA" in qa_skill
    assert "内容哈希" in qa_skill
    assert "再次核对" in qa_skill


def test_held_stock_route_hard_stops_research_work() -> None:
    research = (ROOT / "skills/a-stock-research/SKILL.md").read_text(encoding="utf-8")
    assert "a-stock-cache holdings <股票代码>" in research
    assert "确认已持仓后立即终止本 Skill" in research
    assert "不得继续执行首次研究的 fetch/check、评分或 QA" in research
    assert "HOLDINGS_UNAVAILABLE" in research


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
    rubric = (
        ROOT / "skills/a-stock-qa/references/rubrics/a-stock-research.md"
    ).read_text(encoding="utf-8")
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
    assert "静态PE（`pe_static`" in research
    assert "`pe_ttm` 仅为 deprecated 兼容别名" in research


def test_investment_review_repairs_are_part_of_the_research_and_qa_contract() -> None:
    rubric = (
        ROOT / "skills/a-stock-qa/references/rubrics/a-stock-research.md"
    ).read_text(encoding="utf-8")
    research = (ROOT / "skills/a-stock-research/SKILL.md").read_text(encoding="utf-8")
    resource = (ROOT / "skills/a-stock-research/references/frameworks/C.md").read_text(
        encoding="utf-8"
    )

    assert "综合得分参考阈值" not in research
    assert "可用资金 × 该股仓位建议比例" not in research
    assert "唯一操作出口" in research
    assert "已批准的单股风险上限" in research
    assert "估值冲突" in resource
    assert "AISC" in resource
    assert "最高只能给格档" in resource
    assert "估值算术与报告期一致性" in rubric
    assert "唯一决策出口与仓位范围" in rubric
    assert "C资源估值冲突与成本证据" in rubric
    assert "关键择时数据缺失或估值冲突明确进入 `incomplete`" in rubric


def test_second_investment_review_fail_closed_contract() -> None:
    rubric = (
        ROOT / "skills/a-stock-qa/references/rubrics/a-stock-research.md"
    ).read_text(encoding="utf-8")
    qa_skill = (ROOT / "skills/a-stock-qa/SKILL.md").read_text(encoding="utf-8")
    research = (ROOT / "skills/a-stock-research/SKILL.md").read_text(encoding="utf-8")

    assert "不得用10年分位替代5年分位" in research
    assert "最新中报/季报冲突门" in research
    assert "B框架三项核心数据全缺" in research
    assert "亏损 Biotech" in research and "定性路线" in research
    assert "估值项进入 `incomplete`" in research
    assert "评分上限仍为10/15" not in research
    assert "估值项记0/15" in research
    assert "只输出观察/试探/标准阶段标签" in research
    assert "industry_status=stale_cache" in research
    assert "关键估值能力与最新财报核验" in rubric
    assert "银行核心数据完整性" in rubric
    assert "QA PASS 仅代表报告文本符合流程规则" in qa_skill


def test_wuxi_retro_repairs_are_pinned_in_research_and_qa_contracts() -> None:
    qa_skill = (ROOT / "skills/a-stock-qa/SKILL.md").read_text(encoding="utf-8")
    rubric = (
        ROOT / "skills/a-stock-qa/references/rubrics/a-stock-research.md"
    ).read_text(encoding="utf-8")
    research = (ROOT / "skills/a-stock-research/SKILL.md").read_text(encoding="utf-8")
    framework_a = (
        ROOT / "skills/a-stock-research/references/frameworks/A.md"
    ).read_text(encoding="utf-8")

    fetch_pos = research.index("a-stock-fetch fetch <股票代码>")
    check_pos = research.index("a-stock-cache check <股票代码>")
    assert fetch_pos < check_pos
    assert "禁止并行" in research
    assert "pe_static" in research and "pe_percentile_5y" in research
    assert "ps_ttm" in research and "ps_percentile_5y" in research
    assert "latest_report_snapshot" in research
    for reference in (
        "references/frameworks/A.md",
        "references/frameworks/B.md",
        "references/frameworks/C.md",
        "references/frameworks/D.md",
        "references/frameworks/E.md",
        "references/frameworks/F.md",
        "references/frameworks/step8-graham.md",
        "references/catalyst-cycle-analysis.md",
    ):
        assert f"]({reference})" in research

    assert "INVALID_RUN" in qa_skill
    assert "INVALID_RUN →" in research
    assert "任意 Critical/Important" in qa_skill
    assert "Advisory" in qa_skill and "不得影响 verdict" in qa_skill
    assert "](references/rubrics/a-stock-research.md)" in qa_skill
    assert "外部集中风险" in framework_a
    assert "置信度受限" in research
    assert "外部集中风险覆盖" in rubric
    assert "pe_percentile_5y" in rubric
    assert "ps_percentile_5y" in rubric
    assert "latest_report_snapshot" in rubric
