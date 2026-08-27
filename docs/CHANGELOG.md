# Changelog

## 0.1.7 - 2026-08-27

- Added versioned holding theses with a partial unique index enforcing one active thesis per holding.
- Added the W1 `thesis-rewrite` command, which validates one stdin JSON payload and atomically supersedes the thesis, retires the complete old L3 set and creates linked structured replacements.
- Added L3 lifecycle, scope, action and materiality fields; active listings follow the current thesis, `l3-list --all` retains audit history, and retired updates are rejected.
- Preserved unrevised holdings under the existing behavior with a visible `legacy contract` warning; rewritten holdings fail closed on stale or unclassified active L3 contracts.

## 0.1.6 - 2026-08-23

- Requires `a-stock-lib==0.6.1`, whose rule hash follows executable scorer source automatically.
- Applied the existing Ruff formatter across maintained Python sources and tests, closing the historical format baseline gap without behavior changes.

## 0.1.5 - 2026-08-23

- Added the read-only `a-stock-cache score-fundamentals` bridge to the A—F deterministic 60-point scorer in `a-stock-lib==0.6.0`.
- Research now treats the scorer subtotal, rule version/hash, missing inputs and red lines as authoritative; manual fundamental-score fallback is retired.

## 0.1.4 - 2026-08-23

### Added

- Fetcher now exposes same-basis `ps_ttm` and 5-year month-end `ps_percentile_5y` from TuShare `daily_basic`, with a 60-valid-month fail-closed gate.
- Fundamentals cache now carries a non-scoring `latest_report_snapshot` for newer interim-report direction checks while preserving annual scoring fields.
- Research moves detailed cycle, timing-adjustment and report templates into three directly linked references while retaining safety and fail-closed gates in the main Skill.

## 0.1.3 - 2026-08-14

### Added

- Runtime fetcher now emits a same-basis 5-year PE percentile with explicit window/basis provenance.
- A-framework reports now carry an external-concentration risk overlay without changing the 60-point score.

### Changed

- `pe_static` is the canonical annual-EPS price multiple; legacy `pe_ttm` remains a deprecated compatibility alias.
- Research requires `a-stock-fetch fetch` to complete before `a-stock-cache check`, and explicitly links every framework reference.
- QA classifies missing report inputs as `INVALID_RUN`, aggregates Important/Critical failures deterministically, and keeps rubric-external advice out of verdicts.

## 0.1.2 - 2026-08-11

### Changed

- M8 completion now means all Claude, Codex and Hermes `a-stock-*` entries use the canonical repository and superseded Skill copies remain archived; Claude is not retired.
- The cache CLI now uses argparse subcommands, rejects surplus or misplaced arguments consistently, and accepts holding notes only through `add-holding --notes`.
- The runtime monolith was split into domain, database, schema, store and command modules while preserving the stable `a-stock-cache` entrypoint.
- Historical review packets moved to the independently versioned `/home/lin/a-stock-agent-evidence` repository with a verified manifest and recovery tombstone.

### Fixed

- Tests and subprocesses resolve isolated temporary databases, and cache metadata lookups use an explicit SQLite read-only session.
- Cross-command helpers use owner-module-qualified calls so monkeypatches remain observable after the module split.

## 0.1.1 - 2026-08-11

### Added

- `a-stock-research`: added product-cycle and thematic-catalyst routing that separates event narratives, order progress and financial realization, with explicit counter-evidence and reproducible conditional valuation boundaries.

### Fixed

- Runtime R0 commands no longer invoke the holdings metadata backfill on physically read-only database connections.
- Audit remediation (2026-08-09): R0 database access is physically read-only; unknown/stale quote timestamps cannot trigger stop-loss or portfolio-risk actions; installer releases are wheel-backed and preflighted with collision-free backups; migration and cron failures now fail closed.
- Skill portability: research QA routing now uses host discovery without client-specific commands, QA scope matches its research-only rubric, and checklist output is client-neutral.
- Maintenance: removed stale compatibility exports, broken legacy runners, and the unmaintained mypy gate.
- `a-stock-research`: removed the conflicting total-score action table; the dual-track matrix is now the sole action outlet, and tranche fractions are scoped to a pre-approved single-name risk cap.
- `a-stock-research`: current PB is computed from the validated price and compatible-period BPS; inconsistent PB/BPS reports fail closed.
- C resource framework: added forward/normalised valuation conflict handling, comparable cost evidence for top reserve-competitiveness scores, and adjacent-cycle scenario handling.
- `a-stock-qa`: added checks for valuation arithmetic/period consistency, unique decision output, position scope, and C-resource evidence quality.
- Runtime cache: an analysis without both its stored price and a fresh validated quote can no longer return `ANALYSIS_HIT`.
- Runtime fetcher: cached industry fallback is now persisted as `stale_cache` and cannot silently authorize framework routing.
- `a-stock-research`: unsupported 5-year/PS/true-PEG inputs, newer-report conflicts, and fully missing bank core data now fail closed; Biotech uses a qualitative-only route; timing arithmetic and risk-sizing boundaries are explicit.
- `a-stock-monitor`: split ROE deterioration into 3pt yellow and 5pt red-review gates, removed ambiguous direct-sell wording, and bound accumulation proposals to portfolio-risk prerequisites.
- `a-stock-qa`: added checks for current-report/valuation capability, bank completeness, reproducible timing arithmetic, and an explicit text-only compliance boundary.

Trigger: 紫金矿业（601899）investment review, 2026-08-09, AGY with parent adjudication.

### Fixed (2026-08-10 engineering repairs)

- Development environment: documented `uv sync --frozen --inexact`; the plain form uninstalled the externally provisioned `a-stock-lib` and broke every runtime import.
- Installer tests no longer depend on a warm host `uv` cache reachable through the relocated `HOME`, and locate `a-stock-lib` via `A_STOCK_LIB_SOURCE` instead of a hardcoded path, skipping when it is absent.
- `a-stock-cache --help` now states the global `--confirm-write` gate and its W1 command list, and documents the four `retro-*` commands; a test keeps the text in sync with the command table.
- A failed schema bootstrap no longer leaks the connection it opened. `get_db` closes it before re-raising, so the still-open ledger transaction cannot lock the database and mask the real migration error behind `database is locked`.
- Pinned the migration ledger's real recovery contract: Python's sqlite3 opens an implicit transaction only before DML, so the first pending migration's DDL autocommits and can outlive a failure later in the batch. Recovery is the replay swallowing `duplicate column name`, not atomicity.

### Changed (2026-08-10 engineering repairs)

- Added `scripts/check.sh` as the single repository gate; this repository has no git remote, so there is no hosted CI to be the source of truth.
- Removed the superseded `apply_schema_migrations` duplicate and the redundant `_invoke` dispatch branch; the migration ledger's `apply_column_migration` is now the only column-migration path.

Trigger: P0/P1 engineering repairs, 2026-08-10, AGY review with parent adjudication.
