#!/usr/bin/env python3
"""Validate portable Skill contracts without importing the runtime."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ("a-stock-research", "a-stock-monitor", "a-stock-qa")


def _frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"missing frontmatter: {path}")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError(f"unterminated frontmatter: {path}") from exc
    values: dict[str, str] = {}
    for line in lines[1:end]:
        key, sep, value = line.partition(":")
        if sep:
            values[key.strip()] = value.strip().strip("\"'")
    return values


def validate(root: Path = ROOT, installed_root: Path | None = None) -> list[str]:
    errors: list[str] = []
    for skill in SKILLS:
        skill_root = root / "skills" / skill
        path = skill_root / "SKILL.md"
        if not path.is_file():
            errors.append(f"missing {path}")
            continue
        try:
            fields = _frontmatter(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if fields.get("name") != skill:
            errors.append(f"{path}: name must equal directory")
        if not fields.get("description") or not re.search(r"use|when|触发|用于", fields["description"], re.I):
            errors.append(f"{path}: description lacks trigger language")
        for required in ("license", "compatibility"):
            if not fields.get(required):
                errors.append(f"{path}: missing {required}")
        text = path.read_text(encoding="utf-8")
        if skill != "a-stock-qa" and "--confirm-write" not in text:
            errors.append(f"{path}: missing W1 confirmation boundary")
        if skill != "a-stock-qa" and "fail-closed" not in text:
            errors.append(f"{path}: missing fail-closed boundary")
        for reference in re.findall(r"(?:references|assets)/[A-Za-z0-9_./-]+", text):
            if not (skill_root / reference).is_file():
                errors.append(f"{path}: missing reference {reference}")
    scan_roots = [root / "skills", root / "src" / "a_stock_agent_runtime"]
    if installed_root is not None:
        scan_roots.append(installed_root)
    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"(?:~|/home/[^/]+)/\.(?:claude|agents|hermes)/skills", text):
                errors.append(f"host path in business content: {path}")
            if (root / "skills") in path.parents and re.search(
                r"(?:\bagy\s+--|\bcodex:|\bclaude:|\bhermes:)", text, re.I
            ):
                errors.append(f"{path}: client-specific tool invocation")
            if re.search(r"(?:cache\.db(?:-(?:wal|shm))?|\.env|/logs/|/locks/)", path.name):
                errors.append(f"mutable file packaged: {path}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-root", type=Path)
    args = parser.parse_args(argv)
    errors = validate(ROOT, args.installed_root)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("skill validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
