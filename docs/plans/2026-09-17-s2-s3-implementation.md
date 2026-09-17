# S2 / S3 implementation ledger — 2026-09-17

Governing spec: [risk closure v1.1](../specs/2026-09-17-a-stock-risk-closure-and-performance-validation-spec-v1.1.md).
User explicitly requested starting S2/S3 after S1. This authorizes repository
implementation, not production report enablement, real account inputs/policies,
policy parameter changes, schema, cron, clients, notifications or trading.

## Baseline and delivery boundaries

- Agent implementation starts from `125e3a0e86ad68f3965844960ba2cd5e9ceab4db` on
  isolated master, not the active Skill checkout (`2000d750ca66b4c31e503c6c7656fbbf9a6095ea`).
- Tracker starts from `69f11c99d1720f2dad07113b46f17f5d87a3975d` on an isolated
  master clone. Lib remains `6dc856ea1183fe6f6c8ff9f5201b0c920b5008ec`, unchanged.
- Remote HEADs and clean starting worktrees were checked, not copied from the spec.
- Bounded Wiki search in concepts/operations/queries for `账户业绩`, `风险政策`,
  `收益验证`, `并列分数`, `performance-report`, `experiment.manifest`,
  `a-stock-tracker` found no applicable page. Local spec/source govern; no Wiki edits.

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

S2 draft status after two implementation/review iterations: **NOT_ACCEPTED /
NOT_COMMITTED** in `/tmp/a-stock-tracker-s2-20260917`. Parent validation with
Python 3.13.5 and the declared lib 0.8.0 wheel passed **277 tests** and Ruff,
but mypy reports three errors. Review also found remaining enrollment-vs-as-of,
mutable qualitative-cache/hybrid-source validation, malformed numeric/source and
derived-finiteness issues. These are implementation gaps, not merely a manifest
path decision. `2026-09-17.s2-incomplete` is not e2 acceptance; no T01–T20 or
production claim is made. Detailed handoff remains external at
`/tmp/a-stock-s2-final-parent-review.md`. Tracker and Lib master are unchanged.

## S3a — POLICY-01

Status: **IMPLEMENTED_WITH_FIXTURES_ONLY / NOT_DEPLOYED**.

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

Status: **IMPLEMENTED_WITH_SYNTHETIC_FIXTURES / NOT_DEPLOYED**. This is not full
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

All current real-client qualifications and production identities remain
NOT_VERIFIED. S4 remains deferred. Rollback is a normal revert of the bounded
release commits; retain facts and personal files. Never silently return to
compatibility defaults while claiming a newer personal policy is still active.
