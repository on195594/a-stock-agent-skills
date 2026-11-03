# 2026-11-01 Research 论点卡接入与卖出复核提醒（批次 B）

授权：所有者 2026-11-01 Telegram msg 4046 确认政策（门槛由 Claude 受托决定、透支区只提醒、换仓门槛 3 个百分点并扣交易成本）。
上游设计：`a-share-research/docs/investment-advisor.md` 第 8 节。

## 1 要解决的断点

Research 已能给出论点卡（`有效`/`待复核`）、当前价所处测算区间和三档情景年化回报，但 `monitor-snapshot` 不读这些，持仓复核只看止损、L3 和组合风险。本批让快照读论点卡，产出复核提醒，不改任何现有门禁与动作规则。

## 2 数据来源（只读）

- 一次调用 Research `GET /api/cards`（`research-v1`），返回扫描范围内每家的卡片，字段同 `GET /api/companies/{code}/card`，另带 `origin`（`external`/`l5`），无卡代码在 `missing`。
- 卡片 `current` 由 Research 按其最新收盘价计算：`last_close`、`last_close_date`、`current_zone`，以及 `valuation`（`annual_returns` 三档、`support_below`、`stretched_above`、`horizon`，均按收盘日滚动；不可算时为 null 并给 `reason`）。估值公式只在 Research，Skills 不复算。
- 未配置 `A_STOCK_RESEARCH_URL/TOKEN` 时 `research.status=not_configured`；请求失败、超时、版本不符时 `research.status=unavailable` 并带简短原因。两者都**不改变** `data_status`、`review_status`、`action_status`、`data_gaps` 和 `clean_fast_gate`（Research 不是 decision-v1/monitor-v1 门禁的数据源）。
- 新增 `--no-research` 跳过调用（`research.status=skipped`）；超时沿用 `research_client` 的 `(10, 30)`，不重试。

## 3 快照新增字段（monitor-v1 加法，`schema_version` 不变）

`research` 对象：

- `status`: `ok` / `not_configured` / `unavailable` / `skipped`；`reason` 可选。
- `holdings[]`：每只在仓股票一行：`code`、`card`（`null` 表示无卡）、`card_status`、`verdict`、`report_id`、`completed_at`、`close`、`close_date`、`zone`、`neutral_return`、`conservative_return`、`optimistic_return`、`note`。卡片 `待复核` 时区间与回报照抄 Research，但提醒规则不使用（Research 已标注“区间暂停解读”）。
- `candidates[]`：`origin=l5` 且不在仓的代码，同样字段。
- `missing[]`：Research 报告无卡的代码。

`review_prompts[]`（只提醒，不进入 `escalations`，不影响任何状态字段与 `clean_fast_gate`）：

| `kind` | 条件 | 说明 |
|---|---|---|
| `valuation_stretched` | 持仓卡 `有效` 且 `zone=测算透支区` | 只提醒复核经营假设与退出倍数；不计入 L3、不冻结 |
| `opportunity_cost` | 持仓卡与候选卡均 `有效`、中性回报均非 null、候选 `verdict=值得继续研究`，且 候选不计累计分红的中性回报 − 持仓计全部累计分红的中性回报 − 年化换仓成本 ≥ 0.03 | 每只持仓只报差值最大的一个候选；列出双方 report_id、收盘日 |
| `research_unavailable` | `research.status=unavailable` | 论点卡状态未知 |

年化换仓成本 = 单次成本率 ÷ 候选 `horizon`（年）。单次成本率 = 卖出印花税 `STAMP_TAX_RATE`(0.05%) + 2 × 佣金率；佣金率新增常量 `COMMISSION_RATE = 0.00025`（万 2.5，忽略 5 元最低），与现有 `STAMP_TAX_RATE` 放在同一模块统一引用。两边收盘日不同（相差超过 3 个自然日）时不形成机会成本提醒，在 `research` 里写 `reason`。

每条提醒带 `code`、`kind`、`detail`（中文一句，含关键数字）、`evidence`（report_id、close_date 等）。不给卖出股数、比例或候选买入数量。

## 4 升级项

- 持仓卡 `待复核` → 新升级原因 `research_thesis_review`（`candidate=review`），`detail` 引用 Research 的待复核事件标题/类型；按“日常异常、公告、活动预警或 L3”资料复核，需要证据时按 Research 服务读报告。它影响 `review_status`（与公告类升级一致），不冻结、不产生交易候选。排序放在 `l3_watch` 之后、`governance_gate` 之前。
- `risk_budget_exceeded` 保持原样，即四类理由中的“风险超限”。

## 5 CLI

- `a-stock-cache research cards`：读 `GET /api/cards`。
- `a-stock-cache research card <code>`：读 `GET /api/companies/{code}/card`。
- 二者沿用现有错误与凭据处理，不发起研究。

## 6 Skill 文本

`a-stock-monitor`：首屏在结论后增加“研究提醒（不影响动作状态）”一行到数行，逐条转述 `review_prompts`；用户要求组合复盘或换仓比较时，用 `research.holdings/candidates` 给一张表（区间、三档回报、卡片状态、收盘日、风险占用）。Level 2 表增加 `research_thesis_review` 行，指向日常监控与 L3 资料并按 Research 服务读报告。不从提醒推导股数。

## 7 验收

- 确定性测试：输入取自真实 Research 卡片 JSON（生产只读捕获或开发实例真实输出），覆盖：有效+透支区提醒、待复核升级、机会成本达门槛/差 0.1pp 不达、候选非“值得继续研究”不提醒、收盘日差过大不提醒、未配置/不可用不改变状态、`--no-research`。
- 互变测试：去掉交易成本扣减、把门槛改为 0.02、让提醒进入 `escalations`，相应测试须失败。
- 现有 `monitor-v1` 契约测试全部通过；`bash scripts/check.sh` 通过。
- 激活需所有者当次授权；生产对照（真实持仓一次快照）为激活后验收。

## 2026-11-03 分红敏感性修正（候选，未激活）

依据所有者当次“继续推进”的授权，修正未核对累计分红制造确定换仓优势的问题，不改3个百分点门槛、成本或账户动作。Research新增可选 `current.valuation.neutral_return_without_dividends`：同一冻结中性退出市值、价格和期限下，不计累计分红的年化；退出市值或累计分红为负时不给此值。原三档回报和 `note` 语义不变。

仅在双方均有适用敏感性值时，用候选不计分红、持仓计全部分红作比较。这是非负冻结分红假设内对已付比例不确定性的敏感性端点，并非实际收益上下界，也不覆盖股本变化、未来派息政策或新经营事实。`net_advantage`为此口径的扣费差，证据同时保留原中性回报、新的候选端点及 `comparison_basis`，提示文字说明口径。未达门槛或旧服务缺字段时，只在 `research.reason`说明，不清空卡片、不升级账户状态、不触发研究。已有7日新鲜度、收盘日差及按候选合并规则保持。

先部署Research加法字段，再单独批准激活Skills。旧客户端忽略新字段；新客户端遇旧服务跳过机会成本比较，其余功能继续。仅仓库内离线验证，未安装激活账户程序或发送通知。
