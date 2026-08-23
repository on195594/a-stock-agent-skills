"""Analysis and fundamentals cache commands."""

from __future__ import annotations

import json
import math
import re
import sqlite3
import sys
from dataclasses import asdict
from datetime import timedelta

from a_stock_agent_runtime import db, domain, store
from a_stock_lib.contracts import (
    FrameworkKey,
    parse_cycle_stage_tag,
    parse_subjective_assessment_tags,
    required_subjective_categories,
)
from a_stock_lib.framework_scoring import score_fundamentals

_VALUATION_CONFLICT_RE = re.compile(
    r'估值冲突\[状态=待核实；PB结论="[^"]+"；交叉估值结论="[^"]+"\]'
)


def cmd_check(args: list[str]) -> None:
    """一次性检查分析结论+基本面缓存，输出状态码+内容"""
    if len(args) < 1:
        print("FULL_MISS")
        return
    code = args[0]
    today = domain.cst_today()

    # 优先检查今日分析结论
    with db.db_session() as conn:
        analysis_row = conn.execute(
            """SELECT result, created_at, name, quote_price
               FROM analysis_results WHERE code=? AND date=?""",
            (code, today),
        ).fetchone()
        if analysis_row:
            result, created_at, name, analysis_quote = analysis_row
            latest_quote = store.get_latest_quote_snapshot(
                code, max_age=store.QUOTE_SNAPSHOT_MAX_AGE
            )
            signed_deviation = None
            absolute_deviation = None
            if latest_quote is not None and analysis_quote:
                signed_deviation = (
                    latest_quote["price"] - analysis_quote
                ) / analysis_quote
                absolute_deviation = abs(signed_deviation)
            if latest_quote is None or not analysis_quote:
                print(
                    f"ANALYSIS_PRICE_STALE {code} 缺少新鲜行情或分析价格快照，需要重新分析"
                )
            elif (
                absolute_deviation is not None
                and signed_deviation is not None
                and absolute_deviation < domain.ANALYSIS_PRICE_INVALIDATION_THRESHOLD
            ):
                name_str = f"({name})" if name else ""
                quote_note = (
                    f" 最新报价:{latest_quote['price']:.3f}({latest_quote['source']})"
                    f" 较分析快照:{signed_deviation * 100:+.2f}%"
                )
                print(
                    f"ANALYSIS_HIT {code}{name_str} [{domain.format_timestamp_cst(created_at)}]{quote_note}"
                )
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
            "SELECT name, industry, data, updated_at, ttl_hours FROM stock_fundamentals WHERE code=?",
            (code,),
        ).fetchone()

    if fund_row:
        name, industry, data, updated_at, ttl_hours = fund_row
        if not domain.is_expired(updated_at, ttl_hours):
            result = store.add_market_indicators(json.loads(data))
            result["_cache_meta"] = {
                "code": code,
                "name": name,
                "industry": industry,
                "updated_at": domain.format_timestamp_cst(updated_at),
                "ttl_hours": ttl_hours,
            }
            print(
                f"FUNDAMENTALS_HIT {code}({name}) [{industry}] 更新:{domain.format_timestamp_cst(updated_at)}"
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

    print("FULL_MISS")


def cmd_get(args: list[str]) -> None:
    """获取基本面缓存，未命中或过期返回 CACHE_MISS"""
    if len(args) < 1:
        print("CACHE_MISS")
        return
    code = args[0]
    with db.db_session() as conn:
        row = conn.execute(
            "SELECT name, industry, data, updated_at, ttl_hours FROM stock_fundamentals WHERE code=?",
            (code,),
        ).fetchone()
    if not row:
        print("CACHE_MISS")
        return
    name, industry, data, updated_at, ttl_hours = row
    if domain.is_expired(updated_at, ttl_hours):
        print("CACHE_MISS")
        return
    result = store.add_market_indicators(json.loads(data))
    result["_cache_meta"] = {
        "code": code,
        "name": name,
        "industry": industry,
        "updated_at": domain.format_timestamp_cst(updated_at),
        "ttl_hours": ttl_hours,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_set(args: list[str]) -> None:
    """② 写入基本面数据。TTL 未指定时按行业自动推断。"""
    if len(args) < 4:
        print("错误：需要参数 <代码> <名称> <行业> <JSON数据> [TTL]", file=sys.stderr)
        sys.exit(1)
    code, name, industry, data_str = args[0], args[1], args[2], args[3]
    # TTL：显式指定 > 行业推断
    ttl_hours = int(args[4]) if len(args) > 4 else domain.get_industry_ttl(industry)
    try:
        data = json.loads(data_str)
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}", file=sys.stderr)
        sys.exit(1)
    validation_error = store.validate_fundamentals_payload(data)
    if validation_error:
        print(f"基本面数据校验错误: {validation_error}", file=sys.stderr)
        sys.exit(1)
    with db.db_session() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO stock_fundamentals
               (code, name, industry, data, updated_at, ttl_hours)
               VALUES (?,?,?,?,?,?)""",
            (
                code,
                name,
                industry,
                json.dumps(data, ensure_ascii=False),
                domain.utc_now_iso(),
                ttl_hours,
            ),
        )
        conn.commit()
    print(f"已缓存 {name}({code}) 行业:{industry} TTL:{ttl_hours}h")


def cmd_get_analysis(args: list[str]) -> None:
    """获取今日分析结论缓存，未命中返回 CACHE_MISS"""
    if len(args) < 1:
        print("CACHE_MISS")
        return
    code = args[0]
    today = domain.cst_today()
    with db.db_session() as conn:
        row = conn.execute(
            "SELECT result, created_at FROM analysis_results WHERE code=? AND date=?",
            (code, today),
        ).fetchone()
    if not row:
        print("CACHE_MISS")
        return
    result, created_at = row
    print(f"[缓存命中 {domain.format_timestamp_cst(created_at)}]\n{result}")


def _parse_set_analysis_args(args: list[str]) -> tuple[str, int | None, str]:
    """Strictly parse framework and optional score without silent ignores."""
    if not args:
        print("错误：需要参数 <代码> <框架> [得分]", file=sys.stderr)
        sys.exit(1)
    code = args[0]
    score: int | None = None
    framework: str | None = None
    for token in args[1:]:
        if token in domain.FRAMEWORK_ALIASES:
            normalized = domain.FRAMEWORK_ALIASES[token]
            if framework is not None:
                message = "冲突框架" if normalized != framework else "重复框架"
                print(f"错误：{message}参数 {token}", file=sys.stderr)
                sys.exit(1)
            framework = normalized
            continue
        if re.fullmatch(r"-?\d+", token):
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
        "SELECT name FROM stock_fundamentals WHERE code=?", (code,)
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
        labels = "、".join(sorted(category.value for category in missing))
        print(
            f"错误：{framework}报告缺少必需主观标签：{labels}，拒绝写入缓存。",
            file=sys.stderr,
        )
        print(
            '格式要求：<类别>[评级=<优|格>；证据="<证据1>";"<证据2>";置信度=<高|中|低>]。',
            file=sys.stderr,
        )
        sys.exit(1)
    return result


def _validate_cycle_stage_for_framework(result: str, framework: str) -> None:
    """C/B/D框架均fail-closed（2026-07-01：用户明确选择跳过观察期，B/D与C同步切换）；
    A/E/F框架不校验（周期判断对它们是可选项）。
    """
    # framework 传入的是 portfolio_label 全称（如 "C资源"/"B银行"/"D公用"），
    # 不是裸字母，取首字符判断框架类型（与 checklist.py 的裸字母约定不同）。
    letter = framework[0].upper()
    if letter not in ("B", "C", "D"):
        return
    assessment = parse_cycle_stage_tag(result)
    if assessment is not None:
        return
    print(
        f"错误：{framework}框架报告中未找到有效的周期位置结构化标签，拒绝写入缓存。",
        file=sys.stderr,
    )
    print(
        '格式要求：周期位置[阶段=<上行期|顶部区|下行期|底部区>；依据="<依据文本>"]，依据文本须用ASCII双引号。',
        file=sys.stderr,
    )
    sys.exit(1)


def cmd_score_fundamentals(args: list[str]) -> None:
    """用 a-stock-lib 对缓存与显式补充指标执行只读基本面评分。"""
    if len(args) != 3:
        print("错误：需要参数 <代码> <框架A-F> <补充指标JSON>", file=sys.stderr)
        sys.exit(1)
    code, framework_token, overrides_text = args
    framework = domain.FRAMEWORK_ALIASES.get(framework_token)
    if framework is None:
        print(f"错误：未知框架 {framework_token}", file=sys.stderr)
        sys.exit(1)
    try:
        overrides = json.loads(overrides_text)
    except json.JSONDecodeError as exc:
        print(f"JSON解析错误: {exc}", file=sys.stderr)
        sys.exit(1)
    if not isinstance(overrides, dict):
        print("错误：补充指标必须是 JSON 对象", file=sys.stderr)
        sys.exit(1)
    fundamentals = store.get_fundamentals(code)
    if fundamentals is None:
        print(f"错误：未找到 {code} 的有效基本面缓存", file=sys.stderr)
        sys.exit(1)
    metrics = dict(fundamentals)
    if "net_profit_growth" in metrics:
        metrics["net_profit_growth_3y"] = metrics["net_profit_growth"]
    operating_cf = metrics.get("operating_cf_per_share")
    eps = metrics.get("eps")
    if (
        isinstance(operating_cf, (int, float))
        and not isinstance(operating_cf, bool)
        and isinstance(eps, (int, float))
        and not isinstance(eps, bool)
        and eps > 0
    ):
        metrics["operating_cf_to_net_profit"] = operating_cf / eps
    metrics.update(overrides)
    report = sys.stdin.read().strip()
    cycle_assessment = parse_cycle_stage_tag(report)
    score = score_fundamentals(
        FrameworkKey(framework[0]),
        metrics,
        parse_subjective_assessment_tags(report),
        cycle_stage=cycle_assessment.stage if cycle_assessment else None,
    )
    payload = asdict(score)
    payload["blocked"] = score.blocked
    payload["code"] = code
    print(json.dumps(payload, ensure_ascii=False, indent=2))


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
    quote = store.get_latest_quote_snapshot(code, max_age=store.QUOTE_SNAPSHOT_MAX_AGE)
    if quote is None:
        print("错误：没有 fetcher 刚写入的有效行情快照，拒绝写入分析", file=sys.stderr)
        sys.exit(1)
    with db.db_session() as conn_tmp:
        name = _lookup_cached_stock_name(conn_tmp, code)
        industry_row = conn_tmp.execute(
            "SELECT industry FROM stock_fundamentals WHERE code=?", (code,)
        ).fetchone()
        qualitative_row = conn_tmp.execute(
            """SELECT industry FROM qualitative_only_securities
               WHERE code=?""",
            (code,),
        ).fetchone()
    industry = industry_row[0] if industry_row else None
    if qualitative_row is not None or domain.is_unsupported_financial_industry(
        industry
    ):
        print(
            "错误：保险/券商/证券不适用当前量化框架，不允许写入 set-analysis",
            file=sys.stderr,
        )
        sys.exit(1)
    result = _read_validated_analysis_stdin(framework)
    _validate_cycle_stage_for_framework(result, framework)
    today = domain.cst_today()
    scoring_status = "complete"
    valuation_conflict = framework == "C资源" and _VALUATION_CONFLICT_RE.search(result)
    if valuation_conflict:
        scoring_status = "incomplete"
        if score is not None:
            print("错误：C资源估值冲突待核实时不得写入完整总分", file=sys.stderr)
            sys.exit(1)
    elif (
        framework == "D公用"
        and store.get_market_indicator_snapshot(
            "bond_yield_10y", max_age=timedelta(hours=24)
        )
        is None
    ):
        scoring_status = "incomplete"
        if score is not None:
            print("错误：D公用缺少可信国债收益率时不得写入完整总分", file=sys.stderr)
            sys.exit(1)
    with db.db_session() as conn:
        existing = conn.execute(
            """SELECT score, score_breakdown FROM analysis_results
               WHERE code=? AND date=?""",
            (code, today),
        ).fetchone()
        effective_score = (
            None
            if scoring_status == "incomplete"
            else (score if score is not None else (existing[0] if existing else None))
        )
        clear_stale_breakdown = bool(
            existing and existing[1]
        ) and not _score_breakdown_matches_analysis(
            existing[1],
            framework=framework,
            scoring_status=scoring_status,
            score=effective_score,
        )
        conn.execute(
            """INSERT INTO analysis_results
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
                   END""",
            (
                code,
                today,
                name,
                result,
                domain.utc_now_iso(),
                score,
                framework,
                quote["price"],
                quote["quote_as_of"],
                quote["source"],
                scoring_status,
                clear_stale_breakdown,
            ),
        )
        conn.commit()
    name_str = f"({name})" if name else ""
    score_str = f" 得分:{score}/80" if score is not None else ""
    fw_str = f" 框架:{framework}" if framework else ""
    status_str = " 评分状态:incomplete" if scoring_status == "incomplete" else ""
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
    today = domain.cst_today()
    with db.db_session() as conn:
        state = conn.execute(
            """SELECT framework, COALESCE(scoring_status, 'complete'), score_breakdown
               FROM analysis_results WHERE code=? AND date=?""",
            (code, today),
        ).fetchone()
        if state and state[1] == "incomplete":
            print("错误：评分状态 incomplete 时不得补写完整总分", file=sys.stderr)
            sys.exit(1)
        clear_stale_breakdown = bool(
            state and state[2]
        ) and not _score_breakdown_matches_analysis(
            state[2],
            framework=state[0],
            scoring_status=state[1],
            score=score,
        )
        updated = conn.execute(
            """UPDATE analysis_results
               SET score=?, score_breakdown=CASE WHEN ? THEN NULL ELSE score_breakdown END
               WHERE code=? AND date=?""",
            (score, clear_stale_breakdown, code, today),
        ).rowcount
        conn.commit()
    if updated:
        print(f"得分已记录：{code} → {score}/80")
        if clear_stale_breakdown:
            print("  ⚠️ 原分项得分与新综合得分不一致，已清除，须重新写入")
    else:
        print(
            f"未找到今日分析记录，请先执行 set-analysis（代码：{code}）",
            file=sys.stderr,
        )
        sys.exit(1)


def _validate_score_breakdown_schema(
    breakdown: dict,
    *,
    framework: str | None = None,
    scoring_status: str = "complete",
    score: int | None = None,
) -> str | None:
    """校验 score_breakdown 是否符合统一嵌套 schema，返回错误信息（None 表示通过）。

    统一 schema："fundamentals"/"timing" 均为 dict 且含 "subtotal"。
    旧平铺 schema（{"roe": 8, ...}）不再允许写入，仅历史记录保留供展示降级。
    """
    if not isinstance(breakdown, dict):
        return (
            f"score_breakdown 必须是 JSON 对象（dict），而非 {type(breakdown).__name__}"
        )
    if _contains_non_finite_number(breakdown):
        return "score_breakdown 不得包含 NaN 或 Infinity"
    if "fundamentals" not in breakdown or "timing" not in breakdown:
        return "score_breakdown 必须包含 'fundamentals' 和 'timing' 两个顶层字段（统一 schema）"
    subtotals: dict[str, float | None] = {}
    for key, maximum in (("fundamentals", 60), ("timing", 20)):
        section = breakdown[key]
        if not isinstance(section, dict) or "subtotal" not in section:
            return f"score_breakdown['{key}'] 必须是包含 'subtotal' 字段的对象"
        subtotal = section["subtotal"]
        allow_null_timing = key == "timing" and scoring_status == "incomplete"
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
    if scoring_status == "incomplete":
        if breakdown["timing"]["subtotal"] is not None:
            return "incomplete 状态的 timing.subtotal 必须为 null"
        if breakdown.get("total") is not None:
            return "incomplete 状态的 total 必须为 null"
        return None
    total = breakdown.get("total")
    if not isinstance(total, (int, float)) or isinstance(total, bool):
        return "完整评分的 score_breakdown 必须包含数值 total"
    if not math.isfinite(float(total)) or not 0 <= total <= 80:
        return "score_breakdown['total'] 必须是 0—80 的有限数值"
    expected_total = (subtotals["fundamentals"] or 0) + (subtotals["timing"] or 0)
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
    return (
        _validate_score_breakdown_schema(
            breakdown,
            framework=framework,
            scoring_status=scoring_status,
            score=score,
        )
        is None
    )


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
    today = domain.cst_today()
    with db.db_session() as conn:
        analysis = conn.execute(
            """SELECT framework, COALESCE(scoring_status, 'complete'), score
               FROM analysis_results WHERE code=? AND date=?""",
            (code, today),
        ).fetchone()
        if analysis is None:
            print(
                f"未找到今日分析记录，请先执行 set-analysis（代码：{code}）",
                file=sys.stderr,
            )
            sys.exit(1)
        schema_error = _validate_score_breakdown_schema(
            breakdown,
            framework=analysis[0],
            scoring_status=analysis[1],
            score=analysis[2],
        )
        if schema_error:
            print(f"错误：{schema_error}", file=sys.stderr)
            sys.exit(1)
        updated = conn.execute(
            "UPDATE analysis_results SET score_breakdown=? WHERE code=? AND date=?",
            (json.dumps(breakdown, ensure_ascii=False), code, today),
        ).rowcount
        conn.commit()
    if updated:
        print(f"分项得分已记录：{code} → {breakdown}")
