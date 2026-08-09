"""
fetcher.py 单元测试
覆盖：
  - cmd_batch 只捕获 Exception，不吞 KeyboardInterrupt
  - _extract_fin_fields 从 DataFrame 正确提取各财务字段
"""
import sys
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from types import ModuleType, SimpleNamespace

import pytest
import pandas as pd

from a_stock_agent_runtime import fetcher
from a_stock_agent_runtime import cache
from a_stock_lib.providers import QuoteObservation
from a_stock_lib.fetcher_utils import detect_split_ratio


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_fetcher_cache.db"
    monkeypatch.setattr(cache, 'DB_PATH', str(db_file))
    # fetcher 内部也引用 list_codes，需要同步 patch
    monkeypatch.setattr(fetcher, 'list_codes', lambda: ['600519', '000001'])
    fetcher._fetch_tushare_industry_map.cache_clear()
    yield str(db_file)
    fetcher._fetch_tushare_industry_map.cache_clear()


def _patch_tushare_provider(monkeypatch, provider_factory):
    """为函数内懒加载 import 注入 fake a_stock_lib provider。"""
    root_module = ModuleType('a_stock_lib')
    providers_module = ModuleType('a_stock_lib.providers')
    tushare_module = ModuleType('a_stock_lib.providers.tushare_fundamentals')
    root_module.__path__ = []
    providers_module.__path__ = []
    tushare_module.TushareFundamentalsProvider = provider_factory
    root_module.providers = providers_module
    providers_module.tushare_fundamentals = tushare_module

    monkeypatch.setitem(sys.modules, 'a_stock_lib', root_module)
    monkeypatch.setitem(sys.modules, 'a_stock_lib.providers', providers_module)
    monkeypatch.setitem(
        sys.modules,
        'a_stock_lib.providers.tushare_fundamentals',
        tushare_module,
    )


@pytest.mark.parametrize('name', ['info', 'financials', 'dividends', 'price_history'])
@pytest.mark.parametrize('source', ['tushare', 'akshare'])
def test_structured_fetchers_honor_data_source(monkeypatch, name, source):
    """每条结构化抓取入口都必须选择对应 provider，不能静默走 AKShare。"""
    selected = object()
    other = object()
    monkeypatch.setattr(fetcher, 'DATA_SOURCE', source)
    monkeypatch.setattr(fetcher, f'_fetch_{name}_tushare', lambda code: selected if source == 'tushare' else other)
    monkeypatch.setattr(fetcher, f'_fetch_{name}_akshare', lambda code: selected if source == 'akshare' else other)

    assert getattr(fetcher, f'_fetch_{name}')('600519') is selected


def test_current_pb_uses_the_same_report_period_bps_as_pb_history(monkeypatch):
    assert not hasattr(fetcher, '_fetch_pb_baidu')
    results = {'bps': 6.9176, 'eps': 1.95}
    null_reasons = {}

    fetcher._fetch_pb_pe_data('601899', 35.15, results, null_reasons)

    assert results['pb'] == 5.08
    assert results['pe_ttm'] == 18.03
    assert fetcher.FIELDS['pb'][1] == 'computed'
    assert 'pb' not in null_reasons


def test_trading_dates_prefer_tushare(monkeypatch):
    expected = (date(2026, 8, 7),)
    monkeypatch.setattr(fetcher, 'DATA_SOURCE', 'tushare')
    monkeypatch.setattr(fetcher, '_fetch_trading_dates_tushare', lambda: expected)
    monkeypatch.setattr(
        fetcher,
        '_fetch_trading_dates_akshare',
        lambda: pytest.fail('TuShare calendar should be the primary path'),
    )
    fetcher._fetch_trading_dates.cache_clear()
    try:
        assert fetcher._fetch_trading_dates() == expected
    finally:
        fetcher._fetch_trading_dates.cache_clear()


def test_realtime_quote_uses_sina_only_and_records_snapshot(monkeypatch):
    today = date.today()
    quote = QuoteObservation(
        price=1600.0,
        quote_date=today.isoformat(),
        quote_time='10:00:00',
        source='sina',
        instrument_name='贵州茅台',
    )
    snapshot = {}
    monkeypatch.setattr(fetcher, 'timed_call', lambda *args, **kwargs: (today,))
    monkeypatch.setattr(fetcher, '_fetch_sina_quote', lambda code: quote)
    monkeypatch.setattr(fetcher, '_validate_sina_quote', lambda *args, **kwargs: None)
    monkeypatch.setattr(
        fetcher,
        'record_quote_snapshot',
        lambda *args, **kwargs: snapshot.update(args=args, kwargs=kwargs),
    )

    result = fetcher._fetch_realtime_quote('600519')

    assert result is quote
    assert snapshot['args'][0:5] == ('600519', 1600.0, today.isoformat(), '10:00:00', 'sina')
    assert snapshot['args'][5]['sina']['price'] == 1600.0


def test_sina_quote_validation_rejects_stale_and_future_quotes():
    shanghai = timezone(timedelta(hours=8))
    now = datetime(2026, 8, 7, 10, 1, tzinfo=shanghai)
    trading_dates = (date(2026, 8, 7),)

    valid = QuoteObservation(1600.0, '2026-08-07', '10:00:00', 'sina')
    stale = QuoteObservation(1600.0, '2026-08-07', '09:57:00', 'sina')
    future = QuoteObservation(1600.0, '2026-08-07', '10:02:00', 'sina')

    assert fetcher._validate_sina_quote(valid, trading_dates, now) is None
    assert 'stale' in fetcher._validate_sina_quote(stale, trading_dates, now)
    assert 'stale' in fetcher._validate_sina_quote(future, trading_dates, now)


def test_tushare_dividend_adapter_rescales_per_share_units_to_per_10_shares(monkeypatch):
    """TuShare reports per-share (cash_div/stk_co_rate); downstream consumers
    expect AKShare's per-10-share convention. Values mirror 603606's 2025 plan:
    每10股转增2股派5.6元 -> cash_div 0.56, stk_co_rate 0.2."""
    import a_stock_lib.providers as providers

    class FakeProvider:
        def fetch_dividend_history(self, code):
            return SimpleNamespace(
                status='ok',
                value=pd.DataFrame({
                    'end_date': ['2025-12-31'],
                    'ex_date': ['2026-05-26'],
                    'div_proc': ['实施'],
                    'stk_div': [0.00],
                    'stk_bo_rate': [0.00],
                    'stk_co_rate': [0.20],
                    'cash_div': [0.56],
                }),
            )

    monkeypatch.setattr(providers, 'TushareDividendProvider', FakeProvider)
    frame = fetcher._fetch_dividends_tushare('603606')

    assert frame.loc[0, '送转股份-送转总比例'] == pytest.approx(2.00)
    assert frame.loc[0, '现金分红-现金分红比例'] == pytest.approx(5.60)

    # The whole point of the rescale: these two consumers must recover the
    # per-share figures the announcement states.
    assert fetcher.compute_dividend_yield(frame, 38.67)[1] == pytest.approx(0.56)
    assert detect_split_ratio(frame, 2025) == (pytest.approx(0.2), '2026-05-26')


def test_tushare_dividend_adapter_rescales_stk_div_without_rate_columns(monkeypatch):
    import a_stock_lib.providers as providers

    class FakeProvider:
        def fetch_dividend_history(self, code):
            return SimpleNamespace(
                status='ok',
                value=pd.DataFrame({
                    'end_date': ['2025-12-31'],
                    'stk_div': [0.10],
                    'cash_div': [0.20],
                }),
            )

    monkeypatch.setattr(providers, 'TushareDividendProvider', FakeProvider)
    frame = fetcher._fetch_dividends_tushare('600519')

    assert frame.loc[0, '送转股份-送转总比例'] == pytest.approx(1.0)
    assert frame.loc[0, '现金分红-现金分红比例'] == pytest.approx(2.0)


def test_tushare_financial_adapter_merges_balance_and_cashflow(monkeypatch):
    import a_stock_lib.providers as providers

    def result(frame):
        return SimpleNamespace(status='ok', value=frame)

    class FakeProvider:
        def fetch_indicator_history(self, code):
            return result(pd.DataFrame({
                'end_date': ['2025-12-31'],
                'roe_waa': [12.0],
                'netprofit_yoy': [8.0],
                'debt_to_assets': [40.0],
                'grossprofit_margin': [30.0],
                'bps': [10.0],
            }))

        def fetch_income_history(self, code):
            return result(pd.DataFrame({
                'end_date': ['2025-12-31'],
                'basic_eps': [1.2],
                'total_revenue': [1000.0],
            }))

        def fetch_balance_history(self, code):
            return result(pd.DataFrame({
                'end_date': ['2025-12-31'],
                'total_cur_assets': [200.0],
                'total_cur_liab': [100.0],
                'total_share': [100.0],
            }))

        def fetch_cashflow_history(self, code):
            return result(pd.DataFrame({
                'end_date': ['2025-12-31'],
                'n_cashflow_act': [300.0],
            }))

    monkeypatch.setattr(providers, 'TushareFinancialProvider', FakeProvider)
    frame = fetcher._fetch_financials_tushare('600519')

    assert frame.loc[0, '流动比率'] == pytest.approx(2.0)
    assert frame.loc[0, '每股经营现金流'] == pytest.approx(3.0)


# ── cmd_batch：KeyboardInterrupt 不被吞掉 ────────────────────────────────────

def test_cmd_batch_propagates_keyboard_interrupt(monkeypatch):
    """cmd_batch 只 except Exception，不捕获 KeyboardInterrupt"""

    def raise_kb(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(fetcher, 'cmd_fetch', raise_kb)

    with pytest.raises(KeyboardInterrupt):
        fetcher.cmd_batch([])


def test_cmd_batch_catches_runtime_error(capsys, monkeypatch):
    """cmd_batch 捕获普通 Exception，继续处理下一支"""
    call_count = 0

    def failing_fetch(args):
        nonlocal call_count
        call_count += 1
        raise RuntimeError("API 超时")

    monkeypatch.setattr(fetcher, 'cmd_fetch', failing_fetch)

    fetcher.cmd_batch([])

    # 两支股票都被处理（即使都失败），不中断
    assert call_count == 2
    out = capsys.readouterr().out
    assert '❌' in out
    assert 'API 超时' in out


def test_cmd_batch_empty_watchlist(capsys, monkeypatch):
    """watchlist 为空时 cmd_batch 提前返回，不崩溃"""
    monkeypatch.setattr(fetcher, 'list_codes', lambda: [])

    fetcher.cmd_batch([])
    out = capsys.readouterr().out
    assert 'watchlist 为空' in out


def test_cmd_batch_deduplicates_codes(capsys, monkeypatch):
    """重复代码只取一次（保序去重）"""
    monkeypatch.setattr(fetcher, 'list_codes', lambda: ['600519', '600519', '000001'])

    fetched = []

    def track_fetch(args):
        fetched.append(args[0])

    monkeypatch.setattr(fetcher, 'cmd_fetch', track_fetch)

    fetcher.cmd_batch([])
    assert fetched.count('600519') == 1, "重复代码 600519 应只抓取一次"


# ── 行业字段：优先使用 a_stock_lib 的 Tushare 批量行业映射 ───────────────────

def test_fetch_industry_from_lib_returns_value_when_hit(monkeypatch):
    """Tushare 行业映射命中时返回对应行业字符串"""

    class FakeProvider:
        def fetch_industry_map(self):
            return SimpleNamespace(status='ok', value={'600519': '白酒'})

    _patch_tushare_provider(monkeypatch, lambda: FakeProvider())

    assert fetcher._fetch_industry_from_lib('600519') == '白酒'


def test_fetch_industry_from_lib_returns_none_when_provider_fails(monkeypatch):
    """Tushare provider 返回 failed 时静默返回 None"""

    class FakeProvider:
        def fetch_industry_map(self):
            return SimpleNamespace(status='failed', value=None)

    _patch_tushare_provider(monkeypatch, lambda: FakeProvider())

    assert fetcher._fetch_industry_from_lib('600519') is None


def test_fetch_industry_from_lib_returns_none_on_exception(monkeypatch):
    """Tushare provider 抛异常时不影响主流程"""

    class FakeProvider:
        def fetch_industry_map(self):
            raise RuntimeError("tushare unavailable")

    _patch_tushare_provider(monkeypatch, lambda: FakeProvider())

    assert fetcher._fetch_industry_from_lib('600519') is None


def test_fetch_spot_data_prefers_lib_industry_over_akshare(monkeypatch):
    """_fetch_spot_data 优先使用 a_stock_lib 行业，而不是 AKShare 原始行业字段"""
    monkeypatch.setattr(fetcher, 'timed_call', lambda *args, **kwargs: {
        '股票简称': '贵州茅台',
        '行业': 'AKShare行业',
        '最新': '1600.00',
        '总市值': '200',
        '流通市值': '100',
    })
    monkeypatch.setattr(fetcher, '_fetch_industry_from_lib', lambda code: 'Tushare行业')
    monkeypatch.setattr(fetcher, '_fetch_realtime_quote', lambda code: QuoteObservation(
        price=1600.0, quote_date='2026-07-14', quote_time='10:00:00', source='sina',
    ))

    results = {}
    null_reasons = {}
    name, industry, current_price = fetcher._fetch_spot_data('600519', results, null_reasons)

    assert name == '贵州茅台'
    assert industry == 'Tushare行业'
    assert current_price == 1600.0
    assert results['float_to_total_ratio'] == 50.0


def test_fetch_spot_data_preserves_sina_name_when_akshare_info_fails(monkeypatch):
    """A successful Sina quote still supplies the company name on info failure."""
    monkeypatch.setattr(fetcher, 'timed_call', lambda *args, **kwargs: (None, 'API失败'))
    monkeypatch.setattr(fetcher, '_fetch_industry_from_lib', lambda code: None)
    monkeypatch.setattr(fetcher, '_lookup_cached_name', lambda code: None)
    monkeypatch.setattr(fetcher, '_lookup_cached_industry', lambda code: None)
    monkeypatch.setattr(fetcher, '_fetch_realtime_quote', lambda code: QuoteObservation(
        price=1600.0, quote_date='2026-07-14', quote_time='10:00:00', source='sina',
        instrument_name='贵州茅台',
    ))

    name, industry, current_price = fetcher._fetch_spot_data('600519', {}, {})

    assert name == '贵州茅台'
    assert industry == '未知'
    assert current_price == 1600.0


def test_fetch_spot_data_marks_cached_industry_stale(monkeypatch):
    monkeypatch.setattr(fetcher, 'timed_call', lambda *args, **kwargs: (None, 'API失败'))
    monkeypatch.setattr(fetcher, '_fetch_industry_from_lib', lambda code: None)
    monkeypatch.setattr(fetcher, '_lookup_cached_name', lambda code: '缓存名称')
    monkeypatch.setattr(fetcher, '_lookup_cached_industry', lambda code: '缓存行业')
    monkeypatch.setattr(fetcher, 'update_qualitative_only_security', lambda *args: None)
    monkeypatch.setattr(fetcher, '_fetch_realtime_quote', lambda code: QuoteObservation(
        price=10.0, quote_date='2026-07-14', quote_time='10:00:00', source='sina',
    ))
    results = {}

    _, industry, _ = fetcher._fetch_spot_data('600000', results, {})

    assert industry == '缓存行业'
    assert results['industry_status'] == 'stale_cache'
    assert results['_industry_source'] == 'historical_cache'


def test_fetch_spot_data_persists_qualitative_only_routing_before_fundamentals(monkeypatch):
    monkeypatch.setattr(fetcher, 'timed_call', lambda *args, **kwargs: {
        '股票简称': '保险公司', '行业': '保险',
    })
    monkeypatch.setattr(fetcher, '_fetch_industry_from_lib', lambda code: '保险')
    monkeypatch.setattr(fetcher, '_fetch_realtime_quote', lambda code: QuoteObservation(
        price=50.0, quote_date='2026-07-14', quote_time='10:00:00', source='sina',
    ))

    fetcher._fetch_spot_data('601318', {}, {})

    with cache.db_session() as conn:
        status = conn.execute(
            'SELECT name, industry FROM qualitative_only_securities WHERE code=?',
            ('601318',),
        ).fetchone()
    assert status == ('保险公司', '保险')


# ── _extract_fin_fields：财务字段提取纯函数 ──────────────────────────────────

def _make_fin_df(rows: int = 5) -> 'pd.DataFrame':
    """构造 stock_financial_abstract_ths 格式的 mock DataFrame"""
    import pandas as pd
    data = {
        '净资产收益率':         [f'{10 + i:.2f}' for i in range(rows)],
        '净利润同比增长率':      [f'{8 + i:.2f}' for i in range(rows)],
        '资产负债率':           [f'{45.00:.2f}' for _ in range(rows)],
        '基本每股收益':         [f'{2.5 + i * 0.1:.2f}' for i in range(rows)],
        '每股净资产':           [f'{15.0 + i:.2f}' for i in range(rows)],
        '销售毛利率':           [f'{85.00:.2f}' for _ in range(rows)],
        '营业总收入同比增长率':  [f'{12 + i:.2f}' for i in range(rows)],
        '流动比率':             [f'{2.5:.2f}' for _ in range(rows)],
        '每股经营现金流':       [f'{3.2 + i * 0.1:.2f}' for i in range(rows)],
    }
    return pd.DataFrame(data)


def test_extract_fin_fields_returns_all_keys():
    """_extract_fin_fields 返回 9 个预期字段（含 bps）"""
    fin_df = _make_fin_df()
    result = fetcher._extract_fin_fields(fin_df)

    expected_keys = {
        'roe_3y_avg', 'net_profit_growth', 'debt_ratio', 'eps', 'bps',
        'gross_margin', 'revenue_growth_3y', 'current_ratio', 'operating_cf_per_share',
    }
    assert set(result.keys()) == expected_keys
    # 所有值在正常 DataFrame 下均不应为 None
    for k, v in result.items():
        assert v is not None, f"字段 {k} 不应为 None"


def test_extract_fin_fields_gross_margin():
    """gross_margin 从 '销售毛利率' 列正确提取最新年度值"""
    fin_df = _make_fin_df()
    result = fetcher._extract_fin_fields(fin_df)
    # 最后一行 '销售毛利率' 值固定为 '85.00'
    assert result['gross_margin'] == 85.0


def test_extract_fin_fields_revenue_growth_3y():
    """revenue_growth_3y 是 '营业总收入同比增长率' 最后 3 年的均值"""
    fin_df = _make_fin_df(rows=5)
    result = fetcher._extract_fin_fields(fin_df)
    # 最后3行值为 '14.00', '15.00', '16.00'（i=2,3,4 → 12+i）
    expected = round((14.0 + 15.0 + 16.0) / 3, 2)
    assert result['revenue_growth_3y'] == expected


# ── _fetch_bond_yield fallback tests ──────────────────────────────────────────

def test_fetch_bond_yield_fallback(monkeypatch, isolated_db):
    """API failure may reuse a source-complete market snapshot under 24h."""
    cache.set_market_indicator_snapshot(
        'bond_yield_10y', 2.15, '2026-07-14', 'fixture-source',
        fetched_at=(cache.utc_now() - fetcher.BOND_YIELD_REFRESH_INTERVAL - timedelta(seconds=1)).isoformat(),
    )

    # 2. 模拟国债收益率 API 失败（返回 None）
    monkeypatch.setattr(fetcher, '_fetch_bond_yield_api', lambda *args, **kwargs: None)

    null_reasons = {}
    snapshot = fetcher._fetch_bond_yield(null_reasons)

    assert snapshot is not None
    assert snapshot['value'] == 2.15
    assert 'bond_yield_10y' not in null_reasons


def test_fetch_bond_yield_without_recent_snapshot_is_missing(monkeypatch, isolated_db):
    """No hardcoded baseline is allowed when the API and snapshot both fail."""
    import sqlite3
    # 初始化 DB 以确保表结构存在
    cache.get_db().close()
    # 保证 DB 里没有任何股票的缓存
    with closing(sqlite3.connect(isolated_db)) as conn:
        conn.execute("DELETE FROM stock_fundamentals")
        conn.commit()

    monkeypatch.setattr(fetcher, '_fetch_bond_yield_api', lambda *args, **kwargs: None)

    null_reasons = {}
    snapshot = fetcher._fetch_bond_yield(null_reasons)

    assert snapshot is None
    assert null_reasons['bond_yield_10y'] == '国债收益率API失败，且无24小时内可信快照'


def test_fetch_bond_yield_reuses_one_hour_snapshot_without_api(monkeypatch):
    cache.set_market_indicator_snapshot(
        'bond_yield_10y', 2.15, '2026-07-14', 'fixture-source'
    )
    monkeypatch.setattr(
        fetcher,
        '_fetch_bond_yield_api',
        lambda *args, **kwargs: pytest.fail('fresh global snapshot must avoid API call'),
    )

    snapshot = fetcher._fetch_bond_yield({})

    assert snapshot is not None
    assert snapshot['value'] == 2.15


# ── _detect_split_ratio tests ──────────────────────────────────────────────────

def _make_div_df(rows: list[dict]) -> 'pd.DataFrame':
    """构造 stock_fhps_detail_em 格式的 mock DataFrame"""
    import pandas as pd
    return pd.DataFrame(rows)


def test_detect_split_ratio_no_data():
    """div_df 为空时返回 (0.0, None)"""
    import pandas as pd
    result = fetcher._detect_split_ratio(pd.DataFrame(), 2025)
    assert result == (0.0, None)


def test_detect_split_ratio_normal_split():
    """正常送转事件：10转2 → ratio=0.2, ex_date 正确"""
    div_df = _make_div_df([{
        '送转股份-送转总比例': 2.0,
        '除权除息日': '2026-05-26',
        '方案进度': '实施分配',
    }])
    ratio, ex_date = fetcher._detect_split_ratio(div_df, 2025)
    assert abs(ratio - 0.2) < 1e-5
    assert ex_date == '2026-05-26'


def test_detect_split_ratio_future_ex_date_ignored():
    """除权日在未来时不触发（避免提前调整 EPS）"""
    import datetime
    future = (datetime.date.today() + datetime.timedelta(days=5)).strftime('%Y-%m-%d')
    div_df = _make_div_df([{
        '送转股份-送转总比例': 2.0,
        '除权除息日': future,
        '方案进度': '实施分配',
    }])
    ratio, ex_date = fetcher._detect_split_ratio(div_df, 2025)
    assert ratio == 0.0
    assert ex_date is None


def test_detect_split_ratio_before_report_year_ignored():
    """早于最新年报期末的送转不触发（已反映在年报 EPS 中）"""
    div_df = _make_div_df([{
        '送转股份-送转总比例': 2.0,
        '除权除息日': '2024-06-01',  # before 2025-12-31
        '方案进度': '实施分配',
    }])
    ratio, ex_date = fetcher._detect_split_ratio(div_df, 2025)
    assert ratio == 0.0


def test_detect_split_ratio_non_implemented_ignored():
    """方案进度非"实施分配"时不触发"""
    div_df = _make_div_df([{
        '送转股份-送转总比例': 2.0,
        '除权除息日': '2026-05-26',
        '方案进度': '预案',
    }])
    ratio, ex_date = fetcher._detect_split_ratio(div_df, 2025)
    assert ratio == 0.0


def test_detect_split_ratio_cumulative():
    """两次送转累乘：10转2 (0.2) 后再 10转1 (0.1) → factor=1.2×1.1=1.32, ratio≈0.32"""
    div_df = _make_div_df([
        {'送转股份-送转总比例': 2.0, '除权除息日': '2026-03-01', '方案进度': '实施分配'},
        {'送转股份-送转总比例': 1.0, '除权除息日': '2026-05-01', '方案进度': '实施分配'},
    ])
    ratio, ex_date = fetcher._detect_split_ratio(div_df, 2025)
    assert abs(ratio - 0.32) < 1e-5
    assert ex_date == '2026-05-01'


def test_fetch_dividend_api_failure_returns_zero_float(monkeypatch):
    """_fetch_dividend API 超时时返回 (0.0, None)，不崩溃"""
    monkeypatch.setattr(fetcher, 'timed_call', lambda *a, **kw: '超时')
    results = {}
    null_reasons = {}
    ret = fetcher._fetch_dividend('603606', 42.0, results, null_reasons, 2025)
    assert ret == (0.0, None)
    assert 'dividend_yield' in null_reasons


# ── compute_pe_percentile split adjustment tests ────────────────────────────────

def _make_price_df(start: str, end: str, base_price: float) -> 'pd.DataFrame':
    """构造日期序列价格 DataFrame（用于 PE/PB 分位测试）"""
    import pandas as pd
    dates = pd.date_range(start, end, freq='B')  # business days
    return pd.DataFrame({
        'date': dates.astype('datetime64[us]'),
        '收盘': [base_price] * len(dates),
    })


def _make_fin_df_with_period(year: int, eps: float, bps: float) -> 'pd.DataFrame':
    """构造含报告期的财务 DataFrame"""
    import pandas as pd
    return pd.DataFrame([{
        '报告期': str(year),
        '基本每股收益': str(eps),
        '每股净资产': str(bps),
        '净资产收益率': '15.00',
        '净利润同比增长率': '10.00',
        '资产负债率': '40.00',
        '销售毛利率': '30.00',
        '营业总收入同比增长率': '10.00',
        '流动比率': '2.00',
        '每股经营现金流': '3.00',
    }])


def test_compute_pe_percentile_no_split():
    """无送转时 PE 分位正常计算（基线测试）"""
    fin_df = _make_fin_df_with_period(2024, eps=2.0, bps=15.0)
    # 价格全部用 40元，EPS=2.0 → PE=20x
    price_df = _make_price_df('2025-05-01', '2026-06-01', base_price=40.0)
    pct = fetcher.compute_pe_percentile('test', 20.0, fin_df, price_df=price_df)
    # 所有历史PE均=20x，current_pe=20x → 分位约50%（恰好在中位）
    assert pct is not None
    assert isinstance(pct, float)


def test_compute_pe_percentile_with_split_adjusts_post_split_eps():
    """送转后：除权日后的历史 EPS 被除以 (1+ratio)，PE 序列不再凹陷"""
    import pandas as pd
    fin_df = _make_fin_df_with_period(2024, eps=2.4, bps=15.0)
    # 前一半价格 = 60 (pre-split), 后一半价格 = 50 (post-split, 10转2)
    pre_dates = pd.date_range('2025-05-01', '2025-12-31', freq='B')
    post_dates = pd.date_range('2026-01-02', '2026-06-01', freq='B')
    price_df = pd.DataFrame({
        'date': pd.concat([
            pd.Series(pre_dates.astype('datetime64[us]')),
            pd.Series(post_dates.astype('datetime64[us]')),
        ]).reset_index(drop=True),
        '收盘': [60.0] * len(pre_dates) + [50.0] * len(post_dates),
    })

    # Without split adjustment: post-split PE = 50/2.4 = 20.8x, pre-split PE = 60/2.4 = 25x
    # With split adjustment (ratio=0.2): post-split adjusted eps = 2.4/1.2 = 2.0
    #   → post-split PE in series = 50/2.0 = 25x (same as pre-split) — no dip
    pct_no_adj = fetcher.compute_pe_percentile('test', 25.0, fin_df, price_df=price_df)
    pct_adj    = fetcher.compute_pe_percentile('test', 25.0, fin_df, price_df=price_df,
                                               split_ratio=0.2, split_ex_date='2026-01-02')

    # With adjustment, adjusted EPS = 2.4/1.2 = 2.0 for post-split dates
    # → all historical PEs = 25x = current_pe; strict less-than → percentile = 0.0%
    # Without adjustment, post-split PEs ~20.8x drag series lower → pct_no_adj > 0
    assert pct_adj == 0.0
    assert pct_no_adj is not None and pct_no_adj > 0


def test_compute_pb_percentile_with_split_adjusts_post_split_bps():
    """同理验证 PB 分位：除权后 BPS 也被调整"""
    import pandas as pd
    fin_df = _make_fin_df_with_period(2024, eps=2.0, bps=12.0)
    pre_dates = pd.date_range('2025-05-01', '2025-12-31', freq='B')
    post_dates = pd.date_range('2026-01-02', '2026-06-01', freq='B')
    price_df = pd.DataFrame({
        'date': pd.concat([
            pd.Series(pre_dates.astype('datetime64[us]')),
            pd.Series(post_dates.astype('datetime64[us]')),
        ]).reset_index(drop=True),
        '收盘': [24.0] * len(pre_dates) + [20.0] * len(post_dates),
    })

    pct_no_adj = fetcher.compute_pb_percentile('test', 2.0, fin_df, price_df=price_df)
    pct_adj    = fetcher.compute_pb_percentile('test', 2.0, fin_df, price_df=price_df,
                                               split_ratio=0.2, split_ex_date='2026-01-02')
    # BPS 调整后所有历史 PB = 2.0 = current_pb，严格小于比较 → pct_adj = 0.0%
    assert pct_adj == 0.0
    assert pct_no_adj is not None and pct_no_adj > 0
