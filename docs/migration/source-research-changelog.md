# Changelog — a-stock-research

格式：[版本] 日期 — 变更摘要

---

## [3.2.1] 2026-08-07

### 对齐数据源、评分口径与质量审查流程

- 明确 TuShare 结构化数据失败时需手动切换 AKShare，避免将非自动回退误解为故障转移。
- 统一 C/D 下行期分红评分顺序：先做压力测试，再对压力测试后的前瞻股息率应用周期折扣。
- checklist 改为所有框架执行，未覆盖项继续按框架文档人工评分；补充 TuShare 分红单位转换说明。
- 移除 QA 命令中的权限绕过，使用 agy 原生 5 分钟超时，并为 Codex 备用路径增加宿主能力检查。
- 将搜索年份改为动态占位符，避免规则随年份失效。

## [3.2.0] 2026-08-06

### C框架新增成长型资源股分支（基本面权重 + 择时主估值轴双分支）

- 触发案例：紫金矿业(601899) 2026-08-06 首次研究 — 派息率30.8%，基本面股息率维度判0/15、择时估值信号判3/15，两处均因股息率不达3%及格线，配置评级被压至D级、时机评级「—」，与其 ROE 26.8%、C1现金成本全球最低区间、铜权益储量十年增805% 的实际质地严重背离
- 根因：C框架的两根股息率轴——基本面「前瞻股息率 [15]」与 SKILL.md 第三步择时「估值信号15分」的主估值轴——均按神华、中石油等高派息成熟资源股校准。高再投资率的成长型矿业公司（派息率20%-35%）套用同一口径必然双重失分，属框架口径错配而非质地不足。此为框架规则缺失，非单次执行疏漏
- 修复：以派息率（dps÷eps，均取最近完整财年口径）40% 为界分成熟/成长两支。成长分支基本面「前瞻股息率」15分→5分并新增「产量·储量成长兑现度」10分；择时主估值轴由归一化FCF股息率改为 PB历史分位（<近10年40%分位 + 周期底部区/上行期）。eps≤0 或口径不可比时保守走成熟分支
- 配套：压力测试 `10/15` 上限明确为仅成熟分支适用，两分支统一按维度满分 2/3 封顶；格雷厄姆预筛选 C/D 条目补充成长分支例外声明；C.md 标题下补分支说明行
- 同时统一「格档折算比例」为满分 50%（此前 A/E/F 框架按 60% 隐性推断，B.md 已显式写明 50%），并首次写入 SKILL.md 客观分项核验门槛。⚠️ 此项会使 A/E/F 框架历史评分与新评分存在约 1-2 分的口径差异，跨期比较需注意
- 评审：collab-pipeline plan-stage 文本评审 2 轮（codex-self-review），第1轮 1 Critical + 2 Important、第2轮 4 Important，全部裁定成立并采纳；用户于第2轮后显式放行

## [3.1.0] 2026-08-02

### 客观分项核验状态标签补全"人工核验推翻简化判定"分支

- 触发案例：迈瑞医疗(300760) 2026-08-02 agy审查 — Important-6（毛利率稳定性子项 checklist 标"简化判定"，Claude 自行核实 2023-2025 年趋势后发现连续3年下滑 66.16%→60.32%，据此推翻简化判定给0分，但报告只写了自由文本"已核实趋势，非简化判定放行"，未使用输出格式第5项规定的三选一标准标签之一，导致 agy 判定 NON_COMPLIANT）
- 根因：框架规则本身的空白——"客观分项核验门槛"早已允许 Claude 自行核实简化判定子项的历史趋势/连续性并据此改判，但输出格式第5项的核验状态标签只枚举了「checklist核验」/「⚠️ 无客观数据支撑，纯人工判断」/「⚠️ 数据缺失，未核验」三种，未覆盖"核实后推翻简化判定"这一分支，属于框架文档缺失而非本次执行疏漏
- 修复：客观分项核验门槛"达优"分支补充说明——Claude 自行核实简化判定子项后（无论维持还是推翻原值），一律标注「人工核验推翻简化判定」并注明核实出的实际档位（达优/达格/未达）及依据，不得沿用「checklist核验」（该标签保留给未经额外核实、直接采信 checklist 原始结果的子项）；输出格式第5项的核验状态标签由三选一扩为四选一

### 共享包升级到 a-stock-lib 0.4.1

- 2026-08-02 升级 `a-stock-lib` 从 `0.3.0` 到 `0.4.1`（新增 TuShare 估值/财务/分红 Provider，本仓库尚未接入消费，仅完成纯升级验证）；升级前后全量测试均为 `533 passed`，无回归。
- 本机 Debian 系统 Python 启用了 PEP 668 保护，`pip install --user` 需追加 `--break-system-packages` 才能安装到用户 site-packages；`requirements.txt` 顶部注释已同步更新安装命令。

### C资源框架补齐实际行业别名

- 2026-07-31 通过 fetcher 刷新紫金矿业（601899）确认其实际 `industry` 为 `铜`；该值此前未命中 C资源关键词，持仓路径会静默落到 A通用。
- C资源 `industry_keywords` 新增 `铜`，使其按资源框架路由并使用 18%/25% 止损系数；新增实际样本和关键词穷举回归测试。
- 同次核实：五粮液（000858）为 `白酒`，已正确路由 E消费；招商证券（600999）为 `证券`，已按非量化金融品种拒绝量化写入。

### 可维护性与可重复验证加固

- 运行路径改为由 `project_paths.py` 推导，支持 `CACHE_DB_PATH`、`A_STOCK_LIB_ROOT` 覆盖；移除 fetcher、cron、测试和 prompt 回归中的开发机绝对路径。
- 新增 `schema_migrations` 持久化账本：核心表、每条列迁移、索引和旧数据回填各有稳定 migration ID；首次升级仍兼容旧库，后续独立 CLI 只执行尚未记录的项。
- P2 审查修复：移除原先单一 `001-current-schema` 总开关，避免后续版本新增迁移在既有数据库上被错误跳过；回归覆盖“已完成项不重跑、仅执行新增项”。
- 提取 `market_quotes.py`（行情访问）与 `schema_ledger.py`（跨进程 migration lock/ledger），`cache.py` 保留旧行情函数 façade 以兼容调用方。
- 增加 `requirements-dev.txt`、Ruff/MyPy 质量门禁及其统一测试入口；补强对象到浮点数转换的运行时类型边界。
- 历史审查文档已显式标记为非当前指引，当前状态页不再使用绝对 `file:///` 链接。

---

## [3.0.1] 2026-07-30

### 持仓生命周期、账本治理与行情链路修复

- `close-holding` 统一委托给卖出事件账本；收益、复盘和已平仓展示统一按买入、卖出、费用、税费和分红的完整现金流计算
- 保留 `close-holding` 的 FIFO 单笔平仓语义；`set-score` 与重新分析改分时会清除不再匹配的分项得分
- 强化账本不变量：拒绝 NaN/Infinity、禁止交易事件早于首次买入、`score_breakdown` 校验分项范围及与总分一致性
- 删除持仓和 `cleanup` 会级联清理/治理事件、L3、Tier、预警和复盘记录，避免孤儿数据
- 补齐北交所 `920` 代码路由及北交所最小100股、递增1股的申报规则
- 超时调用改为可终止子进程，超时后不再等待失控线程自然结束
- 抽取无副作用的 `position_ledger.py`，将持仓生命周期收益计算从 CLI/数据库编排中解耦

---

## [3.0.0] 2026-07-30

### 结构化持仓账本与监控状态

- 新增买入、部分/全部卖出、费用、税费、分红和公司行动事件账本；真实回报不再挂靠最近分析日期
- 新增持仓级 framework、initial_shares、reference_cost、main_entry_date，避免分析框架漂移和除息成本重复计算
- 新增 L3、Tier、预警结构化表及 CLI，预警支持稳定 reason_code、到期复核和解除证据
- `portfolio-risk` 改为按市值输出权重、总仓位与第二档止损风险贡献
- 新增上交所主板/科创板可申报股数校验，拒绝500股拆成167股等不可执行委托
- 首次迁移使用跨进程文件锁；旧持仓自动生成带 `inferred=1` 的基线事件并提示核对历史流水
- 同代码只允许一个在仓生命周期，重复建仓必须改用 `buy-holding`
- `position-return` 隔离当前或最近一次已平仓生命周期，避免历史轮次串账
- 加仓手续费只进入经济成本，不进入 Tier/止损使用的 `reference_cost`
- 旧 flags 迁移仅采用最新一期分析，避免复活已经过时的历史预警

## [2.9.1] 2026-07-17

### 退役 watchlist-refresh.sh，止损检查拆分为独立脚本

- **问题**：`watchlist-refresh.sh` 对 watchlist 里每支需要刷新的股票各起一个完整 `claude -p` 会话做全量重新研究（fetcher + WebSearch + 框架计算 + 强制独立QA复核），早高峰批量顺序跑会耗光 Claude Code session 用量额度——refresh.log 显示 2026-07-15/16/17 连续三天在批次中途命中 `session limit`，导致当轮剩余持仓/观察股票分析失败、缓存未写入，且这个额度池与用户白天交互式使用共享。
- **根因诊断**：2026-07-14 一次"加固"重构（commit `c90664d`）把 `MAX_REFRESH` 默认值从 3 提到 10，并删除了当时专门为避免 session token 超限写的截断逻辑；同日先做了两处直接修复（commit `d8fa519`）：`MAX_REFRESH` 改回 3 + 新增"命中 session limit 立即熔断退出批量循环"逻辑。
- **投资+工程双重评审后的结论**：watchlist-refresh.sh 覆盖的 9 支股票与 `a-stock-tracker` 的 `WATCHLIST` 完全重叠，而后者用零 Claude Code 额度成本的机制（Framework A/B 纯 Python 定量评分 + Gemini API 定性评分，30天缓存）每个工作日已在覆盖同一批股票，且多了 a-stock-research 没有的 30/60/90天 outcome 胜率回测能力。持仓监控的职责应由 `a-stock-monitor`（针对性L3论文核验/止损检查，成本远低于全量重新研究）覆盖；候选股买入决策应由用户主动触发的交互式 `a-stock-research` 请求覆盖（例如"帮我分析三花智控"）。批量被动全量重跑在两个场景下都是增量价值有限、代价高昂的重复实现。
- **处理**：删除 `watchlist-refresh.sh` 及其测试 `tests/test_watchlist_refresh.sh`。止损检查（`check_stoploss`，唯一不依赖 LLM、纯 Python+curl 的部分）提取为独立脚本 `check-holdings-cron.sh` + 新测试 `tests/test_check_holdings_cron.sh`（6项场景：无预警/触发预警/命令失败/超时/锁占用/缺Telegram配置），沿用原 cron 时间（工作日 CST 9:35）。crontab 对应条目已从指向 `watchlist-refresh.sh` 改为指向 `check-holdings-cron.sh`。
- **代价（诚实记录）**：不再有"每隔几天自动重新研究一遍非持仓观察股，防止用户没注意到基本面变化"的被动兜底；这类变化现在依赖用户自己想起来主动触发分析。

---

## [2.9.0] 2026-07-17

### D框架分红压力测试补公式（agy 独立QA审查，NON_COMPLIANT修复）

- **问题**：`frameworks/D.md` "前瞻股息率（压力测试后）"评分项要求压力测试后的数值，但"分红可持续性压力测试"步骤只要求定性回答"分红中枢变化幅度"，未给出具体计算方法，导致执行时直接用当前验证股息率代入评分表，混淆"当前股息率"与"压力测试后前瞻股息率"两个概念
- **修复**：`frameworks/D.md` 压力测试步骤2补充显式公式——净利润降幅=业务量降幅×经营杠杆系数（默认1.5倍）→压力后DPS→压力测试后前瞻股息率，并明确该数值才是评分表对应项的依据
- **触发案例**：2026-07-17 长江电力(600900) agy(Gemini 3.5 Flash)审查，Important级FAIL，verdict NON_COMPLIANT；修复后重算：业务量降10%→净利润降15%→压力后DPS 0.85元→压力测试后前瞻股息率3.04%（原报告误用3.57%当前股息率），档位（>2.5%格档）未变，评分结果不受影响，已更正报告表述并重新写入缓存

---

## [2.7.1] 2026-07-13

### B框架NIM下行趋势评分上限（投研准确性第三轮复核，commit `f8187de`）

- **净息差趋势评分补量化约束**（frameworks/B.md）：原"未加速下滑格"无基点定义，精确数据但持续恶化仍可打满分（07-05审查发现的盲点，此前误认为已随 [2.6.1] 的数值来源约束一并解决）。改为按bp变化分档：近两年累计降幅≤10bp满分/11-25bp封顶5分（即使绝对值>1.8%）/>25bp或连续3期同比下降不得打优档。与 [2.6.1] 的"数据来源精确性"约束正交独立判定，不可互相替代。
- **[2.6.1] 范围澄清**：该版本的"B框架数值评分硬约束"只解决了数据是否精确最新的问题，未设定趋势本身的评分上限。

---

## [2.7.0] 2026-07-06

### 新增规则（来源：agy 独立持仓审查 C2，codex 框架缺口审查）

**第三步：择时评分 — 预期差分析**
- **基本面改善与价格背离核验**：引用边际改善作为依据时，若股价同期持续下跌或明显弱于行业，必须解释背离原因（市场已定价？更强反向变量？改善被否定？）；无法解释则只能列为待验证信号，不得作为正向评分主因（来源：C2 agy审查 2026-07-06 — 神华煤价+4%但股价持续下跌矛盾未解释）
- 规则插入位置：预期差分析"回答以下三个问题"之前（agy 二轮独立审查指出首次插入位置错误，已修正至评分决策前）

---

## [2.6.3] 2026-07-06
### score_breakdown 写入侧 schema 校验（TL-3，技术债清理，commits `08ae42c`/`d2bcaf9`）
- 新增 `_validate_score_breakdown_schema`：`set-score-breakdown` 强制要求 JSON 顶层含 `fundamentals`/`timing`，且各自含 `subtotal`，不符合直接拒绝写入（退出码1），不写库
- 范围限定为写入侧校验，不迁移历史数据：生产库仅2条 score_breakdown 记录（1旧1新），字段映射（如 `moat`→`cost_competitiveness`）带业务判断成分，与用户确认后不做自动迁移
- `_format_breakdown_line` 展示侧的旧格式降级分支保留，供唯一的历史孤例（600900）继续正常显示
- **codex code review 追加修复**（`d2bcaf9`）：① 顶层非 dict（`null`/数字/字符串/list）此前会抛未捕获 `TypeError`，改为走正常错误路径；② `subtotal` 此前只检查 key 存在、未检查值类型，`bool`/`list` 等能通过校验写库导致 `watchlist --breakdown` 展示乱码（如 `True/60`），改为显式校验 `isinstance(x, (int, float)) and not isinstance(x, bool)`（`bool` 是 `int` 子类，需显式排除）
- schema 拒绝场景累计覆盖7例（旧平铺schema、缺 subtotal、非dict顶层×3、非数值subtotal×2），407 passed 无回归

---

## [2.6.2] 2026-07-05
### watchlist --breakdown 分项展示（commits `54927f1`/`fd4206c`）
- `watchlist --breakdown`：对有 score_breakdown 的股票打印子行（无 flag 时零影响）
- 双 schema 支持：嵌套格式 → `分项: 基本面 N/60 | 择时 N/20 | 合计 N/80`；旧平铺格式 → `分项: 合计 N`
- `--json` 输出自动包含 score_breakdown 字段（有分项为 dict，无分项为 null）
- 测试基线 400 passed（+3 新增）

---

## [2.6.1] 2026-07-05

### 方法论约束补丁（投研准确性评审遗留盲点，commits `3163c95`/`37cdac1`）

- **B框架数值评分硬约束**（frameworks/B.md）：净息差/不良率/拨备三项，须以本次 WebSearch 实际获得的精确最新值为前提方可打优档分；搜索结果为估算区间、往年数据、或无法对应最新报告期的模糊值时 → 默认格档分（净息差5/10；不良率7.5/15；拨备5/10），不得凭训练记忆或银行知名度打优档分；完全无数据依现有降级规则（该维度0分）。
- **C/D框架操作建议必填项**（SKILL.md 操作建议写法要求）：操作建议须包含"建议持仓期限：X-X年"和"周期退出触发条件"（具体前瞻指标，如"煤价中枢跌破XXX元/吨时开始减仓"），不得仅写"持有到周期转折前"等无触发条件的软承诺。

---

## [2.6.0] 2026-07-05

### 新增：知识沉淀系统（retro_notes）

基于多 AI 对抗设计讨论后实施，解决"每次分析一次性、无复盘数据"问题：

- **新增 retro_notes 表**（永久，不参与 cleanup 生命周期）：绑定 holdings.id，存储 error_tags / thesis_notes / actual_return_pct / holding_days 等字段
- **平仓自动复盘提示**：close-holding 成功后打印复盘提示和可选标签词汇表
- **4 个新 CLI 命令**：
  - `retro-add <代码> <标签> [--note] [--thesis] [--gap]`：填写平仓复盘
  - `retro-pending`：显示已平仓未复盘列表
  - `retro-stats [框架]`：错误标签频率统计，≥3 次标注"★ 建议复查框架规则"
  - `retro-outliers [--loss N]`：优先聚焦亏损大的待复盘记录
- QA（codex-self-review）发现并修复 2 个 Important bug：
  - `--loss 10` 与 `--loss -10` 语义统一（改用 `-abs()`）
  - win_rate 分母含 NULL 行偏低（改用 `len(returns)` 分母）
- 新增测试 9 条，共 69 passed

---

## [2.5.3] 2026-07-03

### cache.py / watchlist-refresh.sh 两项 P2 工程修复

- **watchlist-refresh.sh 日志捕获**：`claude` 个股分析调用改 `>> "$LOG" 2>&1`，stdout+stderr 均进日志，消除静默失败无日志的排查困难（commit `f176e5a`）
- **`cmd_check_holdings` 函数拆分**：提取 `_evaluate_holding_status()` 辅助函数，两函数均 ≤50 行（28/41），满足编码规范（commit `b242a9f`）
- 两次 codex-self-review 均 0 Critical/Important，387 passed 无回归

### 项目配置与文档修正

- **新增 `pyproject.toml`**：固化 pytest 路径配置（`testpaths=["tests"]`，`pythonpath=["."]`），不移动任何源文件；`src/` 重构评估为低收益高风险，不做（commit `c112e62`）
- **`SKILL.md`/`AGENTS.md` 路径修正**：`CHANGELOG.md` 裸路径改为 `docs/CHANGELOG.md`，SKILL.md 手工编写段直接修改后重渲染 AGENTS.md（commit `6e66976`）；原 project-status"需跨仓库处理"判断有误，已纠正

---

## [2.5.2] 2026-07-03

### cache.py 三项工程修复（07-03 审查跟进）

- **P0 连接泄漏修补**：19 处 `get_db()` 裸连接改用 `db_session()` 上下文管理器，保证异常路径下连接也被释放，防止 WAL 膨胀（commit `146ed3a`）
- **P1 进程级 Schema 初始化缓存**：`get_db()` 引入 `_SCHEMA_INITIALIZED` + `_SCHEMA_INITIALIZED_PATH` 双重检查锁定，DDL 只在首次连接（或 `DB_PATH` 切换时）执行，消除高频 DDL 锁争抢（commit `a7d6ae2`）
- **P1 时区漏洞修复**：新增 `_CST = timezone(timedelta(hours=8))`，`cmd_check_holdings` 的 `datetime.now()` 改为 `datetime.now(tz=_CST)`，去除对宿主机系统时区的隐式依赖（commit `2fb0f10`）
- 全程 `387 passed`，三次 codex-self-review 均 0 Critical/Important

---

## 工程整理 2026-07-03

### 目录结构规范化（collab-pipeline 任务 A/B）

- **根目录文档归档**：9 份历史文档（IMPROVEMENT-PLAN.md、ANALYSIS-METHODOLOGY.md 等）迁移至 `docs/archive/`（commit `0c4fd5f`）；同步更新 `ai-collab/config.yaml` 文档路径引用
- **日志/锁文件目录规范化**：`refresh.log`/`refresh.lock` 从根目录迁移至 `logs/` 子目录（commit `d54d542`）；补 tracked `logs/.gitkeep` 防止目录随 checkout 丢失（commit `034b930`，修复 codex-self-review 审查发现的 Important 项）
- `.superpowers/sdd/` 归档 39 个历史协作产物，删除 6 个 `.bak` 垃圾文件
- collab-pipeline 台账：任务 A（`9d12cdf`）、任务 B（`1ffc369`）、project-status 更新（`df32bae`/`0622a66`）

### 工程审查（2026-07-03）

- 工程视角审查发现 2 项高风险（`cache.py` 数据库连接泄漏 + 进程级 Schema 初始化 DDL 锁争抢）、1 项中风险（`_is_a_share_trading_hours` 时区依赖宿主机）、2 项低风险（日志捕获缺口 + `cmd_check_holdings` 超长函数）
- 审查报告：`docs/engineering-review-2026-07-03.md`；整改列入 Active Work（P0/P1/P2），本次未实施

---

## [2.5.1] 2026-07-02

### check-holdings 行情新鲜度校验，修复非交易时段假止损预警（BUG-006）

- **根因**：`cache.py` 的 `fetch_current_prices()` 只提取新浪行情 `fields[3]`（价格），丢弃 `fields[30]/[31]`（行情日期/时间）。`watchlist-refresh.sh` 的 cron 此前误配置为凌晨 01:30 运行（时区注释换算错误），此时新浪返回上一交易日收盘价，被 `cmd_check_holdings()` 无差别当作"现价"比对止损线，2026-07-02 对中国神华（601088）产生假止损预警。
- **修复**：crontab 改为 `35 9 * * 1-5`（commit `168eb3c`）；`cache.py` 新增 `PriceQuote`/`fetch_current_price_quotes()` 携带 quote_date/quote_time，`cmd_check_holdings()` 按新鲜度分三档处理——陈旧行情只输出"📋 观察提醒"不计入预警；盘中跌破用"🚨 盘中已跌破...现价"；收盘后跌破用"...收盘价"；新鲜度未知（字段不足/mock兼容路径）保持改动前行为不变（commit `f7392bf`）。
- **验证**：新增 6 个回归测试（陈旧行情降级、盘中/收盘后文案、交易时段边界、真实32字段解析路径），codex 独立审查 0 Critical/Important，全量 `387 passed`。用真实持仓数据手动复跑确认中国神华不再误报。
- **已知限制**：`cmd_portfolio_risk()`（浮盈%展示）仍用旧 `fetch_current_prices()`，未做同等新鲜度校验，本轮不在范围内。

## [2.4.3] 2026-07-02

### 数据库路径防呆（ai-collab pipeline 首次接入本仓库）

- **根因**：`cache.py` 的 `DB_PATH` 支持 `CACHE_DB_PATH` 环境变量覆盖，但 CLI 运行时不显示实际解析到的路径——历史上发生过手工 smoke test 绕开 pytest 的 `isolated_db` fixture、误写生产 `cache.db` 的真实事故（见 `TODOS.md` P0-8 记录、长期记忆 `feedback_cache_db_absolute_path_hazard.md`）。
- **修复**：CLI 入口在派发命令前把解析到的 `DB_PATH` 打印到 stderr（commit `b99fa11`），不影响 `check` 命令供 SKILL.md 解析的 stdout 协议。覆盖机制仍是既有 `CACHE_DB_PATH` 环境变量，未新增参数。
- **测试**：`test_cli_valid_command_smoke` 断言改为校验 stderr 含新提示行且反映真实覆盖路径；新增 `test_cli_default_db_path_visible_without_touching_real_home`，通过临时 `HOME` + `PYTHONPATH` 保留 user site-packages 的方式，验证默认路径场景全程不触碰生产 `cache.db`。全量 `381 passed`。
### collab-pipeline 执行复盘（首次接入本仓库，2026-07-02）

- **首次初始化**：本仓库此前没有 `.claude/ai-collab/config.yaml`，本轮先跑 collab-setup 初始化配置和空状态文件，再走标准 implement→commit→QA→裁决流程。
- **codex 跨仓库 sandbox 限制**：codex:codex-rescue 的实现派发被拒绝写入本仓库文件（"writing outside of the project; rejected by user approval settings"）——与 a-stock-lib HANDOFF.md 记录的 a-stock-tracker 案例同一模式，确认这不是孤立个案，而是 codex 沙箱把 project_root 绑定在当前会话主工作目录（本次是 a-stock-lib）而非目标 ai-collab 项目目录。PM 按 collab-pipeline 既定 fallback 直接实现，未受阻。
- **QA 审查一次调度异常**：codex-self-review 审查第一次派发返回了与任务完全无关的内容（只回显了 MCP context7 使用说明，报告"未收到任务"），重新派发同一 prompt 后正常完成、0 发现。这个"调度层空转"现象与已知的"后台执行/轮询"问题不同（不是同一类），已作为 ai-collab 共享 skill 的 patch 提案记录（见本轮 collab-retro Output 2）。
- **QA 结论**：codex-self-review，0 Critical/Important/Minor 发现，verdict=reliable。这是本仓库 qa-reliability 台账的第 1 条样本（`reliability_min_samples: 10`，尚不足以判断该 QA 工具在本仓库的长期可靠性）。

## [2.4.2] 2026-06-29

### 审查驱动修复（来源：2026-06-29 全量框架 agy+codex 对抗审查，3 Important成立）

#### Fix-1：格雷厄姆数 A/E 框架三档分层（替换原一刀切置顶规则）
- **根因**：原规则"股价>格雷厄姆数=置顶"在A股制造/消费PE环境下几乎永远触发，产生警告疲劳且无甄别价值
- **修复**：按框架独立设定阈值——A框架：≤1.0x安全/1.0-2.0x合理溢价/>2.0x警戒；E框架：≤1.5x安全/1.5-3.0x消费溢价/>3.0x警戒；C/D框架：>1x不置顶仅标注；B/F/EPS≤0豁免不变

#### Fix-2：B框架 WebSearch 补搜失败降级规则
- **根因**：净息差/不良率/拨备覆盖率缺失时无降级处理，可能输出不可信评分
- **修复**：单字段缺失→对应维度0分+标注可靠性受限；三字段全缺→置顶"不适用于投资决策"强制指向原始数据源

#### Fix-3：医药 REITs 框架路由
- **根因**：亏损创新药路由到A框架会被ROE[15]维度系统性惩罚；REITs进入框架评估会产生无意义得分
- **修复**：路由表新增两行——亏损Biotech（R&D>40%+≥2年亏损）→F框架；REITs→⛔明确拒绝+替代建议；新增tie-break补充规则（50%时优先A框架）

#### Fix-4：A股特有风险——大股东治理专项检查
- **根因**：现有框架缺乏对大股东占款/违规担保的系统性识别，治理风险无法通过财务指标发现
- **修复**：第五步末尾新增专项搜索；官方公告/监管函触发时仓位强制观望（不受矩阵约束）；治理红线与财务红线层级关系明确

---

## [2.4.1] 2026-06-29

### 审查驱动修复（来源：2026-06-29 比亚迪002594独立审查 agy，2 Critical + 1 Important成立发现）

#### Critical-1 修复：送转股不影响PE历史分位——已加入第三步择时评分注意事项
- **根因**：评估时误认为"10送20后历史PE比较基准不确定"，对PE历史分位估值得分额外折扣3分（给12/15而非14/15）
- **正确逻辑**：行情软件历史PE分位均采用后复权EPS+除权调整价格自动重算，送转股不影响历史基准
- **修复**：SKILL.md 第三步估值信号表后新增 ⚠️ 规则，明确禁止以送转股为由折扣历史分位评分

#### Critical-2 修复：汇兑损益须剔除后再评估净利增速——已加入第二步基本面评分
- **根因**：比亚迪Q1 2026财务费用汇兑损益单季摆动约-40亿，报告直接以表面净利-55.38%评分未剔除非经常项，低估经营性增速
- **正确逻辑**：剔除汇兑损益后经营性净利润实际仅-14.7%，而非表面上的"腰斩"级恶化
- **修复**：SKILL.md 第二步基本面评分添加汇兑损益剔除规则，波动金额>当期净利润30%时必须双口径呈现并以经营性口径打分

#### Important-2 修复：流动比率<1.0须明确标注——已加入A.md风险关注项
- **根因**：比亚迪流动比率0.79已在缓存字段中，但报告未在任何评分维度中提及
- **修复**：A.md 红线之后新增 ⚠️ 风险关注规则，流动比率<1.0时须在报告中明确说明成因，不允许完全忽略

### A框架增补
- 资产负债率条目新增行业脚注：整车/重型设备制造负债率≤75%且有息债务/总债务<40%时视同格档，需拆分有息债务与应付账款

### 新增：独立审查闭环规则（SKILL.md末尾）
- Critical/Important级审查发现 → 必须追溯框架根因 → 是框架问题则同轮更新文件+版本+1
- 比亚迪(002594) 2026-06-29 agy审查为首例记录案例

---

## [2.4.0] 2026-06-23

### 架构调整：评分"打分确定性化"砍掉，改为客观指标核对清单（checklist）
**背景**：原计划是把各框架评分做"确定性化"，让代码而非Claude给出可信总分。
codex+agy 两轮对抗审查发现：cache 里多数字段是单期快照（无多年趋势/连续性数据），
商业类指标（R&D强度、订单能见度/NRR、压力测试后股息率等）完全没有数据支撑，
继续做加总总分只会制造"假精确度"。最终决定 pivot：新增 `checklist.py`，
只逐项核对客观指标是否达优/达格/未达/数据缺失，**不输出加总分**；
主观项（护城河/行业地位等）和数据缺口都显式标注不参与代码判定，
最终评级仍由 Claude 综合判断。

### 新增
- `checklist.py`：A/C/F 三框架核对清单（B/D/E 框架未做，见 TODOS.md）
  - 单档判定双向支持：`excellent_threshold`/`pass_threshold` 任一为 `None` 都能正确判定，不强制要求两档都存在
  - `trend_unverified` 标志：数值可核对但框架文档里"趋势/连续性"修饰语（如"不下滑"）无法验证时，`data_status` 标"简化判定"而非"完整"，不冒充已验证趋势
  - `C_SKIPPED_ITEMS`/`F_SKIPPED_ITEMS`：checklist 工具无法核验的维度（C框架压力测试后股息率、F框架研发投入强度——cache未采集对应字段），报告里显式公告，权重不变，仍按框架文档人工评分
  - F框架"经营现金流质量"为唯一派生指标（`operating_cf_per_share/eps`，同期数据，非跨期编造），未引入通用 compute 抽象（YAGNI）
  - `cache.py checklist <代码> <框架A|C|F>` 子命令，直接打印核对报告
- 测试：`tests/test_checklist.py` 41 项，覆盖三框架全部判定分支+边界值+数据缺失路径

### 修复（agy 对抗审查两轮，均为审查后修复，非用户报告）
- C框架"净利润增长趋势"格档判定字段语义错配：原用 `net_profit_growth`（增速）判断"是否亏损"，增速为负不代表亏损，改用 `eps`
- `format_checklist` 完全没有渲染 `note` 字段，导致备注写了但用户看不到
- `_to_float_or_none` 未过滤 NaN，NaN 与任何阈值比较返回 False，被误判"未达"而非"数据缺失"
- F框架"经营现金流质量"比值在 `eps<0`（亏损）时两负数相除符号反转，可能把"亏损且现金流为负"误判为"达格"；现在 `eps<=0` 统一判数据缺失

### SKILL.md 接入设计 + agy 独立审查修复（同日，spec见 docs/superpowers/specs/2026-06-23-skill-checklist-integration-design.md）
- 设计方案已与用户过完brainstorming流程并批准，确定"硬约束"方案：checklist档位绑定Claude打分上下限，档位内裁量空间保留
- agy 独立审查 spec 发现 4 处真实漏洞，已修复：
  - A框架毛利率漏标 `trend_unverified`，导致单期数值过线被误标"完整"（绕过趋势核验降档规则）
  - `C_SKIPPED_ITEMS`/`F_SKIPPED_ITEMS` 的 reason 文案及 `format_checklist` 的小节标题误写"权重不计入总量/不计入权重"，与 spec 的"权重不变、纯人工评分"矛盾——两处文案均已修正
  - spec 约束表对"单档位定义"（`excellent_threshold`/`pass_threshold` 为 `None` 是故意留白，不代表代码判定该档不存在）处理过严，曾导致 Claude 永久无法给优档分或被迫对"无明显下滑"類质性达格情形打0分；已加"单档位留白可人工裁量"例外
  - spec 错误降级路径曾完全静默，与 B/D/E 框架（本不支持 checklist）报告无法区分；已要求显式标注"⚠️ checklist核验失败"
- checklist.py 改动已补测试，41 项全过

### SKILL.md 本体接入实现（同日，writing-plans计划：docs/superpowers/plans/2026-06-23-skill-checklist-integration.md）
- 执行模式：用户指定 codex(implementer CLI) + agy(reviewer CLI) + Claude(adjudicator)，subagent-driven-development流程的CLI化适配
- 3处接入点全部落地：
  - 第二步新增"⚠️ 客观分项核验门槛"规则块（达优/达格/未达/数据缺失四档对Claude打分的硬约束+裁量空间），紧跟既有"主观分项证据门槛"段落
  - 第二步末尾新增触发条件段落：A/C/F执行`cache.py checklist`、B/D/E跳过（无回归）、报错显式标注"⚠️ checklist核验失败"降级
  - 输出格式第1项扩大数据缺失预警触发范围（不再局限于毛利率/PE分位/股息率三个硬编码字段）；第5项基本面评分子项加三态核验标注
- 过程中发现并修复2处计划文档（plan brief）自身的文案缺陷，均非codex实现错误：
  - Task3 brief与Task1已落地文本用语不一致（"人工判断，无客观数据支撑" vs "⚠️ 无客观数据支撑，纯人工判断"）——codex执行时主动标DONE_WITH_CONCERNS提出疑虑，adjudicator统一为后者
  - Task3 brief的报错标注文本遗漏了spec"错误处理"一节要求的"，已降级为纯人工评分"后缀——agy复审发现，adjudicator补全
- CLI层验证：`pytest tests/test_checklist.py` 41 passed（确认本轮未触碰checklist.py）；`cache.py checklist 600036 A`输出格式核对通过；`cache.py checklist 000001 A`报错路径（非0退出码）核对通过；人为制造数据缺失场景（600036 gross_margin=null）验证后已用`fetcher.py fetch 600036`还原生产缓存
- Step5端到端报告验证（实际走一轮A/C/B框架分析，检查报告呈现）无法在当前会话脚本化，留待下次实际分析时人工确认

### checklist.py 新增 D/E 框架支持（同日，TODOS.md P0-3a）
- 执行模式：同上（codex implementer + agy reviewer + Claude adjudicator），commit `640c253`
- D框架（水电/公用事业）：仅"资产负债率"[<55%优/<70%格] 可代码核验；ROE行业相对（fetcher只有
  绝对值无行业分位）、业务量增长（无物理量字段）、前瞻股息率压力测试（复用C框架同款数据缺口）
  三项进 `D_SKIPPED_ITEMS`，权重不变仍需人工评分
- E框架（消费）：ROE近3年均值/净利润增速/毛利率三项可代码核验，字段与A框架同构；存货周转天数
  （fetcher未采集）进 `E_SKIPPED_ITEMS`
- **关键校验点**：E框架毛利率（>50%优/>30%格）原文无"稳定/不下滑/趋势"等修饰语，不同于A/F框架
  的毛利率定义，因此**未**标 `trend_unverified`，`data_status` 为完整判定而非简化判定——codex
  实现与agy复审均确认未踩中这个容易照抄出错的陷阱
- 测试：65 passed（原41 + 新增24，含parametrize边界值展开），CLI手动验证（D/E各一支虚构股票）
  输出格式核对通过
- B框架（银行）不在本次范围：nim/npl_ratio/provision_coverage 三字段已注册但SKILL.md现在把
  WebSearch+写入安排在流程末尾，打分阶段缓存为空、无法核验，需要改动P0-4刚验证过的执行顺序，
  有回归风险，且保险/券商子变体字段名完全不同天然无法覆盖——单独列为TODOS.md P0-3b，待用户决定

### checklist.py 新增 B 框架支持（同日，TODOS.md P0-3b）
- 执行模式：同上（codex implementer + agy reviewer + Claude adjudicator），commit `f6e0944`
- **原计划的"顺序重排"方案被agy对抗审查推翻，改为更简单的"方案D"**：先写设计提案
  `.superpowers/sdd/p03b-b-framework-design-note.md` 交agy对抗审查，发现两层问题——
  ① `cache.py` 的 `set_fundamentals`/`cmd_set` 是 `INSERT OR REPLACE` 整行覆盖、无字段级
  合并，naive提前写入nim/npl/provision会静默冲掉ROE等已缓存字段（Critical）；
  ② 即便解决①，nim/npl_ratio/provision_coverage 三项的数据来源是Claude自己WebSearch后
  手动写入缓存（fetcher.py FIELDS注册表标注来源为'web'），核验对象与核验来源同源，属于
  自证循环/假兜底，不构成独立校验——这条原则已写入长期memory
  `feedback_checklist_independent_data_source.md`，约束以后所有checklist.py框架扩展
- 最终方案：只接入 `roe_3y_avg`[>13%优/>9%格]（fetcher.py独立抓取，与A/C/D/E框架同构）；
  净息差趋势/不良贷款率/拨备覆盖率三项进 `B_SKIPPED_ITEMS`，reason明确写"核验对象与核验
  来源同源，不构成独立校验"（区别于D/E框架SKIPPED_ITEMS表层的"无API"措辞）；**不碰
  cache.py写入逻辑、不改SKILL.md执行顺序**，零回归风险
- 实现过程中发现并修复1处既有测试的隐藏耦合（非codex引入）：`test_unsupported_framework_
  raises_custom_error` 原用 `'B'` 作为"不支持框架"的探测值，B框架支持后该假设不再成立，
  改用 `'Z'`，agy复审确认必要且正确
- 测试：73 passed（原65 + 新增8，含parametrize边界值展开），全量308 passed/2 xfailed/
  1 xpassed（与改动无关），CLI手动验证（中国银行601988虚构数据）输出格式核对通过
- 保险/券商两个B框架子变体字段名与FIELDS注册表完全不一致，仍天然排除在checklist.py覆盖
  范围外——这是既有限制，非本次倒退

### ⚠️ 已知缺口（未在本轮处理）
- SKILL.md 中仍保留旧的 `set-score`/`得分` 参数调用说明，尚未因这次架构调整而更新（TODOS.md P0-5——经后续核实已确认二者正交无需改动，见TODOS.md P0-5说明）
- 端到端报告验证（spec验证点1/3/4，需实际分析一支A/C/B框架股票）尚未做，留待下次分析时确认

### 全仓库工程视角审查（agy独立审查，非投研方法论审查）+ 3条Critical修复
**背景**：用户要求对项目做一次纯工程视角审查（区别于之前已做过的投研方法论审查），
agy审查范围覆盖 cache.py/checklist.py/fetcher.py/测试/配置/CLAUDE.md红线合规，识别出
DRY/架构/测试覆盖/红线合规四个维度的问题，按Critical/Important/Minor分级。

**DRY判定**：6框架的平行硬编码（`checklist.py`的`X_CHECKLIST_DEFINITIONS`/`X_SKIPPED_ITEMS`/
`X_SUBJECTIVE_ITEMS`+if/elif路由、`cache.py`的`cmd_checklist`字典、`FRAMEWORK_KEYWORDS`、
`STOP_LOSS_PCT_MAP`）已跨过YAGNI临界点，建议重构为`FrameworkMetadata` dataclass +
`FrameworkRegistry`统一注册——本轮**未执行**，仅记录为后续重构方向

**Critical 3条已修复（commit `15ac392`，codex implementer + agy reviewer + Claude adjudicator）**：
1. `cmd_set_analysis` 用 `INSERT OR REPLACE` 整行覆盖 `analysis_results` 表，且INSERT列表
   不含 `flags`/`score_breakdown`/`return_pct`/`holding_days`——同一股票同一天重复执行
   set-analysis会把之前 `set-flag`/`set-score-breakdown` 写入的预警和分项得分静默清空成
   NULL，且不限于B框架场景，是当前每天在用的核心分析流程里的真实数据丢失bug。
   修复：SQL改为 `INSERT ... ON CONFLICT(code,date) DO UPDATE SET`，UPDATE子句排除上述4列
   不碰；`score`/`framework` 用 `COALESCE(excluded.x, analysis_results.x)`（显式传参覆盖，
   不传保留旧值——因 `cmd_set_score` 是独立写入同一列的命令，二者语义需要兼容）
2. 项目根目录无 `requirements.txt`，违反CLAUDE.md红线。新建，列出akshare/pandas/requests/
   pytest四个PyPI依赖（版本号已用`pip show`核实）+ a-stock-lib本机本地包说明（写成注释
   而非可解析依赖行，避免在没有该本机绝对路径的环境上`pip install -r`直接报错）
3. `.gitignore` 未排除 `.env`，违反CLAUDE.md红线。已追加一行
- 测试：新增3个回归测试（验证修复前会失败、修复后通过），`tests/test_cache.py` 71 passed，
  全量311 passed/3 xfailed（与改动无关的已知flaky测试本轮未触发）
- agy复审确认：3条Critical均已正确修复，未引入新问题，未超出4文件改动范围（未顺手修
  Important/Minor项），Task quality: Approved

### ⚠️ 本轮未处理（agy审查Important/Minor项，留待后续）
- 6框架平行硬编码的DRY重构（`FrameworkMetadata`+`FrameworkRegistry`方案，见上）
- `cache.py` 18个CLI命令函数缺类型注解；`get_db`/`cmd_set_analysis`/`cmd_add_holding`等
  6处函数超50行限制；`fetcher.py`底层拉取函数（`_fetch_spot_data`等）用`print`代替logger
- `checklist.py`/`cache.py`双向import耦合（`cache.py`延迟导入`checklist`，`checklist.py`
  顶层导入`cache`）；`watchlist-refresh.sh`无任何脚本级测试覆盖；并发写入无显式测试
- `X_SKIPPED_ITEMS`用裸字典未改`@dataclass`；TODOS.md/CHANGELOG.md对T1重构子函数数量
  记录与实际代码漂移（记录5个，实际7个）——文档滴流性问题，无害

**2026-06-24复核更新**（codex只读工程审查，见`.superpowers/sdd/engineering-review-2026-06-24.md`，
详细证据/文件:行号均在报告内）：
- ✅ **已解决**：DRY重构（P0-7，`framework_metadata.py`的`FrameworkMetadata`+`FrameworkRegistry`）；
  `X_SKIPPED_ITEMS`裸字典改`@dataclass`（`SkippedChecklistItem`，P0-7同批引入），旧常量仅作
  向后兼容的派生视图保留（Minor，非新写路径）
- ⏸️ **仍未解决**：类型注解缺口/长函数/print代替logger；`checklist.py`顶层仍`import cache`
  （cache.py这侧已不顶层反向import，耦合降级但未消除）；`watchlist-refresh.sh`无脚本级测试
  （并发写入测试已部分补齐，`test_edge_cases.py`/`test_missing_coverage.py`覆盖了
  `cmd_add_holding`/`cmd_set_flag`/`cmd_close_holding`并发场景，但脚本本身仍无测试）；
  TODOS.md子函数数量记录漂移（`TODOS.md:27`写`_fetch_yield_and_pct`，实际函数名不存在）
- 🆕 **新发现**（本轮新增，详见TODOS.md P0-10）：`cmd_close_holding`未校验卖出价>0（已有
  xfail测试待转正）；`cmd_set_flag`并发非原子更新会丢flag（测试注释已承认）

### checklist.py 框架元数据 DRY 重构（计划一，TODOS.md P0-7）
**背景**：承接上面"全仓库工程视角审查"指出的DRY判定——6框架（A~F）的平行硬编码已跨过
YAGNI临界点，本轮正式执行重构。

- 新增零依赖叶子模块 `framework_metadata.py`（commit `9a9e086`）：`FrameworkMetadata`
  dataclass（`key`/`checklist_name`/`subjective_items`/`skipped_items`/
  `checklist_definitions`/`custom_builder`/`portfolio_label`/`industry_keywords`/
  `stop_loss_pct`，后3个字段为计划二预留，本轮只声明不接线，附WARNING注释防止误以为
  已生效）+ `SkippedChecklistItem` dataclass + `FRAMEWORK_REGISTRY` 容器；用
  `from __future__ import annotations` + `TYPE_CHECKING` 避免与 `checklist.py` 循环导入
- `checklist.py` 改用 registry（commit `62c9c54`）：6个框架的`X_SUBJECTIVE_ITEMS`/
  `X_SKIPPED_ITEMS`/`X_CHECKLIST_DEFINITIONS`平行常量改为从registry派生的兼容视图（18个
  旧模块级常量逐字保留，外部调用方零感知）；F框架专属的现金流质量构建逻辑改`custom_builder`
  钩子，消除`build_checklist()`里的`if normalized_framework=='F'`特判；`build_checklist()`
  改用`registry.get()`显式抛`UnsupportedFrameworkError`（不用裸下标访问——agy投资风险审查
  指出裸`KeyError`会绕过SKILL.md的核验降级路径，是真实投资风险不只是代码风格）；
  `format_checklist()`签名和内部实现完全不变（仍接收`list[dict]`，因为4个既有测试直接传
  legacy字典常量进去）
- `cache.py cmd_checklist()` 同步改读registry（commit `28e6b5f`）：删除手写的subjective/
  skipped两个本地字典查表，CLI输出逐字不变
- 测试：全量323 passed（2/3 xfailed是已知`database is locked`并发flaky测试，跟本次改动
  无关）
- **执行过程中的两次异常**：Task2/3的codex implementer派发均卡死（①scratchpad跨天同名
  文件残留导致误判DONE+并发进程风险；②长时间0% CPU无响应），改Claude直接用写计划阶段
  已预验证代码完成，未脱离plan文本；审查环节agy（实为Google Antigravity CLI）连续卡死
  3次，排查确认根因是prompt里"请核实理由是否站得住"类措辞会触发模型自主决定跑命令、
  进而卡进死循环（详见memory`project_agy_codex_run_command_hang.md`），换简化prompt后
  codex审查正常通过，0 Critical/Important/Minor
### checklist.py 框架元数据整合持仓止损路径（计划二，TODOS.md P0-8）
- 执行模式：codex implementer + codex reviewer（fresh dispatch）+ Claude adjudicator
  （agy本计划起暂停使用，见下方"卡死问题排查"小节），commits `37129dd`(Task1)/
  `614cca2`(Task2)
- Task1：往6个`FrameworkMetadata`实例填入`portfolio_label`/`industry_keywords`/
  `stop_loss_pct`字段值，逐字抄自`cache.py`原有的`FRAMEWORK_KEYWORDS`/
  `STOP_LOSS_PCT_MAP`，此时`cache.py`完全未改动，零行为风险
- Task2：`infer_framework()`/`get_stop_loss_pct()`改读
  `framework_metadata.FRAMEWORK_REGISTRY`，删除手写的`FRAMEWORK_KEYWORDS`/
  `STOP_LOSS_PCT_MAP`两个常量；`_FRAMEWORK_TOKENS`改成`_framework_tokens()`函数
- **写计划阶段实测发现并规避一个真实陷阱**：`cmd_add_holding`/`cmd_portfolio_risk`
  这两个持仓止损生产入口从不会触发`cmd_checklist()`里现有的`checklist`懒加载——
  已用`python3 -c "import cache; import framework_metadata; print(...)"`实测验证，
  若`infer_framework()`/`get_stop_loss_pct()`直接读registry不做自己的懒加载兜底，
  真实CLI调用会读到空registry，所有持仓都会被误判成默认止损线。已在
  `infer_framework()`/`get_stop_loss_pct()`/`_framework_tokens()`三处补上函数体内
  `import checklist`懒加载，并新增子进程隔离测试锁定这个保证（pytest同进程内
  `sys.modules`缓存会掩盖这个问题，必须用子进程隔离才能暴露生产环境下的真实行为）
- 零行为变化验证：穷举现有全部26个行业关键词（不是抽样）+ 穷举6个框架的止损系数，
  全量357 passed（324+33新增测试）

### codex调用方式的重要变更：raw shell → 官方`codex-companion.mjs`封装
- 全天排查codex/agy CLI审查任务反复卡死的过程中，发现codex插件提供了专门的官方封装
  `codex-companion.mjs`（`task`/`status`/`result`/`cancel` + job-id异步任务管理），
  应该通过`Agent`工具配合`codex:codex-rescue`子代理调用，或者直接用这套封装脚本，
  而不是之前一直用的raw shell `codex exec -s ... -o file`——已用`status --all`
  实测验证，raw shell方式对官方job管理系统完全不可见（`"running": []`），等于
  一直在用一条没有任何官方heartbeat/取消支持的野路子
- 换用`codex-companion.mjs`后效果立即可见：Task2 implementer第一次真正跑通
  （约3分钟完成，不是卡死），review稳定在10-20秒内完成；用`cancel <job-id>`
  代替手动`pkill`/`kill -TERM`+`pgrep`猜PID那套笨办法
- agy（实为Google Antigravity CLI）今天反复卡死且排查后确认跟prompt措辞/目录/
  session ID都无关（4组对照测试全部排除），是其后端共享执行通道本身坏死，
  本机找不到可重启的本地daemon——本计划起暂停使用agy，详见memory
  `project_agy_codex_run_command_hang.md`

### scratchpad手动verification环节的真实数据库事故（已发现并修复）
- 写计划阶段为了在隔离scratchpad副本里验证代码改动效果，额外手动跑了几条CLI
  smoke test命令，绕开了pytest的`isolated_db`autouse fixture——`cache.py`的
  `DB_PATH`默认值是硬编码绝对路径（不是相对于当前执行脚本所在目录），导致这几条
  手动命令实际写入了**真实生产cache.db**：虚构持仓（紫金矿业601899）+招商银行
  (600036)当天虚构分析记录+紫金矿业虚构fundamentals
- 发现后逐项核对删除：确认5支真实持仓（招商银行/长江电力/华东医药/中国神华/
  东方电缆）和招商银行原有5条历史分析记录均未受影响，已完整向用户披露事故全过程
- 详见memory `feedback_cache_db_absolute_path_hazard.md`——以后任何绕开pytest的
  手动CLI verification都必须显式传`CACHE_DB_PATH`环境变量指向临时文件

---

## [2.3.0] 2026-06-04

### 架构修复（P2三条，Opus 4.8执行）
- **P2-A 防韭菜断链**：异动股从"暂缓终止"改为继续完整分析+强制惩罚（市场情绪0分+追加-3分，时机评级上限★，仓位减半，结论顶部置顶警告）
- **P2-B 监控边界渗漏**：移除 research 中的减仓/止损仓位公式和止损条件，改为组合配置参考并指向 `/a-stock-monitor`
- **P2-C L3越界引用**：贴权基本面恶化不再跨界调用 monitor 的 L3 检查流程，改为在 research 自有维度落地（预期差 -3 分 + 风险降级 + 结论警示）

## [2.2.0] 2026-06-04

### 修复（Codex快速审查P1）
- **P1 择时封顶**：新增 max(0, min(20, 合计)) 封顶规则
- **P1 B框架**：明确适用范围为商业银行；保险/券商须补搜专属指标
- **P2 权重描述**：顶部"60%+40%"修正为"60分+20分=80分制（75%/25%）"

## [2.1.1] 2026-06-04

### 修复（Codex diff P2）
- D框架择时上限注释修复：从表格行间移至表格末尾（修复Markdown渲染断裂）
- JSON字段说明标注 pe_ttm 为静态PE非TTM

## [2.1.0] 2026-06-04

### 修复（独立审查P0/P1/P2）
- cache.py 评级映射对齐 /80 分制
- fetcher.py PE字段口径标注
- 格雷厄姆预筛选新增F框架/EPS≤0豁免
- C框架7折+上限叠加规则明确
- D框架择时上限迁移到第三步
- description 清晰化，指向 a-stock-monitor

## [2.0.0] 2026-06-04

### 重大改动
- **P4 优化**：框架表格压缩/懒加载，节省约683 token/次（T4-2）
- **拆分架构**：持仓监控步骤独立为 `a-stock-monitor` skill，第八步提取为按需加载（T4-1）
- **fetcher.py 扩展**：结构化字段增至16个，减少 WebSearch 用量（T4-3b）

### 新增功能
- 除权/贴权检查模块（分级扣分 -1/-2/-3，填权进度公式修正）
- 市场风格适配评分（±1分，风格轮动感知）
- DPS 交叉验证流程（防止 AKShare 缓存错误值，如招行3.013→2.016）
- 股息率交叉验证强制要求（所有框架）
- 数据口径标注规范（报告期标注）
- B框架 NIM/NPL/拨备必做 WebSearch 补搜规则

### 修复
- 除权检查：分级扣分区间歧义修正（10-50%→30-50%），优先级顺序明确
- 公式豁免扩展至分母≤0 的情形
- L3豁免明确"最高扣-1分两者并行"
- 市场风格表补 E消费行、B/D加股息率≥3%限定
- "站稳参考价"定义统一为连续3交易日

---

## [1.0.0] 2026-05-14

### 初始版本（CEO Review 通过）
- 基本面60% + 择时40%框架（B/C/D/A/E/F六大行业框架）
- P2 完成：评分验证/B框架结论/组合风险视图
- cache.py + fetcher.py 工具链
- 防韭菜检查模块
- 格雷厄姆估值门槛（第零步）

## [2.5.0] 2026-07-02

### 新增规则（agy 独立投研分析审查，6条防范规则固化至 SKILL.md）

- **C框架煤价口径**：引用现货价核验时须注明长协占比及财报传导滞后（不得用现货价直接推断当期盈利改善）
- **历史分位极低反向检验**：分位<5%时必须排除"结构性重定价"解释，不能单取乐观解读
- **临时L3核验须标注完整度**：未完整核验所有失效条件时，不得笼统写"L3未触发"；须标注"条件N/总条件N"
- **操作建议信息论据要求**：加仓/不加仓理由须为可验证信息论据，禁用情绪性标签（如"赌复仇"）
- **边际改善措辞约束**：单月/单季度数据改善禁止称为"实质性基本面改善"，须连续2+期确认
- **同比增速基数披露**：引用同比增速须同时披露基期量级，脱离基数无法判断含金量

### 流程改进

- collab-pipeline 文档注入任务类型规范补丁已应用至 ai-collab 共享模板（grep -F 验证 + action_safety 锚点规则）
