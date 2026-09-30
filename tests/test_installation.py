from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
import tomllib

import pytest

from a_stock_agent_runtime import install
from a_stock_agent_runtime.install import _backup


# Resolved against the real environment at import time, before any test swaps HOME.
# The installer shells out to `uv build`, which needs its package cache to satisfy
# `build-system.requires` while UV_OFFLINE is set; a relocated HOME would hide it.
UV_CACHE_DIR = os.environ.get("UV_CACHE_DIR") or str(
    Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "uv"
)

# Explicit checkout/wheel inputs are release-candidate test paths. Normal installs
# resolve the immutable release dependency declared by this project's metadata.
LIB_SOURCE_OVERRIDE = os.environ.get("A_STOCK_LIB_SOURCE")
LIB_ROOT = Path(LIB_SOURCE_OVERRIDE) if LIB_SOURCE_OVERRIDE else None
LIB_WHEEL = (
    LIB_ROOT / "dist" / "a_stock_lib-0.8.0-py3-none-any.whl"
    if LIB_ROOT is not None
    else None
)

_MISSING = "a-stock-lib not provisioned; set A_STOCK_LIB_SOURCE"
requires_lib_wheel = pytest.mark.skipif(
    LIB_WHEEL is None or not LIB_WHEEL.is_file(), reason=_MISSING
)
requires_lib_checkout = pytest.mark.skipif(
    LIB_ROOT is None or not (LIB_ROOT / "pyproject.toml").is_file(), reason=_MISSING
)


def _run(args, home):
    uv = shutil.which("uv")
    assert uv
    env = {
        **os.environ,
        "HOME": str(home),
        "PATH": f"{home / '.local/bin'}:{Path(uv).parent}:/usr/bin:/bin",
        "UV_CACHE_DIR": UV_CACHE_DIR,
    }
    return subprocess.run(
        [sys.executable, "scripts/install.py", *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_dry_run_has_no_files(tmp_path) -> None:
    result = _run(
        [
            "--client",
            "all",
            "--source",
            ".",
            "--target-root",
            str(tmp_path),
            "--dry-run",
        ],
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert list(tmp_path.iterdir()) == []


def test_copy_install_has_manifest_and_stable_cli(tmp_path) -> None:
    old_bin = tmp_path / "old-runtime/bin"
    old_bin.mkdir(parents=True)
    for name in ("a-stock-cache", "a-stock-fetch", "a-stock-install"):
        command = old_bin / name
        command.write_text("old command", encoding="utf-8")
        link = tmp_path / ".local/bin" / name
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(command)
    result = _run(
        [
            "--client",
            "codex",
            "--mode",
            "copy",
            "--source",
            ".",
            "--target-root",
            str(tmp_path),
        ],
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    manifest = next(
        (tmp_path / ".agents/skills/a-stock-research").glob(
            ".a-stock-suite-manifest.json"
        )
    )
    assert json.loads(manifest.read_text(encoding="utf-8"))["source_hash"]
    assert (tmp_path / ".local/bin/a-stock-cache").is_symlink()
    rollback = max(
        (tmp_path / ".local/share/a-stock-agent").glob("rollback-*.json"),
        key=lambda path: path.stat().st_mtime_ns,
    )
    entries = json.loads(rollback.read_text(encoding="utf-8"))["entries"]
    command_entries = {
        Path(entry["target"]).name: Path(entry["backup"])
        for entry in entries
        if Path(entry["target"]).parent == tmp_path / ".local/bin"
    }
    assert set(command_entries) == {"a-stock-cache", "a-stock-fetch", "a-stock-install"}
    for name, backup in command_entries.items():
        assert backup.read_text(encoding="utf-8") == str(old_bin / name)
    runtime = next((tmp_path / ".local/share/a-stock-agent/runtime").iterdir())
    module_path = subprocess.check_output(
        [
            str(runtime / "venv/bin/python"),
            "-c",
            "import a_stock_agent_runtime; print(a_stock_agent_runtime.__file__)",
        ],
        text=True,
    ).strip()
    assert str(Path.cwd()) not in module_path
    assert "include-system-site-packages = false" in (
        runtime / "venv/pyvenv.cfg"
    ).read_text(encoding="utf-8")
    metadata = json.loads(
        (runtime / "a-stock-lib-install.json").read_text(encoding="utf-8")
    )
    assert metadata["version"] == "0.8.0"
    assert metadata["wheel_sha256"] == (
        "a811945b23d97eb121ff82d54bc0ba0810000a5379a9e9786fdcdc9220b30310"
    )
    installed = json.loads(
        subprocess.check_output(
            [
                str(runtime / "venv/bin/python"),
                "-c",
                (
                    "import importlib.metadata as m,json; "
                    "print(json.dumps({d.metadata['Name'].lower().replace('_','-'): "
                    "d.version for d in m.distributions()}))"
                ),
            ],
            text=True,
        )
    )
    locked = {
        package["name"].lower().replace("_", "-"): package["version"]
        for package in tomllib.loads(Path("uv.lock").read_text(encoding="utf-8"))[
            "package"
        ]
    }
    mismatches = {
        name: (version, locked[name])
        for name, version in installed.items()
        if name in locked and version != locked[name]
    }
    assert mismatches == {}


@requires_lib_checkout
def test_source_checkout_bootstrap_records_lib_provenance(tmp_path) -> None:
    result = _run(
        [
            "--client",
            "claude",
            "--source",
            ".",
            "--target-root",
            str(tmp_path),
            "--a-stock-lib-source",
            str(LIB_ROOT),
        ],
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    metadata = next(
        (tmp_path / ".local/share/a-stock-agent/runtime").glob(
            "*/a-stock-lib-install.json"
        )
    )
    payload = json.loads(metadata.read_text(encoding="utf-8"))
    assert payload["name"] == "a-stock-lib"
    assert payload["version"] == "0.8.0"
    assert len(payload["wheel_sha256"]) == 64
    wheel = Path(payload["wheel"])
    assert wheel.is_file()
    assert wheel.parent == metadata.parent / "artifacts"
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() == payload["wheel_sha256"]


@requires_lib_wheel
def test_existing_skill_is_rejected_before_runtime_install(tmp_path) -> None:
    target = tmp_path / ".agents/skills/a-stock-research"
    target.mkdir(parents=True)
    result = _run(
        [
            "--client",
            "codex",
            "--source",
            ".",
            "--target-root",
            str(tmp_path),
            "--a-stock-lib-wheel",
            str(LIB_WHEEL),
        ],
        tmp_path,
    )
    assert result.returncode == 1
    assert not (tmp_path / ".local/share/a-stock-agent/runtime").exists()


def test_copy_install_excludes_generated_files_from_payload_and_hash(
    tmp_path, monkeypatch
) -> None:
    source = tmp_path / "source"
    skill = source / "skills/a-stock-monitor"
    scripts = skill / "scripts"
    scripts.mkdir(parents=True)
    (source / "pyproject.toml").write_text('[project]\nversion = "0.1.13"\n')
    (skill / "SKILL.md").write_text("monitor", encoding="utf-8")
    helper = scripts / "policy_replay.py"
    helper.write_text("print('replay')", encoding="utf-8")
    expected_hash = install._tree_hash(skill)
    for relative in (
        "scripts/__pycache__/policy_replay.cpython-313.pyc",
        "scripts/__pycache__/metadata.json",
        "scripts/legacy.pyc",
        "scripts/legacy.pyo",
        ".git/index",
    ):
        path = skill / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"generated")
    assert install._tree_hash(skill) == expected_hash

    home = tmp_path / "home"
    monkeypatch.setenv("PATH", f"{home / '.local/bin'}:{os.environ.get('PATH', '')}")
    monkeypatch.setattr(install.shutil, "which", lambda name: "/fake/uv")
    monkeypatch.setattr(install, "SKILLS", ("a-stock-monitor",))
    monkeypatch.setattr(
        install, "_build_suite_wheel", lambda *args: tmp_path / "fake.whl"
    )
    monkeypatch.setattr(install, "_install_runtime", lambda *args: None)
    assert (
        install.main(
            [
                "--client",
                "codex",
                "--mode",
                "copy",
                "--source",
                str(source),
                "--target-root",
                str(home),
            ]
        )
        == 0
    )

    target = home / ".agents/skills/a-stock-monitor"
    assert not (target / "scripts/__pycache__").exists()
    assert not (target / ".git").exists()
    files = {
        str(path.relative_to(target)) for path in target.rglob("*") if path.is_file()
    }
    assert files == {
        "SKILL.md",
        "scripts/policy_replay.py",
        ".a-stock-suite-manifest.json",
    }
    manifest = json.loads((target / ".a-stock-suite-manifest.json").read_text())
    assert manifest["source_hash"] == expected_hash
    assert (target / "scripts/policy_replay.py").read_bytes() == helper.read_bytes()
    helper.write_text("print('changed')", encoding="utf-8")
    assert install._tree_hash(skill) != expected_hash


def test_backups_are_unique_within_one_second(tmp_path) -> None:
    target = tmp_path / "target"
    target.write_text("first", encoding="utf-8")
    first = _backup(target, tmp_path)
    target.write_text("second", encoding="utf-8")
    second = _backup(target, tmp_path)
    assert first != second
    assert first.read_text(encoding="utf-8") == "first"
    assert second.read_text(encoding="utf-8") == "second"
