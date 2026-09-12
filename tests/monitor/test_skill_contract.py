import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "skills" / "a-stock-monitor"
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
DAILY_MONITORING = (ROOT / "references" / "daily-monitoring-and-l3.md").read_text(
    encoding="utf-8"
)
VALUATION_REVIEW = (ROOT / "references" / "valuation-and-annual-review.md").read_text(
    encoding="utf-8"
)
DATA_OPERATIONS = (ROOT / "references" / "data-operations.md").read_text(
    encoding="utf-8"
)
CD_ACCUMULATION = (ROOT / "references" / "step3.5-cd-accumulation.md").read_text(
    encoding="utf-8"
)
TIER_RULES = (ROOT / "references" / "step4-tier-system.md").read_text(encoding="utf-8")
PORTFOLIO_RISK = (ROOT / "references" / "portfolio-risk.md").read_text(encoding="utf-8")
DECISIONS = json.loads(
    (ROOT / "references" / "decision-table.json").read_text(encoding="utf-8")
)


def test_level2_checklist_semantics_remain_owned_after_main_is_thinned():
    # Deterministic checklist rows must not be duplicated in the entrypoint.
    assert not re.search(r"^\| C\d{2} \|", SKILL, flags=re.MULTILINE)

    # Preserve the substantive C01-C10 coverage at its authoritative owners.
    for contract, owner in (
        ("单股当前净值回撤贡献", PORTFOLIO_RISK),
        ("framework/framework_confident", PORTFOLIO_RISK),
        ("alerts <代码>", DAILY_MONITORING),
        ("明显弱于所属行业指数 ≥2pts", DAILY_MONITORING),
        ("实际止损线由 `cache.py`", DAILY_MONITORING),
        ("L3 全量核查强制要求", DAILY_MONITORING),
        ("不得直接清仓", DAILY_MONITORING),
        ("各框架触发线", VALUATION_REVIEW),
        ("技术卖出候选", VALUATION_REVIEW),
        ("校验交易所整手/零股申报约束", DATA_OPERATIONS),
    ):
        assert contract in owner


def test_generic_single_holding_request_has_bounded_delivery_contract():
    assert "### Level 1：默认快照" in SKILL
    assert "monitor-snapshot --portfolio-value <账户总资产> --json" in SKILL
    assert "干净快速路径" in SKILL and "立即停止" in SKILL
    assert "只加载与 runtime 升级原因相符的资料" in SKILL
    assert "默认不启动研究子代理" in SKILL
    assert "a-stock-qa` 尚无 monitor rubric" in SKILL
    assert "监控任务不得调用它" in SKILL


def test_level1_failure_snapshot_and_context_contract_is_bounded():
    for marker in (
        "有效 JSON 后退出非零",
        "阻断、复核候选、触发、到期、异常或冲突",
        "`escalations` 指定的持仓和证据",
        "缺少 required 数据",
        "冻结相关交易与风险变更",
    ):
        assert marker in SKILL


def test_daily_monitoring_has_a_hard_tool_call_budget():
    for marker in (
        "Level 1 固定为一次 `monitor-snapshot`",
        "不得额外调用 `holdings`、Wiki、Web 或子代理",
        "每个相关主题只取一个主来源",
        "仅失败、不完整、过期或冲突时允许一次 fallback",
        "默认不启动研究子代理",
    ):
        assert marker in SKILL


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


def test_skill_has_no_known_invalid_split_or_legacy_sale_path():
    corpus = SKILL + TIER_RULES + VALUATION_REVIEW
    assert "167股（剩333）" not in corpus
    assert "update-return <代码> <实际回报%>" not in corpus
    assert "references/decision-table.json" in SKILL


def test_all_routed_reference_files_exist():
    paths = set(re.findall(r"`(references/[^`]+)`", SKILL))
    for relative in paths:
        assert (ROOT / relative).exists(), relative


def test_phase5_routes_are_unique_and_keep_fail_closed_boundaries_in_main():
    for name in (
        "daily-monitoring-and-l3.md",
        "valuation-and-annual-review.md",
        "step3.5-cd-accumulation.md",
        "step4-tier-system.md",
        "data-operations.md",
        "portfolio-risk.md",
        "decision-table.json",
    ):
        assert SKILL.count(f"references/{name}") == 1

    for marker in (
        "--confirm-write",
        "动作冲突只服从",
        "数据缺失、过期、冲突、不可交易或 runtime 失败时 fail-closed",
        "不得补造触发、股数或成交",
        "建议、授权、申报与成交必须分开",
    ):
        assert marker in SKILL

    # Thresholds and state machines belong to runtime/library/references, not main.
    for detail in ("≥3%", "成本 × 1.25", "候选信号 → 待确认 → 已确认触发"):
        assert detail not in SKILL


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
    assert "3pts=黄色预警入口" in VALUATION_REVIEW
    assert "5pts=红色框架复核入口" in VALUATION_REVIEW
    assert "两级条件都不是独立卖出授权" in VALUATION_REVIEW
