"""Holding lifecycle, return, and risk commands."""

from __future__ import annotations

import json
import math
import sqlite3
import sys
from datetime import date, datetime

from a_stock_agent_runtime import db, domain, market_quotes, store
from a_stock_agent_runtime.position_ledger import (
    LifecycleReturn,
    calculate_lifecycle_return,
)


def _single_open_holding(conn: sqlite3.Connection, code: str) -> tuple:
    rows = conn.execute(
        """SELECT id, buy_date, framework FROM holdings
           WHERE code=? AND exit_date IS NULL ORDER BY id""",
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


def _load_lifecycle_events(conn: sqlite3.Connection, holding_id: int) -> list[tuple]:
    return conn.execute(
        """SELECT event_type, event_date, shares, price, fees, tax, cash_amount,
                  inferred
           FROM holding_events WHERE holding_id=? ORDER BY event_date, id""",
        (holding_id,),
    ).fetchall()


def _parse_cli_finite_float(
    raw: str,
    label: str,
    *,
    minimum: float | None = None,
    strict_minimum: bool = False,
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
    if minimum is not None and (
        value <= minimum if strict_minimum else value < minimum
    ):
        comparator = f"大于{minimum}" if strict_minimum else f"不小于{minimum}"
        print(f"错误：{label}必须{comparator}", file=sys.stderr)
        sys.exit(1)
    return value


def _validate_event_date_not_before(
    conn: sqlite3.Connection,
    holding_id: int,
    event_date: str,
) -> None:
    """Disallow backdated lifecycle events that would invert cash-flow order."""
    first_row = conn.execute(
        """SELECT MIN(event_date) FROM holding_events
           WHERE holding_id=? AND event_type='buy' """,
        (holding_id,),
    ).fetchone()
    first_buy_date = first_row[0] if first_row else None
    if first_buy_date and event_date < first_buy_date:
        print(f"错误：交易日期不得早于首笔买入日期 {first_buy_date}", file=sys.stderr)
        sys.exit(1)


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
    return PriceQuote(
        price=price, quote_date=quote_date, quote_time=quote_time, source="sina"
    )


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
            result[code] = (
                PriceQuote(price=p, quote_date=None, quote_time=None, source="sina")
                if p is not None
                else None
            )
        return result

    if not codes:
        return {}

    raw = _fetch_sina_batch_quotes(codes)
    return {
        code: (
            PriceQuote(price=v[0], quote_date=v[1], quote_time=v[2], source="sina")
            if v is not None
            else None
        )
        for code, v in raw.items()
    }


def _parse_add_holding_args(
    args: list[str],
) -> tuple[str, float, int | None, str | None, list[str]]:
    if len(args) < 2:
        print("错误：需要参数 <代码> <成本价> [股数] [--notes 备注]", file=sys.stderr)
        sys.exit(1)
    code = args[0]
    cost_price = _parse_cli_finite_float(
        args[1], "成本价", minimum=0, strict_minimum=True
    )
    remaining = args[2:]
    shares = None
    if remaining and not remaining[0].startswith("--"):
        try:
            shares = int(remaining.pop(0))
        except ValueError:
            print("错误：股数必须为整数；备注请使用 --notes", file=sys.stderr)
            sys.exit(1)
    if shares is not None and shares <= 0:
        print("错误：股数必须大于0", file=sys.stderr)
        sys.exit(1)
    notes = None
    trade_options: list[str] = []
    i = 0
    while i < len(remaining):
        if remaining[i] == "--notes":
            if i + 1 >= len(remaining):
                print("错误：--notes 需要参数", file=sys.stderr)
                sys.exit(1)
            notes = remaining[i + 1]
            i += 2
        else:
            trade_options.extend(remaining[i : i + 2])
            i += 2
    return code, cost_price, shares, notes, trade_options


def _a_share_board(code: str) -> tuple[str, int]:
    """Return (board, minimum/integer-lot reference) for executable sizing."""
    if code.startswith("688"):
        return "STAR", 200
    if code.startswith(("4", "8", "920")):
        return "BSE", 100
    return "MAIN", 100


def _validate_buy_quantity(code: str, shares: int) -> str | None:
    board, lot = _a_share_board(code)
    if board == "STAR":
        if shares < lot:
            return f"科创板买入申报不得少于{lot}股"
        return None
    if board == "BSE":
        if shares < lot:
            return f"北交所买入申报不得少于{lot}股"
        return None
    if shares % lot != 0:
        return f"买入申报股数须为{lot}股的整数倍"
    return None


def _validate_sell_quantity(
    code: str, current_shares: int, sell_shares: int
) -> str | None:
    """Validate a sell against board-lot rules while allowing one final odd-lot exit."""
    if sell_shares <= 0:
        return "卖出股数必须大于0"
    if sell_shares > current_shares:
        return f"卖出股数{sell_shares}超过当前持仓{current_shares}"
    if sell_shares == current_shares:
        return None
    board, lot = _a_share_board(code)
    if board == "STAR":
        if sell_shares < lot:
            return f"科创板非清仓卖出申报不得少于{lot}股"
        return None
    if board == "BSE":
        if sell_shares < lot:
            return f"北交所非清仓卖出申报不得少于{lot}股"
        return None
    odd_lot = current_shares % lot
    if sell_shares % lot not in ({0, odd_lot} if odd_lot else {0}):
        return f"当前持仓{current_shares}股时，非清仓卖出须为{lot}股整数倍" + (
            f"或一次性包含全部{odd_lot}股零股" if odd_lot else ""
        )
    return None


def _resolve_holding_framework(
    conn: sqlite3.Connection, code: str
) -> tuple[str, bool, int | None, str | None]:
    score_row = conn.execute(
        "SELECT score, name, framework FROM analysis_results WHERE code=? ORDER BY date DESC LIMIT 1",
        (code,),
    ).fetchone()
    buy_score = score_row[0] if score_row else None
    persisted_framework = score_row[2] if score_row else None
    # 查询股票名称 + 行业（仅在没有持久化framework时才需要industry兜底）
    fund_row = conn.execute(
        "SELECT name, industry FROM stock_fundamentals WHERE code=?", (code,)
    ).fetchone()
    name = (fund_row[0] if fund_row else None) or (
        score_row[1] if score_row and score_row[1] else None
    )
    industry = fund_row[1] if fund_row else None

    if persisted_framework:
        framework, confident = persisted_framework, True
    else:
        framework, confident = domain.infer_framework(industry)
    return framework, confident, buy_score, name


def cmd_add_holding(args: list[str]) -> None:
    """Add a new holding lot and its baseline event; use buy-holding to add shares."""
    code, trade_price, shares, notes, trade_options = _parse_add_holding_args(args)
    fees, tax, buy_date = _parse_trade_options(trade_options, 0)
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
    with db.db_session() as conn:
        conn.execute("BEGIN IMMEDIATE")
        open_count = conn.execute(
            """SELECT COUNT(*) FROM holdings
               WHERE code=? AND exit_date IS NULL""",
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
        sl15_pct, sl20_pct = domain.get_stop_loss_pct(framework)
        stop_loss_15 = round(trade_price * sl15_pct, 3)
        stop_loss_20 = round(trade_price * sl20_pct, 3)

        cursor = conn.execute(
            """INSERT INTO holdings
               (code, name, cost_price, shares, buy_date, buy_score,
                stop_loss_15, stop_loss_20, notes, updated_at, framework, initial_shares,
                main_entry_date, main_entry_basis, additions_since_main, reference_cost,
                framework_confident)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                code,
                name,
                economic_cost,
                shares,
                buy_date,
                buy_score,
                stop_loss_15,
                stop_loss_20,
                notes,
                domain.utc_now_iso(),
                framework,
                shares,
                buy_date,
                economic_cost * shares if shares is not None else None,
                0,
                trade_price,
                int(confident),
            ),
        )
        holding_id = cursor.lastrowid
        if shares is not None:
            conn.execute(
                """INSERT INTO holding_events
                   (holding_id, code, event_type, event_date, shares, price, fees, created_at)
                   VALUES (?, ?, 'buy', ?, ?, ?, ?, ?)""",
                (
                    holding_id,
                    code,
                    buy_date,
                    shares,
                    trade_price,
                    fees,
                    domain.utc_now_iso(),
                ),
            )
        conn.execute(
            """INSERT INTO holding_tier_state (holding_id, updated_at)
               VALUES (?, ?) ON CONFLICT(holding_id) DO NOTHING""",
            (holding_id, domain.utc_now_iso()),
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
    print(
        f"  框架:{framework}{fw_marker}（系数{sl15_pct}/{sl20_pct}） 止损15%:{stop_loss_15}  止损20%:{stop_loss_20}"
    )


def _print_open_holdings(open_rows: list[tuple]) -> None:
    if open_rows:
        unique_open = len(set(r[1] for r in open_rows))
        lot_str = f"，{len(open_rows)} 笔" if len(open_rows) > unique_open else ""
        print(f"\n{'─' * 80}")
        print(f"  在仓持股（{unique_open} 只{lot_str}）")
        print(f"{'─' * 80}")
        print(
            f"  {'股票':<14} {'成本价':>7} {'股数':>6} {'止损15%':>8} {'止损20%':>8} {'得分':>4} {'买入日期':<11} 备注"
        )
        print(f"  {'─' * 74}")
        for r in open_rows:
            _, code, name, cost, shares, buy_date, score, sl15, sl20, notes, _, _ = r
            label = f"{name}({code})" if name else code
            shares_str = str(shares) if shares else "─"
            score_str = str(score) if score else "─"
            notes_str = notes or "─"
            print(
                f"  {label:<14} {cost:>7.3f} {shares_str:>6} {sl15:>8.3f} {sl20:>8.3f} {score_str:>4} {buy_date:<11} {notes_str}"
            )


def _print_closed_holdings(
    closed_rows: list[tuple],
    lifecycle_returns: dict[int, LifecycleReturn],
) -> None:
    if closed_rows:
        print(f"\n{'─' * 80}")
        print(f"  已平仓历史（{len(closed_rows)} 只）")
        print(f"{'─' * 80}")
        print(
            f"  {'股票':<14} {'成本价':>7} {'卖出价':>7} {'盈亏%':>7} {'得分':>4} {'买入':>11} {'卖出':>11} 备注"
        )
        print(f"  {'─' * 74}")
        for r in closed_rows:
            (
                holding_id,
                code,
                name,
                cost,
                shares,
                buy_date,
                score,
                _,
                _,
                notes,
                exit_price,
                exit_date,
            ) = r
            label = f"{name}({code})" if name else code
            score_str = str(score) if score else "─"
            notes_str = notes or "─"
            lifecycle_return = lifecycle_returns.get(holding_id)
            pnl_str = (
                f"{lifecycle_return.total_return_pct:+.1f}%"
                if lifecycle_return is not None
                else "账本缺失"
            )
            print(
                f"  {label:<14} {cost:>7.3f} {exit_price:>7.3f} {pnl_str:>7} {score_str:>4} {buy_date:>11} {exit_date:>11} {notes_str}"
            )

        # 统计：平均盈亏、胜率，帮助验证评分系统有效性
        pnl_list = [item.total_return_pct for item in lifecycle_returns.values()]
        if pnl_list:
            win_rate = round(sum(1 for p in pnl_list if p > 0) / len(pnl_list) * 100)
            avg_pnl = round(sum(pnl_list) / len(pnl_list), 1)
            print(
                f"\n  已平仓统计：胜率 {win_rate}% | 平均盈亏 {avg_pnl:+.1f}% | 有效账本 {len(pnl_list)}/{len(closed_rows)} 笔"
            )
        else:
            print(f"\n  已平仓统计：无可核验事件账本（共 {len(closed_rows)} 笔）")


def cmd_holdings(args: list[str] | None = None) -> None:
    """显示全部持仓，或只显示指定代码的当前/历史持仓。"""
    args = args or []
    compact = "--compact" in args
    json_output = "--json" in args
    active_only = "--active-only" in args
    positionals = [arg for arg in args if not arg.startswith("--")]
    if len(positionals) > 1:
        print("错误：holdings 最多接受一个股票代码", file=sys.stderr)
        sys.exit(1)
    code = positionals[0] if positionals else None
    clauses = []
    params = []
    if code:
        clauses.append("code=?")
        params.append(code)
    if active_only:
        clauses.append("exit_date IS NULL")
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    try:
        with db.read_only_db_session() as conn:
            if compact or json_output:
                rows = conn.execute(
                    """SELECT id, code, name, cost_price, shares, buy_date, buy_score,
                              stop_loss_15, stop_loss_20, exit_price, exit_date,
                              framework, initial_shares, main_entry_date,
                              reference_cost, framework_confident
                       FROM holdings"""
                    + where
                    + " ORDER BY exit_date IS NULL DESC, buy_date DESC",
                    tuple(params),
                ).fetchall()
                records = [
                    {
                        "id": row[0],
                        "code": row[1],
                        "name": row[2],
                        "status": "active" if row[10] is None else "closed",
                        "shares": row[4],
                        "cost_price": row[3],
                        "reference_cost": row[14],
                        "buy_date": row[5],
                        "buy_score": row[6],
                        "framework": row[11],
                        "framework_confident": bool(row[15]),
                        "initial_shares": row[12],
                        "main_entry_date": row[13],
                        "stop_loss_15": row[7],
                        "stop_loss_20": row[8],
                        "exit_price": row[9],
                        "exit_date": row[10],
                    }
                    for row in rows
                ]
                if json_output:
                    print(
                        json.dumps(records, ensure_ascii=False, separators=(",", ":"))
                    )
                elif records:
                    for record in records:
                        print(
                            f"{record['status']} {record['code']}({record['name'] or '─'}) "
                            f"shares={record['shares'] or '─'} framework={record['framework'] or '?'} "
                            f"confident={int(record['framework_confident'])} "
                            f"reference_cost={record['reference_cost'] or '─'} "
                            f"stop1={record['stop_loss_15'] or '─'} "
                            f"stop2={record['stop_loss_20'] or '─'}"
                        )
                else:
                    print(f"NOT_HELD {code}" if code else "暂无持仓记录")
                return
            rows = conn.execute(
                """SELECT id, code, name, cost_price, shares, buy_date, buy_score,
                          stop_loss_15, stop_loss_20, notes, exit_price, exit_date
                   FROM holdings"""
                + where
                + " ORDER BY exit_date IS NULL DESC, buy_date DESC",
                tuple(params),
            ).fetchall()
            lifecycle_returns: dict[int, LifecycleReturn] = {}
            for row in rows:
                holding_id, exit_date = row[0], row[11]
                if exit_date is None:
                    continue
                try:
                    lifecycle_returns[holding_id] = calculate_lifecycle_return(
                        _load_lifecycle_events(conn, holding_id),
                        0,
                        end_date=exit_date,
                    )
                except ValueError:
                    continue
    except sqlite3.OperationalError as exc:
        print(f"HOLDINGS_UNAVAILABLE {exc}", file=sys.stderr)
        sys.exit(1)

    if not rows:
        print(f"NOT_HELD {code}" if code else "暂无持仓记录")
        return

    open_rows = [r for r in rows if r[11] is None]  # exit_date IS NULL
    closed_rows = [r for r in rows if r[11] is not None]

    _print_open_holdings(open_rows)
    _print_closed_holdings(closed_rows, lifecycle_returns)


def _parse_trade_options(args: list[str], start: int) -> tuple[float, float, str]:
    fees = 0.0
    tax = 0.0
    trade_date = domain.cst_today()
    i = start
    while i < len(args):
        if args[i] not in ("--fee", "--tax", "--date") or i + 1 >= len(args):
            print(f"错误：未知或不完整参数 {args[i]}", file=sys.stderr)
            sys.exit(1)
        value = args[i + 1]
        if args[i] == "--date":
            try:
                date.fromisoformat(value)
            except ValueError:
                print("错误：日期必须为 YYYY-MM-DD", file=sys.stderr)
                sys.exit(1)
            trade_date = value
        else:
            label = "费用" if args[i] == "--fee" else "税费"
            amount = _parse_cli_finite_float(value, label, minimum=0)
            if args[i] == "--fee":
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
    buy_price = _parse_cli_finite_float(
        args[1], "买入价", minimum=0, strict_minimum=True
    )
    quantity_error = _validate_buy_quantity(code, buy_shares)
    if quantity_error:
        print(f"错误：{quantity_error}", file=sys.stderr)
        sys.exit(1)
    fees, tax, trade_date = _parse_trade_options(args, 3)
    if tax:
        print("错误：买入事件不接受 --tax，请仅记录实际买入费用 --fee", file=sys.stderr)
        sys.exit(1)
    with db.db_session() as conn:
        conn.execute("BEGIN IMMEDIATE")
        holding_id, _, framework = _single_open_holding(conn, code)
        _validate_event_date_not_before(conn, holding_id, trade_date)
        row = conn.execute(
            """SELECT cost_price, shares, stop_loss_15, stop_loss_20,
                      main_entry_date, main_entry_basis, additions_since_main,
                      reference_cost
               FROM holdings WHERE id=?""",
            (holding_id,),
        ).fetchone()
        (
            cost_price,
            old_shares,
            _,
            _,
            main_date,
            main_basis,
            additions,
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
        sl15_pct, sl20_pct = domain.get_stop_loss_pct(framework or "A通用")
        additions = (additions or 0) + added_cash
        main_basis = main_basis or old_book_cost
        if additions > main_basis * 0.5:
            main_date = trade_date
            main_basis = old_book_cost + added_cash
            additions = 0
        now_iso = domain.utc_now_iso()
        conn.execute(
            """UPDATE holdings
               SET cost_price=?, shares=?, stop_loss_15=?, stop_loss_20=?,
                   main_entry_date=?, main_entry_basis=?,
                   additions_since_main=?, reference_cost=?, updated_at=?
               WHERE id=?""",
            (
                new_cost,
                new_shares,
                round(new_reference_cost * sl15_pct, 3),
                round(new_reference_cost * sl20_pct, 3),
                main_date,
                main_basis,
                additions,
                new_reference_cost,
                now_iso,
                holding_id,
            ),
        )
        conn.execute(
            """INSERT INTO holding_events
               (holding_id, code, event_type, event_date, shares, price, fees, created_at)
               VALUES (?, ?, 'buy', ?, ?, ?, ?, ?)""",
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
    exit_price = _parse_cli_finite_float(
        args[1], "卖出价", minimum=0, strict_minimum=True
    )
    requested = args[2].lower()
    if requested != "all":
        try:
            requested_shares = int(requested)
        except ValueError:
            print("错误：卖出股数必须为正整数或 all", file=sys.stderr)
            sys.exit(1)
    else:
        requested_shares = None
    fees, tax, exit_date = _parse_trade_options(args, 3)

    with db.db_session() as conn:
        conn.execute("BEGIN IMMEDIATE")
        lot_limit = " LIMIT 1" if single_lot else ""
        lots = conn.execute(
            """SELECT id, cost_price, shares, buy_date
               FROM holdings
               WHERE code=? AND exit_date IS NULL
               ORDER BY buy_date ASC, id ASC"""
            + lot_limit,
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
        now_iso = domain.utc_now_iso()
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
                    """UPDATE holdings
                       SET shares=0, exit_price=?, exit_date=?, updated_at=?
                       WHERE id=?""",
                    (exit_price, exit_date, now_iso, holding_id),
                )
            else:
                conn.execute(
                    "UPDATE holdings SET shares=?, updated_at=? WHERE id=?",
                    (new_shares, now_iso, holding_id),
                )
            conn.execute(
                """INSERT INTO holding_events
                   (holding_id, code, event_type, event_date, shares, price,
                    fees, tax, realized_pnl, created_at)
                   VALUES (?, ?, 'sell', ?, ?, ?, ?, ?, ?, ?)""",
                (
                    holding_id,
                    code,
                    exit_date,
                    sold,
                    exit_price,
                    allocated_fee,
                    allocated_tax,
                    realized,
                    now_iso,
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
    cash_amount = _parse_cli_finite_float(args[1], "现金总额", minimum=0)
    event_date = args[2] if len(args) > 2 else domain.cst_today()
    try:
        date.fromisoformat(event_date)
    except ValueError:
        print("错误：日期必须为 YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)
    with db.db_session() as conn:
        row = conn.execute(
            """SELECT id FROM holdings
               WHERE code=? AND exit_date IS NULL
               ORDER BY buy_date ASC, id ASC LIMIT 1""",
            (code,),
        ).fetchone()
        if not row:
            print(f"错误：未找到 {code} 的在仓记录", file=sys.stderr)
            sys.exit(1)
        _validate_event_date_not_before(conn, row[0], event_date)
        conn.execute(
            """INSERT INTO holding_events
               (holding_id, code, event_type, event_date, cash_amount, created_at)
               VALUES (?, ?, 'dividend', ?, ?, ?)""",
            (row[0], code, event_date, cash_amount, domain.utc_now_iso()),
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
    dps = _parse_cli_finite_float(args[1], "分红", minimum=0)
    split_ratio = _parse_cli_finite_float(args[2], "转增比例", minimum=0)
    action_date = args[3] if len(args) > 3 else domain.cst_today()
    try:
        date.fromisoformat(action_date)
    except ValueError:
        print("错误：日期必须为 YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)
    with db.db_session() as conn:
        conn.execute("BEGIN IMMEDIATE")
        holding_id, _, framework = _single_open_holding(conn, code)
        row = conn.execute(
            """SELECT cost_price, reference_cost, shares, initial_shares
               FROM holdings WHERE id=?""",
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
            print(
                "错误：转增后股数不是整数，请使用实际到账股数人工核对", file=sys.stderr
            )
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
        sl15_pct, sl20_pct = domain.get_stop_loss_pct(framework or "A通用")
        dividend_cash = dps * old_shares
        now_iso = domain.utc_now_iso()
        conn.execute(
            """UPDATE holdings
               SET cost_price=?, reference_cost=?, shares=?, initial_shares=?,
                   stop_loss_15=?, stop_loss_20=?, updated_at=?
               WHERE id=?""",
            (
                new_economic_cost,
                new_reference_cost,
                new_shares,
                new_initial_shares,
                round(new_reference_cost * sl15_pct, 3),
                round(new_reference_cost * sl20_pct, 3),
                now_iso,
                holding_id,
            ),
        )
        if dividend_cash:
            conn.execute(
                """INSERT INTO holding_events
                   (holding_id, code, event_type, event_date, cash_amount, created_at)
                   VALUES (?, ?, 'dividend', ?, ?, ?)""",
                (holding_id, code, action_date, dividend_cash, now_iso),
            )
        conn.execute(
            """INSERT INTO holding_events
               (holding_id, code, event_type, event_date, shares, price,
                notes, created_at)
               VALUES (?, ?, 'adjustment', ?, ?, ?, ?, ?)""",
            (
                holding_id,
                code,
                action_date,
                new_shares - old_shares,
                new_reference_cost,
                f"dps={dps};split_ratio={split_ratio}",
                now_iso,
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
    exit_price = _parse_cli_finite_float(
        args[1], "卖出价", minimum=0, strict_minimum=True
    )
    exit_date = args[2] if len(args) > 2 else domain.cst_today()
    try:
        date.fromisoformat(exit_date)
    except ValueError:
        print("错误：日期必须为 YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    with db.db_session() as conn:
        row = conn.execute(
            """SELECT id, cost_price, name, buy_score, shares, buy_date FROM holdings
               WHERE code=? AND exit_date IS NULL
               ORDER BY buy_date ASC, id ASC LIMIT 1""",
            (code,),
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
            [code, str(exit_price), "all", "--date", exit_date],
            single_lot=True,
        )
    else:
        # Older price-only positions cannot be reconstructed into a cash-flow
        # ledger.  Keep the historical close capability, but clear shares so a
        # closed row can never be valued as an open position.
        with db.db_session() as conn:
            conn.execute("BEGIN IMMEDIATE")
            legacy_row = conn.execute(
                """SELECT id, cost_price, name, buy_score, buy_date FROM holdings
                   WHERE code=? AND exit_date IS NULL AND (shares IS NULL OR shares <= 0)
                   ORDER BY buy_date ASC, id ASC LIMIT 1""",
                (code,),
            ).fetchone()
            if legacy_row is None:
                conn.rollback()
                print(f"错误：未找到 {code} 的在仓记录", file=sys.stderr)
                sys.exit(1)
            lot_id, cost_price, name, buy_score, legacy_buy_date = legacy_row
            if legacy_buy_date and exit_date < legacy_buy_date:
                conn.rollback()
                print(
                    f"错误：卖出日期不得早于买入日期 {legacy_buy_date}", file=sys.stderr
                )
                sys.exit(1)
            cursor = conn.execute(
                """UPDATE holdings SET shares=0, exit_price=?, exit_date=?, updated_at=?
                   WHERE id=? AND exit_date IS NULL""",
                (exit_price, exit_date, domain.utc_now_iso(), lot_id),
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
        print(
            "  ⚠️ 该旧持仓缺少股数，无法补建可审计卖出现金流；不得用于事件账本收益统计"
        )
    print("─" * 50)
    print(f"  复盘提示：a-stock-cache retro-add {code} <标签>")
    print("  可选标签：ROE高估 | 周期顶部 | 估值倍杀 | 护城河失守 | 行业误判 | 无错误")


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
        if flag in ("--note", "--thesis", "--gap"):
            if i + 1 >= len(args):
                print(f"错误：{flag} 需要参数", file=sys.stderr)
                sys.exit(1)
            if flag == "--note":
                retro_text = args[i + 1]
            elif flag == "--thesis":
                thesis_notes = args[i + 1]
            else:
                framework_gap = args[i + 1]
            i += 2
        else:
            print(f"错误：未知参数 {flag}", file=sys.stderr)
            sys.exit(1)

    with db.db_session() as conn:
        row = conn.execute(
            """SELECT h.id, h.code, h.name, h.buy_date, h.buy_score,
                      h.exit_date,
                      COALESCE(h.framework, (
                        SELECT framework FROM analysis_results a
                        WHERE a.code = h.code
                        ORDER BY a.date DESC LIMIT 1
                      )) AS framework
               FROM holdings h
               LEFT JOIN retro_notes r ON h.id = r.holding_id
               WHERE h.code=? AND h.exit_date IS NOT NULL AND r.id IS NULL
               ORDER BY h.exit_date DESC LIMIT 1""",
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
            """INSERT INTO retro_notes
               (holding_id, code, name, framework, buy_date, exit_date, buy_score,
                actual_return_pct, holding_days, error_tags, thesis_notes, retro_text,
                framework_gap, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                holding_id,
                code,
                name,
                framework,
                buy_date,
                exit_date,
                buy_score,
                actual_return_pct,
                holding_days,
                error_tags,
                thesis_notes,
                retro_text,
                framework_gap,
                domain.utc_now_iso(),
            ),
        )
        conn.commit()

    inferred_note = (
        "（含推断历史，须核对券商流水）" if lifecycle_return.contains_inferred else ""
    )
    print(
        f"复盘已记录：{code} | 标签:{error_tags} | 实际回报:{actual_return_pct:+.1f}%{inferred_note}"
    )


def cmd_retro_pending(args: list[str] | None = None) -> None:
    """显示已平仓但尚未复盘的记录。用法：retro-pending"""
    with db.read_only_db_session() as conn:
        rows = conn.execute(
            """SELECT h.id, h.code, h.name, h.exit_date, h.buy_score
               FROM holdings h
               LEFT JOIN retro_notes r ON h.id = r.holding_id
               WHERE h.exit_date IS NOT NULL AND r.id IS NULL
               ORDER BY h.exit_date DESC"""
        ).fetchall()

        rendered_rows: list[
            tuple[str, str | None, str, int | None, LifecycleReturn | None, str | None]
        ] = []
        for holding_id, code, name, exit_date, buy_score in rows:
            try:
                lifecycle_return = calculate_lifecycle_return(
                    _load_lifecycle_events(conn, holding_id),
                    0,
                    end_date=exit_date,
                )
                rendered_rows.append(
                    (code, name, exit_date, buy_score, lifecycle_return, None)
                )
            except ValueError as exc:
                rendered_rows.append((code, name, exit_date, buy_score, None, str(exc)))

    if not rendered_rows:
        print("无待复盘记录")
        return

    for code, name, exit_date, buy_score, lifecycle_return, error in rendered_rows:
        name_str = name or "─"
        score_str = str(buy_score) if buy_score is not None else "─"
        if lifecycle_return is None:
            print(
                f"{code} {name_str} 平仓日期:{exit_date} 账本不完整:{error} 买入得分:{score_str}"
            )
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

    with db.db_session() as conn:
        rows = conn.execute(
            f"""SELECT actual_return_pct, error_tags
                FROM retro_notes
                {where}""",
            params,
        ).fetchall()

    if not rows:
        print("暂无复盘记录")
        return

    returns = [r[0] for r in rows if r[0] is not None]
    total = len(rows)
    win_rate = (
        round(sum(1 for value in returns if value > 0) / len(returns) * 100, 1)
        if returns
        else 0.0
    )
    avg_return = round(sum(returns) / len(returns), 1) if returns else 0.0

    tag_counts: dict[str, int] = {}
    for _, tags in rows:
        if not tags:
            continue
        for tag in tags.split(","):
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
        if args[i] == "--loss":
            if i + 1 >= len(args):
                print("错误：--loss 需要参数", file=sys.stderr)
                sys.exit(1)
            threshold = -abs(_parse_cli_finite_float(args[i + 1], "--loss"))
            i += 2
        else:
            print(f"错误：未知参数 {args[i]}", file=sys.stderr)
            sys.exit(1)

    with db.read_only_db_session() as conn:
        rows = conn.execute(
            """SELECT h.id, h.code, h.name, h.exit_date, h.buy_score
               FROM holdings h
               LEFT JOIN retro_notes r ON h.id = r.holding_id
               WHERE h.exit_date IS NOT NULL
                 AND r.id IS NULL
               ORDER BY h.exit_date DESC""",
        ).fetchall()
        outliers: list[tuple[str, str | None, str, LifecycleReturn]] = []
        for holding_id, code, name, exit_date, _buy_score in rows:
            try:
                lifecycle_return = calculate_lifecycle_return(
                    _load_lifecycle_events(conn, holding_id),
                    0,
                    end_date=exit_date,
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
        outliers,
        key=lambda item: item[3].total_return_pct,
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
    with db.db_session() as conn:
        conn.execute("BEGIN IMMEDIATE")
        holding_ids = [
            row[0]
            for row in conn.execute(
                "SELECT id FROM holdings WHERE code=?",
                (code,),
            ).fetchall()
        ]
        if not holding_ids:
            conn.rollback()
            print(f"未找到持仓记录：{code}", file=sys.stderr)
            sys.exit(1)
        placeholders = ",".join("?" for _ in holding_ids)
        for table in (
            "holding_events",
            "holding_l3_conditions",
            "holding_thesis_versions",
            "holding_tier_state",
            "holding_alerts",
            "retro_notes",
        ):
            conn.execute(
                f"DELETE FROM {table} WHERE holding_id IN ({placeholders})",
                holding_ids,
            )
        deleted = conn.execute("DELETE FROM holdings WHERE code=?", (code,)).rowcount
        conn.commit()
    if deleted:
        print(f"已移除持仓：{code}")


def cmd_update_return(args: list[str]) -> None:
    """卖出后记录实际回报。用法：update-return <代码> <实际回报%>"""
    if len(args) < 2:
        print("错误：需要参数 <代码> <实际回报%>", file=sys.stderr)
        sys.exit(1)
    code = args[0]
    return_pct = _parse_cli_finite_float(args[1], "回报率")

    with db.db_session() as conn:
        row = conn.execute(
            "SELECT date FROM analysis_results WHERE code=? ORDER BY date DESC LIMIT 1",
            (code,),
        ).fetchone()
        if not row:
            print(
                f"错误：未找到 {code} 的分析结论记录，请先执行 set-analysis",
                file=sys.stderr,
            )
            sys.exit(1)

        analysis_date = row[0]
        holding_row = conn.execute(
            """SELECT buy_date FROM holdings
               WHERE code=?
               ORDER BY CASE WHEN exit_date IS NULL THEN 0 ELSE 1 END,
                        COALESCE(exit_date, '9999-12-31') DESC, id DESC
               LIMIT 1""",
            (code,),
        ).fetchone()
        try:
            from datetime import date as _date

            start_date = (
                holding_row[0] if holding_row and holding_row[0] else analysis_date
            )
            holding_days = (_date.today() - _date.fromisoformat(start_date)).days
        except Exception:
            holding_days = None

        conn.execute(
            "UPDATE analysis_results SET return_pct=?, holding_days=? WHERE code=? AND date=?",
            (return_pct, holding_days, code, analysis_date),
        )
        conn.commit()
        meta = conn.execute(
            "SELECT name, score FROM analysis_results WHERE code=? AND date=?",
            (code, analysis_date),
        ).fetchone()

    name_str = f"({meta[0]})" if meta and meta[0] else ""
    score_str = f" 买入得分:{meta[1]}/80" if meta and meta[1] else ""
    sign = "+" if return_pct >= 0 else ""
    print(f"✅ 回报已记录：{code}{name_str}{score_str}")
    print(
        f"  分析日期:{analysis_date} | 持有:{holding_days}天 | 实际回报:{sign}{return_pct}%"
    )


def cmd_position_return(args: list[str]) -> None:
    """Calculate cash-flow return for the current, or latest closed, position lifecycle."""
    if not args:
        print("错误：需要参数 <代码> [当前价]", file=sys.stderr)
        sys.exit(1)
    code = args[0]
    current_price = None
    if len(args) > 1:
        current_price = _parse_cli_finite_float(
            args[1],
            "当前价",
            minimum=0,
            strict_minimum=True,
        )
    with db.db_session() as conn:
        open_rows = conn.execute(
            """SELECT id, shares, exit_date FROM holdings
               WHERE code=? AND exit_date IS NULL ORDER BY id""",
            (code,),
        ).fetchall()
        if len(open_rows) > 1:
            print(
                f"错误：{code} 有{len(open_rows)}条在仓记录；"
                "无法确定应计算哪个持仓生命周期",
                file=sys.stderr,
            )
            sys.exit(1)
        lifecycle = (
            open_rows[0]
            if open_rows
            else conn.execute(
                """SELECT id, shares, exit_date FROM holdings
               WHERE code=? AND exit_date IS NOT NULL
               ORDER BY exit_date DESC, id DESC LIMIT 1""",
                (code,),
            ).fetchone()
        )
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
    last_day = domain.cst_today() if remaining_shares else (exit_date or events[-1][1])
    try:
        lifecycle_return = calculate_lifecycle_return(
            events,
            remaining_shares,
            end_date=last_day,
            current_price=current_price,
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
        print(
            "  ⚠️ 含旧持仓推断事件：历史费用、分红或部分交易可能缺失，须与券商流水核对"
        )


def _parse_portfolio_risk_args(args: list[str] | None) -> tuple[float | None, float]:
    portfolio_value = None
    max_position_risk_pct = 2.0
    args = args or []
    i = 0
    while i < len(args):
        if args[i] not in (
            "--portfolio-value",
            "--max-position-risk-pct",
        ) or i + 1 >= len(args):
            print(f"错误：未知或不完整参数 {args[i]}", file=sys.stderr)
            sys.exit(1)
        value = _parse_cli_finite_float(
            args[i + 1],
            args[i],
            minimum=0,
            strict_minimum=True,
        )
        if args[i] == "--portfolio-value":
            portfolio_value = value
        else:
            max_position_risk_pct = value
        i += 2
    return portfolio_value, max_position_risk_pct


def cmd_portfolio_risk(args: list[str] | None = None) -> None:
    """Market-value weighted portfolio view with explicit stop-loss risk budget."""
    portfolio_value, max_position_risk_pct = _parse_portfolio_risk_args(args)
    account_value_supplied = portfolio_value is not None
    with db.db_session() as conn:
        holdings = conn.execute(
            """SELECT h.code, h.name, h.cost_price, h.shares, h.buy_date, h.buy_score,
                      f.industry, h.framework, h.framework_confident, h.stop_loss_20
               FROM holdings h LEFT JOIN stock_fundamentals f ON h.code = f.code
               WHERE h.exit_date IS NULL ORDER BY h.buy_date DESC"""
        ).fetchall()
    if not holdings:
        print("暂无持仓")
        return

    print(f"\n{'─' * 104}")
    print(f"  组合风险视图  现价查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'─' * 104}")

    codes = [h[0] for h in holdings]
    quotes = fetch_current_price_quotes(codes)
    today_str = domain.cst_today()
    valued_rows = []
    for (
        code,
        name,
        cost,
        shares,
        buy_date,
        score,
        industry,
        holding_framework,
        framework_confident,
        sl20,
    ) in holdings:
        if holding_framework:
            fw, confident = holding_framework, bool(framework_confident)
        else:
            fw, confident = domain.infer_framework(industry)
        quote = quotes.get(code)
        curr = quote.price if quote and quote.quote_date == today_str else None
        market_value = curr * shares if curr and shares else None
        valued_rows.append(
            (code, name, cost, shares, score, fw, confident, sl20, curr, market_value)
        )

    stock_market_value = sum(row[9] for row in valued_rows if row[9] is not None)
    valued_count = sum(row[9] is not None for row in valued_rows)
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
    print(f"  {'─' * 100}")

    framework_values: dict[str, float] = {}
    total_stop_risk = 0.0
    for (
        code,
        name,
        cost,
        shares,
        score,
        fw,
        confident,
        sl20,
        curr,
        market_value,
    ) in valued_rows:
        fw_display = fw if confident else f"{fw}?"
        label = f"{name}({code})" if name else code
        pnl_str = f"{(curr - cost) / cost * 100:+.1f}%" if curr and cost else "─"
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
            "已破线"
            if sl20 is not None and curr <= sl20
            else "临时口径"
            if not account_value_supplied
            else "超预算"
            if risk_pct is not None and risk_pct > max_position_risk_pct
            else "正常"
        )
        print(
            f"  {label:<16} {fw_display:>5} {shares_str:>6} {curr_str:>7} "
            f"{weight_pct:>7.1f}% {pnl_str:>7} {risk_str:>9} {risk_pct_str:>8} {status:>5}"
        )

    if account_value_supplied:
        weight_label = "股票总仓位" if valued_count == len(holdings) else "已取价股票仓位（下限）"
        risk_summary = f"{weight_label}：{stock_market_value / portfolio_value * 100:.1f}%"
        risk_pct_label = "占组合总资产"
    else:
        risk_summary = f"已取价股票市值：{stock_market_value:.2f}元（非账户总仓位）"
        risk_pct_label = "占已取价股票市值，临时口径"
    print(
        f"\n  {risk_summary} | 第二档止损总风险：{total_stop_risk:.2f}元 "
        f"({total_stop_risk / portfolio_value * 100:.2f}%，{risk_pct_label})"
    )
    print(f"  行情覆盖：{valued_count}/{len(holdings)}只")
    if account_value_supplied:
        print(f"  单股风险预算上限：{max_position_risk_pct:.2f}%")
    else:
        print("  未提供总资产：不判定预算超限")
    print(f"\n  框架分布（按市值，{len(holdings)} 只在仓）")
    for fw, value in sorted(framework_values.items()):
        print(f"    {fw}: {value:.2f}元 ({value / portfolio_value * 100:.1f}%)")
    print()


def cmd_check_holdings(args: list[str] | None = None) -> None:
    """持仓止损检查：对比当前价与15%/20%止损线，主动预警（P3-4）。
    区分盘中现价/收盘价/上一交易日陈旧行情三种口径，非交易时段拿到隔夜收盘价
    时只输出观察提醒、不触发同等级止损预警（见 PITFALLS.md [BUG-006]）。
    """
    with db.db_session() as conn:
        holdings = conn.execute(
            """SELECT id, code, name, cost_price, stop_loss_15, stop_loss_20
               FROM holdings WHERE exit_date IS NULL ORDER BY code"""
        ).fetchall()
        defer_rows = conn.execute(
            """SELECT holding_id, evidence, review_due
               FROM holding_alerts
               WHERE reason_code='price_stop2_liquidity_defer'
                 AND status != 'resolved'"""
        ).fetchall()
    if not holdings:
        print("暂无持仓")
        return

    now = domain.cst_now()
    today_str = now.strftime("%Y-%m-%d")

    print(f"\n{'─' * 72}")
    print(f"  持仓止损检查  现价查询时间: {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"{'─' * 72}")

    codes = [h[1] for h in holdings]
    quotes = fetch_current_price_quotes(codes)
    market_snapshot = market_quotes.fetch_market_limit_down_snapshot()
    existing_defers = {}
    for holding_id, evidence, review_due in defer_rows:
        try:
            parsed = json.loads(evidence) if evidence else {}
        except (TypeError, json.JSONDecodeError):
            parsed = {}
        if isinstance(parsed, dict):
            existing_defers[holding_id] = {
                key: value
                for key, value in {
                    "defer_started_at": parsed.get("defer_started_at"),
                    "review_due": parsed.get("review_due") or review_due,
                    "original_price": parsed.get("original_price"),
                    "original_stop_loss_20": parsed.get("original_stop_loss_20"),
                }.items()
                if value is not None
            }

    alerts = []
    governance_alerts = []
    for holding_id, code, name, _cost, sl15, sl20 in holdings:
        label, status, is_alert = domain.evaluate_holding_status(
            code, name, sl15, sl20, quotes.get(code), today_str, now
        )
        fundamentals = store.get_fundamentals(code)
        gate_values = (
            [
                fundamentals.get(name)
                for name in ("regulatory_gate", "roe_structural_gate", "cash_flow_gate")
            ]
            if fundamentals
            else []
        )
        failed_gates = [
            gate
            for gate in gate_values
            if isinstance(gate, dict)
            and gate.get("status") not in {"clear", "not_applicable"}
        ]
        if failed_gates:
            reasons = ", ".join(
                str(gate.get("reason_code", "incomplete")) for gate in failed_gates
            )
            governance_alerts.append((label, reasons))
            status += f" | 🔴 风险门冻结加仓({reasons})"
        quote = quotes.get(code)
        existing_defer = existing_defers.get(holding_id)
        p3 = domain.evaluate_liquidity_shock(
            {
                "stop_loss_triggered": bool(
                    existing_defer or is_alert and quote and quote.price <= sl20
                ),
                "stop_loss_20": sl20,
                "quote": {
                    "price": quote.price,
                    "source": quote.source,
                    "suspended": quote.suspended,
                    "limit_down_locked": quote.limit_down_locked,
                    "trading_status": quote.trading_status,
                }
                if quote
                else {},
                "market_snapshot": market_snapshot,
                "existing_defer": existing_defer,
                "now": now,
            }
        )
        if p3["status"] in {"deferred", "untradeable", "incomplete"}:
            status = status.replace("建议立即止损", "暂不可执行")
            status += f" | P3:{p3['status']}({p3['reason_code']})"
            is_alert = True
        if is_alert:
            alerts.append((label, status))
        print(f"  {label:<16} {status}")

    print()
    if alerts:
        print(f"  共 {len(alerts)} 项预警，请及时处理：")
        for label, status in alerts:
            print(f"    {label}: {status}")
    if governance_alerts:
        print(f"  共 {len(governance_alerts)} 项风险门复核，已冻结新增风险敞口：")
        for label, reasons in governance_alerts:
            print(f"    {label}: {reasons}（不自动卖出/清仓）")
    if not alerts and not governance_alerts:
        print("  无预警，所有持仓价格在止损线之上")
    print()
