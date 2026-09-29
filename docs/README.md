# 文档入口

## 日常开发只按需读

- [项目目标与安装](../README.md)
- [开发与验证](development.md)
- [运行、部署与回滚](operations.md) — 部署事实的唯一维护入口。
- [Runtime 合同与职责](architecture/runtime-contracts.md) — decision-v1 / monitor-v1、规则 owner、版本边界。
- [Agent 行为验证](agent-behavior-eval.md)

当前投资规则还须按实际改动阅读 `skills/*/references/`、对应 runtime/lib 实现及测试；不得把缩短文档理解为取消 fail-closed、W1 授权或规则依据。

## 仅追溯时读

- [CHANGELOG](CHANGELOG.md)：版本变化。
- `specs/`：已授权的规则与接口变更依据；按被改规则定位，不全量预读。
- `plans/`：阶段执行与验证记录，不是持续任务队列；完成的 M0–M8、架构收敛或 S1/S2/S3 不因留有计划而重做。
- [迁移记录](migration/README.md)、[审查归档](reviews/README.md)：保留来源、回滚和证据，不参与日常上下文加载。

**Tracker Framework A 已于 2026-09-21 `CLOSED_UNPROVEN` 结案。** 旧 S2 文档的继续收样、窗口成熟和下一阶段描述仅是历史，不是当前待办；结案依据在 Tracker 的 `docs/evolution-roadmap.md`。本次未改写历史记录或其投资规则。

历史证据、部署记录、凭据和生产状态各自隔离；证据目录不是源码依赖，不因精简而删除备份、数据库或发布回滚材料。
