# S2 / S3 implementation ledger — 2026-09-17

Governing spec: [risk closure v1.1](../specs/2026-09-17-a-stock-risk-closure-and-performance-validation-spec-v1.1.md).
The initial S2/S3 request authorized repository implementation only. Later Agent
runtime/client deployment, migration 035 and later Tracker S2 code deployment received
separate explicit authorization (see below). No investment parameter change,
personal policy adoption, experiment registration, other schema change, cron edit
or trading action is authorized here.

## Baseline and delivery boundaries

- Agent implementation starts from `125e3a0e86ad68f3965844960ba2cd5e9ceab4db` on
  isolated master, not the active Skill checkout (`2000d750ca66b4c31e503c6c7656fbbf9a6095ea`).
- Tracker starts from `69f11c99d1720f2dad07113b46f17f5d87a3975d` on an isolated
  master clone. Lib source remains `6dc856ea1183fe6f6c8ff9f5201b0c920b5008ec`,
  unchanged: that master identifies the unreleased 0.8.1 maintenance source, while
  both production consumers intentionally use the immutable published 0.8.0 wheel.
- Remote HEADs and clean starting worktrees were checked, not copied from the spec.
- Bounded Wiki search in concepts/operations/queries for `账户业绩`, `风险政策`,
  `收益验证`, `并列分数`, `performance-report`, `experiment.manifest`,
  `a-stock-tracker` found no applicable page. Local spec/source govern; no Wiki edits.

## 2026-09-18 deployment update

Agent S1/S3 `4789fc9` (0.1.13 / lib 0.8.0) is **DEPLOYED** as of 09:36 CST.
After the earlier rollback, the user separately authorized migration 035. A verified
SQLite backup preceded the single transaction adding nullable `decision_json` and
its ledger entry. All original rows/columns and old ledger records remained intact;
no historical structured decisions were fabricated. The paired CLI/Skill pointer
was switched and Hermes gateway restarted. Current-Skill budget replays passed
in native Hermes/Codex, including Hermes's configured default model. Claude's
explicit authentication/verification waiver remains recorded, not a pass. Only
schema/data-integrity checks accessed production financial state; no personal policy,
real-account performance or live notification test was performed.
Tracker S2 `7516535` / lib 0.8.0 was deployed at 13:17 CST. Its manifest remains
pending and the read-only report smoke correctly returned
`MANIFEST_PENDING / INSUFFICIENT_EVIDENCE`. See the
[current deployment record](../operations.md#current-deployment-record) for exact
provenance, first-attempt rollback, final activation and rollback limits. The
implementation checkpoints below retain their original test counts and scope.
The Agent `ACTIVE_RELEASE.json` remains an immutable 09:36 CST runtime/Skill
snapshot; its then-correct `tracker: NOT_DEPLOYED` value is not the later independent
Tracker deployment record and must not be retroactively rewritten.

## S2 — default manifest location approved

On 2026-09-17 the user explicitly approved `config/experiment_manifest.json`
and requested implementation to continue. This follows Tracker `AGENTS.md` and
`docs/architecture.md`; spec §7.1 now records the dated location correction.
The prior **BLOCKED_DOCUMENT_CONFLICT** is resolved. This does not authorize
production activation, verified production hash/date registration, schema or cron
changes. Existing project path ownership must make loading independent of cwd.

The evaluation engine and explicit synthetic manifest injection can proceed
independently. This does not authorize production activation, declaring a real
scoring hash/date verified, or claiming `2026-09-17.e2` acceptance before the
full snapshot/selection/weight/path rules are validated. No new universe,
scoring weights, 44-point threshold, historical rows, schema or cron may change.

S2 current software status: **DEPLOYED / PRODUCTION_EVIDENCE_PENDING**.
The implementation commit is `41c95d311c0330c8340841e115a539b10d72abe3`;
the deployed Tracker master is the documentation/equivalent-cleanup successor
`7516535893d94fcf4b424ce3356aa3f75274d58b`. Initial 277-test drafts were rejected
for real implementation defects; the historical handoff
`/tmp/a-stock-s2-final-parent-review.md` is superseded by this final evidence.

- Default `config/experiment_manifest.json` is loaded through the existing paths
  owner, independent of cwd. It stays **pending** with empty scoring hashes and
  null unverified dates/evidence. Known expected=35 is shown; unmeasured DB counts
  are null. Pending diagnostics do not read the database.
- The fixed universe was parsed from Tracker commit `69f11c99…` rather than today's
  watchlist: config SHA-256 `87ac0e4972aa1562ed49b034dfd94172fa1f86b77ab181f9323aabd4b27e3a11`,
  universe SHA-256 `cdba80037cdefe10be6eeb4b4e9c4f603b1fd271fd295229ee796162c7d56cfb`.
  Source config, hash-covered scoring/input files, weights and requirements are
  byte-identical to that base. No actual production scoring hash is inferred.
- `evaluation.py` separates immutable snapshot qualification, fixed tie weights,
  fixed schedules and future outcome checks. No mutable qualitative-cache lookup,
  historical re-scoring, member substitution or outcome-driven batch selection.
  Strict numeric/source/component/JSON validation preserves supported null PB and
  honest fallback evidence; unrelated bad prices remain separate diagnostics.
- As-of is independent of enrollment end. Entry and target dates align backwards
  using explicitly evidenced calendars and the original 10-day lag. All basket
  endpoints and daily paths use the same dates/weights. No live calendar interface
  was invented; absent/malformed evidence fails closed.
- Scheduling keeps young batches, but metrics consume only fixed batches whose
  natural-day window is due. Young rows remain diagnostic without blocking existing
  mature 3/2/1 evidence. Due but damaged/unresolved batches are never skipped.
  Date-mature counts and time-due counts are distinguished. Path/batch gaps prevent
  full-chain claims; per-batch endpoints remain explicitly diagnostic. All-tied
  complete evidence routes to manual review, never fabricated zero alpha.
- Three windows share one read transaction; the original automatic report call
  remains compatible. No schema, cron, CLI scoring flow, thresholds or writer
  changes. `2026-09-17.e2` identifies the implemented software protocol, not live
  data qualification, executable returns or investment effectiveness.

Evidence: `tests/test_accuracy_report.py` covers T01–T20 plus parental review
counterexamples; `tests/test_pipeline.py` checks default pending auto-reporting.
Final parent validation in isolated Python 3.13.5 / declared lib 0.8.0:
**299 tests passed**, **11 structure tests passed**, Ruff check/format, mypy
(49 source files) and diff check passed. Log:
`/tmp/a-stock-s2-parent-final-check.log`.

Independent read-only Codex review requested two final changes (young batches
blocking mature evidence; malformed datetime calendar errors). Nine regressions
and the fixes passed a bounded followup: **PASS**, **53 focused tests**, mypy;
the e2 software identifier was accepted in that scope. Reports:
`/tmp/a-stock-s2-landing-review.txt`, `/tmp/a-stock-s2-fixes-review.txt`.
These do not qualify real clients or production.

External candidate archive/provenance manifest:
`/tmp/a-stock-s2-release-41c95d3/` (historical pre-deployment candidate). Active
Tracker contains S2 source `7516535…` plus deployment-status documentation; its
production checkout and remote master are synchronized. The original
Agent checkout stays at `2000d750…` but is no longer the Skill discovery target
after the 2026-09-18 cutover. Lib source remains unchanged at `6dc856ea…`. The isolated
Tracker clone initially had a local active-checkout origin; Git refused that push.
The active branch was verified unchanged; only the clone's origin was corrected
to GitHub. No receive protection was weakened.

Remaining qualification requirements: separately authorized real hash/date/evidence
registration, independently verified local calendar/data coverage and mature samples.
No S4 work or investment-validity claim is included.

## S3a — POLICY-01

Status: **IMPLEMENTED_WITH_FIXTURES / RUNTIME_DEPLOYED_AFTER_AUTHORIZED_035**.
No real personal policy was created or adopted.

- One `risk_policy.py` resolves an effective `RiskParameters` object outside both
  handlers. CLI numeric values override a valid selected file, which overrides
  compatibility defaults. A found/missing-explicit invalid file fails closed,
  including when numeric overrides are provided. No policy file is written.
- Path selection is dynamic: CLI, environment, runtime.env, then the policy JSON
  beside the selected config file. `paths.read_private_config` shares regular-file,
  owner and permission checks with the existing dotenv reader; JSON parsing is
  separate. An invalid runtime config is a controlled CLI failure.
- Strict schema=integer 1; CNY, nonempty policy/account/confirmation identities,
  timezone-aware confirmation/effectivity, matching explicitly supplied account,
  and finite `0 < limit <= 100` are checked. Bool pseudo-numbers, duplicate JSON
  keys and nonfinite values are rejected. Optional drawdown observation target
  is not defaulted or described as a guarantee.
- Both risk CLI option tables expose policy file, account scope, asset valuation
  as-of and numeric overrides. JSON/text show effective field sources and true
  denominator scope. Unknown scope/as-of is explicit and freezes new-risk
  authorization; report collection time is never substituted. No automatic TTL.
- S1 clean/review semantics for existing holdings and W1 fact-recording gates
  remain unchanged. Policy/confirmation metadata grants no write permission.

Evidence: `tests/test_risk_policy.py` maps P13/P22 to source precedence,
owner/permission/missing-file failures, schema/time/scope cases, invalid-file plus
CLI override, no file creation, identical public CLI inputs, and honest denominator
provenance. No fixture represents a real account or a personally adopted threshold.

Validation environment: Python 3.13.5, frozen lib 0.8.0 wheel, isolated HOME/XDG,
no inherited market credentials, `A_STOCK_NOTIFY_MODE=disabled`.

- Focused policy/path checks: **71 passed**, exit 0.
- Broader policy + S1 + holdings checks before the final config-error additions:
  **471 passed**, exit 0.
- Full check before those two config-error tests: **1249 passed, 2 skipped**,
  exit 0; Ruff, Skill validator, regulatory freshness, standalone QA and cron
  fixture passed. The two skips are optional sibling-source installation checks.
- Independent read-only real Codex CLI review returned PASS for §8.1/P13/P22;
  it inspected code but did not independently run tests. Report is external:
  `/tmp/a-stock-s3a-review.txt`. This is not real-client qualification.

Final `bash scripts/check.sh` for this S3a source: **1251 passed, 2 skipped**,
exit 0, with all additional gates above passing. Full log remains external at
`/tmp/a-stock-s3a-check.log`; `git diff --check` passed. No production state,
real personal policy or active Skill entry was modified.

## S3b — file-only performance MVP

Status: **IMPLEMENTED_WITH_SYNTHETIC_FIXTURES / RUNTIME_DEPLOYED_AFTER_AUTHORIZED_035**. This is not full
broker reconciliation or live-client acceptance.

One `performance.py` owns strict parsing, Decimal calculation and rendering.
The command is registered throughout the existing CLI with a local file-only
bypass before DB-path selection/logging. File-only mode never opens a DB; both
modes avoid network, bootstrap, notifications and output-file writes. Only an
explicit ledger-check flag permits reading the existing database. Defaults
produce text; JSON is a single stable object. Argument/schema errors are exit 2,
business gaps 4, runtime/I/O failures 1. No new service/dependency/schema is added.

`tests/test_performance.py` and CLI tests exercise:

- P01/P02/P14/P15: gross flows, Decimal return math, no net-zero timing bypass;
  assumptions require a flag and remain estimated even with provisional sources.
- P03/P04/P05/P06: broker-net dividends/fees/taxes counted once, corporate actions
  not recomputed from QFQ/positions, unsupported flow timing unavailable, no history
  fabricated before the sourced baseline.
- P07/P08/P16/P17/P18: normalized drawdown, withdrawal versus full loss, zero-asset
  restart, missing/unknown calendars and separate segments without gap bridging.
- P09: absent benchmark allowed; malformed/null/currency/date/effectivity gaps
  retain absolute returns. Effectivity is checked per segment so later eligible
  segments remain comparable. Price/total-return reference type is disclosed;
  tradability is a separate unperformed assessment, not a claim of execution.
- P10/P11/P19: byte-deterministic repeated file calls, unchanged inputs, strict
  amounts/identity/timezones/duplicate JSON keys/duplicate Shanghai dates and
  controlled malformed-input failures. All unavailable metrics have null reasons.
- P12/P21: missing DB and even a forbidden DB-path resolver do not affect file-only
  dispatch; global help/options/classification/text/JSON and exit codes are tested.
- P20 **limited diagnostic only**: missing DB/schema, inferred history and declared
  source conflict remain unavailable/provisional with exit 4. Literal filenames
  cannot override the read-only SQLite URI. Connection uses one transaction and
  closes on every path. No authoritative account mapping is available, so counts
  are explicitly `not_reconciled`; a true account-to-ledger conflict reconciliation
  has **not** been implemented/qualified and is not inferred from these tests.

Parent added counterexamples after worker review: null/empty benchmark handling,
read-only URI escaping, row identity conflicts, one-point unavailable returns,
approximation plus provisional-source disclosure, null reasons, and per-segment
benchmark effectivity. The initial independent read-only review requested changes
for effectivity and ambiguous benchmark execution wording; both were fixed with
regressions. Independent read-only Codex followup returned **PASS for those
bounded fixes**, with **74 focused tests passed**, Ruff and diff checks passed;
report: `/tmp/a-stock-s3b-review-followup.txt`. This is not full P20, real-client
or production acceptance.

Final combined `scripts/check.sh`: **1310 passed, 2 skipped**, exit 0; Ruff, Skill
validation, regulatory freshness, standalone QA and disabled-notification cron
fixture all pass. Log: `/tmp/a-stock-s3-final-check.log`. The skips remain the
optional sibling-source installation scenarios. Generated artifacts and raw inputs
remain outside Git; no S3b result writes to decision-v1/monitor-v1 or holdings.

Agent runtime/Skill production identity is deployed and read back; Hermes/Codex
have only the bounded current-release budget replays recorded above, while Claude
remains deployed under the explicit verification waiver. Tracker checkout/lib
identity is deployed, but its scoring registration, calendar, mature samples and
investment result remain unverified. Real-account performance and complete ledger
reconciliation are also NOT_VERIFIED. S4 remains deferred. Rollback is a normal
revert of the bounded release commits; retain facts and personal files. Never
silently return to compatibility defaults while claiming a newer personal policy
is still active.
