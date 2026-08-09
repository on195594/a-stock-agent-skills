from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from a_stock_agent_runtime.install import _backup


def _run(args, home, path):
    uv = shutil.which("uv")
    assert uv
    env = {
        **os.environ,
        "HOME": str(home),
        "PATH": f"{home / '.local/bin'}:{Path(uv).parent}:/usr/bin:/bin",
        "UV_OFFLINE": "1",
    }
    return subprocess.run([sys.executable, "scripts/install.py", *args], env=env, capture_output=True, text=True, check=False)


def test_dry_run_has_no_files(tmp_path) -> None:
    wheel = "/home/lin/a-stock-lib/dist/a_stock_lib-0.4.1-py3-none-any.whl"
    result = _run(["--client", "all", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-wheel", wheel, "--dry-run"], tmp_path, "")
    assert result.returncode == 0, result.stderr
    assert list(tmp_path.iterdir()) == []


def test_copy_install_has_manifest_and_stable_cli(tmp_path) -> None:
    wheel = "/home/lin/a-stock-lib/dist/a_stock_lib-0.4.1-py3-none-any.whl"
    result = _run(["--client", "codex", "--mode", "copy", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-wheel", wheel], tmp_path, "")
    assert result.returncode == 0, result.stderr
    manifest = next((tmp_path / ".agents/skills/a-stock-research").glob(".a-stock-suite-manifest.json"))
    assert json.loads(manifest.read_text(encoding="utf-8"))["source_hash"]
    assert (tmp_path / ".local/bin/a-stock-cache").is_symlink()
    runtime = next((tmp_path / ".local/share/a-stock-agent/runtime").iterdir())
    module_path = subprocess.check_output(
        [str(runtime / "venv/bin/python"), "-c", "import a_stock_agent_runtime; print(a_stock_agent_runtime.__file__)"],
        text=True,
    ).strip()
    assert str(Path.cwd()) not in module_path


def test_source_checkout_bootstrap_records_lib_provenance(tmp_path) -> None:
    lib_source = "/home/lin/a-stock-lib"
    result = _run(["--client", "claude", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-source", lib_source], tmp_path, "")
    assert result.returncode == 0, result.stderr
    metadata = next((tmp_path / ".local/share/a-stock-agent/runtime").glob("*/a-stock-lib-install.json"))
    payload = json.loads(metadata.read_text(encoding="utf-8"))
    assert payload["name"] == "a-stock-lib"
    assert payload["version"] == "0.4.1"
    assert len(payload["wheel_sha256"]) == 64


def test_existing_skill_is_rejected_before_runtime_install(tmp_path) -> None:
    wheel = "/home/lin/a-stock-lib/dist/a_stock_lib-0.4.1-py3-none-any.whl"
    target = tmp_path / ".agents/skills/a-stock-research"
    target.mkdir(parents=True)
    result = _run(["--client", "codex", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-wheel", wheel], tmp_path, "")
    assert result.returncode == 1
    assert not (tmp_path / ".local/share/a-stock-agent/runtime").exists()


def test_backups_are_unique_within_one_second(tmp_path) -> None:
    target = tmp_path / "target"
    target.write_text("first", encoding="utf-8")
    first = _backup(target, tmp_path)
    target.write_text("second", encoding="utf-8")
    second = _backup(target, tmp_path)
    assert first != second
    assert first.read_text(encoding="utf-8") == "first"
    assert second.read_text(encoding="utf-8") == "second"
