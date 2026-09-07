# A股投研与监控框架风控增强规范（2026-09-07）

状态：implemented and verified (2026-09-07)
用户授权：2026-09-07 投研审查与对抗审查结论落地
实施交付：Phase 0 至 Phase 5 落地已完成并通过独立审查与全库门禁

## 问题

现有框架已具备 A—F 确定性评分、最新财报冲突 fail-closed、L3 论文状态机、分框架价格止损与唯一动作出口，但实战中仍有四类会直接扭曲买入或持仓动作的缺口：

1. 研究评分前没有统一的监管与财报合规门。证券已被 ST/*ST、审计意见非标、公司被正式立案调查或已触及交易所分红风险警示条件时，低估值和高股息仍可能继续进入评分，形成“制度风险被估值分数覆盖”的错误结论。
2. 历史 PE/PB 分位默认盈利能力中枢可比。最新 TTM ROE 已显著低于过去五年中枢时，极低分位可能来自净利率、资产周转率或杠杆效率的结构性恶化，而不是均值回归机会。
3. 当前现金流质量主要依赖 CFO 或经营现金流/净利润近似，不能直接回答资本开支后还剩多少可分配现金；研发资本化和资本开支扩张还可能让利润、CFO 与真实自由现金流方向背离。
4. 第二档价格止损在个股风险与全市场流动性挤兑中使用同一执行节奏。全市场大面积跌停时立即形成卖出动作，可能把系统性流动性休克误判为个股论文破灭，且现实中也可能无法成交。

初审提出的大模型宏观状态机、ATR 动态止损和按波动率重写 Tier1，均缺乏稳定、可复算、可回归的增量价值。对抗审查后，本规范只保留四项客观门禁，不引入主观市场预测或参数拟合。

## 目标

1. 在 Research 评分之前增加一个确定性的监管合规前置门，覆盖上市风险标识、财务及内控审计意见、正式立案调查和适用板块的分红合规规则；证据缺失时 fail-closed。
2. 以同口径最新 TTM ROE 与最近五个完整会计年度 ROE 均值比较；最新值严格低于五年均值的 75% 时，使历史估值分位失去动作资格，并展示杜邦三因子劣化方向。
3. 以 `FCF = CFO - Capex` 生成可追溯的 TTM 自由现金流、FCF Yield 与资本开支覆盖状态；Capex 吞噬 CFO 时形成硬阻断，不再用 CFO 或经营现金流/净利润替代 FCF。
4. 第二档价格止损候选动作遇到同一时点全市场跌停家数严格大于 500 家时，只延迟一次 24 个自然小时；期满后按新鲜价格重新判定，既避免恐慌时点误杀，也不得无限续延纪律。
5. 四项机制均产出稳定状态、reason code、数据口径、来源和 as-of；QA 能据此拒绝缺字段、错误边界、主观改判和动作冲突。
6. 不改变既有 A—F 分值、Tier、L3、框架止损价、交易确认和 W1 写入边界；不新增数据库表、列或 migration。

## 非目标

- 坚决不建立由大模型判断牛熊、政策松紧、宏观流动性或风格轮动的 Regime Filter；模型不得从新闻叙事生成市场状态并改变仓位。
- 坚决不引入 ATR、波动率分层、隐含波动率、机器学习、回测寻优或逐股动态止损拟合；现有各框架第一档/第二档价格线保持不变。
- 不调整 Tier1 `+25%`、Tier2/3、分批比例或估值退出阈值；Tier1 继续明确标注为待历史回放验证的启发式基线。
- 不破坏确定性评分与 fail-closed 架构，不修改 A—F 权重、阈值、评分公式、双轨矩阵、L3 优先级和唯一动作出口；硬门只决定评分/动作是否有资格，不创造第二套买卖建议。
- 不把 ST 等同于退市，不把立案等同于违法事实已经成立，也不把任何单一红旗直接改写成自动清仓指令。
- 不以利润表研发费用加回、资产负债表科目变动或 EBITDA 近似真实 FCF；不发明“存贷双高”或研发资本化的未授权数值阈值。
- 不新增 Provider、生产依赖、生产数据库 schema、`user_version`、表、列或 migration；不修改生产数据库、持仓、交易账本、cron、配置、凭证和 active client。
- 本 proposed 规范只授权规范设计，不授权代码实施、生产安装、自动下单或任何生产写入；后续实现与 cutover 仍须分别确认。

## 契约

### P0：新国九条 ST 风险与财报合规前置排雷门

#### 1. 规则版本与证据边界

- `regulatory_gate` 必须在任何 A—F 评分前执行，按证券当日所属交易所和板块选择有效规则，不得把主板阈值套用到科创板、创业板或北交所。
- 规则集必须固化 `exchange`、`board`、`effective_from`、`checked_as_of`、适用条件、比例门槛、金额门槛、豁免条件、官方规则 URL 与规则版本；规则变更只能通过新的显式、 dated spec 和回归测试更新，不得由模型临场解释网页。
- 2026-09-07 基线以现行交易所规则为准：沪深主板只有在**最近一个会计年度归属于上市公司股东的净利润为正，且该年年末母公司报表未分配利润为正**的法定前提同时成立时，才计算分红不达标风险警示；此前提成立后，最近三个会计年度累计现金分红才按该板块规则检验“低于年均净利润的30%”与金额门槛是否同时成立。若当年归母净利润≤0或年末母公司未分配利润≤0，则该分红不达标子规则为 `not_applicable`，不得据此判 `blocked` 或 `clear`；亏损、未分配利润为负等情形另按其他适用财务风险规则核验。科创板、创业板的金额门槛及研发豁免按各自现行规则独立配置。现金回购是否计入分红、上市未满三个完整年度、合并/母公司未分配利润等板块特定条件必须逐板块按官方规则计算。
- 官方基线来源为[上交所股票上市规则（2026年4月修订）](https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/mainipo/c/c_20260424_10816589.shtml)、[上交所科创板股票上市规则（2026年4月修订）](https://www.sse.com.cn/lawandrules/sselawsrules2025/stocks/staripo/c/c_20260424_10816592.shtml)和[深交所股票上市规则（2026年修订）](https://docs.static.szse.cn/www/lawrules/rule/stock/W020260424747613955674.pdf)。仅因分红不达标实施的是其他风险警示 ST，不得误报为退市风险警示 *ST 或已经退市。
- 事实证据只接受交易所/证监会状态与公告、公司正式公告、年度报告及审计报告。聚合新闻、搜索摘要和模型推断只能用于定位原文，不能把门状态判为 `clear`。

#### 2. 输出合同

```json
{
  "regulatory_gate": {
    "status": "clear|blocked|incomplete",
    "action_eligible": false,
    "as_of": "2026-09-07T10:30:00+08:00",
    "exchange": "SSE|SZSE|BSE",
    "board": "main|star|chinext|beijing",
    "rule_version": "official rule name + effective date",
    "checks": {
      "listing_risk": {"status": "clear|blocked|incomplete", "reason_code": "..."},
      "audit_opinion": {"status": "clear|blocked|incomplete", "reason_code": "..."},
      "investigation": {"status": "clear|blocked|incomplete", "reason_code": "..."},
      "dividend_compliance": {
        "status": "clear|blocked|incomplete|not_applicable",
        "reason_code": "...",
        "preconditions": {
          "latest_annual_attributable_profit": null,
          "parent_unallocated_profit_at_year_end": null,
          "consolidated_unallocated_profit_at_year_end": null
        }
      }
    },
    "sources": []
  }
}
```

- 聚合优先级固定为 `blocked > incomplete > clear`；`not_applicable` 只允许用于有官方规则依据的不适用子项，并在聚合时视为该子项已完成，不得用来掩盖缺数。
- 任一子项缺少来源、as-of、报告期、规则版本或完成判定所需字段时为 `incomplete`；不得以“未搜到负面”推定 `clear`。
- `action_eligible` 仅在四个子项均为 `clear` 或有依据的 `not_applicable` 时为 `true`。

#### 3. 子门判定

1. **上市风险标识**：交易所已实施 ST、*ST、退市整理，或已公告终止上市决定时为 `blocked`；证券简称只是交叉校验，交易所状态和公告为权威证据。
2. **审计意见**：最近已披露完整年度财务报表被出具保留、否定或无法表示意见，或依法应披露的内控审计报告被出具否定/无法表示意见或未披露时为 `blocked`。无保留意见但含持续经营重大不确定性、强调事项或其他未更正重大错报说明时为 `incomplete` 并进入人工复核，不能直接判 `clear`。只有财务报表和应适用的内控审计状态均核验完成后才能 `clear`。
3. **立案调查**：公司因涉嫌证券违法、信息披露违法或财务造假收到证监会/有权机关正式立案告知时为 `blocked`，该状态只表示暂停形成新增风险敞口，不宣告违法成立。仅控股股东、实际控制人或董监高被立案时先判 `incomplete`；若官方文件明确事项涉及上市公司财务真实性、资金占用或核心经营资格，则升级为 `blocked`。解除必须依据正式结案、处罚决定及必要的财报更正/专项核查，媒体传闻或公司自述不能解除。
4. **分红合规**：先按版本化板块规则核验最近一个会计年度的法定前提，至少显式记录 `latest_annual_attributable_profit > 0` 与 `parent_unallocated_profit_at_year_end > 0`；深市等有额外合并报表条件的板块还必须记录该条件。任一前置字段缺失为 `incomplete`；任一前提≤0时，该分红不达标子规则为有依据的 `not_applicable`，不得把公司亏损或未分配利润为负误判为该项分红 ST。前提成立后，才对最近三个完整会计年度逐项计算累计现金分红、年均净利润、比例与金额双条件及法定豁免。已被交易所实施相应 ST，或完整数据确定同时触发该板块双门槛时为 `blocked`；只有前提成立且完整计算未触发才为 `clear`。其他财务类风险仍由上市风险标识等子门独立核验。

#### 4. 决策后果

- 首次研究：`blocked` 或 `incomplete` 时不得进入 A—F 评分，配置评级、时机评级、总分和仓位矩阵均为 `not_formed`，沿用 `scoring_status=incomplete` 并列出稳定 reason code；不新增 `scoring_status` 枚举。
- 已有持仓：冻结新增买入、Tier1 后补仓和 C/D 分级加仓，生成红色治理/合规复核候选并进入现有唯一动作合并流程；不得绕过活动论文/L3、交易所申报和用户确认直接清仓。
- P0 的 `blocked` 不受 P3 流动性延迟解释为“风险消失”；P3 只延迟价格止损候选动作，不修改监管事实。

### P1：ROE 结构性恶化阻断器

#### 1. 统一口径

- `latest_roe_ttm = TTM归母净利润 / TTM期初期末平均归母净资产 × 100%`。TTM 归母净利润必须由四个季度求和，或用“最近年报归母净利润 + 当期累计归母净利润 - 上年同期累计归母净利润”构造；不得直接加减各期 ROE，也不得把单季/半年 ROE 乘 4/乘 2 年化。
- `roe_5y_mean` 为 TTM 截止日前最近五个完整会计年度、同一会计口径 ROE 的算术平均值。追溯重述时全部使用重述后数据；少于五年、报告期重复、单位不一致、非有限值或口径无法对齐均为 `incomplete`。
- 先执行符号边界：`latest_roe_ttm` 为有效有限值且 `< 0` 时，P1 **无条件为 `blocked`**，不论 `roe_5y_mean` 为正、零还是负；不得因两个负数相除得到 `>=0.75` 而通过。若五年均值同时缺失/非有限，均值字段记 `incomplete`，但已由有效负值成立的阻断不得恢复为 `clear`。
- 当 `latest_roe_ttm >= 0` 且 `roe_5y_mean <= 0` 时比例没有有效经济含义，状态为 `incomplete`，历史 PE/PB 分位不得用于“低估”结论；不得用绝对值、行业均值或模型估计替代。只有在 `roe_5y_mean > 0` 且最新 ROE 非负时，才计算 `roe_retention_ratio = latest_roe_ttm / roe_5y_mean`；门禁使用未取整值比较，展示值可四舍五入至四位小数。`roe_retention_ratio < 0.75` 为 `blocked`；恰好 `0.75` 为 `clear`。

#### 2. 杜邦穿透与输出

- 在相同 TTM 与五年基线下展示 `net_margin = 归母净利润 / 营业收入`、`asset_turnover = 营业收入 / 平均总资产`、`equity_multiplier = 平均总资产 / 平均归母净资产` 的当前值、五年均值和变动方向。杜邦拆解用于说明劣化来自利润率、周转还是杠杆，不产生第二套阈值或人工豁免。
- ROE 输入足以触发 `blocked`、但某个杜邦分项缺失时，阻断仍然成立，分项状态记 `incomplete`；不得因无法解释原因而把已触发的 ROE 门恢复为 `clear`。
- 输出至少包含 `status`、两项 ROE、五个年度及其报告期、`roe_retention_ratio`、固定阈值 `0.75`、三个杜邦分项、source/as-of 和 reason code。

#### 3. 决策后果

- `blocked` 时所有依赖历史 PE/PB/PS 分位的估值项失去动作资格，`timing_status=incomplete`，不得把低分位解释为均值回归、不得输出新增买入/加仓矩阵；基本面机械分可作为诊断展示，但必须同时显示 `action_eligible=false`。
- `incomplete` 与 `blocked` 采取相同的估值 fail-closed 动作边界；缺数不是“未恶化”。
- 已有持仓触发时生成结构性盈利能力红色复核候选，冻结 Tier1 后补仓和其他加仓；是否减仓/退出仍由现有 L3、价格止损和唯一动作出口裁决，不自动卖出。
- 每个新财报期按同一公式重新计算；不得为个股临时修改 75% 阈值、改用三年均值或增加主观“行业周期例外”。

### P2：真实自由现金流与资本开支红线

#### 1. 公式与字段

- `CFO` 固定为合并现金流量表“经营活动产生的现金流量净额”。`Capex` 固定为“购建固定资产、无形资产和其他长期资产支付的现金”，在内部统一存为正的现金流出额；源数据为负号表示时只在适配层归一一次。
- `FCF = CFO - Capex`。TTM CFO 与 TTM Capex 均用“最近完整年报 + 最新累计期 - 上年同期累计期”构造；不得混用单季度、年度与累计值，不得以 EBITDA、净利润、每股经营现金流或资产负债表固定资产变动替代。
- `FCF Yield = TTM FCF / 同一 quote as-of 的总市值 × 100%`。分母必须是正的总市值而非流通市值；缺少新鲜总市值时 FCF 金额仍可展示，但 FCF Yield 为 `incomplete`。
- 研发资本化新增额、受限资金、货币资金与有息负债作为穿透披露项单列。资本化研发现金若已包含在 Capex 行中不得二次扣减；本规范不据此发明调整后 FCF 或新的“存贷双高”阈值。

#### 2. 红线与适用性

状态固定为 `clear|blocked|incomplete|review_required|not_applicable`；`review_required` 只表示 C/D 专项评估尚未完成，不能当作通过，`not_applicable` 只用于有正式规则依据的金融机构。

- `capex_redline=breached` 的一般规则仅适用于非 C/D 框架：有效 `TTM CFO > 0` 且 `TTM Capex > TTM CFO`；恰好相等时 `FCF=0`，记 `non_positive`，不误报为“Capex 超过 CFO”。
- `TTM CFO <= 0` 时对所有非金融框架记 `cash_generation_redline=breached`，C/D 也不得豁免。对非 C/D 框架，在 Capex 已归一为非负数的前提下，`TTM FCF < 0` 也必然为 `blocked`；`TTM FCF = 0` 时不得获得正向 FCF/FCF Yield 评价，但只有实际触发 redline 才标 `blocked`。
- **C/D 专属适配**：持仓/路由已确定且 `framework=C` 或 `framework=D`、`TTM CFO > 0`、`TTM Capex > TTM CFO` 时，`capex_redline=review_required`，总体 `cash_flow_gate.status=review_required`，**不得仅因 Capex>CFO 自动 `blocked`**。这表示进入资本开支周期与分红覆盖专项评估，不是无条件豁免。评估必须同时完成：①沿用现有第1.5步的 C/D 周期标签；②由年报、公告或项目披露证明 C 为扩产/并购等成长性资本开支，或 D 为大坝/机组等建设期资本开支，不能只接受管理层叙事；③完成对应 C/D 的分红压力测试；④披露 `cash_dividend_coverage = TTM CFO / TTM cash dividends`（`TTM cash dividends` 固定为同一追踪12个月内实际现金分红总额，须以公司公告/年报等正式证据核对；现金分红为0时记 `not_applicable`，但须有正式分红事实证据），且覆盖率 `<1` 时专项评估 `blocked`；⑤专项评估所需字段、来源、报告期、as-of 均完整，且不得覆盖既有 P0/P1、C/D 原有红线或已确认 L3。`fcf_dividend_coverage = TTM FCF / TTM cash dividends` 可为负，必须披露但不得把它改写成新的自动阈值。
- C/D 专项评估完整且上述条件通过后，`cd_capex_review=status=clear`、`cash_flow_gate.status=clear`，并将 `capex_redline=reviewed_cycle`；C 成长分支（派息率<40%）与 D 建设期均走此路径，保留其原有评分权重、周期判断和分红压力测试，不改变任何 A—F 分数或止损参数。评估不完整为 `incomplete`，证据显示非专属周期或现金分红覆盖不足为 `blocked`；框架未知/不自洽时不得授予例外，直接 `incomplete`。
- 银行、证券、保险等以资金为经营对象的金融机构记 `not_applicable`，继续使用其专属框架指标；不得用无意义的金融企业 FCF 阻断 B 框架。其他公司缺 CFO、Capex、同比累计期、总市值口径或 provenance 时为 `incomplete`。
- 输出至少包含 TTM 构造的三个期间、CFO、Capex、FCF、FCF Yield、`capex_to_cfo`（仅 CFO>0 时计算）、两个 redline、`cd_capex_review`（含周期/资本开支类型/分红覆盖及其证据）、适用性、source/as-of 和 reason code；字段只进入现有 fundamentals JSON payload，不新增数据库列，相关缓存写入仍受 W1 `--confirm-write` 与用户对具体内容的确认约束。

#### 3. 决策后果

- 非 C/D 的 `blocked` 或 `incomplete`，以及 C/D 专项评估尚未完成的 `review_required`/`incomplete`，均使 `scoring_status=incomplete`、`action_eligible=false`，停止配置评级、时机评级、总分和仓位矩阵；不得用“扩产期”“战略投入”等未按本节核验的叙事临场豁免。
- C/D 只有在专项评估明确 `clear` 且其他门均通过后，才能恢复本门动作资格；`FCF<0` 仍须原值披露，不得获得正向 FCF 评价。专项评估失败仍为 `blocked`，不得降级成普通警示。
- 已有持仓的任何 P2 `blocked`/`incomplete`/待审状态均冻结新增买入和补仓，生成现金流质量红色复核候选；负 FCF 本身不是自动清仓指令，减仓/退出仍须由有效 L3 或既有价格止损路径产生。
- `clear` 只表示本红线及适用的 C/D 专项评估已完成，不等同财务真实无瑕疵；研发资本化、受限资金和存贷并存异常仍须在报告中披露并按既有证据规则核验。

### P3：极端系统性流动性休克延迟执行

#### 1. 适用范围与市场快照

- 本门只作用于持仓行 `stop_loss_20` 所代表的**第二档价格止损候选动作**。该字段是历史命名，不代表所有框架固定下跌 20%；A/E、B/D、C、F 继续读取各自既有第二档实际价，不重算、不改系数。
- 第一档价格复查、已确认触发的活动 L3、监管合规复核、Tier 止盈和用户已成交交易不适用本延迟门。
- `limit_down_count` 统计同一快照时点沪深京全部正常设有当日跌停价的 A 股中，最新成交价等于交易所当日跌停价的证券数量；停牌和当日无涨跌幅限制证券不进入可统计分母，不得用指数跌幅、跌幅超过 9% 家数或模型情绪标签替代。
- 盘中快照须为同一交易日且抓取时不超过 120 秒；收盘后须为当日最终快照。Provider 必须返回 universe、eligible count、coverage/status、source 和 as-of。完整快照才可证明 `<=500`；不完整快照中已确认跌停数 `>500` 可按下界直接触发延迟，不完整且 `<=500` 时状态为 `incomplete` 并禁止立即形成价格卖出动作。

#### 2. 24 小时状态机

状态仅允许 `not_applicable|clear|deferred|untradeable|incomplete`；`action_eligible=true` 只允许出现在有效、可交易个股报价已确认且状态为 `clear`、或到期后恢复既有第二档动作的分支。

1. 第二档价格线未触发：`status=not_applicable`；但个股价格无效时不得伪装成未触发，必须为 `incomplete`。
2. 第二档已触发且有效 `limit_down_count <= 500`：先核验个股报价 `trading_status`。个股可交易时 `status=clear`，按既有第二档复查、目标减仓50%、可申报股数和用户确认规则继续；个股停牌、封死一字跌停/无流动性或报价无效时为 `untradeable` 或 `incomplete`，不得输出卖出股数。
3. 第二档已触发且有效 `limit_down_count > 500`：`status=deferred`，记录 `defer_started_at`、原始价格/止损线、市场快照与 `review_due = defer_started_at + 24 hours`；24小时为 Asia/Shanghai 自然时钟，周末/休市时在 `review_due` 后首个可取得有效交易快照的决策点复核。
4. `review_due` 前不得输出该价格止损的可执行卖出股数，只输出“系统性流动性休克观察中”；仍须照常核查 L3 和监管事实。若个股在此期间停牌或封死跌停，保持事件及 `defer_started_at`，不得以无成交价格清除候选。
5. `review_due` 到达后，必须取得个股新鲜且可交易的报价；`suspended=true`、`limit_down_locked=true`、无有效成交/流动性或报价无效时，分别记录 `status=untradeable` 或 `incomplete`、`action_eligible=false`，保留原止损事件和原 `defer_started_at`，不恢复动作、不清除候选、不伪造成交，也不新开窗口。直到首个有效可交易快照：价格高于第二档线才解除本次候选；价格仍在或低于第二档线才恢复既有第二档动作。市场跌停家数仍大于500时也不得重置或续延窗口。
6. 同一止损事件的 `defer_started_at` 不得因重复运行、进程重启或市场持续下跌而重置。实现须复用现有 `holding_alerts.reason_code/evidence/review_due` 保存一次性窗口，不新增表或列；任何写入仍走 W1 `--confirm-write`。未持久化成功时必须明确 `incomplete`，不得每次重新起算后声称已受控。

个股快照必须显式提供 `suspended`、`limit_down_locked`、`trading_status`、成交价、quote as-of 和来源；缺任一影响可交易判定的字段即 `incomplete`。`untradeable` 是“止损候选仍存在但当前不可申报”，不是恢复、清除或已成交。

#### 3. 优先级与动作边界

- 决策合并顺序保持：已确认活动 L3/治理退出条件 → P0/P1/P2 风险门 → 第二档价格止损（必要时由 P3 延迟）→ Tier/估值动作。最终仍只输出一个合并后的建议，不并列互相冲突的买卖动作。
- P3 只改变第二档价格止损候选动作的最早可执行时间，不改变止损价、目标减仓比例、L3 结论、账户风险预算、交易所可申报数量和用户成交确认要求。
- Skill 仍只生成和记录建议，不自动向券商下单；只有用户确认真实成交后，交易账本才可写入。

## 验证与测试计划

### 1. P0 单元与契约测试

- 主板适用前提（最近年度归母净利润>0且年末母公司未分配利润>0）成立，三年累计分红同时低于30%和5000万元时 `blocked`；任一前提≤0时分红不达标子规则为 `not_applicable`，不得误报为该项 ST；任一门槛恰好等于边界或高于边界时不因该规则阻断。
- 比例不达标但金额达标、金额不达标但比例达标均为 `clear`；验证双条件为 AND，不误写成 OR。
- 科创板/创业板规则、研发豁免、上市未满三个完整年度及北交所不适用路径按各自版本 fixture 判定，证明未套用主板常量。
- ST、*ST、退市整理、终止上市分别阻断，并断言分红 ST 不被输出为“已退市”。
- 财务审计保留/否定/无法表示意见、内控否定/无法表示/应披未披分别阻断；带持续经营重大不确定性的无保留意见进入 `incomplete`。
- 公司正式立案为 `blocked`；仅高管被立案且与公司财务关联未明为 `incomplete`；搜索无结果、来源非官方、过期规则或字段缺失均不得 `clear`。
- 验证聚合优先级 `blocked > incomplete > clear`，以及 Research 停止评分、Monitor 冻结加仓但不自动清仓。

### 2. P1 单元与契约测试

- `latest=12`、`5y_mean=16` 的恰好 75% 为 `clear`；略低于 12 为 `blocked`，门禁比较未取整值。
- 覆盖最新 ROE 为负且五年均值为正、负（例如 -10%/-20% 与 -30%/-10%）时均为 `blocked`，且不得被比值>0.75放行；另覆盖零/负五年均值、少于五年、重复报告期、非有限值、追溯重述和单位不一致。
- TTM 夹具验证“年报 + 当期累计 - 上年同期累计”且禁止单季机械年化。
- 三个杜邦乘积与 ROE 方向一致；任一杜邦分项缺失时保留已成立的 ROE 阻断并只把解释项标为 `incomplete`。
- 被阻断后 PE/PB/PS 低分位不得产生估值加分、买入矩阵或 Tier1 后补仓；未触发时现有 A—F 评分逐字/逐值保持不变。

### 3. P2 单元与契约测试

- 非 C/D 框架中 `CFO=100, Capex=40` 得 `FCF=60`；`Capex=100` 得 `FCF=0/non_positive`；`Capex=100.01` 严格触发 capex redline。C成长分支（派息率<40%）扩产/并购期与D建设期的 `Capex>CFO` 必须进入 `review_required` 而非自动 `blocked`；专项评估完整且分红现金覆盖率≥1时可 `clear`，证据缺失为 `incomplete`，覆盖率<1或非专属周期为 `blocked`；C/D 的 `CFO<=0` 仍为 `blocked`。
- 覆盖 CFO 为零/负数、Capex 源数据正负号归一、缺同比累计期、非有限值、总市值为零/缺失和 quote as-of 不一致。
- TTM 公式分别验证 CFO 与 Capex，不允许年度 CFO 配单季 Capex；FCF Yield 使用总市值并保留负值。
- 资本化研发已包含在 Capex 时只扣一次；货币资金、受限资金、有息负债只展示，不触发未经授权的“存贷双高”阈值。
- 银行/证券/保险为 `not_applicable` 且不误阻断专属框架；普通企业缺 FCF 输入必须 fail-closed；C/D 专项评估必须包含周期、资本开支类型、分红压力测试、现金分红覆盖率及官方 provenance。
- `blocked/incomplete/review_required` 时不得用 CFO、经营现金流/净利润或管理层“扩产”叙事替代通过，不得自动生成清仓动作；只有 C/D 专项评估明确 `clear` 才能恢复评分资格。

### 4. P3 单元与状态机测试

- 跌停家数恰好 500 家不延迟，501 家延迟；证明比较符为严格 `>500`。
- 不完整快照已确认 501 家允许延迟；不完整快照仅 500 家为 `incomplete`，不得推断市场正常。
- 盘中快照超过 120 秒、跨交易日、缺 universe/eligible/source/as-of 时 fail-closed；收盘最终快照可用。
- 24 小时前禁止价格止损卖出股数；恰好到期可复核。覆盖周五触发、周末到期、周一首个有效交易快照。
- 到期后只有个股取得有效可交易报价，且价格恢复才解除候选、仍跌破才恢复原第二档动作；停牌、封死一字跌停/无流动性或报价无效时保持 `untradeable`/`incomplete`，不得虚假恢复、输出股数或成交；市场仍有501家跌停也不得重置窗口或无限续延。
- 重复运行和进程重启读取同一 `defer_started_at`；W1 未确认或持久化失败时不得声称窗口已可靠记录。
- 验证 P3 不作用于第一档复查、活动 L3、监管事实、Tier 止盈或已成交事件；证券停牌/封板时不伪造成交。
- 覆盖全部框架实际第二档价，证明代码读取持仓 `stop_loss_20` 实值而非硬编码成本的 80%。

### 5. 回归、QA 与验收

1. 静态 contract tests 先 RED 后 GREEN，锁定四个门的字段、状态、reason code、边界符、优先级、唯一动作出口和 fail-closed 文案。
2. Research fixture 覆盖 P0 前置停止、P1 仅使历史分位失效、P2 现金流硬阻断及四门均 clear 的原评分不变路径；Monitor fixture 覆盖冻结加仓、一次性延迟和 L3 高优先级路径。
3. QA 新增四项独立检查：事实与官方来源完整性、公式/边界复算、状态与动作一致性、缺数是否 fail-closed；PASS 仍只代表报告合同合规，不证明事实真实或策略有效。
4. 现有 PB/BPS `valuation_compatibility`、最新报告冲突门、A—F 分数、Tier1 +25%、L3 语义门、交易所申报股数和 W1 门禁回归必须全部通过。
5. 在临时数据库比较实施前后 `PRAGMA user_version`、`sqlite_master` 表/索引/列清单，必须完全一致；生产数据库、配置、cron、active symlink 和持仓/交易行不得改变。
6. `bash scripts/check.sh`、`uv run pytest -q`、`uv run ruff check .`、`uv run python scripts/validate.py`、`python3 -I tests/qa/standalone_smoke.py` 与 `git diff --check` 通过；若命令在项目中重复，以 `scripts/check.sh` 的现有编排为准，不新增第二套验证器。
7. 冻结实际实现 diff 后执行一次独立只读审查；任何评分阈值漂移、P3 无限续延、负 FCF 被叙事豁免、监管缺数判 clear、第二动作出口或 schema 变化均为 blocker。

## 回滚与停止条件

- 后续实现必须按 P0→P1→P2→P3 分成可独立回滚的 bounded commit；规范文件本身不作为生产 cutover 授权。
- 任一实现若需要新增生产数据库表/列、外部生产依赖、宏观状态机、ATR/波动率拟合或修改现有评分/Tier/止损阈值，立即停止并重新请求明确授权。
- 回滚只 revert 对应实现 commit；不执行 reset/rebase，不修改生产持仓、交易事件或历史审计记录。
