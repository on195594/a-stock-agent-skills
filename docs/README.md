# Project documentation

## Start here

- [`../README.md`](../README.md) — install, safety boundary and repository map.
- [`development.md`](development.md) — local setup, tests and evidence rules.
- [`operations.md`](operations.md) — external state, cron, notifications and rollback.

## Governing records

- [`specs/2026-08-08-portable-a-stock-agent-skills-spec.md`](specs/2026-08-08-portable-a-stock-agent-skills-spec.md) — requirements, boundaries and acceptance criteria.
- [`plans/2026-08-08-portable-a-stock-agent-skills-implementation-plan.md`](plans/2026-08-08-portable-a-stock-agent-skills-implementation-plan.md) — milestone ledger, execution commands and rollback plan.
- [`plans/2026-08-10-p2-structural-refactor-plan.md`](plans/2026-08-10-p2-structural-refactor-plan.md) — P2 structural debt: CLI argparse migration, `cache.py` split, evidence relocation. Approved, execution not authorized.
- [`migration/README.md`](migration/README.md) — provenance and redacted execution evidence.

## Evidence policy

`docs/migration/` and `docs/reviews/` are audit records, not scratch space.
They may contain redacted command output, hashes and exit codes, but must not
contain credentials, production database copies, WAL/SHM files or runtime
logs. Generated test caches belong outside Git and can be removed during
worktree cleanup.
