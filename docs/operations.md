# Operations runbook

This runbook covers the currently installed runtime after the M7 cutover and
later coordinated releases. Claude, Codex and Hermes remain supported clients.
Nothing here authorizes investment decisions or unattended W1 writes.

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

### Host execution note

The portable Monitor Skill requires a command-execution tool that preserves
stdout, stderr and exit status. On Hermes, use `terminal` for `a-stock-cache`
and `a-stock-fetch`, rather than wrapping the workflow in `execute_code` (its
300-second cell timeout discards kernel state). This host-specific mapping is
maintained here, not injected into the shared Skill payload.

The 2026-09-29 Skill publication replaced the older local execution note with
the canonical host-neutral requirement. Publish canonical Skill files in new
immutable releases; do not reintroduce the old extra line.

### Commands

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

For a cron smoke, use the isolated fixture check, not production configuration:

```bash
A_STOCK_NOTIFY_MODE=disabled bash tests/test_check_holdings_cron.sh
```

The cron script sources its config after reading the inherited environment;
`A_STOCK_NOTIFY_MODE=disabled` alone does not override a config that enables
Telegram. The fixture uses temporary state/config and fake CLI/notification tools,
so it cannot access production holdings or send a real message.

## S1 risk closure (deployed after authorized migration 035)

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

Read back the actual Skill and CLI link targets; the `current` pointer alone is
not activation evidence. The [current deployment record](#current-deployment-record)
identifies the selected runtime/Skill pair and any drift. Do not pull source into a live discovery target or install a
single client against an incompatible shared runtime. Deploy a complete release
under explicit authorization with compatibility checks and client verification
limits recorded. Do not roll back to a pre-risk-closure runtime that can report
clean despite a budget breach. Repository maintenance does not require a schema
migration, cron change or account-data cleanup.

## S3b file-only account performance (runtime deployed; real accounts unverified)

```bash
a-stock-cache performance-report --input /private/external/account.json --json
a-stock-cache performance-report --input /private/external/account.json \
  --benchmark /private/external/benchmark.json
```

The input schemas and synthetic example are fixed by [spec §8.3–8.5](specs/2026-09-17-a-stock-risk-closure-and-performance-validation-spec-v1.1.md).
Keep real source files in a protected directory outside Git; do not mix accounts.
The command reads files and emits stdout (text by default, JSON with `--json`);
it neither reconstructs account equity from holdings nor saves/imports facts.
Without `--check-ledger`, dispatch does not resolve a database path or enter a
DB handler. No network, notification, database creation, migration or output-file
write is performed. Source files are not corrected or modified.

Amounts are Decimal strings. Returns remove only permitted external flows;
broker equity already includes investment income, fees and corporate actions.
Unknown/intraday flow timing breaks the chain. `end_assumed` requires the explicit
`--allow-eod-flow-assumption` flag and remains estimated, even when source
reconciliation is also provisional. Withdrawal-to-zero is not total loss;
a positive balance after zero establishes a new baseline. Missing dates/intervals
are never bridged into a full-period return or drawdown. No calendar means
observed-only drawdown, not complete daily-close or intraday coverage.

Optional benchmark NAV supports more than two decimal places. Invalid JSON,
null/schema/currency/date/effectivity gaps preserve the absolute report but
suppress comparison. Price-return references are explicitly distinguished from
total-return references; neither implies an executable alternative was evaluated.
`null_reasons` explains unavailable segment metrics; unrequested benchmark is not
an error. Baseline-only input has no measurable return interval (exit 4).

`--check-ledger` is a deliberately limited read-only diagnostic: missing database,
missing history/schema or inferred records are disclosed. Without verifiable
account mapping, row counts are **not** account reconciliation; the report stays
limited/provisional and does not invent cash flows or write back to holdings.

Exit codes: 0 usable requested calculation; 2 invalid account/schema/arguments;
4 a parsed business report with gaps (including requested unusable benchmark or
ledger evidence); 1 unexpected runtime/I/O failure. `exact` is conditional on the
file's source declarations and flow model, not independent broker authentication,
GIPS compliance, causal AI attribution or trading permission.

## S3a read-only risk policy (runtime deployed; no personal policy adopted)

Both risk commands additionally accept `--policy-file`, `--account-scope` and
`--portfolio-value-as-of`. A shared resolver applies explicit numeric overrides,
then a selected effective/confirmed file, then the unconfirmed 2%/8% defaults.
A numeric override never suppresses an invalid selected file. It is not permission
for a model to alter a user's policy or to record a trade.

Policy path selection is CLI → `A_STOCK_RISK_POLICY_FILE` in environment/runtime.env
→ `risk-policy.json` beside the selected runtime.env (the XDG config directory
by default). Only absence of an unconfigured default permits fallback. Files are
read-only, regular, current-user-owned and mode 0600 or stricter. No command
creates, updates or confirms a policy file. The exact schema is in
[spec §8.1](specs/2026-09-17-a-stock-risk-closure-and-performance-validation-spec-v1.1.md).
A file requires an explicit matching account scope and valid timezone-aware
confirmation/effectivity timestamps. Source/confirmation metadata is not a W1 token.

`account.portfolio_value_as_of` is the supplied asset valuation time, not snapshot
collection time. `denominator_freshness_status=as_of_provided` does not independently
prove freshness; no new TTL is imposed. Missing scope or as-of yields
`denominator_requires_review=true`: no authorization for new risk, even if the
existing-position budget report has a clean fast gate. No default 5% drawdown
limit or maximum-drawdown guarantee is introduced.

Invalid risk parameters return controlled failure before market/DB reads in the
handler. Deployment created no real policy file and did not adopt a personal policy;
client activation and verification boundaries are recorded below.

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

For the current schema-compatible release, follow its external `rollback.json`
after explicit rollback authorization. Verify the active pointer still matches
that release, retain both release trees, and atomically restore the recorded
previous `current` target. Do not restore a database, change `CACHE_DB_PATH`,
rewrite client links or alter cron. Validate stable CLI entries using isolated
state and disabled notifications, and reload Skills in existing sessions.

Schema/configuration/cron rollbacks are separate operations requiring their own
authorization and matching evidence. If writes used an incompatible schema or
state contract, pointer-only rollback is not sufficient: stop affected writers
under explicit authorization and reconcile compatibility before proceeding.

## Current deployment record

### Release preflight — 2026-10-07

Live readback supersedes the historical pointer-only deployment description below:
the stable CLI links select `runtime/0.1.13-9574b686f910/venv/bin`, and all nine
client Skill links select the canonical `skills/` directories. The older `current`
pointer is not the active CLI or Skill owner. These links remain unchanged.
Version 0.1.14 (`785460a`) is committed, pushed and published with the hash-pinned
a-stock-lib 0.8.2 wheel, but is not activated on this host.

The exact release passed all 1338 repository tests, including both optional
candidate installer checks; the other repository gates and GitHub CI passed.
The normal installer without dependency overrides passed in an isolated target
root for all clients. All 38 installed Python modules match the release wheels;
all 78 client Skill file copies match committed sources. Dependency checks and
the CLI confirmation-gate smoke passed without protected-state writes.

Production activation is blocked pending explicit credential-routing approval:
the selected runtime config does not contain `TUSHARE_TOKEN`, and direct CLI
execution does not export it. The new library no longer discovers Tracker's
`.env`. Do not activate first and silently borrow or move credentials afterward.
The existing database parent already satisfies 0700; no permissions, database,
client links or cron changes are required or authorized by this preflight.

The release includes literal SQLite read-only paths and fail-closed private-parent
checks. `a-stock-fetch check` can still print a traceback when a selected database
parent is non-private; refusal and exit 1 remain effective and create no database.
This presentation issue does not justify relaxing the permission guard.

### Repository maintenance — 2026-09-30

After explicit user authorization, `50c55b2` was committed, pushed and deployed.
`current` now selects
`~/.local/share/a-stock-agent/deployment-candidates/20260930-50c55b2-maintenance/release-view`.
The 0.1.13 runtime removes the unused `store.get_risk_gate` helper and three
unused status sets; CLI/write gates and investment rules are unchanged. Tests
now exercise the actual stored-gate aggregation path and combine redundant
top-level CLI help checks. README and operations use current release/rollback
instructions; completed architecture-review and superseded deployment prose
remain recoverable from Git. No production alert was cleared.

The full repository gate passed: 1328 tests passed, two optional installer checks
skipped; Ruff lint, Skill validation, regulatory freshness, standalone QA and
cron smokes passed. All 25 installed modules match the committed source and
candidate wheel. All 26 Skill files and 34 installed package versions match the
previous release. Installed gate-aggregation regressions preserve missing-data
fail-closed behavior without backfill; installed copy/symlink regressions and
identical before/after CLI help checks passed. Offline W1/fail-closed/monitor-v1
smokes passed before activation and again through stable CLI entries afterward.

All twelve entry link texts, DB/WAL/SHM and runtime-config fingerprints, and the
crontab hash remained unchanged. No schema migration, production data write,
notification or service restart occurred. Fresh native-client model qualification
was NOT_RUN; existing sessions should reload the Skill or start a new session.
The candidate directory retains source/wheel hashes, validation logs,
`ACTIVE_RELEASE.json`, and `rollback.json`. Pointer-only rollback restores
`20260930-fc54fb6-install-cleanup/release-view`; do not restore a database or
remove retained releases. Later documentation commits do not change the deployed
runtime/Skill source identity.

## Historical deployment evidence

Superseded deployment and preflight records are retained in Git, not as current
operating instructions. Read the preceding 2026-09-30 deployment record and the
older complete ledger from their source snapshots:

```bash
git show 50c55b2:docs/operations.md  # fc54fb6 copy-install hygiene deployment
git show f5307f7:docs/operations.md # older complete ledger
```

The older snapshot includes the 2026-09-12/18 activation attempts, schema-gated
rollback, 2026-09-18/20 Tracker registration, and 2026-09-28/29 publications.
Tracker Framework A closed as `CLOSED_UNPROVEN` on 2026-09-21; historical S2
activation and maturation notes are not pending work. The Research A—F contracts
remain active. Dated investment authorizations under `specs/` and migration
evidence remain in place.

Retain previous external release trees, rollback manifests and private evidence;
removing historical prose from this document is not authorization to delete them.
