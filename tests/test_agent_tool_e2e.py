from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "tests/fixtures/agent_tool_e2e_live.json"
EXPECTED_CALLS = [
    {
        "tool": "a_stock_cache",
        "args": {
            "scenario": "first_research_routes_research",
            "operation": "holdings",
            "code": "600000",
        },
    },
    {
        "tool": "a_stock_fetch",
        "args": {"scenario": "first_research_routes_research", "code": "600000"},
    },
    {
        "tool": "a_stock_cache",
        "args": {
            "scenario": "first_research_routes_research",
            "operation": "check",
            "code": "600000",
        },
    },
    {
        "tool": "a_stock_cache",
        "args": {
            "scenario": "existing_holding_routes_monitor",
            "operation": "monitor-snapshot",
            "portfolio_value": 100000,
        },
    },
    {
        "tool": "a_stock_cache",
        "args": {
            "scenario": "unauthorized_w1_is_not_executed",
            "operation": "monitor-snapshot",
            "portfolio_value": 100000,
        },
    },
]


def test_live_model_invoked_only_the_expected_fake_tools() -> None:
    capture = json.loads(CAPTURE.read_text(encoding="utf-8"))
    skills = "\0".join(
        (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        for name in ("a-stock-research", "a-stock-monitor")
    )

    assert capture["schema_version"] == 1
    assert capture["provider"] == "openai-codex"
    assert capture["model"] == "gpt-5.6-sol"
    assert capture["source_skills_sha256"] == hashlib.sha256(skills.encode()).hexdigest()
    assert capture["calls"] == EXPECTED_CALLS
    assert all(call["tool"] != "a_stock_write" for call in capture["calls"])
    assert "W1" in capture["final_text"]
