# 文档入口

## 当前维护面

- [README](../README.md)：目标、安装和安全边界。
- [development](development.md)：本地验证；[operations](operations.md)：配置、部署与回滚。
- [runtime contracts](architecture/runtime-contracts.md)：decision-v1 / monitor-v1、owner 和版本合同。
- [Agent 行为验证](agent-behavior-eval.md)。
- `skills/*/references/`：Agent 当前执行规则；`specs/`：仍需追溯的投资/风险规则依据。规则变更须显式授权，不能用整理文档绕过。

## 历史只从 Git 追溯

已完成的 M0–M8、P2、架构收敛、S1/S2/S3 实施计划、旧基础规格、已完成 vNext 实施稿及被 v1.1 替代的风险闭环 v1.0 已移出活动树。**它们不是下一轮任务清单。**

归档快照：`165e2c86c74ec4b7c548aef39fe06884100ba7c5`。列出及读取原文：

```bash
git ls-tree -r --name-only 165e2c8 docs/plans docs/specs
git show 165e2c8:docs/plans/2026-09-17-s2-s3-implementation.md
```

Tracker Framework A 已于 2026-09-21 `CLOSED_UNPROVEN` 结案；旧 S2 的继续收样和等待成熟均已取消。Lib/Research 的 A—F 合同并未退役。

技能包中的旧 Monitor CHANGELOG 和重复 QA README 已移出活动树；历史原文保留于 `f9a4ebe`，例如：

```bash
git show f9a4ebe:skills/a-stock-monitor/CHANGELOG.md
git show f9a4ebe:skills/a-stock-qa/README.md
```

QA 当前输入、输出和独立调用边界只维护在其 `SKILL.md`，检查细则维护在 rubric。

旧部署/preflight 记录和已完成的架构计划审查已移出活动文档；完整记录保留于 `f5307f7`：

```bash
git show f5307f7:docs/operations.md
git show f5307f7:docs/reviews/a-stock-codex-plan-agy-review.md
```

当前部署及适用回滚只以 `operations.md` 的当前记录为准。

[CHANGELOG](CHANGELOG.md)、[迁移/回滚证据](migration/README.md)、[外部审查归档](reviews/README.md) 保留原日期含义；其旧路径可通过上述快照读取。历史证据不作为普通开发的必读上下文，也不因整理而删除生产资料。
