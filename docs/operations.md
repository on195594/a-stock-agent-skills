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

Active Skill and CLI links share the versioned release pointer described below,
selecting the complete 0.1.13 pair after the authorized 09:36 cutover on 2026-09-18. Do not pull source into a live discovery target or install a single client
against an incompatible shared runtime. Deploy a complete release under explicit
authorization with compatibility inventory and qualification/waiver recorded. The old producer/consumer
pair can return clean despite a budget breach; rollback therefore requires
manual budget review or suspension of risk suggestions, not a claim of safety.
No S1 database migration, cron change or account-data cleanup is required.

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

If the new runtime has not written production state, rollback is:

1. stop the new cron;
2. restore the previous crontab and client links from the manifest;
3. point `CACHE_DB_PATH` back to the previous database;
4. run integrity and read-only smoke checks with notifications disabled.

If the new runtime has written state, stop all writers first. Do not simply
switch databases; export and reconcile the event/holding differences before
choosing a recovery path.

## Initial 2026-09-18 preflight — historical, before activation

The client checkpoint was subsequently resolved by bounded Hermes/Codex qualification
and the user's explicit Claude verification waiver, but a separate schema gap later
required rollback. See the current record below.
The user authorized pushing and production deployment. Agent `4789fc9` and
Tracker `7516535` were pushed to master. Cutover is **blocked pending current-client
qualification**, not pending another generic deployment authorization.

- Live read-only inventory confirms the active Agent runtime is still 0.1.11,
  Python 3.13.5 / lib 0.7.0. Tracker's active interpreter also reports lib 0.7.0.
  All nine Skill links still resolve to the original Agent checkout; all three
  stable CLI links still resolve to `0.1.11-2c2d6018d411`.
- A candidate wheel/runtime (0.1.13 / declared lib 0.8.0), exact Skill sources,
  Tracker source archive and hash-bound preflight record are staged outside Git:
  `~/.local/share/a-stock-agent/deployment-candidates/20260918-4789fc9/`.
  `pip check`, isolated CLI help, and byte comparison of all 25 runtime Python
  files against both wheel and installed candidate passed. No active link changed.
- Native `claude auth status` returned exit 1, `loggedIn=false`, `authMethod=none`.
  Credentials were not changed. The required current-release budget scenario has
  not qualified Claude, Codex or Hermes. Historical captures cannot replace it.
- Hermes CLI warns that gateways may retain pre-update modules; that warning
  needs live verification, not an assumption that a CLI run qualifies the gateway.
  No gateway restart was attempted.
- No production database, runtime config, cron, policy or experiment registration
  was modified. Tracker remains on its prior active checkout; pending remains
  pending. The staging tree is not a production deployment or a new rollback target.

Next: restore Claude authentication through its supported login/configuration,
run the isolated current-release budget scenario for each intended client, verify
Hermes gateway consistency, and coordinate a complete immutable runtime/Skill
cutover with rollback evidence. Do not partially switch the shared CLI while old
consumers remain active. Until then, retain manual budget review; the old runtime's
unsafe clean behavior is not made safe by this staging exercise.

## Current deployment record

**DEPLOYED_AFTER_AUTHORIZED_MIGRATION_035 — 2026-09-18 09:36 CST.**

The user separately authorized migration 035: add nullable
`analysis_results.decision_json TEXT` and register `035-analysis-decision-json`.
Only that migration was executed. Runtime **0.1.13 / lib 0.8.0**, source
`4789fc9272149d97f8297376afd8f469eed30f7f`, is now active through the shared
`current` release pointer: three CLI links and nine client Skill links.
Hermes gateway is active/running after restart (Result=success, NRestarts=0).

- Before mutation, SQLite Online Backup produced the protected snapshot
  `~/.local/share/a-stock-agent/backups/migration-035-20260918T013603Z/cache-before-035.db`
  (directory 0700, file 0600); its integrity and row fingerprints were verified.
- The existing schema process lock and `BEGIN IMMEDIATE` serialized writers.
  The nullable column and one ledger entry committed in the same transaction;
  general bootstrap/backfill was not invoked. An in-memory check also verified
  that explicit-transaction DDL rolls back on failure.
- All original columns, every original table row, old migration records and
  other schema objects were compared inside the transaction and remained
  unchanged. Existing analysis rows received NULL, not fabricated decisions.
  Foreign-key check results were unchanged; independent backup/production
  readback passed `quick_check`. Database bytes necessarily changed for the
  authorized schema/ledger operation; this is **not** a zero-DB-write claim.
- Current CLI help and twelve target links were checked. All 28 Skill files
  match the release Git tree; all 25 runtime Python files match Git, source,
  wheel and installed files. `uv pip check` passed for 34 installed packages.
  The previously captured same-release Hermes/Codex budget replays remain applicable;
  Claude is **DEPLOYED_NOT_VERIFIED_USER_WAIVER**, with no authentication/model
  check added. Live channel delivery and real-account performance remain untested.
- Crontab bytes are unchanged. No trading/holding/event write, personal-policy
  adoption, experiment registration, provider/credential edit or test notification
  was performed.

### Tracker S2 deployment — 2026-09-18 13:17 CST

After explicit deployment authorization, the production Tracker checkout was
fast-forwarded from `69f11c9` to remote master `7516535`; its virtual environment
was coordinated from a-stock-lib 0.7.0 to the declared immutable 0.8.0 wheel.
Post-cutover validation passed 299 tests, 11 structure tests, Ruff check/format,
mypy and diff check. A read-only production DB smoke returned
`MANIFEST_PENDING / INSUFFICIENT_EVIDENCE`, as required by the unregistered
manifest. Existing cron was inspected and left unchanged. No manual daily run,
database write, notification, credential edit, experiment registration or S4 work
was performed.

This was an independent Tracker checkout deployment, not a mutation of the earlier
Agent runtime/Skill release. The Agent-scoped `ACTIVE_RELEASE.json` was finalized
before this cutover; its `tracker: NOT_DEPLOYED` field is a timestamped 09:36 CST
fact, not the current Tracker state or a unified three-repository manifest. Keep
that evidence immutable. Current Tracker identity is established by its synchronized
production checkout, installed lib version, read-only smoke and this separate record.

The permanent Agent release directory below contains `migration-035-result.json`,
`authorized-cutover-result.json` and the final `ACTIVE_RELEASE.json`. The private
backup directory also contains the integrity and original-row fingerprint receipt.
A runtime/Skill rollback must preserve the additive column, ledger entry and all
subsequent facts: switch the paired code/Skills, **never automatically restore the old DB**.

### Earlier schema-gated rollback (historical)

At 08:47 production was restored to **0.1.11 / lib 0.7.0**, with Skill source `2000d750`.
The shared `current` pointer then selected the retained `rollback-view`; all twelve
entries remained coordinated and no longer depended on a mutable Skill checkout.
Hermes gateway was restored and was active/running (Result=success). The supervised
rollback restart raised NRestarts to 1; this is not a reported crash loop.

A late schema compatibility check found that the cumulative 0.1.11 → 0.1.13 delta
includes `035-analysis-decision-json`: `ALTER TABLE analysis_results ADD COLUMN
decision_json TEXT`. Production then lacked that column. The initial preflight checked
`db.py` but missed the migration in `schema.py`; latest-schema fixtures and CLI
help do not establish production-schema readiness. Before any future activation,
compare **both schema code and migration list** with the active release, then
inspect the live schema read-only. Do not let a subsequent business command
implicitly perform an unapproved migration.

At this rollback checkpoint no migration had been executed; financial DB/WAL
fingerprints and crontab bytes matched the pre-cutover baseline.
`schema-rollback-result.json` preserves that checkpoint, while
`activation-result.json` preserves the earlier temporary activation. The later
explicit schema authorization and final successful deployment are recorded above.
Any return to the old runtime still requires manual budget review.

## Historical 2026-09-18 activation attempt

On 2026-09-18 the user explicitly requested Claude production switching without
authentication or verification, and continued Hermes cutover. Runtime **0.1.13**
(source `4789fc9272149d97f8297376afd8f469eed30f7f`) with **lib 0.8.0** was briefly
activated at 08:33, then rolled back at 08:47 for the schema gate above.
All three public CLIs and nine Claude/Codex/Hermes Skill entries resolve through
`~/.local/share/a-stock-agent/current` to the same complete release view.

Permanent active release/evidence directory (despite its original staging name;
**do not delete it as temporary content**):
`~/.local/share/a-stock-agent/deployment-candidates/20260918-4789fc9/`.
`deployment-preflight.json` binds wheel, source and Skill hashes;
`ACTIVE_RELEASE.json` records the latest authorized Agent runtime/Skill deployment
and twelve-link state at its recorded timestamp; it is not a mutable Tracker registry.
`activation-result.json` preserves the temporary cutover checkpoint, and `rollback.json` keeps
the original twelve link targets. `release-view` contains the current paired set;
`rollback-view` retains the old Skill bytes and 0.1.11 CLI targets.

- **Claude: DEPLOYED_NOT_VERIFIED_USER_WAIVER.** No authentication or model check
  was retried. Link switching is not a claim of client qualification.
- **Hermes:** native CLI loaded candidate Skills and passed the synthetic
  portfolio-only over-budget replay; session provenance confirms the intended
  provider/model and zero actual domain/tool calls. After activation, another replay
  passed using the actual configured default `openai-codex/gpt-5.6-sol` (rather
  than relying on the earlier `gpt-5.6-sol-900k` alias); native provenance was checked
  read-only for that synthetic session. The response preserved review,
  read the portfolio reference in the simulated trace, froze added risk, and did
  not invent a policy, clean status or W1 authorization. Gateway was restarted;
  systemd readback was active/running, Result=success, NRestarts=0.
- **Codex:** native CLI read the named candidate Skill/reference and passed the
  same injected-domain-result budget replay. These bounded replays do not prove
  real-market execution, live Telegram delivery or all client paths.
- The first attempt safely restored old entries and the gateway after a terminal
  icon change confused the evidence parser. The original raw model response was
  retained and independently parsed/checked with native session provenance; no
  evidence was rewritten to change a failing model decision. The second attempt
  atomically switched the shared release pointer and passed three active CLI help
  checks. Financial DB and WAL hashes and crontab bytes matched before/after.
- No production SQL writes, schema migration, cron/config edit, policy creation, trading
  write, or test notification was executed. Hermes recorded its native synthetic
  verification session; that is not a financial-state write. Tracker remains at
  active source `69f11c9` / lib 0.7.0 and is **not deployed** to e2.

Rollback in a coordinated maintenance window: use the native Hermes planned stop,
atomically repoint `current` to the retained `rollback-view`, then start the gateway
and check discovery/CLI identity. `rollback.json` can also restore the original
direct links. Keep the same financial database; do not restore old data snapshots.
The old runtime has known unsafe clean behavior, so rollback requires manual budget
review rather than a safety claim. Existing conversations may retain old Skill
context; reload the Skill or start a new session after cutover.

## Historical 2026-09-12 deployment record

The then-current runtime was `v0.1.11` (`0.1.11-2c2d6018d411`, runtime source
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
