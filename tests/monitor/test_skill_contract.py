import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2] / "skills" / "a-stock-monitor"
SKILL = (ROOT / "SKILL.md").read_text(encoding="utf-8")
CD_ACCUMULATION = (ROOT / "references" / "step3.5-cd-accumulation.md").read_text(
    encoding="utf-8"
)
TIER_RULES = (ROOT / "references" / "step4-tier-system.md").read_text(encoding="utf-8")
DECISIONS = json.loads(
    (ROOT / "references" / "decision-table.json").read_text(encoding="utf-8")
)


def test_daily_checklist_is_complete_and_unique():
    ids = re.findall(r"^\| (C\d{2}) \|", SKILL, flags=re.MULTILINE)
    assert ids == [f"C{number:02d}" for number in range(1, 11)]
    assert len(ids) == len(set(ids))
    assert SKILL.count("## 日常监控唯一检查表") == 1


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
