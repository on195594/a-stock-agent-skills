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

The current runtime is `v0.1.5` (`0.1.5-898af3b6a6f0`) with
`a-stock-lib==0.6.0`. Its library manifest records source commit
`cc413c2636a3f0cbfdd5def0c44af824719c2f80` and a hash-matching wheel retained
under the runtime `artifacts/` directory; rollback manifest
`rollback-1787477884662390720.json` preserves the prior client entries.
The previous `0.1.4-57c882433eeb` runtime remains installed for rollback.
Configuration and crontab SHA256 fingerprints were unchanged, and no database
schema migration was performed.

The nine active client Skill entries still resolve to the canonical repository.
The installed runtime exposes `score-fundamentals` as an R0 command. An isolated
temporary-state production-entrypoint smoke returned a complete A-framework
60-point result with rule version `2026-08-23.v1`. Configuration and crontab
fingerprints matched their pre-cutover values; no database schema migration ran.

The original `v0.1.0` cutover record, redacted DB invariants, client links,
cron before/after snapshots and review disposition are in
[`migration/production-cutover/20260809-115052/`](migration/production-cutover/20260809-115052/).
