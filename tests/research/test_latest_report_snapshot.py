from __future__ import annotations

import pandas as pd
import pytest

from a_stock_agent_runtime import fetcher


def _indicator() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "end_date": ["2025-12-31", "2026-03-31", "2026-03-31"],
            "ann_date": ["2026-03-28", "2026-04-20", "2026-04-25"],
            "update_flag": ["1", "0", "1"],
            "or_yoy": [3.0, -4.0, 6.0],
            "netprofit_yoy": [2.0, -8.0, -5.0],
            "dt_netprofit_yoy": [1.0, -10.0, -7.0],
            "roe_waa": [15.0, 3.0, 3.2],
            "bps": [10.0, 10.2, 10.3],
        }
    )


def _income() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "end_date": ["2025-03-31", "2025-12-31", "2026-03-31"],
            "ann_date": ["2025-04-25", "2026-03-28", "2026-04-25"],
            "f_ann_date": ["2025-04-26", "2026-03-29", "2026-04-26"],
            "n_income_attr_p": [90.0, 400.0, 80.0],
            "total_revenue": [900.0, 4000.0, 1000.0],
        }
    )


def _balance() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "end_date": ["2025-03-31", "2025-12-31", "2026-03-31"],
            "ann_date": ["2025-04-25", "2026-03-28", "2026-04-25"],
            "f_ann_date": ["2025-04-26", "2026-03-29", "2026-04-26"],
            "total_hldr_eqy_exc_min_int": [500.0, 560.0, 550.0],
        }
    )


def test_latest_report_snapshot_uses_same_period_latest_revision_without_annualising() -> None:
    snapshot = fetcher._build_latest_report_snapshot(
        _indicator(), _income(), _balance(), annual_period="2025-12-31"
    )

    assert snapshot["report_period"] == "2026Q1"
    assert snapshot["announcement_date"] == "2026-04-26"
    assert snapshot["source"] == "tushare.fina_indicator+income+balancesheet"
    assert snapshot["is_newer_than_annual"] is True
    fields = snapshot["fields"]
    assert fields["revenue"] == {"value": 1000.0, "status": "ok", "direction": "up"}
    assert fields["revenue_yoy"] == {"value": 6.0, "status": "ok", "direction": "up"}
    assert fields["net_profit_parent"] == {"value": 80.0, "status": "ok", "direction": "down"}
    assert fields["net_profit_yoy"] == {"value": -5.0, "status": "ok", "direction": "down"}
    assert fields["deducted_net_profit_yoy"] == {"value": -7.0, "status": "ok", "direction": "down"}
    assert fields["roe"] == {"value": 3.2, "status": "ok", "direction": "missing"}
    assert fields["bps"] == {"value": 10.3, "status": "ok", "direction": "missing"}
    assert fields["equity_parent"] == {"value": 550.0, "status": "ok", "direction": "up"}


def test_latest_report_snapshot_preserves_field_level_missing() -> None:
    snapshot = fetcher._build_latest_report_snapshot(
        _indicator().drop(columns="dt_netprofit_yoy"),
        _income(),
        _balance(),
        annual_period="2025-12-31",
    )

    assert snapshot["fields"]["deducted_net_profit_yoy"] == {
        "value": None,
        "status": "missing",
        "direction": "missing",
    }
    assert snapshot["fields"]["revenue"]["status"] == "ok"


def test_fetch_fin_data_keeps_annual_baseline_and_exports_snapshot(monkeypatch) -> None:
    annual = pd.DataFrame(
        {
            "报告期": ["2024-12-31", "2025-12-31"],
            "净资产收益率": [14.0, 15.0],
            "净利润同比增长率": [1.0, 2.0],
            "资产负债率": [40.0, 41.0],
            "基本每股收益": [1.0, 1.1],
            "每股净资产": [9.0, 10.0],
            "销售毛利率": [30.0, 31.0],
            "营业总收入同比增长率": [2.0, 3.0],
        }
    )
    expected = {"report_period": "2026Q1", "fields": {}}
    annual.attrs["latest_report_snapshot"] = expected
    monkeypatch.setattr(fetcher, "_fetch_financials", lambda code: annual)
    monkeypatch.setattr(fetcher, "timed_call_with_retry", lambda fn, code, timeout: fn(code))
    results: dict = {}
    null_reasons: dict = {}

    fin_df, eps, bps = fetcher._fetch_fin_data("600000", results, null_reasons)

    assert fetcher._extract_data_period(fin_df) == "2025年报"
    assert eps == pytest.approx(1.1)
    assert bps == pytest.approx(10.0)
    assert results["latest_report_snapshot"] == expected
