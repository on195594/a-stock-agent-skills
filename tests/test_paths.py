from __future__ import annotations

import os
import subprocess
import sys

from a_stock_agent_runtime import paths


def test_default_paths_are_external_and_configurable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CACHE_DB_PATH", raising=False)
    assert paths.cache_db_path() == tmp_path / ".local/share/a-stock-agent/cache.db"
    assert ".claude" not in str(paths.cache_db_path())


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
    env = {**os.environ, "HOME": str(tmp_path), "PYTHONPATH": "src"}
    result = subprocess.run(
        [sys.executable, "-c", "import a_stock_agent_runtime.paths"],
        cwd=tmp_path.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0 or not (tmp_path / ".local").exists()


def test_prompt_renderer_requires_explicit_external_root(tmp_path) -> None:
    env = {**os.environ, "HOME": str(tmp_path), "PYTHONPATH": "src"}
    env.pop("A_STOCK_LIB_ROOT", None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from a_stock_agent_runtime.paths import PROMPT_RENDERER; assert PROMPT_RENDERER is None",
        ],
        cwd=tmp_path.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
