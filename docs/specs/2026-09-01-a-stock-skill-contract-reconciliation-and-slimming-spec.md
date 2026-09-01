# A股 Skill 数据契约对齐与第二轮渐进披露规范（2026-09-01）

状态：approved for implementation
用户授权：2026-09-01 明确批准执行 Hermes Skill 上下文治理计划

## 目标

1. 使 `a-stock-research`、`a-stock-monitor` 与当前 `a-stock-fetch` 输出能力一致。
2. 修复 monitor 对 PE/PS 5年分位能力的陈旧描述，但不把字段能力误写为当次必然可得。
3. 在安全门、资金动作和评分语义不变的前提下，将互斥任务的详细步骤按需下沉到 references。

## 非目标

- 不改 A—F 框架、阈值、L3、Tier、止损、仓位和唯一动作出口。
- 不改 fetcher/provider、数据库 schema、生产配置、cron、凭证或真实持仓。
- 不新增 Skill、provider、依赖、自动交易或近似数据源。

## 数据能力合同

- 当前 runtime 可输出 `pe_percentile_5y`、`pe_percentile_10y`、`pb_percentile_10y`、`ps_ttm` 与 `ps_percentile_5y`。
- 字段存在不代表当次必然可得。调用方必须检查值、as-of/window metadata 与 `null_reasons`；缺失、过期或口径不符继续 fail-closed。
- A 框架的 PE 5年85%线只能使用有效 `pe_percentile_5y`，不得用10年分位替代。
- F 框架可使用同口径 `ps_ttm` / `ps_percentile_5y`；AKShare手动降级路径不提供同口径PS_TTM，有效月份不足或字段无效时仍为 `incomplete`。
- E 框架 PEG 与 C 框架前瞻股息率仍需独立来源和 as-of 记录。

## 渐进披露合同

- Research 主文件保留 W1、fetch→check 串行门、数据质量/最新报告冲突门、行业与评分路由、`incomplete`、唯一动作出口和 QA 边界。
- Monitor 主文件保留 W1、任务路由、C01—C10、全局动作优先级、证据/价格/授权边界和各 reference 触发条件。
- Detailed cache/data commands、full research flow、日常 L3、估值退出和年度复查可下沉；任何硬安全规则不得只存在于 reference。

## 验收

- 文本合同测试先 RED 后 GREEN，固定 research/monitor 对 PE/PS 能力与 fallback 的一致表述。
- 每个按需 reference 有唯一任务路由、存在性检查和主文件 fail-closed 摘要。
- `bash scripts/check.sh` 全绿；独立只读审查无 blocker。

## 回滚与停止条件

- 每阶段独立 commit，可单独 revert。
- 任一阈值、动作、生产数据、数据库、runtime 或安全门发生非预期变化时停止。
