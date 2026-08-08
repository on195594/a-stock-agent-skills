# a-stock-qa 设计规格

> 来源：Google Agent Quality Flywheel 方法论分析（2026-07-04）+ adversarial 决策

---

## 背景

a-stock-* skill family 存在两类质量问题：
1. **步骤遗漏**：强制分析步骤偶尔被跳过（fetcher先行、异动检测、框架路由等）
2. **数据不准**：字段标注缺失、股息率未交叉验证、EPS除权未调整等

根本原因：Claude 既做分析又评估质量（optimizer = evaluator 反模式）。

---

## 架构决策

**2026-07-04 adversarial 决策**（codex + agy 独立评估，两票收敛）：

选择 **Option B：独立共享 a-stock-qa skill**

淘汰原因：
- Option A（各 skill 内置）：rubric 三套各自漂移，结构耦合未解决
- Option C（接入 ai-collab）：阻抗不匹配——ai-collab 围绕"git diff 审查"设计，
  投研分析无 diff、无 commit，强行映射是结构性债务

决策记录：`~/.claude/skills/a-stock-research/.claude/ai-collab/state/decisions.jsonl`

---

## 设计原则

1. **评估者 ≠ 优化者**：a-stock-qa 以独立 AI pass 调用，不与分析 Claude 共享上下文
2. **rubric 单一维护点**：所有检查规则集中在 `rubrics/<skill_type>.md`，调用方只传 output
3. **不阻断流程**：NON_COMPLIANT 在报告首部置顶警告，但不终止后续使用
4. **可扩展 rubric**：按 skill_type 分块，Phase 2/3 只需新增 rubric 文件

---

## Phase 路线图

### Phase 1（已实现，2026-07-04）
- a-stock-research rubric（11 项检查，含周期位置/分红压力测试）
- SKILL.md dispatch 流程
- 结构化 verdict 输出

### Phase 2（待实现）
- a-stock-monitor rubric（L3 裁决质量、止损评估依据）
- 接入 a-stock-monitor skill
- 失败 trace 校准案例收集机制

### Phase 3（待实现）
- a-stock-tracker rubric（批量评分一致性）
- qa-reliability.jsonl 投研专用版
- collab-retro 集成

---

## 关键设计决策（待后续阶段解决）

1. **verdict 是否持久化**：Phase 1 仅输出文本，不写文件。Phase 2 再决定是否引入 jsonl 记录。
2. **调用触发**：目前为手动（PM 在 a-stock-research 完成后主动调用）。
   Phase 2 可考虑在 skill 末尾自动触发。
3. **rubric 更新机制**：目前靠 PR/直接编辑。Phase 2 可参考 ai-collab 的 calibration-cases 机制。
