# Research 数据能力与 Skill 拆分实施计划（2026-08-23）

状态：in_progress
规范：`../specs/2026-08-23-research-data-capability-and-skill-slimming-spec.md`

## minimum_landing_change

在隔离 worktree 中交付：同口径 5 年 PS 分位、非评分最新报告快照、三个渐进披露 reference 及聚焦回归；不部署生产。

## Phase ledger

| Phase | 状态 | 最小落地 | 验证 |
|---|---|---|---|
| 0 复盘 | completed | 三笔 `retro_notes` 写入并回读 | `retro-stats` 3例；`retro-pending` 空 |
| 1 规范 | completed | dated spec + 本计划 | 独立只读 spec review：APPROVE |
| 2 PS | completed | fetcher 输出 PS/current/window | RED/GREEN、真实寒武纪临时状态 smoke |
| 3 最新报告 | completed | lib字段 + consumer snapshot | 双仓 RED/GREEN、2026半年报快照回读 |
| 4 Skill 拆分 | completed | 3个 reference，主边界保留 | contract/validator/QA smoke |
| 5 集成审查 | in_progress | 版本、docs、wheel、影子兼容 | lib 104 tests；suite 641 tests；独立最终审查待完成 |
| 6 landing/cutover | not_started | 合并与生产发布 | 另行生产批准 |

## 执行任务

### Task 1：PS 数据能力

- `suite/src/a_stock_agent_runtime/fetcher.py`
- `suite/tests/research/test_fetcher.py`
- `suite/tests/research/test_p0_contracts.py`

先增加 fixture：10 年 `daily_basic` 含 `ps_ttm`，最近5年与前5年分布故意不同；确认 RED。随后保留 provider frame 的 `ps_ttm`，按月末和5年窗口计算 strict-less 分位并写 provenance。

### Task 2：最新报告快照

- `lib/a_stock_lib/providers/tushare_financials.py`
- `lib/tests/test_tushare_financials.py`
- `suite/src/a_stock_agent_runtime/fetcher.py`
- `suite/tests/research/test_fetcher.py`

先固定 provider 字段与年报/Q1 fixture。实现 endpoint 同期合并、修订去重和字段级 missing；年度 DataFrame 继续用于现有评分，快照从未过滤的最新报告生成。

### Task 3：Skill 渐进披露

- `suite/skills/a-stock-research/SKILL.md`
- `suite/skills/a-stock-research/references/{cycle-assessment,timing-adjustments,report-contract}.md`
- `suite/tests/research/test_p0_contracts.py`
- `suite/tests/qa/test_qa_contract.py`

机械移动详细表格/模板；主文件保留硬边界、摘要和直接链接。禁止改阈值或措辞语义。

### Task 4：版本、制品与影子验证

- `lib/pyproject.toml`、当前 release docs
- `suite/pyproject.toml`、README/CHANGELOG/operations 中当前候选说明
- suite installer version gate/tests

构建 `a-stock-lib 0.5.1` wheel，在临时 venv 外部导入；suite 默认 pinned gate 与 candidate gate分开验证，不改真实安装。

## 验证

```bash
# lib
pytest tests/ -q
ruff check .
python -m build

# suite
bash scripts/check.sh
git diff --check

# candidate shadow
# 临时 venv 安装 candidate wheel，再运行 suite 新增聚焦测试和全量门禁
```

## 审查

- spec review：实现前一次；
- final diff review：冻结双仓 HEAD/diff hash 后一次；
- reviewer 只读，不运行安装器、formatter、build 或生产命令；父级复核所有 finding。

## 回滚

- 实现阶段：删除两个 feature worktree/branch；主 checkout 和生产未变。
- landing 前：保留 base SHA 与 candidate commit。
- production cutover 不在本计划的既有授权中自动发生；需要时使用安装器 rollback manifest 恢复 `0.1.3/0.5.0`。
