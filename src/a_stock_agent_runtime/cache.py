#!/usr/bin/env python3
"""
A股投研数据缓存管理器
用法：
  cache.py [--confirm-write] <子命令> [参数...]

写入安全边界（全局）：
  --confirm-write 必须位于子命令之前。所有 W1（修改投资状态）子命令缺少该参数时
  返回退出码 3，且不打开写事务；R0/R1 只读子命令不需要该参数。
  W1：set / set-analysis / set-score / set-score-breakdown / set-flag / clear-flag /
      alert-open / alert-pending / alert-resolve / l3-add / l3-update / tier-config /
      tier-update / holding-framework / add-holding / buy-holding / sell-holding /
      record-dividend / corporate-action / close-holding / retro-add / remove-holding /
      update-return / cleanup / clear

子命令：
  cache.py check <代码>                                  # 【推荐】一次性检查分析结论+基本面缓存状态
  cache.py get <代码>                                    # 获取基本面缓存数据
  cache.py set <代码> <名称> <行业> <JSON> [TTL]            # 写入基本面数据（TTL自动按行业推断）
  cache.py get-analysis <代码>                           # 获取今日分析结论缓存
  cache.py set-analysis <代码> <框架> [得分]              # 从stdin写入今日分析结论（框架必填）
  cache.py set-score <代码> <分数>                       # 写入今日综合得分（/80，向后兼容）
  cache.py set-score-breakdown <代码> '<JSON>'           # 写入今日各维度分项得分
  cache.py set-flag <代码> <yellow|red> <原因>            # 记录红黄线预警
  cache.py clear-flag <代码>                             # 清除指定股票所有预警标记
  cache.py alert-open ... / alert-pending ... / alert-resolve ... / alerts <代码>
                                                        # 结构化预警生命周期
  cache.py l3-add ... / l3-update ... / l3-list <代码>   # 结构化 L3 条件
  cache.py tier-config ... / tier-update ...             # 结构化 Tier 状态
  cache.py holding-framework <代码> <A|B|C|D|E|F>        # 显式迁移持仓框架并重算止损线
  cache.py add-holding <代码> <成交价> [股数] [备注] [--fee 金额] [--date YYYY-MM-DD]
                                                        # 新增建仓批次
  cache.py buy-holding <代码> <买入价> <股数> [--fee 金额] [--date YYYY-MM-DD]
                                                        # 加仓并保留最初 buy_date
  cache.py sell-holding <代码> <卖出价> <股数|all> [--fee 金额] [--tax 金额] [--date YYYY-MM-DD]
                                                        # 部分/全部卖出并同步持仓与交易账本
  cache.py record-dividend <代码> <现金总额> [日期]        # 记录持仓现金分红
  cache.py corporate-action <代码> <每股现金分红> <转增比例> [日期]
                                                        # 除权/送转，分离经济成本与规则参考成本
  cache.py close-holding <代码> <卖出价> [日期]           # 记录平仓（保留历史，用于评分验证）
  cache.py update-return <代码> <实际回报%>             # 卖出后记录实际回报（如 15.5 或 -8.2）
  cache.py retro-add <代码> <error_tags> [--note 备注] [--thesis 买入理由] [--gap 框架改进建议]
                                                        # 添加平仓复盘
  cache.py retro-pending                                # 已平仓但尚未复盘的记录
  cache.py retro-stats [框架名]                          # 复盘统计（按框架汇总错误标签）
  cache.py retro-outliers [--loss N]                     # 亏损超阈值且未复盘的记录（默认 10）
  cache.py holdings                                     # 显示在仓持股 + 已平仓历史（含盈亏%）
  cache.py position-return <代码> [当前价]               # 交易事件口径总回报
  cache.py remove-holding <代码>                        # 彻底删除持仓记录（慎用）
  cache.py portfolio-risk                              # 组合风险视图（持仓 + 浮盈 + 框架分布）
  cache.py check-holdings                              # 持仓止损检查：现价对比15%/20%止损线，主动预警
  cache.py watchlist                                    # 显示所有有效缓存股票的关键指标摘要
  cache.py list                                         # 查看所有缓存（含过期）
  cache.py cleanup                                      # 清除所有过期缓存条目
  cache.py clear [代码]                                  # 清除全部或指定股票缓存
  cache.py checklist <代码> <框架A|B|C|D|E|F>             # 打印框架客观指标核对清单（仅核对事实，不计分）

check 命令输出格式（供 SKILL.md 解析）：
  ANALYSIS_HIT   → 今日分析结论已缓存，直接输出结论，终止分析流程
  FUNDAMENTALS_HIT → 基本面数据有缓存，跳过基本面搜索，只查实时行情
  FULL_MISS      → 完全未命中，执行完整分析流程

TTL 按行业自动推断（set 命令未指定 TTL 时）：
  银行/保险/券商/公用事业/水电 → 72h（季报数据稳定）
  消费/白酒/食品/零售         → 12h（情绪驱动，变化快）
  其余行业                   → 24h（默认）
"""

import sqlite3
import json
import math
import sys
import os
import hashlib
import logging
import re
import requests  # noqa: F401 - 兼容外部调用方对 cache.requests 的 monkeypatch
import threading
from collections.abc import Iterator
from datetime import date, datetime, timedelta, time as dtime, timezone
from contextlib import contextmanager
from a_stock_agent_runtime import framework_metadata
from a_stock_agent_runtime import market_quotes
from a_stock_agent_runtime.paths import DEFAULT_CACHE_DB_PATH
from a_stock_agent_runtime.schema_ledger import bootstrap_schema, schema_process_lock
from a_stock_agent_runtime.position_ledger import LifecycleReturn, calculate_lifecycle_return
from a_stock_agent_runtime.paths import ensure_db_parent
from a_stock_lib.contracts import (
    FrameworkKey,
    parse_cycle_stage_tag,
    parse_subjective_assessment_tags,
    required_subjective_categories,
)

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get(
    'CACHE_DB_PATH',
    str(DEFAULT_CACHE_DB_PATH),
)

# ② 行业 → TTL 映射（关键词匹配，越靠前优先级越高）
INDUSTRY_TTL_MAP = [
    # 72h：季报驱动、基本面变化慢
    (['银行', '保险', '券商', '国有大行', '股份制银行', '城商行', '农商行',
      '水电', '公用事业', '电网', '水务', '燃气', '高速'], 72),
    # 12h：情绪/渠道敏感
    (['白酒', '消费', '食品', '零售', '饮料', '乳制品'], 12),
    # 24h：默认（能源/科技/制造等）
]

SCHEMA_MIGRATIONS = [
    ('002-analysis-name', 'ALTER TABLE analysis_results ADD COLUMN name TEXT'),
    ('003-analysis-score', 'ALTER TABLE analysis_results ADD COLUMN score INTEGER'),
    ('004-analysis-flags', 'ALTER TABLE analysis_results ADD COLUMN flags TEXT'),
    ('005-analysis-score-breakdown', 'ALTER TABLE analysis_results ADD COLUMN score_breakdown TEXT'),
    ('006-analysis-return-pct', 'ALTER TABLE analysis_results ADD COLUMN return_pct REAL'),
    ('007-analysis-holding-days', 'ALTER TABLE analysis_results ADD COLUMN holding_days INT'),
    ('008-holdings-exit-price', 'ALTER TABLE holdings ADD COLUMN exit_price REAL'),
    ('009-holdings-exit-date', 'ALTER TABLE holdings ADD COLUMN exit_date TEXT'),
    ('010-analysis-framework', 'ALTER TABLE analysis_results ADD COLUMN framework TEXT'),
    ('011-analysis-quote-price', 'ALTER TABLE analysis_results ADD COLUMN quote_price REAL'),
    ('012-analysis-quote-as-of', 'ALTER TABLE analysis_results ADD COLUMN quote_as_of TEXT'),
    ('013-analysis-quote-source', 'ALTER TABLE analysis_results ADD COLUMN quote_source TEXT'),
    ('014-analysis-scoring-status', "ALTER TABLE analysis_results ADD COLUMN scoring_status TEXT DEFAULT 'complete'"),
    ('015-holdings-framework', 'ALTER TABLE holdings ADD COLUMN framework TEXT'),
    ('016-holdings-initial-shares', 'ALTER TABLE holdings ADD COLUMN initial_shares INTEGER'),
    ('017-holdings-main-entry-date', 'ALTER TABLE holdings ADD COLUMN main_entry_date TEXT'),
    ('018-holdings-main-entry-basis', 'ALTER TABLE holdings ADD COLUMN main_entry_basis REAL'),
    ('019-holdings-additions-since-main', 'ALTER TABLE holdings ADD COLUMN additions_since_main REAL NOT NULL DEFAULT 0'),
    ('020-holdings-reference-cost', 'ALTER TABLE holdings ADD COLUMN reference_cost REAL'),
    ('021-holdings-framework-confident', 'ALTER TABLE holdings ADD COLUMN framework_confident INTEGER NOT NULL DEFAULT 0'),
    ('022-holding-events-inferred', 'ALTER TABLE holding_events ADD COLUMN inferred INTEGER NOT NULL DEFAULT 0'),
]

_SCHEMA_LOCK = threading.Lock()
_SCHEMA_INITIALIZED: bool = False
_SCHEMA_INITIALIZED_PATH: str = ""
_READ_ONLY_REQUEST: bool = False
_CST = timezone(timedelta(hours=8))
_UTC = timezone.utc
_DATA_PERIOD_RE = re.compile(r'^(?:\d{4}年报|\d{4}半年报|\d{4}Q[1-3])$')
_VALUATION_CONFLICT_RE = re.compile(
    r'估值冲突\[状态=待核实；PB结论="[^"]+"；交叉估值结论="[^"]+"\]'
)
_FRAMEWORK_ALIASES = {
    'A': 'A通用', 'A通用': 'A通用',
    'B': 'B银行', 'B银行': 'B银行',
    'C': 'C资源', 'C资源': 'C资源',
    'D': 'D公用', 'D公用': 'D公用',
    'E': 'E消费', 'E消费': 'E消费',
    'F': 'F科技', 'F科技': 'F科技',
}
_UNSUPPORTED_FINANCIAL_KEYWORDS = ('保险', '券商', '证券')
QUOTE_SNAPSHOT_MAX_AGE = timedelta(minutes=30)
QUOTE_SNAPSHOT_RETENTION_PER_CODE = 64
MAX_SNAPSHOT_CLOCK_SKEW = timedelta(seconds=30)
ANALYSIS_PRICE_INVALIDATION_THRESHOLD = 0.03


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(_UTC)


def utc_now_iso() -> str:
    """Return a timezone-aware UTC ISO-8601 timestamp."""
    return utc_now().isoformat()


def cst_today() -> str:
    """Return the current calendar date in Asia/Shanghai."""
    return utc_now().astimezone(_CST).date().isoformat()


def parse_timestamp_utc(value: str) -> datetime:
    """Parse timestamps as UTC; legacy naive values are Asia/Shanghai."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_CST)
    return parsed.astimezone(_UTC)


def format_timestamp_cst(value: str) -> str:
    """Format a stored timestamp for human-facing Asia/Shanghai output."""
    try:
        return parse_timestamp_utc(value).astimezone(_CST).strftime('%Y-%m-%d %H:%M')
    except (TypeError, ValueError):
        return str(value)


def is_unsupported_financial_industry(industry: str | None) -> bool:
    """Return whether the industry is intentionally qualitative-only."""
    return bool(
        industry
        and any(keyword in industry for keyword in _UNSUPPORTED_FINANCIAL_KEYWORDS)
    )


def get_industry_ttl(industry: str) -> int:
    """根据行业名称推断合适的 TTL（小时）"""
    for keywords, ttl in INDUSTRY_TTL_MAP:
        if any(kw in industry for kw in keywords):
            return ttl
    return 24


def infer_framework(industry: str | None) -> tuple[str, bool]:
    """根据行业关键词推断打分框架。

    返回 (framework, confident)：confident=False 表示 industry 缺失/未知，
    此时 framework 只是兜底默认值（'A通用'），不是真实判断——调用方应该
    用这个标志区分"确实判断为通用框架"和"数据缺失导致无法判断"。

    行业关键词数据来源是 framework_metadata.FRAMEWORK_REGISTRY（checklist.py
    加载时填入），这里懒加载 import checklist 保证 registry 已被填充——
    cache.py 模块顶层不能直接 import checklist（checklist.py 顶层反向
    import cache，会形成循环依赖），且 add-holding/portfolio-risk 这两个
    调用入口从不会经过 cmd_checklist() 里那次懒加载，必须在这里自己兜底。
    """
    from a_stock_agent_runtime import checklist  # noqa: F401  延迟导入：触发 FRAMEWORK_REGISTRY 注册
    if not industry or '未知' in industry:
        return 'A通用', False
    if is_unsupported_financial_industry(industry):
        return 'A通用', False
    for metadata in framework_metadata.FRAMEWORK_REGISTRY.values():
        if metadata.portfolio_label and any(k in industry for k in metadata.industry_keywords):
            return metadata.portfolio_label, True
    return 'A通用', True


DEFAULT_STOP_LOSS_PCT = (0.85, 0.80)  # 15% / 20%，A通用/E消费及无法识别行业时的默认值


def get_stop_loss_pct(framework: str) -> tuple[float, float]:
    """根据框架返回 (止损15%系数, 止损20%系数)，未在 registry 里配置专属
    止损系数的框架（A通用/E消费）用 DEFAULT_STOP_LOSS_PCT。"""
    from a_stock_agent_runtime import checklist  # noqa: F401  延迟导入：原因同 infer_framework()
    for metadata in framework_metadata.FRAMEWORK_REGISTRY.values():
        if metadata.portfolio_label == framework and metadata.stop_loss_pct is not None:
            return metadata.stop_loss_pct
    return DEFAULT_STOP_LOSS_PCT


def apply_column_migration(conn: sqlite3.Connection, sql: str) -> None:
    """Add one column, ignoring only the already-applied duplicate-column case.

    Swallowing ``duplicate column name`` is the recovery mechanism, not a
    convenience.  Python's sqlite3 opens an implicit transaction only before DML,
    so this DDL autocommits immediately while the ledger INSERT that records it
    does not.  A batch that dies midway therefore leaves columns on disk that the
    ledger still reports as pending, and the next run replays them; this branch is
    what makes that replay idempotent.  Do not "tidy" it away, and do not add a
    commit here -- the ledger owns commits.
    """
    try:
        conn.execute(sql)
    except sqlite3.OperationalError as exc:
        if 'duplicate column name' in str(exc).lower():
            return
        logger.exception('Schema migration failed: %s', sql)
        raise


def _create_core_tables(conn: sqlite3.Connection) -> None:
    conn.execute('''CREATE TABLE IF NOT EXISTS stock_fundamentals (
        code TEXT PRIMARY KEY,
        name TEXT,
        industry TEXT,
        data JSON,
        updated_at TEXT,
        ttl_hours INTEGER DEFAULT 24
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS analysis_results (
        code TEXT,
        date TEXT,
        name TEXT,
        result TEXT,
        created_at TEXT,
        score INTEGER,
        flags TEXT,
        score_breakdown TEXT,
        return_pct REAL,
        holding_days INT,
        framework TEXT,
        quote_price REAL,
        quote_as_of TEXT,
        quote_source TEXT,
        scoring_status TEXT DEFAULT 'complete',
        PRIMARY KEY (code, date)
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS holdings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        name TEXT,
        cost_price REAL,
        shares INTEGER,
        buy_date TEXT,
        buy_score INTEGER,
        stop_loss_15 REAL,
        stop_loss_20 REAL,
        notes TEXT,
        updated_at TEXT,
        exit_price REAL,
        exit_date TEXT,
        framework TEXT,
        initial_shares INTEGER,
        main_entry_date TEXT,
        main_entry_basis REAL,
        additions_since_main REAL NOT NULL DEFAULT 0,
        reference_cost REAL,
        framework_confident INTEGER NOT NULL DEFAULT 0
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS holding_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        holding_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        event_type TEXT NOT NULL,
        event_date TEXT NOT NULL,
        shares INTEGER,
        price REAL,
        fees REAL NOT NULL DEFAULT 0,
        tax REAL NOT NULL DEFAULT 0,
        cash_amount REAL,
        realized_pnl REAL,
        notes TEXT,
        inferred INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        CHECK (event_type IN ('buy', 'sell', 'dividend', 'adjustment'))
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS holding_l3_conditions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        holding_id INTEGER NOT NULL,
        condition_text TEXT NOT NULL,
        origin_type TEXT NOT NULL DEFAULT 'original',
        status TEXT NOT NULL DEFAULT 'pending',
        evidence TEXT,
        as_of TEXT,
        next_review_date TEXT,
        temporary_exit_rule TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        CHECK (origin_type IN ('original', 'recovered', 'new_monitoring')),
        CHECK (status IN ('pending', 'not_triggered', 'watch', 'triggered'))
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS holding_tier_state (
        holding_id INTEGER PRIMARY KEY,
        tier1_status TEXT NOT NULL DEFAULT 'pending',
        tier2_status TEXT NOT NULL DEFAULT 'pending',
        tier3_status TEXT NOT NULL DEFAULT 'pending',
        exit_path TEXT,
        exit_target_pct REAL,
        exemption_framework TEXT,
        exemption_declared_at TEXT,
        peg_method TEXT,
        updated_at TEXT NOT NULL,
        CHECK (tier1_status IN ('pending', 'completed', 'exempted')),
        CHECK (tier2_status IN ('pending', 'completed')),
        CHECK (tier3_status IN ('pending', 'completed'))
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS holding_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        holding_id INTEGER NOT NULL,
        code TEXT NOT NULL,
        level TEXT NOT NULL,
        category TEXT NOT NULL,
        reason_code TEXT NOT NULL,
        reason TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        evidence TEXT,
        opened_at TEXT NOT NULL,
        review_due TEXT,
        resolved_at TEXT,
        resolution_evidence TEXT,
        updated_at TEXT NOT NULL,
        CHECK (level IN ('yellow', 'red')),
        CHECK (category IN ('holding_deterioration', 'entry_valuation', 'unverified')),
        CHECK (status IN ('active', 'pending', 'resolved'))
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS retro_notes (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        holding_id      INTEGER NOT NULL,
        code            TEXT NOT NULL,
        name            TEXT,
        framework       TEXT,
        buy_date        TEXT,
        exit_date       TEXT,
        buy_score       INTEGER,
        actual_return_pct REAL,
        holding_days    INTEGER,
        error_tags      TEXT,
        thesis_notes    TEXT,
        retro_text      TEXT,
        framework_gap   TEXT,
        created_at      TEXT NOT NULL
    )''')
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_retro_holding ON retro_notes(holding_id)'
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_retro_framework ON retro_notes(framework)'
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_holding_events_holding_date '
        'ON holding_events(holding_id, event_date, id)'
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_l3_holding_status '
        'ON holding_l3_conditions(holding_id, status)'
    )
    conn.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_alert_active_reason '
        "ON holding_alerts(holding_id, reason_code) WHERE status != 'resolved'"
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_alert_code_status '
        'ON holding_alerts(code, status)'
    )
    conn.execute('''CREATE TABLE IF NOT EXISTS quote_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        price REAL NOT NULL,
        quote_date TEXT NOT NULL,
        quote_time TEXT NOT NULL,
        fetched_at TEXT NOT NULL,
        source TEXT NOT NULL,
        verification_sources TEXT NOT NULL,
        degraded INTEGER NOT NULL DEFAULT 0,
        valid INTEGER NOT NULL DEFAULT 1
    )''')
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_quote_snapshots_code_time '
        'ON quote_snapshots(code, fetched_at DESC)'
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_quote_snapshots_code_id '
        'ON quote_snapshots(code, id DESC)'
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_analysis_results_code_created '
        'ON analysis_results(code, created_at DESC)'
    )
    conn.execute(
        'CREATE INDEX IF NOT EXISTS idx_analysis_results_date '
        'ON analysis_results(date)'
    )
    conn.execute('''CREATE TABLE IF NOT EXISTS market_indicator_snapshots (
        indicator_key TEXT PRIMARY KEY,
        value REAL NOT NULL,
        as_of TEXT NOT NULL,
        fetched_at TEXT NOT NULL,
        source TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ok'
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS qualitative_only_securities (
        code TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        industry TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )''')


def _migrate_holdings_autoincrement_id(conn: sqlite3.Connection) -> None:
    holdings_cols = [r[1] for r in conn.execute("PRAGMA table_info(holdings)").fetchall()]
    if 'id' not in holdings_cols:
        conn.execute('DROP TABLE IF EXISTS holdings_new')
        conn.execute('''CREATE TABLE holdings_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            name TEXT, cost_price REAL, shares INTEGER, buy_date TEXT,
            buy_score INTEGER, stop_loss_15 REAL, stop_loss_20 REAL,
            notes TEXT, updated_at TEXT, exit_price REAL, exit_date TEXT,
            framework TEXT, initial_shares INTEGER, main_entry_date TEXT,
            main_entry_basis REAL, additions_since_main REAL NOT NULL DEFAULT 0,
            reference_cost REAL, framework_confident INTEGER NOT NULL DEFAULT 0
        )''')
        conn.execute('''INSERT INTO holdings_new
            (code, name, cost_price, shares, buy_date, buy_score,
             stop_loss_15, stop_loss_20, notes, updated_at, exit_price, exit_date,
             framework, initial_shares, main_entry_date, main_entry_basis,
             additions_since_main, reference_cost, framework_confident)
            SELECT code, name, cost_price, shares, buy_date, buy_score,
                   stop_loss_15, stop_loss_20, notes, updated_at, exit_price, exit_date,
                   framework, initial_shares, main_entry_date, main_entry_basis,
                   additions_since_main, reference_cost, framework_confident
            FROM holdings''')
        conn.execute('DROP TABLE holdings')
        conn.execute('ALTER TABLE holdings_new RENAME TO holdings')
        conn.commit()


def _ensure_holdings_indices(conn: sqlite3.Connection) -> None:
    indices = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name IN ('idx_holdings_code', 'idx_holdings_exit')").fetchall()
    if len(indices) < 2:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_holdings_code ON holdings(code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_holdings_exit ON holdings(exit_date)")
        conn.commit()


def _backfill_holding_metadata(conn: sqlite3.Connection) -> None:
    """Populate durable position metadata for legacy rows without changing later choices."""
    conn.execute(
        'UPDATE holdings SET initial_shares=shares '
        'WHERE initial_shares IS NULL AND shares IS NOT NULL'
    )
    conn.execute(
        '''UPDATE holdings
           SET main_entry_date=COALESCE(main_entry_date, buy_date),
               main_entry_basis=COALESCE(main_entry_basis, cost_price * shares),
               reference_cost=COALESCE(reference_cost, cost_price)
           WHERE shares IS NOT NULL'''
    )
    conn.execute(
        '''UPDATE holdings
           SET framework=(
               SELECT a.framework FROM analysis_results a
               WHERE a.code=holdings.code AND a.framework IS NOT NULL
               ORDER BY a.date DESC LIMIT 1
           )
           WHERE framework IS NULL'''
    )
    conn.execute(
        '''UPDATE holdings
           SET framework_confident=1
           WHERE framework IS NOT NULL
             AND EXISTS (
               SELECT 1 FROM analysis_results a
               WHERE a.code=holdings.code AND a.framework=holdings.framework
             )'''
    )
    legacy_rows = conn.execute(
        '''SELECT h.id, h.code, h.cost_price, h.shares, h.buy_date,
                  h.exit_price, h.exit_date
           FROM holdings h
           WHERE h.shares IS NOT NULL AND h.shares > 0
             AND NOT EXISTS (
               SELECT 1 FROM holding_events e WHERE e.holding_id=h.id
             )'''
    ).fetchall()
    for holding_id, code, cost, shares, buy_date, exit_price, exit_date in legacy_rows:
        created_at = utc_now_iso()
        conn.execute(
            '''INSERT INTO holding_events
               (holding_id, code, event_type, event_date, shares, price,
                notes, inferred, created_at)
               VALUES (?, ?, 'buy', ?, ?, ?, 'legacy_inferred_from_holding', 1, ?)''',
            (holding_id, code, buy_date or cst_today(), shares, cost, created_at),
        )
        if exit_date and exit_price:
            conn.execute(
                '''INSERT INTO holding_events
                   (holding_id, code, event_type, event_date, shares, price,
                    realized_pnl, notes, inferred, created_at)
                   VALUES (?, ?, 'sell', ?, ?, ?, ?,
                           'legacy_inferred_from_holding', 1, ?)''',
                (
                    holding_id, code, exit_date, shares, exit_price,
                    (exit_price - cost) * shares, created_at,
                ),
            )
    conn.commit()


def _backfill_legacy_alerts(conn: sqlite3.Connection) -> None:
    """Carry legacy flag JSON forward as pending/unverified without risk-count inflation."""
    rows = conn.execute(
        '''SELECT h.id, h.code, (
               SELECT latest.flags
               FROM analysis_results latest
               WHERE latest.code=h.code
               ORDER BY latest.date DESC
               LIMIT 1
           )
           FROM holdings h
           WHERE h.exit_date IS NULL'''
    ).fetchall()
    for holding_id, code, raw_flags in rows:
        flags = _safe_json_value(raw_flags, list, [])
        latest_reasons = {
            str(flag.get('reason') or '').strip()
            for flag in flags
            if isinstance(flag, dict) and str(flag.get('reason') or '').strip()
        }
        migrated_alerts = conn.execute(
            '''SELECT id, reason FROM holding_alerts
               WHERE holding_id=? AND category='unverified' AND status='pending'
                 AND reason_code LIKE 'legacy-%'
                 AND evidence='legacy analysis_results.flags; requires classification' ''',
            (holding_id,),
        ).fetchall()
        now_iso = utc_now_iso()
        for alert_id, reason in migrated_alerts:
            if reason not in latest_reasons:
                conn.execute(
                    '''UPDATE holding_alerts
                       SET status='resolved', resolved_at=?,
                           resolution_evidence='superseded by latest analysis',
                           updated_at=?
                       WHERE id=?''',
                    (now_iso, now_iso, alert_id),
                )
        for flag in flags:
            if not isinstance(flag, dict):
                continue
            level = flag.get('level')
            reason = str(flag.get('reason') or '').strip()
            if level not in ('yellow', 'red') or not reason:
                continue
            reason_hash = hashlib.sha256(reason.encode('utf-8')).hexdigest()[:16]
            opened_at = str(flag.get('date') or cst_today())
            conn.execute(
                '''INSERT OR IGNORE INTO holding_alerts
                   (holding_id, code, level, category, reason_code, reason, status,
                    evidence, opened_at, updated_at)
                   VALUES (?, ?, ?, 'unverified', ?, ?, 'pending',
                           'legacy analysis_results.flags; requires classification',
                           ?, ?)''',
                (
                    holding_id, code, level, f"legacy-{reason_hash}", reason,
                    opened_at, now_iso,
                ),
            )
    conn.commit()


def _bootstrap_database_schema(conn: sqlite3.Connection) -> None:
    """Upgrade missing schema items and record each one durably.

    ``_SCHEMA_INITIALIZED`` avoids repeat work within a process.  The migration
    ledger below is the cross-process guard: normal one-command CLI invocations
    must not rerun DDL, legacy backfills or migration probes on every startup.
    """
    migrations = [('001-core-tables', lambda: _create_core_tables(conn))]
    migrations.extend(
        (migration_id, lambda sql=sql: apply_column_migration(conn, sql))
        for migration_id, sql in SCHEMA_MIGRATIONS
    )
    migrations.extend([
        ('023-holdings-autoincrement-id', lambda: _migrate_holdings_autoincrement_id(conn)),
        ('024-holdings-indices', lambda: _ensure_holdings_indices(conn)),
        ('025-holdings-metadata-backfill', lambda: _backfill_holding_metadata(conn)),
        ('026-legacy-alerts-backfill', lambda: _backfill_legacy_alerts(conn)),
    ])
    bootstrap_schema(conn, utc_now_iso(), migrations)


def get_db(timeout: float = 30.0) -> sqlite3.Connection:
    global _SCHEMA_INITIALIZED, _SCHEMA_INITIALIZED_PATH
    if _READ_ONLY_REQUEST:
        path = os.path.abspath(os.path.expanduser(DB_PATH))
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=timeout)
        conn.execute(f"PRAGMA busy_timeout={max(1, round(timeout * 1000))}")
        return conn
    ensure_db_parent(DB_PATH)
    conn = sqlite3.connect(DB_PATH, timeout=timeout)
    conn.execute(f"PRAGMA busy_timeout={max(1, round(timeout * 1000))}")
    if not _SCHEMA_INITIALIZED or _SCHEMA_INITIALIZED_PATH != DB_PATH:
        with _SCHEMA_LOCK:
            if not _SCHEMA_INITIALIZED or _SCHEMA_INITIALIZED_PATH != DB_PATH:
                with schema_process_lock(DB_PATH):
                    _bootstrap_database_schema(conn)
                    _SCHEMA_INITIALIZED = True
                    _SCHEMA_INITIALIZED_PATH = DB_PATH
    return conn


@contextmanager
def db_session(timeout: float = 30.0) -> Iterator[sqlite3.Connection]:
    conn = get_db(timeout)
    try:
        yield conn
    finally:
        conn.close()


def _load_lifecycle_events(conn: sqlite3.Connection, holding_id: int) -> list[tuple]:
    return conn.execute(
        '''SELECT event_type, event_date, shares, price, fees, tax, cash_amount,
                  inferred
           FROM holding_events WHERE holding_id=? ORDER BY event_date, id''',
        (holding_id,),
    ).fetchall()


def _parse_cli_finite_float(
    raw: str, label: str, *, minimum: float | None = None, strict_minimum: bool = False,
) -> float:
    """Parse CLI monetary/rate input and reject NaN/Infinity explicitly."""
    try:
        value = float(raw)
    except (TypeError, ValueError):
        print(f"错误：{label}必须为数字", file=sys.stderr)
        sys.exit(1)
    if not math.isfinite(value):
        print(f"错误：{label}必须是有限数值", file=sys.stderr)
        sys.exit(1)
    if minimum is not None and (value <= minimum if strict_minimum else value < minimum):
        comparator = f'大于{minimum}' if strict_minimum else f'不小于{minimum}'
        print(f"错误：{label}必须{comparator}", file=sys.stderr)
        sys.exit(1)
    return value


def _validate_event_date_not_before(
    conn: sqlite3.Connection, holding_id: int, event_date: str,
) -> None:
    """Disallow backdated lifecycle events that would invert cash-flow order."""
    first_row = conn.execute(
        '''SELECT MIN(event_date) FROM holding_events
           WHERE holding_id=? AND event_type='buy' ''',
        (holding_id,),
    ).fetchone()
    first_buy_date = first_row[0] if first_row else None
    if first_buy_date and event_date < first_buy_date:
        print(f"错误：交易日期不得早于首笔买入日期 {first_buy_date}", file=sys.stderr)
        sys.exit(1)


def validate_fundamentals_payload(data: dict) -> str | None:
    """Validate report period, null reasons and per-field provenance."""
    if not isinstance(data, dict):
        return "基本面数据必须是 JSON 对象"
    period = data.get('data_period')
    if not isinstance(period, str) or _DATA_PERIOD_RE.fullmatch(period) is None:
        return "data_period 必须为 YYYY年报、YYYY半年报或 YYYYQ1—YYYYQ3"
    null_reasons = data.get('null_reasons')
    provenance = data.get('field_provenance')
    if not isinstance(null_reasons, dict):
        return "null_reasons 必须是 JSON 对象"
    if not isinstance(provenance, dict):
        return "field_provenance 必须是 JSON 对象"

    business_fields = set(data) - {'data_period', 'null_reasons', 'field_provenance'}
    for field in sorted(business_fields):
        field_provenance = provenance.get(field)
        if not isinstance(field_provenance, dict):
            return f"字段 {field} 缺少 field_provenance"
        source = field_provenance.get('source')
        as_of = field_provenance.get('as_of')
        status = field_provenance.get('status')
        if not isinstance(source, str) or not source.strip():
            return f"字段 {field} provenance.source 缺失"
        if not isinstance(as_of, str) or not as_of.strip():
            return f"字段 {field} provenance.as_of 缺失"
        if status not in {'ok', 'missing'}:
            return f"字段 {field} provenance.status 必须为 ok 或 missing"
        if data[field] is None:
            if status != 'missing' or not isinstance(null_reasons.get(field), str) or not null_reasons[field].strip():
                return f"缺失字段 {field} 必须同时提供 status=missing 和 null_reasons"
        elif status != 'ok':
            return f"非空字段 {field} 的 provenance.status 必须为 ok"

    unknown_provenance = set(provenance) - business_fields
    if unknown_provenance:
        return f"field_provenance 包含未写入的字段: {', '.join(sorted(unknown_provenance))}"
    unknown_reasons = set(null_reasons) - {field for field in business_fields if data[field] is None}
    if unknown_reasons:
        return f"null_reasons 包含非缺失字段: {', '.join(sorted(unknown_reasons))}"
    return None


def _safe_json_value(raw: str | None, expected_type: type, default):
    """Read legacy JSON without letting one corrupt row break batch commands."""
    if not raw:
        return default
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        logger.warning("Ignoring malformed cached JSON value")
        return default
    if not isinstance(value, expected_type):
        logger.warning("Ignoring cached JSON value with unexpected type")
        return default
    return value


def record_quote_snapshot(
    code: str,
    price: float,
    quote_date: str,
    quote_time: str,
    source: str,
    verification_sources: dict,
    degraded: bool,
    *,
    fetched_at: str | None = None,
) -> None:
    """Persist one already-validated realtime quote snapshot."""
    if (
        not code
        or isinstance(price, bool)
        or not isinstance(price, (int, float))
        or not math.isfinite(float(price))
        or price <= 0
        or not source
        or not isinstance(verification_sources, dict)
        or source not in verification_sources
        or not isinstance(degraded, bool)
    ):
        raise ValueError("invalid validated quote snapshot")
    date.fromisoformat(quote_date)
    dtime.fromisoformat(quote_time)
    fetched_at_dt = parse_timestamp_utc(fetched_at or utc_now_iso())
    if fetched_at_dt - utc_now() > MAX_SNAPSHOT_CLOCK_SKEW:
        raise ValueError("quote snapshot fetched_at is in the future")
    fetched_at_value = fetched_at_dt.isoformat()
    with db_session() as conn:
        conn.execute(
            '''INSERT INTO quote_snapshots
               (code, price, quote_date, quote_time, fetched_at, source,
                verification_sources, degraded, valid)
               VALUES (?,?,?,?,?,?,?,?,1)''',
            (
                code, price, quote_date, quote_time, fetched_at_value, source,
                json.dumps(verification_sources, ensure_ascii=False), int(degraded),
            ),
        )
        conn.execute(
            '''DELETE FROM quote_snapshots
               WHERE code=?
                 AND id NOT IN (
                     SELECT id FROM quote_snapshots
                     WHERE code=?
                     ORDER BY fetched_at DESC, id DESC
                     LIMIT ?
                 )''',
            (code, code, QUOTE_SNAPSHOT_RETENTION_PER_CODE),
        )
        conn.commit()


def get_latest_quote_snapshot(
    code: str,
    *,
    max_age: timedelta | None = None,
) -> dict | None:
    """Return the latest valid quote snapshot, optionally bounded by age."""
    if max_age is not None and max_age < timedelta(0):
        raise ValueError("max_age must be non-negative")
    with db_session() as conn:
        row = conn.execute(
            '''SELECT price, quote_date, quote_time, fetched_at, source,
                      verification_sources, degraded
               FROM quote_snapshots
               WHERE code=? AND valid=1 ORDER BY fetched_at DESC LIMIT 1''',
            (code,),
        ).fetchone()
    if row is None:
        return None
    try:
        age = utc_now() - parse_timestamp_utc(row[3])
    except (TypeError, ValueError):
        logger.warning("Ignoring quote snapshot with malformed fetched_at")
        return None
    if age < -MAX_SNAPSHOT_CLOCK_SKEW:
        return None
    if max_age is not None and age > max_age:
        return None
    return {
        'price': row[0], 'quote_date': row[1], 'quote_time': row[2],
        'fetched_at': row[3], 'source': row[4],
        'verification_sources': _safe_json_value(row[5], dict, {}),
        'degraded': bool(row[6]),
        'quote_as_of': f"{row[1]}T{row[2]}",
    }


def set_market_indicator_snapshot(
    indicator_key: str,
    value: float,
    as_of: str,
    source: str,
    *,
    fetched_at: str | None = None,
) -> None:
    """Persist the latest trusted market-wide indicator snapshot."""
    if (
        not indicator_key
        or isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or value <= 0
        or not as_of
        or not source
    ):
        raise ValueError("invalid market indicator snapshot")
    fetched_at_dt = parse_timestamp_utc(fetched_at or utc_now_iso())
    if fetched_at_dt - utc_now() > MAX_SNAPSHOT_CLOCK_SKEW:
        raise ValueError("market indicator fetched_at is in the future")
    fetched_at_value = fetched_at_dt.isoformat()
    with db_session() as conn:
        conn.execute(
            '''INSERT INTO market_indicator_snapshots
               (indicator_key, value, as_of, fetched_at, source, status)
               VALUES (?,?,?,?,?,'ok')
               ON CONFLICT(indicator_key) DO UPDATE SET
                   value=excluded.value, as_of=excluded.as_of,
                   fetched_at=excluded.fetched_at, source=excluded.source,
                   status='ok'
               WHERE excluded.fetched_at >= market_indicator_snapshots.fetched_at''',
            (indicator_key, value, as_of, fetched_at_value, source),
        )
        conn.commit()


def update_qualitative_only_security(code: str, name: str, industry: str | None) -> None:
    """Persist or clear the terminal qualitative-only routing decision."""
    if not industry or '未知' in industry:
        return
    with db_session() as conn:
        if is_unsupported_financial_industry(industry):
            conn.execute(
                '''INSERT INTO qualitative_only_securities
                   (code, name, industry, updated_at) VALUES (?,?,?,?)
                   ON CONFLICT(code) DO UPDATE SET
                       name=excluded.name, industry=excluded.industry,
                       updated_at=excluded.updated_at''',
                (code, name, industry, utc_now_iso()),
            )
        else:
            conn.execute(
                'DELETE FROM qualitative_only_securities WHERE code=?', (code,)
            )
        conn.commit()


def get_market_indicator_snapshot(
    indicator_key: str,
    *,
    max_age: timedelta | None = None,
) -> dict | None:
    """Return a source-complete market indicator within the requested age."""
    if max_age is not None and max_age < timedelta(0):
        raise ValueError("max_age must be non-negative")
    with db_session() as conn:
        row = conn.execute(
            '''SELECT value, as_of, fetched_at, source, status
               FROM market_indicator_snapshots WHERE indicator_key=?''',
            (indicator_key,),
        ).fetchone()
    if row is None or row[4] != 'ok' or not row[3]:
        return None
    try:
        age = utc_now() - parse_timestamp_utc(row[2])
    except (TypeError, ValueError):
        logger.warning("Ignoring market indicator with malformed fetched_at")
        return None
    if age < -MAX_SNAPSHOT_CLOCK_SKEW:
        return None
    if max_age is not None and age > max_age:
        return None
    return {'value': row[0], 'as_of': row[1], 'fetched_at': row[2], 'source': row[3], 'status': row[4]}


def _add_market_indicators(data: dict) -> dict:
    """Expose fresh global indicators without storing them per stock."""
    result = dict(data)
    snapshot = get_market_indicator_snapshot('bond_yield_10y', max_age=timedelta(hours=24))
    if snapshot is not None:
        result['bond_yield_10y'] = snapshot['value']
        result.setdefault('market_indicator_provenance', {})['bond_yield_10y'] = snapshot
    return result


def get_fundamentals(code: str) -> dict | None:
    """获取基本面缓存。未命中或过期返回 None；命中返回含 _cache_meta 的 dict。"""
    with db_session() as conn:
        row = conn.execute(
            'SELECT name, industry, data, updated_at, ttl_hours FROM stock_fundamentals WHERE code=?',
            (code,)
        ).fetchone()
    if not row:
        return None
    name, industry, data, updated_at, ttl_hours = row
    if is_expired(updated_at, ttl_hours):
        return None
    result = _add_market_indicators(json.loads(data))
    result['_cache_meta'] = {
        'code': code, 'name': name, 'industry': industry,
        'updated_at': format_timestamp_cst(updated_at), 'ttl_hours': ttl_hours
    }
    return result


def set_fundamentals(code: str, name: str, industry: str,
                     data_dict: dict, ttl: int | None = None) -> str:
    """写入基本面缓存，ttl=None 时按行业自动推断。返回状态消息。"""
    validation_error = validate_fundamentals_payload(data_dict)
    if validation_error:
        raise ValueError(validation_error)
    ttl_hours = ttl if ttl is not None else get_industry_ttl(industry)
    with db_session() as conn:
        conn.execute(
            '''INSERT OR REPLACE INTO stock_fundamentals
               (code, name, industry, data, updated_at, ttl_hours)
               VALUES (?,?,?,?,?,?)''',
            (code, name, industry, json.dumps(data_dict, ensure_ascii=False),
             utc_now_iso(), ttl_hours)
        )
        conn.commit()
    return f"已缓存 {name}({code}) 行业:{industry} TTL:{ttl_hours}h"


def list_codes() -> list[str]:
    """返回所有基本面缓存中的股票代码（含过期），按更新时间倒序。"""
    with db_session() as conn:
        rows = conn.execute(
            'SELECT code FROM stock_fundamentals ORDER BY updated_at DESC'
        ).fetchall()
    return [r[0] for r in rows]


_orig_fetch_current_price = market_quotes.fetch_current_price
fetch_current_price = _orig_fetch_current_price
_sina_query_prefix = market_quotes.sina_query_prefix
_parse_sina_quote_line = market_quotes.parse_sina_quote_line
_fetch_sina_batch_quotes = market_quotes.fetch_sina_batch_quotes


def fetch_current_prices(codes: list[str]) -> dict[str, float | None]:
    """批量实时查询多只股票当前价（价格-only，向后兼容既有调用方/测试）。"""
    # 兼容已有的 mock_current_price 单元测试
    if fetch_current_price is not _orig_fetch_current_price:
        return {code: fetch_current_price(code) for code in codes}

    if not codes:
        return {}

    raw = _fetch_sina_batch_quotes(codes)
    return {code: (v[0] if v is not None else None) for code, v in raw.items()}


PriceQuote = market_quotes.PriceQuote


def _orig_fetch_current_price_quote(code: str) -> PriceQuote | None:
    """真实查询单只股票行情（含日期/时间）的底层实现。"""
    quotes = _fetch_sina_batch_quotes([code])
    raw = quotes.get(code)
    if raw is None:
        return None
    price, quote_date, quote_time = raw
    return PriceQuote(price=price, quote_date=quote_date, quote_time=quote_time)


# 默认指向原始的单股查询函数（支持 monkeypatch，用于需要精确控制 quote_date 的测试）
fetch_current_price_quote = _orig_fetch_current_price_quote


def fetch_current_price_quotes(codes: list[str]) -> dict[str, PriceQuote | None]:
    """批量查询多只股票行情（含日期/时间），供 check-holdings 等新鲜度校验场景使用。"""
    if fetch_current_price_quote is not _orig_fetch_current_price_quote:
        return {code: fetch_current_price_quote(code) for code in codes}

    if fetch_current_price is not _orig_fetch_current_price:
        # 只 mock 了价格、没有日期信息的既有测试路径：quote_date=None 会让
        # 调用方落回"新鲜度未知"分支，保持这些测试改动前的行为不变。
        result: dict[str, PriceQuote | None] = {}
        for code in codes:
            p = fetch_current_price(code)
            result[code] = PriceQuote(price=p, quote_date=None, quote_time=None) if p is not None else None
        return result

    if not codes:
        return {}

    raw = _fetch_sina_batch_quotes(codes)
    return {
        code: (PriceQuote(price=v[0], quote_date=v[1], quote_time=v[2]) if v is not None else None)
        for code, v in raw.items()
    }


def is_expired(updated_at_str: str, ttl_hours: int) -> bool:
    try:
        return (
            utc_now() - parse_timestamp_utc(updated_at_str)
            > timedelta(hours=ttl_hours)
        )
    except (TypeError, ValueError):
        return True


def cmd_check(args: list[str]) -> None:
    """一次性检查分析结论+基本面缓存，输出状态码+内容"""
    if len(args) < 1:
        print("FULL_MISS")
        return
    code = args[0]
    today = cst_today()

    # 优先检查今日分析结论
    with db_session() as conn:
        analysis_row = conn.execute(
            '''SELECT result, created_at, name, quote_price
               FROM analysis_results WHERE code=? AND date=?''',
            (code, today)
        ).fetchone()
        if analysis_row:
            result, created_at, name, analysis_quote = analysis_row
            latest_quote = get_latest_quote_snapshot(
                code, max_age=QUOTE_SNAPSHOT_MAX_AGE
            )
            signed_deviation = None
            absolute_deviation = None
            if latest_quote is not None and analysis_quote:
                signed_deviation = (latest_quote['price'] - analysis_quote) / analysis_quote
                absolute_deviation = abs(signed_deviation)
            if latest_quote is None or not analysis_quote:
                print(
                    f"ANALYSIS_PRICE_STALE {code} 缺少新鲜行情或分析价格快照，需要重新分析"
                )
            elif (
                absolute_deviation is not None
                and signed_deviation is not None
                and absolute_deviation < ANALYSIS_PRICE_INVALIDATION_THRESHOLD
            ):
                name_str = f"({name})" if name else ""
                quote_note = (
                    f" 最新报价:{latest_quote['price']:.3f}({latest_quote['source']})"
                    f" 较分析快照:{signed_deviation * 100:+.2f}%"
                )
                print(f"ANALYSIS_HIT {code}{name_str} [{format_timestamp_cst(created_at)}]{quote_note}")
                print(result)
                return
            else:
                assert absolute_deviation is not None
                print(
                    f"ANALYSIS_PRICE_STALE {code} 最新报价较分析快照偏离"
                    f"{absolute_deviation * 100:.2f}%（阈值3.00%），需要重新分析"
                )

        # 再检查基本面缓存
        fund_row = conn.execute(
            'SELECT name, industry, data, updated_at, ttl_hours FROM stock_fundamentals WHERE code=?',
            (code,)
        ).fetchone()

    if fund_row:
        name, industry, data, updated_at, ttl_hours = fund_row
        if not is_expired(updated_at, ttl_hours):
            result = _add_market_indicators(json.loads(data))
            result['_cache_meta'] = {
                'code': code, 'name': name, 'industry': industry,
                'updated_at': format_timestamp_cst(updated_at), 'ttl_hours': ttl_hours
            }
            print(f"FUNDAMENTALS_HIT {code}({name}) [{industry}] 更新:{format_timestamp_cst(updated_at)}")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

    print("FULL_MISS")


def cmd_get(args: list[str]) -> None:
    """获取基本面缓存，未命中或过期返回 CACHE_MISS"""
    if len(args) < 1:
        print("CACHE_MISS")
        return
    code = args[0]
    with db_session() as conn:
        row = conn.execute(
            'SELECT name, industry, data, updated_at, ttl_hours FROM stock_fundamentals WHERE code=?',
            (code,)
        ).fetchone()
    if not row:
        print("CACHE_MISS")
        return
    name, industry, data, updated_at, ttl_hours = row
    if is_expired(updated_at, ttl_hours):
        print("CACHE_MISS")
        return
    result = _add_market_indicators(json.loads(data))
    result['_cache_meta'] = {
        'code': code, 'name': name, 'industry': industry,
        'updated_at': format_timestamp_cst(updated_at), 'ttl_hours': ttl_hours
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_set(args: list[str]) -> None:
    """② 写入基本面数据。TTL 未指定时按行业自动推断。"""
    if len(args) < 4:
        print("错误：需要参数 <代码> <名称> <行业> <JSON数据> [TTL]", file=sys.stderr)
        sys.exit(1)
    code, name, industry, data_str = args[0], args[1], args[2], args[3]
    # TTL：显式指定 > 行业推断
    ttl_hours = int(args[4]) if len(args) > 4 else get_industry_ttl(industry)
    try:
        data = json.loads(data_str)
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}", file=sys.stderr)
        sys.exit(1)
    validation_error = validate_fundamentals_payload(data)
    if validation_error:
        print(f"基本面数据校验错误: {validation_error}", file=sys.stderr)
        sys.exit(1)
    with db_session() as conn:
        conn.execute(
            '''INSERT OR REPLACE INTO stock_fundamentals
               (code, name, industry, data, updated_at, ttl_hours)
               VALUES (?,?,?,?,?,?)''',
            (code, name, industry, json.dumps(data, ensure_ascii=False),
             utc_now_iso(), ttl_hours)
        )
        conn.commit()
    print(f"已缓存 {name}({code}) 行业:{industry} TTL:{ttl_hours}h")


def cmd_get_analysis(args: list[str]) -> None:
    """获取今日分析结论缓存，未命中返回 CACHE_MISS"""
    if len(args) < 1:
        print("CACHE_MISS")
        return
    code = args[0]
    today = cst_today()
    with db_session() as conn:
        row = conn.execute(
            'SELECT result, created_at FROM analysis_results WHERE code=? AND date=?',
            (code, today)
        ).fetchone()
    if not row:
        print("CACHE_MISS")
        return
    result, created_at = row
    print(f"[缓存命中 {format_timestamp_cst(created_at)}]\n{result}")


def _framework_tokens() -> set[str]:
    """Return accepted short and full framework tokens."""
    return set(_FRAMEWORK_ALIASES)


def _parse_set_analysis_args(args: list[str]) -> tuple[str, int | None, str]:
    """Strictly parse framework and optional score without silent ignores."""
    if not args:
        print("错误：需要参数 <代码> <框架> [得分]", file=sys.stderr)
        sys.exit(1)
    code = args[0]
    score: int | None = None
    framework: str | None = None
    for token in args[1:]:
        if token in _FRAMEWORK_ALIASES:
            normalized = _FRAMEWORK_ALIASES[token]
            if framework is not None:
                message = "冲突框架" if normalized != framework else "重复框架"
                print(f"错误：{message}参数 {token}", file=sys.stderr)
                sys.exit(1)
            framework = normalized
            continue
        if re.fullmatch(r'-?\d+', token):
            if score is not None:
                print("错误：重复得分参数", file=sys.stderr)
                sys.exit(1)
            score = int(token)
            continue
        print(f"错误：未知参数 {token}", file=sys.stderr)
        sys.exit(1)
    if framework is None:
        print("错误：set-analysis 必须显式提供框架 A—F", file=sys.stderr)
        sys.exit(1)
    if score is not None and not 0 <= score <= 80:
        print("错误：得分必须为 0—80 的整数", file=sys.stderr)
        sys.exit(1)
    return code, score, framework


def _lookup_cached_stock_name(conn: sqlite3.Connection, code: str) -> str | None:
    row = conn.execute(
        'SELECT name FROM stock_fundamentals WHERE code=?', (code,)
    ).fetchone()
    return row[0] if row else None


def _read_validated_analysis_stdin(framework: str) -> str:
    result = sys.stdin.read().strip()
    if not result:
        print("错误：stdin为空", file=sys.stderr)
        sys.exit(1)
    assessments = parse_subjective_assessment_tags(result)
    actual_categories = {assessment.category for assessment in assessments}
    required_categories = required_subjective_categories(FrameworkKey(framework[0]))
    missing = required_categories - actual_categories
    if missing:
        labels = '、'.join(sorted(category.value for category in missing))
        print(f"错误：{framework}报告缺少必需主观标签：{labels}，拒绝写入缓存。", file=sys.stderr)
        print('格式要求：<类别>[评级=<优|格>；证据="<证据1>";"<证据2>";置信度=<高|中|低>]。', file=sys.stderr)
        sys.exit(1)
    return result


def _validate_cycle_stage_for_framework(result: str, framework: str) -> None:
    """C/B/D框架均fail-closed（2026-07-01：用户明确选择跳过观察期，B/D与C同步切换）；
    A/E/F框架不校验（周期判断对它们是可选项）。
    """
    # framework 传入的是 portfolio_label 全称（如 "C资源"/"B银行"/"D公用"），
    # 不是裸字母，取首字符判断框架类型（与 checklist.py 的裸字母约定不同）。
    letter = framework[0].upper()
    if letter not in ('B', 'C', 'D'):
        return
    assessment = parse_cycle_stage_tag(result)
    if assessment is not None:
        return
    print(f"错误：{framework}框架报告中未找到有效的周期位置结构化标签，拒绝写入缓存。", file=sys.stderr)
    print('格式要求：周期位置[阶段=<上行期|顶部区|下行期|底部区>；依据="<依据文本>"]，依据文本须用ASCII双引号。', file=sys.stderr)
    sys.exit(1)


def cmd_set_analysis(args: list[str]) -> None:
    """从stdin读取分析结论并缓存（当日有效）。

    用法：
      a-stock-cache set-analysis <代码> <框架> [得分] << 'EOF'
      <分析文本>
      EOF

    参数：
      <代码>   股票代码（必填）
      <框架>   打分框架（必填），接受 A—F 简称或 A通用/B银行/C资源/D公用/E消费/F科技。
               持久化下来供 add-holding/portfolio-risk 直接复用，
               不用再靠 industry 关键词反推（反推在 industry 缺失/未知时会失真）。
      [得分]   综合得分整数（可选）。若提供，result 与 score 一并写入，
               无需再单独调用 set-score。若不提供，score 保持 NULL。
      框架和得分的相对顺序不重要，按token形态严格识别；未知或重复参数会拒绝写入。
    """
    code, score, framework = _parse_set_analysis_args(args)
    quote = get_latest_quote_snapshot(code, max_age=QUOTE_SNAPSHOT_MAX_AGE)
    if quote is None:
        print("错误：没有 fetcher 刚写入的有效行情快照，拒绝写入分析", file=sys.stderr)
        sys.exit(1)
    with db_session() as conn_tmp:
        name = _lookup_cached_stock_name(conn_tmp, code)
        industry_row = conn_tmp.execute(
            'SELECT industry FROM stock_fundamentals WHERE code=?', (code,)
        ).fetchone()
        qualitative_row = conn_tmp.execute(
            '''SELECT industry FROM qualitative_only_securities
               WHERE code=?''',
            (code,),
        ).fetchone()
    industry = industry_row[0] if industry_row else None
    if qualitative_row is not None or is_unsupported_financial_industry(industry):
        print("错误：保险/券商/证券不适用当前量化框架，不允许写入 set-analysis", file=sys.stderr)
        sys.exit(1)
    result = _read_validated_analysis_stdin(framework)
    _validate_cycle_stage_for_framework(result, framework)
    today = cst_today()
    scoring_status = 'complete'
    valuation_conflict = framework == 'C资源' and _VALUATION_CONFLICT_RE.search(result)
    if valuation_conflict:
        scoring_status = 'incomplete'
        if score is not None:
            print("错误：C资源估值冲突待核实时不得写入完整总分", file=sys.stderr)
            sys.exit(1)
    elif framework == 'D公用' and get_market_indicator_snapshot(
        'bond_yield_10y', max_age=timedelta(hours=24)
    ) is None:
        scoring_status = 'incomplete'
        if score is not None:
            print("错误：D公用缺少可信国债收益率时不得写入完整总分", file=sys.stderr)
            sys.exit(1)
    with db_session() as conn:
        existing = conn.execute(
            '''SELECT score, score_breakdown FROM analysis_results
               WHERE code=? AND date=?''',
            (code, today),
        ).fetchone()
        effective_score = (
            None if scoring_status == 'incomplete'
            else (score if score is not None else (existing[0] if existing else None))
        )
        clear_stale_breakdown = bool(existing and existing[1]) and not _score_breakdown_matches_analysis(
            existing[1], framework=framework, scoring_status=scoring_status,
            score=effective_score,
        )
        conn.execute(
            '''INSERT INTO analysis_results
               (code, date, name, result, created_at, score, framework,
                quote_price, quote_as_of, quote_source, scoring_status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(code, date) DO UPDATE SET
                   name = excluded.name,
                   result = excluded.result,
                   created_at = excluded.created_at,
                   score = CASE
                       WHEN excluded.scoring_status = 'incomplete' THEN NULL
                       ELSE COALESCE(excluded.score, analysis_results.score)
                   END,
                   framework = excluded.framework,
                   quote_price = excluded.quote_price,
                   quote_as_of = excluded.quote_as_of,
                   quote_source = excluded.quote_source,
                   scoring_status = excluded.scoring_status,
                   score_breakdown = CASE
                       WHEN ? THEN NULL ELSE analysis_results.score_breakdown
                   END''',
            (
                code, today, name, result, utc_now_iso(), score, framework,
                quote['price'], quote['quote_as_of'], quote['source'], scoring_status,
                clear_stale_breakdown,
            )
        )
        conn.commit()
    name_str = f"({name})" if name else ""
    score_str = f" 得分:{score}/80" if score is not None else ""
    fw_str = f" 框架:{framework}" if framework else ""
    status_str = " 评分状态:incomplete" if scoring_status == 'incomplete' else ""
    print(f"分析结论已缓存：{code}{name_str} ({today}){score_str}{fw_str}{status_str}")
    if clear_stale_breakdown:
        print("  ⚠️ 原分项得分与本次分析状态/综合得分不一致，已清除，须重新写入")


def cmd_set_score(args: list[str]) -> None:
    """③ 写入今日综合得分（/80）。需先执行 set-analysis。"""
    if len(args) < 2:
        print("错误：需要参数 <代码> <分数>", file=sys.stderr)
        sys.exit(1)
    code = args[0]
    try:
        score = int(args[1])
    except ValueError:
        print("错误：分数必须为整数", file=sys.stderr)
        sys.exit(1)
    if not 0 <= score <= 80:
        print("错误：分数必须为 0—80 的整数", file=sys.stderr)
        sys.exit(1)
    today = cst_today()
    with db_session() as conn:
        state = conn.execute(
            '''SELECT framework, COALESCE(scoring_status, 'complete'), score_breakdown
               FROM analysis_results WHERE code=? AND date=?''',
            (code, today),
        ).fetchone()
        if state and state[1] == 'incomplete':
            print("错误：评分状态 incomplete 时不得补写完整总分", file=sys.stderr)
            sys.exit(1)
        clear_stale_breakdown = bool(state and state[2]) and not _score_breakdown_matches_analysis(
            state[2], framework=state[0], scoring_status=state[1], score=score,
        )
        updated = conn.execute(
            '''UPDATE analysis_results
               SET score=?, score_breakdown=CASE WHEN ? THEN NULL ELSE score_breakdown END
               WHERE code=? AND date=?''',
            (score, clear_stale_breakdown, code, today)
        ).rowcount
        conn.commit()
    if updated:
        print(f"得分已记录：{code} → {score}/80")
        if clear_stale_breakdown:
            print("  ⚠️ 原分项得分与新综合得分不一致，已清除，须重新写入")
    else:
        print(f"未找到今日分析记录，请先执行 set-analysis（代码：{code}）", file=sys.stderr)
        sys.exit(1)


def _validate_score_breakdown_schema(
    breakdown: dict,
    *,
    framework: str | None = None,
    scoring_status: str = 'complete',
    score: int | None = None,
) -> str | None:
    """校验 score_breakdown 是否符合统一嵌套 schema，返回错误信息（None 表示通过）。

    统一 schema："fundamentals"/"timing" 均为 dict 且含 "subtotal"。
    旧平铺 schema（{"roe": 8, ...}）不再允许写入，仅历史记录保留供展示降级。
    """
    if not isinstance(breakdown, dict):
        return f"score_breakdown 必须是 JSON 对象（dict），而非 {type(breakdown).__name__}"
    if _contains_non_finite_number(breakdown):
        return "score_breakdown 不得包含 NaN 或 Infinity"
    if 'fundamentals' not in breakdown or 'timing' not in breakdown:
        return "score_breakdown 必须包含 'fundamentals' 和 'timing' 两个顶层字段（统一 schema）"
    subtotals: dict[str, float | None] = {}
    for key, maximum in (('fundamentals', 60), ('timing', 20)):
        section = breakdown[key]
        if not isinstance(section, dict) or 'subtotal' not in section:
            return f"score_breakdown['{key}'] 必须是包含 'subtotal' 字段的对象"
        subtotal = section['subtotal']
        allow_null_timing = key == 'timing' and scoring_status == 'incomplete'
        if subtotal is None and allow_null_timing:
            subtotals[key] = None
            continue
        if not isinstance(subtotal, (int, float)) or isinstance(subtotal, bool):
            return f"score_breakdown['{key}'] 的 subtotal 必须是数值（int/float），而非 {type(subtotal).__name__}"
        if not math.isfinite(float(subtotal)):
            return f"score_breakdown['{key}'] 的 subtotal 必须是有限数值"
        if not 0 <= subtotal <= maximum:
            return f"score_breakdown['{key}'] 的 subtotal 必须在 0—{maximum} 之间"
        subtotals[key] = float(subtotal)
    if scoring_status == 'incomplete':
        if breakdown['timing']['subtotal'] is not None:
            return "incomplete 状态的 timing.subtotal 必须为 null"
        if breakdown.get('total') is not None:
            return "incomplete 状态的 total 必须为 null"
        return None
    total = breakdown.get('total')
    if not isinstance(total, (int, float)) or isinstance(total, bool):
        return "完整评分的 score_breakdown 必须包含数值 total"
    if not math.isfinite(float(total)) or not 0 <= total <= 80:
        return "score_breakdown['total'] 必须是 0—80 的有限数值"
    expected_total = (subtotals['fundamentals'] or 0) + (subtotals['timing'] or 0)
    if not math.isclose(float(total), expected_total, abs_tol=1e-9):
        return "score_breakdown['total'] 必须等于基本面与择时 subtotal 之和"
    if score is not None and not math.isclose(float(total), float(score), abs_tol=1e-9):
        return "score_breakdown['total'] 必须与已写入的综合得分一致"
    return None


def _contains_non_finite_number(value: object) -> bool:
    if isinstance(value, dict):
        return any(_contains_non_finite_number(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_non_finite_number(item) for item in value)
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and not math.isfinite(float(value))
    )


def _score_breakdown_matches_analysis(
    raw_breakdown: str | None,
    *,
    framework: str | None,
    scoring_status: str,
    score: int | None,
) -> bool:
    """Return whether a persisted breakdown still satisfies its analysis row."""
    if raw_breakdown is None:
        return True
    try:
        breakdown = json.loads(raw_breakdown)
    except (TypeError, json.JSONDecodeError):
        return False
    return _validate_score_breakdown_schema(
        breakdown, framework=framework, scoring_status=scoring_status, score=score,
    ) is None


def cmd_set_score_breakdown(args: list[str]) -> None:
    """写入今日各维度分项得分（JSON格式，统一嵌套 schema）。需先执行 set-analysis。"""
    if len(args) < 2:
        print("错误：需要参数 <代码> '<JSON>'", file=sys.stderr)
        sys.exit(1)
    code = args[0]
    try:
        breakdown = json.loads(args[1])
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}", file=sys.stderr)
        sys.exit(1)
    today = cst_today()
    with db_session() as conn:
        analysis = conn.execute(
            '''SELECT framework, COALESCE(scoring_status, 'complete'), score
               FROM analysis_results WHERE code=? AND date=?''',
            (code, today),
        ).fetchone()
        if analysis is None:
            print(f"未找到今日分析记录，请先执行 set-analysis（代码：{code}）", file=sys.stderr)
            sys.exit(1)
        schema_error = _validate_score_breakdown_schema(
            breakdown, framework=analysis[0], scoring_status=analysis[1], score=analysis[2]
        )
        if schema_error:
            print(f"错误：{schema_error}", file=sys.stderr)
            sys.exit(1)
        updated = conn.execute(
            'UPDATE analysis_results SET score_breakdown=? WHERE code=? AND date=?',
            (json.dumps(breakdown, ensure_ascii=False), code, today)
        ).rowcount
        conn.commit()
    if updated:
        print(f"分项得分已记录：{code} → {breakdown}")


def _parse_add_holding_args(
    args: list[str],
) -> tuple[str, float, int | None, str | None, int]:
    if len(args) < 2:
        print("错误：需要参数 <代码> <成本价> [股数] [备注]", file=sys.stderr)
        sys.exit(1)
    code = args[0]
    cost_price = _parse_cli_finite_float(args[1], '成本价', minimum=0, strict_minimum=True)
    shares = int(args[2]) if len(args) > 2 and args[2].isdigit() else None
    if shares is not None and shares <= 0:
        print("错误：股数必须大于0", file=sys.stderr)
        sys.exit(1)
    if shares is not None:
        if len(args) > 3 and not args[3].startswith('--'):
            notes = args[3]
            option_start = 4
        else:
            notes = None
            option_start = 3
    else:
        notes = args[2] if len(args) > 2 and not args[2].startswith('--') else None
        option_start = 3 if notes is not None else 2
    return code, cost_price, shares, notes, option_start


def _a_share_board(code: str) -> tuple[str, int]:
    """Return (board, minimum/integer-lot reference) for executable sizing."""
    if code.startswith('688'):
        return 'STAR', 200
    if code.startswith(('4', '8', '920')):
        return 'BSE', 100
    return 'MAIN', 100


def _validate_buy_quantity(code: str, shares: int) -> str | None:
    board, lot = _a_share_board(code)
    if board == 'STAR':
        if shares < lot:
            return f"科创板买入申报不得少于{lot}股"
        return None
    if board == 'BSE':
        if shares < lot:
            return f"北交所买入申报不得少于{lot}股"
        return None
    if shares % lot != 0:
        return f"买入申报股数须为{lot}股的整数倍"
    return None


def _validate_sell_quantity(code: str, current_shares: int, sell_shares: int) -> str | None:
    """Validate a sell against board-lot rules while allowing one final odd-lot exit."""
    if sell_shares <= 0:
        return "卖出股数必须大于0"
    if sell_shares > current_shares:
        return f"卖出股数{sell_shares}超过当前持仓{current_shares}"
    if sell_shares == current_shares:
        return None
    board, lot = _a_share_board(code)
    if board == 'STAR':
        if sell_shares < lot:
            return f"科创板非清仓卖出申报不得少于{lot}股"
        return None
    if board == 'BSE':
        if sell_shares < lot:
            return f"北交所非清仓卖出申报不得少于{lot}股"
        return None
    odd_lot = current_shares % lot
    if sell_shares % lot not in ({0, odd_lot} if odd_lot else {0}):
        return (
            f"当前持仓{current_shares}股时，非清仓卖出须为{lot}股整数倍"
            + (f"或一次性包含全部{odd_lot}股零股" if odd_lot else "")
        )
    return None


def _resolve_holding_framework(conn: sqlite3.Connection, code: str) -> tuple[str, bool, int | None, str | None]:
    score_row = conn.execute(
        'SELECT score, name, framework FROM analysis_results WHERE code=? ORDER BY date DESC LIMIT 1',
        (code,)
    ).fetchone()
    buy_score = score_row[0] if score_row else None
    persisted_framework = score_row[2] if score_row else None
    # 查询股票名称 + 行业（仅在没有持久化framework时才需要industry兜底）
    fund_row = conn.execute(
        'SELECT name, industry FROM stock_fundamentals WHERE code=?', (code,)
    ).fetchone()
    name = (fund_row[0] if fund_row else None) or (score_row[1] if score_row and score_row[1] else None)
    industry = fund_row[1] if fund_row else None

    if persisted_framework:
        framework, confident = persisted_framework, True
    else:
        framework, confident = infer_framework(industry)
    return framework, confident, buy_score, name


def cmd_add_holding(args: list[str]) -> None:
    """Add a new holding lot and its baseline event; use buy-holding to add shares."""
    code, trade_price, shares, notes, option_start = _parse_add_holding_args(args)
    fees, tax, buy_date = _parse_trade_options(args, option_start)
    if tax:
        print("错误：建仓买入不接受 --tax，请仅记录实际买入费用 --fee", file=sys.stderr)
        sys.exit(1)
    if shares is not None:
        quantity_error = _validate_buy_quantity(code, shares)
        if quantity_error:
            print(f"错误：{quantity_error}", file=sys.stderr)
            sys.exit(1)

    if fees and shares is None:
        print("错误：记录买入费用时必须提供股数", file=sys.stderr)
        sys.exit(1)
    economic_cost = (
        (trade_price * shares + fees) / shares if shares is not None else trade_price
    )

    # 查询今日分析得分 + 框架（决定止损系数）。优先用 set-analysis 时已经
    # 显式决定并持久化的 framework，只有从未做过分析的代码才退化到用
    # industry 关键词反推——反推在 industry 缺失/未知时会失真。
    with db_session() as conn:
        conn.execute('BEGIN IMMEDIATE')
        open_count = conn.execute(
            '''SELECT COUNT(*) FROM holdings
               WHERE code=? AND exit_date IS NULL''',
            (code,),
        ).fetchone()[0]
        if open_count:
            conn.rollback()
            print(
                f"错误：{code} 已存在在仓持仓；加仓请使用 buy-holding，"
                "或先平仓后再建仓",
                file=sys.stderr,
            )
            sys.exit(1)
        framework, confident, buy_score, name = _resolve_holding_framework(conn, code)
        sl15_pct, sl20_pct = get_stop_loss_pct(framework)
        stop_loss_15 = round(trade_price * sl15_pct, 3)
        stop_loss_20 = round(trade_price * sl20_pct, 3)

        cursor = conn.execute(
            '''INSERT INTO holdings
               (code, name, cost_price, shares, buy_date, buy_score,
                stop_loss_15, stop_loss_20, notes, updated_at, framework, initial_shares,
                main_entry_date, main_entry_basis, additions_since_main, reference_cost,
                framework_confident)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (code, name, economic_cost, shares, buy_date, buy_score,
             stop_loss_15, stop_loss_20, notes, utc_now_iso(), framework, shares,
             buy_date, economic_cost * shares if shares is not None else None, 0,
             trade_price,
             int(confident))
        )
        holding_id = cursor.lastrowid
        if shares is not None:
            conn.execute(
                '''INSERT INTO holding_events
                   (holding_id, code, event_type, event_date, shares, price, fees, created_at)
                   VALUES (?, ?, 'buy', ?, ?, ?, ?, ?)''',
                (
                    holding_id, code, buy_date, shares, trade_price, fees,
                    utc_now_iso(),
                ),
            )
        conn.execute(
            '''INSERT INTO holding_tier_state (holding_id, updated_at)
               VALUES (?, ?) ON CONFLICT(holding_id) DO NOTHING''',
            (holding_id, utc_now_iso()),
        )
        conn.commit()

    name_str = f"({name})" if name else ""
    shares_str = f" {shares}股" if shares else ""
    score_str = f" 买入得分:{buy_score}/80" if buy_score else ""
    fw_marker = "" if confident else "?(数据缺失，建议核实)"
    print(
        f"持仓已记录：{code}{name_str} 成交:{trade_price}"
        f" 经济成本:{economic_cost:.4f}{shares_str}{score_str}"
    )
    print(f"  框架:{framework}{fw_marker}（系数{sl15_pct}/{sl20_pct}） 止损15%:{stop_loss_15}  止损20%:{stop_loss_20}")


def _print_open_holdings(open_rows: list[tuple]) -> None:
    if open_rows:
        unique_open = len(set(r[1] for r in open_rows))
        lot_str = f"，{len(open_rows)} 笔" if len(open_rows) > unique_open else ""
        print(f"\n{'─'*80}")
        print(f"  在仓持股（{unique_open} 只{lot_str}）")
        print(f"{'─'*80}")
        print(f"  {'股票':<14} {'成本价':>7} {'股数':>6} {'止损15%':>8} {'止损20%':>8} {'得分':>4} {'买入日期':<11} 备注")
        print(f"  {'─'*74}")
        for r in open_rows:
            _, code, name, cost, shares, buy_date, score, sl15, sl20, notes, _, _ = r
            label = f"{name}({code})" if name else code
            shares_str = str(shares) if shares else "─"
            score_str  = str(score) if score else "─"
            notes_str  = notes or "─"
            print(f"  {label:<14} {cost:>7.3f} {shares_str:>6} {sl15:>8.3f} {sl20:>8.3f} {score_str:>4} {buy_date:<11} {notes_str}")


def _print_closed_holdings(
    closed_rows: list[tuple], lifecycle_returns: dict[int, LifecycleReturn],
) -> None:
    if closed_rows:
        print(f"\n{'─'*80}")
        print(f"  已平仓历史（{len(closed_rows)} 只）")
        print(f"{'─'*80}")
        print(f"  {'股票':<14} {'成本价':>7} {'卖出价':>7} {'盈亏%':>7} {'得分':>4} {'买入':>11} {'卖出':>11} 备注")
        print(f"  {'─'*74}")
        for r in closed_rows:
            holding_id, code, name, cost, shares, buy_date, score, _, _, notes, exit_price, exit_date = r
            label      = f"{name}({code})" if name else code
            score_str  = str(score) if score else "─"
            notes_str  = notes or "─"
            lifecycle_return = lifecycle_returns.get(holding_id)
            pnl_str = (
                f"{lifecycle_return.total_return_pct:+.1f}%"
                if lifecycle_return is not None else "账本缺失"
            )
            print(f"  {label:<14} {cost:>7.3f} {exit_price:>7.3f} {pnl_str:>7} {score_str:>4} {buy_date:>11} {exit_date:>11} {notes_str}")

        # 统计：平均盈亏、胜率，帮助验证评分系统有效性
        pnl_list = [item.total_return_pct for item in lifecycle_returns.values()]
        if pnl_list:
            win_rate = round(sum(1 for p in pnl_list if p > 0) / len(pnl_list) * 100)
            avg_pnl  = round(sum(pnl_list) / len(pnl_list), 1)
            print(f"\n  已平仓统计：胜率 {win_rate}% | 平均盈亏 {avg_pnl:+.1f}% | 有效账本 {len(pnl_list)}/{len(closed_rows)} 笔")
        else:
            print(f"\n  已平仓统计：无可核验事件账本（共 {len(closed_rows)} 笔）")


def cmd_holdings(args: list[str] | None = None) -> None:
    """显示持仓列表：在仓持股 + 已平仓历史（含盈亏%，用于验证评分准确性）"""
    with db_session() as conn:
        # Lazy compatibility migration for legacy rows imported after process
        # startup.  It only creates explicitly marked inferred baseline events.
        _backfill_holding_metadata(conn)
        rows = conn.execute(
            '''SELECT id, code, name, cost_price, shares, buy_date, buy_score,
                      stop_loss_15, stop_loss_20, notes, exit_price, exit_date
               FROM holdings ORDER BY exit_date IS NULL DESC, buy_date DESC'''
        ).fetchall()
        lifecycle_returns: dict[int, LifecycleReturn] = {}
        for row in rows:
            holding_id, exit_date = row[0], row[11]
            if exit_date is None:
                continue
            try:
                lifecycle_returns[holding_id] = calculate_lifecycle_return(
                    _load_lifecycle_events(conn, holding_id), 0, end_date=exit_date,
                )
            except ValueError:
                continue

    if not rows:
        print("暂无持仓记录")
        return

    open_rows   = [r for r in rows if r[11] is None]   # exit_date IS NULL
    closed_rows = [r for r in rows if r[11] is not None]

    _print_open_holdings(open_rows)
    _print_closed_holdings(closed_rows, lifecycle_returns)


def _parse_trade_options(args: list[str], start: int) -> tuple[float, float, str]:
    fees = 0.0
    tax = 0.0
    trade_date = cst_today()
    i = start
    while i < len(args):
        if args[i] not in ('--fee', '--tax', '--date') or i + 1 >= len(args):
            print(f"错误：未知或不完整参数 {args[i]}", file=sys.stderr)
            sys.exit(1)
        value = args[i + 1]
        if args[i] == '--date':
            try:
                date.fromisoformat(value)
            except ValueError:
                print("错误：日期必须为 YYYY-MM-DD", file=sys.stderr)
                sys.exit(1)
            trade_date = value
        else:
            label = '费用' if args[i] == '--fee' else '税费'
            amount = _parse_cli_finite_float(value, label, minimum=0)
            if args[i] == '--fee':
                fees = amount
            else:
                tax = amount
        i += 2
    return fees, tax, trade_date


def cmd_buy_holding(args: list[str]) -> None:
    """Add shares to the single open position without resetting its original buy date."""
    if len(args) < 3:
        print(
            "错误：需要参数 <代码> <买入价> <股数> [--fee 金额] [--date YYYY-MM-DD]",
            file=sys.stderr,
        )
        sys.exit(1)
    code = args[0]
    try:
        buy_shares = int(args[2])
    except ValueError:
        print("错误：股数必须为数字", file=sys.stderr)
        sys.exit(1)
    buy_price = _parse_cli_finite_float(args[1], '买入价', minimum=0, strict_minimum=True)
    quantity_error = _validate_buy_quantity(code, buy_shares)
    if quantity_error:
        print(f"错误：{quantity_error}", file=sys.stderr)
        sys.exit(1)
    fees, tax, trade_date = _parse_trade_options(args, 3)
    if tax:
        print("错误：买入事件不接受 --tax，请仅记录实际买入费用 --fee", file=sys.stderr)
        sys.exit(1)
    with db_session() as conn:
        conn.execute('BEGIN IMMEDIATE')
        holding_id, _, framework = _single_open_holding(conn, code)
        _validate_event_date_not_before(conn, holding_id, trade_date)
        row = conn.execute(
            '''SELECT cost_price, shares, stop_loss_15, stop_loss_20,
                      main_entry_date, main_entry_basis, additions_since_main,
                      reference_cost
               FROM holdings WHERE id=?''',
            (holding_id,),
        ).fetchone()
        (
            cost_price, old_shares, _, _, main_date, main_basis, additions,
            reference_cost,
        ) = row
        if old_shares is None or old_shares <= 0:
            conn.rollback()
            print("错误：旧持仓股数缺失，无法计算加权成本", file=sys.stderr)
            sys.exit(1)
        added_cash = buy_price * buy_shares + fees
        added_reference_value = buy_price * buy_shares
        old_book_cost = cost_price * old_shares
        new_shares = old_shares + buy_shares
        new_cost = (old_book_cost + added_cash) / new_shares
        new_reference_cost = (
            (reference_cost or cost_price) * old_shares + added_reference_value
        ) / new_shares
        sl15_pct, sl20_pct = get_stop_loss_pct(framework or 'A通用')
        additions = (additions or 0) + added_cash
        main_basis = main_basis or old_book_cost
        if additions > main_basis * 0.5:
            main_date = trade_date
            main_basis = old_book_cost + added_cash
            additions = 0
        now_iso = utc_now_iso()
        conn.execute(
            '''UPDATE holdings
               SET cost_price=?, shares=?, stop_loss_15=?, stop_loss_20=?,
                   main_entry_date=?, main_entry_basis=?,
                   additions_since_main=?, reference_cost=?, updated_at=?
               WHERE id=?''',
            (
                new_cost, new_shares, round(new_reference_cost * sl15_pct, 3),
                round(new_reference_cost * sl20_pct, 3), main_date, main_basis,
                additions, new_reference_cost, now_iso, holding_id,
            ),
        )
        conn.execute(
            '''INSERT INTO holding_events
               (holding_id, code, event_type, event_date, shares, price, fees, created_at)
               VALUES (?, ?, 'buy', ?, ?, ?, ?, ?)''',
            (holding_id, code, trade_date, buy_shares, buy_price, fees, now_iso),
        )
        conn.commit()
    print(
        f"加仓已记录：{code} +{buy_shares}股 @ {buy_price:.3f} | "
        f"新股数:{new_shares} 新成本:{new_cost:.4f} 最初buy_date保持不变"
    )


def cmd_sell_holding(args: list[str], *, single_lot: bool = False) -> None:
    """Partially or fully sell open lots and record an auditable cash-flow event."""
    if len(args) < 3:
        print(
            "错误：需要参数 <代码> <卖出价> <股数|all> "
            "[--fee 金额] [--tax 金额] [--date YYYY-MM-DD]",
            file=sys.stderr,
        )
        sys.exit(1)
    code = args[0]
    exit_price = _parse_cli_finite_float(args[1], '卖出价', minimum=0, strict_minimum=True)
    requested = args[2].lower()
    if requested != 'all':
        try:
            requested_shares = int(requested)
        except ValueError:
            print("错误：卖出股数必须为正整数或 all", file=sys.stderr)
            sys.exit(1)
    else:
        requested_shares = None
    fees, tax, exit_date = _parse_trade_options(args, 3)

    with db_session() as conn:
        conn.execute('BEGIN IMMEDIATE')
        lot_limit = ' LIMIT 1' if single_lot else ''
        lots = conn.execute(
            '''SELECT id, cost_price, shares, buy_date
               FROM holdings
               WHERE code=? AND exit_date IS NULL
               ORDER BY buy_date ASC, id ASC''' + lot_limit,
            (code,),
        ).fetchall()
        if not lots:
            conn.rollback()
            print(f"错误：未找到 {code} 的在仓记录", file=sys.stderr)
            sys.exit(1)
        if any(row[2] is None or row[2] <= 0 for row in lots):
            conn.rollback()
            print(
                f"错误：{code} 存在未记录股数的旧持仓，须先补全 shares 才能部分卖出",
                file=sys.stderr,
            )
            sys.exit(1)
        current_shares = sum(row[2] for row in lots)
        sell_shares = current_shares if requested_shares is None else requested_shares
        quantity_error = _validate_sell_quantity(code, current_shares, sell_shares)
        if quantity_error:
            conn.rollback()
            print(f"错误：{quantity_error}", file=sys.stderr)
            sys.exit(1)

        remaining = sell_shares
        total_realized = 0.0
        now_iso = utc_now_iso()
        for holding_id, cost_price, lot_shares, buy_date in lots:
            if remaining == 0:
                break
            sold = min(lot_shares, remaining)
            _validate_event_date_not_before(conn, holding_id, exit_date)
            allocated_fee = fees * sold / sell_shares
            allocated_tax = tax * sold / sell_shares
            realized = (exit_price - cost_price) * sold - allocated_fee - allocated_tax
            total_realized += realized
            new_shares = lot_shares - sold
            if new_shares == 0:
                conn.execute(
                    '''UPDATE holdings
                       SET shares=0, exit_price=?, exit_date=?, updated_at=?
                       WHERE id=?''',
                    (exit_price, exit_date, now_iso, holding_id),
                )
            else:
                conn.execute(
                    'UPDATE holdings SET shares=?, updated_at=? WHERE id=?',
                    (new_shares, now_iso, holding_id),
                )
            conn.execute(
                '''INSERT INTO holding_events
                   (holding_id, code, event_type, event_date, shares, price,
                    fees, tax, realized_pnl, created_at)
                   VALUES (?, ?, 'sell', ?, ?, ?, ?, ?, ?, ?)''',
                (
                    holding_id, code, exit_date, sold, exit_price,
                    allocated_fee, allocated_tax, realized, now_iso,
                ),
            )
            remaining -= sold
        conn.commit()

    residual = current_shares - sell_shares
    action = "清仓" if residual == 0 else "部分卖出"
    print(f"{action}已记录：{code} {sell_shares}股 @ {exit_price:.3f}")
    print(
        f"  费用:{fees:.2f} 税费:{tax:.2f} | "
        f"本次已实现盈亏:{total_realized:+.2f}元 | 剩余:{residual}股"
    )


def cmd_record_dividend(args: list[str]) -> None:
    """Record total cash dividend received for the current open position."""
    if len(args) < 2:
        print("错误：需要参数 <代码> <现金总额> [日期]", file=sys.stderr)
        sys.exit(1)
    code = args[0]
    cash_amount = _parse_cli_finite_float(args[1], '现金总额', minimum=0)
    event_date = args[2] if len(args) > 2 else cst_today()
    try:
        date.fromisoformat(event_date)
    except ValueError:
        print("错误：日期必须为 YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)
    with db_session() as conn:
        row = conn.execute(
            '''SELECT id FROM holdings
               WHERE code=? AND exit_date IS NULL
               ORDER BY buy_date ASC, id ASC LIMIT 1''',
            (code,),
        ).fetchone()
        if not row:
            print(f"错误：未找到 {code} 的在仓记录", file=sys.stderr)
            sys.exit(1)
        _validate_event_date_not_before(conn, row[0], event_date)
        conn.execute(
            '''INSERT INTO holding_events
               (holding_id, code, event_type, event_date, cash_amount, created_at)
               VALUES (?, ?, 'dividend', ?, ?, ?)''',
            (row[0], code, event_date, cash_amount, utc_now_iso()),
        )
        conn.commit()
    print(f"现金分红已记录：{code} {cash_amount:.2f}元（{event_date}）")


def cmd_corporate_action(args: list[str]) -> None:
    """Apply cash dividend and stock split/bonus without corrupting economic return."""
    if len(args) < 3:
        print(
            "错误：需要参数 <代码> <每股现金分红> <转增比例> [日期]",
            file=sys.stderr,
        )
        sys.exit(1)
    code = args[0]
    dps = _parse_cli_finite_float(args[1], '分红', minimum=0)
    split_ratio = _parse_cli_finite_float(args[2], '转增比例', minimum=0)
    action_date = args[3] if len(args) > 3 else cst_today()
    try:
        date.fromisoformat(action_date)
    except ValueError:
        print("错误：日期必须为 YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)
    with db_session() as conn:
        conn.execute('BEGIN IMMEDIATE')
        holding_id, _, framework = _single_open_holding(conn, code)
        row = conn.execute(
            '''SELECT cost_price, reference_cost, shares, initial_shares
               FROM holdings WHERE id=?''',
            (holding_id,),
        ).fetchone()
        economic_cost, reference_cost, old_shares, initial_shares = row
        if old_shares is None or old_shares <= 0:
            conn.rollback()
            print("错误：持仓股数缺失，无法执行除权调整", file=sys.stderr)
            sys.exit(1)
        _validate_event_date_not_before(conn, holding_id, action_date)
        multiplier = 1 + split_ratio
        raw_new_shares = old_shares * multiplier
        if not math.isclose(raw_new_shares, round(raw_new_shares), abs_tol=1e-8):
            conn.rollback()
            print("错误：转增后股数不是整数，请使用实际到账股数人工核对", file=sys.stderr)
            sys.exit(1)
        new_shares = round(raw_new_shares)
        new_initial_shares = (
            round(initial_shares * multiplier) if initial_shares is not None else None
        )
        # Economic cost keeps cash dividend as a separate return event; only split
        # changes its per-share denominator. Rule reference cost also adjusts for DPS.
        new_economic_cost = economic_cost / multiplier
        new_reference_cost = ((reference_cost or economic_cost) - dps) / multiplier
        if new_reference_cost <= 0:
            conn.rollback()
            print("错误：调整后的规则参考成本必须大于0", file=sys.stderr)
            sys.exit(1)
        sl15_pct, sl20_pct = get_stop_loss_pct(framework or 'A通用')
        dividend_cash = dps * old_shares
        now_iso = utc_now_iso()
        conn.execute(
            '''UPDATE holdings
               SET cost_price=?, reference_cost=?, shares=?, initial_shares=?,
                   stop_loss_15=?, stop_loss_20=?, updated_at=?
               WHERE id=?''',
            (
                new_economic_cost, new_reference_cost, new_shares,
                new_initial_shares, round(new_reference_cost * sl15_pct, 3),
                round(new_reference_cost * sl20_pct, 3), now_iso, holding_id,
            ),
        )
        if dividend_cash:
            conn.execute(
                '''INSERT INTO holding_events
                   (holding_id, code, event_type, event_date, cash_amount, created_at)
                   VALUES (?, ?, 'dividend', ?, ?, ?)''',
                (holding_id, code, action_date, dividend_cash, now_iso),
            )
        conn.execute(
            '''INSERT INTO holding_events
               (holding_id, code, event_type, event_date, shares, price,
                notes, created_at)
               VALUES (?, ?, 'adjustment', ?, ?, ?, ?, ?)''',
            (
                holding_id, code, action_date, new_shares - old_shares,
                new_reference_cost, f"dps={dps};split_ratio={split_ratio}", now_iso,
            ),
        )
        conn.commit()
    print(
        f"除权调整已记录：{code} {old_shares}→{new_shares}股 | "
        f"经济成本/股:{new_economic_cost:.4f} | 规则参考成本:{new_reference_cost:.4f} "
        f"| 现金分红:{dividend_cash:.2f}元"
    )


def cmd_close_holding(args: list[str]) -> None:
    """Close the oldest open lot; ledger-capable positions use the sell path."""
    if len(args) < 2:
        print("错误：需要参数 <代码> <卖出价> [日期，默认今天]", file=sys.stderr)
        sys.exit(1)
    code = args[0]
    exit_price = _parse_cli_finite_float(args[1], '卖出价', minimum=0, strict_minimum=True)
    exit_date = args[2] if len(args) > 2 else cst_today()
    try:
        date.fromisoformat(exit_date)
    except ValueError:
        print("错误：日期必须为 YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    with db_session() as conn:
        row = conn.execute(
            '''SELECT id, cost_price, name, buy_score, shares, buy_date FROM holdings
               WHERE code=? AND exit_date IS NULL
               ORDER BY buy_date ASC, id ASC LIMIT 1''',
            (code,)
        ).fetchone()
    if not row:
        print(f"错误：未找到 {code} 的在仓记录", file=sys.stderr)
        sys.exit(1)
    _, cost_price, name, buy_score, shares, buy_date = row

    if isinstance(shares, int) and shares > 0:
        # Do not duplicate the state transition: sell-holding owns the normal
        # close transaction and immutable sell event.  Limit it to one FIFO
        # lot so this legacy command keeps its original single-lot semantics.
        cmd_sell_holding(
            [code, str(exit_price), 'all', '--date', exit_date], single_lot=True,
        )
    else:
        # Older price-only positions cannot be reconstructed into a cash-flow
        # ledger.  Keep the historical close capability, but clear shares so a
        # closed row can never be valued as an open position.
        with db_session() as conn:
            conn.execute('BEGIN IMMEDIATE')
            legacy_row = conn.execute(
                '''SELECT id, cost_price, name, buy_score, buy_date FROM holdings
                   WHERE code=? AND exit_date IS NULL AND (shares IS NULL OR shares <= 0)
                   ORDER BY buy_date ASC, id ASC LIMIT 1''',
                (code,),
            ).fetchone()
            if legacy_row is None:
                conn.rollback()
                print(f"错误：未找到 {code} 的在仓记录", file=sys.stderr)
                sys.exit(1)
            lot_id, cost_price, name, buy_score, legacy_buy_date = legacy_row
            if legacy_buy_date and exit_date < legacy_buy_date:
                conn.rollback()
                print(f"错误：卖出日期不得早于买入日期 {legacy_buy_date}", file=sys.stderr)
                sys.exit(1)
            cursor = conn.execute(
                '''UPDATE holdings SET shares=0, exit_price=?, exit_date=?, updated_at=?
                   WHERE id=? AND exit_date IS NULL''',
                (exit_price, exit_date, utc_now_iso(), lot_id),
            )
            if cursor.rowcount == 0:
                conn.rollback()
                print(f"错误：未找到 {code} 的在仓记录", file=sys.stderr)
                sys.exit(1)
            conn.commit()
        pnl_pct = round((exit_price - cost_price) / cost_price * 100, 1)
        name_str = f"({name})" if name else ""
        score_str = f" 买入得分:{buy_score}/80" if buy_score is not None else ""
        print(f"平仓已记录：{code}{name_str}{score_str}")
        print(f"  成本:{cost_price} → 卖出:{exit_price} | 盈亏:{pnl_pct:+.1f}%")
        print("  ⚠️ 该旧持仓缺少股数，无法补建可审计卖出现金流；不得用于事件账本收益统计")
    print('─' * 50)
    print(f'  复盘提示：a-stock-cache retro-add {code} <标签>')
    print('  可选标签：ROE高估 | 周期顶部 | 估值倍杀 | 护城河失守 | 行业误判 | 无错误')


def cmd_retro_add(args: list[str]) -> None:
    """添加平仓复盘。用法：retro-add <代码> <error_tags> [--note 备注] [--thesis 买入理由] [--gap 框架改进建议]"""
    if len(args) < 2:
        print("错误：需要参数 <代码> <error_tags>", file=sys.stderr)
        sys.exit(1)

    code = args[0]
    error_tags = args[1]
    retro_text = None
    thesis_notes = None
    framework_gap = None

    i = 2
    while i < len(args):
        flag = args[i]
        if flag in ('--note', '--thesis', '--gap'):
            if i + 1 >= len(args):
                print(f"错误：{flag} 需要参数", file=sys.stderr)
                sys.exit(1)
            if flag == '--note':
                retro_text = args[i + 1]
            elif flag == '--thesis':
                thesis_notes = args[i + 1]
            else:
                framework_gap = args[i + 1]
            i += 2
        else:
            print(f"错误：未知参数 {flag}", file=sys.stderr)
            sys.exit(1)

    with db_session() as conn:
        _backfill_holding_metadata(conn)
        row = conn.execute(
            '''SELECT h.id, h.code, h.name, h.buy_date, h.buy_score,
                      h.exit_date,
                      COALESCE(h.framework, (
                        SELECT framework FROM analysis_results a
                        WHERE a.code = h.code
                        ORDER BY a.date DESC LIMIT 1
                      )) AS framework
               FROM holdings h
               LEFT JOIN retro_notes r ON h.id = r.holding_id
               WHERE h.code=? AND h.exit_date IS NOT NULL AND r.id IS NULL
               ORDER BY h.exit_date DESC LIMIT 1''',
            (code,),
        ).fetchone()
        if not row:
            print(f"错误：未找到 {code} 的待复盘平仓记录", file=sys.stderr)
            sys.exit(1)

        holding_id, code, name, buy_date, buy_score, exit_date, framework = row
        try:
            lifecycle_return = calculate_lifecycle_return(
                _load_lifecycle_events(conn, holding_id),
                0,
                end_date=exit_date,
            )
        except ValueError as exc:
            print(f"错误：{code} 无法写入复盘收益：{exc}", file=sys.stderr)
            sys.exit(1)
        actual_return_pct = round(lifecycle_return.total_return_pct, 1)
        holding_days = lifecycle_return.holding_days

        conn.execute(
            '''INSERT INTO retro_notes
               (holding_id, code, name, framework, buy_date, exit_date, buy_score,
                actual_return_pct, holding_days, error_tags, thesis_notes, retro_text,
                framework_gap, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                holding_id, code, name, framework, buy_date, exit_date, buy_score,
                actual_return_pct, holding_days, error_tags, thesis_notes, retro_text,
                framework_gap, utc_now_iso(),
            ),
        )
        conn.commit()

    inferred_note = "（含推断历史，须核对券商流水）" if lifecycle_return.contains_inferred else ""
    print(f"复盘已记录：{code} | 标签:{error_tags} | 实际回报:{actual_return_pct:+.1f}%{inferred_note}")


def cmd_retro_pending(args: list[str] | None = None) -> None:
    """显示已平仓但尚未复盘的记录。用法：retro-pending"""
    with db_session() as conn:
        _backfill_holding_metadata(conn)
        rows = conn.execute(
            '''SELECT h.id, h.code, h.name, h.exit_date, h.buy_score
               FROM holdings h
               LEFT JOIN retro_notes r ON h.id = r.holding_id
               WHERE h.exit_date IS NOT NULL AND r.id IS NULL
               ORDER BY h.exit_date DESC'''
        ).fetchall()

        rendered_rows: list[tuple[str, str | None, str, int | None, LifecycleReturn | None, str | None]] = []
        for holding_id, code, name, exit_date, buy_score in rows:
            try:
                lifecycle_return = calculate_lifecycle_return(
                    _load_lifecycle_events(conn, holding_id), 0, end_date=exit_date,
                )
                rendered_rows.append((code, name, exit_date, buy_score, lifecycle_return, None))
            except ValueError as exc:
                rendered_rows.append((code, name, exit_date, buy_score, None, str(exc)))

    if not rendered_rows:
        print("无待复盘记录")
        return

    for code, name, exit_date, buy_score, lifecycle_return, error in rendered_rows:
        name_str = name or "─"
        score_str = str(buy_score) if buy_score is not None else "─"
        if lifecycle_return is None:
            print(f"{code} {name_str} 平仓日期:{exit_date} 账本不完整:{error} 买入得分:{score_str}")
        else:
            print(
                f"{code} {name_str} 平仓日期:{exit_date} "
                f"回报:{lifecycle_return.total_return_pct:+.1f}% 买入得分:{score_str}"
            )


def cmd_retro_stats(args: list[str]) -> None:
    """显示复盘统计。用法：retro-stats [框架名]"""
    framework_filter = args[0] if args else None
    params: tuple[str, ...] = ()
    where = ""
    if framework_filter:
        where = "WHERE framework=?"
        params = (framework_filter,)

    with db_session() as conn:
        rows = conn.execute(
            f'''SELECT actual_return_pct, error_tags
                FROM retro_notes
                {where}''',
            params,
        ).fetchall()

    if not rows:
        print("暂无复盘记录")
        return

    returns = [r[0] for r in rows if r[0] is not None]
    total = len(rows)
    win_rate = round(sum(1 for value in returns if value > 0) / len(returns) * 100, 1) if returns else 0.0
    avg_return = round(sum(returns) / len(returns), 1) if returns else 0.0

    tag_counts: dict[str, int] = {}
    for _, tags in rows:
        if not tags:
            continue
        for tag in tags.split(','):
            tag = tag.strip()
            if tag:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    title = framework_filter or "全部"
    print(f"=== 复盘统计 [{title}] ===")
    print(f"案例数: {total}  胜率: {win_rate}%  平均回报: {avg_return:+.1f}%")
    print("错误标签分布:")
    for tag, count in sorted(tag_counts.items(), key=lambda item: (-item[1], item[0])):
        warning = " ★ 建议复查框架规则" if count >= 3 else ""
        print(f"  {tag}: {count}次{warning}")


def cmd_retro_outliers(args: list[str]) -> None:
    """显示亏损超过阈值且尚未复盘的记录。用法：retro-outliers [--loss N]"""
    threshold = -10.0
    i = 0
    while i < len(args):
        if args[i] == '--loss':
            if i + 1 >= len(args):
                print("错误：--loss 需要参数", file=sys.stderr)
                sys.exit(1)
            threshold = -abs(_parse_cli_finite_float(args[i + 1], '--loss'))
            i += 2
        else:
            print(f"错误：未知参数 {args[i]}", file=sys.stderr)
            sys.exit(1)

    with db_session() as conn:
        _backfill_holding_metadata(conn)
        rows = conn.execute(
            '''SELECT h.id, h.code, h.name, h.exit_date, h.buy_score
               FROM holdings h
               LEFT JOIN retro_notes r ON h.id = r.holding_id
               WHERE h.exit_date IS NOT NULL
                 AND r.id IS NULL
               ORDER BY h.exit_date DESC''',
        ).fetchall()
        outliers: list[tuple[str, str | None, str, LifecycleReturn]] = []
        for holding_id, code, name, exit_date, _buy_score in rows:
            try:
                lifecycle_return = calculate_lifecycle_return(
                    _load_lifecycle_events(conn, holding_id), 0, end_date=exit_date,
                )
            except ValueError:
                continue
            if lifecycle_return.total_return_pct < threshold:
                outliers.append((code, name, exit_date, lifecycle_return))

    if not outliers:
        print(f"无亏损超过 {threshold:.0f}% 的未复盘记录")
        return

    print(f"亏损超过 {threshold:.0f}% 的未复盘记录:")
    for code, name, exit_date, lifecycle_return in sorted(
        outliers, key=lambda item: item[3].total_return_pct,
    ):
        name_str = name or "─"
        print(
            f"{code} {name_str} 平仓日期:{exit_date} "
            f"实际回报:{lifecycle_return.total_return_pct:+.1f}%"
        )


def cmd_remove_holding(args: list[str]) -> None:
    """Permanently delete a holding and every lifecycle-owned child record."""
    if len(args) < 1:
        print("错误：需要参数 <代码>", file=sys.stderr)
        sys.exit(1)
    code = args[0]
    with db_session() as conn:
        conn.execute('BEGIN IMMEDIATE')
        holding_ids = [
            row[0] for row in conn.execute(
                'SELECT id FROM holdings WHERE code=?', (code,),
            ).fetchall()
        ]
        if not holding_ids:
            conn.rollback()
            print(f"未找到持仓记录：{code}", file=sys.stderr)
            sys.exit(1)
        placeholders = ','.join('?' for _ in holding_ids)
        for table in (
            'holding_events',
            'holding_l3_conditions',
            'holding_tier_state',
            'holding_alerts',
            'retro_notes',
        ):
            conn.execute(
                f'DELETE FROM {table} WHERE holding_id IN ({placeholders})', holding_ids,
            )
        deleted = conn.execute('DELETE FROM holdings WHERE code=?', (code,)).rowcount
        conn.commit()
    if deleted:
        print(f"已移除持仓：{code}")


def cmd_update_return(args: list[str]) -> None:
    """卖出后记录实际回报。用法：update-return <代码> <实际回报%>"""
    if len(args) < 2:
        print("错误：需要参数 <代码> <实际回报%>", file=sys.stderr)
        sys.exit(1)
    code = args[0]
    return_pct = _parse_cli_finite_float(args[1], '回报率')

    with db_session() as conn:
        row = conn.execute(
            'SELECT date FROM analysis_results WHERE code=? ORDER BY date DESC LIMIT 1',
            (code,)
        ).fetchone()
        if not row:
            print(f"错误：未找到 {code} 的分析结论记录，请先执行 set-analysis", file=sys.stderr)
            sys.exit(1)

        analysis_date = row[0]
        holding_row = conn.execute(
            '''SELECT buy_date FROM holdings
               WHERE code=?
               ORDER BY CASE WHEN exit_date IS NULL THEN 0 ELSE 1 END,
                        COALESCE(exit_date, '9999-12-31') DESC, id DESC
               LIMIT 1''',
            (code,),
        ).fetchone()
        try:
            from datetime import date as _date
            start_date = holding_row[0] if holding_row and holding_row[0] else analysis_date
            holding_days = (_date.today() - _date.fromisoformat(start_date)).days
        except Exception:
            holding_days = None

        conn.execute(
            'UPDATE analysis_results SET return_pct=?, holding_days=? WHERE code=? AND date=?',
            (return_pct, holding_days, code, analysis_date)
        )
        conn.commit()
        meta = conn.execute(
            'SELECT name, score FROM analysis_results WHERE code=? AND date=?',
            (code, analysis_date)
        ).fetchone()

    name_str  = f"({meta[0]})" if meta and meta[0] else ""
    score_str = f" 买入得分:{meta[1]}/80" if meta and meta[1] else ""
    sign      = '+' if return_pct >= 0 else ''
    print(f"✅ 回报已记录：{code}{name_str}{score_str}")
    print(f"  分析日期:{analysis_date} | 持有:{holding_days}天 | 实际回报:{sign}{return_pct}%")


def cmd_position_return(args: list[str]) -> None:
    """Calculate cash-flow return for the current, or latest closed, position lifecycle."""
    if not args:
        print("错误：需要参数 <代码> [当前价]", file=sys.stderr)
        sys.exit(1)
    code = args[0]
    current_price = None
    if len(args) > 1:
        current_price = _parse_cli_finite_float(
            args[1], '当前价', minimum=0, strict_minimum=True,
        )
    with db_session() as conn:
        open_rows = conn.execute(
            '''SELECT id, shares, exit_date FROM holdings
               WHERE code=? AND exit_date IS NULL ORDER BY id''',
            (code,),
        ).fetchall()
        if len(open_rows) > 1:
            print(
                f"错误：{code} 有{len(open_rows)}条在仓记录；"
                "无法确定应计算哪个持仓生命周期",
                file=sys.stderr,
            )
            sys.exit(1)
        lifecycle = open_rows[0] if open_rows else conn.execute(
            '''SELECT id, shares, exit_date FROM holdings
               WHERE code=? AND exit_date IS NOT NULL
               ORDER BY exit_date DESC, id DESC LIMIT 1''',
            (code,),
        ).fetchone()
        if lifecycle is None:
            print(f"错误：未找到 {code} 的持仓记录", file=sys.stderr)
            sys.exit(1)
        holding_id, open_shares, exit_date = lifecycle
        events = _load_lifecycle_events(conn, holding_id)
    if not events:
        print(
            f"错误：{code} 当前持仓生命周期无交易事件；旧持仓须先迁移账本",
            file=sys.stderr,
        )
        sys.exit(1)
    remaining_shares = open_shares if exit_date is None else 0
    if remaining_shares and current_price is None:
        current_price = fetch_current_price(code)
    last_day = cst_today() if remaining_shares else (exit_date or events[-1][1])
    try:
        lifecycle_return = calculate_lifecycle_return(
            events, remaining_shares, end_date=last_day, current_price=current_price,
        )
    except ValueError as exc:
        print(f"错误：{code} {exc}", file=sys.stderr)
        sys.exit(1)
    print(
        f"{code} 事件账本总回报：{lifecycle_return.total_return_pct:+.2f}% | "
        f"盈亏:{lifecycle_return.pnl:+.2f}元 | 投入:{lifecycle_return.invested:.2f} "
        f"卖出回款:{lifecycle_return.sale_cash:.2f} 分红:{lifecycle_return.dividends:.2f} "
        f"在仓市值:{lifecycle_return.market_value:.2f} | 持有:{lifecycle_return.holding_days}天"
    )
    if lifecycle_return.contains_inferred:
        print("  ⚠️ 含旧持仓推断事件：历史费用、分红或部分交易可能缺失，须与券商流水核对")


def _parse_portfolio_risk_args(args: list[str] | None) -> tuple[float | None, float]:
    portfolio_value = None
    max_position_risk_pct = 2.0
    args = args or []
    i = 0
    while i < len(args):
        if args[i] not in ('--portfolio-value', '--max-position-risk-pct') or i + 1 >= len(args):
            print(f"错误：未知或不完整参数 {args[i]}", file=sys.stderr)
            sys.exit(1)
        value = _parse_cli_finite_float(
            args[i + 1], args[i], minimum=0, strict_minimum=True,
        )
        if args[i] == '--portfolio-value':
            portfolio_value = value
        else:
            max_position_risk_pct = value
        i += 2
    return portfolio_value, max_position_risk_pct


def cmd_portfolio_risk(args: list[str] | None = None) -> None:
    """Market-value weighted portfolio view with explicit stop-loss risk budget."""
    portfolio_value, max_position_risk_pct = _parse_portfolio_risk_args(args)
    with db_session() as conn:
        holdings = conn.execute(
            '''SELECT h.code, h.name, h.cost_price, h.shares, h.buy_date, h.buy_score,
                      f.industry, h.framework, h.framework_confident, h.stop_loss_20
               FROM holdings h LEFT JOIN stock_fundamentals f ON h.code = f.code
               WHERE h.exit_date IS NULL ORDER BY h.buy_date DESC'''
        ).fetchall()
    if not holdings:
        print("暂无持仓")
        return

    print(f"\n{'─'*104}")
    print(f"  组合风险视图  现价查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'─'*104}")

    codes = [h[0] for h in holdings]
    quotes = fetch_current_price_quotes(codes)
    today_str = cst_today()
    valued_rows = []
    for (
        code, name, cost, shares, buy_date, score, industry, holding_framework,
        framework_confident, sl20,
    ) in holdings:
        if holding_framework:
            fw, confident = holding_framework, bool(framework_confident)
        else:
            fw, confident = infer_framework(industry)
        quote = quotes.get(code)
        curr = quote.price if quote and quote.quote_date == today_str else None
        market_value = curr * shares if curr and shares else None
        valued_rows.append(
            (code, name, cost, shares, score, fw, confident, sl20, curr, market_value)
        )

    stock_market_value = sum(row[9] for row in valued_rows if row[9] is not None)
    if portfolio_value is None:
        portfolio_value = stock_market_value
        denominator_label = "已取价股票市值（未提供现金/其他资产）"
    else:
        denominator_label = "用户提供的可投资组合总资产"
    if portfolio_value <= 0:
        print("  无法计算：所有持仓均缺少股数或实时价格")
        return

    print(f"  风险分母：{denominator_label} = {portfolio_value:.2f}元")
    print(
        f"  {'股票':<16} {'框架':>5} {'股数':>6} {'当前价':>7} {'市值权重':>8} "
        f"{'浮盈%':>7} {'止损风险':>9} {'风险贡献':>8} {'状态':>5}"
    )
    print(f"  {'─'*100}")

    framework_values: dict[str, float] = {}
    total_stop_risk = 0.0
    for code, name, cost, shares, score, fw, confident, sl20, curr, market_value in valued_rows:
        fw_display = fw if confident else f"{fw}?"
        label      = f"{name}({code})" if name else code
        pnl_str  = f"{(curr - cost) / cost * 100:+.1f}%" if curr and cost else "─"
        curr_str = f"{curr:.2f}" if curr else "─"
        shares_str = str(shares) if shares is not None else "─"
        if market_value is None:
            print(
                f"  {label:<16} {fw_display:>5} {shares_str:>6} {curr_str:>7} "
                f"{'─':>8} {pnl_str:>7} {'─':>9} {'─':>8} {'缺数据':>5}"
            )
            continue
        weight_pct = market_value / portfolio_value * 100
        if sl20 is None:
            stop_risk = None
            risk_pct = None
        else:
            stop_risk = max(curr - sl20, 0) * shares
            risk_pct = stop_risk / portfolio_value * 100
            total_stop_risk += stop_risk
        framework_values[fw] = framework_values.get(fw, 0.0) + market_value
        risk_str = f"{stop_risk:.0f}元" if stop_risk is not None else "─"
        risk_pct_str = f"{risk_pct:.2f}%" if risk_pct is not None else "─"
        status = (
            "超预算" if risk_pct is not None and risk_pct > max_position_risk_pct
            else "已破线" if sl20 is not None and curr <= sl20
            else "正常"
        )
        print(
            f"  {label:<16} {fw_display:>5} {shares_str:>6} {curr_str:>7} "
            f"{weight_pct:>7.1f}% {pnl_str:>7} {risk_str:>9} {risk_pct_str:>8} {status:>5}"
        )

    stock_weight = stock_market_value / portfolio_value * 100
    print(
        f"\n  股票总仓位：{stock_weight:.1f}% | "
        f"第二档止损总风险：{total_stop_risk:.2f}元 "
        f"({total_stop_risk / portfolio_value * 100:.2f}%)"
    )
    print(f"  单股风险预算上限：{max_position_risk_pct:.2f}%")
    print(f"\n  框架分布（按市值，{len(holdings)} 只在仓）")
    for fw, value in sorted(framework_values.items()):
        print(f"    {fw}: {value:.2f}元 ({value / portfolio_value * 100:.1f}%)")
    print()


def _is_a_share_trading_hours(dt: datetime) -> bool:
    """A股标准交易时段：工作日 09:30-11:30 / 13:00-15:00。调用方须传入 Asia/Shanghai (UTC+8) 时区的 datetime。"""
    if dt.weekday() >= 5:  # 5=Sat, 6=Sun
        return False
    t = dt.time()
    return dtime(9, 30) <= t <= dtime(11, 30) or dtime(13, 0) <= t <= dtime(15, 0)


def _legacy_style_status(curr: float, sl15: float, sl20: float, price_label: str) -> tuple[str, bool]:
    """🔴/⚠️/✅ 图标区分严重度的历史文案，用于"新鲜度未知"和"收盘价"两种场景。
    返回 (status_text, is_alert)。
    """
    if curr <= sl20:
        return f"🔴 已跌破20%止损线（{sl20:.3f}），{price_label}{curr:.2f}，建议立即止损", True
    if curr <= sl15:
        return f"⚠️ 已跌破15%止损线（{sl15:.3f}），{price_label}{curr:.2f}，需提高警惕", True
    return f"✅ 正常，{price_label}{curr:.2f}（止损15%:{sl15:.3f} 20%:{sl20:.3f}）", False


def _intraday_status(curr: float, sl15: float, sl20: float) -> tuple[str, bool]:
    """盘中场景：跌破阈值统一用 🚨 盘中已跌破 标注，返回 (status_text, is_alert)。"""
    if curr <= sl20:
        return f"🚨 盘中已跌破20%止损线（{sl20:.3f}），现价{curr:.2f}，建议立即止损", True
    if curr <= sl15:
        return f"🚨 盘中已跌破15%止损线（{sl15:.3f}），现价{curr:.2f}，需提高警惕", True
    return f"✅ 正常，现价{curr:.2f}（止损15%:{sl15:.3f} 20%:{sl20:.3f}）", False


def _evaluate_holding_status(
    code: str, name: str | None,
    sl15: float, sl20: float,
    quote: "PriceQuote | None",
    today_str: str, now: datetime
) -> tuple[str, str, bool]:
    """Evaluate one holding's stop-loss status.

    Returns (label, status_text, is_alert).
    """
    label = f"{name}({code})" if name else code
    curr = quote.price if quote else None

    if curr is None:
        status = "─ 无实时价格"
        is_alert = False
    elif quote.quote_date is not None and quote.quote_date != today_str:
        status = f"📋 上一交易日收盘价观察提醒（{quote.quote_date}收盘{curr:.2f}，非当前价，请开盘后复核）"
        is_alert = False
    elif quote.quote_date == today_str and _is_a_share_trading_hours(now):
        status, is_alert = _intraday_status(curr, sl15, sl20)
    elif quote.quote_date == today_str:
        status, is_alert = _legacy_style_status(curr, sl15, sl20, "收盘价")
    else:
        status = "─ 行情时间戳不可验证，不触发止损预警"
        is_alert = False

    return label, status, is_alert


def cmd_check_holdings(args: list[str] | None = None) -> None:
    """持仓止损检查：对比当前价与15%/20%止损线，主动预警（P3-4）。
    区分盘中现价/收盘价/上一交易日陈旧行情三种口径，非交易时段拿到隔夜收盘价
    时只输出观察提醒、不触发同等级止损预警（见 PITFALLS.md [BUG-006]）。
    """
    with db_session() as conn:
        holdings = conn.execute(
            '''SELECT code, name, cost_price, stop_loss_15, stop_loss_20
               FROM holdings WHERE exit_date IS NULL ORDER BY code'''
        ).fetchall()
    if not holdings:
        print("暂无持仓")
        return

    now = datetime.now(tz=_CST)
    today_str = now.strftime('%Y-%m-%d')

    print(f"\n{'─'*72}")
    print(f"  持仓止损检查  现价查询时间: {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"{'─'*72}")

    codes = [h[0] for h in holdings]
    quotes = fetch_current_price_quotes(codes)

    alerts = []
    for code, name, _cost, sl15, sl20 in holdings:
        label, status, is_alert = _evaluate_holding_status(
            code, name, sl15, sl20, quotes.get(code), today_str, now
        )
        if is_alert:
            alerts.append((label, status))
        print(f"  {label:<16} {status}")

    print()
    if alerts:
        print(f"  共 {len(alerts)} 项预警，请及时处理：")
        for label, status in alerts:
            print(f"    {label}: {status}")
    else:
        print("  无预警，所有持仓价格在止损线之上")
    print()


def _single_open_holding(conn: sqlite3.Connection, code: str) -> tuple:
    rows = conn.execute(
        '''SELECT id, buy_date, framework FROM holdings
           WHERE code=? AND exit_date IS NULL ORDER BY id''',
        (code,),
    ).fetchall()
    if not rows:
        print(f"错误：未找到 {code} 的在仓记录", file=sys.stderr)
        sys.exit(1)
    if len(rows) != 1:
        print(
            f"错误：{code} 有{len(rows)}条在仓记录；结构化状态要求先按单行持仓约定合并",
            file=sys.stderr,
        )
        sys.exit(1)
    return rows[0]


def cmd_l3_add(args: list[str]) -> None:
    """Add a structured L3 condition. Usage: l3-add <code> <origin> <condition> [temporary_exit_rule]."""
    if len(args) < 3:
        print(
            "错误：需要参数 <代码> <original|recovered|new_monitoring> "
            "<条件文本> [临时出场规则]",
            file=sys.stderr,
        )
        sys.exit(1)
    code, origin, condition_text = args[:3]
    temporary_exit_rule = args[3] if len(args) > 3 else None
    if origin not in ('original', 'recovered', 'new_monitoring'):
        print("错误：origin 非法", file=sys.stderr)
        sys.exit(1)
    with db_session() as conn:
        holding_id, _, _ = _single_open_holding(conn, code)
        now_iso = utc_now_iso()
        cursor = conn.execute(
            '''INSERT INTO holding_l3_conditions
               (holding_id, condition_text, origin_type, temporary_exit_rule,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (
                holding_id, condition_text, origin, temporary_exit_rule,
                now_iso, now_iso,
            ),
        )
        conn.commit()
    print(f"L3条件已记录：id={cursor.lastrowid} {code} [{origin}] {condition_text}")


def cmd_l3_update(args: list[str]) -> None:
    """Update evidence-backed status. Usage: l3-update <id> <status> <as_of> <evidence> [next_review]."""
    if len(args) < 4:
        print(
            "错误：需要参数 <条件id> <pending|not_triggered|watch|triggered> "
            "<as-of> <证据> [下次复核日期]",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        condition_id = int(args[0])
    except ValueError:
        print("错误：条件id必须为整数", file=sys.stderr)
        sys.exit(1)
    status, as_of, evidence = args[1:4]
    if status not in ('pending', 'not_triggered', 'watch', 'triggered'):
        print("错误：L3状态非法", file=sys.stderr)
        sys.exit(1)
    next_review = args[4] if len(args) > 4 else None
    for candidate in (as_of, next_review):
        if candidate:
            try:
                date.fromisoformat(candidate)
            except ValueError:
                print("错误：日期必须为 YYYY-MM-DD", file=sys.stderr)
                sys.exit(1)
    with db_session() as conn:
        cursor = conn.execute(
            '''UPDATE holding_l3_conditions
               SET status=?, evidence=?, as_of=?, next_review_date=?, updated_at=?
               WHERE id=?''',
            (status, evidence, as_of, next_review, utc_now_iso(), condition_id),
        )
        if cursor.rowcount == 0:
            print(f"错误：未找到L3条件 id={condition_id}", file=sys.stderr)
            sys.exit(1)
        conn.commit()
    print(f"L3状态已更新：id={condition_id} → {status}")


def cmd_l3_list(args: list[str]) -> None:
    if len(args) != 1:
        print("错误：需要参数 <代码>", file=sys.stderr)
        sys.exit(1)
    code = args[0]
    with db_session() as conn:
        rows = conn.execute(
            '''SELECT l.id, l.origin_type, l.status, l.condition_text, l.as_of,
                      l.next_review_date, l.evidence, l.temporary_exit_rule
               FROM holding_l3_conditions l
               JOIN holdings h ON h.id=l.holding_id
               WHERE h.code=? AND h.exit_date IS NULL ORDER BY l.id''',
            (code,),
        ).fetchall()
    if not rows:
        print(f"{code} 无结构化L3条件")
        return
    for row in rows:
        print(
            f"#{row[0]} [{row[1]}] {row[2]} | {row[3]} | as-of:{row[4] or '─'} "
            f"| 下次:{row[5] or '─'} | 证据:{row[6] or '─'} | 临时出场:{row[7] or '─'}"
        )


def cmd_tier_config(args: list[str]) -> None:
    """Persist entry-time tier choices outside notes."""
    if len(args) < 2:
        print(
            "错误：需要参数 <代码> <A|B|C|none> [目标涨幅%|none] [E|F|none]",
            file=sys.stderr,
        )
        sys.exit(1)
    code = args[0]
    exit_path = None if args[1].lower() == 'none' else args[1].upper()
    if exit_path not in (None, 'A', 'B', 'C'):
        print("错误：出场路径只能为 A/B/C/none", file=sys.stderr)
        sys.exit(1)
    target_pct = None
    if len(args) > 2 and args[2].lower() != 'none':
        target_pct = _parse_cli_finite_float(args[2], '目标涨幅')
    if exit_path == 'B' and (target_pct is None or target_pct <= 0):
        print("错误：路径B必须设置大于0的目标涨幅", file=sys.stderr)
        sys.exit(1)
    if exit_path != 'B' and target_pct is not None:
        print("错误：只有路径B可以设置目标涨幅", file=sys.stderr)
        sys.exit(1)
    exemption = None
    if len(args) > 3 and args[3].lower() != 'none':
        exemption = args[3].upper()
        if exemption not in ('E', 'F'):
            print("错误：豁免框架只能为 E/F/none", file=sys.stderr)
            sys.exit(1)
    if exemption and exit_path is not None:
        print("错误：轻仓试探出场路径与正式仓位Tier1豁免不能同时设置", file=sys.stderr)
        sys.exit(1)
    with db_session() as conn:
        holding_id, buy_date, framework = _single_open_holding(conn, code)
        if exemption and buy_date != cst_today():
            print("错误：Tier1估值豁免只能在建仓当日声明", file=sys.stderr)
            sys.exit(1)
        if exemption and not (framework or '').startswith(exemption):
            print(f"错误：持仓框架{framework or '未知'}与豁免框架{exemption}不一致", file=sys.stderr)
            sys.exit(1)
        conn.execute(
            '''INSERT INTO holding_tier_state
               (holding_id, exit_path, exit_target_pct, exemption_framework,
                exemption_declared_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(holding_id) DO UPDATE SET
                 exit_path=excluded.exit_path,
                 exit_target_pct=excluded.exit_target_pct,
                 exemption_framework=excluded.exemption_framework,
                 exemption_declared_at=excluded.exemption_declared_at,
                 updated_at=excluded.updated_at''',
            (
                holding_id, exit_path, target_pct, exemption,
                cst_today() if exemption else None, utc_now_iso(),
            ),
        )
        conn.commit()
    print(f"Tier配置已记录：{code} 路径={exit_path or 'none'} 豁免={exemption or 'none'}")


def cmd_holding_framework(args: list[str]) -> None:
    if len(args) != 2:
        print("错误：需要参数 <代码> <A|B|C|D|E|F>", file=sys.stderr)
        sys.exit(1)
    code, token = args[0], args[1]
    normalized = _FRAMEWORK_ALIASES.get(token.upper()) or _FRAMEWORK_ALIASES.get(token)
    if normalized is None:
        print("错误：框架必须为 A/B/C/D/E/F 或完整标签", file=sys.stderr)
        sys.exit(1)
    with db_session() as conn:
        holding_id, _, old_framework = _single_open_holding(conn, code)
        row = conn.execute(
            'SELECT reference_cost, cost_price FROM holdings WHERE id=?',
            (holding_id,),
        ).fetchone()
        reference_cost = row[0] or row[1]
        sl15_pct, sl20_pct = get_stop_loss_pct(normalized)
        now_iso = utc_now_iso()
        conn.execute(
            '''UPDATE holdings
               SET framework=?, framework_confident=1,
                   stop_loss_15=?, stop_loss_20=?, updated_at=?
               WHERE id=?''',
            (
                normalized, round(reference_cost * sl15_pct, 3),
                round(reference_cost * sl20_pct, 3), now_iso, holding_id,
            ),
        )
        conn.execute(
            '''INSERT INTO holding_events
               (holding_id, code, event_type, event_date, notes, created_at)
               VALUES (?, ?, 'adjustment', ?, ?, ?)''',
            (
                holding_id, code, cst_today(),
                f"framework:{old_framework or 'unknown'}->{normalized}", now_iso,
            ),
        )
        conn.commit()
    print(f"持仓框架已迁移：{code} {old_framework or 'unknown'} → {normalized}，止损线已重算")


def cmd_tier_update(args: list[str]) -> None:
    if len(args) != 3:
        print("错误：需要参数 <代码> <tier1|tier2|tier3> <状态>", file=sys.stderr)
        sys.exit(1)
    code, tier, status = args
    allowed = {
        'tier1': {'pending', 'completed', 'exempted'},
        'tier2': {'pending', 'completed'},
        'tier3': {'pending', 'completed'},
    }
    if tier not in allowed or status not in allowed[tier]:
        print("错误：Tier或状态非法", file=sys.stderr)
        sys.exit(1)
    with db_session() as conn:
        holding_id, _, _ = _single_open_holding(conn, code)
        conn.execute(
            '''INSERT INTO holding_tier_state (holding_id, updated_at)
               VALUES (?, ?) ON CONFLICT(holding_id) DO NOTHING''',
            (holding_id, utc_now_iso()),
        )
        conn.execute(
            f"UPDATE holding_tier_state SET {tier}_status=?, updated_at=? WHERE holding_id=?",
            (status, utc_now_iso(), holding_id),
        )
        conn.commit()
    print(f"Tier状态已更新：{code} {tier}={status}")


def cmd_alert_open(args: list[str]) -> None:
    """Open/update a deduplicated structured alert."""
    if len(args) < 6:
        print(
            "错误：需要参数 <代码> <yellow|red> "
            "<holding_deterioration|entry_valuation|unverified> "
            "<reason_code> <review_due|none> <原因> [证据]",
            file=sys.stderr,
        )
        sys.exit(1)
    code, level, category, reason_code, review_due, reason = args[:6]
    evidence = args[6] if len(args) > 6 else None
    if level not in ('yellow', 'red'):
        print("错误：预警级别非法", file=sys.stderr)
        sys.exit(1)
    if category not in ('holding_deterioration', 'entry_valuation', 'unverified'):
        print("错误：预警类别非法", file=sys.stderr)
        sys.exit(1)
    review_due = None if review_due.lower() == 'none' else review_due
    if review_due:
        try:
            date.fromisoformat(review_due)
        except ValueError:
            print("错误：复核日期必须为 YYYY-MM-DD 或 none", file=sys.stderr)
            sys.exit(1)
    with db_session() as conn:
        holding_id, _, _ = _single_open_holding(conn, code)
        now_iso = utc_now_iso()
        conn.execute(
            '''INSERT INTO holding_alerts
               (holding_id, code, level, category, reason_code, reason, evidence,
                opened_at, review_due, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(holding_id, reason_code) WHERE status != 'resolved'
               DO UPDATE SET level=excluded.level, category=excluded.category,
                 reason=excluded.reason, evidence=excluded.evidence,
                 review_due=excluded.review_due, updated_at=excluded.updated_at''',
            (
                holding_id, code, level, category, reason_code, reason, evidence,
                now_iso, review_due, now_iso,
            ),
        )
        conn.commit()
    print(f"结构化预警已记录：{code} {level} {reason_code}")


def cmd_alert_resolve(args: list[str]) -> None:
    if len(args) < 3:
        print("错误：需要参数 <代码> <reason_code> <解除证据>", file=sys.stderr)
        sys.exit(1)
    code, reason_code, evidence = args[0], args[1], ' '.join(args[2:])
    with db_session() as conn:
        now_iso = utc_now_iso()
        cursor = conn.execute(
            '''UPDATE holding_alerts
               SET status='resolved', resolved_at=?, resolution_evidence=?, updated_at=?
               WHERE code=? AND reason_code=? AND status!='resolved' ''',
            (now_iso, evidence, now_iso, code, reason_code),
        )
        if cursor.rowcount == 0:
            print("错误：未找到对应的活动预警", file=sys.stderr)
            sys.exit(1)
        conn.commit()
    print(f"预警已解除：{code} {reason_code}")


def cmd_alert_pending(args: list[str]) -> None:
    if len(args) < 3:
        print("错误：需要参数 <代码> <reason_code> <待核实说明>", file=sys.stderr)
        sys.exit(1)
    code, reason_code, evidence = args[0], args[1], ' '.join(args[2:])
    with db_session() as conn:
        cursor = conn.execute(
            '''UPDATE holding_alerts
               SET status='pending', evidence=?, updated_at=?
               WHERE code=? AND reason_code=? AND status='active' ''',
            (evidence, utc_now_iso(), code, reason_code),
        )
        if cursor.rowcount == 0:
            print("错误：未找到对应的活动预警", file=sys.stderr)
            sys.exit(1)
        conn.commit()
    print(f"预警已转待核实：{code} {reason_code}")


def cmd_alerts(args: list[str]) -> None:
    if len(args) != 1:
        print("错误：需要参数 <代码>", file=sys.stderr)
        sys.exit(1)
    with db_session() as conn:
        rows = conn.execute(
            '''SELECT level, category, reason_code, status, reason, review_due,
                      evidence, resolution_evidence
               FROM holding_alerts WHERE code=?
               ORDER BY status='resolved', opened_at, id''',
            (args[0],),
        ).fetchall()
    if not rows:
        print(f"{args[0]} 无结构化预警")
        return
    for row in rows:
        print(
            f"{row[0]} [{row[1]}] {row[2]} {row[3]} | {row[4]} "
            f"| 复核:{row[5] or '─'} | 证据:{row[6] or '─'} "
            f"| 解除:{row[7] or '─'}"
        )


def cmd_set_flag(args: list[str]) -> None:
    """⑤ 记录红黄线预警（追加，不覆盖历史）"""
    if len(args) < 3:
        print("错误：需要参数 <代码> <yellow|red> <原因>", file=sys.stderr)
        sys.exit(1)
    code, level, reason = args[0], args[1], ' '.join(args[2:])
    if level not in ('yellow', 'red'):
        print("错误：level 必须为 yellow 或 red", file=sys.stderr)
        sys.exit(1)
    today = cst_today()
    new_flag = json.dumps({'level': level, 'reason': reason, 'date': today}, ensure_ascii=False)
    with db_session() as conn:
        cursor = conn.execute(
            "UPDATE analysis_results "
            "SET flags = json_insert(COALESCE(NULLIF(flags, ''), '[]'), '$[#]', json(?)) "
            "WHERE code=? AND date=?",
            (new_flag, code, today)
        )
        if cursor.rowcount == 0:
            print(f"未找到今日分析记录，请先执行 set-analysis（代码：{code}）", file=sys.stderr)
            sys.exit(1)
        conn.commit()
    icon = '🔴' if level == 'red' else '⚠️'
    print(f"预警已记录：{code} {icon} {reason}")


def cmd_clear_flag(args: list[str]) -> None:
    """⑤ 清除指定股票今日所有预警标记"""
    if len(args) < 1:
        print("错误：需要参数 <代码>", file=sys.stderr)
        sys.exit(1)
    code = args[0]
    today = cst_today()
    with db_session() as conn:
        conn.execute(
            'UPDATE analysis_results SET flags=NULL WHERE code=? AND date=?',
            (code, today)
        )
        conn.commit()
    print(f"已清除 {code} 的今日预警标记")


def get_watchlist_rows() -> list[dict]:
    """Return the durable refresh set in a single fair scheduling order."""
    now = utc_now()
    today = cst_today()
    analysis_cutoff = now - timedelta(days=14)
    first_analysis_cutoff = now - timedelta(hours=24)
    with db_session() as conn:
        fundamentals_rows = conn.execute(
            'SELECT code, name, industry, data, updated_at, ttl_hours FROM stock_fundamentals'
        ).fetchall()
        analysis_rows = conn.execute(
            '''SELECT code, date, name, created_at, score, flags,
                      score_breakdown, quote_price
               FROM (
                   SELECT code, date, name, created_at, score, flags,
                          score_breakdown, quote_price,
                          ROW_NUMBER() OVER (
                              PARTITION BY code
                              ORDER BY created_at DESC, date DESC
                          ) AS row_rank
                   FROM analysis_results
               )
               WHERE row_rank=1'''
        ).fetchall()
        today_analysis_rows = conn.execute(
            '''SELECT code, date, name, created_at, score, flags,
                      score_breakdown, quote_price
               FROM analysis_results WHERE date=?''',
            (today,),
        ).fetchall()
        holding_rows = conn.execute(
            'SELECT code, name FROM holdings WHERE exit_date IS NULL'
        ).fetchall()
        quote_rows = conn.execute(
            '''SELECT code, price, fetched_at
               FROM (
                   SELECT code, price, fetched_at,
                          ROW_NUMBER() OVER (
                              PARTITION BY code
                              ORDER BY fetched_at DESC, id DESC
                          ) AS row_rank
                   FROM quote_snapshots WHERE valid=1
               )
               WHERE row_rank=1'''
        ).fetchall()
        qualitative_rows = conn.execute(
            'SELECT code, name, industry FROM qualitative_only_securities'
        ).fetchall()

    fundamentals = {row[0]: row for row in fundamentals_rows}
    latest_analysis = {row[0]: row for row in analysis_rows}
    today_analysis = {row[0]: row for row in today_analysis_rows}
    has_any_analysis = set(latest_analysis)
    recent_analysis_codes: set[str] = set()
    for row in analysis_rows:
        code = row[0]
        try:
            if parse_timestamp_utc(row[3]) >= analysis_cutoff:
                recent_analysis_codes.add(code)
        except (TypeError, ValueError):
            continue

    latest_quotes = {row[0]: row for row in quote_rows}
    recent_fetch_codes: set[str] = set()
    for row in quote_rows:
        try:
            if parse_timestamp_utc(row[2]) >= first_analysis_cutoff:
                recent_fetch_codes.add(row[0])
        except (TypeError, ValueError):
            continue

    holding_names = {code: name for code, name in holding_rows}
    qualitative_only_securities = {
        code: (name, industry) for code, name, industry in qualitative_rows
    }
    holding_codes = set(holding_names)
    pending_first_codes = recent_fetch_codes - has_any_analysis
    eligible_codes = holding_codes | recent_analysis_codes | pending_first_codes

    rows: list[dict] = []
    for code in eligible_codes:
        fund = fundamentals.get(code)
        latest = latest_analysis.get(code)
        current = today_analysis.get(code)
        quote = latest_quotes.get(code)
        data = _safe_json_value(fund[3], dict, {}) if fund else {}
        cache_expired = fund is None or is_expired(fund[4], fund[5])
        terminal_status = qualitative_only_securities.get(code)
        industry = (fund[2] if fund else None) or (
            terminal_status[1] if terminal_status else None
        )
        qualitative_only = bool(terminal_status) or is_unsupported_financial_industry(industry)
        price_invalidated = False
        analysis_price = current[7] if current else None
        quote_price = quote[1] if quote else None
        if (
            isinstance(analysis_price, (int, float))
            and not isinstance(analysis_price, bool)
            and math.isfinite(float(analysis_price))
            and analysis_price > 0
            and isinstance(quote_price, (int, float))
            and not isinstance(quote_price, bool)
            and math.isfinite(float(quote_price))
            and quote_price > 0
        ):
            price_invalidated = (
                abs(quote_price - analysis_price) / analysis_price
                >= ANALYSIS_PRICE_INVALIDATION_THRESHOLD
            )
        needs_refresh = (
            not qualitative_only
            and (current is None or cache_expired or price_invalidated)
        )
        if code in holding_codes:
            eligible_reason = 'holding'
        elif code in pending_first_codes:
            eligible_reason = 'pending-first-analysis'
        else:
            eligible_reason = 'recent-analysis'
        display_analysis = current or latest
        raw_flags = (
            _safe_json_value(display_analysis[5], list, [])
            if display_analysis else []
        )
        flags = [
            flag for flag in raw_flags
            if isinstance(flag, dict) and flag.get('level') in {'red', 'yellow'}
        ]
        score_breakdown = (
            _safe_json_value(display_analysis[6], dict, None)
            if display_analysis else None
        )
        rows.append({
            'code': code,
            'name': (
                (fund[1] if fund else None)
                or holding_names.get(code)
                or (terminal_status[0] if terminal_status else None)
                or (latest[2] if latest else None)
                or code
            ),
            'industry': industry,
            'eligible_reason': eligible_reason,
            'refresh_blocked_reason': (
                'unsupported-financial-qualitative-only' if qualitative_only else None
            ),
            'is_holding': code in holding_codes,
            'cache_expired': cache_expired,
            'last_analysis_at': latest[3] if latest else None,
            'updated_at': fund[4] if fund else None,
            'ttl_hours': fund[5] if fund else None,
            'analysis_time': current[3] if current else None,
            'score': display_analysis[4] if display_analysis else None,
            'flags': flags,
            'score_breakdown': score_breakdown,
            'needs_refresh': needs_refresh,
            'price_invalidated': price_invalidated,
            'pe_ttm': data.get('pe_ttm'),
            'pb': data.get('pb'),
            'dividend_yield': data.get('dividend_yield'),
            'roe_3y_avg': data.get('roe_3y_avg'),
        })

    def oldest_first(value: str | None) -> tuple[int, datetime]:
        if value is None:
            return (0, datetime.min.replace(tzinfo=_UTC))
        try:
            return (1, parse_timestamp_utc(value))
        except (TypeError, ValueError):
            return (0, datetime.min.replace(tzinfo=_UTC))

    rows.sort(key=lambda row: (
        not row['needs_refresh'],
        not row['is_holding'],
        row['eligible_reason'] != 'pending-first-analysis',
        oldest_first(row['last_analysis_at']),
        oldest_first(row['updated_at']),
        row['code'],
    ))
    for priority, row in enumerate(rows, start=1):
        row['refresh_priority'] = priority
    return rows


def _format_breakdown_line(bd: dict) -> str:
    """Format score breakdown as a watchlist sub-row.

    Supports two schemas:
    - Nested: {"fundamentals": {"subtotal": N, ...}, "timing": {"subtotal": N, ...}, "total": N}
    - Flat with top-level subtotals: {"fundamentals": N, "timing": N, "total": N}
    - Legacy flat: {"roe": N, "volume": N, ...} (no fundamentals/timing keys)
    """
    if 'fundamentals' in bd and 'timing' in bd:
        f_val = bd['fundamentals']
        t_val = bd['timing']
        f_sub = f_val.get('subtotal', '?') if isinstance(f_val, dict) else f_val
        t_sub = t_val.get('subtotal', '?') if isinstance(t_val, dict) else t_val
        total = bd.get('total', '?')
        return f"  分项: 基本面 {f_sub}/60 | 择时 {t_sub}/20 | 合计 {total}/80"
    total = bd.get('total', sum(v for v in bd.values() if isinstance(v, (int, float))))
    return f"  分项: 合计 {total}"


def cmd_watchlist(args: list[str] | None = None) -> None:
    """显示持久刷新集合，顺序与自动刷新公平调度顺序一致。"""
    args = args or []
    show_breakdown = '--breakdown' in args
    rows = get_watchlist_rows()
    if '--json' in args:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return

    if not rows:
        print("暂无有效缓存股票")
        return

    header = f"{'股票':<14} {'行业':<16} {'得分':>4} {'PE':>6} {'PB':>5} {'股息率':>7} {'ROE':>7}  预警  分析"
    print(header)
    print("─" * 75)
    for row in rows:
        code, name = row['code'], row['name']
        industry = row['industry'] or '─'
        analysis_time, score, flags = row['analysis_time'], row['score'], row['flags']
        pe  = str(row['pe_ttm'] or '─')
        pb  = str(row['pb'] or '─')
        div = (str(row['dividend_yield']) + '%') if row['dividend_yield'] else '─'
        roe = (str(row['roe_3y_avg']) + '%') if row['roe_3y_avg'] else '─'
        score_str = str(score) if score is not None else '─'
        # 预警标记
        if any(f['level'] == 'red' for f in flags):
            flag_str = '🔴'
        elif any(f['level'] == 'yellow' for f in flags):
            flag_str = '⚠️'
        else:
            flag_str = '─'
        tag = (
            "仅定性" if row.get('refresh_blocked_reason')
            else "✅今日" if analysis_time
            else "─"
        )
        label = f"{name}({code})"
        print(f"{label:<14} {industry:<16} {score_str:>4} {pe:>6} {pb:>5} {div:>7} {roe:>7}  {flag_str:<4}  {tag}")
        if show_breakdown and row.get('score_breakdown'):
            print(_format_breakdown_line(row['score_breakdown']))


def cmd_list(args: list[str] | None = None) -> None:
    """列出所有缓存内容（含过期）"""
    today = cst_today()
    with db_session() as conn:
        stocks = conn.execute(
            'SELECT code, name, industry, updated_at, ttl_hours FROM stock_fundamentals ORDER BY updated_at DESC'
        ).fetchall()
        analyses = conn.execute(
            '''SELECT a.code, a.date, a.created_at, COALESCE(a.name, f.name, a.code) as display_name,
                      a.score, a.flags, a.score_breakdown
               FROM analysis_results a
               LEFT JOIN stock_fundamentals f ON a.code = f.code
               ORDER BY a.created_at DESC LIMIT 20'''
        ).fetchall()

    valid_count = sum(1 for s in stocks if not is_expired(s[3], s[4]))
    print(f"=== 基本面缓存 ({valid_count}有效 / {len(stocks)}条) ===")
    for s in stocks:
        code, name, industry, updated_at, ttl_hours = s
        expired = is_expired(updated_at, ttl_hours)
        status = "⚠️ 已过期" if expired else "✅ 有效"
        print(f"  {name}({code}) [{industry}] 更新:{format_timestamp_cst(updated_at)} TTL:{ttl_hours}h [{status}]")

    today_count = sum(1 for a in analyses if a[1] == today)
    print(f"\n=== 分析结论缓存 ({today_count}今日有效 / 近{len(analyses)}条) ===")
    for a in analyses:
        code, date, created_at, display_name, score, flags_raw, breakdown_raw = a
        status = "✅ 今日有效" if date == today else f"⚠️ 过期({date})"
        score_str = f" 得分:{score}" if score is not None else ""
        breakdown_str = " 📊分项" if breakdown_raw else ""
        raw_flags = _safe_json_value(flags_raw, list, [])
        flags = [
            flag for flag in raw_flags
            if isinstance(flag, dict) and flag.get('level') in {'red', 'yellow'}
        ]
        flag_icons = ''.join('🔴' if f['level'] == 'red' else '⚠️' for f in flags)
        print(f"  {display_name}({code}) [{status}]{score_str}{breakdown_str}{flag_icons} 创建:{format_timestamp_cst(created_at)}")


def cmd_cleanup(args: list[str] | None = None) -> None:
    """清除所有过期的缓存条目"""
    with db_session() as conn:
        stocks = conn.execute(
            'SELECT code, name, updated_at, ttl_hours FROM stock_fundamentals'
        ).fetchall()
        expired_names = []
        for s in stocks:
            if is_expired(s[2], s[3]):
                deleted = conn.execute(
                    '''DELETE FROM stock_fundamentals
                       WHERE code=? AND updated_at=?''',
                    (s[0], s[2]),
                ).rowcount
                if deleted:
                    expired_names.append(f"{s[1]}({s[0]})")

        analysis_cutoff = utc_now() - timedelta(days=14)
        analysis_rows = conn.execute(
            'SELECT code, date, created_at FROM analysis_results'
        ).fetchall()
        old_count = 0
        for code, analysis_date, created_at in analysis_rows:
            try:
                if parse_timestamp_utc(created_at) < analysis_cutoff:
                    old_count += conn.execute(
                        '''DELETE FROM analysis_results
                           WHERE code=? AND date=? AND created_at=?''',
                        (code, analysis_date, created_at),
                    ).rowcount
            except (TypeError, ValueError):
                # Unknown legacy timestamp formats are retained rather than
                # risking deletion of scheduler history.
                continue
        pruned_quote_count = conn.execute(
            '''DELETE FROM quote_snapshots
               WHERE id IN (
                   SELECT id FROM (
                       SELECT id,
                              ROW_NUMBER() OVER (
                                  PARTITION BY code
                                  ORDER BY fetched_at DESC, id DESC
                              ) AS row_rank
                       FROM quote_snapshots
                   )
                   WHERE row_rank > ?
               )''',
            (QUOTE_SNAPSHOT_RETENTION_PER_CODE,),
        ).rowcount
        orphan_count = 0
        for table in (
            'holding_events',
            'holding_l3_conditions',
            'holding_tier_state',
            'holding_alerts',
            'retro_notes',
        ):
            orphan_count += conn.execute(
                f'''DELETE FROM {table}
                    WHERE NOT EXISTS (
                      SELECT 1 FROM holdings h WHERE h.id={table}.holding_id
                    )'''
            ).rowcount
        conn.commit()

    if expired_names:
        print(f"已清除过期基本面缓存：{', '.join(expired_names)}")
    if old_count:
        print(f"已清除 {old_count} 条历史分析结论")
    if pruned_quote_count:
        print(f"已清除 {pruned_quote_count} 条超限行情快照")
    if orphan_count:
        print(f"已清除 {orphan_count} 条孤儿持仓关联记录")
    if not expired_names and not old_count and not pruned_quote_count and not orphan_count:
        print("无过期缓存，无需清理")


def cmd_clear(args: list[str]) -> None:
    """清除缓存。不带参数=清全部，带代码=清指定股票"""
    with db_session() as conn:
        if args:
            code = args[0]
            conn.execute('DELETE FROM stock_fundamentals WHERE code=?', (code,))
            conn.execute('DELETE FROM analysis_results WHERE code=?', (code,))
            conn.execute('DELETE FROM quote_snapshots WHERE code=?', (code,))
            conn.execute('DELETE FROM qualitative_only_securities WHERE code=?', (code,))
            conn.commit()
            print(f"已清除 {code} 的所有缓存")
        else:
            conn.execute('DELETE FROM stock_fundamentals')
            conn.execute('DELETE FROM analysis_results')
            conn.execute('DELETE FROM quote_snapshots')
            conn.execute('DELETE FROM market_indicator_snapshots')
            conn.execute('DELETE FROM qualitative_only_securities')
            conn.commit()
            print("已清除全部缓存")


def cmd_checklist(args: list[str]) -> None:
    """打印框架客观指标核对清单：基于缓存的基本面数据逐项核对，不计分、不加总"""
    if len(args) < 2:
        print("用法：cache.py checklist <代码> <框架A|B|C|D|E|F>", file=sys.stderr)
        sys.exit(1)

    code, framework = args[0], args[1]
    from a_stock_agent_runtime import checklist  # 延迟导入：checklist.py 反向依赖 cache，避免模块级循环导入

    try:
        items = checklist.build_checklist(code, framework)
    except (checklist.UnsupportedFrameworkError, checklist.FundamentalsCacheMissingError) as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)

    # build_checklist 已经验证过 framework 合法（否则上面已经 sys.exit 退出），
    # 这里直接下标访问是安全的
    normalized = framework.upper()
    metadata = framework_metadata.FRAMEWORK_REGISTRY[normalized]
    skipped = [{'label': i.label, 'reason': i.reason} for i in metadata.skipped_items]
    print(checklist.format_checklist(items, normalized, code, metadata.subjective_items, skipped))
    if normalized == 'C' and _latest_analysis_missing_cycle_stage(code):
        print("\n⚠️ 提前提示：C资源框架写入分析时必须包含有效的周期位置标签；")
        print('格式：周期位置[阶段=<上行期|顶部区|下行期|底部区>；依据="<依据文本>"]')


def _latest_analysis_missing_cycle_stage(code: str) -> bool:
    with db_session() as conn:
        row = conn.execute(
            'SELECT result FROM analysis_results WHERE code=? ORDER BY date DESC LIMIT 1',
            (code,),
        ).fetchone()
    if not row:
        return True
    return parse_cycle_stage_tag(row[0]) is None


# 供外部 import 的别名（fetcher.py 等可直接 from a_stock_agent_runtime.cache import check）
check = cmd_check

COMMANDS = {
    'check': cmd_check,
    'get': cmd_get,
    'set': cmd_set,
    'get-analysis': cmd_get_analysis,
    'set-analysis': cmd_set_analysis,
    'set-score': cmd_set_score,
    'set-score-breakdown': cmd_set_score_breakdown,
    'set-flag': cmd_set_flag,
    'clear-flag': cmd_clear_flag,
    'alert-open': cmd_alert_open,
    'alert-pending': cmd_alert_pending,
    'alert-resolve': cmd_alert_resolve,
    'alerts': cmd_alerts,
    'l3-add': cmd_l3_add,
    'l3-update': cmd_l3_update,
    'l3-list': cmd_l3_list,
    'tier-config': cmd_tier_config,
    'tier-update': cmd_tier_update,
    'holding-framework': cmd_holding_framework,
    'add-holding': cmd_add_holding,
    'buy-holding': cmd_buy_holding,
    'sell-holding': cmd_sell_holding,
    'record-dividend': cmd_record_dividend,
    'corporate-action': cmd_corporate_action,
    'close-holding': cmd_close_holding,
    'retro-add': cmd_retro_add,
    'retro-pending': cmd_retro_pending,
    'retro-stats': cmd_retro_stats,
    'retro-outliers': cmd_retro_outliers,
    'holdings': cmd_holdings,
    'remove-holding': cmd_remove_holding,
    'update-return': cmd_update_return,
    'position-return': cmd_position_return,
    'portfolio-risk': cmd_portfolio_risk,
    'check-holdings': cmd_check_holdings,
    'watchlist': cmd_watchlist,
    'list': cmd_list,
    'cleanup': cmd_cleanup,
    'clear': cmd_clear,
    'checklist': cmd_checklist,
}

# One source of truth for the side-effect boundary.  R0 is local read-only,
# R1 may refresh/read external data or cache it, and W1 changes investment
# state.  Unknown commands are rejected rather than silently treated as safe.
COMMAND_CLASSIFICATION = {
    **dict.fromkeys(
        (
            'get', 'get-analysis', 'holdings', 'position-return',
            'retro-pending', 'retro-stats', 'retro-outliers',
            'alerts', 'l3-list', 'watchlist', 'list', 'checklist',
        ),
        'R0',
    ),
    **dict.fromkeys(('check', 'check-holdings', 'portfolio-risk'), 'R1'),
    **dict.fromkeys(
        (
            'set', 'set-analysis', 'set-score', 'set-score-breakdown',
            'set-flag', 'clear-flag', 'alert-open', 'alert-pending',
            'alert-resolve', 'l3-add', 'l3-update', 'tier-config',
            'tier-update', 'holding-framework', 'add-holding', 'buy-holding',
            'sell-holding', 'record-dividend', 'corporate-action',
            'close-holding', 'retro-add', 'remove-holding', 'update-return',
            'cleanup', 'clear',
        ),
        'W1',
    ),
}


def main(argv: list[str] | None = None) -> int:
    global _READ_ONLY_REQUEST
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args == ['--help']:
        print(__doc__)
        return 0
    confirm_write = bool(args and args[0] == '--confirm-write')
    if confirm_write:
        args.pop(0)
    if not confirm_write and args and args[0].startswith('--'):
        print('错误：仅支持位于子命令前的全局 --confirm-write', file=sys.stderr)
        return 2
    if not args:
        print(__doc__)
        return 0
    command, remaining = args[0], args[1:]
    classification = COMMAND_CLASSIFICATION.get(command)
    if command not in COMMANDS or classification is None:
        print(f'错误：未知命令 {command}', file=sys.stderr)
        print(__doc__, file=sys.stderr)
        return 1
    if classification == 'W1' and not confirm_write:
        print(
            f'需要明确确认：{command} 将修改本地投资状态；'
            '请在子命令前提供 --confirm-write。',
            file=sys.stderr,
        )
        return 3
    if classification == 'R0' and not os.path.exists(DB_PATH):
        print(f'状态数据库不存在：{DB_PATH}', file=sys.stderr)
        return 0
    print(f'[a-stock-cache] 操作数据库: {DB_PATH}', file=sys.stderr)
    try:
        _READ_ONLY_REQUEST = classification == 'R0'
        COMMANDS[command](remaining)
    except SystemExit as exc:
        return int(exc.code or 0)
    except sqlite3.Error as exc:
        print(f'数据库查询失败：{exc}', file=sys.stderr)
        return 1
    finally:
        _READ_ONLY_REQUEST = False
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
