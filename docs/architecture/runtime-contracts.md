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

The cross-project [contract](https://github.com/on195594/a-share-research/blob/main/docs/project-contract.md)
defines `a-share-research` as an independent peer consuming the same Lib. It owns
its report format, source documents and research state. `a-stock-cache research`
uses its versioned HTTP API for report/evidence reads and research/follow-up/feedback
submission. This R1 namespace bypasses the local investment database entirely;
remote research records do not grant W1 account writes. Explicit HTTPS configuration
(local HTTP is allowed), revocable long-lived API keys (temporary bearer tokens for checks), no redirects and preserved
request IDs keep retries and credentials bounded. Errors remain visible; there is no
automatic provider fallback or polling loop. Evidence does not replace decision-v1/
monitor-v1 or their authorization boundaries.
`a-stock-qa` continues to check only the Research Skill's text rubric, not the
peer application's report format or Monitor output.

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

`a-stock-fetch quarter` shares fetch's annual dividend calculation, including
announced proposals and the existing whole-year split adjustment. The helper
returns the selected year, periods and split metadata with DPS; quarter does not
reconstruct them. Quarter reads the same financial adapter to obtain fetch's
split cutoff year. Missing or nonpositive DPS produces null with a reason and
null dividend-spread thresholds.

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

#### Research card extension (0.1.29, 2026-11-01)

The [dated batch B specification](../specs/2026-11-01-research-card-review-prompts-spec.md)
authorizes this additive extension, retaining `schema_version=1`. New snapshots
include `research` and `review_prompts`; old snapshots without both remain readable.
The new reason enum requires matching runtime, validator and Monitor Skill consumers.

`monitor-snapshot` performs one read-only `GET /api/cards`; `--no-research` skips it.
`research_client.request_json` owns endpoint validation, bearer/version headers,
(10, 30) timeout, no redirects/retries, error redaction and response version checks.
`research cards` and `research card <code>` expose the corresponding GET endpoints;
none starts a research task. Missing configuration gives `not_configured`, opt-out
`skipped`, and transport/version/malformed-card errors `unavailable` with a bounded
reason. Successful reads are `ok`. Tests inject HTTP and never use live credentials.

`research.holdings` has one row per active code; `candidates` contains only L5 codes
outside holdings (including missing L5 cards). Rows contain `code`, the original
`card` (or null), `card_status`, `verdict`, `report_id`, `completed_at`, `close`,
`close_date`, `zone`, the three `*_return` fields, `note` (pause notice) and, since
0.1.31, `assumption` (Research's verbatim caveat on rolled returns, null if absent;
older snapshots without it remain readable). `missing` is the list
of codes reported missing by Research; a holding outside the scan scope also gets
a null card, without being added to that list. No card means null projection fields.
Current prices, zones, annual returns and horizon come from Research, never from
runtime valuation calculations. Pending cards retain those values and their pause note.

`review_prompts` contains `code`, `kind`, a Chinese `detail` and `evidence`.
Kinds are `valuation_stretched`, `opportunity_cost`, `research_unavailable`
(the latter has code=null). These prompts never enter escalations. Opportunity
comparisons require valid cards, non-null neutral returns, a valid L5 candidate
verdict of 值得继续研究, positive candidate horizon, and closing dates at most
three calendar days apart; rejected date comparisons are explained in `research.reason`.
Research optionally supplies `neutral_return_without_dividends`; it must be present and
between -1 and the ordinary neutral return on both cards for opportunity comparisons.
Net advantage now uses the candidate's no-dividend endpoint minus the holding's full-dividend
neutral return minus the existing annual cost. This tests sensitivity within frozen nonnegative
dividend assumptions, not actual-return bounds. Missing endpoints or insufficient robust advantage
are explained in `research.reason`; a near miss (nominal neutral gap already ≥ 0.03 before cost)
states both net advantages in percentage points, full-dividend and candidate no-dividend, so
dividend-heavy candidates stay visible. Original returns and all account gates remain unchanged.
Per holding, only the largest such net advantage reaching 0.03 is reported. Evidence
retains both report IDs and closing dates, neutral returns, candidate horizon,
annual switch cost and net advantage. `trading_costs.py` owns `STAMP_TAX_RATE=0.0005`
and `COMMISSION_RATE=0.00025`; annual cost is `(stamp + 2 * commission) / horizon`.
The holding-sale ledger imports the same stamp-tax constant. No sizing is generated.

The [0.1.30 specification](../specs/2026-11-02-opportunity-cost-digest-spec.md)
adds `research.opportunity_costs` (always an array, empty when no comparisons),
without changing `schema_version`. Each item has the former opportunity prompt's
evidence fields: `holding`, `candidate` (each with `code`, `report_id`, `close_date`,
`close`), `holding_neutral_return`, `candidate_neutral_return`, `candidate_horizon`,
`annual_switch_cost`, `net_advantage`, plus `candidate_return_without_dividends` and
`comparison_basis` explaining the sensitivity calculation. All best-per-holding comparisons remain here
regardless of age; portfolio reviews and switching tables use this complete list.
Opportunity prompts now group by candidate: `code` is the candidate code and
`evidence.comparisons` contains all its retained comparisons. A group is shown only
when the candidate or any compared holding's `completed_at` Asia/Shanghai calendar
date is 0–7 days before the snapshot's own `as_of` date (inclusive). Missing, null or unparseable
completion timestamps are not fresh and do not invalidate the card. No clock or
closing date is substituted. Detail lists the candidate, neutral return, compared
holdings and maximum net advantage, with “情景未经记分，仅提示复核”, followed by
each distinct compared-card `assumption` as “Research 注：…”. Older snapshots
without `opportunity_costs` retain validation of their per-holding prompt shape.

The [0.1.35 specification](../specs/2026-11-04-proactive-decision-spec.md) adds
optional row fields `stance_action`, `stance_price`, `stance_valid_until` (from the
card's frozen `stance_calc`) and `expected_return`, `v2_zone` (from
`current.valuation.v2`), all-or-none and checked against the card; older rows
without them remain readable. Prompt kind `research_opportunity` is emitted for a
valid L5 candidate with verdict 值得继续研究 when `v2_zone` is 测算支持区, a 等价格
stance's price is reached on or before `stance_valid_until`, or a 现在分批 stance
is 0–7 days old. Its evidence is the candidate row's `code`, `report_id`,
`close_date`, `close` plus the five stance fields. It never changes action status;
sizing comes only from the read-only `position-size` command (`position-size-v1`:
second-tier stop, single-stock and portfolio stop-risk budgets, board lots,
`tranches` as fixed 1/3, 2/3, 1 stages of cumulative shares where an unexecutable
stage is 0, `action_status=not_formed`). The validator requires the prompt's
evidence to equal the candidate row field by field and re-checks the date-free
trigger (valid card, 值得继续研究, not 回避, and v2 support, 现在分批, or a reached
等价格 price).

The [0.1.37 specification](../specs/2026-11-04-reference-evidence-spec.md) adds
optional `stance_add_trigger`: the frozen `add_trigger` for 现在分批, or `trigger`
for legacy 等证据, otherwise null. Its exact shape is `{metric, period, op, value}`:
T.* financial row, ISO period date, >=/<=, and a finite number in the source row's
unit and cumulative basis. Cards validate the shape and any corresponding stance
checkpoint; rows and opportunity evidence must match the frozen card. Earlier
snapshots may omit the new field; when a row includes it, its opportunity evidence
must include it too. `schema_version` stays 1 and legacy 等证据 remains accepted.
Legacy 等证据 also qualifies for the 0–7-day opportunity condition. Checkpoint
prompts state the first-tranche ceiling (`tranches[0]`, including zero) and the
reference threshold, which never blocks the first tranche. Later tranches require
actual target-period disclosure meeting the threshold and updated valid Research
confirmation; an unmet threshold calls for reduction review, and undisclosed is
not unmet. The position-size budget calculation and three stages stay unchanged;
its note identifies the first-tranche ceiling when the card has a checkpoint.
Skills never infer fulfillment from the calendar or recompute Research numbers.

The [0.1.36 specification](../specs/2026-11-04-untradable-boards-spec.md) adds the
optional `account.risk_policy.untradable_boards` (distinct `STAR`/`BSE`, source
`policy_file`), applied even when the policy's limits are not applied for a missing
account scope. Candidates on those boards stay in `research.candidates`, are named in
`research.reason`, and are never the subject of `research_opportunity` or an
`opportunity_cost` comparison; the validator rejects either. `position-size` refuses them.

A pending holding card adds `research_thesis_review` with `candidate=review` and
pending event titles/types, ordered after `l3_watch` and before `governance_gate`.
Like every other escalation it ends the clean fast path: `review_status=cleared`
becomes `review_required`, `action_status=no_action` becomes `review_candidate` and
`stop_reason` is null; blocked reviews remain blocked. It never freezes risk or creates
a trade candidate. Research availability (`not_configured`/`unavailable`/`skipped`) and
`review_prompts` never change `data_status`, `action_status`, `data_gaps` or
`clean_fast_gate`. All ordinary escalations retain their gate semantics,
including `risk_budget_exceeded`. Research prompts and errors cannot freeze risk,
confirm L3, authorize trades or write state. Production comparison remains an
activation-time check requiring separate authorization.

#### Research risk cautions (0.1.40)

Research cards optionally supply `open_questions: [{id, where, problem}]` and
`boundary: bool|null` in frozen `valuation_calc` and rolled `current.valuation`.
The frozen summary also retains `close`, `as_of` and `v2.support_below` so its
report-time basis remains inspectable. Research owns the ±5% calculation; Skills
never recompute it. New fields do not rewrite reports or frozen stances.

Rows retain these fields in the existing nested `card`, not another risk state.
Review evidence adds only source-supplied `open_questions`, `report_boundary`,
`current_boundary`; absent legacy keys stay absent, explicit null stays unknown.
Each evidence value and its presence must match the source card, including both
sides of opportunity comparisons. Question ids/locations/problems must be nonempty
strings and ids distinct; flags must be bool/null, with positive price/hurdle
basis when non-null. There is no duplicated threshold calculation in the validator.

The existing `research_opportunity`, `opportunity_cost` and `valuation_stretched`
details preserve specific boundary and unanswered-question cautions, labelled by
code/report. Report-time and current boundary are distinct. Missing fields are
not evidence of stability/completeness; `[]` means no recorded open questions,
not certification that every user requirement was answered, and false is not
statistical confidence. Older cards/snapshots remain readable (`schema_version=1`).
Eligibility, freshness, account gates, first tranche, L3, action status and W1
permissions are unchanged. Cautions create neither a new escalation nor automatic
waiting/research. New snapshots require the matching runtime/validator pair: an
older strict validator may reject the additional evidence keys. Activate runtime
and Skill sources together; old cards and snapshots remain readable by the new
validator. This is a source contract; activation is recorded separately.

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
Sources are an effective, confirmed policy file (S3a), compatibility defaults
(2% / 8%, not a personal policy) or explicit CLI overrides. Comparisons are strict
`>` before formatting.

A budget escalation is a review candidate; code=null means portfolio scope.
There is at most one budget escalation per scope/code. Details identify amount,
its principal/unrealized-gain split (or unknown), ratio, limit, denominator and
source/scope. `account.denominator_components` splits the denominator into the
CLI account value and policy-file `off_account_strategy_cash`;
`manifest.denominator_source` is `cli` or `cli+policy_file`, and
`holdings[].stop_risk_unrealized_gain` is the gain above `reference_cost`.
Proven breaches cannot coexist with
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
file identity, confirmation, scope, timezone and field sources are explicit.
`monitor-snapshot` alone may omit an account scope even with a selected policy:
the file is still validated, but its limits, CLI limit overrides and strategy cash
are not applied. In this mode `account.risk_policy.status`, `source` and both
`field_sources` are `not_applied_account_scope_required`; `policy_id` identifies
the validated file and both limits are null. This documented monitor-v1 exception
requires the matching validator; ordinary policies still require positive limits.
`denominator_requires_review` is always true, even with a value and as-of supplied.
The golden `monitor-policy-not-applied.json` records this shape.
The holding layer remains available; `account_scope` is a data gap, weights and
budget conclusions are null, and the snapshot cannot be clean/no_action. An
explicit mismatched scope, invalid/unreadable or expired policy still fails.
No policy is written or adopted by the model. Denominator as-of/scope gaps remain
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

- **Package version** identifies packaged code. Source versions and dependency
  pins are maintained in `pyproject.toml` and `uv.lock`; actual installed identity
  and the matching runtime/Skill release set are recorded in operations. Do not
  infer active code from a source checkout or a development version alone.
- **Contract version** identifies a wire shape: decision v1 and monitor v1.
- **Policy version** identifies investment or regulatory rules independently of
  package and wire versions. Framework policy uses `RULE_VERSION` and
  `rule_hash`; regulatory policy uses source metadata and its freshness review
  lifecycle.

A package patch may preserve a contract version. A policy update must not be
hidden behind an unchanged policy identity.

## Agent behavior evidence

`scripts/capture_agent_behavior_eval.py` captures the eight behavior scenarios or
one fixed same-session follow-up group on Hermes. It binds candidate source,
Skill and runtime identities, preserves failures and verifies zero executed tools.
The offline scorer accepts historical or external candidate artifacts; follow-up
behavior is manually scored. Commands, baseline failures and validation limits
are maintained in [Agent behavior eval](../agent-behavior-eval.md).

### Historical tool-execution capture

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
