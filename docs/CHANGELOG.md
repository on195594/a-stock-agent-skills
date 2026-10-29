# Changelog

## 0.1.26 — 2026-10-29

- Research 增加 `resume --request-id` 只读任务找回、`report --compact` 精简视图与 `budget` 调用保护说明；不自动重开研究，费用未知不误报免费。
- 复用服务端同口径对照，明确基线状态/时效、旧检查点、排除项与缺口；异常失败保留材料缺口及来源，旧服务不支持新接口时明确提示。
- 新增 R0 `portfolio-scenario`：仅比较用户指定股数和费用下的静态现金、仓位、风险预算变化，复用原风险公式、保留源状态；不生成交易候选、不写账本、不下单。
- 两轮 Claude Opus 5.5 独立审查与真实记录回归已完成；全量模型多轮 Skill 行为回放仍为 NOT_RUN。投资规则、数据库结构不变；先部署配套 Research，再激活本版本。

## 0.1.25 — 2026-10-27

- 精简 Research 上下文：格雷厄姆分支、主估值轴表与 C/D 框架门槛从 `research-execution-flow.md` 移入对应 `frameworks/*.md`，只加载已确认框架；先完成本地 `fetch`/`check` 再复用 Research 服务报告；报告 `checkpoints` 只作下期观察条件，可作为纠错位置。投资规则不变。
- Monitor 首次快照随调用传入已确认的账户范围与资产估值时点；L3 触发或候选须先读 L3 资料再复核。`daily-brief` 把 7 天内未触发的 L3 例行复核按日期合并为一行，状态显示中文。
- 行为评测新增 input version 3（缓存正文、缺失持仓路由定义、待确认 W1 的账户范围/估值时点），历史版本仍可显式评分。

## 0.1.24 — 2026-10-27

- Research 服务改用具名、可撤销的长期 API Key（`A_STOCK_RESEARCH_TOKEN` 不变）；HTTP 401 给出更新凭据、检查环境变量覆盖、沿用原 request-id 的明确提示。

## 0.1.23 — 2026-10-23

- 新增 `a-stock-cache research`：`research-v1` HTTP 客户端，读取报告目录/报告/任务状态，提交研究、追问与纠错；从环境或所选 `runtime.env` 读取 `A_STOCK_RESEARCH_URL`/`A_STOCK_RESEARCH_TOKEN`，从不打开账户数据库。Research/Monitor Skill 按需先复用已有报告。

## 0.1.22 质量修复 — 2026-10-23（`992f5a5`）

- 缓存命中直接展示正文并停止；仅核对持仓且结果不完整时不擅自启动研究；现金或单只市值不能充当总资产；跨追问复用已提供材料；待确认 W1 保持 `blocked`。行为评测补齐完整输入（input version 2）。删除无调用的 checklist 别名。

## 0.1.22 — 2026-10-22

- 新增 `stop-alert`：交易时段内按账本止损线（随分红除权调整）检查全部在仓持仓，跌破第二档、跌破第一档、距第一档 3% 以内三级提醒，每只每天每级只推一次；只用当日 15 分钟内行情，全部无效时以非零退出可见失败。去重状态写在运行时状态目录，不写投资状态。
- `check-holdings-cron.sh` 只在出现价格/P3 止损预警时推送；仅风险门冻结（同为 🔴）不再被当作“持仓止损预警”每日推送。

## 0.1.21 — 2026-10-22

- 新增只读 `daily-brief`：基于 monitor-v1 快照输出盘后推送文本（现价、日涨跌、距两档止损、升级项、未触发以外或 7 天内到期的 L3、疑似漏记分红）；无当日行情时不输出，供 Hermes no-agent 定时推送。`dividend-check` 的扫描抽为共享函数，输出不变。

## 0.1.20 — 2026-10-22

- 新增只读 `benchmark-report [--end YYYY-MM-DD]`：把账本全部买卖与分红现金流按同日同额镜像到沪深300全收益、中证红利全收益（TuShare H00300.CSI/H00922.CSI），在共同估值日比较净盈亏与超额；含推断事件时标为近似值。a-stock-lib 0.8.2 指数接口返回 SCHEMA_CHANGED，暂直接调 TuShare（代码内 shortcut 注释）。

## 0.1.19 — 2026-10-22

- 修复 Codex 审查发现：`regulatory-evidence` 拒绝预设子门对象；P0 沿用改为保存原始事实并按现行规则重判，且在写缓存的同一事务内读取最新证据；`dividend-check` 识别已记账的纯转增，登记日后股数变化时改给按应收总额的命令，现金与转增只记一部分时不给自动命令；`fetch` 完成摘要按写入后的门状态统计；组合级止损风险归因在任一持仓拆分未知时标为 unknown；新增测试守卫，禁止测试撤销数据库隔离。

## 0.1.18 — 2026-10-22

- 新增只读 `dividend-check`：按登记日账本持股找出已实施但未记账的分红，并给出 `corporate-action` 记账命令；`sell-holding` 税费为 0 时提示 0.5‰ 印花税估算。不改投资规则。
- 按[P0 证据按年报期沿用规范](specs/2026-10-22-p0-evidence-annual-carry-forward-spec.md)（用户选择方案 3）：`fetch` 刷新沿用同一年报期已补的 clear/blocked P0 证据（按现行规则重判）；新增 W1 `regulatory-evidence` 合并写入 runtime 计算的 P0 门且不改 `updated_at`；修复显式 null 的上市/立案状态被当作“无风险”的 fail-open。

## 0.1.17 — 2026-10-22

- 按[风险分母与超限归因规范](specs/2026-10-22-risk-denominator-and-breach-attribution-spec.md)（用户选择 B+D）：风险政策可选 `off_account_strategy_cash` 计入分母并输出 `denominator_components`；单股止损风险拆出 `stop_risk_unrealized_gain`，超限明细列出本金/浮盈两部分与分母来源。风险公式、上限与判定不变；超限只触发复核，Skill 禁止提出快照未给出的卖出标的或股数。方案 A（止损随浮盈上移）经历史回放否决。

## 0.1.13 — 2026-09-18 (runtime deployed)

- 13:17 CST：用户明确授权上线后，Tracker S2 `7516535` / lib 0.8.0 已作为独立 checkout 部署；299 tests 与全部项目门禁通过，只读报告 smoke 按 pending manifest 返回证据不足。09:36 的 Agent `ACTIVE_RELEASE.json` 是不可变的 runtime/Skill 快照，其 `tracker: NOT_DEPLOYED` 不代表 13:17 后的 Tracker 现场。cron、schema、生产数据库、通知与实验登记均未改动；S4 继续延后。

- 09:36 CST：用户单独授权后，完成备份与迁移 035，仅新增可空 `analysis_results.decision_json TEXT` 列并登记一次；事务内核验原有列值、业务行与旧迁移记录不变。Agent `4789fc9` / lib 0.8.0 已协调切换三个 CLI 和九个 Skill 入口，Hermes 网关正常，crontab 未变。Hermes/Codex 同版本预算回放通过；Claude 按用户要求部署但未验证。此前 schema 门禁回滚为历史检查点。见[部署与回滚记录](operations.md#current-deployment-record)。

以下实现条目的“未部署”描述保留各自交付时点含义；当前状态以上述部署记录为准。

- 对齐 S1–S3 当前部署状态与开发门禁，清理无调用的 decision-v1 周期字段访问器和 checklist 预留参数；不改变合同验证或运行时行为。

- S2 Tracker e2 软件交付于 `41c95d3`：用户批准默认清单使用 `config/`，固定资格/并列权重/批次与逐日路径；299 tests 及产品门禁通过，交付时清单仍 pending、尚未部署。Agent 仅同步规范与[S2/S3 验收记录（现已 Git 归档）](README.md#历史只从-git-追溯)。后续部署状态见本版本顶部记录。

- 新增 S3b 文件型 `performance-report` MVP：Decimal 现金流调整、分段收益/回撤、按片段对齐的可选基准、明确 null 原因与退出码；默认不选数据库路径，不建库/联网/写回。账本检查仅为未完成账户映射的有限诊断，真实对账未验收；交付时尚未部署。见[S2/S3 记录（现已 Git 归档）](README.md#历史只从-git-追溯)。

- 启动 S2/S3，完成 S3a 只读风险政策解析：统一两风险 CLI 的来源优先级、文件安全与账户/时点校验，非法文件不回退；交付时不创建真实政策、不部署。见[S2/S3 记录（现已 Git 归档）](README.md#历史只从-git-追溯)。

- 完成仓库级风险闭环 S1：预算超限升级复核、未知风险 fail-closed、JSON/文本共用输入与政策参数校验；monitor-v1 合同和 Monitor Skill 协调扩展，新增只读事务、兼容矩阵及事实记账回归。交付时尚未部署，当前客户端资格仍未验证；见[S1 实施记录（现已 Git 归档）](README.md#历史只从-git-追溯)。

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
