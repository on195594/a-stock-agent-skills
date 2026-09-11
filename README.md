# Portable A-Stock Agent Skills Suite

Canonical source for three client-neutral Agent Skills:

- `a-stock-research` — first-time A-share research and valuation;
- `a-stock-monitor` — existing-holding, L3, stop-loss and portfolio checks;
- `a-stock-qa` — text-only compliance checking for research reports.

Research and monitor share one small Python runtime. QA deliberately has no
runtime, market-data or credential dependency. Runtime state, databases,
logs, locks, artifacts and credentials stay outside this repository.

## Current status

The deployed `v0.1.11` runtime release (`0.1.11-996e552a3463`) still uses
`a-stock-lib==0.6.3`. The current repository candidate pins the immutable
`a-stock-lib==0.6.4` GitHub Release wheel and its SHA256 in `uv.lock`. It adds
real TTM P1/P2 inputs and PE/PEG fields, scoped
PB/BPS compatibility, read-only decision metadata, corrected A/F routing and
strict QA snapshot integrity without changing the database schema or W1 write
boundary. All nine client Skill entries resolve directly to `skills/`.

The original M7 production cutover completed on 2026-08-09; the 2026-08-11
maintenance deployments upgraded `a-stock-lib` to 0.5.0 and then deployed the
P2 structural refactor without changing the database schema, configuration or
cron. The 2026-08-14 `v0.1.3` deployment likewise changed no database schema,
configuration or cron. Hermes is the production entry. Claude, Codex and Hermes
remain supported clients; M8 does not retire Claude.

Cutover evidence and the rollback manifest are indexed in
[`docs/migration/`](docs/migration/README.md). The implementation plan remains
the source of truth for the completed M0-M8 migration milestones; dated specs
and [`docs/CHANGELOG.md`](docs/CHANGELOG.md) govern post-cutover work:
[`docs/plans/2026-08-08-portable-a-stock-agent-skills-implementation-plan.md`](docs/plans/2026-08-08-portable-a-stock-agent-skills-implementation-plan.md).

## Install or update

Requirements: Python 3.13+ and `uv`. The installer resolves the hash-pinned
`a-stock-lib==0.6.4` Release wheel from project metadata:

```bash
python3 scripts/install.py \
  --client all \
  --mode symlink \
  --source "$PWD"
```

`--a-stock-lib-source` and `--a-stock-lib-wheel` are limited to release-candidate
checks. Run the normal command with `--dry-run` first when changing an existing
client installation. `--mode copy` is available for clients that cannot discover
symlinks.

The installer exposes these stable commands through `PATH`:

```text
a-stock-cache    shared cache, holdings and portfolio-risk CLI
a-stock-cache score-fundamentals  read-only deterministic A—F fundamental scorer
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

Run the automated test and validation gates with one command:

```bash
bash scripts/check.sh
```

It runs the individual checks below. The frozen lock includes the immutable
`a-stock-lib` Release wheel and hash.

```bash
uv sync --frozen
uv run pytest -q
uv run ruff check .
uv run python scripts/validate.py
python3 -I tests/qa/standalone_smoke.py
```

Before committing, also run `git diff --check` and review the final diff.

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
