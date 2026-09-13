---
name: a-stock-monitor
description: Use when an existing A-share holding needs an action decision, stop-loss/L3 review, periodic review, add/reduce/sell, or a confirmed state update. New positions use a-stock-research.
license: Proprietary
compatibility: Requires local command execution, the installed a-stock-agent runtime and a-stock-lib, plus network access for live monitoring.
---

# A股持仓监控

## 路由

`a-stock-monitor` 是已有持仓的唯一 Primary Skill。明确排除交易判断的公开数据子任务不得加载本 Skill；首次研究改用 `a-stock-research`。

### Level 1：默认快照

先取得用户明确的账户总资产，再只读运行一次：

```bash
a-stock-cache monitor-snapshot --portfolio-value <账户总资产> --json
```

`monitor-snapshot --json` 输出是 `monitor-v1` machine contract；状态、动作、缺口和停止条件只从结构化字段读取，不从自然语言重建。

保留退出码并解析 stdout；业务不完整时命令可能输出有效 JSON 后退出非零。解析前不得额外调用 `holdings`、Wiki、Web 或子代理。

- runtime 返回干净快速路径时，输出结构化 `action_status`、异常项、覆盖率、as-of 与 `stop_reason`，立即停止。
- runtime 返回阻断、复核候选、触发、到期、异常或冲突时，仅对 `escalations` 指定的持仓和证据进入 Level 2。
- 缺少 required 数据时不得输出确定性无动作、继续持有或仓位不变；点名最小补数动作，并冻结相关交易与风险变更。

### Level 2：按升级项展开

只加载与 runtime 升级原因相符的资料：

| 升级原因 | Reference |
|---|---|
| 日常异常、公告、活动预警或 L3 | `references/daily-monitoring-and-l3.md` |
| 估值退出、技术候选或年度复核 | `references/valuation-and-annual-review.md` |
| C/D 加仓复核 | `references/step3.5-cd-accumulation.md` |
| A/E/F Tier 复核 | `references/step4-tier-system.md` |
| 用户确认的交易或状态更新 | `references/data-operations.md` |
| 组合再平衡或任何加仓 | `references/portfolio-risk.md` |

动作冲突只服从 `references/decision-table.json` 及 runtime 输出。阈值、优先级、状态机、整手、组合风险与可执行性由 runtime/library 判定；Skill 不复算或从自然语言推断。

## 工具预算与停止条件

- Level 1 固定为一次 `monitor-snapshot`。快照拥有本轮持仓报价，不得重复查价或另起研究任务。
- 用户明确要求市场、国内宏观或 Fed 背景时，每个相关主题只取一个主来源；仅失败、不完整、过期或冲突时允许一次 fallback。
- 默认不启动研究子代理；只有单份长文档或一个有边界的关键证据缺口可例外，且子代理不得读取账户状态或作最终交易判断。
- 得到可执行动作候选、阻断结论或干净快速路径后立即停止；optional 新闻、宏观、历史估值和技术材料不得阻塞首轮交付。

## 安全边界

- 账户状态、alerts/L3/Tier、最终动作及交易授权始终由父级拥有；支持任务只提供公开证据。
- 数据缺失、过期、冲突、不可交易或 runtime 失败时 fail-closed，不得补造触发、股数或成交。
- 持仓、交易账本、预警、L3 与 Tier 写入均属 W1。仅在用户确认具体动作后追加全局 `--confirm-write`；建议、授权、申报与成交必须分开。
- `a-stock-qa` 尚无 monitor rubric，监控任务不得调用它。
- 本 Skill 基于公开信息和用户提供的账户状态，不构成投资建议。
