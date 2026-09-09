---
name: a-stock-qa
description: Use after an a-stock-research report to independently verify mandatory steps and data completeness. Unsupported types return SKIP; invalid inputs return INVALID_RUN. Returns a structured compliance verdict with per-check details.
license: Proprietary
compatibility: Reads this Skill's rubric and checks supplied report text.
---

# a-stock-qa

本 Skill 只处理输入文本和本 Skill 内 rubric；不会执行 runtime CLI、访问行情或写入状态。

独立合规检查层。在投研分析完成后调用，验证强制步骤执行情况和数据完整性。

> **能力边界**：QA PASS 仅代表报告文本符合流程规则，不证明外部数据真实、周期判断正确、评分已校准或策略具有投资有效性；不得把 `COMPLIANT` 表述为“投资结论可靠/可直接交易”。QA必须由宿主真正独立调用；生成研究报告的同一模型自行阅读 rubric、手工输出检查表不算独立调用，应返回 `SKIP`/“QA未执行”。

## 调用前提

必须已有完整 a-stock-research 分析输出正文，并以正文直接传入或提供当前宿主可读的**不可变快照**。文件输入必须使用本轮唯一版本路径；宿主在 QA 开始前记录内容哈希，并在形成 verdict 前再次核对。QA 开始后不得覆写该路径。QA verdict 仅适用于该快照；正文发生任何修订时必须生成新快照并重新执行 QA，不得沿用旧 verdict。
如缺少完整正文、只提供摘要/修订说明、路径不可读或工具异常，直接返回 `verdict: INVALID_RUN` 并说明缺失项；不得返回 `NON_COMPLIANT`，也不得把该次运行计入报告合规结果。QA输出后，宿主还必须验证最终交付正文（不含固定verdict元数据行）的SHA-256与QA输入哈希一致；不一致时旧verdict立即失效，必须对新快照重新执行。
当前仅支持已有的 a-stock-research rubric；其他类型返回 `SKIP`。

## 执行步骤

### Step 1：确认 skill_type

从调用上下文确认 `skill_type`：
- `a-stock-research`：股票研究分析报告
- `a-stock-monitor`：持仓监控/L3 复核记录
- `a-stock-tracker`：自动评分批量输出

如 skill_type 未指定，根据输出文本特征推断（有"基本面评分/60"→ research；有"L3"→ monitor；有批量代码列表→ tracker）。

### Step 2：加载对应 rubric

```
Read the [a-stock-research rubric](references/rubrics/a-stock-research.md) for <skill_type>
```

如 rubric 文件不存在（Phase 2/3 尚未实现），返回：
```
verdict: SKIP
reason: rubric for <skill_type> not yet implemented (Phase 2/3)
```

### Step 3：逐项执行检查

按 rubric 文件中的检查列表，逐项判断分析输出是否满足条件。

判断原则：
- **PASS**：输出中有明确证据表明该步骤已执行（关键词/数值/标注均可）
- **FAIL**：输出中明确缺少该步骤，或存在与要求相悖的内容
- **SKIP**：该检查项对本次分析不适用（rubric 文件中标注了跳过条件）

每项检查给出 1 句 note 说明判断依据。

### Step 4：汇总 verdict

```
COMPLIANT    = 所有检查均 PASS 或 SKIP（无 FAIL）
PARTIAL      = 有一个或多个 FAIL，但全部为 Minor 级别
NON_COMPLIANT = 有任意 Critical/Important 级别 FAIL
```

必须先按级别汇总再写 verdict，禁止凭整体印象改写结果。Rubric 以外的建议放入独立 `Advisory` 段；Advisory 不得影响 verdict。

### Step 5：输出结构化报告

```
## a-stock-qa 合规检查报告

**Skill type**: <skill_type>
**股票**: <代码 + 名称，如可从输出中提取>
**检查时间**: <今日日期>
**Process verdict**: COMPLIANT | PARTIAL | NON_COMPLIANT | INVALID_RUN
**Data status**: COMPLETE | INCOMPLETE
**Decision status**: FORMED | NOT_FORMED
**Input SHA-256**: <hash>

### 检查明细

| # | 检查项 | 级别 | 结果 | 说明 |
|---|--------|------|------|------|
| 1 | <名称> | Critical/Important/Minor | PASS/FAIL/SKIP | <1句> |
...

### 结论

<如果 COMPLIANT>：报告文本流程合规；这不代表数据完整、事实真实或建议可交易。
<如果 PARTIAL>：存在 Minor 问题，不影响分析结论可用性，建议下次修正。
<如果 NON_COMPLIANT>：存在以下问题需在报告首部置顶警告：
  - [FAIL 项列表，各一句说明]
<如果 INVALID_RUN>：输入缺少完整报告正文或不可读，本次未形成合规结论：[原因]
```

## 注意事项

- 本 skill **不修改**原始分析报告，只输出检查报告
- `Data status` 根据正文中的 gate/关键字段状态汇总；`Decision status` 根据评级/矩阵是否形成汇总，两者不影响按 rubric 级别计算的 Process verdict
- 正式PDF作为关键证据时，检查正文是否写明与首页一致的文件标题、公告日期和发布主体；只有搜索摘要或模糊“正式材料”时按 rubric 失败
- 本 skill **不发表投资意见**，只判断流程合规性
- 检查结果基于报告文本，无法核验外部数据源的实际准确性
  （如 fetcher 数据本身是否正确，不在本 skill 职责范围内）
- 完整报告存在、但某一步骤证据模糊或无法判断 → 按 rubric 级别保守判断为 FAIL，附注"无法从输出文本确认"
- 完整报告本身不存在或不可读 → `INVALID_RUN`，不是合规 FAIL
- 文件输入的前后内容哈希不一致时，返回 `INVALID_RUN` 并说明输入快照漂移；不得对混合版本形成合规 verdict
