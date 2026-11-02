"""Real production valuations, reports 70–78; see fixture provenance.

Only dates/card availability and account scope are perturbed, never valuations.
"""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest

from a_stock_agent_runtime import monitor_contract, monitor_research

HOLDINGS = ["600900", "000963", "002050", "603606"]


@pytest.fixture
def cards():
    path = Path(__file__).resolve().parents[1] / "fixtures/monitor/opportunity-cards-20261102.json"
    return json.loads(path.read_text())["response"]


def summarize(cards, day="2026-11-02"):
    monitor_contract.validate_research_cards(cards)
    research, prompts, escalations = monitor_research.summarize(
        {"status": "ok", **cards}, HOLDINGS, date.fromisoformat(day))
    payload = {"research": research, "review_prompts": prompts}
    monitor_contract._validate_research_fields(payload, set(HOLDINGS))
    assert not escalations
    return research, [p for p in prompts if p["kind"] == "opportunity_cost"]


def test_four_holdings_one_candidate(cards):
    research, prompts = summarize(cards)
    assert len(research["opportunity_costs"]) == 4
    assert len(prompts) == 1 and prompts[0]["code"] == "300750"
    assert prompts[0]["evidence"]["comparisons"] == research["opportunity_costs"]
    assert {r["holding"]["code"] for r in research["opportunity_costs"]} == set(HOLDINGS)
    for comparison in research["opportunity_costs"]:
        assert comparison["candidate"]["report_id"] == 75
        assert comparison["net_advantage"] == pytest.approx(
            comparison["candidate_neutral_return"] - comparison["holding_neutral_return"]
            - .001 / comparison["candidate_horizon"])
    assert "宁德时代" in prompts[0]["detail"] and "19.82%" in prompts[0]["detail"]
    assert "情景未经记分，仅提示复核" in prompts[0]["detail"]


@pytest.mark.parametrize("day,count", [("2026-11-09", 1), ("2026-11-10", 0), ("2026-11-01", 0)])
def test_snapshot_date_freshness_boundary(cards, day, count):
    original, _ = summarize(cards)
    research, prompts = summarize(cards, day)
    assert len(prompts) == count
    assert research["opportunity_costs"] == original["opportunity_costs"]


@pytest.mark.parametrize("completed,day,count", [
    ("2026-11-02T16:30:00Z", "2026-11-10", 1),  # 11-03 00:30 Shanghai: day 7, UTC date would be day 8
    ("2026-11-02T17:00:00Z", "2026-11-02", 0),  # 11-03 Shanghai is after the snapshot date
])
def test_utc_completed_at_uses_shanghai_date(cards, completed, day, count):
    for card in cards["cards"]:
        card["completed_at"] = completed
    _, prompts = summarize(cards, day)
    assert len(prompts) == count


def test_only_one_holding_fresh_includes_all_comparisons(cards):
    cards["cards"][0]["completed_at"] = "2026-11-10T00:00:00+08:00"
    research, prompts = summarize(cards, "2026-11-10")
    assert len(prompts) == 1
    assert len(prompts[0]["evidence"]["comparisons"]) == len(research["opportunity_costs"]) == 4


def test_two_candidates_each_win(cards):
    # Keep real valuations: move CATL's close date 4 days later, and one holding
    # 1 day later. CATL wins that holding; Allist wins the other three.
    for row in cards["cards"]:
        if row["code"] == "300750":
            row["current"]["last_close_date"] = "2026-11-06"
        elif row["code"] == HOLDINGS[0]:
            row["current"]["last_close_date"] = "2026-11-03"
    research, prompts = summarize(cards)
    assert {p["code"] for p in prompts} == {"300750", "688578"}
    assert sorted(len(p["evidence"]["comparisons"]) for p in prompts) == [1, 3]
    assert len(research["opportunity_costs"]) == 4
    assert "超过3日" in research["reason"]


@pytest.mark.parametrize("completed", [None, "missing", "not-a-date", "2026-99-99T00:00:00"])
def test_missing_or_invalid_completed_at_is_not_fresh(cards, completed):
    for row in cards["cards"]:
        if completed == "missing":
            del row["completed_at"]
        else:
            row["completed_at"] = completed
    research, prompts = summarize(cards)
    assert len(research["opportunity_costs"]) == 4 and not prompts
    assert research["status"] == "ok"


@pytest.mark.parametrize("mutation", ["number", "scope", "prompt_code", "empty", "unlisted"])
def test_digest_contract_rejects_invalid_evidence(cards, mutation):
    research, prompts = summarize(cards)
    payload = deepcopy({"research": research, "review_prompts": prompts})
    if mutation == "number":
        payload["research"]["opportunity_costs"][0]["net_advantage"] = None
    elif mutation == "scope":
        payload["research"]["opportunity_costs"][0]["holding"]["code"] = "999999"
    elif mutation == "prompt_code":
        payload["review_prompts"][0]["code"] = HOLDINGS[0]
    elif mutation == "empty":
        payload["review_prompts"][0]["evidence"]["comparisons"] = []
    else:
        payload["research"]["opportunity_costs"] = []
    with pytest.raises(monitor_contract.MonitorContractError):
        monitor_contract._validate_research_fields(payload, set(HOLDINGS))


def test_only_candidate_fresh(cards):
    next(row for row in cards["cards"] if row["code"] == "300750")["completed_at"] = "2026-11-10T18:10:13+08:00"
    research, prompts = summarize(cards, "2026-11-10")
    assert len(prompts) == 1 and len(research["opportunity_costs"]) == 4


def test_legacy_opportunity_prompt_still_readable(cards):
    research, _ = summarize(cards)
    comparisons = research.pop("opportunity_costs")
    prompts = [{"kind": "opportunity_cost", "code": row["holding"]["code"],
                "detail": "旧版逐持仓提示", "evidence": row} for row in comparisons]
    monitor_contract._validate_research_fields(
        {"research": research, "review_prompts": prompts}, set(HOLDINGS))
