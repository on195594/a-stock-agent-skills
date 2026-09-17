"""Resolve one effective read-only risk policy; never create or confirm a file."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any

from a_stock_agent_runtime import paths, risk_budget


class RiskPolicyError(ValueError):
    """Selected policy or explicit risk parameters cannot be used safely."""


@dataclass(frozen=True)
class RiskParameters:
    portfolio_value: float | None
    risk_policy: dict[str, Any]
    account_scope: str | None = None
    portfolio_value_as_of: str | None = None

    def denominator_evidence(self) -> dict[str, Any]:
        has_value = self.portfolio_value is not None
        scope_known = has_value and self.account_scope is not None
        as_of_known = has_value and self.portfolio_value_as_of is not None
        return {
            "account_scope": self.account_scope,
            "portfolio_value_as_of": self.portfolio_value_as_of,
            "denominator_scope_status": "provided" if scope_known else "unknown",
            "denominator_freshness_status": "as_of_provided"
            if as_of_known
            else "unknown",
            "denominator_requires_review": not (scope_known and as_of_known),
        }


def _nonempty(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RiskPolicyError(f"{field} must be a non-empty string")
    return value.strip()


def _timestamp(value: object, field: str) -> datetime:
    try:
        result = datetime.fromisoformat(_nonempty(value, field))
    except ValueError as exc:
        raise RiskPolicyError(f"{field} must be an ISO-8601 timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise RiskPolicyError(f"{field} must be timezone-aware")
    return result


def _limit(value: object, field: str) -> float:
    if not risk_budget.positive_number(value) or value > 100:
        raise RiskPolicyError(f"{field} must be a finite number in (0, 100]")
    return float(value)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RiskPolicyError("duplicate JSON key in risk policy")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise RiskPolicyError("risk policy JSON numbers must be finite")


def _json_float(value: str) -> float:
    number = float(value)
    if not risk_budget.finite_number(number):
        _reject_constant(value)
    return number


def _load_policy(path: str | None, scope: str | None, now: datetime) -> dict | None:
    try:
        selected, configured = paths.risk_policy_path(path)
        if not selected.exists() and not selected.is_symlink() and not configured:
            return None
        text = paths.read_private_config(selected, label="risk policy")
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
            parse_float=_json_float,
        )
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        # Do not echo policy contents, confirmation references or JSON snippets.
        raise RiskPolicyError(
            f"cannot read a valid selected risk policy: {type(exc).__name__}"
        ) from exc
    if (
        not isinstance(value, dict)
        or type(value.get("schema_version")) is not int
        or value["schema_version"] != 1
    ):
        raise RiskPolicyError("risk policy schema_version must be integer 1")
    for field in ("policy_id", "account_scope", "confirmation_ref"):
        value[field] = _nonempty(value.get(field), field)
    if value.get("currency") != "CNY":
        raise RiskPolicyError("risk policy currency must be CNY")
    if scope is None or value["account_scope"] != scope:
        raise RiskPolicyError(
            "risk policy requires a matching explicit --account-scope"
        )
    start = _timestamp(value.get("effective_from"), "effective_from")
    end = (
        _timestamp(value["effective_to"], "effective_to")
        if "effective_to" in value
        else None
    )
    confirmed = _timestamp(value.get("confirmed_at"), "confirmed_at")
    if end is not None and end <= start:
        raise RiskPolicyError("effective_to must be after effective_from")
    if start > now or end is not None and now > end or confirmed > now:
        raise RiskPolicyError("risk policy is not currently effective and confirmed")
    for field in ("max_position_risk_pct", "max_portfolio_risk_pct"):
        value[field] = _limit(value.get(field), field)
    if "drawdown_observation_target_pct" in value:
        value["drawdown_observation_target_pct"] = _limit(
            value["drawdown_observation_target_pct"], "drawdown_observation_target_pct"
        )
    return value


def resolve_risk_parameters(
    *,
    portfolio_value: float | None = None,
    policy_file: str | None = None,
    account_scope: str | None = None,
    portfolio_value_as_of: str | None = None,
    max_position_risk_pct: float | None = None,
    max_portfolio_risk_pct: float | None = None,
    now: datetime | None = None,
) -> RiskParameters:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise RiskPolicyError("policy evaluation time must be timezone-aware")
    if portfolio_value is not None and not risk_budget.positive_number(portfolio_value):
        raise RiskPolicyError("portfolio value must be positive and finite")
    scope = (
        _nonempty(account_scope, "account_scope") if account_scope is not None else None
    )
    as_of = None
    if portfolio_value_as_of is not None:
        timestamp = _timestamp(portfolio_value_as_of, "portfolio_value_as_of")
        if timestamp > current:
            raise RiskPolicyError("portfolio value as-of cannot be in the future")
        as_of = timestamp.isoformat()
    # Always validate the selected file BEFORE any per-call numeric override.
    if policy_file is not None:
        policy_file = _nonempty(policy_file, "policy_file")
    file_policy = _load_policy(policy_file, scope, current)
    for field, override in (
        ("max_position_risk_pct", max_position_risk_pct),
        ("max_portfolio_risk_pct", max_portfolio_risk_pct),
    ):
        if override is not None:
            _limit(override, field)
    if file_policy is None:
        effective = risk_budget.policy(max_position_risk_pct, max_portfolio_risk_pct)
    else:
        effective = {
            "policy_id": file_policy["policy_id"],
            "source": "policy_file",
            "account_scope": file_policy["account_scope"],
            "currency": "CNY",
            "effective_from": file_policy["effective_from"],
            "effective_to": file_policy.get("effective_to"),
            "confirmed_at": file_policy["confirmed_at"],
            "confirmation_ref": file_policy["confirmation_ref"],
            "max_position_risk_pct": file_policy["max_position_risk_pct"],
            "max_portfolio_risk_pct": file_policy["max_portfolio_risk_pct"],
            "field_sources": {
                "max_position_risk_pct": "policy_file",
                "max_portfolio_risk_pct": "policy_file",
            },
        }
        if "drawdown_observation_target_pct" in file_policy:
            effective["drawdown_observation_target_pct"] = file_policy[
                "drawdown_observation_target_pct"
            ]
            effective["field_sources"]["drawdown_observation_target_pct"] = (
                "policy_file"
            )
        for field, override in (
            ("max_position_risk_pct", max_position_risk_pct),
            ("max_portfolio_risk_pct", max_portfolio_risk_pct),
        ):
            if override is not None:
                effective[field] = float(override)
                effective["field_sources"][field] = "cli"
                effective["source"] = "cli_override"
    return RiskParameters(portfolio_value, effective, scope, as_of)


def parse_risk_args(args: list[str] | None) -> RiskParameters:
    """Shared handler-independent parsing for both risk CLI commands."""
    options = {
        "--portfolio-value": "portfolio_value",
        "--policy-file": "policy_file",
        "--account-scope": "account_scope",
        "--portfolio-value-as-of": "portfolio_value_as_of",
        "--max-position-risk-pct": "max_position_risk_pct",
        "--max-portfolio-risk-pct": "max_portfolio_risk_pct",
    }
    numeric = {"portfolio_value", "max_position_risk_pct", "max_portfolio_risk_pct"}
    args = args or []
    values: dict[str, Any] = {}
    if len(args) % 2:
        raise RiskPolicyError("risk CLI options require a value")
    for option, raw in zip(args[::2], args[1::2], strict=True):
        if option not in options or options[option] in values:
            raise RiskPolicyError("unknown or duplicate risk CLI option")
        name = options[option]
        try:
            values[name] = float(raw) if name in numeric else _nonempty(raw, name)
        except ValueError as exc:
            raise RiskPolicyError(f"invalid {option}") from exc
    return resolve_risk_parameters(**values)
