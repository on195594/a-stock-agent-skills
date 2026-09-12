from __future__ import annotations

import json
from io import StringIO

import pytest

from a_stock_agent_runtime import cache, commands_analysis, risk_gates
from tests.helpers import set_valid_fundamentals, valid_fundamentals_payload


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


@pytest.mark.parametrize(
    ("operating_cf", "eps"),
    [
        (1.6, 2.0),
        ("invalid", 2.0),
        (float("nan"), 2.0),
        (float("inf"), 2.0),
        (1.6, 0.0),
        (1e308, 1e-308),
    ],
)
def test_score_fundamentals_routes_cash_ratio_through_owner(
    capsys, monkeypatch, operating_cf, eps
) -> None:
    metrics = {
        "operating_cf_per_share": operating_cf,
        "eps": eps,
        "_cache_meta": {"industry": "软件"},
    }
    calls = []
    real_ratio = (
        commands_analysis.framework_scoring.calculate_operating_cf_to_net_profit
    )

    def ratio(raw_operating_cf, raw_eps):
        calls.append((raw_operating_cf, raw_eps))
        return real_ratio(raw_operating_cf, raw_eps)

    monkeypatch.setattr(
        commands_analysis.store, "get_fundamentals", lambda _code: metrics
    )
    monkeypatch.setattr(
        commands_analysis.framework_scoring,
        "calculate_operating_cf_to_net_profit",
        ratio,
    )
    monkeypatch.setattr(
        commands_analysis,
        "_risk_gate_state",
        lambda _metrics: (
            "blocked",
            ["regulatory_gate:missing"],
            {
                "regulatory_gate": {"status": "missing"},
                "cash_flow_gate": {"status": "clear"},
            },
        ),
    )

    commands_analysis.cmd_score_fundamentals(["688111", "F", "{}"])

    assert calls == [(operating_cf, eps)]
    assert json.loads(capsys.readouterr().out)["blocked"] is True


def test_p1_only_blocks_timing_not_fundamental_subtotal(capsys, monkeypatch) -> None:
    clear_check = {
        "status": "clear",
        "reason_code": "official_clear",
        "sources": ["official exchange"],
        "as_of": "2026-09-09",
    }
    p0 = risk_gates.regulatory_gate(
        {
            "code": "600036",
            "exchange": "SSE",
            "board": "main",
            "report_period": "2025年报",
            "as_of": "2026-09-09",
            "listing_risk": clear_check,
            "audit_opinion": clear_check,
            "investigation": clear_check,
            "dividend_compliance": clear_check,
        }
    )
    p1 = risk_gates.roe_structural_gate(
        latest_roe_ttm=7,
        roe_5y_values=[10] * 5,
        sources=["official annual report"],
        as_of="2026-09-09",
    )
    p2 = risk_gates.cash_flow_gate(
        framework="A通用",
        ttm_cfo=100,
        ttm_capex=40,
        sources=["official annual report"],
        as_of="2026-09-09",
    )
    data = valid_fundamentals_payload(
        {
            "roe_3y_avg": 16.0,
            "net_profit_growth": 16.0,
            "debt_ratio": 39.0,
            "gross_margin": 31.0,
            "regulatory_gate": p0,
            "roe_structural_gate": p1,
            "cash_flow_gate": p2,
        }
    )
    data["field_provenance"]["roe_structural_gate"]["status"] = "missing"
    data["null_reasons"]["roe_structural_gate"] = p1["reason_code"]
    cache.set_fundamentals("600036", "测试公司", "制造业", data)
    monkeypatch.setattr("sys.stdin", StringIO(REPORT))

    commands_analysis.cmd_score_fundamentals(
        ["600036", "A", json.dumps({"gross_margin_stable": True})]
    )

    payload = json.loads(capsys.readouterr().out)
    assert payload["subtotal"] == 60
    assert payload["complete"] is True
    assert payload["blocked"] is False
    assert payload["scoring_status"] == "complete"
    assert payload["timing_status"] == "incomplete"
    assert payload["matrix"] == "not_formed"


def test_score_fundamentals_rejects_unofficial_p0_override(capsys) -> None:
    set_valid_fundamentals(
        "600036",
        "测试公司",
        "制造业",
        {"roe_3y_avg": 16.0},
    )
    check = {
        "status": "clear",
        "action_eligible": True,
        "reason_code": "official_clear",
    }
    override = {
        "regulatory_gate": {
            "status": "clear",
            "action_eligible": True,
            "reason_code": "regulatory_clear",
            "sources": ["tushare.income (company-filed statement mirror)"],
            "as_of": "2026-09-09",
            "rule_version": "test",
            "checks": {
                name: check
                for name in (
                    "listing_risk",
                    "audit_opinion",
                    "investigation",
                    "dividend_compliance",
                )
            },
        }
    }

    with pytest.raises(SystemExit):
        commands_analysis.cmd_score_fundamentals(["600036", "A", json.dumps(override)])

    assert "regulatory_gate.sources 非官方" in capsys.readouterr().err


def test_score_fundamentals_is_r0_command() -> None:
    assert cache.COMMAND_CLASSIFICATION["score-fundamentals"] == "R0"
