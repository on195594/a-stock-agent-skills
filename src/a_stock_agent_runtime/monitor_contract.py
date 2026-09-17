"""Versioned machine-readable monitoring snapshot contract."""

from __future__ import annotations

from datetime import datetime
import json
import math
import re
from typing import Any


class MonitorContractError(ValueError):
    """A monitoring snapshot does not satisfy monitor-v1."""


DATA_STATUSES = frozenset({"complete", "partial", "stale", "unavailable", "conflicted"})
VALUATION_STATUSES = frozenset({"exact", "priced_positions_lower_bound", "unavailable"})
REVIEW_STATUSES = frozenset({"cleared", "review_required", "blocked"})
ACTION_STATUSES = frozenset({"no_action", "review_candidate", "trade_candidate"})
INDUSTRY_CONTEXT_STATUSES = frozenset(
    {"complete", "stale", "invalid", "unavailable", "not_applicable"}
)
ESCALATION_REASON_CODES = frozenset(
    {
        "price_stop_1",
        "price_stop_2",
        "daily_drop",
        "relative_underperformance",
        "tier_review_due",
        "alert_review_due",
        "l3_review_due",
        "l3_candidate",
        "governance_gate",
        "risk_budget_exceeded",
        "quote_gap",
        "denominator_missing",
        "data_conflict",
    }
)
_REQUIRED_FIELDS = {
    "schema_version",
    "as_of",
    "runtime_version",
    "data_status",
    "valuation_status",
    "review_status",
    "action_status",
    "account",
    "quote_coverage",
    "industry_context",
    "holdings",
    "escalations",
    "data_gaps",
    "stop_reason",
    "requires_user_confirmation",
    "manifest",
}


def _reject_nonfinite(value: Any, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise MonitorContractError(f"all numbers must be finite ({path})")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_nonfinite(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_nonfinite(item, f"{path}[{index}]")


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MonitorContractError(f"{field} must be an object")
    return value


def _array(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise MonitorContractError(f"{field} must be an array")
    return value


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MonitorContractError(f"{field} must be a non-empty string")
    return value


def _supported(value: Any, allowed: frozenset[str], field: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise MonitorContractError(f"{field} is unsupported")
    return value


def _iso8601(value: Any, field: str, *, aware: bool = False) -> str:
    text = _nonempty(value, field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MonitorContractError(f"{field} must be ISO-8601") from exc
    if aware and (parsed.tzinfo is None or parsed.utcoffset() is None):
        raise MonitorContractError(f"{field} must be timezone-aware")
    return text


def _optional_string(value: Any, field: str) -> None:
    if value is not None and not isinstance(value, str):
        raise MonitorContractError(f"{field} must be a string or null")


def _required(item: dict[str, Any], fields: set[str], field: str) -> None:
    missing = sorted(fields - item.keys())
    if missing:
        raise MonitorContractError(f"missing required field: {field}.{missing[0]}")


def validate_monitor_snapshot(payload: object) -> dict[str, Any]:
    """Validate monitor-v1 without discarding additive fields."""
    value = _object(payload, "snapshot")
    _reject_nonfinite(value)
    missing = sorted(_REQUIRED_FIELDS - value.keys())
    if missing:
        raise MonitorContractError(f"missing required field: {missing[0]}")

    version = value["schema_version"]
    if type(version) is not int or version != 1:
        raise MonitorContractError("schema_version must be integer 1")
    _iso8601(value["as_of"], "as_of", aware=True)
    _nonempty(value["runtime_version"], "runtime_version")
    data_status = _supported(value["data_status"], DATA_STATUSES, "data_status")
    _supported(value["valuation_status"], VALUATION_STATUSES, "valuation_status")
    _supported(value["review_status"], REVIEW_STATUSES, "review_status")
    action_status = _supported(value["action_status"], ACTION_STATUSES, "action_status")
    account = _object(value["account"], "account")
    _required(
        account,
        {
            "portfolio_value",
            "denominator_status",
            "stock_market_value",
            "stock_weight_pct",
            "total_stop_risk",
            "total_stop_risk_pct",
            "known_stop_risk_lower_bound",
            "risk_budget_status",
            "risk_policy",
        },
        "account",
    )
    for field in (
        "portfolio_value",
        "stock_market_value",
        "stock_weight_pct",
        "total_stop_risk",
        "total_stop_risk_pct",
        "known_stop_risk_lower_bound",
    ):
        number = account[field]
        if number is not None and (
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or number < 0
            or field == "portfolio_value"
            and number == 0
        ):
            raise MonitorContractError(
                f"account.{field} must be a valid number or null"
            )
    denominator_status = _supported(
        account["denominator_status"],
        frozenset({"explicit", "missing"}),
        "account.denominator_status",
    )
    if (account["portfolio_value"] is not None) != (denominator_status == "explicit"):
        raise MonitorContractError("account denominator evidence is inconsistent")
    budget_status = account["risk_budget_status"]
    if budget_status is not None:
        _supported(
            budget_status,
            frozenset({"within_budget", "over_budget"}),
            "risk_budget_status",
        )
        if account["portfolio_value"] is None:
            raise MonitorContractError("risk budget requires an explicit denominator")
    if budget_status == "within_budget" and (
        account["total_stop_risk"] is None or account["total_stop_risk_pct"] is None
    ):
        raise MonitorContractError("within_budget requires complete risk totals")
    if (
        account["total_stop_risk"] is None
        and account["total_stop_risk_pct"] is not None
    ):
        raise MonitorContractError(
            "incomplete risk total cannot have a complete percentage"
        )
    if account["total_stop_risk"] is not None and (
        account["known_stop_risk_lower_bound"] != account["total_stop_risk"]
    ):
        raise MonitorContractError(
            "complete risk total must match its known lower bound"
        )
    policy = _object(account["risk_policy"], "account.risk_policy")
    _required(
        policy,
        {
            "policy_id",
            "source",
            "max_position_risk_pct",
            "max_portfolio_risk_pct",
            "field_sources",
        },
        "account.risk_policy",
    )
    _nonempty(policy["policy_id"], "risk_policy.policy_id")
    _nonempty(policy["source"], "risk_policy.source")
    sources = _object(policy["field_sources"], "risk_policy.field_sources")
    for field in ("max_position_risk_pct", "max_portfolio_risk_pct"):
        number = policy[field]
        if (
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or number <= 0
        ):
            raise MonitorContractError(f"risk_policy.{field} must be positive")
        _nonempty(sources.get(field), f"risk_policy.field_sources.{field}")

    coverage = _object(value["quote_coverage"], "quote_coverage")
    _required(coverage, {"priced", "active", "complete"}, "quote_coverage")
    for field in ("priced", "active"):
        number = coverage[field]
        if type(number) is not int or number < 0:
            raise MonitorContractError(
                f"quote_coverage.{field} must be a non-negative integer"
            )
    if type(coverage["complete"]) is not bool:
        raise MonitorContractError("quote_coverage.complete must be a boolean")
    if coverage["priced"] > coverage["active"]:
        raise MonitorContractError("quote_coverage.priced cannot exceed active")
    if coverage["complete"] and coverage["priced"] != coverage["active"]:
        raise MonitorContractError("complete quote coverage requires priced == active")

    industry = _object(value["industry_context"], "industry_context")
    _required(
        industry,
        {"status", "error_code", "freshness_days", "source", "fetched_at"},
        "industry_context",
    )
    industry_status = _supported(
        industry["status"], INDUSTRY_CONTEXT_STATUSES, "industry_context.status"
    )
    _optional_string(industry["error_code"], "industry_context.error_code")
    _optional_string(industry["source"], "industry_context.source")
    freshness = industry["freshness_days"]
    if freshness is not None and (type(freshness) is not int or freshness < 0):
        raise MonitorContractError(
            "industry_context.freshness_days must be a non-negative integer or null"
        )
    if industry["fetched_at"] is not None:
        _iso8601(industry["fetched_at"], "industry_context.fetched_at")
    if industry_status == "complete" and industry["error_code"] is not None:
        raise MonitorContractError("complete industry_context cannot have error_code")

    holdings = _array(value["holdings"], "holdings")
    if coverage["active"] != len(holdings):
        raise MonitorContractError("quote_coverage.active must match holdings count")
    holding_fields = {"id", "code", "name", "framework", "framework_confident", "quote"}
    for index, raw in enumerate(holdings):
        holding = _object(raw, f"holdings[{index}]")
        _required(holding, holding_fields, f"holdings[{index}]")
        if type(holding["id"]) is not int or holding["id"] <= 0:
            raise MonitorContractError(
                f"holdings[{index}].id must be a positive integer"
            )
        if (
            not isinstance(holding["code"], str)
            or re.fullmatch(r"\d{6}", holding["code"]) is None
        ):
            raise MonitorContractError(
                f"holdings[{index}].code must be a six-digit string"
            )
        _nonempty(holding["name"], f"holdings[{index}].name")
        _nonempty(holding["framework"], f"holdings[{index}].framework")
        if type(holding["framework_confident"]) is not bool:
            raise MonitorContractError(
                f"holdings[{index}].framework_confident must be a boolean"
            )
        _object(holding["quote"], f"holdings[{index}].quote")
        for field in (
            "market_value",
            "portfolio_weight_pct",
            "stop_risk",
            "stop_risk_pct",
        ):
            number = holding.get(field)
            if number is not None and (
                isinstance(number, bool)
                or not isinstance(number, (int, float))
                or number < 0
            ):
                raise MonitorContractError(
                    f"holdings[{index}].{field} must be non-negative or null"
                )
            if budget_status == "within_budget" and number is None:
                raise MonitorContractError(
                    "within_budget requires complete holding risk evidence"
                )

    escalations = _array(value["escalations"], "escalations")
    for index, raw in enumerate(escalations):
        item = _object(raw, f"escalations[{index}]")
        _required(
            item,
            {"code", "reason_code", "candidate", "detail"},
            f"escalations[{index}]",
        )
        if item["code"] is not None and (
            not isinstance(item["code"], str)
            or re.fullmatch(r"\d{6}", item["code"]) is None
        ):
            raise MonitorContractError(
                f"escalations[{index}].code must be six digits or null"
            )
        _supported(
            item["reason_code"],
            ESCALATION_REASON_CODES,
            f"escalations[{index}].reason_code",
        )
        _supported(
            item["candidate"],
            frozenset({"review", "trade"}),
            f"escalations[{index}].candidate",
        )
        _nonempty(item["detail"], f"escalations[{index}].detail")

    gaps = _array(value["data_gaps"], "data_gaps")
    for index, raw in enumerate(gaps):
        item = _object(raw, f"data_gaps[{index}]")
        _required(item, {"code", "field", "minimum_action"}, f"data_gaps[{index}]")
        if item["code"] is not None and (
            not isinstance(item["code"], str)
            or re.fullmatch(r"\d{6}", item["code"]) is None
        ):
            raise MonitorContractError(
                f"data_gaps[{index}].code must be six digits or null"
            )
        _nonempty(item["field"], f"data_gaps[{index}].field")
        _nonempty(item["minimum_action"], f"data_gaps[{index}].minimum_action")

    stop_reason = value["stop_reason"]
    if stop_reason is not None and (
        not isinstance(stop_reason, str) or stop_reason != "clean_fast_gate"
    ):
        raise MonitorContractError("stop_reason is unsupported")
    confirmation = value["requires_user_confirmation"]
    if type(confirmation) is not bool:
        raise MonitorContractError("requires_user_confirmation must be a boolean")
    manifest = _object(value["manifest"], "manifest")
    _required(manifest, {"writes", "stop_reason"}, "manifest")
    if type(manifest["writes"]) is not bool or manifest["writes"]:
        raise MonitorContractError("manifest.writes must be false")
    if manifest["stop_reason"] != stop_reason:
        raise MonitorContractError("manifest.stop_reason must match stop_reason")

    budget_escalations = [
        item for item in escalations if item["reason_code"] == "risk_budget_exceeded"
    ]
    if any(
        item["code"] is not None
        and item["code"] not in {holding["code"] for holding in holdings}
        for item in budget_escalations
    ):
        raise MonitorContractError(
            "position budget escalation requires an active holding code"
        )
    if len({item["code"] for item in budget_escalations}) != len(budget_escalations):
        raise MonitorContractError("duplicate risk budget escalation scope/code")
    if budget_escalations:
        known = account["known_stop_risk_lower_bound"]
        if known is None or known <= 0:
            raise MonitorContractError(
                "budget escalation requires a positive known risk lower bound"
            )
        for escalation in budget_escalations:
            if not any(
                (escalation["code"] is None or item["code"] == escalation["code"])
                and item.get("stop_risk") is not None
                and item["stop_risk"] > 0
                for item in holdings
            ):
                raise MonitorContractError(
                    "budget escalation requires corresponding holding risk evidence"
                )
    if budget_escalations and (
        budget_status != "over_budget"
        or any(item["candidate"] != "review" for item in budget_escalations)
    ):
        raise MonitorContractError(
            "budget escalations require over_budget and review candidates"
        )
    if budget_status == "over_budget" and (
        not budget_escalations
        or value["review_status"] == "cleared"
        or action_status == "no_action"
        or stop_reason == "clean_fast_gate"
    ):
        raise MonitorContractError(
            "over_budget cannot clear review or produce no_action/clean"
        )
    if (
        holdings
        and budget_status is None
        and (value["review_status"] == "cleared" or action_status == "no_action")
    ):
        raise MonitorContractError("unknown holding risk budget cannot clear review")
    if stop_reason == "clean_fast_gate" and (
        budget_status != "within_budget"
        or account["portfolio_value"] is None
        or holdings
        and (
            account["stock_market_value"] is None
            or account["stock_weight_pct"] is None
            or any(
                item.get(field) is None
                for item in holdings
                for field in (
                    "market_value",
                    "stop_risk",
                    "stop_risk_pct",
                    "portfolio_weight_pct",
                )
            )
        )
    ):
        raise MonitorContractError(
            "clean_fast_gate requires complete budget safety evidence"
        )

    if (
        action_status == "no_action" or value["review_status"] == "cleared"
    ) and stop_reason != "clean_fast_gate":
        raise MonitorContractError(
            "cleared/no_action requires clean_fast_gate safety evidence"
        )

    if data_status != "complete" and action_status == "no_action":
        raise MonitorContractError("incomplete data cannot produce no_action")
    if action_status == "trade_candidate" and not any(
        item["candidate"] == "trade" for item in escalations
    ):
        raise MonitorContractError("trade_candidate requires a trade escalation")
    if confirmation != (action_status == "trade_candidate"):
        raise MonitorContractError(
            "requires_user_confirmation does not match action_status"
        )
    if (
        industry_status in {"stale", "invalid", "unavailable"}
        and holdings
        and not any(item["field"] == "industry_context" for item in gaps)
    ):
        raise MonitorContractError("degraded industry_context requires a data gap")
    if stop_reason == "clean_fast_gate":
        for holding in holdings:
            quote = holding["quote"]
            if quote.get("status") != "fresh":
                raise MonitorContractError(
                    "clean_fast_gate requires fresh holding quotes"
                )
            for field, number in (
                ("price", quote.get("price")),
                ("stop_loss_20", holding.get("stop_loss_20")),
            ):
                if (
                    isinstance(number, bool)
                    or not isinstance(number, (int, float))
                    or number <= 0
                ):
                    raise MonitorContractError(
                        f"clean_fast_gate requires valid {field}"
                    )
            if type(holding.get("shares")) is not int or holding["shares"] <= 0:
                raise MonitorContractError("clean_fast_gate requires valid shares")
            _nonempty(quote.get("source"), "clean quote.source")
            _iso8601(quote.get("as_of"), "clean quote.as_of")
    if stop_reason == "clean_fast_gate" and (
        value["data_status"] != "complete"
        or value["valuation_status"] != "exact"
        or value["review_status"] != "cleared"
        or action_status != "no_action"
        or escalations
        or gaps
        or not coverage["complete"]
    ):
        raise MonitorContractError("invalid clean_fast_gate")
    return value


def loads_monitor_snapshot(text: str) -> dict[str, Any]:
    """Parse and validate one monitor-v1 snapshot."""
    try:
        payload = json.loads(
            text,
            parse_constant=lambda constant: (_ for _ in ()).throw(
                MonitorContractError(f"all numbers must be finite ({constant})")
            ),
        )
    except MonitorContractError:
        raise
    except (TypeError, json.JSONDecodeError) as exc:
        raise MonitorContractError(f"invalid monitor JSON: {exc}") from exc
    return validate_monitor_snapshot(payload)


def dumps_monitor_snapshot(payload: object) -> str:
    """Validate and emit deterministic monitor-v1 JSON."""
    return json.dumps(
        validate_monitor_snapshot(payload),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
