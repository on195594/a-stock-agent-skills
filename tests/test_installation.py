from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from a_stock_agent_runtime.install import _backup


# Resolved against the real environment at import time, before any test swaps HOME.
# The installer shells out to `uv build`, which needs its package cache to satisfy
# `build-system.requires` while UV_OFFLINE is set; a relocated HOME would hide it.
UV_CACHE_DIR = os.environ.get("UV_CACHE_DIR") or str(
    Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "uv"
)

# a-stock-lib is deliberately not a declared dependency: the installer takes an
# explicit checkout or wheel and records its provenance.  Tests locate it the same
# way an operator would, and skip rather than fail when it is not provisioned here.
LIB_ROOT = Path(os.environ.get("A_STOCK_LIB_SOURCE") or Path.home() / "a-stock-lib")
LIB_WHEEL = LIB_ROOT / "dist" / "a_stock_lib-0.5.2-py3-none-any.whl"

_MISSING = f"a-stock-lib not provisioned at {LIB_ROOT}; set A_STOCK_LIB_SOURCE"
requires_lib_wheel = pytest.mark.skipif(not LIB_WHEEL.is_file(), reason=_MISSING)
requires_lib_checkout = pytest.mark.skipif(
    not (LIB_ROOT / "pyproject.toml").is_file(), reason=_MISSING
)


def _run(args, home):
    uv = shutil.which("uv")
    assert uv
    env = {
        **os.environ,
        "HOME": str(home),
        "PATH": f"{home / '.local/bin'}:{Path(uv).parent}:/usr/bin:/bin",
        "UV_OFFLINE": "1",
        "UV_CACHE_DIR": UV_CACHE_DIR,
    }
    return subprocess.run([sys.executable, "scripts/install.py", *args], env=env, capture_output=True, text=True, check=False)


@requires_lib_wheel
def test_dry_run_has_no_files(tmp_path) -> None:
    result = _run(["--client", "all", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-wheel", str(LIB_WHEEL), "--dry-run"], tmp_path)
    assert result.returncode == 0, result.stderr
    assert list(tmp_path.iterdir()) == []


@requires_lib_wheel
def test_copy_install_has_manifest_and_stable_cli(tmp_path) -> None:
    result = _run(["--client", "codex", "--mode", "copy", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-wheel", str(LIB_WHEEL)], tmp_path)
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


@requires_lib_checkout
def test_source_checkout_bootstrap_records_lib_provenance(tmp_path) -> None:
    result = _run(["--client", "claude", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-source", str(LIB_ROOT)], tmp_path)
    assert result.returncode == 0, result.stderr
    metadata = next((tmp_path / ".local/share/a-stock-agent/runtime").glob("*/a-stock-lib-install.json"))
    payload = json.loads(metadata.read_text(encoding="utf-8"))
    assert payload["name"] == "a-stock-lib"
    assert payload["version"] == "0.5.2"
    assert len(payload["wheel_sha256"]) == 64


@requires_lib_wheel
def test_existing_skill_is_rejected_before_runtime_install(tmp_path) -> None:
    target = tmp_path / ".agents/skills/a-stock-research"
    target.mkdir(parents=True)
    result = _run(["--client", "codex", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-wheel", str(LIB_WHEEL)], tmp_path)
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
