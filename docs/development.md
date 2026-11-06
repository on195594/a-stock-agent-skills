# Development and validation

This repository contains the canonical Skill source and the shared runtime.
Development work happens directly on `master` in small verified commits. Do not
create feature branches, open pull requests or force-push. It must remain
fixture-first: do not point tests at a production database, production
credentials or the active client directories.

The shared test fixture selects an absent temporary runtime config and clears
inherited state, risk-policy and XDG overrides before isolating the database.
Tests that exercise configuration set their own synthetic overrides afterward;
the caller's environment must not choose a different test path or validation gate.

## Setup

Requirements are Python 3.13+ and `uv`. Install the locked development
environment with:

```bash
uv sync --frozen
```

The frozen lock includes the immutable `a-stock-lib` GitHub Release wheel and
its SHA256. Source/wheel installer overrides are reserved for release-candidate
checks.

An owner source checkout is only needed for release-candidate override checks.
It must be passed explicitly; the project never
guesses a sibling home-directory path. Those tests locate it via
`A_STOCK_LIB_SOURCE`, and skip when it is not provisioned.

## Validation matrix

`scripts/check.sh` runs the full automated matrix in one command, and hosted CI
runs the same gate on every push to `master`. Local validation is tiered:

- **Ordinary change** (one module's logic or wording inside an existing contract,
  tests, docs): run the changed modules' tests and direct callers with `-x`, plus
  the gate of each touched area — version bump: `tests/research/test_p0_contracts.py`
  and `tests/test_installation.py`; Skill text: `tests/test_skill_validation.py`;
  regulatory constants: `scripts/check_regulatory_freshness.py`; QA Skill: the
  standalone smoke; cron scripts: the cron smoke. Then `ruff check` and
  `ruff format --check` on changed Python files. Hosted CI is the full gate.
- **Full local `bash scripts/check.sh` before committing** only when the change
  touches the dependency lock or a-stock-lib version, the installer/release or state
  migrations, monitor-v1 or another wire contract/schema, spans several modules or
  Skill routing, or first introduces an investment rule.
- **Activation** reuses the pre-commit result; do not re-run tests. Activate only
  after hosted CI succeeded on the commit or a descendant that contains it
  (`gh run list`; a run cancelled by a newer push does not count).

Run heavy commands with `nice -n 15` or a CPU quota. Run `bash scripts/check.sh`
**or** the commands below, not both for unchanged code.

```bash
nice -n 15 uv run pytest -q -x
uv run ruff check .
uv run python scripts/check_regulatory_freshness.py
python3 -I tests/qa/standalone_smoke.py
A_STOCK_NOTIFY_MODE=disabled bash tests/test_check_holdings_cron.sh
```

Then run `git diff --check` and review the final diff before committing; those
worktree checks are deliberately separate from the automated matrix.

Skill validation is covered by `tests/test_skill_validation.py` in pytest;
`python3 -I scripts/validate.py` remains a runtime-free focused check, not a
second full-matrix gate. QA standalone smoke runs once, outside pytest, using
system `python3 -I`; do not add a second subprocess wrapper in pytest.

Useful focused checks:

```bash
nice -n 15 uv run pytest tests/test_cli_contract.py tests/test_command_classification.py -q -x
nice -n 15 uv run pytest tests/test_research_client.py tests/test_portfolio_scenario.py -q -x
nice -n 15 uv run pytest tests/test_installation.py tests/test_state_migration.py -q -x
nice -n 15 uv run pytest tests/test_l3_thesis_versioning.py tests/test_cli_contract.py -q -x
nice -n 15 uv run pytest tests/test_risk_policy.py tests/test_performance.py -q -x
nice -n 15 uv run pytest tests/test_agent_behavior_eval.py -q -x
nice -n 15 uv run pytest tests/research/test_fetcher_dividends.py -q -x
bash tests/test_check_holdings_cron.sh
```

Run `uv run ruff format --check <changed Python files>` for Python files touched by
the patch. Full-repository formatting is not part of the automated matrix.

The Agent behavior suite scores immutable historical responses by default.
[Candidate capture and scoring](agent-behavior-eval.md#re-capture) uses an external
artifact; without `A_STOCK_BEHAVIOR_ARTIFACT`, the nine candidate/provenance tests
skip. Multi-turn behavior still needs manual scoring. Required-field and
forbidden-action mutation tests cover every configured entry; the other four
constraint categories have separate mutation cases.

Check active client links before editing canonical Skill files: legacy entries
that point to the source checkout activate edits immediately. Use an isolated
checkout and `HERMES_HOME` while any active client still points to source. New
installer releases point to frozen Skill snapshots beside the runtime; changing
source then has no effect until an explicitly authorized activation.

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

The autouse fixture isolates `CACHE_DB_PATH` but not `A_STOCK_STATE_DIR`: a test of a
command that writes state files (e.g. `stop-alert`) sets that variable to a temporary
path itself. Never undo `monkeypatch` inside a test; it also reverts the database
isolation, which on 2026-10-22 let a test write to the production ledger (now
guarded by `test_tests_never_undo_the_autouse_database_isolation`).

## Directory and test ownership

- `src/a_stock_agent_runtime/`: installed runtime; `cache.py` is the CLI entry,
  not a compatibility import surface.
- `skills/`: three portable Skill packages, including their references and helpers.
- `tests/`: cross-cutting runtime/CLI/install contracts; `research/`, `monitor/`
  and `qa/` hold workflow-specific tests. `fixtures/` and `golden/` are retained
  test inputs, not temporary output.
- `scripts/`: repository checks, explicit installation/migration and opt-in
  fixture capture; not business logic.
- `docs/`: current owner documents; `architecture/` owns runtime boundaries.
  `specs/` retains dated authorizations and `migration/` retains historical
  evidence; neither is a current execution checklist.

Prefer one test owner per invariant. Use behavioral fixtures and targeted
negative cases; avoid asserting private implementation shape or repeating the
same text check across suites. Skill text is itself executable guidance, so
routing, safety and regulatory contract checks are not redundant merely because
they inspect Markdown. Keep write-gate, isolation and multi-board regressions.
Do not split small modules, add compatibility layers, or move established test
directories just to make the tree look more uniform.

## Documentation and evidence

`cache.py` owns CLI parsing, command dispatch and the write gate; Python callers
and tests import domain/store/db/command functions from their actual modules.
Quote I/O lives in `market_quotes.py`; monitoring's industry aggregation remains
in `commands_holdings.fetch_monitor_price_quotes`. Tests inject these boundaries
explicitly, without production branches that detect patched functions.
Paths are resolved through functions at call time; importing `paths` does not
read configuration. Risk adapters call `risk_gates` directly.

Update the current owner document for the behavior being changed; do not create
another plan/spec/review for ordinary maintenance. Read historical specifications
only when tracing or changing their rules. Migration and review evidence may contain command output and hashes but
must not contain credentials, database copies, WAL/SHM files or runtime logs.
Use relative links for repository documents. Historical evidence is retained
for auditability and is not a scratch directory.

## Test ownership and layout

Keep regression tests beside their functional owner rather than adding to broad
catch-all coverage files:

- `tests/research/`: fetching, valuation and Research-specific contracts;
  `test_fetcher_dividends.py` owns dividend fiscal-year/TTM, missing-data and
  Provider unit-conversion regressions. Its clock and report periods are fixed.
- `tests/monitor/`: holding and monitoring scenarios.
- `tests/qa/`: portable report checks, including the runtime-free standalone smoke.
- `tests/test_*.py`: runtime CLI, application contracts and operations tooling.
- `tests/fixtures/` and `tests/helpers.py`: shared fixture evidence and helpers.

Test the production owner directly, not an otherwise-unused wrapper kept alive
only by tests. Consolidate redundant scenarios, but retain distinct regulatory,
missing-data and permission boundaries. Historical authorization specs are not
redundant test data.

## Generated files

Skill-local executable helpers belong in `skills/<name>/scripts/`; keep the
portable backtest helper there. Copy installs and their `source_hash` exclude
`.git`, `__pycache__`, `*.pyc` and `*.pyo`. New symlink installs expose the frozen
release snapshot, not the editable source tree. Legacy source-linked installs
must be isolated before editing; Git ignores do not filter symlink targets.

Generated caches `__pycache__/`, `.pytest_cache/` and `.ruff_cache/` are disposable
and ignored by Git. The Skill validator ignores generated bytecode and rejects
packaged databases, `.env`/`.env.*`, and files under `logs/` or `locks/`.
Delete pre-existing caches only with user confirmation. Keep the active `.venv/`;
remove `*.egg-info/` only after
confirming that no editable installation uses it for package metadata. Raw
captures and database copies in a temporary directory need a verified archive
before cleanup; historical evidence is not a cache.
