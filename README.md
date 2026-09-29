# Portable A-Stock Agent Skills Suite

Canonical source for three client-neutral Agent Skills:

- `a-stock-research` — first-time A-share research and valuation;
- `a-stock-monitor` — existing-holding, L3, stop-loss and portfolio checks;
- `a-stock-qa` — text-only compliance checking for research reports.

Research and monitor share one small Python runtime. QA deliberately has no
runtime, market-data or credential dependency. Runtime state, databases,
logs, locks, artifacts and credentials stay outside this repository.

## Goal and ownership

Help one user research new A-shares, review existing holdings and check report
compliance, with traceable evidence and explicit authorization for state writes.
Research, Monitor and QA stay separate routes; they are not separate code projects.
QA checks report compliance, not factual truth or investment effectiveness.

`a-stock-lib` owns shared deterministic calculations and Providers. This runtime
owns holdings, risk and decision-v1/monitor-v1 application contracts. Tracker
owns generic data collection and historical audit; **Framework A closed as
`CLOSED_UNPROVEN` on 2026-09-21**, so S2 enrollment and maturation are not pending
work. The separate `a-stock-screen` workbench owns peer discovery, personal notes
and fact changes, not holdings or trading. Do not merge these state or permission
boundaries, restore Tracker experiments, or add an LLM orchestration platform.

## Version and deployment records

Source versions and dependency pins live in `pyproject.toml` and `uv.lock`.
Actual activation, paired runtime/Skill identity, client verification limits and
rollback belong in the [operations record](docs/operations.md#current-deployment-record),
not a second deployment ledger here. Passing offline tests is not live-client or
real-account validation.
A separately authorized 2026-09-28 metadata-only publication shortened the three
Skill descriptions to 57/53/58 characters through a new shared release view.
Active bodies/references and runtime targets were preserved, including monitor's
existing execution note not present in this checkout. Fresh native discovery was
checked; no gateway restart or new model qualification is implied. See the
[description publication record](docs/operations.md#description-only-publication--2026-09-28).

Historical migration and S1/S2/S3 ledgers remain available through the
[documentation index](docs/README.md); completed milestones are not a new task queue.

## Install or update

Requirements: Python 3.13+ and `uv`. The installer resolves the hash-pinned
`a-stock-lib==0.8.0` Release wheel from project metadata:

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
a-stock-cache performance-report  file-only account performance, optional read-only ledger check
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
docs/architecture/         runtime contract and ownership architecture
docs/specs/                retained investment/risk-rule specifications
docs/migration/            provenance and redacted execution evidence
```

Start with the [current runtime contracts](docs/architecture/runtime-contracts.md).
Read dated specs only for the rule being changed. Completed implementation plans
and superseded architecture drafts are recoverable from Git using the
[archive instructions](docs/README.md#历史只从-git-追溯), not a standing task queue.
