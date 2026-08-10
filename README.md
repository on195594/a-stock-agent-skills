# Portable A-Stock Agent Skills Suite

Canonical source for three client-neutral Agent Skills:

- `a-stock-research` — first-time A-share research and valuation;
- `a-stock-monitor` — existing-holding, L3, stop-loss and portfolio checks;
- `a-stock-qa` — text-only compliance checking for research reports.

Research and monitor share one small Python runtime. QA deliberately has no
runtime, market-data or credential dependency. Runtime state, databases,
logs, locks, artifacts and credentials stay outside this repository.

## Current status

The `v0.1.0` runtime release is deployed. M7 production cutover completed on
2026-08-09; Hermes is the production entry and the three client Skill links
point to the same canonical source. Claude retirement (M8) has not been
authorized or performed.

Cutover evidence and the rollback manifest are indexed in
[`docs/migration/`](docs/migration/README.md). The implementation plan remains
the source of truth for milestone state:
[`docs/plans/2026-08-08-portable-a-stock-agent-skills-implementation-plan.md`](docs/plans/2026-08-08-portable-a-stock-agent-skills-implementation-plan.md).

## Install or update

Requirements: Python 3.13+, `uv`, and an explicit checkout or wheel for
`a-stock-lib==0.5.0`. The installer itself uses only the Python
standard library, so it can bootstrap the runtime:

```bash
python3 scripts/install.py \
  --client all \
  --mode symlink \
  --source "$PWD" \
  --a-stock-lib-source /path/to/a-stock-lib
```

Use `--a-stock-lib-wheel /path/to/a-stock-lib.whl` instead when a validated
wheel is available. Run the same command with `--dry-run` first when changing
an existing client installation. `--mode copy` is available for clients that
cannot discover symlinks.

The installer exposes these stable commands through `PATH`:

```text
a-stock-cache    shared cache, holdings and portfolio-risk CLI
a-stock-fetch    structured market-data fetch CLI
a-stock-install  installer entrypoint
```

The client adapters install the same Skill content at their own discovery
locations; the canonical files under `skills/` remain the only source of
truth.

## Safety and state

Read-only commands do not need confirmation. Every production W1 state write
requires the global `--confirm-write` flag and an explicit user decision for
the concrete action. Missing confirmation returns exit code `3` without
opening a write transaction. Missing, stale or unverifiable data is
fail-closed.

By default the runtime uses XDG locations:

```text
~/.config/a-stock-agent/runtime.env       # optional, mode 0600
~/.local/share/a-stock-agent/cache.db
~/.local/share/a-stock-agent/{logs,locks,artifacts}/
```

`A_STOCK_CONFIG_FILE`, `A_STOCK_STATE_DIR`, `CACHE_DB_PATH` and the related
directory variables may override these paths. Do not place a database,
credential, runtime log or Telegram token in the repository.

## Development checks

```bash
uv sync --frozen
uv run pytest -q
uv run ruff check .
uv run python scripts/validate.py
python3 -I tests/qa/standalone_smoke.py
```

Use fixture state and `A_STOCK_NOTIFY_MODE=disabled` for local or shadow
checks. See [`docs/development.md`](docs/development.md) for the validation
matrix and [`docs/operations.md`](docs/operations.md) for configuration,
cron, backup and rollback procedures.

## Repository map

```text
skills/                    canonical Agent Skills and references
src/a_stock_agent_runtime/ shared runtime and CLI implementations
tests/                     unit, contract and fixture tests
scripts/                   installer, migration, validation and cron helpers
docs/specs/                governing specification
docs/plans/                implementation plan and milestone ledger
docs/migration/            provenance and redacted execution evidence
```

The governing specification is
[`docs/specs/2026-08-08-portable-a-stock-agent-skills-spec.md`](docs/specs/2026-08-08-portable-a-stock-agent-skills-spec.md).
