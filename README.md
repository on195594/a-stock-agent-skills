# Portable A-Stock Agent Skills Suite

Canonical source for three client-neutral Agent Skills:

- `a-stock-research` — first-time A-share research and valuation;
- `a-stock-monitor` — existing-holding, L3, stop-loss and portfolio checks;
- `a-stock-qa` — text-only compliance checking for research reports.

Research and monitor share one small Python runtime. QA deliberately has no
runtime, market-data or credential dependency. Runtime state, databases,
logs, locks, artifacts and credentials stay outside this repository.

## Current status

Production remains on `0.1.11` / lib 0.7.0 after the 2026-09-18 cutover was
rolled back: production lacks `analysis_results.decision_json`, and migration
`035-analysis-decision-json` requires separate explicit authorization. The
prepared `0.1.13` candidate (source `4789fc9`) and frozen lock use `a-stock-lib==0.8.0`
GitHub Release wheel with SHA-256
`a811945b23d97eb121ff82d54bc0ba0810000a5379a9e9786fdcdc9220b30310`.
Architecture convergence Phases 1-6 are complete: A-F scoring and cache-only
industry lookup have one typed owner; runtime decisions and monitor snapshots
use the versioned decision-v1 and monitor-v1 contracts; framework routing has
one explicit catalog; and the three Skills remain thin routers. Eight captured
Hermes scenarios have deterministic offline checks. One fixed
`openai-codex/gpt-5.6-sol` session also executes three critical routes directly
against isolated in-process fake tools with source and isolation provenance.
All nine client Skill entries and three CLI links now resolve through one atomic
`~/.local/share/a-stock-agent/current` pointer to a versioned runtime/Skill set,
not the mutable source checkout. That pointer currently selects the retained old
CLI/Skill pair. S1/S3 remain **NOT_DEPLOYED** pending schema authorization; no
migration was executed and financial DB/WAL hashes remained unchanged. Hermes and
Codex passed candidate-Skill budget replays (including Hermes's configured default
model); Claude's authentication/verification waiver is recorded, not a pass.
Hermes gateway is running on the restored pair. No real-account or live notification
test was performed.
Historical captures retain their original scope. See the
[deployment/rollback record](docs/operations.md#current-deployment-record) and
[S1 ledger](docs/plans/2026-09-17-risk-closure-implementation.md).
S2 Tracker e2 evaluation remains **not deployed**, fixture-validated with a pending
manifest; production registration and calendar evidence remain unverified. See the [S2/S3 ledger](docs/plans/2026-09-17-s2-s3-implementation.md).

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

It runs the individual checks below. The frozen lock includes the immutable
`a-stock-lib` Release wheel and hash.

```bash
uv sync --frozen
uv run pytest -q
uv run ruff check .
uv run python scripts/validate.py
uv run python scripts/check_regulatory_freshness.py
python3 -I tests/qa/standalone_smoke.py
A_STOCK_NOTIFY_MODE=disabled bash tests/test_check_holdings_cron.sh
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
docs/specs/                governing specifications
docs/plans/                implementation plans and milestone ledgers
docs/migration/            provenance and redacted execution evidence
```

The foundational specification is
[`docs/specs/2026-08-08-portable-a-stock-agent-skills-spec.md`](docs/specs/2026-08-08-portable-a-stock-agent-skills-spec.md); current runtime contracts and ownership follow [`docs/architecture/runtime-contracts.md`](docs/architecture/runtime-contracts.md) and [`docs/specs/2026-09-13-a-stock-runtime-contract-vnext.md`](docs/specs/2026-09-13-a-stock-runtime-contract-vnext.md).
