# 换仓提示合并与时效（0.1.30）

授权：所有者 2026-11-02 Telegram msg 4089 同意（换仓门槛由 Claude 受托决定，见 msg 4046）。修改 [2026-11-01 规格](2026-11-01-research-card-review-prompts-spec.md) 中 `opportunity_cost` 的呈现方式；比较规则本身不变。

## 1 问题

0.1.29 激活后首批快照（2026-11-02，报告 70–78）里，4 只持仓全部触发同一候选（宁德时代，中性年化 19.8%）的换仓提示，每只持仓各一条。情景数字由模型提出，尚未记分（A3/V1 待成熟），各卡保守到乐观的跨度约 40 个百分点，远大于 3 个百分点门槛。同一信息每天重复 4 条，会让用户对研究提醒脱敏。

## 2 规则

比较规则不变：双方卡片 `有效`、候选 `verdict=值得继续研究`、中性回报非空、收盘日相差 ≤3 个自然日、扣年化换仓成本后差值 ≥3 个百分点，每只持仓取扣费后差值最大的候选。

变化只在输出：

1. **结构化结果全部保留**：新增 `research.opportunity_costs`，按持仓逐条列出达标比较（字段沿用原 `opportunity_cost` 提示的 evidence）。组合复盘和换仓比较表都从这里取数，不受时效限制。
2. **按候选合并**：`review_prompts` 不再按持仓逐条给出 `opportunity_cost`，改为每个候选一条 `opportunity_cost`，`code` 为候选代码，detail 形如“宁德时代 300750 中性年化 19.82%，扣费后比 长江电力/三花智控/… 高 ≥3 个百分点（最大差 X），情景未经记分，仅提示复核”，evidence 列出各持仓的比较。
3. **时效**：只有当候选卡或其中任一持仓卡的 `completed_at` 距快照日不超过 7 个自然日时，才生成合并提示；超过 7 日的比较只留在 `research.opportunity_costs`。快照日取 monitor snapshot 本身的日期字段，不取系统时钟以外的推断值。`completed_at` 缺失或不可解析时视为不新鲜，不报错。
4. 透支区提示（`valuation_stretched`）、待复核升级（`research_thesis_review`）和收盘日不匹配原因不变。

## 3 文档

`skills/a-stock-monitor/SKILL.md` 与 `references/valuation-and-annual-review.md`：说明换仓提示按候选合并、7 日时效，组合复盘或换仓比较时从 `research.opportunity_costs` 取全部比较；`docs/architecture/runtime-contracts.md` monitor-v1 增加 `research.opportunity_costs`（加法字段，schema_version 不变）；CHANGELOG 0.1.30，`pyproject.toml` 版本号。

## 4 测试

用 2026-11-02 生产卡片（报告 70–78）的真实 valuation 数值作夹具并注明来源：4 只持仓对同一候选只出 1 条合并提示；卡片全部超过 7 日时不出提示但 `opportunity_costs` 仍有 4 条；只有一只持仓卡新鲜时仍合并出 1 条（列出全部达标持仓）；两个候选各自达标时出 2 条；`completed_at` 缺失视为不新鲜。互变检查：去掉时效条件或改回逐持仓输出，至少一个测试失败。
