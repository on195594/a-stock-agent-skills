from __future__ import annotations

import importlib
from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys

import pytest


MODULES = (
    "cache",
    "fetcher",
    "checklist",
    "framework_metadata",
    "framework_catalog",
    "market_quotes",
    "position_ledger",
    "schema_ledger",
    "paths",
    "domain",
    "db",
    "schema",
    "store",
    "commands_analysis",
    "commands_holdings",
    "commands_monitor",
    "commands_admin",
)


def test_runtime_modules_import_from_package() -> None:
    for module in MODULES:
        importlib.import_module(f"a_stock_agent_runtime.{module}")


def test_no_legacy_top_level_runtime_imports() -> None:
    root = Path(__file__).resolve().parents[1] / "src/a_stock_agent_runtime"
    text = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    assert "from project_paths" not in text
    assert "import project_paths" not in text
    assert "from cache import" not in text


def test_checklist_does_not_import_cache() -> None:
    root = Path(__file__).resolve().parents[1] / "src/a_stock_agent_runtime"
    assert "import cache" not in (root / "checklist.py").read_text(encoding="utf-8")


def test_command_modules_do_not_import_cache() -> None:
    root = Path(__file__).resolve().parents[1] / "src/a_stock_agent_runtime"
    for path in root.glob("commands_*.py"):
        assert "import cache" not in path.read_text(encoding="utf-8")


def test_domain_routing_is_independent_of_checklist_import_order() -> None:
    root = Path(__file__).resolve().parents[1]
    domain_source = root / "src/a_stock_agent_runtime/domain.py"
    assert "import checklist" not in domain_source.read_text(encoding="utf-8")
    script = (
        "import sys; from a_stock_agent_runtime import domain; "
        "assert 'a_stock_agent_runtime.checklist' not in sys.modules; "
        "assert domain.infer_framework('煤炭开采') == ('C资源', True); "
        "assert domain.get_stop_loss_pct('F科技') == (0.80, 0.72)"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_commands_monitor_observes_holdings_owner_patches(monkeypatch) -> None:
    from a_stock_agent_runtime import commands_holdings, commands_monitor, db

    def patched_parser(*_args, **_kwargs):
        raise RuntimeError("parser owner patch observed")

    monkeypatch.setattr(commands_holdings, "_parse_cli_finite_float", patched_parser)
    with pytest.raises(RuntimeError, match="parser owner patch observed"):
        commands_monitor.cmd_tier_config(["000001", "B", "1"])

    @contextmanager
    def fake_db_session():
        yield object()

    def patched_holding(*_args, **_kwargs):
        raise RuntimeError("holding owner patch observed")

    monkeypatch.setattr(db, "db_session", fake_db_session)
    monkeypatch.setattr(commands_holdings, "_single_open_holding", patched_holding)
    with pytest.raises(RuntimeError, match="holding owner patch observed"):
        commands_monitor.cmd_l3_add(["000001", "original", "condition"])
