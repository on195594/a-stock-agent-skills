# Operations runbook

This runbook covers the currently installed runtime after the M7 cutover and
later coordinated releases. Claude, Codex and Hermes remain supported installer clients. On this host, Pi
and AGY also discover the shared Codex Skill directory.
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

The production config contains the state paths and notification mode. After
explicit authorization, `TUSHARE_TOKEN` can be configured in the same private file;
market-data adapters resolve environment → selected runtime.env and pass only the
token to `a-stock-lib`. An exported token takes precedence. Missing credentials
remain fail-closed; no Tracker file is discovered and no settings are exported by
the direct CLI. Keep Telegram credentials in that external file or the existing
secret store; do not copy credentials into this repository or evidence.

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
a-stock-cache dividend-check
a-stock-cache benchmark-report
a-stock-cache report-trades
a-stock-fetch check <代码>
```

`holdings` and `portfolio-risk` are read-only views; `dividend-check`,
`benchmark-report` and `report-trades` read TuShare but write nothing. `check-holdings` is an
R1 routine check: it may refresh market data and record an alert, but it does
not write holdings, transactions or other W1 investment state.

Runtime 0.1.32: with a-stock-lib 0.9.0, `benchmark-report`
uses the library's date-bounded `.CSI` closing-point provider instead of a direct
SDK shortcut. Stock valuation uses the nearest close within ten calendar days;
a fallback prints its actual date, age and source to stderr, never a silent
same-day quote. A longer suspension or missing index data fails closed.

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

## S3a read-only risk policy (runtime deployed; personal policy in use)

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
handler. The user's own `risk-policy.json` (`personal-risk-policy-20261009`: 6% per
position, 18% portfolio, confirmed 2026-10-09) is in use and requires an explicit
matching `--account-scope`; no command created or edited it. An optional
`off_account_strategy_cash` field adds strategy cash held outside the broker account
to the denominator ([2026-10-22 spec](specs/2026-10-22-risk-denominator-and-breach-attribution-spec.md));
it is not configured. An optional `untradable_boards` field (`STAR`, `BSE`) keeps those boards
researched but out of buy/switch advice and sizing, and applies even without an account scope
([2026-11-04 spec](specs/2026-11-04-untradable-boards-spec.md)).

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

The cron script pushes only when `check-holdings` prints `项预警，请及时处理`
(price or P3 stop alerts); risk-gate freeze lines alone are logged, not pushed.

Do not install a second holdings cron entry. Before changing crontab, save the
complete current crontab, inspect the candidate diff, and verify that exactly
one canonical holdings task remains. Hermes no-agent jobs running read-only
`stop-alert` (intraday, deduplicated per day), `daily-brief` and
`benchmark-report` are push supplements, not holdings tasks; they never record alerts.

## Backup and rollback

The current installer prepares the runtime and all three Skill snapshots under
one new release directory before switching any client or CLI entry. Symlink mode
uses the release snapshot; copy mode copies it. An existing release directory is
never rebuilt, even with `--force`. Use a new committed release identity for changed
content; retain failed candidate directories for diagnosis rather than overwriting
an active or ambiguous release.

All replacement entries are prepared and checked before activation. A failed
switch restores entries already touched, including previously absent paths.
The rollback manifest records each entry's kind, backup and original symlink target;
symlink backups remain text files, not executable links. This handles ordinary
caught installation failures, not power loss or a killed installer. If automatic
restoration fails, the installer reports the affected path and manifest for recovery.
These source changes do not convert existing source-linked installations until
an explicitly authorized activation.


For a state migration use `scripts/migrate_state.py`; it uses SQLite's Online
Backup API and records integrity, schema and count invariants. Never copy a
production database into the repository. The installer creates its rollback
manifest outside the repository; retain it with the external runtime backup.

For the current schema-compatible release, use the installer manifest and saved
Skill contents identified in the deployment record after rollback authorization.
Retain both runtimes, then restore the recorded CLI/Skill targets and matching
canonical Skill contents; links alone cannot restore text in a mutable source tree.
The historical `current` pointer owns nothing. The current release does not
change Research credentials. Preserve the named, revocable long-lived API key;
do not restore an old runtime.env containing an expired or revoked token.
A rollback must preserve unrelated
configuration changes, account state, model settings and cron. Reload Skills in
existing sessions after either activation or rollback.

Schema/configuration/cron rollbacks are separate operations requiring their own
authorization and matching evidence. If writes used an incompatible schema or
state contract, pointer-only rollback is not sufficient: stop affected writers
under explicit authorization and reconcile compatibility before proceeding.

## Current deployment record

### 0.1.43 activation (2026-11-06)

Owner explicitly requested commit and deployment in the maintenance session.
Activated **`0.1.43-14838df3a862`** from commit `14838df` after full local validation
(1852 passed / 11 skipped and all `scripts/check.sh` gates) and successful hosted
[CI run 42170735829](https://github.com/on195594/a-stock-agent-skills/actions/runs/42170735829).
The native installer ran dry-run, then `--client all --mode symlink --force`.

Readback verified all 9 Claude/Codex/Hermes Skill links and all 3 stable CLI links
point into that release. All 59 runtime/Skill source files match the committed
source by SHA-256; installed versions are suite 0.1.43 and a-stock-lib 0.10.2.
CLI help smoke passed with isolated state, absent config and notifications disabled.
No account operations, schema migration, credentials or cron changes were made.
Existing client sessions must reload Skills; live-session reload and candidate
model behavior replay were not verified by this deployment.

Evidence: `~/.local/share/a-stock-agent/deployments/maintenance-0.1.43-20261106/`.
Rollback manifest: `~/.local/share/a-stock-agent/rollback-1793944289034472640.json`.
The old `0.1.42-14cbe7ff9acc` runtime and frozen Skill snapshot remain available.
The deployment-record commit does not change the activated runtime/Skill bytes.

### 0.1.43 maintenance review and validation (2026-11-06)

The current working tree freezes runtime/Skill installation together, validates
linked report code/time before ledger writes, reuses prices within `report-trades`
and bounds optional Research card transport waits. Skill/report/QA guidance now
agrees on the single action, brief-report display and clean-monitor stop boundary.
Markdown link checks include optional titles. Copy-mode replacement handles old
files and symlinks, including rollback after unlinking an old entry.

Independent AGY `gemini-3.8-flash-high` source review completed in three groups.
The reproduced copy-mode failure and QA display conflict were fixed; the Monitor
sizing ambiguity was clarified. The proposed rollback-record timing change was
rejected after a failure-injection check proved that recording before directory
removal is necessary for recovery. Source review findings require this evidence
check; they are not automatically confirmed defects.

The latest fixes passed 9 targeted installation cases and 70 Skill/QA/validation
tests, plus 17 runtime-free QA contract assertions, Ruff and the project validator.
Before the authorized commit/deploy, the complete local `scripts/check.sh` passed:
1852 passed, 11 skipped, Ruff, regulatory freshness, standalone QA and cron smoke.
This supersedes the earlier 1837/11 result. Candidate model behavior remains
NOT_RUN in [behavior evaluation](agent-behavior-eval.md#current-semantic-regression-cases-2026-11-06).
The candidate was subsequently committed and activated as recorded above. No
schema, account, credentials or cron change is part of this release.

Task evidence and the superseded temporary source copy were archived outside Git
under `~/.local/share/a-stock-agent/reviews/maintenance-20261106/` before temporary
files were removed. The archive includes its file hashes and verification result;
old review reports describe pre-fix sources, not outstanding implementation work.

### Source-linked Skills frozen before repository maintenance (2026-11-06)

Owner explicitly confirmed freezing the old production Skill text before applying
the reviewed repository improvements. All nine Claude/Codex/Hermes Skill links
were first frozen into `runtime/0.1.42-14cbe7ff9acc/skills/`, including the shared
`~/.agents/skills` entries. The 28 tracked Skill files and their three referenced
specifications were copied from clean source `bf426aa27ae3`; all 31 file hashes
match the old content. CLI links remained on `0.1.42-14cbe7ff9acc` during that freeze.
Manifest and prior link targets:
`~/.local/share/a-stock-agent/deployments/skill-source-freeze-1793936019349043840/manifest.json`.
That freeze only isolated production from source edits; it did not activate the
new repository changes. It was superseded by the 0.1.43 activation above. No account, schema, credentials or cron changes. Returning links
to source after maintenance would expose new text, so it is not a content-preserving
rollback and requires a separate activation decision.

### 0.1.42 activation (2026-11-06)

Owner approved commit, push and activation (Telegram msg 4220, 2026-11-06) after a
read-only review of the report link. Activated **`0.1.42-14cbe7ff9acc`** using the
native installer (`--client all --mode symlink`, dry-run then force), only after
hosted CI succeeded on the exact commit `14cbe7f` (run `42134707740`).

Change: `--report-id` on `add-holding` / `buy-holding` / `sell-holding` is checked
with `GET /api/reports?code=` before the write transaction. The report must belong
to the traded code, be `done` and passed, and not be dated after the trade date.
Otherwise nothing is written, including when Research is unavailable or not
configured. Unlinked trades never call Research. No Research change, schema change,
new dependency, or eligibility, account gate, L3, W1 or investment-policy change.
The check cannot tell apart reports of the same stock or order a report and a trade
within one day, so it echoes the report's name and time. A report deleted after
linking leaves the link dangling, and `reports.id` has no AUTOINCREMENT, so deleting
the newest report reuses its id: check the ledger before deleting a Research report.

Validation: ordinary-change tier, 361 passed / 2 skipped (report-trades, version,
installation, Skill validation, CLI contract, Research client, cache), Ruff; 10 of 10
mutations of the gate caught; full gate by hosted CI. Installed readback: runtime
0.1.42, all 31 modules match source. The installed CLI on an isolated ledger against
real Research refused #94 on 002648 (another stock), #110 on a trade before it,
failed #106 and unknown #999999, accepted #102, refused a linked trade with Research
unreachable and recorded an unlinked one. Live ledger data and schema digests match
before and after (37 events, 0 linked). No trades, backfill, notifications, paid
research, credentials, configuration or cron changes.

Evidence: `~/.local/share/a-stock-agent/deployments/report-link-0.1.42-20261106-0810/`
and `~/.local/share/a-share-research-evaluations/report-link-review-20261106/`.
Rollback manifest: `~/.local/share/a-stock-agent/rollback-1793923835472424400.json`.
0.1.41 remains executable. The Skill text in `data-operations.md` must roll back with
the runtime, because it describes the check.

### 0.1.41 activation (2026-11-05)

Owner explicitly authorized commit, push and publication in this Telegram session.
Research `4c0e67d` was published first, closing the separate homepage/company-page
card projection gap with one shared caution macro; positive live boundary cards,
a normal card and a failed-card control passed browser checks.

Activated **`0.1.41-86170bfe281c`** using the native installer (`--client all
--mode symlink`, dry-run then force), only after hosted CI succeeded on the exact
commit `86170bf` (run `42055914534`). The changed runtime area fixes the undated
ex-dividend case where record date equals the return start: use the existing
unknown/not-comparable result rather than a certain price-only return. Zero-day
windows and known ex-dates at/inside the interval retain their prior semantics.
No schema, eligibility, tranche, account gate, L3, W1 or investment-policy change.

Local full `scripts/check.sh`: **1775 passed / 11 skipped**, Ruff, regulatory
freshness, QA standalone and cron smoke passed. Research reused its exact-content
91-test result. Installed runtime readback: version 0.1.41, all 31 modules match
source, all 9 direct Skill targets match canonical paths, all 3 stable CLI help
checks pass. Four installed pure-function controls verify unknown start, known
inside ex-date, zero-day window and known start ex-date. No paid model turns or
real-account report command were used for these controls.

Read-only schema and protected records match before/after (10 holding rows,
37 event rows). Research integrity/worker preflight passed, model calls remain
915. The 21-card live homepage has two boundary cards; the phone company card
shows its caution outside a fold, the normal card does not invent warnings.
Production currently has no report with `open_questions`: that branch is covered
by captured review questions combined with the captured valuation fixture, not
claimed as a live positive notification or a fabricated production report.
Temporary browser authorization was revoked through logout, confirmed in the
session store, and its private storage-state file removed.

Evidence: `~/.local/share/a-stock-agent/deployments/p2-0.1.41-20261105-232711/`
(before/after account digests), `~/.hermes/projects/codex-p2-fix-20261105/`
(tests, installed-runtime readback and browser checks), Research
`deploy-4c0e67d-20261105-232943/`. Rollback manifest:
`~/.local/share/a-stock-agent/rollback-1793892866379604360.json`.
0.1.40 remains executable. The installer saves former symlink targets as plain
text in its backup files; restore the three recorded old CLI targets, not a link
to the backup file itself. Skill contents did not change in this release, so no
text rollback or account DB restoration is needed. No paid research,
notifications, trades, credentials, configuration or cron changes.

### Historical 2026-10-27 baseline

State as of **2026-10-27**, after explicit paired-release authorization.
Previous activation and rollback evidence remains in `git show 638a0eb:docs/operations.md`.

**Runtime.** Release **0.1.25 (`04dbc6c`, a-stock-lib 0.8.2)**.
The three stable CLI links select `runtime/0.1.25-04dbc6c0c455/venv/bin`.
Claude/Codex entries select `releases/0.1.25-04dbc6c0c455/skills/`;
Hermes retains canonical repository targets for its resolved-path allowlist.
All nine direct Skill entries and 26 runtime files match the committed release.
Previous 0.1.24 runtime and release contents remain available.

**Other local clients.** Pi 1.4.0 natively discovers `~/.agents/skills`; its actual
resource loader found all three Skills without relevant diagnostics. AGY's
`~/.gemini/antigravity-cli/skills` links through `~/.gemini/config/skills` to the
same `~/.agents/skills`. All 15 client/Skill views match the release. No extra
Skill copy, host-specific instruction, or client setting was needed. Future
`--client all` updates also reach Pi and AGY through these existing paths.
Do not replace these shared directory links with a stale independent copy.

**Research connection.** The existing mode-0600 `~/.config/a-stock-agent/runtime.env`
uses `A_STOCK_RESEARCH_URL=https://stock.keyi.win` and the persistent
`skills-runtime` API key (ID 1, created 2026-10-27T15:44:07+08:00). It has no scheduled
expiry and remains valid until revoked. Only `A_STOCK_RESEARCH_TOKEN` changed;
TuShare/Telegram and unrelated settings were preserved. The replaced temporary
credential was revoked. The CLI does not mint or renew credentials. Account schema
remains at migration 035; account state, investment policy, model settings and cron
were not changed.

Owner management uses `docker exec a-share-research-web python -m a_share_research.api_keys`
with `create <name>`, `list`, or `revoke <id>`. Creation prints the secret once;
capture it privately. To rotate, configure and verify the new key before revoking
the old one. Clear stale environment overrides, which take precedence over the file.

**Scheduled jobs.**

| Owner | Job | Schedule | Behaviour |
|---|---|---|---|
| crontab | `scripts/check-holdings-cron.sh` | 09:35 Mon–Fri | canonical holdings check; pushes only on price/P3 stop alerts |
| Hermes `ca568f56d9ef` | `a-stock-stop-alert` | every 5 min 09–15 Mon–Fri | read-only `stop-alert`; once per day per worsening level |
| Hermes `7ab0ded3121c` | `a-stock-daily-brief` | 15:35 Mon–Fri | read-only `daily-brief`; silent without same-day quotes |
| Hermes `93c4f5a4d0fc` | `a-stock-benchmark-monthly` | 09:00 on the 1st | read-only `benchmark-report` |

Hermes jobs are no-agent scripts in `~/.hermes/scripts/cron/a-stock-*.sh`; remove one
with `hermes cron remove <id>`. They replaced the user's hard-coded
`华东医药000963低于27.8预警` job (removed; script and state file left in place).

**Hermes configuration.** `skills.external_dirs` points at this repository's
`skills/` (backup `~/.hermes/backups/config.yaml.pre-skill-dir-20261022`). The private
router `investment-decision-and-account-workflows` now covers non-A-share decisions
and explicitly requested standalone alerts. A-share research/account work goes
directly to the canonical Skills; user-threshold standalone alerts remain supported.
Its previous content is saved as `router-before.md` in the evidence directory below.

**Production state written on 2026-10-22.** 000963/002050 dividends (corporate-action);
P0 regulatory evidence for 000963, 002050, 600900, 603606 (2025 annual period, all
clear). One accidental test write (000963 dividend event 32) was removed; database
backups are under `~/.local/share/a-stock-agent/backups/cache-pre-*-20261022.db`.
No personal `off_account_strategy_cash` is configured.

**Rollback.** Installer manifest: `/home/lin/.local/share/a-stock-agent/rollback-1793091694724515240.json`.
Evidence and candidate model captures: `~/.local/share/a-stock-agent/deployments/slimming-20261027/` (0700).
`before.json` records the prior nine Skill/three CLI targets; `skills-before/`
preserves canonical Skill contents and `router-before.md` preserves the private
Hermes router. Restore matching contents and links together after rollback
authorization, preserving unrelated edits. Pi and AGY follow the restored shared
Skill directory. Do not restore account data, credentials or cron.

**Observed delivery (checked 2026-10-27).** Hermes recorded `daily-brief` as delivered
on 2026-10-22, 10-23, 10-26 and 10-27. Every `stop-alert` run so far was suppressed
(no stop-line crossing). **Not yet observed:** a real `stop-alert` crossing, the
first `benchmark-report` (2026-11-01), and fresh Hermes behaviour under the slimmed router.

**2026-10-27 slimming activation verified.** The existing installer installed
0.1.25 offline using the hash-pinned Lib wheel. All three stable CLI help checks,
15 client/Skill views and 26 runtime files passed. Hermes's actual catalog and
Skill reader found the three canonical Skills and updated private router; Pi's
actual resource loader found the three shared Skills. Claude/Codex/AGY were
verified through discovery paths and matching content, without fresh model turns.
`activation-verification.json`, `hermes-discovery.json` and `pi-discovery.json`
record these checks. Credentials, account state, investment rules, client models
and scheduled jobs were not changed.

The committed release passed **1,450 tests, 11 skipped**, Ruff, Skill validation,
regulatory freshness, standalone QA and isolated cron smoke. Candidate paid
GPT-6.1-sol evaluations and their failures remain archived; the affected L3 case
passed after its existing review prerequisite was clarified. No additional
paid evaluation or real-account flow was run during activation. A later full
replay against the installed release passed the eight cases and four follow-up
groups on GPT-6.1-sol after an evaluation-contract correction; see
[Agent behavior eval](agent-behavior-eval.md#current-status-2026-10-27). It is not a
multi-client or real-account validation.

Hermes currently selects `openai-codex/gpt-6.1-sol-900k`; configuration was not
changed. Existing client sessions may cache old Skill text: reload Skills or
start a new session (Pi supports `/reload`). Installation and discovery checks
do not prove a running conversation has refreshed its context.

## 0.1.40 activation (2026-11-05)

Owner explicitly approved publication in this Telegram session after reviewing the
paired Research/Skills warning fix. Activated `0.1.40-a50f5e6fc505` using the native
installer (`--client all --mode symlink`, `--dry-run` then `--force`), after hosted
CI succeeded on `a50f5e6` (run `42042143569`). Research `b8490e7` was published first.
The previous 0.1.39 same-close trade comparison fixes remain included.

Cards now preserve open questions and separate report/current boundary flags;
opportunity, opportunity-cost and stretched-valuation details/evidence retain the
specific cautions. Eligibility, first tranche, account gates, L3 and W1 rules are
unchanged. Old cards/snapshots remain readable, missing/null is not a negative
certificate, and no automatic waiting or paid research was introduced.

Validation reused the exact-content candidate result: `scripts/check.sh` passed
1772 tests / 11 skipped, Ruff, regulatory freshness, QA standalone and cron smoke;
Research direct-call regression passed 142 tests. Live authenticated cards GET
returned 8 cards; a real monitor snapshot uses runtime 0.1.40, Research status ok,
and passed monitor-v1 including matching source-card cautions. Its business exit
is 1 (`data_status=stale`, `review_status=blocked`) for existing account scope,
portfolio denominator and evidence gaps; these were not relaxed or repaired as a
side effect. The unchanged account/risk builder was compared to 0.1.39. Installed
runtime replay of archived inputs also confirmed 4 positive boundary opportunities
and 3 unanswered-question variants, explicitly not actual delivered notifications.
31 runtime modules and 15 logical client/Skill views match source (Pi shares
`.agents/skills` with Codex; AGY follows its configured shared path); all 3 CLI help
checks pass. Existing client conversations may cache old Skill text; no paid client
model turns were used to refresh them.

Rollback manifest: `~/.local/share/a-stock-agent/rollback-1793887811227008640.json`;
0.1.39 remains installed. Before the source-linked Skill text changed, its matching
contents and link targets were saved under
`~/.local/share/a-stock-agent/deployments/risk-warning-0.1.40-20261105-2203/`
(`previous-skills/`, `before.json`); restore matching text and runtime together,
preserving unrelated later edits, not the account DB. This release has no schema
change. Read-only before/after checks confirm schema and both protected holdings
and event-table digests unchanged (10 holding rows, 37 events). No trades,
notifications, paid research, credentials, policy or cron changes.

## 0.1.39 activation (2026-11-05)

Owner instruction (Telegram msg 4210, 2026-11-05: have Codex review the changes and fix what it finds)
activated `0.1.39-bd54357dc441` for `claude`, `codex`, `hermes` and shared `~/.agents/skills/`,
`--dry-run` then `--force`. Rollback manifest: `~/.local/share/a-stock-agent/rollback-1793884720435478280.json`;
`0.1.38-a2f5c75db5a5` remains installed. No schema change; backup
`~/.local/share/a-stock-agent/backup-pre-0.1.39-20261105-211641.db` (Online Backup API, integrity ok).
Change: `report-trades` compares stock and index from the same closes, counts cash and share
distributions by TuShare ex-date (cash pre-tax, not reinvested), names a stale close or an undated
distribution instead of comparing, and exits 1 without a traceback when the index has no data.
Validation: targeted tests 132 passed / 2 skipped including installer and Skill gates, six mutations of
the new logic each caught by a test, Ruff, hosted CI success on `bd54357`. Real TuShare data on a copy of
the backup, with all 25 priced trades linked only in that copy, produced a comparison for each. Four
checked against `adj_factor` agree within 0.44pp, the gap being reinvestment (600036 +17.68% against
+18.12%, 600900 +10.47% against +10.66%, 601088 +4.82% against +5.17%, 002594 +10.75% against +10.71%).
No real split fell inside these windows, so split handling rests on the tests. The live ledger stays at
37 events, 0 linked. No account writes, trades, credentials or cron changes.

Review evidence for 0.1.38 and this fix:
`~/.local/share/a-share-research-evaluations/knowledge-ledger-20261105/code-review-skills.md`. Its gap on
migration validation is confirmed: 0.1.38 was a migration, and the full local `check.sh` that
`docs/development.md` asks for before committing one was not run, because the host's resource rule forbids
undifferentiated full test runs. Targeted tests and hosted CI ran instead; that is not the same check.

## 0.1.38 activation (2026-11-05)

Owner instruction (Telegram msg 4205, 2026-11-05: add a report field to `holding_events`) activated
`0.1.38-a2f5c75db5a5` for `claude`, `codex`, `hermes` and shared `~/.agents/skills/`, `--dry-run` then
`--force`. Rollback manifest: `~/.local/share/a-stock-agent/rollback-1793882120911620640.json`;
`0.1.37-1468abb5c873` remains installed. Change: `holding_events.report_id` (migration 037, additive and
nullable, no backfill), `--report-id` on `add-holding` / `buy-holding` / `sell-holding`, and read-only
`report-trades`. Schema: authorized by that instruction; backup
`~/.local/share/a-stock-agent/backup-pre-0.1.38-*.db` taken with the Online Backup API, integrity ok.
After migration the live ledger has 37 events (0 linked) and 10 holdings, unchanged, integrity ok.
Validation: targeted tests 511 passed, installer and Skill gates 11 passed / 2 skipped, Ruff, hosted CI
success on `a2f5c75`. `report-trades` ran with real TuShare data on a copy of the backup with three
linked trades; the index changes match the raw closes. No account writes, trades, credentials or cron
changes. Pointer rollback stays compatible because every insert names its columns; the column remains.
No linked trade exists yet. Program checks do not confirm that a report belongs to the traded code.

## 0.1.37 activation (2026-11-04)

Owner instruction (Claude Code session, 2026-11-04: evidence waits are reference only, not a necessary
condition; Codex given full permissions for the plan) activated `0.1.37-1468abb5c873` for `claude`,
`codex`, `hermes` and shared `~/.agents/skills/`, `--dry-run` then `--force`. Rollback manifest:
`~/.local/share/a-stock-agent/rollback-1793776286779678880.json`; `0.1.36-34ca42410a3a` remains
installed. Change: see `docs/specs/2026-11-04-reference-evidence-spec.md` (Research contract
a-share-research b74713c). Validation: targeted tests 249 passed / 2 skipped and Ruff (Codex), read-only
Codex review found one P2 (rounded checkpoint threshold), fixed in 1468abb with a mutation-checked test.
One real read-only `monitor-snapshot` after activation: 300750 and 002946 (legacy 等证据) produce
`research_opportunity` capped at the first tranche with the checkpoint marked reference; 002648 and
601600 unchanged; 688578 still excluded by `untradable_boards`. No account writes, trades, migrations,
credentials or cron changes.

## 0.1.36 activation (2026-11-04)

Owner instruction (Claude Code session, 2026-11-04: the broker account cannot trade STAR; keep it
in research, exclude it from advice) activated `0.1.36-34ca42410a3a` for `claude`, `codex`, `hermes`
and shared `~/.agents/skills/`, `--dry-run` then `--force`. Rollback manifest:
`~/.local/share/a-stock-agent/rollback-1793772038958616040.json`; `0.1.35-8e2ef583632c` remains
installed. Change: see `docs/specs/2026-11-04-untradable-boards-spec.md`. On the same instruction the
owner's `risk-policy.json` gained only `"untradable_boards": ["STAR"]` (mode 0600 kept, no other key
or value changed); remove that key once STAR trading is enabled. Validation: `scripts/check.sh`
passed (1672 passed / 11 skipped) before the Codex finding fix, then targeted monitor/position/policy
tests (470 passed) and Ruff. One real read-only `monitor-snapshot` (no account scope, as the Hermes
scan runs): before the policy key, 688578 (Research report 85, 现在分批, v2 support) produced a
`research_opportunity`; after it, 688578 stays a researched candidate, is named in `research.reason`
and produces no prompt; ChiNext 300750 `opportunity_cost` unchanged. No account writes, trades,
migrations, credentials or cron changes.

## 0.1.35 activation (2026-11-04)

Owner-authorized (Claude Code session, 2026-11-04) activation of `0.1.35-8e2ef583632c` for `claude`,
`codex`, `hermes` and shared `~/.agents/skills/`, `--dry-run` then `--force` through the standard
installer. Rollback manifest:
`~/.local/share/a-stock-agent/rollback-1793770242662242160.json`; the previous runtime
`0.1.34-4a2622904d48` remains installed. Change: see
`docs/specs/2026-11-04-proactive-decision-spec.md`; stop tiers, L3, P0–P3, W1, risk-policy values
and monitor-v1 `schema_version` unchanged; Lib unchanged. Validation:
`scripts/check.sh` passed (1661 passed / 11 skipped, Ruff, regulatory freshness, standalone QA,
cron fixture); read-only Codex review, 6 findings fixed. Independent cwd checks confirmed the CLI
links (`a-stock-cache`, `a-stock-fetch`, `a-stock-install`) and all client links. One real
account `monitor-snapshot` (no `--portfolio-value`, read-only) after activation: runtime
`0.1.35`, Research `ok` (5 candidates, 3 holdings); every production card predates Research
`f65904e` (stance and v2 shipped 2026-11-04), so the stance fields are null and no
`research_opportunity` fired, as specified for old cards. `position-size` on that snapshot failed
closed for the missing confirmed denominator. No account writes, trades, migrations,
credentials or cron changes.

## 0.1.34 activation (2026-11-03)

Owner-authorized (Telegram msg 4137) activation of `0.1.34-4a2622904d48` for `claude`, `codex`,
`hermes` and shared `~/.agents/skills/`, `--dry-run` then `--force` through the standard
installer. Rollback manifest:
`~/.local/share/a-stock-agent/rollback-1793719394930016960.json`; the previous runtime
`0.1.33-5add5f365ee7` remains installed. Change: dividend-sensitivity near misses state both
net advantages in `research.reason`; threshold, basis, prompts, account gates and monitor-v1
schema unchanged; Lib 0.10.0 unchanged. Validation: `scripts/check.sh` passed (1639 passed /
11 skipped, Ruff, regulatory freshness, standalone QA, cron fixture). Independent cwd checks
confirmed all three CLI links, client links and installed Skills 0.1.34 / Lib 0.10.0. One
real account `monitor-snapshot` (no `--portfolio-value`, read-only) after activation: Research
`ok`, `review_candidate`, opportunity comparisons identical to the pre-activation snapshot
(300750 vs 000963/002050/603606: 8.24/14.38/5.15 pp), no near miss present in the current
account. No account writes, trades, migrations, credentials or cron changes.

## 0.1.33 activation (2026-11-03)

Owner-authorized activation of `0.1.33-5add5f365ee7` for `claude`, `codex`, `hermes`
and shared `~/.agents/skills/`, `--dry-run` then `--force` through the standard
installer. Rollback manifest:
`~/.local/share/a-stock-agent/rollback-1793697712640680680.json`.
Only the dependency lock changed: a-stock-lib 0.10.0 (`bd55597`), wheel SHA256
`e69dd873a57b5bc38f989650dad751e319554fd90190a07b0135854431164470`. Lib 0.10.0
changes `framework_rule_hash` values (scoring semantics unchanged; rule hashes are
recorded, not compared), makes `fetched_at` carry `+08:00`, and lets
`detect_split_ratio` accept an explicit `as_of` and native TuShare columns; the
runtime keeps its existing AKShare-column adapter. Validation: full suite 1641
passed / 9 skipped including version and release-install gates; Ruff, regulatory
freshness, standalone QA and cron fixture passed. Independent cwd checks confirmed
active CLI targets, all client links, installed Skills 0.1.33 / Lib 0.10.0 and the
recorded wheel hash. Pairs with Research `b8d4e54` deployed in the same session.
No account commands, migrations, credentials or cron changes.

## 0.1.32 activation (2026-11-03)

Owner-authorized activation of `0.1.32-729d470ee38e` for `claude`, `codex`, `hermes`
and shared `~/.agents/skills/`, following `--dry-run` then `--force` through the
standard installer. Rollback manifest:
`~/.local/share/a-stock-agent/rollback-1793684625927950080.json`.
Independent cwd checks confirmed active CLI targets, all client links, installed
Skills 0.1.32 / Lib 0.9.0 in site-packages and the locked release wheel hash.
Pairs with Research `cb569ad` deployed in the same session. Existing verification
below was reused; no account commands, migrations, credentials or cron changes.

### Source validation

Locks a-stock-lib 0.9.0 (`b278e7b`), wheel SHA256
`4c470038479856767cd686b0c71abe160b8cc5b39dec65fc9d8d2e68ccaf74a9`.
Benchmark index/stock prices now use the library contract above. Candidate installer
used an isolated target root and explicit wheel override; normal frozen sync and
release installation were then verified against the published artifact. Independent
cwd checks confirmed version, site-packages import and byte-for-byte wheel contents.
Validation after rebasing the disjoint dividend-sensitivity work from `1172e2d`:
1641 passed / 9 historical-behavior skips in the full suite, including version and
release-install gates; Ruff, regulatory freshness, standalone QA and cron fixture
checks passed. Real TuShare checks returned both total-return indices through
2026-10-30 and an explicitly degraded 600900 weekend close (2 days old).
The source-validation phase did not alter active clients or production. The separately
authorized activation above supersedes the historical 0.1.31 activation below.

## 0.1.31 activation (2026-11-03)

Release `0.1.31` (`0892de4`, research rows project Research `current.valuation.assumption`; opportunity
prompts append it once as “Research 注”) was pushed to `master` and activated as `0.1.31-0892de4519ec` for
`claude`, `codex`, `hermes` and shared `~/.agents/skills/`; owner request in the CLI session of 2026-11-03.
`--dry-run` first, then `--force`. Rollback manifest
`~/.local/share/a-stock-agent/rollback-1793665792341729320.json`; no schema change. Pairs with Research
`c2d212f`. Full matrix 1,631 passed (11 skipped), `scripts/check.sh` passed; mutation: dropping the
prompt caveat fails the digest test. Live snapshot: 7 rows with rolled returns carry the caveat, the two
not-priced candidates keep `note` and a null `assumption`; the 300750 `opportunity_cost` prompt ends with it.

## 0.1.30 activation (2026-11-02)

Release `0.1.30` (`b6b302c`, opportunity-cost prompts merged per candidate with 7-day freshness, spec
`docs/specs/2026-11-02-opportunity-cost-digest-spec.md`) was pushed to `master` and activated as
`0.1.30-b6b302ca8d69` for `claude`, `codex`, `hermes` and shared `~/.agents/skills/`; owner authorization
Telegram msg 4089. `--dry-run` first, then `--force`. Rollback manifest
`~/.local/share/a-stock-agent/rollback-1793626260241571720.json`; no schema change. Full matrix 1,629
passed (11 skipped), `scripts/check.sh` passed; mutation: dropping the Shanghai conversion in `_fresh`
fails both UTC timestamp cases. Live snapshot (no `--portfolio-value`, `data_status=partial`):
`research.opportunity_costs` keeps 4 comparisons, `review_prompts` now carries one `opportunity_cost`
for 300750 naming all four holdings instead of four separate prompts.

## 0.1.29 activation (2026-11-02)

Release `0.1.29` (`094735e`, Research card reading and review prompts, spec
`docs/specs/2026-11-01-research-card-review-prompts-spec.md`) was activated as
`0.1.29-094735ed3091` for `claude`, `codex`, `hermes` and shared `~/.agents/skills/` after Research
`d15af17` (which serves `GET /api/cards`) went live; owner authorization Telegram msg 4058. `--dry-run`
first, then `--force` to replace the existing same-target symlinks. Rollback manifest
`~/.local/share/a-stock-agent/rollback-1793612399620548720.json`; no schema change. `scripts/check.sh`
passed on 2026-11-01. Live snapshot: `research.status=ok`, 4 holdings and 5 L5 candidates read, no
`missing`; 600900 card `待复核` produced `research_thesis_review` (`review_required`,
`review_candidate`); no `review_prompts` yet because existing reports predate valuation (`note`
reports it). Follow-up research with valuation queued for all nine codes.

## 0.1.28 activation (2026-10-30)

Release `0.1.28` (`048fc45`) was committed and pushed to `master` and activated as
`0.1.28-048fc4532cbc` for `claude`, `codex`, `hermes` and shared `~/.agents/skills/`; rollback
manifest `~/.local/share/a-stock-agent/rollback-1793373971278693640.json`, database backup
`backups/backup-pre-0.1.28-20261030-232608.db` (no schema change). Full matrix 1,569 passed
(11 skipped); mutation check: restoring `watch` as unresolved fails the new test. Live check with
the confirmed account inputs: `data_status=complete`, `review_candidate`, 603606 reported as
`l3_watch` instead of `l3_candidate`. No account state or investment rules were changed.

## 0.1.27 activation (2026-10-30)

Release `0.1.27` (`1e3fad8`) was committed and pushed to `master`. The installer activated
release `0.1.27-1e3fad8bf995` across stable CLI commands and client Skill discovery links
(`claude`, `codex`, `hermes`, shared `~/.agents/skills/`); rollback manifest
`~/.local/share/a-stock-agent/rollback-1793368147753282680.json`. Full matrix: 1,550+ tests
passed (11 skipped), Ruff, regulatory freshness, standalone QA and cron smoke passed; two agy
review rounds, the second clean. Migration `036-l3-evidence-cadence` (additive column, all 34
rows `unspecified`) was first applied by a live `uv run a-stock-fetch quarter` check from the
source tree before the backup, so `backup-pre-0.1.27-20261030-214847.db` already contains the
column; 0.1.26 reads it unchanged. Live checks: `monitor-snapshot --json` without
`--portfolio-value`/`--account-scope` now returns the holdings layer with
`risk_policy.status=not_applied_account_scope_required`, `action_status=review_candidate`;
`a-stock-fetch quarter` for 603606/600900/000963 matched the 2026Q3 filings. Paired Research
server: `08e7e89`. No account state or investment rules were changed.

## 0.1.26 activation (2026-10-29)

Release `0.1.26` (`e838b7f`) was committed and pushed to `master`. The installer activated
release `0.1.26-e838b7f6484f` across stable CLI commands (`~/.local/bin/a-stock-*`) and
client Skill discovery links (`claude`, `codex`, `hermes`, and shared `~/.agents/skills/`).
Rollback manifest recorded at `~/.local/share/a-stock-agent/rollback-1793249965536683360.json`.
All 1,483 tests passed (11 skipped), Ruff passed, standalone QA passed. Paired live
verification: `a-stock-cache research budget` succeeded against the newly deployed
Research production service (`stock.keyi.win`). No credentials, account state,
or investment rules were changed.

## Historical deployment evidence

Superseded deployment and preflight records are retained in Git, not as current
operating instructions. Read older deployment ledgers from their source snapshots:

```bash
git show d14d6ff:docs/operations.md  # 0.1.23/0.1.24 candidate validation before activation
git show 0d7c0a5:docs/operations.md  # 2026-10-08 to 10-22 step records
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
