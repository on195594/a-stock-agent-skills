# 数据与缓存合同

仅在持仓路由确认未持仓且需要刷新/读取结构化数据，或用户已明确授权写入分析缓存时读取。主 `SKILL.md` 的 W1、fetch→check 串行门、数据质量门和 fail-closed 规则优先；本 reference 不形成第二套动作或授权出口。

## 数据源边界（TuShare 2000 积分）

- 结构化数据默认使用 TuShare：`daily_basic`、`fina_indicator`、`income`、`balancesheet`、`cashflow`、`dividend`、`trade_cal`。`daily_basic.ps_ttm` 同时提供当前 `ps_ttm` 与同口径 `ps_percentile_5y`；财务端保留完整年报评分基线，并额外输出非评分 `latest_report_snapshot`。
- TuShare 分红接口返回每股口径；`fetcher.py` 在适配层转换为内部每十股口径，缓存字段 `dps` 仍统一表示每股分红（元/股）。
- 实时价格使用新浪单源，并按交易日、交易时段、未来时间和盘中120秒最大年龄校验行情时间戳；这不是 TuShare 2000 积分覆盖的实时行情接口。
- 10年期国债收益率继续使用 AKShare；TuShare `yc_cb` 需要单独权限，不因 2000 积分自动开通。
- 新闻、政策、银行 NIM/不良率/拨备等定性或非结构化信息继续使用 WebSearch。
- 结构化接口故障时可手动设置 `FETCHER_DATA_SOURCE=akshare` 切换旧链路；默认值为 `tushare`。除交易日历外，不自动在 TuShare 与 AKShare 之间切换。

## 缓存检查（路由确认后，在第零步之前）

**必须按下列顺序串行执行，禁止并行**。只有 `fetch` 成功后才能运行 `check`；`fetch` 失败时停止并报告数据缺口，不得读取可能陈旧的状态继续评分。⚠️ **禁止用 WebSearch 获取当前股价**——fetcher 使用新浪单源，并按交易日、交易时段、未来时间和盘中120秒最大年龄校验行情时间戳；新浪不可用或行情过期时行情获取失败。

```bash
# 必须先成功完成
a-stock-fetch fetch <股票代码>
# 仅在上一条命令成功后执行
a-stock-cache check <股票代码>
```

输出状态码处理：
- `ANALYSIS_HIT`：今日分析结论已缓存，直接输出结论，附注"[来自今日缓存]"，**终止流程**
- `FUNDAMENTALS_HIT`：基本面有缓存，直接使用缓存数据：
    - **以下字段从缓存读取，跳过搜索**：静态PE（`pe_static`；旧字段 `pe_ttm` 仅为 deprecated 兼容别名，不能作为真正 PE_TTM 用于 PEG）、PB、ROE、净利润增速、负债率、股息率、每股分红（dps）、PE历史5年分位（`pe_percentile_5y`）、PE历史10年分位、PB历史10年分位、近5个交易日涨跌（`price_change_5d`）、PS_TTM（`ps_ttm`）、PS历史5年分位（`ps_percentile_5y`）、最新中报/季报方向快照（`latest_report_snapshot`）、10年期国债收益率、流通比、毛利率、收入增速、流动比率、每股经营现金流、基本每股收益、每股净资产（bps）
    - **⚠️ B银行框架必须补搜（AKShare 无此字段，不可跳过）**：净息差（nim）、不良贷款率（npl_ratio）、拨备覆盖率（provision_coverage）。保险/券商不进入 B 框架，只做定性摘要后终止量化评分。
    - **⚠️ B框架银行 WebSearch 补搜失败降级规则**（仅适用净息差/不良率/拨备三字段）：
      - 单字段缺失：该维度记0分（净息差→0/10；不良率→0/15；拨备覆盖率→0/10），并在输出格式第5项前标注"⚠️ B框架[字段名]数据缺失，对应维度0分，基本面总分可靠性受限"
      - 三字段全缺：报告首部置顶"⚠️ B框架核心数据不可获取，本次评估结果不适用于投资决策，须补充数据后重新执行（建议直接查阅[公司名]最近年报或银行业监管信息披露页）"；**B框架三项核心数据全缺时必须 `scoring_status=incomplete`，停止基本面总分、时机评级、综合总分和仓位矩阵，不得把三个0分包装成完整结果**
    - **只补缓存缺口**：异动、治理/政策与外部集中风险；B银行框架另补净息差/不良率/拨备覆盖率。实时价格已由 fetcher 获取，不得用 WebSearch 重新获取价格
- `FULL_MISS`：完全未命中，执行下方完整分析流程

**⚠️ 股息率交叉验证（仅 FULL_MISS 必做；FUNDAMENTALS_HIT 直接信任缓存 dps，跳过本节）**：
1. 搜索获取：`[股票] 每股分红 最近完整年度`
2. 计算值 = 每股分红（dps） ÷ 当前实时股价
3. 若缓存/搜索值与计算值误差 > 0.5%（50bps），**以计算值为准**并在报告中标注差异原因（通常是股价变动导致）
4. 评分和操作建议均使用验证后的股息率，不得直接引用未经验证的缓存值；**FUNDAMENTALS_HIT 豁免：缓存 dps 视为已验证，可直接用 dps ÷ 实时股价计算股息率后引用**
5. B银行框架补搜三项核心字段，FUNDAMENTALS_HIT 和 FULL_MISS 均必做；**dps 验证搜索仅 FULL_MISS**：FULL_MISS 时银行额外搜 `[银行名] 每股分红 派息`；FUNDAMENTALS_HIT 时直接用缓存 dps，不再搜 dps

**⚠️ 数据口径标注（所有框架必做）**：
- ROE、NIM、净利增速等财务指标必须标注来源报告期，格式：`ROE 13.44%（2025年报）`
- 若缓存中 `data_period` 字段早于上一个完整年报，前置警告：「⚠️ 数据可能已过期，建议补搜最新年报」
- PB 必须使用当前已验证股价 ÷ 与历史 PB 分位相同报告期/复权口径的 BPS 计算，并同时列出股价时点、BPS 报告期和公式。若报告列示 PB 与重算值相差超过2%，视为口径冲突：PB、PB分位和择时估值均标记不可用，停止输出时机总分、综合总分和仓位矩阵，不得用第三方不同报告期 PB 继续评分。

**⚠️ 最新中报/季报冲突门（所有量化框架必做）**：当前结构化财务缓存以完整年报口径为主。先读取非评分 `latest_report_snapshot` 核验年报后是否已披露更新的中报/季报；如有，至少核对收入、扣非净利润、ROE/净资产及对应框架核心变量的方向。快照字段缺失时再查公司正式披露，不得把缺失方向补成“无冲突”。若新一期与缓存年度趋势方向冲突，或无法取得同口径数据完成核验，则 `scoring_status=incomplete`，停止配置评级、时机评级、综合总分和仓位矩阵；不得用单季利润机械年化替代TTM，也不得把“年报仍在TTL内”视为最新财务状态。

**⚠️ 行业路由新鲜度门**：fetcher 输出 `industry_status=stale_cache` 或 `missing` 时，历史行业只可展示，不得用于选择 A—F 框架、推断止损系数或形成量化结论。必须从公司最新正式披露核验主营业务后再路由；核验失败则终止量化评分并标记 `scoring_status=incomplete`。

## 分析完成后写入缓存

```bash
# ① 写入今日分析结论 + 框架 + 综合得分（框架必填；得分可选）
# 框架就是第一步行业识别时已经决定的那个（A通用/B银行/C资源/D公用/E消费/F科技），
# 直接传进来持久化，避免后续 add-holding/portfolio-risk 再靠 industry 关键词反推失真
a-stock-cache --confirm-write set-analysis <代码> <框架> <得分> << 'ANALYSIS_EOF'
<完整分析报告全文>
ANALYSIS_EOF

# 框架可用 A—F 简称或完整标签。未知参数、冲突框架、重复/越界得分均拒绝写入。
# D公用缺少24小时内可信国债收益率时：不传得分；报告只保存基本面小计，
# score=null、timing.subtotal=null、scoring_status=incomplete，禁止伪装成完整80分结果。

# ② 事后补录得分（向后兼容，需先执行 set-analysis）
a-stock-cache --confirm-write set-score <代码> <得分数字>

# ③ 写入基本面数据（TTL 按行业自动推断：银行/公用72h，消费12h，其余24h）
a-stock-cache --confirm-write set "<代码>" "<名称>" "<行业>" '<JSON>'

# ④ 若触发红线/黄线，记录预警（可多次调用追加）
# ⚠️ 注意：set-flag 依赖今日已存在 set-analysis 记录，必须先执行 ① 再执行 ④
a-stock-cache --confirm-write set-flag "<代码>" red "<红线原因>"
a-stock-cache --confirm-write set-flag "<代码>" yellow "<黄线原因>"
```

JSON数据结构示例：
```json
{"roe_3y_avg": 12.1, "gross_margin": null, "data_period": "2025年报",
 "null_reasons": {"gross_margin": "银行不适用"},
 "field_provenance": {
   "roe_3y_avg": {"source": "tushare", "as_of": "2025年报", "status": "ok"},
   "gross_margin": {"source": "tushare", "as_of": "2025年报", "status": "missing"}
 }}
```
> **字段说明**：`data_period` 为数据来源报告期（必填，如 "2025年报"/"2026Q1"）；`dps` 为每股分红（用于股息率交叉验证）；`pe_static` 是当前价÷最近完整年报EPS；`pe_ttm` 暂时保留为同值的 deprecated 兼容别名，绝不代表真实TTM。`pe_percentile_5y` 使用相同静态PE口径、披露滞后处理和近5年价格窗口。
