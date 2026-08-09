# 全面审查问题修复规范（2026-08-09）

## 授权与目标

用户已明确要求解决 2026-08-09 全面审查列出的全部问题。本规范只覆盖该审查确认的
安全、可移植性、发布回滚和质量门禁缺口，不授权生产数据库、cron、客户端入口或凭证
变更。

## 范围

1. Skill 不得在普通投研流程中修改投资规则；规则变更仍须单独的 dated spec 和用户授权。
2. 行情日期/时间不可验证时，不得生成止损或组合风险动作。
3. R0 命令以 SQLite 只读模式运行，不执行 schema migration；`portfolio-risk` 改为 R1。
4. Installer 安装不可变 runtime，备份路径唯一，并在替换前持久化回滚 manifest。
5. 状态迁移显式比较 schema、user_version、关键表计数和持仓抽样。
6. Cron 校验外部配置权限，通知或底层检查失败必须非零退出。
7. Research/QA 和 validator 保持客户端中立，QA 只声明已有 research rubric。
8. 删除失效测试 runner、未维护的 mypy 门禁和仅供旧测试使用的兼容常量。

## 非范围

- 不改变 A—F 评分阈值、仓位矩阵、L3、Tier 或有效行情下的止损线。
- 不修改数据库 schema、生产状态、crontab、客户端链接或发送真实通知。
- 不新增生产或开发依赖。

## 验收标准

1. 已有空数据库执行 R0 命令后 hash、schema 和 migration ledger 不变。
2. 缺行情日期时 `check-holdings` 不触发预警；`portfolio-risk` 不使用该价格。
3. Installer 的 suite import 位于 release venv，连续同名备份不碰撞，拒绝覆盖发生在安装前。
4. source/target 任一受检迁移不变量不一致时返回非零；stdout 不打印持仓抽样。
5. Telegram 凭证缺失、发送失败、配置权限不安全或通知模式非法均返回非零。
6. active Skill 不含 AGY/Codex/Claude 专属执行指令，不会自行修改框架文件。
7. 项目声明的 pytest、Ruff、Skill validator、QA standalone、cron smoke 和 diff check 全部通过。

