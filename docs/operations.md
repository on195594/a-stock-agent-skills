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
a-stock-fetch check <代码>
```

`holdings` and `portfolio-risk` are read-only views; `dividend-check` and
`benchmark-report` read TuShare but write nothing. `check-holdings` is an
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
it is not configured.

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

## Research integration validation before activation (2026-10-23)

Runtime 0.1.23 adds `a-stock-cache research` and on-demand Research/Monitor routing.
The candidate was developed separately because current client Skill links resolve
into the canonical source tree; copying candidate Skill text there would activate
it immediately. No active entries, runtime.env, account database, cron, investment
policy or provider/model settings were changed by this candidate validation.

The candidate CLI used the real Research service to read reports 9/11 and submit
run 17 with parent report 9. The follow-up passed in 103 seconds; repeating the
same request ID returned run 17. The explicitly selected nonexistent account
DB remained absent. Candidate Research feedback and method revisions were also
submitted through this CLI to an isolated real Web/worker instance.

The full automated run passed 1,439 tests and found two release-contract omissions
(version assertion and CLI argument registry). Both were fixed; 83 affected tests
passed on rerun. Ruff, Skill validation, regulatory freshness, standalone QA and
isolated cron smoke passed. Eleven optional capture/source-dependent cases skipped.
No new multi-host model capture or real-account action was performed.

This section records candidate evidence. The separately authorized paired
activation and production acceptance are recorded below.

## Long-lived Research credential validation before activation (2026-10-27)

This validation was performed in an isolated checkout before the separately
authorized activation recorded below. Research uses a named, revocable API key
stored separately from browser sessions.
The client keeps `A_STOCK_RESEARCH_TOKEN` and `research-v1`; HTTP 401 explicitly
requires a credential update before retrying with the original request ID.
Use the selected mode-0600 `runtime.env`, and remove stale environment overrides.
Rotate by creating a new key, verifying report access with it, then revoking the
old key through the Research owner's local CLI. Do not put keys in prompts or logs.

An isolated real Web/worker run verified credential rotation during submission,
both revocation paths, CLI 401, service restart, and reading the passed report for
a new Maotai research task. The installed 0.1.23 CLI also read a report using the
new key. No account database was created. Candidate CLI checks (18), Research and
Monitor tests (1,018), Ruff and Skill validation passed. Private configuration
and active links were untouched during that candidate stage.

## Current deployment record

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

**Not yet observed.** First Telegram deliveries of `daily-brief` (2026-10-22 15:35),
a real `stop-alert` crossing, and `benchmark-report` (2026-11-01); fresh Hermes
behaviour under the slimmed router.

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
passed after its existing review prerequisite was clarified. These partial
captures are not a final eight-case or multi-client behavior pass. No additional
paid evaluation or real-account flow was run during activation.

Hermes currently selects `openai-codex/gpt-6.1-sol-900k`; configuration was not
changed. Existing client sessions may cache old Skill text: reload Skills or
start a new session (Pi supports `/reload`). Installation and discovery checks
do not prove a running conversation has refreshed its context.

## Historical deployment evidence

Superseded deployment and preflight records are retained in Git, not as current
operating instructions. Read older deployment ledgers from their source snapshots:

```bash
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
