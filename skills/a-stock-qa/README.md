# a-stock-qa

A股投研分析质量检查 skill——a-stock-* skill family 的共享 evaluator 层。

## 用途

在 a-stock-research / a-stock-monitor / a-stock-tracker 产出分析报告后，
以独立 AI pass 检查：
1. **强制步骤合规性**：所有必须执行的分析步骤是否已执行
2. **数据完整性**：关键字段是否存在、是否有正确的来源标注
3. **框架路由正确性**：是否选用了正确的评分框架

## 调用方式

调用者（PM 或 skill 内部）提供：
```
skill_type: a-stock-research | a-stock-monitor | a-stock-tracker
output: <完整的分析报告文本>
```

a-stock-qa 返回：
```
verdict: COMPLIANT | PARTIAL | NON_COMPLIANT
checks:
  - name: <检查项名称>
    result: PASS | FAIL | SKIP
    note: <简短说明>
```

## Rubric 目录

| 文件 | 覆盖范围 | 状态 |
|------|----------|------|
| `rubrics/a-stock-research.md` | 11 项强制检查（Phase 1）| ✅ 已实现 |
| `rubrics/a-stock-monitor.md` | L3 裁决质量检查（Phase 2）| 待实现 |
| `rubrics/a-stock-tracker.md` | 批量评分一致性检查（Phase 3）| 待实现 |

## 设计决策

本 skill 采用独立共享 skill 架构（Option B），而非内嵌各 skill 或接入 ai-collab。
历史设计记录见
`docs/migration/source-qa-specs/2026-07-04-a-stock-qa-design.md`。

## 版本

- Phase 1（2026-07-04）：a-stock-research 合规检查
