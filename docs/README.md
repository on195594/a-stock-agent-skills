# Project documentation

## Start here

- [`../README.md`](../README.md) — install, safety boundary and repository map.
- [`development.md`](development.md) — local setup, tests and evidence rules.
- [`operations.md`](operations.md) — external state, cron, notifications and rollback.

## Governing records

- [`specs/2026-08-08-portable-a-stock-agent-skills-spec.md`](specs/2026-08-08-portable-a-stock-agent-skills-spec.md) — requirements, boundaries and acceptance criteria.
- [`specs/2026-08-09-audit-remediation-spec.md`](specs/2026-08-09-audit-remediation-spec.md) — completed safety, portability and release-gate repairs.
- [`specs/2026-08-09-investment-framework-repair-spec.md`](specs/2026-08-09-investment-framework-repair-spec.md) — authorized investment-framework and fail-closed repairs.
- [`specs/2026-08-10-catalyst-cycle-analysis-migration-spec.md`](specs/2026-08-10-catalyst-cycle-analysis-migration-spec.md) — product-cycle and thematic-catalyst analysis migration boundaries.
- [`specs/2026-08-11-wuxi-analysis-retro-repairs-spec.md`](specs/2026-08-11-wuxi-analysis-retro-repairs-spec.md) — implemented and deployed Research/QA contract repairs.
- [`specs/2026-08-23-lib-060-consumer-cutover-and-scoring-wire-spec.md`](specs/2026-08-23-lib-060-consumer-cutover-and-scoring-wire-spec.md) — implemented deterministic fundamental scoring and rule-hash wiring.
- [`specs/2026-08-23-research-data-capability-and-skill-slimming-spec.md`](specs/2026-08-23-research-data-capability-and-skill-slimming-spec.md) — deployed PS, interim-report snapshot and progressive-disclosure contract.
- [`specs/2026-08-27-a-stock-research-latency-and-readonly-remediation-spec.md`](specs/2026-08-27-a-stock-research-latency-and-readonly-remediation-spec.md) — deployed physically read-only holdings queries and bounded search budgets.
- [`specs/2026-08-27-l3-materiality-and-thesis-versioning-repair-spec.md`](specs/2026-08-27-l3-materiality-and-thesis-versioning-repair-spec.md) — approved L3 materiality, lifecycle and holding-thesis versioning repair.
- [`specs/2026-08-28-a-stock-research-execution-efficiency-repair-spec.md`](specs/2026-08-28-a-stock-research-execution-efficiency-repair-spec.md) — deployed bounded first-pass research and A-framework concentration contract.
- [`specs/2026-08-30-a-stock-research-tool-chain-efficiency-spec.md`](specs/2026-08-30-a-stock-research-tool-chain-efficiency-spec.md) — deployed 5-session price change reuse and stop conditions for incomplete routes.
- [`specs/2026-09-01-a-stock-skill-contract-reconciliation-and-slimming-spec.md`](specs/2026-09-01-a-stock-skill-contract-reconciliation-and-slimming-spec.md) — deployed PE/PS contract reconciliation and progressive disclosure.
- [`specs/2026-09-02-a-stock-research-incomplete-qa-valuation-compatibility-spec.md`](specs/2026-09-02-a-stock-research-incomplete-qa-valuation-compatibility-spec.md) — deployed latest-report PB/BPS valuation compatibility and Research/QA fail-closed alignment.
- [`specs/2026-09-07-investment-framework-and-risk-control-enhancement-spec.md`](specs/2026-09-07-investment-framework-and-risk-control-enhancement-spec.md) — implemented deterministic P0–P3 investment risk gates (regulatory ST/audit, structural ROE deterioration, true FCF/Capex redline, and liquidity shock delay).
- [`specs/2026-09-09-research-decision-availability-and-qa-integrity-repair-spec.md`](specs/2026-09-09-research-decision-availability-and-qa-integrity-repair-spec.md) — authorized Research data availability, framework routing, valuation compatibility, compact reporting and QA snapshot-integrity repairs.
- [`plans/2026-08-08-portable-a-stock-agent-skills-implementation-plan.md`](plans/2026-08-08-portable-a-stock-agent-skills-implementation-plan.md) — milestone ledger, execution commands and rollback plan.
- [`plans/2026-08-10-p2-structural-refactor-plan.md`](plans/2026-08-10-p2-structural-refactor-plan.md) — completed P2 structural refactor and evidence relocation.
- [`plans/2026-08-23-research-data-capability-and-skill-slimming-plan.md`](plans/2026-08-23-research-data-capability-and-skill-slimming-plan.md) — completed implementation, review and production cutover ledger.
- [`plans/2026-09-07-investment-framework-and-risk-control-enhancement-plan.md`](plans/2026-09-07-investment-framework-and-risk-control-enhancement-plan.md) — completed implementation, independent review and test verification ledger for P0–P3 risk control enhancement.
- [`migration/README.md`](migration/README.md) — provenance and redacted execution evidence.
- [`reviews/README.md`](reviews/README.md) — tombstone and recovery instructions for the external evidence archive.

## Evidence policy

`docs/migration/` contains durable audit records. Per-run review packets live
in `/home/lin/a-stock-agent-evidence`; `docs/reviews/README.md` records the
archive commit, manifest and recovery command. Neither location may contain
credentials, production database copies, WAL/SHM files or runtime logs.
Generated test caches belong outside Git and can be removed during worktree
cleanup.
