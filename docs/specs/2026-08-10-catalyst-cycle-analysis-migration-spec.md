# A股产品周期与主题催化分析迁移规范（2026-08-10）

## 背景

此前一次自动改进将产品周期分析规则误写到 Hermes 的非 canonical 同名技能目录。用户明确要求将该补丁迁移到 `/home/lin/a-stock-agent-skills`，该仓库是 `a-stock-*` 技能的唯一权威源。
用户于 2026-08-11 明确授权完成并提交本批变更。

## 范围

1. 在 `skills/a-stock-research/references/` 增加产品周期与主题催化分析参考。
2. 在 Research `SKILL.md` 增加精确触发路由。
3. 用聚焦契约测试固定路由、证据分层、反证和条件估值边界。

## 非范围

- 不修改 runtime、数据库 schema、生产状态、cron、凭证或客户端链接。
- 不增加投资阈值，不改变 A—F 评分、仓位矩阵或现有估值主轴。
- 不把客户或平台发布直接映射为公司订单或利润。
- 不清理 Hermes 中误建的非 canonical 同名目录；该操作单独授权。

## 验收标准

1. Research Skill 能路由到存在的 `references/catalyst-cycle-analysis.md`。
2. 参考文件要求刷新行情、区分事件/订单/财务兑现、列出最强反向变量，并只输出可复算的条件区间。
3. 聚焦契约测试、Skill validator、Ruff 和 `git diff --check` 通过。
4. Hermes 正式 research symlink 读取到仓库中的新参考文件。

## 回滚

基线 commit：`cbe6a098b29aee3ff9cc88bb3bb19e588ae14c4f`。回滚只恢复本次新增/修改文件，不执行 reset 或 rebase，不触碰生产状态。
