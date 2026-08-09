# A股研究投资框架修复规范（2026-08-09）

## 背景

紫金矿业（601899）报告的独立 AGY 投资审查与父级复核确认：当前研究框架存在决策出口冲突、PB/BPS 报告期混用、成长型资源股单轴估值、资源成本证据不足、周期边界过度确定及 QA 只检查形式等问题。用户已明确授权在本 canonical 项目修复；该目录通过 symlink 同时是 Hermes active Skill 源。

## 目标

在不增加外部依赖、不改变数据库 schema、不触碰生产数据库/cron/凭证/交易执行的前提下，使 Research 结论 fail-closed、只有一个仓位出口，并让 QA 能拒绝关键算术、证据和动作冲突。

## 范围

1. `a-stock-research`：
   - 双轨矩阵是唯一操作/仓位出口；总分保留为启发式展示，不再映射操作。
   - 1/3、2/3 只表示已批准单股风险上限内的分批比例；未知组合时不得解释为账户可用资金比例。
   - C 成长分支的 PB 分位必须与至少一个前瞻或周期归一化估值交叉检查；冲突时不输出时机总分、综合总分或矩阵仓位。
   - C 的储量竞争力缺少 AISC、现金成本、品位或成本曲线可比证据时最高为格档。
   - 周期相邻阶段证据冲突时展示两个情景分数并采用更保守情景，不把边界判断包装成单点精度。
2. Runtime fetcher：当前 PB 使用与历史 PB 分位相同报告期的 BPS 和已验证当前价计算；不再把第三方最新 PB 与年度 BPS 混用。字段 provenance 保留价格时点和财报期说明。
3. `a-stock-qa`：新增估值算术/报告期一致性、唯一动作出口/仓位范围、C 框架估值冲突与成本证据检查。
4. 记录 changelog 和回归测试。

## 非范围

- 不增加 NAV/DCF 平台、共识数据库、回测工程或自动交易。
- 不发明 PB 60% 或 forward PE 12x 等新硬阈值。
- 不修改 A/B/D/E/F 的估值阈值。
- 不修改数据库 schema、生产状态、cron、凭证或客户端链接。
- 不重新分析或写入紫金矿业缓存/持仓。

## 不变量

- 数据缺失、口径不兼容或估值冲突时 fail-closed。
- W1 写入仍要求 `--confirm-write`。
- QA 保持纯文本、`python3 -I` 可运行且不依赖 runtime。
- active symlink、安装路径和客户端路由不变。

## 验收标准

1. `PB = current_price / compatible_BPS` 的单测通过，且不调用第三方 PB provider。
2. Research Skill 不再含综合分数到操作建议的第二出口，也不再用“可用资金 × 矩阵比例”定义仓位。
3. C 框架明确估值冲突 fail-closed、成本证据缺失封顶及周期双情景规则。
4. QA rubric 覆盖三类新增检查，现有 standalone smoke 继续通过。
5. `uv run pytest -q`、`uv run ruff check .`、`uv run python scripts/validate.py`、`python3 -I tests/qa/standalone_smoke.py` 全部通过。
6. 最终 diff 仅包含本规范列出的文件和必要测试/文档。

## 回滚与停止条件

- 基线 commit：`b61ea997d1b8cc9819552e9581ed15d3942f0100`。
- 回滚：对本次变更文件使用该 commit 恢复；不执行 reset、rebase 或生产状态恢复。
- 若 PB 同期计算破坏历史分位可比性、QA standalone 失去独立性、或项目必需门禁失败且无法在本范围内修复，则停止，不发布或提交。
