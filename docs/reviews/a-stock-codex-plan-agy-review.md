# AGY 独立审查：a-stock Codex 执行计划

- 状态：`SUCCESS`
- 结论：`REQUEST_CHANGES`
- Conversation ID：`3b0a7973-57de-4b5e-ab92-2a7388a0181d`
- 审查模式：read-only

## 原始审查输出

- Verdict: **REQUEST_CHANGES**

- **Blockers (P0/P1 only)**
  - **Severity**: P0
    - **Evidence**: `docs/plans/a-stock-codex-execution-plan.md` 第 0.1 节、0.4 节（强制在 `a-stock-agent-skills` 建立 `master` 弃 `main`），第 0.5 节（`git push origin master`）。
    - **Impact**: 违背 GitHub 默认分支（`main`），将导致外部 clone 拉取到冻结代码。直接推送至 master（Direct Push）完全绕过了 PR 和人工 Reviewer 检查防线，在缺乏强制把关的情况下会引入极高风险的架构破坏。
    - **Minimal fix**: 删除第 0.4 节，维持 `a-stock-agent-skills` 使用 `main`；修改 0.1 和 0.5 节，禁止直接 push，必须提交特性分支（Feature Branch）并提交 PR 接受审查。
  - **Severity**: P0
    - **Evidence**: 计划第 0.3 节、0.5 节及第 10 节强制要求执行前 `working tree = clean` 及 `git status` 无输出。
    - **Impact**: 现场活体数据显示，`a-stock-agent-skills` 存在未追踪的执行计划文件，`a-stock-lib` 存在未追踪的 `uv.lock`。严格的 clean 检查会因为这两个文件的存在立刻抛错，直接把 Codex 阻塞在启动阶段，且规则禁止程序越权删除它们。
    - **Minimal fix**: 在环境守卫脚本和执行步骤中增加 `--untracked-files=no` 参数（即 `git status --untracked-files=no`），或显式将这两个文件加入检查白名单。
  - **Severity**: P1
    - **Evidence**: 计划第 2D 节要求“在 lib release candidate 上验证 consumer ... 不要只在 release checklist 写人工步骤”，尝试将下游兼容测试自动化进入代码变更流。
    - **Impact**: 公然违背了 `a-stock-lib/AGENTS.md` 中 “Release and downstream-consumer validation belong to `docs/RELEASE_CHECKLIST.md`, not every code change” 的硬性治理边界，且过度增加了开发期 CI 的复杂度。
    - **Minimal fix**: 删除 Step 2D 中针对日常代码变更自动触发的强制要求，将下游兼容性校验的发生时机退回并锁定在 `RELEASE_CHECKLIST.md` 阶段。

- **Non-blocking findings**
  - **Phase 5 过度设计（Overbuilding）**：计划宣称“不进行大爆炸式重构”，但 Step 5A-5C 计划将 `commands_monitor.py` 等平铺的 CLI 文件强行拆分成 application / domain / infrastructure 级别的复杂 DDD 分层。这对于仅需收敛事实源的第一阶段来说，是无依据的过度构建。
  - **跨仓回滚死锁（Rollback Assumptions）**：第 0.5 节提倡 `git revert`。但在跨仓库绑定的情况下，如果 consumer 已经消费了 owner 的新 API，单独 revert 其中一个仓库的提交会导致接口不匹配，计划中没有提及跨仓事务一致性回滚的策略。
  - **CI 的隔离缺失**：在 Step 2A 中，计划在 `a-stock-agent-skills` 中声明 `a-stock-lib` 的依赖，但后者暂未进入公共 Registry。如果在跨仓 CI 中没有妥善注入本地 Wheel 挂载或 Git 凭证访问，直接调用 `uv sync --frozen` 会立即引发依赖解析失败。

- **Required plan edits, ordered and concrete**
  1. **修改 0.1、0.3 与 0.5 节**：将针对 `a-stock-agent-skills` 的分支操作全部由 `master` 改回 `main`，并废弃 `git push origin master` 操作流程，改为 `git checkout -b <feature> && git push origin <feature> && 建立 PR`。
  2. **彻底删除 0.4 节**（取消 `a-stock-agent-skills` 的 master 初始化与主分支交替）。
  3. **修改 0.3 与 10 节校验命令**：将 `git status` 替换为 `git status --untracked-files=no`，以免被合法留存的未追踪文件阻断。
  4. **修改 Step 2A**：明确在暂无 Registry 时，`pyproject.toml` 中的 `a-stock-lib` 依赖应采用什么样的 fallback 策略（如 Git dependency 指针或约定好的 CI wheel 本地路径）。
  5. **废除 Step 2D 任务**：遵循 `a-stock-lib/AGENTS.md`，将 Downstream consumer 的校验活动移出本计划的执行与 CI 范围。
  6. **裁剪 Phase 5**：将 5A、5B、5C 完全移出当前 Codex 的自动重构范围，将重心专注于 Phase 1 的正确性验证。

- **Claims checked and found correct**
  - ✅ **Agent 越权读取私有 Cache**：计划指控存在直接跨界的私有缓存读取，经查，`a-stock-agent-skills/src/a_stock_agent_runtime/commands_holdings.py` 的确在第 111 行硬编码读取了 `~/.cache/a_stock_lib/tushare_industry_map.json`。
  - ✅ **主干分支状态符合现状**：查证确认 `a-stock-lib` 在 `master` 上，而 `a-stock-agent-skills` 确实如文档所述滞留在无保护的 `main`。
  - ✅ **重复评估引擎（重复框架）**：验证到 `a-stock-lib` 包含 `framework_scoring.py`，而同时 `a-stock-agent-skills` 也保留了 `checklist.py`，存在明确且危险的核心评分逻辑交叉重复。

- **Evidence gaps / limits**
  - **Exact-boundary 测试的遗留盲区**：无法通过静态搜索完全预测 `a-stock-lib` 内所有阈值的运行时浮点行为边界，所以计划中的 1A 针对性基线测试设计确属必须。
  - **GitHub CI 跨仓环境权限**：未通过实际建立流水线来探测 `a-stock-agent-skills` 的 CI 是否能自动克隆未公开发布的 `a-stock-lib` 依赖，如果未配备跨仓 token，Phase 2 将会不可靠。

## 父级核验与裁决

- 接受：保留现有默认分支、禁直推、使用 PR、裁剪预设 DDD 重构、补跨仓 consumer-first 回滚、明确不可变 artifact。
- 修正：不采用 `git status --untracked-files=no`，因为它会隐藏意外文件；改为保护原工作树并在隔离 worktree 内执行严格 clean 检查。
- 修正：不删除下游验证；依 `a-stock-lib/docs/RELEASE_CHECKLIST.md` 将其限定为 release-candidate gate，而不是普通 PR CI。
- 核验：两个仓库均为 public；当前默认分支分别为 `main`、`master`；`a-stock-lib` 当前无 GitHub Release，因此 artifact 发布前 Phase 2 明确 blocked。

## 修订后复审

第一次复审指出一个 P1：原排序要求 Phase 1 consumer 迁移依赖尚未发布的 owner artifact，而 artifact 到 Phase 2 才建立。已据此调整顺序：

1. Phase 1 只固定 owner exact-boundary；
2. Phase 2 建立不可变 wheel、正式依赖和 release gate；
3. Phase 3 才迁移 consumer 的重复评分与私有 cache 读取。

最终 AGY 复审：

- 状态：`SUCCESS`
- Verdict：`APPROVE`
- Conversation ID：`d63b60a1-b70f-4be5-8f22-da9004750507`
- P0/P1 remaining blockers：`None`
- Read-only drift check：计划 hash、两个仓库 status 在复审前后完全一致。
