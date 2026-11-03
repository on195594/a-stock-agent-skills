"""Optional Research card projection and review prompts; no valuation formulas."""

from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import requests

from a_stock_agent_runtime import monitor_contract, research_client
from a_stock_agent_runtime.trading_costs import COMMISSION_RATE, STAMP_TAX_RATE

SHANGHAI = ZoneInfo("Asia/Shanghai")


def fetch_cards(*, skip: bool = False) -> dict:
    if skip:
        return {"status": "skipped"}
    try:
        payload = research_client.request_json("/api/cards", new_endpoint=True)
        monitor_contract.validate_research_cards(payload)
    except research_client.ResearchNotConfigured:
        return {"status": "not_configured"}
    except requests.RequestException as exc:
        # Transport exception text may contain credentials or response bodies.
        return {"status": "unavailable", "reason": f"Research 连接失败：{type(exc).__name__}"}
    except (OSError, RuntimeError) as exc:
        return {"status": "unavailable", "reason": f"Research 配置读取失败：{type(exc).__name__}"}
    except ValueError as exc:
        return {"status": "unavailable", "reason": str(exc)[:700]}
    return {"status": "ok", "cards": payload["cards"], "missing": payload["missing"]}


def _row(code: str, card: dict | None) -> dict:
    current = card["current"] if card else {}
    valuation = current.get("valuation") or {}
    returns = valuation.get("annual_returns") or {}
    return {
        "code": code, "card": card,
        "card_status": card["status"] if card else None,
        "verdict": card.get("verdict") if card else None,
        "report_id": card["report_id"] if card else None,
        "completed_at": card.get("completed_at") if card else None,
        "close": current.get("last_close"),
        "close_date": current.get("last_close_date"),
        "zone": current.get("current_zone"),
        "neutral_return": returns.get("中性"),
        "conservative_return": returns.get("保守"),
        "optimistic_return": returns.get("乐观"),
        "note": current.get("note") or valuation.get("reason") or current.get("reason"),
        # Research's caveat for rolled returns (e.g. unverified cumulative dividends).
        "assumption": valuation.get("assumption"),
    }


def _evidence(row: dict) -> dict:
    return {key: row[key] for key in ("code", "report_id", "close_date", "close")}


def summarize(result: dict, holding_codes: list[str], snapshot_date: date) -> tuple[dict, list, list]:
    """Return research, informational prompts, and thesis-only review escalations."""
    cards = {card["code"]: card for card in result.get("cards", [])}
    missing = result.get("missing", [])
    research = {
        "status": result["status"],
        "holdings": [_row(code, cards.get(code)) for code in dict.fromkeys(holding_codes)],
        "candidates": [
            _row(code, cards.get(code))
            for code in sorted(
                {card["code"] for card in cards.values() if card["origin"] == "l5"}
                | {item["code"] for item in missing if item["origin"] == "l5"}
            ) if code not in holding_codes
        ],
        "missing": [item["code"] for item in missing],
        "opportunity_costs": [],
    }
    if result.get("reason"):
        research["reason"] = result["reason"]
    prompts, escalations = [], []
    if result["status"] == "unavailable":
        prompts.append({
            "code": None, "kind": "research_unavailable",
            "detail": f"论点卡状态未知：{result['reason']}", "evidence": {},
        })
    mismatches = []
    for holding in research["holdings"]:
        code, card = holding["code"], holding["card"]
        if holding["card_status"] == "待复核":
            events = "；".join(
                f"{event.get('title') or '待复核事件'}（{event.get('kind') or event.get('type') or '未分类'}）"
                for event in card["pending_events"]
            ) or "Research 论点卡待复核"
            escalations.append({
                "code": code, "reason_code": "research_thesis_review", "candidate": "review",
                "detail": f"报告 {card['report_id']}：{events}；区间暂停解读，按日常监控与 L3 资料复核",
            })
            continue
        if holding["card_status"] != "有效":
            continue
        if holding["zone"] == "测算透支区":
            prompts.append({
                "code": code, "kind": "valuation_stretched",
                "detail": f"{code} 收盘价 {holding['close']} 处于测算透支区，复核经营假设与退出倍数",
                "evidence": _evidence(holding),
            })
        if holding["neutral_return"] is None:
            continue
        best = None
        for candidate in research["candidates"]:
            if (candidate["card_status"] != "有效"
                    or candidate["verdict"] != "值得继续研究"
                    or candidate["neutral_return"] is None):
                continue
            horizon = (candidate["card"]["current"].get("valuation") or {}).get("horizon")
            if horizon is None or horizon <= 0:
                continue
            # Candidates that cannot reach the threshold even before costs need no date check.
            if candidate["neutral_return"] - holding["neutral_return"] < 0.03:
                continue
            if not holding["close_date"] or not candidate["close_date"]:
                mismatches.append(f"{code}/{candidate['code']} 缺少收盘日，未比较机会成本")
                continue
            days = abs((date.fromisoformat(holding["close_date"])
                        - date.fromisoformat(candidate["close_date"])).days)
            if days > 3:
                mismatches.append(f"{code}/{candidate['code']} 收盘日相差 {days} 个自然日（超过3日），未比较机会成本")
                continue
            # Compare the candidate with none of its frozen dividends remaining against
            # the holding with all remaining. This is sensitivity, not a return guarantee.
            candidate_low = candidate["card"]["current"]["valuation"].get("neutral_return_without_dividends")
            holding_low = (holding["card"]["current"].get("valuation") or {}).get("neutral_return_without_dividends")
            if (candidate_low is None or holding_low is None
                    or not -1 <= candidate_low <= candidate["neutral_return"]
                    or not -1 <= holding_low <= holding["neutral_return"]):
                mismatches.append(f"{code}/{candidate['code']} 缺少适用的分红敏感性值，未比较机会成本")
                continue
            # Decimal avoids excluding the exact 3pp boundary through float subtraction.
            cost = (Decimal(str(STAMP_TAX_RATE)) + 2 * Decimal(str(COMMISSION_RATE))) / Decimal(str(horizon))
            advantage = (Decimal(str(candidate_low))
                         - Decimal(str(holding["neutral_return"])) - cost)
            if advantage < Decimal("0.03"):
                mismatches.append(f"{code}/{candidate['code']} 扣费后优势未稳健达到3个百分点；现金流未核对，不提示换仓优势")
            if advantage >= Decimal("0.03") and (best is None or advantage > best[0]):
                best = advantage, cost, candidate
        if best:
            advantage, cost, candidate = best
            research["opportunity_costs"].append({
                "holding": _evidence(holding), "candidate": _evidence(candidate),
                "holding_neutral_return": holding["neutral_return"],
                "candidate_neutral_return": candidate["neutral_return"],
                "candidate_horizon": candidate["card"]["current"]["valuation"]["horizon"],
                "annual_switch_cost": float(cost), "net_advantage": float(advantage),
                "candidate_return_without_dividends": candidate["card"]["current"]["valuation"]["neutral_return_without_dividends"],
                "comparison_basis": "候选不计累计分红、持仓计全部分红；仅非负冻结分红假设内的敏感性比较，非真实收益上下界",
            })
    grouped = {}
    for comparison in research["opportunity_costs"]:
        grouped.setdefault(comparison["candidate"]["code"], []).append(comparison)
    for code, comparisons in grouped.items():
        compared_codes = [code, *(item["holding"]["code"] for item in comparisons)]
        if not any(_fresh(cards[c].get("completed_at"), snapshot_date) for c in compared_codes):
            continue
        candidate = cards[code]
        names = "/".join(cards[item["holding"]["code"]].get("name") or item["holding"]["code"]
                         for item in comparisons)
        maximum = max(item["net_advantage"] for item in comparisons)
        caveats = dict.fromkeys(
            caveat for c in compared_codes
            if (caveat := (cards[c]["current"].get("valuation") or {}).get("assumption")))
        prompts.append({
            "code": code, "kind": "opportunity_cost",
            "detail": (
                f"{candidate.get('name') or code} {code} 中性年化 "
                f"{comparisons[0]['candidate_neutral_return']:.2%}，按候选不计累计分红、持仓计全部分红，扣费后比 {names} "
                f"高 ≥3 个百分点（最大差 {maximum * 100:.4f} 个百分点），仅冻结分红敏感性、非真实收益界限；情景未经记分，仅提示复核"
                + "".join(f"；Research 注：{caveat}" for caveat in caveats)
            ),
            "evidence": {"comparisons": comparisons},
        })
    if mismatches:
        research["reason"] = "；".join(mismatches)
    return research, prompts, escalations


def _fresh(completed_at: object, snapshot_date: date) -> bool:
    try:
        completed = datetime.fromisoformat(completed_at)
    except (TypeError, ValueError):
        return False
    # Research timestamps are Shanghai dates; naive values are treated as already local.
    if completed.tzinfo is not None:
        completed = completed.astimezone(SHANGHAI)
    completed_date = completed.date()
    return 0 <= (snapshot_date - completed_date).days <= 7
