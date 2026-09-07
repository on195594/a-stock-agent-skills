---
title: A股投研与监控框架风控增强实施计划
status: completed
created: 2026-09-07
spec: ../specs/2026-09-07-investment-framework-and-risk-control-enhancement-spec.md
spec_rationale: 落实 2026-09-07 用户明确授权形成的投资规则规范；本计划只定义实施路径，不构成代码实施、发布或生产切换授权
execution_authorized: true
risk_tier: investment-policy-active-layer
baseline_commit: fb30e5e
tests_baseline: 711 passed
---

# A股投研与监控框架风控增强实施计划

> 本计划已获得用户明确授权执行 Phase 0—Phase 5。实现仅修改仓库代码、测试和 Skill 合同；生产数据库、持仓、交易账本、配置、cron 与 active client 不在本次范围。

> 投资规则按 Phase 0→5 依次交付。每个 Phase 都是独立 bounded commit、独立测试门和独立回滚单元；上一阶段通过不自动授权下一阶段。任何生产安装、active Skill 切换或生产写入仍需在实现完成后另行明确批准。

## 1. 背景与当前基线

现有系统已有 A—F 确定性评分、最新报告冲突 fail-closed、PB/BPS 估值兼容门、框架化止损价、活动论文/L3、Tier 与唯一动作出口。规范要求补齐四个仍会让低估值、评分或机械止损产生错误动作资格的硬门：监管合规、ROE 结构性恶化、真实自由现金流和极端系统性流动性休克。

开工基线固定为：

| 项目 | 基线 |
|---|---|
| Git commit | `fb30e5e`（完整 SHA：`fb30e5e5c74254e049f71a488f110dac08c7fde8`） |
| 全量测试 | `711 passed`（2026-09-07 以 `PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider` 复核） |
| Runtime 版本 | `0.1.11` |
| Python / 工具链 | Python 3.13+、uv、pytest、Ruff |
| 基本面持久化 | `stock_fundamentals.data` JSON；不需要新增列 |
| P3 可复用状态 | `holding_alerts.reason_code/evidence/review_due`；不需要新增表或列 |
| 评分入口 | `src/a_stock_agent_runtime/commands_analysis.py::cmd_score_fundamentals` |
| 持仓价格检查入口 | `src/a_stock_agent_runtime/commands_holdings.py::cmd_check_holdings` |
| 纯领域规则 | `src/a_stock_agent_runtime/domain.py` |
| 数据采集与 provenance | `src/a_stock_agent_runtime/fetcher.py`、`src/a_stock_agent_runtime/store.py` |
| 行情访问 | `src/a_stock_agent_runtime/market_quotes.py` |

当前工作树中的目标 spec 与 `docs/plans/.codex_plan_prompt.md` 为用户已有未跟踪文件。本计划不得覆盖、删除或顺带提交它们；实施开工时先重新记录 `git status --short`，以免把用户内容混入 Phase commit。

## 2. minimum_landing_change 与非目标

### 2.1 minimum_landing_change

首次最小落地只做 Phase 0：

1. 用一个纯规则模块固化 P0 板块法规映射、证据完整性、状态聚合和稳定 reason code；
2. 在现有 fetch/cache JSON 合同中承载 `regulatory_gate`，不改 SQLite schema；
3. 在 Research 评分调用前统一阻断 `blocked/incomplete`，保留 `scoring_status=incomplete` 与 `not_formed` 语义；
4. 在 Monitor 中把 P0 风险转换为“冻结新增风险敞口 + 红色复核候选”，不自动清仓、不产生第二动作出口；
5. 以先 RED、后 GREEN 的聚焦测试固定法规边界、fail-closed 与现有评分不变路径。

Phase 0 不预埋 P1—P3 的状态机、配置开关、数据库字段或抽象层。四个门后续共用一个 `src/a_stock_agent_runtime/risk_gates.py`；不建立四个类、四个包、插件体系或规则 DSL。

### 2.2 明确非目标

- 无 SQLite schema、`PRAGMA user_version`、表、列、索引或 migration 变更。
- 无新 Provider、无新生产依赖、无外部服务部署；只复用当前已安装的数据能力和官方原始证据。现有能力不足时必须返回 `incomplete`，不得临时抓取非权威聚合源补成 `clear`。
- 不修改 `a-stock-lib`、A—F 权重/阈值/公式、双轨矩阵、Tier1 `+25%`、Tier2/3、框架止损价、目标减仓比例、交易所股数校验或 L3 语义。
- 不引入宏观 Regime Filter、ATR、波动率分层、机器学习、回测寻优或主观市场预测。
- 不把 ST 等同退市，不把立案等同违法成立，不把 P0/P1/P2 红旗直接变成清仓命令。
- 不用 EBITDA、净利润、每股经营现金流、固定资产变动或研发费用加回替代 FCF；不发明研发资本化、存贷双高或 C/D 周期的新阈值。
- 不创建第二套验证脚本、第二动作出口或持久治理文件；复用 `scripts/check.sh`、现有 JSON payload、`holding_alerts` 和既有决策表。
- 不进行生产安装、生产 DB 读取/写入、cron/配置/凭证/active symlink 改动或自动下单。

## 3. 跨阶段设计与实施纪律

### 3.1 最小模块边界

```text
fetcher.py / market_quotes.py
        │  规范化事实、期间、单位、source、as-of
        ▼
risk_gates.py
        │  纯函数：P0/P1/P2/P3 状态、reason code、action_eligible
        ├──────────────► commands_analysis.py（评分/评级资格）
        └──────────────► commands_holdings.py（冻结加仓/止损候选）
                              │
                              ▼
                 holding_alerts 既有字段（仅 W1 确认后）
```

- `risk_gates.py` 不访问网络、数据库或 stdin/stdout；只接收规范化 dict 和显式时钟，返回 JSON 可序列化 dict。
- `fetcher.py` 负责数据适配、TTM 所需期间选择、单位/符号归一和 provenance，不把缺数变为零。
- `store.py` 只扩展现有 fundamentals JSON 的嵌套校验；不得读取时回填、重算或写回旧缓存。
- `commands_analysis.py` 是评分资格的唯一运行时门；不得在每个 A—F 框架复制阻断逻辑。
- `commands_holdings.py` 只形成一个合并后的监控候选；已有活动 L3 与治理退出条件仍优先。
- `market_quotes.py` 只负责可交易性及市场快照事实，不解释投资动作。

### 3.2 状态、reason code 与聚合

- P0：`clear|blocked|incomplete`；子项额外允许有依据的 `not_applicable`；聚合固定为 `blocked > incomplete > clear`。
- P1：`clear|blocked|incomplete`。
- P2：`clear|blocked|incomplete|review_required|not_applicable`。
- P3：`not_applicable|clear|deferred|untradeable|incomplete`。
- reason code 使用稳定、机器可测的小写 snake_case；展示文本可调整，但测试不得只依赖中文整句。
- 每个门必须输出 `status`、`action_eligible`、`reason_code`、适用期间、`source`/`sources` 和 `as_of`。缺任一完成判定所需证据时 fail-closed。
- 历史缓存缺新字段时使用明确的 `legacy_field_absent`/对应门 `incomplete`，不在读取时猜测或迁移。

### 3.3 写入、状态与唯一动作出口

- 基本面门结果只进入现有 `stock_fundamentals.data` JSON；缓存写入沿用当前入口及确认边界。
- P0/P1/P2 对持仓只生成红色复核候选并冻结新增买入、Tier1 后补仓和 C/D 加仓；只有用户确认具体写入后才可调用既有 W1 `alert-open`。
- P3 的一次性窗口以固定 reason code 存在 `holding_alerts`。`opened_at`/evidence 中的 `defer_started_at` 首次写入后不可被重复运行覆盖，`review_due` 保存带时区 ISO 8601 时刻。
- 未获得 W1 确认或写入失败时，P3 只能返回 `incomplete`/“待持久化”，不得声称 24H 窗口已经可靠启动。
- 所有门只改变资格、复核状态或第二档动作时间；最终动作仍由 `skills/a-stock-monitor/references/decision-table.json` 合并且只输出一个建议。

### 3.4 RED/GREEN 与阶段提交

每个 Phase 必须按以下顺序执行：

1. 记录 base SHA、工作树、测试基线和临时 DB schema 指纹；
2. 先提交/展示能证明旧行为不满足规范的 RED 测试，并记录预期失败；
3. 实现最小 GREEN，不顺带重构无关代码；
4. 跑本 Phase 聚焦测试、全量门禁、schema 对比和 diff review；
5. 冻结一个 bounded commit，记录 commit SHA；
6. 获得下一 Phase 明确授权后再继续。

测试不得连接、读取、哈希或写入生产数据库。所有数据库测试继续使用 `tests/conftest.py` 的临时路径；网络路径全部以 fixture/fake 隔离。

## 4. Phased Roadmap

| Phase | 目标 | 最小落地 | 初始授权状态 | Go 条件 |
|---|---|---|---|---|
| 0 | P0 监管与财报合规前置门 | 法规映射、JSON 合同、Research 前置阻断、Monitor 冻结加仓 | 等待用户明确授权 | P0 RED/GREEN、711 基线不退化、schema 不变 |
| 1 | P1 ROE 结构性恶化门 | 同口径 TTM/5年均值、杜邦解释、估值资格阻断 | 未授权 | Phase 0 已审查且用户批准 Phase 1 |
| 2 | P2 真实 FCF 与 Capex 红线 | CFO/Capex/FCF/Yield、C/D 专项 review 状态机 | 未授权 | Phase 1 已审查且用户批准 Phase 2 |
| 3 | P3 系统性流动性休克延迟 | 全市场快照、一次性 24H、不可交易处理 | 未授权 | Phase 2 已审查且用户批准 Phase 3 |
| 4 | Skill 与 QA 合同对齐 | Research/Monitor 文本、决策表、QA 四项硬门 | 未授权 | Phase 0—3 运行时合同冻结且用户批准 Phase 4 |
| 5 | 集成回归与发布就绪 | 全库回归、独立只读审查、候选发布清单 | 未授权 | Phase 4 通过且用户批准 Phase 5；不含 cutover |

## 5. Phase 0：P0 新国九条 ST 排雷与审计意见合规门

### 5.1 涉及文件

- 新增 `src/a_stock_agent_runtime/risk_gates.py`
- 修改 `src/a_stock_agent_runtime/fetcher.py`
- 修改 `src/a_stock_agent_runtime/store.py`
- 修改 `src/a_stock_agent_runtime/commands_analysis.py`
- 修改 `src/a_stock_agent_runtime/commands_holdings.py`
- 新增 `tests/research/test_risk_gates.py`
- 扩展 `tests/research/test_fetcher.py`
- 扩展 `tests/research/test_framework_scoring_command.py`
- 扩展 `tests/research/test_p0_contracts.py`
- 扩展 `tests/research/test_missing_coverage.py`

Phase 0 不修改 `schema.py`、`schema_ledger.py`、A—F framework 文件或 Skill 文本；文档合同统一留到 Phase 4，避免运行时合同尚未冻结时反复改文案。

### 5.2 Task 0.0：法规映射与数据能力冻结

- 在 `risk_gates.py` 用只读常量固化 `exchange`、`board`、`effective_from`、适用条件、比例/金额双门槛、豁免条件、官方规则 URL 和规则版本；映射至少区分 SSE main/star、SZSE main/chinext、BSE。
- 代码前缀只负责选择板块候选，最终 `clear` 仍要求交易所/板块证据完整；未知或冲突映射为 `incomplete`。
- 开工时只读盘点当前 `a_stock_lib 0.6.3` 和已有 TuShare/AKShare 调用是否已能返回所需官方事实。不得为补能力新增 Provider 或依赖；自动化能力不足的字段保留 `incomplete`，由 Research 按官方公告补证。
- 官方证据只接受交易所/证监会、公司正式公告、年度报告及审计报告；聚合新闻和搜索摘要只能定位原文。

### 5.3 Task 0.1：先写 RED 合同测试

`tests/research/test_risk_gates.py` 先覆盖：

- 主板法定前提均为正且三年累计现金分红同时低于年均净利润 30% 和金额门槛时 `blocked`；任一前提 `<=0` 时分红子门为有依据的 `not_applicable`。
- 比例或金额只命中一个条件时 `clear`；恰好等于边界不阻断，锁定严格“小于”和 AND 逻辑。
- 科创板、创业板研发豁免、上市未满三个完整年度及北交所分别走自身规则，不得套用主板常量。
- ST、`*ST`、退市整理、终止上市分别 `blocked`；分红 ST 不得输出为已退市。
- 财报审计保留/否定/无法表示，内控否定/无法表示/应披未披分别阻断；无保留但含持续经营重大不确定性/强调事项/未更正重大错报为 `incomplete`。
- 公司正式立案为 `blocked`；仅控股股东/实控人/董监高立案且关联未明为 `incomplete`，官方证据明确影响财务真实性、资金占用或核心资格时升级 `blocked`。
- 缺 source/as-of/报告期/规则版本、仅非官方来源、搜索无结果、解除证据不完整都不得 `clear`。
- 聚合优先级固定为 `blocked > incomplete > clear`；`action_eligible=true` 只出现在四个子门都完成的路径。

### 5.4 Task 0.2：GREEN 纯规则实现

- 在 `risk_gates.py` 实现板块识别、分红适用性、四个子门判定和聚合；函数只消费规范化 payload，不直接读网页或数据库。
- 输出结构严格匹配 spec 的 `regulatory_gate`，包含各子门 reason code、分红 preconditions、规则版本与 sources。
- `not_applicable` 只允许分红子门在法定条件确实不适用时使用；缺数字段绝不能借此通过。
- 不建立配置文件或规则解释器。规则变化只能由新 dated spec、常量 diff 和回归测试更新。

### 5.5 Task 0.3：数据源与缓存 JSON 扩展

- `fetcher.py` 的 `FIELDS`、payload builder 和 provenance 生成加入嵌套 `regulatory_gate`；可从当前结构化能力取得的事实必须保留原始 source/as-of/report period，不能只存最终布尔值。
- 自动采集拿不到正式状态、审计正文、立案公告或板块分红前提时，生成字段完整的 `incomplete` 门；不得用证券简称或“未找到负面”判 `clear`。
- `store.validate_fundamentals_payload` 校验嵌套门的字段类型、合法状态、source/as-of 和 `action_eligible` 一致性。旧缓存缺门时读取为 `legacy_field_absent`，不回填、不写回。
- `tests/research/test_fetcher.py` 用 fixture 证明官方字段原样进入 payload、非官方来源不能变成 clear、缺证据仍可保存明确 incomplete、JSON round-trip 不丢 provenance。
- `tests/research/test_p0_contracts.py` 证明 `PRAGMA user_version`、`sqlite_master` 和列清单不变。

### 5.6 Task 0.4：Research 评分前置阻断

- `commands_analysis.py::cmd_score_fundamentals` 在调用 `a_stock_lib.framework_scoring.score_fundamentals` 前统一读取 P0 门；`blocked/incomplete` 时不得调用 scorer，输出 `scoring_status=incomplete`、`action_eligible=false`、基本面小计/配置评级/时机评级/总分/矩阵 `not_formed` 和稳定 reason code。
- `cmd_set_analysis` 对相同门沿用现有 `scoring_status=incomplete`：允许保存不带得分的审计报告，但拒绝带完整 score 或 stale breakdown 的写入；不得新增 scoring status 枚举。
- P0 `clear` 时传给 `a_stock_lib` 的 metrics 必须与基线一致，已有 A—F 分值逐值不变。
- `tests/research/test_framework_scoring_command.py` 用 spy 断言 P0 未通过时 scorer 调用次数为 0；clear 时调用一次且结果与基线一致。
- `tests/research/test_p0_contracts.py` 断言 incomplete 分析清除不一致 score breakdown，`set-score` 不能补写完整总分。

### 5.7 Task 0.5：Monitor 冻结加仓与候选合并

- `commands_holdings.py::cmd_check_holdings` 读取持仓对应 fundamentals 中的 P0 门。`blocked/incomplete` 输出红色治理/合规复核候选与“冻结新增买入、Tier1 后补仓、C/D 加仓”，但不得自动写 alert、卖出或清仓。
- 已确认活动 L3/治理退出仍按原优先级；P0 只作为复核门进入一个合并后的输出，不得与既有价格/Tier 同时给冲突动作。
- 用户确认具体预警内容后才能通过既有 `commands_monitor.py::cmd_alert_open` 写入；W1 缺失仍返回 3 且数据库不变。
- `tests/research/test_missing_coverage.py` 断言 blocked/incomplete 都冻结加仓、clear 不改变原路径、P0 不生成卖出股数、活动 L3 不被 P0 覆盖。

### 5.8 Phase 0 门禁

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider \
  tests/research/test_risk_gates.py \
  tests/research/test_fetcher.py \
  tests/research/test_framework_scoring_command.py \
  tests/research/test_p0_contracts.py \
  tests/research/test_missing_coverage.py
git diff --check
bash scripts/check.sh
```

Go 条件：P0 聚焦测试和全库门禁全绿；测试数不低于 711；P0 clear 路径的既有评分不变；临时 DB schema 指纹与基线完全一致；diff 只含上述 Phase 0 文件。否则 No-Go，停在 Phase 0。

## 6. Phase 1：P1 ROE 结构性恶化阻断器

### 6.1 涉及文件

- 修改 `src/a_stock_agent_runtime/risk_gates.py`
- 修改 `src/a_stock_agent_runtime/fetcher.py`
- 修改 `src/a_stock_agent_runtime/store.py`
- 修改 `src/a_stock_agent_runtime/commands_analysis.py`
- 修改 `src/a_stock_agent_runtime/commands_holdings.py`
- 扩展 `tests/research/test_risk_gates.py`
- 扩展 `tests/research/test_fetcher.py`
- 扩展 `tests/research/test_framework_scoring_command.py`
- 扩展 `tests/research/test_latest_report_snapshot.py`
- 扩展 `tests/research/test_missing_coverage.py`

### 6.2 Task 1.0：RED 数据构造测试

- 用“最近完整年报 + 当期累计 - 上年同期累计”fixture 分别构造 TTM 归母净利润、营业收入和需要的平均资产/归母净资产；禁止把单季/半年 ROE 乘 4/2。
- 五年基线必须恰为 TTM 截止日前最近五个完整会计年度、同一口径、去重后的重述值。少于五年、重复期、单位冲突、非有限值、口径无法对齐为 `incomplete`。
- 覆盖 `latest=12`、`mean=16` 恰好 0.75 为 clear，未取整值略低于 0.75 为 blocked。
- 最新 ROE 为负时，无论五年均值为正、零或负都 blocked；不得因负数相除放行。最新非负且均值 `<=0` 时为 incomplete。

### 6.3 Task 1.1：GREEN ROE 与杜邦实现

- `fetcher.py` 在 TuShare 既有 indicator/income/balance 历史结果上保留 TTM 三期间和最近五个完整年度；重述去重沿用 `_deduplicated_report_rows`，不增加第二套去重器。
- `risk_gates.py` 计算 `latest_roe_ttm`、`roe_5y_mean`、未取整 `roe_retention_ratio` 和固定 threshold `0.75`。
- 同口径计算 net margin、asset turnover、equity multiplier 的当前值、五年均值和 `up|flat|down|incomplete`。杜邦只解释方向，不产生阈值或豁免。
- ROE 已足以 blocked 时，杜邦任一分项缺失只让该解释项 incomplete，不恢复主门。
- 输出保存五个年度及报告期、TTM 构造期间、source/as-of 和稳定 reason code；`store.py` 做结构校验与旧缓存 fail-closed。

### 6.4 Task 1.2：估值资格与持仓冻结

- `commands_analysis.py` 对 P1 blocked/incomplete 设置 `timing_status=incomplete`、`action_eligible=false`，屏蔽 PE/PB/PS 历史分位形成低估结论、买入/加仓矩阵；基本面机械分只可作为 diagnostics 展示。
- 不改 A—F scorer；P1 clear 时所有原评分输入和输出逐值不变。
- `commands_holdings.py` 把 P1 blocked/incomplete 合并为结构性盈利能力红色复核候选，冻结 Tier1 后补仓及其他加仓，不自动减仓/退出。
- RED/GREEN 断言低 PE/PB/PS 分位不能绕过 P1，活动 L3/既有价格止损仍决定卖出路径，`0.75` 边界无舍入漂移。

### 6.5 Phase 1 门禁

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider \
  tests/research/test_risk_gates.py \
  tests/research/test_fetcher.py \
  tests/research/test_latest_report_snapshot.py \
  tests/research/test_framework_scoring_command.py \
  tests/research/test_missing_coverage.py
git diff --check
bash scripts/check.sh
```

Go 条件：TTM、五年重述、负值、0.75、杜邦缺项及低估值阻断全部通过；P0 回归不变；schema 指纹不变。

## 7. Phase 2：P2 真实自由现金流与资本开支红线

### 7.1 涉及文件

- 修改 `src/a_stock_agent_runtime/risk_gates.py`
- 修改 `src/a_stock_agent_runtime/fetcher.py`
- 修改 `src/a_stock_agent_runtime/store.py`
- 修改 `src/a_stock_agent_runtime/commands_analysis.py`
- 修改 `src/a_stock_agent_runtime/commands_holdings.py`
- 扩展 `tests/research/test_risk_gates.py`
- 扩展 `tests/research/test_fetcher.py`
- 扩展 `tests/research/test_framework_scoring_command.py`
- 扩展 `tests/research/test_checklist.py`
- 扩展 `tests/research/test_missing_coverage.py`

### 7.2 Task 2.0：RED CFO/Capex/FCF 测试

- CFO 只取合并现金流量表 `n_cashflow_act` 对应项；Capex 只取购建固定资产、无形资产和其他长期资产支付的现金，适配层统一为正流出一次。
- CFO 与 Capex 分别以同一组三期间构造 TTM。缺最近年报/当期累计/上年同期累计任一项、混用期间、单位不一致或非有限值都 incomplete。
- 非 C/D fixture：`CFO=100, Capex=40 → FCF=60`；`Capex=100 → FCF=0/non_positive` 且不得误报 exceeded；`Capex=100.01` 严格 breached。
- 覆盖 CFO `=0`、`<0`，Capex 源正/负号，FCF 负值，总市值缺失/为零/非总市值、quote as-of 不一致。
- FCF Yield 必须使用同一 quote as-of 的正总市值；缺市值时 FCF 仍展示而 Yield incomplete。
- 资本化研发已包含 Capex 时只扣一次；受限资金、货币资金和有息负债只展示。

### 7.3 Task 2.1：GREEN 构造与一般红线

- `fetcher.py` 复用当前 cashflow/income/balance/dividend frame，新增 TTM CFO、TTM Capex、TTM cash dividends 和正式证据 provenance；把 `_fetch_spot_data` 已取得的总市值按明确单位归一后与 quote as-of 一起写入 payload。
- `risk_gates.py` 计算 FCF、FCF Yield、`capex_to_cfo`、`cash_generation_redline` 与 `capex_redline`；门禁比较使用未取整值。
- 非金融、非 C/D：CFO `<=0` 必须 blocked；CFO>0 且 Capex>CFO blocked；FCF=0 不得获得正向评价，但只有规范定义的 redline 才标 blocked。
- 银行/证券/保险使用有证据的 `not_applicable`，不得影响 B 专属指标；框架/行业无法确定时 incomplete，不猜金融豁免。

### 7.4 Task 2.2：C/D `review_required` 状态机

- 仅在 framework 明确为 C/D、CFO>0 且 Capex>CFO 时进入 `review_required`，不得自动 blocked 或 clear。
- 专项评估必须同时具备：既有第 1.5 步周期标签、正式披露支持的 C 扩产/并购或 D 建设期资本开支类型、对应 C/D 分红压力测试、同一 TTM 的实际现金分红、`cash_dividend_coverage`、`fcf_dividend_coverage`、完整 source/period/as-of。
- TTM cash dividends=0 且有正式事实证据时 coverage 为 `not_applicable`；无正式证据仍 incomplete。
- `cash_dividend_coverage <1` 或证据显示非专属周期为 blocked；字段缺失为 incomplete；全部完成且 coverage≥1 才将 `cd_capex_review=clear`、`capex_redline=reviewed_cycle`、总门 clear。
- C/D 的 CFO<=0 永远 blocked；专项评估不得覆盖 P0/P1、原 C/D 红线或活动 L3。

### 7.5 Task 2.3：评分与 Monitor 后果

- 非 C/D blocked/incomplete 及 C/D review_required/incomplete 都令 `scoring_status=incomplete`、`action_eligible=false`，停止配置评级、时机评级、总分和矩阵。
- 只有 C/D 专项评估 clear 且其他门 clear 才恢复资格；负 FCF 原值继续披露且不能获得正向 FCF 评价。
- Monitor 对所有 P2 未通过/待审状态冻结新增买入和补仓，生成现金流质量红色复核候选；不把负 FCF 直接转为清仓。
- `tests/research/test_checklist.py` 证明既有 `operating_cf_per_share`/经营现金流质量项未被冒充为 FCF，也未改原权重。

### 7.6 Phase 2 门禁

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider \
  tests/research/test_risk_gates.py \
  tests/research/test_fetcher.py \
  tests/research/test_framework_scoring_command.py \
  tests/research/test_checklist.py \
  tests/research/test_missing_coverage.py
git diff --check
bash scripts/check.sh
```

Go 条件：一般红线、金融不适用、C/D 五条件专项状态机、FCF Yield 口径和“不自动清仓”全部通过；P0/P1 回归与 schema 指纹不变。

## 8. Phase 3：P3 极端系统性流动性休克延迟执行

### 8.1 涉及文件

- 修改 `src/a_stock_agent_runtime/risk_gates.py`
- 修改 `src/a_stock_agent_runtime/market_quotes.py`
- 修改 `src/a_stock_agent_runtime/domain.py`
- 修改 `src/a_stock_agent_runtime/commands_holdings.py`
- 修改 `src/a_stock_agent_runtime/commands_monitor.py`
- 新增 `tests/monitor/test_liquidity_shock.py`
- 扩展 `tests/research/test_missing_coverage.py`
- 扩展 `tests/research/test_edge_cases.py`
- 扩展 `tests/test_cli_contract.py`
- 扩展 `tests/test_command_classification.py`

### 8.2 Task 3.0：市场快照与个股可交易性 RED 测试

- 市场快照 fixture 显式包含 `limit_down_count`、universe、eligible count、coverage/status、source、as-of 和是否收盘最终快照。
- 跌停统计只包括沪深京正常设有当日跌停价且最新成交价等于跌停价的 A 股；停牌和无涨跌幅限制证券不进分母。不得用指数跌幅、跌幅>9%或情绪标签替代。
- 盘中快照同交易日且年龄 `<=120s` 才可作为完整快照；跨日、超过 120s、缺 universe/eligible/source/as-of 均 incomplete。收盘后仅接受当日最终快照。
- 完整 500 不延迟、501 延迟；不完整快照已确认 501 可按下界延迟，不完整且 500 只能 incomplete。
- 个股快照缺 `suspended`、`limit_down_locked`、`trading_status`、price、quote as-of 或 source 任一影响判定字段时 incomplete。

### 8.3 Task 3.1：最小行情适配

- `market_quotes.py` 在现有依赖能力内增加市场跌停快照和个股可交易性结构；不得新增 Provider/dependency。实际数据能力不能满足同一时点、全市场和跌停价字段时返回 incomplete，不实现近似口径。
- 扩展 `PriceQuote` 时新增字段必须有兼容默认值，现有三位置参数构造和旧调用保持通过；只有 P3 动作资格要求完整新字段。
- `domain.py` 保留既有第一/第二档价判断，调用 `risk_gates.py` 的 P3 纯状态机；不得硬编码成本×80%，必须读取持仓 `stop_loss_20` 实值。

### 8.4 Task 3.2：24H 一次性状态机 GREEN

- 第二档未触发且个股价格有效时 `not_applicable`；价格无效时 incomplete。
- 第二档触发且有效 count<=500：可交易为 clear；停牌/一字跌停锁死为 untradeable；字段不全为 incomplete，后两者不得输出卖出股数。
- count>500 时形成 deferred 候选，记录 `defer_started_at`、原价格/第二档线、原市场快照和 `review_due=+24h`，Asia/Shanghai 自然时钟计算。
- `review_due` 前禁止第二档价格止损卖出股数；活动 L3、监管事实和其他高优先级门照常核验。
- 恰好到期允许复核；周五触发、周末到期，在周一首个有效交易快照处理。
- 到期后：新鲜可交易价高于第二档线才解除候选；仍 `<=` 第二档线才恢复原目标减仓 50% 路径。停牌/锁死/无流动性/报价无效保持 untradeable/incomplete；市场仍 501 家也不得新开或续延窗口。

### 8.5 Task 3.3：复用 `holding_alerts` 持久化

- 使用固定 reason code（例如 `price_stop2_liquidity_defer`）定位同一活动 alert；evidence 保存版本化 JSON，包含 `defer_started_at` 和原快照。不得改 `holding_alerts` schema。
- `commands_monitor.py::cmd_alert_open` 仅做兼容性最小扩展：`review_due` 接受原 `YYYY-MM-DD` 或带时区 ISO 8601；已有 date 调用不变。
- 重复运行/进程重启读取首次 `defer_started_at`；upsert 不覆盖起点。若活动 alert 已存在，只更新可变复核证据，不重置窗口。
- `check-holdings` 仍为 R0，只输出待持久化候选；只有用户确认后通过 `a-stock-cache --confirm-write alert-open ...` 写入。缺确认返回 3，失败时状态不得显示为可靠 deferred。
- alert 解除必须有到期后的新鲜、可交易报价证据；不允许无价格解除、伪造成交或写交易账本。

### 8.6 Task 3.4：优先级、全框架止损与 RED/GREEN

`tests/monitor/test_liquidity_shock.py` 必须断言：

- 500/501、完整/不完整快照、120 秒、跨日和收盘最终快照边界；
- 24H 前、恰好 24H、周末、首个有效交易快照；
- 恢复、仍跌破、停牌、一字跌停、无流动性、无效报价；
- 重复运行与重启不重置，持续 501 不续延，W1 未确认/持久化失败不声称已记录；
- P3 不作用于第一档、活动 L3、P0 监管事实、Tier 止盈和已成交事件；
- A/E、B/D、C、F 全部读取各自持仓第二档实值，现有可申报股数与目标减仓 50% 不变；
- 最终只产生一个合并建议，停牌/封板不输出卖出股数或成交事件。

### 8.7 Phase 3 门禁

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider \
  tests/monitor/test_liquidity_shock.py \
  tests/research/test_missing_coverage.py \
  tests/research/test_edge_cases.py \
  tests/test_cli_contract.py \
  tests/test_command_classification.py
A_STOCK_NOTIFY_MODE=disabled bash tests/test_check_holdings_cron.sh
git diff --check
bash scripts/check.sh
```

Go 条件：状态机边界、一次性持久化、不可交易 fail-closed、全框架实值和唯一动作出口均通过；P0—P2 回归、W1 分类和 schema 指纹不变。

## 9. Phase 4：Skill 合同与 QA 验证对齐

### 9.1 涉及文件

- 修改 `skills/a-stock-research/SKILL.md`
- 修改 `skills/a-stock-research/references/data-cache-contract.md`
- 修改 `skills/a-stock-research/references/research-execution-flow.md`
- 修改 `skills/a-stock-research/references/timing-adjustments.md`
- 修改 `skills/a-stock-research/references/report-contract.md`
- 修改 `skills/a-stock-research/references/frameworks/C.md`
- 修改 `skills/a-stock-research/references/frameworks/D.md`
- 修改 `skills/a-stock-monitor/SKILL.md`
- 修改 `skills/a-stock-monitor/references/daily-monitoring-and-l3.md`
- 修改 `skills/a-stock-monitor/references/step3.5-cd-accumulation.md`
- 修改 `skills/a-stock-monitor/references/step4-tier-system.md`
- 修改 `skills/a-stock-monitor/references/data-operations.md`
- 修改 `skills/a-stock-monitor/references/decision-table.json`
- 修改 `skills/a-stock-qa/references/rubrics/a-stock-research.md`
- 修改 `tests/research/test_research_skill_progressive_disclosure.py`
- 修改 `tests/monitor/test_skill_contract.py`
- 修改 `tests/qa/test_qa_contract.py`
- 修改 `tests/qa/standalone_smoke.py`

只修改确实承载四门合同的文件；全仓检索确认无消费者时，删除上表中无需改动的候选文件，禁止为了“文档齐全”机械触碰全部框架。

### 9.2 Task 4.0：Research 文本合同

- 主 Skill 保留四门的顺序、状态、动作边界和 fail-closed 摘要；数据字段、公式、完整 JSON 示例放入现有渐进披露 reference，避免主文件重复。
- 明确执行顺序：持仓路由 → fetch/check → P0 → P1 → P2 → 原 A—F 评分 → 择时/矩阵；P0/P2 未通过停止全部评分，P1 仅让历史估值分位失去动作资格。
- 报告合同必须输出四门状态、reason code、source/as-of、`action_eligible`、适用的 `not_formed`，并保持最新报告冲突、PB/BPS 兼容门和原评分语义。
- C/D reference 只增加 P2 专项评估所需的现有周期/资本开支事实/分红压力与覆盖字段，不调整框架分值。

### 9.3 Task 4.1：Monitor 文本与决策表

- 日常监控检查表加入 P0/P1/P2 冻结加仓和 P3 第二档延迟，但仍保持 C01—C10 唯一清单；不得另建平行清单。
- `decision-table.json` 保持 schema_version 兼容，增加/调整最少规则表达固定优先级：活动 L3/治理退出 → P0/P1/P2 风险复核 → P3 包装的第二档止损 → Tier/估值/加仓。
- P3 文本必须明确 500/501、120 秒、24H、周末、一次性窗口、untradeable/incomplete、持仓第二档实值和 W1 持久化边界。
- `data-operations.md` 只记录复用 `alert-open/resolve` 的标准 reason code、evidence JSON 和确认命令，不引入新 CLI。

### 9.4 Task 4.2：QA rubric 四大硬门

在现有 Research rubric 中增加四项 Critical/Important 检查，不创建第二 rubric：

1. 事实与官方来源完整性：P0 四子门、P2 资本开支/分红、市场快照来源与 as-of；“未搜到负面”不得通过。
2. 公式与边界复算：P0 双门槛 AND、P1 TTM/五年/0.75/负值、P2 FCF/Yield/Capex、P3 500/501/24H。
3. 状态与动作一致性：blocked/incomplete/review_required 对评分、加仓、第二档止损的后果；活动 L3 优先且只有一个动作出口。
4. 缺数 fail-closed：缺 evidence/source/as-of/期间/可交易字段不得 clear 或形成股数。

QA 仍只检查不可变报告文本，不调用 runtime、不访问行情、不验证外部事实真实性；`COMPLIANT` 只表示报告合同合规。完整正文缺失/快照漂移仍为 `INVALID_RUN`，非 Research 类型继续按现有规则 SKIP。

### 9.5 Task 4.3：静态合同测试

- Research 测试锁定四门顺序、状态枚举、字段、not_formed 与唯一操作出口。
- Monitor 测试锁定决策表 id/priority 唯一、P3 只包装 D04 第二档、冻结加仓不自动卖出、交易仍需用户确认和可申报股数。
- QA 测试分别提供四门合规/不合规片段，断言 Critical/Important 汇总、Advisory 不影响 verdict、standalone `python3 -I` 无 runtime 依赖。
- 全仓 `rg` 确认不存在“ST=退市”“立案=违法成立”“C/D Capex>CFO 自动通过/自动阻断”“P3 可续延”“固定成本×80%”等冲突措辞。

### 9.6 Phase 4 门禁

```bash
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider \
  tests/research/test_research_skill_progressive_disclosure.py \
  tests/monitor/test_skill_contract.py \
  tests/qa/test_qa_contract.py
python3 -I tests/qa/standalone_smoke.py
uv run python scripts/validate.py
git diff --check
bash scripts/check.sh
```

Go 条件：Research/Monitor/QA 对同一状态、边界和优先级无冲突；QA 独立运行；三个 Skill 仍 portable/client-neutral；P0—P3 runtime 回归全绿。

## 10. Phase 5：全库集成回归、独立审查与发布就绪

### 10.1 集成 fixture 与不变量

- Research 集成 fixture：P0 前置停止、P1 只使历史分位失效、P2 一般硬阻断、C/D review_required→clear/blocked，以及四门 clear 时原 A—F 得分逐值不变。
- Monitor 集成 fixture：P0/P1/P2 冻结加仓、P3 一次性延迟、活动 L3 高优先级、Tier/估值低优先级、停牌/封板不伪造成交。
- 回归现有 PB/BPS `valuation_compatibility`、最新报告冲突门、A—F 分数、Tier1 +25%、L3 语义门、交易所可申报股数、W1 前置 flag、cron 禁通知 smoke。
- 临时 DB 在实现前后比较 `PRAGMA user_version`、`sqlite_master` 表/索引和每表 `PRAGMA table_info`，必须完全一致。
- 用 `git status --short`、版本文件、安装入口和配置路径确认没有生产状态、凭证、报告、锁或 DB 进入仓库。

### 10.2 独立只读审查

冻结 candidate HEAD 与完整 diff 后，执行一次独立、只读、不可修改文件的审查。审查至少检查：

- spec 每条 MUST/不得是否有代码或测试证据；
- 监管缺数是否可能判 clear，分红双门槛是否误成 OR；
- P1 负 ROE/0.75/重述期间和 P2 符号/单位/C/D 豁免是否可绕过；
- P3 是否能重置/续延窗口，停牌或锁死是否会输出股数，是否硬编码 80%；
- 是否产生第二动作出口、评分/Tier/止损阈值漂移、schema 或依赖变化；
- `src/`/Skill/QA 合同是否一致。

以下任一 finding 为 release blocker：评分或阈值漂移、P3 无限续延、负 FCF 被叙事豁免、监管缺数判 clear、ST/立案错误定性、不可交易时伪造成交、第二动作出口、schema 变化、新生产依赖或 QA 失去 `python3 -I` 独立性。

### 10.3 发布就绪而非生产发布

- 形成 candidate commit 清单、每 Phase base/head SHA、测试结果、schema 对比、独立审查 verdict 和已知限制。
- 仅在现有发布文档确需记录候选变化时，更新 `docs/CHANGELOG.md`；不得提前改版本、打 tag、构建/安装生产 runtime 或切 active client。
- 若审查通过，状态为“release ready / awaiting cutover authorization”。生产 cutover 必须另行提出包含版本、installer、回读、回滚和状态指纹的明确请求。

### 10.4 Phase 5 全量验证

```bash
git rev-parse --short HEAD
git status --short
PYTHONDONTWRITEBYTECODE=1 uv run pytest --collect-only -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 uv run pytest -q -p no:cacheprovider
uv run ruff check .
uv run python scripts/validate.py
python3 -I tests/qa/standalone_smoke.py
A_STOCK_NOTIFY_MODE=disabled bash tests/test_check_holdings_cron.sh
git diff --check
bash scripts/check.sh
```

若 `scripts/check.sh` 已包含重复命令，以它为最终编排真源，不创建新的长期验证器。独立审查只读，不运行 formatter、installer、生产命令或任何写入外部状态的工具。

## 11. 验证命令与基线记录

### 11.1 每阶段共同命令

```bash
git rev-parse --short HEAD
git status --short
PYTHONDONTWRITEBYTECODE=1 uv run pytest --collect-only -q -p no:cacheprovider
git diff --check
bash scripts/check.sh
```

### 11.2 Schema 不变验证（仅临时数据库）

开工前在测试临时 DB 导出：

- `PRAGMA user_version`；
- `SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name`；
- 每张表 `PRAGMA table_info(<table>)` 与 `PRAGMA index_list(<table>)`。

每个 Phase GREEN 后用同一脚本/测试 fixture 重新生成并逐值比较。不得将真实生产 DB 路径、hash、内容或 schema dump 用作测试门禁。

### 11.3 关键静态检索

```bash
rg -n 'regulatory_gate|roe_structural_gate|cash_flow_gate|liquidity_shock' src tests skills
rg -n 'score_fundamentals|stop_loss_20|holding_alerts|review_due' src tests skills
rg -n 'ATR|波动率|Regime Filter|成本.*0\.80|自动清仓' src skills
git diff -- src/a_stock_agent_runtime/schema.py src/a_stock_agent_runtime/schema_ledger.py pyproject.toml uv.lock
```

最后一条预期为空；若不为空立即 No-Go，并按停止条件处理。

## 12. 独立回滚策略

| Phase | 回滚单元 | 回滚后验证 | 不得触碰 |
|---|---|---|---|
| 0 | revert P0 bounded commit | P0 前字段按 legacy 缺失处理；基线全量测试与 schema 对比 | 生产 fundamentals、持仓、active Skill |
| 1 | revert P1 commit | P0 保留；原评分结果恢复；P1 新字段不再消费 | P0 commit、a-stock-lib |
| 2 | revert P2 commit | P0/P1 保留；原 CFO checklist 行为恢复 | 交易账本、schema、C/D 原阈值 |
| 3 | revert P3 commit | 原第二档行为恢复；已有测试临时 alert 清理随临时 DB 丢弃 | 生产 alert、持仓、成交事件 |
| 4 | revert Skill/QA commit | runtime P0—P3 保留；Skill 文本回到上个合同版本 | active client/安装目录 |
| 5 | revert 集成/发布文档 commit | Phase 0—4 实现不变 | tag、生产 runtime、cron |

回滚只使用非破坏性的 `git revert <phase-commit>`；不使用 reset/rebase，不删除或改写生产持仓、预警、交易事件和历史审计记录。若任何 Phase 尚未提交，直接停止并保留 diff 供审查，不以清理用户工作树为名删除内容。

P3 若未来已经在生产形成一次性 alert，代码回滚不自动删除该审计事实；必须由用户对具体 reason code 和解除证据另行确认后，走既有 W1 `alert-resolve`。

## 13. 风险登记、停止条件与 Go/No-Go

| 风险 | 强制控制 / Go 条件 |
|---|---|
| 官方事实不可自动取得 | 保持 incomplete；不得用聚合源或“未搜到”补 clear |
| 板块法规误套 | 版本化 exchange/board fixture；主板、科创、创业、北交分别测试 |
| 新门改变 A—F 分数 | clear 路径 golden/逐值对比；不修改 a-stock-lib |
| 旧缓存被默认为通过 | `legacy_field_absent`→incomplete；读取不回填 |
| TTM 期间或单位混用 | 三期间 provenance、重述去重、非有限值与单位冲突测试 |
| C/D 叙事豁免负 FCF | review_required 五条件齐备；CFO<=0 永不豁免 |
| P3 无限续延 | 首次 `defer_started_at` 不变；持续 501 和重启测试 |
| 停牌/封板伪造成交 | untradeable/incomplete 不输出股数、不写交易事件 |
| R0 静默写状态 | check-holdings 只形成候选；W1 前置确认和无写测试 |
| Schema/依赖漂移 | 每 Phase schema 指纹；`schema.py`/`pyproject.toml`/`uv.lock` diff 为空 |
| Skill 与 runtime 语义冲突 | Phase 4 静态合同 + Phase 5 集成审查 |
| 回归难定位 | 每 Phase 单独 commit、单独门禁、单独 revert |

出现以下任一情况立即停止，不扩大范围，并请求新的明确授权：

- 需要新增数据库表/列/index/migration 或改变 `user_version`；
- 需要新增 Provider、生产依赖、外部服务或修改 `a-stock-lib`；
- 需要改 A—F 分值、Tier、L3、止损价/比例、交易确认或可申报股数；
- 数据源无法满足官方来源、同口径、同一快照或可交易性要求；
- 需要用主观宏观判断、ATR、波动率或拟合参数代替规范客观门；
- 聚焦测试或全量门禁不能恢复绿色，或临时 DB schema 与基线不一致；
- 实际所需文件明显超出本 Phase 列表并形成架构/发布范围变化。

## 14. 交付节奏与授权点

推荐节奏为六个可审查批次：

1. Phase 0：P0 运行时硬门与聚焦测试；
2. Phase 1：P1 ROE/杜邦与估值资格；
3. Phase 2：P2 FCF/C/D 专项状态机；
4. Phase 3：P3 市场快照与 24H 一次性延迟；
5. Phase 4：Research/Monitor/QA 文本合同；
6. Phase 5：集成回归、独立只读审查和 release-ready 证据。

每批次交付：bounded diff、聚焦 RED/GREEN 证据、`bash scripts/check.sh` 结果、schema 不变证据、phase commit SHA、独立回滚命令和下一阶段 Go/No-Go 建议。## Implementation ledger\n\n| Phase | 状态 | 落地证据 |\n|---|---|---|\n| 0 | complete | `risk_gates.py` P0、fundamentals JSON、评分/持仓冻结、回归测试 |\n| 1 | complete | TTM/五年 ROE、杜邦诊断、估值动作资格门、边界测试 |\n| 2 | complete | CFO/Capex/FCF、金融不适用、C/D 专项 review、边界测试 |\n| 3 | complete | 市场快照校验、一次性24H状态机、可交易性保护、P3测试 |\n| 4 | complete | Research/Monitor/QA 合同与唯一决策表更新 |\n| 5 | complete | 731 tests、Ruff、standalone smoke、`scripts/check.sh` 全绿 |\n\n运行时四门均收敛于 `src/a_stock_agent_runtime/risk_gates.py`，状态仅写入既有 JSON/`holding_alerts` 字段；`schema.py`、`schema_ledger.py`、`pyproject.toml`、`uv.lock` 未修改。
