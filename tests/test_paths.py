from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from a_stock_agent_runtime import paths


def test_default_paths_are_external_and_configurable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CACHE_DB_PATH", raising=False)
    assert paths.cache_db_path() == tmp_path / ".local/share/a-stock-agent/cache.db"
    assert ".claude" not in str(paths.cache_db_path())
    monkeypatch.setenv("A_STOCK_STATE_DIR", str(tmp_path / "changed"))
    assert paths.cache_db_path() == tmp_path / "changed/cache.db"


def test_invalid_config_permissions_fail_closed(monkeypatch, tmp_path) -> None:
    config = tmp_path / "runtime.env"
    config.write_text("A_STOCK_STATE_DIR=/tmp/state\n", encoding="utf-8")
    config.chmod(0o644)
    monkeypatch.setenv("A_STOCK_CONFIG_FILE", str(config))
    try:
        paths.cache_db_path()
    except RuntimeError as exc:
        assert "0600" in str(exc)
    else:
        raise AssertionError("insecure config was accepted")


def test_importing_paths_does_not_create_home_state(tmp_path) -> None:
    config = tmp_path / "runtime.env"
    config.write_text("A_STOCK_STATE_DIR=/unused\n", encoding="utf-8")
    config.chmod(0o644)
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        "A_STOCK_CONFIG_FILE": str(config),
    }
    result = subprocess.run(
        [sys.executable, "-c", "import a_stock_agent_runtime.paths"],
        cwd=tmp_path.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / ".local").exists()
