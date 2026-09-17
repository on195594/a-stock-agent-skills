# a-stock-qa

A股投研分析质量检查 skill——a-stock-* skill family 的共享 evaluator 层。

## 用途

当前仅在 a-stock-research 产出分析报告后，以宿主独立调用检查文本 rubric；
a-stock-monitor / a-stock-tracker 等不支持类型返回 `process_verdict: SKIP`，不代表检查通过。
有效调用检查：
1. **强制步骤合规性**：所有必须执行的分析步骤是否已执行
2. **数据完整性**：关键字段是否存在、是否有正确的来源标注
3. **框架路由正确性**：是否选用了正确的评分框架

## 调用方式

调用者（宿主或独立 PM 角色）提供：
```
skill_type: a-stock-research
output: <完整报告正文的不可变快照>
```

a-stock-qa 返回：
```
process_verdict: COMPLIANT | PARTIAL | NON_COMPLIANT | SKIP | INVALID_RUN
data_status: COMPLETE | INCOMPLETE | null
decision_status: FORMED | NOT_FORMED | null
input_sha256: <hash or null>
reason: <未完成原因；正常完成时可为 null>
checks:
  - name: <检查项名称>
    result: PASS | FAIL | SKIP
    note: <简短说明>
```

`SKIP/INVALID_RUN` 表示未产生合规结论，此时数据与决策状态为 `null`、`checks` 为空；哈希无法取得时为 `null`。宿主在 QA 前后核对同一快照的 SHA-256；缺失、摘要代替正文、内容漂移或工具异常返回 `INVALID_RUN`。无独立调用能力返回 `SKIP`，不得模拟完成。

字段语义以 [SKILL.md](SKILL.md) 为准。合规结论不证明事实真实、来源有效或建议可交易。

## Rubric 目录

| 文件 | 覆盖范围 | 状态 |
|------|----------|------|
| [references/rubrics/a-stock-research.md](references/rubrics/a-stock-research.md) | 首次研究流程、门禁、估值、来源与交付完整性 | ✅ 已实现 |

monitor 与 tracker rubric 尚未实现，不是可调用能力。

## 设计决策

本 skill 采用独立共享 skill 架构（Option B），而非内嵌各 skill 或接入 ai-collab。同一模型自行阅读 rubric 不算独立调用；最终交付正文必须与输入快照哈希一致。
历史设计记录见
canonical 仓库根目录下的 `docs/migration/source-qa-specs/2026-07-04-a-stock-qa-design.md`（历史背景，不是本 Skill 的运行依赖）。

## 版本

- Phase 1（2026-07-04）：a-stock-research 合规检查
