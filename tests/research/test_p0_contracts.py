"""P0 regression coverage for strict data, quote, scoring and refresh contracts."""
from __future__ import annotations

import json
import sqlite3
import tomllib
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

import pytest

from a_stock_agent_runtime import cache, domain
from a_stock_agent_runtime import fetcher
from tests.helpers import valid_fundamentals_payload


MOAT = '护城河[评级=优；证据="客户留存率连续三年稳定";置信度=高]'
POSITION = '行业地位[评级=优；证据="市占率连续三年第一";置信度=高]'
FRANCHISE = '特许经营稀缺性[评级=优；证据="特许经营权期限明确";置信度=高]'
BRAND = '品牌渠道[评级=优；证据="核心渠道覆盖率提升";置信度=高]'
CYCLE = '周期位置[阶段=上行期；依据="供需改善且盈利扩张"]'
NOW = datetime(2026, 7, 14, 2, 0, tzinfo=timezone.utc)
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    db_file = tmp_path / 'p0.db'
    monkeypatch.setenv('CACHE_DB_PATH', str(db_file))
    monkeypatch.setattr(domain, 'utc_now', lambda: NOW)
    yield str(db_file)


def record_quote(code: str, price: float = 100.0, fetched_at: str | None = None) -> None:
    cache.record_quote_snapshot(
        code, price, '2026-07-14', '10:00:00', 'sina',
        {'sina': {'price': price, 'quote_date': '2026-07-14'}}, False,
        fetched_at=fetched_at or NOW.isoformat(),
    )


def report_for(framework: str) -> str:
    letter = framework[0]
    first = FRANCHISE if letter == 'D' else BRAND if letter == 'E' else MOAT
    cycle = f'\n{CYCLE}' if letter in {'B', 'C', 'D'} else ''
    return f'{first}\n{POSITION}{cycle}'


def run_set_analysis(monkeypatch, code: str, framework: str, score: int | None = 60) -> None:
    record_quote(code)
    monkeypatch.setattr('sys.stdin', StringIO(report_for(framework)))
    args = [code, framework] + ([str(score)] if score is not None else [])
    cache.cmd_set_analysis(args)


def test_schema_migration_adds_quote_tables_and_analysis_columns() -> None:
    with cache.db_session() as conn:
        analysis_columns = {row[1] for row in conn.execute('PRAGMA table_info(analysis_results)')}
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    assert {'quote_price', 'quote_as_of', 'quote_source', 'scoring_status'} <= analysis_columns
    assert {
        'quote_snapshots',
        'market_indicator_snapshots',
        'qualitative_only_securities',
    } <= tables


def test_schema_migration_ledger_skips_done_work_but_applies_new_item(monkeypatch) -> None:
    """Later releases run newly added migrations without reopening old work."""
    with cache.db_session() as conn:
        migration_ids = {
            row[0] for row in conn.execute('SELECT migration_id FROM schema_migrations')
        }
    assert {'001-core-tables', '022-holding-events-inferred'} <= migration_ids

    monkeypatch.setattr(cache, '_SCHEMA_INITIALIZED', False)
    monkeypatch.setattr(cache, '_SCHEMA_INITIALIZED_PATH', '')
    monkeypatch.setattr(
        cache, '_create_core_tables',
        lambda _conn: pytest.fail('durable migration ledger should skip bootstrap'),
    )
    with cache.db_session() as conn:
        assert conn.execute('SELECT 1').fetchone() == (1,)

    monkeypatch.setattr(
        cache,
        'SCHEMA_MIGRATIONS',
        [
            *cache.SCHEMA_MIGRATIONS,
            ('999-test-incremental-column', 'ALTER TABLE stock_fundamentals ADD COLUMN future_field TEXT'),
        ],
    )
    monkeypatch.setattr(cache, '_SCHEMA_INITIALIZED', False)
    monkeypatch.setattr(cache, '_SCHEMA_INITIALIZED_PATH', '')
    with cache.db_session() as conn:
        columns = {row[1] for row in conn.execute('PRAGMA table_info(stock_fundamentals)')}
        new_row = conn.execute(
            'SELECT migration_id FROM schema_migrations WHERE migration_id=?',
            ('999-test-incremental-column',),
        ).fetchone()
    assert 'future_field' in columns
    assert new_row == ('999-test-incremental-column',)


def test_interrupted_migration_batch_is_recovered_by_replay(monkeypatch) -> None:
    """An incremental release whose second migration dies must still self-heal.

    Python's sqlite3 opens an implicit transaction only before DML, so the first
    pending migration's DDL autocommits before any ledger INSERT exists to open a
    transaction.  Its column therefore survives a failure later in the batch while
    its ledger row does not, leaving the schema ahead of the ledger.  Recovery is
    not atomicity -- it is `apply_column_migration` swallowing `duplicate column
    name` when the ledger replays that item on the next run.
    """
    with cache.db_session():  # bring the fixture database to the current release
        pass

    released = list(cache.SCHEMA_MIGRATIONS)
    good = ('998-test-recovery', 'ALTER TABLE stock_fundamentals ADD COLUMN recovery_field TEXT')
    doomed = ('999-test-doomed', 'ALTER TABLE stock_fundamentals ADD COLUMN bad TEXT, NOT SQL')

    monkeypatch.setattr(cache, 'SCHEMA_MIGRATIONS', [*released, good, doomed])
    monkeypatch.setattr(cache, '_SCHEMA_INITIALIZED', False)
    monkeypatch.setattr(cache, '_SCHEMA_INITIALIZED_PATH', '')
    with pytest.raises(sqlite3.OperationalError):
        with cache.db_session():
            pass

    probe = sqlite3.connect(cache.paths.cache_db_path())
    try:
        columns = {row[1] for row in probe.execute('PRAGMA table_info(stock_fundamentals)')}
        recorded = probe.execute(
            'SELECT 1 FROM schema_migrations WHERE migration_id=?', (good[0],)
        ).fetchone()
    finally:
        probe.close()
    assert 'recovery_field' in columns, 'first pending DDL autocommits outside the ledger transaction'
    assert recorded is None, 'its ledger row is rolled back with the rest of the batch'

    # Replay without the doomed item: the duplicate column must not be fatal.
    monkeypatch.setattr(cache, 'SCHEMA_MIGRATIONS', [*released, good])
    monkeypatch.setattr(cache, '_SCHEMA_INITIALIZED', False)
    monkeypatch.setattr(cache, '_SCHEMA_INITIALIZED_PATH', '')
    with cache.db_session() as conn:
        assert conn.execute(
            'SELECT 1 FROM schema_migrations WHERE migration_id=?', (good[0],)
        ).fetchone() == (1,)


def test_project_version_is_single_release_source() -> None:
    pyproject = tomllib.loads((PROJECT_ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    assert pyproject['project']['version'] == '0.1.1'
    for skill in ('a-stock-research', 'a-stock-monitor', 'a-stock-qa'):
        text = (PROJECT_ROOT / 'skills' / skill / 'SKILL.md').read_text(encoding='utf-8')
        assert '\nversion:' not in text


def test_research_routes_product_cycle_analysis_to_grounded_reference() -> None:
    skill_root = PROJECT_ROOT / 'skills' / 'a-stock-research'
    skill = (skill_root / 'SKILL.md').read_text(encoding='utf-8')
    reference = (skill_root / 'references' / 'catalyst-cycle-analysis.md').read_text(
        encoding='utf-8'
    )

    assert 'references/catalyst-cycle-analysis.md' in skill
    assert '不能把客户或平台发布直接视为公司订单' in skill
    for contract in (
        '延续研究也不能沿用早先盘中价格',
        '强制反证',
        'AI 服务器平台出货不等于公司供应关系',
        '条件区间，不是目标价',
    ):
        assert contract in reference


def test_set_analysis_uses_latest_snapshot_without_requesting_another_quote(monkeypatch) -> None:
    run_set_analysis(monkeypatch, '600000', 'A', score=60)

    with cache.db_session() as conn:
        analysis = conn.execute(
            'SELECT quote_price, quote_as_of, quote_source FROM analysis_results WHERE code=?',
            ('600000',),
        ).fetchone()
        snapshot = conn.execute(
            'SELECT source, verification_sources, degraded FROM quote_snapshots WHERE code=?',
            ('600000',),
        ).fetchone()
    assert analysis == (100.0, '2026-07-14T10:00:00', 'sina')
    assert snapshot[0] == 'sina'
    assert json.loads(snapshot[1])['sina']['price'] == 100.0
    assert snapshot[2] == 0


@pytest.mark.parametrize('period', ['2025年报', '2026半年报', '2026Q1', '2026Q2', '2026Q3'])
def test_fundamentals_accepts_supported_data_periods(period: str) -> None:
    cache.set_fundamentals('600000', '测试', '制造', valid_fundamentals_payload({'roe': 12.0}, period))

    assert cache.get_fundamentals('600000')['data_period'] == period


@pytest.mark.parametrize('period', [None, '', '2026', '2026Q4', '2026年中报'])
def test_fundamentals_rejects_missing_or_invalid_data_period(period) -> None:
    payload = valid_fundamentals_payload({'roe': 12.0})
    payload['data_period'] = period

    with pytest.raises(ValueError, match='data_period'):
        cache.set_fundamentals('600000', '测试', '制造', payload)


def test_fundamentals_requires_provenance_and_null_reason_for_every_field() -> None:
    missing_provenance = valid_fundamentals_payload({'roe': 12.0})
    missing_provenance['field_provenance'].pop('roe')
    missing_reason = valid_fundamentals_payload({'gross_margin': None})
    missing_reason['null_reasons'].clear()

    with pytest.raises(ValueError, match='field_provenance'):
        cache.set_fundamentals('1', '测试', '制造', missing_provenance)
    with pytest.raises(ValueError, match='null_reasons'):
        cache.set_fundamentals('2', '测试', '制造', missing_reason)


def test_fetcher_payload_writes_complete_provenance_and_excludes_global_bond() -> None:
    results = {'roe_3y_avg': 12.0, '_quote_as_of': '2026-07-14T10:00:00'}
    fetcher._build_cache_payload('600000', '测试', '制造', results, {}, '2025年报')

    with cache.db_session() as conn:
        stored = json.loads(conn.execute(
            'SELECT data FROM stock_fundamentals WHERE code=?', ('600000',)
        ).fetchone()[0])
    business_fields = set(stored) - {'data_period', 'null_reasons', 'field_provenance'}
    assert 'bond_yield_10y' not in stored
    assert set(stored['field_provenance']) == business_fields
    assert stored['field_provenance']['roe_3y_avg']['status'] == 'ok'
    assert stored['field_provenance']['pb']['status'] == 'missing'
    assert stored['null_reasons']['pb']


@pytest.mark.parametrize(('raw', 'expected'), [
    ('2025', '2025年报'),
    ('2026Q1', '2026Q1'),
    ('2026-06-30', '2026半年报'),
    ('2026-09-30', '2026Q3'),
])
def test_fetcher_derives_data_period_from_actual_report_column(raw, expected) -> None:
    import pandas as pd

    assert fetcher._extract_data_period(pd.DataFrame({'报告期': [raw]})) == expected


def test_fetcher_refuses_fundamentals_write_when_report_period_unknown() -> None:
    with pytest.raises(SystemExit):
        fetcher._build_cache_payload('600000', '测试', '制造', {}, {}, None)

    with cache.db_session() as conn:
        assert conn.execute('SELECT COUNT(*) FROM stock_fundamentals').fetchone()[0] == 0


def test_legacy_naive_timestamp_is_interpreted_as_asia_shanghai(monkeypatch) -> None:
    monkeypatch.setattr(domain, 'utc_now', lambda: datetime(2026, 7, 14, 2, 0, tzinfo=timezone.utc))

    assert cache.is_expired('2026-07-14T09:00:00', 2) is False
    assert cache.is_expired('2026-07-14T07:59:59', 2) is True


def test_market_indicator_24_hour_boundary(monkeypatch) -> None:
    cache.set_market_indicator_snapshot(
        'bond_yield_10y', 1.8, '2026-07-13', 'fixture',
        fetched_at=(NOW - timedelta(hours=24)).isoformat(),
    )
    assert cache.get_market_indicator_snapshot('bond_yield_10y', max_age=timedelta(hours=24)) is not None
    monkeypatch.setattr(domain, 'utc_now', lambda: NOW + timedelta(microseconds=1))
    assert cache.get_market_indicator_snapshot('bond_yield_10y', max_age=timedelta(hours=24)) is None


def test_older_market_indicator_write_cannot_replace_newer_snapshot() -> None:
    cache.set_market_indicator_snapshot(
        'bond_yield_10y', 1.7, '2026-07-14', 'new-source',
        fetched_at=NOW.isoformat(),
    )
    cache.set_market_indicator_snapshot(
        'bond_yield_10y', 9.9, '2026-07-13', 'late-old-source',
        fetched_at=(NOW - timedelta(hours=1)).isoformat(),
    )

    snapshot = cache.get_market_indicator_snapshot('bond_yield_10y')

    assert snapshot['value'] == 1.7
    assert snapshot['source'] == 'new-source'


def test_future_market_and_quote_snapshots_cannot_replace_current_data() -> None:
    future = (NOW + cache.MAX_SNAPSHOT_CLOCK_SKEW + timedelta(microseconds=1)).isoformat()
    cache.set_market_indicator_snapshot(
        'bond_yield_10y', 1.7, '2026-07-14', 'fixture', fetched_at=NOW.isoformat()
    )
    record_quote('FUTURE', fetched_at=NOW.isoformat())

    with pytest.raises(ValueError, match='future'):
        cache.set_market_indicator_snapshot(
            'bond_yield_10y', 9.9, '2026-07-15', 'bad-clock', fetched_at=future
        )
    with pytest.raises(ValueError, match='future'):
        record_quote('FUTURE', 999.0, fetched_at=future)

    assert cache.get_market_indicator_snapshot('bond_yield_10y')['value'] == 1.7
    assert cache.get_latest_quote_snapshot('FUTURE')['price'] == 100.0


@pytest.mark.parametrize('price', [True, 0.0, -1.0, float('nan'), float('inf'), float('-inf')])
def test_quote_snapshot_rejects_non_positive_or_non_finite_prices(price) -> None:
    with pytest.raises(ValueError, match='invalid validated quote snapshot'):
        record_quote('INVALID', price)


def test_quote_snapshot_retention_is_bounded_per_code() -> None:
    for index in range(cache.QUOTE_SNAPSHOT_RETENTION_PER_CODE + 7):
        record_quote(
            'BOUNDED', 100.0 + index,
            fetched_at=(NOW - timedelta(seconds=index)).isoformat(),
        )

    with cache.db_session() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM quote_snapshots WHERE code='BOUNDED'"
        ).fetchone()[0]

    assert count == cache.QUOTE_SNAPSHOT_RETENTION_PER_CODE


@pytest.mark.parametrize('token,expected', [
    ('A', 'A通用'), ('B', 'B银行'), ('C', 'C资源'),
    ('D', 'D公用'), ('E', 'E消费'), ('F', 'F科技'),
])
def test_set_analysis_accepts_all_framework_aliases(monkeypatch, token: str, expected: str) -> None:
    if token == 'D':
        cache.set_market_indicator_snapshot('bond_yield_10y', 1.8, '2026-07-14', 'fixture')
    run_set_analysis(monkeypatch, f'00000{ord(token)}', token)

    with cache.db_session() as conn:
        stored = conn.execute('SELECT framework FROM analysis_results').fetchone()[0]
    assert stored == expected


@pytest.mark.parametrize('args', [
    ['600000', 'unknown'],
    ['600000', 'A', 'B'],
    ['600000', 'A', '60', '61'],
    ['600000', 'A', '12.5'],
    ['600000', 'A', '-1'],
    ['600000', 'A', '81'],
])
def test_set_analysis_rejects_bad_arguments_without_analysis_write(monkeypatch, args) -> None:
    record_quote('600000')
    monkeypatch.setattr('sys.stdin', StringIO(f'{MOAT}\n{POSITION}'))

    with pytest.raises(SystemExit):
        cache.cmd_set_analysis(args)
    with cache.db_session() as conn:
        assert conn.execute('SELECT COUNT(*) FROM analysis_results').fetchone()[0] == 0


@pytest.mark.parametrize('framework', ['A', 'B', 'C', 'D', 'E', 'F'])
def test_each_framework_requires_its_normalized_subjective_categories(monkeypatch, framework: str) -> None:
    record_quote(framework)
    if framework == 'D':
        cache.set_market_indicator_snapshot('bond_yield_10y', 1.8, '2026-07-14', 'fixture')
    monkeypatch.setattr('sys.stdin', StringIO(report_for(framework)))

    cache.cmd_set_analysis([framework, framework, '60'])


@pytest.mark.parametrize('framework', ['B', 'C', 'D'])
def test_cycle_frameworks_reject_missing_cycle_tag(monkeypatch, framework: str) -> None:
    record_quote(framework)
    monkeypatch.setattr('sys.stdin', StringIO(f'{MOAT}\n{POSITION}'))

    with pytest.raises(SystemExit):
        cache.cmd_set_analysis([framework, framework, '60'])


def test_c_valuation_conflict_is_incomplete_and_rejects_a_total_score(monkeypatch) -> None:
    record_quote('601899')
    report = (
        f'{report_for("C")}\n'
        '估值冲突[状态=待核实；PB结论="高于历史中枢"；交叉估值结论="中周期估值不高"]'
    )
    monkeypatch.setattr('sys.stdin', StringIO(report))

    with pytest.raises(SystemExit):
        cache.cmd_set_analysis(['601899', 'C', '48'])
    with cache.db_session() as conn:
        assert conn.execute(
            'SELECT COUNT(*) FROM analysis_results WHERE code=?', ('601899',)
        ).fetchone()[0] == 0

    monkeypatch.setattr('sys.stdin', StringIO(report))
    cache.cmd_set_analysis(['601899', 'C'])
    with pytest.raises(SystemExit):
        cache.cmd_set_score_breakdown([
            '601899',
            json.dumps({
                'fundamentals': {'subtotal': 44},
                'timing': {'subtotal': 4},
                'total': 48,
            }),
        ])
    incomplete_breakdown = {
        'fundamentals': {'subtotal': 44},
        'timing': {'subtotal': None},
        'total': None,
    }
    cache.cmd_set_score_breakdown(['601899', json.dumps(incomplete_breakdown)])
    with cache.db_session() as conn:
        stored = conn.execute(
            'SELECT score, scoring_status, score_breakdown FROM analysis_results WHERE code=?',
            ('601899',),
        ).fetchone()
    assert stored[:2] == (None, 'incomplete')
    assert json.loads(stored[2]) == incomplete_breakdown


def test_d_without_bond_snapshot_is_incomplete_and_accepts_null_timing(monkeypatch) -> None:
    run_set_analysis(monkeypatch, '600900', 'D', score=None)
    breakdown = {
        'fundamentals': {'subtotal': 45},
        'timing': {'subtotal': None},
        'total': None,
    }
    cache.cmd_set_score_breakdown(['600900', json.dumps(breakdown)])

    with cache.db_session() as conn:
        row = conn.execute(
            'SELECT score, scoring_status, score_breakdown FROM analysis_results WHERE code=?',
            ('600900',),
        ).fetchone()
    assert row[0] is None
    assert row[1] == 'incomplete'
    assert json.loads(row[2])['timing']['subtotal'] is None


def test_d_without_bond_snapshot_rejects_complete_score(monkeypatch) -> None:
    record_quote('600901')
    monkeypatch.setattr('sys.stdin', StringIO(report_for('D')))

    with pytest.raises(SystemExit):
        cache.cmd_set_analysis(['600901', 'D', '60'])
    with cache.db_session() as conn:
        assert conn.execute('SELECT COUNT(*) FROM analysis_results').fetchone()[0] == 0


def test_non_d_or_complete_analysis_rejects_null_timing(monkeypatch) -> None:
    run_set_analysis(monkeypatch, '600000', 'A', score=60)
    breakdown = {'fundamentals': {'subtotal': 45}, 'timing': {'subtotal': None}, 'total': None}

    with pytest.raises(SystemExit):
        cache.cmd_set_score_breakdown(['600000', json.dumps(breakdown)])


@pytest.mark.parametrize('industry', ['保险', '证券', '券商'])
def test_unsupported_financial_industry_cannot_bypass_set_analysis(monkeypatch, industry: str) -> None:
    cache.set_fundamentals('601318', '金融公司', industry, valid_fundamentals_payload({'pb': 1.0}))
    record_quote('601318')
    monkeypatch.setattr('sys.stdin', StringIO(f'{MOAT}\n{POSITION}\n{CYCLE}'))

    with pytest.raises(SystemExit):
        cache.cmd_set_analysis(['601318', 'B', '60'])


def test_persisted_qualitative_terminal_blocks_set_analysis_without_fundamentals(
    monkeypatch,
) -> None:
    cache.update_qualitative_only_security('601318', '保险公司', '保险')
    record_quote('601318')
    monkeypatch.setattr('sys.stdin', StringIO(f'{MOAT}\n{POSITION}\n{CYCLE}'))

    with pytest.raises(SystemExit):
        cache.cmd_set_analysis(['601318', 'B', '60'])

    with cache.db_session() as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM analysis_results WHERE code='601318'"
        ).fetchone()[0] == 0


@pytest.mark.parametrize(
    ('new_price', 'hit'),
    [(102.999, True), (103.0, False), (97.001, True), (97.0, False)],
)
def test_analysis_price_invalidation_three_percent_boundary(monkeypatch, capsys, new_price: float, hit: bool) -> None:
    run_set_analysis(monkeypatch, '600000', 'A', score=60)
    record_quote('600000', new_price, fetched_at=(NOW + timedelta(seconds=1)).isoformat())

    cache.cmd_check(['600000'])
    output = capsys.readouterr().out
    assert ('ANALYSIS_HIT' in output) is hit
    assert ('ANALYSIS_PRICE_STALE' in output) is (not hit)


def test_analysis_hit_reports_signed_price_decline(monkeypatch, capsys) -> None:
    run_set_analysis(monkeypatch, '600000', 'A', score=60)
    record_quote('600000', 98.0, fetched_at=(NOW + timedelta(seconds=1)).isoformat())

    cache.cmd_check(['600000'])
    output = capsys.readouterr().out

    assert 'ANALYSIS_HIT' in output
    assert '较分析快照:-2.00%' in output


def test_analysis_without_fresh_quote_cannot_hit(monkeypatch, capsys) -> None:
    run_set_analysis(monkeypatch, '600000', 'A', score=60)
    with cache.db_session() as conn:
        conn.execute("DELETE FROM quote_snapshots WHERE code='600000'")
        conn.commit()

    cache.cmd_check(['600000'])
    output = capsys.readouterr().out

    assert 'ANALYSIS_HIT' not in output
    assert 'ANALYSIS_PRICE_STALE' in output
    assert 'FULL_MISS' in output


def test_unsupported_financial_watchlist_rows_are_terminal_qualitative_only() -> None:
    for code, industry in [('HOLDINS', '保险'), ('PENDBRK', '证券公司')]:
        cache.update_qualitative_only_security(code, '金融公司', industry)
        record_quote(code)
    with cache.db_session() as conn:
        conn.execute(
            '''INSERT INTO holdings
               (code, name, cost_price, buy_date, updated_at, exit_date)
               VALUES ('HOLDINS','保险持仓',10,'2026-01-01',?,NULL)''',
            (NOW.isoformat(),),
        )
        conn.commit()

    rows = {row['code']: row for row in cache.get_watchlist_rows()}

    assert {'HOLDINS', 'PENDBRK'} <= set(rows)
    for code in ('HOLDINS', 'PENDBRK'):
        assert rows[code]['needs_refresh'] is False
        assert rows[code]['refresh_blocked_reason'] == 'unsupported-financial-qualitative-only'


def test_human_facing_fundamentals_timestamp_is_converted_to_cst(capsys) -> None:
    cache.set_fundamentals(
        '600000', '测试', '制造', valid_fundamentals_payload({'roe': 12.0})
    )
    with cache.db_session() as conn:
        conn.execute(
            "UPDATE stock_fundamentals SET updated_at='2026-07-13T04:09:00+00:00' "
            "WHERE code='600000'"
        )
        conn.commit()

    assert cache.get_fundamentals('600000')['_cache_meta']['updated_at'] == '2026-07-13 12:09'
    cache.cmd_check(['600000'])
    output = capsys.readouterr().out
    assert '更新:2026-07-13 12:09' in output
    assert '"updated_at": "2026-07-13 12:09"' in output


def insert_analysis(code: str, created_at: datetime, *, date_value: str = '2026-07-01') -> None:
    with cache.db_session() as conn:
        conn.execute(
            '''INSERT INTO analysis_results
               (code, date, result, created_at, framework, scoring_status)
               VALUES (?,?,?,?,?,'complete')''',
            (code, date_value, 'legacy report', created_at.isoformat(), 'A通用'),
        )
        conn.commit()


def test_watchlist_candidate_boundaries_and_expired_retention() -> None:
    with cache.db_session() as conn:
        conn.execute(
            '''INSERT INTO holdings
               (code, name, cost_price, buy_date, updated_at, exit_date)
               VALUES ('HOLD','持仓',10,'2026-01-01',?,NULL),
                      ('CLOSED','平仓',10,'2026-01-01',?,'2026-02-01')''',
            (NOW.isoformat(), NOW.isoformat()),
        )
        conn.commit()
    insert_analysis('RECENT', NOW - timedelta(days=14))
    insert_analysis('TOO_OLD', NOW - timedelta(days=14, microseconds=1))
    insert_analysis('EXPIRED', NOW - timedelta(days=1))
    payload = valid_fundamentals_payload({'roe': 10})
    cache.set_fundamentals('EXPIRED', '过期基本面', '制造', payload, ttl=1)
    with cache.db_session() as conn:
        conn.execute(
            'UPDATE stock_fundamentals SET updated_at=? WHERE code=?',
            ((NOW - timedelta(hours=2)).isoformat(), 'EXPIRED'),
        )
        conn.commit()
    record_quote('PENDING', fetched_at=(NOW - timedelta(hours=24)).isoformat())
    record_quote('TOO_LATE', fetched_at=(NOW - timedelta(hours=24, microseconds=1)).isoformat())

    rows = cache.get_watchlist_rows()
    by_code = {row['code']: row for row in rows}

    assert set(by_code) == {'HOLD', 'RECENT', 'EXPIRED', 'PENDING'}
    assert by_code['HOLD']['is_holding'] is True
    assert by_code['PENDING']['eligible_reason'] == 'pending-first-analysis'
    assert by_code['EXPIRED']['cache_expired'] is True
    assert by_code['EXPIRED']['needs_refresh'] is True
    assert [row['refresh_priority'] for row in rows] == list(range(1, len(rows) + 1))
    assert rows[0]['code'] == 'HOLD'
    assert rows[1]['code'] == 'PENDING'
