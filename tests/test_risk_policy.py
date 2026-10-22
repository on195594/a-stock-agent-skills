"""S3a/P13/P22: synthetic policy sources, not confirmed personal settings."""

import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from a_stock_agent_runtime import (
    cache,
    commands_holdings,
    paths,
    risk_budget,
    risk_policy,
)
from tests.helpers import mock_price_quotes
from tests.monitor.test_monitor_snapshot import _quotes, _seed_holding

NOW = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def isolated_policy_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.delenv("A_STOCK_CONFIG_FILE", raising=False)
    monkeypatch.delenv("A_STOCK_RISK_POLICY_FILE", raising=False)


def _policy(**updates):
    return {
        "schema_version": 1,
        "policy_id": "fixture-policy",
        "account_scope": "fixture-account",
        "currency": "CNY",
        "effective_from": "2000-01-01T00:00:00+08:00",
        "effective_to": "2999-01-01T00:00:00+08:00",
        "confirmed_at": "2000-01-01T00:00:00+08:00",
        "confirmation_ref": "fixture:explicit-confirmation-not-a-token",
        "max_position_risk_pct": 1,
        "max_portfolio_risk_pct": 6,
        **updates,
    }


def _file(path, value=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_policy() if value is None else value))
    path.chmod(0o600)
    return str(path)


def _resolve(**kwargs):
    return risk_policy.resolve_risk_parameters(now=NOW, **kwargs)


def test_absent_policy_does_not_create_files_and_retains_defaults(tmp_path):
    before = sorted(tmp_path.rglob("*"))
    result = _resolve(portfolio_value=100000)
    assert result.risk_policy == risk_budget.policy()
    assert result.denominator_evidence() == {
        "account_scope": None,
        "portfolio_value_as_of": None,
        "denominator_scope_status": "unknown",
        "denominator_freshness_status": "unknown",
        "denominator_requires_review": True,
        "denominator_components": {
            "account_value": 100000.0,
            "off_account_strategy_cash": 0.0,
        },
    }
    assert sorted(tmp_path.rglob("*")) == before
    assert "drawdown_observation_target_pct" not in result.risk_policy


def test_paths_priority_is_dynamic_cli_env_config_then_sibling_default(
    tmp_path, monkeypatch
):
    runtime = tmp_path / "custom/runtime.env"
    runtime.parent.mkdir()
    runtime.write_text(f"A_STOCK_RISK_POLICY_FILE={tmp_path / 'from-config.json'}\n")
    runtime.chmod(0o600)
    monkeypatch.setenv("A_STOCK_CONFIG_FILE", str(runtime))
    assert paths.risk_policy_path() == (tmp_path / "from-config.json", True)
    monkeypatch.setenv("A_STOCK_RISK_POLICY_FILE", str(tmp_path / "from-env.json"))
    assert paths.risk_policy_path() == (tmp_path / "from-env.json", True)
    assert paths.risk_policy_path(str(tmp_path / "from-cli.json")) == (
        tmp_path / "from-cli.json",
        True,
    )
    monkeypatch.delenv("A_STOCK_RISK_POLICY_FILE")
    runtime.write_text("# no selected policy\n")
    assert paths.risk_policy_path() == (runtime.with_name("risk-policy.json"), False)


@pytest.mark.parametrize("source", ["cli", "env", "runtime", "default"])
def test_policy_sources_load_without_creating_or_modifying_input(
    source, tmp_path, monkeypatch
):
    path = tmp_path / "policy.json"
    if source == "default":
        path, configured = paths.risk_policy_path()
        assert not configured
    _file(path)
    kwargs = {"account_scope": "fixture-account"}
    if source == "cli":
        kwargs["policy_file"] = str(path)
    elif source == "env":
        monkeypatch.setenv("A_STOCK_RISK_POLICY_FILE", str(path))
    elif source == "runtime":
        runtime = tmp_path / "runtime.env"
        runtime.write_text(f"A_STOCK_RISK_POLICY_FILE={path}\n")
        runtime.chmod(0o600)
        monkeypatch.setenv("A_STOCK_CONFIG_FILE", str(runtime))
    before = path.read_bytes()
    result = _resolve(**kwargs)
    assert result.risk_policy["source"] == "policy_file"
    assert result.risk_policy["policy_id"] == "fixture-policy"
    assert result.risk_policy["max_position_risk_pct"] == 1
    assert result.risk_policy["field_sources"] == {
        "max_position_risk_pct": "policy_file",
        "max_portfolio_risk_pct": "policy_file",
    }
    assert path.read_bytes() == before


def test_numeric_override_is_per_field_and_does_not_reconfirm_policy(tmp_path):
    path = _file(tmp_path / "policy.json", _policy(drawdown_observation_target_pct=7))
    result = _resolve(
        policy_file=path, account_scope="fixture-account", max_position_risk_pct=3
    )
    assert result.risk_policy["max_position_risk_pct"] == 3
    assert result.risk_policy["max_portfolio_risk_pct"] == 6
    assert result.risk_policy["drawdown_observation_target_pct"] == 7
    assert result.risk_policy["source"] == "cli_override"
    assert result.risk_policy["field_sources"]["max_position_risk_pct"] == "cli"
    assert (
        result.risk_policy["field_sources"]["max_portfolio_risk_pct"] == "policy_file"
    )
    assert json.loads(Path(path).read_text())["max_position_risk_pct"] == 1


@pytest.mark.parametrize(
    "field,bad",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("schema_version", 1.0),
        ("policy_id", ""),
        ("account_scope", "other"),
        ("currency", "USD"),
        ("confirmation_ref", None),
        ("confirmed_at", ""),
        ("confirmed_at", "2999-01-01T00:00:00Z"),
        ("effective_from", "2999-01-01T00:00:00Z"),
        ("effective_to", "2001-01-01T00:00:00Z"),
        ("effective_to", "1900-01-01T00:00:00Z"),
        ("effective_from", "2026-01-01"),
        ("confirmed_at", "not-a-date"),
        ("max_position_risk_pct", True),
        ("max_position_risk_pct", float("nan")),
        ("max_portfolio_risk_pct", float("inf")),
        ("max_portfolio_risk_pct", 0),
        ("max_portfolio_risk_pct", 101),
        ("drawdown_observation_target_pct", -1),
        ("max_position_risk_pct", "2"),
    ],
)
def test_invalid_file_never_falls_back_even_with_cli_overrides(field, bad, tmp_path):
    path = _file(tmp_path / "policy.json", _policy(**{field: bad}))
    with pytest.raises(risk_policy.RiskPolicyError):
        _resolve(
            policy_file=path,
            account_scope="fixture-account",
            max_position_risk_pct=3,
            max_portfolio_risk_pct=9,
        )


@pytest.mark.parametrize("field", ["max_position_risk_pct", "max_portfolio_risk_pct"])
@pytest.mark.parametrize(
    "bad", [True, False, 0, -1, 100.01, float("inf"), float("nan")]
)
def test_invalid_override_is_controlled(field, bad):
    with pytest.raises(risk_policy.RiskPolicyError):
        _resolve(**{field: bad})


def test_file_without_explicit_matching_account_cannot_be_applied(tmp_path):
    path = _file(tmp_path / "policy.json")
    with pytest.raises(risk_policy.RiskPolicyError, match="account-scope"):
        _resolve(policy_file=path)


@pytest.mark.parametrize("source", ["cli", "env", "runtime"])
def test_explicit_missing_file_is_not_a_default(source, tmp_path, monkeypatch):
    missing = str(tmp_path / "does-not-exist.json")
    kwargs = {}
    if source == "cli":
        kwargs["policy_file"] = missing
    elif source == "env":
        monkeypatch.setenv("A_STOCK_RISK_POLICY_FILE", missing)
    else:
        path = tmp_path / "runtime.env"
        path.write_text(f"A_STOCK_RISK_POLICY_FILE={missing}")
        path.chmod(0o600)
        monkeypatch.setenv("A_STOCK_CONFIG_FILE", str(path))
    with pytest.raises(risk_policy.RiskPolicyError):
        _resolve(max_position_risk_pct=3, **kwargs)


@pytest.mark.parametrize(
    "case",
    [
        "permissions",
        "directory",
        "symlink",
        "owner",
        "duplicate",
        "malformed",
        "overflow",
        "array",
    ],
)
def test_discovered_bad_default_file_fails_closed(case, tmp_path, monkeypatch):
    path, _ = paths.risk_policy_path()
    _file(path)
    if case == "permissions":
        path.chmod(0o644)
    elif case in {"directory", "symlink"}:
        path.unlink()
        if case == "directory":
            path.mkdir()
        else:
            path.symlink_to(tmp_path / "missing-target")
    elif case == "owner":
        monkeypatch.setattr(
            paths.os,
            "fstat",
            lambda fd: SimpleNamespace(st_uid=os.getuid() + 1, st_mode=0o100600),
        )
    else:
        path.write_text(
            {
                "duplicate": '{"schema_version":1,"schema_version":1}',
                "malformed": "not-json",
                "overflow": '{"x":1e999}',
                "array": "[]",
            }[case]
        )
    with pytest.raises(risk_policy.RiskPolicyError):
        _resolve(account_scope="fixture-account", max_position_risk_pct=3)


@pytest.mark.parametrize(
    "scope,as_of,review",
    [
        (None, None, True),
        ("fixture-account", None, True),
        (None, "2026-09-16T16:00:00+08:00", True),
        ("fixture-account", "2000-01-01T16:00:00+08:00", False),
    ],
)
def test_denominator_provenance_never_uses_collection_time_or_invents_ttl(
    scope, as_of, review
):
    result = _resolve(
        portfolio_value=100000, account_scope=scope, portfolio_value_as_of=as_of
    )
    evidence = result.denominator_evidence()
    assert evidence["portfolio_value_as_of"] == as_of
    assert evidence["denominator_requires_review"] is review
    assert evidence["denominator_freshness_status"] == (
        "as_of_provided" if as_of else "unknown"
    )
    assert "drawdown_observation_target_pct" not in result.risk_policy


@pytest.mark.parametrize("bad", ["2026-09-16", "2999-01-01T00:00:00Z", "bad", True])
def test_bad_denominator_time_cannot_be_used(bad):
    with pytest.raises(risk_policy.RiskPolicyError):
        _resolve(portfolio_value_as_of=bad)


@pytest.mark.parametrize("override", [False, True])
def test_both_public_clis_use_identical_effective_policy_and_denominator(
    override, tmp_path, isolated_cache_database, monkeypatch, capsys
):
    _seed_holding(isolated_cache_database, "600000")
    mock_price_quotes(monkeypatch, _quotes)
    path = _file(tmp_path / "policy.json")
    args = [
        "--portfolio-value",
        "100000",
        "--policy-file",
        path,
        "--account-scope",
        "fixture-account",
        "--portfolio-value-as-of",
        "2000-01-01T16:00:00+08:00",
    ]
    if override:
        args += ["--max-position-risk-pct", "3"]
    assert cache.main(["monitor-snapshot", *args, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    account = payload["account"]
    assert account["risk_budget_status"] == (
        "within_budget" if override else "over_budget"
    )
    assert account["risk_policy"]["source"] == (
        "cli_override" if override else "policy_file"
    )
    assert account["portfolio_value_as_of"] == "2000-01-01T16:00:00+08:00"
    assert account["denominator_freshness_status"] == "as_of_provided"
    assert account["denominator_scope_status"] == "provided"
    assert cache.main(["portfolio-risk", *args]) == 0
    text = capsys.readouterr().out
    assert ("已知超预算" in text) is not override
    assert "fixture-policy" in text and "fixture-account" in text
    assert "2000-01-01T16:00:00+08:00" in text
    assert account["risk_policy"]["source"] in text
    assert json.loads(Path(path).read_text())["max_position_risk_pct"] == 1


@pytest.mark.parametrize("command", ["portfolio-risk", "monitor-snapshot"])
def test_invalid_runtime_config_is_controlled_before_policy_use(
    command, tmp_path, monkeypatch, capsys
):
    runtime = tmp_path / "runtime.env"
    runtime.write_text("A_STOCK_RISK_POLICY_FILE=missing.json\n")
    runtime.chmod(0o644)
    monkeypatch.setenv("A_STOCK_CONFIG_FILE", str(runtime))
    args = [command, "--json"] if command == "monitor-snapshot" else [command]
    assert cache.main(args) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "运行配置不可用" in captured.err


@pytest.mark.parametrize("command", ["portfolio-risk", "monitor-snapshot"])
def test_policy_error_precedes_database_network_and_has_no_report(
    command, tmp_path, monkeypatch, capsys
):
    path = _file(tmp_path / "policy.json", _policy(confirmation_ref=""))
    monkeypatch.setattr(
        commands_holdings.db,
        "read_only_db_session",
        lambda *a: pytest.fail("database access"),
    )
    monkeypatch.setattr(socket.socket, "connect", lambda *a: pytest.fail("network"))
    args = [
        command,
        "--policy-file",
        path,
        "--account-scope",
        "fixture-account",
        "--max-position-risk-pct",
        "3",
    ]
    if command == "monitor-snapshot":
        args += ["--json"]
    assert cache.main(args) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "风险参数不可用" in captured.err


def test_off_account_strategy_cash_extends_cli_denominator_in_both_clis(
    tmp_path, isolated_cache_database, monkeypatch, capsys
):
    _seed_holding(isolated_cache_database, "600000")
    mock_price_quotes(monkeypatch, _quotes)
    path = _file(tmp_path / "policy.json", _policy(off_account_strategy_cash=150000))
    args = [
        "--portfolio-value", "100000", "--policy-file", path,
        "--account-scope", "fixture-account",
    ]
    assert cache.main(["monitor-snapshot", *args, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    account = payload["account"]
    # 2000 CNY at risk: 2% of the broker account alone, 0.8% of strategy capital.
    assert account["portfolio_value"] == 250000
    assert account["denominator_components"] == {
        "account_value": 100000.0,
        "off_account_strategy_cash": 150000.0,
    }
    assert account["risk_budget_status"] == "within_budget"
    assert account["risk_policy"]["field_sources"]["off_account_strategy_cash"] == (
        "policy_file"
    )
    assert payload["manifest"]["denominator_source"] == "cli+policy_file"
    assert payload["holdings"][0]["stop_risk_unrealized_gain"] == 0
    assert cache.main(["portfolio-risk", *args]) == 0
    text = capsys.readouterr().out
    assert "账户外策略现金 150000.00元" in text and "已知超预算" not in text


def test_off_account_strategy_cash_never_creates_a_denominator(tmp_path):
    path = _file(tmp_path / "policy.json", _policy(off_account_strategy_cash=5000))
    result = _resolve(policy_file=path, account_scope="fixture-account")
    assert result.portfolio_value is None
    assert result.denominator_evidence()["denominator_components"] is None
    assert result.denominator_source() is None


@pytest.mark.parametrize("bad", [-1, True, "1000", None])
def test_invalid_off_account_strategy_cash_fails_closed(bad, tmp_path):
    path = _file(tmp_path / "policy.json", _policy(off_account_strategy_cash=bad))
    with pytest.raises(risk_policy.RiskPolicyError):
        _resolve(portfolio_value=1, policy_file=path, account_scope="fixture-account")


@pytest.mark.parametrize(
    ("price", "reference_cost", "gain"),
    [
        (29.41, 25.2014, 800 * (29.41 - 25.2014)),  # 600900 on 2026-10-15
        (24.0, 25.2014, 0.0),  # below reference cost: all principal
        (29.41, 19.0, 800 * (29.41 - 20.665)),  # cost below stop: all gain
        (29.41, None, None),  # unknown cost: attribution unknown
    ],
)
def test_stop_risk_splits_into_principal_and_unrealized_gain(
    price, reference_cost, gain
):
    risk = commands_holdings.calculate_position_risk(
        800, price, 20.665, 75911.02, reference_cost
    )
    assert risk["stop_risk"] == pytest.approx(800 * (price - 20.665))
    assert risk["stop_risk_unrealized_gain"] == (
        None if gain is None else pytest.approx(gain)
    )


def test_breach_detail_reports_drivers_and_unknown_attribution():
    limits = risk_budget.policy(6, 18)
    positions = [
        {"code": "600900", "stop_risk": 6996.0, "stop_risk_unrealized_gain": 3366.88},
        {"code": "603606", "stop_risk": 8000.0, "stop_risk_unrealized_gain": None},
    ]
    breaches = risk_budget.assess(
        positions, 75911.02, limits, denominator_source="cli+policy_file"
    )["breaches"]
    detail = {item["code"]: item["detail"] for item in breaches}
    assert "principal=3629.12 CNY; unrealized_gain=3366.88 CNY" in detail["600900"]
    assert "denominator_source=cli+policy_file" in detail["600900"]
    assert "principal=unknown; unrealized_gain=unknown" in detail[None]
