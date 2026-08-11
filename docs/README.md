# Project documentation

## Start here

- [`../README.md`](../README.md) — install, safety boundary and repository map.
- [`development.md`](development.md) — local setup, tests and evidence rules.
- [`operations.md`](operations.md) — external state, cron, notifications and rollback.

## Governing records

- [`specs/2026-08-08-portable-a-stock-agent-skills-spec.md`](specs/2026-08-08-portable-a-stock-agent-skills-spec.md) — requirements, boundaries and acceptance criteria.
- [`specs/2026-08-10-catalyst-cycle-analysis-migration-spec.md`](specs/2026-08-10-catalyst-cycle-analysis-migration-spec.md) — product-cycle and thematic-catalyst analysis migration boundaries.
- [`plans/2026-08-08-portable-a-stock-agent-skills-implementation-plan.md`](plans/2026-08-08-portable-a-stock-agent-skills-implementation-plan.md) — milestone ledger, execution commands and rollback plan.
- [`plans/2026-08-10-p2-structural-refactor-plan.md`](plans/2026-08-10-p2-structural-refactor-plan.md) — completed P2 structural refactor and evidence relocation.
- [`migration/README.md`](migration/README.md) — provenance and redacted execution evidence.
- [`reviews/README.md`](reviews/README.md) — tombstone and recovery instructions for the external evidence archive.

## Evidence policy

`docs/migration/` contains durable audit records. Per-run review packets live
in `/home/lin/a-stock-agent-evidence`; `docs/reviews/README.md` records the
archive commit, manifest and recovery command. Neither location may contain
credentials, production database copies, WAL/SHM files or runtime logs.
Generated test caches belong outside Git and can be removed during worktree
cleanup.
