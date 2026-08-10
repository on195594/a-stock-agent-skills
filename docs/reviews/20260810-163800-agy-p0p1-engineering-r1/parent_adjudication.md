# Parent adjudication — AGY P0/P1 engineering review r1

Reviewer: AGY (Antigravity CLI, `--effort high`, print mode, no workspace access)
Verdict returned: `PASS_WITH_NOTES`, zero blocking findings
Read-only proof: `before.sha256` == `after.sha256` across all 8 reviewed files

## Disposition

| # | AGY finding | Parent disposition |
|---|---|---|
| Engineering semantics 1 | "DDL 支持完整事务回滚…不存在隐式提交导致回滚失效的反向风险" | **Rejected — factually wrong.** See below. |
| Engineering semantics 2 | Deleting public `apply_schema_migrations` is not an API break | Accepted. Installer replaces the runtime wholesale; no third-party consumer. |
| Engineering semantics 3 | `_invoke` removal is behaviour-preserving; `cleanup` arg-ignoring is inherited, not a blocker | Accepted. |
| Engineering semantics 4 | One-way W1 help assertion is not a security hole | Accepted; runtime classification is unaffected. Left as a known note. |
| Engineering semantics 5–7 | skip-on-missing-lib, `UV_CACHE_DIR`, `--inexact` all sound | Accepted. |
| Important note 1 | Add reverse assertion to the W1 help test | Deferred, not adopted. The gate is enforced by `COMMAND_CLASSIFICATION`, not by the help text. |
| Important note 2 | Reject extra args in `cmd_cleanup` | Deferred, not adopted. Behaviour change beyond this batch's scope; recorded for the P2 argparse migration. |
| Recommended next step | "直接合并并提交，无需进一步修改" | **Not followed.** Two defects were found after the review. |

## Why Engineering semantics 1 was rejected

AGY reasoned that SQLite supports transactional DDL, therefore a failed batch rolls
back. SQLite the engine does; the Python driver does not put the statement in a
transaction. Measured on this machine (Python 3.13.5, sqlite 3.46.1):

```
in_transaction before ALTER: False
in_transaction after  ALTER: False
rollback 之后的列: ['a', 'b']
=> DDL 是否被回滚: 否（已自动提交，回滚无效）
```

`sqlite3` opens an implicit transaction only before DML. The precise behaviour, since
`bootstrap_schema` interleaves `apply()` with a ledger `INSERT`:

- the **first** pending migration's DDL runs with no transaction open, so it autocommits
  and survives a failure later in the batch;
- the ledger `INSERT` that follows opens the transaction, so every subsequent migration
  is transactional and does roll back;
- the schema therefore ends up *ahead* of the ledger by exactly one item, and the next
  run replays it.

Recovery is real but comes from `apply_column_migration` swallowing `duplicate column
name`, not from atomicity. The submitted docstring credited the wrong mechanism and
told a future reader the swallow was a convenience — inviting its removal. Corrected,
and pinned by `test_interrupted_migration_batch_is_recovered_by_replay`.

## Defect found while disproving AGY, not present in the review snapshot

Writing that regression test surfaced a pre-existing production bug neither the
submitter nor AGY had identified. `db_session` binds `conn = get_db(timeout)` before its
`try/finally`; when bootstrap raises inside `get_db`, the connection is never bound and
never closed, leaking a connection that still holds the open ledger transaction. Every
later access in the same process then fails with `database is locked`, hiding the actual
migration error. Fixed at the root in `get_db` (close-and-re-raise), which is also what
made the invariant testable in-process.

Severity in production is bounded — a CLI process exits after one command — but the
failure path masked its own cause, which is the opposite of fail-closed.

## Verification after adjudication

`bash scripts/check.sh` → `614 passed`, ruff clean, skill validation passed, qa
standalone smoke passed, cron smoke passed.

## Note on artifact scope

`before.sha256`/`after.sha256` bracket the AGY invocation only and are unchanged, which
is what proves the review was read-only. The three subsequent edits (docstring
correction, `get_db` leak fix, new regression test) are parent changes made *after* that
window and are deliberately not reflected in those hashes.
