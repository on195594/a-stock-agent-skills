#!/usr/bin/env bash
# Run every repository gate in one command.
#
# Hosted CI and local development both call this script; keep it as the single
# source of truth and keep docs/development.md's validation matrix in sync.
#
# Optional source/wheel overrides are exercised only when A_STOCK_LIB_SOURCE points
# to a checkout; those release-candidate tests skip when it is absent.
set -euo pipefail
cd "$(dirname "$0")/.."
export RUFF_CACHE_DIR="${RUFF_CACHE_DIR:-/tmp/ruff_cache}"

if command -v uv >/dev/null 2>&1; then
    uv sync --frozen
    uv run pytest -q
    uv run ruff check .
    uv run python scripts/validate.py
    uv run python scripts/check_regulatory_freshness.py
elif [ -d ".venv/bin" ]; then
    .venv/bin/pytest -q
    .venv/bin/ruff check .
    .venv/bin/python scripts/validate.py
    .venv/bin/python scripts/check_regulatory_freshness.py
else
    echo "neither uv nor .venv found" >&2
    exit 1
fi
python3 -I tests/qa/standalone_smoke.py
A_STOCK_NOTIFY_MODE=disabled bash tests/test_check_holdings_cron.sh

echo "all repository checks passed"
