# Operations runbook

This runbook covers the installed runtime after the M7 cutover. Claude, Codex
and Hermes remain supported clients. Nothing here authorizes investment
decisions or unattended W1 writes.

## Configuration and state

The runtime resolves settings in this order: explicit environment variable,
`A_STOCK_CONFIG_FILE` (or the default XDG config file), then XDG defaults.
The config file must be user-owned and mode `0600`:

```text
~/.config/a-stock-agent/runtime.env
~/.local/share/a-stock-agent/cache.db
~/.local/share/a-stock-agent/logs/
~/.local/share/a-stock-agent/locks/
~/.local/share/a-stock-agent/artifacts/
```

The production config contains the state paths and notification mode. Keep
Telegram credentials in that external file or the existing secret store; do
not copy them into this repository or evidence.

## Routine checks

Use the stable commands from any working directory:

```bash
a-stock-cache holdings
a-stock-cache portfolio-risk
a-stock-cache check-holdings
a-stock-fetch check <代码>
```

`holdings` and `portfolio-risk` are read-only views. `check-holdings` is an
R1 routine check: it may refresh market data and record an alert, but it does
not write holdings, transactions or other W1 investment state.

For a cron-equivalent smoke, disable notifications and point at the external
config explicitly:

```bash
A_STOCK_CONFIG_FILE="$HOME/.config/a-stock-agent/runtime.env" \
A_STOCK_NOTIFY_MODE=disabled \
  bash scripts/check-holdings-cron.sh
```

## S1 risk closure candidate (not deployed)

`monitor-snapshot --json` and `portfolio-risk` accept the same optional
`--portfolio-value`, `--max-position-risk-pct` and `--max-portfolio-risk-pct`.
Absent overrides, limits remain 2% / 8%, explicitly marked unconfirmed
compatibility defaults. The report displays the effective source; models must
not invent overrides to bypass a breach. Missing total assets or risk inputs
cannot establish budget compliance. A known breach remains visible even if
another holding is unpriced; complete total risk remains unavailable.

Budget review is read-only. It does not sell, change stops, persist alerts or
block recording a user-confirmed broker execution under existing W1 rules.
The `risk_budget_exceeded` reason requires the matching monitor-v1 validator,
CLI and Skill release set; see [runtime contracts](architecture/runtime-contracts.md).

S1 work is isolated from the active Skill symlinks. Do not pull the new source
into that active working tree as an implicit deployment. Deploy only under a
separate authorization using a complete immutable release directory, after
client qualification and compatibility inventory. The old producer/consumer
pair can return clean despite a budget breach; rollback therefore requires
manual budget review or suspension of risk suggestions, not a claim of safety.
No S1 database migration, cron change or account-data cleanup is required.

## Write boundary

`set*`, alert/L3/Tier updates and holding or transaction commands are W1.
Invoke them only after the user confirms the concrete action and append the
global `--confirm-write` flag. Without it, the CLI exits `3` and does not open
a write transaction. A research or monitor report is a recommendation, not an
executed order.

## Cron and notifications

The candidate cron script loads external configuration, uses the stable
`a-stock-cache` command, takes a non-blocking lock and writes only to the
external log directory. `A_STOCK_NOTIFY_MODE=disabled` is the default for
tests and smoke runs. Telegram is enabled only by the production config and
only for a real or explicitly controlled verification event.

Do not install a second holdings cron entry. Before changing crontab, save the
complete current crontab, inspect the candidate diff, and verify that exactly
one canonical holdings task remains.

## Backup and rollback

For a state migration use `scripts/migrate_state.py`; it uses SQLite's Online
Backup API and records integrity, schema and count invariants. Never copy a
production database into the repository. The installer creates its rollback
manifest outside the repository; retain it with the external runtime backup.

If the new runtime has not written production state, rollback is:

1. stop the new cron;
2. restore the previous crontab and client links from the manifest;
3. point `CACHE_DB_PATH` back to the previous database;
4. run integrity and read-only smoke checks with notifications disabled.

If the new runtime has written state, stop all writers first. Do not simply
switch databases; export and reconcile the event/holding differences before
choosing a recovery path.

## Current deployment record

The current runtime is `v0.1.11` (`0.1.11-2c2d6018d411`, runtime source
commit `2c2d6018d4115fbea4dcdf214ce1786f50b478bf`) with the immutable
`a-stock-lib==0.7.0` release wheel (SHA-256
`7c4a16d452f34574584531bab6fe9d150f3cb844e5c9b2fe072295f6bb2ee385`).
Rollback manifest `rollback-1789186222598162920.json` preserves the prior
client Skill entries; runtime `0.1.11-75a3bee8068e` remains installed and
executable for CLI rollback. The repository HEAD may be newer because this
deployment record is committed after cutover.

The nine active client Skill entries and all three public CLI links resolve to
the current canonical/runtime targets. Package provenance, isolated imports,
CLI help, `pip check`, and installed-file hashes were verified. Production DB
and crontab hashes remained unchanged during the runtime-only cutover; no
holdings, W1 state, credentials, or production DB contents were read or written.

The original `v0.1.0` cutover record, redacted DB invariants, client links,
cron before/after snapshots and review disposition are in
[`migration/production-cutover/20260809-115052/`](migration/production-cutover/20260809-115052/).
