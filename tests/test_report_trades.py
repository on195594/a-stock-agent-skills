"""Ledger trades linked to the Research report they relied on."""

import pytest
from a_stock_lib.market_data import MarketDataResult

from a_stock_agent_runtime import cache, commands_holdings, db, schema


def _events():
    with db.db_session() as conn:
        return conn.execute(
            "SELECT event_type, shares, report_id FROM holding_events ORDER BY id"
        ).fetchall()


def test_add_buy_and_sell_store_the_report_and_default_to_unlinked():
    commands_holdings.cmd_add_holding(["000001", "10.0", "500", "--report-id", "101"])
    commands_holdings.cmd_buy_holding(["000001", "11.0", "100"])
    commands_holdings.cmd_buy_holding(
        ["000001", "11.5", "100", "--fee", "1", "--report-id", "102"]
    )
    commands_holdings.cmd_sell_holding(
        ["000001", "12.0", "200", "--report-id", "103", "--tax", "1"]
    )
    assert _events() == [
        ("buy", 500, 101),
        ("buy", 100, None),
        ("buy", 100, 102),
        ("sell", 200, 103),
    ]


def test_cli_accepts_the_option_behind_the_write_gate():
    assert (
        cache.main(
            [
                "--confirm-write",
                "add-holding",
                "000001",
                "10.0",
                "500",
                "--report-id",
                "7",
            ]
        )
        == 0
    )
    assert _events() == [("buy", 500, 7)]


@pytest.mark.parametrize("bad", ["0", "-1", "abc", "1.5", "１"])
def test_invalid_report_id_writes_nothing(bad, capsys):
    commands_holdings.cmd_add_holding(["000001", "10.0", "500"])
    with pytest.raises(SystemExit):
        commands_holdings.cmd_buy_holding(["000001", "11.0", "100", "--report-id", bad])
    assert "--report-id" in capsys.readouterr().err
    assert _events() == [("buy", 500, None)]


def test_missing_report_id_value_is_rejected():
    commands_holdings.cmd_add_holding(["000001", "10.0", "500"])
    with pytest.raises(SystemExit):
        commands_holdings.cmd_sell_holding(["000001", "12.0", "100", "--report-id"])
    assert _events() == [("buy", 500, None)]


def test_price_only_lot_cannot_claim_a_report(capsys):
    with pytest.raises(SystemExit):
        commands_holdings.cmd_add_holding(["000001", "10.0", "--report-id", "7"])
    assert "必须提供股数" in capsys.readouterr().err


def test_migration_adds_the_column_and_keeps_old_events_unlinked():
    commands_holdings.cmd_add_holding(["000001", "10.0", "500"])
    with db.db_session() as conn:
        conn.execute("ALTER TABLE holding_events DROP COLUMN report_id")
        conn.execute(
            "DELETE FROM schema_migrations WHERE migration_id='037-holding-events-report-id'"
        )
        conn.commit()
        schema.bootstrap_database_schema(conn)
    assert _events() == [("buy", 500, None)]


def _close(value, freshness=0):
    return MarketDataResult(
        value,
        "ok" if freshness == 0 else "degraded",
        "tushare.daily",
        "2026-11-05T00:00:00Z",
        freshness_days=freshness,
        source_as_of="2026-05-29" if freshness else None,
    )


def _market(monkeypatch, closes, stock, dividends=()):
    monkeypatch.setattr(commands_holdings, "_index_closes", lambda *_: closes)
    monkeypatch.setattr(
        commands_holdings, "_close_result", lambda code, day: stock[day]
    )
    monkeypatch.setattr(
        commands_holdings, "_implemented_dividends", lambda code: list(dividends)
    )


def _dividend(ex_date, cash=0.0, split=0.0, record_date=None):
    return {
        "record_date": record_date or ex_date,
        "ex_date": ex_date,
        "pay_date": ex_date,
        "cash_div": cash,
        "split_ratio": split,
    }


def _lines(capsys):
    out = capsys.readouterr().out
    return out, [line for line in out.splitlines() if line.startswith("  报告")]


def test_stock_and_index_share_the_same_closes_not_the_trade_price(monkeypatch, capsys):
    commands_holdings.cmd_add_holding(
        ["000001", "10.0", "500", "--date", "2026-05-27", "--report-id", "101"]
    )
    commands_holdings.cmd_buy_holding(["000001", "11.0", "100", "--date", "2026-06-01"])
    commands_holdings.cmd_sell_holding(
        ["000001", "12.0", "100", "--date", "2026-09-30", "--report-id", "103"]
    )
    # 5-27 is not a trading day here: the buy starts from the 5-28 close of both.
    closes = {"2026-05-28": 100.0, "2026-09-30": 110.0, "2026-10-21": 121.0}
    stock = {
        "2026-05-28": _close(11.0),
        "2026-09-30": _close(13.0),
        "2026-10-21": _close(15.4),
    }
    _market(monkeypatch, closes, stock)
    assert cache.main(["report-trades", "--end", "2026-10-22"]) == 0
    out, (buy, sell) = _lines(capsys)
    assert "关联报告的买卖 2 笔，未关联 1 笔" in out
    assert "算到 2026-10-21 收盘" in out
    assert "买入后 500股 @ 10.000：含分红送转 +40.00%，基准 +21.00%，差 +19.00pp" in buy
    assert "卖出后 100股 @ 12.000：含分红送转 +18.46%，基准 +10.00%，差 +8.46pp" in sell
    assert "已实现" in sell and "已实现" not in buy


def test_same_day_trade_has_no_invented_gap_from_its_trade_price(monkeypatch, capsys):
    commands_holdings.cmd_add_holding(
        ["000001", "10.0", "500", "--date", "2026-06-01", "--report-id", "101"]
    )
    _market(
        monkeypatch,
        {"2026-06-01": 100.0},
        {"2026-06-01": _close(11.0)},
        [_dividend(None, cash=1.0, record_date="2026-06-01")],
    )
    assert cache.main(["report-trades", "--end", "2026-06-01"]) == 0
    assert "含分红送转 +0.00%，基准 +0.00%，差 +0.00pp" in _lines(capsys)[1][0]


def test_a_split_is_not_scored_as_a_price_collapse(monkeypatch, capsys):
    commands_holdings.cmd_add_holding(
        ["000001", "10.0", "500", "--date", "2026-06-01", "--report-id", "101"]
    )
    closes = {"2026-06-01": 100.0, "2026-10-21": 100.0}
    stock = {"2026-06-01": _close(10.0), "2026-10-21": _close(5.0)}
    _market(monkeypatch, closes, stock, [_dividend("2026-07-01", split=1.0)])
    assert cache.main(["report-trades", "--end", "2026-10-21"]) == 0
    assert "含分红送转 +0.00%，基准 +0.00%，差 +0.00pp" in _lines(capsys)[1][0]


def test_distributions_after_the_position_closed_still_count_for_a_sell(
    monkeypatch, capsys
):
    commands_holdings.cmd_add_holding(["000001", "10.0", "500", "--date", "2026-05-01"])
    commands_holdings.cmd_sell_holding(
        ["000001", "10.0", "all", "--date", "2026-06-01", "--report-id", "103"]
    )
    closes = {"2026-05-01": 100.0, "2026-06-01": 100.0, "2026-10-21": 100.0}
    stock = {"2026-06-01": _close(10.0), "2026-10-21": _close(9.0)}
    _market(monkeypatch, closes, stock, [_dividend("2026-07-01", cash=1.0)])
    assert cache.main(["report-trades", "--end", "2026-10-21"]) == 0
    assert "含分红送转 +0.00%" in _lines(capsys)[1][0]


@pytest.mark.parametrize(
    "items, expected",
    [
        ([_dividend("2026-07-01", cash=1.0)], 0.1),
        ([_dividend("2026-07-01", split=1.0)], 1.0),
        # Split first: the later cash is paid on twice the shares.
        ([_dividend("2026-07-01", split=1.0), _dividend("2026-08-01", cash=1.0)], 1.2),
        # Cash first: it is paid before the shares double, in ex-date order.
        ([_dividend("2026-08-01", split=1.0), _dividend("2026-07-01", cash=1.0)], 1.1),
        # Went ex on the start day: the start close already excludes it.
        ([_dividend("2026-06-01", cash=1.0)], 0.0),
        # Goes ex after the end date: not known yet at that time.
        ([_dividend("2026-10-22", cash=1.0)], 0.0),
    ],
)
def test_total_return_counts_only_distributions_inside_the_window(items, expected):
    assert commands_holdings.total_return(
        10.0, 10.0, items, "2026-06-01", "2026-10-21"
    ) == pytest.approx(expected)


@pytest.mark.parametrize("record_date", ["2026-06-01", "2026-07-01", "2026-10-21"])
def test_distribution_without_an_ex_date_blocks_the_comparison(record_date):
    item = _dividend(None, cash=1.0, record_date=record_date)
    assert (
        commands_holdings.total_return(10.0, 10.0, [item], "2026-06-01", "2026-10-21")
        is None
    )
    outside = _dividend(None, cash=1.0, record_date="2026-05-01")
    assert (
        commands_holdings.total_return(
            10.0, 10.0, [outside], "2026-06-01", "2026-10-21"
        )
        == 0.0
    )


def test_undated_start_day_distribution_does_not_become_a_certain_price_only_loss(
    monkeypatch, capsys
):
    item = _dividend(None, cash=1.0, record_date="2026-06-01")
    assert (
        commands_holdings.total_return(10.0, 9.0, [item], "2026-06-01", "2026-06-03")
        is None
    )
    known = _dividend("2026-06-02", cash=1.0, record_date="2026-06-01")
    assert (
        commands_holdings.total_return(10.0, 9.0, [known], "2026-06-01", "2026-06-03")
        == 0.0
    )
    commands_holdings.cmd_add_holding(
        ["000001", "10.0", "500", "--date", "2026-06-01", "--report-id", "101"]
    )
    _market(
        monkeypatch,
        {"2026-06-01": 100.0, "2026-06-03": 100.0},
        {"2026-06-01": _close(10.0), "2026-06-03": _close(9.0)},
        [item],
    )
    assert cache.main(["report-trades", "--end", "2026-06-03"]) == 0
    line = _lines(capsys)[1][0]
    assert "期间有分红或送转缺除权日，不作比较" in line
    assert "含分红送转" not in line and "差" not in line


@pytest.mark.parametrize(
    "stock, reason",
    [
        # The stock's only close before the trade day is pre-trade, so never "after buying".
        (
            {"2026-06-01": _close(9.0, 3), "2026-10-21": _close(10.0)},
            "起点 2026-06-01 没有当日收盘",
        ),
        (
            {"2026-06-01": _close(10.0), "2026-10-21": _close(9.0, 5)},
            "期末 2026-10-21 没有当日收盘",
        ),
    ],
)
def test_stale_closes_are_not_compared_with_the_index(
    stock, reason, monkeypatch, capsys
):
    commands_holdings.cmd_add_holding(
        ["000001", "10.0", "500", "--date", "2026-06-01", "--report-id", "101"]
    )
    _market(monkeypatch, {"2026-06-01": 100.0, "2026-10-21": 110.0}, stock)
    assert cache.main(["report-trades", "--end", "2026-10-21"]) == 0
    line = _lines(capsys)[1][0]
    assert reason in line and "行情停在 2026-05-29" in line and "差" not in line


def test_no_index_data_exits_cleanly_without_a_traceback(monkeypatch, capsys):
    commands_holdings.cmd_add_holding(
        ["000001", "10.0", "500", "--date", "2026-06-01", "--report-id", "101"]
    )

    def unavailable(*_):
        raise RuntimeError("H00300.CSI 指数行情不可用（EMPTY）")

    monkeypatch.setattr(commands_holdings, "_index_closes", unavailable)
    assert cache.main(["report-trades", "--end", "2026-06-01"]) == 1
    assert "暂无法计算" in capsys.readouterr().err


def test_one_unavailable_stock_does_not_hide_the_others(monkeypatch, capsys):
    commands_holdings.cmd_add_holding(
        ["000001", "10.0", "500", "--date", "2026-06-01", "--report-id", "101"]
    )
    commands_holdings.cmd_add_holding(
        ["600036", "10.0", "500", "--date", "2026-06-01", "--report-id", "102"]
    )
    monkeypatch.setattr(
        commands_holdings,
        "_index_closes",
        lambda *_: {"2026-06-01": 100.0, "2026-10-21": 110.0},
    )

    def dividends(code):
        if code == "000001":
            raise RuntimeError("TuShare 分红数据不可用（failed）")
        return []

    monkeypatch.setattr(commands_holdings, "_implemented_dividends", dividends)
    monkeypatch.setattr(commands_holdings, "_close_result", lambda *_: _close(10.0))
    assert cache.main(["report-trades", "--end", "2026-10-21"]) == 0
    first, second = _lines(capsys)[1]
    assert "暂不计算（TuShare 分红数据不可用" in first
    assert "差 -10.00pp" in second


def test_without_linked_trades_no_market_data_is_requested(monkeypatch, capsys):
    commands_holdings.cmd_add_holding(["000001", "10.0", "500"])

    def forbidden(*_):
        raise AssertionError("no linked trades should mean no market data call")

    monkeypatch.setattr(commands_holdings, "_index_closes", forbidden)
    monkeypatch.setattr(commands_holdings, "_close_result", forbidden)
    monkeypatch.setattr(commands_holdings, "_implemented_dividends", forbidden)
    assert cache.main(["report-trades"]) == 0
    assert "关联报告的买卖 0 笔，未关联 1 笔" in capsys.readouterr().out


def test_old_inserts_without_the_column_still_work_for_rollback():
    commands_holdings.cmd_add_holding(["000001", "10.0", "500"])
    with db.db_session() as conn:
        conn.execute(
            """INSERT INTO holding_events
               (holding_id, code, event_type, event_date, shares, price, fees, created_at)
               VALUES (1, '000001', 'buy', '2026-05-28', 100, 11.0, 0, '2026-05-28')"""
        )
        conn.commit()
    assert _events()[-1] == ("buy", 100, None)
