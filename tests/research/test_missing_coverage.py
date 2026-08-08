"""
补充测试覆盖：
  - cache.py: cmd_set/cmd_get、cmd_get_analysis、cmd_set_score_breakdown、
              cmd_set_flag/cmd_clear_flag、cmd_remove_holding、cmd_cleanup/cmd_clear、
              fetch_current_price 前缀路由、cmd_check_holdings 精确边界、
              get_watchlist_rows 排序与 needs_refresh=False、并发迁移安全性
  - fetcher.py: _market_prefix、timed_call（超时/异常）、timed_call_with_retry、
                parse_float 边界值、avg_of 边界值、compute_dividend_yield 各分支
"""
import json
import sqlite3
import threading
from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import MagicMock

import pytest

from a_stock_agent_runtime import cache
from tests.helpers import record_valid_quote, set_valid_fundamentals, valid_fundamentals_payload
from a_stock_agent_runtime import fetcher


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_extra.db"
    monkeypatch.setattr(cache, 'DB_PATH', str(db_file))
    yield str(db_file)


# ── helpers ──────────────────────────────────────────────────────────────────

def _insert_analysis(code: str, result: str = '结论', score: int | None = None):
    today = datetime.now().strftime('%Y-%m-%d')
    conn = cache.get_db()
    conn.execute(
        "INSERT INTO analysis_results (code, date, result, created_at, score) VALUES (?,?,?,?,?)",
        (code, today, result, datetime.now().isoformat(), score)
    )
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════
#  cache.py — cmd_set / cmd_get
# ═══════════════════════════════════════════════════════════════════

class TestCmdSetAndGet:
    def test_cmd_set_writes_and_get_reads_back(self, capsys):
        payload = json.dumps(valid_fundamentals_payload({'pe': 5.2, 'pb': 0.6}), ensure_ascii=False)
        cache.cmd_set(['600000', '浦发银行', '国有大行', payload])
        capsys.readouterr()  # discard set output

        cache.cmd_get(['600000'])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data['pe'] == 5.2
        assert data['pb'] == 0.6
        assert data['_cache_meta']['code'] == '600000'

    def test_cmd_set_confirms_industry_ttl(self, capsys):
        payload = json.dumps(valid_fundamentals_payload({}), ensure_ascii=False)
        cache.cmd_set(['601318', '中国平安', '保险', payload])
        out = capsys.readouterr().out
        assert 'TTL:72h' in out

    def test_cmd_set_explicit_ttl_overrides_industry(self, capsys):
        payload = json.dumps(valid_fundamentals_payload({}), ensure_ascii=False)
        cache.cmd_set(['000858', '五粮液', '白酒', payload, '48'])
        out = capsys.readouterr().out
        assert 'TTL:48h' in out

    def test_cmd_set_invalid_json_exits(self):
        with pytest.raises(SystemExit) as exc:
            cache.cmd_set(['600000', '名称', '行业', '{invalid json}'])
        assert exc.value.code == 1

    def test_cmd_set_missing_args_exits(self):
        with pytest.raises(SystemExit) as exc:
            cache.cmd_set(['600000', '名称'])
        assert exc.value.code == 1

    def test_cmd_get_miss(self, capsys):
        cache.cmd_get(['999999'])
        out = capsys.readouterr().out
        assert out.strip() == 'CACHE_MISS'

    def test_cmd_get_expired_returns_cache_miss(self, capsys, monkeypatch):
        payload = json.dumps(valid_fundamentals_payload({'roe': 15}), ensure_ascii=False)
        cache.cmd_set(['600036', '招商银行', '银行', payload])
        capsys.readouterr()
        monkeypatch.setattr(cache, 'is_expired', lambda *_: True)
        cache.cmd_get(['600036'])
        out = capsys.readouterr().out
        assert out.strip() == 'CACHE_MISS'

    def test_cmd_get_no_args_returns_cache_miss(self, capsys):
        cache.cmd_get([])
        out = capsys.readouterr().out
        assert out.strip() == 'CACHE_MISS'


# ═══════════════════════════════════════════════════════════════════
#  cache.py — cmd_get_analysis
# ═══════════════════════════════════════════════════════════════════

class TestCmdGetAnalysis:
    def test_hit_returns_cached_result(self, capsys):
        _insert_analysis('600036', '招行分析：买入')
        cache.cmd_get_analysis(['600036'])
        out = capsys.readouterr().out
        assert '招行分析：买入' in out
        assert '缓存命中' in out

    def test_miss_returns_cache_miss(self, capsys):
        cache.cmd_get_analysis(['999999'])
        assert capsys.readouterr().out.strip() == 'CACHE_MISS'

    def test_no_args_returns_cache_miss(self, capsys):
        cache.cmd_get_analysis([])
        assert capsys.readouterr().out.strip() == 'CACHE_MISS'


# ═══════════════════════════════════════════════════════════════════
#  cache.py — cmd_set_score_breakdown
# ═══════════════════════════════════════════════════════════════════

class TestCmdSetScoreBreakdown:
    def test_valid_breakdown_stored(self, capsys):
        _insert_analysis('600036')
        breakdown = {
            'fundamentals': {'roe_3y': 10, 'subtotal': 44},
            'timing': {'valuation_axis': 13, 'subtotal': 17},
            'total': 61,
        }
        cache.cmd_set_score_breakdown(['600036', json.dumps(breakdown)])
        out = capsys.readouterr().out
        assert '分项得分已记录' in out

        # Verify it's actually in the database
        today = datetime.now().strftime('%Y-%m-%d')
        conn = cache.get_db()
        row = conn.execute(
            'SELECT score_breakdown FROM analysis_results WHERE code=? AND date=?',
            ('600036', today)
        ).fetchone()
        conn.close()
        stored = json.loads(row[0])
        assert stored['fundamentals']['subtotal'] == 44

    def test_no_analysis_record_exits(self):
        breakdown = {'fundamentals': {'subtotal': 1}, 'timing': {'subtotal': 1}}
        with pytest.raises(SystemExit) as exc:
            cache.cmd_set_score_breakdown(['888888', json.dumps(breakdown)])
        assert exc.value.code == 1

    def test_invalid_json_exits(self):
        _insert_analysis('600036')
        with pytest.raises(SystemExit) as exc:
            cache.cmd_set_score_breakdown(['600036', '{bad json}'])
        assert exc.value.code == 1

    def test_legacy_flat_schema_rejected(self, capsys):
        """旧平铺 schema（无 fundamentals/timing）写入应被拒绝（TL-3 写入校验）"""
        _insert_analysis('600036')
        with pytest.raises(SystemExit) as exc:
            cache.cmd_set_score_breakdown(['600036', '{"roe": 8, "volume": 7}'])
        assert exc.value.code == 1
        assert 'fundamentals' in capsys.readouterr().err

    @pytest.mark.parametrize('json_string', ['null', '123', '["fundamentals","timing"]'])
    def test_non_dict_top_level_json_rejected(self, json_string, capsys):
        _insert_analysis('600036')
        with pytest.raises(SystemExit) as exc:
            cache.cmd_set_score_breakdown(['600036', json_string])
        assert exc.value.code == 1
        assert 'dict' in capsys.readouterr().err

    def test_missing_subtotal_rejected(self):
        _insert_analysis('600036')
        breakdown = {'fundamentals': {'roe_3y': 10}, 'timing': {'subtotal': 17}}
        with pytest.raises(SystemExit) as exc:
            cache.cmd_set_score_breakdown(['600036', json.dumps(breakdown)])
        assert exc.value.code == 1

    @pytest.mark.parametrize('bad_subtotal', [True, [1, 2]])
    def test_non_numeric_subtotal_rejected(self, bad_subtotal, capsys):
        _insert_analysis('600036')
        breakdown = {'fundamentals': {'subtotal': bad_subtotal}, 'timing': {'subtotal': 1}}
        with pytest.raises(SystemExit) as exc:
            cache.cmd_set_score_breakdown(['600036', json.dumps(breakdown)])
        assert exc.value.code == 1
        assert 'subtotal' in capsys.readouterr().err

    @pytest.mark.parametrize('breakdown', [
        {'fundamentals': {'subtotal': 61}, 'timing': {'subtotal': 0}, 'total': 61},
        {'fundamentals': {'subtotal': 40}, 'timing': {'subtotal': 15}, 'total': 99},
        {'fundamentals': {'subtotal': float('nan')}, 'timing': {'subtotal': 15}, 'total': float('nan')},
    ])
    def test_breakdown_rejects_invalid_bounds_total_and_nan(self, breakdown):
        _insert_analysis('600036')
        with pytest.raises(SystemExit):
            cache.cmd_set_score_breakdown(['600036', json.dumps(breakdown)])

    def test_breakdown_must_match_persisted_score(self):
        _insert_analysis('600036', score=60)
        breakdown = {'fundamentals': {'subtotal': 44}, 'timing': {'subtotal': 17}, 'total': 61}
        with pytest.raises(SystemExit):
            cache.cmd_set_score_breakdown(['600036', json.dumps(breakdown)])


# ═══════════════════════════════════════════════════════════════════
#  cache.py — cmd_set_flag / cmd_clear_flag
# ═══════════════════════════════════════════════════════════════════

class TestSetAndClearFlag:
    def test_set_red_flag_stored(self, capsys):
        _insert_analysis('000001')
        cache.cmd_set_flag(['000001', 'red', '大股东减持超5%'])
        out = capsys.readouterr().out
        assert '🔴' in out
        assert '大股东减持超5%' in out

    def test_set_yellow_flag_stored(self, capsys):
        _insert_analysis('000001')
        cache.cmd_set_flag(['000001', 'yellow', '短期涨幅过大'])
        out = capsys.readouterr().out
        assert '⚠️' in out

    def test_invalid_level_exits(self):
        _insert_analysis('000001')
        with pytest.raises(SystemExit) as exc:
            cache.cmd_set_flag(['000001', 'green', '理由'])
        assert exc.value.code == 1

    def test_no_analysis_record_exits(self):
        with pytest.raises(SystemExit) as exc:
            cache.cmd_set_flag(['999999', 'red', '理由'])
        assert exc.value.code == 1

    def test_multiple_flags_accumulate(self, capsys):
        """set-flag must append, not overwrite — two calls yield two entries."""
        _insert_analysis('600036')
        cache.cmd_set_flag(['600036', 'yellow', '第一条'])
        cache.cmd_set_flag(['600036', 'red', '第二条'])
        capsys.readouterr()

        today = datetime.now().strftime('%Y-%m-%d')
        conn = cache.get_db()
        row = conn.execute(
            'SELECT flags FROM analysis_results WHERE code=? AND date=?',
            ('600036', today)
        ).fetchone()
        conn.close()
        flags = json.loads(row[0])
        assert len(flags) == 2
        assert flags[0]['level'] == 'yellow'
        assert flags[1]['level'] == 'red'

    def test_clear_flag_removes_all(self, capsys):
        _insert_analysis('600036')
        cache.cmd_set_flag(['600036', 'red', '某原因'])
        capsys.readouterr()

        cache.cmd_clear_flag(['600036'])
        today = datetime.now().strftime('%Y-%m-%d')
        conn = cache.get_db()
        row = conn.execute(
            'SELECT flags FROM analysis_results WHERE code=? AND date=?',
            ('600036', today)
        ).fetchone()
        conn.close()
        assert row[0] is None


# ═══════════════════════════════════════════════════════════════════
#  cache.py — cmd_remove_holding
# ═══════════════════════════════════════════════════════════════════

class TestRemoveHolding:
    def test_removes_existing_holding(self, capsys):
        cache.cmd_add_holding(['600519', '1800'])
        capsys.readouterr()
        cache.cmd_remove_holding(['600519'])
        out = capsys.readouterr().out
        assert '600519' in out

        conn = cache.get_db()
        cnt = conn.execute("SELECT COUNT(*) FROM holdings WHERE code='600519'").fetchone()[0]
        conn.close()
        assert cnt == 0

    def test_nonexistent_holding_exits(self):
        with pytest.raises(SystemExit) as exc:
            cache.cmd_remove_holding(['999888'])
        assert exc.value.code == 1


# ═══════════════════════════════════════════════════════════════════
#  cache.py — cmd_cleanup / cmd_clear
# ═══════════════════════════════════════════════════════════════════

class TestCleanupAndClear:
    def test_cleanup_removes_expired_fundamentals(self, capsys, monkeypatch):
        set_valid_fundamentals('600000', '浦发银行', '银行', {'pe': 5})
        monkeypatch.setattr(cache, 'is_expired', lambda *_: True)
        cache.cmd_cleanup()
        out = capsys.readouterr().out
        assert '浦发银行' in out

        conn = cache.get_db()
        row = conn.execute("SELECT code FROM stock_fundamentals WHERE code='600000'").fetchone()
        conn.close()
        assert row is None

    def test_cleanup_retains_scheduler_window_and_removes_only_older_analysis(
        self, capsys, monkeypatch
    ):
        now = cache.utc_now()
        monkeypatch.setattr(cache, 'utc_now', lambda: now)
        conn = cache.get_db()
        conn.executemany(
            "INSERT INTO analysis_results (code, date, result, created_at) VALUES (?,?,?,?)",
            [
                ('RECENT', (now - timedelta(days=1)).date().isoformat(),
                 '调度窗口内', (now - timedelta(days=1)).isoformat()),
                ('BOUNDARY', (now - timedelta(days=14)).date().isoformat(),
                 '调度窗口边界', (now - timedelta(days=14)).isoformat()),
                ('OLD', (now - timedelta(days=14, microseconds=1)).date().isoformat(),
                 '调度窗口外', (now - timedelta(days=14, microseconds=1)).isoformat()),
            ],
        )
        conn.commit()
        conn.close()

        cache.cmd_cleanup()
        out = capsys.readouterr().out
        assert '1 条历史分析结论' in out
        conn = cache.get_db()
        remaining = {row[0] for row in conn.execute('SELECT code FROM analysis_results')}
        conn.close()
        assert remaining == {'RECENT', 'BOUNDARY'}

    def test_cleanup_no_expired_reports_clean(self, capsys):
        set_valid_fundamentals('000001', '平安银行', '银行', {'pb': 0.7})
        cache.cmd_cleanup()
        out = capsys.readouterr().out
        assert '无过期' in out

    def test_clear_all_removes_everything(self, capsys):
        set_valid_fundamentals('600036', '招商银行', '银行', {'roe': 15})
        _insert_analysis('600036')
        record_valid_quote('600036')
        cache.set_market_indicator_snapshot('bond_yield_10y', 1.7, '2026-07-14', 'test')
        cache.update_qualitative_only_security('601318', '中国平安', '保险')
        cache.cmd_clear([])
        capsys.readouterr()

        conn = cache.get_db()
        f = conn.execute("SELECT COUNT(*) FROM stock_fundamentals").fetchone()[0]
        a = conn.execute("SELECT COUNT(*) FROM analysis_results").fetchone()[0]
        q = conn.execute("SELECT COUNT(*) FROM quote_snapshots").fetchone()[0]
        m = conn.execute("SELECT COUNT(*) FROM market_indicator_snapshots").fetchone()[0]
        qo = conn.execute("SELECT COUNT(*) FROM qualitative_only_securities").fetchone()[0]
        conn.close()
        assert f == 0
        assert a == 0
        assert q == 0
        assert m == 0
        assert qo == 0

    def test_clear_specific_code_leaves_others(self, capsys):
        set_valid_fundamentals('600036', '招商银行', '银行', {'roe': 15})
        set_valid_fundamentals('601318', '中国平安', '保险', {'pb': 1.2})
        record_valid_quote('600036')
        record_valid_quote('601318')
        cache.update_qualitative_only_security('600036', '招商银行', '证券')
        cache.update_qualitative_only_security('601318', '中国平安', '保险')
        cache.cmd_clear(['600036'])
        capsys.readouterr()

        conn = cache.get_db()
        cnt = conn.execute("SELECT COUNT(*) FROM stock_fundamentals").fetchone()[0]
        row = conn.execute("SELECT code FROM stock_fundamentals WHERE code='601318'").fetchone()
        quotes = {item[0] for item in conn.execute('SELECT code FROM quote_snapshots')}
        qualitative = {
            item[0] for item in conn.execute('SELECT code FROM qualitative_only_securities')
        }
        conn.close()
        assert cnt == 1
        assert row is not None
        assert quotes == {'601318'}
        assert qualitative == {'601318'}


# ═══════════════════════════════════════════════════════════════════
#  cache.py — cmd_check_holdings 精确边界
# ═══════════════════════════════════════════════════════════════════

class TestCheckHoldingsBoundary:
    """价格恰好等于止损线时的行为（<=运算符的边界条件）"""

    def _add_holding_cost40(self):
        # cost=40 → sl15=34.000, sl20=32.000
        cache.cmd_add_holding(['600036', '40.0', '100', '测试'])

    def test_price_exactly_at_15pct_stop_triggers_yellow(self, capsys, monkeypatch):
        self._add_holding_cost40()
        monkeypatch.setattr(cache, 'fetch_current_price', lambda code: 34.0)
        cache.cmd_check_holdings()
        out = capsys.readouterr().out
        assert '⚠️ 已跌破15%止损线' in out
        assert '共 1 项预警' in out

    def test_price_exactly_at_20pct_stop_triggers_red(self, capsys, monkeypatch):
        self._add_holding_cost40()
        monkeypatch.setattr(cache, 'fetch_current_price', lambda code: 32.0)
        cache.cmd_check_holdings()
        out = capsys.readouterr().out
        assert '🔴 已跌破20%止损线' in out
        assert '建议立即止损' in out

    def test_price_one_cent_above_15pct_stop_is_normal(self, capsys, monkeypatch):
        """34.001 > sl15=34.000，不应触发预警"""
        self._add_holding_cost40()
        monkeypatch.setattr(cache, 'fetch_current_price', lambda code: 34.001)
        cache.cmd_check_holdings()
        out = capsys.readouterr().out
        assert '✅ 正常' in out
        assert '无预警' in out


# ═══════════════════════════════════════════════════════════════════
#  cache.py — get_watchlist_rows / cmd_watchlist 排序与 needs_refresh
# ═══════════════════════════════════════════════════════════════════

class TestWatchlistRows:
    def test_needs_refresh_false_when_analysed_today(self, capsys):
        set_valid_fundamentals('600036', '招商银行', '银行', {'pe_ttm': 5.5})
        _insert_analysis('600036', score=62)
        cache.cmd_watchlist(['--json'])
        rows = json.loads(capsys.readouterr().out)
        assert rows[0]['code'] == '600036'
        assert rows[0]['needs_refresh'] is False

    def test_ordering_scored_before_unscored(self, capsys):
        """Pending first analysis is prioritized ahead of an already-current row."""
        set_valid_fundamentals('000001', '平安银行', '银行', {})
        set_valid_fundamentals('600036', '招商银行', '银行', {})
        record_valid_quote('000001')
        _insert_analysis('600036', score=55)  # only 600036 has analysis today

        cache.cmd_watchlist(['--json'])
        rows = json.loads(capsys.readouterr().out)
        codes = [r['code'] for r in rows]
        assert codes.index('000001') < codes.index('600036')

    def test_expired_stocks_excluded(self, capsys, monkeypatch):
        set_valid_fundamentals('600036', '招商银行', '银行', {})
        monkeypatch.setattr(cache, 'is_expired', lambda *_: True)
        cache.cmd_watchlist(['--json'])
        rows = json.loads(capsys.readouterr().out)
        assert rows == []

    def test_watchlist_flags_shown_in_json(self, capsys):
        set_valid_fundamentals('600036', '招商银行', '银行', {})
        _insert_analysis('600036')
        cache.cmd_set_flag(['600036', 'red', '大股东减持'])
        capsys.readouterr()
        cache.cmd_watchlist(['--json'])
        rows = json.loads(capsys.readouterr().out)
        assert rows[0]['flags'][0]['level'] == 'red'


# ═══════════════════════════════════════════════════════════════════
#  cache.py — fetch_current_price 市场前缀路由
# ═══════════════════════════════════════════════════════════════════

class TestFetchCurrentPrice:
    def _make_mock_get(self, monkeypatch, price_field: str, captured: dict):
        class MockResp:
            encoding = 'gbk'
            # Sina format: "name,yesterday,open,current,high,low,..."
            text = f'var hq_str_sh000000="{price_field}"'

        def mock_get(url, **kwargs):
            captured['url'] = url
            r = MockResp()
            r.text = r.text.replace('hq_str_sh000000',
                                    f"hq_str_{url.split('=')[1]}")
            r.text = f'var hq_str_x="{price_field}"'
            return r

        monkeypatch.setattr(cache.requests, 'get', mock_get)

    def test_sh_prefix_for_6xx_codes(self, monkeypatch):
        captured = {}

        def mock_get(url, **kwargs):
            captured['url'] = url
            r = MagicMock()
            r.encoding = 'gbk'
            r.text = 'var x="招商银行,40.0,40.1,41.50,42.0,39.8"'
            return r

        monkeypatch.setattr(cache.requests, 'get', mock_get)
        price = cache.fetch_current_price('600036')
        assert 'sh600036' in captured['url']
        assert price == 41.50

    def test_sz_prefix_for_0xx_codes(self, monkeypatch):
        captured = {}

        def mock_get(url, **kwargs):
            captured['url'] = url
            r = MagicMock()
            r.encoding = 'gbk'
            r.text = 'var x="平安银行,10.0,10.1,10.20,10.5,9.9"'
            return r

        monkeypatch.setattr(cache.requests, 'get', mock_get)
        cache.fetch_current_price('000001')
        assert 'sz000001' in captured['url']

    def test_bj_prefix_for_4xx_codes(self, monkeypatch):
        captured = {}

        def mock_get(url, **kwargs):
            captured['url'] = url
            r = MagicMock()
            r.encoding = 'gbk'
            r.text = 'var x="某北交所,5.0,5.1,5.20,5.5,4.9"'
            return r

        monkeypatch.setattr(cache.requests, 'get', mock_get)
        cache.fetch_current_price('430570')
        assert 'bj430570' in captured['url']

    def test_bj_prefix_for_8xx_codes(self, monkeypatch):
        captured = {}

        def mock_get(url, **kwargs):
            captured['url'] = url
            r = MagicMock()
            r.encoding = 'gbk'
            r.text = 'var x="某北交所,1.0,1.0,1.10,1.2,0.9"'
            return r

        monkeypatch.setattr(cache.requests, 'get', mock_get)
        cache.fetch_current_price('872925')
        assert 'bj872925' in captured['url']

    def test_malformed_response_returns_none(self, monkeypatch):
        """Fewer than 4 fields in the response body → None, no crash."""
        def mock_get(url, **kwargs):
            r = MagicMock()
            r.encoding = 'gbk'
            r.text = 'var x="only,three"'
            return r

        monkeypatch.setattr(cache.requests, 'get', mock_get)
        assert cache.fetch_current_price('600036') is None

    def test_empty_quotes_returns_none(self, monkeypatch):
        def mock_get(url, **kwargs):
            r = MagicMock()
            r.encoding = 'gbk'
            r.text = 'var x=""'
            return r

        monkeypatch.setattr(cache.requests, 'get', mock_get)
        assert cache.fetch_current_price('600036') is None

    def test_request_exception_returns_none(self, monkeypatch):
        import requests as req

        def mock_get(url, **kwargs):
            raise req.RequestException("network error")

        monkeypatch.setattr(cache.requests, 'get', mock_get)
        assert cache.fetch_current_price('600036') is None

    def test_fetch_current_prices_batch_success(self, monkeypatch):
        captured = {}

        def mock_get(url, **kwargs):
            captured['url'] = url
            r = MagicMock()
            r.encoding = 'gbk'
            # Sina batch format: multiple lines of var hq_str_sh600036="..."
            r.text = (
                'var hq_str_sh600036="招商银行,40.0,40.1,41.50,42.0,39.8"\n'
                'var hq_str_sz000001="平安银行,10.0,10.1,10.20,10.5,9.9"\n'
            )
            return r

        monkeypatch.setattr(cache.requests, 'get', mock_get)
        res = cache.fetch_current_prices(['600036', '000001'])
        assert 'sh600036,sz000001' in captured['url']
        assert res['600036'] == 41.50
        assert res['000001'] == 10.20

    def test_fetch_current_price_quotes_parses_date_and_time(self, monkeypatch):
        """真实新浪返回32字段（含日期/时间）时，fetch_current_price_quotes 能正确提取 quote_date/quote_time（BUG-006）"""
        def mock_get(url, **kwargs):
            r = MagicMock()
            r.encoding = 'gbk'
            fields = ['招商银行', '40.0', '40.1', '41.50', '42.0', '39.8', '41.49', '41.51',
                      '123456', '987654321'] + [str(x) for x in range(100, 120)] + \
                     ['2026-07-02', '15:00:00']
            r.text = f'var hq_str_sh600036="{",".join(fields)}"\n'
            return r

        monkeypatch.setattr(cache.requests, 'get', mock_get)
        res = cache.fetch_current_price_quotes(['600036'])
        quote = res['600036']
        assert quote.price == 41.50
        assert quote.quote_date == '2026-07-02'
        assert quote.quote_time == '15:00:00'

    def test_fetch_current_price_quotes_short_fields_degrade_to_none(self, monkeypatch):
        """字段不足32个（旧格式/异常返回）时 quote_date/quote_time 降级为 None，不报错"""
        def mock_get(url, **kwargs):
            r = MagicMock()
            r.encoding = 'gbk'
            r.text = 'var hq_str_sh600036="招商银行,40.0,40.1,41.50,42.0,39.8"\n'
            return r

        monkeypatch.setattr(cache.requests, 'get', mock_get)
        res = cache.fetch_current_price_quotes(['600036'])
        quote = res['600036']
        assert quote.price == 41.50
        assert quote.quote_date is None
        assert quote.quote_time is None

    def test_fetch_current_prices_empty(self):
        res = cache.fetch_current_prices([])
        assert res == {}

    def test_fetch_current_prices_mock_compat(self, monkeypatch):
        # When fetch_current_price is mocked, fetch_current_prices delegates to it
        monkeypatch.setattr(cache, 'fetch_current_price', lambda code: 99.9)
        res = cache.fetch_current_prices(['600036', '000001'])
        assert res['600036'] == 99.9
        assert res['000001'] == 99.9


# ═══════════════════════════════════════════════════════════════════
#  cache.py — cmd_set_analysis 边界
# ═══════════════════════════════════════════════════════════════════

class TestSetAnalysisBoundary:
    def test_empty_stdin_exits(self, monkeypatch):
        monkeypatch.setattr('sys.stdin', StringIO(''))
        with pytest.raises(SystemExit) as exc:
            cache.cmd_set_analysis(['600036'])
        assert exc.value.code == 1

    def test_whitespace_only_stdin_exits(self, monkeypatch):
        monkeypatch.setattr('sys.stdin', StringIO('   \n  '))
        with pytest.raises(SystemExit) as exc:
            cache.cmd_set_analysis(['600036'])
        assert exc.value.code == 1


# ═══════════════════════════════════════════════════════════════════
#  cache.py — cmd_close_holding 自定义日期
# ═══════════════════════════════════════════════════════════════════

class TestCloseHoldingCustomDate:
    def test_custom_exit_date_stored(self, capsys):
        cache.cmd_add_holding(['000001', '10.0', '100', '--date', '2025-12-01'])
        capsys.readouterr()
        cache.cmd_close_holding(['000001', '12.0', '2025-12-31'])
        capsys.readouterr()

        conn = cache.get_db()
        row = conn.execute(
            "SELECT exit_date FROM holdings WHERE code='000001'"
        ).fetchone()
        conn.close()
        assert row[0] == '2025-12-31'

# ═══════════════════════════════════════════════════════════════════
#  cache.py — 并发 get_db() 迁移安全性
# ═══════════════════════════════════════════════════════════════════

def test_get_db_concurrent_migration_preserves_data(tmp_path, monkeypatch):
    """Two threads running get_db() on old-schema DB must not lose holding data."""
    db_path = str(tmp_path / 'concurrent.db')
    monkeypatch.setattr(cache, 'DB_PATH', db_path)

    # Prepare old-style holdings table (no id column = pre-migration schema)
    conn0 = sqlite3.connect(db_path)
    conn0.executescript('''
        CREATE TABLE IF NOT EXISTS stock_fundamentals (
            code TEXT PRIMARY KEY, name TEXT, industry TEXT, data JSON,
            updated_at TEXT, ttl_hours INTEGER DEFAULT 24);
        CREATE TABLE IF NOT EXISTS analysis_results (
            code TEXT, date TEXT, name TEXT, result TEXT, created_at TEXT,
            score INTEGER, flags TEXT, score_breakdown TEXT,
            return_pct REAL, holding_days INT, PRIMARY KEY (code, date));
        CREATE TABLE holdings (
            code TEXT PRIMARY KEY, name TEXT, cost_price REAL, shares INTEGER,
            buy_date TEXT, buy_score INTEGER, stop_loss_15 REAL,
            stop_loss_20 REAL, notes TEXT, updated_at TEXT,
            exit_price REAL, exit_date TEXT);
        INSERT INTO holdings (code, cost_price) VALUES ('600519', 1800.0);
    ''')
    conn0.commit()
    conn0.close()

    errors: list[Exception] = []
    barrier = threading.Barrier(2)

    def run():
        try:
            barrier.wait()   # both threads enter get_db at roughly the same time
            c = cache.get_db()
            c.close()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=run) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert not errors, f"Concurrent migration raised: {errors}"

    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT cost_price FROM holdings WHERE code='600519'").fetchone()
    cols = [r[1] for r in conn.execute("PRAGMA table_info(holdings)").fetchall()]
    conn.close()

    assert row is not None, "holding data was lost during concurrent migration"
    assert row[0] == 1800.0
    assert 'id' in cols, "id column missing after migration"


# ═══════════════════════════════════════════════════════════════════
#  fetcher.py — _market_prefix
# ═══════════════════════════════════════════════════════════════════

class TestMarketPrefix:
    def test_sh_for_6xx(self):
        assert fetcher._market_prefix('600036') == 'sh'
        assert fetcher._market_prefix('601318') == 'sh'

    def test_sz_for_0xx(self):
        assert fetcher._market_prefix('000001') == 'sz'

    def test_sz_for_3xx(self):
        assert fetcher._market_prefix('300750') == 'sz'

    def test_bj_for_4xx(self):
        assert fetcher._market_prefix('430570') == 'bj'

    def test_bj_for_8xx(self):
        assert fetcher._market_prefix('872925') == 'bj'

    def test_bj_for_920xx(self):
        assert fetcher._market_prefix('920189') == 'bj'


# ═══════════════════════════════════════════════════════════════════
#  fetcher.py — timed_call
# ═══════════════════════════════════════════════════════════════════

class TestTimedCall:
    def test_success_returns_value(self):
        assert fetcher.timed_call(lambda: 42) == 42

    def test_exception_returns_error_tuple(self):
        result = fetcher.timed_call(lambda: 1 / 0)
        assert isinstance(result, tuple)
        assert result[0] == 'ERROR'
        assert 'division by zero' in result[1]

    def test_timeout_returns_timeout_sentinel(self):
        import time
        # Function sleeps 2s; timeout is 0.2s → TIMEOUT
        result = fetcher.timed_call(time.sleep, 2, timeout=0.2)
        assert result == 'TIMEOUT'

    def test_args_forwarded_correctly(self):
        def add(a, b):
            return a + b
        assert fetcher.timed_call(add, 3, 4) == 7


# ═══════════════════════════════════════════════════════════════════
#  fetcher.py — timed_call_with_retry
# ═══════════════════════════════════════════════════════════════════

class TestTimedCallWithRetry:
    def test_zero_retries_returns_no_attempts(self):
        result = fetcher.timed_call_with_retry(lambda: 42, max_retries=0)
        assert result == ('ERROR', 'no attempts made')

    def test_success_on_first_attempt_no_retry(self):
        import multiprocessing as mp
        calls = mp.Value('i', 0)

        def fn():
            with calls.get_lock():
                calls.value += 1
            return 'ok'

        result = fetcher.timed_call_with_retry(fn, max_retries=3)
        assert result == 'ok'
        assert calls.value == 1

    def test_succeeds_on_second_attempt(self, monkeypatch):
        monkeypatch.setattr('time.sleep', lambda _: None)
        import multiprocessing as mp
        calls = mp.Value('i', 0)

        def flaky():
            with calls.get_lock():
                calls.value += 1
                call_number = calls.value
            if call_number == 1:
                raise ValueError("first failure")
            return 'recovered'

        result = fetcher.timed_call_with_retry(flaky, max_retries=3)
        assert result == 'recovered'
        assert calls.value == 2

    def test_all_retries_exhausted_returns_last_error(self, monkeypatch):
        monkeypatch.setattr('time.sleep', lambda _: None)

        def always_fail():
            raise RuntimeError("always fails")

        result = fetcher.timed_call_with_retry(always_fail, max_retries=2)
        assert isinstance(result, tuple)
        assert result[0] == 'ERROR'


# ═══════════════════════════════════════════════════════════════════
#  fetcher.py — parse_float
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("val,expected", [
    (None, None),
    ('--', None),
    ('-', None),
    ('None', None),
    ('nan', None),
    ('False', None),
    ('True', None),
    ('', None),
    ('3.14', 3.14),
    ('15%', 15.0),       # percentage stripped
    (' 2.5 ', 2.5),      # whitespace stripped
    (10, 10.0),          # int passthrough
    (0.0, 0.0),          # zero is valid
    (-5.5, -5.5),        # negative
])
def test_parse_float(val, expected):
    result = fetcher.parse_float(val)
    assert result == expected


def test_parse_float_custom_default():
    assert fetcher.parse_float(None, default=-1.0) == -1.0
    assert fetcher.parse_float('--', default=0.0) == 0.0


def test_parse_float_nonnumeric_string_returns_default():
    assert fetcher.parse_float('abc') is None
    assert fetcher.parse_float('abc', default=99.0) == 99.0


# ═══════════════════════════════════════════════════════════════════
#  fetcher.py — avg_of
# ═══════════════════════════════════════════════════════════════════

def _pd_series(values):
    import pandas as pd
    return pd.Series(values)


class TestAvgOf:
    def test_none_series_returns_none(self):
        assert fetcher.avg_of(None, 3) is None

    def test_all_none_values_returns_none(self):
        assert fetcher.avg_of(_pd_series([None, None, None]), 3) is None

    def test_fewer_than_n_uses_all_available(self):
        # series has 2 values, n=5 → average of those 2
        result = fetcher.avg_of(_pd_series([10.0, 20.0]), 5)
        assert result == 15.0

    def test_normal_last_n(self):
        # last 3 of [10, 20, 30, 40, 50] = [30, 40, 50] → avg=40
        result = fetcher.avg_of(_pd_series([10.0, 20.0, 30.0, 40.0, 50.0]), 3)
        assert result == 40.0

    def test_mixed_none_ignored(self):
        # last 3 of series: [None, 20, 30] → avg of [20, 30] = 25.0
        result = fetcher.avg_of(_pd_series(['--', '20.00', '30.00']), 3)
        assert result == 25.0


# ═══════════════════════════════════════════════════════════════════
#  fetcher.py — compute_dividend_yield
# ═══════════════════════════════════════════════════════════════════

def _make_div_df(period: str = None, amount_per_10: float = 10.00,
                 status: str = '实施分配', use_amount_col: bool = True):
    import pandas as pd
    period = period or datetime.now().strftime('%Y-12-31')
    data: dict = {
        '报告期': [period],
        '方案进度': [status],
    }
    if use_amount_col:
        data['现金分红-现金分红比例'] = [amount_per_10]
    return pd.DataFrame(data)


def _make_multi_div_df(records):
    import pandas as pd
    return pd.DataFrame({
        '报告期': [period for period, _, _ in records],
        '现金分红-现金分红比例': [amount for _, amount, _ in records],
        '方案进度': [status for _, _, status in records],
    })


# compute_dividend_yield 的分红陈旧守卫以 datetime.now() 为基准，而本类夹具用的是
# 真实报告期（如紫金601899的实际分红记录）。两者相减就是定时炸弹：没人改代码、
# 夹具也不动，测试仍会在「最新报告期 + 400天」那天自己变红——2026-08-04 前后
# test_prior_year_annual_not_mixed_with_current_year 就是这么烂掉的。
# 冻结时钟后夹具得以保留真实数据，守卫行为也变成确定性的。
# 测一个"陈旧性守卫"本就该用受控时间，拿真实时钟去测"多久算陈旧"逻辑上讲不通。
_FROZEN_NOW = datetime(2026, 8, 7)


class _FrozenDatetime(datetime):
    """仅替换 now()，其余行为与 datetime 一致（fetcher 用 from datetime import datetime）。"""

    @classmethod
    def now(cls, tz=None):
        return _FROZEN_NOW


class TestComputeDividendYield:
    @pytest.fixture(autouse=True)
    def _freeze_fetcher_clock(self, monkeypatch):
        monkeypatch.setattr(fetcher, 'datetime', _FrozenDatetime)

    def test_normal_calculation(self):
        div_df = _make_div_df(amount_per_10=10.00)  # 1.0 yuan/share
        dy, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=20.0)
        assert dps == 1.0
        assert dy == 5.0   # 1.0 / 20.0 * 100
        assert reason is None

    def test_no_price_returns_none(self):
        div_df = _make_div_df(amount_per_10=10.00)
        dy, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=None)
        assert dy is None
        assert dps is None
        assert reason is not None

    def test_zero_price_returns_none(self):
        div_df = _make_div_df(amount_per_10=10.00)
        dy, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=0)
        assert dy is None

    def test_none_div_df_returns_none(self):
        dy, dps, reason = fetcher.compute_dividend_yield(None, current_price=20.0)
        assert dy is None

    def test_empty_div_df_returns_none(self):
        import pandas as pd
        dy, dps, reason = fetcher.compute_dividend_yield(pd.DataFrame(), current_price=20.0)
        assert dy is None

    def test_missing_report_period_column(self):
        import pandas as pd
        div_df = pd.DataFrame({'现金分红-现金分红比例': [10.0]})
        dy, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=20.0)
        assert dy is None
        assert '报告期' in reason

    def test_pending_status_with_amount_still_counted(self):
        """'董事会决议通过'/'预案'阶段只要已有具体金额就应计入（与人工核实口径一致的前瞻估计）"""
        div_df = _make_div_df(amount_per_10=10.00, status='董事会决议通过')
        dy, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=20.0)
        assert dps == 1.0
        assert reason is None

    def test_dividend_older_than_12_months(self):
        # 基准必须跟着冻结时钟走，否则真实日期与冻结的 now 相减会得出错误结论。
        # 取 401 天而非 400：守卫是 `latest_period < cutoff` 严格小于，正好 400 天
        # 落在边界上不触发。原先用 datetime.now() 能过是沾了时分秒的光（now 带
        # 时间分量、报告期解析成 00:00），属于偶然通过，不是有意为之。
        old_period = (_FROZEN_NOW - timedelta(days=401)).strftime('%Y-%m-%d')
        div_df = _make_div_df(period=old_period)
        dy, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=20.0)
        assert dy is None
        assert '超过12个月' in reason

    def test_zero_dividend_amount(self):
        div_df = _make_div_df(amount_per_10=0)
        dy, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=20.0)
        assert dy is None
        assert '无有效分红金额' in reason

    def test_missing_amount_column_treated_as_no_data(self):
        div_df = _make_div_df(use_amount_col=False)
        dy, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=20.0)
        assert dy is None

    def test_interim_plus_annual_same_year_summed(self):
        """同一财年中期+年度分红应合并计入（如宝钢2025中期0.12+年度0.18=0.30）"""
        import pandas as pd
        div_df = pd.DataFrame({
            '报告期': ['2025-06-30', '2025-12-31'],
            '现金分红-现金分红比例': [1.20, 1.80],
            '方案进度': ['实施分配', '实施分配'],
        })
        dy, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=6.0)
        assert dps == 0.3
        assert dy == 5.0

    def test_uses_latest_complete_fiscal_year(self):
        """中期披露后应取最近完整财年，而不是截断到当前财年中期。"""
        import pandas as pd
        div_df = pd.DataFrame({
            '报告期': ['2025-12-31', '2026-06-30'],
            '现金分红-现金分红比例': [20.00, 10.13],
            '方案进度': ['实施分配', '实施分配'],
        })
        dy, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=38.0)
        assert dps == 2.0
        assert reason is None

    def test_pending_annual_included_with_implemented_interim(self):
        """本财年年度分红仍是预案阶段，也应与已实施的中期分红合并
        （回归测试：招行案例，正确值=中期1.013+年度1.003=2.016）
        """
        import pandas as pd
        div_df = pd.DataFrame({
            '报告期': ['2024-12-31', '2025-06-30', '2025-12-31'],
            '现金分红-现金分红比例': [20.00, 10.13, 10.03],
            '方案进度': ['实施分配', '实施分配', '董事会决议通过'],
        })
        dy, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=38.0)
        assert dps == 2.016
        assert reason is None

    def test_interim_dividend_does_not_truncate_fiscal_year(self):
        records = [
            ('2023-06-30', 0.5, '实施分配'),
            ('2023-12-31', 2.0, '实施分配'),
            ('2024-06-30', 1.0, '实施分配'),
            ('2024-12-31', 2.8, '实施分配'),
            ('2025-06-30', 2.2, '实施分配'),
            ('2025-12-31', 3.8, '实施分配'),
            ('2026-06-30', 4.2, '董事会决议通过'),
        ]
        div_df = _make_multi_div_df(records)
        dy, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=40.0)
        assert dps == 0.6
        assert dy == 1.5
        assert reason is None

    def test_compute_dps_ttm_uses_latest_365_day_window(self):
        records = [
            ('2025-06-30', 2.2, '实施分配'),
            ('2025-12-31', 3.8, '实施分配'),
            ('2026-06-30', 4.2, '董事会决议通过'),
        ]
        assert fetcher.compute_dps_ttm(_make_multi_div_df(records)) == 0.8

    def test_skipped_annual_dividend_fails_closed_instead_of_returning_stale(self):
        div_df = _make_multi_div_df([
            ('2024-12-31', 20.0, '实施分配'),
            ('2025-12-31', 0.0, '实施分配'),
            ('2026-06-30', 42.0, '董事会决议通过'),
        ])
        dy, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=40.0)
        assert dy is None
        assert dps is None
        assert reason
        assert '2024' in reason

    def test_one_year_gap_keeps_complete_fiscal_year_value(self):
        div_df = _make_multi_div_df([
            ('2025-12-31', 20.0, '实施分配'),
            ('2026-06-30', 42.0, '董事会决议通过'),
        ])
        _, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=40.0)
        assert dps == 2.0
        assert reason is None

    def test_latest_december_period_matches_full_fiscal_year(self):
        div_df = _make_multi_div_df([
            ('2025-06-30', 2.2, '实施分配'),
            ('2025-12-31', 3.8, '实施分配'),
        ])
        dy, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=40.0)
        assert dps == 0.6
        assert fetcher.compute_dps_ttm(div_df) == 0.6
        assert reason is None

    def test_only_interim_dividend_falls_back_to_latest_period_year(self):
        div_df = _make_multi_div_df([
            ('2025-06-30', 2.2, '实施分配'),
            ('2026-06-30', 4.2, '董事会决议通过'),
        ])
        _, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=40.0)
        assert dps == 0.42
        assert reason is None

    def test_skipped_annual_dividend_ttm_remains_available(self):
        div_df = _make_multi_div_df([
            ('2024-12-31', 20.0, '实施分配'),
            ('2025-12-31', 0.0, '实施分配'),
            ('2026-06-30', 4.2, '董事会决议通过'),
        ])
        assert fetcher.compute_dps_ttm(div_df) == 0.42

    def test_fetch_dividend_keeps_ttm_when_main_dividend_is_rejected(self, monkeypatch):
        div_df = _make_multi_div_df([
            ('2024-12-31', 20.0, '实施分配'),
            ('2025-12-31', 0.0, '实施分配'),
            ('2026-06-30', 4.2, '董事会决议通过'),
        ])
        monkeypatch.setattr(fetcher, 'timed_call', lambda *args, **kwargs: div_df)
        results = {}
        null_reasons = {}

        fetcher._fetch_dividend('000001', 40.0, results, null_reasons, 2025)

        assert results['dps_ttm'] == 0.42
        assert 'dividend_yield' not in results
        assert 'dps' not in results
        assert null_reasons['dividend_yield']
        assert null_reasons['dps']

    def test_pending_december_dividend_is_counted(self):
        div_df = _make_multi_div_df([
            ('2025-06-30', 2.2, '实施分配'),
            ('2025-12-31', 3.8, '董事会决议通过'),
            ('2026-06-30', 4.2, '实施分配'),
        ])
        _, dps, reason = fetcher.compute_dividend_yield(div_df, current_price=40.0)
        assert dps == 0.6
        assert reason is None


# ═══════════════════════════════════════════════════════════════════
#  fetcher.py — _extract_fin_fields with missing columns
# ═══════════════════════════════════════════════════════════════════

def test_extract_fin_fields_handles_missing_columns():
    """Missing columns must return None for that field, not raise KeyError."""
    import pandas as pd
    # DataFrame with only some columns
    partial_df = pd.DataFrame({
        '净资产收益率': ['12.00', '13.00', '14.00'],
        # intentionally omit most other columns
    })
    result = fetcher._extract_fin_fields(partial_df)
    assert result['roe_3y_avg'] == 13.0
    # Missing columns should be None, not raise
    assert result['debt_ratio'] is None
    assert result['gross_margin'] is None
    assert result['current_ratio'] is None


def test_extract_fin_fields_empty_dataframe():
    """Empty DataFrame must return all None without crashing."""
    import pandas as pd
    result = fetcher._extract_fin_fields(pd.DataFrame())
    for v in result.values():
        assert v is None
