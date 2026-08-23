# Research 数据能力补齐与 Skill 渐进披露规范（2026-08-23）

状态：implemented and deployed
用户授权：2026-08-23 明确要求按顺序执行复盘、PS、最新财报快照与 Skill 拆分
生产状态：2026-08-23 经用户单独批准后切换至 suite `0.1.4` / lib `0.5.1`

## 目标

1. 为 F 科技框架提供同口径 `ps_ttm` 与近 5 年历史分位，关闭现有系统性 `incomplete` 缺口。
2. 在年度评分基线之外提供最新中报/季报方向快照，支持 Research 执行既有“最新报告冲突门”。
3. 对 `a-stock-research` 做行为保持型渐进披露拆分，降低主 Skill 体积而不隐藏安全边界。

## 非目标

- 不改变 A—F 框架、评分阈值、红黄线、仓位矩阵或唯一动作出口。
- 不实现 PEG、机构一致预期、自动评分、自动交易或新的数据库 schema。
- 不用单季利润机械年化，不把最新报告快照自动解释为趋势已改善或恶化。
- 不改生产数据库、cron、配置、凭证、三端入口或已安装 runtime。
- 不在本轮清理旧仓库、建立回测平台或新增依赖。

## R1：F 框架 PS 数据合同

- 数据源必须复用 `a_stock_lib.providers.TushareValuationProvider.fetch_valuation_history` 已返回的 `ps_ttm`；不得新增第二 provider 或 WebSearch 近似值。
- fetcher 输出：
  - `ps_ttm`：最新有效交易日的正有限值；
  - `ps_percentile_5y`：截至同一交易日，近 5 年窗口内每月最后一个有效 `ps_ttm` 的 strict-less 分位；
  - `_ps_percentile_window`：`sample_start`、`sample_end`、`valid_months`、`basis=ps_ttm`、`source=tushare.daily_basic`。
- 当前值与历史样本必须来自同一 TuShare 字段、同一代码、同一截至日。
- `ps_ttm` 缺失、非有限、非正，或有效月份少于 60 时，两项均不得伪造；记录 `null_reasons`，F 框架继续 `incomplete`。
- 手动 `FETCHER_DATA_SOURCE=akshare` 路径不新增 PS 近似能力，明确返回缺失。

## R2：最新中报/季报方向快照合同

- 完整年报仍是现有基本面评分和 PE/PB 重算基线，不改变现有年度字段含义。
- `a-stock-lib` 的 `fina_indicator` provider 增加官方字段：
  - `or_yoy`：营业收入同比增长率；
  - `dt_netprofit_yoy`：扣除非经常损益后的归母净利润同比增长率。
- fetcher 从最新已公告、非年报报告中输出 `latest_report_snapshot`；若最新报告就是年报，则 `is_newer_than_annual=false`，不得伪称存在更新季报。
- 快照至少包含：
  - `report_period`、`announcement_date`、`source`、`is_newer_than_annual`；
  - `revenue`、`revenue_yoy`；
  - `net_profit_parent`、`net_profit_yoy`；
  - `deducted_net_profit_yoy`；
  - `roe`、`bps`、`equity_parent`；
  - 每个方向字段的 `direction=up|down|flat|missing`。
- 对累计报告数字只按官方同比字段判断方向；不得自行把累计值除以季度数或年化。
- 不同 endpoint 必须按同一 `end_date` 合并；公告日期取可验证的 `f_ann_date/ann_date`。同报告期重复修订取最新公告记录。
- 缺失字段保留 `null` 与字段级 `status=missing`；不得因此丢弃仍可用的其他字段。
- 快照只提供冲突核验事实，不自动修改 `scoring_status`、配置评级、时机评级或仓位动作。

## R3：Research Skill 渐进披露合同

- 主 `SKILL.md` 必须继续保留：触发边界、W1 写入门、fetch→check 串行门、数据新鲜度/口径/季报冲突门、行业路由、评分结构、`incomplete` 规则、唯一动作出口、QA 边界。
- 只把详细执行表和长模板下沉到最多三个直接 reference：
  - 周期位置与压力测试细节；
  - 择时调整（预期差、除权、风格、异动）细节；
  - 报告输出与操作建议模板。
- 主文件保留每个下沉 reference 的适用条件、硬结论和直接 Markdown 链接；不得把安全规则只藏在 reference。
- A—F 框架、格雷厄姆和 catalyst reference 路径保持有效。
- 拆分前后的关键契约标记、阈值、公式和禁止条款必须由测试逐项固定；不要求逐字相同。

## R4：版本与兼容边界

- `a-stock-lib` 候选版本升级为 `0.5.1`，只增加财务字段，不删除或重命名已有字段。
- `a-stock-agent-skills` 候选版本升级为 `0.1.4`，安装器明确要求 `a-stock-lib==0.5.1`。
- 默认已安装 `0.1.3/0.5.0` 在影子验证和生产批准前保持不变。
- 不修改数据库 schema；新增数据只进入现有 fundamentals JSON payload。

## 验收标准

1. PS 聚焦测试先 RED 后 GREEN：能区分 5 年与 10 年样本，月末去重正确，少于 60 个月 fail-closed。
2. 最新报告测试先 RED 后 GREEN：同一 fixture 同时含年报和 Q1/H1，年度评分字段保持年报值，快照取最新非年报且不年化。
3. provider 测试证明请求并返回 `or_yoy`、`dt_netprofit_yoy`，缺失/修订记录行为明确。
4. Skill contract 测试证明主文件仍含所有硬安全边界，三个新 reference 可发现且路径有效。
5. `a-stock-lib` 全量测试、静态检查和 wheel 外部导入通过。
6. consumer 在默认 0.5.0 环境保持原测试通过；在 0.5.1 candidate wheel 影子环境中新增测试零跳过且全量门禁通过。
7. 独立只读审查无 blocker；父级核对最终 diff 和工作树。

## 回滚与停止条件

- 所有实现只在隔离 worktree；主 checkout、生产 DB、runtime、cron 和 active Skill 不变。
- 任一新增字段改变既有年度评分值、破坏 AKShare 手动降级、引入 schema 迁移、或 Skill 拆分隐藏安全边界时停止。
- 代码回滚：删除隔离 worktree/分支；生产未切换时无需运行时回滚。
- 生产部署若后续获批，必须保留当前 `0.1.3-8ce03e794f8a` runtime 与外部 rollback manifest，并在切换后回读版本、入口和真实只读 smoke。
