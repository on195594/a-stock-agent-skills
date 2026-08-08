from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path


def _module():
    path = Path(__file__).resolve().parents[1] / "scripts/migrate_state.py"
    spec = importlib.util.spec_from_file_location("migrate_state", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_online_backup_and_report(tmp_path) -> None:
    module = _module()
    source = tmp_path / "source.db"
    target = tmp_path / "target.db"
    report = tmp_path / "report.json"
    with sqlite3.connect(source) as conn:
        conn.execute("PRAGMA user_version=7")
        conn.execute("CREATE TABLE holdings(code TEXT PRIMARY KEY, shares INTEGER NOT NULL)")
        conn.execute("CREATE TABLE transactions(id INTEGER PRIMARY KEY, code TEXT)")
        conn.execute("CREATE TABLE analysis_results(id INTEGER PRIMARY KEY, code TEXT)")
        conn.execute("INSERT INTO holdings VALUES ('000001', 100)")
    assert module.main(["--source-db", str(source), "--target-db", str(target), "--report", str(report), "--expected-table", "holdings"]) == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["target"]["integrity"] == "ok"
    assert payload["target"]["user_version"] == 7
    assert payload["target"]["counts"]["holdings"] == 1


def test_dry_run_creates_no_target_or_report(tmp_path) -> None:
    module = _module()
    source = tmp_path / "source.db"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE holdings(code TEXT)")
    target, report = tmp_path / "target.db", tmp_path / "report.json"
    assert module.main(["--source-db", str(source), "--target-db", str(target), "--report", str(report), "--dry-run"]) == 0
    assert not target.exists() and not report.exists()
