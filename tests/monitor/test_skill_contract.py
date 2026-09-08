import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "skills" / "a-stock-monitor"
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
DAILY_MONITORING = ROOT / "references" / "daily-monitoring-and-l3.md"
VALUATION_REVIEW = ROOT / "references" / "valuation-and-annual-review.md"
CD_ACCUMULATION = (ROOT / "references" / "step3.5-cd-accumulation.md").read_text(
    encoding="utf-8"
)
TIER_RULES = (ROOT / "references" / "step4-tier-system.md").read_text(encoding="utf-8")
PORTFOLIO_RISK = (ROOT / "references" / "portfolio-risk.md").read_text(encoding="utf-8")
DECISIONS = json.loads(
    (ROOT / "references" / "decision-table.json").read_text(encoding="utf-8")
)


def test_daily_checklist_is_complete_and_unique():
    ids = re.findall(r"^\| (C\d{2}) \|", SKILL, flags=re.MULTILINE)
    assert ids == [f"C{number:02d}" for number in range(1, 11)]
    assert len(ids) == len(set(ids))
    assert SKILL.count("## Level 2 日常深度复核唯一检查表") == 1


def test_generic_single_holding_request_has_bounded_delivery_contract():
    assert "## 日常监控两级路由与停止合同" in SKILL
    assert "monitor-snapshot --portfolio-value <账户总资产> --json" in SKILL
    assert "stop_reason=clean_fast_gate" in SKILL
    assert "研究子代理数必须为 0" in SKILL
    assert "## 单股泛化请求的快速交付合同" in SKILL
    assert "只有命中 Level 2 路由时 C01—C10 才须全部完成" in SKILL
    assert "聚合检索最多一个批次" in SKILL
    assert "正式报告提取最多使用两种方法" in SKILL
    assert "优先复用 `a-stock-fetch`" in SKILL
    assert "对明确的单个文件执行一次有界提取" in SKILL
    assert "monitor 任务不得加载或调用该 Skill" in SKILL
    assert "合规项直接标记 `SKIP`" in SKILL


def test_decision_table_rule_ids_and_priorities_are_unique():
    rules = DECISIONS["rules"]
    assert DECISIONS["schema_version"] == 1
    assert len({rule["id"] for rule in rules}) == len(rules)
    assert len({rule["priority"] for rule in rules}) == len(rules)


def test_trade_proposals_require_confirmation_and_executable_sizing():
    trade_effects = {"propose_trade", "allow_trade_proposal"}
    for rule in DECISIONS["rules"]:
        assert rule["effect"] != "execute_trade"
        if rule["effect"] in trade_effects:
            assert rule["requires_user_confirmation"] is True
            assert rule["requires_executable_sizing"] is True


def test_financial_deterioration_is_review_not_direct_trade():
    rule = next(rule for rule in DECISIONS["rules"] if rule["id"] == "D03")
    assert rule["effect"] == "open_red_alert_and_framework_review"
    assert rule["action_source"] == "none"


def test_roe_warning_and_red_review_are_separate_rules():
    by_id = {rule["id"]: rule for rule in DECISIONS["rules"]}
    assert by_id["D03Y"]["condition"] == "roe_yoy_drop_gt_3pts_two_quarters"
    assert by_id["D03Y"]["effect"] == "open_yellow_alert"
    assert "roe_yoy_drop_gt_5pts_two_quarters" in by_id["D03"]["condition"]


def test_add_risk_requires_portfolio_risk_preconditions():
    by_id = {rule["id"]: rule for rule in DECISIONS["rules"]}
    required = {
        "portfolio_value_known",
        "single_name_risk_within_budget",
        "portfolio_risk_within_budget",
        "not_in_drawdown_breach_state",
    }
    assert required <= set(by_id["D09"]["preconditions"])


def test_portfolio_risk_names_drawdown_and_fails_closed_on_cost_drift():
    assert "单股当前净值回撤贡献" in PORTFOLIO_RISK
    assert "它不是买入本金亏损，也不是现价距离止损线的“安全垫”" in PORTFOLIO_RISK
    assert "成本比例派生的止损/Tier只可展示来源，不得授权对应交易" in PORTFOLIO_RISK
    assert "账户盈亏成本来源、规则参考成本来源及对账状态" in PORTFOLIO_RISK


def test_thesis_break_outranks_stops_tiers_and_accumulation():
    priorities = {rule["id"]: rule["priority"] for rule in DECISIONS["rules"]}
    assert priorities["D01"] > priorities["D04"] > priorities["D07"] > priorities["D09"]


def test_unvalidated_mechanical_thresholds_are_marked_heuristic():
    by_id = {rule["id"]: rule for rule in DECISIONS["rules"]}
    for rule_id in ("D04", "D05", "D06", "D07", "D08", "D09"):
        assert by_id[rule_id]["heuristic"] is True


def test_skill_has_no_known_invalid_500_share_split_or_legacy_sale_path():
    assert "167股（剩333）" not in SKILL
    assert "update-return <代码> <实际回报%>" not in SKILL
    assert "references/decision-table.json" in SKILL


def test_all_routed_reference_files_exist():
    paths = set(re.findall(r"`(references/[^`]+)`", SKILL))
    for relative in paths:
        assert (ROOT / relative).exists(), relative


def test_phase2_routes_are_unique_and_keep_fail_closed_boundaries_in_main():
    for path in (DAILY_MONITORING, VALUATION_REVIEW):
        assert path.is_file()
        assert SKILL.count(f"`references/{path.name}`") == 1

    for marker in (
        "--confirm-write",
        "C01—C10",
        "动作优先级",
        "缺失数据不等于已排除/未触发",
        "操作价格依据要求",
        "建议/授权/成交",
        "行情或状态无法验证时必须 fail-closed",
    ):
        assert marker in SKILL


def test_cd_accumulation_keeps_cumulative_cap_while_allowing_one_lot():
    assert "max(100股, initial_shares 的1/3)" in CD_ACCUMULATION
    assert "累计增持总量仍不得超过 `initial_shares`" in CD_ACCUMULATION

    def single_op_cap(initial_shares: int, cumulative_additions: int) -> int:
        return min(max(100, initial_shares / 3), initial_shares - cumulative_additions)

    assert single_op_cap(100, 0) == 100
    assert single_op_cap(200, 0) == 100
    assert single_op_cap(200, 100) == 100
    assert single_op_cap(200, 200) == 0


def test_tier1_rebuild_explicitly_resets_only_tier1():
    assert "tier-update <代码> tier1 pending" in TIER_RULES
    assert "Tier2/Tier3 状态保持不变" in TIER_RULES


def test_monitor_has_no_ambiguous_direct_sell_shortcuts():
    assert "净利增速转负｜监管重大转向" not in SKILL
    assert "重大利空公告时立即清仓" not in TIER_RULES
    assert "3pts=黄色预警入口" in SKILL
    assert "5pts=红色框架复核入口" in SKILL
