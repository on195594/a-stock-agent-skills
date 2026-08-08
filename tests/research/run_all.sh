#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
A_STOCK_LIB_ROOT="${A_STOCK_LIB_ROOT:-$HOME/a-stock-lib}"

if [ -d "$A_STOCK_LIB_ROOT/a_stock_lib" ]; then
    export PYTHONPATH="$A_STOCK_LIB_ROOT${PYTHONPATH:+:$PYTHONPATH}"
fi

cd "$REPO_ROOT"
bash "$REPO_ROOT/tests/run_quality.sh"
"$PYTHON_BIN" -m pytest -q \
    -W error::ResourceWarning \
    -W error::pytest.PytestUnraisableExceptionWarning
bash tests/test_check_holdings_cron.sh
