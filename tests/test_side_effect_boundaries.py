from __future__ import annotations

import hashlib
from pathlib import Path

from a_stock_agent_runtime import cache


def test_missing_w1_confirmation_keeps_fixture_hash(tmp_path, monkeypatch) -> None:
    database = tmp_path / "cache.db"
    monkeypatch.setattr(cache, "DB_PATH", str(database))
    before = hashlib.sha256(database.read_bytes()).hexdigest() if database.exists() else None
    assert cache.main(["set", "000001", "名称", "行业", "{}"] ) == 3
    after = hashlib.sha256(database.read_bytes()).hexdigest() if database.exists() else None
    assert before == after


def test_business_content_has_no_legacy_client_paths() -> None:
    root = Path(__file__).resolve().parents[1]
    for base in (root / "skills", root / "src/a_stock_agent_runtime"):
        for path in base.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="ignore")
                assert ".claude/skills" not in text
                assert ".agents/skills" not in text
                assert ".hermes/skills" not in text
