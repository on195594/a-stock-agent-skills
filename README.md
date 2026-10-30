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
owns holdings, risk and decision-v1/monitor-v1 application contracts.
`a-share-research` is an independent peer application for cited financial-report
research, history and price references; it also consumes `a-stock-lib`. The two
applications keep separate state and releases. `a-stock-cache research` consumes
its `research-v1` HTTP API: reuse reports and source evidence, then submit focused
research, follow-ups or corrections when needed. It never opens the holdings database
and cannot replace runtime risk gates or grant account-write authorization.
Configure `A_STOCK_RESEARCH_URL` and `A_STOCK_RESEARCH_TOKEN` in the environment
or the selected owner-only `runtime.env`. Use a named, revocable long-lived API
key issued by the Research owner; short-lived tokens remain suitable for temporary
checks. Environment variables override the file. On HTTP 401, update the credential
before retrying, then reuse the original request ID for submissions.
See the [workflow](skills/a-stock-research/references/research-service.md).
Version 0.1.26 additions (require the matching Research server):
`research report <id> --compact` reads a bounded report with source directory,
failure diagnostics and prior checkpoints; omit `--compact` for full evidence.
`research resume --request-id <original-id>` only looks up an existing task,
including failed tasks; it never restarts work. `research budget` reports the
model-call guard, not a monetary cap or bill; unavailable cost stays unknown.
Global budget reads describe configuration (`scope=configuration`, recorded calls
unknown), not account usage; only a task lookup reports that task's recorded calls.
For an authorized rollout, deploy the matching Research server before
activating the matching runtime and Skills. Until then, a missing new endpoint is
a compatibility gap: use explicitly requested full report reads where supported,
never create a replacement research task to work around it.

The shared [project contract](https://github.com/on195594/a-share-research/blob/main/docs/project-contract.md),
[roadmap](https://github.com/on195594/a-share-research/blob/main/docs/roadmap.md) and
[implementation plan](https://github.com/on195594/a-share-research/blob/main/docs/implementation-plan.md)
are maintained in `a-share-research/docs/`. They describe current boundaries and
conditional future work; runtime contracts and active deployment records remain
owned here.

Per the user's 2026-10-21 decision, Tracker is stopped and the planned consumption
of its MCP evidence packages is cancelled. Skills continue to use the installed
runtime and official disclosures directly; Tracker is not a prerequisite or fallback.
Historical Tracker Framework A closed as `CLOSED_UNPROVEN` on 2026-09-21;
neither its experiments nor S2 enrollment/maturation are pending work. Research's
A–F contracts remain active; this does not establish investment effectiveness.
Do not merge state/permission boundaries, restore Tracker experiments, or add an
LLM orchestration platform.

## Version and deployment records

Source versions and dependency pins live in `pyproject.toml` and `uv.lock`.
Actual activation, paired runtime/Skill identity, client verification limits and
rollback belong in the [operations record](docs/operations.md#current-deployment-record),
not a second deployment ledger here. Passing offline tests is not live-client or
real-account validation.
The active release contains matching committed runtime and Skill sources;
client reload limits and pointer-only rollback are recorded in operations.

Historical migration and S1/S2/S3 ledgers remain available through the
[documentation index](docs/README.md); completed milestones are not a new task queue.

## Install or update

Requirements: Python 3.13+ and `uv`. The installer resolves the hash-pinned
`a-stock-lib` Release wheel from project metadata. Market-data commands resolve
`TUSHARE_TOKEN` from the environment first, then the selected private runtime.env
(`A_STOCK_CONFIG_FILE` or the XDG default). Only that token is passed to Providers;
direct CLI calls do not export the file's other secrets. The cron entrypoint
continues to export its explicitly selected configuration. Neither route discovers
another project's `.env`.

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
a-stock-cache portfolio-scenario --snapshot <external.json> --sell <code>:<shares> --fees <estimate>
                local read-only snapshot comparison; optional --cash must match the snapshot
a-stock-cache research            versioned report/evidence reads and focused research/feedback tasks
a-stock-cache score-fundamentals  read-only deterministic A—F fundamental scorer
a-stock-cache performance-report  file-only account performance, optional read-only ledger check
a-stock-cache benchmark-report    read-only ledger cash flows vs the same flows into total-return indices
a-stock-cache daily-brief         read-only post-close push text; silent without same-day quotes
a-stock-cache stop-alert          intraday stop-line push text from canonical stops, once per day per level
a-stock-fetch    structured market-data fetch CLI
a-stock-fetch quarter <code> [--json]
                read-only quarterly/YTD YoY, TTM cash flow, same-period balances and dividend-spread DPS
a-stock-install  installer entrypoint
```

The client adapters install the same Skill content at their own discovery
locations; the canonical files under `skills/` remain the only source of
truth. On this host, Pi and AGY also discover the shared `~/.agents/skills`
entries, so `--client all` updates them too; see the operations record for
verified paths and session reload limits.

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
