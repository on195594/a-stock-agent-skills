---
name: a-stock-research
description: Use when researching or analyzing A-share stocks for the first time, evaluating initial buy decisions, screening quality companies, comparing multiple stocks side by side, or assessing valuation for new positions. For monitoring existing holdings, stop-loss triggers, or sell signals, use a-stock-monitor instead.
license: Proprietary
compatibility: Requires local command execution, Python 3.13+, the a-stock-agent runtime, a-stock-lib, network access for live research, and configured market-data credentials.
---

# A股投研助手

基本面60分 + 择时20分 = 总分80分（基本面75%，择时25%）。数据源：WebSearch抓取东方财富、雪球、巨潮资讯。
缓存工具：`a-stock-cache`

## 写入安全边界

`holdings`、分析、预警、L3/Tier 和交易账本写入属于 W1：只有在用户确认具体动作后，才可在子命令前追加全局 `--confirm-write`。缺少该参数时 CLI 返回 3 且不打开写事务。数据过期、字段缺失或运行时失败必须 fail-closed，只能报告缺口，不能补造投资结论。

> **方法论说明**：本框架区分"配置价值"（公司值不值得持有）和"时机评级"（现在是不是好买点）。两者独立评分，最终仓位建议由两者共同决定。好公司≠好价格，高股息≠高赔率，这是框架的核心前提。
>
> 用户要求结合 AI、新品发布、旺季或半年产品周期判断行情时，读取 [催化与产品周期参考](references/catalyst-cycle-analysis.md)；必须区分事件催化、订单进度与财务兑现，不能把客户或平台发布直接视为公司订单。

## Reference map

- [A 通用框架](references/frameworks/A.md)
- [B 银行框架](references/frameworks/B.md)
- [C 资源框架](references/frameworks/C.md)
- [D 公用事业框架](references/frameworks/D.md)
- [E 消费框架](references/frameworks/E.md)
- [F 科技框架](references/frameworks/F.md)
- [格雷厄姆计算步骤](references/frameworks/step8-graham.md)
- [催化与产品周期参考](references/catalyst-cycle-analysis.md)

## 数据与缓存合同

按需读取[数据与缓存合同](references/data-cache-contract.md)：结构化数据默认走 TuShare，当前 runtime 可输出 `pe_percentile_5y`、`pe_percentile_10y`、`pb_percentile_10y`、`ps_ttm`、`ps_percentile_5y` 与非评分 `latest_report_snapshot`；字段存在不代表当次必然可得，必须核对值、as-of/window metadata 与 `null_reasons`。实时价只走新浪并校验交易日、交易时段、未来时间与盘中120秒最大年龄；10年期国债收益率走 AKShare；NIM/不良率/拨备及定性事实走 WebSearch。TuShare 故障只允许显式 `FETCHER_DATA_SOURCE=akshare` 手动降级，除交易日历外不得自动切源；AKShare 手动降级不提供同口径 PS_TTM。

## 有界首版与检索预算

用户只要求“研究/分析/对比”而未明确要求详细审计时，默认交付**有界首版**：保留本 Skill 的全部适用安全门、评分门和标准报告模块，但每个模块只写决策相关证据与结论，不扩展成新闻综述、链接巡检或技术指标大全。用户明确要求详细审计时再扩展证据深度。

- 安装态 `a-stock-fetch` / `a-stock-cache` 是结构化数据与当前价的首选入口。fetch 已成功取得并校验新浪当前价后，**不得再探测其他实时行情 Provider**，也不得用 TuShare/AKShare/第三方网页重复验证当前价；历史涨跌窗口只走已知可用的现有行情入口。
- WebSearch 只补结构化缓存没有的必需事实。优先交易所、监管机构和公司正式披露；通用搜索每批最多 4 个独立查询，每只股票默认最多一批缺口搜索。结果过大或被截断时，缩小到缺失字段，不得重复整批搜索。PDF 同一文件最多使用两种提取路径。
- 完成持仓路由、fetch/check、适用框架、checklist、确定性评分、最新报告冲突门、估值口径门、异动/治理/外部集中风险和形成动作所需的市场情绪后，即达到首版停止条件：**停止新增非阻塞补充检索**，直接生成简洁完整报告并进入 QA。URL 可达性复查、额外研报、重复行情源和不影响结论的技术信号不得阻塞首版。
- 已触发的 `incomplete` 若已固定唯一动作出口，不得再为融资余额、精确技术指标或其他非阻塞市场情绪字段探测临时 TuShare/AKShare/第三方 Provider；保留缺口并进入报告。缓存提供 `price_change_5d` 时直接复用，不再搜索同口径5日涨跌。
- 后台 QA 或其他异步任务只依赖宿主完成通知；不得轮询任务状态，不得用 `sleep` 等待。QA 运行期间也不得以“等待时顺便补证”为由修改其输入。

## 持仓路由（最先执行）

股票代码确定时，先只读执行 `a-stock-cache holdings <股票代码> --active-only` 核对该股票是否已持仓。可读账本返回 `NOT_HELD <代码>` 才表示已确认未持仓；`HOLDINGS_UNAVAILABLE` 表示账本不可用，不得伪装成未持仓。不得读取单股 monitor 的 `config.json` 代替真实持仓账本。

**确认已持仓后立即终止本 Skill**并改用 `a-stock-monitor`：不得继续执行首次研究的 fetch/check、评分或 QA，不得继续加载首次研究框架引用。只有用户明确要求重新做首次配置研究，才可在说明与当前持仓监控结论分离后继续本 Skill。账本不可用时须标注路由证据缺口；可以继续公开市场研究，但不得声称该标的是新仓，也不得据此给账户级仓位动作。

## 缓存检查（路由确认后，在第零步之前）

**必须按下列顺序串行执行，禁止并行**。只有 `fetch` 成功后才能运行 `check`；失败或行情过期时立即停止并报告缺口，禁止用 WebSearch 获取当前股价，也不得读取可能陈旧状态继续评分。

```bash
a-stock-fetch fetch <股票代码>
a-stock-cache check <股票代码>
```

输出状态码处理：
- `ANALYSIS_HIT`：直接输出今日缓存结论并附注“[来自今日缓存]”，**终止流程**；不得加载完整流程、继续搜索、评分、写缓存或运行 QA。
- `FUNDAMENTALS_HIT`：复用缓存，只补异动、治理/政策与外部集中风险；B银行另补 NIM、不良率、拨备覆盖率。**B框架三项核心数据全缺**时必须 `scoring_status=incomplete`，基本面总分、配置评级、时机评级、综合总分和仓位矩阵均输出 `not_formed`。静态PE（`pe_static`；`pe_ttm` 仅为 deprecated 兼容别名）不得用于 PEG；实时价不得重复搜索。
- `FULL_MISS`：读取[完整投研执行流](references/research-execution-flow.md)并执行全部适用步骤。

**所有量化框架的数据质量门仍在主入口生效**：
- `FULL_MISS` 必须用 dps÷当前价交叉验证股息率，误差 >0.5%（50bps）以计算值为准；`FUNDAMENTALS_HIT` 直接用已验证 dps÷当前价，不重复搜索 dps。
- ROE/NIM/净利增速等必须标报告期。PB 必须用当前已验证价÷同口径 BPS 重算；与列示值相差 >2% 时 PB、PB分位和择时估值不可用，停止时机总分、综合总分和仓位矩阵。
- **最新中报/季报冲突门**：读取 `latest_report_snapshot` 核验年报后方向；缺失再查正式披露。基本面方向冲突或无法同口径核验时 `scoring_status=incomplete`，不得机械年化单季利润，也不得把 TTL 内年报当作最新财务状态。PB/BPS 的 `valuation_compatibility` 仅控制择时，不得单独吞掉配置评级。
- `industry_status=stale_cache` 或 `missing` 时，必须从最新正式披露核验主营后再选 A—F；失败即终止量化评分并标记 `scoring_status=incomplete`。

### FUNDAMENTALS_HIT 最小数据卡

命中后必须先从同一份 `check` JSON 展示：当前价/quote as-of/来源、`price_change_5d`、`pe_static`/`pe_percentile_5y`、`pb`/`bps`及各自报告期、`dividend_yield`/`dps`、`latest_report_snapshot.report_period`、`fields.revenue_yoy`、`fields.net_profit_yoy`、`valuation_compatibility`、`scoring_status`、`timing_status` 与缺失原因。顶层字段无值时展示 `missing` 及 `null_reasons`；nested snapshot 字段无值时展示其自身 `status`，不得因正文未提到就把已取得字段误判为缺失。

`valuation_compatibility` 仅控制择时：`timing_eligible=false` 时 `timing_status=incomplete`，停止时机评级、综合分和仓位矩阵；若基本面评分完整，仍必须输出配置评级。旧缓存没有该字段时按 `reason_code=legacy_field_absent` 处理为 timing incomplete；不得在读取时重算、不得写回。只有基本面必需输入缺失或 latest-report 基本面冲突才能令 `scoring_status=incomplete`，此时基本面总分、配置评级、时机评级、综合分和仓位矩阵均明确输出 `not_formed`。

## 缓存写入边界

分析缓存、基本面、分数或预警的命令与字段结构见上方数据合同。任何写入仍属 W1：只有用户确认具体写入内容后才可使用 `--confirm-write`；`set-flag` 必须在同日 `set-analysis` 后执行。框架冲突、分数越界、必需输入缺失或 `incomplete` 时不得补造得分；D公用缺少24小时内可信国债收益率时 `score=null`、`timing.subtotal=null`。

## FULL_MISS 主流程硬合同

批量输入也必须逐股串行 `fetch`→`check`：`ANALYSIS_HIT` 直接复用，`FUNDAMENTALS_HIT` 只补缺口，`FULL_MISS` 才执行完整流程；最后统一横向对比。下列门、阈值和动作语义保留在主文件，执行细节在完整流程 reference。

### 预筛选、异动与行业路由

- 格雷厄姆门：EPS_TTM≤0 跳过；B用 PB<1.0；F用 PS分位+PEG；A 的警戒线为格雷厄姆数×2，E为×3，C/D仅作参考；C成长分支（派息率<40%）主轴改为PB历史分位。
- 5日内涨停/连板或3日涨幅>15%即异动股：市场情绪=0，再追加-3，时机评级上限★（≤12/20），且必须置顶追高风险；不得在矩阵后重复处罚。政策压制须置顶“政策逆风”。
- 行业路由：商业银行→B；能源/资源→C；水电/电网/水务/燃气/高速→D；消费→E；科技/互联网→F；其余→A。保险/券商/证券、亏损 Biotech、公募REITs不适用量化框架，只输出定性路线并终止评分/矩阵，不调用 `set-analysis`。混合业务按最近财年主营占比>50%路由，恰好50%的创新药+仿制药选A；无法判定时请用户确认。

## 第1.5步：周期位置判断（C/D/B框架必做，其余可选）

C/D/B 评分前必须判断周期位置；C还须核对动态变量、多业务段和分红压力。相邻阶段证据冲突取更保守情景。结构化标签、折扣顺序与压力测试见[周期位置与压力测试细则](references/cycle-assessment.md)。

## 第二步：基本面评分（60分）

- 框架只能按上方路由读取 A—F 对应文件。所有框架必须执行 `a-stock-cache checklist <代码> <框架>`；失败即停止，禁止纯人工加总。
- 主观“优/强”档至少需1—2项可验证证据，并输出映射后的两个 ASCII 双引号结构化标签；缺证据最高“格”。**A框架每次都必须输出** `外部集中风险[状态=正常|受限|重大；...]`；“重大”必须紧邻标注“置信度受限”，不得自动升级动作。
- checklist：达优可满分；简化判定未人工核验最高格档；达格最高格档（仅 note 明示“优档需人工判断”可凭证据上调）；未达只能0或红线；缺失按0并警告。框架未明确格档分时按满分50%。
- 汇兑损益绝对值>当期净利润绝对值30%时，净利增速必须对当期与基期都剔除汇兑损益后同口径比较。
- 报告草稿标签完成后必须执行 `a-stock-cache score-fundamentals <代码> <框架A-F> '<补充指标JSON>' < report-draft.md`。命令 `subtotal` 是唯一基本面分；保留 rule_version/hash、dimensions、missing_inputs、red_flags。`complete=false`、`blocked=true` 或命令失败时停止配置/择时/综合分和矩阵，禁止手工覆盖。

## 第三步：择时评分（20分）

| 框架 | 15分主估值信号 |
|---|---|
| A | PE低于近5年50%分位 |
| B | PB低于近10年30%分位 |
| C成熟（派息率≥40%） | 压力测试后前瞻股息率>5%且周期底部/上行 |
| C成长（派息率<40%） | PB低于近10年40%分位且周期底部/上行 |
| D | 股息率相对国债溢价>200bps |
| E | PEG<1，或PE低于近5年40%分位 |
| F | PS低于近5年40%分位；盈利时PEG<1.5 |

A/E/F 使用5年分位时**不得用10年分位替代5年分位**；E/F PEG 必须使用真实TTM盈利与可复核增长，静态 `pe_static`/兼容 `pe_ttm` 不得代替；F必须有同口径 `ps_ttm`/`ps_percentile_5y`。证据完整且满足信号记15，完整但不满足时**估值项记0/15**；任一所需分位、PS、真实PEG、报告期或交叉估值缺失/冲突时，估值项进入 `incomplete`，不得输出时机评级、综合总分或矩阵。

C成长分支还须核验至少一个前瞻/周期归一化指标；与PB方向冲突时输出 `估值冲突[...]`，该项不得记0/15，`set-analysis` 不传分。D溢价<150bps时择时上限10/20。历史分位<5%时必须排除ROE/盈利中枢结构性下移后才能解释为低估。

市场情绪只有融资余额和近期涨停/连板热度都有时点且均不亢奋才记5；明确亢奋记0；任一缺失即 `incomplete`。预期差、除权/除息、市场风格与异动的证据门和档位见[择时调整细则](references/timing-adjustments.md)。唯一顺序为 `raw = 估值分 + 市场情绪分 + 周期调整 + 预期差调整 + 除权/除息调整 + 市场风格调整 + 异动股调整`，再 `bounded=max(0,min(20,raw))`，最后应用D的10分和异动股12分上限；输入缺失不得计算。

## 第四步：双轨评级与唯一操作出口

配置评级：50—60=A，40—49=B，30—39=C，<30=D。时机评级：17—20=★★★，13—16=★★，9—12=★，<9=—。仓位矩阵保持：A×★★★=积极买入2/3、A×★★=1/3、A×★=轻仓、A×—=等待；B依次1/3/轻仓/小仓/观望；C依次轻仓/小仓/观望/观望；D均观望或回避。

**唯一操作出口**：动作只取双轨矩阵；综合分只展示。1/3、2/3是**已批准的单股风险上限**内分批比例，不是账户资金比例。只有总资产、单股风险预算、止损距离、已有持仓和行业/风格敞口完整且通过风险检查后才可换算资金/股数；否则只输出观察/试探/标准阶段标签。单行业上限40%，同风格上限60%；异动、风格和治理限制必须在矩阵前合并，不得另建出口。D缺24小时内可信国债收益率时 `timing.subtotal=null`、`score=null`。

## 第五、六步：治理、防韭菜与价值核查

复用异动搜索，禁止重复查减持/涨停/大宗折价；流通/总市值<40%须提示高限售比。大股东占款/违规担保只有官方公告/监管函/处罚决定可触发治理红线；触发后矩阵动作强制为“观望”，分数仅供参考。A/E买入前可按需执行格雷厄姆价值核查。

---

## 输出格式

报告必须按标准评估卡输出基本信息、估值/周期、基本面、红线、择时、双轨评级、唯一仓位建议、防韭菜与操作建议；多股使用统一横向对比。完整模块顺序、证据标签、持有期限要求和操作建议禁止条款见[报告与操作建议合同](references/report-contract.md)。

主文件中的数据完整性门、评分公式、唯一操作出口和 W1 写入授权始终优先；reference 不得形成第二套评分或动作。

## 质量合规检查（每次产生新分析后自动触发）

**触发豁免**：ANALYSIS_HIT 路径直接输出缓存结论，跳过 QA（无新分析内容可评估）。

完整分析报告输出完成后，先将正文冻结为**不可变快照**：优先直接按值传入；若使用文件，默认写入宿主按**本轮唯一临时目录**生成的版本路径，不得仅为一次报告新建 durable project，并记录内容哈希，QA 返回前不得覆写。任何正文修订都必须生成新快照并重新执行 QA，旧 verdict 只适用于旧快照。随后通过当前宿主的 Skill discovery/invocation 调用
`a-stock-qa`，传入 `skill_type=a-stock-research` 和该完整报告快照。宿主无法发现或执行
该 Skill 时，明确标记“QA 未执行”及原因；不得把未执行伪装为通过，也不得改用
客户端专属命令或子代理名称。

异步宿主必须依赖完成通知，不得轮询 QA 状态，不得用 `sleep` 等待，也不得在 QA 运行期间继续修改或补充其输入快照。**QA verdict 返回前不得向用户交付完整报告正文**；只能发送简短进度，最终报告在 verdict 合并后一次性交付。

QA 返回后，冻结正文仍不得覆写。下方规定的 verdict 标记属于交付元数据：需要文件交付时，从冻结正文生成新的交付副本并只追加对应的固定标记；任何其他正文变化都必须成为新快照并重新 QA。

**根据 verdict 处理**：
- COMPLIANT → 在报告末尾追加一行：`✓ a-stock-qa 合规检查通过`
- PARTIAL → 在报告末尾追加：`⚠️ a-stock-qa Minor问题：[FAIL检查项及说明（来自QA明细表）]`
- NON_COMPLIANT → **在报告首部置顶警告**（重新输出报告开头）：`⛔ a-stock-qa：以下步骤存在合规问题，报告可信度降低：[FAIL检查项及说明]`
- INVALID_RUN → 在报告末尾追加：`⚠️ a-stock-qa 输入无效，未形成合规结论：[原因]`；不得表述为报告不合规或合规通过
- SKIP → 在报告末尾追加一行：`⚠️ a-stock-qa 未执行：[原因]`

QA 发现 Critical/Important 问题时，只修正本次报告并说明根因。若根因疑似框架规则，
仅提出变更建议；不得在普通投研请求中修改 `SKILL.md`、framework、rubric、版本或
changelog。投资规则变更仍须独立 dated spec 和用户直接授权。

## P0-P3 硬门顺序（2026-09-07）

量化评分前依次核验 `regulatory_gate`、`roe_structural_gate`、`cash_flow_gate`；P0/P2 为 `blocked`/`incomplete`/`review_required` 时对完整评分 fail-closed，P1 则仅允许机械基本面诊断展示，必须将 timing/估值矩阵标为 `incomplete`/`not_formed`，不得让 PE/PB/PS 历史低分位形成买入或加仓资格。B/证券/保险仅在有正式规则依据时将 P2 标为 `not_applicable`；C/D 的 Capex>CFO 必须完成周期、资本开支和现金分红覆盖专项。

持仓监控只冻结新增买入、Tier1 后补仓和 C/D 加仓，不把四门红旗自动改写为清仓。P3 仅包装持仓实际 `stop_loss_20` 第二档：有效全市场跌停数严格 `>500` 时只延迟一次24小时；快照、报价、来源、as-of 或交易状态缺失即 `incomplete`，停牌/一字跌停为 `untradeable`，不得伪造成交或输出股数。
