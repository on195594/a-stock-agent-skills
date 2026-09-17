# Risk closure implementation ledger — 2026-09-17

Governing specification: [v1.1](../specs/2026-09-17-a-stock-risk-closure-and-performance-validation-spec-v1.1.md).
The user's subsequent implementation request authorizes repository work; it does
not authorize deployment, production configuration or investment parameter changes.

## Status and baseline

- S0: repository HEAD/worktree checks complete; production NOT_VERIFIED.
- S1: PARTIALLY_IMPLEMENTED_NOT_DEPLOYED (RISK-04 and RISK-05 only).
- S2, S3a, S3b: not started. S4: DEFERRED / CONDITIONAL.
- Agent initial local and remote master: `2000d750ca66b4c31e503c6c7656fbbf9a6095ea`.
- Tracker unchanged local and remote master: `69f11c99d1720f2dad07113b46f17f5d87a3975d`.
- Lib unchanged local and remote master: `6dc856ea1183fe6f6c8ff9f5201b0c920b5008ec`.
- All three worktrees were clean. Remote references were checked with
  `git ls-remote origin refs/heads/master`, not inferred from the spec.
- Agent lock and installed test environment: Python 3.13.5, Agent 0.1.13,
  lib 0.8.0 immutable release wheel; no dependency change.
- Active `.agents/skills` and `.claude/skills` symlinks point at the original
  Agent checkout. Development therefore uses a separate master clone at
  `/tmp/a-stock-risk-closure-20260917`. Do not fast-forward the active checkout
  as a substitute for separately authorized deployment.
- The approved ecosystem charter is absent from `docs/architecture/`; no
  replacement approval text was invented. Other production/client consumers,
  installed runtime identity and Tracker production evidence remain unverified.
- Bounded Wiki search in concepts/operations/queries for `风险闭环`,
  `risk.closure`, `a-stock-agent-skills`, `三仓总纲` found no directly applicable
  page. Conclusions here come from local source and live Git/link inspection,
  not Wiki authority. No Wiki files changed.

## First delivery

- RISK-04 / A12: validate null/string type before allowed stop-reason value;
  list, object, bool, integer, float and unknown string fail with
  `MonitorContractError` through object and JSON entrypoints.
- RISK-05 / A19: begin one deferred transaction before local SELECTs. A
  two-connection synthetic WAL fixture commits holdings and alert changes
  between reads; the reader retains old holdings and old alerts.
- RISK-05 / A20: use SQLite's native connection context manager to end the
  read transaction on success or exception, and the existing session manager
  to close the connection. Reuse an existing transaction without nested BEGIN.
  Tests assert COMMIT/ROLLBACK, released transaction and closed connection.
- Existing quote-batch test proves the read session is closed before quote
  fetching. Trace/authorizer checks cover read SQL and prohibit application DML.
  WAL sidecars are fixture-only; no physical-zero-write claim is made.
- No changes to enum vocabulary, Skill routing, financial formula, thresholds,
  schema, notification implementation or W1 authorization.

## Verification

All commands ran in the isolated clone with an empty inherited environment,
explicit PATH, isolated HOME `/tmp/a-stock-risk-validation-home` and
`A_STOCK_NOTIFY_MODE=disabled`. uv used the existing dependency cache.

| Command | Exit | Result |
|---|---:|---|
| `uv sync --frozen` | 0 | Python 3.13 environment; dependencies installed, Ruff downloaded |
| `.venv/bin/python -m pytest -q tests/test_monitor_contract.py tests/monitor/test_monitor_snapshot.py` | 0 | 151 passed |
| `bash scripts/check.sh` | 0 | 1061 passed, 2 skipped; Ruff, Skill validation, regulatory freshness, standalone QA and cron fixture passed |
| `.venv/bin/python -m pytest -q -rs` | 0 | 1061 passed, 2 skipped |
| `git diff --check` | 0 | no whitespace errors |

The two skips are optional source-override installation tests in
`tests/test_installation.py` (A_STOCK_LIB_SOURCE intentionally unset), not
missing installed lib dependencies. Full-check log is outside the repository:
`/tmp/a-stock-risk-check-20260917.log`. The permissions-error line in the cron
fixture is an expected negative test; the script returned success.

The tested source changes are in the commit containing this ledger. Historical
model captures and hashes were not edited. No new real-model capture or
independent external-agent review was run. Dependency installation and Git
remote inspection used network; these are not fully offline execution claims.
No production database/account data was accessed; no production schema, cron,
client entry, W1 fact or real notification was changed.

## Remaining work and rollback

Next: RISK-01/02/03 budget escalation, shared input validation, contract
invariants, coordinated Skill extension and text risk output. A01–A11,
A13–A18 and A21–A22 are not claimed as new-spec acceptance; existing historical
checks do not establish the new budget semantics. A14's broader new-delivery
side-effect coverage still belongs to that work. S1 is not complete.

S0 still requires remaining client inventory and authorized production evidence;
S2 requires Tracker-specific source/spec analysis; S3 requires its own bounded
implementation. No real investment or account-performance result is claimed.

Rollback is `git revert` of this delivery commit in a non-active master
checkout. No data migration or account-file cleanup is needed. These two
repairs alone introduce no new monitor enum compatibility set; do not label
this commit as delivery of the later coordinated budget extension.
