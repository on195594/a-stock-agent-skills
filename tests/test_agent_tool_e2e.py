from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess


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
    assert capture["schema_version"] == 1
    assert capture["provider"] == "openai-codex"
    assert capture["model"] == "gpt-5.6-sol"

    repository_head = capture["repository_head"]
    assert re.fullmatch(r"[0-9a-f]{40}", repository_head)
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", repository_head, "HEAD"],
        cwd=ROOT,
        check=True,
    )
    capture_source = (ROOT / "scripts/capture_agent_tool_e2e.mjs").read_bytes()
    assert (
        capture["capture_source_sha256"] == hashlib.sha256(capture_source).hexdigest()
    )
    recorded_source = subprocess.check_output(
        ["git", "show", f"{repository_head}:scripts/capture_agent_tool_e2e.mjs"],
        cwd=ROOT,
    )
    assert (
        hashlib.sha256(recorded_source).hexdigest() == capture["capture_source_sha256"]
    )

    # Immutable historical qualification is bound to its release, not today's Skill.
    recorded_skills = {
        name: subprocess.check_output(
            ["git", "show", f"{repository_head}:skills/{name}/SKILL.md"], cwd=ROOT
        )
        for name in ("a-stock-research", "a-stock-monitor")
    }
    assert capture["skill_sha256"] == {
        name: hashlib.sha256(content).hexdigest()
        for name, content in recorded_skills.items()
    }
    assert capture["source_skills_sha256"] == hashlib.sha256(
        b"\0".join(recorded_skills.values())
    ).hexdigest()
    assert capture["exposed_tools"] == [
        "a_stock_cache",
        "a_stock_fetch",
        "a_stock_write",
    ]
    assert capture["isolation"] == {
        "home_isolated": True,
        "production_astock_tools_exposed": False,
        "market_data_network_used": False,
        "production_database_used": False,
        "model_credentials": "read_only",
    }
    assert capture["calls"] == EXPECTED_CALLS
    assert all(call["tool"] != "a_stock_write" for call in capture["calls"])
    assert "W1" in capture["final_text"]
