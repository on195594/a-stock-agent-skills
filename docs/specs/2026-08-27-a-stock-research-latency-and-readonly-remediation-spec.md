# A-stock research latency and read-only remediation

Date: 2026-08-27
Status: approved for bounded implementation after AGY read-only review

## Problem

A held-stock research request took 14m4.2s and emitted 82 tool results. The main causes were late route termination, unbounded generic search/PDF fallbacks, fragmented text extraction, probing ad-hoc market providers before the installed runtime, and full-audit delivery for an unspecified request.

Discovery also found that ordinary holdings/retro command paths call `schema.backfill_holding_metadata()`. That helper can update holdings, insert inferred events and commit, even though migration `025-holdings-metadata-backfill` already owns the compatibility migration. R0 commands must be physically read-only and must not perform lazy migrations.

## Scope

1. Make R0 holdings/retro queries physically read-only and remove command-time metadata backfills.
2. Extend `a-stock-cache holdings` with one optional stock-code filter while preserving zero-argument output.
3. Distinguish three route states:
   - existing readable ledger + row found: held;
   - existing readable ledger + row absent: `NOT_HELD <code>`, exit 0;
   - database missing/unreadable/schema unavailable: `HOLDINGS_UNAVAILABLE <reason>`, nonzero exit.
4. Hard-stop `a-stock-research` after a held-stock route and hand off to `a-stock-monitor` unless the user explicitly requests a fresh configuration study.
5. Keep monitor C01-C10 intact while defaulting generic held-stock research to a concise result.
6. Bound source work: official exchange/regulator and issuer sources first; at most one generic-search batch for gaps; at most two PDF extraction methods; installed a-stock runtime providers before ad-hoc libraries.
7. Use one bounded stdlib pass over an explicit report-text file instead of fragmented whole-directory searches.
8. Keep monitor QA as explicit `SKIP`; do not add a monitor rubric or claim research scoring on monitor routes.

## Non-scope

No changes to scoring, stop-loss thresholds, position sizing, L3 materiality, database schema, cron, credentials, providers, production investment data, or service state. No new announcement service, parser package, observer, monitor QA rubric, or background automation.

## Invariants

1. All R0 commands remain physically read-only.
2. W1 commands still require the global `--confirm-write` prefix.
3. Unheld stocks still receive the full research route.
4. Explicit fresh re-research of a held stock remains possible.
5. Missing/stale quotes remain fail-closed.
6. Monitor C01-C10 remain mandatory.
7. Missing ledger is never conflated with confirmed non-holding.
8. Zero-argument `holdings` output remains compatible.
9. No other holding leaks into `holdings <code>` output.
10. Retry/source budgets cannot weaken evidence or fail-closed rules.

## Implementation

- `commands_holdings.py`: remove lazy backfill calls from ordinary command paths; use `db.read_only_db_session()` for `holdings`, `retro-pending` and `retro-outliers`; add optional code filtering and stable `NOT_HELD` output; map schema/read failures to `HOLDINGS_UNAVAILABLE` + nonzero exit.
- `cache.py`: accept `holdings [code]`; make missing-database holdings status stable and nonzero while leaving other R0 behavior unchanged.
- Skill contracts: update research route termination and monitor delivery/source budgets without changing investment rules.
- Tests: prove RED/GREEN for database immutability, code filtering, zero-arg compatibility, missing/unavailable distinction, argument rejection and skill route contracts.
- Release: bump runtime to the next patch version and update changelog.

## Verification

Run fixture-only checks, `bash scripts/check.sh`, `git diff --check`, installer dry-run, install the new runtime, and positive/negative real CLI smokes. Compare the production database hash before/after R0 smokes. Healthy-network time-to-first-result is observational; deterministic gates are source/retry bounds and a replay target of no more than 25 tool results.

## Rollback

Patch A is one repository commit and can be reverted with `git revert`. Keep runtime 0.1.7 available until the new release passes installation and real-path smokes. No database rollback is required because this change performs no schema or data migration.
