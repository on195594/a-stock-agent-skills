# Research 报告与操作建议合同

本页定义默认五段标准评估卡和可选详细审计。写入授权、评分完整性与唯一动作出口仍以主 Skill 为准。

权威机器状态只存在于已校验的 decision-v1 JSON。Markdown/`narrative` 仅供人阅读，不得从标题、动作词、标签或自由文本反推评分、阻断、周期、估值冲突或动作。写入时将完整 decision-v1 JSON 通过 stdin 交给 `a-stock-cache --confirm-write set-analysis`；旧记录没有 `decision_json` 时只能按 `LEGACY_ANALYSIS_HUMAN_ONLY` 展示，不得自动回填。

## 有界首版

用户未明确要求详细审计时，默认输出五段决策卡；每段只保留1—3条决策相关证据。强制门、状态和来源仍须出现，但不得用12个展开章节淹没“今天是否买”的答案。用户明确要求详细审计时，才展开基本信息、格雷厄姆、异动、周期、基本面六维、红线、压力测试、择时、双轨、综合分、防韭菜和操作建议原12模块。

正式 PDF 引用前必须核验首页真实标题、公告日期和发布主体；搜索摘要只用于定位原文。无法核验文件身份时写 `source_identity=incomplete`，不得把投资者活动记录、业绩预告或新闻摘要写成定期报告。

## 默认五段标准评估卡

### 1. 结论语义

首句必须在以下三种动作词中选择一个，并紧接原因：

- `回避`：已确认 P0/P2 或框架红线；
- `等待`：数据不足、时机条件未满足或矩阵未形成；
- `买入候选`：P0—P2、评分、择时和矩阵均已形成。

`incomplete/not_formed` 只能写“无法确认买点，默认等待”，不得写成已确认公司不值得买或已确认高估。

### 2. FUNDAMENTALS_HIT 最小数据卡

展示股票/代码、当前价/quote as-of/来源、行业与框架、缓存路径，以及：

- `price_change_5d`；
- `pe_static`/`pe_percentile_5y`；真实 `pe_ttm_true`/`net_profit_ttm_yoy`/`peg_ttm`；
- annual PB/BPS 与 latest-report PB/BPS、`valuation_compatibility`；
- `ps_ttm`/`ps_percentile_5y`、`dividend_yield`/`dps`；
- `latest_report_snapshot.report_period`、`fields.revenue_yoy`、`fields.net_profit_yoy`；
- `_decision_meta.scoring_status`、`timing_status`、`data_completeness` 和缺失原因。

`not_evaluated` 表示 scorer 尚未运行，不得写成 complete。“普通字段X/Y”和“决策门X/3”分开展示；gate dict 非空不等于门完整。顶层字段无值时展示 `missing` 和 `null_reasons`，nested字段展示自身 `status`。

### 3. 基本面与估值

展示确定性 scorer 的 subtotal、rule version/hash、关键强弱项与最新报告方向；未运行或被P0/P2阻断时写 `not_formed`，不得人工加总。

估值只使用适用框架主轴：A看PE5年分位；B看PB10年分位；C/D按各自周期/股息/FCF；E看真实PEG或PE5年分位；F盈利看真实TTM PEG，亏损看PS但在现金跑道/稀释规则落地前只定性观察。不同报告期 BPS 的 `latest_report_update` 不阻断 A/E/F；`pb_percentile_eligible=false` 只阻断依赖PB历史分位的分支。

### 4. P0—P2风险门

按 `regulatory_gate` → `roe_structural_gate` → `cash_flow_gate` 顺序输出 status、reason_code、source、as-of、报告期和action_eligible。

- P0/P2 blocked、incomplete或review_required：`scoring_status=incomplete`、`timing_status=incomplete`，基本面小计、配置评级、时机评级、综合分和矩阵均 `not_formed`；
- P1 blocked/incomplete：保留完整的基本面小计和配置评级，仅时机、综合分和矩阵 `not_formed`；
- “未搜到负面”不得作为 clear；
- 新仓报告的P3只写：`P3：not_applicable（未持仓，仅监控第二档止损适用）`，不展开500/501状态机。

### 5. 唯一动作与复核条件

动作只取双轨矩阵；综合分不得另建动作。任一合法 incomplete 阻断完整矩阵时，综合分与仓位建议均明确写 `not_formed`。1/3、2/3只表示已批准单股风险上限内的分批比例。缺总资产、单股风险预算、止损距离、已有持仓或行业/风格敞口时，只输出观察/试探/标准阶段，不换算资金或股数。

列出最多3个可验证复核节点。技术信号仅参考，不得把当日/近日涨跌或板块联动作为买卖主因。首次研究不输出持仓止损线；止损和L3由建仓后的 `a-stock-monitor` 负责。

## 详细审计附加要求

用户明确要求详细审计时，在五段卡后展开原12模块，并遵守：

- 所有框架的每个 checklist 子项标注「checklist核验」「人工核验推翻简化判定（含实际档位）」「⚠️ 无客观数据支撑，纯人工判断」或「⚠️ 数据缺失，未核验」；
- C/D/B补周期位置，C/D补分红可持续性压力测试；
- 双轨评级、综合分和仓位模块即使被阻断也保留标题并写 `not_formed`；
- C/D操作建议包含建议持有期限和可验证的周期退出触发条件；
- 临时L3核验必须写明已核验条件数，不能笼统称“L3未触发”。

## 操作建议禁止条款

- 禁止把当日/近日涨跌、板块情绪或未经验证的财务数字作为操作主因；
- 禁止混淆品种与公司；
- 禁止把单月/单季边际改善写成已确认长期趋势；
- 引用同比增速时必须同时披露基期绝对量或量级；
- 风险必须进入分数、门禁或动作约束，不能只放在免责声明；
- 加仓/不加仓理由必须是可验证的信息论据，不得使用情绪标签。

本 Skill 基于公开信息，不构成投资建议。数据无法取得时必须明确缺口，不得凭空估计。
