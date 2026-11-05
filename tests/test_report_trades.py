"""Ledger trades linked to the Research report they relied on."""

import pytest

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


def test_outcomes_compare_each_trade_with_the_index_from_its_own_date(
    monkeypatch, capsys
):
    commands_holdings.cmd_add_holding(
        ["000001", "10.0", "500", "--date", "2026-05-27", "--report-id", "101"]
    )
    commands_holdings.cmd_buy_holding(["000001", "11.0", "100", "--date", "2026-06-01"])
    commands_holdings.cmd_sell_holding(
        ["000001", "12.0", "100", "--date", "2026-09-30", "--report-id", "103"]
    )
    # 5-27 is not a trading day here: the buy starts from the 5-28 close.
    closes = {"2026-05-28": 100.0, "2026-09-30": 110.0, "2026-10-21": 121.0}
    monkeypatch.setattr(commands_holdings, "_index_closes", lambda *_: closes)
    monkeypatch.setattr(commands_holdings, "_close_on", lambda code, day: 15.0)
    assert cache.main(["report-trades", "--end", "2026-10-22"]) == 0
    out = capsys.readouterr().out
    assert "关联报告的买卖 2 笔，未关联 1 笔" in out
    assert "算到 2026-10-21 收盘" in out
    assert (
        "报告 #101 000001 2026-05-27 买入后 500股 @ 10.000：股价 +50.00%，基准 +21.00%，差 +29.00pp"
        in out
    )
    assert (
        "报告 #103 000001 2026-09-30 卖出后 100股 @ 12.000：股价 +25.00%，基准 +10.00%，差 +15.00pp"
        in out
    )
    assert "已实现" in out.split("报告 #103")[1]
    assert "未复权" not in out


def test_outcomes_flag_corporate_actions_only_after_the_trade(monkeypatch, capsys):
    commands_holdings.cmd_add_holding(
        ["000001", "10.0", "500", "--date", "2026-05-28", "--report-id", "101"]
    )
    commands_holdings.cmd_record_dividend(["000001", "300", "2026-07-09"])
    commands_holdings.cmd_buy_holding(
        ["000001", "11.0", "100", "--date", "2026-08-03", "--report-id", "102"]
    )
    closes = {"2026-05-28": 100.0, "2026-08-03": 100.0, "2026-10-21": 100.0}
    monkeypatch.setattr(commands_holdings, "_index_closes", lambda *_: closes)
    monkeypatch.setattr(commands_holdings, "_close_on", lambda code, day: 11.0)
    assert cache.main(["report-trades", "--end", "2026-10-22"]) == 0
    first, second = [
        line
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("  报告")
    ]
    assert "未复权" in first
    assert "未复权" not in second


def test_without_linked_trades_no_market_data_is_requested(monkeypatch, capsys):
    commands_holdings.cmd_add_holding(["000001", "10.0", "500"])

    def forbidden(*_):
        raise AssertionError("no linked trades should mean no market data call")

    monkeypatch.setattr(commands_holdings, "_index_closes", forbidden)
    monkeypatch.setattr(commands_holdings, "_close_on", forbidden)
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
