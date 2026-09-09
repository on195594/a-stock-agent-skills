# A股首次研究可用性与 QA 完整性修复规范（2026-09-09）

状态：authorized for repository implementation
用户授权：2026-09-09「请根据以上分析结论帮我逐项修复」
范围：仓库代码、测试与 Skill 合同；不含生产安装、active client 切换、生产数据库/持仓/交易/配置/cron 写入。

## 问题

2026-09-09 立讯精密首次研究暴露以下缺陷：

1. QA 检查后的报告被再次改写，却沿用旧快照 verdict；同一执行主体手工模拟 QA 也被误标为独立通过。
2. fetch 汇总把内部全为 incomplete 的 gate dict 计作“字段有值”，而 check JSON 没有明确的数据完整度和决策资格摘要。
3. P1/P2 已可从现有 TuShare 财务历史构造，但 fetcher 未接线，导致门禁长期 unavailable；P0 仍需正式公告补证。
4. 不同报告期 BPS 的正常更新被当作 PB 冲突，并无差别冻结不依赖 PB 的框架。
5. EMS/ODM/连接器/精密电子制造在 A 通用制造与 F 科技之间边界不清；F 的毛利率、研发强度和 NRR 阈值不适合低毛利规模制造。
6. F 估值没有明确区分盈利 PEG 分支与亏损 PS 分支，runtime 也未提供真实 TTM 利润、PE 和 PEG。
7. P1 只应取消历史估值动作资格，却被 runtime 写成基本面评分 incomplete。
8. 默认报告过长、P3 在新仓报告中喧宾夺主；“无法确认买点”容易被写成“确认不适合买”。
9. QA 主要检查关键词，未清楚区分流程合规、数据完整和是否形成决策；正式 PDF 的真实标题也未纳入来源检查。

## 决策

### 1. 数据与门禁

- 复用现有 TuShare provider，不新增依赖、数据库 schema 或 Provider。
- 从现有 income/balance/cashflow/indicator 历史构造 P1 的真实 TTM ROE、五年 ROE 与杜邦输入，以及 P2 的 TTM CFO/Capex/FCF。结构化财务数据标注为 `tushare.* (company-filed statement mirror)`；该证据只用于 P1/P2 数值门，不得用于把 P0 上市状态、审计意见或调查状态判 clear。
- P0 自动证据仍不足时保持 incomplete；Research 必须以公司、交易所或证监会正式文件补证，并通过 `score-fundamentals` overrides 传入本轮 gate，不在读取时写回缓存。
- check 输出只读 `_decision_meta`：候选框架、框架置信度、`scoring_status`、`timing_status`、`action_eligible`、reason codes，以及按 provenance 计算的顶层字段/门禁完整度。评分尚未执行时使用 `not_evaluated`，不得伪装为 complete。

### 2. 估值

- 不同报告期 BPS 视为正常 `latest_report_update`：展示 annual PB 与 latest-report PB；全局 timing 不再失败。
- 因当前 PB 历史分位仍基于年度 BPS，`pb_percentile_eligible=false`，仅阻断实际使用 PB 历史分位的 B/C 成长分支；同一报告期数值差异超过 2% 仍为真正冲突并 fail-closed。
- F 盈利分支固定使用真实 TTM PEG<1.5；亏损分支只使用 PS<近5年40%分位，但在专门的现金跑道/稀释风险模型落地前不得形成买入矩阵，只能输出定性观察。
- runtime 新增 JSON 字段 `net_profit_ttm`、`net_profit_ttm_yoy`、`pe_ttm_true`、`peg_ttm` 和 `total_market_cap`，不复用 deprecated `pe_ttm`。

### 3. 框架路由

- EMS、ODM、电子组装、连接器、线束、声学器件与精密电子制造默认 A 通用制造；“元器件”不得仅因名称含科技属性自动进入 F。
- F 保留给半导体、软件、AI、互联网平台、信创、新能源设备等以技术产品/平台经济性为主的业务。
- 混合业务仍按最近财年主营收入占比 >50% 决定；无法证明时请求用户确认，不凭公司知名度路由。

### 4. 状态语义

- P0/P2 blocked/incomplete：`scoring_status=incomplete`，停止配置评级、时机、总分和矩阵。
- P1 blocked/incomplete：允许确定性基本面评分和配置评级；只设置 `timing_status=incomplete`、`valuation_action_eligible=false`，停止时机、总分和矩阵，不得覆盖 scorer 的 complete/subtotal。
- PB latest-report update 只影响 `pb_percentile_eligible`，不影响 PE/PS/PEG 框架。

### 5. QA 与交付

- 同一模型自行按 rubric 检查不算独立 Skill 调用；宿主不能真正调用时必须返回“QA 未执行”。
- QA 输入和最终正文哈希必须一致；任何摘要、翻译或删改都生成新快照并重新 QA。
- QA 输出增加 `process_verdict`、`data_status`、`decision_status`。COMPLIANT 仅表示文本流程符合合同。
- COMPLIANT 交付标记改为：`✓ a-stock-qa 文本流程检查通过（不代表数据完整、事实真实或建议可交易）`。
- 正式 PDF 引用必须核验首页真实标题、公告日期和发布主体；搜索摘要只用于定位，不得替代文件身份。

### 6. 默认报告

默认有界首版改为五段决策卡：结论语义、数据卡、基本面/估值、P0-P2 风险门、唯一动作与复核条件。用户明确要求详细审计时再展开原 12 模块。P3 对未持仓研究只写一行“不适用”。

动作词固定：

- `回避`：已确认阻断红线；
- `等待`：数据不足或买入条件未满足；
- `买入候选`：全部门与矩阵均已形成。

## 验收

1. 不同报告期 BPS 更新不再全局冻结 F/A/E；同期间 >2% 差异继续阻断。
2. 002475/“元器件”“连接器”“精密制造”路由 A；半导体/软件仍路由 F。
3. 财务 fixture 可构造 P1/P2；缺期间继续 incomplete，不做机械年化。
4. check 明确显示 gate 完整度，不再把 incomplete gate 算成完整字段。
5. P1 未通过不清空基本面 subtotal/configuration rating；P0/P2 仍 fail-closed。
6. QA 合同禁止自审冒充独立调用，并约束最终正文哈希。
7. `bash scripts/check.sh`、standalone QA smoke、Ruff 和 `git diff --check` 全绿。

## 非目标与停止条件

- 不修改 A—F 分数、Tier、L3、止损比例或交易确认边界。
- 不新增数据库表/列/index/migration，不写生产状态，不安装生产 runtime。
- P0 若需要新增官方公告 Provider 才能自动 clear，本轮保持官方补证路径，不以 TuShare 或“未搜到”替代；自动化 Provider 另行评审。
- 亏损科技现金跑道模型不在本轮臆造；在正式规则落地前保持定性观察。
