from __future__ import annotations

import json
import os
import subprocess
import sys


def _run(args, home, path):
    env = {**os.environ, "HOME": str(home), "PATH": f"{home / '.local/bin'}:/usr/bin:/bin"}
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


def test_source_checkout_bootstrap_records_lib_provenance(tmp_path) -> None:
    lib_source = "/home/lin/a-stock-lib"
    result = _run(["--client", "claude", "--source", ".", "--target-root", str(tmp_path), "--a-stock-lib-source", lib_source], tmp_path, "")
    assert result.returncode == 0, result.stderr
    metadata = next((tmp_path / ".local/share/a-stock-agent/runtime").glob("*/a-stock-lib-install.json"))
    payload = json.loads(metadata.read_text(encoding="utf-8"))
    assert payload["name"] == "a-stock-lib"
    assert payload["version"] == "0.4.1"
    assert len(payload["wheel_sha256"]) == 64
