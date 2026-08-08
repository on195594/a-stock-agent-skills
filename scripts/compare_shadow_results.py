#!/usr/bin/env python3
"""Compare deterministic shadow invariants without comparing prose."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


KEYS = ("framework", "hard_score", "red_lines", "data_gaps", "fail_closed")


def compare(root: Path) -> list[str]:
    files = sorted(root.glob("*/invariants.json"))
    if not files:
        files = sorted(root.glob("*.json"))
    if len(files) < 2:
        return ["need at least two invariant JSON files"]
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    baseline = {key: payloads[0].get(key) for key in KEYS}
    errors: list[str] = []
    for path, payload in zip(files[1:], payloads[1:], strict=True):
        current = {key: payload.get(key) for key in KEYS}
        if current != baseline:
            errors.append(f"invariant drift in {path}: {current} != {baseline}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args(argv)
    errors = compare(args.evidence)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("shadow invariants match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
