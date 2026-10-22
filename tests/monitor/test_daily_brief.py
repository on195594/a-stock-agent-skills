"""Post-close push brief built from the monitor-v1 snapshot."""

from a_stock_agent_runtime.commands_monitor import format_daily_brief


def _holding(code, price, quote_date="2026-10-22", l3=None):
    return {
        "code": code,
        "name": f"fixture-{code}",
        "quote": {"price": price, "quote_date": quote_date, "daily_change_pct": -1.43},
        "stop_loss_15": 24.824,
        "stop_loss_20": 23.364,
        "l3": {"conditions": l3 or []},
    }


def _snapshot(holdings, escalations=()):
    return {"as_of": "2026-10-22T15:30:05+08:00", "holdings": holdings,
            "escalations": list(escalations)}


def test_non_trading_day_or_missing_quotes_is_silent():
    stale = _snapshot([_holding("000963", 26.21, quote_date="2026-10-21")])
    assert format_daily_brief(stale, [], "2026-10-22") == ""
    assert format_daily_brief(_snapshot([_holding("000963", None)]), [], "2026-10-22") == ""


def test_brief_lists_stop_distance_triggers_due_l3_and_extras():
    l3 = [
        {"id": 35, "status": "watch", "next_review": "2026-10-31"},
        {"id": 34, "status": "not_triggered", "next_review": "2026-10-28"},
        {"id": 36, "status": "not_triggered", "next_review": "2027-04-30"},
    ]
    snapshot = _snapshot(
        [_holding("000963", 26.21, l3=l3)],
        [
            {"code": "000963", "reason_code": "daily_drop", "detail": "daily change -3.1%"},
            {"code": None, "reason_code": "denominator_missing", "detail": "x"},
        ],
    )
    brief = format_daily_brief(snapshot, ["000963 疑似漏记分红"], "2026-10-22")
    assert "fixture-000963 000963 26.21（-1.43%） 距止损1+5.3% 距止损2+10.9%" in brief
    assert "- 000963 日跌幅达3%：daily change -3.1%" in brief
    assert "L3#35 watch" in brief and "L3#34 not_triggered" in brief
    assert "L3#36" not in brief and "denominator" not in brief
    assert "- 000963 疑似漏记分红" in brief


def test_calm_day_says_no_triggers():
    brief = format_daily_brief(_snapshot([_holding("000963", 26.21)]), [], "2026-10-22")
    assert "需关注：无触发项" in brief
