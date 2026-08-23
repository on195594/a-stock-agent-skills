# a-stock-lib 0.6.0 消费者切换与真实策略接线规范

**日期：** 2026-08-23
**状态：** 已实施；生产版本随后由 0.6.1/0.1.6 provenance 与格式基线补丁取代
**生产：** tracker `a-stock-lib==0.6.1`；agent runtime `0.1.6-8ab751454a5c` / lib `0.6.1`

## 目标

1. tracker 与 portable agent runtime 在隔离环境安装 `a-stock-lib==0.6.0` 并通过各自完整门禁。
2. tracker 生产环境只升级共享包到 0.6.0；保留现有 Framework A scorer、weights、样本口径和 cron 行为。
3. agent runtime 新增只读 `a-stock-cache score-fundamentals`，将缓存客观指标、调用方显式补充指标、报告中的 typed 主观标签和周期标签送入 `a_stock_lib.framework_scoring.score_fundamentals()`。
4. active `a-stock-research` 强制使用该命令产生基本面60分、规则版本/hash、缺失输入和红线；不得继续手工加总基本面分。
5. portable suite 发布为 `0.1.5`，要求 `a-stock-lib==0.6.0`，通过现有 installer 可回滚切换三个客户端和 runtime。

## 不改变

- 不把 research A—F scorer 接入 tracker daily；tracker 的 A scorer与research A规则不同，替换会重置现有预注册实验口径。
- 不修改 tracker `weights.json`、数据库 schema、股票池、cron 或历史记录。
- 不自动写分析、持仓、预警或交易；`score-fundamentals` 为 R0，只读本地 fundamentals。
- 不改变 timing 20分、双轨矩阵、交易授权和 QA 边界。

## score-fundamentals 合同

```text
a-stock-cache score-fundamentals <代码> <A|B|C|D|E|F> '<补充指标JSON>' < report.md
```

- 从现有 `stock_fundamentals.data` 读取结构化字段，并做固定键映射：`net_profit_growth -> net_profit_growth_3y`。
- 调用方 JSON 只补充缓存没有的、已核验的框架输入；同名键显式覆盖缓存值。
- 报告 stdin 解析现有 `SubjectiveAssessment` 与可选 `CycleStageAssessment`；B/C/D 缺周期时由 lib 返回 `complete=false`。
- 输出 JSON 包含 framework、rule_version、rule_hash、dimensions、subtotal、complete、missing_inputs、red_flags、blocked。
- `complete=false` 或 `blocked=true` 时只能报告缺口/红线，不得形成配置评级、时机总分或仓位动作。

## Shadow gate

- lib：130 tests、build、随机 cwd wheel import。
- tracker：临时 venv 安装0.6.0，项目结构、全量 pytest、Ruff、format、mypy、pip check和CLI smoke；实际 `.venv` 仍为0.5.3。
- agent suite：临时 venv安装 suite候选与lib0.6.0，全部pytest、Ruff、format、pip check、命令正反smoke；实际 runtime仍为0.1.4/0.5.3。
- AGY读取准确 diff 与shadow证据，`REQUEST_CHANGES` blocker 必须先修。

## Cutover

1. 提交三个仓库候选变更；a-stock-lib tag `v0.6.0`，suite tag `v0.1.5`。
2. tracker 更新 pin并安装 immutable 0.6.0 wheel，运行实际环境门禁。
3. 使用 suite installer `--client all --mode symlink --force --a-stock-lib-source /home/lin/a-stock-lib` 生成新 runtime和回滚manifest。
4. 回读两个生产环境的 metadata/module版本和安装路径；回读 runtime 持久 wheel/hash/source commit。
5. 比较切换前后 config 与 crontab hash，必须不变；不访问或修改真实业务数据库。

## 回滚

- tracker：重装保留的 `a_stock_lib-0.5.3` wheel并恢复 requirement pin。
- agent：将 `~/.local/bin/a-stock-*` 链接恢复至 `0.1.4-57c882433eeb` runtime；skill symlink仍指 canonical repo，无内容回滚需求。
- 任一实际门禁失败立即停止，不改 cron/DB，不继续另一个生产切换。
