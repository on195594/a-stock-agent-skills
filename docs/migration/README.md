# Migration records

This directory records source provenance, excluded mutable files, baseline
observations and redacted execution evidence. It must not contain credentials,
production database copies, WAL/SHM files or runtime logs.

## Index

- [`source-provenance.md`](source-provenance.md) — source commits and working-tree state.
- [`source-mapping.md`](source-mapping.md) — source-to-canonical mapping.
- [`excluded-files.md`](excluded-files.md) — mutable and host-owned material intentionally excluded.
- [`baseline-tests.md`](baseline-tests.md) — pre-migration test and host observations.
- [`client-shadow-invocation.md`](client-shadow-invocation.md) — isolated discovery recipes for all three clients.
- [`production-cutover/20260809-115052/`](production-cutover/20260809-115052/) — M7 DB, installer, cron, Hermes and notification evidence.

The per-milestone review packets live under `docs/reviews/`. They are retained
for auditability; they are not temporary build output.

## Current state

M0-M6 fixture and shadow validation is complete. M7 production cutover
completed on 2026-08-09 with release tag `v0.1.0`; the redacted parent
disposition is `PASS`. The rollback manifest remains outside the repository.
M8 stable observation and Claude retirement are still pending and must not be
inferred from this evidence.
