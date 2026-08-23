from __future__ import annotations

import json
from io import StringIO

from a_stock_agent_runtime import cache, commands_analysis
from tests.helpers import set_valid_fundamentals


REPORT = "\n".join(
    [
        '护城河[评级=优；证据="客户留存率稳定";置信度=高]',
        '行业地位[评级=优；证据="市占率连续5年第一";置信度=高]',
    ]
)


def test_score_fundamentals_uses_cache_and_typed_report(capsys, monkeypatch) -> None:
    set_valid_fundamentals(
        "600036",
        "测试公司",
        "制造业",
        {
            "roe_3y_avg": 16.0,
            "net_profit_growth": 16.0,
            "debt_ratio": 39.0,
            "gross_margin": 31.0,
        },
    )
    monkeypatch.setattr("sys.stdin", StringIO(REPORT))

    commands_analysis.cmd_score_fundamentals(
        ["600036", "A", json.dumps({"gross_margin_stable": True})]
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["framework"] == "A"
    assert payload["subtotal"] == 60
    assert payload["complete"] is True
    assert payload["blocked"] is False
    assert len(payload["rule_hash"]) == 64


def test_score_fundamentals_missing_manual_input_fails_closed(
    capsys, monkeypatch
) -> None:
    set_valid_fundamentals(
        "600036",
        "测试公司",
        "制造业",
        {
            "roe_3y_avg": 16.0,
            "net_profit_growth": 16.0,
            "debt_ratio": 39.0,
            "gross_margin": 31.0,
        },
    )
    monkeypatch.setattr("sys.stdin", StringIO(REPORT))

    commands_analysis.cmd_score_fundamentals(["600036", "A", "{}"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["complete"] is False
    assert "gross_margin_stability" in payload["missing_inputs"]


def test_score_fundamentals_is_r0_command() -> None:
    assert cache.COMMAND_CLASSIFICATION["score-fundamentals"] == "R0"
