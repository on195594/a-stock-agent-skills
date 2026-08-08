## 数据操作附录

本节收录交易账本、结构化状态和除权调整的授权流程。日常只读监控不需要加载；
建仓、加减仓、状态更新或公司行动时查阅。

### 交易账本命令（禁止直接 SQL 改持仓）

本项目采用**单行持仓 + 不可变交易事件**：`holdings` 保存当前状态，
`holding_events` 保存每次买入、卖出、费用、税费和现金分红。任何交易都必须通过
下列命令写入，禁止手工 UPDATE 成本、股数或平仓状态。

```bash
# 全新股票第一次建仓；会固化持仓 framework、initial_shares 和最初 buy_date
$CACHE --confirm-write add-holding <代码> <成交价> <股数> [备注] \
  [--fee <金额>] [--date YYYY-MM-DD]

# 已有持仓加仓；自动计算含买入费用的加权成本、重算框架止损线，
# 保留最初 buy_date，并维护结构化 main_entry_date
$CACHE --confirm-write buy-holding <代码> <买入价> <股数> [--fee <金额>] [--date YYYY-MM-DD]

# 部分或全部卖出；校验交易所整手/零股申报约束，FIFO分配到lot，
# 同步剩余股数并记录费用、印花税和已实现盈亏
$CACHE --confirm-write sell-holding <代码> <卖出价> <股数|all> \
  [--fee <金额>] [--tax <金额>] [--date YYYY-MM-DD]

# 记录实际到账的现金分红总额
$CACHE --confirm-write record-dividend <代码> <现金总额> [YYYY-MM-DD]

# 用全部买卖现金流、费用税费、分红和剩余市值计算总回报及真实持有天数
$CACHE position-return <代码> [当前价]
```

`corporate-action` 已自动生成对应现金分红事件；同一次分红不要再调用
`record-dividend`，否则会重复计算回报。后者只用于不伴随规则参考成本调整的独立补录。

`close-holding` 与 `update-return` 仅保留给旧数据兼容，不再作为本 skill 的交易写入路径。
每次写入后执行 `$CACHE holdings` 和 `$CACHE portfolio-risk --portfolio-value <可投资总资产>`，
确认股数、成本、buy_date、风险贡献均正确。

### 结构化状态命令

```bash
# L3
$CACHE --confirm-write l3-add <代码> <original|recovered|new_monitoring> "<条件>" ["临时出场规则"]
$CACHE --confirm-write l3-update <条件id> <pending|not_triggered|watch|triggered> \
  <YYYY-MM-DD> "<证据>" [下次复核日期]
$CACHE l3-list <代码>

# Tier（豁免声明只能在建仓当日写入）
$CACHE --confirm-write tier-config <代码> <A|B|C|none> <目标涨幅%|none> <E|F|none>
$CACHE --confirm-write tier-update <代码> <tier1|tier2|tier3> <状态>

# 显式迁移既有持仓框架并按 reference_cost 重算止损线
$CACHE --confirm-write holding-framework <代码> <A|B|C|D|E|F>

# 预警；reason_code 是稳定去重键
$CACHE --confirm-write alert-open <代码> <yellow|red> \
  <holding_deterioration|entry_valuation|unverified> \
  <reason_code> <复核日期|none> "<原因>" ["证据"]
$CACHE --confirm-write alert-pending <代码> <reason_code> "<仍缺的数据/待核实说明>"
$CACHE --confirm-write alert-resolve <代码> <reason_code> "<解除证据>"
$CACHE alerts <代码>
```

L3、Tier、预警和主力入场日期不得再以自由文本 notes 作为唯一事实源；notes 只保留
无法结构化的补充说明。

### 历史预警查询

使用 `$CACHE alerts <代码>`。首次迁移会把旧版 `analysis_results.flags` 原样转成
`unverified + pending` 预警，保留证据但不计入恶化项门槛；复核后必须重新分类或解除，
不再直接按历史 JSON 条数累计风险。

### 除权成本调整授权规则

```
新成本 = (建仓成本 - 每股现金分红) / (1 + 转增比例)
触发：确认除权日或收到分红入账
操作边界：
  - 用户只问"怎么算"时：若 DPS 或转增比例未提供，先追问完整参数再计算；只输出新成本与
    Tier 1/2/3 目标价，附提醒「如需更新缓存，请明确说更新」；不得写 cache.py。
  - 用户含写入意图时（包括：明确说「更新持仓/cache/成本」、同一句话里「算完再更新」、
    「更新为…」等表达）：先给出拟写入的新成本与重算后的 Tier 目标价，请求用户确认。
    有效确认词：「确认」「是，写入」「好，更新」；单纯认可计算结果（「嗯」「算对了」）
    不视为写入授权。
  - 用户明确确认后执行：
    ```bash
    $CACHE --confirm-write corporate-action <代码> <每股现金分红> <转增比例> [YYYY-MM-DD]
    ```
    该命令把经济成本与规则参考成本分开：现金分红作为回报事件记录，不从经济投入中
    重复扣除；Tier/止损参考成本按除息送转公式调整。不得手工 SQL 或删行重建。
  - 除权成本调整不触发卖出记录，不调用 update-return（该命令仅用于实际卖出后）。
```

### 结构化状态字段参考表

| 字段 | 写入时点 | 适用范围 | 消费方 |
|---|---|---|---|
| `buy_date`（cache.py 列，非notes文本） | 首次建仓（INSERT） | 全部持仓 | 步骤5年度复查计时 |
| 出场路径 / 目标 | 建仓当日通过 `tier-config` | A/E/F框架轻仓试探 | `holding_tier_state` |
| Tier1估值豁免声明 | 建仓当日通过 `tier-config` | E/F正式仓位 | `holding_tier_state` |
| 主力入场日期 | `buy-holding` 自动维护 | 全部持仓 | `holdings.main_entry_date` |
| 压力测试后前瞻股息率数值+来源+核查日期 | 每次步骤3.5核查（无论是否加仓） | C/D框架轻仓试探持仓 | 步骤3.5「首次核查」基线比较 |
| 格档加仓依据（证据+日期、加仓前/后累计增持量、原建仓股数基准） | 步骤3.5"格档小额试探加仓"触发时 | 同上 | 步骤3.5阶段3仓位计算的累计上限判断 |
| Tier1/2/3状态 | `tier-update` | A/E/F | `holding_tier_state` |
| PEG计算记录（数据源、as-of日期、NP0、NP2、`G_pct`、PEG结果） | 每次涉及E框架PEG判定时（Tier1/Tier2-3/Tier1后补仓均适用） | E框架持仓 | 步骤4各处PEG判定 |
| L3核查结论 | `l3-add/l3-update` | 全部持仓 | `holding_l3_conditions` |
| 预警及消除依据 | `alert-open/alert-resolve` | 全部持仓 | `holding_alerts` |

本表汇总各步骤的持久化状态。除 PEG 计算明细和格档核查证据仍可作为补充 notes 外，
交易、L3、Tier、预警与主力入场日期均以结构化列/表为准。
