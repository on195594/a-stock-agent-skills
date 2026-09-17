# A-Stock 下一阶段实施规范

## 风险闭环、投资验证与简化架构

| 项目 | 内容 |
|---|---|
| 文档版本 | **1.1 — 工程与可实施性审查修订版** |
| 编制日期 | 2026-09-17 |
| 状态 | **ENGINEERING REVIEW INCORPORATED — DOCUMENT ONLY** |
| 实施状态 | 尚未开始；本文不构成已实施、已部署或投资有效性的证明 |
| 适用仓库 | `on195594/a-stock-agent-skills`、`on195594/a-stock-tracker`、`on195594/a-stock-lib` |
| 当前 canonical 位置 | `a-stock-agent-skills/docs/specs/2026-09-17-a-stock-risk-closure-and-performance-validation-spec-v1.1.md` |
| 当前授权范围 | 审查并修订本规范；不包含代码提交、生产部署、数据库迁移、cron 修改、真实账户写入或交易 |
| 后续开发方式 | 获得实施授权后，仅在 `master` 小步开发、验证、直接提交与 push；不创建功能分支，不开 PR，不 force-push |

> **下一阶段的主线：先使风险计算真正影响复核结论，再核实投资证据，最后衡量个人账户的真实表现。**
>
> 不重复抽取已完成的 `monitor-v1`，不推翻三仓分工，不通过增加模型、框架或架构层掩盖投资证据不足。

---

## 1. 本规范的定位与优先级

本规范将 2026-09-17 投资与架构审查转化为分阶段实施任务。它是针对当前实现的增量修订，不替代既有总纲、投资规则与生产安全约束，也不重新打开已完成的架构收敛项目。

规范阅读顺序为：**三仓总纲 → 当前架构 → 适用的专项规范 → 本轮实施任务 → 代码及验收证据**。既有规范与本规范发生实质冲突时，应列出冲突并取得裁决；不能自行宣布旧规则失效。

本次先后顺序固定为：

1. **S0：只读确认事实基线。** 区分远端代码、发布包、实际安装版本和生产证据。
2. **S1：修复 Agent 风险状态与复核路径。** 预算超限不得进入干净快速路径；缺失风险不得显示正常。
3. **S2：补齐 Tracker 证据资格与并列分数处理。** 保持生产评分不变，修正评估口径。
4. **S3：建设最小账户业绩闭环。** 复用交易账本，以可核实账户事实衡量净值、收益与回撤。
5. **S4：条件满足后开展下一轮投资实验。** 先简化基线、消融和可成交验证，再讨论扩张。

S1—S3 是有限的软件交付；S4 是有前置条件的研究任务，不能因前面测试通过而自动启动。上述顺序表示优先级，不是全部串行依赖：S0 后优先交付 S1；S2 软件无需等待 90 日样本成熟；S3a 政策解析和 S3b 业绩工具可分别授权，业绩计算不依赖政策模块。生产暂不可访问不阻止源码与合成 fixture 工作，但阻止相应生产验收。缺少三仓总纲原文也不阻塞有明确依据的风险修复。

### 1.1 本次修订的适用范围

1.1 版替代本文件的 1.0 版；仅消除本文内部的实施歧义，不自行废止其他已批准规范。主要修订是：显式只读事务、合同扩展的协调发布、预算与记账分离、确定的实验 manifest、先选样本后看收益、全同分裁决边界、文件型 CLI 的无数据库入口、账户输入与现金流边界、政策来源及分阶段验收。

本次执行了 **25 个独立参考检查**，用于验证 SQLite 事务机制和本文中的计算例子；它们不是三个仓库的回归测试。本文的 A/T/P 验收场景仍是待实施要求，未因此标记为已通过。

## 2. 已确认基线与证据边界

### 2.1 远端代码基线

编制时重新读取三个仓库的 `master` 引用，仍为：

| 仓库 | 固定审查提交 | 当前职责 |
|---|---|---|
| `a-stock-agent-skills` | `f3bbc44b5619316f7a616a9c1b81ce6419034f45` | 个人研究、监控、持仓、授权与应用运行时 |
| `a-stock-tracker` | `69f11c99d1720f2dad07113b46f17f5d87a3975d` | 固定观察池候选发现及策略研究 |
| `a-stock-lib` | `6dc856ea1183fe6f6c8ff9f5201b0c920b5008ec` | 跨消费者的共享确定性计算与数据合同 |

上述提交只用于定位本文证据。实施时必须重新读取远端 HEAD 并检查差异；已经修复的条目只补必要验证，不重复实现。[R1][R2][R3]

### 2.2 已完成能力，不再重复建设

`decision-v1`、`monitor-v1`、框架路由所有权以及薄 Skill 入口已经存在。监控本地状态已集中到同一个只读会话，但当前多次 SELECT 没有显式包在同一读事务内；不能把“单连接”当作“一致性快照”，本轮补齐该局部边界。现有持仓生命周期账本已处理买卖、费用、税费、现金分红、剩余市值及推断历史标记。[R4][R5][R6][R17][R18]

不得以本规范为由重新建设合同系统、交易事件总线、账户服务或独立编排层。

### 2.3 必须区分的事实层级

| 层级 | 可以证明 | 不能证明 |
|---|---|---|
| 源码与定向测试 | 指定逻辑在指定输入下的行为 | 生产已升级、真实账户已受保护 |
| GitHub CI | 指定提交通过其配置的检查 | 投资策略具有收益优势 |
| 生产只读证据 | 当时实际安装身份与真实运行输出 | 未来运行持续正常、未来收益 |
| 历史研究报告 | 规定样本和口径下的观察结果 | 可成交净收益或个性化配置资格 |
| 账户业绩报告 | 已核实账户事实下的表现 | 超额收益由 AI 因果性创造 |

上轮记录的三仓 CI 成功，不应复制成“本轮已重新运行全量测试”。本次重新读取三仓 HEAD，仍与表中一致，并抽查相关入口与辅助模块。未连接生产数据库、未部署、未运行仓库全量测试或生产任务；本文中的测试表都是**待实施验收要求**。

Agent README 记录的部署版本与仓库版本、Tracker 生产依赖与声明依赖存在差异。这属于需要核实的运行记录，不得直接认定服务器目前仍为该状态。[R7][R8]

## 3. 目标与非目标

### 3.1 交付目标

本轮应使系统具备三个可核查的结果：

**风险结论一致。** 同一份有效输入，在 JSON、文本和 Skill 路由中不能同时出现“超预算”与“无事可做”。

**投资证据可裁决。** 报告可以区分“样本不足”“可以进行方向复核”和“尚未证明可实盘采用”，并解释具体缺口。

**账户表现可追踪。** 外部入金不被当作投资盈利，持仓生命周期收益不被当作账户收益，历史不足不被补造。

### 3.2 明确排除

本轮不增加股票池、不调整评分权重与 44 分阈值、不恢复在线模型每日打分、不增加新投资框架；不建设自动交易、券商下单或无人确认的再平衡。

本轮不引入微服务、消息总线、独立 Model Gateway、多 Agent 管理平台、MCP/A2A 基础设施、向量库、图数据库、全量 DDD 或第四个仓库；不将两个消费者的 SQLite 合并或互相开放直接写入。

本轮不宣称实现财富自由、稳定超额收益或最大回撤保证。用户历史表达的 5% 回撤偏好不能自动写成账户阈值；其适用资产范围与当前有效性尚需明确。

## 4. 架构决策

### 4.1 三仓职责保持不变

| 仓库 | 负责 | 不负责 |
|---|---|---|
| Tracker | 分配研究注意力；候选、信号快照、实验与研究评估 | 真实个人持仓、交易授权、账户预算裁决 |
| Agent Skills | 分配个人风险预算；决策、持仓、监控、账本、业绩和复盘 | 全市场选股基础设施、共享数据供应平台 |
| Lib | 可复用的确定性计算、数据适配、来源与时效语义 | 账户状态、L3/Tier 生命周期、Skill 编排 |

两个消费者分别依赖 lib，不相互导入内部实现。未来确需交接候选时，先使用带来源、时间与版本的静态数据，不新增常驻中间服务。[R3][R4]

### 4.2 共享计算不等于统一策略

Tracker 的生产评分和 lib 的 A—F report-only 基本面评分不能仅因同名就被强制合并。财务口径、估值纯函数及数据失败语义可以共享；不同策略的目标、分数含义和验证记录应保持明确身份。[R3][R9]

本轮默认不修改 lib 公共接口、不发布新 lib 版本。Agent 私有需求留在 Agent；只有已存在的跨消费者需求才构成上移理由。

### 4.3 版本身份不得混用

| 身份 | 用途 | 本轮处理 |
|---|---|---|
| build/package identity | 实际代码及依赖身份 | 如实记录，不冒充投资政策版本 |
| scoring/policy identity | 决定输入、评分与阈值的规则身份 | 不改变当前 Tracker 生产评分 |
| evaluation identity | 资格检查、分桶、收益和回撤评估口径 | S2 增加明确的评估版本标记 |
| wire contract identity | JSON 字段和语义约定 | 保留 `decision-v1` / `monitor-v1`，只做必要修正 |

Tracker 当前 hash 包含评分相关源码和 lib 版本，因此无关升级也可能切开 cohort。本轮不得为了版本号整齐而升级生产依赖；不得未经等价性证据合并历史 cohort。[R10]

这里只补显式身份与说明，不建设版本注册中心，不改造整套 hashing 机制。

---

## 5. S0：事实基线与部署差异核验

### 5.1 仓库基线

执行者应记录各仓库 HEAD、工作区状态、适用规范、依赖锁及现有检查命令。发现未知本地改动不得覆盖；不得用 `reset --hard`、清库或 force-push 获得“干净基线”。

若本地存在尚未 push 的修复，先比对差异与测试，不得因远端缺少该提交而重复实现。尤其应重新检查非法 `stop_reason` 的类型处理。

### 5.2 生产只读核验

获得合法的生产读取条件后，记录实际 CLI 路径、解释器、包版本、可取得的制品标识、现有客户端入口与已部署 Skill 身份。无需输出账号、token 或完整环境变量。

Tracker 核验重点是：首个完整新 hash 批次、预定 35 股覆盖、PB 物化来源日期、`scoring_snapshot_json` 和定性来源快照、行情与基准截止日。

不能删除当天记录重跑，不能执行会刷新数据、修改状态或隐含迁移的“检查命令”。生产核验不得使用会做 schema bootstrap 的 `get_db()`；使用适用的只读连接并在多表核验期间建立显式读事务。仅凭 R0/R1 名称不能判断物理副作用。[R17][R20]

生产只读的保证是“不执行应用 DML/DDL、不迁移、不发通知、不改投资事实”。SQLite WAL 读取可能涉及 `-wal/-shm` 的存在、创建或共享内存行为；不能把活跃生产库及 sidecar 的文件 hash 不变当作唯一只读证明。确需物理零写核验时，使用已有、经授权获得的一致备份；不得仅复制活跃 `.db` 而遗漏 WAL，也不得对仍在更新的生产库添加 `immutable=1` 来规避锁。[R19]

### 5.3 输出与退出条件

输出一份脱敏基线记录，分别标记 `REPOSITORY_VERIFIED`、`PRODUCTION_VERIFIED` 或 `PRODUCTION_NOT_VERIFIED`。此处状态仅用于本轮执行报告，不要求新增平台级状态模型。

生产不可访问时，记录原因和缺少的证据，继续可独立完成的源码与 fixture 工作；不得将生产状态写成已通过。

## 6. S1：Agent 风险闭环修复

### 6.1 RISK-01：预算结论、复核与授权分开

**现状。** `commands_monitor.py` 已计算预算状态，但 review/action/clean 不消费该状态；此外，仅在总风险完整可算时才检查单股超限，可能漏报“已有明确超限、同时另有未知风险”的组合。[R5]

最小修改在快照生产者、现有合同和两个风险展示入口完成；不扩建风险引擎。输入校验与预算判断可提取为一个 Agent 内部的小型纯函数，所有入口传入相同的实际限额。原 `calculate_position_risk()` 的经济公式不在本轮改变。[R11]

预算状态按以下规则确定：

| 条件 | `account.risk_budget_status` | 解释 |
|---|---|---|
| 有效分母下，任一已知单股超限，或已知风险之和已超总限额 | `over_budget` | 即使其他风险缺失，已证明的超限也不能丢失 |
| 全部必要风险和分母完整，所有限额均通过 | `within_budget` | 只表示在本次有效参数内 |
| 无法证明以上任一项 | `null` | 未知；不能当作预算内或零风险 |

总风险不完整时，原完整合计字段保持 null；可增加明确命名的 `known_stop_risk_lower_bound`，不能把下限写进完整总风险字段。非法、陈旧或冲突报价不进入已知风险下限。禁止用 `(missing or 0)` 获得预算通过结论。

新增升级原因固定为 `risk_budget_exceeded`，同步修改 `monitor_contract.ESCALATION_REASON_CODES`、`commands_monitor._ESCALATION_REASON_ORDER`、生产者、测试与 Monitor Skill。单股升级带 code，组合升级允许 code=null；detail 展示金额、比例、限额、分母来源和作用范围。同一范围/代码的超限只产生一个确定性升级项，不持久化 alert。

新生产者在 `account.risk_policy` 附加输出实际单股/总限额、policy_id、source；S1 默认来源为 `compatibility_default`，不是个人已确认政策。合同只检查状态和必要字段的一致性，不在校验器内再实现第二份财务计算。

仅预算超限且其他数据完整时：

```text
review_status              = review_required
action_status              = review_candidate
stop_reason                = null
requires_user_confirmation = false
manifest.writes            = false
```

已有合法 reduce/exit 候选不得被预算 review 降级；stale/unavailable/conflicted 仍优先 blocked。`requires_user_confirmation=false` 只表示此次为只读复核，不授予 W1 权限。

**“冻结新增风险”只约束拟议决策与建议授权，绝不通过 W1 总开关阻断事实记账。** 用户明确确认券商已经成交的买入后，仍按现有 W1/具体动作授权要求记录实际成交，即使它使账户超预算；随后报告异常。不能为了让风险报表好看而拒记、改写成交或回滚真实交易。本轮不新增下单能力、不自动卖出、不降低止损线，也不重写既有交易业务门禁。

### 6.2 RISK-02：合同不变量与兼容性

`over_budget` 不能与 cleared、no_action、clean_fast_gate 并存。有活动持仓时，clean 还必须满足：预算可判定且 within_budget、行情与估值完整、无升级与缺口。账户数值有效、`quote_coverage.active == len(holdings)`；已存在的异常/冲突输出仍允许保留持仓明细以便诊断，不能为凑一致而删除异常记录。

真实空仓只保留基线原本允许的快路径条件，不新增绕过分母或其他 required 检查的空仓豁免。数据库失败返回空数组仍为 unavailable，不能等同空仓。

**v1 字段附加兼容不等于枚举扩展兼容。** 新 `risk_budget_exceeded` 对旧严格词表消费者不兼容；不得宣称旧消费者一定会安全理解它，也不得期待新生产者替旧程序控制异常。

本轮不改 `schema_version=1`，但必须作为一个**协调发布的 monitor-v1 扩展**记录在 runtime-contracts 中：候选制品包含匹配的 runtime、校验器、Skill 和命令适配。以 release commit + package/Skill hash 标识兼容集合，不新增协商协议或版本注册服务。

| 组合 | 要求 |
|---|---|
| 新生产者 + 新消费者 | 完整支持预算升级与当前安全不变量 |
| 旧生产者 + 新消费者 | 老数据缺新安全证据时受控拒绝/复核，不能补成 clean |
| 新生产者 + 旧消费者 | **不受支持，禁止混合部署**；负向测试记录旧行为，不把 traceback 说成已受控 |
| 历史捕获证据 | 继续验证原版本身份与历史行为，不拿它证明本版预算能力 |

同一个 v1 标签的此扩展只适用于已盘点、可协调升级的消费集合。若 S0 发现必须支持独立升级的外部消费者，本条进入 `BLOCKED_COMPATIBILITY_DECISION`，只阻塞该合同交付及部署；不能擅自推送破坏性 v1，也不能借机重建合同系统。

当前合成测试 fixture 可以补全必需字段；不可变历史模型捕获及来源 hash 不得重录或篡改为新通过证据。历史证明与当前完整合同测试分开，不新增可在生产启用的宽松 legacy 解析开关。

### 6.3 RISK-03：旧文本入口的未知风险

`cmd_portfolio_risk()` 使用与快照相同的必要输入校验。缺失、NaN/Inf、bool 伪数值、负/零非法价格及非法股数都不能进入正常分支。有效止损已被突破时仍显示破线，即使止损距离公式返回零。[R11]

输出同时区分：已知超限、不可完整判定、已破线。可打印已知风险下限，但数据不完整时不能宣称组合在预算内。JSON 与文本“一致”是指同一注入报价、账户分母和实际政策参数下结果一致，不要求两次独立联网查询的不同时间行情数值相等。

本入口的本地查询改为显式只读会话；缺 schema 返回不可用，不自动迁移。若已有局部只读实现已满足要求，只保留验证，不扩展为全仓数据库改造。

### 6.4 RISK-04：非法 stop_reason 的受控异常

先判断 `None` 或字符串类型，再判断允许值。数组、对象、bool、数字、未知字符串都抛出 `MonitorContractError`，不泄漏 TypeError；合法值仍为 null/clean_fast_gate。[R12]

Python 对象和 JSON 文本两条入口分别验证。已有 finite-number、未知附加字段和 `manifest.writes=false` 检查不退化。

### 6.5 阈值边界与 Skill 接线

S1 保留单股 2%、组合 8% 及严格 `>` 规则；不改变投资参数，也不在显示值四舍五入之后判断是否超限。CLI 的显式覆盖值必须显示真实来源，不能冒充默认值或个人已确认政策。

Monitor Skill 将 `risk_budget_exceeded` 映射至现有 `references/portfolio-risk.md`。code=null 表示组合级复核；只消费当前快照的汇总/持仓，不把它扩展成全组合重新研究，不重复查价、不调用 W1。缺少其他证据时只请求具体缺项，不通过模型心算补全风险。

### 6.6 定向回归验收

| 编号 | 输入场景 | 预期 |
|---|---|---|
| A01 | 数据完整、仅单股超预算 | review_candidate、对应升级项、无 clean |
| A02 | 单股均通过而组合累计超限 | 产生组合级升级项 |
| A03 | 恰好等于单股/组合限额 | 保持 `>` 边界，无政策变化 |
| A04 | 风险完整且预算内、无其他异常 | 保留合法快路径 |
| A05 | 缺有效止损、股数或价格 | 不显示正常，完整风险不可判定 |
| A06 | 缺有效组合分母 | 不宣称预算内，不生成确定性 clean |
| A07 | 已破线而剩余距离为零 | 保留破线语义，不解释为安全 |
| A08 | 超预算与合法交易候选共存 | 不降级原候选；数据/确认门禁不变 |
| A09 | stale/unavailable/conflicted | 保留 blocked 优先级 |
| A10 | 有效空仓 / 数据库失败 | 保留基线空仓条件；失败不当空仓 |
| A11 | 构造超预算+clean，或 active 数量矛盾 | 合同拒绝；不删持仓凑数 |
| A12 | 非法 stop_reason | 两条入口均为 MonitorContractError |
| A13 | 注入同一输入与政策给两入口 | 预算和未知风险结论一致 |
| A14 | 隔离 fixture 调用 | 无应用 DML/DDL、迁移、通知或真实网络；sidecar 单列说明 |
| A15 | 组合级预算升级的消费 | 只读有限复核；离线路由测试为必需，真实模型检查另列 |
| A16 | 新旧生产者/消费者交叉组合 | 按兼容矩阵验收；禁止不支持的混装 |
| A17 | 已知单股超限，另有持仓缺数据 | 保留已证实超限；不完整总额仍为 null |
| A18 | 超预算但用户确认已成交事实 | 现有事实记账授权路径不被新增预算逻辑误拦 |
| A19 | 两个连接在多表读取之间提交更新 | 读者只看到同一事务版本，无混合持仓/预警 |
| A20 | 查询异常或结束 | 读事务总能释放；报价网络不持有该事务 |
| A21 | 当前 fixture 与历史模型捕获 | 当前合同回归通过；历史来源 hash 不被改写 |
| A22 | clean 持仓缺预算安全证据 | 不靠历史宽松 fixture 放行生产输出 |

### 6.7 RISK-05：一次本地逻辑快照必须是一个读事务

在 `_load_monitor_local_snapshot()` 自有只读连接中，于首次 SELECT 前显式 `BEGIN DEFERRED`，完成全部持仓、预警、论文、Tier 和 L3 读取后结束只读事务；异常路径也必须 rollback/close。不使用 `BEGIN IMMEDIATE`，不把网络报价或模型调用放在事务内。若实际连接已处于读事务则复用，不发嵌套 BEGIN。[R5][R17][R18]

只读事务用于本地状态一致性，不声称行情和数据库跨系统原子一致。报价仍携带自己的 as-of，沿用数据门禁。优先在本地快照函数中增加这几行控制，不改变全局连接协议；未来其他读取是否需要同样能力另行评估。

A19 在临时 WAL 数据库用两连接复现：读者取持仓后，写者原子更新持仓及预警；读者随后取预警，必须仍看到旧预警。没有显式事务时可出现旧持仓+新预警。此测试证明机制，不是复制生产数据库。

**S1 完成条件：** A01—A22 获得对应仓库回归证据、现有关键门禁不退化。缺生产部署时标记 IMPLEMENTED_NOT_DEPLOYED。S1 可独立验收，不以账户业绩或成熟投资样本为前提。

---

## 7. S2：Tracker 投资证据与评估口径修复

### 7.1 EVAL-01：固定且有加载路径的实验 manifest

当前 `expected_size` 来自成功预测数；当前收益加载又在分桶前过滤行情缺失。仅更换分母或 tie-breaker 不足以修正评估，必须同时落实 §7.2—7.4 的调用顺序。[R13]

本轮只在报告层新增一份非敏感、可审计的实验声明：

```text
config/experiment_manifest.json
```

**2026-09-17 用户明确裁决：** 默认位置采用 Tracker 仓库规则的 `config/`，
替代本节原定的 `a_stock_tracker/reporting/experiment_manifest.json`。仅解决配置
目录冲突，不授权生产启用、真实 hash/日期登记、schema 或 cron 变更。

这是版本化实验配置，不是生产数据、账户状态或生成报告，允许入 Git。它替代 1.0 中没有定义加载方式的“仓库外冻结文件”建议。用 Tracker 既有项目路径 owner 定位该固定 `config/` 资源，不能依赖 cwd、开发者 home 或 sibling checkout；不得在运行时联网读取 GitHub。

| manifest 字段 | 必需含义与校验 |
|---|---|
| schema_version | 整数 1，拒绝 bool |
| experiment_id / framework | 非空实验标识；本轮 framework=A |
| universe_source | 仓库、固定 commit、config 路径及该文件 hash |
| expected_codes / universe_hash | 事先预定且唯一的六位代码集合；排序后 UTF-8 JSON 数组的 SHA-256 |
| scoring_hashes | 明确登记的精确生产 hash；本轮一个 hash 一项，不按长度自动认定合格 |
| effective_from / effective_to | 可证明的适用日期；不能按收益好坏选择起点 |
| registration_status / evidence_ref | `pending` 或 `verified`；登记依据是来源/部署/落库证据，不是收益结果 |
| windows / minimum_sections / min_coverage | 固定为30/60/90、3/2/1、0.90，不在加载时自动调优 |

建议文件 envelope 含 `experiments` 数组，为未知新 hash 保留明确失败行为；不是建设策略注册平台。已存在等价冻结配置时复用并达到相同合同，不复制第二份。

当前 35 股名单从其对应固定提交解析并校验 hash，不能手工凭记忆录入。生产 hash 或适用起点未核实时允许 pending，但 pending 只能输出诊断。运行时禁止自动把“最新出现的 hash”登记为 verified。仅包版本相同、hash 为16位或股票数为35都不足以证明注册匹配。

`build_accuracy_report(db, strong_threshold=44.0)` 保留现有调用兼容；可增加仅供注入的 keyword-only manifest/as-of 参数。默认自动报告从固定位置加载配置，无需新 cron、手工报告 CLI 或修改 `cli.py`。manifest 缺失、非法或不匹配时，自动报告输出 INSUFFICIENT_EVIDENCE 与具体原因，不让异常中止既有评分落库或伪装旧报告为本次成功。[R14]

必须展示 expected、实际唯一预测数、有效快照数、收益可计算数及排除原因。分母始终来自 manifest。35只、90%意味着至少32只；30只连续漏写不能自我缩小分母。

### 7.2 EVAL-02：快照资格与分层数据流

复用现有 `scoring_snapshot_json`、`qualitative_snapshot_json`、`qualitative_sources_json`、`qualitative_mode`，不新增生产列。[R14]

对修正后记录验证：所属实验及日期（score_date不得晚于evaluation_as_of，读取的结果价格也不得晚于该as-of）；code/framework/hash；对象类型及有限数值；scoring_inputs、weights、result、implementation；落库 quant_score/total_score 与快照结果按原舍入精度一致；定性分来源与各分项一致。金额/分数比较容差必须来自被记录精度，不随意用大容差抹平差异。

快照完整不等于财务输入全部非空。合法缺 PB、冻结缓存与明确 fallback 按冻结评分政策处理；fallback 的日期允许为空，但来源必须诚实。严禁用当前缓存补历史、用当前 scorer 重算旧分数来“修复”记录。时间可得性证据不足作为限制披露，不把财报期末当公告日。

建议在现有报告模块或一个局部 `evaluation.py` 中，使用简单函数/数据类形成以下**不可倒置**的数据流：

```text
只读加载预测、快照与价格序列（同次评估复用，不按窗口重复查全库）
  -> 按 manifest 确认预定集合
  -> 仅凭评分时快照筛出合格评分截面
  -> 按评分截面固定 Q1/Q5/观察池权重
  -> 按评分日期固定非重叠批次日程
  -> 才读取/对齐未来收益及逐日价格
  -> 计算带缺口状态的指标，渲染原有默认报告
```

建议函数责任：`load_qualified_score_sections` 不读取未来价格；`build_bucket_weights` 为纯函数；`select_non_overlapping_sections` 不接收未来收益；`evaluate_section` 不替换成员或批次。命名可与代码风格协调，责任不可合并回“先剔除未来缺价股票再排名”。

90%只用于**评分时证据覆盖**。有32个合格评分时，以这32只形成 n=32 的冻结截面，并披露另3只的评分时缺口；不得把35说成全部有效。池外、重复、冲突记录不能凑覆盖；同一代码的冲突不能挑高分记录，按缺口处理。

### 7.3 EVAL-03：固定批次、缺失路径与资格判定

保留30/60/90自然日和3/2/1个合格非重叠截面的门槛。每个窗口按评分日期升序、仅凭评分时资格选批次；一旦选中日期d，下一个可选日期不得早于d+window。**选择结果不依赖未来行情是否齐全。**

尚未到观察终点的批次记 immature；已成熟但缺价格的批次记 outcome_incomplete，不能改选第二天、替换股票或重新归一化。后续完整批次仍按原定日程保留，不能为了凑3/2/1跳过中间坏批次而称为连续结果。

市场日期和成熟度以明确的 Asia/Shanghai evaluation_as_of、现有本地交易日/数据可用规则确定。先在S0核实可用日历接口；无法证明交易日覆盖时输出 calendar/freshness 缺口，不用“全库最新日期”自证完整，不联网补取日历。沿用自然日窗口及既有端点对齐含义，但端点应对应可证明的适用交易日；陈旧端点只可诊断。

分指标处理缺失，不能只有一个含糊的“完整率”：

| 指标 | 所需数据 |
|---|---|
| IC | 固定评分截面全部成员的同端点收益；不删除缺收益成员后计算正式IC |
| Q5−Q1 spread | 两个冻结篮子的所有正权重成员收益 |
| Q5批次收益 | Q5全部正权重成员收益 |
| 观察池等权收益 | 评分时合格集合的全部成员收益 |
| 日收盘MDD | 对应冻结篮子在必要交易日的全部正权重估值 |

指标可分别为可用或N/A。某篮子日内路径缺失而端点完整时，端点收益可诊断，完整日收盘MDD为N/A。跨不完整批次不得几何链接为完整全区间收益；可以展示有明确起止日期的完整连续片段，但不替代原实验裁决。

报告内部使用一个小型结构化 summary，同时驱动文本，至少包含 experiment_id、manifest_hash、evaluation_version、scoring_hashes、as_of、逐窗 counts、selected_dates、gaps、metrics；不新增通用 wire 框架或并行报告链。默认仍由现有自动任务生成同一报告。

| evidence_status | 含义 |
|---|---|
| INSUFFICIENT_EVIDENCE | 来源、manifest、快照、日历/行情或成熟截面条件未满足 |
| READY_FOR_DIRECTION_REVIEW | 达到本实验方向复核条件，不表示统计显著、可交易或适合实盘 |

各窗口独立说明，总体要求三个窗口同时符合当前协议且相关路径无未解释缺口。缺失指标紧邻标记“诊断/不参与裁决”，不得只写在页脚。

全截面同分的处理按§7.4单列信号状态：完整数据下它可以进入人工方向复核，但不能将N/A转换为0代入旧“继续/简化/停止/重做”比较。旧预注册协议未定义此情形时输出 `verdict=MANUAL_REVIEW_REQUIRED`；不自行授权停止或继续策略。它不是需要无限延长采样才能承认的“未知数据”。

### 7.4 EVAL-04：统一并列权重与版本

IC保留已有平均秩实现。Q5/Q1按同一纯函数产生权重：n为评分时合格截面数，k=max(1,floor(n/5))；严格优于边界的m只各占1/k，边界同分g只各占：

```text
(k - m) / (g × k)
```

同分按已存储分数精度精确比较，不用未经授权的 epsilon 扩大同分组。Q1对称；权重和为1，输出排序可按code但不得以code决定经济权重。不得用未来收益或随机种子打破并列。

同一份权重由 spread、批次收益、逐日NAV/MDD共同消费；期初权重乘以各股累计价格比，不变成每日再平衡。缺必要未来行情只使相应指标不可用，不改变权重。

全同分标记 ALL_SCORES_TIED；IC、spread、Q5排序优势结论为N/A。观察池等权和基准仍可描述；完整数据的无区分能力计入人工方向复核，不隐藏事实。部分边界同分披露人数、权重、两端重叠比例。

本轮固定新的报告口径标识为 `2026-09-17.e2`；未采用本版完整资格/权重/批次规则的实现不得使用该标识。旧报告只能称 legacy，除非确有旧版本证据。修正旧数据上的派生指标允许，但必须写明 scoring hash、旧/新evaluation身份；原始预测不改写，历史报告不冒充同口径连续序列。

### 7.5 S2 测试与验收

| 编号 | 场景 | 预期 |
|---|---|---|
| T01 | 预定35只、长期只写30只 | expected=35，低于32门槛 |
| T02 | 总数够但含重复/池外/冲突代码 | 不凑覆盖，不挑高分冲突记录 |
| T03 | 缺失/损坏评分快照 | 显式缺口，不用当前缓存补造 |
| T04 | 合法缺PB或fallback | 按冻结政策接受如实记录，不增加行业筛选 |
| T05 | 全同分且更换code/输入顺序 | 不产生代码驱动优势 |
| T06 | 边界部分同分 | 权重和为1，经济结果对code置换不变 |
| T07 | 无并列且数据完整fixture | 除明确资格修正外保持原指标 |
| T08 | 端点与逐日路径 | 全部计算消费同一冻结权重 |
| T09 | 数量够但价格/基准/快照不合格 | 总体INSUFFICIENT_EVIDENCE |
| T10 | 未登记股票池/hash/日期 | 无自动注册或今天名单倒填 |
| T11 | 报告层改动 | 原始预测、权重与生产hash不变 |
| T12 | 数据完整但全同分 | 显示无信号；不将N/A代0；人工方向复核 |
| T13 | 已选成员缺未来行情 | 不补位、不重新排名/归一化 |
| T14 | 最早批次缺未来价格、第二天完整 | 不把批次顺延到第二天 |
| T15 | 中间批次不完整、后续恢复 | 全区间链不伪完整；片段独立标记 |
| T16 | 换cwd运行自动报告 | 找到固定manifest，不依赖home或网络 |
| T17 | manifest缺失/非法/pending | 生成明确降级报告；不影响已完成评分落库 |
| T18 | 快照分项与DB分数冲突 | 按记录精度检测，不重算历史修平 |
| T19 | 窗口未成熟/节假日/单股滞后 | 使用可证明日历；未知就报缺口，不看全库max自证 |
| T20 | 三个窗口的一次报告 | 复用同次只读输入；不新增schema/cron，不更新cohort |

**S2完成条件：** 软件可在合成manifest与数据库上完成全部回归；生产manifest未核实或真实样本未成熟不妨碍软件验收，但真实结果只能降级。报告生产启用另行授权；不把fixture中的hash/35股冒充真实登记。

### 7.6 仍未解决的投资边界

评分日收盘研究收益不是盘后信号可成交收益；Q5不是≥44名单。固定池、跨行业可比性、冻结定性分、成本、可成交性与仓位/退出仍未验证。[R8][R10][R13]

本轮修正样本和评估偏差，不承诺消除所有历史时点可得性问题；不升级lib、不改 `cli.py`/scoring/物化/定性源码的hash语义。若实现必须触及这些边界，单独说明新增cohort影响并请求对应授权，不能顺手改动。

---

## 8. S3：独立的政策解析与账户业绩 MVP

S3a=POLICY-01，S3b=PERF-01—04。可分别交付；业绩报告不以用户设置风险阈值、Tracker达到成熟样本或完成S3a为先决条件。

### 8.1 POLICY-01：小型、显式、无写入的有效参数解析

S1先使用兼容默认值；S3a才增加个人政策文件。路径选择为：本次 `--policy-file` → 既有runtime.env/环境中的 `A_STOCK_RISK_POLICY_FILE` → 同一XDG配置目录的 `risk-policy.json`。复用 `paths.py` 的所有者/权限和动态路径解析方式，但新增JSON解析不混入dotenv行解析，不在import时创建文件。[R21]

政策schema=1，最小字段固定为：policy_id、account_scope、currency(CNY)、effective_from、可选effective_to、confirmed_at、confirmation_ref、max_position_risk_pct、max_portfolio_risk_pct，以及可选drawdown_observation_target_pct。时间带时区，数值有限且0<limit≤100；bool不是数值。确认字段是可追溯元数据，不是W1或交易授权令牌。

两个风险CLI同时接通 `--policy-file`、`--account-scope`、`--portfolio-value-as-of`、`--max-position-risk-pct`、`--max-portfolio-risk-pct`；保留原 `portfolio-risk --max-position-risk-pct`。统一在handler之外解析为一个实际参数对象，禁止CLI一套/JSON另一套默认值。数字参数优先级为：用户明确授权的本次覆盖 → 已确认且生效、账户匹配的文件 → 兼容默认值。每个最终字段附来源。

显式路径不存在、已发现政策文件非法/未确认/过期/未来生效或账户不匹配时，受控失败/复核，不静默退回默认；只有确实未配置政策文件时才允许标明来源的兼容默认。CLI覆盖不能掩盖一个已经发现的无效政策文件，也不能由模型为了绕过超预算自行构造。个人阈值变化仍需具体授权，修改文件不在只读报告命令内发生。

分母金额不是政策常量。保留本次显式总资产，记录它的valuation as-of；缺少as-of或不能证明适用范围时显示denominator freshness/scope unknown，新增风险决策须复核，不能将报告采集时间写成资产估值时间。这里不另设一个未经用户批准的自动TTL或5%硬限额。

当前无个人政策的兼容路径必须明确“未确认个人风险预算”，不因通过2%/8%就宣称满足用户5%回撤目标。止损距离估计、已发生回撤、情景损失分开；本轮不加入情景引擎、优化器或自动再平衡。

### 8.2 PERF-01：文件型命令与现有 CLI 接线

S3b只支持一个显式账户、CNY、无融资/负债的现金加多头证券账户。权威资产来源是核实的券商日终总资产；第一版**不从历史持仓重建净值**，不导入第二套成交事件。现有账本仅作可选一致性对照。现金/持仓分项缺失不自动否定已经独立核实的券商总资产。[R6]

新增一个现有命令体系内的R0命令，不新增安装入口或服务：

```bash
a-stock-cache performance-report --input <account.json> [--benchmark <benchmark.json>] [--check-ledger] [--allow-eod-flow-assumption] [--json]
```

必须同步接入 `cache.py` 的 COMMANDS、COMMAND_CLASSIFICATION、_CLI_POSITIONALS、_CLI_VALUE_OPTIONS、bool flags以及帮助输出。**当前R0路径会在数据库不存在时提前返回0，因此必须让这一文件型命令绕过数据库存在性前置检查和“操作数据库”日志。** 只为本命令加局部例外或显式的file-only集合，不重构全部dispatch。[R20]

不带 `--check-ledger` 时不得打开数据库、联网、迁移或写文件；文件来源足够时，即使cache.db不存在也必须正常计算。带该参数才只读检查现有账本的可验证部分；缺数据库、未知历史或未完成对账只影响相应reconciliation状态，不凭空生成交易。真实差异显示为provisional并列缺口，不能伪造现金流“对平”。

输出默认stdout文本；`--json`只输出一个结构化结果。CLI不提供内建输出写入参数，保存由调用者明确重定向到仓库外artifacts；同输入的经济计算确定，生成时间等非经济元数据不参与结果相等比较。

| 退出码 | 语义 |
|---|---|
| 0 | 请求的计算成功；未要求基准/账本对账不作为失败 |
| 2 | 参数、输入JSON/schema/金额/账户类型非法；stderr错误，stdout不伪装有效报告 |
| 4 | 可解析业务报告，但请求范围存在数据、时点、日历、基准或对账缺口；stdout仍有完整状态 |
| 1 | 非预期I/O或运行失败；不输出成功业务结论 |

原其他命令退出语义不改。调用者先保留exit code，再解析有效stdout；不得把4当成无结果后启动无限补数或新研究。

推荐新增局部 `performance.py`（解析、Decimal纯计算、渲染），必要时拆一个命令adapter；不引入pandas/金融分析依赖。只读命令不得为格式化输出创建state目录或打开生产库。

### 8.3 PERF-02：固定输入schema，不让实施者临时发明格式

账户输入为UTF-8 JSON对象，schema_version整数1；字段如下：

| 字段 | 合同 |
|---|---|
| account_scope / currency / account_type | 非空脱敏范围、CNY、`cash_long_only`；整份输入唯一，禁止混账 |
| source_ref / valuation_basis | 脱敏来源；`broker_total_equity`，不支持自动推断历史净值 |
| expected_valuation_dates / calendar_source_ref | 可选的、严格升序且唯一的应估值日期清单及其来源；有清单无来源不证明日频完整 |
| observations | 严格时间升序的日终快照数组；同一上海日期不允许重复或冲突行 |
| valuation_at | 每行带时区，按Asia/Shanghai得到估值日，不使用客户端时区 |
| total_equity / cash / liabilities | Decimal金额字符串，最多2位小数；equity≥0、cash可null否则0≤cash≤equity；liabilities必须明确为0 |
| external_inflow / external_outflow | 各为非负Decimal字符串，覆盖 `(前一估值时点, 当前估值时点]` 的全部外部流；首行仅为基线，两项为0 |
| cashflow_coverage | `complete`或`unknown`；未知时不能将0解释为已确认无外部流 |
| flow_timing | `none`、`end_confirmed`、`end_assumed`、`unsupported` |
| reconciliation_status / source_ref | 行级`verified`、`unverified`或`conflicted`及具体来源；unverified/conflicted只能提供provisional诊断 |

对象未知附加字段可保留，但不参与计算；缺必需字段不得默认补0，JSON重复key拒绝，NaN/Infinity拒绝。金额统一Decimal字符串解析，内部精度至少28位，仅在最终展示舍入。额外证券市值分项是可选信息，不能凭总额推造它。

以下仅为合成算法fixture，不是用户资产或真实市场数据：

```json
{
  "schema_version": 1,
  "account_scope": "fixture-account",
  "currency": "CNY",
  "account_type": "cash_long_only",
  "valuation_basis": "broker_total_equity",
  "source_ref": "fixture:statement",
  "expected_valuation_dates": ["2026-09-15", "2026-09-16"],
  "calendar_source_ref": "fixture:calendar",
  "observations": [
    {
      "valuation_at": "2026-09-15T16:00:00+08:00",
      "total_equity": "100.00", "cash": "0.00", "liabilities": "0.00",
      "external_inflow": "0.00", "external_outflow": "0.00",
      "cashflow_coverage": "complete", "flow_timing": "none",
      "reconciliation_status": "verified", "source_ref": "fixture:day-1"
    },
    {
      "valuation_at": "2026-09-16T16:00:00+08:00",
      "total_equity": "160.00", "cash": "50.00", "liabilities": "0.00",
      "external_inflow": "50.00", "external_outflow": "0.00",
      "cashflow_coverage": "complete", "flow_timing": "end_confirmed",
      "reconciliation_status": "verified", "source_ref": "fixture:day-2"
    }
  ]
}
```

原始输入放在仓库外受保护的专用目录，源文件只读、不自动修正；生成物和输入分开。保存/导入真实账户事实及任何写回操作不因编制本规范而获授权。

### 8.4 PERF-03：现金流、连续性、零资产与回撤

现有生命周期回报保持原义。账户收益中和外部现金流，分红/利息属于投资收益、费用税费已包含在券商净资产时不得再次扣除；不宣称GIPS合规。[R6][R16]

前期流后净资产V0>0，当前流后净资产V1，F=external_inflow−external_outflow；仅在下述允许条件计算：

```text
r = (V1 - F) / V0 - 1
N = previous_N * (1 + r)     # 首个有效基线N=1
DD = N / running_peak_N - 1
MDD = min(DD)
```

| 现金流条件 | 结果 |
|---|---|
| coverage=complete且入/出两项都为0 | `none`，可计算 |
| 每一笔外部流均有证据位于期末估值边界，估值含该流 | `end_confirmed`，在该边界口径下可计算 |
| 时点不明但gross flows完整 | 仅同时标记end_assumed并传显式假设flag后，计算近似；否则该区间N/A |
| 已知期初/盘中发生而缺子期间估值，或流量覆盖未知 | unsupported/N/A；本版不实现期初算法、Modified Dietz或盘中精确TWR |

**净流为0不表示没有外部流。** 同区间入金50、出金50时仍要检查两笔的时点；`flow_timing=none`与非零gross flow冲突属于非法输入。所有非零流都必须属于允许的相同时点模型，不能把相互抵销流绕过检查。

有一个近似区间，所在链整体标记estimated；精确与近似不能悄悄混成“精确TWR”。若V1−F<0，或者不能解释现金流/估值，区间不可用并断链。数据已声明为完整但金额非法时拒绝输入，不通过负收益截断“修复”。

**零资产不是一概当数据缺失：** V0>0且V1=0、期末完整出金为原资产且无投资变化时，该期r=0并结束空仓资金链；V0>0、V1=0且确无外部流，真实全额损失r=−100%、MDD=−100%必须报告。随后V0=0的区间不除零；新的正资产只建立新segment基线，不与旧链拼接。

缺应估值日期或无效区间后，下一个有效估值只做新片段基线，再从其后一期计算。全区间收益/MDD不可宣称完整；每个连续片段保留真实起止日期。不得跨缺口填0收益、前向填价或把片段中最大的MDD叫完整区间MDD。

缺少可验证日历时，可以按提供估值点和完整区间流量输出observed-only片段收益与`max_drawdown_observed_pct`，但`daily_close_max_drawdown_pct=null`，明确日频覆盖未知。有日历且无缺口才输出日收盘MDD；始终不声称涵盖盘中极值。

实际账户市值不与前复权价格/现金分红混算。fixture例子：100→160且期末入50为10%；160→150且期末出10为0%；归一化100→110→99的MDD为−10%。

### 8.5 PERF-04：基准与输出合同

基准可选，单独JSON对象：schema_version=1、benchmark_id、currency、return_type、source_ref、effective_from、observations（唯一升序date与正Decimal字符串nav）。第一版只消费**一条已给定净值序列**，不联网、不临时混合多个指数、不引入动态重平衡。预先批准的复合基准也须由外部提供完整序列并附固定方法说明。

基准事先确定，币种、日期、计量区间必须与账户segment对齐；不插值、不前向填补、不挑更容易跑赢的基准。return_type明确total_return或price_return，价格指数不能冒充全收益；指数参考与可执行替代方案分别说明。没有请求基准不阻断绝对收益；请求的基准无效时绝对收益可保留，相对比较为N/A并返回业务缺口。

输出为一个内部应用结果：schema_version、report_type=`account_performance`、account_scope、currency、method、input_hash、可选benchmark_hash、coverage、gaps、segments；各segment含起止日期、exact/estimated/provisional状态、收益、观察点回撤、可选日频MDD和基准差额。所有N/A用null并附原因，不用0占位；报告不写回decision-v1/monitor-v1。

本版不提供年化、XIRR、自动持仓重建、多因子归因、预测或AI因果贡献。收益变好不证明由AI造成。

### 8.6 S3验收场景

| 编号 | 场景 | 预期 |
|---|---|---|
| P01 | 100→160，期末入50 | 10%，不把入金记收益 |
| P02 | 160→150，期末出10 | 0%，不制造回撤 |
| P03 | 分红/费用/税费已计入净资产 | 只计一次，不再调整equity |
| P04 | 送转与实际账户市值 | 不混前复权价格和现金分红 |
| P05 | 已知盘中流且无子期间估值 | 本版不可精确计算，不伪装期末 |
| P06 | 历史事实缺失 | 不重建；从有来源的基线开始 |
| P07 | 缺应估值日/日历未提供 | 断链或observed-only，日频MDD不可伪完整 |
| P08 | 100→110→99 | MDD=−10% |
| P09 | 未请求基准 / 请求后日期币种不匹配 | 前者不失败；后者保留绝对值、相对N/A |
| P10 | 同一文件重复执行 | 经济结果确定，不追加事实、不写库 |
| P11 | 非法金额/日期/混账/非零负债 | 受控拒绝输入，无可信业绩输出 |
| P12 | 文件型CLI，数据库不存在 | 仍正常处理文件；不建库/迁移/联网/通知 |
| P13 | CLI、有效配置与默认值 | 统一解析、逐字段来源，非法配置不回退 |
| P14 | 入50出50且标记none | 拒绝净额绕过gross-flow时点检查 |
| P15 | end_assumed但无显式flag | 区间N/A；有flag也只标estimated |
| P16 | 完整出金归零 / 真实全损归零 | 分别0%与−100%，不可混淆 |
| P17 | 零资产后重新入金 | 新segment基线，不除零、不拼旧链 |
| P18 | 数据缺口后恢复 | 分段输出；不伪完整区间收益/MDD |
| P19 | 重复JSON key、重复同日快照 | 输入错误；不静默覆盖或选最后一条 |
| P20 | --check-ledger且库缺失/对账冲突 | 对账状态及exit4明确；不虚构现金流 |
| P21 | 顶层help、参数表、--json和dispatch | 新命令全链路注册；输出/退出码一致 |
| P22 | 未确认/过期/范围冲突政策或模型擅改覆盖值 | 不宣称有效个人政策，不扩大授权 |

**完成条件：** S3a以解析/同输入同政策测试验收；S3b以公开接口、输入合同与纯计算fixture验收。真实账户数据不可用时只标 IMPLEMENTED_WITH_FIXTURES_ONLY。软件完成不等于用户数据已核实或新政策已生效。

---

## 9. S4：下一轮投资实验的启动条件

当前修正版本首先完成既有方向复核。原 2026-09-20 / 2026-09-23 检查日期不适用于新版本，不设一个无数据支持的新“最终有效性日期”。[R10]

达到方向复核门槛，也不等于通过实盘采用门槛。是否继续、简化、重做或停止，应沿用当前有效的预注册协议；不根据真实持仓盈亏或单只股票表现替代裁决。

下一轮建议顺序为：简单排序基线 → 去定性分等有限消融 → 行业内比较 → 明确策略对象的可成交验证。每个实验开始前冻结假设、样本、指标和终止条件，不同时搜索大量权重后只保留赢家。

可成交验证必须分别定义 Q5 和 ≥44 分名单，至少说明信号可用时间、最早允许成交时点、进出规则、费用与滑点、无法成交和缺数据处理。交易约束按实施时的交易所及数据提供方原始资料确认，本文不硬编码可能变化的市场规则。

不以更强模型重写旧定性分，不把后见信息加入当时输入，不将费用前研究收益直接宣传为个人账户可实现收益。

**S4 本轮状态：DEFERRED / CONDITIONAL。** 未满足条件时，只记录下一次需要读取的证据，不偷偷启动股票池扩张或参数优化。

## 10. 总纲与文档收敛

在 Agent 的 `docs/architecture/a-stock-ecosystem-charter.md` 放置唯一三仓总纲。实施前先检查用户已有获批总纲及仓库最新内容；存在时做最小补充，不重写；尚未落库时取得正确原文，不根据标题补造“已批准版本”。

Tracker 和 lib 只增加指针，不复制全文。总纲主要记录三仓职责、依赖方向、投资证据边界、禁止事项和真实账户所有权；不扩写成制度手册。

Tracker 路线图中的仓位、退出与风险预算，应明确区分“策略模拟规则”和“真实个人账户管理”。前者可以研究，后者由 Agent 持有唯一应用责任。[R10]

必要文档更新限定为现有 README/索引、runtime contracts、操作说明及相应测试证据。日常 Skill 上下文只保留路由和当前规则，不自动加载全部历史 spec、评审或迁移记录。

## 11. 实施顺序与提交边界

| 顺序 | 建议提交边界 | 主要仓库 | 不得捆绑 |
|---|---|---|---|
| C0 | 基线核实与必要文档定位 | 三仓只读；必要时更新Agent文档 | 生产升级、依赖自动对齐 |
| C1 | 预算超限升级、合同和Skill同步、对应测试 | Agent | 新个人阈值、自动卖出 |
| C2 | 文本缺失风险修复与stop_reason受控异常 | Agent | 通用数据库重构 |
| C3 | 预定股票池与快照证据资格检查 | Tracker | 评分权重、阈值、股票池改变 |
| C4 | 并列分数权重与评估版本 | Tracker | 历史预测改写、无版本历史结果拼接 |
| C5 | 最小个人政策解析 | Agent | 多账户权限、动态策略管理 |
| C6 | 单账户只读业绩MVP及fixture | Agent | 新生产schema、cron、券商自动同步 |
| C7 | 文档收口与实施结果记录 | 必要仓库 | 全仓清理、无关格式化、历史材料搬家 |

提交边界可按实际耦合合并，不要求机械凑次数。C1必须包含RISK-05一致读事务与预算合同回归；C3/C4可在一个候选交付中一起验收，以免“新分桶仍基于未来收益过滤”的中间状态上线。C5与C6相互独立，均不等待投资窗口成熟。

每一步核对diff与回归；用户只授权S1时到C2即止。发现无关修改、真实数据缺失或未授权策略语义变化，仅阻塞相关交付，不把整个项目挂起，也不自动扩大范围。

### 11.1 代码触点与范围预算

| 交付 | 必要触点 | 范围上限 |
|---|---|---|
| S1 | commands_monitor、monitor_contract、commands_holdings、Monitor Skill、定向tests | 最多一个局部risk helper；不改schema/lib |
| S2 | accuracy_report及一个局部evaluation helper、experiment_manifest、tests、现有说明 | 不改评分hash覆盖源码；不加报告服务/新cron |
| S3a | paths局部路径helper、一个policy解析模块、两CLI参数及tests | 单账户文件，不建政策数据库 |
| S3b | performance局部模块、cache命令注册/无DB分支、fixtures/tests | 一条R0命令，不加安装入口、生产表或外部依赖 |

这是限制过度拆分，不是强制凑模块数；发现可复用现有函数时优先复用。新增公开/CLI接口须有实际调用测试，不能只测纯函数。

## 12. 测试与证据要求

Agent 以仓库当前 `scripts/check.sh` 和既有独立 QA、cron fixture、合同及 Agent 行为检查为准；Tracker 以当前 pytest、Ruff、format、mypy 及结构检查为准。执行前读取实际脚本，确认只使用隔离数据与禁用通知配置，不盲跑历史文档中的生产命令。[R7][R8][R15]

lib 未修改则记录所消费版本与相关回归范围，不为形式完整强行改包。涉及合同枚举更新时，必须验证所有已知消费者，不能只通过生产者单元测试。

必需CI为合成fixture、合同、dispatch、数据库并发与安装/导入检查；必须保留现有入口。`scripts/check.sh`包含 `uv sync --frozen`，依赖安装可能访问网络，不能把整个检查宣称为离线。隔离HOME/XDG/状态路径、移除生产凭证、禁用通知后执行；依赖下载与业务网络访问分别记录。[R22]

真实模型捕获是独立的客户端资格检查，不放进每次无凭证CI。Skill/合同扩展改变消费行为时，生产启用前对实际要启用的客户端补一个隔离假工具预算场景；未具备模型访问时，该客户端状态为NOT_VERIFIED，禁止宣称已适配，但不阻塞确定性软件验收。历史捕获只验证其历史来源，不反复重录来换绿。

证据最少包含：被验证提交、命令、退出码、测试摘要、未执行项和原因、实际依赖版本，以及是否使用真实数据/真实模型/网络。参考公式测试、项目回归、历史捕获、当前客户端资格四类分开，不互相冒充。

无副作用用SQL authorizer/trace、fixture前后业务行/schema对比、通知/网络spy及不存在DB的命令测试验证。活跃生产库并发更新或WAL/SHM状态不能靠前后文件hash简单裁决；禁止以删除sidecar或切journal_mode获得“只读通过”。[R19]

测试或报告生成不得泄漏凭证、账户详情、生产数据库、WAL/SHM 文件或未脱敏日志。fixture 使用合成事实，不将真实账户复制进仓库。

本轮不能用以下内容作为完成证明：未经运行的预期数字；过去的测试计数；只更新快照后得到的全绿；仅有文档“已完成”标记；仅有 CI 而无关键缺陷的定向回归。

## 13. 安全、生产授权与回滚

### 13.1 授权不可跨范围继承

| 行为 | 本文是否已授权 | 后续边界 |
|---|---|---|
| 编制本规范 | 是 | 当前请求 |
| 修改、提交并push代码 | 否 | 用户明确实施后，按master直接提交规则 |
| 只读获取生产事实 | 不假定已有访问 | 使用合法访问，确认没有隐式写入 |
| 更改生产schema、cron、客户端入口 | 否 | 单独明确授权，独立验收与回滚 |
| 改评分、股票池、投资阈值 | 否 | 明确有日期的策略规范与用户授权 |
| 真实W1状态写入 | 否 | 用户确认具体动作，并使用全局confirm-write门禁 |
| 自动下单或自动交易 | 否 | 本规范不建设该能力 |

历史规范的 `AUTHORIZED FOR IMPLEMENTATION` 不能自动授权本轮新增策略或生产变更。用户批准某一阶段，也不等于批准所有后续条件实验。[R15]

### 13.2 回滚策略

代码使用小提交和 `git revert` 保留历史，不重写master。生产部署须单独授权，并首先确认当前客户端路径究竟是symlink还是copy：symlink指向开发工作树时，编辑源码本身可能立即影响生产，不能一边声称“仅开发”一边在活动路径修改。应在不会被活动客户端引用的隔离检出目录准备同一master修订；这不是创建feature branch。[R7][R15]

部署制品必须绑定runtime、schema词表、Skill内容及必要manifest身份。copy模式先完整staging再切入口；symlink模式须指向完整不可变release目录，不能逐文件更新生产树。没有条件原子/协调切换时，使用既有运维方式暂停相关任务并在授权窗口中切换，不新建部署平台。

旧消费者不能理解新枚举时，先隔离旧入口而不是把错误包装成无动作。成组回滚后还必须注意：旧版本可能重新带回“预算超限仍clean”的已知问题；因此回滚只是运行恢复，不代表风险缺陷已解决。预算相关监控须降级为人工复核/暂停风险建议，直至修正版重新验证，不允许恢复危险clean后仍标通过。

Tracker 保留原始预测不变。评估逻辑回滚时保留各自 `evaluation_version` 与报告说明；不能把退回旧实现说成统计口径没有变化。

S3 MVP不迁移数据库；回滚仅撤销代码/入口，保留并保护事实输入。不自动删除个人政策文件；退回不认识该配置的版本时禁止声称仍执行个人限额，必要时保持人工复核。不得删除账本、净值原始输入或制造反向交易。

## 14. 总体验收与实施回执

本轮不能只有一个笼统的“完成”。每阶段分别标记实现、项目回归、客户端资格、生产和投资证据。允许软件修复完成、生产未部署、策略证据不足同时成立。

| 验收层 | 可用完成证据 | 不得替代 |
|---|---|---|
| 文档修订（本次） | 问题映射、合同/示例检查、差异与文件校验 | 不等于项目功能已实现 |
| 仓库实现 | 对应源码提交与A/T/P实际回归 | 不等于生产已受保护 |
| 客户端资格 | 当前release/Skill的隔离调用证据 | 历史模型capture不能替代 |
| 生产启用 | 获授权的制品切换与只读回读 | 不可只用仓库CI |
| 投资证据 | 有来源真实样本、冻结协议与真实账户事实 | fixture、测试数量和软件版本不能替代 |

总体验收要求为：

- 风险超限或未知风险不再被伪装成无动作；已有安全门禁不退化。
- Tracker 的证据资格可解释，并列分桶与回撤口径一致，不改变冻结评分。
- 账户业绩MVP区分现金流与收益，数据不足不补造，未声称AI因果性收益。
- 三仓边界保持清晰，未增加不必要平台、仓库或常驻服务。

执行结束必须提供以下回执，逐项如实填写：

```text
Overall status:
  各阶段状态；不要把implemented写成deployed或investment-validated。

Repository heads:
  修改前/后的各仓库SHA；未修改仓库也说明。

Completed:
  条目ID、实际变化、对应证据。

Not completed:
  条目ID、原因、缺少的事实/授权/数据；条件实验明确为deferred。

Tests:
  命令、环境、退出码、通过/失败/跳过；未运行项不可省略。

Security/production impact:
  是否访问生产、是否联网、是否修改schema/cron/客户端/W1、是否发通知。

Rollback:
  可回退提交/制品、数据保留方式及生产者/消费者兼容要求。
```

## 附录 A：给执行 Agent 的任务入口

以下入口仅在用户明确要求实施后使用；当前“审查并修复文档”不构成代码、配置或生产执行授权。

```text
请按本规范实施当前已获授权阶段。

先读取各仓库最新AGENTS、相关规范和master状态；核对本文基线。
已经完成的项目只验证，不重复开发。当前以S1风险闭环为第一代码优先级。只实施明确获批阶段；S3a与S3b独立。

仅在master小步修改、验证、直接commit和push；不建功能分支、不开PR、
不force-push，不覆盖未知本地改动。

保持三仓分工、现有monitor-v1和decision-v1；遵循本规范的枚举兼容矩阵，
不混装新旧消费者，不新增架构平台。只读多表快照必须在同一显式读事务内。
不修改Tracker评分权重、44分阈值、股票池、历史预测或投资实验口径，
除非是本规范已获授权的S2评估修正，并明确记录evaluation_version。

源码、fixture及只读验证与生产操作分离。未经单独授权，不改生产schema、
cron、客户端入口、真实持仓或其他W1状态；不发送真实通知、不自动交易。

完成后按本规范第14节格式报告。原文42个场景已扩为本版A01-A22、T01-T20、
P01-P22；逐项提供实际映射，不用参考检查、过去CI或文档标记冒充项目回归。
```

## 附录 B：来源与固定审查定位

源码引用用于证明编制时的实现事实；本文提出的状态、字段和算法修改属于待实施方案。以下链接固定到审查提交，避免 master 后续变化使证据失去定位。

- **[R1] Agent master 基线：** `f3bbc44b5619316f7a616a9c1b81ce6419034f45`；[固定提交](https://github.com/on195594/a-stock-agent-skills/commit/f3bbc44b5619316f7a616a9c1b81ce6419034f45)。
- **[R2] Tracker master 基线：** `69f11c99d1720f2dad07113b46f17f5d87a3975d`；[固定提交](https://github.com/on195594/a-stock-tracker/commit/69f11c99d1720f2dad07113b46f17f5d87a3975d)。
- **[R3] Lib 职责与当前评分边界：** [README](https://github.com/on195594/a-stock-lib/blob/6dc856ea1183fe6f6c8ff9f5201b0c920b5008ec/README.md)。
- **[R4] 合同与版本维度：** [runtime-contracts.md](https://github.com/on195594/a-stock-agent-skills/blob/f3bbc44b5619316f7a616a9c1b81ce6419034f45/docs/architecture/runtime-contracts.md)。
- **[R5] 监控快照构建与预算分支：** [commands_monitor.py](https://github.com/on195594/a-stock-agent-skills/blob/f3bbc44b5619316f7a616a9c1b81ce6419034f45/src/a_stock_agent_runtime/commands_monitor.py)，重点为`build_monitor_snapshot`及只读快照输入。
- **[R6] 持仓生命周期收益：** [position_ledger.py](https://github.com/on195594/a-stock-agent-skills/blob/f3bbc44b5619316f7a616a9c1b81ce6419034f45/src/a_stock_agent_runtime/position_ledger.py)。
- **[R7] Agent 安装、部署记录及检查：** [README](https://github.com/on195594/a-stock-agent-skills/blob/f3bbc44b5619316f7a616a9c1b81ce6419034f45/README.md)。
- **[R8] Tracker 投资与生产记录：** [project-status.md](https://github.com/on195594/a-stock-tracker/blob/69f11c99d1720f2dad07113b46f17f5d87a3975d/docs/project-status.md)及[README](https://github.com/on195594/a-stock-tracker/blob/69f11c99d1720f2dad07113b46f17f5d87a3975d/README.md)。
- **[R9] Tracker 独立生产评分：** [scoring.py](https://github.com/on195594/a-stock-tracker/blob/69f11c99d1720f2dad07113b46f17f5d87a3975d/a_stock_tracker/scoring.py)。
- **[R10] 实验阶段、修正后门槛与hash边界：** [evolution-roadmap.md](https://github.com/on195594/a-stock-tracker/blob/69f11c99d1720f2dad07113b46f17f5d87a3975d/docs/evolution-roadmap.md)及[cli.py](https://github.com/on195594/a-stock-tracker/blob/69f11c99d1720f2dad07113b46f17f5d87a3975d/a_stock_tracker/cli.py)。
- **[R11] 文本风险入口：** [commands_holdings.py](https://github.com/on195594/a-stock-agent-skills/blob/f3bbc44b5619316f7a616a9c1b81ce6419034f45/src/a_stock_agent_runtime/commands_holdings.py)，重点为`calculate_position_risk`与`cmd_portfolio_risk`。
- **[R12] monitor-v1 校验与Skill消费：** [monitor_contract.py](https://github.com/on195594/a-stock-agent-skills/blob/f3bbc44b5619316f7a616a9c1b81ce6419034f45/src/a_stock_agent_runtime/monitor_contract.py)及[Monitor SKILL](https://github.com/on195594/a-stock-agent-skills/blob/f3bbc44b5619316f7a616a9c1b81ce6419034f45/skills/a-stock-monitor/SKILL.md)。
- **[R13] 覆盖率、IC、分桶及回撤：** [accuracy_report.py](https://github.com/on195594/a-stock-tracker/blob/69f11c99d1720f2dad07113b46f17f5d87a3975d/a_stock_tracker/reporting/accuracy_report.py)。
- **[R14] 实际落库快照：** [cli.py](https://github.com/on195594/a-stock-tracker/blob/69f11c99d1720f2dad07113b46f17f5d87a3975d/a_stock_tracker/cli.py)，重点为`_prepare_stock_scoring_input`、`_write_stock_predictions`和`_upsert_one_framework_prediction`。
- **[R15] 开发、投资规则与生产授权边界：** [AGENTS.md](https://github.com/on195594/a-stock-agent-skills/blob/f3bbc44b5619316f7a616a9c1b81ce6419034f45/AGENTS.md)。
- **[R16] 业绩计量原始参考：** [GIPS Standards Handbook for Asset Owners](https://www.gipsstandards.org/standards/gips-standards-for-asset-owners/gips-standards-handbook-for-asset-owners/)，重点为22.A.21关于外部现金流、时间加权收益和几何链接的讨论。访问日期：2026-09-17；仅借鉴计量原则，不宣称本项目达到GIPS合规。

- **[R17] 只读连接与隐式schema边界：** [db.py](https://github.com/on195594/a-stock-agent-skills/blob/f3bbc44b5619316f7a616a9c1b81ce6419034f45/src/a_stock_agent_runtime/db.py)。
- **[R18] SQLite显式/隐式读事务：** [Transaction](https://www.sqlite.org/lang_transaction.html)，访问2026-09-17；单连接不保证跨语句固定快照。
- **[R19] SQLite只读WAL边界：** [Write-Ahead Logging](https://www.sqlite.org/wal.html)，§2.2/§4/§5，访问2026-09-17。
- **[R20] 命令注册及R0数据库前置检查：** [cache.py](https://github.com/on195594/a-stock-agent-skills/blob/f3bbc44b5619316f7a616a9c1b81ce6419034f45/src/a_stock_agent_runtime/cache.py)，COMMAND_CLASSIFICATION、parser及main。
- **[R21] 外置路径与配置解析：** [paths.py](https://github.com/on195594/a-stock-agent-skills/blob/f3bbc44b5619316f7a616a9c1b81ce6419034f45/src/a_stock_agent_runtime/paths.py)。
- **[R22] 实际测试入口：** [scripts/check.sh](https://github.com/on195594/a-stock-agent-skills/blob/f3bbc44b5619316f7a616a9c1b81ce6419034f45/scripts/check.sh)。

---

**本轮决策原则：先修风险断点，再补投资证据，再衡量账户结果；不以工程复杂度替代投资价值。**
