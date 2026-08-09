---
name: a-stock-qa
description: Use after an a-stock research or monitoring report to independently verify that mandatory analysis steps were executed and data fields are complete. Returns a structured compliance verdict (COMPLIANT/PARTIAL/NON_COMPLIANT) with per-check details.
license: Proprietary
compatibility: Reads this Skill's rubric and checks supplied report text.
---

# a-stock-qa

本 Skill 只处理输入文本和本 Skill 内 rubric；不会执行 runtime CLI、访问行情或写入状态。

独立合规检查层。在投研分析完成后调用，验证强制步骤执行情况和数据完整性。

> **能力边界**：QA PASS 仅代表报告文本符合流程规则，不证明外部数据真实、周期判断正确、评分已校准或策略具有投资有效性；不得把 `COMPLIANT` 表述为“投资结论可靠/可直接交易”。

## 调用前提

必须已有完整分析输出文本（a-stock-research 报告、a-stock-monitor 复核记录等）。
如无完整输出，直接返回 `verdict: SKIP`，附注"无分析输出可检查"。
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
Read the discovered a-stock-qa rubric for <skill_type>
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
PARTIAL      = 有 1-2 个 FAIL，但均为 Minor 级别
NON_COMPLIANT = 有任意 Critical/Important 级别 FAIL
```

### Step 5：输出结构化报告

```
## a-stock-qa 合规检查报告

**Skill type**: <skill_type>
**股票**: <代码 + 名称，如可从输出中提取>
**检查时间**: <今日日期>
**整体 verdict**: COMPLIANT | PARTIAL | NON_COMPLIANT

### 检查明细

| # | 检查项 | 级别 | 结果 | 说明 |
|---|--------|------|------|------|
| 1 | <名称> | Critical/Important/Minor | PASS/FAIL/SKIP | <1句> |
...

### 结论

<如果 COMPLIANT>：分析流程合规，所有强制步骤均已执行。
<如果 PARTIAL>：存在 Minor 问题，不影响分析结论可用性，建议下次修正。
<如果 NON_COMPLIANT>：存在以下问题需在报告首部置顶警告：
  - [FAIL 项列表，各一句说明]
```

## 注意事项

- 本 skill **不修改**原始分析报告，只输出检查报告
- 本 skill **不发表投资意见**，只判断流程合规性
- 检查结果基于报告文本，无法核验外部数据源的实际准确性
  （如 fetcher 数据本身是否正确，不在本 skill 职责范围内）
- 遇到模糊情况（输出不完整、无法判断某步骤是否执行）→ 保守判断为 FAIL，附注"无法从输出文本确认"
