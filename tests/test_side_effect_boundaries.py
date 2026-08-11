from __future__ import annotations

import hashlib
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from a_stock_agent_runtime import cache
from a_stock_agent_runtime import fetcher, paths


def test_isolation_path_propagates_to_child_process(tmp_path) -> None:
    database = paths.cache_db_path()
    assert database.parent == tmp_path
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from a_stock_agent_runtime.paths import cache_db_path; print(cache_db_path())",
        ],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == str(database)


def test_read_only_lookup_does_not_create_database(tmp_path, monkeypatch) -> None:
    database = tmp_path / "missing" / "cache.db"
    monkeypatch.setenv("CACHE_DB_PATH", str(database))
    assert fetcher._lookup_cached_industry("600000") is None
    assert fetcher._lookup_cached_name("600000") is None
    assert not database.parent.exists()


def test_missing_w1_confirmation_keeps_fixture_hash(tmp_path, monkeypatch) -> None:
    database = tmp_path / "cache.db"
    monkeypatch.setenv("CACHE_DB_PATH", str(database))
    before = hashlib.sha256(database.read_bytes()).hexdigest() if database.exists() else None
    assert cache.main(["set", "000001", "名称", "行业", "{}"] ) == 3
    after = hashlib.sha256(database.read_bytes()).hexdigest() if database.exists() else None
    assert before == after


def test_r0_command_never_bootstraps_or_changes_database(tmp_path, monkeypatch) -> None:
    database = tmp_path / "cache.db"
    sqlite3.connect(database).close()
    monkeypatch.setenv("CACHE_DB_PATH", str(database))
    before = hashlib.sha256(database.read_bytes()).hexdigest()

    assert cache.main(["holdings"]) == 1

    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    with sqlite3.connect(database) as conn:
        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall() == []


def test_populated_r0_commands_keep_fixture_hash(tmp_path, monkeypatch) -> None:
    database = tmp_path / "cache.db"
    monkeypatch.setenv("CACHE_DB_PATH", str(database))
    cache.cmd_add_holding(["600036", "40", "100", "--notes", "fixture"])

    for command in (["holdings"], ["retro-pending"], ["retro-outliers"]):
        before = hashlib.sha256(database.read_bytes()).hexdigest()
        assert cache.main(command) == 0
        assert hashlib.sha256(database.read_bytes()).hexdigest() == before


def test_business_content_has_no_legacy_client_paths() -> None:
    root = Path(__file__).resolve().parents[1]
    for base in (root / "skills", root / "src/a_stock_agent_runtime"):
        for path in base.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="ignore")
                assert ".claude/skills" not in text
                assert ".agents/skills" not in text
                assert ".hermes/skills" not in text
