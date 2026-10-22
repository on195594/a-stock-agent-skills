---
name: a-stock-monitor
description: "Use for held A-shares only (A股持仓). New: a-stock-research."
license: Proprietary
compatibility: Requires local command execution, the installed a-stock-agent runtime and a-stock-lib, plus network access for live monitoring.
---

# A股持仓监控

## 路由

`a-stock-monitor` 是已有持仓的唯一 Primary Skill。明确排除交易判断的公开数据子任务不得加载本 Skill；首次研究改用 `a-stock-research`。用户仅要求阈值历史回放或策略复盘验证时，跳过 Level 1，直接读取 [阈值回放](references/backtest.md)。

### Level 1：默认快照

先取得用户明确的账户总资产，再只读运行一次：

```bash
a-stock-cache monitor-snapshot --portfolio-value <账户总资产> --json
```

`monitor-snapshot --json` 输出是 `monitor-v1` machine contract；状态、动作、缺口和停止条件只从结构化字段读取，不从自然语言重建。

可附用户提供的 `--policy-file`、`--account-scope`、`--portfolio-value-as-of`，不得生成政策或确认引用。估值时点须用户或截图明确确认日期与时间，格式 `YYYY-MM-DDTHH:MM:SS+08:00`；手机设备状态栏时间不能替代资产估值时间，缺日期/时点则保持缺省并请求补充。展示 `risk_policy` 逐字段来源及分母时点/范围；`denominator_requires_review=true` 时即使 clean 也不授予加仓权限。2%/8% 是兼容默认，不是个人回撤目标；非法政策不得静默回退，确认元数据不是 W1 令牌。

通过宿主的命令执行工具调用 runtime CLI，保留 stdout、stderr 和退出码；不要在有硬超时的临时代码内核中包裹整轮监控。

保留退出码并解析 stdout；业务不完整时命令可能输出有效 JSON 后退出非零。解析前不得额外调用 `holdings`、Wiki、Web 或子代理。

- 先比对用户最新确认的持仓与快照；股数、清仓事实或账户范围冲突时，不把旧账本风险汇总当作当前账户结果，按下表账户差异路由请求最小对账资料，不改写快照或心算补齐。
- runtime 返回干净快速路径且无上述账户冲突时，输出结构化 `action_status`、异常项、覆盖率、as-of 与 `stop_reason`，立即停止。
- runtime 返回阻断、复核候选、触发、到期、异常或冲突时，仅对 `escalations` 指定的持仓和证据进入 Level 2。
- 缺少 required 数据时不得输出确定性无动作、继续持有或仓位不变；点名最小补数动作（如针对 governance_gates 过期指明执行 `a-stock-fetch fetch <代码>`；`regulatory_gate` 仍 incomplete 时按数据操作资料的“P0 监管门证据补录”，每个年报期一次），并冻结相关交易与风险变更。

### Level 2：按升级项展开

只加载与 runtime 升级原因或上述账户差异相符的资料：

| 升级原因 | Reference |
|---|---|
| 日常异常、公告、活动预警或 L3 | `references/daily-monitoring-and-l3.md` |
| 估值退出、技术候选或年度复核 | `references/valuation-and-annual-review.md` |
| C/D 加仓复核 | `references/step3.5-cd-accumulation.md` |
| A/E/F Tier 复核 | `references/step4-tier-system.md` |
| 账户差异、已成交补账或状态更新 | `references/data-operations.md` |
| `risk_budget_exceeded`、组合再平衡或任何加仓 | `references/portfolio-risk.md` |

`risk_budget_exceeded` 的 `code=null` 表示组合级只读复核：仅用本轮汇总、持仓和 `data_gaps`，不重查价、不心算补全风险、不调用 W1。兼容默认/显式覆盖不等于个人预算，禁止改参数绕过超限；超预算不能 clean/no_action，已有合法交易候选不降级。超限原因只引用明细中的 principal/unrealized_gain 与 `denominator_components`；快照未给出的卖出标的或股数不得提出。

动作冲突只服从 `references/decision-table.json` 及 runtime 输出。阈值、优先级、状态机、整手、组合风险与可执行性由 runtime/library 判定；Skill 不复算或从自然语言推断。

## 工具预算与停止条件

- Level 1 固定为一次 `monitor-snapshot`。快照拥有本轮持仓报价，不得重复查价或另起研究任务。
- 用户明确要求市场、国内宏观或 Fed 背景时，每个相关主题只取一个主来源；仅失败、不完整、过期或冲突时允许一次 fallback。
- 默认不启动研究子代理；只有单份长文档或一个有边界的关键证据缺口可例外，且子代理不得读取账户状态或作最终交易判断。
- 得到可执行动作候选、阻断结论或干净快速路径后立即停止；optional 新闻、宏观、历史估值和技术材料不得阻塞首轮交付。

## 默认交付

- 首屏只写：本次结论、相较上次的关键变化、首要风险、最小待办、下次改变判断的条件；仅比较本会话或用户提供的上次结论，不额外检索历史；无可比记录则说明首次基线，不编造变化。保留快照状态/覆盖率/as-of/停止原因；计算与完整证据按需展开。
- 持有逻辑、现价新增价值、账户风险贡献分开；不能新增不等于必须卖出，未确认退出也不等于可以加仓。不得仅因浮盈或“防御股”标签确定卖出顺序。
- 账户、证据和用户目标未变时，追问不改变行动结论，不凭空增加价格或股数；发现前次错误应明确纠正并解释依据，不能为保持一致延续错误。
- 缺口逐项说明缺什么、由系统还是用户补、影响哪项判断、补齐后复核什么及复核时点/事件；成本对账完成不自动解除财务门禁。能自行取得的公开证据不转嫁用户，已提供材料不重复索取；不可恢复时说明具体缺项。

## 安全边界

- 账户状态、alerts/L3/Tier、最终动作及交易授权始终由父级拥有；支持任务只提供公开证据。
- 数据缺失、过期、冲突、不可交易或 runtime 失败时 fail-closed，不得补造触发、股数或成交。
- 持仓、交易账本、预警、L3 与 Tier 写入均属 W1。仅在用户确认具体动作后追加全局 `--confirm-write`；建议、授权、申报与成交必须分开。
- 冻结新增风险仅约束拟议决策与建议授权，不阻断用户确认的已成交事实记账；即使实际买入造成超预算，也按原 W1 门禁记录并报告异常，不拒记、不改写成交。预算只读复核的 `requires_user_confirmation=false` 不授予任何写权限。
- `a-stock-qa` 尚无 monitor rubric，监控任务不得调用它。
- 本 Skill 基于公开信息和用户提供的账户状态，不构成投资建议。
