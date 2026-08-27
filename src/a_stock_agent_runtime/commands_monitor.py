"""Structured L3, tier, and alert commands."""

from __future__ import annotations

import json
import sys
from datetime import date

from a_stock_agent_runtime import commands_holdings, db, domain

_SCOPES = {"aggregate", "core_driver", "non_core", "governance"}
_ACTIONS = {"review", "reduce", "exit"}


def _fail(message: str) -> None:
    print(f"错误：{message}", file=sys.stderr)
    raise SystemExit(1)


def _validated_rewrite_payload() -> dict:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        _fail("stdin 必须是一个有效 JSON 对象")
    required = {"l1", "l2", "rewrite_reason", "retire_l3_ids", "new_l3"}
    if not isinstance(payload, dict) or set(payload) != required:
        _fail(f"JSON 字段必须且只能为：{', '.join(sorted(required))}")
    for field in ("l1", "l2", "rewrite_reason"):
        if not isinstance(payload[field], str) or not payload[field].strip():
            _fail(f"{field} 必须是非空字符串")
        payload[field] = payload[field].strip()
    retire_ids = payload["retire_l3_ids"]
    if (
        not isinstance(retire_ids, list)
        or any(type(item) is not int or item <= 0 for item in retire_ids)
        or len(retire_ids) != len(set(retire_ids))
    ):
        _fail("retire_l3_ids 必须是不重复的正整数数组")
    if not isinstance(payload["new_l3"], list) or not payload["new_l3"]:
        _fail("new_l3 必须是非空数组")
    l3_fields = {
        "condition",
        "scope",
        "action",
        "materiality_basis",
        "temporary_exit_rule",
    }
    for index, item in enumerate(payload["new_l3"], start=1):
        if not isinstance(item, dict) or set(item) != l3_fields:
            _fail(f"new_l3[{index}] 字段不完整或包含未知字段")
        if any(not isinstance(item[field], str) or not item[field].strip() for field in l3_fields):
            _fail(f"new_l3[{index}] 的所有字段必须是非空字符串")
        for field in l3_fields:
            item[field] = item[field].strip()
        if item["scope"] not in _SCOPES or item["action"] not in _ACTIONS:
            _fail(f"new_l3[{index}] 的 scope/action 非法")
        if item["scope"] == "non_core" and item["action"] != "review":
            _fail("non_core 条件最多只能配置 review，不能配置 reduce/exit")
    return payload


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
    if origin not in ("original", "recovered", "new_monitoring"):
        print("错误：origin 非法", file=sys.stderr)
        sys.exit(1)
    with db.db_session() as conn:
        holding_id, _, _ = commands_holdings._single_open_holding(conn, code)
        if conn.execute(
            """SELECT 1 FROM holding_thesis_versions
               WHERE holding_id=? AND status='active'""",
            (holding_id,),
        ).fetchone():
            _fail("该持仓已启用论文版本，请使用 thesis-rewrite 原子重写 L3")
        now_iso = domain.utc_now_iso()
        cursor = conn.execute(
            """INSERT INTO holding_l3_conditions
               (holding_id, condition_text, origin_type, temporary_exit_rule,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                holding_id,
                condition_text,
                origin,
                temporary_exit_rule,
                now_iso,
                now_iso,
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
    if status not in ("pending", "not_triggered", "watch", "triggered"):
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
    with db.db_session() as conn:
        cursor = conn.execute(
            """UPDATE holding_l3_conditions
               SET status=?, evidence=?, as_of=?, next_review_date=?, updated_at=?
               WHERE id=? AND is_active=1""",
            (status, evidence, as_of, next_review, domain.utc_now_iso(), condition_id),
        )
        if cursor.rowcount == 0:
            _fail(f"未找到活动L3条件 id={condition_id}；已退役条件不可更新")
        conn.commit()
    print(f"L3状态已更新：id={condition_id} → {status}")


def cmd_l3_list(args: list[str]) -> None:
    if len(args) not in (1, 2) or (len(args) == 2 and args[1] != "--all"):
        _fail("需要参数 <代码> [--all]")
    code = args[0]
    show_all = len(args) == 2
    with db.db_session() as conn:
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(holding_l3_conditions)")
        }
        if "thesis_version_id" not in columns:
            print(f"警告：{code} legacy contract（尚未迁移论文版本，保留旧L3行为）")
            rows = conn.execute(
                """SELECT l.id, l.origin_type, l.status, l.condition_text, l.as_of,
                          l.next_review_date, l.evidence, l.temporary_exit_rule
                   FROM holding_l3_conditions l
                   JOIN holdings h ON h.id=l.holding_id
                   WHERE h.code=? AND h.exit_date IS NULL ORDER BY l.id""",
                (code,),
            ).fetchall()
            for row in rows:
                print(
                    f"#{row[0]} [{row[1]}] {row[2]} | {row[3]} | as-of:{row[4] or '─'} "
                    f"| 下次:{row[5] or '─'} | 证据:{row[6] or '─'} | 临时出场:{row[7] or '─'}"
                )
            if not rows:
                print(f"{code} 无结构化L3条件")
            return

        holding = conn.execute(
            "SELECT id FROM holdings WHERE code=? AND exit_date IS NULL ORDER BY id",
            (code,),
        ).fetchone()
        if holding is None:
            print(f"{code} 无结构化L3条件")
            return
        holding_id = holding[0]
        active_thesis = conn.execute(
            """SELECT id, version, l1, l2 FROM holding_thesis_versions
               WHERE holding_id=? AND status='active'""",
            (holding_id,),
        ).fetchone()
        if show_all:
            for version, status, l1, l2, reason in conn.execute(
                """SELECT version, status, l1, l2, rewrite_reason
                   FROM holding_thesis_versions WHERE holding_id=? ORDER BY version""",
                (holding_id,),
            ):
                print(
                    f"thesis:v{version} {status} | L1:{l1} | L2:{l2} "
                    f"| 重写原因:{reason}"
                )
        elif active_thesis is not None:
            print(
                f"thesis:v{active_thesis[1]} active | L1:{active_thesis[2]} "
                f"| L2:{active_thesis[3]}"
            )
        all_rows = conn.execute(
            """SELECT l.id, l.origin_type, l.status, l.condition_text, l.as_of,
                      l.next_review_date, l.evidence, l.temporary_exit_rule,
                      l.thesis_version_id, l.is_active, l.retired_at, l.retired_reason,
                      l.condition_scope, l.action_level, l.materiality_basis, t.version
               FROM holding_l3_conditions l
               LEFT JOIN holding_thesis_versions t ON t.id=l.thesis_version_id
               WHERE l.holding_id=? ORDER BY l.id""",
            (holding_id,),
        ).fetchall()
    if active_thesis is None:
        print(f"警告：{code} legacy contract（尚未重写论文，保留旧L3行为）")
        rows = all_rows if show_all else [row for row in all_rows if row[9] == 1]
    else:
        active_thesis_id = active_thesis[0]

        def valid(row) -> bool:
            return (
                row[9] == 1
                and row[8] == active_thesis_id
                and row[12] in _SCOPES
                and row[13] in _ACTIONS
                and not (row[12] == "non_core" and row[13] != "review")
                and bool(row[14])
                and bool(row[7])
            )

        invalid_active = [row for row in all_rows if row[9] == 1 and not valid(row)]
        if invalid_active:
            print("警告：触发文本成立，但交易契约无效/已过期，冻结交易并重做论文")
        rows = all_rows if show_all else [row for row in all_rows if valid(row)]
    if not rows:
        print(f"{code} 无活动结构化L3条件")
        return
    for row in rows:
        lifecycle = "active" if row[9] else "retired"
        thesis = f"v{row[15]}" if row[15] is not None else "legacy"
        print(
            f"#{row[0]} [{row[1]}] {row[2]} {lifecycle} thesis:{thesis} "
            f"[{row[12]}/{row[13]}] | {row[3]} | as-of:{row[4] or '─'} "
            f"| 下次:{row[5] or '─'} | 证据:{row[6] or '─'} | 重要性:{row[14] or '─'} "
            f"| 临时出场:{row[7] or '─'} | 退役:{row[10] or '─'} {row[11] or ''}"
        )


def cmd_thesis_rewrite(args: list[str]) -> None:
    """Atomically version a holding thesis and replace its active L3 set."""
    if len(args) != 1:
        _fail("需要参数 <代码>")
    code = args[0]
    payload = _validated_rewrite_payload()
    with db.db_session() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            holdings = conn.execute(
                "SELECT id FROM holdings WHERE code=? AND exit_date IS NULL",
                (code,),
            ).fetchall()
            if len(holdings) != 1:
                raise ValueError(f"{code} 必须且只能有一个活动持仓")
            holding_id = holdings[0][0]
            requested = set(payload["retire_l3_ids"])
            if requested:
                placeholders = ",".join("?" for _ in requested)
                matched = conn.execute(
                    f"""SELECT id FROM holding_l3_conditions
                        WHERE id IN ({placeholders}) AND holding_id=? AND is_active=1""",
                    (*sorted(requested), holding_id),
                ).fetchall()
                if {row[0] for row in matched} != requested:
                    raise ValueError("retire_l3_ids 含跨持仓、不存在或已退役的条件")
            active_ids = {
                row[0]
                for row in conn.execute(
                    "SELECT id FROM holding_l3_conditions WHERE holding_id=? AND is_active=1",
                    (holding_id,),
                )
            }
            if requested != active_ids:
                raise ValueError("retire_l3_ids 必须完整覆盖该持仓全部活动L3")
            prior = conn.execute(
                """SELECT id FROM holding_thesis_versions
                   WHERE holding_id=? AND status='active'""",
                (holding_id,),
            ).fetchone()
            if prior:
                conn.execute(
                    "UPDATE holding_thesis_versions SET status='superseded' WHERE id=?",
                    (prior[0],),
                )
            version = conn.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM holding_thesis_versions WHERE holding_id=?",
                (holding_id,),
            ).fetchone()[0]
            now_iso = domain.utc_now_iso()
            thesis_id = conn.execute(
                """INSERT INTO holding_thesis_versions
                   (holding_id, version, l1, l2, rewrite_reason, status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'active', ?)""",
                (
                    holding_id,
                    version,
                    payload["l1"],
                    payload["l2"],
                    payload["rewrite_reason"],
                    now_iso,
                ),
            ).lastrowid
            if requested:
                placeholders = ",".join("?" for _ in requested)
                conn.execute(
                    f"""UPDATE holding_l3_conditions
                        SET is_active=0, retired_at=?, retired_reason=?, updated_at=?
                        WHERE id IN ({placeholders})""",
                    (
                        now_iso,
                        payload["rewrite_reason"],
                        now_iso,
                        *sorted(requested),
                    ),
                )
            for item in payload["new_l3"]:
                conn.execute(
                    """INSERT INTO holding_l3_conditions
                       (holding_id, thesis_version_id, condition_text, origin_type,
                        temporary_exit_rule, condition_scope, action_level,
                        materiality_basis, created_at, updated_at)
                       VALUES (?, ?, ?, 'new_monitoring', ?, ?, ?, ?, ?, ?)""",
                    (
                        holding_id,
                        thesis_id,
                        item["condition"],
                        item["temporary_exit_rule"],
                        item["scope"],
                        item["action"],
                        item["materiality_basis"],
                        now_iso,
                        now_iso,
                    ),
                )
            if conn.execute(
                """SELECT 1 FROM holding_l3_conditions
                   WHERE holding_id=? AND is_active=1
                     AND (thesis_version_id IS NULL
                          OR condition_scope='legacy_unclassified'
                          OR action_level='legacy_unclassified') LIMIT 1""",
                (holding_id,),
            ).fetchone():
                raise ValueError("重写后仍存在活动 legacy-unclassified L3")
            conn.commit()
        except ValueError as exc:
            conn.rollback()
            _fail(str(exc))
        except BaseException:
            conn.rollback()
            raise
    print(
        f"论文已原子重写：{code} thesis:v{version}，退役{len(requested)}条，新增{len(payload['new_l3'])}条L3"
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
    exit_path = None if args[1].lower() == "none" else args[1].upper()
    if exit_path not in (None, "A", "B", "C"):
        print("错误：出场路径只能为 A/B/C/none", file=sys.stderr)
        sys.exit(1)
    target_pct = None
    if len(args) > 2 and args[2].lower() != "none":
        target_pct = commands_holdings._parse_cli_finite_float(args[2], "目标涨幅")
    if exit_path == "B" and (target_pct is None or target_pct <= 0):
        print("错误：路径B必须设置大于0的目标涨幅", file=sys.stderr)
        sys.exit(1)
    if exit_path != "B" and target_pct is not None:
        print("错误：只有路径B可以设置目标涨幅", file=sys.stderr)
        sys.exit(1)
    exemption = None
    if len(args) > 3 and args[3].lower() != "none":
        exemption = args[3].upper()
        if exemption not in ("E", "F"):
            print("错误：豁免框架只能为 E/F/none", file=sys.stderr)
            sys.exit(1)
    if exemption and exit_path is not None:
        print("错误：轻仓试探出场路径与正式仓位Tier1豁免不能同时设置", file=sys.stderr)
        sys.exit(1)
    with db.db_session() as conn:
        holding_id, buy_date, framework = commands_holdings._single_open_holding(
            conn, code
        )
        if exemption and buy_date != domain.cst_today():
            print("错误：Tier1估值豁免只能在建仓当日声明", file=sys.stderr)
            sys.exit(1)
        if exemption and not (framework or "").startswith(exemption):
            print(
                f"错误：持仓框架{framework or '未知'}与豁免框架{exemption}不一致",
                file=sys.stderr,
            )
            sys.exit(1)
        conn.execute(
            """INSERT INTO holding_tier_state
               (holding_id, exit_path, exit_target_pct, exemption_framework,
                exemption_declared_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(holding_id) DO UPDATE SET
                 exit_path=excluded.exit_path,
                 exit_target_pct=excluded.exit_target_pct,
                 exemption_framework=excluded.exemption_framework,
                 exemption_declared_at=excluded.exemption_declared_at,
                 updated_at=excluded.updated_at""",
            (
                holding_id,
                exit_path,
                target_pct,
                exemption,
                domain.cst_today() if exemption else None,
                domain.utc_now_iso(),
            ),
        )
        conn.commit()
    print(
        f"Tier配置已记录：{code} 路径={exit_path or 'none'} 豁免={exemption or 'none'}"
    )


def cmd_holding_framework(args: list[str]) -> None:
    if len(args) != 2:
        print("错误：需要参数 <代码> <A|B|C|D|E|F>", file=sys.stderr)
        sys.exit(1)
    code, token = args[0], args[1]
    normalized = domain.FRAMEWORK_ALIASES.get(
        token.upper()
    ) or domain.FRAMEWORK_ALIASES.get(token)
    if normalized is None:
        print("错误：框架必须为 A/B/C/D/E/F 或完整标签", file=sys.stderr)
        sys.exit(1)
    with db.db_session() as conn:
        holding_id, _, old_framework = commands_holdings._single_open_holding(
            conn, code
        )
        row = conn.execute(
            "SELECT reference_cost, cost_price FROM holdings WHERE id=?",
            (holding_id,),
        ).fetchone()
        reference_cost = row[0] or row[1]
        sl15_pct, sl20_pct = domain.get_stop_loss_pct(normalized)
        now_iso = domain.utc_now_iso()
        conn.execute(
            """UPDATE holdings
               SET framework=?, framework_confident=1,
                   stop_loss_15=?, stop_loss_20=?, updated_at=?
               WHERE id=?""",
            (
                normalized,
                round(reference_cost * sl15_pct, 3),
                round(reference_cost * sl20_pct, 3),
                now_iso,
                holding_id,
            ),
        )
        conn.execute(
            """INSERT INTO holding_events
               (holding_id, code, event_type, event_date, notes, created_at)
               VALUES (?, ?, 'adjustment', ?, ?, ?)""",
            (
                holding_id,
                code,
                domain.cst_today(),
                f"framework:{old_framework or 'unknown'}->{normalized}",
                now_iso,
            ),
        )
        conn.commit()
    print(
        f"持仓框架已迁移：{code} {old_framework or 'unknown'} → {normalized}，止损线已重算"
    )


def cmd_tier_update(args: list[str]) -> None:
    if len(args) != 3:
        print("错误：需要参数 <代码> <tier1|tier2|tier3> <状态>", file=sys.stderr)
        sys.exit(1)
    code, tier, status = args
    allowed = {
        "tier1": {"pending", "completed", "exempted"},
        "tier2": {"pending", "completed"},
        "tier3": {"pending", "completed"},
    }
    if tier not in allowed or status not in allowed[tier]:
        print("错误：Tier或状态非法", file=sys.stderr)
        sys.exit(1)
    with db.db_session() as conn:
        holding_id, _, _ = commands_holdings._single_open_holding(conn, code)
        conn.execute(
            """INSERT INTO holding_tier_state (holding_id, updated_at)
               VALUES (?, ?) ON CONFLICT(holding_id) DO NOTHING""",
            (holding_id, domain.utc_now_iso()),
        )
        conn.execute(
            f"UPDATE holding_tier_state SET {tier}_status=?, updated_at=? WHERE holding_id=?",
            (status, domain.utc_now_iso(), holding_id),
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
    if level not in ("yellow", "red"):
        print("错误：预警级别非法", file=sys.stderr)
        sys.exit(1)
    if category not in ("holding_deterioration", "entry_valuation", "unverified"):
        print("错误：预警类别非法", file=sys.stderr)
        sys.exit(1)
    review_due = None if review_due.lower() == "none" else review_due
    if review_due:
        try:
            date.fromisoformat(review_due)
        except ValueError:
            print("错误：复核日期必须为 YYYY-MM-DD 或 none", file=sys.stderr)
            sys.exit(1)
    with db.db_session() as conn:
        holding_id, _, _ = commands_holdings._single_open_holding(conn, code)
        now_iso = domain.utc_now_iso()
        conn.execute(
            """INSERT INTO holding_alerts
               (holding_id, code, level, category, reason_code, reason, evidence,
                opened_at, review_due, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(holding_id, reason_code) WHERE status != 'resolved'
               DO UPDATE SET level=excluded.level, category=excluded.category,
                 reason=excluded.reason, evidence=excluded.evidence,
                 review_due=excluded.review_due, updated_at=excluded.updated_at""",
            (
                holding_id,
                code,
                level,
                category,
                reason_code,
                reason,
                evidence,
                now_iso,
                review_due,
                now_iso,
            ),
        )
        conn.commit()
    print(f"结构化预警已记录：{code} {level} {reason_code}")


def cmd_alert_resolve(args: list[str]) -> None:
    if len(args) < 3:
        print("错误：需要参数 <代码> <reason_code> <解除证据>", file=sys.stderr)
        sys.exit(1)
    code, reason_code, evidence = args[0], args[1], " ".join(args[2:])
    with db.db_session() as conn:
        now_iso = domain.utc_now_iso()
        cursor = conn.execute(
            """UPDATE holding_alerts
               SET status='resolved', resolved_at=?, resolution_evidence=?, updated_at=?
               WHERE code=? AND reason_code=? AND status!='resolved' """,
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
    code, reason_code, evidence = args[0], args[1], " ".join(args[2:])
    with db.db_session() as conn:
        cursor = conn.execute(
            """UPDATE holding_alerts
               SET status='pending', evidence=?, updated_at=?
               WHERE code=? AND reason_code=? AND status='active' """,
            (evidence, domain.utc_now_iso(), code, reason_code),
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
    with db.db_session() as conn:
        rows = conn.execute(
            """SELECT level, category, reason_code, status, reason, review_due,
                      evidence, resolution_evidence
               FROM holding_alerts WHERE code=?
               ORDER BY status='resolved', opened_at, id""",
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
    code, level, reason = args[0], args[1], " ".join(args[2:])
    if level not in ("yellow", "red"):
        print("错误：level 必须为 yellow 或 red", file=sys.stderr)
        sys.exit(1)
    today = domain.cst_today()
    new_flag = json.dumps(
        {"level": level, "reason": reason, "date": today}, ensure_ascii=False
    )
    with db.db_session() as conn:
        cursor = conn.execute(
            "UPDATE analysis_results "
            "SET flags = json_insert(COALESCE(NULLIF(flags, ''), '[]'), '$[#]', json(?)) "
            "WHERE code=? AND date=?",
            (new_flag, code, today),
        )
        if cursor.rowcount == 0:
            print(
                f"未找到今日分析记录，请先执行 set-analysis（代码：{code}）",
                file=sys.stderr,
            )
            sys.exit(1)
        conn.commit()
    icon = "🔴" if level == "red" else "⚠️"
    print(f"预警已记录：{code} {icon} {reason}")


def cmd_clear_flag(args: list[str]) -> None:
    """⑤ 清除指定股票今日所有预警标记"""
    if len(args) < 1:
        print("错误：需要参数 <代码>", file=sys.stderr)
        sys.exit(1)
    code = args[0]
    today = domain.cst_today()
    with db.db_session() as conn:
        conn.execute(
            "UPDATE analysis_results SET flags=NULL WHERE code=? AND date=?",
            (code, today),
        )
        conn.commit()
    print(f"已清除 {code} 的今日预警标记")
