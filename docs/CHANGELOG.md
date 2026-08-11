# Changelog

## Unreleased

### Changed

- M8 completion now means all Claude, Codex and Hermes `a-stock-*` entries use the canonical repository and superseded Skill copies remain archived; Claude is not retired.

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
