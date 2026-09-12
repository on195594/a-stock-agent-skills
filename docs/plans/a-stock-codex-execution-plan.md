# Codex 执行计划：a-stock-agent-skills × a-stock-lib 架构收敛（审查修订版）

> 基于：`a-stock-agent-skills × a-stock-lib 联合工程审查报告`
>
> 独立审查：AGY，结论 `REQUEST_CHANGES`，conversation id `3b0a7973-57de-4b5e-ab92-2a7388a0181d`
>
> 本修订版只保留能直接降低规则漂移、跨仓耦合和不可复现安装风险的工作。未经单独授权，不改变生产数据库、cron、真实持仓、W1 状态、仓库设置或发布状态。
>
> **状态：已完成（2026-09-12）。** 最终跨仓独立验收结论为
> `APPROVE_PLAN_COMPLETE`；实际落地证据与复盘见第 12 节。

## 0. 审查整改结论

1. **不建立 `a-stock-agent-skills/master`。** 保持 GitHub 当前默认分支：
   - `a-stock-lib` → `master`
   - `a-stock-agent-skills` → `main`
2. **禁止直接推送默认分支。** 每个最小改动在短生命周期主题分支完成，经 CI、独立只读审查和 PR 后合并。
3. **不在现有脏工作树里开发。** 现状中的未跟踪计划文件和 `a-stock-lib/uv.lock` 不得被删除、覆盖或藏匿；执行时使用基于远端默认分支的新 worktree，并在该 worktree 内严格要求 clean。
4. **保留下游兼容验证，但只作为 `a-stock-lib` release candidate gate。** 不把它加入每次普通代码变更的必跑 CI，遵守 `a-stock-lib/docs/RELEASE_CHECKLIST.md`。
5. **不做预设 DDD 目录重构。** 原 Phase 5 的 application/domain/infrastructure/presentation 拆分移到延后事项；只有真实依赖方向问题无法通过删除、复用或小范围移动解决时，另写 spec 再审查。
6. **跨仓回滚必须 consumer-first。** consumer 已依赖 owner 新 contract 时，不得先回退 owner。

---

# 1. 总执行约束

## 1.1 必须遵守

1. 目标分支跟随仓库现有默认分支，不迁移或新增默认分支：`a-stock-lib/master`、`a-stock-agent-skills/main`。
2. 禁止直接 push 默认分支、禁止 force push；通过主题分支和 PR 交付。
3. 每个提交只解决一个架构问题，保持小步、可审查、可回滚。
4. 不修改生产数据库、生产 cron、真实用户持仓，不执行 W1 写操作。
5. 不更改现有投资策略语义；若任务明确要求修复两仓不一致，必须先用测试和已有规范固定 authoritative 语义。
6. 不合并两个仓库，不创建第三个 policy 仓库。
7. 不做无关格式化、全仓 rename 或预防性抽象。
8. 不读取或提交真实 token、env、`cache.db`、日志；凭据一律写为 `[REDACTED]`。
9. 所有跨仓修改先定义 owner、public contract、兼容窗口和回滚顺序。
10. owner 先合并并产出可追溯 contract/artifact，consumer 后更新；不得让 consumer 依赖未合并分支或可变 Git ref。
11. 本计划不授权修改 GitHub 分支保护、发布 artifact 或合并 PR；这些外部状态变更需要执行时的明确授权。
12. 子代理只能提供审查证据，不能替代父级验证、提交、合并或发布决定。

## 1.2 默认分支保护门禁

Phase 1 首个 PR 合并前，确认两个默认分支至少具备：

- 禁止 force push；
- PR 合并；
- 必需测试通过；
- 至少一次独立只读审查。

若当前仓库设置不满足，仍可准备主题分支和 PR，但必须停止在合并前，不得以“仓库未保护”为理由直接推默认分支。

## 1.3 隔离工作区

先只读记录原工作树，不清理任何既有文件：

```bash
git status --porcelain=v1 --untracked-files=all
git branch --show-current
git rev-parse HEAD
git remote get-url origin
```

然后：

```bash
git fetch origin --prune
git worktree add -b arch/<phase-step> <isolated-path> origin/<default-branch>
cd <isolated-path>
git status --porcelain=v1 --untracked-files=all  # 必须无输出
```

禁止用 `git status --untracked-files=no` 掩盖未知文件。若 worktree 不 clean，先找出来源；不得删除原工作树中的未跟踪文件来满足门禁。

每阶段开始前，在隔离 worktree 内读取并遵守：

```text
AGENTS.md
README.md
相关 tests
相关 public API 与所有调用方
```

## 1.4 每个最小修改单元

```text
1. git fetch origin --prune
2. 确认主题分支基于最新 origin/<default-branch>
3. git status --porcelain=v1 --untracked-files=all 必须无输出
4. 运行修改前基线测试
5. 追踪目标函数/contract 的全部调用方
6. 修改最小必要文件
7. 运行聚焦测试
8. 运行仓库完整测试与静态检查
9. git diff --check
10. 审查完整 diff
11. git add <明确文件>
12. git commit -m "<单一目的>"
13. git push -u origin <topic-branch>
14. 建立 PR，等待 CI 与独立只读审查
15. 获得授权后合并；fresh read-back 默认分支 SHA 和 CI 结果
```

不要为每个提交创建 PR；同一 Step 内可有多个单一目的提交，但一个 PR 不得跨 Phase。

## 1.5 每个阶段必须输出

```text
Summary
Files changed
Behavioral changes
Compatibility impact
Tests run
Tests passed
Known gaps
Rollback
Branch / PR
Base SHA
Head SHA
Artifact / contract version（如适用）
```

## 1.6 基线失败规则

- 基线失败：停止，不把既有失败归因于新改动。
- 测试因网络、token 或生产数据不可用：改用仓库已有 fixture/fake provider；不得读取真实凭据或执行写操作。
- 发现计划中的文件、函数或假设不存在：停止该 Step，更新计划或 spec，不猜测替代路径。
- 同一 Step 连续两次修复仍无法通过：停止并报告根因证据，不扩大重构范围。

---

# 2. Phase 1 — Owner correctness

## 目标

先在 owner 仓库固定 A-F 阈值 exact-boundary 语义。Consumer 迁移要等 Phase 2 的不可变 artifact 和正式依赖完成，避免未发布 contract 造成执行死锁。

## Step 1A — 固定 exact-boundary 语义

**仓库：** `a-stock-lib`

### 先证明

1. 审计 `a_stock_lib/framework_scoring.py` 中 `_higher`、`_lower` 及所有直接比较。
2. 对照已有 framework 文档、历史测试、Agent checklist 行为；生成每个维度的 `inclusive/exclusive` 对照清单。
3. 对无法由既有规范判定的边界，停止并请求业务语义确认，不凭直觉选 `>` 或 `>=`。

### 测试先行

在 `tests/test_framework_scoring.py` 增加参数化 exact-boundary regression，至少覆盖 A-F 各一组关键维度：

- `excellent - epsilon`
- `excellent`
- `excellent + epsilon`
- `pass - epsilon`
- `pass`
- `pass + epsilon`
- lower-better 对称边界

固定浮点输入和 epsilon，断言分数、分类、解释文本及 `rule_hash` 变化语义。

### 最小实现

只修改共享 helper 或真实 owner 处的比较语义；不同时改权重、分类名称、结构或输出格式。优先复用 `_higher` / `_lower`，不为每个框架重复补丁。

### 验收

```bash
uv run pytest tests/test_framework_scoring.py -q
uv run pytest -q
```

并保存边界矩阵作为测试参数，而不是再建一份可漂移的 Markdown 阈值表。

---

# 3. Phase 2 — Reproducible packaging and release

## 目标

消除当前已证实的：

- consumer `pyproject.toml` / `uv.lock` 未声明 `a-stock-lib`；
- README 要求 `uv sync --frozen --inexact`；
- installer 使用 `venv --system-site-packages`；
- clean machine 无法仅凭锁文件复现。

## Step 2A — 建立唯一可追溯 artifact 路径

**Owner：** `a-stock-lib`

选择并只维护一种生产依赖来源：公开 GitHub Release 上的版本化 wheel。当前无 GitHub Release，因此在 artifact 发布获得明确授权前，本 Step 状态为 **blocked**，不得用本地绝对路径、可变分支、editable install 或未固定 Git ref 冒充完成。

Release candidate 必须：

1. 从明确 owner commit 构建 wheel；
2. 运行 owner 全量测试与 `python3 -m build`；
3. 记录版本、commit SHA、wheel SHA-256；
4. 获授权后发布不可变 tag/release；
5. fresh download 后重新核验 hash 和 metadata。

## Step 2B — Consumer 正式声明依赖

**Consumer：** `a-stock-agent-skills`

在 owner artifact 可用后：

1. 在 `pyproject.toml` 声明精确版本的 `a-stock-lib`；
2. 使用固定 release wheel URL / lock hash，更新并提交 `uv.lock`；
3. 删除 `--inexact` 要求；
4. 删除 `--system-site-packages`；
5. installer 和 runtime 从同一声明式依赖事实源读取版本，不再平行维护 `REQUIRED_A_STOCK_LIB_VERSION`，除非它由构建元数据自动导出；
6. 临时 source/wheel 安装参数如仅用于 release candidate 验证，应明确为 release-check 路径，不作为日常生产依赖 fallback。

### Clean-install 验收

在新的临时目录和全新 venv 中：

```bash
uv sync --frozen
uv run pytest -q
uv run ruff check .
uv run python scripts/validate.py
python3 -I tests/qa/standalone_smoke.py
```

再从随机 cwd 核验：

```text
importlib.metadata.version("a-stock-lib")
a_stock_lib.__file__
```

必须指向 lock 对应安装产物，不得因仓库 cwd 或 system site packages 偶然成功。

## Step 2C — 仓库内 CI

两个仓库只增加最小 CI：

- frozen lock / clean install；
- full pytest；
- 已有 Ruff / validator；
- build metadata 检查。

不增加矩阵、缓存层或发布自动化，除非一次真实失败证明需要。

## Step 2D — Release-only downstream compatibility gate

遵守 `a-stock-lib/docs/RELEASE_CHECKLIST.md`：只在 owner release candidate 时验证两个直接 consumer，不放进每个普通代码 PR。

提供一个可重复执行的 release-check 脚本或明确命令序列：

1. 构建候选 wheel；
2. 在隔离环境安装该 wheel；
3. 对固定 consumer default-branch SHA 运行其全量测试；
4. 记录 owner SHA、consumer SHA、wheel hash、测试命令和结果；
5. 不修改 consumer 生产配置、cron、数据库或部署状态。

脚本可存在于 owner 仓库，但触发时机仍由 release checklist / RC workflow 管理。

---

# 4. Phase 3 — Consumer contract convergence

Phase 2 完成、consumer 已能从 frozen lock 安装 owner artifact 后，才执行本 Phase。

## Step 3A — `a-stock-lib` 成为唯一 A-F executable owner

先盘点并复用现有 public API：

- `a_stock_lib.framework_scoring.score_fundamentals`
- `a_stock_lib.contracts` 中已有类型
- 现有 score/classification/explanation/rule metadata

只有现有返回值无法表达 consumer 已使用的信息时，才扩展 typed public contract；新增 contract 需先发布新的 owner artifact 并更新 consumer lock。禁止为了“架构整齐”复制第二个 schema 或创建单实现 interface。

### Consumer 迁移

1. 列出 `a-stock-agent-skills/src/a_stock_agent_runtime/checklist.py` 中 `_evaluate_result` 的全部调用方和各自语义。
2. 只迁移与 A-F 共享 framework scoring 重叠的判断；Agent-only workflow 检查不得误删。
3. Consumer 只做输入适配、调用、展示和 W1 安全编排，不再拥有 A-F threshold 比较。
4. 以 golden/fixture 对比迁移前后非边界样本；边界样本以 Step 1A 的 authoritative contract 为准。
5. 所有 consumer 调用切换完成后才删除重复 helper/常量；仍有非重叠调用时保留并改名说明边界，不强删。

### 验收

- 代码搜索确认 A-F authoritative 阈值只在 `a-stock-lib` 可执行实现中存在；文档可引用，不可再执行。
- Agent 报告仍展示分数、分类、解释、`rule_version` / `rule_hash`。
- 两仓全量测试通过。

## Step 3B — 禁止读取 lib 私有 cache

已确认 consumer 中存在：

```text
src/a_stock_agent_runtime/commands_holdings.py
~/.cache/a_stock_lib/tushare_industry_map.json
```

现有 `TushareFundamentalsProvider.fetch_industry_map()` 已提供 public provider contract，因此默认复用它；除非测试证明它缺少必要状态，否则不新增 cache reader API。

### 实现

1. Consumer 移除私有路径、TTL、JSON shape 和 mtime 解释。
2. 通过 public provider 取得 `MarketDataResult`，显式处理 `ok/stale/failed`、provenance、freshness 和 error code。
3. 不吞掉认证/数据错误后伪装为“无行业”；沿用当前 fail-closed 或明确 fallback 语义。
4. Provider 测试用 fake client / tmp path；不得访问真实 token 或生产 cache。

### 验收

```bash
rg '\.cache/a_stock_lib|tushare_industry_map\.json' src tests
```

consumer runtime 代码结果必须为空；fixture 文件名可存在，但不得构成运行时文件 contract。

---

# 5. Phase 4 — Structured decision contract

## 目标

机器状态不再通过 Markdown report regex 反向解析。

## Step 4A — 盘点真实依赖

先搜索全部 report parser、regex、状态写入和调用方，列出：

```text
producer → field → consumer → safety consequence → current fallback
```

只迁移实际被机器消费且影响状态/门禁的字段；展示性文本继续留在 report，不进入 schema。

## Step 4B — 一个 versioned JSON contract

在现有类型/序列化模式上扩展，不并行创建第二套模型。最小字段：

```text
schema_version
stock_code
framework
framework_score
framework_classification
rule_version
rule_hash
l3_status
portfolio_risk
suggested_action
blocked
block_reason
source_provenance
freshness
```

要求：

- JSON 是 machine contract；Markdown 是由同一结构化结果渲染的人类报告。
- unknown field 向前兼容；缺失 safety-critical field 必须 fail-closed。
- schema/version 兼容策略和 golden fixture 同时落地。
- 不引入 schema registry 或新服务；一个仓库内 schema 文件/typed model 足够。

### Phase 4 落地合同（v1）

- 一个 envelope 只描述一只股票；`stock_code` 是六位代码。`framework` 持久化为现有规范值 `A通用`—`F科技`。
- `schema_version` 必须是整数 `1`。未知顶层/嵌套字段保留并接受；缺字段、错误类型、非有限数值和不支持版本在任何写入前拒绝。
- `framework_score` 是 `0—80` 的有限数值或 `null`；`framework_classification` 使用现有 `A级|B级|C级|D级|not_formed`。`rule_version`/`rule_hash` 是非空 scorer 标识。
- `l3_status` 使用现有 `not_applicable|not_triggered|pending|watch|triggered|invalid`；首次研究为 `not_applicable`，不得把 legacy/pending/watch/invalid 当作 clear。
- `portfolio_risk` 是本股票的投影对象，不是账户级第二 envelope；至少含现有状态词 `clear|blocked|incomplete|not_evaluated` 之一的 `status` 和字符串数组 `reason_codes`。
- `suggested_action` 使用报告合同现有唯一出口 `回避|等待|买入候选|观望|轻仓试探|小仓观察|买入1/3仓|积极买入2/3仓`。
- `blocked` 是布尔值；`block_reason` 是稳定代码数组。v1 代码为 `risk_gate_incomplete`、`valuation_conflict`、`bond_yield_missing`、`score_incomplete`、`portfolio_risk_blocked`、`l3_triggered`。估值冲突只能以此字段表达，证据放 `source_provenance`，不再匹配正文。
- `source_provenance` 是对象；`freshness` 是对象且必须含非空 ISO-8601 `as_of`。两者是结构化证据/时效状态，不从 Markdown 重建。
- 安全一致性：`blocked=true` 必须有 `block_reason` 且动作只能为 `回避|等待|观望`；`blocked=false` 必须没有 block reason；`framework_score=null` 与 `framework_classification=not_formed` 必须同时出现，且该状态必须 blocked；`portfolio_risk.status=blocked|incomplete|not_evaluated` 必须 blocked；`l3_status=triggered|invalid` 必须 blocked。
- `score-fundamentals` 的主观评估和周期输入改为一个结构化 JSON 对象；scorer 继续拥有枚举、规则版本/hash 和计算。`set-analysis` 从 stdin 只接收一个 v1 decision JSON，可选 `narrative` 仅用于展示；持久化 `decision_json TEXT`，并从已校验对象渲染 Markdown `result`。
- 新写只写 JSON 权威状态；有 `decision_json` 的当前行绝不调用旧 parser。历史 `decision_json IS NULL` 行原样保留，仅允许窄命名、fail-closed 的临时只读兼容，不自动回填或重建权威状态。

## Step 4C — 迁移与删除旧协议

先双读对比但单写 JSON；确认 fixture/golden 一致后切断 regex consumer，随后删除旧 parser。双写只允许作为有截止条件的迁移步骤，不得长期保留两套事实源。

---

# 6. Phase 5 — Thin Skills

## 目标

Skill 只保留 Agent 必须知道的 routing、stop condition、tool budget 和 safety boundary；确定性计算继续下沉到 runtime/lib。

## Step 5A — `a-stock-research`

保留：

- 何时进入 Research；
- 最少所需输入；
- 调用哪个已有 runtime/public contract；
- 数据缺失时停止条件；
- W1/持仓边界。

删除或引用：

- 可执行阈值副本；
- Python 已实现的估值/评分步骤；
- 重复 schema；
- 冗长示例中不影响 routing 的细节。

## Step 5B — `a-stock-monitor`

保留：

- 仅适用于真实持仓；
- monitor/runtime 入口；
- fail-closed 条件；
- W1 confirmation；
- structured result 的展示约定。

不把 stop-loss、L3、Tier 或 portfolio risk 迁入 `a-stock-lib`；这些仍由 Agent application runtime 所有。

## Step 5C — Progressive disclosure

只拆分真实造成上下文浪费、且有明确触发条件的内容；优先删除重复文字和引用现有文档。不要为每段内容新建 reference 文件。

---

# 7. Phase 6 — Agent behavior eval

在 Phase 1-5 稳定后，增加最小行为 eval。每个场景同时约束：

```text
allowed_tools
max_tool_calls
required_output_fields
forbidden_actions
stop_condition
expected_block_reason
```

至少覆盖：

1. 首次研究 → Research；
2. 真实持仓复盘 → Monitor；
3. 文本完整性检查 → QA；
4. 缺少持仓 → 不执行 Monitor；
5. 数据 stale/conflict/missing → fail-closed；
6. 未授权 → 不执行 W1；
7. 已有结构化数据足够 → 不额外调用 WebSearch；
8. 工具预算达到上限 → 停止并报告缺口。

优先在现有测试框架里增加少量场景，不引入新的 eval framework。

---

# 8. 延后事项：不在本计划自动执行

以下事项不是当前根因修复的必要条件，移出执行范围：

- 将 runtime 预设拆成 `application/domain/infrastructure/presentation`；
- 大规模目录迁移或 import rename；
- 新增 repository/service interface；
- 新 policy 仓库；
- 自动生成全部 policy 文档；
- 全面 observability 平台；
- 多版本并行规则引擎。

只有出现经过测试或 import graph 证明的依赖反转问题，且删除/复用/局部移动不能解决时，才为具体问题另写 spec 并独立审查。

---

# 9. 跨仓兼容与回滚

## 9.1 兼容顺序

1. Owner 先增加向后兼容 public contract；
2. owner tests/build/release gate 通过；
3. owner artifact 可追溯；
4. consumer 更新并验证；
5. 等 consumer 完成迁移后，另一个 PR 删除 owner deprecated surface。

禁止同一时间在两个默认分支制造必须同步合并才能工作的破坏性变更。

## 9.2 回滚顺序

若 consumer 已依赖 owner 新版本：

1. 先 revert / 回退 consumer 到旧 contract；
2. 验证 consumer 恢复；
3. 再决定是否 revert owner；
4. 每个 revert 仍走 PR、CI 和独立审查。

若 owner 变更是向后兼容且无安全风险，优先保留 owner surface，而不是为了“提交对称”冒险回退。

---

# 10. 每 Phase 完成定义

## Phase 1

- exact-boundary 语义有 authoritative tests；
- 非目标策略语义和 W1 行为未改变；
- owner 全量测试通过。

## Phase 2

- owner wheel 来自明确 commit，版本和 hash 可追溯；
- consumer dependency 与 lock 正式包含 `a-stock-lib`；
- 不再需要 `--inexact` 或 `--system-site-packages`；
- clean install 和随机 cwd import 通过；
- downstream compatibility 只在 release candidate gate 执行。

## Phase 3

- A-F executable threshold 只有一个 owner；
- consumer 不读取 lib 私有 cache；
- 两仓全量测试通过。

## Phase 4

- machine state 使用单一 versioned JSON contract；
- Markdown 不再被当作机器 API；
- safety-critical 缺字段 fail-closed；
- 旧 regex parser 已删除。

## Phase 5

- Skill 不复制 deterministic threshold/schema；
- routing、预算、停止条件和安全边界清晰；
- runtime/lib 继续承担确定性计算。

## Phase 6

- routing、tool budget、stop condition、blocked behavior 有可重复 eval；
- 无真实 token、生产数据或 W1 副作用。

---

# 11. 最终验收

全部满足才可宣告完成：

```text
[x] a-stock-lib 默认分支仍为 master
[x] a-stock-agent-skills 默认分支仍为 main
[x] 无直接 push 默认分支、无 force push
[x] 每个 Phase 使用独立 PR，CI 与只读审查证据可追溯
[x] 一个业务规则只有一个 executable owner
[x] consumer 只依赖 public contract，不读取 owner 私有 cache
[x] 新机器可从不可变 artifact + frozen lock 复现
[x] Agent 不承担可确定计算
[x] report 不再充当 machine API
[x] release-only downstream compatibility gate 可重复执行
[x] 无生产数据库、cron、真实持仓或 W1 修改
[x] 无凭据进入仓库
[x] 原工作树中的既有未跟踪/未提交文件未被删除或覆盖
```

若任一项失败，报告具体 blocker、证据和最小下一步；不得用扩大重构、跳过测试或绕过默认分支保护来“完成”计划。

---

# 12. 实际落地与任务复盘（2026-09-12）

## 12.1 最终状态

- `a-stock-lib/master`：`9f669ffb2729063e8fa7d94e69ab835f7fef49e4`；
- `a-stock-agent-skills/main`：`6078b8d73ff75e41728dea87c2cd4ad8e3194ae0`；
- `a-stock-tracker/master`：`32590f8b71320f367a8d19830d1608da7d0f4f86`；
- `a-stock-lib v0.7.0` wheel：
  `sha256:7c4a16d452f34574584531bab6fe9d150f3cb844e5c9b2fe072295f6bb2ee385`；
- 三个仓库的默认分支与远端一致，完整测试、静态检查、fresh frozen
  install、随机 cwd import、Release wheel 下载与元数据检查均通过；
- 最终跨仓只读验收：`APPROVE_PLAN_COMPLETE`。

Phase 1-3 通过 `a-stock-lib` PR #1-#4、`a-stock-agent-skills` PR #2-#5
和 `a-stock-tracker` PR #1-#2 落地；Phase 4-6 分别通过
`a-stock-agent-skills` PR #6、#7、#8 落地。Phase 6 最终 reviewed head 为
`69dab4051a3e5048ac80f158e6e1c2a4ccfb1d89`，merge commit 为
`6078b8d73ff75e41728dea87c2cd4ad8e3194ae0`。行为 eval 的复现方式、
隔离边界与单样本限制见 [`../agent-behavior-eval.md`](../agent-behavior-eval.md)。

## 12.2 复盘

**有效做法**

1. 先固定 owner contract 和不可变 Release wheel，再迁移 consumer，避免了
   两仓必须同步合并的脆弱窗口；回滚顺序保持 consumer-first。
2. 所有开发都在短生命周期 worktree 和主题分支中完成；每个 reviewed head
   均重新核对 CI、PR head 和独立审查结论，没有把“审查已启动”当成“审查通过”。
3. Phase 6 从手写 trace validator 改为真实 Hermes capture 加离线 scorer；
   capture 与 expected behavior 分离，CI 保持离线、确定性且无生产副作用。
4. 对 prompt oracle leakage、空 provenance、宽松 tool descriptor 和无效
   mutation coverage 的两轮审查意见都做了有界修复，并在新 exact head 上复审。

**暴露的问题与修正**

1. 初版行为 eval 同时生成 trace 和答案，属于自证式测试；修正为外部 Agent
   observed artifact，并让 golden oracle 只存在于 evaluator/test 侧。
2. provenance 不能只验证“像 SHA 的字符串”；修正为逐记录绑定实际
   Hermes session/model/provider、capture source commit 和非空 Skill hash 集合。
3. 缺少持仓、stale、missing、conflicted 必须各自拥有 fail-closed mutation；
   不能以一个宽泛 data-quality case 代替关键分支覆盖。
4. 组合验收命令隐藏了失败步骤；最终改为分仓、分 gate 运行并保存明确结论，
   环境缺少 `python -m build` 时使用仓库已有 `uv build`，没有把工具缺失误报为代码失败。

**保留边界**

- 没有修改生产数据库、cron、真实持仓、W1 状态或凭据；
- 不把一次 backend capture 宣称为模型稳定性证明；release candidate 仍需重捕获八个场景；
- 预设 DDD 分层、大规模目录迁移和新 policy 仓库继续延后，没有为本计划新增无消费者抽象。
