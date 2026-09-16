# Development and validation

This repository contains the canonical Skill source and the shared runtime.
Development work happens directly on `master` in small verified commits. Do not
create feature branches, open pull requests or force-push. It must remain
fixture-first: do not point tests at a production database, production
credentials or the active client directories.

## Setup

Requirements are Python 3.13+ and `uv`. Install the locked development
environment with:

```bash
uv sync --frozen
```

The frozen lock includes the immutable `a-stock-lib` GitHub Release wheel and
its SHA256. Source/wheel installer overrides are reserved for release-candidate
checks.

An owner source checkout is only needed for release-candidate override checks or
the external prompt renderer. It must be passed explicitly; the project never
guesses a sibling home-directory path. Those tests locate it via
`A_STOCK_LIB_SOURCE`, and skip when it is not provisioned.

## Validation matrix

Run the smallest relevant check while iterating, then run the full automated
matrix before committing. `scripts/check.sh` runs this matrix in one command and
the hosted CI runs the same gate.

```bash
uv run pytest -q
uv run ruff check .
uv run python scripts/validate.py
uv run python scripts/check_regulatory_freshness.py
python3 -I tests/qa/standalone_smoke.py
A_STOCK_NOTIFY_MODE=disabled bash tests/test_check_holdings_cron.sh
```

Then run `git diff --check` and review the final diff before committing; those
worktree checks are deliberately separate from the automated matrix.

Useful focused checks:

```bash
uv run pytest tests/test_cli_contract.py tests/test_command_classification.py -q
uv run pytest tests/test_installation.py tests/test_state_migration.py -q
uv run pytest tests/test_l3_thesis_versioning.py tests/test_cli_contract.py -q
uv run pytest tests/monitor tests/qa tests/research -q
bash tests/test_check_holdings_cron.sh
```

`uv run ruff format --check .` passes across maintained Python sources and tests.

The checked-in Agent tool fixture comes from one fixed
`openai-codex/gpt-5.6-sol` session using an isolated `HOME`, read-only Pi
credentials and in-process fake tools. Refresh it explicitly (never in CI) with:

```bash
timeout 300 node scripts/capture_agent_tool_e2e.mjs \
  tests/fixtures/agent_tool_e2e_live.json
uv run pytest tests/test_agent_tool_e2e.py -q
```

The capture script fails unless the model makes exactly the expected calls and
never invokes the exposed fake W1 tool. It does not call production CLIs,
market-data networks or runtime state.

The QA standalone smoke intentionally runs with `python3 -I` and no installed
runtime. It proves that the QA Skill can be discovered and evaluated from
text alone.

## Safe local runs

Use a temporary state directory and disable notifications for CLI smoke:

```bash
TMP_STATE=$(mktemp -d)
trap 'rm -rf "$TMP_STATE"' EXIT
A_STOCK_STATE_DIR="$TMP_STATE" \
A_STOCK_NOTIFY_MODE=disabled \
  uv run a-stock-cache --help
```

Fixture writes are allowed only inside that temporary state. Production W1
commands still require `--confirm-write` and a separate user decision; a
Goal or a passing test does not grant that permission.

## Documentation and evidence

Keep the governing Spec and implementation plan aligned with actual milestone
state. Migration and review evidence may contain command output and hashes but
must not contain credentials, database copies, WAL/SHM files or runtime logs.
Use relative links for repository documents. Historical evidence is retained
for auditability and is not a scratch directory.

## Generated files

The following are disposable and ignored by Git: `__pycache__/`, `.pytest_cache/`,
`.ruff_cache/` and `*.egg-info/`. Remove only those generated
paths when cleaning a worktree; keep `.venv/` if it is the active development
environment.
