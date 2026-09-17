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

## S2 — default manifest placement requires a decision

Tracker `AGENTS.md` says tracked configuration belongs in `config/`;
`docs/architecture.md` repeats that requirement. Spec §7.1 names
`a_stock_tracker/reporting/experiment_manifest.json`. No autonomous rule waiver,
AGENTS weakening or silently chosen path is authorized. Default tracked manifest
creation is **BLOCKED_DOCUMENT_CONFLICT** until the user chooses the location.

The evaluation engine and explicit synthetic manifest injection can proceed
independently. This does not authorize production activation, declaring a real
scoring hash/date verified, or claiming `2026-09-17.e2` acceptance before the
full snapshot/selection/weight/path rules are validated. No new universe,
scoring weights, 44-point threshold, historical rows, schema or cron may change.

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

## S3b / next acceptance

Account-performance work is separate from policy parsing; it must not depend on
policy configuration or use real holdings to reconstruct equity. Its acceptance
must cover P01–P12/P14–P21, public file-only dispatch, no-database behavior,
Decimal/flow/zero/restart/gap semantics, optional benchmark, and honestly limited
ledger reconciliation. Generated artifacts and raw accounts remain outside Git.
No S3b acceptance is inferred from S3a test counts.

All current real-client qualifications and production identities remain
NOT_VERIFIED. S4 remains deferred. Rollback is a normal revert of the bounded
release commits; retain facts and personal files. Never silently return to
compatibility defaults while claiming a newer personal policy is still active.
