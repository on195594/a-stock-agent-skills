# A-stock research tool-chain efficiency repair

Date: 2026-08-30
Status: approved for bounded implementation by direct user authorization

## Problem

A single-stock report that combined a newly released interim report and global macro evidence reached the correct fail-closed conclusion, but required 37 parent tool calls in 17 batches before first delivery and exposed about 301,725 characters of tool output. The execution repeated holdings lookup, emitted broad search results, retried optional historical/sentiment data through ad-hoc providers after the action was already incomplete, delivered once before QA completed, and created an unnecessary durable project directory. A follow-up audit also used cross-session search before the live state database and repeated known shell/file-tool mistakes.

## Scope

1. Reuse the price history already loaded by `a-stock-fetch` for valuation percentiles to compute the five-session price change without another provider call.
2. Persist that read-only observation with source/as-of provenance in the existing fundamentals JSON payload; do not add or migrate a database column.
3. Tighten the research execution contract so an already triggered incomplete gate stops recovery of non-blocking sentiment/technical fields, QA completes before report delivery, and file snapshots use host temporary storage rather than creating a durable project.
4. Clarify that the market-data workflow is for quote/index/flow snapshots, not an extra quote route after a successful single-stock research fetch.
5. Clarify that a current-session tool-chain audit reads live `state.db` first and uses `session_search` only for cross-session comparison or historical discovery.
6. Add focused regression and contract checks, preserve rollback evidence, run the repository gate, and exercise the installed runtime path.

## Non-scope

- No scoring thresholds, framework weights, action matrix, holding/L3/Tier logic, financing-balance Provider, extra quote source, dependency, service, cron, gateway, MCP, credential, or database schema migration.
- No attempt to force a complete timing score when financing or other required sentiment evidence remains unavailable.
- No modification of the unrelated pre-existing `skills/a-stock-monitor/SKILL.md` working-tree change.
- No new project, orchestrator, observer, cache layer, or QA system.

## Data contract

`price_change_5d` is the percentage change from the close five valid trading observations before the latest available close to that latest close:

```text
(latest_close / close_5_sessions_ago - 1) * 100
```

Requirements:

- sort by date;
- `_load_price_df()` must coerce and drop malformed provider dates before any downstream percentile or five-session calculation;
- coerce date/close values and discard invalid or non-positive closes;
- require at least six valid observations;
- round to two decimals;
- store the latest observation date as provenance `as_of`;
- return missing with an explicit reason when history is unavailable or insufficient;
- compute from the same `_load_price_df()` result already shared by PE/PB/PS calculations, with no second history fetch.

## Invariants

1. `fetch → check` ordering and Sina-only validated current quote remain unchanged.
2. PE/PB/PS percentile semantics and split handling remain unchanged.
3. Missing five-session history does not block annual fundamentals, but remains explicit and cannot be silently inferred.
4. Latest-report, valuation, sentiment, governance and deterministic-scoring fail-closed gates remain unchanged.
5. QA verdicts still apply only to immutable snapshots; a changed body requires a new QA run.
6. Existing active skills remain reversible and no service restart is required.
7. The unrelated monitor diff remains byte-for-byte untouched.

## Acceptance criteria

1. A focused test observes RED because `compute_price_change_5d` or its persisted field does not yet exist.
2. GREEN proves correct six-observation arithmetic, sorting/invalid-row handling, insufficient-history behavior and single reuse of `_load_price_df()`.
3. Cache readback contains `price_change_5d`, `field_provenance.price_change_5d.source=computed`, and the latest history date as `as_of` without a schema migration.
4. Research contract explicitly stops optional provider recovery after an existing incomplete gate has fixed the action, forbids full report delivery before QA verdict, and defaults file snapshots to per-run temporary storage rather than a new project.
5. Market-data routing contains a single-stock research exclusion after successful fetch; conversation-audit routing states live current session first, cross-session search second.
6. Focused tests, `bash scripts/check.sh`, `git diff --check`, active skill readback, one positive runtime fetch/check smoke and one insufficient-history unit counter-case pass.
7. An independent read-only reviewer checks the frozen authorized diff for behavior, routing, safety, minimality and unrelated-file preservation.
8. Only authorized repository files are committed; the existing monitor modification remains unstaged and unchanged.
9. The installed immutable runtime exposes the new field on a real `a-stock-fetch fetch 002594` followed by `a-stock-cache check 002594`.

## Rollback

- Revert the exact repository commit and reinstall the previous immutable runtime release.
- Restore the two active Hermes skill files from the timestamped backup.
- No database rollback is needed because the existing JSON payload tolerates the additional field and no schema migration occurs; a later fetch from the previous runtime naturally omits it.
