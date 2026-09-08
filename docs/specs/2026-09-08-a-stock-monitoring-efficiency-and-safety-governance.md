# A股持仓日常监控效率与安全治理规范

日期：2026-09-08
状态：治理文档定稿；不授权实现、部署、账本写入或交易
适用仓库：`/home/lin/a-stock-agent-skills`
基线：`eb28c25334e2e60d44500b5c88ec997c7f64b970`

## 1. 背景

一次无已确认交易触发的五股午盘复查耗时约 25 分钟。审计表明，主因不是计算量，而是工作流扩大：

- 日常动作判断扩展为 C01—C10 全量深度审计；
- 行情与宏观子任务超出最低充分证据范围；
- 父级和子级重复取行情；
- required 与 optional 任务放入同一 wait-all 批次；
- 已足够支持“不交易”的证据出现后仍继续等待；
- 投资任务与其他主题共用长会话。

治理目标是保留现有投资安全边界，同时让无触发路径尽早给出最低充分结论。

## 2. 目标与非目标

### 2.1 目标

1. 无触发日常监控在 5—8 分钟内给出首个可执行结论；稳定后以 P95 ≤5 分钟为目标。
2. 当前持仓、历史记录、账户分母和报价完整性保持可审计。
3. 每类数据只指定一个 owner；首结果有效时禁止重复采集。
4. 缺数、过期或冲突时 fail-closed，不把“不知道”写成“未触发”。
5. 任何输出均为建议或候选；交易、账本及结构化状态写入继续要求用户明确确认。

### 2.2 非目标

- 不新建第二个“快速监控”技能；
- 不引入新服务、队列、通用规则引擎或新依赖；
- 不自动下单、清仓、加仓或修改持仓账本；
- 不删除历史平仓、分红、费用或公司行动事件；
- 不把日常持仓检查扩展为用户未请求的选股、加仓或再平衡扫描；
- 不用天气或其他任务承担投资上下文。

## 3. 不可削弱的安全不变量

1. 当前组合只消费 `exit_date IS NULL` / `holdings --active-only`；历史记录只用于审计。
2. 正式组合占比和风险预算必须使用显式账户总资产。分母缺失时不得判断“正常/超预算”。
3. 报价不完整时只报告“已取价股票仓位（下限）”及覆盖率，不能声称完整市值。
4. 技术、估值、价格、公告和 L3 信号必须区分“启动复核”“已确认条件”“允许性动作”“观察预警”。
5. `trade_candidate` 不是交易授权；用户确认、重新取价、交易所股数校验和成交后记账仍是独立步骤。
6. 日常快照只能读取本地投资状态，不得执行迁移、隐式建库、缓存写入、alert/L3/Tier 写入或交易账本写入。

## 4. 技能层治理

### 4.1 单一技能、两级路由

继续由 `a-stock-monitor` 作为唯一 Primary Skill。新增路由合同，不复制领域规则。

**Level 1：日常快速门禁（默认）**

必需证据：

- 当前 active 持仓及框架、实际第一/第二档线；
- 显式账户总资产和现金（若任务需要组合判断）；
- 一次批量取得的全部当前持仓行情及时间；
- active/pending alerts 与活动 L3 的到期/待核验状态；
- P0—P3 风险门现态；
- 报价覆盖率、分母状态和数据缺口。

Level 1 只回答：是否存在硬触发、异常弱势、到期复核、数据阻塞或动作候选。

**Level 2：触发式深度复核**

仅在以下至少一项成立时，对相关持仓和相关原因扩展证据：

- 触及第一档或第二档价格线；
- 单日跌幅 ≥3%，或弱于行业 ≥2 个百分点；
- active/pending alert 到期；
- L3 到达复核日、出现相关重大公告，或活动条件接近/确认触发；
- 估值、Tier、技术或论文规则达到既有复核入口；
- 数据冲突可能改变动作；
- 用户明确要求详细审计、寻找加仓机会或组合再平衡。

深度复核仍按现有 C01—C10 与对应 reference 执行；路由只改变何时加载，不改阈值和动作语义。

### 4.2 停止合同

若 active 持仓一致、required 数据完整且新鲜、无硬触发、无异常波动、无到期复核、无冲突，则立即输出：

- `action_status=no_action`；
- 异常项为空；
- 关键数据时间和覆盖率；
- 停止原因 `clean_fast_gate`。

随后停止，不得为了丰富报告继续抓取宏观、热点、逐股新闻、全量估值或历史材料。

**是否仍有现金或风险容量不影响停止。** 持仓监控不是选股扫描；只有用户显式要求寻找加仓机会/再平衡，或已有规则要求复核新增风险时，才进入相应路径。

若 required 数据缺失、过期或冲突，则不得输出 clean/no-action 结论；应转为 `review_status=blocked|review_required` 并列明最小补数动作。

### 4.3 required 与 optional

**required：** active 持仓、账户分母、行情及时间、实际止损线、活动 alerts/L3、覆盖率和风险门。
**optional：** 未发生新发布且不改变动作的宏观数据、无异动股票的逐股新闻、全量历史估值、与当前门禁无关的旧材料。

optional 失败、超时或尚未返回，不得阻塞已具备的首轮结论。

### 4.4 数据 owner 与复采规则

- 每类数据在一次运行中只有一个 owner；
- 行情按全部 active 代码一次批量请求；
- 只有首结果失败、不完整、过期或来源冲突时允许一次明确记录原因的 fallback；
- 父级已取行情时不得再委托行情子代理，反之亦然；
- 宏观证据只有在官方发布更新、缓存缺失/失效或确实可能改变动作时刷新；
- 同一公告在官方入口成功后不再聚合搜索。

### 4.5 子代理与调度

- 无触发快速路径默认不启动研究子代理；
- 子代理只处理一个边界清楚的公开证据任务，不读取账户状态，不作最终交易判断；
- required 通道需要尽早消费时分别派发，不放入与 optional 相同的 wait-all 批次；
- required 证据齐备即允许首轮交付；未使用的 optional 任务应取消或忽略，不再阻塞。

### 4.6 会话隔离

投资监控、天气、运行时排障及其他主题使用独立话题/会话。结果绑定原始请求投递；历史工具结果只能作为背景，不能冒充本轮执行证据。

## 5. 工程层治理

### 5.1 最小工程形态

在现有 `a-stock-cache` 增加一个只读聚合入口：

```bash
a-stock-cache monitor-snapshot --portfolio-value <账户总资产> --json
```

不新建服务或持久层。复用现有 active holdings、风险计算、止损判断、alerts/L3 查询和 `fetch_current_price_quotes()`。

`cache.py` 只负责现有 CLI 风格的注册、参数和 side-effect classification。行为放在最近的现有 command owner；只有两个以上真实调用方需要时才抽取共享函数。禁止调用多个文本 CLI 后再解析 stdout。

### 5.2 执行顺序

固定流水线：

```text
preflight → local snapshot → close DB session → one quote batch
→ calculate → risk gate → output validation → narrative
```

要求：

1. 在一次 `read_only_db_session` 中读取 active holdings、alerts、L3、Tier/风险门所需本地字段；
2. 关闭数据库会话后再访问行情网络，不能跨网络等待持有 SQLite 事务；
3. 同一份报价对象同时传给组合估值和价格门禁；
4. 纯函数完成覆盖率、估值、止损比较、到期判断和 escalation 排序；
5. 先验证机器输出，再生成自然语言；
6. 不进行 schema bootstrap、迁移或任何写入。

该命令因联网取价按现有体系归类为 `R1`，但本命令自身仍必须满足“本地零写入”。

### 5.3 正交输出合同

顶层至少包含：

```json
{
  "schema_version": 1,
  "as_of": "ISO-8601",
  "runtime_version": "...",
  "data_status": "complete|partial|stale|unavailable|conflicted",
  "valuation_status": "exact|priced_positions_lower_bound|unavailable",
  "review_status": "cleared|review_required|blocked",
  "action_status": "no_action|review_candidate|trade_candidate",
  "account": {
    "portfolio_value": 117086.09,
    "denominator_status": "explicit|missing"
  },
  "quote_coverage": {
    "priced": 5,
    "active": 5,
    "complete": true
  },
  "holdings": [],
  "escalations": [],
  "data_gaps": [],
  "stop_reason": "clean_fast_gate|null",
  "requires_user_confirmation": false
}
```

字段维度不得混用：

- `data_status` 只描述证据质量/可用性；
- `valuation_status` 只描述市值语义；
- `review_status` 只描述流程门；
- `action_status` 只描述建议候选；
- `requires_user_confirmation=true` 只表示后续动作仍需确认，不代表当前已授权。

`portfolio_value` 缺失时，`denominator_status=missing`，正式占比和预算判断必须为 null。报价不完整时，`valuation_status=priced_positions_lower_bound`，并列出未取价代码。

### 5.4 escalation reason codes

首版只实现现有规则所需的固定 reason code，不建设规则引擎：

- `price_stop_1`
- `price_stop_2`
- `daily_drop`
- `relative_underperformance`
- `alert_review_due`
- `l3_review_due`
- `l3_candidate`
- `governance_gate`
- `quote_gap`
- `denominator_missing`
- `data_conflict`

新增 reason code 必须对应已存在的领域规则和至少一个契约测试。

### 5.5 fail-closed 映射

- 分母缺失：组合预算不可判，不阻止个股价格/L3复核；
- 部分报价：只报告下限，缺价持仓进入 `review_required`；
- 报价过期：不得确认当日价格触发；
- active holding 与券商/权威输入冲突：`blocked`，先对账，不删除历史；
- L3 legacy/pending/watch/invalid：保留具体待核实项，不得写“全部未触发”；
- 任一关键字段 unavailable/conflicted：不能生成确定性交易候选。

### 5.6 审计 manifest

每次运行保留或输出：

- 数据来源和获取时间；
- active/closed 数量；
- 账户分母来源；
- 报价覆盖率及缺失代码；
- warning/data gap/escalation；
- runtime 和代码版本；
- 每类数据 owner、fallback 原因、阶段耗时和停止原因。

数据库哈希只用于部署、迁移和写入前后验收；日常监控不重复计算。

## 6. 验收与测试

### 6.1 最小自动化检查

1. **无触发快速路径**：五个 active 持仓、一次批量行情、零研究子代理、`action_status=no_action`、`stop_reason=clean_fast_gate`、数据库零写入。
2. **参数化升级路径**：第一档、第二档、单日跌幅、相对行业弱势、alert/L3 到期、L3 候选、治理门、报价缺失、分母缺失和数据冲突。
3. **正交状态合同**：每个状态字段只接受自己的枚举，缺失值映射稳定，不允许旧混合 enum。
4. **生命周期**：closed 记录不进入快照，历史查询仍可审计，重新入场按活动生命周期处理。
5. **单次取价**：风险和价格门共享同一批报价；失败时最多一次记录原因的 fallback。
6. **只读边界**：缺少数据库 fail-closed；运行前后数据库 hash 不变；命令无 `--confirm-write` 路径。

网络 provider 使用测试替身只限自动化边界测试；首版真实验收直接走既有 production adapter 的只读路径，不增加待替换的 fake 业务层。

### 6.2 本次案例回放

以本次五只 active 持仓的冻结输入回放，预期只产生“冻结新增风险/不加仓”和已存在的定向复查候选，不重新展开五股全量研究，不生成交易或账本写入。

## 7. 发布、回滚与权限

1. 先修改项目源仓库中的 skill 契约和命令/测试，不直接维护已部署副本；
2. 完成定向测试、全量 pytest、Ruff、`git diff --check` 和 build；
3. 对行为/安全边界做一次独立 final-diff review；
4. 生产部署、运行时切换或 active skill 发布须另有授权并先生成回滚清单；
5. 部署后只读验证版本、CLI 合同、数据库 hash 和 `PRAGMA integrity_check`；
6. 回滚恢复上一 runtime/symlink 和 skill 版本，不回写或重建投资数据库。

## 8. 运行指标

- 无触发路径首个结论：首期 ≤8 分钟，稳定后 P95 ≤5 分钟；
- 无触发路径研究子代理数：0；
- 每轮全组合行情：一次主请求，最多一次有原因的 fallback；
- 历史持仓混入当前组合：0；
- 未知分母仍判断预算：0；
- 不完整报价仍声称完整市值：0；
- 未经确认写账本或执行交易：0；
- optional 任务阻塞首轮结论：0。

时间目标是观察指标，不得为了达标跳过 required 安全门。

## 9. 实施顺序

1. 在现有 `a-stock-monitor` 中加入 Level 1/Level 2 路由、停止合同和 required/optional 分类；
2. 添加 `monitor-snapshot` 的 JSON 合同测试，再实现最小聚合入口；
3. 复用/提取现有计算逻辑，消除组合内重复取价；
4. 运行冻结案例回放和只读真实 adapter 验收；
5. 获得部署授权后再发布并观察指标。

## 10. 独立审查吸收记录

AGY R1 verdict：`REQUEST_CHANGES`。

- 已接受 blocker 1：停止合同移除“风险预算不允许增加风险”前提；是否有闲置容量不再触发未请求的加仓扫描。
- 已接受 blocker 2：混合状态枚举拆为 `data_status`、`valuation_status`、`review_status` 和 `action_status`。
- 已接受安全意见：快速门禁不主动抓宏观/新闻不削弱既有量化触发边界；缺数继续 fail-closed。
- 已校正实现建议：`cache.py` 负责 CLI 注册，领域行为遵循现有 command owner；联网取价前关闭只读数据库会话。

R1 证据：`/home/lin/a-stock-agent-evidence/docs/reviews/20260908-1405-monitoring-governance-r1/`。
