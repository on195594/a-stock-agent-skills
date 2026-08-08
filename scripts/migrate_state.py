#!/usr/bin/env python3
"""SQLite Online Backup API migration and invariant report."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys


def _digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)


def _snapshot(conn: sqlite3.Connection) -> dict[str, object]:
    tables = [
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    counts: dict[str, int] = {}
    for table in tables:
        counts[table] = int(conn.execute(f"SELECT COUNT(*) FROM \"{table}\"").fetchone()[0])
    sample: list[dict[str, object]] = []
    if "holdings" in tables:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(holdings)")]
        for row in conn.execute("SELECT * FROM holdings ORDER BY rowid LIMIT 5"):
            sample.append(dict(zip(columns, row)))
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    return {
        "journal_mode": conn.execute("PRAGMA journal_mode").fetchone()[0],
        "user_version": conn.execute("PRAGMA user_version").fetchone()[0],
        "tables": tables,
        "counts": counts,
        "holdings_sample": sample,
        "integrity": integrity,
    }


def migrate(source: Path, target: Path, report: Path, expected_tables: list[str], dry_run: bool) -> int:
    if not source.is_file():
        print(f"source database does not exist: {source}", file=sys.stderr)
        return 2
    if dry_run:
        print(json.dumps({"source": str(source), "target": str(target), "dry_run": True}))
        return 0
    if target.exists():
        print(f"refusing to overwrite target database: {target}", file=sys.stderr)
        return 2
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with _read_only(source) as source_conn, sqlite3.connect(target) as target_conn:
        source_before = _snapshot(source_conn)
        source_conn.backup(target_conn)
        target_conn.commit()
    with _read_only(target) as target_conn:
        target_after = _snapshot(target_conn)
    missing = sorted(set(expected_tables) - set(target_after["tables"]))
    if source_before["integrity"] != "ok" or target_after["integrity"] != "ok" or missing:
        print("migration invariant failed", file=sys.stderr)
        return 1
    payload = {
        "source": {"path": str(source), "sha256": _digest(source), **source_before},
        "target": {"path": str(target), "sha256": _digest(target), **target_after},
        "expected_tables": expected_tables,
        "missing_expected_tables": missing,
    }
    report.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-db", type=Path, required=True)
    parser.add_argument("--target-db", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--expected-table", action="append", default=[])
    args = parser.parse_args(argv)
    return migrate(args.source_db, args.target_db, args.report, args.expected_table, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
