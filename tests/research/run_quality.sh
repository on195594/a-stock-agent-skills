#!/usr/bin/env bash
# 可重复的静态质量门禁；先执行 pip install -r requirements-dev.txt。
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$REPO_ROOT"
"$PYTHON_BIN" -m ruff check .
"$PYTHON_BIN" -m mypy project_paths.py market_quotes.py schema_ledger.py \
    position_ledger.py framework_metadata.py
