#!/usr/bin/env bash
# Run every repository gate in one command.
#
# This repository has no git remote, so there is no hosted CI to be the source of
# truth; this script is it.  Keep docs/development.md's validation matrix in sync.
#
# Requires an `a-stock-lib` checkout or wheel.  Point A_STOCK_LIB_SOURCE at it when
# it does not sit at ~/a-stock-lib; the installer tests skip when it is absent.
set -euo pipefail
cd "$(dirname "$0")/.."

# --inexact keeps the externally provisioned a-stock-lib installed.  It is
# deliberately not a declared dependency (the installer supplies it explicitly and
# records its provenance), so a plain `uv sync --frozen` would uninstall it and
# break every runtime import.
uv sync --frozen --inexact

uv run pytest -q
uv run ruff check .
uv run python scripts/validate.py
python3 -I tests/qa/standalone_smoke.py
A_STOCK_NOTIFY_MODE=disabled bash tests/test_check_holdings_cron.sh

echo "all repository checks passed"
