from __future__ import annotations

import sqlite3

from a_stock_agent_runtime import cache, fetcher


def test_public_mains_return_int() -> None:
    assert isinstance(cache.main(["--help"]), int)
    assert isinstance(fetcher.main(["--help"]), int)


def test_w1_requires_prefix_confirmation_without_opening_database(tmp_path, monkeypatch, capsys) -> None:
    database = tmp_path / "cache.db"
    monkeypatch.setattr(cache, "DB_PATH", str(database))
    assert cache.main(["add-holding", "000001", "10", "100"]) == 3
    assert not database.exists()
    assert "--confirm-write" in capsys.readouterr().err


def test_confirmed_fixture_write_is_transactional(tmp_path, monkeypatch) -> None:
    database = tmp_path / "cache.db"
    monkeypatch.setattr(cache, "DB_PATH", str(database))
    assert cache.main(["--confirm-write", "add-holding", "000001", "10", "100"]) == 0
    with sqlite3.connect(database) as conn:
        assert conn.execute("SELECT shares FROM holdings").fetchone() == (100,)


def test_cli_help_does_not_create_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    assert cache.main(["--help"]) == 0
    assert not (tmp_path / ".local").exists()
