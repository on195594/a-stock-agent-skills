from __future__ import annotations

import os

import pytest

from a_stock_agent_runtime import paths


@pytest.fixture(autouse=True)
def isolated_cache_database(tmp_path, monkeypatch):
    """Keep every test and child process away from external runtime state."""
    external_path = paths.cache_db_path()
    database = tmp_path / "cache.db"
    monkeypatch.setenv("CACHE_DB_PATH", str(database))
    assert paths.cache_db_path() == database
    assert paths.cache_db_path() != external_path
    yield database
    monkeypatch.setenv("CACHE_DB_PATH", str(database))
    assert os.environ["CACHE_DB_PATH"] != str(external_path)
