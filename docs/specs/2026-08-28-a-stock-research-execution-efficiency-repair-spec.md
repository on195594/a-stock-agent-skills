# A-stock research execution-efficiency repair

Date: 2026-08-28
Status: approved for bounded implementation by direct user authorization

## Problem

A two-stock first-research comparison took 11m03s, emitted 75 tool results, and required two QA runs. The investment and fail-closed conclusions were correct, but the execution path over-processed evidence, probed redundant market-data paths, polled an asynchronous reviewer, and allowed the report file to change while QA was reading it. The first QA also exposed a contract mismatch: the A-framework rubric requires an explicit normal/limited/major external-concentration conclusion, while the research entrypoint only requires the tag when risk exists.

## Scope

1. Add a bounded first-pass contract for unspecified first-research and multi-stock comparison requests.
2. Make required source work explicit: installed runtime first, no ad-hoc quote provider after a successful fetch, small generic-search batches, and a stop condition after mandatory evidence and gates are satisfied.
3. Require immutable, versioned QA input and prohibit polling/sleep while asynchronous QA runs.
4. Align A-framework external-concentration output with the QA rubric for both risk-present and risk-absent cases.
5. Document the A-framework `gross_margin_stable` supplemental scorer input so the first deterministic scoring call is complete when evidence is available.
6. Add focused regression assertions and run repository validation.

## Non-scope

No scoring thresholds, formulas, framework weights, market-data providers, runtime CLI behavior, database schema/data, holdings, L3/Tier, cron, credentials, gateway, QA rubric checks, or deployment topology changes. Do not replace portable relative references with absolute paths. Do not add a service, observer, scheduler, lock daemon, schema, or second QA system.

## Invariants

1. Holdings routing remains first and fail-closed.
2. Each stock still executes `fetch` before `check`; a failed fetch stops that stock's scoring route.
3. Required latest-report, industry, PB/BPS, deterministic-scoring, sentiment, governance and framework evidence gates remain unchanged.
4. A bounded first pass may be concise but may not omit a mandatory report section or invent a score.
5. A report snapshot submitted to QA is immutable. A changed report is a new snapshot and requires a new QA run.
6. A QA verdict only applies to the exact supplied snapshot.
7. `a-stock-qa` remains host-neutral and read-only.
8. Existing dirty `skills/a-stock-monitor/SKILL.md` is unrelated and untouched.

## Acceptance criteria

1. Research skill contains an explicit bounded-first-pass contract for unspecified research/comparison requests and a stop condition once mandatory evidence and gates are complete.
2. Research skill forbids ad-hoc quote-provider probes after successful fetch and bounds generic-search batches to at most four independent queries per batch.
3. Research skill and QA skill require a unique immutable report snapshot/path; asynchronous review uses completion notification, not active polling or sleep.
4. A-framework research always emits `外部集中风险[状态=正常|受限|重大…]` with evidence and confidence; the QA rubric remains unchanged.
5. A framework documents `gross_margin_stable` as a required supplemental boolean when deterministic scoring is run.
6. Focused tests fail before the prose changes and pass afterward.
7. `python -m pytest` focused tests, `bash scripts/check.sh`, `git diff --check`, and active symlink/readback checks pass.
8. AGY performs a read-only post-change review against a frozen diff/snapshot, with before/after hashes proving no drift.

## Rollback

Revert only the authorized research/QA/spec/test diff. The unrelated pre-existing monitor modification must remain untouched. Because no runtime or database state changes, no service or data rollback is required.
