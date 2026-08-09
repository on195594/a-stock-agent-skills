from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from a_stock_agent_runtime import cache


def test_missing_w1_confirmation_keeps_fixture_hash(tmp_path, monkeypatch) -> None:
    database = tmp_path / "cache.db"
    monkeypatch.setattr(cache, "DB_PATH", str(database))
    before = hashlib.sha256(database.read_bytes()).hexdigest() if database.exists() else None
    assert cache.main(["set", "000001", "名称", "行业", "{}"] ) == 3
    after = hashlib.sha256(database.read_bytes()).hexdigest() if database.exists() else None
    assert before == after


def test_r0_command_never_bootstraps_or_changes_database(tmp_path, monkeypatch) -> None:
    database = tmp_path / "cache.db"
    sqlite3.connect(database).close()
    monkeypatch.setattr(cache, "DB_PATH", str(database))
    before = hashlib.sha256(database.read_bytes()).hexdigest()

    assert cache.main(["holdings"]) == 1

    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
    with sqlite3.connect(database) as conn:
        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall() == []


def test_business_content_has_no_legacy_client_paths() -> None:
    root = Path(__file__).resolve().parents[1]
    for base in (root / "skills", root / "src/a_stock_agent_runtime"):
        for path in base.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="ignore")
                assert ".claude/skills" not in text
                assert ".agents/skills" not in text
                assert ".hermes/skills" not in text
