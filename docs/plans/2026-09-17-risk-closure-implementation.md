# Risk closure implementation ledger — 2026-09-17

Governing specification: [v1.1](../specs/2026-09-17-a-stock-risk-closure-and-performance-validation-spec-v1.1.md).
The initial implementation request authorized repository work only. Later runtime
deployment and migration 035 were separately authorized as recorded below; those
authorizations do not permit other schema, configuration or investment changes.

## Current status

S1, S3a and the file-only S3b MVP `4789fc9` (0.1.13 / lib 0.8.0) are **DEPLOYED**
since 2026-09-18 09:36 CST, after the user separately authorized migration 035.
The nullable `decision_json` column and migration entry committed together after
verified backup; original rows/columns and old ledger records were preserved.
Hermes/Codex isolated budget replay evidence applies to this unchanged release;
Claude is deployed under its explicit verification waiver (not a pass). Hermes
gateway is active and cron is unchanged. The earlier schema-gated rollback is
historical, not the current state.
See the [deployment record](../operations.md#current-deployment-record).
S2 is Tracker `3040100` (`2026-09-17.e2`, lib 0.8.0), **DEPLOYED**. The verified
`d312c8995522b563` manifest and sourced local calendar are active for the
2026-09-18 through 2026-11-17 enrollment range. Registration is complete, but the
30/60/90-day windows remain immature and investment evidence is still insufficient.
Real-account performance, full ledger reconciliation and live-channel verification
remain unverified; S4 stays deferred. Current cross-repository
results and remaining gates live in the [S2/S3 ledger](2026-09-17-s2-s3-implementation.md).

The rest of this page preserves **historical S1 checkpoints** and their original
test counts/HEADs; “not started” below is not the current S2/S3 status.

### 2026-09-17 maintenance

Aligned historical/current status wording and removed the private, unreferenced
`commands_admin._latest_analysis_missing_cycle_stage` plus its unused import.
Tracked-source/test/document searches and explicit CLI exports show no caller;
existing checklist regressions remain intact. Full checks: **1310 passed,
2 skipped**, Ruff, Skill validation, freshness, standalone QA and cron fixture
passed. Log: `/tmp/a-stock-agent-cleanup-check.log`. No investment rule changed.
Reproducible caches in the isolated clones may be removed; virtual environments,
editable-install metadata, runtime data, review evidence and versioned release
candidates are retained. This maintenance does not regenerate or re-qualify an
older release candidate, and is not deployment.

## Initial S1 status and baseline

- S0: repository HEAD/worktree checks complete; production NOT_VERIFIED.
- S1: IMPLEMENTED_NOT_DEPLOYED (RISK-01–05; current-client qualification remains NOT_VERIFIED).
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

The first delivery's tested source commit is `10dd9a2da6c963f6c6e11905f270bf3fa507d116`.
Historical model captures and hashes were not edited. No new real-model capture or
independent external-agent review was run. Dependency installation and Git
remote inspection used network; these are not fully offline execution claims.
No production database/account data was accessed; no production schema, cron,
client entry, W1 fact or real notification was changed.

## Remaining work and rollback

The first delivery left RISK-01/02/03 outstanding. The subsequent S1 delivery
below completes the repository implementation and A01–A22 fixture evidence;
it does not complete production or real-client qualification.

S0 still requires remaining client inventory and authorized production evidence.
The S2/S3 implementation work outstanding at this S1 checkpoint is now recorded
in the linked S2/S3 ledger; its remaining production gates are separate. No real
investment or account-performance result is claimed.

The first delivery is `10dd9a2da6c963f6c6e11905f270bf3fa507d116` and introduced
no enum extension. Revert subsequent S1 code only as a complete producer,
validator, CLI and Skill set in a non-active master checkout. No data migration
or account-file cleanup is needed. Restoring the old runtime restores the
known unsafe clean behavior: retain manual budget review / suspend automated
risk suggestions until repaired; rollback is not risk acceptance.

## Remaining S1 delivery — current contract

Starting isolated/local and remote Agent HEAD: `10dd9a2da6c963f6c6e11905f270bf3fa507d116`.
The resulting S1 implementation is `125e3a0e86ad68f3965844960ba2cd5e9ceab4db`;
release commit and package/Skill hashes identify its compatibility set.
Original active checkout remains at `2000d750ca66b4c31e503c6c7656fbbf9a6095ea`.
At this S1 checkpoint, Tracker and lib HEADs listed above were unchanged. The additional Hermes
entries under `.hermes/skills/research` were read-only inspected and also point
at the original active checkout. No external independently upgradeable consumer
was found in repository call sites; uninspected clients remain unverified.

Changes:

- RISK-01: one small `risk_budget.py` shares quote/input checks and budget
  assessment. The original economic formula remains in `calculate_position_risk`.
  Proven position/portfolio breaches produce `risk_budget_exceeded` reviews,
  including when another risk is unknown. Complete totals remain null where
  incomplete; the known lower bound is separate. Actual default/override policy
  metadata is explicit. No personal policy, threshold change or W1 gate added.
- RISK-02: current monitor-v1 consumers require safety evidence, matching active
  counts, valid account numbers and budget/status consistency. Clean holdings
  need usable quote and risk evidence. Budget escalation cannot clear review,
  duplicate a scope/code or manufacture a trade candidate. Existing valid
  trade candidates and blocked-data precedence remain intact.
- RISK-03: text risk uses the same validation, limits and assessment; invalid
  inputs never print normal, incomplete totals remain unknown, and broken
  stops are separate from remaining-distance risk. Database reads cannot
  bootstrap missing schema. Both CLIs register explicit per-name/portfolio
  overrides and show their source; unconfirmed compatibility defaults stay 2/8.
- Skill routes code=null to portfolio-only review of the current snapshot;
  no repeated quotes, full-portfolio research, W1 calls or mental risk completion.
  Proposed new risk is frozen, but confirmed executed facts retain the existing
  concrete-action/global-confirmation recording path.
- Immutable captures and fixture source hashes were not rewritten. The live
  capture test now verifies its historical Skill bytes at its recorded commit,
  rather than incorrectly treating old capture as qualification of today's Skill.
  Synthetic clean/Tier scenarios now use genuinely within-budget denominators;
  original over-budget five-holding inputs explicitly test the new escalations.

### A01–A22 evidence map

Names below are pytest functions. Unless otherwise stated they live in
`tests/monitor/test_risk_closure.py`; they use synthetic state, not real accounts.

| ID | Actual regression evidence |
|---|---|
| A01–A04 | `test_budget_controls_review` (single breach, portfolio-only breach, exact 2/8 boundaries, within-budget clean); `test_budget_does_not_compare_rounded_percentages` |
| A05 | `test_unknown_inputs_never_mean_zero_risk`, `test_text_unknown_risk_never_prints_normal`, `test_text_and_json_share_quote_validation` |
| A06 | `test_invalid_denominator_does_not_clear_even_empty` |
| A07 | `test_text_distinguishes_breach_and_unknown_and_broken_stop`; existing P3 and stop-tier tests |
| A08 | `test_budget_does_not_downgrade_legal_trade_candidate` (reduce and exit) |
| A09 | `test_known_breach_survives_other_unknown_risk`; existing stale/unavailable/conflicted snapshot tests |
| A10 | `test_valid_empty_account_keeps_original_requirements`, `test_text_missing_database_does_not_bootstrap`; existing missing-database JSON test |
| A11 | `test_contract_rejects_over_budget_clean_combinations`, `test_contract_requires_current_safety_evidence`, `test_duplicate_holdings_remain_visible_but_not_known_risk` |
| A12 | `tests/test_monitor_contract.py::test_invalid_stop_reason_raises_contract_error` (object and JSON) |
| A13 | `test_both_public_clis_consume_same_input_and_policy` plus text/JSON invalid-input cases |
| A14 | `test_risk_commands_do_not_write_migrate_or_network`: authorizer, SQL trace, business/schema dump equality, socket and external-command spies; missing-schema test; full cron fixture disables notifications |
| A15 | `test_portfolio_escalation_routes_only_to_existing_reference`: actual portfolio-only escalation matched to the current Skill table and bounded reference; no real model claim |
| A16 | `test_new_old_contract_matrix_without_a_legacy_runtime_switch`: fixed old producer/validator source, current producer/validator, both crossing directions; old unsafe clean explicitly recorded, old rejection not represented as supported compatibility |
| A17 | `test_known_breach_survives_other_unknown_risk`, `test_known_portfolio_lower_bound_can_already_exceed_limit` |
| A18 | `test_confirmed_executed_buy_is_not_blocked_by_budget`: unconfirmed exit 3, confirmed fixture buy recorded, subsequent snapshot still reports breach |
| A19–A20 | `test_monitor_snapshot.py::test_local_snapshot_keeps_one_wal_version`, `test_local_snapshot_releases_transaction_and_connection`, and the one-session/one-quote-batch test |
| A21 | current full suite, `tests/test_agent_tool_e2e.py` recorded-source/Skill hashes, unchanged historical capture files |
| A22 | `test_contract_requires_current_safety_evidence`, `test_clean_contract_rejects_invalid_holding_risk`, `test_clean_contract_requires_usable_quote_evidence`, `test_omitted_stop_reason_cannot_bypass_clean_evidence` |

### Verification and boundaries

In the same isolated environment as the first delivery:

- `bash scripts/check.sh`: exit 0, **1183 passed, 2 skipped**; Ruff, Skill
  validation, regulatory freshness, `python3 -I` standalone QA and disabled
  notification cron fixture all passed. Optional sibling source/wheel
  installation scenarios remain skipped because A_STOCK_LIB_SOURCE is unset.
- `.venv/bin/python -m pytest -q tests/monitor/test_risk_closure.py tests/test_monitor_contract.py tests/monitor/test_monitor_snapshot.py`:
  exit 0, **273 passed**.
- `git diff --check`: exit 0. Full log: `/tmp/a-stock-s1-check.log` (outside Git).
- Real Codex CLI independent read-only review initially requested two fixes:
  cleared/no_action without a clean gate, and over_budget without risk evidence.
  Both were fixed and regression-tested. Targeted follow-up returned PASS with
  no remaining direct blocker in those fixes; the reviewer did not run tests.
  Reports remain outside Git: `/tmp/a-stock-s1-independent-review.txt` and
  `/tmp/a-stock-s1-review-followup.txt`. This is code review, not client qualification.
- No production database, broker account, live quote service, schema, cron or
  active client entry was modified/accessed by these fixture checks. No real
  notifications were sent. Real-client fake-tool budget qualification is
  **NOT_VERIFIED** for Claude, Codex and Hermes; historical captures do not
  replace it. Production is **NOT_VERIFIED / NOT_DEPLOYED**.
- Network use is limited here to Git reference/push operations, dependency
  tooling if needed, and independent read-only Codex CLI code review. That
  review is not a real-client monitoring qualification test.
- At this S1 checkpoint S2/S3 were not started; S4 remains deferred. There is no investment-validity
  or personal-account-return claim. Deployment remains separately authorized.
