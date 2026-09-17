# Changelog

## 0.1.13 — Unreleased

- S2 Tracker e2 软件落地于 `41c95d3`：用户批准默认清单使用 `config/`，固定资格/并列权重/批次与逐日路径；299 tests 及产品门禁通过，清单仍 pending，未部署。Agent 仅同步规范与[S2/S3 验收记录](plans/2026-09-17-s2-s3-implementation.md)。

- 新增 S3b 文件型 `performance-report` MVP：Decimal 现金流调整、分段收益/回撤、按片段对齐的可选基准、明确 null 原因与退出码；默认不选数据库路径，不建库/联网/写回。账本检查仅为未完成账户映射的有限诊断，真实对账未验收。未部署，见[S2/S3 记录](plans/2026-09-17-s2-s3-implementation.md)。

- 启动 S2/S3，完成 S3a 只读风险政策解析：统一两风险 CLI 的来源优先级、文件安全与账户/时点校验，非法文件不回退；不创建真实政策、不部署。见[S2/S3 记录](plans/2026-09-17-s2-s3-implementation.md)。

- 完成仓库级风险闭环 S1：预算超限升级复核、未知风险 fail-closed、JSON/文本共用输入与政策参数校验；monitor-v1 合同和 Monitor Skill 协调扩展，新增只读事务、兼容矩阵及事实记账回归。未部署、当前客户端资格未验证，见[实施记录](plans/2026-09-17-risk-closure-implementation.md)。

- 抽取并统一接入 monitor-v1 验证与确定性序列化；unavailable snapshot 补齐结构化 `industry_context`。
- 将 A–F 行业路由、组合标签和止损系数移入显式 catalog，移除 domain 对 checklist import side effect 的依赖。
- Live Agent fake-tool capture 绑定 source commit、脚本、独立 Skill hash、暴露工具和机器可验证的隔离元数据。
- 新增 runtime contract 架构文档；投资阈值、W1 授权和生产状态不变。
- 对齐 QA 的 process verdict 合同、不可变快照边界和宿主独立调用措辞，并新增定向合同检查。
- 新增 2026-09-17 风险闭环、Tracker 验证与账户业绩 MVP 的仅文档规范（v1.1）。

## 0.1.12 — 2026-09-13

- 将 frozen dependency 更新到不可变的 `a-stock-lib==0.8.0` Release wheel，并固定 SHA-256 `a811945b23d97eb121ff82d54bc0ba0810000a5379a9e9786fdcdc9220b30310`。
- 保留行业缓存失败语义、Skill 防回归门与监管规则 freshness guard；用单个固定 `openai-codex/gpt-5.6-sol` 会话直接调用隔离 fake tools，覆盖三条关键路由且不执行未授权 W1。

## 2026-09-09 (deployed runtime 0.1.11-996e552a3463)

- Wired existing TuShare statement history into P1 TTM ROE/five-year inputs and P2 TTM CFO/Capex/FCF without adding a provider or database schema.
- Added true TTM profit, PE and PEG fields plus read-only decision/data-completeness metadata to `check` output.
- Treated newer-report BPS as a normal update and scoped PB-percentile incompatibility to frameworks that actually use PB.
- Routed EMS/ODM, components and precision electronics manufacturing to A instead of F; clarified profitable-F PEG and loss-making-F PS branches.
- Preserved fundamental subtotal/configuration rating when only P1 blocks timing, compacted the default report, and made QA self-invocation/hash/source-identity limits explicit.

## 2026-09-07

- Added pure functional P0–P3 risk control gates (`risk_gates.py`) evaluated before valuation scoring and holding trade proposals.
- P0: Regulatory compliance gate covering ST/listing status, audit opinions, formal CSRC investigation, and board-specific statutory dividend rules (50M CNY for Main Board, 30M CNY for STAR and ChiNext, not applicable for BSE).
- P1: Structural ROE deterioration gate comparing same-basis TTM ROE with 5-year mean, invalidating valuation percentiles when TTM ROE is negative or retention ratio is strictly below 0.75, with 3-factor DuPont drill-down.
- P2: True FCF gate (`FCF = CFO - Capex`) with strict Capex > CFO redline and `review_required` state machine for heavy capex cycles in C/D frameworks.
- P3: Extreme systemic liquidity shock gate delaying second-stop candidate actions for 24 hours when verified limit-down count strictly exceeds 500, with untradeable/suspended price protection and `holding_alerts` persistence.
- Aligned Research, Monitor, and QA contracts with checks 19, 20, 21 added to QA rubric without database schema changes.

## 0.1.11 - 2026-09-02

- Added deterministic `valuation_compatibility` metadata from the existing quote, annual PB/BPS and latest-report BPS, with a decimal-safe inclusive 2% timing gate and no database migration.
- Added a mandatory `FUNDAMENTALS_HIT` data card so available dividend, valuation and latest-report fields cannot disappear from report prose.
- Aligned Research, report and QA contracts: legal fundamental `scoring_status=incomplete` outputs `not_formed`, while PB/BPS compatibility remains timing-only and cannot suppress a complete configuration grade.

## 0.1.10 - 2026-09-01

- Added compact, machine-readable holdings, active-alert and active-L3 views so daily monitoring no longer loads accumulated holding notes or resolved history by default.
- Machine-readable monitoring views now fail nonzero with stable `*_UNAVAILABLE` markers when the state database is missing instead of returning success with empty, invalid JSON.
- Preserved legacy, pending, watch and invalid-contract boundaries in JSON and prohibited clean “all L3 clear” summaries while any such state remains.
- Stopped monitor tasks from invoking the research-only QA Skill until a monitor rubric exists.

## 0.1.9 - 2026-08-30

- Bounded unspecified research/comparison requests to a concise but QA-complete first report, with installed-runtime-first market data, small search batches and an explicit stop condition after mandatory evidence gates.
- Bound QA verdicts to immutable versioned report snapshots and prohibited polling/sleep or concurrent report edits while asynchronous QA runs.
- Aligned the A-framework external-concentration output with the QA rubric for normal as well as limited/major states, and documented the required `gross_margin_stable` scorer supplement.
- Reused the existing valuation price history to expose a provenance-stamped five-session price change without another provider call.
- Stopped optional sentiment/provider recovery after an incomplete gate has fixed the action, required QA-complete one-shot delivery, and kept one-off report snapshots out of durable project directories.

## 0.1.8 - 2026-08-27

- Made holdings and read-only retrospective queries physically read-only and removed command-time compatibility backfills already owned by migration 025.
- Added `a-stock-cache holdings [code]` so routing can inspect one security without exposing unrelated holding notes; missing rows and unavailable ledgers now have distinct stable outcomes.
- Hard-stopped first-time research after confirmed held-stock routing and added bounded official-first retrieval, document fallback and concise monitor-delivery contracts without changing investment rules.

## 0.1.7 - 2026-08-27

- Added versioned holding theses with a partial unique index enforcing one active thesis per holding.
- Added the W1 `thesis-rewrite` command, which validates one stdin JSON payload and atomically supersedes the thesis, retires the complete old L3 set and creates linked structured replacements.
- Added L3 lifecycle, scope, action and materiality fields; active listings follow the current thesis, `l3-list --all` retains audit history, and retired updates are rejected.
- Preserved unrevised holdings under the existing behavior with a visible `legacy contract` warning; rewritten holdings fail closed on stale or unclassified active L3 contracts.

## 0.1.6 - 2026-08-23

- Requires `a-stock-lib==0.6.1`, whose rule hash follows executable scorer source automatically.
- Applied the existing Ruff formatter across maintained Python sources and tests, closing the historical format baseline gap without behavior changes.

## 0.1.5 - 2026-08-23

- Added the read-only `a-stock-cache score-fundamentals` bridge to the A—F deterministic 60-point scorer in `a-stock-lib==0.6.0`.
- Research now treats the scorer subtotal, rule version/hash, missing inputs and red lines as authoritative; manual fundamental-score fallback is retired.

## 0.1.4 - 2026-08-23

### Added

- Fetcher now exposes same-basis `ps_ttm` and 5-year month-end `ps_percentile_5y` from TuShare `daily_basic`, with a 60-valid-month fail-closed gate.
- Fundamentals cache now carries a non-scoring `latest_report_snapshot` for newer interim-report direction checks while preserving annual scoring fields.
- Research moves detailed cycle, timing-adjustment and report templates into three directly linked references while retaining safety and fail-closed gates in the main Skill.

## 0.1.3 - 2026-08-14

### Added

- Runtime fetcher now emits a same-basis 5-year PE percentile with explicit window/basis provenance.
- A-framework reports now carry an external-concentration risk overlay without changing the 60-point score.

### Changed

- `pe_static` is the canonical annual-EPS price multiple; legacy `pe_ttm` remains a deprecated compatibility alias.
- Research requires `a-stock-fetch fetch` to complete before `a-stock-cache check`, and explicitly links every framework reference.
- QA classifies missing report inputs as `INVALID_RUN`, aggregates Important/Critical failures deterministically, and keeps rubric-external advice out of verdicts.

## 0.1.2 - 2026-08-11

### Changed

- M8 completion now means all Claude, Codex and Hermes `a-stock-*` entries use the canonical repository and superseded Skill copies remain archived; Claude is not retired.
- The cache CLI now uses argparse subcommands, rejects surplus or misplaced arguments consistently, and accepts holding notes only through `add-holding --notes`.
- The runtime monolith was split into domain, database, schema, store and command modules while preserving the stable `a-stock-cache` entrypoint.
- Historical review packets moved to the independently versioned `/home/lin/a-stock-agent-evidence` repository with a verified manifest and recovery tombstone.

### Fixed

- Tests and subprocesses resolve isolated temporary databases, and cache metadata lookups use an explicit SQLite read-only session.
- Cross-command helpers use owner-module-qualified calls so monkeypatches remain observable after the module split.

## 0.1.1 - 2026-08-11

### Added

- `a-stock-research`: added product-cycle and thematic-catalyst routing that separates event narratives, order progress and financial realization, with explicit counter-evidence and reproducible conditional valuation boundaries.

### Fixed

- Runtime R0 commands no longer invoke the holdings metadata backfill on physically read-only database connections.
- Audit remediation (2026-08-09): R0 database access is physically read-only; unknown/stale quote timestamps cannot trigger stop-loss or portfolio-risk actions; installer releases are wheel-backed and preflighted with collision-free backups; migration and cron failures now fail closed.
- Skill portability: research QA routing now uses host discovery without client-specific commands, QA scope matches its research-only rubric, and checklist output is client-neutral.
- Maintenance: removed stale compatibility exports, broken legacy runners, and the unmaintained mypy gate.
- `a-stock-research`: removed the conflicting total-score action table; the dual-track matrix is now the sole action outlet, and tranche fractions are scoped to a pre-approved single-name risk cap.
- `a-stock-research`: current PB is computed from the validated price and compatible-period BPS; inconsistent PB/BPS reports fail closed.
- C resource framework: added forward/normalised valuation conflict handling, comparable cost evidence for top reserve-competitiveness scores, and adjacent-cycle scenario handling.
- `a-stock-qa`: added checks for valuation arithmetic/period consistency, unique decision output, position scope, and C-resource evidence quality.
- Runtime cache: an analysis without both its stored price and a fresh validated quote can no longer return `ANALYSIS_HIT`.
- Runtime fetcher: cached industry fallback is now persisted as `stale_cache` and cannot silently authorize framework routing.
- `a-stock-research`: unsupported 5-year/PS/true-PEG inputs, newer-report conflicts, and fully missing bank core data now fail closed; Biotech uses a qualitative-only route; timing arithmetic and risk-sizing boundaries are explicit.
- `a-stock-monitor`: split ROE deterioration into 3pt yellow and 5pt red-review gates, removed ambiguous direct-sell wording, and bound accumulation proposals to portfolio-risk prerequisites.
- `a-stock-qa`: added checks for current-report/valuation capability, bank completeness, reproducible timing arithmetic, and an explicit text-only compliance boundary.

Trigger: 紫金矿业（601899）investment review, 2026-08-09, AGY with parent adjudication.

### Fixed (2026-08-10 engineering repairs)

- Development environment: documented `uv sync --frozen --inexact`; the plain form uninstalled the externally provisioned `a-stock-lib` and broke every runtime import.
- Installer tests no longer depend on a warm host `uv` cache reachable through the relocated `HOME`, and locate `a-stock-lib` via `A_STOCK_LIB_SOURCE` instead of a hardcoded path, skipping when it is absent.
- `a-stock-cache --help` now states the global `--confirm-write` gate and its W1 command list, and documents the four `retro-*` commands; a test keeps the text in sync with the command table.
- A failed schema bootstrap no longer leaks the connection it opened. `get_db` closes it before re-raising, so the still-open ledger transaction cannot lock the database and mask the real migration error behind `database is locked`.
- Pinned the migration ledger's real recovery contract: Python's sqlite3 opens an implicit transaction only before DML, so the first pending migration's DDL autocommits and can outlive a failure later in the batch. Recovery is the replay swallowing `duplicate column name`, not atomicity.

### Changed (2026-08-10 engineering repairs)

- Added `scripts/check.sh` as the single repository gate; this repository has no git remote, so there is no hosted CI to be the source of truth.
- Removed the superseded `apply_schema_migrations` duplicate and the redundant `_invoke` dispatch branch; the migration ledger's `apply_column_migration` is now the only column-migration path.

Trigger: P0/P1 engineering repairs, 2026-08-10, AGY review with parent adjudication.
