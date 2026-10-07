# Runtime contracts

Current source contracts. Active release identity, client verification and rollback
belong in the [operations record](../operations.md#current-deployment-record).

## Ownership

| Layer | Owner | Responsibility |
|---|---|---|
| Shared deterministic domain logic | `a-stock-lib` | Framework scoring, valuation, market-data results and cross-consumer contracts |
| Application runtime | `a-stock-agent-skills` | Holdings, L3, Tier, monitoring workflows, authorization and serialization |
| Framework routing | `framework_catalog.py` | A–F industry routing, portfolio labels and stop-loss coefficients |
| Skill text | `skills/*/SKILL.md` | Thin routing and tool-use instructions; never reconstruct machine state from prose |

`checklist.py` retains checklist presentation metadata. Runtime routing does not
depend on importing that registry.

`db.py` owns SQLite connections: read-only paths use an escaped file URI with
`mode=ro`, preserving literal filenames and refusing missing databases or writes.
Writable setup creates a new database parent with mode `0700`; it never changes
permissions of an existing directory. An existing parent with group/other access
is rejected before opening the database, with a controlled CLI failure. Operators
must select a private state directory or explicitly secure it themselves.

The A-framework checklist debt exception automatically recognizes only cached
industry labels `汽车整车`, `整车`, and `重型设备`. Broader or unknown labels require
manual verification under the existing A-framework rule; the checklist retains
the ordinary threshold until eligibility is established. The TuShare debt ratio
requires all four collected debt components to be present, numeric, finite and
nonnegative, and total liabilities to be finite and positive. Missing components
remain missing, rather than becoming zero, without blocking other financial
fields.

## Versioned wire contracts

### decision-v1

`decision_contract.py` owns validation and deterministic JSON serialization for
research decisions. JSON is authoritative; Markdown is a human rendering.

### monitor-v1

`monitor_contract.py` owns monitoring status vocabularies, structural and
cross-field validation, finite-number enforcement, parsing and deterministic
JSON serialization. Both normal and unavailable `monitor-snapshot --json`
outputs use this contract. Additive unknown fields are accepted; renaming a v1
field requires a future contract version.

#### Coordinated S1 monitor-v1 extension (2026-09-17)

`schema_version=1` is retained, but the new `risk_budget_exceeded` enumeration
is **not compatible with old strict consumers**. This is a coordinated
runtime/validator/command-adapter/Monitor-Skill release, not a generally
backward-compatible additive-field change. Do not mix release sets.

| Producer / consumer | Support |
|---|---|
| New / new | Budget upgrades, required safety evidence and current invariants |
| Old / new | Missing safety evidence is rejected with MonitorContractError; never filled into clean |
| New / old | Unsupported; old validator rejects the unknown reason code; prohibited deployment |
| Historical capture | Validates its original source/Skill identity and behavior only |

`account.risk_budget_status` is `over_budget`, `within_budget`, or null. Known
single-name or portfolio lower-bound breaches survive other missing risks.
Incomplete `total_stop_risk` and `total_stop_risk_pct` remain null; only the
explicit `known_stop_risk_lower_bound` may describe the known part. Required
`account.risk_policy` carries actual limits, policy_id, source and field_sources.
S1 sources are compatibility defaults (2% / 8%) or explicit CLI overrides,
not confirmed personal policy. Comparisons are strict `>` before formatting.

A budget escalation is a review candidate; code=null means portfolio scope.
There is at most one budget escalation per scope/code. Details identify amount,
ratio, limit, denominator and source/scope. Proven breaches cannot coexist with
cleared/no_action/clean. Existing valid trade candidates retain precedence;
stale/unavailable/conflicted data remains blocked. No alert is persisted.
Clean additionally requires complete risk, quotes, valuation and denominator
evidence, with active quote count matching the holdings array. Missing DB state
is unavailable, not empty holdings. Validation checks evidence and consistency;
it does not reproduce financial calculations.

`risk_budget.py` owns shared risk input validity and budget assessment. The
existing `calculate_position_risk()` retains its economic formula. Both risk
CLIs use the same parsed limits and quote checks; monitor local multi-table
reads use one deferred read transaction, released before quotes. Portfolio-risk
opens a read-only connection and cannot bootstrap missing schema.

Release identity is the source commit plus package/source-archive and Skill
SHA-256 values, not the unchanged development package version alone. Package
the matching runtime, validator, CLI adapter and all Skill files as one release
set; archive/build hashes belong in the external release manifest. Inventory
known consumers before rollout. Any independently upgradeable consumer requirement
blocks this v1 rollout pending an explicit compatibility decision.

Current-budget deterministic routing tests are separate from immutable model
captures. Current-client fake-tool budget evidence remains the normal activation
requirement. Historical client-verification waivers in the deployment record do
not exempt future releases. No production legacy-permissive parsing switch exists.

## Risk policy and performance

`risk_policy.py` resolves the shared effective parameters before either risk
handler runs. A selected invalid policy fails closed even with numeric overrides;
file identity, confirmation, scope, timezone and field sources are explicit. No
policy is written or adopted by the model. Denominator as-of/scope gaps remain
visible and do not grant new-risk authorization. Existing monitor-v1 safety and
coordinated-release boundaries above remain in force.

`performance.py` produces an **internal application result**, not a new wire
contract: `schema_version=1`, `report_type=account_performance`, input provenance,
coverage/gaps and independent segments. Null metrics have `null_reasons`;
provisional source status cannot hide estimated cash-flow math. Benchmark returns
are per-segment references, not execution or causal AI attribution. File-only
R0 dispatch precedes database-path handling; optional ledger reads never imply
account mapping/reconciliation was completed. Nothing writes to decision-v1,
monitor-v1 or account facts. See [operations](../operations.md) for input/exit
semantics and the [Git-archived S2/S3 ledger](../README.md#历史只从-git-追溯) for
fixture evidence and unfinished reconciliation/evaluation boundaries.

## Independent version dimensions

- **Package version** identifies installed code: `a-stock-lib==0.8.0` and the
  `a-stock-agent-skills==0.1.13` source line.
- **Contract version** identifies a wire shape: decision v1 and monitor v1.
- **Policy version** identifies investment or regulatory rules independently of
  package and wire versions. Framework policy uses `RULE_VERSION` and
  `rule_hash`; regulatory policy uses source metadata and its freshness review
  lifecycle.

A package patch may preserve a contract version. A policy update must not be
hidden behind an unchanged policy identity.

## Agent behavior evidence

`scripts/capture_agent_tool_e2e.mjs` runs one fixed
`openai-codex/gpt-5.6-sol` session with an isolated home, read-only model
credentials and in-process fake tools. The capture records its source commit,
script and Skill hashes, exposed tools and structured isolation metadata.
`tests/test_agent_tool_e2e.py` verifies that evidence offline, including that
the exposed fake W1 tool was not called.

Production A-stock CLIs, databases, holdings and market-data credentials are
not exposed to this capture. This capture is historical: the test checks its
recorded Skill bytes at its recorded commit, not today's edited Skills. It does
not qualify the S1 budget extension or current production clients.
