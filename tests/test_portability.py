from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_console_scripts_work_from_random_cwd() -> None:
    root = Path(__file__).resolve().parents[1]
    env = {**os.environ, "A_STOCK_STATE_DIR": "/tmp/a-stock-agent-portability-test"}
    for command in ("a-stock-cache", "a-stock-fetch", "a-stock-install"):
        result = subprocess.run([str(root / ".venv/bin" / command), "--help"], cwd="/tmp", env=env, capture_output=True, text=True, check=False)
        assert result.returncode == 0, (command, result.stderr)
